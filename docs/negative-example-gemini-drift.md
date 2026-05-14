# Negative Example: Gemini Drift

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
