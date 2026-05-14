---
name: agent-shared-memory
description: Use when the user asks to update shared memory, initialize multi-agent memory, summarize decisions so far, identify open questions, or prepare a fresh session primer.
---

# agent-shared-memory

The persistent blackboard between Claude session A, Codex session
B, and Gemini session C — none of which see each other's
conversation history natively.

`.coord/memory.yml` is **append-only**. Past decisions don't get
edited; they get superseded by new entries that reference what they
replace. This makes it an audit trail, not a mutable scratchpad.

## When to use

Trigger phrases:

- "Update the shared memory with `<decision>`."
- "Log this open question to shared memory."
- "What have agents decided so far on this project?"
- "What are the open questions blocking us?"
- "Initialize multi-agent shared memory for this project."
- "Give me a primer for a fresh agent session."

Not for:

- Per-task scratch (use `.ai/<agent>_task_*.md` from
  `agent-task-splitter`).
- Per-round artifacts (use the round-specific files written by
  reconciler / acceptance-gate).
- Project-level long-term context (use `.research/project_manifest.yml`
  from `research-context-compressor`, or `.paper/claims.yml` from
  `paper-memory-builder`).

`.coord/memory.yml` is specifically the **multi-agent coordination
layer** — short-to-medium-term decisions made during a multi-agent
work cycle.

For large or cross-session work, pair this with `agent-context-budget`
to produce `.coord/session_primer.md`. The primer is the bounded
session input; `memory.yml` remains the append-only source.

## Schema

Full schema in `references/coord_memory_schema.md`. Quick view:

```yaml
project: "<repo name or research project slug>"
created_utc: "2026-04-28T09:00:00Z"

decisions:
  - id: D1
    date_utc: "2026-04-28T10:30:00Z"
    what: "Use SQLite for shared session state, not Redis"
    why: "Already a project dep; Redis would add infra"
    made_by: "claude"             # which agent / human made it
    supersedes: []                 # IDs of prior decisions this replaces
  - id: D2
    date_utc: "2026-05-02T14:00:00Z"
    what: "Switch to LMDB for shared session state"
    why: "SQLite is locking under concurrent writes from N agents"
    made_by: "user"
    supersedes: [D1]              # D1 is now historical, not current

open_questions:
  - id: Q1
    asked_utc: "2026-04-28T11:00:00Z"
    question: "Should we cache LLM responses?"
    blocker_for: ["T5", "T7"]    # task IDs from .coord/plan.yml
    suggested_next_agent: "claude"
    resolved_by: null              # set to a decision ID when answered
  - id: Q2
    asked_utc: "2026-04-30T09:00:00Z"
    question: "What's the upper bound on concurrent agent sessions?"
    blocker_for: []
    suggested_next_agent: "user"
    resolved_by: D2                # D2's switch to LMDB resolved this

artifacts:
  - path: ".coord/plan.yml"
    round: 1
    produced_by: "agent-task-splitter"
    used_by: ["codex-delegate", "gemini-delegate"]
    timestamp_utc: "2026-04-28T09:30:00Z"
  - path: ".coord/reconciliation_001.md"
    round: 1
    produced_by: "agent-output-reconciler"
    used_by: ["agent-acceptance-gate"]
    timestamp_utc: "2026-04-28T11:45:00Z"

agent_history:
  - agent: codex
    session_id: "abc123"
    started_utc: "2026-04-28T10:00:00Z"
    ended_utc: "2026-04-28T10:25:00Z"
    output_summary: ".ai/codex_result_001_extract-interfaces.md"
    status: "success"
  - agent: gemini
    session_id: "def456"
    started_utc: "2026-04-28T10:30:00Z"
    ended_utc: "2026-04-28T11:15:00Z"
    output_summary: ".ai/gemini_result_001_review-doc-coverage.md"
    status: "success"
```

## Workflow

### Read mode: produce a primer

