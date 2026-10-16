# Migration to 0.6

0.6.0 fits the skills to how multi-agent work is actually run: an in-session
fan-out of subagents, workflow lanes, and CLI delegates, followed by one check
of the merged result. It changes skill text only. The `agent-collab` CLI,
schemas, exit codes, and checkpoint/policy semantics are unchanged.

## Why

A review of one maintainer's Claude Code transcripts for 2026-07-18 to
2026-10-16 (counting Skill, Agent, and Workflow `tool_use` blocks by timestamp) found no
Skill-tool invocation of any bundle skill, while multi-agent work itself was
common: over 1,000 Agent-tool calls, plus Workflow-tool runs in more than ten
sessions. The installed copy in that
period was 0.3.1, whose descriptions waited for a user to ask ("split this",
"reconcile these"). The 0.4/0.5 descriptions describe an abstract need ("a
goal needs ... a provider-neutral DAG") rather than the moment the model is
about to fan out or commit, and every 0.5 skill assumed the policy file,
checkpoint, and `.coord/plan.yml` even for a short in-session fan-out. This is
one maintainer's usage, not a general measurement, and 0.4/0.5 triggering was
not measured separately.

## What changed

| Before (0.5.x) | After (0.6.0) |
|---|---|
| `agent-task-splitter`: provider-neutral DAG planner | Same name, now a fan-out planner: lane table (role, model tier, disjoint scope, brief, capped return) and a merge-and-verify step fixed before launch. The harness plan moved to `references/harness-plan.md`. |
| `agent-output-reconciler` | Merged into `agent-acceptance-gate` as "Step 1: Reconcile". Redirect stub until 0.7.0. |
| `agent-acceptance-gate`: run after reconciliation | Fires before commit or push on merged lane output or a preset trigger; reconciles, runs presets, decides. |
| `agent-shared-memory` | Merged into `agent-context-budget` ("Durable decisions"); schema at `agent-context-budget/references/coord_memory_schema.md`. Redirect stub until 0.7.0. |
| `agent-plan-act-reflect` | Deprecated. The unattended policy-driven loop moved to `agent-context-budget/references/harness-loop.md`. Stub removed in 0.7.0. |
| `agent-context-budget`: policy/checkpoint packets | Return caps, model-tier choice, primers, and durable decisions; harness steps kept for configured policies. |
| `agent-debate` | Two opposed reviewers on the same evidence with a stated round cap. |

New: [native lanes](native-lanes.md) (Claude Code host adapter),
`scripts/check_skill_contracts.py` (descriptions, stubs, and preset triggers
stay in sync), and a `trigger` block in each gate preset.

## Native mode and harness mode

Native mode is the default for an in-session fan-out with the user present:
the lane table lives in the conversation, the host's limits and permissions
apply, and no plan, packet, or checkpoint is written to `.coord/` (a memory
proposal may be; applying it needs harness mode). Harness mode is unchanged and applies
when a round spans sessions or tools, runs unattended, must resume, needs a
signed human gate, or `AGENT_COLLAB_POLICY` is configured. A configured
policy always applies and still fails closed when unreadable.

## What you need to do

- Prompts, plans, or docs that name a removed skill keep working through the
  stubs in 0.6.x. Replace the names before 0.7.0:
  - `agent-output-reconciler` → `agent-acceptance-gate`
  - `agent-shared-memory` → `agent-context-budget`
  - `agent-plan-act-reflect` → `agent-context-budget` (harness loop
    reference), or no skill for ordinary iteration
- A pipeline that ran the reconciler and then the gate now runs one gate pass.
- `.coord/` artifacts, memory events, checkpoints, and policies need no
  migration.
- Update an installed copy with your host's plugin update command; the
  marketplace tracks `main`.

## Rollback

Reinstall 0.5.1 by pinning the plugin source or a checkout to commit
`4aa56e4`, the last 0.5.1 state of `main` (the repository has no 0.5.1 tag).
No data format changed, so no conversion is needed in either direction.
