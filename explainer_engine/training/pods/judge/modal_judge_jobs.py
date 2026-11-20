"""P2: Qwen3-VL (8B and 30B-A3B) as an automatic frame judge on Modal, A100-80GB (coordinator brief TEST_PAID_PLAN_AND_P2_BRIEF_ka.md;
the owner's word for paid tests: cmsg_01Hnu5zB86sjUj5GtTgaUkPWY3u2yHpBodP5oiGxehoiGX, 2026-11-20 08:26 UTC).

The same pattern as ``training/pods/klein/modal_klein_jobs.py`` and ``ltx/modal_ltx_jobs.py`` (OR-37 ladder L0..L4 bound to the launch
file's and this worker's bytes, the one ledger ``core/ledger.Run``, the night ledger, the creator's GO ``EE_MODAL_GO``, CH-07
``paid_offer``, OR-33 upload-and-verify, a function timeout that comes from the cap), cut down to what a judge needs: ONE container, the
models loaded one after the other (never two at once), ``min_containers`` 0, scale-down 2 s, the run id in every output path.

What the audit lessons ask of a Modal worker is built in: a clean deadline that raises between two asks (no ``os._exit``), an attempt
marker on the Volume that refuses a second attempt of the same run key (Modal re-schedules a container that died with work assigned,
whatever ``retries=0`` says), the end path (Volume commit, the last upload and its read-back) inside a margin the timeout leaves, and
``modal run <this file>::<entry>`` as the only way in (the entrypoints refuse without the ladder, the preflight and the GO).

Imports at the top are stdlib only. The container holds this folder (image ``add_local_dir``) and ``launch_a100.json``, not the repo;
the local entrypoints import the repo's ``core.ledger``, ``cloud.modal_run``, ``cloud.paid_offer`` and ``cloud.night_budget``.
The Modal account is the creator's second one (``MODAL1_*`` must be the active ``MODAL_*``); values are never printed."""
from __future__ import annotations

import gc
import hashlib
import json
import os
import re
import sys
import tarfile
import time
import uuid
from pathlib import Path

try:  # the worker module is imported by tests and inside the container; `modal` is only needed to define the app
    import modal
except ImportError:  # pragma: no cover
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
JUDGE_DIR = Path(__file__).resolve().parent
LAUNCH_PATH = JUDGE_DIR / "launch_a100.json"
SHARED_GATES = Path("/mnt/project-files/explainer-engine/final_plan_2026-11-19/ab_gates")
NIGHT_LEDGER = Path(os.environ.get("EE_NIGHT_LEDGER") or
                    "/mnt/project-files/explainer-engine/final_plan_2026-11-19/modal_stage/NIGHT_LEDGER_2026-11-19.json")
SECRET_NAME = "custom-secret"      # the owner's second account holds his HF token under this name; the key inside is HF_TOKEN
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
VOL = "/w"
WORK = Path("/workspace")
BAKED = Path("/root/judge")
GIB = 2 ** 30
JUDGE_FAILED = "JUDGE_FAILED"


def _ladder_dir() -> Path:
    return SHARED_GATES if SHARED_GATES.is_dir() else JUDGE_DIR.parents[3] / "jobs" / "judge_modal"


LADDER_PATH = Path(os.environ.get("EE_JUDGE_LADDER") or (_ladder_dir() / "ladder_modal_judge.json"))


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def sha_json(d) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_id(p) -> str:
    """The git blob id of a file (what the Hub reports for a file that is not LFS)."""
    p = Path(p)
    h = hashlib.sha1(f"blob {p.stat().st_size}\0".encode())
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def file_id(p, want: str) -> str:
    return _sha(p) if len(want) == 64 else git_blob_id(p)


def worker_sha() -> str:
    """The worker's own bytes AND the core and the prompts it runs: a change to any of them is another worker (final audit A5)."""
    h = hashlib.sha256()
    for p in [Path(__file__), JUDGE_DIR / "judge_core.py", *sorted((JUDGE_DIR / "prompts").glob("*.txt"))]:
        h.update(p.name.encode() + b"\0" + p.read_bytes())
    return h.hexdigest()


def proof(launch: dict) -> dict:
    return {"launch_sha": sha_json(launch), "worker_sha": worker_sha()}


