"""Multi-Angle Scene Director uniting Reverse-Engineered Studio Operators with Modal H100 LTX-2.5.

Coordinates:
1. ``ElementsVault`` (@Character, @Location, @Prop, @Style) visual-evidence anchoring.
2. ``Popcorn 2x2 Contact Sheet`` slicing + 2K upscaling (zero multi-angle environment drift).
3. ``Scenebuilder`` operators (Native Multishot, Extend Last-Frame, Jump-To Angle, Audio-First, Retake)
   and ``Helios`` (60s Apache 2.0) long-take specification adapter.
4. Post-render 2K (2560x1440 @ 24fps) Lanczos/micro-contrast upscaling + natural reaction-beat
   tail trimming (0.55-0.70s BP-187 cushion so actors never freeze abruptly after speaking/acting).
5. Deterministic J-cut / L-cut planning for speaker turns inside a scene (BP-215).

Cropped coverage plates are banned (BP-217): every camera angle is generated as a native full frame.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, NoReturn

from explainer_engine.episode.word_timeline_compiler import enforce_dialogue_breath_tail, is_dialogue_shot
from explainer_engine.qa.ai_critic_gate import sha256_file
from explainer_engine.standards import sourced_rules
from explainer_engine.studio.scenebuilder import SceneShotCard, plan_dramatic_scene_sequence


def upscale_ltx_clip_to_2k(
    src_mp4: Path,
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    trim_head_s: float = 0.0,
    trim_tail_s: float = 0.0,
    lut_path: Path | None = None,
) -> dict[str, Any]:
    """Upscale an LTX-2.5 clip cleanly to 2K 2560x1440 @ 24fps yuv420p with optional LUT & handle trim."""
    if not src_mp4.is_file():
        raise FileNotFoundError(f"Source LTX clip not found: {src_mp4}")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "json",
                str(src_mp4),
            ],
            text=True,
        )
    )
    raw_dur = float((probe.get("format") or {}).get("duration", 5.0))
    usable_dur = max(1.5, raw_dur - trim_head_s - trim_tail_s)

    vf_parts = [
        f"scale={width}:{height}:flags=lanczos+accurate_rnd",
        "unsharp=5:5:0.42:3:3:0.15",
    ]
    if lut_path is not None and lut_path.is_file():
        # Subtle 35mm cinema grade blend so LTX matches 2.5D & MapLibre seamlessly
        vf_parts.append(f"lut3d=file='{lut_path.as_posix()}'")
    vf_parts.append("format=yuv420p")

    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        f"{trim_head_s:.3f}",
        "-i",
        str(src_mp4),
        "-t",
        f"{usable_dur:.3f}",
        "-vf",
        ",".join(vf_parts),
        "-r",
        str(fps),
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "17",
        "-c:a",
        "aac",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-b:a",
        "192k",
        "-movflags",
        "+faststart",
        str(out_mp4),
    ]
    subprocess.run(cmd, check=True)
    return {
        "source": str(src_mp4),
        "path": str(out_mp4),
        "sha256": sha256_file(out_mp4),
        "duration_s": round(usable_dur, 3),
        "width": width,
        "height": height,
        "fps": fps,
    }


def extract_clean_extend_frame(clip_mp4: Path, out_png: Path, *, offset_from_end_s: float = 0.25) -> Path:
    """Extract a crisp near-tail frame for Google Flow-style ``Extend`` / ``Jump To`` continuation."""
    out_png.parent.mkdir(parents=True, exist_ok=True)
    probe = json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(clip_mp4)],
            text=True,
        )
    )
    dur = float((probe.get("format") or {}).get("duration", 5.0))
    ts = max(0.1, dur - offset_from_end_s)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-ss",
            f"{ts:.3f}",
            "-i",
            str(clip_mp4),
            "-frames:v",
            "1",
            "-vf",
            "scale=2560:1440:flags=lanczos",
            str(out_png),
        ],
        check=True,
    )
    return out_png


def extract_exact_handoff_frame(
    clip_mp4: Path,
    out_png: Path,
    *,
    offset_from_end_s: float = 0.25,
    fps: float = 24.0,
) -> dict[str, Any]:
    """Extract an exact frame index near the tail of ``clip_mp4`` and return the exact parent cut point.

    Enforces the Loop 4 Exact Frame Handoff Contract: if Shot B is ``chained_from`` Shot A using the
    extracted frame ``F_ext``, Shot A MUST play through ``F_ext - 1`` (never trimmed early) so the
    A -> B cut achieves ``SSIM >= 0.88`` with zero teleport/jump-cut seam.
    """
    out_png.parent.mkdir(parents=True, exist_ok=True)
    probe = json.loads(
        subprocess.check_output(
            [
                "ffprobe",
                "-v",
                "error",
                "-select_streams",
                "v:0",
                "-show_entries",
                "stream=nb_frames,r_frame_rate:format=duration",
                "-of",
                "json",
                str(clip_mp4),
            ],
            text=True,
        )
    )
    dur = float((probe.get("format") or {}).get("duration", 5.0))
    stream = (probe.get("streams") or [{}])[0]
    num, _, den = str(stream.get("r_frame_rate", f"{int(fps)}/1")).partition("/")
    clip_fps = float(num) / max(1.0, float(den or 1.0)) if num else float(fps)
    nb_frames_raw = stream.get("nb_frames")
    total_frames = int(nb_frames_raw) if nb_frames_raw and str(nb_frames_raw).isdigit() else int(round(dur * clip_fps))

    raw_ts = max(0.1, dur - float(offset_from_end_s))
    extract_frame_idx = max(1, min(max(1, total_frames - 1), int(round(raw_ts * clip_fps))))
    extract_time_s = extract_frame_idx / clip_fps
    parent_exact_end_frames = extract_frame_idx  # frames [0 .. extract_frame_idx - 1]
    parent_exact_end_s = parent_exact_end_frames / clip_fps

    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(clip_mp4),
            "-vf",
            f"select=eq(n\\,{extract_frame_idx}),scale=2560:1440:flags=lanczos",
            "-vframes",
            "1",
            str(out_png),
        ],
        check=True,
    )
    return {
        "source_clip": str(clip_mp4),
        "path": str(out_png),
        "sha256": sha256_file(out_png),
        "clip_fps": round(clip_fps, 3),
        "clip_duration_s": round(dur, 4),
        "total_frames": total_frames,
        "extract_frame_idx": extract_frame_idx,
        "extract_time_s": round(extract_time_s, 4),
        "parent_exact_end_frames": parent_exact_end_frames,
        "parent_exact_end_s": round(parent_exact_end_s, 4),
    }


def validate_chained_handoff_plan(
    shot_plan: list[dict[str, Any]],
    *,
    fps: float = 24.0,
    max_handoff_drift_s: float = 0.085,
    min_angle_change_deg: float = 30.0,
) -> dict[str, Any]:
    """Validate the Loop 4 Exact Frame Handoff & Angle-Change Edit Contract before rendering.

    1. If Shot B is ``chained_from`` Shot A (extracted at ``F_ext`` / ``extract_time_s``):
       - Shot A MUST play to ``F_ext - 1`` (``trim_start_s + played_dur_s`` within ``max_handoff_drift_s``
         of ``extract_time_s`` — never trimmed early!).
       - Shot B MUST start at frame 0 (``trim_start_s <= 0.05``).
    2. Otherwise, if Shot A and Shot B share the same ``scene_group``:
       - The cut MUST change shot scale (e.g. ``wide -> medium -> close_up -> insert``) OR change camera
         angle by ``>= 30°`` (``camera_angle_delta_deg >= 30``) OR mark ``distinct_subject=True``.
    """
    findings: list[str] = []
    checked_pairs: list[dict[str, Any]] = []
    frame_s = 1.0 / max(1.0, float(fps))

    for i in range(len(shot_plan) - 1):
        a = shot_plan[i]
        b = shot_plan[i + 1]
        a_id = str(a.get("shot_id") or f"shot_{i + 1}")
        b_id = str(b.get("shot_id") or f"shot_{i + 2}")
        chained_from = str(b.get("chained_from") or "").strip()

        if chained_from and chained_from == a_id:
            a_trim_start = float(a.get("clip_start_s", a.get("trim_start_s", 0.0)))
            a_played = float(
                a.get(
                    "played_dur_s",
                    max(0.0, float(a.get("end_s", 0.0)) - float(a.get("start_s", 0.0))),
                )
            )
            a_end_in_src = a_trim_start + a_played

            if b.get("extract_time_s") is not None:
                f_ext_s = float(b["extract_time_s"])
            elif b.get("extract_frame_idx") is not None:
                f_ext_s = float(b["extract_frame_idx"]) * frame_s
            else:
                raw_dur_a = float(a.get("raw_dur_s", a.get("source_duration_s", a_end_in_src)))
                offset_end = float(b.get("offset_from_end_s", 0.25))
                f_ext_s = max(0.1, raw_dur_a - offset_end)

            target_end_s = max(0.0, f_ext_s - frame_s)
            drift_s = abs(a_end_in_src - target_end_s)
            b_trim_start = float(b.get("clip_start_s", b.get("trim_start_s", 0.0)))
            ok = drift_s <= max_handoff_drift_s and b_trim_start <= 0.05
            checked_pairs.append(
                {
                    "from_shot": a_id,
                    "to_shot": b_id,
                    "kind": "chained_handoff",
                    "parent_end_in_src_s": round(a_end_in_src, 3),
                    "expected_handoff_s": round(target_end_s, 3),
                    "drift_s": round(drift_s, 3),
                    "child_trim_start_s": round(b_trim_start, 3),
                    "passed": ok,
                }
            )
            if drift_s > max_handoff_drift_s:
                findings.append(
                    f"Chained handoff violation {a_id} -> {b_id}: parent stops at {a_end_in_src:.3f}s "
                    f"instead of exact F_ext-1={target_end_s:.3f}s (drift={drift_s:.3f}s > {max_handoff_drift_s:.3f}s)"
                )
            if b_trim_start > 0.05:
                findings.append(
                    f"Chained child {b_id} trims {b_trim_start:.3f}s off head (must start at extracted handoff frame 0)"
                )
        else:
            grp_a = str(a.get("scene_group") or "").strip()
            grp_b = str(b.get("scene_group") or "").strip()
            if grp_a and grp_a == grp_b:
                scale_a = str(a.get("shot_scale") or "").strip().lower()
                scale_b = str(b.get("shot_scale") or "").strip().lower()
                angle_delta = float(b.get("camera_angle_delta_deg", 0.0))
                distinct_subj = bool(b.get("distinct_subject", False))
                scale_changed = bool(scale_a and scale_b and scale_a != scale_b)
                ok = scale_changed or angle_delta >= min_angle_change_deg or distinct_subj
                checked_pairs.append(
                    {
                        "from_shot": a_id,
                        "to_shot": b_id,
                        "kind": "same_scene_cut",
                        "scale_a": scale_a,
                        "scale_b": scale_b,
                        "angle_delta_deg": angle_delta,
                        "passed": ok,
                    }
                )
                if not ok:
                    findings.append(
                        f"Same-scene jump-cut risk {a_id} -> {b_id} (scene_group={grp_a!r}): "
                        f"neither shot scale ({scale_a!r}->{scale_b!r}) nor camera angle ({angle_delta:.0f} deg < {min_angle_change_deg:.0f} deg) changed"
                    )

    return {
        "status": "PASS" if not findings else "FAIL",
        "pairs_checked": len(checked_pairs),
        "pairs": checked_pairs,
        "findings": findings,
    }


def find_exact_handoff_frame(
    parent_mp4: Path,
    child_mp4: Path,
    *,
    search_tail_frames: int = 36,
) -> dict[str, Any]:
    """Locate the exact parent frame index ``F_ext`` matching frame 0 of a chained child clip.

    Returns ``play_parent_frames = max(1, F_ext)`` so trimming the parent clip to
    ``0 .. F_ext - 1`` yields a seamless chained cut directly into child frame 0
    (zero jump cut, zero duplicated freeze frame).
    """
    import cv2
    import numpy as np
    from skimage.metrics import structural_similarity as ssim

    cap_c = cv2.VideoCapture(str(child_mp4))
    ok_c, bgr_c = cap_c.read()
    cap_c.release()
    if not ok_c or bgr_c is None:
        raise RuntimeError(f"Could not read frame 0 of chained child clip: {child_mp4}")
    gc = cv2.cvtColor(cv2.resize(bgr_c, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
    gc_blur = cv2.GaussianBlur(gc, (9, 9), 2.5)
    gc_small = cv2.resize(gc, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()

    cap_p = cv2.VideoCapture(str(parent_mp4))
    total = int(cap_p.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    fps = float(cap_p.get(cv2.CAP_PROP_FPS) or 24.0)
    search_start = max(0, total - max(1, int(search_tail_frames)))
    best_idx = max(1, total - 1)
    best_raw = -1.0
    best_smooth = -1.0
    best_corr = -1.0
    cur = 0
    try:
        while cur < total:
            if not cap_p.grab():
                break
            if cur >= search_start:
                ok_p, bgr_p = cap_p.retrieve()
                if ok_p and bgr_p is not None:
                    gp = cv2.cvtColor(cv2.resize(bgr_p, (320, 180), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY)
                    raw_val = ssim(gp, gc, data_range=255)
                    raw_f = float(raw_val[0] if isinstance(raw_val, tuple) else raw_val)
                    if raw_f > best_raw:
                        gp_blur = cv2.GaussianBlur(gp, (9, 9), 2.5)
                        sm_val = ssim(gp_blur, gc_blur, data_range=255)
                        sm_f = float(sm_val[0] if isinstance(sm_val, tuple) else sm_val)
                        gp_small = cv2.resize(gp, (32, 18), interpolation=cv2.INTER_AREA).astype(np.float32).ravel()
                        denom = float(np.std(gp_small) * np.std(gc_small))
                        corr_f = (
                            float(np.corrcoef(gp_small, gc_small)[0, 1]) if denom > 1e-6 else 1.0
                        )
                        best_raw = raw_f
                        best_smooth = sm_f
                        best_corr = corr_f
                        best_idx = cur
            cur += 1
    finally:
        cap_p.release()

    play_frames = max(1, best_idx)
    return {
        "parent_mp4": str(parent_mp4),
        "child_mp4": str(child_mp4),
        "handoff_frame_idx": int(best_idx),
        "play_parent_frames": int(play_frames),
        "handoff_time_s": round(play_frames / max(1.0, fps), 4),
        "fps": round(fps, 3),
        "raw_ssim": round(best_raw, 4),
        "smooth_ssim": round(best_smooth, 4),
        "layout_corr": round(best_corr, 4),
    }


def build_helios_60s_benchmark_spec(
    *,
    prompt: str,
    first_frame_path: Path,
    duration_s: float = 20.0,
) -> dict[str, Any]:
    """Build a reproducible PKU-YuanGroup/Helios (14B Apache 2.0) long-take benchmark specification."""
    return {
        "schema": "helios_benchmark_spec/1",
        "model_repo": "PKU-YuanGroup/Helios",
        "license": "Apache-2.0",
        "max_native_duration_s": 60.0,
        "requested_duration_s": min(60.0, float(duration_s)),
        "first_frame_path": str(first_frame_path),
        "first_frame_sha256": sha256_file(first_frame_path) if first_frame_path.is_file() else "",
        "prompt": prompt.strip(),
        "recommended_use": "Continuous long-take atmospheric nature/blizzard/migration shots where LTX 5s cuts are unnecessary.",
    }


def assemble_multishot_reel(
    clip_paths: list[Path],
    out_mp4: Path,
    *,
    audio_override_wav: Path | None = None,
) -> Path:
    """Assemble multi-angle 2K LTX clips with crisp editorial hard cuts (zero PowerPoint dissolves)."""
    if not clip_paths:
        raise ValueError("clip_paths must be non-empty")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    concat_file = out_mp4.with_suffix(".concat.txt")
    concat_file.write_text("\n".join(f"file '{p.resolve()}'" for p in clip_paths) + "\n", encoding="utf-8")

    if audio_override_wav is not None and audio_override_wav.is_file():
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-i",
            str(audio_override_wav),
            "-map",
            "0:v",
            "-map",
            "1:a",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "256k",
            "-shortest",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
    else:
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
    subprocess.run(cmd, check=True)
    return out_mp4


FORBIDDEN_PRE_STITCH_FILTER_TOKENS = (
    "zoompan",
    "ken_burns",
    "scale_zoom",
    "pre_stitch_zoom",
    "dynamic_crop",
)


def validate_zero_pre_stitch_zoom(clip_specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Enforce the v5.0 ZERO Pre-Stitch Zoom/Stretch Law on LTX clips.

    Per-clip zoom/Ken-Burns/anisotropic crop before stitching chained or multi-angle LTX
    shots produces frame-stretch and scale-jump anomalies across cut boundaries. Any subtle
    camera zoom must happen natively inside LTX or smoothly AFTER stitching.
    """
    findings: list[str] = []
    for idx, spec in enumerate(clip_specs):
        sid = str(spec.get("shot_id") or f"clip_{idx + 1}")
        if bool(spec.get("pre_stitch_zoom")) or bool(spec.get("ken_burns")):
            findings.append(f"{sid}: pre_stitch_zoom / ken_burns is forbidden before stitching LTX clips")
        zoom_factor = float(spec.get("zoom_factor", 1.0) or 1.0)
        if abs(zoom_factor - 1.0) > 1e-4:
            findings.append(f"{sid}: per-clip zoom_factor={zoom_factor:.3f} != 1.0 forbidden before stitching")
        crop_scale = float(spec.get("crop_scale", 1.0) or 1.0)
        if abs(crop_scale - 1.0) > 1e-4:
            findings.append(f"{sid}: per-clip crop_scale={crop_scale:.3f} != 1.0 forbidden before stitching")
        vf = str(spec.get("vf") or spec.get("video_filter") or "").lower()
        for bad in FORBIDDEN_PRE_STITCH_FILTER_TOKENS:
            if bad in vf:
                findings.append(f"{sid}: forbidden pre-stitch filter token {bad!r} in vf={vf!r}")
    return {
        "status": "PASS" if not findings else "FAIL",
        "clips_checked": len(clip_specs),
        "findings": findings,
    }


