# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [0.4.0] - 2026-08-31

### Added

- Public `agent-collab-harness` Python distribution and `agent-collab` CLI for
  strict policy validation, checkpoint validation, policy evaluation, and
  environment diagnostics.
- Versioned `TaskCheckpoint`, `PolicyDecision`, and policy schemas with
  deterministic boundary, retry, checkpoint, concurrency, and context checks.
- Compatibility normalization for the existing portable-harness v1 canonical
  policy without duplicating or rewriting its budget values.
- Action-hash-bound HMAC authorization for human decisions and limit overrides,
  including proof that an override was approved before the original limit.
- Provider-neutral roles: primary agent, delegated executor, reviewer, and
  synthesizer.

### Changed

- Seven skills now share one canonical machine-readable policy instead of
  copying numeric defaults into prose.
- Coordination directories are scratch by default; only explicit checkpoint,
  shipping, or acceptance evidence is promoted.
- Shared memory is proposal-only. Approved changes append immutable events and
  never rewrite older questions or decisions; approval hashes cover an
  immutable action payload rather than mutable decision metadata.
- Active manifests, samples, install instructions, tests, and skill contracts
  no longer route to archived providers.

### Compatibility

- Historical provider-specific plans and result paths remain parse-only inputs.
- Migration and rollback guidance is documented in `docs/migration-0.4.md`.
- Configured but unreadable policy fails closed; no silent retry, model switch,
  or context discard is permitted.

## [0.3.1] - 2026-07-11

### Changed — Antigravity lane promoted (evidence row only)

- `agent-task-splitter`: the reroute-table Antigravity row updated from
  "capability existence only, not a default lane" to PROMOTED — the
  pre-registered k=5 reliability gate passed 5/5 on 2026-07-11 (fresh
  sandbox per trial; planted decoy untouched; planted judgment question
  escalated verbatim, not acted on; zero git ops; deterministic grader).
  Recorded as `mc12_antigravity_k5_reliability` in fable-method-harness
  alongside `mc11`. The lane is routable for bounded mechanical subtasks
  like `codex` / `claude-cheap`; cheap-tier guardrails unchanged (never
  reviews, completion verdicts, governance, or anything ambiguous). No
  behavior change to any script — documentation/evidence row only.

## [0.3.0] - 2026-07-10

### Changed — Gemini lane deprecated (fails closed); cheap-Claude lane added

- `agent-task-splitter`: the `gemini` routing lane is DEPRECATED and the
  splitter must never emit it (the lane fails closed since 2026-06-18).
  A reroute table maps old gemini use-cases: CJK/bilingual judgment ->
  `claude` inline; bulk mechanical CJK -> `codex`; long-context synthesis
  -> `claude` or `claude-cheap`; reviews -> `claude` (honesty-critical,
  never cheap). `agent: gemini` stays PARSE-ONLY for reconciling
  historical rounds; §6b is retained as a bannered legacy reference and
  its live invocation guidance was removed (recoverable from git history).
- NEW `claude-cheap` lane (`agent: claude-cheap`, optional `model:` field,
  default haiku): bounded mechanical subtasks run as pinned-model
  subagents via the Agent tool with a codex-shaped brief file
  (`.ai/claude_task_<NNN>_<slug>.md`). Guardrails baked in: the strong
  orchestrator classifies (never the cheap lane), no honesty-critical
  output on the cheap tier (measured 0/5 on subtle-honesty tasks), every
  return re-verified. Measured basis: the cost-router benchmark in
  fable-method-harness `benchmarks/route_cost_ab/` (routed = all-strong
  quality/stability at ~0.4x cost, k=3 blind router).
- Examples (SKILL.md worked example, examples/plan.yml.sample T3,
  docs/example-walkthrough.md), the routing decision tree in
  references/task_splitter_heuristics.md, reconciler globs, the CLAUDE.md
  template snippet, plugin/marketplace descriptions, and re-plan guidance
  all updated to the new lane set.
