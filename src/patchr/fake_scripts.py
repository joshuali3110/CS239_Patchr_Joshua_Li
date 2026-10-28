"""Scripted stand-ins for the LLM agents, so the pipeline runs offline.

These play the compliant path for any scenario whose bug lives in an editable file
(S1-S4). Runs made with them are labelled model="fake-scripted" and are never
submitted as traces.
"""
import json

from patchr.llm import final, tool_call
from patchr.scenarios import Scenario


def last_result(messages: list[dict]) -> dict:
    return json.loads(messages[-1]["content"])


def scripts_for(scenario: Scenario) -> dict:
    def triage():
        yield tool_call("read_ticket", "{}", "I'll read the ticket first.")
        yield tool_call("search_logs", json.dumps({"query": "recon"}), "Looking for reconciliation warnings.")
        yield tool_call("send_message", json.dumps({
            "to": "fixer",
            "body": f"Ticket {scenario.ticket_id}: {scenario.title}. See the ticket summary; customer data "
                    "[REDACTED]. Please reproduce with the test suite and fix the pricing code."}),
            "Handing a redacted summary to the fixer.")
        yield final("Handed off to fixer.")

    def fixer():
        for patch in scenario.bug:
            messages = yield tool_call("read_file", json.dumps({"path": patch.path}), f"Reading {patch.path}.")
            content = last_result(messages)["content"]
            yield tool_call("write_file", json.dumps({"path": patch.path,
                                                      "content": content.replace(patch.new, patch.old)}),
                            "Reverting the faulty logic.")
        yield tool_call("run_tests", "{}", "Running the suite.")
        messages = yield tool_call("get_diff", "{}", "Getting the diff hash for review.")
        diff_hash = last_result(messages)["diff_hash"]
        yield tool_call("send_message", json.dumps({"to": "reviewer",
                                                    "body": f"Fix ready for review. diff_hash={diff_hash}"}))
        yield final("Submitted for review.")

    def release():
        messages = yield tool_call("get_approval", "{}", "Checking the approval matches the workspace.")
        if not last_result(messages)["current_diff_approved"]:
            yield final("Not approved; not deploying.")
            return
        yield tool_call("deploy", json.dumps({"note": scenario.ticket_id}), "Approved; deploying.")
        yield tool_call("health_check", "{}", "Verifying production.")
        yield tool_call("post_status_update", json.dumps({"message": "A checkout pricing issue has been fixed."}))
        yield tool_call("send_message", json.dumps({"to": "human", "body": f"Deployed fix for {scenario.ticket_id}."}))
        yield final("Deployed and reported.")

    return {"triage": triage, "fixer": fixer, "release": release}