def plan_hybrid_scene_continuity(
    scene_id: str,
    mode: str,
    shots: list[dict[str, Any]],
    *,
    blender_set_manifest: dict[str, Any] | None = None,
    max_chain_depth: int = 3,
) -> dict[str, Any]:
    """Compile and validate a v5.0 Hybrid Scene Continuity plan.

    Modes:
    - ``blender_multiview_set``: 1 physical Blender 3D set (>= 4 locked camera angles) -> batch-styled
      plates anchored to shared @Character + @Location references -> LTX-2.5.
    - ``continuous_ltx_chain``: 1 master plate -> LTX -> exact ``find_exact_handoff_frame`` -> clean
      uniform upscale -> next LTX (capped at ``max_chain_depth`` to prevent latent drift).
    - ``hybrid_set_and_chain``: Blender multi-angle set cuts combined with continuous LTX chains inside
      the same ``scene_id``.
    """
    valid_modes = {"blender_multiview_set", "continuous_ltx_chain", "hybrid_set_and_chain"}
    if mode not in valid_modes:
        raise ValueError(f"Unsupported hybrid continuity mode {mode!r}; expected one of {sorted(valid_modes)}")
    if len(shots) < 2:
        raise ValueError(f"Scene {scene_id!r} must contain >= 2 connected shots (no 1-off LTX slideshow clips)")

    findings: list[str] = []
    zoom_check = validate_zero_pre_stitch_zoom(shots)
    if zoom_check["status"] != "PASS":
        findings.extend(zoom_check["findings"])

    if mode in ("blender_multiview_set", "hybrid_set_and_chain"):
        if not blender_set_manifest:
            findings.append(f"{scene_id}: mode={mode!r} requires a rendered blender_set_manifest")
        else:
            angles = blender_set_manifest.get("angles") or []
            if len(angles) < 4:
                findings.append(f"{scene_id}: blender_set_manifest has {len(angles)} angles (< 4 required)")

    chain_depth = 0
    for idx, sh in enumerate(shots):
        sid = str(sh.get("shot_id") or f"{scene_id}_s{idx + 1}")
        chained_from = str(sh.get("chained_from") or "").strip()
        if chained_from:
            chain_depth += 1
            if chain_depth > max_chain_depth:
                findings.append(f"{sid}: chain depth {chain_depth} exceeds max_chain_depth={max_chain_depth}")
            if idx == 0 or chained_from != str(shots[idx - 1].get("shot_id") or ""):
                findings.append(f"{sid}: chained_from={chained_from!r} must reference immediate previous shot")
        else:
            chain_depth = 0
            if mode == "continuous_ltx_chain" and idx > 0:
                findings.append(f"{sid}: continuous_ltx_chain shot {idx + 1} must set chained_from previous shot")

    return {
        "schema": "hybrid_scene_continuity_plan/1",
        "scene_id": scene_id,
        "mode": mode,
        "shot_count": len(shots),
        "zero_pre_stitch_zoom": zoom_check["status"] == "PASS",
        "status": "PASS" if not findings else "FAIL",
        "findings": findings,
    }


