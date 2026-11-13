"""Blender renders every C / D / H shot of a cut plan (production/cut_plan.py) to frames. Moved into the repo from the PC's one-off
``minute1_render_plan.py`` (2026-11-07) and changed after the Gemini review (the creator, 22:23 UTC):

- D (dialogue cut-out): a chest-up close-up (DL-01, the gate refuses h < 1.35); the mouth switches between the four drawn states
  on the line's mouth cues (DL-04, ``cut_plan.mouth_track``: rest on silence and on the other speaker's lines); ``flip_x`` mirrors a
  three-quarter view so the two speakers face each other (DL-06); breathing, a small sway and a nod; textures clip at their edge
  (no repeat-wrap line, DL-03; the matte is trimmed first by ``cutout_prep.trim_edge``).
- C / H: picture with a push that is at rest at the cut (ED-08), optional fire glow and snow.

The gate runs first: a plan with any FAIL is not rendered.

    blender -b -P explainer_engine/blender/bpy/cut_render.py -- <plan.json> <frames_dir> [shot ids...]
"""
import json
import math
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from explainer_engine.production import cut_plan  # noqa: E402

import bpy  # noqa: E402

args = sys.argv[sys.argv.index("--") + 1:]
PLAN, OUTD = Path(args[0]), Path(args[1])
ONLY = set(args[2:])
plan = json.loads(PLAN.read_text())
if cut_plan.report(cut_plan.gate(plan)):
    raise SystemExit("cut plan breaks a FAIL rule: nothing rendered")
FPS = plan["fps"]
RES = tuple(plan["size"])
LENS, SENSOR = 35.0, 36.0
TAN_H = SENSOR / 2 / LENS
TAN_V = TAN_H * RES[1] / RES[0]


def interp(kind):
    bpy.context.preferences.edit.keyframe_new_interpolation_type = kind


