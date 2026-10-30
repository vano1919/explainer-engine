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


def seconds(text: str, *, pause_after: float | None = None) -> float:
    """Estimated heard seconds of ``text``: the units of ``_weights`` scaled so that the calibration corpus's average word lasts
    ``60 / BP-01 wpm_target`` seconds (the pace comes from the registry, the shape from the calibration). ``pause_after`` adds a
    planned silence after the line."""
    cal = calibration()
    unit_s = (60.0 / SR.T("BP-01", "wpm_target")) / cal["mean_units_per_word"]
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
