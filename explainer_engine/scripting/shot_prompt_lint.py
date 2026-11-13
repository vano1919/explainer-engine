
"""Shot prompts for animated shots: keyframe, next pose, cut and video (KP-01..KP-62, docs/SHOT_PROMPTS.md). stdlib only.

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
# KP-55 (creator 2026-11-07, Argon's review): a settle that freezes the figures; REVIEW, unmeasured on our clips
FROZEN_SETTLE = re.compile(r"\b(stands?|standing|kneels?|kneeling|sits?|sitting|holds?|waits?|stays?)\s+(?:\w+ly\s+)?still\b",
                           re.I)   # D-121: "stands completely still" (c3) too
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
# KP-47 (BP-172): a clip of a hyped zone names a fast action verb, not a slow gesture
FAST_ACTION_VERBS = tuple(sourced_rules.T("BP-172", "fast_action_verbs"))
SLOW_MODIFIERS = re.compile(r"\b(slow|slowly|gently|unhurried|leisurely|quietly|calmly)\b", re.I)
HYPED_ZONES = frozenset({"hook_0_30s", "early_30_90s", "late_third_480_660s", "climax_660_720s"})
SPEECH_WPS = sourced_rules.T("BP-100", "words_per_second")
SPEECH_SETTLE_S = sourced_rules.T("BP-100", "settle_s")
DIALOGUE_SHOT_MAX_S = sourced_rules.T("BP-108", "dialogue_shot_max_s")
NON_DIALOGUE_VIDEO_MAX_S = sourced_rules.T("BP-108", "non_dialogue_video_max_s")
# BP-108 is the scene; BP-172 one LTX generation of a J2/J4 shot (D-116): the same symbols as scripting/film_shots.py
LTX_CLIP_TARGET_S = tuple(sourced_rules.T("BP-172", "clip_target_s_band"))
LTX_CLIP_MAX_S = sourced_rules.T("BP-172", "middle_clip_s_band")[1]
QUOTE = re.compile(r'"([^"]+)"')
# KP-59 (the creator 2026-11-07 22:23, answer 1a; Gemini review of c3b): time labels split an LTX clip into separate shots; c3 said
# "In the first three seconds ... In the last two seconds" and came back with two jump cuts at ~2 s and ~6 s
TIMESTAMP = re.compile(r"\b\d+(?:\.\d+)?\s*(?:-|\u2013|to)\s*\d+(?:\.\d+)?\s*(?:s|secs?|seconds?)\b|"
                       r"\b(?:at|by|after|until)\s+\d+(?:\.\d+)?\s*(?:s|secs?|seconds?)\b|\b\d+(?:\.\d+)?\s*s\s*:|"
                       r"\bthe\s+(?:first|last|final|next|opening|closing)\s+(?:\w+\s+)?(?:seconds?|frames?)\b", re.I)
# KP-61: one LTX clip is one continuous shot; words that ask for an edit inside it
CONTINUOUS = re.compile(r"\bsingle,?\s+continuous\b|\bone\s+continuous\b|\bcontinuous,?\s+unbroken\b", re.I)
EDIT_ASK = re.compile(r"\b(cut|cuts|cutting)\s+to\b|\bnew shot\b|\bnext shot\b|\bscene changes\b|\bsmash cut\b|"
                      r"\bjump cut\b|\bmontage\b", re.I)
# KP-60: a held prop is named as kept in the hand (c3b: Marcus put the phone down at ~9 s)
KEEP_WORDS = re.compile(r"\b(keeps?|keeping|still|holds?|holding|raised|clutch\w*|grips?|gripping)\b", re.I)
DROP_WORDS = re.compile(r"\b(drops?|dropping|lowers?|lowering|puts?\s+(?:it\s+)?down|sets?\s+(?:it\s+)?down|lets?\s+go|"
                        r"pockets?|throws?\s+away)\b", re.I)
# KP-62: a camera move names the frame it ends on (LTX completes a move it can see the end of)
CAMERA_END = re.compile(r"\b(ends?|ending|settles?|settling|comes? to rest|stops?|stopping|arrives?|lands?)\s+(on|at|in)\b|"
                        r"\bfinal framing\b|\buntil\b[^.]*\bframe", re.I)


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
    # the next pose's fixed opening (after its trigger, film_shots.NEXT_FRAME) acts on nobody
    for sentence in _sentences(text.replace("a later frame of the same continuous animated shot, same camera:", "")):
        if FIXED.search(sentence):
            continue
        if ";" in sentence or re.search(r",\s+then\b", sentence):
            n += sum(1 for part in sentence.split(";") if _acting(part))
        else:
            n += len([c for c in re.split(r"[,;]|\bwhile\b|\bthen\b", sentence) if _acting(c)])
    return n


def check_shot(shot: dict, names: list[str] | None = None) -> list[dict]:
    if 'shot_id' in shot and 'generation_mode' in shot:
        return check_v4_shot(shot)
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
        for m in FROZEN_SETTLE.finditer(action):
            add("KP-55", "FAIL", f"'{m.group(0)}' freezes the clip: name small motions (breathing, blinking, the fire flickering)")
        if not CAMERA.search(action):
            add("KP-04", "FAIL", "no camera sentence: write 'Static camera.' or the one move")
        elif len({m.group(0).lower() for m in MOVES.finditer(action)}) > 1:
            add("KP-04", "FAIL", "more than one camera move: one shot, one move")
        for m in TIMESTAMP.finditer(prompt):
            add("KP-59", "FAIL", f"'{m.group(0)}' is a time label: LTX reads it as a new shot; write one flowing paragraph")
        if shot.get("route") in ("J2", "J4") or shot.get("ltx"):
            if not CONTINUOUS.search(prompt):
                add("KP-61", "FAIL", "say 'a single continuous unbroken shot': one LTX clip is one shot")
            for m in EDIT_ASK.finditer(action):
                add("KP-61", "FAIL", f"'{m.group(0)}' asks for an edit inside one clip")
            moves = {m.group(0).lower() for m in MOVES.finditer(action)}
            if moves and not (CAMERA_END.search(action) or shot.get("camera_end")):
                add("KP-62", "FAIL", f"the camera move ({', '.join(sorted(moves))}) names no end framing ('... ends on ...')")
        for prop in shot.get("held_props", []):
            kept = [s for s in _sentences(action) if prop.lower() in s.lower() and KEEP_WORDS.search(s)]
            if not kept:
                add("KP-60", "FAIL", f"held prop '{prop}': say it stays in the hand ('keeps the {prop} raised in his right hand')")
            if not shot.get("prop_change"):
                drop = re.compile(DROP_WORDS.pattern + r"\s+(?:the\s+|his\s+|her\s+|their\s+|its\s+)?(?:\w+\s+)?"
                                  + re.escape(prop) + r"\b", re.I)
                for m in drop.finditer(action):
                    add("KP-60", "FAIL", f"'{m.group(0)}': a held prop is not put down unless prop_change says so")
        if VEHICLE.search(action) and not FOLLOW.search(action):
            add("KP-05", "REVIEW", "a fast vehicle: let the camera travel with it and keep the heroes large")
        seconds = float(shot.get("seconds", 0) or 0)
        spoken = QUOTE.findall(prompt)
        if spoken and seconds > DIALOGUE_SHOT_MAX_S:
            add("KP-06", "REVIEW", f"{seconds:g} s dialogue/lip-sync shot: aim for at most {DIALOGUE_SHOT_MAX_S:g} s; do not split a non-dialogue action to meet this cap")
        elif not spoken and seconds > NON_DIALOGUE_VIDEO_MAX_S:
            add("KP-06", "REVIEW", f"{seconds:g} s non-dialogue video shot: above the {NON_DIALOGUE_VIDEO_MAX_S:g} s planning ceiling")
        if shot.get("route") in ("J2", "J4"):   # D-116: a video prompt of a J2/J4 shot drives one LTX clip (BP-172)
            lo, hi = LTX_CLIP_TARGET_S
            clip = float(shot.get("clip_seconds", seconds) or 0)
            if clip > LTX_CLIP_MAX_S:
                add("KP-49", sourced_rules.level("BP-172"), f"{clip:g} s for one LTX clip: at most {LTX_CLIP_MAX_S:g} s (BP-172)")
            elif clip and not lo <= clip <= hi:
                add("KP-49", "REVIEW", f"{clip:g} s for one LTX clip: plan {lo:g}-{hi:g} s (BP-172, D-116)")
        sounds = SOUNDS.search(prompt)
        if sounds and len([s for s in re.split(r"[,;]", sounds.group(1)) if s.strip(" .")]) > 3:
            add("KP-11", "FAIL", "more than three sounds: keep three, the loudest once")
        if not STRONG.search(action) and shot.get("mode") not in ("insert", "establish"):
            add("KP-12", "REVIEW", "no big action verb: give the actor a start, a peak and a settle with body parts")
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
        if shot.get("rhythm_zone") in HYPED_ZONES or shot.get("fast_action") is True:
            body = _action(prompt)
            if not any(re.search(rf"\b{v}\b", body, re.I) for v in FAST_ACTION_VERBS):
                add("KP-47", sourced_rules.level("BP-172", "REVIEW"),
                    "a hyped-zone clip names no fast action verb (" + ", ".join(FAST_ACTION_VERBS[:5]) + " ...): one brisk "
                    "action with a start, a peak and a settle")
            if SLOW_MODIFIERS.search(body):
                add("KP-47", sourced_rules.level("BP-172", "REVIEW"),
                    f"'{SLOW_MODIFIERS.search(body).group(0)}' asks for a slow read in a hyped zone")
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




VALID_CONTROL_MODALITIES = frozenset({"openpose", "depth", "canny", "camera_preset", "trajectory_ati_experimental"})


def check_v4_shot(
    shot: dict,
    *,
    style_anchor_token: str | None = None,
    spoken_texts: list[str] | None = None,
) -> list[dict]:
    """Validate a production_script.schema.json v4.0 ShotSpec against Stage 2/3 prompt and conditioning guardrails (D-123)."""
    sid = shot.get("shot_id", shot.get("id", "?"))
    out: list[dict] = []

    def add(rule: str, sev: str, detail: str) -> None:
        out.append({"rule": rule, "severity": sev, "where": sid, "detail": detail})

    gen_mode = shot.get("generation_mode")
    visual_type = shot.get("visual_type")
    kf = shot.get("keyframe_plan") or {}
    img_p = shot.get("image_prompt") or {}
    vid_p = shot.get("video_prompt") or {}
    ctrl = shot.get("selective_control")

    # 1. Single primary physical action guardrail
    primary_actions = vid_p.get("primary_action_count")
    if primary_actions != 1:
        add("KP-V4-ACTION", "FAIL", f"primary_action_count is {primary_actions!r}; must be exactly 1 primary physical action per shot")

    # 2. At most 1 camera move guardrail
    cam_moves = vid_p.get("camera_move_count")
    if cam_moves is None or not (0 <= int(cam_moves) <= 1):
        add("KP-V4-CAMERA", "FAIL", f"camera_move_count is {cam_moves!r}; must be 0 or 1")
    motion_prompt = str(vid_p.get("motion_prompt", ""))
    detected_moves = {m.group(0).lower() for m in MOVES.finditer(motion_prompt)}
    if len(detected_moves) > 1:
        add("KP-V4-CAMERA", "FAIL", f"motion_prompt names multiple camera moves ({sorted(detected_moves)}); at most 1 move allowed")

    # 3. Single control modality on WAN_CONTROL; null otherwise
    if gen_mode == "WAN_CONTROL":
        if not isinstance(ctrl, dict):
            add("KP-V4-CONTROL", "FAIL", "generation_mode is WAN_CONTROL but selective_control is missing")
        else:
            mod = ctrl.get("control_modality")
            if isinstance(mod, (list, tuple, set)) or mod not in VALID_CONTROL_MODALITIES:
                add("KP-V4-CONTROL", "FAIL", f"WAN_CONTROL requires exactly 1 valid control_modality in {sorted(VALID_CONTROL_MODALITIES)}, got {mod!r}")
            if not str(ctrl.get("escalation_reason", "")).strip():
                add("KP-V4-CONTROL", "FAIL", "WAN_CONTROL requires a non-empty escalation_reason")
    else:
        if ctrl is not None:
            add("KP-V4-CONTROL", "FAIL", f"selective_control must be null when generation_mode is {gen_mode!r}")

    # 4. End-frame consistency (WAN_FLF2V vs WAN_I2V / STILL_25D / MAP_25D)
    needs_end = kf.get("needs_end_frame")
    end_reason = kf.get("end_frame_reason")
    if gen_mode == "WAN_FLF2V":
        if needs_end is not True:
            add("KP-V4-ENDFRAME", "FAIL", "WAN_FLF2V requires keyframe_plan.needs_end_frame == True")
        if not (isinstance(end_reason, str) and len(end_reason.strip()) >= 5):
            add("KP-V4-ENDFRAME", "FAIL", "WAN_FLF2V requires a non-empty keyframe_plan.end_frame_reason")
        if not (isinstance(img_p.get("end_frame_prompt"), str) and len(img_p["end_frame_prompt"].strip()) >= 10):
            add("KP-V4-ENDFRAME", "FAIL", "WAN_FLF2V requires a non-empty image_prompt.end_frame_prompt")
    else:
        if needs_end is True:
            add("KP-V4-ENDFRAME", "FAIL", f"keyframe_plan.needs_end_frame is True on {gen_mode!r}; only WAN_FLF2V uses an end frame")

    # 5. Visual type vs generation_mode and layered collage parallax preset consistency
    if visual_type == "composed_illustration":
        if gen_mode not in ("COLLAGE_STILL", "STILL_25D"):
            add("KP-V4-MODE", "FAIL", f"composed_illustration must use COLLAGE_STILL (or legacy STILL_25D), got {gen_mode!r}")
        if not vid_p.get("parallax_preset"):
            add("KP-V4-PARALLAX", "FAIL", f"{gen_mode} requires a non-null video_prompt.parallax_preset")
    elif visual_type == "map_visualization":
        if gen_mode not in ("TACTILE_MAP", "MAP_25D"):
            add("KP-V4-MODE", "FAIL", f"map_visualization must use TACTILE_MAP (or legacy MAP_25D), got {gen_mode!r}")
        if not vid_p.get("parallax_preset"):
            add("KP-V4-PARALLAX", "FAIL", f"{gen_mode} requires a non-null video_prompt.parallax_preset")

    # 6. Style anchor token check
    start_prompt = str(img_p.get("start_frame_prompt", ""))
    if style_anchor_token and style_anchor_token.lower() not in start_prompt.lower():
        add("KP-V4-STYLE", "FAIL", f"start_frame_prompt is missing world_bible.style_anchor_token ({style_anchor_token!r})")

    # 7. Ban spoken dialogue strings leaked into image_prompt or video_prompt
    for field_name, prompt_text in (
        ("image_prompt.start_frame_prompt", start_prompt),
        ("image_prompt.end_frame_prompt", str(img_p.get("end_frame_prompt") or "")),
        ("video_prompt.motion_prompt", motion_prompt),
    ):
        if not prompt_text:
            continue
        quotes = QUOTE.findall(prompt_text)
        if quotes:
            add("KP-V4-DIALOGUE-LEAK", "FAIL", f"{field_name} contains quoted dialogue {quotes[0]!r}; spoken lines belong in audio_lines only")
        for line_txt in spoken_texts or []:
            cleaned = line_txt.strip()
            if len(cleaned) >= 12 and cleaned.lower() in prompt_text.lower():
                add("KP-V4-DIALOGUE-LEAK", "FAIL", f"{field_name} leaks spoken audio_line text {cleaned[:40]!r}")

    # 8. Anti-Loop-Boilerplate & Raw-ID Leak Gate (KP-NO-LOOP-BOILERPLATE)
    boilerplate_patterns = (
        "initial composition of",
        "completed motion cadence",
        "cinematic sequence at",
        "historical tableau of",
        "drive causal mechanism",
        "escalate dramatic stakes",
        "bold ink linework",
        "2.5d ink chronicle",
        "2.5d parallax",
        "2d flat cartoon",
        "anime comic book",
        "flat vector illustration",
    )
    raw_id_regex = re.compile(r"\b(loc_[a-z0-9_]+|char_[a-z0-9_]+|prop_[a-z0-9_]+|S(0[1-9]|1[0-6])_SH[0-9]{3})\b")
    sc_comp = shot.get("screen_composition") or {}
    for field_name, text_val in (
        ("image_prompt.start_frame_prompt", start_prompt),
        ("image_prompt.end_frame_prompt", str(img_p.get("end_frame_prompt") or "")),
        ("video_prompt.motion_prompt", motion_prompt),
        ("action_start_state", str(shot.get("action_start_state") or "")),
        ("action_end_state", str(shot.get("action_end_state") or "")),
        ("narrative_purpose", str(shot.get("narrative_purpose") or "")),
        ("screen_composition.foreground", str(sc_comp.get("foreground") or "")),
        ("screen_composition.midground", str(sc_comp.get("midground") or "")),
        ("screen_composition.background", str(sc_comp.get("background") or "")),
    ):
        if not text_val:
            continue
        low_val = text_val.lower()
        for bp in boilerplate_patterns:
            if bp in low_val:
                add(
                    "KP-NO-LOOP-BOILERPLATE",
                    "FAIL",
                    f"{field_name} contains robotic loop-generated boilerplate {bp!r}; write a concrete visual description of the scene",
                )
        m_id = raw_id_regex.search(text_val)
        if m_id:
            add(
                "KP-NO-LOOP-BOILERPLATE",
                "FAIL",
                f"{field_name} leaks raw database identifier {m_id.group(1)!r} instead of concrete visual nouns",
            )

    return out


def check_v4_script(doc: dict) -> list[dict]:
    """Run v4.0 shot prompt lints, unique-scene checks (D-124), anti-metronome Accordion Pacing checks,
    and anti-cookie-cutter segment template checks on production_script.json."""
    import statistics as _stats
    from collections import Counter as _Counter
    from explainer_engine.scripting import story_lint

    out: list[dict] = []
    wb = doc.get("world_bible") or {}
    style_token = wb.get("style_anchor_token")
    audio_lines = doc.get("audio_lines", [])
    spoken = [str(line.get("text", "")) for line in audio_lines if line.get("text")]
    seen_start_prompts: dict[str, str] = {}
    shots = doc.get("shots", [])
    segments = doc.get("segments", [])

    teaser_pairs = (
        {(str(s.get("shot_id")), str(s.get("teaser_of"))) for s in shots if s.get("teaser_of")}
        | {(str(s.get("teaser_of")), str(s.get("shot_id"))) for s in shots if s.get("teaser_of")}
    )
    for shot in shots:
        out.extend(check_v4_shot(shot, style_anchor_token=style_token, spoken_texts=spoken))
        sid = shot.get("shot_id", "?")
        sp = " ".join(str((shot.get("image_prompt") or {}).get("start_frame_prompt") or "").lower().split())
        if sp in seen_start_prompts and (str(sid), str(seen_start_prompts[sp])) not in teaser_pairs:
            out.append({
                "rule": "KP-V4-NO-DUPLICATE-PROMPT",
                "severity": "FAIL",
                "where": sid,
                "detail": f"Shot {sid} duplicates start_frame_prompt from {seen_start_prompts[sp]}; every shot must have a distinct scene prompt (no single-photo crop padding, D-124)"
            })
        elif sp and sp not in seen_start_prompts:
            seen_start_prompts[sp] = sid

    # 9. Anti-Metronome Shot Duration Gate (PV-NO-METRONOME-DURATIONS, BP-107 / Accordion Pacing)
    if len(shots) >= 6:
        shot_durs = [float(s.get("target_duration_seconds", 0.0)) for s in shots]
        dur_stdev = _stats.pstdev(shot_durs)
        if dur_stdev < 0.45:
            out.append({
                "rule": "PV-NO-METRONOME-DURATIONS",
                "severity": "FAIL",
                "where": "shots",
                "detail": (
                    f"Shot durations have robotic metronome uniformity (stdev={dur_stdev:.3f}s, mean={_stats.mean(shot_durs):.2f}s). "
                    "Cinematography requires Accordion Pacing driven by spoken line length and dramatic tension (target stdev >= 0.65s, range 1.8s-7.5s)."
                ),
            })

    # 10. Anti-Metronome Segment Duration & Shot-Count Gate (PV-NO-METRONOME-SEGMENTS, OR-15 / BP-75)
    if len(segments) >= 4:
        seg_durs = [float(seg.get("target_duration_seconds", 0.0)) for seg in segments]
        seg_dur_stdev = _stats.pstdev(seg_durs)
        shots_per_seg = [sum(1 for s in shots if s.get("segment_id") == seg.get("segment_id")) for seg in segments]
        shots_count_stdev = _stats.pstdev(shots_per_seg)
        if seg_dur_stdev < 3.0 and shots_count_stdev < 0.4:
            out.append({
                "rule": "PV-NO-METRONOME-SEGMENTS",
                "severity": "FAIL",
                "where": "segments",
                "detail": (
                    f"All {len(segments)} segments have robotic identical durations (stdev={seg_dur_stdev:.2f}s) "
                    f"and shot counts (stdev={shots_count_stdev:.2f}). Chapters must vary organically with narrative acts "
                    "(e.g. 35s cold open, 75s setup, 110s escalation, 50s crisis)."
                ),
            })

    # 11. Anti-Cookie-Cutter Segment Mode Pattern Gate (PV-NO-COOKIE-CUTTER-SEGMENTS)
    if len(segments) >= 4:
        seg_patterns = []
        for seg in segments:
            seg_id = seg.get("segment_id")
            modes = tuple(s.get("generation_mode") for s in shots if s.get("segment_id") == seg_id)
            if len(modes) >= 4:
                seg_patterns.append((seg_id, modes))
        if len(seg_patterns) >= 4:
            pattern_counts = _Counter(m for _, m in seg_patterns)
            most_common_pat, most_common_cnt = pattern_counts.most_common(1)[0]
            if most_common_cnt >= 3 or len(pattern_counts) <= len(seg_patterns) // 2:
                out.append({
                    "rule": "PV-NO-COOKIE-CUTTER-SEGMENTS",
                    "severity": "FAIL",
                    "where": "segments",
                    "detail": (
                        f"{most_common_cnt}/{len(seg_patterns)} segments repeat the exact same generation_mode sequence {list(most_common_pat)}. "
                        "Visual routing must follow each scene's unique dramatic action, never a loop template."
                    ),
                })

        # 12. Anti-Cookie-Cutter Dialogue Slot Gate (PV-NO-COOKIE-CUTTER-DIALOGUE)
        char_slot_patterns = []
        for seg in segments:
            seg_id = seg.get("segment_id")
            seg_lines = [l for l in audio_lines if l.get("segment_id") == seg_id]
            if len(seg_lines) >= 4:
                char_indices = tuple(i for i, l in enumerate(seg_lines) if l.get("speaker_type") == "character")
                if char_indices:
                    char_slot_patterns.append(char_indices)
        if len(char_slot_patterns) >= 4:
            slot_counts = _Counter(char_slot_patterns)
            top_slot, top_cnt = slot_counts.most_common(1)[0]
            if top_cnt >= 4 and top_cnt >= len(char_slot_patterns) * 0.65:
                out.append({
                    "rule": "PV-NO-COOKIE-CUTTER-DIALOGUE",
                    "severity": "FAIL",
                    "where": "audio_lines",
                    "detail": (
                        f"Character dialogue appears at the identical relative line indices {list(top_slot)} in {top_cnt}/{len(char_slot_patterns)} segments. "
                        "Place character dialogue organically only where dramatic confrontation demands it."
                    ),
                })


    # 13. Compelling Cinematic Hook Gate (YT-00-3SEC-KINETIC-HOOK, D-130 Creator Directive)
    # The hook must deploy the strongest video/audio material conceptually: rapid grab (shot 0 <= 3.8s, shots 0+1 <= 9.0s),
    # active visual motion or dramatic tension, and zero passive dead holds.
    if len(shots) >= 2:
        passive_hook_regex = re.compile(
            r"\b(stands? still|sits? quietly|stares? blankly|nothing happens|dead silence|frozen pose)\b",
            re.I,
        )
        sh0, sh1 = shots[0], shots[1]
        d0 = float(sh0.get("target_duration_seconds", 0.0))
        d1 = float(sh1.get("target_duration_seconds", 0.0))
        for idx, h_sh in enumerate((sh0, sh1)):
            h_sid = h_sh.get("shot_id", f"shot_{idx}")
            h_text = " ".join([
                str(h_sh.get("action_start_state") or ""),
                str(h_sh.get("action_end_state") or ""),
                str((h_sh.get("video_prompt") or {}).get("motion_prompt") or ""),
            ])
            if passive_hook_regex.search(h_text):
                out.append({
                    "rule": "YT-00-3SEC-KINETIC-HOOK",
                    "severity": "FAIL",
                    "where": h_sid,
                    "detail": f"Opening hook shot {h_sid} contains passive dead action; opening requires compelling visual/dramatic motion.",
                })
        if d0 > 3.8 or (d0 + d1) > 9.0:
            out.append({
                "rule": "YT-00-3SEC-KINETIC-HOOK",
                "severity": "FAIL",
                "where": sh0.get("shot_id", "S01_SH001"),
                "detail": (
                    f"Opening 2 hook shots are too slow ({d0:.1f}s + {d1:.1f}s = {d0+d1:.1f}s); "
                    "the opening requires rapid grab (shot 0 <= 3.8s, shots 0+1 <= 9.0s)."
                ),
            })

    out.extend(story_lint.lint_v4(doc))
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
