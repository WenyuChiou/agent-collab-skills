---
name: Bug report
about: A multi-agent skill misfired, produced wrong output, or broke the .coord/ schema.
title: "[bug] "
labels: bug
---

## Which skill?

- `agent-task-splitter` / `agent-output-reconciler` / `agent-debate` / `agent-shared-memory` / `agent-acceptance-gate`

## What did you ask Claude to do?

```
<paste the prompt or describe the request>
```

## What happened?

<paste the output, the produced .coord/ files, or describe the unexpected behavior>

## What did you expect?

<one or two sentences>

## Multi-agent context

- Were `codex-delegate` / `gemini-delegate-skill` involved? (yes / no)
- Did the delegate skills' `result.json` files exist when you invoked the broken skill?
- Round number (from `.coord/plan.yml`):

## Environment

- Claude Code version: `claude --version`
- OS:
- `codex --version` / `gemini --version` (if relevant):

## Reproduction

Minimum file set / commands to reproduce, if possible.
