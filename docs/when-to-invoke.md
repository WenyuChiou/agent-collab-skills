# When to invoke `agent-collab-skills` — scenarios + decision rules + CLAUDE.md template

> **Audience**: operators using `agent-collab-skills` who keep asking "do I need a splitter / preset for THIS task?"
>
> **Goal**: codify the rules so it's not a judgment call every time. Copy the CLAUDE.md template at the bottom into your own setup.

This doc closes a recurring failure mode — operators skip the skill / preset because the task "felt simple", then drift happens (documented as F11 / F12 / F13 / F14 in [observed-failure-modes.md](observed-failure-modes.md)).

---

## Prerequisite stack (you need ALL of these)

`agent-collab-skills` is the **orchestration layer** above per-tool delegation. It does **not** replace the delegation skills — it coordinates them when ≥2 are running in one round.

```
┌─────────────────────────────────────────────────────────────┐
│  agent-collab-skills (this repo)                            │
│  — orchestration: task-splitter, output-reconciler,         │
│    acceptance-gate, debate, shared-memory, etc.             │
└──────────────────────────┬──────────────────────────────────┘
                           │ delegates work TO
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  codex-delegate     +     gemini-delegate-skill             │
│  (sister repos)                                             │
│  — per-tool: writes brief, invokes CLI, captures result     │
└──────────────────────────┬──────────────────────────────────┘
                           │ shell out TO
                           ▼
┌─────────────────────────────────────────────────────────────┐
│  codex CLI    +    gemini CLI    (must be on PATH)          │
│  — actual binaries that hit OpenAI / Google APIs            │
└─────────────────────────────────────────────────────────────┘
```

**Install everything before applying any rule below**:

