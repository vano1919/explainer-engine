"""The owner's rules of 2026-11-14 measured on frames (qa/liveliness.py, BP-194, BP-195, BP-197): a still world is caught even
when the director said "still", the camera taken out leaves what lives, zoom moves are measured per step like the LTX clips,
a move the words call must be snappy and land on its target, and a REVIEW clip waits for the director's round."""
from __future__ import annotations

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from explainer_engine.qa import liveliness as L  # noqa: E402

FPS = 24.0


def _texture(w=640, h=360, seed=1):
    rng = np.random.default_rng(seed)
    t = cv2.GaussianBlur(rng.uniform(0, 255, (h, w)).astype(np.float32), (0, 0), 3)
    t = (t - t.min()) / (t.max() - t.min()) * 255
    return np.repeat(t[..., None], 3, axis=2).astype(np.uint8)


def _zoom(img, s, dx=0.0):
    h, w = img.shape[:2]
    M = cv2.getRotationMatrix2D((w / 2, h / 2), 0, s)
    M[0, 2] += dx
    return cv2.warpAffine(img, M, (w, h), borderMode=cv2.BORDER_REFLECT)


def _blob(img, t):
    out = img.copy()
    x = int(80 + 150 * t)
    cv2.circle(out, (x, 180), 45, (255, 255, 255), -1)
    return out


BASE = _texture()


def test_a_frozen_clip_is_caught_and_a_living_one_passes():
    still = [BASE.copy() for _ in range(72)]
    rows, m = L.liveliness_rows(still, FPS, "still_by_design")
    by = {r["gate"]: r for r in rows}
    assert by["alive_change"]["status"] == "REVIEW" and by["no_frozen_second"]["status"] == "REVIEW"
    assert m["frozen"]["frozen"] == m["frozen"]["windows"] > 0 and m["reference_pct_s"] == [3.6, 12.2]
    alive = [_blob(BASE, f / FPS) for f in range(72)]
    by = {r["gate"]: r for r in L.liveliness_rows(alive, FPS)[0]}
    assert by["no_frozen_second"]["status"] == "PASS" and by["alive_beyond_camera"]["status"] == "PASS"


def test_a_camera_move_alone_is_not_alive_beyond_the_camera():
    frames = [_zoom(BASE, 1 + 0.12 * f / 71) for f in range(72)]
    ch, lc = L.change_per_s(frames, FPS), L.local_change_per_s(frames, FPS)
    assert ch["pct_per_s"] > 2 * lc["pct_per_s"]
    assert lc["pct_per_s"] < L.LOCAL_FLOOR


def test_camera_curve_and_moves_measure_a_snappy_and_a_slow_zoom():
    # hold 1 s, then a 10 % zoom in 0.5 s, then hold: snappy
    def s_at(f):
        return 1.0 + 0.10 * min(1.0, max(0.0, (f - 24) / 12))
    snappy = [_zoom(BASE, s_at(f)) for f in range(72)]
    ms = L.moves(L.camera_curve(snappy, FPS))
    z = [m for m in ms if m["axis"] == "zoom"]
    assert len(z) == 1 and 8.5 <= z[0]["amount_pct"] <= 11.5 and z[0]["rise_s"] <= 0.6 and 0.8 <= z[0]["from_s"] <= 1.1
    rows, _ = L.camera_rows(L.camera_curve(snappy, FPS), [{"word": "nobody", "frame": 24, "fps": FPS}], "intended")
    assert {r["gate"]: r["status"] for r in rows} == {"camera_amount": "PASS", "move_on_word": "PASS"}
    slow = [_zoom(BASE, 1.0 + 0.10 * f / 71) for f in range(72)]
    rows, _ = L.camera_rows(L.camera_curve(slow, FPS), [{"word": "nobody", "frame": 0, "fps": FPS}], "intended")
    by = {r["gate"]: r for r in rows}
    assert by["move_on_word"]["status"] == "REVIEW" and "snappy" in by["move_on_word"]["detail"]
    small = [_zoom(BASE, 1.0 + 0.03 * f / 71) for f in range(72)]
    rows, _ = L.camera_rows(L.camera_curve(small, FPS), None, "intended")
    assert rows[0]["gate"] == "camera_amount" and rows[0]["status"] == "REVIEW"
    assert L.camera_rows(L.camera_curve(small, FPS), None, "still_by_design")[0] == []


def test_a_move_far_from_its_word_is_review():
    frames = [_zoom(BASE, 1.0 + 0.10 * min(1.0, max(0.0, (f - 48) / 12))) for f in range(72)]
    rows, _ = L.camera_rows(L.camera_curve(frames, FPS), [{"word": "German", "frame": 6, "fps": FPS}], "intended")
    mw = [r for r in rows if r["gate"] == "move_on_word"][0]
    assert mw["status"] == "REVIEW" and "no camera move starts" in mw["detail"]


def test_word_focus_grows_or_centres_the_named_target():
    still = [(0.70, 0.40, 0.80, 0.60)] * 60
    assert L.word_focus_row(L.word_focus(still, 20, FPS), "nobody", "thomas")["status"] == "REVIEW"
    grow = [(0.70, 0.40, 0.80, 0.60)] * 20 + [(0.62, 0.30, 0.82, 0.70)] * 40
    assert L.word_focus_row(L.word_focus(grow, 20, FPS), "nobody", "thomas")["status"] == "PASS"
    centre = [(0.70, 0.40, 0.80, 0.60)] * 20 + [(0.55, 0.40, 0.65, 0.60)] * 40
    assert L.word_focus_row(L.word_focus(centre, 20, FPS), "nobody", "thomas")["status"] == "PASS"
    assert L.word_focus_row(L.word_focus([None] * 60, 20, FPS), "x", "y")["status"] == "NOT_RUN"


def test_a_review_clip_waits_for_the_directors_round():
    rows = [{"gate": "alive_change", "status": "REVIEW"}, {"gate": "fill_reveal", "status": "PASS"}]
    assert L.delivery_row(rows, None)["status"] == "FAIL"
    assert L.delivery_row(rows, [{"looked_at": [0, 120], "answers": ["fill_reveal"]}])["status"] == "FAIL"
    ok = L.delivery_row(rows, [{"looked_at": [0, 120], "answers": {"alive_change": "snow added, re-rendered"}}])
    assert ok["status"] == "PASS"
    assert L.delivery_row([{"gate": "x", "status": "PASS"}], None)["status"] == "PASS"
