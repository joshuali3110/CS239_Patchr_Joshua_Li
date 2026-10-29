"""Checks on the recorded Phase 1 traces in traces/phase1/."""
import json
from pathlib import Path

import pytest

from patchr.tools import ALLOWED_TOOLS

TRACES = sorted((Path(__file__).resolve().parents[1] / "traces" / "phase1").glob("*.json"))


def test_at_least_three_scenarios_recorded():
    scenarios = {json.loads(p.read_text())["meta"]["scenario"] for p in TRACES}
    assert len(scenarios) >= 3


@pytest.mark.parametrize("path", TRACES, ids=lambda p: p.stem)
def test_trace_respects_p11_allowlists(path):
    events = json.loads(path.read_text())["events"]
    outside = [(e["seq"], e["agent"], e["tool"]) for e in events
               if e["type"] == "tool_call" and e["tool"] not in ALLOWED_TOOLS[e["agent"]]]
    assert outside == []


@pytest.mark.parametrize("path", TRACES, ids=lambda p: p.stem)
def test_trace_is_a_real_model_run(path):
    trace = json.loads(path.read_text())
    assert trace["meta"]["model"] != "fake-scripted"
    assert trace["outcome"]["end_reason"] == "quiescent"
