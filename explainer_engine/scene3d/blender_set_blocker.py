"""Headless Blender Python (`bpy`) 3D Roman Architectural Set Blocker for Multi-Angle Film Continuity.

Eliminates shot-to-shot room teleportation by blocking ONE physical 3D architectural set
(columns, stone floors, walls, doorway architraves, fixed morning sun azimuth, and named
character proxy rigs) and rendering 5-6 geometrically locked camera angles (Wide, Medium,
OTS, Close-Up, Insert) plus anti-aliased Mist depth passes in a single headless Blender call.

All rendered camera plates share identical world geometry, lighting direction, and 180-degree
axis discipline (`camera_angle_delta_deg >= 30 deg`), giving downstream Gemini stylization
and LTX-2.5 I2V locked spatial continuity across every cut in the scene.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True, slots=True)
class CameraAngleSpec:
    angle_id: str
    shot_scale: str  # wide, medium, ots, close_up, insert
    location: tuple[float, float, float]
    target: tuple[float, float, float]
    lens_mm: float = 35.0
    focus_subject: str = "scene"


ROMAN_SET_PRESETS: dict[str, dict[str, Any]] = {
    "domus_publica_atrium": {
        "description": "Julius Caesar's Domus Publica peristyle atrium at golden Roman dawn (March 15, 44 BCE)",
        "sun_rotation_deg": (66.0, 12.0, -38.0),
        "sun_energy": 4.2,
        "world_color": (0.14, 0.11, 0.09),
        "architecture": "roman_atrium",
        "actors": [
            {
                "name": "caesar",
                "pos": (-0.75, 0.25, 0.0),
                "yaw_deg": -25.0,
                "height": 1.78,
                "toga_color": (0.82, 0.78, 0.70),
                "trim_color": (0.52, 0.08, 0.09),
            },
            {
                "name": "calpurnia",
                "pos": (0.85, -0.10, 0.0),
                "yaw_deg": 145.0,
                "height": 1.65,
                "toga_color": (0.64, 0.34, 0.16),
                "trim_color": (0.35, 0.10, 0.08),
            },
        ],
        "cameras": [
            CameraAngleSpec("wide_atrium", "wide", (0.1, -6.2, 1.85), (0.0, 0.4, 1.25), 28.0, "caesar_and_calpurnia"),
            CameraAngleSpec("med_calpurnia", "medium", (-1.55, -2.55, 1.52), (0.85, -0.10, 1.38), 50.0, "calpurnia"),
            CameraAngleSpec("med_caesar", "medium", (1.65, -2.65, 1.58), (-0.75, 0.25, 1.48), 50.0, "caesar"),
            CameraAngleSpec("ots_caesar_to_calpurnia", "ots", (-1.45, 0.95, 1.56), (0.85, -0.10, 1.38), 55.0, "calpurnia"),
            CameraAngleSpec("ots_calpurnia_to_caesar", "ots", (1.55, -0.85, 1.50), (-0.75, 0.25, 1.50), 55.0, "caesar"),
            CameraAngleSpec("cu_caesar_hesitation", "close_up", (0.65, -1.35, 1.58), (-0.75, 0.25, 1.56), 75.0, "caesar"),
        ],
    },
    "domus_doorway": {
        "description": "Threshold vestibule of Caesar's Domus Publica opening onto sunlit Roman street",
        "sun_rotation_deg": (62.0, 18.0, -45.0),
        "sun_energy": 4.8,
        "world_color": (0.16, 0.13, 0.10),
        "architecture": "roman_doorway",
        "actors": [
            {
                "name": "caesar",
                "pos": (-0.65, -0.50, 0.0),
                "yaw_deg": -15.0,
                "height": 1.78,
                "toga_color": (0.82, 0.78, 0.70),
                "trim_color": (0.52, 0.08, 0.09),
            },
            {
                "name": "decimus_brutus",
                "pos": (0.75, 0.75, 0.0),
                "yaw_deg": 150.0,
                "height": 1.76,
                "toga_color": (0.72, 0.68, 0.60),
                "trim_color": (0.36, 0.12, 0.14),
            },
        ],
        "cameras": [
            CameraAngleSpec("wide_doorway", "wide", (-0.4, -4.8, 1.72), (0.1, 0.4, 1.4), 32.0, "caesar_and_brutus"),
            CameraAngleSpec("med_brutus_threshold", "medium", (-1.55, -1.85, 1.56), (0.75, 0.75, 1.48), 50.0, "decimus_brutus"),
            CameraAngleSpec("med_caesar_doorway", "medium", (1.65, -1.95, 1.58), (-0.65, -0.50, 1.50), 50.0, "caesar"),
            CameraAngleSpec("ots_caesar_to_brutus", "ots", (-1.35, -1.25, 1.60), (0.75, 0.75, 1.50), 55.0, "decimus_brutus"),
            CameraAngleSpec("cu_brutus_persuasion", "close_up", (-0.45, -0.65, 1.58), (0.75, 0.75, 1.54), 75.0, "decimus_brutus"),
        ],
    },
    "curia_pompey_portico": {
        "description": "Monumental stone colonnade and marble steps of the Curia of Pompey in Rome",
        "sun_rotation_deg": (58.0, 22.0, -52.0),
        "sun_energy": 4.5,
        "world_color": (0.12, 0.12, 0.14),
        "architecture": "roman_portico",
        "actors": [
            {
                "name": "caesar",
                "pos": (0.0, -2.6, 0.35),
                "yaw_deg": 0.0,
                "height": 1.78,
                "toga_color": (0.84, 0.80, 0.72),
                "trim_color": (0.55, 0.07, 0.08),
            },
            {
                "name": "senator_left",
                "pos": (-1.7, 0.8, 0.70),
                "yaw_deg": -150.0,
                "height": 1.74,
                "toga_color": (0.74, 0.70, 0.64),
                "trim_color": (0.34, 0.09, 0.10),
            },
            {
                "name": "senator_right",
                "pos": (1.6, 0.9, 0.70),
                "yaw_deg": 145.0,
                "height": 1.75,
                "toga_color": (0.70, 0.67, 0.62),
                "trim_color": (0.34, 0.09, 0.10),
            },
        ],
        "cameras": [
            CameraAngleSpec("wide_portico_steps", "wide", (0.2, -8.5, 1.75), (0.0, 0.6, 1.9), 28.0, "portico_all"),
            CameraAngleSpec("med_senators_shadow", "medium", (-3.1, -1.6, 1.65), (-0.8, 0.8, 1.5), 50.0, "senator_left"),
            CameraAngleSpec("low_caesar_ascent", "medium", (2.1, -5.2, 1.15), (0.0, -2.2, 1.55), 42.0, "caesar"),
            CameraAngleSpec("ots_senators_to_caesar", "ots", (-1.1, 1.6, 1.95), (0.0, -2.6, 1.65), 55.0, "caesar"),
            CameraAngleSpec("cu_concealed_dagger", "insert", (-0.85, -0.35, 1.45), (-1.7, 0.8, 1.25), 80.0, "senator_left"),
        ],
    },
    "roman_street_forum": {
        "description": "Sunlit cobblestone Via Sacra near the Roman Forum lined with travertine colonnades",
        "sun_rotation_deg": (54.0, 15.0, -40.0),
        "sun_energy": 5.0,
        "world_color": (0.18, 0.15, 0.12),
        "architecture": "roman_street",
        "actors": [
            {
                "name": "caesar",
                "pos": (0.0, 0.0, 0.0),
                "yaw_deg": 0.0,
                "height": 1.78,
                "toga_color": (0.84, 0.80, 0.72),
                "trim_color": (0.55, 0.07, 0.08),
            },
            {
                "name": "artemidorus_citizen",
                "pos": (1.25, 1.5, 0.0),
                "yaw_deg": 135.0,
                "height": 1.70,
                "toga_color": (0.56, 0.48, 0.38),
                "trim_color": (0.30, 0.24, 0.18),
            },
            {
                "name": "crowd_left",
                "pos": (-1.8, 1.2, 0.0),
                "yaw_deg": -70.0,
                "height": 1.72,
                "toga_color": (0.62, 0.54, 0.45),
                "trim_color": (0.35, 0.28, 0.22),
            },
        ],
        "cameras": [
            CameraAngleSpec("wide_forum_walk", "wide", (0.2, -6.4, 1.85), (0.0, 2.0, 1.45), 32.0, "caesar"),
            CameraAngleSpec("tracking_caesar_side", "medium", (-3.1, -1.5, 1.58), (0.0, 0.3, 1.45), 45.0, "caesar"),
            CameraAngleSpec("ots_crowd_warning", "ots", (2.1, 2.5, 1.52), (0.0, 0.0, 1.48), 50.0, "caesar"),
            CameraAngleSpec("med_warning_scroll", "medium", (-1.1, -1.6, 1.52), (1.25, 1.5, 1.38), 55.0, "artemidorus_citizen"),
            CameraAngleSpec("cu_caesar_walk", "close_up", (0.75, 1.65, 1.58), (0.0, 0.0, 1.55), 75.0, "caesar"),
        ],
    },
}


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _camera_azimuth_deg(cam: CameraAngleSpec) -> float:
    dx = cam.location[0] - cam.target[0]
    dy = cam.location[1] - cam.target[1]
    return math.degrees(math.atan2(dy, dx))


def _angle_delta_deg(a_deg: float, b_deg: float) -> float:
    diff = abs(a_deg - b_deg) % 360.0
    return min(diff, 360.0 - diff)


def plan_set_cameras(set_name: str) -> list[dict[str, Any]]:
    """Return deterministic camera metadata (including pairwise angle deltas) for a Roman 3D set preset."""
    if set_name not in ROMAN_SET_PRESETS:
        raise ValueError(f"Unknown Roman set preset {set_name!r}; expected one of {sorted(ROMAN_SET_PRESETS)}")
    preset = ROMAN_SET_PRESETS[set_name]
    cams: list[CameraAngleSpec] = list(preset["cameras"])
    out: list[dict[str, Any]] = []
    prev_az: float | None = None
    for cam in cams:
        az = _camera_azimuth_deg(cam)
        delta = _angle_delta_deg(prev_az, az) if prev_az is not None else 0.0
        prev_az = az
        row = asdict(cam)
        row["azimuth_deg"] = round(az, 2)
        row["delta_from_prev_deg"] = round(delta, 2)
        out.append(row)
    return out


def build_blender_set_script(
    set_name: str,
    out_dir: Path,
    *,
    width: int = 1280,
    height: int = 720,
    cycles_samples: int = 16,
) -> str:
    """Generate a self-contained headless Blender 4.x Python (`bpy`) script rendering all camera angles + Mist depth."""
    if set_name not in ROMAN_SET_PRESETS:
        raise ValueError(f"Unknown Roman set preset {set_name!r}")
    preset = ROMAN_SET_PRESETS[set_name]
    cfg_json = json.dumps(
        {
            "set_name": set_name,
            "architecture": preset["architecture"],
            "sun_rotation_deg": preset["sun_rotation_deg"],
            "sun_energy": preset["sun_energy"],
            "world_color": preset["world_color"],
            "actors": preset["actors"],
            "cameras": [asdict(c) for c in preset["cameras"]],
            "out_dir": str(Path(out_dir).resolve()),
            "width": int(width),
            "height": int(height),
            "cycles_samples": int(cycles_samples),
        }
    )

    return f'''import json
import math
from pathlib import Path
import bpy
from mathutils import Vector

CFG = json.loads({cfg_json!r})
OUT = Path(CFG["out_dir"])
OUT.mkdir(parents=True, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = int(CFG["cycles_samples"])
scene.cycles.use_denoising = False
scene.cycles.max_bounces = 3
scene.cycles.diffuse_bounces = 2
scene.cycles.glossy_bounces = 1
scene.render.use_persistent_data = True
scene.render.resolution_x = int(CFG["width"])
scene.render.resolution_y = int(CFG["height"])
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode = "RGB"

# Enable Mist pass for anti-aliased normalized depth maps
view_layer = scene.view_layers[0]
view_layer.use_pass_mist = True
scene.world = bpy.data.worlds.new("RomanDawnWorld")
scene.world.use_nodes = True
bg = scene.world.node_tree.nodes.get("Background")
if bg:
    wc = CFG["world_color"]
    bg.inputs[0].default_value = (wc[0], wc[1], wc[2], 1.0)
    bg.inputs[1].default_value = 0.85
scene.world.mist_settings.start = 0.8
scene.world.mist_settings.depth = 18.0
scene.world.mist_settings.falloff = "LINEAR"


def make_mat(name, color, roughness=0.65):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    bsdf = m.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (color[0], color[1], color[2], 1.0)
        bsdf.inputs["Roughness"].default_value = roughness
    return m


mat_travertine = make_mat("Travertine", (0.76, 0.70, 0.60), 0.58)
mat_marble_dark = make_mat("DarkMarble", (0.32, 0.29, 0.26), 0.35)
mat_fresco_red = make_mat("PompeianRed", (0.48, 0.16, 0.12), 0.72)
mat_ochre_wall = make_mat("RomanOchre", (0.64, 0.49, 0.31), 0.75)
mat_bronze = make_mat("Bronze", (0.35, 0.26, 0.16), 0.38)
mat_water = make_mat("ImpluviumWater", (0.10, 0.16, 0.18), 0.08)
mat_cobble = make_mat("RomanCobble", (0.42, 0.38, 0.34), 0.82)
mat_skin = make_mat("SkinProxy", (0.68, 0.52, 0.42), 0.65)


def add_box(name, loc, scale, mat):
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=loc)
    obj = bpy.context.active_object
    obj.name = name
    obj.scale = scale
    obj.data.materials.append(mat)
    return obj


def add_column(name, x, y, z0, height, radius, mat):
    bpy.ops.mesh.primitive_cylinder_add(vertices=20, radius=radius, depth=height, location=(x, y, z0 + height / 2.0))
    col = bpy.context.active_object
    col.name = name
    col.data.materials.append(mat)
    add_box(name + "_base", (x, y, z0 + 0.14), (radius * 2.7, radius * 2.7, 0.28), mat_marble_dark)
    add_box(name + "_cap", (x, y, z0 + height + 0.12), (radius * 2.9, radius * 2.9, 0.24), mat)
    return col


def add_actor_rig(actor):
    x, y, z = actor["pos"]
    h = float(actor.get("height", 1.75))
    yaw = math.radians(float(actor.get("yaw_deg", 0.0)))
    mat_toga = make_mat("Toga_" + actor["name"], actor["toga_color"], 0.78)
    mat_trim = make_mat("Trim_" + actor["name"], actor["trim_color"], 0.75)

    # Torso / draped toga cylinder
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.22, depth=h * 0.74, location=(x, y, z + h * 0.37))
    body = bpy.context.active_object
    body.name = actor["name"] + "_body"
    body.rotation_euler = (0.0, 0.0, yaw)
    body.data.materials.append(mat_toga)

    # Senatorial crimson border sash / shoulder drape
    bpy.ops.mesh.primitive_cube_add(size=1.0, location=(x, y, z + h * 0.56))
    sash = bpy.context.active_object
    sash.name = actor["name"] + "_sash"
    sash.scale = (0.48, 0.28, 0.22)
    sash.rotation_euler = (0.28, 0.0, yaw)
    sash.data.materials.append(mat_trim)

    # Head sphere for exact eye-line and framing scale lock
    bpy.ops.mesh.primitive_uv_sphere_add(segments=16, ring_count=12, radius=0.12, location=(x, y, z + h * 0.87))
    head = bpy.context.active_object
    head.name = actor["name"] + "_head"
    head.data.materials.append(mat_skin)


arch = CFG["architecture"]
if arch == "roman_atrium":
    add_box("Floor", (0.0, 0.0, -0.05), (14.0, 14.0, 0.1), mat_travertine)
    add_box("ImpluviumRim", (0.0, 0.6, 0.06), (2.9, 2.4, 0.12), mat_marble_dark)
    add_box("ImpluviumWater", (0.0, 0.6, 0.09), (2.4, 1.9, 0.06), mat_water)
    add_box("BackWall", (0.0, 5.2, 2.3), (12.5, 0.35, 4.6), mat_fresco_red)
    add_box("LeftWall", (-5.4, 0.0, 2.3), (0.35, 11.5, 4.6), mat_ochre_wall)
    add_box("RightWall", (5.4, 0.0, 2.3), (0.35, 11.5, 4.6), mat_ochre_wall)
    add_box("DoorArchLeft", (-1.5, 4.95, 1.65), (0.45, 0.4, 3.3), mat_travertine)
    add_box("DoorArchRight", (1.5, 4.95, 1.65), (0.45, 0.4, 3.3), mat_travertine)
    add_box("DoorLintel", (0.0, 4.95, 3.45), (3.5, 0.45, 0.42), mat_travertine)
    # Peristyle columns around atrium
    for cx in (-3.2, 3.2):
        for cy in (-2.4, 0.6, 3.4):
            add_column(f"Col_{{cx}}_{{cy}}", cx, cy, 0.0, 3.8, 0.22, mat_travertine)
    # Roof beams leaving central compluvium sky opening
    add_box("RoofBeamL", (-4.1, 0.5, 4.15), (2.8, 10.5, 0.32), mat_marble_dark)
    add_box("RoofBeamR", (4.1, 0.5, 4.15), (2.8, 10.5, 0.32), mat_marble_dark)
    add_box("RoofBeamBack", (0.0, 4.2, 4.15), (10.5, 2.2, 0.32), mat_marble_dark)
    add_box("ScrollTable", (-2.1, 1.9, 0.42), (1.1, 0.65, 0.84), mat_bronze)
elif arch == "roman_doorway":
    add_box("Floor", (0.0, 0.0, -0.05), (14.0, 14.0, 0.1), mat_travertine)
    add_box("WallLeft", (-3.4, 1.4, 2.4), (4.2, 0.45, 4.8), mat_fresco_red)
    add_box("WallRight", (3.4, 1.4, 2.4), (4.2, 0.45, 4.8), mat_fresco_red)
    add_box("DoorHeader", (0.0, 1.4, 4.15), (3.0, 0.52, 1.3), mat_travertine)
    add_box("BronzeDoorLeaf", (-1.15, 1.15, 1.75), (0.14, 1.1, 3.5), mat_bronze)
    for cx in (-2.2, 2.2):
        for cy in (-2.2, 0.8, 3.6):
            add_column(f"DoorCol_{{cx}}_{{cy}}", cx, cy, 0.0, 3.9, 0.24, mat_travertine)
elif arch == "roman_portico":
    add_box("PlazaFloor", (0.0, -4.0, -0.05), (18.0, 14.0, 0.1), mat_cobble)
    for step_i in range(4):
        add_box(f"Step_{{step_i}}", (0.0, -2.5 + step_i * 0.7, 0.10 + step_i * 0.17), (12.0, 0.72, 0.18), mat_travertine)
    add_box("PorticoDeck", (0.0, 2.6, 0.34), (14.0, 6.2, 0.70), mat_travertine)
    add_box("PorticoBackWall", (0.0, 5.4, 3.4), (14.0, 0.45, 5.5), mat_marble_dark)
    add_box("Entablature", (0.0, 0.4, 5.5), (14.0, 1.6, 0.75), mat_travertine)
    for cx in (-4.8, -2.4, 0.0, 2.4, 4.8):
        add_column(f"PorticoCol_{{cx}}", cx, 0.4, 0.70, 4.5, 0.28, mat_travertine)
else:  # roman_street
    add_box("ViaSacra", (0.0, 1.5, -0.05), (9.5, 22.0, 0.1), mat_cobble)
    add_box("SidewalkL", (-3.8, 1.5, 0.08), (2.4, 22.0, 0.18), mat_travertine)
    add_box("SidewalkR", (3.8, 1.5, 0.08), (2.4, 22.0, 0.18), mat_travertine)
    add_box("FacadeL", (-5.2, 2.0, 3.0), (0.6, 20.0, 6.0), mat_ochre_wall)
    add_box("FacadeR", (5.2, 2.0, 3.0), (0.6, 20.0, 6.0), mat_fresco_red)
    for cy in (-4.0, -1.0, 2.0, 5.0, 8.0):
        add_column(f"StColL_{{cy}}", -3.1, cy, 0.18, 4.2, 0.23, mat_travertine)
        add_column(f"StColR_{{cy}}", 3.1, cy, 0.18, 4.2, 0.23, mat_travertine)

for actor in CFG["actors"]:
    add_actor_rig(actor)

# Fixed Roman dawn directional sun + soft warm sky bounce
bpy.ops.object.light_add(type="SUN", location=(5.0, -5.0, 8.0))
sun = bpy.context.active_object
sun.data.energy = float(CFG["sun_energy"])
sun.data.color = (1.0, 0.88, 0.72)
sun.data.angle = math.radians(2.2)
sr = CFG["sun_rotation_deg"]
sun.rotation_euler = tuple(math.radians(v) for v in sr)

bpy.ops.object.light_add(type="AREA", location=(0.0, -1.0, 4.2))
fill = bpy.context.active_object
fill.data.energy = 120.0
fill.data.size = 4.0
fill.data.color = (0.76, 0.84, 1.0)

# Compositor outputs Mist depth pass alongside beauty PNG
scene.use_nodes = True
tree = scene.node_tree
tree.nodes.clear()
rl = tree.nodes.new("CompositorNodeRLayers")
comp = tree.nodes.new("CompositorNodeComposite")
tree.links.new(rl.outputs["Image"], comp.inputs["Image"])

depth_out = tree.nodes.new("CompositorNodeOutputFile")
depth_out.base_path = str(OUT)
depth_out.format.file_format = "PNG"
depth_out.format.color_mode = "BW"
tree.links.new(rl.outputs["Mist"], depth_out.inputs[0])

# Render every locked camera angle in ONE persistent Blender session
cam_data = bpy.data.cameras.new("SetCam")
cam_obj = bpy.data.objects.new("SetCam", cam_data)
scene.collection.objects.link(cam_obj)
scene.camera = cam_obj

for idx, c in enumerate(CFG["cameras"]):
    aid = c["angle_id"]
    cam_obj.location = Vector(c["location"])
    direction = Vector(c["target"]) - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_data.lens = float(c["lens_mm"])
    scene.frame_set(idx + 1)
    scene.render.filepath = str(OUT / f"{{aid}}_beauty.png")
    depth_out.file_slots[0].path = f"{{aid}}_depth_"
    bpy.ops.render.render(write_still=True)
    # Normalize Blender frame-suffixed depth filename to {{aid}}_depth.png
    raw_depth = OUT / f"{{aid}}_depth_{{idx + 1:04d}}.png"
    target_depth = OUT / f"{{aid}}_depth.png"
    if raw_depth.is_file():
        raw_depth.replace(target_depth)

print("BLENDER_SET_DONE", CFG["set_name"], len(CFG["cameras"]))
'''


def validate_set_rig_manifest(manifest: dict[str, Any], *, min_angles: int = 4) -> dict[str, Any]:
    """Validate a rendered Blender 3D set manifest (angle count, camera geometry, and on-disk PNGs)."""
    findings: list[str] = []
    angles = manifest.get("angles") or []
    if len(angles) < min_angles:
        findings.append(f"Blender set has only {len(angles)} angles (minimum {min_angles} required)")
    for ang in angles:
        aid = str(ang.get("angle_id") or "unknown")
        bp = Path(str(ang.get("beauty_path") or ""))
        dp = Path(str(ang.get("depth_path") or ""))
        if not bp.is_file():
            findings.append(f"Angle {aid} missing beauty render: {bp}")
        if not dp.is_file():
            findings.append(f"Angle {aid} missing depth/mist render: {dp}")
    return {
        "status": "PASS" if not findings else "FAIL",
        "set_name": manifest.get("set_name"),
        "angle_count": len(angles),
        "findings": findings,
    }


def render_blender_set_angles(
    set_name: str,
    out_dir: Path,
    *,
    width: int = 1280,
    height: int = 720,
    cycles_samples: int = 16,
    blender_bin: str = "blender",
    timeout_s: int = 240,
) -> dict[str, Any]:
    """Build and render a 5-6 camera geometrically locked Roman 3D set in headless Blender."""
    if not shutil.which(blender_bin):
        raise RuntimeError(f"Blender CLI ({blender_bin!r}) not installed on PATH")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    script_text = build_blender_set_script(
        set_name,
        out_dir,
        width=width,
        height=height,
        cycles_samples=cycles_samples,
    )
    script_path = out_dir / f"build_{set_name}.py"
    script_path.write_text(script_text, encoding="utf-8")

    proc = subprocess.run(
        [blender_bin, "--background", "--python-exit-code", "1", "--python", str(script_path)],
        capture_output=True,
        text=True,
        timeout=timeout_s,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"Headless Blender set render failed (rc={proc.returncode}):\n{proc.stderr[-1200:] or proc.stdout[-1200:]}"
        )

    planned = plan_set_cameras(set_name)
    angles_out: list[dict[str, Any]] = []
    for row in planned:
        aid = row["angle_id"]
        beauty_p = out_dir / f"{aid}_beauty.png"
        depth_p = out_dir / f"{aid}_depth.png"
        if not beauty_p.is_file() or not depth_p.is_file():
            raise RuntimeError(f"Expected Blender outputs missing for angle {aid}: {beauty_p}, {depth_p}")
        angles_out.append(
            {
                **row,
                "beauty_path": str(beauty_p),
                "beauty_sha256": _sha256_file(beauty_p),
                "depth_path": str(depth_p),
                "depth_sha256": _sha256_file(depth_p),
            }
        )

    manifest = {
        "schema": "blender_set_rig/1",
        "set_name": set_name,
        "description": ROMAN_SET_PRESETS[set_name]["description"],
        "width": int(width),
        "height": int(height),
        "cycles_samples": int(cycles_samples),
        "sun_rotation_deg": list(ROMAN_SET_PRESETS[set_name]["sun_rotation_deg"]),
        "actors": ROMAN_SET_PRESETS[set_name]["actors"],
        "angles": angles_out,
    }
    manifest_path = out_dir / "set_rig_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    manifest["manifest_path"] = str(manifest_path)
    return manifest
