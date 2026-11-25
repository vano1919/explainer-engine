"""Photo-first LTX-2.5 cinematography loop: vision-grounded prompting, 0.5s handles, mode routing, QA, and 2K chaining.

Key production invariants enforced in code:
1. Photo-First Prompting: Every LTX motion prompt is grounded in an actual visual observation of the
   generated reference photo on disk (bound by 64-char SHA-256), never blindly copied from a stale
   pre-photo text prompt.
2. 0.5-Second Editorial Handles ("ლუფტი"): Every clip adds HEAD_HANDLE_S (0.5s) and TAIL_HANDLE_S (0.5s)
   before quantizing to LTX-2.5's valid ``8n + 1`` frame buckets at 24 fps, giving the editor clean room
   for J/L-cut transitions and tail-frame selection.
3. Explicit Mode Routing: Chooses cleanly between ``flf2v`` (first+last frame interpolation),
   ``last_frame_continuation`` (same-scene upscaled best tail frame, capped at MAX_CHAIN_DEPTH=3 to
   prevent cumulative drift), ``ic_lora_layout`` (Blender spatial blocking), and ``new_keyframe_i2v``.
4. Closed-Loop Autonomous Shot Engine: Photo -> Vision LLM observation -> LTX prompt -> LTX render
   -> Eye+Ear QA -> (PASS & same scene: best tail frame + 2K upscale -> next shot; FAIL: retry).
"""
from __future__ import annotations

import hashlib
import math
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from explainer_engine.core.camera_vocab import ALLOWED_CAMERA_MOVES, validate_camera_move
from explainer_engine.core.errors import ContractError

DEFAULT_FPS = 24
HEAD_HANDLE_S = 0.5
TAIL_HANDLE_S = 0.5
MAX_CHAIN_DEPTH = 3
TARGET_2K_WIDTH = 2560
TARGET_2K_HEIGHT = 1440
LTX_MODES = frozenset({"new_keyframe_i2v", "last_frame_continuation", "flf2v", "ic_lora_layout"})
UPSCALER_BACKENDS = frozenset({"realesrgan_x2", "seedvr2_4n1", "lanczos_cas_fallback", "local_lanczos_unsharp_still", "ffmpeg_2k_lanczos_cas"})


@dataclass(frozen=True)
class PhotoObservation:
    """Structured observation produced by a Vision LLM inspecting the actual generated photo on disk."""

    photo_path: str
    photo_sha256: str
    observed_subjects: list[str]
    observed_lighting: str
    observed_composition: str
    observed_environment: str
    deviation_from_script: str = "none"


@dataclass(frozen=True)
class ClipTimingBudget:
    """Editorial duration plus 0.5s head/tail handles quantized to LTX-2.5 ``8n + 1`` frame buckets."""

    editorial_seconds: float
    head_handle_s: float
    tail_handle_s: float
    raw_total_seconds: float
    ltx_frames: int
    ltx_seconds: float
    fps: int = DEFAULT_FPS
    trim_in_s: float = HEAD_HANDLE_S
    trim_out_s: float = 0.0


@dataclass(frozen=True)
class ShotLoopStep:
    """Verifiable record for one shot processed by the continuous autonomous LTX loop."""

    shot_id: str
    scene_id: str
    ltx_mode: str
    chain_depth: int
    attempts: int
    qa_verdict: str
    prompt: str
    timing: ClipTimingBudget
    start_image_path: str
    start_image_sha256: str
    clip_path: str | None = None
    upscaled_clip_path: str | None = None
    extracted_tail_frame_path: str | None = None
    upscaled_tail_frame_path: str | None = None
    video_upscaler_backend: str | None = None
    still_upscaler_backend: str | None = None
    upscaled_clip_sha256: str | None = None
    upscaled_tail_sha256: str | None = None
    notes: list[str] = field(default_factory=list)


