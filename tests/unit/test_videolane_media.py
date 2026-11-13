"""The video lane on REAL media (VL-07, VL-11, VL-12, VL-13; docs/VIDEO_LANE.md): synthetic LTX-like clips (a moving
picture, a late spoken line in band-limited noise bursts, room tone) are ingested, cut, assembled and measured as files.
Nothing is mocked at the media level: ffmpeg writes and decodes every clip, the gates read the frames and the samples.

Calibration of the engineering defaults (CONT_DIFF_MAX, SAME_DIFF_MIN, ORDER_DIFF_MAX) is the pair of positive and negative
cases here: a continuation that keeps moving passes, a reversal and a jump fail; a coverage cut to another picture of the
same place passes, the same picture twice fails."""
from __future__ import annotations

import json
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest

from explainer_engine.core.errors import ContractError
from explainer_engine.qa import gates as G

FPS = 24
W, H = 320, 176
RATE = 48000


# --- synthetic media -------------------------------------------------------------------------------------------------------

_CANVAS: dict = {}


def _canvas(k: float) -> np.ndarray:
    """A painted-looking place: smooth random detail (blurred noise), seeded by ``k``, six frames wide to pan over."""
    import cv2
    if k not in _CANVAS:
        rng = np.random.default_rng(int(round(k * 100)) + 7)
        z = cv2.GaussianBlur(rng.normal(0, 1, (H, W * 6)).astype(np.float32), (0, 0), 4)
        _CANVAS[k] = (z - z.mean()) / z.std()
    return _CANVAS[k]


def texture(phase: float, *, k: float = 0.0, tint=(1.0, 0.85, 0.6), **_) -> np.ndarray:
    """One frame of the place ``k`` seen from x offset ``phase`` (320 px units; a pan or a march moves it)."""
    z = _canvas(k)
    x0 = int(round(W * 2.5 + phase))
    g = np.clip(128 + 45 * z[:, x0:x0 + W], 0, 255)
    rgb = np.stack([g * tint[0], g * tint[1] + 10, g * tint[2] + 30], axis=-1)
    return np.clip(rgb, 0, 255).astype(np.uint8)


def speechy(seconds: float, spans, *, level=0.25, room=0.004, seed=1) -> np.ndarray:
    """Room tone with spoken-line-like bursts (300-3000 Hz noise, syllables at 4 Hz) inside ``spans``."""
    rng = np.random.default_rng(seed)
    n = int(seconds * RATE)
    x = rng.normal(0, room, n).astype(np.float32)
    for a, b in spans:
        i0, i1 = int(a * RATE), int(b * RATE)
        z = rng.normal(0, 1, i1 - i0)
        f = np.fft.rfftfreq(len(z), 1 / RATE)
        zs = np.fft.rfft(z)
        zs[(f < 300) | (f > 3000)] = 0
        z = np.fft.irfft(zs, len(z))
        z = z / (np.abs(z).max() + 1e-9)
        t = np.arange(i1 - i0) / RATE
        env = 0.55 + 0.45 * np.sin(2 * np.pi * 4.0 * t)
        x[i0:i1] += (level * z * env).astype(np.float32)
    return x


