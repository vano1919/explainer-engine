# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/audio/visemes.py`
# Target Module : explainer_engine/audio/visemes.py
# Target Classes/Symbols : def shape_of(), def opening_of(), def mouth_open(), def blinks(), def _spoken_until(), def emphasis(), def _ease(), def tilt_at()
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

"""RETIRED by D-39 (2026-10-16, ElevenLabs is the narrator):
Kokoro code kept for provenance (docs/PROVENANCE.md) and for audio/timings consumers; never a production read.

A talking mouth, frame by frame, from what is being said. stdlib only.

The mouth follows Kokoro's own phonemes (``[[phoneme, start, end], ...]``): every sound has an opening (wide vowels
open fully, close vowels a little, most consonants a little, m/b/p and silence close it) and a shape (rounded vowels
-> ``talk_o``, the others -> ``talk_e``; consonants keep the vowel's shape). The opening is smoothed over the last
~120 ms and leads the sound by 30 ms, so the mouth glides. Blinks come from a seeded schedule and move to the next
silence, so the character never closes its eyes mid-word. A stressed vowel spoken louder than almost every other one
can drive a small gesture (at most once per sentence). The mapping to the mascot's mouth drawings is the renderer's
job (Phase 4); this module only says how open and which shape.
"""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/render/visemes.py
# changed: owl sprites/poses, layer(), moods (sleep parts) and OwlTrack removed; the timing logic is unchanged

from __future__ import annotations

import bisect
import math
import random

ROUNDED = set("oɔuʊwɒOWQ")
OPEN = set("aæɑʌəɛeiɪɐᵻɜɚAIYɝ")
LIPS = set("mbpfv")
STRESS = "ˈ"
SILENT = set(" .,?!;:—…\"“”()")
WIDE = set("aæɑʌɐAIWY")      # the widest mouth
NARROW = set("iɪᵻuʊw")        # close vowels: a small opening
SHUT = set("mbp")             # lips closed
LIGHT = set("fv")
OPEN_WIDE, OPEN_MID, OPEN_NARROW, OPEN_CONSONANT, OPEN_LIGHT = 1.0, 0.7, 0.45, 0.25, 0.1
MARKS = set("ˈˌːˑ")            # stress and length marks: keep the sound before them
LEAD = 0.03                   # the mouth moves a little before the sound
SMOOTH_TAU = 0.04             # seconds; the opening follows over ~3 tau
SMOOTH_TAPS = 12
SMOOTH_STEP = 0.01
BLINK_SECONDS = 0.16
EMPHASIS_SECONDS = 0.9
EMPHASIS_DEGREES = 2.5


def shape_of(phoneme: str) -> str | None:
    """The mouth for one phoneme, or None to keep the current one."""
    if phoneme in ROUNDED:
        return "talk_o"
    if phoneme in OPEN:
        return "talk_e"
    if phoneme in LIPS:
        return "neutral"
    return None


def opening_of(phoneme: str) -> float | None:
    """How far one sound opens the mouth (0 closed .. 1 widest), or None to keep the sound before it."""
    if phoneme in MARKS:
        return None
    if phoneme in SILENT or phoneme in SHUT:
        return 0.0
    if phoneme in WIDE:
        return OPEN_WIDE
    if phoneme in NARROW:
        return OPEN_NARROW
    if phoneme in OPEN or phoneme in ROUNDED:
        return OPEN_MID
    if phoneme in LIGHT:
        return OPEN_LIGHT
    return OPEN_CONSONANT


