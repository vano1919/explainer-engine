"""Modal Serverless AI Cinema Studio (Stack 2: Split L4 Audio + L40S/H100 ComfyUI v0.28.0+ Workers).

Implements the November 2026 production architecture inside ``explainer-engine``:
- **Split Worker Tiers** (zero idle GPU bleed, scale-to-zero after 60s):
  1. ``AudioFoleyWorker`` (Modal ``L4``, ~$0.80/hr): Qwen3-TTS, MMAudio / HunyuanVideo-Foley (48 kHz),
     ACE-Step 1.5 (MIT, <8 GB VRAM, 8-step Turbo), ClearerVoice/MossFormer2, pyroomacoustics RIR.
  2. ``CinemaVideoWorker`` (Modal ``L40S`` $1.95/hr or ``H100`` $3.95/hr): Headless ComfyUI v0.28.0+
     (16-bit PNG/EXR Save Image Advanced + native SeedVR2), shared ``modal.Volume`` (1 TiB free),
     Wan 2.2 14B (``fp8_e4m3fn_fast`` + SageAttention 2.2 + LightX2V 4-8 step), LTX-2.5 A2V,
     InfiniteTalk / MultiTalk / LatentSync 1.6.
- **Hard Quality & Cost Guardrails**:
  - Episode hard budget cap defaulting to **$10.00** (mandatory 80% / **$8.00** checkpoint).
  - Forbids ``NVFP4`` quantization on Wan 2.2 Low-Noise expert (prevents detail mosaic artifacts; min ``FP8``).
  - Enforces ``>= 0.5s`` trailing silence padding on LatentSync 1.6 audio inputs (prevents last-word clipping).
  - Enforces ``batch_size = 4n+1 >= 5`` and ``blocks_to_swap >= 16`` on native ComfyUI ``SeedVR2``.
"""
from __future__ import annotations

import sqlite3
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

MODAL_GPU_HOURLY_USD: dict[str, float] = {
    "CPU": 0.047,
    "L4": 0.80,
    "A10G": 1.10,
    "L40S": 1.95,
    "A100-80GB": 2.50,
    "H100": 3.95,
}

DEFAULT_EPISODE_BUDGET_CAP_USD = 10.00
DEFAULT_CHECKPOINT_RATIO = 0.80
MIN_LATENTSYNC_SILENCE_PAD_S = 0.50
DEFAULT_VOLUME_NAME = "explainer-cinema-weights"


@dataclass(slots=True)
class SpendRecord:
    job_id: str
    category: str  # modal_gpu | api_lipsync | api_video | api_tts
    provider: str
    estimated_usd: float
    actual_usd: float | None = None
    status: str = "RESERVED"  # RESERVED | SETTLED | RELEASED


