"""Blender library for blender_scene/1 clips: places, capsule people with animated tracks, cameras bound to cuts.

Builds on the three places and the capsule figure of ``blender_blocking`` (lab only, never part of an episode run).
Needs ``bpy`` (run inside ``blender --background --python`` or with ``pip install bpy``); the spec side
(``scene_spec``) does not.
"""

from __future__ import annotations

import math

from explainer_engine.lab import blender_blocking as bb
from explainer_engine.lab import scene_spec as ss

POSES = ("stand", "arm_up", "rifle_chest", "hands_open")


def place_names() -> tuple[str, ...]:
    return tuple(bb.PLACES)


def make_materials() -> dict:
    return {
        "clay": bb._mat("clay", (0.62, 0.62, 0.60)),
        "ground": bb._mat("ground", (0.5, 0.5, 0.48), grid=True),
        "dark": bb._mat("dark", (0.18, 0.18, 0.18)),
        "prop": bb._mat("prop", (0.45, 0.40, 0.33)),
        "marker": bb._mat("marker", (0.9, 0.45, 0.1)),
        "head": bb._mat("head", (0.30, 0.30, 0.32)),
        "british": bb._mat("british", (0.70, 0.62, 0.42)),
        "german": bb._mat("german", (0.45, 0.52, 0.58)),
    }


def add_person(person: dict, mats: dict, last_frame: int):
    """One empty carries the track; each pose the person uses is a child group shown only while that pose holds."""
    bpy = bb._bpy()
    pid = person["id"]
    empty = bpy.data.objects.new(f"{pid}_root", None)
    bpy.context.scene.collection.objects.link(empty)
    keys = sorted(person["track"], key=lambda k: k["frame"])
    poses = []
    for k in keys:
        pose = k.get("pose", "stand")
        if pose not in poses:
            poses.append(pose)
    groups: dict[str, list] = {}
    for pose in poses:
        before = set(bpy.data.objects)
        parts = bb._person(f"{pid}__{pose}", person["side"], {"pos": [0.0, 0.0], "heading": 0, "pose": pose, "z": 0.0},
                           mats)
        parts += [o for o in bpy.data.objects if o not in before and o not in parts]
        for o in set(parts):
            o.parent = empty
        groups[pose] = list(set(parts))
        for o in groups[pose]:                                           # find the head/body by name for measuring
            if o.name.endswith("_body"):
                o["person_id"] = pid
    for k in keys:
        f = k["frame"]
        st = ss.person_state(person, f)
        empty.location = (st["pos"][0], st["pos"][1], st["z"])
        empty.rotation_euler = (0.0, 0.0, math.radians(-st["heading"]))
        empty.keyframe_insert("location", frame=f)
        empty.keyframe_insert("rotation_euler", frame=f)
        for pose, objs in groups.items():
            show = st["pose"] == pose
            for o in objs:
                o.hide_render = not show
                o.hide_viewport = not show
                o.keyframe_insert("hide_render", frame=f)
                o.keyframe_insert("hide_viewport", frame=f)
    if keys[-1]["frame"] < last_frame:
        empty.keyframe_insert("location", frame=last_frame)
        empty.keyframe_insert("rotation_euler", frame=last_frame)
    _constant_for_hides(groups)
    if empty.animation_data and empty.animation_data.action:
        for fc in empty.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return empty


def _constant_for_hides(groups: dict) -> None:
    for objs in groups.values():
        for o in objs:
            ad = o.animation_data
            if ad and ad.action:
                for fc in ad.action.fcurves:
                    if fc.data_path in ("hide_render", "hide_viewport"):
                        for kp in fc.keyframe_points:
                            kp.interpolation = "CONSTANT"


