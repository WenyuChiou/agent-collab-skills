# Provider-neutral task splitting heuristics

Use this reference when a task could fit more than one role, or when splitting
may create more coordination cost than value.

## Role decision tree

Ask in order:

1. Does the task decide scope, architecture, permissions, or a human-facing
   trade-off?
   - primary-agent
2. Does it independently judge whether a stable candidate is correct, safe, or
   acceptable?
   - reviewer
3. Does it convert completed, already-selected inputs into a required
   structure, without new search or tool use?
   - synthesizer
4. Does it apply a clear pattern or approved contract inside a bounded write
   scope?
   - delegated-executor
5. Is the work ambiguous or exploratory?
   - keep it with the primary-agent until the ambiguity is resolved

Classification belongs to the primary-agent. A child cannot widen its own role
or permissions.

## Character tests

### Primary-agent work

- Root-cause diagnosis
- Public API or schema design
- Security/governance decisions
- Breaking-change and migration judgment
- Scope negotiation with a human

### Delegated-executor work

- Repeat the same approved mapping across files
- Generate boilerplate from a frozen interface
- Implement a bounded function with explicit behavior
- Add test cases from a named fixture matrix

### Reviewer work

- Compare a stable diff to requirements
- Check a scientific claim against its evidence
- Assess security or governance impact
- Issue an acceptance verdict

Reviewer work is honesty-critical. Do not combine it with authorship of the
candidate under review.

### Synthesizer work

- Convert completed prose and source locators into a schema
- Merge non-null accepted summaries into one packet
- Normalize terminology after the semantic choices are frozen

A synthesizer does not search, call external tools, or invent missing evidence.

## DAG patterns

### Linear

primary-agent contract → delegated-executor implementation → reviewer

Use when each stage needs the prior accepted artifact.

### Fan-out/fan-in

primary-agent scope → independent delegated-executor tasks → reviewer

Use when writers have disjoint scopes and one reviewer needs every result.

### Research-style synthesis

read-only researchers → filter failed/null results → synthesizer → deterministic
validator → human semantic gate

Use a research-domain router when the workflow owns research truth stores.

## Do not split when

- The cause of a failure is unknown.
- Multiple tasks would write the same file.
- All proposed children need the same context and have a tight sequential
  dependency.
- No task has an objective acceptance criterion.
- The only reason is to use more agents.

## Scope and evidence checks

For every task:

1. Write scope is explicit and disjoint from parallel writers.
2. External mutations are explicit or absent.
3. Dependencies name stable artifact/evidence paths.
4. Result shape distinguishes failure from missing output.
5. Success criteria are runnable or objectively inspectable.
6. A reviewer or human gate is assigned where judgment matters.

## Retry rule

Do not encode retries in the plan. The host updates TaskCheckpoint and evaluates
the policy before retrying. A repeated failure or no-evidence cycle may stop the
task even when the DAG still contains pending nodes.
