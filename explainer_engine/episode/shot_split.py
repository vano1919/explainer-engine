from __future__ import annotations
import copy
import re
from typing import Any
from explainer_engine.standards import sourced_rules as SR
MAX_STILL_S = 5.0
MIN_PART_S = 1.0
CUTIN_CROP = float(SR.T("BP-202", "subshot_cutin_crop"))  # Step 2 Fix (BP-202): never jump-cut 1.35x on sub-parts of the same still
DEFAULT_FOCUS = [0.5, 0.45]
CLAUSE_PUNCT = (".", ",", ";", ":", "!", "?", "—", "–", "…")
_TRAILING_QUOTES = "\"'”’)]}"
_WORD_NORM_RE = re.compile(r"[^\w']+", re.UNICODE)
SAFE_SPLIT_NEXT_WORDS = frozenset({
    "and", "but", "or", "nor", "yet", "so", "while", "where", "when", "before", "after", "until",
    "because", "though", "although", "since", "as", "across", "through", "under", "into", "from",
    "with", "without", "inside", "outside", "around", "along", "between", "against", "toward",
    "towards", "over", "in", "on", "at", "by", "for", "to", "that", "which", "who", "whom", "whose",
})
def _norm_word(token: str) -> str:
    return _WORD_NORM_RE.sub("", str(token).lower()).strip("'")
def _word_token(w: dict) -> str:
    tok = str(w.get("raw") or w.get("text") or w.get("word") or "").strip()
    punct = str(w.get("punct") or "").strip()
    if punct and not tok.endswith(punct):
        tok = tok + punct
    return tok
def is_clause_end(w: dict) -> bool:
    if bool(w.get("clause_end")):
        return True
    tok = _word_token(w).rstrip(_TRAILING_QUOTES)
    return bool(tok) and tok.endswith(CLAUSE_PUNCT)
def is_safe_word_boundary(words: list[dict], idx: int) -> bool:
    """True when splitting after ``words[idx]`` breaks before a conjunction, preposition, or relative clause starter."""
    if idx < 0 or idx + 1 >= len(words):
        return False
    nxt = _norm_word(words[idx + 1].get("word") or words[idx + 1].get("text") or "")
    return nxt in SAFE_SPLIT_NEXT_WORDS
def synthesize_word_spine(
    text: str | None,
    duration_s: float,
    *,
    fps: int = 24,
) -> list[dict]:
    """Synthesize a deterministic word-level timing spine from ``text`` and ``duration_s``.

    Used when pre-render script planning or ``split_long_still(shot, None)`` runs before
    Whisper ``audio/timing.json`` is generated, weighting word durations by character length
    plus natural clause-boundary pause weights (``.?!`` > ``:;—`` > ``,``).
    """
    tokens = [tok for tok in str(text or "").split() if tok.strip()]
    if not tokens or duration_s <= 0.0:
        return []
    weights: list[float] = []
    for tok in tokens:
        core_len = max(1, len(_norm_word(tok)))
        w = float(core_len) + 1.5
        clean = tok.rstrip(_TRAILING_QUOTES)
        if clean.endswith((".", "?", "!")):
            w += 2.6
        elif clean.endswith((":", ";", "—", "–", "…")):
            w += 1.8
        elif clean.endswith(","):
            w += 1.1
        weights.append(w)
    total_w = sum(weights) or 1.0
    cursor = 0.0
    out: list[dict] = []
    for idx, (tok, w) in enumerate(zip(tokens, weights)):
        dt = float(duration_s) * (w / total_w)
        t0 = cursor
        t1 = float(duration_s) if idx == len(tokens) - 1 else (cursor + dt)
        cursor = t1
        clean = tok.rstrip(_TRAILING_QUOTES)
        out.append({
            "word": tok,
            "text": tok,
            "start_s": round(t0, 4),
            "end_s": round(t1, 4),
            "start_frame": int(round(t0 * fps)),
            "end_frame": int(round(t1 * fps)),
            "clause_end": bool(clean and clean.endswith(CLAUSE_PUNCT)),
        })
    return out


