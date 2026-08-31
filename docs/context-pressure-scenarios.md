# Context-pressure scenarios

These deterministic scenarios exercise policy and checkpoint behavior without
depending on a particular model provider.

## Large bounded refactor

Create several delegated-executor tasks plus an independent reviewer. Expected:

- every spawn is preceded by policy evaluation;
- task packets cite artifacts instead of embedding the repository;
- each cycle updates evidence and checkpoint metrics;
- reaching a policy boundary produces checkpoint or stop, not a silent retry.

## Cross-session resume

Resume from a validated checkpoint with a long history. Expected:

- the primary agent loads only current scope, decisions, and evidence refs;
- raw logs stay path-only;
- canonical memory is not used as a substitute for repository state;
- unreadable checkpoint or mismatched policy hash fails closed.

## Executor drift

Give an executor a task packet with explicit scope and inject an out-of-scope
change. Expected:

- reconciler preserves the executor's result but flags the path;
- acceptance gate returns FAIL;
- no automatic retry or commit occurs.

## Optional recall unavailable

Run with a configured recall cache unavailable. Expected:

- canonical files and checkpoint evidence remain authoritative;
- optional recall is reported as degraded or skipped;
- acceptance decisions are never reconstructed from cache.

## Failed structured conversion

Provide valid researcher prose followed by a failed optional structuring step.
Expected:

- the prose result remains available;
- the failed structured payload is filtered and recorded;
- synthesizer or human review may retry only if policy permits;
- the result never becomes an unexplained `null`.
