# Task-splitter heuristics — Codex vs cheap-Claude vs Claude

> **Gemini lane DEPRECATED (2026-06-18, fails closed — see the reroute
> table at the top of `SKILL.md`). No branch below routes to it.**

This is the deeper reasoning behind the routing table in
`SKILL.md`. Use this reference when:

- A task could plausibly go to two agents and you need to break the
  tie.
- You're tempted to split a task that should stay together.
- You're tempted to keep together a task that should be split.

## Routing decision tree

Ask these questions in order. The first YES picks the agent.

1. **Does the task require deciding between options based on
   project-specific judgment, prior decisions, or aesthetic taste?**
   → Claude.
   - Examples: "is this API design consistent with our existing
     conventions?", "should we keep legacy.py?", "is the tone of
     this email right for the audience?"

2. **Does the task require reading > 30 pages of source material
   in one pass to produce one synthesis?**
   → Claude if the synthesis needs judgment (what matters, what
   conflicts); claude-cheap if it is extraction/transcription-shaped
   (inventory what's there, pull the numbers, list the sections).
   - Examples: summarize 5 papers (claude), inventory the endpoints
     across 8 RFCs (claude-cheap), find terminology drift across a
     codebase's docs (claude-cheap to LIST candidates; claude to
     judge them).
   - Counter-example: "read this 50-line file and refactor it" —
     that's Codex; the read is incidental.

3. **Will the task produce CJK / Traditional Chinese / bilingual
   long-form output?**
   → Claude for judgment/語感-bearing prose (release notes,
   summaries); Codex for bulk mechanical CJK (mirror sync, term
   sweeps with a stated mapping).
   - Examples: 繁中 release notes (claude), zh-TW ↔ zh-Hans mirror
     sync per style guide (codex).

4. **Is the task "do roughly the same thing across N files"?**
   → Codex.
   - Examples: rename a config key in 12 files, add type hints to
     all functions in a module, generate test scaffolds for 8
     classes.

5. **Is the task "implement this spec into N lines of code"?**
   → Codex if the spec is concrete + the implementation is
   mechanical. Claude if the spec needs interpretation.
   - Concrete: "implement this function: signature `def foo(x: int) -> int`,
     returns x*2, raises if x < 0". → Codex.
   - Interpretive: "implement caching for the API client". → Claude
     (decisions about TTL, invalidation, key shape, eviction policy
     all need judgment).

6. **Is the task "review what was just written and find problems"?**
   → Claude, always — a review is an honesty-critical verdict and
   never goes to a cheap tier (measured: the cheap tier misses the
   subtle-honesty case 0/5; see `SKILL.md` §3).
   → Codex only for machine-checkable surfaces: type errors, lint
   compliance, test coverage gaps.

7. **None of the above clearly matches?**
   → Claude. Default to the most general-purpose agent when the
   task character is ambiguous.

## DAG patterns

### Linear chain (T1 → T2 → T3)

Each subtask depends on the previous one's output.

Use when:
- Step 2 needs to read step 1's diff to know what to do.
- Step 3 verifies step 2's output and step 2 verifies step 1's.

Example:
- T1 (claude): design the API contract
- T2 (codex): implement the API per T1's contract
- T3 (codex): write tests for T2's implementation

Cost: serial — total time = sum of task times. No parallelism.

### Fan-out (T1 → [T2, T3, T4])

One foundation task, then independent parallel tasks.

Use when:
- Step 1 sets up infrastructure / interface that N independent
  workers can use.
- Steps 2/3/4 don't need each other's output.

Example:
- T1 (codex): define abstract base class in `interfaces.py`
- T2 (codex): refactor provider A to inherit from ABC (parallel)
- T3 (codex): refactor provider B to inherit from ABC (parallel)
- T4 (claude): review T2 + T3 outputs for consistency (depends on
  both — actually this makes T4 a fan-in, see below; reviews are
  honesty-critical, so never a cheap lane)

Cost: bound by max(T2, T3, T4) after T1.

### Fan-in ([T2, T3] → T4)

Multiple independent tasks feed into a single review / synthesis.

Use when:
- A reviewer needs to read all the prior outputs to make a
  judgment.
- A test suite needs all components in place before it can run.

Example:
- T1 (codex): implement feature A
- T2 (codex): implement feature B (parallel with T1)
- T3 (claude): review T1 + T2 for design consistency (depends on
  both)

### Diamond (T1 → [T2, T3] → T4)

Combination — common in real refactors.

Use when:
- T1 is foundation, T2/T3 do parallel work on top, T4 reviews /
  reconciles.

This is the canonical "multi-agent run" shape and is what the
splitter most often produces.

## Anti-patterns to avoid

### Anti-pattern 1: Over-splitting

If you produce 7 tasks for a job that's really 2 tasks, you'll
spend more on overhead (context loading, reconciliation) than the
work itself. Rule of thumb:

- Each subtask should produce ≥ 30 lines of meaningful work
  (code, prose, analysis) or have clear value (e.g., a yes/no
  decision worth its own gate).
- If two adjacent subtasks always go to the same agent and have a
  trivial dependency, fold them together.

### Anti-pattern 2: Routing everything to Codex

If your plan has 5 tasks all `agent: codex`, the splitter isn't
earning its keep — you should have just written one big Codex task
file directly via `codex-delegate`. Multi-agent runs benefit from
heterogeneity. If the goal really is "Codex-only", invoke
`codex-delegate` not the splitter.

### Anti-pattern 3: Hidden cross-agent dependencies

Don't put files in T1 (Codex) that T3 (claude-cheap) needs to read
but not declare in `depends_on`. The DAG is the contract. If one
lane needs another's output, declare it.

### Anti-pattern 4: No success_criteria

A task without a checkable success criterion is a task the
acceptance-gate can't verify. Always declare ≥ 1 verifiable
criterion per task. If you can't think of one, the task is
probably underspecified — clarify the goal first.

### Anti-pattern 5: Architecture decisions in `agent: codex`

If a subtask requires picking between options (which library, what
data model, what API shape), it's not a Codex task — Codex will
pick whatever feels closest to existing code, not the right one.
Make it a Claude task or stage a debate via `agent-debate`.

## When NOT to split at all

If any of these are true, just use a single agent — don't invoke
the splitter:

- Total expected diff < 50 lines.
- Single-file change.
- All work is one character (all mechanical, all judgment-heavy,
  all long-form prose).
- The task is exploratory / debugging — splitting freezes a wrong
  decomposition.

The splitter earns its keep on **multi-step + multi-character +
moderate-to-large** work. For everything else, the overhead of
the plan + task files isn't worth it.
