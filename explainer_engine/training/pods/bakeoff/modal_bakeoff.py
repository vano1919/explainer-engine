"""The v4.3 video bake-off (the creator, 2026-11-12 15:01 UTC; variants 1, 4, 5 at 15:12 UTC): one 10 s dialogue shot and one
10 s action shot from the approved style pictures, made by each chosen video model on Modal, so price and quality are measured
side by side before the episode's model is chosen. The plan is data: ``plan_v43.json`` (shots, pinned weights with every
file's sha256, the variants with their settings, GPU, estimate and cap).

    EE_MODAL_GO=<cmsg_id>:<go sha> modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::check
    EE_MODAL_GO=<cmsg_id>:<go sha> modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::stage
    EE_MODAL_GO=<cmsg_id>:<go sha> modal run explainer_engine/training/pods/bakeoff/modal_bakeoff.py::run --variant <id>

``<go sha>`` = ``go_sha()``: sha256 over the plan's and this worker's bytes, [:12]; any change to either needs a new GO. Each
run is longer than a foreground Bash call: it is launched as a tracked background task of the session (RULE-R1).

Money (Fable OR-34 audit 2026-11-12, A1, A3, A5):
* one ``core/ledger.Run`` (the plan's ``ledger``) with the plan's total as its ``modal`` cap: ``run`` reserves the variant's cap
  before it is sent and settles it from the measured wall seconds after; a lost answer keeps the reservation;
* ``run`` refuses a variant that already has a record on HF or in the ledger unless ``--again "<reason>"`` is given;
* the function ends on time by itself (a step callback / a subprocess timeout raises before the deadline, and a clip that cannot
  finish in the time left is not started: PARTIAL), never by killing its process, because Modal reschedules a crashed
  container whatever ``retries`` says; Modal's own timeout (derived from the cap, OR-37) stays the last wall;
* an attempt guard: the function's first act is to write ``attempt_<nonce>`` for its run on the Volume; a rescheduled input
  finds it and returns ``REFUSED_SECOND_ATTEMPT`` in seconds;
* CPU and memory are requested with their limits equal (billed at the higher of request and use);
* ``stage`` (CPU) downloads only missing pinned files, checks every sha256 and writes a stamp per weight set; ``run`` checks the
  stamp and the sizes only and never downloads or re-hashes weights on the GPU.

Outputs (OR-33, audit A2): every clip is written as it is made (``<shot>.clip<N>.mp4``, then the joined ``<shot>.mp4``); a
batched uploader (one commit per round, backoff, an exception-safe loop) sends the run's folder to HF every 30 s; after the
last flush each file's HF sha256 (LFS) or git blob id is read back and compared, and ``verified.json`` says which made it. The
state is DONE only when every file is verified. The Volume keeps a second copy on every path.

Wan makes 5 s at most per clip, so a 10 s Wan shot is two clips: the second starts from the first clip's frame[-5] with the
shot's ``prompt_2`` (audit B2), and the join keeps the first clip up to that frame and drops its last five (D-125
WAN-CHAIN-MINUS-5, ``wan_optimizer.compute_continuation_splice_spec``: the anchor frame is shown once, as the second clip's frame
0). LTX makes the 10 s (241 frames at 24 fps) in one clip, with its own sound."""
import hashlib, json, os, re, subprocess, sys, threading, time, traceback, uuid
from pathlib import Path
try:
    import modal
except ImportError:
    modal = None

PLAN_PATH = Path(__file__).with_name("plan_v43.json")
BASE_IMAGE = "ghcr.io/vano1919/tmr-pod@sha256:6852f3d9e49de298606baf19fada5ee57a32cc74f3bef8b8f88ed35e890b68c0"
DIFFUSERS = "git+https://github.com/huggingface/diffusers@d8c1b13c756df0059bcdb6e477a1eafcd502098d"
LTX2 = ("https://github.com/Lightricks/LTX-2.git", "e98f6d927d83c92ef2be6aec76c8440b19306e39")
PIP = {"huggingface_hub": "1.33.0", "transformers": "5.21.0", "accelerate": "1.15.0", "peft": "0.21.2"}
SECRET_NAME = "huggingface-secret"
GO = re.compile(r"^(cmsg_\w+):([0-9a-f]{12})$")
FAILED = "BAKEOFF_FAILED"
OUT_ROOT = Path("/workspace/out")
VOL_OUT = Path("/w/out_bakeoff")
H = re.compile(r"^[0-9a-f]{64}$")
ENTRIES = ("check", "stage", "run")     # the only entrypoints a session may call (cloud/hooks.py holds it)
MARGIN_S = 150                          # what the end of a run needs after the last clip: export, final upload, HF check, Volume
# Modal list prices (modal.com/pricing, read 2026-11-12; equal to cloud/modal_schedule.py of 2026-11-07, held by a test)
USD_S = {"H100": 0.001097, "A100-80GB": 0.000694, "L40S": 0.000542}
CPU_CORE_S, MEM_GIB_S = 0.0000131, 0.00000222


class DeadlineHit(RuntimeError):
    """The in-container deadline: raised inside the work so the normal end path writes, uploads and returns (audit A1)."""


def load_plan(path=PLAN_PATH) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def plan_sha(path=PLAN_PATH) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def worker_sha() -> str:
    return hashlib.sha256(Path(__file__).read_bytes()).hexdigest()


