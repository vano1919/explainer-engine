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
import hashlib
import json
import re
from pathlib import Path

from explainer_engine.audio import scribe_words as SW
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.maps import actions as MA
from explainer_engine.standards import sourced_rules as SR

SCHEMA = "episode_timing/1"
SCHEMA_V2 = "episode_timing/2"
PAD_S = 0.25   # air kept after a line before a shot without a line takes over (house default, not a sourced rule)
BP201_HEAD_LEAD_S = float(SR.T("BP-201", "head_lead_s"))
BP201_TAIL_MIN_S = float(SR.T("BP-201", "reaction_tail_min_s"))
BP201_TAIL_TARGET_S = float(SR.T("BP-201", "reaction_tail_target_s"))
_STAGE_DIR_RE = re.compile(r"\([^()\n]*\)")


def strip_stage_directions(text: str) -> str:
    """TD-337 (Audit #21): strip parenthesized stage directions such as ``(Thomas does not answer...)`` and ElevenLabs tags."""
    cleaned = SW.strip_tags(str(text or ""))
    stripped = _STAGE_DIR_RE.sub(" ", cleaned)
    return re.sub(r"\s+", " ", stripped).strip()


def is_spoken_line(ln: dict | None) -> bool:
    """TD-337 (Audit #21): a line is spoken only when ``speaker_type != 'silent_beat'`` and its text after stripping tags
    and parenthesized stage directions still contains spoken words (unless it is the sole explicit test line)."""
    if not isinstance(ln, dict):
        return False
    if str(ln.get("speaker_type") or "").strip().lower() == "silent_beat":
        return False
    raw = SW.strip_tags(str(ln.get("text") or "")).strip()
    if raw.startswith("(") and raw.endswith(")"):
        return False
    return True


def read_order(script: dict) -> list[str]:
    """The line ids in the order the shots carry them (the order of the read). A line carried by two shots is a FAIL of the
    contract: the read has it once. The lines an LTX clip speaks itself (``videolane.plan.clip_spoken``, VL-07) and silent
    stage-direction beats (``speaker_type == 'silent_beat'`` or parenthesized stage directions, TD-337) are not in the read:
    their shots are timed by their trimmed clips or the pause they sit in."""
    from explainer_engine.videolane.plan import clip_spoken
    by_clip = clip_spoken(script)
    lines = {ln.get("line_id"): ln for ln in script.get("audio_lines", []) if ln.get("line_id")}
    out, seen = [], set()
    for s in script.get("shots", []):
        for lid in s.get("audio_line_ids") or []:
            if lid in seen:
                raise ContractError(f"line {lid} is carried by two shots; the read speaks it once")
            seen.add(lid)
            ln = lines.get(lid)
            if ln is not None and not is_spoken_line(ln):
                continue
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
    texts = [strip_stage_directions(str(lines[lid].get("text") or "")) for lid in order]
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
    """The episode clock when some shots are timed by their LTX clips (VL-07)."""
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


_ON_SCREEN_RE = re.compile(r"\(\s*on\s+screen\s*:\s*([^)]+?)\s*\)", re.I)


def extract_on_screen_text(shot: dict, script: dict) -> list[dict]:
    """Step 3 (Epilogue On-Screen Text): extract ``(on screen: ...)`` lines from silent_beat or audio_lines."""
    lines_by_id = {ln.get("line_id"): ln for ln in (script or {}).get("audio_lines", []) if isinstance(ln, dict)}
    out: list[dict] = []
    for lid in shot.get("audio_line_ids") or []:
        ln = lines_by_id.get(lid) or {}
        raw = str(ln.get("text") or "").strip()
        for m in _ON_SCREEN_RE.finditer(raw):
            caption = m.group(1).strip().strip('"')
            if caption:
                out.append({
                    "line_id": lid,
                    "speaker_type": ln.get("speaker_type", "silent_beat"),
                    "text": caption,
                    "fade_in_s": 0.8,
                    "fade_out_s": 1.0,
                })
    if shot.get("on_screen_text") and not out:
        out.append({
            "line_id": f"{shot.get('shot_id', 'shot')}_onscreen",
            "speaker_type": "silent_beat",
            "text": str(shot["on_screen_text"]).strip(),
            "fade_in_s": 0.8,
            "fade_out_s": 1.0,
        })
    return out