def punctuate_spine(spine: list[dict] | None, text: str = "", *, duration_s: float | None = None, fps: int = 24) -> list[dict]:
    if not spine:
        if text and duration_s and float(duration_s) > 0.0:
            return synthesize_word_spine(text, float(duration_s), fps=fps)
        return []
    out = [dict(w) for w in spine]
    if not text or all(is_clause_end(w) for w in out):
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
                if not is_clause_end(w):
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
        for k in ("focus", "centre", "center", "point", "mouth", "where"):
            c = _centre(item.get(k))
            if c is not None:
                return c
        c = _centre(item.get("box") or item.get("bbox"))
        if c is not None:
            return c
        pts = item.get("points") or [p for part in (item.get("parts") or []) if isinstance(part, (list, tuple)) for p in part]
        if isinstance(pts, (list, tuple)) and pts and all(isinstance(p, (list, tuple)) and len(p) >= 2 for p in pts):
            return [round(sum(float(p[0]) for p in pts) / len(pts), 4), round(sum(float(p[1]) for p in pts) / len(pts), 4)]
    return None
def _resolve_focus(shot: dict, part_words: list[dict], full_words: list[dict], seen: dict | None = None) -> Any:
    d = seen if isinstance(seen, dict) else (shot.get("seen") if isinstance(shot.get("seen"), dict) else {})
    spoken = {_norm_word(w.get("word") or w.get("text") or "") for w in (part_words or full_words)}
    spoken.discard("")
    liv_raw = d.get("living")
    liv_list = list(liv_raw) if isinstance(liv_raw, list) else list((liv_raw or {}).get("parts") or []) if isinstance(liv_raw, dict) else []
    objs = [o for o in (list(d.get("objects") or []) + liv_list + list(shot.get("objects") or [])) if isinstance(o, dict)]
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
    liv_faces = list(liv_raw.get("faces") or []) if isinstance(liv_raw, dict) else []
    faces = (list(shot.get("people") or []) + list(shot.get("faces") or [])
             + list(d.get("people") or []) + list(d.get("faces") or [])
             + liv_faces)
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
                     fps: int | None = None, seen: dict | None = None,
                     allow_word_fallback: bool = True, text: str | None = None,
                     limit_s: float | None = None) -> list[dict]:
    if limit_s is not None:
        max_s = float(limit_s)
    route = shot.get("route") or shot.get("visual_kind")
    if route is not None and route != "still_25d":
        return [copy.deepcopy(shot)]
    words = list(spine or shot.get("spine") or [])
    sp_fps = int(fps or _shot_fps(shot, words))
    total_s = _shot_duration_s(shot, words, sp_fps)
    if not words and total_s > float(max_s) + 1e-9:
        raw_txt = str(text or shot.get("_spoken_text") or shot.get("narration_text") or "").strip()
        if raw_txt:
            words = synthesize_word_spine(raw_txt, total_s, fps=sp_fps)
    if total_s <= float(max_s) + 1e-9 or len(words) < 2:
        return [copy.deepcopy(shot)]
    total_frames = int(shot.get("total_frames") or shot.get("frames") or max(1, int(round(total_s * sp_fps))))
    eps = 1e-6
    t_of = lambda i: _word_end_s_at(words, i, sp_fps, total_s)
    def _clause_candidates(w_lo: int, w_hi: int, s_lo: float, s_hi: float) -> list[int]:
        out = []
        for i in range(w_lo, w_hi - 1):
            if is_clause_end(words[i]):
                t = t_of(i)
                if s_lo + eps < t < s_hi - eps:
                    out.append(i)
        return out
    def _word_candidates(w_lo: int, w_hi: int, s_lo: float, s_hi: float) -> list[int]:
        safe = []
        any_w = []
        for i in range(w_lo, w_hi - 1):
            t = t_of(i)
            if not (s_lo + eps < t < s_hi - eps):
                continue
            any_w.append(i)
            if is_safe_word_boundary(words, i) and (t - s_lo) >= MIN_PART_S - eps and (s_hi - t) >= MIN_PART_S - eps:
                safe.append(i)
        return safe or any_w
    memo: dict[tuple[int, int, bool], list[tuple[int, int, float, float]]] = {}
    def _all_ok(segs: list[tuple[int, int, float, float]]) -> bool:
        return all((b - a) <= float(max_s) + eps for _, _, a, b in segs)
    def _split_seg(w_lo: int, w_hi: int, s_lo: float, s_hi: float, use_fallback: bool = False) -> list[tuple[int, int, float, float]]:
        key = (w_lo, w_hi, use_fallback)
        if key in memo:
            return memo[key]
        if (s_hi - s_lo) <= float(max_s) + eps:
            res = [(w_lo, w_hi, s_lo, s_hi)]
            memo[key] = res
            return res
        cands = _clause_candidates(w_lo, w_hi, s_lo, s_hi)
        if not cands and use_fallback:
            cands = _word_candidates(w_lo, w_hi, s_lo, s_hi)
        if not cands:
            res = [(w_lo, w_hi, s_lo, s_hi)]
            memo[key] = res
            return res
        mid = 0.5 * (s_lo + s_hi)
        dist = lambda i: abs(t_of(i) - mid)
        tier1 = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps and (s_hi - t_of(i)) <= float(max_s) + eps]
        if tier1:
            pick = min(tier1, key=dist)
        else:
            tier2_l = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps
                       and _all_ok(_split_seg(i + 1, w_hi, t_of(i), s_hi, use_fallback))]
            tier2_r = [i for i in cands if (s_hi - t_of(i)) <= float(max_s) + eps
                       and _all_ok(_split_seg(w_lo, i + 1, s_lo, t_of(i), use_fallback))]
            if tier2_l:
                pick = min(tier2_l, key=dist)
            elif tier2_r:
                pick = min(tier2_r, key=dist)
            else:
                tier3 = [i for i in cands if _all_ok(_split_seg(w_lo, i + 1, s_lo, t_of(i), use_fallback))
                         and _all_ok(_split_seg(i + 1, w_hi, t_of(i), s_hi, use_fallback))]
                if tier3:
                    pick = min(tier3, key=lambda i: (len(_split_seg(w_lo, i + 1, s_lo, t_of(i), use_fallback))
                                                     + len(_split_seg(i + 1, w_hi, t_of(i), s_hi, use_fallback)), dist(i)))
                else:
                    legal_left = [i for i in cands if (t_of(i) - s_lo) <= float(max_s) + eps]
                    pick = min(legal_left or cands, key=dist)
        t_cut = t_of(pick)
        res = _split_seg(w_lo, pick + 1, s_lo, t_cut, use_fallback) + _split_seg(pick + 1, w_hi, t_cut, s_hi, use_fallback)
        memo[key] = res
        return res
    segs = _split_seg(0, len(words), 0.0, total_s, False)
    if allow_word_fallback and (len(segs) <= 1 or not _all_ok(segs)):
        segs = _split_seg(0, len(words), 0.0, total_s, True)
    if len(segs) <= 1:
        return [copy.deepcopy(shot)]
    k = len(segs)
    bounds_f = [0]
    for m in range(k - 1):
        _, w_hi_m, _, s_hi_m = segs[m]
        w_last = words[w_hi_m - 1]
        raw_f = int(w_last["end_frame"]) if w_last.get("end_frame") is not None else int(round(s_hi_m * sp_fps))
        if w_hi_m < len(words):
            w_next = words[w_hi_m]
            nxt_f = w_next.get("start_frame") if w_next.get("start_frame") is not None else w_next.get("frame")
            if nxt_f is not None:
                raw_f = min(raw_f, int(nxt_f))
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
        part["split_of"] = sid
        part["target_duration_seconds"] = p_dur
        part["duration_sec"] = p_dur
        part["frames"] = p_frames
        part["total_frames"] = p_frames
        part["start_frame"] = f_lo
        part["end_frame"] = f_hi
        part["start_s"] = round(s_lo, 4)
        part["end_s"] = round(s_hi, 4)
        part["word_range"] = [w_lo, w_hi]
        if idx < k - 1:
            part["transition_out"] = "hard_cut"
            part.pop("explicit_transition_override", None)
        part_words = []
        for pos, w in enumerate(words[w_lo:w_hi], start=w_lo):
            nw = dict(w)
            nw.setdefault("index", pos)
            ws = _word_start_s(w, sp_fps)
            we = t_of(pos)
            nw["start_s"] = round(max(0.0, ws - s_lo), 4)
            nw["end_s"] = round(max(0.0, min(p_dur, we - s_lo)), 4)
            sf_raw = w.get("start_frame") if w.get("start_frame") is not None else w.get("frame")
            if sf_raw is not None:
                nw["start_frame"] = max(0, int(sf_raw) - f_lo)
            else:
                nw["start_frame"] = max(0, int(round(nw["start_s"] * sp_fps)))
            if "frame" in nw:
                nw["frame"] = nw["start_frame"]
            if w.get("end_frame") is not None:
                nw["end_frame"] = min(p_frames, max(0, int(w["end_frame"]) - f_lo))
            else:
                nw["end_frame"] = min(p_frames, max(0, int(round(nw["end_s"] * sp_fps))))
            part_words.append(nw)
        if part_words:
            part_words[0]["_part_start_frame"] = f_lo
            part_words[0]["_part_end_frame"] = f_hi
            part_words[0]["_parent_frames"] = total_frames
            part_words[0]["_parent_spine"] = [dict(x) for x in words]
        part["duration_s"] = p_dur
        part["spine"] = part_words
        part["cut_word"] = _word_token(words[w_hi - 1]) if idx < k - 1 else None
        part_norm_words = {_norm_word(_word_token(w)) for w in words[w_lo:w_hi]}
        part_norm_words.discard("")
        part_excerpt = " ".join(_word_token(w) for w in words[w_lo:w_hi]).strip()
        if isinstance(part.get("motion_imitation"), list) and part_norm_words:
            kept_mi = []
            for mi in part["motion_imitation"]:
                if not isinstance(mi, dict):
                    continue
                at_w = _norm_word(str(mi.get("at_word") or ""))
                if at_w and at_w not in part_norm_words:
                    continue
                kept_mi.append(copy.deepcopy(mi))
            part["motion_imitation"] = kept_mi
        if isinstance(part.get("director_brief"), dict) and part_norm_words:
            pb = copy.deepcopy(part["director_brief"])
            fh = pb.get("focal_hierarchy")
            if isinstance(fh, dict) and isinstance(fh.get("timed_focal_shifts"), list):
                matched = [
                    shf for shf in fh["timed_focal_shifts"]
                    if isinstance(shf, dict) and _norm_word(str(shf.get("at_word") or "")) in part_norm_words
                ]
                if matched:
                    fh["primary_anchor"] = str(matched[-1].get("anchor") or fh.get("primary_anchor") or "center")
            part["director_brief"] = pb
        total_f = max(1, int(total_frames))
        base_amount = 0.09
        s0_cont = round(1.0 + base_amount * (f_lo / float(total_f)), 4)
        s1_cont = round(1.0 + base_amount * (f_hi / float(total_f)), 4)
        part["split_from"] = {
            "shot_id": sid,
            "part_index": idx,
            "part_count": k,
            "start_s": round(s_lo, 4),
            "end_s": round(s_hi, 4),
            "parent_start_frame": f_lo,
            "parent_end_frame": f_hi,
            "parent_total_frames": total_f,
            "start_scale": s0_cont,
            "end_scale": s1_cont,
            "cut_after_word": _word_token(words[w_hi - 1]) if w_hi > w_lo else "",
            "narration_excerpt": part_excerpt,
        }
        part["continuous_camera_slice"] = {
            "parent_shot_id": sid,
            "part_index": idx,
            "part_count": k,
            "parent_start_frame": f_lo,
            "parent_end_frame": f_hi,
            "parent_total_frames": total_f,
            "start_scale": s0_cont,
            "end_scale": s1_cont,
        }
        if idx >= 1:
            part["framing"] = {"crop": CUTIN_CROP, "focus": _resolve_focus(shot, words[w_lo:w_hi], words, seen=seen)}
        parts.append(part)
    return parts


