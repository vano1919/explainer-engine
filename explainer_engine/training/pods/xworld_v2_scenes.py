"""The xworld_v2 round test (D-80; ვანო 2026-10-26 13:26 Tbilisi): after every training round, three scenes of five shots in
three worlds (stories/v2: tent = inside, tundra = outside, rome = a city street) are drawn with the round's checkpoint (or
the base model in round 0), in three prompt forms, so we see whether learning the style damages the scene logic and which
description gives each shot best:
  P1  the form that won the 10-26 held-out test (LT-75 "D"): previous drawn shot + full description + change + keep line
  P2  P1 + where the camera stands, what is left / right / behind, the light, the shot size (the shot's "layout")
  P3  every shot from text alone: full description + layout, no picture (answers "D copies a drawn master")
  P2F shot 0 as the picture of every shot (a fixed previous frame: no chained errors; review 2026-10-26), asked in the form the
      cut pairs are trained with (xworld_v2_build.cut_caption): master sentence + description + the cut + keep line, no
      layout sentence (ვანო 2026-10-26 12:42; round 0's P2F carried the layout sentence)
  P2R P2F under `rm style` (the cut skill is trained under that trigger: does it show only there?)
Every scene is drawn with each seed of SEEDS (review 2026-10-26: one seed cannot tell a form from luck).
Shot 0 of a scene is drawn once from text (description + layout) and is the master of P1 and P2. People are described the
way people picture their era (ვანო 13:26) plus an LT-79 face; every scene passes `face_problems`.

    python xworld_v2_scenes.py <scene dir> <out dir> <lora .safetensors | base> [weight] [round|one]   (round = ROUND_TESTS only, one = ONE_SCENE_TESTS)
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
    from .xworld_v2_data import RM_TRIGGER
else:
    from xworld_v1_story import face_problems
    from xworld_v1_test import KEEP, MASTER, TRIGGER
    from xworld_v2_data import RM_TRIGGER

FORMS = ("P1", "P2", "P3", "P2F")
# what a training round draws (reduced test, ვანო 2026-10-26): (form, scenes or None = all, seeds)
ROUND_TESTS = (("P3", None, (11,)), ("P2F", None, (11, 23)), ("P2R", ("tent",), (11,)))
# the short test (ვანო 2026-10-26 16:39: the aim is the best way, not round-to-round comparison): one scene (tundra, the decisive one; the Opus thread 16:39)
ONE_SCENE_TESTS = (("P3", ("tundra",), (11,)), ("P2F", ("tundra",), (11, 23)))
MODES = {"round": ROUND_TESTS, "one": ONE_SCENE_TESTS}
FIXED_REF = ("P2F", "P2R")  # forms whose every shot edits shot 0
SEEDS = (11, 23)
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
    if form in FIXED_REF:  # the cut sentence as trained: "Cut to the next shot: <change>" (xworld_v2_build.cut_caption)
        cut = ch[len("Cut to "):] if ch.startswith("Cut to ") else ch
        return f"{RM_TRIGGER if form == 'P2R' else TRIGGER}, {MASTER} {d} Cut to the next shot: {cut} {KEEP}"
    raise ValueError(form)


def jobs(scenes, seeds=SEEDS, tests=None):
    """[{name, scene, seed, form, shot, prompt, ref}] in drawing order; ref = the name of a drawn picture, or None.
    ``tests`` = ROUND_TESTS-like (form, scenes or None, seeds); without it every form is drawn with every seed."""
    out = []
    for sc in scenes:
        bad = face_problems(sc)
        if bad:
            raise ValueError(f"{sc['name']}: " + "; ".join(bad))
        first = sc["shots"][0]
        want = [(f, sd) for f in FORMS for sd in seeds] if tests is None else \
            [(f, sd) for f, only, sds in tests if only is None or sc["name"] in only for sd in sds]
        for seed in dict.fromkeys(sd for _, sd in want):
            s0 = f"{sc['name']}_{seed}_s0"
            out.append({"name": s0, "scene": sc["name"], "seed": seed, "form": "all", "shot": first["id"],
                        "prompt": prompt("P1", first), "ref": None})
            for form in [f for f, sd in want if sd == seed]:
                prev = s0
                for s in sc["shots"][1:]:
                    name = f"{sc['name']}_{seed}_{form}_{s['id']}"
                    ref = None if form == "P3" else s0 if form in FIXED_REF else prev
                    out.append({"name": name, "scene": sc["name"], "seed": seed, "form": form, "shot": s["id"],
                                "prompt": prompt(form, s), "ref": ref})
                    prev = name
    return out


def load(scene_dir):
    return [json.loads(p.read_text(encoding="utf-8")) for p in sorted(Path(scene_dir).glob("*.json"))]


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, outd, lora = argv[:3]
    weight = float(argv[3]) if len(argv) > 3 else WEIGHT
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs(load(scene_dir), tests=MODES.get(argv[4]) if len(argv) > 4 else None)
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = t.logger(outd, "scenes.log")
    pipe, tr = t.load_pipeline()
    loras = t.Loras(pipe, tr, {} if lora == "base" else {"R": lora}, say)
    p = loras.use(None if lora == "base" else "R", weight)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{j['ref']}.png").convert("RGB")] if j["ref"] else []
        t0 = time.time()
        t.SEED = j["seed"]  # draw() reads the module's seed
        t.draw(p, j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t0), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
