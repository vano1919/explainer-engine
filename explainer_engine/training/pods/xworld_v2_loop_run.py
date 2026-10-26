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
    from . import xworld_v2_cells as K
    from . import xworld_v2_dirs as DR
    from . import xworld_v2_loop as L
    from . import xworld_v2_s2x as X
    from . import xworld_v2_s3 as S3
    from . import xworld_v2_s3c as C
    from .xworld_v2_p2s import framed, p2s_prompt, prompt as p2s_plain
    from .xworld_v2_scenes import frame_desc, frame_extras, load
    from .xworld_v1_test import TRIGGER
else:
    import xworld_v2_cells as K
    import xworld_v2_dirs as DR
    import xworld_v2_loop as L
    import xworld_v2_s2x as X
    import xworld_v2_s3 as S3
    import xworld_v2_s3c as C
    from xworld_v2_p2s import framed, p2s_prompt, prompt as p2s_plain
    from xworld_v2_scenes import frame_desc, frame_extras, load
    from xworld_v1_test import TRIGGER

GRID_NOTE = ("The top-left panel is the established wide shot of this place; the other three panels are later shots of the same place "
             "and the same people, each from the camera its depth shows.")
CONTROL_ROWS = ("S3cA", "M2", "M4", "M5", "M2E50", "M4E50", "M6")
PLAIN_ROWS = ("S1", "S2T", "S2E", "S3cAB", "S2Tp", "S2Ep", "S2L", "TURN", "PO55", "PO70")
PO_STRENGTH = {"PO55": 0.55, "PO70": 0.70}
def load_scenes(scene_dir):
    """The scene cards of the folder plus the held-out ones (<folder>/heldout: never looked at while the methods are tuned)."""
    d = Path(scene_dir)
    return load(d) + (load(d / "heldout") if (d / "heldout").is_dir() else [])


SETS_DIR = Path(__file__).resolve().parent / ("scenes/sets" if (Path(__file__).resolve().parent / "scenes/sets").exists() else "stories/v2/sets")


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


def panels_behind(sc, shots, labels=None):
    """The panels with the 'behind' line FIRST (round 2, S2Tp/S2Ep: E9, the background is named before the subject)."""
    out = []
    for i, s in enumerate(shots):
        lay = f"Behind and around the subject: {s['layout']}" if s.get("layout") else ""
        ex = frame_extras(sc, s).replace(lay, "").strip() if lay else frame_extras(sc, s)
        out.append(f"{(labels or X.ORDER)[i]} panel: {lay} {frame_desc(s)} {ex}".strip())
    return " ".join(out)


def sets_of(sc):
    return S3.load_set(SETS_DIR / f"{sc['name']}.set.json")


def layout_words(s, sid, w=320, h=180):
    """(camera words, landmarks left to right) of one card shot from the set's 3D ray cast: the picture's own layout as words (S2L)."""
    spec = s["shots"][sid]
    cam = S3.camera(s, spec)
    ident, _, _ = S3.render(s, cam, w, h)
    xs = np.arange(ident.shape[1])[None, :].repeat(ident.shape[0], axis=0)
    items = list(s["objects"]) + list(s["people"])
    seen = []
    for k, it in enumerate(items):
        m = ident == k
        if m.mean() >= S3.MIN_PIXELS:
            seen.append((float(xs[m].mean()), f"{it['id'].replace('_', ' ')} ({S3.color_word(it['color'])})"))
    cam_words = f"{spec.get('size', 'wide')} shot, {spec.get('angle', 'eye')} angle"
    return cam_words, [n for _, n in sorted(seen)]


def panels_layout(sc, shots):
    """The S2L addition: per panel, the camera in words and the landmarks in the order the ray cast sees them from left to right."""
    s = sets_of(sc)
    out = []
    for i, sh in enumerate(shots):
        cam, lm = layout_words(s, sh["id"])
        out.append(f"{X.ORDER[i]} panel camera: {cam}; from left to right in that panel: {', '.join(lm) if lm else 'no landmark'}.")
    return " ".join(out)


