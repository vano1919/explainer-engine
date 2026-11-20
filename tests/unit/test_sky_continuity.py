"""Unit tests for explainer_engine.qa.sky_continuity."""

from pathlib import Path

import numpy as np
import pytest

from explainer_engine.qa.sky_continuity import analyse_window_flows, sky_continuity

def test_steady_drift_passes() -> None:
    steady = [0.8, 0.9, 0.85, 0.8, 0.9, 0.8]
    res = analyse_window_flows(steady, [0.0] * 6)
    assert res["ok"] is True
    assert res["windows"] == 6
    assert res["reversed_share"] == pytest.approx(0.0)
    assert res["max_jump_ratio"] <= 3.0
    assert isinstance(res["reason"], str)

def test_pingpong_motion_fails() -> None:
    pingpong = [0.8, -0.8, 0.8, -0.8, 0.8, -0.8]
    res = analyse_window_flows(pingpong, [0.0] * 6)
    assert res["ok"] is False
    assert res["reversed_share"] > 0.10

def test_loop_seam_spike_fails() -> None:
    seam = [0.5, 0.5, 0.5, 4.0, 0.5, 0.5]
    res = analyse_window_flows(seam, [0.0] * 6)
    assert res["ok"] is False
    assert res["max_jump_ratio"] == pytest.approx(8.0)

def test_reversed_share_boundary_at_limit_and_just_above() -> None:
    # 10 counted windows with max_reversed_share=0.10:
    # 1 reversed window -> 0.10 (passes); 2 reversed windows -> 0.20 (fails)
    at_limit = [0.8] * 9 + [-0.8]
    res_ok = analyse_window_flows(at_limit, [0.0] * 10, max_reversed_share=0.10)
    assert res_ok["reversed_share"] == pytest.approx(0.10)
    assert res_ok["ok"] is True

    just_above = [0.8] * 8 + [-0.8] * 2
    res_fail = analyse_window_flows(just_above, [0.0] * 10, max_reversed_share=0.10)
    assert res_fail["reversed_share"] == pytest.approx(0.20)
    assert res_fail["ok"] is False

def test_dominant_axis_vertical() -> None:
    # Horizontal jitter is small and flips signs, while vertical drift is steady and dominant
    mean_dx = [0.1, -0.1, 0.08, -0.09, 0.1, -0.08]
    mean_dy = [-1.2, -1.1, -1.25, -1.15, -1.2, -1.18]
    res = analyse_window_flows(mean_dx, mean_dy)
    assert res["ok"] is True
    assert res["reversed_share"] == pytest.approx(0.0)

def test_all_windows_under_min_speed_fails() -> None:
    res = analyse_window_flows([0.01, -0.02, 0.0, 0.03, -0.01], [0.01, 0.0, -0.02, 0.01, 0.0], min_speed=0.05)
    assert res["ok"] is False
    assert "sky does not move" in res["reason"].lower()

def test_fewer_than_four_windows_not_run() -> None:
    res = analyse_window_flows([0.8, 0.85, 0.9], [0.0, 0.0, 0.0])
    assert res["ok"] is None
    assert "NOT_RUN" in res["reason"]
    assert "clip too short" in res["reason"]

def test_slow_windows_excluded_from_sign_flip_count() -> None:
    res = analyse_window_flows([0.06, 0.06, -0.03, 0.06, 0.06, -0.04], [0.0] * 6)
    assert res["ok"] is True
    assert res["reversed_share"] == pytest.approx(0.0)

def test_median_sign_used_instead_of_first_window() -> None:
    res = analyse_window_flows([-0.8] + [0.8] * 9, [0.0] * 10)
    assert res["ok"] is True
    assert res["reversed_share"] == pytest.approx(0.10)

def test_max_jump_ratio_parameter_respected() -> None:
    res_ok = analyse_window_flows([0.5, 0.5, 0.5, 4.0, 0.5, 0.5], [0.0] * 6, max_jump_ratio=10.0)
    assert res_ok["ok"] is True

    res_fail = analyse_window_flows([0.5, 0.5, 1.25, 1.25, 0.5, 0.5], [0.0] * 6, max_jump_ratio=2.0)
    assert res_fail["ok"] is False

