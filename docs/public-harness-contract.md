# Public harness contract

This document is the human-readable companion to the structural JSON Schemas
shipped by agent-collab-harness. The `agent-collab` CLI and its programmatic
validators are the authoritative semantic contract. JSON Schema Draft 2020-12
describes interchange shape and local field constraints; it cannot express all
cross-field limits or uniqueness-by-property rules. Policy values belong in one
policy document. Skills may name fields and commands, but must not copy numeric
limits.

## Roles

Plans and coordination artifacts use roles rather than model or provider names:

| Role | Responsibility | Normal permissions |
|---|---|---|
| primary-agent | Own the task, scope, architecture, and human communication | Project-scoped tools |
| delegated-executor | Perform a bounded implementation or mechanical task | Only the task packet's explicit scope |
| reviewer | Independently test and judge a stable candidate | Read-only, except for an explicit review artifact |
| synthesizer | Convert completed inputs into a requested structure | No search or external tools unless the plan explicitly changes the role |

The host adapter decides which implementation fulfills a role. Provider names
may appear in adapter configuration, transport metadata, or historical records;
they are not routing values in the public plan contract.

## Coordination files

The default coordination surface is scratch:

- .coord/plan.yml
- .coord/context_<NNN>.md
- .coord/session_primer.md
- .coord/memory-proposals/*.json
- .coord/reconciliation_<NNN>.md
- .coord/debate_<topic>.md
- .coord/acceptance_<NNN>.md
- .coord/par_<topic>.yml
- .ai/task_<NNN>_<slug>.md
- executor logs and transient results under .ai/

.coord/ and .ai/ remain gitignored by default. A repository may explicitly
promote only these classes of evidence:

1. A checkpoint snapshot needed to resume or audit a shipped task.
2. A shipping artifact named by the task's acceptance contract.
3. Acceptance evidence needed to explain a merge or release decision.

Promotion is a deliberate copy or generation into a repository-owned evidence
path. Agent boundaries do not imply commits. Never stage the entire scratch
directory.

## Plan contract

New plans use schema_version 2 and assign a role:

    schema_version: 2
    round: 1
    goal: "..."
    policy_ref: "${AGENT_COLLAB_POLICY}"
    checkpoint_ref: ".coord/task-checkpoint.json"
    tasks:
      - id: T1
        role: delegated-executor
        slug: bounded-change
        description: "..."
        depends_on: []
        files_in_scope: ["src/example.py"]
        files_out_of_scope: ["**/*"]
        success_criteria: ["python -m pytest tests/test_example.py -q"]

Role adapters consume .ai/task_<NNN>_<slug>.md. Historical agent and
provider-specific task names are parse-only compatibility inputs.

## TaskCheckpoint

The structural interchange schema is packaged at:

src/agent_collab_harness/schemas/task-checkpoint-1.json

Required fields:

- schema_version
- task_id
- parent_id
- status
- cycle
- tool_calls
- elapsed_seconds
- transcript_bytes
- same_failure_retries
- no_evidence_cycles
- active_children
- evidence_refs
- decisions
- overrides
- stop_reason
- updated_at

Optional observed metrics cover total children, the prior transcript
checkpoint, task packets, parent summaries, memory digests, and child results.
`pending_action_hash` is optional while no human record exists and required as
soon as a decision or override is present.

Every human decision record contains:

- gate
- actor
- decision: approve, decline, or revise
- timestamp
- rationale
- affected_action_hash
- authorization: HMAC scheme, key id, and signature

`declined`, `timed_out`, and `cancelled` are terminal non-success statuses.
Silence, timeout, decline, and cancellation are never converted to approval.
For append-only decision history, the latest decision for each gate governs;
`decline` or `revise` stops evaluation until a later recorded approval for that
gate exists.

## Policy

The structural interchange schema is packaged at:

src/agent_collab_harness/schemas/agent-policy-1.json

