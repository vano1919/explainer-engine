"""Runs INSIDE Blender (or a Python with the bpy 5.2.3 wheel): the J5 route's 2.5D assembly (D-116, ``blender/assemble_25d.py``).

    blender --background --factory-startup --python-exit-code 1 --python assemble_25d.py -- <job.json>

It reads an ``assemble_25d/1`` job and builds exactly what it lists: the 360 backdrop as the world, one camera-facing card per
hero and prop (emission only: the sheets are drawn flat-lit; no light in the scene, no card casts or takes a shadow), a flat contact
shadow under each hero, the mouth's three states and the blink as keyed mixes of the card's images, breathing as keyed vertical
scale about the feet, and the camera keys. It renders the job's frames one by one (temporary name, then ``os.replace``) and
appends one progress line per frame, flushed, like ``render_shot.py``. The report lists the cards, their shadow flags, the
framing of the probe points and the seconds per frame. Decides nothing; stdlib + bpy (+ mathutils) only.
"""
import json
import math
import os
import sys
import time

import bpy  # noqa: E402  (Blender's own module; this file never runs outside Blender)
from bpy_extras.object_utils import world_to_camera_view  # noqa: E402
from mathutils import Vector  # noqa: E402

ENGINE_IDS = {"eevee": ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"), "cycles": ("CYCLES",)}


def job_path():
    argv = sys.argv
    if "--" not in argv or len(argv) <= argv.index("--") + 1:
        raise SystemExit("assemble_25d.py needs: -- <job.json>")
    return argv[argv.index("--") + 1]


def write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def set_engine(scene, engine):
    for cand in ENGINE_IDS[engine]:
        try:
            scene.render.engine = cand
        except TypeError:
            continue
        return cand
    raise RuntimeError(f"this Blender has no {engine} engine (tried {ENGINE_IDS[engine]})")


def clear(scene):
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras, bpy.data.images):
        for item in list(coll):
            coll.remove(item)


def image(path):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = "sRGB"
    im.alpha_mode = "STRAIGHT"
    return im


def socket(node, ident):
    for s in list(node.inputs) + list(node.outputs):
        if s.identifier == ident:
            return s
    raise RuntimeError(f"{node.bl_idname} has no socket {ident}")


def mix_rgb(nt, a, b, fac):
    m = nt.nodes.new("ShaderNodeMix")
    m.data_type = "RGBA"
    m.blend_type = "MIX"
    nt.links.new(a, socket(m, "A_Color"))
    nt.links.new(b, socket(m, "B_Color"))
    if isinstance(fac, float):
        socket(m, "Factor_Float").default_value = fac
    else:
        nt.links.new(fac, socket(m, "Factor_Float"))
    return m, socket(m, "Result_Color")


def key_value(sock, values, data_path="default_value"):
    """One CONSTANT key per frame (frame 1 = index 0), written only where the value changes."""
    last = None
    for i, v in enumerate(values):
        if last is None or abs(v - last) > 1e-9 or i == len(values) - 1:
            sock.default_value = v
            sock.keyframe_insert(data_path, frame=1 + i)
            last = v


