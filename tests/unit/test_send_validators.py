"""``qa/send_validators.living_motion`` (R-LIVING, G-LIVE-1 and G-LIVE-3): FAILS a known violation fixture ("only the fire moves": a still
photo with one small flame), PASSES a compliant one (a still camera with moving smoke), says NOT_RUN for a moving camera. Synthetic clips
encoded with ffmpeg; no network, $0."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.qa import liveliness as LV
from explainer_engine.qa import send_validators as V

pytestmark = pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="needs ffmpeg")
W, H, FPS = 480, 270, 24


def clip(path, frames):
    p = subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "gray", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p", str(path)],
                       input=b"".join(f.astype(np.uint8).tobytes() for f in frames), capture_output=True)
    assert p.returncode == 0, p.stderr.decode()[-300:]
    return path


def background():
    rng = np.random.default_rng(1)
    return np.clip(np.kron(rng.integers(40, 200, (27, 48)), np.ones((10, 10))), 0, 255).astype(np.float32)


def seconds(n):
    return int(n * FPS)


def wide_texture(seed):
    rng = np.random.default_rng(seed)
    return np.clip(np.kron(rng.integers(30, 220, (27, 88)), np.ones((10, 10))), 0, 255).astype(np.float32)   # 270 x 880


def drifting(bg, area, tex, px_per_frame, i):
    """The picture with one region replaced by a texture that drifts sideways (smoke, cloud, flame body): a world that moves under a still camera."""
    f = bg.copy()
    sh = int(round(px_per_frame * i)) % 300
    f[area] = tex[area[0], area[1].start + sh:area[1].stop + sh]
    return f


def smoke_clip(path, n=3.0, area=(slice(40, 230), slice(60, 400))):
    """A still camera, a textured picture, a big region of drifting texture (smoke, snow bank, sky)."""
    bg, tex = background(), wide_texture(2)
    return clip(path, [drifting(bg, area, tex, 0.5, i) for i in range(seconds(n))])


def fire_only_clip(path, n=3.0):
    """The violation: a still photograph in which only one small flame (1 % of the frame) flickers."""
    rng = np.random.default_rng(3)
    bg = background()
    frames = []
    for _ in range(seconds(n)):
        f = bg.copy()
        f[200:220, 230:250] = rng.integers(150, 255, (20, 20))
        frames.append(f)
    return clip(path, frames)


def camera_move_clip(path, n=3.0, px_per_frame=1):
    """The violation: the camera drifts over a dead picture, nothing in the world moves (the whole frame changes, the world does not)."""
    bg = np.tile(background(), (1, 2))
    return clip(path, [bg[:, px_per_frame * i % 400:px_per_frame * i % 400 + W] for i in range(seconds(n))])


FLAKES = 450


def snow_frames(n, matte_only=False):
    """Still camera, dead picture, 450 flakes of 3x3 px falling 60 px/s: the particle layer alone (and its matte)."""
    rng = np.random.default_rng(4)
    x0, y0 = rng.integers(0, W - 3, FLAKES), rng.integers(0, H, FLAKES)
    bg, out, mattes = background(), [], []
    for i in range(seconds(n)):
        f, m = bg.copy(), np.zeros((H, W), np.float32)
        for x, y in zip(x0, (y0 + 2.5 * i) % (H - 3)):
            f[int(y):int(y) + 3, x:x + 3] = 255
            m[int(y):int(y) + 3, x:x + 3] = 255
        out.append(f)
        mattes.append(m)
    return out, mattes


def snow_only_clip(path, n=3.0):
    return clip(path, snow_frames(n)[0])


def zones_json(tmp_path, name, zones, extra=None):
    """Write masks and ``<name>.zones.json``; ``zones`` = [(zone name, kind, (x0, y0, x1, y1))]."""
    rows = []
    for zn, kind, (x0, y0, x1, y1) in zones:
        m = np.zeros((H, W), np.uint8)
        m[y0:y1, x0:x1] = 255
        Image.fromarray(m).save(tmp_path / f"{zn}.png")
        rows.append({"name": zn, "kind": kind, "mask": f"{zn}.png"})
    (tmp_path / f"{name}.zones.json").write_text(json.dumps(dict({"zones": rows}, **(extra or {}))), encoding="utf-8")


def alive_world_clip(path, n=3.0, with_snow=False, camera_px=0):
    """The compliant clip: a still (or slowly drifting) camera; fire and smoke and clouds move by themselves; optionally a snow layer on top."""
    bg, tex = np.tile(background(), (1, 2)), wide_texture(2)
    sky, smoke, fire = (slice(0, 40), slice(0, W)), (slice(60, 200), slice(60, 260)), (slice(200, 260), slice(300, 400))
    frames = []
    snow, _ = snow_frames(n) if with_snow else (None, None)
    for i in range(seconds(n)):
        f = bg[:, camera_px * i % 400:camera_px * i % 400 + W].copy()
        for area, speed in ((sky, 0.5), (smoke, 0.7), (fire, 1.5)):
            sh = int(round(speed * i)) % 300
            f[area] = tex[area[0], area[1].start + sh:area[1].stop + sh]
        if snow is not None:
            f = np.where(snow[i] == 255, 255, f)
        frames.append(f)
    return clip(path, frames)


ZONES = [("sky", "sky", (0, 0, 480, 40)), ("smoke", "smoke", (60, 60, 260, 200)), ("fire", "fire", (300, 200, 400, 260))]


def test_a_still_camera_with_moving_smoke_passes_with_its_number(tmp_path):
    r = V.living_motion(smoke_clip(tmp_path / "ok.mp4"))
    assert r["status"] == "PASS" and r["value"] >= V.FRAME_COVER_MIN, r
    assert "no .zones.json" in r["detail"] and "flow with the camera out" in r["detail"]


def test_only_the_fire_moves_fails(tmp_path):
    r = V.living_motion(fire_only_clip(tmp_path / "bad.mp4"))
    assert r["status"] == "FAIL" and r["value"] < LV.FROZEN_CHANGE, r
    assert "G-LIVE-1" in r["detail"]


def test_a_camera_move_alone_fails_with_the_camera_taken_out(tmp_path):
    """Client item 8: camera-only must FAIL (it used to be NOT_RUN: the camera is now fitted and subtracted)."""
    r = V.living_motion(camera_move_clip(tmp_path / "pan.mp4"))
    assert r["status"] == "FAIL" and "camera" in r["detail"] and r["value"] < V.FRAME_COVER_MIN, r


def test_snow_alone_fails_without_zones_and_with_zones(tmp_path):
    """Client item 8: snow alone cannot pass a clip (flakes cover a few percent of the frame)."""
    clip_ = snow_only_clip(tmp_path / "snow.mp4")
    r = V.living_motion(clip_)
    assert r["status"] == "FAIL" and "particles alone" in r["detail"], r
    zones_json(tmp_path, "snow", ZONES)
    r = V.living_motion(clip_)
    assert r["status"] == "FAIL" and "G-LIVE-3" in r["detail"], r


def test_with_the_particle_layer_left_out_snow_alone_has_no_zone_motion(tmp_path):
    frames, mattes = snow_frames(3.0)
    clip_ = clip(tmp_path / "snow2.mp4", frames)
    clip(tmp_path / "matte.mp4", mattes)
    zones_json(tmp_path, "snow2", ZONES, {"particles": {"matte": "matte.mp4"}})
    r = V.living_motion(clip_)
    assert r["status"] == "FAIL" and "G-LIVE-3" in r["detail"], r


def test_a_compliant_clip_with_zones_passes(tmp_path):
    p = alive_world_clip(tmp_path / "ok.mp4")
    zones_json(tmp_path, "ok", ZONES)
    r = V.living_motion(p)
    assert r["status"] == "PASS" and all(z in r["detail"] for z in ("sky", "smoke", "fire")), r


def test_a_compliant_clip_on_a_drifting_camera_passes(tmp_path):
    """The world moves by itself while the camera drifts (the slow 2.5D drift of D-139): the camera is fitted and taken out, the effects stay."""
    p = alive_world_clip(tmp_path / "drift.mp4", camera_px=1)
    zones_json(tmp_path, "drift", ZONES)
    r = V.living_motion(p)
    assert r["status"] == "PASS", r


def test_a_camera_drift_with_parallax_and_a_dead_world_still_fails(tmp_path):
    """A 2.5D drift where the far sky moves half as fast as the near layer (parallax) and nothing is alive: the smoke and fire zones fail
    (their motion is the camera's). Limit, stated in BP-215: with the sky zone alone, parallax of the same order as slow clouds could pass."""
    bg, sky_bg = np.tile(background(), (1, 2)), np.tile(wide_texture(7), (1, 2))
    frames = []
    for i in range(seconds(3.0)):
        f = bg[:, i % 400:i % 400 + W].copy()
        f[:40] = sky_bg[:40, (i // 2) % 400:(i // 2) % 400 + W]
        frames.append(f)
    p = clip(tmp_path / "parallax.mp4", frames)
    zones_json(tmp_path, "parallax", ZONES[1:])                       # smoke and fire zones
    r = V.living_motion(p)
    assert r["status"] == "FAIL" and ("smoke zone" in r["detail"] or "fire zone" in r["detail"]), r


def test_a_dead_zone_in_a_moving_clip_fails_by_name(tmp_path):
    p = alive_world_clip(tmp_path / "dead_fire.mp4")
    zones_json(tmp_path, "dead_fire", ZONES[:2] + [("fire", "fire", (400, 100, 470, 180))])    # the 'fire' mask sits on a static part
    r = V.living_motion(p)
    assert r["status"] == "FAIL" and "fire zone" in r["detail"], r


def test_a_zone_kind_without_a_threshold_is_refused(tmp_path):
    p = smoke_clip(tmp_path / "k.mp4")
    zones_json(tmp_path, "k", [("lava", "lava", (60, 40, 400, 230))])
    with pytest.raises(ValueError, match="BP-215"):
        V.living_motion(p)


def test_without_opencv_the_flow_is_not_measured_never_passed(tmp_path, monkeypatch):
    p = smoke_clip(tmp_path / "nocv.mp4")
    monkeypatch.setattr(V, "_cv2", lambda: None)
    r = V.living_motion(p)
    assert r["status"] == "NOT_RUN" and "OpenCV" in r["detail"], r


# ---- the depth-occlusion check (client item 8): the foreground hides the far particles -------------------------------------------

def far_flakes(n, left_too):
    """Far flakes: only over the right half (far background) when compliant; also over the left half (the soldiers) when not."""
    rng = np.random.default_rng(5)
    lo = 0 if left_too else W // 2
    x0, y0 = rng.integers(lo, W - 3, 200), rng.integers(0, H, 200)
    out = []
    for i in range(seconds(n)):
        m = np.zeros((H, W), np.float32)
        for x, y in zip(x0, (y0 + 1.5 * i) % (H - 3)):
            m[int(y):int(y) + 3, x:x + 3] = 255
        out.append(m)
    return out


def occlusion_case(tmp_path, left_too):
    p = alive_world_clip(tmp_path / "occ.mp4")
    clip(tmp_path / "far.mp4", far_flakes(3.0, left_too))
    depth = np.zeros((H, W), np.uint8)
    depth[:, :W // 2] = 230                    # the near half (soldiers, sandbags); the far half is dark
    depth[:, W // 2:] = 40
    Image.fromarray(depth).save(tmp_path / "depth.png")
    zones_json(tmp_path, "occ", ZONES, {"particles": {"far": "far.mp4"}, "depth": "depth.png"})
    return p


def test_far_flakes_hidden_behind_the_foreground_pass(tmp_path):
    r = V.living_motion(occlusion_case(tmp_path, left_too=False))
    assert r["status"] == "PASS" and "far particles over the foreground 0.00 %" in r["detail"], r


def test_far_flakes_drawn_over_the_soldiers_fail(tmp_path):
    r = V.living_motion(occlusion_case(tmp_path, left_too=True))
    assert r["status"] == "FAIL" and "does not hide them" in r["detail"] and r["value"] > V.FAR_OVER_FG_MAX, r


def test_a_declared_particle_layer_without_its_depth_map_fails(tmp_path):                    # lead's ruling 2026-11-20: declaring nothing true is a FAIL, never a NOT_RUN
    p = alive_world_clip(tmp_path / "nodepth.mp4")
    zones_json(tmp_path, "nodepth", ZONES, {"particles": {"far": "far.mp4"}})
    clip(tmp_path / "far.mp4", far_flakes(3.0, False))
    r = V.living_motion(p)
    assert r["status"] == "FAIL" and "depth map is missing" in r["detail"], r


def test_the_thresholds_are_read_from_bp_215():
    from explainer_engine.standards import sourced_rules as SR
    assert V.ZONE_SPEED["fire"] == SR.T("BP-215", "fire_min_px_s") and V.FAR_OVER_FG_MAX == SR.T("BP-215", "far_over_foreground_max_pct")
    assert SR.rule("BP-215")["status"] == "hypothesis"


def test_a_clip_shorter_than_a_second_is_not_run(tmp_path):
    r = V.living_motion(smoke_clip(tmp_path / "s.mp4", n=0.5))
    assert r["status"] == "NOT_RUN"


def test_a_file_that_is_no_video_raises_so_the_send_gate_blocks(tmp_path):
    bad = tmp_path / "x.mp4"
    bad.write_bytes(b"not a video")
    with pytest.raises(RuntimeError):
        V.living_motion(bad)


def test_the_pure_numpy_frozen_windows_agree_with_the_threshold():
    still = [np.zeros((270, 480), np.float32)] * 30
    assert LV.frozen_windows_grey(still, 8)["frozen"] > 0
    moving = [np.full((270, 480), 40.0 * ((i // 8) % 2), np.float32) for i in range(30)]
    assert LV.frozen_windows_grey(moving, 8)["frozen"] == 0


def test_the_phase_shift_sees_a_translation():
    a = background()
    assert V.phase_shift(a, a) < 0.5 and V.phase_shift(a, np.roll(a, 6, axis=1)) > 4


def test_the_validator_declares_its_kinds_for_the_send_gate():
    assert ".mp4" in V.living_motion.kinds


def test_the_command_line_prints_a_line_per_clip_and_exits_1_on_a_fail(tmp_path, capsys):
    ok, bad = smoke_clip(tmp_path / "ok.mp4"), fire_only_clip(tmp_path / "bad.mp4")
    assert V.main(["living_motion", str(ok)]) == 0
    assert "PASS" in capsys.readouterr().out
    assert V.main(["living_motion", str(ok), str(bad)]) == 1
    out = capsys.readouterr().out
    assert "PASS" in out and "FAIL" in out and "G-LIVE-1" in out
    junk = tmp_path / "junk.mp4"
    junk.write_bytes(b"x")
    assert V.main(["living_motion", str(junk)]) == 2


# ---- rule 19 (OR-V35): Gemini photos only in Task mode, 6 per batch ---------------------------------------------------------------

def _batch(n, batch="3"):
    lines = [f"BATCH REPORT {batch}"] + [f"{k} | p{k:02d} | MADE | refs: 1 | prompt: AS GIVEN | note: -" for k in range(1, n + 1)]
    return "\n".join(lines + [f"MADE {n} of {n}"])


def _t0(mode, n=6, model="Gemini 3.8 Flash"):
    return f"T0 REPORT abcdef12\nMODEL: {model} | MODE: {mode}\nDRIVE READ: OK \"v1\"\nDRIVE WRITE: OK x\n{_batch(n, '0')}\nLIMIT: not reached"


def _f(tmp_path, text, name="a.txt"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_an_operator_task_line_with_six_pictures_passes_in_both_forms(tmp_path):
    for k, line in enumerate(("MODE: task", "chat mode **Task** (input box read 'Describe a task')", "> **MODE: Task**")):
        r = V.gemini_task_report(_f(tmp_path, line + "\n" + _batch(6), f"p{k}.txt"))
        assert r["status"] == "PASS" and r["value"] == 6, line
    assert V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _t0("Task"), "t.txt"))["status"] == "PASS"
    assert V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _batch(4), "s.txt"))["status"] == "PASS"   # a shorter batch is fine


def test_gemini_task_report_fails_outside_task_mode_and_over_six(tmp_path):                       # the negative test of OR-V35
    r = V.gemini_task_report(_f(tmp_path, "MODE: chat\n" + _batch(6)))
    assert r["status"] == "FAIL" and "Task mode" in r["detail"]
    r = V.gemini_task_report(_f(tmp_path, "MODE: task\n" + _batch(7), "b.txt"))
    assert r["status"] == "FAIL" and r["value"] == 7
    assert V.gemini_task_report(_f(tmp_path, _t0("Chat"), "c.txt"))["status"] == "FAIL"             # the chat's own words can fail, never pass


def test_without_an_operator_mode_line_the_mode_is_not_measured(tmp_path):
    r = V.gemini_task_report(_f(tmp_path, _batch(6)))
    assert r["status"] == "NOT_RUN" and r["value"] == 6 and "mode is not measured" in r["detail"]
    assert V.gemini_task_report(_f(tmp_path, _t0("Task"), "t.txt"))["status"] == "NOT_RUN"           # the chat cannot vouch for its own mode


def test_a_report_that_does_not_parse_raises_so_the_send_gate_blocks(tmp_path):
    with pytest.raises(Exception):
        V.gemini_task_report(_f(tmp_path, "hello"))
    assert V.gemini_task_report.kinds == (".txt", ".md")


# ---- BP-214 / OR-V36: faces intact (IoU floor from sourced_rules) --------------------------------------------------------------------

def _boxes(*bs):
    return lambda path: list(bs[0 if str(path).startswith("b") else 1])


def _shift(box, dx=0.0, dy=0.0, k=1.0):
    cx, cy = (box[0] + box[2]) / 2 + dx, (box[1] + box[3]) / 2 + dy
    w, h = (box[2] - box[0]) * k, (box[3] - box[1]) * k
    return (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)


FACE = (0.40, 0.20, 0.50, 0.38)


def test_the_same_face_after_an_upscale_passes_with_its_lowest_iou():
    r = V.faces_intact_pair("b", "a", detect=_boxes([FACE], [_shift(FACE, 0.002)]))
    assert r["status"] == "PASS" and r["value"] >= V.FACE_IOU_MIN and "not binding" in r["detail"]


def test_a_moved_a_warped_and_a_missing_or_extra_face_fail(tmp_path):                                # the calibration set of bad fixtures
    for label, after in (("moved", [_shift(FACE, 0.03)]), ("warped", [_shift(FACE, k=1.3)]), ("lost", []),
                         ("extra", [FACE, (0.1, 0.1, 0.2, 0.3)])):
        r = V.faces_intact_pair("b", "a", detect=_boxes([FACE], after))
        assert r["status"] == "FAIL", label


def test_two_faces_are_matched_one_to_one():
    f2 = (0.70, 0.25, 0.80, 0.43)
    assert V.faces_intact_pair("b", "a", detect=_boxes([FACE, f2], [f2, FACE]))["status"] == "PASS"
    assert V.faces_intact_pair("b", "a", detect=_boxes([FACE, f2], [FACE, _shift(f2, 0.05)]))["status"] == "FAIL"


def test_no_face_and_no_opencv_are_not_run_never_a_pass():
    assert V.faces_intact_pair("b", "a", detect=_boxes([], []))["status"] == "NOT_RUN"
    def boom(path):
        raise RuntimeError("OpenCV or the YuNet model is missing")
    r = V.faces_intact_pair("b", "a", detect=boom)
    assert r["status"] == "NOT_RUN" and "not measured" in r["detail"]


def test_the_default_detector_says_not_run_when_opencv_or_the_model_is_missing(tmp_path, monkeypatch):
    from explainer_engine.qa import pixels as PX
    monkeypatch.setattr(PX, "yunet_path", lambda: None)
    img = tmp_path / "x.png"
    Image.new("RGB", (64, 64), (9, 9, 9)).save(img)
    assert V.faces_intact_pair(img, img)["status"] == "NOT_RUN"


def test_the_pair_file_adapter(tmp_path, monkeypatch):
    for n in ("a.png", "b.png"):
        Image.new("RGB", (64, 64), (9, 9, 9)).save(tmp_path / n)
    monkeypatch.setattr(V, "yunet_boxes", lambda p: [FACE] if p.name == "a.png" else [_shift(FACE, 0.05)])
    pair = tmp_path / "s.faces.json"
    pair.write_text(json.dumps({"before": "a.png", "after": "b.png"}), encoding="utf-8")
    assert V.faces_intact(pair)["status"] == "FAIL" and V.faces_intact.kinds == (".json",)
    other = tmp_path / "other.json"
    other.write_text("{}", encoding="utf-8")
    assert V.faces_intact(other)["status"] == "NOT_RUN"
    pair.write_text(json.dumps({"before": "a.png", "after": "gone.png"}), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        V.faces_intact(pair)


def test_the_floor_is_read_from_sourced_rules():
    from explainer_engine.standards import sourced_rules as SR
    assert V.FACE_IOU_MIN == SR.T("BP-214", "face_iou_min") == 0.85 and SR.rule("BP-214")["status"] == "hypothesis"


# ---- OR-V20: the living inventory of a shot-direction file (G-INV, G-BAL, G-WX) --------------------------------------------------------

def _direction(tmp_path, d, name="shot.json"):
    p = tmp_path / name
    p.write_text(json.dumps(d), encoding="utf-8")
    return p


def _base_direction(duration_s=263 / 24):
    import copy
    from test_direction import BASE
    return dict(copy.deepcopy(BASE), duration_s=duration_s)


def test_a_compliant_shot_direction_passes_the_living_inventory(tmp_path):
    r = V.living_inventory(_direction(tmp_path, _base_direction()))
    assert r["status"] == "PASS" and r["value"] == 0 and "balance" in r["detail"], r


def test_an_inventory_with_an_element_left_frozen_without_a_reason_fails(tmp_path):     # the negative test of OR-V20
    d = _base_direction()
    d["seen"]["living"][1].update(decision="skip", effects=[])                          # the smoke is left frozen, no reason
    r = V.living_inventory(_direction(tmp_path, d))
    assert r["status"] == "FAIL" and "without a reason" in r["detail"], r


def test_a_missing_inventory_and_snow_without_the_scene_fail_and_a_thin_balance_is_only_listed(tmp_path):
    d = _base_direction()
    del d["seen"]["living"]
    assert V.living_inventory(_direction(tmp_path, d, "a.json"))["status"] == "FAIL"
    d = _base_direction()
    d["tracks"].append({"track": "atmosphere", "op": "snow", "renderer": "directed25d", "params": {}, "id": "fx_snow"})
    r = V.living_inventory(_direction(tmp_path, d, "b.json"))
    assert r["status"] == "FAIL" and "scene's weather" in r["detail"], r
    d = _base_direction()
    d["seen"]["living"] = d["seen"]["living"][:2]                                         # only the flame and its smoke live
    d["tracks"] = [t for t in d["tracks"] if t.get("id") not in ("fx_mist", "fx_sky")]
    r = V.living_inventory(_direction(tmp_path, d, "c.json"))                           # since the owner's 2026-11-15 Decision 2 the floor is a REVIEW
    assert r["status"] == "PASS" and "REVIEW: LP-08" in r["detail"], r                    # hint, never a FAIL: it is listed, not failed


def test_a_balance_that_cannot_be_measured_is_not_run_and_a_foreign_file_is_not_run(tmp_path):
    d = _base_direction()
    del d["duration_s"]
    r = V.living_inventory(_direction(tmp_path, d, "nodur.json"))
    assert r["status"] == "NOT_RUN" and "duration_s" in r["detail"], r
    assert V.living_inventory(_direction(tmp_path, {"zones": []}, "zones.json"))["status"] == "NOT_RUN"
    bad = tmp_path / "broken.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(ValueError):
        V.living_inventory(bad)


def test_the_living_inventory_declares_its_kind_and_the_command_line_runs_it(tmp_path, capsys):
    assert V.living_inventory.kinds == (".json",)
    p = _direction(tmp_path, _base_direction())
    assert V.main(["living_inventory", str(p)]) == 0
    assert "PASS" in capsys.readouterr().out


# ---- OR-V26: frame change per second against the reference (3.6-12.2 %/s) --------------------------------------------------------------

def test_a_moving_world_changes_the_frame_within_the_reference_and_passes(tmp_path):
    r = V.change_per_second(smoke_clip(tmp_path / "ok.mp4"))
    assert r["status"] == "PASS" and r["value"] >= LV.CHANGE_FLOOR and "reference 3.6-12.2" in r["detail"], r


def test_a_nearly_still_photo_changes_under_the_floor_and_fails(tmp_path):                  # the negative test of OR-V26
    r = V.change_per_second(fire_only_clip(tmp_path / "bad.mp4"))
    assert r["status"] == "FAIL" and r["value"] < LV.CHANGE_FLOOR and "floor 3.6" in r["detail"], r


def test_the_reference_change_needs_opencv_and_a_second_of_frames(tmp_path, monkeypatch):
    assert V.change_per_second(smoke_clip(tmp_path / "short.mp4", n=0.5))["status"] == "NOT_RUN"
    monkeypatch.setattr(V, "_cv2", lambda: None)
    assert V.change_per_second(smoke_clip(tmp_path / "nocv.mp4"))["status"] == "NOT_RUN"
    assert V.change_per_second.kinds == V.living_motion.kinds


# ---- OR-V21: a visible flame is never frozen (flow in the fire zone, every one-second window) ------------------------------------------

def flame_stops_clip(path, n=4.0, stop_s=2.0):
    """The violation: smoke and clouds move all the time, the flame moves for ``stop_s`` seconds and then stands (a world that is alive around it)."""
    bg, tex = np.tile(background(), (1, 2)), wide_texture(2)
    sky, smoke, fire = (slice(0, 40), slice(0, W)), (slice(60, 200), slice(60, 260)), (slice(200, 260), slice(300, 400))
    frames = []
    for i in range(seconds(n)):
        f = bg[:, :W].copy()
        for area, speed in ((sky, 0.5), (smoke, 0.7), (fire, 1.5)):
            sh = int(round(speed * (min(i, seconds(stop_s)) if area is fire else i))) % 300
            f[area] = tex[area[0], area[1].start + sh:area[1].stop + sh]
        frames.append(f)
    return clip(path, frames)


def test_a_flame_that_moves_in_every_second_passes_with_its_quietest_window(tmp_path):
    zones_json(tmp_path, "ok", ZONES)
    r = V.flame_never_frozen(alive_world_clip(tmp_path / "ok.mp4"))
    assert r["status"] == "PASS" and r["value"] >= V.FIRE_WINDOW_MIN and "quietest window" in r["detail"], r


def test_a_flame_that_stands_for_a_second_fails_by_zone_and_second(tmp_path):                 # the negative test of OR-V21
    zones_json(tmp_path, "bad", ZONES)
    clip_path = flame_stops_clip(tmp_path / "bad.mp4")
    r = V.flame_never_frozen(clip_path)
    assert r["status"] == "FAIL" and "fire from 2 s" in r["detail"], r
    assert V.living_motion(clip_path)["status"] == "PASS"                                  # the whole-clip median cannot see it: that is why this check exists


def test_a_flame_that_is_not_located_or_not_measurable_is_not_run(tmp_path, monkeypatch):
    zones_json(tmp_path, "nofire", [z for z in ZONES if z[1] != "fire"])
    r = V.flame_never_frozen(alive_world_clip(tmp_path / "nofire.mp4"))
    assert r["status"] == "NOT_RUN" and "no zone of kind fire" in r["detail"], r
    zones_json(tmp_path, "short", ZONES)
    assert V.flame_never_frozen(alive_world_clip(tmp_path / "short.mp4", n=0.5))["status"] == "NOT_RUN"
    monkeypatch.setattr(V, "_cv2", lambda: None)
    assert V.flame_never_frozen(alive_world_clip(tmp_path / "nofire.mp4"))["status"] == "NOT_RUN"
    assert V.flame_never_frozen.kinds == V.living_motion.kinds and V.FIRE_WINDOW_MIN == 5.0


# ---- OR-V29 / OR-V51: every choice of the director carries a reason, no effect is typed by hand ----------------------------------------

def _reasoned_direction():
    d = _base_direction()
    for e in d["seen"]["living"]:
        e["why"] = "P1: the words name it and it is not a dot"
    return d


def test_a_direction_where_every_choice_carries_a_reason_passes(tmp_path):
    r = V.director_reasons(_direction(tmp_path, _reasoned_direction()))
    assert r["status"] == "PASS" and r["value"] == 0 and "carry a reason" in r["detail"], r


def test_a_choice_without_a_reason_or_an_effect_typed_by_hand_fails(tmp_path):              # the negative test of OR-V29 / OR-V51
    d = _reasoned_direction()
    d["seen"]["living"][0]["why"] = " "
    r = V.director_reasons(_direction(tmp_path, d, "a.json"))
    assert r["status"] == "FAIL" and "living brazier" in r["detail"] and "no why" in r["detail"], r
    d = _reasoned_direction()
    d["tracks"].append({"track": "atmosphere", "op": "dust", "renderer": "directed25d", "params": {}, "id": "fx_typed"})
    r = V.director_reasons(_direction(tmp_path, d, "b.json"))
    assert r["status"] == "FAIL" and "fx_typed" in r["detail"] and "typed by hand" in r["detail"], r
    d = _reasoned_direction()
    d["sound"] = {"events": [{"class": "fire_crackle", "why": ""}]}
    assert V.director_reasons(_direction(tmp_path, d, "c.json"))["status"] == "FAIL"


def test_the_reason_check_says_not_run_for_a_foreign_file_and_fails_effects_without_an_inventory(tmp_path):
    assert V.director_reasons(_direction(tmp_path, {"zones": []}, "z.json"))["status"] == "NOT_RUN"
    d = _reasoned_direction()
    del d["seen"]["living"]
    assert V.director_reasons(_direction(tmp_path, d, "n.json"))["status"] == "FAIL"
    d["tracks"] = [t for t in d["tracks"] if t.get("track") in ("camera", "audio")]
    assert V.director_reasons(_direction(tmp_path, d, "m.json"))["status"] == "NOT_RUN"
    assert V.director_reasons.kinds == (".json",)


def test_a_file_written_by_the_directors_own_code_passes_the_reason_check_and_the_inventory(tmp_path):
    from test_living_director import FACES_PX, SEEN, SPINE, _dark
    from explainer_engine.production import living_director as LD
    d = LD.direct(SEEN, SPINE, 72, 24.0, _dark(), FACES_PX)
    d["duration_s"] = 72 / 24.0
    p = _direction(tmp_path, d, "directed.json")
    r = V.director_reasons(p)
    assert r["status"] == "PASS", r                                                         # the claim of the docstring: the director's writer passes it
    assert V.living_inventory(p)["status"] in ("PASS", "NOT_RUN"), V.living_inventory(p)


# ---- OR-V23: the weather is decided by the director, once, with a written reason ---------------------------------------------------

def _snowy_direction(why):
    d = _base_direction()
    d["scene"] = {"weather": ["snow"], "surroundings": "a muddy trench"}
    d["weather"] = [{"weather": "snow", "in": False, "decided_by": "1 open_sky", "why": why}]
    return d


def test_a_scene_weather_the_director_decided_with_a_reason_passes_the_inventory(tmp_path):
    r = V.living_inventory(_direction(tmp_path, _snowy_direction("inside the dugout, the sky is shut"), "w1.json"))
    assert r["status"] == "PASS", r


def test_a_scene_weather_left_for_someone_to_ask_without_a_decision_or_reason_fails_the_inventory(tmp_path):   # the negative test of OR-V23
    r = V.living_inventory(_direction(tmp_path, _snowy_direction(""), "w2.json"))
    assert r["status"] == "FAIL" and "without a reason" in r["detail"], r
    d = _snowy_direction("x")
    d["weather"][0]["decided_by"] = "ask the owner"
    r = V.living_inventory(_direction(tmp_path, d, "w3.json"))
    assert r["status"] == "FAIL" and "decided_by" in r["detail"], r


# ---- OR-V72: what the photo and the words name must be in the inventory with an effect or a reason -------------------------------------

def test_every_named_element_is_in_the_inventory_with_an_effect_or_a_reason_and_passes(tmp_path):
    d = _base_direction()
    d["seen"]["what"] += ", barbed wire along the parapet"
    d["seen"]["living"].append({"id": "wire", "kind": "wire", "where": [0.1, 0.4], "decision": "skip", "why": "a thin wire, the cut-out would smear it",
                                "area_pct": 1, "text": 0, "focus": 0, "quality": 0, "cost": 2})
    r = V.living_inventory(_direction(tmp_path, d, "v72a.json"))
    assert r["status"] == "PASS", r


def test_a_named_element_missing_from_the_inventory_fails_it(tmp_path):                       # the negative test of OR-V72
    d = _base_direction()
    d["seen"]["what"] += ", barbed wire along the parapet"                                    # the photo shows wire, the inventory has none
    r = V.living_inventory(_direction(tmp_path, d, "v72b.json"))
    assert r["status"] == "FAIL" and "names wire" in r["detail"], r


# ---- OR-V25: body motion is LTX's, not 2.5D's (LP-02) ----------------------------------------------------------------------------------

def test_a_plan_that_leaves_the_bodies_to_ltx_passes_the_body_motion_check(tmp_path):
    d = _base_direction()
    d["seen"]["living"].append({"id": "lips", "kind": "body", "where": [0.4, 0.3], "decision": "skip", "why": "LP-02: the words need the lips to move: LTX",
                                "body_motion": True, "area_pct": 1, "text": 2, "focus": 2, "quality": 2, "cost": 2})
    r = V.no_body_motion_in_25d(_direction(tmp_path, d, "ok.json"))
    assert r["status"] == "PASS" and "left to LTX: lips" in r["detail"], r
    assert V.no_body_motion_in_25d(_direction(tmp_path, _base_direction(), "plain.json"))["status"] == "PASS"


def test_a_body_swayed_or_animated_in_2_5d_fails_the_body_motion_check(tmp_path):            # the negative test of OR-V25
    d = _base_direction()
    d["tracks"].append({"track": "subject", "op": "subject_sway", "renderer": "directed25d", "params": {}, "id": "fx_sway"})
    r = V.no_body_motion_in_25d(_direction(tmp_path, d, "a.json"))
    assert r["status"] == "FAIL" and "sways the subject" in r["detail"], r
    d = _base_direction()
    d["seen"]["living"].append({"id": "hands", "kind": "body", "where": [0.5, 0.5], "decision": "animate", "effects": ["fx_fire"], "body_motion": True})
    r = V.no_body_motion_in_25d(_direction(tmp_path, d, "b.json"))
    assert r["status"] == "FAIL" and "hands" in r["detail"], r
    assert V.no_body_motion_in_25d(_direction(tmp_path, {"zones": []}, "z.json"))["status"] == "NOT_RUN" and V.no_body_motion_in_25d.kinds == (".json",)


# ---- OR-V19b: wind moves cloth, hair and grass (zone kind "wind") -------------------------------------------------------------------

def grass_clip(path, sways=True, n=3.0):
    """A still camera; smoke drifts (the world is alive elsewhere); a band of grass along the bottom sways sideways, or stands dead."""
    bg, tex = np.tile(background(), (1, 2)), wide_texture(2)
    smoke = (slice(60, 160), slice(60, 260))
    frames = []
    for i in range(seconds(n)):
        f = bg[:, :W].copy()
        sh = int(round(0.7 * i)) % 300
        f[smoke] = tex[smoke[0], smoke[1].start + sh:smoke[1].stop + sh]
        if sways:
            for r in range(200, H):
                f[r] = np.roll(bg[r, :W], int(4 * np.sin(2 * np.pi * (i / FPS * 1.5 + r / 20))))
        frames.append(f)
    return clip(path, frames)


GRASS = [("grass", "wind", (0, 200, 480, 270))]


def test_wind_that_sways_a_band_of_grass_in_its_wind_zone_passes(tmp_path):
    zones_json(tmp_path, "sway", GRASS)
    r = V.living_motion(grass_clip(tmp_path / "sway.mp4"))
    assert r["status"] == "PASS" and "grass " in r["detail"] and r["value"] >= V.ZONE_COVER_MIN, r


def test_a_wind_zone_over_grass_that_stands_dead_fails_by_name(tmp_path):                    # the negative test of OR-V19b
    zones_json(tmp_path, "dead", GRASS)
    r = V.living_motion(grass_clip(tmp_path / "dead.mp4", sways=False))
    assert r["status"] == "FAIL" and "grass zone" in r["detail"] and "G-LIVE-3" in r["detail"], r
    assert V.ZONE_SPEED["wind"] == 2.0


# ---- OR-V19c: snow falls with depth, near flakes larger and faster than far ones -------------------------------------------------------

def band_matte(n, flakes, size, px_per_s, seed, x_lo=W // 2):
    rng = np.random.default_rng(seed)
    x0, y0 = rng.integers(x_lo, W - size, flakes), rng.integers(0, H, flakes)
    out = []
    for i in range(seconds(n)):
        m = np.zeros((H, W), np.float32)
        for x, y in zip(x0, (y0 + px_per_s * i / FPS) % (H - size)):
            m[int(y):int(y) + size, x:x + size] = 255
        out.append(m)
    return out


def depth_case(tmp_path, near_size, near_speed):
    """The alive world with a far band (2 px flakes, 20 px/s) and a near band over the far half; the soldiers' half is the depth map's foreground."""
    p = alive_world_clip(tmp_path / "snow.mp4")
    clip(tmp_path / "far.mp4", band_matte(3.0, 160, 2, 20, 5))
    clip(tmp_path / "near.mp4", band_matte(3.0, 60, near_size, near_speed, 6))
    depth = np.zeros((H, W), np.uint8)
    depth[:, :W // 2], depth[:, W // 2:] = 230, 40
    Image.fromarray(depth).save(tmp_path / "depth.png")
    zones_json(tmp_path, "snow", ZONES, {"particles": {"far": "far.mp4", "near": "near.mp4"}, "depth": "depth.png"})
    return p


def test_near_flakes_larger_and_faster_than_far_ones_pass_with_their_ratios(tmp_path):
    r = V.living_motion(depth_case(tmp_path, near_size=5, near_speed=90))
    assert r["status"] == "PASS" and "near flakes" in r["detail"] and "x the size" in r["detail"], r


def test_snow_whose_near_and_far_flakes_are_alike_has_no_depth_and_fails(tmp_path):         # the negative test of OR-V19c
    r = V.living_motion(depth_case(tmp_path, near_size=2, near_speed=20))
    assert r["status"] == "FAIL" and "snow has no depth" in r["detail"], r
    assert V.NEAR_FAR_MIN == 1.2


def test_snow_with_a_dense_layer_and_no_zones_is_a_fail_not_a_not_run(tmp_path):
    snow, _ = snow_frames(3.0)
    r = V.living_motion(clip(tmp_path / "snowonly.mp4", snow))
    assert r["status"] == "FAIL", r                                                           # lead's ruling 2026-11-20: a lazy generator picks that route


# ---- OR-V19e: a camera move alone is not alive (the cheap whole-frame row, on the delivered clip) ---------------------------------------

def test_a_drifting_camera_over_a_living_world_stays_alive_beyond_the_camera(tmp_path):
    r = V.alive_beyond_camera(alive_world_clip(tmp_path / "alive.mp4", camera_px=1))
    assert r["status"] == "PASS" and r["value"] >= LV.LOCAL_FLOOR, r


def test_a_camera_move_over_a_dead_picture_fails_alive_beyond_the_camera(tmp_path):         # the negative test of OR-V19e
    r = V.alive_beyond_camera(camera_move_clip(tmp_path / "pan.mp4"))
    assert r["status"] == "FAIL" and "camera move alone" in r["detail"], r


def test_a_fade_and_grain_are_not_a_living_world_for_alive_beyond_the_camera(tmp_path, monkeypatch):
    bg = background()
    fade = [bg * (0.4 + 0.6 * i / seconds(3)) for i in range(seconds(3))]
    assert V.alive_beyond_camera(clip(tmp_path / "fade.mp4", fade))["status"] == "FAIL"
    rng = np.random.default_rng(7)
    assert V.alive_beyond_camera(clip(tmp_path / "grain.mp4", [bg + rng.normal(0, 25, bg.shape) for _ in range(seconds(3))]))["status"] == "FAIL"
    assert V.alive_beyond_camera(smoke_clip(tmp_path / "short.mp4", n=0.5))["status"] == "NOT_RUN"
    monkeypatch.setattr(V, "_cv2", lambda: None)
    assert V.alive_beyond_camera(smoke_clip(tmp_path / "nocv.mp4"))["status"] == "NOT_RUN" and V.alive_beyond_camera.kinds == V.living_motion.kinds
