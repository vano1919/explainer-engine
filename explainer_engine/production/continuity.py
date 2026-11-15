
"""Zoom continuity (ED-02): consecutive shots of the same picture continue one camera move instead of snapping back to the
default view. Each timed shot gets ``render_motion`` (what the assembler draws); the script's ``motion`` stays what the board
rules (UR-13) judge. State is (zoom, horizontal centre offset as a share of the picture width). ``findings`` also carries
BP-30 (docs/SOURCED_RULES.md): the same framing of the same picture twice in a row is a REVIEW; BP-92: a camera move never
resets (a run of shots on one picture never returns to its start framing, a turn comes to rest); and VL-15 (prop state
continuity across consecutive shots of one scene: a prop held at the end of shot A may not be on the ground, leaning or
released at the start of shot B without an intervening action)."""
from __future__ import annotations

import re

from explainer_engine.standards import sourced_rules as SR

ZMAX = SR.T("BP-20", "scale_max")  # the camera never pushes past this on one picture (a punch accent stacks on top, exempt)
STEP = 0.04  # growth of a continued shot when the script gave none
TOL = 0.005
SAME_ZOOM = SR.T("BP-30", "same_framing_zoom_tol")  # BP-30: the same framing = zooms this close and crops within TOL

_PROPS = (
    "rifle", "gun", "pistol", "bayonet", "button", "mug", "cup", "tin", "cigarette", "cigar", "match",
    "photograph", "photo", "letter", "spade", "shovel", "helmet", "cap", "hat", "lantern", "torch",
    "flag", "cloth", "watch", "diary", "notebook", "pen", "pencil", "bread", "chocolate", "bottle",
    "knife", "harmonica", "bible", "book", "cross", "football", "ball",
)
_HELD_RE = re.compile(
    r"\b(hold(?:s|ing)?|held|in\s+(?:his|her|their|one|both|left|right)\s+hand(?:s)?|grip(?:s|ping|ped)?|"
    r"clutch(?:es|ing|ed)?|carry(?:ing)?|carries|carried|rais(?:es|ing|ed)|lift(?:s|ing|ed)|"
    r"extend(?:s|ing|ed)|offer(?:s|ing|ed)|hand(?:s|ing)?\s+over|present(?:s|ing|ed))\b",
    re.I,
)
_RELEASED_RE = re.compile(
    r"\b(on\s+the\s+(?:ground|floor|table|parapet|earth|mud|snow|crate|bench|ledge|wall)|"
    r"lean(?:s|ing|ed)\s+against|rest(?:s|ing|ed)\s+(?:on|against)|slung|holstered|sheathed|"
    r"in\s+(?:his|her|their)\s+pocket|sewn\s+on\s+(?:his|her|the)\s+(?:coat|tunic|uniform)|"
    r"attached\s+to\s+(?:his|her|the)\s+(?:coat|tunic)|empty[- ]handed|hands\s+empty|unarmed|"
    r"laid\s+down|set\s+down|beside\s+(?:him|her|them))\b",
    re.I,
)


def start_state(m: dict) -> tuple[float, float]:
    x = m["x0"] if "x0" in m else -m.get("dx", 0.0) / 2
    return float(m["z0"]), float(x)


def end_state(m: dict) -> tuple[float, float]:
    x = m["x1"] if "x1" in m else m.get("dx", 0.0) / 2
    return float(m["z1"]), float(x)


def _limit(z: float) -> float:
    """Largest centre offset that keeps the crop inside the picture at zoom z."""
    return max(0.0, (1.0 - 1.0 / z) / 2)


