"""The demo's sounds from the library (W1, 2026-11-12; OV-56 as changed): every overlay motion plays a real library take through
the ``episode/sound_plan`` class its gesture names, and every place plays its own bed. The procedural numpy sounds (sines, band
noise, the one "wind" under a cave, a river and a map alike) are gone: the realism audit of 2026-11-12 heard them as "a
senseless hiss" with action sounds 12 LU under it (BP-192, BP-193).

``render_class(cls, frames, rng)`` returns a library take (mono float32 at ``SR``), a different take per call where the class
has several (BP-57); a gesture that lasts as long as the motion (a line drawn, a bar grown, a swell) is fitted to it. A class
without a real take raises (``needs`` lists it for the priced list); nothing is synthesised.

``beds(places, seconds, rng)`` lays one bed per place (``BED_OF_PLACE``), crossfaded at place changes (``FADE_S``).
"""
from __future__ import annotations

from pathlib import Path

import numpy as np

from explainer_engine.audio import sfx_library
from explainer_engine.core.errors import ContractError
from explainer_engine.episode import sound_plan as SP

SR = 48000
FPS = 24
ROOT = Path(__file__).resolve().parents[2] / "assets" / "audio" / "library"
ERA = "prehistoric_pleistocene"          # the demo is the Toba episode's material
FADE_S = 0.65                            # the beds' crossfade at a place change (sound_plan.BED_FADE_S)

# the overlay's gesture -> the sound_plan class whose library takes play it (OV-52: one organic family)
LIBRARY_CLASS = {"pop_in": "ov_pop", "glow_ping": "ov_glow", "pencil_scribble": "ov_draw", "tick": "ov_tick", "tock": "ov_tick",
                 "landing_thud": "ov_thud", "slide_grow": "ov_slide", "air_swell": "ov_air", "swish": "ov_swish"}
FOLLOWS_MOTION = {"pencil_scribble", "slide_grow", "air_swell"}     # as long as the motion; the others play their take
CLASSES = list(LIBRARY_CLASS)
# what each place of the demo sounds like (what its picture shows): the couple's cliff at sunset, the gorge with its cave
# (smoke, people walking), the dry riverbed; a map keeps the low rumble of the eruption it is about (Q2: the map's own bed under
# its action sounds, never one noise for all)
BED_OF_PLACE = {"photo_C1": ["wind", "birds"], "photo_M1": ["wind", "birds"], "photo_M3": ["river", "wind"],
                "ltx_clip": ["river", "wind"], "map": ["eruption_rumble"]}
EXTRA_TAGS = {"eruption_rumble": ["rumble"]}         # the free take is tagged rumble, not eruption: matched by its own tag


def _resample(x: np.ndarray, rate: int) -> np.ndarray:
    if rate == SR:
        return x.astype(np.float32)
    n = int(round(len(x) * SR / rate))
    return np.interp(np.linspace(0, len(x) - 1, n), np.arange(len(x)), x).astype(np.float32)


def takes(sp_class: str, root: Path = ROOT, era: str = ERA) -> list[dict]:
    """The real (non-procedural) library takes of a sound_plan class, era filter applied."""
    tags = EXTRA_TAGS.get(sp_class) or SP.EVENT_CLASSES[sp_class]["tags"]
    foreign = SP.ERA_FOREIGN_TAGS.get(era, set())
    found = [i for i in sfx_library.find(Path(root), tags=tags) if not foreign & SP._words_of(i)]
    return [i for i in found if SP._origin(i) != "procedural" and (Path(root) / i["file"]).is_file()]


def _load(item: dict, root: Path) -> np.ndarray:
    x, rate = sfx_library.read_wav((Path(root) / item["file"]).read_bytes())
    return _resample(x, rate)


def _fit(x: np.ndarray, n: int) -> np.ndarray:
    """``x`` fitted to ``n`` samples: trimmed with a 40 ms fade, or repeated with 40 ms crossfades."""
    k = int(0.04 * SR)
    out = x.copy()
    while len(out) < n:
        r = np.linspace(0, 1, k, dtype=np.float32)
        out = np.concatenate([out[:-k], out[-k:] * r[::-1] + x[:k] * r, x[k:]])
    out = out[:n].copy()
    f = min(len(out), k)
    out[-f:] *= np.linspace(1, 0, f, dtype=np.float32)
    return out


