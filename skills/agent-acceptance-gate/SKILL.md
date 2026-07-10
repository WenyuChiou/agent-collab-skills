---
name: agent-acceptance-gate
description: Use when a multi-agent round needs a pre-merge gate, pre-commit check, verification before push, or a PASS/FAIL decision after reconciliation.
---

# agent-acceptance-gate

The last gate before merging multi-agent output. The reconciler
**describes** what each agent did; the acceptance-gate **decides**
whether the round is mergeable.

It runs the `success_criteria` declared in `.coord/plan.yml`,
aggregates risks, optionally audits prose, checks budget, and
produces a single PASS / FAIL / RETRY verdict per task and overall.

## Why use this instead of "I'll grep it myself"

The gate replaces ad-hoc inline shell verification with one structured
verdict. Concrete differences observed in production (`measured-benefits.md`
R5 + Phase D):

| Inline shell verification | This skill (R5 measured) |
|---|---|
| Main session runs 5+ grep / diff commands, interprets each output, drafts a manual PASS/FAIL — ~10k tokens of shell-debugging in context | Subagent runs all checks + returns ~2k token structured report → **~5× token saving** in main session |
| Easy to forget a check ("did I grep for banned phrases this time?") | Preset YAML encodes the full check set — no missed checks |
| Catches one drift case; misses cross-language echoes | `cross_document_link_text_parity` v0.2.3 caught 9+ real drift bugs the human audit missed |

### The DeepSeek-R2 fabrication that almost shipped

2026-05-13 session: Codex generated a paragraph claiming "DeepSeek-R2
reaches 94.2% on GPQA Diamond" — pure fabrication. Manual grep on the
diff missed it because the claim was internally consistent. Only a
third-party reviewer agent doing live `gh api` search caught it.

The `fact-check-frontier-models` preset was built directly from this
incident. Running the preset would have caught the fabrication
automatically by hitting arxiv + GitHub for each (model, benchmark, %)
triple in the diff.

→ **F14**: the preset existed by 2026-05-14, but a subsequent operator
skipped it because "the task feels simple". The Phase D dogfood
(49 files × 3 locales, 50k tokens inline vs 16k with gate = ~3× saving)
proved the gate catches drift the operator misses. **The cost of running
the gate is much smaller than the cost of one missed drift.**

### Mandatory invocation triggers (no judgment call)

These triggers are mechanical — if any fire, invoke the matching preset
**before commit**. Skipping is F14 territory.

| Trigger condition | MUST invoke |
|---|---|
| Diff touches ≥ 2 locale variants of same file stem (e.g., `06-x.md` + `06-x.en.md` + `06-x.zh-Hans.md`) | `--preset=multi-locale-mirror-sync --stem=<stem>` |
| Diff adds entries to any catalog file (project listings, framework comparisons) | `--preset=catalog-entry-add --catalog-file=<path>` |
| Diff touches a "frontier model" claim (model name within 3 lines of a benchmark %, e.g., "GPT-5.5 reaches 94% GPQA") | `--preset=fact-check-frontier-models --file=<path> --models=<csv>` |

### CLAUDE.md snippet to enforce the gate

```markdown
## Acceptance gate rule (enforced)

Before any commit that:
- touches ≥ 2 locale variants of the same file stem → invoke
  `Skill("agent-collab-workspace:agent-acceptance-gate",
         args="--preset=multi-locale-mirror-sync --stem=<stem>")`
- adds catalog entries → invoke `--preset=catalog-entry-add ...`
- includes a frontier model + benchmark % claim → invoke
  `--preset=fact-check-frontier-models ...`

Skip only when the trigger does not apply (single-file diff, pure
mechanical rename, etc.). NEVER skip when the trigger fires —
this is the F14 anti-pattern that shipped the DeepSeek-R2
fabrication.

When the preset FAILS:
1. Read the FAIL reasons in the gate report.
2. Either fix-and-rerun (cheap drift) or re-delegate the task with
   tighter constraints (systemic drift).
3. Do NOT override the FAIL by hand. The whole point of the gate is
   that the operator's judgment failed earlier — adding more operator
   judgment on top defeats it.
```

## When to use

Trigger phrases:

