"""Provider-neutral cloud GPU abstractions, lifecycle states, and approval guards (OR-22..36).

Reuses ``explainer_engine.cloud.jobs.Job`` and ``explainer_engine.cloud.store`` without duplicating
state machines or modifying ``config/spend_caps.json`` or ``explainer_engine/cloud/runpod.py``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from pathlib import Path
import re
import time
from typing import Any

from explainer_engine.cloud import jobs, store

NORMALIZED_STATES = (
    "PENDING",
    "PROVISIONING",
    "STARTING",
    "RUNNING",
    "STOPPING",
    "COMPLETED",
    "FAILED",
    "CANCELLED",
    "UNKNOWN",
)

# Map normalized provider state onto explainer_engine/cloud/jobs.py STATES
TO_GUARDIAN_STATE = {
    "PENDING": "QUEUED",
    "PROVISIONING": "PROVISIONING",
    "STARTING": "STARTING",
    "RUNNING": "RUNNING",
    "STOPPING": "STOPPING",
    "COMPLETED": "SUCCEEDED",
    "FAILED": "FAILED",
    "CANCELLED": "STOPPED",
    "UNKNOWN": "STALLED",
}

# Proposed caps for new providers: disabled by default (OR-22: never copy RunPod caps or spend without approval).
# The numbers live in config/provider_caps_proposed.json (not approved); a module never writes a cap as a number (D-56).
_PROPOSED_CAPS_FILE = Path(__file__).resolve().parents[3] / "config" / "provider_caps_proposed.json"


def _load_proposed_caps() -> dict[str, dict[str, Any]]:
    raw = json.loads(_PROPOSED_CAPS_FILE.read_text(encoding="utf-8"))
    caps = {k: dict(v) for k, v in raw.items() if not k.startswith("_")}
    for v in caps.values():
        v["allowed_regions"] = tuple(v.get("allowed_regions", ()))
    return caps


PROPOSED_PROVIDER_CAPS: dict[str, dict[str, Any]] = _load_proposed_caps()

_SECRET_PATTERNS = (
    re.compile(r"(api_key\s*[:=]\s*)(\S+)", re.I),
    re.compile(r"(Bearer\s+)([A-Za-z0-9._\-]{8,})", re.I),
    re.compile(r"(sk-[A-Za-z0-9._\-]{8,}|ak-[A-Za-z0-9._\-]{8,}|rpa_[A-Za-z0-9._\-]{8,})"),
)


def redact_secrets(text: str, extra_secrets: tuple[str, ...] = ()) -> str:
    """Redact API keys, tokens, and caller-provided secrets from error messages and logs."""
    out = str(text or "")
    for sec in extra_secrets:
        if sec and len(sec) >= 4:
            out = out.replace(sec, "[REDACTED]")
    out = _SECRET_PATTERNS[0].sub(r"\1[REDACTED]", out)
    out = _SECRET_PATTERNS[1].sub(r"\1[REDACTED]", out)
    out = _SECRET_PATTERNS[2].sub("[REDACTED]", out)
    return out


class ProviderError(RuntimeError):
    """Base error for provider operations (always secret-redacted)."""

    def __init__(self, message: str, *, status: int | None = None, secrets: tuple[str, ...] = ()) -> None:
        super().__init__(redact_secrets(message, secrets))
        self.status = status


class StaleStockError(ProviderError):
    """Raised when inventory data is older than max_age_s."""


class InsufficientVramError(ProviderError):
    """Raised when a GPU offer has less VRAM than the workload requires."""


class UnsupportedGpuError(ProviderError):
    """Raised when a GPU model is unknown or incompatible with the workload."""


class RegionMismatchError(ProviderError):
    """Raised when a GPU offer is outside the workload's or account's allowed regions."""


class PriceLookupError(ProviderError):
    """Raised when pricing cannot be resolved for a GPU/flavor."""


class BudgetExceededError(ProviderError):
    """Raised when estimated or actual job cost exceeds the provider or job ceiling."""


class ApprovalRequiredError(ProviderError):
    """Raised when live resource creation is attempted without OR-22/23/24/34 approval."""


class RateLimitError(ProviderError):
    """Raised on HTTP 429 rate limiting."""

    def __init__(self, message: str, *, retry_after_s: int = 30) -> None:
        super().__init__(message, status=429)
        self.retry_after_s = retry_after_s


class AuthenticationError(ProviderError):
    """Raised on HTTP 401/403 authentication failure without leaking credentials."""


class DuplicateRequestError(ProviderError):
    """Raised when an idempotency key or resource name already has an in-flight or active resource."""


class UnclearProvisionError(ProviderError):
    """Raised when a provision POST timed out or returned 5xx and must be reconciled before retrying."""


@dataclass(frozen=True)
class WorkloadSpec:
    """Hardware, storage, and timing specification for an Explainer Engine cloud workload."""

    workload_id: str
    kind: str  # "qwen_image", "ltx_video", "combined_p12_p14", "serverless_short"
    min_vram_gb: int
    min_ram_gb: int
    min_disk_gb: int
    ref_a100_work_minutes: float
    setup_minutes_cold: float
    setup_minutes_warm: float = 2.0
    egress_gb: float = 2.0
    allowed_regions: tuple[str, ...] = ()
    require_custom_lora: bool = True
    require_docker_or_custom_image: bool = True
    measure_only: bool = False
    max_budget_usd: float | None = None


WORKLOAD_PRESETS: dict[str, WorkloadSpec] = {
    "workload_a_qwen_16pics": WorkloadSpec(
        workload_id="workload_a_qwen_16pics",
        kind="qwen_image",
        min_vram_gb=48,
        min_ram_gb=48,
        min_disk_gb=80,
        ref_a100_work_minutes=18.0,
        setup_minutes_cold=15.0,
        setup_minutes_warm=1.5,
        egress_gb=0.5,
    ),
    "workload_b_ltx_30s": WorkloadSpec(
        workload_id="workload_b_ltx_30s",
        kind="ltx_video",
        min_vram_gb=80,
        min_ram_gb=64,
        min_disk_gb=180,
        ref_a100_work_minutes=46.4,
        setup_minutes_cold=30.0,
        setup_minutes_warm=2.0,
        egress_gb=1.5,
    ),
    "workload_c_combined_p12_p14": WorkloadSpec(
        workload_id="workload_c_combined_p12_p14",
        kind="combined_p12_p14",
        min_vram_gb=80,
        min_ram_gb=96,
        min_disk_gb=200,
        ref_a100_work_minutes=176.0,
        setup_minutes_cold=45.0,
        setup_minutes_warm=10.0,
        egress_gb=3.5,
    ),
    "workload_c_j5_minimised_p12_p14": WorkloadSpec(
        workload_id="workload_c_j5_minimised_p12_p14",
        kind="combined_p12_p14",
        min_vram_gb=80,
        min_ram_gb=96,
        min_disk_gb=200,
        ref_a100_work_minutes=57.0,
        setup_minutes_cold=18.0,
        setup_minutes_warm=3.0,
        egress_gb=1.8,
    ),
    "workload_d_short_calibration": WorkloadSpec(
        workload_id="workload_d_short_calibration",
        kind="serverless_short",
        min_vram_gb=80,
        min_ram_gb=64,
        min_disk_gb=180,
        ref_a100_work_minutes=7.6,
        setup_minutes_cold=18.0,
        setup_minutes_warm=0.5,
        egress_gb=0.3,
        measure_only=True,
    ),
}


@dataclass(frozen=True)
class GpuCapacityOffer:
    """A single normalized GPU capacity offer from a provider."""

    provider: str
    gpu_type: str
    flavor_name: str
    region: str
    vram_gb: int
    cpu_cores: int
    ram_gb: int
    root_disk_gb: int
    ephemeral_disk_gb: int
    gpu_count: int
    available: bool
    availability_tier: str  # "HIGH", "MEDIUM", "LOW", "NONE"
    fetched_at: float
    price_per_hour_usd: float | None = None
    supports_hibernation: bool = True
    reliability_score: float = 0.99

    @property
    def total_disk_gb(self) -> int:
        return int(self.root_disk_gb) + int(self.ephemeral_disk_gb)

    def is_stale(self, now: float | None = None, max_age_s: float = 120.0) -> bool:
        cur = time.time() if now is None else now
        return (cur - float(self.fetched_at)) > max_age_s


@dataclass(frozen=True)
class CostBreakdown:
    """Transparent total-cost breakdown for running a workload on a specific offer."""

    provider: str
    gpu_type: str
    flavor_name: str
    region: str
    work_minutes: float
    setup_minutes: float
    scaledown_minutes: float
    total_billable_hours: float
    gpu_Hourly_usd: float
    cpu_ram_hourly_usd: float
    active_disk_ip_hourly_usd: float
    compute_usd: float
    egress_usd: float
    idle_storage_per_day_usd: float
    expected_total_usd: float
    conservative_retry_total_usd: float
    net_after_credits_usd: float
    setup_share: float
    assumptions: tuple[str, ...] = ()


@dataclass(frozen=True)
class ApprovalGate:
    """Explicit OR-22/23/24/34 approval bundle required before any live resource creation."""

    or22_creator_word_ref: str = ""
    or23_plan_path: str = ""
    or24_opus_verdict_ref: str = ""
    or34_fable_audit_ref: str = ""
    provider_enabled: bool = False

    def validate(self, provider: str) -> None:
        missing = []
        if not self.provider_enabled:
            missing.append(f"provider '{provider}' live provisioning is disabled by default")
        if not self.or22_creator_word_ref.strip():
            missing.append("missing OR-22 creator confirmation reference")
        if not self.or23_plan_path.strip():
            missing.append("missing OR-23 item-by-item plan path")
        if not self.or24_opus_verdict_ref.strip():
            missing.append("missing OR-24 higher-model (Opus) confirmation reference")
        if not self.or34_fable_audit_ref.strip():
            missing.append("missing OR-34 Fable full-repository readiness audit reference")
        if missing:
            raise ApprovalRequiredError(
                f"Cannot create live resource on {provider}: " + "; ".join(missing)
            )


@dataclass
class JobStatusView:
    """Normalized view of a provider resource's current state and billing status."""

    provider: str
    resource_id: str
    name: str
    provider_state: str
    normalized_state: str
    billing_active: bool
    hourly_rate_usd: float = 0.0
    idle_disk_per_day_usd: float = 0.0
    billing_trap_warning: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def guardian_state(self) -> str:
        return TO_GUARDIAN_STATE.get(self.normalized_state, "STALLED")


