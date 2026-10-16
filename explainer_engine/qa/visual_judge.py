"""Visual QA judge (D-41, UR-24/UR-26): fixed questions, a strict JSON answer, a verdict. stdlib only.

``build_prompt`` writes the question list for a vision model; ``verdict`` turns its JSON into PASS / FAIL / REVIEW with the
reasons. The model call itself lives in ``imagegen.gemini.GeminiClient.judge`` (or a local vision model on the pod).
"""

from __future__ import annotations

import json
import re

QUESTIONS = {
    "adults": "Do all people look like adults (not children, not toddlers, no school-trip look)?",
    "era_objects": "Is any object, clothing or building visible that does not exist in the stated world?",
    "people_in_plate": "Does the picture show any person or animal figure? (answer true if any figure is visible)",
    "text": "Is any text, letter, number or logo visible?",
    "one_light": "Does the picture have one clear light direction and one light source type?",
    "hero_match": "If a named hero is meant to appear, is that figure recognisable from the description (glasses, hair, coat)?",
    "mood": "Does the picture show the stated danger or emotion (not a calm postcard)?",
}
GOOD = {"adults": True, "era_objects": False, "text": False, "one_light": True, "mood": True}


def build_prompt(world: dict, meta: dict) -> str:
    """meta: {plate: bool, hero: str|None, stakes: str}. The answer is JSON only."""
    lines = [f"You review one painted picture for a video about: {world['topic']}.",
             f"The world is: {world['host'].get('place', '')}, {world['host'].get('when', '')}. "
             f"Things that do NOT exist there: {', '.join(world['absent'])}.",
             f"What the picture should show: {meta.get('stakes', '')}.",
             "Answer ONLY a JSON object with a boolean for every key and a short 'note':"]
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
    if meta.get("plate") and result.get("people_in_plate"):
        fails.append("people_in_plate: a plate must show no figure (UR-20)")
    if meta.get("hero") and not result.get("hero_match", False):
        review.append("hero_match: the hero is not clearly recognisable")
    return {"status": "FAIL" if fails else "REVIEW" if review else "PASS", "fails": fails, "review": review,
            "note": result.get("note", "")}
