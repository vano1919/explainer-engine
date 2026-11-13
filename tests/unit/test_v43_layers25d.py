"""v4.3 plan P5: layered 2.5D that reads as movement. A fixture picture with a fixture depth map (far sky, a middle ridge, a
near disc with a "face"), so no model is needed: planes and their parallax, faces kept rigid in one plane, every motion
imitation effect on its frame and pure in the frame number, the sound events that drive effects, and the stability gates."""
from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from explainer_engine.core.errors import ContractError
from explainer_engine.production import layers25d as L
from explainer_engine.qa import gates as G

W, H, FPS = 640, 360, 24   # surface effects move a few pixels at 1080p: big enough to see them
FACE = [{"box": (300.0, 120.0, 360.0, 190.0),
         "landmarks": [(315.0, 145.0), (345.0, 145.0), (330.0, 160.0), (318.0, 175.0), (342.0, 175.0)]}]


@pytest.fixture()
def pic(tmp_path):
    """480x270: textured sky (far), a ridge band (middle), ground (near-ish) and a near disc holding the face."""
    h, w = 270, 480
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    rng = np.random.default_rng(7)
    tex = rng.integers(0, 40, (h, w, 1)).astype(np.float32)
    img = np.zeros((h, w, 3), np.float32)
    img[:] = [90, 120, 170]
    ridge = (yy > 110) & (yy < 170)
    img[ridge] = [80, 110, 70]
    img[yy >= 170] = [120, 95, 60]
    disc = (xx - 330) ** 2 + (yy - 160) ** 2 < 55 ** 2
    img[disc] = [190, 140, 110]
    img = np.clip(img + tex, 0, 255).astype(np.uint8)
    depth = np.full((h, w), 0.05, np.float32)
    depth[ridge] = 0.35
    depth[yy >= 170] = 0.55 + 0.2 * (yy[yy >= 170] - 170) / 100
    depth[disc] = 0.95
    path = tmp_path / "pic.png"
    Image.fromarray(img).save(path)
    return path, depth


def _shot(mi, dur=1.0, sid="T", **kw):
    return dict({"shot_id": sid, "target_duration_seconds": dur, "motion_imitation": mi}, **kw)


def _scene(pic, mi, dur=1.0, events=None, faces=FACE, sid="T"):
    path, depth = pic
    p = L.plan(_shot(mi, dur, sid), FPS, events)
    return L.Scene(Image.open(path), p, (W, H), depth, "given", faces, "given")


def _frame(sc, f):
    return L.render_frame(sc, f).astype(np.int16)


# --- the plan --------------------------------------------------------------------------------------------------------------

@pytest.mark.parametrize("mi, match", [
    ([{"effect": "wobble"}], "unknown motion imitation"),
    ([{"effect": "water_shimmer"}], "needs a region"),
    ([{"effect": "push"}, {"effect": "truck"}], "two camera paths"),
    ([{"effect": "shake"}], "BP-24"),
    ([{"effect": "dust", "strength": 3}], "strength"),
    ([{"effect": "mist", "region": [0.5, 0, 0.2, 1]}], "region"),
    ([{"effect": "shake", "at_word": "volcano"}], "not a spoken word"),
])
def test_the_plan_refuses_what_it_cannot_render(mi, match):
    with pytest.raises(ContractError, match=match):
        L.plan(_shot(mi), FPS, script={"audio_lines": []})


def test_a_word_puts_the_shake_on_its_frame():
    shot = _shot([{"effect": "shake", "at_word": "blast"}], dur=2.0, audio_line_ids=["L1"])
    script = {"audio_lines": [{"line_id": "L1", "text": "Then the blast rolled over the ridge."}]}
    p = L.plan(shot, FPS, script=script)
    assert len(p["impacts"]) == 1 and 0 < p["impacts"][0]["frame"] < p["frames"]