def go_sha(plan_hex=None, worker_hex=None) -> str:
    """What the creator's GO binds (audit A4): the plan's AND the worker's bytes."""
    return hashlib.sha256(((plan_hex or plan_sha()) + (worker_hex or worker_sha())).encode()).hexdigest()


def usd_per_h(gpu, cpu, memory_gib) -> float:
    return round(((USD_S[gpu.rstrip("!")] if gpu else 0.0) + cpu * CPU_CORE_S + memory_gib * MEM_GIB_S) * 3600.0, 4)


def cost_timeout(cap_usd, usd_h, cold_start_s):
    """OR-37: floor(0.9 * (cap - the cold start's cost) / price per hour * 3600); never set by hand."""
    return int(0.9 * (cap_usd - cold_start_s * usd_h / 3600.0) / usd_h * 3600.0)


def variant(plan, vid) -> dict:
    for v in plan["variants"]:
        if v["id"] == vid:
            return v
    raise SystemExit(f"no variant {vid!r} in the plan; nothing was started")


def rate_of(v) -> float:
    return usd_per_h(v["gpu"], v["cpu"], v["memory_gib"])


def timeout_of(plan, v) -> int:
    t = cost_timeout(v["cap_usd"], rate_of(v), plan["cold_start_s"])
    if t <= MARGIN_S + 60:
        raise SystemExit(f"{v['id']}: the cap ${v['cap_usd']} does not cover the cold start; nothing was started")
    return t


def stage_timeout(plan) -> int:
    s = plan["stage"]
    return min(int(s["timeout_s"]), cost_timeout(s["cap_usd"], usd_per_h(None, s["cpu"], s["memory_gib"]), 0))


def frames_ok(v) -> bool:
    """LTX takes 8k+1 frames and sizes divisible by 64 (two stages at half size); Wan 4k+1 frames and sizes divisible by 16."""
    f, w, h = v["frames"], v["width"], v["height"]
    if v["family"] == "ltx":
        return (f - 1) % 8 == 0 and w % 64 == 0 and h % 64 == 0
    return (f - 1) % 4 == 0 and w % 16 == 0 and h % 16 == 0


def chained_frames(v) -> int:
    """Frames of the joined shot: every clip but the last without its last ``chain_back`` frames, then the last clip whole."""
    n, back = v["frames"], v.get("chain_back", 5)
    return n * v["clips"] - back * (v["clips"] - 1)


def shot_seconds(v) -> float:
    return chained_frames(v) / v["fps"]


def clip_prompt(shot, c) -> str:
    """Clip 1 of a shot gets ``prompt``, every chained clip after it ``prompt_2`` (audit B2)."""
    return shot["prompt"] if c == 0 else (shot.get("prompt_2") or shot["prompt"])


def plan_problems(plan) -> list:
    """Everything that keeps the plan from a paid call: pins, sizes, lengths, caps, the total under its cap."""
    out = []
    for wid, w in plan["weights"].items():
        if not re.match(r"^[0-9a-f]{40}$", str(w.get("revision") or "")):
            out.append(f"weights {wid}: no pinned revision")
        out += [f"weights {wid}: {f} has no sha256" for f, h in (w.get("files") or {}).items() if not H.match(str(h))]
        if not w.get("files"):
            out.append(f"weights {wid}: no files")
    for s in plan["shots"]:
        if not H.match(str(s.get("sha256") or "")):
            out.append(f"shot {s['id']}: the picture has no sha256")
        if not str(s.get("prompt") or "").strip():
            out.append(f"shot {s['id']}: no prompt")
    ids = [v["id"] for v in plan["variants"]]
    if len(set(ids)) != len(ids):
        out.append("two variants share an id")
    if sorted(plan.get("run_order") or []) != sorted(ids):
        out.append("run_order must name every variant once")
    if not (plan.get("ledger") or {}).get("path") or (plan.get("ledger") or {}).get("service") != "modal":
        out.append("the plan names no modal ledger")
    for v in plan["variants"]:
        if v["family"] not in ("ltx", "wan"):
            out.append(f"{v['id']}: family must be ltx or wan")
        if not frames_ok(v):
            out.append(f"{v['id']}: frames/size do not fit the model's grid")
        miss = [w for w in v["weights"] if w not in plan["weights"]]
        if miss:
            out.append(f"{v['id']}: unknown weights {miss}")
        for k, f in list((v.get("uses") or {}).items()) + list((v.get("lora") or {}).items()):
            if not any(f in plan["weights"][w]["files"] for w in v["weights"] if w in plan["weights"]):
                out.append(f"{v['id']}: {k} {f} is not a pinned file")
        if v["family"] == "wan" and v["clips"] > 1 and not all(s.get("prompt_2") for s in plan["shots"]):
            out.append(f"{v['id']}: a chained Wan shot needs prompt_2 on every shot")
        if not 9.5 <= shot_seconds(v) <= 10.5:
            out.append(f"{v['id']}: the shot is {shot_seconds(v):.2f} s, not 10 s")
        if v.get("gpu") not in USD_S:
            out.append(f"{v['id']}: unknown GPU {v.get('gpu')}")
        elif not (0 < v["estimate_usd"] <= v["cap_usd"]):
            out.append(f"{v['id']}: the estimate must be above 0 and under the cap")
        else:
            try:
                timeout_of(plan, v)
            except SystemExit as exc:
                out.append(str(exc))
    total = sum(v["cap_usd"] for v in plan["variants"]) + plan["stage"]["cap_usd"]
    if total > plan["total_cap_usd"] + 1e-9:
        out.append(f"the caps add up to ${total:g}, past the plan's total ${plan['total_cap_usd']:g}")
    return out


