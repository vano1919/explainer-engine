"""Colour validators (final plan S15, W2): shot-boundary frames against the scene's master frame (BP-130, BP-212) and the hero's costume
and skin swatches across the episode (BP-212). Images are uint8 arrays ``H x W x 3`` (RGB); colour maths is plain numpy sRGB -> CIE Lab
(D65)."""
from __future__ import annotations

import numpy as np

from explainer_engine.qa import gates as G
from explainer_engine.validators import _common as C

RULE_IDS = ("CRAFT-EDC-09", "CRAFT-EDC-10")
_M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
_WHITE = np.array([0.95047, 1.0, 1.08883])


def rgb_to_lab(rgb) -> np.ndarray:
    """sRGB (0-255, any leading shape ending in 3) -> CIE Lab."""
    c = np.asarray(rgb, dtype=np.float64) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    xyz = (lin @ _M.T) / _WHITE
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], axis=-1)


def delta_e(rgb_a, rgb_b) -> float:
    """CIE76 distance of two sRGB colours."""
    return float(np.linalg.norm(rgb_to_lab(rgb_a) - rgb_to_lab(rgb_b)))


def boundary_vs_master(frame, master, gate: str = "CRAFT-EDC-09") -> dict:
    """CRAFT-EDC-09: the per-channel Lab mean and spread of a shot's boundary frame against the scene master. The Reinhard correction
    is limited to BP-130's blend_max, so what is left after it, (1 - blend_max) times the gap, must stay inside BP-212's
    boundary_residual_delta_max (mean) and std_ratio_residual_max (spread)."""
    blend, res_max, std_max = C.T("BP-130", "blend_max"), C.T("BP-212", "boundary_residual_delta_max"), C.T("BP-212", "std_ratio_residual_max")
    if None in (blend, res_max, std_max):
        return C.missing_threshold(gate, "BP-130/BP-212", "blend_max, boundary_residual_delta_max, std_ratio_residual_max")
    f, m = rgb_to_lab(np.asarray(frame)).reshape(-1, 3), rgb_to_lab(np.asarray(master)).reshape(-1, 3)
    mean_gap = float(np.linalg.norm(f.mean(0) - m.mean(0)))
    std_gap = float(np.max(np.abs(f.std(0) / np.maximum(m.std(0), 1e-6) - 1.0)))
    left_mean, left_std = (1 - blend) * mean_gap, (1 - blend) * std_gap
    ok = left_mean <= res_max and left_std <= std_max
    return C.check(gate, ok, "BP-130", f"mean gap {mean_gap:.1f} Lab, spread gap {std_gap:.2f}; after a blend of {blend} "
                   f"{left_mean:.1f} (max {res_max}) and {left_std:.2f} (max {std_max}) are left",
                   {"mean_gap": mean_gap, "std_gap": std_gap})


def hero_swatches(sheet: dict, frames: dict, gate: str = "CRAFT-EDC-10") -> list[dict]:
    """CRAFT-EDC-10: every named swatch (hero costume, skin) sampled in the episode's frames stays inside hero_delta_e_max of the hero
    sheet's. ``sheet`` {name: (r, g, b)}; ``frames`` {name: [(r, g, b), ...]} (one sample per shot)."""
    mx = C.T("BP-212", "hero_delta_e_max")
    if mx is None:
        return [C.missing_threshold(gate, "BP-212", "hero_delta_e_max")]
    rows = []
    for name, ref in sheet.items():
        samples = frames.get(name) or []
        if not samples:
            rows.append(G.row(f"{gate}:{name}", None, "NOT_RUN: no sample of this swatch in the frames"))
            continue
        worst = max(delta_e(ref, s) for s in samples)
        rows.append(C.check(f"{gate}:{name}", worst <= mx, "BP-212", f"worst delta-E {worst:.1f} over {len(samples)} shots; at most {mx}", worst))
    return rows or [G.row(gate, None, "NOT_RUN: the hero sheet lists no swatch")]
