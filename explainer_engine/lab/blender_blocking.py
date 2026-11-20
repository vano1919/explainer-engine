"""Blender grey-box blocking lab (lab only, never part of an episode run; final plan section 2).

Fixes the place, the camera (height, lens) and every person's position for a start/end frame pair, so a picture
model can copy the layout. Free: headless Blender (``bpy``) on the CPU, simple primitives, grey clay with a faint
floor grid. Nothing here is imported by the production pipeline.

Run (needs ``pip install bpy`` on Python 3.11, any CPU machine)::

    python -m explainer_engine.lab.blender_blocking <out_dir> [--only S04_SH008_start] [--size 1920x1080] [--samples 24]

Units are metres. World axes: +x right, +y away from the camera start, +z up. A heading is a compass angle in
degrees: 0 faces +y, 90 faces +x, -90 faces -x, 180 faces -y.
"""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

PERSON_HEIGHT = 1.75
LENSES_ALLOWED = (28, 35, 50)
SENSOR_WIDTH_MM = 36.0
ASPECT = 16 / 9

# One entry per shot: the place (built by ``PLACES[place]``), the camera, and for each frame the people and props.
# The people list keeps the same ids and the same positions in both frames unless the action moves them
# (``validate`` enforces that "everyone in the same spot" rule of the batch-2 prompt).
LAYOUTS: dict[str, dict] = {
    "S07_SH008": {
        "place": "british_trench",
        "camera": {"pos": [0.0, 0.0, 1.3], "heading": 0, "pitch": 0, "lens": 35},
        "people": {"private": {"side": "british"}},
        "frames": {
            "start": {"private": {"pos": [0.0, 3.6], "heading": -70, "pose": "stand"},
                      "props": {"rifle": "lean_left_wall"}},
            "end": {"private": {"pos": [-0.6, 3.6], "z": 0.4, "heading": -70, "pose": "rifle_chest"},
                    "props": {}},
        },
    },
    "S04_SH008": {
        "place": "no_mans_land",
        "camera": {"pos": [0.0, 0.0, 1.6], "heading": 0, "pitch": 0, "lens": 50},
        "people": {"private": {"side": "british"}, "german": {"side": "german"}},
        "frames": {
            "start": {"private": {"pos": [0.0, 6.0], "heading": 0, "pose": "stand"},
                      "german": {"pos": [0.0, 40.0], "heading": 180, "pose": "stand"}, "props": {}},
            "end": {"private": {"pos": [0.0, 16.0], "heading": 0, "pose": "stand"},
                    "german": {"pos": [0.0, 18.5], "heading": 180, "pose": "hands_open"}, "props": {}},
        },
    },
    "S07_SH006": {
        "place": "german_trench",
        "camera": {"pos": [-2.2, 0.0, 1.2], "heading": 25, "pitch": 10, "lens": 28},
        "people": {"officer": {"side": "german"}, "soldier_1": {"side": "german"},
                   "soldier_2": {"side": "german"}, "soldier_3": {"side": "german"}},
        "frames": {
            "start": {"officer": {"pos": [0.55, 4.0], "z": 0.4, "heading": 90, "pose": "stand"},
                      "soldier_1": {"pos": [-2.17, 2.0], "heading": 54, "pose": "stand"},
                      "soldier_2": {"pos": [-1.73, 2.96], "heading": 66, "pose": "stand"},
                      "soldier_3": {"pos": [-0.88, 4.3], "heading": 102, "pose": "stand"}, "props": {}},
            "end": {"officer": {"pos": [0.55, 4.0], "z": 0.4, "heading": 90, "pose": "arm_up"},
                    "soldier_1": {"pos": [-2.17, 2.0], "heading": 54, "pose": "stand"},
                    "soldier_2": {"pos": [-1.73, 2.96], "heading": 66, "pose": "stand"},
                    "soldier_3": {"pos": [-0.88, 4.3], "heading": 102, "pose": "stand"}, "props": {}},
        },
    },
}

STATIC_ID_FIELDS = ("heading", "side")   # only the pose (and an optional step height) may differ between start and end


