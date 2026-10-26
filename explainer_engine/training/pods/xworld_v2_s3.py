"""The xworld_v2 layout test S3 (D-75; the Opus thread's plan /mnt/project-files/xworld_v2/S3_LAYOUT_PLAN_2026-10-26.md):
every shot of a scene is a camera inside ONE fixed 3D blockout of the set (the studio layout/previs practice); the model is
shown the shot's layout as an extra reference image. QwenImage21Pipeline has no control input, so the layout is just another
reference and two encodings are tested: S3d (grey depth) and S3b (flat-coloured blockout named by colour in the prompt).
Numpy + PIL only, no Blender.

Set file (stories/v2/sets/<scene>.set.json, metres, x right, y away from the master camera, z up): room (interior) or
ground plane (exterior), objects (boxes), people (cylinder + head sphere), `axis` (the two main people, the 180 degree line)
and `shots`: per shot either `cam` {pos, look_at} or a subject camera: subject, size (wide|medium|close), angle
(eye|high|low) and one of `ots` (over that person's shoulder), `from` ([x, y] direction point) or `side` (A|B of the axis).

    python xworld_v2_s3.py <scene dir> <p2s out dir> <out dir> <lora .safetensors> [scenes] [cfg]    (on the pod)
    python xworld_v2_s3.py preview <scene dir> <out dir> [scenes]                                      (free, layouts only)
Pod run draws, per scene and shot s1..s4: S1 (master + sheet, no layout), S3d and S3b (master + layout + sheet) with the
P2S master and sheets, same seed, cfg and weight; the layout image is the only difference. Scoring: `spearman`.
"""
from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

import numpy as np

if __package__:
    from .xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from .xworld_v1_test import TRIGGER
else:
    from xworld_v2_scenes import SEEDS, frame_desc, frame_extras, load
    from xworld_v1_test import TRIGGER

SCENES = ("tent", "rome")
SEED = SEEDS[0]
W, H = 1280, 720
VISIBLE_H = {"medium": 1.3, "close": 0.45}  # wide = the room's height x 1.2 (exterior: 6 m)
EYE, LOW = 1.6, 0.6
MIN_PIXELS = 0.005  # an object is named in the prompt when it covers at least this share of the picture
COLOR_WORDS = {"red": (200, 60, 50), "green": (60, 170, 80), "blue": (30, 40, 140), "yellow": (230, 200, 40),
               "brown": (150, 90, 40), "purple": (140, 60, 120), "orange": (230, 130, 40), "cyan": (40, 180, 200)}
LIGHT = np.array([0.4, -0.5, 0.8]) / np.linalg.norm([0.4, -0.5, 0.8])


def load_set(path):
    s = json.loads(Path(path).read_text(encoding="utf-8"))
    check_set(s)
    return s


def check_set(s):
    """Small schema check: ids unique, min < max, people inside the room, every shot has a camera."""
    ids = [o["id"] for o in s["objects"]] + [p["id"] for p in s["people"]]
    if len(ids) != len(set(ids)):
        raise ValueError(f"{s['scene']}: ids are not unique")
    for o in s["objects"]:
        if not all(a < b for a, b in zip(o["min"], o["max"])):
            raise ValueError(f"{s['scene']}: {o['id']} has min >= max")
    if s["kind"] == "interior":
        lo, hi = s["room"]["min"], s["room"]["max"]
        for p in s["people"]:
            if not (lo[0] < p["pos"][0] < hi[0] and lo[1] < p["pos"][1] < hi[1]):
                raise ValueError(f"{s['scene']}: {p['id']} is outside the room")
    for sid, sp in s["shots"].items():
        if "cam" not in sp and not ("subject" in sp and ("ots" in sp or "from" in sp or "side" in sp)):
            raise ValueError(f"{s['scene']}: shot {sid} has no camera rule")


def _person(s, pid):
    return next(p for p in s["people"] if p["id"] == pid)


def _unit(v):
    v = np.asarray(v, float)
    return v / (np.linalg.norm(v) or 1.0)


