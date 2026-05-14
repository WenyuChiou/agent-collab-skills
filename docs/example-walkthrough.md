# Worked example — multi-agent run on a real refactor

A walkthrough of the 6-skill pipeline on a hypothetical task:

> Refactor `src/auth/` from a monolithic `legacy.py` into a
> plugin-based architecture with `AuthProvider` implementations and
> backward-compatible entry points.

The `.coord/` artifacts produced at each step are checked in as
samples for reference:

- [`examples/plan.yml.sample`](../examples/plan.yml.sample)
- [`examples/reconciliation_001.md.sample`](../examples/reconciliation_001.md.sample)
- [`examples/acceptance_001.md.sample`](../examples/acceptance_001.md.sample)
- [`docs/negative-example-gemini-drift.md`](negative-example-gemini-drift.md)

The positive samples show the intended bounded handoff shape. The
negative drift fixture preserves the earlier dogfood failure pattern
where Gemini invented task metadata under inline-prompt mode.

## Pipeline at a glance

```
[goal]
  ↓ agent-task-splitter            → examples/plan.yml.sample
.coord/plan.yml + .ai/<agent>_task_*.md
  ↓ agent-context-budget
.coord/context_001.md + .coord/session_primer.md
  ↓ codex-delegate / gemini-delegate
.ai/<agent>_log_*.txt + result.json + result_*.md
  ↓ agent-output-reconciler        → examples/reconciliation_001.md.sample
.coord/reconciliation_001.md
  ↓ agent-acceptance-gate          → examples/acceptance_001.md.sample
.coord/acceptance_001.md → merge or retry
```

## Step 1 — splitter decomposes the goal

`agent-task-splitter` decomposed the auth refactor into four tasks
with mixed agent routing (see [plan.yml.sample](../examples/plan.yml.sample)):

| ID | Agent | Slug | Why this agent |
|---|---|---|---|
| T1 | claude | `define-auth-contract` | Architecture / API contract decisions need judgment, not mechanical work |
| T2 | codex | `scaffold-provider-core` | Multi-file boilerplate generation with clear spec |
| T3 | gemini | (long-context audit) | Reading entire `tests/auth/**` to surface migration risks |
| T4 | codex | (provider split + shim) | Mechanical refactor across many files following a fixed pattern |

The plan declared a token budget (180k), time budget (75 min), and
`context_policy` block the gate later checks against. Each task has explicit
`success_criteria` that map to runnable commands like
`pytest tests/auth/test_providers.py` and `mypy src/auth/`.

## Step 2 — delegate skills run the agents

`agent-context-budget` prepares the bounded context plan and fresh
session primer before delegate execution. Tasks T2–T4 went to
`codex-delegate` / `gemini-delegate`, which
emitted the standard wrapper output (`result.json` + summary
`.md`). T1 ran inline in the Claude session.

## Step 3 — reconciler synthesizes

`agent-output-reconciler` reads all four task outputs and writes
[reconciliation_001.md.sample](../examples/reconciliation_001.md.sample).
A real reconciliation includes per-task summaries, a cross-task
**conflict** section (file overlaps + cross-agent contradictions),
aggregated risks, and a recommended-action verdict (Pattern B
"merge with caveats" was chosen here).

## Step 4 — acceptance gate decides

`agent-acceptance-gate` reads the plan, the per-task `result.json`
files, and the reconciliation report. It walks each
`success_criterion` from the plan, runs the verification command
or assertion, and writes
[acceptance_001.md.sample](../examples/acceptance_001.md.sample)
with a final verdict.

This sample's verdict is **⚠ CONDITIONAL PASS** — chosen for
didactic value. The override pathway is documented at the bottom
of the sample, so users see what the "I know better, override the
gate" workflow looks like.

## What real runs look like

Real runs still produce drift and oversized output when prompts are
too loose. Keep those as negative examples, not default positive
samples. See [negative-example-gemini-drift.md](negative-example-gemini-drift.md)
for the preserved failure mode and the expected reconciler response.

## Pointers

- Skill source: [skills/](../skills/)
- Marketplace install: [main README](../README.md)
- Schema references: each skill's `references/` subdir