def render_class(cls: str, frames: int, rng, root: Path = ROOT, era: str = ERA) -> np.ndarray:
    if cls not in LIBRARY_CLASS:
        raise KeyError(cls)
    pool = takes(LIBRARY_CLASS[cls], root, era)
    if not pool:
        raise ContractError(f"{cls}: no real library take of {LIBRARY_CLASS[cls]} (tags {SP.EVENT_CLASSES[LIBRARY_CLASS[cls]]['tags']}); "
                            "a procedural sound never plays (OV-56)")
    pick = sorted(pool, key=lambda i: i["id"])[int(rng.integers(len(pool)))]
    x = _load(pick, root)
    if cls in FOLLOWS_MOTION:
        x = _fit(x, max(int(frames / FPS * SR), int(0.15 * SR)))
    return (x / (np.max(np.abs(x)) + 1e-9)).astype(np.float32)


def needs(classes, root: Path = ROOT, era: str = ERA) -> list[str]:
    """The gestures and bed classes without a real take (the shopping list)."""
    out = [c for c in classes if c in LIBRARY_CLASS and not takes(LIBRARY_CLASS[c], root, era)]
    beds = {b for v in BED_OF_PLACE.values() for b in v}
    return out + sorted(b for b in beds if not takes(b, root, era))


def _loop(x: np.ndarray, n: int, offset: int) -> np.ndarray:
    k = int(0.25 * SR)
    reps = []
    total = 0
    while total < n + offset + k:
        reps.append(x)
        total += len(x) - k
    out = reps[0].copy()
    r = np.linspace(0, 1, k, dtype=np.float32)
    for y in reps[1:]:
        out = np.concatenate([out[:-k], out[-k:] * r[::-1] + y[:k] * r, y[k:]])
    return out[offset:offset + n]


def beds(places: list[dict], seconds: float, rng, root: Path = ROOT, era: str = ERA) -> np.ndarray:
    """One bed per place run (consecutive shots of one place share it), every class of the place at -3 dB per extra layer,
    crossfaded over ``FADE_S`` at a place change; each run starts its loops at a new offset, so a place met again is not the
    same seconds again."""
    n = int(seconds * SR)
    out = np.zeros(n, np.float32)
    f = int(FADE_S * SR)
    runs: list[dict] = []
    for p in places:
        if runs and runs[-1]["place"] == p["place"]:
            runs[-1]["end_s"] = p["end_s"]
        else:
            runs.append(dict(p))
    for k, run in enumerate(runs):
        i0 = max(0, int(run["start_s"] * SR) - (f // 2 if k else 0))
        i1 = min(n, int(run["end_s"] * SR) + (f // 2 if k + 1 < len(runs) else 0))
        m = i1 - i0
        layer = np.zeros(m, np.float32)
        for j, cls in enumerate(BED_OF_PLACE[run["place"]]):
            pool = takes(cls, root, era)
            if not pool:
                raise ContractError(f"{run['place']}: no real take for its bed class {cls}")
            x = _load(sorted(pool, key=lambda i: i["id"])[int(rng.integers(len(pool)))], root)
            y = _loop(x, m, int(rng.integers(0, max(1, len(x) // 2))))
            y = y / (np.sqrt(np.mean(y ** 2)) + 1e-9) * 0.05 * 10 ** ((-3.0 * j) / 20)   # -26 dBFS: never clipped by a 16-bit stem
            layer += y.astype(np.float32)
        ramp = np.ones(m, np.float32)
        if k:
            ramp[:f] = np.sin(np.linspace(0, np.pi / 2, f)) if m > f else 1
        if k + 1 < len(runs):
            ramp[-f:] = np.cos(np.linspace(0, np.pi / 2, f)) if m > f else 1
        out[i0:i1] += layer * ramp
    return out


def place(buf: np.ndarray, x: np.ndarray, t_s: float, gain: float) -> None:
    i = int(round(t_s * SR))
    if i >= len(buf):
        return
    m = min(len(x), len(buf) - i)
    buf[i:i + m] += gain * x[:m]
