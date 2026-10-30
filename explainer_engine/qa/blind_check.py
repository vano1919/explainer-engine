"""Blind description check (KG-23..KG-27, docs/KEYFRAME_GATE.md): the style spec every picture is held to, a describer that
looks at a picture WITHOUT its prompt, and a code comparison of that description with the scene contract. stdlib only.

ვანო (2026-10-25 16:27 Tbilisi): write the scene text, draw the picture, then describe the picture and compare the description
with the prompt's logic; where the description has question marks, look again; the describer has fixed rules, and so does
the prompt writer, so the whole loop stays consistent. A question list (KG-01..22) tells the judge what to look for, so it
tends to find it; a blind description has to say what is there first, and only code compares it with what was asked.

The contract is a keyframe_gate card (film_shots.gate_card, PR #24): ``people`` [{tag, where}], ``things`` [{name, plural,
count}], ``absent`` [str], ``relations`` [str]. The description follows ``DESCRIBE_RULES`` (JSON, below).

    python -m explainer_engine.qa.blind_check rules                       # the describer's instructions
    python -m explainer_engine.qa.blind_check compare <card.json> <description.json>
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

# KG-23: the wldnk style as seen on the approved eras sheet (eras_v5_1750_bf16.jpg, "იდეალურია", ვანო 2026-10-24) and in the
# captions of its training set. Each item is answered yes / no / ? for every picture; the order is the order of importance.
# RETIRED by D-80 (2026-10-26): kept as history, unchanged, and as the fixture of the mechanics' tests; nothing live reads it.
STYLE_SPEC_WLDNK_RETIRED = {
    "line": "bold, uneven, hand-inked black outlines on every figure, object and background shape; the thickness varies "
            "within one stroke (no thin uniform vector line, no painted shapes without an outline)",
    "figures": "lanky, angular cartoon bodies with thin limbs, big heads and noses, bulging round eyes with tiny pupils and "
               "exaggerated expressions (not anime, not chibi, not realistic proportions; not every face the same long nose)",
    "colour": "earthy, slightly muted base colours with a few vivid glowing accents (fire, lamps, neon, lightning); "
              "neither grey and washed out nor neon everywhere",
    "texture": "chalky, painterly background with visible grain and brush texture; figures in flat fills with light shading "
               "(no smooth vector gradients, no 3D render, no photo, no oil-painting chiaroscuro)",
    "detail": "a busy world: props, clutter and background detail drawn with the same ink line as the figures",
    "light": "one clear light source with a warm-cool contrast",
}
# Suspended by D-80 (2026-10-26): the retired spec was measured on the banned wldnk look (KG-23, docs/KEYFRAME_GATE.md); the xworld_v2
# spec is written only after the creator rates the new look (OR-22). While suspended the live spec is empty, `compare` and
# `style_verdict` answer REVIEW, and `keyframe_gate` shows its KG-22 style row as REVIEW. The one home of the flag.
STYLE_SPEC: dict = {}
STYLE_SUSPENDED = True
# kept as a name (history), unused while suspended: KG-23 auto half, DINOv2 vs the 20 eras cells (compose/style_score), the weakest
# cell against the other 19; calibrated on the banned look, so a score in either direction says nothing about xworld_v2
STYLE_SCORE_MIN = 0.557


def describe_rules(spec: dict) -> str:
    """The describer's instructions; the style item and the ``style`` answer key exist only when a spec is given."""
    style_rule = f"7. Answer each style item with yes, no or ?: {json.dumps(spec, ensure_ascii=False)}\n" if spec else ""
    style_key = f'\n  "style": {{{", ".join(f'"{k}": "yes|no|?"' for k in spec)}}},' if spec else ""
    return f"""You describe one picture for a checker that never sees it. You are NOT told what the picture was meant to show.
Rules:
1. Describe only what is visible. Never guess a story, a name or an intention.
2. Count every kind of person, animal and object by scanning the whole picture corner to corner, including the background
   and the edges; a small far copy counts too (a second small bus far away is a second bus).
3. Place each item with one of: left, center, right, plus front or back when it is clearly near or far
   (e.g. "left_back"). Say what it stands or rests on.
4. Name things with plain common nouns ("bus", "mammoth", "building", "road"), the colour first when it is clear
   ("yellow bus"). People are described by look: hair, glasses, clothes, colours, age.
5. When you are not sure (a count, a place, whether something is real or painted), write "?" in that field and add a line
   to "uncertain" saying what is unclear. Never resolve doubt by guessing.
6. Report written text or letters, numbers or lines drawn over the picture, anything floating without support, and broken
   anatomy (extra or missing limbs or fingers, a thing stuck in a face).
{style_rule}Answer with JSON only:
{{"people": [{{"look": str, "where": str, "action": str, "on": str}}],
  "animals": [{{"name": str, "count": int|"?", "where": str}}],
  "things": [{{"name": str, "count": int|"?", "where": str}}],
  "setting": str, "light": str, "text": bool, "overlays": bool, "floating": [str], "anatomy": [str],{style_key}
  "uncertain": [str]}}"""


