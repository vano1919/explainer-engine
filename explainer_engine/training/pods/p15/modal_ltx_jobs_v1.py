"""The first minute's two LTX clips on Modal (stone-age pilot, c1 puddle foot 81 frames, c2 tundra mammoths 89 frames; plain LTX-2.5 distilled
image-to-video from the Qwen first frames, no LoRA, no control). One A100-80 function, timeout from the cap (OR-37), retries 0.
    $env:EE_MODAL_GO="<the creator's message id>"; modal run modal_ltx_jobs_v1.py::check   (free)   then   ::main
The jobs file and the runner come from the image (baked) and are held to the sha256 below; the weights are symlinked from the Volume ee-weights
and sha256-checked in the container; clips go to the jobs file's ``out`` as they are made (OR-33)."""
import hashlib, json, os, subprocess, tarfile, threading, time
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
IN = "route_test_2026-11/sa_test/in_ltx1"
JOBS = "sa_ltx1_jobs.json"   # c1, c2 of the first minute
SHAS = {JOBS: "9a5f8480a9535fe1bab2b42df4c7eda41c335b1e4a1e095dc9767d1aa0b8db2f", "ltx_jobs.py": "fab0a52321dd589733b4747f5f9d33edb640e8b1ce12721da48ac490ac779abc",
        "ff_i01_puddle.png": "9e1410020f4840ae5490c2561cb0b69ab106a4220ccfacde331c0d74b8f90c80", "ff_m_tundra.png": "fa3d09ae314689a76e5115525cbd499a3c428c83366e1162d8aba46df37b7fa2"}
OUT = "route_test_2026-11/sa_test/out_ltx1"   # must equal the jobs file's "out" (checked at start)
BUNDLE_SHA = "53eb909ef3a0c37a332dbb582bc62bdd194733eeba867eb7f5467a84679d0681"
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
SECRET_NAME = "huggingface-secret"
USD_PER_H = 2.5      # A100-80 list price, modal.com/pricing, checked 2026-11-07 (CPU/RAM extra, covered by the 0.9 factor)
CAP_USD, SMOKE_CAP_USD, COLD_START_S = 1.0, 0.25, 120   # 2 clips (81 + 89 frames, 1920x1088) incl. loading ~45 GB from the Volume: ~10-15 min expected (~$0.45), cap $1.00; needs the creator's yes with this price


