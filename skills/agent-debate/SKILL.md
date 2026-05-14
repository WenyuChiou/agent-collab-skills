---
name: agent-debate
description: Use when a consequential decision needs adversarial review, opposing agent arguments, a second opinion via debate, or explicit trade-off analysis before implementation.
---

# agent-debate

Anti-consensus tool. Most LLM output collapses to a single
"reasonable-sounding" answer that hides real trade-offs. For
**consequential decisions** (you'll regret picking the wrong
side), this skill stages an explicit pro/con debate between two
agents, then makes the disagreement legible.

This is **not** for routine choices — variable naming, file layout,
which library to use for a one-off script. It's for decisions where
there's a real trade-off and the "obvious" answer might be wrong.

## When to use

Trigger phrases:

- "Have Claude and Codex debate this design choice."
- "Adversarial review on `<decision>`."
- "Get a second opinion via debate."
- "I'm not sure about this — make the agents argue it out."
- "Steel-man both sides on `<topic>`."

Not for:

- Routine choices (pick whatever; doesn't matter long-term).
- Decisions where you already know the right answer and just want
  validation (that's confirmation bias; the debate will waste
  tokens).
- Open-ended brainstorming (use a single agent + lots of follow-ups).

## Inputs

User must provide:

1. **The decision** — phrased as a yes/no or A/B question.
   - Good: "Should we keep legacy.py as a deprecation shim or
     remove it?"
   - Bad: "What should we do about legacy.py?" (too open)
2. **Optional**: which agent argues which side. If unspecified, the
   skill picks based on agent strengths (see below).
3. **Optional**: number of rounds. Default 2 (each agent gets 2
   turns). More than 3 rarely adds signal.
4. **Optional**: context policy. Default debate turns are 200-400
   words, final synthesis is <= 250 words, and only the accepted
   decision is eligible for shared memory.

## Workflow

### 1. Frame the decision

Restate the decision as a clear A vs B (or yes vs no). If the user
gave an open-ended question, propose the framing back to them and
get confirmation before spending tokens on a debate.

Example:
- User: "Should we cache LLM responses?"
- Skill: "Framing: **A) Yes, add an LRU cache keyed on prompt
  hash** vs **B) No, every call is unique enough that caching adds
  bug surface without saving money.** Confirm before I proceed."

### 2. Assign sides

Default heuristic:

| Position character | Best argued by |
|---|---|
| "We should ship the simpler / less-surface option" | Claude (judgment-heavy, conservative bias) |
| "We should optimize for X performance / scale dimension" | Codex (concrete with numbers) |
| "We should consider edge cases X / Y / Z that the obvious answer misses" | Gemini (long-context, edge-case catching) |
| "We should follow the convention from <reference codebase or paper>" | Gemini (synthesizing from external sources) |

If the user explicitly assigns sides, use those. Otherwise propose
the assignment and confirm.

### 3. Initialize `.coord/debate_<topic>.md`

```markdown
# Debate — <topic-slug>

**Decision:** <one-line A vs B framing>
**Rounds:** 2
**Side A** (argued by Codex): <position A>
**Side B** (argued by Gemini): <position B>
**Started:** 2026-04-28T...

---

## Round 1

### Side A — Codex
<task: read .coord/debate_<topic>.md, argue Side A from scratch>
<argument here>

### Side B — Gemini
<task: read .coord/debate_<topic>.md (which now contains Codex's
arg), argue Side B as a rebuttal>
<argument here>

---

## Round 2

### Side A — Codex
<task: read updated debate file, rebut Side B>
...
```

### 4. Generate task files for the debate rounds

For each agent's turn, write a task file in their delegate-skill
format:

`.ai/codex_task_debate_<topic>_round1.md`:

```markdown
# Task: Argue Side A in debate on <topic>

## Context
- Repo: <path>
- Read: .coord/debate_<topic>.md (the debate transcript so far)
- Side A: <position A>
- Your role: argue Side A. Be specific. Reference real code / files
  / numbers. Don't hedge ("on the other hand" is forbidden).
- Do NOT touch any source files. This is argument-only.

## Goal
Write a 200-400 word argument for Side A, focused on:
- The strongest specific reason Side A is right.
- The most concrete failure mode of Side B (with a worked example
  if possible).
- One thing Side B might say that you concede is a real cost of
  Side A.

## Acceptance
- Append your argument under "## Round 1 / ### Side A — Codex" in
  .coord/debate_<topic>.md.
- Keep argument 200-400 words. Longer = penalty.
- No "on the other hand" hedging.
```

Subsequent rounds: same template, but task file says "rebut Side B's
Round N argument; concede any genuinely strong point but explain
why Side A still wins net." Each round's task file references the
previous rounds in the debate file as input.

### 5. Run the rounds

Hand off to `codex-delegate` / `gemini-delegate` to execute each
agent's turn. They write into the debate file directly (the task
file says where to append).

### 6. Synthesize

