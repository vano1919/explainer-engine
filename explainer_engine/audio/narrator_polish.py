# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/narrator_polish.py`
# Target Module : explainer_engine/audio/narrator_polish.py
# Target Classes/Symbols : def polish(), def polish_in_place(), def _seconds()
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

"""The narrator's standard polish (creator, 2026-11-01): every take of the channel narrator (Odom, config/channel_voices.json)
goes through one fixed ffmpeg chain, chosen by his ear on the same 41 s eleven_v4 take: rumble cut under 60 Hz, light noise
reduction, +12 dB low shelf at 150 Hz, a small -2 dB dip at 300 Hz so the bass does not make the voice muddy, a -0.6 dB trim
that keeps the loudness of the raw take (-24.4 LUFS on the test take), and a limiter at 0.95 (the test take peaked at -2.8 dBFS).
Free: no credits, no regeneration. Timing is untouched (filters only, no tempo or pitch step), so word timings stay valid."""
from __future__ import annotations

import subprocess
from pathlib import Path

from ..core.errors import ConfigError

BASS_DB, BASS_HZ = 12, 150
CHAIN = ("volume=-0.6dB,highpass=f=60,afftdn=nr=8:nf=-50,"
         f"bass=g={BASS_DB}:f={BASS_HZ}:w=0.7,equalizer=f=300:t=q:w=1:g=-2,alimiter=limit=0.95")


def polish(src: Path | str, dst: Path | str) -> Path:
    """``src`` through ``CHAIN`` into ``dst`` (format by its extension). Raises ConfigError when ffmpeg fails."""
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-i", str(src), "-af", CHAIN, str(dst)]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        raise ConfigError(f"narrator polish failed: {done.stderr.strip()[:300]}")
    return Path(dst)


def polish_in_place(wav: Path | str) -> dict:
    """Polish ``wav`` where it lies (temp file + rename) and say what was done, for words.json. The length is checked: a
    filter chain must not move a word (the timings were measured before it)."""
    wav = Path(wav)
    tmp = wav.with_name(wav.stem + ".polish.wav")
    before = _seconds(wav)
    polish(wav, tmp)
    after = _seconds(tmp)
    if abs(after - before) > 1 / 30:
        tmp.unlink(missing_ok=True)
        raise ConfigError(f"narrator polish moved the length by {after - before:+.3f} s: the word timings would be wrong")
    import os
    os.replace(tmp, wav)
    return {"chain": CHAIN, "seconds_before": round(before, 3), "seconds_after": round(after, 3)}


def _seconds(path: Path) -> float:
    import wave
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()
