"""Loop 4 v5.0 unit tests: Zero-sway 3D Rome maps, auto face-safe graphics, Roman explainers & word timeline compiler."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from explainer_engine.episode.word_timeline_compiler import (
    compile_word_locked_timeline,
    load_word_timestamps,
    save_compiled_timeline,
)
from explainer_engine.explainer.drawing_explainer import (
    VALID_EXPLAINER_SCENES,
    DrawingExplainerSpec,
    _build_explainer_html,
)
from explainer_engine.maps.cinema_map_webgl import (
    _build_maplibre_html,
    build_ancient_rome_ides_map_spec,
)
from explainer_engine.overlay.editorial_graphics import (
    EditorialGraphicSpec,
    _build_editorial_html,
    _resolve_safe_floating_origin,
    detect_face_avoid_zones,
)
from explainer_engine.qa.cinema_gates import check_map_stability


def _write_mp4(path: Path, frames_bgr: list[np.ndarray], fps: float = 24.0) -> None:
    h, w = frames_bgr[0].shape[:2]
    vw = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))
    for fr in frames_bgr:
        vw.write(fr)
    vw.release()


def _ensure_vendor_dir(monkeypatch: Any, tmp_path: Path) -> None:
    from explainer_engine.design_system import tokens

    if (tokens.DS_VENDOR_DIR / "rough.js").is_file() and (tokens.DS_VENDOR_DIR / "maplibre-gl.js").is_file():
        return
    stub = tmp_path / "vendor"
    stub.mkdir(parents=True, exist_ok=True)
    for fname in (
        "rough.js",
        "gsap.min.js",
        "SplitText.min.js",
        "DrawSVGPlugin.min.js",
        "CustomEase.min.js",
        "maplibre-gl.js",
        "maplibre-gl.css",
        "turf.min.js",
    ):
        (stub / fname).write_text("// stub\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "DS_VENDOR_DIR", stub)


def test_ancient_rome_3d_map_spec_locks_horizon_and_renders_city_layers(monkeypatch: Any, tmp_path: Path) -> None:
    _ensure_vendor_dir(monkeypatch, tmp_path)
    for kind in ("overview", "route"):
        spec = build_ancient_rome_ides_map_spec(kind=kind, duration_s=12.0)
        assert spec.lock_horizon is True
        assert spec.palette == "ancient_rome_parchment"
        assert spec.city_layers is not None
        assert spec.start_camera["pitch"] == spec.end_camera["pitch"]
        assert spec.start_camera["bearing"] == spec.end_camera["bearing"] == 0.0

        html_doc = _build_maplibre_html(spec, tmp_path / "unused.png", width=960, height=540)
        assert "fill-extrusion" in html_doc
        assert "Curia of Pompey" in html_doc
        assert "Domus Publica" in html_doc
        assert "SPEC.lock_horizon" in html_doc
        assert "INV_SCALE_START" in html_doc
        draw_overlay_block = html_doc.split("function drawOverlay(t_s)")[1].split("window.__renderAt")[0]
        assert "fillText(" not in draw_overlay_block


def test_check_map_stability_catches_rotational_gimbal_sway(tmp_path: Path) -> None:
    base = np.full((340, 580, 3), (30, 26, 22), dtype=np.uint8)
    for y in range(40, 300, 40):
        cv2.line(base, (20, y), (560, y), (145, 125, 95), 2, cv2.LINE_AA)
    for x in range(40, 540, 60):
        cv2.line(base, (x, 20), (x, 320), (120, 105, 85), 2, cv2.LINE_AA)
    cv2.putText(base, "FORUM ROMANUM", (130, 175), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (240, 235, 220), 2, cv2.LINE_AA)

    # Smooth zero-sway pan -> PASS
    smooth_frames: list[np.ndarray] = []
    for i in range(36):
        mat = np.float32([[1.0, 0.0, -i * 0.5], [0.0, 1.0, -i * 0.2]])
        smooth_frames.append(cv2.warpAffine(base, mat, (480, 270), flags=cv2.INTER_LINEAR))
    smooth_mp4 = tmp_path / "rome_smooth.mp4"
    _write_mp4(smooth_mp4, smooth_frames)
    res_ok = check_map_stability(smooth_mp4)
    assert res_ok["status"] == "PASS", res_ok
    assert res_ok["max_rot_sway_deg"] < 0.20

    # Alternating +/- 1.4 degree rotational horizon sway ("ქანაობა") -> FAIL
    sway_frames: list[np.ndarray] = []
    for i in range(36):
        ang = 1.4 if (i % 2 == 0) else -1.4
        rot = cv2.getRotationMatrix2D((290.0, 170.0), ang, 1.0)
        rot[0, 2] -= 50.0 + i * 0.4
        rot[1, 2] -= 35.0
        sway_frames.append(cv2.warpAffine(base, rot, (480, 270), flags=cv2.INTER_LINEAR))
    sway_mp4 = tmp_path / "rome_sway.mp4"
    _write_mp4(sway_mp4, sway_frames)
    res_bad = check_map_stability(sway_mp4)
    assert res_bad["status"] == "FAIL", res_bad
    assert res_bad["max_rot_sway_deg"] > 0.35
    assert any("rotational sway" in f.lower() for f in res_bad["findings"])


def test_auto_face_avoid_zones_and_nearest_safe_callout_origin(monkeypatch: Any, tmp_path: Path) -> None:
    _ensure_vendor_dir(monkeypatch, tmp_path)
    # Blank frame cleanly returns [] without crashing
    blank = tmp_path / "blank.jpg"
    cv2.imwrite(str(blank), np.zeros((270, 480, 3), dtype=np.uint8))
    assert detect_face_avoid_zones(blank) == []
    assert detect_face_avoid_zones(tmp_path / "missing.jpg") == []

    # Protected face zone centered on Caesar's portrait -> callout origin shifts cleanly out of face box
    face_zone = [(720, 180, 1240, 740)]
    sx, sy = _resolve_safe_floating_origin(860, 260, face_zone, note_w=520, note_h=165)
    assert (sx + 520 <= 720) or (sx >= 1240) or (sy + 165 <= 180) or (sy >= 740)

    spec = EditorialGraphicSpec(
        graphic_id="caesar_callout",
        template="chalk_circle_callout",
        title="JULIUS CAESAR",
        subtitle="HESITATES AT DAWN",
        duration_s=4.0,
        meta={"cx": 960, "cy": 420, "rx": 180, "ry": 210, "label_x": 860, "label_y": 260, "avoid_zones": face_zone},
    )
    doc = _build_editorial_html(spec, width=1920, height=1080)
    assert f"left:{sx}px; top:{sy}px;" in doc


def test_roman_drawing_explainer_scenes_render_valid_html(monkeypatch: Any, tmp_path: Path) -> None:
    _ensure_vendor_dir(monkeypatch, tmp_path)
    plate = tmp_path / "roman_plate.jpg"
    cv2.imwrite(str(plate), np.full((180, 320, 3), (35, 30, 24), dtype=np.uint8))
    for kind in ("roman_omens", "roman_conspiracy", "ides_closing_essay"):
        assert kind in VALID_EXPLAINER_SCENES
        spec = DrawingExplainerSpec(
            explainer_id=f"exp_{kind}",
            scene_kind=kind,
            title="IDES OF MARCH",
            subtitle="March 15, 44 BCE",
            illustration_path=plate,
            duration_s=9.0,
            era_stamp="ROME · 44 BCE",
        )
        spec.validate()
        doc = _build_explainer_html(spec, width=1920, height=1080)
        assert "rough.js" in doc
        assert "DrawSVGPlugin" in doc
        assert kind in doc


def test_word_timeline_compiler_snaps_anchors_and_enforces_dialogue_clearance(tmp_path: Path) -> None:
    words = [
        {"word": "Everyone", "start_s": 0.15, "end_s": 0.55},
        {"word": "Domus", "start_s": 5.80, "end_s": 6.20},
        {"word": "Publica", "start_s": 6.25, "end_s": 6.75},
        {"word": "wavers", "start_s": 11.40, "end_s": 11.95},
        {"word": "decides", "start_s": 24.10, "end_s": 24.65},
    ]
    ts_path = tmp_path / "word_timestamps.json"
    import json

    ts_path.write_text(json.dumps({"words": words}), encoding="utf-8")
    loaded = load_word_timestamps(ts_path)
    assert len(loaded) == 5

    shots = [
        {"shot_id": "s1", "scene_id": "hook", "route": "ltx_video", "duration_s": 5.0, "anchor_word": "Everyone"},
        {"shot_id": "s2", "scene_id": "map", "route": "map_action", "duration_s": 6.5, "anchor_word": "Domus"},
        {"shot_id": "s3", "scene_id": "atrium", "route": "ltx_video", "duration_s": 3.5, "anchor_word": "wavers"},
        {"shot_id": "s4_dlg", "scene_id": "atrium", "route": "ltx_video", "duration_s": 8.0, "has_dialogue": True},
        {"shot_id": "s5", "scene_id": "atrium", "route": "ltx_video", "duration_s": 5.0, "anchor_word": "decides"},
    ]
    # Clean narrator utterances with >= 0.40s margin around dialogue [15.0..23.0] and silence drop [14.3..14.8]
    clean_utterances = [
        {"id": "u1", "start_s": 0.10, "end_s": 14.10},
        {"id": "u2", "start_s": 23.60, "end_s": 27.50},
    ]
    silence_drops = [{"label": "pre_plea_drop", "start_s": 14.30, "end_s": 14.80}]

    res_ok = compile_word_locked_timeline(
        shots,
        clean_utterances,
        loaded,
        silence_drops=silence_drops,
        max_word_drift_s=1.2,
        min_dialogue_clearance_s=0.40,
    )
    assert res_ok.status == "PASS", res_ok.to_dict()
    assert res_ok.max_word_drift_s <= 1.2
    assert res_ok.min_dialogue_clearance_s >= 0.40
    out_json = save_compiled_timeline(res_ok, tmp_path / "compiled_timeline.json")
    assert out_json.is_file()

    # Narrator bleeding into character dialogue (only 0.10s clearance) -> FAIL!
    bad_utterances = [
        {"id": "u1", "start_s": 0.10, "end_s": 14.90},
        {"id": "u2", "start_s": 23.60, "end_s": 27.50},
    ]
    res_bad = compile_word_locked_timeline(
        shots,
        bad_utterances,
        loaded,
        silence_drops=silence_drops,
        max_word_drift_s=1.2,
        min_dialogue_clearance_s=0.40,
    )
    assert res_bad.status == "FAIL"
    assert any("clearance" in f.lower() for f in res_bad.findings)

    # Exceeding source clip max_duration_s MUST fail closed (preventing premature cuts / AV desync)
    overlong_shots = [
        {"shot_id": "s1", "scene_id": "hook", "route": "ltx_video", "duration_s": 7.5, "max_duration_s": 5.0, "anchor_word": "Everyone"},
    ]
    res_over = compile_word_locked_timeline(overlong_shots, [{"id": "u1", "start_s": 0.1, "end_s": 6.0}], loaded)
    assert res_over.status == "FAIL"
    assert any("max_duration_s" in f for f in res_over.findings)
