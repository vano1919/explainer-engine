"""Time a production script on its read (D-43): the edit decision list every later step uses.

    timed = time_script(doc, words_doc)

``words_doc`` is ``words.json`` (``scribe_words.align`` of ``script.narration_text`` against the read, then
``pause_pad``). When it was made from this exact text, written token k is word k; otherwise the two are matched by
normalised words and the share that matched is reported (below 97 % the timing FAILs, PV-20). Every time is in
seconds rounded to the millisecond and in frames at the episode's fps; shots tile the video exactly (each shot ends on
the frame the next one starts, the last on the final frame), which is what an automated editor needs.
"""

from __future__ import annotations

import difflib

from explainer_engine.audio import layers as L
from explainer_engine.audio.scribe_words import norm
from explainer_engine.edit import board as B
from explainer_engine.production import accents as ACC, beats as BEATS, continuity, script as S
from explainer_engine.standards import sourced_rules as SR

BED_DEFAULT_DB = L.MAX_BED_DB  # a bed with no gain sits at the AL-04 cap (BP-65); it was -13 and broke the cap

MIN_TEXT_MATCH = 0.97
BUBBLE_LEAD = B.BUBBLE_LEAD
BED_LEAD, BED_FADE = 0.4, 1.5
# BP-54: a picture-synced sound lands on its frame and never early (the ear forgives late more than early): the default
# offset is 0 (the word's first frame), and a scripted ``offset_s`` is held inside the sourced window (early_max_ms before,
# late_max_ms after). The old -0.05 s lead sat past the early limit.
SFX_OFFSET, SFX_MAX = 0.0, 1.0
SFX_EARLY_MAX, SFX_LATE_MAX = SR.T("BP-54", "early_max_ms") / 1000, SR.T("BP-54", "late_max_ms") / 1000
# BP-62: music fades 1 s in and 2 s out unless the script sets ``fade_s`` (one length for both ends, kept from /1 and /2)
MUSIC_FADE_IN, MUSIC_FADE_OUT = float(SR.T("BP-62", "fade_in_s")), float(SR.T("BP-62", "fade_out_s"))


def word_map(toks: list[dict], words: list[dict]) -> tuple[list[int | None], float]:
    """script token index -> words.json index (None when the read has no such word), and the matched share."""
    if len(toks) == len(words) and all(t["w"] == w["w"] for t, w in zip(toks, words)):
        return list(range(len(toks))), 1.0
    a = [" ".join(norm(t["w"])) for t in toks]
    b = [" ".join(norm(w["w"])) for w in words]
    m: list[int | None] = [None] * len(toks)
    for op, a0, a1, b0, b1 in difflib.SequenceMatcher(a=a, b=b, autojunk=False).get_opcodes():
        if op == "equal" or (op == "replace" and a1 - a0 == b1 - b0):
            for k in range(a1 - a0):
                m[a0 + k] = b0 + k
    matched = sum(x is not None for x in m) / max(1, len(m))
    # an unmatched token borrows the next matched word (its start) so phrases still land; reported via the share
    nxt = None
    for i in range(len(m) - 1, -1, -1):
        if m[i] is None:
            m[i] = nxt
        else:
            nxt = m[i]
    # a read that stops early leaves the last tokens with no next word: they hold on the last heard word, so the timing
    # still builds and PV-20 reports the low match instead of a crash (audit 2026-10-19 M3)
    prev = None
    for i in range(len(m)):
        if m[i] is None:
            m[i] = prev
        else:
            prev = m[i]
    if words and any(x is None for x in m):  # nothing matched at all
        m = [min(i, len(words) - 1) for i in range(len(m))]
    return m, round(matched, 4)


def _frames(t: float, fps: int) -> int:
    return int(round(t * fps))


