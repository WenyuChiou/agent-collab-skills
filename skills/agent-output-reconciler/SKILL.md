---
name: agent-output-reconciler
description: Use when multiple agent results must be checked for missing evidence, scope drift, contradictions, and merge conflicts before an acceptance decision.
---

# agent-output-reconciler

Reconcile completed task results into one evidence-based report. This skill
describes what happened and what conflicts remain. It does not accept work,
merge changes, retry tasks, or write canonical memory.

## Inputs

- the current plan and its task IDs, roles, scopes, dependencies, and success
  criteria;
- each task packet, result summary, structured result, and raw-log path;
- the relevant `TaskCheckpoint` and latest `PolicyDecision`;
- repository diff and test evidence.

Current plans use provider-neutral roles: `primary-agent`,
`delegated-executor`, `reviewer`, and `synthesizer`. Historical provider fields
may be parsed for migration only and must not influence current routing.

## Workflow

1. Validate the plan and checkpoint. If either is unreadable, stop and report a
   blocker. Do not infer missing policy values.
2. Inventory every planned task. Preserve `null`, missing, cancelled,
   declined, degraded, and failed results as distinct states.
3. Filter unusable payloads before synthesis, while retaining a record of what
   was filtered and why. Never turn a completed prose result into `null` merely
   because an optional structured-output step failed.
4. Compare actual changed files with each task's declared scope. Record
   justified transitive changes separately from unexplained drift.
5. Verify claimed tests and artifacts from their evidence references. A result
   without evidence remains unverified even if its prose says "success".
6. Identify file collisions, incompatible assumptions, contradictory findings,
   dependency-order violations, and unresolved risks.
7. Compose a reconciliation report using
   `references/reconciliation_template.md`.
8. Hand the report to `agent-acceptance-gate`. Do not convert a reconciliation
   recommendation into an acceptance decision.

## Output contract

The report must contain:

- plan and policy references;
- per-task role, status, evidence references, files changed, tests, and risks;
- filtered or missing result records;
- agreement that is supported by shared evidence;
- contradictions and file conflicts;
- recommended next action with explicit blockers.

Write coordination output to the configured scratch area by default. Promote a
report into a repository-owned evidence path only when the project explicitly
requires a shipping artifact or acceptance record. Scratch output is not
implicitly committable.

## Policy and context

All numeric limits come from the canonical policy evaluated by
`agent-collab policy evaluate`. Do not copy default budgets into the plan or
this skill. Re-evaluate policy after a reconciliation cycle and before any new
spawn. A `stop` decision forbids retry or spawn; a `checkpoint` decision must
be persisted before continuing.

## Safety rules

- Do not vote on factual truth. Prefer verified evidence and surface
  disagreement.
- Do not hide failed or absent results with optimistic synthesis.
- Do not paste raw logs when a path and bounded excerpt are sufficient.
- Do not modify source files, canonical memory, history, or human decisions.
- Do not commit, merge, push, or approve the round.
