"""Deterministic evaluation of TaskCheckpoint documents."""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from .errors import HarnessValidationError
from .io import canonical_sha256
from .models import PolicyDecision
from .validation import validate_checkpoint, validate_policy


HARD_METRICS = {
    "cycle": "max_cycles",
    "tool_calls": "max_tool_calls",
    "elapsed_seconds": "max_elapsed_seconds",
    "transcript_bytes": "max_transcript_bytes",
    "same_failure_retries": "max_same_failure_retries",
    "no_evidence_cycles": "max_no_evidence_cycles",
    "task_packet_tokens": "max_task_packet_tokens",
    "parent_summary_tokens": "max_parent_summary_tokens",
    "memory_digest_tokens": "max_memory_digest_tokens",
    "child_result_words": "max_child_result_words",
}
LIMIT_OBSERVED_METRICS = {
    **{limit_name: metric_name for metric_name, limit_name in HARD_METRICS.items()},
    "checkpoint_transcript_bytes": "transcript_bytes",
    "max_children_per_parent": "children_spawned",
    "max_concurrency": "active_children",
}

TERMINAL_OR_PAUSED_STATUSES = {
    "waiting_for_human",
    "completed",
    "blocked",
    "budget_exhausted",
    "error",
    "cancelled",
    "declined",
    "timed_out",
}


def _observed_metrics(checkpoint: dict[str, Any]) -> dict[str, int | float]:
    return {
        "cycle": checkpoint["cycle"],
        "tool_calls": checkpoint["tool_calls"],
        "elapsed_seconds": checkpoint["elapsed_seconds"],
        "transcript_bytes": checkpoint["transcript_bytes"],
        "same_failure_retries": checkpoint["same_failure_retries"],
        "no_evidence_cycles": checkpoint["no_evidence_cycles"],
        "children_spawned": checkpoint.get("children_spawned", 0),
        "active_children": checkpoint["active_children"],
        "task_packet_tokens": checkpoint.get("task_packet_tokens", 0),
        "parent_summary_tokens": checkpoint.get("parent_summary_tokens", 0),
        "memory_digest_tokens": checkpoint.get("memory_digest_tokens", 0),
        "child_result_words": checkpoint.get("child_result_words", 0),
        "last_checkpoint_transcript_bytes": checkpoint.get(
            "last_checkpoint_transcript_bytes", 0
        ),
    }


def _effective_limits(
    checkpoint: dict[str, Any],
    policy: dict[str, Any],
    metrics: dict[str, int | float],
) -> dict[str, int]:
    limits = dict(policy["limits"])
    for override in checkpoint["overrides"]:
        limit = override["limit"]
        value = override["value"]
        observed_value = override["observed_value"]
        metric_name = LIMIT_OBSERVED_METRICS[limit]
        if observed_value >= limits[limit]:
            raise HarnessValidationError(
                f"checkpoint override for {limit} was not authorized before exhaustion: "
                f"observed_value={observed_value} >= {limits[limit]}"
            )
        if observed_value > metrics[metric_name]:
            raise HarnessValidationError(
                f"checkpoint override observed_value for {limit} exceeds current "
                f"{metric_name}: {observed_value} > {metrics[metric_name]}"
            )
        if value < limits[limit]:
            raise HarnessValidationError(
                f"checkpoint override cannot lower {limit}: {value} < {limits[limit]}"
            )
        limits[limit] = value
    return limits


def _authorization_payload(record: dict[str, Any]) -> bytes:
    payload = {key: value for key, value in record.items() if key != "authorization"}
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def sign_human_record(record: dict[str, Any], secret: str | bytes) -> str:
    """Sign a decision or override record before adding its authorization field."""

    key = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not key:
        raise HarnessValidationError("human authorization secret must not be empty")
    return hmac.new(key, _authorization_payload(record), hashlib.sha256).hexdigest()


def _verify_human_record(
    record: dict[str, Any],
    authorization_keys: Mapping[str, str | bytes] | None,
    trusted_key_hashes: Mapping[str, str],
    label: str,
) -> None:
    authorization = record["authorization"]
    key_id = authorization["key_id"]
    if record["actor"] != f"human:{key_id}":
        raise HarnessValidationError(
            f"{label}.actor must match authorization key_id human:{key_id}"
        )
    if key_id not in trusted_key_hashes:
        raise HarnessValidationError(
            f"{label} key id is not authorized by the canonical policy: {key_id}"
        )
    if authorization_keys is None or key_id not in authorization_keys:
        raise HarnessValidationError(
            f"{label} has no configured human authorization key: {key_id}"
        )
    secret = authorization_keys[key_id]
    secret_bytes = secret.encode("utf-8") if isinstance(secret, str) else secret
    if not hmac.compare_digest(
        hashlib.sha256(secret_bytes).hexdigest(), trusted_key_hashes[key_id]
    ):
        raise HarnessValidationError(
            f"{label} human authorization key does not match canonical policy: {key_id}"
        )
    expected = sign_human_record(record, secret)
    if not hmac.compare_digest(expected, authorization["signature"]):
        raise HarnessValidationError(f"{label} has an invalid human authorization signature")


