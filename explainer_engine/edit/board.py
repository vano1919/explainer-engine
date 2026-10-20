"""The storyboard (D-42, creator 2026-10-16): pictures follow the story, not the clock.

Day 1 v5 cut 44 pictures into 3 minutes (14 a minute) and its fire beat showed campfires already burning while the narrator
was still explaining how the lens would light the first one. Two causes: the story state (UR-27's ``not_yet``) was lifted
for a whole beat instead of at the word, and the cut rate left no time for a picture to mean anything. The board fixes
both:

* a shot starts at a written phrase (``at``), the cut goes in the pause before it (UR-12);
* ``events`` say at which phrase a thing first exists ("fire" at "and fire"); a picture that ``shows`` a thing before
  its event is a FAIL (STATE-1), whatever beat it is in;
* a picture's heroes must fit its line: when the line names heroes and the picture's heroes are all others, FAIL
  (HERO-1: Franklin's hand lifting Einstein's glasses);
* one picture may carry several lines through speech bubbles (``finish/bubbles.py``), so a dialogue is one held picture;
* rhythm (BP-40, docs/SOURCED_RULES.md): at most MAX_PER_MIN pictures a minute, no shot under MIN_SHOT, and something must
  change on screen (a cut, a bubble or an accent) often enough for the section: inside the hook window a still longer than
  HOOK_STILL is a FAIL; in the body a still longer than BODY_REVIEW is a REVIEW and longer than BODY_FAIL a FAIL;
* a pattern interrupt (BP-41): something changes inside the INTERRUPT window of the first minute, else a REVIEW.

    python -m explainer_engine.edit.board <board.json> <words.json> [--out timed.json]
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from explainer_engine.edit import shot_rules as R
from explainer_engine.standards import sourced_rules as SR

MAX_PER_MIN = float(SR.T("BP-40", "pictures_per_min_max"))  # v5 had 14.3; the creator: pictures change too often
MIN_SHOT = 2.5
MIN_INSERT = 2.0
HOOK_WINDOW = float(SR.T("BP-40", "hook_window_s"))  # BP-40: the first seconds, where a still is judged hardest
HOOK_STILL = float(SR.T("BP-40", "hook_max_still_s"))  # a still inside the hook window longer than this FAILs
BODY_REVIEW = float(SR.T("BP-40", "body_review_still_s"))  # a still in the body longer than this is a REVIEW ...
BODY_FAIL = float(SR.T("BP-40", "body_fail_still_s"))  # ... and longer than this a FAIL
INTERRUPT = [float(x) for x in SR.T("BP-41", "window_s")]  # BP-41: a change must land inside this window
STATE_GRACE = 0.3  # a thing may appear this long before its word (the cut sits in the pause before it)
BUBBLE_LEAD = 0.12


def _tok(s: str) -> str:
    return re.sub(r"[^a-z0-9']", "", s.lower().replace("’", "'"))


def find_phrase(words: list[dict], phrase: str, start: int = 0) -> int:
    """Index of the first word of ``phrase`` at or after ``start`` (punctuation and case ignored)."""
    toks = [_tok(t) for t in phrase.split() if _tok(t)]
    for i in range(start, len(words) - len(toks) + 1):
        if all(_tok(words[i + k]["w"]) == toks[k] for k in range(len(toks))):
            return i
    raise ValueError(f"phrase not found after word {start}: {phrase!r}")


def cut_before(words: list[dict], i: int) -> tuple[float, bool]:
    """(time, legal): the middle of the pause before word ``i``; legal when that pause is a UR-12 cut point."""
    if i == 0:
        return 0.0, True
    a, b = words[i - 1]["e"], words[i]["s"]
    t = round((a + b) / 2, 3)
    return t, R.cut_ok(t, words)


def time_board(board: dict, words: list[dict], duration: float) -> dict:
    """Shots with start/end and bubbles with start/end, from the phrases."""
    shots, cursor = [], 0
    for k, s in enumerate(board["shots"]):
        i = 0 if k == 0 else find_phrase(words, s["at"], cursor)
        t, legal = cut_before(words, i)
        row = dict(s, word=i, start=t, cut_legal=legal)
        cursor = i + 1
        shots.append(row)
    for k, s in enumerate(shots):
        s["end"] = shots[k + 1]["start"] if k + 1 < len(shots) else duration
        nxt = shots[k + 1]["word"] if k + 1 < len(shots) else len(words)
        s["text"] = " ".join(w["w"] for w in words[s["word"]:nxt])
        bub, bc = [], s["word"]
        for b in s.get("bubbles", []):
            j = find_phrase(words, b["at"], bc)
            bc = j + 1
            start = max(s["start"], words[j]["s"] - BUBBLE_LEAD)
            if b.get("until"):
                end = words[find_phrase(words, b["until"], bc)]["s"] - 0.05
            elif b.get("hold"):
                end = start + float(b["hold"])
            else:
                end = s["end"] - 0.05
            bub.append(dict(b, start=round(start, 3), end=round(min(end, s["end"] - 0.05), 3)))
        s["bubbles"] = bub
    return {"shots": shots, "duration": duration}


def event_times(board: dict, words: list[dict]) -> dict[str, float]:
    out = {}
    for e in board.get("events", []):
        out[e["thing"]] = cut_before(words, find_phrase(words, e["at"]))[0]  # exists from the cut before its words
    return out


def named_heroes(text: str, heroes: dict[str, list[str]]) -> set[str]:
    low = " " + re.sub(r"[^a-z' ]", " ", text.lower()) + " "
    return {h for h, names in heroes.items() if any(f" {n.lower()} " in low for n in names)}


def change_times(shots: list[dict], duration: float) -> list[float]:
    """When something changes on screen: every cut, every bubble, every accent but the wobble, and the end."""
    times = {s["start"] for s in shots} | {b["start"] for s in shots for b in s.get("bubbles", [])}
    times |= {a["start"] for s in shots for a in s.get("accents", []) if a.get("kind") != "wobble"}
    return sorted(times | {duration})


def still_excess(a: float, b: float) -> tuple[float, float]:
    """A still from ``a`` to ``b`` split by section (BP-40): (its length inside the hook window, its length in the body)."""
    return max(0.0, min(b, HOOK_WINDOW) - a), max(0.0, b - max(a, HOOK_WINDOW))


def still_too_long(a: float, b: float, hook_limit: float | None = None, body_limit: float | None = None) -> bool:
    """True when a still from ``a`` to ``b`` breaks its section's limit (the hook's FAIL line, the body's REVIEW line)."""
    hook, body = still_excess(a, b)
    return hook > (HOOK_STILL if hook_limit is None else hook_limit) + 1e-6 \
        or body > (BODY_REVIEW if body_limit is None else body_limit) + 1e-6


