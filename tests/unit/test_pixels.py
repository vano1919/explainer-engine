"""The QA loop's pixel checks (qa/pixels.py; the creator, 2026-10-20: check the video after every two rendered parts): each
check on a tiny synthetic video made with numpy + ffmpeg, whose first frame is timed frame BASE (a later chunk pair)."""
import subprocess

import numpy as np
import pytest
from PIL import Image, ImageDraw, ImageFilter

pytest.importorskip("cv2")
pytest.importorskip("scenedetect")
pytest.importorskip("imagehash")

from explainer_engine.finish import bubbles as BUB  # noqa: E402
from explainer_engine.production import assemble as A  # noqa: E402
from explainer_engine.qa import pixels as PX  # noqa: E402

FPS = 30
BASE = 300  # the video's first frame is timed frame 300 (10 s): far from the episode's planned fades
OUT = (480, 270)
PW, PH = 2048, 1152


def _picture(seed: int) -> Image.Image:
    """A busy picture ORB can follow: random flat shapes in ink outlines, softened a little."""
    rng = np.random.default_rng(seed)
    im = Image.new("RGB", (PW, PH), tuple(int(x) for x in rng.integers(30, 90, 3)))
    d = ImageDraw.Draw(im)
    for _ in range(420):
        x, y = rng.integers(0, PW), rng.integers(0, PH)
        w, h = rng.integers(20, 160, 2)
        col = tuple(int(c) for c in rng.integers(0, 140, 3))  # dark and saturated: nothing cream
        (d.rectangle if rng.random() < 0.5 else d.ellipse)([x, y, x + w, y + h], fill=col, outline=(10, 10, 10), width=3)
    return im.filter(ImageFilter.GaussianBlur(1.2))


PICS = {"A": _picture(1), "B": _picture(2)}


def _frame(pic: str, box) -> np.ndarray:
    return np.asarray(PICS[pic].resize(OUT, Image.BICUBIC, box=tuple(box)))


def _video(path, frames: list[np.ndarray]):
    w, h = OUT
    p = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r",
                          str(FPS), "-i", "-", "-c:v", "libx264", "-crf", "16", "-pix_fmt", "yuv420p", str(path)],
                         stdin=subprocess.PIPE)
    for fr in frames:
        p.stdin.write(np.ascontiguousarray(fr, dtype=np.uint8).tobytes())
    p.stdin.close()
    assert p.wait() == 0
    return path


def _shot(sid, pic, f0, f1, motion=None, accents=(), bubbles=()):
    m = dict(motion or {"kind": "hold", "z0": 1.0, "z1": 1.0}, ein=True, eout=True)
    return {"id": sid, "picture": pic, "start_frame": f0, "end_frame": f1, "start": f0 / FPS, "end": f1 / FPS,
            "transition": "cut", "render_motion": m, "motion": m, "accents": list(accents), "bubbles": list(bubbles)}


def _timed(shots):
    return {"fps": FPS, "frames": 10000, "shots": shots, "visual_beats": [], "face_sheets": {},
            "pictures": {"A": {"aspect": 16 / 9}, "B": {"aspect": 16 / 9}}}


def _render(shots, override=None) -> list[np.ndarray]:
    """The frames the plan says (assemble.motion_box per shot); ``override(f, box, shot)`` may change a frame's
    (picture, box) to simulate a renderer fault."""
    out = []
    for s in shots:
        for f in range(s["start_frame"], s["end_frame"]):
            u = (f - s["start_frame"]) / max(1, s["end_frame"] - s["start_frame"] - 1)
            pic, box = s["picture"], A.motion_box(s["render_motion"], PW, PH, u)
            if override:
                pic, box = override(f, box, s) or (pic, box)
            out.append(_frame(pic, box))
    return out


def _rules(found, sev=None):
    return {f["rule"] for f in found if sev is None or f["severity"] == sev}


