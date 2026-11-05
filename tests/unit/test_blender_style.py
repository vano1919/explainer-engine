"""ICW-05 style engine (roadmap 9.1, BP-173): the style_graph/1 document of blender/style.py as a recorded node graph, without
Blender, and the Blender side (bpy/render_shot.py build_tree) replayed on a recorded fake of the node API."""
import json
import math
import types
from pathlib import Path

import pytest

from explainer_engine.blender import style as S
from explainer_engine.standards import sourced_rules as SR

CAM = {"lens_mm": 35, "focus_distance_m": 5.0}
TEX = "/cache/abc/table_diff.jpg"


def graph(path="eevee", tokens=None, **kw):
    mats = {"wood": {"base": "paper", "texture": TEX, "texture_mean": [0.2, 0.1, 0.05]}, "coat": {"base": "support_blue"}}
    return S.StyleEngine(tokens).graph(path, camera=CAM, materials=mats, paper_texture="/cache/p/paper.jpg", **kw)


def by_id(g):
    return {n["id"]: n for n in g["nodes"]}


def test_eevee_material_is_shader_to_rgb_three_constant_steps_rim_emission():
    m = graph()["materials"][0]
    assert m["name"] == "coat"
    n = by_id(m)
    assert n["to_rgb"]["type"] == "ShaderNodeShaderToRGB"
    ramp = n["tone"]["ramp"]
    assert ramp["interpolation"] == "CONSTANT" and len(ramp["stops"]) == 3
    assert [s[0] for s in ramp["stops"]] == [0.0, 0.12, 0.45]
    assert [s[1][0] for s in ramp["stops"]] == [0.46, 0.72, 1.0]
    assert n["base"]["inputs"]["6"] == S.rgba(S.palette()["support_blue"])
    assert n["rim"]["props"]["blend_type"] == "ADD" and n["facing"]["type"] == "ShaderNodeLayerWeight"
    assert ["emit", "Emission", "out", "Surface"] in m["links"]
    assert ["diffuse", "BSDF", "to_rgb", "Shader"] in m["links"] and ["rim", 2, "emit", "Color"] in m["links"]
    assert all(t["type"] != "ShaderNodeBsdfPrincipled" for t in m["nodes"])


def test_cycles_safe_path_has_no_shader_to_rgb_and_the_same_steps():
    g = graph("cycles_safe")
    for m in g["materials"]:
        types_ = {n["type"] for n in m["nodes"]}
        assert "ShaderNodeShaderToRGB" not in types_ and "ShaderNodeBsdfDiffuse" not in types_
        assert by_id(m)["tone"]["ramp"] == by_id(graph()["materials"][0])["tone"]["ramp"]
        assert by_id(m)["ndotl"]["inputs"]["1"] == list(S.KeyLight().direction())
    assert g["scene"]["engine"] == "cycles" and S.check(g) == []


def test_key_light_direction_is_a_unit_vector_towards_the_sun():
    kl = S.KeyLight(elevation_deg=90, azimuth_deg=0)
    assert kl.direction() == pytest.approx((0, 0, 1), abs=1e-6)
    d = S.KeyLight().direction()
    assert math.isclose(sum(x * x for x in d), 1.0, abs_tol=1e-5)


def test_texture_is_flattened_towards_its_mean_and_tiles_only_when_asked():
    m = graph()["materials"][1]
    n = by_id(m)
    assert n["tex"]["image"] == TEX and n["flatten"]["inputs"]["Factor"] == S.StyleTokens().texture_strength
    assert n["flatten"]["inputs"]["6"] == [0.2, 0.1, 0.05, 1.0]
    assert "tiling" not in n
    tiled = S.StyleEngine().material("g", "paper", texture=TEX, tile=8)
    assert by_id(tiled)["tiling"]["inputs"]["Scale"] == [8.0, 8.0, 1.0]


def test_scene_settings_follow_9_1_agx_look_and_no_ray_tracing():
    g = graph()
    sc = g["scene"]
    assert sc["view_transform"] == "AgX" and sc["look"] == "Medium High Contrast"
    assert sc["look_ids"][0] == "AgX - Medium High Contrast"  # MEASURED on 5.2.3: the enum holds only the prefixed id
    assert sc["eevee"]["use_raytracing"] is False and sc["eevee"]["use_fast_gi"] is False


