from __future__ import annotations

import copy

import pytest

from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.io import canonical_sha256
from agent_collab_harness.policy import evaluate_policy
from agent_collab_harness.validation import validate_checkpoint, validate_policy
from harness_samples import (
    ACTION_HASH,
    AUTH_KEYS,
    authorized,
    checkpoint,
    policy,
    portable_policy,
)


def test_valid_documents_and_policy_hash_are_stable() -> None:
    first = policy()
    second = {
        "limits": dict(reversed(list(first["limits"].items()))),
        "policy_id": first["policy_id"],
        "schema_version": first["schema_version"],
        "human_authorization": first["human_authorization"],
    }
    assert validate_policy(first) == first
    assert validate_checkpoint(checkpoint())["task_id"] == "task-1"
    assert canonical_sha256(first) == canonical_sha256(second)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("cycle", 3),
        ("tool_calls", 10),
        ("elapsed_seconds", 60),
        ("transcript_bytes", 200),
        ("same_failure_retries", 2),
        ("no_evidence_cycles", 2),
        ("task_packet_tokens", 500),
        ("parent_summary_tokens", 100),
        ("memory_digest_tokens", 100),
        ("child_result_words", 50),
    ],
)
def test_every_hard_limit_stops_and_blocks_spawn(field: str, value: int) -> None:
    result = evaluate_policy(checkpoint(**{field: value}), policy())
    assert result.decision == "stop"
    assert result.spawn_allowed is False
    assert any(field in reason for reason in result.reasons)


def test_checkpoint_threshold_is_distinct_from_stop() -> None:
    result = evaluate_policy(
        checkpoint(transcript_bytes=150, last_checkpoint_transcript_bytes=50),
        policy(),
    )
    assert result.decision == "checkpoint"
    assert result.checkpoint_required is True
    assert result.spawn_allowed is False


@pytest.mark.parametrize(
    "status",
    [
        "waiting_for_human",
        "completed",
        "blocked",
        "budget_exhausted",
        "error",
        "cancelled",
        "declined",
        "timed_out",
    ],
)
def test_nonrunning_status_stops(status: str) -> None:
    result = evaluate_policy(checkpoint(status=status), policy())
    assert result.decision == "stop"
    assert result.spawn_allowed is False
    assert f"task_status:{status}" in result.reasons


def test_child_limits_block_new_spawn_without_stopping_current_work() -> None:
    at_parent_limit = evaluate_policy(checkpoint(children_spawned=4), policy())
    at_concurrency_limit = evaluate_policy(checkpoint(active_children=2), policy())
    assert at_parent_limit.decision == "continue"
    assert at_parent_limit.spawn_allowed is False
    assert at_concurrency_limit.decision == "continue"
    assert at_concurrency_limit.spawn_allowed is False


def test_human_override_must_be_explicit_and_can_only_raise_limit() -> None:
    valid = checkpoint(
        tool_calls=5,
        overrides=[
            authorized({
                "limit": "max_tool_calls",
                "value": 20,
                "observed_value": 5,
                "reason": "Approved bounded extension",
                "actor": "human:owner",
                "timestamp": "2026-08-31T00:00:00Z",
                "affected_action_hash": ACTION_HASH,
            })
        ]
    )
    assert evaluate_policy(
        valid, policy(), authorization_keys=AUTH_KEYS
    ).effective_limits["max_tool_calls"] == 20

    invalid = copy.deepcopy(valid)
    invalid["overrides"][0]["value"] = 5
    invalid["overrides"][0] = authorized(
        {key: value for key, value in invalid["overrides"][0].items() if key != "authorization"}
    )
    with pytest.raises(HarnessValidationError, match="cannot lower"):
        evaluate_policy(invalid, policy(), authorization_keys=AUTH_KEYS)


def test_checkpoint_decision_record_is_strict() -> None:
    valid = checkpoint(
        decisions=[
            authorized({
                "gate": "H0",
                "actor": "human:owner",
                "decision": "approve",
                "timestamp": "2026-08-31T00:00:00Z",
                "rationale": "Approved after reviewing the audit.",
                "affected_action_hash": ACTION_HASH,
            })
        ]
    )
    validate_checkpoint(valid)

    invalid = copy.deepcopy(valid)
    invalid["decisions"][0]["affected_action_hash"] = "not-a-hash"
    with pytest.raises(HarnessValidationError, match="SHA-256"):
        validate_checkpoint(invalid)


@pytest.mark.parametrize("decision", ["decline", "revise"])
def test_latest_nonapproval_human_decision_stops_even_if_status_is_running(
    decision: str,
) -> None:
    document = checkpoint(
        decisions=[
            authorized({
                "gate": "H4",
                "actor": "human:owner",
                "decision": decision,
                "timestamp": "2026-08-31T00:00:00Z",
                "rationale": "Semantic acceptance is not approved.",
                "affected_action_hash": ACTION_HASH,
            })
        ]
    )
    result = evaluate_policy(document, policy(), authorization_keys=AUTH_KEYS)
    assert result.decision == "stop"
    assert result.spawn_allowed is False
    assert f"human_gate:H4:{decision}" in result.reasons


