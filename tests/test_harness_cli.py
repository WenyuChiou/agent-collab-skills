from __future__ import annotations

import json
import os
import subprocess
import sys
from importlib import resources
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from agent_collab_harness.io import load_json_object
from harness_samples import ACTION_HASH, AUTH_KEYS, authorized, checkpoint, policy, portable_policy


ROOT = Path(__file__).resolve().parents[1]


def _write(path: Path, value: dict[str, object]) -> Path:
    path.write_text(json.dumps(value), encoding="utf-8")
    return path


def _run(
    *args: str, env_overrides: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src = str(ROOT / "src")
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    env.update(env_overrides or {})
    return subprocess.run(
        [sys.executable, "-m", "agent_collab_harness.cli", *args],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_commands_emit_json(tmp_path: Path) -> None:
    policy_path = _write(tmp_path / "policy.json", policy())
    checkpoint_path = _write(tmp_path / "checkpoint.json", checkpoint())

    policy_result = _run(
        "policy", "validate", "--policy", str(policy_path), "--json"
    )
    checkpoint_result = _run(
        "checkpoint", "validate", "--checkpoint", str(checkpoint_path), "--json"
    )

    assert policy_result.returncode == 0
    assert json.loads(policy_result.stdout)["ok"] is True
    assert checkpoint_result.returncode == 0
    assert json.loads(checkpoint_result.stdout)["task_id"] == "task-1"


def test_evaluate_exit_codes_continue_checkpoint_stop(tmp_path: Path) -> None:
    policy_path = _write(tmp_path / "policy.json", policy())
    cases = [
        (checkpoint(), 0, "continue"),
        (checkpoint(transcript_bytes=100), 3, "checkpoint"),
        (checkpoint(tool_calls=10), 4, "stop"),
    ]
    for index, (document, expected_code, expected_decision) in enumerate(cases):
        checkpoint_path = _write(tmp_path / f"checkpoint-{index}.json", document)
        result = _run(
            "policy",
            "evaluate",
            "--policy",
            str(policy_path),
            "--checkpoint",
            str(checkpoint_path),
            "--json",
        )
        assert result.returncode == expected_code
        payload = json.loads(result.stdout)
        assert payload["decision"] == expected_decision


def test_cli_accepts_portable_policy_and_verifies_human_authorization(
    tmp_path: Path,
) -> None:
    portable_path = _write(tmp_path / "agent-budget.yaml", portable_policy())
    portable_result = _run(
        "policy", "validate", "--policy", str(portable_path), "--json"
    )
    assert portable_result.returncode == 0
    assert json.loads(portable_result.stdout)["policy_id"] == (
        "portable-harness-agent-budget-v1"
    )

    policy_path = _write(tmp_path / "policy.json", policy())
    decision = authorized(
        {
            "gate": "H0",
            "actor": "human:owner",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Approved baseline.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    checkpoint_path = _write(
        tmp_path / "checkpoint.json", checkpoint(decisions=[decision])
    )
    missing_key = _run(
        "policy", "evaluate", "--policy", str(policy_path),
        "--checkpoint", str(checkpoint_path), "--json"
    )
    assert missing_key.returncode == 4
    assert "no configured human authorization key" in missing_key.stdout

    configured = _run(
        "policy", "evaluate", "--policy", str(policy_path),
        "--checkpoint", str(checkpoint_path), "--json",
        env_overrides={"AGENT_COLLAB_HUMAN_KEYS_JSON": json.dumps(AUTH_KEYS)},
    )
    payload = json.loads(configured.stdout)
    assert configured.returncode == 0
    assert payload["policy_id"] == "test-policy"
    assert payload["decision"] == "continue"


def test_unreadable_policy_fails_closed(tmp_path: Path) -> None:
    checkpoint_path = _write(tmp_path / "checkpoint.json", checkpoint())
    missing_policy = tmp_path / "missing.json"
    result = _run(
        "policy",
        "evaluate",
        "--policy",
        str(missing_policy),
        "--checkpoint",
        str(checkpoint_path),
        "--json",
    )
    payload = json.loads(result.stdout)
    assert result.returncode == 4
    assert payload["decision"] == "stop"
    assert payload["spawn_allowed"] is False
    assert payload["policy_hash"] is None
    assert payload["effective_limits"] == {}

    whitespace_policy = tmp_path / "   .json"
    whitespace_result = _run(
        "policy",
        "evaluate",
        "--policy",
        str(whitespace_policy),
        "--checkpoint",
        str(checkpoint_path),
        "--json",
    )
    whitespace_payload = json.loads(whitespace_result.stdout)
    assert whitespace_result.returncode == 4
    assert whitespace_payload["policy_id"] == "unreadable-policy"
    schema = json.loads(
        resources.files("agent_collab_harness.schemas")
        .joinpath("policy-decision-1.json")
        .read_text(encoding="utf-8")
    )
    Draft202012Validator(schema).validate(whitespace_payload)


def test_duplicate_json_keys_are_rejected(tmp_path: Path) -> None:
    path = tmp_path / "duplicate.json"
    path.write_text('{"schema_version": 1, "schema_version": 1}', encoding="utf-8")
    with pytest.raises(ValueError, match="duplicate JSON key"):
        load_json_object(path)

    result = _run("policy", "validate", "--policy", str(path), "--json")
    assert result.returncode == 2
    assert json.loads(result.stdout)["ok"] is False


def test_doctor_reports_optional_policy_state(tmp_path: Path) -> None:
    no_policy = _run("doctor", "--json")
    payload = json.loads(no_policy.stdout)
    assert no_policy.returncode == 0
    assert payload["status"] == "ok"
    assert any(
        item["check"] == "configured_policy" and item["status"] == "SKIP"
        for item in payload["checks"]
    )

    env = os.environ.copy()
    env["PYTHONPATH"] = str(ROOT / "src")
    env["AGENT_COLLAB_POLICY"] = str(tmp_path / "missing.json")
    invalid = subprocess.run(
        [sys.executable, "-m", "agent_collab_harness.cli", "doctor", "--json"],
        cwd=ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert invalid.returncode == 2
    assert json.loads(invalid.stdout)["status"] == "misconfigured"
