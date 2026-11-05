"""WP-Q1 (INTEGRATION_PLAN WP-Q1): the soft shade mode's lit and rgb_soft paths, the coloured light rigs of
``style.StyleEngine.lights`` and their Blender side (``bpy/render_shot.build_lights``) on a recorded fake of bpy."""
import math
import types

import pytest

from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core import contracts as C
from tests.unit.test_blender_style import load_render_shot

CAM = {"lens_mm": 40, "focus_distance_m": 4.5}
MATS = {"ink_test_m_skin": {"base": "kit_card"}, "coat": {"base": "support_blue"},
        "mco_male_ranger_support_blue": {"base": "support_blue", "texture": "/c/atlas.png", "strength": 0.9, "slot": "costume"}}
Q1 = ("q1_lit_pbrn_cinematic", "q1_lit_std_keyrim", "q1_rgbsoft_pbrn_cinematic", "q1_rgbsoft_pbrn_keyrim")


def graph(vid, **over):
    t = S.look_tokens(vid)
    if over:
        t = S.replace(t, art=S.replace(t.art, **over))
    return S.StyleEngine(t).graph("eevee", camera=CAM, materials=MATS, hdri="/c/sky.hdr", paper_texture="/c/paper.jpg")


def lights(g):
    return {x["name"]: x for x in g["lights"]}


@pytest.mark.parametrize("vid", Q1)
def test_every_q1_variant_makes_a_clean_graph_and_a_valid_shot_spec_3(vid):
    g = graph(vid)
    assert S.check(g) == []
    spec = SS.spec_for("dialogue_cu", vid, S.look_tokens(vid), scene={"probe": 1})
    assert spec["schema"] == "shot_spec/3" and spec["render"]["profile"] == "eevee_painterly"
    assert "line_weight_px" not in spec["look"] and spec["look"]["line_mode"] == "none"
    assert C.errors(spec) == []


def test_cinematic_makes_three_lights_rim_linked_to_the_cast_fill_and_rim_shadowless():
    L = lights(graph("q1_lit_pbrn_cinematic"))
    assert set(L) == {"key", "fill", "rim"}
    assert L["rim"]["link"] == "cast" and L["fill"]["link"] is None and L["key"]["link"] is None
    assert not L["fill"]["use_shadow"] and not L["rim"]["use_shadow"]
    assert L["fill"]["specular_factor"] == 0.0 and L["rim"]["specular_factor"] <= 0.3
    assert L["key"]["use_shadow"] and math.radians(5) <= L["key"]["angle_rad"] <= math.radians(10)
    assert L["key"]["shadow_filter_radius"] == 2.5 and L["key"]["use_shadow_jitter"] is False
    assert L["rim"]["aim"]["relative_to"] == "camera"
    assert L["key"]["color"] != L["fill"]["color"]   # warm key, cool fill: the light keeps its colour


def test_key_disc_is_clamped_into_5_to_10_degrees():
    assert lights(graph("q1_lit_pbrn_cinematic", shadow_softness_deg=1.0))["key"]["angle_rad"] == round(math.radians(5), 6)
    assert lights(graph("q1_lit_pbrn_cinematic", shadow_softness_deg=30.0))["key"]["angle_rad"] == round(math.radians(10), 6)


def test_key_rim_casts_no_shadow_flat_key_is_alone_ambient_only_has_none():
    g = graph("q1_lit_std_keyrim")
    assert not any(x["use_shadow"] for x in g["lights"]) and g["scene"]["eevee"]["use_shadows"] is False
    assert list(lights(graph("q1_lit_std_keyrim", light_rig="flat_key"))) == ["key"]
    assert graph("q1_lit_std_keyrim", light_rig="ambient_only", rim_strength=0.0)["lights"] == []


def test_check_refuses_a_shadowed_fill_an_unlinked_rim_and_a_hard_shadow_key():
    g = graph("q1_lit_pbrn_cinematic")
    bad = dict(g, lights=[dict(x, use_shadow=True) if x["name"] == "fill" else x for x in g["lights"]])
    bad["sha256"] = S.digest(bad)
    assert any("fill and rim" in p for p in S.check(bad))
    bad = dict(g, lights=[dict(x, link=None) if x["name"] == "rim" else x for x in g["lights"]])
    bad["sha256"] = S.digest(bad)
    assert any("light-linked to the cast" in p for p in S.check(bad))
    bad = dict(g, lights=[dict(x, angle_rad=math.radians(1)) if x["name"] == "key" else x for x in g["lights"]])
    bad["sha256"] = S.digest(bad)
    assert any("5-10 degree" in p for p in S.check(bad))


