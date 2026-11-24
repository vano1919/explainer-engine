"""Layout-To-Render on Modal, A100-80GB (S3, coordinator brief BRIEFS_S3_T0B_AND_T1_CARD_ka.md item 1, 2026-11-20): the grey
``layout.mp4`` of a Blender scene + ONE picture on frame 0 + one or two sentences -> a 10 s LTX-2.5 clip through
``ltx_pipelines.ic_lora`` with the Layout-To-Render IC-LoRA (``config/cloud_pins.json`` ``models.video_ltx_layout_lora``).

A NEW worker beside ``modal_ltx_jobs.py``: that file, ``ltx/launch.json``, ``cloud/cheapest.*`` and ``config/retired_era.json`` are not
touched (coordinator, Q1). It is modelled on the P2 judge worker (PR #221): one container per launch, the one ledger ``core/ledger.Run``,
the night ledger, the creator's GO ``EE_MODAL_GO``, CH-07 ``paid_offer``, OR-33 upload-and-verify with a read-back, a function timeout
that comes from the cap, the ladder L1..L4, and what the audit lessons ask of a Modal worker (feedback-modal-crash-reschedule,
feedback-rehearse-container-body): a clean deadline that ends the CLI under ``subprocess.run(timeout=)`` (no ``os._exit``), an attempt
marker on the Volume that refuses a second attempt of the same run key, the end path (Volume copy, last upload, read-back) inside a
margin the timeout leaves, and ``modal run <this file>::<entry>`` as the only way in.

The OR-37 ladder (each rung recorded in the ladder file bound to this launch file and this worker; every GPU rung needs the creator's
GO card, a passing CH-07 offer, the OR-34 audit and the Haiku watchdog the coordinator opens):

    L1  ::check    CPU: the image imports torch, ltx_core, ltx_pipelines.ic_lora, PIL, numpy; ffmpeg and ffprobe exist
    L2  ::weights  CPU: the IC-LoRA is downloaded and its sha256 checked; the base files are checked (size; sha256 with --hash-base)
    L3  ::smoke    GPU, the smallest clip (``launch.smoke.frames``) under ``caps.smoke_usd``: measures memory (torch peak and
                   nvidia-smi peak, host RSS, cgroup peak), seconds, sound; stop-and-write if it does not fit
    L4  ::main     GPU, T1: one 10 s clip (Blender layout + picture + film line) under ``caps.run_usd``
    --  ::chain    GPU, T3: one scene as a chain (each clip from a frame of the one before), after L4 is green, under ``caps.chain_usd``

Nothing here has run on a GPU. Everything that is a number of the A100 (memory, seconds, price per clip, sound) is UNMEASURED until L3.
The container holds this worker's three files (image ``add_local_file``) and ``launch_layout_a100.json``, not the repo; the local
entrypoints import the repo's ``core.ledger``, ``cloud.modal_run``, ``cloud.cheapest`` (``offer_problems`` only) and ``cloud.night_budget``."""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tarfile
import threading
import time
import uuid
from pathlib import Path

try:  # imported by tests and inside the container; `modal` is only needed to define the app
    import modal
except ImportError:  # pragma: no cover
    modal = None

HF_REPO = "vano1919/tmr-artifacts"
LTX_DIR = Path(__file__).resolve().parent
LAUNCH_PATH = LTX_DIR / "launch_layout_a100.json"
WORKER_REL = "explainer_engine/training/pods/ltx/modal_layout_jobs.py"
SHARED_GATES = Path("/mnt/project-files/explainer-engine/final_plan_2026-11-19/ab_gates")
NIGHT_LEDGER = Path(os.environ.get("EE_NIGHT_LEDGER") or
                    (Path.home() / ".explainer_engine" / "night_ledger.sqlite3"))
SECRET_NAME = "custom-secret"      # the owner's second account holds his HF token under this name; the key inside is HF_TOKEN
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
VOL = "/w"
WORK = Path("/workspace")
BAKED = Path("/root/layout")       # layout_job.py, ic_lora_run.py, launch_layout_a100.json (image add_local_file)
CODE_DIR = "/workspace/LTX-2"      # the pinned LTX-2 checkout of the image
VOL_OUT = "out_layout"
GIB = 2 ** 30
LAYOUT_FAILED = "LAYOUT_FAILED"
SAVE_BUDGET_S = 45                 # the upload after each clip: short; the final flush retries longer
FILES = ("modal_layout_jobs.py", "layout_job.py", "ic_lora_run.py")


def _ladder_dir() -> Path:
    if SHARED_GATES.is_dir():
        return SHARED_GATES
    # inside the container the module sits at /root, three parents up does not exist: the ladder is never read there
    return LTX_DIR.parents[3] / "jobs" / "layout_modal" if len(LTX_DIR.parents) > 3 else Path("/tmp/layout_modal")


LADDER_PATH = Path(os.environ.get("EE_LAYOUT_LADDER") or (_ladder_dir() / "ladder_modal_layout.json"))


def load_launch(path=None) -> dict:
    """The launch file beside this worker, else the copy the image baked at ``BAKED`` (in the container only the worker is at /root)."""
    path = Path(path) if path else (LAUNCH_PATH if LAUNCH_PATH.is_file() else BAKED / "launch_layout_a100.json")
    return json.loads(path.read_text(encoding="utf-8"))


def sha_json(d) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def _sha(p) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_id(p) -> str:
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def worker_sha() -> str:
    """The worker's own bytes AND the job code and the wrapper it runs: a change to any of them is another worker."""
    h = hashlib.sha256()
    for name in FILES:
        h.update(name.encode() + b"\0" + (LTX_DIR / name).read_bytes())
    return h.hexdigest()


def proof(launch: dict) -> dict:
    return {"launch_sha": sha_json(launch), "worker_sha": worker_sha()}


# --- the launch file's own arithmetic ----------------------------------------------------------------------------------------

def rate_usd_h(cpu: float, memory_gib: float, gpu: str | None = None) -> float:
    from explainer_engine.cloud import modal_schedule as MS
    per_s = (MS.GPUS[gpu]["usd_s"] if gpu else 0.0) + cpu * MS.CPU_CORE_S + memory_gib * MS.MEM_GIB_S
    return round(per_s * 3600.0, 4)