def write_wav(path: Path, x: np.ndarray, rate=RATE) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def write_clip(path: Path, frames, fps=FPS, audio: np.ndarray | None = None) -> Path:
    """The frames (an iterable of HxWx3 uint8) with the audio (mono at 48 kHz) muxed in, x264 + AAC like LTX's mp4."""
    path.parent.mkdir(parents=True, exist_ok=True)
    frames = list(frames)
    h, w = frames[0].shape[:2]
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps), "-i", "-"]
    if audio is not None:
        wav = write_wav(path.with_suffix(".src.wav"), audio)
        cmd += ["-i", str(wav), "-c:a", "aac", "-b:a", "192k", "-shortest"]
    cmd += ["-c:v", "libx264", "-crf", "14", "-pix_fmt", "yuv420p", str(path)]
    ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for f in frames:
        ff.stdin.write(np.ascontiguousarray(f).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0
    return path


def moving(n, speed, start=0.0, **kw):
    return [texture(start + speed * i, **kw) for i in range(n)]


def join(clips: list[Path], out: Path, fps=FPS, audio: Path | None = None) -> Path:
    """Hard cuts end to end through the production assembler (``production/assemble.assemble_shot_clips``, G9), the sound
    (``audio``, else the clips' own sounds joined) muxed once."""
    from explainer_engine.production import assemble as ASM
    out.parent.mkdir(parents=True, exist_ok=True)
    recs = [{"shot_id": f"x{i}", "clip_path": str(p), "total_frames": frames_of(p)} for i, p in enumerate(clips)]
    if audio is None:
        from explainer_engine.qa import sound_realism as R
        x = np.concatenate([R.read_audio(p) for p in clips])
        audio = write_wav(out.with_suffix(".mix.wav"), x, rate=R.SR)
    ASM.assemble_shot_clips(recs, [{"transition_type": "hard_cut", "transition_frames": 0}] * (len(recs) - 1), audio, out,
                            fps=fps, size=(W, H), chunk_seconds=600.0)
    return out


def frames_of(p: Path) -> int:
    out = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(p)], capture_output=True, text=True, check=True)
    return int(out.stdout.strip())


# --- a scene script -----------------------------------------------------------------------------------------------------

def scene_script() -> dict:
    lines = [{"line_id": "L1", "speaker_type": "character", "speaker_id": "gen", "text": "Three days and not one Trojan."},
             {"line_id": "L2", "speaker_type": "character", "speaker_id": "cmd", "text": "They are out there, my lord."}]

    def shot(sid, mode, size, az, lines=(), src=None, dur=3.0):
        ep = {"continuity_mode": mode, "cut_in_reason": "action", "scene_master": "A_start", "axis_side": "A"}
        if src:
            ep["continuity_from"] = src
        return {"shot_id": sid, "route": "video", "segment_id": "S1", "location_id": "loc_plain",
                "camera_spec": {"shot_size": size, "horizontal_azimuth_deg": az}, "audio_line_ids": list(lines),
                "target_duration_seconds": dur, "edit_plan": ep, "transition_out": "hard_cut"}
    return {"fps": FPS, "audio_lines": lines,
            "shots": [shot("A", "coverage", "wide", 0), shot("B", "continuation", "wide", 0, src="A"),
                      shot("C", "coverage", "medium", 40, lines=["L1"]), shot("D", "coverage", "medium", -40, lines=["L2"])]}


# --- VL-07 ingest: cut by measured speech, raw kept, 24/30 fps --------------------------------------------------------------

def _ltx_clip(tmp, name, fps, seconds=5.0, line=(0.8, 2.9), speed=1.0, **tex):
    n = int(round(seconds * fps))
    return write_clip(tmp / f"{name}.mp4", moving(n, speed * 24 / fps, **tex), fps=fps,
                      audio=speechy(seconds, [line] if line else []))


@pytest.mark.parametrize("raw_fps", [24, 30])
def test_a_spoken_clip_is_cut_around_its_measured_line_on_the_episode_rate(tmp_path, raw_fps):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    raw = _ltx_clip(tmp_path, "C_raw", raw_fps, line=(0.8, 2.9))
    recs = IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "C", "path": str(raw)}], FPS)
    r = recs[0]
    assert r["clip_spoken"] and r["raw_fps"] == pytest.approx(raw_fps) and r["fps"] == FPS
    s0, s1 = r["speech_raw"][0][0], r["speech_raw"][-1][1]
    assert abs(s0 - 0.8) < 0.15 and abs(s1 - 2.9) < 0.15                  # the gate's own detector heard the line
    assert r["in_s"] <= s0 - IN.HEAD_LEAD[0] + 1 / FPS                     # the first word is never cut
    assert s0 - r["in_s"] <= max(IN.HEAD_LEAD[1], 0) + 1 / FPS + 1e-6      # the dead head (LTX speaks late) is gone
    assert IN.CUT_TAIL[0] - 1 / FPS <= r["out_s"] - s1 <= IN.CUT_TAIL[1] + 1 / FPS
    cut = tmp_path / "ep" / r["clip_path"]
    assert frames_of(cut) == r["frames"] == round((r["out_s"] - r["in_s"]) * FPS)
    pr = IN.probe(cut)
    assert pr["fps"] == pytest.approx(FPS) and abs(pr["audio_duration"] - r["frames"] / FPS) < 0.05   # nothing drifts
    assert r["speech"][0][0] >= IN.HEAD_LEAD[0] - 1 / FPS                  # trimmed seconds: the line starts after the lead
    assert (tmp_path / "ep" / r["raw_path"]).read_bytes() == raw.read_bytes()