def run_id(plan_sha_hex: str, worker_hex: str) -> str:
    return f"{plan_sha_hex[:12]}_{worker_hex[:12]}"


def go_gate(env=os.environ, sha=None):
    """EE_MODAL_GO = ``<the creator's message id>:<go_sha()[:12]>``: his yes binds this plan's and this worker's bytes."""
    m = GO.match(str(env.get("EE_MODAL_GO") or ""))
    if not m:
        raise SystemExit("EE_MODAL_GO must be '<the creator's message id>:<go sha[:12]>'; nothing was started")
    if sha is not None and m.group(2) != sha[:12]:
        raise SystemExit("EE_MODAL_GO names another plan or worker than the ones on disk; nothing was started")
    return m.group(1)


def token_for(card, sha) -> str:
    """What the local entrypoint hands the remote function: a direct call of the function without it returns at once."""
    return f"{card}:{sha[:12]}"


def token_ok(token, sha) -> bool:
    m = GO.match(str(token or ""))
    return bool(m) and m.group(2) == sha[:12]


def preflight(plan, env=os.environ, line=None) -> None:
    """Free, local, before any call: the plan holds; each cap stays under the creator's per-run Modal line and the plan's total
    under its ``tests_total_usd``."""
    bad = plan_problems(plan)
    if line is None:
        try:
            from explainer_engine.core import spend_caps
            line = spend_caps.modal()
        except Exception as exc:  # noqa: BLE001 - no line = a zero budget
            bad.append(f"no Modal line in config/spend_caps.json ({type(exc).__name__}: {exc})")
    if line is not None:
        per_run = float(line.get("per_run_usd") or 0.0)
        bad += [f"{v['id']}: cap ${v['cap_usd']:g} is above the creator's ${per_run:g} per run" for v in plan["variants"]
                if v["cap_usd"] > per_run + 1e-9]
        total = float(line.get("tests_total_usd") or 0.0)
        if plan["total_cap_usd"] > total + 1e-9:
            bad.append(f"the plan's total ${plan['total_cap_usd']:g} is above the creator's tests_total_usd ${total:g}")
    if bad:
        raise SystemExit("bake-off preflight FAILED, nothing was started:\n" + "\n".join(bad))


# --- the ledger and the repeat guard (local, audit A3) --------------------------------------------------------------------------

def open_ledger(plan, path=None):
    from explainer_engine.core.ledger import Run
    led = plan["ledger"]
    Path(path or led["path"]).parent.mkdir(parents=True, exist_ok=True)
    return Run.open(Path(path or led["path"]), caps={led["service"]: float(plan["total_cap_usd"])}, plan=plan["id"])


def ledger_item(rid, vid) -> str:
    return f"bakeoff/{rid}/{vid}"


def repeat_reason(plan, rid, vid, ledger_run, hf_has=None) -> str | None:
    """Why a start of ``vid`` would repeat paid work: a ledger reservation for this run and variant, or a record on HF."""
    item = ledger_item(rid, vid)
    if any(k == item or k.startswith(item + "/") for k in ledger_run.data.get("reserved", {})):
        return f"the ledger already holds {item}"
    base = f"{plan['hf_out']}/{rid}/{vid}"
    for f in ("measured.json", "beat.json"):
        if hf_has is not None and hf_has(f"{base}/{f}"):
            return f"HF already has {base}/{f}"
    return None


def reserve(plan, v, rid, ledger_run, nonce) -> str:
    item = f"{ledger_item(rid, v['id'])}/{nonce}"
    ledger_run.reserve(plan["ledger"]["service"], float(v["cap_usd"]), item)
    return item


def settle(plan, v, item, ledger_run, wall_s) -> float:
    """The measured wall seconds of the call (start-up included, audit A5d) at the dated price; recorded even past the cap."""
    usd = round(float(wall_s) * rate_of(v) / 3600.0, 4)
    ledger_run.settle(plan["ledger"]["service"], item, usd)
    return usd


# --- pictures and frames (container and tests) ---------------------------------------------------------------------------------

def fit_picture(img, width, height):
    """Centre-crop to the clip's aspect, then Lanczos to its size (a PIL image in, a PIL image out)."""
    from PIL import Image
    w, h = img.size
    if w * height > h * width:
        cw, ch = round(h * width / height), h
    else:
        cw, ch = w, round(w * height / width)
    left, top = (w - cw) // 2, (h - ch) // 2
    return img.convert("RGB").crop((left, top, left + cw, top + ch)).resize((width, height), Image.LANCZOS)


def join_clips(clips, back=5):
    """Chained clips into one shot: the next clip starts from frame[-back] of the one before, so every clip but the last loses
    its last ``back`` frames (that frame included; it comes back as the next clip's frame 0, never shown twice)."""
    out = []
    for i, c in enumerate(clips):
        out += list(c[:len(c) - back]) if i < len(clips) - 1 else list(c)
    return out


