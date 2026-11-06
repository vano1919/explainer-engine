"""Cut lint for a J5 dialogue (the creator, 2026-11-06 19:52-19:57 UTC: a cut needs a reason; "the man, then the same man only closer" is a jump,
not a change of angle). The rules are the repository's own (BP-30 cut continuity, BP-103 the 30-degree rule and shot-size variety, ED-14 J/L cuts)
applied to the facts a J5 shot carries: who is the subject, from which card (sheet yaw) and at which size. A cut is allowed when it changes the
SUBJECT (the other hero: shot / reverse shot, motivated by the speaker change) or the ANGLE of the same hero by at least ``ANGLE_MIN_DEG`` (another sheet:
front, 3/4 left, 3/4 right, back) and, for the same hero, also the size by a full step; a push-in inside one shot is not a cut and is always free.
The camera stays on one side of the axis between the two heroes (180-degree rule): the heroes keep their sides of the frame in every shot.
"""
from __future__ import annotations

SIZE_RANK = {"wide": 0, "medium": 1, "close": 2}
ANGLE_MIN_DEG = 30.0                   # BP-103, the 30-degree rule
# the yaw of each hero card (degrees, 0 = facing the camera, + = turned to the viewer's right), from the sheet it uses
YAW = {"front": 0.0, "left34": -45.0, "right34": 45.0, "back": 180.0}


def subject(shot: dict) -> tuple[str, str]:
    """(hero, sheet view) of the shot's subject."""
    return shot["subject"], shot["view"]


def lint(shots: list[dict]) -> list[str]:
    """Problems between consecutive shots, one text each; an empty list means every cut has a reason."""
    out = []
    for a, b in zip(shots, shots[1:]):
        name = f"{a['name']} -> {b['name']}"
        if a["subject"] != b["subject"]:
            if not b.get("motivation"):
                out.append(f"{name}: the subject changes but no motivation (speaker change, reaction) is given")
            continue
        dyaw = abs(YAW[a["view"]] - YAW[b["view"]])
        dyaw = min(dyaw, 360 - dyaw)
        step = abs(SIZE_RANK[b["size"]] - SIZE_RANK[a["size"]])
        if dyaw < ANGLE_MIN_DEG:
            out.append(f"{name}: the same hero from the same side ({dyaw:.0f} degrees apart, need {ANGLE_MIN_DEG:.0f}): a jump; keep it one shot with a push-in")
        elif step < 1:
            out.append(f"{name}: the same hero at the same size from another angle: change the size by a full step as well (BP-30)")
    for s in shots:
        sides = s.get("sides")
        if sides and sides != shots[0].get("sides", sides):
            out.append(f"{s['name']}: the heroes swapped sides of the frame (180-degree rule)")
    return out


# the dialogue as cut now (step 4f) and as it was cut until step 4e
SEQUENCE = [
    {"name": "S1_two_shot", "subject": "H2", "view": "right34", "size": "medium", "sides": ("H2", "H1")},
    {"name": "S2_ots_h2_to_h1", "subject": "H1", "view": "left34", "size": "medium", "motivation": "the commander speaks", "sides": ("H2", "H1")},
    {"name": "S3_ots_h1_to_h2", "subject": "H2", "view": "right34", "size": "medium", "motivation": "the scout answers", "sides": ("H2", "H1")},
]
SEQUENCE_4E = [SEQUENCE[0], SEQUENCE[1], {"name": "S4_close_up_h1", "subject": "H1", "view": "left34", "size": "close", "sides": ("H2", "H1")}, SEQUENCE[2]]