The runtime is standard-library-only. Policy contents must be strict JSON. A
file may use a .yaml suffix for compatibility only when its contents are valid
JSON. `AGENT_COLLAB_POLICY` selects exactly one policy source for a run. The
public v1 shape and the existing portable-harness v1 shape are accepted; the
latter is normalized in memory without copying or rewriting its values.
The supported portable v1 `terminal_states` list is validated exactly; a
changed or unknown set fails closed instead of being silently ignored.

Validate and evaluate with:

    agent-collab policy validate --policy PATH --json
    agent-collab policy evaluate --policy PATH --checkpoint PATH --json
    agent-collab checkpoint validate --checkpoint PATH --json
    agent-collab doctor --json

Exit codes:

| Code | Meaning |
|---:|---|
| 0 | Valid document or continue |
| 2 | Invalid document or misconfiguration |
| 3 | Checkpoint required |
| 4 | Stop |

Evaluation never retries, changes models, discards context, or mutates project
state. An unreadable policy returns a PolicyDecision with decision=stop,
spawn_allowed=false, and exit code 4.

Evaluate:

1. Before each child or delegated-executor spawn.
2. After each plan-act-reflect cycle.
3. Before retrying the same failure.

The caller must obey decision, spawn_allowed, and checkpoint_required.

Human decisions and overrides are not trusted merely because an actor string
starts with `human:`. Each record includes an `hmac-sha256` authorization bound
to its immutable fields and to `pending_action_hash`. The trusted host supplies
a key-id-to-secret map through `AGENT_COLLAB_HUMAN_KEYS_JSON`; missing, unknown,
or invalid authorization fails closed. The canonical public policy independently
pins each authorized key's SHA-256 digest under
`human_authorization.key_hashes`; an arbitrary caller-provided key therefore
has no authority. The portable v1 compatibility shape has an empty trust root,
so it cannot authorize human records until the canonical policy is deliberately
upgraded. An override also records the observed metric value at authorization,
which must be below the original limit.

## PolicyDecision

The structural interchange schema is packaged at:

src/agent_collab_harness/schemas/policy-decision-1.json

Fields:

- schema_version
- policy_id
- policy_hash
- decision: continue, checkpoint, or stop
- spawn_allowed
- checkpoint_required
- reasons
- effective_limits
- observed_metrics

The policy hash is the SHA-256 of canonical UTF-8 JSON. It is null only for a
fail-closed decision where the policy could not be read or validated.

## Memory proposals

Memory output is proposal-only. A skill may create:

    .coord/memory-proposals/<proposal-id>.json

Minimum proposal fields:

- schema_version
- proposal_id
- source_task
- action, an immutable object containing operation, target_ref, summary, and evidence_refs
- state: proposed, approved, or rejected
- created_at
- decision, initially null and later containing actor, timestamp, rationale, and affected_action_hash

Rules:

1. New proposals start in proposed state with no decision metadata.
2. Supersede, archive, and delete require a specific target_ref.
3. Only a recorded human approval may change a proposal to approved.
4. Approval does not itself mutate canonical memory.
5. Applying an approved proposal appends a new canonical event; it never edits
   or removes an older event.
6. Resolving a question appends a resolution event that references the
   question. It does not add resolved_by to the old record.
7. Recall systems are caches. They never outrank repository state, evidence, or
   a current human decision.
8. `affected_action_hash` covers only the canonical JSON bytes of the immutable
   `action` object. Envelope state and decision metadata are deliberately
   excluded, so recording approval does not change the authorized bytes.
9. The approval decision carries the same trusted-host HMAC authorization as a
   checkpoint human record; delegated executors never receive the signing key.

## Acceptance

The reviewer uses the task's success criteria, repository tests, result
contracts, and relevant acceptance presets. Agent votes do not establish truth.
A reviewer must report PASS, FAIL, or NEEDS_HUMAN with evidence. A failed,
missing, null, declined, cancelled, or timed-out result is not success.
