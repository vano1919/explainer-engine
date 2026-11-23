"""Transcript observer (OB-1): what was heard against what the script says, word by word.

No transcription happens here (W4 makes no new ASR call): the words come from an existing transcript, a Whisper per-clip file
(``{shot: [[word, start, end], ...]}``, ``planning/full_film_*/ltx_whisper_*.json``) or a Scribe file (``{"words": [{"text", "start",
"end", "type"}]}``). NOT_RUN when no transcript exists for the shot. ASR spells foreign words its own way, so a heard word that is
close enough to the expected one (difflib ratio >= ``SIMILAR``) counts as the same word.
"""
from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from explainer_engine.qa import observe as OB
from explainer_engine.qa import status as ST

SIMILAR = 0.6


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", (text or "").lower().replace("’", "'"))


def load_words(path: Path, shot: str | None = None) -> list[tuple[str, float, float]] | None:
    """[(word, start, end)] of a Whisper per-shot file (needs ``shot``) or a Scribe file; None when the file or the shot is absent."""
    p = Path(path)
    if not p.is_file():
        return None
    doc = json.loads(p.read_text(encoding="utf-8"))
    if "words" in doc:
        return [(w["text"], float(w["start"]), float(w["end"])) for w in doc["words"] if w.get("type", "word") == "word"]
    if shot is None or shot not in doc:
        return None
    return [(w[0], float(w[1]), float(w[2])) for w in doc[shot]]


def compare(expected_text: str, words: list[tuple[str, float, float]], duration_s: float | None = None) -> tuple[list[dict], list[str]]:
    """(defects, diff lines). TXT-FALSE: words where the script has none; TXT-DUP: a heard word repeated beside itself that the
    script does not repeat; TXT-EXTRA / TXT-MISSING; TXT-CUT: the last word ends where the file ends."""
    exp = tokens(expected_text)
    heard, spans = [], []
    for w, s, e in words:
        for t in tokens(w):
            heard.append(t)
            spans.append((s, e))
    defects, diff = [], []

    def at(i, j=None):
        a = spans[i][0] if i < len(spans) else (spans[-1][1] if spans else 0.0)
        b = spans[(j if j is not None else i + 1) - 1][1] if spans and (j or i + 1) <= len(spans) else a
        return f"t={a:.2f}-{b:.2f}s"

    if not exp:
        if heard:
            defects.append({"code": "TXT-FALSE", "where": at(0, len(heard)), "severity": "major",
                            "note": f"the script has no words here; heard: {' '.join(heard)}"})
            diff.append(f"+ {' '.join(heard)}  (silent beat)")
    else:
        sm = difflib.SequenceMatcher(None, exp, heard, autojunk=False)
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op == "equal":
                continue
            e_, h_ = exp[i1:i2], heard[j1:j2]
            if op == "replace" and len(e_) == len(h_) and all(difflib.SequenceMatcher(None, a, b).ratio() >= SIMILAR for a, b in zip(e_, h_)):
                continue   # an ASR spelling of the same words
            if op in ("delete", "replace") and e_:
                defects.append({"code": "TXT-MISSING", "where": at(j1) if heard else "file", "severity": "major",
                                "note": f"expected not heard: {' '.join(e_)}"})
                diff.append(f"- {' '.join(e_)}")
            if op in ("insert", "replace") and h_:
                dup = len(h_) == 1 and ((j1 > 0 and heard[j1 - 1] == h_[0]) or (j2 < len(heard) and heard[j2] == h_[0]))
                where = at(j1, j2)
                if dup:   # the repeated pair: the heard word and the neighbour it repeats
                    nb = j1 - 1 if (j1 > 0 and heard[j1 - 1] == h_[0]) else j2
                    where = f"t={min(spans[j1][0], spans[nb][0]):.2f}-{max(spans[j1][1], spans[nb][1]):.2f}s"
                defects.append({"code": "TXT-DUP" if dup else "TXT-EXTRA", "where": where, "severity": "major",
                                "note": f"heard extra: {' '.join(h_)}"})
                diff.append(f"+ {' '.join(h_)}")
    if duration_s and spans and spans[-1][1] >= duration_s - 0.03:
        defects.append({"code": "TXT-CUT", "where": f"t={spans[-1][1]:.2f}s", "severity": "minor",
                        "note": "the last word ends where the file ends: it may be cut"})
    return defects, diff


def observe(root: Path, shot: str, kind: str, path: str, expected_text: str, words, duration_s: float | None = None,
            evidence_dir: Path | None = None) -> dict:
    """The ``transcript`` record. ``words`` None -> NOT_RUN (no transcript exists)."""
    root = Path(root)
    if words is None:
        return OB.build(root, shot, kind, "transcript", path, verdict=ST.NOT_RUN, note="NOT_RUN: no transcript exists for this asset")
    defects, diff = compare(expected_text, words, duration_s)
    ev = []
    if evidence_dir is not None:
        out = Path(evidence_dir) / f"{shot}_{kind}_transcript_diff.txt"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(f"expected: {expected_text}\nheard:    {' '.join(w for w, _, _ in words).strip()}\n" + "\n".join(diff) + "\n", encoding="utf-8")
        ev.append(str(out))
    return OB.build(root, shot, kind, "transcript", path, questions=["does the heard text equal the script line?"],
                    answers={"expected": expected_text, "heard": " ".join(w.strip() for w, _, _ in words), "words": len(words)},
                    defects=defects, evidence=ev)