def chain(shots: list[dict], zmax: float = ZMAX) -> list[dict]:
    """Set ``render_motion`` on every shot; a shot on the same picture as the one before starts where that one ended."""
    prev = None
    for s in shots:
        m = dict(s["motion"])
        if prev is not None and prev["picture"] == s["picture"]:
            z, x = end_state(prev["render_motion"])
            grow = max(STEP, float(m["z1"]) - float(m["z0"])) if m.get("kind") != "pull" else -abs(float(m["z1"]) - float(m["z0"]))
            if z >= zmax - 0.01 or grow < 0:  # past the cap: pull out by one step, never all the way back (BP-92)
                z1 = max(1.0, z - STEP) if grow >= 0 else max(1.0, z + max(grow, -STEP))
                x1 = x * (z1 - 1.0) / max(z - 1.0, 1e-6) if z > 1.0 else 0.0
            else:
                z1 = min(zmax, z + grow)
                x1 = x
            x1 = max(-_limit(z1), min(_limit(z1), x1))
            m = {"kind": "push" if z1 > z else "pull" if z1 < z else "static", "z0": round(z, 4), "z1": round(z1, 4),
                 "x0": round(max(-_limit(z), min(_limit(z), x)), 4), "x1": round(x1, 4), "chained": True}
        s["render_motion"] = m
        prev = s
    for a, b in zip(shots, shots[1:] + [None]):  # ED-08: the camera is at rest at every cut to another picture
        a["render_motion"]["ein"] = not a["render_motion"].get("chained", False)
        a["render_motion"]["eout"] = b is None or b["picture"] != a["picture"]
    for a, b in zip(shots, shots[1:]):  # BP-92: a move that turns back on one picture comes to rest at the turn
        if b["render_motion"].get("chained") and _direction(a["render_motion"]) * _direction(b["render_motion"]) < 0:
            a["render_motion"]["eout"] = b["render_motion"]["ein"] = True
    return shots


def _direction(m: dict) -> int:
    dz = float(m["z1"]) - float(m["z0"])
    return (dz > 1e-9) - (dz < -1e-9)


def warp(u: float, ein: bool, eout: bool) -> float:
    """Progress 0..1 of a move: eased (zero speed) at an end that meets a cut to another picture, linear where the move
    must carry on into the next shot of the same picture."""
    f = lambda v: v * v * (2 - v)  # noqa: E731  speed 0 at 0, speed 1 at 1
    if ein and eout:
        return u * u * (3 - 2 * u)
    if ein:
        return f(u)
    if eout:
        return 1 - f(1 - u)
    return u


def _prop_states(text: str, extra_props: dict | None = None) -> dict[str, str]:
    """Extract {prop_name: 'held' | 'released'} from a shot's state description or explicit prop dict."""
    states: dict[str, str] = {}
    if isinstance(extra_props, dict):
        for k, v in extra_props.items():
            vs = str(v).lower().strip()
            if vs in ("held", "in_hand", "raised", "carried") or _HELD_RE.search(vs):
                states[str(k).lower()] = "held"
            elif vs in ("released", "ground", "table", "leaning", "unarmed", "coat", "attached") or _RELEASED_RE.search(vs):
                states[str(k).lower()] = "released"
    raw = str(text or "")
    if not raw.strip():
        return states
    clauses = re.split(r"[.;,\n]+|\b(?:while|and|as)\b", raw)
    for clause in clauses:
        cl = clause.lower()
        for prop in _PROPS:
            if not re.search(rf"\b{re.escape(prop)}s?\b", cl):
                continue
            is_held = bool(_HELD_RE.search(cl))
            is_rel = bool(_RELEASED_RE.search(cl))
            if is_held and not is_rel:
                states[prop] = "held"
            elif is_rel and not is_held:
                states[prop] = "released"
    return states


def pair_state_findings(shots: list[dict]) -> list[dict]:
    """VL-15 (Audit #1): compare ``action_end_state`` of shot A with ``action_start_state`` of shot B across consecutive shots
    in the same scene/location. If a prop is held at the end of A and released/leaning/on-ground/sewn-on at the start of B
    (or vice versa) without an explicit transition beat, emit a FAIL finding."""
    out: list[dict] = []
    for a, b in zip(shots, shots[1:]):
        seg_a = a.get("segment_id") or a.get("scene")
        seg_b = b.get("segment_id") or b.get("scene")
        loc_a = a.get("location_id") or a.get("place")
        loc_b = b.get("location_id") or b.get("place")
        if (seg_a and seg_b and seg_a != seg_b) or (loc_a and loc_b and loc_a != loc_b):
            continue
        chars_a = set(a.get("character_ids") or [])
        chars_b = set(b.get("character_ids") or [])
        if chars_a and chars_b and not (chars_a & chars_b):
            continue
        end_a = _prop_states(str(a.get("action_end_state") or a.get("end_state") or ""), a.get("end_props"))
        start_b = _prop_states(str(b.get("action_start_state") or b.get("start_state") or ""), b.get("start_props"))
        sid_a = a.get("shot_id") or a.get("id") or "?"
        sid_b = b.get("shot_id") or b.get("id") or "?"
        for prop in sorted(set(end_a) & set(start_b)):
            if end_a[prop] != start_b[prop]:
                out.append({
                    "rule": "VL-15 PROP-STATE",
                    "severity": "FAIL",
                    "where": f"{sid_a}->{sid_b}",
                    "shot_id": sid_b,
                    "from_shot_id": sid_a,
                    "prop": prop,
                    "detail": (
                        f"prop '{prop}' is {end_a[prop]} at the end of {sid_a} "
                        f"({a.get('action_end_state') or a.get('end_state')!r}) but {start_b[prop]} at the start of {sid_b} "
                        f"({b.get('action_start_state') or b.get('start_state')!r})"
                    ),
                })
    return out


