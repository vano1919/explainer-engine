"""Stage guard (D-48, docs/STORY_ENGINE.md "The writers' room"): each agent stage may change only its own fields of the
one production script, so a later pass (voice tags, shots, sounds) can never quietly rewrite the story an earlier pass
settled. This is how a mid-size model (Claude Sonnet) keeps the whole text while it adds technical detail: the words are
frozen after the scene pass, and the guard proves it.

    python -m explainer_engine.scripting.stage_guard <stage> before.json after.json   # exit 1 on a violation

Stages and what they own:

* ``architect``  the story layer: ``drama``, ``cast``, ``periods``, segment ids, ``beat``, ``purpose``, ``period``, ``light_beat``, segment ``drama``
* ``writer``     the words: segment ``lines`` (text, speaker, claims); one segment at a time
* ``beats``      the visual beats (VB rules): line ``visual_beats`` only, written segment by segment right after the writer, on
  the same frozen words (stage 2b, agent ``beat-writer``); the Shorts' lines too (``shorts[].lines[].visual_beats``, SS-09)
* ``performer``  the delivery: line ``tags``, ``emphasis``, ``tone``, ``emotion``, ``pause_after``; the text may only gain
  an interjection at its start (``INTERJECTIONS``)
* ``editor``     the picture and sound: ``shots``, segment ``audio``, ``music``, ``graphics``, ``library``, ``story``,
  ``look``, ``picture_dirs``, ``sound_dirs``; of the beats only their ``pos`` (where on the frame), never what they show
* ``caster``     the voices: ``voice`` and ``cast.<id>.voice`` (the architect owns the rest of ``cast``)
* ``shorts``     the ``shorts`` block
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

INTERJECTIONS = ("oh", "hmm", "well", "right", "ah", "uh-oh", "wait", "okay", "huh", "so", "look", "yeah", "nope")
SEG_STORY = ("id", "beat", "purpose", "period", "light_beat", "drama")
LINE_WORDS = ("text", "speaker", "claims")
LINE_DELIVERY = ("tags", "emphasis", "tone", "emotion", "pause_after")
STAGES = {
    "architect": {"top": {"drama", "episode", "periods", "cast"}, "seg": set(SEG_STORY), "line": set()},
    "writer": {"top": set(), "seg": {"lines"}, "line": set(LINE_WORDS)},
    "beats": {"top": set(), "seg": set(), "line": {"visual_beats"}},
    "performer": {"top": set(), "seg": set(), "line": set(LINE_DELIVERY) | {"text"}},
    "editor": {"top": {"music", "graphics", "library", "story", "look", "picture_dirs", "sound_dirs", "world"},
               "seg": {"shots", "audio"}, "line": set()},
    "caster": {"top": {"voice"}, "seg": set(), "line": set(), "cast_voice": True},
    "shorts": {"top": {"shorts"}, "seg": set(), "line": set()},
}


def _interjection_only(old: str, new: str) -> bool:
    if old == new:
        return True
    if not new.endswith(old) and not new.endswith(old[:1].lower() + old[1:]):
        return False
    head = new[: len(new) - len(old)].strip().rstrip(",.!?—-").strip().lower()
    return head in INTERJECTIONS


def violations(stage: str, before: dict, after: dict) -> list[str]:
    own = STAGES[stage]
    out: list[str] = []
    for k in sorted(set(before) | set(after)):
        if k == "segments" or k in own["top"]:
            continue
        if k == "cast" and own.get("cast_voice"):  # the caster changes only each hero's voice
            bc, ac = before.get("cast", {}), after.get("cast", {})
            for h in sorted(set(bc) | set(ac)):
                if {x: y for x, y in (bc.get(h) or {}).items() if x != "voice"} != {x: y for x, y in (ac.get(h) or {}).items() if x != "voice"}:
                    out.append(f"cast.{h} changed beyond its voice")
            continue
        if k == "shorts" and stage == "beats" and _no_short_beats(before.get(k)) == _no_short_beats(after.get(k)):
            continue  # SS-09: the beat-writer writes the Shorts' beats too, nothing else of a Short
        if before.get(k) != after.get(k):
            out.append(f"{k} changed: not the {stage}'s field")
    bs, as_ = before.get("segments", []), after.get("segments", [])
    if stage != "architect" and [s.get("id") for s in bs] != [s.get("id") for s in as_]:
        out.append("segments added, removed or reordered: only the architect does that")
        return out
    for sb, sa in zip(bs, as_):
        sid = sa.get("id")
        for k in sorted(set(sb) | set(sa)):
            if k in own["seg"] or k == "lines":
                continue
            if sb.get(k) != sa.get(k):
                out.append(f"{sid}.{k} changed: not the {stage}'s field")
        lb, la = sb.get("lines", []), sa.get("lines", [])
        if "lines" in own["seg"]:
            continue  # the writer owns whole lines of the segments it touches
        if len(lb) != len(la):
            out.append(f"{sid}: lines added or removed (the words are frozen after the writer)")
            continue
        for i, (a, b) in enumerate(zip(lb, la), 1):
            for k in sorted(set(a) | set(b)):
                if a.get(k) == b.get(k):
                    continue
                if k == "text" and "text" in own["line"] and _interjection_only(a["text"], b["text"]):
                    continue
                if k == "visual_beats" and stage == "editor" and _unplaced(a.get(k)) == _unplaced(b.get(k)):
                    continue  # the editor may move a beat on the frame (pos) to fit the picture it chose
                if k not in own["line"] or k == "text":
                    out.append(f"{sid} line {i}: {k} changed ({str(a.get(k))[:30]!r} -> {str(b.get(k))[:30]!r})")
    return out


def _no_short_beats(shorts) -> list | None:
    if shorts is None:
        return None
    return [dict(sh, lines=[{k: v for k, v in ln.items() if k != "visual_beats"} for ln in sh.get("lines", [])]) for sh in shorts]


def _unplaced(beats) -> list | None:
    return None if beats is None else [{k: v for k, v in b.items() if k != "pos"} for b in beats]


def words_frozen(before: dict, after: dict) -> bool:
    """True when every spoken word is unchanged except allowed interjections (the performer's promise)."""
    return not [v for v in violations("performer", before, after) if "text" in v]


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    stage, a, b = argv[0], Path(argv[1]), Path(argv[2])
    found = violations(stage, json.loads(a.read_text(encoding="utf-8")), json.loads(b.read_text(encoding="utf-8")))
    for v in found:
        print("FAIL", v)
    print(f"{len(found)} violation(s) for stage {stage}")
    return 1 if found else 0


if __name__ == "__main__":
    raise SystemExit(main())
