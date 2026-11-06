"""Route-test pod, the LTX part (guide step 3, D-116): every job of ``ltx_jobs.json`` (``ltx_job/1``, written by
``edit/ltx_jobs.py``) as one ``ltx_pipelines.ic_lora`` call at the pinned LTX-2 code, then the free FFmpeg upscale of each clip.

Runs on the pod under ``p14.sh`` (inside pod_wrapper.sh, which uploads ``$EE_OUT`` as files land: OR-33), stdlib + ffmpeg +
huggingface_hub for the downloads. Nothing here decides the matrix: the jobs file does, and its sha256 is pinned in ``p14.json``.

- A job whose weights are not pinned (LJ-01: a null sha256, e.g. the gated Gemma 3 before the creator accepts its licence), whose
  first frame is not on the vault yet, or whose chained clip failed is skipped with its reason; the pod goes on.
- Inputs are sha256-checked when the jobs file names a hash; derived controls (the inverted line pass, the canny of the colour pass)
  are made here and their hashes recorded in the clip's sidecar.
- A chained clip (``chain_from``) takes the previous clip's last N frames as image conditions at frames 0..N-1.
- Every clip: ``<out>/ltx/<job>.mp4`` + ``<job>.json`` (command, seconds, return code, input hashes), then the 2560x1440 copy
  ``<out>/ltx_up/<job>.mp4`` (``finish/upscale.video_filter`` with ``ROUTE_TEST``: crop to
  16:9, Lanczos, cas, grain; both files kept). ``<out>/ltx/speeds.json`` holds the
  measured seconds per clip (median, min-max, failure rate) for ``config/job_speeds.json`` ``ltx_clip_s_per_clip``.

Every flag string is in ``FLAGS``, read at Lightricks/LTX-2@e98f6d9 (packages/ltx-pipelines/src/ltx_pipelines/utils/args.py and
ic_lora.py; the lines are in the comments); the module is ``ltx_pipelines.ic_lora`` (ic_lora.py:813 main).
"""
import hashlib
import json
import os
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CFG_NAME = "p14.json"
MODELS = Path(os.environ.get("P14_MODELS", "/workspace/models"))
CODE_DIR = Path("/workspace/LTX-2")
MODULE = "ltx_pipelines.ic_lora"   # ic_lora.py:813 main(), :815 resolve_cli_params(distilled=True)

FLAGS = {
    "transformer": "--transformer-path",           # args.py:710 (split layout: LTX-2.5)
    "text_encoder": "--text-encoder-path",         # args.py:720 (split single-file Gemma 4 TE of LTX-2.5)
    "video_vae": "--video-vae-path",               # args.py:726
    "audio_vae": "--audio-vae-path",               # args.py:737
    "distilled_ckpt": "--distilled-checkpoint-path",   # args.py:669 (monolith: LTX-2.3)
    "gemma_root": "--gemma-root",                  # args.py:700 (monolith: a Gemma HF directory)
    "upsampler": "--spatial-upsampler-path",       # args.py:1608 (2-stage distilled, required)
    "lora": "--lora",                              # args.py:826 (LoraAction: PATH [STRENGTH])
    "video_cond": "--video-conditioning",          # ic_lora.py:820 (PATH STRENGTH, repeatable: VideoConditioningAction appends)
    "attn_mask": "--conditioning-attention-mask",  # ic_lora.py:831 (MASK_PATH STRENGTH)
    "stage2_ic": "--stage-2-ic-lora",              # ic_lora.py:855 (store_true)
    "image": "--image",                            # args.py:1003 (ImageAction: PATH FRAME_IDX STRENGTH [BINDING])
    "prompt": "--prompt",                          # args.py:813
    "width": "--width",                            # args.py:990
    "height": "--height",                          # args.py:984
    "num_frames": "--num-frames",                  # args.py:966 (8k+1)
    "frame_rate": "--frame-rate",                  # args.py:997
    "seed": "--seed",                              # args.py:759
    "output": "--output-path",                     # args.py:819
}


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