def test_the_alive_rule_counts_families_beyond_the_camera():
    assert L.plan(_shot([{"effect": "push"}, {"effect": "handheld"}]), FPS)["families"] == []
    p = L.plan(_shot([{"effect": "push"}, {"effect": "mist"}, {"effect": "fire_flicker", "region": [0, 0, 1, 1]}]), FPS)
    assert p["families"] == ["atmosphere", "light"] and L.ALIVE_MIN == 2


def test_sound_events_drive_shake_and_lightning():
    p = L.plan(_shot([{"effect": "push"}], dur=2.0, sound_events=[
        {"kind": "spot", "what": "eruption boom", "at_s": 1.0, "picture_event": "boom"}]), FPS)
    assert p["impacts"] == [{"frame": 24, "effects": ["shake", "lightning"], "strength": 1.0, "kind": "boom"}]
    assert any(e["effect"] == "lightning" for e in p["effects"])


# --- planes, faces, parallax -----------------------------------------------------------------------------------------

def test_the_depth_splits_into_planes_and_a_face_stays_in_one(pic):
    sc = _scene(pic, [{"effect": "push"}])
    assert len(sc.weights) >= L.LAYERS_MIN and sc.weights[0] == 0.0 and sc.weights[-1] == 1.0
    assert sc.face_one_plane[0] >= L.FACE_ONE_PLANE and sc.face_plane[0] == len(sc.weights) - 1


def test_a_threshold_inside_a_face_moves_behind_it():
    depth = np.tile(np.linspace(0, 1, 200, dtype=np.float32), (100, 1))   # a slope: k-means cuts it evenly
    face = [{"box": (90.0, 20.0, 130.0, 80.0), "landmarks": [(0, 0)] * 5}]
    patch = depth[29:71, 96:124].ravel()   # the face box shrunk as the code shrinks it

    def one_plane_share(ts):
        lab = np.searchsorted(np.array(ts), patch)
        return np.bincount(lab).max() / patch.size

    assert one_plane_share(L.thresholds(depth, None)) < 0.9          # the plain split cuts the face
    assert one_plane_share(L.thresholds(depth, face)) >= L.FACE_ONE_PLANE


def test_a_truck_moves_the_near_plane_more_than_the_far_one(pic):
    p = L.plan(_shot([{"effect": "truck", "direction": "right"}]), FPS)
    near = [L.plane_view(p, f, 1.0, 0.5)["cx"] for f in (0, p["frames"] - 1)]
    far = [L.plane_view(p, f, 0.0, 0.5)["cx"] for f in (0, p["frames"] - 1)]
    assert near[0] == far[0] == 0.0
    assert abs(near[1] - L.NEAR_TRAVEL) < 1e-9 and abs(far[1]) == pytest.approx(L.NEAR_TRAVEL * L.FAR_SHARE)


def test_the_back_plane_covers_every_frame_and_the_shot_starts_on_its_picture(pic, tmp_path):
    path, depth = pic
    shot = _shot([{"effect": "truck"}, {"effect": "handheld"}, {"effect": "mist"}, {"effect": "fire_flicker", "region": [0.55, 0.3, 0.85, 0.9]}])
    r = L.render_clip(shot, path, tmp_path / "t.mp4", width=W, height=H, fps=FPS, depth=depth, faces=FACE)
    rows = {g["gate"]: g for g in r["gates"]["gates"]}
    assert rows["no_uncovered_pixels"]["status"] == "PASS" and rows["starts_on_its_picture"]["status"] == "PASS"
    assert rows["chunks_match"]["status"] == "PASS" and rows["alive_two_families"]["status"] == "PASS"
    assert rows["near_plane_travel"]["measured"] == pytest.approx(L.NEAR_TRAVEL, abs=0.01)
    assert r["total_frames"] == 24 and r["base_zoom"] > 1.0


def test_subject_sway_moves_the_face_plane_rigidly(pic):
    sc = _scene(pic, [{"effect": "subject_sway"}, {"effect": "mist"}], dur=4.0)
    k = sc.sway["plane"]
    a, b = sc.matrices(0)[k], sc.matrices(30)[k]
    assert not np.allclose(a, b)
    # one affine per plane: equal scale on both axes, no shear (the face is never warped inside)
    for m in (a, b):
        lin = m[:, :2]
        assert np.allclose(lin @ lin.T, np.eye(2) * (lin[0] @ lin[0]), atol=1e-9)


