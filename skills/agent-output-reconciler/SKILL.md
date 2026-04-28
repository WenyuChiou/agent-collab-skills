---
name: agent-output-reconciler
description: After multiple agents (Codex / Gemini / Claude) have completed a multi-agent round, read all their `result.json` + summary files + log tails, compute agreement / conflict / overlap, and write a `.coord/reconciliation_<NNN>.md` report with a recommended merge order or "retry these / escalate that" verdict. Use when the user asks "reconcile these N agent outputs", "did Codex and Gemini agree on this?", "synthesize the multi-agent run results", or "what did the agents do this round?".
---

# agent-output-reconciler

Cross-agent diff + synthesizer. After `agent-task-splitter` plans a
round and the delegate skills have run their tasks, this skill reads
everything they produced and reports:

- Did each task succeed?
- Where do agents agree (same files changed similarly, same
  conclusions)?
- Where do they conflict (same files changed differently, contradictory
  recommendations)?
- What's the recommended next move (merge / retry / escalate)?

## When to use

Trigger phrases:

- "Reconcile these N agent outputs."
- "Did Codex and Gemini agree on this round?"
- "Synthesize the multi-agent run results."
- "What did the agents do this round? Any conflicts?"
- "Round N is done — give me the reconciliation report."

Not for:

- Running the agents — that's `codex-delegate` / `gemini-delegate`.
- Final accept-or-reject gate before merging — that's
  `agent-acceptance-gate`. The reconciler **describes**; the
  acceptance gate **decides**.
- Single-agent runs — if only one task in `.coord/plan.yml`, there's
  nothing to reconcile.

## Inputs (auto-discovered)

1. **`.coord/plan.yml`** — the round's plan. Use the `round` field
   to identify which task files are in scope.
