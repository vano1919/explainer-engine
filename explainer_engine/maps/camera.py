# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/maps/camera.py`
# Target Module : explainer_engine/maps/camera.py
# Target Classes/Symbols : def tier_of(), class State (methods: ), class Move (methods: ), def from_spec(), def state_at(), def tilt(), def zdepth()
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

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


# TODO [CLAUDE-CLASS-SYNC: State] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `State` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
@dataclass(frozen=True)
class State:
    lon: float
    lat: float
    span_km: float
    pitch_deg: float = 0.0


# TODO [CLAUDE-CLASS-SYNC: Move] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `Move` (methods: dataclass fields) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
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
