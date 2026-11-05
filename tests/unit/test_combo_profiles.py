"""The overnight Q1 combinations C1-C4 (combo_profiles.json) and the knobs they added: native character shading (C2),
the front-biased preset key, the per-character skin lift and Perfectly Normal faces (C4)."""
import json
import math
import types

import pytest

from explainer_engine.blender import combos as CB
from explainer_engine.blender import style as S
from tests.unit.test_blender_style import load_render_shot
from tests.unit.test_light_rigs import _Members

CAM = {"lens_mm": 40, "focus_distance_m": 4.5}
MATS = {"rain_skin": {"base": "kit_card"}, "rain_hair": {"base": "ink"},
        "rain_tunic": {"base": "support_blue", "slot": "costume"}, "stone": {"base": "support_blue"}}


def graph(cid, era="E2"):
    return S.StyleEngine(CB.tokens(cid, era)).graph("eevee", camera=CAM, materials=MATS, hdri="/c/sky.hdr",
                                                    paper_texture="/c/paper.jpg")


def test_the_table_loads_c2_is_the_default_and_every_era_brings_its_preset():
    doc = CB.load()
    assert doc["default"] == "C2" and sorted(doc["combos"]) == ["C1", "C2", "C3", "C4"]
    assert {e: CB.tokens("C1", e).art.light_preset for e in doc["eras"]} == {e: x["light_preset"] for e, x in doc["eras"].items()}


@pytest.mark.parametrize("cid", ["C1", "C2", "C3", "C4"])
def test_every_combination_makes_a_clean_graph(cid):
    assert S.check(graph(cid)) == []


def test_c2_keeps_the_cast_own_materials_and_paints_the_set():
    g = graph("C2")
    mats = {m["name"]: m for m in g["materials"]}
    assert all(mats[n].get("native") for n in ("rain_skin", "rain_hair", "rain_tunic")) and not mats["stone"].get("native")
    assert mats["rain_tunic"]["class"] == "costume" and mats["rain_skin"]["nodes"] == []
    assert g["native_classes"] == ["skin", "hair", "eyes", "costume"]
    bad = json.loads(json.dumps(g))
    next(m for m in bad["materials"] if m["name"] == "stone").update(native=True, nodes=[], links=[], **{"class": "set"})
    bad["sha256"] = S.digest(bad)
    assert any("native only for a class the look lists" in p for p in S.check(bad))


def test_the_preset_key_turns_to_the_camera_side_and_the_lift_is_linked_to_its_character():
    L = {x["name"]: x for x in graph("C2")["lights"]}
    k = L["key"]["aim_with_cast"]
    assert k["from"] == "front" and S.FRONT_KEY_BAND[0] <= abs(k["azimuth_offset_deg"]) <= S.FRONT_KEY_BAND[1]
    lift = L["lift_rain"]
    assert lift["link"] == "char:rain" and not lift["use_shadow"] and lift["specular_factor"] == 0.0
    assert lift["energy"] == round(L["key"]["energy"] * 0.2, 6)
    g = graph("C2")
    next(x for x in g["lights"] if x["name"] == "lift_rain")["use_shadow"] = True
    g["sha256"] = S.digest(g)
    assert any("skin lift" in p for p in S.check(g))


def test_a_preset_off_the_front_band_is_refused(tmp_path):
    doc = json.loads(S.LIGHT_PRESETS_PATH.read_text(encoding="utf-8"))
    doc["presets"]["golden_hour"]["key"]["front_offset_deg"] = 70.0
    p = tmp_path / "p.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="front-biased band"):
        S.light_presets(p)


