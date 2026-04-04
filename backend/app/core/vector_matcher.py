"""
vector_matcher.py
=================
SmartBiz AI — Semantic Product Search via pgvector HNSW

Strategy:
  1. Encode cleaned query text with SBERT (same model as seed_data.py / main.py)
  2. Ask PostgreSQL to find the closest Product embedding by cosine distance
     (HNSW index in models.py makes this O(log n) automatically)
  3. Convert cosine distance → similarity percentage
  4. Enforce a strict 90% similarity guardrail — return None if too ambiguous

Cosine distance ↔ similarity mapping:
  cosine_distance = 0.00  →  similarity = 100%  (identical)
  cosine_distance = 0.10  →  similarity =  90%  ← our acceptance floor
  cosine_distance = 0.50  →  similarity =  50%
  cosine_distance = 1.00  →  similarity =   0%  (orthogonal / unrelated)
"""

from __future__ import annotations

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Product


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

# MUST be the same model used in seed_data.py and main.py.
# All stored embeddings and query embeddings must live in the same
# 384-dimensional space — mixing models produces garbage similarity scores.
_SBERT_MODEL_NAME = "all-MiniLM-L6-v2"

# Hard guardrail: reject any match below 90% cosine similarity.
# cosine_similarity = 1 − cosine_distance
# 90% similarity ↔ cosine_distance < 0.10
_SIMILARITY_THRESHOLD = 0.90


# ══════════════════════════════════════════════════════════════════════════════
# VECTOR MATCHER
# ══════════════════════════════════════════════════════════════════════════════

class VectorMatcher:
    """
    Wraps SBERT encoding + pgvector cosine search into a single deterministic call.

    Usage (in main.py / routes.py):
        vector_matcher = VectorMatcher()          # once at startup

        product_id = vector_matcher.find_best_match("Digestive Biscuit", db)
        if product_id is None:
            # similarity < 90% — command too ambiguous, reject
    """

    def __init__(self) -> None:
        print("   - SBERT VectorMatcher initialising...")
        self._model = SentenceTransformer(_SBERT_MODEL_NAME)
        print("   ✅ VectorMatcher ready.")

    # ──────────────────────────────────────────────────────────────────────────
    # PUBLIC API
    # ──────────────────────────────────────────────────────────────────────────

    def find_best_match(
        self,
        search_text: str,
        db_session: Session,
    ) -> int | None:
        """
        Find the Product whose embedding is closest to `search_text`.

        Parameters
        ----------
        search_text : str
            Cleaned canonical text from WhisperService._clean().
            Examples: "Digestive Biscuit", "Rice", "10 packet Flour Remove"
        db_session  : Session
            Active SQLAlchemy session — injected by FastAPI Depends(get_db).

        Returns
        -------
        int
            Product.id of the best match when similarity >= 90%.
        None
            When similarity < 90% (command too ambiguous — caller should reject).

        Raises
        ------
        ValueError
            When the database contains no products with stored embeddings.
            Fix: call POST /refresh-embeddings first.
        """

        if not search_text.strip():
            print("   ⚠️  VectorMatcher: empty search_text — returning None.")
            return None

        # ── Step 1: Encode the query string → 384-dim vector ─────────────────
        print(f"   🔍 VectorMatcher: encoding '{search_text}'...")
        query_vector: list[float] = self._model.encode(search_text).tolist()

        # ── Step 2: HNSW cosine nearest-neighbour search ──────────────────────
        # PostgreSQL automatically selects the HNSW index (vector_cosine_ops)
        # defined in models.py — no manual hinting required.
        # With 10 products this runs in < 1ms; scales to millions with same speed.
        best_product: Product | None = db_session.scalars(
            select(Product)
            .filter(Product.embedding.isnot(None))   # skip unembedded rows
            .order_by(Product.embedding.cosine_distance(query_vector))
            .limit(1)
        ).first()

        if best_product is None:
            raise ValueError(
                "No products with embeddings found. "
                "Call POST /refresh-embeddings to generate them."
            )

        # ── Step 3: Retrieve the actual distance scalar ───────────────────────
        # .order_by(cosine_distance) sorts rows but does NOT expose the value.
        # A targeted single-row query returns the float we need for thresholding.
        raw_distance: float = float(
            db_session.execute(
                select(
                    Product.embedding.cosine_distance(query_vector)
                ).where(Product.id == best_product.id)
            ).scalar()
        )

        # ── Step 4: Convert distance → human-readable similarity ─────────────
        # cosine_distance ∈ [0, 2] in pgvector (can exceed 1 for anti-parallel vectors)
        # We clamp to [0, 1] to get a well-defined similarity percentage.
        similarity: float     = max(0.0, min(1.0, 1.0 - raw_distance))
        similarity_pct: float = round(similarity * 100, 2)

        print(
            f"   🤖 Best match: '{best_product.name_english}' "
            f"(cosine_distance={raw_distance:.4f}, similarity={similarity_pct}%)"
        )

        # ── Step 5: Guardrail ─────────────────────────────────────────────────
        if similarity < _SIMILARITY_THRESHOLD:
            print(
                f"   ❌ Rejected — {similarity_pct}% is below the "
                f"{_SIMILARITY_THRESHOLD * 100:.0f}% acceptance threshold."
            )
            return None

        print(f"   ✅ Accepted — product_id={best_product.id} ({best_product.name_english})")
        return best_product.id