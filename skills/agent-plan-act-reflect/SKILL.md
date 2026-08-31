---
name: agent-plan-act-reflect
description: Use when one agent must iteratively plan, act, evaluate evidence, and revise under a readable policy until acceptance, checkpoint, stop, or human escalation.
---

# agent-plan-act-reflect

Run a single-agent correction loop under the public policy/checkpoint contract.
This differs from agent-debate: plan-act-reflect revises one candidate against
evidence; debate compares genuinely consequential alternatives.

## Use this skill for

- A task with a runnable or otherwise deterministic acceptance contract.
- A candidate likely to need more than one evidence-producing cycle.
- A bounded optimization, refactor, or draft correction.

Do not use it for open-ended ideation, an unbounded “until perfect” request, or
semantic acceptance that belongs to a human.

## Preconditions

Require:

- one concrete goal
- acceptance criteria
- a readable policy_ref
- a valid checkpoint_ref
- an identified critique source

The policy is the only source for cycle, retry, context, and child limits. This
skill does not define fallback numeric limits.

If agent-collab-harness is unavailable, perform at most the currently authorized
single action and return to the human. Do not emulate an autonomous loop with
copied limits.

## Cycle

1. Validate the policy and checkpoint.
2. Evaluate policy before any delegated-executor or reviewer spawn.
3. Plan the smallest action that could add acceptance evidence.
4. Act within the declared scope.
5. Run the critique source.
6. Add evidence references and observed metrics to the checkpoint.
7. Classify progress:
   - acceptance satisfied: stop with PASS.
   - same failure: increment same_failure_retries.
   - no new artifact, test, source, decision, or blocker: increment
     no_evidence_cycles.
   - new evidence: reset the relevant no-progress counter.
8. Run `agent-collab policy evaluate` after the cycle.
9. Obey PolicyDecision:
   - continue: revise the plan using the new evidence.
   - checkpoint: write resumable state and return control.
   - stop: do not retry or spawn; return the reasons and blocker.

An infrastructure error is evidence of an error, not permission to retry. A
retry requires the next policy evaluation to permit it.

## State

Write .coord/par_<topic>.yml:

    schema_version: 2
    goal: "..."
    policy_ref: "${AGENT_COLLAB_POLICY}"
    checkpoint_ref: ".coord/task-checkpoint.json"
    acceptance_criteria:
      - "..."
    critique_source: "..."
    cycles:
      - cycle: 1
        plan_summary: "..."
        artifact_refs: ["..."]
        evidence_refs: ["..."]
        verdict: "pass | fail | error | needs-human"
        next_action: "..."
    final_status: "pass | checkpoint | stop | error | needs-human"

Write .coord/par_<topic>_final.md with:

- final status
- last PolicyDecision
- acceptance evidence
- unsuccessful attempts
- unresolved risks
- human decision required, if any

Both files are scratch by default. Promote only explicit shipping or acceptance
evidence.

## Memory

Never write a lesson directly to canonical memory. Create a proposal under
.coord/memory-proposals/ with evidence references. Applying it requires a
recorded human approval and appends a new event; it never edits an older event.

## Invariants

- Evaluate after every cycle and before every spawn.
- Stop at policy limits; do not silently extend them.
- Agent self-critique is not independent acceptance.
- Human semantic gates cannot be replaced by an aggregate agent score.
- PASS requires cited acceptance evidence, not “looks good”.
