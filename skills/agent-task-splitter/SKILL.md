---
name: agent-task-splitter
description: Use when the user asks to split a goal across Claude, Codex, or Gemini; plan a multi-agent run; break work into parallel agent tasks; or decompose a large task that needs bounded context handoffs.
---

# agent-task-splitter

Bridge between **a high-level goal** and **the multi-agent execution
pipeline**. You write `.coord/plan.yml` (the DAG) and the per-agent
task files. The delegate skills (`codex-delegate`, `gemini-delegate`)
invoke the agents using those task files. The reconciler reads what
they produce.

This skill **does not invoke any agent**. It only plans and writes
files.

## When to use

Trigger phrases:

- "Split this task across Claude / Codex / Gemini."
- "Plan a multi-agent run for `<goal>`."
- "Break this down into parallel agent tasks."
- "Decompose this goal into Codex + Gemini subtasks."
- "Make a `.coord/plan.yml` for this work."

Not for:

- Running the agents themselves — that's `codex-delegate` /
  `gemini-delegate`.
- Reconciling agent outputs after they run — that's
  `agent-output-reconciler`.
- Single-agent tasks — if the whole job is one Codex run, just use
  `codex-delegate` directly. This skill earns its keep when there
  are ≥ 2 subtasks plausibly going to different agents.

## Inputs

The user provides one or both of:

1. **The goal**: a sentence or paragraph describing what they want.
2. **Constraints** (optional): which agents are available, time
   budget, files in / out of scope, success criteria they already
   know.

You may also read existing project context if relevant:

- `.coord/memory.yml` — prior decisions / open questions (if
  `agent-shared-memory` has run before).
- `.research/project_manifest.yml` — research project context (if
  `research-context-compressor` from `ai-research-skills` has run).

If the goal is large, cross-session, or likely to involve parallel
Codex + Gemini work, use `agent-context-budget` before writing task
files. It sets the bounded handoff policy that prevents context
overflow.

## Workflow

### 0. Verify cwd is the project root before writing anything

`.coord/plan.yml`, `.ai/<agent>_task_*.md`, and all downstream
artifacts go to **the project the agents will modify**, not whatever
directory Claude currently happens to be in. Before writing
anything, confirm:

1. The cwd matches the repo the user actually means.
2. If the user is in a worktree (`.git` is a file pointing to
   a worktree dir, not a real `.git/` directory), confirm they want
   `.coord/` in the worktree or the main checkout — these can differ.
3. If working across multiple repos in one conversation, ask which
   one the multi-agent run targets.

This step takes 5 seconds and prevents writing `.coord/plan.yml`
to the wrong filesystem location, which silently breaks downstream
agents that look for it relative to their own `-C`/cwd.

### 1. Understand the goal

Restate the goal back to the user in 1-2 sentences before planning.
If anything is ambiguous (which files, which tests count as
success), ask **one focused clarifying question** before producing
the plan. Don't ask 5 questions; ask the single question that most
narrows the design space.

### 2. Decompose into subtasks

Break the goal into 2-7 subtasks. For each subtask, decide:

| Property | How to determine |
|---|---|
| `id` | `T1`, `T2`, ... contiguous |
| `agent` | One of `codex` / `gemini` / `claude` (see classification below) |
| `slug` | kebab-case task identifier (≤ 30 chars) |
| `description` | one line |
| `depends_on` | list of `T_n` ids that must complete first; `[]` if none |
| `files_in_scope` | glob list of files this task may modify |
| `files_out_of_scope` | glob list this task must NOT touch |
| `success_criteria` | 1-3 bullets, each a runnable check (`pytest`, `ls`, `grep`) or a checkable assertion |

**Guidance on subtask granularity:** if a subtask exceeds ~50 lines
of expected diff or requires more than one round of tool calls, it's
too big — split further. If a subtask is < 10 lines of expected
work, fold it into a sibling.

### 3. Classify each subtask: Codex vs Gemini vs Claude

Use this routing table. When in doubt, see
`references/task_splitter_heuristics.md` for nuanced cases.

| Route to | Best for | Avoid |
|---|---|---|
| `codex` | Multi-file mechanical implementation, batch refactors, test scaffolds, regex-able edits across N files, boilerplate generation, codegen from clear specs | Architecture decisions, debugging root cause, security review, ambiguous requirements |
| `gemini` | Long-context reading + synthesis (>50 page sources), bilingual / CJK long-form writing, second-opinion reviewing of generated output, terminology alignment across documents | Bulk code generation, mechanical implementation with no reading required |
| `claude` | API contract design, bug diagnosis, acceptance review, design judgment, anything needing project memory / cross-conversation context | Token-heavy mechanical work, very-long-context single reading passes |

