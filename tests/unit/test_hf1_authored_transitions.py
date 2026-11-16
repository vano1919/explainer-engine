"""HF-1 (Truce 1914 assembly, FL-406, TD-301): the film follows the script's own ``transition_out``, fade to black included."""
from __future__ import annotations

import collections
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.edit.cinematic_transitions import (
    TRANSITION_TYPES,
    plan_episode_cinematic_transitions,
    render_transition_frame_pair,
    select_optimal_cinematic_transition,
)

REPO = Path(__file__).resolve().parents[2]
SCRIPT_A = REPO / "episodes" / "ep_truce_1914" / "story" / "production_script.json"


def _shot(i, seg="S01", loc="loc_a", out="hard_cut", visual="video"):
    return {"shot_id": f"{seg}_SH{i:03d}", "segment_id": seg, "location_id": loc, "transition_out": out,
            "visual_type": visual, "generation_mode": "", "camera_spec": {"camera_move": "static"}}


def _synthetic():
    """84 shots shaped like script A: dissolves/fades at known places, map shots and segment changes around them."""
    shots = [_shot(i, seg=f"S{1 + i // 11:02d}", loc="loc_a" if i % 7 else "loc_b") for i in range(84)]
    shots[3]["visual_type"] = "map_visualization"          # a map -> scene handoff would zoom through by default
    for i, kind in {4: "fade_to_black", 23: "cross_dissolve_8f", 71: "cross_dissolve_8f", 79: "cross_dissolve_8f",
                    82: "fade_to_black"}.items():
        shots[i]["transition_out"] = kind
    return {"shots": shots}


def test_fade_to_black_is_a_known_transition():
    assert "fade_to_black" in TRANSITION_TYPES


def test_authored_plan_follows_the_script():
    plans = plan_episode_cinematic_transitions(_synthetic(), honour_authored=True)
    assert len(plans) == 83
    kinds = collections.Counter(p["transition_type"] for p in plans)
    assert kinds == {"hard_cut_with_jl_bridge": 78, "cross_dissolve_8f": 3, "fade_to_black": 2}
    assert "map_to_location_zoom_through" not in kinds
    assert all(p["authored"] for p in plans)
    by = {p["from_shot_id"]: p for p in plans}
    assert by["S01_SH004"]["transition_type"] == "fade_to_black" and by["S01_SH004"]["transition_frames"] == 24
    assert by["S03_SH023"]["transition_frames"] == 8
    assert all(p["ed04_compliant"] for p in plans)


def test_j_and_l_cut_words_are_hard_cuts_with_zero_frames():
    for word in ("j_cut", "l_cut", "hard_cut"):
        p = select_optimal_cinematic_transition(_shot(1, out=word), _shot(2, seg="S02"), honour_authored=True)
        assert p["transition_type"] == "hard_cut_with_jl_bridge" and p["transition_frames"] == 0 and p["authored"]


def test_flag_off_the_plan_is_what_it_was():
    doc = _synthetic()
    off = plan_episode_cinematic_transitions(doc)
    assert off == plan_episode_cinematic_transitions(doc, honour_authored=False)
    assert all("authored" not in p for p in off)
    assert "fade_to_black" not in {p["transition_type"] for p in off}


def test_unknown_authored_word_falls_back_to_the_structural_choice():
    a = _shot(1, out="wipe_left")
    assert select_optimal_cinematic_transition(a, _shot(2), honour_authored=True) == select_optimal_cinematic_transition(a, _shot(2))


def test_fade_middle_is_black_and_ends_are_the_shots():
    a = Image.new("RGB", (64, 36), (200, 120, 40))
    b = Image.new("RGB", (64, 36), (30, 90, 210))
    mid = np.asarray(render_transition_frame_pair(a, b, "fade_to_black", 0.5))
    assert mid.max() == 0
    early = np.asarray(render_transition_frame_pair(a, b, "fade_to_black", 0.1))
    late = np.asarray(render_transition_frame_pair(a, b, "fade_to_black", 0.9))
    assert 0 < early.max() < 200 and early[0, 0, 0] > early[0, 0, 2]          # still A (orange), dimmed
    assert 0 < late.max() < 210 and late[0, 0, 2] > late[0, 0, 0]             # already B (blue), not yet full


@pytest.mark.skipif(not SCRIPT_A.is_file(), reason="script A is not in this checkout")
def test_script_a_plan_has_no_zoom_through_and_matches_the_authored_words():
    doc = json.loads(SCRIPT_A.read_text(encoding="utf-8"))
    plans = plan_episode_cinematic_transitions(doc, honour_authored=True)
    want = collections.Counter({"hard_cut": "hard_cut_with_jl_bridge", "cross_dissolve_8f": "cross_dissolve_8f",
                                "fade_to_black": "fade_to_black"}[s["transition_out"]] for s in doc["shots"][:-1])
    assert collections.Counter(p["transition_type"] for p in plans) == want
    assert "map_to_location_zoom_through" not in want
