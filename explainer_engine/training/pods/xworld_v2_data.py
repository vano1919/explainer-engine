"""The new-world part of the xworld_v2 dataset (D-80; ვანო 2026-10-26 13:17 Tbilisi: "99 % is good, train the world"): the
220 BFL pictures of `training/cast` with captions made from the text each was drawn from, without the style words, so the
look binds to the trigger. Ten are held out for the checkpoint choice (HOLD_OUT). Where Claude's look found a woman drawn
as a man (FIXED_MALE) or unclear (FIXED_PERSON) the caption says what is drawn, never what was asked.

    python -m explainer_engine.training.pods.xworld_v2_data <world dir> <out dir>
writes <out>/new/<id>.png + .txt and <out>/manifest.json (train ids, hold-out ids with their captions).
"""
from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

TRIGGER = "xworld style"
RM_TRIGGER = "rm style"  # the training show's sequence pairs keep their own trigger, so its look stays out of ours
HOLD_OUT = ["c007", "c033", "c062", "c085", "p012", "p041", "p065", "p078", "o009", "o024"]
# Claude's look 2026-10-26 (rating page notes): asked for a woman, drawn as a man / unclear
FIXED_MALE = ["c006", "c010", "c014", "c018", "c022", "c030", "c041", "c046", "c050", "c054", "c057", "c058", "c074",
              "c078", "c081", "c089", "c090", "c093", "c097", "c098"]
FIXED_PERSON = ["c029", "c045", "c053", "c086"]
FRAME = {"person": "one person, full body, on a plain off-white background: ",
         "place": "an empty place with no people, wide view: ",
         "object": "one object on a plain off-white background: "}


def as_drawn(cid, desc):
    """The description with the sex of the drawn picture (FIXED_MALE, FIXED_PERSON)."""
    if cid in FIXED_MALE:
        desc = desc.replace(", a woman,", ", a man,")
        desc = re.sub(r"\bShe\b", "He", desc); desc = re.sub(r"\bher\b", "his", desc); desc = re.sub(r"\bHer\b", "His", desc)
    elif cid in FIXED_PERSON:
        desc = desc.replace(", a woman,", ", a person,")
        desc = re.sub(r"\bShe has\b", "The person has", desc); desc = re.sub(r"\b[Hh]er\b", "the", desc)
    return desc


def caption(item_id, kind, desc):
    return f"{TRIGGER}, {FRAME[kind]}{as_drawn(item_id, desc)}"


def build(world, out):
    from explainer_engine.training.cast.rate_page import kept
    from explainer_engine.training.cast.sheet import items
    world, out = Path(world), Path(out)
    (out / "new").mkdir(parents=True, exist_ok=True)
    its, best = items(), kept(world)
    missing = sorted(set(its) - set(best))
    if missing:
        raise ValueError(f"no kept picture for {missing}")
    man = {"train": [], "hold_out": {}}
    for i in sorted(its):
        text = caption(i, its[i]["kind"], its[i]["desc"])
        if i in HOLD_OUT:
            man["hold_out"][i] = text
            continue
        shutil.copy(world / f"{best[i]['name']}.png", out / "new" / f"{i}.png")
        (out / "new" / f"{i}.txt").write_text(text, encoding="utf-8")
        man["train"].append(i)
    (out / "manifest.json").write_text(json.dumps(man, indent=1, ensure_ascii=False), encoding="utf-8")
    print(len(man["train"]), "train,", len(man["hold_out"]), "held out ->", out)
    return man


if __name__ == "__main__":
    build(*sys.argv[1:3])
