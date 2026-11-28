"""Voice-First Audio-Driven Acting & Close-Up Lip-Sync Pipeline (LTX-2 A2V + LatentSync 1.5/1.6 + MuseTalk 1.5).

Replaces restrictive close-up dialogue bans with an active two-stage cinema solution built for
drama-first docudramas and "What If" miniseries (80%+ live dramatic scenes with heavy close-up dialogue):

1. **Voice-First Audio Driver (Stage 1):** Synthesize or record the actor's dialogue WAV first
   (48 kHz master + 16 kHz mono Whisper/SyncNet analysis copy) so cadence, breath, emotion,
   and exact phoneme timing drive the visual performance.
2. **Audio-Conditioned Acting + Pixel-Accurate Lip-Sync (Stage 2):**
   - ``ltx_a2v``: LTX-2 Image + Audio-to-Video conditioning (freezes the dialogue WAV during
     diffusion so eyes, brow, head turns, and body language act directly to the spoken voice).
   - ``latentsync_1_5`` / ``latentsync_1_6``: ByteDance LatentSync (Apache-2.0) diffusion-based
     lip-sync refinement pass directly over the rendered LTX clip, preserving 35mm lighting,
     film grain, and facial identity while locking phoneme-accurate mouth/teeth motion.
   - ``musetalk_1_5``: TMElyralab MuseTalk 1.5 real-time latent-space lip-sync fallback.

Fail-closed (BP-205 as decided 2026-11-27): a speaking close-up is accepted only with its voice-first WAV pinned by
sha256, a refinement pass and a passing mouth-to-voice sync gate (``qa.cinema_gates.check_mouth_motion_sync``). A wider
dialogue shot without a WAV keeps the clip-spoken LTX route; with a WAV it is driven by the audio (``a2v``).
"""
from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from explainer_engine.core.errors import ContractError

CLOSE_UP_SCALES = frozenset({"close_up", "extreme_close_up", "medium_close_up"})
SUPPORTED_LIPSYNC_BACKENDS = frozenset({"ltx_a2v", "latentsync_1_5", "latentsync_1_6", "musetalk_1_5"})


@dataclass(slots=True)
class DialogueLipSyncPlan:
    shot_id: str
    shot_scale: str
    camera_framing: str
    route: str
    primary_engine: str
    refinement_backend: str | None
    requires_voice_first_wav: bool
    audio_driver_path: str
    inference_steps: int
    guidance_scale: float
    min_syncnet_confidence: float
    prompt_directive: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_dialogue_lipsync_route(
    *,
    shot_id: str = "dialogue_shot",
    spoken_line: str | None,
    shot_scale: str | None = None,
    camera_framing: str | None = None,
    audio_driver_path: str | Path | None = None,
    preferred_backend: str = "latentsync_1_5",
) -> DialogueLipSyncPlan:
    """Plan the optimal voice-first acting + lip-sync pipeline for any dialogue shot.

    NEVER bans close-up or medium-close-up dialogue; instead, automatically enables:
    - Voice-first audio-to-video conditioning (``ltx_a2v``), PLUS
    - Diffusion lip-sync refinement (``latentsync_1_5`` / ``latentsync_1_6`` / ``musetalk_1_5``)
      whenever the shot is a close-up or frontal dialogue shot.
    """
    if preferred_backend not in SUPPORTED_LIPSYNC_BACKENDS:
        raise ValueError(
            f"Unsupported lipsync backend {preferred_backend!r}; expected one of {sorted(SUPPORTED_LIPSYNC_BACKENDS)}"
        )

    scale = str(shot_scale or "medium").strip().lower().replace("-", "_").replace(" ", "_")
    framing = str(camera_framing or "unspecified").strip().lower().replace("-", "_").replace(" ", "_")
    driver = str(audio_driver_path or "").strip()

    if not spoken_line or not str(spoken_line).strip():
        return DialogueLipSyncPlan(
            shot_id=shot_id,
            shot_scale=scale,
            camera_framing=framing,
            route="silent_ltx_i2v",
            primary_engine="ltx_i2v",
            refinement_backend=None,
            requires_voice_first_wav=False,
            audio_driver_path="",
            inference_steps=0,
            guidance_scale=0.0,
            min_syncnet_confidence=0.0,
            prompt_directive=(
                "Nobody speaks. No dialogue. Mouth remains naturally closed throughout; "
                "silent breathing only, zero lip movement or speaking."
            ),
        )

    is_close_or_frontal = scale in CLOSE_UP_SCALES or framing in {"frontal", "front"}
    if is_close_or_frontal:
        ref_backend = preferred_backend if preferred_backend != "ltx_a2v" else "latentsync_1_5"
        return DialogueLipSyncPlan(
            shot_id=shot_id,
            shot_scale=scale,
            camera_framing=framing,
            route="ltx_a2v_plus_lipsync_refinement",
            primary_engine="ltx_a2v",
            refinement_backend=ref_backend,
            requires_voice_first_wav=True,
            audio_driver_path=driver,
            inference_steps=25 if ref_backend.startswith("latentsync") else 1,
            guidance_scale=1.5 if ref_backend.startswith("latentsync") else 1.0,
            min_syncnet_confidence=3.5,
            prompt_directive=(
                "Audio-driven cinema close-up acting: eyes, brows, jaw, and head react organically "
                "to the voice cadence; natural lip-sync articulation, subtle micro-expressions, "
                "lips close cleanly at sentence end."
            ),
        )

    if not driver:
        # No voice-first WAV for a wider shot: the clip speaks its line itself (D-131), as before this route existed.
        return DialogueLipSyncPlan(
            shot_id=shot_id,
            shot_scale=scale,
            camera_framing=framing,
            route="ltx_i2v_clip_spoken",
            primary_engine="ltx_i2v",
            refinement_backend=None,
            requires_voice_first_wav=False,
            audio_driver_path="",
            inference_steps=0,
            guidance_scale=0.0,
            min_syncnet_confidence=0.0,
            prompt_directive="Natural jaw cadence, motivated eye-line, lips close cleanly at sentence end.",
        )

    return DialogueLipSyncPlan(
        shot_id=shot_id,
        shot_scale=scale,
        camera_framing=framing,
        route="ltx_a2v_direct",
        primary_engine="ltx_a2v",
        refinement_backend=None,
        requires_voice_first_wav=True,
        audio_driver_path=driver,
        inference_steps=0,
        guidance_scale=0.0,
        min_syncnet_confidence=2.5,
        prompt_directive=(
            "Audio-driven cinema dialogue acting: natural jaw cadence, expressive shoulder/head "
            "blocking, motivated eye-line, lips close cleanly at sentence end."
        ),
    )


