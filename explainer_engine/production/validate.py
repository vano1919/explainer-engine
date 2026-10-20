"""Validation of a production script (D-43). Rule ids PV-xx; FAIL blocks the next paid or final step, REVIEW needs a
one-line answer. Two passes:

* ``check_script(doc)`` before anything is read or painted: schema, ids, phrases in order inside their own segment,
  pictures defined and resolvable, prompts fresh and lint-clean, no duplicate prompts, story state / hero / prop logic,
  bubbles, voice direction, narration lint, sounds; and the whole board on an ESTIMATED read (the voice's pace), so a
  rhythm or story-state problem is found while the segment is being written, not after the read.
* ``check_timed(timed, doc)`` after the read: text match, exact frame tiling, legal cuts, bubbles and sounds inside
  their shots and the video, the board's STATE/HERO/RHYTHM/BUBBLE rules on the real times, and (final only) every
  picture file present.
"""

from __future__ import annotations

import difflib
import json
import re
from pathlib import Path

from explainer_engine.audio import casting, layers
from explainer_engine.edit import board as B
from explainer_engine.edit import motion_lint
from explainer_engine.production import beats as BEATS
from explainer_engine.production import faces as FACES
from explainer_engine.production import compile as C
from explainer_engine.production import continuity
from explainer_engine.production import graphics as GFX
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.qa import engagement as ENG
from explainer_engine.scripting import narration_lint, story_lint
from explainer_engine.standards import sourced_rules as SR

STOP = set("""a an the and or but so of to in on at for with by from into onto over under than then that this these those
it its it's is are was were be been being has have had do does did not no nor as if when while who whom which what where why how
one two all any each every some more most much many few very just only also too here there their them they he she his her him
we our you your i me my out up down off again once now still yet even""".split())
REAL_PERSON_VOICE = re.compile(r"\b(sound(s|ing)? like|in the voice of|imitat\w*|impersonat\w*|clon\w*|voice of)\b", re.I)
NAME_LIKE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")
POINTER = re.compile(r"\b(full (story|video|episode)|whole (story|video)|on the channel|the video|this episode|watch)\b", re.I)
DUP_SIMILAR = 0.97
# The numbers below come from the sourced rules registry (docs/SOURCED_RULES.md), never from this file.
SHORT_WPM = SR.T("BP-01", "wpm_target")  # heard pace of a Short read (BP-01; P-52, D-49)
WPM_MIN, WPM_MAX = SR.T("BP-01", "wpm_min"), SR.T("BP-01", "wpm_max")  # BP-01: the one pace band everywhere
SHORT_EVENTS_PER_10S = SR.T("BP-45", "events_per_10s_min")  # SS-08 / BP-45: breakouts show 3-6, Episode 1's showed 1.4
SHORT_MAX_STILL_S = SR.T("BP-45", "max_still_s")  # BP-45: a Short changes on screen at least this often
HOOK_MAX_WORDS = SR.T("BP-11", "hook_max_words")  # BP-11 (SH-01)
HOOK_DONE_BY_S = SR.T("BP-11", "hook_done_by_s")  # BP-11: the hook's last word ends by this on the Short's estimated read
SHORT_BANDS_S = SR.T("BP-12", "bands_s")  # BP-12: the two length bands of a set (SS-06)
SHORT_WORDS_PER_S, SHORT_SLACK = SR.T("BP-12", "words_per_s"), SR.T("BP-12", "slack")
SHORT_WORD_BANDS = [(lo * SHORT_WORDS_PER_S * (1 - SHORT_SLACK), hi * SHORT_WORDS_PER_S * (1 + SHORT_SLACK)) for lo, hi in SHORT_BANDS_S]
SIGNOFF = [p.lower() for p in SR.T("BP-44", "signoff_lexicon")]  # BP-44: never a sign-off
LINE_WORDS_MAX, GRADE_MAX = SR.T("BP-46", "line_words_max"), SR.T("BP-46", "grade_max")  # BP-46: Short lines read at grade 6
STATEMENT_HOOK_STYLES = {"anti_intuition", "pov_you"}  # may open with one statement instead of a question (SS-05)
REF_EDIT_SOFT = {"UR-22", "UR-26"}  # look thread and light key: carried by the reference picture of a pod_ref edit (PV-11)


