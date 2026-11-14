"""The eye review of the C4A clips (2026-11-14) found four defects no gate could see. Each has its fix and a gate that now
catches it: the scalloped seam round layered people (rest_seam), people cut by the frame (the safe zone, people_in_frame),
a planned truck that came out as a centred zoom (aim_on_target, camera_segments) and effects nobody notices within 3 s
(the swell, effect_seen_3s)."""
from __future__ import annotations

import copy

import numpy as np
import pytest
from PIL import Image

from explainer_engine.production import directed25d as R
from explainer_engine.production import living_director as LD
from explainer_engine.production import living_fx as LFX
from explainer_engine.qa import motion_intent as MI

cv2 = pytest.importorskip("cv2")
H, W = 360, 640
OUT = (480, 270)


def _layers(tmp_path, rough=True, stroke=False):
    rng = np.random.default_rng(7)
    sky = np.full((H, W, 3), (200, 210, 225), np.uint8)
    img = np.clip(sky.astype(np.float32) + rng.normal(0, 4, (H, W, 3)), 0, 255).astype(np.uint8)
    depth = np.repeat(np.linspace(0.05, 0.6, H, dtype=np.float32)[:, None], W, axis=1)
    m = np.zeros((H, W), np.uint8)
    cv2.ellipse(m, (200, 210), (60, 120), 0, 0, 360, 1, -1)              # a "person": a dark body on a pale field
    if rough:                                                            # a hair-like ragged outline: many small nubs
        ys, xs = np.nonzero(cv2.dilate(m, np.ones((3, 3), np.uint8)) - cv2.erode(m, np.ones((3, 3), np.uint8)))
        for k in rng.choice(len(xs), 160, replace=False):
            cv2.circle(m, (int(xs[k]), int(ys[k])), int(rng.integers(1, 3)), 1, -1)
    if stroke:                                                           # a long thin sling hanging off the body
        cv2.line(m, (250, 150), (420, 60), 1, 2)
    img[m > 0] = (60, 45, 35)
    mf = m.astype(np.float32)
    depth[m > 0] = 0.7
    p = tmp_path / "pic.png"
    Image.fromarray(img).save(p)
    plate = img.copy()
    hole = cv2.dilate(mf, np.ones((9, 9), np.uint8))
    plate[hole > 0] = (200, 210, 225)                                   # the fill behind the person: the pale field
    face = np.zeros((H, W), np.float32)
    man = {"lights": [{"id": "sun", "kind": "sun", "point": [0.8, 0.15]}]}
    return p, {"manifest": man, "depth": depth, "plate": plate, "hole": hole, "masks": {"man": mf}, "lights": {}}, face


def _plan(frames=24, **kw):
    return {"shot_id": "T", "frames": frames, "cameras": [], "handheld": None, "rack": None, "effects": [], "far_share": 0.2,
            **kw}


def test_a_rough_outline_keeps_its_nubs_and_the_seam_gate_catches_the_old_bites(tmp_path, monkeypatch):
    p, lay, _ = _layers(tmp_path, rough=True)
    st = R.Stage(p, lay, _plan(), OUT)
    seam = st.rest_seam()
    assert MI.rest_seam_row(seam)["status"] == "PASS", seam
    monkeypatch.setattr(R.Stage, "_strokes", lambda self, parts, r: parts > 0)    # the C4A renderer: every nub cut
    old = R.Stage(p, lay, _plan(), OUT).rest_seam()
    assert old["per_outline_px"] > seam["per_outline_px"] * 3
    assert MI.rest_seam_row(old)["status"] == "FAIL", old


def test_a_real_stroke_is_still_cut_from_its_layer(tmp_path):
    p, lay, _ = _layers(tmp_path, rough=False, stroke=True)
    st = R.Stage(p, lay, _plan(), OUT)
    hard = (lay["masks"]["man"] > 0.5).astype(np.uint8)
    hard = cv2.resize(hard, (st.sw, st.sh), interpolation=cv2.INTER_NEAREST)
    r = max(1, int(round(R.THIN_FILL_PX / 2 * st.sw / 1920)))
    disc = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2 * r + 1, 2 * r + 1))
    parts = hard & (1 - cv2.morphologyEx(hard, cv2.MORPH_OPEN, disc))
    assert st._strokes(parts, r).sum() > 0.5 * parts.sum()            # the sling is a stroke: it stays in the background


def test_the_safe_zone_keeps_the_person_whole_through_a_push_to_the_other_side(tmp_path):
    p, lay, _ = _layers(tmp_path, rough=False)
    cams = [{"op": "push", "strength": 8.0, "from": 0, "to": 24, "easing": "ease_out", "target": {"point": [0.95, 0.5]}}]
    face = [0.29, 0.28, 0.34, 0.36]
    free = R.Stage(p, lay, _plan(cameras=cams), OUT)
    free.keep = R.Stage(p, lay, _plan(cameras=cams, keep_in_frame=[{"face": face}]), OUT).keep
    free._frame_people = lambda z0, s, dp, cx, cy, tx, ty, ox, far: (s, dp, cx, cy)   # measured, not framed
    assert free.people_cut()["share"] > MI.PEOPLE_CUT_FAIL                # without the safe zone the push cuts him
    kept = R.Stage(p, lay, _plan(cameras=cams, keep_in_frame=[{"face": face}]), OUT)
    cut = kept.people_cut()
    assert cut["kept"] == 1 and MI.people_in_frame_row(cut)["status"] == "PASS", cut
    assert kept.view(23)["s"] > 1.0                                       # the camera still moves


