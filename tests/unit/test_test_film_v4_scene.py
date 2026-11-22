"""Test Film v4 shot 3 (the LTX video shot): the committed scene stays inside the creator's lines (Modal $2 line, modal_ltx per-run cap)."""
import json
from pathlib import Path

from explainer_engine.core import spend_caps

SCENE = Path(__file__).resolve().parents[2] / "explainer_engine/training/pods/ltx/scenes/test_film_v4_s3.json"


def _scene():
    return json.loads(SCENE.read_text(encoding="utf-8"))


def test_scene_is_one_silent_push_in_clip():
    s = _scene()
    assert s["schema"] == "ltx_scene_test/1" and len(s["shots"]) == 1
    p = s["shots"][0]["motion_prompt"]
    assert "Nobody speaks." in p and "pushes in" in p      # zoom_in only, no speech
    assert s["shots"][0]["seconds"] <= 5.0


def test_scene_ledger_cap_is_under_the_overnight_line():
    s = _scene()
    cap = s["ledger"]["caps"]["modal_ltx"]
    assert cap <= float(spend_caps.modal_ltx()["per_run_usd"])
    line = spend_caps.overnight("overnight_2026_11_23")["lines"]["test_film_v4_modal"]["modal_usd"]
    assert line == 2.0 and cap <= line
