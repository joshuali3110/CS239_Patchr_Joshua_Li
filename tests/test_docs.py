"""Keep the submission documents consistent with the code."""
import re
from pathlib import Path

from patchr.tools import ALLOWED_TOOLS, SCHEMAS

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "Patchr"


def test_policies_copy_matches():
    assert (ROOT / "policies.md").read_text() == (APP / "policy.md").read_text()


def test_policy_format():
    paragraphs = [p for p in (APP / "policy.md").read_text().split("\n\n") if p.strip()]
    assert len(paragraphs) >= 3
    for number, paragraph in enumerate(paragraphs, 1):
        assert paragraph.startswith(f"P{number}. ")


def test_agent_docs_contain_verbatim_prompts():
    for name in ("triage", "fixer", "release"):
        prompt = (ROOT / "src/patchr/agents/prompts" / f"{name}.md").read_text()
        assert prompt in (APP / "agents" / f"{name}.md").read_text(), f"{name}.md is out of date"


def test_p11_allowlists_match_code():
    p11 = next(p for p in (APP / "policy.md").read_text().split("\n\n") if p.startswith("P11. "))
    agents = {"Triage": "triage", "the Fixer": "fixer", "the Reviewer": "reviewer", "the Release agent": "release"}
    parsed = {}
    for phrase, key in agents.items():
        listed = re.search(rf"{phrase} may call ([^;.]+)", p11).group(1)
        parsed[key] = tuple(re.split(r",\s*|\s+and\s+", listed))
    assert parsed == ALLOWED_TOOLS


def test_allowlists_name_real_tools():
    for tools in ALLOWED_TOOLS.values():
        assert set(tools) <= set(SCHEMAS)


def test_agent_docs_state_their_allowlist():
    for agent, tools in ALLOWED_TOOLS.items():
        doc = (APP / "agents" / f"{agent}.md").read_text()
        capability = next(line for line in doc.splitlines() if line.startswith("| Capability |"))
        assert all(f"`{tool}`" in capability for tool in tools), agent


def test_tools_doc_lists_every_tool():
    lines = [line for line in (APP / "tools.md").read_text().splitlines() if line.strip()]
    names = [re.match(r"(\w+):", line).group(1) for line in lines]
    assert names == list(SCHEMAS)
