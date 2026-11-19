"""The Klein picture batch on Modal (W5, D-132; the creator 2026-11-19 20:07 UTC, cmsg_01Hnu5zB86sjUj5GtTgaUkPWPRTkVzj6iaGYmS7QLe7y4K:
RunPod is dropped, Modal with his second account; the $1.00 cap of cmsg_01Hnu5zB86sjUj5GtTgaUkPWB2qsAtWtX3jWU1XUQtHEm7).

The same pattern as ``training/pods/ltx/modal_ltx_jobs.py`` (OR-37 ladder L0..L4 bound to the launch file's and this worker's bytes, the one
ledger ``core/ledger.Run``, the creator's GO ``EE_MODAL_GO``, CH-07 ``paid_offer``, OR-33 upload-and-verify per picture, a function timeout
that comes from the cap) and the same work as ``klein_jobs.run`` which it calls UNCHANGED: the container fetches the sha256-named code
bundle and batch from HF (never a name on main), checks both hashes, unpacks them, sets the clock and cap that ``run`` reads
(``EE_PRICE`` = the Modal card's rate, ``EE_MAX_USD`` = the run's cap, ``EE_CREATED`` = the container's start minus the measured cold
start), and ``run`` does L2 (model files sha256), the L3 smoke picture and the pictures, each verified on HF before the next.

Imports at the top are stdlib only: the container holds just this file and ``launch.json``; the repo code arrives as the pinned bundle.
Nothing here starts without ``modal run <this file>::<entry>`` (the session hooks refuse every other form) and the entrypoints refuse
without the ladder, the preflight, the GO and a Modal line in ``config/spend_caps.json`` (``modal``; missing = a zero budget).
The Modal account is the creator's second one: ``MODAL1_TOKEN_ID`` / ``MODAL1_TOKEN_SECRET`` / ``MODAL1_PROFILE`` must be the active
``MODAL_*`` credentials; their values are never printed."""
from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import sys
import tarfile
import time
import uuid
from pathlib import Path

try:  # the worker module is imported by tests and inside the container; `modal` is only needed to define the app
    import modal
except ImportError:  # pragma: no cover - the local cloud session has no modal package until it is installed
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
KLEIN_DIR = Path(__file__).resolve().parent
LAUNCH_PATH = KLEIN_DIR / "launch.json"
LAUNCHER = KLEIN_DIR / "klein_pod.sh"                      # its two printf pins are the one record of the code bundle and batch sha256
SHARED_GATES = Path("/mnt/project-files/explainer-engine/final_plan_2026-11-19/ab_gates")   # the project's shared folder: any thread sees the rungs
# The ladder record lives OUTSIDE the code bundle (a record written after the pin must never change the bundle it pins).
LADDER_PATH = Path(os.environ.get("EE_KLEIN_LADDER") or (SHARED_GATES if SHARED_GATES.is_dir() else KLEIN_DIR.parents[3] / "jobs" / "klein_modal")
                   / "ladder_modal_klein.json")
SECRET_NAME = "custom-secret"   # the owner's second account holds his HF token under this name (his message 2026-11-19 20:41 UTC); the key inside is HF_TOKEN
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
MARGIN_S = 90                    # the end path after the last picture: Volume commit, the final upload and the HF check
VOL = "/w"
WORK = Path("/workspace")
BAKED_LAUNCH = Path("/root/launch.json")
KLEIN_FAILED = "KLEIN_FAILED"


