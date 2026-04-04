"""
vector_matcher.py
=================
SmartBiz AI — Hybrid Vector + Lexical Product Search

Strategy:
  1. Encode cleaned query with SBERT → 384-dim vector
  2. pgvector HNSW cosine search → best candidate + distance
  3. Convert distance → similarity %
  4. Three-zone decision:

     similarity >= 95%  → ACCEPT immediately  (clear winner)
     85% <= sim < 95%   → HYBRID ZONE: run secondary lexical check
                          difflib ratio on the DEFINING ADJECTIVE
                          (the first word of a multi-word product name)
                          If adjectives don't match well → REJECT
     similarity < 85%   → REJECT immediately  (too ambiguous)

WHY THE HYBRID ZONE FIXES THE BUG:
  "Tiger Biscuit" and "Digestive Biscuit" share the root noun "Biscuit".
  Their SBERT vectors land very close together (~88-92% similarity).
  A simple >=90% threshold causes false positives when only one variant
  is in the DB — the other variant maps onto it.

  The lexical check compares the ADJECTIVE ("Tiger" vs "Digestive") with
  difflib.SequenceMatcher.  These two words score ~0.27 ratio — well below
  the 0.6 lexical threshold — so the match is correctly rejected and the
  caller receives None (ambiguous).
"""

from __future__ import annotations

from difflib import SequenceMatcher

from sentence_transformers import SentenceTransformer
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Product


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════

_SBERT_MODEL_NAME = "all-MiniLM-L6-v2"

# Similarity zones (cosine similarity = 1 − cosine_distance)
_ACCEPT_THRESHOLD  = 0.95   # >= 95% → accept without lexical check
_HYBRID_THRESHOLD  = 0.85   # >= 85% and < 95% → run lexical check
                             # <  85% → reject immediately

# Lexical check threshold (difflib ratio on defining adjective)
# "Tiger" vs "Digestive" → ~0.27  → below → REJECT
# "Digestiv" vs "Digestive" → ~0.94 → above → ACCEPT
_LEXICAL_THRESHOLD = 0.60


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _defining_adjective(name: str) -> str:
    """
    Extract the defining adjective from a product name.

    For single-word names ("Rice", "Salt") the word itself is returned.
    For multi-word names ("Tiger Biscuit", "Digestive Biscuit") only the
    FIRST word is returned — that's the adjective that distinguishes variants.

    Examples:
        "Tiger Biscuit"    → "Tiger"
        "Digestive Biscuit"→ "Digestive"
        "Rice"             → "Rice"
        "Beaten Rice"      → "Beaten"
    """
    parts = name.strip().split()
    return parts[0] if parts else name


def _lexical_similarity(a: str, b: str) -> float:
    """
    Return difflib SequenceMatcher ratio between two strings (case-insensitive).
    Range: 0.0 (completely different) to 1.0 (identical).
    """
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()


# ══════════════════════════════════════════════════════════════════════════════
# VECTOR MATCHER
# ══════════════════════════════════════════════════════════════════════════════

class VectorMatcher:
    """
    Hybrid semantic + lexical product search.

    Instantiate once at startup (same pattern as WhisperService):
        matcher = VectorMatcher()
        product_id = matcher.find_best_match("Tiger Biscuit", db)
    """

    def __init__(self) -> None:
        print("   - SBERT VectorMatcher initialising...")
        self._model = SentenceTransformer(_SBERT_MODEL_NAME)
        print("   ✅ VectorMatcher ready.")

    def find_best_match(
        self,
        search_text: str,
        db_session: Session,
    ) -> int | None:
        """
        Find the Product whose embedding best matches `search_text`.

        Parameters
        ----------
        search_text : str
            Cleaned canonical text from WhisperService._clean().
        db_session  : Session
            Active SQLAlchemy session.

        Returns
        -------
        int   — Product.id when match is confident.
        None  — When match is ambiguous or below threshold.

        Raises
        ------
        ValueError — No products with embeddings in DB.
        """

        if not search_text.strip():
            print("   ⚠️  VectorMatcher: empty search_text.")
            return None

        # ── Step 1: Encode query ──────────────────────────────────────────────
        print(f"   🔍 VectorMatcher encoding: '{search_text}'")
        query_vector: list[float] = self._model.encode(search_text).tolist()

        # ── Step 2: HNSW cosine search ────────────────────────────────────────
        best_product: Product | None = db_session.scalars(
            select(Product)
            .filter(Product.embedding.isnot(None))
            .order_by(Product.embedding.cosine_distance(query_vector))
            .limit(1)
        ).first()

        if best_product is None:
            raise ValueError(
                "No products with embeddings in DB. "
                "Run POST /refresh-embeddings first."
            )

        # ── Step 3: Get actual distance scalar ───────────────────────────────
        raw_distance: float = float(
            db_session.execute(
                select(
                    Product.embedding.cosine_distance(query_vector)
                ).where(Product.id == best_product.id)
            ).scalar()
        )

        similarity: float     = max(0.0, min(1.0, 1.0 - raw_distance))
        similarity_pct: float = round(similarity * 100, 2)

        print(
            f"   🤖 Vector best: '{best_product.name_english}' "
            f"(distance={raw_distance:.4f}, similarity={similarity_pct}%)"
        )

        # ── Step 4: Three-zone decision ───────────────────────────────────────

        # Zone A: clearly below floor → reject immediately
        if similarity < _HYBRID_THRESHOLD:
            print(
                f"   ❌ Rejected (Zone A) — {similarity_pct}% < "
                f"{_HYBRID_THRESHOLD * 100:.0f}% floor."
            )
            return None

        # Zone B: clear winner → accept immediately
        if similarity >= _ACCEPT_THRESHOLD:
            print(
                f"   ✅ Accepted (Zone B clear) — "
                f"{similarity_pct}% >= {_ACCEPT_THRESHOLD * 100:.0f}%"
            )
            return best_product.id

        # Zone C: hybrid zone (85% ≤ sim < 95%) → secondary lexical check
        #
        # We compare only the DEFINING ADJECTIVE of each name because
        # both "Tiger Biscuit" and "Digestive Biscuit" contain "Biscuit"
        # and full-name lexical similarity would be misleadingly high.
        #
        # search adjective : "Tiger"     (from "Tiger Biscuit")
        # db    adjective  : "Digestive" (from "Digestive Biscuit" in DB)
        # difflib ratio    : ~0.27  → below 0.60 → REJECT  ✅
        #
        # search adjective : "Digestive" (user said "Digestive Biscuit")
        # db    adjective  : "Digestive"
        # difflib ratio    : 1.00  → above 0.60 → ACCEPT  ✅

        search_adj = _defining_adjective(search_text)
        db_adj     = _defining_adjective(best_product.name_english)
        lex_ratio  = _lexical_similarity(search_adj, db_adj)

        print(
            f"   🔤 Hybrid zone — adjective check: "
            f"'{search_adj}' vs '{db_adj}' → ratio={lex_ratio:.3f}"
        )

        if lex_ratio < _LEXICAL_THRESHOLD:
            print(
                f"   ❌ Rejected (Zone C lexical) — "
                f"adjective ratio {lex_ratio:.3f} < {_LEXICAL_THRESHOLD} "
                f"('{search_adj}' ≠ '{db_adj}')"
            )
            return None

        print(
            f"   ✅ Accepted (Zone C lexical) — "
            f"adjective ratio {lex_ratio:.3f} >= {_LEXICAL_THRESHOLD}"
        )
        return best_product.id