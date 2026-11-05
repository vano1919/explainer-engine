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
library .blend files, placed as the job lists them: the ICW-05 style sheets; since ICW-06 also ``character`` objects: rigged cast
members assembled from library GLBs, see ``build_character``). Any kind may carry ``style``, a ``style_graph/1``
document of ``blender/style.py``: its node trees, Line Art, paper pass and colour management are built here exactly as written
(the graph is data; this file only interprets it). stdlib + bpy (+ Blender's own mathutils) only.
"""
import json
import math
import os
import re
import sys
import time

import bpy  # noqa: E402  (Blender's own module; this file never runs outside Blender)
from mathutils import Vector  # noqa: E402  (ships with Blender)

# 5.0 renamed EEVEE Next back to BLENDER_EEVEE (5.0 EEVEE release notes); the _NEXT id is the pre-5.0 fallback
ENGINE_IDS = {"eevee": ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"), "cycles": ("CYCLES",), "workbench": ("BLENDER_WORKBENCH",)}


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


# --- characters (ICW-06; the data comes from blender/characters.py, the mouth shapes from characters.json) ------------------------

SUFFIX = re.compile(r"\.\d{3}$")  # Blender renames a second "MI_Hair_1" to "MI_Hair_1.001"
_ANIM = {}       # GLB path -> {action name: action}: the animation library is imported once per scene
_TEMPLATES = {}  # (character, costume, materials, parts) -> built rig, copied for crowds (meshes shared)


def _import_glb(path):
    """The objects one glTF import adds (the importer's own defaults: blender/assets.py IMPORT_SETTINGS records them)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def _remove(objs):
    for ob in objs:
        bpy.data.objects.remove(ob, do_unlink=True)


def _cut_to_bones(ob, bones, min_weight=0.5):
    """Delete the vertices of ``ob`` that ``bones`` do not carry (summed weight below ``min_weight``): the base body under a
    costume goes, the head and neck stay (no skin pokes through the cloth)."""
    import bmesh
    idx = {g.index for g in ob.vertex_groups if g.name in bones}
    if not idx:
        raise RuntimeError(f"{ob.name}: none of the bones {bones} weights this mesh")
    drop = [v.index for v in ob.data.vertices if sum(g.weight for g in v.groups if g.group in idx) < min_weight]
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in drop], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    return len(drop)


def _smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def _mouth_keys(ob, mouth):
    """The eight Rhubarb mouth shapes (A-H) and the rest (X) as shape keys on the head mesh: each shape is an opening of the
    jaw region below the lip line, a widening or a rounding of the lips, weighted by a smooth falloff around the mouth
    centre (object space of the rest pose). The shape table is data (characters.json, ``mouth.shapes``)."""
    mw = ob.matrix_world.copy()
    back = mw.inverted().to_3x3()
    c = Vector(mouth["center"])
    r, jaw_r = mouth["radius_m"], mouth["jaw_radius_m"]
    drop, lift = mouth["open_drop_m"], mouth["open_lift_m"]
    if ob.data.shape_keys is None:
        ob.shape_key_add(name="Basis", from_mix=False)
    basis = [v.co.copy() for v in ob.data.vertices]
    world = [mw @ co for co in basis]
    made = []
    for name, sh in sorted(mouth["shapes"].items()):
        kb = ob.shape_key_add(name=mouth["keys"][name], from_mix=False)
        for i, co in enumerate(basis):
            d = world[i] - c
            if d.y > mouth["front_y_m"]:   # the back of the head never moves (the face looks along -Y)
                continue
            w = 1.0 - _smooth(math.hypot(d.x, d.z) / r)
            wj = 1.0 - _smooth(math.hypot(d.x * 0.8, d.z) / jaw_r)
            if w <= 0 and wj <= 0:
                continue
            below = d.z < 0
            dz = -sh["open"] * drop * max(wj, 0.0) if below else sh["open"] * lift * max(w, 0.0)
            dx = d.x * (sh["wide"] - sh["round"]) * mouth["wide_gain"] * max(w, 0.0)
            dy = -sh["round"] * mouth["round_push_m"] * max(w, 0.0)
            kb.data[i].co = co + back @ Vector((dx, dy, dz))
        kb.value = 0.0
        made.append(kb.name)
    return made


def _mouth_opening(arm, mouth, mat_name, pending):
    """The open mouth as a drawn shape (the UBC head's lips are one closed surface, so the jaw shape keys stretch the face but
    cannot part the lips): a thin dark lens on the lip line, riding the Head bone, with one shape key per mouth shape (width
    from ``wide``/``round``, height from ``open``, sunk to the middle of the jaw drop). Closed shapes (A, X) shrink it to a
    sliver hidden under the line art. Line Art draws its outline, like an inked mouth."""
    import bmesh
    c = Vector(mouth["center"]) + Vector(mouth["opening_offset_m"])
    w0, t = mouth["opening_half_width_m"], mouth["opening_depth_m"]
    me = bpy.data.meshes.new(f"{arm.name}_mouth")
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=10, radius=1.0)
    bm.to_mesh(me)
    bm.free()
    unit = [v.co.copy() for v in me.vertices]
    closed = mouth["opening_closed_m"]

    def shape(sh):
        hw = w0 * (1.0 + (sh["wide"] - sh["round"]) * mouth["wide_gain"] * 1.6)
        hh = max(sh["open"] * mouth["open_drop_m"] * mouth["opening_height_share"], closed)
        dz = -sh["open"] * mouth["open_drop_m"] * 0.45
        return [Vector((u.x * hw, u.y * t, u.z * hh + dz * (1 - abs(u.x) * 0.15))) for u in unit]
    rest = shape(mouth["shapes"][mouth.get("rest", "X")])
    for v, co in zip(me.vertices, rest):
        v.co = co
    ob = bpy.data.objects.new(f"{arm.name}_mouth", me)
    bpy.context.scene.collection.objects.link(ob)
    ob.shape_key_add(name="Basis", from_mix=False)
    for name, sh in sorted(mouth["shapes"].items()):
        kb = ob.shape_key_add(name=mouth["keys"][name], from_mix=False)
        for i, co in enumerate(shape(sh)):
            kb.data[i].co = co - rest[i] + me.vertices[i].co
        kb.value = 0.0
    bone = arm.data.bones[mouth["bone"]]
    ob.parent = arm
    ob.parent_type = "BONE"
    ob.parent_bone = mouth["bone"]
    from mathutils import Matrix  # Blender's own; imported here so the fake-bpy tests load this file
    ob.matrix_world = arm.matrix_world @ Matrix.Translation(c)
    pending.append(([ob], mat_name, True))
    return ob


