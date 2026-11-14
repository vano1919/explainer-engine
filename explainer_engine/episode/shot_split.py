"""Split a ``still_25d`` shot over 5.0 s at sentence or clause boundaries in its narration spine (BP-109, plan step 3 T7).

The script on disk (``story/production_script.json``) is never edited. ``stage_clips`` splits long ``still_25d`` shots in
memory at the narration word boundary nearest to the middle that falls on a sentence or clause end (punctuation in the spine
words), recursively until every part is at most ``max_s`` seconds. Cut-in parts keep the same start picture with a 1.35x crop
focused on the shot's named target or people centre and receive ``shot_id`` ``<id>a`` / ``<id>b`` (and ``<id>c`` when needed).
"""
from __future__ import annotations

import copy
import re
from typing import Any

MAX_STILL_S = 5.0                   # BP-109 (house, REVIEW): a still_25d shot holds for at most 5.0 s before a re-framing cut
CUTIN_CROP = 1.35                   # T7: part B reuses the start picture with a 1.35x cut-in on the focal point
DEFAULT_FOCUS = [0.5, 0.45]         # standard upper-centre people focus when no named target or face box is present
CLAUSE_PUNCT = (".", ",", ";", ":", "!", "?", "—", "–", "…")
_TRAILING_QUOTES = "\"'”’)]}"
_WORD_NORM_RE = re.compile(r"[^\w']+", re.UNICODE)


def _norm_word(token: str) -> str:
    return _WORD_NORM_RE.sub("", str(token).lower()).strip("'")


def _word_token(w: dict) -> str:
    tok = str(w.get("raw") or w.get("text") or w.get("word") or "").strip()
    punct = str(w.get("punct") or "").strip()
    if punct and not tok.endswith(punct):
        tok = tok + punct
    return tok


def is_clause_end(w: dict) -> bool:
    """True when spine word ``w`` ends a sentence or clause by its punctuation (or explicit ``clause_end`` flag)."""
    if bool(w.get("clause_end")):
        return True
    tok = _word_token(w).rstrip(_TRAILING_QUOTES)
    return bool(tok) and tok.endswith(CLAUSE_PUNCT)


def punctuate_spine(spine: list[dict] | None, text: str = "") -> list[dict]:
    """Return a copy of ``spine`` where words stripped of punctuation by alignment recover their trailing punctuation from
    ``text`` when ``text`` is given. Spine words that already carry punctuation keep it unchanged."""
    if not spine:
        return []
    out = [dict(w) for w in spine]
    if not text or any(is_clause_end(w) for w in out):
        return out
    raw_tokens = [t for t in str(text).split() if _norm_word(t)]
    if not raw_tokens:
        return out
    j = 0
    for w in out:
        target = _norm_word(w.get("word") or w.get("text") or "")
        if not target:
            continue
        for k in range(j, min(len(raw_tokens), j + 6)):
            if _norm_word(raw_tokens[k]) == target:
                w["word"] = raw_tokens[k]
                j = k + 1
                break
    return out


def _centre(item: Any) -> list[float] | None:
    if isinstance(item, (list, tuple)) and len(item) == 2 and all(isinstance(x, (int, float)) for x in item):
        return [round(float(item[0]), 4), round(float(item[1]), 4)]
    if isinstance(item, (list, tuple)) and len(item) == 4 and all(isinstance(x, (int, float)) for x in item):
        x0, y0, x1, y1 = (float(v) for v in item)
        return [round(0.5 * (x0 + x1), 4), round(0.5 * (y0 + y1), 4)]
    if isinstance(item, dict):
        for k in ("focus", "centre", "center", "point", "mouth"):
            c = _centre(item.get(k))
            if c is not None:
                return c
        c = _centre(item.get("box") or item.get("bbox"))
        if c is not None:
            return c
    return None


