---
name: agent-task-splitter
description: Use when about to run two or more subagents, workflow lanes, or delegated CLI executors on one goal. Gives each lane a role, a pinned model tier, a disjoint file scope, a bounded brief, and a capped return, and fixes the merge and verification step before launch. Not for research-domain routing that owns .research, .paper, Zotero, Obsidian, or NotebookLM workflows; use research-hub-multi-ai for those.
---

# agent-task-splitter (fan-out planner)

Plan a fan-out before launching it. This skill plans; the host launches the
lanes. The name stays `agent-task-splitter` so existing prompts and plans keep
working.

## Pick the mode

| Mode | Use when | Artifacts |
|---|---|---|
| Native (default) | All lanes run inside one host session: parallel or background subagents, workflow lanes, one-shot CLI delegates, with the user present | Lane table in the conversation and one brief per lane. No `.coord/` plan, packets, or checkpoint. |
| Harness | A round spans sessions or tools, an unattended loop runs, work must resume after an interruption, a signed human gate is needed, or `AGENT_COLLAB_POLICY` is configured | `.coord/plan.yml` (schema v2) and `.ai/task_<NNN>_<slug>.md` packets; see [references/harness-plan.md](references/harness-plan.md) |

A configured policy always selects harness mode, and an unreadable configured
policy fails closed. Native mode follows the host's own limits and
permissions and adds no numeric limits of its own. Host mechanics are in
[native lanes](../../docs/native-lanes.md).

## Fan out only when

- two or more pieces are independent (none needs another's result) and each
  has a checkable result; or
- implementation and independent review must be separate lanes.

Do not split exploratory debugging before the cause is known, a small
coherent change, or work where every lane needs the same context in tight
sequence. Doing it directly is the default.

## The lane table

Write it before launching anything:

| Lane | Role | Executor | Model tier | May write | Must not touch | Acceptance | Return | Depends on |
|---|---|---|---|---|---|---|---|---|
| L1 | delegated-executor | subagent in a worktree | cheap | `src/a/**` | everything else | `pytest tests/a -q` | summary + paths | none |
| L2 | delegated-executor | CLI delegate | cheap | `docs/x.md` | `src/**` | link check passes | summary + paths | none |
| L3 | reviewer | read-only subagent | strong | nothing | `**/*` | verdict with evidence | verdict + findings | L1, L2 |

Rules:

1. Roles are `primary-agent`, `delegated-executor`, `reviewer`, and
   `synthesizer`, defined in the
   [public contract](../../docs/public-harness-contract.md). The executor
   and model columns are host-adapter choices, not public plan fields.
2. The orchestrator assigns the model tier; a lane never picks its own.
   Mechanical, pattern-following work goes to a cheap tier. Review, verdicts,
   root-cause analysis, security, governance, and anything ambiguous go to a
   strong tier.
3. Write scopes are disjoint. Two parallel writers never own the same file.
   If scopes might touch, isolate the writers or run them in sequence.
4. Every lane has at least one runnable or objectively checkable acceptance
   criterion.
5. Every lane has a capped return: a short summary plus file paths, never raw
   logs or full diffs. `agent-context-budget` covers sizing.
6. A lane cannot approve its own output. Author and reviewer are different
   lanes.

[references/task_splitter_heuristics.md](references/task_splitter_heuristics.md)
helps when a task could fit more than one role or DAG shape.

## Fix the merge step before launch

Write down, before any lane starts:

- who merges the results (normally the primary-agent) and in what order;
- the verification command run on the merged result, not only per lane;
- which `agent-acceptance-gate` presets the merged diff will trigger;
- commit boundaries: one reviewed commit per writing lane, or one commit
  after the merged result passes. Read-only lanes need no commit.

## Brief per lane

    # Lane <id>: <one bounded deliverable>
    Repo/worktree: <absolute path>
    Role: <role>. Model tier: <tier>.
    Depends on: <lane ids and artifact paths>

    Before editing, list the exact paths you may write and must not touch.
    Stop and report if they conflict with this brief.

    May read: <paths>
    May write: <paths>
    Must not touch: <paths>
    External actions: none unless named here.
    Edits required: yes | unchanged output allowed because <reason>

    Acceptance: <runnable check>
    Return (capped): status; short summary; files changed; checks run and
    results; risks; blockers. Put long output in a file and return its path.

## Drift guards

- Copy identifiers (slugs, paths, field names, version strings) verbatim into
  the brief. Do not paraphrase them.
- Record the pre-lane baseline (commit or file hashes) so the result can be
  attributed. File times and a process exit status do not prove the work was
  done; use the [task-content evidence review](../../docs/task-content-evidence.md).
- State whether edits are required. A lane that reports success without
  changing its required files has failed unless the brief allowed unchanged
  output.
- Missing, null, failed, declined, cancelled, and timed-out lanes stay
  non-success. Filter them out of synthesis but keep their records.
- Agent agreement never replaces running the checks.

## Harness mode

1. Write `.coord/plan.yml` (schema_version 2) and one packet per non-inline
   task, using [references/harness-plan.md](references/harness-plan.md).
2. Immediately before each spawn the host runs
   `agent-collab policy evaluate --policy <policy_ref> --checkpoint <checkpoint_ref> --json`
   and spawns only on `decision=continue` with `spawn_allowed=true`. The plan
   never overrides that decision.
3. Coordination files are scratch and gitignored. Promote only an explicit
   checkpoint snapshot, shipping artifact, or acceptance record.
4. Do not encode retries in the plan; the policy decides them.

Historical schema-less plans and provider-specific task paths are parse-only;
see [migration 0.4](../../docs/migration-0.4.md).

## Output

Return the lane table, each brief (or its path), the ready lanes in launch
order, and the merge-and-verify step. Do not launch lanes from this skill and
do not turn a planning-only request into implementation.
