---
name: agent-context-budget
description: Use when multi-agent work risks context overflow, memory growth, noisy logs, oversized handoffs, cross-session continuation, or parallel Codex and Gemini execution.
---

# agent-context-budget

Context governor for multi-agent rounds. The core rule is simple:
keep `.coord/` as the canonical state, pass agents compact packets,
and never paste raw logs or unbounded memory into the main session.

## When to Use

Use this before or during:

- Large Codex + Gemini + Claude runs.
- Cross-session resumes where the prior conversation is too large.
- Any round with more than two delegate tasks.
- Any workflow where `.coord/memory.yml`, `.ai/*_log_*.txt`, or agent
  summaries are starting to dominate the prompt.

Not for small one-agent edits. Use the direct delegate skill instead.

## Default Policy

If `.coord/plan.yml` lacks `context_policy`, add this block:

```yaml
context_policy:
  main_session_token_budget: 3000
  task_packet_token_budget: 6000
  result_summary_word_budget: 250
  memory_digest_token_budget: 1200
  log_tail_lines_on_error: 50
  raw_log_policy: path-only
  agentmemory: optional

  # W3 — $ cost gate per task (v0.2.2+)
  # Optional. If set, agent-acceptance-gate flags any task whose
  # codex/gemini delegate exceeded the cap. Estimated from token
  # usage × provider price (Anthropic / OpenAI / Google rates).
  # Set per-task in plan.yml tasks[].budget.max_cost_usd to override.
  default_max_cost_usd: 0.50  # default $ ceiling per task
  total_round_max_cost_usd: 5.00  # hard stop for the entire round
```

**Why both `token` and `cost` budgets?** Token gate prevents context
bloat (a session quality concern). Cost gate prevents runaway delegation
spend (a financial concern). They're orthogonal: a 2k-token delegate
call can cost $0.05 (Claude Haiku) or $0.50 (Claude Opus), so token
count alone doesn't bound dollars.

Per-task override example:

```yaml
# in plan.yml
tasks:
  - id: T1
    agent: codex
    slug: simple-refactor
    budget:
      max_cost_usd: 0.10  # this task is mechanical, cap low
  - id: T2
    agent: codex
    slug: complex-rewrite
    budget:
      max_cost_usd: 2.00  # this task needs frontier model, allow higher
```

## Workflow

1. Read `.coord/plan.yml` and `.coord/memory.yml` if present.
2. Write `.coord/context_<NNN>.md` with:
   - round goal and success criteria
   - task graph and write ownership
   - per-agent context packets to include
   - context intentionally excluded
   - optional `agentmemory` recall queries, if available
3. Write or refresh `.coord/session_primer.md` with:
   - current decisions
   - open questions
   - active round status
   - recent artifacts by path
   - no raw logs
4. Enforce result packets:
   - delegate summaries are <= 250 words
   - changed files are listed by path
   - tests are listed by command + result
   - risks are explicit and short
5. If a log is needed, include only the path. Read the last 50 lines
   only when the corresponding `result.json` status is `error`.

## Optional agentmemory

`agentmemory` is a recall cache, not the source of truth.

- Query it only to enrich `.coord/session_primer.md`.
- Store only compact memory candidates: accepted decisions, resolved
  open questions, artifact summaries, and final session outcomes.
- If it is unavailable, continue with `.coord/memory.yml` only.
- Never use vector recall as acceptance evidence. The acceptance gate
  must read `.coord/plan.yml`, result files, reconciliation, and tests.

## Memory Promotion Rules

Promote only:

- Decisions with a one-sentence `what` and `why`.
- Open questions with a blocker and suggested next owner.
- Artifact pointers with one-line summaries.
- Agent session outcomes with status and result-summary path.

Do not promote:

- Raw logs.
- Full diffs.
- Source code.
- Long analysis.
- Secrets or credentials.

## Output

End with:

```text
[agent-context-budget]
  Round: <N>
  Policy: .coord/plan.yml context_policy
  Context plan: .coord/context_<NNN>.md
  Session primer: .coord/session_primer.md
  Raw logs: path-only; failure tail max 50 lines
  agentmemory: optional cache, not required
```

## Common Mistakes

- Pasting full logs into chat. Store the path; read bounded tail only
  on failure.
- Treating memory as a transcript. Promote decisions, questions,
  artifacts, and outcomes only.
- Giving Gemini only `.ai/` paths. Inline critical context because
  `.ai/` may be gitignored.
- Using agentmemory as the gate. Gate with tests and `.coord/`
  artifacts.

## Subagent review (keep main session lean)

**When**: ≥ 3 task packets exist and you want to verify they stayed
within the declared `task_packet_token_budget` (default 6000 tokens
≈ 24 KB) without re-reading them all in the main session.

**Why**: After writing `.coord/context_<NNN>.md` + `session_primer.md`,
the main session has the policy in context but doesn't need to re-read
every packet to verify compliance. A subagent can scan all packets
and return only the over-budget list.

**Pattern**:

```
Spawn `code-reviewer` subagent:
- Read .coord/context_<NNN>.md (the declared per-task budgets)
- Read each .ai/<agent>_task_<NNN>_*.md file referenced in plan.yml
- For each, count rough tokens (word count × 1.3 as approximation)
- Return: a single PASS/FAIL line + list of any task slugs > 120%
  of declared budget + suggested compression target

Main session reads only the verdict.
```

If subagent reports FAIL, regenerate the over-budget packets with
tighter prompts before invoking delegates.

## Commit Boundary

Every agent boundary is a commit boundary (see global rule:
`~/.claude/CLAUDE.md` → "Commit Discipline for Multi-Agent Work").

**Specific to this skill**: writing `.coord/context_<NNN>.md` and
`.coord/session_primer.md` are session-setup artifacts — commit
them as a single round-prep commit so the budget policy used for
the round is auditable. Pattern:

```
git add .coord/context_<NNN>.md .coord/session_primer.md
git commit -m "context: round <N> budget plan + session primer"
```

The acceptance gate later verifies actual round consumption against
this committed policy.
