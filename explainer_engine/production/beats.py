"""Visual beats (VB rules, docs/STORY_ENGINE.md; the creator, 2026-10-19): something new happens on screen about every
1.5 s, tied to what the narrator says at that instant, and in dialogue the speaking face changes its expression about once
a second. How often the picture itself changes is BP-40 (pictures a minute, still limits by section; PV-24 RHYTHM); the
beats live between the cuts and count as changes there too. Every cadence number here is read from the sourced rules
(docs/SOURCED_RULES.md: VB-01 BP-36, VB-02 BP-37 with BP-33's flicker floor, VB-04 BP-38, VB-08 spacing BP-39, VB-10 BP-80,
VB-11 BP-81, VB-05/VB-07 BP-82) and each check takes its severity from its rule.

Beats are written WITH the words (stage 2b, agent ``beat-writer``), one list per line (``lines[].visual_beats``), each landing on
a phrase of its own line (``at``) plus an optional ``offset`` in seconds: never a clock time, the read decides (D-43).

Kinds and what draws them (all free and deterministic: a frame renders the same twice):

* ``text``      up to 4 words pop in small (``accents._text_layer``); ``label`` the same words on a tag with a leader line
                to a spot of the picture (``pos``)
* ``prop``      the object the line names: a cut-out PNG (``asset``) popped onto the frame, else a word sticker
* ``chart``     a small ``counter`` (counts up to the number) or ``bars`` (2-3 bars grow); always with a ``claim``
* ``highlight`` a hand-drawn ring drawn round a spot of the picture; ``symbol`` a drawn sign (? ! arrows cross check...)
* ``accent``    a camera ``punch`` / ``shake`` of ``production/accents.py`` (the beat only times it)
* ``expression`` the face of ``who`` changes: a push in on the face (the picture's ``speakers`` point), a drawn emotion
                mark beside it (vein, sparkles, sweat, ? ...) and, when ``cast.<id>.expressions`` has a cut-out for that
                expression, a face inset that swaps on every change

    lint(doc)                   static VB findings (reasons, words, numbers, faces in the cast)
    resolve(...)                timed beats (called by timing.time_script)
    check_timed(timed, doc)     cadence and render findings on a timed script (estimated or real read)
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path

from PIL import Image, ImageDraw

from explainer_engine.audio import cues as CUES
from explainer_engine.finish import bubbles as BUB
from explainer_engine.production import accents as ACC
from explainer_engine.production import script as S
from explainer_engine.standards import sourced_rules as SR

LEGACY = "production_script/1"  # beats optional (one VB-00 REVIEW); /2 makes every VB rule binding
SCENE_SCHEMA = "production_script/3"  # the 2026-10-19 rewrite: metronomes retired, cues opt-in and event-bound (D-58)
# VB-01 on /2 (BP-36): seconds between visual events while the narrator speaks (the metronome)
TARGET, GAP_OK, GAP_FAIL, MEAN_OK = (float(SR.T("BP-36", k)) for k in ("v2_target_s", "v2_gap_review_s", "v2_gap_fail_s",
                                                                         "v2_mean_max_s"))
# VB-01 on /3 (BP-36): pace follows new information; only real dead air blocks. Nested inside BP-40 (the whole video's still
# limits on the same events): in the hook window BP-40 is the stricter one, in the body this one is
GAP_OK_3, GAP_FAIL_3 = float(SR.T("BP-36", "gap_review_s")), float(SR.T("BP-36", "gap_fail_s"))
# VB-02 (BP-37): seconds between expression changes on a dialogue line, /2 metronome and /3 reactions
FACE_TARGET, FACE_OK, FACE_FAIL = (float(SR.T("BP-37", k)) for k in ("v2_target_s", "v2_gap_review_s", "v2_gap_fail_s"))
FACE_OK_3, FACE_FAIL_3 = float(SR.T("BP-37", "gap_review_s")), float(SR.T("BP-37", "gap_fail_s"))
FACE_PER_LINE = int(SR.T("BP-37", "changes_per_line_min"))  # VB-02: no quota since the creator's call of 2026-10-20 21:14
ANCHOR_WORDS = int(SR.T("BP-93", "anchor_content_words_min"))  # VB-12: a beat is new information only on a narration word
FACE_FLICKER = float(SR.T("BP-33", "hold_min_s"))  # two changes of one face closer than BP-33's hold are flicker
CUE_EVENTS = ("reveal", "impact", "transition", "build", "diegetic", "take", "place")  # VB-08 on /3: a cue names its story event
CUE_REPEAT_WINDOW, CUE_REPEAT_FAIL = float(SR.T("BP-80", "window_s")), int(SR.T("BP-80", "fail_count"))  # VB-10
CUE_PER_MIN_OK, CUE_PER_MIN_FAIL = float(SR.T("BP-81", "per_min_review")), float(SR.T("BP-81", "per_min_fail"))  # VB-11
CUE_BURST, CUE_BURST_WINDOW = int(SR.T("BP-81", "burst_max")), float(SR.T("BP-81", "burst_window_s"))  # VB-11 bursts
CUE_DENSITY_FROM = float(SR.T("BP-81", "measured_from_s"))  # VB-11: a read shorter than this has no per-minute rate
EMPHASIS_CUES = set(SR.T("BP-81", "emphasis_cues"))  # VB-11: at most EMPHASIS_PER_LINE per line on /3
EMPHASIS_PER_LINE = int(SR.T("BP-81", "emphasis_per_line_max"))
MAX_WORDS = int(SR.T("BP-38", "max_words"))  # VB-04: words on screen in one beat (MO-05 reads the same cap)
BARS = tuple(int(x) for x in SR.T("BP-38", "bars"))  # VB-04: bars in a bars chart
MAX_SAME_RUN, MAX_WORD_SHARE = int(SR.T("BP-82", "same_kind_run_max")), float(SR.T("BP-82", "word_share_max"))  # VB-05
WORD_SHARE_FROM = int(SR.T("BP-82", "word_share_from_beats"))
MAX_OVERLAYS = int(SR.T("BP-82", "overlays_max"))  # VB-07: beat overlays on screen at once
HOLD = {"prop": 2.0, "symbol": 1.2, "highlight": 1.3, "chart": 2.6}
PICTURE_BOUND = {"label", "highlight", "expression"}  # they point into the picture, so they end with their shot
EXPR_TAIL = 0.3  # an expression stays this long after its line's last word
EXPRESSIONS = ("neutral", "curious", "surprised", "joyful", "amused", "smug", "confused", "doubtful", "worried", "scared",
               "angry", "sad", "determined", "deadpan")
TAKES = {"surprised", "scared", "angry", "joyful"}  # VB-08: the only expression changes that may carry a cue (one a line)
CUE_COVER = float(SR.T("BP-39", "cover_s"))  # a cue within this of an effect, or under a playing effect, doubles it
CUE_MIN_GAP = float(SR.T("BP-39", "min_gap_s"))  # two cues closer than this stack into one noise
TAKE_CUES = int(SR.T("BP-39", "take_cues_per_line_max"))  # cued expression changes on one dialogue line
OVERLAY = {"text", "label", "prop", "chart", "highlight", "symbol"}
FACE_HOLD, FACE_POP, FACE_EASE, POP_S = 0.10, 0.04, 0.25, 0.18
FACE_GLIDE_S = 0.6  # engineering: the face lean moves its pivot to the next speaker over this (a switch jumped, CC-06)
TEXT_SCALE, MARK_R = 1.15, 0.075  # beat words about 0.09 of the frame height; emotion mark radius (share of the height)
DEFAULT_POS = {"text": (0.5, 0.16), "label": (0.5, 0.5), "prop": (0.8, 0.3), "chart": (0.8, 0.24), "symbol": (0.86, 0.2)}
_PALETTE = Path(__file__).resolve().parents[1] / "design" / "palette.json"
_STOP = set("""a an the and or but so of to in on at for with by from into than then that this these those it its is are was
were be been has have had do does did not no as if when while who what where why how one all any each every some more most
very just only also here there their them they he she his her him we our you your i me my out up down off now still yet""".split())


def _rgb(name: str) -> tuple[int, int, int]:
    h = json.loads(_PALETTE.read_text(encoding="utf-8"))["tokens"][name]["hex"].lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


INK, PAPER, CORAL, TEAL, BLUE, GREEN, RED, AMBER = (_rgb(n) for n in (
    "ink", "paper", "answer_coral", "mechanism_teal", "support_blue", "true_green", "false_red", "uncertain_amber"))


def binding(doc: dict) -> bool:
    return doc.get("schema") != LEGACY


def scene_rules(doc: dict) -> bool:
    """True on a /3 script: silence is the default and a cue must name its story event (VB-08 inverted, VB-10, VB-11)."""
    return doc.get("schema") == SCENE_SCHEMA


def _sev(doc: dict, fail: bool, bp: str | None = None) -> str:
    """The severity of a hard case: REVIEW on a legacy /1 script, else the rule's own severity in the registry (``bp``: a
    house rule FAILs, a hypothesis never does), or FAIL for a structural check that has no number of its own."""
    if not (fail and binding(doc)):
        return "REVIEW"
    return SR.rule(bp).get("severity", "REVIEW") if bp else "FAIL"


_WORDS = re.compile(r"[a-z0-9']+")


def _content(text: str) -> set[str]:
    return {w.strip("'") for w in _WORDS.findall(str(text).lower())} - _STOP - {""}


def anchored(beat: dict, line: dict) -> bool:
    """BP-93 (VB-12, RX-12): a beat is tied to a narration word when its line is the narrator's (not a hero's) and its
    ``at`` holds at least ANCHOR_WORDS content word (not only "the", "of", "them"...). What it shows is VB-03's check."""
    if line.get("speaker"):
        return False
    return len(_content(beat.get("at", ""))) >= ANCHOR_WORDS


