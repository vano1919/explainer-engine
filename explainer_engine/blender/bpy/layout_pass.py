"""Runs INSIDE Blender, imported by ``render_shot.py`` when a scene carries a ``layout_pass`` block (``blender/layout_passes.py``;
D-116, guide step 2.3): the built scene, its camera and its motion stay exactly as they are; only how it is drawn changes.

- ``clay``: Workbench, studio light, one grey (``clay_rgb``) on a plain background: the J2 Layout-To-Render input.
- ``depth``: every surface emits its inverse depth, normalised and written Raw (no display curve): (1/z - 1/far) / (1/near - 1/far), near white, far and sky black
  (the disparity convention of the depth estimators the LTX controls were trained on); the J4 depth control.
- ``line``: every surface white, the sky white, Freestyle black lines (silhouette, border, crease) only on the objects that are
  not named background (``no_line`` name prefixes go into one collection the line set excludes): fore and mid planes only
  (plan 9.3); background objects also get ``pass_index`` 2, the rest 1 (the object-index pass).
- ``colour``: every surface emits its own base colour, unlit (flat colour; textures kept), the world kept: the J4 colour layout.

The look's compositor finish (paper, depth haze) is switched off. Each material keeps its alpha: the surface becomes mix(transparent, pass emission, alpha), with alpha taken from the material's
own transparent mix or its Principled alpha, so billboards and cards keep their silhouettes. stdlib + bpy only.
"""
import bpy  # noqa: E402  (Blender's own module)

KINDS = ("clay", "depth", "line", "colour")


def _out_node(nt):
    outs = [n for n in nt.nodes if n.bl_idname == "ShaderNodeOutputMaterial"]
    active = [n for n in outs if getattr(n, "is_active_output", False)]
    return (active or outs or [None])[0]


def _src(sock):
    return sock.links[0].from_socket if sock.is_linked else None


def _alpha_and_shader(nt):
    """(alpha: socket or float, shader node) of a material: through a Mix Shader that has a Transparent BSDF on one side, else a
    Principled BSDF's Alpha, else 1."""
    out = _out_node(nt)
    if out is None or not out.inputs["Surface"].is_linked:
        return 1.0, None
    node = out.inputs["Surface"].links[0].from_node
    if node.bl_idname == "ShaderNodeMixShader":
        a = node.inputs[1].links[0].from_node if node.inputs[1].is_linked else None
        b = node.inputs[2].links[0].from_node if node.inputs[2].is_linked else None
        fac = _src(node.inputs[0]) or node.inputs[0].default_value
        if a is not None and a.bl_idname == "ShaderNodeBsdfTransparent":
            return fac, b
        if b is not None and b.bl_idname == "ShaderNodeBsdfTransparent":
            return ("one_minus", fac), a
        return 1.0, node
    if node.bl_idname == "ShaderNodeBsdfPrincipled":
        return _src(node.inputs["Alpha"]) or node.inputs["Alpha"].default_value, node
    return 1.0, node


def _colour_of(node):
    """The colour socket source (or the default value) of a shader: Base Color, Color, else white."""
    if node is None:
        return (1.0, 1.0, 1.0, 1.0)
    for key in ("Base Color", "Color"):
        if key in node.inputs:
            s = node.inputs[key]
            return _src(s) or tuple(s.default_value)
    return (1.0, 1.0, 1.0, 1.0)


def _link_or_set(nt, value, sock):
    if isinstance(value, (int, float)):
        sock.default_value = float(value)
    elif isinstance(value, tuple) and value and value[0] == "one_minus":
        inv = nt.nodes.new("ShaderNodeMath")
        inv.operation = "SUBTRACT"
        inv.inputs[0].default_value = 1.0
        _link_or_set(nt, value[1], inv.inputs[1])
        nt.links.new(inv.outputs[0], sock)
    elif isinstance(value, tuple):
        sock.default_value = value
    else:
        nt.links.new(value, sock)


def _depth_colour(nt, near, far):
    cam = nt.nodes.new("ShaderNodeCameraData")
    inv = nt.nodes.new("ShaderNodeMath")
    inv.operation = "DIVIDE"
    inv.inputs[0].default_value = 1.0
    nt.links.new(cam.outputs["View Z Depth"], inv.inputs[1])
    rng = nt.nodes.new("ShaderNodeMapRange")
    rng.clamp = True
    rng.inputs["From Min"].default_value = 1.0 / far
    rng.inputs["From Max"].default_value = 1.0 / near
    rng.inputs["To Min"].default_value = 0.0
    rng.inputs["To Max"].default_value = 1.0
    nt.links.new(inv.outputs[0], rng.inputs["Value"])
    return rng.outputs["Result"]


