"""The pod side and the container side of one round of the strategy loop (xworld_v2_loop.py holds the free logic and the plan's rules).

    python xworld_v2_loop_run.py inputs <round.json> <scene dir> <more dir> <sets dir> <p2s dir> <out dir>        (free, the container)
    python xworld_v2_loop_run.py draw   <round.json> <scene dir> <more dir> <inputs dir> <p2s dir> <out dir> <lora> (a pod, after OR-23)

``inputs`` renders everything the control rows need from the set files and the masters, so the pod does no geometry:
  <scene>_<shot>_depth.png      the shot's depth, 1280x720 (S3cA and M5)
  <scene>_m2_control.png        the 2x2 depth canvas of the shots s1..s4 (M2), 2560x1408
  <scene>_m4_control.png / _m4_image.png / _m4_mask.png   M4: depth of s0,s1,s2,s3; the master in panel 1; white = regenerate over panels 2-4
  M5_<scene>_<shot>_{warp,holes,depth}.png   the master warped into the small-move shot's camera and the holes to in-paint
``draw`` writes <out>/<row>/<scene>_<seed>_<shot>.png for every picture of the round (grids also as <scene>_<seed>_grid.png) and logs
the seconds per picture. The masters and sheets are the P2S pictures <scene>_11_s0.png and <scene>_sheet_<role>.png: ONE master per
scene for every seed (the seed changes the drawing, not the established place). Control phase first (one load), then the plain phase.
Deviations from the plan, reported: S2E draws the test shots s1..s4 with the MASTER as Image 1 (test A's s5..s8 come in round 2); M4's
canvas has the master in panel 1 and three new panels (s1, s2, s3), so M4 does not cover s4.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np

if __package__:
    from . import xworld_v2_loop as L
    from . import xworld_v2_s2x as X
    from . import xworld_v2_s3 as S3
    from . import xworld_v2_s3c as C
    from .xworld_v2_p2s import framed, p2s_prompt, prompt as p2s_plain
    from .xworld_v2_scenes import frame_desc, frame_extras, load
    from .xworld_v1_test import TRIGGER
else:
    import xworld_v2_loop as L
    import xworld_v2_s2x as X
    import xworld_v2_s3 as S3
    import xworld_v2_s3c as C
    from xworld_v2_p2s import framed, p2s_prompt, prompt as p2s_plain
    from xworld_v2_scenes import frame_desc, frame_extras, load
    from xworld_v1_test import TRIGGER

GRID_NOTE = ("The top-left panel is the established wide shot of this place; the other three panels are later shots of the same place "
             "and the same people, each from the camera its depth shows.")
CONTROL_ROWS = ("S3cA", "M2", "M4", "M5")
PLAIN_ROWS = ("S1", "S2T", "S2E", "S3cAB")


def shot_of(sc, sid):
    return next(s for s in sc["shots"] if s["id"] == sid)


def grid_prompt_for(sc, shots, note=""):
    """The S2 grid prompt over the given four shots (the words round the panels are the S2 ones, so rows differ only in what the plan says)."""
    return (f"{TRIGGER}, a storyboard of 4 panels in a 2x2 grid separated by thin white borders, the same place, the same people with "
            f"the same faces and clothes in every panel, four different camera shots. The place: {sc['place']} {note + ' ' if note else ''}"
            f"{X.cast_text(sc)} {X.panels_text(sc, shots)}")


def edit_prompt_for(sc, shots):
    n = len(sc["cast"])
    return (f"{TRIGGER}, Image 1 is this scene: the same place and the same {n} people with the same faces and clothes. Draw a four-panel "
            f"storyboard in a 2x2 grid separated by thin white borders, continuing it. The place: {sc['place']} {X.cast_text(sc)} "
            f"{X.panels_text(sc, shots)}")


def prompts(sc, row, sid=None):
    """The text of one picture of a row (no model): per-shot rows take the shot id, grid rows the whole grid."""
    test = [shot_of(sc, s) for s in L.SHOTS]
    if row == "S2T":
        return grid_prompt_for(sc, test)
    if row == "S2E":
        return edit_prompt_for(sc, test)
    if row == "M2":
        return grid_prompt_for(sc, test)
    if row == "M4":
        return grid_prompt_for(sc, [shot_of(sc, s) for s in ("s0", "s1", "s2", "s3")], GRID_NOTE)
    if row in ("S3cA", "M5"):
        return C.pass_a_prompt(sc, shot_of(sc, sid))
    if row == "S3cAB":
        return C.pass_b_prompt(sc, shot_of(sc, sid))[0]
    if row == "S1":
        s = shot_of(sc, sid)
        roles = [r for r in s.get("faces", []) if r in sc["cast"]][:2]
        return p2s_prompt(framed(sc, s), sc["cast"], roles) if roles else p2s_plain("P2F", framed(sc, s))
    raise KeyError(row)


# --- inputs (free, the container) ------------------------------------------------------------------------------------------------

def build_inputs(cfg, scenes, sets_dir, p2s_dir, outd, estimator=None):
    """Writes the control inputs listed in the module docstring; returns {file name: what}. ``estimator`` = Depth-Anything (M5 only)."""
    from PIL import Image
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    made = {}
    for sc in scenes:
        n = sc["name"]
        s = S3.load_set(Path(sets_dir) / f"{n}.set.json")
        S3.check_set(s)
        master = Image.open(Path(p2s_dir) / f"{n}_11_s0.png").convert("RGB")

        def depth(sid, w, h):
            cam = S3.camera(s, s["shots"][sid])
            ident, t, _ = S3.render(s, cam, w, h)
            return S3.depth_image(t), t, cam

        for sid in L.SHOTS:
            d, t, _ = depth(sid, 1280, 720)
            d.save(outd / f"{n}_{sid}_depth.png"); made[f"{n}_{sid}_depth.png"] = "S3cA"
        L.control_canvas([depth(sid, *L.PANEL)[0] for sid in L.SHOTS]).save(outd / f"{n}_m2_control.png")
        L.control_canvas([depth(sid, *L.PANEL)[0] for sid in ("s0", "s1", "s2", "s3")]).save(outd / f"{n}_m4_control.png")
        img, mask = L.inpaint_canvas(master)
        img.save(outd / f"{n}_m4_image.png"); mask.save(outd / f"{n}_m4_mask.png")
        made.update({f"{n}_m2_control.png": "M2", f"{n}_m4_control.png": "M4", f"{n}_m4_image.png": "M4", f"{n}_m4_mask.png": "M4"})
        if "M5" in cfg["rows"]:
            est = estimator or S3.depth_estimator()
            cam0 = S3.camera(s, s["shots"]["s0"])
            m = np.asarray(master)
            inv = est(master)
            _, t0, _ = S3.render(s, cam0, m.shape[1], m.shape[0])
            for sid in L.SMALL_MOVES[n]:
                cam1 = S3.camera(s, s["shots"][sid])
                warp, holes = L.reproject(m, inv, cam0, cam1, t0)
                Image.fromarray(warp).save(outd / f"M5_{n}_{sid}_warp.png")
                Image.fromarray((holes * 255).astype(np.uint8)).save(outd / f"M5_{n}_{sid}_holes.png")
                depth(sid, 1280, 720)[0].save(outd / f"M5_{n}_{sid}_depth.png")
                made.update({f"M5_{n}_{sid}_{k}.png": "M5" for k in ("warp", "holes", "depth")})
    (outd / "inputs.json").write_text(json.dumps(made, indent=1), encoding="utf-8")
    return made


# --- the pod ---------------------------------------------------------------------------------------------------------------------

def cut_grid(grid, shot_ids, outd, row, scene, seed):
    """Saves the grid and its four panels as the row's per-shot pictures (panel k = shot_ids[k]); a shot id None skips that panel."""
    from PIL import Image
    grid.save(Path(outd) / row / f"{scene}_{seed}_grid.png")
    for sid, panel in zip(shot_ids, X.cut(grid.convert("RGB"))):
        if sid:
            panel.resize(L.PANEL).save(Path(outd) / row / L.picture_name(row, scene, seed, sid).split("/")[1])