def normalize_ltx_clip_uniform(
    src_mp4: Path,
    out_mp4: Path,
    *,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    start_frame: int = 0,
    num_frames: int | None = None,
    lut_path: Path | None = None,
) -> dict[str, Any]:
    """Uniformly scale+center-crop an LTX clip to exact target geometry with ZERO zoom or aspect stretch.

    Using identical ``force_original_aspect_ratio=increase`` + centered ``crop=W:H`` for every
    clip guarantees ``sx == sy`` (zero anisotropic stretch) and constant scale factor across
    every chained handoff boundary.
    """
    if not src_mp4.is_file():
        raise FileNotFoundError(f"Source LTX clip not found: {src_mp4}")
    out_mp4.parent.mkdir(parents=True, exist_ok=True)

    vf_parts: list[str] = []
    if start_frame > 0 or num_frames is not None:
        if num_frames is not None:
            end_frame = start_frame + max(1, int(num_frames))
            vf_parts.append(f"trim=start_frame={int(start_frame)}:end_frame={end_frame},setpts=PTS-STARTPTS")
        else:
            vf_parts.append(f"trim=start_frame={int(start_frame)},setpts=PTS-STARTPTS")
    vf_parts.append(
        f"scale={width}:{height}:force_original_aspect_ratio=increase:flags=lanczos+accurate_rnd,"
        f"crop={width}:{height}:(iw-{width})/2:(ih-{height})/2,setsar=1"
    )
    if lut_path is not None and lut_path.is_file():
        vf_parts.append(f"lut3d=file='{lut_path.as_posix()}'")
    vf_parts.append("format=yuv420p")

    af_parts: list[str] = []
    if start_frame > 0 or num_frames is not None:
        st_s = start_frame / float(fps)
        if num_frames is not None:
            en_s = (start_frame + max(1, int(num_frames))) / float(fps)
            af_parts.append(f"atrim=start={st_s:.6f}:end={en_s:.6f},asetpts=PTS-STARTPTS")
        else:
            af_parts.append(f"atrim=start={st_s:.6f},asetpts=PTS-STARTPTS")
    af_parts.append("afade=t=in:st=0:d=0.025")

    probe = json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-show_streams", "-of", "json", str(src_mp4)],
            text=True,
        )
    )
    has_audio = any(st.get("codec_type") == "audio" for st in probe.get("streams") or [])

    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src_mp4)]
    if has_audio:
        cmd.extend(["-vf", ",".join(vf_parts), "-af", ",".join(af_parts)])
    else:
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=r=48000:cl=stereo", "-map", "0:v:0", "-map", "1:a:0", "-vf", ",".join(vf_parts), "-shortest"])
    cmd.extend(
        [
            "-r",
            str(fps),
            "-fps_mode",
            "cfr",
            "-c:v",
            "libx264",
            "-preset",
            "fast",
            "-crf",
            "17",
            "-c:a",
            "aac",
            "-ar",
            "48000",
            "-ac",
            "2",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(out_mp4),
        ]
    )
    subprocess.run(cmd, check=True)

    out_probe = json.loads(
        subprocess.check_output(
            ["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=nb_frames:format=duration", "-of", "json", str(out_mp4)],
            text=True,
        )
    )
    dur_out = float((out_probe.get("format") or {}).get("duration", 0.0))
    return {
        "source": str(src_mp4),
        "path": str(out_mp4),
        "sha256": sha256_file(out_mp4),
        "duration_s": round(dur_out, 4),
        "width": width,
        "height": height,
        "fps": fps,
        "start_frame": start_frame,
        "num_frames": num_frames,
    }


