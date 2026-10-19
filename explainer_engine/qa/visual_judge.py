"""Visual QA judge (D-41, UR-24/UR-26): fixed questions, a strict JSON answer, a verdict. stdlib only.

``build_prompt`` writes the question list for a vision model; ``verdict`` turns its JSON into PASS / FAIL / REVIEW with the
reasons. The model call itself lives in ``imagegen.gemini.GeminiClient.judge`` (or a local vision model on the pod).
"""

from __future__ import annotations

import json
import re

QUESTIONS = {
    "adults": "Do all people look like adults (not children, not toddlers, no school-trip look)?",
    "era_objects": "Is any object or building visible that does not exist in the stated world AND is not worn or carried by the intended time-travelling visitors (their later-century clothes, spectacles, watches and pocket items are expected and are NOT a problem; flag only things like metal tools, pottery, tents, glass bottles, wheels or modern clothing on the hosts)?",
    "people_in_plate": "Does the picture show any person or animal figure? (answer true if any figure is visible)",
    "text": "Is any readable text, letters, numbers or logo visible (clock-face numerals on a pocket watch do not count)?",
    "one_light": "Does the picture have one clear light direction and one light source type?",
    "hero_match": "If a named hero is meant to appear, is that figure recognisable from the description (glasses, hair, coat)?",
    "too_early": "Does the picture show anything from the 'must NOT appear yet' list?",
    "mood": "Does the picture show the stated danger or emotion (not a calm postcard)?",
}
GOOD = {"adults": True, "era_objects": False, "text": False, "mood": True}  # FAIL when the answer differs
SOFT = {"one_light": True}  # REVIEW only: firelight against dusk is two lights on purpose in some beats


VISITORS_NOTE = "scientists from the 1700s to 1900s dropped into this world"  # Day 1 default; world.visitors_note overrides


def build_prompt(world: dict, meta: dict) -> str:
    """meta: {plate: bool, hero: str|None, stakes: str}. The answer is JSON only."""
    lines = [f"You review one painted picture for a video about: {world['topic']}.",
             f"The world is: {world['host'].get('place', '')}, {world['host'].get('when', '')}. "
             f"Things that do NOT exist there: {', '.join(world['absent'])}.",
             f"The scene intentionally shows {world.get('visitors_note') or VISITORS_NOTE}: they keep their own clothes.",
             f"What the picture should show: {meta.get('stakes', '')}.",
             "Answer ONLY a JSON object with a boolean for every key, plus a string 'why_<key>' for every key you answer true, "
             "naming exactly what you see, and a short 'note':"]
    if meta.get("not_yet"):
        lines.insert(3, f"Must NOT appear yet at this point of the story (it has not been made): {', '.join(meta['not_yet'])}.")
    for key, q in QUESTIONS.items():
        lines.append(f'  "{key}": {q}')
    if meta.get("hero"):
        lines.append(f'The named hero meant to appear is: {meta["hero"]}.')
    return "\n".join(lines)


def parse(answer: str) -> dict:
    m = re.search(r"\{.*\}", answer, re.S)
    if not m:
        raise ValueError("the judge returned no JSON")
    return json.loads(m.group(0))


def verdict(result: dict, meta: dict) -> dict:
    fails, review = [], []
    for key, want in GOOD.items():
        if key not in result:
            review.append(f"{key}: no answer")
        elif bool(result[key]) != want:
            fails.append(f"{key}: expected {want}")
    for key, want in SOFT.items():
        if key in result and bool(result[key]) != want:
            review.append(f"{key}: expected {want}")
    if meta.get("not_yet") and result.get("too_early"):
        fails.append(f"too_early: shows {', '.join(meta['not_yet'])} before the story makes it (UR-27)")
    if meta.get("plate") and result.get("people_in_plate"):
        fails.append("people_in_plate: a plate must show no figure (UR-20)")
    if meta.get("hero") and not result.get("hero_match", False):
        review.append("hero_match: the hero is not clearly recognisable")
    return {"status": "FAIL" if fails else "REVIEW" if review else "PASS", "fails": fails, "review": review,
            "note": result.get("note", "")}
