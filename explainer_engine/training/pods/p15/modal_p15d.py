"""p15d pilot on Modal (PLAN CODE, never run without the creator's recorded yes): 24 Qwen look variants + 16 J5 mouth variants and
ONE LTX-2.5 battle clip (121 f), photos and video as two concurrent Modal functions. The same stages as p15c1.sh (``p15_qwen`` and
``p15_ltx``, bundle sha pinned), on weights read from the Volume ``ee-weights`` (``modal_load_weights.py``).

Run (creator's PC, after the weight load is verified, the OR-23 card is answered "yes" and ``EE_MODAL_GO`` is set to his yes):
    EE_MODAL_GO=<the card id> modal run explainer_engine/training/pods/p15/modal_p15d.py

Design (docs/providers/ and OR23_P15D_ON_MODAL_PLAN_2026-11-07.md, the schedule pick of ``cloud/modal_schedule.py``):
  * ``qwen_pictures``: H100, timeout 40 min. Draws the battle frame (S2) FIRST (a runtime re-order of ``p15_qwen.jobs``, the bundle is
    untouched), puts a signal into a ``modal.Dict`` and uploads every output to HF as it appears (OR-33).
  * ``ltx_clip``: A100-80GB, timeout 30 min. Starts with the weight check (sha256 of the pinned files), waits for the signal, fetches the
    first frame from HF, makes the 121-frame clip.
  * Caps (hard brakes, no automatic Modal retries): H100 40 min = $2.63, A100 30 min = $1.25, CPU/RAM of both ~$0.4 -> $4.3 worst, cap $4.5;
    stop at 80 % = $3.6 is the executor's job (the dashboard line); nothing is left running (functions end, no pod).
Speeds are ESTIMATES (nothing measured on Modal). Weights stay on the Volume, the image holds only code and libraries.
"""
from __future__ import annotations

import json
import os
import sys
import threading
import time
from pathlib import Path

try:
    import modal
except ImportError:      # the tests and a plain import need no Modal SDK
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
HF_PREFIX = "route_test_2026-11/pilot"
BUNDLE_SHA = "53eb909ef3a0c37a332dbb582bc62bdd194733eeba867eb7f5467a84679d0681"
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
FIRST = "battle_f000_colour__S2"
LTX_JOB = "pilot.c4.battle_f000_colour.S2.ltx25.i2v.f121.s42"
CAPS = {"max_usd": 4.5, "stop_usd": 3.6, "max_hours": 2.7, "qwen_timeout_s": 40 * 60, "ltx_timeout_s": 30 * 60}
VOL_NAME = "ee-weights"
# (repo, type, pinned revision or None for 'main', is a cache entry to link)
HF_LINKS = [("Qwen/Qwen-Image-2.1", "model", "d26bb61231c349cf6b7896fa83353113880e1ba3"),
            ("Lightricks/LTX-2.5", "model", "49b093a39c19169a8a81721dcc541e07e945232f"),
            ("vano1919/tmr-artifacts", "dataset", None)]


def go_gate(env=os.environ) -> str:
    """Nothing starts on Modal without the creator's recorded yes: the card id of his answer in EE_MODAL_GO."""
    v = env.get("EE_MODAL_GO", "")
    if not v.startswith("cmsg_"):
        raise SystemExit("EE_MODAL_GO must be the card id of the creator's yes (OR-23); nothing was started")
    return v


def link_hf_cache(vol_root: Path, hf_home: Path, links=HF_LINKS) -> list[str]:
    """Build the Hugging Face cache layout out of the Volume's plain folders (``<vol>/<type>/<repo>/...``, ``modal_load_weights.py``) with
    symlinks, so the pinned ``snapshot_download``/``hf_hub_download`` calls of the stages find the files without a download.
    ``refs/main`` names the snapshot; a repo whose revision is unpinned uses the name ``local``."""
    made = []
    for repo, rtype, rev in links:
        src = Path(vol_root) / rtype / repo
        if not src.is_dir():
            continue
        folder = f"{rtype}s--" + repo.replace("/", "--")
        base = Path(hf_home) / "hub" / folder
        snap = base / "snapshots" / (rev or "local")
        (base / "refs").mkdir(parents=True, exist_ok=True)
        (base / "refs" / "main").write_text(rev or "local")
        for f in src.rglob("*"):
            if f.is_file() and ".cache" not in f.relative_to(src).parts:
                dst = snap / f.relative_to(src)
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.exists():
                    dst.symlink_to(f)
                    made.append(str(dst))
    return made


