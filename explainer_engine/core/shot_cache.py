# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0): Synchronous Master Mold v2.1.0 Alignment for `explainer_engine/core/shot_cache.py`
# Target Module : explainer_engine/core/shot_cache.py
# Target Classes/Symbols : def _round(), def canonical(), def key(), class ShotCache (methods: __init__, _dir, get, put)
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    Synchronize this core module with `production_script/4` (`schema_version.py`, `mold_contract.py`), the 4-tier visual router (`tier_router.py`), the 6-stage `D-81` voice chain (`voice_chain.py`), and the 24 fps rational-time `bounded_timeline.py` solver so all CLI commands, config loaders, and package exports operate seamlessly across `/1`, `/2`, `/3`, and `/4` scripts.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    Currently this core module defaults to v2/v3 assumptions and does not expose or wire the new Master Mold v2.1.0 subsystems.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Ensures end-to-end synchronous behavior from CLI invocation through script validation, audio synthesis, 4-tier rendering, OTIO export, and final QA verification.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] JSON Schema Draft 2020-12 Official Specification
#        URL: https://json-schema.org/draft/2020-12
#        Rationale: Defines canonical $schema URI resolution, discriminator dispatch, additionalProperties: false enforcement, and backwards-compatible schema evolution across versioned contracts.
#    [2] JSON Schema Core Validation Spec (2020-12)
#        URL: https://json-schema.org/draft/2020-12/json-schema-core
#        Rationale: Establishes structural validation guarantees so versioned payloads (/1, /2, /3, /4) cannot silently fall back to incompatible schema validators.
#    [3] Python jsonschema Library Documentation
#        URL: https://python-jsonschema.readthedocs.io/en/stable/
#        Rationale: Reference implementation used by explainer_engine for Draft202012Validator dispatch and strict contract validation.
#    [4] Anthropic Claude Code Costs & Prompt Caching
#        URL: https://code.claude.com/docs/en/costs
#        Rationale: Demonstrates why deterministic offline schema/contract validation (BATCH-M0/M2) must precede paid LLM/API calls to avoid wasted token and GPU spend.
#    [5] OpenTimelineIO File Format Specification
#        URL: https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html
#        Rationale: Defines timeline metadata and rational-time contract serialization that downstream edit/render stages consume from production_script/4.
# =============================================================================

"""The shot cache (docs/CONTRACTS.md, CN-07): a rendered shot is stored under the SHA-256 of everything its render depends on,
so a shot is paid for once. Editing shot 05 of a 60-shot episode changes only shot 05's key; the other 59 resolve from disk.

    key = sha256(canonical JSON of the shot_spec/1 without file paths)

``params`` is hashed whole, so it holds the renderer's numbers and names and no file paths (a path there is a new key on
every machine). The key covers the prompt, negative, seed, model hash or revision, LoRA hashes and weights, size, frames, fps, the audio slice
hash, every reference's role and hash, the blocking hash, the recipe version and the renderer's params. A moved file keeps its
key (references are named by hash, not path); one changed byte in any of them is a new key. A hit also needs every stored
output to still match its recorded sha256. stdlib only (the contract check uses jsonschema).
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import shot_cache_root, write_json_atomic

logger = logging.getLogger(__name__)
NOT_IN_KEY = ("job_id", "shot_id")


def _round(obj):
    """Numbers as the cache sees them: floats rounded to 6 places, and a whole float is the integer (1.0 and 1 are one key)."""
    if isinstance(obj, bool):
        return obj
    if isinstance(obj, float):
        if obj != obj or obj in (float("inf"), float("-inf")):
            raise ValueError("a non-finite number (inf or NaN) has no JSON form")
        obj = round(obj, 6)
        return int(obj) if obj == int(obj) else obj
    if isinstance(obj, dict):
        return {k: _round(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_round(v) for v in obj]
    return obj


def canonical(spec: dict) -> bytes:
    """The spec as the cache sees it: validated, without who asked and where files lie, lists in a fixed order, floats rounded."""
    contracts.validate(spec)
    doc = {k: v for k, v in spec.items() if k not in NOT_IN_KEY}
    doc["refs"] = sorted(({"role": r["role"], "sha256": r["sha256"]} for r in spec["refs"]), key=lambda r: (r["role"], r["sha256"]))
    doc["loras"] = sorted(spec["loras"], key=lambda r: r["id"])
    try:
        return json.dumps(_round(doc), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    except ValueError as exc:  # inf / NaN has no JSON form, so no stable key
        raise ContractError(f"shot spec {spec.get('shot_id')!r} holds a non-finite number: {exc}") from exc


def key(spec: dict) -> str:
    return hashlib.sha256(canonical(spec)).hexdigest()


# TODO [CLAUDE-CLASS-SYNC: ShotCache] (BATCH-M0..M7 (Core Package & Configuration Synchronization with Master Mold v2.1.0)): Synchronize class `ShotCache` (methods: __init__, _dir, get, put) with the module-top TODO specification (sections 1-4: exact change, current flaw, superiority rationale, and >=5 verified web sources).
class ShotCache:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root) if root else shot_cache_root()

    def _dir(self, k: str) -> Path:
        return self.root / k[:2] / k

    def get(self, spec: dict) -> dict | None:
        """The stored entry (``outputs``: name -> {path, sha256}) or None; a damaged entry is a miss, never a wrong picture."""
        k = key(spec)
        entry_path = self._dir(k) / "entry.json"
        if not entry_path.exists():
            return None
        entry = json.loads(entry_path.read_text(encoding="utf-8"))
        for name, row in entry["outputs"].items():
            path = self._dir(k) / row["path"]
            if not path.exists() or contracts.sha256_file(path) != row["sha256"]:
                logger.warning("shot cache %s: output %s is damaged; treated as a miss", k[:12], name)
                return None
        return {**entry, "dir": str(self._dir(k))}

    def put(self, spec: dict, files: dict[str, Path | str], *, job_id: str) -> dict:
        k = key(spec)
        d = self._dir(k)
        d.mkdir(parents=True, exist_ok=True)
        outputs = {}
        for name, src in files.items():
            src = Path(src)
            dst = d / f"{name}{src.suffix}"
            shutil.copyfile(src, dst)
            outputs[name] = {"path": dst.name, "sha256": contracts.sha256_file(dst)}
        entry = {"key": k, "shot_id": spec["shot_id"], "job_id": job_id, "outputs": outputs}
        write_json_atomic(d / "entry.json", entry)
        return {**entry, "dir": str(d)}