def camera(s, spec):
    """{pos, look_at, vfov} of one shot, from its card (see the module docstring)."""
    vfov = s.get("vfov", 45)
    if "cam" in spec:
        pos, look = np.array(spec["cam"]["pos"], float), np.array(spec["cam"]["look_at"], float)
        return {"pos": _clamp(s, pos), "look_at": look, "vfov": vfov}
    p = _person(s, spec["subject"])
    sub = np.array(p["pos"], float)
    size = spec.get("size", "medium")
    room_h = (s["room"]["max"][2] - s["room"]["min"][2]) * 1.2 if s["kind"] == "interior" else 6.0
    vis = room_h if size == "wide" else VISIBLE_H[size]
    d = (vis / 2) / math.tan(math.radians(vfov) / 2)
    hh = p["height"]
    angle = spec.get("angle", "eye")
    z = {"eye": EYE, "high": hh + 2.0, "low": LOW}[angle]
    look = np.array([sub[0], sub[1], hh - 0.12 if size == "close" else 0.65 * hh])
    if "ots" in spec:
        o = np.array(_person(s, spec["ots"])["pos"], float)
        v = _unit(sub - o)
        xy = o - v * 0.35 + np.array([-v[1], v[0]]) * 0.25
        pos = np.array([xy[0], xy[1], hh - 0.1])
        return {"pos": _clamp(s, pos), "look_at": look, "vfov": vfov}
    if "from" in spec:
        direc = _unit(np.array(spec["from"], float) - sub)
    else:
        a, b = (np.array(_person(s, i)["pos"], float) for i in s["axis"])
        ax = _unit(b - a)
        n = np.array([-ax[1], ax[0]])
        direc = n if spec["side"] == "A" else -n
    xy = sub + direc * d
    return {"pos": _clamp(s, np.array([xy[0], xy[1], z])), "look_at": look, "vfov": vfov}


def _clamp(s, pos):
    if s["kind"] != "interior":
        return pos
    lo, hi = np.array(s["room"]["min"], float) + 0.1, np.array(s["room"]["max"], float) - 0.1
    return np.minimum(np.maximum(pos, lo), hi)


def _rays(cam, w, h):
    f = _unit(cam["look_at"] - cam["pos"])
    right = _unit(np.cross(f, [0, 0, 1.0]))
    up = np.cross(right, f)
    tn = math.tan(math.radians(cam["vfov"]) / 2)
    u = ((np.arange(w) + 0.5) / w * 2 - 1) * (w / h) * tn
    v = (1 - (np.arange(h) + 0.5) / h * 2) * tn
    d = f[None, None, :] + u[None, :, None] * right[None, None, :] + v[:, None, None] * up[None, None, :]
    return (d / np.linalg.norm(d, axis=2, keepdims=True)).reshape(-1, 3)


def _slab(o, d, lo, hi):
    d = np.where(np.abs(d) < 1e-9, 1e-9, d)
    t1, t2 = (lo - o) / d, (hi - o) / d
    tmin, tmax = np.minimum(t1, t2), np.maximum(t1, t2)
    return tmin, tmax


def render(s, cam, w=W, h=H):
    """(id map, t map, shade): id >= 0 index into objects + people, -1 sky, -2 wall/ceiling, -3 floor; t = nan on a miss."""
    o = np.asarray(cam["pos"], float)
    d = _rays(cam, w, h)
    n = len(d)
    best = np.full(n, np.inf)
    ident = np.full(n, -1)
    norm = np.zeros((n, 3))

    def take(mask_t, t, i, normal):
        better = mask_t & (t < best)
        best[better] = t[better]
        ident[better] = i
        norm[better] = normal[better] if getattr(normal, "ndim", 1) == 2 else normal

    if s["kind"] == "interior":
        tmin, tmax = _slab(o, d, np.array(s["room"]["min"], float), np.array(s["room"]["max"], float))
        t = tmax.min(axis=1)
        ax = tmax.argmin(axis=1)
        nm = np.zeros((n, 3)); nm[np.arange(n), ax] = -np.sign(d[np.arange(n), ax])
        ids = np.where(nm[:, 2] > 0.5, -3, -2)
        best[:] = t; ident[:] = ids; norm[:] = nm
    else:
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(d[:, 2] < -1e-9, -o[2] / d[:, 2], np.inf)
        ok = np.isfinite(t) & (t > 0) & (t < s.get("far", 1e3))
        best[ok] = t[ok]; ident[ok] = -3; norm[ok] = [0, 0, 1.0]
    for i, ob in enumerate(s["objects"]):
        tmin, tmax = _slab(o, d, np.array(ob["min"], float), np.array(ob["max"], float))
        t0, t1 = tmin.max(axis=1), tmax.min(axis=1)
        hit = (t1 >= t0) & (t0 > 0)
        ax = tmin.argmax(axis=1)
        nm = np.zeros((n, 3)); nm[np.arange(n), ax] = -np.sign(d[np.arange(n), ax])
        take(hit, t0, i, nm)
    base = len(s["objects"])
    for j, p in enumerate(s["people"]):
        cx, cy = p["pos"]; r = p["radius"]; top = p["height"] - 0.12
        ox, oy = o[0] - cx, o[1] - cy
        a = d[:, 0] ** 2 + d[:, 1] ** 2
        b = 2 * (ox * d[:, 0] + oy * d[:, 1])
        c = ox * ox + oy * oy - r * r
        disc = b * b - 4 * a * c
        with np.errstate(divide="ignore", invalid="ignore"):
            t = (-b - np.sqrt(np.where(disc >= 0, disc, np.nan))) / (2 * a)
        z = o[2] + t * d[:, 2]
        hit = np.isfinite(t) & (t > 0) & (z >= 0) & (z <= top)
        nm = np.stack([ox + t * d[:, 0], oy + t * d[:, 1], np.zeros(n)], axis=1) / r
        take(hit, np.where(hit, t, np.inf), base + j, nm)
        sc = np.array([cx, cy, p["height"] - 0.12]); rr = 0.12
        oc = o - sc
        bq = d @ oc; cq = oc @ oc - rr * rr
        disq = bq * bq - cq
        with np.errstate(invalid="ignore"):
            t = -bq - np.sqrt(np.where(disq >= 0, disq, np.nan))
        hit = np.isfinite(t) & (t > 0)
        pt = o[None, :] + t[:, None] * d
        take(hit, np.where(hit, t, np.inf), base + j, (pt - sc[None, :]) / rr)
    miss = ~np.isfinite(best)
    shade = 0.75 + 0.25 * np.abs(norm @ LIGHT)
    tmap = np.where(miss, np.nan, best)
    return ident.reshape(h, w), tmap.reshape(h, w), shade.reshape(h, w)


