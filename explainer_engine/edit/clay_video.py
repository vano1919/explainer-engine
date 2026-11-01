"""Clay layout clips for LTX-2.5's Layout-To-Render IC-LoRA (P12 stage L2, WP-1c; reusable, OR-21).

The LoRA's model card (Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render @ bd765d55, "Control Signal Requirements"): the driving
clip is "a grey clay viewport, or a blocky playblast of simple shapes" carrying the camera move and where objects sit; 24 fps
preferred; width and height divisible by 64 (1920x1088 known good); the frame count is snapped to 8k+1; the art direction comes
from a keyframe made from the clay's FIRST frame, so the clay's first frame must put every block where the keyframe has its
figure. Nothing here assumes more than that card says: flat-lit grey blocks, a grey floor and back wall, a pinhole camera.

A spec (JSON, one per shot)::

    {"id": "tent_s0", "seconds": 5.0417, "fps": 24, "width": 1920, "height": 1088,
     "camera": [{"t": 0, "pos": [0, 1.6, -6], "look": [0, 1.2, 0], "fov": 50}, {"t": 5, "pos": [0, 1.6, -4.5], ...}],
     "room": {"floor_y": 0, "back_z": 4, "half_width": 8, "height": 4},
     "objects": [{"id": "emperor", "shape": "figure", "size": [0.6, 1.75, 0.4],
                  "keys": [{"t": 0, "pos": [-1.2, 0, 0], "yaw": 20}, {"t": 3, "pos": [-0.8, 0, 0.3], "yaw": 0}]},
                 {"id": "table", "shape": "box", "size": [1.8, 0.8, 1.0], "keys": [{"t": 0, "pos": [0, 0, 0.5]}]}]}

``t`` is in seconds; positions are metres (x right, y up, z away from the camera's start); a key's missing fields hold the
previous key's value; between keys the value eases (smoothstep). Shapes: ``box``, ``cylinder`` (12-sided prism) and ``figure``
(a blocky person: legs, body, head; its ``size`` is width, height, depth). Rendering is a pure function of (spec, frame).

    python -m explainer_engine.edit.clay_video render <spec.json> <out.mp4> [--width W --height H --frames N]
    python -m explainer_engine.edit.clay_video first <spec.json> <out.png>      # the frame the keyframe must match

A file with ``{"shots": {id: spec, ...}}`` (the P12 specs, ``training/pods/p12/clay/clay_specs.json``) is named
``<file.json>#<id>``.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

GRID = 8                     # LTX: frames = 8k + 1 (model card, "Preprocessing")
SIZE_STEP = 64               # width and height divide by 64 (model card)
LIGHT = np.array([-0.4, 0.8, -0.45])
LIGHT = LIGHT / np.linalg.norm(LIGHT)
GREYS = {"floor": 150, "wall": 175, "object": 205}
SKY = (120, 120, 120)


def snap_frames(n: int) -> int:
    """The largest 8k+1 not above ``n`` (the LoRA trims to it; we render exactly that count)."""
    if n < 1:
        raise ValueError("a clip needs at least one frame")
    return (n - 1) // GRID * GRID + 1


def frame_count(spec: dict) -> int:
    return snap_frames(int(round(float(spec["seconds"]) * int(spec.get("fps", 24)))) + 1)


def check_spec(spec: dict) -> list[str]:
    """Problems that make a spec unusable for the LoRA (empty = fine)."""
    out = []
    w, h = int(spec.get("width", 1920)), int(spec.get("height", 1088))
    if w % SIZE_STEP or h % SIZE_STEP:
        out.append(f"{w}x{h}: width and height must divide by {SIZE_STEP} (model card)")
    if not spec.get("camera"):
        out.append("no camera keys")
    for o in spec.get("objects", []):
        if o.get("shape") not in ("box", "cylinder", "figure"):
            out.append(f"{o.get('id')}: shape {o.get('shape')!r} is not box, cylinder or figure")
        if not o.get("keys"):
            out.append(f"{o.get('id')}: no keys")
    return out


def _ease(x: float) -> float:
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def _at(keys: list[dict], t: float, field: str, default):
    """The eased value of ``field`` at time ``t`` over keys sorted by t (a missing field holds the previous value)."""
    filled, last = [], default
    for k in sorted(keys, key=lambda k: float(k.get("t", 0))):
        last = k.get(field, last)
        filled.append((float(k.get("t", 0)), last))
    if not filled:
        return default
    if t <= filled[0][0]:
        return filled[0][1]
    for (t0, v0), (t1, v1) in zip(filled, filled[1:]):
        if t0 <= t <= t1:
            a = _ease((t - t0) / (t1 - t0)) if t1 > t0 else 1.0
            if isinstance(v0, (list, tuple)):
                return [x0 + (x1 - x0) * a for x0, x1 in zip(v0, v1)]
            return v0 + (v1 - v0) * a
    return filled[-1][1]


def _box(cx: float, y0: float, cz: float, w: float, h: float, d: float, yaw: float) -> list[np.ndarray]:
    """Six quads of a box standing on y0, centred on (cx, cz), turned by yaw degrees about y."""
    c, s = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    pts = []
    for dy in (0, h):
        for dx, dz in ((-w / 2, -d / 2), (w / 2, -d / 2), (w / 2, d / 2), (-w / 2, d / 2)):
            pts.append((cx + dx * c + dz * s, y0 + dy, cz - dx * s + dz * c))
    p = np.array(pts)
    idx = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)]
    return [p[list(f)] for f in idx]


def _cylinder(cx: float, y0: float, cz: float, w: float, h: float, d: float, sides: int = 12) -> list[np.ndarray]:
    ring = [(cx + w / 2 * math.cos(2 * math.pi * i / sides), cz + d / 2 * math.sin(2 * math.pi * i / sides)) for i in range(sides)]
    faces = [np.array([(x, y0 + h, z) for x, z in ring])]
    for (x0, z0), (x1, z1) in zip(ring, ring[1:] + ring[:1]):
        faces.append(np.array([(x0, y0, z0), (x1, y0, z1), (x1, y0 + h, z1), (x0, y0 + h, z0)]))
    return faces


def _figure(cx: float, y0: float, cz: float, w: float, h: float, d: float, yaw: float) -> list[np.ndarray]:
    """A blocky person: legs 45 %, body 37 %, head 18 % of the height (a playblast stand-in, not a likeness)."""
    legs, body, head = 0.45 * h, 0.37 * h, 0.18 * h
    return (_box(cx, y0, cz, 0.7 * w, legs, 0.7 * d, yaw) + _box(cx, y0 + legs, cz, w, body, d, yaw)
            + _box(cx, y0 + legs + body, cz, 0.45 * w, head, 0.55 * d, yaw))


def _faces(spec: dict, t: float) -> list[tuple[np.ndarray, int]]:
    room = {"floor_y": 0.0, "back_z": 6.0, "half_width": 10.0, "height": 5.0, "near_z": -20.0, **spec.get("room", {})}
    fy, bz, hw, rh, nz = (float(room[k]) for k in ("floor_y", "back_z", "half_width", "height", "near_z"))
    out = [(np.array([(-hw, fy, nz), (hw, fy, nz), (hw, fy, bz), (-hw, fy, bz)]), GREYS["floor"]),
           (np.array([(-hw, fy, bz), (hw, fy, bz), (hw, fy + rh, bz), (-hw, fy + rh, bz)]), GREYS["wall"])]
    for o in spec.get("objects", []):
        x, y, z = _at(o["keys"], t, "pos", [0.0, fy, 0.0])
        yaw = float(_at(o["keys"], t, "yaw", 0.0))
        w, h, d = (float(v) for v in o.get("size", [1, 1, 1]))
        grey = int(o.get("grey", GREYS["object"]))
        if o["shape"] == "box":
            fs = _box(x, y, z, w, h, d, yaw)
        elif o["shape"] == "cylinder":
            fs = _cylinder(x, y, z, w, h, d)
        else:
            fs = _figure(x, y, z, w, h, d, yaw)
        out += [(f, grey) for f in fs]
    return out


def _camera(spec: dict, t: float) -> tuple[np.ndarray, np.ndarray, float]:
    keys = spec["camera"]
    pos = np.array(_at(keys, t, "pos", [0.0, 1.6, -6.0]), dtype=float)
    look = np.array(_at(keys, t, "look", [0.0, 1.2, 0.0]), dtype=float)
    fov = float(_at(keys, t, "fov", 50.0))
    fwd = look - pos
    fwd /= np.linalg.norm(fwd)
    right = np.cross(np.array([0.0, 1.0, 0.0]), fwd)
    right /= np.linalg.norm(right)
    up = np.cross(fwd, right)
    return pos, np.stack([right, up, fwd]), fov


def render_frame(spec: dict, i: int, width: int | None = None, height: int | None = None) -> Image.Image:
    """Frame ``i`` of the clip: painter's algorithm over flat-shaded quads, faces behind the camera clipped away."""
    w, h = int(width or spec.get("width", 1920)), int(height or spec.get("height", 1088))
    t = i / float(spec.get("fps", 24))
    pos, rot, fov = _camera(spec, t)
    f = (w / 2) / math.tan(math.radians(fov) / 2)
    img = Image.new("RGB", (w, h), SKY)
    dr = ImageDraw.Draw(img)
    drawn = []
    for k, (quad, grey) in enumerate(_faces(spec, t)):
        cam = (quad - pos) @ rot.T
        if (cam[:, 2] <= 0.05).any():
            cam = _clip_near(cam)
            if cam is None:
                continue
        n = np.cross(quad[1] - quad[0], quad[2] - quad[0])
        nn = np.linalg.norm(n)
        if nn == 0:
            continue
        n /= nn
        centre = quad.mean(axis=0)
        if np.dot(n, centre - pos) > 0:          # face turned away: flip (rooms are seen from inside, blocks from outside)
            n = -n
        shade = grey * (0.45 + 0.55 * max(0.0, float(np.dot(n, LIGHT))))
        pts = [(w / 2 + f * x / z, h / 2 - f * y / z) for x, y, z in cam]
        # the floor and back wall (the first two faces) always go first: their centroids lie close to the camera
        depth = math.inf if k < 2 else float(np.linalg.norm(centre - pos))
        drawn.append((depth, pts, int(min(255, shade))))
    for _, pts, g in sorted(drawn, key=lambda d: -d[0]):
        dr.polygon(pts, fill=(g, g, g), outline=(max(0, g - 40),) * 3)
    return img


