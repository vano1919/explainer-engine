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
