"""The shot edit plan of the video lane (VL-01..VL-09, docs/VIDEO_LANE.md, D-137): how every LTX shot joins the shot before,
written in the shot itself (``edit_plan``, schema ``production_script``) BEFORE any paid clip, and checked here.

Why: the 2026-11-12 battle scene had four good clips that did not cut together (sky, ground, helmet and shield changed
across cut 1, the cut fell on dead air, the first line started 0.75 s into its clip). A shot that knows its continuity mode,
its camera state at both ends, its axis side, where its one line sits in the clip and how much clean picture it keeps can be
generated for the cut instead of being rescued after it.

Three continuity modes, never one strategy for every cut:

* ``continuation``: the same action goes on. The clip is generated from a chosen frame of the clip before (our self-hosted
  LTX-2.5 distilled CLI takes only a frame-0 picture and has no extend or retake, so the frame is the hand-over; VL-05).
  Screen direction, camera motion and the place carry over.
* ``coverage``: a new angle on the same scene, drawn fresh from the scene master and the hero sheets (CT-03), never from
  the previous clip's last frame. Size or angle changes by a step (CT-07), the axis side holds (CT-06) and every shared
  character keeps their screen side.
* ``insert``: a reaction, hand, object or detail. Usually ``still_25d``; never a speaking close-up.

The clip's length comes from its line, never a fixed 10 s (VL-06): onset + the line + BP-187's tail + the handles.
"""
from __future__ import annotations

from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

MODES = ("continuation", "coverage", "insert")
SIZES = ("extreme_wide", "wide", "medium_wide", "medium", "over_the_shoulder", "medium_close_up", "close_up",
         "extreme_close_up")
SIZE_STEP = {"extreme_wide": 0, "wide": 1, "medium_wide": 2, "medium": 3, "over_the_shoulder": 3, "medium_close_up": 4,
             "close_up": 5, "extreme_close_up": 6}
SPEAKING_CLOSE = ("close_up", "extreme_close_up")   # the creator 2026-11-12 20:37 UTC: weak mouths, no speaking close-up
MOVING = ("push", "pull", "pan_left", "pan_right", "tilt_up", "tilt_down", "track_left", "track_right")
SPEECH_ONSET_S = 0.75        # measured: LTX-2.5 starts the line about 0.75 s into a clip (battle scene, 2026-11-12); house
WORDS_PER_S = 2.6            # engineering default for a line without an estimate (conversational English, ~155 wpm)
TAIL_S = float(SR.T("BP-187", "speech_tail_s"))
HEAD_LEAD = SR.T("BP-190", "head_lead_s")
CUT_TAIL = SR.T("BP-190", "tail_s")
MIN_CLIP_S = 2.0             # engineering default: LTX needs a few seconds to settle a motion
DIALOGUE_RUN_MAX = 3         # VL-08: more lines in a row than this without a reaction or insert = REVIEW (ED-14's 2nd-4th line)


def is_video(shot: dict) -> bool:
    return shot.get("route") in ("video", "wan")


def _lines(script: dict) -> dict:
    return {ln["line_id"]: ln for ln in script.get("audio_lines", [])}


def clip_spoken(script: dict) -> set[str]:
    """The video shots whose every line is a character's line: the clip speaks them (D-132), so the narrator's read does not
    and the shot's length comes from the trimmed clip (VL-07)."""
    lines = _lines(script)
    out = set()
    for s in script.get("shots", []):
        ids = s.get("audio_line_ids") or []
        if is_video(s) and ids and all(lines.get(i, {}).get("speaker_type") == "character" for i in ids):
            out.add(s["shot_id"])
    return out


def line_seconds(script: dict, shot: dict, speaker_type: str | None = None) -> float:
    """The planned speaking time of the shot's lines (only those of ``speaker_type`` when given): their estimate, else their
    words at WORDS_PER_S."""
    lines = _lines(script)
    t = 0.0
    for lid in shot.get("audio_line_ids") or []:
        ln = lines.get(lid) or {}
        if speaker_type and ln.get("speaker_type") != speaker_type:
            continue
        est = ln.get("estimated_duration_seconds")
        t += float(est) if est else max(0.6, len(str(ln.get("text") or "").split()) / WORDS_PER_S)
    return t


