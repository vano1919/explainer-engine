# explainer_engine/qa/camera_move.py
# Source: Gemini chat https://gemini.google.com/app/f8d46811b0a2af4c (VAL-CAMERA-MOVE)
# Text copied from the chat page (page text), not byte-exact. Review before use.
"""Camera move validation for shot cards and rendered video clips (VAL-CAMERA-MOVE).

Validates:
1. Shot cards (`check_shot_cards`): ensures each shot specifies an allowed
   camera move (`CAMERA_MOVES`), forbids static/orbit/rotation moves, enforces
   a single-line `camera_why` quoting the shot's narration cue, and flags
   proposal-keyword mismatches or excessive consecutive identical moves as REVIEW.
2. Video clips (`camera_move_clip` / `measure_camera`): estimates 2D similarity
   transforms across frames and 1-second windows to verify zoom %, horizontal
   pan %, near-zero rotation, continuous motion, and synchronized easing for
   combined truck+zoom moves.

Note on sourced rules (`SR.T`):
Numeric thresholds from `BP-109`, `BP-181`, and `BP-215` are loaded dynamically
from `sourced_rules.json` (and module hypothesis tolerances from
`camera_move_tolerances.json`) rather than hardcoded in source logic.
"""

from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

# ---------------------------------------------------------------------------
# Public constants
# ---------------------------------------------------------------------------

CAMERA_MOVES: tuple[str, ...] = (
    "truck_l",
    "truck_r",
    "zoom_in",
    "zoom_out",
    "truck_zoom_in",
    "truck_zoom_out",
)

FORBIDDEN_MOVES: tuple[str, ...] = (
    "static", "still", "none", "orbit", "rotate", "rotation", "roll", "spin", "arc", "pan_rotate",
)
_STATIC_VALUES = ("static", "still", "none")


def _bad_move_message(value: str, what: str = "camera_move") -> str:
    """The CM-02 text for a value outside CAMERA_MOVES (case/space-insensitive; any value containing orbit/rot)."""
    low = re.sub(r"\s+", "_", value.strip().lower())
    if low in _STATIC_VALUES:
        return "static is not allowed: the camera never stops (owner 2026-11-20 18:10, OR-V24)"
    if low in FORBIDDEN_MOVES or "orbit" in low or "rot" in low:
        return f"{what}={value!r}: orbit and rotation are forbidden (owner decision 2026-11-20 16:25)"
    return f"{what}={value!r} is not in allowed CAMERA_MOVES {CAMERA_MOVES}"

SUPPORTED_CLIP_KINDS: tuple[str, ...] = (".mp4", ".mov", ".webm", ".mkv")

# Single constant defining the sign convention for `truck_l` in image-motion space:
# Camera moves left -> scene content shifts right -> positive x translation (+1.0).
TRUCK_L_PAN_SIGN: float = 1.0

DEFAULT_FPS: int = 8

# CM-05 proposal table (the lead's proposal from CAMERA_MOVES_DECISION_2026-11-20.md, NOT the owner's). It also lives in
# camera_move_tolerances.json under "proposal_table"; a row = {moves, cues}. A REVIEW only.
PROPOSAL_TABLE: dict[str, dict[str, Any]] = {
    "truck (extent or travelling)": {
        "moves": ["truck_l", "truck_r"],
        "cues": ["all along", "line of", "row of", "advance", "marches", "walks", "street", "trench", "crowd"],
    },
    "zoom_in (attention, tension)": {
        "moves": ["zoom_in"],
        "cues": ["named", "reveal", "decision", "decides", "clue", "face", "number"],
    },
    "zoom_out (scale, context, aftermath)": {
        "moves": ["zoom_out"],
        "cues": ["all of this", "aftermath", "consequence", "alone", "the end of", "everything"],
    },
}

# Fallback tolerance values used ONLY if `camera_move_tolerances.json` is absent.
# Every entry carries `kind` and `status` metadata matching the spec.
_DEFAULT_TOLERANCES: dict[str, dict[str, Any]] = {
    "rotation_max_deg": {
        "value": 0.5,
        "kind": "deg",
        "status": "hypothesis, not binding until the owner has seen it",
    },
    "pan_min_pct": {
        "value": 2.0,
        "kind": "pct",
        "status": "hypothesis, not binding until the owner has seen it",
    },
    "pan_none_pct": {
        "value": 1.0,
        "kind": "pct",
        "status": "hypothesis, not binding until the owner has seen it",
    },
    "zoom_none_pct": {
        "value": 1.0,
        "kind": "pct",
        "status": "hypothesis, not binding until the owner has seen it",
    },
    "ease_tol": {
        "value": 0.15,
        "kind": "ratio",
        "status": "hypothesis, not binding until the owner has seen it",
    },
    "same_move_run_max": {
        "value": 3,
        "kind": "count",
        "status": "hypothesis, not binding until the owner has seen it",
    },
}

# ---------------------------------------------------------------------------
# Sourced rules (SR.T) & tolerance configuration loaders
# ---------------------------------------------------------------------------