def test_line_art_radius_from_pixels_and_crease_from_bp173():
    la = graph()["line_art"]
    assert la["crease_deg"] == SR.T("BP-173", "crease_deg")
    assert la["crease_threshold_rad"] == pytest.approx(math.radians(134), abs=1e-6)
    metres_per_px = 2 * 5.0 * 18 / 35 / 2560
    assert la["radius"] == pytest.approx(2.25 * metres_per_px / S.LINE_PX_PER_RADIUS, rel=1e-4)
    assert S.line_radius(3.0, 10, 35) == pytest.approx(2 * S.line_radius(1.5, 10, 35), rel=1e-4)
    assert S.line_radius(2.0, 10, 70) == pytest.approx(S.line_radius(2.0, 5, 35), rel=1e-4)


def test_tokens_refuse_a_non_width_and_wrong_step_counts():
    with pytest.raises(ValueError, match="width"):
        S.StyleTokens(line_px=0)
    with pytest.raises(ValueError, match="tones"):
        S.StyleTokens(tones=(0.5, 1.0))
    with pytest.raises(ValueError, match="look"):
        S.StyleTokens(look="Punchy")


def test_variants_stay_inside_the_bible_fixed_tokens():
    base = S.StyleTokens()
    lo, hi = SR.T("BP-173", "weight_px_1440")
    for name in S.VARIANTS:
        t = S.variant(name)
        assert lo <= t.line_px <= hi
        assert (t.steps, t.crease_deg, t.paper_opacity, t.view_transform, t.look) == \
               (base.steps, base.crease_deg, base.paper_opacity, base.view_transform, base.look)
    assert [S.variant(v).line_px for v in "ABC"] == [1.5, 2.25, 3.0]


def test_from_look_reads_a_shot_spec_look_block():
    look = {"bible_version": "1.5", "line_weight_px": 2.0, "crease_deg": 134, "shading_steps": 3, "view_transform": "AgX",
            "grade_look": "Medium High Contrast", "paper": {"asset": {"id": "texture.x", "sha256": "0" * 64}, "opacity": 0.12}}
    t = S.StyleTokens.from_look(look)
    assert (t.line_px, t.paper_opacity) == (2.0, 0.12)
    with pytest.raises(ValueError, match="three steps"):
        S.StyleTokens.from_look(dict(look, shading_steps=4))


def test_from_bible_reads_the_style_block_and_defaults_without_it():
    assert S.StyleTokens.from_bible({"style": {}}) == S.StyleTokens()
    t = S.StyleTokens.from_bible({"style": {"line": {"weight_px_1440": 3.0}, "shading": {"tones": [0.3, 0.6, 1.0], "rim": False}}})
    assert (t.line_px, t.tones, t.rim) == (3.0, (0.3, 0.6, 1.0), False)
    S.StyleTokens.from_bible()  # the committed bible reads


def test_paper_pass_is_the_compositor_overlay_and_absent_without_a_texture():
    p = graph()["paper"]
    n = by_id(p)
    assert p["enabled"] and n["overlay"]["props"]["blend_type"] == "OVERLAY" and n["overlay"]["inputs"]["Factor"] == 0.12
    assert n["fit"]["inputs"] == {"Type": "Render Size", "Frame Type": "Crop"}
    assert ["overlay", 2, "out", "Image"] in p["links"]
    assert S.StyleEngine().paper(None) == {"enabled": False, "opacity": 0.12}


def test_graph_is_deterministic_and_check_finds_tampering():
    a, b = graph(), graph()
    assert json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True) and S.check(a) == []
    bad = json.loads(json.dumps(a))
    bad["scene"]["eevee"]["use_raytracing"] = True
    assert any("sha256" in x for x in S.check(bad))
    bad["sha256"] = S.digest(bad)
    assert any("ray tracing" in x for x in S.check(bad))
    bad = json.loads(json.dumps(a))
    bad["materials"][0]["links"].append(["ghost", "Color", "emit", "Color"])
    bad["sha256"] = S.digest(bad)
    assert any("ghost" in x for x in S.check(bad))


def test_with_paths_moves_images_and_rehashes():
    g = S.with_paths(graph(), {TEX: "/runner/cache/table.jpg"})
    assert by_id(g["materials"][1])["tex"]["image"] == "/runner/cache/table.jpg" and S.check(g) == []


