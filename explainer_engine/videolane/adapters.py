"""Interchangeable Still Upscaler, Video Upscaler, and LTX Video Generation adapters.

Strictly separates still-image upscaling from video upscaling (never sharing one callback
across fundamentally different media types) and isolates paid GPU execution from the
deterministic Episode runner via explicit approval + spend-ledger contracts.
"""
from __future__ import annotations

import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from PIL import Image, ImageFilter

from explainer_engine.core import approvals, spend_ledger
from explainer_engine.core.errors import ContractError

TARGET_2K_SIZE = (2560, 1440)


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


class StillUpscalerAdapter(Protocol):
    """Upscale a single still image (e.g., extracted continuation tail frame) to 2K."""

    backend_name: str

    def upscale_still(self, image_path: Path, out_path: Path, *, target_size: tuple[int, int] = TARGET_2K_SIZE) -> dict[str, Any]: ...


class VideoUpscalerAdapter(Protocol):
    """Upscale an entire video clip while preserving audio and frame cadence."""

    backend_name: str

    def upscale_video(self, video_path: Path, out_path: Path, *, target_size: tuple[int, int] = TARGET_2K_SIZE) -> dict[str, Any]: ...


class LTXGenerationAdapter(Protocol):
    """Generate a video clip from a photo-grounded LTX request."""

    backend_name: str

    def generate_clip(self, request: dict[str, Any], out_path: Path) -> dict[str, Any]: ...


class LocalStillUpscaler:
    """Deterministic local CPU still upscaler (Lanczos + subtle edge unsharp; Real-ESRGAN hook when weights exist)."""

    backend_name = "local_lanczos_unsharp_still"

    def upscale_still(
        self,
        image_path: Path,
        out_path: Path,
        *,
        target_size: tuple[int, int] = TARGET_2K_SIZE,
    ) -> dict[str, Any]:
        if not image_path.is_file():
            raise ContractError(f"Still image not found for upscaling: {image_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with Image.open(image_path) as im:
            rgb = im.convert("RGB")
            up = rgb.resize(target_size, Image.Resampling.LANCZOS)
            up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=95, threshold=2))
            up.save(out_path, format="PNG")
        return {
            "backend": self.backend_name,
            "input_path": str(image_path),
            "output_path": str(out_path),
            "width": target_size[0],
            "height": target_size[1],
            "sha256": _sha256(out_path),
        }


class LocalFFmpeg2KVideoUpscaler:
    """Deterministic local FFmpeg 2K video upscaler (Lanczos + Contrast Adaptive Sharpening, preserves audio)."""

    backend_name = "ffmpeg_2k_lanczos_cas"

    def upscale_video(
        self,
        video_path: Path,
        out_path: Path,
        *,
        target_size: tuple[int, int] = TARGET_2K_SIZE,
    ) -> dict[str, Any]:
        if not video_path.is_file():
            raise ContractError(f"Video clip not found for upscaling: {video_path}")
        out_path.parent.mkdir(parents=True, exist_ok=True)
        w, h = target_size
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(video_path),
            "-vf",
            f"scale={w}:{h}:flags=lanczos,cas=0.35",
            "-fps_mode",
            "passthrough",
            "-c:v",
            "libx264",
            "-crf",
            "18",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "copy",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)
        return {
            "backend": self.backend_name,
            "input_path": str(video_path),
            "output_path": str(out_path),
            "width": w,
            "height": h,
            "sha256": _sha256(out_path),
        }


class LocalRehearsalVideoAdapter:
    """Offline $0.00 FFmpeg rehearsal adapter animating a real start photo with subtle zoom + ambient noise.

    Explicitly marks ``rehearsal=True`` so rehearsal clips can NEVER masquerade as paid LTX production renders.
    """

    backend_name = "local_ffmpeg_rehearsal_only"

    def generate_clip(self, request: dict[str, Any], out_path: Path) -> dict[str, Any]:
        start_img = Path(request["start_image_path"])
        if not start_img.is_file():
            raise ContractError(f"Start image missing: {start_img}")
        frames = int(request.get("ltx_frames", 73))
        fps = int(request.get("fps", 24))
        dur = round(frames / fps, 4)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        cmd = [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-loop",
            "1",
            "-i",
            str(start_img),
            "-f",
            "lavfi",
            "-i",
            f"anoisesrc=color=pink:amplitude=0.06:duration={dur},pan=stereo|c0=c0|c1=0.9*c0",
            "-vf",
            f"scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,"
            f"zoompan=z='min(zoom+0.0012,1.15)':d={frames}:x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':s=1280x720:fps={fps}",
            "-t",
            f"{dur:.4f}",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            "-shortest",
            str(out_path),
        ]
        subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)
        return {
            "schema": "video_clip_record/1",
            "status": "REHEARSAL",
            "rehearsal": True,
            "backend": self.backend_name,
            "clip_path": str(out_path),
            "sha256": _sha256(out_path),
            "frames": frames,
            "fps": fps,
            "cost_usd": 0.0,
        }


@dataclass(frozen=True)
class GovernedModalLTXRequest:
    """Fail-closed preflight wrapper ensuring no Modal LTX call runs without approval + ledger reservation."""

    approval_id: str | None
    manifest: dict[str, Any]
    estimated_usd: float
    cap_usd: float
    item_id: str
    operation_mode: str = "modal-ltx-smoke"

    def validate_and_reserve(
        self,
        *,
        registry_path: Path | None = None,
        ledger_path: Path | None = None,
    ) -> dict[str, Any]:
        msha = approvals.canonical_manifest_sha256(self.manifest)
        proof = approvals.verify_approval(
            self.approval_id,
            provider="modal_modal1",
            operation_mode=self.operation_mode,
            manifest_sha256=msha,
            requested_usd=self.estimated_usd,
            registry_path=registry_path,
        )
        res = spend_ledger.reserve(
            "modal_modal1",
            self.item_id,
            self.estimated_usd,
            cap_usd=self.cap_usd,
            why=self.operation_mode,
            ledger_path=ledger_path,
        )
        return {"approval_proof": proof, "reservation": res, "manifest_sha256": msha}