def draw_control(pipe, prompt, control, scale, cfg, seed, w, h, image=None, mask=None):
    import torch
    from videox_fun.utils.utils import get_image_latent
    g = torch.Generator(device="cuda").manual_seed(seed)
    ctrl = get_image_latent(control, sample_size=[h, w])[:, :, 0]
    kw = {} if image is None else {"image": image.resize((w, h)), "mask_image": mask.resize((w, h))}
    with torch.no_grad():
        return pipe(prompt, negative_prompt=" ", height=h, width=w, generator=g, num_inference_steps=30, true_cfg_scale=cfg,
                    control_image=ctrl, control_context_scale=scale, **kw).images[0]


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    cfg_path, scene_dir, more_dir, inp, p2s, outd, lora = argv[:7]
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    bad = L.check_round(cfg)
    if bad:
        raise SystemExit("REFUSED: " + "; ".join(bad))
    outd, inp, p2s = Path(outd), Path(inp), Path(p2s)
    scenes = [s for s in load(scene_dir) if s["name"] in cfg.get("scenes", L.SCENES)]  # round 1: the card shots s0..s4 only
    (outd).mkdir(parents=True, exist_ok=True)
    for r in cfg["rows"]:
        (outd / r).mkdir(exist_ok=True)
    (outd / "changes.json").write_text(json.dumps(cfg.get("changes", []), indent=1), encoding="utf-8")
    say = t.logger(outd, "loop.log")
    jobs = L.jobs(cfg)
    cf, scale = cfg.get("cfg", 2.5), cfg.get("control_scale", 1.0)
    by = {sc["name"]: sc for sc in scenes}

    def todo(rows):
        return [j for j in jobs if j["row"] in rows]

    def exists(j):
        n = f"{j['scene']}_{j['seed']}_" + ("grid" if j["kind"] == "grid" else j["shot"]) + ".png"
        return (outd / j["row"] / n).exists()

    t.SEED, t.CFG = cfg.get("seeds", L.SEEDS)[0], cf
    if todo(CONTROL_ROWS):  # --- control phase: one load of the control pipeline
        pipe, tr = C.load_control_pipeline()
        if not C.step0(pipe, tr, lora, outd, say, t):
            say("STEP0 FAIL: control rows cannot run with the LoRA; stop")
            return
        p = t.Loras(pipe, tr, {"R": lora}, say).use("R", 1.0)
        for j in todo(CONTROL_ROWS):
            if exists(j):
                continue
            sc, n, seed, row = by[j["scene"]], j["scene"], j["seed"], j["row"]
            t0 = time.time()
            if row == "S3cA":
                img = draw_control(p, prompts(sc, row, j["shot"]), Image.open(inp / f"{n}_{j['shot']}_depth.png"), scale, cf, seed, 1280, 720)
                img.convert("RGB").save(outd / row / f"{n}_{seed}_{j['shot']}.png")
            elif row == "M5":
                s_ = j["shot"]
                img = draw_control(p, prompts(sc, row, s_), Image.open(inp / f"M5_{n}_{s_}_depth.png"), scale, cf, seed, 1280, 720,
                                   Image.open(inp / f"M5_{n}_{s_}_warp.png").convert("RGB"), Image.open(inp / f"M5_{n}_{s_}_holes.png").convert("L"))
                img.convert("RGB").save(outd / row / f"{n}_{seed}_{s_}.png")
            elif row == "M2":
                g = draw_control(p, prompts(sc, row), Image.open(inp / f"{n}_m2_control.png"), scale, cf, seed, 2560, 1408)
                cut_grid(g.convert("RGB"), L.SHOTS, outd, row, n, seed)
            elif row == "M4":
                master = Image.open(p2s / f"{n}_11_s0.png").convert("RGB")
                g = draw_control(p, prompts(sc, row), Image.open(inp / f"{n}_m4_control.png"), scale, cf, seed, 2560, 1408,
                                 Image.open(inp / f"{n}_m4_image.png").convert("RGB"), Image.open(inp / f"{n}_m4_mask.png").convert("L"))
                cut_grid(L.paste_back(g.convert("RGB"), master), (None, "s1", "s2", "s3"), outd, row, n, seed)
            say("made", row, n, seed, j.get("shot") or "grid", round(time.time() - t0), "s")
        del pipe, tr, p
        import gc
        gc.collect()
        import torch
        torch.cuda.empty_cache()
    pipe, tr = t.load_pipeline()  # --- plain phase
    p = t.Loras(pipe, tr, {"R": lora}, say).use("R", 1.0)
    t.CFG = cf
    for j in todo(PLAIN_ROWS):
        if exists(j):
            continue
        sc, n, seed, row = by[j["scene"]], j["scene"], j["seed"], j["row"]
        t.SEED = seed
        t0 = time.time()
        master = Image.open(p2s / f"{n}_11_s0.png").convert("RGB")
        if row == "S2T":
            t.W, t.H = X.GRID_W, X.GRID_H
            cut_grid(t.draw(p, prompts(sc, row), []).convert("RGB"), L.SHOTS, outd, row, n, seed)
        elif row == "S2E":
            t.W, t.H = X.GRID_W, X.GRID_H
            cut_grid(t.draw(p, prompts(sc, row), [master.resize(L.PANEL)]).convert("RGB"), L.SHOTS, outd, row, n, seed)
        elif row == "S1":
            pr = prompts(sc, row, j["shot"])
            s = shot_of(sc, j["shot"])
            roles = [r for r in s.get("faces", []) if r in sc["cast"]][:2]
            refs = [master] + [Image.open(p2s / f"{n}_sheet_{r}.png").convert("RGB") for r in roles]
            t.W, t.H = 1280, 720
            t.draw(p, pr, refs).convert("RGB").save(outd / row / f"{n}_{seed}_{j['shot']}.png")
        elif row == "S3cAB":
            a = outd / "S3cA" / f"{n}_{seed}_{j['shot']}.png"
            if not a.exists():
                say("skip", row, n, seed, j["shot"], "(no S3cA picture to repaint)")
                continue
            pr, role = C.pass_b_prompt(sc, shot_of(sc, j["shot"]))
            refs = [Image.open(a).convert("RGB"), master] + ([Image.open(p2s / f"{n}_sheet_{role}.png").convert("RGB")] if role else [])
            t.W, t.H = 1280, 720
            t.draw(p, pr, refs).convert("RGB").save(outd / row / f"{n}_{seed}_{j['shot']}.png")
        say("made", row, n, seed, j.get("shot") or "grid", round(time.time() - t0), "s")
    say("LOOP ROUND DONE")


def inputs_main(argv):
    cfg_path, scene_dir, more_dir, sets_dir, p2s, outd = argv[:6]
    cfg = json.loads(Path(cfg_path).read_text(encoding="utf-8"))
    scenes = [s for s in load(scene_dir) if s["name"] in cfg.get("scenes", L.SCENES)]  # round 1: the card shots s0..s4 only
    print(len(build_inputs(cfg, scenes, sets_dir, p2s, outd)), "input files")


if __name__ == "__main__":
    if sys.argv[1:2] == ["inputs"]:
        inputs_main(sys.argv[2:])
    elif sys.argv[1:2] == ["draw"]:
        main(sys.argv[2:])
    else:
        raise SystemExit(__doc__)