def test_rgb_soft_lifts_only_the_named_character_skin_tint():
    t = S.look_tokens("q1_rgbsoft_pbrn_cinematic")
    mats = {"rain_skin": {"base": "kit_card"}, "bran_skin": {"base": "kit_card"}}
    plain = S.StyleEngine(t).graph("eevee", camera=CAM, materials=mats, hdri=None, paper_texture=None)
    t2 = S.replace(t, art=S.replace(t.art, skin_lift=(("rain", 0.5),)))
    lifted = S.StyleEngine(t2).graph("eevee", camera=CAM, materials=mats, hdri=None, paper_texture=None)
    def tint(g, n):
        mat = next(m for m in g["materials"] if m["name"] == n)
        return next(x for x in mat["nodes"] if x["id"] == "shadow")["inputs"]["7"]

    assert tint(lifted, "bran_skin") == tint(plain, "bran_skin")
    assert all(b > a for a, b in zip(tint(plain, "rain_skin")[:3], tint(lifted, "rain_skin")[:3]))
    assert S.check(lifted) == []


def test_c4_asks_for_perfectly_normal_and_one_face_method_at_a_time():
    g = graph("C4")
    assert g["perfectly_normal"] == {"converge": 0.6, "applies_to": "cast", "extension": "perfectly_normal", "version": "0.0.3"}
    assert "normal_soften" not in g
    a = CB.tokens("C4", "E2").art
    with pytest.raises(ValueError, match="one face-normal method"):
        S.replace(a, normal_soften=4)
    luma = S.look_tokens("v01_reference_soft3d").art
    with pytest.raises(ValueError, match="need real lights"):
        S.replace(luma, native_classes=("skin",))


def test_the_combination_table_refuses_a_mismatched_character_path(tmp_path):
    doc = json.loads(CB.PATH.read_text(encoding="utf-8"))
    doc["combos"]["C2"]["characters"] = "toon"
    p = tmp_path / "c.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="does not match"):
        CB.load(p)


def test_build_lights_links_a_lift_to_its_character_and_fronts_the_key_with_a_cast():
    rs = load_render_shot()
    objs = []

    def light(name, kind):
        return types.SimpleNamespace(name=name, type=kind, energy=0, color=None, use_shadow=None, angle=0,
                                     shadow_filter_radius=0, use_shadow_jitter=None, specular_factor=1, diffuse_factor=1)

    def obj(name, data):
        o = types.SimpleNamespace(name=name, data=data, rotation_euler=None,
                                  light_linking=types.SimpleNamespace(receiver_collection=None))
        objs.append(o)
        return o

    rs["bpy"] = types.SimpleNamespace(data=types.SimpleNamespace(
        lights=types.SimpleNamespace(new=light), objects=types.SimpleNamespace(new=obj),
        collections=types.SimpleNamespace(new=lambda name: types.SimpleNamespace(name=name, objects=_Members()))))
    rs["_camera_aim"] = lambda scene, el, az, front=False: ("front" if front else "behind", el, az)
    scene = types.SimpleNamespace(collection=types.SimpleNamespace(objects=_Members()))
    specs = graph("C2")["lights"]
    missing = []
    done = rs["build_lights"](scene, specs, ["rain_head", "bran_head"], missing, {"rain": ["rain_head"], "bran": ["bran_head"]})
    by = {o.name: o for o in objs}
    assert missing == [] and list(by["lift_rain"].light_linking.receiver_collection.objects) == ["rain_head"]
    assert by["key"].rotation_euler[0] == "front" and by["rim_a"].rotation_euler[0] == "behind"
    assert next(d for d in done if d["name"] == "key")["front_offset_deg"] == specs[0]["aim_with_cast"]["azimuth_offset_deg"]
    objs.clear()
    done = rs["build_lights"](scene, specs, [], missing, {})
    assert by["key"] is not None and objs[0].rotation_euler == specs[0]["rotation_euler"]
    assert {"name": "lift_rain", "skipped": "no rain in the shot"} in done


