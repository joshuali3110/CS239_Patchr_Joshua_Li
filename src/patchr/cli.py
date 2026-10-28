"""Command line: list scenarios, run one, or replay a saved trace."""
import argparse
import shutil
import time
from pathlib import Path

from patchr import config, scenarios
from patchr.printer import print_event
from patchr.trace import load

REPLAY_PAUSE = {"message": 1.2, "thought": 0.8, "turn_start": 0.6, "tool_call": 0.4}


def cmd_list(args) -> None:
    for s in scenarios.SCENARIOS.values():
        print(f"{s.id}  {s.title}\n    {s.purpose}\n    policies: {', '.join(s.policies)}")


def cmd_run(args) -> None:
    from patchr.runner import run_scenario
    scenario = scenarios.get(args.scenario)
    if args.fake:
        from patchr.fake_scripts import scripts_for
        from patchr.llm import ScriptedModel
        model = ScriptedModel(scripts_for(scenario))
    else:
        from patchr.llm import OpenAICompatModel
        settings = config.model_settings()
        model = OpenAICompatModel(settings, max_calls=config.MAX_LLM_CALLS)
        pace = f", paced to {settings.rpm:g} requests/min" if settings.rpm else ""
        print(f"Using {settings.model_id} via {settings.base_url}{pace}. Limit: {config.MAX_LLM_CALLS} requests.")
    listeners = [] if args.quiet else [print_event]
    ctx, outcome = run_scenario(scenario, model, label="fake" if args.fake else "", listeners=listeners)
    print(f"\nRun directory: {ctx.run_dir}")
    print(f"Trace:         {ctx.run_dir / 'trace.json'}")
    if not args.fake and not args.no_save:
        dest = config.TRACES_ROOT / f"{ctx.run_id}.json"
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ctx.run_dir / "trace.json", dest)
        print(f"Saved to:      {dest}")


def cmd_replay(args) -> None:
    trace = load(Path(args.trace))
    meta = trace["meta"]
    print(f"REPLAY of recorded run {meta['run_id']} (model: {meta['model']}, recorded {meta['started_at']})")
    for event in trace["events"]:
        print_event(event)
        time.sleep(REPLAY_PAUSE.get(event["type"], 0.15) * args.speed)


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="patchr", description="Patchr: multi-agent bug-fix and release pipeline")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="list scenarios").set_defaults(func=cmd_list)
    run = sub.add_parser("run", help="run a scenario")
    run.add_argument("scenario", help="scenario id, e.g. S1")
    run.add_argument("--fake", action="store_true", help="use the scripted offline model (no API calls)")
    run.add_argument("--quiet", action="store_true", help="do not print events live")
    run.add_argument("--no-save", action="store_true", help="do not copy the trace into traces/phase1/")
    run.set_defaults(func=cmd_run)
    replay = sub.add_parser("replay", help="replay a saved trace at reading speed")
    replay.add_argument("trace", help="path to a trace JSON file")
    replay.add_argument("--speed", type=float, default=1.0, help="pause multiplier (0 = no pauses)")
    replay.set_defaults(func=cmd_replay)
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
