"""Public result models."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal


@dataclass(frozen=True)
class PolicyDecision:
    """The stable result of evaluating one TaskCheckpoint."""

    schema_version: int
    policy_id: str
    policy_hash: str | None
    decision: Literal["continue", "checkpoint", "stop"]
    spawn_allowed: bool
    checkpoint_required: bool
    reasons: list[str]
    effective_limits: dict[str, int]
    observed_metrics: dict[str, int | float]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serializable representation."""

        return asdict(self)
