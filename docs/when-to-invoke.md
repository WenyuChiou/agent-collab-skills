# When to invoke the collaboration harness

Use Agent Collab when a task has at least one control-flow risk that ordinary
single-turn work does not cover.

## Invoke

- before two or more lanes (subagents, workflow lanes, delegates) run on one
  goal: `agent-task-splitter`;
- when launching parallel or background lanes, or when a result or handoff
  would crowd the primary context: `agent-context-budget`;
- when a consequential decision has two plausible options: `agent-debate`;
- before committing or pushing merged lane output, or a diff that triggers a
  preset: `agent-acceptance-gate`.

## Native or harness mode

Native mode is the default for in-session fan-out with the user present: the
lane table and briefs live in the conversation, the host's limits apply, and
no plan, packet, or checkpoint is written to `.coord/` (a memory proposal at
most). Harness mode adds the policy and checkpoint
contract when a round spans sessions or tools, runs unattended, must resume,
needs a signed human gate, or `AGENT_COLLAB_POLICY` is configured. See
[native lanes](native-lanes.md).

## Do not invoke

- for a one-step read-only answer;
- merely because a repository is large;
- to create background loops or coordination files with no need;
- to replace project tests, evidence verification, or human authority;
- to turn a provider choice into public policy.

## Minimal flow

```text
scope and acceptance criteria
  -> lane table: role, model tier, disjoint scope, capped return per lane
  -> fix the merge and verification step
  -> (harness mode) validate policy and checkpoint; evaluate before each spawn
  -> run lanes and record evidence
  -> acceptance gate: reconcile results (failures preserved), run presets,
     verify the merged result
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
