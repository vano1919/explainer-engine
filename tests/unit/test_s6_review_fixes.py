from __future__ import annotations
import json
from pathlib import Path
import numpy as np
import pytest
from PIL import Image
from explainer_engine.episode import run as RUN
from explainer_engine.episode import shot_split as SS
from explainer_engine.production import directed25d as R
from explainer_engine.production import direction as D
from explainer_engine.qa import gates as G
from explainer_engine.qa import motion_intent as MI
cv2 = pytest.importorskip("cv2") if hasattr(pytest, "importorskip") else __import__("cv2")
def _s05_sh020_stage(tmp_path: Path, wf_scot: int = 72, wf_stud: int = 136) -> R.Stage:
    w, h = 480, 270
    rng = np.random.default_rng(20)
    img = rng.integers(40, 180, (h, w, 3), dtype=np.uint8)
    p = tmp_path / "s05_sh020.png"
    Image.fromarray(img).save(p)
    depth = np.full((h, w), 0.62, np.float32)
    left_m = np.zeros((h, w), np.float32)
    left_m[int(0.341 * h):int(0.875 * h), int(0.146 * w):int(0.425 * w)] = 1.0
    right_m = np.zeros((h, w), np.float32)
    right_m[int(0.347 * h):int(0.787 * h), int(0.554 * w):int(0.864 * w)] = 1.0
    post_l = np.zeros((h, w), np.float32)
    post_l[int(0.70 * h):int(0.95 * h), int(0.03 * w):int(0.08 * w)] = 1.0
    post_r = np.zeros((h, w), np.float32)
    post_r[int(0.70 * h):int(0.95 * h), int(0.91 * w):int(0.96 * w)] = 1.0
    depth[post_l > 0] = 0.961
    depth[post_r > 0] = 0.826
    lay = {
        "manifest": {
            "lights": [
                {"id": "sun", "kind": "sun", "point": [0.497, 0.235]},
                {"id": "brazier_left", "kind": "fire", "point": [0.11, 0.54]},
                {"id": "brazier_right", "kind": "fire", "point": [0.91, 0.545]},
                {"id": "candle_3", "kind": "candle", "point": [0.556, 0.915]},
            ],
            "masks": {
                "objects": [
                    {"id": "left_group", "layer": False},
                    {"id": "right_group", "layer": False},
                    {"id": "post_left", "layer": True},
                    {"id": "post_right", "layer": True},
                ]
            },
        },
        "depth": depth,
        "plate": img.copy(),
        "hole": None,
        "masks": {"left_group": left_m, "right_group": right_m, "post_left": post_l, "post_right": post_r},
        "lights": {},
    }
    dir_doc = {
        "schema": D.SCHEMA,
        "shot_id": "S05_SH020",
        "intent": "intended",
        "far_share": 0.2,
        "tracks": [
            {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 0.153, "ease": "linear"},
             "timing": {"end": {"word": "scottish"}}, "target": {"point": [0.518, 0.403]}, "validate": {"measure": "scale"}},
            {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 1.0, "ease": "ease_out"},
             "timing": {"start": {"word": "scottish"}, "end": {"frame": 74}},
             "target": {"mask": "left_group", "point": [0.3, 0.514]}, "validate": {"measure": "scale"}},
            {"track": "camera", "op": "truck", "renderer": "directed25d",
             "params": {"strength": 2.0, "ease": "ease_out", "direction": "right"},
             "timing": {"start": {"word": "student"}, "end": {"frame": 162}},
             "target": {"mask": "right_group", "point": [0.717, 0.532]}, "validate": {"measure": "shift_x_pct"}},
            {"track": "camera", "op": "handheld", "renderer": "directed25d", "params": {"strength": 0.3}, "timing": {}, "validate": {}},
        ],
        "keep_in_frame": [
            {"face": [0.1965, 0.3941, 0.2181, 0.4437], "why": "live face"},
            {"face": [0.2959, 0.3749, 0.3136, 0.4146], "why": "live face"},
            {"face": [0.5709, 0.3488, 0.5854, 0.3820], "why": "live face"},
            {"face": [0.7949, 0.4010, 0.8160, 0.4530], "why": "live face"},
            {"light": "brazier_left", "soft": True, "why": "fire"},
            {"light": "brazier_right", "soft": True, "why": "fire"},
            {"light": "candle_3", "soft": True, "why": "candle"},
            {"light": "sun", "soft": True, "why": "sun"},
        ],
    }
    spine = [{"word": "scottish", "start_frame": wf_scot}, {"word": "student", "start_frame": wf_stud}]
    plan = D.resolve(dir_doc, 188, spine=spine)
    return R.Stage(p, lay, plan, size=(w, h))