def _actions(path):
    if path not in _ANIM:
        new = _import_glb(path)
        acts = {}
        for a in bpy.data.actions:
            if a.name not in acts:
                a.use_fake_user = True
                acts[SUFFIX.sub("", a.name)] = a
        _remove(new)
        _ANIM[path] = acts
    return _ANIM[path]


def _play(arm, anim, frames_total, report):
    """The clip on the rig as one NLA strip repeated over the shot; ``offset`` shifts the cycle (a crowd never steps in sync)."""
    acts = _actions(anim["path"])
    act = acts.get(anim["action"])
    if act is None:
        raise RuntimeError(f"no action {anim['action']!r} in {os.path.basename(anim['path'])} (have {sorted(acts)[:12]}...)")
    ad = arm.animation_data_create()
    ad.action = None
    track = ad.nla_tracks.new()
    start = bpy.context.scene.frame_start - int(anim.get("offset", 0))
    strip = track.strips.new(anim["action"], start, act)
    if hasattr(strip, "action_slot") and act.slots:
        strip.action_slot = act.slots[0]
    length = max(act.frame_range[1] - act.frame_range[0], 1.0)
    speed = float(anim.get("speed", 1.0))   # < 1 slows the clip; a turnaround holds a pose with a tiny speed
    strip.scale = 1.0 / speed
    strip.repeat = max(1.0, math.ceil((frames_total + int(anim.get("offset", 0)) + 1) * speed / length))
    report.setdefault("actions", {})[arm.name] = {"action": anim["action"], "frames": round(length, 3), "offset": int(anim.get("offset", 0))}


def _lipsync(head, lip, report):
    """Rhubarb tracks (rigs.LipSync.plan: shape-key name -> [[frame, value], ...]) keyed on the head's shape keys."""
    meshes = [head] + ([bpy.data.objects[head["mouth_opening"]]] if head.get("mouth_opening") else [])
    n = 0
    for me in meshes:
        keys = me.data.shape_keys.key_blocks
        for name, pts in lip["tracks"].items():
            if name not in keys:
                raise RuntimeError(f"lip sync names the shape key {name!r}; {me.name} has {[k.name for k in keys]}")
            kb = keys[name]
            for f, v in pts:
                kb.value = v
                kb.keyframe_insert("value", frame=bpy.context.scene.frame_start + int(f))
                n += 1
    report.setdefault("lipsync", {})[head.name] = {"keys": n, "shapes": sorted(lip["tracks"])}