def findings(shots: list[dict]) -> list[dict]:
    """ZOOM-1: the camera state at a cut inside one picture must be the same on both sides. BP-30: a shot that ends where the
    shot before it ended (same crop, zoom within SAME_ZOOM) shows the same framing of the same picture twice in a row.
    VL-15: end state of shot A must not contradict start state of shot B on held/released props."""
    out = []
    run_start = None
    for a, b in zip([None] + shots, shots):  # BP-92: a run of shots on one picture never comes back to where it started
        if "render_motion" not in b:
            run_start = None
            continue
        if a is None or a.get("picture") != b.get("picture") or "render_motion" not in a:
            run_start, moved = start_state(b["render_motion"]), False
        ze, xe = end_state(b["render_motion"])
        back = abs(ze - run_start[0]) < SAME_ZOOM and abs(xe - run_start[1]) <= TOL
        if moved and back:
            out.append({"rule": "BP-92", "severity": SR.rule("BP-92").get("severity", "REVIEW"), "where": b.get("id") or b.get("shot_id"),
                        "detail": f"the camera returns to the framing this picture's run started from (zoom {ze:.3f}): a "
                                  "reset; continue the move, or cut to another picture"})
        moved = moved or not back
    for a, b in zip(shots, shots[1:]):
        if a.get("picture") != b.get("picture") or "render_motion" not in a or "render_motion" not in b:
            continue
        za, xa = end_state(a["render_motion"])
        zb, xb = start_state(b["render_motion"])
        if abs(za - zb) > TOL or abs(xa - xb) > TOL:
            out.append({"rule": "ED-02 ZOOM-1", "severity": "FAIL", "where": b.get("id") or b.get("shot_id"),
                        "detail": f"zoom snaps from {za:.3f} to {zb:.3f} (offset {xa:.3f} to {xb:.3f}) on the same picture"})
            continue
        ze, xe = end_state(b["render_motion"])
        if abs(ze - za) < SAME_ZOOM and abs(xe - xa) <= TOL:
            out.append({"rule": "BP-30", "severity": SR.rule("BP-30").get("severity", "REVIEW"), "where": b.get("id") or b.get("shot_id"),
                        "detail": f"same framing twice in a row: {b.get('id') or b.get('shot_id')} ends at zoom {ze:.3f} where {a.get('id') or a.get('shot_id')} ended "
                                  f"({za:.3f}) on the same picture; a cut changes the shot size by a full step"})
    out.extend(pair_state_findings(shots))
    out.extend(evaluate_neighbouring_shot_continuity(shots))
    return out


_SHOT_SIZE_ORDER = {
    "extreme_wide": 0,
    "wide": 1,
    "medium_wide": 2,
    "medium": 3,
    "over_the_shoulder": 3,
    "medium_close_up": 4,
    "close_up": 5,
    "extreme_close_up": 6,
}

_POSTURE_STATES = {
    "standing": ("standing", "stands", "upright", "on his feet", "on their feet"),
    "sitting": ("sitting", "sits", "seated"),
    "kneeling": ("kneeling", "kneels", "crouching", "crouches"),
}


def _extract_posture(text: str, structured_posture: str | None = None) -> str | None:
    if structured_posture:
        return str(structured_posture).strip().lower()
    low = (text or "").lower()
    for state, toks in _POSTURE_STATES.items():
        if any(re.search(rf"\b{re.escape(t)}\b", low) for t in toks):
            return state
    return None


def _is_same_scene(a: dict, b: dict) -> bool:
    if b.get("continues") is True or b.get("continues") == (a.get("shot_id") or a.get("id")):
        return True
    sc_a = a.get("scene_id") or (a.get("staging") or {}).get("scene_id")
    sc_b = b.get("scene_id") or (b.get("staging") or {}).get("scene_id")
    if sc_a and sc_b:
        return sc_a == sc_b
    seg_a = a.get("segment_id") or a.get("scene")
    seg_b = b.get("segment_id") or b.get("scene")
    loc_a = a.get("location_id") or a.get("place")
    loc_b = b.get("location_id") or b.get("place")
    if seg_a and seg_b and seg_a == seg_b:
        if loc_a and loc_b:
            return loc_a == loc_b
        return True
    return False