def run_models(launch: dict) -> list[str]:
    """The models the main run asks and the weights rung stages: ``run_models`` of the launch (all pinned models when absent)."""
    return list(launch.get("run_models") or launch["models"])


def rate_usd_h(launch: dict) -> float:
    from explainer_engine.cloud import modal_schedule as MS
    per_s = MS.GPUS[launch["gpu"]]["usd_s"] + launch["cpu"] * MS.CPU_CORE_S + launch["memory_gib"] * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def stated_rate(launch: dict) -> float:
    return float(launch["usd_per_h"][launch["gpu"]])


def cost_timeout(cap_usd: float, usd_h: float, cold_start_s: float) -> int:
    """OR-37: the function timeout comes from the cap: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600) / usd_h * 3600)


def timeouts(launch: dict) -> tuple[int, int]:
    """(smoke, run) function timeouts, each checked to leave work time beyond the margin and to fit its cap."""
    c, h = launch["caps"], stated_rate(launch)
    out = []
    for k in ("smoke_usd", "run_usd"):
        t = cost_timeout(c[k], h, c["cold_start_s"])
        if t <= c["margin_s"] or (t + c["cold_start_s"]) * h / 3600 > c[k] + 1e-9:
            raise ValueError(f"{k}: timeout {t}s leaves no room beyond the {c['margin_s']}s end path, or does not fit the cap")
        out.append(t)
    return out[0], out[1]


def launch_problems(launch: dict, check_table: bool = True) -> list[str]:
    bad = [f"launch.{k} is not set" for k in ("app_name", "gpu", "cpu", "memory_gib", "usd_per_h", "caps", "models", "volume",
                                             "scaledown_window_s", "hf_out", "verdict") if not launch.get(k)]
    if bad:
        return bad
    c = launch["caps"]
    for k in ("smoke_usd", "run_usd", "ledger_line_usd", "cold_start_s", "margin_s"):
        if not isinstance(c.get(k), (int, float)) or c[k] <= 0:
            bad.append(f"caps.{k} is not set")
    if bad:
        return bad
    if c["smoke_usd"] + c["run_usd"] > 0.8 * c["ledger_line_usd"] + 1e-9:
        bad.append(f"smoke {c['smoke_usd']} + run {c['run_usd']} is above 80 % of the ledger line {c['ledger_line_usd']} (the ledger would refuse)")
    if launch["scaledown_window_s"] > 5:
        bad.append("scaledown_window_s is above 5 s")
    for k in run_models(launch):
        if k not in launch["models"]:
            bad.append(f"run_models names {k}, which is not pinned")
    for k, m in launch["models"].items():
        if not re.fullmatch(r"[0-9a-f]{40}", m.get("revision", "")) or not m.get("files"):
            bad.append(f"models.{k}: no full revision sha or no pinned files")
    if check_table:
        want = rate_usd_h(launch)
        if abs(want - stated_rate(launch)) > 0.01 * want:
            bad.append(f"usd_per_h {stated_rate(launch)} is not the price table's {want} (cloud/modal_schedule)")
    return bad


def token_problems(env=os.environ) -> list[str]:
    need = ("MODAL1_TOKEN_ID", "MODAL1_TOKEN_SECRET", "MODAL1_PROFILE")
    bad = [f"{k} is not set" for k in need if not env.get(k)]
    if bad:
        return bad
    if env.get("MODAL_TOKEN_ID") != env["MODAL1_TOKEN_ID"] or env.get("MODAL_TOKEN_SECRET") != env["MODAL1_TOKEN_SECRET"]:
        bad.append("the active MODAL_TOKEN_ID / MODAL_TOKEN_SECRET are not the MODAL1 pair")
    if env.get("MODAL_PROFILE") != env["MODAL1_PROFILE"]:
        bad.append("MODAL_PROFILE is not MODAL1_PROFILE")
    return bad


def go_gate(env=os.environ, plan_sha: str | None = None) -> str:
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of the plan he said yes to>`` (OR-23)."""
    v = env.get("EE_MODAL_GO", "")
    m = GO.match(v)
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the creator's yes message id>:<the plan's sha256[:12]>' (OR-23); nothing was started")
    if not plan_sha or m.group(2) != plan_sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than this one (OR-23); nothing was started")
    return v


