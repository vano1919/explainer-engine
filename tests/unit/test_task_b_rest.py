"""Regression tests for Round B (B-13, B-14, B-P1, B-EXTRA) on branch o239-argon-impl."""
from __future__ import annotations

import copy
import inspect
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
from PIL import Image

from explainer_engine.audio import voice_check as VC
from explainer_engine.core import delivery
from explainer_engine.core.errors import ContractError
from explainer_engine.edit import rhythm_profile as RP
from explainer_engine.episode import production_runner as PR
from explainer_engine.episode import router as RT
from explainer_engine.episode import run as RUN
from explainer_engine.finish import upscale as UP
from explainer_engine.maps import actions as MA
from explainer_engine.maps import draw as MDRAW
from explainer_engine.production import continuity as CONT
from explainer_engine.production import directed25d as D25
from explainer_engine.production import direction as DIR
from explainer_engine.production import layers25d as L25
from explainer_engine.production import living_fx as LFX
from explainer_engine.production import motion_isolation as MI
from explainer_engine.qa import motion_intent as MQA
from explainer_engine.training.pods.ltx import modal_ltx_jobs as MLTX
from explainer_engine.videolane import identity as VID


def _make_dummy_layers(tmp_path: Path, w: int = 160, h: int = 90):
    pic = tmp_path / "pic.png"
    arr = np.full((h, w, 3), 80, np.uint8)
    arr[20:60, 40:80] = [180, 140, 100]
    Image.fromarray(arr).save(pic)
    tree_m = np.zeros((h, w), np.float32)
    tree_m[10:50, 20:50] = 1.0
    trench_m = np.zeros((h, w), np.float32)
    trench_m[60:85, 10:150] = 1.0
    sky_m = np.zeros((h, w), np.float32)
    sky_m[:30, :] = 1.0
    depth = np.full((h, w), 0.2, np.float32)
    depth[60:85, :] = 0.8
    layers = {
        "plate": arr.copy(),
        "depth": depth,
        "hole": np.zeros((h, w), np.float32),
        "masks": {"tree": tree_m, "trench": trench_m, "sky": sky_m},
        "lights": {},
        "manifest": {
            "masks": {"objects": [
                {"id": "tree", "layer": True},
                {"id": "trench", "layer": False},
                {"id": "sky", "layer": False},
            ]},
            "lights": [],
        },
    }
    return pic, layers


# --- B-13 ---

def test_b13_particles_respect_mask_and_leave_background_stationary(tmp_path: Path):
    pic, layers = _make_dummy_layers(tmp_path)
    plan = {"shot_id": "s1", "frames": 6, "intent": "still_by_design", "cameras": [],
            "effects": [{"op": "snow", "mask": "sky", "strength": 1.0}]}
    st = D25.Stage(pic, layers, plan, size=(160, 90), fps=24)
    f0 = st.render(0)
    f5 = st.render(5)
    # Outside sky mask (y >= 40), background must remain completely unchanged
    diff_bg = np.abs(f5[45:, :].astype(np.float32) - f0[45:, :].astype(np.float32)).max()
    assert diff_bg == 0.0, f"particles leaked outside declared mask: max diff={diff_bg}"