def _resolve_focus(shot: dict, part_words: list[dict], full_words: list[dict], seen: dict | None = None) -> Any:
    """Resolve ``<the shot's named target or people centre>`` for part B's cut-in framing."""
    d = seen if isinstance(seen, dict) else (shot.get("seen") if isinstance(shot.get("seen"), dict) else {})
    spoken = {_norm_word(w.get("word") or w.get("text") or "") for w in (part_words or full_words)}
    spoken.discard("")
    objs = list(d.get("objects") or []) + list((d.get("living") or {}).get("parts") or []) + list(shot.get("objects") or [])

    named = shot.get("named_target") if shot.get("named_target") is not None else shot.get("target")
    if named is not None:
        c = _centre(named)
        if c is not None:
            return c
        if isinstance(named, str) and named.strip():
            key = _norm_word(named)
            targets = shot.get("targets") if isinstance(shot.get("targets"), dict) else {}
            if named in targets and _centre(targets[named]) is not None:
                return _centre(targets[named])
            for o in objs:
                names = {_norm_word(n) for n in (o.get("names") or [])} | {_norm_word(o.get("id") or ""), _norm_word(o.get("name") or "")}
                if key and key in names:
                    oc = _centre(o)
                    if oc is not None:
                        return oc
            return named.strip()

    for o in objs:
        names = {_norm_word(n) for n in (o.get("names") or [])} | {_norm_word(o.get("id") or ""), _norm_word(o.get("name") or "")}
        names.discard("")
        if spoken & names:
            oc = _centre(o)
            if oc is not None:
                return oc

    for k in ("people_centre", "people_center", "focus"):
        c = _centre(shot.get(k))
        if c is not None:
            return c
    if isinstance(shot.get("camera_spec"), dict):
        c = _centre(shot["camera_spec"].get("focus"))
        if c is not None:
            return c
    if isinstance(shot.get("framing"), dict):
        c = _centre(shot["framing"].get("focus"))
        if c is not None:
            return c
    faces = (list(shot.get("people") or []) + list(shot.get("faces") or [])
             + list(d.get("people") or []) + list(d.get("faces") or [])
             + list((d.get("living") or {}).get("faces") or []))
    pts = [p for p in (_centre(f) for f in faces) if p is not None]
    if pts:
        return [round(sum(p[0] for p in pts) / len(pts), 4), round(sum(p[1] for p in pts) / len(pts), 4)]
    return list(DEFAULT_FOCUS)


def _shot_fps(shot: dict, spine: list[dict] | None) -> int:
    if shot.get("fps"):
        return int(shot["fps"])
    if spine:
        for w in spine:
            if w.get("end_frame") and w.get("end_s") and float(w["end_s"]) > 0:
                return max(1, int(round(int(w["end_frame"]) / float(w["end_s"]))))
    return 24


def _shot_duration_s(shot: dict, spine: list[dict] | None, fps: int) -> float:
    for k in ("target_duration_seconds", "duration_sec", "duration_s", "seconds"):
        if shot.get(k) is not None:
            return float(shot[k])
    if shot.get("total_frames") is not None or shot.get("frames") is not None:
        return float(shot.get("total_frames") or shot["frames"]) / float(fps)
    if spine:
        return max(float(w.get("end_s") if w.get("end_s") is not None else (float(w.get("end_frame", 0)) / fps)) for w in spine)
    return 0.0


def _word_start_s(w: dict, fps: int) -> float:
    if w.get("start_s") is not None:
        return float(w["start_s"])
    if w.get("start") is not None:
        return float(w["start"])
    if w.get("start_frame") is not None:
        return float(w["start_frame"]) / float(fps)
    return 0.0


def _word_end_s_at(words: list[dict], idx: int, fps: int, total_s: float) -> float:
    w = words[idx]
    if w.get("end_s") is not None:
        return float(w["end_s"])
    if w.get("end") is not None:
        return float(w["end"])
    if w.get("end_frame") is not None:
        return float(w["end_frame"]) / float(fps)
    if idx + 1 < len(words):
        nxt = _word_start_s(words[idx + 1], fps)
        if nxt > 0.0:
            return nxt
    return float((idx + 1) * total_s / max(1, len(words)))