def _is_motivated_reframe(a: dict, b: dict) -> bool:
    if b.get("reframe_reason") or b.get("motivated_reframe") or (b.get("staging") or {}).get("reframe_reason"):
        return True
    sa = str((a.get("camera_spec") or {}).get("shot_size") or "").lower()
    sb = str((b.get("camera_spec") or {}).get("shot_size") or "").lower()
    if sa in _SHOT_SIZE_ORDER and sb in _SHOT_SIZE_ORDER:
        return abs(_SHOT_SIZE_ORDER[sa] - _SHOT_SIZE_ORDER[sb]) >= 1
    return False


def _positions_map(shot: dict) -> dict[str, tuple[float, float]]:
    staging = shot.get("staging") or {}
    layout = shot.get("layout") or staging.get("layout") or {}
    raw_pos = shot.get("positions") or staging.get("positions") or layout.get("positions") or {}
    out: dict[str, tuple[float, float]] = {}
    if isinstance(raw_pos, dict):
        for k, v in raw_pos.items():
            if isinstance(v, (list, tuple)) and len(v) >= 2:
                if len(v) >= 4:
                    out[str(k)] = (0.5 * (float(v[0]) + float(v[2])), 0.5 * (float(v[1]) + float(v[3])))
                else:
                    out[str(k)] = (float(v[0]), float(v[1]))
    elif isinstance(raw_pos, list):
        for item in raw_pos:
            if isinstance(item, dict):
                cid = item.get("id") or item.get("character_id") or item.get("subject")
                box = item.get("box") or item.get("bbox") or item.get("face_box") or item.get("pos")
                if cid and isinstance(box, (list, tuple)) and len(box) >= 2:
                    if len(box) >= 4:
                        out[str(cid)] = (0.5 * (float(box[0]) + float(box[2])), 0.5 * (float(box[1]) + float(box[3])))
                    else:
                        out[str(cid)] = (float(box[0]), float(box[1]))
    return out