def test_s05_sh020_soft_lights_yield_so_push_and_truck_move_the_camera(tmp_path):
    st = _s05_sh020_stage(tmp_path, wf_scot=72, wf_stud=136)
    push_acc = st.p["cameras"][1]
    assert push_acc["from"] == 72 and push_acc["to"] >= 102
    assert st.z0 >= 1.06
    v0 = st.view(0)
    v_scot = st.view(push_acc["to"])
    v_stud0 = st.view(136)
    v_stud1 = st.view(162)
    ccx0, _ = st._coef(v0, 0.62)
    ccx_scot, _ = st._coef(v_scot, 0.62)
    ccx_stud0, _ = st._coef(v_stud0, 0.62)
    ccx_stud1, _ = st._coef(v_stud1, 0.62)
    shift_scot_pct = (ccx0 - ccx_scot) / st.sw * 100.0
    assert shift_scot_pct >= 3.5
    shift_stud_pct = (ccx_stud0 - ccx_stud1) / st.sw * 100.0
    assert shift_stud_pct <= -6.5
    cut = st.people_cut()
    assert cut["share"] == 0.0 and MI.people_in_frame_row(cut)["status"] == G.PASS
    vs = [st.view(f) for f in range(188)]
    ccxs = [st._coef(v, 0.62)[0] / st.sw * 100.0 for v in vs]
    ss = [v["s"] * (1 + v["dp"] * 0.62) for v in vs]
    assert max(abs(ccxs[f] - ccxs[f - 1]) for f in range(1, 188)) <= 1.5
    assert max(abs((ss[f] / ss[f - 1] - 1.0) * 100.0) for f in range(1, 188)) <= 0.7
def test_pull_frame0_has_zero_fill_at_rest_and_feathered_rim_does_not_false_trigger_fill_invents(tmp_path):
    h, w = 270, 480
    rng = np.random.default_rng(14)
    src = rng.integers(50, 140, (h, w, 3), dtype=np.uint8)
    depth = np.repeat(np.linspace(0.05, 0.75, h, dtype=np.float32)[:, None], w, axis=1)
    post = np.zeros((h, w), np.uint8)
    post[40:250, 15:65] = 1
    src[post > 0] = (25, 30, 35)
    depth[post > 0] = 1.0
    p = tmp_path / "s06.png"
    Image.fromarray(src).save(p)
    hole = cv2.dilate(post, np.ones((15, 15), np.uint8)).astype(np.float32)
    plate = src.copy()
    plate[hole > 0] = (210, 215, 220)
    lay = {
        "manifest": {"lights": [], "masks": {"objects": [{"id": "post_left", "layer": True}]}},
        "depth": depth, "plate": plate, "hole": hole,
        "masks": {"post_left": post.astype(np.float32)}, "lights": {},
    }
    pull_plan = {"shot_id": "S06_SH001", "frames": 24, "handheld": None, "rack": None, "effects": [], "far_share": 0.2,
                 "cameras": [{"op": "pull", "strength": 0.75, "from": 0, "to": 24, "easing": "linear"}]}
    st_pull = R.Stage(p, lay, pull_plan, size=(w, h))
    tl0: dict = {}
    f0 = st_pull.render(0, tl0)
    assert abs(tl0["view"]["dp"]) < 1e-7
    assert MI.fill_at_rest(tl0["fill"], h)["band_px"] == 0.0
    assert st_pull.cover_k(st_pull.view(23), 1.0) > st_pull.cover_k(st_pull.view(0), 1.0)
    push_plan = {"shot_id": "S05_SH016", "frames": 24, "handheld": None, "rack": None, "effects": [], "far_share": 0.2,
                 "cameras": [{"op": "push", "strength": 0.2, "from": 0, "to": 24, "easing": "linear"}]}
    st_push = R.Stage(p, lay, push_plan, size=(w, h))
    w_watch = MI.Watch()
    for f in (0, 8):
        tl: dict = {}
        fr = st_push.render(f, tl)
        w_watch.add(f, fr, tl["fill"], None)
    assert MI.invented_detail_row(w_watch.summary(h)["fill_invents"])["status"] != G.REVIEW
