"""The stone-age pilot's approach test (the creator, 2026-11-07 12:48 UTC): six layouts, three scenes built two ways."""

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.blender import stoneage_test_layouts as ST
from explainer_engine.blender import world_kits as WK
from explainer_engine.blender import stoneage_qwen_jobs as SQ
from explainer_engine.production import paid_preflight as PF


def test_six_layouts_are_in_world_layouts_and_dress_their_shot():
    doc = WK.layouts()
    for lid in ST.ids():
        assert lid in doc["layouts"], lid
    assert len(ST.ids()) == 6
    for lid in ST.ids():
        scene = lid.split("_")[1]
        assert WK.dressing(lid, ST.SHOT[scene], doc=doc)   # every name in in_shot is placed (unknown names are refused)


def test_both_ways_hold_the_same_story_props_cast_and_camera():
    for scene in ST.SCENES:
        a, b = ST.layout(scene, "block"), ST.layout(scene, "flat3")
        assert a["cast"] == b["cast"] and a["shots"] == b["shots"] and a["cards"] == b["cards"] and a["tags"] == b["tags"]
        story = {n for n in (x["name"] for x in a["blocks"]) if n.startswith(("mammoth_", "hut_", "paint_", "sky_", "hand_", "hearth_", "camp_"))}
        assert story <= {x["name"] for x in b["blocks"]}


def test_every_qwen_prompt_is_composed_and_passes_the_style_check():
    doc = WK.layouts()["layouts"]
    for lid in ST.ids():
        scene = lid.split("_")[1]
        p = PS.prompts(ST.SHOT[scene], layout=doc[lid])
        assert p["qwen"].startswith("xworld style, Image 1 is the scene")
        assert p["qwen_words"] <= PS.QWEN_MAX_WORDS
        assert "everyone stays in frame" in p["ltx"] and "Static camera." in p["ltx"]



def test_superseded_blender_reference_jobs_are_blocked_by_d120_preflight():
    blender_jobs = SQ.jobs({"sa_cave_flat3.png": "0" * 64})
    findings = PF.qwen(blender_jobs)
    assert any("RF-01" in finding and "flat3" in finding for finding in findings)


def test_qwen_first_asset_jobs_are_blocked_until_d121_metadata_and_rf05_are_fixed():
    findings = PF.qwen(SQ.asset_jobs())
    assert any("HI-01" in finding and "in_shot" in finding for finding in findings)
    assert any("RF-05" in finding and "variant_of" in finding for finding in findings)
