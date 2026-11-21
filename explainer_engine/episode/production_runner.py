"""The episode-first production run as one call (v4.3 plan P8): ``run_episode_production`` runs every stage of the one
runner (``episode/run.py``, ``python -m explainer_engine.episode run <episode> --to qa``) and returns the QA manifest.

Kept here from the archive's runner (plan section 6: "keep the stem-audit idea"): the stem audit (RMS, peak, mid-line
dropouts of the narration, the sound director's SD-02) and the contact sheet drawn from the rendered master. The archive's
in-RAM assembler is gone (F15): assembly goes through ``production/assemble.assemble_shot_clips`` in chunks (RULE-R1).
"""
from __future__ import annotations

import hashlib
import math
import subprocess
import wave
from pathlib import Path
from typing import Any, Dict, List

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.audio import acoustics, dropouts, sound_director


def _read_wav_mono_and_stereo(wav_path: Path) -> tuple[np.ndarray, np.ndarray, int]:
    with wave.open(str(wav_path), "rb") as wf:
        sr = wf.getframerate()
        n_ch = wf.getnchannels()
        raw = np.frombuffer(wf.readframes(wf.getnframes()), dtype="<i2").astype(np.float32) / 32768.0
        stereo = raw.reshape(-1, n_ch) if n_ch > 1 else np.stack([raw, raw], axis=1)
        mono = stereo.mean(axis=1)
    return mono, stereo, sr


def audit_rendered_audio_stems(
    stems_dir: Path,
    script_doc: Dict[str, Any],
    fps: int = 24,
) -> Dict[str, Any]:
    """Run quantitative continuity, RMS/peak dBFS, and mid-word dropout checks across all 5 audio stems."""
    stem_names = ("narration", "music", "ambience", "sfx", "mix")
    loaded_mono: Dict[str, np.ndarray] = {}
    loaded_stereo: Dict[str, np.ndarray] = {}
    metrics: Dict[str, Any] = {}
    sr = 48000

    for name in stem_names:
        p = stems_dir / f"{name}.wav"
        if not p.is_file():
            raise FileNotFoundError(f"Missing required audio stem: {p}")
        mono, stereo, sr = _read_wav_mono_and_stereo(p)
        loaded_mono[name] = mono
        loaded_stereo[name] = stereo
        rms_val = float(acoustics.rms_db(mono.astype(np.float64)))
        peak_val = float(20.0 * math.log10(float(np.max(np.abs( stereo ))) + 1e-12))
        metrics[name] = {
            "path": str(p),
            "sample_rate_hz": sr,
            "channels": int(stereo.shape[1]),
            "duration_sec": round(len(mono) / sr, 3),
            "rms_dbfs": round(rms_val, 2),
            "peak_dbfs": round(peak_val, 2),
            "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
        }

    # Build synthetic word spine from audio_lines to verify independent narration stem continuity across all 25 spoken lines
    words: List[Dict[str, Any]] = []
    for ln in script_doc.get("audio_lines", []):
        s_sec = float(ln.get("start_sec", 0.0))
        e_sec = float(ln.get("end_sec", s_sec + float(ln.get("estimated_duration_seconds", 4.0))))
        active_end_sec = max(s_sec + 0.20, e_sec - 0.14)
        words.append({
            "word": str(ln.get("line_id") or "line"),
            "start_frame": int(round(s_sec * fps)),
            "end_frame": int(round(active_end_sec * fps)),
        })

    total_frames = int(round(sum(float(s.get("target_duration_seconds", 4.0)) for s in script_doc.get("shots", [])) * fps))
    spine = {"fps": fps, "total_frames": total_frames, "words": words}
    manifest = {
        "fps": fps,
        "total_frames": total_frames,
        "scenes": [{"scene": "S01", "start_frame": 0, "end_frame": total_frames, "acoustic": "outdoor", "entry": "butt", "ir_seed": acoustics.seed_of("S01")}],
        "beds": [{"id": "rt01", "scene": "S01", "kind": "room_tone", "ref": "rt", "gain_db": -38.0, "start_frame": 0, "end_frame": total_frames}],
        "music": [],
        "spots": [],
        "vacuums": [],
        "dialogue": [],
    }

    sd_findings = sound_director._check_stems(manifest, spine, loaded_stereo, {}, (0.5, 1.5))

    # Measure active-speech narration RMS and check for mid-line dropouts
    nar_mono = loaded_mono["narration"]
    line_audits: List[Dict[str, Any]] = []
    mid_line_dropouts = 0
    for ln in script_doc.get("audio_lines", []):
        s_sec = float(ln.get("start_sec", 0.0))
        e_sec = float(ln.get("end_sec", s_sec + 4.0))
        active_end = max(s_sec + 0.2, e_sec - 0.14)
        a_i = int(round(s_sec * sr))
        b_i = min(len(nar_mono), int(round(active_end * sr)))
        seg = nar_mono[a_i:b_i]
        seg_rms = float(acoustics.rms_db(seg.astype(np.float64)))
        d_scan = dropouts.scan(seg, sr, min_run=0.05, loud_db=-45.0)
        n_cuts = len(d_scan["cut_into_sound"])
        mid_line_dropouts += n_cuts
        line_audits.append({
            "line_id": ln.get("line_id"),
            "shot_id": ln.get("shot_id"),
            "start_sec": s_sec,
            "end_sec": e_sec,
            "active_rms_dbfs": round(seg_rms, 2),
            "mid_line_dropouts": n_cuts,
        })

    return {
        "stems": metrics,
        "spoken_lines_audited": len(line_audits),
        "mid_line_narration_dropouts": mid_line_dropouts,
        "sound_director_stem_findings": [f for f in sd_findings if f["rule"] == "SD-02"],
        "line_audits": line_audits,
    }