@dataclass(slots=True)
class EpisodeBudgetGuard:
    """Enforces a strict per-episode hard USD cap ($10.00 default) with 80% ($8.00) checkpoint.

    When ``db_path`` is supplied, persists every reservation and settlement atomically to a
    SQLite WAL database so crash recovery never forgets prior Modal/API spend.
    """

    episode_id: str
    cap_usd: float = DEFAULT_EPISODE_BUDGET_CAP_USD
    checkpoint_ratio: float = DEFAULT_CHECKPOINT_RATIO
    records: list[SpendRecord] = field(default_factory=list)
    db_path: Path | None = None

    def __post_init__(self) -> None:
        if self.db_path is not None:
            self.db_path = Path(self.db_path)
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            self._init_db()
            self._load_from_db()

    def _connect(self) -> sqlite3.Connection:
        assert self.db_path is not None
        conn = sqlite3.connect(str(self.db_path), timeout=15.0)
        conn.execute("PRAGMA journal_mode=WAL;")
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS episode_spend (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    episode_id TEXT NOT NULL,
                    job_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    estimated_usd REAL NOT NULL,
                    actual_usd REAL,
                    status TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def _load_from_db(self) -> None:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT job_id, category, provider, estimated_usd, actual_usd, status "
                "FROM episode_spend WHERE episode_id = ? ORDER BY id ASC",
                (self.episode_id,),
            ).fetchall()
        self.records = [
            SpendRecord(
                job_id=str(r[0]),
                category=str(r[1]),
                provider=str(r[2]),
                estimated_usd=float(r[3]),
                actual_usd=float(r[4]) if r[4] is not None else None,
                status=str(r[5]),
            )
            for r in rows
        ]

    @property
    def checkpoint_usd(self) -> float:
        return round(self.cap_usd * self.checkpoint_ratio, 4)

    @property
    def committed_usd(self) -> float:
        if self.db_path is not None:
            self._load_from_db()
        total = 0.0
        for r in self.records:
            if r.status == "SETTLED" and r.actual_usd is not None:
                total += r.actual_usd
            elif r.status == "RESERVED":
                total += r.estimated_usd
        return round(total, 4)

    @property
    def remaining_usd(self) -> float:
        return round(max(0.0, self.cap_usd - self.committed_usd), 4)

    def reserve(self, *, job_id: str, category: str, provider: str, estimated_usd: float) -> dict[str, Any]:
        est = max(0.0, float(estimated_usd))
        projected = round(self.committed_usd + est, 4)
        if projected > self.cap_usd + 1e-9:
            raise RuntimeError(
                f"Episode {self.episode_id!r} hard budget cap exceeded: "
                f"committed=${self.committed_usd:.2f} + est=${est:.2f} = ${projected:.2f} > cap=${self.cap_usd:.2f}"
            )
        rec = SpendRecord(job_id=job_id, category=category, provider=provider, estimated_usd=est)
        if self.db_path is not None:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                conn.execute(
                    "INSERT INTO episode_spend (episode_id, job_id, category, provider, estimated_usd, actual_usd, status) "
                    "VALUES (?, ?, ?, ?, ?, NULL, 'RESERVED')",
                    (self.episode_id, job_id, category, provider, est),
                )
                conn.commit()
        self.records.append(rec)
        return {
            "job_id": job_id,
            "committed_usd": projected,
            "remaining_usd": self.remaining_usd,
            "checkpoint_reached": projected >= self.checkpoint_usd,
            "checkpoint_usd": self.checkpoint_usd,
            "cap_usd": self.cap_usd,
        }

    def settle(self, job_id: str, *, actual_usd: float) -> dict[str, Any]:
        act = max(0.0, float(actual_usd))
        if self.db_path is not None:
            with self._connect() as conn:
                conn.execute("BEGIN IMMEDIATE")
                row = conn.execute(
                    "SELECT id FROM episode_spend WHERE episode_id = ? AND job_id = ? AND status = 'RESERVED' ORDER BY id DESC LIMIT 1",
                    (self.episode_id, job_id),
                ).fetchone()
                if row is None:
                    raise KeyError(f"No open RESERVED spend record found for job_id={job_id!r}")
                conn.execute(
                    "UPDATE episode_spend SET actual_usd = ?, status = 'SETTLED' WHERE id = ?",
                    (act, int(row[0])),
                )
                conn.commit()
            self._load_from_db()
            return {
                "job_id": job_id,
                "actual_usd": act,
                "committed_usd": self.committed_usd,
                "remaining_usd": self.remaining_usd,
            }
        for r in reversed(self.records):
            if r.job_id == job_id and r.status == "RESERVED":
                r.actual_usd = act
                r.status = "SETTLED"
                return {
                    "job_id": job_id,
                    "actual_usd": r.actual_usd,
                    "committed_usd": self.committed_usd,
                    "remaining_usd": self.remaining_usd,
                }
        raise KeyError(f"No open RESERVED spend record found for job_id={job_id!r}")

    def summary(self) -> dict[str, Any]:
        committed = self.committed_usd
        return {
            "episode_id": self.episode_id,
            "cap_usd": self.cap_usd,
            "checkpoint_usd": self.checkpoint_usd,
            "committed_usd": committed,
            "remaining_usd": round(max(0.0, self.cap_usd - committed), 4),
            "checkpoint_reached": committed >= self.checkpoint_usd,
            "db_path": str(self.db_path) if self.db_path is not None else None,
            "records": [asdict(r) for r in self.records],
        }


def estimate_modal_job_cost(gpu: str, runtime_s: float, *, cpu_cores: int = 4, ram_gib: int = 16) -> float:
    """Estimate Modal serverless job cost including GPU + CPU + RAM overhead."""
    gpu_key = gpu.upper()
    if gpu_key not in MODAL_GPU_HOURLY_USD:
        raise ValueError(f"Unsupported Modal GPU tier {gpu!r}; expected one of {sorted(MODAL_GPU_HOURLY_USD)}")
    hours = max(0.0, float(runtime_s)) / 3600.0
    gpu_cost = MODAL_GPU_HOURLY_USD[gpu_key] * hours
    cpu_cost = (MODAL_GPU_HOURLY_USD["CPU"] * max(1, int(cpu_cores))) * hours
    ram_cost = (0.0080 * max(1, int(ram_gib))) * hours
    return round(gpu_cost + cpu_cost + ram_cost, 4)


