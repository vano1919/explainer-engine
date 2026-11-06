"""The lean step-3 pod's runner (STEP3_POD_PLAN_LEAN_ka.md; the creator 2026-11-06 13:21 UTC, stage G 13:25 UTC, extras X1-X6 13:33
UTC): every stage of ``p14_stages.json`` in its order, each one as its own process, so one failed stage is recorded and the next one
runs (a stage whose input a failed stage should have made is skipped with that reason). ``p14.sh`` starts it inside pod_wrapper.sh,
which uploads ``$EE_OUT`` as files land (OR-33): ``$EE_OUT/layouts/`` -> HF ``route_test_2026-11/layouts/`` and ``$EE_OUT/step3/``
-> ``route_test_2026-11/step3/`` (the pod's heartbeat file is ``route_test_2026-11/beat.txt``, so the wrapper's prefix is
``route_test_2026-11``).

Three lanes, so the card is never idle while the CPU works and the paid time is not stretched:

- net (from the start): the LTX weights of both bases, checked by sha256 once (``p14_ltx.py --prefetch``), Qwen-Image-2.1 and BiRefNet;
- cpu: A (Blender layout passes: first the line frame 0 of both scenes for B, then the duel's clay and the battle's colour, depth and
  line), X6.move (the still's FFmpeg camera move), then G (the J5 shots of the pilot window, ``nice``d, stopped at the deadline
  reserve; it starts when D's cut-outs exist);
- gpu: B + C + X6.still (one Qwen process) -> D (BiRefNet) -> E (the five core LTX jobs, then the extras X1, X2, X5, X3, X6.ltx in one
  LTX process) -> X4 (a second Qwen process, when stage G has the frame) -> F (speeds.json).

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
         "gpu": ["B", "C", "X6.still", "D", "E", "X1", "X2", "X5", "X3", "X6.ltx", "X4", "F"]}
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
        self.events = {k: threading.Event() for k in ("A.frame0", "A", "B", "weights", "D", "G", "X6.still", "cpu_done")}

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
    """(return code or 'timeout'/'oserror', seconds) of one stage process; never raises."""
    t0 = time.time()
    if deadline:
        left = deadline - time.time()
        timeout = max(1.0, min(timeout or left, left))
    try:
        with open(log_path or os.devnull, "a", encoding="utf-8") as lf:
            rc = subprocess.run(cmd, stdout=lf, stderr=subprocess.STDOUT, timeout=timeout, env=env).returncode
    except subprocess.TimeoutExpired:
        rc = "timeout"
    except OSError as e:
        rc = f"oserror {e}"[:120]
    return rc, round(time.time() - t0, 1)


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

    # --- helpers -------------------------------------------------------------------------------------------------------------
    def missing(self, name: str) -> str | None:
        bad = [n for n in NEEDS.get(name, []) if not self.book.ok(n)]
        return f"needs {', '.join(bad)}, which did not finish" if bad else None

    def stage(self, name: str, cmd, *, timeout=None, env=None, need=True) -> bool:
        why = self.missing(name) if need else None
        if why is None and time.time() > self.deadline - self.reserve:
            why = "inside the end reserve"
        if why:
            self.book.mark(name, "skipped", reason=why)
            self.book.done(name)
            return False
        self.book.mark(name, "running")
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

    def stage_a(self):
        a = self.cfg["A"]
        lp = ["-m", "explainer_engine.blender.layout_passes", "render", "--binary", self.binary]
        ok0 = True
        for f in a["first_frames"]:
            rc, sec = self.run([PY, *lp, "--scene", f["scene"], "--out", self.lay_f0, "--passes", f["pass"], "--only-frames",
                                str(f["frame"])], timeout=1800, env=self.env, log_path=self.logs / "A.frame0.log",
                               deadline=self.deadline - self.reserve)
            src = self.lay_f0 / f["scene"] / f["pass"] / "frames" / f"frame_{f['frame']:06d}.png"
            ok0 = ok0 and rc == 0 and src.exists()
            if src.exists():
                dst = self.lay_out / f["scene"] / f["pass"] / f"frame0_{f['frame']:06d}.png"
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        self.book.mark("A.frame0", "ok" if ok0 else "failed")
        self.book.done("A.frame0")
        ok = True
        for r in a["renders"]:
            name = f"A.{r['scene']}"
            done = self.stage(name, [PY, *lp, "--scene", r["scene"], "--out", self.lay_work, "--passes", ",".join(r["passes"])],
                              timeout=a["timeout_s"], need=False)
            ok = ok and done
            if done:
                self.publish_layout(r["scene"])
        self.book.mark("A", "ok" if ok else "failed")
        self.book.done("A")

    def publish_layout(self, scene: str):
        """The clip mp4s and the manifest of one scene into ``$EE_OUT/layouts/<scene>/<pass>/`` (the PNG frames stay on the pod's
        disk; the upload carries what LTX and the verdict page read)."""
        d = self.lay_work / scene
        man = json.loads((d / "layout_manifest.json").read_text(encoding="utf-8"))
        dst = self.lay_out / scene
        dst.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(d / "layout_manifest.json", dst / "layout_manifest.json")
        for kind, row in man["passes"].items():
            (dst / kind).mkdir(parents=True, exist_ok=True)
            for c in row.get("clips", {}).values():
                shutil.copyfile(d / kind / c["path"], dst / kind / c["path"])

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
                first_frame(Image.open(src), (self.cfg["X"]["X3"]["width"], self.cfg["X"]["X3"]["height"])).save(ff)

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
                rc = p14_j5.run(self.step3, self.assets, self.binary, deadline=dl, on_shot=self.g_frames)
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
            self.book.done("A.frame0")
            self.book.done("A")
            self.book.done("G")
            self.book.done("cpu_done")

    def gpu(self):
        q = self.cfg["qwen"]
        self.wait("A.frame0", self.deadline - self.reserve)
        stages = ["C", "X6"] + (["B"] if self.book.ok("A.frame0") else [])
        if not self.book.ok("A.frame0"):
            self.book.mark("B", "skipped", reason=self.missing("B"))
        name = "qwen1"
        ok = self.stage(name, self.mod("p14_qwen", "--stages", ",".join(stages), "--out", self.step3, "--layouts", self.lay_f0,
                                       "--assets", self.assets), timeout=q["timeout_s"], need=False)
        man = read_manifest(self.step3 / "qwen" / "manifest.jsonl")
        for st, label in (("B", "B"), ("C", "C"), ("X6", "X6.still")):
            if st in stages:
                got = [r for r in man if r.get("stage") == st]
                self.book.mark(label, "ok" if got and all(r.get("status") == "ok" for r in got) else "failed",
                               pictures=len([r for r in got if r.get("status") == "ok"]), process_ok=ok)
            self.book.done(label)
        self.stage("D", self.mod("p14_cutout", "--out", self.step3, "--assets", self.assets), timeout=self.cfg["D"]["timeout_s"])
        self.wait("A", self.deadline - self.reserve)
        self.wait("weights", self.deadline - self.reserve)
        self.stage("E", [PY, str(HERE / "p14_ltx.py")], timeout=None)
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