class SourcedRuleTable:
    """Lightweight reader (`SR.T`) for `sourced_rules.json`."""

    def __init__(self, rules: Mapping[str, Any]) -> None:
        self._rules = dict(rules)

    @classmethod
    def load(cls, search_dirs: Sequence[Path] | None = None) -> "SourcedRuleTable":
        if search_dirs is None and not os.environ.get("CAMERA_MOVE_SOURCED_RULES"):
            try:  # the repo's own registry reader (SR.T) is the source of truth
                from explainer_engine.standards import sourced_rules as _SR  # type: ignore

                return cls(cls._normalize({"rules": _SR.rules()}))
            except Exception:
                pass
        env_path = os.environ.get("CAMERA_MOVE_SOURCED_RULES")
        candidates: list[Path] = []
        if env_path:
            candidates.append(Path(env_path))

        here = Path(__file__).resolve().parent
        bases = list(search_dirs) if search_dirs else [
            here,
            here.parent,
            here.parent.parent,
            Path.cwd(),
            Path.cwd() / "camera_move",
            Path.cwd() / "validator_inputs_g4" / "camera_move",
        ]
        for base in bases:
            candidates.append(base / "sourced_rules.json")

        for path in candidates:
            if path.is_file():
                raw = json.loads(path.read_text(encoding="utf-8"))
                return cls(cls._normalize(raw))

        raise FileNotFoundError(
            "sourced_rules.json not found; required for BP-109, BP-181, and BP-215 thresholds."
        )

    @staticmethod
    def _normalize(raw: Any) -> dict[str, dict[str, Any]]:
        """Normalize either dict-keyed or list-of-rules JSON schemas."""
        out: dict[str, dict[str, Any]] = {}
        if isinstance(raw, Mapping):
            container = raw.get("rules", raw) if "rules" in raw and isinstance(raw["rules"], (Mapping, list)) else raw
            if isinstance(container, Mapping):
                for k, v in container.items():
                    if isinstance(v, Mapping):
                        out[str(k)] = dict(v)
            elif isinstance(container, list):
                for item in container:
                    if isinstance(item, Mapping):
                        rule_id = item.get("id") or item.get("rule_id") or item.get("code")
                        if rule_id:
                            out[str(rule_id)] = dict(item)
        elif isinstance(raw, list):
            for item in raw:
                if isinstance(item, Mapping):
                    rule_id = item.get("id") or item.get("rule_id") or item.get("code")
                    if rule_id:
                        out[str(rule_id)] = dict(item)
        return out

    def get_number(self, rule_id: str, field: str) -> float:
        rule = self._rules.get(rule_id)
        if rule is None:
            raise KeyError(f"Sourced rule {rule_id!r} missing from sourced_rules.json")
        if field in rule and isinstance(rule[field], (int, float)):
            return float(rule[field])
        # Support nested `values` / `params` / `thresholds` dictionaries
        for subkey in ("values", "params", "thresholds", "numbers"):
            sub = rule.get(subkey)
            if isinstance(sub, Mapping) and field in sub and isinstance(sub[field], (int, float)):
                return float(sub[field])
        raise KeyError(f"Field {field!r} missing from sourced rule {rule_id!r}")


