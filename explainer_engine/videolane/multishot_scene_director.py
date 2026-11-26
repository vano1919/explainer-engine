"""Multi-Angle Scene Director uniting Reverse-Engineered Studio Operators with Modal H100 LTX-2.5.

Coordinates:
1. ``ElementsVault`` (@Character, @Location, @Prop, @Style) visual-evidence anchoring.
2. ``Popcorn 2x2 Contact Sheet`` slicing + 2K upscaling (zero multi-angle environment drift).
3. ``Scenebuilder`` operators (Native Multishot, Extend Last-Frame, Jump-To Angle, Audio-First, Retake)
   and ``Helios`` (60s Apache 2.0) long-take specification adapter.
4. Post-render 2K (2560x1440 @ 24fps) Lanczos/micro-contrast upscaling + natural reaction-beat
   tail trimming (0.55-0.70s BP-187 cushion so actors never freeze abruptly after speaking/acting).
"""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from explainer_engine.qa.ai_critic_gate import sha256_file
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


__all__ = [
    "SceneShotCard",
    "assemble_multishot_reel",
    "build_helios_60s_benchmark_spec",
    "extract_clean_extend_frame",
    "extract_exact_handoff_frame",
    "plan_dramatic_scene_sequence",
    "upscale_ltx_clip_to_2k",
    "validate_chained_handoff_plan",
]
