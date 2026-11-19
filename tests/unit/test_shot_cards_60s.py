"""The 60 s shot cards (W8, plan 5.2): bundle schema, every card as continuity_card/1, the clock, the route mix, prompt shape."""
import json
import re
from pathlib import Path

import jsonschema

from explainer_engine.scripting import continuity

ROOT = Path(__file__).resolve().parents[2]
CARDS = ROOT / "episodes" / "ep_truce_1914" / "story" / "shot_cards_60s.json"
SCHEMAS = ROOT / "explainer_engine" / "schemas"
ORDER = ["S01_SH001", "S01_SH002", "S01_SH003", "S01_SH004", "S01_SH005",
         "S02_SH001", "S02_SH002", "S02_SH003", "S02_SH004", "S02_SH005"]
STYLE_HEAD = "Photoreal live-action cinematic film still, shot on 35 mm film, natural low winter sun"
SLOP = ["masterpiece", "8k", "ultra detailed", "hyperrealistic", "stunning", "breathtaking", "epic", "award-winning", "trending"]


def _bundle():
    return json.loads(CARDS.read_text(encoding="utf-8"))


def _shots():
    return {s["shot_id"]: (c, s) for c in _bundle()["cards"] for s in c["shots"]}


def test_bundle_validates_and_every_card_is_a_continuity_card():
    b = _bundle()
    jsonschema.Draft202012Validator(json.loads((SCHEMAS / "shot_cards_bundle.schema.json").read_text())).validate(b)
    assert continuity.schema_findings  # the checker exists
    for card in b["cards"]:
        assert continuity.schema_findings(card) == [], card["scene_id"]
        if not any(s.get("route") == "map_action" for s in card["shots"]):
            assert continuity.check(card) == [], card["scene_id"]


def test_ten_shots_in_order_with_the_measured_route_mix():
    shots = _shots()
    assert list(shots) != [] and sorted(shots) == sorted(ORDER) and _bundle()["shot_order"] == ORDER
    routes = [shots[i][1]["route"] for i in ORDER]
    assert (routes.count("still_25d"), routes.count("map_action"), routes.count("video")) == (5, 3, 2)


def test_durations_come_from_the_clock_and_are_contiguous():
    shots = _shots()
    frame, secs = 0, 0.0
    for i in ORDER:
        d = shots[i][1]["duration"]
        assert d["start_frame"] == frame and d["frames"] >= 1 and "timing.json" in d["source"]
        assert abs(d["seconds"] - d["frames"] / 24) < 0.001
        frame += d["frames"]
        secs += d["seconds"]
    assert frame == 1470 and abs(secs - 61.25) < 0.01


def test_every_shot_has_the_52_fields_and_questions():
    for sid, (_, s) in _shots().items():
        for k in ("dramatic_purpose", "narrative_information", "environment", "time_and_light", "camera_position", "lens",
                  "character_action", "background_action", "acting_lane", "audio_events", "continuity_constraints",
                  "motion_prompt", "motion_kind", "acceptance_questions", "camera_move"):
            assert s.get(k), (sid, k)
        assert len(s["audio_events"]) >= 1


def test_image_prompts_are_baseline_plus_delta_with_a_lens_and_no_slop():
    for sid, (_, s) in _shots().items():
        if s["route"] == "map_action":
            assert "image_prompt" not in s and s["map"]["laws"], sid
            continue
        p = s["image_prompt"]
        assert p.startswith(STYLE_HEAD), sid
        assert "shallow depth of field. Faces" not in p and "fine film grain. Faces" in p, sid  # depth of field is per shot
        assert re.search(r"Lens \d+ mm at f/[\d.]+, focused at ", p), sid
        assert not [w for w in SLOP if w in p.lower()], sid
        assert len(s["motion_prompt"]) != len(p) and s["motion_prompt"] not in p  # image and motion prompts stay separate


def test_video_shots_have_one_action_and_a_separate_camera():
    for sid in ("S01_SH002", "S01_SH003"):
        s = _shots()[sid][1]
        assert s["route"] == "video" and s["motion_kind"] == "ltx" and s["camera_move"]
        assert len(s["audio_events"]) >= 3  # D-135: every visible event has its audio decision
