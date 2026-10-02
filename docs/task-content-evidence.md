# Task-content evidence review

This is a review contract for hosts using the collaboration skills. Presets
are declarative; the Python harness evaluates policy and checkpoints, not
these acceptance checks. The fixtures in
`tests/test_task_content_evidence_contract.py` are specification tests, not
proof of production preset execution or successful model runs.

## Why file times are advisory

The legacy `post_brief_mtime_check` cannot establish that an executor edited
content: a touch can move mtime without changing bytes. A valid edit can
preserve mtime, and an idempotent task can already satisfy its criterion.
Keep `brief_file` and the legacy check ID/type for adapter compatibility, but
treat its result as advisory. Hosts adopting this revised preset must support
the required content-evidence review; ignoring an unfamiliar check is not PASS.

## Before execution

The primary-agent records the task ID, run or attempt reference, exact brief,
authorized scope, and pre-task repository/worktree baseline. Record existing
dirty state so that an older edit is not attributed to this task. A commit SHA
alone does not identify dirty candidate content. Use artifact references and
content digests or a task-bounded diff as appropriate to the host.

State whether content changes are required, unchanged output is permitted, or
the role is read-only. The worker cannot grant itself an unchanged exception
or wider write scope. Preserve existing authorization; review itself does not
require the user to approve the same task again.

## After execution

The primary-agent or independent reviewer checks:

1. Evidence belongs to this run/attempt, task, brief, and baseline. Missing,
   stale, or wrong-task evidence stays unverified.
2. Candidate content is independently observed, not accepted solely from
   worker-authored hashes, prose, mtimes, or a claimed changed-file list.
3. All observed task deltas, including additions, deletions, and relevant
   untracked files, fit the authorized scope. A justified transitive change
   still needs applicable authority. With parallel writers, use isolated
   worktrees or attributable task deltas; an aggregate diff cannot identify
   which worker made an edit.
4. Tests and manual criteria refer to the current candidate. A prior passing
   result is not evidence that a later candidate passed.
5. A change-required task has the required content delta. An unchanged result
   is allowed only by the task contract, with a reason and current criterion
   evidence. Never force meaningless edits or manufacture a delta.
6. Declined, cancelled, missing, degraded, and failed stages retain their
   states. A successful process exit is not technical acceptance or shipping
   authorization.

Content hashes establish byte identity. They do not prove that an edit is
correct, that a term sweep respected meta-documentation, or that no semantic
drift occurred within an allowed file. Those checks remain with the declared
criterion, project validator, or qualified independent reviewer.

Record a content-evidence result alongside the existing scope and criterion
results. If evidence collection was unavailable, preserve the limitation as
BLOCKED or FAIL; do not silently fall back to timestamps. Existing policies,
checkpoint schemas, transports, native approvals, and human gates are unchanged.