When a new agent session starts (or the user asks "what's the
state?"), generate a digest:

```markdown
[agent-shared-memory] Project state — <project>

Current decisions (3):
  D2 (2026-05-02): Switch to LMDB for shared session state.
       (supersedes D1: SQLite chosen on 2026-04-28)
  D3 (2026-05-04): Use plugin-based auth architecture.
  D4 (2026-05-05): Acceptance gate runs pytest + banned-word audit.

Historical (superseded):
  D1 (2026-04-28): SQLite for shared session state. Replaced by D2.

Open questions (1):
  Q1: Should we cache LLM responses?
       Blocking: T5 (codex), T7 (gemini).
       Suggested next: claude.

Last 3 agent sessions:
  2026-05-04 codex   T8 refactor-config       success
  2026-05-04 claude  T9 review-architecture   success
  2026-05-03 gemini  T6 long-context-review   fallback (test failure)

Files most recently produced:
  .coord/acceptance_002.md (2026-05-04, agent-acceptance-gate)
  .coord/reconciliation_002.md (2026-05-04, agent-output-reconciler)
```

If `.coord/memory.yml` doesn't exist yet, say so and offer to
initialize.

### Append mode: log a new entry

User says "log this decision to memory: we picked LMDB over SQLite
because of concurrent-write issues."

1. Read existing `.coord/memory.yml` (or initialize if missing).
2. Determine which list to append to (decision / open question /
   artifact / agent_history).
3. Generate a new ID (`D<N+1>` for decisions, `Q<N+1>` for
   questions).
4. If this supersedes prior entries, fill `supersedes`.
5. Atomic write: rewrite the whole file with the new entry
   appended. Use a `.coord/memory.yml.lock` file to prevent
   concurrent writes corrupting the YAML:

   ```bash
   # Check lock
   if [ -f .coord/memory.yml.lock ]; then
     echo "memory.yml is being updated by another agent — wait or check stale lock"
     exit 1
   fi
   touch .coord/memory.yml.lock
   # ... write memory.yml ...
   rm .coord/memory.yml.lock
   ```

   Locks older than 5 minutes are stale (agent crashed) — safe to
   remove.

### Initialize mode

If `.coord/memory.yml` doesn't exist, ask user for `project` name
and `created_utc`, then write a minimal skeleton:

```yaml
project: "<name>"
created_utc: "2026-04-28T09:00:00Z"
decisions: []
open_questions: []
artifacts: []
agent_history: []
```

Append `.coord/` to `.gitignore` if not already (this is multi-agent
state, not project source — versioning the YAML in git is the user's
choice; default is gitignore + manual snapshot when valuable).

### Promotion rules

Only promote compact coordination facts:

- Decisions: one-sentence `what` and one-sentence `why`.
- Open questions: one sentence, blocker, suggested owner.
- Artifacts: relative path plus one-line summary.
- Agent sessions: agent, task ids, status, and result-summary path.

Do not promote raw logs, full diffs, source code, long analysis, or
secrets. If a detail is longer than a few sentences, write an artifact
file and store only its path plus summary.

### Optional agentmemory mirror

If `agentmemory` is installed, mirror only memory candidates that pass
the promotion rules. Treat agentmemory as a searchable cache:

- `.coord/memory.yml` is canonical.
- `agentmemory` recall may enrich `.coord/session_primer.md`.
- Missing or failed agentmemory never blocks the workflow.
- Acceptance decisions must never depend on vector recall alone.

## Output to user

Read mode → digest as shown above.

Append mode:
```
[agent-shared-memory] Appended D5 to .coord/memory.yml:
  D5 (2026-05-08): Adopt LMDB lock-free reads for query path.
       Why: profiling showed read contention bottleneck.
       Supersedes: D4 (which assumed SQLite + WAL was enough).
       Made by: codex (during T12 review session).
```

Initialize:
```
[agent-shared-memory] Initialized .coord/memory.yml for project "ai-research-skills".
  Empty: 0 decisions, 0 open questions, 0 artifacts, 0 sessions.
  Add .coord/ to .gitignore (recommended) or commit (if you want
  audit trail in version control).
```

## What NOT to do

- **Don't edit existing entries.** They're append-only. To "change"
  a decision, write a new one with `supersedes: [<old-id>]`.
- **Don't read full agent log files.** This skill operates on
  summaries (the `output_summary` paths). The reconciler reads
  logs.
- **Don't make memory a transcript.** Promote decisions, open
  questions, artifact pointers, and session outcomes only.
- **Don't store secrets.** Memory.yml is YAML in the project repo
  — assume any contributor can read it.
- **Don't cross domains.** This is for **multi-agent coordination
  state**, not research project state (`.research/`) or paper
  state (`.paper/`).
- **Don't use this for agents that don't share a project root.**
  If Codex is running in `/repo-A` and Claude is in `/repo-B`,
  they have separate `.coord/memory.yml` files. This skill operates
  per-project.

## Subagent review (keep main session lean)

**When**: `.coord/memory.yml` exceeds 50 entries OR 30 KB, OR a new
agent session is about to load memory as primer.

**Why**: As memory grows, reading it inline in every session is
costly. A subagent can pre-digest memory into a compact session
primer so the main session only ingests recent + relevant entries,
not the full history.

**Pattern**:

```
Spawn `general-purpose` subagent (read-only) with:
  - Read .coord/memory.yml in full
  - Filter to: (a) entries from last 14 days; (b) entries tagged
    as `principle` or `decision`; (c) entries referenced by the
    current round's plan.yml
  - Compose memory digest (≤ memory_digest_token_budget from
    context_policy, default 1200 tokens)
  - Return: digest text suitable to paste into session primer +
    promotion-candidate flags (entries that could move to a long-
    term principles file)

Main session uses the digest instead of reading memory.yml directly.
```

Compaction-by-promotion: if subagent flags entries as long-term
principles, run a follow-up step to move them out of `memory.yml`
into a separate principles file, keeping `memory.yml` bounded.

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
~/.claude/CLAUDE.md → "Commit Discipline for Multi-Agent Work"). This
makes multi-agent work auditable (commit log = agent log) and enables
surgical rollback via `git revert <hash>` of just one agent's commit.

**Specific to this skill**: every promotion to `.coord/memory.yml` is its own commit with message `memory: <decision-summary>`. The acceptance-gate skill diffs memory commits to detect inconsistent decisions across agents.