def _load_tolerances(tolerances_path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load `camera_move_tolerances.json`, falling back to `_DEFAULT_TOLERANCES`."""
    candidates: list[Path] = []
    if tolerances_path is not None:
        candidates.append(tolerances_path)
    env_tol = os.environ.get("CAMERA_MOVE_TOLERANCES")
    if env_tol:
        candidates.append(Path(env_tol))
    candidates.append(Path(__file__).resolve().parent / "camera_move_tolerances.json")

    merged = {k: dict(v) for k, v in _DEFAULT_TOLERANCES.items()}
    for path in candidates:
        if path.is_file():
            raw = json.loads(path.read_text(encoding="utf-8"))
            if isinstance(raw, Mapping):
                for key, spec in raw.items():
                    if isinstance(spec, Mapping) and ("value" in spec or "rows" in spec):
                        merged[key] = dict(spec)
                    elif isinstance(spec, (int, float)):
                        base = merged.get(key, {"kind": "unknown", "status": "hypothesis, not binding until the owner has seen it"})
                        merged[key] = {**base, "value": spec}
            break
    return merged


def _tol_val(tolerances: Mapping[str, Mapping[str, Any]], key: str) -> float:
    return float(tolerances[key]["value"])


# ---------------------------------------------------------------------------
# OpenCV & frame decoding helpers (self-contained)
# ---------------------------------------------------------------------------


def _cv2() -> Any | None:
    """Import cv2 lazily; return None if unavailable."""
    try:
        import cv2  # type: ignore

        return cv2
    except Exception:
        return None


def _numpy() -> Any | None:
    """Import numpy lazily; return None if unavailable."""
    try:
        import numpy as np  # type: ignore

        return np
    except Exception:
        return None


def decode_grey(path: str | Path, fps: int = DEFAULT_FPS) -> tuple[list[Any], float]:
    """Decode a video file into grayscale frames sampled at `fps`.

    Returns `(frames, effective_fps)`. Returns `([], 0.0)` if OpenCV is
    unavailable or the file cannot be opened.
    """
    cv2 = _cv2()
    if cv2 is None:
        return [], 0.0

    cap = cv2.VideoCapture(str(path))
    if not cap or not cap.isOpened():
        if cap:
            cap.release()
        return [], 0.0

    try:
        src_fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        if src_fps <= 0.0 or math.isnan(src_fps):
            src_fps = float(fps)
        target_fps = float(fps) if fps > 0 else src_fps
        step = max(1, int(round(src_fps / target_fps))) if src_fps > target_fps else 1
        effective_fps = src_fps / step

        frames: list[Any] = []
        idx = 0
        while True:
            ok, frame = cap.read()
            if not ok or frame is None:
                break
            if idx % step == 0:
                if frame.ndim == 3:
                    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                else:
                    grey = frame
                frames.append(grey)
            idx += 1
        return frames, effective_fps
    finally:
        cap.release()


# ---------------------------------------------------------------------------
# Motion estimation helpers (2D similarity transform)
# ---------------------------------------------------------------------------


def _estimate_similarity(prev_grey: Any, curr_grey: Any) -> Any | None:
    """Estimate a 2x3 partial affine (similarity: scale, rotation, translation)
    transform mapping `prev_grey` -> `curr_grey`.

    Returns a 2x3 numpy ndarray or None if camera motion cannot be fitted.
    """
    cv2 = _cv2()
    np = _numpy()
    if cv2 is None or np is None:
        return None

    h, w = prev_grey.shape[:2]
    if h < 16 or w < 16:
        return None

    # Primary: Shi-Tomasi corners + Lucas-Kanade optical flow + RANSAC partial affine
    pts_prev = cv2.goodFeaturesToTrack(
        prev_grey,
        maxCorners=400,
        qualityLevel=0.01,
        minDistance=max(4, min(h, w) // 40),
        blockSize=7,
    )
    if pts_prev is not None and len(pts_prev) >= 6:
        pts_curr, status, _err = cv2.calcOpticalFlowPyrLK(
            prev_grey,
            curr_grey,
            pts_prev,
            None,
            winSize=(21, 21),
            maxLevel=3,
        )
        if pts_curr is not None and status is not None:
            mask = status.reshape(-1) == 1
            good_prev = pts_prev[mask]
            good_curr = pts_curr[mask]
            if len(good_prev) >= 6:
                mat, inliers = cv2.estimateAffinePartial2D(
                    good_prev,
                    good_curr,
                    method=cv2.RANSAC,
                    ransacReprojThreshold=3.0,
                    maxIters=2000,
                    confidence=0.99,
                )
                if mat is not None and inliers is not None and int(inliers.sum()) >= 4:
                    return mat

    # Fallback: ORB feature matching + RANSAC partial affine
    orb = cv2.ORB_create(nfeatures=500)
    kp1, des1 = orb.detectAndCompute(prev_grey, None)
    kp2, des2 = orb.detectAndCompute(curr_grey, None)
    if des1 is not None and des2 is not None and len(kp1) >= 6 and len(kp2) >= 6:
        bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
        matches = bf.match(des1, des2)
        if len(matches) >= 6:
            matches = sorted(matches, key=lambda m: m.distance)[:200]
            src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
            dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)
            mat, inliers = cv2.estimateAffinePartial2D(
                src_pts,
                dst_pts,
                method=cv2.RANSAC,
                ransacReprojThreshold=3.0,
            )
            if mat is not None and inliers is not None and int(inliers.sum()) >= 4:
                return mat

    return None


def _rotation_deg_from_similarity(mat: Any) -> float:
    """Compute rotation in degrees from a 2x3 similarity matrix."""
    return math.degrees(math.atan2(float(mat[1, 0]), float(mat[0, 0])))


def _decompose_step(mat: Any, width: int, height: int) -> dict[str, float]:
    """Decompose a 2x3 similarity matrix into step zoom %, pan_x %, pan_y %, rotation_deg.

    Convention:
    - A similarity transform maps point `(x, y)` in frame t to `(x', y')` in frame t+1:
        x' = s * cos(theta) * x - s * sin(theta) * y + tx
        y' = s * sin(theta) * x + s * cos(theta) * y + ty
    - Pure scale `s` about frame center `(cx, cy)` yields:
        tx_center = tx + (s * cos(theta) - 1) * cx - s * sin(theta) * cy
        ty_center = ty + s * sin(theta) * cx + (s * cos(theta) - 1) * cy
      Separating center-anchored translation removes false pan caused by
      zooming around the image center.
    - `zoom_pct`: `(s - 1.0) * 100.0` (positive = zoom_in, negative = zoom_out).
    - `pan_x_pct`: `(tx_center / width) * 100.0` (positive = scene shifts right = `truck_l`).
    - `pan_y_pct`: `(ty_center / height) * 100.0`.
    - `rotation_deg`: `degrees(atan2(M[1, 0], M[0, 0]))`.
    """
    a = float(mat[0, 0])
    b = float(mat[1, 0])
    tx = float(mat[0, 2])
    ty = float(mat[1, 2])

    scale = math.hypot(a, b)
    rot_deg = _rotation_deg_from_similarity(mat)

    cx = width / 2.0
    cy = height / 2.0
    # Residual translation at the frame center
    dx_center = (a * cx - float(mat[0, 1]) * cy + tx) - cx
    dy_center = (b * cx + float(mat[1, 1]) * cy + ty) - cy

    return {
        "scale": scale,
        "zoom_pct": (scale - 1.0) * 100.0,
        "pan_x_pct": (dx_center / float(width)) * 100.0 if width > 0 else 0.0,
        "pan_y_pct": (dy_center / float(height)) * 100.0 if height > 0 else 0.0,
        "rotation_deg": rot_deg,
    }


def measure_camera(
    frames: Sequence[Any],
    fps: float = DEFAULT_FPS,
    hold_step_eps_pct: float = 0.05,
) -> dict[str, Any]:
    """Measure camera zoom %, pan_x %, pan_y %, rotation, easing, and hold share
    across a sequence of grayscale frames.

    Returns a dictionary containing:
    - `fitted`: bool (False if < 2 frames, OpenCV missing, or transforms fail)
    - `reason`: str | None (when `fitted` is False)
    - `frame_count`: int
    - `fps`: float
    - `zoom_pct`: float (cumulative clip zoom %)
    - `pan_x_pct`: float (cumulative clip horizontal pan %)
    - `pan_y_pct`: float (cumulative clip vertical pan %)
    - `rotation_deg`: float (net clip rotation in degrees)
    - `max_abs_rotation_deg`: float (peak |rotation| across clip and 1s windows)
    - `total_change_pct`: float (overall magnitude combining zoom and pan)
    - `hold_share`: float (fraction of frame steps with near-zero motion)
    - `ease_diff`: float (max progress discrepancy between pan_x and zoom trajectories)
    - `windows`: list[dict] (1-second window measurements)
    """
    frame_list = list(frames)
    n = len(frame_list)
    if _cv2() is None or _numpy() is None:
        return {"fitted": False, "reason": "opencv_unavailable", "frame_count": n}
    if n < 2:
        return {"fitted": False, "reason": "insufficient_frames", "frame_count": n}

    h, w = frame_list[0].shape[:2]
    steps: list[dict[str, float]] = []
    failed_pairs = 0

    for i in range(n - 1):
        mat = _estimate_similarity(frame_list[i], frame_list[i + 1])
        if mat is None:
            failed_pairs += 1
            continue
        steps.append(_decompose_step(mat, w, h))

    if not steps or failed_pairs > max(1, (n - 1) // 2):
        return {
            "fitted": False,
            "reason": "camera_not_fitted",
            "frame_count": n,
            "failed_pairs": failed_pairs,
        }

    # Accumulate trajectory across fitted steps
    cum_scale = 1.0
    cum_pan_x = 0.0
    cum_pan_y = 0.0
    cum_rot = 0.0

    zoom_traj: list[float] = [0.0]
    pan_x_traj: list[float] = [0.0]
    hold_steps = 0

    for st in steps:
        cum_scale *= st["scale"]
        cum_pan_x += st["pan_x_pct"]
        cum_pan_y += st["pan_y_pct"]
        cum_rot += st["rotation_deg"]

        zoom_traj.append((cum_scale - 1.0) * 100.0)
        pan_x_traj.append(cum_pan_x)

        step_mag = math.hypot(st["zoom_pct"], math.hypot(st["pan_x_pct"], st["pan_y_pct"]))
        if step_mag < hold_step_eps_pct:
            hold_steps += 1

    total_zoom_pct = (cum_scale - 1.0) * 100.0
    total_pan_x_pct = cum_pan_x
    total_pan_y_pct = cum_pan_y
    net_rotation_deg = cum_rot
    hold_share = hold_steps / float(len(steps))

    # Build 1-second windows
    win_size = max(1, int(round(fps))) if fps > 0 else DEFAULT_FPS
    windows: list[dict[str, float]] = []
    max_win_abs_rot = abs(net_rotation_deg)

    for start in range(0, len(steps), win_size):
        chunk = steps[start : start + win_size]
        w_scale = 1.0
        w_pan_x = 0.0
        w_pan_y = 0.0
        w_rot = 0.0
        for st in chunk:
            w_scale *= st["scale"]
            w_pan_x += st["pan_x_pct"]
            w_pan_y += st["pan_y_pct"]
            w_rot += st["rotation_deg"]
        max_win_abs_rot = max(max_win_abs_rot, abs(w_rot))
        windows.append(
            {
                "start_step": float(start),
                "end_step": float(start + len(chunk)),
                "zoom_pct": (w_scale - 1.0) * 100.0,
                "pan_x_pct": w_pan_x,
                "pan_y_pct": w_pan_y,
                "rotation_deg": w_rot,
            }
        )

    # Easing synchronization check: compare normalized progress of pan_x vs zoom
    # across 1-second window boundaries (and intermediate samples).
    ease_diff = 0.0
    if abs(total_zoom_pct) > 1e-6 and abs(total_pan_x_pct) > 1e-6:
        sample_indices = list(range(win_size, len(zoom_traj), win_size))
        if not sample_indices or sample_indices[-1] != len(zoom_traj) - 1:
            sample_indices.append(len(zoom_traj) - 1)
        for idx in sample_indices:
            z_prog = zoom_traj[idx] / total_zoom_pct
            p_prog = pan_x_traj[idx] / total_pan_x_pct
            ease_diff = max(ease_diff, abs(z_prog - p_prog))

    total_change_pct = math.hypot(total_zoom_pct, math.hypot(total_pan_x_pct, total_pan_y_pct))

    return {
        "fitted": True,
        "reason": None,
        "frame_count": n,
        "fps": float(fps),
        "zoom_pct": round(total_zoom_pct, 4),
        "pan_x_pct": round(total_pan_x_pct, 4),
        "pan_y_pct": round(total_pan_y_pct, 4),
        "rotation_deg": round(net_rotation_deg, 4),
        "max_abs_rotation_deg": round(max_win_abs_rot, 4),
        "total_change_pct": round(total_change_pct, 4),
        "hold_share": round(hold_share, 4),
        "ease_diff": round(ease_diff, 4),
        "windows": windows,
    }


# ---------------------------------------------------------------------------
# Card validation (`check_shot_cards`)
# ---------------------------------------------------------------------------

_QUOTE_RE = re.compile(r'["“”]([^"“”]+)["“”]')  # straight or curly DOUBLE quotes (an apostrophe is not a quote)
_FORBIDDEN_WORD_RE = re.compile(r"\b(orbit|rotate|rotation|roll|spin|arc)\b", re.IGNORECASE)


def _normalize_text(text: str) -> str:
    """Normalize case, punctuation spacing, and whitespace for cue matching."""
    lowered = text.lower()
    # Collapse all whitespace runs into a single space
    return re.sub(r"\s+", " ", lowered).strip()


def _extract_quoted_fragments(why: str) -> list[str]:
    """Extract non-empty quoted substrings from `camera_why`."""
    matches = _QUOTE_RE.findall(why)
    return [m.strip() for m in matches if m.strip()]


def _resolve_narration_for_shot(
    card: Mapping[str, Any],
    index: int,
    narration: Mapping[Any, str] | Sequence[str] | str | None,
) -> str | None:
    """Resolve the narration string for a shot from a mapping, sequence, or string."""
    if narration is None:
        # Check if the card itself embeds narration text
        for key in ("narration", "narration_text", "voiceover", "vo"):
            val = card.get(key)
            if isinstance(val, str) and val.strip():
                return val
        return None

    if isinstance(narration, str):
        return narration

    if isinstance(narration, Mapping):
        for id_key in ("shot_id", "id", "shot", "number", "index"):
            if id_key in card:
                shot_key = card[id_key]
                if shot_key in narration:
                    return str(narration[shot_key])
                if str(shot_key) in narration:
                    return str(narration[str(shot_key)])
        if index in narration:
            return str(narration[index])
        if str(index) in narration:
            return str(narration[str(index)])
        return None

    if isinstance(narration, Sequence):
        if 0 <= index < len(narration):
            item = narration[index]
            if isinstance(item, str):
                return item
            if isinstance(item, Mapping):
                for key in ("text", "narration", "line", "cue"):
                    if isinstance(item.get(key), str):
                        return item[key]
        return None


def _proposal_hint_mismatch(move: str, why: str, shot_narration: str | None,
                            table: Mapping[str, Mapping[str, Any]] | None = None) -> str | None:
    """CM-05 text if the cue in ``camera_why`` matches a proposal-table row whose moves do not include ``move``."""
    table = table or PROPOSAL_TABLE
    haystack = _normalize_text(why)
    hits = [(row, spec) for row, spec in table.items()
            if any(re.search(rf"\b{re.escape(str(c).lower())}", haystack) for c in spec.get("cues", []))]
    if hits and not any(move in spec.get("moves", []) for _, spec in hits):
        rows = "; ".join(row for row, _ in hits)
        return (f"declared {move!r} disagrees with the proposal table row(s) [{rows}] (a proposal, not the owner's "
                "rule; hypothesis, not binding until the owner has seen it)")
    return None


def check_shot_cards(
    cards: Sequence[Mapping[str, Any]] | Mapping[str, Any],
    narration: Mapping[Any, str] | Sequence[str] | str | None = None,
    *,
    tolerances_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Validate shot cards for camera move compliance (rules CM-01 .. CM-06).

    Accepts either a list/sequence of shot card dicts or a wrapper dict
    containing `"shots"` or `"cards"`. Returns findings ``[{rule, severity, where, detail}]``.
    """
    if isinstance(cards, Mapping):
        if "shots" in cards and isinstance(cards["shots"], Sequence):
            card_list = list(cards["shots"])
        elif "cards" in cards and isinstance(cards["cards"], Sequence):
            card_list = list(cards["cards"])
        else:
            card_list = [cards]
    else:
        card_list = list(cards)

    if not card_list:
        return []

    tolerances = _load_tolerances(tolerances_path)
    same_move_run_max = int(_tol_val(tolerances, "same_move_run_max"))
    proposal_table = tolerances.get("proposal_table", {}).get("rows") or None

    findings: list[dict[str, Any]] = []
    valid_moves_sequence: list[tuple[str, str]] = []  # (shot_label, move)

    for idx, card in enumerate(card_list):
        if not isinstance(card, Mapping):
            findings.append(
                {
                    "rule": "CM-01",
                    "severity": "FAIL",
                    "shot": f"shot_{idx + 1}",
                    "message": "shot card must be a mapping/object",
                }
            )
            continue

        shot_label = str(card.get("shot_id") or card.get("id") or f"shot_{idx + 1}")
        raw_move = card.get("camera_move")
        raw_rot = card.get("camera_rotation_deg", card.get("rotation"))

        # CM-02 check on nonzero camera_rotation_deg even if camera_move is present
        rot_invalid = False
        if raw_rot is not None:
            try:
                rot_val = float(raw_rot)
            except (TypeError, ValueError):
                rot_val = float("nan")
            if math.isnan(rot_val) or abs(rot_val) > 1e-9:
                rot_invalid = True
                findings.append(
                    {
                        "rule": "CM-02",
                        "severity": "FAIL",
                        "shot": shot_label,
                        "message": (
                            f"camera_rotation_deg={raw_rot!r} is forbidden: "
                            "orbit and rotation are forbidden (owner decision 2026-11-20 16:25)"
                        ),
                    }
                )

        # CM-01: camera_move missing, empty, or not a string
        if not isinstance(raw_move, str) or not raw_move.strip():
            findings.append(
                {
                    "rule": "CM-01",
                    "severity": "FAIL",
                    "shot": shot_label,
                    "message": "camera_move is missing, empty, or not a string",
                }
            )
            move_ok = False
            move = ""
        else:
            move = raw_move.strip()
            # CM-02: value outside CAMERA_MOVES
            if move not in CAMERA_MOVES:
                move_ok = False
                msg = _bad_move_message(move)
                findings.append(
                    {
                        "rule": "CM-02",
                        "severity": "FAIL",
                        "shot": shot_label,
                        "message": msg,
                    }
                )
            else:
                move_ok = not rot_invalid
                valid_moves_sequence.append((shot_label, move))

        # CM-03: camera_why missing, empty, or multi-line
        raw_why = card.get("camera_why")
        if not isinstance(raw_why, str) or not raw_why.strip():
            findings.append(
                {
                    "rule": "CM-03",
                    "severity": "FAIL",
                    "shot": shot_label,
                    "message": "camera_why is missing, empty, or not a string",
                }
            )
            continue

        if "\n" in raw_why or "\r" in raw_why:
            findings.append(
                {
                    "rule": "CM-03",
                    "severity": "FAIL",
                    "shot": shot_label,
                    "message": "camera_why must be a single line (no newlines allowed)",
                }
            )
            continue

        # CM-04: camera_why must contain a quoted narration fragment;
        # when narration is provided, the fragment must occur in that shot's text.
        quotes = _extract_quoted_fragments(raw_why)
        shot_narration = _resolve_narration_for_shot(card, idx, narration)

        if not quotes:
            findings.append(
                {
                    "rule": "CM-04",
                    "severity": "FAIL",
                    "shot": shot_label,
                    "message": "camera_why must quote a narration fragment",
                }
            )
        elif shot_narration is None:
            findings.append(
                {
                    "rule": "CM-04",
                    "severity": "REVIEW",
                    "shot": shot_label,
                    "message": "cue not checked against the narration (no narration given)",
                }
            )
        elif shot_narration is not None:
            norm_narr = _normalize_text(shot_narration)
            matched_any = any(_normalize_text(q) in norm_narr for q in quotes)
            if not matched_any:
                findings.append(
                    {
                        "rule": "CM-04",
                        "severity": "FAIL",
                        "shot": shot_label,
                        "message": (
                            f"quoted narration fragment {quotes!r} not found in shot narration "
                            "(after case and whitespace normalization)"
                        ),
                    }
                )

        # CM-05 (REVIEW): move disagrees with proposal keyword table
        if move_ok:
            mismatch = _proposal_hint_mismatch(move, raw_why, shot_narration, proposal_table)
            if mismatch:
                findings.append(
                    {
                        "rule": "CM-05",
                        "severity": "REVIEW",
                        "shot": shot_label,
                        "message": mismatch,
                    }
                )

    # CM-06 (REVIEW): same move on more than same_move_run_max consecutive shots
    if valid_moves_sequence:
        run_move = valid_moves_sequence[0][1]
        run_shots = [valid_moves_sequence[0][0]]
        for shot_label, mv in valid_moves_sequence[1:]:
            if mv == run_move:
                run_shots.append(shot_label)
            else:
                if len(run_shots) > same_move_run_max:
                    findings.append(
                        {
                            "rule": "CM-06",
                            "severity": "REVIEW",
                            "shot": run_shots[-1],
                            "message": (
                                f"camera_move={run_move!r} repeated for {len(run_shots)} consecutive "
                                f"shots ({', '.join(run_shots)}), exceeding same_move_run_max={same_move_run_max}"
                            ),
                        }
                    )
                run_move = mv
                run_shots = [shot_label]
        if len(run_shots) > same_move_run_max:
            findings.append(
                {
                    "rule": "CM-06",
                    "severity": "REVIEW",
                    "shot": run_shots[-1],
                    "message": (
                        f"camera_move={run_move!r} repeated for {len(run_shots)} consecutive "
                        f"shots ({', '.join(run_shots)}), exceeding same_move_run_max={same_move_run_max}"
                    ),
                }
            )

    return [
        {"rule": f["rule"], "severity": f["severity"], "where": f["shot"], "detail": f["message"]} for f in findings
    ]


# ---------------------------------------------------------------------------
# Clip validation (`camera_move_clip`)
# ---------------------------------------------------------------------------


def _sidecar_path(clip_path: Path) -> Path:
    """Return `<clip>.camera.json` sidecar path for a video file."""
    return Path(f"{clip_path}.camera.json")


def _read_declared_move_from_sidecar(clip_path: Path) -> str | None:
    """Read `camera_move` from `<clip>.camera.json` if present."""
    sc = _sidecar_path(clip_path)
    if not sc.is_file():
        sc = clip_path.with_suffix(".camera.json")
    if not sc.is_file():
        return None
    try:
        data = json.loads(sc.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, Mapping):
        mv = data.get("camera_move") or data.get("move")
        if isinstance(mv, str) and mv.strip():
            return mv.strip()
    return None


def camera_move_clip(
    path: str | Path,
    move: str | None = None,
    *,
    fps: int = DEFAULT_FPS,
    tolerances_path: Path | None = None,
    sourced_rules_dirs: Sequence[Path] | None = None,
) -> dict[str, Any]:
    """Validate camera motion in a rendered video clip against its declared move.

    Args:
        path: Path to `.mp4`, `.mov`, `.webm`, or `.mkv` video clip.
        move: Declared camera move from `CAMERA_MOVES`. If None, reads
            `<clip>.camera.json`. If neither supplies a move, returns `NOT_RUN`.
        fps: Frame sampling rate for optical-flow / similarity tracking.
        tolerances_path: Optional override path for `camera_move_tolerances.json`.
        sourced_rules_dirs: Optional search directories for `sourced_rules.json`.

    Returns:
        Result dictionary with `status` (`PASS`, `REVIEW`, `FAIL`, `NOT_RUN`),
        `declared_move`, `measured`, `findings`, and `detail`.
    """
    clip_path = Path(path)

    if clip_path.suffix.lower() not in SUPPORTED_CLIP_KINDS:
        return {
            "status": "NOT_RUN",
            "reason": f"unsupported_clip_kind:{clip_path.suffix.lower()}",
            "declared_move": move,
            "findings": [],
        }

    if not clip_path.is_file():
        return {
            "status": "NOT_RUN",
            "reason": "clip_not_found",
            "declared_move": move,
            "findings": [],
        }

    declared_move = move.strip() if isinstance(move, str) and move.strip() else _read_declared_move_from_sidecar(clip_path)
    if not declared_move:
        return {
            "status": "NOT_RUN",
            "reason": "no_declared_move",
            "declared_move": None,
            "findings": [],
        }

    # Validate declared move name before running OpenCV
    if declared_move not in CAMERA_MOVES:
        msg = _bad_move_message(declared_move, "declared move")
        return {
            "status": "FAIL",
            "value": None,
            "declared_move": declared_move,
            "detail": msg,
            "findings": [{"rule": "CM-02", "severity": "FAIL", "where": str(clip_path.name), "detail": msg}],
        }

    if _cv2() is None or _numpy() is None:
        return {
            "status": "NOT_RUN",
            "reason": "opencv_unavailable",
            "declared_move": declared_move,
            "findings": [],
        }

    frames, effective_fps = decode_grey(clip_path, fps=fps)
    if not frames:
        return {"status": "NOT_RUN", "value": None, "reason": "undecodable", "declared_move": declared_move,
                "detail": "NOT_RUN: the clip could not be decoded", "findings": []}
    if len(frames) < 2:
        return {
            "status": "NOT_RUN",
            "reason": "insufficient_frames",
            "declared_move": declared_move,
            "findings": [],
        }

    measured = measure_camera(frames, fps=effective_fps)
    if not measured.get("fitted"):
        return {
            "status": "NOT_RUN",
            "reason": str(measured.get("reason") or "camera_not_fitted"),
            "declared_move": declared_move,
            "measured": measured,
            "findings": [],
        }

    # Load hypothesis tolerances and sourced rules (SR.T)
    tolerances = _load_tolerances(tolerances_path)
    try:
        sr = SourcedRuleTable.load(sourced_rules_dirs)
        zoom_min_pct = sr.get_number("BP-181", "still_move_min")
        still_drift_min_pct = sr.get_number("BP-215", "still_drift_min_pct")
    except (FileNotFoundError, KeyError) as exc:
        return {
            "status": "NOT_RUN",
            "value": None,
            "reason": "sourced_threshold_missing",
            "declared_move": declared_move,
            "detail": f"NOT_RUN (never a pass): {exc}",
            "findings": [],
        }

    rotation_max_deg = _tol_val(tolerances, "rotation_max_deg")
    pan_min_pct = _tol_val(tolerances, "pan_min_pct")
    pan_none_pct = _tol_val(tolerances, "pan_none_pct")
    zoom_none_pct = _tol_val(tolerances, "zoom_none_pct")
    ease_tol = _tol_val(tolerances, "ease_tol")

    zoom_pct = float(measured["zoom_pct"])
    pan_x_pct = float(measured["pan_x_pct"])
    max_abs_rot = float(measured["max_abs_rotation_deg"])
    total_change_pct = float(measured["total_change_pct"])
    ease_diff = float(measured["ease_diff"])

    findings: list[dict[str, Any]] = []

    # CM-10: |rotation| above rotation_max_deg in clip or any window -> FAIL
    if max_abs_rot > rotation_max_deg:
        findings.append(
            {
                "rule": "CM-10",
                "severity": "FAIL",
                "where": clip_path.name,
                "message": (
                    f"rotation exceeded limit: declared rotation<=0 deg, "
                    f"measured max |rotation|={max_abs_rot:.3f} deg > {rotation_max_deg} deg"
                ),
            }
        )

    # CM-15: the camera never stops: total change under BP-215 still_drift_min_pct -> FAIL
    duration_s = max((int(measured["frame_count"]) - 1) / float(effective_fps or fps), 1e-6)
    change_5s = total_change_pct * (5.0 / duration_s)  # whole clip scaled to 5 s (brief CM-15)
    if change_5s < still_drift_min_pct:
        findings.append(
            {
                "rule": "CM-15",
                "severity": "FAIL",
                "where": clip_path.name,
                "message": (
                    f"camera stopped or static: declared {declared_move}, "
                    f"measured total_change={total_change_pct:.3f}% ({change_5s:.3f}% per 5 s) < BP-215 "
                    f"still_drift_min_pct={still_drift_min_pct}%: the camera stands still, static is not allowed "
                    "(owner 18:10, OR-V24)"
                ),
            }
        )

    expected_pan_sign = TRUCK_L_PAN_SIGN if declared_move in ("truck_l", "truck_zoom_in", "truck_zoom_out") else -TRUCK_L_PAN_SIGN

    # CM-11: zoom_in / zoom_out
    if declared_move == "zoom_in":
        if zoom_pct < zoom_min_pct:
            findings.append(
                {
                    "rule": "CM-11",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected zoom >= +{zoom_min_pct:.2f}%), "
                        f"measured zoom={zoom_pct:+.2f}%, pan_x={pan_x_pct:+.2f}%"
                    ),
                }
            )
        if abs(pan_x_pct) > pan_none_pct:
            findings.append(
                {
                    "rule": "CM-11",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected |pan_x| <= {pan_none_pct:.2f}%), "
                        f"measured pan_x={pan_x_pct:+.2f}%, zoom={zoom_pct:+.2f}%"
                    ),
                }
            )

    elif declared_move == "zoom_out":
        if zoom_pct > -zoom_min_pct:
            findings.append(
                {
                    "rule": "CM-11",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected zoom <= -{zoom_min_pct:.2f}%), "
                        f"measured zoom={zoom_pct:+.2f}%, pan_x={pan_x_pct:+.2f}%"
                    ),
                }
            )
        if abs(pan_x_pct) > pan_none_pct:
            findings.append(
                {
                    "rule": "CM-11",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected |pan_x| <= {pan_none_pct:.2f}%), "
                        f"measured pan_x={pan_x_pct:+.2f}%, zoom={zoom_pct:+.2f}%"
                    ),
                }
            )

    # CM-12: truck_l / truck_r
    elif declared_move in ("truck_l", "truck_r"):
        signed_pan = pan_x_pct * expected_pan_sign
        if signed_pan < pan_min_pct:
            findings.append(
                {
                    "rule": "CM-12",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected pan_x sign {expected_pan_sign:+.0f} "
                        f"with |pan_x| >= {pan_min_pct:.2f}%), "
                        f"measured pan_x={pan_x_pct:+.2f}%, zoom={zoom_pct:+.2f}%"
                    ),
                }
            )
        if abs(zoom_pct) > zoom_none_pct:
            findings.append(
                {
                    "rule": "CM-12",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected |zoom| <= {zoom_none_pct:.2f}%), "
                        f"measured zoom={zoom_pct:+.2f}%, pan_x={pan_x_pct:+.2f}%"
                    ),
                }
            )

    # CM-13 & CM-14: truck_zoom_in / truck_zoom_out
    elif declared_move in ("truck_zoom_in", "truck_zoom_out"):
        # the enum has no left/right form for the combined moves: either direction of pan is a truck
        zoom_ok = zoom_pct >= zoom_min_pct if declared_move == "truck_zoom_in" else zoom_pct <= -zoom_min_pct
        pan_ok = abs(pan_x_pct) >= pan_min_pct
        if not (zoom_ok and pan_ok):
            expected_zoom_str = f">= +{zoom_min_pct:.2f}%" if declared_move == "truck_zoom_in" else f"<= -{zoom_min_pct:.2f}%"
            findings.append(
                {
                    "rule": "CM-13",
                    "severity": "FAIL",
                    "message": (
                        f"declared {declared_move} (expected |pan_x| "
                        f">= {pan_min_pct:.2f}% and zoom {expected_zoom_str}), "
                        f"measured pan_x={pan_x_pct:+.2f}%, zoom={zoom_pct:+.2f}%"
                    ),
                }
            )
        elif ease_diff > ease_tol:
            # CM-14 (REVIEW): pan and zoom progress per window differ by more than ease_tol
            findings.append(
                {
                    "rule": "CM-14",
                    "severity": "REVIEW",
                    "message": (
                        f"combined move {declared_move} easing mismatch: "
                        f"window progress diff={ease_diff:.3f} > ease_tol={ease_tol:.3f}"
                    ),
                }
            )

    for f in findings:  # repo shape {rule, severity, where, detail}
        f["detail"] = f.pop("message")
        f["where"] = clip_path.name
    has_fail = any(f["severity"] == "FAIL" for f in findings)
    has_review = any(f["severity"] == "REVIEW" for f in findings)
    status = "FAIL" if has_fail else ("REVIEW" if has_review else "PASS")

    detail = (
        f"declared={declared_move}; measured zoom={zoom_pct:+.2f}%, pan_x={pan_x_pct:+.2f}%, "
        f"max_abs_rot={max_abs_rot:.3f}deg, ease_diff={ease_diff:.3f}. "
        "global camera fit, depth parallax not measured."
    )

    return {
        "status": status,
        "value": round(total_change_pct, 4),
        "declared_move": declared_move,
        "measured": measured,
        "findings": findings,
        "detail": detail,
    }