def time_script(doc: dict, words_doc: dict) -> dict:
    fps = int(doc["episode"].get("fps", 30))
    words, duration = words_doc["words"], float(words_doc["duration"])
    toks = S.tokens(doc)
    wmap, share = word_map(toks, words)
    spans = S.segment_spans(toks, len(doc["segments"]))
    pics, _ = S.pictures(doc)
    problems: list[dict] = []

    def wi(i: int | None):
        return None if i is None else wmap[i]

    def at_word(phrase: str, lo: int, hi: int, where: str) -> int | None:
        i = S.find_phrase(toks, phrase, lo, hi)
        if i is None or wi(i) is None:
            problems.append({"rule": "PV-04", "severity": "FAIL", "where": where, "detail": f"phrase {phrase!r} not found in order"})
            return None
        return i

    out_shots, segs, lines = [], [], []
    cursor = 0
    for si, seg in enumerate(doc["segments"]):
        lo, hi = spans[si]
        idx = [i for i, t in enumerate(toks) if t["seg"] == si]
        for li, line in enumerate(seg["lines"]):
            li_idx = [i for i in idx if toks[i]["line"] == li]
            a, b = words[wi(li_idx[0])], words[wi(li_idx[-1])]
            lines.append({"segment": seg["id"], "line": li + 1, "text": line["text"], "start": a["s"], "end": b["e"],
                          "duration": round(b["e"] - a["s"], 3), "tone": line.get("tone"), "emotion": line.get("emotion"),
                          "pause_after": line.get("pause_after", 0)})
            if line.get("speaker"):
                lines[-1]["speaker"] = line["speaker"]
        segs.append({"id": seg["id"], "beat": seg["beat"], "start": words[wi(lo)]["s"], "end": words[wi(hi - 1)]["e"]})
        for s in seg["shots"]:
            n = len(out_shots) + 1
            where = f"SH{n:03d}"
            i = at_word(s["at"], max(lo, cursor), hi, where) if n > 1 else lo
            if i is None:
                i = max(lo, cursor)
            cursor = i + 1
            w = wi(i)
            start, legal = B.cut_before(words, w)
            pid = s["picture"] if isinstance(s["picture"], str) else s["picture"]["id"]
            out_shots.append({"seq": n, "id": where, "segment": seg["id"], "picture": pid, "type": s["type"],
                              "at": s["at"], "token": i, "word": w, "start": start, "cut_legal": legal,
                              "motion": s["motion"], "transition": s.get("transition", "cut"),
                              "insert": s.get("insert", False), "reuse": s.get("reuse"), "reveal": s.get("reveal"), "heroes_ok": s.get("heroes_ok", False),
                              "_bubbles": s.get("bubbles", []), "_accents": s.get("accents", []), "_seg_hi": hi})
    seg_period = {sg["id"]: sg.get("period") for sg in doc["segments"]}
    for k, s in enumerate(out_shots):  # UR-14/ED-04: a period opens with a dissolve (a time jump), nothing else dissolves
        if k and s.get("transition", "cut") == "cut" and seg_period.get(s["segment"]) != seg_period.get(out_shots[k - 1]["segment"]):
            s["transition"], s["time_jump"], s["transition_seconds"] = "dissolve", True, 1.0
    continuity.chain(out_shots)  # ED-02: render_motion continues across shots of one picture
    total_frames = _frames(duration, fps)
    for k, s in enumerate(out_shots):
        nxt = out_shots[k + 1] if k + 1 < len(out_shots) else None
        s["end"] = nxt["start"] if nxt else round(duration, 3)
        s["duration"] = round(s["end"] - s["start"], 3)
        s["start_frame"] = _frames(s["start"], fps)
        s["end_frame"] = _frames(nxt["start"], fps) if nxt else total_frames
        s["frames"] = s["end_frame"] - s["start_frame"]
        tok_end = nxt["token"] if nxt else len(toks)
        s["text"] = " ".join(t["w"] for t in toks[s["token"]:tok_end])
        bub, bc = [], s["token"]
        for b in s.pop("_bubbles"):
            j = at_word(b["at"], bc, tok_end, s["id"] + " bubble")
            if j is None:
                continue
            bc = j + 1
            bstart = max(s["start"], words[wi(j)]["s"] - BUBBLE_LEAD)
            if b.get("until"):
                u = at_word(b["until"], bc, tok_end, s["id"] + " bubble until")
                bend = words[wi(u)]["s"] - 0.05 if u is not None else s["end"] - 0.05
            elif b.get("hold"):
                bend = bstart + float(b["hold"])
            else:
                bend = s["end"] - 0.05
            bend = min(bend, s["end"] - 0.05)
            bub.append({"who": b["who"], "text": b["text"], "kind": b.get("kind", "speech"), "start": round(bstart, 3),
                        "end": round(bend, 3), "start_frame": _frames(bstart, fps), "end_frame": _frames(bend, fps)})
        s["bubbles"] = bub

        def accent_start(phrase, lo=s["token"], hi=tok_end, where=s["id"]):
            j = at_word(phrase, lo, hi, where + " accent")
            return None if j is None else words[wi(j)]["s"]

        s["accents"] = ACC.resolve(s.pop("_accents"), s["start"], s["end"], accent_start, fps)  # MO rules (D-48)
        s.pop("_seg_hi")
    beats = BEATS.resolve(doc, toks, words, wi, out_shots, fps, duration, problems)  # VB rules: the lines' visual beats
    # sound
    beds, sfx = [], []
    for si, seg in enumerate(doc["segments"]):
        lo, hi = spans[si]
        au = seg.get("audio", {})
        cb = lo
        for bd in au.get("beds", []):
            j = at_word(bd["at"], cb, hi, f"{seg['id']} bed {bd['sound']}")
            if j is None:
                continue
            cb = j
            beds.append({"sound": bd["sound"], "segment": seg["id"], "at": bd["at"], "gain_db": bd.get("gain_db", BED_DEFAULT_DB),
                         "start": 0.0 if not beds else round(max(0.0, words[wi(j)]["s"] - BED_LEAD), 3)})
        for e in au.get("sfx", []):
            j = at_word(e["at"], lo, hi, f"{seg['id']} sfx {e['sound']}")
            if j is None:
                continue
            off = min(max(float(e.get("offset_s", SFX_OFFSET)), -SFX_EARLY_MAX), SFX_LATE_MAX)  # BP-54 window
            st = max(0.0, words[wi(j)]["s"] + off)
            en = min(duration, st + e.get("max_s", SFX_MAX))
            sfx.append({"sound": e["sound"], "segment": seg["id"], "at": e["at"], "gain_db": e.get("gain_db", -18),
                        "start": round(st, 3), "end": round(en, 3), "start_frame": _frames(st, fps), "end_frame": _frames(en, fps)})
    for k, b in enumerate(beds):
        b["end"] = round(min(duration, beds[k + 1]["start"] + BED_FADE), 3) if k + 1 < len(beds) else round(duration, 3)
        b["fade_s"] = BED_FADE
    cues = BEATS.cue_track(beats, duration, fps)  # VB-08: a short light sound on every beat that has one
    music = []
    for m in doc.get("music", []):
        a = at_word(m["from"], 0, len(toks), f"music {m['track']}") if m["from"] != "<start>" else 0
        st = 0.0 if m["from"] == "<start>" or a is None else words[wi(a)]["s"]
        if m.get("to"):
            z = at_word(m["to"], a or 0, len(toks), f"music {m['track']} to")
            en = words[wi(z)]["s"] if z is not None else duration
        else:
            en = duration
        music.append({"track": m["track"], "start": round(st, 3), "end": round(min(en, duration), 3), "gain_db": m.get("gain_db", -18),
                      "fade_in_s": float(m.get("fade_s", MUSIC_FADE_IN)), "fade_out_s": float(m.get("fade_s", MUSIC_FADE_OUT))})
    for k in range(len(music) - 1):  # ED-03: a track handing over to the next one crossfades (the earlier rings on while the later fades in)
        a, b = music[k], music[k + 1]
        if abs(a["end"] - b["start"]) < 0.05:
            a["end"] = round(min(duration, b["start"] + float(b["fade_in_s"])), 3)
    visuals = []  # ED-10: data visuals start on the phrase they explain and hold 3-7 s
    seg_index = {sg["id"]: i for i, sg in enumerate(doc["segments"])}
    for g in doc.get("graphics", []):
        si = seg_index.get(g["segment"])
        j = at_word(g["at"], *spans[si], f"visual {g['id']}") if si is not None else None
        if j is None:
            continue
        st = words[wi(j)]["s"]
        hold = float(g.get("hold", 4.0))
        visuals.append(dict(g, start=round(st, 3), end=round(min(duration, st + hold), 3), hold=hold,
                            start_frame=_frames(st, fps), end_frame=_frames(min(duration, st + hold), fps)))
    cards = []  # ED-09: the first seconds of every period carry its card
    for pi, per in enumerate(doc.get("periods", [])):
        first = next((s for s in out_shots if seg_period.get(s["segment"]) == per["id"]), None)
        if first:
            card = per.get("card") or {}
            cards.append({"period": per["id"], "index": pi, "of": len(doc["periods"]), "title": card.get("title", per["id"].upper()),
                          "line": card.get("line", per.get("question", "")), "start": first["start"],
                          "start_frame": first["start_frame"] if "start_frame" in first else _frames(first["start"], fps)})
    counters = []  # ED-15: the corner counter shows each label from the first shot of its segment to the next label
    for c in doc.get("counter", []):
        first = next((s for s in out_shots if s["segment"] == c["segment"]), None)
        if first:
            counters.append({"label": c["label"], "start": first["start"],
                             "start_frame": first["start_frame"] if "start_frame" in first else _frames(first["start"], fps)})
    counters.sort(key=lambda c: c["start_frame"])
    for a, b in zip(counters, counters[1:] + [None]):
        a["end_frame"] = b["start_frame"] if b else total_frames
        a["prev"] = None
    for a, b in zip(counters, counters[1:]):
        b["prev"] = a["label"]
    events = {}
    for e in doc.get("story", {}).get("events", []):
        j = S.find_phrase(toks, e["at"], 0)
        if j is None or wi(j) is None:
            problems.append({"rule": "PV-04", "severity": "FAIL", "where": "story", "detail": f"event phrase {e['at']!r} not found"})
            continue
        events[e["thing"]] = B.cut_before(words, wi(j))[0]  # a thing exists from the cut before its words
    return {"schema": "production_timed/1", "script_schema": doc.get("schema"), "episode": doc["episode"]["id"], "fps": fps,
            "duration": round(duration, 3),
            "frames": total_frames, "text_match": share, "segments": segs, "lines": lines, "shots": out_shots,
            "audio": {"beds": beds, "sfx": sfx, "music": music, "cues": cues}, "visuals": visuals, "cards": cards, "counters": counters, "visual_beats": beats,
            "expressions": {h: c["expressions"] for h, c in doc.get("cast", {}).items() if c.get("expressions")},
            "face_sheets": {h: c["face_sheet"] for h, c in doc.get("cast", {}).items() if c.get("face_sheet")}, "events": events,
            "pictures": {k: {kk: vv for kk, vv in v.items() if kk not in ("source",)} for k, v in pics.items()},
            "problems": problems}
