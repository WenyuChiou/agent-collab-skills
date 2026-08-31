"""Provider-neutral workflow, scratch, and policy-source invariants."""

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
ACTIVE_SURFACES = [
    ROOT / ".claude-plugin" / "plugin.json",
    ROOT / ".claude-plugin" / "marketplace.json",
    ROOT / ".github" / "PULL_REQUEST_TEMPLATE.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "skill-request.md",
    ROOT / ".github" / "ISSUE_TEMPLATE" / "bug-report.md",
    ROOT / "scripts" / "install-all.sh",
    ROOT / "scripts" / "install-all.ps1",
    ROOT / "examples" / "plan.yml.sample",
    ROOT / "examples" / "reconciliation_001.md.sample",
    ROOT / "examples" / "acceptance_001.md.sample",
]


def test_plan_sample_uses_roles_and_policy_checkpoint_references():
    plan = yaml.safe_load((ROOT / "examples" / "plan.yml.sample").read_text())
    assert plan["schema_version"] == 2
    assert plan["policy_ref"]
    assert plan["checkpoint_ref"]
    assert "budget" not in plan and "context_policy" not in plan
    assert {task["role"] for task in plan["tasks"]} <= {
        "primary-agent",
        "delegated-executor",
        "reviewer",
        "synthesizer",
    }
    assert all(task["task_packet"].startswith(".ai/task_") for task in plan["tasks"])
    assert all("agent" not in task for task in plan["tasks"])


def test_active_surfaces_do_not_route_to_archived_provider():
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8").lower()
        assert "gemini" not in text, path
        for stale_count in ("5" + " skills", "6" + " skills", "6th" + " skill"):
            assert stale_count not in text, f"{path}: {stale_count}"


def test_skill_contracts_use_canonical_policy_without_numeric_defaults():
    numeric_default_patterns = (
        "default 250",
        "default 50",
        "max 3 rounds",
        "8 kb",
        "200-400 words",
    )
    for skill in (ROOT / "skills").glob("*/SKILL.md"):
        text = skill.read_text(encoding="utf-8").lower()
        for pattern in numeric_default_patterns:
            assert pattern not in text, f"{skill}: duplicated policy value {pattern}"

    budget = (ROOT / "skills" / "agent-context-budget" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    par = (ROOT / "skills" / "agent-plan-act-reflect" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "agent-collab policy evaluate" in budget
    assert "agent-collab policy evaluate" in par


def test_scratch_and_memory_contracts_are_explicit():
    splitter = (ROOT / "skills" / "agent-task-splitter" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    memory = (ROOT / "skills" / "agent-shared-memory" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "scratch" in splitter.lower()
    assert "proposal" in memory.lower()
    assert "explicit human" in memory.lower()
    assert "never edits an existing event" in memory.lower()


def test_acceptance_presets_parse_and_are_discoverable():
    skill_text = (
        ROOT / "skills" / "agent-acceptance-gate" / "SKILL.md"
    ).read_text(encoding="utf-8")
    names = {
        "multi-locale-mirror-sync",
        "catalog-entry-add",
        "fact-check-frontier-models",
    }
    for name in names:
        path = ROOT / "skills" / "agent-acceptance-gate" / "presets" / f"{name}.yml"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["preset_name"] == name
        assert data["checks"]
        assert name in skill_text

    locale_preset = yaml.safe_load(
        (
            ROOT
            / "skills"
            / "agent-acceptance-gate"
            / "presets"
            / "multi-locale-mirror-sync.yml"
        ).read_text(encoding="utf-8")
    )
    assert locale_preset["invocation_param"]["files"]["required"] is True
    check_ids = {check["id"] for check in locale_preset["checks"]}
    assert {
        "h2_parity",
        "table_structure_parity",
        "mermaid_node_parity",
        "mermaid_edge_parity",
        "internal_link_resolution",
        "markdown_anchor_resolution",
        "locale_profile",
    } <= check_ids
    assert all(check.get("type") != "command" for check in locale_preset["checks"])
    assert "command_param" not in locale_preset


def test_failure_history_is_retained_as_history():
    history = (ROOT / "docs" / "observed-failure-modes.md").read_text(
        encoding="utf-8"
    )
    for failure_id in range(1, 15):
        assert f"## F{failure_id}." in history
