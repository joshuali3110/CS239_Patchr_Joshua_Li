"""Model clients: an OpenAI-compatible client (Gemini by default) and a scripted fake."""
import time
from dataclasses import dataclass, field
from typing import Callable, Generator


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: str  # JSON text, as the model produced it


@dataclass
class Reply:
    content: str | None
    tool_calls: list[ToolCall]
    raw: dict  # the assistant message, appended to history exactly as received
    usage: dict = field(default_factory=dict)


class BudgetExceeded(RuntimeError):
    pass


class QuotaExhausted(RuntimeError):
    pass


class OpenAICompatModel:
    """Chat-completions client with request pacing and retry on overload.

    Gemini attaches a thought signature to tool calls (extra_content); the raw
    assistant message must be sent back unchanged on the next request.
    """
    RETRYABLE = {429, 500, 502, 503, 504}
    MAX_ATTEMPTS = 6

    def __init__(self, settings, max_calls: int, on_event: Callable | None = None):
        from openai import OpenAI
        self.client = OpenAI(base_url=settings.base_url, api_key=settings.api_key, max_retries=0, timeout=120)
        self.name = settings.model_id
        self.temperature = settings.temperature
        self.min_interval = 60 / settings.rpm if settings.rpm else 0
        self.max_calls = max_calls
        self.calls = 0
        self.on_event = on_event or (lambda *a, **k: None)
        self._last = 0.0

    def chat(self, agent: str, messages: list[dict], tools: list[dict]) -> Reply:
        from openai import APIConnectionError, APIStatusError
        kwargs = {"model": self.name, "messages": messages, "tools": tools}
        if self.temperature is not None:
            kwargs["temperature"] = self.temperature
        for attempt in range(1, self.MAX_ATTEMPTS + 1):
            if self.calls >= self.max_calls:
                raise BudgetExceeded(f"run reached its limit of {self.max_calls} model requests")
            wait = self._last + self.min_interval - time.monotonic()
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.calls += 1
            started = time.monotonic()
            try:
                response = self.client.chat.completions.create(**kwargs)
                break
            except APIStatusError as exc:
                text = str(exc)
                if exc.status_code == 429 and "PerDay" in text:
                    raise QuotaExhausted("daily request quota exhausted for this model") from exc
                if exc.status_code not in self.RETRYABLE or attempt == self.MAX_ATTEMPTS:
                    raise
                status = exc.status_code
            except APIConnectionError:
                if attempt == self.MAX_ATTEMPTS:
                    raise
                status = "connection"
            delay = min(60, 5 * 2 ** (attempt - 1))
            self.on_event(agent, "llm_retry", status=status, attempt=attempt, delay_s=delay)
            time.sleep(delay)

        message = response.choices[0].message
        raw = message.model_dump(exclude_none=True)
        calls = [ToolCall(tc.id, tc.function.name, tc.function.arguments or "{}") for tc in message.tool_calls or []]
        usage = response.usage.model_dump(exclude_none=True) if response.usage else {}
        self.on_event(agent, "llm_call", model=self.name, latency_s=round(time.monotonic() - started, 2),
                      usage={k: usage[k] for k in ("prompt_tokens", "completion_tokens") if k in usage})
        return Reply(content=message.content, tool_calls=calls, raw=raw, usage=usage)


# ---------------------------------------------------------------- scripted fake

def tool_call(name: str, arguments: str, thought: str | None = None) -> Reply:
    call = ToolCall(id=f"fake_{name}_{time.monotonic_ns()}", name=name, arguments=arguments)
    raw = {"role": "assistant", "content": thought,
           "tool_calls": [{"id": call.id, "type": "function",
                           "function": {"name": name, "arguments": arguments}}]}
    return Reply(content=thought, tool_calls=[call], raw=raw)


def final(text: str) -> Reply:
    return Reply(content=text, tool_calls=[], raw={"role": "assistant", "content": text})


class ScriptedModel:
    """Plays each agent from a generator script. For offline tests and demos only.

    A script yields Replies; each yield receives the agent's current message history.
    """
    name = "fake-scripted"

    def __init__(self, scripts: dict[str, Callable[[], Generator]]):
        self.scripts = scripts
        self.running: dict[str, Generator] = {}
        self.calls = 0

    def chat(self, agent: str, messages: list[dict], tools: list[dict]) -> Reply:
        self.calls += 1
        try:
            if agent not in self.running:
                self.running[agent] = self.scripts[agent]()
                return next(self.running[agent])
            return self.running[agent].send(messages)
        except StopIteration:
            return final("(script finished)")
