"""Keep the submission documents consistent with the code."""
import re
from pathlib import Path

from patchr.tools import SCHEMAS

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


def test_tools_doc_lists_every_tool():
    lines = [line for line in (APP / "tools.md").read_text().splitlines() if line.strip()]
    names = [re.match(r"(\w+):", line).group(1) for line in lines]
    assert names == list(SCHEMAS)