def stated_rate(launch: dict) -> float:
    return float(launch["usd_per_h"][launch["gpu"]])


def cost_timeout(cap_usd: float, usd_h: float, cold_start_s: float) -> int:
    """OR-37: the function timeout comes from the cap: floor(0.9 * (cap - cold start cost) / price per hour * 3600)."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600) / usd_h * 3600)


def timeouts(launch: dict) -> tuple[int, int, int]:
    """(smoke, run, chain) function timeouts, each checked to leave work time beyond the margin and to fit its cap."""
    c, h = launch["caps"], stated_rate(launch)
    out = []
    for k in ("smoke_usd", "run_usd", "chain_usd"):
        t = cost_timeout(c[k], h, c["cold_start_s"])
        if t <= c["margin_s"] or (t + c["cold_start_s"]) * h / 3600 > c[k] + 1e-9:
            raise ValueError(f"{k}: timeout {t}s leaves no room beyond the {c['margin_s']}s end path, or does not fit the cap")
        out.append(t)
    return out[0], out[1], out[2]


def stage_timeout(launch: dict) -> int:
    s = launch["stage"]
    t = cost_timeout(s["cap_usd"], s["usd_per_h"], s["cold_start_s"])
    if t < 120:
        raise ValueError("the CPU stage window is under 120 s")
    return t


def launch_problems(launch: dict, check_table: bool = True) -> list[str]:
    bad = [f"launch.{k} is not set" for k in ("app_name", "model_repo", "model_revision", "model_files", "ltx_code", "module", "uses", "lora",
                                             "settings", "native", "smoke", "gpu", "cpu", "memory_gib", "usd_per_h", "base_image",
                                             "hf_hub_pin", "hf_out", "scaledown_window_s", "startup_timeout_s", "chain", "caps", "stage")
           if not launch.get(k)]
    if bad:
        return bad
    c = launch["caps"]
    for k in ("smoke_usd", "run_usd", "chain_usd", "ledger_line_usd", "cold_start_s", "margin_s"):
        if not isinstance(c.get(k), (int, float)) or c[k] <= 0:
            bad.append(f"caps.{k} is not set")
    if bad:
        return bad
    for k in ("smoke_usd", "run_usd", "chain_usd"):          # each rung has its own ledger file: its cap must pass that ledger's 80 % rule
        if c[k] > 0.8 * c["ledger_line_usd"] + 1e-9:
            bad.append(f"caps.{k} {c[k]} is above 80 % of the ledger line {c['ledger_line_usd']} (the ledger would refuse)")
    ceil, before = c.get("item_ceiling_usd"), c.get("item_spent_before_usd", 0.0)
    if not isinstance(ceil, (int, float)) or ceil <= 0:
        bad.append("caps.item_ceiling_usd is not set (the owner's shared ceiling, at its 80 % stop)")
    elif c["smoke_usd"] + c["run_usd"] + c["chain_usd"] + before > ceil + 1e-9:
        bad.append(f"smoke {c['smoke_usd']} + run {c['run_usd']} + chain {c['chain_usd']} + already spent {before} is above the item's "
                   f"ceiling {ceil}")
    if not (isinstance(launch["scaledown_window_s"], int) and launch["scaledown_window_s"] <= 5):
        bad.append("CH-04: scaledown_window_s is above 5 s")
    if not (30 <= launch["startup_timeout_s"] <= c["cold_start_s"]):
        bad.append("startup_timeout_s must be 30..caps.cold_start_s (a hung start bills it)")
    code = launch["ltx_code"]
    if not (code.get("repo") and re.fullmatch(r"[0-9a-f]{40}", str(code.get("commit") or ""))):
        bad.append("ltx_code needs the repo and a full 40-hex commit")
    if launch["module"] != "ltx_pipelines.ic_lora":
        bad.append("module must be ltx_pipelines.ic_lora")
    if not re.fullmatch(r"[0-9a-f]{40}", str(launch["model_revision"])):
        bad.append("model_revision is not a full revision sha")
    files = launch["model_files"]
    bad += [f"model file {f} has no sha256" for f, h in files.items() if not re.fullmatch(r"[0-9a-f]{64}", str(h))]
    bad += [f"uses.{k} is not one of the model files" for k, f in launch["uses"].items() if f not in files]
    lo = launch["lora"]
    if not (re.fullmatch(r"[0-9a-f]{40}", str(lo.get("revision"))) and re.fullmatch(r"[0-9a-f]{64}", str(lo.get("sha256")))
            and isinstance(lo.get("size"), int) and lo["size"] > 0 and lo.get("file") and lo.get("repo") and lo.get("dir")):
        bad.append("lora needs repo, file, a full revision, sha256, size and dir")
    st = launch["settings"]
    for k in ("lora_strength", "video_conditioning_strength", "image_strength"):
        if not isinstance(st.get(k), (int, float)):
            bad.append(f"settings.{k} is not set")
    if st.get("first_frame_index") != 0:
        bad.append("settings.first_frame_index must be 0: the pinned CLI refuses a negative index")
    n = launch["native"]
    if n.get("use") != [1280, 704] or n.get("fps") != 24 or n["use"] not in n.get("sizes", []):
        bad.append("CH-02: native.use must be 1280x704 at 24 fps")
    if not ((n.get("max_frames", 0) - 1) % 8 == 0 and n.get("max_frames", 0) >= 9):
        bad.append("native.max_frames must be 8k+1")
    sf = launch["smoke"].get("frames")
    if not (isinstance(sf, int) and sf >= 9 and (sf - 1) % 8 == 0 and sf <= n.get("max_frames", 0)):
        bad.append("smoke.frames must be 8k+1 and not above native.max_frames")
    if check_table:
        want = rate_usd_h(launch["cpu"], launch["memory_gib"], launch["gpu"])
        if abs(want - stated_rate(launch)) > 0.01 * want:
            bad.append(f"usd_per_h {stated_rate(launch)} is not the price table's {want} (cloud/modal_schedule)")
        s = launch["stage"]
        want = rate_usd_h(s["cpu"], s["memory_gib"])
        if abs(want - s["usd_per_h"]) > 0.01 * want:
            bad.append(f"stage.usd_per_h {s['usd_per_h']} is not the price table's {want}")
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



_SEEN_REMOTE_OPERATION_IDS: set[str] = set()


def verify_remote_approval_payload(
    approval_proof: dict | None,
    *,
    operation_mode: str,
    expected_manifest_sha256: str | None = None,
    estimated_max_usd: float | None = None,
    signing_key: str | None = None,
    registry_path: Path | None = None,
) -> dict:
    """Enforce cryptographically or registry-authenticated owner approval proof inside remote Modal workers."""
    import datetime as _dt
    import hashlib as _hashlib
    import hmac as _hmac

    if not isinstance(approval_proof, dict):
        raise RuntimeError("Remote worker refused: missing owner approval_proof payload")
    aid = approval_proof.get("approval_id")
    if not isinstance(aid, str) or not re.fullmatch(r"^cmsg_[A-Za-z0-9_-]{8,128}$", aid):
        raise RuntimeError(f"Remote worker refused: invalid approval_id {aid!r}")
    if approval_proof.get("provider") != "modal_modal1":
        raise RuntimeError(f"Remote worker refused: invalid provider {approval_proof.get('provider')!r}")
    msha = approval_proof.get("manifest_sha256")
    if not isinstance(msha, str) or not re.fullmatch(r"^[0-9a-f]{64}$", msha):
        raise RuntimeError("Remote worker refused: missing valid 64-char manifest_sha256")
    if expected_manifest_sha256 is not None and msha != expected_manifest_sha256:
        raise RuntimeError(
            f"Remote worker refused: manifest_sha256 mismatch ({msha} != {expected_manifest_sha256})"
        )
    mode = approval_proof.get("operation_mode")
    if mode != operation_mode and not (operation_mode == "modal-ltx-smoke" and mode == "modal-ltx-stage-and-smoke"):
        raise RuntimeError(f"Remote worker refused: operation_mode mismatch ({mode!r} != {operation_mode!r})")
    max_usd = approval_proof.get("max_usd")
    if isinstance(max_usd, bool) or not isinstance(max_usd, (int, float)) or not math.isfinite(max_usd) or max_usd <= 0:
        raise RuntimeError(f"Remote worker refused: invalid max_usd {max_usd!r}")
    if estimated_max_usd is not None and float(max_usd) + 1e-9 < float(estimated_max_usd):
        raise RuntimeError(
            f"Remote worker refused: approval max_usd ${float(max_usd):.4f} < required ${float(estimated_max_usd):.4f}"
        )
    ev = approval_proof.get("owner_evidence")
    if not isinstance(ev, str) or not ev.strip():
        raise RuntimeError("Remote worker refused: missing owner_evidence")
    exp_raw = approval_proof.get("expires_at")
    if not isinstance(exp_raw, str) or not exp_raw.strip():
        raise RuntimeError("Remote worker refused: missing expires_at")
    exp = _dt.datetime.fromisoformat(exp_raw)
    if exp.tzinfo is None:
        exp = exp.replace(tzinfo=_dt.UTC)
    if _dt.datetime.now(_dt.UTC) >= exp:
        raise RuntimeError(f"Remote worker refused: approval {aid!r} expired at {exp_raw}")

    # Replay protection: require unique operation_id
    op_id = approval_proof.get("operation_id")
    if not isinstance(op_id, str) or len(op_id.strip()) < 8:
        raise RuntimeError("Remote worker refused: missing unique operation_id for replay protection")
    if op_id in _SEEN_REMOTE_OPERATION_IDS:
        raise RuntimeError(f"Remote worker refused: replayed operation_id {op_id!r}")

    # Authenticity check: MUST verify either HMAC-SHA256 signature OR authoritative owner_approvals.json registry
    authenticated = False
    key = signing_key if signing_key is not None else os.environ.get("OWNER_APPROVAL_SIGNING_KEY")
    provided_hmac = approval_proof.get("approval_hmac")
    if key and isinstance(provided_hmac, str) and re.fullmatch(r"^[0-9a-f]{64}$", provided_hmac):
        canonical = {
            "approval_id": aid,
            "provider": approval_proof.get("provider"),
            "operation_mode": mode,
            "manifest_sha256": msha,
            "max_usd": round(float(max_usd), 6),
            "expires_at": exp_raw,
            "owner_evidence": ev,
            "operation_id": op_id,
        }
        msg = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
        expected_sig = _hmac.new(key.encode("utf-8"), msg, _hashlib.sha256).hexdigest()
        if _hmac.compare_digest(provided_hmac, expected_sig):
            authenticated = True
        else:
            raise RuntimeError("Remote worker refused: forged or invalid approval_hmac signature")

    if not authenticated:
        reg_p = registry_path or (Path(__file__).resolve().parents[4] / "config" / "owner_approvals.json")
        if reg_p.is_file():
            reg_data = json.loads(reg_p.read_text(encoding="utf-8"))
            reg_rec = (reg_data.get("approvals") or {}).get(aid)
            if (
                isinstance(reg_rec, dict)
                and reg_rec.get("provider") == "modal_modal1"
                and reg_rec.get("manifest_sha256") == msha
                and reg_rec.get("operation_mode") == mode
                and float(reg_rec.get("max_usd") or 0) >= float(max_usd)
                and reg_rec.get("expires_at") == exp_raw
                and reg_rec.get("owner_evidence") == ev
            ):
                authenticated = True

    if not authenticated:
        raise RuntimeError(
            "Remote worker refused: unauthenticated/forged approval_proof (neither valid HMAC signature nor matching owner_approvals.json entry)"
        )

    _SEEN_REMOTE_OPERATION_IDS.add(op_id)
    return approval_proof


def verify_worker_approval(
    env=os.environ,
    *,
    plan_sha: str,
    operation_mode: str,
    requested_usd: float,
    registry_path: Path | None = None,
) -> dict:
    """Fail-closed owner approval verification directly inside modal_layout_jobs entrypoints."""
    from explainer_engine.core import approvals

    go_val = go_gate(env=env, plan_sha=plan_sha)
    card_id = go_val.split(":", 1)[0]
    manifest_sha = str(env.get("EE_MODAL_APPROVAL_MANIFEST_SHA256") or "").strip()
    effective_mode = str(env.get("EE_MODAL_OPERATION_MODE") or operation_mode).strip()
    try:
        return approvals.verify_approval(
            card_id,
            provider="modal_modal1",
            operation_mode=effective_mode,
            manifest_sha256=manifest_sha,
            requested_usd=requested_usd,
            registry_path=registry_path,
        )
    except approvals.ApprovalError as exc:
        raise SystemExit(f"owner approval verification failed: {exc}; nothing was started") from None


def offer_problems(launch: dict, entry: str, env=os.environ, now=None) -> list[str]:
    """CH-07: a passing ``paid_offer/1`` that names THIS worker and rung and chose the card the launch runs on (``cloud/cheapest.
    offer_problems``, called, not edited)."""
    from explainer_engine.cloud import cheapest
    return [f"{r}: {why}" for r, why in cheapest.offer_problems(entry, "", env, launch, WORKER_REL, now)]


def preflight(launch: dict, *, entry: str | None = None, paid: bool = True, env=os.environ):
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
        bad += offer_problems(launch, entry or "main", env)
    if bad:
        raise SystemExit("paid preflight FAILED, nothing was started:\n" + "\n".join(bad))


def container_gate(launch: dict, baked=BAKED / "launch_layout_a100.json") -> list[str]:
    """The last line inside the container: the launch passed in is the one baked into the image; CH-02 and CH-04 on it."""
    bad = []
    if _exists(baked) and json.loads(Path(baked).read_text(encoding="utf-8")) != launch:
        bad.append("the launch passed in is not the launch file baked into the image")
    return bad + launch_problems(launch, check_table=False)


# --- ledgers (local side) ----------------------------------------------------------------------------------------------------

def reserve_launch(ledger_path: str, item: str, amount: float, line: float):
    """Reserve the launch's cap in the one ledger BEFORE the GPU function is called; a launch item that exists is refused (a repeat pays twice)."""
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
    cfg = spend_caps.load()
    has_night = isinstance((cfg.get("modal") or {}).get("night_total_usd"), (int, float))
    has_env = "modal_modal1" in ((cfg.get("orchestration_envelopes") or {}).get("services") or {})
    if not (has_night or has_env):
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
        raise SystemExit(f"NIGHT LEDGER SETTLE FAILED: {exc}") from None


