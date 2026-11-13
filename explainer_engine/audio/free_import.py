"""Free, licence-checked sounds into the library (the creator's order 2026-11-12 22:15 UTC: our library first, then free sources
with a checked licence, then ElevenLabs from a priced list).

A pick list (``assets/audio/free_picks_<date>.json``, schema ``free_sound_picks/1``) names, for every take, the page it came
from, its author, the file inside the downloaded page folder and the licence read on that page. ``run`` decodes each file with
FFmpeg to 48 kHz mono and stores it through ``sfx_library.add``:

* a ``loop`` (a bed) is cut from ``start_s`` and closed with an equal-power crossfade, so the wrap is the source continuing
  into itself (BP-58: at least ``loop_min_s``; a shorter source is first tiled with crossfades);
* a ``one_shot`` is trimmed to where it sounds (``TRIM_BELOW_PEAK_DB`` under its peak) with a short fade-out;
* an ``arranged`` take is built only from the stored real takes (no generated noise): ``march`` places every soldier's steps
  on its own pace, phase and distance, wrapped round the loop length so the loop has no seam at all.

Nobody listens here: ``review.human`` stays ``not_listened`` and ``review.machine`` says what was measured.

CLI: ``python -m explainer_engine.audio.free_import <picks.json> <raw folder> [--root assets/audio/library] [--only name,...]``
"""
from __future__ import annotations

import argparse
import glob
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

from explainer_engine.audio import sfx_library as L
from explainer_engine.standards import sourced_rules as SR

RATE = 48000
XFADE_S = 2.0               # the loop's closing crossfade
TRIM_BELOW_PEAK_DB = 50.0   # a one-shot starts and ends where it rises this far under its peak
FADE_OUT_S = 0.012
PICKS_SCHEMA = "free_sound_picks/1"


def decode(path: Path, rate: int = RATE) -> np.ndarray:
    """Any audio file -> mono float32 at ``rate`` (FFmpeg)."""
    r = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate), "-f", "f32le", "-"],
                       capture_output=True, check=True)
    x = np.frombuffer(r.stdout, dtype=np.float32).copy()
    if not len(x):
        raise ValueError(f"{path}: no audio")
    return x


def _ramps(n: int) -> tuple[np.ndarray, np.ndarray]:
    t = (np.arange(n) + 0.5) / n
    return np.sin(np.pi / 2 * t).astype(np.float32), np.cos(np.pi / 2 * t).astype(np.float32)


def tile(x: np.ndarray, seconds: float, rate: int = RATE, xfade_s: float = XFADE_S) -> np.ndarray:
    """Repeat ``x`` with equal-power crossfades until it is at least ``seconds`` long."""
    k = int(xfade_s * rate)
    out = x.copy()
    while len(out) < seconds * rate:
        fin, fout = _ramps(k)
        out = np.concatenate([out[:-k], out[-k:] * fout + x[:k] * fin, x[k:]])
    return out


def make_loop(x: np.ndarray, seconds: float, start_s: float = 0.0, rate: int = RATE, xfade_s: float = XFADE_S,
              min_s: float | None = None) -> np.ndarray:
    """A seamless loop of ``seconds`` (or what the source allows, never under ``min_s``): its first ``xfade_s`` hold the
    source's continuation faded in over its own start, so the wrap is the source running on."""
    min_s = SR.T("BP-58", "loop_min_s") if min_s is None else min_s
    k = int(xfade_s * rate)
    a = int(start_s * rate)
    if len(x) - a < int(max(seconds, min_s) * rate) + k + int(3.5 * rate):
        a = 0
        if len(x) < int(max(seconds, min_s) * rate) + k + int(3.5 * rate):
            x = tile(x, max(seconds, min_s) + xfade_s + 3.5, rate, xfade_s)
    n0 = min(int(seconds * rate), len(x) - a - k)
    fin, fout = _ramps(k)

    def build(a: int, n: int) -> np.ndarray:
        seg = x[a:a + n + k]
        out = seg[:n].copy()
        out[:k] = seg[:k] * fin + seg[n:n + k] * fout
        return out

    # the wrap is the source running on, but the source itself swells: choose the cut (start within 2 s, length within
    # 1.5 s) where the level is steady across the wrap and no transient sits next to it (BP-58)
    clear = SR.T("BP-58", "seam_clear_s")
    best, best_cost = None, None
    step = int(0.1 * rate)
    for da in range(0, int(2.0 * rate) + 1, step):
        for dn in range(-int(1.5 * rate), int(1.5 * rate) + 1, step):
            aa, nn = a + da, n0 + dn
            if nn < int(min_s * rate) or aa + nn + k > len(x):
                continue
            out = build(aa, nn)
            cost = L.seam_step_db(out, rate) + (10.0 if L.transient_near_seam(out, rate, clear) else 0.0)
            if best_cost is None or cost < best_cost:
                best, best_cost = out, cost
    return best if best is not None else build(a, n0)