def counts_as_new(item: dict) -> bool:
    """BP-36 / BP-40 count a visual beat (or an accent a beat made) as a change only when it is tied to a narration word
    (BP-93); a timed file written before the rule carries no flag and counts as before."""
    return item.get("anchored", True)


def is_short(doc: dict) -> bool:
    """A Short's script (``short_doc``): its pace is BP-45's, so VB-01's narration cadence does not run on it."""
    return bool(doc.get("short"))


def _f(out, rule, sev, where, detail):
    out.append({"rule": "PV-44 " + rule, "severity": sev, "where": where, "detail": detail})


def _stems(text: str) -> set[str]:
    return {w[:5] for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 2 and w not in _STOP}


def has_beats(doc: dict) -> bool:
    return any(ln.get("visual_beats") for seg in doc["segments"] for ln in seg["lines"])


SHORT_PUSH = 1.07  # a Short's shot pushes in from 1.0 to this over its length (production/shorts.py)


def has_short_beats(doc: dict) -> bool:
    return any(ln.get("visual_beats") for sh in doc.get("shorts", []) for ln in sh["lines"])


def short_doc(doc: dict, short: dict) -> dict:
    """SS-09: a Short as a script of its own (one segment named after the Short, its lines, its shots on the video's
    pictures), so the VB lint, the timing and the cadence check run on it unchanged and report "SH03 line 2"."""
    pics, _ = S.pictures(doc)
    shots = [{"at": x["at"], "picture": x["picture"], "type": "A", "crop_x": x["crop_x"], "zoom": x.get("zoom", 1.0),
              "motion": {"kind": "push", "z0": 1.0, "z1": SHORT_PUSH}} for x in short["shots"]]
    return {"schema": doc.get("schema"), "short": short["id"], "episode": doc["episode"], "voice": doc["voice"], "cast": doc.get("cast", {}),
            "library": {k: {kk: vv for kk, vv in v.items() if kk not in ("id", "source", "first_use", "uses")}
                        for k, v in pics.items()},
            "segments": [{"id": short["id"], "beat": "short", "light_beat": 1, "lines": short["lines"], "shots": shots}]}


def payload(b: dict) -> str:
    return " ".join([b.get("text", ""), b.get("thing", ""), " ".join(b.get("labels", [])), b.get("unit", "")]).strip()