def load_launch(path=LAUNCH_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _modal(launch: dict) -> dict:
    return launch.get("modal") or {}


def sha_json(d) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def launch_sha(launch: dict) -> str:
    return sha_json(launch)


def _sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def worker_sha() -> str:
    return _sha(__file__)


def proof(launch: dict) -> dict:
    return {"launch_sha": launch_sha(launch), "worker_sha": worker_sha()}


def gpus(launch: dict) -> list[str]:
    m = _modal(launch)
    return [g for g in (m.get("gpu"), m.get("gpu_fallback")) if g]


def rate_usd_h(launch: dict, gpu: str | None = None) -> float:
    """GPU + CPU + memory per hour from ``cloud/modal_schedule`` (the dated table; local side only)."""
    from explainer_engine.cloud import modal_schedule as MS
    m = _modal(launch)
    g = gpu or m["gpu"]
    per_s = MS.GPUS[g]["usd_s"] + m["cpu"] * MS.CPU_CORE_S + m["memory_gib"] * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def stated_rate(launch: dict, gpu: str | None = None) -> float:
    """The rate the clock runs on, from the launch file (its source and date are recorded there)."""
    m = _modal(launch)
    g = gpu or m["gpu"]
    return float(m["usd_per_h"][g])


def cost_timeout(cap_usd: float, usd_h: float, cold_start_s: float) -> int:
    """OR-37: the function timeout comes from the cap: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600) / usd_h * 3600)


def check_timeout(timeout_s: int, cap_usd: float, usd_h: float, cold_start_s: float) -> int:
    if timeout_s <= MARGIN_S or timeout_s * usd_h / 3600 + cold_start_s * usd_h / 3600 > cap_usd:
        raise ValueError(f"timeout {timeout_s}s does not fit the cap ${cap_usd} (or leaves no room for the end path)")
    return timeout_s


def timeouts(launch: dict, gpu: str | None = None) -> tuple[int, int] | None:
    """(smoke, run) function timeouts of one card from the caps; None while the modal section is unpinned (no GPU function is defined)."""
    if modal_problems(launch, check_table=False):
        return None
    c, m = _modal(launch)["caps"], _modal(launch)
    h = stated_rate(launch, gpu)
    return (check_timeout(cost_timeout(c["smoke_usd"], h, m["cold_start_s"]), c["smoke_usd"], h, m["cold_start_s"]),
            check_timeout(cost_timeout(c["run_usd"], h, m["cold_start_s"]), c["run_usd"], h, m["cold_start_s"]))


def _num(v) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool) and v > 0


def modal_problems(launch: dict, *, check_table: bool = True) -> list[str]:
    """Every pin and cap of the Modal section, the rate equal to the dated price table, the caps inside the run's cap (OR-22: none guessed)."""
    m = _modal(launch)
    if not m:
        return ["launch.json has no modal section"]
    bad = [f"modal.{k} is not set" for k in ("app_name", "gpu", "cpu", "memory_gib", "scaledown_window_s", "startup_timeout_s", "hf_hub_pin",
                                            "prices_date", "prices_source", "usd_per_h", "caps", "minutes", "volume") if not m.get(k)]
    if bad:
        return bad
    for g in gpus(launch):
        if not _num((m["usd_per_h"] or {}).get(g)):
            bad.append(f"modal.usd_per_h has no rate for {g}")
    c = m["caps"]
    for k in ("smoke_usd", "run_usd"):
        if not _num(c.get(k)):
            bad.append(f"modal.caps.{k} is not set")
    if not _num(m.get("cold_start_s")):
        bad.append("modal.cold_start_s is not set (the measured container overhead; an estimate until L3 measures it)")
    if not bad and launch.get("cap_usd") and c["run_usd"] > float(launch["cap_usd"]) + 1e-9:
        bad.append(f"modal.caps.run_usd {c['run_usd']} is above the creator's recorded cap_usd {launch['cap_usd']}")
    if not bad and launch.get("cap_usd") and c["smoke_usd"] + c["run_usd"] > float(launch["cap_usd"]) + 1e-9:
        bad.append(f"modal.caps smoke_usd {c['smoke_usd']} + run_usd {c['run_usd']} is above the creator's recorded total cap_usd "
                   f"{launch['cap_usd']} (his Klein $1 is the total, smoke included)")
    if not bad and m["scaledown_window_s"] > 5:
        bad.append(f"modal.scaledown_window_s {m['scaledown_window_s']} is above 5 s (no warm container is paid)")
    if not bad and check_table:
        for g in gpus(launch):
            want = rate_usd_h(launch, g)
            if abs(want - stated_rate(launch, g)) > 0.01 * want:
                bad.append(f"modal.usd_per_h[{g}] {stated_rate(launch, g)} is not the price table's {want} (cloud/modal_schedule)")
    return bad


def token_problems(env=os.environ) -> list[str]:
    """The creator's second Modal account must be the active one (his message 2026-11-19 20:07 UTC); values are never printed."""
    need = ("MODAL1_TOKEN_ID", "MODAL1_TOKEN_SECRET", "MODAL1_PROFILE")
    bad = [f"{k} is not set" for k in need if not env.get(k)]
    if bad:
        return bad
    if env.get("MODAL_TOKEN_ID") != env["MODAL1_TOKEN_ID"] or env.get("MODAL_TOKEN_SECRET") != env["MODAL1_TOKEN_SECRET"]:
        bad.append("the active MODAL_TOKEN_ID / MODAL_TOKEN_SECRET are not the MODAL1 pair: run this under the second account "
                   "(MODAL_TOKEN_ID=$MODAL1_TOKEN_ID MODAL_TOKEN_SECRET=$MODAL1_TOKEN_SECRET MODAL_PROFILE=$MODAL1_PROFILE)")
    if env.get("MODAL_PROFILE") != env["MODAL1_PROFILE"]:
        bad.append("MODAL_PROFILE is not MODAL1_PROFILE")
    return bad


def pins_of_script(script=LAUNCHER) -> dict:
    """The code bundle and batch sha256 the klein pod script carries (one source for the Modal and the pod route)."""
    text = Path(script).read_text(encoding="utf-8")
    out = {}
    for key, name in (("code", "ee_src.tar.gz"), ("batch", "batch.tar.gz")):
        m = re.search(r"printf '%s  %s\\n' ([0-9a-f]{64}) \"\$JOB/" + re.escape(name), text)
        out[key] = m.group(1) if m else None
    return out


def hf_paths(pins: dict) -> dict:
    """The sha256-NAMED files the container fetches (never a name on main that a later upload can replace)."""
    return {"code": f"code/klein/ee_src-{pins['code']}.tar.gz", "batch": f"code/klein/batch-{pins['batch']}.tar.gz"}


def modal_view(launch: dict, gpu: str | None = None) -> dict:
    """The launch ``klein_jobs.run`` sees inside the container: its numbers for this card (the estimate table with no download, the
    weights on the Volume); every pin and cap is the launch file's own."""
    m = _modal(launch)
    v = json.loads(json.dumps(launch))
    v["minutes"] = dict(launch["minutes"], **m["minutes"])
    v["weights_dir"] = VOL + "/klein"
    v["cap_usd"] = launch["cap_usd"]
    return v


def go_gate(env=os.environ, plan_sha: str | None = None):
    """EE_MODAL_GO = ``<the creator's message id>:<sha256[:12] of the plan he said yes to>`` (final audit B10)."""
    v = env.get("EE_MODAL_GO", "")
    m = GO.match(v)
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the card id of the creator's yes>:<the plan's sha256[:12]>' (OR-23); nothing was started")
    if not plan_sha or m.group(2) != plan_sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan than this one (OR-23); nothing was started")
    return v


def run_id(plan_sha: str, launch: dict) -> str:
    if not (isinstance(plan_sha, str) and len(plan_sha) == 64):
        raise ValueError("a run id needs the approved plan's sha256")
    return f"{plan_sha[:12]}_{launch_sha(launch)[:12]}"


def ladder_gate(rung: str, path=None, launch=None):
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(path or LADDER_PATH), rung, proof=proof(LAUNCH if launch is None else launch))


