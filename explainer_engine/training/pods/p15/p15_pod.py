"""The pilot pod's runner (PILOT_1MIN_PLAN.md v4; the creator 2026-11-06 15:25 / 16:05 UTC; Fable 15:52 UTC: option A only, 185
frames, the room clip is the two-shot). No Blender on the pod: the stills were rendered free and are on HF, pinned in ``p15.json``.
Two lanes, as ``p15_schedule.json`` (the file ``runpod create --schedule`` costs under RP-11) draws them, so the card never waits on
a download it does not need:

- net: Qwen-Image-2.1 + the xworld_v2 LoRA (``weights_qwen``), then the LTX-2.5 weights checked by sha256 (``weights_ltx25``);
- gpu: ``qwen_restyle`` (``p15_qwen``: the 8 edits) as soon as Qwen's weights are in, then the 8 clips ``ltx_c1`` ..
  ``ltx_c8`` (v4: run order c1-c4, c6, c7, c8, c5; ``p15_ltx``, one process per clip, each started when its first frame exists and the LTX weights are checked), then ``F``.

Each stage is its own process with its schedule max as timeout; a failed stage is recorded and the next one runs (a clip whose first
frame was not drawn is skipped with that reason). Records: ``stages.json``, ``stages.txt``, ``t.jsonl`` under ``$EE_OUT`` (the wrapper
uploads ``$EE_OUT`` to HF ``route_test_2026-11/pilot/`` as files land: OR-33).

    python3 -m explainer_engine.training.pods.p15.p15_pod            # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
    python3 -m explainer_engine.training.pods.p15.p15_pod --plan     # the stages, their lanes and timeouts, no work
    python3 -m explainer_engine.training.pods.p15.p15_pod --only qwen   # the creator 2026-11-06 17:34 UTC: only the 8 Qwen pictures,
                                                                     # no LTX weights, no clips, three look variants per still = 24 pictures
                                                                     # (``p15q_schedule.json``, ``p15q.sh``)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import time
from pathlib import Path

from explainer_engine.training.pods.p14 import p14_pod as P

HERE = Path(__file__).resolve().parent
PY = sys.executable
PKG = "explainer_engine.training.pods.p15"
CLIP_STAGES = ["ltx_c1", "ltx_c2", "ltx_c3", "ltx_c4", "ltx_c6", "ltx_c7", "ltx_c8", "ltx_c5"]   # v4: build.CLIPS order, c5 + c8 last
LANES = {"net": ["weights_qwen", "weights_ltx25"], "gpu": ["qwen_restyle", *CLIP_STAGES, "F"]}
QWEN_LANES = {"net": ["weights_qwen"], "gpu": ["qwen_restyle", "F"]}   # --only qwen: never the LTX weights, never a clip


def load_cfg() -> dict:
    return json.loads((HERE / "p15.json").read_text(encoding="utf-8"))


def load_schedule(only: str | None = None) -> dict:
    return json.loads((HERE / ("p15q_schedule.json" if only == "qwen" else "p15_schedule.json")).read_text(encoding="utf-8"))


def timeouts(schedule: dict) -> dict[str, float]:
    """Stage -> seconds: its max in the schedule on its lane (the run's worst case is what RP-11 priced)."""
    out = {}
    for s in schedule["stages"]:
        (lane, t), = s["on"].items()
        out[s["id"]] = t["max_min"] * 60
    return out


class Pod:
    def __init__(self, cfg: dict, schedule: dict, out: Path, *, deadline: float, run=P.run_proc, only: str | None = None):
        self.cfg, self.out, self.deadline, self.run, self.only = cfg, Path(out), deadline, run, only
        self.book = P.Book(self.out)
        self.book.events = {k: threading.Event() for k in ("weights_qwen", "weights_ltx25")}
        self.reserve = schedule["end_reserve_min"] * 60
        self.t = timeouts(schedule)
        self.logs = self.out / "logs"
        self.logs.mkdir(parents=True, exist_ok=True)
        self.env = dict(os.environ, EE_OUT=str(self.out), PYTHONUNBUFFERED="1", XW_GPU_MODE=cfg["qwen"]["gpu_mode"],
                        P14_LOCAL_ROOTS=json.dumps([[cfg["hf_root"], str(self.out)]]))

    def stage(self, name: str, cmd, *, why: str | None = None) -> bool:
        if why is None and time.time() > self.deadline - self.reserve:
            why = "inside the end reserve"
        if why:
            self.book.mark(name, "skipped", reason=why)
            self.book.done(name)
            return False
        self.book.mark(name, "running")
        rc, sec = self.run(cmd, timeout=self.t[name], env=self.env, log_path=self.logs / f"{name}.log",
                           deadline=self.deadline - self.reserve)
        self.book.mark(name, "ok" if rc == 0 else "failed", rc=rc, seconds=sec)
        self.book.done(name)
        return rc == 0

    def mod(self, m: str, *args) -> list[str]:
        return [PY, "-m", f"{PKG}.{m}", *map(str, args)]

    def net(self):
        q = self.cfg["qwen"]
        code = ("from huggingface_hub import snapshot_download, hf_hub_download\n"
                f"snapshot_download({q['base']!r})\n"
                f"hf_hub_download({q['style_lora']['hf']!r}, {q['style_lora']['path']!r}, repo_type='dataset')\n")
        self.stage("weights_qwen", [PY, "-c", code])
        if self.only != "qwen":
            self.stage("weights_ltx25", self.mod("p15_ltx", "--prefetch"))

    def gpu(self):
        until = self.deadline - self.reserve
        self.book.events["weights_qwen"].wait(max(0.0, until - time.time()))
        self.stage("qwen_restyle", self.mod("p15_qwen", "--out", self.out, *(["--variants"] if self.only == "qwen" else [])),
                   why=None if self.book.ok("weights_qwen") else "the Qwen weights did not download")
        if self.only == "qwen":
            return
        self.book.events["weights_ltx25"].wait(max(0.0, until - time.time()))
        fails = 0
        for name, job in self.cfg["clips"].items():
            ff = self.out / "first_frames" / f"{job['first_frame_of']}.png"
            why = ("the LTX-2.5 weights are missing or wrong" if not self.book.ok("weights_ltx25") else
                   f"no first frame {ff.name} (the restyle did not draw it)" if not ff.is_file() else
                   f"{fails} LTX failures (the plan's stop condition)" if fails >= self.cfg["max_ltx_failures"] else None)
            if not self.stage(name, self.mod("p15_ltx", "--job", job["job"]), why=why) and why is None:
                fails += 1

    def stage_f(self):
        self.book.mark("F", "running")
        try:
            rows = {k: v for k, v in self.book.rows.items() if k != "F"}
            ltx = {}
            for f in sorted((self.out / "ltx").glob("speeds_*.json")):
                ltx[f.stem[len("speeds_"):]] = json.loads(f.read_text(encoding="utf-8"))
            qwen = [json.loads(x) for x in (self.out / "qwen" / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
                    if x.strip()] if (self.out / "qwen" / "manifest.jsonl").is_file() else []
            audio = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in sorted((self.out / "ltx").glob("*.audio.json"))}
            P.write_side(self.out / "speeds.json", {"schema": "p15_speeds/1", "stages": rows, "ltx": ltx, "audio": audio,
                                                    "qwen_s": [q.get("seconds") for q in qwen if q.get("status") == "ok"]})
            self.book.mark("F", "ok")
        except Exception as e:   # noqa: BLE001
            self.book.mark("F", "failed", reason=repr(e)[:200])

    def main(self) -> int:
        lane = threading.Thread(target=self.net, daemon=True)
        lane.start()
        try:
            self.gpu()
        except Exception as e:   # noqa: BLE001 - the record says what broke; F still runs
            self.book.mark("gpu_lane", "failed", reason=repr(e)[:300])
        self.stage_f()
        if self.only == "qwen":
            return 0 if self.book.ok("qwen_restyle") else 1
        return 0 if any(self.book.ok(n) for n in self.cfg["clips"]) else 1


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true")
    ap.add_argument("--only", choices=["qwen"], help="run only the Qwen restyle (no LTX weights, no clips)")
    a = ap.parse_args(argv)
    cfg, sch = load_cfg(), load_schedule(a.only)
    if a.plan:
        print(json.dumps({"lanes": QWEN_LANES if a.only else LANES, "timeouts_s": timeouts(sch), "clips": {} if a.only else cfg["clips"]}, indent=1))
        return 0
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    return Pod(cfg, sch, out, deadline=float(os.environ["EE_DEADLINE"]), only=a.only).main()


if __name__ == "__main__":
    sys.exit(main())
