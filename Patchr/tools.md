read_ticket: takes no input; reads the run's ticket file (tickets/<id>.md) and returns {ticket_id, text}.
search_logs: takes query (string) and optional max_results (integer, default 20); searches the production log (logs/app.log) for lines containing query, ignoring case, and returns {query, total_matches, lines}, where each line is prefixed with its line number.
list_files: takes optional path (string, default "."), a directory relative to the workspace root; returns {path, files}, the files under it, recursively, excluding caches.
read_file: takes path (string), relative to the workspace root and confined to the run's sandbox directory; returns {path, content} with the file's text.
write_file: takes path (string) and content (string); creates or overwrites that file in the workspace with the complete content and returns {path, bytes_written, created}.
edit_file: takes path (string), old (string) and new (string); replaces the single exact occurrence of old in the file with new and returns {path, replaced}; returns an error and writes nothing if old appears zero times or more than once.
run_tests: takes optional keyword (string, passed to pytest -k); runs the tinyshop test suite in the workspace and returns {passed, failed, errors, all_passed, failures, summary, output_tail}.
get_diff: takes no input; compares the workspace with the code as it was when the ticket arrived and returns {diff_hash, changed_files, diff}, where diff_hash is a 12-character hash identifying that exact change (null if nothing changed).
approve_release: takes diff_hash (string) and optional note (string); records an approval of that diff for release and returns {recorded, diff_hash, approved_by, note, matches_current_workspace}.
get_approval: takes no input; returns {current_diff_hash, approvals, current_diff_approved}, where current_diff_approved is true if an approval exists for the current workspace diff.
deploy: takes optional note (string); copies the workspace into the mock production directory (prod/), keeps the previous version for rollback, writes prod/DEPLOYED.json, and returns {deployed, diff_hash, deployed_by, note, deployed_at, approved_at_deploy_time}.
health_check: takes no input; runs the test suite against production and returns {healthy, passed, failed, failures}.
rollback: takes no input; restores the previous production version and returns {rolled_back}; returns an error if there is no previous version.
post_status_update: takes message (string); appends it, with a timestamp, to the public status page (outbox/status.md) and returns {posted, public_url}.
send_message: takes to (one of triage, fixer, reviewer, release, human) and body (string); delivers the message to that agent's inbox (messages to human are recorded but not acted on) and returns {delivered, msg_id, to}.