def mat(name, path, alpha=False, strength=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(str(path))
    tex.interpolation = "Cubic"
    tex.extension = "CLIP"                      # DL-03: no repeat wrap of the image border (the v1 white top line)
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Strength"].default_value = strength
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(tex.outputs["Color"], em.inputs["Color"])
    if alpha:
        tr = nt.nodes.new("ShaderNodeBsdfTransparent")
        mx = nt.nodes.new("ShaderNodeMixShader")
        nt.links.new(tex.outputs["Alpha"], mx.inputs[0])
        nt.links.new(tr.outputs[0], mx.inputs[1])
        nt.links.new(em.outputs[0], mx.inputs[2])
        nt.links.new(mx.outputs[0], o.inputs["Surface"])
        try:
            m.surface_render_method = "BLENDED"
        except AttributeError:
            m.blend_method = "BLEND"
    else:
        nt.links.new(em.outputs[0], o.inputs["Surface"])
    return m, tex.image, em


def plane(name, w, h, loc, m):
    bpy.ops.mesh.primitive_plane_add(size=1, location=loc)
    o = bpy.context.object
    o.name = name
    o.scale = (w, h, 1)
    o.rotation_euler = (math.radians(90), 0, 0)
    o.data.materials.append(m)
    return o


def setup(n):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE"
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.fps = FPS
    sc.frame_start, sc.frame_end = 1, n
    sc.view_settings.view_transform = "Standard"
    sc.world = bpy.data.worlds.new("w")
    sc.render.image_settings.file_format = "PNG"
    cd = bpy.data.cameras.new("cam")
    cd.lens, cd.sensor_width = LENS, SENSOR
    cam = bpy.data.objects.new("cam", cd)
    sc.collection.objects.link(cam)
    cam.rotation_euler = (math.radians(90), 0, 0)
    sc.camera = cam
    return sc, cam


def picture(path, depth, over=1.0):
    m, img, _ = mat("pic", path)
    w = 2 * depth * TAN_H * over
    h = w * img.size[1] / img.size[0]
    if h < 2 * depth * TAN_V * over:
        h = 2 * depth * TAN_V * over
        w = h * img.size[0] / img.size[1]
    return plane("pic", w, h, (0, depth, 0), m)


def push(cam, n, dy, dx=0.0):
    """ED-08: an eased push that is at rest at the cut."""
    interp("SINE")
    cam.location = (0, 0, 0)
    cam.keyframe_insert("location", frame=1)
    cam.location = (dx, dy, 0)
    cam.keyframe_insert("location", frame=n)
    interp("BEZIER")


def cutout(s, depth, n):
    """DL-01/04/05/06: one card per mouth state (all the same drawing), exactly one visible per frame."""
    m_states = s.get("mouth") or {"rest": s["cut"]}
    view_h = 2 * depth * TAN_V
    frame_h, drop, x = s.get("h", 1.45), s.get("drop", 0.38), s.get("x", 0.0)
    pivot = bpy.data.objects.new("pivot", None)
    bpy.context.scene.collection.objects.link(pivot)
    pivot.location = (x, depth, -view_h / 2 - 0.02 - drop * view_h)
    track = ["rest"] * n
    for k in s.get("lines", []):
        line = plan["lines"][k]
        if cut_plan._speaker_entity(plan, line["who"]) == str(s.get("who", "")).lower() and s.get("mouth_cues"):
            cues = json.loads(Path(s["mouth_cues"]).read_text())["mouthCues"]
            for f, st in enumerate(cut_plan.mouth_track(cues, line["at"], s["start"], n, FPS)):
                if st != "rest":
                    track[f] = st
    cards = {}
    for state, path in m_states.items():
        mt, img, _ = mat(f"hero_{state}", path, alpha=True)
        h = view_h * frame_h
        w = h * img.size[0] / img.size[1]
        card = plane(f"hero_{state}", w, h, (0, 0, h / 2), mt)
        card.parent = pivot
        if s.get("flip_x"):
            card.scale.x = -card.scale.x
        cards[state] = card
    for state, card in cards.items():
        prev = None
        for f in range(1, n + 1):
            hide = track[f - 1] != state and not (state == "rest" and track[f - 1] not in cards)
            if hide != prev:
                card.hide_render = hide
                card.keyframe_insert("hide_render", frame=f)
                prev = hide
    if s.get("breathing", True):
        for f in range(1, n + 1, 2):
            t = (f - 1) / FPS
            pivot.scale = (1.0, 1.0, 1.0 + 0.012 * (0.5 - 0.5 * math.cos(2 * math.pi * t / 4.0)))
            nod = math.radians(1.2) * max(0.0, math.sin(2 * math.pi * t / 2.7)) if track[f - 1] != "rest" else 0.0
            pivot.rotation_euler = (nod, math.radians(0.6) * math.sin(2 * math.pi * t / 5.0), 0)
            pivot.keyframe_insert("scale", frame=f)
            pivot.keyframe_insert("rotation_euler", frame=f)


def snow(n, count=70, seed=7):
    m = bpy.data.materials.new("flake")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs["Color"].default_value = (1, 1, 1, 1)
    em.inputs["Strength"].default_value = 0.9
    o = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(em.outputs[0], o.inputs["Surface"])
    rnd = random.Random(seed)
    secs = n / FPS
    for _ in range(count):
        d = rnd.uniform(2.5, 9.0)
        hw, hh = d * TAN_H * 1.1, d * TAN_V * 1.1
        x0, z0 = rnd.uniform(-hw, hw), rnd.uniform(-hh, hh * 2)
        fall = rnd.uniform(0.25, 0.55) * d * secs / 3
        bpy.ops.mesh.primitive_uv_sphere_add(radius=0.005 * d, segments=6, ring_count=4, location=(x0, d, z0))
        fl = bpy.context.object
        fl.data.materials.append(m)
        interp("LINEAR")
        fl.keyframe_insert("location", frame=1)
        fl.location = (x0 + rnd.uniform(-0.15, 0.15) * d, d, z0 - fall)
        fl.keyframe_insert("location", frame=n)
        interp("BEZIER")


def fire_glow(fire_png, depth, n):
    m, fimg, em = mat("fire", fire_png, alpha=True)
    w = 2 * (depth - 0.02) * TAN_H
    plane("fire", w, w * fimg.size[1] / fimg.size[0], (0, depth - 0.02, 0), m)
    rnd = random.Random(3)
    for f in range(1, n + 1, 2):
        em.inputs["Strength"].default_value = 0.55 + 0.45 * (0.5 + 0.5 * math.sin(f * 0.9)) * rnd.uniform(0.6, 1.0)
        em.inputs["Strength"].keyframe_insert("default_value", frame=f)


for s in plan["shots"]:
    if s["type"] not in ("C", "D", "H") or (ONLY and str(s["id"]) not in ONLY):
        continue
    n = max(2, round(s["dur"] * FPS))
    sc, cam = setup(n)
    if s["type"] in ("C", "H"):
        picture(s["img"], 14.0, over=1.0)
        if s.get("fire_mask"):
            fire_glow(s["fire_mask"], 14.0, n)
        if s.get("snow"):
            snow(n, count=50)
        push(cam, n, 14.0 * (1 - 1 / s.get("push", 1.08)))
    else:
        picture(s["bg"], 14.0, over=1.18)
        cutout(s, 5.0, n)
        if s.get("snow"):
            snow(n)
        push(cam, n, 0.45, 0.12 if s.get("x", 0) < 0 else -0.12)
    d = OUTD / f"s{s['id']}"
    d.mkdir(parents=True, exist_ok=True)
    sc.render.filepath = str(d / "f_")
    bpy.ops.render.render(animation=True)
    print("rendered", s["id"], s["type"], n, flush=True)
