# Claude Code Plugin Marketplace — `agent-collab-skills`

Marketplace configuration for the `agent-collab-skills` catalog. For
end-user install instructions, see [the main README](../README.md).
This file documents the marketplace internals (plugin shipped, schema
notes, update behavior) for contributors and the curious.

## Quick install

```bash
claude plugin marketplace add WenyuChiou/agent-collab-skills
claude plugin install agent-collab-workspace@agent-collab-skills
claude plugin list
```

Default install scope is `user` (this OS account, all projects). Pass
`--scope project` for project-only install.

## Plugin shipped

The marketplace ships **one bundle plugin** — `agent-collab-workspace`
— that auto-discovers 5 skills from this same repo's `skills/<name>/`
layout:

| Plugin | Source repo | Skills bundled |
|---|---|---|
| `agent-collab-workspace` | `WenyuChiou/agent-collab-skills` (this repo) | `agent-task-splitter`, `agent-output-reconciler`, `agent-debate`, `agent-shared-memory`, `agent-acceptance-gate` |

Unlike `ai-research-skills` (which is a multi-source catalog of 5
upstream repos), this marketplace is **single-source**: the marketplace
config and the skill source live together in one repo. The 5 skills
are tightly coupled — they all read/write `.coord/` shared state — so
a single bundle keeps the contract obvious.

## Composes with `codex-delegate` and `gemini-delegate`

These skills are **not standalone agents**. They produce inputs that
[`codex-delegate`](https://github.com/WenyuChiou/codex-delegate) and
[`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill)
consume, and read outputs they produce:

- `agent-task-splitter` writes `.ai/codex_task_<NNN>_<slug>.md` and
  `.ai/gemini_task_<NNN>_<slug>.md` files in the exact format the
  delegate skills expect (Context / Goal / Constraints / Acceptance
  sections).
- `agent-output-reconciler` reads `<log-file>.result.json` files
  produced by the delegate skills' wrappers.
- `agent-acceptance-gate` reads `result.json` + reconciliation
  reports + runs verification commands.

If you don't already have `codex-delegate` / `gemini-delegate` and
their CLI binaries (`codex --version` / `gemini --version`), the new
skills will still help with planning + memory, but the
"actually-run-Codex" steps need those installed first.

## The `.coord/` directory convention

All 5 skills read/write a shared `.coord/` directory at your project
root. Files inside:

| File | Owner | Purpose |
|---|---|---|
| `.coord/plan.yml` | `agent-task-splitter` | Task DAG + agent assignment |
| `.coord/memory.yml` | `agent-shared-memory` | Append-only audit trail of decisions, open questions, artifacts, agent sessions |
| `.coord/reconciliation_<NNN>.md` | `agent-output-reconciler` | Per-round agreement / conflict report |
| `.coord/debate_<topic>.md` | `agent-debate` | Adversarial decision transcript |
| `.coord/acceptance_<NNN>.md` | `agent-acceptance-gate` | Pre-merge gate verdict |

Number `<NNN>` matches the `round` field in `plan.yml` so artifacts
are traceable to the multi-agent run that produced them.

## Schema reference

This marketplace follows the [Claude Code plugin marketplace schema](https://code.claude.com/docs/en/plugin-marketplaces).
The `agent-collab-workspace` plugin uses a `url` source pointing at
this same repo — Claude Code clones it on install and auto-discovers
SKILL.md files under `skills/<name>/`.

## Updating the marketplace

Pushing to `main` triggers a re-fetch on `claude plugin marketplace
update` (Claude Code tracks the source repo's default branch).

To ship a new skill in this bundle:
1. Add `skills/<new-skill-name>/SKILL.md` (and `references/` if
   needed).
2. Bump `metadata.version` in `marketplace.json` and `plugin.json`'s
   `version` field.
3. Update this README's "Plugin shipped" table.
4. Update `tests/test_catalog.py` if you've added schema invariants
   to enforce.