def _norm(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def _f(out, rule, where, detail, sev="FAIL"):
    out.append({"rule": rule, "severity": sev, "where": where, "detail": detail})


def estimated_words(doc: dict) -> dict:
    """A plausible read of the text at the middle of the voice's pace: the same tokens, times from word counts and
    punctuation (0.35 s after . ? !, 0.15 s after , ; : and dashes, plus each line's pause_after)."""
    lo, hi = doc["voice"]["pace_wpm"]
    per_word = 60.0 / ((lo + hi) / 2)
    toks = S.tokens(doc)
    lines = [ln for seg in doc["segments"] for ln in seg["lines"]]
    flat_line = [(t["seg"], t["line"]) for t in toks]
    words, t = [], 0.3
    for k, tk in enumerate(toks):
        dur = per_word * (0.6 + 0.08 * len(re.sub(r"[^A-Za-z]", "", tk["w"])))
        words.append({"w": tk["w"], "s": round(t, 3), "e": round(t + dur * 0.85, 3), "para": tk["para"]})
        t += dur
        mark = tk["w"].rstrip("\"'”’)")[-1:]
        t += 0.35 if mark in ".?!…" else 0.15 if mark in ",;:—" else 0.0
        last_of_line = k + 1 == len(toks) or flat_line[k + 1] != flat_line[k]
        if last_of_line:
            seg_i, line_i = flat_line[k]
            line = doc["segments"][seg_i]["lines"][line_i]
            t += float(line.get("pause_after", 0))
    del lines
    return {"words": words, "duration": round(t + 0.5, 3), "estimated": True}


def content_words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z']+", text.lower()) if len(w) > 3 and w not in STOP}


def check_script(doc: dict, picture_dirs: list[Path] | None = None, sound_ok=None, claim_map: dict | None = None) -> list[dict]:
    """PV findings. ``claim_map`` (``scripting.claims.load_map``) turns on PV-37; callers that know the script's folder pass it."""
    out: list[dict] = []
    errs = S.schema_errors(doc)
    for e in errs:
        _f(out, "PV-01", "schema", e)
    if errs:
        return out  # the rest assumes the shape
    # PV-02 ids and order
    ids = [s["id"] for s in doc["segments"]]
    if ids != [f"S{k + 1:02d}" for k in range(len(ids))]:
        _f(out, "PV-02", "segments", f"segment ids must run S01..S{len(ids):02d} in order, got {ids}")
    pics, problems = S.pictures(doc)
    for p in problems:
        _f(out, "PV-03", "pictures", p)
    try:
        toks = S.tokens(doc)
    except ValueError as e:
        _f(out, "PV-04", "text", str(e))
        return out
    spans = S.segment_spans(toks, len(doc["segments"]))
    # PV-04 phrases: each segment opens with its own picture; shots, bubbles and sounds in order inside the segment
    shot_list = S.shots(doc)
    prev = -1
    for sh in shot_list:
        seg_i = ids.index(sh["segment"])
        lo, hi = spans[seg_i]
        s = sh["shot"]
        first_of_seg = sh is next(x for x in shot_list if x["segment"] == sh["segment"])
        i = lo if (first_of_seg and sh["seq"] == 1) else S.find_phrase(toks, s["at"], max(lo, prev + 1), hi)
        if i is None:
            _f(out, "PV-04", sh["id"], f"phrase {s['at']!r} is not in segment {sh['segment']} after the previous shot")
            continue
        if first_of_seg and i != lo:
            _f(out, "PV-04", sh["id"], f"segment {sh['segment']} starts with {toks[lo]['w']!r} but its first picture waits for "
                                       f"{s['at']!r}: the previous segment's picture would cover its opening words")
        prev = i
    for seg_i, seg in enumerate(doc["segments"]):
        lo, hi = spans[seg_i]
        c = lo
        for e in seg.get("audio", {}).get("sfx", []):
            j = S.find_phrase(toks, e["at"], c, hi)
            if j is None:
                _f(out, "PV-04", f"{seg['id']} sfx", f"phrase {e['at']!r} for {e['sound']} not in the segment (in order)")
            else:
                c = j
    # PV-05 assets
    used = {k: v for k, v in pics.items() if v.get("uses")}
    for pid, p in used.items():
        eng = C.engine_of(doc, p)
        if eng == "existing" and not p.get("file"):
            _f(out, "PV-05", pid, "picture has no file and no engine to paint it")
        if eng in ("gemini", "pod_text") and not p.get("subject"):
            _f(out, "PV-05", pid, f"engine {eng} needs a subject (written with its line)")
        if eng == "pod_ref":
            if not p.get("refs"):
                _f(out, "PV-05", pid, "pod_ref needs refs (the Gemini frames it starts from)")
            for r in p.get("refs", []):
                if r not in pics or not pics[r].get("file"):
                    _f(out, "PV-05", pid, f"reference {r!r} is not an existing picture")
            if not (p.get("edit") or p.get("subject")):
                _f(out, "PV-05", pid, "pod_ref needs an edit or a subject")
        if p.get("stand_in") and (p["stand_in"] not in pics or not pics[p["stand_in"]].get("file")):
            _f(out, "PV-05", pid, f"stand-in {p['stand_in']!r} is not an existing picture")
        if picture_dirs and p.get("file") and not any((Path(d) / p["file"]).exists() for d in picture_dirs):
            _f(out, "PV-05", pid, f"file {p['file']} not found in {[str(d) for d in picture_dirs]}")
        for h in p.get("heroes", []):
            if h not in doc["cast"]:
                _f(out, "PV-05", pid, f"hero {h!r} is not in the cast")
        for b_who in p.get("speakers", {}):
            if b_who not in doc["cast"]:
                _f(out, "PV-05", pid, f"speaker {b_who!r} is not in the cast")
    # PV-26 likeness by reference: a painted-by-edit picture shows a named hero only when one of its references carries that
    # hero's face (library `heroes` of the reference). 2026-10-16: two Snow pictures named a reference that is Franklin + Einstein.
    for pid, p in used.items():
        if C.engine_of(doc, p) != "pod_ref":
            continue
        for h in p.get("heroes", []):
            if not any(h in pics.get(r, {}).get("heroes", []) for r in p.get("refs", [])):
                _f(out, "PV-26", pid, f"hero {h!r} has no reference with their face (refs {p.get('refs')}); add a reference "
                                      f"picture that shows {h} and list {h} in its library `heroes`")
    if sound_ok:
        for seg in doc["segments"]:
            au = seg.get("audio", {})
            for name in [b["sound"] for b in au.get("beds", [])] + [e["sound"] for e in au.get("sfx", [])]:
                if not sound_ok(name):
                    _f(out, "PV-05", seg["id"], f"sound {name!r} not found (sound_dirs or the library manifest)")
        for m in doc.get("music", []):
            if not sound_ok(m["track"]):
                _f(out, "PV-05", "music", f"track {m['track']!r} not found")
    beds = [seg.get("audio", {}).get("beds", []) for seg in doc["segments"]]
    if any(beds) and not beds[0]:
        _f(out, "PV-14", "S01", "a bed is used later but the first segment names none: the opening would be silent")
    for seg_i, seg in enumerate(doc["segments"]):  # beds and sfx phrases inside their segment, in order
        lo, hi = spans[seg_i]
        c = lo
        for bd in seg.get("audio", {}).get("beds", []):
            j = S.find_phrase(toks, bd["at"], c, hi)
            if j is None:
                _f(out, "PV-04", f"{seg['id']} bed", f"phrase {bd['at']!r} for {bd['sound']} not in the segment (in order)")
            else:
                c = j
    if not doc["voice"].get("voice_id"):
        _f(out, "PV-10", "voice", "no voice chosen yet: pick one of voice.candidates (test read first) before the full read",
           "REVIEW")
    # PV-11 prompts fresh and clean; PV-06 duplicates
    world = C.world_of(doc)
    prompts = {}
    for pid, p in used.items():
        want = C.compose(doc, pid, p, world)
        if want is None:
            continue
        if p.get("prompt") != want:
            _f(out, "PV-11", pid, "prompt is missing or stale: run `python -m explainer_engine.production compile`")
            continue
        prompts[pid] = want
        # every painted prompt is linted, the reference edits (pod_ref) too: they are what is paid for (audit 2026-10-19 H1).
        # A reference edit takes its look and light from the reference picture, so a missing thread (UR-22) or light key
        # (UR-26) is a REVIEW there; child cues, absent objects and "not yet" stay FAIL for every engine.
        eng = C.engine_of(doc, p)
        _, beat = C.shot_type_of(doc, pid)
        people = C.subject_with_cast(doc, p)[1]
        soft = []
        for f in C.prompt_v2.lint(want, world, people=people, visitors_named=sorted(doc["cast"]), beat=beat):
            if eng == "pod_ref" and f["rule"] in REF_EDIT_SOFT:
                soft.append(f["rule"])
            elif f["severity"] == "FAIL":
                _f(out, "PV-11", pid, f"{f['rule']}: {f['detail']}")
        if soft:
            _f(out, "PV-11", pid, f"reference edit without {' and '.join(sorted(set(soft)))} (look thread / one light key): "
                                  "the reference picture must carry them", "REVIEW")
    seen = {}
    for pid, pr in prompts.items():
        key = re.sub(r"\s+", " ", pr.lower()).strip()
        if key in seen:
            _f(out, "PV-06", pid, f"same prompt as {seen[key]}: one picture, two ids (reuse the id instead)")
        seen.setdefault(key, pid)
    subj = {pid: used[pid].get("edit") or used[pid].get("subject", "") for pid in prompts}
    keys = sorted(subj)
    for a_i, a in enumerate(keys):
        for b in keys[a_i + 1:]:
            if subj[a] and subj[b] and difflib.SequenceMatcher(a=subj[a].lower(), b=subj[b].lower()).ratio() > DUP_SIMILAR:
                _f(out, "PV-06", b, f"subject almost the same as {a}", "REVIEW")
    # PV-07 props
    forbidden = [x.lower() for x in doc.get("story", {}).get("forbidden_props", [])]
    owners = {prop.lower(): h for h, c in doc["cast"].items() for prop in c.get("props", [])}
    for pid, p in used.items():
        text = p.get("subject", "").lower()  # an edit may name what it removes ("replace the magnifying glass")
        for fp in forbidden:
            if fp in text or any(fp == pr["thing"].lower() for pr in p.get("props", [])):
                _f(out, "PV-07", pid, f"shows {fp!r}, which the story forbids")
        for pr in p.get("props", []):
            own = owners.get(pr["thing"].lower())
            if own and pr.get("held_by") and pr["held_by"] != own:
                _f(out, "PV-07", pid, f"{pr['thing']!r} belongs to {own} but is held by {pr['held_by']}")
    # PV-08 the picture's subject and its line share content (painted pictures only)
    toks_text = [t["w"] for t in toks]
    for k, sh in enumerate(shot_list):
        p = pics.get(sh["picture_id"], {})
        if p.get("first_use") != sh["id"] or not (p.get("subject") or p.get("edit")):
            continue
        seg_i = ids.index(sh["segment"])
        lo, hi = spans[seg_i]
        line = " ".join(toks_text[lo:hi])
        if not content_words(p.get("subject", "") + " " + p.get("edit", "")) & content_words(line):
            _f(out, "PV-08", sh["id"], f"{sh['picture_id']}: its subject shares no word with segment {sh['segment']}", "REVIEW")
    # PV-10 voice direction never names a person to imitate
    v = doc["voice"]
    if REAL_PERSON_VOICE.search(v["style"]) or NAME_LIKE.search(v["style"]):
        _f(out, "PV-10", "voice", "the voice style must describe the sound, never a real person to imitate or clone")
    # PV-52 / BP-01: the heard pace of the estimated read lies inside BP-01's band. Heard pace is words / duration with the
    # pauses (BP-01's one definition); voice.pace_wpm is the voice's speaking rate, which the estimate times the words at
    # before it adds the punctuation and held pauses, so a pace_wpm inside the band can still estimate a slower heard read.
    heard = heard_wpm(estimated_words(doc))
    if heard is not None and not WPM_MIN <= heard <= WPM_MAX:
        lo_wpm, hi_wpm = v["pace_wpm"]
        _f(out, "PV-52 BP-01", "voice", f"the estimated read is heard at {heard:.0f} wpm (pace_wpm {lo_wpm}-{hi_wpm} plus the "
           f"punctuation and held pauses), outside the heard-pace band {WPM_MIN}-{WPM_MAX} wpm (target {SHORT_WPM}, BP-01): "
           "change pace_wpm or the pauses, or say why this voice is slower", SR.rule("BP-01").get("severity", "REVIEW"))
    # PV-32 voiced dialogue (D-45): a speaking hero is in the cast and has a voice of their own, described, never imitated
    spoken = [(seg["id"], ln) for seg in doc["segments"] for ln in seg["lines"]]
    spoken += [(sh["id"], ln) for sh in doc.get("shorts", []) for ln in sh["lines"]]
    for who in dict.fromkeys(ln["speaker"] for _, ln in spoken if ln.get("speaker")):
        where = next(w for w, ln in spoken if ln.get("speaker") == who)
        if who not in doc["cast"]:
            _f(out, "PV-32", where, f"speaker {who!r} is not in the cast")
        elif not doc["cast"][who].get("voice"):
            _f(out, "PV-32", where, f"speaker {who!r} has no cast voice: describe it in cast.{who}.voice.style")
        else:
            hv = doc["cast"][who]["voice"]
            if REAL_PERSON_VOICE.search(hv["style"]) or NAME_LIKE.search(hv["style"]):
                _f(out, "PV-10", who, "the voice style must describe the sound, never a real person to imitate or clone")
            if not hv.get("voice_id"):
                _f(out, "PV-32", who, "no voice chosen yet for this hero: pick one after a test read, before the full read",
                   "REVIEW")
            if not casting.age_of(doc["cast"][who]):  # the creator 2026-10-19: ages matter most
                _f(out, "PV-32", who, "the hero's age is not known: set voice.traits.age (young/middle_aged/old) before "
                   "casting, so no voice of the wrong age is offered", "REVIEW")
            if not casting.accent_of(doc["cast"][who]["voice"].get("traits", {})):  # VC-05
                _f(out, "PV-32", who, "no accent follows from voice.traits.origin or .ethnicity: name where the hero is from "
                   "so the voice carries the right accent", "REVIEW")
            for why in casting.problems(doc["cast"][who]):  # VC-01/VC-02: cast from documented traits, never imitate
                _f(out, "PV-10", who, why)
    if S.has_dialogue(doc):
        ids = {}
        for who in [S.NARRATOR] + [h for h in doc["cast"] if doc["cast"][h].get("voice")]:
            vid = S.voice_of(doc, who)
            if vid and vid in ids:
                _f(out, "PV-32", who, f"same voice id as {ids[vid]!r}: two speakers must sound different", "REVIEW")
            ids.setdefault(vid, who)
        for why in casting.distinct({h: c for h, c in doc["cast"].items() if c.get("voice")}):
            _f(out, "PV-32", "cast", why + " (VC-04)", "REVIEW")
    # PV-27 time-jump periods: each period's last spoken line opens the next question; tone mix sums to about 1
    periods = {p["id"]: p for p in doc.get("periods", [])}
    if periods:
        order = []
        for si, seg in enumerate(doc["segments"]):
            pid = seg.get("period")
            if pid is None or pid not in periods:
                _f(out, "PV-27", seg["id"], f"segment period {pid!r} is not in the document's periods")
            elif not order or order[-1][0] != pid:
                order.append([pid, si])
            if pid in periods:
                order[-1].append(si) if order and order[-1][0] == pid else None
        ids = [pid for pid, *_ in order]
        if len(set(ids)) != len(ids):
            _f(out, "PV-27", "segments", "a period's segments must be consecutive")
        for k, (pid, *sis) in enumerate(order[:-1]):
            last = doc["segments"][max(sis)]["lines"][-1]["text"].strip()
            if "?" not in last:
                _f(out, "PV-27", doc["segments"][max(sis)]["id"],
                   f"period {pid} should end on the question that opens {order[k + 1][0]} (SR-03), got: {last[-60:]!r}", "REVIEW")
        for pid, p in periods.items():
            tone = p.get("tone")
            if tone and abs(sum(tone.values()) - 1.0) > 0.05:
                _f(out, "PV-27", pid, f"tone shares sum to {sum(tone.values()):.2f}, not 1 (SR-07)")
    # PV-30/31 period cards and data visuals (ED-09, ED-10)
    for per in doc.get("periods", []):
        if not (per.get("card") or {}).get("title"):
            _f(out, "PV-30", per["id"], "the period has no card title (ED-09)", "REVIEW")
    seen = {}
    for g in doc.get("graphics", []):
        for why in GFX.check_visual(g):
            _f(out, "PV-31", g["id"], why)
        seg = next((s for s in doc["segments"] if s["id"] == g["segment"]), None)
        if seg is None:
            _f(out, "PV-31", g["id"], f"segment {g['segment']!r} does not exist")
        else:
            seen[seg.get("period")] = seen.get(seg.get("period"), 0) + 1
    for per in doc.get("periods", []):
        if doc.get("graphics") and not seen.get(per["id"]):
            _f(out, "PV-31", per["id"], "no data visual in this period (ED-10)", "REVIEW")
    # PV-28 shorts: the hook per BP-11 (one question, or one statement that raises several, at most HOOK_MAX_WORDS words),
    # whole-picture references, the word budget per BP-12, the open premise per BP-44, readability per BP-46
    pic_ids = set(S.pictures(doc)[0])
    for sh in doc.get("shorts", []):
        hook = sh["hook"].strip()
        statement_ok = sh.get("style") in STATEMENT_HOOK_STYLES  # creator 2026-10-19 (SS-05)
        one_sentence = len(re.findall(r"[.!?](?:\s|$)", hook)) <= 1
        if len(hook.split()) > HOOK_MAX_WORDS:
            _f(out, "PV-28", sh["id"], f"the hook is {len(hook.split())} words; at most {HOOK_MAX_WORDS} (SH-01, BP-11)")
        if not hook.endswith("?"):
            if not one_sentence:
                _f(out, "PV-28", sh["id"], "the hook is one question or one statement, not several sentences (SH-01, BP-11)")
            elif not statement_ok:
                _f(out, "PV-28", sh["id"], "a statement hook must raise a question (SH-04): say which, or make it a question "
                   "(BP-11; the styles anti_intuition and pov_you open with a statement by design, SS-05)", "REVIEW")
        if sh["lines"][0]["text"].strip() != hook:
            _f(out, "PV-28", sh["id"], "the first line must be the hook")
        else:  # BP-11: the hook is complete by HOOK_DONE_BY_S (the tighter bound at 170 wpm). On the estimated read it is a
            # REVIEW, as every timing guess here is (RHYTHM below); the real read decides with BP-11's severity in shorts.py
            end = hook_end_s(doc, sh)
            if end is not None and end > HOOK_DONE_BY_S:
                fit = int(HOOK_DONE_BY_S * SHORT_WPM / 60)
                _f(out, "PV-28", sh["id"], f"the hook ends at {end:.1f} s on the estimated read ({SHORT_WPM} wpm); it is complete by "
                   f"{HOOK_DONE_BY_S:g} s (about {fit} words fit; BP-11): shorten it, or the real read stops the Short's render",
                   "REVIEW")
        words = sum(len(l["text"].split()) for l in sh["lines"])
        if not any(a <= words <= b for a, b in SHORT_WORD_BANDS):
            bands = " or ".join(f"{a:.0f}-{b:.0f} words ({lo}-{hi} s)" for (a, b), (lo, hi) in zip(SHORT_WORD_BANDS, SHORT_BANDS_S))
            _f(out, "PV-28", sh["id"], f"{words} words: a Short's budget is {bands} at {SHORT_WPM} wpm (BP-12)", "REVIEW")
        # BP-44: the premise stays open. The line that answers the hook cannot be told apart mechanically from the lines
        # around it (payoff_after_share is the shorts-writer's and the script-critic's reading); the code checks the two
        # ends it can see: lines 2-3 foreshadow with a promise marker, the last line never signs off.
        last_text = sh["lines"][-1]["text"].lower().replace("’", "'")
        for phrase in SIGNOFF:
            if phrase in last_text:
                _f(out, "PV-28", sh["id"], f"the last line signs off ({phrase!r}): a Short ends on a loop or a pointer, never a "
                   "sign-off (BP-44)")
        foreshadow = " ".join(l["text"] for l in sh["lines"][1:3])
        if foreshadow and not ENG.PROMISE.search(foreshadow):
            _f(out, "PV-28", sh["id"], "lines 2-3 carry no promise marker (will, by the end, watch, until, but, turns out, wait): "
               "foreshadow the payoff inside 3 s of the hook (BP-44)", "REVIEW")
        # BP-46: every line short, the whole Short at grade GRADE_MAX or under
        for k, l in enumerate(sh["lines"], 1):
            if len(l["text"].split()) > LINE_WORDS_MAX:
                _f(out, "PV-28", sh["id"], f"line {k} has {len(l['text'].split())} words; at most {LINE_WORDS_MAX} per Short line "
                   "(BP-46)", "REVIEW")
        grade = fk_grade(" ".join(l["text"] for l in sh["lines"]))
        if grade > GRADE_MAX:
            _f(out, "PV-28", sh["id"], f"reads at grade {grade:.1f} (Flesch-Kincaid); Short lines stay at grade {GRADE_MAX:g} or "
               "under (BP-46): shorter words, shorter sentences", "REVIEW")
        main = re.sub(r"\W+", " ", S.narration_text(doc).lower())
        new = sum(len(l["text"]) for l in sh["lines"][1:] if re.sub(r"\W+", " ", l["text"].lower()).strip() not in main)
        if new > 400:
            _f(out, "PV-28", sh["id"], f"{new} characters are new text, not in the main read: each is paid again (EL-09); "
               "cut lines from the main read where the story allows", "REVIEW")
        for x in sh["shots"]:
            if x["picture"] not in pic_ids:
                _f(out, "PV-28", sh["id"], f"picture {x['picture']!r} is not a picture of the video (SH-03)")
        if len(sh["lines"]) > 1 and not POINTER.search(sh["lines"][-1]["text"]):
            _f(out, "PV-28", sh["id"], "the last line does not point to the full video (SH-01)", "REVIEW")
    # PV-28 a set of Shorts (SH-05): each opens its own question and tells its own scene
    shorts = doc.get("shorts", [])
    for i, a in enumerate(shorts):
        for b in shorts[i + 1:]:
            if _norm(a["hook"]) == _norm(b["hook"]):
                _f(out, "PV-28", b["id"], f"the same hook as {a['id']}: every Short opens its own question (SH-05)")
            shared = {_norm(x["text"]) for x in a["lines"][1:-1]} & {_norm(x["text"]) for x in b["lines"][1:-1]}
            if shared:
                _f(out, "PV-28", b["id"], f"{len(shared)} line(s) also told in {a['id']}: one scene, one Short (SH-05)",
                   "REVIEW")
            pa, pb = {x["picture"] for x in a["shots"]}, {x["picture"] for x in b["shots"]}
            if pa and pb and len(pa & pb) / len(pa | pb) >= 0.5:
                _f(out, "PV-28", b["id"], f"half or more of its pictures are also in {a['id']}: one scene, one Short (SH-05)",
                   "REVIEW")
    # PV-34 a set of Shorts in different styles (SS-01..SS-03)
    styles = [sh.get("style") for sh in shorts]
    if len(shorts) >= 5:
        if None in styles:
            _f(out, "PV-34", "shorts", f"{styles.count(None)} Short(s) without a style (SS-01)", "REVIEW")
        named = [x for x in styles if x]
        need = min(6, max(3, len(shorts) * 6 // 10))
        if len(set(named)) < need:
            _f(out, "PV-34", "shorts", f"{len(set(named))} styles in {len(shorts)} Shorts; a set uses at least {need} (SS-01)", "REVIEW")
    for a, b in zip(shorts, shorts[1:]):
        if a.get("style") and a.get("style") == b.get("style"):
            _f(out, "PV-34", b["id"], f"same style as {a['id']} right before it: alternate styles in the posting order (SS-02)", "REVIEW")
    for sh in shorts:
        end = sh.get("ending")
        last = sh["lines"][-1]["text"] if sh["lines"] else ""
        if end == "loop" and not (content_words(last) & content_words(sh["lines"][0]["text"]) or last.rstrip()[-1:] in ",-—…"):
            _f(out, "PV-34", sh["id"], "a loop ending must run into the first line (shared words or an unfinished last line) (SS-04)", "REVIEW")
        if end == "pointer" and not POINTER.search(last):
            _f(out, "PV-34", sh["id"], "ending 'pointer' but the last line does not point to the video (SS-04)", "REVIEW")
    # PV-34 continued (D-49): two length bands (BP-12), the first cut inside the hook, enough visual events (SS-06..SS-08, BP-45)
    def _short_seconds(sh):
        return sum(len(x["text"].split()) for x in sh["lines"]) / SHORT_WPM * 60
    (b1_lo, b1_hi), (b2_lo, b2_hi) = SHORT_BANDS_S
    if len(shorts) >= 6:
        secs = [_short_seconds(sh) for sh in shorts]
        short_band = sum(s <= b1_hi * (1 + SHORT_SLACK) for s in secs)
        long_band = sum(s >= b2_lo * (1 - SHORT_SLACK) for s in secs)
        if short_band < 3 or long_band < 3:
            _f(out, "PV-34", "shorts", f"{short_band} Short(s) of {b1_lo}-{b1_hi} s and {long_band} of {b2_lo}-{b2_hi} s (estimated at "
               f"{SHORT_WPM} wpm, BP-12): a set spans both bands, at least 3 each, so the channel's own data decides the length (SS-06)",
               "REVIEW")
    for sh in shorts:
        hook_words = content_words(sh["hook"])
        shots = sh.get("shots", [])
        if len(shots) >= 2 and not content_words(shots[1].get("at", "")) & hook_words:
            _f(out, "PV-34", sh["id"], "the first cut is not inside the hook line: the second shot starts on a word of the hook "
               "(about 2 s in), the first still never holds past it (SS-07)", "REVIEW")
        secs = _short_seconds(sh)
        events = len(shots) + sum(len(x.get("accents", [])) + len(x.get("bubbles", [])) for x in shots)
        if secs >= 10 and events / secs * 10 < SHORT_EVENTS_PER_10S:
            _f(out, "PV-34", sh["id"], f"{events / secs * 10:.1f} visual events every 10 s (shots + accents + bubbles): "
               f"the breakouts show 3-6, ours showed 1.4; plan at least {SHORT_EVENTS_PER_10S} (SS-08, BP-45)", "REVIEW")
        # BP-45 max_still_s on the Short's estimated read: no picture holds longer than SHORT_MAX_STILL_S
        if len(shots) >= 1 and not [f for f in out if f["where"] == sh["id"] and f["severity"] == "FAIL"]:
            sd = BEATS.short_doc(doc, sh)
            timed = T.time_script(sd, short_words(sd))
            if not timed["problems"]:
                for row in timed["shots"]:
                    if row["end"] - row["start"] > SHORT_MAX_STILL_S:
                        _f(out, "PV-34", sh["id"], f"shot {row['id']} holds {row['end'] - row['start']:.1f} s on the estimated read: "
                           f"a Short changes on screen at least every {SHORT_MAX_STILL_S:g} s (BP-45)", "REVIEW")
    # PV-33 the story layer (ST rules, scripting/story_lint.py)
    for f in story_lint.lint(doc):
        _f(out, "PV-33 " + f["rule"], f["where"], f["detail"], f["severity"])
    # PV-48 scenes and dialogue (SC rules, scripting/scene_lint.py; binding on production_script/3, D-58)
    from explainer_engine.scripting import scene_lint
    for f in scene_lint.lint(doc):
        _f(out, "PV-48 " + f["rule"], f["where"], f["detail"], f["severity"])
    if doc["episode"].get("rulebook"):  # scripts written to an episode rulebook (D-51/D-52)
        out += rulebook_era_findings(doc, picture_dirs)
    out += canva_findings(doc)
    out += BEATS.lint(doc)  # PV-44 visual beats: reasons, words, numbers, faces (VB-00, VB-03, VB-04, VB-06)
    out += FACES.lint(doc, picture_dirs)  # PV-44 expression sheets (VB-09)
    out += short_beat_findings(doc)  # PV-44 on every Short (SS-09)
    # PV-12 narration lint on what the voice gets: FAILs block, REVIEWs are forwarded too (audit 2026-10-19 A6: they
    # never reached the validator before; the BP numbers behind the N rules live in the sourced rules). N-14 runs on the
    # narrator's lines only (doc_findings): a hero may name a date inside a scene, and on /3 SC-07 (PV-48) reads the same
    # BP-15 lexicon on those lines, so N-14 is not repeated there. N-15: a narration hold over BP-10's limit.
    from explainer_engine.scripting import scene_lint as _scene
    for f in narration_lint.lint(S.tts_text(doc), press=False) + narration_lint.doc_findings(doc, press=not _scene.binding(doc)):
        _f(out, "PV-12", f.get("where", "-"), f"{f['rule']}: {f['detail']}", f["severity"])
    # board on the estimated read (rhythm, state, heroes, bubbles)
    if not [x for x in out if x["severity"] == "FAIL" and x["rule"] in ("PV-03", "PV-04")]:
        timed = T.time_script(doc, estimated_words(doc))
        for f in board_findings(timed, doc):
            f = dict(f, detail=f["detail"] + " (estimated read)")
            if "RHYTHM" in f["rule"]:
                f["severity"] = "REVIEW"  # pace is a guess before the read; the real read decides
            out.append(f)
        for f in motion_lint.check(timed):  # MO rules on the estimated read (REVIEW)
            out.append(dict(f, rule="PV-35 " + f["rule"], detail=f["detail"] + " (estimated read)"))
        for f in layers.check(timed):  # AL rules on the estimated read (REVIEW)
            out.append(dict(f, rule="PV-36 " + f["rule"], detail=f["detail"] + " (estimated read)"))
        for f in BEATS.check_timed(timed, doc):  # VB rules on the estimated read (the beat-writer's own check)
            out.append(dict(f, detail=f["detail"] + " (estimated read)"))
    if claim_map is not None or any(c for seg in doc["segments"] for ln in seg["lines"] for c in ln.get("claims", [])):
        from explainer_engine.scripting import claims as _claims
        out += _claims.check(doc, claim_map)
    from explainer_engine.scripting import distinct as _distinct
    out += _distinct.check(doc)
    from explainer_engine.scripting import scenario as _scenario
    out += _scenario.check(doc, picture_dirs[0].parent if picture_dirs else None)
    from explainer_engine.scripting import speech as _speech
    out += _speech.check(doc)
    from explainer_engine.scripting import reference_approval as _reference
    out += _reference.check(doc, picture_dirs[0].parent if picture_dirs else None)  # PV-47 variant collage first (OR-16)
    return out


def heard_wpm(read: dict) -> float | None:
    """BP-01's heard pace of a read (``words.json`` shape): spoken words per minute of the whole read, pauses included."""
    n = sum(1 for w in read["words"] if re.search(r"[A-Za-z0-9]", w["w"]))
    return n / read["duration"] * 60 if read["duration"] and n else None


def short_seconds(sh: dict) -> float:
    """BP-12: a Short's estimated length, its words at BP-01's heard pace (SHORT_WPM). The one duration every Short check
    uses: the word budget's bands, PV-34's length bands, and the estimated read below (``short_words``) all agree with it."""
    return sum(len(x["text"].split()) for x in sh["lines"]) / SHORT_WPM * 60


def short_words(sd: dict) -> dict:
    """The estimated read of a Short (``short_doc``): its shape from ``estimated_words`` (word lengths, punctuation, held
    pauses), scaled so that it lasts exactly ``short_seconds`` (BP-12's heard-pace definition)."""
    est = estimated_words(dict(sd, voice=dict(sd["voice"], pace_wpm=[SHORT_WPM, SHORT_WPM])))
    total = short_seconds({"lines": [ln for seg in sd["segments"] for ln in seg["lines"]]})
    k = total / est["duration"] if est["duration"] else 1.0
    words = [dict(w, s=round(w["s"] * k, 3), e=round(w["e"] * k, 3)) for w in est["words"]]
    return {"words": words, "duration": round(total, 3), "estimated": True}


def hook_end_s(doc: dict, sh: dict) -> float | None:
    """BP-11: when the hook (the Short's first line) ends on the Short's estimated read (``short_words``), or None."""
    try:
        read = short_words({"voice": doc["voice"], "segments": [{"id": sh["id"], "lines": sh["lines"]}]})
    except (ValueError, KeyError, IndexError):
        return None
    n = len(S.script_tokens(sh["lines"][0]["text"]))
    return read["words"][n - 1]["e"] if 0 < n <= len(read["words"]) else None


def syllables(word: str) -> int:
    """Syllables of one English word by vowel groups (a silent final -e dropped, -le kept); at least one. Good enough for a
    Flesch-Kincaid grade on short lines; no dependency."""
    w = re.sub(r"[^a-z]", "", word.lower())
    if not w:
        return 0
    groups = len(re.findall(r"[aeiouy]+", w))
    if w.endswith("e") and not w.endswith(("le", "ee", "ye")) and groups > 1:
        groups -= 1
    return max(1, groups)


def fk_grade(text: str) -> float:
    """Flesch-Kincaid grade level of ``text`` (BP-46): 0.39 x words per sentence + 11.8 x syllables per word - 15.59."""
    sents = [s for s in re.split(r"(?<=[.!?])\s+", text.strip()) if re.search(r"[A-Za-z0-9]", s)]
    ws = re.findall(r"[A-Za-z0-9][A-Za-z0-9'’-]*", text)
    if not ws or not sents:
        return 0.0
    syl = sum(syllables(w) for w in ws)
    return 0.39 * len(ws) / len(sents) + 11.8 * syl / len(ws) - 15.59


def short_beat_findings(doc: dict) -> list[dict]:
    """PV-44 on every Short (SS-09): the same VB lint and cadence check as the segments, on the Short's own estimated read,
    reported as "SH03 line 2". A legacy script whose Shorts have no beats gets nothing (its one VB-00 notice covers it)."""
    out: list[dict] = []
    if not BEATS.binding(doc) and not BEATS.has_short_beats(doc):
        return out
    for sh in doc.get("shorts", []):
        sd = BEATS.short_doc(doc, sh)
        if not BEATS.has_beats(sd) and not BEATS.binding(doc):
            continue
        found = BEATS.lint(sd) + [f for f in FACES.lint(sd) if not f["where"].startswith("cast.")]
        found = [dict(f, where=sh["id"]) if f["where"] == "script" else f for f in found]
        if BEATS.has_beats(sd) and not [f for f in found if f["severity"] == "FAIL" and f["rule"].endswith("VB-03")]:
            timed = T.time_script(sd, short_words(sd))
            if timed["problems"]:
                found += [dict(f, detail=f["detail"] + f" ({sh['id']})") for f in timed["problems"]]
            else:
                found += [dict(f, detail=f["detail"] + " (estimated read)") for f in BEATS.check_timed(timed, sd)]
        out += found
    return out


NUMBER = re.compile(r"\d")


def canva_findings(doc: dict) -> list[dict]:
    """PV-43 (D-53): a picture may come from Canva only when it is filler, only while the Canva terms are verified, and at
    most FILLER_SHARE_MAX of the episode's pictures (always checked, a script without a rulebook included)."""
    from explainer_engine.imagegen import importance
    from explainer_engine.standards import rulebook
    pics, _ = S.pictures(doc)
    used = {k: p for k, p in pics.items() if p.get("uses")}
    canva = [k for k, p in used.items() if p.get("engine") == "canva"]
    out: list[dict] = []
    if not canva:
        return out
    if not rulebook.baseline()["channel"].get("canva_terms_verified"):
        _f(out, "PV-43", "pictures", f"{len(canva)} pictures use engine canva but the Canva AI terms and content licence are "
           "not verified (policy_baseline channel.canva_terms_verified); paint them on the Gemini batch tier")
    kinds = importance.classify(doc)
    for k in canva:
        if not kinds[k]["filler"]:
            _f(out, "PV-43", k, "Canva is for filler only; this picture is not filler: " + "; ".join(kinds[k]["why_not"]))
    if len(canva) / len(used) > importance.FILLER_SHARE_MAX:
        _f(out, "PV-43", "pictures", f"{len(canva)} of {len(used)} pictures come from Canva (> "
           f"{importance.FILLER_SHARE_MAX:.0%})")
    if len(canva) > importance.CANVA_FREE_AI_USES:
        _f(out, "PV-43", "pictures", f"{len(canva)} Canva pictures exceed the free plan's about "
           f"{importance.CANVA_FREE_AI_USES} AI uses (V-39)", "REVIEW")
    return out


def _pod_planned(doc: dict, picture_dirs: list[Path] | None = None) -> set[str]:
    """Picture ids a paint plan with provider ``pod`` names (``<pictures>/plans/*.json``, written by ``paint plan``)."""
    plans = list(doc.get("_plans") or [])
    for d in picture_dirs or []:
        for f in sorted(Path(d).glob("plans/*.json")):
            try:
                plans.append(json.loads(f.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue
    return {it["id"] for pl in plans if pl.get("provider") == "pod" for it in pl.get("items", [])}


def rulebook_era_findings(doc: dict, picture_dirs: list[Path] | None = None) -> list[dict]:
    """PV-39..PV-42 for scripts written to an episode rulebook (older scripts keep their rules unchanged)."""
    from explainer_engine.imagegen import routing
    out: list[dict] = []
    segs = doc["segments"]
    for seg in segs:  # PV-39 every beat says what it does for the viewer
        if not seg.get("job"):
            _f(out, "PV-39", seg["id"], "no beat job (hook, question, explanation, evidence, complication, reveal, "
               "emotional_pause, humor, payoff, transition)")
    if segs[0].get("job") not in (None, "hook", "question"):
        _f(out, "PV-39", segs[0]["id"], "the first beat is not a hook or a question", "REVIEW")
    if segs[-1].get("job") not in (None, "payoff"):
        _f(out, "PV-39", segs[-1]["id"], "the last beat is not a payoff", "REVIEW")
    pics, _ = S.pictures(doc)  # PV-40 the creator picks the provider per batch (D-50 supersedes D-52's "Gemini only"): a pod
    painted = [p for p in pics.values() if p.get("uses") and not p.get("file")]  # engine needs a paint plan that names the pod
    planned = _pod_planned(doc, picture_dirs)
    for p in painted:
        eng = C.engine_of(doc, p)
        if eng == "pod_text" and p["id"] not in planned:
            _f(out, "PV-40", p["id"], "a pod picture without a paint plan naming it: `paint plan --provider pod` first, then the "
               "creator's provider choice (D-50); else engine gemini or pod_ref", "REVIEW")
        if routing.tier_of(p) == "premium" and not (p.get("tier_reason") or "").strip():
            _f(out, "PV-40", p["id"], "a premium picture needs tier_reason (reused across videos, or a reveal that must "
               "hold several references)")
    prem = sum(routing.tier_of(p) == "premium" for p in painted)
    if painted and prem / len(painted) > routing.PREMIUM_SHARE_MAX:
        _f(out, "PV-40", "pictures", f"{prem} of {len(painted)} pictures are premium (> {routing.PREMIUM_SHARE_MAX:.0%})",
           "REVIEW")
    for seg in segs:  # PV-41 sounds have a job; PV-42 shots have a purpose, numbers have a claim
        for kind in ("beds", "sfx"):
            for ev in seg.get("audio", {}).get(kind, []):
                if not (ev.get("purpose") or "").strip():
                    _f(out, "PV-41", seg["id"], f"{kind[:-1] if kind == 'beds' else 'sound'} {ev['sound']!r} at "
                       f"{ev['at']!r} has no purpose", "REVIEW")
        for sh in seg["shots"]:
            if not (sh.get("purpose") or "").strip():
                _f(out, "PV-42", seg["id"], f"shot at {sh['at']!r} has no purpose", "REVIEW")
        for line in seg["lines"]:
            if NUMBER.search(line["text"]) and not line.get("claims"):
                _f(out, "PV-42", seg["id"], f"a number without a claim id: {line['text'][:50]!r} (invariant 5)")
    return out


def board_findings(timed: dict, doc: dict) -> list[dict]:
    """The storyboard rules (edit/board.py) on a timed script."""
    pics = timed["pictures"]
    board = {"pictures": pics, "heroes": S.hero_names(doc), "_event_times": timed["events"]}
    shots = [dict(s, id=s["id"]) for s in timed["shots"]]
    found = B.check(board, {"shots": shots, "duration": timed["duration"]})
    return [{"rule": "PV-24 " + f["rule"], "severity": f["severity"], "where": f["shot"], "detail": f["detail"]} for f in found]


TICKS = ("clockwork_loop",)  # music beds that are a tick: they sit well under every other track (ED-03)
TICK_MAX_DB = -25.0
MAX_CROSSFADE = 3.0


def music_findings(music: list[dict]) -> list[dict]:
    """PV-29 / ED-03: one music at a time (a handover may overlap by a crossfade), and a tick stays quiet."""
    out: list[dict] = []
    ms = sorted(music, key=lambda m: m["start"])
    for a, b in zip(ms, ms[1:]):
        over = a["end"] - b["start"]
        if over > MAX_CROSSFADE + 1e-6:
            _f(out, "PV-29", b["track"], f"two music tracks together for {over:.1f} s ({a['track']} and {b['track']}); a crossfade is at most {MAX_CROSSFADE:.0f} s")
    for m in ms:
        if m["track"].startswith(TICKS) and m["gain_db"] > TICK_MAX_DB:
            _f(out, "PV-29", m["track"], f"the tick is at {m['gain_db']} dB; it must be {TICK_MAX_DB} dB or lower")
    return out


def check_timed(timed: dict, doc: dict, *, final: bool = False, picture_dirs: list[Path] | None = None) -> list[dict]:
    out = [dict(p) for p in timed.get("problems", [])]
    if timed["text_match"] < T.MIN_TEXT_MATCH:
        _f(out, "PV-20", "words", f"the read matches the script only {timed['text_match']:.1%}: re-read or re-align")
    shots = timed["shots"]
    if [s["seq"] for s in shots] != list(range(1, len(shots) + 1)):
        _f(out, "PV-21", "shots", "sequence numbers are not 1..N in order")
    if shots and shots[0]["start_frame"] != 0:
        _f(out, "PV-21", shots[0]["id"], "the first shot does not start on frame 0")
    for a, b in zip(shots, shots[1:]):
        if a["end_frame"] != b["start_frame"]:
            _f(out, "PV-21", b["id"], f"gap or overlap: {a['id']} ends on frame {a['end_frame']}, {b['id']} starts on {b['start_frame']}")
        if b["start"] <= a["start"]:
            _f(out, "PV-21", b["id"], "starts before or with the shot before it (ordering)")
    if shots and shots[-1]["end_frame"] != timed["frames"]:
        _f(out, "PV-21", shots[-1]["id"], "the last shot does not end on the final frame")
    for s in shots:
        if s["frames"] <= 0:
            _f(out, "PV-21", s["id"], "has no frames")
        for b in s["bubbles"]:
            if not (s["start"] <= b["start"] < b["end"] <= s["end"]):
                _f(out, "PV-23", s["id"], f"bubble {b['text'][:24]!r} is not inside its shot")
    for e in timed["audio"]["sfx"]:
        if not (0 <= e["start"] < e["end"] <= timed["duration"] + 1e-6):
            _f(out, "PV-23", e["sound"], "sound outside the video")
    beds = timed["audio"]["beds"]
    if beds and (beds[0]["start"] > 0 or beds[-1]["end"] < timed["duration"] - 1e-6):
        _f(out, "PV-23", "beds", "the ambience does not cover the whole video")
    out += board_findings(timed, doc)
    out += continuity.findings(shots)
    out += music_findings(timed["audio"]["music"])
    out += [dict(f, rule="PV-35 " + f["rule"]) for f in motion_lint.check(timed)]  # MO rules (D-48)
    out += [dict(f, rule="PV-36 " + f["rule"]) for f in layers.check(timed)]  # AL rules (D-48)
    out += BEATS.check_timed(timed, doc)  # VB rules on the real read (PV-44)
    for pid in {s["picture"] for s in shots}:
        p = timed["pictures"].get(pid, {})
        names = [n for n in (p.get("file"), f"{pid}.png", f"{pid}_v1.png") if n]  # as assemble.find_picture looks them up
        have = any((Path(d) / n).exists() for d in picture_dirs for n in names) if picture_dirs else bool(p.get("file"))
        if not have:
            if final:
                _f(out, "PV-25", pid, "picture not painted yet: a final render needs every picture")
            else:
                _f(out, "PV-25", pid, f"not painted yet: the draft shows {p.get('stand_in') or 'a placeholder card'}", "REVIEW")
    return out


def summary(found: list[dict]) -> str:
    n_f = sum(f["severity"] == "FAIL" for f in found)
    return f"{n_f} FAIL, {len(found) - n_f} REVIEW"