def lint(doc: dict) -> list[dict]:
    """Static VB findings: every beat has a reason and lands on its own line (VB-03), few words and no number without a
    claim (VB-04), an expression belongs to a hero of the cast (VB-06). Cadence needs times: ``check_timed``."""
    out: list[dict] = []
    if not has_beats(doc):
        if not binding(doc):
            _f(out, "VB-00", "REVIEW", "script", "a production_script/1 without visual beats: a new episode is written as "
               "production_script/2 with lines[].visual_beats (stage 2b, beat-writer)")
        else:
            _f(out, "VB-01", "FAIL", "script", "no visual beats at all: every line carries its beats (stage 2b, beat-writer)")
        return out
    toks = S.tokens(doc)
    for si, seg in enumerate(doc["segments"]):
        for li, line in enumerate(seg["lines"]):
            idx = [i for i, t in enumerate(toks) if t["seg"] == si and t["line"] == li]
            lo, hi = idx[0], idx[-1] + 1
            here = _stems(line["text"])
            near = set(here)
            for nb in (li - 1, li + 1):
                if 0 <= nb < len(seg["lines"]):
                    near |= _stems(seg["lines"][nb]["text"])
            cur = lo
            for bi, b in enumerate(line.get("visual_beats", [])):
                where = f"{seg['id']} line {li + 1} beat {bi + 1}"
                j = S.find_phrase(toks, b["at"], cur, hi)
                if j is None:
                    _f(out, "VB-03", _sev(doc, True), where, f"phrase {b['at']!r} is not in this line after the beat before: a "
                       "beat lands on the words said at that instant")
                else:
                    cur = j
                if len(b.get("why", "").split()) < 3:
                    _f(out, "VB-03", _sev(doc, True), where, "no reason: 'why' says in a few words what in the line this shows")
                words = payload(b)
                if words and not (_stems(words) & near) and not (_stems(b.get("why", "")) & here):
                    _f(out, "VB-03", "REVIEW", where, f"{words!r} shares no word with this line or its neighbours: is it what the "
                       "narrator says here?")
                elif not words and not (_stems(b.get("why", "")) & here):
                    _f(out, "VB-03", "REVIEW", where, "the reason names nothing of this line: quote the word the beat shows")
                if scene_rules(doc) and not anchored(b, line) and not (b["kind"] == "expression" and line.get("speaker")):
                    _f(out, "VB-12", SR.rule("BP-93").get("severity", "REVIEW"), where, f"{b['kind']} beat on {b['at']!r} is "
                       "not tied to a narration word (it sits on a hero's line, or its phrase has no content word): it does "
                       "not count as something new (BP-93); keep it only if the story needs it")
                if b["kind"] in ("text", "label") and len(b["text"].split()) > MAX_WORDS:
                    _f(out, "VB-04", _sev(doc, True, "BP-38"), where, f"{len(b['text'].split())} words on screen; at most {MAX_WORDS}")
                shows_number = re.search(r"\d", words) or b["kind"] == "chart"
                if shows_number and not (b.get("claim") or line.get("claims")):
                    _f(out, "VB-04", _sev(doc, True), where, "a number on screen without a claim id (invariant 5): put the claim "
                       "on the beat or its line")
                if b["kind"] == "chart" and b.get("chart") == "bars" and not BARS[0] <= len(b["values"]) <= BARS[1]:
                    _f(out, "VB-04", _sev(doc, True, "BP-38"), where, f"bars need {BARS[0]}-{BARS[1]} values")
                if b["kind"] == "expression":
                    who = b.get("who") or line.get("speaker")
                    if not who:
                        _f(out, "VB-06", _sev(doc, True), where, "an expression on a narrator line needs 'who' (a hero of the cast)")
                    elif who not in doc.get("cast", {}):
                        _f(out, "VB-06", _sev(doc, True), where, f"{who!r} is not in the cast")
                cue = b.get("cue")
                if scene_rules(doc):
                    # /3: silence is the default; a cue is opt-in and names the story event it marks (VB-08 inverted)
                    if cue and cue["sound"] != CUES.NONE:
                        if cue.get("event") not in CUE_EVENTS:
                            _f(out, "VB-08", "FAIL", where, f"cue {cue['sound']!r} names no story event: a sound exists only "
                               f"for an event ({', '.join(CUE_EVENTS)}); a plain beat stays silent")
                        if b["kind"] == "expression" and b["expression"] not in TAKES:
                            _f(out, "VB-08", "REVIEW", where, f"a cue on a quiet expression ({b['expression']}): only a big "
                               f"take ({', '.join(sorted(TAKES))}) may sound, the voice carries the rest")
                        if not CUES.MIN_MS <= CUES.length_ms(cue["sound"], cue.get("max_ms")) <= CUES.MAX_MS:  # BP-64
                            _f(out, "VB-08", _sev(doc, True, "BP-64"), where, f"cue {cue['sound']!r} lasts "
                               f"{CUES.length_ms(cue['sound'], cue.get('max_ms')):.0f} ms; a cue is {CUES.MIN_MS}-{CUES.MAX_MS} ms")
                elif cue is None:
                    _f(out, "VB-08", _sev(doc, True), where, "no cue: every beat names its short sound (audio/cues.py) or "
                       "'none' with a reason")
                elif cue["sound"] == CUES.NONE and not cue.get("why"):
                    _f(out, "VB-08", _sev(doc, True), where, "cue 'none' without a reason")
                elif b["kind"] == "expression" and cue["sound"] != CUES.NONE and b["expression"] not in TAKES:
                    _f(out, "VB-08", "REVIEW", where, f"a cue on a quiet expression ({b['expression']}): only a big take "
                       f"({', '.join(sorted(TAKES))}) may sound, the voice carries the rest")
                elif cue["sound"] != CUES.NONE and not CUES.MIN_MS <= CUES.length_ms(cue["sound"], cue.get("max_ms")) <= CUES.MAX_MS:
                    _f(out, "VB-08", _sev(doc, True, "BP-64"), where, f"cue {cue['sound']!r} lasts {CUES.length_ms(cue['sound'], cue.get('max_ms')):.0f} "
                       f"ms; a cue is {CUES.MIN_MS}-{CUES.MAX_MS} ms")
                if b["kind"] == "prop" and not b.get("asset"):
                    _f(out, "VB-06", "REVIEW", where, f"prop {b['thing']!r} has no cut-out (asset): it is drawn as a word sticker")
    return out


def resolve(doc: dict, toks: list[dict], words: list[dict], wi, shots: list[dict], fps: int, duration: float,
            problems: list[dict]) -> list[dict]:
    """Timed beats: start = the phrase's first word + offset, the shot it lands in, an end per kind (``HOLD``, a text's
    reading time, an expression until the same face changes again or its line ends). ``accent`` beats are added to their
    shot's accents (``accents.resolve`` form) so the camera code draws them."""
    out: list[dict] = []
    starts = [s["start"] for s in shots]
    for si, seg in enumerate(doc["segments"]):
        for li, line in enumerate(seg["lines"]):
            if not line.get("visual_beats"):
                continue
            idx = [i for i, t in enumerate(toks) if t["seg"] == si and t["line"] == li]
            lo, hi = idx[0], idx[-1] + 1
            line_end = words[wi(idx[-1])]["e"]
            cur = lo
            last_j = None
            for bi, b in enumerate(line["visual_beats"]):
                j = S.find_phrase(toks, b["at"], cur, hi)
                if j is None or wi(j) is None:
                    problems.append({"rule": "PV-44 VB-03", "severity": _sev(doc, True), "where": f"{seg['id']} line {li + 1} "
                                     f"beat {bi + 1}", "detail": f"phrase {b['at']!r} not found in its line"})
                    continue
                cur = j
                st = round(min(max(0.0, words[wi(j)]["s"] + float(b.get("offset", 0.0))), duration), 3)
                if (out and j != last_j and out[-1]["segment"] == seg["id"] and out[-1]["line"] == li + 1
                        and out[-1]["start"] == st):
                    # the timing fallback gives unmatched words (numbers, acronyms) the next matched word's start, so
                    # beats on DIFFERENT words can land on one instant and their cues double; keep the first, report the
                    # rest (two beats written on the SAME word stay: the cue-spacing lint owns that authoring error)
                    problems.append({"rule": "PV-44 VB-03", "severity": "REVIEW", "where": f"{seg['id']} line {li + 1} beat "
                                     f"{bi + 1}", "detail": f"beat {b['at']!r} lands at the same instant ({st:.3f}s) as the beat "
                                     "before (collapsed word timing): kept the first beat, dropped this one"})
                    continue
                last_j = j
                k = max(0, sum(1 for x in starts if x <= st) - 1)
                item = dict(b, segment=seg["id"], line=li + 1, start=st, start_frame=int(round(st * fps)), shot=shots[k]["id"],
                            picture=shots[k]["picture"], line_end=round(line_end, 3), _shot_end=shots[k]["end"],
                            anchored=anchored(b, line) if scene_rules(doc) else True)  # BP-93 binds /3; /2 keeps its contract
                if line.get("speaker"):
                    item["speaker"] = line["speaker"]
                if b["kind"] == "expression":
                    item["who"] = b.get("who") or line.get("speaker")
                out.append(item)
    for k, b in enumerate(out):
        kind = b["kind"]
        if kind == "expression":
            nxt = next((x["start"] for x in out[k + 1:] if x["kind"] == "expression" and x["who"] == b["who"]), None)
            end = b["line_end"] + EXPR_TAIL
            if nxt is not None and nxt < end:
                end = nxt
        elif kind in ("text", "label"):
            end = b["start"] + ACC.text_hold(b["text"])
        elif kind == "accent":
            end = b["start"]
        else:
            end = b["start"] + HOLD[kind]
        if kind in PICTURE_BOUND:
            end = min(end, b["_shot_end"])
        b["end"] = round(max(b["start"], min(end, duration)), 3)
        b["end_frame"] = int(round(b["end"] * fps))
        b.pop("_shot_end")
    by_id = {s["id"]: s for s in shots}
    for b in out:
        sh = by_id[b["shot"]]
        sh["visual_beats"] = sh.get("visual_beats", 0) + 1
        if b["kind"] == "accent":
            sh["accents"].append({"kind": b["effect"], "start": b["start"], "start_frame": b["start_frame"],
                                  "strength": float(b.get("strength", 0.6)), "text": "", "pos": [0.5, 0.2], "beat": True,
                                  "anchored": b["anchored"]})
            sh["accents"].sort(key=lambda a: a["start"])
    return out