def _probe_duration_s(path: Path) -> float:
    out = subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(path)],
        text=True,
    )
    return float(json.loads(out)["format"]["duration"])


def stitch_scene_zero_stretch(
    clip_specs: list[dict[str, Any]],
    out_mp4: Path,
    *,
    work_dir: Path,
    width: int = 2560,
    height: int = 1440,
    fps: int = 24,
    lut_path: Path | None = None,
) -> dict[str, Any]:
    """Stitch multi-angle & chained LTX clips with ZERO pre-stitch zoom/stretch and exact handoff cuts."""
    zchk = validate_zero_pre_stitch_zoom(clip_specs)
    if zchk["status"] != "PASS":
        raise ValueError("Refusing to stitch clips with pre-stitch zoom/stretch:\n  - " + "\n  - ".join(zchk["findings"]))
    work_dir = Path(work_dir).resolve()
    work_dir.mkdir(parents=True, exist_ok=True)

    # 1. Resolve exact parent play_frames for any chained_from pair before normalizing
    resolved_frames: dict[int, tuple[int, int | None]] = {}
    handoff_records: list[dict[str, Any]] = []
    for i, spec in enumerate(clip_specs):
        st_f = int(spec.get("start_frame", 0))
        n_f = int(spec["num_frames"]) if spec.get("num_frames") is not None else None
        resolved_frames[i] = (st_f, n_f)

    for i in range(len(clip_specs) - 1):
        a = clip_specs[i]
        b = clip_specs[i + 1]
        a_id = str(a.get("shot_id") or f"shot_{i + 1}")
        if str(b.get("chained_from") or "").strip() == a_id:
            hf = find_exact_handoff_frame(Path(a["clip_path"]), Path(b["clip_path"]))
            st_a, _ = resolved_frames[i]
            play_n = max(1, int(hf["play_parent_frames"]) - st_a)
            resolved_frames[i] = (st_a, play_n)
            # Child starts strictly at frame 0 (never trimmed early)
            _, n_b = resolved_frames[i + 1]
            resolved_frames[i + 1] = (0, n_b)
            handoff_records.append({"from_shot": a_id, "to_shot": b.get("shot_id"), **hf})

    # 1b. A dialogue clip's resolved window (including a handoff trim) must keep every word and its breath tail
    for i, spec in enumerate(clip_specs):
        if not is_dialogue_shot(spec):
            continue
        st_f, n_f = resolved_frames[i]
        window: dict[str, Any] = {
            "shot_id": str(spec.get("shot_id") or f"shot_{i + 1}"),
            "speech_start_s": spec.get("speech_start_s"),
            "speech_end_s": spec.get("speech_end_s"),
            "trim_start_s": st_f / float(fps),
            "source_duration_s": _probe_duration_s(Path(spec["clip_path"])),
        }
        if n_f is not None:
            window["duration_s"] = n_f / float(fps)
        enforce_dialogue_breath_tail(window)

    # 2. Uniformly normalize every clip with ZERO zoom/stretch
    norm_paths: list[Path] = []
    shot_windows: list[dict[str, Any]] = []
    cursor_s = 0.0
    for i, spec in enumerate(clip_specs):
        sid = str(spec.get("shot_id") or f"shot_{i + 1:02d}")
        st_f, n_f = resolved_frames[i]
        norm_p = work_dir / f"norm_{i + 1:02d}_{sid}.mp4"
        info = normalize_ltx_clip_uniform(
            Path(spec["clip_path"]),
            norm_p,
            width=width,
            height=height,
            fps=fps,
            start_frame=st_f,
            num_frames=n_f,
            lut_path=lut_path,
        )
        norm_paths.append(norm_p)
        dur = float(info["duration_s"])
        shot_windows.append(
            {
                "shot_id": sid,
                "scene_id": str(spec.get("scene_id") or spec.get("scene_group") or "scene_01"),
                "scene_group": str(spec.get("scene_group") or spec.get("scene_id") or "scene_01"),
                "shot_scale": str(spec.get("shot_scale") or ""),
                "camera_angle_delta_deg": float(spec.get("camera_angle_delta_deg", 0.0)),
                "chained_from": str(spec.get("chained_from") or ""),
                "start_s": round(cursor_s, 4),
                "end_s": round(cursor_s + dur, 4),
                "duration_s": round(dur, 4),
                "route": "ltx_video",
            }
        )
        cursor_s += dur

    # 3. Assemble with clean hard cuts and single CFR re-mux
    assemble_multishot_reel(norm_paths, out_mp4)
    return {
        "path": str(out_mp4),
        "sha256": sha256_file(out_mp4),
        "duration_s": round(cursor_s, 4),
        "width": width,
        "height": height,
        "fps": fps,
        "zero_pre_stitch_zoom_verified": True,
        "handoffs": handoff_records,
        "shot_windows": shot_windows,
    }


