"""P8 identity and sync QA (BP-133, CRAFT-ANI-15/16): fake embedder, synthetic envelope, REVIEW only, no weights."""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import envelope as ENV
from explainer_engine.qa import identity as ID
from explainer_engine.standards import sourced_rules as SR


def fake_embedder(paths):
    """Deterministic stand-in for CLIP: an 8x8 colour thumbnail, centred (no torch, no weights)."""
    out = []
    for p in paths:
        with Image.open(p) as im:
            v = np.asarray(im.convert("RGB").resize((8, 8)), dtype=float).ravel()
        out.append(v - v.mean())
    return np.array(out)


def _hero(path, seed, noise=0, size=64):
    rng = np.random.default_rng(seed)
    base = rng.integers(0, 255, (8, 8, 3)).astype(float)
    img = np.kron(base, np.ones((size // 8, size // 8, 1)))
    if noise:
        img = img + np.random.default_rng(seed + 1000).normal(0, noise, img.shape)
    Image.fromarray(np.clip(img, 0, 255).astype("uint8")).save(path)
    return path


def test_identical_frame_has_cosine_one_and_another_hero_scores_lower(tmp_path):
    a1 = _hero(tmp_path / "a1.png", 1)
    a2 = _hero(tmp_path / "a2.png", 1, noise=12)
    b1 = _hero(tmp_path / "b1.png", 2)
    same = ID.hero_identity([a1], [a1], fake_embedder)
    assert same["mean"] == pytest.approx(1.0, abs=1e-6)
    own = ID.hero_identity([a2], [a1], fake_embedder)["mean"]
    other = ID.hero_identity([b1], [a1], fake_embedder)["mean"]
    assert own > other and own < 1.0


def test_identity_without_a_calibrated_threshold_is_a_passing_review_row_never_a_guess():
    scores = {"per_frame": [0.4], "mean": 0.4, "min": 0.4}
    row = ID.identity_check("s01", scores)
    assert row["severity"] == "REVIEW" and row["passed"] and "uncalibrated" in row["threshold"]
    low = ID.identity_check("s01", scores, threshold=0.7)
    assert low["severity"] == "REVIEW" and not low["passed"]  # a hypothesis rule never FAILs (BP-133)


def test_the_default_embedder_says_so_when_clip_is_missing(tmp_path):
    p = _hero(tmp_path / "a.png", 1)
    try:
        import open_clip  # noqa: F401
        pytest.skip("open_clip is installed here")
    except ImportError:
        from explainer_engine.core.errors import ConfigError
        with pytest.raises(ConfigError):
            ID.hero_identity([p], [p])


def test_style_check_reads_style_score_read_only():
    refs = [np.array([1.0, 0.0]), np.array([0.9, 0.1])]
    good = ID.style_check("s01", np.array([1.0, 0.05]), refs, control_embedding=np.array([1.0, 0.0]))
    bad = ID.style_check("s01", np.array([0.0, 1.0]), refs, control_embedding=np.array([1.0, 0.0]))
    assert good["passed"] and not bad["passed"] and bad["severity"] == "REVIEW" and bad["rule"] == "AC-14"
    assert ID.style_check("s01", np.array([1.0, 0.0]), refs)["severity"] == "INFO"


def _speech_envelope(seconds=20, seed=3):
    rng = np.random.default_rng(seed)
    n = int(seconds / ENV.STEP)
    env, k = np.zeros(n), 0
    while k < n:  # words: bursts of 2-5 steps, then a gap
        w = int(rng.integers(2, 6))
        env[k:k + w] = rng.uniform(0.2, 1.0)
        k += w + int(rng.integers(1, 5))
    return env.tolist()


def _mouth_from(env, delay_s, fps=24):
    t = np.arange(0, len(env) * ENV.STEP - 1.0, 1 / fps)
    return np.interp(t - delay_s, np.arange(len(env)) * ENV.STEP, env, left=0.0).tolist()


def test_an_envelope_delayed_120_ms_is_measured_within_one_frame_and_is_review():
    env = _speech_envelope()
    off = ID.lipsync_offset(_mouth_from(env, 0.120), 24, env)
    assert abs(off["offset_ms"] - 120) <= 1000 / 24 and off["confidence"] > 0.5
    row = ID.lipsync_check("s01", off)
    assert row["severity"] == "REVIEW" and not row["passed"] and row["threshold"] == SR.T("BP-133", "lipsync_max_ms")


def test_an_aligned_mouth_passes_and_a_lead_is_negative():
    env = _speech_envelope()
    aligned = ID.lipsync_offset(_mouth_from(env, 0.0), 24, env)
    assert abs(aligned["offset_ms"]) <= 1000 / 24 and ID.lipsync_check("s01", aligned)["passed"]
    early = ID.lipsync_offset(_mouth_from(env, -0.120), 24, env)
    assert early["offset_ms"] < -80


def test_mouth_openness_follows_the_dark_inside_of_the_box_and_the_box_follows_the_face():
    shut, wide = np.full((40, 40), 240, np.uint8), np.full((40, 40), 240, np.uint8)
    wide[18:22, 16:24] = 10
    box = ID.mouth_box({"x": 0.5, "y": 0.4, "w": 0.4, "h": 0.4})
    o = ID.mouth_openness([shut, wide], box)
    assert o[1] > o[0] + 0.05
    assert box[0] < 0.5 < box[2] and box[1] > 0.4
