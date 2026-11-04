# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/scripting/syllables.py`
# Target Module : explainer_engine/scripting/syllables.py
# Target Classes/Symbols : def count(), def calibration(), def _weights(), def seconds(), def calibrate(), def main()
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

"""How long a line takes to say, estimated from its syllables (Blueprint P3, BP-01, BP-115). numpy and stdlib only.

Used before any voice exists: the twist length (ST-23), the ad-safety window (ST-22), a segment's seconds in a plan that has no
words yet (``variant_plan``). The pace is BP-01's heard pace (``wpm_target``), never a number of this module; the committed
``syllables_calibration.json`` supplies only the SHAPE of a read: how much a syllable adds to a word and how long the full stop
and the comma pause, as ratios fitted on the word times of released episodes read by ElevenLabs Scribe (a file whose ``source``
names another provider is skipped: Kokoro and local Whisper times have another rhythm).

    python -m explainer_engine.scripting.syllables calibrate examples/stone_age/day1_v5/words.json ... [--write]
    python -m explainer_engine.scripting.syllables seconds "A line to time."

``count`` is the one syllable counter of the project (``production/validate.syllables`` delegates to it).
"""

from __future__ import annotations

import json
import re
import sys
from functools import lru_cache
from pathlib import Path

from explainer_engine.standards import sourced_rules as SR

CALIBRATION = Path(__file__).with_name("syllables_calibration.json")
WORD = re.compile(r"[A-Za-z0-9][A-Za-z0-9'’-]*")
SCRIBE = "elevenlabs scribe"


def count(word: str) -> int:
    """Syllables of one English word by vowel groups (a silent final -e dropped, -le kept); at least one. Good enough for a
    Flesch-Kincaid grade and a read-time estimate on short lines; no dependency."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and groups > 1:
        groups -= 1
    return max(1, groups)


@lru_cache(maxsize=1)
def calibration() -> dict:
    return json.loads(CALIBRATION.read_text(encoding="utf-8"))


def _weights(text: str, cal: dict) -> float:
    """Relative duration of ``text``: per word ``1 + ratio * syllables`` units, plus a pause (in units) after . ! ? and ,"""
    total = 0.0
    for m in WORD.finditer(text):
        total += 1.0 + cal["ratio_b_over_a"] * (count(m.group()) if re.search(r"[A-Za-z]", m.group()) else 2)
        tail = text[m.end():m.end() + 2].lstrip("\"'”’)")[:1]
        if tail in ".!?":
            total += cal["pause_units_sentence"]
        elif tail in ",;:—-" or text[m.end():m.end() + 2] == "—":
            total += cal["pause_units_clause"]
    return total


def seconds(text: str, *, pause_after: float | None = None, zone: str | None = None, wpm: float | None = None) -> float:
    """Estimated heard seconds of ``text``: the units of ``_weights`` scaled so that the calibration corpus's average word lasts
    ``60 / pace`` seconds (the pace comes from the registry, the shape from the calibration). The pace is BP-01's ``wpm_target``,
    or ``wpm``, or the heard pace of a rhythm ``zone`` (BP-169, ``edit/rhythm_profile.py``). ``pause_after`` adds a planned
    silence after the line."""
    cal = calibration()
    if wpm is None and zone is not None:
        from explainer_engine.edit import rhythm_profile
        wpm = rhythm_profile.zone_wpm(zone)
    unit_s = (60.0 / (float(wpm) if wpm is not None else SR.T("BP-01", "wpm_target"))) / cal["mean_units_per_word"]
    return round(_weights(text, cal) * unit_s + (pause_after or 0.0), 3)


def calibrate(words_json: list[Path]) -> dict:
    """Fit the shape on word-time files (``{"source", "words": [{"w", "s", "e"}]}``) read by Scribe; others are skipped and listed."""
    import numpy as np

    syl, dur, gaps_sentence, gaps_clause, gaps_word, used, skipped = [], [], [], [], [], [], []
    for path in words_json:
        doc = json.loads(Path(path).read_text(encoding="utf-8"))
        if SCRIBE not in str(doc.get("source", "")).lower():
            skipped.append({"path": str(path), "why": f"source is not Scribe: {str(doc.get('source', ''))[:60]}"})
            continue
        ws = doc["words"]
        for i, w in enumerate(ws):
            syl.append(count(w["w"]) if re.search(r"[A-Za-z]", w["w"]) else 2)
            dur.append(w["e"] - w["s"])
            if i + 1 < len(ws):
                gap = max(0.0, ws[i + 1]["s"] - w["e"])
                last = w["w"].rstrip("\"'”’)")[-1:]
                (gaps_sentence if last in ".!?" else gaps_clause if last in ",;:" else gaps_word).append(gap)
        used.append({"path": str(path), "words": len(ws), "seconds": doc.get("duration"),
                     "provider": "ElevenLabs Scribe", "voice": doc.get("voice")})
    if not used:
        raise ValueError("no Scribe file among the inputs")
    b, a = np.polyfit(np.array(syl, float), np.array(dur, float), 1)
    g0 = float(np.mean(gaps_word)) if gaps_word else 0.0
    unit = float(a) + g0  # one word's base duration plus its ordinary gap = 1 unit
    ratio = float(b) / unit
    cal = {"ratio_b_over_a": round(ratio, 4),
           "pause_units_sentence": round(max(0.0, (float(np.mean(gaps_sentence)) - g0)) / unit, 4) if gaps_sentence else 0.0,
           "pause_units_clause": round(max(0.0, (float(np.mean(gaps_clause)) - g0)) / unit, 4) if gaps_clause else 0.0}
    n = len(syl)
    units = n + cal["ratio_b_over_a"] * sum(syl) + cal["pause_units_sentence"] * len(gaps_sentence) + cal["pause_units_clause"] * len(gaps_clause)
    cal.update({"mean_units_per_word": round(units / n, 4), "sources": used, "skipped": skipped,
                "fit": {"duration_s = a + b * syllables": [round(float(a), 4), round(float(b), 4)], "gap_word_s": round(g0, 4)}})
    return cal


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 2
    if argv[0] == "calibrate":
        cal = calibrate([Path(a) for a in argv[1:] if not a.startswith("--")])
        if "--write" in argv:
            CALIBRATION.write_text(json.dumps(cal, indent=1) + "\n", encoding="utf-8")
        print(json.dumps(cal, indent=1))
        return 0
    if argv[0] == "seconds":
        print(seconds(" ".join(argv[1:])))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