def cost_timeout(cap_usd, usd_per_h=USD_PER_H, cold_start_s=COLD_START_S):
    """OR-37: the function timeout comes from the cap, never by hand: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    startup = cold_start_s * usd_per_h / 3600
    return int(0.9 * (cap_usd - startup) / usd_per_h * 3600)


def check_timeout(timeout_s, cap_usd, usd_per_h=USD_PER_H, cold_start_s=COLD_START_S):
    if timeout_s * usd_per_h / 3600 + cold_start_s * usd_per_h / 3600 > cap_usd:
        raise ValueError(f"timeout {timeout_s}s costs more than the cap ${cap_usd}")
    return timeout_s


TIMEOUT_S = check_timeout(cost_timeout(CAP_USD), CAP_USD)
SMOKE_TIMEOUT_S = check_timeout(cost_timeout(SMOKE_CAP_USD), SMOKE_CAP_USD)
HF_LINKS = [("Qwen/Qwen-Image-2.1", "model", "d26bb61231c349cf6b7896fa83353113880e1ba3"),
            ("Lightricks/LTX-2.5", "model", "49b093a39c19169a8a81721dcc541e07e945232f"),
            ("vano1919/tmr-artifacts", "dataset", None)]


def go_gate(env=os.environ):
    v = env.get("EE_MODAL_GO", "")
    if not v.startswith("cmsg_"):
        raise SystemExit("EE_MODAL_GO must be the card id of the creator's yes (OR-23); nothing was started")
    return v


def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def link_hf_cache(vol_root, hf_home):
    n = 0
    for repo, rtype, rev in HF_LINKS:
        src = Path(vol_root) / rtype / repo
        if not src.is_dir():
            continue
        base = Path(hf_home) / "hub" / (f"{rtype}s--" + repo.replace("/", "--"))
        snap = base / "snapshots" / (rev or "local")
        (base / "refs").mkdir(parents=True, exist_ok=True)
        (base / "refs" / "main").write_text(rev or "local")
        for f in src.rglob("*"):
            if f.is_file() and ".cache" not in f.relative_to(src).parts:
                d = snap / f.relative_to(src)
                d.parent.mkdir(parents=True, exist_ok=True)
                if not d.exists():
                    d.symlink_to(f)
                    n += 1
    return n


def _sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _is_limit(e):
    t = repr(e).lower()
    return "429" in t or "rate limit" in t or "too many requests" in t or "503" in t or "502" in t


def _retry_after(e, default):
    r = getattr(getattr(e, "response", None), "headers", None) or {}
    try:
        return max(float(r.get("Retry-After", 0)), default)
    except (TypeError, ValueError):
        return default


def _upload_batch(api, out, seen, sleep=time.sleep, base=15.0, tries=6, final=False):
    """One commit with every new file (HF caps commits per hour, 128 for us on 2026-11-07: one commit per file ran into it and lost
    the last photos). A 429 or 5xx is retried with exponential backoff that honours Retry-After; a file is never dropped: it stays
    unseen and the next tick sends it. At the final flush the retries are bounded and the Volume copy (persist) is the safety net."""
    from huggingface_hub import CommitOperationAdd
    new = [p for p in sorted(Path(out).rglob("*")) if p.is_file() and p.stat().st_size > 0 and (str(p), p.stat().st_size) not in seen]
    if not new:
        return 0
    ops = [CommitOperationAdd(path_in_repo=f"{OUT}/{p.relative_to(out)}", path_or_fileobj=str(p)) for p in new]
    keys = [(str(p), p.stat().st_size) for p in new]
    for k in range(tries if final else 2):
        try:
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops, commit_message=f"{OUT}: {len(new)} files")
            seen.update(keys)
            return len(new)
        except Exception as e:  # noqa: BLE001
            print("upload failed", len(new), "files", repr(e)[:160], flush=True)
            if not _is_limit(e):
                return 0
            sleep(_retry_after(e, base * 2 ** k))
    return 0


def _uploader(out, stop, api=None, interval=60.0):
    if api is None:
        from huggingface_hub import HfApi
        api = HfApi(token=_tok())
    seen = set()
    while True:
        done = stop.is_set()
        _upload_batch(api, out, seen, final=done)
        if done:
            return
        stop.wait(interval)


CHECK = ("import sys, importlib; mods = ['torch', 'huggingface_hub', 'PIL', 'ltx_core', 'ltx_pipelines', 'ltx_pipelines.distilled']; bad = []\n"
         "for m in mods:\n"
         "    try: importlib.import_module(m); print('ok', m)\n"
         "    except Exception as e: bad.append(m); print('MISSING', m, repr(e)[:150])\n"
         "sys.exit(1 if bad else 0)")


def import_check():
    """OR-37: every module the run imports, on the container's own python; fails in seconds, before any weight is read."""
    r = subprocess.run(["python3", "-c", CHECK], capture_output=True, text=True)
    print(r.stdout, r.stderr[-500:], flush=True)
    return r.returncode


def deadline_guard(seconds, on_fire):
    """in-container wall: fires ``on_fire`` after ``seconds`` (a daemon timer); the caller's on_fire writes the beat, flushes and exits."""
    t = threading.Timer(seconds, on_fire)
    t.daemon = True
    t.start()
    return t


def verdict(out, expected):
    """DONE only if every expected output exists, is non-empty and (for png) opens; anything less is FAILED with n_ok/n_expected."""
    ok = []
    for name in expected:
        p = Path(out) / name
        try:
            good = p.is_file() and p.stat().st_size > 0
            if good and p.suffix == ".png":
                from PIL import Image
                with Image.open(p) as im:
                    im.verify()
        except Exception:  # noqa: BLE001
            good = False
        if good:
            ok.append(name)
    return {"state": "DONE" if len(ok) == len(expected) else "FAILED", "n_ok": len(ok), "n_expected": len(expected)}



LOCAL_IN = "/in_local"
VOL_OUT = "/w/out_ltx1"   # a copy of every output on the Volume too: modal volume get ee-weights out_v3 .


def persist(out):
    import shutil
    try:
        shutil.copytree(out, VOL_OUT, dirs_exist_ok=True)
        vol.commit()
    except Exception as e:  # noqa: BLE001
        print("volume copy failed", repr(e)[:200], flush=True)


def expected_outputs(doc, smoke=False):
    return [f"ltx/{j['clip_id']}.mp4" for j in doc["jobs"]] and [f"ltx/{j['id']}.mp4" for j in doc["jobs"]]