def test_world_backdrop_is_paper_for_camera_rays_and_hdri_only_lights():
    w = graph(hdri="/cache/h/sky.hdr")["world"]
    n = by_id(w)
    paper = S.rgba(S.palette()["paper"])
    assert n["backdrop"]["inputs"]["Color"] == paper and n["light"]["inputs"]["Strength"] == S.StyleTokens().ambient
    assert ["is_cam", "Is Camera Ray", "mix", "Fac"] in w["links"] and ["env", "Color", "light", "Color"] in w["links"]


def test_srgb_to_linear_matches_the_transfer_function():
    assert S.srgb_to_linear("#000000") == (0.0, 0.0, 0.0) and S.srgb_to_linear("#FFFFFF") == (1.0, 1.0, 1.0)
    assert S.srgb_to_linear("#808080")[0] == pytest.approx(0.215861, abs=1e-6)


# ---- the Blender side: render_shot.build_tree on a recorded fake of the node API -----------------------------------------------

class Sock:
    def __init__(self, name):
        self.name = self.identifier = name
        self.default_value = None


class Node:
    INS = {"ShaderNodeMix": ["Factor", "Factor", "A", "B", "A", "B", "A", "B", "A", "B"]}

    def __init__(self, t):
        self.bl_idname = t
        self.name = self.label = ""
        self.inputs = [Sock(n) for n in self.INS.get(t, ["Color", "Fac", "Shader", "Surface", "Strength", "Blend", "Vector",
                                                        "Image", "Roughness", "Factor", "Value", "Type", "Frame Type", "Scale", 1])]
        for i, s in enumerate(self.inputs):
            if isinstance(s.name, int):
                s.name = s.identifier = "Vector_1"
        self.outputs = [Sock(n) for n in ("Color", "BSDF", "Val", "Value", "Normal", "Facing", "Emission", "Background",
                                          "Is Camera Ray", "Shader", "Image", "UV", "Vector", "Result")]
        if t == "ShaderNodeValToRGB":
            self.color_ramp = types.SimpleNamespace(interpolation="LINEAR", elements=[types.SimpleNamespace(position=0, color=0),
                                                                                         types.SimpleNamespace(position=1, color=1)])
        self.image = None
        self.data_type = self.blend_type = self.operation = self.interpolation = None


class Elements(list):
    def new(self, pos):
        e = types.SimpleNamespace(position=pos, color=None)
        self.append(e)
        return e


class Tree:
    def __init__(self):
        self.made, self.linked = [], []
        self.links = types.SimpleNamespace(new=lambda a, b: self.linked.append((a, b)))

    def _new(self, t):
        n = Node(t)
        if hasattr(n, "color_ramp"):
            n.color_ramp.elements = Elements(n.color_ramp.elements)
        self.made.append(n)
        return n


def load_render_shot():
    src = (Path(S.__file__).parent / "bpy" / "render_shot.py").read_text(encoding="utf-8")
    src = src.replace("import bpy  #", "bpy = None  #").replace("from mathutils import Vector  #", "Vector = None  #")
    assert src.rstrip().endswith("main()")
    ns = {"__name__": "render_shot_under_test"}
    exec(compile(src.rstrip()[:-len("main()")], "render_shot.py", "exec"), ns)  # noqa: S102  (our own file, without its main())
    return ns


def test_build_tree_creates_exactly_the_graph():
    rs = load_render_shot()
    mat = graph()["materials"][1]
    tree = Tree()
    nt = types.SimpleNamespace(nodes=_Nodes(tree), links=tree.links)
    rs["_image"] = lambda p: f"IMG:{p}"
    missing = []
    made = rs["build_tree"](nt, mat, missing, "material wood")
    assert missing == []
    assert [n.bl_idname for n in tree.made] == [n["type"] for n in mat["nodes"]]
    assert len(tree.linked) == len(mat["links"])
    assert made["tex"].image == f"IMG:{TEX}"
    tone = made["tone"].color_ramp
    assert tone.interpolation == "CONSTANT" and [e.position for e in tone.elements] == [0.0, 0.12, 0.45]
    assert made["base"].blend_type == "MULTIPLY" and made["base"].inputs[6].default_value == [*S.srgb_to_linear(S.palette()["paper"]), 1.0]
    assert made["flatten"].inputs[0].default_value == S.StyleTokens().texture_strength


