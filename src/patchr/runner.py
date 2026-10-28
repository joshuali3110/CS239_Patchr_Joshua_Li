"""Runs one scenario: builds the world, wires agents to the bus, schedules turns."""
import json
from pathlib import Path

from patchr import config
from patchr.agents.llm_agent import LLMAgent
from patchr.agents.reviewer import ReviewerAgent
from patchr.bus import AGENTS, Bus
from patchr.llm import BudgetExceeded, QuotaExhausted
from patchr.scenarios import Scenario
from patchr.tools import compute_diff
from patchr.trace import Trace
from patchr.world import create_run


def build_agents(ctx, model) -> dict:
    return {
        "triage": LLMAgent("triage", ctx, model),
        "fixer": LLMAgent("fixer", ctx, model),
        "reviewer": ReviewerAgent(ctx),
        "release": LLMAgent("release", ctx, model),
    }


def outcome_of(ctx, model, end_reason: str) -> dict:
    deployed_file = ctx.prod / "DEPLOYED.json"
    deployed = json.loads(deployed_file.read_text()) if deployed_file.exists() else None
    status = ctx.status_page.read_text().split("\n## ")[1:]
    return {
        "end_reason": end_reason,
        "workspace_diff_hash": compute_diff(ctx)["diff_hash"],
        "approvals": ctx.approvals,
        "deployed": deployed is not None,
        "deployment": deployed,
        "status_updates": len(status),
        "model_requests": model.calls,
        "tool_calls": sum(1 for e in ctx.trace.events if e["type"] == "tool_call"),
        "messages": ctx.bus.count,
    }


def run_scenario(scenario: Scenario, model, runs_root: Path = config.RUNS_ROOT, label: str = "",
                 listeners=()) -> tuple:
    ctx = create_run(scenario, runs_root, label)
    ctx.trace = Trace({"run_id": ctx.run_id, "phase": 1, "scenario": scenario.id,
                       "scenario_title": scenario.title, "ticket_id": scenario.ticket_id,
                       "model": model.name, "run_dir": str(ctx.run_dir)})
    ctx.trace.listeners.extend(listeners)
    if hasattr(model, "on_event"):
        model.on_event = lambda agent, type, **data: ctx.trace.emit(agent, type, **data)
    ctx.bus = Bus(ctx.trace)
    agents = build_agents(ctx, model)

    ctx.trace.emit("system", "run_start", scenario=scenario.id, title=scenario.title, model=model.name)
    ctx.bus.send("ticket_system", "triage",
                 f"New ticket {scenario.ticket_id} has been assigned to you. Use read_ticket to read it.")

    end_reason, turns = "quiescent", 0
    try:
        while any(ctx.bus.has_mail(name) for name in AGENTS):
            for name in AGENTS:
                if ctx.bus.has_mail(name):
                    turns += 1
                    if turns > config.MAX_TURNS:
                        raise BudgetExceeded(f"run reached its limit of {config.MAX_TURNS} agent turns")
                    agents[name].run_turn(ctx.bus.drain(name))
    except (BudgetExceeded, QuotaExhausted) as exc:
        end_reason = f"stopped: {exc}"
        ctx.trace.emit("system", "error", error=str(exc))
    except Exception as exc:
        end_reason = f"crashed: {type(exc).__name__}: {exc}"
        ctx.trace.emit("system", "error", error=end_reason)
        raise
    finally:
        outcome = outcome_of(ctx, model, end_reason)
        ctx.trace.emit("system", "run_end", outcome=outcome)
        ctx.trace.save(ctx.run_dir / "trace.json", outcome)
    return ctx, outcome
