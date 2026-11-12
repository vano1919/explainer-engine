"""The lean step-3 pod's runner (STEP3_POD_PLAN_LEAN_ka.md; the creator 2026-11-06 13:21 UTC, stage G 13:25 UTC, extras X1-X6 13:33
UTC): every stage of ``p14_stages.json`` in its order, each one as its own process, so one failed stage is recorded and the next one
runs (a stage whose input a failed stage should have made is skipped with that reason). ``p14.sh`` starts it inside pod_wrapper.sh,
which uploads ``$EE_OUT`` as files land (OR-33): ``$EE_OUT/layouts/`` -> HF ``route_test_2026-11/layouts/`` and ``$EE_OUT/step3/``
-> ``route_test_2026-11/step3/`` (the pod's heartbeat file is ``route_test_2026-11/beat.txt``, so the wrapper's prefix is
``route_test_2026-11``).

Three lanes, so the card is never idle while the CPU works and the paid time is not stretched:

- net (from the start): the LTX weights of both bases, checked by sha256 once (``p14_ltx.py --prefetch``), Qwen-Image-2.1 and BiRefNet;
- cpu: A (Blender layout passes: first the line frame 0 of the duel, then of the battle, each killed at ``frame0_timeout_s``; then the
  core passes, the duel's clay and the battle's colour and depth; last the battle's line, only when frame 0's time x its frames fits
  its budget), X6.move (the still's FFmpeg camera move), then G (the J5 shots of the pilot window, ``nice``d, stopped at the deadline
  reserve; it starts when D's cut-outs exist);
- gpu: C + X6.still (one Qwen process, at once) -> D (BiRefNet) -> B (a second Qwen process, when the frames 0 are done; the duel
  alone when the battle's frame 0 did not finish) -> E when the core passes exist (the five core LTX jobs, then the extras X1, X2,
  X5, X3, X6.ltx in one LTX process; a job whose layout clip is the battle line still being drawn waits at the end of the queue
  for it, ``P14_PENDING``) -> X4 (a Qwen process, when stage G has the frame) -> F (speeds.json).

Blender's device (the creator 2026-11-06 14:49 UTC): ``A.preflight`` draws the duel's line frame 0 with EEVEE on the card (NVIDIA's
EGL vendor, ``PREFLIGHT_S`` at most); when the report's GL renderer is NVIDIA's, A and G render there beside Qwen and LTX, else on the
CPU (Mesa's software EGL, the card hidden), as before. Nothing waits for the preflight but A itself.

Fix of 2026-11-06 14:44 UTC (pod ygg2ztmflr8pv2): the GPU lane used to wait for the battle's line frame 0 before any Qwen picture and
E for every A pass; a timed-out stage now kills its whole process group (Blender too), and the Blender logs' tails are copied into
``step3/logs/`` every minute while a pass runs.

Records: ``step3/stages.json`` (per stage: status, rc, seconds, reason), ``step3/stages.txt`` and ``step3/t.jsonl``.

    python3 -m explainer_engine.training.pods.p14.p14_pod --binary <blender>        # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
    python3 -m explainer_engine.training.pods.p14.p14_pod --plan                     # the stage list and lanes, no work
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PY = sys.executable
PKG = "explainer_engine.training.pods.p14"
LANES = {"net": ["weights"], "cpu": ["A", "X6.move", "G"],
         "gpu": ["C", "X6.still", "D", "B", "E", "X1", "X2", "X5", "X3", "X6.ltx", "X4", "F"]}
TAIL_LINES = 200
TAIL_EVERY_S = 60
PREFLIGHT_S = 120          # the creator 2026-11-06 14:49 UTC: a 2-minute preflight frame decides card or CPU for Blender
MESA_JSON = "/usr/share/glvnd/egl_vendor.d/50_mesa.json"
EGL_DIRS = ("/usr/share/glvnd/egl_vendor.d", "/etc/glvnd/egl_vendor.d")
NEEDS = {   # stage -> the stages whose output it reads (a failed one skips it with that reason)
    # E needs nothing as a whole: p14_ltx skips each job whose layout clip or first frame is missing, with that reason
    "B": ["A.frame0"], "C": [], "X6.still": [], "D": [], "E": [], "X4": ["G"], "X6.move": ["X6.still"],
    "G": ["D"], "F": [],
}


def load_cfg() -> dict:
    return json.loads((HERE / "p14_stages.json").read_text(encoding="utf-8"))


class Book:
    """The stage records, written after every change (the wrapper uploads them with the outputs)."""

    def __init__(self, d: Path):
        self.d = Path(d)
        self.d.mkdir(parents=True, exist_ok=True)
        self.rows: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.events = {k: threading.Event() for k in ("A.frame0", "A.core", "A", "B", "weights", "D", "G", "X6.still", "cpu_done")}

    def _write(self):
        tmp = self.d / "stages.json.tmp"
        tmp.write_text(json.dumps({"schema": "p14_stages_run/1", "stages": self.rows}, indent=1), encoding="utf-8")
        os.replace(tmp, self.d / "stages.json")

    def mark(self, name: str, status: str, **kw):
        with self.lock:
            row = self.rows.setdefault(name, {})
            row.update(status=status, t=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), **kw)
            self._write()
            with open(self.d / "stages.txt", "a", encoding="utf-8") as f:
                f.write(f"{time.strftime('%H:%M:%S', time.gmtime())} {name} {status} {kw.get('reason', '')}\n")
            with open(self.d / "t.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps({"t": row["t"], "ev": "stage", "stage": name, "status": status, **kw}) + "\n")
            p = self.d / "progress.txt"
            p.write_text(f"{time.strftime('%T', time.gmtime())} {name} {status}\n", encoding="utf-8")

    def ok(self, name: str) -> bool:
        return (self.rows.get(name) or {}).get("status") == "ok"

    def done(self, name: str):
        if name in self.events:
            self.events[name].set()


def run_proc(cmd, *, timeout=None, env=None, log_path=None, deadline=None) -> tuple[object, float]:
    """(return code or 'timeout'/'oserror', seconds) of one stage process; never raises. The process gets its own session, so a
    timeout kills the whole group: a Blender that layout_passes started dies with it instead of eating the CPU on."""
    t0 = time.time()
    if deadline:
        left = deadline - time.time()
        timeout = max(1.0, min(timeout or left, left))
    try:
        with open(log_path or os.devnull, "a", encoding="utf-8") as lf:
            pr = subprocess.Popen(cmd, stdout=lf, stderr=subprocess.STDOUT, env=env, start_new_session=True)
            try:
                rc = pr.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                kill_group(pr)
                rc = "timeout"
    except OSError as e:
        rc = f"oserror {e}"[:120]
    return rc, round(time.time() - t0, 1)


def kill_group(pr):
    import signal
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(pr.pid, sig)
        except (ProcessLookupError, PermissionError):
            return
        try:
            pr.wait(timeout=20)
            return
        except subprocess.TimeoutExpired:
            continue


def tail(src: Path, dst: Path, n: int = TAIL_LINES):
    """The last ``n`` lines of a log into ``dst`` (the wrapper uploads ``dst``); a missing log writes nothing."""
    try:
        with open(src, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - 256 * 1024))
            lines = f.read().decode("utf-8", "replace").splitlines()[-n:]
    except OSError:
        return
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(dst.name + ".tmp")
    tmp.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.replace(tmp, dst)


class Tailer:
    """While a Blender pass runs: every ``every`` s the tails of its ``blender.log`` files into ``step3/logs/`` (and once at the end)."""

    def __init__(self, pairs, every: float = TAIL_EVERY_S):
        self.pairs, self.every, self.stop = list(pairs), every, threading.Event()
        self.t = threading.Thread(target=self._loop, daemon=True)

    def _copy(self):
        for src, dst in self.pairs:
            tail(src, dst)

    def _loop(self):
        while not self.stop.wait(self.every):
            self._copy()

    def __enter__(self):
        self.t.start()
        return self

    def __exit__(self, *exc):
        self.stop.set()
        self.t.join(timeout=5)
        self._copy()


class Pod:
    def __init__(self, cfg: dict, out: Path, *, binary: str, deadline: float, run=run_proc, layouts_work=Path("/workspace/layouts"),
                 assets=Path("/workspace/assets")):
        self.cfg, self.out, self.binary, self.deadline, self.run = cfg, Path(out), binary, deadline, run
        self.step3, self.lay_out = self.out / "step3", self.out / "layouts"
        self.lay_work, self.lay_f0, self.assets = Path(layouts_work), Path(str(layouts_work) + "_f0"), Path(assets)
        self.book = Book(self.step3)
        self.reserve = cfg["end_reserve_min"] * 60
        self.env = dict(os.environ, P14_OUT=str(self.step3), PYTHONUNBUFFERED="1", P14_LOCAL_ROOTS=json.dumps([
            [f"{cfg['hf_root']}/layouts", str(self.lay_out)], [f"{cfg['hf_root']}/step3", str(self.step3)]]))
        self.logs = self.step3 / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.blender_env = cpu_env(self.env)   # until the preflight puts Blender on the card

    # --- helpers -------------------------------------------------------------------------------------------------------------
    def missing(self, name: str) -> str | None:
        bad = [n for n in NEEDS.get(name, []) if not self.book.ok(n)]
        return f"needs {', '.join(bad)}, which did not finish" if bad else None

    def stage(self, name: str, cmd, *, timeout=None, env=None, need=True, tails=()) -> bool:
        why = self.missing(name) if need else None
        if why is None and time.time() > self.deadline - self.reserve:
            why = "inside the end reserve"
        if why:
            self.book.mark(name, "skipped", reason=why)
            self.book.done(name)
            return False
        self.book.mark(name, "running")
        with Tailer(tails):
            rc, sec = self.run(cmd, timeout=timeout, env=env or self.env, log_path=self.logs / f"{name}.log",
                               deadline=self.deadline - self.reserve)
        self.book.mark(name, "ok" if rc == 0 else "failed", rc=rc, seconds=sec)
        self.book.done(name)
        return rc == 0

    def mod(self, m: str, *args) -> list[str]:
        return [PY, "-m", f"{PKG}.{m}", *map(str, args)]

    def wait(self, event: str, until: float) -> bool:
        return self.book.events[event].wait(max(0.0, until - time.time()))

    # --- lanes ----------------------------------------------------------------------------------------------------------------
    def net(self):
        q = self.cfg["qwen"]
        code = ("from huggingface_hub import snapshot_download, hf_hub_download\n"
                f"snapshot_download({q['base']!r})\n"
                f"hf_hub_download({q['style_lora']['hf']!r}, {q['style_lora']['path']!r}, repo_type='dataset')\n"
                "import json; p = json.load(open('config/cloud_pins.json'))['models']['cutout_birefnet']\n"
                "snapshot_download(p['id'], revision=p['revision'])\n")
        self.run([PY, "-c", code], timeout=3600, env=self.env, log_path=self.logs / "weights_qwen.log", deadline=self.deadline)
        self.stage("weights", [PY, str(HERE / "p14_ltx.py"), "--prefetch"], timeout=5400, need=False)

    def blender_tails(self, root: Path, scene: str, passes, label: str):
        return [(Path(root) / scene / k / "blender.log", self.logs / f"{label}.{k}.blender_tail.txt") for k in passes]

    def stage_a(self):
        a = self.cfg["A"]
        lp = ["-m", "explainer_engine.blender.layout_passes", "render", "--binary", self.binary]
        got, f0_seconds = [], {}
        pre = self.preflight(lp, a["first_frames"][0])
        for f in a["first_frames"]:   # the duel first (seconds), then the battle; each one killed at frame0_timeout_s
            name = f"A.frame0.{f['scene']}"
            if pre and f is a["first_frames"][0]:   # the preflight drew it on the card: the same frame, kept
                rc, sec = 0, pre["seconds"]
            else:
                self.book.mark(name, "running")
                with Tailer(self.blender_tails(self.lay_f0, f["scene"], [f["pass"]], name)):
                    rc, sec = self.run([PY, *lp, "--scene", f["scene"], "--out", self.lay_f0, "--passes", f["pass"], "--only-frames",
                                        str(f["frame"])], timeout=a["frame0_timeout_s"], env=self.blender_env,
                                       log_path=self.logs / f"{name}.log", deadline=self.deadline - self.reserve)
            src = self.lay_f0 / f["scene"] / f["pass"] / "frames" / f"frame_{f['frame']:06d}.png"
            ok = rc == 0 and src.exists()
            if src.exists():
                dst = self.lay_out / f["scene"] / f["pass"] / f"frame0_{f['frame']:06d}.png"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
            if ok:
                got.append(f["scene"])
                f0_seconds[f["scene"]] = sec
            self.book.mark(name, "ok" if ok else "failed", rc=rc, seconds=sec)
        missing = [f["scene"] for f in a["first_frames"] if f["scene"] not in got]
        self.book.mark("A.frame0", "ok" if got else "failed", scenes=got, missing=missing)
        self.book.done("A.frame0")
        ok = True
        for r in a["renders"]:
            if not r.get("core", True):
                self.release_core(ok)   # the core passes are done: E may start while the battle line is drawn
            name = f"A.{r['scene']}" + ("" if r.get("core", True) else "." + "+".join(r["passes"]))
            why = None
            if r.get("budget_s"):
                s0 = f0_seconds.get(r["scene"])
                if s0 is None:
                    why = f"the {r['scene']} frame 0 did not finish inside {a['frame0_timeout_s']} s"
                elif s0 * r["frames"] > r["budget_s"]:
                    why = (f"the {r['scene']} frame 0 took {s0} s: {r['frames']} frames would take ~{round(s0 * r['frames'])} s, "
                           f"over the {r['budget_s']} s budget")
            if why:
                self.book.mark(name, "skipped", reason=why)
                done = False
            else:
                timeout = min(a["timeout_s"], r["budget_s"]) if r.get("budget_s") else a["timeout_s"]
                done = self.stage(name, [PY, *lp, "--scene", r["scene"], "--out", self.lay_work, "--passes", ",".join(r["passes"])],
                                  timeout=timeout, need=False, env=self.blender_env,
                                  tails=self.blender_tails(self.lay_work, r["scene"], r["passes"], name))
            ok = ok and done
            if done:
                self.publish_layout(r["scene"])
        self.release_core(ok)
        self.clear_pending()
        self.book.mark("A", "ok" if ok else "failed")
        self.book.done("A")

    def preflight(self, lp: list[str], f: dict) -> dict | None:
        """A.preflight: the first frame 0 (the duel's line) with EEVEE on the card, at most ``PREFLIGHT_S``. Kept (and
        ``blender_env`` switched to the card) only when it rendered and its report's GL renderer is NVIDIA's; else Blender stays on
        the CPU and the frame is drawn again there. Returns the kept row or None."""
        env, egl = gpu_env(self.env, self.lay_work.parent / "egl")
        row = {"mode_tried": "gpu", "egl": egl, "budget_s": PREFLIGHT_S}
        if env is None:
            self.book.mark("A.preflight", "ok", chosen="cpu", reason="no NVIDIA EGL vendor on this pod", **row)
            return None
        self.book.mark("A.preflight", "running", **row)
        with Tailer(self.blender_tails(self.lay_f0, f["scene"], [f["pass"]], "A.preflight")):
            rc, sec = self.run([PY, *lp, "--scene", f["scene"], "--out", self.lay_f0, "--passes", f["pass"], "--only-frames",
                                str(f["frame"])], timeout=PREFLIGHT_S, env=env, log_path=self.logs / "A.preflight.log",
                               deadline=self.deadline - self.reserve)
        d = self.lay_f0 / f["scene"] / f["pass"]
        frame = d / "frames" / f"frame_{f['frame']:06d}.png"
        gl = ((read_json(d / "bpy_report.json") or {}).get("gl") or {})
        on_card = "nvidia" in f"{gl.get('vendor', '')} {gl.get('renderer', '')}".lower()
        keep = rc == 0 and frame.exists() and on_card
        if keep:
            self.blender_env = env
        elif frame.exists():
            frame.unlink()   # drawn by Mesa after all: the CPU loop draws it again under its own record
        self.book.mark("A.preflight", "ok", chosen="gpu" if keep else "cpu", rc=rc, seconds=sec, s_per_frame=sec, gl=gl,
                       reason="" if keep else ("not drawn on the NVIDIA renderer" if rc == 0 else f"rc {rc}"), **row)
        return {"seconds": sec} if keep else None

    def release_core(self, ok: bool):
        if not self.book.events["A.core"].is_set():
            self.book.mark("A.core", "ok" if ok else "failed")
            self.book.done("A.core")

    @property
    def pending(self) -> Path:
        return Path(str(self.lay_work) + ".pending.json")   # on the pod's disk, not in the upload

    def promised(self) -> list[str]:
        """The vault prefixes the CPU lane makes for E: every layout clip (until A ends) and X3's first frame (until G draws it)."""
        root = self.cfg["hf_root"]
        return [f"{root}/layouts/", f"{root}/step3/{self.cfg['X']['X3']['first_frame']}"]

    def settle(self, prefix: str | None = None):
        """Drop one promise (all of them when ``prefix`` is None): E stops waiting for it."""
        with self.book.lock:
            left = [] if prefix is None else [x for x in ((read_json(self.pending) or {}).get("prefixes") or []) if x != prefix]
            if left:
                write_side(self.pending, {"prefixes": left})
            else:
                try:
                    self.pending.unlink()
                except FileNotFoundError:
                    pass

    def clear_pending(self):
        self.settle(f"{self.cfg['hf_root']}/layouts/")

    def publish_layout(self, scene: str):
        """The clip mp4s and the manifest of one scene into ``$EE_OUT/layouts/<scene>/<pass>/`` (the PNG frames stay on the pod's
        disk; the upload carries what LTX and the verdict page read)."""
        d = self.lay_work / scene
        man = json.loads((d / "layout_manifest.json").read_text(encoding="utf-8"))
        dst = self.lay_out / scene
        dst.mkdir(parents=True, exist_ok=True)
        old = dst / "layout_manifest.json"   # the battle comes in two renders (core, then line): one manifest with every pass
        if old.exists():
            prev = json.loads(old.read_text(encoding="utf-8"))
            man["passes"] = {**prev.get("passes", {}), **man["passes"]}
        write_side(old, man)
        for kind, row in man["passes"].items():
            (dst / kind).mkdir(parents=True, exist_ok=True)
            for c in row.get("clips", {}).values():
                tmp = dst / kind / f".{c['path']}.tmp"
                shutil.copyfile(d / kind / c["path"], tmp)
                os.replace(tmp, dst / kind / c["path"])   # whole, before E reads it

    def stage_x6_move(self):
        x = self.cfg["X"]["X6"]
        still = self.step3 / "qwen" / f"{x['still']['name']}.png"
        dst = self.step3 / "x6" / f"{x['shot']}.move.mp4"
        dst.parent.mkdir(parents=True, exist_ok=True)
        if self.stage("X6.move", move_cmd(still, dst, **x["move"]), timeout=900):
            write_side(dst.with_suffix(".json"), {"question": x["question"], "recipe": "still_move/1 (FFmpeg zoompan, CPU)",
                                                   "still": str(still), "move": x["move"]})

    def g_frames(self, sid: str, d: Path):
        """After each J5 shot: the frames the extras read (X3's first frame, X4's frame) into first_frames/ and x4/."""
        from PIL import Image
        from explainer_engine.training.pods.p14.p14_qwen import first_frame
        x3 = self.cfg["X"]["X3"]["first_frame_from_g"]
        if sid == x3["shot"]:
            src = d / "frames" / f"frame_{x3['frame']:06d}.png"
            if src.exists():
                ff = self.step3 / self.cfg["X"]["X3"]["first_frame"]
                ff.parent.mkdir(parents=True, exist_ok=True)
                tmp = ff.with_name(ff.stem + ".tmp.png")
                first_frame(Image.open(src), (self.cfg["X"]["X3"]["width"], self.cfg["X"]["X3"]["height"])).save(tmp)
                os.replace(tmp, ff)   # whole, before E reads it
            self.settle(f"{self.cfg['hf_root']}/step3/{self.cfg['X']['X3']['first_frame']}")

    def stage_g(self):
        self.wait("D", self.deadline - self.reserve)
        dl = self.deadline - self.reserve
        if self.missing("G"):
            self.book.mark("G", "skipped", reason=self.missing("G"))
        else:
            self.book.mark("G", "running")
            t0 = time.time()
            try:
                from explainer_engine.training.pods.p14 import p14_j5
                rc = p14_j5.run(self.step3, self.assets, self.binary, deadline=dl, on_shot=self.g_frames, env=self.blender_env)
            except Exception as e:   # noqa: BLE001 - G failing never stops the GPU lane
                rc = f"error {e!r}"[:200]
            self.book.mark("G", "ok" if rc == 0 else "failed", rc=rc, seconds=round(time.time() - t0, 1))
        self.book.done("G")

    def cpu(self):
        try:
            self.stage_a()
            self.wait("X6.still", self.deadline - self.reserve)
            self.stage_x6_move()
            self.stage_g()
        finally:
            self.settle()   # whatever happened, E waits for nothing more from this lane
            self.book.done("A.frame0")
            self.book.done("A.core")
            self.book.done("A")
            self.book.done("G")
            self.book.done("cpu_done")

    def qwen(self, name: str, stages: list[str], labels) -> bool:
        q = self.cfg["qwen"]
        ok = self.stage(name, self.mod("p14_qwen", "--stages", ",".join(stages), "--out", self.step3, "--layouts", self.lay_f0,
                                       "--assets", self.assets), timeout=q["timeout_s"], need=False)
        man = read_manifest(self.step3 / "qwen" / "manifest.jsonl")
        for st, label in labels:
            got = [r for r in man if r.get("stage") == st]
            good = [r for r in got if r.get("status") == "ok"]
            self.book.mark(label, "ok" if got and len(good) == len(got) else "partial" if good else "failed",
                           pictures=len(good), names=[r.get("name") for r in good], process_ok=ok)
            self.book.done(label)
        return ok

    def gpu(self):
        q = self.cfg["qwen"]
        self.qwen("qwen1", ["C", "X6"], (("C", "C"), ("X6", "X6.still")))   # at once: neither reads a layout frame
        self.stage("D", self.mod("p14_cutout", "--out", self.step3, "--assets", self.assets), timeout=self.cfg["D"]["timeout_s"])
        self.wait("A.frame0", self.deadline - self.reserve)
        if self.book.ok("A.frame0"):
            self.qwen("qwen2", ["B"], (("B", "B"),))
        else:
            self.book.mark("B", "skipped", reason=self.missing("B"))
            self.book.done("B")
        self.wait("weights", self.deadline - self.reserve)   # not A: a job whose layout clip is not drawn yet waits inside E
        self.stage("E", [PY, str(HERE / "p14_ltx.py")], timeout=None, env=dict(self.env, P14_PENDING=str(self.pending)))
        core = self.step3 / "ltx" / "speeds.json"
        if core.exists():
            sp = json.loads(core.read_text(encoding="utf-8"))
            self.book.mark("E", "ok" if sp.get("ok") else "failed", clips_ok=sp.get("ok"), started=sp.get("started"),
                           rows=[{k: r.get(k) for k in ("job", "status", "seconds", "reason")} for r in sp["rows"]])
        self.mark_extras()
        self.wait("G", self.deadline - self.reserve)
        if (self.step3 / "j5" / self.cfg["X"]["X4"]["frame_from_g"]["shot"] / "frames"
                / f"frame_{self.cfg['X']['X4']['frame_from_g']['frame']:06d}.png").exists():
            self.stage("X4", self.mod("p14_qwen", "--stages", "X4", "--out", self.step3, "--layouts", self.step3,
                                      "--assets", self.assets), timeout=q["timeout_s"], need=False)
        else:
            self.book.mark("X4", "skipped", reason="stage G has not rendered the frame X4 edits")

    def mark_extras(self):
        """The extras' rows from the LTX process's speeds_extra.json (one record per extra in the stage list)."""
        p = self.step3 / "ltx" / "speeds_extra.json"
        rows = json.loads(p.read_text(encoding="utf-8"))["rows"] if p.exists() else []
        for r in rows:
            label = r["job"].split(".", 1)[0]
            self.book.mark(label if label != "X6" else "X6.ltx", r["status"], job=r["job"], seconds=r.get("seconds"),
                           reason=r.get("reason", ""))

    def stage_f(self):
        self.book.mark("F", "running")
        try:
            write_side(self.step3 / "speeds.json", speeds_report(self.step3, self.lay_out, self.book.rows))
            self.book.mark("F", "ok")
        except Exception as e:   # noqa: BLE001
            self.book.mark("F", "failed", reason=repr(e)[:200])

    def main(self) -> int:
        write_side(self.pending, {"prefixes": self.promised()})   # before the lanes start: E reads it
        lanes = [threading.Thread(target=self.net, daemon=True), threading.Thread(target=self.cpu, daemon=True)]
        for t in lanes:
            t.start()
        try:
            self.gpu()
        except Exception as e:   # noqa: BLE001 - the record says what broke; the CPU lane and F still run
            self.book.mark("gpu_lane", "failed", reason=repr(e)[:300])
        self.book.events["cpu_done"].wait(max(0.0, self.deadline - self.reserve - time.time()))
        self.stage_f()
        ok = [k for k, v in self.book.rows.items() if v.get("status") == "ok"]
        return 0 if ok else 1


