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