def _assemble(o, pending, report):
    """Import the parts, merge them onto the first part's armature (one 65-bone UBC skeleton), cut the base body to its head,
    build the mouth, assign the slot materials. Returns (armature, meshes, head mesh)."""
    ch = o["character"]
    arm, meshes, head = None, [], None
    for k, part in enumerate(ch["parts"]):
        new = _import_glb(part["path"])
        rigs = [x for x in new if x.type == "ARMATURE"]
        if len(rigs) != 1:
            raise RuntimeError(f"{part['path']}: {len(rigs)} armatures (one expected)")
        drop = set(part.get("drop", []))
        part_meshes = []
        for x in new:
            if x.type != "MESH":
                continue
            mods = [m for m in x.modifiers if m.type == "ARMATURE"]
            if not mods or x.name in drop or SUFFIX.sub("", x.name) in drop:
                bpy.data.objects.remove(x, do_unlink=True)   # the importer's stray Icosphere, or a part left out (a hood)
                continue
            part_meshes.append(x)
        if arm is None:
            arm = rigs[0]
            arm.name = f"{o['name']}_rig"
        else:
            for x in part_meshes:
                mw = x.matrix_world.copy()
                x.parent = arm
                x.matrix_world = mw
                for m in x.modifiers:
                    if m.type == "ARMATURE":
                        m.object = arm
            bpy.data.objects.remove(rigs[0], do_unlink=True)
        if part.get("keep_bones"):
            body = max(part_meshes, key=lambda x: len(x.data.vertices))
            report.setdefault("cut", {})[o["name"]] = _cut_to_bones(body, part["keep_bones"])
            head = body
        meshes += part_meshes
    for x in meshes:
        slots = {}
        for i, ms in enumerate(x.material_slots):
            base = SUFFIX.sub("", ms.material.name) if ms.material else None
            if base not in ch["materials"]:
                raise RuntimeError(f"{x.name}: material {base!r} has no toon material in the character's map")
            slots[i] = ch["materials"][base]
        pending.append(([x], slots, True))
    if head is not None and ch.get("mouth"):
        report.setdefault("mouth", {})[o["name"]] = _mouth_keys(head, ch["mouth"])
        opening = _mouth_opening(arm, ch["mouth"], ch["mouth"]["interior_material"], pending)
        head["mouth_opening"] = opening.name
    return arm, meshes, head


def _copy_rig(src_arm, src_meshes, name, pending, slots_of):
    """A crowd member: a new armature (its own pose and clip) over the same mesh data."""
    arm = src_arm.copy()
    arm.data = src_arm.data
    arm.animation_data_clear()
    arm.name = f"{name}_rig"
    bpy.context.scene.collection.objects.link(arm)
    meshes = []
    for x in src_meshes:
        y = x.copy()
        bpy.context.scene.collection.objects.link(y)
        y.parent = arm
        for m in y.modifiers:
            if m.type == "ARMATURE":
                m.object = arm
        meshes.append(y)
        pending.append(([y], slots_of[x.name], True))
    return arm, meshes


def build_character(o, frames_total, pending, report):
    """One cast member under an empty named ``o['name']`` (placed and moved like any described object). A rig without lip
    sync is built once per (character, costume, materials) and copied for the next crowd member."""
    ch = o["character"]
    key = json.dumps([ch["id"], ch["costume"], ch["materials"], ch["parts"], ch.get("mouth")], sort_keys=True)
    root = bpy.data.objects.new(o["name"], None)
    bpy.context.scene.collection.objects.link(root)
    if ch.get("lipsync") or key not in _TEMPLATES:
        start = len(pending)
        arm, meshes, head = _assemble(o, pending, report)
        if not ch.get("lipsync"):
            _TEMPLATES[key] = (arm, meshes, {x.name: s for (obs, s, _) in pending[start:] for x in obs if isinstance(s, dict)})
    else:
        src_arm, src_meshes, slots_of = _TEMPLATES[key]
        arm, meshes = _copy_rig(src_arm, src_meshes, o["name"], pending, slots_of)
        head = None
    arm.parent = root
    if ch.get("animation"):
        _play(arm, ch["animation"], frames_total, report)
    if ch.get("lipsync"):
        if head is None:
            raise RuntimeError(f"{o['name']}: lip sync needs the head mesh")
        _lipsync(head, ch["lipsync"], report)
    report.setdefault("characters", {})[o["name"]] = {"id": ch["id"], "costume": ch["costume"], "assets": ch["assets"],
                                                      "meshes": len(meshes), "bones": len(arm.data.bones)}
    _place(root, o)
    return root


def _tracked(scene, frame, tr, loc, at):
    """``loc``/``at`` are given in the rest pose; both are carried by the bone (``track``: {rig, bone}) from its rest frame to its
    posed frame at ``frame``."""
    arm = bpy.data.objects[tr["rig"]]
    scene.frame_set(frame)
    bpy.context.view_layer.update()
    rest = arm.matrix_world @ arm.data.bones[tr["bone"]].matrix_local
    posed = arm.matrix_world @ arm.pose.bones[tr["bone"]].matrix
    carry = posed @ rest.inverted()   # the camera rides rigidly with the bone: a close-up stays frontal when the head tilts
    return list(carry @ Vector(loc)), list(carry @ Vector(at))


