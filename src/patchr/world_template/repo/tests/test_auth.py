from tinyshop.auth import can_issue_refund, is_staff


def test_is_staff():
    assert is_staff({"role": "staff"})
    assert not is_staff({"role": "customer"})


def test_refund_requires_mfa():
    assert not can_issue_refund({"role": "staff"})
    assert can_issue_refund({"role": "staff", "mfa": True})
