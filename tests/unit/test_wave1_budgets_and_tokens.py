"""Unit tests for Wave 1: independent aggregate budget envelopes ($20/$4.50/$50) and token telemetry."""
from __future__ import annotations

import json
from pathlib import Path
import pytest

from explainer_engine.core import spend_caps as SC
from explainer_engine.llm import deepseek_api as DS
from explainer_engine.llm import opus_code as OC


def test_independent_aggregate_envelopes_enforce_exact_ceilings(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_ENVELOPE_LEDGER", str(tmp_path / "env_ledger.json"))
    assert SC.envelope_limit("modal_modal1") == 20.0
    assert SC.envelope_limit("deepseek") == 4.5
    assert SC.envelope_limit("claude_api") == 50.0

    SC.envelope_reserve("deepseek", "T1", 2.0)
    SC.envelope_settle("deepseek", "T1", 1.75)
    SC.envelope_reserve("deepseek", "T2", 2.5)
    with pytest.raises(SC.OverCeiling):
        SC.envelope_reserve("deepseek", "T3", 0.30)  # 1.75 + 2.50 + 0.30 = 4.55 > 4.50

    # Budgets are independent: Modal1 still has full $20.00
    st = SC.envelope_status()
    assert st["modal_modal1"]["remaining_usd"] == 20.0
    assert st["deepseek"]["spent_usd"] == 1.75
    assert st["deepseek"]["reserved_usd"] == 2.5


def test_opus_and_deepseek_dry_run_emit_labeled_token_estimates(tmp_path: Path, capsys):
    brief = tmp_path / "b.md"
    brief.write_text("Add a small helper function.", encoding="utf-8")

    rc1 = OC.main(["code", "--brief", str(brief), "--max-usd", "1.0", "--max-tokens", "4000", "--dry-run"])
    assert rc1 == 0
    out1 = json.loads(capsys.readouterr().out)
    assert out1["max_output_tokens"] == 4000
    assert out1["token_count_basis"].startswith("upper_bound_estimate")
    assert out1["input_tokens_estimate"] > 0

    rc2 = DS.main(["code", "--brief", str(brief), "--max-usd", "0.5", "--max-tokens", "2000", "--dry-run"])
    assert rc2 == 0
    out2 = json.loads(capsys.readouterr().out)
    assert out2["max_output_tokens"] == 2000
    assert out2["token_count_basis"].startswith("upper_bound_estimate")
