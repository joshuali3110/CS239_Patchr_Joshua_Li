# Patchr

Patchr is a multi-agent pipeline that takes a bug ticket for a small fictional checkout
service ("tinyshop") from diagnosis to a reviewed, deployed fix. Four agents work
together: Triage, Fixer, Reviewer (rule-based) and Release.

This is the Phase 1 prototype: policies are written into agent prompts but are not
enforced. Every tool call and message goes through one chokepoint (`patchr/tools.py:call_tool`)
and is recorded in a JSON trace.

## Requirements

- Python 3.13 and [uv](https://docs.astral.sh/uv/)
- An OpenAI-compatible model endpoint with tool calling. The default is the Gemini API
  (the free tier works). Not needed for `--fake` runs.

## Setup

```bash
uv sync
cp .env.example .env   # then set MODEL_ID and MODEL_API_KEY
```

| Variable | Meaning | Default |
|---|---|---|
| `MODEL_BASE_URL` | OpenAI-compatible endpoint | `https://generativelanguage.googleapis.com/v1beta/openai/` |
| `MODEL_ID` | Model name, e.g. `gemini-3.5-flash-lite` | required |
| `MODEL_API_KEY` | API key (falls back to `GEMINI_API_KEY`) | required |
| `MODEL_RPM` | Client-side request pacing, requests per minute | no pacing |
| `MODEL_TEMPERATURE` | Sampling temperature | provider default |
| `PATCHR_MAX_LLM_CALLS` | Model requests allowed per run | 60 |

## Usage

```bash
uv run patchr list                 # scenarios S1-S5
uv run patchr run S1 --fake        # offline: scripted stand-in model, no API calls
uv run patchr run S1               # real model; trace saved to traces/phase1/
uv run patchr replay traces/phase1/<run>.json   # replay a recorded run
```

Each run creates `.runs/<run_id>/` with the sandbox `workspace/`, mock production
`prod/` (with `DEPLOYED.json`), `logs/`, `tickets/`, `outbox/status.md` and `trace.json`.

## Tests

```bash
uv run pytest
```