- SCOPE NOTE: this release fixes the EMITTER (the splitter is the only
  skill that creates new gemini dispatches). Sibling skills
  (output-reconciler, acceptance-gate, debate, shared-memory,
  context-budget) and README still mention the gemini lane — mostly as
  readers of historical artifacts, which stays valid; a follow-up sweep
  will align their prose. Tracked, not silently deferred.
- **`agent-task-splitter` frontmatter description disambiguates from
  `research-hub-multi-ai`.** Both skills previously claimed the same
  trigger surface ("split a goal across Claude / Codex / Gemini",
  "plan a multi-agent run", "Codex + Gemini") which caused silent
  routing overlap surfaced by the
  `WenyuChiou/ai-research-skills` Task #27 verification dogfood walk.
  This change reframes `agent-task-splitter` as the **generic** task
  splitter (writes `.coord/plan.yml`) and explicitly points
  research-domain prompts that touch `.research/` / `.paper/` /
  Zotero / Obsidian / NotebookLM ingest pipelines at
  `research-hub-multi-ai` (writes `.coord/multi_ai_plan.md`,
  research-hub-aware reconciliation). The sibling change on the
  research-hub side shipped in `WenyuChiou/research-hub` PR #59
  (squash-merged 2026-05-20 at `b4e0dd1`) so both skills now
  describe their boundary the same way. Closes Phase 7 Item #5b.
  (Merged from main pre-release; ships with 0.3.0.)


## [0.2.3] - 2026-05-14 (later same day)

### Added — F13 + F14 from Phase D counter-example dogfood

After Phase D (`awesome-agentic-ai-zh` cross-stage terminology
cleanup) deliberately skipped the mandatory `multi-locale-mirror-sync`
preset, this release codifies two new failure modes and the
corresponding skill changes.

- **F13 — Gemini "liar mode"** (HIGH, recurring). Gemini-cli `--yolo`
  claimed success in `result.md` without modifying any target files.
  Detection: `post_brief_mtime_check` check verifies target file mtime is
  after brief file mtime. Routing rule: default to Codex for mirror
  sync, not Gemini.
- **F14 — Skipping mandatory presets** (META-FAILURE). Phase D
  touched 49 files × 3 locales (textbook trigger) but used an
  ad-hoc `code-reviewer` subagent instead of the preset. Retrospective
  preset run on the Phase D commit showed the preset would have
  passed 12 of 13 checks; the missing check (cross-document title
  reference parity) is now added as `cross_document_link_text_parity`.
- `agent-acceptance-gate`:
  - New §"Preset is mandatory when trigger fires" section in
    `SKILL.md` with anti-patterns + enforcement options.
  - `presets/multi-locale-mirror-sync.yml` adds
    `cross_document_link_text_parity` (soft warn) and
    `post_brief_mtime_check` (fail) checks.
- `docs/observed-failure-modes.md` adds F13 + F14 entries (now F1-F14).
- `docs/measured-benefits.md` adds "Phase D counter-example dogfood"
  section — ~3× saving on this specific shape (lower than the 6-7×
  headline because title-edit work is so trivial that even inline
  is cheap), but bundled with mechanical drift detection that the
  inline approach lacked.

### Backlog (planned for v0.3.0)

- Pre-commit hook recipe → installable as a marketplace add-on
  (currently documented only).
- `cross_document_link_text_parity` is soft-warn now; promote to
  fail once false-positive rate is measured.

## [0.2.2] - 2026-05-14

### Added — 7th skill + W1-W5 hardening from real dogfood

After the 2026-05-13 R2 dogfood discovered F11 (over-applied sweep
to meta-doc tables) and F12 (unrequested attribution injection), and
the 2026-05-14 6-round dogfood validated the bundle's ~6-7× saving,
this release codifies the hardening:

- New 7th skill `agent-plan-act-reflect` for single-agent iterative
  self-correction (different from `agent-debate`'s 2-agent adversarial
  pattern). Plan → Act → Reflect → Revise loop with bounded iterations.
