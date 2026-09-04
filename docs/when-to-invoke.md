# When to invoke the collaboration harness

Use Agent Collab when a task has at least one control-flow risk that ordinary
single-turn work does not cover.

## Invoke

- before two or more bounded tasks run in parallel;
- before a child, delegated executor, or reviewer is spawned;
- after every plan-act-reflect cycle;
- when the task must survive interruption or resume;
- when results need reconciliation across agents or tools;
- when memory promotion or semantic acceptance needs a human decision;
- when locale, catalog, or factual-claim presets are triggered.

## Do not invoke

- for a one-step read-only answer;
- merely because a repository is large;
- to create background loops or coordination files with no need;
- to replace project tests, evidence verification, or human authority;
- to turn a provider choice into public policy.

## Minimal flow

```text
scope and acceptance criteria
  -> validate policy and checkpoint
  -> split provider-neutral task packets
  -> evaluate policy before each spawn
  -> execute and record evidence
  -> update checkpoint and evaluate after each cycle
  -> reconcile non-null results while preserving failures
  -> deterministic acceptance gate
  -> deliver within existing authorization, or request a genuinely new decision
```

## Gate triggers

Run `agent-acceptance-gate` with:

- `multi-locale-mirror-sync` for multiple locale variants;
- `catalog-entry-add` for new catalog entries;
- `fact-check-frontier-models` for model-and-benchmark claims.

These presets complement independent review. They do not authorize merge or
substitute for authoritative sources.

## Failure handling

- Unreadable configured policy: stop and fail closed.
- Same failure at the policy limit: stop repeating that action. In v2, safe
  primary-agent diagnosis remains allowed; changing adapters is not a fix.
- No evidence progress: replan with available evidence; report a blocker when
  no safe next step exists. Do not renew slices by renaming the same evidence.
- Missing or `null` result: retain the status and exclude it from synthesis.
- Decline, cancel, or timeout: preserve terminal non-success semantics.
- Optional provider or recall outage: report degraded/SKIP only where the plan
  marks it optional; never report PASS.

## Shipping boundary

PASS is technical acceptance, not new authority. Commit, merge, release, and
cleanup remain repository-owner actions unless explicitly delegated by that
owner. Existing valid user authorization may already cover delivery; do not
request it again merely because a review or session ended. New irreversible
actions, expanded scope, and true signed-policy exceptions require a concrete
human decision. Never synthesize a human signature for ordinary continuation.
