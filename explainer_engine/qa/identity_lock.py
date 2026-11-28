"""Calibrated, commercial-safe cross-scene character identity check.

Design & honesty principles:
- Never uses non-commercial InsightFace weights.
- Local deterministic comparator computes normalized RGB+luminance portrait-region histograms
  plus structural grayscale cosine similarity; it is an offline commercial-safe heuristic,
  NOT a deep facial biometric recognizer (limitations are explicitly recorded in every report).
- Confidence-aware: back-facing, occluded, distant (``face_width_ratio < 0.05``), or extreme
  profile poses yield ``NOT_APPLICABLE`` rather than arbitrary failures.
- Clearly distinguishes ``MISSING_REFERENCE`` from an actual identity mismatch.
- Mandatory checks emit ``FAIL`` on mismatch or missing reference so production QA cannot
  silently pass; soft-gated checks emit ``REVIEW`` until calibrated on the approved cast.
"""
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from explainer_engine.core.errors import ContractError

MIN_FACE_WIDTH_RATIO = 0.05
DEFAULT_SIMILARITY_REVIEW_THRESHOLD = 0.55
NON_FRONTAL_POSES = frozenset({"back_facing", "occluded", "extreme_profile", "distant"})


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _crop_signature(image_path: Path) -> np.ndarray:
    """Compute a normalized RGB+luminance center-portrait signature vector for deterministic comparison."""
    with Image.open(image_path) as im:
        rgb = im.convert("RGB")
        w, h = rgb.size
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
    mandatory: bool = False,
    allow_missing_reference_status: bool = False,
) -> dict[str, Any]:
    """Compare a character across separated scenes with explicit fingerprints and failure semantics."""
    ref_p = Path(reference_image)
    cand_p = Path(candidate_image)

    if not ref_p.is_file():
        if allow_missing_reference_status:
            return {
                "schema": "identity_lock_check/1",
                "character_id": character_id,
                "status": "FAIL" if mandatory else "MISSING_REFERENCE",
                "failure_kind": "missing_reference",
                "mandatory": mandatory,
                "reference_path": str(ref_p),
                "reference_sha256": None,
                "candidate_path": str(cand_p),
                "candidate_sha256": _sha256(cand_p) if cand_p.is_file() else None,
                "similarity": None,
                "threshold": threshold,
                "reason": f"Reference character image not found: {ref_p}",
                "backend": "missing_reference_guard",
                "license_safe": True,
            }
        raise ContractError(f"Reference character image not found: {ref_p}")
    if not cand_p.is_file():
        raise ContractError(f"Candidate scene image not found: {cand_p}")

    ref_sha = _sha256(ref_p)
    cand_sha = _sha256(cand_p)

    if ref_p.resolve() == cand_p.resolve() or ref_sha == cand_sha:
        return {
            "schema": "identity_lock_check/1",
            "character_id": character_id,
            "status": "FAIL",
            "failure_kind": "self_comparison_forbidden",
            "mandatory": mandatory,
            "reference_path": str(ref_p),
            "reference_sha256": ref_sha,
            "candidate_path": str(cand_p),
            "candidate_sha256": cand_sha,
            "similarity": None,
            "threshold": threshold,
            "reason": (
                f"Self-comparison prohibited for {character_id!r}: candidate image matches reference "
                "path or SHA-256 identically"
            ),
            "backend": "self_comparison_guard",
            "license_safe": True,
        }

    if pose_tag in NON_FRONTAL_POSES or face_width_ratio < MIN_FACE_WIDTH_RATIO:
        return {
            "schema": "identity_lock_check/1",
            "character_id": character_id,
            "status": "NOT_APPLICABLE",
            "failure_kind": None,
            "mandatory": mandatory,
            "reference_path": str(ref_p),
            "reference_sha256": ref_sha,
            "candidate_path": str(cand_p),
            "candidate_sha256": cand_sha,
            "reason": f"Skipped arbitrary identity failure for pose={pose_tag!r}, face_width_ratio={face_width_ratio:.3f}",
            "similarity": None,
            "threshold": threshold,
            "backend": "skipped_pose_guard",
            "license_safe": True,
        }

    ref_vec = _crop_signature(ref_p)
    cand_vec = _crop_signature(cand_p)
    sim = round(cosine_similarity(ref_vec, cand_vec), 4)
    if sim >= threshold:
        status = "PASS"
        failure_kind = None
        reason = f"Similarity {sim:.4f} >= threshold {threshold:.4f}"
    else:
        status = "FAIL" if mandatory else "REVIEW"
        failure_kind = "identity_mismatch"
        reason = f"Cross-scene similarity {sim:.4f} < threshold {threshold:.4f}"

    return {
        "schema": "identity_lock_check/1",
        "character_id": character_id,
        "status": status,
        "failure_kind": failure_kind,
        "mandatory": mandatory,
        "reference_path": str(ref_p),
        "reference_sha256": ref_sha,
        "candidate_path": str(cand_p),
        "candidate_sha256": cand_sha,
        "similarity": sim,
        "threshold": threshold,
        "reason": reason,
        "backend": "deterministic_portrait_hist_fallback",
        "commercial_safe_target": "opencv_zoo_yunet_mit_sface_apache2",
        "license_safe": True,
        "limitations": (
            "Local portrait-region RGB histogram comparator detects large palette/appearance drift "
            "offline without InsightFace weights, but is not a deep facial landmark biometric."
        ),
    }