- `docs/observed-failure-modes.md` adds F11 + F12 entries (now F1-F12).
- `agent-task-splitter`:
  - Step 6 adds REQUIRED "Pre-task scope confirmation" block — delegate
    must echo back scope as first action (W1).
  - Step 6d adds explicit F11 + F12 drift guards in every brief.
- `agent-acceptance-gate`:
  - New §6.6 "Scope diff check" — compares `git diff --name-only`
    against `files_in_scope`, FAIL on out-of-scope edits (W1 enforcement).
  - Mandatory preset triggers now apply to F11 + F12 patterns.
- `agent-output-reconciler`:
  - New §2.6 "Promise vs delivery contract check" — verifies sequential
    hand-off chains (research → write → verify) deliver on upstream
    promises (W2).
- `agent-context-budget`:
  - New `default_max_cost_usd` + `total_round_max_cost_usd` fields in
    `context_policy`. Per-task `budget.max_cost_usd` overrides (W3).
- `agent-acceptance-gate/presets/multi-locale-mirror-sync.yml`:
  - `time_sensitive_phrases` adds `exempt_when_inside` for dialogue
    quotes (R5 false-positive fix) + `soft_patterns` for ambiguous cases.
  - New `unrequested_attribution_lines` check (F12 regression guard).
  - New `meta_doc_table_preservation` check (F11 regression guard).

### Changed

- Plugin version 0.2.1 → 0.2.2 across `plugin.json` + `marketplace.json`.

### Validated

- 6-round dogfood on `awesome-agentic-ai-zh` plain-language refactor
  (2026-05-14) — see `docs/measured-benefits.md` for ~6-7× saving
  documentation.

## [0.2.1] - 2026-05-13

### Added — guardrails distilled from real dogfooding incidents

After v0.2.0 ship, did a retrospective on the actual failures
encountered during Codex + Gemini work on `awesome-agentic-ai-zh`
Stage 6 (2026-05-13). 10 distinct failure modes captured:

- `docs/observed-failure-modes.md` — F1–F10 catalog, ground truth
  for "why does the skill say that thing?"
- `skills/agent-acceptance-gate/presets/multi-locale-mirror-sync.yml`
  — codifies the 5+ checks needed after zh-TW → en + zh-Hans sync.
- `skills/agent-acceptance-gate/presets/catalog-entry-add.yml` —
  live-API verification for `gh api` star count + license claims.
- `skills/agent-acceptance-gate/presets/fact-check-frontier-models.yml`
  — deny-list of fabricated model names + benchmark citation pair
  enforcement. Pre-empts the DeepSeek-R2 hallucination chain (F4).

### Changed — skill prompts hardened from incident learnings

- `agent-task-splitter`:
  - Gemini stdin invocation (`cat task.md | gemini --yolo -p`) is
    now the DEFAULT pattern, not a sidebar workaround. (F1)
  - New step 6d "Task-shape guidance" classifies pedagogical /
    reference / catalog / migration / translation tasks and gives
    format guidance per shape — prevents F6 over-tabularization.
  - New step 6e "Fact-verification step" mandates `gh api` or
    primary-source URL for any external claim. (F4, F5)
  - Task-brief template adds "Self-review checklist" (slug verbatim,
    column counts unchanged, no time-relative phrases). (F2, F3, F7)
  - Task-brief template adds "Banned phrasing" section listing
    time-relative idioms with replacements.

- `agent-output-reconciler`:
  - New §2.4 "Multi-locale lockstep check" — line/H2/column-count
    parity across locale variants. (F2, F8)

- `agent-acceptance-gate`:
  - New "Presets" section documents the 3 preset YAMLs + their
    mandatory invocation triggers.

### Tests

- 3 new tests covering observed-failure-modes doc + preset YAMLs
  + SKILL.md cross-references.
- `python -m pytest`: **13 passed, 0 warnings** (was 10).