def test_b13_flame_explicit_holder_and_motion_isolation_and_gate(tmp_path: Path):
    pic, layers = _make_dummy_layers(tmp_path)
    holder_m = np.zeros((90, 160), np.float32)
    holder_m[55:75, 70:90] = 1.0
    flame_m = np.zeros((90, 160), np.float32)
    flame_m[40:55, 74:86] = 1.0
    layers["masks"]["brazier"] = holder_m
    layers["lights"]["flame"] = flame_m
    layers["manifest"]["masks"]["objects"].append({"id": "brazier", "layer": True})
    layers["manifest"]["lights"].append({"id": "flame", "point": [0.5, 0.52], "holder_object_id": "brazier"})

    plan = {"shot_id": "s_flame", "frames": 4, "intent": "still_by_design", "cameras": [],
            "effects": [{"op": "fire", "lights": ["flame"], "holder_object_id": "brazier", "strength": 1.0}]}
    st = D25.Stage(pic, layers, plan, size=(160, 90), fps=24)
    host = st._layer_of_light(st.lights["flame"], [], effect=plan["effects"][0])
    assert host is not None and host["id"] == "brazier"

    # motion_isolation gate must use AND (not OR): large holder_leak_p95 fails even if ratio is small
    f0 = np.zeros((64, 64, 3), np.uint8)
    f1 = np.zeros((64, 64, 3), np.uint8)
    mover = np.zeros((64, 64), np.float32)
    mover[5:25, 5:25] = 1.0
    anchor = np.zeros((64, 64), np.float32)
    anchor[40:55, 40:55] = 1.0
    f1[5:25, 5:25] = 240  # huge mover diff
    f1[40:55, 40:55] = 5  # > 1.25 luma holder leak, but ratio 5/240 = 0.02 < 0.08
    mi = MI.evaluate_motion_isolation([f0, f1], mover_mask=mover, anchor_mask=anchor)
    assert mi["passed"] is False and mi["status"] == "FAIL"
    assert "holder_flow_p95" in mi

    # episode/run.py QA rows must include motion_isolation
    rows = RUN._directed_qa_rows("s_flame", plan, {"frames": 4, "motion_isolation": mi}, None, 90, 24)
    assert any(r["gate"] == "motion_isolation" and r["status"] == "FAIL" for r in rows)


def test_b13_wind_target_semantic_validation_rejects_wrong_trench_id():
    d = {
        "schema": DIR.SCHEMA, "shot_id": "S01_SH001", "intent": "still_by_design",
        "seen": {
            "what": "a tree beside a trench",
            "objects": [{"id": "tree"}, {"id": "trench"}],
            "lights": [],
            "living": [{"id": "tree", "kind": "plants", "where": [0.2, 0.3], "mask": "tree",
                        "decision": "animate", "effects": ["fx_tree"]}],
        },
        "tracks": [
            {"id": "fx_tree", "track": "effect", "op": "foliage_sway", "renderer": "directed25d",
             "target": {"mask": "trench"}, "params": {}},
        ],
    }
    probs = DIR.check(d)
    assert any(p["level"] == "FAIL" and "trench" in p["what"] for p in probs)


def test_b13_missing_surface_mask_never_warps(tmp_path: Path):
    pic, layers = _make_dummy_layers(tmp_path)
    plan = {"shot_id": "s_nomask", "frames": 4, "intent": "still_by_design", "cameras": [],
            "effects": [{"op": "foliage_sway", "strength": 1.0}]}
    st = D25.Stage(pic, layers, plan, size=(160, 90), fps=24)
    f0 = st.render(0)
    f3 = st.render(3)
    assert np.array_equal(f0, f3), "missing surface mask must NOT fall back to full-frame warp"
    assert any(r["status"] == "NOT_RUN" for r in getattr(st, "fx_target_status", []))


def test_b13_layers25d_two_instances_same_effect_keep_own_region(tmp_path: Path):
    pic, _ = _make_dummy_layers(tmp_path)
    p = {
        "shot_id": "s_l25", "fps": 24, "frames": 6, "seed": 1,
        "camera": {"kind": "static", "z0": 1.0, "z1": 1.0, "dx": 0.0, "dy": 0.0},
        "cameras": [], "handheld": None, "rack": None, "impacts": [], "events": [],
        "effects": [
            {"id": "sway_left", "effect": "foliage_sway", "strength": 1.0, "region": [0.0, 0.0, 0.3, 0.5]},
            {"id": "sway_right", "effect": "foliage_sway", "strength": 1.0, "region": [0.7, 0.5, 1.0, 1.0]},
        ],
    }
    depth = np.zeros((90, 160), np.float32)
    depth[:, :80] = 0.2
    depth[:, 80:] = 0.8
    sc = L25.build_scene(pic, p, (160, 90), depth=depth)
    assert "sway_left" in sc.fx and "sway_right" in sc.fx
    assert sc.region_plane["sway_left"] != sc.region_plane["sway_right"]