def build_comfy_wan22_distilled_graph(
    *,
    prompt: str,
    start_image_name: str,
    width: int = 1280,
    height: int = 720,
    num_frames: int = 121,
    fps: int = 24,
    steps: int = 6,
    high_noise_dtype: str = "fp8_e4m3fn_fast",
    low_noise_dtype: str = "fp8_e4m3fn_fast",
    use_sage_attention: bool = True,
    use_lightx2v_lora: bool = True,
    seed: int = 42,
) -> dict[str, Any]:
    """Build a Headless ComfyUI v0.28.0+ API JSON graph for Wan 2.2 14B Distilled I2V.

    Hard Guard: NEVER allows ``nvfp4`` on the Low-Noise detail expert (prevents mosaic artifacts).
    """
    low_norm = str(low_noise_dtype).strip().lower()
    if "nvfp4" in low_norm or "int4" in low_norm or "fp4" in low_norm:
        raise ValueError(
            f"Forbidden low_noise_dtype={low_noise_dtype!r}: NVFP4/FP4 on Wan 2.2 Low-Noise expert "
            f"causes mosaic detail degradation; use 'fp8_e4m3fn_fast' or 'fp16' minimum."
        )
    if not (4 <= int(steps) <= 12):
        raise ValueError(f"LightX2V distilled Wan 2.2 steps must be in [4, 12], got {steps}")

    return {
        "schema": "comfyui_api_graph/1",
        "engine": "wan2.2_14b_i2v_distilled",
        "comfyui_min_version": "0.28.0",
        "gpu_tier": "L40S",
        "nodes": {
            "1": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "wan2.2_i2v_high_noise_14B_fp8.safetensors",
                    "weight_dtype": high_noise_dtype,
                },
            },
            "2": {
                "class_type": "UNETLoader",
                "inputs": {
                    "unet_name": "wan2.2_i2v_low_noise_14B_fp8.safetensors",
                    "weight_dtype": low_noise_dtype,
                },
            },
            "3": {
                "class_type": "PatchSageAttentionKJ" if use_sage_attention else "ModelPassthrough",
                "inputs": {"model": ["1", 0], "sage_attention": "auto"},
            },
            "4": {
                "class_type": "LoraLoaderModelOnly" if use_lightx2v_lora else "ModelPassthrough",
                "inputs": {
                    "model": ["3", 0],
                    "lora_name": "Wan2.2-I2V-A14B-4step-720p-high.safetensors",
                    "strength_model": 1.0,
                },
            },
            "5": {
                "class_type": "LoadImage",
                "inputs": {"image": start_image_name},
            },
            "6": {
                "class_type": "WanImageToVideo",
                "inputs": {
                    "positive": prompt.strip(),
                    "start_image": ["5", 0],
                    "width": int(width),
                    "height": int(height),
                    "length": int(num_frames),
                    "fps": int(fps),
                    "steps": int(steps),
                    "seed": int(seed),
                    "force_offload": True,
                },
            },
            "7": {
                "class_type": "SaveImageAdvanced",
                "inputs": {
                    "images": ["6", 0],
                    "bit_depth": "16bit_png",
                    "filename_prefix": "wan22_shot",
                },
            },
        },
    }


def pad_audio_for_latentsync(src_wav: Path, out_wav: Path, *, tail_silence_s: float = 0.60) -> Path:
    """Append >= 0.5s clean trailing silence to a dialogue WAV so LatentSync 1.6 never clips the last word."""
    if tail_silence_s < MIN_LATENTSYNC_SILENCE_PAD_S:
        raise ValueError(
            f"tail_silence_s={tail_silence_s:.2f}s < required minimum {MIN_LATENTSYNC_SILENCE_PAD_S:.2f}s for LatentSync"
        )
    if not src_wav.is_file():
        raise FileNotFoundError(f"Source dialogue WAV not found: {src_wav}")
    out_wav.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-v",
            "error",
            "-i",
            str(src_wav),
            "-af",
            f"apad=pad_dur={tail_silence_s:.3f}",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(out_wav),
        ],
        check=True,
    )
    return out_wav


def build_comfy_latentsync16_graph(
    *,
    video_name: str,
    padded_audio_wav_name: str,
    tail_silence_s: float = 0.60,
    inference_steps: int = 25,
    guidance_scale: float = 1.5,
    seed: int = 1247,
) -> dict[str, Any]:
    """Build a Headless ComfyUI API JSON graph for LatentSync 1.6 (18 GB VRAM, 512px TREPA)."""
    if tail_silence_s < MIN_LATENTSYNC_SILENCE_PAD_S:
        raise ValueError(
            f"LatentSync 1.6 requires >= {MIN_LATENTSYNC_SILENCE_PAD_S:.2f}s trailing silence padding; got {tail_silence_s:.2f}s"
        )
    if not (1.0 <= float(guidance_scale) <= 2.5):
        raise ValueError(f"LatentSync 1.6 guidance_scale must be in [1.0, 2.5] to avoid jaw jitter; got {guidance_scale}")
    return {
        "schema": "comfyui_api_graph/1",
        "engine": "latentsync_1_6",
        "gpu_tier": "L40S",
        "min_vram_gb": 18,
        "nodes": {
            "1": {"class_type": "VHS_LoadVideo", "inputs": {"video": video_name, "force_rate": 25}},
            "2": {"class_type": "LoadAudio", "inputs": {"audio": padded_audio_wav_name}},
            "3": {
                "class_type": "LatentSyncNode",
                "inputs": {
                    "images": ["1", 0],
                    "audio": ["2", 0],
                    "version": "1.6",
                    "resolution": 512,
                    "inference_steps": int(inference_steps),
                    "guidance_scale": round(float(guidance_scale), 2),
                    "seed": int(seed),
                    "tail_silence_verified_s": round(float(tail_silence_s), 2),
                },
            },
        },
    }