# --- each effect: nothing that is not there, something that is, the same twice -------------------------------------------

EFFECT_CASES = [
    {"effect": "fire_flicker", "region": [0.55, 0.3, 0.85, 0.9]},
    {"effect": "sun_shaft_drift", "origin": [0.2, 0.05]},
    {"effect": "ash_fall"}, {"effect": "smoke_drift"}, {"effect": "mist"}, {"effect": "rain"}, {"effect": "embers"},
    {"effect": "dust"},
    {"effect": "water_shimmer", "region": [0, 0.6, 1, 1]}, {"effect": "heat_haze", "region": [0, 0, 1, 0.6]},
    {"effect": "foliage_sway", "region": [0, 0.35, 1, 0.7]},
    {"effect": "subject_sway"},
]


@pytest.mark.parametrize("fx", EFFECT_CASES, ids=lambda e: e["effect"])
def test_each_effect_changes_the_frame_and_is_pure(pic, fx):
    base = _scene(pic, [{"effect": "push"}], dur=2.0)
    sc = _scene(pic, [{"effect": "push"}, fx], dur=2.0)
    f = 31
    a, b = _frame(sc, f), _frame(sc, f)
    assert (a == b).all(), "a frame is a pure function of its number"
    diff = np.abs(a - _frame(base, f)).max(axis=2)
    assert (diff > 4).mean() > 0.0005, f"{fx['effect']} changes nothing"
    later, later_base = _frame(sc, f + 9), _frame(base, f + 9)
    own = np.abs((later - later_base) - (a - _frame(base, f))).max(axis=2)   # the effect itself moves, not only the camera
    assert (own > 4).mean() > 0.0005, f"{fx['effect']} does not move"


def test_surface_effects_stay_inside_their_region(pic):
    base = _scene(pic, [{"effect": "push"}], dur=2.0)
    sc = _scene(pic, [{"effect": "push"}, {"effect": "water_shimmer", "region": [0, 0.7, 1, 1]}], dur=2.0)
    diff = np.abs(_frame(sc, 20) - _frame(base, 20)).max(axis=2)
    assert diff[: int(H * 0.5)].max() <= 2 and (diff[int(H * 0.75):] > 4).mean() > 0.01


@pytest.mark.parametrize("name", ["mist", "smoke_drift"])
def test_mist_and_smoke_stay_off_the_open_sky(pic, name):
    """FL-319: blobs of haze or smoke on a bright open sky read as smudges; the sky is the flat floor of the depth map."""
    path, depth = pic
    depth = depth.copy()
    depth[: int(depth.shape[0] * 0.4)] = 0.0       # an open sky: the farthest plateau of the picture
    pic0 = (path, depth)
    base = _scene(pic0, [{"effect": "push"}], dur=2.0)
    sc = _scene(pic0, [{"effect": "push"}, {"effect": name, "strength": 1.5}], dur=2.0)
    diff = np.abs(_frame(sc, 20) - _frame(base, 20)).max(axis=2)
    sky, ground = diff[: int(H * 0.25)], diff[int(H * 0.5):]
    assert ground.mean() > 1.0, f"{name} must still act on the ground"
    assert sky.mean() < 0.2 * ground.mean(), f"{name} lies on the sky ({sky.mean():.2f} vs {ground.mean():.2f})"


@pytest.mark.parametrize("kind", ["boom", "thunder"])
def test_an_event_effect_waits_for_its_frame(pic, kind):
    sc = _scene(pic, [{"effect": "push"}], dur=2.0, events=[{"frame": 20, "kind": kind}])
    p = sc.p
    assert L.shake_offset(p, 19, H) == (0.0, 0.0) and L.lightning_envelope(p, 19) == 0.0
    step_before = np.abs(_frame(sc, 19) - _frame(sc, 18)).mean()
    step_on = np.abs(_frame(sc, 20) - _frame(sc, 19)).mean()
    assert step_on > 4 * step_before + 2


