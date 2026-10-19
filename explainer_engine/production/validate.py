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

from explainer_engine.audio import casting, layers
from explainer_engine.edit import board as B
from explainer_engine.edit import motion_lint
from explainer_engine.production import compile as C
from explainer_engine.production import continuity
from explainer_engine.production import graphics as GFX
from explainer_engine.production import script as S
from explainer_engine.production import timing as T
from explainer_engine.scripting import narration_lint, story_lint

STOP = set("""a an the and or but so of to in on at for with by from into onto over under than then that this these those
it its it's is are was were be been being has have had do does did not no nor as if when while who whom which what where why how
one two all any each every some more most much many few very just only also too here there their them they he she his her him
we our you your i me my out up down off again once now still yet even""".split())
REAL_PERSON_VOICE = re.compile(r"\b(sound(s|ing)? like|in the voice of|imitat\w*|impersonat\w*|clon\w*|voice of)\b", re.I)
NAME_LIKE = re.compile(r"\b[A-Z][a-z]+ [A-Z][a-z]+\b")
POINTER = re.compile(r"\b(full (story|video|episode)|whole (story|video)|on the channel|the video|this episode|watch)\b", re.I)
DUP_SIMILAR = 0.97


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
    # PV-28 shorts: a question or "did you know" hook in 3 s, whole-picture references, own length
    pic_ids = set(S.pictures(doc)[0])
    for sh in doc.get("shorts", []):
        hook = sh["hook"].strip()
        if not (hook.endswith("?") and len(hook.split()) <= 14):
            _f(out, "PV-28", sh["id"], "the hook must be one question of at most 14 words (SH-01)")
        if sh["lines"][0]["text"].strip() != hook:
            _f(out, "PV-28", sh["id"], "the first line must be the hook")
        words = sum(len(l["text"].split()) for l in sh["lines"])
        if not 40 <= words <= 130:
            _f(out, "PV-28", sh["id"], f"{words} words: a Short is 40-130 words (about 20-55 s)", "REVIEW")
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
    # PV-33 the story layer (ST rules, scripting/story_lint.py)
    for f in story_lint.lint(doc):
        _f(out, "PV-33 " + f["rule"], f["where"], f["detail"], f["severity"])
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
        for f in motion_lint.check(timed):  # MO rules on the estimated read (REVIEW)
            out.append(dict(f, rule="PV-35 " + f["rule"], detail=f["detail"] + " (estimated read)"))
        for f in layers.check(timed):  # AL rules on the estimated read (REVIEW)
            out.append(dict(f, rule="PV-36 " + f["rule"], detail=f["detail"] + " (estimated read)"))
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
