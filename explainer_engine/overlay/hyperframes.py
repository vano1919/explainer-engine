"""HyperFrames driver (v4.3 plan section 9.2, stage B5): overlay spec -> HTML project -> transparent video -> composite over a clip.

Free and local: Node 22 + headless Chrome + ffmpeg, no network at render time (GSAP and the font are vendored next to the template,
never a CDN). Telemetry of the CLI is switched off through its documented environment variables. The spec (``overlay/spec.py``) is the
only input; the render is a pure function of it.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

from explainer_engine.core.errors import ConfigError
from explainer_engine.core.store import write_text_atomic

HERE = Path(__file__).resolve().parent
TEMPLATE_DIR = HERE / "hyperframes"
HF_VERSION = "0.9.39"      # pinned (npm, Apache-2.0); package.json in the template folder is the one home of the pin
ENV = {"HYPERFRAMES_NO_TELEMETRY": "1", "DO_NOT_TRACK": "1"}


def write_project(spec: dict, out_dir: Path | str) -> Path:
    """The HyperFrames project folder of one overlay: index.html (template + spec inlined), vendored GSAP and font."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for sub in ("vendor", "fonts"):
        shutil.copytree(TEMPLATE_DIR / sub, out / sub, dirs_exist_ok=True)
    html = (TEMPLATE_DIR / "template.html").read_text(encoding="utf-8")
    dur = round(spec["frames"] / spec["fps"], 4)
    for key, val in (("__DURATION__", dur), ("__W__", spec["frame"]["w"]), ("__H__", spec["frame"]["h"]), ("__FPS__", spec["fps"])):
        html = html.replace(key, str(val))
    html = html.replace("__SPEC__", json.dumps(spec, separators=(",", ":")))
    write_text_atomic(out / "index.html", html)
    write_text_atomic(out / "spec.json", json.dumps(spec, indent=1))
    return out


def hf_binary() -> list[str]:
    """The CLI: an env override, a project-local install, or npx at the pinned version. Node 22+ is required."""
    exe = os.environ.get("EXPLAINER_HYPERFRAMES")
    if exe:
        return exe.split()
    if shutil.which("node") is None or shutil.which("npx") is None:
        raise ConfigError("HyperFrames needs Node 22+ (node and npx not found)")
    return ["npx", "--yes", f"hyperframes@{HF_VERSION}"]


def render_overlay(project: Path | str, out_file: Path | str, *, fmt: str = "webm", quality: str = "looks", workers: int | None = None,
                   timeout: int = 3600) -> subprocess.CompletedProcess:
    """Render the project to a transparent video (webm = VP9 alpha, mov = ProRes 4444, png-sequence = RGBA frames)."""
    cmd = hf_binary() + ["render", str(project), "--format", fmt, "-q", quality, "-o", str(out_file), "--quiet"]
    if workers:
        cmd += ["-w", str(workers)]
    env = {**os.environ, **ENV}
    return subprocess.run(cmd, capture_output=True, text=True, env=env, timeout=timeout, check=True)


def composite(clip: Path | str, plate_png: Path | str, overlay: Path | str, out_file: Path | str, spec: dict, *, crf: int = 16) -> subprocess.CompletedProcess:
    """clip (2K) + map plate inset fading in over the card's frames + the transparent overlay -> one MP4 (audio of the clip kept)."""
    c = spec["card"]
    fps = spec["fps"]
    dec = ["-c:v", "libvpx-vp9"] if str(overlay).endswith(".webm") else []   # the native vp9 decoder drops the alpha plane
    fg = (f"[1:v]format=rgba,fade=t=in:st=0:d={6 / fps:.4f}:alpha=1[p];"
          f"[0:v][p]overlay={c['x']}:{c['y']}:shortest=1[a];"
          f"[a][2:v]overlay=0:0:format=auto:shortest=1,format=yuv420p[o]")
    cmd = ["ffmpeg", "-v", "error", "-y", "-i", str(clip), "-loop", "1", "-framerate", str(fps), "-i", str(plate_png), *dec, "-i", str(overlay),
           "-filter_complex", fg, "-map", "[o]", "-map", "0:a?", "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-c:a", "copy",
           "-t", f"{spec['frames'] / fps:.4f}", str(out_file)]
    return subprocess.run(cmd, capture_output=True, text=True, check=True)
