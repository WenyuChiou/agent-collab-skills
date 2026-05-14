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


def test_observed_failure_modes_doc_exists_and_covers_real_incidents():
    """The observed-failure-modes doc must capture every failure
    category that the skills now defend against. If a new failure
    is added to the skills without being documented here, that's a
    knowledge-loss risk for future maintainers.
    """
    failure_modes = ROOT / "docs" / "observed-failure-modes.md"
    assert failure_modes.exists(), (
        "docs/observed-failure-modes.md must exist — it's the ground "
        "truth for why each skill guardrail exists."
    )

    text = failure_modes.read_text(encoding="utf-8")
    # Each failure mode codified in the skills must have an F-number
    # entry in this doc.
    required_failure_ids = [
        "F1",  # Gemini gitignore
        "F2",  # Gemini drops table structure
        "F3",  # Time-sensitive language drift
        "F4",  # Frontier-model fabrication
        "F5",  # Star count drift
        "F6",  # Codex over-tabularization
        "F7",  # Slug drift
        "F8",  # Large diff context bloat
        "F9",  # Cascading review rounds
        "F10",  # Stale ScheduleWakeup
    ]
    for fid in required_failure_ids:
        assert f"## {fid}." in text, (
            f"Failure mode {fid} not documented in observed-failure-modes.md"
        )


def test_acceptance_gate_presets_present_and_well_formed():
    """The 3 presets must exist as YAML files under
    skills/agent-acceptance-gate/presets/ and parse cleanly.
    """
    import yaml  # PyYAML; if missing, test will fail with ImportError
    # which is the right signal — the bundle assumes PyYAML.

    presets_dir = ROOT / "skills" / "agent-acceptance-gate" / "presets"
    assert presets_dir.exists(), "presets/ directory must exist"

    required_presets = [
        "multi-locale-mirror-sync.yml",
        "catalog-entry-add.yml",
        "fact-check-frontier-models.yml",
    ]
    for name in required_presets:
        path = presets_dir / name
        assert path.exists(), f"Required preset missing: {name}"
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        # Each preset has the canonical schema
        assert "preset_name" in data, f"{name}: missing preset_name"
        assert "description" in data, f"{name}: missing description"
        assert "checks" in data, f"{name}: missing checks"
        assert isinstance(data["checks"], list) and len(data["checks"]) > 0, (
            f"{name}: checks must be non-empty list"
        )


def test_acceptance_gate_skill_documents_presets():
    """The acceptance-gate SKILL.md must mention each preset by name
    so users can discover them.
    """
    skill = ROOT / "skills" / "agent-acceptance-gate" / "SKILL.md"
    text = skill.read_text(encoding="utf-8")
    for preset_name in [
        "multi-locale-mirror-sync",
        "catalog-entry-add",
        "fact-check-frontier-models",
    ]:
        assert preset_name in text, (
            f"acceptance-gate SKILL.md must reference preset '{preset_name}'"
        )
