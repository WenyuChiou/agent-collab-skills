---
name: agent-debate
description: Use when a consequential decision has genuinely competing positions that need bounded adversarial review before a human decision.
---

# agent-debate

Run a bounded adversarial review of a consequential trade-off. Debate improves
the evidence visible to a decision maker; it does not establish truth by vote
and does not authorize implementation.

## Preconditions

Use debate only when:

- the positions are both plausible and materially different;
- the decision is consequential enough to justify independent review;
- the question can be falsified or informed by identifiable evidence; and
- the current policy allows the required work.

Do not debate a factual question that can be settled by direct verification, a
minor naming preference, or a decision already made by an authorized human.

## Roles

- Independent `reviewer` task packets argue named positions.
- A `synthesizer` compares their evidence without external tool access unless
  the plan explicitly grants it.
- The `primary-agent` records the recommendation and presents it to the human.
- The human approves, declines, or requests revision.

Provider and model names belong to host-adapter metadata, not the public debate
contract.

## Workflow

1. Define the decision, alternatives, known facts, disputed assumptions,
   evidence standard, and human decision owner.
2. Evaluate policy before every reviewer spawn. Persist a required checkpoint
   before continuing.
3. Give each reviewer the same evidence packet plus one position to steel-man.
   Reviewers are argument-only and must not modify source files.
4. After each plan-act-reflect cycle, update the `TaskCheckpoint` and evaluate
   policy. Stop immediately when policy says `stop`.
5. Filter missing or failed reviewer outputs, but record their status. Never
   invent the absent side.
6. Have the synthesizer separate agreed facts, contested claims, evidence
   quality, uncertainties, and falsifiable conditions that would change the
   recommendation.
7. Present the synthesis to the human decision owner. No implementation or
   canonical-memory update occurs without an explicit recorded decision.

All cycle, context, concurrency, and transcript limits come from the canonical
machine-readable policy. Do not hardcode them in task packets or prose.

## Output

Produce a scratch debate record containing:

- decision and alternatives;
- policy and checkpoint references;
- each position's claims and evidence references;
- missing or failed reviewer records;
- agreed facts and contested points;
- synthesizer recommendation, uncertainty, and what would change it;
- pending human decision.

If the outcome may be useful later, emit a memory proposal. The proposal may
become canonical only after an explicit human decision; resolution appends a
new event and never rewrites an earlier memory record.

See `references/debate_protocol.md` for task framing.

## Prohibitions

- No majority vote as an evidence or acceptance mechanism.
- No silent retry, model switch, context discard, or missing-result coercion.
- No implementation, source mutation, commit, merge, or push during debate.
- No direct write, overwrite, archive, or deletion of canonical memory.
