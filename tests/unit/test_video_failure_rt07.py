"""RT-07 for the video route in one place (Fable audit 2026-11-13, FA-16): measured, one paid retry with a new seed inside
the approved plan, then the still_25d fallback with the shot's fallback motion; the runner reads it from videolane/failure."""
from __future__ import annotations

from explainer_engine.aivideo.wan_adapter import DEFAULT_FALLBACK, MAX_ATTEMPTS, SEED_STEP
from explainer_engine.videolane import failure as VF


def test_the_ladder_accept_retry_fallback():
    assert VF.decide([])["action"] == "generate"
    assert VF.decide([{"status": "PASS"}])["action"] == "accept"
    assert VF.decide([{"status": "REVIEW"}])["action"] == "accept"
    r = VF.decide([{"status": "FAIL", "seed": 7100}])
    assert MAX_ATTEMPTS == 2 and r["action"] == "retry" and r["seed"] == 7100 + SEED_STEP
    assert VF.decide([{"status": "FAIL"}, {"status": "FAIL"}])["action"] == "fallback_25d"
    assert VF.decide([{"status": "FAIL"}, {"status": "FAIL"}], allow_fallback=False)["action"] == "fail"


def test_the_fallback_draws_the_shots_own_fallback_motion():
    shot = {"shot_id": "V1", "route": "video", "fallback_motion_imitation": [{"effect": "push"}, {"effect": "mist"}]}
    assert VF.fallback_shot(shot)["motion_imitation"] == shot["fallback_motion_imitation"]
    assert VF.fallback_shot({"shot_id": "V2", "route": "video"})["motion_imitation"] == DEFAULT_FALLBACK


def test_the_runner_reads_rt07_from_the_one_place():
    from pathlib import Path
    src = (Path(__file__).resolve().parents[2] / "explainer_engine" / "episode" / "run.py").read_text(encoding="utf-8")
    body = src[src.index("def stage_clips("):src.index("def stage_sound(")]
    assert "VF.decide(" in body and "VF.fallback_shot(" in body
    assert "fallback_motion_imitation\") or DEFAULT_FALLBACK" not in body     # the private copy of the rule is gone
