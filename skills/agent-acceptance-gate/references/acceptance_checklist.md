# Acceptance gate checklist — standard checks + how to add custom ones

The acceptance gate runs N checks per round. The standard checks
are described in `SKILL.md`'s workflow. This reference documents:

1. The full checklist taxonomy (what categories of checks exist).
2. How `success_criteria` from `.coord/plan.yml` map to runnable
   checks.
3. How to add custom project-specific checks.

## Full checklist taxonomy

The gate runs checks in this order, short-circuiting on hard
failures:

### Layer 1: existence checks (cheapest, run first)

For each task in the round:
- Does `result.json` exist? (If not → run never completed → FAIL.)
- Does `result_<NNN>_<slug>.md` exist? (If not → agent didn't
  write summary, acceptance criterion violated → FAIL.)
- For `agent: claude` tasks: did Claude make the required statement
  in conversation? (If not → FAIL.)

If any L1 check fails, downstream checks don't matter — fail fast.

### Layer 2: status checks

For each `result.json`:
- `status: "success"` → continue to L3.
- `status: "fallback"` → flag as DEGRADED, run L3 anyway, downgrade
  final verdict.
- `status: "error"` → FAIL the task; aggregate errors for report.

### Layer 3: success_criteria verification

For each task with `agent: codex|gemini`, walk through
`success_criteria` from plan.yml:

#### Type A: runnable command

```yaml
success_criteria:
  - "pytest tests/auth/ passes"
  - "mypy src/auth/ has 0 errors"
  - "ruff check src/auth/ exits clean"
```

Translate to:
- `pytest tests/auth/`
- `mypy src/auth/` and check for `Found 0 errors`
- `ruff check src/auth/` and check exit 0

Run each. PASS = exit 0; FAIL = otherwise. Capture last 20 lines of
output for the report.

#### Type B: file existence / content assertion

```yaml
success_criteria:
  - "src/auth/interfaces.py exists and defines AuthProvider ABC"
  - "no imports of src.auth.legacy from other modules"
```

Translate:
- `[ -f src/auth/interfaces.py ] && grep -q "class AuthProvider" src/auth/interfaces.py`
- `! grep -r "from src.auth.legacy" src/ tests/`

For "exists and X" patterns, both halves must hold.

#### Type C: structural / AST assertion

```yaml
success_criteria:
  - "every public symbol in src/auth has a docstring"
```

These are harder to translate. Options:
- Use a lint tool (`pydocstyle src/auth/`).
- Spawn a sub-agent (small Codex task to verify).
- If neither is available, mark as "manual check needed" — don't
  silently pass.

#### Type D: in-conversation verdict (for `agent: claude` tasks)

```yaml
success_criteria:
  - "explicit YES/NO verdict + rationale in chat"
```

Read the current Claude conversation for the most recent in-task
output. Check whether it contains an unambiguous YES or NO with a
rationale paragraph. If not → FAIL with "Claude didn't deliver
verdict".

### Layer 4: cross-task checks (if reconciliation report exists)

Read `.coord/reconciliation_<NNN>.md`. Look for the "Recommended
action" section.

| Reconciler said | Gate verdict (assuming L1-L3 pass) |
|---|---|
| "Merge all" | ✅ PASS |
| "Merge X, Y; manually merge Z" | ⚠ CONDITIONAL PASS — user does manual merge |
| "Retry T<n>" | ❌ FAIL — task needs retry |
| "Escalate to debate" | ⚠ CONDITIONAL PASS — debate first, then re-gate |

The reconciler's verdict caps the gate's verdict. Gate can be
stricter (downgrade based on its own checks) but not laxer.

### Layer 5: aggregate risks

Concat all `risks` arrays from result.json files. Risks classified:
- **High** (failed test, security warning, breaking change without
  shim) → blocks PASS.
- **Medium** (deprecation warning, suboptimal performance,
  inconsistent style) → mention in report, don't block.
- **Low / informational** → mention in report.

If you can't tell severity from the risk text, ask Claude to
classify (1 prompt, 1 sentence per risk).

### Layer 6: optional prose audit

If any task changed `*.md` / `*.tex` / `*.docx` AND
`academic-writing-skills` is installed:
- Invoke `academic-writing-skills` banned-word audit on changed
  files.
- Invoke claim-evidence audit if `.paper/claims.yml` exists in
  project.
- Add results to gate report.

If audit finds issues: mention but don't auto-fail (these are
quality concerns, not correctness blockers — user decides).

If `academic-writing-skills` isn't installed: skip silently. Don't
fail just because the audit isn't available.

### Layer 7: budget check

If `.coord/plan.yml` declared `budget.tokens`:
- Sum `tokens_used` across all `result.json` (handle missing field
  gracefully).
- If sum > budget → ❌ FAIL with "exceeded budget by N tokens".

If no budget declared, skip silently.

## Custom checks

### Project-specific success criteria

Real projects have invariants beyond what `.coord/plan.yml`
declares. Add them as success criteria in plan.yml when the
splitter produces it, OR maintain a project-level checklist file
the gate also runs.

Convention: `.coord/checklist.yml` (optional, project-level):

```yaml
project_invariants:
  # These run on every gate, every round
  - id: "no-prints-in-prod"
    description: "No bare print() statements in src/"
    command: "! grep -rn 'print(' src/"
  - id: "no-todo-comments-on-main"
    description: "No TODO comments in main-branch code"
    command: "! grep -rn 'TODO' src/"
    severity: "medium"     # warning, not blocker
```

The gate reads this file (if present) and runs each invariant
after the per-task success_criteria.

### Custom check via sub-skill

For project invariants too complex for a shell command, write a
new skill that the gate invokes. Example: a research project
might have a `research-invariants` skill that checks
`.research/project_manifest.yml` is up to date.

The gate calls that skill (in-conversation Claude invocation),
treats its output as a check result.

## Severity calibration

Default severity for failed checks:

| Check | Severity |
|---|---|
| Failed test | High |
| Compile/lint error | High |
| Missing required file | High |
| Security warning | High |
| Deprecation warning | Medium |
| Inconsistent style / convention violation | Medium |
| Banned word / overclaim flagged in prose | Medium |
| TODO comment | Low |
| Naming inconsistency | Low |

High blocks PASS. Medium mentioned in report; gate verdict depends
on combined count (5+ medium = downgrade to CONDITIONAL).

## Override pathway

Sometimes the user knows better than the gate — e.g., a failing
test is actually expected because a dependency broke, not the
agent's work. To override:

1. Manually edit `.coord/acceptance_<NNN>.md` to replace the
   verdict.
2. Add an "Override rationale" section explaining why.
3. Future gate runs see the override and don't overwrite it
   (the gate writes a NEW file `acceptance_<NNN>_run<M>.md` if
   one already exists).

The gate respects user overrides — its job is to surface what's
checkable, not to be the final authority. The user is.

## What gate does NOT do

- Run agents (delegate skills).
- Decide which tasks to retry — it reports FAIL; user retries.
- Commit / merge / push — those are user actions.
- Modify source code — gate is read-only on source.
- Update `.coord/plan.yml` — gate can recommend re-planning, but
  user invokes `agent-task-splitter` again.
- Update `.coord/memory.yml` — separate skill.
