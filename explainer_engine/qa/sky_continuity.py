"""Sky optical-flow continuity check to detect looping seams and ping-pong motion.

Implements requirement IDs LP-09 (one wind per shot) and OR-V19e (alive sky) by
verifying that cloud drift within a declared sky mask moves continuously in one
dominant direction at a steady speed without reversals or sudden velocity jumps.
"""

from __future__ import annotations

from typing import Any
import numpy as np


def analyse_window_flows(
   mean_dx: list[float],
   mean_dy: list[float],
   min_speed: float = 0.05,
   max_reversed_share: float = 0.10,
   max_jump_ratio: float = 3.0,
) -> dict[str, Any]:
   """Analyse consecutive window optical-flow vectors for steady, unidirectional drift.

   Args:
       mean_dx: Mean horizontal optical flow (pixels per window) for consecutive windows.
       mean_dy: Mean vertical optical flow (pixels per window) for consecutive windows.
       min_speed: Minimum flow magnitude threshold below which motion is treated as static.
       max_reversed_share: Maximum allowed fraction of moving windows opposing the median direction.
       max_jump_ratio: Maximum allowed speed ratio between any two adjacent windows.

   Returns:
       Dictionary containing:
           - 'ok': bool | None (True if continuous, False if failed, None if NOT_RUN)
           - 'reversed_share': float
           - 'max_jump_ratio': float
           - 'windows': int
           - 'reason': str
   """
   n_windows = min(len(mean_dx), len(mean_dy))
   if n_windows < 4:
       return {
           "ok": None,
           "reversed_share": 0.0,
           "max_jump_ratio": 0.0,
           "windows": n_windows,
           "reason": "NOT_RUN: clip too short",
       }

   dx = np.asarray(mean_dx[:n_windows], dtype=np.float64)
   dy = np.asarray(mean_dy[:n_windows], dtype=np.float64)
   speeds = np.hypot(dx, dy)

   # Calculate max speed jump ratio across consecutive windows
   if n_windows >= 2:
       s_prev = speeds[:-1]
       s_next = speeds[1:]
       high = np.maximum(s_prev, s_next)
       low = np.maximum(np.minimum(s_prev, s_next), min_speed)
       jump = float(np.max(high / low))
   else:
       jump = 0.0

   # Check if the sky is completely static across all windows
   if bool(np.all(speeds < min_speed)):
       return {
           "ok": False,
           "reversed_share": 0.0,
           "max_jump_ratio": jump,
           "windows": n_windows,
           "reason": "sky does not move",
       }

   # Determine dominant axis via larger median absolute displacement
   med_abs_x = float(np.median(np.abs(dx)))
   med_abs_y = float(np.median(np.abs(dy)))
   dominant = dx if med_abs_x >= med_abs_y else dy

   # Filter to windows where movement along the dominant axis meets min_speed
   moving_mask = np.abs(dominant) >= min_speed
   counted_vals = dominant[moving_mask]

   if counted_vals.size == 0:
       return {
           "ok": False,
           "reversed_share": 0.0,
           "max_jump_ratio": jump,
           "windows": n_windows,
           "reason": "sky does not move",
       }

   med_sign = float(np.sign(np.median(counted_vals)))
   if med_sign == 0.0:
       # Tie in positive vs negative counts: median is 0, meaning half are reversed
       reversed_share = 0.5
   else:
       reversed_count = int(np.sum(np.sign(counted_vals) != med_sign))
       reversed_share = float(reversed_count / counted_vals.size)

   rev_ok = reversed_share <= max_reversed_share
   jump_ok = jump <= max_jump_ratio
   ok = bool(rev_ok and jump_ok and n_windows >= 4)

   if ok:
       reason = "OK"
   elif not rev_ok and not jump_ok:
       reason = (
           f"direction reversal ({reversed_share:.2%} > {max_reversed_share:.2%}) "
           f"and speed jump ({jump:.2f} > {max_jump_ratio:.2f})"
       )
   elif not rev_ok:
       reason = f"direction reversal ({reversed_share:.2%} > {max_reversed_share:.2%})"
   else:
       reason = f"speed jump ({jump:.2f} > {max_jump_ratio:.2f})"

   return {
       "ok": ok,
       "reversed_share": reversed_share,
       "max_jump_ratio": jump,
       "windows": n_windows,
       "reason": reason,
   }


