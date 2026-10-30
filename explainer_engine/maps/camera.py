"""The map camera: a start state and moves between words, eased, in log-scale of the view's width (law 5).

A state is a centre (lon, lat), a view width in km and a pitch. A move runs from the first frame of one spoken word to the first
frame of another, so the picture and the voice change together (word lock). ``tier_of`` names the altitude of a width:
macro, meso or micro, by the nearest of the three BP-148 widths on a log scale.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from explainer_engine.maps import draw as D
from explainer_engine.standards import sourced_rules as SR

TIERS = ("macro", "meso", "micro")


def tier_of(span_km: float) -> str:
    """The altitude tier of a view width (BP-148): the nearest of the macro, meso and micro widths on a log scale."""
    widths = {t: SR.T("BP-148", f"{t}_km") for t in TIERS}
    return min(TIERS, key=lambda t: abs(math.log(span_km / widths[t])))


@dataclass(frozen=True)
class State:
    lon: float
    lat: float
    span_km: float
    pitch_deg: float = 0.0


@dataclass(frozen=True)
class Move:
    """One move: from frame ``start`` to frame ``end`` (item-relative) the camera goes to ``to``."""

    start: int
    end: int
    to: State


def from_spec(camera: dict, frame_of) -> tuple[State, list[Move]]:
    """The camera of a payload: ``{"start": {...}, "moves": [{"from_word", "to_word", "lon", "lat", "span_km", "pitch_deg"}]}`` with
    the words turned into item-relative frames by ``frame_of(word_index)``."""
    s = camera["start"]
    start = State(s["lon"], s["lat"], s["span_km"], s.get("pitch_deg", 0.0))
    moves = [Move(frame_of(m["from_word"]), frame_of(m["to_word"]), State(m["lon"], m["lat"], m["span_km"], m.get("pitch_deg", 0.0)))
             for m in camera.get("moves", [])]
    return start, moves


def state_at(start: State, moves: list[Move], frame: float) -> State:
    """The camera at ``frame``: a hold between moves, an eased glide inside one (position linear in lon/lat, width in its log)."""
    cur = start
    for m in moves:
        if frame <= m.start:
            return cur
        if frame < m.end:
            u = D.ease_in_out((frame - m.start) / max(1, m.end - m.start))
            return State(cur.lon + (m.to.lon - cur.lon) * u, cur.lat + (m.to.lat - cur.lat) * u,
                         math.exp(math.log(cur.span_km) + (math.log(m.to.span_km) - math.log(cur.span_km)) * u),
                         cur.pitch_deg + (m.to.pitch_deg - cur.pitch_deg) * u)
        cur = m.to
    return cur


def tilt(im, pitch_deg: float):
    """A map seen at ``pitch_deg`` from straight above: the far (top) edge narrows (a trapezoid warp). ``zdepth`` ramps with the same pitch."""
    from PIL import Image
    if pitch_deg <= 0:
        return im
    w, h = im.size
    squeeze = 0.5 * math.sin(math.radians(pitch_deg))  # share of the width taken off each top corner
    inset = squeeze * w * 0.5
    # PIL maps the output corners (top-left, bottom-left, bottom-right, top-right) to these source points: the output top edge
    # samples a wider band of the source than the bottom edge, so the far edge narrows
    quad = (-inset, 0, 0, h, w, h, w + inset, 0)
    return im.transform((w, h), Image.QUAD, quad, Image.BICUBIC)


def zdepth(width: int, height: int, pitch_deg: float):
    """The depth map the camera exports when it pitches (law 7): near (bottom) white, far (top) dark, a ramp of the pitch."""
    import numpy as np
    from PIL import Image
    far = 1.0 - min(max(pitch_deg, 0.0), 90.0) / 90.0 * 0.8
    col = np.linspace(far, 1.0, height, dtype=np.float32)[:, None]
    return Image.fromarray((np.repeat(col, width, axis=1) * 255 + 0.5).astype(np.uint8), "L")