class Log:
    def __init__(self, out):
        self.out = Path(out)
        self.out.mkdir(parents=True, exist_ok=True)

    def ev(self, name, **kw):
        line = {"t": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "ev": name, **kw}
        with open(self.out / "t.jsonl", "a", encoding="utf-8") as f:
            f.write(json.dumps(line) + "\n")

    def stage_line(self, text):
        with open(self.out / "stages.txt", "a", encoding="utf-8") as f:
            f.write(f"{time.strftime('%H:%M:%S', time.gmtime())} {text}\n")

    def progress(self, text):
        tmp = self.out / "progress.txt.tmp"
        tmp.write_text(f"{time.strftime('%T', time.gmtime())} {text}\n", encoding="utf-8")
        os.replace(tmp, self.out / "progress.txt")


def write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1), encoding="utf-8")
    os.replace(tmp, path)


# --- weights ----------------------------------------------------------------------------------------------------------------

def weight_paths(cfg, base):
    """Local paths of one base's files (``p14.json`` weights[base]) under MODELS/<base>."""
    w, root = cfg["weights"][base], MODELS / base
    out = {"lora": root / "lora" / w["lora"]["file"], "upsampler": root / w["upsampler"]["file"]}
    if base == "ltx25":
        files = w["files"]
        pick = lambda part: root / next(f for f in files if part in f)  # noqa: E731
        out.update(transformer=pick("distilled-transformer"), text_encoder=pick("text_encoders/"), video_vae=pick("video-vae"),
                   audio_vae=pick("audio-vae"))
    else:
        out.update(distilled_ckpt=root / w["checkpoint"]["file"], gemma_root=root / "gemma")
    return out


def unpinned(job):
    """LJ-01 at the pod: the weights of the job that carry no sha256 (the job is skipped while any is listed)."""
    return [x["id"] for x in (job["model"], job["lora"], job.get("text_encoder")) if x and not x.get("sha256")]


def bases_wanted(jobs):
    return sorted({j["base"] for j in jobs if not unpinned(j)})


def download_base(cfg, base, log):
    """Fetches one base's files at their pinned revisions and checks every sha256 the config names; returns the bad names."""
    from huggingface_hub import hf_hub_download, snapshot_download
    w, root, bad = cfg["weights"][base], MODELS / base, []
    items = [(w["repo"], w["revision"], f, sha) for f, sha in (w.get("files") or {}).items()]
    if base == "ltx23":
        items.append((w["repo"], w["revision"], w["checkpoint"]["file"], w["checkpoint"]["sha256"]))
    items.append((w["repo"], w["revision"], w["upsampler"]["file"], w["upsampler"]["sha256"]))
    lo = w["lora"]
    items.append((lo["repo"], lo["revision"], lo["file"], lo["sha256"]))
    for repo, rev, f, want in items:
        sub = root / ("lora" if repo == lo["repo"] else "")
        log.progress(f"downloading {base} {f}")
        try:
            p = Path(hf_hub_download(repo, f, revision=rev, local_dir=str(sub)))
            if want and sha256_file(p) != want:
                bad.append(f)
                log.ev("sha256_mismatch", base=base, file=f)
        except Exception as e:   # noqa: BLE001
            bad.append(f)
            log.ev("download_failed", base=base, file=f, error=str(e)[:300])
    te = w.get("text_encoder")
    if te:
        try:
            snapshot_download(te["repo"], revision=te["revision"], local_dir=str(root / "gemma"))
            for f, want in (te.get("files") or {}).items():
                if sha256_file(root / "gemma" / f) != want:
                    bad.append(f"gemma/{f}")
        except Exception as e:   # noqa: BLE001
            bad.append("gemma")
            log.ev("download_failed", base=base, file="gemma", error=str(e)[:300])
    return bad


# --- inputs -------------------------------------------------------------------------------------------------------------------

def fetch_input(cfg, path, want, work):
    """One vault file (a layout clip, a first frame) into ``work``; (local path, sha256) or (None, reason)."""
    from huggingface_hub import hf_hub_download
    try:
        p = Path(hf_hub_download(cfg["hf"]["repo"], path, repo_type=cfg["hf"]["repo_type"], local_dir=str(work)))
    except Exception as e:   # noqa: BLE001
        return None, f"not on the vault: {path} ({str(e)[:120]})"
    got = sha256_file(p)
    if want and got != want:
        return None, f"sha256 of {path} is {got}, not the pinned {want}"
    return p, got


def derive_cmd(cfg, kind, src, dst):
    """FFmpeg for a derived control: ``invert`` (the line pass, black ink on white -> white lines on black, like the canny maps
    the Union LoRA was trained on) or ``canny`` (FFmpeg's Canny edge detector over the colour pass, white edges on black)."""
    vf = {"invert": "negate", "canny": cfg["controls"]["canny_vf"]}[kind]
    return ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", vf, "-c:v", "libx264", "-crf", "12", "-pix_fmt", "yuv420p",
            str(dst)]