class Deadline:
    """The in-container clock (audit A1): ``left()`` seconds until the function must be wrapping up; ``check()`` raises
    ``DeadlineHit``; ``fits(seconds)`` says whether a piece of work that took ``seconds`` last time still fits."""

    def __init__(self, timeout_s, margin_s=MARGIN_S, now=time.time):
        self.now, self.end = now, now() + float(timeout_s) - float(margin_s)

    def left(self) -> float:
        return self.end - self.now()

    def check(self):
        if self.left() <= 0:
            raise DeadlineHit("the in-container deadline came; the run ends cleanly with what it has")

    def fits(self, seconds) -> bool:
        return seconds is None or self.left() > float(seconds) * 1.1


# --- in the container --------------------------------------------------------------------------------------------------------

def _tok():
    t = os.environ.get("HF_TOKEN") or os.environ.get("HUGGING_FACE_HUB_TOKEN")
    if not t:
        raise SystemExit("the Modal secret has no HF_TOKEN")
    return t


def _sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


def git_blob_id(p) -> str:
    """The git object id HF reports for a small (non-LFS) file."""
    data = Path(p).read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def weights_root(w, vol_root="/w"):
    return Path(vol_root) / "model" / w["repo"]


def files_hash(w) -> str:
    return hashlib.sha256(json.dumps({"revision": w["revision"], "files": w["files"]}, sort_keys=True).encode()).hexdigest()


def stamp_path(w, vol_root="/w"):
    return weights_root(w, vol_root) / ".bakeoff_verified.json"


def check_weights(w, vol_root="/w"):
    """The full check (stage, on the CPU): every pinned file there with its sha256."""
    root, bad = weights_root(w, vol_root), []
    for f, want in w["files"].items():
        p = root / f
        if not p.is_file():
            bad.append(f"missing {w['repo']}/{f}")
        elif _sha(p) != want:
            bad.append(f"sha256 mismatch {w['repo']}/{f}: delete it on the Volume and stage again")
    return bad


def stamp_ok(w, vol_root="/w"):
    """The cheap check (run, on the GPU, audit A5a): the stage's stamp names this exact file set, every file has its size."""
    p = stamp_path(w, vol_root)
    if not p.is_file():
        return [f"{w['repo']}: not staged (no stamp); run ::stage first"]
    try:
        st = json.loads(p.read_text())
    except ValueError:
        return [f"{w['repo']}: the stamp is unreadable; run ::stage again"]
    if st.get("files_hash") != files_hash(w):
        return [f"{w['repo']}: the stamp is of another file set; run ::stage again"]
    root = weights_root(w, vol_root)
    return [f"{w['repo']}/{f}: size differs from the stamp" for f, n in (st.get("sizes") or {}).items()
            if not (root / f).is_file() or (root / f).stat().st_size != n] + \
           [f"{w['repo']}/{f}: not in the stamp" for f in w["files"] if f not in (st.get("sizes") or {})]


def stage_weights(plan, vol_root="/w", download=None):
    """Every pinned file still missing on the Volume, at its pinned revision, then every sha256; a stamp per clean set."""
    bad = []
    for w in plan["weights"].values():
        root = weights_root(w, vol_root)
        miss = [f for f in w["files"] if not (root / f).is_file()]
        if miss:
            (download or _hf_download)(w["repo"], w["revision"], miss, root)
        b = check_weights(w, vol_root)
        if not b:
            stamp_path(w, vol_root).write_text(json.dumps({"files_hash": files_hash(w), "revision": w["revision"],
                                                           "sizes": {f: (root / f).stat().st_size for f in w["files"]}}))
        bad += b
    return bad


def _hf_download(repo, revision, files, root):
    from huggingface_hub import snapshot_download
    snapshot_download(repo_id=repo, revision=revision, allow_patterns=list(files), local_dir=str(root), token=_tok())


def beat(out, **kw):
    (Path(out) / "beat.json").write_text(json.dumps(dict(kw, at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))))


def _files(root):
    """The run folder's files as (path, key); a file that vanishes while it is listed is skipped, never fatal (audit A2)."""
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


def upload_round(api, root, hf_prefix, repo, seen: dict, final=False, sleep=time.sleep, op=None) -> int:
    """One batched commit of every new or changed file (the Wan worker's lesson: one commit per round, backoff, more tries at
    the final flush); returns the number sent, 0 when nothing was new or every try failed."""
    new = [(p, k) for p, k in _files(root) if seen.get(str(p)) != k]
    if not new:
        return 0
    if op is None:
        from huggingface_hub import CommitOperationAdd as op
    ops = [op(path_in_repo=f"{hf_prefix}/{p.relative_to(root).as_posix()}", path_or_fileobj=str(p)) for p, _ in new]
    for k in range(6 if final else 2):
        try:
            api.create_commit(repo_id=repo, repo_type="dataset", operations=ops, commit_message=f"bakeoff: {len(new)} files")
            seen.update({str(p): key for p, key in new})
            return len(new)
        except Exception as e:  # noqa: BLE001 - a 429/5xx is retried with backoff; the Volume copy is the safety net
            print("upload failed", repr(e)[:160], flush=True)
            sleep(15.0 * 2 ** k)
    return 0


def _uploader(root, hf_prefix, stop, repo, seen, interval=30.0):
    from huggingface_hub import HfApi
    api = HfApi(token=_tok())
    while not stop.is_set():
        try:
            upload_round(api, root, hf_prefix, repo, seen)
        except Exception as e:  # noqa: BLE001 - the loop never dies; the final flush runs on the main thread
            print("upload round failed", repr(e)[:160], flush=True)
        stop.wait(interval)


