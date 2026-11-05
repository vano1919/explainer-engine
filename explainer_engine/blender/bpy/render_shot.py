"""Runs INSIDE Blender, the only file of the repository that imports ``bpy`` (roadmap section 11). ``blender/render.py`` starts it:

    blender --background --factory-startup --python-exit-code 1 --python render_shot.py -- <job.json>

It reads the render job (``render_shot/1``, written by ``render.HeadlessRender``), checks that it runs on the pinned Blender, builds
or opens the scene, applies the profile's settings, renders exactly the frame indices the job lists and, after EACH frame, moves
the finished PNG into place (written under a temporary name first) and appends one line to the progress file, flushed to disk:
the host side commits frames from those lines while Blender keeps rendering (roadmap 10.4, ``RENDERED``). It ends with a report
(Blender version, build hash, engine, what was applied and what this Blender lacks, object counts). Any error raises, and
``--python-exit-code 1`` turns it into a non-zero exit (the 2026-11-04 PoC script raised and Blender still exited 0).

Scene kinds: ``smoke`` (a few primitives under a moving camera, built here: the CI smoke of roadmap 12.4 step 1), ``blend``
(a .blend file written by the scene builder, ICW-06, opened as it is) and ``described`` (primitives and objects appended from
library .blend files, placed as the job lists them: the ICW-05 style sheets). Any kind may carry ``style``, a ``style_graph/1``
document of ``blender/style.py``: its node trees, Line Art, paper pass and colour management are built here exactly as written
(the graph is data; this file only interprets it). stdlib + bpy (+ Blender's own mathutils) only.
"""
import json
import math
import os
import sys
import time

import bpy  # noqa: E402  (Blender's own module; this file never runs outside Blender)
from mathutils import Vector  # noqa: E402  (ships with Blender)

ENGINE_IDS = {"eevee": ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"), "cycles": ("CYCLES",), "workbench": ("BLENDER_WORKBENCH",)}


def job_path():
    argv = sys.argv
    if "--" not in argv or len(argv) <= argv.index("--") + 1:
        raise SystemExit("render_shot.py needs: -- <job.json>")
    return argv[argv.index("--") + 1]


def write_json(path, payload):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=1)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def set_engine(scene, engine):
    """Set the render engine by trying its known ids: the RNA enum lists only the built-in items (5.2.3 shows just
    BLENDER_EEVEE), while Workbench and Cycles are registered at run time, so the enum cannot be read up front."""
    for cand in ENGINE_IDS[engine]:
        try:
            scene.render.engine = cand
        except TypeError:
            continue
        return cand
    raise RuntimeError(f"this Blender has no {engine} engine (tried {ENGINE_IDS[engine]})")


def set_attr(obj, name, value, applied, missing, label):
    if value is None:
        return
    if hasattr(obj, name):
        setattr(obj, name, value)
        applied[label] = value
    else:
        missing.append(label)


