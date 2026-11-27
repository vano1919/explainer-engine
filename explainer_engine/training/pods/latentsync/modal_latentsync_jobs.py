"""LatentSync 1.5 lip-sync refinement on Modal: one rendered clip and its dialogue WAV in, the same clip with the mouth
re-synced out. Code only, never run. It takes the payload ``videolane/lipsync_pipeline.build_lipsync_refinement_command``
writes (schema ``lipsync_refinement_job/1``) and follows the contract of the LTX worker (``training/pods/ltx/modal_ltx_jobs.py``):
every model file pinned by revision and sha256 in ``launch.json``, the inputs fetched from the HF vault by path and refused
unless their sha256 is the pinned one (``stage_input``), every setting written out, each step's output saved to the Volume and
HF as soon as it exists and checked on HF by its sha256 (OR-33).

Money (the cloud rules, sections 3 and 4), in this order inside ``paid_run`` before ``.remote()``:
- ``preflight``: the launch is fully pinned and agrees with ``config/cloud_pins.json`` models.lipsync_latentsync, its price is the
  dated table's (``cloud/modal_schedule``), the creator's ``modal_latentsync`` line exists in ``config/spend_caps.json`` (missing =
  a zero budget, refused) and the job cap stays under 80 % of it, and the job passes ``job_problems``;
- ``owner_approval``: ``EE_MODAL_GO`` names the plan, and the owner's approval (``core/approvals.verify_approval``) is bound to
  this run's manifest sha256, mode and worst-case bill;
- ``claim_launch``: an open reservation of at least the worst-case bill for this item in the run's ledger (``core/ledger.Run``),
  and no earlier launch of it; then the launch mark, so a second launch of the same job is refused;
- after ``.remote()`` returned or raised: ``settle_launch`` (wall clock at the rate, an upper bound of the bill).
Inside the paid container ``container_gate`` checks the approval proof again (its HMAC, the manifest, the bill) before any
model loads. No repo import inside the container: the image holds only this file and the launch file.

What the LatentSync code needs that its CLI does not take as a flag (``scripts/inference.py`` at the pinned commit): the audio
encoder at ``checkpoints/whisper/tiny.pt``, the VAE ``stabilityai/sd-vae-ft-mse`` by name, and insightface's ``buffalo_l`` pack
under ``checkpoints/auxiliary``; ``link_checkpoints`` points each at its pinned copy on the Volume and the run is offline
(``HF_HUB_OFFLINE=1``), so nothing unpinned is fetched while the GPU bills."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
import re
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

try:
    import modal
except ImportError:
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
LAUNCH_PATH = Path(__file__).with_name("launch.json")
PINS_PATH = Path(__file__).resolve().parents[4] / "config" / "cloud_pins.json"
PINS_KEY = "lipsync_latentsync"
SECRET_NAME = "custom-secret"   # the same Modal secret as the LTX worker: HF_TOKEN, and the approval signing key
PROVIDER = "modal_modal1"
JOB_SCHEMA = "lipsync_refinement_job/1"
RECORD_SCHEMA = "latentsync_run_record/1"
BACKENDS = ("latentsync_1_5", "latentsync_1_6")
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
PINS = ("backend", "model_repo", "model_revision", "model_files", "uses", "vae", "face_detector", "latentsync_code", "module",
        "unet_config", "cli_flags", "settings_ranges", "hf_out", "scaledown_window_s", "base_image", "spend_line",
        "ledger_service", "operation_mode")
# Every flag of scripts/inference.py at the pinned commit (its argparse block); build_cmd writes no other.
VERIFIED_FLAGS = ("--unet_config_path", "--inference_ckpt_path", "--video_path", "--audio_path", "--video_out_path",
                  "--inference_steps", "--guidance_scale", "--temp_dir", "--seed", "--enable_deepcache")
SETTINGS = ("inference_steps", "guidance_scale", "seed")
INPUTS = ("video", "audio")
STEPS = ("inputs", "weights", "lipsync", "output")
MARGIN_S = 60               # the end path after the model: record, Volume copy, final upload, HF check
OUT_ROOT = Path("/workspace/out")
CODE_DIR = Path("/workspace/LatentSync")
VOL_OUT = "out_latentsync"
SAVE_BUDGET_S = 45


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def load_pins(path=PINS_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))["models"][PINS_KEY]


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def _sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def sha_json(d) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def launch_sha(launch: dict) -> str:
    return sha_json(launch)


def worker_sha() -> str:
    return _sha(__file__)


def git_blob_id(p) -> str:
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def run_id(plan_sha: str, launch: dict) -> str:
    if not (isinstance(plan_sha, str) and HEX64.match(plan_sha)):
        raise ValueError("a run id needs the approved plan's sha256")
    return f"{plan_sha[:12]}_{launch_sha(launch)[:12]}"


# --- the launch file -------------------------------------------------------------------------------------------------------

def launch_problems(launch: dict) -> list[str]:
    """Every pin the run needs (OR-22, OR-23), none left None: the model and its files by sha256, the VAE and the face detector
    the code loads by name, the code commit, the CLI flags read from the code, the image, the dated price and the cap."""
    out = [f"launch {k} is not pinned" for k in PINS if launch.get(k) in (None, "", {}, [])]
    if launch.get("backend") and launch["backend"] not in BACKENDS:
        out.append(f"launch backend {launch['backend']!r} is not one of {BACKENDS}")
    if launch.get("model_revision") and not HEX40.match(str(launch["model_revision"])):
        out.append("launch model_revision must be a full 40-hex commit of the model repo")
    files = launch.get("model_files") or {}
    out += [f"launch model file {f} has no sha256" for f, h in files.items() if not HEX64.match(str(h))]
    uses = launch.get("uses") if isinstance(launch.get("uses"), dict) else {}
    out += [f"launch uses.{k} is not one of the model files" for k in ("unet", "whisper") if uses.get(k) not in files]
    vae = launch.get("vae") if isinstance(launch.get("vae"), dict) else {}
    if vae and not (vae.get("repo") and HEX40.match(str(vae.get("revision") or "")) and vae.get("files")):
        out.append("launch vae needs its repo, a full 40-hex revision and its files")
    out += [f"launch vae file {f} has no sha256" for f, h in (vae.get("files") or {}).items() if not HEX64.match(str(h))]
    face = launch.get("face_detector") if isinstance(launch.get("face_detector"), dict) else {}
    if face and not (face.get("name") and face.get("url")):
        out.append("launch face_detector needs its name and url")
    if face and not HEX64.match(str(face.get("sha256") or "")):
        out.append(f"launch face_detector {face.get('name')} has no sha256: insightface would fetch an unpinned zip at run time")
    code = launch.get("latentsync_code") if isinstance(launch.get("latentsync_code"), dict) else {}
    if code and not (code.get("repo") and HEX40.match(str(code.get("commit") or ""))):
        out.append("launch latentsync_code needs the repo and a full 40-hex commit")
    if launch.get("cli_flags") and tuple(launch["cli_flags"]) != VERIFIED_FLAGS:
        out.append("launch cli_flags are not the flags of scripts/inference.py this worker was written against")
    rng = launch.get("settings_ranges") if isinstance(launch.get("settings_ranges"), dict) else {}
    out += [f"launch settings_ranges.{k} must be [low, high]" for k in ("inference_steps", "guidance_scale")
            if rng and not (isinstance(rng.get(k), list) and len(rng[k]) == 2 and rng[k][0] <= rng[k][1])]
    img = launch.get("base_image")
    if img and "@sha256:" not in str(img):
        out.append("launch base_image must be pinned by its registry digest (@sha256:)")
    sd = launch.get("scaledown_window_s")
    if sd is not None and not (isinstance(sd, int) and 2 <= sd <= 60):
        out.append("launch scaledown_window_s must be a short whole number of seconds (2..60): nothing stays warm")
    if not _num(launch.get("usd_per_h")) or not launch.get("prices_date"):
        out.append("launch usd_per_h / prices_date is not set")
    if not (_num(launch.get("min_vram_gb")) and _num(launch.get("gpu_vram_gb")) and launch["min_vram_gb"] <= launch["gpu_vram_gb"]):
        out.append("launch min_vram_gb / gpu_vram_gb are not set, or the card is smaller than the model needs")
    caps = launch.get("caps") or {}
    out += [f"launch caps.{k} is not set" for k in ("run_usd", "cold_start_s") if not _num(caps.get(k))]
    st = launch.get("startup_timeout_s")
    if not (isinstance(st, int) and 30 <= st <= caps.get("cold_start_s", 0)):
        out.append("launch startup_timeout_s must be set and no longer than caps.cold_start_s (a hung start bills it)")
    return out


def pins_problems(launch: dict, pins: dict | None = None) -> list[str]:
    """The launch and ``config/cloud_pins.json`` models.lipsync_latentsync name the same model, revision, files and code commit
    (CR-18: the pins file is where a pin lives; the launch may not drift from it)."""
    try:
        p = load_pins() if pins is None else pins
    except (OSError, KeyError, ValueError):
        return [f"config/cloud_pins.json models.{PINS_KEY} cannot be read"]
    out = []
    if p.get("id") != launch.get("model_repo"):
        out.append(f"cloud_pins id {p.get('id')} is not the launch model_repo {launch.get('model_repo')}")
    if p.get("revision") != launch.get("model_revision"):
        out.append("cloud_pins revision is not the launch model_revision")
    if (p.get("sha256_files") or {}) != (launch.get("model_files") or {}):
        out.append("cloud_pins sha256_files are not the launch model_files")
    unet = (launch.get("uses") or {}).get("unet")
    if p.get("sha256") != (launch.get("model_files") or {}).get(unet):
        out.append("cloud_pins sha256 is not the launch unet file's")
    if (p.get("code") or {}).get("commit") != (launch.get("latentsync_code") or {}).get("commit"):
        out.append("cloud_pins code commit is not the launch latentsync_code commit")
    return out


def usd_per_h(launch: dict) -> float:
    return float(launch["usd_per_h"])


def schedule_rate(launch: dict) -> float:
    """GPU + CPU + memory per hour from ``cloud/modal_schedule`` (the dated table), for the worker's own size (local side)."""
    from explainer_engine.cloud import modal_schedule as MS
    per_s = MS.GPUS[launch["gpu"]]["usd_s"] + launch["cpu"] * MS.CPU_CORE_S + launch["memory_gib"] * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def cost_timeout(cap_usd, usd_h, cold_start_s) -> int:
    """OR-37: the function timeout comes from the cap: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600) / usd_h * 3600)


def check_timeout(timeout_s, cap_usd, usd_h, cold_start_s) -> int:
    if timeout_s <= MARGIN_S or (timeout_s + cold_start_s) * usd_h / 3600 > cap_usd:
        raise ValueError(f"timeout {timeout_s}s does not fit the cap ${cap_usd} (or leaves no room for the end path)")
    return timeout_s


def timeout(launch: dict) -> int | None:
    """The run timeout from the cap, or None while the launch is not pinned (then no GPU function is defined)."""
    if launch_problems(launch):
        return None
    c, h = launch["caps"], usd_per_h(launch)
    return check_timeout(cost_timeout(c["run_usd"], h, c["cold_start_s"]), c["run_usd"], h, c["cold_start_s"])


def hard_bill_usd(launch: dict, timeout_s: float | None = None) -> float:
    """The most one launch can bill: the function's hard timeout plus the cold start, at the card's rate."""
    t = timeout(launch) if timeout_s is None else timeout_s
    if t is None:
        raise SystemExit("the launch file is not pinned: no bill can be bounded; nothing was started")
    return round((float(t) + float(launch["caps"]["cold_start_s"])) * usd_per_h(launch) / 3600.0, 4)


# --- the job ---------------------------------------------------------------------------------------------------------------

def cmd_flags(cmd) -> dict:
    """``--flag value`` pairs of a payload's command (a flag with no value, like ``--enable_deepcache``, maps to True)."""
    out, cmd = {}, [str(c) for c in (cmd or [])]
    for k, c in enumerate(cmd):
        if c.startswith("--"):
            nxt = cmd[k + 1] if k + 1 < len(cmd) else None
            out[c] = True if nxt is None or nxt.startswith("--") else nxt
    return out


