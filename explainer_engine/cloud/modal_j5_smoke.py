"""One CPU smoke render of the J5 dialogue on Modal (PLAN CODE, not run without the creator's explicit pick on the card).

The creator, 2026-11-07 ("run it on Modal"; the Fable thread is asking him which step he means): a Modal CPU render of the J5 tent
dialogue, 3 shots x 3 frames at 1280x720, to see whether the render works there and what a frame costs. The renderer
(``explainer_engine/blender/j5_background.py``, branch claude/project-thread-4nebmi, commit 38cfff1, PR #151) is numpy / Pillow / OpenCV /
scipy / ffmpeg only: NO Blender and no GL are involved, so the earlier "EEVEE on software GL" question does not arise for this step.
Checked locally 2026-11-07: the same command takes 7 s on this machine's CPU.

Run (creator's PC, profile vanotimmy):  EE_MODAL_GO=<card id of his pick> modal run explainer_engine/cloud/modal_j5_smoke.py
Code and kit come from HF ``vano1919/tmr-artifacts`` ``code/j5/`` (sha256 pinned below), the secret is ``huggingface-secret``.
Caps: hard cap $0.15 for everything (image build included); one container of 2 physical cores (= 4 vCPU) and 8 GiB, timeout 20 min
= at most 1200 s x ($0.0000131 x 2 + $0.00000222 x 8) = $0.053; no GPU. Output PNGs and the timing record go to HF as they appear.
"""
from __future__ import annotations

import json
import os
import subprocess
import tarfile
import time
from pathlib import Path

try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
OUT_PREFIX = "route_test_2026-11/j5_smoke"
SECRET_NAME = "huggingface-secret"
PINS = {"code/j5/ee_src_j5.tar.gz": "857fdfd00419c6dee1977cf342689150430f4a8af0a27a3db18e0a66b3286f61",
        "code/j5/j5_kit.tar.gz": "7bcf01b4622012ac518f32415940e8fa2dd92c51b83a5f81f133f9c3dbf9bf3b"}
CODE_COMMIT = "38cfff1"
SHOTS = ("S1_two_shot", "S2_ots_h2_to_h1", "S3_ots_h1_to_h2")
CAPS = {"max_usd": 0.15, "timeout_s": 20 * 60, "cores": 2, "mem_gib": 8}
CPU_CORE_S, MEM_GIB_S = 0.0000131, 0.00000222     # modal.com/pricing, 2026-11-07
PIP = ["numpy", "pillow", "opencv-python-headless", "scipy", "jsonschema==4.26.0", "huggingface_hub==1.33.0"]


def go_gate(env=os.environ) -> str:
    v = env.get("EE_MODAL_GO", "")
    if not v.startswith("cmsg_"):
        raise SystemExit("EE_MODAL_GO must be the card id of the creator's pick (OR-23); nothing was started")
    return v


def _tok(env=os.environ) -> str:
    t = env.get("HF_TOKEN") or env.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit(f"Modal secret {SECRET_NAME} has neither HF_TOKEN nor HUGGING_FACE_HUB_TOKEN")
    return t


def render_cmd(root: Path, kit: Path, out: Path, *, seconds: float = 0.125, size: str = "1280x720") -> list[str]:
    """the README's one line (j5_dialogue_pc_kit): 3 shots x 3 frames."""
    return ["python3", "-m", "explainer_engine.blender.j5_background", "render", "--collage", str(kit / "collage"), "--inputs",
            str(kit / "in"), "--voice", str(kit / "voice"), "--out", str(out), "--seconds", str(seconds), "--size", size]


def frame_cmd(mp4: Path, png: Path, n: int = 2) -> list[str]:
    return ["ffmpeg", "-y", "-loglevel", "error", "-i", str(mp4), "-vf", f"select=eq(n\\,{n})", "-vframes", "1", str(png)]


def worst_usd(seconds: float = CAPS["timeout_s"]) -> float:
    return seconds * (CAPS["cores"] * CPU_CORE_S + CAPS["mem_gib"] * MEM_GIB_S)


def _sha(p) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def smoke_body() -> dict:
    from huggingface_hub import HfApi, hf_hub_download
    t0 = time.time()
    work = Path("/tmp/j5")
    work.mkdir(parents=True, exist_ok=True)
    api = HfApi(token=_tok())
    for name, sha in PINS.items():
        p = hf_hub_download(HF_REPO, name, repo_type="dataset", local_dir=str(work / "dl"), token=_tok())
        if _sha(p) != sha:
            raise SystemExit(f"{name}: sha256 mismatch")
        dest = work / ("src" if "ee_src" in name else "kit")
        dest.mkdir(exist_ok=True)
        with tarfile.open(p) as t:
            t.extractall(dest)
    out = work / "out"
    env = dict(os.environ, PYTHONPATH=str(work / "src"), PYTHONUNBUFFERED="1")
    t1 = time.time()
    r = subprocess.run(render_cmd(work / "src", work / "kit", out), env=env, cwd=work / "src", capture_output=True, text=True)
    render_s = time.time() - t1
    rec = {"rc": r.returncode, "render_s": round(render_s, 1), "frames": 9, "s_per_frame": round(render_s / 9, 2),
           "total_s": round(time.time() - t0, 1), "code_commit": CODE_COMMIT, "tail": (r.stdout + r.stderr)[-600:],
           "est_usd": round((time.time() - t0) * (CAPS["cores"] * CPU_CORE_S + CAPS["mem_gib"] * MEM_GIB_S), 4)}
    files = []
    if r.returncode == 0:
        for s in SHOTS:
            png = out / f"{s}.png"
            subprocess.run(frame_cmd(out / "segments" / f"{s}.mp4", png), check=True)
            files.append(png)
    (out / "timing.json").write_text(json.dumps(rec, indent=1))
    files.append(out / "timing.json")
    for f in files:
        api.upload_file(path_or_fileobj=str(f), path_in_repo=f"{OUT_PREFIX}/{f.name}", repo_id=HF_REPO, repo_type="dataset")
    return rec


if modal is not None:
    app = modal.App("ee-j5-smoke")
    image = (modal.Image.debian_slim(python_version="3.12").apt_install("ffmpeg").pip_install(*PIP))

    @app.function(image=image, cpu=CAPS["cores"], memory=CAPS["mem_gib"] * 1024, timeout=CAPS["timeout_s"], retries=0,
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def smoke():
        return smoke_body()

    @app.local_entrypoint()
    def main():
        print("GO card", go_gate(), "caps", CAPS, flush=True)
        print(smoke.remote())
