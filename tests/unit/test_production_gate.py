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


def test_a_production_script_episode_is_gated_on_what_its_flow_writes(tmp_path):
    """D-43 episodes: gates read the script, words.json, the paint plans and the ledger, never shots.json (audit M2)."""
    import json
    import sys
    sys.path.insert(0, str(Path(__file__).parent))
    from test_production_script import compiled
    from explainer_engine.core.ledger import Run
    from explainer_engine.imagegen import plan as P
    from explainer_engine.production import script as S
    doc = compiled()
    S.save(doc, tmp_path / "production_script.json")
    g = {r["gate"]: r for r in G.gates(tmp_path)}
    assert g[0]["status"] in ("PASS", "BLOCKED") and g[2]["status"] == "WAIT" and "words.json" in g[2]["detail"]
    assert g[5]["status"] == "WAIT" and "0 plans" in g[5]["detail"]
    plan = P.make("B1", "mini", [{"id": "cold_hands", "prompt": "p", "refs": []}], provider="pod", purpose="x")
    (tmp_path / "pictures" / "plans").mkdir(parents=True)
    (tmp_path / "pictures" / "plans" / "B1.json").write_text(json.dumps(plan))
    run = Run.open(tmp_path / "run.json", caps={"runpod_usd": 3.0})
    assert "1 waiting" in G.gates(tmp_path, run_path=tmp_path / "run.json")[5]["detail"]
    run.approve("B1", plan["hash"], by="creator", ref="cmsg_x", provider="pod", usd=plan["estimate_usd"])
    assert "0 waiting" in G.gates(tmp_path, run_path=tmp_path / "run.json")[5]["detail"]
