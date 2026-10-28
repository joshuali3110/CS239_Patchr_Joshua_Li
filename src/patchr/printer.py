"""Human-readable, colored rendering of trace events (used live and for replay)."""
import json
import shutil
import sys
import textwrap

COLORS = {"triage": "36", "fixer": "33", "reviewer": "35", "release": "32",
          "human": "1;31", "ticket_system": "90", "system": "90"}
USE_COLOR = sys.stdout.isatty()


def paint(text: str, agent: str) -> str:
    return f"\033[{COLORS.get(agent, '0')}m{text}\033[0m" if USE_COLOR else text


def dim(text: str) -> str:
    return f"\033[2m{text}\033[0m" if USE_COLOR else text


def short(value, limit: int = 160) -> str:
    text = value if isinstance(value, str) else json.dumps(value)
    text = " ".join(text.split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def wrap(text: str, indent: str) -> str:
    width = max(60, shutil.get_terminal_size((100, 20)).columns - 2)
    lines = []
    for paragraph in text.splitlines() or [""]:
        lines.extend(textwrap.wrap(paragraph, width, initial_indent=indent, subsequent_indent=indent) or [indent])
    return "\n".join(lines)


def summarize_result(tool: str, result: dict) -> str:
    if not result.get("ok", True):
        return "ERROR " + result.get("error", "")
    keys = {
        "run_tests": ("summary", "failures"), "health_check": ("healthy", "passed", "failed"),
        "get_diff": ("diff_hash", "changed_files"), "get_approval": ("current_diff_hash", "current_diff_approved"),
        "deploy": ("diff_hash", "approved_at_deploy_time"), "search_logs": ("total_matches",),
        "write_file": ("path", "bytes_written"), "read_file": ("path",), "list_files": ("files",),
        "read_ticket": ("ticket_id",), "approve_release": ("diff_hash", "matches_current_workspace"),
    }.get(tool)
    picked = {k: result[k] for k in keys if k in result} if keys else {k: v for k, v in result.items() if k != "ok"}
    return short(picked)


def format_event(event: dict) -> str | None:
    agent, kind = event["agent"], event["type"]
    tag = paint(f"[{agent}]", agent)
    if kind == "run_start":
        return paint(f"\n=== Patchr run: {event['scenario']} — {event['title']}  (model: {event['model']}) ===\n", "system")
    if kind == "turn_start":
        return paint(f"\n── {agent}'s turn " + "─" * 40, agent)
    if kind == "thought":
        return f"{tag} {dim('thinks:')}\n" + dim(wrap(event["text"], "    "))
    if kind == "tool_call":
        if event["tool"] == "send_message":
            return None
        return f"{tag} → {event['tool']}({short(event['args'], 120)})"
    if kind == "tool_result":
        if event["tool"] == "send_message":
            return None
        return dim(f"{' ' * len(agent)}   ← {summarize_result(event['tool'], event['result'])}")
    if kind == "message":
        head = paint(f"[{event['sender']} ✉ {event['to']}]", event["sender"])
        return f"{head}\n" + wrap(event["body"], "    ")
    if kind == "llm_retry":
        return dim(f"{tag} model busy ({event['status']}); retry {event['attempt']} in {event['delay_s']}s")
    if kind == "error":
        return paint(f"!! {event['error']}", "human")
    if kind == "run_end":
        o = event["outcome"]
        dep = o.get("deployment") or {}
        lines = ["", paint("=== Run finished ===", "system"),
                 f"  end reason:      {o['end_reason']}",
                 f"  approvals:       {[a['diff_hash'] for a in o['approvals']] or 'none'}",
                 f"  deployed:        {dep.get('diff_hash') if o['deployed'] else 'no'}"
                 + (f" (approved at deploy time: {dep.get('approved_at_deploy_time')})" if o["deployed"] else ""),
                 f"  status updates:  {o['status_updates']}",
                 f"  model requests:  {o['model_requests']}   tool calls: {o['tool_calls']}   messages: {o['messages']}"]
        return "\n".join(lines)
    return None


def print_event(event: dict) -> None:
    text = format_event(event)
    if text is not None:
        print(text, flush=True)
