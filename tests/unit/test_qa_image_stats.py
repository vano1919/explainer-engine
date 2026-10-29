import numpy as np
from PIL import Image

from explainer_engine.training.qa import image_stats as s


def _save(tmp_path, name, arr):
    p = tmp_path / name
    Image.fromarray(arr.astype(np.uint8)).save(p)
    return p


def test_noise_raises_laplacian_and_busy_share(tmp_path):
    rng = np.random.default_rng(0)
    flat = np.full((128, 128, 3), 120.0)
    noisy = np.clip(flat + rng.normal(0, 40, flat.shape), 0, 255)
    a, b = s.stats(_save(tmp_path, "flat.png", flat)), s.stats(_save(tmp_path, "noisy.png", noisy))
    assert b["lap_var"] > 50 * max(a["lap_var"], 1.0)
    assert a["busy"] == 0.0 and b["busy"] == 1.0


def test_saturated_picture_scores_higher_than_grey(tmp_path):
    grey = np.full((64, 64, 3), 128.0)
    vivid = np.zeros((64, 64, 3))
    vivid[..., 0], vivid[..., 2] = 255, 20
    a, b = s.stats(_save(tmp_path, "g.png", grey)), s.stats(_save(tmp_path, "v.png", vivid))
    assert b["colourful"] > a["colourful"] + 50 and b["sat_p95"] > 0.9 > a["sat_p95"] and b["clip"] == 1.0


def test_ratio_against_reference(tmp_path):
    a = {"lap_var": 4.0, "busy": 0.5}
    assert s.ratio(a, {"lap_var": 2.0, "busy": 0.5}) == {"lap_var": 2.0, "busy": 1.0}
