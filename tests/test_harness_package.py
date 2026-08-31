from __future__ import annotations

import json
import re
from importlib import resources
from pathlib import Path

import agent_collab_harness
import pytest
from jsonschema import Draft202012Validator
from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.validation import (
    CHECKPOINT_KEYS,
    CHECKPOINT_REQUIRED_KEYS,
    CHECKPOINT_STATUSES,
    LIMIT_KEYS,
    validate_checkpoint,
    validate_policy,
)
from harness_samples import ACTION_HASH, authorized, checkpoint, policy


ROOT = Path(__file__).resolve().parents[1]


def test_public_exports_and_version() -> None:
    assert agent_collab_harness.__version__ == "0.4.0"
    assert callable(agent_collab_harness.evaluate_policy)
    assert callable(agent_collab_harness.sign_human_record)
    assert callable(agent_collab_harness.validate_checkpoint)
    assert callable(agent_collab_harness.validate_policy)


def test_packaged_schemas_are_json_objects() -> None:
    schema_root = resources.files("agent_collab_harness.schemas")
    for name in (
        "agent-policy-1.json",
        "task-checkpoint-1.json",
        "policy-decision-1.json",
    ):
        with schema_root.joinpath(name).open("r", encoding="utf-8") as handle:
            schema = json.load(handle)
        assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
        assert schema["type"] == "object"


def test_reference_schemas_match_programmatic_validator_fields() -> None:
    schema_root = resources.files("agent_collab_harness.schemas")
    policy_schema = json.loads(
        schema_root.joinpath("agent-policy-1.json").read_text(encoding="utf-8")
    )
    checkpoint_schema = json.loads(
        schema_root.joinpath("task-checkpoint-1.json").read_text(encoding="utf-8")
    )
    assert set(policy_schema["$defs"]["publicLimits"]["properties"]) == LIMIT_KEYS
    assert set(policy_schema["$defs"]["publicLimits"]["required"]) == LIMIT_KEYS
    assert set(checkpoint_schema["properties"]) == CHECKPOINT_KEYS
    assert set(checkpoint_schema["required"]) == CHECKPOINT_REQUIRED_KEYS
    assert set(checkpoint_schema["properties"]["status"]["enum"]) == CHECKPOINT_STATUSES


def test_package_plugin_and_source_versions_are_synchronized() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    project_version = re.search(
        r'^version\s*=\s*"([^"]+)"$', pyproject, re.MULTILINE
    )
    plugin = json.loads(
        (ROOT / ".claude-plugin" / "plugin.json").read_text(encoding="utf-8")
    )
    assert project_version
    assert project_version.group(1) == plugin["version"] == agent_collab_harness.__version__


def test_public_example_documents_validate() -> None:
    policy = json.loads((ROOT / "examples" / "policy.json.sample").read_text())
    checkpoint = json.loads(
        (ROOT / "examples" / "checkpoint.json.sample").read_text()
    )
    validate_policy(policy)
    validate_checkpoint(checkpoint)


def test_structural_schemas_and_semantic_validators_have_documented_boundary() -> None:
    schema_root = resources.files("agent_collab_harness.schemas")
    policy_schema = json.loads(
        schema_root.joinpath("agent-policy-1.json").read_text(encoding="utf-8")
    )
    checkpoint_schema = json.loads(
        schema_root.joinpath("task-checkpoint-1.json").read_text(encoding="utf-8")
    )
    Draft202012Validator.check_schema(policy_schema)
    Draft202012Validator.check_schema(checkpoint_schema)
    policy_validator = Draft202012Validator(policy_schema)
    checkpoint_validator = Draft202012Validator(checkpoint_schema)

    whitespace_id = policy()
    whitespace_id["policy_id"] = "   "
    assert list(policy_validator.iter_errors(whitespace_id))
    with pytest.raises(HarnessValidationError):
        validate_policy(whitespace_id)

    uppercase_hash = checkpoint(
        decisions=[
            authorized({
                "gate": "H4",
                "actor": "human:owner",
                "decision": "approve",
                "timestamp": "2026-08-31T00:00:00Z",
                "rationale": "Approved test fixture.",
                "affected_action_hash": "A" * 64,
            })
        ]
    )
    assert list(checkpoint_validator.iter_errors(uppercase_hash))
    with pytest.raises(HarnessValidationError, match="lowercase SHA-256"):
        validate_checkpoint(uppercase_hash)

    semantic_policy = policy(checkpoint_transcript_bytes=201)
    assert list(policy_validator.iter_errors(semantic_policy)) == []
    with pytest.raises(HarnessValidationError, match="max_transcript_bytes"):
        validate_policy(semantic_policy)

    duplicate_override = checkpoint(
        overrides=[
            authorized({
                "limit": "max_cycles",
                "value": 4,
                "observed_value": 0,
                "reason": "first",
                "actor": "human:owner",
                "timestamp": "2026-08-31T00:00:00Z",
                "affected_action_hash": ACTION_HASH,
            }),
            authorized({
                "limit": "max_cycles",
                "value": 5,
                "observed_value": 0,
                "reason": "second",
                "actor": "human:owner",
                "timestamp": "2026-08-31T00:01:00Z",
                "affected_action_hash": ACTION_HASH,
            }),
        ]
    )
    assert list(checkpoint_validator.iter_errors(duplicate_override)) == []
    with pytest.raises(HarnessValidationError, match="duplicate checkpoint override"):
        validate_checkpoint(duplicate_override)

    contract = (ROOT / "docs" / "public-harness-contract.md").read_text(
        encoding="utf-8"
    )
    assert "authoritative semantic contract" in contract
    assert "structural JSON Schemas" in contract
