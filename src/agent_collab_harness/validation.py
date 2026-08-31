"""Strict validators for public policy and checkpoint documents."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from .errors import HarnessValidationError


POLICY_REQUIRED_KEYS = {"schema_version", "policy_id", "limits", "human_authorization"}
POLICY_KEYS = POLICY_REQUIRED_KEYS
PORTABLE_POLICY_KEYS = {"version", "limits", "context", "terminal_states"}
PORTABLE_LIMIT_KEYS = {
    "max_plan_act_reflect_cycles",
    "max_tool_calls",
    "max_wall_time_seconds",
    "checkpoint_transcript_bytes",
    "max_transcript_bytes",
    "max_same_failure_retries",
    "max_no_evidence_cycles",
    "max_children_per_parent",
    "max_concurrency",
}
PORTABLE_CONTEXT_KEYS = {
    "task_packet_tokens",
    "parent_summary_tokens",
    "memory_digest_tokens",
    "child_result_words",
}
PORTABLE_TERMINAL_STATES = (
    "completed",
    "blocked",
    "budget_exhausted",
    "error",
    "cancelled",
)
LIMIT_KEYS = {
    "max_cycles",
    "max_tool_calls",
    "max_elapsed_seconds",
    "checkpoint_transcript_bytes",
    "max_transcript_bytes",
    "max_same_failure_retries",
    "max_no_evidence_cycles",
    "max_children_per_parent",
    "max_concurrency",
    "max_task_packet_tokens",
    "max_parent_summary_tokens",
    "max_memory_digest_tokens",
    "max_child_result_words",
}

CHECKPOINT_REQUIRED_KEYS = {
    "schema_version",
    "task_id",
    "parent_id",
    "status",
    "cycle",
    "tool_calls",
    "elapsed_seconds",
    "transcript_bytes",
    "same_failure_retries",
    "no_evidence_cycles",
    "active_children",
    "evidence_refs",
    "decisions",
    "overrides",
    "stop_reason",
    "updated_at",
}
CHECKPOINT_OPTIONAL_KEYS = {
    "children_spawned",
    "last_checkpoint_transcript_bytes",
    "task_packet_tokens",
    "parent_summary_tokens",
    "memory_digest_tokens",
    "child_result_words",
    "pending_action_hash",
}
CHECKPOINT_KEYS = CHECKPOINT_REQUIRED_KEYS | CHECKPOINT_OPTIONAL_KEYS

CHECKPOINT_STATUSES = {
    "running",
    "waiting_for_human",
    "completed",
    "blocked",
    "budget_exhausted",
    "error",
    "cancelled",
    "declined",
    "timed_out",
}
DECISIONS = {"approve", "decline", "revise"}
HASH_LENGTH = 64


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise HarnessValidationError(f"{label} must be an object")
    return value


def _exact_keys(
    value: dict[str, Any],
    allowed: set[str],
    required: set[str],
    label: str,
) -> None:
    missing = sorted(required - set(value))
    if missing:
        raise HarnessValidationError(f"missing {label} fields: {', '.join(missing)}")
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise HarnessValidationError(f"unexpected {label} fields: {', '.join(unexpected)}")


def _nonempty_string(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HarnessValidationError(f"{label} must be a non-empty string")
    return value.strip()


def _nonnegative_integer(value: object, label: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise HarnessValidationError(f"{label} must be a non-negative integer")
    return value


def _nonnegative_number(value: object, label: str) -> int | float:
    if (
        not isinstance(value, (int, float))
        or isinstance(value, bool)
        or value < 0
        or value != value
        or value in (float("inf"), float("-inf"))
    ):
        raise HarnessValidationError(f"{label} must be a finite non-negative number")
    return value


def _timestamp(value: object, label: str) -> str:
    text = _nonempty_string(value, label)
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise HarnessValidationError(f"{label} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None:
        raise HarnessValidationError(f"{label} must include a timezone")
    return text


def _unique_strings(value: object, label: str) -> list[str]:
    if not isinstance(value, list):
        raise HarnessValidationError(f"{label} must be an array")
    result = [_nonempty_string(item, f"{label}[]") for item in value]
    if len(result) != len(set(result)):
        raise HarnessValidationError(f"{label} must not contain duplicates")
    return result


def _sha256(value: object, label: str) -> str:
    text = _nonempty_string(value, label)
    if len(text) != HASH_LENGTH or any(char not in "0123456789abcdef" for char in text):
        raise HarnessValidationError(f"{label} must be a lowercase SHA-256 hex digest")
    return text


def _validate_authorization(value: object, label: str) -> None:
    authorization = _object(value, label)
    keys = {"scheme", "key_id", "signature"}
    _exact_keys(authorization, keys, keys, label)
    if authorization["scheme"] != "hmac-sha256":
        raise HarnessValidationError(f"{label}.scheme must be hmac-sha256")
    key_id = _nonempty_string(authorization["key_id"], f"{label}.key_id")
    if any(char.isspace() for char in key_id):
        raise HarnessValidationError(f"{label}.key_id must not contain whitespace")
    _sha256(authorization["signature"], f"{label}.signature")


def _validate_limit_values(limits: dict[str, Any]) -> None:
    for key, value in limits.items():
        _nonnegative_integer(value, f"policy.limits.{key}")
    if limits["max_transcript_bytes"] < limits["checkpoint_transcript_bytes"]:
        raise HarnessValidationError(
            "policy.limits.max_transcript_bytes must be >= checkpoint_transcript_bytes"
        )
    if limits["max_concurrency"] > limits["max_children_per_parent"]:
        raise HarnessValidationError(
            "policy.limits.max_concurrency must be <= max_children_per_parent"
        )


def _validate_human_authorization(value: object) -> dict[str, str]:
    authorization = _object(value, "policy.human_authorization")
    _exact_keys(
        authorization,
        {"key_hashes"},
        {"key_hashes"},
        "policy.human_authorization",
    )
    key_hashes = _object(
        authorization["key_hashes"], "policy.human_authorization.key_hashes"
    )
    for key_id, key_hash in key_hashes.items():
        _nonempty_string(key_id, "policy.human_authorization key id")
        if any(char.isspace() for char in key_id):
            raise HarnessValidationError(
                "policy.human_authorization key ids must not contain whitespace"
            )
        _sha256(key_hash, f"policy.human_authorization.key_hashes.{key_id}")
    return key_hashes


def _normalize_portable_policy(policy: dict[str, Any]) -> dict[str, Any]:
    _exact_keys(policy, PORTABLE_POLICY_KEYS, PORTABLE_POLICY_KEYS, "portable policy")
    if policy["version"] != 1:
        raise HarnessValidationError("portable policy.version must be 1")
    source_limits = _object(policy["limits"], "portable policy.limits")
    _exact_keys(
        source_limits,
        PORTABLE_LIMIT_KEYS,
        PORTABLE_LIMIT_KEYS,
        "portable policy limit",
    )
    context = _object(policy["context"], "portable policy.context")
    _exact_keys(
        context,
        PORTABLE_CONTEXT_KEYS,
        PORTABLE_CONTEXT_KEYS,
        "portable policy context",
    )
    for key, value in source_limits.items():
        _nonnegative_integer(value, f"portable policy.limits.{key}")
    for key, value in context.items():
        _nonnegative_integer(value, f"portable policy.context.{key}")
    terminal_states = _unique_strings(
        policy["terminal_states"], "portable policy.terminal_states"
    )
    if terminal_states != list(PORTABLE_TERMINAL_STATES):
        raise HarnessValidationError(
            "portable policy.terminal_states must match the supported canonical v1 set"
        )

    limits = {
        "max_cycles": source_limits["max_plan_act_reflect_cycles"],
        "max_tool_calls": source_limits["max_tool_calls"],
        "max_elapsed_seconds": source_limits["max_wall_time_seconds"],
        "checkpoint_transcript_bytes": source_limits["checkpoint_transcript_bytes"],
        "max_transcript_bytes": source_limits["max_transcript_bytes"],
        "max_same_failure_retries": source_limits["max_same_failure_retries"],
        "max_no_evidence_cycles": source_limits["max_no_evidence_cycles"],
        "max_children_per_parent": source_limits["max_children_per_parent"],
        "max_concurrency": source_limits["max_concurrency"],
        "max_task_packet_tokens": context["task_packet_tokens"],
        "max_parent_summary_tokens": context["parent_summary_tokens"],
        "max_memory_digest_tokens": context["memory_digest_tokens"],
        "max_child_result_words": context["child_result_words"],
    }
    _validate_limit_values(limits)
    return {
        "schema_version": 1,
        "policy_id": "portable-harness-agent-budget-v1",
        "limits": limits,
        "human_authorization": {"key_hashes": {}},
    }


def validate_policy(document: dict[str, Any]) -> dict[str, Any]:
    """Validate and normalize a public or portable-harness v1 policy."""

    policy = _object(document, "policy")
    if set(policy) == PORTABLE_POLICY_KEYS:
        return _normalize_portable_policy(policy)
    _exact_keys(policy, POLICY_KEYS, POLICY_REQUIRED_KEYS, "policy")
    if policy["schema_version"] != 1:
        raise HarnessValidationError("policy.schema_version must be 1")
    _nonempty_string(policy["policy_id"], "policy.policy_id")
    limits = _object(policy["limits"], "policy.limits")
    _exact_keys(limits, LIMIT_KEYS, LIMIT_KEYS, "policy limit")
    _validate_limit_values(limits)
    _validate_human_authorization(policy["human_authorization"])
    return policy


def _validate_decision(value: object, index: int) -> None:
    decision = _object(value, f"checkpoint.decisions[{index}]")
    keys = {
        "gate",
        "actor",
        "decision",
        "timestamp",
        "rationale",
        "affected_action_hash",
        "authorization",
    }
    _exact_keys(decision, keys, keys, f"checkpoint.decisions[{index}]")
    _nonempty_string(decision["gate"], f"checkpoint.decisions[{index}].gate")
    actor = _nonempty_string(
        decision["actor"], f"checkpoint.decisions[{index}].actor"
    )
    if (
        not actor.startswith("human:")
        or not actor.removeprefix("human:")
        or any(char.isspace() for char in actor)
    ):
        raise HarnessValidationError(
            f"checkpoint.decisions[{index}].actor must use the human: namespace"
        )
    if decision["decision"] not in DECISIONS:
        raise HarnessValidationError(
            f"checkpoint.decisions[{index}].decision must be approve, decline, or revise"
        )
    _timestamp(decision["timestamp"], f"checkpoint.decisions[{index}].timestamp")
    _nonempty_string(decision["rationale"], f"checkpoint.decisions[{index}].rationale")
    _sha256(
        decision["affected_action_hash"],
        f"checkpoint.decisions[{index}].affected_action_hash",
    )
    _validate_authorization(
        decision["authorization"], f"checkpoint.decisions[{index}].authorization"
    )


def _validate_override(value: object, index: int) -> None:
    override = _object(value, f"checkpoint.overrides[{index}]")
    keys = {
        "limit",
        "value",
        "reason",
        "actor",
        "timestamp",
        "affected_action_hash",
        "observed_value",
        "authorization",
    }
    _exact_keys(override, keys, keys, f"checkpoint.overrides[{index}]")
    if override["limit"] not in LIMIT_KEYS:
        raise HarnessValidationError(
            f"checkpoint.overrides[{index}].limit is not a public policy limit"
        )
    _nonnegative_integer(override["value"], f"checkpoint.overrides[{index}].value")
    _nonnegative_number(
        override["observed_value"], f"checkpoint.overrides[{index}].observed_value"
    )
    _nonempty_string(override["reason"], f"checkpoint.overrides[{index}].reason")
    actor = _nonempty_string(override["actor"], f"checkpoint.overrides[{index}].actor")
    if (
        not actor.startswith("human:")
        or not actor.removeprefix("human:")
        or any(char.isspace() for char in actor)
    ):
        raise HarnessValidationError(
            f"checkpoint.overrides[{index}].actor must use the human: namespace"
        )
    _timestamp(override["timestamp"], f"checkpoint.overrides[{index}].timestamp")
    _sha256(
        override["affected_action_hash"],
        f"checkpoint.overrides[{index}].affected_action_hash",
    )
    _validate_authorization(
        override["authorization"], f"checkpoint.overrides[{index}].authorization"
    )


def validate_checkpoint(document: dict[str, Any]) -> dict[str, Any]:
    """Validate and return a public TaskCheckpoint."""

    checkpoint = _object(document, "checkpoint")
    _exact_keys(
        checkpoint,
        CHECKPOINT_KEYS,
        CHECKPOINT_REQUIRED_KEYS,
        "checkpoint",
    )
    if checkpoint["schema_version"] != 1:
        raise HarnessValidationError("checkpoint.schema_version must be 1")
    _nonempty_string(checkpoint["task_id"], "checkpoint.task_id")
    if checkpoint["parent_id"] is not None:
        _nonempty_string(checkpoint["parent_id"], "checkpoint.parent_id")
    if checkpoint["status"] not in CHECKPOINT_STATUSES:
        raise HarnessValidationError(f"invalid checkpoint.status: {checkpoint['status']}")

    for key in (
        "cycle",
        "tool_calls",
        "transcript_bytes",
        "same_failure_retries",
        "no_evidence_cycles",
        "active_children",
    ):
        _nonnegative_integer(checkpoint[key], f"checkpoint.{key}")
    _nonnegative_number(checkpoint["elapsed_seconds"], "checkpoint.elapsed_seconds")

    for key in CHECKPOINT_OPTIONAL_KEYS:
        if key in checkpoint:
            if key == "pending_action_hash":
                if checkpoint[key] is not None:
                    _sha256(checkpoint[key], "checkpoint.pending_action_hash")
            else:
                _nonnegative_integer(checkpoint[key], f"checkpoint.{key}")

    _unique_strings(checkpoint["evidence_refs"], "checkpoint.evidence_refs")

    decisions = checkpoint["decisions"]
    if not isinstance(decisions, list):
        raise HarnessValidationError("checkpoint.decisions must be an array")
    for index, decision in enumerate(decisions):
        _validate_decision(decision, index)

    overrides = checkpoint["overrides"]
    if not isinstance(overrides, list):
        raise HarnessValidationError("checkpoint.overrides must be an array")
    seen_limits: set[str] = set()
    for index, override in enumerate(overrides):
        _validate_override(override, index)
        limit = override["limit"]
        if limit in seen_limits:
            raise HarnessValidationError(f"duplicate checkpoint override: {limit}")
        seen_limits.add(limit)

    if decisions or overrides:
        pending_action_hash = checkpoint.get("pending_action_hash")
        if pending_action_hash is None:
            raise HarnessValidationError(
                "checkpoint.pending_action_hash is required when decisions or overrides exist"
            )
        for index, decision in enumerate(decisions):
            if decision["affected_action_hash"] != pending_action_hash:
                raise HarnessValidationError(
                    f"checkpoint.decisions[{index}].affected_action_hash must match "
                    "checkpoint.pending_action_hash"
                )
        for index, override in enumerate(overrides):
            if override["affected_action_hash"] != pending_action_hash:
                raise HarnessValidationError(
                    f"checkpoint.overrides[{index}].affected_action_hash must match "
                    "checkpoint.pending_action_hash"
                )

    if checkpoint["stop_reason"] is not None:
        _nonempty_string(checkpoint["stop_reason"], "checkpoint.stop_reason")
    _timestamp(checkpoint["updated_at"], "checkpoint.updated_at")
    return checkpoint