def check(board: dict, timed: dict) -> list[dict]:
    words_by_shot = [s["text"] for s in timed["shots"]]
    pics, heroes = board["pictures"], board.get("heroes", {})
    events = board.get("_event_times", {})
    out: list[dict] = []

    def add(rule, sid, detail, sev="FAIL"):
        out.append({"rule": rule, "shot": sid, "severity": sev, "detail": detail})

    shots = timed["shots"]
    for k, s in enumerate(shots):
        sid, p = s.get("id", f"#{k + 1}"), pics[s["picture"]]
        dur = s["end"] - s["start"]
        if not s["cut_legal"]:
            add("CUT-1", sid, f"cut at {s['start']:.2f} s is not in a punctuated pause before {s['at']!r}")
        if dur < (MIN_INSERT if s.get("insert") else MIN_SHOT):
            add("RHYTHM-2", sid, f"{dur:.2f} s is shorter than {MIN_INSERT if s.get('insert') else MIN_SHOT} s")
        for thing in p.get("shows", []):
            if thing in events and events[thing] > s["start"] + STATE_GRACE:
                add("STATE-1", sid, f"{s['picture']} shows {thing!r} at {s['start']:.1f} s; it first exists at "
                                    f"{events[thing]:.1f} s")
        if "reveal" in s:  # the shot that shows a new thing should start on its word, not seconds before
            thing = s["reveal"]
            if thing in events and abs(events[thing] - s["start"]) > 1.0:
                add("STATE-2", sid, f"reveal of {thing!r} starts {events[thing] - s['start']:.1f} s off its word", "REVIEW")
        lead = re.split(r"(?<=[.!?])\s", s["text"], maxsplit=1)[0]  # the line the picture is cut on
        said = named_heroes(lead, heroes) or named_heroes(s["text"], heroes)
        shown = set(p.get("heroes", []))
        if said and shown and not (said & shown):
            add("HERO-1", sid, f"the line names {sorted(said)}, the picture shows {sorted(shown)}")
        context = named_heroes(s["text"], heroes) | named_heroes(" ".join(words_by_shot[max(0, k - 2):k]), heroes)
        stray = shown - context
        if stray and not s.get("heroes_ok"):
            add("HERO-2", sid, f"{sorted(stray)} on screen but not named in this or the two lines before", "REVIEW")
        for b in s["bubbles"]:
            if b["who"] not in p.get("speakers", {}):
                add("BUBBLE-3", sid, f"bubble speaker {b['who']!r} has no mouth point in {s['picture']}")
    from explainer_engine.finish.bubbles import check_bubbles
    for f in check_bubbles([b for s in shots for b in s["bubbles"]]):
        out.append(dict(f, shot="-"))
    dur = timed["duration"]
    # a re-frame of the picture already on screen (reuse "reframe") is not a new picture: it counts half (creator 2026-10-16:
    # "too many picture changes" was the complaint; a different move on the same picture is the zoom he asked for)
    weight = sum(0.5 if s.get("reuse") == "reframe" else 1.0 for s in shots)
    rate = weight / (max(dur, 60.0) / 60.0) if dur else 0.0  # a clip under a minute is measured as a minute
    if rate > MAX_PER_MIN:
        add("RHYTHM-1", "-", f"{rate:.1f} pictures a minute > {MAX_PER_MIN}")
    changes = change_times(shots, dur)
    for a, b in zip(changes, changes[1:]):  # RHYTHM-3 is section-aware (BP-40): the hook window, then the body
        hook, body = still_excess(a, b)
        if hook > HOOK_STILL + 1e-6:
            add("RHYTHM-3", "-", f"nothing changes on screen from {a:.1f} to {b:.1f} s inside the first {HOOK_WINDOW:.0f} s "
                                 f"({hook:.1f} s > {HOOK_STILL:.0f}; BP-40)")
        if body > BODY_FAIL + 1e-6:
            add("RHYTHM-3", "-", f"nothing changes on screen from {a:.1f} to {b:.1f} s ({body:.1f} s > {BODY_FAIL:.0f}; BP-40)")
        elif body > BODY_REVIEW + 1e-6:
            add("RHYTHM-3", "-", f"nothing changes on screen from {a:.1f} to {b:.1f} s ({body:.1f} s > {BODY_REVIEW:.0f}; BP-40)",
                "REVIEW")
    if dur >= INTERRUPT[1] and not any(INTERRUPT[0] <= t <= INTERRUPT[1] for t in changes[1:-1]):
        add("BP-41", "-", f"no cut, bubble or accent between {INTERRUPT[0]:.0f} and {INTERRUPT[1]:.0f} s: script one pattern "
                          "interrupt there (an insert, a text pop or a music change)", "REVIEW")
    return out


def build(board: dict, words_doc: dict) -> tuple[dict, list[dict]]:
    words = words_doc["words"]
    timed = time_board(board, words, float(words_doc["duration"]))
    board = dict(board, _event_times=event_times(board, words))
    return timed, check(board, timed)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    p.add_argument("board")
    p.add_argument("words")
    p.add_argument("--out")
    a = p.parse_args(argv)
    board = json.loads(Path(a.board).read_text(encoding="utf-8"))
    timed, findings = build(board, json.loads(Path(a.words).read_text(encoding="utf-8")))
    if a.out:
        Path(a.out).write_text(json.dumps(timed, indent=1), encoding="utf-8")
    for f in findings:
        print(f"{f['severity']:6} {f['rule']:9} {f['shot']:6} {f['detail']}")
    n = len(timed["shots"])
    print(f"{n} shots, {n / (timed['duration'] / 60):.1f} a minute, "
          f"{sum(f['severity'] == 'FAIL' for f in findings)} FAIL", file=sys.stderr)
    return 1 if any(f["severity"] == "FAIL" for f in findings) else 0


if __name__ == "__main__":
    raise SystemExit(main())