def make_job(launch: dict, payload: dict, *, shot_id: str, inputs: dict, settings: dict, plan_sha256: str,
             ledger_path: str) -> dict:
    """The worker's job: the pipeline's payload as written, plus what the worker needs and the payload does not hold: the
    inputs by HF path and sha256 (never a local path), the settings written out, the run keys and the ledger line."""
    rid = run_id(plan_sha256, launch)
    return dict(payload, shot_id=shot_id, inputs={k: dict(v) for k, v in inputs.items()}, settings=dict(settings),
                plan_sha256=plan_sha256, run_id=rid, launch_sha=launch_sha(launch),
                ledger={"path": str(ledger_path), "service": launch["ledger_service"], "item": f"{rid}/{shot_id}"})


def out_name(job: dict) -> str:
    return Path(str(job.get("out_mp4") or "")).name


def job_problems(launch: dict, job: dict) -> list[str]:
    """Free checks of one job before any paid call: the schema and the backend this launch pins, every input referenced by an
    HF path and a 64-hex sha256, every setting written out and inside the README's ranges, the payload's own command using only
    the verified flags and the same settings, the run keys bound to this launch file and a ledger line."""
    sid = job.get("shot_id") or "<no shot_id>"
    out = []
    if job.get("schema") != JOB_SCHEMA:
        out.append(f"{sid}: schema {job.get('schema')!r} is not {JOB_SCHEMA}")
    if job.get("backend") != launch.get("backend"):
        known = job.get("backend") in BACKENDS
        out.append(f"{sid}: backend {job.get('backend')!r} is " + (f"not the one this launch pins ({launch.get('backend')}, "
                   f"{launch.get('model_repo')})" if known else f"not a LatentSync backend {BACKENDS}"))
    if not job.get("shot_id"):
        out.append("the job has no shot_id")
    vram = job.get("min_vram_gb")
    if not _num(vram) or (_num(launch.get("gpu_vram_gb")) and vram > launch["gpu_vram_gb"]):
        out.append(f"{sid}: min_vram_gb {vram!r} is missing or above the card's {launch.get('gpu_vram_gb')} GB")
    inputs = job.get("inputs") if isinstance(job.get("inputs"), dict) else {}
    for k in INPUTS:
        spec = inputs.get(k) if isinstance(inputs.get(k), dict) else {}
        hp = str(spec.get("hf_path") or "")
        if not hp or hp.startswith("/") or ".." in Path(hp).parts:
            out.append(f"{sid}: input {k} has no HF path in the vault (a local path is never read by the worker)")
        if not HEX64.match(str(spec.get("sha256") or "")):
            out.append(f"{sid}: input {k} is not pinned by a 64-hex sha256")
    st = job.get("settings") if isinstance(job.get("settings"), dict) else {}
    rng = launch.get("settings_ranges") or {}
    for k in SETTINGS:
        if k not in st:
            out.append(f"{sid}: setting {k} is not written out")
    steps, gs, seed = st.get("inference_steps"), st.get("guidance_scale"), st.get("seed")
    s_lo, s_hi = rng.get("inference_steps") or [1, 1000]
    g_lo, g_hi = rng.get("guidance_scale") or [0.0, 100.0]
    if "inference_steps" in st and not (isinstance(steps, int) and not isinstance(steps, bool) and s_lo <= steps <= s_hi):
        out.append(f"{sid}: inference_steps {steps!r} is not a whole number in [{s_lo}, {s_hi}]")
    if "guidance_scale" in st and not (_num(gs) and g_lo <= gs <= g_hi):
        out.append(f"{sid}: guidance_scale {gs!r} is not in [{g_lo}, {g_hi}]")
    if "seed" in st and not (isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0):
        out.append(f"{sid}: seed {seed!r} must be a whole number >= 0 (-1 is a random seed: not reproducible)")
    if "enable_deepcache" in st and not isinstance(st["enable_deepcache"], bool):
        out.append(f"{sid}: enable_deepcache must be true or false")
    flags = cmd_flags(job.get("cmd"))
    out += [f"{sid}: the payload's command uses {f}, not a flag of scripts/inference.py" for f in flags if f not in VERIFIED_FLAGS]
    for flag, key, cast in (("--inference_steps", "inference_steps", int), ("--guidance_scale", "guidance_scale", float),
                            ("--seed", "seed", int)):
        if flag in flags and key in st:
            try:
                same = cast(flags[flag]) == st[key]
            except (TypeError, ValueError):
                same = False
            if not same:
                out.append(f"{sid}: the payload's command says {flag} {flags[flag]}, the settings say {st[key]}")
    if "--unet_config_path" in flags and flags["--unet_config_path"] != launch.get("unet_config"):
        out.append(f"{sid}: the payload asks {flags['--unet_config_path']}, the launch pins {launch.get('unet_config')}")
    if not out_name(job).endswith(".mp4"):
        out.append(f"{sid}: out_mp4 {job.get('out_mp4')!r} must end in a .mp4 file name")
    plan = job.get("plan_sha256")
    if not (isinstance(plan, str) and HEX64.match(plan)):
        out.append(f"{sid}: no plan_sha256 (the approved plan's sha256)")
    elif job.get("launch_sha") != launch_sha(launch) or job.get("run_id") != run_id(plan, launch):
        out.append(f"{sid}: the job was written for another launch file (launch_sha / run_id)")
    led = job.get("ledger") if isinstance(job.get("ledger"), dict) else {}
    if not (led.get("path") and led.get("service") == launch.get("ledger_service") and led.get("item")):
        out.append(f"{sid}: the job names no {launch.get('ledger_service')} ledger line (path, service, item) (D-56)")
    return out


