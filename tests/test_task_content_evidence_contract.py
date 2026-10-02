"""Specification fixtures, not a production acceptance/preset engine.

Agent Collab's presets are declarative. These tests reproduce the historical
mtime predicate on real files and pin the safer evidence-review contract.
They do not demonstrate a model run, semantic correctness, or cost savings.
"""

import hashlib
import os
from copy import deepcopy
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
PRESET = ROOT / "skills/agent-acceptance-gate/presets/multi-locale-mirror-sync.yml"


def _checks():
    return {item["id"]: item for item in yaml.safe_load(
        PRESET.read_text(encoding="utf-8"))["checks"]}


def test_contract_reads_ignore_locale_default_encoding(monkeypatch):
    read_text = Path.read_text

    def require_utf8(path, encoding=None, errors=None):
        # Windows cp1252 cannot decode the preset's UTF-8 Chinese text. Do not
        # let an environment-wide UTF-8 mode mask an implicit-encoding read.
        assert encoding == "utf-8"
        return read_text(path, encoding=encoding, errors=errors)

    monkeypatch.setattr(Path, "read_text", require_utf8)
    assert "task_content_evidence" in _checks()


def _digest(text):
    return hashlib.sha256(text.encode()).hexdigest()


def _files(tmp_path, before, after, target_time):
    brief = tmp_path / "brief.md"
    target = tmp_path / "README.md"
    brief.write_text("Sync the target if needed.", encoding="utf-8")
    target.write_text(before, encoding="utf-8")
    baseline = hashlib.sha256(target.read_bytes()).hexdigest()
    target.write_text(after, encoding="utf-8")
    os.utime(brief, (1000, 1000))
    os.utime(target, (target_time, target_time))
    return brief, target, baseline


def test_declared_mtime_predicate_accepts_touch_without_content_edit(tmp_path):
    brief, target, before = _files(tmp_path, "Already correct", "Already correct", 1001)
    assert target.stat().st_mtime > brief.stat().st_mtime
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_declared_mtime_predicate_rejects_real_edit_with_preserved_timestamp(tmp_path):
    brief, target, before = _files(tmp_path, "Old content", "Correct content", 1000)
    assert not target.stat().st_mtime > brief.stat().st_mtime
    assert hashlib.sha256(target.read_bytes()).hexdigest() != before


def test_declared_mtime_predicate_rejects_legitimate_idempotent_noop(tmp_path):
    brief, target, before = _files(tmp_path, "Already correct", "Already correct", 999)
    assert not target.stat().st_mtime > brief.stat().st_mtime
    assert hashlib.sha256(target.read_bytes()).hexdigest() == before


def test_preset_retains_legacy_mtime_as_advisory_only():
    data = yaml.safe_load(PRESET.read_text(encoding="utf-8"))
    assert "brief_file" in data["invocation_param"]
    mtime = _checks()["post_brief_mtime_check"]
    assert mtime["type"] == "file_mtime_after"
    assert mtime["severity"] == "warn"
    assert "not proof" in mtime["note"].lower()


def test_preset_requires_explicit_content_evidence_review():
    check = _checks()["task_content_evidence"]
    assert check["type"] == "manual_check"
    assert check["severity"] == "fail"
    assert check["reference_file_param"] == "brief_file"
    assert check["skip_when_empty"] is True
    text = " ".join(check["requirements"]).lower()
    for phrase in (
        "run", "task", "baseline", "candidate", "scope", "unchanged",
        "criterion", "missing", "stale", "not semantic",
    ):
        assert phrase in text


@pytest.mark.parametrize("skill", [
    "agent-task-splitter", "agent-output-reconciler", "agent-acceptance-gate",
])
def test_active_skills_link_the_shared_evidence_contract(skill):
    text = (ROOT / "skills" / skill / "SKILL.md").read_text(encoding="utf-8")
    assert "docs/task-content-evidence.md" in text


def _review_fixture(evidence, *, actual_after, baseline, run="R1", task="T1"):
    """Illustrative review of the shared contract; no public runtime API.

    The caller supplies independently observed baseline/candidate data. A
    worker-authored hash alone is deliberately insufficient in this fixture.
    Exact paths here model a bounded task, not production glob semantics.
    """
    if evidence.get("run") != run or evidence.get("task") != task:
        return False
    if evidence.get("status") != "success":
        return False
    if evidence.get("before") != baseline or evidence.get("after") != actual_after:
        return False
    changed = {p for p in baseline.keys() | actual_after.keys()
               if baseline.get(p) != actual_after.get(p)}
    if changed - set(evidence.get("allowed_paths", [])):
        return False
    if set(evidence.get("changed_paths", [])) != changed:
        return False
    if not evidence.get("criterion_evidence"):
        return False
    if not changed:
        return (evidence.get("change_expectation") == "unchanged_allowed"
                and bool(evidence.get("unchanged_reason")))
    return True


def _evidence():
    return {
        "run": "R1", "task": "T1", "status": "success",
        "before": {"README.md": _digest("old")},
        "after": {"README.md": _digest("correct")},
        "allowed_paths": ["README.md"], "changed_paths": ["README.md"],
        "change_expectation": "change_required", "unchanged_reason": None,
        "criterion_evidence": ["review:current-candidate"],
    }


def test_specification_fixture_accepts_scoped_edit_with_criterion_evidence():
    e = _evidence()
    assert _review_fixture(e, actual_after=e["after"], baseline=e["before"])


@pytest.mark.parametrize("mutation", [
    {"run": "stale-run"}, {"task": "wrong-task"}, {"status": "error"},
    {"status": "cancelled"}, {"status": "declined"}, {"status": "degraded"},
    {"after": {"README.md": _digest("stale-candidate")}},
    {"before": {"README.md": _digest("wrong-baseline")}},
    {"allowed_paths": []}, {"changed_paths": []}, {"criterion_evidence": []},
])
def test_specification_fixture_rejects_missing_or_wrong_bound_evidence(mutation):
    e = _evidence()
    actual_after, baseline = deepcopy(e["after"]), deepcopy(e["before"])
    e.update(mutation)
    assert not _review_fixture(e, actual_after=actual_after, baseline=baseline)


def test_specification_fixture_rejects_unreported_out_of_scope_delta():
    e = _evidence()
    actual_after = {**e["after"], "mirror.en.md": _digest("unrequested attribution")}
    assert not _review_fixture(e, actual_after=actual_after, baseline=e["before"])


def test_specification_fixture_accepts_explicit_verified_unchanged_result():
    e = _evidence()
    e.update(after=e["before"].copy(), changed_paths=[],
             change_expectation="unchanged_allowed",
             unchanged_reason="The target already meets the current criterion.")
    assert _review_fixture(e, actual_after=e["after"], baseline=e["before"])
    e["change_expectation"] = "change_required"
    assert not _review_fixture(e, actual_after=e["after"], baseline=e["before"])


def test_content_hashes_do_not_prove_semantic_correctness():
    e = _evidence()
    e["after"] = {"README.md": _digest("Incorrect rewrite, different bytes")}
    # Hash/change evidence establishes byte provenance only. The named reviewer
    # still has to check the criterion; the fixture cannot decide its truth.
    assert _review_fixture(e, actual_after=e["after"], baseline=e["before"])
