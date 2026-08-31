# Bounded adversarial-review protocol

## Decision frame

Each reviewer receives the same packet:

```markdown
## Decision
<specific decision and authorized human owner>

## Alternatives
- Position A: <testable statement>
- Position B: <testable statement>

## Shared evidence
- <immutable artifact or source references>

## Evaluation criteria
- <criterion and how it can be verified>

## Constraints
- Argue only the assigned position.
- Identify assumptions and cite evidence references.
- Do not modify source files or canonical memory.
- Use the current policy and checkpoint; do not invent budgets.
```

Reviewers should commit to the strongest defensible form of the assigned
position, then engage with the strongest opposing evidence in a later cycle if
policy permits. A reviewer that changes its conclusion should state that
plainly rather than simulate disagreement.

## Synthesis frame

The synthesizer receives completed prose results only. It must not turn a
missing reviewer into an empty success or use vote count as a truth signal.

```markdown
## Synthesis

### Agreed facts
- <fact> — <evidence>

### Contested claims
- <claim> — <supporting and opposing evidence>

### Missing or degraded inputs
- <reviewer/task status and effect>

### Recommendation
- <position or defer>
- Confidence and uncertainty: <plain-language assessment>
- What would change this recommendation: <falsifiable condition>

### Human decision
- Pending: approve / decline / revise
```

## Guardrails

- Evaluate canonical policy before each spawn and after every cycle.
- Let policy determine the number and size of cycles.
- Keep debate scratch uncommitted unless a project explicitly promotes an
  acceptance evidence artifact.
- Preserve every human decision as an append-only record with gate, actor,
  decision, timestamp, rationale, and affected action hash.
- Do not implement the recommendation until the authorized workflow permits it.