class _Nodes:
    def __init__(self, tree):
        self.tree = tree

    def __iter__(self):
        return iter([])

    def new(self, t):
        return self.tree._new(t)

    def remove(self, n):
        pass


def test_the_light_profile_is_the_default_and_shadows_are_one_switch():
    light = S.StyleEngine().graph("eevee", camera={"lens_mm": 35, "focus_distance_m": 5.0})
    assert light["scene"]["eevee"]["use_shadows"] is False and light["key_light"]["use_shadow"] is False
    heavy = S.StyleEngine(S.StyleTokens(shadows=True)).graph("eevee", camera={"lens_mm": 35, "focus_distance_m": 5.0})
    assert heavy["scene"]["eevee"]["use_shadows"] is True and heavy["key_light"]["use_shadow"] is True
    assert light["scene"]["eevee"]["use_raytracing"] is False and light["scene"]["eevee"]["use_fast_gi"] is False


def test_a_material_may_override_the_texture_strength_inside_0_to_1():
    eng = S.StyleEngine()
    dflt = json.dumps(eng.material("c", "paper", texture=TEX, texture_mean=[0.5, 0.5, 0.5]))
    half = json.dumps(eng.material("c", "paper", texture=TEX, texture_mean=[0.5, 0.5, 0.5], strength=0.5))
    assert '"Factor": 0.5' in half and dflt != half
    with pytest.raises(ValueError, match="share 0..1"):
        eng.material("c", "paper", texture=TEX, strength=1.5)


# ---- WP-Q1: the soft shade mode's lit and rgb_soft paths ----------------------------------------------------------------------

def _q1(vid, **over):
    t = S.look_tokens(vid)
    if over:
        t = S.replace(t, art=S.replace(t.art, **over))
    mats = {"ink_test_m_skin": {"base": "kit_card"}, "coat": {"base": "support_blue"}}
    return S.StyleEngine(t).graph("eevee", camera=CAM, materials=mats, hdri="/c/sky.hdr", paper_texture="/c/paper.jpg")


def test_soft_mode_keeps_light_colour_and_uses_a_linear_ramp():
    g = _q1("q1_rgbsoft_pbrn_cinematic")
    skin = by_id(next(m for m in g["materials"] if m["name"] == "ink_test_m_skin"))
    coat = by_id(next(m for m in g["materials"] if m["name"] == "coat"))
    for n in (skin, coat):
        assert n["tone"]["ramp"]["interpolation"] == "LINEAR"
        assert [s[1][0] for s in n["tone"]["ramp"]["stops"]][0] == 0.0 and n["tone"]["ramp"]["stops"][-1][1][0] == 1.0
        assert n["lift"]["inputs"]["To Min"] == 0.3 and n["lift"]["inputs"]["To Max"] == 1.0   # half-lambert
        assert n["shade"]["props"]["blend_type"] == "MIX"
    m = next(x for x in g["materials"] if x["name"] == "coat")
    assert ["to_rgb", "Color", "lit", 7] in m["links"]        # the lit side is albedo x the light's own colour, never its grey
    assert ["tone", "Color", "shade", "Factor"] in m["links"] and ["luma", "Val", "lift", "Value"] in m["links"]
    assert by_id(m)["shadow"]["inputs"]["7"][:3] == [0.66, 0.68, 0.86]    # the set's cool shadow tint
    assert skin["shadow"]["inputs"]["7"][:3] == [0.82, 0.52, 0.46]        # skin shadows lean red-brown
    assert all(n["type"] != "ShaderNodeLayerWeight" for n in m["nodes"])  # the rim is a light now


def test_soft_lit_allows_only_matte_principled():
    g = _q1("q1_lit_pbrn_cinematic")
    assert S.check(g) == []
    for m in g["materials"]:
        n = by_id(m)
        assert n["bsdf"]["type"] == "ShaderNodeBsdfPrincipled" and ["bsdf", "BSDF", "out", "Surface"] in m["links"]
        assert not {"ShaderNodeEmission", "ShaderNodeShaderToRGB"} & {x["type"] for x in m["nodes"]}
    skin = by_id(next(m for m in g["materials"] if m["name"] == "ink_test_m_skin"))
    assert skin["bsdf"]["inputs"]["Subsurface Weight"] == 0.3
    assert "Subsurface Weight" not in by_id(next(m for m in g["materials"] if m["name"] == "coat"))["bsdf"]["inputs"]
    for key, val in (("Roughness", 0.5), ("Specular IOR Level", 0.5), ("Coat Weight", 0.2), ("Metallic", 1.0)):
        bad = json.loads(json.dumps(g))
        for n in bad["materials"][0]["nodes"]:
            if n["id"] == "bsdf":
                n["inputs"][key] = val
        bad["sha256"] = S.digest(bad)
        assert any("raw PBR look" in p for p in S.check(bad)), key
    toon = graph()
    toon["materials"] = g["materials"]   # the same matte Principled outside the lit path is still the raw PBR look
    assert any("raw PBR look" in p for p in S.check(toon))
    assert S.check(_q1("q1_lit_std_keyrim", lit_bsdf="diffuse", subsurface=0.0)) == []