def verify_uploads(api, root, hf_prefix, repo) -> dict:
    """Each local file against HF (audit A2): an LFS file by its sha256, a small one by its git blob id."""
    files = [p for p, _ in _files(root)]
    paths = [f"{hf_prefix}/{p.relative_to(root).as_posix()}" for p in files]
    try:
        info = {i.path: i for i in api.get_paths_info(repo, paths, repo_type="dataset", expand=True)}
    except Exception as e:  # noqa: BLE001
        return {str(p.relative_to(root)): f"not checked: {type(e).__name__}" for p in files}
    out = {}
    for p, hp in zip(files, paths):
        i = info.get(hp)
        if i is None:
            out[str(p.relative_to(root))] = "missing on HF"
            continue
        lfs = getattr(i, "lfs", None)
        want = (lfs.sha256 if hasattr(lfs, "sha256") else (lfs or {}).get("sha256")) if lfs else None
        ok = (want == _sha(p)) if want else (getattr(i, "blob_id", None) == git_blob_id(p))
        out[str(p.relative_to(root))] = "ok" if ok else "hash differs on HF"
    return out


def _picture(plan, shot, root="/tmp/in"):
    from huggingface_hub import hf_hub_download
    p = hf_hub_download(plan["hf_repo"], shot["picture"], repo_type="dataset", local_dir=root, token=_tok())
    if _sha(p) != shot["sha256"]:
        raise SystemExit(f"{shot['id']}: the picture's sha256 is not the plan's")
    return p


def libs() -> dict:
    import importlib
    out = {"python": sys.version.split()[0]}
    for m in ("torch", "diffusers", "transformers", "accelerate", "peft", "huggingface_hub"):
        try:
            out[m] = getattr(importlib.import_module(m), "__version__", "?")
        except Exception:  # noqa: BLE001
            out[m] = None
    try:
        import torch
        out["cuda"], out["device"] = torch.version.cuda, torch.cuda.get_device_name(0)   # audit B3: the card that really ran
    except Exception:  # noqa: BLE001
        pass
    return out


def write_clip(frames, path, fps):
    from diffusers.utils import export_to_video
    tmp = Path(str(path) + ".tmp")
    export_to_video(frames, str(tmp), fps=fps, quality=9)          # audit B4: not the default CRF ~25
    os.replace(tmp, path)
    return path


def make_wan(plan, v, out, start_pictures, deadline, phases, beat_fn=beat, rows=None):
    """One Wan variant, both shots: the pipeline loaded once from the Volume; a shot is ``clips`` clips chained on frame[-5],
    each clip written as it is made; a clip that cannot finish in the time left is not started (PARTIAL)."""
    import numpy as np
    import torch
    import diffusers
    from PIL import Image
    t0 = time.time()
    beat_fn(out, stage="load", variant=v["id"])
    base = plan["weights"][v["weights"][0]]
    kw = {}
    if v.get("vae_fp32"):
        kw["vae"] = diffusers.AutoencoderKLWan.from_pretrained(str(weights_root(base) / "vae"), torch_dtype=torch.float32)
    pipe = getattr(diffusers, v["pipeline"]).from_pretrained(str(weights_root(base)), torch_dtype=torch.bfloat16, **kw)
    if v.get("scheduler"):                                           # audit B1: the LoRA authors' sampler
        sc = v["scheduler"]
        pipe.scheduler = getattr(diffusers, sc["class"]).from_config(pipe.scheduler.config, shift=float(sc["shift"]))
    if v.get("lora"):
        lw = plan["weights"][v["weights"][1]]
        names = []
        for target, f in v["lora"].items():
            name = f"lightning_{target}"
            pipe.load_lora_weights(str(weights_root(lw) / f), adapter_name=name,
                                   **({"load_into_transformer_2": True} if target == "transformer_2" else {}))
            names.append(name)
        pipe.set_adapters(names, adapter_weights=[1.0] * len(names))
    if v.get("offload") == "model_cpu_offload":
        pipe.enable_model_cpu_offload()
    else:
        pipe = pipe.to("cuda")
    phases["load_s"] = round(time.time() - t0, 1)
    settings = {k: x for k, x in v["settings"].items() if k != "source"}
    rows, last = ([] if rows is None else rows), None   # the caller's list: what was made survives a DeadlineHit
    for shot in plan["shots"]:
        t1, clips, row = time.time(), [], {"shot": shot["id"], "clips": []}
        rows.append(row)
        start = fit_picture(Image.open(start_pictures[shot["id"]]), v["width"], v["height"])
        for c in range(v["clips"]):
            if not deadline.fits(last):
                row["state"] = "PARTIAL"
                row["why"] = f"clip {c + 1} would not finish: {deadline.left():.0f} s left, the last clip took {last:.0f} s"
                break

            def _step(p, i, t, cbk, _c=c):
                deadline.check()
                beat_fn(out, stage="generate", variant=v["id"], shot=shot["id"], clip=_c + 1, step=int(i) + 1)
                return cbk
            tc = time.time()
            res = pipe(image=start, prompt=clip_prompt(shot, c), height=v["height"], width=v["width"], num_frames=v["frames"],
                       generator=torch.Generator("cuda").manual_seed(int(shot["seed"]) + c), callback_on_step_end=_step,
                       output_type="np", **settings)
            frames = res.frames[0]
            beat_fn(out, stage="export", variant=v["id"], shot=shot["id"], clip=c + 1)
            cp = write_clip(frames, Path(out) / f"{shot['id']}.clip{c + 1}.mp4", v["fps"])
            last = time.time() - tc
            row["clips"].append({"clip": c + 1, "gen_s": round(last, 1), "frames": len(frames), "sha256": _sha(cp)})
            clips.append(frames)
            start = Image.fromarray((np.clip(frames[-v.get("chain_back", 5)], 0, 1) * 255).astype("uint8"))
        if clips:
            joined = join_clips(clips, v.get("chain_back", 5))
            mp4 = write_clip(joined, Path(out) / f"{shot['id']}.mp4", v["fps"])
            row.update(frames=len(joined), fps=v["fps"], sha256=_sha(mp4))
        row["gen_s"] = round(time.time() - t1, 1)
        row.setdefault("state", "DONE" if len(clips) == v["clips"] else "PARTIAL")
        (Path(out) / f"{shot['id']}.measured.json").write_text(json.dumps(row))
        if row["state"] != "DONE":
            break
    return rows


