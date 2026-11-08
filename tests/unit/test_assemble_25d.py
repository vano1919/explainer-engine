"""The J5 route's 2.5D assembly (D-116, guide step 2.1, ICW-11): scene_assets/1, the cut-out finish (SA-04), the planner of
``blender/assemble_25d.py`` (SA-06..SA-09). No Blender here: the bpy side runs in the CI smoke and on the creator's PC."""
import json
import math

import numpy as np
import pytest
from PIL import Image, ImageDraw

from explainer_engine.blender import assemble_25d as A
from explainer_engine.blender import camera_setups as CS
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.edit import cutout as K


# --- cut-outs (SA-04) ------------------------------------------------------------------------------------------------------------

def _inked_sheet(soft: bool):
    """A red figure with a black ink outline on the light-grey sheet; the matte soft (a BiRefNet-like 3 px edge) or hard."""
    im = Image.new("RGB", (200, 300), (200, 200, 200))
    ImageDraw.Draw(im).ellipse((40, 40, 160, 260), fill=(200, 30, 30), outline=(0, 0, 0), width=6)
    m = Image.new("L", im.size, 0)
    ImageDraw.Draw(m).ellipse((40, 40, 160, 260), fill=255)
    mask = np.asarray(m, dtype=np.float64) / 255.0
    if soft:
        mask = K._blur(mask, 1.5)
    return im, mask


def _straight_cut(im, mask):
    """What a plain alpha cut gives: the sheet's own colours (the grey rim rides along)."""
    return Image.fromarray(np.dstack([np.asarray(im), (mask * 255).round()]).astype(np.uint8), mode="RGBA")


def test_a_straight_cut_of_an_inked_figure_has_a_halo_and_finish_removes_it():
    im, mask = _inked_sheet(soft=True)
    raw = _straight_cut(im, mask)
    assert K.halo_score(raw) > K.HALO_REVIEW
    assert any(f["rule"] == "SA-04" and f["severity"] == "REVIEW" for f in K.check(raw))
    done = K.finish(im, Image.fromarray((mask * 255).round().astype(np.uint8)))
    assert done.mode == "RGBA" and K.halo_score(done) < K.HALO_REVIEW / 4
    assert K.check(done) == []
    a = np.asarray(done)
    rim = (a[..., 3] > 5) & (a[..., 3] < 250)
    assert a[rim][:, :3].mean() < 60   # the rim is the ink's black now, not the sheet's grey


def test_finish_keeps_a_soft_matte_and_feathers_a_hard_one_to_about_two_pixels():
    im, soft = _inked_sheet(soft=True)
    assert K.edge_width(soft) >= K.FEATHER_PX
    out = K.load_mask(K.finish(im, Image.fromarray((soft * 255).round().astype(np.uint8))))
    assert np.abs(out - np.round(soft * 255) / 255).max() < 1e-6   # a BiRefNet-soft edge is not blurred again (hair strands)
    im, hard = _inked_sheet(soft=False)
    assert K.edge_width(hard) < 1.0
    out = K.load_mask(K.finish(im, Image.fromarray((hard * 255).astype(np.uint8))))
    assert 1.0 <= K.edge_width(out) <= 2 * K.FEATHER_PX + 1


def test_a_card_must_be_rgba_and_the_figure_alone():
    im, _ = _inked_sheet(soft=False)
    assert any(f["rule"] == "SA-04" and f["severity"] == "FAIL" for f in K.check(im))
    cut = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(cut).rectangle((0, 20, 60, 99), fill=(255, 0, 0, 255))
    assert any(f["rule"] == "AC-15" for f in K.check(cut))   # touches the edge: cut


def test_the_birefnet_pin_is_the_mit_model_at_a_revision():
    from explainer_engine.cloud import pins
    p = pins.load()["models"][K.BIREFNET_PIN]
    assert p["id"] == "ZhengPeng7/BiRefNet" and len(p["revision"]) == 40 and p["licence"] == "SPDX:MIT"
    assert p.get("legacy") is False


# --- scene_assets/1 --------------------------------------------------------------------------------------------------------------

def test_a_hero_without_the_flat_lighting_note_fails():
    doc = json.loads((C.SCHEMAS.parents[1] / "tests/fixtures/contracts/scene_assets/valid.json").read_text(encoding="utf-8"))
    assert C.errors(doc) == []
    doc["scenes"]["S01"]["heroes"][1]["prompt"] = doc["scenes"]["S01"]["heroes"][1]["prompt"].replace(
        ", flat ambient lighting, no cast shadows", "")
    assert [(f["rule"], f["severity"]) for f in C.errors(doc)] == [("SA-01", "FAIL")]


# --- the planner -----------------------------------------------------------------------------------------------------------------

