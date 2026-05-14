# Optional agentmemory Integration

`.coord/memory.yml is canonical`. agentmemory is an optional searchable
cache for recall across sessions and tools. The collaboration workflow
must still work when agentmemory is missing, stopped, or returning no
results.

## Supported Pattern

Use `.coord/` as the source of truth:

- `.coord/plan.yml` defines the round and context policy.
- `.coord/memory.yml` records accepted decisions, open questions,
  artifact pointers, and session outcomes.
- `.coord/session_primer.md` is the bounded context loaded into a fresh
  session.

Use agentmemory only to enrich recall:

- Query for prior decisions or similar issues before writing the
  primer.
- Mirror compact memory candidates only after they pass the promotion
  rules in `agent-shared-memory`.
- Store paths and summaries, not raw logs, diffs, source code, or
  secrets.

## Failure Behavior

If agentmemory is unavailable, continue without it. Do not block task
splitting, reconciliation, acceptance, or shared-memory updates.

Acceptance evidence must come from tests, `.coord/plan.yml`,
`result.json`, result summaries, and reconciliation reports. Vector
recall is context, not proof.