def build_shot_split_plan(
    shot: dict[str, Any],
    spine: list[dict[str, Any]] | None = None,
    *,
    text: str | None = None,
    limit_s: float = MAX_STILL_S,
) -> dict[str, Any] | None:
    """Build a serialisable ``split_plan`` metadata block for a ``still_25d`` shot exceeding ``limit_s`` (BP-109)."""
    parts = split_long_still(shot, spine, max_s=limit_s, text=text)
    if len(parts) <= 1:
        return None
    return {
        "original_shot_id": str(shot.get("shot_id") or ""),
        "original_duration_s": round(float(shot.get("duration_s") or shot.get("target_duration_seconds") or 0.0), 3),
        "limit_s": float(limit_s),
        "part_count": len(parts),
        "parts": [
            {
                "part_shot_id": str(p.get("shot_id") or ""),
                "duration_s": round(float(p.get("duration_s") or p.get("duration_sec") or 0.0), 3),
                "start_s": float((p.get("split_from") or {}).get("start_s", 0.0)),
                "end_s": float((p.get("split_from") or {}).get("end_s", 0.0)),
                "cut_after_word": str((p.get("split_from") or {}).get("cut_after_word") or ""),
                "narration_excerpt": str((p.get("split_from") or {}).get("narration_excerpt") or ""),
                "framing": p.get("framing"),
                "transition_out": str(p.get("transition_out") or "hard_cut"),
            }
            for p in parts
        ],
    }


