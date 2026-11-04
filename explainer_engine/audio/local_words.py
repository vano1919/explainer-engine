# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/local_words.py`
# Target Module : explainer_engine/audio/local_words.py
# Target Classes/Symbols : def decode(), def _model(), def transcribe(), def transcribe_chunks(), def main()
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

"""Free word times from a local Whisper (faster-whisper on the CPU) instead of ElevenLabs Scribe (~1,000 credits per
3 minutes, 2026-10-16). Writes the same shape Scribe returns (``{"words": [{"text", "start", "end", "type"}]}``), so
``scribe_words.py --transcript`` aligns it to the script unchanged (missed or misheard words are interpolated there and
counted against the 97 % coverage gate).

    python -m explainer_engine.audio.local_words <audio> <out.json> [--model small.en]

faster-whisper is optional (``pip install faster-whisper``); the audio is decoded by ffmpeg (the bundled PyAV may not
open every file). Measured 2026-10-16: small.en int8 hears 25 s of ElevenLabs speech in 6-10 s on this container's CPU.
"""
from __future__ import annotations

import argparse
import functools
import json
import subprocess
import sys
import time
from pathlib import Path


def decode(path: Path, sr: int = 16000):
    import numpy as np

    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(sr), "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, dtype=np.float32)


@functools.lru_cache(maxsize=2)
def _model(model: str):
    from faster_whisper import WhisperModel
    return WhisperModel(model, device="cpu", compute_type="int8")


def transcribe(path: Path, model: str = "small.en", prompt: str | None = None) -> dict:
    t0 = time.time()
    m = _model(model)
    segs, _ = m.transcribe(decode(path), word_timestamps=True, language="en", initial_prompt=prompt)
    words = [{"text": w.word.strip(), "start": round(float(w.start), 3), "end": round(float(w.end), 3), "type": "word"}
             for s in segs for w in s.words if w.word.strip()]
    words = [w for w in words if w["end"] - w["start"] >= 0.03]  # 20 ms "words" at the end are hallucinations
    return {"source": f"faster-whisper {model} (local, free)", "seconds": round(time.time() - t0, 1), "words": words}


def transcribe_chunks(paths: list[Path], offsets: list[float], model: str = "small.en") -> dict:
    """Each chunk read heard on its own, its words moved to where the chunk sits in the joined read. On a 12-minute joined
    read Whisper dropped repeated words ("Rivals sign. Rivals smile.") and a second speaker's echo ("Mostly. Mostly?")
    that it hears in the chunk alone (Syndicate Wars, coverage 96 % -> see PROGRESS)."""
    t0, words = time.time(), []
    for p, off in zip(paths, offsets):
        words += [dict(w, start=round(w["start"] + off, 3), end=round(w["end"] + off, 3)) for w in transcribe(p, model)["words"]]
    return {"source": f"faster-whisper {model} per chunk (local, free)", "seconds": round(time.time() - t0, 1), "words": words}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("audio")
    p.add_argument("out")
    p.add_argument("--model", default="small.en")
    p.add_argument("--script", help="the script text: names in it are given to Whisper as a spelling hint")
    a = p.parse_args(argv)
    hint = Path(a.script).read_text(encoding="utf-8")[:800] if a.script else None
    res = transcribe(Path(a.audio), a.model, hint)
    Path(a.out).write_text(json.dumps(res, indent=0), encoding="utf-8")
    print(f"{len(res['words'])} words in {res['seconds']} s", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