def ladder_gate(rung: str, launch: dict):
    from explainer_engine.cloud import modal_run as MR
    MR.gate(MR.load_ladder(LADDER_PATH), rung, proof=proof(launch))


def record(rung: str, ok: bool, launch: dict, **info):
    from explainer_engine.cloud import modal_run as MR
    MR.record_rung(LADDER_PATH, rung, ok, **proof(launch), **info)
    if not ok:
        raise SystemExit(f"rung {rung} is red: {json.dumps(info, default=str)[:600]}")


# --- weights (CPU container) -------------------------------------------------------------------------------------------------

def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def base_root(launch: dict, vol_root=VOL) -> Path:
    return Path(vol_root) / "model" / launch["model_repo"]


def lora_path(launch: dict, vol_root=VOL) -> Path:
    return Path(vol_root) / launch["lora"]["dir"] / launch["lora"]["file"]


def check_weights(launch: dict, vol_root=VOL, *, hash_lora: bool, hash_base: bool = False) -> list[str]:
    """The files a clip needs: the five base files of ``uses`` (present, non-empty; sha256 when ``hash_base``) and the IC-LoRA
    (pinned size; sha256 when ``hash_lora``). The base was staged and hashed by W5's L2 on 2026-11-19; the paid function only checks presence."""
    bad, root = [], base_root(launch, vol_root)
    for role, f in launch["uses"].items():
        p = root / f
        if not p.is_file() or p.stat().st_size == 0:
            bad.append(f"missing base file {f}")
        elif hash_base and _sha(p) != launch["model_files"][f]:
            bad.append(f"sha256 mismatch {f}")
    lp, lo = lora_path(launch, vol_root), launch["lora"]
    if not lp.is_file():
        bad.append(f"missing IC-LoRA {lo['file']}")
    elif lp.stat().st_size != lo["size"]:
        bad.append(f"IC-LoRA size {lp.stat().st_size} is not the pinned {lo['size']}")
    elif hash_lora and _sha(lp) != lo["sha256"]:
        bad.append("IC-LoRA sha256 mismatch")
    return bad


