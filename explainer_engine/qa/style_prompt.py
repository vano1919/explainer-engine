"""LT-65 (docs/LORA_TRAINING.md): a keyframe prompt for the style LoRA keeps the shape it was trained on, or the LoRA's look
fades into a generic cartoon. stdlib only.

Evidence (2026-10-24, one pod, one LoRA file, one pipeline, seeds 7 and 8): the approved eras prompt (31 words, caricature
words "thin", "arguing", a fire, a frozen lake) drew the approved look; the film's bus prompt (337 words, no caricature word,
"flat grey daylight", "empty white horizon", every tag repeated) drew flat, round, grey pictures. All 164 training captions
of v5 are "wldnk style, <scene>, " + STYLE_TAIL; the film composer sent the trigger without the tail.

    python -m explainer_engine.qa.style_prompt <prompts.json>    # the composer's output: FAIL/REVIEW per keyframe prompt
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

TRIGGER = "wldnk style"
# word for word the end of every v5 training caption (dataset_style_v5/*.txt, 164 of 164)
STYLE_TAIL = ("lanky angular cartoon characters with long noses, thin limbs and bulging round eyes with tiny pupils, bold "
              "uneven black ink outlines, chalky textured painterly background, muted earthy colours with vivid glowing accents")
MAX_WORDS = 90          # training captions: median 51, max 88 words (LT-03)
# light and colour words that wash the look out (the bus prompt's "flat grey daylight" on an "empty white" plain)
DULL = re.compile(r"\b(flat|overcast|dull|grey|gray|pale|washed[- ]out)(\s+(grey|gray|white|pale))?\s+(day)?light\b|"
                  r"\bempty white\b|\bplain (white|grey|gray) (snow|plain|sky|field)\b", re.I)


def with_tail(prompt: str) -> str:
    """The training caption's shape: trigger first, the scene, then the tail once."""
    p = prompt.strip().rstrip(".")
    if not p.lower().startswith(TRIGGER):
        p = f"{TRIGGER}, {p}"
    return p if STYLE_TAIL in p else f"{p}, {STYLE_TAIL}"


def check(prompt: str) -> list[dict]:
    out = []
    if not prompt.lower().startswith(TRIGGER):
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"does not start with '{TRIGGER}'"})
    if STYLE_TAIL not in prompt:
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": "the training caption's style tail is missing"})
    n = len(prompt.split())
    if n > MAX_WORDS:
        out.append({"rule": "LT-65", "severity": "FAIL", "detail": f"{n} words; the LoRA was trained on {MAX_WORDS} at most"})
    m = DULL.search(prompt)
    if m:
        out.append({"rule": "LT-65", "severity": "REVIEW", "detail": f"'{m.group(0)}' washes the colours out"})
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
