"""Crash-safe local persistence for v2 goal checkpoints.

This module serializes checkpoint state transitions only.  It never executes an
agent action and does not provide exactly-once semantics for external effects.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator, Mapping

from .errors import HarnessValidationError
from .goals import advance_checkpoint, validate_goal_checkpoint
from .io import load_json_object


def _absolute(path: str | Path) -> Path:
    return Path(os.path.abspath(os.fspath(path)))


def _is_reparse(info: os.stat_result) -> bool:
    flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(getattr(info, "st_file_attributes", 0) & flag)


def _validate_components(path: Path) -> None:
    """Reject links/reparse points in every existing path component."""
    current = Path(path.anchor)
    for part in path.parts[1:]:
        current /= part
        try:
            info = os.lstat(current)
        except FileNotFoundError:
            continue
        except OSError as exc:
            raise HarnessValidationError(f"cannot inspect checkpoint path {current}: {exc}") from exc
        if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
            raise HarnessValidationError(f"checkpoint path contains a symlink or reparse point: {current}")


def _require_regular_file(path: Path) -> None:
    _validate_components(path)
    try:
        info = os.lstat(path)
    except OSError as exc:
        raise HarnessValidationError(f"cannot inspect checkpoint file {path}: {exc}") from exc
    if not stat.S_ISREG(info.st_mode):
        raise HarnessValidationError(f"checkpoint is not a regular file: {path}")


def _lock_path(path: Path) -> Path:
    return path.with_name(path.name + ".lock")


@contextmanager
def _exclusive_lock(path: Path) -> Iterator[None]:
    lock_path = _lock_path(path)
    _validate_components(lock_path)
    try:
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(lock_path, flags, 0o600)
    except OSError as exc:
        raise HarnessValidationError(f"cannot open checkpoint lock {lock_path}: {exc}") from exc
    try:
        if not stat.S_ISREG(os.fstat(descriptor).st_mode):
            raise HarnessValidationError(f"checkpoint lock is not a regular file: {lock_path}")
        if os.name == "nt":
            import msvcrt

            if os.fstat(descriptor).st_size == 0:
                os.write(descriptor, b"\0")
            os.lseek(descriptor, 0, os.SEEK_SET)
            try:
                msvcrt.locking(descriptor, msvcrt.LK_NBLCK, 1)
            except OSError as exc:
                raise HarnessValidationError(f"checkpoint lock conflict: {lock_path}") from exc
        else:
            import fcntl

            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError as exc:
                raise HarnessValidationError(f"checkpoint lock conflict: {lock_path}") from exc
        yield
    finally:
        try:
            if os.name == "nt":
                import msvcrt

                os.lseek(descriptor, 0, os.SEEK_SET)
                msvcrt.locking(descriptor, msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(descriptor, fcntl.LOCK_UN)
        except OSError:
            pass
        os.close(descriptor)


def _bytes(state: dict[str, Any]) -> bytes:
    return (json.dumps(state, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode("utf-8")


def _write_temp(path: Path, payload: bytes) -> Path:
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        return temporary
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _sync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _validate_expected(value: str | None) -> None:
    if value is not None and (len(value) != 64 or any(char not in "0123456789abcdef" for char in value)):
        raise HarnessValidationError("expected_sha256 must be a lowercase SHA-256 digest")


def advance_file(
    path: str | Path,
    policy: dict[str, Any],
    request_id: str,
    expected_sha256: str | None = None,
    authorization_keys: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Lock, validate, and atomically advance one checkpoint file."""
    checkpoint = _absolute(path)
    _validate_expected(expected_sha256)
    with _exclusive_lock(checkpoint):
        _require_regular_file(checkpoint)
        try:
            raw = checkpoint.read_bytes()
        except OSError as exc:
            raise HarnessValidationError(f"cannot read checkpoint file {checkpoint}: {exc}") from exc
        state = validate_goal_checkpoint(load_json_object(checkpoint))
        if any(event["request_id"] == request_id for event in state["history"]):
            return state
        actual_hash = hashlib.sha256(raw).hexdigest()
        if expected_sha256 is not None and actual_hash != expected_sha256:
            raise HarnessValidationError(f"checkpoint hash conflict: expected {expected_sha256}, found {actual_hash}")
        updated = advance_checkpoint(state, policy, request_id=request_id, authorization_keys=authorization_keys)
        temporary = _write_temp(checkpoint, _bytes(updated))
        try:
            os.replace(temporary, checkpoint)
            _sync_directory(checkpoint.parent)
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
        return updated


def create_file(path: str | Path, state: dict[str, Any]) -> dict[str, Any]:
    """Validate and atomically publish a new checkpoint without overwriting."""
    checkpoint = _absolute(path)
    validated = validate_goal_checkpoint(state)
    _validate_components(checkpoint)
    if not checkpoint.parent.exists() or not checkpoint.parent.is_dir():
        raise HarnessValidationError(f"checkpoint parent is not an existing directory: {checkpoint.parent}")
    with _exclusive_lock(checkpoint):
        _validate_components(checkpoint)
        if checkpoint.exists():
            raise HarnessValidationError(f"checkpoint already exists: {checkpoint}")
        temporary = _write_temp(checkpoint, _bytes(validated))
        try:
            os.link(temporary, checkpoint)
            temporary.unlink()
            _sync_directory(checkpoint.parent)
        except FileExistsError as exc:
            temporary.unlink(missing_ok=True)
            raise HarnessValidationError(f"checkpoint already exists: {checkpoint}") from exc
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    return validated
