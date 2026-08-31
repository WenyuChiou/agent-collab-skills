"""Strict JSON loading and canonical hashing helpers."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .errors import HarnessValidationError


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise HarnessValidationError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json_object(path: str | Path) -> dict[str, Any]:
    """Load a strict JSON object.

    The file extension is intentionally irrelevant. A .yaml policy is
    accepted only when its contents are valid JSON, keeping the runtime
    standard-library-only and the machine-readable source unambiguous.
    """

    candidate = Path(path)
    try:
        with candidate.open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_reject_duplicate_keys)
    except HarnessValidationError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HarnessValidationError(f"cannot read JSON object {candidate}: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessValidationError(f"expected JSON object: {candidate}")
    return value


def canonical_sha256(value: dict[str, Any]) -> str:
    """Return the SHA-256 of canonical UTF-8 JSON bytes."""

    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def load_human_authorization_keys(raw: str | None) -> dict[str, str]:
    """Parse the trusted host's in-memory HMAC key map without logging secrets."""

    if raw is None:
        return {}
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_keys)
    except HarnessValidationError:
        raise
    except json.JSONDecodeError as exc:
        raise HarnessValidationError(
            "AGENT_COLLAB_HUMAN_KEYS_JSON must be a JSON object"
        ) from exc
    if not isinstance(value, dict):
        raise HarnessValidationError(
            "AGENT_COLLAB_HUMAN_KEYS_JSON must be a JSON object"
        )
    result: dict[str, str] = {}
    for key_id, secret in value.items():
        if not isinstance(key_id, str) or not key_id or any(
            char.isspace() for char in key_id
        ):
            raise HarnessValidationError(
                "human authorization key ids must be non-empty and contain no whitespace"
            )
        if not isinstance(secret, str) or not secret:
            raise HarnessValidationError(
                f"human authorization secret must be non-empty: {key_id}"
            )
        result[key_id] = secret
    return result
