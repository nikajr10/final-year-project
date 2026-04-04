"""
crud.py
=======
SmartBiz AI — Atomic Database Operations

Design rules:
  • Every function accepts an active Session — never opens its own connection.
  • Every function commits internally — the caller never needs to call db.commit().
  • Every function returns a plain dict — routes stay decoupled from ORM objects.
  • Error conditions are returned as {"success": False, ...} — never raised,
    so FastAPI route handlers can pass them straight to JSONResponse.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import Product


# ══════════════════════════════════════════════════════════════════════════════
# INVENTORY MUTATIONS
# ══════════════════════════════════════════════════════════════════════════════

def deduct_inventory(
    db_session: Session,
    product_id: int,
    quantity:   int,
) -> dict:
    """
    Subtract `quantity` units from Product.current_stock and persist the change.

    Parameters
    ----------
    db_session : Session
        Active SQLAlchemy session (injected by FastAPI Depends(get_db)).
    product_id : int
        Primary key of the product to update.
    quantity   : int
        Number of units to deduct.  Must be > 0.

    Returns
    -------
    dict — always contains at minimum:
        success (bool)   — True on success, False on any error condition
        message (str)    — Human-readable result or error description

    On success, additionally contains:
        product_id   (int)
        name_english (str)
        name_nepali  (str)
        qty_deducted (int)
        new_stock    (int | float)
        unit         (str)

    Error cases handled (success=False, never raises):
        • quantity <= 0
        • Product ID not found
        • Resulting stock would go below zero
    """

    # ── Guard: valid quantity ─────────────────────────────────────────────────
    if quantity <= 0:
        return {
            "success":    False,
            "product_id": product_id,
            "message":    (
                f"Quantity must be greater than zero (received: {quantity}). "
                "Please say a positive number."
            ),
        }

    # ── Fetch product ─────────────────────────────────────────────────────────
    product: Product | None = db_session.get(Product, product_id)

    if product is None:
        return {
            "success":    False,
            "product_id": product_id,
            "message":    (
                f"Product with id={product_id} was not found in the database. "
                "The product catalogue may need to be updated."
            ),
        }

    # ── Guard: sufficient stock ───────────────────────────────────────────────
    if product.current_stock < quantity:
        return {
            "success":      False,
            "product_id":   product_id,
            "name_english": product.name_english,
            "name_nepali":  product.name_nepali,
            "unit":         product.unit,
            "message": (
                f"Insufficient stock: tried to remove {quantity} {product.unit} "
                f"of '{product.name_english}', but only "
                f"{_fmt(product.current_stock)} {product.unit} in stock. "
                "No change was made."
            ),
        }

    # ── Deduct + persist ──────────────────────────────────────────────────────
    product.current_stock -= quantity
    db_session.commit()
    db_session.refresh(product)   # reload from DB to confirm the written value

    new_stock = _fmt(product.current_stock)

    print(
        f"   ✅ Deducted {quantity} {product.unit} of "
        f"'{product.name_english}'. New stock: {new_stock} {product.unit}."
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
    Add `quantity` units to Product.current_stock and persist the change.

    Same contract as deduct_inventory — returns a plain dict with
    success/message keys so route handlers require zero conditional logic.
    """

    if quantity <= 0:
        return {
            "success":    False,
            "product_id": product_id,
            "message":    f"Quantity must be greater than zero (received: {quantity}).",
        }

    product: Product | None = db_session.get(Product, product_id)

    if product is None:
        return {
            "success":    False,
            "product_id": product_id,
            "message":    f"Product with id={product_id} not found.",
        }

    product.current_stock += quantity
    db_session.commit()
    db_session.refresh(product)

    new_stock = _fmt(product.current_stock)

    print(
        f"   ✅ Added {quantity} {product.unit} of "
        f"'{product.name_english}'. New stock: {new_stock} {product.unit}."
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
    Return current stock level for a single product without modifying anything.
    """

    product: Product | None = db_session.get(Product, product_id)

    if product is None:
        return {
            "success":    False,
            "product_id": product_id,
            "message":    f"Product with id={product_id} not found.",
        }

    return {
        "success":      True,
        "product_id":   product.id,
        "name_english": product.name_english,
        "name_nepali":  product.name_nepali,
        "current_stock": _fmt(product.current_stock),
        "unit":          product.unit,
        "message": (
            f"'{product.name_english}' has "
            f"{_fmt(product.current_stock)} {product.unit} in stock."
        ),
    }


# ══════════════════════════════════════════════════════════════════════════════
# PRIVATE HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _fmt(qty: float) -> int | float:
    """
    Return int for whole numbers (10.0 → 10), float for fractions (1.5 → 1.5).
    Keeps JSON responses clean — no trailing '.0' on integer quantities.
    """
    return int(qty) if qty == int(qty) else qty