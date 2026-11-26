"""Fail-closed Multimodal AI Media Critic Gate (``ai_critic_verdict/1``).

Enforces that every component showcase (bridges, maps, 2.5D, audio, LTX scene) and every
final master film has been **actually watched and listened to** by a Clean-Room AI Media
Critic whose structured verdict JSON is cryptographically pinned to the exact 64-char
SHA-256 of the rendered media file on disk.

Zero silent bypasses:
- Missing verdict file -> FAIL.
- SHA-256 mismatch (stale verdict after re-render) -> FAIL.
- Any ``critical`` defect -> FAIL.
- ``overall_score < min_overall_score`` (default 8.5) -> FAIL.
- Any dimension sub-score ``< min_subscore`` (default 7.5) -> FAIL.
- ``audio_visual_sync_verified`` not ``True`` (for video/audio components) -> FAIL.
- ``verdict != "APPROVE"`` -> FAIL.
"""
from __future__ import annotations

import hashlib
import json
import re
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
TIMECODE_RE = re.compile(r"^[0-9]{2}:[0-9]{2}(\.[0-9]+)?(-[0-9]{2}:[0-9]{2}(\.[0-9]+)?)?$")

VALID_COMPONENTS = frozenset(
    {
        "bridges",
        "maps",
        "fx25d",
        "audio",
        "ltx_scene",
        "storyboard",
        "final_film",
        "youtube_ab_packaging",
    }
)
VALID_VERDICTS = frozenset({"APPROVE", "REJECT", "NEEDS_REMEDIATION"})
VALID_SEVERITIES = frozenset({"critical", "major", "minor"})

AUDIO_FREE_COMPONENTS = frozenset({"storyboard", "youtube_ab_packaging"})

RUBRIC_DIMENSIONS_BY_COMPONENT: dict[str, tuple[str, ...]] = {
    "bridges": (
        "modern_design_craft",
        "typography_hierarchy",
        "motion_fluidity",
        "mobile_readability",
        "visual_integration",
    ),
    "maps": (
        "geographic_clarity",
        "cartographic_aesthetics",
        "camera_and_route_motion",
        "label_readability_no_collision",
        "audio_sfx_balance",
    ),
    "fx25d": (
        "depth_realism_no_warp",
        "optical_bokeh_and_lighting",
        "atmospheric_motion",
        "subject_appropriateness",
        "color_grade_cohesion",
    ),
    "audio": (
        "narrator_voice_naturalness",
        "pronunciation_and_pacing",
        "music_emotional_arc",
        "scene_ambience_and_foley_sync",
        "mix_dynamics_no_pumping",
    ),
    "ltx_scene": (
        "multi_angle_set_consistency",
        "character_identity_lock",
        "acting_and_physics_realism",
        "shot_progression_and_handles",
        "audio_visual_sync",
    ),
    "storyboard": (
        "environment_consistency",
        "character_identity_lock",
        "cinematic_framing_variety",
        "lighting_and_lens_cohesion",
    ),
    "final_film": (
        "hook_and_retention_pull",
        "realism_and_style_cohesion",
        "motion_and_acting_naturalness",
        "maps_and_bridges_craft",
        "edit_rhythm_and_cuts",
        "narrator_voice_and_pacing",
        "audio_visual_sync",
        "music_and_soundscape_dynamics",
        "color_and_grade_unity",
        "payoff_and_youtube_readiness",
    ),
    "youtube_ab_packaging": (
        "mobile_3sec_readability",
        "ctr_curiosity_gap",
        "photoreal_thumbnail_craft",
        "title_hook_alignment",
    ),
}


def sha256_file(path: Path) -> str:
    """Compute lowercase 64-character SHA-256 digest of ``path``."""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def build_inspection_proxy(
    media_path: Path,
    proxy_out: Path,
    *,
    max_width: int = 1280,
    crf: int = 23,
) -> Path:
    """Build a compact <=40MB full-audio inspection proxy MP4 for multimodal AI review."""
    if not media_path.is_file():
        raise FileNotFoundError(f"Media file not found: {media_path}")
    proxy_out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-i",
        str(media_path),
        "-vf",
        f"scale='min({max_width},iw)':-2:flags=lanczos",
        "-c:v",
        "libx264",
        "-preset",
        "fast",
        "-crf",
        str(crf),
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(proxy_out),
    ]
    subprocess.run(cmd, check=True)
    return proxy_out


