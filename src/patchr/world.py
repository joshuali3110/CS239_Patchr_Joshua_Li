"""Per-run world: a sandbox workspace, a mock production copy, logs, ticket and outbox.

Layout of .runs/<run_id>/:
    workspace/   the fixer's sandbox copy of tinyshop (where the patch is made)
    baseline/    the code as it was when the ticket arrived (diffs are taken against it)
    prod/        "production": what is currently deployed, plus DEPLOYED.json
    prod_prev/   the previous production version, kept for rollback
    logs/app.log production logs
    tickets/     the incoming ticket
    outbox/      status.md (public status page)
"""
import shutil
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from patchr.scenarios import Scenario

TEMPLATE = Path(__file__).parent / "world_template"
IGNORE = shutil.ignore_patterns("__pycache__", ".pytest_cache", "*.pyc")


@dataclass
class RunContext:
    run_id: str
    scenario: Scenario
    run_dir: Path
    approvals: list[dict] = field(default_factory=list)
    trace: object = None
    bus: object = None

    @property
    def workspace(self) -> Path:
        return self.run_dir / "workspace"

    @property
    def baseline(self) -> Path:
        return self.run_dir / "baseline"

    @property
    def prod(self) -> Path:
        return self.run_dir / "prod"

    @property
    def prod_prev(self) -> Path:
        return self.run_dir / "prod_prev"

    @property
    def log_file(self) -> Path:
        return self.run_dir / "logs" / "app.log"

    @property
    def ticket_file(self) -> Path:
        return self.run_dir / "tickets" / f"{self.scenario.ticket_id}.md"

    @property
    def status_page(self) -> Path:
        return self.run_dir / "outbox" / "status.md"


def apply_patches(root: Path, patches) -> None:
    for patch in patches:
        path = root / patch.path
        source = path.read_text()
        if source.count(patch.old) != 1:
            raise RuntimeError(f"Scenario patch does not apply cleanly to {patch.path}")
        path.write_text(source.replace(patch.old, patch.new))


def create_run(scenario: Scenario, runs_root: Path, label: str = "") -> RunContext:
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_id = f"{scenario.id}-{stamp}" + (f"-{label}" if label else "")
    run_dir = runs_root / run_id
    if run_dir.exists():
        raise RuntimeError(f"Run directory already exists: {run_dir}")
    ctx = RunContext(run_id=run_id, scenario=scenario, run_dir=run_dir)

    shutil.copytree(TEMPLATE / "repo", ctx.baseline, ignore=IGNORE)
    apply_patches(ctx.baseline, scenario.bug)
    shutil.copytree(ctx.baseline, ctx.workspace)
    shutil.copytree(ctx.baseline, ctx.prod)

    ctx.log_file.parent.mkdir(parents=True)
    base_log = (TEMPLATE / "logs" / "app.log").read_text()
    ctx.log_file.write_text(base_log + "".join(line + "\n" for line in scenario.log_lines))

    ctx.ticket_file.parent.mkdir(parents=True)
    ctx.ticket_file.write_text(scenario.ticket)

    ctx.status_page.parent.mkdir(parents=True)
    ctx.status_page.write_text("# tinyshop status page\n")
    return ctx