def test_later_approval_for_same_gate_supersedes_prior_decline() -> None:
    decisions = [
        authorized({
            "gate": "H4",
            "actor": "human:owner",
            "decision": "decline",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "First draft was not accepted.",
            "affected_action_hash": ACTION_HASH,
        }),
        authorized({
            "gate": "H4",
            "actor": "human:owner",
            "decision": "approve",
            "timestamp": "2026-08-31T00:10:00Z",
            "rationale": "Revised bytes were accepted.",
            "affected_action_hash": ACTION_HASH,
        }),
    ]
    result = evaluate_policy(
        checkpoint(decisions=decisions), policy(), authorization_keys=AUTH_KEYS
    )
    assert result.decision == "continue"
    assert result.spawn_allowed is True


def test_unknown_fields_and_duplicate_overrides_are_rejected() -> None:
    unknown = checkpoint()
    unknown["silent_retry"] = True
    with pytest.raises(HarnessValidationError, match="unexpected checkpoint"):
        validate_checkpoint(unknown)

    duplicate = checkpoint(
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
    with pytest.raises(HarnessValidationError, match="duplicate checkpoint override"):
        validate_checkpoint(duplicate)


def test_policy_rejects_incoherent_limits() -> None:
    with pytest.raises(HarnessValidationError, match="max_transcript_bytes"):
        validate_policy(policy(checkpoint_transcript_bytes=201))
    with pytest.raises(HarnessValidationError, match="max_concurrency"):
        validate_policy(policy(max_concurrency=5))


def test_portable_harness_canonical_policy_is_normalized_and_hashed_as_source() -> None:
    source = portable_policy()
    normalized = validate_policy(source)
    assert normalized["policy_id"] == "portable-harness-agent-budget-v1"
    assert normalized["limits"]["max_cycles"] == 3
    result = evaluate_policy(checkpoint(), source)
    assert result.policy_hash == canonical_sha256(source)


def test_human_records_fail_closed_without_valid_authorization() -> None:
    record = authorized(
        {
            "gate": "H1",
            "actor": "human:owner",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Approved contract change.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    document = checkpoint(decisions=[record])
    with pytest.raises(HarnessValidationError, match="no configured human authorization"):
        evaluate_policy(document, policy())

    forged = copy.deepcopy(document)
    forged["decisions"][0]["decision"] = "decline"
    with pytest.raises(HarnessValidationError, match="invalid human authorization signature"):
        evaluate_policy(forged, policy(), authorization_keys=AUTH_KEYS)

    attacker_record = authorized(
        {
            "gate": "H1",
            "actor": "human:attacker",
            "decision": "approve",
            "timestamp": "2026-08-31T00:01:00Z",
            "rationale": "Untrusted caller-created identity.",
            "affected_action_hash": ACTION_HASH,
        },
        key_id="owner",
    )
    attacker_record["actor"] = "human:attacker"
    attacker_record["authorization"]["key_id"] = "attacker"
    with pytest.raises(HarnessValidationError, match="not authorized by the canonical policy"):
        evaluate_policy(
            checkpoint(decisions=[attacker_record]),
            policy(),
            authorization_keys={"attacker": "agent-chosen-secret"},
        )


def test_override_must_be_authorized_before_original_limit_is_exhausted() -> None:
    late = checkpoint(
        tool_calls=10,
        overrides=[
            authorized(
                {
                    "limit": "max_tool_calls",
                    "value": 20,
                    "observed_value": 10,
                    "reason": "Too late.",
                    "actor": "human:owner",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "affected_action_hash": ACTION_HASH,
                }
            )
        ],
    )
    with pytest.raises(HarnessValidationError, match="not authorized before exhaustion"):
        evaluate_policy(late, policy(), authorization_keys=AUTH_KEYS)


def test_action_hash_binding_rejects_decision_for_other_pending_action() -> None:
    decision = authorized(
        {
            "gate": "H2",
            "actor": "human:owner",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Approved a different action.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    with pytest.raises(HarnessValidationError, match="must match"):
        validate_checkpoint(
            checkpoint(decisions=[decision], pending_action_hash="b" * 64)
        )


def test_delegated_executor_cannot_self_authorize_human_gate() -> None:
    forged = authorized(
        {
            "gate": "H1",
            "actor": "delegated-executor",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Agent attempted self-approval.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    with pytest.raises(HarnessValidationError, match="human: namespace"):
        validate_checkpoint(checkpoint(decisions=[forged]))


def test_decision_order_uses_signed_timestamp_not_array_position() -> None:
    newer_decline = authorized(
        {
            "gate": "H4",
            "actor": "human:owner",
            "decision": "decline",
            "timestamp": "2026-08-31T00:10:00Z",
            "rationale": "Current action is declined.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    older_approval = authorized(
        {
            "gate": "H4",
            "actor": "human:owner",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Earlier approval.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    result = evaluate_policy(
        checkpoint(decisions=[newer_decline, older_approval]),
        policy(),
        authorization_keys=AUTH_KEYS,
    )
    assert result.decision == "stop"
    assert "human_gate:H4:decline" in result.reasons


def test_portable_policy_rejects_changed_terminal_state_contract() -> None:
    changed = portable_policy()
    changed["terminal_states"] = ["running"]
    with pytest.raises(HarnessValidationError, match="supported canonical v1 set"):
        validate_policy(changed)


def test_bare_human_namespace_is_rejected_by_programmatic_validator() -> None:
    record = authorized(
        {
            "gate": "H0",
            "actor": "human:",
            "decision": "approve",
            "timestamp": "2026-08-31T00:00:00Z",
            "rationale": "Invalid empty identity.",
            "affected_action_hash": ACTION_HASH,
        }
    )
    with pytest.raises(HarnessValidationError, match="human: namespace"):
        validate_checkpoint(checkpoint(decisions=[record]))
