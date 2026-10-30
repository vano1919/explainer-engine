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


def test_the_chatgpt_copy_of_claude_is_gone_and_the_ci_does_not_trigger_on_it():
    """P0a / D2 (2026-10-29): no second instruction tree; `.claude/` is the only one."""
    assert not (ROOT / ".chatgpt").exists()
    assert not [f for f in _tracked() if f.startswith(".chatgpt/")]
    assert "chatgpt/**" not in (ROOT / ".github" / "workflows" / "quality.yml").read_text(encoding="utf-8")


def test_visemes_stays_importable_and_retired_deps_are_not_required():
    """audio/visemes.py is a TMR port the hosts world (P5b) uses; kokoro-onnx is no install requirement (D-39)."""
    import importlib

    assert importlib.import_module("explainer_engine.audio.visemes")
    reqs = (ROOT / "requirements.txt").read_text(encoding="utf-8")
    assert not [line for line in reqs.splitlines() if line.strip().lower().startswith(("kokoro-onnx", "remotion"))]


def test_kokoro_modules_carry_the_d39_banner_and_narrate_cli_refuses():
    import sys

    for m in ("narrate", "timings", "visemes"):
        head = (ROOT / f"explainer_engine/audio/{m}.py").read_text(encoding="utf-8")[:400]
        assert "RETIRED by D-39" in head, m
    r = subprocess.run([sys.executable, "-m", "explainer_engine.audio.narrate"], capture_output=True, text=True, cwd=ROOT,
                       timeout=60)
    assert r.returncode != 0 and "RETIRED by D-39" in (r.stdout + r.stderr)
    rules = (ROOT / "docs/PRODUCTION_RULES.md").read_text(encoding="utf-8")
    assert "Kokoro only for drafts" not in rules
    assert "Pro plan" not in rules
    assert "voice (Clyde)" not in rules
    assert re.search(r"\| \*\*keyframes\*\* \|", rules) and re.search(r"\| \*\*clips\*\* \|", rules)
    assert "docs/KEYFRAME_GATE.md" in rules and "video_qa" in rules