def chain_cmd(prev, frames, total, dst_pattern):
    """The last ``frames`` frames of the previous clip as PNGs (``dst_pattern`` with %d from 0)."""
    first = total - frames
    return ["ffmpeg", "-y", "-v", "error", "-i", str(prev), "-vf", f"select='gte(n\\,{first})'", "-vsync", "0", "-start_number",
            "0", str(dst_pattern)]


# --- one generation -------------------------------------------------------------------------------------------------------------

def _flag(cmd, key, *vals):
    cmd += [FLAGS[key], *[str(v) for v in vals]]


def command(job, cfg, paths):
    """The ic_lora argv of one job. ``paths``: images [(path, frame)], controls [(path, strength)], mask (path, strength) or
    None, out."""
    wp = weight_paths(cfg, job["base"])
    cmd = [sys.executable, "-m", MODULE]
    if job["base"] == "ltx25":
        for k in ("transformer", "text_encoder", "video_vae", "audio_vae"):
            _flag(cmd, k, wp[k])
    else:
        _flag(cmd, "distilled_ckpt", wp["distilled_ckpt"])
        _flag(cmd, "gemma_root", wp["gemma_root"])
    _flag(cmd, "upsampler", wp["upsampler"])
    _flag(cmd, "lora", wp["lora"], job["lora"]["strength"])
    for p, s in paths["controls"]:
        _flag(cmd, "video_cond", p, s)
    if paths.get("mask"):
        _flag(cmd, "attn_mask", *paths["mask"])
    if job["stage2_ic"]:
        _flag(cmd, "stage2_ic")
    for p, frame in paths["images"]:
        _flag(cmd, "image", p, frame, 1.0)
    _flag(cmd, "prompt", job["prompt"])
    _flag(cmd, "width", job["width"])
    _flag(cmd, "height", job["height"])
    _flag(cmd, "num_frames", job["frames"])
    _flag(cmd, "frame_rate", job["fps"])
    _flag(cmd, "seed", job["seed"])
    _flag(cmd, "output", paths["out"])
    return cmd


def upscale_cmd(cfg, src, dst):
    return ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-vf", cfg["upscale"]["vf"], "-an", "-c:v", "libx264", "-crf", "17",
            "-preset", "medium", "-pix_fmt", "yuv420p", str(dst)]   # finish/upscale.upscale's encode


def run_cmd(cmd, timeout, log, label):
    stop = threading.Event()

    def tick():
        t0 = time.time()
        while not stop.wait(60):
            log.progress(f"{label} {int(time.time() - t0)} s")

    threading.Thread(target=tick, daemon=True).start()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=str(CODE_DIR) if CODE_DIR.is_dir() else None)
        return p.returncode, (p.stderr or "")[-2000:]
    except subprocess.TimeoutExpired as e:
        return "timeout", str(e.stderr or "")[-2000:]
    except OSError as e:
        return "oserror", str(e)[-2000:]
    finally:
        stop.set()


def speeds(rows):
    """Seconds per clip of the generations that ran: median, min, max, and the failure rate over every started one."""
    started = [r for r in rows if r["status"] in ("ok", "failed")]
    ok = [r["seconds"] for r in started if r["status"] == "ok"]
    return {"started": len(started), "ok": len(ok), "failure_rate": round(1 - len(ok) / len(started), 3) if started else None,
            "median_s": round(statistics.median(ok), 1) if ok else None, "min_s": round(min(ok), 1) if ok else None,
            "max_s": round(max(ok), 1) if ok else None}


def may_start(now, deadline, reserve_s):
    return now < deadline - reserve_s


