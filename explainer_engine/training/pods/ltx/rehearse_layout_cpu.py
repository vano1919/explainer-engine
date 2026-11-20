"""Free CPU rehearsal of the Layout-To-Render worker's ``body()`` (audit lesson feedback-rehearse-container-body): the REAL body, the REAL
wrapper ``ic_lora_run.py`` as a child process, the REAL ``layout_job`` (ffprobe, ffmpeg, PIL, hash checks, the sha-named tar) and the REAL
imageio writer on a ``.mp4``-suffixed temp name, with a FAKE ``ltx_pipelines.ic_lora`` (it parses the same arguments the real CLI takes and
writes a clip with the asked frame count) and a FAKE Hugging Face client. It proves the plumbing - the run key, the deadline, the save
after each clip, the hand-over frame, the read-back - and proves NOTHING about LTX, memory, seconds or sound on the A100.

    python -m explainer_engine.training.pods.ltx.rehearse_layout_cpu <work dir>

Used by ``tests/unit/test_layout_worker.py``; ``make_world`` is the one place that builds the fake files."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tarfile
import textwrap
from pathlib import Path
from types import SimpleNamespace

from explainer_engine.training.pods.ltx import layout_job as J
from explainer_engine.training.pods.ltx import modal_layout_jobs as M

# What the fake CLI does, by FAKE_MODE: ok (write a clip), sound (clip with a sine track), fail (exit 3), sleep (a clip that never ends).
FAKE_IC_LORA = textwrap.dedent('''\
    """Fake ltx_pipelines.ic_lora: the real CLI's argument names, a clip of the asked size and frame count."""
    import argparse, os, subprocess, sys, time

    def main():
        p = argparse.ArgumentParser()
        for a in ("--transformer-path", "--text-encoder-path", "--video-vae-path", "--audio-vae-path", "--spatial-upsampler-path",
                  "--prompt", "--height", "--width", "--num-frames", "--frame-rate", "--seed", "--output-path"):
            p.add_argument(a, required=True)
        p.add_argument("--lora", nargs="+", action="append", required=True)
        p.add_argument("--video-conditioning", nargs=2, action="append", required=True)
        p.add_argument("--image", nargs=3, action="append", required=True)
        p.add_argument("--stage-2-ic-lora", action="store_true")
        a = p.parse_args()
        mode = os.environ.get("FAKE_MODE", "ok")
        log = os.environ.get("FAKE_LOG")
        if log:
            open(log, "a").write(a.output_path + "|" + a.image[0][0] + "|" + a.prompt + "\\n")
        if mode == "sleep":
            time.sleep(600)
        if mode == "fail":
            sys.exit(3)
        import numpy as np
        w, h, n = int(a.width), int(a.height), int(a.num_frames)

        def frame(i):
            f = np.zeros((h, w, 3), np.uint8)
            f[:, :, 0] = (i * 20) % 256
            f[:, : w // 2, 1] = 90
            return f
        try:                                   # the real writer when imageio is installed (it picks the format by the suffix) ...
            if os.environ.get("FAKE_NO_IMAGEIO"):
                raise ImportError("imageio hidden")
            import imageio.v2 as iio
            wr = iio.get_writer(a.output_path, fps=int(a.frame_rate), macro_block_size=None, codec="libx264", quality=7)
            for i in range(n):
                wr.append_data(frame(i))
            wr.close()
        except ImportError:                    # ... else ffmpeg on raw frames (the CI box has ffmpeg, not imageio); same suffix rule
            ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{w}x{h}",
                                   "-r", str(a.frame_rate), "-i", "-", "-c:v", "libx264", "-pix_fmt", "yuv420p", a.output_path],
                                  stdin=subprocess.PIPE)
            for i in range(n):
                ff.stdin.write(frame(i).tobytes())
            ff.stdin.close()
            if ff.wait() != 0:
                sys.exit(5)
        if mode == "sound":
            tmp = a.output_path[:-4] + ".snd.mp4"
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", a.output_path, "-f", "lavfi", "-i", "sine=frequency=440",
                            "-shortest", "-c:v", "copy", "-c:a", "aac", tmp], check=True)
            os.replace(tmp, a.output_path)

    main()
