"""P1 (roadmap 2026-11-14 B.10, H.1): the three deterministic defect detectors and the intent check, on synthetic frames:
a revealed fill band is measured, a ghost copy of a moved layer scores high while a clean edge does not, a blurred target
loses its sharpness ratio, and still / push / truck are read from the measured motion. Plus the telemetry of the unchanged
layers25d renderer (fill revealed after a truck, against frame 0)."""
from __future__ import annotations

import numpy as np
import pytest

from explainer_engine.qa import gates as G
from explainer_engine.qa import motion_intent as MI

cv2 = pytest.importorskip("cv2")


def _texture(h, w, seed=3):
    rng = np.random.default_rng(seed)
    t = cv2.GaussianBlur(rng.uniform(0, 255, (h, w)).astype(np.float32), (0, 0), 2.0)
    return np.clip((t - t.mean()) * 4 + 128, 0, 255)


def test_reveal_measures_share_and_band():
    maps = [np.zeros((270, 480), np.float32) for _ in range(3)]
    maps[2][100:120, 50:400] = 1.0                # a 20-row band at 270 rows -> 80 px at 1080
    r = MI.reveal(maps, 1080)
    assert r["frame"] == 2 and 70 <= r["band_px"] <= 90 and r["share"] == pytest.approx(20 * 350 / (270 * 480), rel=0.01)
    assert MI.reveal_row(r)["status"] == G.REVIEW
    clean = MI.reveal([np.zeros((270, 480), np.float32)] * 4)
    assert clean["share"] == 0 and MI.reveal_row(clean)["status"] == G.PASS


def test_fill_seen_on_frame_zero_is_not_a_reveal():
    m = np.zeros((270, 480), np.float32)
    m[10:20, 10:20] = 1
    assert MI.reveal([m, m.copy()])["share"] == 0


def _scene_with_layer(ghost: bool, v=(12.0, 0.0)):
    h, w = 540, 960
    bg = np.full((h, w), 120.0, np.float32) + _texture(h, w, 1) * 0.05
    obj = _texture(h, w, 9)
    alpha = np.zeros((h, w), np.float32)
    alpha[200:340, 400:520] = 1
    frame = bg.copy()
    if ghost:                                     # what a split layer leaves behind: its own content shifted by -v
        sh = MI._shift(obj * alpha, v[0], v[1])
        sa = MI._shift(alpha, v[0], v[1])
        frame = frame * (1 - 0.8 * sa) + sh * 0.8
    frame = frame * (1 - alpha) + obj * alpha
    return frame, alpha


def test_ghost_copy_scores_high_and_clean_edge_low():
    f_ghost, a = _scene_with_layer(True)
    f_clean, _ = _scene_with_layer(False)
    g = MI.ghost_score(f_ghost, a, (12.0, 0.0))
    c = MI.ghost_score(f_clean, a, (12.0, 0.0))
    assert g["score"] > MI.GHOST_REVIEW > c["score"]
    assert MI.ghost_score(f_ghost, a, (0.5, 0.0)) is None      # too small a shift to tell a copy from the edge


def test_target_sharpness_catches_a_blurred_target():
    img = np.dstack([_texture(540, 960)] * 3).astype(np.uint8)
    blur = cv2.GaussianBlur(img, (0, 0), 5)
    mask = np.zeros((540, 960), np.float32)
    mask[100:400, 200:700] = 1
    r = MI.target_sharpness(img, blur, mask, mask)
    assert r["ratio"] < 0.2 and MI.target_sharpness_row(r, "photo")["status"] == G.REVIEW
    same = MI.target_sharpness(img, img, mask, mask)
    assert same["ratio"] == 1.0 and MI.target_sharpness_row(same, "photo")["status"] == G.PASS
    # blurred from the first frame on: first == last, so only the picture shows it (Stage B v1 S08_SH002)
    both = MI.target_sharpness(blur, blur, mask, mask, picture=img)
    assert both["ratio"] == 1.0 and both["picture_to_end"] < 0.2
    assert MI.target_sharpness_row(both, "photo")["status"] == G.REVIEW
    wire = np.zeros((540, 960), np.float32)
    wire[200:204, 100:800] = 1                    # a thin target: 3 erosions would leave nothing
    assert MI.sharpness(img, wire) == MI.sharpness(img, wire)


def _zoomed(img, s, dx=0.0, dy=0.0):
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    m[0, 2] += dx
    m[1, 2] += dy
    return cv2.warpAffine(img, m, (w, h), borderMode=cv2.BORDER_REFLECT)


def test_intent_rows_read_still_push_and_truck():
    img = np.dstack([_texture(540, 960, 5)] * 3).astype(np.uint8)
    still = MI.global_motion(img, img)
    assert MI.intent_rows("still_by_design", {}, still)[0]["status"] == G.PASS
    push = MI.global_motion(img, _zoomed(img, 1.06))
    assert MI.intent_rows("intended", {"move": "push"}, push)[0]["status"] == G.PASS
    assert MI.intent_rows("still_by_design", {}, push)[0]["status"] == G.REVIEW
    truck = MI.global_motion(img, _zoomed(img, 1.0, dx=-30))       # camera right: the picture moves left
    assert MI.intent_rows("intended", {"move": "truck", "direction": "right"}, truck)[0]["status"] == G.PASS
    assert MI.intent_rows("intended", {"move": "truck", "direction": "left"}, truck)[0]["status"] == G.REVIEW


def test_target_towards_centre():
    assert MI.target_towards_centre((300, 300), (700, 450), (1920, 1080))["status"] == G.PASS
    assert MI.target_towards_centre((900, 500), (300, 300), (1920, 1080))["status"] == G.REVIEW


def test_layers25d_telemetry_reveals_fill_after_a_truck(tmp_path):
    from PIL import Image
    from explainer_engine.production import layers25d as L
    h, w = 270, 480
    img = np.dstack([_texture(h, w, 2)] * 3).astype(np.uint8)
    depth = np.full((h, w), 0.1, np.float32)
    depth[120:230, 150:300] = 0.95
    p = tmp_path / "p.png"
    Image.fromarray(img).save(p)
    shot = {"shot_id": "T", "target_duration_seconds": 1.0,
            "motion_imitation": [{"effect": "truck", "direction": "right", "strength": 1.5}, {"effect": "mist"},
                                 {"effect": "dust"}]}
    plan = L.plan(shot, 24)
    sc = L.build_scene(p, plan, (480, 270), depth=depth, faces=[])
    t0 = MI.layers25d_telemetry(sc, 0)
    t1 = MI.layers25d_telemetry(sc, 23)
    assert t1["fill"].mean() > t0["fill"].mean() + 0.002     # frame 0 shows only the thin dilation ring of the hole
    assert MI.reveal([t0["fill"], t1["fill"]])["band_px"] > 0
    assert any(abs(r["v"][0]) > 1 for r in t1["layers"])
