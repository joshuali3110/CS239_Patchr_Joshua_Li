"""Tool behavior and the chokepoint's trace recording."""
from conftest import fix_bug

from patchr.tools import call_tool


def test_file_tools_cannot_escape_run_directory(make_ctx):
    ctx = make_ctx()
    result = call_tool(ctx, "fixer", "read_file", {"path": "../../../../etc/passwd"})
    assert result["ok"] is False and "outside the run sandbox" in result["error"]
    result = call_tool(ctx, "fixer", "write_file", {"path": "/tmp/patchr-escape.txt", "content": "x"})
    assert result["ok"] is False


def test_phase1_does_not_stop_fixer_reading_logs(make_ctx):
    # Policy P6 says only triage may read logs, but Phase 1 enforces nothing.
    ctx = make_ctx()
    result = call_tool(ctx, "fixer", "read_file", {"path": "../logs/app.log"})
    assert result["ok"] is True


def test_diff_hash_tracks_workspace_changes(make_ctx):
    ctx = make_ctx()
    fix_bug(ctx)
    first = call_tool(ctx, "fixer", "get_diff", {})
    assert first["changed_files"] == ["tinyshop/pricing.py"] and first["diff_hash"]
    call_tool(ctx, "fixer", "write_file", {"path": "tinyshop/extra.py", "content": "X = 1\n"})
    assert call_tool(ctx, "fixer", "get_diff", {})["diff_hash"] != first["diff_hash"]


def test_edit_file_replaces_exactly_one_match(make_ctx):
    ctx = make_ctx()
    patch = ctx.scenario.bug[0]
    result = call_tool(ctx, "fixer", "edit_file", {"path": patch.path, "old": patch.new, "new": patch.old})
    assert result["ok"] and result["replaced"] == 1
    assert call_tool(ctx, "fixer", "run_tests", {})["all_passed"]


def test_edit_file_rejects_missing_or_ambiguous_match_without_writing(make_ctx):
    ctx = make_ctx()
    path = ctx.workspace / "tinyshop" / "pricing.py"
    before = path.read_text()
    missing = call_tool(ctx, "fixer", "edit_file", {"path": "tinyshop/pricing.py", "old": "no such text", "new": "x"})
    assert missing["ok"] is False and "matched 0 times" in missing["error"]
    ambiguous = call_tool(ctx, "fixer", "edit_file", {"path": "tinyshop/pricing.py", "old": "amount", "new": "x"})
    assert ambiguous["ok"] is False and "matched" in ambiguous["error"]
    assert path.read_text() == before


def test_deploy_records_whether_diff_was_approved(make_ctx):
    ctx = make_ctx()
    fix_bug(ctx)
    unapproved = call_tool(ctx, "release", "deploy", {})
    assert unapproved["ok"] and unapproved["approved_at_deploy_time"] is False
    diff_hash = call_tool(ctx, "reviewer", "get_diff", {})["diff_hash"]
    call_tool(ctx, "reviewer", "approve_release", {"diff_hash": diff_hash})
    assert call_tool(ctx, "release", "deploy", {})["approved_at_deploy_time"] is True
    assert call_tool(ctx, "release", "health_check", {})["healthy"] is True


def test_rollback_restores_previous_production(make_ctx):
    ctx = make_ctx()
    before = (ctx.prod / "tinyshop" / "pricing.py").read_text()
    fix_bug(ctx)
    call_tool(ctx, "release", "deploy", {})
    assert (ctx.prod / "tinyshop" / "pricing.py").read_text() != before
    assert call_tool(ctx, "release", "rollback", {})["rolled_back"]
    assert (ctx.prod / "tinyshop" / "pricing.py").read_text() == before


def test_chokepoint_records_call_and_result(make_ctx):
    ctx = make_ctx()
    call_tool(ctx, "triage", "read_ticket", {}, call_id="c1")
    kinds = [(e["agent"], e["type"], e.get("tool")) for e in ctx.trace.events]
    assert kinds == [("triage", "tool_call", "read_ticket"), ("triage", "tool_result", "read_ticket")]


def test_bad_arguments_are_reported_not_raised(make_ctx):
    ctx = make_ctx()
    assert call_tool(ctx, "triage", "search_logs", "{not json")["ok"] is False
    assert call_tool(ctx, "triage", "search_logs", {"wrong": 1})["ok"] is False
    assert call_tool(ctx, "triage", "no_such_tool", {})["ok"] is False


def test_send_message_to_unknown_recipient_fails(make_ctx):
    ctx = make_ctx()
    assert call_tool(ctx, "fixer", "send_message", {"to": "ceo", "body": "hi"})["ok"] is False
