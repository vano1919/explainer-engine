"""P1's pod runner (EXEC_QUEUE.md P1, the creator 2026-11-06 16:18 UTC): the rest of the 60 s minute after the p15 pod. p15 already
drew the 7 room restyles and the battle frame 0 and animated the room two-shot and the battle frame 0; this pod reuses those first
frames (read from HF ``route_test_2026-11/pilot/first_frames/``, pinned by sha256 in ``p16.json``) and does only what is missing:
Qwen restyles of the three new battle stills, then LTX-2.5 distilled i2v for the other 8 clips of the minute.

The order is RP-11's (``p16_schedule.json``): the room clips need no restyle, so the card starts them as soon as the LTX weights are
in, while Qwen's weights download on the net lane; the restyle runs after them and the three battle clips last (so the end of the
table is what is dropped when the deadline's reserve is reached). Each stage is its own process with its schedule max as timeout;
the stage records and the per-picture and per-clip uploads are ``p15_pod``'s (OR-33).

    python3 -m explainer_engine.training.pods.p16.p16_pod            # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
    python3 -m explainer_engine.training.pods.p16.p16_pod --plan     # the stages, lanes and timeouts, no work
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
from explainer_engine.training.pods.p15 import p15_pod as P15

HERE = Path(__file__).resolve().parent
PKG = "explainer_engine.training.pods.p16"
ROOM_CLIPS = ("ltx_room_establishing", "ltx_room_close_host", "ltx_room_close_guest", "ltx_room_reverse", "ltx_room_insert_table")
BATTLE_CLIPS = ("ltx_battle_wide_high", "ltx_battle_front_mid", "ltx_battle_f200")
# the committed order: weights of the LTX first (the room clips wait for nothing else), then Qwen's, the restyle, the battle clips
LANES = {"net": ["weights_ltx25", "weights_qwen"], "gpu": [*ROOM_CLIPS, "qwen_restyle", *BATTLE_CLIPS, "F"]}


def load_cfg() -> dict:
    return json.loads((HERE / "p16.json").read_text(encoding="utf-8"))


def load_schedule() -> dict:
    return json.loads((HERE / "p16_schedule.json").read_text(encoding="utf-8"))


class Pod(P15.Pod):
    def mod(self, m: str, *args) -> list[str]:
        return [P15.PY, "-m", f"{PKG}.{m}", *map(str, args)]

    def net(self):
        q = self.cfg["qwen"]
        self.stage("weights_ltx25", self.mod("p16_ltx", "--prefetch"))
        code = ("from huggingface_hub import snapshot_download, hf_hub_download\n"
                f"snapshot_download({q['base']!r})\n"
                f"hf_hub_download({q['style_lora']['hf']!r}, {q['style_lora']['path']!r}, repo_type='dataset')\n")
        self.stage("weights_qwen", [P15.PY, "-c", code])

    def clip(self, name: str, fails: int) -> bool:
        """One clip stage; returns True when it counts as a failure (it ran and did not finish)."""
        job = self.cfg["clips"][name]
        ff = job["first_frame_of"]
        local = self.out / "first_frames" / f"{ff}.png"
        drawn_here = job.get("from") == "qwen_restyle"
        why = ("the LTX-2.5 weights are missing or wrong" if not self.book.ok("weights_ltx25") else
               f"no first frame {local.name} (the restyle did not draw it)" if drawn_here and not local.is_file() else
               f"{fails} LTX failures (the plan's stop condition)" if fails >= self.cfg["max_ltx_failures"] else None)
        return not self.stage(name, self.mod("p16_ltx", "--job", job["job"]), why=why) and why is None

    def gpu(self):
        until = self.deadline - self.reserve
        self.book.events["weights_ltx25"].wait(max(0.0, until - time.time()))
        fails = 0
        for name in ROOM_CLIPS:
            fails += self.clip(name, fails)
        self.book.events["weights_qwen"].wait(max(0.0, until - time.time()))
        self.stage("qwen_restyle", self.mod("p16_qwen", "--out", self.out),
                   why=None if self.book.ok("weights_qwen") else "the Qwen weights did not download")
        for name in BATTLE_CLIPS:
            fails += self.clip(name, fails)

    def main(self) -> int:
        lane = threading.Thread(target=self.net, daemon=True)
        lane.start()
        try:
            self.gpu()
        except Exception as e:   # noqa: BLE001 - the record says what broke; F still runs
            self.book.mark("gpu_lane", "failed", reason=repr(e)[:300])
        self.stage_f()
        return 0 if any(self.book.ok(n) for n in self.cfg["clips"]) else 1

    def stage_f(self):
        super().stage_f()
        # the p15 record is "p15_speeds/1" (a name only); this pod's file says which pod wrote it
        f = self.out / "speeds.json"
        if f.is_file():
            d = json.loads(f.read_text(encoding="utf-8"))
            d["schema"] = "p16_speeds/1"
            P.write_side(f, d)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--plan", action="store_true")
    a = ap.parse_args(argv)
    cfg, sch = load_cfg(), load_schedule()
    if a.plan:
        print(json.dumps({"lanes": LANES, "timeouts_s": P15.timeouts(sch), "clips": cfg["clips"]}, indent=1))
        return 0
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    return Pod(cfg, sch, out, deadline=float(os.environ["EE_DEADLINE"])).main()


if __name__ == "__main__":
    sys.exit(main())
