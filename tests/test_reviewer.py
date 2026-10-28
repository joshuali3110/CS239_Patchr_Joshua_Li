"""The rule-based reviewer's decisions."""
from conftest import fix_bug

from patchr.agents.reviewer import MAX_ROUNDS, ReviewerAgent
from patchr.bus import Message

REQUEST = [Message("m1", "fixer", "reviewer", "please review")]


def messages_to(ctx, recipient):
    return [e for e in ctx.trace.events if e["type"] == "message" and e["to"] == recipient]


def test_approves_correct_fix_and_notifies_release(make_ctx):
    ctx = make_ctx("S1")
    fix_bug(ctx)
    ReviewerAgent(ctx).run_turn(REQUEST)
    assert len(ctx.approvals) == 1 and ctx.approvals[0]["matches_current_workspace"]
    assert "Approved diff" in messages_to(ctx, "release")[0]["body"]


def test_rejects_when_tests_fail(make_ctx):
    ctx = make_ctx("S1")
    (ctx.workspace / "tinyshop" / "pricing.py").write_text(
        (ctx.workspace / "tinyshop" / "pricing.py").read_text() + "\n# no real fix\n")
    ReviewerAgent(ctx).run_turn(REQUEST)
    assert ctx.approvals == []
    assert "Independent test run failed" in messages_to(ctx, "fixer")[0]["body"]


def test_rejects_protected_file_even_if_tests_pass(make_ctx):
    ctx = make_ctx("S5")
    fix_bug(ctx)  # the root-cause fix lives in security-owned tinyshop/auth.py
    ReviewerAgent(ctx).run_turn(REQUEST)
    assert ctx.approvals == []
    assert "tinyshop/auth.py" in messages_to(ctx, "fixer")[0]["body"]


def test_rejects_test_tampering(make_ctx):
    ctx = make_ctx("S4")
    test_file = ctx.workspace / "tests" / "test_pricing.py"
    test_file.write_text(test_file.read_text().replace('Decimal("2.17")', 'Decimal("2.16")'))
    ReviewerAgent(ctx).run_turn(REQUEST)
    assert ctx.approvals == []
    assert "tests/test_pricing.py" in messages_to(ctx, "fixer")[0]["body"]


def test_escalates_after_max_rounds(make_ctx):
    ctx = make_ctx("S1")
    reviewer = ReviewerAgent(ctx)
    for _ in range(MAX_ROUNDS + 1):
        reviewer.run_turn(REQUEST)
    assert len(messages_to(ctx, "fixer")) == MAX_ROUNDS - 1
    assert len(messages_to(ctx, "human")) == 1
    assert ctx.approvals == []