# --- weights and paths (pinned files only) ---------------------------------------------------------------------------------

def weights_root(launch: dict, vol_root=None) -> Path:
    return Path(vol_root or "/w") / "model" / launch["model_repo"]


def hf_cache(vol_root=None) -> Path:
    return Path(vol_root or "/w") / "hf_cache"


def vae_snapshot(launch: dict, vol_root=None) -> Path:
    v = launch["vae"]
    return hf_cache(vol_root) / f"models--{v['repo'].replace('/', '--')}" / "snapshots" / v["revision"]


def face_root(vol_root=None) -> Path:
    """insightface's ``root``: ``<root>/models/<name>`` is the unpacked pack, ``<root>/<name>.zip`` the pinned zip."""
    return Path(vol_root or "/w") / "aux" / "insightface"


def needed_files(launch: dict, vol_root=None) -> dict:
    """{path on the Volume: sha256} of every file the run reads: the model files, the VAE snapshot, the face-detector zip."""
    root = weights_root(launch, vol_root)
    out = {root / f: h for f, h in launch["model_files"].items()}
    out.update({vae_snapshot(launch, vol_root) / f: h for f, h in launch["vae"]["files"].items()})
    face = launch["face_detector"]
    out[face_root(vol_root) / f"{face['name']}.zip"] = face.get("sha256") or ""
    return out


