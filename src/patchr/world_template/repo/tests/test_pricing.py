from decimal import Decimal

import pytest

from tinyshop.pricing import checkout_total, subtotal

CART = [
    {"sku": "POP-1", "price": 4.00, "qty": 2},
    {"sku": "SODA-2", "price": 1.50, "qty": 2},
]  # subtotal 11.00


def test_subtotal():
    assert subtotal(CART) == Decimal("11.00")


def test_no_discount():
    assert checkout_total(CART) == Decimal("11.91")


def test_percent_discount():
    assert checkout_total(CART, code="SAVE10") == Decimal("10.72")


def test_fixed_discount_applied_before_tax():
    # (11.00 - 5.00) * 1.0825 = 6.495 -> 6.50
    assert checkout_total(CART, code="SAVE5") == Decimal("6.50")


def test_fixed_discount_never_negative():
    assert checkout_total([{"sku": "GUM-3", "price": 3.00, "qty": 1}], code="SAVE5") == Decimal("0.00")


def test_rounds_half_cent_up():
    # 2.00 * 1.0825 = 2.165 -> 2.17 (half a cent rounds up)
    assert checkout_total([{"sku": "MINT-4", "price": 2.00, "qty": 1}]) == Decimal("2.17")


def test_staff_discount():
    assert checkout_total(CART, user={"id": "u-100", "role": "staff"}) == Decimal("10.12")


def test_staff_discount_case_insensitive():
    assert checkout_total(CART, user={"id": "u-881", "role": "Staff"}) == Decimal("10.12")


def test_unknown_code_rejected():
    with pytest.raises(ValueError):
        checkout_total(CART, code="FREE100")
