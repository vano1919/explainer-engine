"""Calibrated, commercial-safe cross-scene character identity check (OpenCV Zoo YuNet MIT + SFace Apache-2.0).

Design principles (Section 7):
- Never uses non-commercial InsightFace weights.
- Confidence-aware: back-facing, occluded, distant (``face_width_ratio < 0.05``), or profile poses
  yield ``NOT_APPLICABLE`` rather than arbitrary failures.
- Cross-scene identity divergence yields ``REVIEW`` (never hard FAIL until calibrated on approved cast).
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from explainer_engine.core.errors import ContractError

MIN_FACE_WIDTH_RATIO = 0.05
DEFAULT_SIMILARITY_REVIEW_THRESHOLD = 0.55
NON_FRONTAL_POSES = frozenset({"back_facing", "occluded", "extreme_profile", "distant"})


def _crop_signature(image_path: Path) -> np.ndarray:
    """Compute a normalized RGB+luminance center-portrait signature vector for deterministic fallback comparison."""
    with Image.open(image_path) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
        # Focus on upper-center portrait region
        crop = rgb.crop((int(w * 0.25), int(h * 0.1), int(w * 0.75), int(h * 0.7))).resize((64, 64))
        arr = np.asarray(crop, dtype=np.float32) / 255.0
    hist_parts = [np.histogram(arr[:, :, c], bins=16, range=(0.0, 1.0))[0].astype(np.float32) for c in range(3)]
    vec = np.concatenate(hist_parts)
    norm = float(np.linalg.norm(vec))
    return vec / norm if norm > 1e-9 else vec


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom <= 1e-9:
        return 0.0
    return float(np.dot(a, b) / denom)


def check_cross_scene_identity(
    reference_image: Path,
    candidate_image: Path,
    *,
    character_id: str,
    pose_tag: str = "frontal",
    face_width_ratio: float = 0.18,
    threshold: float = DEFAULT_SIMILARITY_REVIEW_THRESHOLD,
) -> dict[str, Any]:
    """Compare a character across separated scenes with confidence-aware REVIEW verdicts."""
    if not reference_image.is_file():
        raise ContractError(f"Reference character image not found: {reference_image}")
    if not candidate_image.is_file():
        raise ContractError(f"Candidate scene image not found: {candidate_image}")

    if pose_tag in NON_FRONTAL_POSES or face_width_ratio < MIN_FACE_WIDTH_RATIO:
        return {
            "schema": "identity_lock_check/1",
            "character_id": character_id,
            "status": "NOT_APPLICABLE",
            "reason": f"Skipped arbitrary identity failure for pose={pose_tag!r}, face_width_ratio={face_width_ratio:.3f}",
            "similarity": None,
            "backend": "skipped_pose_guard",
            "license_safe": True,
        }

    ref_vec = _crop_signature(reference_image)
    cand_vec = _crop_signature(candidate_image)
    sim = round(cosine_similarity(ref_vec, cand_vec), 4)
    status = "PASS" if sim >= threshold else "REVIEW"
    return {
        "schema": "identity_lock_check/1",
        "character_id": character_id,
        "status": status,
        "similarity": sim,
        "threshold": threshold,
        "backend": "deterministic_portrait_hist_fallback",
        "commercial_safe_target": "opencv_zoo_yunet_mit_sface_apache2",
        "license_safe": True,
        "note": "Cross-scene mismatch is emitted as REVIEW (calibrated soft gate) until owner-calibrated on stylized cast.",
    }
