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


# --- HF-5: the voice track's levels and line ends (FL-408, FL-409; TD-306) --------------------------------------------

def _wav16(path: Path, x: np.ndarray, rate: int = 48000) -> Path:
    from explainer_engine.videolane import voice as VV
    return VV.write_mono(path, x, rate)


def _sine(seconds: float, hz: float, amp: float, rate: int = 48000) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def _one_clip_timing(frames: int = 36) -> dict:
    return {"fps": 24, "total_frames": 24 + frames, "inserts": [{"shot_id": "C", "at_read_frame": 24, "frames": frames}],
            "shots": {"A": {"start_frame": 0}, "C": {"start_frame": 24}}}


def _amp_at(y: np.ndarray, hz: float, a: float, b: float, rate: int = 48000) -> float:
    seg = y[int(a * rate):int(b * rate)]
    f = np.fft.rfftfreq(len(seg), 1 / rate)
    return float(np.abs(np.fft.rfft(seg))[np.argmin(np.abs(f - hz))]) * 2 / len(seg)


def test_a_clip_louder_than_the_read_is_turned_down_to_the_reads_level(tmp_path):
    from explainer_engine.videolane import voice as VV
    read = _wav16(tmp_path / "read.wav", _sine(1.0, 400, 0.05))
    clip = _wav16(tmp_path / "clip.wav", _sine(1.5, 900, 0.05 * 10 ** (15 / 20)))    # 15 dB over the read
    rep = VV.compose(_one_clip_timing(), read, {"C": {"path": str(clip), "speech": [[0.0, 1.5]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 1.0]])
    laid = [e for e in rep["laid"] if e["what"] == "clip"][0]
    assert laid["gain_db"] == pytest.approx(-15.0, abs=0.3) and laid["boost_clamped"] is False
    y = VV.read_mono(tmp_path / "v.wav")
    assert _amp_at(y, 900, 1.1, 1.8) == pytest.approx(_amp_at(y, 400, 0.1, 0.9), rel=0.1)
    assert rep["peak_dbfs"] < 0 and rep["boost_clamped"] == []


def test_a_boost_is_still_clamped_and_reported(tmp_path):
    from explainer_engine.videolane import voice as VV
    read = _wav16(tmp_path / "read.wav", _sine(1.0, 400, 0.2))
    clip = _wav16(tmp_path / "clip.wav", _sine(1.5, 900, 0.2 * 10 ** (-20 / 20)))    # 20 dB under the read
    rep = VV.compose(_one_clip_timing(), read, {"C": {"path": str(clip), "speech": [[0.0, 1.5]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 1.0]])
    laid = [e for e in rep["laid"] if e["what"] == "clip"][0]
    assert laid["gain_db"] == VV.GAIN_MAX_DB and laid["boost_clamped"] is True and rep["boost_clamped"] == ["C"]


def test_the_last_sound_after_an_early_closed_speech_span_keeps_its_level(tmp_path):
    from explainer_engine.videolane import voice as VV
    clip_x = np.concatenate([_sine(0.9, 900, 0.2), _sine(0.3, 700, 0.2), np.zeros(int(0.3 * 48000), np.float32)])
    read = _wav16(tmp_path / "read.wav", _sine(1.0, 400, 0.2))
    clip = _wav16(tmp_path / "clip.wav", clip_x)
    VV.compose(_one_clip_timing(), read, {"C": {"path": str(clip), "speech": [[0.0, 0.9]]}}, tmp_path / "v.wav",
               read_speech=[[0.0, 1.0]])
    y = VV.read_mono(tmp_path / "v.wav")
    tail, speech = _amp_at(y, 700, 1.0 + 1.02, 1.0 + 1.15), _amp_at(y, 900, 1.0 + 0.2, 1.0 + 0.8)
    assert tail > 0.7 * speech      # the 0.3 s sound is as loud as the line (was 15 dB down)


# --- HF-4: a clip over BP-50's ceiling is trimmed in its cut, the raw clip untouched (FL-401, FL-111; TD-305) ----------------

def _speech_clip(tmp_path: Path, name: str, peak: float) -> Path:
    import test_videolane_media as M   # the media helpers of the video lane's own tests (tests/unit is on the path)
    audio = M.speechy(5.0, [(0.8, 2.9)])
    audio = (audio * (peak / float(np.abs(audio).max()))).astype(np.float32)
    return M.write_clip(tmp_path / f"{name}.mp4", M.moving(120, 1.0), fps=24, audio=audio)


def test_a_loud_clip_is_trimmed_in_its_cut_and_ingests_without_a_fail(tmp_path):
    import test_videolane_media as M
    from explainer_engine.qa import targets as TG
    from explainer_engine.videolane import ingest as IN
    raw = _speech_clip(tmp_path, "C_raw", 0.985)          # about -0.1 dBFS: over the -1 dBTP ceiling
    raw_bytes = raw.read_bytes()
    rec = IN.ingest_scene(tmp_path / "ep", M.scene_script(), [{"shot_id": "C", "path": str(raw)}], 24)[0]
    assert rec["level_trim_db"] <= -2.0 and rec["true_peak_before"] > TG.PROFILES["long"]["true_peak_max"]
    assert rec["status"] != "FAIL" and not [f for f in rec["findings"] if f["rule"] == "CLIP-06"]
    assert (tmp_path / "ep" / rec["raw_path"]).read_bytes() == raw_bytes == raw.read_bytes()   # the model's file is untouched
    assert rec["raw_sha256"] == IN._sha(raw)
    after = TG.measure_file(tmp_path / "ep" / rec["clip_path"])["true_peak"]
    assert after <= TG.PROFILES["long"]["true_peak_max"]
    # the trim rides along when the same clip is cut again for another length
    again = IN.cut(raw, tmp_path / "again.mp4", rec["in_s"], rec["frames"], 24, gain_db=rec["level_trim_db"])
    assert TG.measure_file(again)["true_peak"] <= TG.PROFILES["long"]["true_peak_max"]


def test_a_clip_under_the_ceiling_gets_no_trim(tmp_path):
    import test_videolane_media as M
    from explainer_engine.videolane import ingest as IN
    raw = _speech_clip(tmp_path, "C_raw", 0.3)
    rec = IN.ingest_scene(tmp_path / "ep", M.scene_script(), [{"shot_id": "C", "path": str(raw)}], 24)[0]
    assert "level_trim_db" not in rec and rec["status"] != "FAIL"


def test_recut_uses_the_records_level_trim(tmp_path, monkeypatch):
    from explainer_engine.videolane import ingest as IN
    seen = {}

    def fake_cut(raw, out, in_s, frames, fps, gain_db=0.0):
        seen["gain"] = gain_db
        Path(out).write_bytes(b"cut")
        return out
    monkeypatch.setattr(IN, "cut", fake_cut)
    raw = tmp_path / "raw.mp4"
    raw.write_bytes(b"x")
    rec = {"shot_id": "S", "raw_path": "raw.mp4", "raw_sha256": IN._sha(raw), "raw_seconds": 9.0, "in_s": 0.5, "frames": 48,
           "clip_path": "cut.mp4", "level_trim_db": -2.0}
    IN.recut(tmp_path, rec, 72, 24)
    assert seen["gain"] == -2.0


# --- HF-7: --sound-library on run and status (FL-404; TD-308) ------------------------------------------------------------

def _tiny_episode(tmp_path: Path) -> Path:
    root = tmp_path / "ep"
    (root / "story").mkdir(parents=True)
    (root / "episode.json").write_text(json.dumps({"episode_id": "ep_x"}), encoding="utf-8")
    (root / "story" / "production_script.json").write_text(json.dumps({"fps": 24, "shots": []}), encoding="utf-8")
    return root


def test_the_sound_library_flag_reaches_the_episode_and_changes_the_g4_fingerprint(tmp_path, monkeypatch, capsys):
    from explainer_engine.episode import run as RUN
    root = _tiny_episode(tmp_path)
    libs = []
    for name, body in (("a", {"items": [1]}), ("b", {"items": [1, 2]})):
        (tmp_path / name).mkdir()
        (tmp_path / name / "manifest.json").write_text(json.dumps(body), encoding="utf-8")
        libs.append(tmp_path / name)
    fa = RUN.fingerprint(RUN.Episode(root, sound_library=libs[0]), "sound_plan")
    fb = RUN.fingerprint(RUN.Episode(root, sound_library=libs[1]), "sound_plan")
    assert fa != fb
    assert RUN.fingerprint(RUN.Episode(root, sound_library=libs[0]), "sound") != RUN.fingerprint(
        RUN.Episode(root, sound_library=libs[1]), "sound")
    seen = []
    real = RUN.Episode

    def spy(*a, **kw):
        ep = real(*a, **kw)
        seen.append(ep.sound_library)
        return ep
    monkeypatch.setattr(RUN, "Episode", spy)
    assert RUN.main(["status", str(root), "--sound-library", str(libs[1])]) == 0
    assert seen == [libs[1]]
    monkeypatch.setattr(RUN, "STAGE_FUNCS", {s: (lambda ep, rh: ([], {})) for s in RUN.STAGES})
    RUN.main(["run", str(root), "--stage", "script", "--sound-library", str(libs[0])])
    assert seen[-1] == libs[0]
    RUN.main(["status", str(root)])
    from explainer_engine.assets_reuse import SOUND_LIB
    assert seen[-1] == Path(SOUND_LIB)                  # without the flag: the repo's own library, as before
