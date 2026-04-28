# `.coord/memory.yml` — full schema and rules

## Why this file exists

Codex resume sessions, Gemini sessions, and Claude sessions don't
share memory natively. When a multi-agent project spans days or
weeks (and 5+ agent runs), decisions get made in one session and
forgotten by the next agent that picks up the work.

`.coord/memory.yml` is the cross-session blackboard. Every
significant decision, open question, artifact, or agent run gets
appended. Reading it gives a new session enough context to be
useful without re-deriving everything.

## Schema

```yaml
project: "<repo name or research project slug>"
created_utc: "<ISO 8601 UTC timestamp of file creation>"

decisions:
  - id: D<n>                          # D1, D2, ...; monotonic, never reused
    date_utc: "<ISO 8601 UTC>"
    what: "<one-sentence statement of the decision>"
    why: "<one-sentence rationale>"
    made_by: "claude"|"codex"|"gemini"|"user"|"agent-debate"
    supersedes: [<list of older D-ids that this replaces>]
    # Optional fields:
    related_artifacts: [<paths of artifacts that informed or implement this>]
    confidence: "high"|"medium"|"low"
    revisit_after_utc: "<ISO 8601>"   # if decision is provisional

open_questions:
  - id: Q<n>                          # Q1, Q2, ...; monotonic
    asked_utc: "<ISO 8601>"
    question: "<one-sentence question>"
    blocker_for: [<task IDs from .coord/plan.yml or "none">]
    suggested_next_agent: "claude"|"codex"|"gemini"|"user"|"debate"
    resolved_by: <D-id, or null if unresolved>
    # Optional:
    context: "<longer description if needed>"

artifacts:
  - path: "<file path relative to project root>"
    round: <int>                      # which .coord/plan.yml round produced it
    produced_by: "<skill or agent name>"
    used_by: [<list of skills / agents that consume this>]
    timestamp_utc: "<ISO 8601>"
    # Optional:
    summary: "<one-line description>"

agent_history:
  - agent: "claude"|"codex"|"gemini"
    session_id: "<agent-provided session ID, e.g., codex resume token>"
    started_utc: "<ISO 8601>"
    ended_utc: "<ISO 8601 or null if still running>"
    output_summary: "<path to result.md or 'in-conversation'>"
    status: "success"|"fallback"|"error"|"in-progress"
    # Optional:
    task_ids: [<plan.yml task IDs handled in this session>]
    tokens_used: <int>
```

## Append-only rule

The file is append-only at the **list-element level**. You may:

- Add new entries to any of the 4 lists.
- Update an existing entry's `resolved_by` field (when an open
  question gets answered).
- Update `agent_history[i].ended_utc` and `status` when an
  in-progress session completes.

You may NOT:

- Edit the `what`, `why`, `question`, or other content fields of
  existing entries.
- Delete entries.
- Reuse IDs.

To "change" a decision: append a new decision with `supersedes:
[<old-id>]`. The old entry stays as historical record.

## Atomic writes

When multiple agents are running concurrently (Claude session A
adds a decision while Codex session B's wrapper appends an
agent_history entry), naive write-without-lock can corrupt the
YAML.

Use a lock file pattern:

```bash
LOCK=.coord/memory.yml.lock
TIMEOUT=300                                # seconds; 5 min stale-lock cutoff

acquire_lock() {
  local i=0
  while [ $i -lt 30 ]; do
    if mkdir "$LOCK" 2>/dev/null; then
      echo $$ > "$LOCK/pid"
      return 0
    fi
    # Check if existing lock is stale
    if [ -f "$LOCK/pid" ]; then
      local age=$(( $(date +%s) - $(stat -c %Y "$LOCK/pid" 2>/dev/null || echo 0) ))
      if [ $age -gt $TIMEOUT ]; then
        echo "stale lock, removing" >&2
        rm -rf "$LOCK"
        continue
      fi
    fi
    sleep 1
    i=$((i+1))
  done
  echo "couldn't acquire lock after 30s" >&2
  return 1
}

release_lock() {
  rm -rf "$LOCK"
}

# Usage:
acquire_lock || exit 1
trap release_lock EXIT
# ... read memory.yml, modify, write atomically (write to .tmp then mv) ...
mv .coord/memory.yml.tmp .coord/memory.yml
```

In practice, since `agent-shared-memory` is invoked by the
in-conversation Claude (not by Codex's wrapper), single-agent
serialization is the common case. The lock is defense in depth.

## ID assignment

- Decisions: `D1`, `D2`, ... in order of `date_utc` (= file
  position in the list).
- Questions: `Q1`, `Q2`, ... same.
- Never reuse. Never renumber. If you delete the file and start
  over, that's a new project — don't carry old IDs.

## Initialization

For a new project:

```yaml
project: "<name>"
created_utc: "<now>"
decisions: []
open_questions: []
artifacts: []
agent_history: []
```

That's it. Fields get added as work happens.

## Read-mode digest format

When generating a digest for a new agent session, format:

```
[agent-shared-memory] Project state — <project>

Current decisions (<count>):
  <D-id> (<date>): <what>
  ...

Historical / superseded (<count>):
  <D-id> (<date>): <what>. Replaced by <D-id>.
  ...

Open questions (<count>):
  <Q-id>: <question>
       Blocking: <task IDs or "nothing">.
       Suggested next: <agent>.
  ...

Last <N> agent sessions (most recent first):
  <date> <agent>  <task slug>  <status>
  ...

Recent artifacts (last <N>):
  <path> (<date>, <produced_by>)
  ...
```

Default `<N>`: 3 for sessions, 5 for artifacts. Adjust based on
how much context the user actually wants.

## What goes in vs what doesn't

### Goes in

- Decisions about architecture / library / data model with
  explicit `why`.
- Open questions blocking work, with which task is blocked.
- Artifacts produced by skills (plan.yml, reconciliation reports,
  etc.).
- Agent session boundaries (start, end, status, output summary
  pointer).

### Doesn't go in

- Per-task scratch (use `.ai/<agent>_task_*.md`).
- Source code (it's already in version control).
- Long prose / analysis (link to `.md` artifact files instead;
  store the path).
- Secrets, API keys, credentials.
- Information specific to a single research project — that goes
  in `.research/project_manifest.yml`, not `.coord/memory.yml`.
  This file is for **multi-agent coordination**, not project-level
  facts.

## Versioning

If you commit `.coord/memory.yml` to git: append-only enforces a
clean diff per decision. Each commit shows exactly what was added
to memory.

If you `.gitignore` it: it's local state. Less audit trail; less
secrets-leak risk. Default behavior in `.gitignore`-shipped
projects.

The skill itself doesn't enforce either; the user picks per
project.