def build_comfy_seedvr2_graph(
    *,
    input_video_name: str,
    target_height: int = 1440,
    batch_size: int = 5,
    blocks_to_swap: int = 16,
    model_variant: str = "seedvr2_ema_7b_fp16.safetensors",
) -> dict[str, Any]:
    """Build a native ComfyUI v0.28.0+ SeedVR2 temporal 2K/4K upscaler graph.

    Enforces SeedVR2's temporal consistency law: ``batch_size`` MUST be ``4n + 1`` and ``>= 5`` (5, 9, 13, 17...).
    """
    b = int(batch_size)
    if b < 5 or (b - 1) % 4 != 0:
        raise ValueError(
            f"SeedVR2 temporal consistency requires batch_size = 4n+1 >= 5 (5, 9, 13, 17...); got {batch_size}"
        )
    return {
        "schema": "comfyui_api_graph/1",
        "engine": "seedvr2_native_comfyui",
        "comfyui_min_version": "0.28.0",
        "gpu_tier": "L40S",
        "nodes": {
            "1": {"class_type": "VHS_LoadVideo", "inputs": {"video": input_video_name}},
            "2": {
                "class_type": "SeedVR2VideoUpscaler",
                "inputs": {
                    "images": ["1", 0],
                    "model": model_variant,
                    "target_resolution": int(target_height),
                    "batch_size": b,
                    "blocks_to_swap": max(0, int(blocks_to_swap)),
                    "encode_tiled": True,
                    "decode_tiled": True,
                },
            },
        },
    }


def generate_modal_app_spec(
    *,
    app_name: str = "explainer-cinema-studio-v2",
    volume_name: str = DEFAULT_VOLUME_NAME,
    video_gpu: str = "L40S",
    audio_gpu: str = "L4",
    episode_cap_usd: float = DEFAULT_EPISODE_BUDGET_CAP_USD,
) -> dict[str, Any]:
    """Return the declarative Modal Serverless deployment blueprint for Stack 2 split workers."""
    return {
        "schema": "modal_cinema_studio_spec/1",
        "app_name": app_name,
        "volume": {"name": volume_name, "mount_path": "/vol/cinema", "free_tier_tib": 1.0},
        "budget_policy": {
            "episode_hard_cap_usd": round(float(episode_cap_usd), 2),
            "checkpoint_usd": round(float(episode_cap_usd) * DEFAULT_CHECKPOINT_RATIO, 2),
            "scale_to_zero_idle_s": 60,
            "enable_memory_snapshot": True,
        },
        "workers": [
            {
                "name": "audio_foley_worker",
                "gpu": audio_gpu,
                "hourly_usd": MODAL_GPU_HOURLY_USD[audio_gpu],
                "roles": ["qwen3_tts", "mmaudio_foley", "hunyuan_foley_48k", "ace_step_1_5", "clearervoice_mossformer2"],
            },
            {
                "name": "cinema_video_worker",
                "gpu": video_gpu,
                "hourly_usd": MODAL_GPU_HOURLY_USD[video_gpu],
                "comfyui_version": ">=0.28.0",
                "roles": ["wan22_distilled_fp8", "ltx25_a2v", "infinitetalk", "multitalk", "latentsync_1_6", "seedvr2_native"],
            },
        ],
    }


__all__ = [
    "DEFAULT_CHECKPOINT_RATIO",
    "DEFAULT_EPISODE_BUDGET_CAP_USD",
    "DEFAULT_VOLUME_NAME",
    "MIN_LATENTSYNC_SILENCE_PAD_S",
    "MODAL_GPU_HOURLY_USD",
    "EpisodeBudgetGuard",
    "SpendRecord",
    "build_comfy_latentsync16_graph",
    "build_comfy_seedvr2_graph",
    "build_comfy_wan22_distilled_graph",
    "estimate_modal_job_cost",
    "generate_modal_app_spec",
    "pad_audio_for_latentsync",
]