def ltx_cmd(plan, v, shot, picture, mp4):
    """The LTX-2 CLI of one shot (ltx_pipelines.distilled): split weights from the Volume, the start picture at frame 0, every
    other setting the CLI's own LTX-2.5 default."""
    w = plan["weights"]["ltx25"]
    root = weights_root(w)
    f = lambda part: str(root / next(x for x in w["files"] if part in x))  # noqa: E731
    cmd = [sys.executable, "-m", v["module"], "--transformer-path", str(root / v["uses"]["transformer"]),
           "--text-encoder-path", f("text_encoders/"), "--video-vae-path", f("video-vae"), "--audio-vae-path", f("audio-vae"),
           "--spatial-upsampler-path", f("spatial-upscaler")]
    if v["uses"].get("distilled_lora"):
        cmd += ["--distilled-lora", str(root / v["uses"]["distilled_lora"])]
    prompt = shot["prompt"] + (" " + shot["audio_prompt"] if shot.get("audio_prompt") else "")
    cmd += ["--image", str(picture), "0", "1.0", "--prompt", prompt, "--width", str(v["width"]), "--height", str(v["height"]),
            "--num-frames", str(v["frames"]), "--frame-rate", str(v["fps"]), "--seed", str(shot["seed"]), "--output-path", str(mp4)]
    return cmd


def make_ltx(plan, v, out, start_pictures, deadline, phases, beat_fn=beat, sh=subprocess.run, tmp="/tmp/in",
             rows=None):
    """Each shot is one CLI process (it loads the weights itself), bounded by the time left (audit A1)."""
    from PIL import Image
    rows, last = ([] if rows is None else rows), None
    for shot in plan["shots"]:
        if not deadline.fits(last):
            rows.append({"shot": shot["id"], "state": "PARTIAL",
                         "why": f"would not finish: {deadline.left():.0f} s left, the last shot took {last:.0f} s"})
            break
        t1 = time.time()
        beat_fn(out, stage="generate", variant=v["id"], shot=shot["id"])
        Path(tmp).mkdir(parents=True, exist_ok=True)
        pic = Path(tmp) / f"{shot['id']}_{v['width']}x{v['height']}.png"
        fit_picture(Image.open(start_pictures[shot["id"]]), v["width"], v["height"]).save(pic)
        mp4 = Path(out) / f"{shot['id']}.mp4"
        row = {"shot": shot["id"], "fps": v["fps"], "frames": v["frames"]}
        with open(Path(out) / f"{shot['id']}.log", "w") as log:
            try:
                row["rc"] = sh(ltx_cmd(plan, v, shot, pic, mp4), stdout=log, stderr=subprocess.STDOUT, cwd="/workspace/LTX-2",
                               timeout=max(1.0, deadline.left())).returncode
            except subprocess.TimeoutExpired:
                row["rc"], row["why"] = None, "the in-container deadline came during this shot"
        last = time.time() - t1
        row["gen_s"] = round(last, 1)
        if row["rc"] == 0 and mp4.is_file():
            row["sha256"], row["state"] = _sha(mp4), "DONE"
        else:
            row["state"] = "PARTIAL" if row["rc"] is None else "FAILED"
        rows.append(row)
        (Path(out) / f"{shot['id']}.measured.json").write_text(json.dumps(row))
        if row["state"] != "DONE":
            break
    return rows


def run_state(rows, n_shots, verified, error=None) -> str:
    if error and not rows:
        return "FAILED"
    shots_done = [r for r in rows if r.get("state") == "DONE"]
    if any(r.get("state") == "FAILED" for r in rows):
        state = "FAILED"
    elif len(shots_done) == n_shots and not error:
        state = "DONE"
    else:
        state = "PARTIAL"
    if state == "DONE" and any(x != "ok" for x in verified.values()):
        state = "UPLOAD_UNVERIFIED"
    return state


