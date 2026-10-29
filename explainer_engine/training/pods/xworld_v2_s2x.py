"""The xworld_v2 test S2x (Opus plan, relay 2026-10-26 19:20 UTC): does the S2 storyboard idea hold for a scene of EIGHT shots?

One scene is drawn as two 2x2 grids (2560x1408, panels 1280x704, both divisible by 64):
  g1   shots s1..s4 of the scene card (s0, the wide, is shot 0 of grid 1: the card's shots 0..3)
  g2t  shots s5..s8 (the continuation in stories/v2/more/<scene>.json), text only, the same prompt shape as g1
  g2e  the same four panels as an EDIT: Image 1 = grid 1's wide panel (cropped to 1280x704), "Image 1 is this scene: ..."
The cast and place text are identical character for character in the three prompts (from the card). Each panel line names its
shot size and angle and carries the E7 out-of-frame rule (frame_desc), the E9 "behind" sentence and, over a shoulder, the E8
"exactly two people" line (frame_extras). Seeds 11 and 23, scenes tent and rome: 2 x 2 x 3 = 12 grids.

Free measures (``measure``): the four panels found (border search), grain statistics of g2t/g2e against g1 (E5), distinct faces per
panel and the identity of the same person across the two grids (YuNet + SFace of qa/face_points, when their models exist; the
numbers are REVIEW only, cartoon faces are a heuristic), and the landmark questions that are answered by eye on the sheet.

    python xworld_v2_s2x.py <scene dir> <more dir> <out dir> <lora .safetensors> [scenes] [cfg]    (a pod)
    python xworld_v2_s2x.py sheet <out dir>        python xworld_v2_s2x.py measure <out dir>
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from .xworld_v2_s2 import cut
    from .xworld_v1_story import face_problems
    from .xworld_v1_test import TRIGGER
else:
    from xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from xworld_v2_s2 import cut
    from xworld_v1_story import face_problems
    from xworld_v1_test import TRIGGER

SCENES = ("tent", "rome")
GRID_W, GRID_H = 2560, 1408
PANEL_W, PANEL_H = 1280, 704
PANELS = 4
ORDER = ("top-left", "top-right", "bottom-left", "bottom-right")
GRIDS = ("g1", "g2t", "g2e")
LANDMARKS = {
    "tent": ("the camp bed", "the brass lantern", "the entrance flap", "the map table"),
    "rome": ("the bakery counter with loaves", "the stone fountain", "the Colosseum", "the ochre apartment buildings with balconies"),
}


def extra_shots(more_dir, scene):
    """The continuation shots of a scene, each with its ``desc`` built from the card's cast text (so it is word for word the card's)."""
    doc = json.loads((Path(more_dir) / f"{scene['name']}.json").read_text(encoding="utf-8"))
    out = []
    for s in doc["shots"]:
        cast = " ".join(f"{scene['cast'][r]['look']} {scene['cast'][r]['face']}" for r in s.get("faces", []))
        out.append({**s, "desc": " ".join(x for x in (s["pre"], cast, s["post"]) if x)})
    return out


def with_continuation(scene, more_dir):
    """The card with the shots s5..s8 appended (the cast, the place and shots 0..3 are the card's own)."""
    sc = {**scene, "shots": list(scene["shots"][:PANELS]) + extra_shots(more_dir, scene)}
    bad = face_problems(sc)
    if bad:
        raise ValueError(f"{sc['name']}: " + "; ".join(bad))
    return sc


def cast_text(sc):
    return " ".join(f"{role}: {c['look']} {c['face']}" for role, c in sc["cast"].items())


def panels_text(sc, shots):
    return " ".join(f"{ORDER[i]} panel: {frame_desc(s)} {frame_extras(sc, s)}" for i, s in enumerate(shots))


def grid_prompt(sc, k):
    """k = 0: shots 0..3, k = 1: shots 4..7; the same words round the panels, so the two grids differ only in their panels."""
    shots = sc["shots"][k * PANELS:(k + 1) * PANELS]
    return (f"{TRIGGER}, a storyboard of {PANELS} panels in a 2x2 grid separated by thin white borders, the same place, the same "
            f"people with the same faces and clothes in every panel, four different camera shots. The place: {sc['place']} "
            f"{cast_text(sc)} {panels_text(sc, shots)}")


def edit_prompt(sc):
    """G2E: the same panels as grid 2, led by the sentence that points Image 1 at the scene."""
    n = len(sc["cast"])
    shots = sc["shots"][PANELS:2 * PANELS]
    return (f"{TRIGGER}, Image 1 is this scene: the same place and the same {n} people with the same faces and clothes. Draw a "
            f"four-panel storyboard in a 2x2 grid separated by thin white borders, continuing it. The place: {sc['place']} "
            f"{cast_text(sc)} {panels_text(sc, shots)}")


def jobs(scenes, seeds=SEEDS):
    """[{name, scene, seed, grid, prompt, ref}] in run order: per scene and seed g1, g2t, then g2e (its ref is the name of g1)."""
    out = []
    for sc in scenes:
        for seed in seeds:
            base = f"{sc['name']}_{seed}"
            out.append({"name": f"{base}_g1", "scene": sc["name"], "seed": seed, "grid": "g1", "prompt": grid_prompt(sc, 0), "ref": None})
            out.append({"name": f"{base}_g2t", "scene": sc["name"], "seed": seed, "grid": "g2t", "prompt": grid_prompt(sc, 1), "ref": None})
            out.append({"name": f"{base}_g2e", "scene": sc["name"], "seed": seed, "grid": "g2e", "prompt": edit_prompt(sc), "ref": f"{base}_g1"})
    return out


def questions(scene):
    """The landmark questions of one panel set, answered by eye on the sheet (free)."""
    return [f"Is {x} visible in the picture, and where the other panels have it?" for x in LANDMARKS[scene]]


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, more_dir, outd, lora = argv[:4]
    only = argv[4].split(",") if len(argv) > 4 and argv[4] else SCENES
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs([with_continuation(s, more_dir) for s in load(scene_dir) if s["name"] in only])
    say = t.logger(outd, "s2x.log")
    pipe, tr = t.load_pipeline()
    loras = t.Loras(pipe, tr, {"R": lora}, say)
    p = loras.use("R", 1.0)
    if len(argv) > 5:
        t.CFG = float(argv[5])
    for i, j in enumerate(todo):
        grid = outd / f"{j['name']}.png"
        if not grid.exists():
            ref = []
            if j["ref"]:
                g1 = cut(Image.open(outd / f"{j['ref']}.png").convert("RGB"))
                ref = [g1[0].resize((PANEL_W, PANEL_H))]
            t0 = time.time(); t.W, t.H = GRID_W, GRID_H; t.SEED = j["seed"]
            t.draw(p, j["prompt"], ref).convert("RGB").save(grid)
            say("made", j["name"], round(time.time() - t0), "s")
        panels = cut(Image.open(grid).convert("RGB"))
        for k, pn in enumerate(panels):
            pn.resize((PANEL_W, PANEL_H)).save(outd / f"{j['name']}_p{k}.png")
        if i == 0:
            say("GATE first grid cut", [pn.size for pn in panels])


def sheet(outd):
    """<out>/s2x_sheet_<scene>_<seed>.jpg: grid 1's panels above, G2T and G2E below (the eye check of the plan)."""
    from PIL import Image, ImageDraw
    outd = Path(outd)
    made = []
    for scene in SCENES:
        for seed in SEEDS:
            rows = []
            for g in GRIDS:
                fs = [outd / f"{scene}_{seed}_{g}_p{k}.png" for k in range(PANELS)]
                if all(f.exists() for f in fs):
                    rows.append((g, [Image.open(f).convert("RGB").resize((480, 264)) for f in fs]))
            if not rows:
                continue
            img = Image.new("RGB", (480 * PANELS, (264 + 14) * len(rows)), (255, 255, 255)); y = 0
            for g, ims in rows:
                ImageDraw.Draw(img).text((2, y + 1), f"{scene} seed {seed} {g}", fill=(0, 0, 0)); y += 14
                for k, im in enumerate(ims):
                    img.paste(im, (480 * k, y))
                y += 264
            out = outd / f"s2x_sheet_{scene}_{seed}.jpg"
            img.save(out, quality=88); made.append(out)
    return made


def identity_report(emb):
    """emb = {(grid, panel): [feature, ...]} (one unit-length feature per face). The best cosine of each face of a g2 panel to any face of a
    g1 panel (cross) against the same between different g1 panels (within): the same person should score alike across the grids as inside one."""
    import numpy as np

    def best(a, b):
        return [max(float(np.dot(x, y)) for y in b) for x in a if len(b)]

    within = [v for p in range(PANELS) for q in range(PANELS) if p != q for v in best(emb.get(("g1", p), []), emb.get(("g1", q), []))]
    cross = {g: [v for p in range(PANELS) for q in range(PANELS) for v in best(emb.get((g, p), []), emb.get(("g1", q), []))]
             for g in ("g2t", "g2e")}
    mean = lambda xs: round(sum(xs) / len(xs), 3) if xs else None
    return {"within_g1": mean(within), "cross_g2t": mean(cross["g2t"]), "cross_g2e": mean(cross["g2e"]),
            "n": {"within_g1": len(within), "g2t": len(cross["g2t"]), "g2e": len(cross["g2e"])}}


def grain(outd, scene, seed):
    """Grain statistics (training/qa/image_stats) of each grid's panels, as the mean per grid and its ratio to g1 (E5)."""
    import numpy as np
    from explainer_engine.training.qa import image_stats as S  # measure runs in the container, not on the pod
    mean = {}
    for g in GRIDS:
        rows = [S.stats(Path(outd) / f"{scene}_{seed}_{g}_p{k}.png") for k in range(PANELS) if (Path(outd) / f"{scene}_{seed}_{g}_p{k}.png").exists()]
        if rows:
            mean[g] = {k: float(np.mean([r[k] for r in rows])) for k in rows[0]}
    return {"mean": mean, "ratio": {g: S.ratio(mean[g], mean["g1"]) for g in mean if g != "g1" and "g1" in mean}}


def measure(outd):
    """The free numbers of the plan for every drawn grid; written to <out>/s2x_measures.json (REVIEW values, never a verdict)."""
    outd = Path(outd)
    res = {"panels": {}, "grain": {}, "faces": {}, "questions": {s: questions(s) for s in SCENES}}
    for scene in SCENES:
        for seed in SEEDS:
            for g in GRIDS:
                n = len(list(outd.glob(f"{scene}_{seed}_{g}_p?.png")))
                if n:
                    res["panels"][f"{scene}_{seed}_{g}"] = n
            if (outd / f"{scene}_{seed}_g1_p0.png").exists():
                res["grain"][f"{scene}_{seed}"] = grain(outd, scene, seed)
            res["faces"][f"{scene}_{seed}"] = _faces(outd, scene, seed)
    (outd / "s2x_measures.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    return res


def _faces(outd, scene, seed):
    """Faces per panel and the identity report; says so when OpenCV or the YuNet/SFace models are missing."""
    try:
        from explainer_engine.qa import face_points as FP
        from explainer_engine.qa import pixels as PX
        import numpy as np
        rec = FP.recognizer()
        if PX._cv2() is None or not PX.YUNET.is_file() or rec is None:
            return {"skipped": "OpenCV or the YuNet/SFace models are missing (tools/yunet)"}
    except Exception as e:  # the check is optional
        return {"skipped": f"{type(e).__name__}: {e}"}
    emb, count = {}, {}
    for g in GRIDS:
        for k in range(PANELS):
            f = Path(outd) / f"{scene}_{seed}_{g}_p{k}.png"
            if not f.exists():
                continue
            faces = FP.detect(f, PX.YUNET, rec)
            count[f"{g}_p{k}"] = len(faces)
            feats = [np.asarray(x["_emb"], dtype=float).ravel() for x in faces]
            emb[(g, k)] = [v / (np.linalg.norm(v) or 1.0) for v in feats]
    return {"faces_per_panel": count, "identity": identity_report(emb)}


if __name__ == "__main__":
    if sys.argv[1:2] == ["sheet"]:
        print([str(p) for p in sheet(sys.argv[2])])
    elif sys.argv[1:2] == ["measure"]:
        print(json.dumps(measure(sys.argv[2]), indent=1)[:4000])
    else:
        main(sys.argv[1:])
