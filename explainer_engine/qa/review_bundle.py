"""The review bundle's manifest (REVIEW_APPROVED, approval #2, invariant 4; N-03 option A, ვანო 2026-10-30).

The creator approves the bundle he watched; ``bundle_manifest.json`` inside it lists every file with its sha256, and the
lifecycle gate binds the sha256 of that manifest file (``core/store.bound_sha256``). A file changed, added or removed after the
approval is refused (``check``). stdlib only.

    python -m explainer_engine.qa.review_bundle write <bundle folder>     # writes <bundle>/bundle_manifest.json, prints its sha256
    python -m explainer_engine.qa.review_bundle check <bundle folder>     # exit 1 when the bundle no longer matches its manifest
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

MANIFEST = "bundle_manifest.json"
SCHEMA = "review_bundle_manifest/1"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def listing(folder: Path | str) -> list[dict]:
    """Every file of the bundle but the manifest: relative path (``/``) and sha256, sorted by path."""
    folder = Path(folder)
    return [{"path": f.relative_to(folder).as_posix(), "sha256": _sha256(f)}
            for f in sorted(folder.rglob("*")) if f.is_file() and f.relative_to(folder).as_posix() != MANIFEST]


def write(folder: Path | str) -> Path:
    """Write ``<folder>/bundle_manifest.json`` and return its path; its sha256 is what the creator's approval carries."""
    from explainer_engine.core.store import write_json_atomic
    folder = Path(folder)
    if not folder.is_dir():
        raise ValueError(f"{folder} is not a bundle folder")
    path = folder / MANIFEST
    write_json_atomic(path, {"schema": SCHEMA, "files": listing(folder)})
    return path


def check(manifest: Path | str) -> list[str]:
    """What no longer matches the manifest (empty = the bundle is the one listed): changed, missing and unlisted files."""
    manifest = Path(manifest)
    doc = json.loads(manifest.read_text(encoding="utf-8"))
    if doc.get("schema") != SCHEMA:
        return [f"{manifest.name} is not a {SCHEMA}"]
    listed = {r["path"]: r["sha256"] for r in doc.get("files", [])}
    now = {r["path"]: r["sha256"] for r in listing(manifest.parent)}
    out = [f"changed: {p}" for p in sorted(listed) if p in now and now[p] != listed[p]]
    out += [f"missing: {p}" for p in sorted(set(listed) - set(now))]
    out += [f"not listed: {p}" for p in sorted(set(now) - set(listed))]
    return out


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in ("write", "check"):
        print(__doc__)
        return 2
    if argv[0] == "write":
        path = write(argv[1])
        print(f"{path}  sha256 {_sha256(path)}")
        return 0
    problems = check(Path(argv[1]) / MANIFEST)
    for p in problems:
        print(p)
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