def attempt_guard(vol_out: Path, rid, vid, nonce) -> str | None:
    """The first act of a GPU function (audit A1): a marker per launch nonce on the Volume. A rescheduled input carries the same
    nonce and finds its marker: it returns at once instead of paying for the work again."""
    d = vol_out / rid / vid
    d.mkdir(parents=True, exist_ok=True)
    m = d / f"attempt_{nonce}"
    if m.exists():
        return "REFUSED_SECOND_ATTEMPT"
    m.write_text(time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    return None


def body(plan, vid, rid, nonce, timeout_s, commit=lambda: None, reload=lambda: None):
    t_in = time.time()
    v = variant(plan, vid)
    reload()
    if attempt_guard(VOL_OUT, rid, vid, nonce):
        return {"state": "REFUSED_SECOND_ATTEMPT", "variant": vid, "run_id": rid, "body_s": round(time.time() - t_in, 1)}
    commit()
    deadline = Deadline(timeout_s)
    out = OUT_ROOT / rid / vid
    out.mkdir(parents=True, exist_ok=True)
    phases = {}
    beat(out, stage="start", variant=vid)
    stop, seen = threading.Event(), {}
    hf_prefix = f"{plan['hf_out']}/{rid}"
    th = threading.Thread(target=_uploader, args=(OUT_ROOT / rid, hf_prefix, stop, plan["hf_repo"], seen), daemon=True)
    th.start()
    rows, err = [], None
    try:
        t = time.time()
        beat(out, stage="verify", variant=vid)
        pics = {s["id"]: _picture(plan, s) for s in plan["shots"]}       # the cheapest thing that can fail goes first
        bad = [b for w in v["weights"] for b in stamp_ok(plan["weights"][w])]
        if bad:
            raise SystemExit("weights not staged: " + "; ".join(bad[:5]))
        phases["verify_s"] = round(time.time() - t, 1)
        (make_ltx if v["family"] == "ltx" else make_wan)(plan, v, out, pics, deadline, phases, rows=rows)
    except BaseException as e:  # noqa: BLE001 - recorded, then the run ends through the normal path
        err = f"{type(e).__name__}: {str(e)[:400]}"
        (out / "traceback.txt").write_text(traceback.format_exc())
    m = {"variant": vid, "run_id": rid, "shots": rows, "error": err, "phases": phases, "gpu": v["gpu"], "usd_per_h": rate_of(v),
         "worker_sha": worker_sha(), "plan_sha": plan_sha(), "libs": libs(), "body_s": round(time.time() - t_in, 1)}
    m["state"] = run_state(rows, len(plan["shots"]), {}, err)
    (out / "measured.json").write_text(json.dumps(m, indent=1))
    beat(out, stage="upload", variant=vid)
    stop.set()
    th.join(timeout=120)
    t = time.time()
    verified = {}
    try:
        from huggingface_hub import HfApi
        api = HfApi(token=_tok())
        upload_round(api, OUT_ROOT / rid, hf_prefix, plan["hf_repo"], seen, final=True)
        verified = verify_uploads(api, OUT_ROOT / rid / vid, f"{hf_prefix}/{vid}", plan["hf_repo"])
    except Exception as e:  # noqa: BLE001
        verified = {"_": f"upload failed: {type(e).__name__}"}
    phases["upload_s"] = round(time.time() - t, 1)
    m["state"], m["verified"] = run_state(rows, len(plan["shots"]), verified, err), verified
    (out / "verified.json").write_text(json.dumps({"state": m["state"], "files": verified}, indent=1))
    try:
        upload_round(api, OUT_ROOT / rid, hf_prefix, plan["hf_repo"], seen, final=True)
    except Exception:  # noqa: BLE001 - the Volume keeps it; the local side gets it in the answer too
        pass
    try:
        import shutil
        shutil.copytree(OUT_ROOT / rid, VOL_OUT / rid, dirs_exist_ok=True)
        commit()
    except Exception as e:  # noqa: BLE001
        print("volume copy failed", repr(e)[:200], flush=True)
    m["body_s"] = round(time.time() - t_in, 1)
    return m


PLAN = load_plan()

if modal is not None:
    app = modal.App(PLAN["app_name"])
    vol = modal.Volume.from_name(PLAN["volume"], version=2)
    secrets = [modal.Secret.from_name(SECRET_NAME)]
    pins = " ".join(f'"{k}=={x}"' for k, x in PIP.items())
    wan_image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12").apt_install("ffmpeg")
                 .run_commands(f'pip install -q "{DIFFUSERS}" {pins} ftfy "imageio[ffmpeg]"')
                 .add_local_file(str(PLAN_PATH), "/root/plan_v43.json"))
    ltx_image = (modal.Image.from_registry(BASE_IMAGE, add_python="3.12").apt_install("ffmpeg", "git")
                 .run_commands(f'pip install -q "huggingface_hub=={PIP["huggingface_hub"]}"',
                               f"git clone -q {LTX2[0]} /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q {LTX2[1]} && "
                               "pip install -q -e /workspace/LTX-2/packages/ltx-core -e /workspace/LTX-2/packages/ltx-pipelines")
                 .add_local_file(str(PLAN_PATH), "/root/plan_v43.json"))
    common = dict(retries=0, volumes={"/w": vol}, secrets=secrets, scaledown_window=2)

    def _gpu_kw(v):
        """Audit A5c: the CPU and memory limits equal the requests; audit B3: ``H100!`` so Modal cannot swap the card."""
        return dict(gpu=v["gpu"] + "!", cpu=(float(v["cpu"]), float(v["cpu"])),
                    memory=(v["memory_gib"] * 1024, v["memory_gib"] * 1024), timeout=timeout_of(PLAN, v), **common)

    def _gpu_body(vid, rid, token, nonce):
        if not token_ok(token, go_sha()):
            return {"state": "REFUSED_NO_TOKEN", "variant": vid}
        return body(PLAN, vid, rid, nonce, timeout_of(PLAN, variant(PLAN, vid)), commit=vol.commit, reload=vol.reload)

    @app.function(image=wan_image, cpu=(2.0, 2.0), memory=(4096, 4096), timeout=300, retries=0, secrets=secrets)
    def wan_env(token: str):
        if not token_ok(token, go_sha()):
            return ["REFUSED_NO_TOKEN"]
        import importlib.util
        bad = [m for m in ("torch", "diffusers", "transformers", "peft", "PIL", "imageio") if importlib.util.find_spec(m) is None]
        import diffusers
        bad += [p for p in ("WanImageToVideoPipeline", "AutoencoderKLWan", "FlowMatchEulerDiscreteScheduler")
                if not hasattr(diffusers, p)]
        return bad

    @app.function(image=ltx_image, cpu=(2.0, 2.0), memory=(4096, 4096), timeout=300, retries=0, secrets=secrets)
    def ltx_env(token: str):
        if not token_ok(token, go_sha()):
            return ["REFUSED_NO_TOKEN"]
        import importlib.util
        return [m for m in ("torch", "ltx_core", "ltx_pipelines.distilled", "PIL") if importlib.util.find_spec(m) is None]

    @app.function(image=wan_image, cpu=(float(PLAN["stage"]["cpu"]),) * 2, memory=(PLAN["stage"]["memory_gib"] * 1024,) * 2,
                  timeout=stage_timeout(PLAN), **common)
    def stage_fn(token: str):
        if not token_ok(token, go_sha()):
            return ["REFUSED_NO_TOKEN"]
        bad = stage_weights(PLAN)
        vol.commit()
        return bad

    _V = {v["id"]: v for v in PLAN["variants"]}

    @app.function(image=ltx_image, **_gpu_kw(_V["ltx_distilled"]))
    def run_ltx_distilled(rid: str, token: str, nonce: str):
        return _gpu_body("ltx_distilled", rid, token, nonce)

    @app.function(image=wan_image, **_gpu_kw(_V["wan_a14b_lightning"]))
    def run_wan_a14b_lightning(rid: str, token: str, nonce: str):
        return _gpu_body("wan_a14b_lightning", rid, token, nonce)

    @app.function(image=wan_image, **_gpu_kw(_V["wan_ti2v_5b"]))
    def run_wan_ti2v_5b(rid: str, token: str, nonce: str):
        return _gpu_body("wan_ti2v_5b", rid, token, nonce)

    GPU_FNS = {"ltx_distilled": run_ltx_distilled, "wan_a14b_lightning": run_wan_a14b_lightning,
               "wan_ti2v_5b": run_wan_ti2v_5b}

    def _gate():
        preflight(PLAN)
        sha = go_sha()
        card = go_gate(sha=sha)
        return card, sha

    @app.local_entrypoint()
    def check():
        card, sha = _gate()
        tok = token_for(card, sha)
        print("wan image", wan_env.remote(tok) or "imports ok")
        print("ltx image", ltx_env.remote(tok) or "imports ok")

    @app.local_entrypoint()
    def stage():
        card, sha = _gate()
        print("GO card", card, "stage timeout", stage_timeout(PLAN), "s", flush=True)
        bad = stage_fn.remote(token_for(card, sha))
        print("stage", bad or "every pinned file on the Volume, sha256 match, stamps written")
        if bad:
            raise SystemExit(4)

    @app.local_entrypoint()
    def run(variant: str = "", again: str = ""):
        card, sha = _gate()
        v = _V.get(variant)
        if v is None:
            raise SystemExit(f"no variant {variant!r}; one of {list(_V)}")
        rid = run_id(plan_sha(), worker_sha())
        led = open_ledger(PLAN)
        from huggingface_hub import HfApi
        api = HfApi(token=os.environ.get("HF_TOKEN"))
        why = repeat_reason(PLAN, rid, variant, led, lambda p: api.file_exists(PLAN["hf_repo"], p, repo_type="dataset"))
        if why and not again.strip():
            raise SystemExit(f"{variant}: {why}; a repeat pays again: pass --again '<reason>' only on the creator's word")
        nonce = uuid.uuid4().hex[:12]
        item = reserve(PLAN, v, rid, led, nonce)
        if why:
            led.data.setdefault("items", {})[item] = {"again": again.strip(), "why": why}
            led.save()
        print("GO card", card, "run id", rid, "timeout", timeout_of(PLAN, v), "s, cap $", v["cap_usd"], "reserved", item, flush=True)
        t0 = time.time()
        try:
            res = GPU_FNS[variant].remote(rid, token_for(card, sha), nonce)
        except BaseException as e:  # noqa: BLE001 - a lost answer: the reservation stays, nothing is retried
            led.fail(item, f"{type(e).__name__}: {str(e)[:200]}")
            print(FAILED, "no answer; the cap stays reserved until the Modal bill is read", flush=True)
            raise SystemExit(5)
        wall = time.time() - t0
        usd = settle(PLAN, v, item, led, wall)
        led.done("bakeoff", item, state=res.get("state"), wall_s=round(wall, 1), body_s=res.get("body_s"), usd=usd)
        print("result", json.dumps(res), "wall", round(wall, 1), "s, settled $", usd, flush=True)
        if res.get("state") != "DONE":
            print(FAILED, flush=True)
            raise SystemExit(4)