def stage_weights(launch: dict, vol_root=VOL, download=None, *, hash_base: bool = False) -> list[str]:
    """L2 on CPU: fetch what the Volume lacks (the IC-LoRA; a base file only if missing), then verify."""
    lo, root = launch["lora"], base_root(launch, vol_root)
    lp = lora_path(launch, vol_root)
    if not lp.is_file() or lp.stat().st_size != lo["size"]:
        (download or _hf_download)(lo["repo"], lo["revision"], [lo["file"]], lp.parent)
    miss = [f for f in launch["uses"].values() if not (root / f).is_file()]
    if miss:
        (download or _hf_download)(launch["model_repo"], launch["model_revision"], miss, root)
    return check_weights(launch, vol_root, hash_lora=True, hash_base=hash_base)


def _hf_download(repo: str, revision: str, files: list[str], root: Path):
    from huggingface_hub import hf_hub_download
    for f in files:
        hf_hub_download(repo, f, revision=revision, local_dir=str(root), token=_tok())


# --- HF upload with read-back (OR-33): the same helpers as modal_ltx_jobs, kept equal by a test -------------------------------

def tmp_name(p: Path) -> Path:
    """A temp name that keeps the suffix (imageio and ffmpeg pick the format by it; delta audit N1)."""
    return p.with_name("." + p.name)


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
            api.create_commit(repo_id=HF_REPO, repo_type="dataset", operations=ops, commit_message=f"layout: {len(new)} files")
            seen.update({str(p): key for p, key in new})
            return len(new)
        except Exception as e:  # noqa: BLE001 - retried with backoff; the Volume copy is the safety net
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
    except Exception as e:  # noqa: BLE001
        return {p.name: f"not checked: {type(e).__name__}" for p in files}
    out = {}
    for p, hp in zip(files, paths):
        i = info.get(hp)
        if i is None:
            out[p.name] = "missing on HF"
            continue
        lfs = getattr(i, "lfs", None)
        want = (lfs.sha256 if hasattr(lfs, "sha256") else (lfs or {}).get("sha256")) if lfs else None
        ok = (want == _sha(p)) if want else (getattr(i, "blob_id", None) == git_blob_id(p))
        out[p.name] = "ok" if ok else "hash differs on HF"
    return out