# --- camera rigs (WP-Q7): the Add Camera Rigs extension, installed from the pinned zip and keyed with the engine's camera path ----

RIG = {}   # {"rig": armature object, "camera": camera object} when the camera is a rig


def install_extension(path, report):
    """The pinned Add Camera Rigs zip into this Blender (a user repository, enabled), once per process."""
    if "bl_ext.user_default.add_camera_rigs" in bpy.context.preferences.addons:
        return
    res = bpy.ops.extensions.package_install_files(filepath=path, repo="user_default", enable_on_install=True)
    if "FINISHED" not in res:
        raise RuntimeError(f"the camera rig extension {path} did not install: {res}")
    report["camera_rig_extension"] = os.path.basename(path)


def _bone_world(rig, name, world):
    """The pose bone ``name`` on the world point (parents first: the caller updates the view layer between bones)."""
    from mathutils import Matrix
    rig.pose.bones[name].matrix = rig.matrix_world.inverted() @ Matrix.Translation(Vector(world))
    bpy.context.view_layer.update()


def build_rig(scene, cam, report):
    """The camera of a described scene as a Dolly or Crane rig of the extension: its camera object becomes ``scene.camera``,
    its lens, aperture and focus are the rig's bone properties (drivers feed them to the camera data)."""
    install_extension(cam["extension"], report)
    kind = cam["rig_kind"].upper()
    bpy.ops.object.build_camera_rig(mode=kind)
    rig = bpy.data.objects[kind.capitalize() + "_Rig"]
    ob = bpy.data.objects[kind.capitalize() + "_Camera"]
    ob.name = "camera"
    ob.data.sensor_width, ob.data.clip_end = cam.get("sensor_mm", 36.0), cam.get("clip_end", 500.0)
    scene.camera = ob
    pb = rig.pose.bones["Camera"]
    pb["lens"] = float(cam["lens_mm"])
    RIG.update(rig=rig, camera=ob)
    return rig, ob


def set_dof(scene, focus_m, fstop):
    """The depth of field of the scene camera: through the rig's properties when it is a rig, else on the camera data."""
    cd = scene.camera.data.dof
    cd.use_dof = True
    if RIG:
        pb = RIG["rig"].pose.bones["Camera"]
        pb["focus_distance"], pb["aperture_fstop"] = float(focus_m), float(fstop)
    else:
        cd.focus_distance, cd.aperture_fstop = focus_m, fstop


def key_rig(scene, cam, first, last, interp):
    """The engine's camera keys on the rig: Root under the camera on the floor, the Camera bone at the camera, Aim at the look-at
    point; the focus distance follows ``focus_at`` and the aperture holds ``fstop``."""
    rig = RIG["rig"]
    pbs = rig.pose.bones
    keys = cam.get("keys") or [{"frame": 0, "location": cam["location"], "look_at": cam["look_at"]}]
    bpy.context.preferences.edit.keyframe_new_interpolation_type = interp
    for k in keys:
        loc, at = k["location"], k["look_at"]
        frame = first + int(k["frame"])
        pbs["Root"].location = (loc[0], loc[1], 0.0)
        bpy.context.view_layer.update()
        _bone_world(rig, "Aim", at)
        _bone_world(rig, "Camera", loc)
        for name in ("Root", "Aim", "Camera"):
            pbs[name].keyframe_insert("location", frame=frame)
        # a property the job names is keyed (the focus follows ``focus_at``, the aperture holds ``fstop``); one it does not name
        # stays the style's (apply_style -> set_dof writes it later)
        if cam.get("focus_at"):
            pbs["Camera"]["focus_distance"] = float((Vector(cam["focus_at"]) - Vector(loc)).length)
            pbs["Camera"].keyframe_insert('["focus_distance"]', frame=frame)
        if cam.get("fstop") is not None:
            pbs["Camera"]["aperture_fstop"] = float(cam["fstop"])
            pbs["Camera"].keyframe_insert('["aperture_fstop"]', frame=frame)
    scene.frame_set(first)