def constant_interp(id_data):
    ad = id_data.animation_data
    if ad and ad.action:
        for fc in fcurves(ad.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def fcurves(action):
    """The F-curves of an action: ``action.fcurves`` before 5.0, the layered action's channelbags since (5.0 API)."""
    if hasattr(action, "fcurves"):
        return list(action.fcurves)
    out = []
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                out.extend(bag.fcurves)
    return out


def card_material(card):
    mat = bpy.data.materials.new("mat_" + card["name"])
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    base = nt.nodes.new("ShaderNodeTexImage")
    base.image = image(card["image"])
    base.interpolation = "Linear"
    col = base.outputs["Color"]
    keyed = []
    if card.get("mouth"):
        half = nt.nodes.new("ShaderNodeTexImage")
        half.image = image(card["mouth"]["half"])
        opn = nt.nodes.new("ShaderNodeTexImage")
        opn.image = image(card["mouth"]["open"])
        m1, col = mix_rgb(nt, col, half.outputs["Color"], 0.0)
        m2, col = mix_rgb(nt, col, opn.outputs["Color"], 0.0)
        keyed += [(socket(m1, "Factor_Float"), [f[0] for f in card["mouth"]["factors"]]),
                  (socket(m2, "Factor_Float"), [f[1] for f in card["mouth"]["factors"]])]
    if card.get("blink"):
        lid = nt.nodes.new("ShaderNodeTexImage")
        lid.image = image(card["blink"]["image"])
        w = nt.nodes.new("ShaderNodeMath")
        w.operation = "MULTIPLY"
        nt.links.new(lid.outputs["Alpha"], w.inputs[0])
        m3, col = mix_rgb(nt, col, lid.outputs["Color"], w.outputs[0])
        keyed.append((w.inputs[1], card["blink"]["track"]))
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    nt.links.new(col, emit.inputs["Color"])
    clear_bsdf = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(base.outputs["Alpha"], mix.inputs["Fac"])
    nt.links.new(clear_bsdf.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], outn.inputs["Surface"])
    for sock, values in keyed:
        key_value(sock, values)
    constant_interp(nt)
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    return mat


