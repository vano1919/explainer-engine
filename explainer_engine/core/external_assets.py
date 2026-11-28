"""External commercial-safe asset provenance registry & L2 verification gate."""
from __future__ import annotations

import hashlib
import json
import wave
from pathlib import Path
from typing import Any

DEFAULT_MANIFEST_PATH = Path("assets/external_manifest.json")
ALLOWED_LICENSES = frozenset({"CC0-1.0", "Public Domain", "MIT", "Apache-2.0", "BSD-3-Clause", "SIL-OFL-1.1", "Liberation-Font-License"})


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_external_manifest(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    repo_root: Path | None = None,
    allow_missing_large_optional: bool = False,
) -> dict[str, Any]:
    """L2 provenance verification gate: checks existence, non-empty, license, commercial_use, format, and SHA-256."""
    root = Path(repo_root) if repo_root else Path.cwd()
    mp = manifest_path if manifest_path.is_absolute() else root / manifest_path
    if not mp.is_file():
        return {"status": "FAIL", "findings": [f"Manifest not found: {mp}"], "checked": 0}

    data = json.loads(mp.read_text(encoding="utf-8"))
    assets = data.get("assets") or []
    findings: list[str] = []
    checked = 0

    for entry in assets:
        fp = entry.get("file_path", "")
        abs_p = (root / fp) if fp else Path()
        if not fp:
            findings.append("Asset entry missing file_path")
            continue
        if entry.get("commercial_use") is not True:
            findings.append(f"{fp}: commercial_use must be true")
        lic = str(entry.get("license", ""))
        if lic not in ALLOWED_LICENSES:
            findings.append(f"{fp}: disallowed or unknown license {lic!r}")
        src_url = str(entry.get("source_url", ""))
        if not src_url.startswith(("http://", "https://", "local-deterministic:")):
            findings.append(f"{fp}: invalid source_url {src_url!r}")
        if not entry.get("integrated_module"):
            findings.append(f"{fp}: missing integrated_module")

        if not abs_p.is_file():
            if allow_missing_large_optional and entry.get("gitignored_large_binary"):
                continue
            findings.append(f"{fp}: missing on disk")
            continue

        size = abs_p.stat().st_size
        if size <= 0:
            findings.append(f"{fp}: empty file (0 bytes)")
            continue

        actual_sha = sha256_file(abs_p)
        expected_sha = str(entry.get("sha256", ""))
        if expected_sha and actual_sha != expected_sha:
            findings.append(f"{fp}: sha256 mismatch (expected {expected_sha[:12]}, got {actual_sha[:12]})")

        if abs_p.suffix.lower() == ".wav":
            try:
                with wave.open(str(abs_p), "rb") as wf:
                    if wf.getframerate() != 48000 or wf.getnchannels() != 2 or wf.getsampwidth() != 2:
                        findings.append(
                            f"{fp}: invalid WAV format ({wf.getframerate()}Hz, {wf.getnchannels()}ch, {wf.getsampwidth()*8}bit)"
                        )
            except wave.Error as exc:
                findings.append(f"{fp}: corrupt WAV ({exc})")
        checked += 1

    return {
        "status": "PASS" if not findings else "FAIL",
        "manifest": str(mp),
        "total_entries": len(assets),
        "checked": checked,
        "findings": findings,
    }


if __name__ == "__main__":
    res = verify_external_manifest()
    print(json.dumps(res, indent=2))
    raise SystemExit(0 if res["status"] == "PASS" else 1)
