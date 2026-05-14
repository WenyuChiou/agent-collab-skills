# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

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