def frame_names() -> list[str]:
    return [f"{shot}_{frame}" for shot in LAYOUTS for frame in ("start", "end")]


def validate(layouts: dict | None = None) -> list[str]:
    """Pure-Python checks; returns the problems (empty = fine)."""
    problems: list[str] = []
    for shot, spec in (layouts or LAYOUTS).items():
        cam = spec["camera"]
        if cam["lens"] not in LENSES_ALLOWED:
            problems.append(f"{shot}: lens {cam['lens']} not in {LENSES_ALLOWED}")
        if not 0.3 <= cam["pos"][2] <= 2.2:
            problems.append(f"{shot}: camera height {cam['pos'][2]} out of range")
        start, end = spec["frames"]["start"], spec["frames"]["end"]
        for pid in spec["people"]:
            if pid not in start or pid not in end:
                problems.append(f"{shot}: person {pid} missing in start or end")
                continue
            for field in STATIC_ID_FIELDS:
                if start[pid].get(field) != end[pid].get(field) and field == "heading" and pid in (
                        "soldier_1", "soldier_2", "soldier_3", "german", "officer"):
                    problems.append(f"{shot}: {pid} {field} changes between start and end")
        extra = set(start) ^ set(end)
        if extra - {"props"}:
            problems.append(f"{shot}: start and end list different people: {sorted(extra)}")
    return problems


def plan_view(shot: str, path: Path, size=(1000, 1000)) -> Path:
    """Top-down plan (PIL only): camera + view wedge, start people filled, end people outlined, arrows = heading."""
    from PIL import Image, ImageDraw  # noqa: PLC0415
    spec = LAYOUTS[shot]
    pts = [spec["camera"]["pos"][:2]] + [f["pos"] for fr in spec["frames"].values() for k, f in fr.items() if k != "props"]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    pad = 1.2
    x0, x1, y0, y1 = min(xs) - pad, max(xs) + pad, min(ys) - pad, max(ys) + pad
    scale = min((size[0] - 80) / (x1 - x0), (size[1] - 80) / (y1 - y0))

    def px(x, y):
        return 40 + (x - x0) * scale, size[1] - 40 - (y - y0) * scale
    img = Image.new("RGB", size, (245, 245, 242))
    d = ImageDraw.Draw(img)
    cam = spec["camera"]
    half = math.degrees(math.atan(SENSOR_WIDTH_MM / 2 / cam["lens"]))
    cx, cy = cam["pos"][:2]
    for sgn in (-1, 1):
        fx, fy = _heading_vec(cam["heading"] + sgn * half)
        d.line([px(cx, cy), px(cx + fx * (y1 - y0), cy + fy * (y1 - y0))], fill=(150, 150, 190), width=2)
    d.ellipse([px(cx, cy)[0] - 8, px(cx, cy)[1] - 8, px(cx, cy)[0] + 8, px(cx, cy)[1] + 8], fill=(40, 40, 160))
    d.text((px(cx, cy)[0] + 12, px(cx, cy)[1] - 6), f"camera {cam['lens']} mm, h {cam['pos'][2]} m", fill=(40, 40, 160))
    for frame, fill in (("start", True), ("end", False)):
        for pid in spec["people"]:
            f = spec["frames"][frame][pid]
            x, y = f["pos"]
            r = 0.22 * scale
            colour = (190, 150, 60) if spec["people"][pid]["side"] == "british" else (70, 110, 150)
            bx, by = px(x, y)
            d.ellipse([bx - r, by - r, bx + r, by + r], fill=colour if fill else None, outline=colour, width=3)
            hx, hy = _heading_vec(f["heading"])
            d.line([(bx, by), (bx + hx * r * 2.2, by - hy * r * 2.2)], fill=(200, 80, 20), width=3)
            if fill:
                d.text((bx + r + 4, by - 6), pid, fill=(60, 60, 60))
            if f.get("pose") not in (None, "stand") and not fill:
                d.text((bx + r + 4, by + 6), f"end: {f['pose']}", fill=(160, 60, 20))
    d.text((20, 14), f"{shot} plan view (top-down, y up the page). filled = start, ring = end, orange = heading",
           fill=(30, 30, 30))
    img.save(path)
    return path