DESCRIBE_RULES = describe_rules(STYLE_SPEC)
DESCRIBE_RULES_WLDNK_RETIRED = describe_rules(STYLE_SPEC_WLDNK_RETIRED)

# KG-25: words that name the same kind of thing; kept short on purpose (a missing synonym gives a REVIEW, never a false PASS)
SYNONYMS = {"bus": {"bus", "coach", "school bus", "minibus"}, "building": {"building", "house", "skyscraper", "tower",
            "city", "town", "skyline", "block"}, "road": {"road", "street", "highway", "asphalt", "pavement"},
            "car": {"car", "truck", "van", "vehicle"}, "mammoth": {"mammoth", "elephant"}}


def _kind(name: str) -> str:
    n = re.sub(r"[^a-z ]", "", name.lower())
    for kind, words in SYNONYMS.items():
        if any(re.search(rf"\b{w}s?\b", n) for w in words):
            return kind
    words = n.split()
    return words[-1].rstrip("s") if words else n


def _count(items: list[dict], kind: str) -> int | str:
    """Total count of one kind in a description; "?" when any matching entry is unsure."""
    total = 0
    for it in items:
        if _kind(it.get("name", "")) == kind:
            c = it.get("count", 1)
            if not isinstance(c, int):
                return "?"
            total += c
    return total


def _named_in_scene(text: str, scene: str) -> bool:
    """KG-27: a floating thing the scene text itself names (steam, sparks, a flying hat) is meant to float."""
    words = [w for w in re.findall(r"[a-z]{4,}", text.lower()) if w not in {"with", "from", "above", "near", "that"}]
    scene = scene.lower()
    return any(re.search(rf"\b{re.escape(w.rstrip('s'))}", scene) for w in words)