def cue_track(beats: list[dict], duration: float, fps: int) -> list[dict]:
    """VB-08: the cues of the timed beats (start on the beat's first frame, in sync with the change on screen)."""
    out = []
    for b in beats:
        cue = b.get("cue") or {}
        name = cue.get("sound", CUES.NONE)
        if name == CUES.NONE:
            continue
        st = b["start"]
        en = min(duration, st + CUES.length_ms(name, cue.get("max_ms")) / 1000)
        out.append({"sound": name, "start": st, "end": round(en, 3), "gain_db": float(cue.get("gain_db", CUES.DEFAULT_GAIN_DB)),
                    "max_ms": cue.get("max_ms"), "segment": b["segment"], "line": b["line"], "kind": b["kind"],
                    "start_frame": int(round(st * fps))})
    return out


def _cue_findings(timed: dict, doc: dict, beats: list[dict], out: list[dict]) -> None:
    from explainer_engine.audio import layers as L

    au = timed.get("audio", {})
    sfx, cues, music, beds = au.get("sfx", []), au.get("cues", []), au.get("music", []), au.get("beds", [])
    starts = [e["start"] for e in sfx]

    def covered(t: float) -> bool:
        return any(abs(x - t) <= CUE_COVER for x in starts) or any(e["start"] <= t < e["end"] for e in sfx)

    for b in beats:
        where = f"{b['segment']} line {b['line']}"
        name = (b.get("cue") or {}).get("sound", CUES.NONE)
        if name != CUES.NONE and covered(b["start"]):
            _f(out, "VB-08", _sev(doc, True, "BP-39"), where, f"cue {name!r} at {b['start']:.1f}s doubles a sound effect: the effect is "
               "this beat's sound, set the cue to 'none'")
        elif name == CUES.NONE and b["kind"] not in ("expression",) and not covered(b["start"]) and not scene_rules(doc):
            _f(out, "VB-08", _sev(doc, True), where, f"a {b['kind']} beat at {b['start']:.1f}s makes no sound: every addition "
               "gets a short cue unless an effect already sounds there")
    for a, c in zip(cues, cues[1:]):
        if c["start"] - a["start"] < CUE_MIN_GAP:
            _f(out, "VB-08", _sev(doc, True, "BP-39"), f"{c['segment']} line {c['line']}", f"two cues {c['start'] - a['start']:.2f} s apart "
               f"stack into noise (at least {CUE_MIN_GAP} s)")
    for c in cues:
        t = c["start"] + 1e-3
        n = 1 + min(1, L._active(music, t)) + min(1, L._active(beds, t)) + L._active(sfx, t) + L._active(cues, t)
        if n > L.MAX_LAYERS:
            _f(out, "VB-08", _sev(doc, True), f"{c['segment']} line {c['line']}", f"{n} layers at {c['start']:.1f}s with the cue "
               f"(at most {L.MAX_LAYERS} in all, BP-56: voice, music, bed and effects or cues)")
    cued: dict = {}
    for b in beats:
        if b["kind"] == "expression" and (b.get("cue") or {}).get("sound", CUES.NONE) != CUES.NONE:
            cued.setdefault((b["segment"], b["line"]), []).append(b)
    for (sid, ln), bs in cued.items():
        if len(bs) > TAKE_CUES:
            _f(out, "VB-08", _sev(doc, True, "BP-39"), f"{sid} line {ln}", f"{len(bs)} expression cues on one dialogue line: at "
               f"most {TAKE_CUES} (the big take), the rest of the face changes are silent")
    if scene_rules(doc):
        # VB-10 a repeated sound stops meaning anything; VB-11 density: silence is the baseline a cue stands out of (D-58)
        last_name = None
        recent: dict = {}
        for c in cues:
            where = f"{c['segment']} line {c['line']}"
            times = [t for t in recent.get(c["sound"], []) if c["start"] - t <= CUE_REPEAT_WINDOW]
            times.append(c["start"])
            recent[c["sound"]] = times
            if len(times) == CUE_REPEAT_FAIL:
                _f(out, "VB-10", _sev(doc, True, "BP-80"), where, f"{c['sound']!r} sounds {len(times)} times inside {CUE_REPEAT_WINDOW:.0f} s: a "
                   "repeated cue is a tic, not a mark; vary the sound or keep only the one on the turn")
            elif c["sound"] == last_name and len(times) < CUE_REPEAT_FAIL:
                _f(out, "VB-10", "REVIEW", where, f"{c['sound']!r} twice in a row: two neighbouring story events should not "
                   "sound the same")
            last_name = c["sound"]
        dur = float(timed.get("duration") or 0.0)
        if dur >= CUE_DENSITY_FROM and cues:
            per_min = len(cues) / dur * 60
            if per_min > CUE_PER_MIN_FAIL:
                _f(out, "VB-11", _sev(doc, True, "BP-81"), "audio", f"{per_min:.0f} cues a minute (cap {CUE_PER_MIN_FAIL:.0f}): a sound exists "
                   "only for a story event; a track this dense marks nothing")
            elif per_min > CUE_PER_MIN_OK:
                _f(out, "VB-11", "REVIEW", "audio", f"{per_min:.0f} cues a minute (aim under {CUE_PER_MIN_OK:.0f})")
        ts = [c["start"] for c in cues]
        burst_flagged = set()
        for c in cues:
            n = sum(1 for t in ts if c["start"] - CUE_BURST_WINDOW < t <= c["start"])
            if n > CUE_BURST and (c["segment"], c["line"]) not in burst_flagged:
                burst_flagged.add((c["segment"], c["line"]))
                _f(out, "VB-11", "REVIEW", f"{c['segment']} line {c['line']}", f"{n} cues inside {CUE_BURST_WINDOW:.0f} s around "
                   f"{c['start']:.1f}s "
                   f"(at most {CUE_BURST}): the moments stop standing out")
        emph: dict = {}
        for c in cues:
            if c["sound"] in EMPHASIS_CUES:
                emph.setdefault((c["segment"], c["line"]), []).append(c["sound"])
        for (sid, ln), names in emph.items():
            if len(names) > EMPHASIS_PER_LINE:
                _f(out, "VB-11", _sev(doc, True, "BP-81"), f"{sid} line {ln}", f"{len(names)} emphasis cues ({', '.join(names)}) "
                   f"on one line: one line gets at most {EMPHASIS_PER_LINE} emphasis, the voice carries the rest")


# --- cadence on a timed script -------------------------------------------------------------------------------------------

def _windows(timed: dict, dialogue: bool) -> list[dict]:
    return [ln for ln in timed.get("lines", []) if bool(ln.get("speaker")) == dialogue and ln["end"] > ln["start"]]


