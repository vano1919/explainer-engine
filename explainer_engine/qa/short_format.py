# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/qa/short_format.py`
# Target Module : explainer_engine/qa/short_format.py
# Target Classes/Symbols : def probe(), def check(), def main()
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

"""Is a rendered file a YouTube Short? (creator 2026-10-19: "the Shorts uploaded as videos, fix the code so it never happens")

YouTube makes an upload a Short from the file alone: square or vertical and at most three minutes (YouTube Help 15424877,
read 2026-10-19); the API has no Shorts flag. Our Shorts are 9:16 at any height (BP-167: 1440x2560; 1080x1920 older ones stay valid), so a horizontal or other-ratio file is a render fault. A Short is
reached at ``youtube.com/shorts/<id>``; a ``youtu.be`` link opens even a Short in the ordinary player, which is how the
2026-10-19 uploads looked like videos although YouTube served all ten as Shorts.

    python -m explainer_engine.qa.short_format <SH01.mp4> [...]    # exit 1 on a FAIL
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

MAX_SECONDS = 180.0
ASPECT = (9, 16)
SHORTS_LINK = "https://www.youtube.com/shorts/{id}"


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream=width,height:stream_side_data=rotation:format=duration", "-of", "json", str(path)],
                         capture_output=True, text=True, check=True).stdout
    d = json.loads(out)
    s = (d.get("streams") or [{}])[0]
    rot = next((abs(int(x.get("rotation", 0))) for x in s.get("side_data_list") or [] if "rotation" in x), 0)
    w, h = int(s.get("width", 0)), int(s.get("height", 0))
    if rot in (90, 270):
        w, h = h, w
    return {"width": w, "height": h, "seconds": float(d.get("format", {}).get("duration", 0))}


def check(info: dict) -> list[dict]:
    """FAILs for a file YouTube would not treat as a Short, or that is not our 9:16 frame."""
    out = []
    w, h, sec = info["width"], info["height"], info["seconds"]
    if not (w and h) or w > h:
        out.append({"rule": "SF-01", "severity": "FAIL", "detail": f"{w}x{h} is horizontal: YouTube makes it a video"})
    elif w * ASPECT[1] != h * ASPECT[0]:
        out.append({"rule": "SF-02", "severity": "FAIL", "detail": f"{w}x{h} is not 9:16 (the Short frame is 9:16, 1440x2560 at the delivery size)"})
    if not 0 < sec <= MAX_SECONDS:
        out.append({"rule": "SF-03", "severity": "FAIL", "detail": f"{sec:.1f} s: a Short is at most {MAX_SECONDS:g} s"})
    return out


def main(argv: list[str] | None = None) -> int:
    bad = 0
    for p in argv if argv is not None else sys.argv[1:]:
        info = probe(Path(p))
        found = check(info)
        bad += bool(found)
        print(f"{'FAIL' if found else 'PASS'} {p}: {info['width']}x{info['height']}, {info['seconds']:.1f} s"
              + "".join(f"\n  {f['rule']} {f['detail']}" for f in found))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