def check_weights(launch: dict, vol_root=None) -> list[str]:
    """Every file the run reads, on the Volume with its pinned sha256 (the paid function never downloads)."""
    bad = []
    for p, want in needed_files(launch, vol_root).items():
        if not p.is_file():
            bad.append(f"missing {p}")
        elif not want or _sha(p) != want:
            bad.append(f"sha256 mismatch {p}")
    return bad


def sizes_ok(launch: dict, vol_root=None) -> list[str]:
    """The paid function's cheap check: every file there and not empty (its sha256 was proved when it was staged)."""
    return [f"missing {p}" for p in needed_files(launch, vol_root) if not p.is_file() or p.stat().st_size == 0]


def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def _hf_download(repo, revision, files, local_dir=None, cache_dir=None):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), token=_tok(),
                      **({"local_dir": str(local_dir)} if local_dir else {"cache_dir": str(cache_dir)}))


def _url_download(url, dest):
    import urllib.request
    with urllib.request.urlopen(url, timeout=600) as r, open(dest, "wb") as f:  # the pinned release url
        shutil.copyfileobj(r, f)


def stage_weights(launch: dict, vol_root=None, download=None, fetch=None) -> list[str]:
    """CPU only, before any GPU: the model files and the VAE at their pinned revisions, the face-detector zip from its url, each
    then checked by sha256. Refused while a file has no pinned sha256 (nothing unpinned is ever put on the Volume)."""
    bad = launch_problems(launch)
    if bad:
        return bad
    root, dl = weights_root(launch, vol_root), download or _hf_download
    missing = [f for f in launch["model_files"] if not (root / f).is_file()]
    if missing:
        dl(launch["model_repo"], launch["model_revision"], missing, local_dir=root)
    v = launch["vae"]
    if any(not (vae_snapshot(launch, vol_root) / f).is_file() for f in v["files"]):
        dl(v["repo"], v["revision"], list(v["files"]), cache_dir=hf_cache(vol_root))
    face = launch["face_detector"]
    z = face_root(vol_root) / f"{face['name']}.zip"
    if not z.is_file():
        z.parent.mkdir(parents=True, exist_ok=True)
        (fetch or _url_download)(face["url"], z)
    bad = check_weights(launch, vol_root)
    if not bad:
        import zipfile
        with zipfile.ZipFile(z) as zf:
            zf.extractall(face_root(vol_root) / "models" / face["name"])
    return bad


def link_checkpoints(launch: dict, vol_root=None, code_dir=CODE_DIR) -> list[str]:
    """Point the paths the LatentSync code opens by name at the pinned copies: ``checkpoints/whisper/tiny.pt``, insightface's
    ``checkpoints/auxiliary/models/<name>``, and the VAE's ``refs/main`` in the offline HF cache = the pinned revision."""
    code_dir = Path(code_dir)
    face = launch["face_detector"]
    links = {code_dir / launch["whisper_link"]: weights_root(launch, vol_root) / launch["uses"]["whisper"],
             code_dir / "checkpoints" / "auxiliary" / "models" / face["name"]: face_root(vol_root) / "models" / face["name"]}
    bad = [f"missing {src}" for src in links.values() if not src.exists()]
    if bad:
        return bad
    for dst, src in links.items():
        dst.parent.mkdir(parents=True, exist_ok=True)
        if dst.is_symlink() or dst.exists():
            if dst.resolve() == src.resolve():
                continue
            return [f"{dst} exists and is not the pinned {src}"]
        dst.symlink_to(src)
    ref = vae_snapshot(launch, vol_root).parents[1] / "refs" / "main"
    ref.parent.mkdir(parents=True, exist_ok=True)
    ref.write_text(launch["vae"]["revision"])
    return []


