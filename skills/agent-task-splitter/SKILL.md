---
name: agent-task-splitter
description: Use when a goal needs multiple bounded agent roles, parallel or dependent task packets, explicit scope partitions, and a provider-neutral DAG. Not for research-domain routing that owns .research, .paper, Zotero, Obsidian, or NotebookLM workflows; use research-hub-multi-ai for those.
---

# agent-task-splitter

Turn one approved goal into a provider-neutral role DAG and bounded task
packets. This skill plans; it does not spawn agents.

Read references/task_splitter_heuristics.md when role selection or DAG shape is
not obvious. Read ../../docs/public-harness-contract.md for schemas and artifact
policy.

## Roles

- primary-agent: owns scope, architecture, and human communication.
- delegated-executor: performs bounded implementation or mechanical work.
- reviewer: independently tests and judges a stable candidate.
- synthesizer: structures completed inputs without reopening discovery.

The host chooses the adapter for each role. Do not put provider or model names
in the public role field.

## Use this skill when

- Two or more independent task packets can run in parallel.
- Implementation and independent review must be separate.
- A fan-out/fan-in or diamond DAG materially shortens the critical path.
- Several results require explicit reconciliation and acceptance.

Do not split exploratory debugging before the cause is known. Do not split a
small coherent change merely to create agent activity.

## Inputs

- Goal and authorized scope.
- Success criteria.
- Files, systems, and external actions in/out of scope.
- Available policy_ref and checkpoint_ref when any child may be spawned.
- Existing recorded human decisions and evidence refs.

If scope or acceptance is ambiguous, ask one focused question. Do not invent
permission for external writes.

## Workflow

1. Confirm the repository/worktree root.
2. Restate the goal and scope.
3. Identify task boundaries by work character and evidence dependencies.
4. Assign one role to each task.
5. Build an acyclic dependency graph.
6. Partition write scope. Two parallel writers must not own the same file.
7. Add at least one runnable or objectively checkable success criterion per
   task.
8. Write .coord/plan.yml using schema_version 2.
9. Write .ai/task_<NNN>_<slug>.md for each non-inline task.
10. Return the ready task ids and dependency order. Do not spawn.

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

Omit policy_ref/checkpoint_ref only when the plan cannot spawn or loop
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

The host must not spawn unless decision=continue and spawn_allowed=true.
Splitter output does not override that decision.

The host may delegate read-only exploration while planning, but must not turn
a planning-only request into implementation. Prefer direct execution for small
coherent work. Reserve capacity for required independent review and retain
cumulative child usage when a v2 slice advances. Agent boundaries alone do not
require commits or fresh human authorization.

## Invariants

- Provider names are transport metadata, not public roles.
- Reviewer and synthesizer are different: a synthesizer structures accepted
  inputs; a reviewer judges them.
- A task cannot approve its own semantic or governance-sensitive output.
- Missing, null, failed, declined, cancelled, and timed-out tasks stay
  non-success.
- Every parallel result list filters absent/failed results before downstream
  synthesis while retaining their failure records.
- Agent voting never replaces evidence verification or a human gate.

## Compatibility

Historical schema-less plans and provider-specific task paths are parse-only.
Writers emit v2 roles and generic task paths. See
../../docs/migration-0.4.md.
