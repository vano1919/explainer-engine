"""ICW-05c look round (plan rev. 2): look_variants.json -> style.Look -> a valid style_graph/1 and shot_spec/2 for every variant,
deterministic, inside the token ranges, each variant different on shading, light, finish and background (not only palette), the
old ICW-05 graphs unchanged, and the report's cost flag (over 2x B_light)."""
import json

import pytest

from explainer_engine.blender import style as S
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core import contracts as C

CAM = {"lens_mm": 40, "focus_distance_m": 4.5}
MATS = {"coat": {"base": "support_blue"}, "wood": {"base": "paper", "texture": "/c/wood.jpg", "texture_mean": [0.2, 0.1, 0.05]},
        "cloth": {"base": "answer_coral", "texture": "/c/atlas.png", "strength": 0.5, "slot": "costume"}}


def doc():
    return S.look_variants()


def graph(vid, **kw):
    return S.StyleEngine(S.look_tokens(vid)).graph("eevee", camera=CAM, materials=MATS, hdri="/c/sky.hdr",
                                                   paper_texture="/c/paper.jpg", **kw)


def by_id(g):
    return {n["id"]: n for n in g["nodes"]}


def test_ten_variants_on_a_slider_and_three_swatch_twins():
    d = doc()
    assert d["schema"] == "look_variants/1"
    assert [v["slider"] for v in d["variants"]] == list(range(1, 11))
    assert len({v["id"] for v in d["variants"]}) == 10
    assert d["swatch_twins"] == ["v01_reference_soft3d", "v05_gouache", "v09_painted_matte"]
    assert len(SS.look_ids()) == 13 and len(SS.look_ids(twins=False)) == 10


def test_every_variant_builds_a_clean_deterministic_graph():
    for vid in SS.look_ids():
        g = graph(vid)
        assert S.check(g) == [], vid
        assert g == graph(vid) and g["sha256"] == S.digest(g)
        assert g["tokens"]["art"]["id"] == vid and g["path"] == "eevee"


def test_variants_differ_on_more_than_palette():
    keys = ("shade_mode", "light_rig", "line_mode", "bg_mode", "kuwahara", "plate_kuwahara", "paper", "grain", "ramp", "brush",
            "halftone", "sky")
    seen = set()
    for v in doc()["variants"]:
        a = S.Look.from_dict(v).to_dict()
        sig = json.dumps({k: a[k] for k in keys}, sort_keys=True)
        assert sig not in seen, v["id"]
        seen.add(sig)
    assert {S.Look.from_dict(v).shade_mode for v in doc()["variants"]} == set(S.SHADE_MODES)
    assert {S.Look.from_dict(v).light_rig for v in doc()["variants"]} == set(S.LIGHT_RIGS)
    assert {S.Look.from_dict(v).line_mode for v in doc()["variants"]} == set(S.LINE_MODES)


def test_the_old_toon_graph_is_unchanged_by_the_look_round():
    g = S.StyleEngine(S.variant("B")).graph("eevee", camera=CAM, materials={"coat": {"base": "support_blue"}})
    assert "art" not in g["tokens"] and "fill_light" not in g and "camera_dof" not in g
    assert g["line_art"]["line_px_1440"] == 2.25 and "enabled" not in g["line_art"]


def test_the_reference_end_is_soft_lit_shadowed_and_blurred():
    g = graph("v01_reference_soft3d")
    m = by_id(g["materials"][0])
    assert m["tone"]["ramp"]["interpolation"] == "EASE"
    assert g["key_light"]["use_shadow"] and g["scene"]["eevee"]["use_shadows"] and g["key_light"]["energy"] == 1.0
    assert g["fill_light"]["use_shadow"] is False and g["fill_light"]["energy"] == 0.35
    assert g["camera_dof"] == {"use_dof": True, "focus_distance_m": 4.5, "fstop": 1.4}
    assert g["line_art"] == {"enabled": False, "line_px_1440": 0.0, "mode": "none"}
    assert any(n["type"] == "ShaderNodeTexEnvironment" for n in g["world"]["nodes"])
    # the dark end of the ramp leans cool, the lit end warm
    lo, hi = m["tone"]["ramp"]["stops"][0][1], m["tone"]["ramp"]["stops"][-1][1]
    assert lo[2] > lo[0] and hi[0] > hi[2]


def test_the_flat_end_has_no_live_light_and_a_painted_finish():
    g = graph("v09_painted_matte")
    m = by_id(g["materials"][0])
    assert "to_rgb" not in m and m["xyz"]["type"] == "ShaderNodeSeparateXYZ"
    assert g["key_light"]["energy"] == 0.0 and not g["key_light"]["use_shadow"] and "fill_light" not in g
    assert by_id(g["paper"])["kuwahara"]["inputs"]["Size"] == 12
    assert "camera_dof" not in g


def test_costume_keeps_its_own_atlas_and_sets_flatten_their_photo():
    g = graph("v01_reference_soft3d")
    mats = {m["name"]: by_id(m) for m in g["materials"]}
    assert mats["cloth"]["flatten"]["inputs"]["Factor"] == 0.9         # costume_keep: the atlas over 10 % of the tint
    assert mats["wood"]["flatten"]["inputs"]["Factor"] == 0.35         # texture_keep of a set texture
    toon = by_id(S.StyleEngine(S.variant("B")).material("cloth", "answer_coral", texture="/c/atlas.png", strength=0.5, slot="costume"))
    assert toon["flatten"]["inputs"]["Factor"] == 0.5                  # the ICW-05 path ignores the slot