A useful sanity check: **if the subtask is "do X to many files in
roughly the same way", that's Codex. If the subtask is "read this
big thing carefully and tell me what's there", that's Gemini. If
the subtask is "decide whether X is right", that's Claude.**

### 4. Identify dependencies (DAG)

For each subtask, list which other subtasks must finish before it
can start (`depends_on`). Common patterns:

- **Linear chain**: `T1 → T2 → T3` (each depends on previous).
- **Fan-out**: `T1 → [T2, T3, T4]` (T2/3/4 parallel after T1).
- **Fan-in**: `[T2, T3] → T4` (T4 needs both).
- **Independent**: all `depends_on: []` — runnable fully parallel.

Avoid cycles. If you have one, redesign.

### 5. Write `.coord/plan.yml`

Schema (full reference: `references/task_splitter_heuristics.md`):

```yaml
round: 1
goal: "Refactor the auth module into plugin-based architecture"
budget:
  tokens: 200000          # optional, gate skill checks against this
  duration_min: 60        # optional advisory
context_policy:
  main_session_token_budget: 3000
  task_packet_token_budget: 6000
  result_summary_word_budget: 250
  memory_digest_token_budget: 1200
  log_tail_lines_on_error: 50
  raw_log_policy: path-only
  agentmemory: optional
created_utc: "2026-04-28T09:00:00Z"
tasks:
  - id: T1
    agent: codex
    slug: extract-interfaces
    description: "Define abstract base classes in src/auth/interfaces.py"
    depends_on: []
    files_in_scope:
      - "src/auth/interfaces.py"
    files_out_of_scope:
      - "src/auth/legacy.py"
      - "tests/**"
    success_criteria:
      - "src/auth/interfaces.py exists and defines AuthProvider ABC"
      - "no other source files modified"
  - id: T2
    agent: codex
    slug: refactor-providers
    description: "Move existing provider classes to inherit from new ABC"
    depends_on: [T1]
    files_in_scope:
      - "src/auth/providers/*.py"
    success_criteria:
      - "pytest tests/auth/test_providers.py passes"
      - "no imports of src.auth.legacy from other modules"
  - id: T3
    agent: gemini
    slug: review-doc-coverage
    description: "Read all public APIs in src/auth and verify docstrings reflect new architecture"
    depends_on: [T1, T2]
    success_criteria:
      - "every public symbol in src/auth has a docstring"
      - "report flags any docstring still mentioning the legacy class"
  - id: T4
    agent: claude
    slug: design-review
    description: "Read T1-T3 outputs, verify the architecture choice survives the implementation"
    depends_on: [T1, T2, T3]
    success_criteria:
      - "explicit YES/NO verdict + rationale in chat"
```

### 6. Write per-agent task files

Codex and Gemini have **different task file conventions**. Don't use
a single template for both — each delegate skill expects its own
shape.

#### 6a. Codex task files (`agent: codex`)

Path: `.ai/codex_task_<NNN>_<slug>.md`. `<NNN>` is the zero-padded
`round` (`001` for round 1). Format follows `codex-delegate`'s
"Supervisor Workflow" section:

```markdown
# Task: <description>

## Context
- Repo: <absolute path>
- Plan: .coord/plan.yml (round <N>, task <T-id>)
- Read these files first:
  - <files_in_scope items + relevant references>
- Only modify (files_in_scope):
  - <files_in_scope items>
  - .ai/codex_result_<NNN>_<slug>.md   ← REQUIRED: the result-summary file
- Do NOT touch (files_out_of_scope):
  - <files_out_of_scope items>
- Depends on outputs of: <list T-ids + their result paths>

## Goal
<task.description, expanded with concrete deliverable>

## Constraints
- Follow adjacent code style.
- Do not make architectural changes beyond the scope.
- Do not edit files outside the allowed list.

## Acceptance
- Required tests: <test command from success_criteria>
- Required result summary: write a concise summary to
  .ai/codex_result_<NNN>_<slug>.md
- Summary limit: <= 250 words. Include changed files, tests run,
  risks, and blockers. Do not paste raw logs.
```

> **Critical**: `.ai/codex_result_<NNN>_<slug>.md` MUST appear in
> `files_in_scope`. The Acceptance section requires writing there;
> if it's not in scope, codex flags a self-conflict and may refuse
> to write it.

