"""Task 2 Step 2B regression and vertical-slice verification suite (R2 Steps 1-6 + YF-Q1 + YF-Q2).

Every test here is designed to FAIL on baseline 9ecdd875 and PASS on the Step 2B implementation,
completely offline on CPU ($0, no paid calls, deterministic fallbacks).
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

import jsonschema
import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[2]


def _make_slice_layers(shot_id: str, h: int = 120, w: int = 200) -> dict:
    """Deterministic synthetic layer bundle mirroring the vertical-slice paintings."""
    fg = np.zeros((h, w), dtype=np.float32)
    mid = np.zeros((h, w), dtype=np.float32)
    sky = np.zeros((h, w), dtype=np.float32)
    ground = np.zeros((h, w), dtype=np.float32)
    sky[: int(h * 0.32), :] = 1.0
    ground[int(h * 0.65) :, :] = 1.0
    objects = []
    lights = []
    masks = {"foreground": fg, "midground": mid, "sky": sky, "ground": ground, "objects": {}, "lights": {}}

    if shot_id == "S08_SH002":
        photo_m = np.zeros((h, w), dtype=np.float32)
        photo_m[int(h * 0.52) : int(h * 0.75), int(w * 0.36) : int(w * 0.57)] = 1.0
        btn_m = np.zeros((h, w), dtype=np.float32)
        btn_m[int(h * 0.58) : int(h * 0.65), int(w * 0.45) : int(w * 0.52)] = 1.0
        hands_m = np.zeros((h, w), dtype=np.float32)
        hands_m[int(h * 0.56) : int(h * 0.80), int(w * 0.30) : int(w * 0.62)] = 1.0
        candle_m = np.zeros((h, w), dtype=np.float32)
        candle_m[int(h * 0.25) : int(h * 0.50), int(w * 0.80) : int(w * 0.90)] = 1.0
        fg = np.maximum(photo_m, hands_m)
        mid = candle_m.copy()
        masks["foreground"] = fg
        masks["midground"] = mid
        for oid, what, m, box, where in [
            ("photo", "sepia family portrait card", photo_m, [0.36, 0.52, 0.57, 0.75], [0.465, 0.635]),
            ("button", "British brass tunic button", btn_m, [0.45, 0.58, 0.52, 0.65], [0.485, 0.615]),
            ("hands", "gloved hands", hands_m, [0.30, 0.56, 0.62, 0.80], [0.46, 0.68]),
            ("candle", "candle stub in tin holder", candle_m, [0.80, 0.25, 0.90, 0.50], [0.85, 0.375]),
        ]:
            masks[oid] = m
            masks["objects"][oid] = m
            objects.append({"id": oid, "what": what, "plane": "foreground", "area_share": 0.05, "depth": 0.7, "box": box, "where": where})
        lights = [
            {"id": "candle_flame", "kind": "candle", "point": [0.848, 0.295], "radius": 0.04, "warmth": 0.85},
            {"id": "far_brazier", "kind": "fire", "point": [0.22, 0.36], "radius": 0.03, "warmth": 0.75},
        ]
    elif shot_id == "S02_SH008":
        thomas_m = np.zeros((h, w), dtype=np.float32)
        thomas_m[int(h * 0.25) : int(h * 0.90), int(w * 0.08) : int(w * 0.40)] = 1.0
        harris_m = np.zeros((h, w), dtype=np.float32)
        harris_m[int(h * 0.25) : int(h * 0.90), int(w * 0.60) : int(w * 0.92)] = 1.0
        brazier_m = np.zeros((h, w), dtype=np.float32)
        brazier_m[int(h * 0.55) : int(h * 0.83), int(w * 0.44) : int(w * 0.60)] = 1.0
        fg = np.maximum(np.maximum(thomas_m, harris_m), brazier_m)
        masks["foreground"] = fg
        for oid, what, is_p, m, box, where in [
            ("thomas", "British private Thomas", True, thomas_m, [0.08, 0.25, 0.40, 0.90], [0.24, 0.575]),
            ("harris", "Sergeant Harris", True, harris_m, [0.60, 0.25, 0.92, 0.90], [0.76, 0.575]),
            ("brazier", "glowing coke brazier", False, brazier_m, [0.44, 0.55, 0.60, 0.83], [0.52, 0.69]),
        ]:
            masks[oid] = m
            masks["objects"][oid] = m
            objects.append({"id": oid, "what": what, "is_person": is_p, "plane": "foreground", "area_share": 0.12, "depth": 0.75, "box": box, "where": where})
        lights = [
            {"id": "brazier_flame", "kind": "fire", "point": [0.52, 0.64], "radius": 0.06, "warmth": 0.9},
            {"id": "niche_candle", "kind": "candle", "point": [0.46, 0.38], "radius": 0.025, "warmth": 0.8},
        ]
    elif shot_id == "S05_SH020":
        lg_m = np.zeros((h, w), dtype=np.float32)
        lg_m[int(h * 0.20) : int(h * 0.84), int(w * 0.06) : int(w * 0.46)] = 1.0
        rg_m = np.zeros((h, w), dtype=np.float32)
        rg_m[int(h * 0.20) : int(h * 0.82), int(w * 0.54) : int(w * 0.92)] = 1.0
        fg = np.maximum(lg_m, rg_m)
        masks["foreground"] = fg
        for oid, what, m, box, where in [
            ("left_group", "Scottish chaplain and Highland soldiers", lg_m, [0.06, 0.20, 0.46, 0.84], [0.26, 0.52]),
            ("right_group", "German student and soldiers", rg_m, [0.54, 0.20, 0.92, 0.82], [0.73, 0.51]),
        ]:
            masks[oid] = m
            masks["objects"][oid] = m
            objects.append({"id": oid, "what": what, "is_person": True, "plane": "foreground", "area_share": 0.15, "depth": 0.72, "box": box, "where": where})
        lights = [
            {"id": "sun", "kind": "sun", "point": [0.50, 0.16], "radius": 0.09, "warmth": 0.75},
            {"id": "brazier_left", "kind": "fire", "point": [0.14, 0.68], "radius": 0.04, "warmth": 0.85},
            {"id": "candle_1", "kind": "candle", "point": [0.48, 0.74], "radius": 0.02, "warmth": 0.8},
        ]

    manifest = {
        "schema": "layers/1",
        "key": f"key_{shot_id}",
        "picture_sha256": f"sha_{shot_id}",
        "sha256": f"sha_{shot_id}",
        "size": [w, h],
        "planes": {"foreground": {"area": 0.30}, "midground": {"area": 0.20}, "sky": {"area": 0.32}},
        "sky": {"area_pct": 32.0},
        "masks": {"objects": objects},
        "objects": objects,
        "lights": lights,
        "geometry": {"horizon_y": 0.32, "sky_area_pct": 32.0},
    }
    return {"manifest": manifest, "masks": masks, "depth": np.full((h, w), 0.5, dtype=np.float32)}


def test_step1_contracts_and_vertical_slice_briefs_and_ownership():
    from explainer_engine.scripting import stage_guard as SG

    # 1. New guides and knowledge base v2.0.0 exist
    assert (ROOT / "explainer_engine" / "standards" / "screenwriter_guide.json").is_file()
    assert (ROOT / "explainer_engine" / "standards" / "motion_isolation.json").is_file()
    assert (ROOT / "docs" / "SCREENWRITER_GUIDE.md").is_file()
    assert (ROOT / "docs" / "DIRECTOR_GUIDE.md").is_file()
    assert (ROOT / "docs" / "MOTION_ISOLATION.md").is_file()
    kb = json.loads((ROOT / "explainer_engine" / "standards" / "director_knowledge_base.json").read_text(encoding="utf-8"))
    assert kb.get("version") == "2.1.0"

    # 2. Stage ownership for director_brief and authored_intent_archive (V4_OWNERS is a tuple of (pattern, owner))
    owners_dict = dict(SG.V4_OWNERS)
    assert owners_dict.get("shots[*].director_brief") == "editor"
    assert owners_dict.get("shots[*].authored_intent_archive") == "editor"
    assert SG.owner_v4("shots[S02_SH008].director_brief") == "editor"
    assert SG.owner_v4("shots[S02_SH008].authored_intent_archive") == "editor"

    # 3. Validate production_script.json against schema and check the 6 vertical-slice briefs + 11 still_25d > 5.0 s
    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    schema = json.loads((ROOT / "explainer_engine" / "schemas" / "production_script.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(ps, schema)

    long_stills = [
        s["shot_id"]
        for s in ps["shots"]
        if s.get("route") == "still_25d" and float(s.get("target_duration_seconds") or 0) > 5.0
    ]
    assert len(long_stills) == 11

    shots_by_id = {s["shot_id"]: s for s in ps["shots"]}
    for sid in ("S02_SH001", "S02_SH003", "S02_SH004", "S02_SH008", "S05_SH020", "S08_SH002"):
        brief = shots_by_id[sid].get("director_brief")
        assert isinstance(brief, dict), f"missing director_brief on {sid}"
        assert brief["focal_anchor"]["keep_in_frame"] is True
        assert brief["word_turn_beat"]["word"]

    assert "authored_intent_archive" in shots_by_id["S02_SH008"]
    assert "authored_intent_archive" in shots_by_id["S08_SH002"]


def test_step1_dependency_fingerprints_and_decision2_no_effect_count_fails():
    from explainer_engine.core import fingerprints as FP
    from explainer_engine.production import direction as D
    from explainer_engine.production import living as L

    shot_a = {"shot_id": "S08_SH002", "route": "still_25d", "director_brief": {"focal_anchor": {"id": "button"}}}
    shot_b = {"shot_id": "S08_SH002", "route": "still_25d", "director_brief": {"focal_anchor": {"id": "candle"}}}
    fp_a = FP.direction_fingerprint(shot_a, picture_sha256="sha1")
    fp_b = FP.direction_fingerprint(shot_b, picture_sha256="sha1")
    assert fp_a != fp_b
    doc = {"dependency_fingerprint": fp_a}
    assert FP.is_direction_fresh(doc, shot=shot_a, picture_sha256="sha1")
    assert not FP.is_direction_fresh(doc, shot=shot_b, picture_sha256="sha1")

    # Creator Decision 2: DELIBERATELY_STILL shot with stillness_reason has 0 FAILs and 0 LP-08 count notes
    still_doc = {
        "schema": D.SCHEMA,
        "shot_id": "S08_SH002",
        "picture_sha256": "abc",
        "intent": "still_by_design",
        "stillness_reason": "Intimate relic study held in deliberate silence and stillness.",
        "seen": {
            "what": "a sepia family photograph in gloved hands",
            "objects": [{"id": "photo", "points": [[0.46, 0.63]], "names": ["photo"]}],
            "lights": [],
            "living": [
                {
                    "id": "dust_motes",
                    "kind": "dust",
                    "where": [0.5, 0.5],
                    "decision": "skip",
                    "why": "deliberate stillness for the photograph",
                    "area_pct": 10,
                    "text": 0,
                    "focus": 0,
                    "quality": 2,
                    "cost": 2,
                }
            ],
        },
        "tracks": [
            {"track": "camera", "op": "hold", "renderer": "directed25d", "validate": {}},
            {"track": "audio", "decision": "silent_by_design", "why": "intimate stillness"},
        ],
    }
    probs = D.check(still_doc, "abc", frames=120)
    assert [p for p in probs if p["level"] == "FAIL"] == []
    lp = L.plan(still_doc, 5.0)
    assert not any("LP-08" in n for n in lp["notes"])


def test_step2_understand_and_perceive_picture_real_centroids_not_05_05():
    from explainer_engine.production import perceive_picture as PP
    from explainer_engine.production import understand as U

    mask = np.zeros((100, 200), dtype=np.float32)
    mask[20:40, 140:180] = 1.0
    cx, cy = U._mask_centroid(mask)
    assert [cx, cy] != [0.5, 0.5]
    assert 0.75 <= cx <= 0.85 and 0.25 <= cy <= 0.35

    layers = _make_slice_layers("S08_SH002")
    pic = np.full((120, 200, 3), 35, dtype=np.uint8)
    pic[30:38, 166:174] = [255, 220, 120]
    pic[38:55, 164:176] = [70, 75, 80]

    shot_802 = {"shot_id": "S08_SH002", "lighting_and_time": "warm candlelight at night"}
    perc = PP.perceive_picture(shot_802, picture=pic, layers=layers)
    interp = PP.interpret_scene(shot_802, perc)
    assert all(obj["where"] != [0.5, 0.5] for obj in perc["objects"])
    assert perc["environment"]["sky_visible"]["value"] is True
    assert interp["reconciliation_state"] in ("ALIGNED", "ADAPTED_STAGING_NON_BREAKING")


def test_step3_motion_isolation_flame_star_clip_and_attachment_ramp():
    from explainer_engine.production import directed25d as D25
    from explainer_engine.production import living_fx as FX
    from explainer_engine.production import motion_isolation as MI

    h, w = 100, 160
    pic = np.full((h, w, 3), 40, dtype=np.uint8)
    # Bright flame tip at top (y=24..32), dark rigid tin holder below (y=34..52)
    pic[24:32, 76:84] = [255, 230, 130]
    pic[34:52, 72:88] = [55, 60, 65]
    fm = np.zeros((h, w), dtype=np.float32)
    fm[24:50, 72:88] = 1.0

    mover, anchor = MI.isolate_flame_mover(pic, fm, op="candle")
    assert float(mover[42, 80]) == 0.0
    assert float(anchor[42, 80]) == 1.0

    # Verify directed25d._Scene._deform_flame leaves the rigid holder untouched
    import cv2
    class _DummyScene:
        def __init__(self):
            self.cv2 = cv2
            self.W = w
            self.H = h
            self.masks_src = {}
        def _layer_of_light(self, li, layers):
            return None
    rgb_f = pic.astype(np.float32)
    out_rgb = D25.Stage._deform_flame(
        _DummyScene(),
        rgb_f.copy(),
        fm,
        {"id": "candle"},
        t=0.5,
        i=0,
        s=1.0,
        zoom=1.0,
        op="candle",
    )
    holder_diff = float(np.abs(out_rgb[40:50, 74:86] - rgb_f[40:50, 74:86]).max())
    assert holder_diff == 0.0

    # Star/glint mask clipping: stars must never leak onto foreground silhouettes
    sky_mask = np.zeros((h, w), dtype=np.float32)
    sky_mask[:45, :] = 1.0
    fg_mask = np.zeros((h, w), dtype=np.float32)
    fg_mask[20:90, 50:110] = 1.0
    base_reg = np.ones((h, w), dtype=np.float32)
    sparkle_mask = MI.isolate_sparkle_region(
        base_reg,
        op="stars",
        sky_mask=sky_mask,
        masks_src={"sky": sky_mask, "thomas": fg_mask},
    )
    assert float((sparkle_mask * fg_mask).max()) == 0.0

    # Verify living_fx._sparkle clips stars off the foreground silhouette
    class _DummyStage:
        def __init__(self):
            self.cv2 = cv2
            self.W = w
            self.H = h
            self.sw = w
            self.sh = h
            self.seed = 7
            self.sky = sky_mask
            self.masks_src = {"sky": sky_mask, "thomas": fg_mask}
            self.depth = np.full((h, w), 0.5, dtype=np.float32)
            self.p = {"seed": 7, "solemn_restraint": False}
            self.src = np.full((h, w, 3), 40, dtype=np.uint8)
            self.src[15, 25] = [245, 245, 250]   # valid sky star peak
            self.src[35, 75] = [245, 245, 250]   # peak inside fg_mask silhouette that MUST be clipped out
        def _to_out(self, pt, v=None, d=None):
            return pt[0], pt[1], 0.5

    frame_f = np.full((h, w, 3), 40.0, dtype=np.float32)
    sparkled = FX._sparkle(
        _DummyStage(),
        frame_f.copy(),
        np.full((h, w), 0.5, dtype=np.float32),
        {"op": "stars", "strength": 1.0, "box": [0.0, 0.0, 1.0, 0.50], "params": {"count": 40}},
        t=0.4,
        v={},
        mx=0.0,
        my=0.0,
        layers=[],
        op="stars",
    )
    fg_leak = float(np.abs(sparkled[25:44, 55:105] - frame_f[25:44, 55:105]).max())
    assert fg_leak == 0.0

    # Cloth attachment ramp: proximal 20% seam on left is 0.0, free right edge == 1.0
    xx = np.arange(0, 100, dtype=np.float32)[None, :]
    ramp = MI.attachment_ramp(xx, 0, 99, fixed_left=True, pinned_frac=0.20)
    assert float(ramp[:, :19].max()) == 0.0
    assert float(ramp[:, -1].min()) > 0.95


def test_step4_vertical_slice_direction_s08_sh002_s02_sh008_s05_sh020():
    from explainer_engine.production import direction as D
    from explainer_engine.production import living_director as LD

    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    shots = {s["shot_id"]: s for s in ps["shots"]}

    # 1. S08_SH002
    l_802 = _make_slice_layers("S08_SH002")
    spine_802 = [{"word": "Their", "frame": 0}, {"word": "commanders", "frame": 12}, {"word": "prevent", "frame": 32}]
    d_802 = LD.build_shot_direction_from_script(
        shots["S08_SH002"], ps, layers=l_802, spine=spine_802, fps=24.0, picture_sha256="sha_S08_SH002"
    )
    assert "dependency_fingerprint" in d_802
    assert all(o["where"] != [0.5, 0.5] for o in d_802["seen"]["objects"])
    assert [p for p in D.check(d_802, "sha_S08_SH002", spine=spine_802, frames=120, manifest=l_802["manifest"]) if p["level"] == "FAIL"] == []

    # 2. S02_SH008
    l_208 = _make_slice_layers("S02_SH008")
    spine_208 = [{"word": "In", "frame": 0}, {"word": "Pope", "frame": 24}, {"word": "Nobody", "frame": 72}, {"word": "asked", "frame": 80}]
    d_208 = LD.build_shot_direction_from_script(
        shots["S02_SH008"], ps, layers=l_208, spine=spine_208, fps=24.0, picture_sha256="sha_S02_SH008"
    )
    track_ids_208 = {t.get("id") for t in d_208["tracks"]}
    assert "fx_mug_steam" in track_ids_208
    kept_masks = {k.get("mask") for k in d_208.get("keep_in_frame", []) if k.get("mask")}
    assert {"thomas", "harris", "brazier"} <= kept_masks
    assert [p for p in D.check(d_208, "sha_S02_SH008", spine=spine_208, frames=120, manifest=l_208["manifest"]) if p["level"] == "FAIL"] == []

    # 3. S05_SH020
    l_520 = _make_slice_layers("S05_SH020")
    spine_520 = [{"word": "At", "frame": 0}, {"word": "Scottish", "frame": 20}, {"word": "German", "frame": 64}]
    d_520 = LD.build_shot_direction_from_script(
        shots["S05_SH020"], ps, layers=l_520, spine=spine_520, fps=24.0, picture_sha256="sha_S05_SH020"
    )
    cam_ops_520 = [t.get("op") for t in d_520["tracks"] if t.get("track") == "camera"]
    assert "pan_crop_2d" in cam_ops_520
    assert [p for p in D.check(d_520, "sha_S05_SH020", spine=spine_520, frames=120, manifest=l_520["manifest"]) if p["level"] == "FAIL"] == []


def test_step5_authoritative_sound_plan_decision3_map_and_yfq2_cough_bridge(tmp_path):
    from explainer_engine.episode import sound_plan as SP
    from explainer_engine.production import living_director as LD
    from explainer_engine.qa import perceive_audio as PA

    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    shots = {s["shot_id"]: s for s in ps["shots"]}

    # Decision 3: map shot S02_SH001 has no mandatory wind bed
    d_map = LD.build_shot_direction_from_script(shots["S02_SH001"], ps, fps=24.0, picture_sha256="sha_map")
    assert d_map["sound"]["beds"] == []

    # Build authoritative post-direction sound plan with direction override
    l_208 = _make_slice_layers("S02_SH008")
    d_208 = LD.build_shot_direction_from_script(shots["S02_SH008"], ps, layers=l_208, fps=24.0, picture_sha256="sha_208")
    directions = {"S02_SH001": d_map, "S02_SH008": d_208}
    plan = SP.build(ps, fps=24, directions=directions, plan_status="authoritative_post_direction")
    assert plan["plan_status"] == "authoritative_post_direction"
    assert "dependency_fingerprint" in plan

    events_by_shot = {sh["shot_id"]: sh.get("events", []) for sh in plan["shots"]}

    # S02_SH001 has tactile map cues (map_arrive_click, map_route_draw) and NO mandatory wind bed
    s02_sh001_classes = [e.get("class") for e in events_by_shot.get("S02_SH001", [])]
    assert "map_arrive_click" in s02_sh001_classes and "map_route_draw" in s02_sh001_classes
    assert "wind" not in s02_sh001_classes

    # YF-Q2: S02_SH003 carries the J-cut cough and trench wind bridge over the last ~1.5 s into S02_SH004
    s02_sh003_events = {e["event_id"]: e for e in events_by_shot.get("S02_SH003", [])}
    assert "S02_SH003.J_COUGH" in s02_sh003_events
    assert s02_sh003_events["S02_SH003.J_COUGH"]["class"] == "cough"
    assert s02_sh003_events["S02_SH003.J_COUGH"]["audio_basis"] == "director_j_cut"
    assert "S02_SH003.J_WIND" in s02_sh003_events

    # Offline deterministic audio perception check
    wav_path = tmp_path / "test_mix.wav"
    sr = 16000
    t = np.linspace(0, 3.0, sr * 3, endpoint=False)
    samples = np.zeros_like(t)
    samples[:sr] = 0.25 * np.sin(2 * np.pi * 220 * t[:sr])
    pcm = np.clip(samples * 32767, -32768, 32767).astype(np.int16)
    with wave.open(str(wav_path), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sr)
        wf.writeframes(pcm.tobytes())
    rep = PA.perceive_audio(wav_path, shot_id="S02_SH003")
    assert rep["dsp"]["duration_s"] == pytest.approx(3.0, abs=0.1)
    assert rep["technical_pass"] is True


def test_step6_look_and_listen_gate_and_yfq1_solemn_profile(tmp_path):
    from explainer_engine.edit import rhythm_profile as RP
    from explainer_engine.qa import look_and_listen as LL
    from explainer_engine.standards import sourced_rules as SR

    # YF-Q1: solemn_historical_docudrama in BP-169 and active on Truce 1914
    profiles = SR.T("BP-169", "profiles")
    assert "solemn_historical_docudrama" in profiles
    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    assert RP.resolve_profile_name(ps) == "solemn_historical_docudrama"

    # Step 6: Look-and-listen blocking record
    eval_row = LL.evaluate_shot_render(
        {"shot_id": "S08_SH002"},
        {"shot_id": "S08_SH002", "stillness_reason": "Intimate relic study", "tracks": []},
    )
    assert eval_row["motion_state"] == "DELIBERATELY_STILL"
    assert eval_row["passed_automated_checks"] is True

    rec_path = LL.write_look_and_listen_record(tmp_path, [eval_row], approved_by=None)
    assert rec_path.is_file()
    rows_unapproved = LL.check_look_and_listen_gate(tmp_path, rehearsal=False)
    assert any(r["status"] == "FAIL" and r["gate"] == "look_and_listen_claude_signoff" for r in rows_unapproved)

    # Sign off with reviewer approval
    LL.write_look_and_listen_record(tmp_path, [eval_row], approved_by="claude_opus", notes="Verified vertical slice.")
    rows_approved = LL.check_look_and_listen_gate(tmp_path, rehearsal=False)
    assert all(r["status"] == "PASS" for r in rows_approved)


# ============================================================================
# R2 STEP 7 TESTS (All 84 Briefs, LTX compose_prompt, Map Timeline/Grade,
# YouTube Fit 11 Splits / S05 Turn / S02 Chain / S08 Beats, Proportional BP-42/BP-76)
# ============================================================================

def test_step7_all_84_briefs_and_sequence_review_table():
    """R2 Step 7.1: All 84 Truce shots carry a schema-valid director_brief (owned by edit-planner/editor),
    no two adjacent shots share the same mood, and docs/wip/TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md covers all 84 shots."""
    from explainer_engine.scripting import stage_guard as SG
    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    shots = ps["shots"]
    assert len(shots) == 84
    for i, sh in enumerate(shots):
        sid = sh["shot_id"]
        brief = sh.get("director_brief")
        assert isinstance(brief, dict), f"{sid} missing director_brief"
        for req in ("narrative_purpose", "viewer_takeaway", "focal_anchor", "word_turn_beat", "restraint_note", "continuity_in", "continuity_out", "mood", "approval_status"):
            assert brief.get(req), f"{sid} director_brief missing {req}"
        assert brief["approval_status"] == "PENDING_CREATOR"
        if i > 0:
            prev_brief = shots[i - 1]["director_brief"]
            assert brief["mood"] != prev_brief["mood"], f"Neighbours {shots[i-1]['shot_id']} and {sid} have identical mood"

    owners = dict(SG.V4_OWNERS)
    assert owners.get("shots[*].director_brief") == "editor"
    assert owners.get("shots[*].split_plan") == "editor"

    rev_md = ROOT / "docs" / "wip" / "TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md"
    assert rev_md.is_file(), "Missing docs/wip/TRUCE_84_BRIEFS_SEQUENCE_REVIEW.md"
    md_text = rev_md.read_text(encoding="utf-8")
    for sh in shots:
        assert f"`{sh['shot_id']}`" in md_text
    assert md_text.count("PENDING_CREATOR") >= 84
    assert md_text.count("| picture not inspected |") == 81


def test_step7_ltx_compose_prompt_consumes_brief_and_reconciles_perception(tmp_path):
    """R2 Step 7.2: videolane/scene.py::compose_prompt consumes director_brief and reconciles action_start_state
    with start-picture perception (picture wins for physical staging; story-breaking conflicts queue to regeneration_queue.json)."""
    import copy
    from explainer_engine.videolane import scene as VSC
    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    by_id = {s["shot_id"]: copy.deepcopy(s) for s in ps["shots"]}

    # 1. Consumes director_brief and adapts non-breaking start state to picture
    sh_adapt = by_id["S02_SH008"]
    sh_adapt["action_start_state"] = "Soldiers under an open sky with a brass telescope."
    sh_adapt["perception"] = {
        "shot_id": "S02_SH008",
        "environment": {
            "sky_visible": {"value": False, "confidence": 0.95, "basis": "interior_dugout"},
            "enclosure": {"value": "interior_dugout", "confidence": 0.95},
        },
        "objects": [{"id": "thomas", "confidence": 0.92, "centroid": [0.24, 0.58], "bbox": [0.06, 0.22, 0.42, 0.94]}],
        "lights": [{"id": "coal_brazier", "confidence": 0.94, "centroid": [0.25, 0.74], "bbox": [0.16, 0.62, 0.34, 0.86]}],
        "scripted_queries_audit": [
            {"query": "brass telescope", "source_field": "action_start_state", "status": "not_detected", "breaks_spoken_narration": False}
        ],
    }
    comp_adapt = VSC.compose_prompt(ps, sh_adapt, episode_dir=tmp_path)
    assert "brief" in comp_adapt["parts"]
    assert "Director mood:" in comp_adapt["parts"]["brief"]
    assert comp_adapt["adapted_to_picture"] is True
    assert "enclosed timber dugout interior" in comp_adapt["reconciled_start_state"]
    assert comp_adapt["regeneration_required"] is False
    assert comp_adapt["prompt"].endswith(VSC.NOBODY_SPEAKS)

    # 2. Story-breaking conflict routes to production/regeneration_queue.json
    sh_break = by_id["S05_SH020"]
    sh_break["perception"] = {
        "shot_id": "S05_SH020",
        "environment": {"sky_visible": {"value": True, "confidence": 0.95, "basis": "layers_sky_mask"}},
        "objects": [],
        "lights": [],
        "scripted_queries_audit": [
            {"query": "chaplain", "source_field": "audio_lines", "status": "absent_corroborated", "breaks_spoken_narration": True}
        ],
    }
    comp_break = VSC.compose_prompt(ps, sh_break, episode_dir=tmp_path)
    assert comp_break["regeneration_required"] is True
    assert comp_break["reconciliation_state"] == "STORY_BREAKING_CONFLICT"
    q_file = tmp_path / "production" / "regeneration_queue.json"
    assert q_file.is_file()
    q_data = json.loads(q_file.read_text(encoding="utf-8"))
    assert any(it.get("shot_id") == "S05_SH020" for it in q_data.get("items", []))


def test_step7_map_keyframe_timeline_scene_sound_and_scene_grade():
    """R2 Step 7.3: Map actions export keyframe_frames/keyframe_seconds/keyframe_timeline to the visual-event timeline,
    get scene-aware Decision 3 sound via sound_of_map, and grade plates by scene via plate.resolve_scene_map_look."""
    from explainer_engine.episode import events as EV
    from explainer_engine.maps import actions as MA, plate as MP
    from explainer_engine.production import living_director as LD

    ep_dir = ROOT / "episodes" / "ep_truce_1914"
    episode = json.loads((ep_dir / "episode.json").read_text(encoding="utf-8"))
    ps = json.loads((ep_dir / "story" / "production_script.json").read_text(encoding="utf-8"))
    by_id = {s["shot_id"]: s for s in ps["shots"]}
    sh_map1 = by_id["S02_SH001"]
    sh_map2 = by_id["S02_SH002"]

    vis = EV.visual_events(sh_map1, ps, None, 24)
    assert vis and all("keyframe_frames" in e and "keyframe_seconds" in e for e in vis)
    for e in vis:
        kf = e["keyframe_frames"]
        ks = e["keyframe_seconds"]
        assert kf["onset_frame"] <= kf["peak_frame"] <= kf["end_frame"]
        assert ks["onset_s"] <= ks["peak_s"] <= ks["end_s"]

    plan1 = MA.plan(sh_map1, ps, episode["places"], 24)
    assert plan1.get("keyframe_timeline") and len(plan1["keyframe_timeline"]) == len(plan1["actions"])

    snd1 = LD.sound_of_map(sh_map1, ps, fps=24)
    assert snd1.get("keyframe_timeline")
    assert snd1.get("beds") == []

    # Scene-matched map plate grade: August 1914 (late_summer_1914) vs December 1914 Flanders (flanders_winter_1914)
    look_aug = MP.resolve_scene_map_look({}, scene={"title": "August 1914 Mobilization"}, shot=sh_map1)
    look_dec = MP.resolve_scene_map_look({}, scene={"title": "December 1914 Flanders Winter"}, shot=sh_map2)
    assert look_aug["scene_grade_profile"] == "late_summer_1914"
    assert look_dec["scene_grade_profile"] == "flanders_winter_1914"
    col_aug = MP.colours(look_aug)
    col_dec = MP.colours(look_dec)
    assert col_aug["land"] != col_dec["land"]
    assert col_aug["land"][0] > col_dec["land"][0]  # warmer ochre-red channel in August vs colder winter slate in December


def test_step7_youtube_fit_11_splits_s05_turn_s02_map_chain_s08_beats():
    """R2 Step 7.4: All 11 still_25d shots > 5.0 s split cleanly <= 5.0 s on clause boundaries via shot_split;
    S05_SH018 has its burial silence turn; S02_SH001->S02_SH003 chain continuously; S08_SH001..S08_SH004 have word-timed beats."""
    from explainer_engine.episode import shot_split as SS
    ps = json.loads((ROOT / "episodes" / "ep_truce_1914" / "story" / "production_script.json").read_text(encoding="utf-8"))
    by_id = {s["shot_id"]: s for s in ps["shots"]}
    lines_by_id = {al["line_id"]: al["text"] for al in ps["audio_lines"]}

    long_stills = [s for s in ps["shots"] if s.get("route") == "still_25d" and float(s.get("target_duration_seconds") or 0.0) > 5.0]
    assert len(long_stills) == 11
    for sh in long_stills:
        sid = sh["shot_id"]
        txt = " ".join(lines_by_id[lid] for lid in sh.get("audio_line_ids", []) if lid in lines_by_id)
        parts = SS.split_long_still(sh, None, max_s=5.0, text=txt)
        assert len(parts) >= 2, f"{sid} did not split"
        assert all(0.0 < float(p["target_duration_seconds"]) <= 5.0 + 1e-6 for p in parts)
        sp = sh.get("split_plan")
        assert isinstance(sp, dict) and sp["part_count"] == len(parts)

    # S05_SH018 tonal turn before the burial
    sh18 = by_id["S05_SH018"]
    assert sh18["transition_out"] == "cross_dissolve_8f"
    assert "Karl" in str(sh18.get("intentional_silence") or "")
    assert "Karl" in str((sh18.get("sound_design") or {}).get("silence") or "")

    # S02_SH001 -> S02_SH002 -> S02_SH003 continuous map chain + J-cut bridge
    assert by_id["S02_SH002"]["continuity_refs"]["inherit_from_previous_shot_id"] == "S02_SH001"
    assert by_id["S02_SH003"]["continuity_refs"]["inherit_from_previous_shot_id"] == "S02_SH002"
    assert by_id["S02_SH003"]["transition_out"] == "j_cut"

    # S08 kept alive with word-timed beats
    assert by_id["S08_SH001"]["motion_imitation"][0].get("at_word") == "January"
    assert by_id["S08_SH002"]["motion_imitation"][0].get("at_word") == "prevent"
    assert by_id["S08_SH003"]["motion_imitation"][0].get("at_word") == "four"
    assert by_id["S08_SH004"]["motion_imitation"][0].get("from_frac") == 0.15


def test_step7_proportional_rehook_intervals_bp42_bp76():
    """R2 Step 7.5: BP-42 and BP-76 define proportional runtime shares in sourced_rules.json and scale
    re-hook/turn intervals proportionally to episode runtime in engagement.py and story_lint.py."""
    from explainer_engine.qa import engagement as ENG
    from explainer_engine.scripting import story_lint as SL
    from explainer_engine.standards import sourced_rules as SR

    assert SR.T("BP-42", "review_gap_share") == 0.25
    assert SR.T("BP-42", "rehook_at_share") == [0.25, 0.5]
    assert SR.T("BP-76", "turn_gap_share") == 0.2083

    th_367 = ENG.proportional_rehook_thresholds(367.0)
    assert th_367["proportional"] is True
    assert abs(th_367["review_gap_s"] - 91.75) < 0.5
    assert abs(th_367["rehook_at_s"][0] - 91.75) < 0.5
    assert abs(th_367["rehook_at_s"][1] - 183.5) < 0.5

    gap_367 = SL.proportional_turn_gap_s(367.0)
    assert abs(gap_367 - 76.45) < 0.5
    assert SL.proportional_turn_gap_s(None) == 150.0
