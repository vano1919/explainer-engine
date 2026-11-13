"""The voice stage's clock (v4.3 plan section 4, G6; RN-03 in docs/EPISODE_FIRST.md): the episode's real read, its Scribe
transcript aligned to the script's lines, and from it the measured length of every shot.

The read is ONE file, the lines in the order the shots carry them. Every line's words get the transcript's times
(``audio/scribe_words.align``: the written words, the heard times). A cut between two shots that both carry a line falls in
the middle of the pause between the two lines; shots without a line share the pause they sit in by their planned lengths, and
the line next to them keeps ``PAD_S`` of air (at most a quarter of the pause). The shots then tile the read exactly, frame by
frame, and each shot's word spine (``[{word, start_frame}]``, shot-relative, in the tokens ``maps/actions.shot_words`` counts)
is what the map actions, the 2.5D accents and the sound events start on (``word_basis: measured``).

Nothing in the script is edited: ``audio/timing.json`` holds the measured lengths and ``timed_script`` applies them to a copy.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

from explainer_engine.audio import scribe_words as SW
from explainer_engine.core.errors import ContractError
from explainer_engine.maps import actions as MA

SCHEMA = "episode_timing/1"
PAD_S = 0.25   # air kept after a line before a shot without a line takes over (house default, not a sourced rule)


def read_order(script: dict) -> list[str]:
    """The line ids in the order the shots carry them (the order of the read). A line carried by two shots is a FAIL of the
    contract: the read has it once. The lines an LTX clip speaks itself (``videolane.plan.clip_spoken``, VL-07) are not in
    the read: their shots are timed by their trimmed clips (``retime_with_clips``)."""
    from explainer_engine.videolane.plan import clip_spoken
    by_clip = clip_spoken(script)
    out, seen = [], set()
    for s in script.get("shots", []):
        for lid in s.get("audio_line_ids") or []:
            if lid in seen:
                raise ContractError(f"line {lid} is carried by two shots; the read speaks it once")
            seen.add(lid)
            if s["shot_id"] not in by_clip:
                out.append(lid)
    return out


def align_read(script: dict, transcript, duration: float | None = None) -> dict:
    """Every line's written words with the heard times: ``{"lines": {line_id: [{w, s, e[, estimated]}]}, "coverage",
    "status", "unmatched"}``. Each line is one paragraph of the text handed to the aligner."""
    lines = {ln["line_id"]: ln for ln in script.get("audio_lines", [])}
    order = read_order(script)
    missing = [lid for lid in order if lid not in lines]
    if missing:
        raise ContractError(f"{len(missing)} line id(s) of the shots are not in audio_lines: {missing[:5]}")
    texts = [re.sub(r"\s+", " ", SW.strip_tags(str(lines[lid].get("text") or ""))).strip() for lid in order]
    empty = [lid for lid, t in zip(order, texts) if not t]
    if empty:
        raise ContractError(f"line(s) without words cannot be timed: {empty[:5]}")
    res = SW.align("\n".join(texts), SW.transcript_words(transcript), duration)
    by_line: dict[str, list] = {lid: [] for lid in order}
    for w in res["words"]:
        by_line[order[w["para"]]].append(w)
    return {"lines": by_line, "order": order, "coverage": res["coverage"], "status": res["status"],
            "unmatched": res["unmatched"]}


def _line_span(words: list[dict]) -> tuple[float, float]:
    return words[0]["s"], words[-1]["e"]


def retime(script: dict, aligned: dict, fps: int, read_s: float) -> dict:
    """The measured shot lengths (see the module text) and the per-shot word spines."""
    shots = script.get("shots", [])
    if not shots:
        raise ContractError("a script without shots has nothing to time")
    span = {}
    for s in shots:
        ws = [w for lid in s.get("audio_line_ids") or [] for w in aligned["lines"].get(lid, [])]
        span[s["shot_id"]] = _line_span(ws) if ws else None
    if all(v is None for v in span.values()):
        raise ContractError("no shot carries a line: nothing to time the shots by")
    n = len(shots)
    lined = [span[s["shot_id"]] is not None for s in shots]
    starts: list[float] = [0.0] * n
    for k in range(n - 1):   # two lines side by side: the cut in the middle of the pause between them
        if lined[k] and lined[k + 1]:
            e, s2 = span[shots[k]["shot_id"]][1], span[shots[k + 1]["shot_id"]][0]
            starts[k + 1] = (e + s2) / 2.0 if s2 > e else e
    i = 0
    while i < n:   # a run of shots without a line [i, j) shares the pause it sits in by the planned lengths
        if lined[i]:
            i += 1
            continue
        j = i
        while j < n and not lined[j]:
            j += 1
        left = span[shots[i - 1]["shot_id"]][1] if i > 0 else 0.0
        right = span[shots[j]["shot_id"]][0] if j < n else read_s
        gap = max(0.0, right - left)
        a = left + (min(PAD_S, gap / 4.0) if i > 0 else 0.0)
        b = right - (min(PAD_S, gap / 4.0) if j < n else 0.0)
        planned = [float(shots[k].get("target_duration_seconds") or 1.0) for k in range(i, j)]
        tot = sum(planned)
        if i > 0:
            starts[i] = a
        t = a
        for k in range(i, j - 1):
            t += (b - a) * planned[k - i] / tot
            starts[k + 1] = t
        if j < n:
            starts[j] = b
        i = j
    frames_at = [int(round(c * fps)) for c in starts] + [int(round(read_s * fps))]
    for k in range(1, len(frames_at)):   # every shot keeps at least one frame
        frames_at[k] = max(frames_at[k], frames_at[k - 1] + 1)
    out_shots, spines = {}, {}
    for k, s in enumerate(shots):
        sid = s["shot_id"]
        a, b = frames_at[k], frames_at[k + 1]
        out_shots[sid] = {"start_frame": a, "frames": b - a, "seconds": round((b - a) / fps, 4),
                          "planned_seconds": float(s.get("target_duration_seconds") or 0.0)}
        sp = []
        for lid in s.get("audio_line_ids") or []:
            for w in aligned["lines"].get(lid, []):
                for tok in MA._words(w["w"]):
                    sp.append({"word": tok, "start_frame": max(0, int(round(w["s"] * fps)) - a),
                               "estimated": bool(w.get("estimated"))})
        want = MA.shot_words(s, script)
        if [x["word"] for x in sp] != want:
            raise ContractError(f"{sid}: the timed words {len(sp)} differ from the shot's words {len(want)} "
                                "(the line text changed after the read?)")
        spines[sid] = sp
    late = [sid for sid, s in out_shots.items() if span[sid] is not None and
            span[sid][1] * fps > s["start_frame"] + s["frames"] + 1]
    if late:
        raise ContractError(f"internal: line(s) run past their shot: {late[:5]}")
    return {"schema": SCHEMA, "fps": fps, "read_s": round(read_s, 4), "total_frames": frames_at[-1], "shots": out_shots,
            "spines": spines, "coverage": aligned["coverage"], "alignment_status": aligned["status"],
            "unmatched": aligned["unmatched"][:50]}


def clip_spine(script: dict, shot: dict, speech: list, fps: int) -> list[dict]:
    """A clip-timed shot's word spine (VL-07): its line's words spread over the speech the clip's own sound holds (trimmed-
    clip seconds), every word marked estimated (no aligner ran on the clip)."""
    words = MA.shot_words(shot, script)
    if not words:
        return []
    spans = [(float(a), float(b)) for a, b in speech or []] or [(0.0, float(shot.get("target_duration_seconds") or 1.0))]
    total = sum(b - a for a, b in spans) or 1.0
    out, k = [], 0
    for a, b in spans:
        n = len(words) - k if (a, b) == spans[-1] else int(round(len(words) * (b - a) / total))
        for i in range(n):
            if k >= len(words):
                break
            out.append({"word": words[k], "start_frame": int(round((a + (b - a) * i / max(1, n)) * fps)), "estimated": True})
            k += 1
    while k < len(words):
        out.append({"word": words[k], "start_frame": int(round(spans[-1][1] * fps)), "estimated": True})
        k += 1
    return out


def retime_with_clips(script: dict, aligned: dict | None, fps: int, read_s: float, clips: dict) -> dict:
    """The episode clock when some shots are timed by their LTX clips (VL-07). ``clips``: ``{shot_id: {"frames": n,
    "speech": [[s, e], ...]}}`` for every clip-timed shot (trimmed clip, its own speech in clip seconds). The read times the
    other shots exactly as ``retime`` does; each clip-timed shot is then inserted at the read's cut where it sits, so the read
    pauses for it (``inserts``: where the voice track splits the read, ``videolane/voice``). Without any read line the shots
    without a clip keep their planned lengths."""
    by_clip = [s["shot_id"] for s in script.get("shots", []) if s["shot_id"] in clips]
    missing = sorted(set(clips) - {s["shot_id"] for s in script.get("shots", [])})
    if missing:
        raise ContractError(f"clip timings for shots the script does not have: {missing[:5]}")
    read_shots = [s for s in script.get("shots", []) if s["shot_id"] not in clips]
    has_read = aligned is not None and any(aligned["lines"].get(lid) for s in read_shots for lid in s.get("audio_line_ids") or [])
    if has_read:
        base = retime(dict(script, shots=read_shots), aligned, fps, read_s)
    else:
        base, t = {"shots": {}, "spines": {}, "total_frames": 0, "coverage": None, "alignment_status": None,
                   "unmatched": []}, 0
        for s in read_shots:
            n = max(1, int(round(float(s.get("target_duration_seconds") or 1.0) * fps)))
            base["shots"][s["shot_id"]] = {"start_frame": t, "frames": n, "seconds": round(n / fps, 4),
                                           "planned_seconds": float(s.get("target_duration_seconds") or 0.0)}
            base["spines"][s["shot_id"]] = []
            t += n
        base["total_frames"] = t
    out_shots, spines, inserts, shift = {}, {}, [], 0
    order = script.get("shots", [])
    for k, s in enumerate(order):
        sid = s["shot_id"]
        if sid in clips:
            nxt = next((o["shot_id"] for o in order[k + 1:] if o["shot_id"] not in clips), None)
            at = base["shots"][nxt]["start_frame"] if nxt else base["total_frames"]
            n = int(clips[sid]["frames"])
            if n < 1:
                raise ContractError(f"{sid}: a clip-timed shot without frames")
            out_shots[sid] = {"start_frame": at + shift, "frames": n, "seconds": round(n / fps, 4),
                              "planned_seconds": float(s.get("target_duration_seconds") or 0.0), "timed_by": "clip"}
            spines[sid] = clip_spine(script, s, clips[sid].get("speech"), fps)
            inserts.append({"shot_id": sid, "at_read_frame": at, "frames": n})
            shift += n
        else:
            b = base["shots"][sid]
            out_shots[sid] = dict(b, start_frame=b["start_frame"] + shift)
            spines[sid] = base["spines"].get(sid, [])
    starts = [out_shots[s["shot_id"]]["start_frame"] for s in order]
    if any(b < a for a, b in zip(starts, starts[1:])):
        raise ContractError("internal: clip-timed shots broke the shot order")
    return {"schema": SCHEMA, "fps": fps, "read_s": round(read_s, 4), "total_frames": base["total_frames"] + shift,
            "shots": out_shots, "spines": spines, "inserts": inserts, "clip_timed": by_clip,
            "coverage": base.get("coverage"), "alignment_status": base.get("alignment_status"),
            "unmatched": base.get("unmatched", [])[:50]}


def timed_script(script: dict, timing: dict | None) -> dict:
    """A copy of the script with every shot's measured length (``timing`` None: the script as planned, a copy)."""
    doc = copy.deepcopy(script)
    if timing is None:
        return doc
    for s in doc.get("shots", []):
        t = timing["shots"].get(s["shot_id"])
        if t is None:
            raise ContractError(f"{s['shot_id']} has no measured length in audio/timing.json (the script changed after G6?)")
        s["target_duration_seconds"] = round(t["frames"] / timing["fps"], 6)
    return doc


def spines_of(timing: dict | None) -> dict:
    """``{shot_id: [{word, start_frame}]}`` for the shots with a line (the measured spine)."""
    if timing is None:
        return {}
    return {sid: [{"word": w["word"], "start_frame": w["start_frame"]} for w in sp]
            for sid, sp in timing["spines"].items() if sp}


def load(root: Path) -> dict | None:
    p = Path(root) / "audio" / "timing.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None