> **Critical (Codex invocation)**: when launching codex directly
> (not via the `codex-delegate` wrapper script), **close stdin
> with `< /dev/null`** — codex-cli ≥ 0.121.0 otherwise hangs at
> "Reading additional input from stdin..." indefinitely. Pattern:
>
> ```bash
> # Preferred: structured result via -o flag (bounded, machine-readable)
> codex exec --full-auto -m gpt-5.4 \
>   -o .ai/codex_result_<NNN>_<slug>.jsonl \
>   "Read .ai/codex_task_<NNN>_<slug>.md and execute all instructions inside." \
>   < /dev/null
>
> # Fallback (only if you need raw stdout for diagnostics): MUST cap with head
> # WITHOUT this cap, codex retries + verbose tool calls can grow logs to
> # multi-GB (real incident: 7 GB in .ai/ on 2026-04-17). Never use bare
> # `> file.log 2>&1`.
> codex exec --full-auto -m gpt-5.4 \
>   "Read .ai/codex_task_<NNN>_<slug>.md and execute all instructions inside." \
>   < /dev/null 2>&1 | head -c 10485760 > .ai/codex_log_<NNN>_<slug>.txt
> ```
>
> The `codex-delegate` wrapper script (`run_codex.sh`) handles both
> the `-o` flag and the 10 MB log cap internally; only direct
> `codex exec` calls need to set these explicitly.

#### 6b. Gemini task files (`agent: gemini`)

Path: `.ai/gemini_task_<NNN>_<slug>.md`. Format follows
`gemini-delegate`'s "Supervisor Workflow" — different sections from
codex:

```markdown
# Task: <description>

## Context
- Repo: <absolute path>
- Plan: .coord/plan.yml (round <N>, task <T-id>)
- Read these files first:
  - <files_in_scope items + relevant references>
- Output file(s):
  - <files this task produces>
  - .ai/gemini_result_<NNN>_<slug>.md   ← REQUIRED: the result-summary file
- Depends on outputs of: <list T-ids + their result paths>

## Goal
<task.description, expanded with concrete deliverable>

## Language
- Output language: <English | Traditional Chinese | Simplified Chinese | bilingual>
- Tone: <formal | concise | technical | executive>
- Audience: <who will read it>

## Constraints
- Preserve dates, proper nouns, code identifiers exactly.
- Keep terminology consistent with referenced sources.
- Do not invent facts missing from the inputs.

## Acceptance
- Required verification files: <files Claude will check after run>
- Required sentinel strings: <strings the gate will grep for>
- Required result summary: write a concise summary to
  .ai/gemini_result_<NNN>_<slug>.md
- Summary limit: <= 250 words. Include findings, files inspected,
  risks, and blockers. Do not paste raw logs.
- Self-review checklist (REQUIRED, see docs/observed-failure-modes.md F9):
  Before declaring done, agent must explicitly verify:
  1. Slugs in output files match `plan.yml` slug VERBATIM (F7)
  2. Table column counts are unchanged for any table the task touched (F2)
  3. No time-relative phrases ("today", "this week", "soon") in output (F3)
- Claude will perform a final review (terminology, factual accuracy,
  schema adherence) before merging.

## Banned phrasing (output-language-agnostic, applies in all locales)
- Time-relative: "today", "this week", "yesterday", "soon",
  "recently", "now" — replace with absolute year or "actively
  maintained" / specific date.
- Vague popularity: "popular", "widely used" — replace with star
  count + date or specific user count.
- Unverified status: "production-ready", "battle-tested" — only if
  primary source confirms.
```

> **Critical (Gemini-specific, F1 in `docs/observed-failure-modes.md`)**:
> gemini-cli **refuses to read gitignored files by default**. Since
> `.ai/` is conventionally gitignored to keep transient task files
> out of commits, this means
> `gemini -p "Read .ai/gemini_task_<NNN>_<slug>.md and execute"`
> **WILL FAIL** with `"File path '.ai/...' is ignored by configured
> ignore patterns."` — this is the single most common Gemini failure
> mode observed in dogfooding.
>
> **Default invocation pattern** (use this, not the `gemini -p "Read .ai/..."`
> pattern):
>
> ```bash
> # Pipe task content via stdin to bypass gitignore restriction.
> # Cap stdout at 10 MB to prevent runaway logs (incident pattern from
> # global CLAUDE.md).
> cat .ai/gemini_task_<NNN>_<slug>.md | gemini --yolo -p \
>   "Below is your full task brief via stdin. Execute it. Report
>    PASS/FAIL of the acceptance checks at end. Don't ask questions,
>    just do it." \
>   2>&1 | head -c 10485760 > .ai/gemini_log_<NNN>_<slug>.txt
> ```
>
> Avoid the older "inline TASK=$(cat)" pattern — it's longer and
> the `cat | gemini --yolo -p ...` pipe is what actually got tested
> on 2026-05-13. The `< /dev/null` redirect is not needed when stdin
> is piped (the pipe satisfies stdin closure).
>
> When you produce the gemini task file, also produce a sibling
> shell snippet `.ai/gemini_run_<NNN>_<slug>.sh` with the inlined
> invocation, so the user can run it directly without manual
> assembly. Side effect of the inline mode: gemini doesn't have
> file-system context for the task file's referenced inputs — make
> sure the prompt body itself contains all critical context, not
> just paths.

