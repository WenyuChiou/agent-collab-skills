# agent-collab-workspace plugin

This plugin exposes seven provider-neutral collaboration skills:

- `agent-task-splitter`
- `agent-context-budget`
- `agent-plan-act-reflect`
- `agent-output-reconciler`
- `agent-debate`
- `agent-shared-memory`
- `agent-acceptance-gate`

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
