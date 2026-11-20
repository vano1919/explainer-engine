"""Lip-sync measurer of a speaking shot (BP-133, the SyncNet method; the owner chose SyncNet by card, 2026-11-20 20:34 UTC).

BP-133 is a ``hypothesis`` rule of severity REVIEW: its 80 ms limit has no found source (only the method does). So a measured offset above
``lipsync_review_frames`` frames is reported as ``status FAIL`` with a detail starting ``REVIEW:`` (the convention of the hypothesis rules in
``qa/send_validators.py``); there is no fourth status. Nothing here is a pass unless it was measured and trusted.

SyncNet itself (``joonson/syncnet_python``, MIT) is NOT copied into the repo: the adapter calls an external checkout named by the environment
variable ``SYNCNET_DIR`` (or the first line of the gitignored ``tools/syncnet_dir.txt``). A missing checkout, weights, ``torch``,
``python_speech_features`` or ffmpeg is NOT_RUN with the reason. SyncNet wants 25 fps video and 16 kHz mono audio; the adapter converts a COPY
for the measurement only. Its offset is in whole video frames, so at 25 fps one step is 40 ms (the limit of 80 ms is 2 steps).

Codes (each has a test that triggers exactly it):
- LS-01 no face track found (clip shorter than the track minimum, no face, face too small): NOT_RUN, never a pass.
- LS-02 offset magnitude above ``lipsync_review_frames``: REVIEW (status FAIL, detail ``REVIEW:``).
- LS-03 confidence below ``conf_min`` (or ``conf_min`` still null): NOT_RUN, never a pass and never a fail.
- LS-04 several tracks: all are listed; the verdict uses the worst offset among the tracks with ``conf >= conf_min``.

``value`` is SyncNet's signed offset of the most confident trusted track, in ms. SIGN, measured 2026-11-20 on the SyncNet example clip: delaying the
sound by 3 frames lowered the offset by exactly 3 and advancing it by 3 raised it by exactly 3, so a POSITIVE offset means the sound comes BEFORE
the picture (audio early), a negative one that it comes after (audio late).
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Callable

from explainer_engine.standards import sourced_rules as SR

PASS, FAIL, NOT_RUN = "PASS", "FAIL", "NOT_RUN"
FPS = 25                                # SyncNet's input rate
AUDIO_HZ = 16000                        # SyncNet's input audio rate
FRAME_MS = 1000 // FPS                  # one offset step: 40 ms
ROOT = Path(__file__).resolve().parents[2]
TOLERANCES = Path(__file__).with_name("lipsync_tolerances.json")
HYPOTHESIS = "BP-133 hypothesis (the 80 ms limit has no found source), REVIEW-level, not binding until the owner has seen it"
STEP_NOTE = f"offset measured in whole frames of {FRAME_MS} ms at {FPS} fps; positive = sound before the picture (measured on SyncNet's example clip with known shifts)"


class LipsyncUnavailable(RuntimeError):
    """The measurer cannot run here (no checkout, weights, torch, ffmpeg): the caller says NOT_RUN."""


def tolerances() -> dict:
    """``{"conf_min": float | None, "min_track_frames": int | None}`` from ``lipsync_tolerances.json``."""
    doc = json.loads(TOLERANCES.read_text(encoding="utf-8"))
    return {k: doc[k]["value"] for k in ("conf_min", "min_track_frames")}


def review_frames() -> int:
    return int(SR.T("BP-133", "lipsync_review_frames"))


def _checkout() -> Path:
    raw = os.environ.get("SYNCNET_DIR")
    if not raw:
        f = ROOT / "tools" / "syncnet_dir.txt"
        raw = f.read_text(encoding="utf-8").splitlines()[0].strip() if f.is_file() and f.read_text(encoding="utf-8").strip() else ""
    if not raw:
        raise LipsyncUnavailable("SyncNet checkout not set (env SYNCNET_DIR or tools/syncnet_dir.txt)")
    d = Path(raw)
    if not (d / "SyncNetInstance.py").is_file() or not (d / "run_pipeline.py").is_file():
        raise LipsyncUnavailable(f"SYNCNET_DIR {d} is not a syncnet_python checkout")
    if not (d / "data" / "syncnet_v2.model").is_file():
        raise LipsyncUnavailable("SyncNet weights missing (data/syncnet_v2.model; run download_model.sh in the checkout)")
    return d


def _convert(src: Path, out_dir: Path) -> Path:
    """One 25 fps copy of the clip with its sound as 16 kHz mono (run_pipeline.py takes the sound from the same file); the original is never touched."""
    out = out_dir / "clip25.avi"
    cmd = ["ffmpeg", "-y", "-v", "error", "-i", str(src), "-r", str(FPS), "-ac", "1", "-ar", str(AUDIO_HZ), str(out)]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=1800)
    except FileNotFoundError as exc:
        raise LipsyncUnavailable("ffmpeg is missing") from exc
    if r.returncode != 0:
        raise LipsyncUnavailable("ffmpeg could not convert the clip: " + r.stderr.decode("utf-8", "replace")[-200:])
    return out


def syncnet_runner(path: Path, min_track_frames: int | None = None) -> dict | None:
    """The real measurer: face detection and tracking (``run_pipeline.py``) and ``SyncNetInstance.evaluate`` on every face track of a copy of ``path``
    converted to 25 fps and 16 kHz. Written from the files read on the SyncNet master (``run_pipeline.py``, ``run_syncnet.py``); run on an install on 2026-11-20 (CPU, example clip: offset 4 frames, 3 on the README's own demo). Raises ``LipsyncUnavailable`` when it cannot run here."""
    checkout = _checkout()
    try:
        import torch  # noqa: F401  (heavy imports only here)
        import python_speech_features  # noqa: F401
    except ImportError as exc:
        raise LipsyncUnavailable(f"missing Python package: {exc.name}") from exc
    with tempfile.TemporaryDirectory() as tmp:
        tmp_dir = Path(tmp)
        video = _convert(Path(path), tmp_dir)
        cmd = [sys.executable, "run_pipeline.py", "--videofile", str(video), "--reference", "clip", "--data_dir", str(tmp_dir / "work")]
        if min_track_frames:
            cmd += ["--min_track", str(int(min_track_frames))]
        r = subprocess.run(cmd, cwd=checkout, capture_output=True, timeout=3600)
        if r.returncode != 0:
            raise LipsyncUnavailable("run_pipeline.py failed: " + r.stderr.decode("utf-8", "replace")[-200:])
        crops = sorted((tmp_dir / "work" / "pycrop" / "clip").glob("0*.avi"))
        if not crops:
            return {"tracks": [], "fps": FPS}
        sys.path.insert(0, str(checkout))
        try:
            from argparse import Namespace
            from SyncNetInstance import SyncNetInstance
            opt = Namespace(tmp_dir=str(tmp_dir / "work" / "pytmp"), reference="clip", batch_size=20, vshift=15,
                            initial_model=str(checkout / "data" / "syncnet_v2.model"))
            net = SyncNetInstance()
            net.loadParameters(opt.initial_model)
            tracks = []
            for crop in crops:
                offset, conf, _dists = net.evaluate(opt, videofile=str(crop))
                tracks.append({"offset_frames": int(offset), "offset_ms": FRAME_MS * int(offset), "conf": float(conf),
                               "frames": _frames(crop)})
        finally:
            sys.path.remove(str(checkout))
    return {"tracks": tracks, "fps": FPS}


def _frames(video: Path) -> int:
    r = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries", "stream=nb_read_frames",
                        "-of", "csv=p=0", str(video)], capture_output=True, timeout=300)
    try:
        return int(r.stdout.decode().strip())
    except ValueError:
        return 0


