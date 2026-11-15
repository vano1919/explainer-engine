"""Unit tests for Scene Director Steps 1-3 (D1 knowledge base & fixtures, D2 picture geometry & pan_crop_2d,
D3 feasibility, variety, audit & direction.check rules, D4 regenerated directions, and 16-row Truce fixture run)."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from explainer_engine.production import directed25d as R
from explainer_engine.production import direction as D
from explainer_engine.production import living_director as LD
from explainer_engine.production import understand as U


ROOT = Path(__file__).resolve().parents[2]


def test_d1_knowledge_base_and_truce_fixtures_exist_and_validate():
    kb_path = ROOT / "explainer_engine" / "standards" / "director_knowledge_base.json"
    assert kb_path.is_file()
    kb = D.load_knowledge_base(kb_path)
    assert set(kb.keys()) >= {"idiom_grammar", "camera_feasibility_rules", "variety_and_continuity_rules"}
    assert "truce_1914_examples" not in kb
    assert len(kb["idiom_grammar"]) >= 10
    assert {"push_in", "pull_back", "pan_crop_2d", "crane_up", "truck_25d", "orbit_small", "rack_focus"} <= set(
        kb["camera_feasibility_rules"].keys()
    )
    var = kb["variety_and_continuity_rules"]
    assert var["no_two_same_camera_ops_in_a_row"] is True
    assert var["max_push_in_in_5_shot_window"] == 2
    assert var["max_push_share_non_map"] <= 0.40

    fix_path = ROOT / "tests" / "fixtures" / "truce_1914_examples.json"
    assert fix_path.is_file()
    fix = json.loads(fix_path.read_text(encoding="utf-8"))
    rows = fix.get("truce_1914_examples") or []
    assert len(rows) == 16
    assert rows[0]["shot_id"] == "S01_SH001" and rows[-1]["shot_id"] == "S08_SH003"


def test_d2_understand_writes_and_computes_picture_geometry(tmp_path):
    # 1. Pure helper computes geometry when fields are missing from an existing manifest + seen.
    manifest_legacy = {
        "schema": U.SCHEMA,
        "shot_id": "S05_SH020",
        "size": [1376, 768],
        "depth": {
            "chosen": "depth_pro",
            "candidates": {
                "depth_pro": {
                    "checks": {
                        "right": 2,
                        "of": 2,
                        "rows": [
                            {"near": [0.5, 0.85], "far": [0.5, 0.25], "values": [0.785, 0.004], "right": True},
                            {"near": [0.27, 0.52], "far": [0.5, 0.25], "values": [0.47, 0.004], "right": True},
                        ],
                    }
                }
            },
        },
        "masks": {
            "hole_share": 0.0426,
            "objects": [
                {"id": "left_group", "what": "Scottish soldiers", "layer": False, "area_pct": 11.4},
                {"id": "right_group", "what": "German soldiers", "layer": False, "area_pct": 10.6},
            ],
        },
        "lights": [{"id": "sun", "kind": "sun", "point": [0.497, 0.235]}],
    }
    seen = {
        "what": "Scottish and German soldiers around open graves at dawn",
        "objects": [
            {"id": "left_group", "what": "Scottish soldiers", "layer": False, "points": [[0.14, 0.55], [0.42, 0.72]]},
            {"id": "right_group", "what": "German soldiers", "layer": False, "points": [[0.56, 0.52], [0.86, 0.75]]},
        ],
        "living": [{"id": "sky", "kind": "sky", "where": [0.5, 0.15], "area_pct": 30.0}],
    }
    geom = U.picture_geometry(manifest_legacy, seen)
    assert len(geom["person_boxes"]) == 2
    assert geom["edge_margin_x"] == pytest.approx(0.115, abs=1e-3)
    assert geom["edge_margin_y"] < 0.5
    assert geom["sky_area_pct"] == pytest.approx(30.0)
    assert geom["fg_bg_depth_delta"] == pytest.approx(0.781, abs=1e-2)
    assert geom["unlayered_people"] is True

    # 2. understand() writes all six D2 geometry fields into manifest.json using synthetic runners (no model weights).
    h, w = 80, 120
    rgb = np.full((h, w, 3), 90, dtype=np.uint8)
    pic_path = tmp_path / "shot.png"
    Image.fromarray(rgb).save(pic_path)
    disp = np.repeat(np.linspace(0.0, 1.0, h, dtype=np.float32)[:, None], w, axis=1)
    seg_mask = np.zeros((h, w), dtype=np.float32)
    seg_mask[20:70, 10:40] = 1.0
    disp = np.full((h, w), 0.1, dtype=np.float32)
    disp[seg_mask > 0] = 0.95

    dir_doc = {
        "shot_id": "SYN_01",
        "seen": {
            "what": "one soldier under open sky",
            "objects": [{"id": "thomas", "what": "soldier Thomas", "points": [[0.25, 0.55]], "layer": True}],
            "lights": [{"id": "sun", "kind": "sun", "point": [0.5, 0.15], "radius": 0.05}],
            "depth_checks": [{"near": [0.25, 0.75], "far": [0.5, 0.1], "why": "soldier nearer than sky"}],
            "living": [{"id": "sky", "kind": "sky", "where": [0.5, 0.15], "area_pct": 28.0}],
        },
    }
    out_dir = tmp_path / "layers"
    man = U.understand(
        pic_path,
        dir_doc["seen"],
        out_dir=out_dir,
        depth_model="da_v2_small",
        runners={
            "da_v2_small": lambda img: {"disparity": disp},
            "sam": lambda img, prompts: [{"mask": seg_mask > 0.5, "score": 0.96} for _ in prompts],
            "lama": lambda img, hole: img.copy(),
        },
    )
    saved = json.loads((out_dir / "manifest.json").read_text(encoding="utf-8"))
    for key in ("person_boxes", "edge_margin_x", "edge_margin_y", "sky_area_pct", "fg_bg_depth_delta", "unlayered_people"):
        assert key in man and key in saved
    assert len(saved["person_boxes"]) >= 1
    assert 0.05 <= saved["edge_margin_x"] <= 0.15
    assert saved["sky_area_pct"] == pytest.approx(28.0)
    assert saved["fg_bg_depth_delta"] > 0.3
    assert saved["unlayered_people"] is False


def test_d2_directed25d_pan_crop_2d_rigid_window_pan_zero_parallax_zero_fill(tmp_path):
    assert "pan_crop_2d" in R.CAMERA_OPS
    assert "pan_crop_2d" in D.CAMERA_OPS

    h, w = 180, 320
    rng = np.random.default_rng(7)
    img = rng.integers(40, 200, (h, w, 3), dtype=np.uint8)
    p = tmp_path / "pan2d.png"
    Image.fromarray(img).save(p)

    depth = np.full((h, w), 0.15, dtype=np.float32)
    fg_mask = np.zeros((h, w), dtype=np.float32)
    fg_mask[40:150, 60:120] = 1.0
    depth[fg_mask > 0] = 0.95
    hole = fg_mask.copy()
    plate = np.zeros_like(img)  # black plate: any fill leak would show up in tl["fill"] and frame pixels

    lay = {
        "manifest": {"lights": [], "masks": {"objects": [{"id": "soldier_fg", "layer": True}]}},
        "depth": depth,
        "plate": plate,
        "hole": hole,
        "masks": {"soldier_fg": fg_mask},
        "lights": {},
    }
    dir_doc = {
        "schema": D.SCHEMA,
        "shot_id": "TEST_PAN2D",
        "intent": "intended",
        "tracks": [
            {
                "track": "camera",
                "op": "pan_crop_2d",
                "renderer": "directed25d",
                "params": {
                    "strength": 1.5,
                    "direction": "right",
                    "overscan": 1.10,
                    "from_xy": [0.32, 0.50],
                    "to_xy": [0.68, 0.50],
                    "ease": "ease_in_out",
                },
                "timing": {"start": {"frame": 0}, "end": {"frame": 24}},
                "validate": {"measure": "shift_x_pct"},
            }
        ],
    }
    plan = D.resolve(dir_doc, 24)
    st = R.Stage(p, lay, plan, size=(w, h))
    assert st.z0 >= 1.10

    v0 = st.view(0)
    v12 = st.view(12)
    v23 = st.view(23)
    for v in (v0, v12, v23):
        assert v["dp"] == 0.0 and v["tx"] == 0.0 and v["ty"] == 0.0
        assert v["no_parallax"] is True
        # Foreground (z=0.95) and background (z=0.10) have identical affine transform (zero depth parallax).
        assert st._coef(v, 0.95) == pytest.approx(st._coef(v, 0.10))

    assert v23["cx"] > v0["cx"] + 0.03
    tl: dict = {}
    st.render(23, tl)
    assert float(tl["fill"].max()) == 0.0


def test_d3_choose_camera_feasibility_variety_push_cap_and_audit():
    # 1. Two-group shot with unlayered crowd near lateral edges vetoes orbit/truck and downgrades to pan_crop_2d.
    d_crowd = {
        "shot_id": "S05_SH020",
        "intent": "intended",
        "people_mid_or_close": True,
        "seen": {
            "what": "Scottish and German soldiers by graves",
            "objects": [
                {"id": "left_group", "what": "Scottish soldiers", "layer": False, "names": ["scottish"], "points": [[0.14, 0.51], [0.35, 0.65]]},
                {"id": "right_group", "what": "German soldiers", "layer": False, "names": ["student"], "points": [[0.58, 0.52], [0.86, 0.68]]},
            ],
            "living": [],
        },
    }
    spine = [{"word": "scottish", "start_frame": 44}, {"word": "student", "start_frame": 132}]
    faces = [
        {"box": [0.196, 0.39, 0.218, 0.44], "mouth": [0.207, 0.43], "share": 0.001, "score": 0.92},
        {"box": [0.795, 0.40, 0.816, 0.45], "mouth": [0.805, 0.44], "share": 0.001, "score": 0.91},
    ]
    tracks, _ = LD.choose_camera(d_crowd, spine, 188, 24.0, faces, set())
    ops = [t["op"] for t in tracks if t["track"] == "camera"]
    assert "pan_crop_2d" in ops
    assert "orbit" not in ops and "truck" not in ops
    audit = d_crowd["choice"]["audit"]
    assert audit["idiom"]["id"] == "IDM_TWO_GROUP_PIVOT"
    assert audit["chosen"]["primary_op"] == "pan_crop_2d"
    assert "orbit_small" in audit["rejected"] and "truck_25d" in audit["rejected"]
    assert audit["measurements"]["unlayered_people"] is True

    # 2. Variety & push-cap across 5 consecutive non-map shots that would otherwise all push.
    ep_state: dict = {}
    prev_dir = None
    chosen_primary = []
    for idx in range(5):
        shot_d = {
            "shot_id": f"S03_SH00{idx + 1}",
            "intent": "intended",
            "seen": {
                "what": "a soldier by a brazier in a trench",
                "objects": [{"id": "thomas", "what": "soldier Thomas", "points": [[0.45, 0.5]], "layer": True}],
                "living": [{"id": "sky", "kind": "sky", "where": [0.5, 0.15], "area_pct": 22.0}],
            },
        }
        next_s = {"shot_id": f"S03_SH00{idx + 2}"} if idx < 4 else None
        LD.choose_camera(
            shot_d,
            [],
            96,
            24.0,
            [{"box": [0.42, 0.30, 0.48, 0.42], "mouth": [0.45, 0.39], "share": 0.007, "score": 0.95}],
            set(),
            prev_direction=prev_dir,
            next_shot=next_s,
            episode_state=ep_state,
        )
        p_op = shot_d["choice"]["audit"]["chosen"]["primary_op"]
        chosen_primary.append(p_op)
        prev_dir = shot_d

    assert all(chosen_primary[i] != chosen_primary[i - 1] for i in range(1, len(chosen_primary)))
    assert sum(1 for m in chosen_primary if m == "push") <= 2


def test_d3_direction_check_feasibility_and_audit_present_rows():
    # Vetoed lateral angle-change move (truck/orbit) with people near edge -> FAIL (_feasibility)
    bad_veto = copy.deepcopy(D.load(ROOT / "tests" / "unit" / "test_direction.py") if False else {
        "schema": D.SCHEMA,
        "shot_id": "S05_SH020",
        "picture_sha256": "abc",
        "intent": "intended",
        "seen": {
            "what": "two groups of soldiers by graves",
            "objects": [{"id": "left_group", "what": "Scottish soldiers", "layer": False, "points": [[0.11, 0.5]]}],
            "lights": [{"id": "flame", "point": [0.5, 0.7], "radius": 0.03}],
            "living": [
                {"id": "brazier", "kind": "fire", "where": [0.5, 0.7], "decision": "animate", "effects": ["fx_fire"],
                 "area_pct": 2, "text": 1, "focus": 2, "quality": 2, "cost": 2},
                {"id": "mist", "kind": "mist", "where": [0.5, 0.6], "decision": "animate", "effects": ["fx_mist"],
                 "area_pct": 30, "text": 0, "focus": 1, "quality": 2, "cost": 2},
            ],
        },
        "tracks": [
            {"track": "camera", "op": "truck", "renderer": "directed25d", "params": {"strength": 2.0, "direction": "right"},
             "timing": {"start": {"frame": 0}, "end": {"frame": 60}}, "validate": {"measure": "shift_x_pct"}},
            {"track": "lighting", "op": "fire", "renderer": "directed25d", "target": {"lights": ["flame"]}, "params": {}, "id": "fx_fire"},
            {"track": "atmosphere", "op": "mist", "renderer": "directed25d", "params": {}, "id": "fx_mist"},
            {"track": "audio", "decision": "ambience_only", "why": "wind"},
        ],
        "choice": {},
    })
    probs = D.check(bad_veto, "abc")
    feas_fails = [p for p in probs if p.get("rule") == "_feasibility" and p["level"] == "FAIL"]
    audit_revs = [p for p in probs if p.get("rule") == "_audit_present" and p["level"] == "REVIEW"]
    assert len(feas_fails) == 1 and "creator's veto" in feas_fails[0]["what"]
    assert len(audit_revs) == 1 and "choice.audit" in audit_revs[0]["what"]

    # Non-veto feasibility violation (crane with 0% sky and no people near edge) -> REVIEW (D-59), not FAIL.
    crane_no_sky = copy.deepcopy(bad_veto)
    crane_no_sky["seen"]["objects"] = []
    crane_no_sky["seen"]["sky_open"] = False
    crane_no_sky["tracks"][0] = {
        "track": "camera", "op": "crane", "renderer": "directed25d", "params": {"strength": 1.0, "direction": "up"},
        "timing": {"start": {"frame": 0}, "end": {"frame": 60}}, "validate": {"measure": "shift_y_pct"},
    }
    probs_crane = D.check(crane_no_sky, "abc")
    assert not [p for p in probs_crane if p.get("rule") == "_feasibility" and p["level"] == "FAIL"]
    assert any(p.get("rule") == "_feasibility" and p["level"] == "REVIEW" for p in probs_crane)


def test_d4_six_regenerated_directions_and_s05_sh020_uses_horizontal_pan():
    s20_base = {
        "schema": D.SCHEMA,
        "shot_id": "S05_SH020",
        "picture_sha256": "0ed409434bda10ea47fdcc750eb5397772daf59f95608f6c5b062a0ec3f72919",
        "intent": "intended",
        "people_mid_or_close": True,
        "scene": {"weather": ["snow_light", "mist"], "surroundings": "dawn, open field, frozen ground, graves, braziers", "wind": [0.02, 0.0]},
        "seen": {
            "what": "Scottish and German soldiers standing around open graves at dawn with candles and braziers",
            "sky_open": True,
            "objects": [
                {"id": "left_group", "what": "Scottish soldiers on the left", "layer": False, "names": ["scottish", "chaplain"], "points": [[0.14, 0.55], [0.42, 0.72]]},
                {"id": "right_group", "what": "German soldiers on the right", "layer": False, "names": ["student"], "points": [[0.56, 0.52], [0.86, 0.75]]},
            ],
            "lights": [
                {"id": "sun", "kind": "sun", "point": [0.497, 0.235]},
                {"id": "brazier_left", "kind": "fire", "point": [0.11, 0.54], "radius": 0.03},
                {"id": "brazier_right", "kind": "fire", "point": [0.91, 0.545], "radius": 0.03},
                {"id": "candle_1", "kind": "candle", "point": [0.422, 0.903], "radius": 0.015},
            ],
            "living": [
                {"id": "sun", "kind": "sun", "where": [0.497, 0.235], "area_pct": 15.0},
                {"id": "sky", "kind": "sky", "where": [0.5, 0.15], "area_pct": 30.0},
                {"id": "mist", "kind": "mist", "where": [0.5, 0.55], "area_pct": 40.0},
                {"id": "brazier_left", "kind": "fire", "where": [0.11, 0.54], "area_pct": 2.0},
                {"id": "brazier_right", "kind": "fire", "where": [0.91, 0.545], "area_pct": 2.0},
                {"id": "candles", "kind": "candle", "where": [0.5, 0.88], "area_pct": 1.5, "lights": ["candle_1"]},
                {"id": "frost", "kind": "ice", "where": [0.5, 0.75], "area_pct": 8.0, "box": [0.2, 0.65, 0.8, 0.9]},
            ],
        },
        "choice": {
            "faces": [
                {"box": [0.1965, 0.3941, 0.2181, 0.4437], "mouth": [0.2073, 0.4338], "share": 0.0011, "score": 0.92},
                {"box": [0.7949, 0.4010, 0.8160, 0.4530], "mouth": [0.8055, 0.4426], "share": 0.0011, "score": 0.91},
            ]
        },
    }
    spine_s20 = [
        {"word": "At", "start_frame": 0}, {"word": "one", "start_frame": 8}, {"word": "burial,", "start_frame": 18},
        {"word": "a", "start_frame": 38}, {"word": "Scottish", "start_frame": 44}, {"word": "chaplain", "start_frame": 60},
        {"word": "read", "start_frame": 76}, {"word": "the", "start_frame": 86}, {"word": "Twenty-Third", "start_frame": 94},
        {"word": "Psalm.", "start_frame": 112}, {"word": "A", "start_frame": 120}, {"word": "German", "start_frame": 124},
        {"word": "student", "start_frame": 132}, {"word": "read", "start_frame": 146}, {"word": "it", "start_frame": 154},
    ]
    s20 = LD.direct(s20_base, spine_s20, 188, 24.0)
    probs = D.check(s20, s20["picture_sha256"], spine_s20, 24.0, 188)
    assert [p for p in probs if p["level"] == "FAIL"] == []
    assert D._audit_present(s20) == []
    cam_ops = [t["op"] for t in s20["tracks"] if t["track"] == "camera"]
    assert "orbit" not in cam_ops and "truck" not in cam_ops
    assert "pan_crop_2d" in cam_ops
    pan_track = next(t for t in s20["tracks"] if t.get("op") == "pan_crop_2d")
    assert pan_track["target"]["mask"] == "right_group"
    assert pan_track["timing"]["start"] == {"word": "student"}


def test_director_over_16_truce_fixture_rows():
    fix_path = ROOT / "tests" / "fixtures" / "truce_1914_examples.json"
    rows = json.loads(fix_path.read_text(encoding="utf-8"))["truce_1914_examples"]
    assert len(rows) == 16

    ep_state: dict = {}
    prev_dir = None
    decisions = []

    for i, row in enumerate(rows):
        next_row = rows[i + 1] if i + 1 < len(rows) else None
        pf = row.get("picture_facts") or {}
        is_map = str(row.get("route") or "") == "map_action"
        words = [
            {"word": w, "start_frame": idx * 8}
            for idx, w in enumerate(str(row.get("narration") or "").split())
        ]
        frames = int(round(float(row.get("duration_s", 4.0)) * 24.0))
        d = {
            "schema": D.SCHEMA,
            "shot_id": row["shot_id"],
            "kind": "map" if is_map else "photo",
            "route": row.get("route", "still_25d"),
            "intent": "intended",
            "narration": row.get("narration", ""),
            "picture_facts": pf,
            "rejected_moves": row.get("rejected_moves") or {},
            "seen": {
                "what": row.get("narration", row["shot_id"]),
                "sky_open": bool(pf.get("sky_open", True)),
                "objects": [],
                "lights": [],
                "living": [{"id": "sky", "kind": "sky", "where": [0.5, 0.15], "area_pct": float(pf.get("sky_area_pct", 25.0))}]
                if pf.get("sky_open")
                else [],
            },
        }
        if row["shot_id"] == "S05_SH020":
            d["people_mid_or_close"] = True
            d["seen"]["objects"] = [
                {"id": "left_group", "what": "Scottish soldiers", "layer": False, "names": ["scottish"], "where": [0.30, 0.51]},
                {"id": "right_group", "what": "German soldiers", "layer": False, "names": ["student"], "where": [0.72, 0.53]},
            ]
        elif row["shot_id"] == "S02_SH008":
            d["people_mid_or_close"] = True
            d["seen"]["objects"] = [
                {"id": "thomas", "what": "Private Thomas Hale", "layer": True, "names": ["nobody"], "where": [0.355, 0.33]},
            ]
        faces = [
            {"box": fb, "mouth": [(fb[0] + fb[2]) / 2, (fb[1] + fb[3]) / 2], "share": 0.01, "score": 0.92}
            for fb in (pf.get("faces") or [])
        ]
        chosen_fx = {"light_fade"} if "light_fade" in (row.get("living_fx") or []) else set()
        tracks, _ = LD.choose_camera(
            d,
            words,
            frames,
            24.0,
            faces,
            chosen_fx,
            prev_direction=prev_dir,
            next_shot=next_row,
            episode_state=ep_state,
        )
        d["tracks"] = tracks
        audit = d.get("choice", {}).get("audit")
        assert audit and audit.get("idiom") and audit.get("chosen") and audit.get("rejected") and audit.get("measurements")
        # Zero vetoed angle-change moves
        cam_ops = [t["op"] for t in tracks if t.get("track") == "camera"]
        assert "orbit" not in cam_ops and "orbit_small" not in cam_ops
        assert "truck" not in cam_ops and "truck_25d" not in cam_ops
        assert not [p for p in D._feasibility(d) if p["level"] == "FAIL"]

        decisions.append((row["shot_id"], is_map, audit["chosen"]["primary_op"], audit))
        prev_dir = d

    # No two identical consecutive primary moves across the sequence
    primary_ops = [op for _, _, op, _ in decisions]
    for idx in range(1, len(primary_ops)):
        assert primary_ops[idx] != primary_ops[idx - 1], (
            f"Consecutive identical moves at {decisions[idx - 1][0]} -> {decisions[idx][0]}: {primary_ops[idx]}"
        )

    # Non-map shots: no two identical consecutive moves, push share <= 40%, and <= 2 pushes in any 5-shot window
    non_map_ops = [op for _, is_map, op, _ in decisions if not is_map]
    for idx in range(1, len(non_map_ops)):
        assert non_map_ops[idx] != non_map_ops[idx - 1]
    push_share = sum(1 for op in non_map_ops if op == "push") / len(non_map_ops)
    assert push_share <= 0.40, f"Push share {push_share:.2%} exceeds 40%"
    for i in range(len(non_map_ops) - 4):
        win = non_map_ops[i:i + 5]
        assert sum(1 for op in win if op == "push") <= 2