def require_voice_first_inputs(plan: DialogueLipSyncPlan) -> dict[str, Any]:
    """Fail closed before anything is rendered: an audio-driven plan needs its WAV on disk, pinned by sha256, and a
    close-up needs its refinement pass. Returns the ``audio`` block an ``a2v`` request carries (empty without audio)."""
    if not plan.requires_voice_first_wav:
        return {}
    wav = Path(plan.audio_driver_path) if plan.audio_driver_path else None
    if wav is None or not wav.is_file():
        raise ContractError(
            f"{plan.shot_id}: route {plan.route} needs the voice-first dialogue WAV first (audio_driver_path), "
            f"got {plan.audio_driver_path or 'none'}"
        )
    if plan.route == "ltx_a2v_plus_lipsync_refinement" and plan.refinement_backend not in SUPPORTED_LIPSYNC_BACKENDS - {"ltx_a2v"}:
        raise ContractError(f"{plan.shot_id}: a speaking close-up needs a lip-sync refinement backend")
    digest = hashlib.sha256(wav.read_bytes()).hexdigest()
    return {"path": str(wav), "sha256": digest}


def build_lipsync_refinement_command(
    *,
    backend: str,
    video_path: Path,
    audio_wav_path: Path,
    out_mp4: Path,
    inference_steps: int = 25,
    guidance_scale: float = 1.5,
    seed: int = 1247,
) -> dict[str, Any]:
    """Build a reproducible CLI / Modal worker payload for LatentSync 1.5/1.6 or MuseTalk 1.5 refinement."""
    if backend not in SUPPORTED_LIPSYNC_BACKENDS or backend == "ltx_a2v":
        raise ValueError(f"Refinement backend must be latentsync_1_5, latentsync_1_6, or musetalk_1_5; got {backend!r}")

    if backend in {"latentsync_1_5", "latentsync_1_6"}:
        cfg = "configs/unet/stage2_512.yaml" if backend == "latentsync_1_6" else "configs/unet/stage2.yaml"
        vram_gb = 18 if backend == "latentsync_1_6" else 8
        cmd = [
            "python",
            "-m",
            "scripts.inference",
            "--unet_config_path",
            cfg,
            "--inference_ckpt_path",
            "checkpoints/latentsync_unet.pt",
            "--inference_steps",
            str(int(inference_steps)),
            "--guidance_scale",
            f"{float(guidance_scale):.2f}",
            "--video_path",
            str(video_path),
            "--audio_path",
            str(audio_wav_path),
            "--video_out_path",
            str(out_mp4),
            "--seed",
            str(int(seed)),
        ]
        return {
            "schema": "lipsync_refinement_job/1",
            "backend": backend,
            "repo": "https://github.com/bytedance/LatentSync",
            "license": "Apache-2.0",
            "min_vram_gb": vram_gb,
            "video_path": str(video_path),
            "audio_wav_path": str(audio_wav_path),
            "out_mp4": str(out_mp4),
            "cmd": cmd,
        }

    # musetalk_1_5
    cmd = [
        "python",
        "-m",
        "scripts.inference",
        "--version",
        "v15",
        "--unet_model_path",
        "models/musetalkV15/unet.pth",
        "--unet_config",
        "models/musetalkV15/musetalk.json",
        "--video_path",
        str(video_path),
        "--audio_path",
        str(audio_wav_path),
        "--result_dir",
        str(out_mp4.parent),
    ]
    return {
        "schema": "lipsync_refinement_job/1",
        "backend": "musetalk_1_5",
        "repo": "https://github.com/TMElyralab/MuseTalk",
        "license": "MIT",
        "min_vram_gb": 8,
        "video_path": str(video_path),
        "audio_wav_path": str(audio_wav_path),
        "out_mp4": str(out_mp4),
        "cmd": cmd,
    }


__all__ = [
    "CLOSE_UP_SCALES",
    "DialogueLipSyncPlan",
    "SUPPORTED_LIPSYNC_BACKENDS",
    "build_lipsync_refinement_command",
    "plan_dialogue_lipsync_route",
    "require_voice_first_inputs",
]
