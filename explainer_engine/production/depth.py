# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/production/depth.py`
# Target Module : explainer_engine/production/depth.py
# Target Classes/Symbols : def folder(), def available(), def map_path(), def _model(), def estimate(), def ensure(), def main()
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

# from vano1919/tmr-video-script-engine@1c34e27:tmr_engine/render/depth.py
"""Depth maps for the pictures: the 2.5D parallax of D-70 stage F (motion stays stills + parallax by default, bible.json).

Depth-Anything V2 Small (Apache-2.0; onnx-community/depth-anything-v2-small, ~99 MB) runs once per picture on the CPU
(onnxruntime, ~2.5 s) and its map is stored next to the picture (``<picture>.depth.png``, 8-bit, near = white, softened so
no edge tears). ``production/parallax.py`` then moves the near parts of a picture a little more than the far parts as the
shot runs. The map is computed once, so every frame stays a pure function of its number. Without the model
(``tools/depth`` or ``$EXPLAINER_DEPTH_DIR``) the pictures simply stay flat and the render report says so.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path

import numpy as np

logger = logging.getLogger(__name__)

ROOT = Path(__file__).resolve().parents[2]
MODEL_FILE = "depth_anything_v2_small.onnx"
SUFFIX = ".depth.png"
INPUT_SIZE = (924, 518)   # width, height: 518 rows as the model was trained, a multiple of 14, 16:9
MAP_SIZE = (576, 324)     # stored map: smooth enough to be resized to any frame
SOFTEN = 3.0              # Gaussian blur radius of the stored map (px): depth edges become slopes, never tears
MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD = np.array([0.229, 0.224, 0.225], dtype=np.float32)
_session = None


def folder() -> Path:
    return Path(os.environ.get("EXPLAINER_DEPTH_DIR") or ROOT / "tools" / "depth")


def available() -> bool:
    return (folder() / MODEL_FILE).exists()


def map_path(picture: Path) -> Path:
    picture = Path(picture)
    return picture.with_name(picture.stem + SUFFIX)


def _model():
    global _session
    if _session is None:
        import onnxruntime as ort

        _session = ort.InferenceSession(str(folder() / MODEL_FILE), providers=["CPUExecutionProvider"])
    return _session


def estimate(image, session=None):
    """A PIL RGB image -> its depth map (PIL "L", MAP_SIZE, 255 = nearest), normalised per picture."""
    from PIL import Image, ImageFilter

    x = np.asarray(image.convert("RGB").resize(INPUT_SIZE, Image.BICUBIC), dtype=np.float32) / 255.0
    x = ((x - MEAN) / STD).transpose(2, 0, 1)[None].astype(np.float32)
    s = session or _model()
    d = np.asarray(s.run(None, {s.get_inputs()[0].name: x})[0], dtype=np.float32).reshape(-1, *x.shape[2:])[0]
    lo, hi = np.percentile(d, 1.0), np.percentile(d, 99.0)
    d = np.clip((d - lo) / max(hi - lo, 1e-6), 0.0, 1.0)
    out = Image.fromarray((d * 255.0 + 0.5).astype(np.uint8), mode="L").resize(MAP_SIZE, Image.BILINEAR)
    return out.filter(ImageFilter.GaussianBlur(SOFTEN))


def ensure(picture: Path, session=None) -> Path | None:
    """The stored map of a picture, made now if missing; None when no model is installed."""
    from PIL import Image

    out = map_path(picture)
    if out.exists():
        return out
    if session is None and not available():
        return None
    try:
        estimate(Image.open(picture), session).save(out.with_suffix(".tmp.png"), format="PNG")
        os.replace(out.with_suffix(".tmp.png"), out)
    except Exception as exc:  # a broken model or picture: the picture stays flat, the video goes on
        logger.warning("depth map for %s failed: %s", picture, exc)
        return None
    return out


def main(argv: list[str] | None = None) -> int:
    """Depth maps for picture files or folders (free, local CPU). Exit 1 when the model is not installed."""
    import argparse

    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.depth")
    ap.add_argument("paths", nargs="+")
    a = ap.parse_args(argv)
    if not available():
        print(f"no depth model: put {MODEL_FILE} (onnx-community/depth-anything-v2-small, Apache-2.0) in {folder()}")
        return 1
    files = []
    for p in map(Path, a.paths):
        files += sorted(x for x in p.glob("*.png") if not x.name.endswith(SUFFIX)) if p.is_dir() else [p]
    made = [f for f in files if ensure(f)]
    print(f"{len(made)} of {len(files)} pictures have a depth map")
    return 0 if len(made) == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())