def test_view_transform_and_ao_follow_the_path():
    lit, soft = graph("q1_lit_pbrn_cinematic")["scene"], graph("q1_rgbsoft_pbrn_cinematic")["scene"]
    assert lit["view_transform"] == "Khronos PBR Neutral" and lit["look"] == "None"
    assert lit["eevee"]["use_fast_gi"] and lit["eevee"]["fast_gi_method"] == "AMBIENT_OCCLUSION_ONLY"
    assert soft["eevee"]["use_fast_gi"] is False   # Shader to RGB is unreliable with AO (9.1)
    assert graph("q1_lit_std_keyrim")["scene"]["view_transform"] == "Standard"


class _Members(list):
    def link(self, ob):
        self.append(ob)


def test_build_lights_links_the_rim_to_the_cast_and_leaves_it_out_without_one():
    rs = load_render_shot()
    made = {"lights": [], "objects": []}

    def light(name, kind):
        d = types.SimpleNamespace(name=name, type=kind, energy=0, color=None, use_shadow=None, angle=0, shadow_filter_radius=0,
                                  use_shadow_jitter=None, specular_factor=1, diffuse_factor=1)
        made["lights"].append(d)
        return d

    def obj(name, data):
        o = types.SimpleNamespace(name=name, data=data, rotation_euler=None,
                                  light_linking=types.SimpleNamespace(receiver_collection=None))
        made["objects"].append(o)
        return o

    rs["bpy"] = types.SimpleNamespace(data=types.SimpleNamespace(
        lights=types.SimpleNamespace(new=light), objects=types.SimpleNamespace(new=obj),
        collections=types.SimpleNamespace(new=lambda name: types.SimpleNamespace(name=name, objects=_Members()))))
    rs["_camera_aim"] = lambda scene, el, az: ("aimed", el, az)
    scene = types.SimpleNamespace(collection=types.SimpleNamespace(objects=_Members()))
    specs = graph("q1_lit_pbrn_cinematic")["lights"]
    missing = []
    done = rs["build_lights"](scene, specs, ["head", "body"], missing)
    assert missing == [] and [d["name"] for d in done] == ["key", "fill", "rim"] and done[2]["receivers"] == 2
    key, fill, rim = made["objects"]
    assert list(rim.light_linking.receiver_collection.objects) == ["head", "body"]
    assert key.light_linking.receiver_collection is None and fill.light_linking.receiver_collection is None
    assert rim.rotation_euler == ("aimed", 35.0, 25.0) and key.rotation_euler == specs[0]["rotation_euler"]
    assert key.data.use_shadow is True and key.data.angle == specs[0]["angle_rad"] and key.data.shadow_filter_radius == 2.5
    assert fill.data.specular_factor == 0.0 and rim.data.specular_factor == 0.3
    assert rs["build_lights"](scene, specs, [], missing)[-1] == {"name": "rim", "skipped": "no cast in the shot"}


@pytest.mark.parametrize("name", sorted(S.light_presets()))
def test_every_light_preset_keeps_the_wing_it_rule(name):
    g = graph("q1_lit_pbrn_cinematic", light_preset=name)
    assert S.check(g) == []
    L = lights(g)
    assert [n for n, x in L.items() if x["use_shadow"]] == ["key"]            # only the sun casts a shadow
    rims = [x for n, x in L.items() if n.startswith("rim")]
    assert len(rims) == 2 and all(x["link"] == "cast" and x["specular_factor"] <= 0.3 for x in rims)
    assert rims[0]["color"] != rims[1]["color"]                                # two colourable rims
    tint = S.light_presets()[name]["world_tint"]
    light = next(n for n in g["world"]["nodes"] if n["id"] == "light")
    assert light["inputs"]["Color"][:3] == tint["colour"] and light["inputs"]["Strength"] == tint["strength"]


def test_a_preset_needs_a_lit_path_and_a_known_name():
    base = S.Look.from_dict(next(v for v in S.look_variants()["q1_variants"] if v["id"] == "q1_lit_pbrn_cinematic"))
    with pytest.raises(ValueError):
        S.replace(base, light_preset="disco")
    with pytest.raises(ValueError):
        S.Look(id="x", light_preset="golden_hour")   # the luma path reads the key as an N.L probe