''')


def _png(path: Path, color=(120, 80, 40), size=(640, 400)):
    from PIL import Image
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)


def _layout(path: Path, frames: int, sh=subprocess.run):
    """A grey 1280x704@24 clip of exactly ``frames`` frames, no sound (what a Blender layout is)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "color=c=gray:s=1280x704:r=24", "-frames:v", str(frames),
        "-pix_fmt", "yuv420p", "-an", str(path)], check=True, timeout=120)


def sha(p) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def make_job(folder: Path, *, seconds=9 / 24, chain=1, prompt="A knight walks along a castle wall at dawn.", extra=None) -> dict:
    """A job folder: first picture, ``1 + chain`` layouts of ``seconds`` each, ``job.json``."""
    frames = J.ltx_frames(seconds, 24)
    _png(folder / "first.png")
    job = {"schema": J.SCHEMA, "shot_id": "t1_a", "seed": 42, "seconds": seconds, "fps": 24, "width": 1280, "height": 704,
           "layout_mp4": "l0/layout.mp4", "first_picture": "first.png", "first_picture_sha256": sha(folder / "first.png"),
           "motion_prompt": prompt}
    _layout(folder / "l0" / "layout.mp4", frames)
    job["layout_sha256"] = sha(folder / "l0" / "layout.mp4")
    rows = []
    for i in range(chain):
        _layout(folder / f"l{i + 1}" / "layout.mp4", frames)
        rows.append({"shot_id": f"t1_b{i + 1}", "seed": 43 + i, "seconds": seconds, "layout_mp4": f"l{i + 1}/layout.mp4",
                     "layout_sha256": sha(folder / f"l{i + 1}" / "layout.mp4"), "motion_prompt": "The knight turns and looks at the sea.",
                     "hop": i + 1})
    if rows:
        job["chain"] = rows
    job.update(extra or {})
    (folder / "job.json").write_text(json.dumps(job, indent=1))
    return job


class FakeOp:
    """Stands in for huggingface_hub.CommitOperationAdd (the CI box has no hub package; the worker takes ``op_cls``)."""

    def __init__(self, path_in_repo, path_or_fileobj):
        self.path_in_repo, self.path_or_fileobj = path_in_repo, path_or_fileobj


class FakeApi:
    """The two calls of huggingface_hub the worker makes; ``down`` makes the hub unreachable; mp4 files are 'LFS' (sha256), the rest git blobs."""

    def __init__(self, down=False):
        self.files, self.commits, self.down = {}, [], down

    def create_commit(self, repo_id, repo_type, operations, commit_message):
        if self.down:
            raise ConnectionError("hub unreachable")
        self.commits.append([op.path_in_repo for op in operations])
        for op in operations:
            self.files[op.path_in_repo] = Path(op.path_or_fileobj).read_bytes()

    def get_paths_info(self, repo, paths, repo_type, expand=False):
        out = []
        for p in paths:
            if p not in self.files:
                continue
            d = self.files[p]
            if p.endswith(".mp4"):
                out.append(SimpleNamespace(path=p, lfs=SimpleNamespace(sha256=hashlib.sha256(d).hexdigest()), blob_id=None))
            else:
                out.append(SimpleNamespace(path=p, lfs=None, blob_id=hashlib.sha1(b"blob %d\0" % len(d) + d).hexdigest()))
        return out


def make_world(tmp: Path, *, chain=1, seconds=9 / 24, prompt=None, extra=None, kind="main") -> SimpleNamespace:
    """Everything ``body`` needs on disk: staged fake weights on a fake Volume, the packed batch tar, the spec, a launch whose LoRA pin is
    the fake file's own size and hash, the fake CLI package, and an ``sh`` that puts the fake package on the child's path."""
    launch = json.loads(json.dumps(M.LAUNCH))
    vol = tmp / "vol"
    root = M.base_root(launch, vol)
    for f in launch["uses"].values():
        (root / f).parent.mkdir(parents=True, exist_ok=True)
        (root / f).write_bytes(b"fake weights " + f.encode())
    lp = M.lora_path(launch, vol)
    lp.parent.mkdir(parents=True, exist_ok=True)
    lp.write_bytes(b"fake IC-LoRA")
    launch["lora"].update(size=lp.stat().st_size, sha256=sha(lp))
    folder = tmp / "job"
    make_job(folder, chain=chain, seconds=seconds, **({"prompt": prompt} if prompt else {}), extra=extra)
    if kind == "smoke":
        job = json.loads((folder / "job.json").read_text())
        job.pop("chain", None)
        (folder / "job.json").write_text(json.dumps(job))
    path, bsha = J.pack(folder, tmp / "pack", launch, smoke=True)
    pkg = tmp / "fakepkg" / "ltx_pipelines"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("")
    (pkg / "ic_lora.py").write_text(FAKE_IC_LORA)
    env = dict(os.environ, PYTHONPATH=str(tmp / "fakepkg"), FAKE_LOG=str(tmp / "fake_cli.log"))
    offset = [0.0]

    def sh(cmd, **kw):
        kw.setdefault("env", env)
        kw["env"] = dict(kw["env"], **{"FAKE_MODE": os.environ.get("FAKE_MODE", "ok")})
        r = subprocess.run(cmd, **kw)
        if "ltx_pipelines.ic_lora" in " ".join(map(str, cmd)):
            offset[0] += float(os.environ.get("FAKE_CLOCK_JUMP", "0"))
        return r

    spec = {"kind": kind, "run_id": "abc123_def456", "batch_path": f"code/layout/batch-{bsha}.tar.gz", "batch_sha": bsha,
            "worker_sha": "w" * 64}
    return SimpleNamespace(launch=launch, vol=vol, spec=spec, tar=path, work=tmp / "work", sh=sh, offset=offset, log=tmp / "fake_cli.log",
                           api=FakeApi())


class NoPoller:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def facts(self):
        return {"gpu_used_peak_gib": 0.0, "samples": 0}


def run_body(w, *, timeout_s=3600, api="default", poller_factory=NoPoller, **kw):
    import time
    return M.body(w.spec, w.launch, timeout_s=timeout_s, vol_root=w.vol, work=w.work, api=w.api if api == "default" else api,
                  download=lambda name, dest: w.tar, sh=w.sh, poller_factory=poller_factory, now=lambda: time.time() + w.offset[0],
                  sleep=lambda s: None, op_cls=FakeOp, baked=w.vol / "none.json", **kw)


def main(argv=None) -> int:
    import tempfile
    root = Path((argv or sys.argv[1:] or [tempfile.mkdtemp()])[0])
    root.mkdir(parents=True, exist_ok=True)
    w = make_world(root)
    res = run_body(w)
    print(json.dumps({"state": res["state"], "error": res["error"], "clips": [
        {k: c.get(k) for k in ("shot_id", "state", "gen_s", "frames_out", "sound", "sha256")} for c in res["clips"]],
        "verified": res.get("verified")}, indent=1))
    return 0 if res["state"] == "DONE" else 1


if __name__ == "__main__":
    sys.exit(main())
