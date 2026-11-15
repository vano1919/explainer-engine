
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
    return out
