"""The video lane (VL-01..VL-13, docs/VIDEO_LANE.md, D-137): the shot edit plan, the clip-timed clock, the voice track, the
storyboard gate, the paid scene file and the worker's hand-over frame. Media-level checks of real frames and sound are in
test_videolane_media.py."""
from __future__ import annotations

import copy
import json
import subprocess
import wave
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.episode import timing as TM
from explainer_engine.qa import gates as G
from explainer_engine.videolane import plan as P

ROOT = Path(__file__).resolve().parents[2]
FPS = 24


def _shot(sid, *, route="video", size="medium", az=0, lines=(), mode="coverage", src=None, dur=3.0, **ep):
    plan = {"continuity_mode": mode, "cut_in_reason": ep.pop("cut_in_reason", "line"), "scene_master": "S1_master"}
    if src:
        plan["continuity_from"] = src
    plan.update(ep)
    return {"shot_id": sid, "route": route, "segment_id": "S1", "location_id": "loc_plain",
            "camera_spec": {"shot_size": size, "horizontal_azimuth_deg": az}, "audio_line_ids": list(lines),
            "target_duration_seconds": dur, "edit_plan": plan, "transition_out": "hard_cut",
            "video_prompt": {"motion_prompt": f"motion of {sid}, one action", "primary_action_count": 1,
                             "camera_move_count": 0}}


def _scene() -> dict:
    """A good scene: an establishing wide, its continuation, a medium coverage with a line, a reaction insert, a reverse."""
    lines = [{"line_id": "L1", "speaker_type": "character", "speaker_id": "gen", "text": "Three days and not one Trojan."},
             {"line_id": "L2", "speaker_type": "character", "speaker_id": "cmd", "text": "They are out there, my lord."},
             {"line_id": "L3", "speaker_type": "narrator", "speaker_id": "narrator_main", "text": "The plain was empty."}]
    shots = [_shot("A", size="wide", lines=["L3"], cut_in_reason="establish", screen_direction="left_to_right",
                   camera_out="track_right", axis_side="A", screen_positions={"gen": "left", "cmd": "right"}),
             _shot("B", size="wide", mode="continuation", src="A", cut_in_reason="action", screen_direction="left_to_right",
                   camera_in="track_right", axis_side="A"),
             _shot("C", size="medium", az=40, lines=["L1"], axis_side="A", screen_positions={"gen": "left", "cmd": "right"}),
             _shot("D", route="still_25d", size="close_up", az=60, mode="insert", cut_in_reason="reaction"),
             _shot("E", size="medium", az=-40, lines=["L2"], axis_side="A", screen_positions={"gen": "left", "cmd": "right"})]
    cast = {"characters": [   # FA-02: the voice-caster's voice descriptions feed the LTX prompt composer
        {"character_id": "gen", "name": "The General", "voice_description": "a hoarse older man, low and slow, a dry Argive accent",
         "voice_card": {"age": "older", "timbre": "hoarse", "pace": "slow", "accent": "a dry Argive accent"}},   # Q5
        {"character_id": "cmd", "name": "The Commander", "voice_description": "a firm younger man, clipped and quick, a plain Ithacan accent",
         "voice_card": {"age": "younger", "timbre": "firm", "pace": "clipped and quick", "accent": "a plain Ithacan accent"}}]}
    return {"shots": shots, "audio_lines": lines, "fps": FPS, "world_bible": cast}


def _fails(doc, rule=None):
    return [f for f in P.findings(doc) if f["severity"] == G.FAIL and (rule is None or f["rule"] == rule)]


def test_a_good_scene_passes_the_edit_plan():
    doc = _scene()
    assert _fails(doc) == []
    rows = {r["gate"]: r["status"] for r in P.rows(doc)}
    assert rows["video_edit_plan"] == G.PASS
    assert P.clip_spoken(doc) == {"C", "E"}                      # the narrator's line in A is the read's, not the clip's


def _mut(fn):
    def apply(doc):
        fn({s["shot_id"]: s for s in doc["shots"]}, doc)
        return doc
    return apply


