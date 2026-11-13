"""Truce 1914 assembly hotfixes HF-1..HF-7 (TD-301..TD-308 of the plan audit): one focused test each, nothing here edits
or weakens an existing test. HF-1 cuts, HF-6 stretch are below; the others are added with their commits."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.edit import cinematic_transitions as CT
from explainer_engine.production import assemble as ASM

ROOT = Path(__file__).resolve().parents[2]
TRUCE = ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json"


# --- HF-1: the film follows the script's transition_out (FL-406, TD-301) -----------------------------------------------

def _shots(outs: list[str | None]) -> dict:
    return {"shots": [{"shot_id": f"S01_SH{i + 1:03d}", "segment_id": "S01", "location_id": "loc_a",
                       "visual_type": "cinematic_video", "generation_mode": "VIDEO", "transition_out": t}
                      for i, t in enumerate(outs)]}


def test_authored_transitions_win_only_when_asked():
    doc = _shots(["hard_cut", "j_cut", "l_cut", "cross_dissolve_8f", "fade_to_black", None])
    on = CT.plan_episode_cinematic_transitions(doc, fps=24, honour_authored=True)
    kinds = [(p["transition_type"], p["transition_frames"], p.get("authored")) for p in on]
    assert kinds == [("hard_cut_with_jl_bridge", 0, True), ("hard_cut_with_jl_bridge", 0, True),
                     ("hard_cut_with_jl_bridge", 0, True), ("cross_dissolve_8f", 8, True), ("fade_to_black", 24, True)]
    off = CT.plan_episode_cinematic_transitions(doc, fps=24)
    assert off == CT.plan_episode_cinematic_transitions(doc, fps=24, honour_authored=False)
    assert all("authored" not in p for p in off)
    assert all(p["transition_type"] == "hard_cut_with_jl_bridge" for p in off)   # same segment: today's default


def test_a_shot_without_transition_out_keeps_the_structural_choice_even_when_honouring():
    a = {"shot_id": "A", "segment_id": "S01", "location_id": "x", "visual_type": "map_visualization"}
    b = {"shot_id": "B", "segment_id": "S01", "location_id": "y", "visual_type": "cinematic_video"}
    assert CT.select_optimal_cinematic_transition(a, b, honour_authored=True) == CT.select_optimal_cinematic_transition(a, b)
    assert CT.select_optimal_cinematic_transition(a, b, honour_authored=True)["transition_type"] == "map_to_location_zoom_through"
    a["transition_out"] = "hard_cut"   # the script's word beats the map handoff only when asked for
    assert CT.select_optimal_cinematic_transition(a, b, honour_authored=True)["transition_type"] == "hard_cut_with_jl_bridge"
    assert CT.select_optimal_cinematic_transition(a, b)["transition_type"] == "map_to_location_zoom_through"


@pytest.mark.skipif(not TRUCE.is_file(), reason="script A is not in this checkout")
def test_script_a_plan_is_the_scripts_own_cuts_and_no_zoom_through():
    doc = json.loads(TRUCE.read_text(encoding="utf-8"))
    want = [s.get("transition_out") for s in doc["shots"][:-1]]
    plans = CT.plan_episode_cinematic_transitions(doc, fps=24, honour_authored=True)
    assert len(plans) == len(doc["shots"]) - 1
    got = [p["transition_type"] for p in plans]
    assert got.count("fade_to_black") == want.count("fade_to_black") >= 2
    assert got.count("cross_dissolve_8f") == want.count("cross_dissolve_8f") >= 3
    assert got.count("hard_cut_with_jl_bridge") == sum(w in ("hard_cut", "j_cut", "l_cut") for w in want)
    assert not [g for g in got if g in ("map_to_location_zoom_through", "infographic_number_to_scene_morph")]
    assert all(p["authored"] for p in plans)
    off = CT.plan_episode_cinematic_transitions(doc, fps=24)
    assert not any(p.get("authored") for p in off)


def test_the_middle_of_a_fade_is_black_and_the_ends_are_the_pictures():
    a = Image.new("RGB", (64, 36), (200, 120, 40))
    b = Image.new("RGB", (64, 36), (30, 90, 220))
    mid = np.asarray(CT.render_transition_frame_pair(a, b, "fade_to_black", 0.5))
    assert mid.max() == 0
    assert np.asarray(CT.render_transition_frame_pair(a, b, "fade_to_black", 0.0)).tolist() == np.asarray(a).tolist()
    assert np.asarray(CT.render_transition_frame_pair(a, b, "fade_to_black", 1.0)).tolist() == np.asarray(b).tolist()
    first = np.asarray(CT.render_transition_frame_pair(a, b, "fade_to_black", 0.25)).mean()
    assert 0 < first < np.asarray(a).mean()


def test_the_fade_boundary_goes_to_black_in_the_middle_and_back_up(tmp_path):
    def clip(path: Path, colour):
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", f"color=c={colour}:s=64x36:r=24:d=3", "-c:v",
                        "libx264", "-pix_fmt", "yuv420p", str(path)], check=True)
    ca, cb = tmp_path / "a.mp4", tmp_path / "b.mp4"
    clip(ca, "0xC87828")
    clip(cb, "0x1E5ADC")
    a = {"clip": str(ca), "frames": 72}
    b = {"clip": str(cb), "frames": 72}
    plan = {"transition_type": "fade_to_black", "transition_frames": 24}
    half_a, frames, half_b = ASM._boundary_frames(a, b, plan, (64, 36))
    assert (half_a, len(frames), half_b) == (12, 24, 12)
    lum = [float(f.mean()) for f in frames]
    assert lum[half_a - 1] < 3.0                      # black where the two halves meet
    assert lum[0] > lum[half_a - 1] and lum[-1] > lum[half_a]   # down, then up
    assert min(lum) == lum[half_a - 1]
    hard = ASM._boundary_frames(a, b, {"transition_type": "hard_cut_with_jl_bridge", "transition_frames": 0}, (64, 36))
    assert hard == (0, [], 0)