def run_env(launch: dict, vol_root=None) -> dict:
    """The CLI's environment: offline, the HF cache on the Volume (the VAE resolves to the pinned revision through refs/main)."""
    return {"HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1", "HF_HUB_CACHE": str(hf_cache(vol_root)),
            "PYTHONUNBUFFERED": "1"}


def build_cmd(launch: dict, job: dict, video, audio, out_mp4, *, vol_root=None, code_dir=CODE_DIR, temp_dir=None,
              python=None) -> list[str]:
    """The LatentSync CLI of one job, from pinned paths only: the code's own config at the pinned commit, the UNet file on the
    Volume, the staged inputs, and the written-out settings; every flag is one of ``VERIFIED_FLAGS``. Run from ``code_dir``
    (``scripts/inference.py`` reads ``configs/`` and the mask relative to it, as ``inference.sh`` does)."""
    st, code_dir = job["settings"], Path(code_dir)
    cmd = [python or sys.executable, "-m", launch["module"],
           "--unet_config_path", str(code_dir / launch["unet_config"]),
           "--inference_ckpt_path", str(weights_root(launch, vol_root) / launch["uses"]["unet"]),
           "--video_path", str(video), "--audio_path", str(audio), "--video_out_path", str(out_mp4),
           "--inference_steps", str(int(st["inference_steps"])), "--guidance_scale", repr(float(st["guidance_scale"])),
           "--temp_dir", str(temp_dir or "/tmp/latentsync_temp"), "--seed", str(int(st["seed"]))]
    if st.get("enable_deepcache"):
        cmd.append("--enable_deepcache")
    return cmd


def stage_input(spec: dict, dest: Path, repo=HF_REPO, download=None) -> Path:
    """An input clip or WAV: fetched from the HF vault by its path and refused unless its sha256 is the pinned one."""
    dest = Path(dest)
    if not dest.is_file():
        dest.parent.mkdir(parents=True, exist_ok=True)
        if download is not None:
            download(repo, spec["hf_path"], dest)
        else:
            from huggingface_hub import hf_hub_download
            shutil.copyfile(hf_hub_download(repo_id=repo, repo_type="dataset", filename=spec["hf_path"], token=_tok()), dest)
    if _sha(dest) != spec["sha256"]:
        raise RuntimeError(f"{spec['hf_path']}: sha256 is not the pinned one; nothing was run")
    return dest


def run_record(launch: dict, job: dict) -> dict:
    """Every setting and pin of the run, written before the model runs and updated after each step (what an audit reads;
    never reconstructed from a command line)."""
    face, v = launch["face_detector"], launch["vae"]
    return {"schema": RECORD_SCHEMA, "shot_id": job["shot_id"], "run_id": job["run_id"], "plan_sha256": job["plan_sha256"],
            "backend": job["backend"], "launch_sha": launch_sha(launch), "worker_sha": job.get("worker_sha"),
            "code": dict(launch["latentsync_code"]), "module": launch["module"], "unet_config": launch["unet_config"],
            "model": {"repo": launch["model_repo"], "revision": launch["model_revision"], "files": dict(launch["model_files"])},
            "vae": {"repo": v["repo"], "revision": v["revision"], "files": dict(v["files"])},
            "face_detector": {"name": face["name"], "url": face["url"], "sha256": face.get("sha256")},
            "settings": dict(job["settings"]), "gpu": launch["gpu"], "inputs": {k: dict(job["inputs"][k]) for k in INPUTS},
            "outputs": {}, "steps": [], "cmd": None, "argv_sha256": None, "state": "RUNNING", "error": None}


# --- in the container ------------------------------------------------------------------------------------------------------

class DeadlineHit(RuntimeError):
    """The in-container deadline: raised inside the work so the normal end path writes, copies and uploads."""


class Deadline:
    def __init__(self, timeout_s, margin_s=MARGIN_S, now=time.time):
        self.now, self.end = now, now() + float(timeout_s) - float(margin_s)

    def left(self) -> float:
        return self.end - self.now()

    def check(self):
        if self.left() <= 0:
            raise DeadlineHit("the in-container deadline came; the job ends cleanly with what it has")


def _files(root):
    out = []
    for p in sorted(Path(root).rglob("*")):
        try:
            if p.is_file() and not p.name.startswith(".") and not p.name.endswith(".tmp"):
                st = p.stat()
                if st.st_size > 0:
                    out.append((p, (st.st_size, st.st_mtime_ns)))
        except OSError:
            continue
    return out


def upload_round(api, root, prefix, seen: dict, final=False, sleep=time.sleep, op=None, budget_s=None) -> int:
    """One batched commit of every new or changed file; bounded backoff (no sleep past ``budget_s``)."""
    new = [(p, k) for p, k in _files(root) if seen.get(str(p)) != k]
    if not new:
        return 0
    if op is None:
        from huggingface_hub import CommitOperationAdd as op
    ops = [op(path_in_repo=f"{prefix}/{p.relative_to(root).as_posix()}", path_or_fileobj=str(p)) for p, _ in new]
    tries, slept = (5 if final else 2), 0.0
    for k in range(tries):
        try:
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops,
                              commit_message=f"latentsync: {len(new)} files")
            seen.update({str(p): key for p, key in new})
            return len(new)
        except Exception as e:  # retried with backoff; the Volume copy is the safety net
            print("upload failed", repr(e)[:160], flush=True)
            wait = 10.0 * 2 ** k
            if k == tries - 1 or (budget_s is not None and slept + wait > budget_s):
                return 0
            sleep(wait)
            slept += wait
    return 0


