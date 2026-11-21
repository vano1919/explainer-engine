"""Cut lint for a J5 dialogue (the creator, 2026-11-06 19:52-19:57 UTC: a cut needs a reason; "the man, then the same man only closer" is a jump,
not a change of angle). The rules are the repository's own (BP-30 cut continuity, BP-103 the 30-degree rule and shot-size variety, ED-14 J/L cuts)
applied to the facts a J5 shot carries: who is the subject, from which card (sheet yaw) and at which size. A cut is allowed when it changes the
SUBJECT (the other hero: shot / reverse shot, motivated by the speaker change) or the ANGLE of the same hero by at least ``ANGLE_MIN_DEG`` (another sheet:
front, 3/4 left, 3/4 right, back) and, for the same hero, also the size by a full step; a push-in inside one shot is not a cut and is always free.
The camera stays on one side of the axis between the two heroes (180-degree rule): the heroes keep their sides of the frame in every shot.
"""
from __future__ import annotations

from explainer_engine.standards import sourced_rules as SR

SIZE_RANK = {"wide": 0, "medium": 1, "close": 2}
ANGLE_MIN_DEG = float(SR.T("BP-176", "angle_min_deg"))      # the 30-degree rule; the number lives in the registry (BP-176)
SIZE_STEP_MIN = int(SR.T("BP-176", "size_step_min"))
AXIAL_STEP_MIN = int(SR.T("BP-176", "axial_size_step_min"))
PUNCH_MIN, PUNCH_MAX = float(SR.T("BP-178", "punch_scale_min")), float(SR.T("BP-178", "punch_scale_max"))
PUNCH_GAP_S = float(SR.T("BP-178", "punch_gap_min_s"))
# the yaw of each hero card (degrees, 0 = facing the camera, + = turned to the viewer's right), from the sheet it uses
YAW = {"front": 0.0, "left34": -45.0, "right34": 45.0, "back": 180.0}


def subject(shot: dict) -> tuple[str, str]:
    """(hero, sheet view) of the shot's subject."""
    return shot["subject"], shot["view"]


def lint(shots: list[dict]) -> list[str]:
    """Problems between consecutive shots, one text each; an empty list means every cut has a reason."""
    out = []
    last_punch = None
    for a, b in zip(shots, shots[1:]):
        name = f"{a['name']} -> {b['name']}"
        if b.get("cut") == "punch_in":                  # a declared, deliberate jump cut (BP-178): same subject, same angle, a small scale step
            sc = b.get("scale", 0.0)
            if (a["subject"], a["view"]) != (b["subject"], b["view"]):
                out.append(f"{name}: a punch-in stays on the same subject and sheet view")
            if not PUNCH_MIN <= sc <= PUNCH_MAX:
                out.append(f"{name}: punch-in scale {sc} is outside {PUNCH_MIN}-{PUNCH_MAX}")
            if last_punch is not None and b.get("start", 0.0) - last_punch < PUNCH_GAP_S:
                out.append(f"{name}: punch-ins closer than {PUNCH_GAP_S:g} s")
            last_punch = b.get("start", 0.0)
            continue
        if a["subject"] != b["subject"]:
            if not b.get("motivation"):
                out.append(f"{name}: the subject changes but no motivation (speaker change, reaction) is given")
            continue
        dyaw = abs(YAW[a["view"]] - YAW[b["view"]])
        dyaw = min(dyaw, 360 - dyaw)
        step = abs(SIZE_RANK[b["size"]] - SIZE_RANK[a["size"]])
        if dyaw < ANGLE_MIN_DEG and b.get("cut") == "axial" and step >= AXIAL_STEP_MIN:
            continue                                    # a declared axial cut-in with a big size step (wide to close)
        if dyaw < ANGLE_MIN_DEG:
            out.append(f"{name}: the same hero from the same side ({dyaw:.0f} degrees apart, need {ANGLE_MIN_DEG:.0f}): a jump; keep it one shot with a push-in, or declare an axial cut-in of {AXIAL_STEP_MIN} size steps")
        elif step < SIZE_STEP_MIN:
            out.append(f"{name}: the same hero at the same size from another angle: change the size by a full step as well (BP-176)")
    for s in shots:
        sides = s.get("sides")
        if sides and sides != shots[0].get("sides", sides):
            out.append(f"{s['name']}: the heroes swapped sides of the frame (180-degree rule)")
    return out


EYE = {"H2": "right", "H1": "left"}                   # the scout on the left looks right, the commander on the right looks left
# the dialogue as cut now (step 4f) and as it was cut until step 4e
SEQUENCE = [
    {"name": "S1_two_shot", "subject": "H2", "view": "right34", "size": "wide", "sides": ("H2", "H1"), "eyeline": EYE},
    {"name": "S2_ots_h2_to_h1", "subject": "H1", "view": "left34", "size": "medium", "motivation": "the commander speaks", "sides": ("H2", "H1"), "eyeline": EYE},
    {"name": "S3_ots_h1_to_h2", "subject": "H2", "view": "right34", "size": "medium", "motivation": "the scout answers", "sides": ("H2", "H1"), "eyeline": EYE},
]
SEQUENCE_4E = [SEQUENCE[0], SEQUENCE[1], {"name": "S4_close_up_h1", "subject": "H1", "view": "left34", "size": "close", "sides": ("H2", "H1"), "eyeline": EYE}, SEQUENCE[2]]


def plan_check(plan: list[dict]) -> list[str]:
    """The plan-stage check (BP-177), run BEFORE any picture of the dialogue is generated: every shot carries the required fields, the first shot is
    the wide two-shot that fixes the sides and eyelines, the heroes look at each other (the one on the left looks right and the other way round),
    every later shot keeps those sides and eyelines, and the cuts pass ``lint``. Returns the problems; empty = the plan may go to generation."""
    out = []
    need = SR.T("BP-177", "required_fields")
    for s in plan:
        miss = [k for k in need if not s.get(k)]
        if miss:
            out.append(f"{s.get('name', '?')}: missing {', '.join(miss)}")
    if out or not plan:
        return out or ["the plan is empty"]
    first = plan[0]
    if first["size"] != SR.T("BP-177", "establishing_size") or len(first["sides"]) != 2:
        out.append(f"{first['name']}: the first picture must be the wide two-shot of both heroes (the master the coverage is derived from)")
    left, right = first["sides"]
    if first["eyeline"].get(left) != "right" or first["eyeline"].get(right) != "left":
        out.append(f"{first['name']}: the hero on the left must look right and the one on the right look left")
    for s in plan[1:]:
        if s["sides"] != first["sides"]:
            out.append(f"{s['name']}: the heroes changed sides of the frame (180-degree rule)")
        for hero, direction in s["eyeline"].items():
            if first["eyeline"].get(hero) != direction:
                out.append(f"{s['name']}: {hero} looks {direction} but the master has {hero} looking {first['eyeline'].get(hero)}")
    names = {s["name"]: s for s in plan}
    for i, s in enumerate(plan):
        src = s.get("reuse_of")
        if src:
            o = names.get(src)
            if o is None or plan.index(o) >= i:
                out.append(f"{s['name']}: reuse_of {src} must name an EARLIER shot of the plan")
            elif (o["subject"], o["view"]) != (s["subject"], s["view"]):
                out.append(f"{s['name']}: a reused picture keeps its subject and sheet view (BP-178)")
    return out + lint(plan)