# ---------------------------------------------------------------------------
# CLI entrypoint (`main(argv)`)
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="camera_move",
        description="Validate camera moves on shot cards or rendered video clips.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_cards = sub.add_parser("cards", help="Validate shot cards JSON.")
    p_cards.add_argument("cards_path", help="Path to shot cards JSON file.")
    p_cards.add_argument(
        "--narration",
        default=None,
        help="Optional path to narration JSON mapping/list or text file.",
    )
    p_cards.add_argument(
        "--tolerances",
        default=None,
        help="Optional path to camera_move_tolerances.json.",
    )

    p_clip = sub.add_parser("clip", help="Validate camera move on a video clip.")
    p_clip.add_argument("clip_path", help="Path to video clip (.mp4, .mov, .webm, .mkv).")
    p_clip.add_argument(
        "--move",
        default=None,
        help="Declared camera move (overrides <clip>.camera.json).",
    )
    p_clip.add_argument(
        "--fps",
        type=int,
        default=DEFAULT_FPS,
        help=f"Sampling FPS for optical flow tracking (default: {DEFAULT_FPS}).",
    )
    p_clip.add_argument(
        "--tolerances",
        default=None,
        help="Optional path to camera_move_tolerances.json.",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entrypoint. Exit codes: 0 on PASS/REVIEW/NOT_RUN, 1 on FAIL, 2 on error."""
    parser = _build_parser()
    try:
        args = parser.parse_args(list(argv) if argv is not None else None)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 2
        return 0 if code == 0 else 2

    try:
        if args.command == "cards":
            cards_file = Path(args.cards_path)
            if not cards_file.is_file():
                print(json.dumps({"error": f"cards file not found: {cards_file}"}), file=sys.stderr)
                return 2
            cards_data = json.loads(cards_file.read_text(encoding="utf-8"))

            narration_data: Any = None
            if args.narration:
                narr_file = Path(args.narration)
                if not narr_file.is_file():
                    print(json.dumps({"error": f"narration file not found: {narr_file}"}), file=sys.stderr)
                    return 2
                raw_text = narr_file.read_text(encoding="utf-8")
                try:
                    narration_data = json.loads(raw_text)
                except json.JSONDecodeError:
                    narration_data = raw_text

            tol_path = Path(args.tolerances) if args.tolerances else None
            result = check_shot_cards(cards_data, narration=narration_data, tolerances_path=tol_path)

        elif args.command == "clip":
            tol_path = Path(args.tolerances) if args.tolerances else None
            result = camera_move_clip(
                args.clip_path,
                move=args.move,
                fps=args.fps,
                tolerances_path=tol_path,
            )
        else:
            return 2

    except Exception as exc:
        print(json.dumps({"error": str(exc)}), file=sys.stderr)
        return 2

    if args.command == "cards":
        for f in result:
            print(f"[{f['severity']}] {f['rule']} {f['where']}: {f['detail']}")
        if not result:
            print("PASS: no findings")
        return 1 if any(f["severity"] == "FAIL" for f in result) else 0
    print(f"{result['status']}: {result.get('detail') or result.get('reason', '')}")
    for f in result.get("findings", []):
        print(f"[{f['severity']}] {f['rule']}: {f.get('detail') or f.get('message')}")
    if result.get("reason") == "undecodable":
        return 2
    return 1 if result.get("status") == "FAIL" else 0


if __name__ == "__main__":
    sys.exit(main())
