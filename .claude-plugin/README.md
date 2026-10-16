# agent-collab-workspace plugin

This plugin exposes four provider-neutral collaboration skills:

- `agent-task-splitter`: fan-out planner (lane table, model tiers, disjoint
  scopes, capped returns, merge step)
- `agent-context-budget`: return caps, primers, and proposal-only memory
- `agent-debate`: two opposed reviewers for a consequential decision
- `agent-acceptance-gate`: reconcile lane output, run presets, verdict

Three redirect stubs remain until 0.7.0: `agent-output-reconciler` (now in
the gate), `agent-shared-memory` (now in context budget), and
`agent-plan-act-reflect` (deprecated). See `docs/migration-0.6.md`.

Install from the marketplace:

```bash
claude plugin marketplace add WenyuChiou/agent-collab-skills
claude plugin install agent-collab-workspace@agent-collab-skills
```

The skill bundle describes behavior. Install the optional
`agent-collab-harness` Python distribution when the host needs executable policy
and checkpoint validation. Provider/model selection remains a host-adapter
concern and is not part of public task routing.

Coordination directories are scratch by default. Memory is proposal-only;
shipping and canonical writes remain human-authorized.
