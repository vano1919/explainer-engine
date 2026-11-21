"""Give the overlay demo of 2026-11-12 its new sound without making the picture again (W1, free): the narration is taken back out of
the old file by Demucs (``htdemucs``, vocals stem; the Kokoro scratch read is the only voice in it), the old sound plan's events
(``mix_report.json``) are played from the library by ``demo_mix.build`` (``demo_sound``: a bed per place, a real take per
motion), and the new mix goes under the old picture (video stream copied). The final file is measured by ``qa/sound_realism``.

    python -m explainer_engine.overlay.demo_resound <demo folder> --out <dir> [--timeline <scene_timeline.json>]
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import numpy as np
import soundfile as sf

from explainer_engine.core.store import write_json_atomic
from explainer_engine.overlay import demo_mix as MIX
from explainer_engine.overlay import demo_script as D
from explainer_engine.qa import sound_realism as R


def narration_back(video: Path, work: Path) -> np.ndarray:
    """The voice of a finished file (Demucs vocals, CPU), mono at the mix's rate."""
    wav = work / "demo_audio.wav"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-ac", "2", "-ar", "44100", str(wav)], check=True)
    subprocess.run([sys.executable, "-m", "demucs", "--two-stems", "vocals", "-n", "htdemucs", "-o", str(work / "sep"), str(wav)],
                   check=True, capture_output=True)
    v, rate = sf.read(work / "sep" / "htdemucs" / "demo_audio" / "vocals.wav", dtype="float32")
    v = v.mean(axis=1) if v.ndim > 1 else v
    n = int(round(len(v) * MIX.SR / rate))
    return np.interp(np.linspace(0, len(v) - 1, n), np.arange(len(v)), v).astype(np.float32)


def specs_from(report: dict) -> list[dict]:
    """The old sound plan, per shot, from the mix report's event list (cls, t in frames of the shot, dur, gain, item)."""
    by: dict[int, list] = {}
    for e in report["events"]:
        by.setdefault(e["shot_no"], []).append({k: e[k] for k in ("cls", "t", "dur", "gain", "item") if k in e})
    return [{"shot_no": no, "sound": by.get(no, [])} for no in sorted(s["no"] for s in D.SHOTS)]


def run(demo: Path, out: Path, timeline: dict | None = None, sfx_db: float = 0.0, label: str = "A") -> dict:
    out.mkdir(parents=True, exist_ok=True)
    video = demo / "demo_overlay_2min.mp4"
    old = json.loads((demo / "mix_report.json").read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as d:
        voice = narration_back(video, Path(d))
    res = MIX.build(D.SHOTS, specs_from(old), None, None, out / "stems", narration_track=voice)
    total = sum(s["dur"] for s in D.SHOTS)
    mix = MIX.mix_range(res["stems"], 0, total, sfx_db=sfx_db)   # B: the overlay sounds sfx_db louder (a listening A/B)
    sf.write(out / "mix.wav", mix, MIX.SR)
    new = out / f"demo_overlay_2min_resound_{label}.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(out / "mix.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "256k", "-ar", str(MIX.SR), "-shortest", str(new)], check=True)
    rep = res["report"]
    rep["sfx_db_offset"] = sfx_db
    rep["narration_source"] = "Demucs htdemucs vocals of the old demo file (the Kokoro scratch read)"
    write_json_atomic(out / "mix_report.json", rep)
    tl = timeline or {"cuts": [MIX.starts(D.SHOTS)[s["no"]] for s in D.SHOTS[1:]],
                      "events": [{"at_s": e["abs_t"], "dur_s": e["dur_s"], "class": e["cls"]} for e in rep["events"]],
                      "places": [{k: p[k] for k in ("start_s", "end_s", "place")} for p in rep["places"]]}
    gate = R.measure(new, tl)
    write_json_atomic(out / f"sound_realism_{label}.json", gate)
    return {"video": str(new), "gate": {r["gate"]: r["status"] for r in gate["rows"]}, "verdict": gate["verdict"],
            "sfx_above_bed_db": round(rep["sfx_above_bed_db"] + sfx_db, 2), "bed_under_narration_lu": rep["bed_under_narration_lu"]}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="demo_resound")
    ap.add_argument("demo")
    ap.add_argument("--out", required=True)
    ap.add_argument("--timeline")
    ap.add_argument("--sfx-db", type=float, default=0.0)
    ap.add_argument("--label", default="A")
    a = ap.parse_args(argv)
    tl = json.loads(Path(a.timeline).read_text(encoding="utf-8")) if a.timeline else None
    print(json.dumps(run(Path(a.demo), Path(a.out), tl, a.sfx_db, a.label), indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
