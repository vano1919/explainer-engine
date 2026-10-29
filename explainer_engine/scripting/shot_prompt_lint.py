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

from explainer_engine.standards import sourced_rules

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
                    r"catches?|drops?|lifts?|raises?|bangs?|hugs?|gasps?|covers?|tips?|bares?|snarls?|roars?|bites?|jabs?|stomps?|"
                    r"whirls?|staggers?|flings?|hurls?|yanks?|slaps?|smacks?|bolts?|scrambles?|"
                    r"collapses?|topples?)\b", re.I)

SOUNDS = re.compile(r"(?:\bsounds?\s*:|\bwe hear\b)\s*(.+)$", re.I | re.S)
# KP-17: a named feeling leaves the face neutral unless the sentence says what the face or body does (LTX-2 guide)
EMOTION = re.compile(r"\b(sad|happy|angry|scared|afraid|anxious|nervous|worried|surprised|shocked|excited|confused|"
                     r"embarrassed|ashamed|proud|jealous|frustrated|terrified|annoyed|disappointed|hopeful|relieved|"
                     r"emotional|upset|furious|desperate|determined)\b", re.I)
BODY = re.compile(r"\b(eyes?|brows?|eyebrows?|mouth|lips?|jaw|teeth|grin\w*|frown\w*|smil\w*|tears?|cheeks?|nose|chin|"
                  r"shoulders?|hands?|fists?|fingers?|arms?|chest|knees?|legs?|feet|head|neck|back|body|face|"
                  r"trembl\w*|shak\w*|sweat\w*|gasp\w*|blink\w*|wince\w*|squint\w*|pout\w*|slump\w*)\b", re.I)
# KP-21: score music belongs to the edit (one music at a time, ED-03); only music with a visible source is asked of LTX
MUSIC = re.compile(r"\bmusic\b|\bsoundtrack\b|\bscore\b|\bmelody\b", re.I)
# KP-23: quality words do nothing; readable text is the edit's (captions, cards), the models garble it
BUZZ = re.compile(r"\b(8k|4k|uhd|hdr|masterpiece|best quality|high quality|ultra[- ]detailed|hyper[- ]?realistic|"
                  r"photorealistic|award[- ]winning|trending on artstation|sharp focus|highly detailed)\b", re.I)
TEXT_ASK = re.compile(r"\b(sign|banner|poster|caption|label|title|headline)s?\s+(that\s+)?(says?|reads?|reading|saying|with the "
                      r"words?)\b|\btext\s+(reading|that says|saying)\b|\bwritten\s+on\b", re.I)
# KP-24: our cartoons hold most frames (drawn on twos); "smooth, natural motion" asks for the floaty motion LT-57 flags
SMOOTH = re.compile(r"\b(smooth|fluid|natural|realistic|lifelike)\b[^.]{0,20}\b(motion|movement|animation)\b", re.I)
# BP-102: a video prompt is one paragraph of four to eight sentences, not a page
VIDEO_WORDS = sourced_rules.T("BP-102", "video_words")
# BP-100: lip-sync budget of a spoken line
SPEECH_WPS = sourced_rules.T("BP-100", "words_per_second")
SPEECH_SETTLE_S = sourced_rules.T("BP-100", "settle_s")
QUOTE = re.compile(r'"([^"]+)"')


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _action(text: str) -> str:
    """The prompt without its style sentence and its sound list."""
    text = SOUNDS.sub("", text)
    parts = _sentences(text)
    if parts and re.search(r"\b(animation|wldnk|style)\b", parts[0], re.I) and len(parts) > 1:
        parts = parts[1:]
    return " ".join(parts)


FIXED = re.compile(r"\bstays? in frame\b|\bnobody speaks\b|\bsame characters\b|\bnobody new appears\b|\bstatic camera\b|"
                   r"^the camera\b|\"", re.I)


def _acting(clause: str) -> bool:
    return bool(STRONG.search(clause) or re.search(r"\b\w+s\b", clause))


def _clauses(text: str) -> int:
    """Acting clauses. The formula sentences (in frame, camera, nobody speaks, a quoted line) act on nobody; one actor's
    'X, then Y, and Z' chain (KP-12's start, peak and settle) is one clause per semicolon part."""
    n = 0
    for sentence in _sentences(text.replace("nextpose, a later frame of the same continuous animated shot, same camera:", "")):
        if FIXED.search(sentence):
            continue
        if ";" in sentence or re.search(r",\s+then\b", sentence):
            n += sum(1 for part in sentence.split(";") if _acting(part))
        else:
            n += len([c for c in re.split(r"[,;]|\bwhile\b|\bthen\b", sentence) if _acting(c)])
    return n