MEASURED_BASES = ("measured_length", "measured_line")   # Q4 (D-138): the bases that come from a real read


def clip_seconds(script: dict, shot: dict, max_s: float, measured_s: float | None = None,
                 measured_line_s: float | None = None) -> dict:
    """VL-06: the seconds to generate for one video shot. A clip-spoken shot (it carries a character line, which LTX speaks):
    onset + its line + BP-187's tail + the tail handle (the head handle lies inside the onset: LTX speaks late anyway). A
    narrated or silent shot (the narrator's read lies over it, the clip says nothing; Fable audit FA-01): its length + both
    handles, where the length is the measured shot of the read when ``measured_s`` is given (FA-15: ``basis``
    ``measured_length``) and the planned length otherwise. Rounded up to 0.25 s, at least MIN_CLIP_S, at most the model's
    ``max_s``; ``over`` says when the plan does not fit. A clip-spoken shot whose line was read first (TTS or a recording,
    ``videolane.line_reads``; Q4, D-138) uses that measured speech (``measured_line_s``, basis ``measured_line``) instead of
    the estimate."""
    ep = shot.get("edit_plan") or {}
    head = float(ep.get("head_handle_s", 0.0))
    tail = float(ep.get("tail_handle_s", float(CUT_TAIL[1])))
    speak = line_seconds(script, shot, "character")
    if speak > 0:
        onset = float(ep.get("speech_onset_s", SPEECH_ONSET_S))
        basis = "line"
        if measured_line_s is not None:
            speak, basis = float(measured_line_s), "measured_line"
        need = max(onset, head) + speak + TAIL_S + tail
    elif measured_s is not None:
        need = head + float(measured_s) + tail
        basis = "measured_length"
    else:
        need = head + float(shot.get("target_duration_seconds") or 0.0) + tail
        basis = "planned_length"
    sec = max(MIN_CLIP_S, -(-need * 4 // 1) / 4.0)
    return {"seconds": min(sec, max_s), "needed_s": round(need, 3), "over": sec > max_s + 1e-9, "basis": basis,
            "speech_s": round(speak, 3)}


def scenes(script: dict) -> list[list[dict]]:
    """Consecutive shots of one segment and one place are one scene."""
    out: list[list[dict]] = []
    for s in script.get("shots", []):
        if out and out[-1][-1].get("segment_id") == s.get("segment_id") \
                and out[-1][-1].get("location_id") == s.get("location_id"):
            out[-1].append(s)
        else:
            out.append([s])
    return out


def _f(rule, sid, severity, detail) -> dict:
    return {"rule": rule, "shot_id": sid, "severity": severity, "detail": detail}


def findings(script: dict, max_s: float = 10.0) -> list[dict]:
    """Every VL-01..VL-08 finding of the script's video shots (and of the shots cut against them)."""
    out: list[dict] = []
    lines = _lines(script)
    spoken = clip_spoken(script)
    ids = {s["shot_id"] for s in script.get("shots", [])}
    for scene in scenes(script):
        run = 0
        for k, s in enumerate(scene):
            sid = s["shot_id"]
            prev = scene[k - 1] if k else None
            # the last earlier shot of the scene that set the axis side / the screen positions (an insert between two
            # coverage shots does not reset them)
            axis_at = next(({"shot_id": o["shot_id"], "axis_side": o["edit_plan"]["axis_side"]} for o in reversed(scene[:k])
                            if (o.get("edit_plan") or {}).get("axis_side")), None)
            pos_at = next(({"shot_id": o["shot_id"], "screen_positions": o["edit_plan"]["screen_positions"]}
                           for o in reversed(scene[:k]) if (o.get("edit_plan") or {}).get("screen_positions")), None)
            ep = s.get("edit_plan")
            has_line = bool(s.get("audio_line_ids"))
            character_line = any(lines.get(i, {}).get("speaker_type") == "character" for i in s.get("audio_line_ids") or [])
            run = run + 1 if character_line else (0 if (ep or {}).get("continuity_mode") == "insert"
                                                  or s.get("shot_role") in ("listener_reaction", "reaction", "insert_cutaway")
                                                  else run)
            if run > DIALOGUE_RUN_MAX:
                out.append(_f("VL-08", sid, G.REVIEW, f"{run} character lines in a row without a reaction or insert"))
                run = 0
            if not is_video(s):
                continue
            if not ep:
                out.append(_f("VL-01", sid, G.FAIL, "a video shot without its edit_plan (written before any paid clip)"))
                continue
            mode = ep.get("continuity_mode")
            if len(s.get("audio_line_ids") or []) > 1 and sid in spoken:
                out.append(_f("VL-02", sid, G.FAIL, "two lines in one LTX clip: LTX leaves 0.85-1.0 s between "
                              "sentences; one clip, one line"))
            size = (s.get("camera_spec") or {}).get("shot_size")
            if has_line and character_line and size in SPEAKING_CLOSE:
                out.append(_f("VL-02", sid, G.FAIL, f"a speaking {size}: LTX mouths are weak, a close-up is silent"))
            if mode == "continuation":
                src = ep.get("continuity_from")
                if not src or src not in ids:
                    out.append(_f("VL-03", sid, G.FAIL, f"continuation names no shot to continue ({src!r})"))
                elif prev is None or prev["shot_id"] != src:
                    out.append(_f("VL-03", sid, G.FAIL, f"continuation of {src}, but the shot before in this scene is "
                                  f"{prev['shot_id'] if prev else 'none'}: a continuation follows its source directly"))
                elif not is_video(prev):
                    out.append(_f("VL-03", sid, G.FAIL, f"continuation of {src}, which is not a video clip"))
                else:
                    pep = prev.get("edit_plan") or {}
                    a, b = pep.get("screen_direction"), ep.get("screen_direction")
                    if a and b and a != b and not ep.get("axis_cross_reason"):
                        out.append(_f("VL-03", sid, G.FAIL, f"screen direction {a} -> {b} across a continuation "
                                      "without an axis-cross reason"))
                    co, ci = pep.get("camera_out", "rest"), ep.get("camera_in", "rest")
                    if co != ci:
                        out.append(_f("VL-03", sid, G.FAIL, f"camera {co} at the end of {src} but {ci} at the start "
                                      "of its continuation: the move must carry over"))
                    if prev.get("transition_out") in ("cross_dissolve_8f", "fade_to_black"):
                        out.append(_f("VL-03", sid, G.REVIEW, f"{prev.get('transition_out')} inside a continuous action"))
            elif mode in ("coverage", "insert"):
                if not ep.get("scene_master"):
                    out.append(_f("VL-04", sid, G.FAIL, f"{mode} without the scene master it is drawn from"))
                if prev is not None:
                    pep = prev.get("edit_plan") or {}
                    ps, pa = (prev.get("camera_spec") or {}).get("shot_size"), (prev.get("camera_spec") or {}).get(
                        "horizontal_azimuth_deg")
                    cs, ca = size, (s.get("camera_spec") or {}).get("horizontal_azimuth_deg")
                    if mode == "coverage" and ps in SIZE_STEP and cs in SIZE_STEP and SIZE_STEP[ps] == SIZE_STEP[cs] \
                            and pa is not None and ca is not None and min(abs(pa - ca), 360 - abs(pa - ca)) < 30:
                        out.append(_f("VL-04", sid, G.FAIL, f"coverage cut {ps}@{pa} -> {cs}@{ca}: no size step and under "
                                      "30 degrees, it reads as a jump cut"))
                    sa, sb = (axis_at or {}).get("axis_side"), ep.get("axis_side")
                    if sa and sb and sa != sb and not ep.get("axis_cross_reason"):
                        out.append(_f("VL-04", sid, G.FAIL, f"camera crosses the axis {sa} -> {sb} (set by "
                                      f"{axis_at['shot_id']}) without a reason"))
                    if sa and sb and sa == sb and pos_at:
                        pp, cp = pos_at.get("screen_positions") or {}, ep.get("screen_positions") or {}
                        for who in sorted(set(pp) & set(cp)):
                            if {pp[who], cp[who]} == {"left", "right"}:
                                out.append(_f("VL-04", sid, G.FAIL, f"{who} swaps screen side {pp[who]} -> {cp[who]} "
                                              f"(after {pos_at['shot_id']}) on the same side of the axis"))
                if mode == "insert" and has_line and character_line:
                    out.append(_f("VL-04", sid, G.REVIEW, "an insert carrying a character line: the speaker is off "
                                  "screen (Q7 REVIEW)"))
            else:
                out.append(_f("VL-01", sid, G.FAIL, f"unknown continuity_mode {mode!r}"))
            reason = ep.get("cut_in_reason")
            if reason == "line" and prev is not None and not prev.get("audio_line_ids"):
                out.append(_f("VL-09", sid, G.REVIEW, "cut on a line, but the shot before carries none"))
            if prev is None and reason not in ("establish", "scene_change", "time_cut"):
                out.append(_f("VL-09", sid, G.REVIEW, f"the scene opens on a {reason!r} cut: a scene opens on an "
                              "establishing, place or time cut"))
            cs_ = clip_seconds(script, s, max_s)
            if cs_["over"]:
                out.append(_f("VL-06", sid, G.FAIL, f"needs {cs_['needed_s']} s of clip, the model makes {max_s:g} s: split "
                              "the line or the shot"))
    return out


def fit_rows(script: dict, max_s: float, model: str, fps: int) -> list[dict]:
    """G1 (Fable audit FA-01, VL-06): every video shot fits one clip of the pinned LTX model. The need is the same number the
    lane generates (``clip_seconds``: a spoken shot = onset + line + BP-187's tail + handle; a narrated shot = its length +
    handles), so this row and VL-06 never disagree. It replaces the Wan fit row (``aivideo/wan_adapter.fit_rows``), which
    measured LTX shots against Wan's 5 s clip (D-132: the route ``video`` is LTX)."""
    vids = [s for s in script.get("shots", []) if is_video(s)]
    long_ = []
    for s in vids:
        c = clip_seconds(script, s, max_s)
        if c["over"]:
            long_.append(f"{s.get('shot_id')}: needs {c['needed_s']:g} s ({c['basis']})")
    return [G.row("video_shots_fit_the_model", not long_, f"{len(long_)} of {len(vids)} video shot(s) need more than one clip "
                  f"of the LTX model {model} ({max_s:.2f} s at {fps} fps, VL-06): split the line or the shot in the script",
                  long_[:30])]


def rows(script: dict, max_s: float = 10.0) -> list[dict]:
    """The edit plan's gate rows: FAIL findings block a paid clip, REVIEW findings are listed for the creator."""
    fs = findings(script, max_s)
    fail = [f"{f['rule']} {f['shot_id']}: {f['detail']}" for f in fs if f["severity"] == G.FAIL]
    rev = [f"{f['rule']} {f['shot_id']}: {f['detail']}" for f in fs if f["severity"] == G.REVIEW]
    n = sum(1 for s in script.get("shots", []) if is_video(s))
    return [G.row("video_edit_plan", not fail, f"{len(fail)} FAIL finding(s) over {n} video shot(s) (VL-01..VL-06)", fail[:30]),
            G.row("video_edit_plan_review", not rev, f"{len(rev)} REVIEW finding(s) (VL-03/04/08/09)", rev[:30],
                  level=G.REVIEW)]


# ---- the edit-planner's first draft (Fable audit 2026-11-13, P3) ------------------------------------------------------------
# A script written before D-137 has no edit_plan. The draft reads what the script already says (camera_spec, the screen
# direction notes, the continuity refs, who speaks) and proposes one plan per video shot; the edit-planner reviews it and
# the findings above check it. A draft never overwrites a written plan.
_CAMERA = {"push_in": "push", "slow_push_in": "push", "dolly_in": "push", "pull_back": "pull", "slow_pull_back": "pull",
           "dolly_out": "pull", "static": "rest", "locked_off": "rest", "tilt_up": "tilt_up", "tilt_down": "tilt_down",
           "pan_left": "pan_left", "pan_right": "pan_right"}
_WIDE = ("extreme_wide", "wide", "medium_wide")


def _direction(text: str) -> str:
    t = text.lower()
    if "right-to-left" in t or "right to left" in t:
        return "right_to_left"
    if "left-to-right" in t or "left to right" in t:
        return "left_to_right"
    if "toward the camera" in t or "toward camera" in t:
        return "toward_camera"
    return "none"


def _positions(script: dict, shot: dict, text: str) -> dict:
    import re
    names = {c.get("name", ""): c["character_id"] for c in (script.get("world_bible") or {}).get("characters", [])
             if c.get("character_id") in (shot.get("character_ids") or [])}
    out = {}
    for name, cid in names.items():
        m = re.search(rf"\b{re.escape(name)}\b[^;.]{{0,40}}?\b(?:screen-|on screen-|strictly on screen-)?(left|right|center)\b",
                      text, re.I)
        if m:
            out[cid] = m.group(1).lower()
    return out


def draft_edit_plans(script: dict) -> dict[str, dict]:
    """``{shot_id: edit_plan}`` for every video shot that has none yet (see the comment above)."""
    lines = _lines(script)
    spoken = clip_spoken(script)
    out: dict[str, dict] = {}
    for scene in scenes(script):
        sized = [s for s in scene if (s.get("camera_spec") or {}).get("shot_size") in SIZE_STEP]
        master = min(sized or scene, key=lambda s: SIZE_STEP.get((s.get("camera_spec") or {}).get("shot_size"), 9))
        for k, s in enumerate(scene):
            if not is_video(s) or s.get("edit_plan"):
                continue
            prev = scene[k - 1] if k else None
            cam = s.get("camera_spec") or {}
            notes = str((s.get("screen_composition") or {}).get("screen_direction_notes") or "")
            size = cam.get("shot_size")
            inherit = (s.get("continuity_refs") or {}).get("inherit_from_previous_shot_id")
            character_line = any(lines.get(i, {}).get("speaker_type") == "character" for i in s.get("audio_line_ids") or [])
            if inherit and prev is not None and prev["shot_id"] == inherit and is_video(prev):
                mode = "continuation"
            elif not s.get("character_ids") and size in SPEAKING_CLOSE and k:
                mode = "insert"
            else:
                mode = "coverage"
            direction = _direction(notes)
            move = _CAMERA.get(str(cam.get("camera_move") or ""), None)
            if move is None:   # tracking / parallax: a lateral move with the action's direction
                move = "track_left" if direction == "right_to_left" else "track_right"
            if prev is None:
                reason = "establish" if size in _WIDE else "scene_change"
            elif mode == "insert":
                reason = "insert"
            elif s.get("shot_role") in ("listener_reaction", "reaction"):
                reason = "reaction"
            elif character_line:
                reason = "line"
            else:
                reason = "action"
            ep = {"continuity_mode": mode, "cut_in_reason": reason, "axis_side": "A", "screen_direction": direction,
                  "camera_in": move, "camera_out": move}
            if mode == "continuation":
                ep["continuity_from"] = inherit
            else:
                ep["scene_master"] = f"{master['shot_id']}_start"
            pos = _positions(script, s, notes)
            if pos:
                ep["screen_positions"] = pos
            if s["shot_id"] in spoken:
                ep["speech_onset_s"] = SPEECH_ONSET_S
            out[s["shot_id"]] = ep
    return out