def test_four_mouth_states_cross_blend_and_reconstruct_all_state_weights():
    shapes = list("XXDDBBEFX")
    w = A.mouth_weights(shapes)
    assert w[1] == {"rest": 1.0, "half": 0.0, "wide": 0.0, "round": 0.0}
    assert w[2] == {"rest": 0.5, "half": 0.0, "wide": 0.5, "round": 0.0}
    assert w[3]["wide"] == 1.0
    assert w[4] == {"rest": 0.0, "half": 0.5, "wide": 0.5, "round": 0.0}
    assert w[6] == {"rest": 0.0, "half": 0.5, "wide": 0.0, "round": 0.5}
    assert w[7]["round"] == 1.0
    for x in w:
        assert sum(x.values()) == pytest.approx(1.0)
        fh, fw, fr = A.mix_factors(x)
        weights = ((1 - fh) * (1 - fw) * (1 - fr), fh * (1 - fw) * (1 - fr), fw * (1 - fr), fr)
        assert weights == pytest.approx(tuple(x[k] for k in A.STATES))
    assert set(A.MOUTH_STATE) == set("ABCDEFGHX") and set(A.MOUTH_STATE.values()) == set(A.STATES)
    from explainer_engine.production import cut_plan
    assert A.MOUTH_STATE == cut_plan.CUE_TO_STATE


def test_smoke_cues_exercise_rest_half_wide_and_round_at_low_resolution():
    cues = A._smoke_cues(0.5)
    planned = A.LipSync(fps=24).plan(cues, frames=12)
    states = set(planned["shapes"])
    assert {"A", "C", "D", "E", "X"} <= states
    mapped = {A.MOUTH_STATE[s] for s in states}
    assert mapped == set(A.STATES)


def test_blinks_come_every_three_to_five_seconds_and_breathing_is_half_a_percent_at_a_quarter_hertz():
    fps, frames = 24, 24 * 20
    b = A.blink_track(frames, fps, "shot/H1")
    starts = [i for i, v in enumerate(b) if v == A.BLINK_WEIGHTS[0] and (i == 0 or b[i - 1] == 0)]
    gaps = [(q - p) / fps for p, q in zip(starts, starts[1:])]
    assert len(starts) >= 4 and all(A.BLINK_EVERY_S[0] - 0.05 <= g <= A.BLINK_EVERY_S[1] + 0.05 for g in gaps)
    assert b == A.blink_track(frames, fps, "shot/H1") and b != A.blink_track(frames, fps, "shot/H3")   # seeded, per hero
    s = A.breath_track(frames, fps, "shot/H1")
    assert max(s) == pytest.approx(1 + A.BREATH_SCALE, abs=1e-4) and min(s) == pytest.approx(1 - A.BREATH_SCALE, abs=1e-4)
    period = fps / A.BREATH_HZ
    assert s[0] == pytest.approx(s[int(period)], abs=1e-6)


@pytest.fixture(scope="module")
def smoke_assets(tmp_path_factory):
    d = tmp_path_factory.mktemp("assets")
    return A._smoke_assets(d), d


def test_the_smoke_assets_are_a_valid_scene_assets_document(smoke_assets):
    doc, _ = smoke_assets
    assert C.errors(doc) == []


def test_a_card_stands_on_its_feet_at_its_real_height(smoke_assets):
    doc, d = smoke_assets
    geo = A.card_geometry(d / "h1_base.png", 1.75)
    box = A.alpha_box(d / "h1_base.png")["box"]
    m = 1.75 / (box[3] - box[1])
    assert geo["height_m"] == pytest.approx(1000 * m, abs=1e-5) and geo["bottom_m"] == pytest.approx(-(1000 - box[3]) * m, abs=1e-5)
    assert geo["left_m"] == pytest.approx(-(box[0] + box[2]) / 2 * m, abs=1e-5)
    assert geo["bottom_m"] + (1000 - box[1]) * m == pytest.approx(1.75, abs=1e-5)   # the top of the head at the real height


