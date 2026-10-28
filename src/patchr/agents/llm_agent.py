"""LLM-based agent: a tool-calling loop over the shared chokepoint."""
import json
from pathlib import Path

from patchr import config
from patchr.tools import SCHEMAS, call_tool

PROMPTS = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    return (PROMPTS / f"{name}.md").read_text()


def format_inbox(messages) -> str:
    parts = [f"You have {len(messages)} new message(s)."]
    for m in messages:
        parts.append(f"--- message {m.id} from {m.sender} ---\n{m.body}")
    return "\n\n".join(parts)


class LLMAgent:
    def __init__(self, name: str, ctx, model, tool_names=None):
        self.name = name
        self.ctx = ctx
        self.model = model
        # Phase 1: every agent sees every tool; its prompt says which ones to use.
        self.tools = [SCHEMAS[t] for t in (tool_names or SCHEMAS)]
        self.history: list[dict] = [{"role": "system", "content": load_prompt(name)}]

    def run_turn(self, inbox) -> None:
        trace = self.ctx.trace
        trace.emit(self.name, "turn_start", inbox=[m.id for m in inbox])
        self.history.append({"role": "user", "content": format_inbox(inbox)})
        for _ in range(config.MAX_STEPS_PER_TURN):
            reply = self.model.chat(self.name, self.history, self.tools)
            self.history.append(reply.raw)
            if reply.content and reply.content.strip():
                trace.emit(self.name, "thought", text=reply.content.strip())
            if not reply.tool_calls:
                trace.emit(self.name, "turn_end", reason="done")
                return
            for call in reply.tool_calls:
                result = call_tool(self.ctx, self.name, call.name, call.arguments, call_id=call.id)
                self.history.append({"role": "tool", "tool_call_id": call.id,
                                     "content": json.dumps(result)})
        trace.emit(self.name, "turn_end", reason="step_limit")
