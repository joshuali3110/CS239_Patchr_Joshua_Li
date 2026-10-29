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

## Future direction: Patchr for any repository

Today the core (agents, message bus, scheduler, traces, the `call_tool` chokepoint and the Reviewer's logic) is already independent of tinyshop. The tinyshop-specific parts are the run environment (`world.py`), the scenarios, the tools' file-based behavior, the Reviewer's path constants, and the prompts' mentions of tinyshop.

To work with any repository, those parts would sit behind a few interfaces (ports), each with swappable implementations (adapters):

| Port | Responsibility | Local adapter (today) | GitHub adapter |
|---|---|---|---|
| **TicketSource** / `submit(ticket)` | Turn an outside request into a `Ticket` (id, title, body, reporter, trust level) | A ticket file, or the CLI | An issue event, via a GitHub App or Action |
| **Workspace** | Sandbox checkout; produce the diff and its hash | Copied folders | A git worktree on a branch; hash = commit SHA |
| **TestRunner** | Run the repo's tests and report results | pytest | The repo's configured command, reporting JUnit results |
| **ChangeSink** | Deliver the *approved* change | Copy into mock `prod/` | Push a branch and open or merge a PR |
| **Notifier** | Status updates and reports to humans | `outbox/status.md` | An issue or PR comment, Slack |
| **LogSource** (optional) | Production evidence for Triage | A log file | Datadog, CloudWatch, Sentry |

A GitHub integration is then one adapter package that implements several of these ports, plus an entry point that turns issue events into `submit()` calls. The core never imports anything GitHub-specific.

Design notes:
- **Policies come from the target repo's configuration** instead of code constants: editable and protected paths, test command, review-round limit, for example in a `.patchr.toml`, with protected paths optionally generated from `CODEOWNERS`.
- **Approving a diff hash (P2) maps onto GitHub's model:** PR approvals are tied to a commit SHA, and branch protection can dismiss stale approvals when new commits are pushed.
- **Capabilities become credentials:** the Fixer's token cannot merge, and only Release's can. P1 is then enforced by the platform as well as by `call_tool`.
- **Running untrusted code:** a real repository's tests need a container sandbox, and every outside input (issue text, comments) carries its author's trust level, which makes P7 central.
- **tinyshop and S1–S5 remain** as a repeatable test and evaluation set for any configuration, model or policy set.
