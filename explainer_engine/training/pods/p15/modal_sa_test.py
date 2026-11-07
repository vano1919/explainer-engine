"""6 test Qwen photos on Modal (OR-23 plan OR23_SA_TEST_6_QWEN_PHOTOS.md; the creator's yes cmsg_01Hnu5zB86sjUj5GtTgaUkPWKzpwThjB1xvJu5yyAbzP6j,
2026-11-07 13:16 UTC). One A100-80 function, hard timeout 25 min, retries 0. Run on the creator's PC:
    set EE_MODAL_GO=cmsg_01Hnu5zB86sjUj5GtTgaUkPWKzpwThjB1xvJu5yyAbzP6j   (PowerShell: $env:EE_MODAL_GO="...")
    modal run modal_sa_test.py
Inputs (6 stills, prompts, runner) come from HF vano1919/tmr-artifacts route_test_2026-11/sa_test/in/ held to the sha256 below; photos go to
.../sa_test/out/qwen/ as they are drawn (OR-33). Weights come from the Volume ee-weights; nothing is downloaded from outside."""
import hashlib, json, os, subprocess, tarfile, threading, time
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
IN = "route_test_2026-11/sa_test/in"
OUT = "route_test_2026-11/sa_test/out"
SHAS = {
 "sa_camp_block.png": "78a9470037b1095d5fe65acf03b44c170cecbada362a43de72ef044882836917",
 "sa_camp_cc0.png": "94bb50ff599d82139755935dcdd06a193a5c06ec0c1f87592ab6e4b70f7f01cd",
 "sa_cave_block.png": "39e7097bbd01191a536b93688514791ceba62920d1cd3bb39a628f5d7d7ef172",
 "sa_cave_cc0.png": "6d6f453107e52dc93abf654bcbc1712779e21f79cd5303ba79cce120c2b8edc1",
 "sa_ice_block.png": "543eb2f1ec7685da411a4325bfb7a0086b1ac4db0dd5cef294a3742e2365158d",
 "sa_ice_cc0.png": "8ca83e3d218d3089af415c605298453a4dd7acb75c9f03c01db7adb4f3eb8ab8",
 "sa_prompts.json": "ab9c2a1e15ad4de0c50a0aa7e098cc7ce3f48edea4ce2a16990cdc2b53f164f3",
 "sa_test_qwen.py": "e452d2c42ef7f11270be63399cbf8004e2d60e35d5c9b4695a860f4cb66cf16c"}
BUNDLE_SHA = "53eb909ef3a0c37a332dbb582bc62bdd194733eeba867eb7f5467a84679d0681"
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
SECRET_NAME = "huggingface-secret"
TIMEOUT_S = 25 * 60
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


def body():
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
    with open(out / "modal_sa.log", "a") as f:
        rc = subprocess.run(["python3", str(inp / "sa_test_qwen.py"), "--out", str(out), "--inputs", str(inp)], env=env,
                            cwd="/workspace/ee", stdout=f, stderr=subprocess.STDOUT).returncode
    (out / "beat_sa.txt").write_text(f"{'DONE' if rc == 0 else 'FAILED'} rc={rc} seconds={int(time.time() - t0)}\n")
    stop.set()
    th.join(timeout=300)
    return {"rc": rc, "seconds": int(time.time() - t0)}


if modal is not None:
    app = modal.App("ee-sa-test")
    vol = modal.Volume.from_name("ee-weights", version=2)
    image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12")
             .apt_install("git")
             .run_commands(
                 'pip install -q "huggingface_hub==1.33.0" "jsonschema==4.26.0" '
                 '"git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d" '
                 '"git+https://github.com/huggingface/peft@ebf159f74d80a0d406f7afa943ede73b3901c20e"'))

    @app.function(image=image, gpu="A100-80GB", cpu=2, memory=65536, timeout=TIMEOUT_S, retries=0, volumes={"/w": vol},
                  secrets=[modal.Secret.from_name(SECRET_NAME)])
    def sa_photos():
        return body()

    @app.local_entrypoint()
    def main():
        print("GO card", go_gate(), "timeout", TIMEOUT_S, "s", flush=True)
        print("result", sa_photos.remote())
