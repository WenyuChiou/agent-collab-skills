---
name: agent-debate
description: Use when a consequential decision has two plausible, materially different options and you are about to pick one. Runs two opposed reviewers on the same evidence with a stated round cap, then hands the human a synthesis that names the deciding evidence.
---

# agent-debate

A bounded adversarial review of one consequential trade-off. Debate makes the
evidence visible to the decision maker; it does not settle truth by vote and
does not authorize implementation.

## Use only when

- both options are plausible and materially different;
- the decision is consequential enough to justify two independent reviewers;
- identifiable evidence could inform or falsify each side.

Do not debate a factual question that a direct check can settle, a naming
preference, or a decision an authorized human already made.

## Setup

1. Write one evidence packet: the decision and who owns it, the two
   positions as testable statements, shared evidence paths, and the criteria
   for judging. Template: [references/debate_protocol.md](references/debate_protocol.md).
2. Launch two `reviewer` lanes in parallel, one position each, both on a
   strong model tier, both read-only, both with the same packet. Each argues
   the strongest form of its side and cites evidence.
3. State the round cap before launch and stop there. A rebuttal round, if
   the cap allows one, answers the other side's strongest point. In harness
   mode the policy's `max_cycles` limit sets the cap; evaluate the policy
   before each reviewer spawn.
4. A reviewer that changes its conclusion says so plainly; do not simulate
   disagreement.

## Synthesis

The primary-agent, or a separate `synthesizer` with no search tools, writes:

- agreed facts, with evidence;
- contested claims, with the evidence on each side;
- missing or failed reviewer outputs (recorded, never invented);
- a recommendation, how uncertain it is, and what finding would change it;
- the pending human decision: approve, decline, or revise.

Nothing is implemented and no canonical memory changes until the human
decides. If the outcome is worth keeping, write a memory proposal as described
in `agent-context-budget`.

## Prohibitions

- No majority vote as evidence or acceptance.
- No silent retry, model switch, context discard, or invented missing side.
- No source edits, commits, merges, or pushes during the debate.
- No direct write to canonical memory.
