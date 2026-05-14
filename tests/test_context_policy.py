from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_sample_plan_declares_context_policy_defaults():
    sample = (ROOT / "examples" / "plan.yml.sample").read_text(encoding="utf-8")

    assert "context_policy:" in sample
    assert "main_session_token_budget: 3000" in sample
    assert "task_packet_token_budget: 6000" in sample
    assert "result_summary_word_budget: 250" in sample
    assert "memory_digest_token_budget: 1200" in sample
    assert "log_tail_lines_on_error: 50" in sample
    assert "raw_log_policy: path-only" in sample
    assert "agentmemory: optional" in sample


def test_default_reconciliation_sample_is_context_safe():
    r"""The reconciliation sample must demonstrate path-only log handling
    + bounded summaries. We check the positive contract (path references
    present, agent task counts present) and a few specific anti-patterns
    that would indicate a regression toward inline raw logs.

    Note: we intentionally do NOT assert ``` not in sample — a
    fenced YAML/shell block in the prose section is fine and may be added
    later for readability. The real context-safety check is that log
    contents are referenced by *path*, not pasted inline.
    """
    sample = (ROOT / "examples" / "reconciliation_001.md.sample").read_text(
        encoding="utf-8"
    )

    # Positive contract: agent task counts are listed
    assert "Task Count by Agent:" in sample
    assert "- claude: 1" in sample
    assert "- codex: 2" in sample
    assert "- gemini: 1" in sample

    # Positive contract: at least one result/log path is referenced
    # (path-only handling, the whole point of context-safety)
    assert ".ai/" in sample, "reconciliation should reference .ai/ result paths"

    # Negative contract: no raw stack traces or "last N lines" log dumps
    # These would indicate the reconciler pasted log content inline.
    forbidden_patterns = [
        "Traceback (most recent call last)",  # python stack trace
        "Error log tail:",                     # log dump header
        "last 50 lines",                       # explicit log-tail dump
    ]
    for pattern in forbidden_patterns:
        assert pattern.lower() not in sample.lower(), (
            f"Found '{pattern}' in reconciliation sample — context "
            f"safety regression (logs should stay path-only)."
        )


def test_context_docs_and_agentmemory_docs_exist():
    pressure = ROOT / "docs" / "context-pressure-scenarios.md"
    agentmemory = ROOT / "docs" / "agentmemory-integration.md"

    assert pressure.exists()
    assert agentmemory.exists()

    pressure_text = pressure.read_text(encoding="utf-8")
    for phrase in [
        "large Codex + Gemini refactor",
        "cross-session resume with long memory",
        "Gemini task drift",
        "agentmemory unavailable",
    ]:
        assert phrase in pressure_text

    agentmemory_text = agentmemory.read_text(encoding="utf-8")
    assert ".coord/memory.yml is canonical" in agentmemory_text
    assert "optional" in agentmemory_text.lower()
