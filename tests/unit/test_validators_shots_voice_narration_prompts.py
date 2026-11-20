"""W2: validators for shots, voice, narration and prompts: a passing and a failing fixture per rule; critic rules never PASS."""
from __future__ import annotations

import json
from pathlib import Path

from explainer_engine.qa import gates as G
from explainer_engine.validators import narration as N
from explainer_engine.validators import prompts as P
from explainer_engine.validators import shots as S
from explainer_engine.validators import voice as V

ROOT = Path(__file__).resolve().parents[2]


def _gates(rows):
    return {r["gate"].split(":")[0] for r in rows}


def _status(rows, gate):
    return [r["status"] for r in rows if r["gate"].split(":")[0] == gate]


# --- shots ----------------------------------------------------------------------------------------------------------------

def _card(i, **kw):
    base = {"shot_id": f"SH{i}", "subject": "kael", "lens_tier": "wide", "camera_height": "low",
            "camera_spec": {"horizontal_azimuth_deg": 0},
            "screen_composition": {"foreground": "ash", "midground": "Kael", "background": "wall"}}
    base.update(kw)
    return base


def test_shots_critic_rows_are_review_never_pass_and_name_missing_fields():
    good = [_card(1), _card(2, lens_tier="long")]
    bad = [_card(1, lens_tier=None, camera_height="sideways", screen_composition={"foreground": "ash"})]
    for rows in (S.validate(good), S.validate(bad)):
        for g in ("CRAFT-CIN-01", "CRAFT-CIN-02", "CRAFT-CIN-06"):
            assert _status(rows, g) == [G.REVIEW]
    assert S.lens_tier(good)["measured"]["missing"] == []
    assert S.lens_tier(bad)["measured"]["missing"] == ["lens_tier on SH1"]
    assert S.camera_height(bad)["measured"]["missing"] == ["camera_height on SH1"]
    assert S.depth_staging(bad)["measured"]["missing"] == ["foreground/midground/background on SH1"]


def test_cin03_same_subject_changes_angle_or_lens_or_it_is_review():
    ok = S.angle_or_lens_change([_card(1), _card(2, camera_spec={"horizontal_azimuth_deg": 45})])
    assert [r["status"] for r in ok] == [G.PASS]
    ok_lens = S.angle_or_lens_change([_card(1, lens_tier="wide"), _card(2, lens_tier="long")])   # 24 -> 85 mm
    assert [r["status"] for r in ok_lens] == [G.PASS]
    jump = S.angle_or_lens_change([_card(1), _card(2, camera_spec={"horizontal_azimuth_deg": 10})])
    assert [r["status"] for r in jump] == [G.REVIEW]        # a hypothesis rule never BLOCKs
    unknown = S.angle_or_lens_change([{"shot_id": "a", "subject": "x"}, {"shot_id": "b", "subject": "x"}])
    assert [r["status"] for r in unknown] == [G.NOT_RUN]
    other = S.angle_or_lens_change([_card(1), _card(2, subject="sena")])
    assert [r["status"] for r in other] == [G.NOT_RUN]       # different subjects: nothing to compare


def test_map_rules_are_critic_rows():
    steps = [{"changed": ["fleet"], "highlight_before_move": True}, {"changed": ["a", "b"]}]
    r = S.map_steps(steps)
    assert r["status"] == G.REVIEW and r["measured"]["missing"] == ["changed/highlight_before_move on step 1"]
    assert r["measured"]["measured"]["too_many"] == [1]
    plates = {"projection": "mercator", "north_up": True,
              "plates": [{"id": "m1", "scale": "meso", "scale_bar": False, "legend": True, "symbol_classes": 2}]}
    r = S.map_plates(plates)
    assert r["status"] == G.REVIEW and r["measured"]["measured"]["no_scale_bar"] == ["m1"] and r["measured"]["measured"]["bad_legend"] == ["m1"]
    assert S.map_plates({})["measured"]["missing"] == ["projection", "north_up", "plates"]
    assert _gates(S.validate([_card(1), _card(2, camera_spec={"horizontal_azimuth_deg": 90})], map_step_list=steps,
                             map_plate_set=plates)) == set(S.RULE_IDS)


# --- voice ----------------------------------------------------------------------------------------------------------------

def test_voice_critic_rows():
    lines = [{"line_id": "L1", "text": "[hushed] The ash fell.", "delivery_direction": "hushed"},
             {"line_id": "L2", "text": "It was HUGE and LOUD.", "delivery_direction": ""}]
    shots = [{"shot_id": "S1", "visual_type": "cinematic_video", "audio_line_ids": ["L1"], "face_visible": True},
             {"shot_id": "S2", "visual_type": "cinematic_video", "audio_line_ids": ["L2"], "face_visible": False}]
    rows = V.validate(lines, shots)
    assert _gates(rows) == set(V.RULE_IDS) and all(r["status"] == G.REVIEW for r in rows)
    assert V.one_stressed_word(lines[:1])["measured"]["missing"] == []
    assert V.one_stressed_word(lines)["measured"]["missing"] == ["one stressed word in line L2"]
    ok = V.animated_line_delivery(shots[:1], {l["line_id"]: l for l in lines})
    bad = V.animated_line_delivery(shots, {l["line_id"]: l for l in lines})
    assert ok["measured"]["missing"] == [] and bad["measured"]["missing"] == ["delivery_direction of L2", "face_visible on S2"]


