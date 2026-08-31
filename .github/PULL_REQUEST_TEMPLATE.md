## What this PR changes

<one or two sentences>

## Touches a public contract?

- [ ] No
- [ ] Yes — if so, which schema/CLI/skill, and which consumers were updated in lockstep:
  - File:
  - Updated SKILL.md(s):
  - Migration and rollback path:

## Touches the role-adapter handoff format?

If this PR changes how `agent-task-splitter` writes
`.ai/task_<NNN>_<slug>.md`, how a host adapter returns results, or how
`agent-output-reconciler` reads evidence, link the corresponding host-adapter
PR or issue:

- Upstream coordination: <link, or "N/A">

## Checklist

- [ ] `python -m pytest tests/ -q` passes locally
- [ ] If a skill was added or removed: manifests, both READMEs, install scripts, and `tests/test_catalog.py` agree on the seven-skill inventory or document the approved migration
- [ ] If schema or trigger phrases changed: README + bundle README regenerated, examples in SKILL.md still match
- [ ] CONTRIBUTING.md updated if the interop contract changed
- [ ] `.github` contributor templates contain no stale provider routing or skill counts
- [ ] Memory changes are proposal-only and human decisions remain append-only

## Verification

How did you confirm this works end-to-end?

- [ ] `bash scripts/install-all.sh` produces `claude plugin list` showing `agent-collab-workspace@agent-collab-skills` ✔ enabled
- [ ] Smoke-tested the affected skill on a real multi-agent task
- [ ] Policy/checkpoint examples pass `agent-collab ... validate --json`
- [ ] Any promoted checkpoint or acceptance artifact is explicitly required; scratch remains uncommitted
