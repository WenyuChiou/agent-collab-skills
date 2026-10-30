"""Regression cases for incremental future receipts and legacy history."""
from copy import deepcopy
import hashlib
import json
from unittest import mock

import pytest

from agent_collab_harness.checkpoint_store import advance_file
from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.goals import (
    advance_checkpoint,
    goal_policy,
    new_goal,
    refresh_totals,
    validate_goal_checkpoint,
)
from agent_collab_harness.io import canonical_sha256
from harness_samples import checkpoint, policy


def _policy():
    return goal_policy(policy())


def _ready(state=None, refs=("old:a",)):
    if state is None:
        state = new_goal(checkpoint(), goal_id="receipt-regression", next_step="continue")
    state = deepcopy(state)
    state["task"]["cycle"] = _policy()["base_policy"]["limits"]["max_cycles"]
    state["task"]["evidence_refs"] = list(refs)
    state["task"]["tool_calls"] = 1
    return refresh_totals(state)


def _legacy_fixture_transition(state, request_id):
    """Make a valid legacy cumulative receipt fixture, not an old executor."""
    result = advance_checkpoint(state, _policy(), request_id=request_id)
    event = result["history"][-1]
    event["evidence_refs"] = list(state["task"]["evidence_refs"])
    event["sha256"] = canonical_sha256({k: v for k, v in event.items() if k != "sha256"})
    return validate_goal_checkpoint(result)


def _seed_file(path, state):
    # Setup only: do not exercise native hard-link creation in this fixture.
    validate_goal_checkpoint(state)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(state, stream, sort_keys=True, indent=2)
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_fresh_reference_order_and_complete_task_hash():
    first = advance_checkpoint(_ready(), _policy(), request_id="first")
    prepared = _ready(first, ("new:z", "old:a", "new:b"))
    task_before = deepcopy(prepared["task"])
    result = advance_checkpoint(prepared, _policy(), request_id="second")
    event = result["history"][-1]
    assert event["evidence_refs"] == ["new:z", "new:b"]
    assert event["task_sha256"] == canonical_sha256(task_before)
    assert prepared["task"] == task_before  # Caller input was not mutated.
    assert result["accepted_evidence"] == ["new:b", "new:z", "old:a"]


def test_dropped_and_reintroduced_accepted_refs_are_not_new():
    s = advance_checkpoint(_ready(refs=("old:a", "old:b")), _policy(), request_id="one")
    s = advance_checkpoint(_ready(s, ("new:c",)), _policy(), request_id="two")
    assert s["history"][-1]["evidence_refs"] == ["new:c"]
    s = advance_checkpoint(_ready(s, ("old:b", "old:a", "new:d")), _policy(), request_id="three")
    assert s["history"][-1]["evidence_refs"] == ["new:d"]
    assert set(s["accepted_evidence"]) == {"old:a", "old:b", "new:c", "new:d"}


def test_duplicate_task_input_is_rejected_before_transition():
    state = _ready(refs=("duplicate", "duplicate"))
    before = deepcopy(state)
    with pytest.raises(HarnessValidationError):
        advance_checkpoint(state, _policy(), request_id="bad")
    assert state == before


def test_legacy_receipt_duplicates_remain_accepted_and_unchanged():
    legacy = _legacy_fixture_transition(_ready(), "legacy")
    event = legacy["history"][0]
    event["evidence_refs"].append("old:a")
    event["sha256"] = canonical_sha256({k: v for k, v in event.items() if k != "sha256"})
    validate_goal_checkpoint(legacy)
    old_event = deepcopy(event)
    result = advance_checkpoint(_ready(legacy, ("old:a", "new:b")), _policy(), request_id="new")
    assert result["history"][0] == old_event
    assert result["history"][1]["evidence_refs"] == ["new:b"]


def test_old_incremental_old_receipt_sequence_preserves_old_hashes():
    s = _legacy_fixture_transition(_ready(), "old-one")
    s = _legacy_fixture_transition(_ready(s, ("old:a", "old:b")), "old-two")
    original = deepcopy(s["history"])
    s = advance_checkpoint(_ready(s, ("old:a", "old:b", "new:c")), _policy(), request_id="new")
    assert s["history"][:2] == original
    assert s["history"][2]["evidence_refs"] == ["new:c"]
    s = _legacy_fixture_transition(_ready(s, ("old:a", "old:b", "new:c", "last:d")), "old-again")
    assert s["history"][:2] == original
    assert s["history"][-1]["evidence_refs"] == ["old:a", "old:b", "new:c", "last:d"]
    assert set(s["accepted_evidence"]) == {"old:a", "old:b", "new:c", "last:d"}
    validate_goal_checkpoint(s)


@pytest.mark.parametrize("rehash", [False, True])
def test_removed_history_reference_is_rejected(rehash):
    s = _legacy_fixture_transition(_ready(refs=("old:a", "old:b")), "old")
    event = s["history"][0]
    event["evidence_refs"].remove("old:b")
    if rehash:
        event["sha256"] = canonical_sha256({k: v for k, v in event.items() if k != "sha256"})
    with pytest.raises(HarnessValidationError, match="accepted evidence differs|history hash mismatch"):
        validate_goal_checkpoint(s)


def test_each_future_receipt_has_only_fixed_size_new_refs():
    state = None
    refs = []
    for n in range(16):
        refs.append(f"fixture:{n:04d}")
        state = advance_checkpoint(_ready(state, refs), _policy(), request_id=f"r:{n:04d}")
    assert [len(e["evidence_refs"]) for e in state["history"]] == [1] * 16
    assert state["accepted_evidence"] == refs
    assert state["totals"]["tool_calls"] == 16
    assert state["totals"]["cost_microusd"] is None


def test_store_duplicate_request_and_stale_cas(tmp_path):
    path = tmp_path / "checkpoint.json"
    original_hash = _seed_file(path, _ready())
    first = advance_file(path, _policy(), "one", original_hash)
    published = path.read_bytes()
    with mock.patch("agent_collab_harness.checkpoint_store._write_temp", side_effect=AssertionError("duplicate write")):
        assert advance_file(path, _policy(), "one", original_hash) == first
    assert path.read_bytes() == published
    with pytest.raises(HarnessValidationError, match="hash conflict"):
        advance_file(path, _policy(), "different", original_hash)
    assert path.read_bytes() == published


def test_store_prepublication_failure_preserves_input(tmp_path):
    path = tmp_path / "checkpoint.json"
    original_hash = _seed_file(path, _ready())
    original = path.read_bytes()
    with mock.patch("agent_collab_harness.checkpoint_store.os.replace", side_effect=OSError("injected")):
        with pytest.raises(OSError, match="injected"):
            advance_file(path, _policy(), "one", original_hash)
    assert path.read_bytes() == original
    assert list(tmp_path.glob(".checkpoint.json.*.tmp")) == []


def test_store_postpublication_recovery_uses_same_request_id(tmp_path):
    path = tmp_path / "checkpoint.json"
    original_hash = _seed_file(path, _ready())
    with mock.patch("agent_collab_harness.checkpoint_store._sync_directory", side_effect=OSError("injected")):
        with pytest.raises(OSError, match="injected"):
            advance_file(path, _policy(), "one", original_hash)
    published = path.read_bytes()
    result = advance_file(path, _policy(), "one", original_hash)
    assert result["slice_id"] == 1
    assert len(result["history"]) == 1
    assert path.read_bytes() == published