# --- the batch (inputs) ------------------------------------------------------------------------------------------------------

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
    shutil.rmtree(dest, ignore_errors=True)
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(tar) as tf:
        tf.extractall(dest, filter="data") if sys.version_info >= (3, 12) else tf.extractall(dest)
    return dest


# --- the container's own facts ------------------------------------------------------------------------------------------------

class Deadline:
    """The in-container clock: ``left()`` seconds until the function must wrap up (the end path runs inside the margin)."""

    def __init__(self, timeout_s, margin_s, now=time.time):
        self.now, self.end = now, now() + float(timeout_s) - float(margin_s)

    def left(self) -> float:
        return self.end - self.now()


class GpuPoller:
    """nvidia-smi once a second while a clip runs: the card's peak ``memory.used`` (what the OS sees, beside torch's own counter written
    by ``ic_lora_run.py``); it also records a run the process never got to report on (an OOM kill)."""

    def __init__(self, sh=subprocess.run, every_s=1.0):
        self.sh, self.every, self.peak_mib, self.samples, self._stop = sh, every_s, 0, 0, threading.Event()
        self._t = threading.Thread(target=self._loop, daemon=True)

    def _loop(self):
        while not self._stop.is_set():
            try:
                r = self.sh(["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"], capture_output=True, text=True,
                            timeout=10)
                vals = [int(x) for x in (r.stdout or "").split() if x.strip().isdigit()]
                if vals:
                    self.peak_mib, self.samples = max(self.peak_mib, max(vals)), self.samples + 1
            except Exception:  # noqa: BLE001 - facts only
                pass
            self._stop.wait(self.every)

    def __enter__(self):
        self._t.start()
        return self

    def __exit__(self, *exc):
        self._stop.set()
        self._t.join(timeout=15)

    def facts(self) -> dict:
        return {"gpu_used_peak_gib": round(self.peak_mib / 1024, 2), "samples": self.samples}


def cgroup_peak_gib(path="/sys/fs/cgroup/memory.peak"):
    try:
        return round(int(Path(path).read_text().strip()) / GIB, 2)
    except (OSError, ValueError):
        return None


def libs() -> dict:
    """Library versions as plain strings (a TorchVersion lost the bake-off's answer on a client without torch)."""
    import importlib
    out = {"python": sys.version.split()[0]}
    for m in ("torch", "ltx_core", "ltx_pipelines", "PIL", "numpy"):
        try:
            v = getattr(importlib.import_module(m), "__version__", None)
            out[m] = None if v is None else str(v)
        except Exception:  # noqa: BLE001
            out[m] = None
    return out


def _job_code():
    """layout_job is imported from this folder both locally (package import) and in the container (folder on sys.path)."""
    try:
        from explainer_engine.training.pods.ltx import layout_job
    except ImportError:
        sys.path.insert(0, str(BAKED if _exists(BAKED) else LTX_DIR))
        import layout_job
    return layout_job


def _exists(p) -> bool:
    try:
        return Path(p).exists()
    except OSError:      # /root is not readable for a non-root user (a CI box)
        return False


def _wrapper_path() -> Path:
    """The wrapper baked into the image, else the one beside this file (an unreadable /root on a CI box is 'not baked', not a crash)."""
    return BAKED / "ic_lora_run.py" if _exists(BAKED / "ic_lora_run.py") else LTX_DIR / "ic_lora_run.py"


def claim_attempt(vol_root, key: str, now=time.time, reload=lambda: None, commit=lambda: None) -> str | None:
    """One attempt per run key on the Volume: a container that Modal re-schedules after a crash finds the marker and refuses
    (a re-run with a fresh timeout would pay twice). Returns an error text, or None when this attempt owns the key."""
    reload()
    p = Path(vol_root) / "attempts_layout" / f"{key}.json"
    p.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(p, "x", encoding="utf-8") as f:
            json.dump({"key": key, "at": round(now(), 1), "pid": os.getpid()}, f)
    except FileExistsError:
        return (f"attempt marker {p.name} exists: this run was started before; a second attempt would pay twice "
                "(feedback-modal-crash-reschedule)")
    commit()
    return None


# --- the body (inside the container) -----------------------------------------------------------------------------------------

def _clip_row(J, launch, r, pic_png, layout, out, work, deadline, sh, poller_factory, python, wrapper, now, film_line, vol_root) -> dict:
    """One clip: the CLI as its own process bounded by the time left, torch's peak from the wrapper, the card's peak from nvidia-smi."""
    sid = r["shot_id"]
    mp4 = out / f"{sid}.mp4"
    tmp = tmp_name(mp4)
    vram_json = out / f"{sid}.vram.json"
    prompt = J.compose_prompt(r, film_line)
    cmd = J.layout_cmd(launch, r, pic_png, layout, tmp, prompt, vol_root=vol_root, python=python, wrapper=wrapper, vram_json=vram_json)
    row = {"shot_id": sid, "seed": r["seed"], "hop": r.get("hop", 0), "prompt": prompt,
           "run": J.run_settings(launch, r, prompt, cmd), "frames": J.ltx_frames(float(r["seconds"]), int(r["fps"]))}
    t0 = now()
    with poller_factory() as poller, open(out / f"{sid}.log", "w") as log:
        try:
            row["rc"] = sh(cmd, stdout=log, stderr=subprocess.STDOUT, cwd=CODE_DIR if Path(CODE_DIR).is_dir() else None,
                           timeout=max(1.0, deadline.left())).returncode
        except subprocess.TimeoutExpired:
            row["rc"], row["why"] = None, "the in-container deadline came during the clip"
    row["gen_s"] = round(now() - t0, 1)
    vram = json.loads(vram_json.read_text()) if vram_json.is_file() else {}
    row["vram"] = dict(vram, **poller.facts(), cgroup_peak_gib=cgroup_peak_gib())
    if row["rc"] == 0 and tmp.is_file() and tmp.stat().st_size > 0:
        os.replace(tmp, mp4)
        row.update(sha256=_sha(mp4), state="DONE", clip=mp4.name, s_per_clip_s=round(row["gen_s"] / float(r["seconds"]), 2))
        try:
            p = J.probe_video(mp4, sh=sh) if sh is subprocess.run else J.probe_video(mp4)
            row.update(frames_out=p["frames"], size_out=[p["width"], p["height"]], fps_out=p["fps"], sound=p["audio"])
            if p["frames"] != row["frames"]:
                row["state"], row["why"] = "FAILED", f"the clip has {p['frames']} frames, {row['frames']} were asked"
        except (ValueError, OSError) as exc:
            row["state"], row["why"] = "FAILED", f"the output cannot be probed: {str(exc)[:120]}"
    else:
        row["state"] = "PARTIAL" if row["rc"] is None else "FAILED"
        tmp.unlink(missing_ok=True)
    return row