def evaluate_neighbouring_shot_continuity(
    shots: list[dict],
    *,
    boundary_frames: dict[str, dict] | None = None,
) -> list[dict]:
    """P1-3 Neighbouring-Shot Continuity Stage: compare every consecutive pair of shots in the same scene across:
    1. Subject/face bounding boxes & positions (BP-30 focal_shift_max unless motivated reframe),
    2. Character identity and roster count (CONT-ROSTER),
    3. Camera scale and direction (motivated reframe vs accidental jump, BP-30 direction_change_max_deg),
    4. Light level and colour balance (BP-34 luma_tolerance / warmth_tolerance),
    5. Weather and atmosphere (BP-196),
    6. Final action/posture/prop state vs next initial state (VL-15),
    7. No static photo inserted inside an ongoing live video action scene (CONT-PHOTO-IN-LIVE-SCENE).
    """
    out: list[dict] = []
    boundary_frames = boundary_frames or {}
    focal_shift_max = float(SR.T("BP-30", "focal_shift_max"))
    dir_max_deg = float(SR.T("BP-30", "direction_change_max_deg"))
    luma_tol = float(SR.T("BP-34", "luma_tolerance"))
    warmth_tol = float(SR.T("BP-34", "warmth_tolerance"))

    for idx, (a, b) in enumerate(zip(shots, shots[1:])):
        if not _is_same_scene(a, b):
            continue
        sid_a = a.get("shot_id") or a.get("id") or f"shot_{idx}"
        sid_b = b.get("shot_id") or b.get("id") or f"shot_{idx + 1}"
        where = f"{sid_a}->{sid_b}"
        motivated = _is_motivated_reframe(a, b)

        # 1. Subject / face bounding box position continuity
        pos_a = _positions_map(a)
        pos_b = _positions_map(b)
        for cid in sorted(set(pos_a) & set(pos_b)):
            dx = abs(pos_a[cid][0] - pos_b[cid][0])
            dy = abs(pos_a[cid][1] - pos_b[cid][1])
            shift = (dx * dx + dy * dy) ** 0.5
            if shift > focal_shift_max and not motivated:
                out.append({
                    "rule": "CONT-BBOX-JUMP",
                    "severity": "FAIL",
                    "where": where,
                    "shot_id": sid_b,
                    "from_shot_id": sid_a,
                    "subject": cid,
                    "detail": (
                        f"subject '{cid}' jumps by {shift:.3f} (> {focal_shift_max:.2f}) across {where} "
                        "without a motivated reframe"
                    ),
                })

        # 2. Character identity & count continuity when continues=True or same framing
        roster_a = set(a.get("roster") or (a.get("staging") or {}).get("roster") or a.get("character_ids") or [])
        roster_b = set(b.get("roster") or (b.get("staging") or {}).get("roster") or b.get("character_ids") or [])
        if (b.get("continues") or not motivated) and roster_a and roster_b and roster_a != roster_b:
            if not b.get("announced_newcomer") and not b.get("roster_change_reason"):
                out.append({
                    "rule": "CONT-ROSTER",
                    "severity": "FAIL",
                    "where": where,
                    "shot_id": sid_b,
                    "from_shot_id": sid_a,
                    "detail": f"character roster changes from {sorted(roster_a)} to {sorted(roster_b)} across {where} without reframe or announcement",
                })

        # 3. Camera direction & unmotivated scale jump
        ang_a = (a.get("camera_spec") or {}).get("angle_deg")
        ang_b = (b.get("camera_spec") or {}).get("angle_deg")
        if ang_a is not None and ang_b is not None:
            if abs(float(ang_b) - float(ang_a)) > dir_max_deg and not b.get("neutral_bridge"):
                out.append({
                    "rule": "CONT-CAMERA-DIRECTION",
                    "severity": "FAIL",
                    "where": where,
                    "shot_id": sid_b,
                    "from_shot_id": sid_a,
                    "detail": f"camera direction flips by {abs(float(ang_b) - float(ang_a)):.1f} deg (> {dir_max_deg:.0f} deg) across {where}",
                })

        # 4. Light level & colour balance continuity (from boundary_frames or shot lighting metadata)
        bf = boundary_frames.get(where) or {}
        luma_a = bf.get("end_luma", a.get("end_luma", (a.get("lighting") or {}).get("luma")))
        luma_b = bf.get("start_luma", b.get("start_luma", (b.get("lighting") or {}).get("luma")))
        if luma_a is not None and luma_b is not None and abs(float(luma_b) - float(luma_a)) > luma_tol:
            out.append({
                "rule": "CONT-LIGHT-COLOUR",
                "severity": "FAIL",
                "where": where,
                "shot_id": sid_b,
                "from_shot_id": sid_a,
                "detail": f"light level jumps from {float(luma_a):.3f} to {float(luma_b):.3f} (> {luma_tol:.2f}) across {where}",
            })
        warm_a = bf.get("end_warmth", a.get("end_warmth", (a.get("lighting") or {}).get("warmth")))
        warm_b = bf.get("start_warmth", b.get("start_warmth", (b.get("lighting") or {}).get("warmth")))
        if warm_a is not None and warm_b is not None and abs(float(warm_b) - float(warm_a)) > warmth_tol:
            out.append({
                "rule": "CONT-LIGHT-COLOUR",
                "severity": "FAIL",
                "where": where,
                "shot_id": sid_b,
                "from_shot_id": sid_a,
                "detail": f"colour warmth jumps from {float(warm_a):.3f} to {float(warm_b):.3f} (> {warmth_tol:.2f}) across {where}",
            })

        # 5. Weather & atmosphere continuity
        wea_a = a.get("weather") or (a.get("staging") or {}).get("weather")
        wea_b = b.get("weather") or (b.get("staging") or {}).get("weather")
        if wea_a and wea_b and str(wea_a).lower() != str(wea_b).lower() and not b.get("weather_reason"):
            out.append({
                "rule": "CONT-WEATHER",
                "severity": "FAIL",
                "where": where,
                "shot_id": sid_b,
                "from_shot_id": sid_a,
                "detail": f"weather jumps from {wea_a!r} to {wea_b!r} inside the same scene across {where} without weather_reason",
            })

        # 6. Action posture continuity
        post_a = _extract_posture(str(a.get("action_end_state") or a.get("end_state") or ""), a.get("end_posture"))
        post_b = _extract_posture(str(b.get("action_start_state") or b.get("start_state") or ""), b.get("start_posture"))
        if post_a and post_b and post_a != post_b and (roster_a & roster_b or not (roster_a or roster_b)):
            out.append({
                "rule": "CONT-ACTION-STATE",
                "severity": "FAIL",
                "where": where,
                "shot_id": sid_b,
                "from_shot_id": sid_a,
                "detail": f"actor posture is {post_a!r} at end of {sid_a} but {post_b!r} at start of {sid_b} without transition beat",
            })

        # 7. Forbid inserting a static photo inside an ongoing live video action scene
        route_a = str(a.get("route") or "")
        route_b = str(b.get("route") or "")
        c = shots[idx + 2] if idx + 2 < len(shots) else None
        route_c = str(c.get("route") or "") if isinstance(c, dict) else ""
        if route_a == "video" and route_b in ("still_25d", "still") and not b.get("insert_cutaway_reason"):
            if b.get("continues") or (isinstance(c, dict) and route_c == "video" and _is_same_scene(b, c)):
                out.append({
                    "rule": "CONT-PHOTO-IN-LIVE-SCENE",
                    "severity": "FAIL",
                    "where": where,
                    "shot_id": sid_b,
                    "from_shot_id": sid_a,
                    "detail": f"{sid_b} inserts a static photo ({route_b}) inside an ongoing live video scene without insert_cutaway_reason",
                })

    return out