def build_smoke(scene, frames_total):
    """A floor, three coloured primitives and a sun under a camera that dollies in and pans: every frame differs, none is black."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("smoke_world")
    scene.world.color = (0.62, 0.58, 0.50)

    def mat(name, rgba):
        m = bpy.data.materials.new(name)
        m.diffuse_color = rgba
        return m

    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0))
    bpy.context.active_object.data.materials.append(mat("floor", (0.80, 0.74, 0.60, 1)))
    shapes = ((bpy.ops.mesh.primitive_cube_add, (-2.0, 0, 1), (0.70, 0.18, 0.12, 1)),
              (bpy.ops.mesh.primitive_uv_sphere_add, (0, 1.5, 1), (0.15, 0.35, 0.60, 1)),
              (bpy.ops.mesh.primitive_cone_add, (2.0, 0, 1), (0.20, 0.50, 0.25, 1)))
    for add, loc, rgba in shapes:
        add(location=loc)
        bpy.context.active_object.data.materials.append(mat(f"m{loc[0]:g}", rgba))
    bpy.ops.object.light_add(type="SUN", location=(4, -4, 8))
    bpy.ops.object.camera_add(location=(0, -12, 4), rotation=(1.30, 0, 0))
    cam = bpy.context.active_object
    scene.camera = cam
    last = scene.frame_start + max(frames_total - 1, 1)
    cam.keyframe_insert("location", frame=scene.frame_start)
    cam.keyframe_insert("rotation_euler", frame=scene.frame_start)
    cam.location = (3, -8, 3)
    cam.rotation_euler = (1.30, 0, 0.35)
    cam.keyframe_insert("location", frame=last)
    cam.keyframe_insert("rotation_euler", frame=last)


# --- the described scene and the style graph (ICW-05; the graph is made by blender/style.py) --------------------------------------

PRIMITIVES = {"plane": "primitive_plane_add", "cube": "primitive_cube_add", "cylinder": "primitive_cylinder_add",
              "uv_sphere": "primitive_uv_sphere_add", "ico_sphere": "primitive_ico_sphere_add", "cone": "primitive_cone_add"}


def _rad(deg):
    return tuple(math.radians(d) for d in deg)


def _place(ob, o):
    ob.location = o.get("location", (0, 0, 0))
    ob.rotation_euler = _rad(o.get("rotation_deg", (0, 0, 0)))
    sc = o.get("scale", 1.0)
    ob.scale = (sc, sc, sc) if isinstance(sc, (int, float)) else sc


def _append(o, report):
    """Mesh objects of a library .blend under one empty (their own transforms kept), with every material replaced by the named
    toon material. Armatures, widgets and curves are left out (a prop is drawn at its rest pose), and so are their modifiers."""
    src = o["append"]
    with bpy.data.libraries.load(src["path"], link=False) as (data_from, data_to):
        names = src.get("objects") or list(data_from.objects)
        data_to.objects = [n for n in names if n in data_from.objects]
    root = bpy.data.objects.new(o["name"], None)
    bpy.context.scene.collection.objects.link(root)
    kept = 0
    for ob in data_to.objects:
        if ob is None or ob.type != "MESH" or len(ob.data.polygons) == 0:
            continue
        for m in list(ob.modifiers):
            if m.type == "ARMATURE":
                ob.modifiers.remove(m)
        ob.parent = None
        bpy.context.scene.collection.objects.link(ob)
        ob.parent = root
        kept += 1
    report.setdefault("appended", {})[o["name"]] = kept
    if kept == 0:
        raise RuntimeError(f"{src['path']}: no mesh object to append")
    _place(root, o)
    return [c for c in root.children]


def _assign(obs, material, smooth=None):
    for ob in obs:
        if smooth is not None:
            for poly in ob.data.polygons:
                poly.use_smooth = smooth
        ob.data.materials.clear()
        ob.data.materials.append(material)


def _aim(ob, location, look_at, compat=None):
    ob.location = location
    q = (Vector(look_at) - Vector(location)).to_track_quat("-Z", "Y")
    ob.rotation_euler = q.to_euler("XYZ", compat) if compat is not None else q.to_euler()


def _key(ob, paths, frame, interp):
    """One keyframe of ``paths`` at ``frame``; the new key's interpolation is the preference at insert time (Blender 5.x
    layered actions have no per-call argument), so it is set first."""
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    for p in paths:
        ob.keyframe_insert(p, frame=frame)


def build_described(scene, sc, report):
    """Objects, camera and (optional) motion of a ``described`` scene. Motion: an object or the camera with a ``to`` block
    ({location[, rotation_deg]} / {location, look_at}) is keyed at the first and the last frame of ``frames_total``;
    ``interp`` is LINEAR (a march, a cart) or BEZIER (a camera push that eases in and out, the default for the camera)."""
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)
    pending, moving = [], []
    for o in sc["objects"]:
        if "add" in o:
            getattr(bpy.ops.mesh, PRIMITIVES[o["add"]])(**o.get("params", {}))
            ob = bpy.context.active_object
            ob.name = o["name"]
            _place(ob, o)
            obs, handle = [ob], ob
        elif "append" in o:
            obs = _append(o, report)
            handle = bpy.data.objects[o["name"]]
        else:
            raise RuntimeError(f"object {o.get('name')!r}: neither add nor append")
        pending.append((obs, o.get("material"), o.get("smooth")))
        if o.get("to"):
            moving.append((handle, o))
    cam = sc["camera"]
    data = bpy.data.cameras.new("camera")
    data.lens, data.sensor_width = cam["lens_mm"], cam.get("sensor_mm", 36.0)
    data.clip_end = cam.get("clip_end", 500.0)
    ob = bpy.data.objects.new("camera", data)
    scene.collection.objects.link(ob)
    _aim(ob, cam["location"], cam["look_at"])
    scene.camera = ob
    first = scene.frame_start
    last = first + int(sc.get("frames_total", 1)) - 1
    if last > first:
        for h, o in moving:
            _key(h, ("location", "rotation_euler"), first, o.get("interp", "LINEAR"))
            h.location = o["to"]["location"]
            if "rotation_deg" in o["to"]:
                h.rotation_euler = _rad(o["to"]["rotation_deg"])
            _key(h, ("location", "rotation_euler"), last, o.get("interp", "LINEAR"))
        if cam.get("to"):
            _key(ob, ("location", "rotation_euler"), first, cam.get("interp", "BEZIER"))
            _aim(ob, cam["to"]["location"], cam["to"]["look_at"], ob.rotation_euler.copy())
            _key(ob, ("location", "rotation_euler"), last, cam.get("interp", "BEZIER"))
        report["motion"] = {"frames": [first, last], "objects": len(moving), "camera": bool(cam.get("to"))}
    return pending


def _set(node, key, value, missing, where):
    """A node setting: an RNA property when the node has one, else the input socket of that name (Blender 5 turned many
    compositor properties into inputs)."""
    if hasattr(node, key):
        try:
            setattr(node, key, value)
            return
        except (TypeError, AttributeError, ValueError):
            pass
    for sock in node.inputs:
        if sock.name.lower().replace(" ", "_") == key.lower():
            try:
                sock.default_value = value
                return
            except (TypeError, AttributeError, ValueError):
                break
    missing.append(f"{where}:{node.bl_idname}.{key}")


def _socket(coll, key):
    if isinstance(key, int):
        return coll[key]
    for sock in coll:
        if sock.name == key or sock.identifier == key:
            return sock
    raise RuntimeError(f"no socket {key!r} (have {[x.name for x in coll]})")


def _image(path):
    img = bpy.data.images.load(path, check_existing=True)
    return img


def build_tree(nt, graph, missing, where):
    """The nodes and links of one graph of blender/style.py, exactly as listed."""
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    made = {}
    for spec in graph["nodes"]:
        node = nt.nodes.new(spec["type"])
        node.name = node.label = spec["id"]
        for k, v in spec.get("props", {}).items():
            _set(node, k, v, missing, where)
        if "image" in spec:
            node.image = _image(spec["image"])
        if "ramp" in spec:
            cr = node.color_ramp
            cr.interpolation = spec["ramp"]["interpolation"]
            stops = spec["ramp"]["stops"]
            while len(cr.elements) < len(stops):
                cr.elements.new(0.5)
            for el, (pos, col) in zip(cr.elements, stops):
                el.position, el.color = pos, col
        for k, v in spec.get("inputs", {}).items():
            key = int(k) if isinstance(k, str) and k.isdigit() else k
            _socket(node.inputs, key).default_value = v
        made[spec["id"]] = node
    for a, out, b, inp in graph["links"]:
        nt.links.new(_socket(made[a].outputs, out), _socket(made[b].inputs, inp))
    return made


def apply_style(scene, style, pending, report):
    """The style_graph/1 document on the built scene: materials, world, key light, Line Art, paper pass, colour management."""
    missing = []
    mats = {}
    for m in style["materials"]:
        mat = bpy.data.materials.new(m["name"])
        build_tree(mat.node_tree, m, missing, f"material {m['name']}")
        mats[m["name"]] = mat
    for obs, name, smooth in pending:
        if name is not None:
            if name not in mats:
                raise RuntimeError(f"the style graph has no material {name!r}")
            _assign(obs, mats[name], smooth)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("world")
    build_tree(scene.world.node_tree, style["world"], missing, "world")
    kl = style["key_light"]
    sun = bpy.data.lights.new("key", "SUN")
    sun.energy, sun.angle = kl["energy"], kl["angle_rad"]
    sun.use_shadow = kl.get("use_shadow", True)  # the light profile turns cast shadows off (style.StyleTokens.shadows)
    ob = bpy.data.objects.new("key", sun)
    scene.collection.objects.link(ob)
    ob.rotation_euler = kl["rotation_euler"]
    la = style["line_art"]
    bpy.ops.object.grease_pencil_add(type="LINEART_SCENE", location=(0, 0, 0))
    gp = bpy.context.active_object
    gp.name = "line_art"
    mod = [m for m in gp.modifiers if m.type == "LINEART"][0]
    mod.radius, mod.crease_threshold, mod.opacity = la["radius"], la["crease_threshold_rad"], la["opacity"]
    for gm in gp.data.materials:
        gm.grease_pencil.color = la["ink_rgba"]
    st = style["scene"]
    vs = scene.view_settings
    vs.view_transform = st["view_transform"]
    for cand in st["look_ids"]:
        try:
            vs.look = cand
            break
        except TypeError:
            continue
    else:
        raise RuntimeError(f"this Blender has no look {st['look']!r} (tried {st['look_ids']})")
    applied = {"view_transform": vs.view_transform, "look": vs.look, "line_art_radius": mod.radius,
               "crease_threshold": mod.crease_threshold}
    for k, v in st.get("eevee", {}).items():
        set_attr(scene.eevee, k, v, applied, missing, f"eevee.{k}")
    for k, v in st.get("cycles", {}).items():
        if hasattr(scene, "cycles"):
            set_attr(scene.cycles, k, v, applied, missing, f"cycles.{k}")
    paper = style["paper"]
    if paper.get("enabled"):
        ng = bpy.data.node_groups.new("ink_paper", "CompositorNodeTree")
        ng.interface.new_socket("Image", in_out="OUTPUT", socket_type="NodeSocketColor")
        build_tree(ng, paper, missing, "paper")
        scene.compositing_node_group = ng
        applied["paper"] = paper["opacity"]
    report["style"] = {"schema": style["schema"], "path": style["path"], "sha256": style.get("sha256"), "applied": applied,
                       "missing": missing, "materials": sorted(mats)}
    if missing:
        raise RuntimeError(f"style graph settings this Blender lacks: {missing}")


def apply_settings(scene, job):
    applied, missing = {}, []
    s, eng = job["settings"], job["engine"]
    set_engine(scene, eng)
    applied["engine_id"] = scene.render.engine
    if eng == "eevee":
        ee = scene.eevee
        set_attr(ee, "taa_render_samples", s.get("samples"), applied, missing, "eevee.taa_render_samples")
        set_attr(ee, "use_raytracing", s.get("raytracing"), applied, missing, "eevee.use_raytracing")
        set_attr(ee, "use_gtao", s.get("ambient_occlusion"), applied, missing, "eevee.use_gtao")
    elif eng == "cycles":
        cy = scene.cycles
        set_attr(cy, "samples", s.get("samples"), applied, missing, "cycles.samples")
        set_attr(cy, "use_denoising", s.get("denoise"), applied, missing, "cycles.use_denoising")
        set_attr(cy, "seed", job.get("seed"), applied, missing, "cycles.seed")
        if job["device"] == "gpu":
            prefs = bpy.context.preferences.addons["cycles"].preferences
            for kind in ("OPTIX", "CUDA", "METAL"):  # METAL: Apple silicon (the creator's Mac, ICG-3)
                try:
                    prefs.compute_device_type = kind
                    prefs.get_devices()
                    if any(d.type == kind for d in prefs.devices):
                        break
                except TypeError:
                    continue
            else:
                raise RuntimeError("device gpu: Cycles finds no OPTIX, CUDA or METAL device")
            for d in prefs.devices:
                d.use = d.type == prefs.compute_device_type
            cy.device = "GPU"
            applied["cycles.device"] = f"GPU/{prefs.compute_device_type}"
    else:
        sh = scene.display.shading
        set_attr(sh, "light", "STUDIO", applied, missing, "display.shading.light")
        set_attr(sh, "color_type", "MATERIAL", applied, missing, "display.shading.color_type")
    set_attr(scene.render, "use_motion_blur", s.get("motion_blur"), applied, missing, "render.use_motion_blur")
    return applied, missing


def gpu_backend():
    try:
        import gpu
        return gpu.platform.backend_type_get()
    except Exception:  # noqa: BLE001  (informational only: a missing field never fails a render)
        return None


def main():
    path = job_path()
    with open(path, encoding="utf-8") as f:
        job = json.load(f)
    if job.get("job") != "render_shot/1":
        raise RuntimeError(f"{path} is not a render_shot/1 job")
    have = bpy.app.version_string.split()[0]
    if have != job["pin_version"]:
        raise RuntimeError(f"Blender {have} is not the pinned {job['pin_version']} (BP-175)")
    sc = job["scene"]
    if sc["kind"] == "blend":
        bpy.ops.wm.open_mainfile(filepath=sc["path"])
    scene = bpy.context.scene
    scene.frame_start = job["frame_start"]
    scene.render.fps, scene.render.fps_base = job["fps"], 1.0
    built = {}
    pending = []
    if sc["kind"] == "smoke":
        build_smoke(scene, sc["frames_total"])
    elif sc["kind"] == "described":
        pending = build_described(scene, sc, built)
    elif sc["kind"] != "blend":
        raise RuntimeError(f"unknown scene kind {sc['kind']!r}")
    if scene.camera is None:
        raise RuntimeError("the scene has no camera")
    r = scene.render
    r.resolution_x, r.resolution_y, r.resolution_percentage = job["width"], job["height"], int(job["percent"])
    r.pixel_aspect_x = r.pixel_aspect_y = 1.0
    r.film_transparent = False
    r.use_file_extension = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.color_depth = "8"
    applied, missing = apply_settings(scene, job)
    if sc.get("style"):
        apply_style(scene, sc["style"], pending, built)  # after the profile: the style's EEVEE switches win (roadmap 9.1)
    os.makedirs(job["frames_dir"], exist_ok=True)
    with open(job["progress"], "a", encoding="utf-8") as prog:
        for idx in job["frames"]:
            name = job["frame_name"].format(index=idx)
            final = os.path.join(job["frames_dir"], name)
            tmp = os.path.join(job["frames_dir"], ".part_" + name)
            scene.frame_set(job["frame_start"] + idx)
            r.filepath = tmp
            t0 = time.perf_counter()
            bpy.ops.render.render(write_still=True)
            if not os.path.isfile(tmp) or os.path.getsize(tmp) == 0:
                raise RuntimeError(f"frame {idx}: Blender wrote no image at {tmp}")
            os.replace(tmp, final)
            secs = time.perf_counter() - t0
            prog.write(json.dumps({"index": idx, "file": name, "seconds": round(secs, 4)}) + "\n")
            prog.flush()
            os.fsync(prog.fileno())
    kinds = {}
    for ob in scene.objects:
        kinds[ob.type] = kinds.get(ob.type, 0) + 1
    write_json(job["report"], {
        "blender_version": bpy.app.version_string,
        "build_hash": bpy.app.build_hash.decode("ascii", "replace") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "engine_id": scene.render.engine, "applied": applied, "missing": missing, "objects": kinds,
        "frames": len(job["frames"]), "gpu_backend": gpu_backend(), **built,
    })


main()