MUTATIONS = [   # each breaks one rule of a passing scene; the rule must catch it (mutation tests, prompt section 15)
    ("no edit plan", _mut(lambda s, d: s["C"].pop("edit_plan")), "VL-01"),
    ("unknown mode", _mut(lambda s, d: s["C"]["edit_plan"].update(continuity_mode="montage")), "VL-01"),
    ("two lines in one clip", _mut(lambda s, d: s["C"]["audio_line_ids"].append("L2") or s["E"].update(audio_line_ids=[])),
     "VL-02"),
    ("speaking close-up", _mut(lambda s, d: s["C"]["camera_spec"].update(shot_size="close_up")), "VL-02"),
    ("continuation of a shot that is not the one before", _mut(lambda s, d: s["B"]["edit_plan"].update(continuity_from="C")),
     "VL-03"),
    ("continuation reverses screen direction", _mut(lambda s, d: s["B"]["edit_plan"].update(screen_direction="right_to_left")),
     "VL-03"),
    ("continuation drops the camera move", _mut(lambda s, d: s["B"]["edit_plan"].update(camera_in="rest")), "VL-03"),
    ("coverage without a scene master", _mut(lambda s, d: s["C"]["edit_plan"].pop("scene_master")), "VL-04"),
    ("coverage with no size step and 10 degrees", _mut(lambda s, d: s["E"]["camera_spec"].update(
        shot_size="medium", horizontal_azimuth_deg=-10) or s["D"].update(route="video", camera_spec={
            "shot_size": "medium", "horizontal_azimuth_deg": 0}) or s["D"]["edit_plan"].update(continuity_mode="coverage")),
     "VL-04"),
    ("axis crossed without a reason", _mut(lambda s, d: s["E"]["edit_plan"].update(axis_side="B")), "VL-04"),
    ("a character swaps screen side", _mut(lambda s, d: s["C"]["edit_plan"].update(
        screen_positions={"gen": "right", "cmd": "left"})), "VL-04"),
    ("a line longer than one clip", _mut(lambda s, d: d["audio_lines"][0].update(text=" ".join(["word"] * 40))), "VL-06"),
]


@pytest.mark.parametrize("name,mutate,rule", MUTATIONS, ids=[m[0] for m in MUTATIONS])
def test_every_broken_rule_is_caught(name, mutate, rule):
    doc = mutate(copy.deepcopy(_scene()))
    got = _fails(doc, rule)
    assert got, f"{name}: no {rule} FAIL in {P.findings(doc)}"
    assert {r["gate"]: r["status"] for r in P.rows(doc)}["video_edit_plan"] == G.FAIL


def test_an_axis_cross_with_its_reason_passes():
    doc = _scene()
    doc["shots"][4]["edit_plan"].update(axis_side="B", axis_cross_reason="the general walks around the chariot on screen")
    assert _fails(doc, "VL-04") == []


def test_four_lines_without_a_reaction_is_review_not_fail():
    doc = _scene()
    doc["shots"] = [s for s in doc["shots"] if s["shot_id"] != "D"]
    for k in range(3):
        sid = f"X{k}"
        doc["audio_lines"].append({"line_id": f"LX{k}", "speaker_type": "character", "speaker_id": "gen", "text": "Go on now."})
        doc["shots"].append(_shot(sid, size=("medium_wide", "medium", "medium_close_up")[k], az=40 * (k % 2) - 20,
                                  lines=[f"LX{k}"], axis_side="A"))
    fs = P.findings(doc)
    assert any(f["rule"] == "VL-08" and f["severity"] == G.REVIEW for f in fs)


def test_clip_seconds_come_from_the_line_not_a_fixed_ten():
    doc = _scene()
    c = next(s for s in doc["shots"] if s["shot_id"] == "C")
    got = P.clip_seconds(doc, c, 10.0)
    words = len(doc["audio_lines"][0]["text"].split())
    need = P.SPEECH_ONSET_S + words / P.WORDS_PER_S + P.TAIL_S + float(P.CUT_TAIL[1])
    assert got["basis"] == "line" and abs(got["needed_s"] - need) < 1e-3
    assert got["seconds"] == -(-need * 4 // 1) / 4 and got["seconds"] < 10.0 and not got["over"]
    silent = next(s for s in doc["shots"] if s["shot_id"] == "B")
    assert P.clip_seconds(doc, silent, 10.0)["basis"] == "planned_length"


def test_the_schema_takes_an_edit_plan_and_refuses_a_bad_one():
    import jsonschema
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text())
    shot_schema = dict(schema["$defs"]["ShotSpec"]["properties"]["edit_plan"], **{"$defs": schema["$defs"]})
    v = jsonschema.Draft202012Validator(shot_schema)
    good = {"continuity_mode": "continuation", "continuity_from": "S01_SH001", "cut_in_reason": "action",
            "continue_frame": {"pick": "best_tail", "window_s": 0.75, "crop": [0.1, 0.1, 0.9, 0.9]},
            "camera_in": "push", "head_handle_s": 0.25, "tail_handle_s": 0.5}
    assert list(v.iter_errors(good)) == []
    assert list(v.iter_errors(dict(good, continuity_mode="montage")))
    assert list(v.iter_errors({"cut_in_reason": "line"}))          # the mode is required


# --- the clip-timed clock --------------------------------------------------------------------------------------------------

