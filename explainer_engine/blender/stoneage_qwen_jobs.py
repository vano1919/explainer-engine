"""The stone-age pilot's second Qwen run (the creator 2026-11-07): one jobs file for ``training/pods/p15/qwen_jobs.py``.

* flat3 wide masters at style LoRA 0.7 and 1.0 (14:42 UTC "every frame once also at strength 1"; 15:05 UTC: only the rich build, flat3);
* test A (15:04 UTC, KP-57): the same place from two more Blender angles, Image 1 = the new angle's still, Image 2 = the painted master;
* test B (15:04 UTC, Qwen first): each place drawn by Qwen alone (no Blender), then the same place from three more sides as edits of
  that first view, and one turnaround of each person, as reusable assets that Blender will assemble afterwards;
* test C (15:08 UTC): the flat3 wide still with a code on every named thing (A people, B animals, C landmarks) and the prompt in codes,
  at style LoRA 1.0 (15:08 UTC: so Qwen does not paint the letters).

    python -m explainer_engine.blender.stoneage_qwen_jobs build --stills DIR --out DIR   # labelled stills + sa_v3_jobs.json (free)
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.blender import stoneage_test_layouts as S

OUT_HF = "route_test_2026-11/sa_test/out_v3"
VIEWS = {"left": "its left side", "right": "its right side", "back": "the far end, looking back the other way"}
ENV = {"cave": "a dark ice-age cave with no people: a fire in a ring of stones, a back wall painted with gold towers and red "
               "handprints, a stone ledge with hanging bone talismans on the left wall, a tall rock fissure on the right wall, "
               "stalactites and dark rock teeth, a red ochre bowl",
       "ice": "a wide snow plain at dusk in the ice age with no people and no animals: low snow hills, ice-blue snowdrifts in "
              "front, square blocks of ice, a jagged ice ridge far away",
       "camp": "an ice-age camp in a night snowstorm with no people: four round huts with pointed roofs, the left one with an arch "
               "of mammoth tusks, one with a drying hide rack, the largest the chief's hut, the right one beside a gate of mammoth "
               "bones; a campfire in a ring of stones and a log seat in front"}
PEOPLE = {"marcus": S.MARCUS, "ura": S.URA, "hunter": "the hunter in grey fur with a torch"}
CODES = {"cave": {"ura": "A1", "marcus": "A2", "hunter_a": "A3", "hunter_b": "A4", "hunter_c": "A5", "hearth_flame": "C1", "paint_panel": "C2"},
         "ice": {"marcus": "A1", "mammoth_0_body": "B1", "mammoth_1_body": "B2", "mammoth_2_body": "B3"},
         "camp": {"marcus": "A1", "ura": "A2", "torch_a": "A3", "torch_b": "A4", "log_seat": "C1", "camp_flame": "C2", "hut_0_wall": "C3"}}
MAX_WORDS = 130   # a ceiling for the test prompts: the code legend and the KP-57 master prefix add words; pilot_stills holds the plain 90


def _words(p: str) -> int:
    return len(p.split())


def env_prompt(scene: str, view: str | None = None) -> str:
    light = S.LIGHT[scene]
    if view is None:
        return f"xworld style, {ENV[scene]}, lit by {light}."
    return (f"xworld style, Image 1 is this place. Show the same place seen from {VIEWS[view]}: the same landmarks, colours and light. "
            f"{ENV[scene][0].upper() + ENV[scene][1:]}, lit by {light}.")


def sheet_prompt(who: str) -> str:
    return (f"xworld style, a character turnaround of {PEOPLE[who]}: the same man four times side by side, full body, standing "
            "relaxed, seen from the front, three-quarter, side and back, on a plain light grey background, nothing else.")


MAGENTA_FONT = "FreeMonoBoldOblique.ttf"   # the creator 15:10 UTC: codes in one unique font and colour, and only those are forbidden
MAGENTA_NEGATIVE = "magenta code labels, magenta letters, magenta stencil codes, watermark, signature, photo, 3d render"


def code_prompt(scene: str, magenta: bool = False) -> str:
    """Test C: the card's start with each named thing replaced by its code; the codes and what they are listed once."""
    codes, tags = CODES[scene], S.layout(scene, "flat3")["tags"]
    plain = {n: re.sub(r" (on the left|in the middle|on the right)$", "", tags[n]) for n in codes}
    legend = ", ".join(f"{c} is {plain[n]}" for n, c in codes.items())
    start = re.sub(r"\{(\w+)\}", lambda m: codes[m.group(1)], S.CARDS[scene]["start"])
    rule = ("Image 1 is the scene with a magenta code on each thing: keep every place, size and pose, and remove every magenta code."
            if magenta else "Image 1 is the scene with a letter code on each thing: keep every place, size and pose, and paint no codes or letters.")
    return (f"xworld style, {rule} {legend}. {start[0].upper() + start[1:]}, in {S.PLACE[scene]}, lit by {S.LIGHT[scene]}.")


