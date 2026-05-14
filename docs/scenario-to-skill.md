# Scenario → Skill mapping — which delegation skill to invoke when

> **Companion to [`when-to-invoke.md`](when-to-invoke.md)**. That doc covers **trigger conditions** for the orchestration skills (splitter / gate / reconciler). This doc covers **per-task scenarios** for the 3 delegation skills (`codex-delegate` / `gemini-delegate` / `coding-agent`).

## The 3 delegation skills + their roles

| Skill | Role | What it adds on top of raw CLI |
|---|---|---|
| **`coding-agent`** (local skill, e.g. `~/.agents/skills/coding-agent/`) | Generic PTY-aware Bash spawn primitive | PTY mode (required for codex / claude / opencode / pi — without it agents hang or get broken output) |
| **[`codex-delegate`](https://github.com/WenyuChiou/codex-delegate)** | Codex-specific delegation wrapper | (a) stdin closure (codex hangs without `</dev/null`)<br>(b) `.result.json` structured output (`status` / `risks` / `files_changed` / `tests_run`)<br>(c) brief template (`.ai/codex_task_<name>.md` format)<br>(d) routing rules (mechanical → codex) |
| **[`gemini-delegate`](https://github.com/WenyuChiou/gemini-delegate-skill)** | Gemini-specific delegation wrapper | (a) F1 workaround — stdin pipe instead of `-p` flag (gemini honors gitignore and skips `.ai/`)<br>(b) `--approval-mode yolo` enforcement<br>(c) No `-C` flag (gemini doesn't support it)<br>(d) CJK / 中文 routing |

→ **They are NOT redundant**: each handles a tool-specific footgun that the others don't.

---

## Scenario table — which skill for which task

### `codex-delegate` scenarios — "mechanical + multi-file + clear pattern"

| Scenario | Concrete example |
|---|---|
| **Multi-locale mirror sync** | zh-TW canonical → zh-Hans + en, 3 locale × 1 stage = 3 files (Stage 6 / Stage 7.5 / Track A3 patterns) |
| **Style sweep across files** | `「默認」→「預設」` × 50 files; § strip × 100 files |
| **Catalog star count refresh** | After `refresh-stars.py --apply`, batch update README + stages/ tables |
| **New section quick mirror** | You write a new playbook section in zh-TW, codex translates to zh-Hans + en |
| **Test scaffold generation** | Write 27 example folders' README + test stubs |
| **Prompt rewrite (v1 → v2)** | 9 image-gen prompts updated to v2 (icons + bilingual + no-source rule) |
| **Type hint / docstring batch add** | Annotate Python files en masse |
| **Code migration with clear pattern** | Same analysis pattern applied to 3 different seeds / configs |

**Don't use codex-delegate for**:
- Architecture / framework decisions
- Mental model rewrites (Claude's job — needs conversation context)
- Security-sensitive code

---

### `gemini-delegate` scenarios — "long context + CJK + second opinion"

| Scenario | Concrete example |
|---|---|
| **Long Chinese draft** | MoodRing daily / 盤後日報 / 週報 (Chinese narrative beyond Claude's comfort zone) |
| **Multi-paper synthesis** | research-hub cluster of 5-10 papers → unified brief (NotebookLM-style) |
| **Long paper translation + terminology alignment** | Academic paper EN → 中文 keeping the paper's existing terminology (paper memory + style overrides) |
| **Cross-document terminology audit** | One repo's docs/ + README + stages/ = 200k token, run banned-word audit |
| **Second-opinion review** | Claude wrote a paper abstract; Gemini runs "is this clear" adversarial review |
| **Bilingual translation preserving voice** | Convert 繁中 to 简中 while keeping **author's tone** (mechanical conversion → codex; voice-preserving → gemini) |
| **Reading-list / brief from long primary sources** | Pull 1-line summaries from a 100k-token text |

**Don't use gemini-delegate for**:
- Bulk code generation (use codex)
- Security-sensitive tasks (use Claude)
- Final acceptance / commit decisions (use Claude)

---

### `coding-agent` scenarios — "generic agent spawn"

| Scenario | Concrete example |
|---|---|
| **Background long-running CLI** | Wait 60s for a build to complete; watch deploy log scroll |
| **Run non-codex/gemini agent** | OpenCode / Pi / Aider with same PTY-aware wrapper pattern |
| **PTY mode critical** | Interactive terminal apps where colour codes / progress bars matter |
| **Process control** | Start / check / kill an agent (not fire-and-forget) |

**Important**: if the task IS for codex or gemini specifically, use `codex-delegate` / `gemini-delegate` instead — they use `coding-agent` internally as the spawn primitive AND add the tool-specific value (brief + result contract + footgun handling).

---

## Composition with `agent-collab-skills`

When a round has **≥ 2 parallel delegates**, the orchestration is:

```
[agent-task-splitter]
  Writes briefs:
    .ai/codex_task_001_<slug>.md
    .ai/gemini_task_001_<slug>.md
  Writes orchestration plan:
    .coord/plan.yml
        ↓
┌─────────────────────────────┬─────────────────────────────┐
│ [codex-delegate]            │ [gemini-delegate]           │
│   model: gpt-5.5            │   stdin pipe + yolo         │
│   stdin closure             │   no -C flag                │
│   writes result.json        │   writes result.json        │
└──────────┬──────────────────┴───────────┬─────────────────┘
           ▼                              ▼
    .ai/codex_log_001.txt.result.json    .ai/gemini_log_001.txt.result.json
           │                              │
           └──────────────┬───────────────┘
                          ▼
            [agent-output-reconciler]
              Reads both result.json
              Computes diff / merge
              Writes .coord/reconciliation_NNN.md
                          ↓
            [agent-acceptance-gate]
              --preset=multi-locale-mirror-sync
              --stem=<file-stem>
              --brief-file=<original-brief>
                          ↓
            PASS → [Agent(subagent_type="code-reviewer")] (mandatory)
                          ↓
                       Commit
```

→ Each delegate skill runs ONE tool. The orchestration skills coordinate ≥ 2 of them.

---

## Anti-patterns (F-N case studies)

| Anti-pattern | Maps to | Why it fails |
|---|---|---|
| Raw `Bash("codex exec ...")` for production task | Bypasses codex-delegate | Loses stdin closure, result.json contract, brief template — re-inventing every round |
| `gemini -p "..."` with prompt as positional arg | F1 incident | Gemini CLI ignores `.ai/` (gitignored), task silently fails |
| 2 parallel codex without `agent-task-splitter` | F11 | Cross-agent drift, one sweeps into another's scope (F12 is a separate defect — unrequested attribution injection — not parallelism-related) |
| Multi-locale commit without `multi-locale-mirror-sync` preset | F14 | Mirror divergence ships, anchor-only check misses content drift |
| Skipping `code-reviewer` subagent after multi-file commit | "Will review later" → never reviewed | Production drift accumulates |
| Using gpt-5.4 when 5.5 is available | Sub-optimal model | Minor but consistent quality hit; bumped 2026-05-14 default |

---

## How to invoke (canonical patterns)

```python
# Single codex run (replaces raw codex exec)
Skill("codex-delegate",
      args="brief=.ai/codex_task_001_translate.md model=gpt-5.5")

# Single gemini run (replaces raw gemini --yolo)
Skill("gemini-delegate",
      args="brief=.ai/gemini_task_001_chinese-report.md")

# Generic non-codex/gemini agent
Skill("coding-agent",
      args="pty:true command:'opencode run \"refactor foo.py\"'")

# Parallel delegation (mandatory: split first)
Skill("agent-collab-workspace:agent-task-splitter", args="round=N tasks=...")
# → Then run codex-delegate / gemini-delegate per task brief
```

---

## See also

- [`when-to-invoke.md`](when-to-invoke.md) — trigger rules for orchestration skills (splitter / gate / reconciler / debate / shared-memory / PAR)
- [`observed-failure-modes.md`](observed-failure-modes.md) — F1 – F14 case studies behind these rules
- [`measured-benefits.md`](measured-benefits.md) — token measurements + retrospective preset test