def trim_one_shot(x: np.ndarray, rate: int = RATE, below_db: float = TRIM_BELOW_PEAK_DB) -> np.ndarray:
    """Cut a one-shot to where it sounds, with 5 ms before its onset and a short fade-out."""
    peak = float(np.max(np.abs(x)))
    on = np.flatnonzero(np.abs(x) > peak * 10 ** (-below_db / 20))
    a = max(0, int(on[0]) - int(0.005 * rate))
    b = min(len(x), int(on[-1]) + int(0.02 * rate))
    y = x[a:b].copy()
    f = min(len(y), int(FADE_OUT_S * rate))
    y[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return y


def _place_wrapped(buf: np.ndarray, x: np.ndarray, at: int, gain: float) -> None:
    n = len(buf)
    at %= n
    m = min(len(x), n)
    first = min(m, n - at)
    buf[at:at + first] += gain * x[:first]
    if first < m:
        buf[:m - first] += gain * x[first:m]


def arrange_march(steps: list[np.ndarray], clinks: list[np.ndarray], *, seconds: float, seed: int, soldiers: int,
                  steps_per_s: tuple[float, float], clinks_per_s: float, rate: int = RATE) -> np.ndarray:
    """A marching column from real step and armour takes: every soldier keeps his own pace and phase at a distance of 8-80 m
    (level 1/d, the air's high-frequency loss as a low-pass per distance band); armour clinks fall at random through the
    column. Every event wraps round the loop's length, so the loop has no seam."""
    rng = np.random.default_rng(seed)
    n = int(seconds * rate)
    bands = [(8, 15, 9000), (15, 30, 6000), (30, 50, 3800), (50, 80, 2400)]
    out = np.zeros(n, np.float32)
    for lo, hi, fc in bands:
        buf = np.zeros(n, np.float32)
        share = soldiers // len(bands)
        for _ in range(share):
            d = rng.uniform(lo, hi)
            pace = rng.uniform(*steps_per_s)
            period = int(rate / pace)
            t = int(rng.uniform(0, period))
            # a whole number of steps per loop keeps each soldier's step on the same beat at the wrap
            count = max(1, round(n / period))
            period = n // count
            for j in range(count):
                take = steps[rng.integers(len(steps))]
                jitter = int(rng.normal(0, 0.012) * rate)
                g = (8.0 / d) * 10 ** (rng.normal(0, 2.0) / 20)
                _place_wrapped(buf, take, t + j * period + jitter, g)
        for _ in range(int(clinks_per_s * seconds / len(bands))):
            take = clinks[rng.integers(len(clinks))]
            d = rng.uniform(lo, hi)
            _place_wrapped(buf, take, int(rng.uniform(0, n)), 0.5 * (8.0 / d) * 10 ** (rng.normal(0, 3.0) / 20))
        out += sosfilt(butter(2, fc, fs=rate, output="sos"), np.concatenate([buf, buf]))[n:].astype(np.float32)
    return rotate_to_quiet_seam(out, rate)


def rotate_to_quiet_seam(x: np.ndarray, rate: int = RATE) -> np.ndarray:
    """A circular loop can start anywhere: start it where the level is steadiest across the wrap and no transient is near."""
    clear = SR.T("BP-58", "seam_clear_s")
    best, best_cost = x, None
    for r in range(0, len(x), int(0.05 * rate)):
        y = np.roll(x, -r)
        cost = L.seam_step_db(y, rate) + (10.0 if L.transient_near_seam(y, rate, clear) else 0.0)
        if best_cost is None or cost < best_cost:
            best, best_cost = y, cost
    return best


def _source(pick: dict, raw_name: str, read: str) -> dict:
    return {"kind": "third_party", "prompt": f"OpenGameArt '{pick['page'].rsplit('/', 1)[-1]}' by {pick['author']}: {raw_name}",
            "generated": read, "cost_usd_estimate": 0}


def _licence(pick: dict, read: str) -> dict:
    return {"status": "cc0", "note": f"CC0 1.0 per {pick['page']} (licence field read {read}; author {pick['author']}); "
                                     "no attribution required, credited in the description as a courtesy"}


def expand(pick: dict, raw: Path) -> list[tuple[int, Path]]:
    """(take number, file) of one pick: one file, or a glob whose matches become takes 1..n in name order."""
    if pick.get("takes") == "glob":
        files = sorted(Path(p) for p in glob.glob(str(raw / pick["raw"])))
        if not files:
            raise FileNotFoundError(f"{pick['name']}: nothing matches {pick['raw']}")
        return list(enumerate(files, 1))
    return [(int(pick["take"]), raw / pick["raw"])]


def run(picks_path: Path, raw: Path, root: Path, only: set[str] | None = None) -> list[dict]:
    data = json.loads(Path(picks_path).read_text(encoding="utf-8"))
    if data.get("schema") != PICKS_SCHEMA:
        raise ValueError(f"{picks_path}: not a {PICKS_SCHEMA} pick list")
    read = data["read"]
    stored: dict[str, list[np.ndarray]] = {}
    out = []
    for pick in data["picks"]:
        for take, path in expand(pick, Path(raw)):
            x = decode(path)
            if pick["kind"] == "loop":
                y = make_loop(x, float(pick["seconds"]), float(pick.get("start_s", 0.0)))
                note = f"loop cut at {pick.get('start_s', 0.0)} s, closed with a {XFADE_S:g} s equal-power crossfade"
            else:
                y = trim_one_shot(x)
                note = f"one-shot trimmed at -{TRIM_BELOW_PEAK_DB:g} dB under its peak"
                lo, hi = SR.T("BP-58", "one_shot_s")
                if not lo <= len(y) / RATE <= hi:
                    print(f"skip {pick['name']} take {take} ({path.name}): {len(y) / RATE:.2f} s is outside BP-58's one-shot range")
                    continue
            stored.setdefault(pick["name"], []).append(y)
            if only and pick["name"] not in only:
                continue
            e = L.add(root, name=pick["name"], take=take, category=pick["category"], tags=pick["tags"], samples=y, rate=RATE,
                      source=_source(pick, path.name, read), licence=_licence(pick, read),
                      machine_review=f"measured only (free_import): {note}; nobody has listened", loop=pick["kind"] == "loop")
            out.append(e)
    for arr in data.get("arranged", []):
        if only and arr["name"] not in only:
            continue
        steps = [s for k in arr["from"] for s in stored[k]]
        clinks = [s for k in arr["clinks_from"] for s in stored[k]]
        y = arrange_march(steps, clinks, seconds=arr["seconds"], seed=arr["seed"], soldiers=arr["soldiers"],
                          steps_per_s=tuple(arr["steps_per_s"]), clinks_per_s=arr["clinks_per_s"])
        pages = sorted({p["page"] for p in data["picks"] if p["name"] in set(arr["from"]) | set(arr["clinks_from"])})
        src = {"kind": "third_party", "prompt": f"arranged by free_import.arrange_march from the CC0 takes "
                                                f"{', '.join(arr['from'] + arr['clinks_from'])}: {arr['note']}",
               "seed": int(arr["seed"]), "generated": read, "cost_usd_estimate": 0}
        lic = {"status": "cc0", "note": f"arranged from CC0 1.0 takes ({'; '.join(pages)}, licence fields read {read})"}
        out.append(L.add(root, name=arr["name"], take=int(arr["take"]), category=arr["category"], tags=arr["tags"], samples=y,
                         rate=RATE, source=src, licence=lic, loop=True,
                         machine_review="measured only (free_import): wrapped placement, no seam; nobody has listened"))
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("picks")
    ap.add_argument("raw")
    ap.add_argument("--root", default="assets/audio/library")
    ap.add_argument("--only", default="")
    a = ap.parse_args(argv)
    only = {s for s in a.only.split(",") if s} or None
    entries = run(Path(a.picks), Path(a.raw), Path(a.root), only)
    for e in entries:
        print(f"{e['id']:32} {e['seconds']:7.2f} s  rms {e['rms_dbfs']:6.1f}  {'loop' if e.get('loop') else 'one_shot'}")
    findings = [f for f in L.lint(Path(a.root)) if f["where"] in {e["id"] for e in entries}]
    for f in findings:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