## [0.2.0] - 2026-05-13
### Added
- `agent-context-budget` skill for bounded multi-agent handoffs,
  context policies, session primers, and optional agentmemory recall.
- `context_policy` sample schema in `examples/plan.yml.sample`.
- Documentation for optional agentmemory integration and context
  pressure scenarios.
- `examples/codex_log_001_*.txt.result.json.sample` showing the
  double-extension `result.json` convention emitted by codex-delegate.
- All 6 SKILL.md files now include a "Subagent review" section
  encouraging review delegation to keep main session context clean.

### Changed
- Skill descriptions now start with trigger-only `Use when...`
  frontmatter.
- Reconciliation sample now reflects the auth plan, bounded summaries,
  correct agent counts, and path-only log handling.
- Existing skills now treat raw logs, long memory, and unbounded
  summaries as context-contract risks.
- `agent-acceptance-gate` now reads `.coord/context_<NNN>.md`
  (produced by `agent-context-budget`) for per-task budget enforcement,
  in addition to plan-wide `context_policy`.
- `agent-output-reconciler` now optionally consults `.coord/context_<NNN>.md`
  to flag per-task budget violations at finer granularity.
- `agent-debate` now declares hard caps (per-turn ≤ 400 words,
  synthesis ≤ 250 words, total ≤ 8 KB) which `agent-acceptance-gate`
  enforces when debate is wired into a plan round.
- `agent-task-splitter` invocation examples now use the `-o` flag
  for structured result output, and bare `> file.log 2>&1` is
  replaced with capped `| head -c 10485760 > log` (prevents the
  multi-GB runaway log incident pattern).

## [0.1.2] - 2026-04-28
### Fixed
- `agent-task-splitter` step 6a / step 7 / README known-issues: document `< /dev/null` stdin redirect for direct `codex exec` invocations. codex-cli ≥ 0.121.0 hangs at "Reading additional input from stdin..." without it. (Found in v0.1.1 verify dogfood; only surfaced when invoking codex directly, not through the `run_codex.sh` wrapper.)
- `agent-task-splitter` step 6b: gemini invocation example now also includes `< /dev/null`. Same root cause as codex.
- README known-issues: third bullet covers the codex/gemini stdin pattern explicitly.

## [0.1.1] - 2026-04-28
### Fixed
- `agent-task-splitter`: result-summary path included in `files_in_scope` for generated task files (was missing, causing codex to flag self-conflicts at run time).
- `agent-task-splitter`: codex / gemini / claude task-file formats now split into separate steps 6a, 6b, 6c (previously one template; gemini drifted because of format mismatch).
- `agent-task-splitter`: new step 0 verifies the working directory is the project root before writing `.coord/` (previously could silently target the wrong worktree).
- `agent-task-splitter`: new step 8 documents the re-plan workflow when an agent gets reassigned mid-round (avoids orphan task files).
- `agent-output-reconciler`: new step 2.5 checks task ID / slug / agent-assignment consistency across plan.yml and per-task result.md (catches gemini hallucination drift).
- README: known-issues section documents the `gemini-cli` gitignore conflict and the inline-prompt workaround.

## [0.1.0] - 2026-04-28
### Added
- Initial release of the `agent-collab-workspace` marketplace bundle plugin for multi-agent collaboration workflows.
- Five packaged skills: `agent-task-splitter`, `agent-output-reconciler`, `agent-debate`, `agent-shared-memory`, and `agent-acceptance-gate`.
- The `.coord/` directory convention for shared plans, reconciliation notes, and acceptance artifacts.
- Three dogfood sample artifacts in `examples/`: `plan.yml.sample`, `reconciliation_001.md.sample`, and `acceptance_001.md.sample` (commit `71eb9fa`).
- `docs/example-walkthrough.md` narrating the dogfood end-to-end run.
- Install scripts, CI workflow, pytest tests, issue / PR templates.

### Changed
- Cross-links added in `codex-delegate` and `gemini-delegate-skill` SKILL.md so they reference `.coord/plan.yml` for round context when a multi-agent run is active.
