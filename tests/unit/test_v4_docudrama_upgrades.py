"""Unit tests for v4.0 Docudrama Engine upgrades (Loops 1-4):
- Loop 1: Zero-jitter 2x supersampled WebGL2 maps & check_map_stability()
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2
import numpy as np

from explainer_engine.maps.cinema_map_webgl import WebGLMapSpec, _build_maplibre_html
from explainer_engine.qa.cinema_gates import check_map_stability


def _write_mp4(path: Path, frames_bgr: list[np.ndarray], fps: int = 24) -> None:
    h, w = frames_bgr[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for fr in frames_bgr:
        vw.write(fr)
    vw.release()


def test_maplibre_html_enables_antialias_2x_sprites_and_zero_filltext_per_frame(tmp_path: Path) -> None:
    relief = tmp_path / "relief.png"
    cv2.imwrite(str(relief), np.full((64, 128, 3), (30, 50, 70), dtype=np.uint8))
    spec = WebGLMapSpec(
        map_id="test_map",
        title="TEST MAP",
        subtitle="Zero Jitter",
        duration_s=5.0,
        relief_bounds=(10.0, 0.0, 60.0, 45.0),
        start_camera={"center_lon": 30.0, "center_lat": 20.0, "zoom": 3.0, "pitch": 22.0, "bearing": 0.0},
        end_camera={"center_lon": 40.0, "center_lat": 30.0, "zoom": 3.5, "pitch": 22.0, "bearing": 0.0},
        sea_and_region_labels=[{"text": "MEDITERRANEAN SEA", "lon": 18.0, "lat": 35.0, "kind": "sea"}],
        markers=[{"label": "EAST AFRICA", "sublabel": "70,000 BCE", "lon": 38.0, "lat": 8.0}],
    )
    html_doc = _build_maplibre_html(spec, relief, width=1600, height=900)
    assert "antialias: true" in html_doc
    assert "buildLabelSprite" in html_doc
    assert "buildMarkerBadgeSprite" in html_doc
    assert '"line-dasharray"' not in html_doc
    # Ensure drawOverlay never calls ctx.fillText per frame
    draw_overlay_block = html_doc.split("function drawOverlay(t_s)")[1].split("window.__renderAt")[0]
    assert "fillText(" not in draw_overlay_block
    assert "drawImage(sp.canvas" in draw_overlay_block


def test_check_map_stability_passes_smooth_glide_and_fails_jittery_shimmer(tmp_path: Path) -> None:
    # Build a synthetic high-contrast map canvas (480x270) with clean features & text
    base = np.full((340, 580, 3), (34, 48, 62), dtype=np.uint8)
    for y in range(40, 300, 40):
        cv2.line(base, (20, y), (560, y), (95, 130, 160), 2, cv2.LINE_AA)
    cv2.putText(base, "OUT OF AFRICA", (140, 170), cv2.FONT_HERSHEY_SIMPLEX, 1.1, (240, 245, 250), 2, cv2.LINE_AA)
    cv2.circle(base, (260, 120), 12, (67, 155, 227), -1, cv2.LINE_AA)

    # 1. Smooth subpixel bilinear pan (0.6px/frame) -> PASS
    smooth_frames: list[np.ndarray] = []
    for i in range(36):
        dx = i * 0.6
        dy = i * 0.25
        mat = np.float32([[1.0, 0.0, -dx], [0.0, 1.0, -dy]])
        fr = cv2.warpAffine(base, mat, (480, 270), flags=cv2.INTER_LINEAR)
        smooth_frames.append(fr)
    smooth_mp4 = tmp_path / "smooth_map.mp4"
    _write_mp4(smooth_mp4, smooth_frames)
    res_ok = check_map_stability(smooth_mp4)
    assert res_ok["status"] == "PASS", res_ok

    # 2. Alternating +-2px jitter + high-freq shimmer noise -> FAIL
    rng = np.random.default_rng(123)
    jitter_frames: list[np.ndarray] = []
    for i in range(36):
        dx = i * 0.6 + (2.5 if i % 2 == 0 else -2.5)
        dy = i * 0.25 + (-2.0 if i % 2 == 0 else 2.0)
        mat = np.float32([[1.0, 0.0, -dx], [0.0, 1.0, -dy]])
        fr = cv2.warpAffine(base, mat, (480, 270), flags=cv2.INTER_NEAREST)
        shimmer = rng.integers(-18, 19, fr.shape, dtype=np.int16)
        fr = np.clip(fr.astype(np.int16) + shimmer, 0, 255).astype(np.uint8)
        jitter_frames.append(fr)
    jitter_mp4 = tmp_path / "jitter_map.mp4"
    _write_mp4(jitter_mp4, jitter_frames)
    res_bad = check_map_stability(jitter_mp4)
    assert res_bad["status"] == "FAIL", res_bad
    assert res_bad["findings"]


def _ensure_vendor_dir(monkeypatch: Any, tmp_path: Path) -> None:
    from explainer_engine.design_system import tokens

    if (tokens.DS_VENDOR_DIR / "rough.js").is_file() and (tokens.DS_VENDOR_DIR / "gsap.min.js").is_file():
        return
    stub = tmp_path / "vendor"
    stub.mkdir(parents=True, exist_ok=True)
    for fname in ("rough.js", "gsap.min.js", "DrawSVGPlugin.min.js"):
        (stub / fname).write_text("// stub for clean CI unit test\n", encoding="utf-8")
    monkeypatch.setattr(tokens, "DS_VENDOR_DIR", stub)


def test_editorial_graphics_boxless_roughjs_and_ink_filter(monkeypatch: Any, tmp_path: Path) -> None:
    from explainer_engine.design_system.tokens import resolve_vendor_js
    from explainer_engine.overlay.editorial_graphics import (
        VALID_EDITORIAL_TEMPLATES,
        EditorialGraphicSpec,
        _build_editorial_html,
    )

    _ensure_vendor_dir(monkeypatch, tmp_path)
    assert resolve_vendor_js("rough.js").is_file()
    for tmpl in sorted(VALID_EDITORIAL_TEMPLATES):
        spec = EditorialGraphicSpec(
            graphic_id=f"ed_{tmpl}",
            template=tmpl,
            title="THE FIRST SPARK",
            subtitle="Ice Age Survival",
            duration_s=3.5,
            meta={"start_val": 0, "end_val": 1200, "suffix": "°C"},
        )
        spec.validate()
        doc = _build_editorial_html(spec, width=1920, height=1080)
        assert "rough.js" in doc
        assert "feTurbulence" in doc
        assert "glass-card" not in doc


def test_drawing_explainer_builds_all_four_scenes_with_roughjs_and_gsap(monkeypatch: Any, tmp_path: Path) -> None:
    from explainer_engine.explainer.drawing_explainer import (
        VALID_EXPLAINER_SCENES,
        DrawingExplainerSpec,
        _build_explainer_html,
    )

    _ensure_vendor_dir(monkeypatch, tmp_path)
    art = tmp_path / "plate.jpg"
    cv2.imwrite(str(art), np.full((180, 320, 3), (20, 24, 30), dtype=np.uint8))
    for kind in sorted(VALID_EXPLAINER_SCENES):
        spec = DrawingExplainerSpec(
            explainer_id=f"exp_{kind}",
            scene_kind=kind,
            title="VISUAL ESSAY",
            subtitle="Documentary sketch",
            illustration_path=art,
            duration_s=8.0,
        )
        spec.validate()
        doc = _build_explainer_html(spec, width=1920, height=1080)
        assert "rough.js" in doc
        assert "DrawSVGPlugin" in doc
        assert "feTurbulence" in doc
        assert "data:image/jpeg;base64," in doc


def test_cinematic_score_rejects_short_loops_and_applies_silence_drop(tmp_path: Path) -> None:
    import pytest
    import soundfile as sf

    from explainer_engine.audio.cinematic_score import (
        apply_cinema_silence_drops,
        validate_music_stem,
    )

    sr = 48000
    # 6s short SFX loop MUST be rejected by >=45s hard gate!
    short_wav = tmp_path / "short_loop.wav"
    sf.write(str(short_wav), np.zeros((sr * 6, 2), dtype=np.float32), sr)
    with pytest.raises(ValueError, match="45.0s"):
        validate_music_stem(short_wav)

    # Synthetic placeholder name MUST be rejected even if long
    synth_wav = tmp_path / "synth_pad_60s.wav"
    sf.write(str(synth_wav), np.zeros((sr * 50, 2), dtype=np.float32), sr)
    with pytest.raises(ValueError, match="Forbidden synthetic"):
        validate_music_stem(synth_wav)

    # Real >=45s stem passes
    long_wav = tmp_path / "real_cello_adagio.wav"
    sf.write(str(long_wav), np.zeros((sr * 48, 2), dtype=np.float32), sr)
    assert validate_music_stem(long_wav)["status"] == "PASS"

    # 0.4s Cinema Silence Drop carves energy cleanly at t=2.0..2.4s
    buf = np.full((sr * 4, 2), 0.5, dtype=np.float32)
    dropped = apply_cinema_silence_drops(buf, sr, [{"time_s": 2.0, "duration_s": 0.40, "depth_db": -36.0}])
    pre_rms = float(np.sqrt(np.mean(dropped[int(1.2 * sr) : int(1.6 * sr)] ** 2)))
    mid_rms = float(np.sqrt(np.mean(dropped[int(2.1 * sr) : int(2.3 * sr)] ** 2)))
    assert pre_rms > 0.45
    assert mid_rms < 0.02


def test_ltx_audio_guide_transient_detection_and_6layer_mix(tmp_path: Path) -> None:
    import soundfile as sf

    from explainer_engine.audio.broadcast_cinema_mix import mix_broadcast_cinema_audio
    from explainer_engine.audio.ltx_audio_guide import (
        analyze_audio_transients,
        snap_sfx_events_to_ltx_onsets,
    )

    sr = 48000
    t = np.linspace(0.0, 4.0, sr * 4, endpoint=False, dtype=np.float32)
    sig = 0.004 * np.sin(2 * np.pi * 120 * t)
    # Inject a crisp flint-strike transient at t=1.50s
    idx = int(1.50 * sr)
    sig[idx : idx + int(0.06 * sr)] += 0.45 * np.exp(-np.linspace(0, 8, int(0.06 * sr), dtype=np.float32))
    clip_wav = tmp_path / "flint_native.wav"
    sf.write(str(clip_wav), np.stack([sig, sig], axis=1), sr)

    analysis = analyze_audio_transients(clip_wav)
    assert analysis["onsets_s"], "Expected flint transient onset detected"
    assert any(abs(o - 1.50) <= 0.06 for o in analysis["onsets_s"]), analysis["onsets_s"]

    guide = {"timeline_onsets": [{"shot_id": "s1", "time_s": 1.50}]}
    snapped = snap_sfx_events_to_ltx_onsets([{"time_s": 1.62, "wav_path": "hit.wav"}], guide)
    assert snapped[0]["ltx_snapped"] is True
    assert abs(snapped[0]["time_s"] - 1.50) <= 0.001

    # Verify 6-layer mix completes cleanly at -14.0 LUFS / <= -1.2 dBTP with LTX diegetic stem & silence drop
    voice = (0.3 * np.sin(2 * np.pi * 200 * t)).astype(np.float32)
    v_wav = tmp_path / "voice.wav"
    sf.write(str(v_wav), voice, sr)
    rep = mix_broadcast_cinema_audio(
        total_duration_s=4.0,
        voice_wav=v_wav,
        music_acts=[],
        scene_ambiences=[],
        sfx_events=[],
        ltx_diegetic_wav=clip_wav,
        silence_drops=[{"time_s": 2.5, "duration_s": 0.4}],
        out_wav=tmp_path / "mix6.wav",
        target_lufs=-14.0,
        true_peak_ceiling_db=-1.2,
    )
    assert rep["layers"] == 6
    assert rep["ltx_diegetic_layer_active"] is True
    assert rep["silence_drop_count"] == 1
    assert -14.4 <= rep["integrated_lufs"] <= -13.6
    assert rep["true_peak_dbtp"] <= -1.1


def test_exact_frame_handoff_plan_and_no_jump_cuts_gate(tmp_path: Path) -> None:
    from explainer_engine.qa.cinema_gates import check_no_jump_cuts
    from explainer_engine.videolane.multishot_scene_director import validate_chained_handoff_plan

    # 1. Plan validator catches early-trimmed parent (v3 bug!) and passes exact F_ext - 1
    bad_plan = [
        {"shot_id": "s1", "raw_dur_s": 5.708, "clip_start_s": 0.0, "played_dur_s": 3.0},
        {"shot_id": "s2", "chained_from": "s1", "extract_time_s": 5.458, "clip_start_s": 0.0, "played_dur_s": 4.5},
    ]
    res_plan_bad = validate_chained_handoff_plan(bad_plan)
    assert res_plan_bad["status"] == "FAIL"
    assert "Chained handoff violation" in res_plan_bad["findings"][0]

    good_plan = [
        {"shot_id": "s1", "raw_dur_s": 5.708, "clip_start_s": 0.0, "played_dur_s": 5.417, "scene_group": "cave", "shot_scale": "wide"},
        {"shot_id": "s2", "chained_from": "s1", "extract_time_s": 5.458, "clip_start_s": 0.0, "played_dur_s": 4.5, "scene_group": "cave", "shot_scale": "wide"},
        {"shot_id": "s3", "scene_group": "cave", "shot_scale": "close_up", "camera_angle_delta_deg": 45.0, "played_dur_s": 4.0},
    ]
    res_plan_ok = validate_chained_handoff_plan(good_plan)
    assert res_plan_ok["status"] == "PASS", res_plan_ok

    # 2. Pixel-level check_no_jump_cuts catches broken chained handoff + same-framing jump cut
    bg = np.full((180, 320, 3), (30, 42, 55), dtype=np.uint8)
    for y in range(20, 170, 20):
        cv2.line(bg, (0, y), (320, y), (70, 90, 110), 2)
    f_a = bg.copy()
    cv2.circle(f_a, (100, 90), 34, (220, 180, 120), -1)
    f_b_seamless = f_a.copy()
    cv2.circle(f_b_seamless, (101, 90), 34, (220, 180, 120), -1)
    f_b_jump = bg.copy()
    cv2.circle(f_b_jump, (235, 90), 34, (220, 180, 120), -1)  # same background, subject teleports -> jump cut!
    f_c_new_angle = np.full((180, 320, 3), (185, 110, 40), dtype=np.uint8)
    cv2.rectangle(f_c_new_angle, (60, 30), (260, 150), (245, 220, 150), -1)

    # Seamless chained handoff + genuine angle change -> PASS
    vid_ok = tmp_path / "seamless.mp4"
    _write_mp4(vid_ok, [f_a] * 24 + [f_b_seamless] * 24 + [f_c_new_angle] * 24, fps=24)
    shots_ok = [
        {"shot_id": "s1", "start_s": 0.0, "end_s": 1.0, "scene_group": "cave", "shot_scale": "medium"},
        {"shot_id": "s2", "start_s": 1.0, "end_s": 2.0, "chained_from": "s1", "scene_group": "cave", "shot_scale": "medium"},
        {"shot_id": "s3", "start_s": 2.0, "end_s": 3.0, "scene_group": "cave", "shot_scale": "close_up", "camera_angle_delta_deg": 45},
    ]
    r_ok = check_no_jump_cuts(vid_ok, shots_ok)
    assert r_ok["status"] == "PASS", r_ok

    # Broken chained handoff (SSIM < 0.88) -> FAIL
    vid_broken_chain = tmp_path / "broken_chain.mp4"
    _write_mp4(vid_broken_chain, [f_a] * 24 + [f_b_jump] * 24, fps=24)
    r_bc = check_no_jump_cuts(
        vid_broken_chain,
        [
            {"shot_id": "s1", "start_s": 0.0, "end_s": 1.0},
            {"shot_id": "s2", "start_s": 1.0, "end_s": 2.0, "chained_from": "s1"},
        ],
    )
    assert r_bc["status"] == "FAIL", r_bc
    assert "Broken chained handoff" in r_bc["findings"][0]

    # Unchained same-environment jump cut (0.55 < SSIM < 0.88 & high layout corr) -> FAIL
    r_jc = check_no_jump_cuts(
        vid_broken_chain,
        [
            {"shot_id": "s1", "start_s": 0.0, "end_s": 1.0, "scene_group": "cave", "shot_scale": "medium"},
            {"shot_id": "s2", "start_s": 1.0, "end_s": 2.0, "scene_group": "cave", "shot_scale": "medium"},
        ],
    )
    assert r_jc["status"] == "FAIL", r_jc
    assert "Jump cut detected" in r_jc["findings"][0]


def test_docudrama_70_30_balance_and_dramatic_narration_exemption() -> None:
    from explainer_engine.qa.cinema_gates import (
        check_docudrama_70_30_balance,
        check_narration_pacing_gaps,
    )

    # True 70/30 layout: 300s total, Scene A = 50s (38s silent), Scene B = 42s (30s silent) -> 30.7% dramatic
    shots = [
        {"shot_id": "w1", "kind": "ltx", "start_s": 0.0, "end_s": 100.0},
        {"shot_id": "da_1", "kind": "ltx", "start_s": 100.0, "end_s": 125.0, "is_dramatic_scene": True, "dramatic_scene_id": "scene_a"},
        {"shot_id": "da_2", "kind": "ltx", "start_s": 125.0, "end_s": 150.0, "is_dramatic_scene": True, "dramatic_scene_id": "scene_a"},
        {"shot_id": "w2", "kind": "explainer", "start_s": 150.0, "end_s": 210.0},
        {"shot_id": "db_1", "kind": "ltx", "start_s": 210.0, "end_s": 252.0, "is_dramatic_scene": True, "dramatic_scene_id": "scene_b"},
        {"shot_id": "w3", "kind": "ltx", "start_s": 252.0, "end_s": 300.0},
    ]
    utterances = [
        {"start_s": 0.5, "end_s": 104.0},
        # 38s narrator-free dramatic acting inside Scene A (104 -> 142)
        {"start_s": 142.0, "end_s": 145.0},
        {"start_s": 147.0, "end_s": 214.0},
        # 32s narrator-free dramatic acting inside Scene B (214 -> 246)
        {"start_s": 246.0, "end_s": 298.0},
    ]
    bal = check_docudrama_70_30_balance(shots, utterances)
    assert bal["status"] == "PASS", bal
    assert 0.25 <= bal["dramatic_ratio"] <= 0.38
    assert bal["qualifying_scene_count"] == 2

    # Narration gap gate respects the two dramatic scene windows
    pac = check_narration_pacing_gaps(
        utterances,
        total_duration_s=300.0,
        dramatic_scene_windows=[(100.0, 150.0), (210.0, 252.0)],
    )
    assert pac["status"] == "PASS", pac

    # 98% wall-to-wall narration montage (v3 defect) MUST FAIL
    utterances_wall = [{"start_s": 0.5, "end_s": 298.0}]
    bal_fail = check_docudrama_70_30_balance(shots, utterances_wall)
    assert bal_fail["status"] == "FAIL", bal_fail