def offer_problems(env=os.environ, now=None) -> list[str]:
    path = env.get("EE_PAID_OFFER")
    if not path or not Path(path).is_file():
        return ["CH-07: EE_PAID_OFFER must name a paid_offer/1 file (python -m explainer_engine.cloud.paid_offer check)"]
    from explainer_engine.cloud import paid_offer
    try:
        offer = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as exc:
        return [f"CH-07: {path} is not JSON: {exc}"]
    return [f"CH-07: {p}" for p in paid_offer.problems(offer, now)]


def preflight(launch: dict, *, paid: bool = True, env=os.environ):
    """Free checks before any paid call; ``paid=False`` for the CPU rungs (no offer: CH-07 is GPU-only)."""
    bad = launch_problems(launch) + token_problems(env)
    if paid:
        from explainer_engine.core import spend_caps
        try:
            line = float(spend_caps.modal()["per_run_usd"])
            if launch["caps"]["ledger_line_usd"] > line + 1e-9:
                bad.append(f"ledger_line_usd {launch['caps']['ledger_line_usd']} is above the creator's modal line ${line:g}")
        except spend_caps.OverCeiling as exc:
            bad.append(str(exc))
        bad += offer_problems(env)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def container_gate(launch: dict, baked=BAKED / "launch_a100.json") -> list[str]:
    """The last line inside the container: the launch passed in is the one baked into the image, the scale-down is short."""
    bad = []
    if Path(baked).exists() and json.loads(Path(baked).read_text(encoding="utf-8")) != launch:
        bad.append("the launch passed in is not the launch file baked into the image")
    return bad + launch_problems(launch, check_table=False)


# --- ledgers (local side) ----------------------------------------------------------------------------------------------------

def reserve_launch(ledger_path: str, item: str, amount: float, line: float):
    from explainer_engine.core.ledger import Run
    run = Run.open(ledger_path, caps={"modal_usd": float(line)})
    if item in run.data.get("items", {}).get("launch", {}):
        raise SystemExit(f"{item}: launched already; a repeat would pay twice; nothing was started")
    run.reserve("modal_usd", float(amount), item)
    run.done("launch", item, at=round(time.time(), 1), reserved_usd=float(amount))
    return run


def settle_launch(run, item: str, wall_s: float, rate: float) -> float:
    usd = round(max(0.0, float(wall_s)) * float(rate) / 3600.0, 4)
    run.settle("modal_usd", item, usd)
    return usd


def night_reserve(item: str, usd: float, why: str = ""):
    from explainer_engine.cloud import night_budget as NB
    from explainer_engine.core import spend_caps
    if not isinstance((spend_caps.modal() or {}).get("night_total_usd"), (int, float)):
        return
    try:
        NB.reserve(NIGHT_LEDGER, item, usd, why)
    except NB.NightCapExceeded as exc:
        raise SystemExit(f"night total: {exc}; nothing was started") from None


def night_settle(item: str, usd: float):
    from explainer_engine.cloud import night_budget as NB
    try:
        NB.settle(NIGHT_LEDGER, item, usd)
    except NB.NightCapExceeded as exc:
        print("NIGHT LEDGER SETTLE FAILED:", exc, flush=True)


def ladder_gate(rung: str, launch: dict):
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(LADDER_PATH), rung, proof=proof(launch))


def record(rung: str, ok: bool, launch: dict, **info):
    from explainer_engine.cloud import modal_run as MR
    MR.record_rung(LADDER_PATH, rung, ok, **proof(launch), **info)
    if not ok:
        raise SystemExit(f"rung {rung} is red: {json.dumps(info, default=str)[:600]}")


# --- weights (CPU container) -------------------------------------------------------------------------------------------------

def weights_root(launch: dict, key: str, vol_root=VOL) -> Path:
    return Path(vol_root) / launch["models"][key]["dir"]


def check_weights(launch: dict, key: str, vol_root=VOL, *, hash_files: bool) -> list[str]:
    """Every pinned file present with its size; with ``hash_files`` also its sha256 / git blob id (done once, on CPU, after staging)."""
    root, bad = weights_root(launch, key, vol_root), []
    for f, pin in launch["models"][key]["files"].items():
        p = root / f
        if not p.is_file():
            bad.append(f"missing {f}")
        elif p.stat().st_size != pin["size"]:
            bad.append(f"size {p.stat().st_size} is not the pinned {pin['size']}: {f}")
        elif hash_files and file_id(p, pin["id"]) != pin["id"]:
            bad.append(f"{pin['kind']} mismatch {f}")
    return bad


