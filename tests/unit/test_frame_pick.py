"""BP-199 (the owner, 2026-11-14): the frame a continuation or a still takes from a clip is chosen by its person: the face
that stands still beats a sharper frame whose face is mid-move; a one-frame false face loses to the face of the window;
without a face the frame decides and the report goes to the reviewer."""
from __future__ import annotations

import numpy as np
import pytest

from explainer_engine.finish import frame_pick as FP
from explainer_engine.qa import gates as G

cv2 = pytest.importorskip("cv2")
H, W = 180, 320
FACE = [140.0, 30.0, 40.0, 40.0, 0.9]


def _frames(n=12, moving_face_until=7, busy_frame_from=7, seed=3):
    rng = np.random.default_rng(seed)
    base = cv2.GaussianBlur(rng.uniform(0, 255, (H, W, 3)).astype(np.float32), (0, 0), 1.2).astype(np.uint8)
    face = cv2.GaussianBlur(rng.uniform(0, 255, (60, 60, 3)).astype(np.float32), (0, 0), 1.0).astype(np.uint8)
    out = []
    for i in range(n):
        f = base.copy()
        dx = (i * 3) % 9 if i < moving_face_until else 0          # the face turns until frame 6, then holds
        f[30:70, 140:180] = face[10 + dx:50 + dx, 10:50]
        if i >= busy_frame_from:                                  # the background flickers later (smoke, fire)
            glow = cv2.GaussianBlur(rng.uniform(-60, 60, (H - 120, W)).astype(np.float32), (0, 0), 8)[..., None]
            f[120:, :] = np.clip(f[120:, :].astype(np.float32) + glow * 4, 0, 255).astype(np.uint8)
        out.append(f)
    return out


def test_the_still_face_wins_over_a_still_background():
    frames = _frames()
    rows = FP.score(frames, [FACE] * len(frames))
    best = max(rows, key=lambda r: r["score"])["i"]
    assert best >= 7                                              # the face has settled (it holds from frame 6)
    frame_only = max(FP.score(frames), key=lambda r: r["score"])["i"]
    assert frame_only < 7                                         # by the frame alone the mid-turn face would have won


def test_the_face_of_the_window_beats_a_one_frame_false_hit():
    faces = [[FACE] for _ in range(10)]
    faces[4] = [FACE, [10.0, 120.0, 30.0, 30.0, 0.95]]           # a knot in the wood, one frame
    faces[6] = []                                                 # the real face missed once
    tr = FP.face_track(faces)
    assert all(t is not None and abs(t[0] - FACE[0]) < 1 for t in tr) and tr[6][4] == 0.0


def test_no_face_falls_back_to_the_frame_and_asks_the_reviewer(tmp_path):
    clip = tmp_path / "c.mp4"
    vw = cv2.VideoWriter(str(clip), cv2.VideoWriter_fourcc(*"mp4v"), 24, (W, H))
    for f in _frames(n=30, moving_face_until=30, busy_frame_from=99):
        vw.write(f)
    vw.release()
    rep = FP.pick(clip, window_s=0.5, model=None)
    assert rep["status"] == G.REVIEW and rep["person"].startswith("NOT_RUN") and rep["window"][1] == 29
    assert rep["window"][0] == 18 and rep["window"][0] <= rep["frame"] <= 29
    assert FP.pick(clip, window_s=0.5, after=40, model=None)["frame"] is None    # nothing after the line: no frame


def test_the_weights_come_from_the_rule():
    assert FP.W_FACE > FP.W_BODY > FP.W_FRAME and abs(FP.W_FACE + FP.W_BODY + FP.W_FRAME - 1.0) < 1e-9