def plane(name, x0, x1, z0, z1, y=0.0):
    """A plane in the object's XZ plane, its front facing -Y; uv 0..1 over it."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="uv")
    for i, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = (u, v)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def no_shadow(ob):
    if hasattr(ob, "visible_shadow"):
        ob.visible_shadow = False


def build_card(card):
    ob = plane(card["name"], card["left_m"], card["left_m"] + card["width_m"], card["bottom_m"], card["bottom_m"] + card["height_m"])
    ob.location = card["pos"]
    ob.rotation_euler = (0.0, 0.0, math.radians(card["yaw_deg"]))
    ob.data.materials.append(card_material(card))
    no_shadow(ob)
    if card.get("breath"):
        for i, s in enumerate(card["breath"]):
            ob.scale = (1.0, 1.0, s)
            ob.keyframe_insert("scale", index=2, frame=1 + i)
    return ob


def shadow_image(name, size=(128, 64)):
    w, h = size
    im = bpy.data.images.new(name, w, h, alpha=True)
    px = []
    for j in range(h):
        for i in range(w):
            dx, dy = (i + 0.5) / w * 2 - 1, (j + 0.5) / h * 2 - 1
            r = math.sqrt(dx * dx + dy * dy)
            a = max(0.0, 1.0 - r) ** 1.5
            px += [0.0, 0.0, 0.0, a]
    im.pixels.foreach_set(px)
    im.alpha_mode = "STRAIGHT"
    return im


def build_shadow(card):
    s = card["shadow"]
    w, d = s["width_m"], s["depth_m"]
    me = bpy.data.meshes.new("shadow_" + card["name"])
    me.from_pydata([(-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="uv")
    for i, (u, v) in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = (u, v)
    ob = bpy.data.objects.new("shadow_" + card["name"], me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = (card["pos"][0], card["pos"][1], card["pos"][2] + 0.003)
    ob.rotation_euler = (0.0, 0.0, math.radians(card["yaw_deg"]))
    mat = bpy.data.materials.new("mat_shadow_" + card["name"])
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = shadow_image("shadow_" + card["name"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    mul.inputs[1].default_value = s["alpha"]
    nt.links.new(tex.outputs["Alpha"], mul.inputs[0])
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (0.0, 0.0, 0.0, 1.0)
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    nt.links.new(mul.outputs[0], mix.inputs["Fac"])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    me.materials.append(mat)
    no_shadow(ob)
    return ob


def build_world(scene, world):
    w = bpy.data.worlds.new("backdrop_360")
    scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    coord = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Rotation"].default_value = (0.0, 0.0, math.radians(world["yaw_deg"]))
    env = nt.nodes.new("ShaderNodeTexEnvironment")
    env.image = image(world["image"])
    env.projection = "EQUIRECTANGULAR"
    env.interpolation = "Linear"
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    nt.links.new(env.outputs["Color"], bg.inputs["Color"])
    nt.links.new(bg.outputs[0], out.inputs["Surface"])


def build_camera(scene, cam):
    data = bpy.data.cameras.new("camera")
    data.lens = cam["lens_mm"]
    data.sensor_width = cam["sensor_mm"]
    data.sensor_fit = "HORIZONTAL"
    data.clip_start, data.clip_end = 0.05, 500.0
    ob = bpy.data.objects.new("camera", data)
    scene.collection.objects.link(ob)
    scene.camera = ob
    for k in cam["keys"]:
        loc, at = Vector(k["location"]), Vector(k["look_at"])
        ob.location = loc
        ob.rotation_euler = (at - loc).to_track_quat("-Z", "Y").to_euler()
        ob.keyframe_insert("location", frame=1 + k["frame"])
        ob.keyframe_insert("rotation_euler", frame=1 + k["frame"])
    if ob.animation_data and ob.animation_data.action:
        for fc in fcurves(ob.animation_data.action):
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"
    return ob


def main():
    path = job_path()
    with open(path, encoding="utf-8") as f:
        job = json.load(f)
    if job.get("job") != "assemble_25d/1":
        raise RuntimeError(f"{path} is not an assemble_25d/1 job")
    have = bpy.app.version_string.split()[0]
    if have != job["pin_version"]:
        raise RuntimeError(f"Blender {have} is not the pinned {job['pin_version']} (BP-175)")
    scene = bpy.context.scene
    clear(scene)
    scene.frame_start, scene.frame_end = 1, job["frames"]
    scene.render.fps, scene.render.fps_base = job["fps"], 1.0
    engine_id = set_engine(scene, job["engine"])
    if job["engine"] == "eevee":
        scene.eevee.taa_render_samples = job["samples"]
    else:
        scene.cycles.samples = job["samples"]
        scene.cycles.use_denoising = False
        scene.cycles.device = "CPU"
    scene.view_settings.view_transform = "Standard"   # the drawn colours exactly, no filmic curve
    scene.view_settings.look = "None"
    scene.view_settings.exposure, scene.view_settings.gamma = 0.0, 1.0
    build_world(scene, job["world"])
    cam = build_camera(scene, job["camera"])
    cards = []
    for c in job["cards"]:
        cards.append(build_card(c))
        if c.get("shadow"):
            build_shadow(c)
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = job["width"], job["height"], 100
    transparent = bool(job.get("transparent"))   # a layer pass (J5 dialogue test): the cards alone on alpha, the world not drawn
    r.film_transparent = transparent
    r.use_file_extension = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGBA" if transparent else "RGB"
    r.image_settings.color_depth = "8"
    os.makedirs(job["frames_dir"], exist_ok=True)
    secs = []
    with open(job["progress"], "a", encoding="utf-8") as prog:
        for idx in job["frame_list"]:
            name = job["frame_name"].format(index=idx)
            final = os.path.join(job["frames_dir"], name)
            tmp = os.path.join(job["frames_dir"], ".part_" + name)
            scene.frame_set(1 + idx)
            r.filepath = tmp
            t0 = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
                raise RuntimeError(f"frame {idx}: Blender wrote no image at {tmp}")
            os.replace(tmp, final)
            secs.append(time.perf_counter() - t0)
            prog.write(json.dumps({"index": idx, "file": name, "seconds": round(secs[-1], 4)}) + "\n")
            prog.flush()
            os.fsync(prog.fileno())
    framing = {}
    for which, idx in (("first", job["frame_list"][0]), ("last", job["frame_list"][-1])):
        scene.frame_set(1 + idx)
        framing[which] = {p["name"]: list(world_to_camera_view(scene, cam, Vector(p["at"])))[:2] for p in job.get("probe", [])}
    shadows = [ob.name for ob in scene.objects if ob.type == "MESH" and getattr(ob, "visible_shadow", False)]
    write_json(job["report"], {
        "blender_version": bpy.app.version_string, "engine_id": engine_id, "frames": len(job["frame_list"]),
        "seconds_per_frame": round(sum(secs) / len(secs), 4) if secs else None,
        "cards": [ob.name for ob in cards], "lights": len([o for o in scene.objects if o.type == "LIGHT"]),
        "cast_shadows": shadows, "framing": framing, "view_transform": scene.view_settings.view_transform,
    })


main()