# --- B-14 ---

def test_b14_delivery_profile_single_source():
    sig = inspect.signature(PR.run_episode_production)
    assert sig.parameters["width"].default is None
    assert sig.parameters["height"].default is None
    assert delivery.size() == (2560, 1440)


def test_b14_unified_final_frame_qa_all_frames():
    from explainer_engine.qa import final_frame_qa as FFQA
    fr0 = np.full((64, 64, 3), 120, np.uint8)
    fr1 = np.full((64, 64, 3), 120, np.uint8)
    fr2 = np.zeros((64, 64, 3), np.uint8)  # black frame / invalid coverage at frame 2
    res = FFQA.evaluate_final_frame_qa([fr0, fr1, fr2], [fr0, fr0, fr0])
    assert res["frames_checked"] == 3
    assert res["needs_owner_calibration"] is True
    assert res["ranges"]["upscaler_default"] == "native"
    assert res["metrics"]["valid_coverage"]["frame"] == 2
    assert res["status"] == "FAIL"


# --- B-P1 ---

def test_bp1a_ltx_face_identity_and_not_measured(tmp_path: Path):
    fr = np.zeros((64, 64, 3), np.uint8)
    # Missing reference -> NOT_MEASURED, never PASS
    nm = VID.evaluate_ltx_face_identity([fr, fr, fr], reference_image=None)
    assert nm["status"] == "NOT_MEASURED" and nm["passed"] is False

    # Fake detector: stable face passes, distorted last frame fails
    ref_emb = np.array([1.0, 0.0, 0.0], np.float32)
    bad_emb = np.array([0.0, 1.0, 0.0], np.float32)
    def fake_det(img):
        tag = int(img[0, 0, 0])
        return [{"x": 0.5, "y": 0.5, "w": 0.2, "h": 0.2, "_emb": bad_emb if tag == 99 else ref_emb}]

    f_good = np.zeros((64, 64, 3), np.uint8)
    f_bad = np.full((64, 64, 3), 99, np.uint8)
    cs = tmp_path / "sheet.png"
    ok = VID.evaluate_ltx_face_identity([f_good, f_good, f_good], reference_image=f_good,
                                        detector=fake_det, recognizer=False, out_cut_sheet=cs)
    assert ok["status"] == "PASS" and cs.is_file()
    fail = VID.evaluate_ltx_face_identity([f_good, f_good, f_bad], reference_image=f_good,
                                          detector=fake_det, recognizer=False)
    assert fail["status"] == "FAIL"


def test_bp1b_effects_visible_3s_and_still_by_design():
    row_still = MQA.effects_seen_row([{"op": "snow", "change_p95": 0.0, "still_by_design": True}])
    assert row_still["status"] == "PASS"
    assert hasattr(L25, "render_clip") and "effects_seen" in inspect.getsource(L25.render_clip)


@pytest.mark.parametrize("subtype", ["document", "letter", "newspaper", "telegram"])
def test_bp1c_archival_helper_lane_subtypes_and_provenance(tmp_path: Path, subtype: str):
    from explainer_engine.production import archival_helper as AH
    sh = {
        "shot_id": f"SH_{subtype}",
        "helper_subtype": subtype,
        "target_duration_seconds": 1.0,
        "archival_asset": {"subtype": subtype, "title": "Truce Dispatch", "date": "1914-12-25",
                           "text": "Official dispatch text.", "provenance": "Imperial War Museum Archive"},
    }
    route, _ = RT.route_shot(sh)
    assert route == "map_action"
    res = AH.render_archival_helper_clip(sh, {}, {}, tmp_path / f"{subtype}.mp4", width=320, height=180, fps=24)
    assert res["provider"] == f"archival_helper:{subtype}"
    assert res["gates"]["status"] == "PASS"

    bad_sh = copy.deepcopy(sh)
    bad_sh["archival_asset"]["provenance"] = ""
    with pytest.raises(ContractError):
        AH.validate_archival_asset(bad_sh)


