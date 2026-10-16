# Negative Example: Gemini Drift

> Historical evidence only (2026-05 dogfood). The Gemini lane was archived
> on 2026-06-18 and is not an active route; see
> [Gemini history](migration-0.4.md#gemini-history). Skill names and step
> numbers below refer to the release current at the time, not to 0.6.

Earlier dogfood runs showed a common failure mode: Gemini received an
inline prompt derived from a task file, then wrote a reconciliation-like
report that treated all tasks as Claude tasks and invented slugs that
did not match `examples/plan.yml.sample`.

That output is useful as a failure pattern, but it should not be the
default positive sample. The positive sample now demonstrates aligned
task IDs, correct agent counts, bounded summaries, and path-only log
references.

Use this as a pressure scenario for `agent-output-reconciler`: any
result summary that claims the wrong task ID, slug, or agent assignment
must be flagged as high severity drift before acceptance.