def frame_probe(scene, cam, first, last, report):
    """Where the probe points land in the frame at the first and the last frame (0..1 from the left / bottom; the bpy side of
    ``camera_setups.framing``): the CI cross-check of the pure-Python pinhole."""
    from bpy_extras.object_utils import world_to_camera_view
    out = {}
    for f in sorted({first, last}):
        scene.frame_set(f)
        out[str(f - first)] = {p["name"]: [round(v, 5) for v in world_to_camera_view(scene, scene.camera, Vector(p["at"]))[:2]]
                               for p in cam["probe"]}
    scene.frame_set(first)
    report["framing"] = out


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
        elif "character" in o:
            handle = build_character(o, int(sc.get("frames_total", 1)), pending, report)
            if o.get("to"):
                moving.append((handle, o))
            continue
        else:
            raise RuntimeError(f"object {o.get('name')!r}: neither add, append nor character")
        pending.append((obs, o.get("material"), o.get("smooth")))
        if o.get("to"):
            moving.append((handle, o))
    cam = sc["camera"]
    if cam.get("rig_kind"):
        build_rig(scene, cam, report)
        ob, data = scene.camera, scene.camera.data
        data.lens = cam["lens_mm"]
    else:
        RIG.clear()
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
        if cam.get("to") and RIG:
            raise RuntimeError("a camera rig is keyed from camera.keys, not from a to block")
        if cam.get("to"):
            _key(ob, ("location", "rotation_euler"), first, cam.get("interp", "BEZIER"))
            _aim(ob, cam["to"]["location"], cam["to"]["look_at"], ob.rotation_euler.copy())
            _key(ob, ("location", "rotation_euler"), last, cam.get("interp", "BEZIER"))
        if cam.get("keys") and not RIG:   # a camera path of several poses (scene_builder: rail, orbit, dramatic curve; a turnaround's views)
            for k in cam["keys"]:
                loc, at = k["location"], k["look_at"]
                if k.get("track"):   # aim at a point of a posed bone (a face close-up follows the head the clip moves)
                    loc, at = _tracked(scene, first + int(k["frame"]), k["track"], loc, at)
                _aim(ob, loc, at, ob.rotation_euler.copy())
                if "lens_mm" in k:
                    data.lens = k["lens_mm"]
                    data.keyframe_insert("lens", frame=first + int(k["frame"]))
                _key(ob, ("location", "rotation_euler"), first + int(k["frame"]), cam.get("interp", "BEZIER"))
        report["motion"] = {"frames": [first, last], "objects": len(moving), "camera": bool(cam.get("to") or cam.get("keys"))}
    if RIG:
        key_rig(scene, cam, first, last, cam.get("interp", "LINEAR"))
        report["camera_rig"] = {"kind": cam["rig_kind"], "rig": RIG["rig"].name, "bones": sorted(b.name for b in RIG["rig"].pose.bones)}
    if cam.get("probe"):
        frame_probe(scene, cam, first, last, report)
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


def _camera_aim(scene, elevation_deg, azimuth_offset_deg, front=False):
    """A sun rotation whose light travels from behind the subject towards the camera (seen at the shot's first frame), coming
    down at ``elevation_deg`` and turned ``azimuth_offset_deg`` to the side: the film rim cheat, the same for every shot.
    ``front``: the light travels the camera's way instead (from the camera's side onto the faces: the front-biased key and the
    skin lifts)."""
    scene.frame_set(scene.frame_start)
    fwd = scene.camera.matrix_world.to_3x3() @ Vector((0.0, 0.0, -1.0))
    flat = Vector((fwd.x, fwd.y, 0.0))
    if flat.length < 1e-6:
        flat = Vector((0.0, 1.0, 0.0))
    flat.normalize()
    az = math.radians(azimuth_offset_deg)
    toward = Vector((-flat.x * math.cos(az) + flat.y * math.sin(az), -flat.y * math.cos(az) - flat.x * math.sin(az), 0.0))
    if front:
        toward = -toward
    el = math.radians(elevation_deg)
    travel = Vector((toward.x * math.cos(el), toward.y * math.cos(el), -math.sin(el)))
    return travel.to_track_quat("-Z", "Y").to_euler()


def build_lights(scene, specs, cast, missing, by_char=None):
    """The WP-Q1 rig: each light as listed; ``link: "cast"`` light-links it to the character meshes only (Blender 5.2
    ``Object.light_linking.receiver_collection``; a rim with no cast in the shot is left out and reported); ``link:
    "char:<id>"`` to that character's meshes (a skin lift). ``aim_with_cast`` turns the key to the camera's side when a cast is
    in the shot (the front-biased key)."""
    done = []
    by_char = by_char or {}
    for lt in specs:
        link = lt.get("link")
        receivers = cast if link == "cast" else by_char.get(link[5:], []) if link and link.startswith("char:") else None
        if link and not receivers:
            done.append({"name": lt["name"], "skipped": "no cast in the shot" if link == "cast" else f"no {link[5:]} in the shot"})
            continue
        data = bpy.data.lights.new(lt["name"], lt["type"])
        data.energy, data.color, data.use_shadow = lt["energy"], lt["color"], lt["use_shadow"]
        for k in ("angle_rad", "shadow_filter_radius", "use_shadow_jitter", "specular_factor", "diffuse_factor"):
            if lt.get(k) is None:
                continue
            attr = "angle" if k == "angle_rad" else k
            if hasattr(data, attr):
                setattr(data, attr, lt[k])
            else:
                missing.append(f"light {lt['name']}.{attr}")
        ob = bpy.data.objects.new(lt["name"], data)
        scene.collection.objects.link(ob)
        aim = lt.get("aim") or (lt.get("aim_with_cast") if cast else None)
        if aim:
            ob.rotation_euler = _camera_aim(scene, aim["elevation_deg"], aim["azimuth_offset_deg"], aim.get("from") == "front")
        else:
            ob.rotation_euler = lt["rotation_euler"]
        row = {"name": lt["name"], "energy": data.energy, "shadow": data.use_shadow}
        if aim and "aim_with_cast" in lt:
            row["front_offset_deg"] = aim["azimuth_offset_deg"]
        if link:
            coll = bpy.data.collections.new(f"{lt['name']}_receivers")
            for m in receivers:
                coll.objects.link(m)
            ob.light_linking.receiver_collection = coll
            row["receivers"] = len(coll.objects)
        done.append(row)
    return done


