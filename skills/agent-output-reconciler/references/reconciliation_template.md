# Reconciliation report template

Use this shape for a scratch reconciliation report. The policy determines
size limits; this template defines content, not numeric budgets.

```markdown
# Multi-agent reconciliation — round <round-id>

**Goal:** <goal>
**Created:** <ISO 8601 UTC>
**Plan:** <plan path or artifact reference>
**Checkpoint:** <checkpoint path or artifact reference>
**Policy:** <policy id and hash>

## Task inventory

### <task-id> — <role> — <slug>
- **Status:** success / degraded / failed / cancelled / declined / missing
- **Scope:** <declared scope>
- **Files changed:** <paths or none>
- **Evidence:** <test, artifact, result, and log references>
- **Risks:** <risks or none reported>
- **Verification:** verified / partially verified / unverified

## Filtered or missing results

- <task-id>: <null, missing, or unusable field> — <reason and retained source>

## Cross-task analysis

### Supported agreement
- <shared conclusion> — <evidence references>

### Contradictions
- <claim A versus claim B> — <evidence on each side and unresolved question>

### File and dependency conflicts
- <path or dependency> — <conflict and safe next action>

## Aggregated risks

- **Blocking:** <items or none>
- **Non-blocking:** <items or none>

## Recommended next action

<acceptance-gate / targeted retry / human decision / stop>

## Unresolved blockers

- <blocker and required actor>
```

Rules:

- Count tasks by role, never by provider.
- Preserve failed, declined, cancelled, and missing states.
- Cite artifacts by path or immutable reference instead of pasting raw logs.
- A recommendation is not an acceptance decision.
- Do not append the report to canonical memory; create a proposal if a durable
  memory entry may be useful.