def compare(card: dict, desc: dict, scene: str = "", *, spec: dict | None = None) -> dict:
    """KG-25: the description against the contract. FAIL = a hard mismatch; REVIEW = a "?" or something the code cannot
    match, which gets a second, single-question look (KG-26) before anyone sees the picture. ``scene`` = the scene text:
    a floating thing it names is meant to float (KG-27); a named thing counted 0 is a REVIEW (the describer may have used
    another noun), never a FAIL. ``spec`` is the style spec (default ``STYLE_SPEC``); with none, the style half is suspended
    (D-80) and says so in one REVIEW row, so a result is never a silent PASS."""
    spec = STYLE_SPEC if spec is None else spec
    fails, reviews = [], []
    items = list(desc.get("things", [])) + list(desc.get("animals", []))
    for t in card.get("things", []):
        kind, want = _kind(t["name"]), t.get("count", 1)
        got = _count(items, kind)
        if got == "?":
            reviews.append({"code": "KG-25", "what": f"count of {t['name']}", "want": want, "got": "?"})
        elif got == 0 and want:
            reviews.append({"code": "KG-25", "what": f"count of {t['name']}", "want": want, "got": 0})
        elif got != want:
            fails.append({"code": "KG-25", "what": f"count of {t['name']}", "want": want, "got": got})
    for a in card.get("absent", []):
        kind = _kind(a)
        got = _count(items, kind)
        if got == "?":
            reviews.append({"code": "KG-25", "what": f"absent {a}", "want": 0, "got": "?"})
        elif got:
            fails.append({"code": "KG-25", "what": f"absent {a}", "want": 0, "got": got})
    people = desc.get("people", [])
    want_people = len(card.get("people", []))
    if want_people:
        # KG-27: the cast = the foreground people, plus animal characters (a monkey that steals the map is a cast member);
        # people placed far in the back are scenery of the place, not cast
        front = [x for x in people if "back" not in str(x.get("where", ""))]
        animals = sum(a.get("count", 1) for a in desc.get("animals", []) if isinstance(a.get("count", 1), int))
        if want_people not in (len(people), len(front), len(front) + animals, len(people) + animals):
            fails.append({"code": "KG-25", "what": "number of people", "want": want_people, "got": len(people)})
    for flag, label in (("text", "written text"), ("overlays", "lines or numbers over the picture")):
        if desc.get(flag):
            reviews.append({"code": "KG-25", "what": label, "want": False, "got": True})
    for f in desc.get("floating", []):
        if scene and _named_in_scene(f, scene):
            continue
        fails.append({"code": "KG-25", "what": f"floating: {f}", "want": "supported", "got": "floating"})
    for f in desc.get("anatomy", []):
        fails.append({"code": "KG-25", "what": f"anatomy: {f}", "want": "whole", "got": f})
    style = desc.get("style", {})
    if not spec:
        reviews.append({"code": "KG-23", "what": "style spec suspended by D-80", "want": "a spec rated by the creator on xworld_v2",
                        "got": "none"})
    for k in spec:
        v = str(style.get(k, "?")).lower()
        if v == "no":
            fails.append({"code": "KG-23", "what": f"style {k}", "want": "yes", "got": "no"})
        elif v != "yes":
            reviews.append({"code": "KG-23", "what": f"style {k}", "want": "yes", "got": v})
    for u in desc.get("uncertain", []):
        reviews.append({"code": "KG-26", "what": u, "want": "sure", "got": "?"})
    status = "FAIL" if fails else "REVIEW" if reviews else "PASS"
    return {"status": status, "fails": fails, "reviews": reviews,
            "relations_to_check": list(card.get("relations", []))}   # relations stay with the question gate (KG-06)


def second_look(item: dict) -> str:
    """KG-26: one focused question for one doubtful item, asked of a fresh look at the whole picture."""
    return (f"Look at the whole picture again, corner to corner, including the far background. Question: {item['what']}? "
            "Answer with a number, yes or no, and one short reason.")


def style_verdict(score: float, desc_style: dict, *, spec: dict | None = None) -> str:
    """KG-23: both halves must pass. The auto score alone passed flat vector frames (2026-10-25: 0.56-0.69). While the style is
    suspended (D-80, no spec) the answer is REVIEW whatever the score: 0.557 was calibrated on the banned look."""
    spec = STYLE_SPEC if spec is None else spec
    if not spec:
        return "REVIEW"
    if score < STYLE_SCORE_MIN or any(str(desc_style.get(k, "?")).lower() == "no" for k in spec):
        return "FAIL"
    if any(str(desc_style.get(k, "?")).lower() != "yes" for k in spec):
        return "REVIEW"
    return "PASS"


def main(argv: list[str]) -> int:
    if argv and argv[0] == "rules":
        print(DESCRIBE_RULES)
        return 0
    if len(argv) == 3 and argv[0] == "compare":
        card = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
        desc = json.loads(Path(argv[2]).read_text(encoding="utf-8"))
        print(json.dumps(compare(card, desc), indent=1, ensure_ascii=False))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