def prompts(sc, row, sid=None):
    """The text of one picture of a row (no model): per-shot rows take the shot id, grid rows the whole grid."""
    if K.parse(row):
        return cell_prompt(sc, K.parse(row), sid)
    if row == "TURN":
        return DR.turnaround_prompt(sc, sets_of(sc), TRIGGER)
    if row in PO_STRENGTH:
        return po_plate_prompt(sc, shot_of(sc, sid)) if sid else None
    test = [shot_of(sc, s) for s in L.SHOTS]
    if row == "S2T":
        return grid_prompt_for(sc, test)
    if row == "S2E":
        return edit_prompt_for(sc, test)
    if row == "S2Tp":
        return grid_prompt_for(sc, test).replace(X.panels_text(sc, test), panels_behind(sc, test))
    if row == "S2Ep":
        return edit_prompt_for(sc, test).replace(X.panels_text(sc, test), panels_behind(sc, test))
    if row == "S2L":
        return grid_prompt_for(sc, test) + " " + panels_layout(sc, test)
    row = L.ROWS[row].get("base", row)
    if row == "M6":  # M6 is the M4 prompt (round 2); only the control and the fill change
        row = "M4"
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


# --- factor cells (round 3 and 4, xworld_v2_cells.py) -------------------------------------------------------------------------------

def object_ids(s, sid, w=320, h=180):
    """The set's objects (not people) the camera of this shot sees, left to right: the D=1 prop list."""
    ident, _, _ = S3.render(s, S3.camera(s, s["shots"][sid]), w, h)
    return [it["id"] for it, _ in S3.visible(s, ident, "objects")]


def panel_line(sc, shot, label, c):
    """One panel's text in a cell: the behind line first, then (C=1) the ray-cast camera and landmarks, then (D=1) the prop counts."""
    out = panels_behind(sc, [shot], [label])
    if c["C"] == "1" or c["D"] == "1":
        s = sets_of(sc)
        if c["C"] == "1":
            cam, lm = layout_words(s, shot["id"])
            out += f" Camera: {cam}; from left to right in this panel: {', '.join(lm) if lm else 'no landmark'}."
        if c["D"] == "1":
            out += " " + K.prop_counts(object_ids(s, shot["id"]))
    return out


GRID_SHOTS = {"c": ("s0", "s1", "s2", "s3")}  # an in-context grid holds the master in panel 1, so it draws s1..s3 only (as M4)
PAIR_LABELS = ("right",)


def cell_prompt(sc, c, sid=None):
    """The text of a cell picture (no model). A grid cell takes the four panels, a pair cell the one target shot ``sid`` (left panel = the master s0)."""
    n = len(sc["cast"])
    place, cast = sc["place"], X.cast_text(sc)
    if c["A"] == "g":
        ids = GRID_SHOTS.get(c["B"], L.SHOTS)
        shots = [shot_of(sc, s) for s in ids]
        body = " ".join(panel_line(sc, sh, X.ORDER[i], c) for i, sh in enumerate(shots))
        body += cell_extras(sc, c, [sh["id"] for sh in shots])
        head = {
            "n": f"{TRIGGER}, a storyboard of 4 panels in a 2x2 grid separated by thin white borders, the same place, the same people with the same faces and clothes in every panel, four different camera shots.",
            "e": f"{TRIGGER}, Image 1 is this scene: the same place and the same {n} people with the same faces and clothes. Draw a four-panel storyboard in a 2x2 grid separated by thin white borders, continuing it.",
            "c": f"{TRIGGER}, Image 1 is a storyboard of 4 panels in a 2x2 grid: its top-left panel is final and the other three panels are still grey. Draw the whole storyboard: keep the top-left panel as it is and fill the three grey panels with later shots of the same place and the same {n} people with the same faces and clothes.",
            "s": f"{TRIGGER}, the images are the model sheets of the {n} people. Draw a storyboard of 4 panels in a 2x2 grid separated by thin white borders: the same place, and these people with exactly these faces and clothes in every panel, four different camera shots.",
        }[c["B"]]
        return f"{head} The place: {place} {cast} {body}"
    left = panel_line(sc, shot_of(sc, "s0"), "left", dict(c, C="0", D="0"))
    right = panel_line(sc, shot_of(sc, sid), "right", c)
    head = {
        "n": f"{TRIGGER}, a pair of two panels side by side separated by a thin white border: the left panel is the established wide shot, the right panel is another shot of the same place and the same {n} people with the same faces and clothes.",
        "e": f"{TRIGGER}, Image 1 is the established wide shot of this scene: the same place and the same {n} people with the same faces and clothes. Draw a pair of two panels side by side separated by a thin white border: the left panel is that wide shot, the right panel is another shot of the same scene.",
        "c": f"{TRIGGER}, Image 1 is a pair of two panels: its left panel is final and the right panel is still grey. Draw the whole pair: keep the left panel as it is and fill the right panel with another shot of the same place and the same {n} people with the same faces and clothes.",
        "s": f"{TRIGGER}, Image 1 is a pair of two panels whose left panel is final and whose right panel is grey; the other images are the model sheets of the people. Draw the whole pair: keep the left panel and fill the right panel with another shot of the same place and these people with exactly these faces and clothes.",
    }[c["B"]]
    return f"{head} The place: {place} {cast} {left} {right}"


