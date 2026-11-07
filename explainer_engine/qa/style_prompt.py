
"""D-80 (2026-10-26): the trigger check (A1) is live on the one stack, Qwen-Image-2.1 + the xworld LoRA; its word comes from
``training/lora_rules.json`` (``training/lora_rules.trigger()``, N-09). The rest of the shape below (word limit, caption tail,
body words) was measured on the banned wldnk look and stays as written until the 2.1 prompt-type test rewrites it; the eras
sheet comparison (A10, KG-22) stays suspended. LT-65 (docs/LORA_TRAINING.md): a prompt for the style LoRA has the shape of the prompts that drew the approved look: the
trigger, then a short story of the moment (a place, an action at its peak, someone's reaction, the bodies' caricature words,
a light source, one or two props), with no camera, sizes or positions in the words. stdlib only.

Word band (the creator, 2026-11-06 12:27 UTC, msg cmsg_01Hnu5zB86sjUj5GtTgaUkPWQ83nahs7XqJbJiNjko9vuk: "40 to 150 words, as much as
the scene's proportions and setting need"): a prompt over MAX_WORDS (150) FAILs; how long a scene's prompt is inside the band is
the prompt writer's choice, not this validator's. One measured exception stays a REVIEW: on the crowd and mass sub-categories
(CROWD_SUB_CATEGORIES) a prompt over CROWD_REVIEW_WORDS (90) drew clone soldiers that neither a redraw nor a fix-edit removed (asset
pod, 2026-11-06); 150 words are untested, and 337 broke the style on 2026-10-24. The composer's default moment stays
MOMENT_WORDS (40, the eras shape below).

Evidence (free analysis 2026-10-25, https://claude.ai/artifact/BCfwRAUtF34g9xcS1bjk6D):
- the 20 approved eras prompts are 19-29 words in that shape, and the v5 training samples drew the film's own heroes in the
  approved look from 19-33 words in it (HF lora_plan_2026-10-22/train_qwen_v5/output/samples, step 1750);
- the film prompts that lost the look were 73-337 words of standing figures, layout and grey light;
- the caption tail (all 164 v5 captions end with it) brings the look back but over-caricatures and adds long-nosed extras
  (style test 2026-10-25: 6 of 8 shots), and neither eras nor the samples had it. The tail rule of 2026-10-24 is retired.

    python -m explainer_engine.qa.style_prompt <prompts.json>    # FAIL/REVIEW per style-LoRA prompt
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from explainer_engine.cloud import pins as _pins
from explainer_engine.training import lora_rules

TRIGGER = lora_rules.trigger()  # one home (N-09, D-80)
# word for word the end of every v5 training caption (dataset_style_v5/*.txt, 164 of 164); kept to recognise it
STYLE_TAIL = ("lanky angular cartoon characters with long noses, thin limbs and bulging round eyes with tiny pupils, bold "
              "uneven black ink outlines, chalky textured painterly background, muted earthy colours with vivid glowing accents")
MAX_WORDS = 150         # the creator's band 40-150 (2026-11-06 12:27 UTC); was 40 (2026-10-25 analysis below)
MOMENT_WORDS = 40       # the composer's default moment: approved eras 19-29 words, v5 samples 19-33, captions' scene part median 19
CROWD_REVIEW_WORDS = 90   # measured 2026-11-06 (asset pod): 90 words drew clone soldiers in a crowd scene
CROWD_SUB_CATEGORIES = ("V1", "S3")   # battle / siege / formation and group tableau (visual/archetypes_ic.json sub_categories)
# light and colour words that wash the look out (the bus prompt's "flat grey daylight" on an "empty white" plain)
DULL = re.compile(r"\b(flat|overcast|dull|grey|gray|pale|washed[- ]out)(\s+(grey|gray|white|pale))?\s+(day)?light\b|"
                  r"\bempty white\b|\bplain (white|grey|gray) (snow|plain|sky|field)\b", re.I)
# camera, sizes and positions belong to the layout (boxes, composition), not to the words
LAYOUT = re.compile(r"\b(close-up|full[- ]body shot|wide shot|medium shot|eye level|low angle|high angle|camera|"
                    r"\d+\s*(%|percent|metres?|meters?|m\b)|of the frame( height)?|from the (left|right|top) edge|"
                    r"in the (center|centre) of the frame)\b", re.I)


# other media or art styles fight the LoRA's look (they are never allowed in a style-LoRA prompt, LT-66)
STYLE_CLASH = re.compile(r"\b(photo(graph)?|photoreal\w*|realistic|hyper-?real\w*|3d|cgi|render(ed|ing)?|anime|manga|pixar|"
                         r"disney|watercolou?r|oil painting|pixel art|unreal engine|octane|cinematic|in the style of)\b", re.I)

# LT-66: the absolutes. No episode look, scene, thread or test run changes them; only the creator's word does, and then
# this table, its test (tests/unit/test_style_prompt.py) and docs/LORA_TRAINING.md change together.
NEGATIVE = "text, lettering, letters, words, watermark, signature, photo, 3d render"
# D-83 / D-116 (2026-11-06): the LoRA and its weight come from config/cloud_pins.json models.loras.xworld_v2, their one home
_LORA = _pins.load()["models"]["loras"]["xworld_v2"]
INFERENCE = {"base": "Qwen/Qwen-Image-2.1", "lora": _LORA["id"], "lora_weight": _LORA["weight"], "dtype": "bfloat16",
             "size": [1280, 720], "steps": 30, "true_cfg": 4.0}  # D-80: one stack
ABSOLUTES = (
    ("A1", f"the prompt starts with the trigger '{TRIGGER}', once"),
    ("A2", f"the LoRA {INFERENCE['lora']} (checkpoint 3000, D-83) at weight {INFERENCE['lora_weight']:g} (creator 2026-10-31), only on {INFERENCE['base']} in bf16, 30 steps, true_cfg 4; "
           "plain or in its edit mode with references (D-80)"),
    ("A3", "the negative prompt is exactly NEGATIVE"),
    ("A4", f"at most {MAX_WORDS} words, as many as the scene's proportions and setting need (the creator's band 40-150, "
           f"2026-11-06): a place, an action at its peak, a reaction, caricature body words, a light source, the props; a crowd "
           f"scene over {CROWD_REVIEW_WORDS} words is a REVIEW"),
    ("A5", "no caption tail"),
    ("A6", "no camera, shot size, position, measurement or number in the words: layout lives in boxes and composition"),
    ("A7", "every figure's full tag is said once"),
    ("A8", "no other medium or art style (photo, 3d, anime, watercolour, cinematic ...)"),
    ("A9", "an episode look adds colour and light words only; it never replaces A1-A8"),
    ("A10", "every picture is compared with the approved eras sheet before the creator sees it (KG-22)"),
)


def shaped(prompt: str) -> str:
    """The approved shape's opening: the trigger first, once. (The caption tail is no longer added, LT-65.)"""
    p = prompt.strip().rstrip(".")
    if STYLE_TAIL in p:
        p = p.replace(", " + STYLE_TAIL, "").replace(STYLE_TAIL, "").strip().rstrip(",")
    return p if p.lower().startswith(TRIGGER) else f"{TRIGGER}, {p}"