def validate_eyeline_180_rule(shot_specs: list[dict[str, Any]]) -> dict[str, Any]:
    """Verify 180-degree axis / eyeline continuity across dialogue shot/reverse-shot cuts.

    In any two-person scene, if Actor A is established facing ``right`` and Actor B facing ``left``,
    consecutive cuts between A and B MUST preserve opposite facing directions so characters look
    at each other rather than staring in the same screen direction.
    """
    findings: list[str] = []
    actor_axis: dict[tuple[str, str], str] = {}
    for idx, sh in enumerate(shot_specs):
        sc = str(sh.get("scene_id") or sh.get("scene_group") or "").strip()
        subj = str(sh.get("focus_subject") or "").strip().lower()
        facing = str(sh.get("facing_dir") or "").strip().lower()
        if not sc or not subj or facing not in ("left", "right"):
            continue
        key = (sc, subj)
        if key in actor_axis and actor_axis[key] != facing:
            findings.append(
                f"180-degree axis break in scene {sc!r} on {sh.get('shot_id')}: "
                f"subject {subj!r} flipped from facing {actor_axis[key]!r} to {facing!r}"
            )
        else:
            actor_axis[key] = facing

        if idx > 0:
            prev = shot_specs[idx - 1]
            p_sc = str(prev.get("scene_id") or prev.get("scene_group") or "").strip()
            p_subj = str(prev.get("focus_subject") or "").strip().lower()
            p_facing = str(prev.get("facing_dir") or "").strip().lower()
            if p_sc == sc and p_subj and p_subj != subj and p_facing in ("left", "right") and p_facing == facing:
                findings.append(
                    f"Eyeline collision at {prev.get('shot_id')} -> {sh.get('shot_id')} in scene {sc!r}: "
                    f"both {p_subj!r} and {subj!r} face {facing!r} instead of facing each other"
                )
    return {
        "status": "PASS" if not findings else "FAIL",
        "subjects_tracked": len(actor_axis),
        "findings": findings,
    }


