"""The demo's audio (free, procedural, OV-50..OV-56): narration lines (Kokoro scratch), a continuous wind + fire bed, one sound event per
overlay motion, and the LTX clip's own audio, level-matched. Levels are measured with ffmpeg ebur128; the report is what the validator reads.
"""
from __future__ import annotations

import re
import subprocess
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from explainer_engine.overlay import demo_sound as S

SR, FPS = S.SR, S.FPS
LEAD_S = 0.6
AMB_LUFS = -34.0          # the scene's real sounds (wind + fire)
NARR_LUFS = -20.0
SFX_UNDER_LU = 6.5        # overlay sounds this far below the scene's real sounds (OV-53 asks at least 6 LU)
GROUPS = {"10 %": [2, 4, 7, 10, 12], "30 %": [1, 3, 5, 6, 9, 11], "LTX": [8]}


def lufs(x: np.ndarray, sr: int = SR) -> dict:
    """Integrated loudness, the loudest momentary (400 ms) and the median momentary of a mono array (ffmpeg ebur128)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x.wav"
        sf.write(p, x.astype(np.float32), sr)
        r = subprocess.run(["ffmpeg", "-nostats", "-i", str(p), "-af", "ebur128=peak=true", "-f", "null", "-"], capture_output=True, text=True)
    integ = re.findall(r"I:\s+(-?[\d.]+|-inf) LUFS", r.stderr)
    mom = [float(v) for v in re.findall(r"\sM:\s*(-?[\d.]+)", r.stderr)]
    mom = [m for m in mom if m > -90]
    return {"integrated": float(integ[-1]) if integ and integ[-1] != "-inf" else -99.0, "momentary_max": max(mom) if mom else -99.0,
            "momentary_median": float(np.median(mom)) if mom else -99.0}


def gain_for(x: np.ndarray, target_lufs: float) -> float:
    return 10 ** ((target_lufs - lufs(x)["integrated"]) / 20.0)


def starts(shots: list[dict]) -> dict[int, float]:
    t, out = 0.0, {}
    for s in shots:
        out[s["no"]] = t
        t += s["dur"]
    return out


def load_narration(narr: list[dict]) -> dict[int, np.ndarray]:
    out = {}
    for l in narr:
        a, sr = sf.read(l["wav"], dtype="float32")
        out[l["no"]] = resample_poly(a, SR // 1000, sr // 1000).astype(np.float32)
    return out


def clip_audio(clip: Path, seconds: float) -> np.ndarray:
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "c.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-t", str(seconds), "-vn", "-ac", "1", "-ar", str(SR), str(p)], check=True)
        a, _ = sf.read(p, dtype="float32")
    return a.astype(np.float32)


def build(shots: list[dict], specs: list[dict], narr: list[dict], clip: Path | None, out_dir: Path, seed: int = 7) -> dict:
    """Render the stems (narr, amb, sfx, clip) over the whole video, level them, write them and return the level report + event list."""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = sum(s["dur"] for s in shots)
    n = int(total * SR)
    st = starts(shots)
    rng = np.random.default_rng(seed)
    wind, fire = S.ambience(total, rng, [(0.0, float(total))])
    amb = wind + 0.45 * fire
    amb *= gain_for(amb, AMB_LUFS)
    # narration
    narr_stem = np.zeros(n, np.float32)
    lines = load_narration(narr)
    for no, a in lines.items():
        S.place(narr_stem, a, st[no] + LEAD_S, 1.0)
    narr_stem *= gain_for(narr_stem, NARR_LUFS)
    # overlay sounds: one event per entry of every spec's sound list (BP-57 variants through the seeded jitter)
    sfx = np.zeros(n, np.float32)
    events = []
    for sp in specs:
        base = st[sp["shot_no"]]
        for k, ev in enumerate(sp["sound"]):
            r = np.random.default_rng(seed * 1000 + sp["shot_no"] * 100 + k)
            x = S.render_class(ev["cls"], ev["dur"], r)
            gj = 10 ** ((r.random() - 0.5) * 3.0 / 20)         # BP-57: a gain jitter of +-1.5 dB
            S.place(sfx, x, base + ev["t"] / FPS, ev.get("gain", 1.0) * gj)
            events.append({**ev, "shot_no": sp["shot_no"], "abs_t": round(base + ev["t"] / FPS, 3), "dur_s": round(len(x) / SR, 3)})
    amb_l = lufs(amb)
    probe = lufs(sfx)
    sfx *= 10 ** ((amb_l["momentary_median"] - SFX_UNDER_LU - probe["momentary_max"]) / 20.0)
    # the LTX clip's own audio, matched to the level of the other groups' non-narration sound (OV-55)
    clip_stem = np.zeros(n, np.float32)
    if clip is not None:
        ca = clip_audio(clip, shots[[s["no"] for s in shots].index(8)]["dur"])
        a0 = int(st[8] * SR)
        clip_stem[a0:a0 + len(ca)] = ca[:n - a0]
        ref = _group_level(amb, sfx, clip_stem, st, shots, ["10 %", "30 %"])
        lo, hi = -60.0, 0.0                                   # bisect the clip's gain (dB) until the LTX group sits at the other groups' level
        for _ in range(10):
            mid = (lo + hi) / 2
            lv = _group_level(amb, sfx, clip_stem * 10 ** (mid / 20), st, shots, ["LTX"])
            lo, hi = (mid, hi) if lv < ref else (lo, mid)
        clip_stem *= 10 ** (((lo + hi) / 2) / 20)
    stems = {"narr": narr_stem, "amb": amb, "sfx": sfx, "clip": clip_stem}
    for k, v in stems.items():
        sf.write(out_dir / f"stem_{k}.wav", v, SR)
    rep = {"groups": {}, "ambience": amb_l, "sfx": lufs(sfx), "narration": lufs(narr_stem), "sfx_under_scene_lu": round(amb_l["momentary_median"] - lufs(sfx)["momentary_max"], 2),
           "events": events}
    for g, nos in GROUPS.items():
        rep["groups"][g] = round(_group_level(amb, sfx, clip_stem, st, shots, [g]), 2)
    rep["ambience_min_100ms_dbfs"] = ambience_floor(amb)
    return {"stems": stems, "report": rep, "starts": st}


def _segments(x: np.ndarray, st: dict, shots: list[dict], groups: list[str]) -> np.ndarray:
    dur = {s["no"]: s["dur"] for s in shots}
    parts = []
    for g in groups:
        for no in GROUPS[g]:
            parts.append(x[int(st[no] * SR):int((st[no] + dur[no]) * SR)])
    return np.concatenate(parts)


def _group_level(amb, sfx, clip, st, shots, groups) -> float:
    """Integrated loudness of the non-narration sound (bed + overlay sounds + clip) over the shots of the groups."""
    x = _segments(amb + sfx + clip, st, shots, groups)
    return lufs(x)["integrated"]


def ambience_floor(amb: np.ndarray) -> float:
    w = SR // 10
    k = len(amb) // w
    r = np.sqrt((amb[:k * w].reshape(k, w) ** 2).mean(axis=1) + 1e-12)
    return round(float(20 * np.log10(r.min())), 1)


def mix_range(stems: dict, t0: float, t1: float, sfx_db: float = 0.0, with_clip: bool = True) -> np.ndarray:
    a, b = int(t0 * SR), int(t1 * SR)
    m = stems["narr"][a:b] + stems["amb"][a:b] + stems["sfx"][a:b] * 10 ** (sfx_db / 20) + (stems["clip"][a:b] if with_clip else 0)
    peak = float(np.max(np.abs(m)) + 1e-9)
    return (m * min(1.0, 0.95 / peak)).astype(np.float32)