def test_max_reversed_share_parameter_respected() -> None:
    res_ok = analyse_window_flows([0.8] * 8 + [-0.8] * 2, [0.0] * 10, max_reversed_share=0.30)
    assert res_ok["ok"] is True

    res_fail = analyse_window_flows([0.8] * 9 + [-0.8], [0.0] * 10, max_reversed_share=0.05)
    assert res_fail["ok"] is False

@pytest.mark.parametrize(
    ("mean_dx", "mean_dy"),
    [
        ([-0.8] * 6, [0.0] * 6),
        ([0.0] * 6, [0.8] * 6),
        ([0.0] * 6, [-0.8] * 6),
    ],
)
def test_steady_drift_any_cardinal_direction_passes(mean_dx: list[float], mean_dy: list[float]) -> None:
    res = analyse_window_flows(mean_dx, mean_dy)
    assert res["ok"] is True
    assert res["reversed_share"] == pytest.approx(0.0)

def _write_sky_shift_video(
    path: Path,
    shifts_x: list[int],
    width: int = 240,
    height: int = 160,
    fps: int = 8,
    move_ground_instead: bool = False,
) -> None:
    cv2 = pytest.importorskip("cv2")
    rng = np.random.default_rng(42)

    # Smooth low-frequency random field so Farneback optical flow tracks cleanly
    coarse = rng.integers(30, 225, size=(height // 8, width // 8), dtype=np.uint8)
    tex = cv2.resize(coarse, (width, height), interpolation=cv2.INTER_CUBIC)
    static_half = np.full((height // 2, width), 40, dtype=np.uint8)

    fourcc = cv2.VideoWriter_fourcc(*"MJPG")
    writer = cv2.VideoWriter(str(path), fourcc, float(fps), (width, height), isColor=True)
    assert writer.isOpened(), "Failed to open cv2.VideoWriter"

    try:
        for dx in shifts_x:
            shifted = np.roll(tex, shift=dx, axis=1)
            if move_ground_instead:
                frame_gray = np.vstack([static_half, shifted[height // 2 :, :]])
            else:
                frame_gray = np.vstack([shifted[: height // 2, :], static_half])
            frame_bgr = cv2.cvtColor(frame_gray, cv2.COLOR_GRAY2BGR)
            writer.write(frame_bgr)
    finally:
        writer.release()

def test_sky_continuity_steady_drift_video(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    # 3.0 seconds at 8 fps = 24 frames (~6 windows of 0.5 s), shifting +3 px/frame
    shifts = [i * 3 for i in range(24)]
    video_path = tmp_path / "steady_sky.avi"
    _write_sky_shift_video(video_path, shifts, width=width, height=height, fps=fps)

    sky_mask = np.zeros((height, width), dtype=bool)
    sky_mask[: height // 2, :] = True

    res = sky_continuity(str(video_path), sky_mask, window_s=0.5, pair_gap_s=0.25)
    assert res["ok"] is True

def test_sky_continuity_pingpong_video(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    # 3.0 seconds at 8 fps = 24 frames: shift right for 1.5s, then shift left for 1.5s
    shifts = [i * 3 for i in range(12)] + [(11 - i) * 3 for i in range(12)]
    video_path = tmp_path / "pingpong_sky.avi"
    _write_sky_shift_video(video_path, shifts, width=width, height=height, fps=fps)

    sky_mask = np.zeros((height, width), dtype=bool)
    sky_mask[: height // 2, :] = True

    res = sky_continuity(str(video_path), sky_mask, window_s=0.5, pair_gap_s=0.25)
    assert res["ok"] is False

def test_sky_continuity_missing_file_not_run(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    missing = tmp_path / "does_not_exist.avi"
    sky_mask = np.ones((160, 240), dtype=bool)

    res = sky_continuity(str(missing), sky_mask)
    assert res["ok"] is None
    assert res["reason"].startswith("NOT_RUN:")

def test_sky_continuity_respects_sky_mask_over_ground(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    shifts = [i * 3 for i in range(24)]

    # Case 1: sky moves right, but mask selects the static bottom ground half
    steady_sky_path = tmp_path / "steady_sky_masked_ground.avi"
    _write_sky_shift_video(steady_sky_path, shifts, width=width, height=height, fps=fps)
    # Mask the bottom quarter only: Farneback smears flow a few pixels across the moving/static boundary,
    # so a mask touching the boundary half would read a small non-zero flow from the sky (not a defect).
    bottom_mask = np.zeros((height, width), dtype=bool)
    bottom_mask[3 * height // 4 :, :] = True

    res_static_mask = sky_continuity(str(steady_sky_path), bottom_mask, window_s=0.5, pair_gap_s=0.25)
    assert res_static_mask["ok"] is False
    assert "sky does not move" in res_static_mask["reason"].lower()

    # Case 2: sky half is static, ground half moves steadily, mask selects top sky half
    moving_ground_path = tmp_path / "static_sky_moving_ground.avi"
    _write_sky_shift_video(
        moving_ground_path, shifts, width=width, height=height, fps=fps, move_ground_instead=True
    )
    top_mask = np.zeros((height, width), dtype=bool)
    top_mask[: height // 4, :] = True

    res_static_sky = sky_continuity(str(moving_ground_path), top_mask, window_s=0.5, pair_gap_s=0.25)
    assert res_static_sky["ok"] is False
    assert "sky does not move" in res_static_sky["reason"].lower()

def test_sky_continuity_float_mask_matches_bool_mask(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    shifts = [i * 3 for i in range(24)]
    video_path = tmp_path / "float_mask_sky.avi"
    _write_sky_shift_video(video_path, shifts, width=width, height=height, fps=fps)

    bool_mask = np.zeros((height, width), dtype=bool)
    bool_mask[: height // 2, :] = True
    float_mask = np.where(bool_mask, 1.0, 0.0).astype(np.float32)

    res_bool = sky_continuity(str(video_path), bool_mask, window_s=0.5, pair_gap_s=0.25)
    res_float = sky_continuity(str(video_path), float_mask, window_s=0.5, pair_gap_s=0.25)
    assert res_bool["ok"] is True
    assert res_float["ok"] == res_bool["ok"]
    assert res_float["windows"] == res_bool["windows"]
    assert res_float["reversed_share"] == pytest.approx(res_bool["reversed_share"])

def test_sky_continuity_loop_seam_video_fails(tmp_path: Path) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    # Texture shifts right for 12 frames, then snaps back to start and repeats
    shifts = [i * 3 for i in range(12)] + [i * 3 for i in range(12)]
    video_path = tmp_path / "loop_seam_sky.avi"
    _write_sky_shift_video(video_path, shifts, width=width, height=height, fps=fps)

    sky_mask = np.zeros((height, width), dtype=bool)
    sky_mask[: height // 2, :] = True

    res = sky_continuity(str(video_path), sky_mask, window_s=0.5, pair_gap_s=0.25)
    assert res["ok"] is False

@pytest.mark.parametrize("pair_gap_s", [0.125, 0.25])
def test_sky_continuity_pair_gap_variants(tmp_path: Path, pair_gap_s: float) -> None:
    pytest.importorskip("cv2")
    width, height, fps = 240, 160, 8
    steady_shifts = [i * 3 for i in range(24)]
    pingpong_shifts = [i * 3 for i in range(12)] + [(11 - i) * 3 for i in range(12)]

    steady_path = tmp_path / f"steady_gap_{pair_gap_s}.avi"
    pingpong_path = tmp_path / f"pingpong_gap_{pair_gap_s}.avi"
    _write_sky_shift_video(steady_path, steady_shifts, width=width, height=height, fps=fps)
    _write_sky_shift_video(pingpong_path, pingpong_shifts, width=width, height=height, fps=fps)

    sky_mask = np.zeros((height, width), dtype=bool)
    sky_mask[: height // 2, :] = True

    res_steady = sky_continuity(str(steady_path), sky_mask, window_s=0.5, pair_gap_s=pair_gap_s)
    res_pingpong = sky_continuity(str(pingpong_path), sky_mask, window_s=0.5, pair_gap_s=pair_gap_s)
    assert res_steady["ok"] is True
    assert res_pingpong["ok"] is False