def check_shot(shot: dict, names: list[str] | None = None) -> list[dict]:
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
            if not IN_FRAME.search(action) and shot.get("people", 1):
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
        if not STRONG.search(action) and shot.get("mode") not in ("insert", "establish"):
            add("KP-12", "REVIEW", "no big action verb: give the actor a start, a peak and a settle with body parts")
        spoken = QUOTE.findall(prompt)
        if spoken and seconds:
            n = sum(len(q.split()) for q in spoken)
            room = SPEECH_WPS * max(0.0, seconds - 2 * SPEECH_SETTLE_S)
            if n > room:
                add("KP-18", "REVIEW", f"{n} spoken words in {seconds:g} s: at most {room:.0f} lip-sync (BP-100)")
        if re.search(r"\b(says?|said|shouts?|whispers?|asks?|yells?|mutters?|speaks?)\b", action, re.I) and not spoken \
                and not re.search(r"\bnobody speaks\b", action, re.I):
            add("KP-18", "REVIEW", "someone speaks but no words are in quotes: the model invents gibberish")
        heard = SOUNDS.search(prompt)
        if heard and MUSIC.search(heard.group(1)) and not shot.get("diegetic_music"):
            add("KP-21", "REVIEW", "music in the clip's sound: the score is added in the edit; ask only for music with "
                                   "a visible source (set diegetic_music)")
        first = _sentences(prompt)[0] if _sentences(prompt) else ""
        if SMOOTH.search(first):
            add("KP-24", "REVIEW", f"'{SMOOTH.search(first).group(0)}' in the style sentence asks for floaty motion; our "
                                   "cartoons hold poses between quick moves")
        lo, hi = VIDEO_WORDS
        n_words = len(prompt.split())
        if not lo <= n_words <= hi:
            add("KP-25", "REVIEW", f"{n_words} words: a video prompt is one paragraph of {lo}-{hi} words (BP-102)")
    if kind in ("keyframe", "video"):
        for sentence in _sentences(action):
            if EMOTION.search(sentence) and not BODY.search(sentence):
                add("KP-17", "REVIEW", f"'{EMOTION.search(sentence).group(0)}' names a feeling: say what the face or body does")
    for m in BUZZ.finditer(prompt):
        add("KP-23", "REVIEW", f"'{m.group(0)}' does nothing for the model; spend the words on the action")
    for m in TEXT_ASK.finditer(prompt):
        add("KP-23", "REVIEW", f"'{m.group(0)}': readable text is garbled by the models; captions and cards are the edit's")
    unquoted = QUOTE.sub('""', prompt)  # a hero may say another's name aloud
    for name in names or []:
        if re.search(rf"\b{re.escape(name)}\b", unquoted):
            add("KP-22", "FAIL", f"'{name}' is a story name the model does not know: use the hero's tag")
    neg = str(shot.get("neg", ""))
    for m in OWN_STYLE.finditer(neg):
        add("KP-09", "FAIL", f"the negative prompt names our own style: '{m.group(0)}'")
    return out


def check(shots: list[dict], names: list[str] | None = None) -> list[dict]:
    out = [f for shot in shots for f in check_shot(shot, names)]
    firsts = {_sentences(str(s.get("prompt", "")))[0] for s in shots
              if s.get("kind") == "video" and _sentences(str(s.get("prompt", "")))}
    if len(firsts) > 1:
        out.append({"rule": "KP-10", "severity": "REVIEW", "where": "video shots",
                    "detail": f"{len(firsts)} different style sentences: one fixed style sentence in every shot"})
    return out


def main(argv: list[str]) -> int:
    data = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    shots = data["shots"] if isinstance(data, dict) else data
    found = check(shots, names=data.get("names") if isinstance(data, dict) else None)
    for f in found:
        print(f"{f['severity']:6} {f['rule']} {f['where']}: {f['detail']}")
    fails = sum(f["severity"] == "FAIL" for f in found)
    print(f"{len(shots)} shot(s), {fails} FAIL, {len(found) - fails} REVIEW")
    return 1 if fails else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