def po_plate_prompt(sc, shot):
    """The text of the paintover plate: the EMPTY place as this shot's camera sees it (the people are added in the next step)."""
    return (f"{TRIGGER}, {shot['size']} shot of an empty place with no people. The place: {sc['place']} "
            f"{('Behind and around: ' + shot['layout']) if shot.get('layout') else ''}").strip()


def po_people_prompt(sc, shot, s):
    """The text that adds the people to a plate: image 1 = the painted empty place (kept), then one sheet per person; where each stands comes from the ray cast."""
    roles = [r for r in shot.get("faces", []) if r in sc["cast"]][:2]
    where = DR.people_words(s, shot["id"])
    pos = " ".join(f"The person of the model sheet of {r} {where[r]}." for r in roles if r in where)
    base = p2s_prompt(framed(sc, shot), sc["cast"], roles) if roles else p2s_plain("P2F", framed(sc, shot))
    base = base.replace("Image 1 is the master frame of the place", "Image 1 is the empty place in exactly this camera view with every object where it must be")
    base = base.replace("the place as in image 1", "the place and every object exactly where they are in image 1")
    return f"{base} {pos}".strip(), roles


def sdedit(pipe, prompt, init, strength, seed, w, h, steps, cfg):
    """Paints over an init picture (SDEdit, flow matching): the init's latents are noised to the sigma the shortened schedule starts at, and the
    normal pipeline denoises from there with the LoRA. Strength 1.0 = a full redraw, 0 = the init unchanged."""
    import copy
    import numpy as np
    import torch
    if __package__:
        from videox_fun.pipeline.pipeline_qwenimage21 import calculate_shift
    else:
        from videox_fun.pipeline.pipeline_qwenimage21 import calculate_shift
    dev = pipe._execution_device
    gen = torch.Generator(device="cuda").manual_seed(seed)
    x = pipe.image_processor.preprocess(init.convert("RGB"), width=w, height=h).unsqueeze(2).to(dev, torch.bfloat16)
    with torch.no_grad():
        enc = pipe._encode_vae_image(x, gen)
        c = pipe.transformer.config.in_channels
        x0 = pipe._pack_latents(enc, 1, c, enc.shape[3], enc.shape[4])
        k = max(1, int(round(strength * steps)))
        sig = np.linspace(1.0, 1 / steps, steps)[steps - k:]
        sc = pipe.scheduler.config
        mu = calculate_shift(x0.shape[1], sc.get("base_image_seq_len", 256), sc.get("max_image_seq_len", 4096), sc.get("base_shift", 0.5), sc.get("max_shift", 1.15))
        sch = copy.deepcopy(pipe.scheduler)
        sch.set_timesteps(sigmas=sig, device=dev, mu=mu)
        s0 = float(sch.sigmas[0])
        noise = torch.randn(x0.shape, generator=gen, device=dev, dtype=x0.dtype)
        lat = (1 - s0) * x0 + s0 * noise
        return pipe(prompt, image=None, negative_prompt="", height=h, width=w, generator=gen, num_inference_steps=len(sig),
                    true_cfg_scale=cfg, latents=lat, sigmas=sig).images[0]


