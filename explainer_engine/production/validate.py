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
from explainer_engine.production import continuity
from explainer_engine.production import graphics as GFX
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
    if doc["episode"].get("rulebook"):  # scripts written to an episode rulebook (D-45/D-46)
        out += rulebook_era_findings(doc)
    out += canva_findings(doc)
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


NUMBER = re.compile(r"\d")


def canva_findings(doc: dict) -> list[dict]:
    """PV-36 (D-47): a picture may come from Canva only when it is filler, only while the Canva terms are verified, and at
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
        _f(out, "PV-36", "pictures", f"{len(canva)} pictures use engine canva but the Canva AI terms and content licence are "
           "not verified (policy_baseline channel.canva_terms_verified); paint them on the Gemini batch tier")
    kinds = importance.classify(doc)
    for k in canva:
        if not kinds[k]["filler"]:
            _f(out, "PV-36", k, "Canva is for filler only; this picture is not filler: " + "; ".join(kinds[k]["why_not"]))
    if len(canva) / len(used) > importance.FILLER_SHARE_MAX:
        _f(out, "PV-36", "pictures", f"{len(canva)} of {len(used)} pictures come from Canva (> "
           f"{importance.FILLER_SHARE_MAX:.0%})")
    if len(canva) > importance.CANVA_FREE_AI_USES:
        _f(out, "PV-36", "pictures", f"{len(canva)} Canva pictures exceed the free plan's about "
           f"{importance.CANVA_FREE_AI_USES} AI uses (V-39)", "REVIEW")
    return out


def rulebook_era_findings(doc: dict) -> list[dict]:
    """PV-32..PV-35 for scripts written to an episode rulebook (older scripts keep their rules unchanged)."""
    from explainer_engine.imagegen import routing
    out: list[dict] = []
    segs = doc["segments"]
    for seg in segs:  # PV-32 every beat says what it does for the viewer
        if not seg.get("job"):
            _f(out, "PV-32", seg["id"], "no beat job (hook, question, explanation, evidence, complication, reveal, "
               "emotional_pause, humor, payoff, transition)")
    if segs[0].get("job") not in (None, "hook", "question"):
        _f(out, "PV-32", segs[0]["id"], "the first beat is not a hook or a question", "REVIEW")
    if segs[-1].get("job") not in (None, "payoff"):
        _f(out, "PV-32", segs[-1]["id"], "the last beat is not a payoff", "REVIEW")
    pics, _ = S.pictures(doc)  # PV-33 every painted picture goes to the Gemini batch tier, premium only with a reason
    painted = [p for p in pics.values() if p.get("uses") and not p.get("file")]
    for p in painted:
        eng = C.engine_of(doc, p)
        if eng == "pod_text":
            _f(out, "PV-33", p["id"], "pod pictures are no longer made (D-46): engine gemini or pod_ref, batch tier")
        if routing.tier_of(p) == "premium" and not (p.get("tier_reason") or "").strip():
            _f(out, "PV-33", p["id"], "a premium picture needs tier_reason (reused across videos, or a reveal that must "
               "hold several references)")
    prem = sum(routing.tier_of(p) == "premium" for p in painted)
    if painted and prem / len(painted) > routing.PREMIUM_SHARE_MAX:
        _f(out, "PV-33", "pictures", f"{prem} of {len(painted)} pictures are premium (> {routing.PREMIUM_SHARE_MAX:.0%})",
           "REVIEW")
    for seg in segs:  # PV-34 sounds have a job; PV-35 shots have a purpose, numbers have a claim
        for kind in ("beds", "sfx"):
            for ev in seg.get("audio", {}).get(kind, []):
                if not (ev.get("purpose") or "").strip():
                    _f(out, "PV-34", seg["id"], f"{kind[:-1] if kind == 'beds' else 'sound'} {ev['sound']!r} at "
                       f"{ev['at']!r} has no purpose", "REVIEW")
        for sh in seg["shots"]:
            if not (sh.get("purpose") or "").strip():
                _f(out, "PV-35", seg["id"], f"shot at {sh['at']!r} has no purpose", "REVIEW")
        for line in seg["lines"]:
            if NUMBER.search(line["text"]) and not line.get("claims"):
                _f(out, "PV-35", seg["id"], f"a number without a claim id: {line['text'][:50]!r} (invariant 5)")
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