def test_mixed_24_and_30_fps_clips_join_without_drift(tmp_path):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    a = _ltx_clip(tmp_path, "C_raw", 24, line=(0.8, 2.6))
    b = _ltx_clip(tmp_path, "D_raw", 30, line=(0.75, 2.4), k=1.3)
    recs = IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "C", "path": str(a)}, {"shot_id": "D", "path": str(b)}], FPS)
    master = join([tmp_path / "ep" / r["clip_path"] for r in recs], tmp_path / "m.mp4")
    pr = IN.probe(master)
    total = sum(r["frames"] for r in recs)
    assert frames_of(master) == total and abs(pr["audio_duration"] - total / FPS) < 0.08


def test_a_spoken_clip_with_no_line_in_its_sound_is_refused_not_trimmed_blind(tmp_path):
    from explainer_engine.videolane import ingest as IN
    raw = _ltx_clip(tmp_path, "C_raw", 24, line=None)
    with pytest.raises(ContractError, match="no speech"):
        IN.ingest_scene(tmp_path / "ep", scene_script(), [{"shot_id": "C", "path": str(raw)}], FPS)


def test_the_raw_clip_is_never_overwritten(tmp_path):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    a = _ltx_clip(tmp_path, "one", 24, line=(0.8, 2.6))
    b = _ltx_clip(tmp_path, "two", 24, line=(0.9, 2.2), k=2.0)
    IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "C", "path": str(a)}], FPS)
    with pytest.raises(ContractError, match="never overwritten"):
        IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "C", "path": str(b)}], FPS)


def test_a_continuation_hands_over_on_one_frame_and_drops_the_repeat(tmp_path):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    for s in doc["shots"][:2]:
        s["target_duration_seconds"] = 2.0
    a = write_clip(tmp_path / "A.mp4", moving(96, 2.0), audio=speechy(4.0, []))
    # B was generated from frame 70 of A (the hand-over), so its frame 0 is A's frame 70
    b = write_clip(tmp_path / "B.mp4", moving(96, 2.0, start=2.0 * 70), audio=speechy(4.0, [], seed=2))
    recs = IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "A", "path": str(a)},
                                                  {"shot_id": "B", "path": str(b), "chain_from_frame": {"frame": 70}}], FPS)
    ra, rb = recs
    assert ra["ends_on_handover"] and round(ra["out_s"] * FPS) == 71              # A ends ON frame 70
    assert round(rb["in_s"] * FPS) >= 1                                          # B drops its frame 0 (= A's frame 70)
    with pytest.raises(ContractError, match="continuation starts from"):
        IN.recut(tmp_path / "ep", ra, ra["frames"] + 5, FPS)


def test_a_narrated_video_shot_is_recut_from_its_raw_clip_never_stretched(tmp_path):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    a = write_clip(tmp_path / "A.mp4", moving(120, 1.0), audio=speechy(5.0, []))
    r = IN.ingest_scene(tmp_path / "ep", doc, [{"shot_id": "A", "path": str(a)}], FPS)[0]
    assert r["frames"] == 72
    longer = IN.recut(tmp_path / "ep", r, 96, FPS)
    assert longer["frames"] == 96 and frames_of(tmp_path / "ep" / longer["clip_path"]) == 96
    with pytest.raises(ContractError, match="never stretched"):
        IN.recut(tmp_path / "ep", r, 200, FPS)


# --- VL-11 cuts on the real frames -------------------------------------------------------------------------------------------

