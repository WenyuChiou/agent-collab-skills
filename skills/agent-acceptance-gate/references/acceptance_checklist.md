# Acceptance verification taxonomy

Run the cheapest deterministic checks first. Short-circuit on a blocking
failure, but retain evidence from completed checks.

## 1. Contract existence

For every task, verify:

- task packet and declared role exist;
- checkpoint and policy decision validate;
- result status is explicit;
- required result, evidence, and log references exist.

Missing artifacts are failures unless the plan explicitly marks them optional.
Declined, cancelled, timeout, degraded, and failed are not aliases for success.

## 2. Status and evidence

- `success`: continue to criterion verification.
- `degraded`: verify available evidence and cap the verdict as specified by the
  plan; never silently pass a missing required capability.
- `failed`, `cancelled`, `declined`, or `timeout`: fail the task unless the plan
  explicitly treats that task as optional.
- `missing` or `null`: record the missing input and fail any dependent check.

A prose claim that tests passed is not test evidence. Require the command, exit
code, environment, bounded output excerpt, and artifact reference expected by
the project.

## 3. Success criteria

Classify each declared criterion:

- command: run the exact command and record exit code;
- file/content: verify existence and required content;
- structure/schema: use the project validator or an AST/schema check;
- semantic/manual: mark pending until the named human or qualified reviewer
  records a decision.

If a criterion cannot be translated safely, record `manual check required`.
Never infer PASS.

## 4. Scope and reconciliation

- Compare the staged or task-bounded diff with declared file scopes.
- Accept a transitive change only when the task result names and justifies it.
- Fail unexplained files or undisclosed within-file scope expansion.
- A reconciliation recommendation may cap the verdict but cannot make the gate
  less strict.

## 5. Presets and project invariants

Run triggered multi-locale, catalog-entry, and factual-claim presets. Also run
repository-defined invariants. Report skipped optional checks as `SKIP` and
required unavailable checks as `FAIL` or `BLOCKED`, never PASS.

For claim verification, distinguish:

- documented by an authoritative source;
- locally verified;
- not found;
- not applicable.

## 6. Policy

Use `agent-collab policy evaluate` with the current policy and checkpoint. Do
not reproduce policy numbers in the acceptance report. Record policy ID, hash,
decision, reasons, and whether spawning or another cycle is allowed.

## 7. Risk severity

Blocking examples include failed required tests, invalid schemas, security
findings, unsupported factual claims, unapproved breaking changes, scope drift,
and unreadable configured policy. Non-blocking risks remain visible and require
the plan's stated disposition.

## 8. Immutable evidence and human decision

Each gate run creates a new acceptance record. A later human decision appends a
separate record containing:

- gate;
- actor;
- decision: `approve`, `decline`, or `revise`;
- timestamp;
- rationale;
- affected action hash.

Do not edit an earlier acceptance record or memory event. Human approval may
authorize a documented exception; it does not falsify the underlying evidence.

## Acceptance record skeleton

```markdown
# Acceptance evidence — <run-id>

**Technical verdict:** PASS / CONDITIONAL PASS / FAIL
**Action hash:** <sha256>
**Plan:** <reference>
**Checkpoint:** <reference>
**Policy:** <policy id and hash>

## Per-task checks
- <task-id> — <role> — <status> — <criterion and evidence>

## Scope and preset checks
- <check> — PASS / FAIL / SKIP — <evidence>

## Risks and blockers
- <severity> — <finding> — <required action>

## Human decision
- Pending, or <immutable decision-record reference>
```

The gate is read-only with respect to source, plan, canonical memory, commits,
branches, and releases.