def rewrite_material(mat, lp):
    """The material's surface replaced by mix(transparent, the pass's emission, its own alpha). Returns what was used."""
    if not mat.use_nodes or mat.node_tree is None:
        mat.use_nodes = True
    nt = mat.node_tree
    alpha, shader = _alpha_and_shader(nt)
    out = _out_node(nt) or nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Strength"].default_value = 1.0
    kind = lp["kind"]
    if kind == "depth":
        nt.links.new(_depth_colour(nt, lp["near_m"], lp["far_m"]), emit.inputs["Color"])
    elif kind == "line":
        emit.inputs["Color"].default_value = (1.0, 1.0, 1.0, 1.0)
    else:   # colour
        _link_or_set(nt, _colour_of(shader), emit.inputs["Color"])
    tr = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    _link_or_set(nt, alpha, mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(emit.outputs[0], mix.inputs[2])
    for link in list(out.inputs["Surface"].links):
        nt.links.remove(link)
    nt.links.new(mix.outputs[0], out.inputs["Surface"])
    if out.inputs.get("Displacement") is not None:
        for link in list(out.inputs["Displacement"].links):
            nt.links.remove(link)
    return {"shader": shader.bl_idname if shader is not None else None, "alpha": "linked" if not isinstance(alpha, float) else alpha}


def _flat_world(scene, rgb):
    w = bpy.data.worlds.new("layout_world")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (*rgb, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg.outputs[0], out.inputs["Surface"])
    w.color = rgb
    scene.world = w


def _set_engine(scene, ids):
    for cand in ids:
        try:
            scene.render.engine = cand
            return cand
        except TypeError:
            continue
    raise RuntimeError(f"no engine of {ids}")


def apply(scene, lp, report):
    kind = lp["kind"]
    if kind not in KINDS:
        raise RuntimeError(f"unknown layout pass {kind!r}")
    vs = scene.view_settings
    # depth is data: written as is (Raw), so a pixel's 8-bit value is the normalised inverse depth; the others are pictures (sRGB)
    vs.view_transform, vs.look, vs.exposure, vs.gamma = "Raw" if kind == "depth" else "Standard", "None", 0.0, 1.0
    scene.render.use_freestyle = False
    scene.render.dither_intensity = 0.0   # a control image carries no film-grain dither
    # the look's finish (paper overlay and depth haze, a compositor tree) is a picture layer, not geometry: off for every pass
    if hasattr(scene, "compositing_node_group"):
        scene.compositing_node_group = None
    scene.render.use_compositing = False
    out = {"kind": kind, "materials": 0, "shaders": {}, "no_line": []}
    background = [ob for ob in scene.objects if any(ob.name.startswith(p) for p in lp.get("no_line", []))]
    for ob in scene.objects:
        ob.pass_index = 2 if ob in background else 1
    if kind == "clay":
        _set_engine(scene, ("BLENDER_WORKBENCH",))
        sh = scene.display.shading
        sh.light, sh.color_type = "STUDIO", "SINGLE"
        sh.single_color = tuple(lp["clay_rgb"])
        sh.show_shadows = sh.show_cavity = sh.show_object_outline = False
        sh.background_type = "WORLD"
        _flat_world(scene, tuple(lp["background_rgb"]))
        report["layout_pass"] = out
        return out
    _set_engine(scene, ("BLENDER_EEVEE", "BLENDER_EEVEE_NEXT"))
    for attr, val in (("use_shadows", False), ("use_raytracing", False), ("use_fast_gi", False), ("use_bloom", False)):
        if hasattr(scene.eevee, attr):
            setattr(scene.eevee, attr, val)
    for mat in bpy.data.materials:
        if mat.users == 0:
            continue
        used = rewrite_material(mat, lp)
        out["materials"] += 1
        out["shaders"][used["shader"] or "none"] = out["shaders"].get(used["shader"] or "none", 0) + 1
    if kind == "depth":
        _flat_world(scene, (0.0, 0.0, 0.0))
        out.update(near_m=lp["near_m"], far_m=lp["far_m"])
    elif kind == "line":
        _flat_world(scene, (1.0, 1.0, 1.0))
        r = scene.render
        r.use_freestyle = True
        r.line_thickness_mode = "ABSOLUTE"
        r.line_thickness = float(lp["line_px"])
        vl = bpy.context.view_layer
        vl.use_freestyle = True
        fs = vl.freestyle_settings
        ls = fs.linesets[0] if fs.linesets else fs.linesets.new("lines")
        ls.select_by_visibility, ls.visibility = True, "VISIBLE"
        ls.select_by_edge_types = True
        ls.select_silhouette = ls.select_border = ls.select_crease = True
        if background:
            coll = bpy.data.collections.new("LP_no_line")
            for ob in background:
                coll.objects.link(ob)
            ls.select_by_collection = True
            ls.collection = coll
            ls.collection_negation = "EXCLUSIVE"
        ls.linestyle.color = (0.0, 0.0, 0.0)
        ls.linestyle.thickness = float(lp["line_px"])
        out["no_line"] = sorted(ob.name for ob in background)
    report["layout_pass"] = out
    return out