- "Run the acceptance gate."
- "Pre-commit check across multi-agent output."
- "Are we ready to commit this round?"
- "Verify all multi-agent output before I push."
- "Gate this round — go or no-go?"

Not for:

- Describing what each agent did → that's
  `agent-output-reconciler`.
- Running the agents → delegate skills.
- Per-task acceptance during agent execution → that's the agent
  skill itself (codex-delegate's wrapper checks its own task's
  acceptance).
- Single-agent runs without a `.coord/plan.yml` → just run
  `pytest` and call it a day.

## Inputs (auto-discovered)

1. **`.coord/plan.yml`** — round, tasks, `success_criteria` per
   task, `budget` if declared, and `context_policy` if declared.
2. **`.ai/<agent>_log_<NNN>_<slug>.txt.result.json`** — token usage,
   risks, files_changed. Filename uses double extension by design
   (codex-delegate appends `.result.json` to the log path; see
   `examples/codex_log_001_*.txt.result.json.sample`).
3. **`.coord/reconciliation_<NNN>.md`** — reconciler's verdict; if
   reconciler said "retry", gate respects that.
4. **`.coord/context_<NNN>.md`** (optional, if `agent-context-budget`
   ran) — declared per-task context budgets for this round. Gate
   checks that actual summary sizes / log tail counts honored the
   declared budgets. Absence is OK (the round may not have used
   the context-budget skill); presence means the gate enforces it.
5. **For prose changes**: if any `result.json` shows files_changed
   matching `*.md`, `*.tex`, `*.docx`, the gate optionally invokes
   `academic-writing-skills` banned-word + claim-evidence audit.
   (Skipped silently if `academic-writing-skills` not installed.)

## Presets (one-line invocation for common acceptance shapes)

Instead of hand-writing acceptance criteria every time, invoke a
preset that codifies a tested set of checks:

| Preset | When to use | Invocation |
|---|---|---|
| `multi-locale-mirror-sync` | After zh-TW → en + zh-Hans mirror sync (or any N-locale fan-out) | `agent-acceptance-gate --preset=multi-locale-mirror-sync --stem=stages/06-foo --required-terms="A,B,C"` |
| `catalog-entry-add` | Added entries to a catalog file | `agent-acceptance-gate --preset=catalog-entry-add --catalog-file=resources/foo.md --new-entries="org/repo1,org/repo2"` |
| `fact-check-frontier-models` | Touched a frontier-model table | `agent-acceptance-gate --preset=fact-check-frontier-models --file=stages/06-foo.md --models="GPT-5.5,Claude Opus 4.7"` |

Preset YAMLs live in `presets/`. Each codifies failure modes
observed in real dogfooding (see `docs/observed-failure-modes.md`).
Don't hand-write checks if a preset covers your case.

