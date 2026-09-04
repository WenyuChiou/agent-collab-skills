import pytest

from agent_collab_harness import evaluate_policy, validate_checkpoint
from agent_collab_harness.goals import new_goal, goal_policy, advance_checkpoint
from agent_collab_harness.errors import HarnessValidationError
from harness_samples import checkpoint, policy


def ready(**kw):
    task = checkpoint(evidence_refs=["test:passing"], **kw)
    return new_goal(task, goal_id="goal-1", next_step="Continue verification")


@pytest.mark.parametrize(
    "metrics", [{"cycle": 3}, {"tool_calls": 10}, {"elapsed_seconds": 60}]
)
def test_slice_limit_continues_goal(metrics):
    state = ready(**metrics)
    result = evaluate_policy(state, goal_policy(policy()))
    assert result.decision == "checkpoint"
    assert result.scope == "slice"
    assert result.auto_continue


def test_advance_preserves_totals_and_is_idempotent():
    state = ready(cycle=3, tool_calls=7, elapsed_seconds=20)
    p = goal_policy(policy())
    advanced = advance_checkpoint(state, p, request_id="step-1")
    assert advanced["task"]["cycle"] == 0
    assert advanced["totals"]["tool_calls"] == 7
    assert advance_checkpoint(advanced, p, request_id="step-1") == advanced
    assert state["task"]["cycle"] == 3
    validate_checkpoint(advanced)


def test_repeated_failure_stops_action_but_allows_diagnosis():
    state = ready(same_failure_retries=2)
    p = goal_policy(policy())
    result = evaluate_policy(state, p)
    assert result.decision == "stop" and result.scope == "action"
    state["action_kind"] = "diagnose"
    assert evaluate_policy(state, p).decision == "continue"
    assert state["task"]["same_failure_retries"] == 2


def test_review_slot_reserved_and_four_finished_children_can_advance():
    p = goal_policy(policy())
    state = ready(children_spawned=3)
    state["review_required"] = True
    assert not evaluate_policy(state, p).spawn_allowed
    state["action_kind"] = "review"
    assert evaluate_policy(state, p).spawn_allowed
    state = ready(children_spawned=4)
    assert evaluate_policy(state, p).auto_continue


@pytest.mark.parametrize(
    "status", ["cancelled", "declined", "waiting_for_human", "blocked"]
)
def test_terminal_gate_cannot_advance(status):
    state = ready(cycle=3, status=status)
    p = goal_policy(policy())
    assert evaluate_policy(state, p).scope == "goal"
    with pytest.raises(HarnessValidationError):
        advance_checkpoint(state, p, request_id="bad")


def test_hard_goal_budget_and_missing_cost_fail_closed():
    p = goal_policy(policy(), goal_limits={"tool_calls": 7})
    assert evaluate_policy(ready(tool_calls=7), p).scope == "goal"
    p = goal_policy(policy(), goal_limits={"cost_microusd": 1})
    assert evaluate_policy(ready(), p).decision == "stop"


def test_no_evidence_does_not_renew_forever():
    s = ready(cycle=3)
    s["task"]["evidence_refs"] = []
    r = evaluate_policy(s, goal_policy(policy()))
    assert not r.auto_continue


def test_bad_totals_rejected():
    state = ready(tool_calls=2)
    state["totals"]["tool_calls"] = 0
    with pytest.raises(HarnessValidationError):
        validate_checkpoint(state)


def test_v1_still_stops_on_three_cycles():
    assert evaluate_policy(checkpoint(cycle=3), policy()).decision == "stop"


@pytest.mark.parametrize(
    "metrics", [{"cycle": 3}, {"tool_calls": 75}, {"elapsed_seconds": 1800}]
)
def test_actual_host_slice_thresholds_continue_without_human(metrics):
    p = goal_policy(policy(max_tool_calls=75, max_elapsed_seconds=1800))
    state = ready(**metrics)
    result = evaluate_policy(state, p)
    assert result.auto_continue and result.scope == "slice"
    advanced = advance_checkpoint(state, p, request_id="actual-threshold")
    assert advanced["totals"] == state["totals"]


def test_danger_gate_and_signed_decline_survive_slice():
    from harness_samples import authorized, AUTH_KEYS, ACTION_HASH

    state = ready(cycle=3)
    state["requires_human"] = True
    assert not evaluate_policy(state, goal_policy(policy())).auto_continue
    state["requires_human"] = False
    state["task"]["pending_action_hash"] = ACTION_HASH
    state["task"]["decisions"] = [
        authorized(
            {
                "gate": "danger",
                "actor": "human:owner",
                "decision": "decline",
                "timestamp": "2026-08-31T00:00:00Z",
                "rationale": "not authorized",
                "affected_action_hash": ACTION_HASH,
            }
        )
    ]
    result = evaluate_policy(state, goal_policy(policy()), authorization_keys=AUTH_KEYS)
    assert result.decision == "stop" and result.scope == "goal"
    with pytest.raises(HarnessValidationError):
        evaluate_policy(state, goal_policy(policy()))


