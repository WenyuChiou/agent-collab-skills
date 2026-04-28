## What this PR changes

<one or two sentences>

## Touches the .coord/ schema?

- [ ] No
- [ ] Yes — if so, which file, and which consumer skills had to be updated in lockstep:
  - File:
  - Updated SKILL.md(s):
  - Migration path documented in CONTRIBUTING.md:

## Touches the delegate-skill handoff format?

If this PR changes how `agent-task-splitter` writes
`.ai/codex_task_*.md` / `.ai/gemini_task_*.md`, or how
`agent-output-reconciler` reads `result.json`, link the corresponding
upstream PR / issue in `codex-delegate` or `gemini-delegate-skill`:

- Upstream coordination: <link, or "N/A">

## Checklist

- [ ] `python -m pytest tests/ -q` passes locally
- [ ] If a new skill added: `marketplace.json` + `plugin.json` versions bumped, README "5 skills" table updated, `tests/test_catalog.py` skill list updated
- [ ] If schema or trigger phrases changed: README + bundle README regenerated, examples in SKILL.md still match
- [ ] CONTRIBUTING.md updated if the interop contract changed

## Verification

How did you confirm this works end-to-end?

- [ ] `bash scripts/install-all.sh` produces `claude plugin list` showing `agent-collab-workspace@agent-collab-skills` ✔ enabled
- [ ] Smoke-tested the affected skill on a real multi-agent task
- [ ] Output `.coord/<file>` validates against the schema
