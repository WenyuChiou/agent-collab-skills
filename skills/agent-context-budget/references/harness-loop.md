# Harness-mode correction loop

Formerly the body of `agent-plan-act-reflect` (deprecated in 0.6.0, stub
removed in 0.7.0). Use it only for an unattended, multi-cycle loop under a
configured `agent-collab` policy. Ordinary in-session iteration, such as
editing until the tests pass with the user present, needs no skill.

A correction loop revises one candidate against evidence. `agent-debate`
compares genuinely consequential alternatives; it is not a loop.

## Preconditions

- one concrete goal;
- acceptance criteria with a runnable or otherwise deterministic check;
- a readable `policy_ref` and a valid `checkpoint_ref`;
- an identified critique source.

The policy is the only source for cycle, retry, context, and child limits.
There are no fallback numeric limits. If `agent-collab-harness` is
unavailable, perform at most the currently authorized single action and
return to the human; do not emulate an autonomous loop with copied limits.

Do not use a loop for open-ended ideation, an unbounded "until perfect"
request, or semantic acceptance that belongs to a human.

## Cycle

1. Validate the policy and checkpoint.
2. Evaluate the policy before any delegated-executor or reviewer spawn.
3. Plan the smallest action that could add acceptance evidence.
4. Act within the declared scope.
5. Run the critique source.
6. Add evidence references and observed metrics to the checkpoint.
7. Classify progress:
   - acceptance satisfied: stop with PASS;
   - same failure: increment `same_failure_retries`;
   - no new artifact, test, source, decision, or blocker: increment
     `no_evidence_cycles`;
   - new evidence: reset the relevant no-progress counter.
8. Run `agent-collab policy evaluate` after the cycle.
9. Obey the `PolicyDecision`:
   - `continue`: revise the plan using the new evidence.
   - `checkpoint`: save resumable state. For a v2 slice with auto_continue,
     use `agent-collab checkpoint advance` and continue the same authorized
     goal; no human override is needed for an ordinary eligible slice
     transition. For a v2 action checkpoint that requires context compaction,
     keep evidence and authorization in a smaller linked packet, record
     measured active sizes, then re-evaluate before execution. Maintenance is
     not a human approval gate.
   - `stop`: obey its scope. An action stop prohibits repeating that action;
     the primary-agent may diagnose read-only or prepare an evidence-backed
     correction. A goal stop preserves the hard limit or human gate.
   - v1 decisions keep their original checkpoint and stop semantics until an
     explicit migration; do not silently reinterpret an old record.

An infrastructure error is evidence of an error, not permission to retry. A
retry requires the next policy evaluation to permit it.

## State

`.coord/par_<topic>.yml`:

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

`.coord/par_<topic>_final.md`: final status, last `PolicyDecision`,
acceptance evidence, unsuccessful attempts, unresolved risks, and any human
decision required. Both files are scratch by default.

Lessons never go directly into canonical memory; write a proposal as
described in [coord_memory_schema.md](coord_memory_schema.md).

## Context packet

`.coord/context_<NNN>.md`, the bounded packet handed to a child in harness
mode:

    # Context packet — <task id>

    Policy
    - policy_ref: <path>
    - policy_hash: <sha256>
    - checkpoint_ref: <path>

    Goal
    <one bounded objective>

    Recorded decisions
    - <gate / actor / decision / action hash>

    Evidence
    - <path or stable source locator>

    Scope
    - may read: <paths>
    - may write: <paths>
    - must not touch: <paths>

    Acceptance
    - <runnable check>

    Return contract
    - concise summary
    - files changed
    - tests run
    - risks and blockers
    - raw logs by path only

## Invariants

- Evaluate after every cycle and before every spawn.
- v2 slice counters reset only through `agent-collab checkpoint advance`;
  goal totals and accepted evidence never reset. Keep the stricter of the
  policy limit and an explicit native or host limit.
- Completed children release active concurrency; the host's actual capacity
  also limits spawning.
- If safe compaction is unavailable, report that limitation rather than a
  generic request to continue. Never clear an ambiguous legacy blocker
  automatically.
- Preserve cumulative usage and failure history across slices, sessions, and
  executors. Unknown tokens or cost remain unknown, never zero. Explicit goal
  limits and native platform limits remain hard; absent limits are not
  invented.
- Use stable failure identities based on operation, target, relevant inputs,
  and error class. Renaming a task or switching executors is not a correction.
- A waiting external service is not a failed retry. Continue only with new
  evidence, a safe next step, and the required acceptance checks.
- Diagnose recoverable action failures and perform safe context maintenance
  before escalating. Do not ask the user to renew unchanged authorization.
  Count actual human intervention separately from automatic recovery or
  waiting; fewer pauses never justify bypassing a real gate or claiming
  unmeasured success.
- Agent self-critique is not independent acceptance, and an aggregate agent
  score never replaces a human semantic gate.
- PASS requires cited acceptance evidence, not "looks good".
