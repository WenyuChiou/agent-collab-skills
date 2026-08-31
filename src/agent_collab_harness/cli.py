"""Command-line interface for the public harness contract."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Sequence

from .doctor import run_doctor
from .errors import HarnessValidationError
from .io import canonical_sha256, load_human_authorization_keys, load_json_object
from .policy import evaluate_policy, fail_closed_decision
from .validation import validate_checkpoint, validate_policy


EXIT_OK = 0
EXIT_INVALID = 2
EXIT_CHECKPOINT = 3
EXIT_STOP = 4


def _emit(value: dict[str, Any]) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True))


def _validation_error(kind: str, path: Path, error: Exception) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "ok": False,
        "kind": kind,
        "path": str(path),
        "errors": [str(error)],
    }


def _policy_validate(args: argparse.Namespace) -> int:
    try:
        source_policy = load_json_object(args.policy)
        policy = validate_policy(source_policy)
    except HarnessValidationError as exc:
        _emit(_validation_error("policy", args.policy, exc))
        return EXIT_INVALID
    _emit(
        {
            "schema_version": 1,
            "ok": True,
            "kind": "policy",
            "path": str(args.policy),
            "policy_id": policy["policy_id"],
            "policy_hash": canonical_sha256(source_policy),
            "errors": [],
        }
    )
    return EXIT_OK


def _policy_evaluate(args: argparse.Namespace) -> int:
    try:
        checkpoint = load_json_object(args.checkpoint)
        policy = load_json_object(args.policy)
        result = evaluate_policy(
            checkpoint,
            policy,
            authorization_keys=load_human_authorization_keys(
                os.environ.get("AGENT_COLLAB_HUMAN_KEYS_JSON")
            ),
        )
    except HarnessValidationError as exc:
        fail_closed_policy_id = args.policy.stem.strip() or "unreadable-policy"
        result = fail_closed_decision(
            policy_id=fail_closed_policy_id,
            reason=str(exc),
        )
    _emit(result.to_dict())
    if result.decision == "stop":
        return EXIT_STOP
    if result.decision == "checkpoint":
        return EXIT_CHECKPOINT
    return EXIT_OK


def _checkpoint_validate(args: argparse.Namespace) -> int:
    try:
        checkpoint = validate_checkpoint(load_json_object(args.checkpoint))
    except HarnessValidationError as exc:
        _emit(_validation_error("checkpoint", args.checkpoint, exc))
        return EXIT_INVALID
    _emit(
        {
            "schema_version": 1,
            "ok": True,
            "kind": "checkpoint",
            "path": str(args.checkpoint),
            "task_id": checkpoint["task_id"],
            "errors": [],
        }
    )
    return EXIT_OK


def _doctor(_args: argparse.Namespace) -> int:
    result = run_doctor()
    _emit(result)
    return EXIT_OK if result["status"] == "ok" else EXIT_INVALID


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="agent-collab",
        description="Validate and evaluate bounded agent policy checkpoints.",
    )
    subparsers = parser.add_subparsers(dest="group", required=True)

    policy = subparsers.add_parser("policy", help="Policy operations")
    policy_commands = policy.add_subparsers(dest="command", required=True)
    policy_validate = policy_commands.add_parser("validate", help="Validate a policy")
    policy_validate.add_argument("--policy", required=True, type=Path)
    policy_validate.add_argument("--json", action="store_true")
    policy_validate.set_defaults(handler=_policy_validate)

    policy_evaluate = policy_commands.add_parser(
        "evaluate", help="Evaluate a checkpoint against a policy"
    )
    policy_evaluate.add_argument("--policy", required=True, type=Path)
    policy_evaluate.add_argument("--checkpoint", required=True, type=Path)
    policy_evaluate.add_argument("--json", action="store_true")
    policy_evaluate.set_defaults(handler=_policy_evaluate)

    checkpoint = subparsers.add_parser("checkpoint", help="Checkpoint operations")
    checkpoint_commands = checkpoint.add_subparsers(dest="command", required=True)
    checkpoint_validate = checkpoint_commands.add_parser(
        "validate", help="Validate a TaskCheckpoint"
    )
    checkpoint_validate.add_argument("--checkpoint", required=True, type=Path)
    checkpoint_validate.add_argument("--json", action="store_true")
    checkpoint_validate.set_defaults(handler=_checkpoint_validate)

    doctor = subparsers.add_parser("doctor", help="Inspect package configuration")
    doctor.add_argument("--json", action="store_true")
    doctor.set_defaults(handler=_doctor)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return int(args.handler(args))


if __name__ == "__main__":
    raise SystemExit(main())
