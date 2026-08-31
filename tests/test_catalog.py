"""Plugin and skill discovery contract tests."""

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VERSION = "0.4.0"
EXPECTED_SKILLS = {
    "agent-acceptance-gate",
    "agent-context-budget",
    "agent-debate",
    "agent-output-reconciler",
    "agent-plan-act-reflect",
    "agent-shared-memory",
    "agent-task-splitter",
}


def _frontmatter(text: str) -> str:
    assert text.startswith("---\n")
    end = text.find("\n---\n", 4)
    assert end > 0
    return text[4:end]


def test_exactly_seven_active_skills_have_valid_frontmatter():
    skill_dirs = {
        path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
    }
    assert skill_dirs == EXPECTED_SKILLS

    for name in EXPECTED_SKILLS:
        frontmatter = _frontmatter(
            (ROOT / "skills" / name / "SKILL.md").read_text(encoding="utf-8")
        )
        parsed_name = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        description = re.search(
            r"^description:\s*(.+)$", frontmatter, re.MULTILINE
        )
        assert parsed_name and parsed_name.group(1) == name
        assert description and description.group(1).startswith("Use when")


def test_manifests_are_synchronized_and_provider_neutral():
    plugin = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    marketplace = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    entry = marketplace["plugins"][0]

    assert plugin["name"] == entry["name"] == "agent-collab-workspace"
    assert plugin["version"] == marketplace["metadata"]["version"] == VERSION
    assert entry["version"] == VERSION
    assert entry["source"]["url"].endswith("agent-collab-skills.git")
    assert entry["source"]["ref"] == "main"

    active_text = json.dumps([plugin, marketplace], ensure_ascii=False).lower()
    assert "7 provider-neutral skills" in active_text or "7 multi-agent" in active_text
    assert "gemini" not in active_text


def test_readmes_and_installers_list_every_active_skill():
    surfaces = [
        ROOT / "README.md",
        ROOT / "README.zh-TW.md",
        ROOT / "scripts" / "install-all.sh",
        ROOT / "scripts" / "install-all.ps1",
    ]
    for path in surfaces:
        text = path.read_text(encoding="utf-8")
        for name in EXPECTED_SKILLS:
            assert name in text, f"{path.name} is missing {name}"


def test_marketplace_contains_one_source_repo_bundle():
    data = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["name"] == "agent-collab-skills"
    assert len(data["plugins"]) == 1
    assert data["plugins"][0]["source"]["source"] == "url"