def compute_timing_id(timing_doc: dict) -> str:
    """Deterministic SHA-256 fingerprint of the episode clock so all downstream consumers verify they read ONE clock."""
    fps = int(timing_doc.get("fps") or 24)
    shots = timing_doc.get("shots") or {}
    canonical_shots = []
    for sid in sorted(shots.keys(), key=lambda k: (int(shots[k].get("start_frame", 0)), k)):
        sh = shots[sid]
        tc = sh.get("trim_contract") or {}
        canonical_shots.append({
            "shot_id": sid,
            "start_frame": int(sh.get("start_frame", 0)),
            "end_frame": int(sh.get("end_frame", int(sh.get("start_frame", 0)) + int(sh.get("frames", 0)))),
            "frames": int(sh.get("frames", 0)),
            "in_s": round(float(tc.get("in_s", sh.get("in_s", 0.0))), 4),
            "out_s": round(float(tc.get("out_s", sh.get("out_s", 0.0))), 4),
        })
    payload = json.dumps({
        "fps": fps,
        "total_frames": int(timing_doc.get("total_frames", 0)),
        "shots": canonical_shots,
    }, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _ordered_shots_from_script_and_timing(script: dict | None, timing_doc: dict) -> list[dict]:
    """Collect shots in canonical order from script['shots'], script['segments'], and any remaining timing_doc['shots']."""
    script = script or {}
    seen: set[str] = set()
    ordered: list[dict] = []
    for s in script.get("shots") or []:
        if isinstance(s, dict) and s.get("shot_id") and s["shot_id"] not in seen:
            seen.add(s["shot_id"])
            ordered.append(s)
    for seg in script.get("segments") or []:
        if not isinstance(seg, dict):
            continue
        seg_id = seg.get("id") or seg.get("segment_id")
        for s in seg.get("shots") or []:
            if isinstance(s, dict) and s.get("shot_id") and s["shot_id"] not in seen:
                s_copy = dict(s)
                if seg_id and not s_copy.get("segment_id"):
                    s_copy["segment_id"] = seg_id
                seen.add(s_copy["shot_id"])
                ordered.append(s_copy)
    t_shots = timing_doc.get("shots") or {}
    for sid in sorted(t_shots.keys(), key=lambda k: (int(t_shots[k].get("start_frame", 0)), k)):
        if sid not in seen:
            seen.add(sid)
            ordered.append({"shot_id": sid, "segment_id": t_shots[sid].get("segment_id")})
    return ordered


def retime_with_edit_points(
    timing_doc: dict,
    script: dict | None = None,
    edit_points_doc: dict | None = None,
    raw_durations: dict[str, float] | None = None,
) -> dict:
    """P0-1 Authoritative Film Clock: synchronize ``timing.json`` shot frame counts, start/end frames, segment windows,
    narrator offsets, dialogue positions, and map events with trimmed clips for ALL shots (both spoken inserts and
    non-insert video/render shots), and attach ``timing_id`` and ``render_epoch``."""
    doc = copy.deepcopy(timing_doc)
    script = script or {}
    fps = int(doc.get("fps") or 24)
    ep_clips = (
        edit_points_doc.get("clips")
        if isinstance(edit_points_doc, dict) and "clips" in edit_points_doc
        else edit_points_doc
    ) or {}
    raw_durations = raw_durations or {}
    shots_list = _ordered_shots_from_script_and_timing(script, doc)

    # Support both {"shot_id": ...} and {"shot": ...} in doc["inserts"]
    spoken_inserts: dict[str, dict] = {}
    for ins in doc.get("inserts", []) or []:
        if isinstance(ins, dict):
            ins_sid = ins.get("shot_id") or ins.get("shot")
            if ins_sid:
                spoken_inserts[ins_sid] = ins

    frame_deltas: dict[str, int] = {}
    for s in shots_list:
        sid = s["shot_id"]
        if sid not in doc.get("shots", {}):
            continue
        t_shot = doc["shots"][sid]
        old_frames = int(t_shot.get("frames", fps))
        ep = ep_clips.get(sid)
        if isinstance(ep, dict) and ep.get("retime_clock", True):
            t_in = float(ep.get("in_s", ep.get("in", 0.0)))
            if "frames" in ep and ep["frames"] is not None:
                new_frames = max(1, int(ep["frames"]))
                t_out = round(t_in + new_frames / fps, 4)
            elif "trim_duration_s" in ep and ep["trim_duration_s"] is not None:
                dur_s = float(ep["trim_duration_s"])
                new_frames = max(1, int(round(dur_s * fps)))
                t_out = float(ep.get("out_s", ep.get("out", round(t_in + dur_s, 4))))
            elif "in" in ep or "out" in ep or "in_s" in ep or "out_s" in ep:
                out_val = ep.get("out_s", ep.get("out", "end"))
                if out_val == "end" or out_val is None:
                    t_out = float(raw_durations.get(sid, t_in + old_frames / fps))
                else:
                    t_out = float(out_val)
                new_frames = max(1, int(round((t_out - t_in) * fps))) if t_out > t_in else old_frames
            else:
                new_frames = old_frames
                t_out = round(t_in + old_frames / fps, 4)

            if new_frames > 0:
                frame_deltas[sid] = new_frames - old_frames
                t_shot["frames"] = new_frames
                t_shot["seconds"] = round(new_frames / fps, 4)
                t_shot["duration_s"] = round(new_frames / fps, 4)
                t_shot["trim_contract"] = {
                    "in_s": round(t_in, 4),
                    "out_s": round(t_out, 4),
                    "trim_duration_s": round(new_frames / fps, 4),
                    "frames": new_frames,
                    "clip_path": str(ep.get("clip_path") or f"production/video/cut/{sid}.mp4"),
                    "head_lead_min_s": BP201_HEAD_LEAD_S,
                    "reaction_tail_min_s": BP201_TAIL_MIN_S,
                    "reaction_tail_target_s": BP201_TAIL_TARGET_S,
                    "single_trimmed_source": True,
                }
                if sid in spoken_inserts:
                    spoken_inserts[sid]["frames"] = new_frames
                    spoken_inserts[sid]["seconds"] = round(new_frames / fps, 4)

    # Recompute monotonic start_frame / end_frame across all shots, shift spines, and build downstream schedules
    cur_frame = 0
    read_cursor_frame = 0
    on_screen_map: dict[str, list[dict]] = {}
    narrator_offsets: list[dict] = []
    dialogue_positions: dict[str, dict] = {}
    map_events: dict[str, dict] = {}
    seg_bounds: dict[str, dict] = {}

    for s in shots_list:
        sid = s["shot_id"]
        if sid not in doc.get("shots", {}):
            continue
        t_shot = doc["shots"][sid]
        old_start = int(t_shot.get("start_frame", cur_frame))
        n_frames = int(t_shot["frames"])
        shift = cur_frame - old_start
        t_shot["start_frame"] = cur_frame
        t_shot["end_frame"] = cur_frame + n_frames
        t_shot["seconds"] = round(n_frames / fps, 4)
        t_shot["duration_s"] = round(n_frames / fps, 4)
        t_shot["start_s"] = round(cur_frame / fps, 4)
        t_shot["end_s"] = round((cur_frame + n_frames) / fps, 4)

        seg_id = s.get("segment_id") or t_shot.get("segment_id") or sid.split("_")[0]
        t_shot["segment_id"] = seg_id
        if seg_id not in seg_bounds:
            seg_bounds[seg_id] = {
                "segment_id": seg_id,
                "start_frame": cur_frame,
                "end_frame": cur_frame + n_frames,
                "frames": n_frames,
                "start_s": round(cur_frame / fps, 4),
                "end_s": round((cur_frame + n_frames) / fps, 4),
            }
        else:
            seg_bounds[seg_id]["end_frame"] = cur_frame + n_frames
            seg_bounds[seg_id]["frames"] = seg_bounds[seg_id]["end_frame"] - seg_bounds[seg_id]["start_frame"]
            seg_bounds[seg_id]["end_s"] = round((cur_frame + n_frames) / fps, 4)

        if sid in doc.get("spines", {}) and doc["spines"][sid] and shift != 0:
            for w in doc["spines"][sid]:
                if "frame" in w:
                    w["frame"] = int(w["frame"]) + shift
                if "start_frame" in w and w.get("timeline_absolute"):
                    w["start_frame"] = int(w["start_frame"]) + shift
                if "end_frame" in w and w.get("timeline_absolute"):
                    w["end_frame"] = int(w["end_frame"]) + shift

        is_insert = sid in spoken_inserts or t_shot.get("timed_by") == "clip"
        if is_insert:
            if sid in spoken_inserts:
                spoken_inserts[sid]["at_read_frame"] = read_cursor_frame
                spoken_inserts[sid]["timeline_start_frame"] = cur_frame
                spoken_inserts[sid]["timeline_end_frame"] = cur_frame + n_frames
            tc = t_shot.get("trim_contract") or {}
            dialogue_positions[sid] = {
                "shot_id": sid,
                "segment_id": seg_id,
                "start_frame": cur_frame,
                "end_frame": cur_frame + n_frames,
                "frames": n_frames,
                "start_s": round(cur_frame / fps, 4),
                "end_s": round((cur_frame + n_frames) / fps, 4),
                "at_read_frame": read_cursor_frame,
                "in_s": float(tc.get("in_s", 0.0)),
                "out_s": float(tc.get("out_s", round(n_frames / fps, 4))),
                "clip_path": tc.get("clip_path", f"production/video/cut/{sid}.mp4"),
            }
            narrator_offsets.append({
                "shot_id": sid,
                "segment_id": seg_id,
                "timeline_start_frame": cur_frame,
                "timeline_end_frame": cur_frame + n_frames,
                "read_start_frame": read_cursor_frame,
                "read_end_frame": read_cursor_frame,
                "paused_for_insert": True,
            })
        else:
            narrator_offsets.append({
                "shot_id": sid,
                "segment_id": seg_id,
                "timeline_start_frame": cur_frame,
                "timeline_end_frame": cur_frame + n_frames,
                "read_start_frame": read_cursor_frame,
                "read_end_frame": read_cursor_frame + n_frames,
                "paused_for_insert": False,
            })
            read_cursor_frame += n_frames

        route = str(s.get("route") or t_shot.get("route") or "")
        if route == "map" or s.get("map_spec") is not None:
            map_events[sid] = {
                "shot_id": sid,
                "segment_id": seg_id,
                "start_frame": cur_frame,
                "end_frame": cur_frame + n_frames,
                "frames": n_frames,
                "start_s": round(cur_frame / fps, 4),
                "end_s": round((cur_frame + n_frames) / fps, 4),
                "duration_s": round(n_frames / fps, 4),
            }

        ost = extract_on_screen_text(s, script)
        if ost:
            on_screen_map[sid] = ost
            t_shot["on_screen_text"] = ost
        cur_frame += n_frames

    doc["schema"] = SCHEMA_V2
    doc["total_frames"] = cur_frame
    doc["total_seconds"] = round(cur_frame / fps, 4)
    doc["segments"] = seg_bounds
    doc["narrator_offsets"] = narrator_offsets
    doc["dialogue_positions"] = dialogue_positions
    doc["map_events"] = map_events
    doc["on_screen_texts"] = on_screen_map
    doc["frame_deltas"] = frame_deltas
    doc["timing_id"] = compute_timing_id(doc)
    doc["render_epoch"] = f"epoch_{doc['timing_id']}"
    return doc


def persist_authoritative_clock(timing_doc: dict, path: Path) -> dict:
    """Persist the authoritative retimed clock atomically to ``path`` with ``timing_id`` and ``render_epoch``."""
    doc = copy.deepcopy(timing_doc)
    doc["schema"] = doc.get("schema") or SCHEMA_V2
    doc["timing_id"] = compute_timing_id(doc)
    doc["render_epoch"] = doc.get("render_epoch") or f"epoch_{doc['timing_id']}"
    write_json_atomic(Path(path), doc)
    return doc


def verify_clock_alignment(timing_doc: dict, consumer_record: dict) -> list[dict]:
    """Verify that a segment build, audio mix, or QA review record was produced against the exact authoritative clock."""
    findings: list[dict] = []
    expected_id = timing_doc.get("timing_id") or compute_timing_id(timing_doc)
    got_id = consumer_record.get("timing_id")
    if got_id != expected_id:
        findings.append({
            "rule": "BP-201",
            "status": "FAIL",
            "detail": f"clock mismatch: consumer timing_id={got_id!r} != authoritative timing_id={expected_id!r}",
        })
    expected_epoch = timing_doc.get("render_epoch")
    got_epoch = consumer_record.get("render_epoch")
    if expected_epoch and got_epoch and got_epoch != expected_epoch:
        findings.append({
            "rule": "BP-201",
            "status": "FAIL",
            "detail": f"render_epoch mismatch: consumer={got_epoch!r} != authoritative={expected_epoch!r}",
        })
    sid = consumer_record.get("shot_id")
    if sid and sid in (timing_doc.get("shots") or {}):
        t_shot = timing_doc["shots"][sid]
        if "frames" in consumer_record and int(consumer_record["frames"]) != int(t_shot["frames"]):
            findings.append({
                "rule": "BP-201",
                "status": "FAIL",
                "detail": f"{sid}: consumer frames={consumer_record['frames']} != authoritative frames={t_shot['frames']}",
            })
    return findings
