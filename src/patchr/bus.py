"""Message bus between agents: per-agent inboxes and a sink for the on-call human."""
from collections import defaultdict
from dataclasses import dataclass

AGENTS = ("triage", "fixer", "reviewer", "release")
# Recipients that are recorded but never scheduled: they are outside the agent system.
SINKS = ("human",)


@dataclass(frozen=True)
class Message:
    id: str
    sender: str
    to: str
    body: str


class Bus:
    def __init__(self, trace):
        self.trace = trace
        self.inboxes: dict[str, list[Message]] = defaultdict(list)
        self.count = 0

    def send(self, sender: str, to: str, body: str) -> Message:
        if to not in AGENTS and to not in SINKS:
            raise ValueError(f"unknown recipient {to!r}; valid recipients: {', '.join(AGENTS + SINKS)}")
        if to == sender:
            raise ValueError("an agent cannot message itself")
        self.count += 1
        message = Message(id=f"m{self.count}", sender=sender, to=to, body=body)
        if to in AGENTS:
            self.inboxes[to].append(message)
        self.trace.emit(sender, "message", msg_id=message.id, sender=sender, to=to, body=body)
        return message

    def has_mail(self, agent: str) -> bool:
        return bool(self.inboxes[agent])

    def drain(self, agent: str) -> list[Message]:
        messages, self.inboxes[agent] = self.inboxes[agent], []
        return messages
