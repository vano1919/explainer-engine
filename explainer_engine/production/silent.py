"""Silent lines (D-62): a line with ``"voiced": false`` is never read by a synthetic voice; it is shown as speech bubbles.

The creator's call (2026-10-20, titans thread): real living people speak only in bubbles, because the voice provider's
terms bar synthesizing a living person's identity without consent (episode rule RK-01/RK-02). PV-55 binds it: a cast
member marked ``traits.real_person`` has no voiced line.

A silent line takes reading time instead of speaking time. Its text is cut into bubble pieces of at most BP-84's words,
each held BP-27's reading hold. ``production words`` aligns the read against the voiced lines only, then ``insert``
opens a quiet gap in the read for every silent line and gives its tokens synthetic word times inside that gap, so
words.json keeps one entry per written token and the timing, beats and shots work as before. ``time_script`` turns each
piece into one bubble on the shot that holds it (``bubbles_for``); a piece is never drawn twice (BUBBLE-5).
"""

from __future__ import annotations

import re

from explainer_engine.audio.scribe_words import script_tokens
from explainer_engine.standards import sourced_rules as SR

LEAD_S = 0.35      # quiet before a silent line's first bubble (the previous voice settles, the bubble pops)
GAP_S = 0.3        # between two bubble pieces of one line (a legal cut point, UR-12)
TAIL_S = 0.35      # after the last piece, before the next line


def voiced(line: dict) -> bool:
    return line.get("voiced", True)


def max_words() -> int:
    return int(SR.T("BP-84", "bubble_words_max"))


def hold(n_words: int) -> float:
    """BP-27: a popped text holds at least max(hold_min_s, s_per_word x words), at most hold_max_s."""
    return min(SR.T("BP-27", "hold_max_s"), max(SR.T("BP-27", "hold_min_s"), SR.T("BP-27", "s_per_word") * n_words))


