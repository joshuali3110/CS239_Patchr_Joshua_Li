"""Structured run traces: every thought, tool call, tool result and message, in order."""
import json
import time
from datetime import datetime, timezone
from pathlib import Path


class Trace:
    def __init__(self, meta: dict):
        self.meta = {**meta, "started_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        self.events: list[dict] = []
        self.listeners = []
        self._start = time.monotonic()

    def emit(self, agent: str, type: str, **data) -> dict:
        event = {"seq": len(self.events) + 1, "t": round(time.monotonic() - self._start, 2),
                 "agent": agent, "type": type, **data}
        self.events.append(event)
        for listener in self.listeners:
            listener(event)
        return event

    def to_dict(self, outcome: dict | None = None) -> dict:
        meta = {**self.meta, "ended_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
        return {"meta": meta, "outcome": outcome or {}, "events": self.events}

    def save(self, path: Path, outcome: dict | None = None) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(outcome), indent=2) + "\n")
        return path


def load(path: Path) -> dict:
    return json.loads(Path(path).read_text())
