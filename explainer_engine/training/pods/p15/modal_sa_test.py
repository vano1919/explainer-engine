"""6 test Qwen photos on Modal (OR-23 plan OR23_SA_TEST_6_QWEN_PHOTOS.md; the creator's yes cmsg_01Hnu5zB86sjUj5GtTgaUkPWKzpwThjB1xvJu5yyAbzP6j,
2026-11-07 13:16 UTC). One A100-80 function, hard timeout 25 min, retries 0. Run on the creator's PC:
    set EE_MODAL_GO=cmsg_01Hnu5zB86sjUj5GtTgaUkPWKzpwThjB1xvJu5yyAbzP6j   (PowerShell: $env:EE_MODAL_GO="...")
    modal run modal_sa_test.py
Inputs (6 stills, prompts, runner) come from HF vano1919/tmr-artifacts route_test_2026-11/sa_test/in_v2/ held to the sha256 below; photos go to
.../sa_test/out_v2/qwen/ as they are drawn (OR-33). Weights come from the Volume ee-weights; nothing is downloaded from outside."""
import hashlib, json, os, subprocess, tarfile, threading, time
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
IN = "route_test_2026-11/sa_test/in_v2"   # Argon review re-render (KP-50..55); in/ keeps the first test
OUT = "route_test_2026-11/sa_test/out_v2"
SHAS = {
 "sa_camp_block.png": "db5e6c9f8814c3b1a99f81086dcb6bbe39ecb6ad55d1badf0c1498d9a33ed9f6",
 "sa_camp_flat3.png": "e909321cb9ddbef2427dba0718921a4fbdb2dbade8d0467c8f902a8762538e3b",
 "sa_cave_block.png": "b3aff0e9a09f06c82a4a249e02d6fe18ad02e996b4c1c0fb4c455db37466ae42",
 "sa_cave_flat3.png": "f619ffcb370f14e9ac785c7d4a61ca5c752b8d1ddf1a94a2a9adf9fadb673cae",
 "sa_ice_block.png": "94f36f95f8573558c65e81caaccdab8392b960da9f1211307875fb4740f1018d",
 "sa_ice_flat3.png": "ee61f371f4391a532a7b1719d46f3f1a11949ee7b35bfd7d64dd271c907cce1a",
 "sa_prompts.json": "7ca6620dd46916b26d1f5fae36cd07c00f1bb4d4ee1075003f3b49b1fff715ba",
 "sa_test_qwen.py": "03d8a86c64c11fd1c8aee19218d33b4afd93968ffd4e3c8b17f933adbd1e2622"}
BUNDLE_SHA = "53eb909ef3a0c37a332dbb582bc62bdd194733eeba867eb7f5467a84679d0681"
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
SECRET_NAME = "huggingface-secret"
USD_PER_H = 2.5      # A100-80 list price, modal.com/pricing, checked 2026-11-07 (CPU/RAM extra, covered by the 0.9 factor)
CAP_USD, SMOKE_CAP_USD, COLD_START_S = 1.0, 0.25, 90


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


def _uploader(out, stop):
    from huggingface_hub import HfApi
    api, seen = HfApi(token=_tok()), set()
    while True:
        done = stop.is_set()
        for p in sorted(Path(out).rglob("*")):
            if p.is_file() and p.stat().st_size > 0 and (str(p), p.stat().st_size) not in seen:
                try:
                    api.upload_file(path_or_fileobj=str(p), path_in_repo=f"{OUT}/{p.relative_to(out)}", repo_id=HF_REPO, repo_type="dataset")
                    seen.add((str(p), p.stat().st_size))
                except Exception as e:  # noqa: BLE001
                    print("upload failed", p.name, repr(e)[:120], flush=True)
        if done:
            return
        stop.wait(20)