def body(spec: dict, launch: dict, *, timeout_s: int, vol_root=VOL, work=WORK, commit=lambda: None, reload=lambda: None, api=None,
         download=None, now=time.time, sh=subprocess.run, poller_factory=None, python=None, wrapper=None, probe=None,
         sleep=time.sleep, op_cls=None, baked=BAKED / "launch_layout_a100.json") -> dict:
    """The GPU function: attempt marker, weights there, the batch checked, each clip saved to the Volume and HF as soon as it is made
    (OR-33), the next clip started from a frame of the one before, then the final upload read back from HF."""
    J = _job_code()
    t_in = now()
    bad = container_gate(launch, baked)
    if bad:
        return {"state": "FAILED", "error": "refused in the container: " + "; ".join(bad)}
    kind, run_id = spec["kind"], spec["run_id"]
    err = claim_attempt(vol_root, f"{run_id}_{kind}", reload=reload, commit=commit)
    if err:
        return {"state": "FAILED", "error": err}
    unstaged = check_weights(launch, vol_root, hash_lora=False)
    if unstaged:
        return {"state": "FAILED", "error": "the weights are not staged on the Volume (run the L2 rung first)", "problems": unstaged[:8]}
    try:
        root = unpack(fetch_batch(spec, Path(work) / "dl", download), Path(work) / "batch")
        job = json.loads((root / "job.json").read_text(encoding="utf-8"))
    except (SystemExit, OSError, ValueError, tarfile.TarError) as exc:
        return {"state": "FAILED", "error": str(exc)[:300]}
    problems, warnings = J.job_problems(job, root, launch, probe=probe or J.probe_video, smoke=kind == "smoke")
    if kind == "smoke" and J.ltx_frames(float(job.get("seconds") or 0), int(job.get("fps") or 24)) != launch["smoke"]["frames"]:
        problems.append(f"the smoke job must be {launch['smoke']['frames']} frames (launch.smoke.frames)")
    if kind == "smoke" and job.get("chain"):
        problems.append("the smoke job is one clip, no chain")
    if problems:
        return {"state": "FAILED", "error": "the job is refused in the container", "problems": problems[:12], "warnings": warnings}
    deadline = Deadline(timeout_s, launch["caps"]["margin_s"], now=now)
    out = Path(work) / "out" / run_id / kind
    out.mkdir(parents=True, exist_ok=True)
    prefix = f"{launch['hf_out']}/{run_id}/{kind}"
    sent: dict = {}
    m = {"run_id": run_id, "kind": kind, "gpu": launch["gpu"], "launch_sha": sha_json(launch), "worker_sha": spec.get("worker_sha"),
         "batch_sha": spec["batch_sha"], "warnings": warnings, "error": None, "state": "FAILED"}
    poller_factory = poller_factory or (lambda: GpuPoller())
    wrapper = wrapper if wrapper is not None else _wrapper_path()
    rows: list[dict] = []

    def to_volume():
        try:
            shutil.copytree(out, Path(vol_root) / VOL_OUT / run_id / kind, dirs_exist_ok=True)
            commit()
        except Exception as e:  # noqa: BLE001
            print("volume copy failed", repr(e)[:200], flush=True)

    def write_record():
        m["clips"] = rows
        (out / "layout_record.json").write_text(json.dumps(m, default=str, indent=1))

    def save_now():
        """After every finished clip: the record so far, the Volume copy, one short HF round (the clip leaves the container)."""
        write_record()
        to_volume()
        if api is not None:
            upload_round(api, out, prefix, sent, sleep=sleep, op=op_cls, budget_s=min(SAVE_BUDGET_S, max(0.0, deadline.left())))

    try:
        from PIL import Image
        all_rows = J.rows(job)
        prev, prev_row = None, None
        for r in all_rows:
            sid = r["shot_id"]
            sibling = J.is_sibling(r)
            if prev is not None:
                if prev.get("state") != "DONE":
                    break
                need = 1.15 * float(prev["gen_s"]) * max(1.0, float(r["seconds"]) / float(prev_row["seconds"]))
                if deadline.left() < need:
                    rows.append({"shot_id": sid, "state": "PARTIAL", "why": f"{deadline.left():.0f} s left, the clip needs ~{need:.0f} s: not started"})
                    break
                cont = r.get("continue_frame") or {}
                hand = {"frame": -1} if sibling else J.handover_frame(out / prev["clip"], int(prev["frames"]), int(r["fps"]), cont, launch, sh=sh,
                                        speech_end_s=prev_row.get("speech_end_s"), tail_s=prev_row.get("speech_tail_s"))
                if hand["frame"] is None:
                    rows.append({"shot_id": sid, "state": "FAILED", "why": hand["why"] + "; not started", "handover": hand})
                    break
                if sibling:
                    src_png, handover = root / job["first_picture"], None
                else:
                    png = out / f"{sid}.first.png"
                    J.frame_png(out / prev["clip"], hand["frame"], png, sh=sh, crop=cont.get("crop"))
                    src_png, handover = png, {"clip": prev["clip"], "frame": hand["frame"], "pick": hand["pick"], "crop": cont.get("crop"),
                                              "window": hand.get("window"), "after": hand.get("after")}
            else:
                src_png, handover = root / job["first_picture"], None
            fitted = Path(work) / "tmp" / f"{sid}_{r['width']}x{r['height']}.png"
            fitted.parent.mkdir(parents=True, exist_ok=True)
            with Image.open(src_png) as im:
                J.fit_picture(im, r["width"], r["height"]).save(fitted)
            row = _clip_row(J, launch, r, fitted, root / r["layout_mp4"], out, work, deadline, sh, poller_factory, python, wrapper, now,
                            r.get("film_line", job.get("film_line")), vol_root)
            row["first_picture"] = {"source": "job" if handover is None else "previous clip's frame", "sha256": _sha(fitted),
                                    "handover": handover}
            rows.append(row)
            prev, prev_row = row, r
            print("clip", sid, row.get("state"), f"gen {row.get('gen_s')} s", flush=True)
            if row.get("state") == "DONE":
                save_now()
        m["state"] = "DONE" if rows and all(x.get("state") == "DONE" for x in rows) and len(rows) == len(all_rows) else (
            "PARTIAL" if any(x.get("state") == "DONE" for x in rows) else "FAILED")
    except Exception as e:  # noqa: BLE001 - one attempt: the failure is written, copied and returned
        m.update(state="FAILED", error=f"{type(e).__name__}: {str(e)[:300]}")
    m.update(body_s=round(now() - t_in, 1), libs=libs())
    write_record()
    to_volume()                                  # the Volume first, then the final upload
    if api is not None:
        upload_round(api, out, prefix, sent, final=True, sleep=sleep, op=op_cls,
                     budget_s=max(0.0, deadline.left() + launch["caps"]["margin_s"] - 30))
        m["verified"] = verify_uploads(api, out, prefix)
        if m["state"] == "DONE" and any(v != "ok" for v in m["verified"].values()):
            m["state"] = "UPLOAD_UNVERIFIED"
        (out / "verified.json").write_text(json.dumps(m["verified"]))
        write_record()
        to_volume()
        upload_round(api, out, prefix, sent, final=True, sleep=sleep, op=op_cls, budget_s=20)
    m["body_s"] = round(now() - t_in, 1)
    write_record()
    return json.loads(json.dumps(m, default=str))   # plain JSON only, never a library object