def split_long_still(shot: dict, spine: list[dict] | None, max_s: float = MAX_STILL_S, *,
                     fps: int | None = None, seen: dict | None = None) -> list[dict]:
    """Split a ``still_25d`` shot longer than ``max_s`` at the narration word boundary nearest to the middle that falls on a
    sentence or clause end (punctuation in ``spine``), recursively until every part is ``<= max_s``."""
    route = shot.get("route")
    if route is not None and route != "still_25d":
        return [copy.deepcopy(shot)]
    words = list(spine or shot.get("spine") or [])
    sp_fps = int(fps or _shot_fps(shot, words))
    total_s = _shot_duration_s(shot, words, sp_fps)
    if total_s <= float(max_s) + 1e-9 or len(words) < 2:
        return [copy.deepcopy(shot)]
    total_frames = int(shot.get("total_frames") or shot.get("frames") or max(1, int(round(total_s * sp_fps))))
    eps = 1e-6
    t_of = lambda i: _word_end_s_at(words, i, sp_fps, total_s)  # noqa: E731

    def _candidates(w_lo: int, w_hi: int, s_lo: float, s_hi: float) -> list[int]:
        out = []
        for i in range(w_lo, w_hi - 1):
            if is_clause_end(words[i]):
                t = t_of(i)
                if s_lo + eps < t < s_hi - eps:
                    out.append(i)
        return out

    memo: dict[tuple[int, int], list[tuple[int, int, float, float]]] = {}

    def _split_seg(w_lo: int, w_hi: int, s_lo: float, s_hi: float) -> list[tuple[int, int, float, float]]:
        key = (w_lo, w_hi)
        if key in memo:
            return memo[key]
        if (s_hi - s_lo) <= float(max_s) + eps:
            res = [(w_lo, w_hi, s_lo, s_hi)]
            memo[key] = res
            return res
        cands = _candidates(w_lo, w_hi, s_lo, s_hi)
        if not cands:
            res = [(w_lo, w_hi, s_lo, s_hi)]
            memo[key] = res
            return res
        mid = 0.5 * (s_lo + s_hi)
        dist = lambda i: abs(t_of(i) - mid)  # noqa: E731

        def _all_ok(segs: list[tuple[int, int, float, float]]) -> bool:
            return all((b - a) <= float(max_s) + eps for _, _, a, b in segs)

        tier1 = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps and (s_hi - t_of(i)) <= float(max_s) + eps]
        if tier1:
            pick = min(tier1, key=dist)
        else:
            tier2_l = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps
                       and _all_ok(_split_seg(i + 1, w_hi, t_of(i), s_hi))]
            tier2_r = [i for i in cands if (s_hi - t_of(i)) <= float(max_s) + eps
                       and _all_ok(_split_seg(w_lo, i + 1, s_lo, t_of(i)))]
            if tier2_l:
                pick = min(tier2_l, key=dist)
            elif tier2_r:
                pick = min(tier2_r, key=dist)
            else:
                tier3 = [i for i in cands if _all_ok(_split_seg(w_lo, i + 1, s_lo, t_of(i)))
                         and _all_ok(_split_seg(i + 1, w_hi, t_of(i), s_hi))]
                if tier3:
                    pick = min(tier3, key=lambda i: (len(_split_seg(w_lo, i + 1, s_lo, t_of(i)))
                                                     + len(_split_seg(i + 1, w_hi, t_of(i), s_hi)), dist(i)))
                else:
                    legal_left = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps]
                    pick = min(legal_left or cands, key=dist)

        t_cut = t_of(pick)
        res = _split_seg(w_lo, pick + 1, s_lo, t_cut) + _split_seg(pick + 1, w_hi, t_cut, s_hi)
        memo[key] = res
        return res

    segs = _split_seg(0, len(words), 0.0, total_s)
    if len(segs) <= 1:
        return [copy.deepcopy(shot)]

    k = len(segs)
    bounds_f = [0]
    for m in range(k - 1):
        _, w_hi_m, _, s_hi_m = segs[m]
        w_last = words[w_hi_m - 1]
        raw_f = int(w_last["end_frame"]) if w_last.get("end_frame") is not None else int(round(s_hi_m * sp_fps))
        lo_f = bounds_f[-1] + 1
        hi_f = total_frames - (k - 1 - m)
        bounds_f.append(max(lo_f, min(hi_f, raw_f)))
    bounds_f.append(total_frames)

    sid = str(shot.get("shot_id") or "shot")
    parts: list[dict] = []
    for idx, (w_lo, w_hi, s_lo, s_hi) in enumerate(segs):
        f_lo, f_hi = bounds_f[idx], bounds_f[idx + 1]
        p_frames = f_hi - f_lo
        p_dur = round(s_hi - s_lo, 4)
        part = copy.deepcopy(shot)
        part["shot_id"] = f"{sid}{chr(ord('a') + idx)}"
        part["parent_shot_id"] = sid
        part["target_duration_seconds"] = p_dur
        part["duration_sec"] = p_dur
        part["frames"] = p_frames
        part["total_frames"] = p_frames
        part["start_frame"] = f_lo
        part["end_frame"] = f_hi
        part["start_s"] = round(s_lo, 4)
        part["end_s"] = round(s_hi, 4)
        part["word_range"] = [w_lo, w_hi]
        part_words = []
        for pos, w in enumerate(words[w_lo:w_hi], start=w_lo):
            nw = dict(w)
            nw.setdefault("index", pos)
            ws = _word_start_s(w, sp_fps)
            we = t_of(pos)
            nw["start_s"] = round(max(0.0, ws - s_lo), 4)
            nw["end_s"] = round(max(0.0, min(p_dur, we - s_lo)), 4)
            if w.get("start_frame") is not None:
                nw["start_frame"] = max(0, int(w["start_frame"]) - f_lo)
            else:
                nw["start_frame"] = max(0, int(round(nw["start_s"] * sp_fps)))
            if w.get("end_frame") is not None:
                nw["end_frame"] = min(p_frames, max(0, int(w["end_frame"]) - f_lo))
            else:
                nw["end_frame"] = min(p_frames, max(0, int(round(nw["end_s"] * sp_fps))))
            part_words.append(nw)
        part["spine"] = part_words
        part["cut_word"] = _word_token(words[w_hi - 1]) if idx < k - 1 else None
        if idx >= 1:
            part["framing"] = {"crop": CUTIN_CROP, "focus": _resolve_focus(shot, words[w_lo:w_hi], words, seen=seen)}
        parts.append(part)
    return parts
