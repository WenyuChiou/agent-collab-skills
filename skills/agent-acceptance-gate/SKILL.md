---
name: agent-acceptance-gate
description: Use when reconciled multi-agent output needs an evidence-based PASS, CONDITIONAL PASS, or FAIL record before a human shipping decision.
---

# agent-acceptance-gate

Run the final read-only verification step for a multi-agent round. The gate
checks declared criteria and produces acceptance evidence. It never merges,
commits, retries, or silently converts a decline, cancellation, timeout, or
failure into success.

## Inputs

- current provider-neutral plan and success criteria;
- validated `TaskCheckpoint` and latest `PolicyDecision`;
- task results, evidence references, and raw-log paths;
- reconciliation report;
- repository diff and project-specific verification commands;
- prior human decision records, if any.

Historical provider fields may be read for migration only. Current checks use
task IDs and roles (`primary-agent`, `delegated-executor`, `reviewer`, and
`synthesizer`).

## Mandatory preset routing

Run the matching preset when a staged diff:

- touches multiple locale variants of the same document stem;
- adds entries to a catalog; or
- changes a model-and-benchmark claim.

The bundled preset names are `multi-locale-mirror-sync`,
`catalog-entry-add`, and `fact-check-frontier-models`.

Presets encode additional failure-mode checks; they do not replace independent
review or factual source verification. If a preset cannot run, report a blocker
or explicit degraded state. Never claim PASS.

## Workflow

1. Validate the plan, checkpoint, and policy. Unreadable configured policy is a
   fail-closed blocker.
2. Inventory all tasks and required artifacts. Missing, `null`, declined,
   cancelled, timeout, degraded, and failed states remain distinct.
3. Verify each declared success criterion with a deterministic command,
   artifact check, or explicit manual-check requirement. Never invent missing
   criteria.
4. Compare changed files with declared task scopes and record unexplained drift
   as FAIL.
5. Check structured statuses, claimed tests, evidence references, reconciliation
   blockers, and unresolved high-severity risks.
6. Run triggered presets and applicable project invariants. For external facts,
   cite authoritative sources and mark whether evidence was locally verified.
7. Evaluate canonical policy after the gate cycle. Policy `stop` forbids retry
   or spawn; policy `checkpoint` must be persisted before further work.
8. Write a new immutable acceptance evidence record. Do not overwrite a prior
   run or human decision.
9. Present the evidence to the authorized human. Human approval, decline, or
   revision is a separate append-only decision record tied to the action hash.

All numeric budgets and retry limits come only from the canonical policy. This
skill and its presets must not copy default values.

## Verdicts

- `PASS`: every required check passed and no blocker remains. This means
  technically acceptable, not human-authorized to merge.
- `CONDITIONAL PASS`: deterministic checks passed but an explicit human action,
  degraded optional check, or documented non-blocking condition remains.
- `FAIL`: any required criterion, scope, policy, evidence, preset, or blocker
  check failed.

A human may approve a documented exception, but the original gate record stays
immutable. The new decision must include gate, actor, decision, timestamp,
rationale, and affected action hash. A human override does not rewrite a failed
test into a passing test.

## Output contract

Write an acceptance evidence artifact with:

- run ID, timestamp, plan/checkpoint/policy references, and action hash;
- per-task status and criterion results;
- scope and preset results;
- test commands, exit codes, bounded excerpts, and artifact paths;
- risks, degraded checks, and blockers;
- technical verdict;
- pending or recorded human decision reference.

Coordination scratch is gitignored by default. Promote only explicitly required
checkpoint snapshots, shipping artifacts, or acceptance evidence into a
repository-owned path.

See `references/acceptance_checklist.md` for the verification taxonomy.

## Prohibitions

- Do not run implementation agents or decide retries.
- Do not mutate source, plan, checkpoint history, or canonical memory.
- Do not overwrite prior acceptance or human-decision records.
- Do not treat agent consensus as evidence.
- Do not commit, merge, push, release, or delete branches.
