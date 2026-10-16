---
name: agent-shared-memory
description: Use when a plan, prompt, or doc still names agent-shared-memory. Since 0.6.0 proposal-only coordination memory is the Durable decisions section of agent-context-budget; this redirect stub is removed in 0.7.0.
---

# agent-shared-memory (redirect)

Merged into [agent-context-budget](../agent-context-budget/SKILL.md) in 0.6.0.
Use its "Durable decisions" section. The event and proposal schema, approval
binding, and read/propose/decide/apply modes moved to
[coord_memory_schema.md](../agent-context-budget/references/coord_memory_schema.md).

The contract is unchanged: memory output is a proposal, only an explicit human
approval lets it apply, and applying appends a new event that never edits an
existing one.

This stub is removed in 0.7.0. See [migration 0.6](../../docs/migration-0.6.md).