def test_accepted_receipt_cannot_be_erased_for_repeat_evidence():
    s = advance_checkpoint(ready(cycle=3), goal_policy(policy()), request_id="accepted")
    s["accepted_evidence"] = []
    with pytest.raises(HarnessValidationError):
        validate_checkpoint(s)


def test_failure_identity_survives_slices_and_input_revisions():
    from agent_collab_harness.goals import record_failure, permit_corrected_attempt

    s = ready()
    args = dict(
        operation="test",
        target="suite",
        input_sha256="a" * 64,
        error_class="assertion",
        evidence_ref="failure:1",
    )
    for _ in range(3):
        s = record_failure(s, **args)
    p = goal_policy(policy())
    assert evaluate_policy(s, p).decision == "stop"
    with pytest.raises(HarnessValidationError):
        permit_corrected_attempt(s, input_sha256="a" * 64, evidence_ref="test:passing")
    s["task"]["evidence_refs"].append("fix:b")
    corrected = permit_corrected_attempt(s, input_sha256="b" * 64, evidence_ref="fix:b")
    assert evaluate_policy(corrected, p).decision == "continue"
    corrected["task"]["evidence_refs"].append("fix:restore")
    restored = permit_corrected_attempt(
        corrected, input_sha256="a" * 64, evidence_ref="fix:restore"
    )
    assert evaluate_policy(restored, p).decision == "stop"
    assert restored["failure_history"][0]["attempts"] == 3


@pytest.mark.parametrize("gate", ["cancelled", "requires_human", "hard_budget"])
def test_concurrency_cannot_downgrade_goal_gate(gate):
    s = ready(active_children=3)
    p = goal_policy(policy())
    if gate == "cancelled":
        s["task"]["status"] = "cancelled"
    if gate == "requires_human":
        s["requires_human"] = True
    if gate == "hard_budget":
        p["goal_limits"] = {"tool_calls": 0}
    r = evaluate_policy(s, p)
    assert r.decision == "stop" and r.scope == "goal"


def test_mixed_action_failures_allow_diagnosis():
    s = ready(status="error", same_failure_retries=2)
    p = goal_policy(policy())
    assert evaluate_policy(s, p).scope == "action"
    s["action_kind"] = "diagnose"
    assert evaluate_policy(s, p).decision == "continue"


@pytest.mark.parametrize("invalid", [[], {}])
def test_unhashable_active_failure_is_validation_error(invalid):
    s = ready()
    s["active_failure"] = invalid
    with pytest.raises(HarnessValidationError):
        validate_checkpoint(s)


def test_correction_rejects_pre_failure_and_reused_evidence():
    from agent_collab_harness.goals import record_failure, permit_corrected_attempt

    s = record_failure(
        ready(),
        operation="test",
        target="suite",
        input_sha256="a" * 64,
        error_class="assertion",
        evidence_ref="failure:1",
    )
    with pytest.raises(HarnessValidationError):
        permit_corrected_attempt(s, input_sha256="b" * 64, evidence_ref="test:passing")
    s["task"]["evidence_refs"].append("fix:new")
    s = permit_corrected_attempt(s, input_sha256="b" * 64, evidence_ref="fix:new")
    with pytest.raises(HarnessValidationError):
        permit_corrected_attempt(s, input_sha256="c" * 64, evidence_ref="fix:new")


def test_explicit_legacy_migration_preserves_source_and_real_blockers():
    from agent_collab_harness.goals import migrate_goal
    from agent_collab_harness.io import canonical_sha256

    p = goal_policy(policy())
    t = checkpoint(
        cycle=3,
        status="budget_exhausted",
        evidence_refs=["test:passed"],
        stop_reason="limit_reached:cycle=3:max_cycles=3",
    )
    s = migrate_goal(t, p, goal_id="existing", next_step="review")
    assert s["source_sha256"] == canonical_sha256(t)
    assert t["status"] == "budget_exhausted"
    assert evaluate_policy(s, p).auto_continue
    t["stop_reason"] = "Permission denied"
    s = migrate_goal(t, p, goal_id="existing", next_step="review")
    assert evaluate_policy(s, p).decision == "stop"


def test_second_slice_needs_new_evidence_and_accumulates():
    from agent_collab_harness.goals import refresh_totals

    p = goal_policy(policy())
    s = advance_checkpoint(ready(cycle=3, tool_calls=7), p, request_id="first")
    s["task"]["cycle"] = 3
    s["task"]["tool_calls"] = 9
    s = refresh_totals(s)
    assert not evaluate_policy(s, p).auto_continue
    s["task"]["evidence_refs"].append("test:new")
    s = advance_checkpoint(s, p, request_id="second")
    assert s["totals"]["tool_calls"] == 16
    assert s["totals"]["cycle"] == 6
