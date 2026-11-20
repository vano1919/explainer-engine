"""Pure frame-integrity checks for drift and push clips.


Detects black/blank or smeared outer edge bands and verifies that optional
head bounding boxes remain inside the frame with a safety margin.
"""


from __future__ import annotations


from typing import Any


import numpy as np




def _to_luma(frame: np.ndarray) -> np.ndarray:
    """Convert an (H, W, 3) uint8 array to float64 grayscale luminance."""
    if frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError(f"Expected frame with shape (H, W, 3), got {frame.shape}")
    arr = frame.astype(np.float64)
    # Standard Rec.601 weights; identical across RGB/BGR for grey-level thresholds
    return 0.299 * arr[:, :, 0] + 0.587 * arr[:, :, 1] + 0.114 * arr[:, :, 2]




def _inward_mean_diff(band: np.ndarray, axis: int) -> float:
    """Mean absolute adjacent-pixel difference along the inward axis."""
    if band.shape[axis] < 2:
        return 0.0
    return float(np.mean(np.abs(np.diff(band, axis=axis))))




def border_defects(frame: np.ndarray, border_px: int = 6) -> list[str]:
    """Check outer border_px bands of all 4 edges for black/blank or smeared pixels.


    Args:
        frame: uint8 array of shape (H, W, 3).
        border_px: Width in pixels of the outer band (and inner reference band).


    Returns:
        List of defect codes among 'black:<edge>' and 'smear:<edge>', where
        <edge> is one of 'top', 'bottom', 'left', 'right'. Empty list means intact.
    """
    if border_px <= 0:
        return []


    luma = _to_luma(frame)
    height, width = luma.shape
    if height < 2 * border_px or width < 2 * border_px:
        return []


    # (edge_name, outer_band, inner_band, inward_axis)
    edges: list[tuple[str, np.ndarray, np.ndarray, int]] = [
        ("top", luma[:border_px, :], luma[border_px : 2 * border_px, :], 0),
        ("bottom", luma[height - border_px :, :], luma[height - 2 * border_px : height - border_px, :], 0),
        ("left", luma[:, :border_px], luma[:, border_px : 2 * border_px], 1),
        ("right", luma[:, width - border_px :], luma[:, width - 2 * border_px : width - border_px], 1),
    ]


    defects: list[str] = []
    for edge_name, outer, inner, axis in edges:
        outer_mean = float(np.mean(outer))
        outer_std = float(np.std(outer))
        inner_std = float(np.std(inner))


        if outer_mean < 8.0 and outer_std < 3.0 and inner_std > 12.0:
            defects.append(f"black:{edge_name}")
            continue


        outer_diff = _inward_mean_diff(outer, axis)
        inner_diff = _inward_mean_diff(inner, axis)
        if outer_diff < 1.0 and inner_diff > 4.0:
            defects.append(f"smear:{edge_name}")


    return defects




def head_box_defects(
    boxes: list[tuple[float, float, float, float]],
    shape_hw: tuple[int, int],
    margin_px: float = 8.0,
) -> list[str]:
    """Check whether each (x0, y0, x1, y1) box stays inside the frame with margin_px.


    Args:
        boxes: List of (x0, y0, x1, y1) bounding boxes in pixel coordinates.
        shape_hw: Frame (height, width) in pixels.
        margin_px: Required minimum distance from every frame edge.


    Returns:
        List of 'head_out:<index>' strings for boxes violating the margin.
    """
    height, width = shape_hw
    min_x = float(margin_px)
    min_y = float(margin_px)
    max_x = float(width) - float(margin_px)
    max_y = float(height) - float(margin_px)


    defects: list[str] = []
    for idx, (x0, y0, x1, y1) in enumerate(boxes):
        if x0 < min_x or y0 < min_y or x1 > max_x or y1 > max_y:
            defects.append(f"head_out:{idx}")
    return defects