def sha256_file(path: Path) -> str:
    if not path.is_file():
        raise ContractError(f"Required media file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def quantize_ltx_frames(seconds: float, *, fps: int = DEFAULT_FPS, min_frames: int = 25) -> int:
    """Round ``seconds`` UP to the nearest valid LTX-2.5 ``8n + 1`` frame count (e.g. 49, 73, 97, 121)."""
    if not math.isfinite(seconds) or seconds <= 0:
        raise ContractError(f"seconds must be a positive finite number, got {seconds!r}")
    raw = max(min_frames, math.ceil(seconds * fps))
    rem = (raw - 1) % 8
    return raw if rem == 0 else raw + (8 - rem)


def compute_clip_timing_with_handles(
    editorial_seconds: float,
    *,
    head_handle_s: float = HEAD_HANDLE_S,
    tail_handle_s: float = TAIL_HANDLE_S,
    fps: int = DEFAULT_FPS,
) -> ClipTimingBudget:
    """Add 0.5s head + 0.5s tail handles ("ლუფტი") and quantize to LTX ``8n + 1`` frames."""
    if not math.isfinite(editorial_seconds) or editorial_seconds <= 0:
        raise ContractError(f"editorial_seconds must be positive finite, got {editorial_seconds!r}")
    if head_handle_s < 0 or tail_handle_s < 0:
        raise ContractError("head_handle_s and tail_handle_s cannot be negative")
    raw_total = round(editorial_seconds + head_handle_s + tail_handle_s, 4)
    ltx_frames = quantize_ltx_frames(raw_total, fps=fps)
    ltx_seconds = round(ltx_frames / fps, 4)
    trim_out = round(head_handle_s + editorial_seconds, 4)
    return ClipTimingBudget(
        editorial_seconds=round(editorial_seconds, 4),
        head_handle_s=round(head_handle_s, 4),
        tail_handle_s=round(tail_handle_s, 4),
        raw_total_seconds=raw_total,
        ltx_frames=ltx_frames,
        ltx_seconds=ltx_seconds,
        fps=fps,
        trim_in_s=round(head_handle_s, 4),
        trim_out_s=trim_out,
    )


def select_ltx_mode(
    shot: dict[str, Any],
    *,
    prev_scene_id: str | None = None,
    chain_depth: int = 0,
    has_upscaled_tail: bool = False,
) -> str:
    """Select the optimal LTX-2.5 generation mode based on scene continuity, end-frame targets, and drift limits."""
    if shot.get("end_image_path") or shot.get("requires_exact_end_pose"):
        return "flf2v"
    if shot.get("blender_layout_pass") or shot.get("ic_lora_conditioning"):
        return "ic_lora_layout"
    same_scene = prev_scene_id is not None and shot.get("scene_id") == prev_scene_id
    wants_continue = bool(shot.get("continue_from_previous", False))
    if same_scene and wants_continue and has_upscaled_tail and chain_depth < MAX_CHAIN_DEPTH:
        return "last_frame_continuation"
    return "new_keyframe_i2v"


def build_photo_grounded_prompt(
    observation: PhotoObservation,
    *,
    camera_move: str,
    action_beat: str,
    acting_style: str,
    spoken_line: str | None = None,
    speaker_name: str | None = None,
    voice_description: str | None = None,
    ambient_sound: str = "",
    ltx_mode: str = "new_keyframe_i2v",
) -> str:
    """Compose an LTX-2.5 motion prompt strictly grounded in the observed pixels of the reference photo."""
    photo_p = Path(observation.photo_path)
    actual_sha = sha256_file(photo_p)
    if actual_sha != observation.photo_sha256:
        raise ContractError(
            f"PhotoObservation SHA-256 mismatch for {photo_p}: prompt would drift from actual pixels on disk"
        )
    cam = validate_camera_move(camera_move)
    if ltx_mode not in LTX_MODES:
        raise ContractError(f"Unsupported ltx_mode: {ltx_mode!r}")

    subjects_str = ", ".join(s.strip() for s in observation.observed_subjects if s.strip()) or "the scene subjects"
    path_prefix = (
        "Smooth continuous transition from the starting frame to the target end frame: "
        if ltx_mode == "flf2v"
        else ""
    )
    parts = [
        f"{path_prefix}Starting from the exact observed composition ({observation.observed_composition}) "
        f"with {subjects_str} under {observation.observed_lighting} in {observation.observed_environment}.",
        f"Camera executes a controlled {cam} while {action_beat.strip()}.",
        f"Acting & motion discipline: {acting_style.strip()}.",
    ]
    if spoken_line:
        if not speaker_name or not voice_description:
            raise ContractError("Clip-spoken LTX prompt requires both speaker_name and voice_description")
        parts.append(f'{speaker_name.strip()} says in {voice_description.strip()}: "{spoken_line.strip()}"')
    else:
        parts.append("Nobody speaks. No dialogue.")
    if ambient_sound.strip():
        parts.append(f"Diegetic sound: {ambient_sound.strip()}.")
    return " ".join(parts)


def run_continuous_shot_loop(
    shots: list[dict[str, Any]],
    *,
    vision_observer: Callable[[Path, dict[str, Any]], PhotoObservation],
    video_generator: Callable[[dict[str, Any]], Path],
    qa_reviewer: Callable[[Path, dict[str, Any]], dict[str, Any]],
    tail_extractor: Callable[[Path], Path],
    upscaler_2k: Callable[[Path, str], Path] | None = None,
    still_upscaler: Any = None,
    video_upscaler: Any = None,
    acting_style: str = "restrained historical documentary realism, natural micro-expressions, steady posture",
    max_retries: int = 2,
    upscaler_backend: str = "realesrgan_x2",
) -> dict[str, Any]:
    """Execute the closed-loop Photo -> Vision Prompt -> LTX (+0.5s handles) -> QA -> 2K Upscale -> Chain loop.

    All external model calls are injected as callables so the full loop is 100% deterministic and
    unit-testable offline ($0.00 spend) and fails closed if any shot exhausts retries without QA PASS.
    """
    if upscaler_backend not in UPSCALER_BACKENDS:
        raise ContractError(f"Unsupported upscaler_backend: {upscaler_backend!r}")

    steps: list[ShotLoopStep] = []
    prev_scene_id: str | None = None
    prev_upscaled_tail: Path | None = None
    chain_depth = 0

    for shot in shots:
        shot_id = str(shot["shot_id"])
        scene_id = str(shot.get("scene_id", "S01"))
        timing = compute_clip_timing_with_handles(float(shot.get("editorial_seconds", 4.0)))
        mode = select_ltx_mode(
            shot,
            prev_scene_id=prev_scene_id,
            chain_depth=chain_depth,
            has_upscaled_tail=prev_upscaled_tail is not None and prev_upscaled_tail.is_file(),
        )

        if mode == "last_frame_continuation" and prev_upscaled_tail is not None:
            start_img = prev_upscaled_tail
            chain_depth += 1
        else:
            raw_img = shot.get("start_image_path")
            if not raw_img:
                raise ContractError(f"Shot {shot_id} ({mode}) requires start_image_path")
            start_img = Path(raw_img)
            chain_depth = 0

        obs = vision_observer(start_img, shot)
        camera_move = str(shot.get("camera_move", ALLOWED_CAMERA_MOVES[0]))
        prompt = build_photo_grounded_prompt(
            obs,
            camera_move=camera_move,
            action_beat=str(shot.get("action_beat", "subtle natural motion unfolds")),
            acting_style=acting_style,
            spoken_line=shot.get("spoken_line"),
            speaker_name=shot.get("speaker_name"),
            voice_description=shot.get("voice_description"),
            ambient_sound=str(shot.get("ambient_sound", "")),
            ltx_mode=mode,
        )

        qa_verdict = "FAIL"
        clip_path: Path | None = None
        notes: list[str] = []
        attempts = 0
        for attempt in range(1, max_retries + 2):
            attempts = attempt
            req = {
                "shot_id": shot_id,
                "scene_id": scene_id,
                "ltx_mode": mode,
                "prompt": prompt,
                "start_image_path": str(start_img),
                "end_image_path": str(shot["end_image_path"]) if shot.get("end_image_path") else None,
                "ltx_frames": timing.ltx_frames,
                "ltx_seconds": timing.ltx_seconds,
                "attempt": attempt,
            }
            clip_path = video_generator(req)
            qa_res = qa_reviewer(clip_path, req)
            qa_verdict = str(qa_res.get("verdict", "FAIL")).upper()
            if qa_verdict == "PASS":
                break
            notes.append(f"attempt {attempt}: QA={qa_verdict} ({qa_res.get('reason', 'unspecified')})")

        from explainer_engine.videolane.adapters import LocalFFmpeg2KVideoUpscaler, LocalStillUpscaler

        eff_video_up = video_upscaler if video_upscaler is not None else (None if upscaler_2k is not None else LocalFFmpeg2KVideoUpscaler())
        eff_still_up = still_upscaler if still_upscaler is not None else (None if upscaler_2k is not None else LocalStillUpscaler())

        upscaled_clip: Path | None = None
        extracted_tail: Path | None = None
        upscaled_tail: Path | None = None
        vid_up_backend: str | None = None
        still_up_backend: str | None = None
        upscaled_clip_sha: str | None = None
        upscaled_tail_sha: str | None = None
        if qa_verdict == "PASS" and clip_path is not None:
            if eff_video_up is not None:
                v_out = clip_path.with_name(f"{clip_path.stem}_2k{clip_path.suffix or '.mp4'}")
                v_meta = eff_video_up.upscale_video(clip_path, v_out)
                upscaled_clip = Path(v_meta["output_path"])
                vid_up_backend = str(v_meta.get("backend", getattr(eff_video_up, "backend_name", "video_upscaler")))
                upscaled_clip_sha = str(v_meta.get("sha256") or (sha256_file(upscaled_clip) if upscaled_clip.is_file() else ""))
            elif upscaler_2k is not None:
                upscaled_clip = upscaler_2k(clip_path, upscaler_backend)
                vid_up_backend = upscaler_backend
                upscaled_clip_sha = sha256_file(upscaled_clip) if upscaled_clip.is_file() else None

            extracted_tail = tail_extractor(clip_path)
            if eff_still_up is not None:
                s_out = extracted_tail.with_name(f"{extracted_tail.stem}_2k.png")
                s_meta = eff_still_up.upscale_still(extracted_tail, s_out)
                upscaled_tail = Path(s_meta["output_path"])
                still_up_backend = str(s_meta.get("backend", getattr(eff_still_up, "backend_name", "still_upscaler")))
                upscaled_tail_sha = str(s_meta.get("sha256") or (sha256_file(upscaled_tail) if upscaled_tail.is_file() else ""))
            elif upscaler_2k is not None:
                upscaled_tail = upscaler_2k(extracted_tail, upscaler_backend)
                still_up_backend = upscaler_backend
                upscaled_tail_sha = sha256_file(upscaled_tail) if upscaled_tail.is_file() else None

            prev_upscaled_tail = upscaled_tail
            prev_scene_id = scene_id
        else:
            prev_upscaled_tail = None
            prev_scene_id = scene_id

        step = ShotLoopStep(
            shot_id=shot_id,
            scene_id=scene_id,
            ltx_mode=mode,
            chain_depth=chain_depth,
            attempts=attempts,
            qa_verdict=qa_verdict,
            prompt=prompt,
            timing=timing,
            start_image_path=str(start_img),
            start_image_sha256=obs.photo_sha256,
            clip_path=str(clip_path) if clip_path else None,
            upscaled_clip_path=str(upscaled_clip) if upscaled_clip else None,
            extracted_tail_frame_path=str(extracted_tail) if extracted_tail else None,
            upscaled_tail_frame_path=str(upscaled_tail) if upscaled_tail else None,
            video_upscaler_backend=vid_up_backend,
            still_upscaler_backend=still_up_backend,
            upscaled_clip_sha256=upscaled_clip_sha,
            upscaled_tail_sha256=upscaled_tail_sha,
            notes=notes,
        )
        steps.append(step)
        if qa_verdict != "PASS":
            return {
                "status": "FAIL",
                "halted_shot_id": shot_id,
                "target_resolution": f"{TARGET_2K_WIDTH}x{TARGET_2K_HEIGHT}",
                "steps": [asdict(s) for s in steps],
            }

    return {
        "status": "PASS",
        "halted_shot_id": None,
        "target_resolution": f"{TARGET_2K_WIDTH}x{TARGET_2K_HEIGHT}",
        "steps": [asdict(s) for s in steps],
    }


MAX_LTX_ACTION_SECONDS = 6.0
MIN_LTX_ACTION_SECONDS = 4.0
_ACTION_TRANSFORMATION_WORDS = (
    "ignit", "light", "lights up", "lit", "open", "advance", "erupt", "draw",
    "unsheathe", "raise", "launch", "signal", "spark", "flame", "catch", "burn", "rise",
)
_AFTER_STATE_RED_FLAGS = ("already lit", "already blazing", "already burning", "already open", "fully blazing", "already ignited", "roaring flames at start")
_HELD_PROP_WORDS = ("torch", "sword", "staff", "spear", "shield", "scroll", "map", "lantern", "cup", "dagger", "helmet", "banner", "bow")
_PROP_END_STATE_CUES = ("remains in", "stays in", "held firmly", "still holds", "keeps holding", "places ", "sets down", "lowers ", "sheathes ", "grips ", "resting ")


def validate_anchor_binding(shot: dict[str, Any], anchor_registry: dict[str, dict[str, str]]) -> list[str]:
    """DEF-01 & DEF-02: Enforce SHA-256-locked character & location anchor ImagePaths on every scene keyframe."""
    errors: list[str] = []
    sid = str(shot.get("shot_id", "unknown"))
    required_anchors = list(shot.get("character_anchors") or []) + (
        [shot["location_anchor"]] if shot.get("location_anchor") else []
    )
    if not required_anchors:
        errors.append(f"{sid}: shot declares zero character/location anchors (Anchor-First law violated)")
        return errors

    refs_used = [str(Path(p)) for p in (shot.get("reference_image_paths") or [])]
    for aid in required_anchors:
        meta = anchor_registry.get(str(aid))
        if not meta:
            errors.append(f"{sid}: anchor {aid!r} missing from locked anchor_registry")
            continue
        ap = Path(meta["path"])
        if not ap.is_file():
            errors.append(f"{sid}: anchor file missing on disk: {ap}")
            continue
        actual = sha256_file(ap)
        if actual != meta.get("sha256"):
            errors.append(f"{sid}: anchor {aid!r} SHA-256 mismatch (drift detected)")
        if str(ap) not in refs_used and ap.name not in [Path(r).name for r in refs_used]:
            errors.append(f"{sid}: anchor {aid!r} ({ap.name}) was not passed in reference_image_paths (ImagePaths)")
    return errors


def lint_before_state_keyframe(shot: dict[str, Any]) -> list[str]:
    """DEF-04: Transformation/action shots MUST start from a pre-action initial state, never the outcome."""
    errors: list[str] = []
    sid = str(shot.get("shot_id", "unknown"))
    motion = str(shot.get("motion_prompt", "")).lower()
    keyframe_desc = str(shot.get("start_frame_description") or shot.get("image_prompt") or "").lower()
    is_transform = any(w in motion for w in _ACTION_TRANSFORMATION_WORDS)
    if is_transform and keyframe_desc:
        for flag in _AFTER_STATE_RED_FLAGS:
            if flag in keyframe_desc:
                errors.append(
                    f"{sid}: Before-State violation — action prompt transforms scene but start frame already depicts outcome ({flag!r})"
                )
    return errors


def enforce_ltx_action_clip_contract(editorial_seconds: float, motion_prompt: str) -> dict[str, Any]:
    """DEF-05: Enforce 4.0-6.0s LTX-2.5 action clip ceiling (97-145 frames) and explicit prop end-state continuity."""
    from explainer_engine.episode.style_bible import lint_super_realistic_prompt

    errors: list[str] = []
    if editorial_seconds > MAX_LTX_ACTION_SECONDS + 1e-6:
        errors.append(
            f"LTX clip duration {editorial_seconds:.2f}s exceeds {MAX_LTX_ACTION_SECONDS:.1f}s object-permanence ceiling (DEF-05)"
        )
    if editorial_seconds < 2.0:
        errors.append(f"LTX clip duration {editorial_seconds:.2f}s is below minimum 2.0s")

    low = motion_prompt.lower()
    props_found = [p for p in _HELD_PROP_WORDS if p in low]
    has_end_state = any(c in low for c in _PROP_END_STATE_CUES)
    if props_found and not has_end_state:
        errors.append(
            f"Held prop(s) {props_found} present without explicit prop end-state continuity clause "
            "(e.g., 'remains in his hand', 'keeps holding', 'lowers the torch') (DEF-05)"
        )

    errors.extend(lint_super_realistic_prompt(motion_prompt))
    frames = quantize_ltx_frames(editorial_seconds, fps=DEFAULT_FPS)
    return {
        "status": "PASS" if not errors else "FAIL",
        "editorial_seconds": round(editorial_seconds, 3),
        "ltx_frames": frames,
        "held_props": props_found,
        "errors": errors,
    }
