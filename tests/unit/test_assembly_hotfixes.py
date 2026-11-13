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


# --- HF-6: the video shots are never squeezed (FL-412, TD-307) --------------------------------------------------------

def test_fit_covers_and_crops_a_1280x704_frame_without_squeezing():
    img = Image.new("RGB", (1280, 704), (20, 20, 20))
    d = ImageDraw.Draw(img)
    d.ellipse((640 - 200, 352 - 200, 640 + 200, 352 + 200), fill=(250, 250, 250))
    out = ASM._fit(np.asarray(img), (1920, 1080))
    assert out.shape == (1080, 1920, 3)
    ys, xs = np.nonzero(out[:, :, 0] > 128)
    width, height = xs.max() - xs.min() + 1, ys.max() - ys.min() + 1
    assert abs(int(width) - int(height)) <= 1, (width, height)   # still a circle
    assert abs(int(xs.mean()) - 960) <= 1 and abs(int(ys.mean()) - 540) <= 1   # centred


def test_fit_with_the_same_aspect_gives_the_plain_resize_pixels():
    rng = np.random.default_rng(3)
    frame = rng.integers(0, 255, (360, 640, 3), dtype=np.uint8)
    plain = np.asarray(Image.fromarray(frame).resize((1920, 1080), Image.LANCZOS))
    assert np.array_equal(ASM._fit(frame, (1920, 1080)), plain)
    assert ASM._fit(frame, (640, 360)) is frame


# --- HF-2 and HF-3: the delivered mix, the measured master, the narrator's own file (FL-402, FL-403; TD-302, TD-303) ----

def _tone(path: Path, db: float, seconds: float = 4.0, channels: int = 2, rate: int = 48000) -> Path:
    layout = "stereo" if channels == 2 else "mono"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i",
                    f"sine=f=220:r={rate}:d={seconds},volume={db}dB,aformat=channel_layouts={layout}", "-c:a", "pcm_s16le",
                    str(path)], check=True)
    return path


def test_a_quiet_mix_is_delivered_inside_bp50s_band_and_the_raw_mix_stays(tmp_path):
    from explainer_engine.episode import run as RUN
    from explainer_engine.qa import targets as TG
    raw = _tone(tmp_path / "mix.wav", -28.0)
    before = RUN._sha(raw)
    delivered = tmp_path / "mix_delivered.wav"
    rows, raw_meas, meas = RUN._deliver_mix(raw, delivered)
    assert RUN._sha(raw) == before and delivered.is_file()
    assert raw_meas["lufs"] < TG.PROFILES["long"]["pass_band"][0] - 5     # the raw mix is far too quiet
    lo, hi = TG.PROFILES["long"]["pass_band"]
    assert lo <= meas["lufs"] <= hi and meas["true_peak"] <= TG.PROFILES["long"]["true_peak_max"]
    assert [r["gate"] for r in rows] == ["delivered_mix_loudness", "delivered_mix_true_peak"]
    assert all(r["status"] == "PASS" for r in rows)


def test_a_silent_preview_mix_is_copied_and_says_not_run(tmp_path):
    from explainer_engine.episode import run as RUN
    raw = _tone(tmp_path / "mix.wav", -200.0)
    rows, _raw_meas, _meas = RUN._deliver_mix(raw, tmp_path / "mix_delivered.wav")
    assert (tmp_path / "mix_delivered.wav").is_file()
    assert [r["status"] for r in rows] == ["NOT_RUN", "NOT_RUN"]


def test_the_master_file_gets_its_own_bp50_rows(tmp_path):
    from explainer_engine.episode import run as RUN
    quiet = tmp_path / "quiet.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "color=c=black:s=64x36:r=24:d=4", "-f", "lavfi", "-i",
                    "sine=f=220:r=48000:d=4,volume=-28dB", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac",
                    "-shortest", str(quiet)], check=True)
    rows, meas = RUN._master_loudness_rows(quiet)
    assert [r["gate"] for r in rows] == ["master_loudness", "master_true_peak"]
    assert rows[0]["status"] != "PASS" and meas["lufs"] < -30      # a master 20 LU too quiet no longer passes unseen
    assert rows[1]["status"] == "PASS"


class _Ep:
    def __init__(self, root: Path):
        self.root = root

    def path(self, rel: str) -> Path:
        return self.root / rel


def test_the_polish_writes_its_own_file_and_never_the_read(tmp_path):
    from explainer_engine.audio import narrator_polish as NP
    from explainer_engine.episode import run as RUN
    (tmp_path / "audio").mkdir()
    read = _tone(tmp_path / "audio" / "narration.wav", -20.0, seconds=3.0, channels=1, rate=24000)
    before = RUN._sha(read)
    out, info = RUN._polish_read(_Ep(tmp_path))
    assert out == tmp_path / RUN.POLISHED_REL and out.is_file()
    assert RUN._sha(read) == before                       # the pinned read is untouched
    assert info["read_sha256"] == before and info["polished_sha256"] == RUN._sha(out) != before
    assert info["chain"] == NP.CHAIN
    assert abs(NP._seconds(out) - NP._seconds(read)) <= 1 / 30
    assert RUN._polish_read(_Ep(tmp_path / "nowhere")) == (None, None)


def test_a_polish_that_moves_the_length_is_refused_and_leaves_nothing(tmp_path, monkeypatch):
    from explainer_engine.audio import narrator_polish as NP
    from explainer_engine.core.errors import ContractError
    from explainer_engine.episode import run as RUN
    (tmp_path / "audio").mkdir()
    read = _tone(tmp_path / "audio" / "narration.wav", -20.0, seconds=2.0, channels=1, rate=24000)
    seen = iter([2.0, 2.2])
    monkeypatch.setattr(NP, "_seconds", lambda _p: next(seen))
    with pytest.raises(ContractError, match="moved the length"):
        RUN._polish_read(_Ep(tmp_path))
    assert not (tmp_path / RUN.POLISHED_REL).exists() and read.is_file()
