---
name: Bug report
about: A multi-agent skill misfired, produced wrong output, or broke the .coord/ schema.
title: "[bug] "
labels: bug
---

## Which skill?

- `agent-task-splitter` / `agent-context-budget` / `agent-plan-act-reflect` / `agent-output-reconciler` / `agent-debate` / `agent-shared-memory` / `agent-acceptance-gate`

## What did you ask the primary agent to do?

```
<paste the prompt or describe the request>
```

## What happened?

<paste the output, the produced .coord/ files, or describe the unexpected behavior>

## What did you expect?

<one or two sentences>

## Multi-agent context

- Which provider-neutral roles and host adapters were involved?
- Did each task's result and evidence references exist when you invoked the broken skill?
- Round number (from `.coord/plan.yml`):

## Environment

- Host and plugin version:
- OS:
- Role-adapter versions (if relevant):
- `agent-collab doctor --json` output:

## Reproduction

Minimum file set / commands to reproduce, if possible.
