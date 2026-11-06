"""The pilot pod's LTX part (PILOT_1MIN_PLAN.md v4): ONE job of ``p15.json`` ``ltx_jobs`` (plain LTX-2.5 distilled image-to-video
from the Qwen first frame, no LoRA, no control video) through the step-3 pod's runner (``p14/p14_ltx.run``: pinned weights, inputs
read from the pod's own disk first, ``ltx/<job>.mp4`` + sidecar, the speeds file). One process per clip, so a hung clip is killed
at its schedule max without taking the next one.

    python3 -m explainer_engine.training.pods.p15.p15_ltx --job <id>        # on the pod (EE_OUT, EE_DEADLINE from the wrapper)
    python3 -m explainer_engine.training.pods.p15.p15_ltx --prefetch        # the LTX-2.5 weights, checked by sha256
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from explainer_engine.training.pods.p14 import p14_ltx as X

HERE = Path(__file__).resolve().parent


def load_cfg() -> dict:
    return json.loads((HERE / "p15.json").read_text(encoding="utf-8"))


def audio_sidecar(mp4: Path, *, sh=subprocess.run) -> dict:
    """v4 (Fable 16:42 UTC): the clip's native audio stays in the mp4 and is also written beside it as ``<job>.wav``
    (PCM 16-bit), with ``<job>.audio.json`` saying whether the mp4 had an audio stream at all."""
    wav, side = mp4.with_suffix(".wav"), mp4.with_suffix(".audio.json")
    probe = sh(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=codec_name,sample_rate,channels",
                "-of", "json", str(mp4)], capture_output=True, text=True)
    streams = json.loads(probe.stdout or "{}").get("streams", []) if probe.returncode == 0 else []
    doc = {"mp4": mp4.name, "has_audio": bool(streams), "streams": streams, "wav": None}
    if streams:
        r = sh(["ffmpeg", "-y", "-v", "error", "-i", str(mp4), "-vn", "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True)
        if r.returncode == 0 and wav.is_file():
            doc["wav"] = {"path": wav.name, "sha256": hashlib.sha256(wav.read_bytes()).hexdigest(), "bytes": wav.stat().st_size}
        else:
            doc["wav_error"] = (r.stderr or "")[-300:]
    side.write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="pilot pod: one LTX clip")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--job")
    g.add_argument("--prefetch", action="store_true")
    a = ap.parse_args(argv)
    cfg = load_cfg()
    ltx = cfg["ltx"]
    out = Path(os.environ.get("EE_OUT", "/workspace/out"))
    log = X.Log(out)
    if a.prefetch:
        bad = X.download_base(ltx, "ltx25", log)
        log.ev("prefetch_done", bad=bad)
        return 1 if bad else 0
    jobs = [j for j in cfg["ltx_jobs"] if j["id"] == a.job]
    if len(jobs) != 1:
        raise SystemExit(f"no LTX job {a.job!r} in p15.json")
    rows = X.run(ltx, {"jobs": jobs}, out, float(os.environ["EE_DEADLINE"]), log, speeds_name=f"speeds_{a.job}.json")
    ok = bool(rows) and rows[-1]["status"] == "ok"
    mp4 = out / "ltx" / f"{a.job}.mp4"
    if ok and mp4.is_file():
        log.ev("audio", **audio_sidecar(mp4))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