def _cut_master(tmp, a_frames, b_frames, name="m"):
    a = write_clip(tmp / f"{name}_a.mp4", a_frames, audio=speechy(len(a_frames) / FPS, []))
    b = write_clip(tmp / f"{name}_b.mp4", b_frames, audio=speechy(len(b_frames) / FPS, [], seed=3))
    return join([a, b], tmp / f"{name}.mp4"), [{"shot_id": "A", "total_frames": len(a_frames)},
                                               {"shot_id": "B", "total_frames": len(b_frames)}]


def _two(mode):
    doc = scene_script()
    doc["shots"] = doc["shots"][:2]
    doc["shots"][1]["edit_plan"]["continuity_mode"] = mode
    return doc


def test_a_continuation_that_keeps_moving_passes_and_a_reversal_or_jump_fails(tmp_path):
    from explainer_engine.videolane import cuts as CU
    good, recs = _cut_master(tmp_path, moving(36, 2.0), moving(36, 2.0, start=72.0), "good")
    c = CU.check_master(good, recs, _two("continuation"), FPS)["cuts"][0]
    assert c["status"] == G.PASS and c["dx_out"] < -CU.FLOW_MIN and c["dx_in"] < -CU.FLOW_MIN, c   # the pan carries on
    back, recs = _cut_master(tmp_path, moving(36, 2.0), moving(36, -2.0, start=72.0), "back")
    c = CU.check_master(back, recs, _two("continuation"), FPS)["cuts"][0]
    assert c["status"] == G.FAIL and "reverses" in " ".join(c["why"]), c
    jump, recs = _cut_master(tmp_path, moving(36, 2.0), moving(36, 2.0, k=2.5, fx=9.0), "jump")
    c = CU.check_master(jump, recs, _two("continuation"), FPS)["cuts"][0]
    assert c["status"] == G.FAIL and "jumps" in " ".join(c["why"]), c


def test_a_coverage_cut_to_a_new_angle_passes_and_the_same_picture_twice_fails(tmp_path):
    from explainer_engine.videolane import cuts as CU
    ok, recs = _cut_master(tmp_path, moving(36, 0.5), moving(36, 0.5, k=2.2, fx=15.0), "cov")
    c = CU.check_master(ok, recs, _two("coverage"), FPS)["cuts"][0]
    assert c["status"] in (G.PASS, G.REVIEW) and c["diff"] >= CU.SAME_DIFF_MIN, c
    same, recs = _cut_master(tmp_path, moving(36, 0.0), moving(36, 0.0), "same")
    c = CU.check_master(same, recs, _two("coverage"), FPS)["cuts"][0]
    assert c["status"] == G.FAIL and "jump cut" in " ".join(c["why"]), c


def test_a_coverage_cut_to_another_place_is_review(tmp_path):
    from explainer_engine.videolane import cuts as CU
    m, recs = _cut_master(tmp_path, moving(36, 0.5), moving(36, 0.5, k=1.0, tint=(0.2, 1.0, 0.3)), "place")
    res = CU.check_master(m, recs, _two("coverage"), FPS)
    assert res["cuts"][0]["status"] == G.REVIEW
    assert {r["gate"]: r["status"] for r in res["rows"]}["cuts_place_holds"] == G.REVIEW
    sheet = CU.boundary_sheet(m, res["cuts"], tmp_path / "cuts.jpg")
    assert sheet.is_file() and sheet.stat().st_size > 1000


# --- VL-12 the master as a file ----------------------------------------------------------------------------------------------

def _qa_episode(tmp, shots_frames, *, master_clips=None, bed=None, voice=None, mute_audio=False, sound_plan=True):
    """An episode folder with records, per-shot clips, a master joined from ``master_clips`` (default: the clips in order),
    the ambience and narration stems. ``shots_frames``: [(shot_id, frames list)]."""
    root = tmp / "ep"
    clips, records = [], []
    for sid, fr in shots_frames:
        p = write_clip(root / "production" / "video" / "cut" / f"{sid}.mp4", fr, audio=speechy(len(fr) / FPS, []))
        clips.append(p)
        records.append({"shot_id": sid, "total_frames": len(fr), "clip_path": str(p)})
    total = sum(len(f) for _, f in shots_frames) / FPS
    bed = bed if bed is not None else speechy(total, [], room=0.02, seed=9)
    voice = voice if voice is not None else np.zeros(int(total * RATE), np.float32)
    mix = write_wav(root / "audio" / "stems" / "mix.wav", bed + voice)
    master = join(master_clips or clips, root / "renders" / "m.mp4", audio=mix)
    if mute_audio:
        silent = root / "renders" / "m_silent.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(master), "-an", "-c:v", "copy", str(silent)], check=True)
        master = silent
    stems = root / "audio" / "stems"
    write_wav(stems / "ambience.wav", bed)
    write_wav(stems / "narration.wav", voice)
    plan = {"beds": [{"bed_id": "BED_01_loc_plain", "start_s": 0.0, "end_s": total,
                      "shot_ids": [s for s, _ in shots_frames]}]} if sound_plan else None
    return root, records, master, plan


