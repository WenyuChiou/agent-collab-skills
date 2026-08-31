---
name: agent-shared-memory
description: Use when a user asks to inspect coordination memory, propose a durable decision or resolution, review pending memory proposals, or apply an explicitly approved proposal as a new append-only event.
---

# agent-shared-memory

Coordinate durable facts without letting an agent silently rewrite project
memory. Read the event schema in references/coord_memory_schema.md before
creating or applying a proposal.

## Authority

Repository state, current evidence, and recorded human decisions outrank memory.
Recall systems are optional caches.

All memory mutations start as proposals:

    .coord/memory-proposals/<proposal-id>.json

Without an explicit human approve decision, do not add, supersede, archive,
delete, overwrite, or compact canonical memory.

## Modes

### Read

Read canonical events and return:

- current decisions, following supersedes references
- unresolved questions
- relevant artifact/evidence pointers
- recent execution outcomes
- conflicts or stale claims

Do not load raw agent logs into the primary session. Follow their stable paths
only when needed.

### Propose

Create a proposal with:

    {
      "schema_version": 1,
      "proposal_id": "<uuid>",
      "source_task": "<task id>",
      "action": {
        "operation": "add | supersede | archive | delete",
        "target_ref": null,
        "summary": "<compact proposed event>",
        "evidence_refs": ["<stable ref>"]
      },
      "state": "proposed",
      "created_at": "<ISO 8601>",
      "decision": null
    }

Supersede, archive, and delete require a specific `action.target_ref`. A
proposal with no `action.evidence_refs` remains pending and must not be applied.
The `action` object is immutable. Its canonical JSON bytes, not the mutable
proposal envelope, are the approval payload.

### Decide

Only a human may approve, decline, or revise a proposal. Record:

- actor
- decision
- timestamp
- rationale
- affected proposal/action hash
- HMAC authorization from the trusted host

Decline and timeout remain non-success. A revise decision creates or updates a
proposal; it is not approval.

### Apply

Apply only a proposal whose recorded state is approved and whose immutable
`action` bytes still match `decision.affected_action_hash`. Decision metadata
and state are outside that hashed payload, so recording approval does not
invalidate the approval hash.
The decision uses the same `hmac-sha256` authorization boundary as checkpoint
human records. Do not expose the signing secret to a delegated executor.

Application appends one immutable event to .coord/memory.yml. It does not edit
the target event:

It never edits an existing event; a resolution, correction, or supersession is
a new append-only event.

- Superseding a decision appends a new decision event with supersedes.
- Resolving a question appends a resolution event with resolves.
- Archiving or deleting appends a lifecycle event referencing target_ref.
- Canonical removal, compaction, or physical deletion requires a separate
  repository-specific retention decision.

## Coordination scope

Use this memory for agent coordination decisions, questions, artifact pointers,
and execution outcomes. Research truth belongs in research evidence stores;
paper claims belong in the paper's claim/evidence contract.

## Artifact policy

.coord/ is scratch and gitignored by default. Do not commit every proposal or
agent boundary. Promote only an explicitly selected checkpoint snapshot,
shipping artifact, or acceptance record into a repository-owned evidence path.

## Output

Always report:

- mode: read, propose, decide, or apply
- proposal/event id
- state
- evidence refs
- whether canonical memory changed
- human decision still required

Never report an unapproved proposal as a canonical decision.