def check_timed(timed: dict, doc: dict) -> list[dict]:
    """VB-01 (narration cadence), VB-02 (expression cadence in dialogue), VB-05 (variety), VB-06 (a face to change),
    VB-07 (overlays at once) on the read's times."""
    from explainer_engine.edit import motion_lint

    out: list[dict] = []
    beats = timed.get("visual_beats", [])
    if not has_beats(doc) and not binding(doc):
        return out
    times = sorted(t for t, _ in motion_lint.events(timed))
    pts = [0.0] + times + [timed["duration"]]
    narr = _windows(timed, False)
    gap_ok, gap_fail = (GAP_OK_3, GAP_FAIL_3) if scene_rules(doc) else (GAP_OK, GAP_FAIL)
    if is_short(doc):  # BP-45 owns a Short's pace (PV-34): the 1.5 s metronome is not a Shorts rule
        pts = []
    for a, b in zip(pts, pts[1:]):
        gap = b - a
        if gap <= gap_ok:
            continue
        ln = next((w for w in narr if w["start"] < b and w["end"] > a), None)
        if ln is None:
            continue
        sev = _sev(doc, True, "BP-36") if gap > gap_fail else "REVIEW"
        if scene_rules(doc):
            # /3: the metronome is retired; pace follows new information (D-58), only real dead air is flagged
            _f(out, "VB-01", sev, f"{ln['segment']} line {ln['line']} {a:.1f}s",
               f"{gap:.1f} s with nothing new on screen while the narrator speaks: a hold is fine while the line carries "
               f"new information, this long is dead air (REVIEW over {gap_ok:.0f} s, FAIL over {gap_fail:.0f} s)")
        else:
            _f(out, "VB-01", sev, f"{ln['segment']} line {ln['line']} {a:.1f}s",
               f"{gap:.1f} s with nothing new on screen while the narrator speaks; a beat about every {TARGET} s "
               f"(REVIEW over {GAP_OK} s, FAIL over {GAP_FAIL} s)")
    if not scene_rules(doc) and not is_short(doc):
        by_seg: dict = {}
        for w in narr:
            s = by_seg.setdefault(w["segment"], [0.0, 0])
            s[0] += w["end"] - w["start"]
            s[1] += sum(1 for t in times if w["start"] <= t < w["end"])
        for sid, (secs, n) in by_seg.items():
            if secs >= 6 and (n == 0 or secs / n > MEAN_OK):
                _f(out, "VB-01", "REVIEW", sid, f"one visual event every {secs / max(n, 1):.1f} s of narration on average (target "
                   f"{TARGET} s, at most {MEAN_OK} s)")
    expr = [b for b in beats if b["kind"] == "expression"]
    face_ok, face_fail = (FACE_OK_3, FACE_FAIL_3) if scene_rules(doc) else (FACE_OK, FACE_FAIL)
    for ln in _windows(timed, True):
        last: dict = {}
        last_t: dict = {}
        for b in expr:
            if b["start"] < ln["start"] - 0.05:
                last[b["who"]] = b["expression"]
        changes = []
        for b in expr:
            if ln["start"] - 0.05 <= b["start"] < ln["end"]:
                if last.get(b["who"]) == b["expression"]:
                    _f(out, "VB-02", "REVIEW", f"{ln['segment']} line {ln['line']}", f"{b['who']} stays {b['expression']}: "
                       "an expression beat is a change")
                    continue
                if scene_rules(doc) and b["who"] in last_t and b["start"] - last_t[b["who"]] < FACE_FLICKER:
                    _f(out, "VB-02", "REVIEW", f"{ln['segment']} line {ln['line']}", f"{b['who']}'s face changes twice within "
                       f"{b['start'] - last_t[b['who']]:.1f} s: under {FACE_FLICKER} s reads as flicker; one reaction per thought")
                last[b["who"]] = b["expression"]
                last_t[b["who"]] = b["start"]
                changes.append(b["start"])
        where = f"{ln['segment']} line {ln['line']}"
        if not changes:
            if len(changes) >= FACE_PER_LINE:  # BP-37: no quota per line (0): a reaction is a choice, not a rule
                continue
            if scene_rules(doc):
                _f(out, "VB-02", _sev(doc, True, "BP-37"), where, f"a dialogue line ({ln['duration']:.1f} s) with no expression change: "
                   "the listener's face is where the line lands (Kuleshov); at least one reaction on every spoken line")
            else:
                _f(out, "VB-02", _sev(doc, True, "BP-37"), where, f"a dialogue line ({ln['duration']:.1f} s) with no expression change: the "
                   f"face carries the line, about one change every {FACE_TARGET:.0f} s")
            continue
        p = [ln["start"]] + changes + [ln["end"]]
        worst = max(y - x for x, y in zip(p, p[1:]))
        if scene_rules(doc):
            if worst > face_fail:
                _f(out, "VB-02", _sev(doc, True, "BP-37"), where, f"{worst:.1f} s without an expression change in dialogue (FAIL over "
                   f"{face_fail:.0f} s): a listener reacts when a line lands, not on a clock")
            elif worst > face_ok:
                _f(out, "VB-02", "REVIEW", where, f"{worst:.1f} s without an expression change (REVIEW over {face_ok:.0f} s)")
        elif worst > FACE_FAIL:
            _f(out, "VB-02", _sev(doc, True, "BP-37"), where, f"{worst:.1f} s without an expression change in dialogue (FAIL over "
               f"{FACE_FAIL} s, target {FACE_TARGET:.0f} s)")
        elif worst > FACE_OK:
            _f(out, "VB-02", "REVIEW", where, f"{worst:.1f} s without an expression change (target {FACE_TARGET:.0f} s, "
               f"REVIEW over {FACE_OK} s)")
    pics = timed.get("pictures", {})
    for b in expr:
        hero = doc.get("cast", {}).get(b["who"] or "", {})
        if not hero:
            continue
        face = (pics.get(b["picture"], {}).get("speakers") or {}).get(b["who"])
        from explainer_engine.production import faces as FACES
        sprite = FACES.file_name(b["who"], hero, b["expression"])
        if face is None and not sprite:
            _f(out, "VB-06", _sev(doc, True), f"{b['segment']} line {b['line']}", f"{b['who']}'s face is not in picture "
               f"{b['picture']!r} (no speakers point) and {b['expression']!r} is in neither cast.{b['who']}.face_sheet nor "
               f"cast.{b['who']}.expressions: "
               "the render has no face to change")
    _cue_findings(timed, doc, beats, out)
    by_seg_kinds: dict = {}
    for b in beats:
        if b["kind"] != "expression":
            by_seg_kinds.setdefault(b["segment"], []).append(b["kind"])
    for sid, kinds in by_seg_kinds.items():
        run = 1
        for x, y in zip(kinds, kinds[1:]):
            run = run + 1 if x == y else 1
            if run == MAX_SAME_RUN + 1:
                _f(out, "VB-05", "REVIEW", sid, f"{run} {y} beats in a row: vary the kind (text, prop, chart, highlight, symbol, "
                   "accent)")
        if len(kinds) >= WORD_SHARE_FROM and sum(k in ("text", "label") for k in kinds) / len(kinds) > MAX_WORD_SHARE:
            _f(out, "VB-05", "REVIEW", sid, f"{sum(k in ('text', 'label') for k in kinds)} of {len(kinds)} beats are words: "
               f"at most {MAX_WORD_SHARE:.0%}; show the thing instead")
    ov = sorted((b["start"], b["end"], b["segment"]) for b in beats if b["kind"] in OVERLAY)
    flagged = set()
    for i, (s, _, sid) in enumerate(ov):
        n = sum(1 for s2, e2, _ in ov[:i + 1] if e2 > s)
        if n > MAX_OVERLAYS and sid not in flagged:
            flagged.add(sid)
            _f(out, "VB-07", "REVIEW", sid, f"{n} beat overlays on screen at once at {s:.1f}s (at most {MAX_OVERLAYS})")
    return out


