# Migration to 0.4

Version 0.4 introduces the public agent-collab-harness package and removes the
archived Gemini lane from active routing. Historical artifacts remain readable.

## Active routing

Replace provider values with roles:

| Before | 0.4 role |
|---|---|
| Claude orchestrator | primary-agent |
| Codex or another bounded worker | delegated-executor |
| Independent code/research review | reviewer |
| Output-only structural conversion | synthesizer |
| Gemini lane | no active mapping; choose a supported role adapter |

The host chooses an adapter for each role. Adapter selection is configuration,
not a public plan-schema field.

## Plan files

New plans:

- add schema_version: 2
- replace agent with role
- replace provider-specific task paths with .ai/task_<NNN>_<slug>.md
- add policy_ref and checkpoint_ref when autonomous loops or child spawns are
  allowed
- point policy_ref at the single `AGENT_COLLAB_POLICY` source; the existing
  portable-harness v1 policy is accepted directly
- keep .coord/ and .ai/ ignored unless evidence is explicitly promoted

Readers may parse schema-less v1 plans and historical provider-specific task
files. Writers must emit only v2.

## Shared memory

Previous guidance described .coord/memory.yml as append-only while allowing
fields on older questions and sessions to be changed. That contract is
deprecated.

New work:

1. Writes a proposal under .coord/memory-proposals/ with an immutable nested
   action object.
2. Records approve, decline, or revise from a human.
3. Applies an approved proposal by appending a new event.
4. Never edits, archives, supersedes, or deletes canonical memory without the
   recorded decision.

The approval hash covers only the immutable action object. Existing proposal
drafts that hashed their whole mutable envelope must be regenerated and
re-approved; do not carry those hashes forward.

## Human authorization

Checkpoint decisions and overrides now require HMAC authorization from a key
held by the trusted host. Configure `AGENT_COLLAB_HUMAN_KEYS_JSON` only in the
policy evaluator process, do not expose it to delegated executors, and never
write it into a checkpoint, task packet, log, or repository file. Unsigned,
unknown-key, or altered records fail closed. Overrides additionally record the
observed metric value and must be signed before the original limit is reached.
The public canonical policy must pin each permitted key's SHA-256 digest under
`human_authorization.key_hashes`. The portable v1 compatibility policy has no
such trust root, so it remains budget-compatible but cannot authorize human
records until a reviewed canonical-policy migration adds one.

Existing memory.yml files remain readable. Convert an updated question into a
new resolution event rather than editing resolved_by in place.

## Gemini history

The archived gemini-delegate-skill repository, changelog entries, observed
failure reports, and historical result files are preserved. Current install
instructions, keywords, routing examples, and tests no longer present Gemini as
an available lane.

## Operational rollback

Version 0.4 is the first release of the Python distribution, so there is no
earlier Python package version to reinstall. To roll back:

1. Save the current policy, checkpoint, plugin source revision, and acceptance
   evidence before changing the installation.
2. Disable any host adapter that invokes `agent-collab`.
3. Run `python -m pip uninstall agent-collab-harness` in the environment where
   0.4 was installed.
4. Restore the skill plugin from the exact pre-migration Git revision or saved
   plugin artifact using the host's normal plugin installation workflow.
5. Run the host's plugin list/doctor command and confirm the restored seven or
   historical skill inventory matches that revision.
6. Re-open a copied v1 plan or memory file read-only before resuming work. Do
   not rewrite 0.4 evidence or checkpoints in place.

A source rollback is a normal Git revert of the 0.4 migration commit. Neither
package nor source rollback re-enables a retired provider. Re-enabling any host
adapter is a separate explicit governance decision.
