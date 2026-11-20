"""The finishing chain of the one render path (final plan S14-S16 and S18, W7), as one function ``run_chain``.

Master picture chunks + mix -> ``ffwrap.join_with_audio`` (stream-copied join, mix under it) -> ``grade.grade_master`` (once, toward the
scene key) -> rows: VAL-EDT-01 blended cuts, VAL-CLR-01/02 grade, VAL-QA-01..08 technical QA -> captions (SRT by subtitle-skill, soft track,
VAL-SUB-01/02). The result is a report dict (``finish_chain/1``) of gate rows; nothing here PASSes what only a person can judge.
``episode/run.py`` (W4's lines are the only edits it takes in Wave 2) calls this after G9; it is also what the parity run calls."""
from __future__ import annotations

from pathlib import Path

import numpy as np

from explainer_engine.core.store import write_json_atomic
from explainer_engine.finish import cut_check, ffwrap, grade as GR, qa_steps, subtitles as SUB
from explainer_engine.qa import gates as G
from explainer_engine.validators import color as VC, tech_qa as VQ

SCHEMA = "finish_chain/1"


def _sample_frames(video: Path, n: int = 6, width: int = 160, *, start_frame: int | None = None, end_frame: int | None = None,
                   fps: int = 24) -> np.ndarray:
    """``n`` frames spread over the file (or over ``start_frame``..``end_frame``) as float RGB 0-1 (statistics only: a small decode)."""
    import subprocess
    info = ffwrap.probe(video)
    h = max(2, int(round(width * info["video"]["height"] / info["video"]["width"] / 2)) * 2)
    t0, t1 = (0.0, max(info["duration"], 0.1)) if start_frame is None else (start_frame / fps, max(end_frame, start_frame + 1) / fps)
    out = []
    for i in range(n):
        raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t0 + (t1 - t0) * (i + 0.5) / n:.3f}", "-i", str(video), "-frames:v", "1", "-vf",
                              f"scale={width}:{h}", "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True, check=True).stdout
        out.append(np.frombuffer(raw, np.uint8).reshape(h, width, 3).astype(np.float32) / 255.0)
    return np.stack(out)


def finish_rows(master: Path, out_dir: Path, *, scene_keys: dict[str, tuple[np.ndarray, tuple[int, int]]] | None = None, fps: int = 24,
                expected_frames: int | None = None, words: list[dict] | None = None, platform: str = "youtube") -> list[dict]:
    """The rows of the finishing chain on a master that is already joined with its sound (``episode/run.py`` stage G9 calls this).

    ``scene_keys``: ``{scene_id: (key_frame RGB 0-1, (first_frame, end_frame))}`` - the accepted keyframe of the scene's first shot and where
    the scene lies in the master (VAL-CLR-01 per scene; a scene with no accepted keyframe is simply absent and gets a NOT_RUN row from the
    caller). One grade of the whole master needs ONE key: with exactly one scene the master is graded once toward it (a graded copy
    ``<stem>_graded.mp4`` next to it, the master itself untouched); with several scenes a per-scene LUT would be needed, which is not built,
    so VAL-CLR-02 says NOT_RUN and VAL-CLR-01 measures the master as it is."""
    master, out_dir = Path(master), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    rows = [cut_check.blended_row(master, gate="VAL-EDT-01")]
    scene_keys = scene_keys or {}
    target = master
    if len(scene_keys) == 1:
        (key, _span), = scene_keys.values()
        graded = out_dir / (master.stem + "_graded.mp4")
        GR.grade_master(master, graded, key, _sample_frames(master))
        target = graded
        rows.append(VC.graded_once(graded))
    else:
        rows.append(G.row("VAL-CLR-02", None, "NOT_RUN: " + ("no scene has an accepted keyframe to grade toward" if not scene_keys else
                          f"{len(scene_keys)} scenes need a per-scene LUT, which is not built (one grade of the master needs one key)")))
    for sid, (key, (a, b)) in scene_keys.items():
        frames = _sample_frames(target, start_frame=a, end_frame=b, fps=fps)
        row = VC.master_vs_key((frames * 255).astype(np.uint8), (np.asarray(key) * 255).astype(np.uint8), gate="VAL-CLR-01")
        row["gate"] = f"VAL-CLR-01:{sid}"
        rows.append(row)
    rows += VQ.check_file(target, {"fps": fps, **({"frames": expected_frames} if expected_frames else {})})
    rows += [qa_steps.check_row(target, platform), qa_steps.look_row(target, out_dir / (target.stem + "_sheet.png"))]
    if words:
        cues = SUB.build_cues(words)
        srt = SUB.write_srt(cues, out_dir, "captions.srt")
        SUB.mux_soft(target, srt, out_dir / (target.stem + "_cc.mp4"))
        rows += SUB.rows(cues)
    else:
        rows += [G.row("VAL-SUB-01", None, "NOT_RUN: no word timings given"), G.row("VAL-SUB-02", None, "NOT_RUN: no word timings given")]
    return rows


def run_chain(clips: list[Path], audio: Path, out_dir: Path, *, key_frame: np.ndarray, words: list[dict] | None = None,
              fps: int = 24, expected_frames: int | None = None, platform: str = "youtube") -> dict:
    """Run the chain into ``out_dir`` and return the report (also written as ``finish_chain.json``). ``key_frame``: the scene key, float
    RGB 0-1. ``words``: the read's word timings (``[{word, start, end}]``) for the captions, or None (captions NOT_RUN)."""
    from explainer_engine.production import assemble as A
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    master, graded, sheet = out_dir / "master.mp4", out_dir / "master_graded.mp4", out_dir / "master_graded_sheet.png"
    ffwrap.join_with_audio(list(map(Path, clips)), Path(audio), master, **A._audio_args())
    rec = GR.grade_master(master, graded, key_frame, _sample_frames(master))
    rows = [cut_check.blended_row(graded, gate="VAL-EDT-01")]
    sample = (_sample_frames(graded) * 255).astype(np.uint8)
    rows += [VC.master_vs_key(sample, (np.asarray(key_frame) * 255).astype(np.uint8)), VC.graded_once(graded)]
    rows += VQ.check_file(graded, {"fps": fps, **({"frames": expected_frames} if expected_frames else {})})
    rows += [qa_steps.check_row(graded, platform), qa_steps.look_row(graded, sheet)]
    captions = None
    if words:
        cues = SUB.build_cues(words)
        srt = SUB.write_srt(cues, out_dir, "captions.srt")
        SUB.mux_soft(graded, srt, out_dir / "master_graded_cc.mp4")
        rows += SUB.rows(cues)
        captions = str(srt)
    else:
        rows += [G.row("VAL-SUB-01", None, "NOT_RUN: no word timings given"), G.row("VAL-SUB-02", None, "NOT_RUN: no word timings given")]
    report = {"schema": SCHEMA, "master": str(master), "graded": str(graded), "contact_sheet": str(sheet), "captions": captions,
              "grade": rec, "verdict": G.verdict(rows)}
    write_json_atomic(out_dir / "finish_chain.json", report)
    return report