# --- the Modal app -----------------------------------------------------------------------------------------------------------

LAUNCH = load_launch()

if modal is not None:
    app = modal.App(LAUNCH.get("app_name") or "ee-layout-jobs")
    vol = modal.Volume.from_name("ee-weights", version=2)
    _code = LAUNCH["ltx_code"]
    # the image recipe of the LTX worker (the bake-off's, same base image and LTX-2 commit); this folder's three files and the launch are added
    image = (modal.Image.from_registry(LAUNCH["base_image"], add_python="3.12")
             .apt_install("ffmpeg", "git")
             .run_commands(f'pip install -q "huggingface_hub=={LAUNCH["hf_hub_pin"]}"',
                           f"git clone -q {_code['repo']} {CODE_DIR} && git -C {CODE_DIR} checkout -q {_code['commit']} && "
                           f"pip install -q -e {CODE_DIR}/packages/ltx-core -e {CODE_DIR}/packages/ltx-pipelines")
             .add_local_file(str(LAUNCH_PATH), str(BAKED / "launch_layout_a100.json"))
             .add_local_file(str(LTX_DIR / "layout_job.py"), str(BAKED / "layout_job.py"))
             .add_local_file(str(LTX_DIR / "ic_lora_run.py"), str(BAKED / "ic_lora_run.py")))
    secrets = [modal.Secret.from_name(SECRET_NAME)]
    _st = LAUNCH["stage"]
    CPU_KW = dict(image=image, cpu=(2.0, 2.0), retries=0, secrets=secrets)

    @app.function(memory=(4096, 4096), timeout=300, **CPU_KW)
    def env_check():
        _tok()
        bad, info = [], libs()
        for mod in ("torch", "ltx_core", "ltx_pipelines.ic_lora", "PIL", "numpy"):
            try:
                __import__(mod)
            except Exception as exc:  # noqa: BLE001
                bad.append(f"{mod}: {type(exc).__name__}: {str(exc)[:120]}")
        for tool in ("ffmpeg", "ffprobe"):
            if not shutil.which(tool):
                bad.append(f"{tool} is not on the PATH")
        return {"problems": bad, **{k: v for k, v in info.items()}}

    @app.function(cpu=(float(_st["cpu"]),) * 2, memory=(_st["memory_gib"] * 1024,) * 2, timeout=stage_timeout(LAUNCH), volumes={VOL: vol},
                  image=image, retries=0, secrets=secrets)
    def weights_stage(launch: dict, hash_base: bool = False, approval_proof: dict | None = None):
        verify_remote_approval_payload(approval_proof, operation_mode="modal-layout-weights")
        bad = stage_weights(launch, hash_base=hash_base)
        vol.commit()
        return bad

    _t_smoke, _t_run, _t_chain = timeouts(LAUNCH)
    _gpu_kw = dict(image=image, gpu=LAUNCH["gpu"], cpu=(float(LAUNCH["cpu"]),) * 2, memory=(LAUNCH["memory_gib"] * 1024,) * 2, retries=0,
                   volumes={VOL: vol}, secrets=secrets, scaledown_window=LAUNCH["scaledown_window_s"],
                   startup_timeout=LAUNCH["startup_timeout_s"], max_containers=1)

    def _remote(spec, launch, timeout_s, *, operation_mode: str = "modal-layout-smoke"):
        verify_remote_approval_payload(spec.get("approval_proof"), operation_mode=operation_mode)
        from huggingface_hub import HfApi
        return body(spec, launch, timeout_s=timeout_s, commit=vol.commit, reload=vol.reload, api=HfApi(token=_tok()))

    @app.function(timeout=_t_smoke, name="layout_smoke", **_gpu_kw)
    def smoke_fn(spec: dict, launch: dict):
        return _remote(spec, launch, _t_smoke, operation_mode="modal-layout-smoke")

    @app.function(timeout=_t_run, name="layout_main", **_gpu_kw)
    def main_fn(spec: dict, launch: dict):
        return _remote(spec, launch, _t_run, operation_mode="modal-layout-main")

    @app.function(timeout=_t_chain, name="layout_chain", **_gpu_kw)
    def chain_fn(spec: dict, launch: dict):
        return _remote(spec, launch, _t_chain, operation_mode="modal-layout-chain")

    def _spec(plan: str, batch: str, kind: str, cap: float) -> dict:
        plan_sha, bsha = _sha(plan), _sha(batch)
        return {"kind": kind, "cap_usd": cap, "plan_sha256": plan_sha, "run_id": f"{plan_sha[:12]}_{sha_json(LAUNCH)[:12]}",
                "batch_sha": bsha, "batch_path": f"code/layout/batch-{bsha}.tar.gz", "launch_sha": sha_json(LAUNCH),
                "worker_sha": worker_sha(), "nonce": uuid.uuid4().hex[:12]}

    def _batch_on_hf(spec: dict):
        from huggingface_hub import HfApi
        info = HfApi(token=_tok()).get_paths_info(HF_REPO, [spec["batch_path"]], repo_type="dataset")
        if not info:
            raise SystemExit(f"{spec['batch_path']} is not on HF: upload the batch first (free); nothing was started")

    @app.local_entrypoint()
    def check():
        """L1 (CPU): the launch, the token pair, the image imports."""
        preflight(LAUNCH, paid=False)
        ladder_gate("L1", LAUNCH)
        res = env_check.remote()
        print("env_check", res["problems"] or "imports ok", {k: v for k, v in res.items() if k != "problems"})
        record("L1", not res["problems"], LAUNCH, missing=res["problems"], versions={k: v for k, v in res.items() if k != "problems"})

    @app.local_entrypoint()
    def weights(plan: str = "", hash_base: bool = False):
        """L2 (CPU, a few cents, capped by ``launch.stage.cap_usd``): the IC-LoRA onto the Volume, every pinned file checked. Never on the GPU."""
        preflight(LAUNCH, paid=False)
        plan_sha = _sha(plan)
        stage_cap = float((LAUNCH.get("stage") or {}).get("cap_usd", 0.32))
        approval_proof = verify_worker_approval(plan_sha=plan_sha, operation_mode="modal-layout-weights", requested_usd=stage_cap)
        print("GO", go_gate(plan_sha=plan_sha), "stage timeout", stage_timeout(LAUNCH), "s", flush=True)
        ladder_gate("L2", LAUNCH)
        item = f"layout_weights_{plan_sha[:12]}"
        night_reserve(item, stage_cap, "L2 layout weights stage")
        t0 = time.time()
        try:
            res = weights_stage.remote(LAUNCH, hash_base, approval_proof=approval_proof)
        finally:
            night_settle(item, round((time.time() - t0) * 0.32 / 3600.0, 4))
        print("weights", res or "IC-LoRA staged, every pinned file present, hashes match")
        record("L2", not res, LAUNCH, problems=res, hash_base=bool(hash_base))

    def _launch(plan: str, ledger: str, batch: str, rung: str, kind: str):
        entry = kind                                   # the entry, the cap and the function carry the kind's name
        preflight(LAUNCH, entry=entry)
        cap = LAUNCH["caps"][{"smoke": "smoke_usd", "main": "run_usd", "chain": "chain_usd"}[kind]]
        t = {"smoke": _t_smoke, "main": _t_run, "chain": _t_chain}[kind]
        plan_sha = _sha(plan)
        hard_est = round((t + LAUNCH["caps"]["cold_start_s"]) * stated_rate(LAUNCH) / 3600, 4)
        approval_proof = verify_worker_approval(plan_sha=plan_sha, operation_mode=f"modal-layout-{kind}", requested_usd=hard_est)
        print("GO", go_gate(plan_sha=plan_sha), "timeout", t, "s on", LAUNCH["gpu"], flush=True)
        ladder_gate(rung, LAUNCH)
        spec = dict(_spec(plan, batch, kind, cap), approval_proof=approval_proof)
        _batch_on_hf(spec)
        item = f"layout_{kind}_{spec['run_id']}"
        run = reserve_launch(ledger, item, cap, LAUNCH["caps"]["ledger_line_usd"])
        hard = round((t + LAUNCH["caps"]["cold_start_s"]) * stated_rate(LAUNCH) / 3600, 4)
        night_reserve(item, hard, f"layout {kind}")
        t0, res = time.time(), None
        try:
            res = {"smoke": smoke_fn, "main": main_fn, "chain": chain_fn}[kind].remote(spec, LAUNCH)
        finally:
            wall = time.time() - t0
            usd = settle_launch(run, item, wall, stated_rate(LAUNCH))
            night_settle(item, usd)
            print("settled", usd, "USD for", round(wall, 1), "s", flush=True)
        print("result", json.dumps(res, default=str))
        return res

    @app.local_entrypoint()
    def smoke(plan: str = "", ledger: str = "", batch: str = ""):
        """L3 (GPU, tiny cap): the smallest clip; memory (torch and nvidia-smi peaks, host RSS), seconds and sound measured."""
        res = _launch(plan, ledger, batch, "L3", "smoke")
        ok = res.get("state") == "DONE"
        c = (res.get("clips") or [{}])[0]
        record("L3", ok, LAUNCH, measured={"gpu": LAUNCH["gpu"], "body_s": res.get("body_s"), "gen_s": c.get("gen_s"), "vram": c.get("vram"),
                                           "sound": c.get("sound")} if ok else None,
               result={k: res.get(k) for k in ("state", "error", "problems")})

    @app.local_entrypoint()
    def main(plan: str = "", ledger: str = "", batch: str = ""):
        """L4 (GPU, the run's cap): the job's chain, every clip saved and read back from HF."""
        res = _launch(plan, ledger, batch, "L4", "main")
        if res.get("state") != "DONE":
            print(LAYOUT_FAILED, flush=True)
            raise SystemExit(4)

    @app.local_entrypoint()
    def chain(plan: str = "", ledger: str = "", batch: str = ""):
        """T3 (GPU, ``caps.chain_usd``): one scene, each clip from a frame of the one before; its own launch after L4 is green."""
        res = _launch(plan, ledger, batch, "L4", "chain")
        if res.get("state") != "DONE":
            print(LAYOUT_FAILED, flush=True)
            raise SystemExit(4)
