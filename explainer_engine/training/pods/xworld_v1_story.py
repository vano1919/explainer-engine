"""Draw a short story with xworld_v1 from frame 0 (D-80; ვანო 2026-10-26 10:32 Tbilisi); run by xworld_v1_story.sh (OR-21).

A story file (stories/<name>.json) lists shots: a shot with "master": null is drawn from its description alone (frame 0 of a
place); every other shot uses the prompt form that won the held-out test (LT-75: D = master + full description + change
line + "Keep everything else the same.") with its master's DRAWN picture as the only reference. A run picks the LoRA (or
null = the base model) and the shots; "text_master" lists masters that the run also draws from text alone, as a second
branch (`<run>_t_<shot>`) for every shot built on them. Same sampler as the test (1280x720, 30 steps, true_cfg 4, seed 11).

    python xworld_v1_story.py <story.json> <out dir> <lora A>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v1_test import TRIGGER, prompt
else:
    from xworld_v1_test import TRIGGER, prompt


def jobs(story):
    """[{name, run, shot, lora, prompt, ref}] in run order; ref = the name of the drawn master, or None."""
    shots = {s["id"]: s for s in story["shots"]}
    out = []
    for run in story["runs"]:
        ids = [s["id"] for s in story["shots"]] if run["shots"] == "all" else run["shots"]
        missing = [m for i in ids if (m := shots[i]["master"]) and m not in ids]
        if missing:
            raise ValueError(f"run {run['name']}: masters not drawn in the run: {missing}")
        branches = [("", None)] + [("t_", m) for m in run.get("text_master", [])]
        for tag, alt in branches:
            for i in ids:
                s = shots[i]
                if alt and i != alt and s["master"] != alt:
                    continue
                name = f"{run['name']}_{tag}{i}"
                if s["master"] is None or i == alt:
                    text, ref = f"{TRIGGER}, {s['desc']}", None
                else:
                    text = prompt("D", s["desc"], s["change"])
                    ref = f"{run['name']}_{tag if s['master'] == alt else ''}{s['master']}"
                out.append({"name": name, "run": run["name"], "shot": i, "lora": run["lora"], "prompt": text, "ref": ref})
    return out


def main(argv):
    from PIL import Image
    if __package__:
        from .xworld_v1_test import Loras, draw, load_pipeline, logger
    else:
        from xworld_v1_test import Loras, draw, load_pipeline, logger
    story_path, outd, lora_a = argv[:3]
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs(json.loads(Path(story_path).read_text(encoding="utf-8")))
    (outd / "jobs.json").write_text(json.dumps(todo, indent=1, ensure_ascii=False), encoding="utf-8")
    say = logger(outd, "story.log")
    pipe, tr = load_pipeline()
    loras = Loras(pipe, tr, {"A": lora_a}, say)
    for j in todo:
        if (outd / f"{j['name']}.png").exists():
            continue
        refs = [Image.open(outd / f"{j['ref']}.png").convert("RGB")] if j["ref"] else []
        t = time.time()
        draw(loras.use(j["lora"]), j["prompt"], refs).convert("RGB").save(outd / f"{j['name']}.png")
        say("made", j["name"], round(time.time() - t), "s")


if __name__ == "__main__":
    main(sys.argv[1:])
