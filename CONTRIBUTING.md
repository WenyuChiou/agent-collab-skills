# Contributing

Agent Collab has two public surfaces that must move together:

1. the seven skills under `skills/`;
2. the `agent-collab-harness` Python package and `agent-collab` CLI.

## Contracts

- Use provider-neutral roles: `primary-agent`, `delegated-executor`,
  `reviewer`, and `synthesizer`.
- Keep numeric limits in one canonical machine-readable policy. Skill prose,
  samples, and host adapters must not copy policy defaults.
- Treat `.coord/` and `.ai/` as scratch. Only explicitly promoted checkpoint,
  shipping, or acceptance artifacts belong in version control.
- Memory output is proposal-only. Canonical changes require a recorded human
  decision and append a new immutable event.
- Preserve declined, cancelled, timeout, degraded, failed, and missing states.
  Never normalize them to success.
- Configured policy failures are fail closed. No silent retry, provider/model
  switch, or context discard.

See `docs/public-harness-contract.md` and `docs/migration-0.4.md` before changing
schemas or behavior.

## Skill changes

Every `SKILL.md` must:

- have valid YAML frontmatter;
- use a directory-matching `name`;
- start its description with `Use when`;
- state inputs, outputs, policy boundary, and prohibited mutations;
- avoid provider-specific routing in the public contract.

Run the skill validator for every changed skill directory.

## Package changes

The runtime remains standard-library first and supports Python 3.10 or newer.
Keep CLI commands and exit codes stable unless a migration and rollback path are
approved:

- `agent-collab policy validate`
- `agent-collab policy evaluate`
- `agent-collab checkpoint validate`
- `agent-collab doctor`

Reference JSON schemas and programmatic validators must agree on fields and
local structural constraints. The CLI validator is authoritative for semantic
rules that Draft 2020-12 cannot express, including cross-field ordering and
unique override limits. Reject duplicate JSON keys and unexpected fields.

## Tests

```bash
python -m pip install -e .
python -m pytest -q
python -m compileall -q src
agent-collab doctor --json
```

For bilingual changes, verify English and zh-TW terminology and structural
parity. For catalog, locale, or factual benchmark changes, run the matching
acceptance preset as well as independent review.

## Pull requests

- Use a focused branch and preserve unrelated worktree changes.
- Stage explicit paths only.
- Report exact commands, pass/fail/skip counts, environment, duration, and
  commit SHA.
- Document schema migrations and rollback.
- Do not merge, release, tag, or delete branches from an implementation task
  unless the authorized maintainer explicitly owns that gate.