**Mandatory preset trigger conditions** (gate auto-suggests if you
don't specify):

- Diff touches ≥ 2 locale variants of the same file stem →
  `multi-locale-mirror-sync` MUST be invoked.
- Diff adds entries to any file under `resources/` matching catalog
  shape → `catalog-entry-add` MUST be invoked.
- Diff touches a frontier-model claim (regex: model name within 3
  lines of a benchmark %) → `fact-check-frontier-models` MUST be
  invoked.

### Preset is mandatory when trigger fires (F14, 2026-05-14)

The presets above are not "consider running" — they are **must run
before commit** when their trigger condition matches. The F14
incident (`docs/observed-failure-modes.md`) is the cautionary tale:
a Phase D run on `awesome-agentic-ai-zh` touched 49 files across 3
locale variants (textbook `multi-locale-mirror-sync` trigger),
skipped the preset, used a `code-reviewer` subagent instead, and
shipped a drift the preset's `cross_document_link_text_parity` check
was designed to catch.

**Why skipping is tempting**: when the work feels "just a title
sweep, surely nothing can go wrong", the operator short-circuits the
mandatory invocation. The presets exist precisely because that
intuition is wrong — drift hides in the "obvious" cases.

**Anti-patterns**:

1. **Replacing the preset with an ad-hoc `code-reviewer` subagent**.
   The subagent is a reasonable backup but cannot substitute for
   the codified checks, which encode observed failure modes. Run
   both, not one-instead-of-the-other.
2. **"I'll run the preset later"**. The preset's diff-size check is
   tied to the commit-staged diff; later means re-staging or
   running against history. Just run it before commit.
3. **Manually grep'ing for the same patterns the preset already
   knows**. You'll miss one. The preset won't.

**Enforcement options** (in increasing strength):

- **Documentation** (current): this section + `CLAUDE.md` rule.
  Held in 5 of 6 Phase B rounds, failed in Phase D.
- **Pre-commit hook** (recommended): mechanical check that any
  mirror-diff commit prompts for preset invocation. Recipe in
  `docs/observed-failure-modes.md` F14.
- **Block on missing preset run** (strict): pre-commit hook fails
  unless a `.coord/acceptance_<NNN>.md` file exists in the commit.
  Use this in repos where the cost of drift is high (curriculum,
  public docs, anything user-facing).

## Workflow

### 1. Identify round

Read `.coord/plan.yml`. Default to highest `round`. User can
override.

### 2. Run each task's success_criteria

For each task with `agent: codex` or `agent: claude-cheap` (or, in historical pre-0.3.0 rounds, `agent: gemini`):

- Each `success_criteria` is either a runnable command or a
  checkable assertion.
- Runnable command (`pytest tests/auth`, `mypy src/`, `npm test`):
  - Execute it. Record exit code + last 20 lines of output.
  - PASS = exit 0; FAIL otherwise.
- Checkable assertion (`"src/auth/interfaces.py exists and defines AuthProvider ABC"`):
  - Translate to a verification (file existence, grep, AST check).
  - Run it.
  - PASS = assertion holds; FAIL otherwise.

For `agent: claude` tasks:

- `success_criteria` is usually "explicit YES/NO verdict in chat".
- Read the current Claude conversation for the most recent
  statement matching the criterion. Mark PASS / FAIL based on
  whether Claude actually delivered the verdict.

### 3. Check the reconciler's recommendation

Read `.coord/reconciliation_<NNN>.md`. If the reconciler's
"Recommended action" section says anything other than "merge all"
(e.g., "retry T2", "escalate", "manual merge needed"), the gate's
verdict is **at most CONDITIONAL PASS** — the user is responsible
for resolving the reconciler's flagged issue.

### 4. Aggregate risks

Concat all `risks` arrays from `result.json` files. Group by
severity (gate makes its own call if not labeled — `failed test` =
high; `legacy compat concern noted but not breaking` = medium).

### 5. Optional: prose audit

If any task changed `*.md` / `*.tex` files AND
`academic-writing-skills` is installed:

- Invoke its banned-word audit on the changed files.
- Invoke its claim-evidence audit if `.paper/claims.yml` exists in
  the project.
- Add results to the gate report.

If `academic-writing-skills` isn't installed, skip silently — don't
fail the gate just because prose audit isn't available.

### 6. Cost / budget check

If `.coord/plan.yml` declared a `budget.tokens`:

- Sum `tokens` field across all `result.json` files for this round
  (if present; some delegate wrappers don't write tokens — handle
  missing gracefully).
- PASS if under budget; FAIL with clear "you exceeded budget by X
  tokens" if over.

If no budget declared, skip — don't invent one.

### 6.5. Context contract check

If `.coord/plan.yml` declares `context_policy` OR
`.coord/context_<NNN>.md` exists, enforce both:

**From `context_policy` (plan-wide defaults):**
- Each result summary must be at or below
  `result_summary_word_budget` (default 250 words).
- Reconciliation and acceptance reports must reference raw logs by
  path, not paste them.
- Failure diagnostics may include only the configured log tail
  (default 50 lines).
- `.coord/memory.yml` entries must be promoted facts: decisions, open
  questions, artifact pointers, or session outcomes. Long analysis in
  memory is a context violation.

**From `context_<NNN>.md` (per-task overrides, if present):**
- Read the per-task `task_packet_token_budget` declarations.
- For each task, verify `<task-id>` packet (the actual `.ai/<agent>_task_<NNN>_<slug>.md`)
  did not exceed declared budget (rough char/word count, no need for
  exact tokenizer — flag at >120% of declared).
- Verify `result_summary_word_budget` per-task (overrides plan-wide
  default if specified).
- Verify `raw_logs_inline: path-only` was honored — any log file
  pasted inline in reconciliation / acceptance is a violation.

**Debate caps (if `.coord/debate_*.md` files exist and are linked from `plan.yml`):**
- Each per-turn Pro / Con argument ≤ 400 words.
- Total debate rounds ≤ 3 (unless `plan.yml` declares `debate_rounds: N` override).
- Final synthesis section ≤ 250 words.
- Total debate file size ≤ 8 KB.
- Violations: gate at most CONDITIONAL PASS; recommend compressing
  the transcript before promoting any decision to memory.

Violations make the verdict at most **CONDITIONAL PASS**. If the
violation hides acceptance evidence, mark **FAIL** and require a
bounded summary rewrite.

### 6.6. Scope diff check (W1 — work boundary enforcement, file-level)

Compare `git diff --name-only` against each task's declared `files_in_scope`
(from `.coord/plan.yml` task entries).

For each modified file F in the diff:
- If F appears in **any** task's `files_in_scope` → in-scope ✅
- If F is a "transitive fix" (e.g., anchor heading sync, mentioned in
  task's result.md as intentional spillover with justification) →
  accept with WARN
- Otherwise → **FAIL** with message: `Scope violation: <file> not in
  any task's files_in_scope; agent went outside brief`

This is the **file-level enforcement** for the W1 work boundary discipline.
Without this check, brief writing "files in scope: [a, b, c]" is just
guidance — the agent may still touch [d, e, f] and only manual diff
review would catch it.

**What this check does NOT verify** (be honest):
- It does NOT verify the agent actually emitted the `Confirmed scope:`
  echo block before editing. `git diff --name-only` only tells you which
  files got modified — it can't reconstruct whether the echo was the
  agent's first action. If you need echo verification, add an
  optional secondary check that greps the agent's `result.md` for the
  `Confirmed scope:` sentinel string.
- It does NOT catch scope violations WITHIN a permitted file (e.g.,
  agent was told to edit `foo.md` section §3 but also edited §1). Use
  finer-grained acceptance criteria (per-section grep / line-range
  check) for that.

**F11 + F12 specific catches**:
- If diff touches `resources/style-guide*.md` AND the change replaces
  a literal term in a contrast table → FAIL (F11 violation)
- If diff inserts a line matching pattern `^>?\s*(Attribution|Source|
  Credits|Citation)s?:\s*` that wasn't requested in brief → FAIL
  (F12 violation)

### 7. Compose verdict

| Condition | Verdict |
|---|---|
| All success_criteria PASS, no risks, reconciler says merge, prose audit clean, budget ok | **✅ PASS** |
| All success_criteria PASS but reconciler flagged something | **⚠ CONDITIONAL PASS** — user resolves reconciler's issue, then re-run gate |
| Context contract violated but evidence is still checkable | **⚠ CONDITIONAL PASS** — rewrite bounded summaries before next round |
| Any success_criterion FAIL | **❌ FAIL** — list which task / criterion |
| Risks include unresolved blockers | **❌ FAIL** — must address before merge |
| Budget exceeded | **❌ FAIL — over budget** (user explicitly OK can override by editing plan.yml) |

### 8. Write `.coord/acceptance_<NNN>.md`

```markdown
# Acceptance gate — round 1

**Verdict:** ⚠ CONDITIONAL PASS
**Run:** 2026-04-28T11:50:00Z
**Tasks gated:** 4
**Reconciliation report:** .coord/reconciliation_001.md

## Per-task results

### T1 — codex — extract-interfaces
- ✅ "src/auth/interfaces.py exists and defines AuthProvider ABC" — file present, grep matches.
- ✅ "no other source files modified" — git diff scope confirmed.

### T2 — codex — refactor-providers
- ❌ "pytest tests/auth/test_providers.py passes" — test_legacy_compat FAILED.
- ✅ "no imports of src.auth.legacy from other modules" — grep clean.

### T3 — gemini — review-doc-coverage
- ✅ "every public symbol in src/auth has a docstring" — gemini's report confirms.
- ✅ "report flags any docstring still mentioning the legacy class" — 12 flagged.

### T4 — claude — design-review
- ✅ "explicit YES/NO verdict + rationale in chat" — said YES with conditional concerns.

## Risks

- **High:** test_legacy_compat failing in T2. Means backwards compat
  is broken under the refactor.

## Budget

Declared: 200,000 tokens. Used: 142,000. ✅ Under budget.

## Reconciler verdict

The reconciler flagged a cross-agent contradiction: T2's fallback
status conflicts with T4's "design is sound" verdict. The reconciler
recommended either retrying T2 with a deprecation shim, or accepting
the breaking change.

## Decision

⚠ **CONDITIONAL PASS.** Don't merge T2 in its current state.

**To unblock:**

Path 1 — Retry T2 with deprecation shim:
  1. Edit `.coord/plan.yml` round 1, T2: add to constraints
     "preserve test_legacy_compat backward compatibility via shim".
  2. Re-run T2 (`bash .claude/skills/codex-delegate/scripts/run_codex.sh ...`).
  3. Re-run reconciler + gate.

Path 2 — Accept breaking change:
  1. Update `tests/auth/test_legacy_compat.py` to reflect new
     architecture.
  2. Re-run pytest manually to confirm green.
  3. Manually mark this gate PASS by replacing the verdict above
     with ✅ PASS + your override rationale.

T1, T3, T4 are individually mergeable; only T2 is blocked.
```

### 9. Hand off

```
[agent-acceptance-gate]
  Round: 1
  Verdict: ⚠ CONDITIONAL PASS
  Tasks gated: 4 (3 pass, 1 fail)
  Risks: 1 high (test_legacy_compat)
  Budget: 142k / 200k tokens — under
  Report: .coord/acceptance_001.md

  Don't push yet. Resolve T2 (see report for two paths).
  Then re-invoke this skill.
```

## What NOT to do

- **Don't merge or commit.** The gate decides; the user merges.
- **Don't override the reconciler.** If reconciler said retry, the
  gate's max verdict is CONDITIONAL PASS.
- **Don't invent success criteria.** If `.coord/plan.yml` doesn't
  declare any for a task, that's a planning bug — flag it, don't
  invent assertions.
- **Don't skip the prose audit silently if it found issues** — only
  skip silently if the audit skill isn't available. If it ran and
  flagged banned words, those go in the report.
- **Don't fail the gate on things the user can override.** Budget
  overrun is a FAIL but the user can edit plan.yml's budget and
  re-run. Test failures are a real FAIL.
- **Don't run inside an agent's task.** This skill runs as a final
  step **after** all delegate tasks completed and the reconciler
  has been read. It's a Claude-in-session skill, not delegated.

## Subagent review (keep main session lean)

**When**: ≥ 5 `success_criteria` checks to run, OR ≥ 4 result.json
files to aggregate, OR prose audit on ≥ 3 changed `.md` files.

**Why**: The acceptance gate naturally pulls a lot of data into the
main session (test outputs, all result.json files, reconciliation
report, optional banned-word audits). Delegating the mechanical
checks to a subagent and keeping only the structured verdict in
main session cuts context cost roughly 3-5×.

**Pattern**:

```
Spawn `code-reviewer` subagent with:
  - Read .coord/plan.yml + .coord/reconciliation_<NNN>.md + every
    .ai/*.result.json + .coord/context_<NNN>.md (if present)
  - For each success_criterion in plan.yml: execute the command
    or check the assertion (file existence, grep, etc.)
  - Aggregate risks; sum tokens against budget
  - Verify context contract (summary word budgets, raw-log-paths-only,
    memory promotion rules, debate caps)
  - Return: structured verdict
    { verdict: PASS/CONDITIONAL_PASS/FAIL,
      per_task: [...], risks: [...], budget_used: N,
      context_violations: [...], next_actions: [...] }

Main session reads the structured verdict and writes
.coord/acceptance_<NNN>.md from it without re-reading the result.json /
test output files.
```

This makes the gate auditable AND keeps the gating session itself
under the context_policy main_session_token_budget.

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
~/.claude/CLAUDE.md → "Commit Discipline for Multi-Agent Work"). This
makes multi-agent work auditable (commit log = agent log) and enables
surgical rollback via `git revert <hash>` of just one agent's commit.

**Specific to this skill**: this gate IS the final pre-merge commit check. It reads the per-agent commits between the round's plan commit and HEAD, verifies they collectively satisfy `success_criteria`, and writes its PASS/FAIL verdict to `.coord/acceptance_<NNN>.md` as a final commit. Only after PASS does the round get merged to main.