def mouth_open(phones: list[list], fps: float, first: int, n: int) -> tuple[list[float], list[str]]:
    """(opening 0..1, shape ``talk_o``/``talk_e``) for frames first .. first+n-1 (phones: [[p, start, end], ...] sorted).
    Each frame depends only on its own time: the smoothing is a fixed window over the sounds just before it."""
    starts = [p[1] for p in phones]
    values, shapes, last, shape = [], [], 0.0, "talk_e"
    for p, _s, _e in phones:  # marks and consonants carry the sound and the vowel shape before them
        v = opening_of(p)
        last = last if v is None else v
        shape = {"talk_o": "talk_o", "talk_e": "talk_e"}.get(shape_of(p), shape)
        values.append(last)
        shapes.append(shape)
    weights = [math.exp(-j * SMOOTH_STEP / SMOOTH_TAU) for j in range(SMOOTH_TAPS)]
    total = sum(weights)

    def at(t: float) -> tuple[float, int]:
        k = bisect.bisect_right(starts, t) - 1
        if k < 0 or t >= phones[k][2] + 0.04:  # between phones: silence closes the mouth
            return 0.0, k
        return values[k], k

    opening, shape_track = [], []
    for i in range(first, first + n):
        t = (i + 0.5) / fps + LEAD
        o = sum(w * at(t - j * SMOOTH_STEP)[0] for j, w in enumerate(weights)) / total
        k = at(t)[1]
        opening.append(min(1.0, max(0.0, o)))
        shape_track.append(shapes[k] if k >= 0 else "talk_e")
    return opening, shape_track



def blinks(seed: str, duration: float, phones: list[list]) -> list[tuple[float, float]]:
    """Seeded blinks every 4-8 s, each moved into the next silence (within 1.5 s) or dropped."""
    rng = random.Random(f"{seed}|blink")
    starts = [p[1] for p in phones]
    out, t = [], rng.uniform(2.0, 5.0)
    while t < duration:
        a = t
        while a < t + 1.5:
            busy = _spoken_until(phones, starts, a - 0.04, a + BLINK_SECONDS + 0.04)
            if busy is None:
                out.append((round(a, 3), round(a + BLINK_SECONDS, 3)))
                break
            a = busy + 0.05
        t += rng.uniform(4.0, 8.0)
    return out


def _spoken_until(phones: list[list], starts: list[float], a: float, b: float) -> float | None:
    """The end of the last spoken phoneme overlapping [a, b], or None when [a, b] is silent."""
    k = max(0, bisect.bisect_right(starts, a) - 1)
    end = None
    while k < len(phones) and phones[k][1] < b:
        if phones[k][2] > a and phones[k][0] not in SILENT:
            end = phones[k][2]
        k += 1
    return end


def emphasis(phones: list[list], level_at, sentence_ends: list[float], share: float = 0.1) -> list[float]:
    """Times of the loudest stressed vowels: the top ``share`` of all stressed vowels, at most one per sentence."""
    cands = []
    for k, (p, s, _e) in enumerate(phones[:-1]):
        if p == STRESS and shape_of(phones[k + 1][0]) in ("talk_o", "talk_e"):
            t = phones[k + 1][1]
            cands.append((float(level_at(t)), t))
    if not cands:
        return []
    cut = sorted(c[0] for c in cands)[int(len(cands) * (1.0 - share))] if len(cands) > 1 else cands[0][0]
    best: dict[int, tuple[float, float]] = {}
    for lv, t in cands:
        if lv < cut:
            continue
        sent = bisect.bisect_left(sentence_ends, t)
        if sent not in best or lv > best[sent][0]:
            best[sent] = (lv, t)
    return sorted(t for _, t in best.values())


def _ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3.0 - 2.0 * x)


def tilt_at(t: float, emphasis_times: list[float]) -> float:
    """Head tilt in degrees: a slow, irregular sway plus a short lean on an emphasised word."""
    sway = 0.5 * (math.sin(0.131 * t) + math.sin(0.0713 * t + 1.7)) * 0.6
    k = bisect.bisect_right(emphasis_times, t) - 1
    lean = 0.0
    if k >= 0:
        x = (t - emphasis_times[k]) / EMPHASIS_SECONDS
        if x < 1.0:
            lean = EMPHASIS_DEGREES * (_ease(x / 0.3) if x < 0.3 else 1.0 - _ease((x - 0.3) / 0.7))
    return sway + lean