def test_split_long_still_and_direction_resolve_keep_effects_cameras_and_cutin_framing(tmp_path):
    dir_doc = {
        "schema": D.SCHEMA,
        "shot_id": "S05_SH020",
        "intent": "intended",
        "far_share": 0.2,
        "seen": {
            "what": "Scottish and German soldiers by graves",
            "objects": [
                {"id": "left_group", "layer": False, "names": ["scottish"], "parts": [[[0.2, 0.5], [0.3, 0.6]]]},
                {"id": "right_group", "layer": False, "names": ["student"], "points": [[0.7, 0.5], [0.74, 0.56]]},
            ],
            "lights": [{"id": "brazier", "kind": "fire", "point": [0.11, 0.54]}],
            "living": [{"id": "mist", "kind": "mist", "where": [0.5, 0.6], "decision": "animate", "effects": ["fx_mist"]}],
        },
        "tracks": [
            {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 0.2, "ease": "linear"},
             "timing": {"end": {"word": "scottish"}}, "target": {"point": [0.5, 0.45]}, "validate": {"measure": "scale"}},
            {"track": "camera", "op": "push", "renderer": "directed25d", "params": {"strength": 1.0, "ease": "ease_out"},
             "timing": {"start": {"word": "scottish"}, "end": {"frame": 74}},
             "target": {"mask": "left_group", "point": [0.25, 0.55]}, "validate": {"measure": "scale"}},
            {"track": "camera", "op": "truck", "renderer": "directed25d",
             "params": {"strength": 2.0, "ease": "ease_out", "direction": "right"},
             "timing": {"start": {"word": "student"}, "end": {"frame": 162}},
             "target": {"mask": "right_group", "where": [0.72, 0.53]}, "validate": {"measure": "shift_x_pct"}},
            {"track": "camera", "op": "handheld", "renderer": "directed25d", "params": {"strength": 0.3}, "timing": {}, "validate": {}},
            {"id": "fx_mist", "track": "atmosphere", "op": "mist", "renderer": "directed25d", "params": {"strength": 0.9}, "target": {}},
        ],
    }
    raw_spine = [
        {"word": "The", "frame": 0, "start_frame": 0, "end_frame": 20, "start_s": 0.0, "end_s": 0.83},
        {"word": "Scottish", "frame": 44, "start_frame": 44, "end_frame": 65, "start_s": 1.83, "end_s": 2.71},
        {"word": "soldiers", "frame": 65, "start_frame": 65, "end_frame": 96, "start_s": 2.71, "end_s": 4.00},
        {"word": "A", "frame": 94, "start_frame": 94, "end_frame": 105, "start_s": 3.92, "end_s": 4.38},
        {"word": "student", "frame": 132, "start_frame": 132, "end_frame": 150, "start_s": 5.50, "end_s": 6.25},
        {"word": "psalm.", "frame": 150, "start_frame": 150, "end_frame": 188, "start_s": 6.25, "end_s": 7.8333},
    ]
    sp = SS.punctuate_spine(raw_spine, "The Scottish soldiers. A student psalm.")
    assert SS.is_clause_end(sp[2])
    shot = {"shot_id": "S05_SH020", "route": "still_25d", "target_duration_seconds": 7.8333, "total_frames": 188}
    parts = SS.split_long_still(shot, sp, max_s=5.0, fps=24, seen=dir_doc["seen"])
    assert [p["shot_id"] for p in parts] == ["S05_SH020a", "S05_SH020b"]
    assert parts[0]["end_frame"] <= 94 and parts[1]["start_frame"] == parts[0]["end_frame"]
    assert parts[1]["framing"] == {"crop": 1.35, "focus": [0.72, 0.53]}
    stud_w = next(w for w in parts[1]["spine"] if "student" in w["word"].lower())
    assert stud_w["frame"] == stud_w["start_frame"] == 132 - parts[1]["start_frame"]
    plan_a = RUN._resolve_direction_plan(dir_doc, parts[0], parts[0]["total_frames"], parts[0]["spine"])
    plan_b = RUN._resolve_direction_plan(dir_doc, parts[1], parts[1]["total_frames"], parts[1]["spine"])
    assert len(plan_a["effects"]) == 1 and plan_a["handheld"] == pytest.approx(0.3) and len(plan_a["cameras"]) >= 2
    assert len(plan_b["effects"]) == 1 and plan_b["handheld"] == pytest.approx(0.3) and len(plan_b["cameras"]) >= 1
    assert any(c["op"] == "truck" for c in plan_b["cameras"])
    h, w = 180, 320
    img = np.full((h, w, 3), 120, dtype=np.uint8)
    p = tmp_path / "cutin.png"
    Image.fromarray(img).save(p)
    lay = {"manifest": {"lights": [], "masks": {"objects": []}}, "depth": np.full((h, w), 0.5, np.float32),
           "plate": img.copy(), "hole": None, "masks": {}, "lights": {}}
    st_b = R.Stage(p, lay, plan_b, size=(w, h))
    assert st_b.z0 >= 1.35 and st_b.view(0)["cx"] > 0.55
