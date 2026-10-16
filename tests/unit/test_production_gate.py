"""The production gates (docs/PRODUCTION_RULES.md): free checks, one line per gate."""

from __future__ import annotations

from pathlib import Path

from explainer_engine import production_gate as G

ROOT = Path(__file__).resolve().parents[2]
DAY = ROOT / "examples/stone_age/day1_v4"


def by_gate():
    return {r["gate"]: r for r in G.gates(DAY)}


def test_day1_v4_state_is_reported_honestly():
    g = by_gate()
    assert g[1]["status"] == "PASS"  # narration_lint has no FAIL
    assert g[2]["status"] == "WAIT" and "another read" in g[2]["detail"]  # timings of the v2 text, not v4
    assert g[3]["status"] == "BLOCKED"  # Wallace and Snow have no sprite
    assert g[4]["status"] == "WAIT" and g[5]["status"] == "WAIT" and g[6]["status"] == "WAIT"


def test_a_missing_folder_waits_instead_of_crashing(tmp_path):
    rows = G.gates(tmp_path, tmp_path / "look.json")
    assert all(r["status"] in ("WAIT", "BLOCKED") for r in rows) and rows[0]["status"] == "WAIT"
    assert [r["gate"] for r in rows] == list(range(1, 10))


def test_production_rules_page_is_linked_and_names_every_gate():
    text = (ROOT / "docs/PRODUCTION_RULES.md").read_text(encoding="utf-8")
    assert all(f"| {n} |" in text for n in range(10))
    assert "PRODUCTION_RULES" in (ROOT / "docs/INDEX.md").read_text(encoding="utf-8")
