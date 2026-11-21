"""Provider-neutral cloud GPU adapters and capacity selector (Hyperstack, Modal, RunPod)."""

from __future__ import annotations

from explainer_engine.cloud.providers.base import (
    ApprovalGate,
    ApprovalRequiredError,
    AuthenticationError,
    BudgetExceededError,
    CostBreakdown,
    DuplicateRequestError,
    GpuCapacityOffer,
    InsufficientVramError,
    JobStatusView,
    NORMALIZED_STATES,
    PROPOSED_PROVIDER_CAPS,
    PriceLookupError,
    ProviderError,
    RateLimitError,
    RegionMismatchError,
    StaleStockError,
    UnclearProvisionError,
    UnsupportedGpuError,
    WORKLOAD_PRESETS,
    WorkloadSpec,
    redact_secrets,
    sync_job_from_view,
    verify_and_mark_stored,
)
from explainer_engine.cloud.providers.hyperstack import HyperstackAdapter
from explainer_engine.cloud.providers.modal_provider import ModalAdapter
from explainer_engine.cloud.providers.runpod_adapter import RunPodProviderAdapter
from explainer_engine.cloud.providers.selector import ProviderSelector, RankedCandidate

__all__ = [
    "ApprovalGate",
    "ApprovalRequiredError",
    "AuthenticationError",
    "BudgetExceededError",
    "CostBreakdown",
    "DuplicateRequestError",
    "GpuCapacityOffer",
    "HyperstackAdapter",
    "InsufficientVramError",
    "JobStatusView",
    "ModalAdapter",
    "NORMALIZED_STATES",
    "PROPOSED_PROVIDER_CAPS",
    "PriceLookupError",
    "ProviderError",
    "ProviderSelector",
    "RankedCandidate",
    "RateLimitError",
    "RegionMismatchError",
    "RunPodProviderAdapter",
    "StaleStockError",
    "UnclearProvisionError",
    "UnsupportedGpuError",
    "WORKLOAD_PRESETS",
    "WorkloadSpec",
    "redact_secrets",
    "sync_job_from_view",
    "verify_and_mark_stored",
]