# --- narration ------------------------------------------------------------------------------------------------------------

def _line(text, lid="L1", speaker="narrator"):
    return {"line_id": lid, "text": text, "speaker_type": speaker}


def test_words_per_line_pass_review_and_not_run():
    assert [r["status"] for r in N.words_per_line([_line("Eight billion people alive today.")])] == [G.PASS]
    long = " ".join(["word"] * 22) + "."
    assert [r["status"] for r in N.words_per_line([_line(long)])] == [G.REVIEW]
    huge = " ".join(["word"] * 30) + "."
    assert [r["status"] for r in N.words_per_line([_line(huge)])] == [G.FAIL]     # BP-06 is binding: over 25 words is BLOCK
    assert [r["status"] for r in N.words_per_line([_line("Hi.", speaker="hero")])] == [G.NOT_RUN]


def test_hook_seconds():
    assert N.hook_seconds([_line("Eight billion people alive today.")])["status"] == G.PASS
    slow = N.hook_seconds([_line("In the long and winding history of volcanic eruptions across the African continent, one stands apart.")])
    assert slow["status"] == G.REVIEW
    assert N.hook_seconds([])["status"] == G.NOT_RUN


def test_twist_sentence_lands_or_is_not_named():
    rows = N.twist_sentence([{"segment_id": "A", "twist": "It was glass."},
                             {"segment_id": "B", "twist": " ".join(["glass"] * 40) + "."}, {"segment_id": "C"}])
    assert [r["status"] for r in rows] == [G.PASS, G.REVIEW, G.NOT_RUN]


def test_narration_critic_rows_and_the_real_script_runs_end_to_end():
    r = N.ai_tells("It is not just a rock. It is a testament, a journey, a revolution.")
    assert r["status"] == G.REVIEW and r["measured"]["missing"] == [] and "measured" in r["measured"]
    assert N.ai_tells("")["measured"]["missing"] == ["narration text"]
    lines = [_line("A line.", "L1")]
    assert N.no_double_exposition(lines, [])["measured"]["missing"] == ["shot card for line L1"]
    shots = [{"audio_line_ids": ["L1"], "image_prompt": {"start_frame_prompt": "x"}}]
    assert N.no_double_exposition(lines, shots)["measured"]["missing"] == []
    script = json.loads((ROOT / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    rows = N.validate(script)
    assert _gates(rows) == set(N.RULE_IDS)
    assert all(_status(rows, g) == [G.REVIEW] for g in ("CRAFT-SCR-02", "CRAFT-SCR-06"))


# --- prompts --------------------------------------------------------------------------------------------------------------

GOOD_IMG = ("Cinematic 35mm frame; Kael in an antelope-hide cloak sprints across dark basalt rock, glowing amber pumice streaks "
            "past the lens, a wall of black ash laced with lightning rises behind him")


def _shot(img=GOOD_IMG, motion="Kael sprints across the ledge; the camera tracks backward.", count=1):
    return {"shot_id": "SH1", "image_prompt": {"start_frame_prompt": img}, "video_prompt": {"motion_prompt": motion, "primary_action_count": count}}


def test_slop_words():
    assert P.slop_words([_shot()])["status"] == G.PASS
    bad = P.slop_words([_shot(img="A masterpiece, 8k, highly detailed battle, trending on artstation")])
    assert bad["status"] == G.REVIEW and len(bad["measured"]) == 4
    assert P.slop_words([_shot(motion="stunning breathtaking pan")])["status"] == G.REVIEW


def test_image_prompt_needs_three_physical_details():
    assert [r["status"] for r in P.image_details([_shot()])] == [G.PASS]
    assert [r["status"] for r in P.image_details([_shot(img="A man runs.")])] == [G.REVIEW]
    assert [r["status"] for r in P.image_details([{"shot_id": "x"}])] == [G.NOT_RUN]


def test_motion_prompt_is_one_physical_action():
    assert [r["status"] for r in P.motion_actions([_shot()])] == [G.PASS]
    assert [r["status"] for r in P.motion_actions([_shot(count=2)])] == [G.REVIEW]
    undeclared = _shot()
    undeclared["video_prompt"].pop("primary_action_count")
    undeclared["video_prompt"]["motion_prompt"] = "He jumps; she screams; they run; he falls."
    assert [r["status"] for r in P.motion_actions([undeclared])] == [G.REVIEW]   # counted by shot_prompt_lint
    assert [r["status"] for r in P.motion_actions([{"shot_id": "still"}])] == [G.NOT_RUN]


def test_prompt_rules_all_report_on_the_real_script():
    script = json.loads((ROOT / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    assert _gates(P.validate(script)) == set(P.RULE_IDS)
