"""Runs INSIDE Blender (``blender -b --factory-startup --python make_rain_lead.py -- <rain_v3.2.blend> <out.blend>``, scripts stay OFF).
WP-Q4: Rain v3.3 (CC-BY 4.0, Rain Rig © Blender Foundation | cloud.blender.org) adapted to the historical direction as the cast lead:

1. the head lattice HLP-rain-lattice-head is moved (longer jaw, narrower cheeks), baked into the file;
2. ONE authored shape key ``angular`` on GEO-rain-head (value 1): a longer, sharper nose, a heavier brow ridge and a squarer chin, by
   smooth falloffs around three centres (numbers measured on Rain's rest head: nose tip (0, -0.172, 1.428), brow z 1.47-1.50);
3. a cloak mesh (an open half-cylinder from the shoulders to the knees, wavy hem), its bone weights transferred from Rain's own top by
   a Data Transfer modifier and then applied, deformed by her armature; material ``MAT-lead.cloak``.

Rain's rig, face controls, shape keys and materials are untouched; the tunic is Rain's own top recoloured by the style (character_benchmark).
stdlib + bpy + bmesh + mathutils only.
"""
import math
import sys

import bmesh
import bpy
from mathutils import Vector

LATTICE_DELTAS = {}   # filled below; lattice units, points ordered x fastest, then y, then z (z=0 chin row)
for i in range(12):
    x, z = i % 2, i // 4
    sx = -1.0 if x == 0 else 1.0
    if z == 0:
        LATTICE_DELTAS[i] = (-0.12 * sx * 0.9, 0.0, -0.18 * 0.9)
    elif z == 1:
        LATTICE_DELTAS[i] = (-0.06 * sx * 0.9, 0.0, 0.0)


def gauss(d2, r):
    return math.exp(-d2 / (2 * r * r))


def angular_key(head):
    if "angular" in head.data.shape_keys.key_blocks:
        return
    basis = head.data.shape_keys.key_blocks["Basis"]
    key = head.shape_key_add(name="angular", from_mix=False)
    nose, chin = Vector((0.0, -0.172, 1.428)), Vector((0.0, -0.135, 1.31))
    moved = 0
    for i, v in enumerate(basis.data):
        p = v.co.copy()
        d = Vector((0.0, 0.0, 0.0))
        w = gauss((p - nose).length_squared, 0.03)
        d += Vector((0.0, -0.022, -0.002)) * w                      # the nose tip pushed out and a touch down
        bridge = gauss(((p.x) ** 2) * 6 + (p.z - 1.455) ** 2 + (p.y + 0.165) ** 2, 0.025)
        d += Vector((0.0, -0.009, 0.0)) * bridge                    # a straighter, longer bridge
        if p.y < -0.12 and 1.46 < p.z < 1.52:                        # brow ridge: out and down, strongest at the middle of the brow
            wb = gauss((p.z - 1.488) ** 2, 0.014) * min(1.0, abs(p.x) / 0.03 + 0.6) * gauss(max(abs(p.x) - 0.07, 0) ** 2, 0.03)
            d += Vector((0.0, -0.011, -0.005)) * wb
        wc = gauss((p - chin).length_squared, 0.03)
        d += Vector((0.0, -0.008, -0.014)) * wc                      # a squarer, longer chin
        key.data[i].co = p + d
        moved += d.length > 1e-6
    key.value = 1.0
    print("ANGULAR_KEY moved", moved)


def weighted(name, me, mat_name, rig, top, collection, subdiv=1):
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new(name, me)
    collection.objects.link(ob)
    me.materials.append(bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name))
    dt = ob.modifiers.new("WeightsFromTop", "DATA_TRANSFER")
    dt.object = top
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for g in top.vertex_groups:
        ob.vertex_groups.new(name=g.name)
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig
    ob.parent = rig
    if subdiv:
        sm = ob.modifiers.new("Subdivision", "SUBSURF")
        sm.levels = sm.render_levels = subdiv
    return ob


def tube_mesh(rings, cols, centre_fn, closed=True):
    bm = bmesh.new()
    for r in range(rings + 1):
        for c in range(cols):
            bm.verts.new(centre_fn(r / rings, 2 * math.pi * c / cols))
    bm.verts.ensure_lookup_table()
    for r in range(rings):
        for c in range(cols):
            a, b = r * cols + c, r * cols + (c + 1) % cols
            bm.faces.new((bm.verts[a], bm.verts[b], bm.verts[b + cols], bm.verts[a + cols]))
    me = bpy.data.meshes.new("tube")
    bm.to_mesh(me)
    bm.free()
    return me


