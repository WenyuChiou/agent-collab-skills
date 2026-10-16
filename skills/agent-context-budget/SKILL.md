---
name: agent-context-budget
description: Use when launching parallel or background subagents, or when a handoff, log, or result would be more than a short summary (roughly 2 KB). Caps return sizes (summary in the reply, detail by path), picks a cheap model tier for mechanical lanes, records durable decisions as proposals, and checkpoints or primes a fresh session before context runs out.
---

# agent-context-budget

Keep the primary session small while lanes do the reading and writing. There
is no second budget source: native mode follows the host's limits and the caps
written into each brief; harness mode takes every number from the policy
referenced by the current `TaskCheckpoint`. The "roughly 2 KB" in the
description says when to use this skill; it is not a limit.

Do not use this skill to summarize away unresolved failures, human decisions,
raw scientific evidence, or security findings.

## Before launching lanes

- Put a return cap in every brief: status, short summary, files changed,
  checks run, risks, blockers. Long output goes to a file and the lane returns
  the path. Raw logs, transcripts, and full diffs never come back inline.
- Reading lanes return conclusions with `file:line` references, not file
  dumps. Name exact files and line ranges in the brief.
- Choose model tiers before launch: a cheap tier for mechanical lanes (pattern
  edits, scaffolds, bulk reads), a strong tier for review, verdicts,
  root-cause analysis, security, and governance. Never switch a lane's model
  silently after a failure.
- Background lanes notify on completion. Keep working and read the result
  then; do not poll.
- For a follow-up, continue the lane that already holds the context instead
  of starting a fresh one.

Host mechanics (parallel calls, background runs, per-lane model, return
schemas) are in [native lanes](../../docs/native-lanes.md).

## What goes into a brief

Only decision-relevant material:

- goal and acceptance contract;
- explicit files and tools in scope;
- direct evidence paths;
- current recorded human decisions;
- relevant interfaces or schemas.

Keep raw logs and complete artifacts at their paths. Include a short failure
excerpt only when the next action needs it.

## Before context runs out

Write a fresh-session primer: goal, current state, decisions and who made
them, open questions, evidence paths, next step. Keep unresolved failures,
human decisions, and security findings visible. Compaction changes the active
context, not cumulative usage or failure history.

## Durable decisions (formerly agent-shared-memory)

Memory output is proposal-only. Repository state, current evidence, and
recorded human decisions outrank memory; recall systems are optional caches.
Native mode may write a proposal file and nothing else under `.coord/`;
applying an approved proposal needs the signed approval of harness mode.

- Write a proposal to `.coord/memory-proposals/<proposal-id>.json` with an
  immutable `action` (operation, target_ref, summary, evidence_refs).
- Supersede, archive, and delete need a specific `target_ref`. A proposal
  with no evidence refs stays pending.
- Only an explicit human approval, recorded with actor, decision, timestamp,
  rationale, affected action hash, and trusted-host HMAC authorization, lets a
  proposal be applied. Decline, timeout, and revise are not approval.
- Applying appends one new event to `.coord/memory.yml`.
  It never edits an existing event; a resolution, correction, or
  supersession is a new append-only event.
- Never report an unapproved proposal as a canonical decision. Delegated
  executors never receive the signing key.

Full schema and apply rules:
[references/coord_memory_schema.md](references/coord_memory_schema.md).

## Harness mode

Applies when `AGENT_COLLAB_POLICY` is configured, or a round spans sessions or
tools, runs unattended, or must resume.

1. Validate:

       agent-collab policy validate --policy <policy-ref> --json
       agent-collab checkpoint validate --checkpoint <checkpoint-ref> --json

2. Record the observed metrics in the checkpoint. Never estimate a lower
   number to fit the policy.
3. Before each child spawn and after each returned result, run:

       agent-collab policy evaluate \
         --policy <policy-ref> \
         --checkpoint <checkpoint-ref> \
         --json

4. Obey the decision:
   - `continue` with `spawn_allowed=true`: build the bounded packet.
   - `checkpoint`: write the checkpoint and primer. A v2 slice with
     auto_continue advances atomically under the same goal; v1 returns
     control. For a v2 action-scope `context_compaction_required`, do local
     context maintenance without asking for renewed approval: keep full
     artifacts, acceptance evidence, failures, and authorization; build a
     smaller linked packet or use native compaction; record measured sizes;
     re-evaluate. Do not spawn or advance a slice while this gate is pending.
   - `stop` or `spawn_allowed=false`: do not spawn. Respect the v2 scope; an
     exhausted action still allows safe primary-agent diagnosis.
5. A configured but unreadable policy stops the run. If the harness package is
   unavailable, do not start an autonomous loop; prepare packets for
   human-controlled execution instead.

Multi-cycle loop rules (retry counting, failure identity, no-progress cycles)
are in [references/harness-loop.md](references/harness-loop.md).

Outputs (scratch by default): `.coord/context_<NNN>.md` (shape in
[references/harness-loop.md](references/harness-loop.md)),
`.coord/session_primer.md`, and the updated checkpoint. Promote a checkpoint
snapshot only when the repository needs it for resume, shipping, or
acceptance evidence. Agent boundaries do not imply commits.

## Invariants

- Policy values have one machine-readable source; the stricter of the policy
  and the host's native limit wins.
- Reserve capacity for required independent review.
- No silent retry, model switch, context discard, or result truncation. A
  capped return that points to the full output is not truncation.
- Missing evidence is reported as missing. A decline, cancellation, timeout,
  error, or `null` result remains non-success.
- Recall systems may suggest context; they never override repository state or
  recorded human decisions.
