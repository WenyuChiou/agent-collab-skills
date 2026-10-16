# Native lanes: the Claude Code host adapter

The public contract names roles. This page maps those roles to the mechanisms
Claude Code already has, so an in-session fan-out needs no `.coord/` plan or
checkpoint and no `agent-collab` CLI. Other hosts map the roles their own way.

## Role mapping

| Role | Claude Code mechanism | Notes |
|---|---|---|
| `primary-agent` | The main session | Owns the lane table, the merge, verification, and the conversation with the user. |
| `delegated-executor` | An Agent tool subagent with a pinned `model`; a Workflow `agent()` lane with its own `model` and `effort`; or an external CLI delegate driven by a brief file | Writers whose scopes might overlap get `isolation: "worktree"`. |
| `reviewer` | A read-only subagent on a strong model | Never the author of the candidate it judges. |
| `synthesizer` | The main session, or a subagent without search tools | Structures completed inputs only. |

## Mechanisms

- **Parallel**: send independent Agent calls in one message; they run at the
  same time.
- **Background**: a lane started with `run_in_background` notifies the
  session when it finishes. Keep working and read the result then; do not
  poll or sleep-wait.
- **Continue a lane**: `SendMessage` to an existing agent keeps its context.
  Prefer it to a fresh Agent call for a follow-up on the same work.
- **Workflow tool**: a script fans out `agent()` lanes with a per-lane
  `model` and `effort`, and an optional output `schema` that doubles as a
  return cap. `parallel()` and `pipeline()` shape the graph. The host runs
  workflows only when the user has opted into multi-agent orchestration.
- **Worktree isolation**: `isolation: "worktree"` gives a writing lane its
  own checkout and branch. Review the lane's diff before merging it.
  Read-only lanes do not need one.
- **External CLI delegates**: write the brief to a scratch file, ask for a
  bounded structured output file, and never redirect unbounded stdout into a
  log. The delegate does not commit or push; the primary-agent reviews the
  diff first.

## Model tiers

The orchestrator pins each lane's model before launch; a lane never chooses
its own. Mechanical lanes (pattern edits, scaffolds, bulk reads, measurement)
run on a cheap tier. Review, acceptance verdicts, root-cause analysis,
security, governance, and the final synthesis the user reads run on a strong
tier. A lane's model is never switched silently after a failure.

## Return caps

Every brief ends with the return contract from `agent-task-splitter`: status,
short summary, files changed, checks run, risks, blockers, with long material
written to a file and returned as a path. Workflow lanes can enforce this
with a `schema`. Reading lanes return conclusions with `file:line`
references, not file contents.

## Commit boundaries

A writing lane gets one reviewed commit, or the primary-agent makes one commit
after the merged result passes. Read-only lanes need no commit. Run
`agent-acceptance-gate` on the merged diff before the final commit.

## When to use harness mode instead

Write `.coord/` plan, packet, or checkpoint files and run
`agent-collab policy evaluate` only when:

- a round spans sessions or tools, for example planned in one session and
  executed by CLI delegates over hours;
- a loop runs unattended;
- work must resume after an interruption from a checkpoint;
- a signed human gate is required; or
- `AGENT_COLLAB_POLICY` is configured. A configured policy always applies,
  and an unreadable one fails closed.

Otherwise the lane table lives in the conversation, and no plan, packet, or
checkpoint is written to `.coord/`. A memory proposal may still be written to
`.coord/memory-proposals/`; applying it needs harness mode's signed approval.