def test_the_four_dialogue_shots_plan_cards_facing_the_camera_and_one_speaking_mouth(smoke_assets):
    doc, d = smoke_assets
    shots = {s["id"]: s for s in A.smoke_shots(1.0)}
    bodies = {k: A.plan(doc, s, base=d, width=480, height=270) for k, s in shots.items()}
    for k, b in bodies.items():
        assert b["job"] == A.JOB and b["frames"] == 24 and b["world"]["image"].endswith("grid360.png")
        cam = b["camera"]["keys"][0]["location"]
        for c in b["cards"]:
            f = (math.sin(math.radians(c["yaw_deg"])), -math.cos(math.radians(c["yaw_deg"])))   # the card's front (-Y turned)
            to_cam = (cam[0] - c["pos"][0], cam[1] - c["pos"][1])
            n = math.hypot(*to_cam)
            assert f[0] * to_cam[0] / n + f[1] * to_cam[1] / n == pytest.approx(1.0, abs=1e-6), (k, c["name"])
            assert c["kind"] == "hero" and len(c["breath"]) == 24 and c["shadow"]["alpha"] == A.SHADOW["alpha"]
            assert "blink" in c
    speaking = [c for b in bodies.values() for c in b["cards"] if "mouth" in c]
    assert [c["name"] for c in speaking] == ["card_H3"] and len(speaking[0]["mouth"]["factors"]) == 24
    assert any(any(v > 0.5 for v in f) for f in speaking[0]["mouth"]["factors"])   # a mouth state opens on the line
    mcu, rev = bodies["J5-03_mcu_b_speaks"], bodies["J5-04_mcu_a_reacts"]
    assert mcu["camera"]["setup"] == rev["camera"]["setup"] == "mcu_front"
    assert mcu["probe"][0]["at"][:2] == pytest.approx(A.SMOKE_CAST["H3"][:2])
    assert rev["probe"][0]["at"][:2] == pytest.approx(A.SMOKE_CAST["H1"][:2])
    pan = bodies["J5-05_pan30"]["camera"]["keys"]
    from explainer_engine.blender import scene_builder as SB
    yaw = [SB.angles([k["look_at"][i] - k["location"][i] for i in range(3)])[0] for k in (pan[0], pan[-1])]
    assert (yaw[0] - yaw[1]) % 360 == pytest.approx(30.0, abs=1e-3)


def test_the_planner_refuses_what_is_not_drawn_or_not_the_drawn_file(smoke_assets, tmp_path):
    doc, d = smoke_assets
    shot = A.smoke_shots(1.0)[0]
    bad = json.loads(json.dumps(doc))
    bad["scenes"]["S01"]["heroes"][0]["angles"]["3q_right"]["base"] = None
    with pytest.raises(ContractError, match="not drawn yet"):
        A.plan(bad, shot, base=d)
    bad = json.loads(json.dumps(doc))
    bad["scenes"]["S01"]["heroes"][0]["angles"]["3q_right"]["base"]["sha256"] = "0" * 64
    with pytest.raises(ContractError, match="sha256"):
        A.plan(bad, shot, base=d)
    with pytest.raises(ContractError, match="no sheet"):
        A.plan(doc, {**shot, "cast": {"H9": {"pos": [0, 2, 0], "angle": "front"}}}, base=d)


def test_a_speaking_card_needs_four_mouth_states_and_a_lip_synced_shot_keeps_bp108(smoke_assets):
    doc, d = smoke_assets
    speak = A.smoke_shots(1.0)[2]
    bad = json.loads(json.dumps(doc))
    del bad["scenes"]["S01"]["heroes"][1]["angles"]["front"]["mouth_round"]
    with pytest.raises(ContractError, match="SA-06"):
        A.plan(bad, speak, base=d)
    from explainer_engine.standards import sourced_rules as SR
    cap = SR.T("BP-108", "dialogue_shot_max_s")
    with pytest.raises(ValueError, match="BP-108"):
        A.plan(doc, {**speak, "seconds": cap + 1.0}, base=d)
    assert A.plan(doc, {**A.smoke_shots(cap + 1.0)[3]}, base=d)["frames"] == round((cap + 1.0) * 24)   # no line: no cap


def test_the_horizon_bend_measure_finds_a_bent_horizon():
    def frame(rows, path):
        a = np.zeros((100, len(rows), 3), np.uint8)
        a[:] = (0, 0, 255)
        for x, r in enumerate(rows):
            a[r:, x] = (0, 255, 0)
        Image.fromarray(a).save(path)
        return path
    import tempfile, os
    with tempfile.TemporaryDirectory() as t:
        straight = frame([50 + x // 20 for x in range(200)], os.path.join(t, "s.png"))
        bent = frame([50 + round(4 * math.sin(math.pi * x / 199)) for x in range(200)], os.path.join(t, "b.png"))
        assert A.horizon_bend(straight) <= 0.011
        assert A.horizon_bend(bent) == pytest.approx(0.04, abs=0.006)


def test_the_bpy_script_follows_the_frame_protocol_and_builds_no_light():
    text = A.SCRIPT.read_text(encoding="utf-8")
    assert "assemble_25d/1" in text and "pin_version" in text and "os.replace" in text and "fsync" in text
    assert "bpy.data.lights.new" not in text and "visible_shadow = False" in text and '"Standard"' in text
    assert A.command(["/opt/blender/blender"], "j.json")[:5] == ["/opt/blender/blender", "--background", "--factory-startup",
                                                                 "--python-exit-code", "1"]
    assert A.command(["/venv/bin/python"], "j.json") == ["/venv/bin/python", str(A.SCRIPT), "--", "j.json"]


def test_mcu_front_is_a_camera_setup_the_planner_can_use():
    assert "mcu_front" in CS.names()
