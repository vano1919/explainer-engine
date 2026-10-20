"""Scene and dialogue rules SC-01..SC-10 (docs/STORY_ENGINE.md, the 2026-10-19 rewrite) on a production_script/3,
wired as PV-48. stdlib only, free, run by ``production validate`` before any paid step.

The Syndicate Wars review (the creator, 2026-10-19): "no dialogue - characters speak out of context, never meet, no
scene is set"; the audit traced it to the schema having no scene object and the DW rules having no code. These rules
make a scene a contract: a place with people in it, opposing wants, a value that turns (open_charge != close_charge,
McKee's nonevent test), lines addressed to someone present (a hero never talks to the narrator), a real back-and-forth,
subtext never spoken, and a narration register that tells the story instead of citing sources ("Rockstar's page
says..." x7 was required by the old rules; now one honesty beat carries the disclosure). Evidence per rule:
docs/research/STORYTELLING_EDITING_2026-10-19.md.

    python -m explainer_engine.scripting.scene_lint production_script.json
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SCENE_SCHEMA = "production_script/3"
ADDRESS_EXTRA = {"self", "room"}
MAX_TURN_WORDS = 35       # SC-09 hard cap; a longer turn is split or given to the narrator
REVIEW_TURN_WORDS = 15    # SC-09: the default spoken turn is 5-15 words
SPEECH_WORDS = 25         # SC-09: at most one 25-60-word "speech" per scene, at its peak
MIN_EXCHANGE = 4          # SC-05: at least one run of 4+ character lines (2+ speakers, no narrator inside)
MAX_QA_CHAIN = 3          # SC-09/DW-12: more consecutive ?-turns read as an interview
MAX_DISCLAIMER_SEGMENTS = 2  # SC-08: one honesty beat plus at most one callback
GREETING = re.compile(r"^\s*(hello|hi there|hi[,.! ]|hey there|hey[,.! ]|good (morning|evening|afternoon)|welcome)\b", re.I)
WRAP_UP = re.compile(r"^\s*(so that's|anyway|in conclusion|to sum up|well, that settles)\b", re.I)
PRESS_RELEASE = (  # SC-07: announcement register on a narrator line
    re.compile(r"\b\w+['’]s (page|site|website) (says|gives|names|lists|confirms)\b", re.I),
    re.compile(r"\b(announced|announcement|press release)\b", re.I),
    re.compile(r"\brelease date\b", re.I),
    re.compile(r"\bis set to (release|launch|come out)\b", re.I),
    re.compile(r"\bcoming (january|february|march|april|may|june|july|august|september|october|november|december)\b", re.I),
    re.compile(r"\baccording to [^.?!]{0,40}\b(page|site|website|trailer)\b", re.I),
    re.compile(r"\bthe trailer (shows|confirms|reveals)\b", re.I),
)
DISCLAIMER = re.compile(r"\b(invented|made (it |this |that )?up|we['’]re guessing|we can only guess|our (own )?assumption"
                        r"|none of this happened|our invention)\b", re.I)


def _f(out, rule, where, detail, sev):
    out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)


def binding(doc: dict) -> bool:
    return doc.get("schema") == SCENE_SCHEMA


def lint(doc: dict) -> list[dict]:
    """SC findings on a /3 script; an earlier schema gets none (its contract is unchanged)."""
    out: list[dict] = []
    if not binding(doc):
        return out
    cast = doc.get("cast", {})
    disclaimer_segs: list[str] = []
    for seg in doc["segments"]:
        sid = seg["id"]
        lines = seg["lines"]
        dialogue = [ln for ln in lines if ln.get("speaker")]
        scene = seg.get("scene")
        for li, ln in enumerate(lines):
            if not ln.get("speaker") and any(p.search(ln["text"]) for p in PRESS_RELEASE):
                _f(out, "SC-07", f"{sid} line {li + 1}", f"press-release register in narration ({ln['text'][:60]!r}): tell the "
                   "story; a date or spec enters only inside a scene as stakes or ammunition", "FAIL")
        if any(DISCLAIMER.search(ln["text"]) for ln in lines if not ln.get("speaker")):
            disclaimer_segs.append(sid)
        if not dialogue:
            continue
        if not scene:
            _f(out, "SC-01", sid, "a segment with dialogue has no scene: write scene {place, present, pov, want, "
               "obstacle_want, value, open_charge, close_charge, exit} before the lines", "FAIL")
            continue
        for who in scene.get("present", []):
            if who not in cast:
                _f(out, "SC-01", sid, f"scene.present names {who!r}, not in the cast", "FAIL")
        present = set(scene.get("present", []))
        if scene.get("pov") not in present:
            _f(out, "SC-01", sid, f"scene.pov {scene.get('pov')!r} is not present in the scene", "FAIL")
        if scene.get("open_charge") == scene.get("close_charge"):
            _f(out, "SC-02", sid, f"the value {scene.get('value', '?')!r} opens and closes {scene.get('open_charge')!r}: "
               "a scene whose charge does not turn is a nonevent - cut it or give it a turn", "FAIL")
        if len(_words(scene.get("turn", ""))) < 3:
            _f(out, "SC-02", sid, "scene.turn names the beat where the scene turns, in one sentence", "FAIL")
        want, ow = scene.get("want", "").strip().lower(), scene.get("obstacle_want", "").strip().lower()
        if want and want == ow:
            _f(out, "SC-03", sid, "want and obstacle_want are the same: no conflict, no scene; someone present must "
               "want something that collides", "FAIL")
        if not scene.get("surface_topic") or not scene.get("real_subject"):
            _f(out, "SC-10", sid, "no surface_topic / real_subject: say what they talk about and what the scene is "
               "really about (the subtext)", "REVIEW")
        real = (scene.get("real_subject") or "").strip().lower()
        speakers_seen: set[str] = set()
        speeches = 0
        qa_chain = 0
        run, best_run, run_speakers, best_speakers = 0, 0, set(), set()
        for li, ln in enumerate(lines):
            where = f"{sid} line {li + 1}"
            spk = ln.get("speaker")
            if not spk:
                run, run_speakers = 0, set()
                continue
            run += 1
            run_speakers = run_speakers | {spk}
            if run > best_run or (run == best_run and len(run_speakers) > len(best_speakers)):
                best_run, best_speakers = run, set(run_speakers)
            speakers_seen.add(spk)
            if spk not in present:
                _f(out, "SC-04", where, f"{spk} speaks but is not in scene.present: a hero talks only inside a scene "
                   "they are in", "FAIL")
            to = ln.get("to")
            if not to:
                _f(out, "SC-04", where, f"{spk}'s line has no 'to': every line is said to someone present (or 'self' / "
                   "'room'); a hero never answers the narrator", "FAIL")
            elif to not in present | ADDRESS_EXTRA:
                _f(out, "SC-04", where, f"'to': {to!r} is not present in the scene (and the narrator is never an "
                   "addressee: the fourth wall stands)", "FAIL")
            elif to == spk:
                _f(out, "SC-04", where, f"{spk} addresses themselves by id; use 'self'", "REVIEW")
            n = len(_words(ln["text"]))
            if n > MAX_TURN_WORDS:
                _f(out, "SC-09", where, f"a {n}-word turn (cap {MAX_TURN_WORDS}): split it, cut it, or give the "
                   "summary to the narrator", "FAIL")
            elif n >= SPEECH_WORDS:
                speeches += 1
                if speeches > 1:
                    _f(out, "SC-09", where, f"a second {n}-word speech in one scene: one long turn per scene, at its "
                       "peak; everything else is 5-15 words", "FAIL")
            elif n > REVIEW_TURN_WORDS:
                _f(out, "SC-09", where, f"{n} words in one turn (default 5-15): people speak in jabs; save length for "
                   "the scene's one speech", "REVIEW")
            qa_chain = qa_chain + 1 if ln["text"].rstrip().endswith("?") else 0
            if qa_chain == MAX_QA_CHAIN + 1:
                _f(out, "SC-09", where, f"{qa_chain} question-turns in a row read as an interview: answer sideways - "
                   "deflect, change the subject, counterattack (DW-12)", "REVIEW")
            if real and len(real) >= 4 and real in ln["text"].lower():
                _f(out, "SC-10", where, f"the line states the real subject ({scene['real_subject']!r}) out loud: "
                   "subtext is never spoken; let the surface carry it", "FAIL")
            if ln.get("intent") == "reveal":
                nxt = lines[li + 1] if li + 1 < len(lines) else None
                reacted = (nxt is not None and nxt.get("speaker") and nxt["speaker"] != spk) or any(
                    b["kind"] == "expression" and b.get("who") not in (None, spk)
                    for b in (ln.get("visual_beats") or []) + ((nxt or {}).get("visual_beats") or []))
                if not reacted:
                    _f(out, "SC-05", where, "a reveal lands and nobody reacts: the next beat is another character's "
                       "line or a listener's expression (DW-05, Kuleshov: show the face the line affects)", "REVIEW")
        if len(present) >= 2 and (best_run < MIN_EXCHANGE or len(best_speakers) < 2):
            _f(out, "SC-05", sid, f"no real exchange: the longest unbroken run is {best_run} character line(s) "
               f"({len(best_speakers)} speaker(s)); a scene plays at least {MIN_EXCHANGE} character lines in a row, "
               "two voices, no narrator inside", "FAIL")
        silent = present - speakers_seen - {b.get("who") for ln in lines for b in (ln.get("visual_beats") or [])
                                            if b["kind"] == "expression"}
        if silent:
            _f(out, "SC-05", sid, f"{', '.join(sorted(silent))} present but never speaks or reacts: everyone in a "
               "scene is in the scene", "REVIEW")
        first = dialogue[0]["text"]
        if GREETING.match(first):
            _f(out, "SC-06", sid, f"the scene opens on a greeting ({first[:30]!r}): enter late, in the middle of the "
               "action", "REVIEW")
        if WRAP_UP.match(lines[-1]["text"]):
            _f(out, "SC-06", sid, f"the scene closes on a wrap-up ({lines[-1]['text'][:30]!r}): leave early, within a "
               "line or two of the turn", "REVIEW")
    if len(disclaimer_segs) > MAX_DISCLAIMER_SEGMENTS:
        _f(out, "SC-08", ",".join(disclaimer_segs[:6]), f"{len(disclaimer_segs)} segments carry invention disclaimers: "
           "one honesty beat (plus at most one callback) says it once; on-screen labels and the description carry the "
           "rest (ST-09)", "FAIL")
    return out


def main(argv: list[str] | None = None) -> int:
    argv = argv if argv is not None else sys.argv[1:]
    doc = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    found = lint(doc)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    n_fail = sum(f["severity"] == "FAIL" for f in found)
    print(f"{n_fail} FAIL, {len(found) - n_fail} REVIEW")
    return 1 if n_fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
