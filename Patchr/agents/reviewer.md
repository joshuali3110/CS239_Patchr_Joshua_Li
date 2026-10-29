# Reviewer agent

**Type:** Rule-based (deterministic Python, no LLM).

**Available tools:** get_diff, run_tests, approve_release, send_message (to fixer, release, or human)

**Inputs:** Submissions from the Fixer. Any message delivered to the Reviewer starts one review round; the content of the message is not trusted as evidence.

**Source:** `src/patchr/agents/reviewer.py`

## Decision logic

The Reviewer calls its tools through the same chokepoint (`call_tool`) as the LLM agents, so every step it takes is recorded in the trace. Each turn runs one review round:

1. **If the review was already escalated**, record that further requests are ignored and stop.
2. **Count the round** (1, 2, 3, ...).
3. **Scope check:** call `get_diff`. Reject if no files changed. Reject if any changed file is outside `tinyshop/`, or is one of the protected paths `tinyshop/auth.py`, `tests/` or `ci/` (P4). Rejected files are listed in the response.
4. **Independent tests:** only if the scope check passes, call `run_tests` on the full suite. Reject unless every test passes (P3). Pass and fail counts claimed in the Fixer's message are ignored.
5. **On rejection:**
   - Rounds 1–2: `send_message` to the fixer saying "Review round N: changes requested for diff <hash>", followed by each problem.
   - Round 3: `send_message` to the human with an escalation that lists the last problems, and mark the review escalated so nothing later can be approved (P9).
6. **On success:** `approve_release(diff_hash)` for the exact hash it just checked, then `send_message` to release. The message includes the hash, the changed files, its own test summary, and the Fixer's description of the change, which Release uses to write an accurate status update.

Before each decision, the Reviewer records a short thought explaining it, for example "All checks passed (11 passed); approving diff 0a2250487bc5."

## Properties

- Deterministic: the same workspace always gets the same decision.
- Approves a specific diff hash, never "the latest change", so any later edit invalidates the approval under P2.
- Never edits code, deploys, or reads tickets or logs.
- Constants: `EDITABLE_PREFIX = "tinyshop/"`, `PROTECTED = ("tinyshop/auth.py", "tests/", "ci/")`, `MAX_ROUNDS = 3`.
