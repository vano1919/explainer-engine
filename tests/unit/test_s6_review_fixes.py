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
    assert parts[1]["framing"] == {"crop": 1.0, "focus": [0.72, 0.53]}
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


def test_s10_defect1_s05_sh020_pan_crop_2d_sign_hold_smooth_and_keep_in_frame(tmp_path):
    """DEFECT 1 (S10): S05_SH020 exact track list (push to left_group on 'scottish', pan_crop_2d to right_group on 'student',
    end = word + 30 frames, plus handheld) must:
      (a) move the window centre toward the target's x (left toward left_group, then right toward right_group),
      (b) stay within 1 % of its end position after the accent until the last frame,
      (c) have no frame-to-frame jump above 4x the clip median,
      (d) keep all hard-kept people inside the frame (people_cut share == 0.0).
    """
    w, h = 480, 270
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    base_img = (
        95.0
        + 28.0 * np.sin(2.0 * np.pi * xx / 48.0)
        + 22.0 * np.cos(2.0 * np.pi * yy / 36.0)
        + 12.0 * np.sin(2.0 * np.pi * (xx + yy) / 24.0)
    )
    img = np.stack([
        np.clip(base_img + 10.0, 0, 255),
        np.clip(base_img, 0, 255),
        np.clip(base_img - 10.0, 0, 255),
    ], axis=2).astype(np.uint8)
    p = tmp_path / "s05_sh020_s10.png"
    Image.fromarray(img).save(p)

    depth = np.clip(0.35 + 0.45 * (yy / h), 0.0, 1.0).astype(np.float32)
    left_m = np.zeros((h, w), np.float32)
    left_m[int(0.43 * h):int(0.875 * h), int(0.1458 * w):int(0.425 * w)] = 1.0
    right_m = np.zeros((h, w), np.float32)
    right_m[int(0.43 * h):int(0.787 * h), int(0.554 * w):int(0.8641 * w)] = 1.0
    depth[left_m > 0] = 0.62
    depth[right_m > 0] = 0.60
    # Outer right soldier slightly nearer than median to test per-person depth safety in _frame_people
    depth[int(0.38 * h):int(0.82 * h), int(0.76 * w):int(0.87 * w)] = 0.72

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
                ]
            },
        },
        "depth": depth,
        "plate": img.copy(),
        "hole": None,
        "masks": {"left_group": left_m, "right_group": right_m},
        "lights": {},
    }
    dir_doc = {
        "schema": D.SCHEMA,
        "shot_id": "S05_SH020",
        "intent": "intended",
        "far_share": 0.2,
        "tracks": [
            {
                "id": "cam_1",
                "track": "camera",
                "op": "push",
                "renderer": "directed25d",
                "params": {"strength": 0.55, "ease": "ease_in_out"},
                "timing": {"end": {"word": "scottish"}},
                "target": {"point": [0.518, 0.403]},
                "validate": {"measure": "scale"},
            },
            {
                "id": "cam_2",
                "track": "camera",
                "op": "push",
                "renderer": "directed25d",
                "params": {"strength": 1.0, "ease": "ease_out"},
                "timing": {"start": {"word": "scottish"}, "end": {"word": "scottish", "offset": 30}},
                "target": {"mask": "left_group", "point": [0.3, 0.514]},
                "validate": {"measure": "scale"},
            },
            {
                "id": "cam_3",
                "track": "camera",
                "op": "pan_crop_2d",
                "renderer": "directed25d",
                "params": {
                    "strength": 2.0,
                    "ease": "ease_out",
                    "direction": "right",
                    "overscan": 1.1,
                    "from_xy": [0.3, 0.514],
                    "to_xy": [0.717, 0.533],
                },
                "timing": {"start": {"word": "student"}, "end": {"word": "student", "offset": 30}},
                "target": {"mask": "right_group", "point": [0.717, 0.533]},
                "validate": {"measure": "shift_x_pct"},
            },
            {
                "id": "cam_hand",
                "track": "camera",
                "op": "handheld",
                "renderer": "directed25d",
                "params": {"strength": 0.3},
                "timing": {},
                "validate": {},
            },
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
    spine = [{"word": "scottish", "start_frame": 72}, {"word": "student", "start_frame": 136}]
    plan = D.resolve(dir_doc, 188, spine=spine)
    st = R.Stage(p, lay, plan, size=(w, h))

    vs = [st.view(f) for f in range(188)]
    cxs = [v["cx"] for v in vs]
    cys = [v["cy"] for v in vs]

    # (a) Window centre moves toward target's x: left on 'scottish' (72..102), then right on 'student' (136..166)
    assert cxs[102] < cxs[72] - 0.015, f"expected left move toward left_group, got {cxs[72]:.4f} -> {cxs[102]:.4f}"
    assert cxs[166] > cxs[136] + 0.015, f"expected right pan toward right_group, got {cxs[136]:.4f} -> {cxs[166]:.4f}"
    for f in range(136, 166):
        assert cxs[f + 1] >= cxs[f] - 2e-3, f"pan_crop_2d moved wrong way at frame {f}: {cxs[f]:.4f} -> {cxs[f + 1]:.4f}"

    # (b) After the accent (f >= 166), the window stays within 1 % of its end position until the last frame
    cx_end, cy_end = cxs[166], cys[166]
    for f in range(166, 188):
        assert abs(cxs[f] - cx_end) <= 0.01, f"cx drifted after accent at frame {f}: {cxs[f]:.4f} vs {cx_end:.4f}"
        assert abs(cys[f] - cy_end) <= 0.01, f"cy drifted after accent at frame {f}: {cys[f]:.4f} vs {cy_end:.4f}"

    # (c) Render all frames and assert no frame-to-frame jump above 4x the clip median
    frames = [st.render(f) for f in range(188)]
    diffs = [float(np.abs(frames[f].astype(np.float32) - frames[f - 1].astype(np.float32)).mean()) for f in range(1, 188)]
    med_diff = float(np.median(diffs))
    max_diff = float(np.max(diffs))
    assert med_diff > 0.0 and max_diff <= 4.0 * med_diff, (
        f"frame-to-frame jump {max_diff:.3f} exceeds 4x median {med_diff:.3f} (ratio {max_diff / max(1e-6, med_diff):.2f}x)"
    )

    # (d) Kept people stay inside the frame
    cut = st.people_cut(every=1)
    assert cut["share"] == 0.0, f"kept person cut during shot: {cut}"


def test_s10_defect2_close_span_paper_map_blob_contrast_and_accented_labels(monkeypatch):
    """DEFECT 2 (S10):
      1. Close-span views (60-90 km, upsample > 3x) fade raster relief to ~25 % and use clean parchment + light procedural
         hatch so low-frequency blob contrast (std of a 64 px Gaussian blur of luma) stays below CLOSE_BLOB_STD_MAX (D-59),
         calibrated against the old blurry output (~10.97-14.24 at 1/60 deg scale, ~1.65-4.41 on 1 deg fixture).
      2. Macro views (530-1000 km) have upsample <= 3x independent of render pixel width and keep sharp, noise-capped relief.
      3. Accented labels (Liège, Armentières) render with real accented glyphs rather than stripping accents.
    """
    from scipy.ndimage import gaussian_filter
    from explainer_engine.maps import draw as MDRAW
    from explainer_engine.maps import geo
    from explainer_engine.maps import plate as MPLATE
    from explainer_engine.maps import relief as MRELIEF

    # 1. Upsample depends on span_km, not render pixel width
    v_macro_hd = geo.View(4.5, 49.5, 650.0, 1920, 1080)
    v_close = geo.View(2.89, 50.71, 75.0, 640, 360)
    assert MPLATE.relief_upsample(v_macro_hd) < 3.0
    assert MPLATE.relief_upsample(v_close) > 10.0

    # 2. Close-span synthetic plate calibrated at SR_HR (1/60 deg) resolution: old blurry output vs fixed paper map output
    def _sr_hr_close_sample(view: geo.View, path=None) -> np.ndarray:
        rr, cc = np.mgrid[0:28, 0:48].astype(np.float32)
        grid = (
            MPLATE.RELIEF_FLAT
            + 0.095 * np.sin(cc / 4.2) * np.cos(rr / 3.4)
            + 0.055 * np.cos((cc + rr) / 5.0)
        ).astype(np.float32)
        yy = np.linspace(0, grid.shape[0] - 1, view.height, dtype=np.float32)
        xx = np.linspace(0, grid.shape[1] - 1, view.width, dtype=np.float32)
        from scipy.ndimage import map_coordinates
        ry, cx = np.meshgrid(yy, xx, indexing="ij")
        return np.clip(map_coordinates(grid, [ry, cx], order=3, mode="nearest"), 0.55, 0.98).astype(np.float32)

    monkeypatch.setattr(MRELIEF, "sample", _sr_hr_close_sample)
    monkeypatch.setattr(MPLATE, "land_mask", lambda view, ss=1: np.ones((view.height, view.width), dtype=bool))
    col = MPLATE.colours()

    # Old un-faded raster relief (disable_micro_relief=True, gain 1.6x) produces strong 64 px low-frequency blobs (> 8.0 luma std)
    rgb_blurry = MPLATE.relief_rgb(v_close, col, look={"disable_micro_relief": True})
    luma_blurry = (0.299 * rgb_blurry[..., 0] + 0.587 * rgb_blurry[..., 1] + 0.114 * rgb_blurry[..., 2]).astype(np.float32)
    blob_std_blurry = float(gaussian_filter(luma_blurry, sigma=64.0)[32:-32, 32:-32].std())

    # Fixed close-span paper plate fades raster relief to ~25 % and carries texture via clean high-frequency parchment + hatch
    rgb_fixed = MPLATE.relief_rgb(v_close, col, look={})
    luma_fixed = (0.299 * rgb_fixed[..., 0] + 0.587 * rgb_fixed[..., 1] + 0.114 * rgb_fixed[..., 2]).astype(np.float32)
    blob_std_fixed = float(gaussian_filter(luma_fixed, sigma=64.0)[32:-32, 32:-32].std())

    assert blob_std_blurry > 5.0
    assert blob_std_fixed < MPLATE.CLOSE_BLOB_STD_MAX, (
        f"close-span 64 px blob std {blob_std_fixed:.3f} exceeds threshold {MPLATE.CLOSE_BLOB_STD_MAX} (blurry was {blob_std_blurry:.3f})"
    )

    # 3. Accented labels (Liège, Armentières) preserve/restore accents and render distinct glyph masks from unaccented ASCII
    assert MDRAW.map_label_text("Liege") == "Liège"
    assert MDRAW.map_label_text("Liège") == "Liège"
    assert MDRAW.map_label_text("Armentieres") == "Armentières"
    assert MDRAW.map_label_text("Armentières") == "Armentières"

    f_map = MDRAW.font_for_text(28, "map", "Liège Armentières")
    assert not MDRAW.has_missing_glyph(f_map, "Liège Armentières")
    assert not np.array_equal(MDRAW.glyph_mask(f_map, "è"), MDRAW.glyph_mask(f_map, "e"))

    c_acc = MDRAW.Canvas(260, 80, (245, 240, 230), ss=2)
    c_acc.face = "map"
    c_acc.text((20, 20), "Liege - Armentieres", 22, (20, 20, 20))
    c_plain = MDRAW.Canvas(260, 80, (245, 240, 230), ss=2)
    c_plain.face = "ui"
    c_plain.d.text((20 * c_plain.ss, 20 * c_plain.ss), "Liege - Armentieres", font=f_map, fill=(20, 20, 20), anchor="la")
    diff_px = int((np.abs(np.asarray(c_acc.image(), np.int16) - np.asarray(c_plain.image(), np.int16)).max(axis=2) > 25).sum())
    assert diff_px >= 10, f"expected visible grave accent marks on Liège and Armentières, got diff_px={diff_px}"
