"""
crud.py
=======
SmartBiz AI — Atomic Database Operations

Race-condition fix in deduct_inventory:
  OLD (unsafe):
      product = db.get(Product, id)        # read stock into Python
      product.current_stock -= quantity    # math in Python
      db.commit()                          # write back
      ↑ Two concurrent requests both read the same stock value,
        both subtract, both commit — one subtraction is silently lost.

  NEW (safe) — row-level locking with SELECT ... FOR UPDATE:
      product = db.get(Product, id, with_lockmode="update")
      # PostgreSQL now holds an exclusive row lock.
      # Any second request trying to read the same row blocks here
      # until the first transaction commits and releases the lock.
      # The second request then reads the ALREADY-UPDATED value.
      product.current_stock -= quantity
      db.commit()   # lock released here

  The stock-below-zero guard runs AFTER acquiring the lock so the
  check and the write are atomic — no other transaction can sneak in
  between the check and the commit.

  add_inventory uses the same locking pattern for consistency.
"""

from __future__ import annotations

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.models import Product


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# Routes catch these for clean JSON error responses.
# ══════════════════════════════════════════════════════════════════════════════

class InsufficientStockError(Exception):
    """Raised when a deduction would push stock below zero."""
    pass


class ProductNotFoundError(Exception):
    """Raised when the product_id does not exist in the database."""
    pass


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY MUTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def deduct_inventory(
    db_session: Session,
    product_id: int,
    quantity:   int,
) -> dict:
    """
    Atomically subtract `quantity` from Product.current_stock.

    Uses SELECT FOR UPDATE to acquire a row-level exclusive lock before
    reading the stock value.  This prevents the race condition where two
    concurrent requests both read the same stock and both subtract,
    causing one subtraction to be silently lost.

    Parameters
    ----------
    db_session : Session
    product_id : int
    quantity   : int  — must be > 0

    Returns
    -------
    dict with success=True and updated product details.

    Raises
    ------
    ValueError            — quantity <= 0
    ProductNotFoundError  — product_id not in DB
    InsufficientStockError— stock would go below zero
    """

    # ── Guard: valid quantity ─────────────────────────────────────────────────
    if quantity <= 0:
        raise ValueError(
            f"Quantity must be > 0 (received: {quantity})."
        )

    # ── Acquire row-level lock (SELECT ... FOR UPDATE) ────────────────────────
    # PostgreSQL holds an exclusive lock on this row until db_session.commit().
    # Any concurrent transaction that tries to lock the same row blocks here
    # and waits — it will read the post-commit stock value when it unblocks.
    product: Product | None = db_session.scalars(
        select(Product)
        .where(Product.id == product_id)
        .with_for_update()          # ← the key line — acquires row lock
    ).first()

    if product is None:
        raise ProductNotFoundError(
            f"Product id={product_id} not found in database."
        )

    # ── Guard: sufficient stock ───────────────────────────────────────────────
    # This check is now atomic with the subsequent write because we hold the
    # row lock — no other transaction can modify current_stock between here
    # and the commit below.
    if product.current_stock < quantity:
        raise InsufficientStockError(
            f"Insufficient stock: tried to remove {quantity} {product.unit} "
            f"of '{product.name_english}', but only "
            f"{_fmt(product.current_stock)} {product.unit} available."
        )

    # ── Atomic deduct + commit (releases lock) ────────────────────────────────
    product.current_stock -= quantity
    db_session.commit()
    db_session.refresh(product)

    new_stock = _fmt(product.current_stock)
    print(
        f"   ✅ Deducted {quantity} {product.unit} of "
        f"'{product.name_english}'. New stock: {new_stock}."
    )

    return {
        "success":      True,
        "product_id":   product.id,
        "name_english": product.name_english,
        "name_nepali":  product.name_nepali,
        "qty_deducted": quantity,
        "new_stock":    new_stock,
        "unit":         product.unit,
        "message": (
            f"Removed {quantity} {product.unit} of '{product.name_english}'. "
            f"{new_stock} {product.unit} remaining."
        ),
    }


def add_inventory(
    db_session: Session,
    product_id: int,
    quantity:   int,
) -> dict:
    """
    Atomically add `quantity` to Product.current_stock.
    Uses the same SELECT FOR UPDATE locking pattern as deduct_inventory.
    """

    if quantity <= 0:
        raise ValueError(f"Quantity must be > 0 (received: {quantity}).")

    product: Product | None = db_session.scalars(
        select(Product)
        .where(Product.id == product_id)
        .with_for_update()
    ).first()

    if product is None:
        raise ProductNotFoundError(
            f"Product id={product_id} not found in database."
        )

    product.current_stock += quantity
    db_session.commit()
    db_session.refresh(product)

    new_stock = _fmt(product.current_stock)
    print(
        f"   ✅ Added {quantity} {product.unit} of "
        f"'{product.name_english}'. New stock: {new_stock}."
    )

    return {
        "success":      True,
        "product_id":   product.id,
        "name_english": product.name_english,
        "name_nepali":  product.name_nepali,
        "qty_added":    quantity,
        "new_stock":    new_stock,
        "unit":         product.unit,
        "message": (
            f"Added {quantity} {product.unit} of '{product.name_english}'. "
            f"{new_stock} {product.unit} now in stock."
        ),
    }


def get_stock(
    db_session: Session,
    product_id: int,
) -> dict:
    """
    Return current stock for a single product — read-only, no lock needed.
    """

    product: Product | None = db_session.get(Product, product_id)

    if product is None:
        raise ProductNotFoundError(
            f"Product id={product_id} not found in database."
        )

    return {
        "success":       True,
        "product_id":    product.id,
        "name_english":  product.name_english,
        "name_nepali":   product.name_nepali,
        "current_stock": _fmt(product.current_stock),
        "unit":          product.unit,
        "message": (
            f"'{product.name_english}' has "
            f"{_fmt(product.current_stock)} {product.unit} in stock."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt(qty: float) -> int | float:
    """10.0 → 10,  1.5 → 1.5  (keeps JSON clean)."""
    return int(qty) if qty == int(qty) else qty