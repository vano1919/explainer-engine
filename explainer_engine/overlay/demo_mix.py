"""The demo's audio (free, from the library, OV-50..OV-56 as changed by W1 2026-11-12): narration lines (Kokoro scratch) or one
narration track, a bed per place from real library takes (``demo_sound.beds``), one library take per overlay motion set
``SFX_ABOVE_BED_DB`` over the bed around it (BP-192: heard), and the LTX clip's own audio, level-matched. Levels are measured with
ffmpeg ebur128; the report is what the validator reads.
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
from explainer_engine.standards import sourced_rules as SR_RULES

SR, FPS = S.SR, S.FPS
LEAD_S = 0.6
AMB_LUFS = -36.0          # the places' beds: 16 LU under the narration (BP-52: a bed at least 15 LU under the voice)
NARR_LUFS = -20.0
SFX_ABOVE_BED_DB = float(np.mean(SR_RULES.T("BP-192", "target_above_bed_db")))   # an action's loudest 100 ms over its bed
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


def place_of(shot: dict) -> str:
    """The place a shot's sound belongs to: its picture (a chart's blurred photo too), a map, or the LTX clip."""
    if shot.get("route") == "ltx":
        return "ltx_clip"
    if shot.get("bg") == "map":
        return "map"
    return f"photo_{shot.get('photo', 'C1')}"


def places(shots: list[dict]) -> list[dict]:
    st = starts(shots)
    return [{"start_s": st[s["no"]], "end_s": st[s["no"]] + s["dur"], "place": place_of(s), "shot_no": s["no"]} for s in shots]


def _peak100_db(x: np.ndarray) -> float:
    w = SR // 10
    k = max(1, len(x) // w)
    r = np.sqrt((np.pad(x, (0, max(0, k * w - len(x))))[:k * w].reshape(k, w) ** 2).mean(axis=1) + 1e-12)
    return float(20 * np.log10(r.max()))


def _bed_around_db(amb: np.ndarray, t: float, span_s: float = 1.0) -> float:
    a, b = max(0, int((t - span_s) * SR)), min(len(amb), int((t + span_s) * SR))
    w = SR // 10
    seg = amb[a:b]
    k = max(1, len(seg) // w)
    r = np.sqrt((seg[:k * w].reshape(k, w) ** 2).mean(axis=1) + 1e-12)
    return float(20 * np.log10(np.median(r)))


def build(shots: list[dict], specs: list[dict], narr: list[dict] | None, clip: Path | None, out_dir: Path, seed: int = 7,
          narration_track: np.ndarray | None = None, root: Path = S.ROOT) -> dict:
    """Render the stems (narr, amb, sfx, clip) over the whole video, level them, write them and return the level report + event list.
    ``narration_track`` (mono, SR) replaces the per-line narration when the lines exist only as one read."""
    out_dir.mkdir(parents=True, exist_ok=True)
    total = sum(s["dur"] for s in shots)
    n = int(total * SR)
    st = starts(shots)
    rng = np.random.default_rng(seed)
    amb = S.beds(places(shots), total, rng, root)
    amb *= gain_for(amb, AMB_LUFS)
    # narration
    narr_stem = np.zeros(n, np.float32)
    if narration_track is not None:
        narr_stem[:min(n, len(narration_track))] = narration_track[:n]
    else:
        for no, a in load_narration(narr or []).items():
            S.place(narr_stem, a, st[no] + LEAD_S, 1.0)
    narr_stem *= gain_for(narr_stem, NARR_LUFS)
    # overlay sounds: one library take per entry of every spec's sound list, its loudest 100 ms SFX_ABOVE_BED_DB over the bed
    sfx = np.zeros(n, np.float32)
    events = []
    for sp in specs:
        base = st[sp["shot_no"]]
        for k, ev in enumerate(sp["sound"]):
            r = np.random.default_rng(seed * 1000 + sp["shot_no"] * 100 + k)
            x = S.render_class(ev["cls"], ev["dur"], r, root)
            t = base + ev["t"] / FPS
            gj = (r.random() - 0.5) * 3.0                                  # BP-57: a gain jitter of +-1.5 dB
            g_db = _bed_around_db(amb, t) + SFX_ABOVE_BED_DB + gj - _peak100_db(x) + 20 * np.log10(ev.get("gain", 1.0))
            S.place(sfx, x, t, 10 ** (g_db / 20))
            events.append({**ev, "shot_no": sp["shot_no"], "abs_t": round(t, 3), "dur_s": round(len(x) / SR, 3),
                           "above_bed_db": round(SFX_ABOVE_BED_DB + gj, 2)})
    amb_l = lufs(amb)
    # the LTX clip's own audio, matched to the level of the other groups' non-narration sound (OV-55)
    clip_stem = np.zeros(n, np.float32)
    if clip is not None and 8 in st:
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
    rep = {"groups": {}, "ambience": amb_l, "sfx": lufs(sfx), "narration": lufs(narr_stem),
           "sfx_above_bed_db": round(float(np.median([e["above_bed_db"] for e in events])), 2) if events else None,
           "bed_under_narration_lu": round(lufs(narr_stem)["integrated"] - amb_l["integrated"], 2),
           "sound_source": "library", "places": places(shots), "events": events}
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
    return limit(m, 0.95)


def limit(m: np.ndarray, ceiling: float, hold_s: float = 0.01) -> np.ndarray:
    """A peak limiter: the gain dips only around the samples over ``ceiling`` (10 ms hold, 10 ms ramps), so one loud hit does not
    lower the whole mix (W1: scaling the whole mix by its peak pushed 13 % of the dialogue part under -40 dBFS)."""
    from scipy.ndimage import minimum_filter1d, uniform_filter1d
    a = np.abs(m)
    g = np.minimum(1.0, ceiling / np.maximum(a, 1e-9))
    k = max(1, int(hold_s * SR))
    g = minimum_filter1d(g, 2 * k + 1)
    g = np.minimum(g, uniform_filter1d(g, k))
    return (m * g).astype(np.float32)