def test_an_unplanned_cut_fails_and_a_planned_one_passes(tmp_path):
    # the video cuts A -> B at frame 330 and B -> A at 360; the plan knows only the cut at 360
    shots = [_shot("SH1", "A", BASE, BASE + 60), _shot("SH2", "A", BASE + 60, BASE + 90)]
    video = _video(tmp_path / "v.mp4", _render(shots, lambda f, box, s: ("B", box) if BASE + 30 <= f < BASE + 60 else None))
    plan = PX.planned(_timed(shots))
    cuts = PX.detect_cuts(video)
    found = PX.check_cuts(cuts, plan, FPS, BASE, 90)
    assert _rules(found, "FAIL") == {"PX-CUT-EXTRA"}
    assert any("11.00 s" in f["detail"] for f in found)  # frame 330, in timed time
    planned = [_shot("SH1", "A", BASE, BASE + 30), _shot("SH2", "B", BASE + 30, BASE + 60), _shot("SH3", "A", BASE + 60, BASE + 90)]
    assert not PX.check_cuts(cuts, PX.planned(_timed(planned)), FPS, BASE, 90)


def test_a_view_plans_cut_from_the_wide_to_a_close_up_is_planned(tmp_path):
    # one shot, two views: the wide (A) until frame 330, then the face close-up (B); the face track has no run for the wide
    sh = _shot("SH1", "A", BASE, BASE + 60)
    sh["views"] = [{"start_frame": BASE, "end_frame": BASE + 30}, {"start_frame": BASE + 30, "end_frame": BASE + 60}]
    video = _video(tmp_path / "v.mp4", _render([sh], lambda f, box, s: ("B", box) if f >= BASE + 30 else None))
    assert not PX.check_cuts(PX.detect_cuts(video), PX.planned(_timed([sh])), FPS, BASE, 60)
    del sh["views"]
    assert _rules(PX.check_cuts(PX.detect_cuts(video), PX.planned(_timed([sh])), FPS, BASE, 60)) == {"PX-CUT-EXTRA"}


def test_a_camera_jump_inside_a_shot_is_a_review_and_a_smooth_push_is_clean(tmp_path):
    push = {"kind": "push", "z0": 1.1, "z1": 1.16}
    shots = [_shot("SH1", "A", BASE, BASE + 60, push)]
    t = _timed(shots)
    plan = PX.planned(t)
    smooth = _video(tmp_path / "smooth.mp4", _render(shots))
    found, stats = PX.check_camera(t, plan, PX.scan(smooth, set())["steps"], BASE)
    assert not found and stats["SH1"]["frames"] > 40

    def reset(f, box, s):  # from frame 330 the move restarts 60 px (picture px) to the side: the "reset" of CC-06
        return ("A", (box[0] + 60, box[1], box[2] + 60, box[3])) if f >= BASE + 30 else None
    jumped = _video(tmp_path / "jump.mp4", _render(shots, reset))
    found, _ = PX.check_camera(t, plan, PX.scan(jumped, set())["steps"], BASE)
    assert _rules(found) == {"PX-CAM-JUMP"} and all(f["severity"] == "REVIEW" for f in found)
    assert any(abs(f["t"] - (BASE + 30) / FPS) < 0.05 for f in found)


def test_a_frozen_picture_where_the_plan_moves_fails_and_black_is_a_review(tmp_path):
    pan = {"kind": "pan", "z0": 1.1, "z1": 1.1, "dx": 0.08}
    shots = [_shot("SH1", "A", BASE, BASE + 90, pan)]
    t = _timed(shots)
    held = {}

    def stuck(f, box, s):  # frames 330-374 repeat frame 330: the renderer stuck while the plan pans
        if f == BASE + 30:
            held["box"] = box
        return ("A", held["box"]) if BASE + 30 <= f < BASE + 75 else None
    video = _video(tmp_path / "frozen.mp4", _render(shots, stuck))
    sc = PX.scan(video, set())
    fb = PX.freeze_black(video)
    found = PX.check_freeze_black(fb, t, PX.planned(t), sc["steps"], BASE, sc["count"])
    assert _rules(found, "FAIL") == {"PX-FROZEN"}

    # a held shot that does not move is not frozen; a black stretch in the middle is a REVIEW
    held_shots = [_shot("SH1", "A", BASE, BASE + 90)]
    frames = _render(held_shots)
    for k in range(30, 60):
        frames[k] = np.zeros_like(frames[k])
    video = _video(tmp_path / "black.mp4", frames)
    t = _timed(held_shots)
    sc = PX.scan(video, set())
    found = PX.check_freeze_black(PX.freeze_black(video), t, PX.planned(t), sc["steps"], BASE, sc["count"])
    assert _rules(found) == {"PX-BLACK"} and not _rules(found, "FAIL")


