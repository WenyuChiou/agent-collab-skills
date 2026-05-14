# Context Pressure Scenarios

Use these scenarios when testing whether the skills keep multi-agent
work bounded. They are pressure tests for behavior, not implementation
fixtures.

## large Codex + Gemini refactor

Ask for a four-task refactor with one Claude design task, two Codex
implementation tasks, and one Gemini audit. Expected behavior:
`agent-task-splitter` adds `context_policy`, each delegate task has a
clear write scope, and `agent-context-budget` writes
`.coord/context_001.md` plus `.coord/session_primer.md`.

## cross-session resume with long memory

Provide a `.coord/memory.yml` with many historical decisions and ask
for a fresh session primer. Expected behavior: the response summarizes
current decisions, unresolved questions, recent artifacts, and recent
sessions without pasting the whole memory file.

## Gemini task drift

Give Gemini an inline task where `.ai/` is gitignored and the task body
mentions the full plan. Expected behavior: `agent-output-reconciler`
checks task ID, slug, and agent assignment against `.coord/plan.yml`
and flags drift as high severity instead of treating the report as
valid evidence.

## agentmemory unavailable

Ask for cross-session recall while `agentmemory` is not installed or
not reachable. Expected behavior: the workflow continues using
`.coord/memory.yml`; optional recall is skipped and acceptance decisions
still depend only on `.coord/` artifacts and verification commands.
