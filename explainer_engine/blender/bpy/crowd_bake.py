"""Runs INSIDE Blender, imported by ``render_shot.build_crowd`` (never by the host side): the crowd of a ``described`` scene's
``crowds`` block (``blender/crowd.py``, schema crowd_gn/1; MOTION_RESEARCH.md Group 7, route A + animated yaw billboards).

1. ``bake_clip``: a template (an ordinary cast member playing its UAL clip) is sampled at ``bake_frames`` evenly spaced times of one
   cycle; at each, its deformed meshes are evaluated (``Object.evaluated_get`` + ``BlendData.meshes.new_from_object``, Blender API)
   and joined into ONE mesh in the template's own space (``bmesh.from_mesh`` joins on repeated calls). A Decimate modifier makes the
   T1 copy (``mid_tris`` per soldier). Meshes go into one collection per tier, named so slot k, frame f is child k * N + f.
2. ``bake_atlas``: the T2 billboard atlas. The full meshes of each far template are drawn by an orthographic camera from the shot
   camera's direction and elevation, ``yaw`` copies side by side (copy k turned k x 360/yaw from facing the camera), one render
   per atlas row (frame), in the shot's own look and light, transparent, saved as EXR (scene-linear, so the shot's view transform
   is applied once, at the end).
3. ``build_tree``: the GN modifier ``EE_Crowd`` on one object per tier over the same points mesh (one vertex per soldier with the
   plan's columns as point attributes): Set Position (closed-form advance), the camera distance from Object Info, Instance on
   Points with Pick Instance (index = slot x N + floor(wrap(frame x rate + phase, N))), and for T2 a camera-facing yaw rotation
   and the atlas cell stored as point attributes, read by the quad's material through the Attribute node's Instancer lookup.

The far tier and the far T1 band cast no shadow and every crowd object is excluded from Line Art (Group 7: the costs are moving
shadow casters and Line Art, not the instance count). stdlib + bpy + bmesh + mathutils (+ the numpy Blender ships) only.
"""
import math
import os
import time

import bmesh
import bpy
from mathutils import Matrix, Vector

DUST_NAMES = ("x", "y", "z", "w", "h", "vx", "vy", "seed", "t_in")          # crowd.DUST_COLUMNS
ARROW_NAMES = ("x", "y", "z", "vx", "vy", "vz", "t0", "flight")            # crowd.ARROW_COLUMNS
SMOKE_NAMES = ("x", "y", "z", "phase", "period", "height", "lean", "size0", "size1", "seed")   # crowd.SMOKE_COLUMNS
TIERS_T1 = (("t1_near", True), ("t1_shadow", True), ("t1_far", False))   # near: the full baked meshes; the others the decimated ones


def _tris(me):
    return sum(len(p.vertices) - 2 for p in me.polygons)


def _parts(root):
    meshes = [o for o in root.children_recursive if o.type == "MESH"]
    arms = [o for o in root.children_recursive if o.type == "ARMATURE"]
    if not meshes or len(arms) != 1:
        raise RuntimeError(f"crowd template {root.name}: {len(meshes)} meshes, {len(arms)} armatures (want >= 1 and 1)")
    return arms[0], meshes


def _cycle(arm):
    tr = arm.animation_data.nla_tracks if arm.animation_data else []
    if not tr or not tr[0].strips:
        raise RuntimeError(f"crowd template {arm.name}: no clip on the rig")
    a = tr[0].strips[0].action
    return max(a.frame_range[1] - a.frame_range[0], 1.0), a.name


def _joined(name, meshes, inv, dg):
    bm, mats = bmesh.new(), []
    for ob in meshes:
        me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=False, depsgraph=dg)
        me.transform(inv @ ob.matrix_world)
        off = len(mats)
        mats += [s.material for s in ob.material_slots] or [None]
        n0 = len(bm.faces)
        bm.from_mesh(me)
        bm.faces.ensure_lookup_table()
        if off:
            for f in bm.faces[n0:]:
                f.material_index += off
        bpy.data.meshes.remove(me)
    out = bpy.data.meshes.new(name)
    bm.to_mesh(out)
    bm.free()
    for m in mats:
        out.materials.append(m)
    return out


def _decimated(me, ratio, name):
    if ratio >= 0.999:
        return me
    tmp = bpy.data.objects.new("_crowd_tmp", me)
    bpy.context.scene.collection.objects.link(tmp)
    mod = tmp.modifiers.new("decimate", "DECIMATE")
    mod.ratio = ratio
    dg = bpy.context.evaluated_depsgraph_get()
    out = bpy.data.meshes.new_from_object(tmp.evaluated_get(dg), depsgraph=dg)
    out.name = name
    for i, m in enumerate(me.materials):   # new_from_object keeps the slots; make sure they are the toon materials
        if i < len(out.materials):
            out.materials[i] = m
    bpy.data.objects.remove(tmp, do_unlink=True)
    return out


def bake_clip(scene, root, n, mid_tris):
    """The template's clip as ``n`` full meshes and ``n`` T1 meshes; returns (full, mid, cycle_frames, action, full_tris, mid_tris)."""
    arm, meshes = _parts(root)
    length, action = _cycle(arm)
    inv = root.matrix_world.inverted()
    full = []
    for k in range(n):
        f = scene.frame_start + k * length / n
        scene.frame_set(int(math.floor(f)), subframe=f - math.floor(f))
        dg = bpy.context.evaluated_depsgraph_get()
        full.append(_joined(f"{root.name}_full_{k:04d}", meshes, inv, dg))
    t_full = _tris(full[0])
    ratio = min(1.0, mid_tris / max(t_full, 1))
    mid = [_decimated(full[k], ratio, f"{root.name}_mid_{k:04d}") for k in range(n)]
    return full, mid, length, action, t_full, _tris(mid[0])