def test_perfectly_normal_is_pinned_licensed_and_unpacked_by_sha(tmp_path):
    import io
    import zipfile

    from explainer_engine.blender import face_normals as FN
    from explainer_engine.core.errors import ConfigError
    p = FN.pin()
    combo = next(x for x in CB.load()["combos"]["C4"]["extensions"] if x["id"] == "perfectly_normal")
    assert (p["sha256"], p["version"], p["url"]) == (combo["sha256"], combo["version"], combo["url"])
    lic = json.loads((CB.PATH.parents[1] / "assets" / "licence_sources.json").read_text(encoding="utf-8"))
    assert "perfectly_normal" in json.dumps(lic) and p["sha256"] in json.dumps(lic)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr(FN.MEMBER, b"BLENDER-fake")
    with pytest.raises(ConfigError, match="differs from the pin"):   # a fake zip never passes the pin
        FN.ensure(tmp_path, download=lambda url, dst: dst.write_bytes(buf.getvalue()))


def test_a_close_up_takes_the_character_key_and_keeps_the_era_rims():
    t = CB.tokens("C2", "E2", close_up=True)
    g = S.StyleEngine(t).graph("eevee", camera=CAM, materials=MATS, hdri=None, paper_texture=None)
    L = {x["name"]: x for x in g["lights"]}
    ck = S.character_key()
    assert L["key"]["energy"] == ck["key"]["energy"] and L["key"]["aim"]["azimuth_offset_deg"] == 35.0
    assert L["key"]["aim"]["from"] == "front" and L["key"]["aim"]["elevation_deg"] > 0
    assert L["fill"]["energy"] == round(ck["key"]["energy"] * 0.25, 6) and L["fill"]["aim"]["azimuth_offset_deg"] == -35.0
    assert not L["fill"]["use_shadow"] and {"rim_a", "rim_b", "lift_rain"} <= set(L) and S.check(g) == []
    with pytest.raises(ValueError, match="names? a light_preset"):
        S.replace(S.look_tokens("q1_lit_pbrn_cinematic").art, character_key=True)


def test_the_character_key_stays_front_biased_with_its_fill_opposite(tmp_path):
    doc = json.loads(S.LIGHT_PRESETS_PATH.read_text(encoding="utf-8"))
    doc["character_key"]["fill"]["front_offset_deg"] = 35.0
    p = tmp_path / "p.json"
    p.write_text(json.dumps(doc), encoding="utf-8")
    with pytest.raises(ValueError, match="opposite"):
        S.character_key(p)


def test_a_look_id_carries_the_era_light_for_every_cli():
    from explainer_engine.blender import style_sheets as SS
    path, t = SS.style_for("q1_c2_native_skin@E1")
    assert path == "eevee" and t.art.light_preset == "noon_epic" and not t.art.character_key
    assert S.look_tokens("q1_c2_native_skin@overcast_day+cu").art.light_preset == "overcast_day"
    assert S.look_tokens("q1_c2_native_skin@E3+cu").art.character_key is True
    assert S.look_tokens("q1_c1_lit_preset@E4").art.light_preset == CB.load()["eras"]["E4"]["light_preset"]
    for bad in ("q1_c2_native_skin@E9", "q1_c2_native_skin@E1+wide", "q1_lit_pbrn_cinematic@E1"):
        with pytest.raises(KeyError):
            S.look_tokens(bad)
    spec = SS.spec_for("dialogue_cu", "q1_c2_native_skin@E1", t)
    assert spec["schema"] == "shot_spec/3" and spec["render"]["profile"] == "eevee_painterly"


