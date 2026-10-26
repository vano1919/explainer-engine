"""The xworld_v2 storyboard test S2 (D-75; the Opus thread's plan 2026-10-26 16:39 UTC): one canvas holds a 2x2 grid of four
shots of ONE scene, so the model draws place, faces and clothes once and every panel shares them (the idea of In-Context LoRA,
arXiv 2410.23775, and StoryDiffusion, 2405.01434). The grid is cut into panels and each panel is cleaned up as a P2F-style
edit of itself at 1280x720.

For each scene (tent, rome), seed 11, ONE checkpoint, LoRA weight 1.0:
  grid   shots 0..3 of the scene in one 1792x1008 picture, thin white borders, panel order top-left, top-right, bottom-left, bottom-right
  panel  the four panels cut out of the grid (border search, so a slightly shifted gutter still cuts right)
  clean  each panel as the reference of an edit "same picture, sharp clean ink lines" at 1280x720
Gate: the first grid is drawn and cut before the rest (the run stops with GATE in the log when its panels are not four).

    python xworld_v2_s2.py <scene dir> <out dir> <lora .safetensors> [scenes comma list] [cfg]
writes <out>/<scene>_grid.png, <scene>_p<k>.png, <scene>_c<k>.png, s2.log; drawn pictures are skipped on a rerun.
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

if __package__:
    from .xworld_v2_scenes import SEEDS, frame_desc, load
    from .xworld_v1_story import face_problems
    from .xworld_v1_test import TRIGGER
else:
    from xworld_v2_scenes import SEEDS, frame_desc, load
    from xworld_v1_story import face_problems
    from xworld_v1_test import TRIGGER

SCENES = ("tent", "rome")
SEED = SEEDS[0]
GRID_W, GRID_H = 1792, 1008
PANELS = 4
ORDER = ("top-left", "top-right", "bottom-left", "bottom-right")
CLEAN = f"{TRIGGER}, the same picture at full size, same people, same clothes, same place, sharp clean ink lines."


def grid_prompt(sc):
    """One prompt for the whole canvas: the cast once, then the four panels in order."""
    shots = sc["shots"][:PANELS]
    cast = " ".join(f"{role}: {c['look']} {c['face']}" for role, c in sc["cast"].items())
    panels = " ".join(f"{ORDER[i]} panel: {frame_desc(s)} {s['layout']}" for i, s in enumerate(shots))
    return (f"{TRIGGER}, a storyboard of {PANELS} panels in a 2x2 grid separated by thin white borders, the same place, the same "
            f"people with the same faces and clothes in every panel, four different camera shots. {cast} {panels}")


def _is_border(vals, lo=0.9):
    return sum(vals) / max(len(vals), 1) >= lo * 255


def gutters(img):
    """(x, y) of the middle gutter's centre: the brightest column / row band near the centre of the canvas (greyscale means)."""
    g = img.convert("L")
    w, h = g.size
    col = [sum(g.crop((x, 0, x + 1, h)).getdata()) / h for x in range(w)]
    row = [sum(g.crop((0, y, w, y + 1)).getdata()) / w for y in range(h)]
    cx = max(range(w * 2 // 5, w * 3 // 5), key=col.__getitem__)
    cy = max(range(h * 2 // 5, h * 3 // 5), key=row.__getitem__)
    return cx, cy


def cut(img, pad=6):
    """The four panels of a 2x2 grid, row by row; pad drops the border pixels round each panel."""
    w, h = img.size
    cx, cy = gutters(img)
    xs, ys = (0, cx, w), (0, cy, h)
    return [img.crop((xs[c] + (pad if c else 0), ys[r] + (pad if r else 0), xs[c + 1] - (0 if c else pad), ys[r + 1] - (0 if r else pad)))
            for r in range(2) for c in range(2)]


def jobs(scenes):
    out = []
    for sc in scenes:
        bad = face_problems(sc)
        if bad:
            raise ValueError(f"{sc['name']}: " + "; ".join(bad))
        out.append({"name": f"{sc['name']}_grid", "scene": sc["name"], "prompt": grid_prompt(sc)})
    return out


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, outd, lora = argv[:3]
    only = argv[3].split(",") if len(argv) > 3 and argv[3] else SCENES
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    todo = jobs([s for s in load(scene_dir) if s["name"] in only])
    say = t.logger(outd, "s2.log")
    pipe, tr = t.load_pipeline()
    loras = t.Loras(pipe, tr, {"R": lora}, say)
    p = loras.use("R", 1.0)
    t.SEED = SEED
    if len(argv) > 4:
        t.CFG = float(argv[4])
    for i, j in enumerate(todo):
        grid = outd / f"{j['name']}.png"
        if not grid.exists():
            t0 = time.time(); t.W, t.H = GRID_W, GRID_H
            t.draw(p, j["prompt"], []).convert("RGB").save(grid)
            say("made", j["name"], round(time.time() - t0), "s")
        panels = cut(Image.open(grid).convert("RGB"))
        for k, pn in enumerate(panels):
            pn.save(outd / f"{j['scene']}_p{k}.png")
        if i == 0:
            sizes = [pn.size for pn in panels]
            say("GATE first grid cut", sizes)  # the first grid is looked at (collage) before the rest are cleaned
    t.W, t.H = 1280, 720
    for j in todo:
        for k in range(PANELS):
            c = outd / f"{j['scene']}_c{k}.png"
            if c.exists():
                continue
            ref = Image.open(outd / f"{j['scene']}_p{k}.png").convert("RGB").resize((1280, 720))
            t0 = time.time()
            t.draw(p, CLEAN, [ref]).convert("RGB").save(c)
            say("made", c.name, round(time.time() - t0), "s")


def sheet(outd, label="S2"):
    """<out>/s2_sheet.jpg: per scene a row of the grid, then a row of its four cut panels and a row of their clean-ups."""
    from PIL import Image
    outd = Path(outd)
    rows = []
    for scene in SCENES:
        g = outd / f"{scene}_grid.png"
        if not g.exists():
            continue
        rows.append([Image.open(g).convert("RGB").resize((640, 360))])
        for tag in ("p", "c"):
            rows.append([Image.open(f).convert("RGB").resize((480, 270)) for f in
                         (outd / f"{scene}_{tag}{k}.png" for k in range(PANELS)) if f.exists()])
    h = sum(max(i.size[1] for i in r) for r in rows) if rows else 0
    w = max((sum(i.size[0] for i in r) for r in rows), default=0)
    sheet_img = Image.new("RGB", (max(w, 1), max(h, 1)), (255, 255, 255)); y = 0
    for r in rows:
        x = 0
        for i in r:
            sheet_img.paste(i, (x, y)); x += i.size[0]
        y += max(i.size[1] for i in r)
    out = outd / "s2_sheet.jpg"
    sheet_img.save(out, quality=88)
    return out


if __name__ == "__main__":
    if sys.argv[1:2] == ["sheet"]:
        print(sheet(sys.argv[2]))
    else:
        main(sys.argv[1:])
