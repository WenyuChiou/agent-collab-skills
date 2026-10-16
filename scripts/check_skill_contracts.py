#!/usr/bin/env python3
"""Check that skill descriptions, redirect stubs, and gate presets agree.

Standard library only. Exit code 0 when every check passes, 1 otherwise.

    python scripts/check_skill_contracts.py
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
GATE = "agent-acceptance-gate"
STUB_REMOVAL_VERSION = "0.7.0"

# Active skills: SKILL.md byte cap and terms the description must contain so it
# fires on the situation (about to fan out, about to commit), not only on a
# user request.
ACTIVE = {
    "agent-task-splitter": (8192, ("subagents", "model tier", "disjoint", "merge")),
    "agent-context-budget": (7168, ("subagents", "summary", "cheap model tier")),
    "agent-debate": (4608, ("two plausible", "round cap")),
    GATE: (8192, ("commit or push", "subagent", "PASS", "FAIL")),
}

# Redirect stubs kept for one release: stub name -> skill that replaces it.
STUBS = {
    "agent-output-reconciler": GATE,
    "agent-shared-memory": "agent-context-budget",
    "agent-plan-act-reflect": "agent-context-budget",
}
STUB_MAX_BYTES = 1536

PRESET_ROW = re.compile(r"^\|\s*(.+?)\s*\|\s*`([a-z0-9-]+)`\s*\|\s*$")
REQUEST_ONLY = re.compile(
    r"\b(the|a) user (asks|requests)\b|\bwhen asked\b", re.IGNORECASE
)


def _has_term(description: str, term: str) -> bool:
    """Word-boundary match so 'bypass' does not count as 'PASS'."""
    return re.search(rf"\b{re.escape(term)}\b", description, re.IGNORECASE) is not None


def _frontmatter(text: str) -> dict[str, str] | None:
    text = text.replace("\r\n", "\n")
    if not text.startswith("---\n"):
        return None
    end = text.find("\n---\n", 4)
    if end < 0:
        return None
    fields: dict[str, str] = {}
    for line in text[4:end].splitlines():
        key, sep, value = line.partition(":")
        if sep and key and not key.startswith((" ", "\t")):
            fields[key.strip()] = value.strip()
    return fields


def _scalar(text: str, key: str) -> str | None:
    match = re.search(rf'^\s+{key}:\s*"([^"]*)"\s*$', text, re.MULTILINE)
    return match.group(1) if match else None


def _check_frontmatter(name: str, text: str, errors: list[str]) -> str:
    fields = _frontmatter(text)
    if fields is None:
        errors.append(f"{name}: SKILL.md has no YAML frontmatter")
        return ""
    if fields.get("name") != name:
        errors.append(f"{name}: frontmatter name is {fields.get('name')!r}")
    description = fields.get("description", "")
    if not description.startswith("Use when"):
        errors.append(f"{name}: description must start with 'Use when'")
    quoted = description[:1] in {'"', "'"}
    if ": " in description and not quoted:
        errors.append(f"{name}: unquoted ': ' in description breaks YAML")
    if " #" in description and not quoted:
        errors.append(f"{name}: unquoted ' #' in description starts a YAML comment")
    return description


def check() -> list[str]:
    errors: list[str] = []
    found = {p.parent.name for p in SKILLS.glob("*/SKILL.md")}
    expected = set(ACTIVE) | set(STUBS)
    if found != expected:
        errors.append(
            f"skill directories {sorted(found)} != expected {sorted(expected)}"
        )

    for name, (max_bytes, terms) in ACTIVE.items():
        path = SKILLS / name / "SKILL.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        description = _check_frontmatter(name, text, errors)
        if size > max_bytes:
            errors.append(f"{name}: SKILL.md is {size} bytes (cap {max_bytes})")
        for term in terms:
            if not _has_term(description, term):
                errors.append(f"{name}: description lacks situational term {term!r}")
        if REQUEST_ONLY.search(description):
            errors.append(f"{name}: description waits for a user request")

    for name, target in STUBS.items():
        path = SKILLS / name / "SKILL.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        size = len(text.encode("utf-8"))
        description = _check_frontmatter(name, text, errors)
        if size > STUB_MAX_BYTES:
            errors.append(f"{name}: stub is {size} bytes (cap {STUB_MAX_BYTES})")
        if STUB_REMOVAL_VERSION not in description:
            errors.append(f"{name}: stub description must name removal in {STUB_REMOVAL_VERSION}")
        if target not in text:
            errors.append(f"{name}: stub does not point to {target}")
        if target not in ACTIVE:
            errors.append(f"{name}: stub target {target} is not an active skill")

    for path in sorted(SKILLS.glob("*/SKILL.md")) + sorted(SKILLS.glob("*/references/*.md")):
        if "gemini" in path.read_text(encoding="utf-8").lower():
            errors.append(f"{path.relative_to(ROOT)}: mentions the archived Gemini lane")

    errors.extend(_check_presets())
    return errors


def _check_presets() -> list[str]:
    errors: list[str] = []
    gate_text = (SKILLS / GATE / "SKILL.md").read_text(encoding="utf-8")
    description = (_frontmatter(gate_text) or {}).get("description", "").lower()
    table = {
        match.group(2): match.group(1)
        for match in map(PRESET_ROW.match, gate_text.replace("\r\n", "\n").splitlines())
        if match
    }
    presets = sorted((SKILLS / GATE / "presets").glob("*.yml"))
    names = {p.stem for p in presets}
    if set(table) != names:
        errors.append(
            f"{GATE}: preset table {sorted(table)} != preset files {sorted(names)}"
        )
    for preset in presets:
        text = preset.read_text(encoding="utf-8")
        match = re.search(r"^preset_name:\s*(\S+)\s*$", text, re.MULTILINE)
        if not match or match.group(1) != preset.stem:
            errors.append(f"{preset.name}: preset_name must equal the file stem")
        keyword = _scalar(text, "description_keyword")
        situation = _scalar(text, "situation")
        if not keyword or not situation:
            errors.append(f"{preset.name}: needs trigger.situation and trigger.description_keyword")
            continue
        if keyword.lower() not in description:
            errors.append(f"{preset.name}: gate description lacks trigger keyword {keyword!r}")
        row = table.get(preset.stem, "")
        if keyword.lower() not in row.lower():
            errors.append(f"{preset.name}: gate preset-table row lacks trigger keyword {keyword!r}")
    return errors


def main() -> int:
    errors = check()
    for error in errors:
        print(f"FAIL {error}")
    if not errors:
        print(f"OK {len(ACTIVE)} active skills, {len(STUBS)} redirect stubs, presets in sync")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
