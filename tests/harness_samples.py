from __future__ import annotations

import hashlib
from typing import Any

from agent_collab_harness.policy import sign_human_record


ACTION_HASH = "a" * 64
AUTH_KEYS = {"owner": "test-owner-secret"}
AUTH_KEY_HASHES = {
    key_id: hashlib.sha256(secret.encode("utf-8")).hexdigest()
    for key_id, secret in AUTH_KEYS.items()
}


def authorized(record: dict[str, Any], key_id: str = "owner") -> dict[str, Any]:
    result = dict(record)
    result["authorization"] = {
        "scheme": "hmac-sha256",
        "key_id": key_id,
        "signature": sign_human_record(result, AUTH_KEYS[key_id]),
    }
    return result


def policy(**limit_overrides: int) -> dict[str, Any]:
    limits = {
        "max_cycles": 3,
        "max_tool_calls": 10,
        "max_elapsed_seconds": 60,
        "checkpoint_transcript_bytes": 100,
        "max_transcript_bytes": 200,
        "max_same_failure_retries": 2,
        "max_no_evidence_cycles": 2,
        "max_children_per_parent": 4,
        "max_concurrency": 2,
        "max_task_packet_tokens": 500,
        "max_parent_summary_tokens": 100,
        "max_memory_digest_tokens": 100,
        "max_child_result_words": 50,
    }
    limits.update(limit_overrides)
    return {
        "schema_version": 1,
        "policy_id": "test-policy",
        "limits": limits,
        "human_authorization": {"key_hashes": AUTH_KEY_HASHES},
    }


def portable_policy(**limit_overrides: int) -> dict[str, Any]:
    limits = {
        "max_plan_act_reflect_cycles": 3,
        "max_tool_calls": 10,
        "max_wall_time_seconds": 60,
        "checkpoint_transcript_bytes": 100,
        "max_transcript_bytes": 200,
        "max_same_failure_retries": 2,
        "max_no_evidence_cycles": 2,
        "max_children_per_parent": 4,
        "max_concurrency": 2,
    }
    limits.update(limit_overrides)
    return {
        "version": 1,
        "limits": limits,
        "context": {
            "task_packet_tokens": 500,
            "parent_summary_tokens": 100,
            "memory_digest_tokens": 100,
            "child_result_words": 50,
        },
        "terminal_states": [
            "completed",
            "blocked",
            "budget_exhausted",
            "error",
            "cancelled",
        ],
    }


def checkpoint(**overrides: Any) -> dict[str, Any]:
    result: dict[str, Any] = {
        "schema_version": 1,
        "task_id": "task-1",
        "parent_id": None,
        "status": "running",
        "cycle": 0,
        "tool_calls": 0,
        "elapsed_seconds": 0,
        "transcript_bytes": 0,
        "same_failure_retries": 0,
        "no_evidence_cycles": 0,
        "active_children": 0,
        "children_spawned": 0,
        "last_checkpoint_transcript_bytes": 0,
        "task_packet_tokens": 0,
        "parent_summary_tokens": 0,
        "memory_digest_tokens": 0,
        "child_result_words": 0,
        "evidence_refs": [],
        "decisions": [],
        "overrides": [],
        "stop_reason": None,
        "updated_at": "2026-08-31T00:00:00Z",
    }
    result.update(overrides)
    if (result["decisions"] or result["overrides"]) and "pending_action_hash" not in overrides:
        records = [*result["decisions"], *result["overrides"]]
        result["pending_action_hash"] = records[0]["affected_action_hash"]
    return result
