# Debate protocol — how to stage productive adversarial review

The hard part of multi-agent debate isn't running it. It's
preventing the two agents from collapsing to the same answer by
round 2.

This reference documents the framing tricks that keep debate
genuinely adversarial.

## The framing failure mode

Without explicit anti-consensus instructions, LLM agents tend to:

1. Round 1: each side argues its assigned position.
2. Round 2: each side concedes most of the other side's points and
   suggests a hybrid.
3. By round 3: both sides agree on a consensus that nobody actually
   committed to.

This is the LLM equivalent of "design by committee" — produces
mush. The protocol below prevents it.

## Frame 1: Force commitment in Round 1

Each agent's Round 1 task file must include this constraint:

```markdown
## Constraints

- You must commit to Side <A or B>. You may not concede ANY
  point in Round 1.
- Concessions are only allowed in Round 2+, and only on points
  the other side made that you genuinely cannot rebut.
- "On the other hand" / "however" / "to be fair" are forbidden
  in Round 1 output.
- Length: 200-400 words. Going over is a penalty.
```

The "no hedging in Round 1" rule is doing the work. It forces the
agent to find the strongest version of its assigned argument.

## Frame 2: Steel-man requirement in Round 2

Round 2's task file:

```markdown
## Constraints

- Read the other side's Round 1 argument carefully.
- Identify the strongest 1 point they made. Concede it explicitly:
  "Side <other> is right that <X>. This is a real cost of Side
  <mine>."
- Then explain why Side <mine> still wins net, given that conceded
  cost.
- You may not concede the core thesis. If you find yourself
  agreeing with their core, scrap this round and admit you've
  changed your mind in plain text instead of pretending to argue.
- Length: 200-400 words.
```

The "concede their best point, then defend net" rule keeps the
debate productive. Each agent must engage with the other's
strongest argument, not strawman.

## Frame 3: Synthesis is by Claude, not by the debaters

Crucial: don't ask the debaters to synthesize their own debate.
They'll just average out to "both sides have a point."

The synthesis is done by **Claude in the active session**, after
reading the full transcript:

```markdown
## Synthesis (Claude as judge)

### Agreed facts
- <facts that emerged from the debate as common ground>

### Contested points
- <points where neither side conceded>

### Decision
- **Recommendation:** A or B, with confidence rating.
- **Rationale:** one paragraph.
- **What would change my mind:** falsifiable condition.
```

The "what would change my mind" line is critical — it forces the
synthesis to be falsifiable, not just preference dressed up as
analysis.

## Topic suitability checklist

Not every decision deserves a debate. Use the debate skill only
when ALL of these hold:

- [ ] The decision is consequential (you'll regret picking the
      wrong side; not "rename a variable").
- [ ] There's a real trade-off, not just one side being correct.
- [ ] You don't already know the answer and just want validation.
- [ ] The debate's output (~600-1500 words across rounds + synthesis)
      will save more time than it costs.

If any of these fail, don't debate — use a single-agent query.

## Side assignment heuristics

When the user doesn't specify which agent argues which side:

| Side character | Best argued by | Why |
|---|---|---|
| "Ship the simpler / smaller-surface option" | Claude | Tends toward conservative bias, won't manufacture features |
| "Optimize for performance / scale numbers" | Codex | Will produce concrete numbers + implementation specifics |
| "Watch out for edge case X / Y / Z" | Gemini | Long context = better at scanning for cases |
| "Follow convention from <reference>" | Gemini | Synthesis from external sources is its strength |
| "Question the framing of the question itself" | Claude | Most likely to challenge premises |

If the natural sides don't map cleanly to agents, just split based
on which agent is most willing to commit (Codex tends to commit
hardest; Claude hedges most by default).

## Anti-patterns

### Anti-pattern 1: Both sides argued by the same agent

Same-agent debate produces mush. Different agents have different
priors and blind spots — that's the point.

### Anti-pattern 2: Topic too vague

"Should we use AI for X?" is too vague. Reframe to "Should we use
LLM-based agent A for task X, or rule-based system B?" before
starting.

### Anti-pattern 3: One side obviously stronger

If one side is genuinely stronger and the user knows it, debate is
theater. Just pick the stronger side. Debate is for **genuinely
contested** decisions.

### Anti-pattern 4: More than 3 rounds

Diminishing returns. After round 2, agents start repeating
themselves. After round 3, you're paying tokens for noise.

### Anti-pattern 5: Letting agents implement during the debate

The debate task file must say "argument-only, no source files
modified." Otherwise one agent will start writing the code for
its preferred side and the debate becomes a fait accompli.

## Worked example

**Topic:** "Should we keep `legacy.py` as a deprecation shim or
remove it after the refactor?"

**Side A** (argued by Codex): keep it as a shim for one release.
**Side B** (argued by Gemini): remove now, force breaking change
in changelog.

**Round 1:**
- Codex (Side A): Concrete arg about backward-compat consumers,
  test_legacy_compat existence, semver expectations. 280 words,
  no hedging. Commits to "keep shim".
- Gemini (Side B): Cites references showing 70% of similar
  refactors that kept shims still removed them in a later release
  anyway, suggesting shims just delay pain. 320 words. Commits to
  "remove now."

**Round 2:**
- Codex: Concedes Gemini's point that shims often get permanent.
  Counters: in this case the consumer count is small (3 internal
  callers, all in our control), so the shim is bounded — different
  from the references Gemini cited.
- Gemini: Concedes Codex's point about bounded consumer count.
  Counters: the cost of the breaking change is one-time-now or
  permanent-pain-of-shim-maintenance; given low consumer count,
  one-time-now is cheaper.

**Synthesis (Claude):**

- Agreed: shim has real maintenance cost; consumer count is
  bounded (3 callers).
- Contested: whether 3 callers × 1 release of shim ≤ break-now
  cost.
- Decision: **Side B wins (remove now).** The shim's expected
  carrying cost (1+ releases of dual maintenance + risk of
  permanence) is greater than the one-time cost of updating 3
  internal callers.
- Confidence: medium.
- What would change my mind: if any of the 3 callers turn out to
  be external (vendored / forked code we don't control), shim
  becomes correct.

This is the kind of concrete output a real debate produces. If
your debate's synthesis reads like "both sides have a point, let's
do a hybrid", the framing failed — restart with stronger
adversarial constraints.