def build_continuous_camera_waypoints(shot: dict, spine: list[dict] | None = None, fps: int = 24) -> list[dict]:
    """Step 2 Fix: build a single continuous multi-waypoint camera pass over ``0..total_frames`` for a long 2.5D still.

    Instead of splitting a 6-10 s still into sub-clips ``a/b/c`` that each reset ``s=1.0, dp=0.0`` at their local
    frame 0, this function returns continuous camera segments over the full shot frame range ``[0, total_frames]``.
    """
    dur = float(shot.get("target_duration_seconds") or 0.0)
    total_frames = max(1, int(round(dur * fps)))
    existing_cams = list(shot.get("cameras") or [])
    if existing_cams:
        # Ensure segments cover [0, total_frames] monotonically without resetting zoom to 1.0 mid-shot
        out = []
        for idx, c in enumerate(existing_cams):
            seg = dict(c)
            seg.setdefault("start", 0 if idx == 0 else int(out[-1]["end"]))
            seg.setdefault("end", total_frames if idx == len(existing_cams) - 1 else min(total_frames, int(seg["start"]) + max(fps, total_frames // len(existing_cams))))
            out.append(seg)
        if out:
            out[-1]["end"] = total_frames
        return out

    brief = shot.get("director_brief") if isinstance(shot.get("director_brief"), dict) else {}
    fa = brief.get("focal_anchor") if isinstance(brief.get("focal_anchor"), dict) else {}
    box = fa.get("box_hint") if isinstance(fa.get("box_hint"), list) and len(fa.get("box_hint")) == 4 else [0.25, 0.20, 0.75, 0.85]
    cx = round(0.5 * (float(box[0]) + float(box[2])), 4)
    cy = round(0.5 * (float(box[1]) + float(box[3])), 4)
    cam_spec = shot.get("camera_spec") or {}
    move = str(cam_spec.get("camera_move") or "push_in").lower()
    op = "pull_back" if "pull" in move else ("crane_up" if "crane" in move or "tilt_up" in move else ("pan_crop_2d" if "pan" in move else "push_in"))
    return [{
        "op": op,
        "start": 0,
        "end": total_frames,
        "amount": 0.09 if op in ("push_in", "pull_back") else 0.06,
        "target": {"point": [cx, cy], "mask": str(fa.get("id") or "primary")},
        "continuous_single_pass": True,
    }]
