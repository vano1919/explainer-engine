"""The stone-age pilot's second Qwen run (the creator 2026-11-07): one jobs file for ``training/pods/p15/qwen_jobs.py``.

* flat3 wide masters at style LoRA 0.7 and 1.0 (14:42 UTC "every frame once also at strength 1"; 15:05 UTC: only the rich build, flat3);
* test A (15:04 UTC, KP-57): the same place from two more Blender angles, Image 1 = the new angle's still, Image 2 = the painted master;
* test B (15:04 UTC, Qwen first): each place drawn by Qwen alone (no Blender), then the same place from three more sides as edits of
  that first view, and one turnaround of each person, as reusable assets that Blender will assemble afterwards;
* test C (15:08-15:29 UTC): the flat3 wide still with a code on every named thing (A people, B animals, C objects); an edit that
  removes one person or animal and one object, asked in letter codes, magenta codes and plain words, at style LoRA 1.0.

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
CODES = {"cave": {"ura": "A1", "marcus": "A2", "hunter_a": "A3", "hunter_b": "A4", "hunter_c": "A5", "hearth_flame": "C1", "paint_panel": "C2",
                  "west_ledge": "C3", "ochre_bowl": "C4"},
         "ice": {"marcus": "A1", "mammoth_0_body": "B1", "mammoth_1_body": "B2", "mammoth_2_body": "B3", "ice_block_0": "C1", "drift_l": "C2"},
         "camp": {"marcus": "A1", "ura": "A2", "torch_a": "A3", "torch_b": "A4", "hut_0_wall": "C1", "hut_1_wall": "C2", "hut_2_wall": "C3",
                  "hut_3_wall": "C4", "camp_flame": "C5", "log_seat": "C6"}}
# the objects' words for the legend and for the plain-words variant (people and animals come from the layout's tags)
OBJ = {"hearth_flame": "the fire", "paint_panel": "the painted wall", "west_ledge": "the stone ledge with hanging bone talismans",
       "ochre_bowl": "the red ochre bowl", "ice_block_0": "the block of ice on the left", "drift_l": "the ice-blue snowdrift on the left",
       "hut_0_wall": "the hut with the arch of tusks", "hut_1_wall": "the hut with the hide rack", "hut_2_wall": "the chief's big hut",
       "hut_3_wall": "the hut by the bone gate", "camp_flame": "the campfire", "log_seat": "the log"}
# the creator 15:29 UTC: a code only proves itself when an edit follows it; each scene removes one person or animal and one object
REMOVE = {"cave": ("hunter_b", "ochre_bowl"), "ice": ("mammoth_1_body", "drift_l"), "camp": ("torch_b", "hut_2_wall")}
MAX_WORDS = 150   # a ceiling for the test prompts: the code legend and the KP-57 master prefix add words; pilot_stills holds the plain 90


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


def _words_of(scene: str, name: str) -> str:
    tags = S.layout(scene, "flat3")["tags"]
    return OBJ.get(name) or re.sub(r" (on the left|in the middle|on the right)$", "", tags[name])


def code_prompt(scene: str, magenta: bool = False, plain: bool = False) -> str:
    """Test C (15:29 UTC): the same removal asked in codes (letters or magenta) or in plain words; nothing else changes."""
    codes, gone = CODES[scene], REMOVE[scene]
    if plain:
        rule = "Image 1 is the scene: keep every place, size and pose of everything except what is removed."
        what = " and ".join(_words_of(scene, n) for n in gone)
        return f"xworld style, {rule} Remove {what} completely; nothing is left in their place but the floor or the snow. Everything else stays exactly as in Image 1."
    legend = ", ".join(f"{c} is {_words_of(scene, n)}" for n, c in codes.items())
    mark = "a magenta" if magenta else "a letter"
    tail = "remove every magenta code" if magenta else "paint no codes or letters"
    what = " and ".join(codes[n] for n in gone)
    return (f"xworld style, Image 1 is the scene with {mark} code on each thing: keep every place, size and pose of everything except what "
            f"is removed, and {tail}. {legend}. Remove {what} completely; nothing is left in their place but the floor or the snow. "
            "Everything else stays exactly as in Image 1.")


def label_still(scene: str, src: Path, dst: Path, magenta: bool = False, angle: str = "wide") -> dict:
    """Test C: the code of every named thing drawn on the flat3 wide still at its projected place (white box, black letters; or, with
    ``magenta``, bold oblique mono magenta letters with a dark outline and no box)."""
    from PIL import Image, ImageDraw, ImageFont
    blocks, cast, _, cam = getattr(S, "_" + scene)("flat3")
    cam = cam if angle == "wide" else S.ANGLES[scene][angle]
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
        if not (0.03 < sx < 0.97 and 0.05 < sy < 0.97):
            continue   # out of frame from this angle: no code, and chain_prompts() refuses a move that names it
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
    for sc in S.SCENES:   # the creator 15:08 / 15:10 / 15:29 UTC: the removal in codes (letters, magenta) and in plain words, LoRA 1.0
        g10.append({"name": f"{sc}_codes_w10", "prompt": code_prompt(sc), "refs": [f"in:sa_{sc}_flat3_codes.png"]})
        g10.append({"name": f"{sc}_magenta_w10", "prompt": code_prompt(sc, magenta=True), "refs": [f"in:sa_{sc}_flat3_magenta.png"],
                    "negative": MAGENTA_NEGATIVE})   # only the magenta codes are forbidden, other text is allowed
        g10.append({"name": f"{sc}_plainedit_w10", "prompt": code_prompt(sc, plain=True), "refs": [f"in:sa_{sc}_flat3.png"]})
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


# the creator 15:29 / 15:30 / 15:31 UTC (test D): the heroes MOVE and the view CHANGES, asked by code; the codes stay in the picture along
# the whole edit chain (so a later edit keeps the context) and a last pass strips them. Variant 1 = codes kept in pixels, variant 2 = the
# same moves in plain words on a clean still. Image 2 is the painted master of the place (KP-57).
MOVES = {"cave": ("A2 walks over and stands beside C1.", "A3 sits down on C3."),
         "ice": ("A1 runs over and stands beside B2.", "B1 turns its back and walks away to the left; C2 is gone."),
         "camp": ("A1 sits down on C6.", "A2 walks over and stands beside C3.")}
CHAIN_ANGLE = "side"
KEEP_NEGATIVE = "watermark, signature, photo, 3d render"   # the chain steps must NOT forbid the magenta codes they keep
_MASTER = "Image 2 is the painted master of the same place: copy its exact rock style, colours, lighting and outfits."


def _visible(scene: str) -> dict:
    """The codes that are in frame from CHAIN_ANGLE (the same test label_still uses)."""
    blocks, cast, _, _ = getattr(S, "_" + scene)("flat3")
    cam, blocks = S.ANGLES[scene][CHAIN_ANGLE], blocks + S.proxies(cast)
    out = {}
    for n, c in CODES[scene].items():
        sx, sy, _ = S.project(cam, S._subject_point(blocks, cast, n))
        if 0.03 < sx < 0.97 and 0.05 < sy < 0.97:
            out[c] = n
    return out


def _plain_move(scene: str, text: str) -> str:
    """The same move in plain words: each code replaced by its description (A2 -> the young courier ...)."""
    import re
    by = {c: n for n, c in CODES[scene].items()}
    return re.sub(r"\b([ABC]\d)\b", lambda m: _words_of(scene, by[m.group(1)]), text)


def chain_prompts(scene: str) -> dict:
    vis, (m1, m2) = _visible(scene), MOVES[scene]
    for c in {t for m in (m1, m2) for t in __import__("re").findall(r"\b[ABC]\d\b", m)}:
        if c not in vis:
            raise ValueError(f"{scene}: move names {c}, which is out of frame from the {CHAIN_ANGLE} view")
    legend = ", ".join(f"{c} is {_words_of(scene, n)}" for c, n in vis.items())
    keep = "Keep every magenta code on its thing, wherever it moves, and keep every other place, size and pose."
    return {"c1": f"xworld style, Image 1 is the scene from a new view with a magenta code on each thing. {_MASTER} {legend}. {m1} {keep}",
            "c2": f"xworld style, Image 1 is the scene with a magenta code on each thing. {_MASTER} {m2} {keep}",
            "c3": "xworld style, Image 1 is the scene with magenta codes. Remove every magenta code; everything else stays exactly as it is.",
            "p1": f"xworld style, Image 1 is the scene from a new view. {_MASTER} {_plain_move(scene, m1)} Keep every other place, size and pose.",
            "p2": f"xworld style, Image 1 is the scene. {_MASTER} {_plain_move(scene, m2)} Keep every other place, size and pose."}


def chain_jobs(inputs: dict) -> dict:
    g = []
    for sc in S.SCENES:
        pr, m = chain_prompts(sc), f"in:{sc}_wide_w10.png"
        g += [{"name": f"{sc}_d1_codes", "prompt": pr["c1"], "refs": [f"in:sa_{sc}_flat3_{CHAIN_ANGLE}_magenta.png", m], "negative": KEEP_NEGATIVE},
              {"name": f"{sc}_d2_codes", "prompt": pr["c2"], "refs": [f"out:{sc}_d1_codes", m], "negative": KEEP_NEGATIVE},
              {"name": f"{sc}_d3_strip", "prompt": pr["c3"], "refs": [f"out:{sc}_d2_codes"], "negative": MAGENTA_NEGATIVE},
              {"name": f"{sc}_d1_plain", "prompt": pr["p1"], "refs": [f"in:sa_{sc}_flat3_{CHAIN_ANGLE}.png", m]},
              {"name": f"{sc}_d2_plain", "prompt": pr["p2"], "refs": [f"out:{sc}_d1_plain", m]}]
    for j in g:
        j["size"] = [1280, 720]
        if _words(j["prompt"]) > MAX_WORDS:
            raise ValueError(f"{j['name']}: {_words(j['prompt'])} words, over {MAX_WORDS}")
    return {"run": "sa_v4", "out": OUT_HF.replace("out_v3", "out_v4"), "inputs": inputs, "groups": [{"lora_weight": 1.0, "jobs": g}]}


def chain_build(stills: Path, masters: Path, out: Path) -> dict:
    """Free: the magenta-coded angle stills + the clean ones + the painted masters of run sa_v3, pinned, and the jobs file."""
    out.mkdir(parents=True, exist_ok=True)
    names = []
    for sc in S.SCENES:
        src = stills / f"sa_{sc}_flat3_{CHAIN_ANGLE}.png"
        (out / src.name).write_bytes(src.read_bytes())
        label_still(sc, out / src.name, out / f"sa_{sc}_flat3_{CHAIN_ANGLE}_magenta.png", magenta=True, angle=CHAIN_ANGLE)
        (out / f"{sc}_wide_w10.png").write_bytes((masters / f"{sc}_wide_w10.png").read_bytes())
        names += [src.name, f"sa_{sc}_flat3_{CHAIN_ANGLE}_magenta.png", f"{sc}_wide_w10.png"]
    doc = chain_jobs({n: hashlib.sha256((out / n).read_bytes()).hexdigest() for n in names})
    (out / "sa_v4_jobs.json").write_text(json.dumps(doc, indent=1) + "\n")
    return doc


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="stoneage_qwen_jobs")
    ap.add_argument("cmd", choices=["build", "assets", "chain"]); ap.add_argument("--stills", type=Path); ap.add_argument("--masters", type=Path); ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "assets":
        a.out.mkdir(parents=True, exist_ok=True)
        doc = asset_jobs()
        (a.out / "sa_v3b_jobs.json").write_text(json.dumps(doc, indent=1) + "\n")
    elif a.cmd == "chain":
        doc = chain_build(a.stills, a.masters, a.out)
    else:
        doc = build(a.stills, a.out)
    print(sum(len(g["jobs"]) for g in doc["groups"]), "jobs")
    return 0


if __name__ == "__main__":
    sys.exit(main())