def measure(timed: dict) -> dict:
    """Numbers for the review bundle: beats by kind, mean narration gap, expression changes a second of dialogue."""
    from explainer_engine.edit import motion_lint

    beats = timed.get("visual_beats", [])
    times = sorted(t for t, _ in motion_lint.events(timed))
    narr = _windows(timed, False)
    secs = sum(w["end"] - w["start"] for w in narr)
    n = sum(1 for w in narr for t in times if w["start"] <= t < w["end"])
    dial = _windows(timed, True)
    dsecs = sum(w["end"] - w["start"] for w in dial)
    ex = sum(1 for b in beats if b["kind"] == "expression")
    kinds: dict = {}
    for b in beats:
        kinds[b["kind"]] = kinds.get(b["kind"], 0) + 1
    return {"beats": len(beats), "kinds": kinds, "narration_gap_mean": round(secs / n, 2) if n else None,
            "expressions_per_dialogue_second": round(ex / dsecs, 2) if dsecs else None}


# --- render ------------------------------------------------------------------------------------------------------------

def _ease(u: float) -> float:
    u = min(max(u, 0.0), 1.0)
    return 1 - (1 - u) ** 3


def _bump(u: float) -> float:
    return math.sin(math.pi * min(max(u, 0.0), 1.0))


def faces(shot_beats: list[dict], pics: dict) -> list[dict]:
    """The expression beats of one shot that have a face point in the shot's picture."""
    out = []
    for b in shot_beats:
        if b["kind"] == "expression":
            p = (pics.get(b["picture"], {}).get("speakers") or {}).get(b["who"])
            if p is not None:
                out.append(dict(b, face=p))
    return out


def face_camera(box, W: int, H: int, face_beats: list[dict], f: int, fps: int):
    """ED-02-safe face focus: while a shot's faces talk the crop leans in on the face (eased in and out over the span of
    the shot's expressions) and every expression change adds a short pop toward it."""
    if not face_beats:
        return box
    span0 = min(b["start_frame"] for b in face_beats)
    span1 = max(b["end_frame"] for b in face_beats)
    if not span0 <= f < span1 + FACE_EASE * fps:
        return box
    hold = FACE_HOLD * min(_ease((f - span0) / (FACE_EASE * fps)), _ease((span1 + FACE_EASE * fps - f) / (FACE_EASE * fps)))
    cur = [b for b in face_beats if b["start_frame"] <= f]
    b = cur[-1] if cur else face_beats[0]
    pop = FACE_POP * _bump((f - b["start_frame"]) / (POP_S * fps)) if cur else 0.0
    z = 1 + hold + pop
    fx, fy = b["face"]
    if len(cur) > 1 and cur[-2]["face"] != b["face"]:  # the lean glides to the next face; a switched pivot jumped (CC-06)
        u = min(max((f - b["start_frame"]) / (FACE_GLIDE_S * fps), 0.0), 1.0)
        m = u * u * (3 - 2 * u)  # smoothstep: no speed step where the glide starts or ends
        fx, fy = cur[-2]["face"][0] + (fx - cur[-2]["face"][0]) * m, cur[-2]["face"][1] + (fy - cur[-2]["face"][1]) * m
    px, py = fx * W, fy * H
    x0, y0, x1, y1 = box
    nx0, ny0 = px + (x0 - px) / z, py + (y0 - py) / z
    nx1, ny1 = px + (x1 - px) / z, py + (y1 - py) / z
    dx = max(0.0, -nx0) - max(0.0, nx1 - W)
    dy = max(0.0, -ny0) - max(0.0, ny1 - H)
    return (nx0 + dx, ny0 + dy, nx1 + dx, ny1 + dy)


def _to_frame(pt, box, W, H, OW, OH):
    x0, y0, x1, y1 = box
    return ((pt[0] * W - x0) / (x1 - x0) * OW, (pt[1] * H - y0) / (y1 - y0) * OH)


def _alpha(t: float, life: float) -> float:
    return max(0.0, min(_ease(t / 0.12), _ease((life - t) / 0.15)))


def _scale(t: float) -> float:
    u = t / 0.25
    return 0.6 + 0.52 * _ease(u) if u < 1 else 1.12 - 0.12 * min(1.0, (t - 0.25) / 0.1)


def _font(size: float, shout: bool = False):
    return ACC._font(int(size), BUB.SHOUT_FONT if shout else BUB.FONT)


def _star(d, cx, cy, r, col):
    pts = []
    for i in range(8):
        a = math.pi / 4 * i - math.pi / 2
        rr = r if i % 2 == 0 else r * 0.32
        pts.append((cx + rr * math.cos(a), cy + rr * math.sin(a)))
    d.polygon(pts, fill=col)


def _drop(d, cx, cy, r, col):
    d.ellipse([cx - r * 0.6, cy - r * 0.1, cx + r * 0.6, cy + r * 1.1], fill=col)
    d.polygon([(cx - r * 0.55, cy + r * 0.35), (cx, cy - r * 0.9), (cx + r * 0.55, cy + r * 0.35)], fill=col)


def _sign(d, ch: str, cx, cy, r, col, a):
    f = _font(r * 2.2, shout=True)
    d.text((cx, cy), ch, font=f, fill=col + (a,), anchor="mm", stroke_width=max(2, int(r / 6)), stroke_fill=INK + (a,))


class _Inked:
    """Draws every stroke twice, a dark ink line under the colour, so a mark reads on a light and a dark picture alike."""

    def __init__(self, d: ImageDraw.ImageDraw, a: int):
        self.d, self.a = d, a

    def line(self, pts, fill, width=1):
        self.d.line(pts, fill=INK + (self.a,), width=width + 4, joint="curve")
        self.d.line(pts, fill=fill, width=width, joint="curve")

    def arc(self, box, start, end, fill, width=1):
        self.d.arc(box, start, end, fill=INK + (self.a,), width=width + 4)
        self.d.arc(box, start, end, fill=fill, width=width)

    def polygon(self, pts, fill):
        self.d.polygon(pts, fill=fill, outline=INK + (self.a,), width=3)

    def ellipse(self, box, fill=None, outline=None, width=1):
        self.d.ellipse(box, fill=fill, outline=outline or INK + (self.a,), width=max(width, 3))

    def text(self, *args, **kw):
        self.d.text(*args, **kw)