def test_camera_segments_flags_cancelled_target_push_and_weak_truck():
    cams = [
        {"op": "push", "from": 72, "to": 74, "strength": 1.0, "target": {"mask": "left_group", "point": [0.3, 0.514]}},
        {"op": "truck", "direction": "right", "from": 136, "to": 162, "strength": 2.0,
         "target": {"mask": "right_group", "point": [0.717, 0.532]}},
    ]
    views = [{"s": 1.009 if f <= 72 else 1.07, "tx": 0.0 if f <= 136 else 0.10, "ty": 0.0, "far": 0.2} for f in range(188)]
    curve_bad = []
    for f in range(188):
        z = 0.0 if f <= 72 else 7.7
        px = 0.0 if f <= 72 else (-0.20 if f <= 136 else -0.20 - 1.45 * (f - 136) / 26.0)
        curve_bad.append({"t": f / 24.0, "zoom_pct": z, "pan_x_pct": px, "pan_y_pct": 0.0})
    row_bad = MI.segment_rows(cams, curve_bad, 24.0, views=views)[0]
    assert row_bad["status"] == G.FAIL
    assert not row_bad["measured"][0]["ok"] and not row_bad["measured"][1]["ok"]
    curve_good = []
    for f in range(188):
        z = 0.0 if f <= 72 else 7.0
        px = 0.0 if f <= 72 else (4.4 if f <= 136 else 4.4 - 7.5 * (f - 136) / 26.0)
        curve_good.append({"t": f / 24.0, "zoom_pct": z, "pan_x_pct": px, "pan_y_pct": 0.0})
    row_good = MI.segment_rows(cams, curve_good, 24.0, views=views)[0]
    assert row_good["status"] == G.PASS
def test_living_director_uses_horizontal_pan_without_angle_change_and_word_offset_end_for_people():
    from explainer_engine.production import living_director as LD
    d = {
        "intent": "intended",
        "people_mid_or_close": True,
        "seen": {
            "objects": [
                {"id": "left_group", "names": ["scottish"], "where": [0.30, 0.51]},
                {"id": "right_group", "names": ["student"], "where": [0.72, 0.53]},
            ],
            "living": [],
        },
    }
    spine = [{"word": "scottish", "start_frame": 44}, {"word": "student", "start_frame": 132}]
    faces = [{"box": [0.20, 0.39, 0.22, 0.44], "mouth": [0.21, 0.43], "share": 0.001, "score": 0.9}]
    tracks, _ = LD.choose_camera(d, spine, 188, 24.0, faces, set())
    cams = [t for t in tracks if t["op"] not in ("handheld",)]
    assert cams[1]["op"] == "push" and cams[1]["timing"]["end"] == {"word": "scottish", "offset": 30}
    assert cams[2]["op"] == "pan" and cams[2]["timing"]["end"] == {"word": "student", "offset": 30}
