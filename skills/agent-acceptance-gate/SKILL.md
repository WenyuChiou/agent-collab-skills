---
name: agent-acceptance-gate
description: Pre-merge / pre-commit checklist after a multi-agent round completes. Reads `.coord/plan.yml` for `success_criteria`, runs each verification command, aggregates `risks` from `result.json`, optionally calls academic-writing-skills banned-word audit on prose changes, checks token cost vs budget, and writes a PASS/FAIL verdict to `.coord/acceptance_<NNN>.md`. Use when the user asks "run the acceptance gate", "pre-commit check before merging", "are we ready to commit this round?", "verify all multi-agent output before I push".
---

# agent-acceptance-gate

The last gate before merging multi-agent output. The reconciler
**describes** what each agent did; the acceptance-gate **decides**
whether the round is mergeable.

It runs the `success_criteria` declared in `.coord/plan.yml`,
aggregates risks, optionally audits prose, checks budget, and
produces a single PASS / FAIL / RETRY verdict per task and overall.

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
   task, `budget` if declared.
2. **`.ai/<agent>_log_<NNN>_<slug>.txt.result.json`** — token usage,
   risks, files_changed.
3. **`.coord/reconciliation_<NNN>.md`** — reconciler's verdict; if
   reconciler said "retry", gate respects that.
4. **For prose changes**: if any `result.json` shows files_changed
   matching `*.md`, `*.tex`, `*.docx`, the gate optionally invokes
   `academic-writing-skills` banned-word + claim-evidence audit.
   (Skipped silently if `academic-writing-skills` not installed.)

## Workflow

### 1. Identify round

Read `.coord/plan.yml`. Default to highest `round`. User can
override.

### 2. Run each task's success_criteria

For each task with `agent: codex` or `agent: gemini`:

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

### 7. Compose verdict

| Condition | Verdict |
|---|---|
| All success_criteria PASS, no risks, reconciler says merge, prose audit clean, budget ok | **✅ PASS** |
| All success_criteria PASS but reconciler flagged something | **⚠ CONDITIONAL PASS** — user resolves reconciler's issue, then re-run gate |
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
