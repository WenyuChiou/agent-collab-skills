"""Bilingual entry-point and active internal-link checks."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = {
    "agent-task-splitter",
    "agent-context-budget",
    "agent-plan-act-reflect",
    "agent-output-reconciler",
    "agent-debate",
    "agent-shared-memory",
    "agent-acceptance-gate",
}
ROLES = {"primary-agent", "delegated-executor", "reviewer", "synthesizer"}
CLI_COMMANDS = {
    "agent-collab policy validate",
    "agent-collab checkpoint validate",
    "agent-collab policy evaluate",
    "agent-collab doctor",
}


def _mermaid_node_ids(text: str) -> set[str]:
    block = re.search(r"```mermaid\n(.*?)\n```", text, re.DOTALL)
    assert block
    return set(re.findall(r"^\s*([A-Z])\[", block.group(1), re.MULTILINE))


def test_english_and_traditional_chinese_entry_points_have_contract_parity():
    english = (ROOT / "README.md").read_text(encoding="utf-8")
    chinese = (ROOT / "README.zh-TW.md").read_text(encoding="utf-8")

    for term in SKILLS | ROLES | CLI_COMMANDS:
        assert term in english
        assert term in chinese
    assert len(re.findall(r"^## ", english, re.MULTILINE)) == len(
        re.findall(r"^## ", chinese, re.MULTILINE)
    )
    assert english.count("-->") == chinese.count("-->")
    assert _mermaid_node_ids(english) == _mermaid_node_ids(chinese)
    assert "繁體中文" in chinese
    assert "人類決策" in chinese
    assert "不可變" in chinese


def test_active_relative_markdown_links_resolve():
    active_files = [
        ROOT / "README.md",
        ROOT / "README.zh-TW.md",
        ROOT / "CONTRIBUTING.md",
        ROOT / ".claude-plugin" / "README.md",
        ROOT / "docs" / "public-harness-contract.md",
        ROOT / "docs" / "migration-0.4.md",
        ROOT / "docs" / "context-pressure-scenarios.md",
        ROOT / "docs" / "agentmemory-integration.md",
        ROOT / "docs" / "example-walkthrough.md",
        ROOT / "docs" / "scenario-to-skill.md",
        ROOT / "docs" / "when-to-invoke.md",
        *sorted((ROOT / "skills").glob("*/SKILL.md")),
    ]
    pattern = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")
    failures: list[str] = []
    for source in active_files:
        for raw_target in pattern.findall(source.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0].strip()
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            resolved = (source.parent / target).resolve()
            if not resolved.exists():
                failures.append(f"{source.relative_to(ROOT)} -> {raw_target}")
    assert failures == []
