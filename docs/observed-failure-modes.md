# Observed Failure Modes — what actually breaks when you delegate to Codex / Gemini

> Catalog of real failures encountered while dogfooding the bundle on
> `awesome-agentic-ai-zh` Stage 6 (2026-05-13). Each entry: what
> happened, why, the skill change that addresses it.
>
> This doc is the ground truth of "why does the skill say that thing?"
> — every guard rail traces back to one of these incidents.

---

## F1. Gemini refuses gitignored task files (HIGH frequency, CRITICAL)

**What happened**: Wrote task brief to `.ai/2026/05/13/<task>/brief.md`, invoked

```bash
gemini --yolo -p "Read .ai/2026/05/13/<task>/brief.md and execute..."
```

→ `Error executing tool read_file: File path '.ai/...' is ignored by configured ignore patterns.`

**Root cause**: `.ai/` is in `.gitignore` (convention to keep transient
task files out of commits). Gemini's `read_file` tool honors gitignore
by default and refuses to open ignored paths. Codex doesn't have this
restriction — it's a Gemini-only failure mode.

**Workaround that worked**:

```bash
cat .ai/2026/05/13/<task>/brief.md | gemini --yolo -p \
  "Below is your full task brief via stdin. Execute it. Report PASS/FAIL at end."
```

**Skill change**: `agent-task-splitter` step 6b now documents this
verbatim as the **default** Gemini invocation pattern — not as a
"known issue workaround" tucked in a sidebar.

---

## F2. Gemini drops table structure during translation (HIGH, CRITICAL)

**What happened**: Asked Gemini to mirror-sync zh-TW → en + zh-Hans
for Stage 6. After sync, post-review found a 3-column Tools table
had 4 rows with 5 cells each — Gemini had merged content from a
nearby 5-column Projects table into the wrong table. Manual fix
required removing 4 rows from 2 mirror files.

**Root cause**: Gemini's CJK translation passes are token-by-token;
when translating a markdown table, it sometimes pulls in adjacent
rows from a different table if they're visually similar (e.g., both
start with `| **Bold label**`). The structural boundary is lost.

**Skill change**: `agent-acceptance-gate` preset
`multi-locale-mirror-sync.yml` now checks **column count parity per
table** across locales, not just total H2 count + line count.

---

## F3. Time-sensitive language drift (MEDIUM, HIGH frequency)

**What happened**: Source said `actively maintained (pushed today)`.
Gemini translated literally to `(today 已更新)` and `(pushed today)`.
3 weeks later the docs say "pushed today" while the repo's last
push is 21 days ago.

**Root cause**: No instruction in the task brief about avoiding
time-relative phrasing.

**Skill change**: `agent-task-splitter` task-brief template (step 6b
Gemini) now has explicit `## Banned phrasing` section listing
time-sensitive idioms ("today", "this week", "yesterday", "soon",
"recently") with replacements ("actively maintained", "2025+",
specific year).

---

## F4. Frontier-model fabrication via hallucination chain (CRITICAL, RARE but high impact)

**What happened**: During Stage 6 expansion, drafted "DeepSeek-R2
(2026-03, AIME 2025 79.7%)" — both the model release and the
benchmark number were fabricated. The number 79.7% is R1's actual
AIME 2024 Pass@1 score that the LLM hallucinated as R2's AIME 2025.
Caught only when a 3rd-party reviewer agent searched DeepSeek's
official channels and found R2 doesn't exist.

**Root cause**: When extending frontier-model tables, LLMs project
the existing pattern forward without grounding in primary sources.
A "version + benchmark" claim that sounds plausible passes informal
review.

**Skill change**: `agent-task-splitter` task-brief template for
"frontier model" or "catalog entry" tasks now **requires** a
verification step calling `gh api repos/<org>/<repo>` for repos OR
explicit primary-source URL for model releases. The `agent-acceptance-gate`
preset `fact-check-frontier-models.yml` enforces that every model
claim has a verified primary-source URL.

---

## F5. Star-count / status drift between brief and actual repo state (MEDIUM, recurring)