def _gn_inputs(mod, values):
    """Set a Geometry Nodes modifier's inputs by socket name (Blender 5.2 keeps them in ``modifier.properties.inputs``)."""
    for it in mod.node_group.interface.items_tree:
        if getattr(it, "in_out", "") == "INPUT" and it.name in values:
            mod.properties.inputs[it.identifier]["value"] = values[it.name]


def perfectly_normal(meshes, spec, missing):
    """C4's faces: Perfectly Normal 0.0.3 (Seth Trowbridge, GPL-3.0-or-later, extensions.blender.org) used as data, its four GN
    groups appended from the extension's own ``assets/perfectly_normal.blend`` (no add-on code runs). On each cast mesh, after the
    armature: Manip Verts (Re)create -> Tweak (Converge = spherize the corner normals) -> Apply (Ready to Apply). The file comes
    from ``$EE_PERFECTLY_NORMAL_BLEND`` (the unpacked extension; sha256 of the zip in docs/PROVENANCE.md)."""
    path = os.environ.get("EE_PERFECTLY_NORMAL_BLEND", "")
    if not path or not os.path.exists(path):
        missing.append("perfectly_normal: EE_PERFECTLY_NORMAL_BLEND is not set to the extension's perfectly_normal.blend")
        return 0
    names = ("Manip Verts: (Re)create", "Manip Verts: Tweak", "Manip Verts: Apply")
    if not all(n in bpy.data.node_groups for n in names):
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.node_groups = [n for n in src.node_groups if n.startswith("Manip Verts") or n == "Perform Tweak"]
    # PN's Converge pulls each face's manip verts towards the face (a positive share turns the normals inward: measured on a UV
    # sphere in 5.2.3, mean dot with the outward normal 0.971 flat, -0.911 at +0.6, the C4 cast rendered black); a negative share
    # pushes them out of the face, i.e. spherizes (0.984 at -0.6). The look's pn_converge is that outward share.
    steps = ((names[0], {}), (names[1], {"Converge": -float(spec["converge"])}), (names[2], {"Ready to Apply": True}))
    keep, restore = _material_index_guard()
    for ob in meshes:
        # the kit's glTF meshes carry imported custom normals: PN on top of them wrote black faces (C4's first frames), so the
        # cast starts from plain smooth normals (custom ones cleared, shade smooth)
        me = ob.data
        if getattr(me, "has_custom_normals", False):
            with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
                bpy.ops.mesh.customdata_custom_splitnormals_clear()
        if hasattr(me, "shade_smooth"):
            me.shade_smooth()
        ob.modifiers.new("pn_keep_material_index", "NODES").node_group = keep
        for name, values in steps:
            g = bpy.data.node_groups[name]
            g.is_modifier = True
            mod = ob.modifiers.new(f"pn_{name.split(': ')[1].strip('()').lower()}", "NODES")
            mod.node_group = g
            _gn_inputs(mod, values)
        ob.modifiers.new("pn_restore_material_index", "NODES").node_group = restore
    return len(meshes)


def _material_index_guard():
    """PN 0.0.3's rebuild shifts every face's material index by one (measured in 5.2.3: [0, 1] -> [1, 2]; the kit cast rendered
    in the wrong slots, black). Two small GN groups keep it: the index stored as a face attribute before PN, set back after."""
    made = []
    for gname in ("wpq1_pn_keep_matidx", "wpq1_pn_restore_matidx"):
        ng = bpy.data.node_groups.get(gname)
        if ng is None:
            ng = bpy.data.node_groups.new(gname, "GeometryNodeTree")
            ng.is_modifier = True
            ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
            ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
            gin, gout = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
            if gname.endswith("keep_matidx"):
                st, idx = ng.nodes.new("GeometryNodeStoreNamedAttribute"), ng.nodes.new("GeometryNodeInputMaterialIndex")
                st.data_type, st.domain = "INT", "FACE"
                st.inputs["Name"].default_value = "ee_material_index"
                ng.links.new(gin.outputs[0], st.inputs["Geometry"])
                ng.links.new(idx.outputs[0], st.inputs["Value"])
                ng.links.new(st.outputs["Geometry"], gout.inputs[0])
            else:
                na, sm = ng.nodes.new("GeometryNodeInputNamedAttribute"), ng.nodes.new("GeometryNodeSetMaterialIndex")
                na.data_type = "INT"
                na.inputs["Name"].default_value = "ee_material_index"
                ng.links.new(gin.outputs[0], sm.inputs["Geometry"])
                ng.links.new(na.outputs["Attribute"], sm.inputs["Material Index"])
                ng.links.new(sm.outputs["Geometry"], gout.inputs[0])
        made.append(ng)
    return made