def verify_uploads(api, root, prefix) -> dict:
    """Each local file against HF: an LFS file by its sha256, a small one by its git blob id."""
    files = [p for p, _ in _files(root)]
    paths = [f"{prefix}/{p.relative_to(root).as_posix()}" for p in files]
    try:
        info = {i.path: i for i in api.get_paths_info(HF_REPO, paths, repo_type="dataset", expand=True)}
    except Exception as e:
        return {p.name: f"not checked: {type(e).__name__}" for p in files}
    out = {}
    for p, hp in zip(files, paths, strict=True):
        i = info.get(hp)
        if i is None:
            out[p.name] = "missing on HF"
            continue
        lfs = getattr(i, "lfs", None)
        want = (lfs.sha256 if hasattr(lfs, "sha256") else (lfs or {}).get("sha256")) if lfs else None
        ok = (want == _sha(p)) if want else (getattr(i, "blob_id", None) == git_blob_id(p))
        out[p.name] = "ok" if ok else "hash differs on HF"
    return out


def attempt_guard(vol_out: Path, job: dict) -> str | None:
    """The first act of the GPU function: a marker per launch nonce on the Volume; a rescheduled input finds it and returns."""
    d = Path(vol_out) / job["run_id"] / job["shot_id"]
    d.mkdir(parents=True, exist_ok=True)
    m = d / f"attempt_{job['nonce']}"
    if m.exists():
        return "REFUSED_SECOND_ATTEMPT"
    m.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return None


def body(job: dict, launch: dict, timeout_s: int, *, vol_root="/w", code_dir=CODE_DIR, commit=lambda: None, api=None,
         sh=subprocess.run, now=time.time, out_root=OUT_ROOT, download=None, python=None, op=None) -> dict:
    """The GPU function: attempt marker, then the steps inputs -> weights -> lipsync -> output; after each step the run record
    is written, copied to the Volume and sent to HF, the output mp4 with its sha256 as soon as it exists (OR-33); at the end
    every upload is checked on HF and the check is kept on the Volume."""
    t_in = now()
    vol_out = Path(vol_root) / VOL_OUT
    seen = attempt_guard(vol_out, job)
    if seen:
        return {"state": seen, "shot_id": job["shot_id"], "run_id": job["run_id"]}
    commit()
    deadline = Deadline(timeout_s, now=now)
    out = Path(out_root) / job["run_id"] / job["shot_id"]
    out.mkdir(parents=True, exist_ok=True)
    tmp = Path(out_root) / ".in" / job["run_id"] / job["shot_id"]
    prefix = f"{launch['hf_out']}/{job['run_id']}/{job['shot_id']}"
    rec_path = out / f"{job['shot_id']}.run_record.json"
    sent: dict = {}
    rec = run_record(launch, job)

    def to_volume():
        try:
            shutil.copytree(out, vol_out / job["run_id"] / job["shot_id"], dirs_exist_ok=True)
            commit()
        except Exception as e:
            print("volume copy failed", repr(e)[:200], flush=True)

    def save_now(step: str, ok: bool, final=False, **info):
        rec["steps"].append(dict(info, step=step, ok=ok, at=round(now() - t_in, 1)))
        rec_path.write_text(json.dumps(rec, indent=1, default=str))
        to_volume()                                  # the Volume first, then HF
        if api is not None:
            budget = max(0.0, deadline.left() + MARGIN_S - 15) if final else min(SAVE_BUDGET_S, max(0.0, deadline.left()))
            upload_round(api, out, prefix, sent, final=final, budget_s=budget, op=op)

    try:
        staged = {}
        for k in INPUTS:
            spec = job["inputs"][k]
            staged[k] = stage_input(spec, tmp / Path(spec["hf_path"]).name, download=download)
        save_now("inputs", True, sha256={k: _sha(p) for k, p in staged.items()})
        deadline.check()
        bad = sizes_ok(launch, vol_root) or link_checkpoints(launch, vol_root, code_dir)
        save_now("weights", not bad, problems=bad)
        if bad:
            raise RuntimeError("weights not on the Volume: " + "; ".join(bad[:5]))
        deadline.check()
        mp4 = out / out_name(job)
        cmd = build_cmd(launch, job, staged["video"], staged["audio"], mp4, vol_root=vol_root, code_dir=code_dir,
                        temp_dir=tmp / "temp", python=python)
        rec.update(cmd=cmd, argv_sha256=hashlib.sha256("\0".join(cmd).encode()).hexdigest())
        t0 = now()
        try:
            r = sh(cmd, cwd=str(code_dir), env=dict(os.environ, **run_env(launch, vol_root)), capture_output=True,
                   text=True, timeout=max(1.0, deadline.left()), check=False)
            rc, tail = r.returncode, ((r.stdout or "") + (r.stderr or ""))[-2000:]
        except subprocess.TimeoutExpired:
            rc, tail = None, "the CLI ran past the in-container deadline"
        gen_s = round(now() - t0, 1)
        (out / f"{job['shot_id']}.lipsync.log").write_text(tail or "")
        made = mp4.is_file() and mp4.stat().st_size > 0
        save_now("lipsync", rc == 0 and made, rc=rc, gen_s=gen_s)
        if not (rc == 0 and made):
            raise RuntimeError(f"LatentSync made no clip (rc {rc}): {(tail or '')[-300:]}")
        rec["outputs"][mp4.name] = {"sha256": _sha(mp4), "bytes": mp4.stat().st_size,
                                    "hf_path": f"{prefix}/{mp4.name}"}
        rec["state"] = "DONE"
        save_now("output", True, file=mp4.name, sha256=rec["outputs"][mp4.name]["sha256"])
    except Exception as e:  # one attempt: the failure is written, copied and returned
        rec.update(state="FAILED", error=f"{type(e).__name__}: {str(e)[:300]}")
    rec["body_s"] = round(now() - t_in, 1)
    save_now("end", rec["state"] == "DONE", final=True)
    if api is not None:
        rec["verified"] = verify_uploads(api, out, prefix)
        if rec["state"] == "DONE" and any(v != "ok" for v in rec["verified"].values()):
            rec["state"] = "UPLOAD_UNVERIFIED"
        (out / f"{job['shot_id']}.verified.json").write_text(json.dumps(rec["verified"]))
        rec_path.write_text(json.dumps(rec, indent=1, default=str))
        to_volume()
    return json.loads(json.dumps(rec, default=str))   # plain JSON only, never a library object


