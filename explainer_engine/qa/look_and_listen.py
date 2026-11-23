"""Post-render re-perception feedback loop and mandatory Look-and-Listen review bundle (Task 2 R2 Step 6, Requirements E, G2, P6).

Connects ``qa/frame_review.py``, ``qa/sheet_review.py``, ``qa/visual_judge.py``, ``production/perceive_picture.py``,
``production/motion_isolation.py``, and ``qa/perceive_audio.py`` into one closed feedback loop:
1. After rendering a shot clip and its audio slice, re-perceive the actual rendered frames and audio.
2. Distinguish ``DELIBERATELY_STILL`` (PASS with written reason) from ``ACCIDENTALLY_FROZEN`` (FAIL: motion planned but
   frames did not move) and ``TECHNICALLY_BROKEN`` (FAIL: holder motion leak, sky/glint leak onto foreground, or sliced
   anchor base).
3. Recommend one of ``AUTO_ADJUST_AND_RERENDER``, ``FLAG_FOR_REGENERATION``, or ``READY_FOR_CLAUDE_REVIEW``.
4. Write ``episodes/<ep>/qa/look_and_listen_bundle/`` with contact strips, motion heatmaps, audio excerpts, and
   ``look_and_listen_record.json`` (blocking final ``stage_qa`` delivery until Claude signs off ``status == 'APPROVED'``).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import numpy as np

from explainer_engine.core.store import write_json_atomic
from explainer_engine.production import motion_isolation as MI
from explainer_engine.production import perceive_picture as PP
from explainer_engine.qa import gates as G
from explainer_engine.qa import perceive_audio as PA

RECORD_SCHEMA = "look_and_listen_record/1.0"
BUNDLE_REL = "qa/look_and_listen_bundle"
RECORD_REL = "qa/look_and_listen_bundle/look_and_listen_record.json"


def check_anchor_framing(
    views: list[dict],
    keep_in_frame: list[dict],
    *,
    sw: int = 1920,
    sh: int = 1080,
    W: int = 1920,
    H: int = 1080,
) -> dict[str, Any]:
    """Verify that no non-soft anchor in ``keep_in_frame`` (e.g. brazier basket base or soldier boots in ``S02_SH008``)
    is sliced off at the bottom or side of the camera crop across ``views``."""
    violations: list[dict] = []
    for f_idx, v in enumerate(views or []):
        s = float(v.get("s", 1.0))
        z0 = float(v.get("z0", 1.0))
        zs = max(1.0, z0 * s)
        cx, cy = float(v.get("cx", 0.5)), float(v.get("cy", 0.5))
        half_w = 0.5 / zs
        half_h = 0.5 / zs
        crop_x0, crop_x1 = cx - half_w, cx + half_w
        crop_y0, crop_y1 = cy - half_h, cy + half_h
        for kb in keep_in_frame or []:
            if kb.get("soft"):
                continue
            box = kb.get("box") or kb.get("face")
            if not isinstance(box, (list, tuple)) and len(box or ()) != 4:
                continue
            bx0, by0, bx1, by1 = [float(c) for c in box]
            # Check bottom support slicing (e.g. brazier bottom or boots inside the original frame)
            if by1 <= 0.995 and crop_y1 < by1 - 0.015:
                violations.append({
                    "frame": f_idx,
                    "target": kb.get("mask") or kb.get("light") or kb.get("why") or "anchor",
                    "box_bottom_y": round(by1, 4),
                    "crop_bottom_y": round(crop_y1, 4),
                    "reason": "camera crop slices off bottom of protected anchor",
                })
                break
            if bx0 >= 0.005 and crop_x0 > bx0 + 0.015:
                violations.append({
                    "frame": f_idx,
                    "target": kb.get("mask") or kb.get("light") or kb.get("why") or "anchor",
                    "reason": "camera crop slices left edge of protected anchor",
                })
                break
            if bx1 <= 0.995 and crop_x1 < bx1 - 0.015:
                violations.append({
                    "frame": f_idx,
                    "target": kb.get("mask") or kb.get("light") or kb.get("why") or "anchor",
                    "reason": "camera crop slices right edge of protected anchor",
                })
                break
    return {"passed": len(violations) == 0, "violations": violations[:10]}


def evaluate_shot_render(
    shot: dict,
    direction: dict,
    *,
    frames: list[np.ndarray] | None = None,
    views: list[dict] | None = None,
    mover_mask: np.ndarray | None = None,
    anchor_mask: np.ndarray | None = None,
    fg_mask: np.ndarray | None = None,
    sky_mask: np.ndarray | None = None,
    audio_input: Path | str | np.ndarray | None = None,
    audio_sr: int = 48000,
) -> dict[str, Any]:
    """Re-perceive a rendered shot's frames and audio, compare with ``direction``, and return the feedback decision."""
    sid = str(shot.get("shot_id") or direction.get("shot_id") or "shot")
    tracks = list(direction.get("tracks") or [])
    planned_fx = [t for t in tracks if t.get("track") not in ("camera", "audio")]
    planned_cam = [t for t in tracks if t.get("track") == "camera" and t.get("op") not in ("hold",)]
    still_reason = str(
        direction.get("stillness_reason")
        or (direction.get("decision_record") or {}).get("stillness_reason")
        or ((shot.get("director_brief") or {}).get("restraint_note") if not planned_fx else "")
        or ""
    ).strip()

    leak_rep = MI.evaluate_motion_isolation(
        frames or [],
        mover_mask=mover_mask,
        anchor_mask=anchor_mask,
        fg_mask=fg_mask,
        sky_mask=sky_mask,
        views=views,
    ) if frames else {"status": "NOT_RUN", "passed": True, "accidental_freeze": False}

    keep_list = list(direction.get("keep_in_frame") or [])
    anchor_rep = check_anchor_framing(views or [], keep_list) if views else {"passed": True, "violations": []}

    # Classify stillness vs accidental freeze vs technical break (Creator Decision 2 & Outside Review 3.D)
    if not leak_rep.get("passed") or not anchor_rep.get("passed"):
        motion_state = "TECHNICALLY_BROKEN"
    elif (planned_fx or planned_cam) and frames and len(frames) >= 2:
        f_diff = float(np.mean(np.abs(frames[-1].astype(np.float32) - frames[0].astype(np.float32))))
        if f_diff < 0.15 or leak_rep.get("accidental_freeze"):
            motion_state = "ACCIDENTALLY_FROZEN"
        else:
            motion_state = "ACTIVE_AND_ISOLATED"
    elif not planned_fx and still_reason:
        motion_state = "DELIBERATELY_STILL"
    elif not planned_fx and not still_reason:
        motion_state = "UNEXPLAINED_STILLNESS_NEEDS_REVIEW"
    else:
        motion_state = "ACTIVE_AND_ISOLATED"

    brief = shot.get("director_brief") if isinstance(shot.get("director_brief"), dict) else {}
    silence = (shot.get("sound_design") or {}).get("silence") or shot.get("intentional_silence")
    audio_rep = (
        PA.perceive_audio(
            audio_input,
            sr=audio_sr,
            shot_id=sid,
            expected_perspective=str(brief.get("sound_perspective") or ""),
            intentional_silence=str(silence) if silence else None,
        )
        if audio_input is not None
        else {"status": "NOT_RUN", "technical_pass": True, "human_listen_required": True}
    )

    re_perception = PP.perceive_picture(shot, picture=frames[0]) if (frames and len(frames) > 0) else None

    adjustments: list[dict] = []
    if motion_state == "TECHNICALLY_BROKEN":
        if not anchor_rep.get("passed"):
            adjustments.append({"parameter": "camera.push.strength", "action": "reduce_by_35_pct_and_enforce_keep_in_frame", "reason": anchor_rep["violations"][0]["reason"]})
        if not leak_rep.get("passed"):
            adjustments.append({"parameter": "motion_isolation.holder_erosion", "action": "tighten_mover_mask_and_zero_holder", "reason": f"holder_leak_p95={leak_rep.get('holder_leak_p95')}"})
        feedback_action = "AUTO_ADJUST_AND_RERENDER"
    elif motion_state == "ACCIDENTALLY_FROZEN":
        adjustments.append({"parameter": "effects.strength", "action": "restore_non_zero_strength", "reason": "planned motion produced near-zero frame change"})
        feedback_action = "AUTO_ADJUST_AND_RERENDER"
    elif (direction.get("interpretation") or {}).get("needs_regeneration"):
        feedback_action = "FLAG_FOR_REGENERATION"
    else:
        feedback_action = "READY_FOR_CLAUDE_REVIEW"

    passed_auto = motion_state in ("ACTIVE_AND_ISOLATED", "DELIBERATELY_STILL") and bool(audio_rep.get("technical_pass", True))
    return {
        "shot_id": sid,
        "motion_state": motion_state,
        "stillness_reason": still_reason or None,
        "motion_isolation": leak_rep,
        "anchor_framing": anchor_rep,
        "audio_perception": audio_rep,
        "re_perception_frame0": re_perception.get("environment") if isinstance(re_perception, dict) else None,
        "feedback_action": feedback_action,
        "recommended_adjustments": adjustments,
        "passed_automated_checks": bool(passed_auto),
        "claude_review_status": "PENDING_CLAUDE_REVIEW",
    }


