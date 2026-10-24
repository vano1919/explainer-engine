"""Shot prompts for animated shots: keyframe, next pose, cut and video (KP-01..KP-14, docs/SHOT_PROMPTS.md). stdlib only.

Every rule comes from a picture or clip we made and measured (2026-10-22..24); hypotheses only give REVIEW. A shot is
``{"id", "kind": keyframe|nextpose|cut|video, "prompt", "neg"?, "seconds"?, "source"?, "exit"?}``.

    python -m explainer_engine.scripting.shot_prompt_lint <shots.json>   # a list of shots or {"shots": [...]}
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

KINDS = ("keyframe", "nextpose", "cut", "video")

# KP-01: a bare role word cannot be found among several people ("the woman points" painted a stranger)
ROLE = re.compile(r"\b(the|a|an|one|another|some)\s+(woman|man|girl|boy|person|guy|lady|kid|child)\b(?!\s+(with|in|wearing|"
                  r"holding|who|from|on)\b)", re.I)
NOBODY = re.compile(r"\b(someone|somebody)\b", re.I)
# KP-03: verbs that carry a hero to the frame's edge (the farm clip ended on an empty barn)
EXIT = re.compile(r"\b(runs?|running|walks?|walking|gallops?|galloping|rides?|riding|drives?|driving)\s+(after|off|away|out)\b|"
                  r"\bheading\s+(into|to|toward|towards|off)\b|\bheads?\s+(into|off|away)\b|\b(flees|flee|fleeing|leaves|"
                  r"exits?|disappears?)\b|\bout of (the )?frame\b", re.I)
IN_FRAME = re.compile(r"\b(stays?|remains?|keeps?|kept)\b[^.;]*\bin (the )?frame\b|\bin frame\b", re.I)
# KP-04: one camera sentence
CAMERA = re.compile(r"\b(static|locked|locked-off|fixed|still) camera\b|\bcamera\s+(follows|tracks|pans|pushes|pulls|tilts|"
                    r"dollies|cranes|rises|travels|moves|holds|stays|orbits|trucks)\b|\b(slow )?(push-in|push in|pull-out|"
                    r"pull out|whip pan|pan left|pan right|tracking shot|dolly)\b", re.I)
MOVES = re.compile(r"\b(follows|tracks|pans|pushes|pulls|tilts|dollies|cranes|rises|travels|orbits|trucks|push-in|push in|"
                   r"pull-out|pull out|whip pan|pan left|pan right|tracking shot|dolly)\b", re.I)
# KP-05: a fast vehicle smears small heroes unless the camera travels with it
VEHICLE = re.compile(r"\b(moving|speeding|racing|rushing) (train|car|bus|cart|wagon|boat|ship)\b|\bgalloping\b|\bat full speed\b",
                     re.I)
FOLLOW = re.compile(r"\bcamera\s+(follows|tracks|travels|moves with)\b|\btracking shot\b", re.I)
# KP-07: a next pose changes poses only; a framing word re-frames the shot
FRAMING = re.compile(r"\b(close-up|close up|closeup|wide shot|wide view|medium shot|long shot|zoom(s|ed|ing)?( in| out)?|"
                     r"pan(s|ning)?|angle|from behind|from above|from below|overhead|bird's-eye|view of|seen from|"
                     r"camera (moves|pans|tilts|zooms|pulls|pushes))\b", re.I)
# KP-09: the negative prompt never names our own style (LTX's stock negative does)
OWN_STYLE = re.compile(r"\b(cartoon\w*|exaggerated\w*|styli[sz]ed|illustrat\w*|drawing|drawn|2d|flat colou?rs?|flat lighting|"
                       r"outlines?|caricatur\w*|distorted proportions|motion blur|anime|comic)\b", re.I)
# KP-12: a shot with only small verbs freezes (ice age clip, timid IC layouts)
STRONG = re.compile(r"\b(throws?|flails?|jumps?|leaps?|falls?|slips?|stumbles?|trips?|ducks?|recoils?|jerks?|flinch(es)?|grabs?|"
                    r"points?|shouts?|screams?|yells?|waves?|stamps?|bucks?|spins?|swings?|slams?|kicks?|punch(es)?|pushes?|"
                    r"pulls?|shakes?|shoves?|lunges?|crouch(es)?|hiss(es)?|splash(es)?|claps?|dances?|tumbles?|dives?|"
                    r"catches?|drops?|lifts?|raises?|bangs?|hugs?|gasps?|covers?|tips?|bares?|snarls?|roars?|bites?)\b", re.I)

SOUNDS = re.compile(r"\bsounds?\s*:\s*(.+)$", re.I | re.S)


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _action(text: str) -> str:
    """The prompt without its style sentence and its sound list."""
    text = SOUNDS.sub("", text)
    parts = _sentences(text)
    if parts and re.search(r"\b(animation|wldnk|style)\b", parts[0], re.I) and len(parts) > 1:
        parts = parts[1:]
    return " ".join(parts)


def _clauses(text: str) -> int:
    return len([c for c in re.split(r"[,;]|\bwhile\b|\bthen\b", text) if STRONG.search(c) or re.search(r"\b\w+s\b", c)])


def check_shot(shot: dict) -> list[dict]:
    sid = shot.get("id", "?")
    kind = shot.get("kind")
    prompt = str(shot.get("prompt", ""))
    out: list[dict] = []

    def add(rule: str, sev: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": sid, "detail": detail})

    if kind not in KINDS:
        add("KP-00", "FAIL", f"kind must be one of {KINDS}")
        return out
    action = _action(prompt) if kind == "video" else SOUNDS.sub("", prompt)
    for m in ROLE.finditer(action):
        add("KP-01", "FAIL", f"'{m.group(0)}' is a bare role word: name the person by what the picture shows "
                             "(hair, clothes colour, a prop)")
    for m in NOBODY.finditer(action):
        add("KP-01", "FAIL", f"'{m.group(0)}' names nobody: say who")
    if kind in ("nextpose", "video") and _clauses(action) > 4:
        add("KP-02", "REVIEW", f"{_clauses(action)} action clauses: one main actor named first, the others react small")
    if kind == "nextpose":
        for m in FRAMING.finditer(action):
            add("KP-07", "FAIL", f"'{m.group(0)}' re-frames a next pose: poses only, a new framing is a cut")
        if shot.get("source", "master") != "master":
            add("KP-08", "FAIL", f"drawn from '{shot.get('source')}': every next pose is drawn from the master frame")
    if kind == "video":
        if not shot.get("exit"):
            for m in EXIT.finditer(action):
                add("KP-03", "FAIL", f"'{m.group(0)}' takes a hero out of the frame; set exit: true only when the story wants it")
            if not IN_FRAME.search(action):
                add("KP-03", "REVIEW", "say that the heroes stay in frame")
        if not CAMERA.search(action):
            add("KP-04", "FAIL", "no camera sentence: write 'Static camera.' or the one move")
        elif len({m.group(0).lower() for m in MOVES.finditer(action)}) > 1:
            add("KP-04", "REVIEW", "more than one camera move: one shot, one move")
        if VEHICLE.search(action) and not FOLLOW.search(action):
            add("KP-05", "REVIEW", "a fast vehicle: let the camera travel with it and keep the heroes large")
        seconds = float(shot.get("seconds", 0) or 0)
        if seconds > 10:
            add("KP-06", "FAIL", f"{seconds:g} s: at most 10 s, split the action into two shots")
        elif seconds > 8:
            add("KP-06", "REVIEW", f"{seconds:g} s: over 8 s")
        sounds = SOUNDS.search(prompt)
        if sounds and len([s for s in re.split(r"[,;]", sounds.group(1)) if s.strip(" .")]) > 3:
            add("KP-11", "REVIEW", "more than three sounds: keep three, the loudest once")
        if not STRONG.search(action):
            add("KP-12", "REVIEW", "no big action verb: give the actor a start, a peak and a settle with body parts")
    neg = str(shot.get("neg", ""))
    for m in OWN_STYLE.finditer(neg):
        add("KP-09", "FAIL", f"the negative prompt names our own style: '{m.group(0)}'")
    return out


def check(shots: list[dict]) -> list[dict]:
    out = [f for shot in shots for f in check_shot(shot)]
    firsts = {_sentences(str(s.get("prompt", "")))[0] for s in shots
              if s.get("kind") == "video" and _sentences(str(s.get("prompt", "")))}
    if len(firsts) > 1:
        out.append({"rule": "KP-10", "severity": "REVIEW", "where": "video shots",
                    "detail": f"{len(firsts)} different style sentences: one fixed style sentence in every shot"})
    return out


def main(argv: list[str]) -> int:
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    shots = data["shots"] if isinstance(data, dict) else data
    found = check(shots)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(f"{len(shots)} shot(s), {fails} FAIL, {len(found) - fails} REVIEW")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
