
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
# float32 copies: a 2560x1440 frame in float64 is 88 MB per array and the colour transfer makes several; float32 halves that and is
# far finer than one 8-bit level. The statistics are taken on a ~STATS_ROWS-row grid of the frame (they are means and spreads).
_M32, _WHITE32, _MINV32 = _M.astype(np.float32), _WHITE.astype(np.float32), np.linalg.inv(_M).astype(np.float32)
STATS_ROWS = 180


def rgb_to_lab(img: np.ndarray) -> np.ndarray:
    x = np.clip(np.asarray(img, dtype=np.float32), 0.0, 1.0)
    lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
    t = (lin @ _M32.T) / _WHITE32
    f = np.where(t > _EPS, np.cbrt(t), (_KAPPA * t + 16.0) / 116.0)
    return np.stack([116.0 * f[..., 1] - 16.0, 500.0 * (f[..., 0] - f[..., 1]), 200.0 * (f[..., 1] - f[..., 2])], axis=-1)


def lab_to_rgb(lab: np.ndarray) -> np.ndarray:
    fy = (lab[..., 0] + 16.0) / 116.0
    f = np.stack([fy + lab[..., 1] / 500.0, fy, fy - lab[..., 2] / 200.0], axis=-1)
    t = np.where(f ** 3 > _EPS, f ** 3, (116.0 * f - 16.0) / _KAPPA)
    lin = (t * _WHITE32) @ _MINV32.T
    lin = np.clip(lin, 0.0, 1.0)
    return np.clip(np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055), 0.0, 1.0)


def lab_stats(img: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Per-channel (mean, std) of an RGB image in LAB: the two statistics BP-130 compares."""
    img = np.asarray(img)
    step = max(1, img.shape[0] // STATS_ROWS) if img.ndim == 3 else 1   # statistics on a ~STATS_ROWS-row grid, not on every pixel
    lab = rgb_to_lab(img[::step, ::step]).reshape(-1, 3)
    return lab.mean(axis=0, dtype=np.float64), lab.std(axis=0, dtype=np.float64)


def lab_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Mean-colour distance (Euclidean in LAB) between two images' LAB means."""
    return float(np.linalg.norm(lab_stats(a)[0] - lab_stats(b)[0]))


def blend_cap(blend: float) -> tuple[float, bool]:
    """``(applied, capped)``: the blend limited to BP-130's ``blend_max`` (and to >= 0); ``capped`` is the REVIEW case."""
    top = float(SR.T("BP-130", "blend_max"))
    return max(0.0, min(float(blend), top)), float(blend) > top


# The scale (key std / frame std) is bounded: a near-flat boundary frame (night sky, black frame) would give a scale in the thousands
# and blow its noise up over the whole shot. BP-130 has no such number (its thresholds are blend_max and the statistics), so these two
# are module constants and a REVIEW house choice (not sourced); `scale_clipped` in the params is the REVIEW finding the caller reports.
SCALE_MIN, SCALE_MAX = 0.25, 4.0


def transfer_params(frame: np.ndarray, key_frame: np.ndarray) -> dict:
    """The per-channel scale and shift that move ``frame``'s LAB mean/std onto the key's (one set can serve a whole shot); the scale
    is clipped to ``SCALE_MIN``..``SCALE_MAX`` and ``scale_clipped`` says so (REVIEW)."""
    (m, s), (km, ks) = lab_stats(frame), lab_stats(key_frame)
    raw = np.where(s > 1e-6, ks / np.maximum(s, 1e-6), 1.0)
    scale = np.clip(raw, SCALE_MIN, SCALE_MAX)
    return {"mean": m, "scale": scale, "key_mean": km, "scale_clipped": bool(np.any(scale != raw))}


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


# --- grade ONCE on the master (final plan S15, W7; method of scenario-video-color-grade: Lab Reinhard, 33^3 LUT, applied once) ---
# A per-pixel colour function bakes into a 33^3 .cube LUT that ffmpeg applies in one pass over the master. The transfer is the
# Reinhard one above, capped at BP-130's blend_max. A record next to the output names the input hash, the LUT hash and the key, and a
# file that already carries such a record (an input that is itself a graded master) is refused: the grade is applied once.
import hashlib as _hashlib
import json as _json
from pathlib import Path as _Path

LUT_SIZE = 33
GRADE_RECORD = "grade_record/1"


def build_lut(params: dict, blend: float, size: int = LUT_SIZE) -> np.ndarray:
    """``size``^3 x 3 RGB lattice (red varies fastest, the .cube order) the transfer maps every grid colour to."""
    g = np.linspace(0.0, 1.0, size)
    b, gg, r = np.meshgrid(g, g, g, indexing="ij")     # axis order b, g, r: the last index (red) runs fastest on flattening
    grid = np.stack([r, gg, b], axis=-1).reshape(-1, 3)
    return np.clip(apply_transfer(grid.reshape(-1, 1, 3), params, blend).reshape(-1, 3), 0.0, 1.0)


def write_cube(path, lattice: np.ndarray, title: str = "scene key grade", size: int = LUT_SIZE) -> str:
    """The .cube text; returns its sha256 (the grade record's LUT hash)."""
    if lattice.shape != (size ** 3, 3):
        raise ValueError(f"a {size}^3 LUT has {size ** 3} rows, got {lattice.shape}")
    text = f'TITLE "{title}"\nLUT_3D_SIZE {size}\nDOMAIN_MIN 0 0 0\nDOMAIN_MAX 1 1 1\n' + "".join(
        f"{r:.6f} {g:.6f} {b:.6f}\n" for r, g, b in lattice)
    p = _Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="ascii")
    return _hashlib.sha256(text.encode("ascii")).hexdigest()


