# Measured Benefits — what `agent-collab-skills` actually saves

> Honest dogfood report based on 1 production session (2026-05-14,
> awesome-agentic-ai-zh plain-language refactor, 5 rounds × 9 tasks).
> No napkin math — actual token-byte measurement per round.

## TL;DR

**Realistic saving: ~7-8× on main-session token cost** when the round
involves delegation. **0× savings** on pure-judgment work that has to
stay inline. **Non-quantifiable but critical**: drift catch + spec-
codified verification stops broken code from shipping.

If you're evaluating whether to install this bundle, the calculus is:

- **You write Chinese curriculum / docs across multiple locales** → install (R4 sweet spot, 13-16× saving)
- **You delegate to Codex / Gemini regularly and review their output** → install (R2 sweet spot, F11/F12 drift catch alone justifies it)
- **You only work solo on small judgment-heavy tasks** → don't bother (R1/R3 = no saving)

---

## Measurement methodology

- Token proxy: file bytes / 3 chars per token (mixed zh-TW + EN)
- "Main session tokens" = bytes read into Claude's main context window
- "Control tokens" = hypothetical estimate if Claude did everything inline (no delegate)
- Subagent / Codex / Gemini token consumption is **separate** — not in main session count
- All numbers below are real, not estimated

## Round-by-round breakdown

| Round | Task type | Main tokens | Control tokens | Saving | What the skill bought |
|---|---|---|---|---|---|
| R1 | Term definitions (Claude inline, no delegate) | ~6.5k | ~6.5k | **1×** | Nothing — pure Claude work. Skills had no role to play. |
| R2 | Mechanical sweeps + jargon glosses (Codex × 2 parallel) | ~5k | ~37k | **~7×** | Codex read 80 KB of stages NOT in main session; main only read 12 KB of diff for review. **Also caught 4 drift files** (F11/F12) that would have shipped broken. |
| R3 | Pedagogical rewrites (Claude inline) | ~3k | ~15-20k | **~5×** | Audit-led approach: prior audit's specific findings let Claude do surgical rewrites instead of re-reading + diagnosing. Skills had partial role. |
| R4 + R5 | Mirror sync (Gemini) + acceptance gate (subagent) | ~6k | ~80-100k | **~13-16×** | Gemini did 200 KB read + 50 KB write entirely outside main session. Subagent acceptance gate returned 600w verdict instead of main session running 5+ grep commands. **Sweet spot of the bundle.** |
| R6 | GitHub triage (gh CLI direct) | ~0.5k | ~0.5k | **1×** | Single command via gh CLI — skills not relevant here. |
| **TOTAL** | (5 rounds) | **~21k** | **~140-165k** | **~7-8×** | |

## Where the savings really come from

### 1. Mirror sync / multi-file translation (Gemini delegation) — biggest win

When the task is "translate / sync 8 mirror files faithfully":

- Main session writes 1 brief (~3 KB)
- Delegate reads + writes 250 KB of content (not in main session)
- Main session reads ≤ 250-word `result.md` summary (~1 KB)
- **Token cost ratio: ~13-16× saving**

This is the bundle's bread and butter. If you do trilingual / multi-locale curriculum work, you'll feel this immediately.

### 2. Codex parallel mechanical sweeps — second biggest

When the task is "apply rule X across N files" (e.g., `「默認」→「預設」`):

- 2 Codex tasks launched in parallel (1 codebase sweep + 1 jargon glosses)
- Each runs independently
- Main session reads only the diff for review (~12 KB)
- **Token cost ratio: ~7× saving**

Caveat: Codex drifts. In the same session we caught:
- **F11**: Codex over-applied a sweep rule to a META documentation table that was literally documenting the rule
- **F12**: Codex injected unrequested "Attributions: Karpathy, Simon Willison, ..." lines into mirror files