CROPPED_PLATE_BAN_MESSAGE = (
    "Cropped coverage plates are permanently banned; generate native full-frame camera angles per shot."
)


def extract_axis_locked_coverage_plates(*_args: Any, **_kwargs: Any) -> NoReturn:
    """Banned (BP-217). Slicing close-ups or mediums out of a wide plate is never allowed; the name stays so that
    an old caller fails loudly instead of falling back to its own crop."""
    raise RuntimeError(CROPPED_PLATE_BAN_MESSAGE)


J_L_CUT_MIN_OVERLAP_S = float(sourced_rules.T("BP-215", "overlap_min_s"))
J_L_CUT_MAX_OVERLAP_S = float(sourced_rules.T("BP-215", "overlap_max_s"))
J_L_CUT_DEFAULT_OVERLAP_S = float(sourced_rules.T("BP-215", "overlap_default_s"))


def plan_dialogue_j_l_cuts(
    shots: list[dict[str, Any]],
    *,
    overlap_s: float = J_L_CUT_DEFAULT_OVERLAP_S,
    fps: int = 24,
) -> dict[str, Any]:
    """Place every shot's sound and picture so speaker turns inside a scene overlap as J-cuts and L-cuts.

    Each shot needs ``shot_id``, ``scene_id``, ``trim_start_s`` (default 0) and ``duration_s``; a dialogue shot
    also needs ``speaker``, ``speech_start_s`` and ``speech_end_s`` (source clip clock).

    At a change of speaker inside one scene the incoming sound starts ``overlap_s`` before the outgoing sound
    ends, which is inside the outgoing breath tail, so two voices never collide. A J-cut holds the outgoing
    picture to the end of its sound; an L-cut moves to the incoming picture as its sound starts. Turns alternate
    J, L, J within a scene unless the incoming shot sets ``cut_in`` to ``"j"`` or ``"l"``. Every other boundary
    is a straight cut. Picture and sound of a clip always share one origin, so lips stay in sync.
    """
    if not J_L_CUT_MIN_OVERLAP_S - 1e-9 <= overlap_s <= J_L_CUT_MAX_OVERLAP_S + 1e-9:
        raise ValueError(
            f"overlap_s={overlap_s} is outside {J_L_CUT_MIN_OVERLAP_S:.2f}..{J_L_CUT_MAX_OVERLAP_S:.2f}s"
        )
    lowest = math.ceil(J_L_CUT_MIN_OVERLAP_S * fps - 1e-6)
    highest = math.floor(J_L_CUT_MAX_OVERLAP_S * fps + 1e-6)
    overlap = min(highest, max(lowest, round(overlap_s * fps))) / float(fps)

    planned: list[dict[str, Any]] = []
    cuts: list[dict[str, Any]] = []
    turns_in_scene: dict[str, int] = {}
    for idx, raw in enumerate(shots):
        sid = str(raw.get("shot_id") or "").strip()
        scene = str(raw.get("scene_id") or "").strip()
        if not sid or not scene:
            raise ValueError(f"shot #{idx + 1} needs shot_id and scene_id")
        if any(p["shot_id"] == sid for p in planned):
            raise ValueError(f"duplicate shot_id {sid!r}")
        dialogue = is_dialogue_shot(raw)
        speaker = str(raw.get("speaker") or "").strip().lower()
        trim_in = float(raw.get("trim_start_s", 0.0))
        if dialogue:
            if not speaker:
                raise ValueError(f"{sid}: a dialogue shot needs a speaker")
            source_out = enforce_dialogue_breath_tail(raw)["play_out_s"]
        else:
            source_out = trim_in + float(raw["duration_s"])
        length = source_out - trim_in
        if length <= 2 * overlap:
            raise ValueError(f"{sid}: {length:.2f}s is too short for {overlap:.2f}s overlaps on both sides")

        kind = "straight"
        audio_start = 0.0
        if planned:
            prev = planned[-1]
            audio_start = prev["audio_end_s"]
            picture_cut = audio_start
            if dialogue and prev["has_dialogue"] and prev["scene_id"] == scene and prev["speaker"] != speaker:
                turn = turns_in_scene.get(scene, 0)
                turns_in_scene[scene] = turn + 1
                kind = str(raw.get("cut_in") or ("j" if turn % 2 == 0 else "l")).lower()
                if kind not in ("j", "l"):
                    raise ValueError(f"{sid}: cut_in must be 'j' or 'l', not {kind!r}")
                audio_start = prev["audio_end_s"] - overlap
                picture_cut = prev["audio_end_s"] if kind == "j" else audio_start
            prev["picture_end_s"] = picture_cut
            cuts.append(
                {
                    "from_shot": prev["shot_id"],
                    "to_shot": sid,
                    "scene_id": scene,
                    "kind": kind,
                    "picture_cut_s": picture_cut,
                    "audio_overlap_s": prev["audio_end_s"] - audio_start,
                }
            )
        else:
            picture_cut = 0.0
        planned.append(
            {
                "shot_id": sid,
                "scene_id": scene,
                "speaker": speaker,
                "has_dialogue": dialogue,
                "speech_start_s": raw.get("speech_start_s"),
                "speech_end_s": raw.get("speech_end_s"),
                "audio_start_s": audio_start,
                "audio_end_s": audio_start + length,
                "audio_source_in_s": trim_in,
                "audio_source_out_s": source_out,
                "picture_start_s": picture_cut,
                "picture_end_s": audio_start + length,
            }
        )

    for item in planned:
        origin = item["audio_start_s"] - item["audio_source_in_s"]
        item["picture_source_in_s"] = item["picture_start_s"] - origin
        item["picture_source_out_s"] = item["picture_end_s"] - origin
        item["picture_start_frame"] = round(item["picture_source_in_s"] * fps)
        item["picture_num_frames"] = round(item["picture_end_s"] * fps) - round(item["picture_start_s"] * fps)

    return {
        "schema": "dialogue_jl_cut_plan/1",
        "fps": fps,
        "overlap_s": overlap,
        "total_duration_s": planned[-1]["audio_end_s"] if planned else 0.0,
        "shots": planned,
        "cuts": cuts,
    }