# ----------------------------------------------------------------------------------------------- Blender part

def _bpy():
    import bpy  # noqa: PLC0415  (only the render path needs Blender)
    return bpy


def _mat(name: str, rgb: tuple[float, float, float], grid: bool = False):
    bpy = _bpy()
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bsdf = nt.nodes["Principled BSDF"]
    bsdf.inputs["Roughness"].default_value = 0.95
    if grid:
        geo = nt.nodes.new("ShaderNodeNewGeometry")
        sep = nt.nodes.new("ShaderNodeSeparateXYZ")
        nt.links.new(geo.outputs["Position"], sep.inputs[0])
        lines = []
        for axis in ("X", "Y"):
            mod = nt.nodes.new("ShaderNodeMath"); mod.operation = "PINGPONG"; mod.inputs[1].default_value = 1.0
            nt.links.new(sep.outputs[axis], mod.inputs[0])
            lt = nt.nodes.new("ShaderNodeMath"); lt.operation = "LESS_THAN"; lt.inputs[1].default_value = 0.025
            nt.links.new(mod.outputs[0], lt.inputs[0])
            lines.append(lt)
        add = nt.nodes.new("ShaderNodeMath"); add.operation = "ADD"; add.use_clamp = True
        nt.links.new(lines[0].outputs[0], add.inputs[0]); nt.links.new(lines[1].outputs[0], add.inputs[1])
        mix = nt.nodes.new("ShaderNodeMix"); mix.data_type = "RGBA"
        mix.inputs[6].default_value = (*rgb, 1)
        mix.inputs[7].default_value = (rgb[0] * 0.45, rgb[1] * 0.45, rgb[2] * 0.45, 1)
        nt.links.new(add.outputs[0], mix.inputs[0])
        nt.links.new(mix.outputs[2], bsdf.inputs["Base Color"])
    else:
        bsdf.inputs["Base Color"].default_value = (*rgb, 1)
    return m


def _box(name, centre, size, mat, rot=(0, 0, 0)):
    bpy = _bpy()
    bpy.ops.mesh.primitive_cube_add(size=1, location=centre, rotation=[math.radians(a) for a in rot])
    o = bpy.context.active_object
    o.name = name
    o.scale = size
    o.data.materials.append(mat)
    return o


def _cyl(name, centre, radius, depth, mat, rot=(0, 0, 0), verts=16):
    bpy = _bpy()
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=depth, vertices=verts, location=centre,
                                        rotation=[math.radians(a) for a in rot])
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def _cone(name, centre, r1, depth, mat, rot=(0, 0, 0)):
    bpy = _bpy()
    bpy.ops.mesh.primitive_cone_add(radius1=r1, radius2=0, depth=depth, vertices=16, location=centre,
                                    rotation=[math.radians(a) for a in rot])
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def _sphere(name, centre, radius, mat):
    bpy = _bpy()
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=centre, segments=24, ring_count=12)
    o = bpy.context.active_object
    o.name = name
    o.data.materials.append(mat)
    return o


def _fill_light(loc, watts, size=4.0):
    bpy = _bpy()
    bpy.ops.object.light_add(type="AREA", location=loc)
    light = bpy.context.active_object
    light.data.energy = watts
    light.data.size = size
    return light


def _heading_vec(h):
    return math.sin(math.radians(h)), math.cos(math.radians(h))