def depth_image(tmap):
    """Grey depth: white = near, black = far / sky; linear in 1/t between the 2nd and 98th percentile of the hits."""
    from PIL import Image
    inv = 1.0 / tmap
    hits = inv[np.isfinite(inv)]
    lo, hi = np.percentile(hits, 2), np.percentile(hits, 98)
    g = np.clip((inv - lo) / max(hi - lo, 1e-9), 0, 1)
    g = np.where(np.isfinite(inv), g, 0.0)
    return Image.fromarray((g * 255).astype(np.uint8), "L").convert("RGB")


def blockout_image(s, ident, shade):
    from PIL import Image
    pal = {-1: (190, 215, 235), -2: (205, 205, 205), -3: (140, 140, 140)}
    cols = [tuple(o["color"]) for o in s["objects"]] + [tuple(p["color"]) for p in s["people"]]
    img = np.zeros(ident.shape + (3,))
    for k in np.unique(ident):
        img[ident == k] = pal[int(k)] if k < 0 else cols[int(k)]
    return Image.fromarray(np.clip(img * shade[..., None], 0, 255).astype(np.uint8))


def visible(s, ident, kind):
    """[(item, color word)] of the objects (kind 'objects') or people ('people') in the picture, left to right."""
    items = s[kind]
    base = 0 if kind == "objects" else len(s["objects"])
    out = []
    xs = np.arange(ident.shape[1])[None, :].repeat(ident.shape[0], axis=0)
    for i, it in enumerate(items):
        m = ident == base + i
        if m.mean() >= MIN_PIXELS:
            out.append((float(xs[m].mean()), it, color_word(it["color"])))
    return [(it, cw) for _, it, cw in sorted(out, key=lambda x: x[0])]


def color_word(rgb):
    return min(COLOR_WORDS, key=lambda k: sum((a - b) ** 2 for a, b in zip(COLOR_WORDS[k], rgb)))


def shot_prompt(sc, shot, s, ident, variant):
    """(prompt, refs) for S1 / S3d / S3b; refs name the pictures in order: master, [layout], [sheet]."""
    role = next((r for r in shot.get("faces", []) if r in sc["cast"]), None)
    nxt = 2
    head = f"{TRIGGER}, Image 1 is the place of this scene: keep its landmarks, light and colours."
    refs = ["master"]
    if variant != "S1":
        refs.append("layout")
        nxt = 3
        objs = visible(s, ident, "objects")
        names = [p["id"] for p, _ in visible(s, ident, "people")]
        if variant == "S3d":
            head += (" Image 2 is a grey depth sketch of this shot's camera view: white is near, black is far. Draw the scene of "
                     "Image 1 from exactly this camera: put " + ", ".join(o["label"] for o, _ in objs) +
                     " where Image 2 has them, and the people where the pale upright shapes are. Image 2 is only a guide: do not draw it.")
        else:
            head += (" Image 2 is a coloured blockout of this shot's camera view: " +
                     "; ".join(f"the {cw} box is {o['label']}" for o, cw in objs) +
                     f"; the pale figures are the people ({', '.join(names) or 'none'}). Draw the scene of Image 1 from exactly this "
                     "camera, with everything where Image 2 has it. Image 2 is only a guide: do not draw boxes.")
    if role:
        head += f" Image {nxt} is {role}'s model sheet: keep their face and clothes exactly."
        refs.append("sheet:" + role)
    return f"{head} {frame_desc(shot)} {shot.get('change') or ''} {frame_extras(sc, shot)}".strip(), refs


