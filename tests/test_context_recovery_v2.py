"""Recovery is host work, not permission to bypass a stopped action."""

from copy import deepcopy

import pytest

from agent_collab_harness import evaluate_policy
from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.goals import (
    advance_checkpoint, goal_policy, migrate_goal, new_goal, refresh_totals,
)
from agent_collab_harness.io import canonical_sha256
from harness_samples import ACTION_HASH, AUTH_KEYS, authorized, checkpoint, policy


CONTEXT = (
    "transcript_bytes", "task_packet_tokens", "parent_summary_tokens",
    "memory_digest_tokens", "child_result_words",
)


def ready(**metrics):
    return new_goal(checkpoint(evidence_refs=["test:passing"], **metrics),
                    goal_id="existing-goal", next_step="Verify remaining work")


@pytest.mark.parametrize("metric", CONTEXT)
def test_context_limit_requests_local_compaction_not_goal_stop(metric):
    p = goal_policy(policy())
    s = ready(**{metric: p["base_policy"]["limits"]["max_" + metric]})
    before = deepcopy(s)
    r = evaluate_policy(s, p)
    assert (r.decision, r.scope, r.auto_continue) == ("checkpoint", "action", False)
    assert not r.spawn_allowed and r.checkpoint_required
    assert "context_compaction_required" in r.reasons
    assert s == before  # Evaluation cannot fabricate smaller observations.
    with pytest.raises(HarnessValidationError):
        advance_checkpoint(s, p, request_id="cannot-reset-context")
    # Host preserves source artifacts, creates a smaller active packet, and measures it.
    s["task"][metric] = 0
    s["task"]["evidence_refs"].append("packet:measured-and-linked")
    assert evaluate_policy(s, p).decision == "continue"
    assert s["totals"] == before["totals"]
    assert s["failure_history"] == before["failure_history"]


@pytest.mark.parametrize("hard", [False, True])
def test_context_maintenance_precedes_slice_advance(hard):
    p = goal_policy(policy())
    size_key = "max_transcript_bytes" if hard else "checkpoint_transcript_bytes"
    s = ready(cycle=3, transcript_bytes=p["base_policy"]["limits"][size_key])
    r = evaluate_policy(s, p)
    assert r.decision == "checkpoint" and r.scope == "action" and not r.auto_continue
    with pytest.raises(HarnessValidationError):
        advance_checkpoint(s, p, request_id="premature")
    s["task"]["transcript_bytes"] = 0
    s["task"]["last_checkpoint_transcript_bytes"] = 0
    assert evaluate_policy(s, p).auto_continue
    advanced = advance_checkpoint(s, p, request_id="after-compaction")
    assert advanced["totals"] == s["totals"]


@pytest.mark.parametrize("gate", [
    "cancelled", "declined", "waiting_for_human", "blocked", "budget_exhausted",
    "requires_human", "hard_budget", "unknown_cost", "signed_decline",
])
@pytest.mark.parametrize("action", ["execute", "diagnose", "wait"])
def test_real_gate_dominates_context_recovery(gate, action):
    p = goal_policy(policy())
    s = ready(cycle=3, transcript_bytes=p["base_policy"]["limits"]["max_transcript_bytes"])
    s["action_kind"] = action
    if gate == "requires_human":
        s[gate] = True
    elif gate == "hard_budget":
        p["goal_limits"] = {"tool_calls": 0}
    elif gate == "unknown_cost":
        p["goal_limits"] = {"cost_microusd": 1}
    elif gate == "signed_decline":
        s["task"]["pending_action_hash"] = ACTION_HASH
        s["task"]["decisions"] = [authorized({
            "gate": "danger", "actor": "human:owner", "decision": "decline",
            "timestamp": "2026-09-04T00:00:00Z", "rationale": "Not authorized",
            "affected_action_hash": ACTION_HASH,
        })]
    else:
        s["task"]["status"] = gate
    r = evaluate_policy(s, p, authorization_keys=AUTH_KEYS)
    assert r.decision == "stop" and r.scope == "goal" and not r.auto_continue
    assert not r.spawn_allowed
    with pytest.raises(HarnessValidationError):
        advance_checkpoint(s, p, request_id="blocked", authorization_keys=AUTH_KEYS)


def test_mixed_context_and_failed_action_remains_action_stop():
    p = goal_policy(policy())
    s = ready(transcript_bytes=200, same_failure_retries=2, status="error")
    r = evaluate_policy(s, p)
    assert r.decision == "stop" and r.scope == "action"
    s["action_kind"] = "diagnose"
    r = evaluate_policy(s, p)
    assert r.decision == "checkpoint" and r.scope == "action"
    assert s["task"]["same_failure_retries"] == 2 and s["task"]["status"] == "error"