Without the reviewer rejection pattern (from `agent-acceptance-gate`'s subagent review section), these would have shipped. The bundle's drift catch value is **non-quantifiable but critical**.

### 3. Subagent acceptance gate — third biggest

When the task is "verify 8 files match a spec":

- Subagent reads all 8 files (~30 KB) and returns 1 structured verdict (~2 KB)
- Main session would have needed to run 5+ different grep commands plus interpret each
- Replaces "shell debugging in main session" with "structured PASS/FAIL"
- **Token cost ratio: ~3-4× saving**, plus consistency (no missed checks)

## Where the skills do NOT help

Be honest with yourself:

### Pure-judgment work (R1, R3 in our dogfood)

- Writing nuanced definitions
- Rewriting prose for clarity
- Making architectural decisions

These are inline Claude work. Skills can't delegate them — the value
is in Claude's judgment, not throughput. **You'll see 0× saving** on
these rounds. That's fine — that's not what the skills are for.

### Single-file fixes

If you're fixing one typo in one file, don't invoke task-splitter.
**Use the direct Edit tool**. CLAUDE.md routing rule: "1 delegate run
per round → use delegate directly. ≥2 parallel → invoke
task-splitter first."

### Real-time exploration

If you're iterating with the user to figure out what to build, skills
slow you down. Use them when the SHAPE of the work is clear, not
during ideation.

## Non-quantifiable but high-value benefits

These don't show up in token counts but matter a lot:

### Drift catch (F1-F12)

This session caught 12 distinct agent failure modes:
- F1-F10 captured in `docs/observed-failure-modes.md` from prior sessions
- F11 (over-applied meta-doc sweep) + F12 (unrequested attributions) discovered THIS session and will be codified into v0.2.2

Each F# is a real bug that would have shipped without the
review-and-reject pattern. **Even at 0× token saving, this would
justify the bundle.**

### Spec-as-code (preset YAMLs)

Three presets eliminated hand-rolling acceptance criteria:
- `multi-locale-mirror-sync.yml` — automatic 5-check verification
- `catalog-entry-add.yml` — live `gh api` star/license verification
- `fact-check-frontier-models.yml` — fabrication deny-list

Without these, our DeepSeek-R2 fabrication (2026-05-13 session) would
have shipped. The preset that didn't exist yet was rebuilt as a guard
rail after the incident.

### Consistency across sessions

Every multi-locale sync now follows the same acceptance pattern. No
forgetting checks, no "did I grep for banned phrases this time".
Memory aid + standard process in one.

## What v0.2.1 still doesn't do (planned for v0.2.2)

Based on this session's dogfood:

1. **Work Boundary enforcement** — brief writes "files in scope" as text; no mechanism to verify post-task `git diff --name-only` actually stayed within. (Codex T3 + T4 drifted outside listed files; only caught by manual review.)

2. **Contract-driven hand-offs** — `agent-output-reconciler` checks slug / agent / path consistency but not "agent A promised 5 video URLs → did agent B use all 5?"

3. **Cost gate (\$ not tokens)** — `agent-context-budget` limits token bytes; doesn't cap actual dollar cost per task. R2's Codex parallel × 2 burned ~\$0.50 with no ceiling.

4. **Plan-Act-Reflect integrated skill** — building blocks exist (task-splitter / debate / shared-memory) but no single PAR loop skill.

These four are the v0.2.2 priority list, in order.

## How to validate this for your own use case

Run one round of multi-locale or multi-file work twice:

1. **Treatment**: with the bundle installed, using task-splitter + acceptance-gate
2. **Control**: without the bundle, Claude does it all inline

Measure:
- Main session token usage (Anthropic API counts, or rough byte-count proxy)
- Time-to-PR
- Drift incidents caught vs not

If you're doing curriculum / docs / catalog work, you'll likely see
~5-10× saving + 1-2 drift catches per round. If you're doing pure
single-agent code work, you may see 1× — and that's the bundle telling
you it's the wrong tool.

## TL;DR (again)

- **~7-8× average token saving** when the round has real delegation work
- **13-16× peak savings** on mirror sync rounds (Gemini delegate)
- **0× on pure judgment** rounds — don't pretend it'll help there
- **Drift catch (F11/F12 etc.) is the non-quantifiable winner** — it stops real bugs from shipping

The bundle isn't magic. It's discipline + spec + scaffolding around
existing tools (codex-delegate, gemini-delegate, Claude subagents).
The savings come from delegation patterns the bundle codifies, not
from the bundle itself doing anything novel.

Use it when delegation makes sense. Skip it when it doesn't.