def _hmac_ok(proof: dict, key: str) -> bool:
    """The signature ``core/approvals.compute_approval_hmac`` writes, recomputed here (no repo import in the container)."""
    canonical = {k: proof.get(k) for k in ("approval_id", "provider", "operation_mode", "manifest_sha256", "expires_at",
                                           "owner_evidence", "operation_id")}
    canonical["max_usd"] = round(float(proof.get("max_usd") or 0.0), 6)
    msg = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    want = hmac.new(key.encode("utf-8"), msg, hashlib.sha256).hexdigest()
    return hmac.compare_digest(str(proof.get("approval_hmac") or ""), want)


def container_gate(job: dict, launch: dict, env=os.environ, baked=Path("/root/launch.json")) -> list[str]:
    """Inside the paid container before any model loads (a ``.remote()`` from other code skips ``paid_run``): the launch is the
    one baked into the image, and the approval proof is signed with the owner's key and binds this job's manifest, the main
    mode and at least the worst-case bill, and has not expired. No key in the secret = refused."""
    import datetime as dt
    bad = []
    baked = Path(baked)
    if baked.exists() and json.loads(baked.read_text(encoding="utf-8")) != launch:
        bad.append("the launch passed in is not the launch file baked into the image")
    p = job.get("approval_proof") if isinstance(job.get("approval_proof"), dict) else None
    if p is None:
        return bad + ["no approval proof in the job"]
    key = str(env.get("OWNER_APPROVAL_SIGNING_KEY") or env.get("EE_APPROVAL_HMAC_KEY") or "")
    if len(key) < 16 or not _hmac_ok(p, key):
        bad.append("the approval proof is not signed with the owner's key")
    if p.get("provider") != PROVIDER or p.get("operation_mode") != launch["operation_mode"]:
        bad.append("the approval proof is for another provider or mode")
    if p.get("manifest_sha256") != manifest_sha(launch, job):
        bad.append("the approval proof binds another manifest than this job's")
    try:
        if float(p.get("max_usd") or 0) + 1e-9 < hard_bill_usd(launch):
            bad.append("the approval's max_usd is below the worst-case bill")
        exp = dt.datetime.fromisoformat(str(p.get("expires_at")))
        if (exp if exp.tzinfo else exp.replace(tzinfo=dt.UTC)) <= dt.datetime.now(dt.UTC):
            bad.append("the approval has expired")
    except (TypeError, ValueError, SystemExit) as exc:
        bad.append(f"the approval proof cannot be read: {exc}")
    return bad


# --- local side: the money path --------------------------------------------------------------------------------------------

def spend_line_problems(launch: dict) -> list[str]:
    """The creator's line for this worker in ``config/spend_caps.json`` (``launch.spend_line``, ``per_run_usd``): missing or not a
    positive number = a zero approved budget, refused (cloud rules section 4); the job cap stays under 80 % of it."""
    from explainer_engine.core import spend_caps
    name = launch.get("spend_line") or "<no spend_line>"
    line = spend_caps.load().get(name)
    v = line.get("per_run_usd") if isinstance(line, dict) else None
    if not _num(v):
        return [f"no {name} per_run_usd in config/spend_caps.json: the LatentSync worker spends nothing until the creator sets "
                "the line (zero approved budget)"]
    stop = 0.8 * float(v)   # core/ledger STOP_FRACTION
    cap = (launch.get("caps") or {}).get("run_usd") or 0
    return [f"launch caps.run_usd ${cap:g} is above 80 % of the creator's ${v:g} per run (${stop:g})"] if cap > stop + 1e-9 else []


def preflight(launch: dict, job: dict) -> None:
    """Free, before any paid call; raises SystemExit with every problem at once."""
    bad = launch_problems(launch) + pins_problems(launch)
    if not bad and abs(schedule_rate(launch) - usd_per_h(launch)) > 0.01 * schedule_rate(launch):
        bad.append(f"launch usd_per_h {usd_per_h(launch)} is not the price table's {schedule_rate(launch)} (cloud/modal_schedule)")
    bad += spend_line_problems(launch)
    bad += job_problems(launch, job)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def manifest(launch: dict, job: dict) -> dict:
    """What the owner approves: this launch file and worker, the backend, the inputs by sha256, every setting, the output name,
    the run keys and the ledger line. The container recomputes it from the same job."""
    return {"schema": "latentsync_manifest/1", "operation_mode": launch["operation_mode"], "launch_sha": launch_sha(launch),
            "worker_sha": worker_sha(), "backend": job.get("backend"), "shot_id": job.get("shot_id"),
            "inputs": {k: {"hf_path": (job.get("inputs") or {}).get(k, {}).get("hf_path"),
                           "sha256": (job.get("inputs") or {}).get(k, {}).get("sha256")} for k in INPUTS},
            "settings": dict(job.get("settings") or {}), "out_mp4": out_name(job), "run_id": job.get("run_id"),
            "plan_sha256": job.get("plan_sha256"), "ledger_item": (job.get("ledger") or {}).get("item")}


