"""Suspended by D-80 (2026-10-26) for the new look: the shape below was measured on the banned wldnk look
and is rewritten from the 2.1 prompt-type test. LT-65 (docs/LORA_TRAINING.md): a prompt for the style LoRA has the shape of the prompts that drew the approved look: the
trigger, then a short story of the moment (a place, an action at its peak, someone's reaction, the bodies' caricature words,
a light source, one or two props), at most 40 words, with no camera, sizes or positions in the words. stdlib only.

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

TRIGGER = "wldnk style"
# word for word the end of every v5 training caption (dataset_style_v5/*.txt, 164 of 164); kept to recognise it
STYLE_TAIL = ("lanky angular cartoon characters with long noses, thin limbs and bulging round eyes with tiny pupils, bold "
              "uneven black ink outlines, chalky textured painterly background, muted earthy colours with vivid glowing accents")
MAX_WORDS = 40          # approved eras 19-29 words, v5 samples 19-33, captions' scene part median 19
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
INFERENCE = {"base": "Qwen/Qwen-Image-2.1", "lora": None, "lora_weight": 1.0, "dtype": "bfloat16",
             "size": [1280, 720], "steps": 30, "true_cfg": 4.0}  # D-80: one stack; no LoRA until the creator rates the new one
ABSOLUTES = (
    ("A1", "the prompt starts with the trigger 'wldnk style', once"),
    ("A2", f"the creator-rated LoRA (none yet, D-80) at weight 1.0, only on {INFERENCE['base']} in bf16, 30 steps, true_cfg 4; "
           "plain or in its edit mode with references (D-80)"),
    ("A3", "the negative prompt is exactly NEGATIVE"),
    ("A4", f"at most {MAX_WORDS} words: a place, an action at its peak, a reaction, caricature body words, a light source, "
           "one or two props"),
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


def check(prompt: str) -> list[dict]:
    out = []
    if not prompt.lower().startswith(TRIGGER):
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"does not start with '{TRIGGER}'"})
    n = len(prompt.split())
    if n > MAX_WORDS:
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"{n} words; the approved prompts have {MAX_WORDS} at most"})
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
        if it.get("kind") != "keyframe" and it.get("lora") != "style":
            continue
        found = check(it["prompt"])
        bad += any(f["severity"] == "FAIL" for f in found)
        for f in found:
            print(it.get("id", "?"), f["severity"], f["detail"])
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