def stage_weights(launch: dict, key: str, vol_root=VOL, download=None) -> list[str]:
    m = launch["models"][key]
    root = weights_root(launch, key, vol_root)
    missing = [f for f in m["files"] if not (root / f).is_file() or (root / f).stat().st_size != m["files"][f]["size"]]
    if missing:
        (download or _hf_download)(m["repo"], m["revision"], missing, root)
    return check_weights(launch, key, vol_root, hash_files=True)


def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def _hf_download(repo: str, revision: str, files: list[str], root: Path):
    from huggingface_hub import hf_hub_download
    for f in files:
        hf_hub_download(repo, f, revision=revision, local_dir=str(root), token=_tok())


# --- HF upload with read-back (OR-33) ---------------------------------------------------------------------------------------

class Uploader:
    """Uploads the run's files under ``<hf_out>/<run_id>/<kind>/`` in ONE commit per flush (the Hub limits commits per hour) and
    reads every file's git blob id back; ``pending`` holds what changed since the last flush."""

    def __init__(self, api, out: Path, prefix: str, repo=HF_REPO, op_cls=None):
        self.api, self.out, self.prefix, self.repo = api, Path(out), prefix.rstrip("/"), repo
        self.op_cls = op_cls               # the Hub's CommitOperationAdd in the container; a test passes its own (no huggingface_hub needed)
        self.sent: dict[str, str] = {}
        self.problems: list[str] = []

    def files(self) -> dict[str, str]:
        return {str(p.relative_to(self.out)): git_blob_id(p) for p in sorted(self.out.rglob("*.json")) if not p.name.startswith(".")}

    def flush(self, verify: bool = False) -> list[str]:
        now = self.files()
        todo = [r for r, b in now.items() if self.sent.get(r) != b]
        if todo:
            if self.op_cls is None:
                from huggingface_hub import CommitOperationAdd
                self.op_cls = CommitOperationAdd
            ops = [self.op_cls(path_in_repo=f"{self.prefix}/{r}", path_or_fileobj=str(self.out / r)) for r in todo]
            self.api.create_commit(repo_id=self.repo, repo_type="dataset", operations=ops, commit_message=f"judge P2 {self.prefix.rsplit('/', 2)[-2]}: {len(todo)} files")
            self.sent.update({r: now[r] for r in todo})
        if verify:
            bad = []
            for r, b in now.items():
                info = self.api.get_paths_info(self.repo, [f"{self.prefix}/{r}"], repo_type="dataset")
                got = info[0].blob_id if info else None
                if got != b:
                    bad.append(f"{r}: HF has {got}, local {b}")
            self.problems = bad
            return bad
        return []


# --- the body (inside the container) ----------------------------------------------------------------------------------------

def fetch_batch(spec: dict, dest: Path, download=None) -> Path:
    """The sha256-NAMED batch tar from HF (never a name on main), hash-checked before it is unpacked."""
    name = spec["batch_path"]
    if not re.search(r"-[0-9a-f]{64}\.tar\.gz$", name):
        raise SystemExit(f"{name}: not a sha256-named file")
    dest.mkdir(parents=True, exist_ok=True)
    if download:
        got = Path(download(name, dest))
    else:
        from huggingface_hub import hf_hub_download
        got = Path(hf_hub_download(HF_REPO, name, repo_type="dataset", local_dir=str(dest), token=_tok()))
    have = _sha(got)
    if have != spec["batch_sha"]:
        raise SystemExit(f"batch {name} has sha256 {have[:12]}, the pin says {spec['batch_sha'][:12]}: nothing was run")
    return got


def unpack(tar: Path, dest: Path) -> Path:
    import shutil
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar) as tf:
        tf.extractall(dest, filter="data") if sys.version_info >= (3, 12) else tf.extractall(dest)
    return dest


