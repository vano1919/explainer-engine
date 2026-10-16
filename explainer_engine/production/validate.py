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
import re
from pathlib import Path

from explainer_engine.edit import board as B
from explainer_engine.production import compile as C
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.scripting import narration_lint

STOP = set("""a an the and or but so of to in on at for with by from into onto over under than then that this these those
it its it's is are was were be been being has have had do does did not no nor as if when while who whom which what where why how
one two all any each every some more most much many few very just only also too here there their them they he she his her him
we our you your i me my out up down off again once now still yet even""".split())
REAL_PERSON_VOICE = re.compile(r"\b(sound(s|ing)? like|in the voice of|imitat\w*|impersonat\w*|clon\w*|voice of)\b", re.I)
NAME_LIKE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")
DUP_SIMILAR = 0.97


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


def check_script(doc: dict, picture_dirs: list[Path] | None = None, sound_ok=None) -> list[dict]:
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
        if C.engine_of(doc, p) in ("gemini", "pod_text"):
            _, beat = C.shot_type_of(doc, pid)
            people = C.subject_with_cast(doc, p)[1]
            for f in C.prompt_v2.lint(want, world, people=people, visitors_named=sorted(doc["cast"]), beat=beat):
                if f["severity"] == "FAIL":
                    _f(out, "PV-11", pid, f"{f['rule']}: {f['detail']}")
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
    # PV-12 narration lint on what the voice gets
    for f in narration_lint.lint(S.tts_text(doc)):
        if f["severity"] == "FAIL":
            _f(out, "PV-12", f.get("where", "-"), f"{f['rule']}: {f['detail']}")
    # board on the estimated read (rhythm, state, heroes, bubbles)
    if not [x for x in out if x["severity"] == "FAIL" and x["rule"] in ("PV-03", "PV-04")]:
        timed = T.time_script(doc, estimated_words(doc))
        for f in board_findings(timed, doc):
            f = dict(f, detail=f["detail"] + " (estimated read)")
            if "RHYTHM" in f["rule"]:
                f["severity"] = "REVIEW"  # pace is a guess before the read; the real read decides
            out.append(f)
    return out


def board_findings(timed: dict, doc: dict) -> list[dict]:
    """The storyboard rules (edit/board.py) on a timed script."""
    pics = timed["pictures"]
    board = {"pictures": pics, "heroes": S.hero_names(doc), "_event_times": timed["events"]}
    shots = [dict(s, id=s["id"]) for s in timed["shots"]]
    found = B.check(board, {"shots": shots, "duration": timed["duration"]})
    return [{"rule": "PV-24 " + f["rule"], "severity": f["severity"], "where": f["shot"], "detail": f["detail"]} for f in found]


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
    for pid in {s["picture"] for s in shots}:
        p = timed["pictures"].get(pid, {})
        have = p.get("file") and (not picture_dirs or any((Path(d) / p["file"]).exists() for d in picture_dirs))
        if not have:
            if final:
                _f(out, "PV-25", pid, "picture not painted yet: a final render needs every picture")
            else:
                _f(out, "PV-25", pid, f"not painted yet: the draft shows {p.get('stand_in') or 'a placeholder card'}", "REVIEW")
    return out


def summary(found: list[dict]) -> str:
    n_f = sum(f["severity"] == "FAIL" for f in found)
    return f"{n_f} FAIL, {len(found) - n_f} REVIEW"