def sync_job_from_view(job: jobs.Job, view: JobStatusView, *, now: float | None = None) -> str | None:
    """Update an ``explainer_engine.cloud.jobs.Job`` record from a provider-neutral ``JobStatusView``."""
    now = time.time() if now is None else now
    if not job.state.get("resource") and view.resource_id:
        job.attach(view.resource_id, now=now, provider_state=view.provider_state)

    target = view.guardian_state
    cur = job.state["state"]

    # If the resource failed/cancelled while unstored outputs exist on disk, require recovery (OR-33)
    if view.normalized_state in ("FAILED", "CANCELLED") and job.unstored_outputs():
        target = "RECOVERY_REQUIRED"

    reason = f"{view.provider} {view.resource_id} state={view.provider_state}"
    if view.billing_trap_warning:
        reason += f" [WARNING: {view.billing_trap_warning}]"

    if view.normalized_state == "RUNNING":
        job.heartbeat(stage=job.state.get("stage") or "running", note=reason, now=now, source=view.provider)

    if target == cur:
        return None
    if target in jobs.TRANSITIONS.get(cur, ()):
        job.move(target, reason, now=now)
        return target
    job.move(target, reason, now=now, force=True, forced_from=cur)
    return target


def verify_and_mark_stored(job: jobs.Job, local_dir: Path, repo_path: str, *, now: float | None = None) -> list[str]:
    """Verify every recorded output via ``cloud.store`` (size + sha256) before marking stored (OR-33)."""
    problems = store.check_folder(local_dir) if hasattr(store, "check_folder") else []
    for out in job.state.get("outputs", []):
        p = Path(out["path"])
        if not p.exists():
            problems.append(f"missing output file: {p}")
            continue
        actual_sha = hashlib.sha256(p.read_bytes()).hexdigest()
        if actual_sha != out["sha256"]:
            problems.append(f"sha256 mismatch for {p}: expected {out['sha256']}, got {actual_sha}")
    if problems:
        return problems
    job.mark_stored(repo_path, now=now)
    return []