def read_cube(path) -> tuple[int, np.ndarray]:
    size, rows = 0, []
    for ln in _Path(path).read_text(encoding="ascii").splitlines():
        if ln.startswith("LUT_3D_SIZE"):
            size = int(ln.split()[1])
        elif ln and (ln[0].isdigit() or ln[0] == "-"):
            rows.append([float(x) for x in ln.split()])
    return size, np.asarray(rows)


def lut_apply(lattice: np.ndarray, rgb: np.ndarray, size: int = LUT_SIZE) -> np.ndarray:
    """Trilinear lookup (what ffmpeg's lut3d does) of float RGB ``[0,1]`` pixels, shape (..., 3): the check that the baked LUT
    does what the transfer does."""
    cube = lattice.reshape(size, size, size, 3)          # [b][g][r]
    x = np.clip(np.asarray(rgb, dtype=np.float64), 0.0, 1.0) * (size - 1)
    i0 = np.minimum(np.floor(x).astype(int), size - 2)
    f = x - i0
    out = 0.0
    for db in (0, 1):
        for dg in (0, 1):
            for dr in (0, 1):
                w = (f[..., 2] if db else 1 - f[..., 2]) * (f[..., 1] if dg else 1 - f[..., 1]) * (f[..., 0] if dr else 1 - f[..., 0])
                out = out + w[..., None] * cube[i0[..., 2] + db, i0[..., 1] + dg, i0[..., 0] + dr]
    return out


def delta_e_to_key(frame: np.ndarray, key_frame: np.ndarray) -> float:
    """CIE76 distance between the Lab means of a frame (or a set of sampled frames stacked) and the scene key frame."""
    return lab_distance(frame, key_frame)


def _sha(path) -> str:
    h = _hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def record_path(video) -> _Path:
    p = _Path(video)
    return p.with_name(p.stem + ".grade.json")


def graded(video) -> bool:
    """True when ``video`` is the output of ``grade_master`` (its record exists and names this very file)."""
    rec = record_path(video)
    if not rec.exists():
        return False
    try:
        return _json.loads(rec.read_text(encoding="utf-8")).get("output_sha256") == _sha(video)
    except (ValueError, OSError):
        return False


def grade_master(master, out, key_frame: np.ndarray, sample_frames: np.ndarray, *, blend: float | None = None,
                 lut_dir=None) -> dict:
    """Grade the master ONCE toward the scene key: the Reinhard parameters from ``sample_frames`` (the master's own frames, RGB 0-1,
    stacked on axis 0 or one image) against ``key_frame``, baked into a 33^3 LUT, applied through ffmpeg-skill ``color --lut``.
    Writes ``<out stem>.grade.json`` (``grade_record/1``). Raises ``ContractError`` when ``master`` is already a graded output."""
    from explainer_engine.core.errors import ContractError
    from explainer_engine.core.store import write_json_atomic
    from explainer_engine.finish import ffwrap
    master, out = _Path(master), _Path(out)
    if graded(master):
        raise ContractError(f"{master} already carries a grade record: the grade is applied once, on the master (S15)")
    top = float(SR.T("BP-130", "blend_max"))
    b, capped = blend_cap(top if blend is None else blend)
    frames = np.asarray(sample_frames, dtype=np.float32)
    params = transfer_params(frames.reshape(-1, frames.shape[-2], 3) if frames.ndim == 4 else frames, key_frame)
    lut_path = _Path(lut_dir or out.parent) / (out.stem + ".cube")
    lut_sha = write_cube(lut_path, build_lut(params, b))
    ffwrap.run("color", [master, "--lut", lut_path, "-o", out, "--overwrite"])
    rec = {"schema": GRADE_RECORD, "input_sha256": _sha(master), "output_sha256": _sha(out), "lut": lut_path.name,
           "lut_sha256": lut_sha, "lut_size": LUT_SIZE, "blend": b, "blend_capped": capped, "scale_clipped": params["scale_clipped"],
           "key_mean_lab": [float(x) for x in params["key_mean"]], "method": "lab_reinhard_33_lut_once"}
    write_json_atomic(record_path(out), rec)
    return rec