def record(rung: str, ok: bool, path=None, launch=None, **info):
    from explainer_engine.cloud import modal_run as MR
    MR.record_rung(path or LADDER_PATH, rung, ok, **proof(LAUNCH if launch is None else launch), **info)
    if not ok:
        raise SystemExit(f"rung {rung} is red: {json.dumps(info, default=str)[:600]}")


def offer_problems(env=os.environ, now=None) -> list[str]:
    """CH-07: a paid rung starts only from a passing ``paid_offer/1`` file named by ``EE_PAID_OFFER`` (the free credit checked first)."""
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
    """Free check before any paid call: the Modal section pinned, the klein pins closed, the caps inside the creator's Modal line
    (``config/spend_caps.json`` ``modal``; missing = a zero budget, refused), the second account active, the offer passing."""
    bad = modal_problems(launch) + token_problems(env)
    pins = pins_of_script()
    bad += [f"klein_pod.sh carries no {k} sha256 pin" for k, v in pins.items() if not v]
    from explainer_engine.training.pods.klein import klein_jobs as K
    bad += K.open_pins(launch)
    if paid:
        from explainer_engine.core import spend_caps
        try:
            line = float(spend_caps.modal()["per_run_usd"])
            stop = 0.8 * line   # core/ledger STOP_FRACTION: a reservation past 80 % of the line is refused, so the cap stays under it
            bad += [f"modal.caps.{k} ${_modal(launch)['caps'][k]:g} is above 80 % of the creator's ${line:g} per run (${stop:g})"
                    for k in ("smoke_usd", "run_usd") if _modal(launch).get("caps", {}).get(k, 0) > stop + 1e-9]
        except spend_caps.OverCeiling as exc:
            bad.append(str(exc))
        bad += offer_problems(env)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def container_gate(launch: dict, baked=BAKED_LAUNCH, *, gpu: str | None = None) -> list[str]:
    """The last line inside the paid container before anything loads (a ``.remote()`` from custom code skips the local entrypoints):
    the launch passed in is the launch file baked into the image, the scale-down is short, the cap is the creator's recorded one."""
    bad = []
    if Path(baked).exists() and json.loads(Path(baked).read_text(encoding="utf-8")) != launch:
        bad.append("the launch passed in is not the launch file baked into the image")
    bad += modal_problems(launch, check_table=False)
    if gpu and gpu not in gpus(launch):
        bad.append(f"{gpu} is not one of the launch's cards {gpus(launch)}")
    return bad