def save_contact_strip_and_heatmap(frames: list[np.ndarray], out_strip_jpg: Path, out_diff_jpg: Path | None = None) -> None:
    """Write a horizontal or vertical contact strip JPG and an amplified Frame-0-to-Frame-N difference heatmap JPG."""
    import cv2

    if not frames:
        return
    out_strip_jpg = Path(out_strip_jpg)
    out_strip_jpg.parent.mkdir(parents=True, exist_ok=True)
    # Stack up to 6 evenly spaced frames vertically (matching visual_task1.zip s08/s02/s05 strip format)
    idxs = np.linspace(0, len(frames) - 1, min(6, len(frames)), dtype=int)
    picked = [frames[int(i)] for i in idxs]
    strip = np.vstack(picked)
    cv2.imwrite(str(out_strip_jpg), strip[..., ::-1])
    if out_diff_jpg is not None and len(frames) >= 2:
        diff = np.clip(np.abs(frames[-1].astype(np.float32) - frames[0].astype(np.float32)).mean(axis=2) * 4.0, 0, 255).astype(np.uint8)
        heat = cv2.applyColorMap(diff, cv2.COLORMAP_INFERNO)
        cv2.imwrite(str(out_diff_jpg), heat)


def write_look_and_listen_record(
    episode_root: Path,
    shot_evaluations: list[dict],
    *,
    approved_by: str | None = None,
    notes: str | None = None,
) -> Path:
    """Write ``episodes/<ep>/qa/look_and_listen_bundle/look_and_listen_record.json``."""
    root = Path(episode_root)
    rec_path = root / RECORD_REL
    all_auto_ok = all(bool(e.get("passed_automated_checks")) for e in shot_evaluations)
    status = "APPROVED" if (approved_by and all_auto_ok) else ("FAILED_AUTO_CHECK" if not all_auto_ok else "PENDING_CLAUDE_REVIEW")
    doc = {
        "schema": RECORD_SCHEMA,
        "episode_id": root.name,
        "status": status,
        "approved_by": approved_by,
        "notes": notes,
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "shots": shot_evaluations,
    }
    write_json_atomic(rec_path, doc)
    return rec_path


