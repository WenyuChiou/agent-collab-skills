---
name: agent-acceptance-gate
description: Use when about to commit or push a diff that touches two or more locale variants of one file stem, adds catalog or listing entries, states benchmark numbers, release dates, or licenses for named frontier models, or merges output from any subagent or delegate. Reconciles the lane results, runs the matching preset, and returns PASS, CONDITIONAL PASS, or FAIL with evidence.
---

# agent-acceptance-gate

The read-only check between "the lanes are done" and "commit or push". It
reconciles results, runs the triggered presets, and returns a verdict. It
never merges, commits, retries, or turns a decline, cancellation, timeout, or
failure into success. Since 0.6.0 it includes the former
`agent-output-reconciler`.

## Inputs

- the lane table or plan: lane ids, roles, scopes, acceptance criteria;
- each lane's returned summary, evidence paths, and log paths;
- the merged diff and the project's verification commands;
- in harness mode, the `TaskCheckpoint` and latest `PolicyDecision`;
- prior human decision records, if any.

Historical provider fields may be read for migration only. Current checks use
lane or task ids and roles.

## Step 0: Harness mode only

Validate the plan, checkpoint, and policy before anything else. An unreadable
configured policy, plan, or checkpoint is a fail-closed blocker: stop and
report it. Do not infer missing policy values.

## Step 1: Reconcile

1. Inventory every planned lane. Keep missing, `null`, declined, cancelled,
   timed-out, degraded, and failed as distinct states. Never invent an absent
   result.
2. Filter unusable results out of synthesis and record what was filtered and
   why. A completed prose result is not `null` just because an optional
   structured-output step failed.
3. Compare changed files with each lane's declared scope. Record justified
   transitive changes separately; unexplained drift is FAIL.
4. Bind each result to its task, attempt, and baseline with the
   [task-content evidence review](../../docs/task-content-evidence.md). Stale
   or wrong-task evidence stays unverified. Account for pre-existing dirty
   state and parallel writers before attributing a change. File times alone
   cannot prove or disprove success.
5. Re-run claimed checks or verify their evidence. A "success" with no
   evidence is unverified.
6. List file collisions, contradictory findings, incompatible assumptions, and
   dependency-order violations.

Report shape: [references/reconciliation_template.md](references/reconciliation_template.md).
Harness mode writes it to scratch; native mode keeps it short in the
conversation or PR body.

## Step 2: Presets (mandatory when triggered)

| Trigger in the diff | Preset |
|---|---|
| two or more locale variants of one file stem | `multi-locale-mirror-sync` |
| new catalog or listing entries | `catalog-entry-add` |
| a named frontier model with a benchmark number, release date, or license claim | `fact-check-frontier-models` |

Presets are declarative review contracts in `presets/`, not an executable
engine; follow their checks. They add to independent review and source
verification and never replace them. If a triggered preset cannot run, report
a blocker or an explicit degraded state, never PASS. Structural parity
(heading counts, line counts, ordering) is not content parity: check meaning
adversarially and quote the passages that disagree.

## Step 3: Verify and decide

1. Run each lane's acceptance criteria and the merge-level verification
   command on the merged result. Never invent missing criteria; mark manual
   checks as manual.
2. Check unresolved high-severity risks and reconciliation blockers.
3. For external facts, cite authoritative sources and say whether each was
   verified locally.
4. Harness mode: evaluate the policy after the gate cycle and write a new
   immutable acceptance record. Never overwrite a prior run or human
   decision.
5. Native mode: put the verdict and its evidence in the conversation or the
   PR body.

All numeric budgets and retry limits come from the canonical policy in harness
mode or from the host in native mode. This skill and its presets do not copy
default values.

## Verdicts

- `PASS`: every required check passed and no blocker remains. Technically
  acceptable; not authorization to merge.
- `CONDITIONAL PASS`: deterministic checks passed, but an explicit human
  action, a degraded optional check, or a documented non-blocking condition
  remains.
- `FAIL`: any required criterion, scope, policy, evidence, preset, or blocker
  check failed.

A human may approve a documented exception, but the original gate record stays
unchanged. The new decision records gate, actor, decision, timestamp,
rationale, and affected action hash. An override never rewrites a failed test
into a passing one. Existing authorization may already cover delivery; do not
ask again just because a review, session, or slice ended. A genuinely new
human gate still needs a separate recorded decision bound to the specific
affected action.

## Output

- verdict;
- per-lane status and criterion results, including filtered or missing lanes;
- scope and preset results;
- commands with exit codes, bounded excerpts, and artifact paths;
- risks, degraded checks, and blockers;
- pending or recorded human decision reference;
- in harness mode, also the run ID, timestamp, plan, checkpoint, and policy
  references, and the action hash that any later human decision binds to.

Coordination scratch is gitignored by default. Promote only an explicitly
required checkpoint snapshot, shipping artifact, or acceptance record. See
[references/acceptance_checklist.md](references/acceptance_checklist.md) for
the verification taxonomy.

## Prohibitions

- Do not run implementation agents or decide retries.
- Do not mutate source, the plan, checkpoint history, or canonical memory.
- Do not overwrite prior acceptance or human-decision records.
- Do not treat agent consensus as evidence.
- Do not commit, merge, push, release, or delete branches.
