"""Unit tests for v5.0 Loop 1: Blender 3D Multi-Angle Set Blocking, Hybrid Continuity & Zero-Stretch QA Gates."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from explainer_engine.qa.cinema_gates import (
    check_no_transition_stretch_or_zoom_jump,
    check_same_scene_environment_continuity,
)
from explainer_engine.scene3d.blender_set_blocker import (
    ROMAN_SET_PRESETS,
    build_blender_set_script,
    plan_set_cameras,
    validate_set_rig_manifest,
)
from explainer_engine.videolane.multishot_scene_director import (
    plan_hybrid_scene_continuity,
    validate_zero_pre_stitch_zoom,
)


def _write_mp4(path: Path, frames_bgr: list[np.ndarray], fps: int = 24) -> None:
    h, w = frames_bgr[0].shape[:2]
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    vw = cv2.VideoWriter(str(path), fourcc, fps, (w, h))
    for fr in frames_bgr:
        vw.write(fr)
    vw.release()


def test_blender_set_blocker_presets_and_script_generation(tmp_path: Path) -> None:
    for preset in sorted(ROMAN_SET_PRESETS):
        cams = plan_set_cameras(preset)
        assert len(cams) >= 5
        script = build_blender_set_script(preset, tmp_path / preset, width=640, height=360, cycles_samples=4)
        assert "use_pass_mist = True" in script
        assert "use_persistent_data = True" in script
        assert preset in script

    # Manifest validation catches missing files and passes complete angle set
    angles = []
    for i in range(4):
        bp = tmp_path / f"a{i}_beauty.png"
        dp = tmp_path / f"a{i}_depth.png"
        bp.write_bytes(b"png")
        dp.write_bytes(b"png")
        angles.append({"angle_id": f"a{i}", "beauty_path": str(bp), "depth_path": str(dp)})
    assert validate_set_rig_manifest({"set_name": "test", "angles": angles})["status"] == "PASS"
    assert validate_set_rig_manifest({"set_name": "test", "angles": angles[:2]})["status"] == "FAIL"


def test_zero_pre_stitch_zoom_and_hybrid_scene_continuity() -> None:
    clean_shots = [
        {"shot_id": "s1", "scene_id": "atrium", "shot_scale": "wide"},
        {"shot_id": "s2", "scene_id": "atrium", "shot_scale": "medium"},
        {"shot_id": "s3", "scene_id": "atrium", "chained_from": "s2"},
    ]
    assert validate_zero_pre_stitch_zoom(clean_shots)["status"] == "PASS"

    bad_zoom = [
        {"shot_id": "s1", "zoom_factor": 1.12},
        {"shot_id": "s2", "vf": "scale=1920:1080,zoompan=z='zoom+0.002'"},
    ]
    res_bad = validate_zero_pre_stitch_zoom(bad_zoom)
    assert res_bad["status"] == "FAIL"
    assert len(res_bad["findings"]) >= 2

    manifest = {"angles": [{"angle_id": f"c{i}"} for i in range(5)]}
    plan_ok = plan_hybrid_scene_continuity("atrium", "hybrid_set_and_chain", clean_shots, blender_set_manifest=manifest)
    assert plan_ok["status"] == "PASS"

    # Reject single-shot LTX slideshow
    with pytest.raises(ValueError, match=">= 2 connected shots"):
        plan_hybrid_scene_continuity("solo", "continuous_ltx_chain", [{"shot_id": "only_one"}])

    # Reject chain depth > 3
    too_deep = [
        {"shot_id": "c1"},
        {"shot_id": "c2", "chained_from": "c1"},
        {"shot_id": "c3", "chained_from": "c2"},
        {"shot_id": "c4", "chained_from": "c3"},
        {"shot_id": "c5", "chained_from": "c4"},
    ]
    res_deep = plan_hybrid_scene_continuity("walk", "continuous_ltx_chain", too_deep)
    assert res_deep["status"] == "FAIL"


def test_same_scene_environment_continuity_passes_cohesive_and_fails_disconnected(tmp_path: Path) -> None:
    # Build two cohesive shots in the SAME warm Roman terracotta atrium (different angle/foreground)
    def make_atrium_frame(shift_x: int, fg_x: int) -> np.ndarray:
        img = np.full((180, 320, 3), (42, 68, 128), dtype=np.uint8)  # warm terracotta-ochre BGR
        # Vertical travertine columns in background
        for cx in range(30 + shift_x, 300, 70):
            cv2.rectangle(img, (cx, 10), (cx + 22, 165), (140, 165, 185), -1)
        # Warm stone floor
        cv2.rectangle(img, (0, 130), (320, 180), (92, 118, 145), -1)
        # Foreground character silhouette (different angle/position)
        cv2.circle(img, (fg_x, 82), 18, (110, 120, 140), -1)
        cv2.rectangle(img, (fg_x - 24, 100), (fg_x + 24, 175), (165, 172, 182), -1)
        return img

    cohesive_frames = [make_atrium_frame(0, 110) for _ in range(24)] + [make_atrium_frame(20, 210) for _ in range(24)]
    cohesive_mp4 = tmp_path / "cohesive.mp4"
    _write_mp4(cohesive_mp4, cohesive_frames)
    shots = [
        {"shot_id": "a1", "scene_id": "atrium", "start_s": 0.0, "end_s": 1.0},
        {"shot_id": "a2", "scene_id": "atrium", "start_s": 1.0, "end_s": 2.0},
    ]
    ok = check_same_scene_environment_continuity(cohesive_mp4, shots)
    assert ok["status"] == "PASS", ok
    assert ok["median_env_similarity"] >= 0.78

    # Now swap shot 2 to a completely disconnected icy-blue outdoor glacier room -> FAIL
    glacier = np.full((180, 320, 3), (215, 180, 105), dtype=np.uint8)  # icy cyan-blue BGR
    cv2.line(glacier, (0, 60), (320, 120), (245, 240, 230), 6)
    cv2.line(glacier, (0, 110), (320, 70), (200, 210, 220), 4)
    broken_frames = [make_atrium_frame(0, 110) for _ in range(24)] + [glacier for _ in range(24)]
    broken_mp4 = tmp_path / "disconnected.mp4"
    _write_mp4(broken_mp4, broken_frames)
    bad = check_same_scene_environment_continuity(broken_mp4, shots)
    assert bad["status"] == "FAIL", bad


def test_no_transition_stretch_or_zoom_jump_catches_zoom_and_stretch(tmp_path: Path) -> None:
    # Textured synthetic canvas with rich corner features
    rng = np.random.default_rng(7)
    base = np.full((260, 420, 3), (60, 75, 95), dtype=np.uint8)
    for _ in range(180):
        x, y = int(rng.integers(15, 405)), int(rng.integers(15, 245))
        c = tuple(int(v) for v in rng.integers(110, 245, size=3))
        cv2.circle(base, (x, y), int(rng.integers(3, 9)), c, -1, cv2.LINE_AA)

    def crop_center(img: np.ndarray, sx: float = 1.0, sy: float = 1.0, dx: float = 0.0) -> np.ndarray:
        h, w = img.shape[:2]
        m = np.float32([[sx, 0.0, (1.0 - sx) * w * 0.5 + dx], [0.0, sy, (1.0 - sy) * h * 0.5]])
        warped = cv2.warpAffine(img, m, (w, h), flags=cv2.INTER_LINEAR)
        return warped[40:220, 50:370]  # 320x180

    # 1. Clean chained cut with continuous slight pan (0 stretch, 0 zoom jump) -> PASS
    clean_frames = [crop_center(base, 1.0, 1.0, dx=i * 0.4) for i in range(48)]
    clean_mp4 = tmp_path / "clean_chain.mp4"
    _write_mp4(clean_mp4, clean_frames)
    windows = [
        {"shot_id": "s1", "start_s": 0.0, "end_s": 1.0},
        {"shot_id": "s2", "chained_from": "s1", "start_s": 1.0, "end_s": 2.0},
    ]
    res_ok = check_no_transition_stretch_or_zoom_jump(clean_mp4, windows)
    assert res_ok["status"] == "PASS", res_ok

    # 2. Chained cut with sudden 1.15x zoom jump at boundary -> FAIL
    jump_frames = [crop_center(base, 1.0, 1.0) for _ in range(24)] + [crop_center(base, 1.16, 1.16) for _ in range(24)]
    jump_mp4 = tmp_path / "zoom_jump.mp4"
    _write_mp4(jump_mp4, jump_frames)
    res_jump = check_no_transition_stretch_or_zoom_jump(jump_mp4, windows)
    assert res_jump["status"] == "FAIL", res_jump

    # 3. Chained cut with horizontal aspect stretch (sx=1.14, sy=1.0) -> FAIL
    stretch_frames = [crop_center(base, 1.0, 1.0) for _ in range(24)] + [crop_center(base, 1.14, 1.0) for _ in range(24)]
    stretch_mp4 = tmp_path / "aspect_stretch.mp4"
    _write_mp4(stretch_mp4, stretch_frames)
    res_stretch = check_no_transition_stretch_or_zoom_jump(stretch_mp4, windows)
    assert res_stretch["status"] == "FAIL", res_stretch


def test_eyeline_180_rule_and_axis_locked_coverage_plates(tmp_path: Path) -> None:
    from explainer_engine.videolane.multishot_scene_director import (
        extract_axis_locked_coverage_plates,
        validate_eyeline_180_rule,
    )

    good = [
        {"shot_id": "s1", "scene_id": "atrium", "focus_subject": "calpurnia", "facing_dir": "left"},
        {"shot_id": "s2", "scene_id": "atrium", "focus_subject": "caesar", "facing_dir": "right"},
        {"shot_id": "s3", "scene_id": "atrium", "focus_subject": "calpurnia", "facing_dir": "left"},
    ]
    assert validate_eyeline_180_rule(good)["status"] == "PASS"

    bad = [
        {"shot_id": "s1", "scene_id": "atrium", "focus_subject": "calpurnia", "facing_dir": "left"},
        {"shot_id": "s2", "scene_id": "atrium", "focus_subject": "caesar", "facing_dir": "left"},
    ]
    assert validate_eyeline_180_rule(bad)["status"] == "FAIL"

    master = tmp_path / "wide.png"
    cv2.imwrite(str(master), np.full((720, 1280, 3), (60, 80, 120), dtype=np.uint8))
    plates = extract_axis_locked_coverage_plates(
        master,
        [
            {"shot_id": "left_actor", "cx": 0.35, "cy": 0.5, "rel_w": 0.45, "focus_subject": "caesar", "facing_dir": "right"},
            {"shot_id": "right_actor", "cx": 0.75, "cy": 0.5, "rel_w": 0.45, "focus_subject": "calpurnia", "facing_dir": "left"},
        ],
        tmp_path / "plates",
        allow_destructive_crop=True,
    )
    assert Path(plates["left_actor"]["path"]).is_file()
    assert Path(plates["right_actor"]["path"]).is_file()