def test_an_aim_outside_its_object_fails(tmp_path):
    p, lay, _ = _layers(tmp_path, rough=False)
    bad = [{"op": "push", "strength": 1.0, "from": 0, "to": 24, "target": {"mask": "man", "point": [0.5, 0.5]}}]
    good = [{"op": "push", "strength": 1.0, "from": 0, "to": 24, "target": {"mask": "man", "point": [0.31, 0.58]}}]
    assert MI.aim_row(R.Stage(p, lay, _plan(cameras=bad), OUT).aim_check())["status"] == "FAIL"
    assert MI.aim_row(R.Stage(p, lay, _plan(cameras=good), OUT).aim_check())["status"] == "PASS"


def test_a_truck_that_came_out_as_a_zoom_fails_its_segment():
    cams = [{"op": "truck", "direction": "right", "from": 24, "to": 48, "strength": 2.0}]
    zoom_only = [{"t": i / 12, "zoom_pct": i * 0.5, "pan_x_pct": 0.0, "pan_y_pct": 0.0} for i in range(25)]
    lateral = [{"t": i / 12, "zoom_pct": 0.0, "pan_x_pct": -0.3 * i, "pan_y_pct": 0.0} for i in range(25)]
    assert MI.segment_rows(cams, zoom_only, 24.0)[0]["status"] == "FAIL"
    assert MI.segment_rows(cams, lateral, 24.0)[0]["status"] == "PASS"
    push = [{"op": "push", "from": 0, "to": 24, "strength": 1.0}]
    views = [{"s": 1.0 + 0.06 * f / 23} for f in range(24)]
    flat = [{"t": i / 12, "zoom_pct": 0.0, "pan_x_pct": 0.0, "pan_y_pct": 0.0} for i in range(25)]
    assert MI.segment_rows(push, flat, 24.0, views)[0]["status"] == "FAIL"


def test_the_sun_swells_within_its_seconds_and_a_weak_effect_is_flagged():
    assert LFX.swell(0.0) == pytest.approx(LFX.SWELL_FROM)
    assert LFX.swell(LFX.SWELL_S) == pytest.approx(1.0) and LFX.SWELL_S <= 3.0
    rows = [{"op": "sun_shaft", "index": 0, "change_p95": 40.0, "at_s": 2.9},
            {"op": "mist", "index": 1, "change_p95": 3.0, "at_s": 2.9}]
    r = MI.effects_seen_row(rows)
    assert r["status"] == "REVIEW" and "mist" in r["detail"] and "sun_shaft" not in r["detail"]


def test_the_sun_shaft_is_seen_to_change_within_3_s(tmp_path):
    p, lay, _ = _layers(tmp_path, rough=False)
    st = R.Stage(p, lay, _plan(frames=72, effects=[{"op": "sun_shaft", "strength": 1.0, "light": "sun", "params": {}}]), OUT)
    for f in range(0, 72, 6):
        st.render(f, {})
    seen = st.effects_seen()[0]
    assert seen["change_p95"] >= MI.SEEN_REVIEW, seen


def test_the_director_reads_crowds_carries_an_early_word_and_writes_the_safe_zone():
    assert LD._centre({"parts": [[[0.17, 0.62], [0.165, 0.45]], [[0.41, 0.43], [0.41, 0.55]]]})[0] == pytest.approx(0.289, abs=0.01)
    d = {"intent": "intended", "people_mid_or_close": False,
         "seen": {"objects": [{"id": "spade", "points": [[0.3, 0.4], [0.4, 0.6]], "names": ["spades"]}], "living": []}}
    tracks, why = LD.choose_camera(d, [{"word": "spades", "start_frame": 6}], 84, 24.0, [], set())
    assert tracks[0]["op"] == "push" and not tracks[0].get("timing", {}).get("start")     # the base move, not a snap at 0.25 s
    assert tracks[0]["target"]["mask"] == "spade" and "too early for an accent" in why[0]
    keep = LD.keep_in_frame([{"box": [0.3, 0.3, 0.35, 0.38]}],
                            [{"op": "candle", "target": {"lights": ["c1"]}}, {"op": "snow", "target": {}}])
    assert keep[0]["face"] == [0.3, 0.3, 0.35, 0.38] and not keep[0].get("soft")
    assert keep[1] == {"light": "c1", "soft": True, "why": "the candle effect lives on it"} and len(keep) == 2


def test_clouds_and_sun_light_stay_off_a_kept_person_and_a_smeared_face_fails(tmp_path):
    """C5's first renders: the stronger cloud drift smeared a face standing against the sky and the sun bloom washed out
    heads. The sky slides only where the frame is far and never on a kept person; ``face_intact`` FAILs a smear."""
    p, lay, _ = _layers(tmp_path, rough=False)
    lay["depth"][:] = 0.01                                               # all sky behind him, so the blur would leak
    lay["depth"][lay["masks"]["man"] > 0] = 0.7
    keep = [{"face": [0.29, 0.28, 0.34, 0.36]}]
    fx = [{"op": "cloud_drift", "strength": 1.0, "params": {}}]
    a = R.Stage(p, lay, _plan(frames=72, keep_in_frame=keep), OUT).render(70)
    b = R.Stage(p, lay, _plan(frames=72, keep_in_frame=keep, effects=fx), OUT).render(70)
    head = (slice(int(0.25 * OUT[1]), int(0.40 * OUT[1])), slice(int(0.28 * OUT[0]), int(0.35 * OUT[0])))
    assert np.abs(a[head].astype(float) - b[head].astype(float)).mean() < 3.0
    assert MI.face_intact_row({"ncc": 0.80, "frame": 68, "faces": 2})["status"] == "FAIL"
    assert MI.face_intact_row({"ncc": 0.96, "frame": 68, "faces": 2})["status"] == "PASS"
    assert MI.face_intact_row({"ncc": 1.0, "frame": None, "faces": 0})["status"] == "NOT_RUN"
