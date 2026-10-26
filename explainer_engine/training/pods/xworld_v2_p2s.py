"""The xworld_v2 reference test P2S (D-75; the Opus thread's plan 2026-10-26 16:17 UTC, ვანო's panorama question 16:14):
does a master frame plus one model sheet per person keep the faces and clothes across the shots of a scene, and do a lower
cfg (4.0 -> 2.5) or a lower LoRA weight (1.0 -> 0.7) take the grain and the heavy colour out of the edits?

For each scene (tent, rome) and seed 11, with ONE checkpoint:
  s0     shot 0, drawn once from text (the master)
  sheet  one model sheet per person of the cast, drawn once from text (P3 form)
  cells  refs in (P2F = master only, P2S = master + the sheets of the people in the shot, three images at most)
         x true_cfg in (4.0, 2.5) x LoRA weight in (1.0, 0.7); shots 1..4 of each cell are edits of those references
The P2S prompt names the images by position; the rest is the P2F prompt (the cut as trained). If the pipeline refuses three
images the run falls back to two (master + the first sheet) and says FALLBACK in the log.

    python xworld_v2_p2s.py <scene dir> <out dir> <lora .safetensors> [scenes comma list]
writes <out>/<name>.png, jobs.json, p2s.log; drawn pictures are skipped on a rerun; sheets: xworld_v2_sheet.py p2s.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import SEEDS, load, prompt
    from .xworld_v1_story import face_problems
    from .xworld_v1_test import TRIGGER
else:
    from xworld_v2_scenes import SEEDS, load, prompt
    from xworld_v1_story import face_problems
    from xworld_v1_test import TRIGGER

REFS = ("P2F", "P2S")
CFGS = (4.0, 2.5)
WEIGHTS = (1.0, 0.7)
SCENES = ("tent", "rome")
SEED = SEEDS[0]
MAX_IMAGES = 3  # the arch takes up to three reference images (ai-toolkit GenerateImageConfig ctrl_img_1..3)
SHEET = "character model sheet: front view, three-quarter view and side view of one person, neutral standing pose, plain white background."


def sheet_prompt(c):
    return f"{TRIGGER}, {SHEET} {c['look']} {c['face']}"


def p2s_prompt(shot, cast, roles):
    """The P2F prompt with the images named by position: image 1 = the master frame, then one sheet per person."""
    names = [f"Image {i + 2} is the model sheet of {r}" for i, r in enumerate(roles)]
    lead = "Image 1 is the master frame of the place" + "".join(". " + n for n in names) + \
           ". Keep every person's face and clothes exactly as on their sheet and the place as in image 1."
    body = prompt("P2F", shot)
    return body.replace(f"{TRIGGER}, ", f"{TRIGGER}, {lead} ", 1)


def cell_name(scene, ref, cfg, weight, shot_id):
    return f"{scene}_{SEED}_{ref}_c{cfg}_w{weight}_{shot_id}"


def jobs(scenes, max_images=MAX_IMAGES):
    """[{name, scene, kind, ref_kind, cfg, weight, shot, prompt, refs}] ordered so the LoRA weight changes as seldom as
    possible; refs = names of drawn pictures."""
    out = []
    for sc in scenes:
        bad = face_problems(sc)
        if bad:
            raise ValueError(f"{sc['name']}: " + "; ".join(bad))
        s0 = f"{sc['name']}_{SEED}_s0"
        first = sc["shots"][0]
        out.append({"name": s0, "scene": sc["name"], "kind": "master", "cfg": 4.0, "weight": 1.0, "shot": first["id"],
                    "prompt": prompt("P3", first), "refs": []})
        for role, c in sc["cast"].items():
            out.append({"name": f"{sc['name']}_sheet_{role}", "scene": sc["name"], "kind": "sheet", "cfg": 4.0, "weight": 1.0,
                        "shot": role, "prompt": sheet_prompt(c), "refs": []})
        for ref in REFS:
            for cfg in CFGS:
                for weight in WEIGHTS:
                    for s in sc["shots"][1:]:
                        roles = [r for r in s.get("faces", []) if r in sc["cast"]][:max_images - 1] if ref == "P2S" else []
                        out.append({"name": cell_name(sc["name"], ref, cfg, weight, s["id"]), "scene": sc["name"], "kind": ref,
                                    "cfg": cfg, "weight": weight, "shot": s["id"],
                                    "prompt": p2s_prompt(s, sc["cast"], roles) if roles else prompt("P2F", s),
                                    "refs": [s0] + [f"{sc['name']}_sheet_{r}" for r in roles]})
    head = [j for j in out if j["kind"] in ("master", "sheet")]
    cells = sorted((j for j in out if j["kind"] not in ("master", "sheet")), key=lambda j: -j["weight"])
    return head + cells


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, outd, lora = argv[:3]
    only = argv[3].split(",") if len(argv) > 3 else SCENES
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs([s for s in load(scene_dir) if s["name"] in only])
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = t.logger(outd, "p2s.log")
    pipe, tr = t.load_pipeline()
    loras = t.Loras(pipe, tr, {"R": lora}, say)
    limit = MAX_IMAGES
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{r}.png").convert("RGB") for r in j["refs"]]
        p = loras.use("R", j["weight"])
        t.SEED, t.CFG = SEED, j["cfg"]  # draw() reads the module's seed and cfg
        t0 = time.time()
        try:
            img = t.draw(p, j["prompt"], refs[:limit])
        except Exception as e:  # the pipeline may take fewer images than the arch: say so and go on with two
            if len(refs) <= 2:
                raise
            limit = 2
            say("FALLBACK: three images refused, using two:", str(e)[:160])
            img = t.draw(p, j["prompt"], refs[:limit])
        img.convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t0), "s", f"cfg {j['cfg']} w {j['weight']} refs {len(refs[:limit])}")


if __name__ == "__main__":
    main(sys.argv[1:])
