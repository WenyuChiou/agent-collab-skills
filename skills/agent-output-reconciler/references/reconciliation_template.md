# `.coord/reconciliation_<NNN>.md` — output template

This is the canonical structure for the reconciliation report.
Use it verbatim where it applies; deviate when the round's
specifics demand it (e.g., no need for "cross-task analysis" if
there was only 1 non-Claude task).

## Template

```markdown
# Multi-agent reconciliation — round <N>

**Goal:** <copied verbatim from .coord/plan.yml>
**Created:** <ISO8601 UTC timestamp of reconciler run>
**Tasks:** <N> (<count> codex, <count> gemini, <count> claude)
**Plan source:** .coord/plan.yml

## Per-task summary

### T<n> — <agent> — <slug>  <status emoji>
- **Status:** success / fallback / error / not-run
- **Files changed:** <count> file(s) — <one-line list or summary>
- **Tests run:** <list> — <PASS / FAIL counts>
- **Token cost:** <if available from result.json>
- **Risks:** <bullet list, or "none reported">
- **Output summary:** .ai/<agent>_result_<NNN>_<slug>.md
- **Log:** .ai/<agent>_log_<NNN>_<slug>.txt

[repeat per task]

## Cross-task analysis

### Agreement

<For each pair of tasks that touched overlapping files OR addressed
overlapping concerns, describe whether they agree:>

- T1 and T2 share scope on `src/auth/*` — both touched only files
  in their declared in-scope globs. ✅
- T3's doc review aligns with T2's implementation: T3 flagged the
  same legacy references that T2 should have removed.

<Or, if no overlap:>

- Tasks touched disjoint file sets — no agreement check applicable.

### Conflicts

<List file-level conflicts (multiple tasks edited the same file)
and check whether the edits are mergeable:>

- `src/auth/providers.py` — touched by T1 (added imports) and T2
  (added new method). Independent changes; mergeable.
- `tests/test_auth.py` — touched by T2 (rewrote test_basic) and T4
  (rewrote test_basic differently). ⚠ Genuine collision; needs
  manual merge.

<Or:>

- No file-level conflicts.

<List cross-agent contradictions (one agent's output says X, another
says NOT-X about the same thing):>

- T2 succeeded with fallback (test_legacy_compat failing); T4's
  design review said "design is sound." T4 didn't see T2's failure.
  ⚠ Contradiction worth surfacing to user.

### Aggregated risks

<Concat all `risks` arrays from result.json + risks mentioned in
.md summaries; group by severity:>

**High:**
1. test_legacy_compat is failing — backwards compat possibly broken.

**Medium:**
2. T3 flagged 12 docstrings still reference the legacy class.

**Low / informational:**
- T1's new ABC name is "AuthProvider"; team conventions usually use
  "*Service" suffix — minor naming inconsistency.

## Recommended action

<Pick one of these patterns:>

**Pattern A: Clean run.** "Merge all tasks in dependency order
(T1 → T2 → T3 → T4). No outstanding issues."

**Pattern B: Mergeable with caveats.** "Merge T1, T3, T4. Manually
resolve T2's edits to `tests/test_auth.py` against T4's edits to
the same file."

**Pattern C: Retry needed.** "Don't merge T2 yet — `test_legacy_compat`
is failing. Two paths:
  1. Retry T2 with a deprecation shim (recommended)
  2. Accept the breaking change (update the test)
T1, T3, T4 can be merged independently."

**Pattern D: Escalate.** "Cross-agent contradiction between T2 and
T4 — invoke `agent-debate` on 'should we keep the deprecation shim?'
before deciding."

**Pattern E: Wholesale failure.** "Round failed — N tasks errored.
Don't merge anything. Re-plan via `agent-task-splitter` with
revised constraints."

## Next steps

<Concrete commands or actions the user can take:>

```bash
# If retrying T2:
edit .coord/plan.yml round <N> task T2 to add shim constraint
bash .claude/skills/codex-delegate/scripts/run_codex.sh \
  --prompt "Read .ai/codex_task_<NNN>_<slug>.md and execute" \
  --log-file .ai/codex_log_<NNN>_<slug>.txt
# Then re-run reconciler.

# If accepting breaking change:
manually update tests/auth/test_legacy_compat.py
git add -p && commit -m "..."
# Then run agent-acceptance-gate to confirm verdict.
```
```

## Style guidelines for the reconciler's output

- **Concrete file paths and line numbers** wherever possible.
  "T2 changed src/auth/providers.py" is better than "T2 made
  changes to auth code".
- **Surface contradictions explicitly** even if both sides could
  be defensible. The reconciler's job is to make ambiguity
  legible, not to resolve it.
- **Don't suppress weak signals.** If T1 has 1 risk and T2 has 0,
  list both — the user might catch a pattern across rounds that
  no single round shows.
- **Recommended action should be actionable**, not "consider
  re-evaluating the architecture". Say what specifically to do.
- **Length budget**: ~300-600 words for typical 3-5-task rounds.
  Longer is OK for big rounds (10+ tasks) but every line should
  earn its place.

## Common pitfalls

- **Inventing agreement.** If T1 and T3 touched totally different
  files, they didn't "agree" — they were independent. Don't
  manufacture cross-references.
- **Burying conflicts.** If two agents edited the same function
  differently, that's the most important thing to surface — make
  it the headline of the conflicts section.
- **Treating "fallback" as "success."** Fallback means the agent
  completed but in degraded mode (e.g., 1 test failing). Always
  surface this distinction.
- **Ignoring `agent: claude` tasks.** Claude tasks don't have
  result.json, but they have observable output (verdicts, designs,
  reviews) in conversation. Treat the most recent in-conversation
  output as the equivalent.