def emotion_mark(d: ImageDraw.ImageDraw, expression: str, cx: float, cy: float, r: float, a: int) -> None:
    """The drawn emotion mark beside a face (comic emanata): one per expression, none for neutral."""
    d = _Inked(d, a)
    w = max(2, int(r / 5))
    if expression == "angry":
        for sx, sy in ((-1, -1), (1, -1), (-1, 1), (1, 1)):
            box = [cx + sx * r * 0.3 - r * 0.7, cy + sy * r * 0.3 - r * 0.7, cx + sx * r * 0.3 + r * 0.7,
                   cy + sy * r * 0.3 + r * 0.7]
            start = {(-1, -1): 0, (1, -1): 90, (1, 1): 180, (-1, 1): 270}[(sx, sy)]
            d.arc(box, start, start + 90, fill=RED + (a,), width=w + 1)
    elif expression in ("joyful", "smug", "amused"):
        spots = [(0, 0, 1.0), (-0.9, 0.6, 0.55), (0.8, 0.8, 0.45)] if expression == "joyful" else [(0, 0, 0.8)]
        for ox, oy, k in spots:
            _star(d, cx + ox * r, cy + oy * r, r * k, AMBER + (a,))
        if expression == "amused":
            for k in (0.6, 1.0):
                d.arc([cx - r * k, cy + r * 0.2, cx + r * k, cy + r * (0.2 + k)], 200, 340, fill=INK + (a,), width=w)
    elif expression == "surprised":
        _sign(d, "!", cx, cy, r, PAPER, a)
        for i in range(5):
            ang = -math.pi / 2 + (i - 2) * 0.45
            d.line([(cx + math.cos(ang) * r * 1.1, cy + math.sin(ang) * r * 1.1),
                    (cx + math.cos(ang) * r * 1.6, cy + math.sin(ang) * r * 1.6)], fill=PAPER + (a,), width=w)
    elif expression == "curious":
        _sign(d, "?", cx, cy, r, TEAL, a)
    elif expression == "doubtful":
        for i in (-1, 0, 1):
            d.ellipse([cx + i * r * 0.6 - r * 0.16, cy - r * 0.16, cx + i * r * 0.6 + r * 0.16, cy + r * 0.16], fill=PAPER + (a,),
                      outline=INK + (a,), width=max(1, w // 2))
    elif expression == "confused":
        pts = [(cx + math.cos(u) * r * u / 12, cy + math.sin(u) * r * u / 12) for u in [i * 0.3 for i in range(40)]]
        d.line(pts, fill=PAPER + (a,), width=w)
    elif expression in ("worried", "scared"):
        _drop(d, cx, cy, r * 0.7, BLUE + (a,))
        if expression == "scared":
            for i in (-1, 1):
                x = cx + i * r * 1.1
                d.line([(x, cy - r * 0.8), (x - r * 0.15, cy - r * 0.3), (x + r * 0.15, cy + r * 0.2), (x, cy + r * 0.7)],
                       fill=PAPER + (a,), width=w)
    elif expression == "sad":
        for i in (-1, 1):
            _drop(d, cx + i * r * 0.45, cy + r * 0.3 * (i + 1), r * 0.4, BLUE + (a,))
    elif expression == "determined":
        for i in range(3):
            x = cx - r * 0.6 + i * r * 0.6
            d.line([(x, cy + r * 0.6), (x + r * 0.45, cy - r * 0.6)], fill=CORAL + (a,), width=w + 1)
    elif expression == "deadpan":
        d.line([(cx - r * 0.8, cy), (cx + r * 0.8, cy)], fill=PAPER + (a,), width=w + 1)


def _tag(d, text, x, y, size, a):
    f = _font(size)
    l, t, r, b = d.textbbox((x, y), text, font=f, anchor="mm")
    pad = size * 0.35
    d.rounded_rectangle([l - pad, t - pad, r + pad, b + pad], int(size * 0.4), fill=PAPER + (int(a * 0.94),),
                        outline=INK + (a,), width=max(2, int(size / 12)))
    d.text((x, y), text, font=f, fill=INK + (a,), anchor="mm")
    return l - pad, t - pad, r + pad, b + pad


def _symbol(d, sym, cx, cy, r, a):
    d = _Inked(d, a)
    w = max(3, int(r / 4))
    if sym in ("question", "exclaim"):
        _sign(d, "?" if sym == "question" else "!", cx, cy, r, AMBER, a)
    elif sym in ("arrow_up", "arrow_down"):
        s = -1 if sym == "arrow_up" else 1
        col = (GREEN if s < 0 else RED) + (a,)
        d.line([(cx, cy - s * r), (cx, cy + s * r * 0.6)], fill=col, width=w)
        d.polygon([(cx - r * 0.6, cy + s * r * 0.3), (cx + r * 0.6, cy + s * r * 0.3), (cx, cy + s * r * 1.1)], fill=col)
    elif sym == "cross":
        for s in (-1, 1):
            d.line([(cx - r * 0.8, cy - s * r * 0.8), (cx + r * 0.8, cy + s * r * 0.8)], fill=RED + (a,), width=w)
    elif sym == "check":
        d.line([(cx - r * 0.8, cy), (cx - r * 0.2, cy + r * 0.6), (cx + r * 0.9, cy - r * 0.7)], fill=GREEN + (a,), width=w)
    elif sym in ("plus", "equals"):
        _sign(d, "+" if sym == "plus" else "=", cx, cy, r, TEAL, a)
    elif sym == "clock":
        d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=PAPER + (a,), width=w)
        d.line([(cx, cy), (cx, cy - r * 0.7)], fill=PAPER + (a,), width=w)
        d.line([(cx, cy), (cx + r * 0.5, cy)], fill=PAPER + (a,), width=w)


def _chart(d, b, x, y, H, t, a):
    k = _ease((t - 0.1) / 0.8)
    vals = b["values"]
    if b["chart"] == "counter":
        v0, v1 = (vals[0], vals[-1]) if len(vals) > 1 else (0, vals[0])
        v = v0 + (v1 - v0) * k
        num = f"{v:,.0f}" if abs(v1) >= 10 or float(v1).is_integer() else f"{v:.1f}"
        label = (b.get("labels") or [""])[0]
        f = _font(H * 0.08, shout=True)
        l, tt, r, bb = d.textbbox((x, y), num + (" " + b["unit"] if b.get("unit") else ""), font=f, anchor="mm")
        d.rounded_rectangle([l - H * 0.025, tt - H * 0.03, r + H * 0.025, bb + H * (0.06 if label else 0.03)], int(H * 0.02),
                            fill=(34, 27, 22, int(a * 0.85)), outline=PAPER + (a,), width=max(2, H // 300))
        d.text((x, y), num + (" " + b["unit"] if b.get("unit") else ""), font=f, fill=AMBER + (a,), anchor="mm")
        if label:
            d.text((x, bb + H * 0.025), label, font=_font(H * 0.035), fill=PAPER + (a,), anchor="mm")
        return
    top = max(abs(v) for v in vals) or 1
    bw, bh = H * 0.07, H * 0.2
    x0 = x - (len(vals) * bw * 1.5) / 2
    d.rounded_rectangle([x0 - bw * 0.4, y - bh * 0.75, x0 + len(vals) * bw * 1.5 + bw * 0.1, y + bh * 0.45], int(H * 0.02),
                        fill=(34, 27, 22, int(a * 0.85)), outline=PAPER + (a,), width=max(2, H // 300))
    for i, v in enumerate(vals):
        h = bh * 0.8 * abs(v) / top * k
        bx = x0 + i * bw * 1.5
        d.rectangle([bx, y + bh * 0.25 - h, bx + bw, y + bh * 0.25], fill=(CORAL if i == len(vals) - 1 else TEAL) + (a,))
        lab = (b.get("labels") or [])[i] if i < len(b.get("labels") or []) else ""
        if lab:
            d.text((bx + bw / 2, y + bh * 0.33), lab, font=_font(H * 0.028), fill=PAPER + (a,), anchor="mt")


_SPRITES: dict = {}


def _sprite(path: Path | None):
    if path is None:
        return None
    if path not in _SPRITES:
        _SPRITES.clear() if len(_SPRITES) > 32 else None
        _SPRITES[path] = Image.open(path).convert("RGBA")
    return _SPRITES[path]


def find_file(name: str | None, dirs: list[Path]) -> Path | None:
    if not name:
        return None
    for d in list(dirs) + [Path(__file__).resolve().parents[2]]:
        p = Path(d) / name
        if p.exists():
            return p
    return None


def draw(frame: Image.Image, shot_beats: list[dict], f: int, fps: int, box, src_size: tuple[int, int], cast: dict,
         dirs: list[Path]) -> Image.Image:
    """Every beat of the shot active at frame ``f``, drawn on the finished frame (after accents and bubbles)."""
    OW, OH = frame.size
    U = min(OW, OH)  # mark size: the short side, so a 9:16 Short draws marks as big as the video does, not 1.8x
    W, H = src_size
    active = [b for b in shot_beats if b["kind"] != "accent" and b["start_frame"] <= f < max(b["end_frame"], b["start_frame"] + 1)]
    if not active:
        return frame
    lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
    d = ImageDraw.Draw(lay)
    for b in active:
        t = (f - b["start_frame"]) / fps
        life = max(1.0 / fps, b["end"] - b["start"])
        a = int(255 * _alpha(t, life))
        if a <= 0:
            continue
        kind = b["kind"]
        px, py = b.get("pos") or DEFAULT_POS.get(kind, (0.5, 0.5))
        if kind in ("label", "highlight"):  # a spot of the picture: follow the camera
            px, py = _to_frame((px, py), box, W, H, OW, OH)
            px, py = px / OW, py / OH
        x, y = px * OW, py * OH
        sc = _scale(t)
        if kind == "text":
            frame = Image.alpha_composite(frame.convert("RGBA"), lay).convert("RGB")
            lay = Image.new("RGBA", frame.size, (0, 0, 0, 0))
            d = ImageDraw.Draw(lay)
            frame = ACC._text_layer(frame, b["text"], (px, py), sc * TEXT_SCALE, a / 255, BUB.SHOUT_FONT, big=False)
        elif kind == "label":
            tx, ty = x + (-1 if px > 0.5 else 1) * U * 0.16, max(U * 0.08, y - U * 0.14)
            d.line([(x, y), (tx, ty)], fill=PAPER + (a,), width=max(2, U // 220))
            d.ellipse([x - U * 0.008, y - U * 0.008, x + U * 0.008, y + U * 0.008], fill=CORAL + (a,))
            _tag(d, b["text"], tx, ty, U * 0.06 * min(sc, 1.05), a)
        elif kind == "highlight":
            r = U * 0.13 * (b.get("strength") or 1.0)
            sweep = 360 * _ease(t / 0.35)
            d.arc([x - r, y - r * 0.8, x + r, y + r * 0.8], -90, -90 + sweep, fill=CORAL + (a,), width=max(4, U // 90))
        elif kind == "symbol":
            _symbol(d, b["symbol"], x, y, U * 0.085 * sc, a)
        elif kind == "chart":
            _chart(d, b, x, y, U, t, a)
        elif kind == "prop":
            im = _sprite(find_file(b.get("asset"), dirs))
            if im is None:
                _tag(d, b["thing"], x, y, U * 0.06 * min(sc, 1.05), a)
            else:
                h = int(U * 0.26 * sc)
                w = max(1, int(im.width * h / max(1, im.height)))
                piece = im.resize((w, max(1, h)), Image.BICUBIC)
                if a < 255:
                    piece.putalpha(piece.getchannel("A").point(lambda v: v * a // 255))
                lay.alpha_composite(piece, (int(x - w / 2), int(y - h / 2)))
        elif kind == "expression":
            if b.get("close_up"):  # VB-09: the sheet's close-up is the frame (faces.composite); nothing drawn on top
                continue
            face = (b.get("face") or None)
            if face is not None:
                fx, fy = _to_frame(face, box, W, H, OW, OH)
                r = U * MARK_R * min(sc, 1.05)
                emotion_mark(d, b["expression"], fx + U * 0.13, fy - U * 0.13, r, a)
            sprite = _sprite(find_file((cast.get(b["who"], {}).get("expressions") or {}).get(b["expression"]), dirs))
            if sprite is not None:  # the face inset: the hero's own cut-out for this expression, swapped on every change
                h = int(U * 0.34 * sc)
                w = max(1, int(sprite.width * h / max(1, sprite.height)))
                left = face is not None and face[0] > 0.5
                ix = int(OW * 0.03) if left else int(OW * 0.97) - w
                iy = int(OH * 0.95) - h
                d.rounded_rectangle([ix - 8, iy - 8, ix + w + 8, iy + h + 8], 18, fill=(34, 27, 22, int(a * 0.8)),
                                    outline=PAPER + (a,), width=3)
                piece = sprite.resize((w, max(1, h)), Image.BICUBIC)
                if a < 255:
                    piece.putalpha(piece.getchannel("A").point(lambda v: v * a // 255))
                lay.alpha_composite(piece, (ix, iy))
    return Image.alpha_composite(frame.convert("RGBA"), lay).convert("RGB")


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (s or "").lower())


def named_heroes(at: str, cast: dict) -> list[str]:
    """The cast heroes a beat's phrase names: the hero id or the full name of his card (``name``) in the words."""
    t = _norm(at)
    return [w for w, c in cast.items() if _norm(w) in t or (c.get("name") and _norm(c["name"]) in t)]


def fit_to_views(shots: list[dict], beats: list[dict], pics: dict, cast: dict, fps: int, problems: list[dict]) -> list[dict]:
    """The timed beats made to fit what the frame shows (frame review 2026-10-20, CC-04):

    * a ring (``highlight``) whose phrase names a hero is centred on his face point in the shot's picture (FR-RING-HERO:
      the script's ``pos`` missed the face by most of the ring's radius);
    * a mark that points into the picture (ring, label) is kept only on the scene: trimmed to the scene frames of its
      shot's ``views`` (faces.views), dropped with a REVIEW when a close-up covers all of it (FR-RING-FACE);
    * a word, symbol, prop or chart that would run past its shot's cut ends with the shot when it stays readable there
      (BP-27's hold floor), so it never lands on the next picture (FR-TEXT-CUT).
    Returns the beats that remain."""
    by_id = {s["id"]: s for s in shots}
    hold_min, per_word = float(SR.T("BP-27", "hold_min_s")), float(SR.T("BP-27", "s_per_word"))
    keep = []
    for b in beats:
        s = by_id.get(b.get("shot"))
        if s is None:
            keep.append(b)
            continue
        if b["kind"] == "highlight":
            speakers = (pics.get(s["picture"], {}) or {}).get("speakers") or {}
            named = [w for w in named_heroes(b.get("at", ""), cast) if w in speakers]
            if len(named) == 1:
                b["pos"] = list(speakers[named[0]])
                b["on_hero"] = named[0]
        if b["kind"] in ("highlight", "label"):
            scene = [v for v in s.get("views") or [] if v["who"] is None]
            if s.get("views") and any(v["who"] is not None for v in s["views"]):
                e = max(b["end_frame"], b["start_frame"] + 1)
                runs = [(max(b["start_frame"], v["start_frame"]), min(e, v["end_frame"])) for v in scene]
                runs = [r for r in runs if r[1] > r[0]]
                if not runs:
                    problems.append({"rule": "PV-44 VB-03", "severity": "REVIEW", "where": f"{b['segment']} line {b['line']}",
                                     "detail": f"{b['kind']} {b.get('at', '')!r} falls on a close-up of {s['id']}: dropped "
                                     "(a mark in the picture cannot point at a close-up)"})
                    s["visual_beats"] = max(0, s.get("visual_beats", 1) - 1)
                    continue
                a, z = runs[0]
                b["start_frame"], b["end_frame"] = a, z
                b["start"], b["end"] = round(a / fps, 3), round(z / fps, 3)
        elif b["kind"] in OVERLAY and b["end"] > s["end"] + 1e-6:
            n = len(payload(b).split())
            need = max(hold_min, per_word * n) if b["kind"] == "text" else hold_min
            if s["end"] - b["start"] >= need - 1e-6:
                b["end"], b["end_frame"] = round(s["end"], 3), s["end_frame"]
        keep.append(b)
    return keep
