# Patchr: a multi-agent bug-fix and release pipeline

CS239 (Agentic Software Engineering, UCLA, Fall 2026) project by Joshua Li. MIT licensed.

Patchr takes a bug ticket for **tinyshop**, a small fictional checkout service, from diagnosis to a reviewed, deployed fix:

```
ticket ─▶ Triage ─▶ Fixer ⇄ Reviewer ─▶ Release ─▶ production + public status page
          (LLM)     (LLM)   (rules)     (LLM)        └─▶ report to the on-call human
```

- **Triage** reads the ticket and production logs and hands the Fixer a redacted bug report.
- **Fixer** patches the code in a sandbox until the tests pass.
- **Reviewer** is deterministic: it checks the change's scope, runs the tests itself, and approves one exact diff hash.
- **Release** deploys only that approved diff, runs a health check, rolls back on failure, and posts a public status update.

**Phase 1 (this version)** states the policies only in the agents' prompts. Every tool call and message goes through one chokepoint (`call_tool`) that records it in a trace; Phase 2 will enforce the policies there.

## Where things are

| Deliverable | Location |
|---|---|
| Requirements | [requirements.md](requirements.md) |
| Policies | [policies.md](policies.md) (same as [Patchr/policy.md](Patchr/policy.md)) |
| Application description | [Patchr/app.md](Patchr/app.md) |
| Tools | [Patchr/tools.md](Patchr/tools.md) |
| Agents (prompts and rules) | [Patchr/agents/](Patchr/agents/) |
| Example episodes | [Patchr/episodes/](Patchr/episodes/) |
| Phase 1 traces and how to read them | [traces/README.md](traces/README.md), [traces/phase1/](traces/phase1/) |
| Source, setup and usage | [src/README.md](src/README.md), [src/patchr/](src/patchr/) |
| Tests | [tests/README.md](tests/README.md), [tests/](tests/) |

## Quick start

```bash
uv sync
uv run patchr run S1 --fake          # offline, no API key needed
cp .env.example .env                 # then set MODEL_ID and MODEL_API_KEY
uv run patchr run S1                 # real run with the configured model
uv run patchr replay traces/phase1/S1-20261028-194810.json
uv run pytest
```

See [src/README.md](src/README.md) for configuration details.
