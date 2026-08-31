# Provider-neutral walkthrough

This walkthrough uses the samples in `examples/` to demonstrate a bounded
auth refactor.

## 1. Split

`agent-task-splitter` creates a schema-v2 plan with reviewer,
delegated-executor, and synthesizer roles. The plan references a policy and a
checkpoint instead of embedding budget values.

Task packets are written to generic `.ai/task_<NNN>_<slug>.md` scratch paths.
The host adapter chooses an available implementation for each role.

## 2. Evaluate before spawn

```bash
agent-collab policy evaluate \
  --policy "$AGENT_COLLAB_POLICY" \
  --checkpoint .coord/checkpoint_001.json \
  --json
```

Only `continue` with `spawn_allowed: true` permits an executor or reviewer
spawn. `checkpoint` returns control after state is persisted. `stop` forbids a
retry or replacement spawn.

## 3. Preserve results

The reviewer succeeds, the executor produces a failed compatibility test, and
the dependent synthesizer is not run. The reconciler records all three states.
It does not replace the missing synthesis with an empty success or hide the
executor's prose.

See `examples/reconciliation_001.md.sample`.

## 4. Gate

The acceptance gate verifies declared commands, evidence references, scope,
and triggered presets. The sample technical verdict is FAIL because a required
test failed.

See `examples/acceptance_001.md.sample`.

## 5. Human decision

The human may approve a retry, decline the change, or request revision. That
decision is a new append-only record tied to the action hash. It does not edit
the failed acceptance evidence or mutate canonical memory.

## 6. Promote only durable evidence

`.coord/` and `.ai/` remain scratch. A project may copy a required checkpoint
snapshot or immutable acceptance record into its evidence directory, but agent
boundaries do not imply commits.
