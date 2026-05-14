# Agent Collab Skills

[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

**English** ・ [繁體中文](README.zh-TW.md)

![Pipeline overview: agent-task-splitter → codex-delegate / gemini-delegate / claude-in-session → agent-output-reconciler → agent-acceptance-gate, with agent-shared-memory and agent-debate as cross-cutting chips](docs/pipeline-overview.png)

> 6 Claude Code skills for context-safe multi-agent collaboration —
> task splitter, context budget, output reconciler, adversarial debate,
> shared memory, acceptance gate. Designed to compose with [`codex-delegate`](https://github.com/WenyuChiou/codex-delegate)
> and [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill).

> 📚 Part of the [**agentic AI learning roadmap**](https://github.com/WenyuChiou/awesome-agentic-ai-zh) — a 7-stage curated path for building agentic AI, multilingual (zh-TW · zh-CN · English). Multi-agent orchestration is covered in Stage 7.

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

This installs all 6 skills as one bundle. Verify:

```bash
claude plugin list
ls ~/.claude/skills/   # should include agent-task-splitter, etc.
```

Or use the helper script:

```bash
bash scripts/install-all.sh        # macOS / Linux / git-bash
pwsh scripts/install-all.ps1       # Windows PowerShell
```

### Do I need to modify `CLAUDE.md`?

**No.** Claude Code's built-in skill matching reads each `SKILL.md`'s `description` field and auto-routes user prompts. Plugin install is the only setup step — saying *"split this across Claude, Codex, and Gemini"* triggers `agent-task-splitter` without any extra configuration.

You may optionally add explicit routing rules to your `~/.claude/CLAUDE.md` if you:

- already have a delegation protocol there that competes with these skills (e.g., a long-standing *"always hand-write codex task files"* rule that would otherwise win the routing race)
- want to enforce hard behaviors (e.g., *"always run `agent-acceptance-gate` before merging any multi-agent round"*)

Otherwise leave `CLAUDE.md` alone — the skills are designed to work via description-based discovery.

---

## The 6 skills

| Skill | Triggered when you say... | Writes to `.coord/` |
|---|---|---|
| **`agent-task-splitter`** | "Split this task across Claude / Codex / Gemini" / "Plan a multi-agent run for X" | `plan.yml` + `.ai/codex_task_*.md` / `.ai/gemini_task_*.md` |
| **`agent-context-budget`** | "Context is getting too large" / "Prepare a fresh session primer" / "Bound this Codex + Gemini run" | `context_<NNN>.md` + `session_primer.md` |
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
  ↓ agent-context-budget
.coord/context_<NNN>.md + .coord/session_primer.md
  ↓ codex-delegate / gemini-delegate (existing)
.ai/codex_log_*.txt + .result.json + codex_result_*.md
  ↓ agent-output-reconciler
.coord/reconciliation_<NNN>.md
  ↓ agent-acceptance-gate
.coord/acceptance_<NNN>.md → merge or retry
```

`agent-shared-memory` runs alongside the whole pipeline and stores
accepted decisions, open questions, artifacts, and session outcomes.
`agent-context-budget` keeps handoffs bounded so the main session does
not absorb raw logs or full memory. `agent-debate` is invoked on
consequential decisions (architecture, design choice), not in the main
loop.

See [docs/example-walkthrough.md](docs/example-walkthrough.md) for
a worked example with real `.coord/` sample artifacts produced by
running the pipeline end-to-end against actual Codex + Gemini CLI
invocations.

---

## Why these 6 specifically

The pain points each one solves, in order:

1. **Task splitting is mental load.** You currently classify "is
   this Codex-shaped or Gemini-shaped?" in your head every time. The
   splitter encodes the heuristics.
2. **Context explodes during large runs.** The context-budget skill
   turns memory, logs, and agent outputs into bounded packets and a
   session primer.
3. **Multi-agent output is hard to compare.** When 3 Codex jobs come
   back in parallel, you read 3 result.json files and merge them
   manually. The reconciler does the diff.
4. **Consensus-driven LLM output hides trade-offs.** When you ask one
   agent for a design, you get one answer. The debate skill forces
   two agents to argue opposing positions.
5. **Agent sessions don't share memory.** Codex resume works
   per-session; nothing persists across Claude session A → Codex
   session B → Gemini session C. Shared-memory makes `.coord/memory.yml`
   the cross-session blackboard.
6. **No standardized merge gate.** You currently eyeball the diff +
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
- [`agentmemory`](https://github.com/rohitg00/agentmemory) —
  optional recall cache only. `.coord/memory.yml` remains canonical;
  see [docs/agentmemory-integration.md](docs/agentmemory-integration.md).

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
  gemini -p "$TASK" --yolo \
    < /dev/null > .ai/gemini_log_<NNN>_<slug>.txt 2>&1
  ```
  Side effect: gemini doesn't have file-system context for paths
  the task file references — make sure the prompt body itself
  contains all critical context, not just paths to read. The
  splitter skill's step 6b documents this.
- **Both `codex` and `gemini` hang at startup if stdin is open.**
  When launching from a script or non-interactive shell, codex-cli
  ≥ 0.121.0 prints "Reading additional input from stdin..." and
  waits forever. Same for gemini-cli. **Workaround**: redirect
  stdin to `/dev/null` on every direct invocation:
  ```bash
  codex exec --full-auto -m <model> "<prompt>" \
    < /dev/null > .ai/codex_log_<NNN>_<slug>.txt 2>&1
  ```
  The `codex-delegate` wrapper script handles this internally; only
  direct `codex exec` / `gemini -p` calls need the explicit
  redirect.
- **Codex reads gitignored files normally** — only gemini has the
  gitignore conflict.
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