def layouts(s, outd):
    """Render every shot's camera to <out>/<scene>_<shot>_{depth,block}.png; returns {shot id: ident map}."""
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    out = {}
    for sid, spec in s["shots"].items():
        ident, tmap, shade = render(s, camera(s, spec))
        depth_image(tmap).save(outd / f"{s['scene']}_{sid}_depth.png")
        blockout_image(s, ident, shade).save(outd / f"{s['scene']}_{sid}_block.png")
        np.save(outd / f"{s['scene']}_{sid}_t.npy", tmap.astype(np.float32))
        out[sid] = ident
    return out


def spearman(a, b):
    """Rank correlation of two equal-size arrays (nan pairs dropped)."""
    a, b = np.asarray(a, float).ravel(), np.asarray(b, float).ravel()
    ok = np.isfinite(a) & np.isfinite(b)
    ra, rb = np.argsort(np.argsort(a[ok])), np.argsort(np.argsort(b[ok]))
    return float(np.corrcoef(ra, rb)[0, 1])


def preview(scene_dir, sets_dir, outd, only=SCENES):
    from PIL import Image
    outd = Path(outd); outd.mkdir(parents=True, exist_ok=True)
    rows = []
    for name in only:
        s = load_set(Path(sets_dir) / f"{name}.set.json")
        layouts(s, outd)
        for kind in ("block", "depth"):
            rows.append([Image.open(outd / f"{name}_{sid}_{kind}.png").resize((384, 216)) for sid in s["shots"]])
    sheet = Image.new("RGB", (384 * 5, 216 * len(rows)), (255, 255, 255))
    for r, row in enumerate(rows):
        for c, im in enumerate(row):
            sheet.paste(im, (c * 384, r * 216))
    out = outd / "s3_layouts.jpg"
    sheet.save(out, quality=88)
    return out


def main(argv):
    from PIL import Image
    if __package__:
        from . import xworld_v1_test as t
    else:
        import xworld_v1_test as t
    scene_dir, p2s_dir, outd, lora = argv[:4]
    only = argv[4].split(",") if len(argv) > 4 and argv[4] else SCENES
    cfg = float(argv[5]) if len(argv) > 5 else 2.5
    outd, p2s_dir = Path(outd), Path(p2s_dir); outd.mkdir(parents=True, exist_ok=True)
    say = t.logger(outd, "s3.log")
    say("cfg", cfg, "weight 1.0 seed", SEED)
    pipe, tr = t.load_pipeline()
    p = t.Loras(pipe, tr, {"R": lora}, say).use("R", 1.0)
    t.SEED, t.CFG = SEED, cfg
    for sc in (x for x in load(scene_dir) if x["name"] in only):
        s = load_set(Path(scene_dir) / "sets" / f"{sc['name']}.set.json")
        idents = layouts(s, outd)
        for shot in sc["shots"][1:]:
            for variant in ("S1", "S3d", "S3b"):
                name = f"{sc['name']}_{shot['id']}_{variant}"
                if (outd / f"{name}.png").exists():
                    continue
                prompt, refs = shot_prompt(sc, shot, s, idents[shot["id"]], variant)
                files = {"master": p2s_dir / f"{sc['name']}_{SEED}_s0.png",
                         "layout": outd / f"{sc['name']}_{shot['id']}_{'depth' if variant == 'S3d' else 'block'}.png"}
                imgs = [Image.open(files.get(r) or p2s_dir / f"{sc['name']}_sheet_{r.split(':')[1]}.png").convert("RGB") for r in refs]
                t0 = time.time()
                t.draw(p, prompt, imgs[:3]).convert("RGB").save(outd / f"{name}.png")
                (outd / f"{name}.txt").write_text(prompt, encoding="utf-8")
                say("made", name, round(time.time() - t0), "s")


if __name__ == "__main__":
    if sys.argv[1:2] == ["preview"]:
        print(preview(sys.argv[2], Path(sys.argv[2]) / "sets", sys.argv[3], sys.argv[4].split(",") if len(sys.argv) > 4 else SCENES))
    else:
        main(sys.argv[1:])
