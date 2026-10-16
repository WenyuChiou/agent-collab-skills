---
name: agent-output-reconciler
description: Use when a plan, prompt, or doc still names agent-output-reconciler. Since 0.6.0 reconciliation is step 1 of agent-acceptance-gate; this redirect stub is removed in 0.7.0.
---

# agent-output-reconciler (redirect)

Merged into [agent-acceptance-gate](../agent-acceptance-gate/SKILL.md) in
0.6.0. Run that skill: its "Step 1: Reconcile" is the former workflow, and the
report template moved to
[reconciliation_template.md](../agent-acceptance-gate/references/reconciliation_template.md).

A plan that hands a round to the reconciler and then to the gate now needs one
gate pass. The rules are unchanged: missing and failed results stay distinct,
scope drift is recorded, and a reconciliation is not an acceptance decision.

This stub is removed in 0.7.0. See [migration 0.6](../../docs/migration-0.6.md).