def verify_ai_critic_verdict(
    media_path: Path,
    verdict_path: Path,
    *,
    expected_component: str | None = None,
    min_overall_score: float = 8.5,
    min_subscore: float = 7.5,
    require_audio_sync: bool | None = None,
) -> dict[str, Any]:
    """Verify a Clean-Room AI Media Critic verdict file fail-closed against ``media_path``."""
    findings: list[str] = []
    if not media_path.is_file():
        return {
            "status": "FAIL",
            "findings": [f"Target media file does not exist: {media_path}"],
        }
    if not verdict_path.is_file():
        return {
            "status": "FAIL",
            "findings": [f"Mandatory AI Critic verdict missing: {verdict_path}"],
        }

    try:
        data = json.loads(verdict_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "status": "FAIL",
            "findings": [f"Malformed AI Critic verdict JSON ({verdict_path}): {exc}"],
        }

    if not isinstance(data, dict):
        return {"status": "FAIL", "findings": ["AI Critic verdict root must be a JSON object"]}

    if data.get("schema") != "ai_critic_verdict/1":
        findings.append(f"Invalid schema {data.get('schema')!r}; expected 'ai_critic_verdict/1'")

    component = str(data.get("component", ""))
    if component not in VALID_COMPONENTS:
        findings.append(f"Invalid component {component!r}")
    if expected_component and component != expected_component:
        findings.append(f"Component mismatch: expected {expected_component!r}, got {component!r}")

    actual_sha = sha256_file(media_path)
    recorded_sha = str(data.get("video_sha256", "")).strip().lower()
    if not SHA256_RE.match(recorded_sha):
        findings.append("video_sha256 must be a valid 64-character lowercase hex digest")
    elif recorded_sha != actual_sha:
        findings.append(
            f"Stale/mismatched AI Critic verdict SHA-256: verdict={recorded_sha[:12]} != media={actual_sha[:12]}"
        )

    verdict_val = str(data.get("verdict", ""))
    if verdict_val not in VALID_VERDICTS:
        findings.append(f"Invalid verdict enum: {verdict_val!r}")
    elif verdict_val != "APPROVE":
        findings.append(f"AI Critic did not approve media (verdict={verdict_val!r})")

    try:
        overall = float(data["overall_score"])
    except (KeyError, TypeError, ValueError):
        overall = 0.0
        findings.append("Missing or non-numeric overall_score")
    if overall < min_overall_score:
        findings.append(f"overall_score {overall:.2f} < required {min_overall_score:.2f}")

    scores = data.get("scores")
    if not isinstance(scores, dict) or len(scores) < 4:
        findings.append("scores must be an object with at least 4 rated dimensions")
    else:
        required_dims = RUBRIC_DIMENSIONS_BY_COMPONENT.get(component, ())
        for dim in required_dims:
            if dim not in scores:
                findings.append(f"Missing required rubric dimension {dim!r} for component {component!r}")
        for dim, val in scores.items():
            try:
                fval = float(val)
            except (TypeError, ValueError):
                findings.append(f"Non-numeric score for {dim!r}: {val!r}")
                continue
            if not (0.0 <= fval <= 10.0):
                findings.append(f"Score out of [0,10] range for {dim!r}: {fval}")
            elif fval < min_subscore:
                findings.append(f"Sub-score {dim!r}={fval:.2f} < required {min_subscore:.2f}")

    need_sync = (component not in AUDIO_FREE_COMPONENTS) if require_audio_sync is None else require_audio_sync
    sync_flag = data.get("audio_visual_sync_verified")
    if not isinstance(sync_flag, bool):
        findings.append("audio_visual_sync_verified must be a strict boolean")
    elif need_sync and not sync_flag:
        findings.append("audio_visual_sync_verified is False — audiovisual sync not verified")

    defects = data.get("defects")
    critical_count = 0
    major_count = 0
    if not isinstance(defects, list):
        findings.append("defects must be a JSON array")
    else:
        for i, d in enumerate(defects):
            if not isinstance(d, dict):
                findings.append(f"defects[{i}] must be an object")
                continue
            sev = str(d.get("severity", ""))
            tc = str(d.get("timecode", ""))
            if sev not in VALID_SEVERITIES:
                findings.append(f"defects[{i}] invalid severity {sev!r}")
            if not TIMECODE_RE.match(tc):
                findings.append(f"defects[{i}] invalid timecode {tc!r}")
            if sev == "critical":
                critical_count += 1
                findings.append(
                    f"CRITICAL defect at {tc} [{d.get('category', 'unknown')}]: {d.get('description', '')}"
                )
            elif sev == "major":
                major_count += 1

    return {
        "status": "PASS" if not findings else "FAIL",
        "component": component,
        "media_sha256": actual_sha,
        "overall_score": round(overall, 2),
        "verdict": verdict_val,
        "critical_defects": critical_count,
        "major_defects": major_count,
        "findings": findings,
    }


def make_verdict_template(
    *,
    component: str,
    media_path: Path,
    duration_s: float,
    inspector_role: str = "Clean-Room AI Media Critic",
) -> dict[str, Any]:
    """Create a schema-valid starter verdict skeleton pinned to ``media_path`` SHA-256."""
    dims = RUBRIC_DIMENSIONS_BY_COMPONENT.get(component, ("quality", "craft", "sync", "cohesion"))
    return {
        "schema": "ai_critic_verdict/1",
        "component": component,
        "video_path": str(media_path),
        "video_sha256": sha256_file(media_path),
        "duration_s": round(float(duration_s), 3),
        "inspected_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "inspector_role": inspector_role,
        "overall_score": 0.0,
        "verdict": "NEEDS_REMEDIATION",
        "audio_visual_sync_verified": False,
        "scores": {d: 0.0 for d in dims},
        "defects": [],
        "strengths": [],
        "remediation_actions": [],
    }
