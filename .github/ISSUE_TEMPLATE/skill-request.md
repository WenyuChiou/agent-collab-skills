---
name: Skill request
about: Propose extending one of the seven skills, or justify a new bounded skill.
title: "[skill-request] "
labels: enhancement
---

## What multi-agent pain point does this solve?

<one paragraph: when does this hurt in real workflows? Is it a
gap in the splitter → delegate → reconciler → gate pipeline, or
orthogonal?>

## Why don't the existing seven skills cover it?

<which skill is closest, and what it doesn't do>

## Proposed shape

- **Skill name:** `<proposed-name>` (must start with `agent-` for naming consistency in this bundle)
- **Trigger phrases** (3-5 examples):
  - "..."
- **Input** (which checkpoint, policy, task packet, or evidence references?):
- **Output** (scratch, shipping artifact, acceptance evidence, or memory proposal?):
- **Composes with** (which other skills / provider-neutral roles / host adapters):
- **Prerequisites** (CLI binary, `result.json` from prior agent run, etc.):

## Should it extend an existing skill or be a new one?

<argue one way or the other; new skills risk bloating the bundle, but
extensions can dilute scope>

## Out of scope

<what this skill specifically should NOT do — surfaces hidden
ambiguity early>