After the final round, Claude (in-session, not delegated) reads
the full debate transcript and writes the synthesis at the bottom:

```markdown
---

## Synthesis (Claude as judge)

### Agreed facts (both sides accept)
- <facts that emerged from the debate as common ground>

### Contested points (genuine disagreement)
- <points where neither side conceded>

### Decision
- **Recommendation:** A or B (with one-paragraph rationale).
- **Confidence:** high / medium / low.
- **What would change my mind:** <falsifiable condition>.
```

Keep the synthesis under 250 words unless the user explicitly asks
for a longer decision record. If the recommendation is accepted,
promote only the final decision and rationale to `.coord/memory.yml`;
do not promote the full debate transcript.

### 7. Hand off

```
[agent-debate]
  Topic: <topic-slug>
  Rounds: 2
  Transcript: .coord/debate_<topic>.md
  Synthesis: bottom of same file
  Recommendation: <A or B>, confidence <high/medium/low>

  Update .coord/memory.yml with this decision via agent-shared-memory
  if you accept the recommendation.
```

## Anti-patterns to avoid

- **Forcing both sides to be equally strong** when one is genuinely
  weaker. Honest debate sometimes ends "Side A wins decisively." If
  that's what came out, say so — don't manufacture a 50-50 to seem
  balanced.
- **Letting both sides converge to the same view by Round 2** ("both
  sides agree the answer is C, a third option neither argued"). If
  that happens, scrap the debate — neither side actually committed.
  Restart with stronger framing.
- **More than 3 rounds.** Diminishing returns kicks in fast. If you
  haven't found the disagreement by round 3, the question wasn't
  contested enough to debate.
- **Debating something where you already know the answer.** That's
  confirmation theater, not adversarial review.

## What NOT to do

- **Don't write source code as a side effect of the debate.** The
  task files explicitly forbid touching source. Debate is
  argument-only; implementation comes after the user picks a side.
- **Don't have the same agent argue both sides.** Different agents
  have different priors / blind spots — that's the point.
- **Don't update `.coord/memory.yml` automatically.** The
  recommendation goes there only if the user accepts it. Use
  `agent-shared-memory` separately to log the decision.
- **Don't let debate transcripts become memory.** Store the transcript
  as `.coord/debate_<topic>.md`; memory gets only the accepted
  decision, if any.

## Hard caps (enforced by `agent-acceptance-gate` when debate is wired into a plan round)

If the debate is referenced from `.coord/plan.yml` (i.e., recorded as a
formal task with `agent: claude` or similar), the acceptance gate
checks these caps against `.coord/debate_<topic>.md`:

| Field | Cap |
|---|---|
| Per-turn argument (Pro / Con) | 400 words |
| Total rounds | 3 (override requires explicit user opt-in in plan.yml `debate_rounds`) |
| Final synthesis section | 250 words |
| Total debate file size | 8 KB (~ 1200 words across all rounds + synthesis) |

If the debate is invoked ad-hoc (no plan.yml round), these caps are
soft guidance — Claude should still respect them but no automated
gate runs. **For consequential decisions, always wire the debate
into a formal round** so the gate enforces the cap.

When caps are exceeded:
- Pro/Con turn over 400 words → reject the turn, ask the agent to
  compress to ≤400 before continuing.
- Synthesis over 250 words → rewrite to ≤250 before promoting any
  decision to memory.
- Total file over 8 KB → debate is no longer auditable in a glance;
  recommend splitting into sub-debates per sub-decision.

## Subagent review (keep main session lean)

**When**: Debate enters round 3+, OR `.coord/debate_<topic>.md`
exceeds 4 KB.

**Why**: After 2-3 rounds, the full transcript is heavy. The judge
synthesis is where the user actually consumes value. A subagent can
read the entire transcript and return only the synthesis + verdict,
so the main session never holds the full Pro/Con turns.

**Pattern**:

```
Spawn `general-purpose` subagent (read-only) with:
  - Read .coord/debate_<topic>.md (entire transcript)
  - Verify cap compliance: each turn ≤ 400 words, total ≤ 8 KB,
    rounds ≤ 3 (or plan-declared override)
  - Compose synthesis (≤ 250 words) covering: framing, strongest
    Pro argument, strongest Con argument, recommended decision,
    confidence level, conditions to revisit
  - Return: synthesis text + cap-violation flags

Main session reads only the synthesis; if user accepts, `agent-shared-memory`
promotes the decision (NOT the transcript) to `.coord/memory.yml`.
```

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
~/.claude/CLAUDE.md → "Commit Discipline for Multi-Agent Work"). This
makes multi-agent work auditable (commit log = agent log) and enables
surgical rollback via `git revert <hash>` of just one agent's commit.

**Specific to this skill**: each round (Pro turn, Con turn, judge verdict) is a commit. The full debate is then a commit-by-commit replay. If Pro and Con both edit the same file in a round, the second commit appears as the contested diff that the judge resolves in the third commit.