def test_perfectly_normal_runs_outward_between_the_material_index_guards(tmp_path, monkeypatch):
    rs = load_render_shot()
    blend = tmp_path / "pn.blend"
    blend.write_bytes(b"x")
    monkeypatch.setenv("EE_PERFECTLY_NORMAL_BLEND", str(blend))

    class Inputs(dict):
        pass

    def group(name, sockets=()):
        items = [types.SimpleNamespace(in_out="INPUT", name=n, identifier=f"S_{n}") for n in sockets]
        return types.SimpleNamespace(name=name, is_modifier=False, interface=types.SimpleNamespace(items_tree=items))

    groups = {n: group(n, s) for n, s in (("Manip Verts: (Re)create", ()), ("Manip Verts: Tweak", ("Converge",)),
                                          ("Manip Verts: Apply", ("Ready to Apply",)),
                                          ("wpq1_pn_keep_matidx", ()), ("wpq1_pn_restore_matidx", ()))}

    class Mods(list):
        def new(self, name, kind):
            m = types.SimpleNamespace(name=name, node_group=None, properties=types.SimpleNamespace(
                inputs=Inputs({f"S_{n}": {"value": None} for n in ("Converge", "Ready to Apply")})))
            self.append(m)
            return m

    class Groups(dict):
        def __contains__(self, k):
            return dict.__contains__(self, k)

    rs["bpy"] = types.SimpleNamespace(data=types.SimpleNamespace(node_groups=Groups(groups)))
    ob = types.SimpleNamespace(modifiers=Mods(), data=types.SimpleNamespace(has_custom_normals=False, shade_smooth=lambda: None))
    missing = []
    assert rs["perfectly_normal"]([ob], {"converge": 0.6}, missing) == 1 and missing == []
    assert [m.node_group.name for m in ob.modifiers] == ["wpq1_pn_keep_matidx", "Manip Verts: (Re)create", "Manip Verts: Tweak",
                                                          "Manip Verts: Apply", "wpq1_pn_restore_matidx"]
    assert ob.modifiers[2].properties.inputs["S_Converge"]["value"] == -0.6   # outward: PN's positive Converge points inward
    assert ob.modifiers[3].properties.inputs["S_Ready to Apply"]["value"] is True
    monkeypatch.delenv("EE_PERFECTLY_NORMAL_BLEND")
    assert rs["perfectly_normal"]([ob], {"converge": 0.6}, missing) == 0 and "EE_PERFECTLY_NORMAL_BLEND" in missing[0]


@pytest.mark.parametrize("cid", ["C1", "C2", "C3", "C4"])
def test_every_cell_gets_the_depth_haze_from_the_mist_pass(cid):
    p = graph(cid)["paper"]
    assert p["passes"] == ["z"] and p["mist"]["falloff"] == "QUADRATIC" and 0 < p["mist"]["start_m"] < p["mist"]["depth_m"]
    ids = [n["id"] for n in p["nodes"]]
    assert ids.index("haze_mix") > ids.index("kuwahara")   # the painted frame fades into the haze, not the other way round
    assert ["render", "Depth", "haze_ramp", "Value"] in p["links"] and not any(x[1] == "Mist" for x in p["links"])
    geo = next(n for n in p["nodes"] if n["id"] == "haze_geo")   # the sky (depth ~1e10) is masked out, geometry gets the haze
    assert geo["props"]["operation"] == "LESS_THAN" and geo["inputs"]["1"] == S.HAZE_SKY_M and "z" in p["passes"]
    ramp = next(n for n in p["nodes"] if n["id"] == "haze_ramp")["inputs"]
    assert ramp["From Max"] == p["mist"]["start_m"] + p["mist"]["depth_m"]
    mix = next(n for n in p["nodes"] if n["id"] == "haze_mix")
    assert mix["inputs"]["7"][:3] == list(CB.tokens(cid, "E2").art.haze_colour)


def test_haze_is_off_by_default_and_bounded():
    assert "mist" not in S.StyleEngine(S.look_tokens("q1_lit_pbrn_cinematic")).graph(
        "eevee", camera=CAM, materials=MATS, hdri=None, paper_texture=None)["paper"]
    a = CB.tokens("C2", "E2").art
    for bad in ({"haze": 0.8}, {"haze_depth_m": 0.0}, {"haze_colour": (2.0, 0.5, 0.5)}):
        with pytest.raises(ValueError, match="haze"):
            S.replace(a, **bad)


