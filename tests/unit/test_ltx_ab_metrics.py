"""The free A/B metrics of CT-2 (training/pods/ltx/ab_metrics.py), tested on synthetic clips: LAB conversion, flicker mean/p95,
sharpness ratio, PSNR, the LAB colour lock, the CT-1 continuation check, NOT_RUN without an embedder or LPIPS, ffmpeg decode of a
real file, and the blind labels."""
from __future__ import annotations

import json
import shutil
import subprocess

import numpy as np
import pytest
from PIL import Image

from explainer_engine.training.pods.ltx import ab_metrics as M
from explainer_engine.videolane import plan as P


def _img(color, size=(64, 48), noise=0.0, seed=0):
    a = np.full((size[1], size[0], 3), color, dtype=np.float64)
    if noise:
        a += np.random.default_rng(seed).normal(0, noise, a.shape)
    return np.clip(a, 0, 255).astype(np.uint8)


def test_lab_round_trip_and_known_values():
    rgb = np.array([[[255, 255, 255], [0, 0, 0], [255, 0, 0], [128, 64, 200]]], dtype=np.uint8)
    lab = M.rgb_to_lab(rgb)
    assert abs(lab[0, 0, 0] - 100) < 0.1 and abs(lab[0, 1, 0]) < 0.1 and abs(lab[0, 2, 0] - 53.24) < 0.3
    assert np.abs(M.lab_to_rgb(lab).astype(int) - rgb.astype(int)).max() <= 1


def test_a_still_clip_does_not_flicker_and_a_flashing_one_does():
    still = np.stack([_img((90, 100, 110))] * 12)
    assert M.flicker(still) == {"mean": 0.0, "p95": 0.0, "pairs": 11}
    flash = np.stack([_img((90, 100, 110)) if k % 2 == 0 else _img((140, 100, 110)) for k in range(12)])
    f = M.flicker(flash)
    assert f["mean"] > 5 and f["p95"] >= f["mean"] and f["pairs"] == 11
    assert M.flicker(still[:1])["mean"] is None


def test_sharpness_ratio_compares_the_last_frame_with_the_master():
    master = _img((120, 120, 120), noise=20, seed=1)
    blurred = np.asarray(Image.fromarray(master).resize((16, 12)).resize((64, 48), Image.BILINEAR))
    assert M.sharpness_ratio(master, master) == 1.0 and M.sharpness_ratio(blurred, master) < 0.5
    assert M.sharpness_ratio(np.asarray(Image.fromarray(master).resize((32, 24))), master) >= 0   # fitted to the master's size


def test_psnr_and_lab_delta_e_of_equal_and_shifted_pictures():
    a = _img((100, 100, 100), noise=5, seed=2)
    assert M.psnr_db(a, a) == float("inf") and M.lab_delta_e(a, a) == 0.0
    b = np.clip(a.astype(int) + 20, 0, 255).astype(np.uint8)
    assert 20 < M.psnr_db(b, a) < 30 and M.lab_delta_e(a, b) > 5


def test_the_lab_lock_moves_a_drifted_frame_toward_the_master():
    master = _img((110, 100, 90), noise=15, seed=3)
    drift = np.clip(master.astype(int) + np.array([30, -10, -25]), 0, 255).astype(np.uint8)
    locked = M.lab_lock(drift, master)
    assert M.lab_delta_e(master, locked) < 0.4 * M.lab_delta_e(master, drift)
    half = M.lab_lock(drift, master, strength=0.5)
    assert M.lab_delta_e(master, locked) < M.lab_delta_e(master, half) < M.lab_delta_e(master, drift)
    assert locked.dtype == np.uint8 and locked.shape == drift.shape


