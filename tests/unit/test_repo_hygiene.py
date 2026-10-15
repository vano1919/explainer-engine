"""Repository guard rails that should not depend on anyone remembering them."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MEDIA = (".mp4", ".wav", ".mp3", ".flac", ".onnx", ".gguf", ".bin")
SECRET_NAMES = re.compile(r"(api_key|token[^/]*\.json$|secret|credentials|id_ed25519|\.pem$|^\.env$)", re.I)


def _tracked() -> list[str]:
    try:
        out = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True, check=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return []
    return [line for line in out.splitlines() if line]


def test_no_media_models_or_secret_files_are_tracked():
    tracked = _tracked()
    assert not [f for f in tracked if f.lower().endswith(MEDIA)]
    assert not [f for f in tracked if SECRET_NAMES.search(Path(f).name) and not f.startswith("tests/")]


def test_no_runtime_import_of_the_sleep_engine():
    imports = re.compile(r"^\s*(from|import)\s+tmr_engine\b|import_module\(\s*['\"]tmr_engine", re.M)
    offenders = [p for p in (ROOT / "explainer_engine").rglob("*.py") if imports.search(p.read_text(encoding="utf-8"))]
    assert not offenders, "copy what you need (with provenance); never import tmr_engine"


def test_every_copied_file_is_listed_in_provenance():
    provenance = (ROOT / "docs" / "PROVENANCE.md").read_text(encoding="utf-8")
    for path in (ROOT / "explainer_engine").rglob("*.py"):
        if "# from vano1919/tmr-video-script-engine@" in path.read_text(encoding="utf-8"):
            assert path.relative_to(ROOT).as_posix() in provenance, path