def test_plate_background_mixes_a_painted_copy_by_depth():
    g = graph("v05_gouache")
    p = by_id(g["paper"])
    assert g["paper"]["passes"] == ["z"] and p["plate"]["inputs"]["Size"] == 14
    assert ["render", "Depth", "far", "Value"] in g["paper"]["links"]
    assert p["far"]["inputs"]["From Min"] == pytest.approx(4.5 * 1.15) and "brush" in by_id(g["materials"][0])


def test_swatch_twin_swaps_tokens_for_the_reference_swatches():
    plain, twin = graph("v05_gouache"), graph("v05_gouache_swatch")
    sw = doc()["swatch_map"]
    coat = lambda g: by_id(next(m for m in g["materials"] if m["name"] == "coat"))  # noqa: E731
    assert coat(twin)["base"]["inputs"]["6"] == S.rgba(sw["support_blue"])
    assert coat(plain)["base"]["inputs"]["6"] == S.rgba(S.palette()["support_blue"])
    assert twin["tokens"]["art"]["palette_map"] == "reference_swatches"
    with pytest.raises(KeyError):
        S.look_tokens("v02_painterly_3d_swatch")


def test_line_modes_and_widths():
    assert graph("v10_ink_accent")["line_art"]["ink_rgba"] == S.rgba(S.palette()["ink"])
    faint = graph("v04_painted_cel")["line_art"]
    assert faint["mode"] == "faint" and faint["opacity"] == 0.4 and faint["line_px_1440"] == 1.5
    assert graph("v06_storybook")["line_art"]["ink_rgba"] == S.rgba(S.palette()["kit_shadow"])


@pytest.mark.parametrize("bad", [{"shade_mode": "glossy"}, {"light_rig": "studio"}, {"grain": 1.5}, {"ramp": [[0.5, 1.0], [0.2, 0.5]]},
                                 {"fstop": 0.1}, {"kuwahara": 60}, {"costume_keep": 2}, {"line_mode": "dark", "line_px": 0}])
def test_token_ranges_are_refused(bad):
    with pytest.raises(ValueError):
        S.Look.from_dict({"id": "x", **bad})


def test_every_variant_is_a_master_spec_with_its_own_cache_key(tmp_path):
    keys = set()
    for vid in SS.look_ids():
        _, tokens = SS.style_for(vid)
        g = graph(vid)
        scene = {"kind": "described", "objects": [], "camera": CAM, "style": g}
        spec = SS.spec_for("dialogue_cu", vid, tokens, scene=scene, frames=24)
        assert spec["lane"] == "VIDEO_3D" and spec["recipe"] == "blender_eevee/1"
        fails = [f for f in C.errors({**spec}) if f["severity"] == "FAIL"] if hasattr(C, "errors") else []
        assert not fails, (vid, fails)
        from explainer_engine.core import shot_cache
        keys.add(shot_cache.key(spec))
    assert len(keys) == 13


def _write_round(root, rows):
    for i, (vid, secs) in enumerate(rows):
        d = root / f"look-{vid}"
        (d / "frames").mkdir(parents=True)
        art = {"id": vid, "slider": -1} if vid == "B_light" else S.look_tokens(vid).art.to_dict()
        out = []
        for sc, s in secs.items():
            from PIL import Image
            Image.new("RGB", (64, 36), (200, 100 + i * 10, 50)).save(d / "frames" / f"{sc}_{vid}.png")
            out.append({"scene": sc, "variant": vid, "label": vid, "slider": art["slider"], "frames": 24 if sc != "establishing" else 1,
                        "frame_rel": f"frames/{sc}_{vid}.png", "times": {"steady_median_s": s, "first_s": s * 2}, "art": art})
        (d / "looks.json").write_text(json.dumps({"schema": "look_round/1", "rows": out}), encoding="utf-8")


def test_report_flags_a_look_over_twice_b_light_and_the_collage_has_its_rows(tmp_path):
    _write_round(tmp_path, [("B_light", {"dialogue_cu": 10.0, "battle_wide": 20.0}),
                            ("v01_reference_soft3d", {"dialogue_cu": 25.0, "battle_wide": 30.0, "establishing": 9.0}),
                            ("v09_painted_matte", {"dialogue_cu": 8.0, "battle_wide": 15.0, "establishing": 5.0})])
    rep = SS.look_report(tmp_path)
    v = {x["variant"]: x for x in rep["variants"]}
    assert v["v01_reference_soft3d"]["over_2x"] == ["dialogue_cu"] and v["v01_reference_soft3d"]["ratio_to_b_light"]["dialogue_cu"] == 2.5
    assert v["v09_painted_matte"]["over_2x"] == [] and v["v09_painted_matte"]["bp173"] == "none drawn"
    assert "**over 2x**" in (tmp_path / "look_round_table.md").read_text(encoding="utf-8")
    from PIL import Image
    path = SS.look_collage(tmp_path, cell_w=160)
    with Image.open(path) as im:
        assert im.size[1] > 2 * 90   # two look rows (B_light is the yardstick, not a row)
