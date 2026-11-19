"""Typed calls of the vendored kajisho5 ffmpeg-skill (``.claude/skills/v-ffmpeg-skill``, final plan S14, W7).

The skill's scripts take typed flags, never a free ffmpeg string, and print a JSON result with the numbers (``--json``). This module
is the one place the episode path calls them: join clips without re-encoding, put the mix under a picture, measure a file (``check``)
and look at it (``look``). A failed call raises ``ContractError`` with the skill's own message; a missing ffmpeg or skill folder is
``NOT_RUN`` for the callers that measure (``available``). The skill's scripts import their sibling modules, so they run from their own
folder as scripts (no ``-I``), the way the skill documents it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from explainer_engine.core.errors import ContractError

SKILL_DIR = Path(__file__).resolve().parents[2] / ".claude" / "skills" / "v-ffmpeg-skill" / "scripts"


def available() -> bool:
    """ffmpeg, ffprobe and the vendored scripts are all present."""
    return shutil.which("ffmpeg") is not None and shutil.which("ffprobe") is not None and (SKILL_DIR / "check.py").exists()


def run(tool: str, args: list[str], *, ok_exit: tuple[int, ...] = (0,), timeout: int = 3600) -> dict:
    """One skill script with ``--json``; returns its parsed result. ``ok_exit`` lists exit codes whose JSON is still wanted
    (``check`` exits 1 when a row fails and prints the table all the same)."""
    script = SKILL_DIR / f"{tool}.py"
    if not script.exists():
        raise ContractError(f"ffmpeg-skill has no tool {tool!r} at {script}")
    proc = subprocess.run([sys.executable, str(script), *[str(a) for a in args], "--json"], capture_output=True, text=True,
                          timeout=timeout, env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"})   # vendored folders stay byte-identical
    doc = None
    for text in (proc.stdout, proc.stdout[proc.stdout.find("{"):] if "{" in proc.stdout else ""):
        try:
            doc = json.loads(text)
            break
        except ValueError:
            continue
    if doc is None or (proc.returncode not in ok_exit and doc.get("status") == "failed"):
        msg = (doc or {}).get("error", {}).get("message") or proc.stderr.strip() or proc.stdout.strip()[:300]
        raise ContractError(f"ffmpeg-skill {tool} failed: {msg}")
    return doc


def join_copy(clips: list[Path], out: Path) -> dict:
    """The clips one after the other, stream copy (no re-encode, no transition): the chunk join of RULE-R1."""
    return run("join", [*clips, "--transition", "none", "--copy", "-o", out, "--overwrite"])


def replace_audio(video: Path, audio: Path, out: Path, *, sample_rate: int, channels: int, kbps: int) -> dict:
    """The mix under a finished picture (picture stream-copied, audio padded or trimmed to the picture's length)."""
    flag = "--stereo" if channels == 2 else "--mono"
    return run("audio", [video, "--replace", audio, "--sample-rate", sample_rate, flag, "--bitrate", f"{kbps}k", "-o", out,
                         "--overwrite"])


def join_with_audio(clips: list[Path], audio: Path, out: Path, *, sample_rate: int, channels: int, kbps: int) -> dict:
    """Chunks joined by copy, then the mix put under them; ``out`` appears only after both steps (an atomic replace by the caller)."""
    tmp = out.with_name(out.stem + ".joined.mp4")
    try:
        if len(clips) == 1:   # the skill's join takes two or more; one chunk needs no join
            j, tmp = {"summary": None}, Path(clips[0])
        else:
            j = join_copy(clips, tmp)
        a = replace_audio(tmp, audio, out, sample_rate=sample_rate, channels=channels, kbps=kbps)
    finally:
        if len(clips) > 1:
            tmp.unlink(missing_ok=True)
    return {"join": j.get("summary"), "audio": a.get("summary")}


def check(path: Path, *, platform: str = "youtube", content: bool = True) -> dict:
    """``check.py``: the platform's spec rows (and black / frozen / silent / dropout rows with ``content``): a list of
    ``{check, status, value, expected}`` under ``checks``."""
    return run("check", [path, "--platform", platform, *(["--content"] if content else [])], ok_exit=(0, 1))


def look(path: Path, out_png: Path, *, tiles: str = "4x3") -> dict:
    """``look.py``: a contact sheet PNG with timecodes, for the agent's (or the creator's) eyes."""
    return run("look", [path, "--tiles", tiles, "-o", out_png, "--overwrite"])


def probe(path: Path) -> dict:
    return run("probe", [path])