#### 6c. Claude tasks (`agent: claude`)

**Don't write a task file.** Claude executes inline in the current
conversation. The plan.yml entry serves as the spec.

### 6d. Task-shape guidance (prevents F6 over-tabularization)

Before writing the task body, classify the task by **output shape**:

| Task shape | Format guidance to include in brief |
|---|---|
| **Pedagogical** (curriculum, tutorial, explainer) | "Prefer prose. A table is justified ONLY if (a) data is genuinely comparative (≥3 attributes per row) AND (b) reader will use it as decision tool, not inventory. 'Catalog of N variants' is anti-pattern — replace with prose covering 2-3 axes + `<details>` for long tail." |
| **Reference** (API docs, schema definitions) | "Tables OK for structured data. Each table should answer one specific question." |
| **Catalog** (project listings, comparisons) | "Tables OK but include: (a) ≤ 10 entries in primary table; (b) `<details>` collapsible for long tail; (c) live `gh api` verification step for stars/license/pushed_at — required in `result.md`." |
| **Migration / mechanical edit** (rename, replace pattern) | "No tables. Concrete file list + diff summary." |
| **Translation / mirror-sync** | "Maintain source structure VERBATIM. No new tables, no removed tables, no merged tables. Column counts must match per-table across locales. (F2 incident)" |

This block should appear in `## Format guidance` section of every
task brief. Skipping it is the F6 root cause.

### 6e. Fact-verification step (prevents F4, F5)

For any task that asserts external facts (star counts, model
releases, license types, benchmark numbers, paper acceptance
status), the task brief MUST include:

```markdown
## Fact verification (REQUIRED)

Before writing any "★ Nk", "License: X", or "(Year) Model" claim,
run the live check:

  # For GitHub repos:
  gh api repos/<org>/<repo> --jq '{stars: .stargazers_count,
    license: .license.spdx_id, pushed: .pushed_at, archived: .archived}'

  # For arxiv papers:
  curl -s "https://arxiv.org/abs/<id>" | grep -o "title>[^<]*"

Quote the actual returned value in `result.md`. Any claim NOT
verified this way must be marked `(claimed, unverified)` so the
reconciler / acceptance gate can flag it.
```

This step prevented the DeepSeek-R2 fabrication incident (F4) when
applied retroactively.

### 7. Hand off to the user

End with:

```
Plan written to .coord/plan.yml (round 1, N tasks).
Task files ready:
  .ai/codex_task_001_<slug1>.md
  .ai/codex_task_001_<slug2>.md
  .ai/gemini_task_001_<slug3>.md

Next steps:
  # Run codex tasks (after T1 finishes, T2/T3 can run in parallel).
  # Option A (preferred) — use the codex-delegate wrapper:
  bash .claude/skills/codex-delegate/scripts/run_codex.sh \
    --prompt "Read .ai/codex_task_001_<slug1>.md and execute all instructions inside." \
    --log-file .ai/codex_log_001_<slug1>.txt

  # Option B — direct codex exec (must close stdin or codex hangs):
  codex exec --full-auto -m gpt-5.4 \
    "Read .ai/codex_task_001_<slug1>.md and execute all instructions inside." \
    < /dev/null > .ai/codex_log_001_<slug1>.txt 2>&1

  # Run gemini tasks (must inline + close stdin per Known issues / step 6b):
  TASK=$(cat .ai/gemini_task_001_<slug3>.md)
  gemini -p "$TASK" --yolo \
    < /dev/null > .ai/gemini_log_001_<slug3>.txt 2>&1

  # After all delegate tasks finish, reconcile:
  # invoke agent-output-reconciler in this session
```

### 8. Re-plan workflow (when reassigning agents mid-round)