def label_still(scene: str, src: Path, dst: Path, magenta: bool = False) -> dict:
    """Test C: the code of every named thing drawn on the flat3 wide still at its projected place (white box, black letters; or, with
    ``magenta``, bold oblique mono magenta letters with a dark outline and no box)."""
    from PIL import Image, ImageDraw, ImageFont
    blocks, cast, _, cam = getattr(S, "_" + scene)("flat3")
    blocks = blocks + S.proxies(cast)
    im = Image.open(src).convert("RGB")
    d = ImageDraw.Draw(im)
    try:
        font = ImageFont.truetype(MAGENTA_FONT if magenta else "DejaVuSans-Bold.ttf", int(im.height * (0.06 if magenta else 0.045)))
    except OSError:
        font = ImageFont.load_default()
    where = {}
    for n, code in CODES[scene].items():
        sx, sy, _ = S.project(cam, S._subject_point(blocks, cast, n))
        x, y = int(sx * im.width), int(sy * im.height) - int(im.height * 0.08)
        if magenta:
            d.text((x, y), code, font=font, fill="#FF00FF", anchor="mm", stroke_width=2, stroke_fill="#2A0030")
        else:
            box = d.textbbox((x, y), code, font=font, anchor="mm")
            d.rectangle([box[0] - 6, box[1] - 4, box[2] + 6, box[3] + 4], fill="white", outline="black", width=2)
            d.text((x, y), code, font=font, fill="black", anchor="mm")
        where[code] = [round(sx, 3), round(sy, 3)]
    im.save(dst)
    return where


def jobs(inputs: dict) -> dict:
    g07, g10 = [], []
    for sc in S.SCENES:   # masters first: test A needs them
        p = PS.prompts(S.SHOT[sc], layout=S.layout(sc, "flat3"))["qwen"]
        g07.append({"name": f"{sc}_wide_w07", "prompt": p, "refs": [f"in:sa_{sc}_flat3.png"]})
        g10.append({"name": f"{sc}_wide_w10", "prompt": p, "refs": [f"in:sa_{sc}_flat3.png"]})
    for sc in S.SCENES:
        for a in S.ANGLES[sc]:
            p = PS.prompts(S.shot_id(sc, a), layout=S.layout(sc, "flat3", a), master=True)["qwen"]
            g07.append({"name": f"{sc}_{a}_w07", "prompt": p, "refs": [f"in:sa_{sc}_flat3_{a}.png", f"out:{sc}_wide_w07"]})
    for sc in S.SCENES:   # the creator 15:08 UTC: the code test at style strength 1.0, so the letters are not painted
        g10.append({"name": f"{sc}_codes_w10", "prompt": code_prompt(sc), "refs": [f"in:sa_{sc}_flat3_codes.png"]})
        g10.append({"name": f"{sc}_magenta_w10", "prompt": code_prompt(sc, magenta=True), "refs": [f"in:sa_{sc}_flat3_magenta.png"],
                    "negative": MAGENTA_NEGATIVE})   # 15:10 UTC: only the magenta codes are forbidden, other text is allowed
    for j in g07 + g10:
        j["size"] = [1280, 720]
        if _words(j["prompt"]) > MAX_WORDS:
            raise ValueError(f"{j['name']}: {_words(j['prompt'])} words, over {MAX_WORDS}")
    return {"run": "sa_v3", "out": OUT_HF, "inputs": inputs,
            "groups": [{"lora_weight": 0.7, "jobs": g07}, {"lora_weight": 1.0, "jobs": g10}]}


def asset_jobs() -> dict:
    """Test B alone (the creator 15:12 UTC: the assets need no Blender, so they run first): places and people drawn by Qwen."""
    g = []
    for sc in S.SCENES:
        g.append({"name": f"env_{sc}_front", "prompt": env_prompt(sc), "refs": [], "size": [1280, 720]})
        for v in VIEWS:
            g.append({"name": f"env_{sc}_{v}", "prompt": env_prompt(sc, v), "refs": [f"out:env_{sc}_front"], "size": [1280, 720]})
    for who in PEOPLE:
        g.append({"name": f"char_{who}", "prompt": sheet_prompt(who), "refs": [], "size": [1280, 720]})
    return {"run": "sa_v3b", "out": OUT_HF.replace("out_v3", "out_v3b"), "inputs": {}, "groups": [{"lora_weight": 0.7, "jobs": g}]}


def build(stills: Path, out: Path) -> dict:
    out.mkdir(parents=True, exist_ok=True)
    names = [f"sa_{sc}_flat3.png" for sc in S.SCENES] + [f"sa_{sc}_flat3_{a}.png" for sc in S.SCENES for a in S.ANGLES[sc]]
    for n in names:
        (out / n).write_bytes((stills / n).read_bytes())
    codes = {sc: label_still(sc, out / f"sa_{sc}_flat3.png", out / f"sa_{sc}_flat3_codes.png") for sc in S.SCENES}
    for sc in S.SCENES:
        label_still(sc, out / f"sa_{sc}_flat3.png", out / f"sa_{sc}_flat3_magenta.png", magenta=True)
    names += [f"sa_{sc}_flat3_{k}.png" for sc in S.SCENES for k in ("codes", "magenta")]
    inputs = {n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in names}
    doc = jobs(inputs)
    doc["codes"] = codes
    (out / "sa_v3_jobs.json").write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stoneage_qwen_jobs")
    ap.add_argument("cmd", choices=["build", "assets"]); ap.add_argument("--stills", type=Path); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "assets":
        a.out.mkdir(parents=True, exist_ok=True)
        doc = asset_jobs()
        (a.out / "sa_v3b_jobs.json").write_text(json.dumps(doc, indent=1) + "\n")
    else:
        doc = build(a.stills, a.out)
    print(sum(len(g["jobs"]) for g in doc["groups"]), "jobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