def measure_lipsync(path, *, runner: Callable | None = None) -> dict | None:
    """``{"tracks": [{"offset_frames", "offset_ms", "conf", "frames"}], "fps": 25}`` of one clip; ``runner(path)`` is injectable (the tests use a fake,
    so no torch is needed). Raises ``LipsyncUnavailable`` when the real measurer cannot run."""
    tol = tolerances()
    if runner is not None:
        return runner(Path(path))
    return syncnet_runner(Path(path), tol["min_track_frames"])


def _speaking(path: Path, speaking: bool | None) -> bool | None:
    if speaking is not None:
        return bool(speaking)
    side = path.with_suffix(".lipsync.json")
    if side.is_file():
        doc = json.loads(side.read_text(encoding="utf-8"))
        if isinstance(doc, dict) and "speaking" in doc:
            return bool(doc["speaking"])
    return None


def _not_run(detail: str) -> dict:
    return {"status": NOT_RUN, "value": None, "detail": detail}


def _fmt(t: dict) -> str:
    return f"{t['offset_ms']:+d} ms ({t['offset_frames']:+d} fr, conf {t['conf']:.2f}, {t.get('frames', '?')} fr)"


def lipsync_clip(path, speaking: bool | None = None, runner: Callable | None = None) -> dict:
    """BP-133: the lip-sync offset of a speaking shot. ``speaking`` is the argument or ``<clip>.lipsync.json`` ``{"speaking": true}``; a clip not
    marked as speaking is NOT_RUN. See the module text for LS-01..LS-04."""
    p = Path(path)
    if not _speaking(p, speaking):
        return _not_run("not a speaking shot: nothing to measure")
    try:
        res = measure_lipsync(p, runner=runner)
    except LipsyncUnavailable as exc:
        return _not_run(f"lip sync not measured: {exc}")
    tracks = list((res or {}).get("tracks") or [])
    if not tracks:
        return _not_run("LS-01 no face track found (clip shorter than the track minimum, no face, or a face too small): not judged")
    listing = "; ".join(f"track {i + 1}: {_fmt(t)}" for i, t in enumerate(tracks))
    conf_min = tolerances()["conf_min"]
    if conf_min is None:
        return _not_run(f"LS-03 confidence threshold has no sourced number yet (conf_min null): not judged; {listing}; {HYPOTHESIS}")
    trusted = [t for t in tracks if t["conf"] >= conf_min]
    if not trusted:
        return _not_run(f"LS-03 confidence below {conf_min} on every track: not judged; {listing}")
    best = max(trusted, key=lambda t: t["conf"])
    worst = max(trusted, key=lambda t: abs(t["offset_frames"]))
    limit = review_frames()
    if abs(worst["offset_frames"]) > limit:
        return {"status": FAIL, "value": best["offset_ms"],
                "detail": f"REVIEW: LS-02 offset {_fmt(worst)} is over {limit} frames; {listing}; {STEP_NOTE}; {HYPOTHESIS}"}
    return {"status": PASS, "value": best["offset_ms"],
            "detail": f"offset within {limit} frames (worst {_fmt(worst)}); {listing}; {STEP_NOTE}; {HYPOTHESIS}"}


lipsync_clip.kinds = (".mp4", ".mov", ".mkv", ".avi", ".webm")


def main(argv=None) -> int:
    """``python -m explainer_engine.qa.lipsync clip <clip.mp4> [--speaking]``: one line per clip, exit 1 on a FAIL, 2 on an error."""
    import argparse
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.qa.lipsync")
    ap.add_argument("validator", choices=("clip",))
    ap.add_argument("files", nargs="+")
    ap.add_argument("--speaking", action="store_true", help="mark the clip as a speaking shot (else <clip>.lipsync.json decides)")
    a = ap.parse_args(argv)
    worst = 0
    for f in a.files:
        try:
            r = lipsync_clip(f, True if a.speaking else None)
        except Exception as exc:                       # an undecodable file is an error, never a pass
            print(f"BLOCK {f}: {type(exc).__name__}: {exc}", file=sys.stderr)
            worst = max(worst, 2)
            continue
        print(f"{r['status']:8} {'' if r['value'] is None else r['value']!s:>7}  {f}  {r['detail']}")
        worst = max(worst, 1 if r["status"] == FAIL else 0)
    return worst


if __name__ == "__main__":
    sys.exit(main())