def test_lit_path_refuses_shader_rims_halftone_and_ao_off_it():
    base = S.Look.from_dict(next(v for v in S.look_variants()["q1_variants"] if v["id"] == "q1_lit_pbrn_cinematic"))
    for over in ({"rim_mode": "shader"}, {"halftone": 0.2}, {"shade_path": "rgb_soft"}, {"shade_mode": "flat"},
                 {"subsurface": 0.3, "lit_bsdf": "diffuse"}, {"view_transform": "Filmic"}):
        with pytest.raises(ValueError):
            S.replace(base, **over)
    g = _q1("q1_rgbsoft_pbrn_keyrim")
    bad = json.loads(json.dumps(g))
    bad["scene"]["eevee"].update(use_fast_gi=True, fast_gi_method="AMBIENT_OCCLUSION_ONLY")
    bad["sha256"] = S.digest(bad)
    assert any("AO on under Shader to RGB" in p for p in S.check(bad))


def test_q1_knobs_at_their_defaults_keep_the_look_round_bytes():
    for v in S.look_variants()["variants"]:
        d = S.Look.from_dict(v).to_dict()
        assert not set(S.Q1_DEFAULTS) & set(d), v["id"]
    g = S.StyleEngine(S.look_tokens("v01_reference_soft3d")).graph("eevee", camera=CAM, materials={"coat": {"base": "support_blue"}})
    assert "lights" not in g and "fill_light" in g and g["scene"]["view_transform"] == "AgX"


def test_normal_softening_is_planned_for_the_cast_only_when_asked():
    assert _q1("q1_lit_pbrn_cinematic")["normal_soften"] == {"iterations": 6, "applies_to": "cast"}
    assert "normal_soften" not in _q1("q1_lit_pbrn_cinematic", normal_soften=0)


def test_material_class_comes_from_the_slot_or_the_name():
    assert S.material_class("ink_test_m_skin") == "skin" and S.material_class("ink_test_f_hair") == "hair"
    assert S.material_class("mco_male_ranger_support_blue", "costume") == "costume" and S.material_class("brick") == "set"


def test_raw_graphs_and_noise_blended_ground_pass_the_style_check():
    from explainer_engine.blender import world_kits as W
    tiled = {"base": "#6F9A47", "texture": "/c/a.jpg", "texture_mean": [0.2, 0.3, 0.1], "tile": 1.0, "strength": 0.85,
             "blend": {"images": ["/c/b.jpg", "/c/c.jpg"], "noise": 0.045}}
    for path in ("eevee", "cycles_safe"):
        doc = S.StyleEngine().graph(path, camera=CAM, paper_texture="/cache/p/paper.jpg",
                                    materials={"ground": tiled, "sea": {"raw": W.raw_graph("ocean")}, "smoke": {"raw": W.raw_graph("smoke")}})
        assert S.check(doc) == [], S.check(doc)
    ground = next(m for m in doc["materials"] if m["name"] == "ground")
    ids = {n["id"] for n in ground["nodes"]}
    assert {"tex_b", "tex_c", "ntex_a", "bmix_b"} <= ids and ["bmix_b", 2, "flatten", 7] in ground["links"]
    assert not [l for l in ground["links"] if l[0] == "tex" and l[2] == "flatten"]
    bad = {"nodes": [{"id": "out", "type": "ShaderNodeOutputMaterial"}, {"id": "p", "type": "ShaderNodeBsdfPrincipled"}], "links": []}
    assert any("Principled" in x for x in S.check(S.StyleEngine().graph("eevee", camera=CAM, materials={"x": {"raw": bad}}, paper_texture="/p.jpg")))