def test_legacy_exact_context_exhaustion_migrates_without_clearing_limit():
    p = goal_policy(policy())
    t = checkpoint(status="budget_exhausted", transcript_bytes=200,
                   stop_reason="limit_reached:transcript_bytes=200:max_transcript_bytes=200")
    original = deepcopy(t)
    s = migrate_goal(t, p, goal_id="existing", next_step="Compact then verify")
    assert t == original and s["source_sha256"] == canonical_sha256(t)
    assert s["task"]["status"] == "running"
    r = evaluate_policy(s, p)
    assert r.scope == "action" and r.decision == "checkpoint" and not r.spawn_allowed
    assert s["task"]["transcript_bytes"] == 200
    for change in ({"stop_reason": "Permission denied"}, {"same_failure_retries": 2},
                   {"status": "blocked"}, {"status": "waiting_for_human"}):
        original = {**t, **change}
        s = migrate_goal(original, p, goal_id="existing", next_step="Inspect")
        assert s["task"]["status"] == original["status"]
        assert evaluate_policy(s, p).scope == "goal"


def test_v1_context_semantics_unchanged():
    r = evaluate_policy(checkpoint(transcript_bytes=200), policy())
    assert r.schema_version == 1 and r.decision == "stop"


@pytest.mark.parametrize("limit", ["max_transcript_bytes", "checkpoint_transcript_bytes",
    "max_task_packet_tokens", "max_parent_summary_tokens", "max_memory_digest_tokens",
    "max_child_result_words"])
def test_compaction_preserves_signed_context_override(limit):
    from agent_collab_harness.policy import LIMIT_OBSERVED_METRICS
    p = goal_policy(policy())
    base = p["base_policy"]["limits"][limit]
    metric = LIMIT_OBSERVED_METRICS[limit]
    record = authorized({
        "limit": limit, "value": base * 2, "observed_value": base - 1,
        "reason": "Authorized before original exhaustion", "actor": "human:owner",
        "timestamp": "2026-09-04T00:00:00Z", "affected_action_hash": ACTION_HASH,
    })
    s = ready(overrides=[record], **{metric: base * 2})
    assert evaluate_policy(s, p, authorization_keys=AUTH_KEYS).scope == "action"
    s["task"][metric] = 1
    s["task"]["last_checkpoint_transcript_bytes"] = s["task"]["transcript_bytes"]
    before = deepcopy(s)
    assert evaluate_policy(s, p, authorization_keys=AUTH_KEYS).decision == "continue"
    assert s == before and s["task"]["overrides"] == [record]
    with pytest.raises(HarnessValidationError):
        evaluate_policy(s["task"], p["base_policy"], authorization_keys=AUTH_KEYS)
    with pytest.raises(HarnessValidationError):
        evaluate_policy(s, p)  # Still requires the authentic trusted-host key.
    s["task"]["overrides"][0]["value"] += 1
    with pytest.raises(HarnessValidationError):
        evaluate_policy(s, p, authorization_keys=AUTH_KEYS)


@pytest.mark.parametrize("limit,metric", [
    ("max_tool_calls", "tool_calls"), ("max_same_failure_retries", "same_failure_retries"),
    ("max_concurrency", "active_children"),
])
def test_context_recovery_never_relaxes_noncontext_override_observations(limit, metric):
    p = goal_policy(policy())
    base = p["base_policy"]["limits"][limit]
    record = authorized({
        "limit": limit, "value": base * 2, "observed_value": base - 1,
        "reason": "Fixture", "actor": "human:owner",
        "timestamp": "2026-09-04T00:00:00Z", "affected_action_hash": ACTION_HASH,
    })
    s = ready(overrides=[record], **{metric: 0})
    with pytest.raises(HarnessValidationError):
        evaluate_policy(s, p, authorization_keys=AUTH_KEYS)


def test_one_hundred_synthetic_context_recoveries_keep_cumulative_usage():
    # Deterministic policy replay, NOT 100 live tasks or a human-intervention estimate.
    p = goal_policy(policy())
    s = ready()
    for index in range(100):
        s["task"].update(cycle=3, tool_calls=2, transcript_bytes=200)
        s["task"]["evidence_refs"].append(f"test:round-{index}")
        s = refresh_totals(s)
        r = evaluate_policy(s, p)
        assert r.scope == "action" and r.decision == "checkpoint"
        s["task"]["transcript_bytes"] = 0
        s = advance_checkpoint(s, p, request_id=f"slice-{index}")
        assert s["totals"]["tool_calls"] == (index + 1) * 2
    assert s["slice_id"] == 100 and s["totals"]["cycle"] == 300
    assert s["totals"]["cost_microusd"] is None
