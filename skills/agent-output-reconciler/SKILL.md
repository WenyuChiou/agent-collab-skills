---
name: agent-output-reconciler
description: Use when multiple agents have completed a round and the user asks to reconcile outputs, compare Codex and Gemini, synthesize run results, identify conflicts, or decide what should be retried.
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

- Running the agents — that's `codex-delegate` (Claude lanes run via the Agent tool; `gemini-delegate` is deprecated, fails closed).
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
     "timestamp_utc": "...",

     // v0.2.2+ optional fields — see §2.6 promise/delivery contract:
     "promised": [],   // artifacts this task surfaces for downstream consumers
     "consumed": []    // artifacts this task used from upstream tasks
   }
   ```
   Each entry in `risks` must be a single sentence (≤ 30 words).
   Long-form analysis belongs in `output_file`, not here — verbose
   `risks` entries are a context-contract violation and the
   reconciler should flag them.
3. **`.ai/<agent>_result_<NNN>_<slug>.md`** — agent-written summary
   (referenced from each task file's `Acceptance` section).
4. **`.ai/<agent>_log_<NNN>_<slug>.txt`** — full log path; read only
   the configured tail for error context if `status: error`.
5. **For `agent: claude` tasks** — read the Claude session's
   in-conversation output (whatever Claude said in the chat for that
   task, treated as the equivalent of `result.md`).
6. **`.coord/context_<NNN>.md`** (optional, if `agent-context-budget`
   ran) — declared per-task context budgets. Reconciler uses these
   to flag oversized summaries / unbounded `risks` arrays at the
   per-task granularity, not just the plan-wide default. Absence is OK.

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
  log tail only when `status: error` (default max: last 50 lines).
- Claude: pull from current conversation history.

Flag any task where:
- `result.json` is missing → run never completed.
- `status: "error"` → run failed.
- `status: "fallback"` → run completed but in degraded mode.
- `result_<NNN>_<slug>.md` missing → agent didn't write the
  required summary (acceptance criterion violated).
- `result_<NNN>_<slug>.md` exceeds `context_policy.result_summary_word_budget`
  (default 250 words) → context contract violated.

### 2.4. Multi-locale lockstep check (catches Gemini drop / merge)

When the round's outputs include ≥ 2 locale variants of the same
file stem (e.g., `06-memory-rag.md` + `06-memory-rag.en.md` +
`06-memory-rag.zh-Hans.md`), verify they actually stayed in lockstep:

1. **Line count parity** — each mirror within ±3% of canonical's
   line count. Larger delta usually means Gemini dropped or
   duplicated a section.
2. **H2 count parity** — `grep -c '^## '` returns identical count
   across all locales.
3. **Per-table column count parity** — for each markdown table at
   position N in canonical, verify table N in each mirror has the
   same column count. (F2 incident in `docs/observed-failure-modes.md`:
   Gemini merged a 5-column Projects table's rows into a 3-column
   Tools table.)
4. **Required headline-term cross-presence** — if `plan.yml` declares
   `required_terms` for this round, each must appear in every locale
   variant. Missing in one locale = mirror sync dropped content.
5. **Anchor strict** — if repo has an anchor validator script,
   run it. Broken cross-stage links are a common drop-side-effect.

If any of these fail, **defer to the `multi-locale-mirror-sync`
preset of `agent-acceptance-gate`** rather than computing it
manually — it's already codified there.

Surface each lockstep failure as **HIGH** in "Aggregated risks":
the gate will demand a re-run before merging.

### 2.5. Cross-task ID / slug consistency check (catches agent drift)

Real multi-agent runs sometimes produce outputs that **claim to be
about different tasks than they actually were**. Common cause:
gemini under inline-prompt mode (no file-system access) hallucinates
plausible-but-wrong task slugs and agent assignments because it
doesn't have plan.yml loaded.

For each agent's `result.md` summary, verify:

1. **Task IDs in the summary match plan.yml's IDs.** If the agent
   ran for `T2` per plan.yml, but its summary references "T1, T2,
   T3, T4" as if doing all of them, that's drift — the agent
   restated the entire plan instead of reporting on its own task.
2. **Slugs match plan.yml's slugs.** If plan.yml says T2's slug is
   `scaffold-provider-core` but the result.md mentions
   `implement-auth-middleware` (a slug not in the plan), the agent
   invented context.
3. **Agent assignments match plan.yml.** If the agent's summary
   claims "all 4 tasks were claude" but plan.yml has mixed
   routing, the agent is treating its inline prompt as a
   stand-alone planning exercise rather than a single-task report.

Surface each drift as a **HIGH** severity item in the
"Aggregated risks" section. Don't quietly ignore it; the gate
needs to see it.

If drift is severe (entire summary is about a different task /
scenario), recommend re-running that task with file-system access
or with the prompt body itself containing all critical context
(rather than just paths to read).

### 2.6. Promise vs delivery contract check (W2 — sequential hand-off integrity)

When tasks form a sequential chain (e.g., research-agent → write-agent →
verify-agent), each task's `result.json` MAY declare a `promised` field
listing artifacts the downstream consumer is expected to use:

```json
{
  "status": "ok",
  "summary": "...",
  "promised": [
    {"kind": "video_url", "count": 5,
     "detail": ["lVdajtNpaGI", "M2Yg1kwPpts", "bJFtcwLSNxI", "abc123", "def456"]},
    {"kind": "concept_mapping", "count": 19}
  ]
}
```

The downstream consumer's `result.json` MAY declare a matching `consumed` field:

```json
{
  "consumed": [
    {"kind": "video_url", "count": 3,
     "detail": ["lVdajtNpaGI", "M2Yg1kwPpts", "bJFtcwLSNxI"]}
  ]
}
```

The reconciler computes the diff:
- Promised but not consumed → soft WARN (downstream agent ignored part of upstream contract — may be intentional / out of scope for this round)
- Consumed but not promised → **HIGH** (downstream agent invented artifacts not in any upstream `promised` list — likely hallucination)
- Counts mismatch → WARN

**Severity asymmetry rationale**: dropped artifacts (promised but not
consumed) are common in real workflows — research surfaces 10 facts,
write pass uses 7 because 3 weren't relevant. Invented artifacts
(consumed but not promised) are a different signal entirely — the
agent claims to use something nobody surfaced, which strongly
indicates fabrication. WARN vs HIGH reflects this difference in
expected legitimacy.

This is the **contract-driven hand-off** check. It catches the common
case where upstream research surfaces N facts, but downstream write
pass only uses M < N. Without this check, the contract is implicit
and silently breakable.

**Backward compatibility**: `promised` / `consumed` are optional fields.
Tasks without them skip this check (no FAIL). Adoption is incremental —
agents that opt-in benefit from the contract verification.

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
  is enough for error context, and only when status is `error`. The
  summary `.md` files and `result.json` are the primary inputs.
- **Don't paste raw logs into reconciliation reports.** Record log
  paths and compact failure summaries only.
- **Don't compute aggregate token cost** — that's the acceptance
  gate's job (it reads the same result.json files).

## Subagent review (keep main session lean)

**When**: ≥ 3 agent outputs to reconcile, OR any agent's
`result_*.md` exceeds 200 words.

**Why**: Reading 4 × full result.md files inline costs ~10 KB of
main session context. A per-agent subagent can pre-digest each
output and return only a structured ≤ 150-word verdict so the
reconciler works from compact digests, not raw summaries.

**Pattern** (parallel, one subagent per agent output):

```
For each task in plan.yml round:
  Spawn `code-reviewer` subagent with:
    - Read .ai/<agent>_result_<NNN>_<slug>.md
    - Read .ai/<agent>_log_<NNN>_<slug>.txt.result.json (status,
      risks, files_changed)
    - Return: ≤ 150-word digest = { status, key claim, risks,
      slug consistency vs plan.yml, missing-output flags }

Main session reads only the digests and writes reconciliation_<NNN>.md
from them. Never inlines the original result.md / result.json content.
```

This is the canonical pattern for "fan-out / fan-in" multi-agent
reconciliation. It keeps the main session linear in N (number of
agents) instead of quadratic in (N × avg result size).

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
~/.claude/CLAUDE.md → "Commit Discipline for Multi-Agent Work"). This
makes multi-agent work auditable (commit log = agent log) and enables
surgical rollback via `git revert <hash>` of just one agent's commit.

**Specific to this skill**: the reconciler reads each agent's output as a separate commit. If agents share an uncommitted working tree, the reconciler cannot disentangle which change came from which agent. Always commit each agent's output before invoking the reconciler.