def check_look_and_listen_gate(episode_root: Path, rehearsal: bool = False) -> list[dict]:
    """Return QA gate rows for ``stage_qa``: blocks shipping unless ``look_and_listen_record.json`` exists and is ``APPROVED``."""
    root = Path(episode_root)
    rec_path = root / RECORD_REL
    if not rec_path.is_file():
        return [
            G.row(
                "look_and_listen_record_present",
                False,
                f"missing {RECORD_REL}: every visual and audio render must be perceived and reviewed before shipping",
                level=G.REVIEW if rehearsal else G.FAIL,
            )
        ]
    doc = json.loads(rec_path.read_text(encoding="utf-8"))
    shots = doc.get("shots") or []
    auto_failed = [s.get("shot_id") for s in shots if not s.get("passed_automated_checks")]
    status = doc.get("status")
    rows = [
        G.row(
            "look_and_listen_self_perception",
            not auto_failed,
            f"{len(shots) - len(auto_failed)} of {len(shots)} shot(s) passed re-perception & motion-isolation checks",
            auto_failed[:20],
            level=G.FAIL,
        ),
        G.row(
            "look_and_listen_claude_signoff",
            status == "APPROVED",
            f"look-and-listen status is {status!r} (approved_by={doc.get('approved_by')!r})",
            {"status": status, "record": RECORD_REL},
            level=G.REVIEW if rehearsal else G.FAIL,
        ),
    ]
    return rows


REQUIRED_REVIEW_RECORD_FIELDS = (
    "shot_id",
    "route",
    "scene_id",
    "source_sha256",
    "output_sha256",
    "frame_count",
    "timing_range",
    "visual_findings",
    "audio_findings",
    "decision",
    "render_epoch",
)