def run(cfg, jobs_doc, out, deadline, log, *, runner=run_cmd, fetch=fetch_input, download=download_base, sh=subprocess.run):
    out, work = Path(out), MODELS / "p14"
    (out / "ltx").mkdir(parents=True, exist_ok=True)
    jobs = jobs_doc["jobs"]
    broken = {b: download(cfg, b, log) for b in bases_wanted(jobs)}
    rows, done = [], {}
    for job in jobs:
        jid = job["id"]
        row = {"job": jid, "base": job["base"], "variant": job.get("variant"), "status": "skipped"}
        rows.append(row)
        why = None
        if unpinned(job):
            why = f"not pinned: {', '.join(unpinned(job))} (LJ-01)"
        elif broken.get(job["base"]):
            why = f"weights of {job['base']} missing or wrong: {', '.join(broken[job['base']])}"
        elif not may_start(time.time(), deadline, cfg["end_reserve_min"] * 60):
            why = "inside the end reserve"
        elif job.get("chain_from") and done.get(job["chain_from"]["job"]) is None:
            why = f"chained clip {job['chain_from']['job']} did not finish"
        paths, hashes = {"controls": [], "images": [], "mask": None, "out": out / "ltx" / f"{jid}.mp4"}, {}
        if why is None:
            for c in job["conditioning"]:
                p, got = fetch(cfg, c["path"], c["sha256"], work / "in")
                if p is None:
                    why = got
                    break
                hashes[c["path"]] = got
                if c.get("derive"):
                    dst = work / "derived" / f"{jid}.{c['pass']}.mp4"
                    dst.parent.mkdir(parents=True, exist_ok=True)
                    sh(derive_cmd(cfg, c["derive"], p, dst), check=True)
                    hashes[f"derived:{c['pass']}"] = sha256_file(dst)
                    p = dst
                paths["controls"].append((p, c["strength"]))
        if why is None and job.get("chain_from"):
            prev, n = done[job["chain_from"]["job"]], job["chain_from"]["frames"]
            pat = work / "chain" / jid / "f_%d.png"
            pat.parent.mkdir(parents=True, exist_ok=True)
            total = next(j["frames"] for j in jobs if j["id"] == job["chain_from"]["job"])
            sh(chain_cmd(prev, n, total, pat), check=True)
            paths["images"] = [(pat.parent / f"f_{k}.png", k) for k in range(n)]
        elif why is None:
            p, got = fetch(cfg, job["first_frame"]["path"], job["first_frame"]["sha256"], work / "in")
            if p is None:
                why = f"no first frame: {got}"
            else:
                hashes[job["first_frame"]["path"]] = got
                paths["images"] = [(p, 0)]
        if why:
            row["reason"] = why
            log.stage_line(f"skipped {jid} ({why})")
            log.ev("job_skipped", job=jid, reason=why)
            continue
        cmd = command(job, cfg, paths)
        log.stage_line(f"start {jid}")
        t0 = time.time()
        rc, err = runner(cmd, cfg["clip_timeout_s"], log, jid)
        row.update(seconds=round(time.time() - t0, 1), rc=rc, status="ok" if rc == 0 and paths["out"].exists() else "failed")
        side = {"job": jid, "cmd": [str(x) for x in cmd], "rc": rc, "seconds": row["seconds"], "inputs": hashes,
                "stderr_tail": err if rc != 0 else ""}
        if row["status"] == "ok":
            side["sha256"] = sha256_file(paths["out"])
            done[jid] = paths["out"]
            up = out / "ltx_up" / f"{jid}.mp4"
            up.parent.mkdir(parents=True, exist_ok=True)
            u = sh(upscale_cmd(cfg, paths["out"], up))
            side["upscaled"] = {"path": f"ltx_up/{jid}.mp4", "rc": getattr(u, "returncode", None),
                                "sha256": sha256_file(up) if up.exists() else None}
        write_json(out / "ltx" / f"{jid}.json", side)
        log.stage_line(f"{row['status']} {jid} {row['seconds']} s")
        write_json(out / "ltx" / "speeds.json", {"rows": rows, **speeds(rows)})
    write_json(out / "ltx" / "speeds.json", {"rows": rows, **speeds(rows)})
    log.progress("done")
    return rows


def main():
    cfg = json.loads((HERE / CFG_NAME).read_text(encoding="utf-8"))
    jobs_doc = json.loads((HERE / cfg["jobs_file"]).read_text(encoding="utf-8"))
    if jobs_doc.get("schema") != "ltx_job/1" or jobs_doc["code"]["sha"] != cfg["code"]["sha"]:
        raise SystemExit("the jobs file is not ltx_job/1 at this pod's code pin")
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    log = Log(out)
    deadline = float(os.environ["EE_DEADLINE"])
    rows = run(cfg, jobs_doc, out, deadline, log)
    log.ev("ltx_exit", ok=sum(r["status"] == "ok" for r in rows), jobs=len(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main())
