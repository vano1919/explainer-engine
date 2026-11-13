"""The lean step-3 pod's runner (STEP3_POD_PLAN_LEAN_ka.md; the creator 2026-11-06 13:21 UTC, stage G 13:25 UTC, extras X1-X6 13:33
UTC): every stage of ``p14_stages.json`` in its order, each one as its own process, so one failed stage is recorded and the next one
runs (a stage whose input a failed stage should have made is skipped with that reason). ``p14.sh`` starts it inside pod_wrapper.sh,
which uploads ``$EE_OUT`` as files land (OR-33): ``$EE_OUT/layouts/`` -> HF ``route_test_2026-11/layouts/`` and ``$EE_OUT/step3/``
-> ``route_test_2026-11/step3/`` (the pod's heartbeat file is ``route_test_2026-11/beat.txt``, so the wrapper's prefix is
``route_test_2026-11``).

Three lanes, so the card is never idle while the CPU works and the paid time is not stretched (fix 2, Fable thread 15:07 UTC:
the stage graph is ``p14_schedule.json``, the file ``runpod create --schedule`` costs under RP-11, and the code follows it):

- net: Qwen-Image-2.1 + its LoRA + BiRefNet (``weights_qwen``), then the LTX weights checked by sha256 (``weights``);
- cpu (the Blender lane, a thread beside the card): ``A.preflight`` (the duel's line frame 0 with EEVEE on NVIDIA's EGL; kept, and
  Blender moved to the card, when the report's GL renderer is NVIDIA's), the frames 0 of the duel and the battle, the duel's clay,
  the battle's colour and depth, last the battle's line (only when frame 0 x its frames fits its max), then X6.move;
- gpu: a ready-queue over ``gpu_order`` (p14_stages.json): a free card takes the first stage whose needs (the schedule's) are done:
  qwen1 (C + X6 still), D, B.duel / B.battle (one Qwen process per scene, as its frame 0 lands), E.duel, X6.ltx, E.battle,
  E.battle_line (each an LTX process of its own jobs, ``E_stages``), G (the J5 shots, on the pod only when Blender is on the card
  and the preflight frame took at most ``G.on_pod.max_frame_s``; else they render free on CI or the PC, D-114, and X3 and X4
  skip with them), X3, X4, then F (speeds.json) once the CPU lane is done.

Every timeout is the stage's max in ``p14_schedule.json`` on the lane (device) it runs on.

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
LANES = {"net": ["weights_qwen", "weights"],
         "cpu": ["A.preflight", "A.frame0.duel", "A.frame0.battle", "A.duel", "A.battle", "A.battle.line", "X6.move"],
         "gpu": ["qwen1", "D", "B.duel", "B.battle", "E.duel", "X6.ltx", "E.battle", "E.battle_line", "G", "X3", "X4", "F"]}
TAIL_LINES = 200
TAIL_EVERY_S = 60
PREFLIGHT_S = 120          # the creator 2026-11-06 14:49 UTC: a 2-minute preflight frame decides card or CPU for Blender
MESA_JSON = "/usr/share/glvnd/egl_vendor.d/50_mesa.json"
EGL_DIRS = ("/usr/share/glvnd/egl_vendor.d", "/etc/glvnd/egl_vendor.d")
NEEDS = {   # stage -> the stages whose output it must have (a failed one skips it with that reason); the GPU lane's waits are the
    # schedule's needs (p14_schedule.json), these are the ones whose failure makes the stage pointless
    "B.duel": ["A.frame0.duel"], "B.battle": ["A.frame0.battle"], "X6.move": ["X6.still"], "G": ["D"], "X3": ["G"], "X4": ["G"],
}
QWEN_LABELS = {"qwen1": (("C", "C"), ("X6", "X6.still"))}


def load_cfg() -> dict:
    return json.loads((HERE / "p14_stages.json").read_text(encoding="utf-8"))


def load_schedule() -> dict:
    return json.loads((HERE / "p14_schedule.json").read_text(encoding="utf-8"))


class Book:
    """The stage records, written after every change (the wrapper uploads them with the outputs)."""

    def __init__(self, d: Path):
        self.d = Path(d)
        self.d.mkdir(parents=True, exist_ok=True)
        self.rows: dict[str, dict] = {}
        self.lock = threading.Lock()
        self.events: dict[str, threading.Event] = {}
        self.changed = threading.Condition(self.lock)

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

    def event(self, name: str) -> threading.Event:
        with self.lock:
            return self.events.setdefault(name, threading.Event())

    def done(self, name: str):
        self.event(name).set()
        with self.changed:
            self.changed.notify_all()

    def is_done(self, name: str) -> bool:
        return self.event(name).is_set()

    def wait_change(self, timeout: float):
        with self.changed:
            self.changed.wait(max(0.0, timeout))


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
                 assets=Path("/workspace/assets"), schedule: dict | None = None):
        self.cfg, self.out, self.binary, self.deadline, self.run = cfg, Path(out), binary, deadline, run
        self.step3, self.lay_out = self.out / "step3", self.out / "layouts"
        self.lay_work, self.lay_f0, self.assets = Path(layouts_work), Path(str(layouts_work) + "_f0"), Path(assets)
        self.book = Book(self.step3)
        self.reserve = cfg["end_reserve_min"] * 60
        self.env = dict(os.environ, P14_OUT=str(self.step3), PYTHONUNBUFFERED="1", P14_LOCAL_ROOTS=json.dumps([
            [f"{cfg['hf_root']}/layouts", str(self.lay_out)], [f"{cfg['hf_root']}/step3", str(self.step3)]]))
        self.logs = self.step3 / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.blender_env, self.blender_on = cpu_env(self.env), "cpu"   # until the preflight puts Blender on the card
        self.sched = {s["id"]: s for s in (schedule or load_schedule())["stages"]}
        self.active = set(self.sched)   # fix 2: the pod runs only the stages its schedule names (lean.graph)
        self.pre_frame_s = None

    # --- helpers -------------------------------------------------------------------------------------------------------------
    def off_reason(self, sid: str) -> str:
        pod = self.cfg.get("pod") or {}
        if sid in (pod.get("off") or {}):
            return pod["off"][sid]
        if ".battle" in sid or sid.endswith("battle"):
            return pod.get("battle_why", "the battle is not on this pod")
        return "not in this pod's schedule"

    def mark_off(self):
        """Every stage the lanes know that this pod's schedule leaves out: recorded as skipped with its reason, never waited for."""
        for sid in [*LANES["cpu"], *LANES["gpu"], *LANES["net"]]:
            if sid not in self.active:
                self.book.mark(sid, "skipped", reason=self.off_reason(sid), off_pod=True)
                self.book.done(sid)

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

    def max_s(self, sid: str, lane: str | None = None) -> float:
        """The stage's timeout: its max minutes in p14_schedule.json (the graph RP-11 costs), on the lane it runs on."""
        on = self.sched[sid]["on"]
        lane = lane if lane in on else ("gpu" if self.blender_on == "gpu" and "gpu" in on and lane is None else next(iter(on)))
        return float(on[lane]["max_min"]) * 60

    def blender_max_s(self, sid: str) -> float:
        return self.max_s(sid, self.blender_on)

    def mod(self, m: str, *args) -> list[str]:
        return [PY, "-m", f"{PKG}.{m}", *map(str, args)]

    def wait(self, event: str, until: float) -> bool:
        return self.book.event(event).wait(max(0.0, until - time.time()))

    # --- lanes ----------------------------------------------------------------------------------------------------------------
    def net(self):
        q = self.cfg["qwen"]
        code = ("from huggingface_hub import snapshot_download, hf_hub_download\n"
                f"snapshot_download({q['base']!r})\n"
                f"hf_hub_download({q['style_lora']['hf']!r}, {q['style_lora']['path']!r}, repo_type='dataset')\n"
                "import json; p = json.load(open('config/cloud_pins.json'))['models']['cutout_birefnet']\n"
                "snapshot_download(p['id'], revision=p['revision'])\n")
        try:
            self.stage("weights_qwen", [PY, "-c", code], timeout=self.max_s("weights_qwen"), need=False)
            self.stage("weights", [PY, str(HERE / "p14_ltx.py"), "--prefetch"], timeout=self.max_s("weights"), need=False)
        finally:
            self.book.done("weights_qwen")
            self.book.done("weights")

    def blender_tails(self, root: Path, scene: str, passes, label: str):
        return [(Path(root) / scene / k / "blender.log", self.logs / f"{label}.{k}.blender_tail.txt") for k in passes]

    def stage_a(self):
        a = self.cfg["A"]
        lp = ["-m", "explainer_engine.blender.layout_passes", "render", "--binary", self.binary]
        got, f0_seconds = [], {}
        firsts = [f for f in a["first_frames"] if f"A.frame0.{f['scene']}" in self.active]
        pre = self.preflight(lp, firsts[0]) if firsts else None
        fetched = self.hf_first()   # layouts already on the vault: fetched and checked, not rendered (fix 2)
        for f in firsts:   # the duel first (seconds), then the battle; each one killed at frame0_timeout_s
            name = f"A.frame0.{f['scene']}"
            if f["scene"] in fetched:
                got.append(f["scene"])
                continue
            if pre and f is a["first_frames"][0]:   # the preflight drew it on the card: the same frame, kept
                rc, sec = 0, pre["seconds"]
                self.book.mark(name, "running")
            else:
                self.book.mark(name, "running")
                with Tailer(self.blender_tails(self.lay_f0, f["scene"], [f["pass"]], name)):
                    rc, sec = self.run([PY, *lp, "--scene", f["scene"], "--out", self.lay_f0, "--passes", f["pass"], "--only-frames",
                                        str(f["frame"])], timeout=self.blender_max_s(name), env=self.blender_env,
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
            self.book.mark(name, "ok" if ok else "failed", rc=rc, seconds=sec, on=self.blender_on)
            self.book.done(name)
        missing = [f["scene"] for f in firsts if f["scene"] not in got]
        self.book.mark("A.frame0", "ok" if got else "failed", scenes=got, missing=missing)
        self.book.done("A.frame0")
        ok = True
        for r in a["renders"]:
            name = f"A.{r['scene']}" + ("" if r.get("core", True) else "." + "+".join(r["passes"]))
            if name not in self.active or (r["scene"] in fetched and r.get("core", True)):
                continue
            if not r.get("core", True):
                self.release_core(ok)   # the core passes are done: E may start while the battle line is drawn
            name = f"A.{r['scene']}" + ("" if r.get("core", True) else "." + "+".join(r["passes"]))
            why = None
            if not r.get("core", True):   # the battle's line: only when frame 0's seconds x its frames fit its max (the schedule's)
                budget = self.blender_max_s(name)
                s0 = f0_seconds.get(r["scene"])
                if s0 is None:
                    f0 = round(self.blender_max_s("A.frame0." + r["scene"]))
                    why = f"the {r['scene']} frame 0 did not finish inside {f0} s"
                elif s0 * r["frames"] > budget:
                    why = (f"the {r['scene']} frame 0 took {s0} s: {r['frames']} frames would take ~{round(s0 * r['frames'])} s, "
                           f"over the {round(budget)} s budget")
            if why:
                self.book.mark(name, "skipped", reason=why)
                self.book.done(name)
                done = False
            else:
                timeout = self.blender_max_s(name)
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

    def hf_first(self) -> set[str]:
        """The scenes of ``hf_first`` (p14_stages.json) whose layout files are on the vault with their pinned sha256: frame 0 goes
        where B reads it (``<layouts>_f0/<scene>/<pass>/frames/``), the clips stay on the vault (E fetches them by path and hash),
        and A.frame0.<scene> and A.<scene> are recorded as fetched. Any missing or changed file: the scene renders as before."""
        out = set()
        for scene, spec in (self.cfg.get("hf_first") or {}).items():
            if scene.startswith("_") or f"A.frame0.{scene}" not in self.active:
                continue
            t0 = time.time()
            try:
                got = {}
                for f in [spec["frame0"], spec["manifest"], *spec["clips"]]:
                    p = hf_fetch(f["path"], self.lay_work.parent / "hf_first")
                    sha = sha256_file(p)
                    if sha != f["sha256"]:
                        raise ValueError(f"{f['path']}: sha256 {sha} is not the pinned {f['sha256']}")
                    got[f["path"]] = p
            except Exception as e:   # noqa: BLE001 - the vault copy is a shortcut, never a reason to lose the scene
                self.book.mark(f"A.hf_first.{scene}", "failed", reason=repr(e)[:200])
                continue
            f0 = spec["frame0"]
            dst = self.lay_f0 / scene / f0["pass"] / "frames" / f"frame_{f0['frame']:06d}.png"
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(got[f0["path"]], dst)
            sec = round(time.time() - t0, 1)
            for name in (f"A.frame0.{scene}", f"A.{scene}"):
                if name in self.active:
                    self.book.mark(name, "ok", source="hf", seconds=sec, files=sorted(got))
                    self.book.done(name)
            out.add(scene)
        return out

    def preflight(self, lp: list[str], f: dict) -> dict | None:
        """A.preflight: the first frame 0 (the duel's line) with EEVEE on the card, at most ``PREFLIGHT_S``. Kept (and
        ``blender_env`` switched to the card) only when it rendered and its report's GL renderer is NVIDIA's; else Blender stays on
        the CPU and the frame is drawn again there. Returns the kept row or None."""
        if "G" not in self.active:   # fix 2: only G needed Blender on the card; the duel's passes are small CPU work
            self.book.mark("A.preflight", "ok", chosen="cpu", reason="G is not on this pod: Blender stays on the CPU")
            self.book.done("A.preflight")
            return None
        env, egl = gpu_env(self.env, self.lay_work.parent / "egl")
        row = {"mode_tried": "gpu", "egl": egl, "budget_s": PREFLIGHT_S}
        if env is None:
            self.book.mark("A.preflight", "ok", chosen="cpu", reason="no NVIDIA EGL vendor on this pod", **row)
            self.book.done("A.preflight")
            return None
        self.book.mark("A.preflight", "running", **row)
        with Tailer(self.blender_tails(self.lay_f0, f["scene"], [f["pass"]], "A.preflight")):
            rc, sec = self.run([PY, *lp, "--scene", f["scene"], "--out", self.lay_f0, "--passes", f["pass"], "--only-frames",
                                str(f["frame"])], timeout=min(PREFLIGHT_S, self.max_s("A.preflight", "gpu")), env=env,
                               log_path=self.logs / "A.preflight.log",
                               deadline=self.deadline - self.reserve)
        d = self.lay_f0 / f["scene"] / f["pass"]
        frame = d / "frames" / f"frame_{f['frame']:06d}.png"
        gl = ((read_json(d / "bpy_report.json") or {}).get("gl") or {})
        on_card = "nvidia" in f"{gl.get('vendor', '')} {gl.get('renderer', '')}".lower()
        keep = rc == 0 and frame.exists() and on_card
        frame_s = frame_seconds(d / "progress.jsonl", f["frame"])
        if keep:
            self.blender_env, self.blender_on, self.pre_frame_s = env, "gpu", frame_s
        elif frame.exists():
            frame.unlink()   # drawn by Mesa after all: the CPU loop draws it again under its own record
        self.book.mark("A.preflight", "ok", chosen="gpu" if keep else "cpu", rc=rc, seconds=sec, s_per_frame=frame_s, gl=gl,
                       reason="" if keep else ("not drawn on the NVIDIA renderer" if rc == 0 else f"rc {rc}"), **row)
        self.book.done("A.preflight")
        return {"seconds": sec} if keep else None

    def release_core(self, ok: bool):
        if not self.book.is_done("A.core"):
            self.book.mark("A.core", "ok" if ok else "failed")
            self.book.done("A.core")

    @property
    def pending(self) -> Path:
        return Path(str(self.lay_work) + ".pending.json")   # on the pod's disk, not in the upload

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
        if self.stage("X6.move", move_cmd(still, dst, **x["move"]), timeout=self.max_s("X6.move")):
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

    def g_on_pod(self) -> str | None:
        """None when G may run on the pod, else why not: on the pod only with Blender on the card and the preflight's frame at most
        ``G.on_pod.max_frame_s``; otherwise the J5 shots render free on CI or the creator's PC (D-114)."""
        lim = self.cfg["G"]["on_pod"]["max_frame_s"]
        if self.blender_on != "gpu":
            return "Blender is on the CPU here (A.preflight): G renders free on CI or the PC (D-114)"
        if self.pre_frame_s is None or self.pre_frame_s > lim:
            return f"the preflight frame took {self.pre_frame_s} s on the card, over {lim} s: G renders free on CI or the PC (D-114)"
        return None

    def stage_g(self):
        why = self.missing("G") or self.g_on_pod()
        if why:
            self.book.mark("G", "skipped", reason=why)
        else:
            self.book.mark("G", "running")
            t0 = time.time()
            dl = min(self.deadline - self.reserve, t0 + self.max_s("G"))
            try:
                from explainer_engine.training.pods.p14 import p14_j5
                rc = p14_j5.run(self.step3, self.assets, self.binary, deadline=dl, on_shot=self.g_frames, env=self.blender_env)
            except Exception as e:   # noqa: BLE001 - G failing never stops the GPU lane
                rc = f"error {e!r}"[:200]
            self.book.mark("G", "ok" if rc == 0 else "failed", rc=rc, seconds=round(time.time() - t0, 1), cut_at_min=self.max_s("G") / 60)
        self.settle(f"{self.cfg['hf_root']}/step3/{self.cfg['X']['X3']['first_frame']}")
        self.book.done("G")

    def cpu(self):
        try:
            self.stage_a()
            self.wait("X6.still", self.deadline - self.reserve)
            self.stage_x6_move()
        finally:
            self.settle(f"{self.cfg['hf_root']}/layouts/")   # whatever happened, E waits for no layout clip more
            for s in LANES["cpu"] + ["A.frame0", "A.core", "A", "cpu_done"]:
                self.book.done(s)

    def qwen(self, name: str, stages: list[str], labels, *, scene: str | None = None, need=False) -> bool:
        extra = ["--scene", scene] if scene else []
        ok = self.stage(name, self.mod("p14_qwen", "--stages", ",".join(stages), "--out", self.step3, "--layouts", self.lay_f0,
                                       "--assets", self.assets, *extra), timeout=self.max_s(name), need=need)
        man = read_manifest(self.step3 / "qwen" / "manifest.jsonl")
        names = {j["name"] for j in self.cfg["B"]["jobs"] if j["layout"]["scene"] == scene} if scene else None
        for st, label in labels:
            got = [r for r in man if r.get("stage") == st and (names is None or r.get("name") in names)]
            good = [r for r in got if r.get("status") == "ok"]
            self.book.mark(label, "ok" if got and len(good) == len(got) else "partial" if good else "failed",
                           pictures=len(good), names=[r.get("name") for r in good], process_ok=ok)
            self.book.done(label)
        return ok

    def gpu(self):
        """The card's stages in ``gpu_order`` (p14_stages.json, the order RP-11 costs): a free card takes the first stage whose
        inputs are done (the schedule's needs), so it waits only when nothing of its own is ready: list scheduling, as
        cloud/schedule.py simulates it."""
        left = [s for s in self.cfg["gpu_order"] if s != "F" and s in self.active]
        until = self.deadline - self.reserve
        while left:
            ready = [s for s in left if all(self.book.is_done(n) for n in self.sched[s]["needs"])]
            if not ready:
                if time.time() >= until:
                    ready = left[:1]   # the end reserve: each one is recorded as skipped, with that reason
                else:
                    self.book.wait_change(min(5.0, until - time.time()))
                    continue
            s = ready[0]
            left.remove(s)
            try:
                self.gpu_stage(s)
            except Exception as e:   # noqa: BLE001 - one stage's crash never ends the lane
                self.book.mark(s, "failed", reason=repr(e)[:300])
            self.book.done(s)

    def gpu_stage(self, s: str):
        if s == "qwen1":
            self.qwen("qwen1", ["C", "X6"], QWEN_LABELS["qwen1"])
        elif s == "D":
            self.stage("D", self.mod("p14_cutout", "--out", self.step3, "--assets", self.assets), timeout=self.max_s("D"))
        elif s.startswith("B."):
            scene = s.split(".", 1)[1]
            self.qwen(s, ["B"], (("B", f"B.{scene}.pictures"),), scene=scene, need=True)
        elif s in self.cfg["E_stages"]:
            self.ltx(s, self.cfg["E_stages"][s])
        elif s == "G":
            self.stage_g()
        elif s == "X4":
            fg = self.cfg["X"]["X4"]["frame_from_g"]
            if (self.step3 / "j5" / fg["shot"] / "frames" / f"frame_{fg['frame']:06d}.png").exists():
                self.stage("X4", self.mod("p14_qwen", "--stages", "X4", "--out", self.step3, "--layouts", self.step3,
                                          "--assets", self.assets), timeout=self.max_s("X4"), need=False)
            else:
                self.book.mark("X4", "skipped", reason=self.missing("X4") or "stage G has not rendered the frame X4 edits")
        else:
            raise ValueError(f"no runner for GPU stage {s!r}")

    def ltx(self, s: str, ids: list[str]):
        """One LTX process for the stage's jobs (``P14_JOBS``); its speeds files are tagged with the stage."""
        if s == "X3" and self.missing("X3"):
            self.book.mark(s, "skipped", reason=self.missing("X3"))
            return
        env = dict(self.env, P14_JOBS=",".join(ids), P14_TAG=s)   # its inputs are done: the GPU lane waited for them
        self.stage(s, [PY, str(HERE / "p14_ltx.py")], timeout=self.max_s(s), env=env)
        rows = []
        for name in (f"speeds.{s}.json", f"speeds_extra.{s}.json"):
            p = self.step3 / "ltx" / name
            if p.exists():
                rows += json.loads(p.read_text(encoding="utf-8"))["rows"]
        if rows:
            self.book.mark(s, "ok" if any(r["status"] == "ok" for r in rows) else "failed", clips_ok=sum(r["status"] == "ok" for r in rows),
                           rows=[{k: r.get(k) for k in ("job", "status", "seconds", "reason")} for r in rows])
        for r in rows:
            label = r["job"].split(".", 1)[0]
            if label.startswith("X"):
                self.book.mark(label if label != "X6" else "X6.ltx.clip", r["status"], job=r["job"], seconds=r.get("seconds"),
                               reason=r.get("reason", ""))

    def stage_f(self):
        self.book.mark("F", "running")
        try:
            write_side(self.step3 / "speeds.json", speeds_report(self.step3, self.lay_out, self.book.rows))
            self.book.mark("F", "ok")
        except Exception as e:   # noqa: BLE001
            self.book.mark("F", "failed", reason=repr(e)[:200])

    def main(self) -> int:
        self.mark_off()
        lanes = [threading.Thread(target=self.net, daemon=True), threading.Thread(target=self.cpu, daemon=True)]
        for t in lanes:
            t.start()
        try:
            self.gpu()
        except Exception as e:   # noqa: BLE001 - the record says what broke; the CPU lane and F still run
            self.book.mark("gpu_lane", "failed", reason=repr(e)[:300])
        self.book.event("cpu_done").wait(max(0.0, self.deadline - self.reserve - time.time()))
        self.stage_f()
        ok = [k for k, v in self.book.rows.items() if v.get("status") == "ok"]
        return 0 if ok else 1


def sha256_file(p) -> str:
    import hashlib
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hf_fetch(path: str, dest: Path) -> Path:
    """One vault file (``vano1919/tmr-artifacts``, the dataset every stage reads) under ``dest``."""
    from huggingface_hub import hf_hub_download
    return Path(hf_hub_download("vano1919/tmr-artifacts", path, repo_type="dataset", local_dir=str(dest)))


def read_json(p: Path):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def frame_seconds(progress: Path, index: int) -> float | None:
    """The seconds Blender spent on one frame (render_shot.py's progress.jsonl row), without the scene build and start-up."""
    try:
        for ln in Path(progress).read_text(encoding="utf-8").splitlines():
            row = json.loads(ln) if ln.strip() else {}
            if int(row.get("index", -1)) == index and row.get("seconds") is not None:
                return float(row["seconds"])
    except (OSError, ValueError):
        return None
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
    ltx = {p.stem: load(p) for p in sorted((step3 / "ltx").glob("speeds.*.json"))}
    extra = {p.stem: load(p) for p in sorted((step3 / "ltx").glob("speeds_extra.*.json"))}
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