# --- the ledger (one ledger, core/ledger.Run; before .remote() the reservation, after it the settlement) -----------------------

def reserve_launch(ledger_path: str, item: str, amount: float, run_line: float):
    """Open the run's ledger with the creator's Modal line and reserve the cap BEFORE the paid call (refused past 80 % of it); a second
    launch of the same item is refused (it would pay twice), the launch mark is written here."""
    from explainer_engine.core.ledger import Run
    run = Run.open(ledger_path, caps={"modal_usd": float(run_line)})
    if item in run.data.get("items", {}).get("launch", {}):
        raise SystemExit(f"{item}: this run was launched already ({run.data['items']['launch'][item]}); a repeat would pay twice; "
                         "nothing was started")
    run.reserve("modal_usd", float(amount), item)
    run.done("launch", item, at=round(time.time(), 1), reserved_usd=float(amount))
    return run


def settle_launch(run, item: str, wall_s: float, rate: float) -> float:
    """After ``.remote()`` returned or raised: the launch's own wall clock at the card's rate, an upper bound of the bill."""
    usd = round(max(0.0, float(wall_s)) * float(rate) / 3600.0, 4)
    run.settle("modal_usd", item, usd)
    return usd


# --- in the container ------------------------------------------------------------------------------------------------------

def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def fetch_pinned(paths: dict, pins: dict, dest: Path, download=None) -> dict:
    """Download the sha256-named code bundle and batch and check each hash before anything is unpacked; returns their local paths.
    A name on main is never read: the file names carry the pins (a later upload cannot replace what a pin names)."""
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    out = {}
    for key in ("code", "batch"):
        name = paths[key]
        if not re.search(r"-[0-9a-f]{64}\.tar\.gz$", name):
            raise SystemExit(f"{name}: not a sha256-named file")
        got = Path((download or _hf_get)(name, dest))
        have = _sha(got)
        if have != pins[key]:
            raise SystemExit(f"{key}: {name} has sha256 {have[:12]}, the pin says {pins[key][:12]}: nothing was run")
        out[key] = got
    return out


def _hf_get(name: str, dest: Path) -> str:
    from huggingface_hub import hf_hub_download
    return hf_hub_download(HF_REPO, name, repo_type="dataset", local_dir=str(dest), token=_tok())


def unpack(files: dict, work=WORK) -> tuple[Path, Path]:
    ee, batch = Path(work) / "ee", Path(work) / "batch"
    for target, key in ((ee, "code"), (batch, "batch")):
        shutil.rmtree(target, ignore_errors=True)
        target.mkdir(parents=True, exist_ok=True)
        with tarfile.open(files[key]) as tf:
            tf.extractall(target, filter="data") if sys.version_info >= (3, 12) else tf.extractall(target)   # hashed above; the data filter refuses odd members
    return ee, batch


def set_clock(env, rate: float, cap: float, cold_start_s: float, now=time.time) -> dict:
    """What ``klein_jobs.run`` reads: the card's rate, the run's cap, and the pod's birth (the container's start less the measured
    cold start, so a slow start is paid for in the clock)."""
    env["EE_PRICE"] = str(rate)
    env["EE_MAX_USD"] = str(cap)
    env["EE_CREATED"] = str(now() - float(cold_start_s))
    return {"price_usd_per_h": rate, "cap_usd": cap, "cold_start_s": cold_start_s}


