"""Regression guard for the camera jumps the creator saw by eye (S05_SH020 frame 73/143 snaps, the S7 whip back)."""
from __future__ import annotations

import numpy as np

from explainer_engine.qa import motion_intent as MI


def _clip(steps: list[float], n: int = 120) -> list[np.ndarray]:
    """Frames of a horizontal gradient that slides by the given per-frame step (pixels) - a stand-in for a camera move."""
    x = np.linspace(0, 255, 480, dtype=np.float32)
    base = np.tile(np.concatenate([x, x[::-1]]), (270, 1))
    out, pos = [], 0.0
    for i in range(n):
        pos += steps[i] if i < len(steps) else 0.2
        k = int(round(pos)) % base.shape[1]
        out.append(np.roll(base, k, axis=1)[:, :480])
    return out


def test_one_frame_snap_fails():
    steps = [0.3] * 120
    steps[72] = 60.0                      # the frame-73 snap: one huge step ...
    steps[73] = -60.0                     # ... and back
    r = MI.frame_jumps(_clip(steps))
    assert r["snaps"] or r["whips"]
    assert MI.frame_jumps_row(r)["status"] == "FAIL"


def test_short_whip_back_fails_but_a_one_second_accent_passes():
    whip = [0.4] * 120
    for i in range(147, 151):             # 4 frames of very fast motion: the S7 whip back
        whip[i - 40] = 45.0
    assert MI.frame_jumps_row(MI.frame_jumps(_clip(whip)))["status"] == "FAIL"
    accent = [0.4] * 120
    for i in range(60, 75):               # a 15-frame accent snap rising and settling: deliberate, allowed
        accent[i] = 6.0 + 2.0 * np.sin(np.pi * (i - 60) / 15)
    assert MI.frame_jumps_row(MI.frame_jumps(_clip(accent)))["status"] == "PASS"


def test_smooth_drift_passes():
    assert MI.frame_jumps_row(MI.frame_jumps(_clip([0.5] * 120)))["status"] == "PASS"


def test_watch_collects_steps_and_reports_camera_jumps():
    w = MI.Watch()
    steps = [0.3] * 60
    steps[30] = 60.0
    steps[31] = -60.0
    for f, g in enumerate(_clip(steps, 60)):
        rgb = np.dstack([g, g, g]).astype(np.uint8)
        w.add(f, rgb, np.zeros(g.shape, np.float32), None)
    r = w.summary()["camera_jumps"]
    assert MI.frame_jumps_row(r)["status"] == "FAIL"