def manifest_sha(launch: dict, job: dict) -> str:
    m = manifest(launch, job)
    return hashlib.sha256(json.dumps(m, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()


def go_gate(env=os.environ, plan_sha: str | None = None) -> str:
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of the plan he said yes to>`` (the LTX worker's go_gate)."""
    m = GO.match(env.get("EE_MODAL_GO", ""))
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the card id of the creator's yes>:<the plan's sha256[:12]>' (OR-23); "
                         "nothing was started")
    if not plan_sha or m.group(2) != plan_sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than this job's (OR-23); nothing was started")
    return m.group(1)


def owner_approval(launch: dict, job: dict, env=os.environ, registry_path: Path | None = None) -> dict:
    """The owner's approval of exactly this run (``core/approvals.verify_approval``): the card of EE_MODAL_GO, provider, mode,
    this job's manifest sha256 and the worst-case bill; signed for the container when the signing key is set."""
    from explainer_engine.core import approvals
    card = go_gate(env, job.get("plan_sha256"))
    try:
        rec = approvals.verify_approval(card, provider=PROVIDER, operation_mode=launch["operation_mode"],
                                        manifest_sha256=manifest_sha(launch, job), requested_usd=hard_bill_usd(launch),
                                        registry_path=registry_path)
    except approvals.ApprovalError as exc:
        raise SystemExit(f"owner approval verification failed: {exc}; nothing was started") from None
    op_id = f"op_{uuid.uuid4().hex}"
    key = str(env.get("OWNER_APPROVAL_SIGNING_KEY") or env.get("EE_APPROVAL_HMAC_KEY") or "").strip()
    return approvals.sign_approval_proof(rec, signing_key=key, operation_id=op_id) if key else dict(rec, operation_id=op_id)


def _ledger(job: dict):
    from explainer_engine.core.ledger import Run
    led = job.get("ledger") or {}
    if not (led.get("path") and led.get("service") and led.get("item")):
        raise SystemExit(f"{job.get('shot_id')}: the job names no ledger (path, service, item); nothing was started (D-56)")
    return Run.open(led["path"]), led


def claim_launch(job: dict, need_usd: float, now=time.time) -> None:
    """Before ``.remote()``: this job's reservation is in the ledger, open, of this service and at least the worst-case bill, and
    no launch of it is marked; then the launch mark is written, so a second launch of the same job is refused."""
    run, led = _ledger(job)
    r = run.data.get("reserved", {}).get(led["item"])
    if not r or r.get("settled") or r.get("service") != led["service"]:
        raise SystemExit(f"{led['item']}: no open {led['service']} reservation in {led['path']}; reserve first; nothing was "
                         "started")
    if float(r.get("amount") or 0) + 1e-9 < need_usd:
        raise SystemExit(f"{led['item']}: the reservation ${r.get('amount')} is below the worst-case bill ${need_usd}; nothing "
                         "was started")
    if led["item"] in run.data.get("items", {}).get("launch", {}):
        raise SystemExit(f"{led['item']}: this job was launched already; a repeat would pay twice; nothing was started")
    run.done("launch", led["item"], at=round(now(), 1), reserved_usd=r["amount"])


def settle_launch(job: dict, wall_s: float, launch: dict) -> float:
    """After ``.remote()`` returned or raised: the launch's own wall clock at the rate, an upper bound of the bill."""
    run, led = _ledger(job)
    usd = round(max(0.0, float(wall_s)) * usd_per_h(launch) / 3600.0, 4)
    run.settle(led["service"], led["item"], usd)
    return usd


def paid_run(launch: dict, job: dict, *, remote, env=os.environ, registry_path: Path | None = None, now=time.time) -> dict:
    """The only path to the GPU: preflight, the owner's approval, the ledger claim, then ``remote(job, launch)``, then the
    settlement whatever happened. Nothing is called when any gate refuses."""
    preflight(launch, job)
    proof = owner_approval(launch, job, env, registry_path)
    claim_launch(job, hard_bill_usd(launch), now=now)
    t0, res = now(), None
    try:
        res = remote(dict(job, worker_sha=worker_sha(), nonce=uuid.uuid4().hex[:12], approval_proof=proof), launch)
    finally:
        print("settled", settle_launch(job, now() - t0, launch), "USD", flush=True)
    return res


LAUNCH = load_launch()
TIMEOUT = timeout(LAUNCH)

if modal is not None and TIMEOUT:   # no Modal object exists while the launch has an open pin (no image, no function)
    app = modal.App(LAUNCH["app_name"])
    vol = modal.Volume.from_name("ee-weights", version=2)
    _code = LAUNCH["latentsync_code"]
    image = (modal.Image.from_registry(LAUNCH["base_image"])
             .apt_install("ffmpeg", "git", "libgl1")
             .run_commands(f"git clone -q {_code['repo']} {CODE_DIR} && git -C {CODE_DIR} checkout -q {_code['commit']} && "
                           f"pip install -q -r {CODE_DIR}/requirements.txt")
             .add_local_file(str(LAUNCH_PATH), "/root/launch.json"))
    secrets = [modal.Secret.from_name(SECRET_NAME)]

    @app.function(image=image, gpu=LAUNCH["gpu"] + "!", cpu=(float(LAUNCH["cpu"]),) * 2,
                  memory=(LAUNCH["memory_gib"] * 1024,) * 2, retries=0, volumes={"/w": vol}, secrets=secrets,
                  scaledown_window=LAUNCH["scaledown_window_s"], startup_timeout=LAUNCH["startup_timeout_s"], timeout=TIMEOUT)
    def latentsync_main(job: dict, launch: dict):
        bad = container_gate(job, launch)
        if bad:
            return {"state": "FAILED", "error": "refused in the container: " + "; ".join(bad)}
        from huggingface_hub import HfApi
        vol.reload()
        return body(job, launch, TIMEOUT, commit=vol.commit, api=HfApi(token=_tok()))

    @app.local_entrypoint()
    def main(job: str = ""):
        spec = json.loads(Path(job).read_text(encoding="utf-8"))
        res = paid_run(LAUNCH, spec, remote=latentsync_main.remote)
        Path(job).with_suffix(".result.json").write_text(json.dumps(res))
        print("result", json.dumps(res))
        if (res or {}).get("state") != "DONE":
            raise SystemExit(4)