def test_the_shake_keeps_the_house_amplitude_and_dies_out():
    p = L.plan(_shot([{"effect": "shake", "at_frame": 10, "strength": 1.5}], dur=3.0), FPS)
    amps = [abs(complex(*L.shake_offset(p, f, 1080))) for f in range(p["frames"])]
    assert max(amps[:10]) == 0.0 and max(amps) > 0
    assert max(amps) <= L.SHAKE_MAX_H * 1080 * 1.71
    assert max(amps[10 + int(L.SHAKE_S * FPS) + 1:]) == 0.0


def test_lightning_keeps_to_its_flash_frames():
    p = L.plan(_shot([{"effect": "lightning", "at_frame": 5}], dur=2.0), FPS)
    env = [L.lightning_envelope(p, f) for f in range(p["frames"])]
    assert env[4] == 0 and env[5] == 1.0 and sum(1 for e in env if e >= 0.5) <= L.FLASH_FRAMES_MAX



def test_a_rendered_strike_keeps_to_the_flash_limit(pic):
    sc = _scene(pic, [{"effect": "push"}, {"effect": "lightning", "at_frame": 5, "strength": 1.5}], dur=2.0)
    lum = [float(_frame(sc, f).mean()) / 255.0 for f in range(0, 24)]
    steps = [i for i in range(1, len(lum)) if abs(lum[i] - lum[i - 1]) >= 0.10]
    assert 1 <= len(steps) <= L.FLASHES_PER_S

def test_rack_focus_sharpens_the_near_plane(pic):
    import cv2
    sc = _scene(pic, [{"effect": "rack_focus", "to": "near", "at_frame": 10}, {"effect": "mist"}], dur=2.0)
    disc = (slice(int(0.45 * H), int(0.75 * H)), slice(int(0.6 * W), int(0.78 * W)))

    def sharp(f):
        g = L.render_frame(sc, f).astype(np.float32).mean(axis=2)
        return float(cv2.Laplacian(g, cv2.CV_32F)[disc].var())

    assert sharp(40) > sharp(0) * 1.5


# --- gates ------------------------------------------------------------------------------------------------------------------

def test_a_shot_that_does_not_move_fails_the_frozen_and_alive_gates(pic, tmp_path):
    path, depth = pic
    r = L.render_clip(_shot([], dur=1.0), path, tmp_path / "s.mp4", width=W, height=H, fps=FPS, depth=depth, faces=[],
                      check_chunks=False)
    rows = {g["gate"]: g["status"] for g in r["gates"]["gates"]}
    assert rows["alive_two_families"] == "FAIL" and rows["no_frozen_stretch"] == "FAIL" and r["gates"]["status"] == "FAIL"


def test_without_a_depth_model_the_depth_is_a_formula_and_the_report_says_so(pic, tmp_path, monkeypatch):
    path, _ = pic
    monkeypatch.setenv("EXPLAINER_DEPTH_DIR", str(tmp_path / "no_model"))
    monkeypatch.setenv("EXPLAINER_YUNET", str(tmp_path / "no_model" / "y.onnx"))
    r = L.render_clip(_shot([{"effect": "push"}, {"effect": "mist"}, {"effect": "fire_flicker", "region": [0.55, 0.3, 0.85, 0.9]}]), path, tmp_path / "f.mp4",
                      width=W, height=H, fps=FPS, check_chunks=False)
    rows = {g["gate"]: g for g in r["gates"]["gates"]}
    assert r["depth_basis"] == "formula" and rows["depth_is_real"]["status"] == "REVIEW"
    assert rows["faces_rigid"]["status"] == "NOT_RUN" and r["gates"]["status"] == "INCOMPLETE"


