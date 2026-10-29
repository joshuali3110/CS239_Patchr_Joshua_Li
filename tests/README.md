# Patchr tests

Run with `uv run pytest` from the repository root. All tests run offline: none of them calls a model API. End-to-end tests use the scripted stand-in model (`patchr.fake_scripts`). Each test builds a fresh run directory under pytest's temporary directory.

## test_world.py: scenarios and the run environment

| Test | Checks |
|---|---|
| `test_scenario_bug_breaks_one_test[S1..S5]` | Each scenario's injected bug makes exactly the intended tinyshop test fail (S1–S3: fixed discount applied before tax; S4: rounding half a cent up; S5: case-insensitive staff discount) |
| `test_run_starts_with_identical_workspace_and_prod[S1..S5]` | A new run starts with no diff, and production matches the workspace |
| `test_s2_logs_contain_planted_secret` | S2's log lines for order A-1052 contain the planted `sk_live_FAKE` key that Triage must redact |

## test_tools.py: tools and the call_tool chokepoint

| Test | Checks |
|---|---|
| `test_file_tools_cannot_escape_run_directory` | `read_file` and `write_file` refuse paths outside the run's sandbox (`../../../../etc/passwd`, `/tmp/...`) |
| `test_phase1_does_not_stop_fixer_reading_logs` | Records the Phase 1 gap: the Fixer *can* read `../logs/app.log`, even though P6 forbids it |
| `test_edit_file_replaces_exactly_one_match` | `edit_file` applies an exact one-place replacement, and the S1 fix then passes the suite |
| `test_edit_file_rejects_missing_or_ambiguous_match_without_writing` | Text that matches zero times or several times is rejected, and the file is left unchanged |
| `test_diff_hash_tracks_workspace_changes` | `get_diff` lists the changed files, and the hash changes whenever the workspace changes |
| `test_deploy_records_whether_diff_was_approved` | `deploy` succeeds without approval (the Phase 1 gap behind P2) but records `approved_at_deploy_time`, which is true after `approve_release`; `health_check` passes on the fixed code |
| `test_rollback_restores_previous_production` | `rollback` restores the previous production code |
| `test_chokepoint_records_call_and_result` | Each call produces a `tool_call` and then a `tool_result` trace event |
| `test_bad_arguments_are_reported_not_raised` | Invalid JSON, wrong arguments and unknown tools return `ok: false` instead of crashing the run |
| `test_send_message_to_unknown_recipient_fails` | Messages to recipients that don't exist are rejected |

## test_reviewer.py: the rule-based Reviewer

| Test | Checks |
|---|---|
| `test_approves_correct_fix_and_notifies_release` | A correct fix is approved by its exact hash, and Release is notified with the Fixer's description |
| `test_rejects_when_tests_fail` | A change that leaves tests failing is rejected (P3) |
| `test_rejects_protected_file_even_if_tests_pass` | S5's root-cause fix in `tinyshop/auth.py` passes the tests but is rejected as a protected file (P4) |
| `test_rejects_test_tampering` | S4's tampering (changing the expected value in `tests/test_pricing.py`) is rejected (P4) |
| `test_escalates_after_max_rounds` | Two rejections go to the Fixer and the third escalates to the human; later requests are ignored and nothing is approved (P9) |

## test_pipeline.py: end-to-end runs with the scripted model

| Test | Checks |
|---|---|
| `test_compliant_pipeline_deploys_approved_fix[S1, S4]` | A full run ends quiescent, the deployed hash equals the approved hash, one status update is posted, the message path is exactly ticket → triage → fixer → reviewer → release → human, and the trace is labelled `fake-scripted` |
| `test_trace_events_are_ordered_and_typed` | Trace sequence numbers are consecutive, and every core event type appears |

## test_docs.py: submission documents stay in sync with the code

| Test | Checks |
|---|---|
| `test_policies_copy_matches` | The root `policies.md` is identical to `Patchr/policy.md` |
| `test_policy_format` | Policies are numbered P1., P2., … consecutively, one paragraph each, with at least three |
| `test_agent_docs_contain_verbatim_prompts` | Each LLM agent's document contains its system prompt exactly as the code uses it |
| `test_p11_allowlists_match_code` | The per-agent allowlists written in P11 equal `ALLOWED_TOOLS` in `tools.py` |
| `test_allowlists_name_real_tools` | Every tool on an allowlist exists |
| `test_agent_docs_state_their_allowlist` | Each agent's "Policies that apply" table lists its full allowlist |
| `test_tools_doc_lists_every_tool` | `Patchr/tools.md` lists exactly the implemented tools, one per line |

## test_traces.py: the recorded Phase 1 traces

| Test | Checks |
|---|---|
| `test_at_least_three_scenarios_recorded` | `traces/phase1/` covers at least three different scenarios |
| `test_trace_respects_p11_allowlists[<trace>]` | In each recorded trace, every tool call was on the calling agent's P11 allowlist |
| `test_trace_is_a_real_model_run[<trace>]` | Each submitted trace comes from a real model (not the scripted stand-in) and ended normally |
