"""LTX clips into the episode (VL-07, VL-11, docs/VIDEO_LANE.md): every generated clip is kept whole (``production/video/raw``,
sha256 pinned, never overwritten), cut to its edit by its MEASURED speech, normalised to the episode's rate, and recorded in
``production/video/<shot>.json``: the record the runner's clips stage (G7) reads for a ``video`` shot (``run._wan_clip``).

Before this module no code wrote that record for an LTX clip, so the runner could not take an LTX clip at all (the
2026-11-12 battle and love scenes were joined by hand, outside the runner).

The edit of one clip:

* spoken clip: in = the first word minus a head lead (BP-190; never past the first word, the first word is never cut), widened
  to the shot's ``head_handle_s`` when the clip has it; out = the last word plus the tail (BP-190's band, at least the shot's
  ``tail_handle_s``). LTX starts a line about 0.75 s in, so this is where the dead head goes.
* silent clip: in = its head handle (LTX's first settling frames), out = in + its planned length (the tail handle stays in
  the raw clip for the editor).
* continuation hand-over (VL-05): when the next clip was generated from frame k of this one, this clip ends ON frame k and
  the next clip drops its frame 0 (the same picture), so the action runs on across the cut without a repeated frame.
* the clip's frame rate is normalised to the episode's (a 30 fps clip on a 24 fps episode is resampled by ffmpeg ``fps``,
  the sound is cut by the same seconds so nothing drifts).

The trimmed clip's speech spans (trimmed seconds) are the clip-timed clock's input (``episode/timing.retime_with_clips``).
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from fractions import Fraction
from pathlib import Path

from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR

SCHEMA = "video_clip_record/1"
HEAD_LEAD = [float(v) for v in SR.T("BP-190", "head_lead_s")]
CUT_TAIL = [float(v) for v in SR.T("BP-190", "tail_s")]
SPEECH_TAIL_S = float(SR.T("BP-187", "speech_tail_s"))   # a spoken line ends inside its clip with this much after it


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def probe(path: Path) -> dict:
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type,avg_frame_rate,nb_frames,duration",
                          "-show_entries", "format=duration", "-of", "json", str(path)], capture_output=True, text=True,
                         check=True).stdout
    d = json.loads(out)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), None)
    a = next((s for s in d.get("streams", []) if s.get("codec_type") == "audio"), None)
    if v is None:
        raise ContractError(f"{Path(path).name}: no video stream")
    fps = Fraction(v.get("avg_frame_rate") or "0/1")
    dur = float(v.get("duration") or d.get("format", {}).get("duration") or 0)
    return {"fps": float(fps) if fps else 0.0, "duration": dur, "has_audio": a is not None,
            "audio_duration": float(a.get("duration") or 0) if a else 0.0}


def speech(path: Path) -> list[tuple[float, float]]:
    """Where the clip's own sound speaks (``qa/sound_realism.speech_spans``, the gate's own detector, so the trim and the
    final-file gate agree)."""
    from explainer_engine.qa import sound_realism as R
    x = R.read_audio(path)
    return [(float(a), float(b)) for a, b in R.speech_spans(x)] if len(x) else []


def edit_points(dur: float, spans: list, edit_plan: dict | None, planned_s: float, fps: int, *, spoken: bool,
                handover_s: float | None = None, drop_first: bool = False, shot_id: str = "?") -> dict:
    """The in and out points (clip seconds, on whole frames) of one clip; see the module text.

    A hand-over frame (VL-05) before the last speech end + BP-187's tail would cut the line: a ContractError (repair class C,
    regenerate the clip or move the hand-over), never a silent cut (Fable audit FA-07)."""
    ep = edit_plan or {}
    fr = 1.0 / fps
    if handover_s is not None and spans:
        s_end = float(spans[-1][1])
        if handover_s + 1e-9 < s_end + SPEECH_TAIL_S:
            raise ContractError(f"{shot_id}: the hand-over frame at {handover_s:.3f} s lies before the speech end {s_end:.3f} s "
                                f"+ BP-187's {SPEECH_TAIL_S:g} s tail: the cut would clip the line (class C: regenerate the "
                                "clip or pick a later hand-over frame, FA-07)")
    if spoken:
        if not spans:
            raise ContractError("a spoken clip with no speech in its own sound (LTX dropped the line?): regenerate or "
                                "re-plan; nothing is trimmed blind")
        s0, s1 = spans[0][0], spans[-1][1]
        lead = max(HEAD_LEAD[1], float(ep.get("head_handle_s", 0.0)))
        t_in = max(0.0, s0 - lead)
        t_out = min(dur, s1 + max(CUT_TAIL[0], min(CUT_TAIL[1], float(ep.get("tail_handle_s", CUT_TAIL[1])))))
    else:
        t_in = min(float(ep.get("head_handle_s", 0.0)), max(0.0, dur - planned_s))
        t_out = min(dur, t_in + planned_s) if planned_s > 0 else dur
    if drop_first:
        t_in = max(t_in, fr)
    if handover_s is not None:
        t_out = min(dur, handover_s + fr)            # end ON the hand-over frame (VL-05)
    f_in, f_out = int(round(t_in * fps)), int(round(t_out * fps))
    if spoken and f_in / fps > spans[0][0] - HEAD_LEAD[0] + 1e-6 and spans[0][0] >= HEAD_LEAD[0]:
        f_in = max(0, int((spans[0][0] - HEAD_LEAD[0]) * fps))   # the first word is never cut
    if f_out - f_in < 1:
        raise ContractError(f"the edit leaves {f_out - f_in} frame(s) of a {dur:.2f} s clip")
    return {"in_s": round(f_in / fps, 4), "out_s": round(f_out / fps, 4), "frames": f_out - f_in}


def cut(raw: Path, out: Path, in_s: float, frames: int, fps: int) -> Path:
    """The trimmed clip: picture resampled to ``fps`` and cut to ``frames``, the sound cut by the same seconds."""
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part.mp4")
    dur = frames / fps
    # read two frames more than the edit: the fps filter's rounding can otherwise drop the last frame (seen on CI's
    # ffmpeg with a 30 fps clip on a 24 fps episode); -frames:v caps the picture, atrim the sound
    cmd = ["ffmpeg", "-v", "error", "-y", "-ss", f"{in_s:.4f}", "-i", str(raw), "-t", f"{dur + 2.0 / fps:.4f}",
           "-vf", f"fps={fps}", "-frames:v", str(frames), "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16",
           "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-af", f"apad,atrim=0:{dur:.4f}", str(tmp)]
    subprocess.run(cmd, check=True, capture_output=True)
    got = subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0", "-show_entries",
                          "stream=nb_read_frames", "-of", "csv=p=0", str(tmp)], capture_output=True, text=True,
                         check=True).stdout.strip()
    if int(got or 0) != frames:   # the record must say what the file holds (the assembler refuses a short clip)
        tmp.unlink(missing_ok=True)
        raise ContractError(f"{Path(raw).name}: the cut has {got} frames, the edit {frames} (from {in_s:.3f} s)")
    tmp.replace(out)
    return out


def ingest_scene(root: Path, script: dict, clips: list[dict], fps: int, *, backend: str = "ltx") -> list[dict]:
    """Ingest one scene's clips. ``clips``: in cut order, ``[{shot_id, path, chain_from_frame?: {frame}}]`` (the worker's rows
    with the downloaded file). Writes the raw copy, the trimmed clip and the record of each; returns the records."""
    from explainer_engine.training import video_qa as VQ
    from explainer_engine.videolane import plan as P
    root = Path(root)
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    spoken = P.clip_spoken(script)
    vdir = root / "production" / "video"
    out = []
    for k, c in enumerate(clips):
        sid = c["shot_id"]
        if sid not in by:
            raise ContractError(f"{sid}: a clip for a shot the script does not have")
        shot = by[sid]
        src = Path(c["path"])
        raw = vdir / "raw" / f"{sid}.mp4"
        raw.parent.mkdir(parents=True, exist_ok=True)
        if raw.exists() and _sha(raw) != _sha(src):
            raise ContractError(f"{sid}: production/video/raw/{sid}.mp4 holds another clip; the raw evidence is never "
                                "overwritten (move it aside with its record first)")
        if not raw.exists():
            shutil.copyfile(src, raw)
        pr = probe(raw)
        nxt = clips[k + 1] if k + 1 < len(clips) else None
        hand = (nxt or {}).get("chain_from_frame")
        handover_s = (int(hand["frame"]) / pr["fps"]) if hand and pr["fps"] else None
        is_cont = bool(c.get("chain_from_frame"))
        spans = speech(raw) if pr["has_audio"] else []
        planned = float(shot.get("target_duration_seconds") or 0.0)
        pts = edit_points(pr["duration"], spans, shot.get("edit_plan"), planned, fps, spoken=sid in spoken,
                          handover_s=handover_s, drop_first=is_cont, shot_id=sid)
        trimmed = cut(raw, vdir / "cut" / f"{sid}.mp4", pts["in_s"], pts["frames"], fps)
        t_spans = [(round(max(0.0, a - pts["in_s"]), 3), round(min(pts["frames"] / fps, b - pts["in_s"]), 3))
                   for a, b in spans if b > pts["in_s"] and a < pts["out_s"]]
        metrics, finds = VQ.clip_findings(trimmed, fps=fps, expect_speech=sid in spoken)
        bad = [f for f in finds if f.get("status") == "FAIL" or f.get("severity") == "FAIL"]
        rec = {"schema": SCHEMA, "shot_id": sid, "route": "video", "backend": backend,
               "status": G.FAIL if bad else (G.REVIEW if any((f.get("status") or f.get("severity")) == "REVIEW"
                                                                for f in finds) else G.PASS),
               "clip_path": str(trimmed.relative_to(root)), "clip_sha256": _sha(trimmed),
               "raw_path": str(raw.relative_to(root)), "raw_sha256": _sha(raw), "raw_fps": pr["fps"],
               "raw_seconds": round(pr["duration"], 4), "fps": fps, "in_s": pts["in_s"], "out_s": pts["out_s"],
               "frames": pts["frames"], "speech_raw": spans, "speech": t_spans, "clip_spoken": sid in spoken,
               "chain_from_frame": c.get("chain_from_frame"), "ends_on_handover": handover_s is not None,
               "findings": finds, "attempts": c.get("attempts") or []}
        write_json_atomic(vdir / f"{sid}.json", rec)
        out.append(rec)
    return out


def recut(root: Path, rec: dict, frames: int, fps: int) -> dict:
    """A silent or narrated video shot whose clock (the read) gives it another length than its first cut: cut it again from
    its kept raw clip at the same in point (free, class A). A raw clip too short for the shot is a ContractError: the clip
    is made again (class C), never stretched."""
    root = Path(root)
    raw = root / rec["raw_path"]
    if not raw.is_file() or _sha(raw) != rec["raw_sha256"]:
        raise ContractError(f"{rec['shot_id']}: its raw clip is missing or changed; it cannot be cut again")
    if rec.get("clip_spoken"):
        raise ContractError(f"{rec['shot_id']}: a clip-spoken shot is timed by its own cut, never re-cut to a clock")
    if rec.get("ends_on_handover") and frames != int(rec["frames"]):
        raise ContractError(f"{rec['shot_id']}: it ends on the frame its continuation starts from (VL-05); a cut at another "
                            "frame would repeat or skip the action: time the read to it, or re-plan the continuation")
    have = float(rec["raw_seconds"]) - float(rec["in_s"])
    if frames / fps > have + 0.5 / fps:
        raise ContractError(f"{rec['shot_id']}: the shot needs {frames / fps:.2f} s, the raw clip holds {have:.2f} s after "
                            "its in point: make the clip longer (VL-06), it is never stretched")
    out = root / rec["clip_path"]
    cut(raw, out, float(rec["in_s"]), frames, fps)
    new = dict(rec, frames=frames, out_s=round(float(rec["in_s"]) + frames / fps, 4), clip_sha256=_sha(out),
               recut_from=rec.get("frames"))
    write_json_atomic(root / "production" / "video" / f"{rec['shot_id']}.json", new)
    return new


def clip_timings(root: Path, script: dict) -> dict:
    """``{shot_id: {frames, speech}}`` of every clip-timed shot whose record exists (the voice stage's input)."""
    from explainer_engine.videolane import plan as P
    out = {}
    for sid in sorted(P.clip_spoken(script)):
        p = Path(root) / "production" / "video" / f"{sid}.json"
        if p.is_file():
            d = json.loads(p.read_text(encoding="utf-8"))
            if d.get("status") != G.FAIL:
                out[sid] = {"frames": int(d["frames"]), "speech": d.get("speech") or []}
    return out


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(prog="videolane.ingest", description="LTX clips into the episode: raw kept, cut by speech")
    ap.add_argument("episode")
    ap.add_argument("clips", help="JSON list [{shot_id, path, chain_from_frame?}] in cut order (the worker's rows + files)")
    ap.add_argument("--fps", type=int, default=24)
    a = ap.parse_args(argv)
    root = Path(a.episode)
    script = json.loads((root / "story" / "production_script.json").read_text(encoding="utf-8"))
    recs = ingest_scene(root, script, json.loads(Path(a.clips).read_text(encoding="utf-8")), a.fps)
    print(json.dumps([{k: r[k] for k in ("shot_id", "status", "in_s", "out_s", "frames")} for r in recs], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
