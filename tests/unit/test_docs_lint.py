"""Unit tests for documentation lint and Decision D-123 (Storytelling System Rebuild, 2026-11-09)."""

from __future__ import annotations

from pathlib import Path

from explainer_engine import docs_lint

ROOT = Path(__file__).resolve().parents[2]
DECISIONS_DOC = ROOT / "docs" / "DECISIONS_AND_OPEN_QUESTIONS.md"


def test_docs_lint_passes_with_zero_findings() -> None:
    """All canonical IDs, relative links, JSON blocks, and index entries must pass docs_lint."""
    assert docs_lint.check() == []


def test_decision_d123_is_defined_in_canonical_home() -> None:
    """D-123 must be uniquely defined in docs/DECISIONS_AND_OPEN_QUESTIONS.md."""
    defs = docs_lint.definitions()
    assert "D-123" in defs
    assert defs["D-123"] == ["DECISIONS_AND_OPEN_QUESTIONS.md"]


def test_decision_d123_resolves_prior_contradictory_decisions() -> None:
    """D-123 must explicitly scope or supersede D-80, D-95, D-96, D-116, D-120, D-121, and D-122."""
    text = DECISIONS_DOC.read_text(encoding="utf-8")
    rows = {
        line.split("|")[1].strip(): line
        for line in text.splitlines()
        if line.startswith("| D-")
    }
    assert "D-123" in rows
    d123 = rows["D-123"]

    # Core architectural locks in D-123
    for required_term in (
        "720",
        "Z1-Z5",
        "S01-S16",
        "0.70-0.80",
        "0.20-0.30",
        "WAN_I2V",
        "WAN_FLF2V",
        "WAN_CONTROL",
        "STILL_25D",
        "MAP_25D",
        "local_preflight.py",
        "EXPLAINER_LOCAL_ONLY=1",
        "Qwen-Image-Edit-2511",
        "Wan2.2-Fun-5B-InP",
    ):
        assert required_term in d123, f"Missing {required_term!r} in D-123 row"

    # Prior decision rows must reference D-123 resolution while keeping their historical text intact
    for decision_id in ("D-80", "D-95", "D-96", "D-116", "D-120", "D-121", "D-122"):
        assert decision_id in rows, f"Missing {decision_id} in decision log"
        assert "by D-123" in rows[decision_id], f"{decision_id} row does not record D-123 resolution"


def test_main_method_and_phase_b_docs_reconciled() -> None:
    """Verify TODO-04, TODO-05, TODO-06, and TODO-07 documentation reconciliation."""
    main_method = (ROOT / "docs" / "MAIN_METHOD.md").read_text(encoding="utf-8")
    for stage_num in range(1, 13):
        assert f"## Stage {stage_num}:" in main_method, f"Missing Stage {stage_num} in MAIN_METHOD.md"
    for term in ("production_script.schema.json", "Z1", "Z5", "S01", "S16", "WAN_I2V", "WAN_FLF2V", "WAN_CONTROL", "STILL_25D", "MAP_25D"):
        assert term in main_method

    assert "docs/MAIN_METHOD.md" in (ROOT / "CHATGPT.md").read_text(encoding="utf-8")
    assert "MAIN_METHOD.md" in (ROOT / "docs" / "CHATGPT_WORKFLOW.md").read_text(encoding="utf-8")
    assert (ROOT / "docs" / "VIDEO_GENERATION_WAN.md").exists()
    assert (ROOT / "docs" / "LOCAL_COMFYUI_SETUP.md").exists()
    assert not (ROOT / "docs" / "pods" / "P12_LTX_FLAGS.md").exists()
    assert (ROOT / "docs" / "archive" / "P12_LTX_FLAGS_2026-11-08.md").exists()

    brief = (ROOT / "docs" / "PROJECT_BRIEF.md").read_text(encoding="utf-8")
    assert "720" in brief and "S01-S16" in brief and "Z1-Z5" in brief and "EXPLAINER_LOCAL_ONLY=1" in brief

    runbook = (ROOT / "docs" / "CLOUD_RUNBOOK.md").read_text(encoding="utf-8")
    assert "DISABLED BY DEFAULT" in runbook
