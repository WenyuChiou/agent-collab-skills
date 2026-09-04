from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
from unittest import mock

import pytest

from agent_collab_harness.checkpoint_store import (
    _exclusive_lock,
    advance_file,
    create_file,
)
from agent_collab_harness.errors import HarnessValidationError
from agent_collab_harness.goals import goal_policy, new_goal
from harness_samples import checkpoint, policy


def ready_state():
    task = checkpoint(cycle=3, evidence_refs=["test:passing"])
    return new_goal(task, goal_id="goal-store", next_step="continue")


def store_policy():
    return goal_policy(policy())


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _advance_worker(path: str, request_id: str, expected: str, queue) -> None:
    try:
        result = advance_file(path, store_policy(), request_id, expected)
        queue.put(("ok", result["slice_id"]))
    except Exception as exc:  # process boundary returns evidence, not exceptions
        queue.put(("error", type(exc).__name__, str(exc)))


def _crash_with_lock(path: str, ready) -> None:
    with _exclusive_lock(Path(path)):
        ready.set()
        os._exit(23)


def test_create_and_advance_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    created = create_file(path, ready_state())
    updated = advance_file(path, store_policy(), "request-1", file_hash(path))
    assert created["slice_id"] == 0
    assert updated["slice_id"] == 1
    assert json.loads(path.read_text(encoding="utf-8")) == updated


def test_duplicate_request_wins_over_old_expected_hash(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    old_hash = file_hash(path)
    first = advance_file(path, store_policy(), "same-request", old_hash)
    second = advance_file(path, store_policy(), "same-request", old_hash)
    assert second == first


def test_concurrent_duplicate_request_is_idempotent(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    expected = file_hash(path)
    context = multiprocessing.get_context("spawn")
    queue = context.Queue()
    processes = [context.Process(target=_advance_worker, args=(str(path), "shared", expected, queue)) for _ in range(2)]
    for process in processes:
        process.start()
    for process in processes:
        process.join(10)
        assert process.exitcode == 0
    results = [queue.get(timeout=2) for _ in processes]
    # Nonblocking lock contention may fail closed; every successful observation
    # is the same single transition and no second history event is created.
    assert any(item[0] == "ok" for item in results)
    assert len(json.loads(path.read_text(encoding="utf-8"))["history"]) == 1


def test_crashed_process_releases_os_lock(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    context = multiprocessing.get_context("spawn")
    ready = context.Event()
    process = context.Process(target=_crash_with_lock, args=(str(path), ready))
    process.start()
    assert ready.wait(5)
    process.join(5)
    assert process.exitcode == 23
    assert advance_file(path, store_policy(), "after-crash")["slice_id"] == 1


def test_lock_conflict_fails_closed_without_retry(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    with _exclusive_lock(path):
        with pytest.raises(HarnessValidationError, match="lock conflict"):
            advance_file(path, store_policy(), "blocked")


def test_invalid_json_and_hash_conflict_fail_closed(tmp_path: Path) -> None:
    invalid = tmp_path / "invalid.json"
    invalid.write_text('{"a":1,"a":2}', encoding="utf-8")
    with pytest.raises(HarnessValidationError, match="duplicate JSON key"):
        advance_file(invalid, store_policy(), "bad")
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    with pytest.raises(HarnessValidationError, match="hash conflict"):
        advance_file(path, store_policy(), "stale", "0" * 64)


def test_replace_failure_preserves_original_and_cleans_temp(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    original = path.read_bytes()
    with mock.patch("agent_collab_harness.checkpoint_store.os.replace", side_effect=OSError("injected")):
        with pytest.raises(OSError, match="injected"):
            advance_file(path, store_policy(), "replace-fails")
    assert path.read_bytes() == original
    assert list(tmp_path.glob(f".{path.name}.*.tmp")) == []


def test_partial_temp_is_never_loaded_as_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    partial = tmp_path / f".{path.name}.abandoned.tmp"
    partial.write_text('{"partial":', encoding="utf-8")
    assert advance_file(path, store_policy(), "ignores-partial")["slice_id"] == 1
    assert partial.exists()


def test_create_never_overwrites_existing_checkpoint(tmp_path: Path) -> None:
    path = tmp_path / "goal.json"
    create_file(path, ready_state())
    original = path.read_bytes()
    with pytest.raises(HarnessValidationError, match="already exists"):
        create_file(path, ready_state())
    assert path.read_bytes() == original


def test_symlink_checkpoint_is_rejected(tmp_path: Path) -> None:
    target = tmp_path / "target.json"
    create_file(target, ready_state())
    link = tmp_path / "link.json"
    try:
        link.symlink_to(target)
    except OSError as exc:
        pytest.skip(f"symlink unavailable: {exc}")
    with pytest.raises(HarnessValidationError, match="symlink or reparse"):
        advance_file(link, store_policy(), "linked")
