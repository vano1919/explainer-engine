"""The finishing grade (D-41, UR-26): one era grade, grain and black level over every picture. numpy only.

``grade(img, params, seed)`` takes float RGB ``[0,1]`` of shape (H, W, 3). ``params`` come from ``world/eras.json`` "grades".
Applied to pod pictures, Gemini pictures and composited sprites alike, so mixed sources share one finish.
"""

from __future__ import annotations

import numpy as np

from explainer_engine.standards import sourced_rules as SR

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


# --- shot-to-shot colour (P7, BP-130): Reinhard mean/std transfer in CIE LAB toward the scene's key master frame ----------------
# The LOOK above (era grade + grain) stays the last step of the pipeline (ED-04); this runs before it, on the raw shot.

_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])
_EPS, _KAPPA = 216.0 / 24389.0, 24389.0 / 27.0


def rgb_to_lab(img: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(img, dtype=np.float64), 0.0, 1.0)
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    t = (lin @ _M.T) / _WHITE
    f = np.where(t > _EPS, np.cbrt(t), (_KAPPA * t + 16.0) / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    fy = (lab[..., 0] + 16.0) / 116.0
    f = np.stack([fy + lab[..., 1] / 500.0, fy, fy - lab[..., 2] / 200.0], axis=-1)
    t = np.where(f ** 3 > _EPS, f ** 3, (116.0 * f - 16.0) / _KAPPA)
    lin = (t * _WHITE) @ np.linalg.inv(_M).T
    lin = np.clip(lin, 0.0, 1.0)
    return np.clip(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055), 0.0, 1.0)


def lab_stats(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel (mean, std) of an RGB image in LAB: the two statistics BP-130 compares."""
    lab = rgb_to_lab(img).reshape(-1, 3)
    return lab.mean(axis=0), lab.std(axis=0)


def lab_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Mean-colour distance (Euclidean in LAB) between two images' LAB means."""
    return float(np.linalg.norm(lab_stats(a)[0] - lab_stats(b)[0]))


def blend_cap(blend: float) -> tuple[float, bool]:
    """``(applied, capped)``: the blend limited to BP-130's ``blend_max`` (and to >= 0); ``capped`` is the REVIEW case."""
    top = float(SR.T("BP-130", "blend_max"))
    return max(0.0, min(float(blend), top)), float(blend) > top


def transfer_params(frame: np.ndarray, key_frame: np.ndarray) -> dict:
    """The per-channel scale and shift that move ``frame``'s LAB mean/std onto the key's (one set can serve a whole shot)."""
    (m, s), (km, ks) = lab_stats(frame), lab_stats(key_frame)
    scale = np.where(s > 1e-6, ks / np.maximum(s, 1e-6), 1.0)
    return {"mean": m, "scale": scale, "key_mean": km}


def apply_transfer(frame: np.ndarray, params: dict, blend: float) -> np.ndarray:
    """``frame`` corrected toward the key by ``blend`` (capped at ``blend_max``); 0 returns the frame as it was."""
    b, _ = blend_cap(blend)
    if b == 0.0:
        return np.clip(np.asarray(frame, dtype=np.float64), 0.0, 1.0)
    lab = rgb_to_lab(frame)
    moved = (lab - params["mean"]) * params["scale"] + params["key_mean"]
    return lab_to_rgb(lab + b * (moved - lab))


def transfer_to_key(frame: np.ndarray, key_frame: np.ndarray, blend: float) -> np.ndarray:
    """Reinhard colour transfer: ``frame`` toward ``key_frame`` by mean and std per LAB channel, blend <= BP-130 ``blend_max``."""
    return apply_transfer(frame, transfer_params(frame, key_frame), blend)
