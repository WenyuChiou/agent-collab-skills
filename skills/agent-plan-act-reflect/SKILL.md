---
name: agent-plan-act-reflect
description: Use when a plan, prompt, or doc still names agent-plan-act-reflect. Deprecated in 0.6.0; ordinary iterate-until-it-passes work needs no skill, and an unattended policy-driven loop follows agent-context-budget's harness loop reference. This stub is removed in 0.7.0.
---

# agent-plan-act-reflect (deprecated)

Deprecated in 0.6.0 and removed in 0.7.0.

- Iterating with the user present (edit, run the check, fix, repeat) needs no
  skill. Keep the acceptance check runnable and report its real result.
- An unattended multi-cycle loop under a configured `agent-collab` policy
  follows [harness-loop.md](../agent-context-budget/references/harness-loop.md),
  the former body of this skill. It still runs `agent-collab policy evaluate`
  after every cycle and before every spawn.
- Comparing two consequential alternatives is
  [agent-debate](../agent-debate/SKILL.md), not a loop.

See [migration 0.6](../../docs/migration-0.6.md).