def reorder_first(jobs, first=FIRST):
    """the battle frame (the LTX clip's first frame) goes first so the video function can start while the other pictures are drawn."""
    return sorted(jobs, key=lambda j: j["name"] != first)


def new_files(out: Path, seen: dict) -> list[Path]:
    """files under ``out`` that are new or changed since the last call (the upload loop, OR-33)."""
    fresh = []
    for p in sorted(Path(out).rglob("*")):
        if p.is_file():
            st = (p.stat().st_size, int(p.stat().st_mtime))
            if seen.get(str(p)) != st:
                seen[str(p)] = st
                fresh.append(p)
    return fresh


def _uploader(out: Path, stop: threading.Event, every: float = 30.0):
    from huggingface_hub import HfApi
    api, seen = HfApi(token=os.environ["HF_TOKEN"]), {}
    while True:
        done = stop.is_set()
        for p in new_files(out, seen):
            if p.stat().st_size < 3_000_000_000:
                try:
                    api.upload_file(path_or_fileobj=str(p), path_in_repo=f"{HF_PREFIX}/{p.relative_to(out)}", repo_id=HF_REPO,
                                    repo_type="dataset")
                except Exception as e:   # noqa: BLE001 - the next pass retries; a final failure is in the beat
                    print("upload failed", p.name, repr(e)[:120], flush=True)
                    seen.pop(str(p), None)
        if done:
            return
        stop.wait(every)


def _prepare(out: Path) -> dict:
    """the pod's environment on Modal: weights linked from the Volume, the pinned code bundle, the Pod's env vars."""
    import subprocess
    import tarfile
    from huggingface_hub import hf_hub_download
    hf_home = Path("/tmp/hf")
    n = link_hf_cache(Path("/w"), hf_home)
    print("linked", len(n), "weight files from the Volume", flush=True)
    p = hf_hub_download(HF_REPO, "code/p15/ee_src.tar.gz", repo_type="dataset", local_dir="/tmp/job", token=os.environ["HF_TOKEN"])
    sha = subprocess.run(["sha256sum", p], capture_output=True, text=True).stdout.split()[0]
    if sha != BUNDLE_SHA:
        raise SystemExit(f"bundle sha mismatch {sha}")
    Path("/workspace/ee").mkdir(parents=True, exist_ok=True)
    with tarfile.open(p) as t:
        t.extractall("/workspace/ee")
    cfg = json.loads(Path("/workspace/ee/explainer_engine/training/pods/p15/p15.json").read_text())
    out.mkdir(parents=True, exist_ok=True)
    return dict(os.environ, HF_HOME=str(hf_home), EE_OUT=str(out), PYTHONUNBUFFERED="1", XW_GPU_MODE=cfg["qwen"]["gpu_mode"],
                EE_DEADLINE=str(time.time() + CAPS["max_hours"] * 3600),
                P14_LOCAL_ROOTS=json.dumps([[cfg["hf_root"], str(out)]]), PYTHONPATH="/workspace/ee")


def _run(cmd, env, log):
    import subprocess
    with open(log, "a") as f:
        return subprocess.run(cmd, env=env, cwd="/workspace/ee", stdout=f, stderr=subprocess.STDOUT).returncode


def _finish(out: Path, name: str, rc: int, started: float):
    (out / f"beat_{name}.txt").write_text(f"{'DONE' if rc == 0 else 'FAILED'} rc={rc} seconds={int(time.time() - started)}\n")


