import pytest

from patchr import scenarios
from patchr.bus import Bus
from patchr.trace import Trace
from patchr.world import create_run


@pytest.fixture
def make_ctx(tmp_path):
    """Build a fresh run context for a scenario, with a trace and bus attached."""
    def _make(scenario_id="S1"):
        ctx = create_run(scenarios.get(scenario_id), tmp_path / "runs")
        ctx.trace = Trace({"run_id": ctx.run_id})
        ctx.bus = Bus(ctx.trace)
        return ctx
    return _make


def fix_bug(ctx):
    """Apply the correct fix for the scenario's bug, as a well-behaved fixer would."""
    for patch in ctx.scenario.bug:
        path = ctx.workspace / patch.path
        path.write_text(path.read_text().replace(patch.new, patch.old))
