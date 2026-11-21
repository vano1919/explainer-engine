"""KP-50..55 (creator 2026-11-07 14:42 UTC, Argon's review of the 6-photo test): screen sides from the camera, counts, distinct
proxies, clutter clashes, the Blender gate and the frozen settle."""
import numpy as np

from explainer_engine.blender import pilot_stills as PS
from explainer_engine.blender import stoneage_test_layouts as S
from explainer_engine.qa import blender_gate as G
from explainer_engine.scripting import shot_prompt_lint as SPL


def test_screen_side_thresholds():
    assert S.screen_side(0.2) == "on the left" and S.screen_side(0.5) == "in the middle" and S.screen_side(0.8) == "on the right"
    cam = [[0, 0, 1.5], None, [0, 10, 1.5], None, 24, 1]
    assert abs(S.project(cam, [0, 10, 1.5])[0] - 0.5) < 1e-9
    assert S.project(cam, [-3, 10, 1.5])[0] < 0.5 < S.project(cam, [3, 10, 1.5])[0]


def test_every_named_subject_has_a_side_and_counts_are_words():
    for sc in S.SCENES:
        for w in S.WAYS:
            L = S.layout(sc, w)
            for n in S.SUBJECTS[sc]:
                assert any(x in L["tags"][n] for x in ("on the left", "in the middle", "on the right")), (sc, w, n)
            q = PS.prompts(S.SHOT[sc], layout=L)["qwen"]
            assert q.count(" on the ") + q.count(" in the middle") >= len(S.SUBJECTS[sc])
    camp = S.layout("camp", "flat3")
    assert camp["tags"]["hut_0_wall"].startswith("four ")
    assert "a round hut" not in PS.prompts(S.SHOT["camp"], layout=camp)["qwen"]


def test_people_get_distinct_proxies():
    for sc in ("cave", "camp"):
        L = S.layout(sc, "flat3")
        cols = {}
        for b in L["blocks"]:
            if b.get("name", "").endswith("_head_proxy"):
                cols[b["name"]] = b["colour"]
        people = [c[0] for c in L["cast"]]
        assert len(cols) == len(people)
        if sc == "cave":
            assert len(set(cols.values())) == len(people)
        assert any(b["name"].startswith("ura_antler") for b in L["blocks"])


def test_clutter_clash_is_found_and_the_layouts_are_clear():
    blocks, cast, structure, cam = S._ice("cc0")
    blocks = blocks + [S.piece("rock_x", "model.ph_boulder_01", [-6.0, 20.5, 0.0])]
    assert S.clutter_clashes(blocks, cast, cam, "ice", structure)
    for sc in S.SCENES:
        for w in S.WAYS:
            S.layout(sc, w)   # raises on a clash


def test_blender_gate_luma_and_colour():
    dark = np.full((90, 160, 3), 0.05, dtype=np.float32)
    f = G.check(dark, {"a": (0.5, 0.5)}, "xworld style, at night", None, [])
    assert any(x["id"] == "BL-01" for x in f)
    warm = np.full((90, 160, 3), 0.5, dtype=np.float32)
    warm[..., 0] = 0.8
    f = G.check(warm, {"a": (0.5, 0.5)}, "lit by a cold blue dusk glow", None, [])
    assert any(x["id"] == "BL-02" for x in f)
    ok = np.full((90, 160, 3), 0.5, dtype=np.float32)
    ok[..., 2] = 0.7
    assert G.check(ok, {"a": (0.5, 0.5)}, "lit by a cold blue dusk glow", None, []) == []
    assert G.check(ok, {}, "", None, ["rock next to mammoth"])[0]["id"] == "BL-03"


def test_frozen_settle_fails():   # D-121 (the creator 2026-11-07 22:23 UTC): KP-55 is FAIL
    shot = {"id": "x", "kind": "video", "prompt": "The hunter in grey fur kneels still. Everyone stays in frame. Static camera."}
    found = SPL.check_shot(shot)
    assert any(f["rule"] == "KP-55" and f["severity"] == "FAIL" for f in found)
    for sc in S.SCENES:
        assert not SPL.FROZEN_SETTLE.search(S.CARDS[sc]["settle"])


def test_flat3_has_no_cc0_and_refuses_one():
    """KP-56 (creator 14:55 UTC, Argon Part 4): richness from flat silhouette planes, never CC0 meshes or textures."""
    for sc in S.SCENES:
        L = S.layout(sc, "flat3")
        assert S.textured(L["blocks"]) == []
        assert any(b.get("dress") for b in L["blocks"])
    assert S.textured(S._cave("cc0")[0])
    huts = {b["name"]: b["scale"][0] for b in S.layout("camp", "flat3")["blocks"] if b["name"].endswith("_wall") and b["name"].startswith("hut_")}
    assert max(huts, key=huts.get) == "hut_2_wall"


def test_flat3_layout_raises_on_a_cc0_piece(monkeypatch):
    real = S._ice
    monkeypatch.setattr(S, "_ice", lambda way: (lambda r: (r[0] + [S.piece("rock_x", "model.ph_boulder_01", [-30.0, 60.0, 0.0])],) + r[1:])(real(way)))
    import pytest
    with pytest.raises(ValueError, match="KP-56"):
        S.layout("ice", "flat3")


def test_secondary_angle_puts_the_painted_master_second():
    """KP-57: Image 1 = the new angle's Blender still, Image 2 = the painted master; the fixed prefix is not counted."""
    L = S.layout("cave", "flat3")
    p = PS.prompts(S.SHOT["cave"], layout=L, master=True)
    assert p["qwen"].startswith("xworld style, " + PS.MASTER_PREFIX)
    assert p["qwen_words"] == PS.prompts(S.SHOT["cave"], layout=L)["qwen_words"] <= PS.QWEN_MAX_WORDS