QWEN_RUNNER = ("import sys; sys.path.insert(0, '/workspace/ee'); import runpy; "
               "import explainer_engine.training.pods.p15.p15_qwen as Q; import explainer_engine.training.pods.p15.modal_p15d as M; "
               "o = Q.jobs; Q.jobs = lambda cfg, variants=False: M.reorder_first(o(cfg, variants)); "
               "sys.exit(Q.main(['--out', sys.argv[1], '--variants', '--mouth']))")


def qwen_body(signal):
    t0, out = time.time(), Path("/workspace/out")
    env = _prepare(out)
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(out, stop), daemon=True)
    th.start()

    def watch():   # tell the video function when the first frame exists
        ff = out / "first_frames" / f"{FIRST}.png"
        while not stop.is_set():
            if ff.is_file() and ff.stat().st_size > 10_000:
                time.sleep(3)
                signal["first_frame"] = time.time()
                return
            time.sleep(5)
    threading.Thread(target=watch, daemon=True).start()
    rc = _run(["python3", "-c", QWEN_RUNNER, str(out)], env, out / "qwen_modal.log")
    stop.set()
    th.join(timeout=300)
    _finish(out, "qwen", rc, t0)
    return {"rc": rc, "seconds": int(time.time() - t0)}


def ltx_body(signal):
    from huggingface_hub import hf_hub_download
    t0, out = time.time(), Path("/workspace/out")
    env = _prepare(out)
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(out, stop), daemon=True)
    th.start()
    rc = _run(["python3", "-m", "explainer_engine.training.pods.p15.p15_ltx", "--prefetch"], env, out / "ltx_modal.log")  # sha256 check of the weights
    if rc == 0:
        deadline = time.time() + CAPS["ltx_timeout_s"] - 600
        while "first_frame" not in signal and time.time() < deadline:
            time.sleep(5)
        if "first_frame" in signal:
            p = hf_hub_download(HF_REPO, f"{HF_PREFIX}/first_frames/{FIRST}.png", repo_type="dataset", token=os.environ["HF_TOKEN"])
            (out / "first_frames").mkdir(parents=True, exist_ok=True)
            (out / "first_frames" / f"{FIRST}.png").write_bytes(Path(p).read_bytes())
            rc = _run(["python3", "-m", "explainer_engine.training.pods.p15.p15_ltx", "--job", LTX_JOB, "--variant-frames"], env,
                      out / "ltx_clip_modal.log")
        else:
            rc = 2
    stop.set()
    th.join(timeout=300)
    _finish(out, "ltx", rc, t0)
    return {"rc": rc, "seconds": int(time.time() - t0)}


if modal is not None:
    app = modal.App("ee-p15d")
    vol = modal.Volume.from_name(VOL_NAME, version=2)
    image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12")
             .apt_install("ffmpeg", "git")
             .run_commands(
                 'pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" '
                 '"git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" '
                 '"git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e"',
                 "git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && "
                 "git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead",
                 "pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout 'imageio[ffmpeg]' "
                 "opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations kornia",
                 "git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && "
                 "git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && "
                 "pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines"))
    secrets = [modal.Secret.from_name("hf-token")]
    signal = modal.Dict.from_name("ee-p15d-signal", create_if_missing=True)

    @app.function(image=image, gpu="H100", cpu=2, memory=49152, timeout=CAPS["qwen_timeout_s"], retries=0,
                  volumes={"/w": vol}, secrets=secrets)
    def qwen_pictures():
        return qwen_body(signal)

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=CAPS["ltx_timeout_s"], retries=0,
                  volumes={"/w": vol}, secrets=secrets)
    def ltx_clip():
        return ltx_body(signal)

    @app.local_entrypoint()
    def main():
        go = go_gate()
        signal.clear()
        print("GO card", go, "caps", CAPS, flush=True)
        a, b = qwen_pictures.spawn(), ltx_clip.spawn()   # concurrent
        print("qwen", a.get(), "ltx", b.get())