def _collection(name, meshes_by_slot):
    """Children named ``<name>_<slot>_<frame>`` and linked in that order: Pick Instance child k * N + f either way."""
    col = bpy.data.collections.new(name)
    col.lineart_usage = "EXCLUDE"
    for slot, mesh_list in meshes_by_slot:
        for f, me in enumerate(mesh_list):
            ob = bpy.data.objects.new(f"{name}_{slot:03d}_{f:04d}", me)
            col.objects.link(ob)
    return col


def bake_atlas(scene, far_meshes, n, atlas, centre, workdir):
    """The T2 atlas image: ``far_meshes`` = [(far_slot, [n full meshes])]. One render per (far slot, atlas frame) of ``yaw`` copies
    side by side. Returns (image, info)."""
    import numpy as np
    yaw_n, frames = atlas["yaw"], atlas["frames"]
    cw, ch = atlas["cell_px"]
    mw, mh = atlas["cell_m"]
    cam = scene.camera
    cpos = cam.matrix_world.translation.copy()
    d = Vector((cpos.x - centre[0], cpos.y - centre[1], 0.0))
    horiz = max(d.length, 1e-3)
    elev = math.atan2(cpos.z, horiz)
    phi = math.atan2(-d.x, d.y)            # the facing angle (0 = +Y) that points at the camera
    ce = math.cos(elev)
    base = Vector((0.0, -1200.0, 0.0))      # the bake stage, far from the set (the key light is a sun: position does not matter)
    view = Vector((d.x / horiz * ce, d.y / horiz * ce, math.sin(elev)))
    up = Vector((0, 0, 1))
    right = (-view).cross(up).normalized()
    look = base + Vector((0, 0, (mh / 2 - 0.15) / ce))
    bcd = bpy.data.cameras.new("crowd_atlas_cam")
    bcd.type, bcd.ortho_scale, bcd.clip_end = "ORTHO", mw * yaw_n, 400.0
    bco = bpy.data.objects.new("crowd_atlas_cam", bcd)
    scene.collection.objects.link(bco)
    bco.location = look + view * 120.0
    bco.rotation_euler = (look - bco.location).to_track_quat("-Z", "Y").to_euler()
    copies = []
    for k in range(yaw_n):
        ob = bpy.data.objects.new(f"crowd_atlas_copy_{k}", far_meshes[0][1][0])
        scene.collection.objects.link(ob)
        ob.location = base + right * ((k - (yaw_n - 1) / 2) * mw)
        ob.rotation_euler = (0.0, 0.0, phi + 2 * math.pi * k / yaw_n + math.pi)
        copies.append(ob)
    r = scene.render
    keep = {"camera": scene.camera, "x": r.resolution_x, "y": r.resolution_y, "pct": r.resolution_percentage,
            "transparent": r.film_transparent, "comp": r.use_compositing, "fmt": r.image_settings.file_format,
            "mode": r.image_settings.color_mode, "depth": r.image_settings.color_depth, "path": r.filepath,
            "hidden": {o.name: o.hide_render for o in scene.objects}}
    for o in scene.objects:
        if o.type not in ("LIGHT",) and o not in copies and o is not bco:
            o.hide_render = True
    scene.camera = bco
    r.resolution_x, r.resolution_y, r.resolution_percentage = cw * yaw_n, ch, 100
    r.film_transparent, r.use_compositing = True, False
    r.image_settings.file_format, r.image_settings.color_mode, r.image_settings.color_depth = "OPEN_EXR", "RGBA", "16"
    cols, rows = len(far_meshes) * yaw_n, frames
    W, H = cols * cw, rows * ch
    px = np.zeros((H, W, 4), dtype=np.float32)
    t0 = time.perf_counter()
    try:
        for fs, mesh_list in far_meshes:
            for j in range(frames):
                me = mesh_list[min(n - 1, int(j * n / frames))]
                for ob in copies:
                    ob.data = me
                path = os.path.join(workdir, f"atlas_{fs:02d}_{j:02d}.exr")
                r.filepath = path
                bpy.ops.render.render(write_still=True)
                img = bpy.data.images.load(path)
                a = np.empty(cw * yaw_n * ch * 4, dtype=np.float32)
                img.pixels.foreach_get(a)
                bpy.data.images.remove(img)
                y0 = H - (j + 1) * ch            # bpy pixels run bottom-up; frame 0 is the top row
                px[y0:y0 + ch, fs * yaw_n * cw:(fs + 1) * yaw_n * cw] = a.reshape(ch, cw * yaw_n, 4)
    finally:
        scene.camera = keep["camera"]
        r.resolution_x, r.resolution_y, r.resolution_percentage = keep["x"], keep["y"], keep["pct"]
        r.film_transparent, r.use_compositing = keep["transparent"], keep["comp"]
        r.image_settings.file_format, r.image_settings.color_mode = keep["fmt"], keep["mode"]
        r.image_settings.color_depth, r.filepath = keep["depth"], keep["path"]
        for o in scene.objects:
            if o.name in keep["hidden"]:
                o.hide_render = keep["hidden"][o.name]
        for ob in copies + [bco]:
            bpy.data.objects.remove(ob, do_unlink=True)
    img = bpy.data.images.new("EE_Crowd_atlas", W, H, alpha=True, float_buffer=True)   # scene-linear already
    img.pixels.foreach_set(px.ravel())   # after any colour-space change: changing it reloads the (blank) generated buffer
    img.update()
    img.filepath_raw = os.path.join(workdir, "crowd_atlas.exr")
    img.file_format = "OPEN_EXR"
    img.save()
    img.pack()
    prev = img.copy()   # a small PNG for review (the save applies the scene's view transform to the linear pixels)
    prev.scale(max(1, W // 3), max(1, H // 3))
    prev.filepath_raw, prev.file_format = os.path.join(workdir, "crowd_atlas_preview.png"), "PNG"
    prev.save()
    bpy.data.images.remove(prev)
    cover = float((px[..., 3] > 0.5).mean())
    return img, {"size": [W, H], "cells": [cols, rows], "seconds": round(time.perf_counter() - t0, 2),
                 "renders": len(far_meshes) * frames, "elevation_deg": round(math.degrees(elev), 2),
                 "view_yaw_deg": round(math.degrees(phi), 2), "alpha_cover": round(cover, 4), "file": img.filepath_raw,
                 "preview": os.path.join(workdir, "crowd_atlas_preview.png")}


def _quad(atlas, elev_deg):
    """The billboard: a vertical 1.6 x (2.4 / cos e) m quad facing +Y, feet at the cell's 0.15 m line; u runs right-to-left in x
    because a viewer on +Y sees -X on the right."""
    mw, mh = atlas["cell_m"]
    ce = math.cos(math.radians(elev_deg))
    z0, z1 = -0.15 / ce, (mh - 0.15) / ce
    me = bpy.data.meshes.new("EE_Crowd_quad")
    me.from_pydata([(-mw / 2, 0, z0), (mw / 2, 0, z0), (mw / 2, 0, z1), (-mw / 2, 0, z1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for li, (u, v) in zip(range(4), ((1, 0), (0, 0), (0, 1), (1, 1))):
        uv.data[li].uv = (u, v)
    ob = bpy.data.objects.new("EE_Crowd_quad", me)
    return ob


def _atlas_material(img, cols, rows):
    mat = bpy.data.materials.new("EE_Crowd_billboard")
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    tc = N.new("ShaderNodeTexCoord")
    sep = N.new("ShaderNodeSeparateXYZ")
    L.new(tc.outputs["UV"], sep.inputs[0])
    acol, arow = N.new("ShaderNodeAttribute"), N.new("ShaderNodeAttribute")
    for a, name in ((acol, "atlas_col"), (arow, "atlas_row")):
        a.attribute_type, a.attribute_name = "INSTANCER", name

    def math_node(op, a, b):
        m = N.new("ShaderNodeMath")
        m.operation = op
        for i, v in enumerate((a, b)):
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                L.new(v, m.inputs[i])
        return m.outputs[0]

    u = math_node("DIVIDE", math_node("ADD", sep.outputs["X"], acol.outputs["Fac"]), float(cols))
    v = math_node("SUBTRACT", 1.0, math_node("DIVIDE", math_node("SUBTRACT", math_node("ADD", arow.outputs["Fac"], 1.0),
                                                                    sep.outputs["Y"]), float(rows)))
    comb = N.new("ShaderNodeCombineXYZ")
    L.new(u, comb.inputs["X"])
    L.new(v, comb.inputs["Y"])
    tex = N.new("ShaderNodeTexImage")
    tex.image, tex.interpolation, tex.extension = img, "Linear", "CLIP"
    L.new(comb.outputs[0], tex.inputs["Vector"])
    em, tr, mix = N.new("ShaderNodeEmission"), N.new("ShaderNodeBsdfTransparent"), N.new("ShaderNodeMixShader")
    L.new(tex.outputs["Color"], em.inputs["Color"])
    L.new(tex.outputs["Alpha"], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(em.outputs[0], mix.inputs[2])
    out = N.new("ShaderNodeOutputMaterial")
    L.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "DITHERED"
    return mat


def _points(name, block, rates):
    p = block["points"]
    n = block["count"]
    me = bpy.data.meshes.new(name)
    me.from_pydata([(p["x"][i], p["y"][i], 0.0) for i in range(n)], [], [])
    cols = {"yaw": p["yaw"], "slot": [float(s) for s in p["slot"]], "far_slot": [float(s) for s in p["far_slot"]],
            "phase": p["phase"], "rate": [p["speed"][i] * rates[p["slot"][i]] for i in range(n)], "vx": p["vx"], "vy": p["vy"],
            "delay": p["delay"], "banner": [float(b) for b in p["banner"]], "stop": p["stop"],
            "slot2": [float(s) for s in p["slot2"]], "far_slot2": [float(s) for s in p["far_slot2"]], "switch": p["switch"],
            "rate2": [p["speed"][i] * rates[p["slot2"][i]] for i in range(n)]}
    for k, vals in cols.items():
        at = me.attributes.new(k, "FLOAT", "POINT")
        at.data.foreach_set("value", [float(v) for v in vals])
    return me


class _Tree:
    """A small builder over one Geometry Nodes group (sockets found by name, so a renamed socket fails loudly)."""

    def __init__(self, name):
        self.ng = bpy.data.node_groups.new(name, "GeometryNodeTree")
        self.ng.interface.new_socket("Geometry", in_out="INPUT", socket_type="NodeSocketGeometry")
        self.ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
        self.gin = self.node("NodeGroupInput")
        self.gout = self.node("NodeGroupOutput")

    def node(self, kind, **props):
        n = self.ng.nodes.new(kind)
        for k, v in props.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.ng.links.new(a, b)

    @staticmethod
    def sock(coll, name):
        for s in coll:
            if s.name == name and s.enabled:
                return s
        for s in coll:
            if s.name == name:
                return s
        raise RuntimeError(f"no socket {name!r} (have {[s.name for s in coll]})")

    def val(self, node, name, v):
        s = self.sock(node.inputs, name) if isinstance(name, str) else node.inputs[name]
        if isinstance(v, bpy.types.NodeSocket):
            self.link(v, s)
        else:
            s.default_value = v

    def attr(self, name):
        n = self.node("GeometryNodeInputNamedAttribute", data_type="FLOAT")
        self.sock(n.inputs, "Name").default_value = name
        return self.sock(n.outputs, "Attribute")

    def math(self, op, a, b=None, c=None):
        n = self.node("ShaderNodeMath", operation=op)
        for i, v in enumerate((a, b, c)):
            if v is not None:
                self.val(n, i, v)
        return n.outputs[0]

    def vmath(self, op, a, b):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self.val(n, 0, a)
        self.val(n, 1, b)
        return n.outputs["Value"] if op in ("DISTANCE", "LENGTH", "DOT_PRODUCT") else n.outputs["Vector"]

    def xyz(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for k, v in zip("XYZ", (x, y, z)):
            self.val(n, k, v)
        return n.outputs[0]

    def sep(self, v):
        n = self.node("ShaderNodeSeparateXYZ")
        self.val(n, 0, v)
        return n.outputs

    def compare(self, op, a, b):
        n = self.node("FunctionNodeCompare", data_type="FLOAT", operation=op)
        self.val(n, "A", a)
        self.val(n, "B", b)
        return self.sock(n.outputs, "Result")

    def band(self, a, b):
        n = self.node("FunctionNodeBooleanMath", operation="AND")
        self.val(n, 0, a)
        self.val(n, 1, b)
        return n.outputs[0]


def _common(t, cam, dmin, dmax):
    """Set Position (closed-form advance), the camera distance and the tier's selection; returns (geometry, selection, pos, camloc)."""
    st = t.node("GeometryNodeInputSceneTime")
    secs = t.sock(st.outputs, "Seconds")
    walk = t.math("MINIMUM", t.math("MAXIMUM", t.math("SUBTRACT", secs, t.attr("delay")), 0.0), t.attr("stop"))   # stops at the clash
    off = t.xyz(t.math("MULTIPLY", t.attr("vx"), walk), t.math("MULTIPLY", t.attr("vy"), walk), 0.0)
    sp = t.node("GeometryNodeSetPosition")
    t.link(t.gin.outputs[0], t.sock(sp.inputs, "Geometry"))
    t.val(sp, "Offset", off)
    oi = t.node("GeometryNodeObjectInfo", transform_space="RELATIVE")
    t.sock(oi.inputs, "Object").default_value = cam
    camloc = t.sock(oi.outputs, "Location")
    pos = t.sock(t.node("GeometryNodeInputPosition").outputs, "Position")
    dist = t.vmath("DISTANCE", pos, camloc)
    sel = t.band(t.compare("GREATER_EQUAL", dist, dmin), t.compare("LESS_THAN", dist, dmax))
    return t.sock(sp.outputs, "Geometry"), sel, pos, camloc, t.sock(st.outputs, "Frame")


def _instance(t, geom, sel, instance, rot_z, *, pick=None, scale=None, rotation=None):
    if rotation is None:
        eu = t.node("FunctionNodeEulerToRotation")
        t.val(eu, "Euler", t.xyz(0.0, 0.0, rot_z))
        rotation = t.sock(eu.outputs, "Rotation")
    iop = t.node("GeometryNodeInstanceOnPoints")
    t.link(geom, t.sock(iop.inputs, "Points"))
    t.val(iop, "Selection", sel)
    t.link(instance, t.sock(iop.inputs, "Instance"))
    t.link(rotation, t.sock(iop.inputs, "Rotation"))
    if scale is not None:
        t.val(iop, "Scale", scale)
    if pick is not None:
        t.sock(iop.inputs, "Pick Instance").default_value = True
        t.val(iop, "Instance Index", pick)
    t.link(t.sock(iop.outputs, "Instances"), t.gout.inputs[0])


def _frame_t(t, frame, n, rate=None):
    rate = t.attr("rate") if rate is None else rate
    return t.math("WRAP", t.math("ADD", t.math("MULTIPLY", frame, rate), t.attr("phase")), float(n), 0.0)


def _switched(t, a, b):
    """``a`` before the soldier's clip switch, ``b`` from it on (the shot time against the ``switch`` column; closed form)."""
    st = t.node("GeometryNodeInputSceneTime")
    on = t.compare("GREATER_EQUAL", t.sock(st.outputs, "Seconds"), t.attr("switch"))
    return t.math("ADD", t.attr(a), t.math("MULTIPLY", t.math("SUBTRACT", t.attr(b), t.attr(a)), on))


def tree_t1(name, cam, col, n, dmin, dmax):
    t = _Tree(name)
    geom, sel, _, _, frame = _common(t, cam, dmin, dmax)
    ci = t.node("GeometryNodeCollectionInfo", transform_space="ORIGINAL")
    t.sock(ci.inputs, "Collection").default_value = col
    t.sock(ci.inputs, "Separate Children").default_value = True
    t.sock(ci.inputs, "Reset Children").default_value = True
    idx = t.math("ADD", t.math("MULTIPLY", _switched(t, "slot", "slot2"), float(n)),
                 t.math("FLOOR", _frame_t(t, frame, n, _switched(t, "rate", "rate2"))))
    rot = t.math("ADD", t.math("RADIANS", t.attr("yaw")), math.pi)
    _instance(t, geom, sel, ci.outputs[0], rot, pick=idx)
    return t.ng


def tree_t2(name, cam, quad, n, atlas, dmin):
    t = _Tree(name)
    geom, sel, pos, camloc, frame = _common(t, cam, dmin, 1.0e9)
    dx, dy, _ = t.sep(t.vmath("SUBTRACT", camloc, pos))[:3]
    theta = t.math("ARCTAN2", t.math("MULTIPLY", dx, -1.0), dy)             # the facing angle pointing at the camera
    rel = t.math("SUBTRACT", t.math("RADIANS", t.attr("yaw")), theta)
    step = 2 * math.pi / atlas["yaw"]
    bucket = t.math("FLOOR", t.math("DIVIDE", t.math("WRAP", t.math("ADD", rel, step / 2), 2 * math.pi, 0.0), step))
    col = t.math("ADD", t.math("MULTIPLY", _switched(t, "far_slot", "far_slot2"), float(atlas["yaw"])),
                 t.math("MINIMUM", bucket, atlas["yaw"] - 1.0))
    row = t.math("MINIMUM", t.math("FLOOR", t.math("MULTIPLY", _frame_t(t, frame, n, _switched(t, "rate", "rate2")), atlas["frames"] / n)),
                 atlas["frames"] - 1.0)
    for name_, value in (("atlas_col", col), ("atlas_row", row)):
        s = t.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
        t.link(geom, t.sock(s.inputs, "Geometry"))
        t.sock(s.inputs, "Name").default_value = name_
        t.val(s, "Value", value)
        geom = t.sock(s.outputs, "Geometry")
    oi = t.node("GeometryNodeObjectInfo", transform_space="ORIGINAL")
    t.sock(oi.inputs, "Object").default_value = quad
    _instance(t, geom, sel, t.sock(oi.outputs, "Geometry"), theta)
    return t.ng

# --- props: banners carried by standard-bearers, dust cards over the far ranks --------------------------------------------------

def _banner(bn, mats):
    """A pole in the soldier's right hand and a flag at its top (two material slots), in the soldier's frame (rest pose faces -Y)."""
    bm = bmesh.new()
    pole, (fw, fh), x0 = bn["pole_m"], bn["flag_m"], 0.32
    bmesh.ops.create_cone(bm, segments=8, radius1=0.03, radius2=0.03, depth=pole,
                          matrix=Matrix.Translation((x0, 0.0, pole / 2)))
    for f in bm.faces:
        f.material_index = 0
    cols, rows = 8, 4
    vs = []
    for j in range(rows + 1):
        for i in range(cols + 1):
            u = i / cols
            vs.append(bm.verts.new((x0 + u * fw, 0.12 * u * math.sin(u * math.pi * 1.6), pole - 0.05 - (1 - j / rows) * fh)))
    for j in range(rows):
        for i in range(cols):
            a = j * (cols + 1) + i
            f = bm.faces.new((vs[a], vs[a + 1], vs[a + cols + 2], vs[a + cols + 1]))
            f.material_index, f.smooth = 1, True
    me = bpy.data.meshes.new(f"EE_Crowd_banner_{bn['id']}")
    bm.to_mesh(me)
    bm.free()
    for key in (bn.get("pole_material"), bn["material"]):
        me.materials.append(mats.get(key))
    return bpy.data.objects.new(f"EE_Crowd_banner_{bn['id']}", me)


def tree_banner(name, cam, ob, k):
    t = _Tree(name)
    geom, sel, _, _, _ = _common(t, cam, 0.0, 1.0e9)
    sel = t.band(sel, t.compare("EQUAL", t.attr("banner"), float(k)))
    st = t.node("GeometryNodeInputSceneTime")
    sway = t.math("MULTIPLY", t.math("SINE", t.math("ADD", t.math("MULTIPLY", t.sock(st.outputs, "Seconds"), 1.3), t.attr("phase"))), 0.1)
    rot = t.math("ADD", t.math("ADD", t.math("RADIANS", t.attr("yaw")), math.pi), sway)
    oi = t.node("GeometryNodeObjectInfo", transform_space="ORIGINAL")
    t.sock(oi.inputs, "Object").default_value = ob
    _instance(t, geom, sel, t.sock(oi.outputs, "Geometry"), rot)
    return t.ng


def _dust_material(dust, name="EE_Crowd_dust"):
    """Soft dust or smoke: a 4D noise (W = the card's seed, read from the instancer) under a radial falloff, times the card's
    ``fade`` (stored by its tree from the shot time), lit by the shot's own lights (diffuse + translucent), blended."""
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nt = mat.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    N, L = nt.nodes, nt.links
    tc, seed = N.new("ShaderNodeTexCoord"), N.new("ShaderNodeAttribute")
    seed.attribute_type, seed.attribute_name = "INSTANCER", "seed"
    noise = N.new("ShaderNodeTexNoise")
    noise.noise_dimensions = "4D"
    noise.inputs["Scale"].default_value, noise.inputs["Detail"].default_value = 2.2, 4.0
    L.new(tc.outputs["UV"], noise.inputs["Vector"])
    L.new(seed.outputs["Fac"], noise.inputs["W"])
    ramp = N.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value, ramp.inputs["From Max"].default_value = 0.38, 0.72
    L.new(noise.outputs["Fac"], ramp.inputs["Value"])
    dist = N.new("ShaderNodeVectorMath")
    dist.operation = "DISTANCE"
    L.new(tc.outputs["UV"], dist.inputs[0])
    dist.inputs[1].default_value = (0.5, 0.5, 0.0)
    fall = N.new("ShaderNodeMapRange")
    fall.interpolation_type = "SMOOTHSTEP"
    fall.inputs["From Min"].default_value, fall.inputs["From Max"].default_value = 0.5, 0.12
    L.new(dist.outputs["Value"], fall.inputs["Value"])
    m1, m2, m3 = N.new("ShaderNodeMath"), N.new("ShaderNodeMath"), N.new("ShaderNodeMath")
    m1.operation = m2.operation = m3.operation = "MULTIPLY"
    fade = N.new("ShaderNodeAttribute")
    fade.attribute_type, fade.attribute_name = "INSTANCER", "fade"
    L.new(ramp.outputs["Result"], m1.inputs[0])
    L.new(fall.outputs["Result"], m1.inputs[1])
    L.new(m1.outputs[0], m3.inputs[0])
    L.new(fade.outputs["Fac"], m3.inputs[1])
    L.new(m3.outputs[0], m2.inputs[0])
    m2.inputs[1].default_value = float(dust["alpha"])
    rgb = (*dust["rgb"], 1.0)
    dif, trl, add = N.new("ShaderNodeBsdfDiffuse"), N.new("ShaderNodeBsdfTranslucent"), N.new("ShaderNodeAddShader")
    dif.inputs["Color"].default_value = trl.inputs["Color"].default_value = rgb
    L.new(dif.outputs[0], add.inputs[0])
    L.new(trl.outputs[0], add.inputs[1])
    tr, mix = N.new("ShaderNodeBsdfTransparent"), N.new("ShaderNodeMixShader")
    L.new(m2.outputs[0], mix.inputs[0])
    L.new(tr.outputs[0], mix.inputs[1])
    L.new(add.outputs[0], mix.inputs[2])
    out = N.new("ShaderNodeOutputMaterial")
    L.new(mix.outputs[0], out.inputs["Surface"])
    if hasattr(mat, "surface_render_method"):
        mat.surface_render_method = "BLENDED"
    if hasattr(mat, "use_transparency_overlap"):
        mat.use_transparency_overlap = True
    return mat


def _rows_points(name, rows, names):
    """One vertex per row at its first three values; the rest become float point attributes named ``names[3:]``."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(r[0], r[1], r[2]) for r in rows], [], [])
    for i, k in enumerate(names[3:]):
        at = me.attributes.new(k, "FLOAT", "POINT")
        at.data.foreach_set("value", [float(r[3 + i]) for r in rows])
    return me


def _store(t, geom, name, value):
    s = t.node("GeometryNodeStoreNamedAttribute", data_type="FLOAT", domain="POINT")
    t.link(geom, t.sock(s.inputs, "Geometry"))
    t.sock(s.inputs, "Name").default_value = name
    t.val(s, "Value", value)
    return t.sock(s.outputs, "Geometry")


def _facing(t, cam, pos):
    oi = t.node("GeometryNodeObjectInfo", transform_space="RELATIVE")
    t.sock(oi.inputs, "Object").default_value = cam
    dx, dy, _ = t.sep(t.vmath("SUBTRACT", t.sock(oi.outputs, "Location"), pos))[:3]
    return t.math("ARCTAN2", t.math("MULTIPLY", dx, -1.0), dy)


def _clamp01(t, v):
    return t.math("MINIMUM", t.math("MAXIMUM", v, 0.0), 1.0)


def tree_dust(name, cam, quad):
    """Cards drift (closed form) and turn to the camera about Z, scaled by their own w x h; ``fade`` rises over 2.5 s from t_in."""
    t = _Tree(name)
    st = t.node("GeometryNodeInputSceneTime")
    secs = t.sock(st.outputs, "Seconds")
    sp = t.node("GeometryNodeSetPosition")
    t.link(t.gin.outputs[0], t.sock(sp.inputs, "Geometry"))
    t.val(sp, "Offset", t.xyz(t.math("MULTIPLY", t.attr("vx"), secs), t.math("MULTIPLY", t.attr("vy"), secs), 0.0))
    pos = t.sock(t.node("GeometryNodeInputPosition").outputs, "Position")
    geom = _store(t, t.sock(sp.outputs, "Geometry"), "fade", _clamp01(t, t.math("DIVIDE", t.math("SUBTRACT", secs, t.attr("t_in")), 2.5)))
    qi = t.node("GeometryNodeObjectInfo", transform_space="ORIGINAL")
    t.sock(qi.inputs, "Object").default_value = quad
    _instance(t, geom, True, t.sock(qi.outputs, "Geometry"), _facing(t, cam, pos), scale=t.xyz(t.attr("w"), 1.0, t.attr("h")))
    return t.ng


def tree_smoke(name, cam, quad):
    """Smoke columns: puff k rises in a loop (life = fract(t / period + phase)), leans with the wind, grows from size0 to size1
    and fades in and out as sin(pi life). Every frame is a function of the shot time alone (chunk-safe)."""
    t = _Tree(name)
    st = t.node("GeometryNodeInputSceneTime")
    life = t.math("FRACT", t.math("ADD", t.math("DIVIDE", t.sock(st.outputs, "Seconds"), t.attr("period")), t.attr("phase")))
    rise = t.math("MULTIPLY", life, t.attr("height"))
    sp = t.node("GeometryNodeSetPosition")
    t.link(t.gin.outputs[0], t.sock(sp.inputs, "Geometry"))
    t.val(sp, "Offset", t.xyz(t.math("MULTIPLY", rise, t.attr("lean")), 0.0, rise))
    pos = t.sock(t.node("GeometryNodeInputPosition").outputs, "Position")
    geom = _store(t, t.sock(sp.outputs, "Geometry"), "fade", t.math("SINE", t.math("MULTIPLY", life, math.pi)))
    size = t.math("ADD", t.attr("size0"), t.math("MULTIPLY", t.math("SUBTRACT", t.attr("size1"), t.attr("size0")), life))
    qi = t.node("GeometryNodeObjectInfo", transform_space="ORIGINAL")
    t.sock(qi.inputs, "Object").default_value = quad
    _instance(t, geom, True, t.sock(qi.outputs, "Geometry"), _facing(t, cam, pos), scale=t.xyz(size, 1.0, size))
    return t.ng


def _arrow(mats, scale):
    """A shaft along +X (the tip at x = 0) with a two-vane fletch at the back, ``scale`` x a 0.85 m arrow."""
    bm = bmesh.new()
    L_ = 0.85 * scale
    bmesh.ops.create_cone(bm, segments=5, radius1=0.012 * scale, radius2=0.012 * scale, depth=L_,
                          matrix=Matrix.Translation((-L_ / 2, 0, 0)) @ Matrix.Rotation(math.pi / 2, 4, "Y"))
    for a, b in (((0, 0.05), (0, -0.05)), ((0.05, 0), (-0.05, 0))):
        vs = [bm.verts.new((-L_ + 0.02 * scale, a[0] * scale, a[1] * scale)), bm.verts.new((-L_ + 0.17 * scale, 0, 0)),
              bm.verts.new((-L_ + 0.02 * scale, b[0] * scale, b[1] * scale))]
        bm.faces.new(vs)
    me = bpy.data.meshes.new("EE_Crowd_arrow")
    bm.to_mesh(me)
    bm.free()
    me.materials.append(mats.get("night"))
    return bpy.data.objects.new("EE_Crowd_arrow", me)


def tree_arrows(name, ob, g):
    """Ballistic arrows: tau = clamp(t - t0, 0, flight); p = p0 + v tau - g tau^2 / 2 along -Z; the shaft along the velocity
    (Align Rotation to Vector, X axis). An arrow appears at its launch and stays where it lands."""
    t = _Tree(name)
    st = t.node("GeometryNodeInputSceneTime")
    secs = t.sock(st.outputs, "Seconds")
    tau = t.math("MINIMUM", t.math("MAXIMUM", t.math("SUBTRACT", secs, t.attr("t0")), 0.0), t.attr("flight"))
    drop = t.math("MULTIPLY", t.math("MULTIPLY", tau, tau), -0.5 * g)
    sp = t.node("GeometryNodeSetPosition")
    t.link(t.gin.outputs[0], t.sock(sp.inputs, "Geometry"))
    t.val(sp, "Offset", t.xyz(t.math("MULTIPLY", t.attr("vx"), tau), t.math("MULTIPLY", t.attr("vy"), tau),
                              t.math("ADD", t.math("MULTIPLY", t.attr("vz"), tau), drop)))
    vel = t.xyz(t.attr("vx"), t.attr("vy"), t.math("SUBTRACT", t.attr("vz"), t.math("MULTIPLY", tau, g)))
    al = t.node("FunctionNodeAlignRotationToVector")
    al.axis = "X"
    t.val(al, "Vector", vel)
    oi = t.node("GeometryNodeObjectInfo", transform_space="ORIGINAL")
    t.sock(oi.inputs, "Object").default_value = ob
    _instance(t, t.sock(sp.outputs, "Geometry"), t.compare("GREATER_EQUAL", secs, t.attr("t0")), t.sock(oi.outputs, "Geometry"),
              None, rotation=t.sock(al.outputs, "Rotation"))
    return t.ng


def _dust_quad():
    me = bpy.data.meshes.new("EE_Crowd_dust_quad")
    me.from_pydata([(-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new(name="UVMap")
    for li, (u, v) in zip(range(4), ((1, 0), (0, 0), (0, 1), (1, 1))):
        uv.data[li].uv = (u, v)
    return bpy.data.objects.new("EE_Crowd_dust_quad", me)


def build_props(scene, block, pts, holder):
    """Banner and dust objects (none when the block has no props); every one off Line Art, dust casts no shadow."""
    props, cam, out = block.get("props") or {}, scene.camera, {}
    mats = {m.name: m for m in bpy.data.materials}
    for bn in props.get("banners", []):
        ob = _banner(bn, mats)
        holder.objects.link(ob)
        inst = bpy.data.objects.new(f"EE_Crowd_banners_{bn['id']}", pts)
        scene.collection.objects.link(inst)
        inst.modifiers.new("EE_Crowd", "NODES").node_group = tree_banner(f"EE_Crowd_banners_{bn['id']}", cam, ob, bn["id"])
        out[f"banners_{bn['id']}"] = inst
    dust = props.get("dust")
    if dust:
        quad = _dust_quad()
        quad.data.materials.append(_dust_material(dust))
        holder.objects.link(quad)
        inst = bpy.data.objects.new("EE_Crowd_dust", _rows_points("EE_Crowd_dust_points", dust["cards"], DUST_NAMES))
        scene.collection.objects.link(inst)
        inst.modifiers.new("EE_Crowd", "NODES").node_group = tree_dust("EE_Crowd_dust", cam, quad)
        inst.visible_shadow = False
        out["dust"] = inst
    smoke = props.get("smoke")
    if smoke:
        quad = _dust_quad()
        quad.name = "EE_Crowd_smoke_quad"
        quad.data.materials.append(_dust_material(smoke, "EE_Crowd_smoke"))
        holder.objects.link(quad)
        inst = bpy.data.objects.new("EE_Crowd_smoke", _rows_points("EE_Crowd_smoke_points", smoke["puffs"], SMOKE_NAMES))
        scene.collection.objects.link(inst)
        inst.modifiers.new("EE_Crowd", "NODES").node_group = tree_smoke("EE_Crowd_smoke", cam, quad)
        inst.visible_shadow = False
        out["smoke"] = inst
    arrows = props.get("arrows")
    if arrows:
        ob = _arrow(mats, float(arrows.get("scale", 1.0)))
        holder.objects.link(ob)
        inst = bpy.data.objects.new("EE_Crowd_arrows", _rows_points("EE_Crowd_arrow_points", arrows["rows"], ARROW_NAMES))
        scene.collection.objects.link(inst)
        inst.modifiers.new("EE_Crowd", "NODES").node_group = tree_arrows("EE_Crowd_arrows", ob, float(arrows.get("gravity", 9.81)))
        inst.visible_shadow = False
        out["arrows"] = inst
    for o in out.values():
        o.lineart.usage = "EXCLUDE"
    return out


def build(scene, block, workdir, report):
    """The whole crowd of a crowds block on the built, styled scene; the templates are hidden afterwards."""
    t0 = time.perf_counter()
    n = int(block["bake_frames"])
    by_slot, full_of, rates, rows = {}, {}, {}, []
    for tpl in block["templates"]:
        root = bpy.data.objects.get(tpl["name"])
        if root is None:
            raise RuntimeError(f"crowd template {tpl['name']} was not built")
        full, mid, length, action, t_full, t_mid = bake_clip(scene, root, n, block["mid_tris"])
        by_slot[tpl["slot"]], full_of[tpl["slot"]] = mid, full
        rates[tpl["slot"]] = n / length
        counts = {len(m.vertices) for m in mid}
        rows.append({"slot": tpl["slot"], "action": action, "cycle_frames": round(length, 3), "full_tris": t_full,
                     "mid_tris": t_mid, "mid_vertex_counts": sorted(counts)[:4]})
    bake_s = time.perf_counter() - t0
    for tpl in block["templates"]:   # the templates' job is done
        for o in [bpy.data.objects[tpl["name"]]] + list(bpy.data.objects[tpl["name"]].children_recursive):
            o.hide_render = True
    col = _collection("EE_Crowd_T1", sorted(by_slot.items()))
    p = block["points"]
    centre = (sum(p["x"]) / max(len(p["x"]), 1), sum(p["y"]) / max(len(p["y"]), 1))
    far = [(ft["far_slot"], full_of[ft["slot"]]) for ft in sorted(block["far_templates"], key=lambda x: x["far_slot"])]
    vf = block["atlas"].get("view_frame")
    if vf is not None:      # a moving camera: the atlas is drawn from its pose at this frame (the billboards' elevation)
        scene.frame_set(scene.frame_start + int(vf))
    img, ainfo = bake_atlas(scene, far, n, block["atlas"], centre, workdir)
    scene.frame_set(scene.frame_start)
    # the near band draws the full meshes only of the slots a soldier wears near the camera (``near_slots``, planned on the host);
    # every other slot gets its decimated meshes there (the Pick Instance order stays slot x N + f) and its full ones are freed
    near_slots = set(block.get("near_slots", full_of))
    col_full = _collection("EE_Crowd_T1_full", [(k, full_of[k] if k in near_slots else by_slot[k]) for k in sorted(full_of)])
    freed = 0
    for k in sorted(full_of):
        if k not in near_slots:
            for me in full_of[k]:
                if me.users == 0:
                    bpy.data.meshes.remove(me)
                    freed += 1
    quad = _quad(block["atlas"], ainfo["elevation_deg"])
    quad.data.materials.append(_atlas_material(img, *ainfo["cells"]))
    holder = bpy.data.collections.new("EE_Crowd_quad")   # out of the scene: drawn only through the instancer
    holder.objects.link(quad)
    pts = _points("EE_Crowd_points", block, rates)
    cam = scene.camera
    b = block["borders"]
    objs = {}
    near = min(b["hero_max_m"], block["mid_shadow_max_m"])
    shadow_to = min(block["mid_shadow_max_m"], b["far_min_m"])
    bands = {"t1_near": (0.0, near), "t1_shadow": (near, shadow_to), "t1_far": (shadow_to, b["far_min_m"])}
    for tier, shadow in TIERS_T1:
        ob = bpy.data.objects.new(f"EE_Crowd_{tier}", pts)
        scene.collection.objects.link(ob)
        ob.modifiers.new("EE_Crowd", "NODES").node_group = tree_t1(f"EE_Crowd_{tier}", cam, col_full if tier == "t1_near" else col,
                                                                   n, *bands[tier])
        ob.visible_shadow = shadow
        objs[tier] = ob
    ob = bpy.data.objects.new("EE_Crowd_t2", pts)
    scene.collection.objects.link(ob)
    ob.modifiers.new("EE_Crowd", "NODES").node_group = tree_t2("EE_Crowd_t2", cam, quad, n, block["atlas"], b["far_min_m"])
    ob.visible_shadow = False
    objs["t2"] = ob
    for o in objs.values():
        o.lineart.usage = "EXCLUDE"
    extras = build_props(scene, block, pts, holder)

    def census(frame):
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        every = dict(objs, **extras)
        counts, shown = {k: 0 for k in every}, []
        names = {o.name: k for k, o in every.items()}
        for di in dg.object_instances:
            if di.is_instance and di.parent is not None and di.parent.original.name in names:
                k = names[di.parent.original.name]
                counts[k] += 1
                if k.startswith("t1"):
                    shown.append(di.instance_object.original.name)
        return counts, shown

    allc, shown0 = census(scene.frame_start + 1)
    inst = {k: v for k, v in allc.items() if k in objs}
    _, shown1 = census(scene.frame_start + 2)
    changed = sum(a != b for a, b in zip(shown0, shown1)) / max(len(shown0), 1)
    scene.frame_set(scene.frame_start)
    report["crowd"] = {"schema": block["schema"], "points": block["count"], "heroes": len(block.get("heroes", [])),
                       "bake_frames": n, "templates": rows, "bake_seconds": round(bake_s, 2), "atlas": ainfo,
                       "instances_second_frame": inst, "t1_changed_share": round(changed, 4), "borders": b, "bands_m": bands,
                       "shadow": {k: o.visible_shadow for k, o in objs.items()},
                       "lineart": {k: o.lineart.usage for k, o in dict(objs, **extras).items()},
                       "props": {k: allc[k] for k in extras}, "near_slots": sorted(near_slots), "full_meshes_freed": freed,
                       "seconds": round(time.perf_counter() - t0, 2)}
    return objs