**What happened**: Wrote catalog entry "mem0 53k stars" based on what
Codex said. Later check via `gh api repos/mem0ai/mem0` returned
55.6k. Off by 5% — within human tolerance for a "popularity" claim,
but the brief had no verification step, so a 10× error wouldn't
have been caught.

**Root cause**: LLMs cite remembered numbers without re-checking.
Numbers go stale within weeks for active repos.

**Skill change**: `agent-task-splitter` catalog-entry workflow now
includes a "live verification" step:

```bash
gh api repos/<org>/<repo> --jq '{stars: .stargazers_count, license: .license.spdx_id, pushed: .pushed_at}'
```

Result must be cited in the task's `result.md` summary. The
acceptance preset `catalog-entry-add.yml` greps for this output
shape in the summary.

---

## F6. Codex over-tabularizes when asked to "expand" content (MEDIUM, HIGH frequency)

**What happened**: User asked Codex to "expand Stage 6 with more
projects." Codex added 7 more comparison tables, totalling 30+
encyclopedic rows. User pushed back: "we're supposed to teach
concepts + share resources, not write Wikipedia." Required a full
restructure pass.

**Root cause**: Codex's default mode for "expand" + "list" prompts is
to produce comprehensive tables. Pedagogical narrative requires
explicit prompt guidance.

**Skill change**: `agent-task-splitter` task-brief template now
distinguishes **prose-first** vs **table-first** tasks. For
pedagogical content (curriculum, tutorial, explainer), task brief
includes:

```
## Format guidance
- Prefer prose paragraphs over tables.
- A table is justified ONLY if: (a) the data is genuinely comparative
  (≥ 3 attributes per row), AND (b) the reader will use it as a
  decision tool, not as an inventory.
- "Catalog of N variants of X" is an anti-pattern. Replace with prose
  describing 2-3 axes + a collapsible <details> for the long tail.
```

---

## F7. Slug drift across plan.yml ↔ task files ↔ result files (MEDIUM, recurring)

**What happened**: `plan.yml` had `slug: define-auth-contract`. Gemini's
generated task file used `slug: auth-contract-definition`. The reconciler
auto-discovery couldn't find the result.

**Root cause**: When the task brief is in natural language ("define
the auth contract"), agents sometimes regenerate the slug from the
description instead of copying it from `plan.yml`. Slugs are an
internal coordination key — they MUST be verbatim.

**Skill change**: Already partially documented in
`docs/negative-example-gemini-drift.md`. Strengthened with:

- `agent-task-splitter` step 6 now puts the slug in a `# VERBATIM` block
  at the top of every task file
- `agent-output-reconciler` step 2.5 cross-checks slugs and FAILS
  fast (not WARN) on mismatch

---

## F8. Stage 6's 707-line single-file refactor → context bloat in main session (HIGH)

**What happened**: Single mirror-sync round produced 1097-insertion /
873-deletion diff across 3 files. Main session held all 3 files in
context simultaneously to verify. Felt context pressure halfway
through.

**Root cause**: Acceptance verification by hand requires reading the
diff. Main session can't read 2100+ lines without losing earlier
context.

**Skill change**: This is exactly the case for
`agent-acceptance-gate` subagent review pattern (added in v0.2.0).
Strengthened: the preset `multi-locale-mirror-sync.yml` now
**mandates** subagent delegation for diffs > 500 lines.

---

## F9. Cascading review rounds (MEDIUM, expensive)

**What happened**: Stage 6 had 3 separate review rounds:
- Round 1 (after restructure): found 5 issues
- Round 2 (after polish): found 1 typo
- Round 3 (post-curation): found 5 more issues including 2 CRITICAL

Each round cost ~2 minutes of subagent time + main-session
integration overhead.

**Root cause**: No "self-review" gate before declaring a delegation
complete. Each delegation result was reviewed only AFTER commit.

**Skill change**: Task-brief template now includes an explicit
"Self-review checklist" step: agent must list 3 specific things it
verified before returning the result. The `result.json` schema gains
an optional `self_review_passed` boolean field; the gate flags it as
soft warning if missing.

---

## F10. Background task notification handling (LOW)

**What happened**: Scheduled a 270s wakeup for a Gemini sync that
actually finished in ~90 seconds. Wakeup fired stale.

**Root cause**: Used `ScheduleWakeup` when `run_in_background` +
auto-notification would have sufficed.

**Skill change**: `agent-task-splitter` output (final message
format) now reminds: "Use `run_in_background` + wait for notification.
Do NOT poll. Do NOT schedule wakeup unless task is truly idle for
>10 minutes."

---

## F11. Codex over-applies sweep rules to meta-documentation tables (CRITICAL, recurring)

**What happened**: Round 2 of 2026-05-14 plain-language refactor. Brief said
"sweep `「默認」` → `「預設」` across zh-TW canonical files (skip code
blocks)". Codex applied the sweep correctly to prose **but also rewrote
the contrast table row in `resources/style-guide.md`**:

Before: `| 默認 | 預設 |` (this row literally documents the convention)
After: `| 簡體慣用詞（表示預設） | 預設 |` (replaced the documenting term)

The contrast table's whole purpose is to document zh-Hans → zh-TW mappings;
removing the literal term destroys the documentation.

**Root cause**: Codex applies sweep rules at character level without
recognizing that some occurrences are **meta-references to the rule itself**.
A documentation table that contains the term being swept is a meta-level
reference, not a content-level occurrence.

**Skill change**: `agent-task-splitter` step 6d (Task-shape guidance) now
has explicit rule:

> **Skip meta-documentation tables**: do NOT replace term X with term Y
> in any row that literally documents the X→Y mapping. This includes
> style guides, glossary contrast tables, conversion tables, and any
> convention reference. The literal term must remain to document the rule.

Also: `agent-acceptance-gate` `multi-locale-mirror-sync.yml` preset adds
exemption for paths under `resources/style-guide*.md`.

---

## F12. Codex injects unrequested attribution / metadata lines (HIGH, observed once)

**What happened**: Same Round 2 session. T4 brief asked Codex to add
inline glosses for jargon terms (`context fragmentation`, `frontmatter`,
etc.) on Stage 6/7 zh-TW canonical files. Codex did this correctly **but also
inserted a new line in `stages/02-prompt-engineering.zh-Hans.md`**:

```
> Attributions: Karpathy, Simon Willison, Addy Osmani
```

Not requested. Worse, in the en mirror Codex **replaced** the greeting
paragraph with this attribution line, corrupting the file.

**Root cause**: Codex sometimes interprets "add gloss explaining X" as
license to add **any** metadata about X, including authorship / source
attribution that the brief never asked for.

**Skill change**: `agent-task-splitter` step 6d adds explicit rule:

> **No metadata injection**: do NOT add lines like `Attributions: <names>`,
> `Source: <link>`, `Citations: <list>`, or any metadata beyond what the
> brief explicitly requested. Glosses are inline explanations, not
> source attributions. If attribution is needed, the brief will say so.

Also: `agent-acceptance-gate` `multi-locale-mirror-sync.yml` preset adds
check for unrequested `Attribution`/`Source`/`Credits` line insertions.

---

## Summary — patterns that emerged

1. **Gemini-specific failures** dominate over Codex-specific failures.
   Gemini honors gitignore, drops table structure, drifts on slugs.
   Codex over-tabularizes but is more structurally faithful.

2. **Time-sensitive language** is a silent footgun — passes review,
   bites you weeks later.

3. **Fact-check via primary source** is non-negotiable for any
   "frontier" or "popularity" claim. Trust nothing the LLM remembered
   about external repos / model releases.

4. **Slug discipline** matters more than it looks — a 1-character
   drift breaks the entire reconciliation pipeline.

5. **Subagent delegation pays off** for diffs > 500 lines, debate
   transcripts > 4 KB, and any acceptance check that requires reading
   multiple result files.

When in doubt: assume the future-version of yourself reading the
result has no memory of the task. The result must stand alone.
