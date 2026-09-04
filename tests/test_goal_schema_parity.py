from __future__ import annotations

from copy import deepcopy
from importlib import resources

import pytest
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.goals import (
    advance_checkpoint,
    evaluate_goal,
    goal_policy,
    new_goal,
    permit_corrected_attempt,
    record_failure,
    validate_goal_checkpoint,
    validate_goal_policy,
)
from harness_samples import checkpoint, policy


SCHEMAS = ("agent-policy-1.json", "task-checkpoint-1.json", "agent-policy-2.json", "task-checkpoint-2.json", "policy-decision-2.json")


def schema_bundle():
    root = resources.files("agent_collab_harness.schemas")
    documents = {name: __import__("json").loads(root.joinpath(name).read_text(encoding="utf-8")) for name in SCHEMAS}
    registry = Registry().with_resources((document["$id"], Resource.from_contents(document)) for document in documents.values())
    return documents, registry


def validator(name: str) -> Draft202012Validator:
    documents, registry = schema_bundle()
    return Draft202012Validator(documents[name], registry=registry)


def ready(**changes):
    return new_goal(checkpoint(evidence_refs=["test:passing"], **changes), goal_id="goal-1", next_step="continue")


def test_v2_schemas_are_valid_and_resolve_only_bundled_v1_resources() -> None:
    documents, registry = schema_bundle()
    for document in documents.values():
        Draft202012Validator.check_schema(document)
    validator("agent-policy-2.json").validate(goal_policy(policy()))
    validator("task-checkpoint-2.json").validate(ready())


def test_advanced_history_and_prepared_failure_match_checkpoint_schema() -> None:
    state = advance_checkpoint(ready(cycle=3), goal_policy(policy()), request_id="slice-1")
    state = record_failure(state, operation="test", target="suite", input_sha256="a" * 64, error_class="assertion", evidence_ref="failure:1")
    state["task"]["evidence_refs"].append("fix:prepared")
    state = permit_corrected_attempt(state, input_sha256="b" * 64, evidence_ref="fix:prepared")
    assert state["failure_history"][-1]["attempts"] == 0
    validator("task-checkpoint-2.json").validate(state)
    validate_goal_checkpoint(state)


def test_goal_decision_matches_v2_schema_with_unknown_usage() -> None:
    decision = evaluate_goal(ready(cycle=3), goal_policy(policy())).to_dict()
    assert decision["observed_metrics"]["cost_microusd"] is None
    validator("policy-decision-2.json").validate(decision)


def test_fractional_elapsed_seconds_match_schema_and_python() -> None:
    state = ready(elapsed_seconds=3.5)
    policy_value = goal_policy(policy(), goal_limits={"elapsed_seconds": 10.5})
    validator("task-checkpoint-2.json").validate(state)
    validator("agent-policy-2.json").validate(policy_value)
    validate_goal_checkpoint(state)
    validate_goal_policy(policy_value)
    validator("policy-decision-2.json").validate(evaluate_goal(state, policy_value).to_dict())


@pytest.mark.parametrize(
    ("mutate", "python_validator"),
    [
        (lambda value: value.__setitem__("reviewer_reserve", True), validate_goal_policy),
        (lambda value: value.__setitem__("policy_id", "   "), validate_goal_policy),
        (lambda value: value.__setitem__("unexpected", 1), validate_goal_policy),
    ],
)
def test_invalid_policy_rejected_by_schema_and_python(mutate, python_validator) -> None:
    value = goal_policy(policy())
    mutate(value)
    assert not validator("agent-policy-2.json").is_valid(value)
    with pytest.raises(HarnessValidationError):
        python_validator(value)


@pytest.mark.parametrize(
    "mutate",
    [
        lambda value: value.__setitem__("slice_id", True),
        lambda value: value.__setitem__("goal_id", ""),
        lambda value: value.__setitem__("unexpected", None),
        lambda value: value["totals"].__setitem__("cycle", None),
        lambda value: value.__setitem__("review_required", 1),
    ],
)
def test_invalid_checkpoint_rejected_by_schema_and_python(mutate) -> None:
    value = ready()
    mutate(value)
    assert not validator("task-checkpoint-2.json").is_valid(value)
    with pytest.raises(HarnessValidationError):
        validate_goal_checkpoint(value)


def test_decision_schema_rejects_invalid_bool_null_empty_and_extra() -> None:
    source = evaluate_goal(ready(), goal_policy(policy())).to_dict()
    variants = []
    for field, invalid in (("auto_continue", 0), ("scope", None), ("policy_id", "")):
        value = deepcopy(source)
        value[field] = invalid
        variants.append(value)
    extra = deepcopy(source)
    extra["unexpected"] = True
    variants.append(extra)
    for value in variants:
        assert not validator("policy-decision-2.json").is_valid(value)