def _toba(ids, durs):
    doc = json.loads((ROOT / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    by = {s["shot_id"]: s for s in doc["shots"]}
    doc["shots"] = [dict(copy.deepcopy(by[s]), target_duration_seconds=d) for s, d in zip(ids, durs)]
    keep = {l for s in doc["shots"] for l in s.get("audio_line_ids") or []}
    doc["audio_lines"] = [l for l in doc["audio_lines"] if l["line_id"] in keep]
    return doc


def _transcript(doc, starts, word_s=0.12, gap=0.03):
    lines = {l["line_id"]: l for l in doc["audio_lines"]}
    words, spans = [], []
    for lid, t in zip(TM.read_order(doc), starts):
        a = t
        for w in lines[lid]["text"].split():
            words.append({"text": w, "start": round(t, 3), "end": round(t + word_s, 3), "type": "word"})
            t += word_s + gap
        spans.append((a, t - gap))
    return {"words": words}, spans


def test_the_read_skips_clip_lines_and_the_clock_inserts_each_clip():
    doc = _toba(("S05_SH001", "S05_SH002", "S05_SH007"), (3.0, 4.0, 3.0))
    assert P.clip_spoken(doc) == {"S05_SH002"}
    order = TM.read_order(doc)
    assert "S05_L002" not in order and order == ["S05_L001", "S05_L007"]
    tr, spans = _transcript(doc, [0.2, 4.0], word_s=0.08, gap=0.01)
    read_s = spans[-1][1] + 0.5
    aligned = TM.align_read(doc, tr, read_s)
    clips = {"S05_SH002": {"frames": 77, "speech": [[0.2, 2.9]]}}
    tm = TM.retime_with_clips(doc, aligned, FPS, read_s, clips)
    base = TM.retime(dict(doc, shots=[doc["shots"][0], doc["shots"][2]]), aligned, FPS, read_s)
    a, b, c = (tm["shots"][s["shot_id"]] for s in doc["shots"])
    assert b["timed_by"] == "clip" and b["frames"] == 77
    assert b["start_frame"] == a["start_frame"] + a["frames"] == base["shots"]["S05_SH007"]["start_frame"]
    assert c["start_frame"] == b["start_frame"] + 77 and tm["total_frames"] == base["total_frames"] + 77
    assert tm["inserts"] == [{"shot_id": "S05_SH002", "at_read_frame": b["start_frame"], "frames": 77}]
    sp = tm["spines"]["S05_SH002"]
    assert sp and all(w["estimated"] for w in sp) and sp[0]["start_frame"] == round(0.2 * FPS)
    timed = TM.timed_script(doc, tm)
    assert round(timed["shots"][1]["target_duration_seconds"] * FPS) == 77


def test_a_scene_spoken_only_by_clips_needs_no_read():
    doc = _toba(("S05_SH002", "S05_SH005"), (4.0, 3.0))
    assert TM.read_order(doc) == []
    tm = TM.retime_with_clips(doc, None, FPS, 0.0, {"S05_SH002": {"frames": 60, "speech": []},
                                                    "S05_SH005": {"frames": 50, "speech": [[0.3, 1.5]]}})
    assert tm["total_frames"] == 110 and [i["at_read_frame"] for i in tm["inserts"]] == [0, 0]
    assert tm["shots"]["S05_SH005"]["start_frame"] == 60


def test_clip_timings_for_an_unknown_shot_are_refused():
    doc = _toba(("S05_SH002",), (4.0,))
    with pytest.raises(ContractError, match="does not have"):
        TM.retime_with_clips(doc, None, FPS, 0.0, {"S99_SH001": {"frames": 3, "speech": []}})


# --- the voice track -------------------------------------------------------------------------------------------------------

def _wav(path, x, rate=48000):
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype("<i2").tobytes())
    return path


def _tone(seconds, hz, amp, rate=48000):
    t = np.arange(int(seconds * rate)) / rate
    return (amp * np.sin(2 * np.pi * hz * t)).astype(np.float32)


def test_the_voice_track_lays_each_clip_once_and_splits_the_read_around_it(tmp_path):
    from explainer_engine.videolane import voice as VV
    rate = 48000
    read = _wav(tmp_path / "read.wav", np.concatenate([_tone(1.0, 300, 0.2), _tone(1.0, 500, 0.2)]))
    clip = _wav(tmp_path / "clip.wav", np.concatenate([np.zeros(int(0.25 * rate)), _tone(1.0, 900, 0.02),
                                                         np.zeros(int(0.25 * rate))]))
    timing = {"fps": FPS, "total_frames": 3 * FPS, "inserts": [{"shot_id": "C", "at_read_frame": FPS, "frames": FPS + 12}],
              "shots": {"A": {"start_frame": 0}, "C": {"start_frame": FPS}, "E": {"start_frame": 2 * FPS + 12}}}
    rep = VV.compose(timing, read, {"C": {"path": str(clip), "speech": [[0.25, 1.25]]}}, tmp_path / "v.wav",
                     read_speech=[[0.0, 2.0]])
    y = VV.read_mono(tmp_path / "v.wav")
    assert len(y) == 3 * rate

    def power_at(x, hz, a, b):
        seg = x[int(a * rate):int(b * rate)]
        f = np.fft.rfftfreq(len(seg), 1 / rate)
        s = np.abs(np.fft.rfft(seg))
        return float(s[np.argmin(np.abs(f - hz))])
    assert power_at(y, 300, 0.1, 0.9) > 10 * power_at(y, 300, 1.1, 2.4)          # the read pauses for the clip
    assert power_at(y, 900, 1.3, 2.2) > 10 * power_at(y, 900, 0.0, 1.0)          # the clip's line is where its picture is
    assert power_at(y, 500, 2.6, 2.95) > 10 * power_at(y, 500, 1.3, 2.2)        # the read goes on after it, shifted
    clips = [e for e in rep["laid"] if e["what"] == "clip"]
    assert len(clips) == 1 and clips[0]["at_s"] == 1.0
    assert clips[0]["gain_db"] == VV.GAIN_MAX_DB                                 # 20 dB quieter: clamped, not boosted blind


def test_a_clip_timed_shot_without_its_sound_is_refused(tmp_path):
    from explainer_engine.videolane import voice as VV
    timing = {"fps": FPS, "total_frames": FPS, "inserts": [{"shot_id": "C", "at_read_frame": 0, "frames": FPS}],
              "shots": {"C": {"start_frame": 0}}}
    with pytest.raises(ContractError, match="without its clip sound"):
        VV.compose(timing, None, {}, tmp_path / "v.wav")


# --- the storyboard gate and the paid scene file -----------------------------------------------------------------------------

def _pic(path, seed, tone=(90, 120, 160)):
    rng = np.random.default_rng(seed)
    a = np.zeros((180, 320, 3), np.uint8)
    hz = int(rng.integers(40, 130))                          # every shot frames the place differently
    a[:hz] = tone
    a[hz:] = (110, 90, 60)
    x0, w, y0 = int(rng.integers(10, 250)), int(rng.integers(30, 70)), int(rng.integers(20, 100))
    a[y0:y0 + 70, x0:x0 + w] = (200, 60, 40)                 # a figure in a different place and size in every shot
    a = np.clip(a.astype(int) + rng.integers(0, 12, a.shape), 0, 255).astype(np.uint8)
    Image.fromarray(a).save(path)
    return path


def _board_episode(tmp_path, doc):
    root = tmp_path / "ep"
    (root / "assets").mkdir(parents=True)
    pics = {}
    for k, s in enumerate(doc["shots"]):
        if (s.get("edit_plan") or {}).get("continuity_mode") != "continuation":
            p = _pic(root / "assets" / f"{s['shot_id']}.png", seed=k * 7 + 1)
            pics[f"{s['shot_id']}_start"] = {"file": f"assets/{s['shot_id']}.png"}
    pics["S1_master"] = {"file": "assets/A.png"}
    (root / "production").mkdir()
    (root / "production" / "pictures.json").write_text(json.dumps({"pictures": pics}))
    return root, pics


LINE_S = 2.1   # the measured speech of a clip line in the fixture (Q4)


def _reads(root, doc, shot_s=3.2):
    """Q4 (the creator 2026-11-13, D-138): the measured read every paid LTX scene needs: the narration's shot lengths in
    audio/timing.json and every clip line's read in audio/line_reads.json (a file whose sha256 matches the record)."""
    import hashlib
    from explainer_engine.videolane import line_reads as LR
    from explainer_engine.videolane import plan as VP
    spoken = VP.clip_spoken(doc)
    (root / "audio").mkdir(parents=True, exist_ok=True)
    (root / "audio" / "timing.json").write_text(json.dumps({"shots": {s["shot_id"]: {"seconds": shot_s}
                                                                       for s in doc["shots"] if s["shot_id"] not in spoken}}))
    lines = {}
    for ln in doc["audio_lines"]:
        if ln.get("speaker_type") == "character":
            f = root / "audio" / f"{ln['line_id']}.wav"
            f.write_bytes(b"line read " + ln["line_id"].encode())
            lines[ln["line_id"]] = {"seconds": LINE_S, "source": "tts", "file": str(f),
                                    "sha256": hashlib.sha256(f.read_bytes()).hexdigest()}
    (root / LR.REL).write_text(json.dumps({"schema": LR.SCHEMA, "lines": lines}))


def test_the_storyboard_passes_a_good_scene_and_fails_a_repeated_or_missing_picture(tmp_path):
    from explainer_engine.videolane import storyboard as SB
    doc = _scene()
    root, pics = _board_episode(tmp_path, doc)
    ids = [s["shot_id"] for s in doc["shots"]]
    rec = SB.build(root, doc, ids, "s1", pictures=pics)
    rows = {r["gate"]: r["status"] for r in rec["rows"]}
    assert rows["storyboard_pictures_present"] == G.PASS and rows["storyboard_no_repeated_composition"] == G.PASS
    assert rec["verdict"]["status"] in (G.PASS, G.REVIEW)
    cell_b = next(c for c in rec["cells"] if c["shot_id"] == "B")
    assert cell_b["from"] == "A" and cell_b["picture"] == "A_start"       # a continuation shows where it starts
    assert Path(rec["sheet"]).is_file() and SB.fresh(root, rec, doc, pics) == []
    # the same picture twice is the same composition
    (root / "assets" / "E.png").write_bytes((root / "assets" / "C.png").read_bytes())
    rec2 = SB.build(root, doc, ids, "s1", pictures=pics)
    assert {r["gate"]: r["status"] for r in rec2["rows"]}["storyboard_no_repeated_composition"] == G.FAIL
    assert SB.fresh(root, rec, doc, pics)                                 # the old record no longer describes the pictures
    del pics["C_start"]
    rec3 = SB.build(root, doc, ids, "s1", pictures=pics)
    assert {r["gate"]: r["status"] for r in rec3["rows"]}["storyboard_pictures_present"] == G.FAIL


def test_a_coverage_picture_from_another_place_is_review(tmp_path):
    from explainer_engine.videolane import storyboard as SB
    doc = _scene()
    root, pics = _board_episode(tmp_path, doc)
    a = np.zeros((180, 320, 3), np.uint8)
    a[:] = (20, 160, 40)                                                 # green night jungle instead of the dusk plain
    Image.fromarray(a).save(root / "assets" / "C.png")
    rec = SB.build(root, doc, [s["shot_id"] for s in doc["shots"]], "s1", pictures=pics)
    assert {r["gate"]: r["status"] for r in rec["rows"]}["storyboard_same_place_as_master"] == G.REVIEW


def test_the_scene_file_needs_a_fresh_storyboard_and_chains_its_continuations(tmp_path):
    from explainer_engine.training.pods.ltx import scene_run as SRN
    from explainer_engine.videolane import scene as SC
    from explainer_engine.videolane import storyboard as SB
    doc = _scene()
    root, pics = _board_episode(tmp_path, doc)
    _reads(root, doc)   # Q4 (D-138)
    ids = [s["shot_id"] for s in doc["shots"]]
    with pytest.raises(ContractError, match="no storyboard"):
        SC.build(root, doc, "s1", tmp_path / "scene.json")
    SB.build(root, doc, ids, "s1", pictures=pics)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json")
    assert scene["schema"] == SC.SCHEMA and scene["draft"]
    by = {s["shot_id"]: s for s in scene["shots"]}
    assert "D" not in by                                                   # the insert is still_25d: no LTX clip
    assert by["B"]["continue_frame"]["pick"] == "best_tail" and "picture" not in by["B"]
    assert by["C"]["picture"] == "C_start" and by["C"]["line"]["text"].startswith("Three days")
    assert by["C"]["seconds"] == P.clip_seconds(doc, doc["shots"][2], 10.0, measured_line_s=LINE_S)["seconds"]   # Q4
    got = SRN.scene_pictures(scene)
    assert set(got) == {"A", "C", "E"}                                     # the continuation has no picture of its own
    assert SC.storyboard_problems(scene) == ["a draft scene (no budget or ledger from the creator, OR-23)"]
    # a picture changed after the storyboard: the scene is refused
    _pic(root / "assets" / "C.png", seed=99)
    with pytest.raises(ContractError, match="stale"):
        SC.build(root, doc, "s1", tmp_path / "scene.json")
    # a failing storyboard: refused
    (root / "assets" / "E.png").write_bytes((root / "assets" / "C.png").read_bytes())
    SB.build(root, doc, ids, "s1", pictures=pics)
    with pytest.raises(ContractError, match="FAILs"):
        SC.build(root, doc, "s1", tmp_path / "scene.json")


# --- the worker's hand-over frame (VL-05) ---------------------------------------------------------------------------------

def _clip_frames(path, frames, fps=24):
    h, w = frames[0].shape[:2]
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r",
                           str(fps), "-i", "-", "-c:v", "libx264", "-crf", "10", "-pix_fmt", "yuv420p", str(path)],
                          stdin=subprocess.PIPE)
    for f in frames:
        ff.stdin.write(np.ascontiguousarray(f).tobytes())
    ff.stdin.close()
    assert ff.wait() == 0
    return path


