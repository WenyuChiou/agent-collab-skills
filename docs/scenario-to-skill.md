# Scenario-to-skill routing

Route by collaboration need, not by provider name.

| Scenario | Skill | Evidence produced |
|---|---|---|
| About to run two or more subagents, workflow lanes, or delegates on one goal | `agent-task-splitter` | lane table and capped briefs (native); schema-v2 plan and task packets (harness) |
| Launching parallel or background lanes, or a result or handoff is too large for the primary context | `agent-context-budget` | capped returns, primer, checkpoint handoff |
| A durable decision may be useful later | `agent-context-budget` (Durable decisions) | memory proposal, never a direct canonical write |
| An unattended multi-cycle loop under a configured policy | `agent-context-budget` ([harness loop](../skills/agent-context-budget/references/harness-loop.md)) | cycle evidence and PolicyDecision |
| A consequential trade-off has two plausible positions | `agent-debate` | opposed reviews and a pending human decision |
| Before commit or push: merged lane output, locale variants, catalog entries, or frontier-model benchmark claims | `agent-acceptance-gate` | reconciliation plus an immutable technical verdict |

`agent-output-reconciler`, `agent-shared-memory`, and `agent-plan-act-reflect`
are redirect stubs in 0.6.0 and are removed in 0.7.0; see
[migration 0.6](migration-0.6.md).

## Role adapters

The public plan chooses a role:

- `primary-agent`
- `delegated-executor`
- `reviewer`
- `synthesizer`

The host maps roles to supported runtimes. Adapter configuration may include a
provider or model, but the public plan does not. Missing adapters are explicit
blockers; the harness does not silently switch models.

## Direct work versus collaboration

Use direct work for a single bounded action with no retry loop, independent
review, or resume requirement. Add the harness when work includes spawns,
retries, multiple result streams, checkpoints, or a human decision gate.

For open-ended research, let the researcher return prose and sources. Use a
no-tool synthesizer afterward if a structured packet is needed. Do not force
deep structured output on the same agent that is exploring sources.
