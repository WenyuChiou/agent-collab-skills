---
name: agent-context-budget
description: Use when an agent task needs bounded context packets, checkpoint-aware compaction, a fresh-session primer, or policy-controlled child results without loading raw logs into the primary session.
---

# agent-context-budget

Prepare bounded context for a task without inventing a second budget source.
Numeric limits come from the policy referenced by the current TaskCheckpoint.
The public contract and commands are documented in
../../docs/public-harness-contract.md.

## Use this skill for

- A task that may spawn a delegated executor or reviewer.
- A transcript approaching its configured checkpoint boundary.
- A fresh session that needs a compact, evidence-linked primer.
- Results or logs that are too large for the primary-agent context.

Do not use it to summarize away unresolved failures, human decisions, raw
scientific evidence, or security findings.

## Inputs

- Goal and task id.
- Readable agent policy.
- Current TaskCheckpoint.
- Evidence and artifact paths needed by the next role.
- Optional existing .coord/plan.yml and approved memory events.

If the policy is configured but unreadable, stop. If the optional
agent-collab-harness package is unavailable, do not start an autonomous loop or
child spawn; prepare the packet for human-controlled execution instead.

## Workflow

1. Validate policy and checkpoint:

       agent-collab policy validate --policy <policy-ref> --json
       agent-collab checkpoint validate --checkpoint <checkpoint-ref> --json

2. Record current observed metrics in the checkpoint. Do not estimate a lower
   number to fit the policy.
3. Run policy evaluation before a child spawn:

       agent-collab policy evaluate \
         --policy <policy-ref> \
         --checkpoint <checkpoint-ref> \
         --json

4. Obey the result:
   - continue and spawn_allowed=true: create the bounded task packet.
   - checkpoint: write a checkpoint/primer. A v2 slice with auto_continue
     advances atomically and resumes under the same goal; v1 returns control.
   - stop or spawn_allowed=false: do not spawn. Respect v2 decision scope;
     exhaustion of one action does not prohibit safe primary-agent diagnosis.
5. Put only decision-relevant material in the packet:
   - goal and acceptance contract
   - explicit files and tools in scope
   - direct evidence references
   - current recorded human decisions
   - relevant interfaces or schemas
6. Keep raw logs and complete artifacts at paths. Include a short failure
   excerpt only when it is needed to diagnose the next action.
7. After a result returns, update observed metrics and evaluate again.

## Outputs

- .coord/context_<NNN>.md: round-specific packet plan.
- .coord/session_primer.md: bounded fresh-session digest.
- Updated TaskCheckpoint at the plan's checkpoint_ref.

These are scratch artifacts by default. Promote a checkpoint snapshot only when
the repository explicitly needs it for resume, shipping, or acceptance
evidence. Agent boundaries do not imply commits.

## Packet shape

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

- Policy values have one machine-readable source.
- v2 slice counters reset only through checkpoint advance; goal totals and
  accepted evidence never reset. Retain the stricter explicit native/host limit.
- Reserve child capacity for required independent review. Completed children
  release active concurrency; the host's actual capacity also limits spawning.
- No silent retry, model switch, context discard, or result truncation.
- Missing evidence is reported as missing, not summarized as success.
- A decline, cancellation, timeout, error, or null result remains non-success.
- Recall systems may suggest context; they do not override repository state or
  recorded human decisions.
