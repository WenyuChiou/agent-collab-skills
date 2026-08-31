"""Read-only installation and configuration diagnostics."""

from __future__ import annotations

import json
import os
import platform
from importlib import resources
from pathlib import Path
from typing import Any

from . import __version__
from .errors import HarnessValidationError
from .io import load_human_authorization_keys, load_json_object
from .validation import validate_policy


SCHEMA_FILES = (
    "agent-policy-1.json",
    "task-checkpoint-1.json",
    "policy-decision-1.json",
)


def run_doctor() -> dict[str, Any]:
    """Return package and optional policy health without mutating state."""

    checks: list[dict[str, str]] = []
    schema_root = resources.files("agent_collab_harness.schemas")
    for name in SCHEMA_FILES:
        try:
            with schema_root.joinpath(name).open("r", encoding="utf-8") as handle:
                value = json.load(handle)
            if not isinstance(value, dict):
                raise ValueError("schema root is not an object")
            checks.append({"check": f"schema:{name}", "status": "OK", "detail": "loaded"})
        except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
            checks.append(
                {"check": f"schema:{name}", "status": "FAIL", "detail": str(exc)}
            )

    configured = os.environ.get("AGENT_COLLAB_POLICY")
    if configured:
        policy_path = Path(configured).expanduser()
        try:
            policy = validate_policy(load_json_object(policy_path))
            checks.append(
                {
                    "check": "configured_policy",
                    "status": "OK",
                    "detail": f"{policy['policy_id']} ({policy_path})",
                }
            )
        except HarnessValidationError as exc:
            checks.append(
                {
                    "check": "configured_policy",
                    "status": "FAIL",
                    "detail": str(exc),
                }
            )
    else:
        checks.append(
            {
                "check": "configured_policy",
                "status": "SKIP",
                "detail": "AGENT_COLLAB_POLICY is not set",
            }
        )

    raw_keys = os.environ.get("AGENT_COLLAB_HUMAN_KEYS_JSON")
    if raw_keys is None:
        checks.append(
            {
                "check": "human_authorization_keys",
                "status": "SKIP",
                "detail": "AGENT_COLLAB_HUMAN_KEYS_JSON is not set",
            }
        )
    else:
        try:
            keys = load_human_authorization_keys(raw_keys)
            checks.append(
                {
                    "check": "human_authorization_keys",
                    "status": "OK",
                    "detail": f"{len(keys)} key id(s) configured; secrets not displayed",
                }
            )
        except HarnessValidationError as exc:
            checks.append(
                {
                    "check": "human_authorization_keys",
                    "status": "FAIL",
                    "detail": str(exc),
                }
            )

    failed = any(item["status"] == "FAIL" for item in checks)
    return {
        "schema_version": 1,
        "status": "misconfigured" if failed else "ok",
        "package": "agent-collab-harness",
        "version": __version__,
        "python": platform.python_version(),
        "checks": checks,
    }