CHECK = ("import sys; sys.path.insert(0, '/workspace/VideoX-Fun'); "
         "import importlib; mods = ['torch', 'diffusers', 'peft', 'huggingface_hub', 'PIL', 'einops', 'timm', 'omegaconf', 'cv2', 'kornia', "
         "'videox_fun.models', 'videox_fun.pipeline', 'videox_fun.utils']; bad = []\n"
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


WEIGHTS = (0.7, 1.0)   # creator 2026-11-07 14:42 UTC: the house 0.7 and once at 1.0, each in a fresh process (the merge is in place)


def wtag(w):
    return f"_w{int(round(w * 10)):02d}"


def body(smoke=False, seeds="", weights=()):
    if import_check() != 0:
        raise SystemExit("OR-37: the image lacks a module the run imports; stopped before any weight was read")
    from huggingface_hub import hf_hub_download
    t0, out, inp = time.time(), Path("/workspace/out"), Path("/workspace/in")
    out.mkdir(parents=True, exist_ok=True)
    inp.mkdir(parents=True, exist_ok=True)
    hf_home = Path("/tmp/hf")
    print("linked", link_hf_cache("/w", hf_home), "weight files", flush=True)
    for name, sha in SHAS.items():
        p = hf_hub_download(HF_REPO, f"{IN}/{name}", repo_type="dataset", local_dir="/tmp/dl", token=_tok())
        if _sha(p) != sha:
            raise SystemExit(f"{name}: sha256 mismatch")
        (inp / name).write_bytes(Path(p).read_bytes())
    b = hf_hub_download(HF_REPO, "code/p15/ee_src.tar.gz", repo_type="dataset", local_dir="/tmp/job", token=_tok())
    if _sha(b) != BUNDLE_SHA:
        raise SystemExit("bundle sha mismatch")
    Path("/workspace/ee").mkdir(parents=True, exist_ok=True)
    with tarfile.open(b) as t:
        t.extractall("/workspace/ee")
    cfg = json.loads(Path("/workspace/ee/explainer_engine/training/pods/p15/p15.json").read_text())
    env = dict(os.environ, HF_HOME=str(hf_home), EE_OUT=str(out), PYTHONUNBUFFERED="1", XW_GPU_MODE=cfg["qwen"]["gpu_mode"],
               EE_DEADLINE=str(time.time() + TIMEOUT_S), P14_LOCAL_ROOTS=json.dumps([[cfg["hf_root"], str(out)]]), PYTHONPATH="/workspace/ee")
    stop = threading.Event()
    th = threading.Thread(target=_uploader, args=(out, stop), daemon=True)
    th.start()

    def _fire():
        (out / "beat_sa.txt").write_text("TIMEOUT: the in-container deadline fired\n")
        stop.set()
        th.join(timeout=40)
        os._exit(3)
    deadline_guard((SMOKE_TIMEOUT_S if smoke else TIMEOUT_S) - 60, _fire)
    base = ["python3", str(inp / "sa_test_qwen.py"), "--out", str(out), "--inputs", str(inp)] + (["--smoke"] if smoke else []) + (["--seeds", seeds] if seeds else [])
    rc = 0
    with open(out / "modal_sa.log", "a") as f:
        for extra in ([["--lora-weight", str(w)] for w in weights] or [[]]):
            rc = subprocess.run(base + extra, env=env, cwd="/workspace/ee", stdout=f, stderr=subprocess.STDOUT).returncode
            if rc != 0:
                break   # one attempt: the first failure stops the run (OR-37)
    names = list(json.loads((inp / "sa_prompts.json").read_text()))
    stems = [f"{n}_s{s}" for s in seeds.split(",") for n in names] if seeds else list(names)
    expected = ["qwen/smoke.json"] if smoke else [f"qwen/{s}{wtag(w)}.png" for w in weights for s in stems] or [f"qwen/{s}.png" for s in stems]
    v = verdict(out, expected)
    if rc != 0:
        v["state"] = "FAILED"
    (out / "beat_sa.txt").write_text(f"{v['state']} rc={rc} ok={v['n_ok']}/{v['n_expected']} seconds={int(time.time() - t0)}\n")
    stop.set()
    th.join(timeout=300)
    return {"rc": rc, "seconds": int(time.time() - t0)}


if modal is not None:
    app = modal.App("ee-sa-test")
    vol = modal.Volume.from_name("ee-weights", version=2)
    image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12")
             .apt_install("ffmpeg", "git")
             .run_commands(
                 'pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" '
                 '"git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" '
                 '"git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e"',
                 "git clone -q https://github.com/aigc-apps/VideoX-Fun.git /workspace/VideoX-Fun && "
                 "git -C /workspace/VideoX-Fun checkout -q e8c314fbfa494d0429bbef605c9f6112b79a7ead",
                 "pip install -q einops timm tomesd torchdiffeq torchsde omegaconf SentencePiece ftfy func_timeout 'imageio[ffmpeg]' "
                 "opencv-python-headless scikit-image beautifulsoup4 decord librosa albumentations kornia"))

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def sa_photos():
        return body(weights=WEIGHTS)   # 12 photos: 2 x (~60 s load + 6 x ~40 s) = ~10 min, inside the cost-derived timeout

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=SMOKE_TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def sa_smoke():
        return body(smoke=True)

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def sa_seeds():
        return body(seeds="12,13")   # 12 photos: 44 s load + 12 x ~40 s = ~9 min, inside the cost-derived timeout

    @app.local_entrypoint()
    def seeds():
        print("GO card", go_gate(), "timeout", TIMEOUT_S, "s", flush=True)
        print("result", sa_seeds.remote())

    @app.local_entrypoint()
    def smoke():
        print("GO card", go_gate(), "smoke timeout", SMOKE_TIMEOUT_S, "s", flush=True)
        print("result", sa_smoke.remote())

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
        print("result", sa_photos.remote())