def _decision_time(record: dict[str, Any]) -> datetime:
    text = record["timestamp"]
    normalized = text[:-1] + "+00:00" if text.endswith("Z") else text
    return datetime.fromisoformat(normalized)


def evaluate_policy(
    checkpoint_document: dict[str, Any],
    policy_document: dict[str, Any],
    *,
    authorization_keys: Mapping[str, str | bytes] | None = None,
) -> PolicyDecision:
    """Evaluate one checkpoint without performing retries or side effects."""

    checkpoint = validate_checkpoint(checkpoint_document)
    policy = validate_policy(policy_document)
    trusted_key_hashes = policy["human_authorization"]["key_hashes"]
    metrics = _observed_metrics(checkpoint)
    for index, human_decision in enumerate(checkpoint["decisions"]):
        _verify_human_record(
            human_decision,
            authorization_keys,
            trusted_key_hashes,
            f"checkpoint.decisions[{index}]",
        )
    for index, override in enumerate(checkpoint["overrides"]):
        _verify_human_record(
            override,
            authorization_keys,
            trusted_key_hashes,
            f"checkpoint.overrides[{index}]",
        )
    limits = _effective_limits(checkpoint, policy, metrics)
    reasons: list[str] = []

    if checkpoint["status"] in TERMINAL_OR_PAUSED_STATUSES:
        reasons.append(f"task_status:{checkpoint['status']}")

    latest_gate_decisions: dict[str, dict[str, Any]] = {}
    for human_decision in checkpoint["decisions"]:
        gate = human_decision["gate"]
        current = latest_gate_decisions.get(gate)
        if current is None or _decision_time(human_decision) > _decision_time(current):
            latest_gate_decisions[gate] = human_decision
        elif _decision_time(human_decision) == _decision_time(current):
            raise HarnessValidationError(
                f"checkpoint has ambiguous human decisions for gate {gate} at "
                f"{human_decision['timestamp']}"
            )
    for gate, human_record in latest_gate_decisions.items():
        decision_value = human_record["decision"]
        if decision_value in {"decline", "revise"}:
            reasons.append(f"human_gate:{gate}:{decision_value}")

    for metric_name, limit_name in HARD_METRICS.items():
        observed = metrics[metric_name]
        limit = limits[limit_name]
        if observed >= limit:
            reasons.append(f"limit_reached:{metric_name}={observed}:{limit_name}={limit}")

    children_spawned = int(metrics["children_spawned"])
    active_children = int(metrics["active_children"])
    if children_spawned > limits["max_children_per_parent"]:
        reasons.append(
            "limit_exceeded:"
            f"children_spawned={children_spawned}:"
            f"max_children_per_parent={limits['max_children_per_parent']}"
        )
    if active_children > limits["max_concurrency"]:
        reasons.append(
            "limit_exceeded:"
            f"active_children={active_children}:"
            f"max_concurrency={limits['max_concurrency']}"
        )

    decision = "stop" if reasons else "continue"
    checkpoint_required = False
    if decision == "continue":
        growth = (
            int(metrics["transcript_bytes"])
            - int(metrics["last_checkpoint_transcript_bytes"])
        )
        if growth >= limits["checkpoint_transcript_bytes"]:
            decision = "checkpoint"
            checkpoint_required = True
            reasons.append(
                "checkpoint_required:"
                f"transcript_growth={growth}:"
                f"checkpoint_transcript_bytes={limits['checkpoint_transcript_bytes']}"
            )

    spawn_allowed = (
        decision == "continue"
        and children_spawned < limits["max_children_per_parent"]
        and active_children < limits["max_concurrency"]
    )

    return PolicyDecision(
        schema_version=1,
        policy_id=policy["policy_id"],
        policy_hash=canonical_sha256(policy_document),
        decision=decision,
        spawn_allowed=spawn_allowed,
        checkpoint_required=checkpoint_required,
        reasons=reasons,
        effective_limits=limits,
        observed_metrics=metrics,
    )


def fail_closed_decision(
    *,
    policy_id: str,
    reason: str,
    observed_metrics: dict[str, int | float] | None = None,
) -> PolicyDecision:
    """Create a fail-closed result when evaluation inputs are unreadable."""

    return PolicyDecision(
        schema_version=1,
        policy_id=policy_id,
        policy_hash=None,
        decision="stop",
        spawn_allowed=False,
        checkpoint_required=False,
        reasons=[f"evaluation_error:{reason}"],
        effective_limits={},
        observed_metrics=observed_metrics or {},
    )
