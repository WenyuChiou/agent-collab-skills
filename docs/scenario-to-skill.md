# Scenario-to-skill routing

Route by collaboration need, not by provider name.

| Scenario | Skill | Evidence produced |
|---|---|---|
| Several tasks need disjoint scopes and dependencies | `agent-task-splitter` | schema-v2 plan and generic task packets |
| Context or runtime pressure may interrupt work | `agent-context-budget` | validated checkpoint handoff |
| One agent needs bounded self-correction | `agent-plan-act-reflect` | cycle evidence and PolicyDecision |
| Multiple results may conflict or be missing | `agent-output-reconciler` | reconciliation report |
| A consequential trade-off has two plausible positions | `agent-debate` | adversarial evidence and pending human decision |
| A durable lesson may be useful later | `agent-shared-memory` | memory proposal, never a direct canonical write |
| A reconciled round needs a shipping-quality gate | `agent-acceptance-gate` | immutable technical verdict |

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
