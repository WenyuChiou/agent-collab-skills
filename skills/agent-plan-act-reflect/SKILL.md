---
name: agent-plan-act-reflect
description: Use when a task needs single-agent self-correction across multiple iterations — write plan, execute, critique own output, revise plan, re-execute, until convergence or budget exhausted. Different from `agent-debate` (which is 2 agents arguing pro vs con); this is 1 agent looping over its own work.
---

# agent-plan-act-reflect

Single-agent iterative self-correction loop. Composes existing
building blocks (task-splitter / shared-memory / acceptance-gate)
into one closed cycle.

This is the **agent equivalent of test-driven development**: write
spec, build, test, fail, revise, build again, until pass. Where
`agent-debate` is "2 agents disagree", PAR is "1 agent revises".

## When to use

Good for:
- A single agent owns the task end-to-end, but the first attempt
  rarely lands clean (refactors, papers, optimizations, anything
  with > 3 quality dimensions to balance)
- The success criterion is automatically checkable (tests, eval, linter)
- Budget allows 2-5 iterations
- You want a paper trail of what was tried + why it failed

Not for:
- Single-shot tasks (overkill)
- Tasks where two agents should argue opposing designs (use `agent-debate`)
- Multi-agent coordination (use `agent-task-splitter`)
- Pure exploration / ideation (no test criterion to drive iteration)
- Tasks where a human is the final adjudicator (PAR can't replace human review for high-stakes decisions; run PAR, then present result to human)

## Inputs

User must provide:

1. **Goal** — single sentence, with concrete acceptance criterion
   - Good: "Stage 6 §RAG section reads at < 10 grade-level + passes anchor strict"
   - Bad: "Make Stage 6 better"
2. **Max iterations** — default 3. After this many cycles without
   convergence, surface to user.
3. **Critique source** — what gives the "fail signal" each iteration:
   - Test results (preferred — most objective)
   - Subagent review (next-most objective)
   - Eval framework score (ragas / promptfoo / etc.)
   - Self-critique by the same agent (least reliable, only as fallback)
4. **Optional**: which delegate (Claude inline / Codex / Gemini). Default Claude inline.

## Workflow

```
write plan ──► .coord/par_<topic>.yml
    │
    ▼
┌──────────────────────────────────────┐
│  Iteration loop (cap = max_iterations): │
│                                      │
│  Act    ─► delegate executes        │
│             writes result.md         │
│                                      │
│  Reflect ─► run critique source     │
│             (test / subagent /      │
│              eval / self)            │
│                                      │
│  Pass?   ─► YES → exit loop with PASS │
│            NO  → continue if N <    │
│                  max_iterations      │
│                                      │
│  N = max?─► YES → exit loop with    │
│                   `EXHAUSTED` —     │
│                   surface to user   │
│            NO  → continue           │
│                                      │
│  Revise  ─► update .coord/par_      │
│             <topic>.yml with        │
│             learned-from-failure    │
└──────────────────────────────────────┘
    │
    ▼
write final summary → .coord/par_<topic>_final.md
+ promote learned principles → .coord/memory.yml
```

**Exit conditions (be explicit, prevents runaway loops)**:
- Verdict PASS at any iteration → exit immediately with status `PASS`
- N reaches `max_iterations` without PASS → exit with status `EXHAUSTED`, surface to user with summary of all failed attempts
- Any iteration fails with status `error` (test infrastructure crash, delegate timeout, etc.) → exit with status `ERROR`, do NOT continue

The loop NEVER continues past `max_iterations`. The anti-pattern says
"don't go past 5"; the workflow enforces this by failing closed.

## Outputs

- `.coord/par_<topic>.yml` — running state (plan + iteration history)
- `.coord/par_<topic>_final.md` — final summary + lessons (≤ 500 words)
- Promoted principles → `.coord/memory.yml` (via `agent-shared-memory`)

## par_<topic>.yml schema

```yaml
goal: "Stage 6 §RAG passes plain-language test"
acceptance_criterion: "subagent code-reviewer scores >= 8/10 on clarity"
max_iterations: 3
critique_source: subagent
delegate: claude-inline

iterations:
  - n: 1
    plan_summary: "Drop encyclopedic table; replace with prose + 3 concrete examples"
    artifact: ".coord/par_rag_iter1.md"
    critique:
      score: 6
      issues:
        - "Examples still too abstract (no specific Yelp/database)"
        - "DSPy reference confuses scope"
      verdict: FAIL
    revise: "Add concrete Yelp example; drop DSPy until next iteration"

  - n: 2
    plan_summary: "Apply iter-1 revisions"
    artifact: ".coord/par_rag_iter2.md"
    critique:
      score: 8
      issues:
        - "Heading hierarchy still inconsistent"
      verdict: CONDITIONAL PASS
    revise: "Fix heading levels; minor polish"

  - n: 3
    plan_summary: "Final polish"
    artifact: ".coord/par_rag_iter3.md"
    critique:
      score: 9
      issues: []
      verdict: PASS

final_status: PASS
total_cost_usd: 0.45
elapsed_minutes: 22
```

## Anti-patterns

- **Don't loop more than 5 times.** If after 5 the agent hasn't
  converged, the goal is probably mis-specified or the critique
  source is inconsistent. Surface to user, don't keep burning $.
- **Don't use self-critique as the only critique source.** The agent
  that wrote the code will mostly approve its own code. Bias is
  real and well-documented. Use external test / subagent / eval.
- **Don't promote raw iteration content to memory.** Only PROMOTE
  the learned principle (e.g., "DSPy belongs in §進階 RAG, not in
  intro") to `.coord/memory.yml`. Iteration artifacts stay in
  `.coord/par_*.md` and get archived after 14 days like other
  `.ai/` files.
- **Don't run PAR for trivial tasks.** Single-shot is fine for
  typo fixes, sweep rules, single-file edits. PAR is for tasks
  where 1 iteration is reliably insufficient.

## Subagent review (keep main session lean)

**When**: PAR loop enters iteration 3+, OR `.coord/par_*.yml` exceeds 8 KB.

**Why**: Main session that wrote the original plan + observed
iteration 1+2 results doesn't need to re-read all artifacts in
later iterations. A subagent can read the par_*.yml + recent
iteration artifact + return a structured "should we iterate again
or stop?" verdict.

**Pattern**:

```
Spawn `code-reviewer` subagent:
  - Read .coord/par_<topic>.yml in full
  - Read latest iteration artifact (.coord/par_<topic>_iterN.md)
  - Apply critique source (test results / preset / etc.)
  - Return: { verdict: PASS/CONDITIONAL/FAIL,
              top 3 issues: [...],
              recommend: continue/stop/escalate,
              estimated_iterations_remaining: N }

Main session reads only the verdict.
```

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
`~/.claude/CLAUDE.md` → "Commit Discipline for Multi-Agent Work").

**Specific to this skill**: each iteration is its own commit with
message `par(iter-N): <plan_summary>`. The final `PASS` iteration
commit can be followed by a `par(final): merge to main` commit
that includes the principle promotion to `.coord/memory.yml`.

This makes the PAR loop **a commit-by-commit replay**: a future
maintainer can `git log --grep "par(iter"` to see the full
self-correction history.

## Composes with

- `agent-task-splitter` — write the initial plan
- `agent-shared-memory` — promote learned principles after PAR converges
- `agent-acceptance-gate` — can be the critique source for an iteration
- `agent-debate` — different tool (multi-agent disagreement). Use PAR
  for single-agent self-correction; use debate for adjudicating between
  two equally-valid options.

## Output to user (final message format)

```
[agent-plan-act-reflect]
  Goal: <one-line goal>
  Status: PASS after N iterations
  Final artifact: <path>
  Cost: ~$X.XX total
  Promoted to memory: <list of principles, if any>

  Iteration summary:
    iter 1: FAIL (score 6/10) → revised plan
    iter 2: CONDITIONAL (score 8/10) → minor polish
    iter 3: PASS (score 9/10)

  Time: ~N min wall-clock
```
