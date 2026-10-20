"""The finishing grade (D-41, UR-26): one era grade, grain and black level over every picture. numpy only.

``grade(img, params, seed)`` takes float RGB ``[0,1]`` of shape (H, W, 3). ``params`` come from ``world/eras.json`` "grades".
Applied to pod pictures, Gemini pictures and composited sprites alike, so mixed sources share one finish.
"""

from __future__ import annotations

import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722])


def grade(img: np.ndarray, params: dict, seed: int = 0) -> np.ndarray:
    x = np.clip(np.asarray(img, dtype=np.float64), 0.0, 1.0)
    luma = (x @ LUMA)[..., None]
    x = luma + (x - luma) * params["saturation"]
    x = 0.5 + (x - 0.5) * params["contrast"]
    shadow = np.clip(1.0 - luma / 0.5, 0.0, 1.0)
    high = np.clip((luma - 0.5) / 0.5, 0.0, 1.0)
    x = x + shadow * np.array(params["shadow_tint"]) + high * np.array(params["high_tint"])
    x = params["black"] + x * (1.0 - params["black"])
    rng = np.random.default_rng(seed)
    x = x + rng.normal(0.0, params["grain"], size=x.shape[:2])[..., None]
    return np.clip(x, 0.0, 1.0)


def mean_luma(img: np.ndarray) -> float:
    return float((np.asarray(img, dtype=np.float64) @ LUMA).mean())