def pieces(text: str, limit: int | None = None) -> list[str]:
    """The line cut into bubbles: one sentence each, a sentence over ``limit`` words into even parts."""
    limit = limit or max_words()
    out: list[str] = []
    for sent in [p.strip() for p in re.split(r"(?<=[.!?…])\s+", text.strip()) if p.strip()]:
        w = sent.split()
        if len(w) > limit:
            k = -(-len(w) // limit)
            size = -(-len(w) // k)
            out += [" ".join(w[i:i + size]) for i in range(0, len(w), size)]
        else:  # one sentence, one bubble: the edit may cut between sentences, never inside a bubble (BUBBLE-5)
            out.append(sent)
    return out


def plan(line: dict) -> list[dict]:
    """[{text, tokens, seconds}] per bubble piece; ``tokens`` counts the written tokens the piece covers."""
    rows = []
    for p in pieces(line["text"]):
        n = len(script_tokens(p))
        rows.append({"text": p, "tokens": n, "seconds": round(hold(len(p.split())), 3)})
    if sum(r["tokens"] for r in rows) != len(script_tokens(line["text"])):  # tokenisation across a cut: keep it one piece
        rows = [{"text": line["text"], "tokens": len(script_tokens(line["text"])),
                 "seconds": round(hold(len(line["text"].split())), 3)}]
    return rows


def plan_n(line: dict, n: int) -> list[dict]:
    """``plan`` held to ``n`` tokens, the line's token count in the whole script (a lone mark glued to a neighbour line
    changes it): on a mismatch the line is one piece."""
    rows = plan(line)
    if sum(r["tokens"] for r in rows) != n:
        rows = [{"text": line["text"], "tokens": n, "seconds": round(sum(r["seconds"] for r in rows), 3)}]
    return rows


def seconds(line: dict) -> float:
    """How long a silent line holds the screen, quiet lead and tail included."""
    p = plan(line)
    return LEAD_S + sum(r["seconds"] for r in p) + GAP_S * (len(p) - 1) + TAIL_S


def voiced_doc(doc: dict) -> dict:
    """The script with only what a voice reads: silent lines dropped (a segment may become empty)."""
    return dict(doc, segments=[dict(s, lines=[ln for ln in s["lines"] if voiced(ln)]) for s in doc["segments"]])


def has_silent(doc: dict) -> bool:
    return any(not voiced(ln) for s in doc["segments"] for ln in s["lines"])


def insert(doc: dict, voiced_words: list[dict], pcm, sr: int):
    """The full word list (one entry per token of ``script.tokens(doc)``) and the read with a quiet gap for every silent
    line. ``voiced_words`` are the aligned words of ``voiced_doc(doc)``. Each gap opens at the quietest spot of the pause
    between the voiced words around it (``pause_pad.quiet_point``) and is filled with the read's own room tone, so no
    voiced sound is cut and no gap reads as a dropout (ED-12, BP-60)."""
    import numpy as np

    from explainer_engine.production import script as S
    toks, vtoks = S.tokens(doc), S.tokens(voiced_doc(doc))
    if len(vtoks) != len(voiced_words):
        raise ValueError(f"voiced words {len(voiced_words)} != voiced tokens {len(vtoks)}")
    order: list[tuple[int, int]] = []
    for t in toks:
        if not order or order[-1] != (t["seg"], t["line"]):
            order.append((t["seg"], t["line"]))
    count = {}
    for t in toks:
        count[(t["seg"], t["line"])] = count.get((t["seg"], t["line"]), 0) + 1
    # pass 1: original-time insert point for every run of silent lines
    from explainer_engine.audio import pause_pad as PP
    pcm = np.asarray(pcm)
    total = len(pcm) / sr
    j, prev_e, runs = 0, 0.0, []
    for key in order:
        line = doc["segments"][key[0]]["lines"][key[1]]
        n = count[key]
        if voiced(line):
            if runs and runs[-1]["at"] is None:  # the quietest spot of the pause, as pause_pad finds it (word times are off
                nxt_s = voiced_words[j]["s"]     # by 0.1-0.2 s: the measured middle can be inside a word, ED-12)
                lo, hi = max(0.0, prev_e - PP.SEARCH), min(total, nxt_s + PP.SEARCH)
                mid = (prev_e + nxt_s) / 2 if nxt_s > prev_e else prev_e
                runs[-1]["at"] = PP.quiet_point(pcm, sr, lo, hi, mid)[0] if hi > lo else mid
            prev_e = voiced_words[j + n - 1]["e"]
            j += n
        elif runs and runs[-1]["at"] is None:
            runs[-1]["lines"].append(key)
        else:
            runs.append({"at": None, "lines": [key]})
    for r in runs:
        if r["at"] is None:
            r["at"] = min(total, prev_e + 0.2)
    # pass 2: the new pcm and the full word list
    pieces_pcm, cursor, shift = [], 0, 0.0
    lens = {}
    src = pcm.astype(pcm.dtype, copy=True)
    f = max(1, int(PP.FADE_MS / 1000 * sr))
    for r in runs:  # entered and left on a short fade (no click, no clipped consonant)
        i = int(round(r["at"] * sr))
        n0, n1 = min(f, i), min(f, len(src) - i)
        if n0:
            src[i - n0:i] *= np.linspace(1, 0, n0).astype(src.dtype)
        if n1:
            src[i:i + n1] *= np.linspace(0, 1, n1).astype(src.dtype)
    fill_db = min(PP.noise_floor_db(pcm, sr), PP.FILL_MAX_DB)  # room tone, never digital zero (BP-60, ED-12)
    for n, r in enumerate(runs):
        k = int(round(r["at"] * sr))
        pieces_pcm.append(src[cursor:k])
        dur = sum(seconds(doc["segments"][a]["lines"][b]) for a, b in r["lines"])
        pieces_pcm.append(PP.room_tone(int(round(dur * sr)), fill_db, 1000 + n, src.dtype))
        cursor = k
        r["shift_before"], r["seconds"] = shift, dur
        shift += dur
        for key in r["lines"]:
            lens[key] = r
    pieces_pcm.append(src[cursor:])
    out_pcm = np.concatenate(pieces_pcm) if pieces_pcm else pcm

    def shifted(w: dict, t0: float, after: list[dict]) -> dict:
        """A word of a line that follows a gap in script order never lands before that gap's end: a word the recogniser
        missed is only interpolated and can sit just before the insert point (Titans "Elon Musk. Musk signs.")."""
        add = sum(r["seconds"] for r in runs if r["at"] <= t0 + 1e-9 or r in after)
        floor = max([r["at"] for r in after], default=0.0)
        s0 = max(w["s"], floor)
        return dict(w, s=round(s0 + add, 3), e=round(max(w["e"], s0) + add, 3))

    words, j = [], 0
    starts = {}
    for r in runs:
        t = r["at"] + r["shift_before"] + LEAD_S
        for key in r["lines"]:
            starts[key] = t
            t += seconds(doc["segments"][key[0]]["lines"][key[1]])
    passed: list[dict] = []
    for key in order:
        line = doc["segments"][key[0]]["lines"][key[1]]
        n = count[key]
        if voiced(line):
            words += [shifted(w, w["s"], passed) for w in voiced_words[j:j + n]]
            j += n
            continue
        if not any(r is lens[key] for r in passed):
            passed.append(lens[key])
        t = starts[key]
        for p in plan_n(line, n):
            step = p["seconds"] / max(1, p["tokens"])
            for i in range(p["tokens"]):
                words.append({"w": toks[len(words)]["w"], "s": round(t + i * step, 3), "e": round(t + (i + 1) * step, 3),
                              "silent": True})
            t += p["seconds"] + GAP_S
    return out_pcm, words


def bubbles_for(doc: dict, toks: list[dict], words: list[dict], wi, shots: list[dict]) -> tuple[dict, list[dict]]:
    """{shot index: [bubble spec]} for every silent line's pieces, and problems: a piece must sit inside one shot (a cut
    inside it would draw the same text twice, BUBBLE-5)."""
    out: dict[int, list[dict]] = {}
    problems = []
    first = {}
    for i, t in enumerate(toks):
        first.setdefault((t["seg"], t["line"]), i)
    n_of = {}
    for t in toks:
        n_of[(t["seg"], t["line"])] = n_of.get((t["seg"], t["line"]), 0) + 1
    for (si, li), i0 in first.items():
        line = doc["segments"][si]["lines"][li]
        if voiced(line):
            continue
        i = i0
        for p in plan_n(line, n_of[(si, li)]):
            a, b = words[wi(i)], words[wi(i + p["tokens"] - 1)]
            start, end = a["s"], b["e"]
            k = max((k for k, s in enumerate(shots) if s["start"] <= start + 1e-6), default=0)
            if end > shots[k]["end"] + 1e-6:
                problems.append({"rule": "BUBBLE-5", "severity": "FAIL", "where": shots[k]["id"],
                                 "detail": f"a cut at {shots[k]['end']:.2f} s falls inside the bubble {p['text'][:40]!r}: "
                                           "move the cut so each bubble lives in one shot"})
            out.setdefault(k, []).append({"who": line.get("speaker"), "text": p["text"], "kind": "speech",
                                          "start": round(start, 3), "end": round(min(end, shots[k]["end"] - 0.05), 3),
                                          "silent": True})
            i += p["tokens"]
    return out, problems


def check_real_people(doc: dict) -> list[str]:
    """PV-55: no voiced line for a cast member who is a real living person (D-62). Binds a production_script/3; a real
    person counts as living unless ``traits.living`` is false (the provider's terms on the dead are narrower)."""
    if doc.get("schema") != "production_script/3":
        return []

    def traits(c):
        return {**(c.get("traits") or {}), **((c.get("voice") or {}).get("traits") or {})}
    real = {h for h, c in doc.get("cast", {}).items() if traits(c).get("real_person") and traits(c).get("living", True)}
    out = []
    for seg in doc["segments"]:
        for k, line in enumerate(seg["lines"], 1):
            if line.get("speaker") in real and voiced(line):
                out.append(f"{seg['id']} line {k}: {line['speaker']} is a real person and must not be voiced "
                           "(voiced: false, shown as bubbles; D-62)")
            if not voiced(line) and not line.get("speaker"):
                out.append(f"{seg['id']} line {k}: a silent line needs a speaker to hang its bubble on")
    for sh in doc.get("shorts", []):
        for k, line in enumerate(sh.get("lines", []), 1):
            if isinstance(line, dict) and line.get("speaker") in real and voiced(line):
                out.append(f"{sh['id']} line {k}: {line['speaker']} is a real person and must not be voiced (D-62)")
    return out


MAX_ACCENT_BUBBLES = 1  # D-63 (creator 2026-10-20): "nobody reads the text"; a bubble survives only as one accent per scene


def check_reported_dialogue(doc: dict) -> list[str]:
    """PV-56 (D-63): the narrator tells what the real people said ("he asks...", "the other answers..."); a scene keeps at
    most MAX_ACCENT_BUBBLES silent line, as an accent. Binds a production_script/3 that has real people in its cast."""
    if doc.get("schema") != "production_script/3":
        return []
    out = []
    for seg in doc["segments"]:
        silent = [k for k, line in enumerate(seg["lines"], 1) if not voiced(line)]
        if len(silent) > MAX_ACCENT_BUBBLES:
            out.append(f"{seg['id']}: {len(silent)} bubble lines (lines {silent[:6]}); the narrator reports the exchange and "
                       f"a scene keeps at most {MAX_ACCENT_BUBBLES} bubble as an accent (D-63)")
    return out


def check_duplicates(shots: list[dict]) -> list[dict]:
    """BUBBLE-5: the same text is never on screen twice at once, and a text is not popped again in the next shot."""
    out = []
    seen = []
    for s in shots:
        for b in s.get("bubbles", []):
            for o in seen:
                if o["text"].strip().lower() == b["text"].strip().lower() and (o["end"] > b["start"] - 1e-6
                                                                               or b["start"] - o["end"] < 3.0):
                    out.append({"rule": "BUBBLE-5", "severity": "FAIL", "where": s["id"],
                                "detail": f"{b['text'][:40]!r} is shown twice ({o['start']:.2f} s and {b['start']:.2f} s)"})
            seen.append(b)
    return out