def check_weights(launch: dict, vol_root=VOL + "/klein", *, hash_files: bool = True) -> list[str]:
    """Every model file of the pin present on the Volume, hashed after staging (L2 on CPU, never on the GPU). ``hash_files=False``
    checks presence and the pinned size only: the GPU body must not hash 21 GB twice, ``klein_jobs.run`` L2 does it once."""
    from explainer_engine.training.pods.klein import klein_jobs as K
    m = K.model_of(launch)
    root = K.weights_root(launch, vol_root)
    bad = []
    for f, want in m["files"].items():
        p = root / f
        if not p.is_file() or p.stat().st_size == 0:
            bad.append(f"missing {f}")
        elif not hash_files:
            size = (m.get("sizes") or {}).get(f)
            if size is not None and p.stat().st_size != size:
                bad.append(f"size {p.stat().st_size} is not the pinned {size}: {f}")
        elif K.file_id(p, want) != want:
            bad.append(f"{'sha256' if len(want) == 64 else 'git blob id'} mismatch {f}")
    return bad


def stage_weights(launch: dict, vol_root=VOL + "/klein", download=None) -> list[str]:
    from explainer_engine.training.pods.klein import klein_jobs as K
    m = K.model_of(launch)
    root = K.weights_root(launch, vol_root)
    missing = [f for f in m["files"] if not (root / f).is_file()]
    if missing:
        (download or K._hf_download)(m["repo"], m["revision"], missing, root)
    return check_weights(launch, vol_root)


def body(spec: dict, launch: dict, *, gpu: str, timeout_s: int, vol_root=VOL + "/klein", work=WORK, commit=lambda: None, api=None,
         download=None, now=time.time, env=None, run_fn=None, baked=BAKED_LAUNCH, **run_kw) -> dict:
    """The paid body: gate, fetch and check the pinned files, set the clock, check the weights are staged, then ``klein_jobs.run`` unchanged."""
    env = os.environ if env is None else env
    t0 = now()
    bad = container_gate(launch, baked, gpu=gpu)
    if bad:
        return {"state": "FAILED", "error": "refused in the container: " + "; ".join(bad)}
    try:
        files = fetch_pinned(spec["paths"], spec["pins"], Path(work) / "dl", download=download)
    except SystemExit as exc:
        return {"state": "FAILED", "error": str(exc)}
    ee, batch_dir = unpack(files, work)
    if str(ee) not in sys.path:
        sys.path.insert(0, str(ee))
    view = modal_view(launch, gpu)
    from explainer_engine.training.pods.klein import klein_jobs as K
    unstaged = [f"{p}" for p in check_weights(view, vol_root, hash_files=False)]
    if unstaged:
        return {"state": "FAILED", "error": "the model files are not staged on the Volume (run the L2 rung first)",
                "problems": unstaged[:8]}
    batch = json.loads((batch_dir / "batch.json").read_text(encoding="utf-8"))
    if spec.get("smoke_only"):
        batch = dict(batch, jobs=batch["jobs"][:1], prefix=str(batch["prefix"]) + "_modal_smoke")
    clock = set_clock(env, stated_rate(launch, gpu), spec["cap_usd"], _modal(launch)["cold_start_s"], now=lambda: t0)   # fetch, unpack and hash time is on the clock
    out = WORK / "out" if work is WORK else Path(work) / "out"
    try:
        res = (run_fn or K.run)(batch, out, api=api, launch=view, vol_root=vol_root, created=float(env["EE_CREATED"]), **run_kw)
    except Exception as exc:  # noqa: BLE001 - the end path below still uploads what exists (OR-33); the rung is red
        res = {"end": "CRASHED", "problems": [f"{type(exc).__name__}: {str(exc)[:200]}"]}
    commit()
    ok = res.get("end") == "DONE"
    result = {"state": "DONE" if ok else "FAILED", "end": res.get("end"), "gpu": gpu, "smoke_only": bool(spec.get("smoke_only")),
              "spent_usd": res.get("spent_usd"), "clock": clock, "price_source": res.get("price_source"),
              "cap_source": res.get("cap_source"), "steps": res.get("steps"), "pictures": res.get("pictures"),
              "problems": res.get("problems"), "body_s": round(now() - t0, 1)}
    if api is not None:                              # run_record.json and the rung's own record go up verified, also on CAPPED or a failure
        out.mkdir(parents=True, exist_ok=True)
        from explainer_engine.core.store import write_json_atomic
        write_json_atomic(Path(out) / "modal_record.json", result)
        bad = upload_records(api, out, str(batch["prefix"]), ("run_record.json", "modal_record.json"), op=run_kw.get("upload_op"))
        if bad:
            result.update(state="FAILED", problems=list(result.get("problems") or []) + bad)
    return result


