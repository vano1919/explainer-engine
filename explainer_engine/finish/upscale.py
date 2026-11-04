# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/finish/upscale.py`
# Target Module : explainer_engine/finish/upscale.py
# Target Classes/Symbols : def video_filter(), def probe_size(), def upscale()
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

"""WP-5b: an LTX clip (1920x1088, the sizes the video model takes: width and height divisible by 64, edit/clay_video.py)
becomes a delivery-frame clip (BP-167, 2560x1440 at 24 fps): the 4 px strips the model's size adds are cropped off the top
and bottom to a true 16:9 frame, then a Lanczos scale. ffmpeg only, free, deterministic. A latent upscaler on the pod is a
different, paid step and is not this one. Shorts are not made here: ``production/shorts.py`` owns them (BP-167, 1440x2560)."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

from explainer_engine.core import delivery
from explainer_engine.core.errors import ConfigError

CRF = 17  # the same crf as production/shorts.FINAL_VIDEO: the clip is re-encoded once more in assembly


def video_filter(src_w: int, src_h: int, size: tuple[int, int] | None = None) -> str:
    """The -vf chain: crop to the delivery aspect (centred, never stretch), then Lanczos to the delivery size at its fps."""
    w, h = size or delivery.size()
    if src_w <= 0 or src_h <= 0:
        raise ConfigError(f"source size {src_w}x{src_h} is not a picture")
    if src_w * h >= src_h * w:  # wider than the delivery aspect (or equal): trim the sides
        crop_w, crop_h = round(src_h * w / h) // 2 * 2, src_h
    else:  # taller (the model's 1088): trim the top and bottom
        crop_w, crop_h = src_w, round(src_w * h / w) // 2 * 2
    if crop_w < src_w * 0.9 or crop_h < src_h * 0.9:
        raise ConfigError(f"{src_w}x{src_h} is not close to {w}:{h}: cropping would cut more than 10 %, re-render the clip")
    return f"crop={crop_w}:{crop_h}:(in_w-out_w)/2:(in_h-out_h)/2,scale={w}:{h}:flags=lanczos,fps={delivery.fps()}"


def probe_size(path: Path | str) -> tuple[int, int]:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0:s=x", str(path)], capture_output=True, text=True)
    if out.returncode != 0 or "x" not in out.stdout:
        raise ConfigError(f"ffprobe could not read {path}: {out.stderr.strip()[:200]}")
    w, h = out.stdout.strip().split("x")[:2]
    return int(w), int(h)


def upscale(src: Path | str, dst: Path | str, size: tuple[int, int] | None = None) -> Path:
    """``src`` to ``dst`` at the delivery frame. The sound track is dropped (a native-audio LTX clip keeps its own through the
    sound stems); a temp file is renamed so a half-written clip never lies under the final name."""
    w, h = probe_size(src)
    dst = Path(dst)
    part = dst.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(src), "-vf", video_filter(w, h, size), "-an", "-c:v", "libx264",
           "-crf", str(CRF), "-preset", "medium", "-pix_fmt", "yuv420p", str(part)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        part.unlink(missing_ok=True)
        raise ConfigError(f"upscale failed: {done.stderr.strip()[:300]}")
    os.replace(part, dst)
    return dst