def vram_facts() -> dict:
    try:
        import torch
        if not torch.cuda.is_available():
            return {}
        return {"max_allocated_gib": round(torch.cuda.max_memory_allocated() / GIB, 2), "reserved_gib": round(torch.cuda.memory_reserved() / GIB, 2),
                "total_gib": round(torch.cuda.get_device_properties(0).total_memory / GIB, 2), "device": torch.cuda.get_device_name(0)}
    except Exception as exc:  # noqa: BLE001 - facts only, never a reason to stop
        return {"error": f"{type(exc).__name__}: {str(exc)[:100]}"}


def _core():
    """judge_core is imported from this folder both locally (package import) and in the container (folder on sys.path)."""
    try:
        from explainer_engine.training.pods.judge import judge_core
    except ImportError:
        sys.path.insert(0, str(JUDGE_DIR if JUDGE_DIR.exists() else BAKED))
        import judge_core
    return judge_core


def body(spec: dict, launch: dict, *, timeout_s: int, vol_root=VOL, work=WORK, commit=lambda: None, reload=lambda: None, api=None,
             download=None, now=time.monotonic, load_judge=None, vram=vram_facts, free=None, baked=BAKED / "launch_a100.json", op_cls=None) -> dict:
    J = _core()
    t0, wall0 = now(), time.time()
    bad = container_gate(launch, baked)
    if bad:
        return {"state": "FAILED", "error": "refused in the container: " + "; ".join(bad)}
    kind, key = spec["kind"], f"{spec['run_id']}_{spec['kind']}"
    err = J.claim_attempt(vol_root, key, reload=reload, commit=commit)
    if err:
        return {"state": "FAILED", "error": err}
    models = [{"key": k, "path": str(weights_root(launch, k, vol_root)), "cls": launch["models"][k]["model_cls"], "experts": launch["models"][k].get("experts_implementation")}
              for k in (["qwen3vl_8b"] if kind == "smoke" else run_models(launch))]
    unstaged = [f"{m['key']}: {p}" for m in models for p in check_weights(launch, m["key"], vol_root, hash_files=False)]
    if unstaged:
        return {"state": "FAILED", "error": "the model files are not staged on the Volume (run the L2 rung first)", "problems": unstaged[:8]}
    try:
        root = unpack(fetch_batch(spec, Path(work) / "dl", download), Path(work) / "batch")
        batch = json.loads((root / "batch.json").read_text(encoding="utf-8"))
    except SystemExit as exc:
        return {"state": "FAILED", "error": str(exc)}
    out = Path(work) / "out"
    up = Uploader(api, out, f"{launch['hf_out']}/{spec['run_id']}/{kind}", op_cls=op_cls) if api is not None else None
    up_errors: list[str] = []

    def on_step(path, info):
        commit()                                      # the Volume copy exists before any network upload
        if up and (info["kind"] != "frame" or info.get("flush")):
            try:
                up.flush()
            except Exception as exc:  # noqa: BLE001 - storage down must not kill the run; the final flush reports it
                up_errors.append(f"{type(exc).__name__}: {str(exc)[:160]}")
    if load_judge is None:
        def load_judge(m):
            import torch
            torch.cuda.reset_peak_memory_stats()
            return J.HFJudge(m["path"], device="cuda", model_cls=m["cls"], experts=m.get("experts"))
    if free is None:
        def free(judge):
            del judge.model
            gc.collect()
            try:
                import torch
                torch.cuda.empty_cache()
            except Exception:  # noqa: BLE001
                pass
    deadline = t0 + timeout_s - launch["caps"]["margin_s"]
    try:
        res = J.run(batch, root, out, models, load_judge, th=launch["verdict"], deadline=deadline, now=now, on_step=on_step, vram=vram,
                    free=free, only_frames=1 if kind == "smoke" else None)
    except Exception as exc:  # noqa: BLE001 - the end path still saves and uploads what exists
        res = {"end": "CRASHED", "problems": [f"{type(exc).__name__}: {str(exc)[:300]}"]}
    result = {"state": "DONE" if res.get("end") == "DONE" else "FAILED", "end": res.get("end"), "kind": kind, "gpu": launch["gpu"],
              "run_id": spec["run_id"], "body_s": round(time.time() - wall0, 1), "problems": res.get("problems"),
              "models": {k: {s: v.get(s) for s in ("state", "load_s", "run_s", "vram_after_load", "vram_peak", "error")}
                         for k, v in (res.get("models") or {}).items()}}
    J._atomic(out / "modal_record.json", result)
    commit()
    if up:
        try:
            bad = up.flush(verify=True)
        except Exception as exc:  # noqa: BLE001
            bad = [f"final upload failed: {type(exc).__name__}: {str(exc)[:160]}"]
        bad = up_errors[-3:] + bad if bad else []     # earlier errors count only if the final read-back is not clean
        if bad:
            result.update(state="FAILED", problems=list(result.get("problems") or []) + bad)
    return result


