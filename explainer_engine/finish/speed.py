# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/finish/speed.py`
# Target Module : explainer_engine/finish/speed.py
# Target Classes/Symbols : def _filter(), def retime(), def excerpts(), def main()
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

"""Speed as a finishing step (ED-06): the finished video is time-compressed (picture and sound together, pitch kept), the
voice is never re-synthesised. ``excerpts`` makes short samples of the BP-02 rates of the same places for the creator to
compare; ``retime`` makes the full file at the chosen rate, never above BP-02's ceiling (the tempo just-noticeable
difference; docs/SOURCED_RULES.md). The sped file is the delivered file (ED-06), so its sound is BP-63's delivery codec.
ffmpeg only, no cost."""
from __future__ import annotations

import subprocess
from pathlib import Path

from explainer_engine.production.assemble import AUDIO_CODEC  # BP-63: stereo AAC at the delivery bitrate and rate
from explainer_engine.standards import sourced_rules as SR

RATES = tuple(SR.T("BP-02", "rates"))  # BP-02: the rates offered to the creator
MAX_RATE = SR.T("BP-02", "max_tempo")  # BP-02: the creator's ceiling, under the tempo JND


def _filter(rate: float) -> str:
    return f"[0:v]setpts=PTS/{rate},fps=30[v];[0:a]atempo={rate}[a]"


def retime(src: Path, dst: Path, rate: float, *, start: float | None = None, length: float | None = None,
           crf: int = 18, scale: str | None = None) -> Path:
    if not 1.0 < rate <= MAX_RATE:
        raise ValueError(f"rate must be above 1.0 and at most {MAX_RATE} (BP-02: a speed-up stays under the tempo "
                         "just-noticeable difference; the rhythm and pace checks run again on the sped file)")
    cut = (["-ss", f"{start}"] if start is not None else []) + (["-t", f"{length}"] if length is not None else [])
    graph = _filter(rate) if not scale else f"[0:v]scale={scale},setpts=PTS/{rate},fps=30[v];[0:a]atempo={rate}[a]"
    part = dst.with_suffix(".part.mp4")
    subprocess.run(["ffmpeg", "-v", "error", "-y", *cut, "-i", str(src), "-filter_complex", graph, "-map", "[v]", "-map", "[a]",
                    "-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p", *AUDIO_CODEC,
                    str(part)], check=True)
    part.replace(dst)
    return dst


def excerpts(src: Path, out_dir: Path, places: list[tuple[float, float]], rates=RATES, scale: str = "1280:720") -> list[Path]:
    """One 720p sample per place and rate; ``places`` are (start s, length s) on the original clock."""
    out_dir.mkdir(parents=True, exist_ok=True)
    made = []
    for k, (a, n) in enumerate(places, 1):
        for r in rates:
            made.append(retime(src, out_dir / f"p{k}_x{r:.2f}.mp4", r, start=a, length=n, crf=23, scale=scale))
    return made


def main(argv: list[str] | None = None) -> int:
    import argparse
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("video")
    p.add_argument("--out", required=True, help="a folder for --places, the output file for --final")
    p.add_argument("--places", help="start:length pairs in seconds, e.g. 240:45,780:45")
    p.add_argument("--final", type=float, help="make the full file at this rate")
    a = p.parse_args(argv)
    if a.final:
        print(retime(Path(a.video), Path(a.out), a.final))
    else:
        pairs = [tuple(float(x) for x in t.split(":")) for t in a.places.split(",")]
        for f in excerpts(Path(a.video), Path(a.out), pairs):
            print(f)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