def _graph_at(look_id, focus_m):
    cam = {"lens_mm": 26, "focus_distance_m": focus_m}
    return S.StyleEngine(S.look_tokens(look_id)).graph("eevee", camera=cam, materials=MATS, hdri="/c/sky.hdr",
                                                       paper_texture="/c/paper.jpg")


def test_golden_hour_is_a_low_warm_shadowed_sun_that_rakes_a_world_shot_and_fronts_a_character_shot():
    """Fable 2026-11-05 22:51 UTC: E2's sun must read in the world shot (low, warm, shadows on), not turn to the camera."""
    k = S.light_presets()["golden_hour"]["key"]
    assert k["elevation_deg"] <= 12.0 and k["colour"][0] > k["colour"][1] > k["colour"][2]
    world = {x["name"]: x for x in _graph_at("q1_c2_native_skin@E2", 49.0)["lights"]}["key"]
    assert world["use_shadow"] and "aim_with_cast" not in world
    assert world["aim"] == {"relative_to": "camera", "elevation_deg": k["elevation_deg"], "azimuth_offset_deg": k["world_offset_deg"]}
    assert 90.0 <= abs(k["world_offset_deg"]) <= 135.0          # from the camera's side: the long shadows run across the frame
    close = {x["name"]: x for x in _graph_at("q1_c2_native_skin@E2", S.CHARACTER_SHOT_M - 0.5)["lights"]}["key"]
    assert close["aim_with_cast"]["from"] == "front" and "aim" not in close
    noon = {x["name"]: x for x in _graph_at("q1_c2_native_skin@E1", 49.0)["lights"]}["key"]
    assert "aim" not in noon and "aim_with_cast" not in noon   # a preset without world_offset_deg keeps its world-fixed sun


def test_golden_hour_warms_the_hdri_sky_with_a_band_over_the_horizon():
    w = _graph_at("q1_c2_native_skin@E2", 49.0)["world"]
    sky = S.light_presets()["golden_hour"]["sky"]
    ids = {n["id"]: n for n in w["nodes"]}
    assert ids["sky_warm"]["inputs"]["7"][:3] == sky["tint"] and ids["glow_mix"]["inputs"]["7"][:3] == sky["horizon"]
    assert ids["glow_h"]["inputs"]["To Min"] == sky["glow"] and ids["glow_h"]["inputs"]["To Max"] == 0.0
    assert ["glow_mix", 2, "sky_mix", 7] in w["links"] and ["sky_warm", 2, "sky_mix", 7] not in w["links"]
    plain = _graph_at("q1_c2_native_skin@E1", 49.0)["world"]      # noon_epic has no sky block: the HDRI path as before
    assert "glow_mix" not in {n["id"] for n in plain["nodes"]} and ["sky_warm", 2, "sky_mix", 7] in plain["links"]


def test_a_bad_preset_sky_or_world_offset_is_refused(tmp_path):
    doc = json.loads(S.LIGHT_PRESETS_PATH.read_text(encoding="utf-8"))
    bad = json.loads(json.dumps(doc))
    bad["presets"]["golden_hour"]["sky"]["glow"] = 2.0
    (tmp_path / "a.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        S.light_presets(tmp_path / "a.json")
    bad = json.loads(json.dumps(doc))
    bad["presets"]["golden_hour"]["key"]["world_offset_deg"] = 270.0
    (tmp_path / "b.json").write_text(json.dumps(bad), encoding="utf-8")
    with pytest.raises(ValueError):
        S.light_presets(tmp_path / "b.json")


def test_golden_hour_opens_a_world_shot_by_half_a_stop_and_leaves_a_close_up_alone():
    ev = S.light_presets()["golden_hour"]["world_exposure_ev"]
    assert ev == 0.5 and _graph_at("q1_c2_native_skin@E2", 49.0)["scene"]["exposure"] == ev
    assert "exposure" not in _graph_at("q1_c2_native_skin@E2", 3.0)["scene"]
    assert "exposure" not in _graph_at("q1_c2_native_skin@E1", 49.0)["scene"]