def base_images(c):
    """How many images the reference level B of a cell gives (the extras are numbered after them)."""
    return {"n": 0, "e": 1, "c": 1, "s": 2 if c["A"] == "g" else 3}[c["B"]]


def cell_extras(sc, c, shot_ids):
    """The text that tells the prompt what the extra images are (E: dir, sk, dsk); they come after the reference images."""
    if not c.get("E"):
        return ""
    s = sets_of(sc)
    k = base_images(c) + 1
    out = []
    if c["E"] in ("dir", "dsk"):
        out.append(DR.dir_words(s, shot_ids, k)); k += 1
    if c["E"] in ("sk", "dsk"):
        out.append(DR.sketch_words(k))
    return " " + " ".join(out)


def cell_refs(c, master, sheets, extras=()):
    """The images of a cell picture, at most three (Opus plan 10): n none, e the master, c the canvas with the master in its first panel,
    s the model sheets (on a pair canvas the pair canvas comes first)."""
    b = c["B"]
    if b == "n":
        base = []
    elif b == "e":
        base = [master.resize(L.PANEL)]
    else:
        canvas = L.pair_canvas(master) if c["A"] == "p" else L.inpaint_canvas(master, fill="grey")[0]
        base = [canvas] if b == "c" else ([canvas] if c["A"] == "p" else []) + list(sheets)[:2]
    out = base + list(extras)
    if len(out) > 3:
        raise ValueError(f"{len(out)} images in a cell: at most 3")
    return out


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
        img6, mask6 = L.inpaint_canvas(master, fill="noise")
        img6.save(outd / f"{n}_m6_image.png"); mask6.save(outd / f"{n}_m6_mask.png")
        made.update({f"{n}_m2_control.png": "M2", f"{n}_m4_control.png": "M4", f"{n}_m4_image.png": "M4", f"{n}_m4_mask.png": "M4",
                     f"{n}_m6_image.png": "M6", f"{n}_m6_mask.png": "M6"})
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


STEPS = 30


class ControlEnd:
    """Ends the control branch once the denoising is half way: zeroes `control_context_scale` in the transformer's forward kwargs from the first
    call whose `timestep` is below half of the first call's timestep (Opus 2026-10-26; no call counting, so batched CFG or another step count
    cannot move the cut). Records the timestep at the cut; `ok()` is False when the scale kwarg or the timestep was never seen or nothing was
    zeroed: that row is a SETUP-FAIL and is never scored as a plain M2/M4."""

    def __init__(self, transformer, frac=0.5):
        self.tr, self.frac, self.t0, self.cut_t, self.seen, self.tseen, self.zeroed = transformer, frac, None, None, False, False, 0

    @staticmethod
    def _t(v):
        try:
            return float(v.flatten()[0]) if hasattr(v, "flatten") else float(v)
        except Exception:
            return None

    def __enter__(self):
        self.orig = self.tr.forward

        def fwd(*a, **kw):
            t = self._t(kw["timestep"]) if "timestep" in kw else None
            if t is not None:
                self.tseen = True
                if self.t0 is None:
                    self.t0 = t
            if "control_context_scale" in kw:
                self.seen = True
                if t is not None and self.t0 is not None and t < self.frac * self.t0:
                    if self.cut_t is None:
                        self.cut_t = t
                    kw["control_context_scale"] = 0.0
                    self.zeroed += 1
            return self.orig(*a, **kw)
        self.tr.forward = fwd
        return self

    def __exit__(self, *e):
        self.tr.forward = self.orig

    def ok(self):
        return self.seen and self.tseen and self.zeroed > 0

    def report(self):
        return (f"control end: scale kwarg seen={self.seen}, timestep seen={self.tseen}, t0={self.t0}, cut at t={self.cut_t}, "
                f"zeroed {self.zeroed} calls, ok={self.ok()}")


