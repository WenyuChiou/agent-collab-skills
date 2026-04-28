# Agent Collab Skills

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

> 5 Claude Code skills for multi-agent collaboration — task splitter,
> output reconciler, adversarial debate, shared memory, acceptance
> gate. Designed to compose with [`codex-delegate`](https://github.com/WenyuChiou/codex-delegate)
> and [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill).

A focused marketplace for the orchestration layer **above** delegation.
Existing delegate skills solve "Claude → Codex / Gemini handoff." This
catalog solves what comes next: how to split a goal across agents, how
to reconcile their outputs, how to remember decisions across sessions,
and how to gate merges.

Sister marketplace: [`ai-research-skills`](https://github.com/WenyuChiou/ai-research-skills)
(13 skills for the research workflow).

---

## Install

Prerequisite: Claude Code (https://claude.ai/code). Recommended (but
not required): `codex-delegate` and `gemini-delegate` already
installed via `ai-research-skills`, plus their CLI binaries on PATH.

```bash
claude plugin marketplace add WenyuChiou/agent-collab-skills
claude plugin install agent-collab-workspace@agent-collab-skills
```

This installs all 5 skills as one bundle. Verify:

```bash
claude plugin list
ls ~/.claude/skills/   # should include agent-task-splitter, etc.
```

Or use the helper script:

```bash
bash scripts/install-all.sh        # macOS / Linux / git-bash
pwsh scripts/install-all.ps1       # Windows PowerShell
```

---

## The 5 skills

| Skill | Triggered when you say... | Writes to `.coord/` |
|---|---|---|
| **`agent-task-splitter`** | "Split this task across Claude / Codex / Gemini" / "Plan a multi-agent run for X" | `plan.yml` + `.ai/codex_task_*.md` / `.ai/gemini_task_*.md` |
| **`agent-output-reconciler`** | "Reconcile these N agent outputs" / "Did Codex and Gemini agree?" | `reconciliation_<NNN>.md` |
| **`agent-debate`** | "Have Claude and Codex debate this design" / "Adversarial review on X" | `debate_<topic>.md` |
| **`agent-shared-memory`** | "Update shared memory with X" / "What have agents decided so far?" | `memory.yml` |
| **`agent-acceptance-gate`** | "Run the acceptance gate" / "Pre-commit check before merging" | `acceptance_<NNN>.md` |

Numbering `<NNN>` matches the `round` field in `plan.yml` so artifacts
trace back to the run that produced them.

---

## How they compose

```
goal
  ↓ agent-task-splitter
.coord/plan.yml + .ai/codex_task_*.md / .ai/gemini_task_*.md
  ↓ codex-delegate / gemini-delegate (existing)
.ai/codex_log_*.txt + .result.json + codex_result_*.md
  ↓ agent-output-reconciler
.coord/reconciliation_<NNN>.md
  ↓ agent-acceptance-gate
.coord/acceptance_<NNN>.md → merge or retry
```

`agent-shared-memory` runs alongside the whole pipeline — gets
updated at each step. `agent-debate` is invoked on consequential
decisions (architecture, design choice), not in the main loop.

See [docs/example-walkthrough.md](docs/example-walkthrough.md) for
a worked example with real `.coord/` sample artifacts produced by
running the pipeline end-to-end against actual Codex + Gemini CLI
invocations.

---

## Why these 5 specifically

The pain points each one solves, in order:

1. **Task splitting is mental load.** You currently classify "is
   this Codex-shaped or Gemini-shaped?" in your head every time. The
   splitter encodes the heuristics.
2. **Multi-agent output is hard to compare.** When 3 Codex jobs come
   back in parallel, you read 3 result.json files and merge them
   manually. The reconciler does the diff.
3. **Consensus-driven LLM output hides trade-offs.** When you ask one
   agent for a design, you get one answer. The debate skill forces
   two agents to argue opposing positions.
4. **Agent sessions don't share memory.** Codex resume works
   per-session; nothing persists across Claude session A → Codex
   session B → Gemini session C. Shared-memory makes `.coord/memory.yml`
   the cross-session blackboard.
5. **No standardized merge gate.** You currently eyeball the diff +
   run `pytest` manually. The gate runs all `success_criteria` from
   `plan.yml` + cost budget + cross-agent consistency check.

---

## Composes with

- [`codex-delegate`](https://github.com/WenyuChiou/codex-delegate) —
  consumes splitter output, produces input for reconciler.
- [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill)
  — same.
- [`academic-writing-skills`](https://github.com/WenyuChiou/academic-writing-skills)
  — acceptance gate optionally calls its banned-word audit on prose
  changes.

---

## Known issues

- **Gemini-cli refuses to read gitignored files.** The `.ai/`
  directory is conventionally gitignored to keep transient task
  files out of commits, but `gemini -p "Read .ai/gemini_task_*.md"`
  fails with `file ignored by configured ignore patterns`.
  **Workaround**: invoke gemini with the task content inlined into
  the prompt:
  ```bash
  TASK=$(cat .ai/gemini_task_<NNN>_<slug>.md)
  gemini -p "$TASK" --yolo > .ai/gemini_log_<NNN>_<slug>.txt 2>&1
  ```
  Side effect: gemini doesn't have file-system context for paths
  the task file references — make sure the prompt body itself
  contains all critical context, not just paths to read. The
  splitter skill's step 6b documents this.
- **Codex inline-prompt mode is fine.** `codex exec` reads
  gitignored files normally; only gemini has the conflict.
- **Worked example** with sample `.coord/` artifacts and honest
  documentation of what real multi-agent runs look like:
  [docs/example-walkthrough.md](docs/example-walkthrough.md).

---

## Status & License

MIT. Early-stage — the SKILL.md prompt scaffolding is complete and
tested in real workflows; please file issues if a skill misfires or
the `.coord/` schema breaks under your use case.

Contributions welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) for
the catalog ↔ delegate-skill interop rules.