def read_json(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def cpu_env(base: dict) -> dict:
    """Blender on the CPU: Mesa's software EGL, the card hidden (so it stays Qwen's and LTX's)."""
    return dict(base, CUDA_VISIBLE_DEVICES="", __EGL_VENDOR_LIBRARY_FILENAMES=MESA_JSON)


def gpu_env(base: dict, work: Path, *, dirs=EGL_DIRS, ldconfig=None) -> tuple[dict | None, dict]:
    """Blender on the card: glvnd pointed at NVIDIA's EGL vendor file only, so the Mesa vendor p14.sh installs cannot be picked
    instead. The file is the driver's (``*nvidia*.json`` in the glvnd folders) or, when the container mounts ``libEGL_nvidia.so.0``
    without one, written to ``work``. (None, what was seen) when neither exists."""
    seen = {"vendor_files": sorted(str(f) for d in dirs for f in Path(d).glob("*.json")) if dirs else []}
    nv = [f for f in seen["vendor_files"] if "nvidia" in Path(f).name.lower()]
    if not nv:
        lib = find_lib("libEGL_nvidia.so.0", ldconfig)
        seen["libEGL_nvidia"] = lib
        if not lib:
            return None, seen
        work.mkdir(parents=True, exist_ok=True)
        f = work / "10_nvidia.json"
        f.write_text(json.dumps({"file_format_version": "1.0.0", "ICD": {"library_path": "libEGL_nvidia.so.0"}}), encoding="utf-8")
        nv = [str(f)]
    seen["used"] = nv[0]
    env = dict(base, __EGL_VENDOR_LIBRARY_FILENAMES=nv[0])
    env.pop("CUDA_VISIBLE_DEVICES", None)
    return env, seen


def find_lib(name: str, ldconfig=None) -> str | None:
    try:
        out = ldconfig() if ldconfig else subprocess.run(["ldconfig", "-p"], capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    for ln in out.splitlines():
        if name in ln and "=>" in ln:
            return ln.split("=>", 1)[1].strip()
    return None


def read_manifest(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def write_side(p: Path, obj: dict):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + ".tmp")
    tmp.write_text(json.dumps(obj, indent=1, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, p)


def move_cmd(still: Path, dst: Path, *, seconds: float, size, zoom_end: float, fps: int) -> list[str]:
    """X6's free camera move: a slow centred push from 1.0 to ``zoom_end`` over ``seconds`` (FFmpeg zoompan on a 2x Lanczos copy,
    so the sub-pixel steps do not jitter), at the master size."""
    n = round(seconds * fps)
    w, h = size
    step = (zoom_end - 1.0) / max(n - 1, 1)
    vf = (f"scale={2 * w}:{2 * h}:flags=lanczos,zoompan=z='1+{step:.6f}*on':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
          f":d={n}:s={w}x{h}:fps={fps},format=yuv420p")
    return ["ffmpeg", "-y", "-v", "error", "-loop", "1", "-i", str(still), "-vf", vf, "-frames:v", str(n), "-c:v", "libx264",
            "-crf", "16", str(dst)]


def speeds_report(step3: Path, lay_out: Path, stages: dict) -> dict:
    """F: what each kind of work cost in seconds on this pod (job_speeds rows for the ICW-09 benchmark)."""
    def load(p):
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None
    ltx, extra = load(step3 / "ltx" / "speeds.json"), load(step3 / "ltx" / "speeds_extra.json")
    qwen = [r for r in read_manifest(step3 / "qwen" / "manifest.jsonl") if r.get("status") == "ok"]
    blender = {}
    for man in sorted(lay_out.glob("*/layout_manifest.json")):
        m = load(man)
        for kind, row in m["passes"].items():
            blender[f"layout.{m['scene']}.{kind}"] = {"frames": row["frames"], "s_per_frame": row["seconds_per_frame"]}
    j5 = load(step3 / "j5" / "report.json") or {}
    for sid, r in (j5.get("shots") or {}).items():
        if r.get("frames"):
            blender[f"j5.{sid}"] = {"frames": r["frames"], "s_per_frame": r["s_per_frame"], "size": j5.get("size")}
    return {"schema": "p14_speeds/1", "stages": {k: {"status": v.get("status"), "seconds": v.get("seconds")} for k, v in stages.items()},
            "ltx_clip_s_per_clip": ltx, "ltx_extras": extra,
            "qwen_s_per_picture": {r["name"]: r["seconds"] for r in qwen}, "blender": blender,
            "cutout": [{"name": r["name"], "seconds": r.get("seconds")} for r in
                       (load(step3 / "cutout" / "report.json") or {}).get("pictures", [])]}


def plan(cfg: dict) -> dict:
    return {"order": cfg["order"], "lanes": LANES, "needs": NEEDS, "gpu_order": cfg["gpu_order"], "cpu_order": cfg["cpu_order"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="the lean step-3 pod's runner")
    ap.add_argument("--binary")
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_cfg()
    if a.plan:
        print(json.dumps(plan(cfg), indent=1))
        return 0
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    return Pod(cfg, out, binary=a.binary, deadline=float(os.environ["EE_DEADLINE"])).main()


if __name__ == "__main__":
    sys.exit(main())