If the user reassigns a task to a different agent **after** plan.yml
and task files were already written (e.g., "actually, T2 should be
gemini, not codex"):

1. **Edit the agent assignment in `.coord/plan.yml`** for that
   single task. Don't bulk-replace — surgical edit only. Bulk
   `sed` replacements typically over-match and rewrite assignments
   you wanted to keep.

2. **Delete the obsolete task file** (e.g., the old
   `.ai/codex_task_<NNN>_<slug>.md` if T2 was codex and is now
   gemini). Lingering obsolete files confuse the reconciler — it
   may pick them up and report on a task that didn't actually run.

3. **Write the new task file** in the new agent's format (per step
   6a / 6b). Slug stays the same; only the agent prefix changes.

4. **If dependents already ran** (e.g., T3 ran depending on T2's
   old codex output): note in the round's `.coord/memory.yml`
   that T3's output was based on a now-stale T2; flag for re-review
   in the reconciliation report.

Re-planning mid-round is normal. The schema supports it; just be
explicit about what changed instead of letting orphan files
accumulate.

## What NOT to do

- **Don't run any agent.** This skill stops at writing files.
- **Don't fabricate `success_criteria`.** If the user hasn't told
  you what success looks like and you can't infer it from context,
  ask before writing the plan.
- **Don't create unbounded task packets.** Use `context_policy` and
  keep each task file to the critical files, constraints, and result
  contract. Link paths instead of pasting logs or long analysis.
- **Don't classify everything as Codex.** Real multi-agent runs
  benefit from heterogeneity. If your plan has 5 tasks all routed
  to Codex, reconsider whether the goal needs a multi-agent split
  or just one big Codex run.
- **Don't put architecture / design decisions in `agent: codex`
  tasks.** Those go to Claude (or to `agent-debate` if
  consequential).
- **Don't number `<NNN>` independently per task.** It matches
  `round`. All tasks in round 1 use `001` in their filename. The
  task `slug` distinguishes them.

## Heuristics for the hardest case (when to split at all)

If you find yourself writing a 1-task plan, you're using the wrong
skill — invoke `codex-delegate` or `claude` directly. The splitter
earns its keep when:

- The goal has both judgment-heavy and mechanical components.
- Multiple files / domains / stages need work in parallel.
- A long-context read + a code edit are both required.
- An adversarial review on the result would be valuable (then
  consider also queueing `agent-debate` after).

## Subagent review (keep main session lean)

**When**: ≥ 4 task files written in one round, OR ≥ 2 agents will run
in parallel.

**Why**: The main session that just wrote `plan.yml` + N task files
already holds the entire plan in context. Asking it to also verify
slug/agent/path consistency across all task files doubles the context
cost. Delegate the verification to a subagent that returns only the
verdict.

**Pattern** (Claude Code's Task tool, or equivalent subagent harness):

```
Spawn `code-reviewer` subagent with this brief:
- Read .coord/plan.yml + every .ai/{codex,gemini,claude}_task_<NNN>_*.md
  generated this round
- Verify: (a) each plan.yml task has a matching task file at correct
  path; (b) slugs in filenames match plan.yml task.slug exactly;
  (c) agent assignment matches; (d) no orphan task files from prior
  rounds; (e) each task file's "Output file(s)" section references
  the required result-summary path
- Return: PASS / FAIL + ≤ 200-word verdict + list of any drifted
  slug/agent/path mismatches

Main session reads only the verdict; never re-reads the task files.
```

If subagent reports FAIL, run step 8 (re-plan) on the flagged tasks
before invoking delegates.

## Output to user (final message format)

```
[agent-task-splitter]
  Plan: .coord/plan.yml (round 1, 4 tasks)
  Routing: 2× codex, 1× gemini, 1× claude
  DAG: T1 → [T2, T3] → T4
  Task files ready under .ai/

  Run order (respecting dependencies):
    1. codex T1 (no deps)
    2. codex T2 + gemini T3 (parallel after T1)
    3. claude T4 (after T2 + T3)

  After all 3 external tasks finish:
    invoke agent-output-reconciler
```


## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
~/.claude/CLAUDE.md → "Commit Discipline for Multi-Agent Work"). This
makes multi-agent work auditable (commit log = agent log) and enables
surgical rollback via `git revert <hash>` of just one agent's commit.

**Specific to this skill**: after the splitter writes `.coord/plan.yml` and per-agent `.ai/<agent>_task_<NNN>_<slug>.md` files, commit them as a single 'plan commit' before any agent begins execution. This gives every downstream agent's commit a clean parent to attribute work against.