def soften_normals(meshes, iterations, missing):
    """Wing It!'s soft faces: a Geometry Nodes modifier after the armature blurs the vertex normals (Blur Attribute on Normal)
    and writes them back as free custom normals (Set Mesh Normal), so the shading reads rounder and flatter than the mesh."""
    ng = bpy.data.node_groups.get("wpq1_soft_normals")
    if ng is None:
        ng = bpy.data.node_groups.new("wpq1_soft_normals", "GeometryNodeTree")
        ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        gin, gout = ng.nodes.new("NodeGroupInput"), ng.nodes.new("NodeGroupOutput")
        nrm, blur, setn = ng.nodes.new("GeometryNodeInputNormal"), ng.nodes.new("GeometryNodeBlurAttribute"), ng.nodes.new("GeometryNodeSetMeshNormal")
        blur.data_type = "FLOAT_VECTOR"
        blur.inputs["Iterations"].default_value = int(iterations)
        setn.mode = "FREE"
        setn.domain = "POINT"
        ng.links.new(nrm.outputs[0], blur.inputs["Value"])
        custom = next((x for x in setn.inputs if x.name in ("Custom Normal", "Normal") and x.enabled), None)
        if custom is None:
            missing.append("GeometryNodeSetMeshNormal.FREE input")
            return
        ng.links.new(gin.outputs[0], setn.inputs["Mesh"])
        ng.links.new(blur.outputs[0], custom)
        ng.links.new(setn.outputs[0], gout.inputs[0])
    for ob in meshes:
        mod = ob.modifiers.new("soft_normals", "NODES")
        mod.node_group = ng


