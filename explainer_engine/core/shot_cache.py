"""The shot cache (docs/CONTRACTS.md, CN-07): a rendered shot is stored under the SHA-256 of everything its render depends on,
so a shot is paid for once. Editing shot 05 of a 60-shot episode changes only shot 05's key; the other 59 resolve from disk.

    key = sha256(canonical JSON of the shot_spec/1 without file paths)

The key covers the prompt, negative, seed, model hash or revision, LoRA hashes and weights, size, frames, fps, the audio slice
hash, every reference's role and hash, the blocking hash, the recipe version and the renderer's params. A moved file keeps its
key (references are named by hash, not path); one changed byte in any of them is a new key. A hit also needs every stored
output to still match its recorded sha256. stdlib only (the contract check uses jsonschema).
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
from pathlib import Path

from explainer_engine.core import contracts
from explainer_engine.core.store import write_json_atomic

logger = logging.getLogger(__name__)
ROOT = Path(__file__).resolve().parents[2]
NOT_IN_KEY = ("job_id", "shot_id")


def _round(obj):
    if isinstance(obj, float):
        return round(obj, 6)
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
    return json.dumps(_round(doc), sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def key(spec: dict) -> str:
    return hashlib.sha256(canonical(spec)).hexdigest()


class ShotCache:
    def __init__(self, root: Path | str | None = None) -> None:
        self.root = Path(root or os.environ.get("EXPLAINER_SHOT_CACHE") or ROOT / "jobs" / "_cache" / "shots")

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