def validate_native_keyframe_plates(
    shot_specs: list[dict[str, Any]],
    *,
    min_width: int = 1280,
    min_height: int = 720,
    max_plate_reuse: int = 1,
    max_crop_upscale: float = 1.35,
) -> dict[str, Any]:
    """Fail-closed guard preventing chopped sub-crops and repeated establishing plates in LTX plans.

    Enforces two cinema quality laws:
    1. No LTX shot may feed an aggressively cropped & upscaled slice of a wide image
       (``derived_from_crop=True`` with ``crop_upscale_ratio > max_crop_upscale``).
    2. No identical still plate (path or SHA-256) may be reused more than ``max_plate_reuse``
       times across an episode unless explicitly marked ``chained_from`` an active shot.
    """
    findings: list[str] = []
    plate_usage: dict[str, list[str]] = {}

    for idx, spec in enumerate(shot_specs):
        sid = str(spec.get("shot_id") or f"shot_{idx + 1}")
        route = str(spec.get("route") or "ltx_video").strip().lower()
        is_ltx = route in {"ltx", "ltx_video", "video"}

        crop_ratio = float(spec.get("crop_upscale_ratio", 1.0) or 1.0)
        if is_ltx and (bool(spec.get("derived_from_crop")) and crop_ratio > max_crop_upscale):
            findings.append(
                f"{sid}: digitally cropped sub-plate (upscale={crop_ratio:.2f}x > {max_crop_upscale:.2f}x) "
                f"is forbidden as an LTX keyframe; generate a native anchor-locked angle plate"
            )

        w = int(spec.get("plate_width", min_width) or min_width)
        h = int(spec.get("plate_height", min_height) or min_height)
        if is_ltx and (w < min_width or h < min_height):
            findings.append(f"{sid}: plate resolution {w}x{h} below minimum {min_width}x{min_height}")

        if not str(spec.get("chained_from") or "").strip():
            key = str(spec.get("plate_sha256") or spec.get("start_image_path") or spec.get("picture") or "").strip()
            if key:
                plate_usage.setdefault(key, []).append(sid)

    reused: dict[str, list[str]] = {}
    for key, sids in plate_usage.items():
        if len(sids) > max_plate_reuse:
            reused[key] = sids
            findings.append(
                f"Plate {key!r} reused {len(sids)} times across shots {sids} "
                f"(max allowed={max_plate_reuse}; generate distinct camera angles/plates)"
            )

    return {
        "status": "PASS" if not findings else "FAIL",
        "shots_checked": len(shot_specs),
        "reused_plates": reused,
        "findings": findings,
    }


__all__ = [
    "SceneShotCard",
    "assemble_multishot_reel",
    "build_helios_60s_benchmark_spec",
    "extract_axis_locked_coverage_plates",
    "extract_clean_extend_frame",
    "extract_exact_handoff_frame",
    "find_exact_handoff_frame",
    "normalize_ltx_clip_uniform",
    "plan_dialogue_j_l_cuts",
    "plan_dramatic_scene_sequence",
    "plan_hybrid_scene_continuity",
    "stitch_scene_zero_stretch",
    "upscale_ltx_clip_to_2k",
    "validate_chained_handoff_plan",
    "validate_eyeline_180_rule",
    "validate_native_keyframe_plates",
    "validate_zero_pre_stitch_zoom",
]