def apply_style(scene, style, pending, report):
    """The style_graph/1 document on the built scene: materials, world, key light, Line Art, paper pass, colour management."""
    missing = []
    mats = {}
    native = 0
    for m in style["materials"]:
        if m.get("native"):   # C2: the slot keeps the asset's own material (Blender Studio SSS skin, cloth) under our lights
            mats[m["name"]] = None
            continue
        mat = bpy.data.materials.new(m["name"])
        build_tree(mat.node_tree, m, missing, f"material {m['name']}")
        mats[m["name"]] = mat
    for obs, name, smooth in pending:
        if isinstance(name, dict):   # a character mesh: material slot index -> toon material name
            for ob in obs:
                for i, mname in name.items():
                    if mname not in mats:
                        raise RuntimeError(f"the style graph has no material {mname!r}")
                    if mats[mname] is None:
                        native += ob.material_slots[int(i)].material is not None
                        continue
                    ob.material_slots[int(i)].link = "OBJECT"
                    ob.material_slots[int(i)].material = mats[mname]
        elif name is not None:
            if name not in mats:
                raise RuntimeError(f"the style graph has no material {name!r}")
            _assign(obs, mats[name], smooth)
    if scene.world is None:
        scene.world = bpy.data.worlds.new("world")
    build_tree(scene.world.node_tree, style["world"], missing, "world")
    cast = [ob for obs, name, _ in pending if isinstance(name, dict) for ob in obs]   # the character meshes
    by_char = {}   # a character's meshes, by the id its slot materials carry ({char}_skin, {char}_hair, ...)
    for obs, name, _ in pending:
        if isinstance(name, dict):
            for who in {m.rsplit("_", 1)[0] for m in name.values() if "_" in m}:
                by_char.setdefault(who, []).extend(ob for ob in obs if ob not in by_char.get(who, []))
    if "lights" in style:   # WP-Q1: real coloured lights (style.StyleEngine.lights); key_light is only their record
        lights_applied = build_lights(scene, style["lights"], cast, missing, by_char)
        fill = None
    else:
        lights_applied = None
        kl = style["key_light"]
        sun = bpy.data.lights.new("key", "SUN")
        sun.energy, sun.angle = kl["energy"], kl["angle_rad"]
        sun.use_shadow = kl.get("use_shadow", True)  # the light profile turns cast shadows off (style.StyleTokens.shadows)
        ob = bpy.data.objects.new("key", sun)
        scene.collection.objects.link(ob)
        ob.rotation_euler = kl["rotation_euler"]
        fill = style.get("fill_light")   # ICW-05c looks: a cool fill from the other side, never a shadow caster
    if style.get("normal_soften"):
        soften_normals(cast, style["normal_soften"]["iterations"], missing)
    pn_done = perfectly_normal(cast, style["perfectly_normal"], missing) if style.get("perfectly_normal") else None
    if fill:
        fl = bpy.data.lights.new("fill", "SUN")
        fl.energy, fl.use_shadow = fill["energy"], fill.get("use_shadow", False)
        fob = bpy.data.objects.new("fill", fl)
        scene.collection.objects.link(fob)
        fob.rotation_euler = fill["rotation_euler"]
    la = style["line_art"]
    mod = None
    if la.get("enabled", True):   # a look without lines has no Line Art at all (and saves its CPU time)
        bpy.ops.object.grease_pencil_add(type="LINEART_SCENE", location=(0, 0, 0))
        gp = bpy.context.active_object
        gp.name = "line_art"
        mod = [m for m in gp.modifiers if m.type == "LINEART"][0]
        mod.radius, mod.crease_threshold, mod.opacity = la["radius"], la["crease_threshold_rad"], la["opacity"]
        for gm in gp.data.materials:
            gm.grease_pencil.color = la["ink_rgba"]
    dof = style.get("camera_dof")
    if dof:
        if RIG:   # WP-Q7: keyed properties of the rig win at render time; the style fills the ones the job did not name
            set_dof(scene, dof["focus_distance_m"], dof["fstop"])
        else:
            cd = scene.camera.data.dof
            cd.use_dof, cd.focus_distance, cd.aperture_fstop = True, dof["focus_distance_m"], dof["fstop"]
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
    applied = {"view_transform": vs.view_transform, "look": vs.look, "line_art_radius": mod.radius if mod else None,
               "crease_threshold": mod.crease_threshold if mod else None}
    if fill:
        applied["fill_light"] = fill["energy"]
    if lights_applied is not None:
        applied["lights"] = lights_applied
    if style.get("normal_soften"):
        applied["normal_soften"] = {"iterations": style["normal_soften"]["iterations"], "meshes": len(cast)}
    if style.get("perfectly_normal"):
        applied["perfectly_normal"] = {"converge": style["perfectly_normal"]["converge"], "meshes": pn_done}
    if style.get("native_classes"):
        applied["native"] = {"classes": style["native_classes"], "slots_kept": native}
    if dof:
        applied["dof_fstop"] = scene.camera.data.dof.aperture_fstop
    for k, v in st.get("eevee", {}).items():
        set_attr(scene.eevee, k, v, applied, missing, f"eevee.{k}")
    for k, v in st.get("cycles", {}).items():
        if hasattr(scene, "cycles"):
            set_attr(scene.cycles, k, v, applied, missing, f"cycles.{k}")
    paper = style["paper"]
    if paper.get("enabled"):
        if "z" in paper.get("passes", []):   # the painted plate mixes by depth
            bpy.context.view_layer.use_pass_z = True
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
        ao = s.get("ambient_occlusion")   # 5.x has no use_gtao: AO is Fast GI in its AO-only method (SceneEEVEE API 5.2)
        set_attr(ee, "use_fast_gi", ao, applied, missing, "eevee.use_fast_gi")
        if ao:
            set_attr(ee, "fast_gi_method", "AMBIENT_OCCLUSION_ONLY", applied, missing, "eevee.fast_gi_method")
        set_attr(ee, "use_shadows", s.get("shadows"), applied, missing, "eevee.use_shadows")
        set_attr(ee, "motion_blur_steps", s.get("motion_blur_steps"), applied, missing, "eevee.motion_blur_steps")
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


def bounds(scene, names):
    """World bounding box of each named top-level object and its mesh descendants, at the shot's first frame."""
    scene.frame_set(scene.frame_start)
    out = []
    for n in names:
        ob = bpy.data.objects.get(n)
        if ob is None:
            continue
        obs = [ob] + list(ob.children_recursive)
        pts = [x.matrix_world @ Vector(c) for x in obs if x.type == "MESH" for c in x.bound_box]
        if not pts:
            continue
        out.append({"object": n, "min": [round(min(p[i] for p in pts), 4) for i in range(3)],
                    "max": [round(max(p[i] for p in pts), 4) for i in range(3)]})
    return out


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
    if sc["kind"] == "described":
        built["bounds"] = bounds(scene, [o["name"] for o in sc["objects"]])
    write_json(job["report"], {
        "blender_version": bpy.app.version_string,
        "build_hash": bpy.app.build_hash.decode("ascii", "replace") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
        "engine_id": scene.render.engine, "applied": applied, "missing": missing, "objects": kinds,
        "frames": len(job["frames"]), "gpu_backend": gpu_backend(), **built,
    })


main()