def body(smoke=False):
    if import_check() != 0:
        raise SystemExit("OR-37: the image lacks a module the run imports; stopped before any weight was read")
    from huggingface_hub import hf_hub_download
    t0, out, inp = time.time(), Path("/workspace/out"), Path("/workspace/in")
    out.mkdir(parents=True, exist_ok=True)
    inp.mkdir(parents=True, exist_ok=True)
    hf_home = Path("/tmp/hf")
    print("linked", link_hf_cache("/w", hf_home), "weight files", flush=True)

    def fetch(name, sha):
        local = Path(LOCAL_IN) / name   # inputs baked into the image (HF commits were rate-limited 15:30 UTC); the sha pin still holds
        p = local if local.is_file() else hf_hub_download(HF_REPO, f"{IN}/{name}", repo_type="dataset", local_dir="/tmp/dl", token=_tok())
        if _sha(p) != sha:
            raise SystemExit(f"{name}: sha256 mismatch")
        (inp / name).write_bytes(Path(p).read_bytes())
    for name, sha in SHAS.items():
        fetch(name, sha)
    doc = json.loads((inp / JOBS).read_text())
    if doc["out"] != OUT:
        raise SystemExit(f"jobs file out {doc['out']} != {OUT}")
    b = hf_hub_download(HF_REPO, "code/p15/ee_src.tar.gz", repo_type="dataset", local_dir="/tmp/job", token=_tok())
    if _sha(b) != BUNDLE_SHA:
        raise SystemExit("bundle sha mismatch")
    Path("/workspace/ee").mkdir(parents=True, exist_ok=True)
    with tarfile.open(b) as t:
        t.extractall("/workspace/ee")
    cfg = json.loads(Path("/workspace/ee/explainer_engine/training/pods/p15/p15.json").read_text())
    timeout = SMOKE_TIMEOUT_S if smoke else TIMEOUT_S
    env = dict(os.environ, HF_HOME=str(hf_home), EE_OUT=str(out), PYTHONUNBUFFERED="1", XW_GPU_MODE=cfg["qwen"]["gpu_mode"],
               EE_DEADLINE=str(time.time() + timeout), P14_LOCAL_ROOTS=json.dumps([[cfg["hf_root"], str(out)]]), PYTHONPATH="/workspace/ee")
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(out, stop), daemon=True)
    th.start()

    def _fire():
        (out / "beat.txt").write_text("TIMEOUT: the in-container deadline fired\n")
        persist(out)
        stop.set()
        th.join(timeout=40)
        os._exit(3)
    deadline_guard(timeout - 60, _fire)
    rc = 0
    with open(out / "modal_jobs.log", "a") as f:
        rc = subprocess.run(["python3", str(inp / "ltx_jobs.py"), "--jobs", str(inp / JOBS), "--inputs", str(inp), "--out", str(out)],
                            env=env, cwd="/workspace/ee", stdout=f, stderr=subprocess.STDOUT).returncode
    v = verdict(out, expected_outputs(doc, smoke))
    if rc != 0:
        v["state"] = "FAILED"
    (out / "beat.txt").write_text(f"{v['state']} rc={rc} ok={v['n_ok']}/{v['n_expected']} seconds={int(time.time() - t0)}\n")
    persist(out)
    stop.set()
    th.join(timeout=300)
    return {"rc": rc, "seconds": int(time.time() - t0), **v}


if modal is not None:
    app = modal.App("ee-ltx-jobs")
    vol = modal.Volume.from_name("ee-weights", version=2)
    image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12")
             .apt_install("ffmpeg", "git")
             .run_commands(
                 'pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0"',
                 "git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q "
                 "e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-core "
                 "-e /workspace/LTX-2/packages/ltx-pipelines")
             .add_local_dir("/home/user/in_ltx1", LOCAL_IN))

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def ltx_jobs():
        return body()

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=SMOKE_TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def ltx_smoke():
        return body(smoke=True)

    @app.local_entrypoint()
    def smoke():
        print("GO card", go_gate(), "smoke timeout", SMOKE_TIMEOUT_S, "s", flush=True)
        print("result", ltx_smoke.remote())

    @app.function(image=image, cpu=2, memory=4096, timeout=300, retries=0)
    def env_check():
        """FREE (CPU only, no GPU, no weights): OR-37 proof of the image before the paid GPU run."""
        return import_check()

    @app.local_entrypoint()
    def check():
        print("env_check rc", env_check.remote())

    @app.local_entrypoint()
    def main():
        print("GO card", go_gate(), "timeout", TIMEOUT_S, "s", flush=True)
        print("result", ltx_jobs.remote())
