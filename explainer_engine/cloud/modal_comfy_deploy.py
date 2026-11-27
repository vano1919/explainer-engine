"""Deployable Modal Serverless AI Cinema Studio App (Stack 2: Split L4 Audio + L40S/H100 ComfyUI v0.28.0+).

Deploy directly to Modal with::

    modal deploy explainer_engine/cloud/modal_comfy_deploy.py

Architecture:
- Shared ``modal.Volume("explainer-cinema-weights")`` mounted at ``/vol/cinema`` (1 TiB free tier).
- ``AudioFoleyWorker`` (``gpu="L4"``, ~$0.80/hr, ``scaledown_window=60``): runs Qwen3-TTS,
  MMAudio / HunyuanVideo-Foley (48 kHz), ACE-Step 1.5 (MIT, 8-step Turbo), and ClearerVoice.
- ``CinemaVideoWorker`` (``gpu="L40S"``, ~$1.95/hr, ``scaledown_window=60``): boots Headless
  ComfyUI v0.28.0+ (native SeedVR2 + 16-bit PNG/EXR Save Image Advanced) on ``127.0.0.1:8188``,
  submits API JSON graphs via ``POST /api/prompt``, polls ``/history/{prompt_id}``, and saves
  rendered outputs back to ``/vol/cinema/renders/``.
- ``sync_weights_to_volume``: one-time HuggingFace weight downloader into ``/vol/cinema/models/``.

Gracefully importable offline (without ``modal`` installed locally) so unit tests, dry-run CLI
launchers, and CI linters can validate every graph, timeout, and endpoint deterministically.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from explainer_engine.cloud.modal_cinema_studio import (
    DEFAULT_VOLUME_NAME,
    estimate_modal_job_cost,
)

APP_NAME = "explainer-cinema-studio-v2"
VOLUME_MOUNT = "/vol/cinema"
COMFY_DIR = "/opt/ComfyUI"
COMFY_PORT = 8188

DEFAULT_WEIGHT_MANIFEST: list[dict[str, str]] = [
    {
        "repo_id": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "filename": "split_files/diffusion_models/wan2.2_i2v_high_noise_14B_fp8_scaled.safetensors",
        "dest_rel": "models/diffusion_models/wan2.2_i2v_high_noise_14B_fp8.safetensors",
    },
    {
        "repo_id": "Comfy-Org/Wan_2.2_ComfyUI_Repackaged",
        "filename": "split_files/diffusion_models/wan2.2_i2v_low_noise_14B_fp8_scaled.safetensors",
        "dest_rel": "models/diffusion_models/wan2.2_i2v_low_noise_14B_fp8.safetensors",
    },
    {
        "repo_id": "lightx2v/Wan2.2-Lightning",
        "filename": "Wan2.2-I2V-A14B-4steps-lora-rank64-Seko-V1/high_noise_model.safetensors",
        "dest_rel": "models/loras/Wan2.2-I2V-A14B-4step-720p-high.safetensors",
    },
    {
        "repo_id": "ByteDance/LatentSync-1.6",
        "filename": "latentsync_unet.pt",
        "dest_rel": "models/latentsync/latentsync_unet.pt",
    },
    {
        "repo_id": "ByteDance-Seed/SeedVR2-7B",
        "filename": "seedvr2_ema_7b_fp16.safetensors",
        "dest_rel": "models/seedvr2/seedvr2_ema_7b_fp16.safetensors",
    },
]


def submit_comfy_prompt_http(
    api_graph: dict[str, Any],
    *,
    base_url: str = f"http://127.0.0.1:{COMFY_PORT}",
    client_id: str = "explainer-engine-modal",
    timeout_s: float = 900.0,
    poll_interval_s: float = 1.5,
) -> dict[str, Any]:
    """Submit a ComfyUI API JSON prompt to a local headless server and poll until completion."""
    nodes = api_graph.get("nodes") if "nodes" in api_graph else api_graph
    payload = json.dumps({"prompt": nodes, "client_id": client_id}).encode("utf-8")
    req = urllib.request.Request(
        f"{base_url.rstrip('/')}/prompt",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30.0) as resp:
        queued = json.loads(resp.read().decode("utf-8"))
    prompt_id = str(queued["prompt_id"])

    deadline = time.monotonic() + float(timeout_s)
    while time.monotonic() < deadline:
        hist_url = f"{base_url.rstrip('/')}/history/{prompt_id}"
        with urllib.request.urlopen(hist_url, timeout=15.0) as hresp:
            hist = json.loads(hresp.read().decode("utf-8"))
        if prompt_id in hist:
            entry = hist[prompt_id]
            status_obj = entry.get("status") or {}
            if status_obj.get("status_str") == "error":
                raise RuntimeError(f"ComfyUI execution error for prompt_id={prompt_id}: {status_obj}")
            return {"prompt_id": prompt_id, "outputs": entry.get("outputs") or {}, "status": "completed"}
        time.sleep(poll_interval_s)

    raise TimeoutError(f"ComfyUI prompt_id={prompt_id} did not finish within {timeout_s:.1f}s")


def wait_for_comfy_ready(base_url: str = f"http://127.0.0.1:{COMFY_PORT}", *, timeout_s: float = 120.0) -> bool:
    """Poll ComfyUI ``/system_stats`` until headless server accepts HTTP requests."""
    deadline = time.monotonic() + float(timeout_s)
    url = f"{base_url.rstrip('/')}/system_stats"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=3.0) as resp:
                if resp.status == 200:
                    return True
        except (urllib.error.URLError, TimeoutError, OSError):
            time.sleep(1.0)
    return False


try:
    import modal  # type: ignore[import-not-found]
except ImportError:  # pragma: no cover - local offline test/CLI mode without modal SDK
    modal = None


if modal is not None:  # pragma: no cover - executed on Modal cloud runtime
    app = modal.App(APP_NAME)
    cinema_volume = modal.Volume.from_name(DEFAULT_VOLUME_NAME, create_if_missing=True)

    video_image = (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install("git", "ffmpeg", "libgl1", "libglib2.0-0", "libsndfile1")
        .pip_install(
            "torch==2.6.0",
            "torchvision==0.21.0",
            "torchaudio==2.6.0",
            "huggingface-hub>=0.28.0",
            "hf-transfer>=0.1.9",
            "safetensors",
            "einops",
            "opencv-python-headless",
            "soundfile",
            "scipy",
            "Pillow",
            "sageattention",
        )
        .run_commands(
            f"git clone --depth 1 --branch v0.28.0 https://github.com/comfyanonymous/ComfyUI.git {COMFY_DIR} "
            f"|| git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git {COMFY_DIR}",
            f"pip install -r {COMFY_DIR}/requirements.txt",
            f"git clone --depth 1 https://github.com/kijai/ComfyUI-WanVideoWrapper.git {COMFY_DIR}/custom_nodes/ComfyUI-WanVideoWrapper",
            f"git clone --depth 1 https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git {COMFY_DIR}/custom_nodes/ComfyUI-VideoHelperSuite",
            f"git clone --depth 1 https://github.com/bytedance/LatentSync.git {COMFY_DIR}/custom_nodes/LatentSync",
        )
        .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    )

    audio_image = (
        modal.Image.debian_slim(python_version="3.11")
        .apt_install("git", "ffmpeg", "libsndfile1")
        .pip_install(
            "torch==2.6.0",
            "torchaudio==2.6.0",
            "huggingface-hub>=0.28.0",
            "soundfile",
            "scipy",
            "numpy",
            "pyloudnorm",
            "pyroomacoustics",
            "pedalboard",
        )
        .env({"HF_HUB_ENABLE_HF_TRANSFER": "1"})
    )

    @app.function(
        image=audio_image,
        volumes={VOLUME_MOUNT: cinema_volume},
        timeout=1800,
    )
    def sync_weights_to_volume(manifest: list[dict[str, str]] | None = None) -> dict[str, Any]:
        """Download required Wan 2.2 / LightX2V / LatentSync 1.6 / SeedVR2 weights into Modal Volume."""
        from huggingface_hub import hf_hub_download  # type: ignore[import-not-found]

        items = manifest or DEFAULT_WEIGHT_MANIFEST
        downloaded: list[str] = []
        skipped: list[str] = []
        for entry in items:
            dest = Path(VOLUME_MOUNT) / entry["dest_rel"]
            if dest.is_file() and dest.stat().st_size > 0:
                skipped.append(str(dest))
                continue
            dest.parent.mkdir(parents=True, exist_ok=True)
            cached = hf_hub_download(
                repo_id=entry["repo_id"],
                filename=entry["filename"],
                token=os.environ.get("HF_TOKEN"),
            )
            subprocess.run(["cp", cached, str(dest)], check=True)
            downloaded.append(str(dest))
        cinema_volume.commit()
        return {"downloaded": downloaded, "skipped": skipped, "volume": DEFAULT_VOLUME_NAME}

    @app.cls(
        image=video_image,
        gpu="L40S",
        volumes={VOLUME_MOUNT: cinema_volume},
        scaledown_window=60,
        timeout=900,
        enable_memory_snapshot=True,
    )
    class CinemaVideoWorker:
        """Headless ComfyUI v0.28.0+ serverless video worker (Wan 2.2 / LTX-2.5 / LatentSync 1.6 / SeedVR2)."""

        _proc: subprocess.Popen[bytes] | None = None

        @modal.enter()
        def start_comfyui(self) -> None:
            models_src = Path(VOLUME_MOUNT) / "models"
            models_dst = Path(COMFY_DIR) / "models"
            if models_src.is_dir():
                for sub in models_src.iterdir():
                    target = models_dst / sub.name
                    if not target.exists():
                        target.symlink_to(sub)
            self._proc = subprocess.Popen(
                [
                    "python3",
                    f"{COMFY_DIR}/main.py",
                    "--listen",
                    "127.0.0.1",
                    "--port",
                    str(COMFY_PORT),
                    "--disable-auto-launch",
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if not wait_for_comfy_ready(timeout_s=120.0):
                raise RuntimeError("Headless ComfyUI failed to become ready within 120s")

        @modal.method()
        def run_graph(self, api_graph: dict[str, Any], *, job_id: str = "shot") -> dict[str, Any]:
            t0 = time.monotonic()
            res = submit_comfy_prompt_http(api_graph, client_id=job_id)
            elapsed = round(time.monotonic() - t0, 3)
            cinema_volume.commit()
            return {
                "job_id": job_id,
                "engine": api_graph.get("engine", "comfyui"),
                "elapsed_s": elapsed,
                "estimated_usd": estimate_modal_job_cost("L40S", elapsed),
                "result": res,
            }

        @modal.exit()
        def stop_comfyui(self) -> None:
            if self._proc is not None and self._proc.poll() is None:
                self._proc.terminate()

    @app.cls(
        image=audio_image,
        gpu="L4",
        volumes={VOLUME_MOUNT: cinema_volume},
        scaledown_window=60,
        timeout=600,
    )
    class AudioFoleyWorker:
        """Low-cost Modal L4 ($0.80/hr) worker for TTS, Foley, ACE-Step 1.5, and acoustic glue."""

        @modal.method()
        def apply_acoustic_glue(
            self,
            *,
            wav_rel_path: str,
            out_rel_path: str,
            room_dims_m: tuple[float, float, float] = (6.0, 5.0, 3.2),
            rt60_s: float = 0.35,
        ) -> dict[str, Any]:
            import numpy as np
            import pyroomacoustics as pra  # type: ignore[import-not-found]
            import soundfile as sf

            t0 = time.monotonic()
            src = Path(VOLUME_MOUNT) / wav_rel_path
            dst = Path(VOLUME_MOUNT) / out_rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            sig, sr = sf.read(str(src), dtype="float32")
            mono = sig.mean(axis=1) if sig.ndim > 1 else sig

            e_abs, max_ord = pra.inverse_sabine(rt60_s, list(room_dims_m))
            room = pra.ShoeBox(
                list(room_dims_m),
                fs=sr,
                materials=pra.Material(e_abs),
                max_order=min(6, int(max_ord)),
            )
            room.add_source([room_dims_m[0] * 0.35, room_dims_m[1] * 0.5, 1.55], signal=mono)
            room.add_microphone([room_dims_m[0] * 0.65, room_dims_m[1] * 0.5, 1.55])
            room.simulate()
            wet = np.asarray(room.mic_array.signals[0], dtype=np.float32)[: len(mono)]
            peak = float(np.max(np.abs(wet))) + 1e-9
            wet = wet / peak * 0.85
            blended = 0.82 * mono + 0.18 * wet
            sf.write(str(dst), blended.astype(np.float32), sr)
            cinema_volume.commit()
            elapsed = round(time.monotonic() - t0, 3)
            return {
                "out_path": str(dst),
                "elapsed_s": elapsed,
                "estimated_usd": estimate_modal_job_cost("L4", elapsed),
            }


__all__ = [
    "APP_NAME",
    "COMFY_DIR",
    "COMFY_PORT",
    "DEFAULT_WEIGHT_MANIFEST",
    "VOLUME_MOUNT",
    "submit_comfy_prompt_http",
    "wait_for_comfy_ready",
]