def _cut_pair(tmp_path, z2: float, name: str):
    shots = [_shot("SH1", "A", BASE, BASE + 30, {"kind": "hold", "z0": 1.1, "z1": 1.1}),
             _shot("SH2", "A", BASE + 30, BASE + 60, {"kind": "hold", "z0": z2, "z1": z2})]
    t = _timed(shots)
    plan = PX.planned(t)
    video = _video(tmp_path / name, _render(shots))
    sc = PX.scan(video, {29, 30})
    return PX.check_jump_cuts(t, plan, sc["frames"], BASE)


def test_a_cut_to_the_same_picture_at_almost_the_same_framing_is_a_jump_cut(tmp_path):
    found, rows = _cut_pair(tmp_path, 1.2, "near.mp4")  # 1.2 / 1.1 = 1.09: neither the same framing nor a full step
    assert rows[0]["same_picture"] and _rules(found) == {"PX-JUMP-CUT"}
    found, rows = _cut_pair(tmp_path, 1.5, "step.mp4")  # 1.36: a full step
    assert not found
    found, rows = _cut_pair(tmp_path, 1.1, "same.mp4")  # the same framing continues: not a jump cut
    assert rows[0]["same_picture"] and not found


def test_a_bubble_over_a_face_is_a_review(tmp_path):
    shots = [_shot("SH1", "A", BASE, BASE + 60, bubbles=[{"who": "ann", "text": "Hi.", "start_frame": BASE + 20,
                                                          "end_frame": BASE + 50}])]
    frames = _render(shots)
    for k in range(20, 50):  # the bubble the renderer drew: a cream rounded box with ink, top right
        im = Image.fromarray(frames[k])
        d = ImageDraw.Draw(im)
        d.rounded_rectangle([300, 30, 450, 90], radius=14, fill=BUB.FILL[:3], outline=(20, 20, 20), width=3)
        frames[k] = np.asarray(im)
    video = _video(tmp_path / "bubble.mp4", frames)
    t = _timed(shots)
    items = PX.bubble_frames(t, BASE, 60)
    sc = PX.scan(video, {x for it in items for x in (it["pre"], it["mid"])})
    on_face = lambda fr: [(620.0, 80.0, 780.0, 240.0)]  # noqa: E731  (960 px frame: the bubble is at 600-900 x 60-180)
    found, rows = PX.check_bubble_faces(t, sc["frames"], items, None, on_face)
    assert rows[0]["bubble"] is not None and _rules(found) == {"PX-BUBBLE-FACE"}
    found, _ = PX.check_bubble_faces(t, sc["frames"], items, None, lambda fr: [(100.0, 300.0, 200.0, 420.0)])
    assert not found


def test_without_the_face_model_the_face_check_is_skipped_not_failed(tmp_path, monkeypatch):
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "missing.onnx"))
    shots = [_shot("SH1", "A", BASE, BASE + 45)]
    video = _video(tmp_path / "v.mp4", _render(shots))
    r = PX.check_video(_timed(shots), video, BASE / FPS)
    assert any("YuNet" in s for s in r["skipped"])
    assert not [f for f in r["findings"] if f["severity"] == "FAIL"]


def test_a_word_slam_is_planned_so_its_dim_and_blur_are_no_camera_jump():
    """BP-97: the slam blurs and dims the picture in its first frames; the camera check skips its hold (titans 28.7 s)."""
    acc = [{"kind": "slam_text", "start": 11.0, "start_frame": BASE + 30, "strength": 0.6, "text": "PAPERWORK",
            "pos": [0.5, 0.5]}]
    plan = PX.planned(_timed([_shot("SH001", "A", BASE, BASE + 120, accents=acc)]))
    skip = PX._skip_frames(plan, {})
    assert {BASE + 30, BASE + 31, BASE + 45} <= skip
