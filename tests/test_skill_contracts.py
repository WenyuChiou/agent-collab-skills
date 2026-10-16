"""scripts/check_skill_contracts.py passes on the repo and catches drift."""

import importlib.util
import shutil
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture()
def checker():
    spec = importlib.util.spec_from_file_location(
        "check_skill_contracts", ROOT / "scripts" / "check_skill_contracts.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def skills_copy(tmp_path, checker, monkeypatch):
    target = tmp_path / "skills"
    shutil.copytree(ROOT / "skills", target)
    monkeypatch.setattr(checker, "SKILLS", target)
    monkeypatch.setattr(checker, "ROOT", tmp_path)
    return target


def _rewrite(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    assert old in text
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def test_repository_skills_pass(checker):
    assert checker.check() == []


def test_gate_description_must_keep_preset_trigger(checker, skills_copy):
    _rewrite(
        skills_copy / "agent-acceptance-gate" / "SKILL.md",
        "two or more locale variants of one file stem, adds",
        "two or more variants of one file stem, adds",
    )
    errors = checker.check()
    assert any("multi-locale-mirror-sync.yml" in e and "description" in e for e in errors)


def test_preset_file_without_table_row_fails(checker, skills_copy):
    preset = skills_copy / "agent-acceptance-gate" / "presets" / "catalog-entry-add.yml"
    shutil.copy(preset, preset.with_name("new-preset.yml"))
    errors = checker.check()
    assert any("preset table" in e for e in errors)


def test_stub_must_name_removal_release_and_target(checker, skills_copy):
    _rewrite(
        skills_copy / "agent-shared-memory" / "SKILL.md",
        "removed in 0.7.0",
        "removed later",
    )
    errors = checker.check()
    assert any("agent-shared-memory" in e and "0.7.0" in e for e in errors)


def test_unquoted_colon_in_description_fails(checker, skills_copy):
    _rewrite(
        skills_copy / "agent-debate" / "SKILL.md",
        "and you are about to pick one.",
        "and you are about to pick one: now.",
    )
    errors = checker.check()
    assert any("agent-debate" in e and "YAML" in e for e in errors)


@pytest.mark.parametrize("phrase", ["the user asks", "a user asks", "a user requests"])
def test_user_request_only_description_fails(checker, skills_copy, phrase):
    _rewrite(
        skills_copy / "agent-task-splitter" / "SKILL.md",
        "description: Use when about to run two or more subagents",
        f"description: Use when {phrase} to run two or more subagents",
    )
    errors = checker.check()
    assert any("agent-task-splitter" in e and "user request" in e for e in errors)


def test_terms_match_whole_words_only(checker, skills_copy):
    _rewrite(
        skills_copy / "agent-acceptance-gate" / "SKILL.md",
        "returns PASS, CONDITIONAL PASS, or FAIL with evidence.",
        "returns a bypass note or a failure note with evidence.",
    )
    errors = checker.check()
    assert any("'PASS'" in e for e in errors)
    assert any("'FAIL'" in e for e in errors)


def test_yaml_comment_marker_in_description_fails(checker, skills_copy):
    _rewrite(
        skills_copy / "agent-debate" / "SKILL.md",
        "and you are about to pick one.",
        "and you are about to pick one #now.",
    )
    errors = checker.check()
    assert any("agent-debate" in e and "comment" in e for e in errors)
