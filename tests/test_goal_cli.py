import hashlib
import json

from agent_collab_harness.goals import goal_policy
from harness_samples import checkpoint, policy
from test_harness_cli import _run, _write


def test_migrate_advance_cli_is_explicit_and_idempotent(tmp_path):
    source = _write(
        tmp_path / "old.json", checkpoint(cycle=3, evidence_refs=["test:pass"])
    )
    original = source.read_bytes()
    p = _write(tmp_path / "policy.json", goal_policy(policy()))
    meta = _write(
        tmp_path / "metadata.json", {"goal_id": "goal", "next_step": "review"}
    )
    target = tmp_path / "new.json"
    result = _run(
        "checkpoint",
        "migrate",
        "--checkpoint",
        str(source),
        "--policy",
        str(p),
        "--metadata",
        str(meta),
        "--output",
        str(target),
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert source.read_bytes() == original
    digest = hashlib.sha256(target.read_bytes()).hexdigest()
    args = (
        "checkpoint",
        "advance",
        "--checkpoint",
        str(target),
        "--policy",
        str(p),
        "--request-id",
        "next",
        "--expected-sha256",
        digest,
    )
    first = _run(*args)
    assert first.returncode == 0, first.stdout + first.stderr
    saved = target.read_bytes()
    duplicate = _run(*args)
    assert duplicate.returncode == 0
    assert target.read_bytes() == saved
    assert json.loads(first.stdout)["slice_id"] == 1


def test_cli_does_not_overwrite_migration_destination(tmp_path):
    source = _write(tmp_path / "old.json", checkpoint())
    p = _write(tmp_path / "policy.json", goal_policy(policy()))
    meta = _write(
        tmp_path / "metadata.json", {"goal_id": "goal", "next_step": "review"}
    )
    target = _write(tmp_path / "target.json", {"user": "data"})
    result = _run(
        "checkpoint",
        "migrate",
        "--checkpoint",
        str(source),
        "--policy",
        str(p),
        "--metadata",
        str(meta),
        "--output",
        str(target),
    )
    assert result.returncode == 2
    assert json.loads(target.read_text()) == {"user": "data"}
