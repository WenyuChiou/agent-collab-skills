"""Provider-neutral goal slices. This module never executes agent actions."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
import math

from .errors import HarnessValidationError
from .io import canonical_sha256
from .models import PolicyDecision


COUNTERS = ("cycle", "tool_calls", "elapsed_seconds", "children_spawned")
USAGE = ("input_tokens", "cached_input_tokens", "output_tokens", "cost_microusd")
TOTALS = COUNTERS + USAGE
EXTRA = {
    "schema_version",
    "task_id",
    "goal_id",
    "slice_id",
    "task",
    "totals",
    "baseline",
    "usage",
    "accepted_evidence",
    "history",
    "next_step",
    "action_kind",
    "review_required",
    "requires_human",
    "source_sha256",
    "failure_history",
    "active_failure",
}


def _object(value, keys, label):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise HarnessValidationError(f"{label}: expected fields {sorted(keys)}")


def _number(value, label, *, nullable=False):
    if nullable and value is None:
        return
    if (
        label == "elapsed_seconds"
        and type(value) in (int, float)
        and value >= 0
        and math.isfinite(value)
    ):
        return
    if type(value) is not int or value < 0:
        raise HarnessValidationError(f"{label}: expected nonnegative integer")


def _text(value, label, *, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        raise HarnessValidationError(f"{label}: expected text")


def goal_policy(base_policy, *, goal_limits=None):
    from .validation import validate_policy

    base = validate_policy(base_policy)
    if base.get("schema_version") != 1:
        raise HarnessValidationError("goal_policy requires a v1 base")
    result = {
        "schema_version": 2,
        "policy_id": base["policy_id"] + "-goals",
        "base_policy": base,
        "goal_limits": dict(goal_limits or {}),
        "reviewer_reserve": 1,
    }
    return validate_goal_policy(result)


def validate_goal_policy(document):
    from .validation import validate_policy

    _object(
        document,
        {
            "schema_version",
            "policy_id",
            "base_policy",
            "goal_limits",
            "reviewer_reserve",
        },
        "goal policy",
    )
    if document["schema_version"] != 2 or type(document["schema_version"]) is not int:
        raise HarnessValidationError("expected policy v2")
    _text(document["policy_id"], "policy_id")
    if (
        not isinstance(document["base_policy"], dict)
        or document["base_policy"].get("schema_version") != 1
    ):
        raise HarnessValidationError("base_policy must be public v1")
    validate_policy(document["base_policy"])
    if not isinstance(document["goal_limits"], dict) or not set(
        document["goal_limits"]
    ) <= set(TOTALS):
        raise HarnessValidationError("unknown goal limit")
    for k, v in document["goal_limits"].items():
        _number(v, k)
    _number(document["reviewer_reserve"], "reviewer_reserve")
    if (
        document["reviewer_reserve"]
        >= document["base_policy"]["limits"]["max_children_per_parent"]
    ):
        raise HarnessValidationError("review reserve must leave an executor slot")
    return deepcopy(document)


def _slice_metrics(state):
    return {**{k: state["task"].get(k, 0) for k in COUNTERS}, **state["usage"]}


def refresh_totals(state):
    """Update totals after observed task counters change; never reset baseline."""
    state = deepcopy(state)
    for key, value in _slice_metrics(state).items():
        before = state["baseline"][key]
        state["totals"][key] = (
            None if value is None or before is None else value + before
        )
    return state


def new_goal(task, *, goal_id, next_step):
    from .validation import validate_checkpoint

    if task.get("schema_version") != 1:
        raise HarnessValidationError("new_goal expects public v1 checkpoint")
    task = validate_checkpoint(task)
    state = {
        "schema_version": 2,
        "task_id": task["task_id"],
        "goal_id": goal_id,
        "slice_id": 0,
        "task": task,
        "totals": {},
        "baseline": dict.fromkeys(TOTALS, 0),
        "usage": dict.fromkeys(USAGE, None),
        "accepted_evidence": [],
        "history": [],
        "next_step": next_step,
        "action_kind": "execute",
        "review_required": False,
        "requires_human": False,
        "source_sha256": canonical_sha256(task),
        "failure_history": [],
        "active_failure": None,
    }
    state = refresh_totals(state)
    return validate_goal_checkpoint(state)


def validate_goal_checkpoint(document):
    from .validation import validate_checkpoint

    _object(document, EXTRA, "goal checkpoint")
    if type(document["schema_version"]) is not int or document["schema_version"] != 2:
        raise HarnessValidationError("expected checkpoint v2")
    for key in ("task_id", "goal_id", "next_step", "source_sha256"):
        _text(document[key], key, empty=key == "next_step")
    if len(document["source_sha256"]) != 64 or any(
        c not in "0123456789abcdef" for c in document["source_sha256"]
    ):
        raise HarnessValidationError("invalid source hash")
    if (
        not isinstance(document["task"], dict)
        or document["task"].get("schema_version") != 1
    ):
        raise HarnessValidationError("task must be public v1")
    validate_checkpoint(document["task"])
    if document["task_id"] != document["task"]["task_id"]:
        raise HarnessValidationError("task_id mismatch")
    for key in ("review_required", "requires_human"):
        if type(document[key]) is not bool:
            raise HarnessValidationError(f"{key}: expected boolean")
    if document["action_kind"] not in ("execute", "diagnose", "review", "wait"):
        raise HarnessValidationError("unknown action kind")
    _number(document["slice_id"], "slice_id")
    for field, keys in [("totals", TOTALS), ("baseline", TOTALS), ("usage", USAGE)]:
        _object(document[field], keys, field)
        for key, value in document[field].items():
            _number(value, key, nullable=key in USAGE)
    expected = refresh_totals(document)["totals"]
    if document["totals"] != expected:
        raise HarnessValidationError("totals must equal baseline plus slice")
    for field in ("accepted_evidence", "history", "failure_history"):
        if not isinstance(document[field], list):
            raise HarnessValidationError(f"{field}: expected list")
    if any(
        not isinstance(ref, str) or not ref.strip()
        for ref in document["accepted_evidence"]
    ):
        raise HarnessValidationError("invalid accepted evidence")
    if len(document["accepted_evidence"]) != len(set(document["accepted_evidence"])):
        raise HarnessValidationError("duplicate accepted evidence")
    previous = None
    requests = set()
    for index, event in enumerate(document["history"]):
        _object(
            event,
            {
                "slice_id",
                "request_id",
                "previous_sha256",
                "sha256",
                "totals",
                "task_sha256",
                "evidence_refs",
            },
            "history event",
        )
        if event["slice_id"] != index or event["previous_sha256"] != previous:
            raise HarnessValidationError("history sequence or chain mismatch")
        _number(event["slice_id"], "history slice_id")
        _text(event["request_id"], "request_id")
        _hash(event["task_sha256"], "history task hash")
        if not isinstance(event["evidence_refs"], list) or any(
            not isinstance(ref, str) or not ref.strip()
            for ref in event["evidence_refs"]
        ):
            raise HarnessValidationError("invalid history evidence")
        if event["request_id"] in requests:
            raise HarnessValidationError("duplicate advance request")
        requests.add(event["request_id"])
        payload = {k: v for k, v in event.items() if k != "sha256"}
        if event["sha256"] != canonical_sha256(payload):
            raise HarnessValidationError("history hash mismatch")
        _object(event["totals"], TOTALS, "history totals")
        for k, v in event["totals"].items():
            _number(v, k, nullable=k in USAGE)
        if index:
            for k, v in event["totals"].items():
                prior = document["history"][index - 1]["totals"][k]
                if (
                    prior is None
                    and v is not None
                    or prior is not None
                    and v is not None
                    and v < prior
                ):
                    raise HarnessValidationError("history totals regressed")
        previous = event["sha256"]
    if len(document["history"]) != document["slice_id"]:
        raise HarnessValidationError("slice id does not match history")
    baseline = (
        document["history"][-1]["totals"]
        if document["history"]
        else dict.fromkeys(TOTALS, 0)
    )
    if document["baseline"] != baseline:
        raise HarnessValidationError("baseline differs from history")
    accepted = {ref for event in document["history"] for ref in event["evidence_refs"]}
    if set(document["accepted_evidence"]) != accepted:
        raise HarnessValidationError(
            "accepted evidence differs from transition receipts"
        )
    failure_ids = set()
    if document["active_failure"] is not None:
        _hash(document["active_failure"], "active_failure")
    for failure in document["failure_history"]:
        _object(
            failure,
            {
                "identity",
                "input_sha256",
                "error_class",
                "attempts",
                "evidence_ref",
                "observed_evidence",
            },
            "failure",
        )
        for key in ("identity", "input_sha256", "error_class", "evidence_ref"):
            _text(failure[key], key)
        _hash(failure["identity"], "failure identity")
        _hash(failure["input_sha256"], "failure input")
        _number(failure["attempts"], "attempts")
        refs = failure["observed_evidence"]
        if not isinstance(refs, list) or any(
            not isinstance(ref, str) or not ref.strip() for ref in refs
        ):
            raise HarnessValidationError("invalid failure observed_evidence")
        failure_id = canonical_sha256(
            [failure["identity"], failure["input_sha256"], failure["error_class"]]
        )
        if failure_id in failure_ids:
            raise HarnessValidationError("duplicate failure identity")
        failure_ids.add(failure_id)
        if (
            failure_id == document["active_failure"]
            and document["task"]["same_failure_retries"] < failure["attempts"] - 1
        ):
            raise HarnessValidationError("retry counter regressed from failure history")
    if (
        document["active_failure"] is not None
        and document["active_failure"] not in failure_ids
    ):
        raise HarnessValidationError("active failure missing from history")
    return deepcopy(document)


def _hash(value, label):
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise HarnessValidationError(f"{label}: expected SHA-256")


def record_failure(
    state, *, operation, target, input_sha256, error_class, evidence_ref
):
    """Record a failed action, independent of model, session, or slice names.

    Hosts must use stable operation/target identifiers and actual relevant-input
    hashes. This is accounting, not verification that an agent told the truth.
    """
    state = validate_goal_checkpoint(state)
    for name, value in [
        ("operation", operation),
        ("target", target),
        ("error_class", error_class),
        ("evidence_ref", evidence_ref),
    ]:
        _text(value, name)
    _hash(input_sha256, "input_sha256")
    identity = canonical_sha256([operation, target])
    record_id = canonical_sha256([identity, input_sha256, error_class])
    match = next(
        (
            f
            for f in state["failure_history"]
            if f["identity"] == identity
            and f["input_sha256"] == input_sha256
            and f["error_class"] == error_class
        ),
        None,
    )
    if match:
        match["attempts"] += 1
        match["evidence_ref"] = evidence_ref
        match["observed_evidence"] = sorted(
            set(match["observed_evidence"]) | set(state["task"]["evidence_refs"])
        )
    else:
        match = {
            "identity": identity,
            "input_sha256": input_sha256,
            "error_class": error_class,
            "attempts": 1,
            "evidence_ref": evidence_ref,
            "observed_evidence": list(state["task"]["evidence_refs"]),
        }
        state["failure_history"].append(match)
    prior = (
        state["task"]["same_failure_retries"]
        if state["active_failure"] in (None, record_id)
        else 0
    )
    state["task"]["same_failure_retries"] = max(prior, match["attempts"] - 1)
    state["active_failure"] = record_id
    return validate_goal_checkpoint(state)


def permit_corrected_attempt(state, *, input_sha256, evidence_ref):
    """Permit a bounded new input revision without deleting prior failures."""
    state = validate_goal_checkpoint(state)
    _hash(input_sha256, "input_sha256")
    if (
        not evidence_ref
        or evidence_ref not in state["task"]["evidence_refs"]
        or evidence_ref in state["accepted_evidence"]
    ):
        raise HarnessValidationError("corrected attempt requires new evidence")
    if state["active_failure"] is None:
        raise HarnessValidationError(
            "unclassified legacy failure requires diagnosis before retry"
        )
    failure = next(
        f
        for f in state["failure_history"]
        if canonical_sha256([f["identity"], f["input_sha256"], f["error_class"]])
        == state["active_failure"]
    )
    if input_sha256 == failure["input_sha256"]:
        raise HarnessValidationError(
            "renaming or switching models does not change failure inputs"
        )
    consumed = {
        ref
        for record in state["failure_history"]
        for ref in record["observed_evidence"]
    }
    consumed.update(record["evidence_ref"] for record in state["failure_history"])
    if evidence_ref in consumed:
        raise HarnessValidationError(
            "correction evidence predates failure or was already consumed"
        )
    failure["observed_evidence"].append(evidence_ref)
    # Restore an old revision's count if the caller returns to previously failed inputs.
    match = next(
        (
            f
            for f in state["failure_history"]
            if f["identity"] == failure["identity"]
            and f["input_sha256"] == input_sha256
            and f["error_class"] == failure["error_class"]
        ),
        None,
    )
    if match:
        state["active_failure"] = canonical_sha256(
            [match["identity"], input_sha256, match["error_class"]]
        )
        state["task"]["same_failure_retries"] = max(0, match["attempts"] - 1)
    else:
        match = {
            **failure,
            "input_sha256": input_sha256,
            "attempts": 0,
            "evidence_ref": evidence_ref,
        }
        state["failure_history"].append(match)
        state["active_failure"] = canonical_sha256(
            [match["identity"], input_sha256, match["error_class"]]
        )
        state["task"]["same_failure_retries"] = 0
    return validate_goal_checkpoint(state)


def migrate_goal(task, policy, *, goal_id, next_step, authorization_keys=None):
    """Explicitly migrate a v1 task; only proven slice-only exhaustion resumes."""
    from .policy import evaluate_policy

    policy = validate_goal_policy(policy)
    original = deepcopy(task)
    old = evaluate_policy(
        task, policy["base_policy"], authorization_keys=authorization_keys
    )
    if task["status"] == "budget_exhausted":
        allowed = (
            "task_status:budget_exhausted",
            "limit_reached:cycle=",
            "limit_reached:tool_calls=",
            "limit_reached:elapsed_seconds=",
            "limit_exceeded:children_spawned=",
        )
        # Do not clear an unrelated recorded blocker merely because a slice
        # counter also happens to be exhausted.
        reason = task.get("stop_reason")
        metric_reasons = [r for r in old.reasons if r != "task_status:budget_exhausted"]
        if (
            metric_reasons
            and all(r.startswith(allowed) for r in old.reasons)
            and reason in metric_reasons
        ):
            task = deepcopy(task)
            task["status"] = "running"
            task["stop_reason"] = None
    state = new_goal(task, goal_id=goal_id, next_step=next_step)
    state["source_sha256"] = canonical_sha256(original)
    return validate_goal_checkpoint(state)


@dataclass(frozen=True)
class GoalDecision(PolicyDecision):
    scope: str
    auto_continue: bool


def evaluate_goal(state, policy, *, authorization_keys=None):
    from .policy import evaluate_policy

    state = validate_goal_checkpoint(state)
    policy = validate_goal_policy(policy)
    task = deepcopy(state["task"])
    original = deepcopy(task)
    # Only these budgets become slice boundaries. Security, signed decisions,
    # hard context limits, and explicit terminal states retain their v1 gates.
    for key in ("cycle", "tool_calls", "elapsed_seconds", "children_spawned"):
        task[key] = 0
    if state["action_kind"] in ("diagnose", "wait"):
        task["same_failure_retries"] = 0
        task["no_evidence_cycles"] = 0
        if task["status"] in ("error", "timed_out"):
            task["status"] = "running"
    # Verify signatures and overrides against ORIGINAL observations first.
    evaluate_policy(
        original, policy["base_policy"], authorization_keys=authorization_keys
    )
    # Overrides refer to original observations; use their effective limits and
    # already-verified decisions, without altering any stored authorization.
    from .policy import _effective_limits, _observed_metrics

    effective = _effective_limits(
        original, policy["base_policy"], _observed_metrics(original)
    )
    task["overrides"] = []
    base = deepcopy(policy["base_policy"])
    base["limits"] = effective
    old = evaluate_policy(task, base, authorization_keys=authorization_keys)
    reasons = list(old.reasons)
    decision = old.decision
    scope = "goal" if decision == "stop" else "action"
    auto = False
    limit = effective
    if reasons and all(
        r in ("task_status:error", "task_status:timed_out")
        or r.startswith(
            (
                "limit_reached:same_failure_retries=",
                "limit_reached:no_evidence_cycles=",
                "limit_exceeded:active_children=",
            )
        )
        for r in reasons
    ):
        scope = "action"
    if state["requires_human"]:
        decision = "stop"
        scope = "goal"
        reasons.append("human_authorization_required")
    for key, maximum in policy["goal_limits"].items():
        observed = state["totals"][key]
        if observed is None or observed >= maximum:
            decision = "stop"
            scope = "goal"
            reasons.append(f"goal_limit:{key}:unknown_or_reached")
    if original["status"] == "completed" and (
        not original["evidence_refs"] or state["next_step"]
    ):
        decision = "stop"
        scope = "goal"
        reasons.append("completion_missing_acceptance_or_work_remains")
    children = original.get("children_spawned", 0)
    boundaries = [
        ("cycle", "max_cycles"),
        ("tool_calls", "max_tool_calls"),
        ("elapsed_seconds", "max_elapsed_seconds"),
        ("children_spawned", "max_children_per_parent"),
    ]
    reached = [key for key, cap in boundaries if original.get(key, 0) >= limit[cap]]
    if decision != "stop" and reached:
        decision = "checkpoint"
        scope = "slice"
        reasons += ["slice_limit:" + k for k in reached]
        fresh = set(original["evidence_refs"]) - set(state["accepted_evidence"])
        auto = bool(fresh and state["next_step"] and not original["active_children"])
        if not auto:
            reasons.append("slice_needs_evidence_next_step_or_children_completion")
    if original["active_children"] > limit["max_concurrency"]:
        scope = "goal" if decision == "stop" and scope == "goal" else "action"
        decision = "stop"
        auto = False
        reasons.append("concurrency_exceeded")
    reserved = (
        policy["reviewer_reserve"]
        if state["review_required"] and state["action_kind"] != "review"
        else 0
    )
    spawn = (
        decision == "continue"
        and old.spawn_allowed
        and children < limit["max_children_per_parent"] - reserved
        and state["action_kind"] != "wait"
    )
    return GoalDecision(
        2,
        policy["policy_id"],
        canonical_sha256(policy),
        decision,
        spawn,
        decision == "checkpoint",
        reasons,
        effective,
        state["totals"],
        scope,
        auto,
    )


def advance_checkpoint(state, policy, *, request_id, authorization_keys=None):
    state = validate_goal_checkpoint(state)
    _text(request_id, "request_id")
    if any(e["request_id"] == request_id for e in state["history"]):
        return state
    result = evaluate_goal(state, policy, authorization_keys=authorization_keys)
    if result.decision != "checkpoint" or not result.auto_continue:
        raise HarnessValidationError("advance not authorized by slice decision")
    event = {
        "slice_id": state["slice_id"],
        "request_id": request_id,
        "previous_sha256": state["history"][-1]["sha256"] if state["history"] else None,
        "totals": deepcopy(state["totals"]),
        "task_sha256": canonical_sha256(state["task"]),
        "evidence_refs": list(state["task"]["evidence_refs"]),
    }
    event["sha256"] = canonical_sha256(event)
    state["history"].append(event)
    state["slice_id"] += 1
    state["baseline"] = deepcopy(state["totals"])
    state["accepted_evidence"] = sorted(
        set(state["accepted_evidence"]) | set(state["task"]["evidence_refs"])
    )
    for key in COUNTERS:
        state["task"][key] = 0
    for key in USAGE:
        state["usage"][key] = 0
    # Signed overrides bind original observations; require explicit migration
    # rather than silently reusing them with reset slice counters.
    if state["task"]["overrides"]:
        raise HarnessValidationError(
            "signed slice overrides require explicit migration"
        )
    return validate_goal_checkpoint(refresh_totals(state))
