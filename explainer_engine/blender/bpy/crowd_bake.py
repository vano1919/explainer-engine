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
from mathutils import Vector

TIERS_T1 = (("t1_shadow", True), ("t1_far", False))


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
    cover = float((px[..., 3] > 0.5).mean())
    return img, {"size": [W, H], "cells": [cols, rows], "seconds": round(time.perf_counter() - t0, 2),
                 "renders": len(far_meshes) * frames, "elevation_deg": round(math.degrees(elev), 2),
                 "view_yaw_deg": round(math.degrees(phi), 2), "alpha_cover": round(cover, 4), "file": img.filepath_raw}


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
            "delay": p["delay"]}
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
    walk = t.math("MAXIMUM", t.math("SUBTRACT", secs, t.attr("delay")), 0.0)
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


def _instance(t, geom, sel, instance, rot_z, *, pick=None):
    eu = t.node("FunctionNodeEulerToRotation")
    t.val(eu, "Euler", t.xyz(0.0, 0.0, rot_z))
    iop = t.node("GeometryNodeInstanceOnPoints")
    t.link(geom, t.sock(iop.inputs, "Points"))
    t.val(iop, "Selection", sel)
    t.link(instance, t.sock(iop.inputs, "Instance"))
    t.link(t.sock(eu.outputs, "Rotation"), t.sock(iop.inputs, "Rotation"))
    if pick is not None:
        t.sock(iop.inputs, "Pick Instance").default_value = True
        t.val(iop, "Instance Index", pick)
    t.link(t.sock(iop.outputs, "Instances"), t.gout.inputs[0])


def _frame_t(t, frame, n):
    return t.math("WRAP", t.math("ADD", t.math("MULTIPLY", frame, t.attr("rate")), t.attr("phase")), float(n), 0.0)


def tree_t1(name, cam, col, n, dmin, dmax):
    t = _Tree(name)
    geom, sel, _, _, frame = _common(t, cam, dmin, dmax)
    ci = t.node("GeometryNodeCollectionInfo", transform_space="ORIGINAL")
    t.sock(ci.inputs, "Collection").default_value = col
    t.sock(ci.inputs, "Separate Children").default_value = True
    t.sock(ci.inputs, "Reset Children").default_value = True
    idx = t.math("ADD", t.math("MULTIPLY", t.attr("slot"), float(n)), t.math("FLOOR", _frame_t(t, frame, n)))
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
    col = t.math("ADD", t.math("MULTIPLY", t.attr("far_slot"), float(atlas["yaw"])), t.math("MINIMUM", bucket, atlas["yaw"] - 1.0))
    row = t.math("MINIMUM", t.math("FLOOR", t.math("MULTIPLY", _frame_t(t, frame, n), atlas["frames"] / n)), atlas["frames"] - 1.0)
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
    img, ainfo = bake_atlas(scene, far, n, block["atlas"], centre, workdir)
    quad = _quad(block["atlas"], ainfo["elevation_deg"])
    quad.data.materials.append(_atlas_material(img, *ainfo["cells"]))
    holder = bpy.data.collections.new("EE_Crowd_quad")   # out of the scene: drawn only through the instancer
    holder.objects.link(quad)
    pts = _points("EE_Crowd_points", block, rates)
    cam = scene.camera
    b = block["borders"]
    objs = {}
    bands = {"t1_shadow": (0.0, min(block["mid_shadow_max_m"], b["far_min_m"])),
             "t1_far": (min(block["mid_shadow_max_m"], b["far_min_m"]), b["far_min_m"])}
    for tier, shadow in TIERS_T1:
        ob = bpy.data.objects.new(f"EE_Crowd_{tier}", pts)
        scene.collection.objects.link(ob)
        ob.modifiers.new("EE_Crowd", "NODES").node_group = tree_t1(f"EE_Crowd_{tier}", cam, col, n, *bands[tier])
        ob.visible_shadow = shadow
        objs[tier] = ob
    ob = bpy.data.objects.new("EE_Crowd_t2", pts)
    scene.collection.objects.link(ob)
    ob.modifiers.new("EE_Crowd", "NODES").node_group = tree_t2("EE_Crowd_t2", cam, quad, n, block["atlas"], b["far_min_m"])
    ob.visible_shadow = False
    objs["t2"] = ob
    for o in objs.values():
        o.lineart.usage = "EXCLUDE"
    def census(frame):
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        counts, shown = {k: 0 for k in objs}, []
        names = {o.name: k for k, o in objs.items()}
        for di in dg.object_instances:
            if di.is_instance and di.parent is not None and di.parent.original.name in names:
                k = names[di.parent.original.name]
                counts[k] += 1
                if k.startswith("t1"):
                    shown.append(di.instance_object.original.name)
        return counts, shown

    inst, shown0 = census(scene.frame_start + 1)
    _, shown1 = census(scene.frame_start + 2)
    changed = sum(a != b for a, b in zip(shown0, shown1)) / max(len(shown0), 1)
    scene.frame_set(scene.frame_start)
    report["crowd"] = {"schema": block["schema"], "points": block["count"], "heroes": len(block.get("heroes", [])),
                       "bake_frames": n, "templates": rows, "bake_seconds": round(bake_s, 2), "atlas": ainfo,
                       "instances_second_frame": inst, "t1_changed_share": round(changed, 4), "borders": b, "bands_m": bands,
                       "shadow": {k: o.visible_shadow for k, o in objs.items()},
                       "lineart": {k: o.lineart.usage for k, o in objs.items()},
                       "seconds": round(time.perf_counter() - t0, 2)}
    return objs
