"""End-to-end runs with the scripted offline model (no API calls)."""
import json

import pytest

from patchr import scenarios
from patchr.fake_scripts import scripts_for
from patchr.llm import ScriptedModel
from patchr.runner import run_scenario


@pytest.mark.parametrize("scenario_id", ["S1", "S4"])
def test_compliant_pipeline_deploys_approved_fix(tmp_path, scenario_id):
    scenario = scenarios.get(scenario_id)
    ctx, outcome = run_scenario(scenario, ScriptedModel(scripts_for(scenario)), runs_root=tmp_path)
    assert outcome["end_reason"] == "quiescent"
    assert outcome["deployed"] and outcome["deployment"]["approved_at_deploy_time"]
    assert outcome["deployment"]["diff_hash"] == outcome["approvals"][0]["diff_hash"]
    assert outcome["status_updates"] == 1

    trace = json.loads((ctx.run_dir / "trace.json").read_text())
    routes = [(e["sender"], e["to"]) for e in trace["events"] if e["type"] == "message"]
    assert routes == [("ticket_system", "triage"), ("triage", "fixer"), ("fixer", "reviewer"),
                      ("reviewer", "release"), ("release", "human")]
    assert trace["meta"]["model"] == "fake-scripted"


def test_trace_events_are_ordered_and_typed(tmp_path):
    scenario = scenarios.get("S1")
    ctx, _ = run_scenario(scenario, ScriptedModel(scripts_for(scenario)), runs_root=tmp_path)
    events = ctx.trace.events
    assert [e["seq"] for e in events] == list(range(1, len(events) + 1))
    assert {e["type"] for e in events} >= {"run_start", "turn_start", "thought", "tool_call", "tool_result",
                                           "message", "turn_end", "run_end"}