def _select_frame_indices(total_frames: int, max_frames: int) -> list[int]:
    """Select sorted unique frame indices to inspect, always including 0, mid, and last."""
    if total_frames <= 0:
        return []
    if max_frames <= 0 or total_frames <= max_frames:
        return list(range(total_frames))


    step = max(1, total_frames // max_frames)
    indices = set(range(0, total_frames, step))
    indices.add(0)
    indices.add(total_frames // 2)
    indices.add(total_frames - 1)
    return sorted(indices)




def _format_defect_reason(first_defect: dict[str, Any]) -> str:
    """Build a single plain-English sentence naming the first defect and its frame."""
    frame_idx = first_defect["frame"]
    code = str(first_defect["code"])
    kind, _, target = code.partition(":")


    if kind == "black":
        return f"Frame {frame_idx} has a black or blank {target} border ({code})."
    if kind == "smear":
        return f"Frame {frame_idx} has a smeared {target} border ({code})."
    if kind == "head_out":
        return f"Frame {frame_idx} has head box {target} extending outside the safe margin ({code})."
    return f"Frame {frame_idx} failed integrity check with defect {code}."




def frame_integrity(
    video_path: str,
    head_boxes: dict[int, list[tuple[float, float, float, float]]] | None = None,
    border_px: int = 6,
    margin_px: float = 8.0,
    max_frames: int = 240,
) -> dict[str, Any]:
    """Inspect a video clip for edge border defects and out-of-bounds head boxes.


    Args:
        video_path: Path to the video file.
        head_boxes: Optional mapping from frame index to (x0, y0, x1, y1) boxes.
        border_px: Outer edge band thickness in pixels.
        margin_px: Safe margin in pixels required around head boxes.
        max_frames: Maximum target number of sampled frames when clip is longer.


    Returns:
        Dictionary with keys 'ok', 'checked_frames', 'defects', and 'reason'.
    """
    try:
        import cv2
    except Exception as exc:
        return {
            "ok": None,
            "checked_frames": 0,
            "defects": [],
            "reason": f"NOT_RUN: cv2 unavailable ({exc}).",
        }


    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        cap.release()
        return {
            "ok": None,
            "checked_frames": 0,
            "defects": [],
            "reason": f"NOT_RUN: could not open video '{video_path}'.",
        }


    try:
        reported_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        frames_by_idx: dict[int, np.ndarray] = {}


        if reported_count > 0:
            target_indices = _select_frame_indices(reported_count, max_frames)
            current_pos = 0
            for idx in target_indices:
                if idx != current_pos:
                    cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                    current_pos = idx
                ret, frame = cap.read()
                if ret and frame is not None:
                    frames_by_idx[idx] = frame
                    current_pos += 1
                else:
                    # Fallback if seeking past actual readable end (e.g. VFR/container mismatch)
                    break


        # Fallback to sequential read if metadata frame count was 0 or seeking failed early
        if not frames_by_idx:
            cap.release()
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                return {
                    "ok": None,
                    "checked_frames": 0,
                    "defects": [],
                    "reason": f"NOT_RUN: could not open video '{video_path}'.",
                }
            all_frames: list[np.ndarray] = []
            while True:
                ret, frame = cap.read()
                if not ret or frame is None:
                    break
                all_frames.append(frame)


            if not all_frames:
                return {
                    "ok": None,
                    "checked_frames": 0,
                    "defects": [],
                    "reason": f"NOT_RUN: no readable frames in '{video_path}'.",
                }
            for idx in _select_frame_indices(len(all_frames), max_frames):
                frames_by_idx[idx] = all_frames[idx]
    finally:
        cap.release()


    if not frames_by_idx:
        return {
            "ok": None,
            "checked_frames": 0,
            "defects": [],
            "reason": f"NOT_RUN: no readable frames in '{video_path}'.",
        }


    defects: list[dict[str, Any]] = []
    boxes_map = head_boxes or {}


    for frame_idx in sorted(frames_by_idx):
        frame = frames_by_idx[frame_idx]
        for code in border_defects(frame, border_px=border_px):
            defects.append({"frame": frame_idx, "code": code})


        if frame_idx in boxes_map:
            h, w = frame.shape[:2]
            for code in head_box_defects(boxes_map[frame_idx], (h, w), margin_px=margin_px):
                defects.append({"frame": frame_idx, "code": code})


    checked_frames = len(frames_by_idx)
    if defects:
        return {
            "ok": False,
            "checked_frames": checked_frames,
            "defects": defects,
            "reason": _format_defect_reason(defects[0]),
        }


    return {
        "ok": True,
        "checked_frames": checked_frames,
        "defects": [],
        "reason": f"All {checked_frames} checked frames passed border and head-box integrity checks.",
    }