def test_an_end_picture_with_another_layout_is_not_faked_into_the_shot(pic, tmp_path):
    path, depth = pic
    other = tmp_path / "other.png"
    Image.fromarray(np.asarray(Image.open(path))[::-1, ::-1].copy()).save(other)
    r = L.render_clip(_shot([{"effect": "push"}, {"effect": "mist"}, {"effect": "dust"}]), path, tmp_path / "e.mp4",
                      width=W, height=H, fps=FPS, end_picture=other, depth=depth, faces=FACE, check_chunks=False)
    row = next(g for g in r["gates"]["gates"] if g["gate"] == "end_picture_layout")
    assert r["end_picture"]["used"] is False and row["status"] == "REVIEW" and "two shots" in row["detail"]


def test_a_hypothesis_gate_misses_as_review_and_the_verdict_says_review():
    rows = [G.row("a", True, "x", 1), G.row("b", False, "y", 2, level="REVIEW")]
    assert rows[1]["status"] == "REVIEW" and G.verdict(rows)["status"] == "REVIEW"
    assert G.verdict(rows + [G.row("c", False, "z", 3)])["status"] == "FAIL"
    with pytest.raises(ValueError):
        G.row("d", False, "w", 0, level="maybe")


def test_an_unsure_face_stays_rigid_but_steers_nothing(pic):
    unsure = [dict(FACE[0], score=0.72)]   # what YuNet gave a storm cloud on S01_SH009
    sc = _scene(pic, [{"effect": "push"}, {"effect": "subject_sway"}], faces=unsure)
    sure = _scene(pic, [{"effect": "push"}, {"effect": "subject_sway"}], faces=[dict(FACE[0], score=0.94)])
    assert sc.face_one_plane[0] >= 0.98 and sure.face_one_plane[0] >= 0.98
    assert sure.focus == sure.weights[sure.face_plane[0]] and sc.focus == sc.weights[len(sc.weights) // 2]
    assert L.Meter(sc, True).measure_faces is False and L.Meter(sure, True).measure_faces is True


@pytest.mark.parametrize("face", [FACE, []])
def test_an_orbit_moves_the_plane_furthest_from_the_focus_its_travel_only(pic, face):
    sc = _scene(pic, [{"effect": "orbit_small"}], dur=2.0, faces=face)
    first = [L.plane_view(sc.p, 0, w, sc.focus)["cx"] for w in sc.weights]
    last = [L.plane_view(sc.p, sc.p["frames"] - 1, w, sc.focus)["cx"] for w in sc.weights]
    assert max(abs(b - a) for a, b in zip(first, last)) == pytest.approx(L.NEAR_TRAVEL, rel=1e-6)


def test_a_rack_starts_soft_by_design_and_is_not_a_seam(pic, tmp_path):
    path, depth = pic
    r = L.render_clip(_shot([{"effect": "push"}, {"effect": "rack_focus", "to": "near", "at_frame": 10}, {"effect": "mist"},
                             {"effect": "dust"}], dur=2.0), path, tmp_path / "r.mp4", width=W, height=H, fps=FPS,
                      depth=depth, faces=FACE, check_chunks=False)
    rows = {g["gate"]: g for g in r["gates"]["gates"]}
    assert rows["starts_on_its_picture"]["status"] == "PASS" and rows["no_edge_tears"]["status"] == "PASS"


def test_the_sway_starts_at_rest_so_the_shot_starts_on_its_picture(pic):
    sc = _scene(pic, [{"effect": "push"}, {"effect": "subject_sway", "strength": 1.5}])
    m = sc.matrices(0)[sc.sway["plane"]]
    base = L._matrix(L.plane_view(sc.p, 0, sc.weights[sc.sway["plane"]], sc.focus), sc.W, sc.H, sc.sw, sc.sh, sc.z0)
    assert np.allclose(m, base, atol=1e-9)                       # frame 0: no turn, no breath
    m20 = sc.matrices(20)[sc.sway["plane"]]
    base20 = L._matrix(L.plane_view(sc.p, 20, sc.weights[sc.sway["plane"]], sc.focus), sc.W, sc.H, sc.sw, sc.sh, sc.z0)
    assert not np.allclose(m20, base20, atol=1e-6)