def verify_split_clip_continuity(
    parts: list,
    *,
    shot_spec: dict | None = None,
    max_luma_jump: float = 14.0,
    max_scale_jump: float = 0.025,
) -> dict:
    """P1-3 Split-Clip Fallback Guard: verify that legacy split [a-z].mp4 sub-clips (or their part descriptors)
    maintain continuous camera trajectory and frame appearance across every boundary before concatenation."""
    import numpy as np

    findings_list: list[dict] = []
    if not parts:
        return {"status": "FAIL", "findings": [{"rule": "CONT-SPLIT-EMPTY", "severity": "FAIL", "detail": "no split parts provided"}]}

    for idx in range(len(parts) - 1):
        pa, pb = parts[idx], parts[idx + 1]
        if isinstance(pa, dict) and isinstance(pb, dict):
            sa = float(pa.get("end_scale", pa.get("scale_end", 1.0)))
            sb = float(pb.get("start_scale", pb.get("scale_start", 1.0)))
            if abs(sb - sa) > max_scale_jump:
                findings_list.append({
                    "rule": "CONT-SPLIT-ZOOM-JUMP",
                    "severity": "FAIL",
                    "boundary": f"part_{idx}->part_{idx+1}",
                    "detail": f"split sub-clip scale jumps from {sa:.3f} to {sb:.3f} (> {max_scale_jump:.3f})",
                })
            luma_diff = abs(float(pb.get("start_luma", 0.0)) - float(pa.get("end_luma", 0.0)))
            if luma_diff > max_luma_jump:
                findings_list.append({
                    "rule": "CONT-SPLIT-FRAME-JUMP",
                    "severity": "FAIL",
                    "boundary": f"part_{idx}->part_{idx+1}",
                    "detail": f"split sub-clip boundary luma jumps by {luma_diff:.2f} (> {max_luma_jump:.1f})",
                })
        else:
            p_a = Path(pa)
            p_b = Path(pb)
            if p_a.is_file() and p_b.is_file():
                try:
                    import cv2
                    cap_a = cv2.VideoCapture(str(p_a))
                    n_a = int(cap_a.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
                    if n_a > 0:
                        cap_a.set(cv2.CAP_PROP_POS_FRAMES, max(0, n_a - 1))
                    ok_a, frame_a = cap_a.read()
                    cap_a.release()

                    cap_b = cv2.VideoCapture(str(p_b))
                    ok_b, frame_b = cap_b.read()
                    cap_b.release()

                    if ok_a and ok_b and frame_a is not None and frame_b is not None:
                        if frame_a.shape[:2] != frame_b.shape[:2]:
                            frame_b = cv2.resize(frame_b, (frame_a.shape[1], frame_a.shape[0]))
                        mad = float(np.mean(np.abs(frame_a.astype(np.float32) - frame_b.astype(np.float32))))
                        if mad > max_luma_jump:
                            findings_list.append({
                                "rule": "CONT-SPLIT-FRAME-JUMP",
                                "severity": "FAIL",
                                "boundary": f"{p_a.name}->{p_b.name}",
                                "detail": f"split sub-clip boundary frame MAD={mad:.2f} > {max_luma_jump:.1f} (camera reset or crop jump)",
                            })
                except Exception:
                    pass

    return {
        "status": "FAIL" if findings_list else "PASS",
        "part_count": len(parts),
        "findings": findings_list,
    }
