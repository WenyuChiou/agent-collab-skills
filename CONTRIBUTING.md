# Contributing

This is a single-source marketplace + plugin bundle. Both the
marketplace config (`.claude-plugin/marketplace.json`) and the 5 skills
live in this one repo. Unlike `ai-research-skills` (5 upstream source
repos coordinated via a catalog), here all changes go in one PR.

## Where the change belongs

| Change | File(s) |
|---|---|
| Modify a skill's behavior or prompt | `skills/<name>/SKILL.md` |
| Reference content (templates, schemas, heuristics) | `skills/<name>/references/*.md` |
| Add a new skill to the bundle | `skills/<new-name>/SKILL.md` + bump `metadata.version` in `marketplace.json` and `version` in `.claude-plugin/plugin.json` |
| Marketplace config | `.claude-plugin/marketplace.json` |
| Bundle plugin metadata | `.claude-plugin/plugin.json` |
| End-user install / how-to-use docs | `README.md` |
| Marketplace internals doc | `.claude-plugin/README.md` |
| Test invariants | `tests/test_catalog.py` |

## Interop contract — read before modifying

The 5 skills share a contract. Breaking any part of it can silently
corrupt multi-agent runs. The contract has 3 layers:

### 1. The `.coord/` directory schema

All 5 skills read/write a shared `.coord/` directory at the user's
project root. Files inside:

| File | Owner skill | Format | Lifetime |
|---|---|---|---|
| `.coord/plan.yml` | `agent-task-splitter` | YAML, mutable | per-goal |
| `.coord/memory.yml` | `agent-shared-memory` | YAML, append-only | persistent |
| `.coord/reconciliation_<NNN>.md` | `agent-output-reconciler` | Markdown | per-round |
| `.coord/debate_<topic>.md` | `agent-debate` | Markdown | per-decision |
| `.coord/acceptance_<NNN>.md` | `agent-acceptance-gate` | Markdown | per-round |

The number `<NNN>` is the `round` field from `plan.yml`. The full
schemas are in `skills/<owner-skill>/references/*.md`.

**If you change the schema:**
- Update the canonical reference markdown for the owner skill.
- Update every consumer skill's SKILL.md that reads the changed file.
- Bump version (semver: schema break = major bump).
- Document the migration path in this CONTRIBUTING.md (or open an
  issue for discussion first).

### 2. The delegate-skill handoff format

`agent-task-splitter` writes `.ai/codex_task_<NNN>_<slug>.md` and
`.ai/gemini_task_<NNN>_<slug>.md` files. The format must match what
`codex-delegate` and `gemini-delegate-skill` expect:

- Sections: `Context`, `Goal`, `Constraints`, `Acceptance`
- File naming: `<agent>_task_<NNN>_<slug>.md` where `<NNN>` is
  zero-padded round number, `<slug>` is kebab-case task ID.
- See `codex-delegate/skills/codex-delegate/SKILL.md` "Supervisor
  Workflow" section for the canonical template.

`agent-output-reconciler` reads `<log-file>.result.json` produced
by the delegate skills' wrappers. Schema fields:

- `status`, `delegate`, `model`, `log_file`, `output_file`, `summary`,
  `risks`, `files_changed`, `tests_run`, `timestamp_utc`

If you add fields, the reconciler skill must handle missing fields
gracefully (older runs won't have new fields).

**If `codex-delegate` or `gemini-delegate-skill` change their
contract:** open a coordination issue here so the splitter +
reconciler skills can update in lockstep. Drift breaks multi-agent
runs silently.

### 3. The Claude / Codex / Gemini routing heuristics

`agent-task-splitter` decides which agent gets each subtask. The
heuristics live in `skills/agent-task-splitter/references/task_splitter_heuristics.md`.
If you change them, also update:

- `skills/agent-task-splitter/SKILL.md` examples
- `README.md` "How they compose" section if the routing table changes

## Local development

```bash
git clone https://github.com/WenyuChiou/agent-collab-skills
cd agent-collab-skills
python -m pytest tests/ -q
```

Tests guard:
- `marketplace.json` structure (exactly 1 plugin, name + source +
  required fields).
- `plugin.json` structure (name, description, version, license).
- Every skill named in the marketplace has a `skills/<name>/SKILL.md`
  file present on disk.
- Every SKILL.md has valid YAML frontmatter with `name` + `description`.

## Adding a new skill

1. `skills/<new-name>/SKILL.md` with YAML frontmatter (`name`,
   `description`).
2. Reference files in `skills/<new-name>/references/` if needed.
3. Bump version in `marketplace.json` and `plugin.json`.
4. Update the table in `README.md` "The 5 skills" → "The 6 skills".
5. Update `tests/test_catalog.py` skill list.
6. Run `python -m pytest tests/`.
7. Smoke test:
   ```bash
   claude plugin marketplace remove agent-collab-skills
   claude plugin marketplace add WenyuChiou/agent-collab-skills
   claude plugin install agent-collab-workspace@agent-collab-skills
   claude plugin list
   ```

## For maintainers: GitHub repo settings

```bash
gh api -X PATCH repos/WenyuChiou/agent-collab-skills \
  -f description="..." \
  -f homepage="..."

gh api -X PUT repos/WenyuChiou/agent-collab-skills/topics \
  -f 'names[]=multi-agent' -f 'names[]=claude-code' \
  -f 'names[]=codex' -f 'names[]=gemini' -f 'names[]=orchestration'
```
