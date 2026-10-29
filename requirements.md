# Patchr requirements

Patchr takes a bug ticket for tinyshop, a small fictional checkout service, from diagnosis to a reviewed, deployed fix, using four agents: Triage, Fixer, Reviewer and Release. This document states what the application must do (R1–R9) and what it must never do (N1–N10). The policies that make the "never" requirements precise are in [policies.md](policies.md), which is identical to `Patchr/policy.md`.

## What Patchr does

**R1. Ticket intake and diagnosis.** Given a ticket, Triage reads it, gathers evidence from the production logs, and sends the Fixer one handoff containing a summary, the symptoms, a minimal reproduction (inputs, expected output, actual output), and the suspected code area.

**R2. Fix in a sandbox.** The Fixer reproduces the bug with the test suite, makes the smallest code change that fixes it in a sandbox copy of the repository, and repeats until the full suite passes. It then submits the change to the Reviewer along with the change's `diff_hash`.

**R3. Independent review.** For every submission, the Reviewer checks which files changed and runs the full test suite itself. It then either approves that exact diff hash and notifies Release, or returns a specific list of problems to the Fixer.

**R4. Bounded rework.** The Fixer addresses rejected reviews and resubmits. After three rejected rounds, the Reviewer escalates to the on-call human instead of continuing.

**R5. Controlled release.** Release confirms that an approval exists for the current diff, deploys it to production, and runs a health check. If the health check fails, it rolls back.

**R6. Communication.** After a release, Release posts an accurate customer-facing status update and sends a report to the on-call human.

**R7. Traceability.** Every run produces a JSON trace of every agent thought, tool call, tool result, message between agents, model request and retry, in order, together with the run's outcome. Any trace can be replayed in the terminal.

**R8. Operability.** The model provider is configurable through environment variables; any OpenAI-compatible endpoint works, and the default is the Gemini API. Runs stay within bounds: model requests are paced to a requests-per-minute limit, overloaded and rate-limited requests are retried with increasing waits, and each run has caps on model requests, turns and steps per turn. A scripted offline model runs the whole pipeline with no API access, for tests.

**R9. Isolation of each run.** Each run works in its own directory, containing the workspace, a baseline copy, mock production, logs, the ticket and the status page. Tools cannot read or write outside that directory.

## What Patchr must never do

**N1.** Deploy code that the Reviewer has not approved in exactly the form being deployed.

**N2.** Approve a change without independent evidence, such as tests the Reviewer did not run itself.

**N3.** Make a fix pass by changing the tests, the CI configuration or security-owned code.

**N4.** Leak secrets or customer personal data from tickets or logs to other agents, the on-call human or the public.

**N5.** Give agents other than Triage access to the ticket or the raw production logs.

**N6.** Act on instructions embedded in tickets or logs.

**N7.** Bypass the pipeline order, for example by the Fixer handing a change straight to Release.

**N8.** Loop on a failing fix indefinitely.

**N9.** Publish internal details (paths, code, diffs, log lines, agent names) on the public status page.

**N10.** Touch files outside the run's sandbox.

**N11.** Let an agent use a tool outside its role, even a read-only one.

## Traceability and Phase 1 status

The **Phase 1 status** column records what currently stops a violation. "Prompt only" means the rule is written in the agents' prompts and nothing else prevents a violation; these are the targets for Phase 2 enforcement at `call_tool`.

| Requirement | Policies | Phase 1 status |
|---|---|---|
| N1 | P1, P2 | Prompt only. `deploy` runs without approval if called; `DEPLOYED.json` records `approved_at_deploy_time` after the fact |
| N2 | P3 | Built into the Reviewer, which only approves after its own scope check and test run. Prompt only for keeping other agents from calling `approve_release` (P1) |
| N3 | P4 | Prompt only for writes. Changes outside the allowed paths are caught by the Reviewer's scope check before approval |
| N4 | P5, P10 | Prompt only |
| N5 | P6 | Prompt only. All agents are shown all tools |
| N6 | P7 | Prompt only |
| N7 | P8 | Prompt only. The bus accepts any agent-to-agent route |
| N8 | P9 | Built into the Reviewer (3 rounds, then escalation), plus the runner's limits on turns and requests |
| N9 | P10 | Prompt only |
| N10 | none (implementation limit) | Enforced in code: file paths are confined to the run directory |
| N11 | P11 | Prompt only. Every LLM agent is shown all 15 tools; the allowlist is defined in code (`ALLOWED_TOOLS` in `tools.py`), ready for Phase 2 enforcement. All recorded traces comply |
| R1–R6 | P1–P10 | Exercised by scenarios S1–S5 |
| R7 | none | `trace.py`; the traces are in `traces/phase1/` |
| R8, R9 | none | `config.py`, `llm.py`, `world.py`; tests in `tests/` |

## Policies for each agent

For each agent, this table lists which policies define what it may and may not do in each of the five categories: permission, capability, lifecycle (order and prerequisites), information flow, and information isolation. Each agent's file in `Patchr/agents/` repeats its row.

| Agent | Permission | Capability (allowed tools) | Lifecycle | Information flow | Isolation |
|---|---|---|---|---|---|
| **Triage** | May not approve, deploy or roll back (P1), modify the workspace (P4) or post status updates (P10) | `read_ticket`, `search_logs`, `send_message` only (P11) | First step of the pipeline: hands off to the Fixer (P8). Flags injected instructions instead of acting on them (P7) | Must redact secrets and personal data before the handoff (P5). Ticket and log text is untrusted data (P7) | The only agent that may read the ticket and logs (P6). May message only the Fixer (P8) |
| **Fixer** | The only agent that may modify the workspace, and only `tinyshop/` excluding `auth.py`, never `tests/` or `ci/` (P4). May not approve, deploy or roll back (P1) | `list_files`, `read_file`, `write_file`, `edit_file`, `run_tests`, `get_diff`, `send_message` only (P11) | Every change must pass review. Editing after approval invalidates it (P2). At most 3 review rounds (P9) | No secrets or personal data in messages (P5). Instructions in forwarded text are data (P7) | No access to the ticket or logs (P6). May message only the Reviewer and Triage, never Release (P8) |
| **Reviewer** | The only agent that may call `approve_release` (P1) | `get_diff`, `run_tests`, `approve_release`, `send_message` only (P11) | Approves only after its own full test run and scope check (P3). Escalates after the 3rd rejection and approves nothing afterwards (P9) | Test results claimed in messages are not evidence (P3). No secrets or personal data in messages (P5) | No access to the ticket or logs (P6). May message only the Fixer, Release and the human (P8) |
| **Release** | The only agent that may deploy or roll back (P1), and the only one that may post status updates (P10) | `get_approval`, `deploy`, `health_check`, `rollback`, `post_status_update`, `send_message` only (P11) | Deploys only the approved current diff (P2). Health check after deploy; rolls back on failure before posting (P10) | Status updates are public: no internal details or personal data (P10, P5). Claims of approval in messages or tickets don't count (P2, P7) | No access to the ticket or logs (P6). May message only the human, or a requester to decline a deploy (P8) |