with_tail = shaped      # the composer's old name (PR #24); it now returns the approved shape without the tail


def check(prompt: str, *, sub_category: str | None = None) -> list[dict]:
    out = []
    if not prompt.lower().startswith(TRIGGER):
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"does not start with '{TRIGGER}'"})
    n = len(prompt.split())
    if n > MAX_WORDS:
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"{n} words; the creator's band ends at {MAX_WORDS}"})
    elif n > CROWD_REVIEW_WORDS and sub_category in CROWD_SUB_CATEGORIES:
        out.append({"rule": "LT-65", "severity": "REVIEW",
                    "detail": f"{n} words on a crowd scene ({sub_category}): over {CROWD_REVIEW_WORDS} words drew clone soldiers "
                              "(asset pod 2026-11-06); shorten it or keep the crowd to Blender (J4)"})
    if STYLE_TAIL in prompt:
        out.append({"rule": "LT-65", "severity": "REVIEW", "detail": "the caption tail over-caricatures and adds long-nosed extras"})
    m = STYLE_CLASH.search(prompt)
    if m:
        out.append({"rule": "LT-66", "severity": "FAIL", "detail": f"'{m.group(0)}' names another medium or style (A8)"})
    m = DULL.search(prompt)
    if m:
        out.append({"rule": "LT-65", "severity": "REVIEW", "detail": f"'{m.group(0)}' washes the colours out"})
    m = LAYOUT.search(prompt)
    if m:
        out.append({"rule": "LT-65", "severity": "REVIEW", "detail": f"'{m.group(0)}': camera and sizes go to the layout"})
    return out


def main(argv: list[str]) -> int:
    items = json.loads(Path(argv[0]).read_text(encoding="utf-8"))
    if isinstance(items, dict):      # the composer's prompts.json: {"sheets": [...], "shots": [...], "gate": [...]}
        items = items.get("sheets", []) + items.get("shots", [])
    bad = 0
    for it in items:
        if it.get("kind") != "keyframe":  # moments and hero sheets; a next pose or a cut is an edit prompt (N-09)
            continue
        found = check(it["prompt"])
        bad += any(f["severity"] == "FAIL" for f in found)
        for f in found:
            print(it.get("id", "?"), f["severity"], f["detail"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