def add_cameras(spec: dict):
    """One camera object per spec camera; a timeline marker bound to it switches cameras at every cut."""
    bpy = bb._bpy()
    sc = bpy.context.scene
    objs = {}
    for cam in spec["cameras"]:
        data = bpy.data.cameras.new(cam["id"])
        data.lens = cam["lens"]
        data.sensor_width = ss.SENSOR_WIDTH_MM
        data.sensor_fit = "HORIZONTAL"
        obj = bpy.data.objects.new(cam["id"], data)
        sc.collection.objects.link(obj)
        objs[cam["id"]] = obj
    for cut in spec["cuts"]:
        obj = objs[cut["camera"]]
        for fr in (cut["frame_in"], cut["frame_out"]):
            st = ss.camera_state(spec, cut, fr)
            obj.location = st["pos"]
            obj.rotation_euler = (math.radians(90 + st["pitch"]), 0, math.radians(-st["heading"]))
            obj.keyframe_insert("location", frame=fr)
            obj.keyframe_insert("rotation_euler", frame=fr)
        marker = sc.timeline_markers.new(f"cut_{cut['frame_in']}", frame=cut["frame_in"])
        marker.camera = obj
    for obj in objs.values():
        ad = obj.animation_data
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"
    sc.camera = objs[spec["cuts"][0]["camera"]]
    return objs


def build_scene(spec: dict, samples: int = 8):
    """Clear the Blender file and build place + people + cameras + lights for the whole clip."""
    bpy = bb._bpy()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mats = make_materials()
    bb.PLACES[spec["place"]](mats)
    last = spec["clip_frames"] - 1
    for person in spec["people"]:
        add_person(person, mats, last)
    bpy.ops.object.light_add(type="SUN", location=(10, -10, 20))
    sun = bpy.context.active_object
    sun.data.energy = 0.7
    sun.rotation_euler = (math.radians(50), math.radians(10), math.radians(35))
    world = bpy.data.worlds.new("w")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.8, 0.82, 0.85, 1)
    world.node_tree.nodes["Background"].inputs[1].default_value = 0.45
    sc = bpy.context.scene
    sc.world = world
    add_cameras(spec)
    sc.frame_start, sc.frame_end = 0, last
    sc.render.fps = spec["fps"]
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.render.use_persistent_data = True
    sc.cycles.denoising_quality = "FAST"   # the OIDN pass dominates the time at 2 samples
    sc.cycles.max_bounces, sc.cycles.diffuse_bounces, sc.cycles.glossy_bounces = 2, 1, 0   # grey clay: one bounce is plenty
    sc.cycles.transmission_bounces = sc.cycles.volume_bounces = sc.cycles.transparent_max_bounces = 0
    sc.render.resolution_x, sc.render.resolution_y = spec["size"]
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.compression = 15
    sc.view_settings.view_transform = "Standard"
    return sc


def blender_projection_check(spec: dict, frames: list[int]) -> float:
    """Largest pixel gap between the pure-Python projection and Blender's camera for each person's feet and head."""
    from bpy_extras.object_utils import world_to_camera_view  # noqa: PLC0415
    from mathutils import Vector  # noqa: PLC0415
    bpy = bb._bpy()
    sc = bpy.context.scene
    size = spec["size"]
    worst = 0.0
    for fr in frames:
        sc.frame_set(fr)
        bpy.context.view_layer.update()
        cut = ss.cut_of(spec, fr)
        sc.camera = next(o for o in bpy.data.objects if o.name == cut["camera"] and o.type == "CAMERA")
        cam = ss.camera_state(spec, cut, fr)
        for p in spec["people"]:
            st = ss.person_state(p, fr)
            for dz in (0.0, ss.PERSON_HEIGHT):
                v = world_to_camera_view(sc, sc.camera, Vector((st["pos"][0], st["pos"][1], st["z"] + dz)))
                mine = ss.project(cam, tuple(size), (st["pos"][0], st["pos"][1], st["z"] + dz))
                if mine is None or v.z <= 0:
                    continue
                worst = max(worst, abs(v.x * size[0] - mine[0]), abs((1 - v.y) * size[1] - mine[1]))
    return worst