def test_identity_is_not_run_without_an_embedder_and_measured_with_one(monkeypatch):
    from explainer_engine.core.errors import ConfigError
    from explainer_engine.qa import identity as ID

    def none(paths, cache=None):
        raise ConfigError("no torch")
    monkeypatch.setattr(ID, "clip_embedder", none)
    a = _img((10, 20, 30))
    r = M.identity_cosine(a, a)
    assert r["state"] == "NOT_RUN" and "no torch" in r["why"]
    r = M.identity_cosine(a, a, embedder=lambda paths: np.array([[1.0, 0.0], [0.6, 0.8]]))
    assert r == {"state": "MEASURED", "cosine": 0.6}


def test_the_continuation_check_feeds_ct1_and_a_missing_embedding_is_refused_not_invented(monkeypatch):
    master = _img((110, 100, 90), noise=15, seed=3)
    frame = M.lab_lock(np.clip(master.astype(int) + 12, 0, 255).astype(np.uint8), master)
    chk = M.continuation_check(frame, master, "S07_SH004_start", embedder=lambda p: np.array([[1.0, 0.0], [0.99, 0.1]]),
                               upscaled_x2=True, lab_locked=True)
    assert set(P.CT1_CHECK_KEYS) <= set(chk) and chk["master"] == "S07_SH004_start"
    assert P.ct1_check_problems(chk, 1) == []
    from explainer_engine.core.errors import ConfigError
    from explainer_engine.qa import identity as ID
    monkeypatch.setattr(ID, "clip_embedder", lambda paths, cache=None: (_ for _ in ()).throw(ConfigError("no torch")))
    nofc = M.continuation_check(frame, master, "m", upscaled_x2=True, lab_locked=True)
    assert nofc["face_cosine"] is None and nofc["identity_state"] == "NOT_RUN"
    assert any("face_cosine" in w for w in P.ct1_check_problems(nofc, 1))


@pytest.mark.skipif(not shutil.which("ffmpeg"), reason="ffmpeg is not installed")
def test_a_synthetic_clip_is_decoded_and_scored_against_its_master(tmp_path, monkeypatch):
    from explainer_engine.core.errors import ConfigError
    from explainer_engine.qa import identity as ID
    monkeypatch.setattr(ID, "clip_embedder", lambda paths, cache=None: (_ for _ in ()).throw(ConfigError("no torch")))
    clip = tmp_path / "c.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=size=320x176:rate=24:duration=1", "-pix_fmt", "yuv420p",
                    str(clip)], check=True)
    frames = M.read_frames(clip, width=160)
    assert frames.shape[0] == 24 and frames.shape[3] == 3 and frames.shape[2] == 160
    master = tmp_path / "m.png"
    Image.fromarray(frames[-1]).resize((320, 176)).save(master)
    s = M.score_clip(clip, master)
    assert s["frames"] == 24 and s["flicker"]["pairs"] == 23 and s["psnr_db"] > 20
    assert s["identity"]["state"] == "NOT_RUN" and s["lpips"]["state"] == "NOT_RUN"
    s2 = M.score_clip(clip, master, lpips_fn=lambda a, b: 0.12, embedder=lambda p: np.array([[1.0, 0.0], [1.0, 0.0]]))
    assert s2["lpips"] == {"state": "MEASURED", "value": 0.12} and s2["identity"]["cosine"] == 1.0
    assert json.loads(json.dumps(s2, default=float))["frames"] == 24


def test_the_blind_labels_hide_the_arms_and_are_reproducible():
    items = {sh: {arm: f"/c/{sh}_{arm}.mp4" for arm in "abcd"} for sh in ("S07_SH008", "S04_SH008", "S07_SH006")}
    one, two = M.blind_labels(items, seed=5), M.blind_labels(items, seed=5)
    assert one == two and M.blind_labels(items, seed=6)["key"] != one["key"]
    for sh, labels in one["sheet"].items():
        assert sorted(labels) == ["A", "B", "C", "D"]
        for lab, path in labels.items():
            assert path == items[sh][one["key"][sh][lab]]
    assert len(one["key_sha256"]) == 64
