# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/parallax.py`
# Target Module : explainer_engine/production/parallax.py
# Target Classes/Symbols : def amount(), def load(), def direction(), def shift()
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

"""2.5D parallax (D-70 stage F, bible.json motion default "stills + 2.5D parallax"): near parts of a picture slide a little
more than far parts while the shot runs. numpy only.

A shot opts in with ``motion.parallax`` (the near-far shift at the shot's ends, a share of the frame width, at most
MAX_AMP). The depth map is ``<picture>.depth.png`` (``production/depth.py``); a picture without one stays flat and the render
report lists it. ``shift`` is a pure function of the frame (the shot's progress u), so a chunked render draws the same pixels.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image

MAX_AMP = 0.02    # 2 % of the width end to end: a camera drift, never a wobble (schema maximum too)
DEFAULT_AMP = 0.012


def amount(motion: dict) -> float:
    return min(float(motion.get("parallax") or 0.0), MAX_AMP)


def load(picture: Path | None) -> np.ndarray | None:
    """The picture's depth map as float32 0..1 (1 = nearest), or None."""
    if picture is None:
        return None
    p = Path(picture).with_name(Path(picture).stem + ".depth.png")
    if not p.exists():
        return None
    return np.asarray(Image.open(p).convert("L"), dtype=np.float32) / 255.0


def direction(motion: dict) -> float:
    """Near parts move with the camera's side move; a push or a hold drifts left to right."""
    if "x0" in motion:
        d = float(motion["x1"]) - float(motion["x0"])
    else:
        d = float(motion.get("dx", 0.0))
    return -1.0 if d < 0 else 1.0


def shift(frame: Image.Image, depth: np.ndarray, box, src_size: tuple[int, int], u: float, amp: float,
          sign: float = 1.0) -> Image.Image:
    """``frame`` (the crop ``box`` of a picture of ``src_size``, already resized) with its near parts moved by
    amp * width * (2u - 1) * (depth - mean depth). Inverse mapping with clamped edges: no holes, no tears."""
    if amp <= 0:
        return frame
    OW, OH = frame.size
    W, H = src_size
    dh, dw = depth.shape
    sx0, sy0, sx1, sy1 = box[0] * dw / W, box[1] * dh / H, box[2] * dw / W, box[3] * dh / H
    d = np.asarray(Image.fromarray(depth).resize((OW, OH), Image.BILINEAR, box=(sx0, sy0, sx1, sy1)), dtype=np.float32)
    off = sign * amp * OW * (2.0 * u - 1.0) * (d - float(d.mean()))
    if not np.any(np.abs(off) >= 0.5):
        return frame
    xs = np.clip(np.rint(np.arange(OW, dtype=np.float32)[None, :] - off), 0, OW - 1).astype(np.intp)
    src = np.asarray(frame)
    out = src[np.arange(OH)[:, None], xs]
    return Image.fromarray(out)
