"""Catalog tests for agent-collab-skills.

Single-source marketplace + plugin bundle. These tests guard the
contract that:

1. The marketplace ships exactly one bundle plugin
   (agent-collab-workspace).
2. The bundle plugin's source is this same repo (url, .git, ref:main).
3. Every skill named in the marketplace has a SKILL.md file present
   under skills/<name>/.
4. Every SKILL.md has YAML frontmatter with name + description.
5. The 6 expected skills are present and named consistently.
"""

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

EXPECTED_SKILLS = [
    "agent-task-splitter",
    "agent-context-budget",
    "agent-output-reconciler",
    "agent-debate",
    "agent-shared-memory",
    "agent-acceptance-gate",
]


def test_marketplace_well_formed():
    """The .claude-plugin/marketplace.json file makes the catalog a
    Claude Code plugin marketplace. Single bundle plugin
    (agent-collab-workspace) sourced from this same repo."""
    marketplace_path = ROOT / ".claude-plugin" / "marketplace.json"
    assert marketplace_path.exists(), "missing .claude-plugin/marketplace.json"

    with marketplace_path.open(encoding="utf-8") as f:
        data = json.load(f)

    # Top-level required fields
    assert data.get("name") == "agent-collab-skills"
    assert "owner" in data and data["owner"].get("name")
    assert "metadata" in data and data["metadata"].get("version")
    assert "plugins" in data and isinstance(data["plugins"], list)
    assert len(data["plugins"]) == 1, "marketplace must ship exactly 1 bundle plugin"

    plugin = data["plugins"][0]
    assert plugin["name"] == "agent-collab-workspace"
    assert plugin["description"]
    assert plugin.get("category") == "productivity"
    assert plugin.get("homepage")
    assert plugin.get("version")

    src = plugin["source"]
    assert src["source"] == "url"
    assert src["url"].endswith(".git")
    assert "agent-collab-skills" in src["url"]
    assert src.get("ref") == "main"


def test_plugin_json_well_formed():
    """The .claude-plugin/plugin.json declares the bundle plugin
    metadata (consumed by Claude Code on install)."""
    plugin_path = ROOT / ".claude-plugin" / "plugin.json"
    assert plugin_path.exists(), "missing .claude-plugin/plugin.json"

    with plugin_path.open(encoding="utf-8") as f:
        data = json.load(f)

    assert data["name"] == "agent-collab-workspace"
    assert data["description"]
    assert data["version"]
    assert data.get("license") == "MIT"
    assert "keywords" in data and len(data["keywords"]) >= 3


def test_all_expected_skills_have_skill_md():
    """Every skill named in EXPECTED_SKILLS must have a SKILL.md
    file at skills/<name>/SKILL.md."""
    skills_dir = ROOT / "skills"
    assert skills_dir.exists(), "missing skills/ directory"

    for skill_name in EXPECTED_SKILLS:
        skill_md = skills_dir / skill_name / "SKILL.md"
        assert skill_md.exists(), f"missing skills/{skill_name}/SKILL.md"


def test_skill_md_has_valid_frontmatter():
    """Every SKILL.md must start with YAML frontmatter declaring
    name + description (which Claude Code's auto-discovery reads to
    decide whether to trigger the skill on a given user prompt)."""
    for skill_name in EXPECTED_SKILLS:
        skill_md = ROOT / "skills" / skill_name / "SKILL.md"
        text = skill_md.read_text(encoding="utf-8")

        # Must start with --- frontmatter block
        assert text.startswith("---\n"), f"{skill_name}: SKILL.md doesn't start with frontmatter"

        # Find closing --- line
        end = text.find("\n---\n", 4)
        assert end > 0, f"{skill_name}: SKILL.md frontmatter not closed"

        frontmatter = text[4:end]
        # name and description are required
        assert re.search(r"^name:\s*\S+", frontmatter, re.MULTILINE), (
            f"{skill_name}: SKILL.md frontmatter missing 'name'"
        )
        assert re.search(r"^description:\s*\S+", frontmatter, re.MULTILINE), (
            f"{skill_name}: SKILL.md frontmatter missing 'description'"
        )
        description = re.search(r"^description:\s*(.+)$", frontmatter, re.MULTILINE)
        assert description and description.group(1).startswith("Use when"), (
            f"{skill_name}: description must start with 'Use when'"
        )

        # name in frontmatter should match directory name
        m = re.search(r"^name:\s*(\S+)\s*$", frontmatter, re.MULTILINE)
        assert m, f"{skill_name}: couldn't parse name field"
        assert m.group(1) == skill_name, (
            f"{skill_name}: SKILL.md frontmatter name='{m.group(1)}' "
            f"doesn't match directory '{skill_name}'"
        )


def test_readme_lists_all_6_skills():
    """README must mention all 6 skills by name so users searching
    for a particular capability find their way in."""
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    for skill_name in EXPECTED_SKILLS:
        assert skill_name in readme, f"README missing reference to {skill_name}"


def test_plugin_versions_bumped_for_context_policy_release():
    """Adding agent-context-budget and context_policy is a public
    interface change, so plugin metadata should advertise 0.2.0."""
    plugin = json.loads((ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8"))
    marketplace = json.loads(
        (ROOT / ".claude-plugin" / "marketplace.json").read_text(encoding="utf-8")
    )

    assert plugin["version"] == "0.2.0"
    assert marketplace["metadata"]["version"] == "0.2.0"
    assert marketplace["plugins"][0]["version"] == "0.2.0"


def test_install_scripts_present():
    """install-all helper scripts exist for both shells."""
    assert (ROOT / "scripts" / "install-all.sh").exists()
    assert (ROOT / "scripts" / "install-all.ps1").exists()
