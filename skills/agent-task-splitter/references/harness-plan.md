# Harness-mode plan and task packets

Use this reference only in harness mode: a round that spans sessions or tools,
an unattended loop, a resume requirement, a signed human gate, or a configured
`AGENT_COLLAB_POLICY`. Native in-session fan-out needs only the lane table and
briefs in `SKILL.md`.

## Inputs

- Goal and authorized scope.
- Success criteria.
- Files, systems, and external actions in and out of scope.
- `policy_ref` and `checkpoint_ref` when any child may be spawned.
- Existing recorded human decisions and evidence refs.

If scope or acceptance is ambiguous, ask one focused question. Do not invent
permission for external writes.

## Workflow

1. Confirm the repository or worktree root.
2. Restate the goal and scope.
3. Identify task boundaries by work character and evidence dependencies.
4. Assign one role to each task.
5. Build an acyclic dependency graph.
6. Partition write scope. Two parallel writers must not own the same file.
7. Add at least one runnable or objectively checkable success criterion per
   task.
8. Write `.coord/plan.yml` using schema_version 2.
9. Write `.ai/task_<NNN>_<slug>.md` for each non-inline task.
10. Return the ready task ids and dependency order. Do not spawn.

Before execution, the host captures the attributable pre-task baseline and
states whether edits are required or unchanged output is permitted. Use the
[task-content evidence review](../../../docs/task-content-evidence.md). A
read-only role does not need to manufacture an edit.

## Plan shape

    schema_version: 2
    round: 1
    goal: "..."
    policy_ref: "${AGENT_COLLAB_POLICY}"
    checkpoint_ref: ".coord/task-checkpoint.json"
    created_at: "<ISO 8601 with timezone>"
    tasks:
      - id: T1
        role: primary-agent
        slug: define-contract
        description: "Freeze the public contract."
        depends_on: []
        files_in_scope: ["docs/contract.md"]
        files_out_of_scope: ["src/**"]
        success_criteria:
          - "contract is traceable to the current authorized user goal"
      - id: T2
        role: delegated-executor
        slug: implement-contract
        description: "Implement the approved contract."
        depends_on: [T1]
        files_in_scope: ["src/**", "tests/**"]
        files_out_of_scope: ["docs/contract.md"]
        success_criteria:
          - "python -m pytest tests -q"
      - id: T3
        role: reviewer
        slug: review-candidate
        description: "Review the stable T2 candidate."
        depends_on: [T2]
        files_in_scope: []
        files_out_of_scope: ["**/*"]
        success_criteria:
          - "verdict is PASS, FAIL, or NEEDS_HUMAN with evidence"

Omit `policy_ref` and `checkpoint_ref` only when the plan cannot spawn or loop
autonomously.

## Task packet

    # Task: <id> — <description>

    ## Context
    - Repo/worktree: <absolute path>
    - Plan: .coord/plan.yml
    - Role: <role>
    - Depends on: <task ids and artifact refs>

    ## Pre-task scope confirmation
    Before editing, report the exact allowed and forbidden paths. Stop if the
    brief conflicts with the plan.

    ## Goal
    <one bounded deliverable>

    ## Scope
    - May read: <paths>
    - May write: <paths>
    - Must not touch: <paths>
    - External actions: <none or explicit authorization>

    ## Acceptance
    - <runnable or objective criterion>

    ## Return contract
    - status
    - concise summary
    - files_changed
    - tests_run
    - evidence_refs
    - baseline/candidate references bound to this task and run/attempt
    - change-required or permitted-unchanged result, with criterion evidence
    - risks
    - blockers

Task packets and raw results are scratch. A task may write only its explicit
shipping artifact; acceptance evidence is promoted separately.

## Policy boundary

Immediately before a host spawns a task:

    agent-collab policy evaluate \
      --policy <policy_ref> \
      --checkpoint <checkpoint_ref> \
      --json

The host must not spawn unless `decision=continue` and `spawn_allowed=true`.
Reserve capacity for required independent review and retain cumulative child
usage when a v2 slice advances. Agent boundaries alone do not require commits
or fresh human authorization.

## Invariants

- Provider names are transport metadata, not public roles.
- Reviewer and synthesizer are different: a synthesizer structures accepted
  inputs; a reviewer judges them.
- A task cannot approve its own semantic or governance-sensitive output.
- Missing, null, failed, declined, cancelled, and timed-out tasks stay
  non-success.
- Every parallel result list filters absent or failed results before
  downstream synthesis while retaining their failure records.
- Agent voting never replaces evidence verification or a human gate.
