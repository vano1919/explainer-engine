"""The Opus medium technical-check line (owner's $10, 2026-11-21) routes through the existing opus-code class, no routing change."""

import json
from pathlib import Path

from explainer_engine.llm import claude_api as ca

ROOT = Path(__file__).resolve().parents[2]


def test_opus_medium_routes_through_opus_code_class():
    row = ca.route("opus-code", "opus", "medium")
    assert row is not None


def test_tech_check_line_is_ten_dollars():
    c = json.loads((ROOT / "config" / "spend_caps.json").read_text(encoding="utf-8"))["claude_api"]
    assert c["jobs"]["opus_tech_check"] == 10.0