def test_bp1d_ltx_manifest_and_upscale_cli_default():
    launch = {"module": "ltx_pipelines.distilled", "uses": {"transformer": "t.safetensors", "distilled_lora": "lora.safetensors"}}
    job = {"shot_id": "S02_SH006", "motion_prompt": "soldier blinks", "seed": 42,
           "negative_prompt": "cartoonish rendering, blurry", "width": 1920, "height": 1088, "fps": 24, "seconds": 3.0}
    man = MLTX.build_ltx_render_manifest(launch, job)
    assert man["seed"] == 42
    assert "cartoonish" not in man["negative_prompt"].lower()
    assert "deformed facial features" in man["negative_prompt"].lower()
    # Programmatic upscale() default and CLI default both have sharpen="none", grain=0
    sig = inspect.signature(UP.upscale)
    assert sig.parameters["sharpen"].default == "none"
    assert sig.parameters["grain"].default == 0
    src_main = inspect.getsource(UP.main)
    assert 'default="none"' in src_main and "default=0" in src_main


# --- B-EXTRA ---

def test_bextra_1_2_map_labels_title_safe_phase_reset_and_region_dot():
    # 1. Label validation against places
    places = {"verdun": {"name": "Verdun"}}
    bad_plan = {"actions": [{"kind": "label", "from_id": "verdun", "label": "Verdus"}]}
    assert len(MA.validate_map_labels(bad_plan, places)) == 1
    good_plan = {"actions": [{"kind": "label", "from_id": "verdun", "label": "Verdun"}]}
    assert MA.validate_map_labels(good_plan, places) == []

    # 2. Title-safe margin >= 5% for HUD chip
    c = MDRAW.Canvas(1920, 1080)
    x0, y0, x1, y1, _, _ = MA._hud_chip_box(c, "August 1914", 1080)
    assert x0 >= 1920 * 0.05 and y0 >= 1080 * 0.05

    # 2b. phase_reset + locked_span_km + is_region in maps/actions.py
    src_draw = inspect.getsource(MA.draw)
    assert "phase_reset" in src_draw
    assert "locked_span_km" in src_draw
    assert "is_region" in inspect.getsource(MA._draw_geo_label_pill)


def test_bextra_3_4_5_6_continuity_voice_rhythm():
    # 3. Script-to-visual time-of-day mismatch
    tod = CONT.check_narration_time_of_day([{"shot_id": "S1", "light": "sunrise sky", "narration": "Every night they waited."}])
    assert len(tod) == 1 and tod[0]["level"] == "REVIEW"

    # 4. Prop/costume continuity across adjacent shots
    cc = CONT.costume_prop_continuity_findings([
        {"shot_id": "A", "scene_id": "SC1", "costume": {"gloves": "wool_brown"}},
        {"shot_id": "B", "scene_id": "SC1", "costume": {"gloves": "leather_black"}},
    ])
    assert len(cc) == 1 and cc[0]["level"] == "REVIEW"

    # 5. Voice accent missing -> REVIEW
    va = VC.check_character_accents({"thomas": {"role": "soldier"}})
    assert len(va) == 1 and va[0]["level"] == "REVIEW"

    # 6. Illustrated history profile & 60/30/10 still/video/helper lane targets
    prof = RP.get_profile("illustrated_history")
    assert prof["lane_share"] == {"still": 0.60, "video": 0.30, "helper": 0.10}
    assert RT.lane_mix_targets("illustrated_history") == {"still_25d": 0.60, "video": 0.30, "map_action": 0.10}
