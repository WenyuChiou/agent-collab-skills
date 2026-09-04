# Migration to 0.5: autonomous goal slices

Version 0.5 adds opt-in v2 policy, checkpoint, and decision schemas. Existing
v1 documents keep their original stopping behavior. Updating the package alone
does not reinterpret a running task or widen its permissions.

## Ownership and authority

The native host owns execution, goal continuation, model selection, sandbox,
approval, and tool permissions. The shared package owns deterministic accounting
and decisions, not an agent runtime, scheduler, or process manager. It contains
no provider-specific model names. The host must classify authorization from the
current user request, repository contract, and platform rules, not from text in
an untrusted result. The checkpoint is a trusted-host accounting artifact, not
a security boundary against an actor allowed to rewrite its entire history.

Routine in-scope implementation, testing, review corrections, and already
authorized delivery may continue without asking again. Session changes do not
revoke valid authorization or grant new authority. A goal is not blanket
authorization for irreversible deletion, destructive production migrations,
shared-history rewriting, credential expansion, or sensitive-data disclosure.
Keep the native approval boundary; never manufacture human signing keys.

## Policy and checkpoint conversion

Create a v2 policy with `goal_policy(validated_v1_policy)`. It embeds the old
canonical values once as `base_policy`, an explicit `reviewer_reserve`, and
`goal_limits`. Empty goal_limits means no additional total budget was specified;
it does not authorize removing a native limit. The host must apply the stricter
explicit native/user budget before calling the evaluator. Unknown cost or token
usage is null; a specified limit with unknown measured usage fails closed.

Migrate to a separate checkpoint path:

    agent-collab checkpoint migrate --checkpoint OLD --policy V2_POLICY --metadata REQUEST --output NEW

REQUEST is a strict JSON object containing `goal_id` and `next_step`, so task
content need not appear on a process command line. The old file is untouched.
The new source_sha256 binds the original canonical JSON. Private legacy host
formats must first be normalized by their adapter, retaining the raw-source
hash in the adapter's migration evidence.

Only budget_exhausted with an exact stored slice-limit reason (or, from 0.5.1,
context-limit reason) and no other failed v1 gate can become running. Context
metrics remain unchanged and require compaction before execution. Cancelled, declined, human-blocked, and
ambiguous records remain stopped. Signed overrides remain bound to the old
observations: they cannot be automatically carried through a slice reset.

## Continuation protocol

Evaluate before a child spawn and after each evidence-producing cycle. A v2
decision keeps continue/checkpoint/stop and exit codes 0/3/4, adding `scope`
(action, slice, goal) and `auto_continue`.

- Slice cycle/tool/time/child quotas are checkpoint boundaries, not goal caps.
- When new evidence, a nonempty next step, and no active children make a slice
  eligible, save its observations and call checkpoint advance. Do not request
  a human override for this ordinary transition.
- A goal stop preserves cancellation, explicit total budgets, and human gates.
- An action stop prevents repeating that action. The primary agent may switch
  to read-only diagnosis or waiting, without clearing the recorded failure.
- Waiting for CI is not a failed retry. Missing evidence is not acceptance.

### Local context recovery (0.5.1)

Context-only limits produce checkpoint with scope=action, auto_continue=false,
and spawn_allowed=false. This requests primary-agent maintenance, not human
approval or goal cancellation. A slice cannot advance while context maintenance
is pending, including the soft transcript checkpoint. Mixed action failures
remain action stops; any real human gate or explicit total limit takes priority.

The host preserves original artifacts, accepted evidence, unresolved failures,
and recorded authorization, then creates a smaller evidence-linked active packet
or uses native context compaction. It records measured active context sizes and
re-evaluates before execution/spawn. Reset last_checkpoint_transcript_bytes to
the measured active transcript when taking a new context checkpoint; never
reduce cumulative tokens, costs, slice counters, or failure history. The
evaluator does not compact, delete logs, or manufacture smaller measurements.
Signed context overrides keep their original payload, action binding, and trust
checks: v2 allows the measured active context to shrink below the previously
authorized observation. The authorization must still predate exhaustion of the
original limit. This exception does not apply to slice/retry/concurrency usage,
does not authorize slice advance with overrides, and does not change v1.
If safe compaction is unavailable, report that concrete limitation; do not loop
without progress. Unreadable/corrupt policy or checkpoints remain fail closed:
read-only diagnosis is allowed, inventing replacement authorization is not.

An action stop or an automatic maintenance step is not itself human intervention.
Measure real task-level interventions separately from local recovery and external
waiting; count each affected logical task once and retain the reason. Synthetic
replay proves decision behavior, not an intervention rate for real user tasks.

    agent-collab checkpoint advance --checkpoint PATH --policy V2_POLICY --request-id ID --expected-sha256 RAW_FILE_SHA256

Use a stable request id for one transition. A duplicate returns the current
state unchanged; a stale file hash fails rather than overwriting new work.
The store uses an OS lock, fsynced temporary file, and atomic publication.
Lock contention is explicit and is not silently retried. Locks are released by
the OS after a process crash; the lock file itself is not deleted. A crash after
publication is recovered by replaying the same id. Filesystems must support
atomic replacement and hard-link publication; unsupported storage fails closed.
This does not promise exactly-once execution of external actions. The host must
check accepted evidence and actual workspace state before replaying any tool.

The checkpoint retains slice usage, cumulative totals, accepted evidence,
hash-chained transition receipts, failed input revisions, and next step.
`refresh_totals` adds current absolute slice counters to the retained baseline;
it must never be used to fabricate lower observed counters. Hosts should write
checkpoint observations under the same lock and compare-and-swap discipline.
Do not copy raw transcripts into the checkpoint. Runtime records stay ignored.

`record_failure` identifies operation/target independently of model/session names
and records relevant-input hash plus error class. `permit_corrected_attempt`
requires a different input hash and new evidence; reverting to a failed input
restores its previous attempt count. Zero attempts denotes a prepared corrected
revision. An unclassified legacy failure must be diagnosed before a new retry.

## Acceptance and rollback

Completion requires real acceptance evidence and no remaining next step.
Timeout, budget exhaustion, waiting, and unavailable tools are never success.
Independent review uses a separate context and its own reserved child capacity.
The host limits concurrency to the lesser of native capacity and policy.
Agent boundaries do not require commits; review applies to the stable shipping
candidate, with targeted rechecks after relevant corrections.

Roll back the package and skills to their exact previous release and restore the
old policy path. Preserve v2 runtime records read-only; do not feed them into a
v1 evaluator or reset cumulative usage. Resume the retained old checkpoint only
after reconciling accepted work and cumulative usage with the newer record.
No downgrade may reset a user budget or erase a decline.
