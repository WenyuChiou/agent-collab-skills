# Measured Benefits — what `agent-collab-skills` actually saves

> Honest dogfood report based on 1 production session (2026-05-14,
> awesome-agentic-ai-zh plain-language refactor, **6 rounds × 9 tasks**).
> Main-session token counts are real byte-proxy measurements;
> control-token column is a constructed baseline estimate (see methodology).

## TL;DR

**Realistic saving: ~6-7× on main-session token cost** across a 6-round mixed-workload session. **~1× saving** on pure-judgment rounds (skills don't help there). **Up to 17-22×** on the sweet-spot round (multi-file mirror sync via Gemini delegate). **Drift catch** (F11/F12 incidents) is the non-quantifiable bonus on top — the review step that catches drift IS already paid for in the main-session token cost, so it's not "free", it's "the right use of the budget".

If you're evaluating whether to install this bundle, the calculus is:

- **You write Chinese curriculum / docs across multiple locales** → install (R4 = mirror sync round, peak 17-22× saving)
- **You delegate to Codex / Gemini regularly and review their output** → install (R2 sweet spot, F11/F12 drift catch alone justifies it)
- **You only work solo on small judgment-heavy tasks** → don't bother (R1/R3 = no saving)

---

## Measurement methodology

- Token proxy: file bytes / 3 chars per token (mixed zh-TW + EN)
- **"Main session tokens"** = bytes read into Claude's main context window — **measured** from actual file sizes touched
- **"Control tokens"** = hypothetical estimate of cost if Claude did everything inline (no delegate) — **estimated**, not measured, because we didn't run the control condition
- Subagent / Codex / Gemini token consumption is **separate** — not in main session count
- The headline "~7-8× saving" derives from main (measured) ÷ control (estimated). Treat as a directional figure, not a precise multiplier.

## Round-by-round breakdown (6 rounds)

| Round | Task type | Main tokens | Control tokens | Saving | What the skill bought |
|---|---|---|---|---|---|
| R1 | Term definitions (Claude inline, no delegate) | ~6.5k | ~6.5k | **1×** | Nothing — pure Claude work. Skills had no role to play. |
| R2 | Mechanical sweeps + jargon glosses (Codex × 2 parallel) | ~5k | ~37k | **~7×** | Codex read 80 KB of stages NOT in main session; main only read 12 KB of diff for review. **Also caught 4 drift files** (F11/F12) that would have shipped broken. |
| R3 | Pedagogical rewrites (Claude inline, no delegate) | ~3k | ~6k | **~1× (effectively 0 skill contribution)** | Pure Claude work — skills had no direct role. The lower control estimate vs naive baseline came from carrying over prior audit findings; that's discipline value, not skill value. |
| R4 | Mirror sync (Gemini delegate, 8 files) | ~4k | ~70-90k | **~17-22×** | Gemini did 200 KB read + 50 KB write entirely outside main session; main only read its ≤ 250-word `result.md` summary. **This is the bundle's sweet spot.** |
| R5 | Acceptance gate (subagent verdict) | ~2k | ~10k | **~5×** | Subagent ran 5+ grep checks + verdict synthesis; main only read 600-word structured PASS/FAIL report instead of running shell verification inline. |
| R6 | GitHub triage (gh CLI direct, no delegate) | ~0.5k | ~0.5k | **1×** | Single command via gh CLI — skills not relevant here. |
| **TOTAL** | (6 rounds combined) | **~21k** | **~130-150k** | **~6-7×** | |

(Earlier "~7-8×" headline rounded high; correct band is ~6-7× once R3
is properly attributed as skill-neutral.)

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
is in Claude's judgment, not throughput. **You'll see ~1× saving** on
these rounds (skills had no role). That's fine — that's not what the
skills are for. (R1 and R3 above are both effectively 1×; R3's table
row shows a tiny carryover-audit benefit but that's discipline, not
delegation.)

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

These don't show up directly as additional token-cost saving — but they're the strongest reason to use the bundle:

### Drift catch (F1-F12)

This session caught 12 distinct agent failure modes:
- F1-F10 captured in `docs/observed-failure-modes.md` from prior sessions
- F11 (over-applied meta-doc sweep) + F12 (unrequested attributions) discovered THIS session and will be codified into v0.2.2

Each F# is a real bug that would have shipped without the review-and-reject pattern. **The review-step token cost is already baked into the main-session number** (e.g., R2's ~5k tokens include the review pass that caught the 4 drift files). So drift catch isn't "free on top" — it's "the highest-leverage use of the same token budget you'd spend anyway". Even at 1× token saving, the review pattern alone would justify the bundle for any team that delegates to Codex/Gemini regularly.

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

## Phase D dogfood (2026-05-14, Counter-Example: skipping mandatory preset)

A 2nd production session (after the 6-round Phase B above) deliberately
**did not** invoke the skills, to measure what gets lost. Honest report.

**The work**: cross-stage terminology cleanup on `awesome-agentic-ai-zh` —
49 files × 3 locale variants × 1,220 line diff. Textbook trigger for
`multi-locale-mirror-sync` preset. The supervising Claude session
**skipped the mandatory invocation** and used direct inline Edit calls
plus one `code-reviewer` subagent at the end.

### What the inline approach cost

| Step | Tokens (estimated proxy) | Notes |
|---|---|---|
| Read 30+ files to inspect | ~25k | Each title line check = 1 read + 1 edit |
| Apply 25 title edits inline | ~10k | 25 Edit calls × ~400 tokens each |
| Final code-reviewer subagent | ~12k | Comprehensive 5-category review |
| Drift fix (README Track A) | ~3k | Reviewer caught it, supervising session patched |
| **Total main-session** | **~50k** | |

### What `agent-task-splitter` + Codex delegate would have cost

| Step | Tokens (estimated proxy) | Notes |
|---|---|---|
| Splitter writes 1 plan + 1 Codex brief | ~6k | Reusable, version-controlled |
| Codex executes all 25 title edits | **0 (off main session)** | Codex reads + writes outside |
| `multi-locale-mirror-sync` preset verification | ~8k | Subagent runs structured checks |
| Supervising session reads PASS/FAIL | ~2k | Structured report only |
| **Total main-session** | **~16k** | |

**Ratio: ~3× saving** — smaller than R2/R4 (which were 7× / 17-22×)
because most title-edit work is so trivial that even inline is cheap.
But the **3× saving comes bundled with mechanical drift detection**
that the inline approach lacked entirely.

### The drift that was missed (and how it would have been caught)

Inline approach + reviewer-subagent caught the **README Track A title
drift** post-commit. Retrospective `multi-locale-mirror-sync` preset
run against the Phase D commit:

| Check | Result | Cost equivalent |
|---|---|---|
| file_existence + line_parity + h2_parity | PASS | 5 sec, ~1k tokens |
| banned_phrases + simplified purity | PASS | 5 sec, ~1k tokens |
| anchor_strict | PASS | 1 sec |
| diff_size_subagent_threshold (>500) | **FIRES** | mandates subagent review |
| cross_document_link_text_parity (proposed v0.2.3) | **WOULD FIRE** | would have caught README drift |

The first 12 checks passed automatically. Check #13 mandates the same
subagent review that the inline approach added ad-hoc. The proposed
check #14 (added to v0.2.3 backlog from this dogfood) closes the gap
that the human reviewer had to catch manually.

### F14 lesson — process beats spec when skill compliance is policy-only

The preset is documented as **mandatory** in `CLAUDE.md`. Phase D
operator skipped it anyway because the task "felt simple". This is a
META-FAILURE: the skills work, the documentation says use them, the
operator didn't.

Two fixes shipped from this dogfood:

1. New section "Preset is mandatory when trigger fires" added to
   `agent-acceptance-gate/SKILL.md`
2. Pre-commit hook recipe added — mechanical check that mirror-diff
   commits prompt for preset invocation

The pre-commit hook is the actual fix. Documentation alone didn't
hold. See F14 in `observed-failure-modes.md`.

### v0.2.3 retrospective test — `cross_document_link_text_parity` validated against real history

**Test date**: 2026-05-14, same day as v0.2.3 ship.

A standalone Python implementation of the new
`cross_document_link_text_parity` check (see
`.ai/v0.2.3-preset-test/test_cross_document_link_text_parity.py` in
this repo) was run against `awesome-agentic-ai-zh` at commit
`4a60742` — the Phase D commit **before** the README Track A fix.

**What it should catch**: the 3 stale link texts in README.md Track A
table (`CLI Agent 入門 + 選擇` etc.) that point at track files whose H1
titles already moved to the new bilingual format.

**What it actually caught (zh-TW + en + zh-Hans READMEs combined): 23 warnings**, of which:

| Category | Count | Example |
|---|---|---|
| **Real drift the audit knew about** | 3 | README.md Track A: `CLI Agent 入門 + 選擇` vs new `選一個 CLI Agent，開始用它做事（CLI Agent Intro & Selection）` |
| **Real drift the audit DID NOT know about** | 6+ | README.en.md: `LLM Basics` vs en H1 `LLM Fundamentals`; `Memory · RAG · Advanced` vs en H1 `Context Engineering: RAG and Memory`. README.zh-Hans.md: 4 similar stale link texts. |
| False positive — semantic alias (CTA links) | 2 | `從 Stage 0 開始` / `Start at Stage 0` linking to Foundations H1 |
| False positive — partial-match algorithm too strict | ~10 | Link text contains English term inside parens (`Agent Interfaces`) but stripping `Stage N — ` prefix only from H1 misses the intersection |
| **Net real bugs surfaced** | **9+** | |

**Key finding**: the check **works conceptually** — it catches all 3
audit-known cases plus surfaces ≥ 6 bugs the human audit missed.
The matching algorithm needs 2 refinements for production:

1. **Normalize both sides**: strip `Stage N — ` / `AN — ` prefix from
   the link text as well as from the H1, not just from H1
2. **Match on the English term inside parens** as a separate token
   (so `Agent Interfaces` in link text matches H1's
   `Agent 操作介面（Agent Interfaces）：...`)

These refinements are filed as v0.2.4 backlog. For v0.2.3 the check
ships with `severity: warn` (soft fail), which correctly reflects
the algorithm maturity — operators get the signal but the gate does
not block on it.

**Bug list surfaced for downstream fix in `awesome-agentic-ai-zh`**:

- README.en.md L102: `LLM Basics` (stale) → target en H1 `LLM Fundamentals`
- README.en.md L124: `Memory · RAG · Advanced` (stale) → target en H1 `Context Engineering: RAG and Memory`
- README.zh-Hans.md L88: `LLM 入门` (stale) → target zh-Hans H1 `LLM 基础（LLM Basics）`
- README.zh-Hans.md L95: `CLI Agent 入门 + 选择` (stale) → target zh-Hans H1 `选一个 CLI Agent，开始用它做事（CLI Agent Intro & Selection）`
- README.zh-Hans.md L110: `Memory · RAG · 进阶` (stale) → target zh-Hans H1 `上下文管理（Context Engineering）：RAG 与 Memory`
- README.zh-Hans.md L111: `Multi-Agent · 进阶应用` (stale) → target zh-Hans H1 `多 Agent 系统与稳定运作（Multi-Agent & Production）`

These are the cross-language echoes of the original Phase D
Track A drift — the audit caught the zh-TW row but missed the
en + zh-Hans equivalents. The preset would have caught all
language variants at once.

---

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

## Bottom line (no marketing)

- **~6-7× average token saving** across a mixed 6-round workload (not 30× from earlier napkin math)
- **17-22× peak** on the mirror-sync round (Gemini delegate, biggest individual win)
- **~1× on pure judgment** rounds — don't pretend it'll help there
- **Drift catch is the highest-leverage use of the token budget you'd spend anyway** — review-step cost is included, not extra

The bundle isn't magic. It's discipline + spec + scaffolding around
existing tools (codex-delegate, gemini-delegate, Claude subagents).
The savings come from delegation patterns the bundle codifies, not
from the bundle itself doing anything novel.

Use it when delegation makes sense. Skip it when it doesn't.