def build_per_shot_review_record(
    shot_id: str,
    *,
    route: str,
    scene_id: str = "",
    source_sha256: str = "",
    output_sha256: str = "",
    frame_count: int = 0,
    timing_range: list[float] | tuple[float, float] = (0.0, 0.0),
    visual_findings: list[dict] | None = None,
    audio_findings: list[dict] | None = None,
    decision: str | None = None,
    render_epoch: str = "",
    timing_id: str = "",
) -> dict:
    """P2-7 Per-Shot Review Record: build an auditable review record tied to source/output hashes and render_epoch.
    Any shot missing hashes, frame count, or render_epoch is marked ``NOT_REVIEWED`` (never ``PASS``).
    """
    vis = list(visual_findings) if visual_findings is not None else []
    aud = list(audio_findings) if audio_findings is not None else []
    has_evidence = bool(
        shot_id
        and route
        and source_sha256
        and source_sha256 != "missing"
        and output_sha256
        and output_sha256 != "missing"
        and int(frame_count) > 0
        and render_epoch
    )
    if not has_evidence:
        resolved_decision = "NOT_REVIEWED"
    elif decision in ("PASS", "REVIEW", "FAIL", "NOT_REVIEWED"):
        resolved_decision = decision
    else:
        all_f = vis + aud
        if any((f.get("status") or f.get("severity")) == "FAIL" for f in all_f):
            resolved_decision = "FAIL"
        elif any((f.get("status") or f.get("severity")) == "REVIEW" for f in all_f):
            resolved_decision = "REVIEW"
        else:
            resolved_decision = "PASS"

    return {
        "schema": "per_shot_review_record/1",
        "shot_id": str(shot_id),
        "route": str(route),
        "scene_id": str(scene_id or str(shot_id).split("_")[0]),
        "source_sha256": str(source_sha256 or ""),
        "output_sha256": str(output_sha256 or ""),
        "frame_count": int(frame_count or 0),
        "timing_range": [round(float(timing_range[0]), 4), round(float(timing_range[1]), 4)],
        "visual_findings": vis,
        "audio_findings": aud,
        "decision": resolved_decision,
        "render_epoch": str(render_epoch or ""),
        "timing_id": str(timing_id or ""),
    }


def validate_episode_review_records(
    shots: list[dict],
    records_by_shot: dict[str, dict] | None,
    *,
    expected_render_epoch: str = "",
    expected_timing_id: str = "",
) -> dict:
    """Verify every shot in ``shots`` has a complete, current-epoch review record.
    Missing or stale records are reported as ``NOT_REVIEWED`` and block episode ``PASS``."""
    records_by_shot = records_by_shot or {}
    per_shot: dict[str, dict] = {}
    not_reviewed: list[str] = []
    failed: list[str] = []
    review_needed: list[str] = []

    for sh in shots:
        sid = str(sh.get("shot_id") or "")
        if not sid:
            continue
        rec = records_by_shot.get(sid)
        if not isinstance(rec, dict):
            per_shot[sid] = build_per_shot_review_record(
                sid,
                route=str(sh.get("route") or "still_25d"),
                scene_id=str(sh.get("scene_id") or sh.get("segment_id") or sid.split("_")[0]),
                decision="NOT_REVIEWED",
            )
            not_reviewed.append(sid)
            continue
        missing_fields = [k for k in REQUIRED_REVIEW_RECORD_FIELDS if k not in rec or rec[k] in (None, "")]
        stale_epoch = bool(expected_render_epoch and rec.get("render_epoch") != expected_render_epoch)
        stale_timing = bool(expected_timing_id and rec.get("timing_id") and rec.get("timing_id") != expected_timing_id)
        if missing_fields or stale_epoch or stale_timing or int(rec.get("frame_count", 0)) <= 0:
            rec_copy = dict(rec, decision="NOT_REVIEWED")
            if stale_epoch:
                rec_copy["stale_reason"] = f"render_epoch {rec.get('render_epoch')!r} != {expected_render_epoch!r}"
            elif missing_fields:
                rec_copy["stale_reason"] = f"missing fields: {missing_fields}"
            per_shot[sid] = rec_copy
            not_reviewed.append(sid)
            continue
        per_shot[sid] = rec
        dec = str(rec.get("decision") or "NOT_REVIEWED")
        if dec == "NOT_REVIEWED":
            not_reviewed.append(sid)
        elif dec == "FAIL":
            failed.append(sid)
        elif dec == "REVIEW":
            review_needed.append(sid)

    if failed:
        overall = "FAIL"
    elif not_reviewed:
        overall = "NOT_REVIEWED"
    elif review_needed:
        overall = "REVIEW"
    else:
        overall = "PASS"

    return {
        "schema": "episode_review_audit/1",
        "status": overall,
        "shot_count": len(per_shot),
        "not_reviewed": not_reviewed,
        "failed": failed,
        "review": review_needed,
        "records": per_shot,
    }