def upload_records(api, out, prefix: str, names, op=None) -> list[str]:
    """OR-33 for the records: each named file that exists is uploaded and its sha256 / blob id read back from HF (empty list = verified)."""
    from explainer_engine.training.pods.ltx import modal_ltx_jobs as M          # the pinned bundle is on sys.path by now
    present = [n for n in names if (Path(out) / n).is_file()]
    for _ in range(2):
        M.upload_round(api, Path(out), prefix, {}, final=True, op=op)
    res = M.verify_uploads(api, Path(out), prefix)
    return [f"{n}: {res.get(n, 'not verified')}" for n in present if res.get(n) != "ok"]

LAUNCH = load_launch()

if modal is not None:
    _m = _modal(LAUNCH)
    app = modal.App(_m.get("app_name") or "ee-klein-jobs")
    vol = modal.Volume.from_name(_m.get("volume") or "ee-weights", version=2, create_if_missing=True)   # the second account starts without one; a Volume is free until it holds data
    pip = LAUNCH.get("diffusers_version")
    image = (modal.Image.from_registry(LAUNCH["image"], add_python="3.12")
             .run_commands(f'pip install -q "torch=={_m.get("torch_pin")}" --index-url {_m.get("torch_cuda_index")}',
                           f'echo "torch=={_m.get("torch_pin")}" > /root/constraints.txt',
                           f'PIP_CONSTRAINT=/root/constraints.txt pip install -q "huggingface_hub=={_m.get("hf_hub_pin")}" '
                           f'"diffusers=={LAUNCH.get("diffusers_version")}" "transformers=={LAUNCH.get("transformers_version")}"')
             .add_local_file(str(LAUNCH_PATH), "/root/launch.json"))
    secrets = [modal.Secret.from_name(SECRET_NAME)]

    @app.function(image=image, cpu=(2.0, 2.0), memory=(4096, 4096), timeout=300, retries=0, secrets=secrets)
    def env_check():
        _tok()
        bad = []
        for mod in ("torch", "diffusers", "transformers", "huggingface_hub"):
            try:
                __import__(mod)
            except Exception as exc:  # noqa: BLE001 - reported, the rung is red
                bad.append(f"{mod}: {type(exc).__name__}: {str(exc)[:120]}")
        info = {}
        try:
            import torch
            info = {"torch": torch.__version__, "cuda": torch.version.cuda}
            if info["torch"].split("+")[0] != _m.get("torch_pin"):
                bad.append(f"torch {info['torch']} is not the pinned {_m.get('torch_pin')}")
        except Exception:  # noqa: BLE001 - already in bad
            pass
        return {"problems": bad, **info}

    @app.function(image=image, cpu=(2.0, 2.0), memory=(8192, 8192), timeout=3600, retries=0, volumes={VOL: vol}, secrets=secrets)
    def weights_stage(launch: dict, spec: dict):
        files = fetch_pinned(spec["paths"], spec["pins"], WORK / "dl")
        ee, _ = unpack(files)
        sys.path.insert(0, str(ee))
        bad = stage_weights(launch)
        vol.commit()
        return bad

    GPU_FUNCS = {}
    for _gpu in gpus(LAUNCH):
        _t = timeouts(LAUNCH, _gpu)
        if not _t:
            continue
        _kw = dict(image=image, gpu=_gpu, cpu=(float(_m["cpu"]),) * 2, memory=(_m["memory_gib"] * 1024,) * 2, retries=0,
                   volumes={VOL: vol}, secrets=secrets, scaledown_window=_m["scaledown_window_s"], startup_timeout=_m["startup_timeout_s"])

        def _make(gpu_name, t_smoke, t_run, kw):
            def _remote(spec, launch, timeout_s):
                from huggingface_hub import HfApi
                return body(spec, launch, gpu=gpu_name, timeout_s=timeout_s, commit=vol.commit, api=HfApi(token=_tok()))

            @app.function(timeout=t_smoke, name=f"klein_smoke_{gpu_name.lower().replace('-', '_')}", serialized=True, **kw)
            def smoke_fn(spec: dict, launch: dict):
                return _remote(spec, launch, t_smoke)

            @app.function(timeout=t_run, name=f"klein_main_{gpu_name.lower().replace('-', '_')}", serialized=True, **kw)
            def main_fn(spec: dict, launch: dict):
                return _remote(spec, launch, t_run)
            return smoke_fn, main_fn

        GPU_FUNCS[_gpu] = _make(_gpu, _t[0], _t[1], _kw)

    def _spec(plan: str, rung_cap: float, extra=None) -> dict:
        plan_sha = _sha(plan)
        pins = pins_of_script()
        return dict({"paths": hf_paths(pins), "pins": pins, "cap_usd": rung_cap, "plan_sha256": plan_sha,
                     "run_id": run_id(plan_sha, LAUNCH), "launch_sha": launch_sha(LAUNCH), "worker_sha": worker_sha(),
                     "nonce": uuid.uuid4().hex[:12]}, **(extra or {}))

    def _pick(gpu: str) -> str:
        g = gpu or _m["gpu"]
        if g not in GPU_FUNCS:
            raise SystemExit(f"{g!r} has no function: the launch's cards are {gpus(LAUNCH)}")
        return g

    @app.local_entrypoint()
    def check():
        """L1 (CPU, free credit): the token pair, the pins and shas, the image imports."""
        ladder_gate("L1")
        bad = modal_problems(LAUNCH) + token_problems()
        pins = pins_of_script()
        bad += [f"klein_pod.sh carries no {k} sha256 pin" for k, v in pins.items() if not v]
        if bad:
            raise SystemExit("the launch is not pinned:\n" + "\n".join(bad))
        res = env_check.remote()
        missing = res["problems"]
        print("env_check", missing or "imports ok", {k: v for k, v in res.items() if k != "problems"})
        record("L1", not missing, missing=missing, pins=pins, torch=res.get("torch"), cuda=res.get("cuda"))

    @app.local_entrypoint()
    def weights(plan: str = ""):
        """L2 (CPU): stage the model files on the Volume, then every size and sha256 is checked; never on the GPU."""
        preflight(LAUNCH, paid=False)
        print("GO card", go_gate(plan_sha=_sha(plan)), flush=True)
        ladder_gate("L2")
        bad = weights_stage.remote(LAUNCH, _spec(plan, _m["caps"]["smoke_usd"]))
        print("weights", bad or "all files on the Volume, sha256 match")
        record("L2", not bad, problems=bad)

    def _launch(plan: str, ledger: str, gpu: str, rung: str, smoke: bool):
        preflight(LAUNCH)
        from explainer_engine.core import spend_caps
        g = _pick(gpu)
        t = timeouts(LAUNCH, g)[0 if smoke else 1]
        cap = _m["caps"]["smoke_usd" if smoke else "run_usd"]
        print("GO card", go_gate(plan_sha=_sha(plan)), "timeout", t, "s on", g, flush=True)
        ladder_gate(rung)
        spec = _spec(plan, cap, {"smoke_only": smoke})
        item = f"klein_{'smoke' if smoke else 'main'}_{spec['run_id']}"
        run = reserve_launch(ledger, item, cap, spend_caps.modal()["per_run_usd"])
        t0, res = time.time(), None
        try:
            res = (GPU_FUNCS[g][0] if smoke else GPU_FUNCS[g][1]).remote(spec, LAUNCH)
        finally:
            wall = time.time() - t0
            print("settled", settle_launch(run, item, wall, stated_rate(LAUNCH, g)), "USD for", round(wall, 1), "s", flush=True)
        print("result", json.dumps(res, default=str))
        return g, res

    @app.local_entrypoint()
    def smoke(plan: str = "", ledger: str = "", gpu: str = ""):
        """L3 (GPU, tiny cap): the smoke picture and one picture, measured."""
        g, res = _launch(plan, ledger, gpu, "L3", True)
        ok = res.get("state") == "DONE"
        record("L3", ok, measured={"gpu": g, "body_s": res.get("body_s"), "steps": res.get("steps")} if ok else None,
               result={k: res.get(k) for k in ("state", "end", "error", "problems")})

    @app.local_entrypoint()
    def main(plan: str = "", ledger: str = "", gpu: str = ""):
        """L4 (GPU, the run's cap): the batch."""
        g, res = _launch(plan, ledger, gpu, "L4", False)
        if res.get("state") != "DONE":
            print(KLEIN_FAILED, flush=True)
            raise SystemExit(4)