# --- the Modal app -----------------------------------------------------------------------------------------------------------

LAUNCH = load_launch()

if modal is not None:
    _img = LAUNCH.get("image", {})
    app = modal.App(LAUNCH.get("app_name") or "ee-judge-jobs")
    vol = modal.Volume.from_name(LAUNCH.get("volume") or "ee-weights", version=2, create_if_missing=True)
    image = (modal.Image.debian_slim(python_version=f"{sys.version_info.major}.{sys.version_info.minor}")
             .pip_install(f"torch=={_img.get('torch')}", extra_index_url=_img.get("torch_index"))
             .pip_install(f"torchvision=={_img.get('torchvision')}", extra_index_url=_img.get("torch_index"))
             .pip_install(f"huggingface_hub=={LAUNCH.get('hf_hub_pin')}", f"transformers=={_img.get('transformers')}", "accelerate", "pillow")
             .add_local_dir(str(JUDGE_DIR), str(BAKED), ignore=["__pycache__", "*.pyc"]))
    secrets = [modal.Secret.from_name(SECRET_NAME)]
    CPU_KW = dict(image=image, cpu=(2.0, 2.0), retries=0, secrets=secrets)

    @app.function(memory=(4096, 4096), timeout=600, **CPU_KW)
    def env_check():
        _tok()
        bad, info = [], {}
        for mod in ("torch", "torchvision", "transformers", "huggingface_hub", "PIL", "accelerate"):
            try:
                info[mod] = str(getattr(__import__(mod), "__version__", "?"))
            except Exception as exc:  # noqa: BLE001
                bad.append(f"{mod}: {type(exc).__name__}: {str(exc)[:120]}")
        try:
            from transformers import AutoModelForImageTextToText, AutoProcessor  # noqa: F401
        except Exception as exc:  # noqa: BLE001
            bad.append(f"transformers classes: {type(exc).__name__}: {str(exc)[:120]}")
        if not str(info.get("torch", "")).startswith(_img.get("torch", "?")):
            bad.append(f"torch {info.get('torch')} is not the pinned {_img.get('torch')}")
        return {"problems": bad, **info}

    @app.function(memory=(8192, 8192), timeout=3600, volumes={VOL: vol}, **CPU_KW)
    def weights_stage(launch: dict):
        out = {}
        for k in run_models(launch):
            out[k] = stage_weights(launch, k)
            vol.commit()
        return out

    _t_smoke, _t_run = timeouts(LAUNCH)
    _gpu_kw = dict(image=image, gpu=LAUNCH["gpu"], cpu=(float(LAUNCH["cpu"]),) * 2, memory=(LAUNCH["memory_gib"] * 1024,) * 2, retries=0,
                   volumes={VOL: vol}, secrets=secrets, scaledown_window=LAUNCH["scaledown_window_s"],
                   startup_timeout=LAUNCH["startup_timeout_s"], max_containers=1)

    def _remote(spec, launch, timeout_s):
        from huggingface_hub import HfApi
        return body(spec, launch, timeout_s=timeout_s, commit=vol.commit, reload=vol.reload, api=HfApi(token=_tok()))

    @app.function(timeout=_t_smoke, name="judge_smoke", serialized=True, **_gpu_kw)
    def smoke_fn(spec: dict, launch: dict):
        return _remote(spec, launch, _t_smoke)

    @app.function(timeout=_t_run, name="judge_main", serialized=True, **_gpu_kw)
    def main_fn(spec: dict, launch: dict):
        return _remote(spec, launch, _t_run)

    def _spec(plan: str, batch: str, kind: str, cap: float) -> dict:
        plan_sha, bsha = _sha(plan), _sha(batch)
        run_id = f"{plan_sha[:12]}_{sha_json(LAUNCH)[:12]}"
        return {"kind": kind, "cap_usd": cap, "plan_sha256": plan_sha, "run_id": run_id, "batch_sha": bsha,
                "batch_path": f"code/judge/batch-{bsha}.tar.gz", "launch_sha": sha_json(LAUNCH), "worker_sha": worker_sha(),
                "nonce": uuid.uuid4().hex[:12]}

    def _batch_on_hf(spec: dict):
        from huggingface_hub import HfApi
        info = HfApi(token=_tok()).get_paths_info(HF_REPO, [spec["batch_path"]], repo_type="dataset")
        if not info:
            raise SystemExit(f"{spec['batch_path']} is not on HF: upload the batch first (free); nothing was started")

    @app.local_entrypoint()
    def check():
        """L1 (CPU): the launch, the token pair, the image imports."""
        ladder_gate("L1", LAUNCH)
        bad = launch_problems(LAUNCH) + token_problems()
        if bad:
            raise SystemExit("the launch is not pinned:\n" + "\n".join(bad))
        res = env_check.remote()
        print("env_check", res["problems"] or "imports ok", {k: v for k, v in res.items() if k != "problems"})
        record("L1", not res["problems"], LAUNCH, missing=res["problems"], versions={k: v for k, v in res.items() if k != "problems"})

    @app.local_entrypoint()
    def weights(plan: str = ""):
        """L2 (CPU): stage both models on the Volume, then every pinned size and sha256 / blob id is checked. Never on the GPU."""
        preflight(LAUNCH, paid=False)
        print("GO", go_gate(plan_sha=_sha(plan)), flush=True)
        ladder_gate("L2", LAUNCH)
        res = weights_stage.remote(LAUNCH)
        bad = [f"{k}: {p}" for k, v in res.items() for p in v]
        print("weights", bad or "all files on the Volume, hashes match")
        record("L2", not bad, LAUNCH, problems=bad)

    def _launch(plan: str, ledger: str, batch: str, rung: str, kind: str):
        preflight(LAUNCH)
        smoke = kind == "smoke"
        cap = LAUNCH["caps"]["smoke_usd" if smoke else "run_usd"]
        t = _t_smoke if smoke else _t_run
        print("GO", go_gate(plan_sha=_sha(plan)), "timeout", t, "s on", LAUNCH["gpu"], flush=True)
        ladder_gate(rung, LAUNCH)
        spec = _spec(plan, batch, kind, cap)
        _batch_on_hf(spec)
        item = f"judge_{kind}_{spec['run_id']}"
        run = reserve_launch(ledger, item, cap, LAUNCH["caps"]["ledger_line_usd"])
        hard = round((t + LAUNCH["caps"]["cold_start_s"]) * stated_rate(LAUNCH) / 3600, 4)
        night_reserve(item, hard, f"P2 judge {kind}")
        t0, res = time.time(), None
        try:
            res = (smoke_fn if smoke else main_fn).remote(spec, LAUNCH)
        finally:
            wall = time.time() - t0
            usd = settle_launch(run, item, wall, stated_rate(LAUNCH))
            night_settle(item, usd)
            print("settled", usd, "USD for", round(wall, 1), "s", flush=True)
        print("result", json.dumps(res, default=str))
        return res

    @app.local_entrypoint()
    def smoke(plan: str = "", ledger: str = "", batch: str = ""):
        """L3 (GPU, tiny cap): Qwen3-VL-8B, one frame, four questions; memory and seconds measured."""
        res = _launch(plan, ledger, batch, "L3", "smoke")
        ok = res.get("state") == "DONE"
        m = (res.get("models") or {}).get("qwen3vl_8b") or {}
        record("L3", ok, LAUNCH, measured={"gpu": LAUNCH["gpu"], "body_s": res.get("body_s"), "load_s": m.get("load_s"),
                                          "vram": m.get("vram_peak")} if ok else None,
               result={k: res.get(k) for k in ("state", "end", "error", "problems")})

    @app.local_entrypoint()
    def main(plan: str = "", ledger: str = "", batch: str = ""):
        """L4 (GPU, the run's cap): both models, every frame."""
        res = _launch(plan, ledger, batch, "L4", "main")
        if res.get("state") != "DONE":
            print(JUDGE_FAILED, flush=True)
            raise SystemExit(4)