| Layer | Repo / Skill | What it does |
|---|---|---|
| **Orchestration** | [`agent-collab-skills`](https://github.com/WenyuChiou/agent-collab-skills) (this) | Decides splitter / preset / debate / reconciler invocations |
| **Codex delegation** | [`codex-delegate`](https://github.com/WenyuChiou/codex-delegate) | Writes `.ai/codex_task_*.md` brief + invokes `codex exec` + captures result.jsonl |
| **Gemini delegation** | [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill) | Writes `.ai/gemini_task_*.md` brief + uses `cat task.md \| gemini --yolo -p ...` stdin pipe (F1 workaround) |
| **CLI binaries** | `codex` + `gemini` on PATH | npm-installed OpenAI Codex CLI + Google Gemini CLI |

→ The rules below only make sense if **all three** layers are installed.

---

## TL;DR — the 5 decision rules

| If the round has... | Do this | Why |
|---|---|---|
| **1 delegate run** (1× codex / 1× gemini) | Direct delegate skill ([`codex-delegate`](https://github.com/WenyuChiou/codex-delegate) or [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill)) | splitter overhead > value |
| **≥2 parallel delegate runs producing files** | `agent-task-splitter` first | prevents drift between parallel outputs |
| **Diff touches ≥2 locale variants** (`.md` + `.zh-Hans.md` + `.en.md`) | `agent-acceptance-gate --preset=multi-locale-mirror-sync` before commit | mirror divergence is the most common drift class |
| **Diff adds catalog entries** (project listing, framework comparison table) | `agent-acceptance-gate --preset=catalog-entry-add` before commit | catalog drift is hard to spot manually |
| **Diff touches frontier-model claims** (`<model>` within 3 lines of `<benchmark %>`) | `agent-acceptance-gate --preset=fact-check-frontier-models` before commit | hallucinated benchmark/model names ship if no live verification |

---

## Scenarios — when YES, when NO, when judgment call

### 1. `agent-task-splitter`

**YES — use it when**:
- 2+ parallel delegates each writing files that ship (commit)
- Cross-file consistency required (one agent's output is another's input)
- Output will land in production / be merged
- Multi-locale work: zh-TW canonical + zh-Hans mirror + en mirror in one round

**Concrete example — needed**:
> "Codex sweeps `default → preset` in 50 files. Gemini translates 5 new sections to zh-Hans + en. Both run in parallel and commit results."
>
> → Must use `agent-task-splitter`. Otherwise Codex changes `default` inside a sentence Gemini is translating; the two outputs collide.

**NO — skip it when**:
- Pure research (agents gather info, you synthesize and write yourself)
- Single delegate run (1× codex)
- Output is for your own reading (`.ai/<task>.md` notes, never ship)
- Iterative back-and-forth with one delegate

**Concrete example — skip**:
> "I want 3 agents to research how Claude Code docs explain advanced concepts; I'll synthesize the findings myself and write the section."
>
> → Just dispatch 3 `Agent` calls in parallel. Splitter overhead exceeds value because no production artifacts are produced by the agents.

**Judgment call territory** (operator decides):
- 2+ delegates writing to non-shipping locations (`.ai/<task>/` scratch space, throwaway PR comments)
- Parallel research + 1 production output (research agents skip splitter; the 1 production output goes through delegate normally)

---

### 2. `agent-acceptance-gate` presets

The 3 mandatory presets fire on specific triggers. **Do not skip when trigger fires.**

#### 2a. `multi-locale-mirror-sync`

**Triggers** (any of these):
- Commit touches ≥2 files with same stem in different locales (e.g., `stages/06-x.md` + `stages/06-x.zh-Hans.md`)
- Cross-stage anchor changes (forward-ref between files needs update)
- New section added that requires mirror in zh-Hans + en

**Invocation**:
```bash
# Per docs/SKILL.md of agent-acceptance-gate
invoke agent-acceptance-gate \
  --preset=multi-locale-mirror-sync \
  --stem="06-memory-rag" \
  --required-terms="Context Engineering,RAG,vector database" \
  --brief-file=".ai/2026/05/14/codex_task_006.md"
```

#### 2b. `catalog-entry-add`

**Triggers**:
- Adding to a project listing table (e.g., `stages/05-claude-code-ecosystem.md` MCP server table)
- Adding to a framework comparison matrix
- Adding to a "curated projects" table (any rated list)

**Invocation**:
```bash
invoke agent-acceptance-gate \
  --preset=catalog-entry-add \
  --catalog-file="stages/05-claude-code-ecosystem.md" \
  --new-entries="yamadashy/repomix,anthropics/claude-for-legal"
```

#### 2c. `fact-check-frontier-models`

**Triggers**:
- New text mentions a frontier model name within 3 lines of a benchmark %
- Examples: "GPT-5.5 reaches 94% on GPQA" / "DeepSeek-R2 hits 96% MMLU"
- Anytime you add a model-version × benchmark-result claim

**Invocation**:
```bash
invoke agent-acceptance-gate \
  --preset=fact-check-frontier-models \
  --file="stages/01-llm-basics.md" \
  --models="GPT-5.5,Claude Opus 4.7,Gemini 3"
```

→ This is the preset that would have caught the 2026-05-13 "DeepSeek-R2" hallucination. **Don't skip.**

---

### 3. Other skills (no mandatory presets, judgment call)

| Skill | Use when | Concrete example |
|---|---|---|
| `agent-context-budget` | Context window > 60% used + 2+ more delegate runs planned | "Main session at 130k / 200k tokens, need 2 more codex sweeps + 1 gemini translate — budget the remaining 70k across 3 runs" |
| `agent-output-reconciler` | 2-3+ delegates produced outputs that need to merge into one final | Codex wrote `paper3-results.md` + Gemini wrote `paper3-results.zh.md` + Claude reviewed both → reconcile into single `paper3-final.md` |
| `agent-debate` | Design decision where 2 perspectives matter (Claude vs Codex argue, you arbitrate) | "Should this be one big SKILL.md or split into 3 sub-skills?" → Claude argues 1, Codex argues 3, transcript saved to `.coord/debate_skill_structure.md`, you decide |
| `agent-shared-memory` | Multi-round session where decisions need to persist across rounds | Across 4 rounds editing same paper: round-1 decided abstract structure, round-3 needs to recall it — `.coord/memory.yml` holds the prior decisions |
| `agent-plan-act-reflect` | Iterative quality refinement (PAR loop until acceptance check passes) | "Banned-phrase audit on Section 5 fails repeatedly" → PAR loop: plan rewrite → act (rewrite) → reflect (re-run audit) → loop until PASS |

→ `agent-plan-act-reflect` is the **alternative to a full splitter + reconciler cycle** when you're iterating on ONE artifact's quality, not orchestrating multiple parallel outputs. Use it when the task is "make this thing better until check X passes", not "split this work across N agents".

---

## Decision flowchart

```
┌─────────────────────────────────────┐
│ Are 2+ delegates producing          │
│ shipping files in this round?       │
└─────┬───────────────────────┬───────┘
      │ YES                   │ NO (1 delegate or pure research)
      ▼                       ▼
  agent-task-splitter      Direct delegate or
                           parallel research agents
      │
      ▼
  (delegates execute)
      │
      ▼
┌─────────────────────────────────────┐
│ Before commit, does the diff:       │
│ (a) touch ≥2 locale variants?       │
│ (b) add catalog entries?            │
│ (c) include frontier-model claims?  │
└─────┬───────────────────────┬───────┘
      │ ANY YES               │ NO
      ▼                       ▼
  Run matching preset      Skip preset
  (mandatory)              (verify anchors only)
      │
      ▼
  Preset PASS → commit
  Preset FAIL → fix + re-run, OR re-delegate
```

---

## When a preset FAILS — what to do

Presets are advisory checks before commit. A FAIL is not a soft warning to override — it blocks until resolved. Three paths, in order of preference:

### Path 1 — Fix the diff manually + re-run the same preset (default)

For most FAILs (broken anchor, missing required term, line-parity off, mirror divergence), the issue is identifiable from the FAIL message. Examples:

- `anchor_strict FAIL: target X not found` → either the target file's heading changed (update reference) or the reference is stale (update or remove)
- `required_terms FAIL: "Context Engineering" missing from zh-Hans` → add the term in the right section
- `line_parity FAIL: zh-TW 188 vs zh-Hans 250` → check if zh-Hans accidentally retained old + new section; trim or align

After the fix, re-run the same preset. If PASS → commit. If FAIL again → check whether your "fix" actually addressed the diagnosed problem.

### Path 2 — Re-delegate to the original agent with the FAIL output as new brief

When the FAIL points at a delegate's output (e.g., Gemini produced zh-Hans with wrong terminology), do NOT manually fix the delegate's output yourself — re-delegate with the FAIL log as context. Append to the original brief:

```markdown
## Issues to fix (from acceptance-gate FAIL)

The previous run produced output with the following issues that the
multi-locale-mirror-sync preset caught:

[paste the preset FAIL log here verbatim]

Re-do the same task with these specific issues addressed. Keep the
rest of your previous output intact.
```

This preserves the agent-as-author boundary — operators don't ship-by-hand the agent's work; agents stay accountable for their own outputs.

### Path 3 — Override (rare, document it)

If the preset is wrong about the specific case (false positive, e.g., a banned-phrase check flagging a term that's correctly used in a code block), document the override in the commit message:

```
docs(...): apply X change

Preset FAIL override: multi-locale-mirror-sync flagged "function" as banned-
phrase in zh-Hans line 47, but the line is inside a `<pre>` code block
showing literal API name. False positive; pattern needs refinement.

Filed v0.2.4 backlog: preset should skip banned-phrase check inside
fenced code blocks.
```

Override should be the exception, not the routine. If you find yourself overriding 2+ times in the same week, the preset's checks need refinement, not your patience.

### Never do this

- **Don't disable the preset** (e.g., comment out the YAML check) to "make CI green"
- **Don't commit with a FAIL** and "fix it later" — later doesn't happen
- **Don't manually edit the delegate's output to make the preset PASS** without re-delegating; this hides the underlying drift cause

---

## CLAUDE.md template (copy-paste ready)

Drop this into your project's `CLAUDE.md` to codify the rules for any agent operating in your repo:

```markdown
## Multi-Agent Collaboration Rules

When ≥2 delegate runs in one round produce shipping output, OR diffs touch
≥2 locale variants / catalogs / frontier-model claims, the following skills
and presets are **mandatory** — not "consider", not "if you remember", but
required-before-commit.

### Prerequisites (install all three)

These rules assume your environment has the 3-layer stack installed:

1. **Per-tool delegation skills** (sister marketplaces):
   - [`codex-delegate`](https://github.com/WenyuChiou/codex-delegate) — writes brief + invokes `codex exec` + captures result
   - [`gemini-delegate-skill`](https://github.com/WenyuChiou/gemini-delegate-skill) — same, uses `cat task.md | gemini --yolo -p ...` stdin pipe
2. **Orchestration layer** (this rule set assumes you have it):
   - [`agent-collab-skills`](https://github.com/WenyuChiou/agent-collab-skills) — `agent-task-splitter`, `agent-acceptance-gate`, etc.
3. **CLI binaries on PATH**: `codex` (npm: `@openai/codex`) + `gemini` (Google's CLI)

Without all three layers, the rules below are not enforceable — `agent-task-splitter` writes briefs that `codex-delegate` / `gemini-delegate` then execute. They are layered, not interchangeable.

### Mandatory invocations

| Trigger | Skill / preset | Why |
|---|---|---|
| ≥2 parallel delegate runs → shipping files | `agent-task-splitter` | Prevents drift between parallel outputs |
| Diff touches ≥2 locale variants (e.g., `*.md` + `*.zh-Hans.md`) | `agent-acceptance-gate --preset=multi-locale-mirror-sync` | Mirror divergence is the #1 drift class |
| Diff adds entries to a curated catalog / project list | `agent-acceptance-gate --preset=catalog-entry-add` | Catalog drift is hard to spot manually |
| Diff includes frontier model + benchmark % | `agent-acceptance-gate --preset=fact-check-frontier-models` | Live primary-source verification, prevents hallucinated benchmarks |

### Direct delegate (no splitter / preset needed)

- 1 delegate run (single `codex-delegate` or `gemini-delegate`)
- Pure research dispatch (multiple `Agent` calls gathering info, you synthesize)
- Single-file edit with no locale mirrors
- Output that does not commit (scratch `.ai/<task>/` files)

### Anti-patterns to watch (from observed-failure-modes.md)

- **F11**: Codex applies a sweep rule to meta-documentation tables that document the rule itself (e.g., a style-guide contrast table containing the term being swept) — intra-agent scope overreach
- **F12**: parallel agents add unrequested attributions without coordinator
- **F13**: Gemini "liar mode" — claims success without writing files (use Codex for high-stakes mirror sync, or verify mtime)
- **F14**: skipping mandatory preset because task "felt simple" → drift ships

### How to invoke

```bash
# Multi-locale mirror sync example
invoke agent-acceptance-gate \
  --preset=multi-locale-mirror-sync \
  --stem="<file-stem-without-locale-suffix>" \
  --required-terms="<comma-sep-key-terms>" \
  --brief-file="<path-to-task-brief>"

# Frontier-model fact-check example
invoke agent-acceptance-gate \
  --preset=fact-check-frontier-models \
  --file="<path-to-modified-file>" \
  --models="<comma-sep-model-names>"
```

### When you skip a mandatory invocation

You don't. If the trigger fires, the preset runs before commit. Period.
This is the same discipline that ships F14 from happening twice.

> Full rules: [`agent-collab-skills/docs/when-to-invoke.md`](https://github.com/WenyuChiou/agent-collab-skills/blob/main/docs/when-to-invoke.md)
```

---

## Source attribution

This rule set codifies discipline learned through repeated F-N incidents in production use of `agent-collab-skills` v0.1 → v0.2.3. See [observed-failure-modes.md](observed-failure-modes.md) for the case studies behind each rule.
