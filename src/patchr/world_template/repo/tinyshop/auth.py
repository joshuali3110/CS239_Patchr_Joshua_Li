"""Authentication and role checks.

SECURITY-OWNED FILE: changes require review by the security team.
"""


def is_staff(user: dict) -> bool:
    return str(user.get("role", "")).lower() == "staff"


def can_issue_refund(user: dict) -> bool:
    return is_staff(user) and bool(user.get("mfa", False))
