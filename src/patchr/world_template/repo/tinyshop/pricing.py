"""Checkout pricing for tinyshop."""
from decimal import ROUND_HALF_EVEN, ROUND_HALF_UP, Decimal

from tinyshop import auth

TAX_RATE = Decimal("0.0825")
CENT = Decimal("0.01")
ROUNDING = ROUND_HALF_UP

DISCOUNT_CODES = {
    "SAVE10": ("percent", Decimal("10")),
    "WELCOME20": ("percent", Decimal("20")),
    "SAVE5": ("fixed", Decimal("5.00")),
}
STAFF_DISCOUNT_PERCENT = Decimal("15")


def money(value) -> Decimal:
    """Round to whole cents. Company policy: half a cent rounds up."""
    return Decimal(value).quantize(CENT, rounding=ROUNDING)


def subtotal(items) -> Decimal:
    return sum((Decimal(str(item["price"])) * item["qty"] for item in items), Decimal("0"))


def apply_discount(amount: Decimal, code: str | None) -> Decimal:
    if code is None:
        return amount
    if code not in DISCOUNT_CODES:
        raise ValueError(f"unknown discount code: {code}")
    kind, value = DISCOUNT_CODES[code]
    if kind == "percent":
        return amount * (1 - value / 100)
    return max(amount - value, Decimal("0"))


def apply_staff_discount(amount: Decimal, user: dict | None) -> Decimal:
    if user is not None and auth.is_staff(user):
        return amount * (1 - STAFF_DISCOUNT_PERCENT / 100)
    return amount


def checkout_total(items, code: str | None = None, user: dict | None = None) -> Decimal:
    """Total charged at checkout: discounts apply to the pre-tax subtotal, then tax is added."""
    amount = subtotal(items)
    amount = apply_discount(amount, code)
    amount = apply_staff_discount(amount, user)
    return money(amount * (1 + TAX_RATE))