def panel_mesh(sign, rows=10, cols=8):
    """A flat, slightly curved hip-length panel hanging from the shoulders over the chest (sign -1) or the back (sign +1)."""
    bm = bmesh.new()
    for r in range(rows + 1):
        t = r / rows
        z = 1.27 - 0.47 * t
        half = 0.10 + 0.035 * t
        for c in range(cols + 1):
            x = half * (2 * c / cols - 1)
            y = sign * (0.128 * math.sqrt(max(0.0, 1 - (x / 0.2) ** 2)) + 0.012) + 0.01
            bm.verts.new((x, y, z))
    bm.verts.ensure_lookup_table()
    for r in range(rows):
        for c in range(cols):
            i = r * (cols + 1) + c
            bm.faces.new((bm.verts[i], bm.verts[i + 1], bm.verts[i + cols + 2], bm.verts[i + cols + 1]))
    me = bpy.data.meshes.new("panel")
    bm.to_mesh(me)
    bm.free()
    return me


def tunic(rig, top, collection):
    """A narrow open-sided tabard: two flat panels (front and back, hip-length) and a belt over Rain's own top and trousers (which
    keep her silhouette and arm motion); weights from Rain's top."""
    weighted("GEO-lead-tabard-front", panel_mesh(-1), "MAT-lead.tunic", rig, top, collection, subdiv=1)
    weighted("GEO-lead-tabard-back", panel_mesh(1), "MAT-lead.tunic", rig, top, collection, subdiv=1)

    def belt(t, a):   # an elliptical strip at the waist, a thin tube around the body outside the panels
        u = 2 * math.pi * t
        rx, ry = 0.195, 0.138
        r = 0.014
        return ((rx + r * math.cos(a)) * math.sin(u), (ry + r * math.cos(a)) * math.cos(u) + 0.01, 1.02 + r * math.sin(a) * 1.6)
    weighted("GEO-lead-belt", tube_mesh(40, 8, belt), "MAT-lead.belt", rig, top, collection, subdiv=0)
    print("TUNIC built")


def cloak(rig, top, collection):
    bm = bmesh.new()
    rows, cols = 18, 33
    z0, z1 = 1.31, 0.62
    for r in range(rows + 1):
        t = r / rows
        z = z0 + (z1 - z0) * t
        rx, ry = 0.215 + 0.12 * t ** 1.3, 0.14 + 0.10 * t ** 1.3
        for c in range(cols + 1):
            a = math.radians(-35 + 185 * c / cols)                   # one shoulder only: from the back over the +X shoulder and down its side
            hem = 0.025 * math.sin(c * 1.7) * t * t
            bm.verts.new((rx * math.sin(a) * (1 + hem), ry * math.cos(a) * (1 + hem) + 0.015, z - abs(hem) * 0.6))
    bm.verts.ensure_lookup_table()
    for r in range(rows):
        for c in range(cols):
            i = r * (cols + 1) + c
            bm.faces.new((bm.verts[i], bm.verts[i + 1], bm.verts[i + cols + 2], bm.verts[i + cols + 1]))
    me = bpy.data.meshes.new("GEO-lead-cloak")
    bm.to_mesh(me)
    bm.free()
    for p in me.polygons:
        p.use_smooth = True
    ob = bpy.data.objects.new("GEO-lead-cloak", me)
    collection.objects.link(ob)
    mat = bpy.data.materials.new("MAT-lead.cloak")
    me.materials.append(mat)
    dt = ob.modifiers.new("WeightsFromTop", "DATA_TRANSFER")
    dt.object = top
    dt.use_vert_data = True
    dt.data_types_verts = {"VGROUP_WEIGHTS"}
    dt.vert_mapping = "POLYINTERP_NEAREST"
    bpy.context.view_layer.objects.active = ob
    ob.select_set(True)
    for g in top.vertex_groups:                                       # the groups must exist for the transfer
        ob.vertex_groups.new(name=g.name)
    bpy.ops.object.datalayout_transfer(modifier=dt.name)
    bpy.ops.object.modifier_apply(modifier=dt.name)
    am = ob.modifiers.new("Armature", "ARMATURE")
    am.object = rig
    ob.parent = rig
    sm = ob.modifiers.new("Subdivision", "SUBSURF")
    sm.levels = sm.render_levels = 1
    print("CLOAK groups", len(ob.vertex_groups), "verts", len(me.vertices))


def main():
    src, dst = sys.argv[sys.argv.index("--") + 1:][:2]
    bpy.ops.wm.open_mainfile(filepath=src)
    lat = bpy.data.objects["HLP-rain-lattice-head"].data
    for i, d in LATTICE_DELTAS.items():
        co = lat.points[i].co_deform
        lat.points[i].co_deform = (co[0] + d[0], co[1] + d[1], co[2] + d[2])
    angular_key(bpy.data.objects["GEO-rain-head"])
    tunic(bpy.data.objects["RIG-rain"], bpy.data.objects["GEO-rain-top"], bpy.data.collections["rain-clothes"])
    cloak(bpy.data.objects["RIG-rain"], bpy.data.objects["GEO-rain-top"], bpy.data.collections["rain-clothes"])
    bpy.ops.wm.save_as_mainfile(filepath=dst, compress=True)
    print("SAVED", dst)


main()
