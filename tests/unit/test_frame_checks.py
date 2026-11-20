"""Unit tests for explainer_engine.qa.frame_checks."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from explainer_engine.qa.frame_checks import (
    border_defects,
    frame_integrity,
    head_box_defects,
)

FRAME_H = 704
FRAME_W = 1280
BORDER_PX = 6

def _textured_frame(seed: int = 0, height: int = FRAME_H, width: int = FRAME_W) -> np.ndarray:
    """Create a deterministic high-contrast random-texture BGR uint8 frame."""
    rng = np.random.default_rng(seed)
    return rng.integers(40, 220, size=(height, width, 3), dtype=np.uint8)

def _write_lossless_avi(path: Path, frames: list[np.ndarray], fps: float = 24.0) -> Path:
    """Write BGR uint8 frames losslessly using FFV1 or HFYU in .avi, skipping if unavailable."""
    cv2 = pytest.importorskip("cv2")
    assert frames, "At least one frame is required to write a video"
    height, width = frames[0].shape[:2]
    avi_path = path.with_suffix(".avi")

    writer = None
    for fourcc_str in ("FFV1", "HFYU"):
        fourcc = cv2.VideoWriter_fourcc(*fourcc_str)
        candidate = cv2.VideoWriter(str(avi_path), fourcc, fps, (width, height))
        if candidate.isOpened():
            writer = candidate
            break
        candidate.release()

    if writer is None:
        pytest.skip("Neither FFV1 nor HFYU lossless codec available in test environment")

    for frame in frames:
        writer.write(frame)
    writer.release()
    assert avi_path.exists() and avi_path.stat().st_size > 0
    return avi_path

class TestBorderDefects:
    """Tests for border_defects()."""

    def test_intact_random_texture_frame_returns_empty(self) -> None:
        frame = _textured_frame(seed=0)
        assert border_defects(frame, border_px=BORDER_PX) == []

    @pytest.mark.parametrize("edge", ["top", "bottom", "left", "right"])
    def test_black_border_detected_on_each_edge(self, edge: str) -> None:
        frame = _textured_frame(seed=42)
        if edge == "top":
            frame[:BORDER_PX, :] = 0
        elif edge == "bottom":
            frame[-BORDER_PX:, :] = 0
        elif edge == "left":
            frame[:, :BORDER_PX] = 0
        elif edge == "right":
            frame[:, -BORDER_PX:] = 0

        defects = border_defects(frame, border_px=BORDER_PX)
        assert defects == [f"black:{edge}"]

    def test_near_black_low_variance_border_detected(self) -> None:
        frame = _textured_frame(seed=7)
        rng = np.random.default_rng(8)
        frame[:, :BORDER_PX] = rng.integers(0, 6, size=(FRAME_H, BORDER_PX, 3), dtype=np.uint8)
        assert border_defects(frame, border_px=BORDER_PX) == ["black:left"]

    def test_black_border_mean_threshold_rejects_dark_non_black_band(self) -> None:
        # Band mean 20 (>= 8) but low std (~2.6 < 3), non-constant inward (so it is not a smear either).
        # The three channels are equal so the result does not depend on the grey conversion.
        frame = _textured_frame(seed=11)
        rng = np.random.default_rng(15)
        noise = rng.integers(16, 25, size=(FRAME_H, BORDER_PX, 1), dtype=np.uint8)
        frame[:, :BORDER_PX] = np.broadcast_to(noise, (FRAME_H, BORDER_PX, 3))
        assert border_defects(frame, border_px=BORDER_PX) == []

    def test_black_border_std_threshold_rejects_high_std_and_accepts_low_std(self) -> None:
        # 80% zeros and 20% 30s -> mean = 6.0 (< 8), std = 12.0 (>= 3) -> not black defect
        frame_high_std = _textured_frame(seed=12)
        # random per-pixel mask (same in all channels) so the band also changes inward and is not a smear
        rng_hi = np.random.default_rng(16)
        mask = rng_hi.random((FRAME_H, BORDER_PX, 1)) < 0.2
        band = np.where(mask, 30, 0).astype(np.uint8)
        frame_high_std[:, :BORDER_PX] = np.broadcast_to(band, (FRAME_H, BORDER_PX, 3))
        assert border_defects(frame_high_std, border_px=BORDER_PX) == []

        # Uniform noise 0..8 -> mean ~ 4.0 (< 8), std ~ 2.58 (< 3) -> black:left
        frame_low_std = _textured_frame(seed=13)
        rng = np.random.default_rng(14)
        noise_lo = rng.integers(0, 9, size=(FRAME_H, BORDER_PX, 1), dtype=np.uint8)
        frame_low_std[:, :BORDER_PX] = np.broadcast_to(noise_lo, (FRAME_H, BORDER_PX, 3))
        assert border_defects(frame_low_std, border_px=BORDER_PX) == ["black:left"]

    def test_uniform_dark_frame_does_not_false_positive_as_black_border(self) -> None:
        dark_frame = np.full((FRAME_H, FRAME_W, 3), 2, dtype=np.uint8)
        assert border_defects(dark_frame, border_px=BORDER_PX) == []

    @pytest.mark.parametrize("edge", ["top", "bottom", "left", "right"])
    def test_smeared_border_detected_on_each_edge(self, edge: str) -> None:
        frame = _textured_frame(seed=99)
        if edge == "top":
            frame[:BORDER_PX, :] = frame[BORDER_PX : BORDER_PX + 1, :]
        elif edge == "bottom":
            frame[-BORDER_PX:, :] = frame[-BORDER_PX - 1 : -BORDER_PX, :]
        elif edge == "left":
            frame[:, :BORDER_PX] = frame[:, BORDER_PX : BORDER_PX + 1]
        elif edge == "right":
            frame[:, -BORDER_PX:] = frame[:, -BORDER_PX - 1 : -BORDER_PX]

        defects = border_defects(frame, border_px=BORDER_PX)
        assert defects == [f"smear:{edge}"]

    def test_smear_outer_gradient_above_1_is_not_smear(self) -> None:
        frame = _textured_frame(seed=101)
        # 3 grey levels per pixel inward -> avg inward diff = 3.0 (>= 1.0), not smear
        ramp = (100 + 3 * np.arange(BORDER_PX, dtype=np.uint8))[None, :, None]
        frame[:, :BORDER_PX] = np.broadcast_to(ramp, (FRAME_H, BORDER_PX, 3))
        assert border_defects(frame, border_px=BORDER_PX) == []

    def test_smear_inner_band_gentle_gradient_below_4_is_not_smear(self) -> None:
        frame = _textured_frame(seed=102)
        # Constant outer band (diff 0 < 1.0), gentle 1.5/px gradient in next band (diff 1.5 <= 4.0)
        frame[:, :BORDER_PX] = 100
        inner_ramp = np.round(100 + 1.5 * np.arange(BORDER_PX)).astype(np.uint8)[None, :, None]
        frame[:, BORDER_PX : 2 * BORDER_PX] = np.broadcast_to(inner_ramp, (FRAME_H, BORDER_PX, 3))
        assert border_defects(frame, border_px=BORDER_PX) == []

    def test_custom_border_px_is_respected(self) -> None:
        frame_3px = _textured_frame(seed=103)
        frame_3px[:, :3] = 0
        assert border_defects(frame_3px, border_px=3) == ["black:left"]

        # 6px black band inside a 10px border_px leaves 4px of texture inside outer 10px band (std > 3)
        frame_6px = _textured_frame(seed=104)
        frame_6px[:, :6] = 0
        assert border_defects(frame_6px, border_px=10) == []

    def test_multiple_defects_reported_together(self) -> None:
        frame = _textured_frame(seed=123)
        frame[:BORDER_PX, :] = 0
        frame[:, -BORDER_PX:] = frame[:, -BORDER_PX - 1 : -BORDER_PX]

        defects = border_defects(frame, border_px=BORDER_PX)
        assert set(defects) == {"black:top", "smear:right"}

class TestHeadBoxDefects:
    """Tests for head_box_defects()."""

    def test_empty_boxes_returns_empty(self) -> None:
        assert head_box_defects([], (FRAME_H, FRAME_W), margin_px=8.0) == []

    def test_box_strictly_inside_margin_is_ok(self) -> None:
        boxes = [(20.0, 30.0, 200.0, 250.0)]
        assert head_box_defects(boxes, (FRAME_H, FRAME_W), margin_px=8.0) == []

    def test_box_exactly_on_margin_boundary_is_ok(self) -> None:
        margin = 8.0
        boxes = [(margin, margin, float(FRAME_W) - margin, float(FRAME_H) - margin)]
        assert head_box_defects(boxes, (FRAME_H, FRAME_W), margin_px=margin) == []

    def test_custom_margin_px_is_respected(self) -> None:
        assert head_box_defects([(2.0, 20.0, 120.0, 140.0)], (FRAME_H, FRAME_W), margin_px=0.0) == []
        assert head_box_defects([(15.0, 20.0, 120.0, 140.0)], (FRAME_H, FRAME_W), margin_px=20.0) == ["head_out:0"]

    @pytest.mark.parametrize(
        "box",
        [
            (7.9, 50.0, 150.0, 200.0),
            (50.0, 7.9, 150.0, 200.0),
            (1100.0, 50.0, 1272.1, 200.0),
            (50.0, 500.0, 150.0, 696.1),
            (-5.0, 50.0, 150.0, 200.0),
        ],
    )
    def test_box_outside_margin_returns_indexed_defect(
        self, box: tuple[float, float, float, float]
    ) -> None:
        assert head_box_defects([box], (FRAME_H, FRAME_W), margin_px=8.0) == ["head_out:0"]

    def test_multiple_boxes_report_only_violating_indices(self) -> None:
        boxes = [
            (20.0, 20.0, 120.0, 140.0),
            (2.0, 20.0, 120.0, 140.0),
            (300.0, 300.0, 400.0, 420.0),
            (300.0, 300.0, 400.0, 700.0),
        ]
        assert head_box_defects(boxes, (FRAME_H, FRAME_W), margin_px=8.0) == [
            "head_out:1",
            "head_out:3",
        ]

class TestFrameIntegrity:
    """Integration tests for frame_integrity() on synthetic clips."""

    def test_missing_file_returns_not_run(self, tmp_path: Path) -> None:
        missing = tmp_path / "does_not_exist.avi"
        result = frame_integrity(str(missing))

        assert result["ok"] is None
        assert result["checked_frames"] == 0
        assert result["defects"] == []
        assert isinstance(result["reason"], str)
        assert result["reason"].startswith("NOT_RUN")

    def test_intact_synthetic_clip_returns_ok_true(self, tmp_path: Path) -> None:
        frames = [_textured_frame(seed=10 + i) for i in range(6)]
        video_path = _write_lossless_avi(tmp_path / "intact.avi", frames)

        head_boxes = {
            0: [(100.0, 100.0, 220.0, 240.0)],
            5: [(110.0, 105.0, 230.0, 245.0)],
        }
        result = frame_integrity(str(video_path), head_boxes=head_boxes, border_px=BORDER_PX)

        assert result["ok"] is True
        assert result["checked_frames"] == 6
        assert result["defects"] == []
        assert isinstance(result["reason"], str) and len(result["reason"]) > 0

    def test_clip_with_head_boxes_none_returns_ok_true(self, tmp_path: Path) -> None:
        frames = [_textured_frame(seed=15 + i) for i in range(4)]
        video_path = _write_lossless_avi(tmp_path / "no_boxes.avi", frames)

        result = frame_integrity(str(video_path), head_boxes=None, border_px=BORDER_PX)

        assert result["ok"] is True
        assert result["checked_frames"] == 4
        assert result["defects"] == []

    def test_clip_with_black_left_border_on_one_frame_returns_ok_false(
        self, tmp_path: Path
    ) -> None:
        frames = [_textured_frame(seed=20 + i) for i in range(6)]
        bad_frame_idx = 3
        frames[bad_frame_idx][:, :BORDER_PX] = 0
        video_path = _write_lossless_avi(tmp_path / "black_left.avi", frames)

        result = frame_integrity(str(video_path), border_px=BORDER_PX)

        assert result["ok"] is False
        assert result["checked_frames"] == 6
        assert any(
            d["frame"] == bad_frame_idx and d["code"] == "black:left"
            for d in result["defects"]
        )
        assert str(bad_frame_idx) in result["reason"]
        assert "black:left" in result["reason"]

    def test_clip_with_head_box_outside_margin_returns_ok_false(self, tmp_path: Path) -> None:
        frames = [_textured_frame(seed=30 + i) for i in range(5)]
        video_path = _write_lossless_avi(tmp_path / "head_out.avi", frames)

        bad_frame_idx = 2
        head_boxes = {
            0: [(100.0, 100.0, 200.0, 220.0)],
            bad_frame_idx: [(2.0, 100.0, 120.0, 220.0)],
        }
        result = frame_integrity(
            str(video_path),
            head_boxes=head_boxes,
            border_px=BORDER_PX,
            margin_px=8.0,
        )

        assert result["ok"] is False
        assert result["checked_frames"] == 5
        assert result["defects"] == [{"frame": bad_frame_idx, "code": "head_out:0"}]
        assert str(bad_frame_idx) in result["reason"]
        assert "head_out:0" in result["reason"]

    def test_frame_integrity_forwards_margin_px_and_border_px(self, tmp_path: Path) -> None:
        frames_clean = [_textured_frame(seed=40 + i) for i in range(4)]
        video_clean = _write_lossless_avi(tmp_path / "margin_fwd.avi", frames_clean)
        head_boxes = {1: [(12.0, 50.0, 120.0, 180.0)]}

        res_default = frame_integrity(str(video_clean), head_boxes=head_boxes)
        assert res_default["ok"] is True

        res_strict_margin = frame_integrity(
            str(video_clean), head_boxes=head_boxes, margin_px=20.0
        )
        assert res_strict_margin["ok"] is False
        assert res_strict_margin["defects"] == [{"frame": 1, "code": "head_out:0"}]

        frames_3px = [_textured_frame(seed=45 + i) for i in range(4)]
        frames_3px[2][:, :3] = 0
        video_3px = _write_lossless_avi(tmp_path / "border_3px.avi", frames_3px)

        res_3px = frame_integrity(str(video_3px), border_px=3)
        assert res_3px["ok"] is False
        assert res_3px["defects"] == [{"frame": 2, "code": "black:left"}]

    def test_long_clip_subsampling_always_checks_first_middle_and_last_frames(
        self, tmp_path: Path
    ) -> None:
        total_frames = 15
        max_frames = 5
        frames = [_textured_frame(seed=50 + i) for i in range(total_frames)]
        for idx in (0, total_frames // 2, total_frames - 1):
            frames[idx][:BORDER_PX, :] = 0

        video_path = _write_lossless_avi(tmp_path / "subsampled.avi", frames)
        result = frame_integrity(
            str(video_path),
            border_px=BORDER_PX,
            max_frames=max_frames,
        )

        assert result["ok"] is False
        assert 3 <= result["checked_frames"] <= max_frames + 3
        defect_frames = {d["frame"] for d in result["defects"] if d["code"] == "black:top"}
        assert {0, total_frames // 2, total_frames - 1}.issubset(defect_frames)