def _person(pid, side, spec, mats):
    """Capsule body 1.75 m tall (head marker included), a nose cone shows the facing, arms/props by pose."""
    bpy = _bpy()
    x, y = spec["pos"]
    z0 = spec.get("z", 0.0)
    h = spec["heading"]
    body_m = mats["british" if side == "british" else "german"]
    r = 0.18
    parts = []
    body_h = PERSON_HEIGHT - 0.24            # head sphere r=0.12 sits on top
    parts.append(_cyl(f"{pid}_body", (x, y, z0 + body_h / 2), r, body_h - 0.05, body_m))
    parts.append(_sphere(f"{pid}_shoulders", (x, y, z0 + body_h - 0.05), r, body_m))
    parts.append(_sphere(f"{pid}_feet_cap", (x, y, z0 + 0.0), r, body_m))
    head = _sphere(f"{pid}_head", (x, y, z0 + PERSON_HEIGHT - 0.12), 0.12, mats["head"])
    fx, fy = _heading_vec(h)
    nose = _cone(f"{pid}_facing", (x + fx * 0.15, y + fy * 0.15, z0 + PERSON_HEIGHT - 0.12), 0.05, 0.14, mats["marker"],
                 rot=(-90, 0, 0))
    nose.rotation_euler = (math.radians(-90), 0, math.radians(-h))
    nose.rotation_mode = "XYZ"
    # cone default axis is +z; rotate it to lie along the heading vector
    nose.rotation_euler = (math.radians(90), 0, math.radians(-h + 180))
    parts += [head, nose]
    pose = spec.get("pose", "stand")
    rx, ry = fy, -fx                          # the person's right-hand side
    if pose == "arm_up":
        sx, sy, sz = x + rx * 0.24, y + ry * 0.24, z0 + 1.42
        parts.append(_cyl(f"{pid}_arm_up", (sx, sy, sz + 0.38), 0.05, 0.8, body_m))
        parts.append(_box(f"{pid}_pistol", (sx, sy, sz + 0.86), (0.04, 0.2, 0.12), mats["prop"],
                          rot=(0, 0, -h)))
    elif pose == "rifle_chest":
        parts.append(_box(f"{pid}_rifle", (x + fx * 0.28, y + fy * 0.28, z0 + 1.2), (0.05, 0.05, 1.2), mats["prop"],
                          rot=(0, 25, -h)))
    elif pose == "hands_open":
        for sgn in (-1, 1):
            parts.append(_cyl(f"{pid}_hand_{sgn}", (x + rx * 0.3 * sgn, y + ry * 0.3 * sgn, z0 + 0.95), 0.045, 0.5,
                              body_m, rot=(0, 0, 0)))
    return parts


def _build_british_trench(mats):
    clay, ground = mats["clay"], mats["ground"]
    _box("floor", (0, 5, -0.05), (1.8, 14, 0.1), ground)
    for sgn in (-1, 1):                                                     # top ground, 2 m above the trench floor
        _box(f"outer_{sgn}", (sgn * 16, 40, 1.95), (28, 120, 0.1), ground)
    _box("left_wall", (-1.4, 5, 1.0), (1.0, 14, 2.0), clay)
    _box("left_sandbags", (-1.15, 5, 2.3), (0.9, 14, 0.7), clay)
    _box("right_wall", (1.4, 5, 1.0), (1.0, 14, 2.0), clay)
    _box("right_lip", (1.15, 5, 2.2), (0.5, 14, 0.4), clay)
    _box("fire_step", (-0.65, 6.2, 0.2), (0.5, 11.5, 0.4), clay)
    _box("dugout", (0.82, 6.0, 0.9), (0.15, 1.2, 1.8), mats["dark"])        # doorway recess marker, right wall
    _cyl("brazier", (0.5, 6.0, 0.3), 0.18, 0.6, mats["marker"])
    _fill_light((0, 4, 4.5), 500)
    for i, dz in enumerate((0.45, 0.9, 1.35, 1.8)):                         # ladder on the left wall at y=3.2
        _box(f"rung{i}", (-0.82, 3.2 - dz * 0.12, 0.2 + dz), (0.05, 0.5, 0.04), mats["prop"], rot=(0, 0, 0))
    for dy in (-0.25, 0.25):
        _box(f"ladder_rail{dy}", (-0.88, 3.2 + dy, 1.0), (0.05, 0.05, 2.2), mats["prop"], rot=(0, -8, 0))
    _box("traverse", (-0.3, 10.0, 1.0), (1.2, 1.2, 2.0), clay)               # sandbag traverse, gap on the right
    _box("parapet_wire_post", (-1.0, 9.0, 3.0), (0.06, 0.06, 1.0), mats["prop"])