2. **`.ai/<agent>_log_<NNN>_<slug>.txt.result.json`** — one per
   non-Claude task. Schema (from `codex-delegate`'s contract):
   ```json
   {
     "status": "success|fallback|error",
     "delegate": "codex|gemini",
     "model": "...",
     "log_file": "...",
     "output_file": "...",
     "summary": "...",
     "risks": [],
     "files_changed": [],
     "tests_run": [],
     "timestamp_utc": "..."
   }
   ```
3. **`.ai/<agent>_result_<NNN>_<slug>.md`** — agent-written summary
   (referenced from each task file's `Acceptance` section).
4. **`.ai/<agent>_log_<NNN>_<slug>.txt`** — full log; read tail for
   error context if `status: error`.
5. **For `agent: claude` tasks** — read the Claude session's
   in-conversation output (whatever Claude said in the chat for that
   task, treated as the equivalent of `result.md`).

If the user passes specific paths, use those instead of
auto-discovery.

## Workflow

### 1. Identify round + tasks

Read `.coord/plan.yml`. If multiple rounds exist, default to the
highest `round` number unless the user specifies. Collect the list
of `(task_id, agent, slug)`.

### 2. Read each task's outputs

For each task:
- Codex / Gemini: load `result.json` + `result_<NNN>_<slug>.md` +
  log tail (last 50 lines).
- Claude: pull from current conversation history.

Flag any task where:
- `result.json` is missing → run never completed.
- `status: "error"` → run failed.
- `status: "fallback"` → run completed but in degraded mode.
- `result_<NNN>_<slug>.md` missing → agent didn't write the
  required summary (acceptance criterion violated).

### 3. Compute cross-task analysis

Build three views:

**(a) Agreement table** — per task pair, did agents converge?

| | T1 (codex) | T2 (codex) | T3 (gemini) |
|---|---|---|---|
| T1 | — | overlap: src/auth/providers.py | no overlap |
| T2 | overlap | — | no overlap |
| T3 | no overlap | no overlap | — |

Two tasks "overlap" if their `files_changed` lists share any path.
Two tasks "agree" if they overlap AND their changes don't
contradict (heuristic: same file changed by two agents → flag for
manual review unless one is `git mv`-style and the other is content
edit).

**(b) Conflict heatmap** — which files were touched by multiple
tasks?

```
src/auth/providers.py    [T1, T2]   ⚠ conflict — both edit same file
src/auth/interfaces.py   [T1]       ok
docs/auth.md             [T3]       ok
tests/test_auth.py       [T2]       ok
```

For conflicts, read the actual diffs and either:
- Confirm changes are independent (T1 added imports, T2 added a
  function — likely mergeable).
- Flag genuine collision (both rewrote the same function differently
  — needs human merge).

**(c) Aggregated risks** — concat all `risks` arrays from
result.json + risks mentioned in the .md summaries.

### 4. Suggest a recommended action

Based on the analysis:

| Situation | Recommendation |
|---|---|
| All tasks `status: success`, no conflicts, no risks | "Merge all in dependency order (T1 → T2 → T3 → T4)." |
| All success but one conflict on file X | "Merge T1, T3, T4. Manually merge T2's edits to X with T1's." |
| One task `status: error` | "Retry T2 (failure reason: <log tail summary>). Don't merge other tasks until T2 succeeds, since T4 depends on T2." |
| One task `status: fallback` | "Review T3's degraded output before merging. Acceptance criteria may not have been met." |
| Risks flagged | "Address risks before merging: ..." |
| Cross-agent contradiction (e.g., Codex says X, Gemini's review says X is wrong) | "Escalate: invoke `agent-debate` on the contested point before deciding." |

### 5. Write `.coord/reconciliation_<NNN>.md`

Format (full template: `references/reconciliation_template.md`):

```markdown
# Multi-agent reconciliation — round 1

**Goal:** Refactor the auth module into plugin-based architecture
**Created:** 2026-04-28T10:30:00Z
**Tasks:** 4 (2 codex, 1 gemini, 1 claude)

## Per-task summary

### T1 — codex — extract-interfaces  ✅ success
Files: src/auth/interfaces.py (+47 lines)
Tests: pytest tests/auth/test_interfaces.py PASS
Risks: none reported.

### T2 — codex — refactor-providers  ⚠ fallback
Files: src/auth/providers/google.py, src/auth/providers/saml.py (+93 / -41)
Tests: pytest tests/auth/test_providers.py — 1 FAIL (test_legacy_compat)
Risks:
  - Backwards compat with legacy.py possibly broken; test_legacy_compat is failing.

### T3 — gemini — review-doc-coverage  ✅ success
Output: 12 docstrings flagged as outdated (still mention legacy class).
Risks: none reported.

### T4 — claude — design-review  ✅ success
Verdict: YES, the refactor is sound. Specific concerns: the
test_legacy_compat failure suggests we may need a deprecation
shim before removing legacy.py.

## Cross-task analysis

### Agreement
- T1 and T2 share scope on src/auth/* — both touched only files in
  their declared in-scope globs. ✅
- T3's doc review aligns with T2's implementation: T3 flagged the
  same legacy references that T2 should have removed.
- T4's design review confirms T1's interface choice.

### Conflicts
- None on file paths.
- One contradiction: T2 succeeded with a fallback (legacy compat
  test failing), T4 said design is sound; T4 didn't see T2's test
  failure. Flag for user decision.

### Aggregated risks
1. test_legacy_compat is failing — backwards compat possibly broken.

## Recommended action

⚠ **Don't merge yet.** Two paths:

1. **Keep legacy.py as deprecation shim** (T4's suggestion). Re-run T2
   with this constraint, retry, then re-reconcile.
2. **Accept the breaking change.** Update test_legacy_compat to
   reflect the new architecture, then merge T1 + T2 + T3 (and treat
   T4's verdict as conditional-pass).

If you want a third opinion, invoke `agent-debate` on "should we
keep a deprecation shim for legacy auth?" before deciding.
```

### 6. Hand off

End with:

```
[agent-output-reconciler]
  Round: 1
  Tasks reconciled: 4 (2 success, 1 fallback, 1 success-claude)
  Conflicts: 0 file-level, 1 cross-agent contradiction (T2 failure ↔ T4 verdict)
  Risks: 1 (legacy compat)

  Report: .coord/reconciliation_001.md
  Recommended next: review the report and either retry T2 with shim,
  or accept breaking change. After deciding, run agent-acceptance-gate
  for the merge decision.
```

## What NOT to do

- **Don't merge anything.** Reconciler describes; acceptance gate
  decides; user merges.
- **Don't make up agreement.** If two agents touched different files
  on different topics, they didn't "agree" — they ran independently.
- **Don't suppress conflicts.** If two agents edited the same
  function, surface that even if both edits are syntactically valid.
- **Don't read the agent log files in full** — tail of last 50 lines
  is enough for error context. The summary `.md` files are the
  primary input.
- **Don't compute aggregate token cost** — that's the acceptance
  gate's job (it reads the same result.json files).
