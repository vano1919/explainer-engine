"""The xworld_v2 round test (D-80; ვანო 2026-10-26 13:26 Tbilisi): after every training round, three scenes of five shots in
three worlds (stories/v2: tent = inside, tundra = outside, rome = a city street) are drawn with the round's checkpoint (or
the base model in round 0), in three prompt forms, so we see whether learning the style damages the scene logic and which
description gives each shot best:
  P1  the form that won the 10-26 held-out test (LT-75 "D"): previous drawn shot + full description + change + keep line
  P2  P1 + where the camera stands, what is left / right / behind, the light, the shot size (the shot's "layout")
  P3  every shot from text alone: full description + layout, no picture (answers "D copies a drawn master")
Shot 0 of a scene is drawn once from text (description + layout) and is the master of P1 and P2. People are described the
way people picture their era (ვანო 13:26) plus an LT-79 face; every scene passes `face_problems`.

    python xworld_v2_scenes.py <scene dir> <out dir> <lora .safetensors | base> [weight]
writes <out>/<scene>_<form>_<shot>.png, jobs.json and scenes.log; drawn pictures are skipped on a rerun.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v1_story import face_problems
    from .xworld_v1_test import KEEP, MASTER, TRIGGER
else:
    from xworld_v1_story import face_problems
    from xworld_v1_test import KEEP, MASTER, TRIGGER

FORMS = ("P1", "P2", "P3")
WEIGHT = 1.0  # ვანო 2026-10-26 12:13 Tbilisi: weight 1.0 once the system differs from the show (the v2 world)


def prompt(form, shot):
    """The prompt of one shot in one form (shot 0 is always drawn from text)."""
    d, lay, ch = shot["desc"], shot["layout"], shot.get("change")
    if not ch or form == "P3":
        return f"{TRIGGER}, {d} {lay}"
    if form == "P1":
        return f"{TRIGGER}, {MASTER} {d} {ch} {KEEP}"
    if form == "P2":
        return f"{TRIGGER}, {MASTER} {d} {lay} {ch} {KEEP}"
    raise ValueError(form)


def jobs(scenes):
    """[{name, scene, form, shot, prompt, ref}] in drawing order; ref = the name of the drawn previous shot, or None."""
    out = []
    for sc in scenes:
        bad = face_problems(sc)
        if bad:
            raise ValueError(f"{sc['name']}: " + "; ".join(bad))
        first = sc["shots"][0]
        out.append({"name": f"{sc['name']}_s0", "scene": sc["name"], "form": "all", "shot": first["id"],
                    "prompt": prompt("P1", first), "ref": None})
        for form in FORMS:
            prev = f"{sc['name']}_s0"
            for s in sc["shots"][1:]:
                name = f"{sc['name']}_{form}_{s['id']}"
                out.append({"name": name, "scene": sc["name"], "form": form, "shot": s["id"], "prompt": prompt(form, s),
                            "ref": None if form == "P3" else prev})
                prev = name
    return out


def load(scene_dir):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(scene_dir).glob("*.json"))]


def main(argv):
    from PIL import Image
    if __package__:
        from .xworld_v1_test import Loras, draw, load_pipeline, logger
    else:
        from xworld_v1_test import Loras, draw, load_pipeline, logger
    scene_dir, outd, lora = argv[:3]
    weight = float(argv[3]) if len(argv) > 3 else WEIGHT
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs(load(scene_dir))
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = logger(outd, "scenes.log")
    pipe, tr = load_pipeline()
    loras = Loras(pipe, tr, {} if lora == "base" else {"R": lora}, say)
    p = loras.use(None if lora == "base" else "R", weight)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{j['ref']}.png").convert("RGB")] if j["ref"] else []
        t = time.time()
        draw(p, j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