def _build_no_mans_land(mats):
    clay, ground = mats["clay"], mats["ground"]
    _box("field", (0, 70, -0.05), (240, 260, 0.1), ground)
    lane = 1.6
    for side in (-1, 1):
        for row, off in enumerate((0.7, 2.4)):
            for k in range(2, 98, 3):
                x = side * (lane + off)
                for sgn in (-1, 1):
                    _cyl(f"stake{side}_{row}_{k}_{sgn}", (x, k, 0.6), 0.04, 1.4, mats["prop"], rot=(sgn * 28, 0, 0),
                         verts=6)
            _box(f"wire{side}_{row}", (side * (lane + off), 50, 0.9), (0.05, 96, 0.05), mats["prop"])
    _box("german_line", (0, 101, 0.6), (60, 1.6, 1.2), clay)
    for tx in (-5, -1.5, 4, 11, -12):
        _cone(f"fir{tx}", (tx, 101, 1.2 + 1.2), 0.6, 2.4, mats["clay"])
    _box("farmhouse", (22, 106, 2.5), (9, 6, 5), clay)
    _box("farm_chimney", (25, 106, 6.0), (0.9, 0.9, 2.5), clay)
    for px in (-60, -40, -18, 6, 30, 55):
        _cyl(f"poplar{px}", (px, 135, 6.0), 0.35, 12.0, clay)
        _sphere(f"poplar_top{px}", (px, 135, 11.0), 0.9, clay)
    for sx, sy in ((6.5, 22), (-7, 55), (9, 80)):
        _cyl(f"shellhole{sx}", (sx, sy, 0.01), 1.8, 0.04, mats["dark"], verts=24)


def _build_german_trench(mats):
    """Trench runs along +y. Front wall (enemy side) is on the RIGHT at x=+0.8, 1.5 m above the floor."""
    clay, ground = mats["clay"], mats["ground"]
    _box("floor", (-0.8, 5, -0.05), (3.2, 14, 0.1), ground)
    _box("back_wall", (-2.8, 5, 0.9), (1.0, 14, 1.8), clay)
    _box("fire_step", (0.55, 5, 0.2), (0.5, 14, 0.4), clay)
    _box("front_wall", (1.8, 5, 0.75), (2.0, 14, 1.5), clay)
    _box("front_sandbags", (1.3, 5, 1.62), (1.0, 14, 0.25), clay)
    _box("outside_ground", (12, 5, 1.45), (20, 40, 0.1), ground)
    _cyl("brazier", (-0.9, 3.0, 0.35), 0.17, 0.5, mats["marker"])
    _cone("fir", (1.6, 5.5, 1.75 + 1.1), 0.7, 2.2, mats["clay"])
    _box("fir_trunk", (1.6, 5.5, 1.85), (0.1, 0.1, 0.3), mats["prop"])
    _fill_light((0, 3, 4.0), 120)


PLACES = {"british_trench": _build_british_trench, "no_mans_land": _build_no_mans_land,
          "german_trench": _build_german_trench}