def test_the_hand_over_is_the_sharpest_stillest_tail_frame_not_a_blurred_last_one(tmp_path):
    from PIL import ImageFilter

    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    base = np.zeros((176, 320, 3), np.uint8)
    yy, xx = np.mgrid[0:176, 0:320]
    base[((yy // 8 + xx // 8) % 2) == 1] = 220                           # a sharp checkerboard
    frames = []
    for k in range(48):
        im = Image.fromarray(np.roll(base, k // 4, axis=1))
        blur = 0 if 30 <= k <= 36 else (4 if k > 36 else 1)               # the tail blurs (mid-motion) after frame 36
        frames.append(np.asarray(im.filter(ImageFilter.GaussianBlur(blur)) if blur else im))
    clip = _clip_frames(tmp_path / "c.mp4", frames)
    last = L.chain_from(L.LAUNCH, 48)
    assert L.handover_frame(clip, 48, 24, None, L.LAUNCH) == {"frame": last, "pick": "last"}
    got = L.handover_frame(clip, 48, 24, {"pick": "best_tail", "window_s": 1.0}, L.LAUNCH)
    assert got["pick"] == "best_tail" and 30 <= got["frame"] <= 36 and got["window"][1] == last
    png = tmp_path / "h.png"
    L.frame_png(clip, got["frame"], png, crop=[0.1, 0.1, 0.9, 0.9])
    assert Image.open(png).size == (256, 140)                              # 80 % of 320x176: a reframe, then fit_picture


def test_the_best_tail_search_starts_after_the_line_and_its_tail(tmp_path):
    """P5 / BP-187 (the creator 2026-11-13): with the clip's expected speech end, the sharpest still frame is searched only
    from the line's end + tail on; the sharp frames 30..36 lie inside the line here, so the pick moves past them; the
    ingest check (``edit_points``) accepts the chosen frame."""
    from PIL import ImageFilter

    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    from explainer_engine.videolane import ingest as VI
    base = np.zeros((176, 320, 3), np.uint8)
    yy, xx = np.mgrid[0:176, 0:320]
    base[((yy // 8 + xx // 8) % 2) == 1] = 220
    frames = []
    for k in range(48):
        im = Image.fromarray(np.roll(base, k // 4, axis=1))
        blur = 0 if 30 <= k <= 36 else (2 if k <= 42 else 5)
        frames.append(np.asarray(im.filter(ImageFilter.GaussianBlur(blur)) if blur else im))
    clip = _clip_frames(tmp_path / "c.mp4", frames)
    cont = {"pick": "best_tail", "window_s": 1.0}
    free = L.handover_frame(clip, 48, 24, cont, L.LAUNCH)
    assert 30 <= free["frame"] <= 36 and "after" not in free
    got = L.handover_frame(clip, 48, 24, cont, L.LAUNCH, speech_end_s=1.25, tail_s=P.TAIL_S)
    floor = L.speech_floor(24, 1.25, P.TAIL_S)
    assert got["after"] == floor and got["window"][0] == floor and got["frame"] >= floor > 36
    assert got["frame"] / 24 + 1e-9 >= 1.25 + P.TAIL_S
    VI.edit_points(2.0, [(0.5, 1.25)], {"tail_handle_s": 0.0}, 2.0, 24, spoken=True, handover_s=got["frame"] / 24,
                   shot_id="S")
    none = L.handover_frame(clip, 48, 24, cont, L.LAUNCH, speech_end_s=1.9, tail_s=P.TAIL_S)
    assert none["frame"] is None and "keeps the line whole" in none["why"]


def test_the_scene_row_tells_the_worker_where_the_line_ends(tmp_path):
    """P5: a clip-spoken row carries ``speech_end_s`` (onset + its measured line) and BP-187's ``speech_tail_s``; a narrated
    row carries neither (the clip says nothing, the hand-over may be anywhere in its tail)."""
    from explainer_engine.videolane import scene as SC
    from explainer_engine.videolane import storyboard as SB
    doc = _scene()
    root, pics = _board_episode(tmp_path, doc)
    _reads(root, doc)
    SB.build(root, doc, [s["shot_id"] for s in doc["shots"]], "s1", pictures=pics)
    scene = SC.build(root, doc, "s1", tmp_path / "scene.json")
    spoken = P.clip_spoken(doc)
    for row in scene["shots"]:
        s = next(x for x in doc["shots"] if x["shot_id"] == row["shot_id"])
        secs = P.clip_seconds(doc, s, 10.0, measured_line_s=LINE_S if row["shot_id"] in spoken else None)
        if row["shot_id"] in spoken:
            assert row["speech_end_s"] == secs["speech_end_s"] > 0 and row["speech_tail_s"] == P.TAIL_S
            assert row["seconds"] >= row["speech_end_s"] + P.TAIL_S
        else:
            assert "speech_end_s" not in row and "speech_tail_s" not in row


def test_a_crop_that_enlarges_too_much_is_refused():
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as L
    assert L.crop_filter([0.1, 0.1, 0.9, 0.9]) == "crop=iw*0.800000:ih*0.800000:iw*0.100000:ih*0.100000"
    with pytest.raises(ValueError, match="soft"):
        L.crop_filter([0.3, 0.3, 0.7, 0.7])
    with pytest.raises(ValueError, match="inside the frame"):
        L.crop_filter([0.5, 0.1, 0.4, 0.9])


def test_g1_fit_row_reads_the_ltx_model_not_wan():
    """FA-01 (Fable audit 2026-11-13): G1's ``video_shots_fit_the_model`` sizes a video shot as the lane does (VL-06) against
    the pinned LTX launch; a 9 s narrated shot fits one clip, an 11 s one FAILs and names the LTX limit."""
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as LJ
    max_s, fps, model = LJ.max_seconds(LJ.LAUNCH), LJ.LAUNCH["native"]["fps"], LJ.LAUNCH["model_repo"]
    doc = _scene()
    doc["shots"][0]["target_duration_seconds"] = 9.0
    doc["shots"][0]["edit_plan"]["tail_handle_s"] = 0.25
    row = P.fit_rows(doc, max_s, model, fps)[0]
    assert row["gate"] == "video_shots_fit_the_model" and row["status"] == G.PASS
    doc["shots"][0]["target_duration_seconds"] = 11.0
    row = P.fit_rows(doc, max_s, model, fps)[0]
    assert row["status"] == G.FAIL and row["measured"] == ["A: needs 11.25 s (planned_length)"]
    assert "LTX" in row["detail"] and model in row["detail"] and "Wan" not in row["detail"]


def test_a_narrated_video_shot_is_sized_by_its_length_not_the_narrators_words():
    """FA-01 / FA-15: the narrator's line is read over the clip, not spoken by it: length + handles, the measured length when
    the read exists (``basis`` says which)."""
    doc = _scene()
    a = doc["shots"][0]                                    # carries the narrator's line L3
    planned = P.clip_seconds(doc, a, 10.0)
    assert planned["basis"] == "planned_length" and planned["speech_s"] == 0
    measured = P.clip_seconds(doc, a, 10.0, measured_s=5.0)
    assert measured["basis"] == "measured_length" and measured["needed_s"] == round(5.0 + float(P.CUT_TAIL[1]), 3)


def test_the_runner_g1_on_toba_no_longer_reports_wan():
    """FA-01 measured on the real script: the fit row of G1 names LTX and no Toba shot is judged against Wan's 5 s clip."""
    import inspect
    from explainer_engine.episode import run as RUN
    src = inspect.getsource(RUN.stage_script)
    assert "VP.fit_rows" in src and "WA.fit_rows" not in src and "modal_wan_jobs" not in src
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as LJ
    doc = json.loads((ROOT / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    row = P.fit_rows(doc, LJ.max_seconds(LJ.LAUNCH), LJ.LAUNCH["model_repo"], LJ.LAUNCH["native"]["fps"])[0]
    assert row["status"] == G.PASS and "Wan" not in row["detail"]


def test_the_ltx_prompt_is_composed_with_the_line_and_the_voice(tmp_path):
    """FA-02: the row's motion_prompt = motion + '<Name> says in <voice>: "<line>"' (+ sound) for a clip-spoken shot, and
    the fixed no-speech clause for a narrated or silent one; the parts are in the row; a missing voice refuses the scene."""
    from explainer_engine.videolane import scene as SC
    from explainer_engine.videolane import storyboard as SB
    doc = _scene()
    doc["shots"][2]["sound_events"] = [{"kind": "foley", "what": "chariot", "class": "chariot", "at_word": "days"}]
    root, pics = _board_episode(tmp_path, doc)
    _reads(root, doc)   # Q4 (D-138): every video shot measured before the scene file
    SB.build(root, doc, [s["shot_id"] for s in doc["shots"]], "s1", pictures=pics)
    by = {s["shot_id"]: s for s in SC.build(root, doc, "s1", tmp_path / "scene.json")["shots"]}
    c = by["C"]["motion_prompt"]
    assert c.startswith("motion of C, one action")
    assert 'The General says in a hoarse older man, low and slow, a dry Argive accent: "Three days and not one Trojan."' in c
    assert "Sound: chariot." in c and SC.NOBODY_SPEAKS not in c
    assert by["A"]["motion_prompt"].endswith(SC.NOBODY_SPEAKS) and "says" not in by["A"]["motion_prompt"]   # narrated
    assert by["B"]["prompt_parts"] == {"motion": "motion of B, one action", "no_speech": SC.NOBODY_SPEAKS}
    assert by["C"]["seconds_basis"] == "measured_line" and by["A"]["seconds_basis"] == "measured_length"   # Q4 (D-138)
    # the script itself stays clean: the line never sits in the script's motion prompt (KP-V4-DIALOGUE-LEAK)
    assert '"' not in doc["shots"][2]["video_prompt"]["motion_prompt"]
    del doc["world_bible"]["characters"][1]["voice_description"]
    scene = SC.build(root, doc, "s1", tmp_path / "scene2.json")
    assert scene["voice_missing"] == ["E: cmd"]
    assert any("no voice description" in w for w in SC.storyboard_problems(scene))


def test_toba_scene_rows_carry_their_lines_and_the_narrated_ones_say_nobody_speaks():
    """FA-02 on the real script: the 9 clip-spoken video shots compose their line, the 46 narrated ones the no-speech clause,
    and the script's own motion prompts still pass the leak lint."""
    from explainer_engine.scripting import shot_prompt_lint as SPL
    from explainer_engine.videolane import scene as SC
    doc = json.loads((ROOT / "episodes" / "ep_toba" / "story" / "production_script.json").read_text(encoding="utf-8"))
    vids = [s for s in doc["shots"] if P.is_video(s)]
    comps = [SC.compose_prompt(doc, s) for s in vids]
    spoken = [c for c in comps if c["spoken"]]
    assert len(vids) == 55 and len(spoken) == 9 and sum(c["prompt"].endswith(SC.NOBODY_SPEAKS) for c in comps) == 46
    lines = {ln["line_id"]: ln["text"] for ln in doc["audio_lines"]}
    for s, c in zip(vids, comps):
        if c["spoken"]:
            assert lines[s["audio_line_ids"][0]].replace('"', "'") in c["prompt"]
    leaks = [i for i in SPL.check_v4_script(doc) if i.get("rule") == "KP-V4-DIALOGUE-LEAK"]
    assert leaks == []


def test_a_hand_over_before_the_speech_end_is_refused_not_cut():
    """FA-07, measured case of the audit: speech to 4.6 s, hand-over at 105/24 = 4.375 s -> ContractError naming the shot,
    the speech end and the hand-over; a hand-over at 5.2 s (after 4.6 + BP-187's 0.5 s) passes."""
    from explainer_engine.videolane import ingest as VI
    with pytest.raises(ContractError, match=r"S05_SH002: the hand-over frame at 4\.375 s lies before the speech end 4\.600 s"):
        VI.edit_points(5.0, [(0.8, 4.6)], {"tail_handle_s": 0.5}, 4.0, 24, spoken=True, handover_s=105 / 24,
                       shot_id="S05_SH002")
    pts = VI.edit_points(6.0, [(0.8, 4.6)], {"tail_handle_s": 0.5}, 4.0, 24, spoken=True, handover_s=5.2, shot_id="S")
    assert pts["out_s"] >= 4.6 + VI.SPEECH_TAIL_S
    from explainer_engine.standards import sourced_rules as SR
    assert "explainer_engine/videolane/ingest.py" in SR.rule("BP-187")["enforced_by"]


def test_the_draft_edit_plans_cover_toba_and_leave_no_fail():
    """Fable audit 2026-11-13 P3: the edit-planner's first draft (``plan.draft_edit_plans``) reads the script's camera,
    screen-direction notes and continuity refs; on the Toba script (55 video shots, plans now written) every video shot has a
    plan and the VL findings hold no FAIL. A draft never overwrites a written plan."""
    import json
    from pathlib import Path
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as LJ
    from explainer_engine.videolane import plan as P
    doc = json.loads((Path(__file__).resolve().parents[2] / "episodes/ep_toba/story/production_script.json").read_text("utf-8"))
    vids = [s for s in doc["shots"] if P.is_video(s)]
    assert len(vids) == 55 and all(s.get("edit_plan") for s in vids)
    assert P.draft_edit_plans(doc) == {}                       # nothing left to draft, nothing overwritten
    assert not [f for f in P.findings(doc, LJ.max_seconds(LJ.LAUNCH)) if f["severity"] == "FAIL"]
    bare = json.loads(json.dumps(doc))
    for s in bare["shots"]:
        s.pop("edit_plan", None)
    drafts = P.draft_edit_plans(bare)
    assert set(drafts) == {s["shot_id"] for s in vids}
    assert drafts["S05_SH002"]["speech_onset_s"] == P.SPEECH_ONSET_S          # a clip-spoken shot
    assert drafts["S05_SH002"]["axis_side"] == "A" and drafts["S05_SH002"]["screen_positions"] == {"char_kael_74000bce": "left"}
    assert drafts["S02_SH002"]["continuity_mode"] == "insert"                 # a close-up with nobody in it


def test_continuity_cards_from_the_v4_script():
    """P3 / FA-14: ``continuity.cards_from_v4`` drafts continuity_card/1 for every Toba scene with a video shot and a hero;
    they pass the schema (CT-01) and the card check; the master frame is image 1 of every other shot (CT-03)."""
    import json
    from pathlib import Path
    from explainer_engine.scripting import continuity as C
    from explainer_engine.videolane import plan as P
    doc = json.loads((Path(__file__).resolve().parents[2] / "episodes/ep_toba/story/production_script.json").read_text("utf-8"))
    n = 0
    for scene in P.scenes(doc):
        if not any(P.is_video(s) for s in scene):
            continue
        card = C.cards_from_v4(doc, scene)
        if card is None:
            continue
        n += 1
        assert not [f for f in C.check(card) if f["level"] == "FAIL"], card["scene_id"]
        for s in card["shots"]:
            if not s.get("is_master"):
                assert s["refs"][0] == {"path": card["location"]["master_frame"], "role": "place"}
    assert n == 24