def _clip_near(cam: np.ndarray, near: float = 0.05):
    """Sutherland-Hodgman against z = near; None when nothing is in front."""
    out = []
    for a, b in zip(cam, np.roll(cam, -1, axis=0)):
        ina, inb = a[2] > near, b[2] > near
        if ina:
            out.append(a)
        if ina != inb:
            k = (near - a[2]) / (b[2] - a[2])
            out.append(a + (b - a) * k)
    return np.array(out) if len(out) >= 3 else None


def render(spec: dict, out: Path, *, width: int | None = None, height: int | None = None, frames: int | None = None) -> dict:
    """The clip as H.264 mp4 (yuv420p, the spec's fps), exactly 8k+1 frames; returns its facts."""
    w, h = int(width or spec.get("width", 1920)), int(height or spec.get("height", 1088))
    problems = check_spec({**spec, "width": w, "height": h})          # the override is checked too, not only the spec's own size
    if problems:
        raise ValueError("; ".join(problems))
    n = snap_frames(frames) if frames else frame_count(spec)
    fps = int(spec.get("fps", 24))
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    ff = subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}", "-r", str(fps),
                           "-i", "-", "-frames:v", str(n), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
                           "-threads", "1", "-fflags", "+bitexact", "-flags:v", "+bitexact", "-map_metadata", "-1", str(tmp)],
                          stdin=subprocess.PIPE)
    try:
        for i in range(n):
            ff.stdin.write(render_frame(spec, i, w, h).tobytes())
    finally:
        ff.stdin.close()
        rc = ff.wait()
    if rc:
        raise RuntimeError(f"ffmpeg exited {rc}")
    tmp.replace(out)
    return {"id": spec.get("id"), "path": str(out), "frames": n, "fps": fps, "width": w, "height": h}


def load_spec(ref: str) -> dict:
    """``spec.json`` or ``shots.json#<id>``."""
    path, _, shot = ref.partition("#")
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if "shots" in doc:
        if shot not in doc["shots"]:
            raise SystemExit(f"{path}: name a shot with #<id>, one of {sorted(doc['shots'])}")
        return doc["shots"][shot]
    return doc


def main(argv: list[str]) -> int:
    if len(argv) < 3 or argv[0] not in ("render", "first"):
        print(__doc__)
        return 2
    spec = load_spec(argv[1])
    opts = {argv[i].lstrip("-"): int(argv[i + 1]) for i in range(3, len(argv) - 1, 2)}
    if argv[0] == "first":
        render_frame(spec, 0, opts.get("width"), opts.get("height")).save(argv[2])
        print(argv[2])
        return 0
    print(json.dumps(render(spec, Path(argv[2]), **opts)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
