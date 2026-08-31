# Coordination memory event and proposal schemas

Version 2 resolves two earlier contradictions:

1. Canonical memory is an immutable event log. Resolving a question or ending
   an execution appends an event instead of editing an older record.
2. Agents produce proposals. Canonical writes require a recorded human
   approval bound to the proposed bytes.

## Canonical event log

Path: .coord/memory.yml

    schema_version: 2
    project: "<project slug>"
    created_at: "<ISO 8601 with timezone>"
    events:
      - event_id: M1
        event_type: decision
        created_at: "<ISO 8601 with timezone>"
        actor: "human:owner"
        summary: "Use an append-only event log for coordination memory."
        rationale: "Older records must remain auditable."
        evidence_refs:
          - "docs/public-harness-contract.md"
        supersedes: []
        resolves: []
        target_ref: null
        source_proposal_id: "<uuid>"
        approval:
          actor: "human:owner"
          decision: approve
          timestamp: "<ISO 8601 with timezone>"
          rationale: "Approved after schema review."
          affected_action_hash: "<lowercase SHA-256>"

Required event fields:

| Field | Contract |
|---|---|
| event_id | M followed by a monotonic integer; never reused |
| event_type | decision, open_question, resolution, artifact, execution, lifecycle |
| created_at | Timezone-aware ISO 8601 |
| actor | Human or provider-neutral role identity |
| summary | Compact durable fact |
| rationale | Why the event belongs in memory |
| evidence_refs | Non-empty stable references |
| supersedes | Older event ids made non-current by this event |
| resolves | Open-question event ids resolved by this event |
| target_ref | Required for lifecycle events; otherwise null when unused |
| source_proposal_id | Proposal that authorized the event |
| approval | Recorded human decision bound to the proposal/action hash |

Older events never gain a resolved_by, ended_at, status, archive, or deletion
field later. Changes are new events.

## Proposal

Path: .coord/memory-proposals/<proposal-id>.json

    {
      "schema_version": 1,
      "proposal_id": "<canonical lowercase UUID>",
      "source_task": "<task id>",
      "action": {
        "operation": "add",
        "target_ref": null,
        "summary": "<proposed durable event>",
        "evidence_refs": ["<stable ref>"]
      },
      "state": "proposed",
      "created_at": "<ISO 8601 with timezone>",
      "decision": null
    }

Operations:

| Operation | target_ref | Canonical effect after approval |
|---|---|---|
| add | null | Append a new fact event |
| supersede | required | Append an event whose supersedes includes target_ref |
| archive | required | Append a lifecycle event |
| delete | required | Append a lifecycle request; physical removal still follows repository retention policy |

The initial state is proposed. Proposed records have a null decision. Approval
changes only the envelope state and decision object; the nested action object is
immutable. A revise decision produces a new proposal and does not authorize
application.

An approval decision contains actor, decision, timestamp, rationale,
affected_action_hash, and an `hmac-sha256` authorization object. The trusted
host signs it using a key that is not available to delegated executors.

## Approval binding

Compute `affected_action_hash` from the exact canonical JSON bytes of the
immutable nested `action` object used for the decision. Never include `state` or
decision metadata in this payload. Before application:

1. Recompute the hash from the unchanged `action` object.
2. Confirm it matches the recorded approval.
3. Confirm state is approved.
4. Verify the decision HMAC using the trusted host key.
5. Confirm evidence references still resolve.
6. Acquire the memory lock.
7. Append one event using an atomic temporary-file replacement.

Any mismatch stops application and returns to the human. Do not repair, rehash,
or approve on the human's behalf.

## Concurrency

Use an atomic create-only lock at .coord/memory.yml.lock. The lock record must
contain owner, created_at, task_id, and proposal_id. A stale-looking lock is not
standing permission to delete it; first confirm its owner is no longer active.

Write the complete next document to a temporary sibling, flush it, then replace
memory.yml atomically. Failure leaves the original bytes unchanged.

## Reading current state

Derive current state without mutating events:

1. Index all events by event_id.
2. Mark superseded ids from later events.
3. Mark resolved question ids from resolution events.
4. Apply lifecycle events as a view, not physical deletion.
5. Report conflicts where two current events disagree.

Do not use agent majority as a truth rule. Evidence and human decisions decide
whether a claim becomes canonical.

## v1 compatibility

Schema-less/v1 memory remains read-only compatibility input:

- decisions become decision events
- open questions become open_question events
- resolved_by becomes a separate resolution event
- artifacts become artifact events
- agent_history becomes execution events

Migration is dry-run first and does not overwrite v1. This repository does not
ship an automatic canonical-memory migration command in 0.4; conversion remains
a reviewed, human-approved proposal.

## Artifact policy

.coord/ is ignored by default. Do not commit every event or proposal. Promote
only an explicit checkpoint snapshot, shipping artifact, or acceptance record
into a repository-owned evidence path.