def generate_master_video_contact_sheet(
    master_mp4_path: Path,
    shot_records: List[Dict[str, Any]],
    out_jpg_path: Path,
    cols: int = 5,
    thumb_w: int = 384,
    thumb_h: int = 216,
) -> Path:
    """Extract midpoint frames directly from the rendered `master_mp4_path` for every shot and build an annotated contact sheet."""
    out_jpg_path = Path(out_jpg_path)
    out_jpg_path.parent.mkdir(parents=True, exist_ok=True)
    n = len(shot_records)
    rows = math.ceil(n / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + 36)), (14, 16, 20))
    draw = ImageDraw.Draw(sheet)

    for idx, rec in enumerate(shot_records):
        mid_s = 0.5 * (float(rec["start_sec"]) + float(rec["end_sec"]))
        raw = subprocess.run(
            [
                "ffmpeg", "-v", "error",
                "-ss", f"{mid_s:.3f}",
                "-i", str(master_mp4_path),
                "-frames:v", "1",
                "-f", "rawvideo", "-pix_fmt", "rgb24",
                "-s", f"{thumb_w}x{thumb_h}",
                "-",
            ],
            capture_output=True,
            check=True,
        ).stdout
        if len(raw) == thumb_w * thumb_h * 3:
            im = Image.frombytes("RGB", (thumb_w, thumb_h), raw)
        else:
            im = Image.new("RGB", (thumb_w, thumb_h), (40, 20, 20))
        r, c = divmod(idx, cols)
        x0, y0 = c * thumb_w, r * (thumb_h + 36)
        sheet.paste(im, (x0, y0))
        label = f"{rec['shot_id']} ({rec['start_sec']:.1f}-{rec['end_sec']:.1f}s) [{rec.get('route') or rec.get('generation_mode')}]"
        draw.text((x0 + 6, y0 + thumb_h + 8), label[:46], fill=(235, 228, 210))

    sheet.save(out_jpg_path, quality=92)
    return out_jpg_path


def run_episode_production(episode_dir: Path | str, width: int = 1920, height: int = 1080, fps: int | None = None,
                           force_rerender_clips: bool = False, rehearsal: bool = True) -> Dict[str, Any]:
    """Every stage of ``episode/run.py`` up to QA; returns the production manifest (``production/production_manifest.json``).
    ``rehearsal`` (the default here, as in the archive's one-call run) goes on after a FAIL; the manifest then says so and
    ``all_gates_passed`` is false. Nothing paid is called."""
    import json
    from explainer_engine.episode import run as RUN
    ep = RUN.Episode(Path(episode_dir), size=(width, height), fps=fps, rehearsal=rehearsal, force=force_rerender_clips)
    RUN.run_to(ep, "qa")
    man = ep.path("production/production_manifest.json")
    if not man.is_file():
        last = [s for s in RUN.state(ep) if s["status"]][-1]
        raise RuntimeError(f"the run stopped at {last['stage']} ({last['status']}); see production/stages/{last['stage']}.json")
    return json.loads(man.read_text(encoding="utf-8"))