def _rows(res):
    return {r["gate"]: r["status"] for r in res["rows"]}


def test_a_clean_master_passes_the_file_checks(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    doc = scene_script()
    shots = [("A", moving(36, 2.0)), ("B", moving(36, 2.0, start=72.0)), ("C", moving(36, 0.6, k=2.2, fx=15.0)),
             ("D", moving(36, 0.6, k=4.0, fx=31.0))]
    voice = speechy(6.0, [(3.2, 4.3), (4.7, 5.8)], seed=8)               # C and D speak their lines in their windows
    root, recs, master, plan = _qa_episode(tmp_path, shots, voice=voice)
    res = VM.check(root, doc, recs, master, FPS, sound_plan=plan)
    rows = _rows(res)
    for g in ("master_container", "master_frames_match_the_plan", "video_shots_not_black_or_frozen", "video_shots_in_order",
              "cuts_continuation_and_coverage", "bed_continuous_in_its_place", "master_has_no_dead_air",
              "dialogue_heard_in_its_shot"):
        assert rows[g] == G.PASS, (g, [r for r in res["rows"] if r["gate"] == g])
    assert (root / "qa" / "video_master_qa.json").is_file() and (root / "qa" / "cut_boundaries.jpg").is_file()
    assert res["repairs"] == []


FAULTS = {   # name -> (how the master is broken, the row that must FAIL, the repair class it gets)
    "frozen video shot": (lambda s: s.__setitem__(2, ("C", [texture(5.0, k=2.2, fx=15.0)] * 36)),
                          "video_shots_not_black_or_frozen", "C"),
    "black frames in a video shot": (lambda s: s.__setitem__(3, ("D", moving(18, 0.6, k=4.0, fx=31.0)
                                                                + [np.zeros((H, W, 3), np.uint8)] * 18)),
                                     "video_shots_not_black_or_frozen", "C"),
}


@pytest.mark.parametrize("name", sorted(FAULTS))
def test_a_broken_video_shot_fails_with_its_repair_class(tmp_path, name):
    from explainer_engine.videolane import master_qa as VM
    breaker, row, cls = FAULTS[name]
    shots = [("A", moving(36, 2.0)), ("B", moving(36, 2.0, start=72.0)), ("C", moving(36, 0.6, k=2.2, fx=15.0)),
             ("D", moving(36, 0.6, k=4.0, fx=31.0))]
    breaker(shots)
    root, recs, master, plan = _qa_episode(tmp_path, shots)
    res = VM.check(root, scene_script(), recs, master, FPS, sound_plan=plan)
    assert _rows(res)[row] == G.FAIL
    assert any(r["row"] == row and r["class"] == cls for r in res["repairs"])


def test_a_master_without_sound_or_with_missing_frames_fails(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    shots = [("A", moving(36, 2.0)), ("B", moving(36, 2.0, start=72.0))]
    doc = scene_script()
    doc["shots"] = doc["shots"][:2]
    root, recs, master, plan = _qa_episode(tmp_path, shots, mute_audio=True)
    res = VM.check(root, doc, recs, master, FPS, sound_plan=plan)
    assert _rows(res)["master_container"] == G.FAIL and _rows(res)["master_has_no_dead_air"] == G.FAIL
    recs2 = [dict(recs[0]), dict(recs[1], total_frames=48)]                  # the plan says 12 frames more than the file
    root2, _, master2, plan2 = _qa_episode(tmp_path / "two", shots)
    res2 = VM.check(root2, doc, recs2, master2, FPS, sound_plan=plan2)
    assert _rows(res2)["master_frames_match_the_plan"] == G.FAIL
    assert any(r["class"] == "A" and r["row"] == "master_frames_match_the_plan" for r in res2["repairs"])


def test_swapped_clips_are_caught_by_the_shot_order_check(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    shots = [("A", moving(36, 2.0)), ("B", moving(36, 2.0, start=72.0)), ("C", moving(36, 0.6, k=2.2, fx=15.0)),
             ("D", moving(36, 0.6, k=4.0, fx=31.0))]
    root = tmp_path / "ep"
    paths = {sid: root / "production" / "video" / "cut" / f"{sid}.mp4" for sid, _ in shots}
    root, recs, master, plan = _qa_episode(tmp_path, shots, master_clips=None)
    swapped = join([paths["A"], paths["B"], paths["D"], paths["C"]], root / "renders" / "swapped.mp4")
    res = VM.check(root, scene_script(), recs, swapped, FPS, sound_plan=plan)
    assert _rows(res)["video_shots_in_order"] == G.FAIL
    bad = [m for m in [r for r in res["rows"] if r["gate"] == "video_shots_in_order"][0]["measured"]]
    assert any(b.startswith("C:") for b in bad) and any(b.startswith("D:") for b in bad)


# --- the mandatory battlefield-ambience test (prompt section 15) ------------------------------------------------------------

def _battlefield(total_s, shot_s, *, drop_shot=None):
    """A battlefield bed (low rumble + distant clash noise) through three shots of one place, ducked 6 dB under two lines of
    dialogue (BP-52, the stems' BED_DUCK_DB), never muted; ``drop_shot`` k zeroes the bed inside shot k (the regression)."""
    rng = np.random.default_rng(11)
    n = int(total_s * RATE)
    t = np.arange(n) / RATE
    bed = 0.03 * rng.normal(0, 1, n) * (0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t)) + 0.02 * np.sin(2 * np.pi * 55 * t)
    voice = speechy(total_s, [(shot_s + 0.4, 2 * shot_s - 0.5), (2 * shot_s + 0.4, 3 * shot_s - 0.6)], seed=4)
    duck = np.ones(n, np.float32)
    for a, b in [(shot_s + 0.4, 2 * shot_s - 0.5), (2 * shot_s + 0.4, 3 * shot_s - 0.6)]:
        duck[int(a * RATE):int(b * RATE)] = 10 ** (-6 / 20)
    k = int(0.05 * RATE)                                  # the duck's attack and release (a gain ramp, not a switch)
    duck = np.convolve(duck, np.ones(k) / k, mode="same")
    bed = (bed * duck).astype(np.float32)
    if drop_shot is not None:
        bed[int(drop_shot * shot_s * RATE):int((drop_shot + 1) * shot_s * RATE)] = 0.0
    return bed, voice


def _battle_episode(tmp, drop_shot=None):
    from explainer_engine.videolane import ingest as IN
    doc = scene_script()
    doc["shots"] = [doc["shots"][0], doc["shots"][2], doc["shots"][3]]          # wide, then the general, then the commander
    doc["shots"][1]["edit_plan"]["continuity_mode"] = "coverage"
    shot_s = 3.0
    shots = [("A", moving(72, 1.5)), ("C", moving(72, 0.6, k=2.2, fx=15.0)), ("D", moving(72, 0.6, k=4.0, fx=31.0))]
    bed, voice = _battlefield(3 * shot_s, shot_s, drop_shot=drop_shot)
    root, recs, master, plan = _qa_episode(tmp, shots, bed=bed, voice=voice)
    for sid, line in (("C", (0.4, shot_s - 0.5)), ("D", (0.4, shot_s - 0.6))):   # the clip records hold the trimmed speech
        IN.write_json_atomic(root / "production" / "video" / f"{sid}.json",
                             {"shot_id": sid, "speech": [list(line)], "raw_path": "", "raw_seconds": shot_s, "out_s": shot_s})
    voice_rep = {"laid": [{"what": "clip", "shot_id": "C", "at_s": 3.0}, {"what": "clip", "shot_id": "D", "at_s": 6.0}]}
    return root, doc, recs, master, plan, voice_rep


def test_battlefield_ambience_runs_under_the_dialogue_across_every_cut(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    root, doc, recs, master, plan, voice_rep = _battle_episode(tmp_path)
    res = VM.check(root, doc, recs, master, FPS, sound_plan=plan, voice_report=voice_rep)
    rows = _rows(res)
    assert rows["bed_continuous_in_its_place"] == G.PASS, res["metrics"]["bed"]
    assert rows["dialogue_heard_in_its_shot"] == G.PASS and rows["dialogue_laid_once"] == G.PASS, res["metrics"].get("dialogue")
    assert rows["bed_level_holds_at_cuts"] in (G.PASS, G.REVIEW)
    bed = res["metrics"]["bed"][0]
    assert bed["min_db"] > -50.0                                    # ducked under the lines, never muted (BP-52, BP-189)


def test_battlefield_ambience_removed_in_shot_b_fails(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    root, doc, recs, master, plan, voice_rep = _battle_episode(tmp_path, drop_shot=1)
    res = VM.check(root, doc, recs, master, FPS, sound_plan=plan, voice_report=voice_rep)
    row = next(r for r in res["rows"] if r["gate"] == "bed_continuous_in_its_place")
    assert row["status"] == G.FAIL and "shot C" in row["measured"][0]
    assert any(r["row"] == "bed_continuous_in_its_place" and r["class"] == "B" for r in res["repairs"])


def test_a_line_laid_twice_or_not_heard_fails(tmp_path):
    from explainer_engine.videolane import master_qa as VM
    root, doc, recs, master, plan, voice_rep = _battle_episode(tmp_path)
    twice = {"laid": voice_rep["laid"] + [{"what": "clip", "shot_id": "C", "at_s": 3.0}]}
    assert _rows(VM.check(root, doc, recs, master, FPS, sound_plan=plan, voice_report=twice))["dialogue_laid_once"] == G.FAIL
    under = {"laid": voice_rep["laid"] + [{"what": "read", "read_s": [0.0, 4.0], "at_s": 2.0}]}
    assert _rows(VM.check(root, doc, recs, master, FPS, sound_plan=plan, voice_report=under))["dialogue_laid_once"] == G.FAIL
    write_wav(root / "audio" / "stems" / "narration.wav", np.zeros(9 * RATE, np.float32))
    res = VM.check(root, doc, recs, master, FPS, sound_plan=plan, voice_report=voice_rep)
    assert _rows(res)["dialogue_heard_in_its_shot"] == G.FAIL


# --- end to end: LTX clips through the runner's real stages ------------------------------------------------------------------

def test_ltx_clips_go_through_the_runner_timed_voiced_assembled_and_measured(tmp_path, monkeypatch):
    """A Toba scene (narrator wide, then two clip-spoken LTX shots): fake LTX clips with late lines are ingested, the runner
    times the clip shots by their cuts, lays the dialogue once in the voice track, assembles and measures the master. The
    pictures never went through intake, so the chain is a rehearsal (its QA never passes); everything else is measured."""
    import copy

    from PIL import Image

    from explainer_engine.episode import run as RUN
    from explainer_engine.episode import timing as TM
    from explainer_engine.videolane import ingest as IN
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    toba = Path(__file__).resolve().parents[2] / "episodes" / "ep_toba"
    doc = json.loads((toba / "story" / "production_script.json").read_text(encoding="utf-8"))
    by = {s["shot_id"]: s for s in doc["shots"]}
    ids = ("S05_SH001", "S05_SH002", "S05_SH005")
    doc["shots"] = [dict(copy.deepcopy(by[s]), target_duration_seconds=d) for s, d in zip(ids, (2.0, 3.0, 3.0))]
    doc["shots"][2]["camera_spec"]["horizontal_azimuth_deg"] = -45        # a reverse angle, not the same set-up again
    for s, mode, reason in ((doc["shots"][1], "coverage", "line"), (doc["shots"][2], "coverage", "line")):
        s["edit_plan"] = {"continuity_mode": mode, "cut_in_reason": reason, "scene_master": "S05_SH001_start",
                          "axis_side": "A"}
    keep = {l for s in doc["shots"] for l in s.get("audio_line_ids") or []}
    doc["audio_lines"] = [l for l in doc["audio_lines"] if l["line_id"] in keep]
    doc["segments"] = [g for g in doc["segments"] if g["segment_id"] == "S05"]
    root = tmp_path / "ep_toba"
    (root / "story").mkdir(parents=True)
    (root / "episode.json").write_text((toba / "episode.json").read_text())
    (root / "story" / "production_script.json").write_text(json.dumps(doc))
    img = root / "assets" / "generated" / "images"
    img.mkdir(parents=True)
    rng = np.random.default_rng(3)
    for s in doc["shots"]:
        a = np.zeros((216, 384, 3), np.uint8)
        a[:110], a[110:] = (90, 120, 160), (110, 90, 60)
        Image.fromarray(np.clip(a + rng.integers(0, 40, a.shape), 0, 255).astype(np.uint8)).save(img / f"{s['shot_id']}_start.png")
    # the narrator's read (one line) and its transcript
    lines = {l["line_id"]: l for l in doc["audio_lines"]}
    order = TM.read_order(doc)
    assert order == ["S05_L001"]
    words, t = [], 0.2
    for w in lines["S05_L001"]["text"].split():
        words.append({"text": w, "start": round(t, 3), "end": round(t + 0.06, 3), "type": "word"})
        t += 0.07
    (root / "audio").mkdir()
    write_wav(root / "audio" / "narration.wav", speechy(t + 0.4, [(0.2, t)], seed=5))
    (root / "audio" / "narration.scribe.json").write_text(json.dumps({"words": words}))
    # the LTX clips (1280x704 is the model's; small here), lines starting late like LTX's
    clips = []
    for k, s in enumerate(doc["shots"][1:]):
        raw = write_clip(tmp_path / f"{s['shot_id']}_ltx.mp4", moving(144, 0.8, k=1.5 * k, fx=15.0 + 8 * k), fps=24,
                         audio=speechy(6.0, [(0.8, 2.6 + 0.3 * k)], seed=6 + k))
        clips.append({"shot_id": s["shot_id"], "path": str(raw)})
    recs = IN.ingest_scene(root, doc, clips, FPS)
    ep = RUN.Episode(root, size=(192, 108), rehearsal=True, chunk_seconds=2.0)
    out = {r["stage"]: r for r in RUN.run_to(ep, "qa")}
    assert list(out) == list(RUN.STAGES)
    g1 = {r["gate"]: r["status"] for r in out["script"]["rows"]}
    assert g1["video_edit_plan"] == G.PASS
    g6 = {r["gate"]: r["status"] for r in out["voice"]["rows"]}
    assert g6["clip_spoken_shots_timed_by_their_clips"] == G.PASS
    timing = json.loads((root / "audio" / "timing.json").read_text())
    assert timing["clip_timed"] == ["S05_SH002", "S05_SH005"]
    for r in recs:
        assert timing["shots"][r["shot_id"]]["frames"] == r["frames"]          # the clip's cut is the shot's length
    shots = json.loads((root / "production" / "shot_records.json").read_text())["shots"]
    assert all(s["provider"].startswith("wan:ltx") for s in shots if s["route"] == "video")    # the LTX cut, no fallback
    voice = json.loads((root / "audio" / "voice_track.json").read_text())
    assert sorted(e["shot_id"] for e in voice["laid"] if e["what"] == "clip") == ["S05_SH002", "S05_SH005"]
    vm = json.loads((root / "qa" / "video_master_qa.json").read_text())
    rows = {r["gate"]: r["status"] for r in vm["rows"]}
    assert rows["master_frames_match_the_plan"] == G.PASS and rows["video_shots_in_order"] == G.PASS
    assert rows["dialogue_heard_in_its_shot"] == G.PASS and rows["dialogue_laid_once"] == G.PASS, vm["metrics"].get("dialogue")
    qa = out["qa"]
    assert qa["verdict"]["status"] == G.FAIL and {r["gate"]: r["status"] for r in qa["rows"]}["not_a_rehearsal"] == G.FAIL