def draw_control(pipe, prompt, control, scale, cfg, seed, w, h, image=None, mask=None, end=None, say=print, fail_dir=None):
    import contextlib
    import torch
    from videox_fun.utils.utils import get_image_latent
    g = torch.Generator(device="cuda").manual_seed(seed)
    ctrl = get_image_latent(control, sample_size=[h, w])[:, :, 0]
    kw = {} if image is None else {"image": image.resize((w, h)), "mask_image": mask.resize((w, h))}
    ce = ControlEnd(pipe.transformer, end) if end else contextlib.nullcontext()
    with torch.no_grad(), ce:
        out = _call(pipe, prompt, g, h, w, cfg, ctrl, scale, kw)
    if end:
        say(ce.report())
        if not ce.ok() and fail_dir is not None:  # never scored as a plain M2/M4
            (Path(fail_dir) / "SETUP_FAIL.json").write_text(json.dumps({"reason": ce.report()}), encoding="utf-8")
    return out


def _call(pipe, prompt, g, h, w, cfg, ctrl, scale, kw):
    if True:
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
    scenes = [s for s in load_scenes(scene_dir) if s["name"] in cfg.get("scenes", L.SCENES)]  # round 1: the card shots s0..s4 only
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
            end, row_ = L.ROWS[row].get("end"), L.ROWS[row].get("base", row)
            t0 = time.time()
            if row_ == "S3cA":
                img = draw_control(p, prompts(sc, row, j["shot"]), Image.open(inp / f"{n}_{j['shot']}_depth.png"), scale, cf, seed, 1280, 720)
                img.convert("RGB").save(outd / row / f"{n}_{seed}_{j['shot']}.png")
            elif row_ == "M5":
                s_ = j["shot"]
                img = draw_control(p, prompts(sc, row, s_), Image.open(inp / f"M5_{n}_{s_}_depth.png"), scale, cf, seed, 1280, 720,
                                   Image.open(inp / f"M5_{n}_{s_}_warp.png").convert("RGB"), Image.open(inp / f"M5_{n}_{s_}_holes.png").convert("L"))
                img.convert("RGB").save(outd / row / f"{n}_{seed}_{s_}.png")
            elif row_ == "M2":
                g = draw_control(p, prompts(sc, row), Image.open(inp / f"{n}_m2_control.png"), scale, cf, seed, 2560, 1408, end=end, say=say, fail_dir=outd / row)
                cut_grid(g.convert("RGB"), L.SHOTS, outd, row, n, seed)
            elif row == "M6":  # round 2: the control OFF (scale 0), the noise-filled canvas, the master kept in panel 1
                master = Image.open(p2s / f"{n}_11_s0.png").convert("RGB")
                g = draw_control(p, prompts(sc, row), Image.open(inp / f"{n}_m4_control.png"), 0.0, cf, seed, 2560, 1408,
                                 Image.open(inp / f"{n}_m6_image.png").convert("RGB"), Image.open(inp / f"{n}_m6_mask.png").convert("L"),
                                 say=say, fail_dir=outd / row)
                say("M6 fill survived (copied share, before paste-back):", round(L.fill_survived(g.convert("RGB"), master), 3), n, seed)
                cut_grid(L.paste_back(g.convert("RGB"), master), (None, "s1", "s2", "s3"), outd, row, n, seed)
            elif row_ == "M4":
                master = Image.open(p2s / f"{n}_11_s0.png").convert("RGB")
                g = draw_control(p, prompts(sc, row), Image.open(inp / f"{n}_m4_control.png"), scale, cf, seed, 2560, 1408,
                                 Image.open(inp / f"{n}_m4_image.png").convert("RGB"), Image.open(inp / f"{n}_m4_mask.png").convert("L"), end=end, say=say, fail_dir=outd / row)
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
    for j in [x for x in jobs if x["row"] in PLAIN_ROWS or K.parse(x["row"])]:
        if exists(j):
            continue
        sc, n, seed, row = by[j["scene"]], j["scene"], j["seed"], j["row"]
        t.SEED = seed
        t0 = time.time()
        master = Image.open(p2s / f"{n}_11_s0.png").convert("RGB")
        if row in PO_STRENGTH:  # paintover (round 3a): the shaded ray-cast plate of the EMPTY place, painted over, then the people added by the edit pipeline
            sid, st = j["shot"], PO_STRENGTH[row]
            plate_path = outd / row / f"{n}_{seed}_{sid}_plate.png"
            t.W, t.H = L.PANEL
            plate = sdedit(p, prompts(sc, row, sid), DR.shaded_plate(sets_of(sc), sid), st, seed, *L.PANEL, t.STEPS, cf).convert("RGB")
            plate.save(plate_path)
            pr, roles = po_people_prompt(sc, shot_of(sc, sid), sets_of(sc))
            refs = [plate] + [Image.open(p2s / f"{n}_sheet_{r}.png").convert("RGB") for r in roles]
            t.draw(p, pr, refs).convert("RGB").save(outd / row / f"{n}_{seed}_{sid}.png")
        elif row == "TURN":  # the empty place from four directions (round 3a), the master as Image 1
            t.W, t.H = X.GRID_W, X.GRID_H
            img = t.draw(p, prompts(sc, row), [master.resize(L.PANEL)]).convert("RGB")
            img.save(outd / row / f"{n}_{seed}_grid.png")
        elif K.parse(row):
            c = K.parse(row)
            sheets = [Image.open(p2s / f"{n}_sheet_{r}.png").convert("RGB") for r in sc["cast"]]
            extras = []
            if c["E"] in ("dir", "dsk"):
                tp = sorted((outd / "TURN").glob(f"{n}_*_grid.png"))
                if not tp:
                    say("skip", row, n, seed, "(no turnaround picture)")
                    continue
                extras.append(Image.open(tp[0]).convert("RGB"))
            if c["E"] in ("sk", "dsk"):
                extras.append(DR.sketch_canvas(sets_of(sc), GRID_SHOTS.get(c["B"], L.SHOTS)))
                extras[-1].save(outd / row / f"{n}_{seed}_sketch.png")
            refs = cell_refs(c, master, sheets, extras)
            t.W, t.H = (X.GRID_W, X.GRID_H) if c["A"] == "g" else (2 * L.PANEL[0], L.PANEL[1])
            img = t.draw(p, prompts(sc, row, j["shot"]), refs).convert("RGB")
            if c["B"] == "c":
                gs = L.grey_copied(img, c["A"])
                say("cell", row, n, seed, "grey copied share", round(gs, 3))
                if gs > 0.5:  # the reference was copied: a SETUP_FAIL of this cell, never a strategy failure
                    (outd / row / "SETUP_FAIL.json").write_text(json.dumps({"reason": f"grey panels copied ({gs:.2f})"}), encoding="utf-8")
            if c["A"] == "g":
                cut_grid(img, GRID_SHOTS.get(c["B"], L.SHOTS) if c["B"] != "c" else (None, "s1", "s2", "s3"), outd, row, n, seed)
            else:
                img.save(outd / row / f"{n}_{seed}_{j['shot']}_pair.png")
                img.crop((L.PANEL[0], 0, 2 * L.PANEL[0], L.PANEL[1])).save(outd / row / f"{n}_{seed}_{j['shot']}.png")
        elif row in ("S2T", "S2Tp", "S2L"):
            t.W, t.H = X.GRID_W, X.GRID_H
            cut_grid(t.draw(p, prompts(sc, row), []).convert("RGB"), L.SHOTS, outd, row, n, seed)
        elif row in ("S2E", "S2Ep"):
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
    scenes = [s for s in load_scenes(scene_dir) if s["name"] in cfg.get("scenes", L.SCENES)]  # round 1: the card shots s0..s4 only
    print(len(build_inputs(cfg, scenes, sets_dir, p2s, outd)), "input files")


if __name__ == "__main__":
    if sys.argv[1:2] == ["inputs"]:
        inputs_main(sys.argv[2:])
    elif sys.argv[1:2] == ["draw"]:
        main(sys.argv[2:])
    else:
        raise SystemExit(__doc__)