def sky_continuity(
   video_path: str,
   sky_mask: np.ndarray,
   window_s: float = 0.5,
   pair_gap_s: float = 0.25,
   **kw: Any,
) -> dict[str, Any]:
   """Evaluate sky motion continuity on a video clip using dense Farneback optical flow.

   Args:
       video_path: Path to the input video file.
       sky_mask: 2D mask (boolean or 0..1 float, > 0.5 counts as sky) matching frame aspect/shape.
       window_s: Duration in seconds of each aggregation window.
       pair_gap_s: Temporal spacing in seconds between frame pairs for Farneback flow.
       **kw: Additional keyword arguments forwarded to `analyse_window_flows`.

   Returns:
       Result dictionary from `analyse_window_flows`, or {'ok': None, 'reason': 'NOT_RUN: ...'}.
   """
   try:
       import cv2
   except ImportError:
       return {"ok": None, "reason": "NOT_RUN: cv2 not available"}

   if window_s <= 0 or pair_gap_s <= 0:
       return {"ok": None, "reason": "NOT_RUN: window_s and pair_gap_s must be positive"}

   cap = cv2.VideoCapture(str(video_path))
   if not cap.isOpened():
       return {"ok": None, "reason": f"NOT_RUN: cannot open video {video_path}"}

   try:
       fps = float(cap.get(cv2.CAP_PROP_FPS))
       if fps <= 0.0 or np.isnan(fps):
           return {"ok": None, "reason": "NOT_RUN: invalid video FPS"}

       # Read first frame to establish dimensions and scaling
       ret, first_frame = cap.read()
       if not ret or first_frame is None:
           return {"ok": None, "reason": "NOT_RUN: empty or unreadable video"}

       orig_h, orig_w = first_frame.shape[:2]
       target_w = 480
       scale = target_w / float(orig_w) if orig_w > 0 else 1.0
       target_h = max(1, int(round(orig_h * scale)))

       mask_arr = np.asarray(sky_mask)
       if mask_arr.ndim == 3:
           mask_arr = mask_arr[:, :, 0]
       if mask_arr.shape != (orig_h, orig_w) and mask_arr.shape != (target_h, target_w):
           return {
               "ok": None,
               "reason": f"NOT_RUN: sky_mask shape {mask_arr.shape} mismatches frame {(orig_h, orig_w)}",
           }

       # Prepare binary mask at downscaled resolution
       mask_float = (mask_arr > 0.5).astype(np.uint8)
       if mask_float.shape != (target_h, target_w):
           mask_resized = cv2.resize(mask_float, (target_w, target_h), interpolation=cv2.INTER_NEAREST)
       else:
           mask_resized = mask_float
       sky_bool = mask_resized > 0

       if not np.any(sky_bool):
           return {"ok": None, "reason": "NOT_RUN: empty sky_mask"}

       # Preprocess and store grayscale frames
       def _prep_gray(bgr: np.ndarray) -> np.ndarray:
           resized = cv2.resize(bgr, (target_w, target_h), interpolation=cv2.INTER_AREA)
           return cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

       gray_frames: list[np.ndarray] = [_prep_gray(first_frame)]
       while True:
           ok_read, frame = cap.read()
           if not ok_read or frame is None:
               break
           gray_frames.append(_prep_gray(frame))
   finally:
       cap.release()

   n_frames = len(gray_frames)
   gap_frames = max(1, int(round(pair_gap_s * fps)))
   window_frames = max(1, int(round(window_s * fps)))

   if n_frames <= gap_frames:
       return {"ok": None, "reason": "NOT_RUN: clip too short"}

   # Compute mean sky flow per window_s window using pairs spaced pair_gap_s apart
   mean_dx: list[float] = []
   mean_dy: list[float] = []

   win_start = 0
   while win_start + window_frames <= n_frames:
       win_end = win_start + window_frames
       pair_dxs: list[float] = []
       pair_dys: list[float] = []

       # Sample pairs anchored inside this window
       step = max(1, gap_frames)
       for idx in range(win_start, win_end, step):
           pair_idx = idx + gap_frames
           if pair_idx >= n_frames:
               break
           flow = cv2.calcOpticalFlowFarneback(
               gray_frames[idx],
               gray_frames[pair_idx],
               None,
               pyr_scale=0.5,
               levels=3,
               winsize=15,
               iterations=3,
               poly_n=5,
               poly_sigma=1.2,
               flags=0,
           )
           # Normalize displacement to per-window scale so thresholds remain consistent across pair_gap_s
           scale_to_window = float(window_frames) / float(gap_frames)
           pair_dxs.append(float(np.mean(flow[..., 0][sky_bool])) * scale_to_window)
           pair_dys.append(float(np.mean(flow[..., 1][sky_bool])) * scale_to_window)

       if pair_dxs:
           mean_dx.append(float(np.mean(pair_dxs)))
           mean_dy.append(float(np.mean(pair_dys)))

       win_start += window_frames

   return analyse_window_flows(mean_dx, mean_dy, **kw)