def build_scene(shot: str, frame: str, size=(1920, 1080), samples=24):
    """Clear the Blender file, build the shot's place, its people for ``frame`` and the camera; return the camera."""
    bpy = _bpy()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    spec = LAYOUTS[shot]
    mats = {
        "clay": _mat("clay", (0.62, 0.62, 0.60)),
        "ground": _mat("ground", (0.5, 0.5, 0.48), grid=True),
        "dark": _mat("dark", (0.18, 0.18, 0.18)),
        "prop": _mat("prop", (0.45, 0.40, 0.33)),
        "marker": _mat("marker", (0.9, 0.45, 0.1)),
        "head": _mat("head", (0.30, 0.30, 0.32)),
        "british": _mat("british", (0.70, 0.62, 0.42)),
        "german": _mat("german", (0.45, 0.52, 0.58)),
    }
    PLACES[spec["place"]](mats)
    data = spec["frames"][frame]
    for pid, meta in spec["people"].items():
        _person(pid, meta["side"], data[pid], mats)
    if data.get("props", {}).get("rifle") == "lean_left_wall":
        _box("rifle_leaning", (-0.8, 2.4, 0.55), (0.05, 0.05, 1.2), mats["prop"], rot=(0, -6, 0))
    # light and sky
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
    sun = bpy.context.active_object
    sun.data.energy = 0.7
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.82, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    bpy.context.scene.world = world
    # camera
    cam_spec = spec["camera"]
    cam_data = bpy.data.cameras.new("cam")
    cam_data.lens = cam_spec["lens"]
    cam_data.sensor_width = SENSOR_WIDTH_MM
    cam_data.sensor_fit = "HORIZONTAL"
    cam = bpy.data.objects.new("cam", cam_data)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = cam_spec["pos"]
    cam.rotation_euler = (math.radians(90 + cam_spec["pitch"]), 0, math.radians(-cam_spec["heading"]))
    sc = bpy.context.scene
    sc.camera = cam
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = size
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Standard"
    return cam


def measure(cam, shot: str, frame: str, size) -> dict:
    """Where every person lands in the picture: feet/head pixel, height in pixels, head height in pixels."""
    from bpy_extras.object_utils import world_to_camera_view  # noqa: PLC0415
    bpy = _bpy()
    sc = bpy.context.scene
    out = {}
    spec = LAYOUTS[shot]
    for pid in spec["people"]:
        body, head = bpy.data.objects[f"{pid}_body"], bpy.data.objects[f"{pid}_head"]
        z0 = spec["frames"][frame][pid].get("z", 0.0)
        x, y = spec["frames"][frame][pid]["pos"]
        feet = world_to_camera_view(sc, cam, __import__("mathutils").Vector((x, y, z0)))
        top = world_to_camera_view(sc, cam, __import__("mathutils").Vector((x, y, z0 + PERSON_HEIGHT)))
        out[pid] = {
            "feet_px": [round(feet.x * size[0]), round((1 - feet.y) * size[1])],
            "height_px": round(abs(feet.y - top.y) * size[1]),
            "head_px": round(abs(feet.y - top.y) * size[1] * 0.24 / PERSON_HEIGHT),
            "in_frame": bool(0 <= feet.x <= 1 and 0 <= top.y <= 1 and feet.z > 0),
        }
        del body, head
    return out


def render(out_dir: Path, only: list[str] | None = None, size=(1920, 1080), samples=24, save_blend=True) -> dict:
    bpy = _bpy()
    out_dir.mkdir(parents=True, exist_ok=True)
    report = {}
    for shot in LAYOUTS:
        for frame in ("start", "end"):
            name = f"{shot}_{frame}"
            if only and name not in only:
                continue
            cam = build_scene(shot, frame, size, samples)
            bpy.context.scene.render.filepath = str(out_dir / f"{name}_blocking.png")
            bpy.ops.render.render(write_still=True)
            report[name] = {"lens_mm": LAYOUTS[shot]["camera"]["lens"], "camera_height_m": LAYOUTS[shot]["camera"]["pos"][2],
                            "people": measure(cam, shot, frame, size)}
            if save_blend:
                bpy.ops.wm.save_as_mainfile(filepath=str(out_dir / f"{name}.blend"))
    for shot in LAYOUTS:
        plan_view(shot, out_dir / f"{shot}_plan.png")
    (out_dir / "blocking_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main(argv: list[str]) -> int:
    if not argv:
        print(__doc__)
        return 2
    out = Path(argv[0])
    only, size, samples = None, (1920, 1080), 24
    it = iter(argv[1:])
    for a in it:
        if a == "--only":
            only = next(it).split(",")
        elif a == "--size":
            w, h = next(it).lower().split("x")
            size = (int(w), int(h))
        elif a == "--samples":
            samples = int(next(it))
    problems = validate()
    if problems:
        print("\n".join(problems))
        return 1
    print(json.dumps(render(out, only, size, samples), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
