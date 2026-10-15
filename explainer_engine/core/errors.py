"""Deterministic error types. The pipeline fails loudly and specifically, and says which kind of failure it is:
retryable (transient), permanent (configuration/contract) or a human-review stop."""

# from vano1919/tmr-video-script-engine@d88ba8f:tmr_engine/errors.py
# changed: cue/schedule errors removed; RetryableError, NeedsReview added

from __future__ import annotations

from dataclasses import dataclass, field


class EngineError(Exception):
    """Base class for all engine failures."""


class ContractError(EngineError):
    """A document did not satisfy its versioned schema or a referential rule (permanent: fix the input)."""


class ConfigError(EngineError):
    """Invalid or missing configuration (permanent: fix the config before the job starts)."""


class RetryableError(EngineError):
    """A transient failure (network, a renderer crash) that may succeed on a bounded retry."""


class NeedsReview(EngineError):
    """A gate needs a human decision; the job stops with NEEDS_REVIEW after saving everything."""


class ValidationError(EngineError):
    """Deterministic validation failed; ``findings`` lists each failed check."""

    def __init__(self, findings: list[dict]) -> None:
        self.findings = findings
        super().__init__("; ".join(f"{f['check']}: {f['detail']}" for f in findings))


@dataclass
class PipelineFailure(EngineError):
    """A job stopped at a known stage, with a readable report."""

    stage: str
    message: str
    details: dict = field(default_factory=dict)

    def __str__(self) -> str:
        return f"[{self.stage}] {self.message}"
