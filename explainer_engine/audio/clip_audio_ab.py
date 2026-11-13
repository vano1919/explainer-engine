"""The free A/B of Q2 (the creator 2026-11-13, answer c; D-138): one narrated LTX shot made two ways by the one renderer
(``audio/stems.render``), so he chooses by ear whether a narrated clip keeps its own sound.

* ``a_stripped``: the clip's own sound is dropped; the bed is the place's library bed (switch Q2 off, today's default).
* ``b_clip_layer``: the same, plus the clip's own sound as a quiet layer (``stems.clip_audio_layer``, CLIP_AUDIO_DB, BP-188
  seam fades) ducked under the narrator like the bed (switch Q2 on, for this render only).

Both use the same plan (``episode/sound_plan.build`` of a one-shot script), the same library takes, the same narrator read
and the same picture; only the switch differs. Each result is an mp4 (the clip's picture, the new mix) plus its stems and
its report. Free: it reads files that exist, generates nothing.

    python -m explainer_engine.audio.clip_audio_ab <clip.mp4> <narration.wav> <out_dir> --library <root> \\
        --bed battle_din,wind --seconds 6 [--from 0] [--place trojan_plain] [--era bronze_age]
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from explainer_engine.core.store import write_json_atomic

SHOT = "AB_SH001"


def one_shot_script(seconds: float, bed: list[str], place: str, era: str, line: str) -> dict:
    return {"episode_id": "q2_ab", "historical_period": era,
            "segments": [{"segment_id": "S1", "mood": "tense"}],
            "world_bible": {"locations": [{"location_id": place, "ambience_bed": {"classes": list(bed)}}]},
            "audio_lines": [{"line_id": "N1", "speaker_type": "narrator", "speaker_id": "narrator_main", "text": line}],
            "shots": [{"shot_id": SHOT, "segment_id": "S1", "location_id": place, "route": "video",
                       "target_duration_seconds": float(seconds), "audio_line_ids": ["N1"]}]}


def _ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *map(str, args)], check=True)


def build(clip: Path, narration: Path, out_dir: Path, library_root: Path, *, bed: list[str], seconds: float,
          start_s: float = 0.0, place: str = "battlefield", era: str = "bronze_age",
          line: str = "the narrator's line over the shot") -> dict:
    from explainer_engine.audio import stems as STEMS
    from explainer_engine.core import open_questions as OQ
    from explainer_engine.episode import sound_plan as SP
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    pic = out_dir / "picture.mp4"
    clip_wav = out_dir / "clip_audio.wav"
    read = out_dir / "narration.wav"
    _ff("-ss", start_s, "-t", seconds, "-i", clip, "-an", "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p", pic)
    _ff("-ss", start_s, "-t", seconds, "-i", clip, "-vn", "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", clip_wav)
    _ff("-i", narration, "-ac", "1", "-ar", "48000", "-c:a", "pcm_s16le", "-af", f"apad=whole_dur={seconds}",
        "-t", seconds, read)
    script = one_shot_script(seconds, bed, place, era, line)
    plan = SP.build(script, fps=24, era=era)
    sources = SP.resolve(plan, library_root)
    real = OQ.value
    report = {"clip": str(clip), "from_s": start_s, "seconds": seconds, "narration": str(narration), "bed": bed,
              "switch_q2_default": real("Q2"), "versions": {}}
    for name, q2 in (("a_stripped", "off"), ("b_clip_layer", "on")):
        OQ.value = (lambda qid, path=OQ.PATH, _v=q2: _v if qid == "Q2" else real(qid, path))   # this render only
        try:
            rep = STEMS.render(plan, sources, out_dir / name / "stems", library_root=library_root, narration=read,
                               shippable=False, clip_audio={SHOT: clip_wav})
        finally:
            OQ.value = real
        mix = out_dir / name / "stems" / "mix.wav"
        mp4 = out_dir / f"{name}.mp4"
        _ff("-i", pic, "-i", mix, "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "256k",
            "-shortest", mp4)
        report["versions"][name] = {"mp4": str(mp4), "switch_q2": q2, "clip_audio": rep.get("clip_audio"),
                                    "stems": str(out_dir / name / "stems")}
    write_json_atomic(out_dir / "ab_report.json", report)
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="audio.clip_audio_ab")
    ap.add_argument("clip")
    ap.add_argument("narration")
    ap.add_argument("out_dir")
    ap.add_argument("--library", required=True)
    ap.add_argument("--bed", required=True)
    ap.add_argument("--seconds", type=float, required=True)
    ap.add_argument("--from", dest="start", type=float, default=0.0)
    ap.add_argument("--place", default="battlefield")
    ap.add_argument("--era", default="bronze_age")
    a = ap.parse_args(argv)
    rep = build(Path(a.clip), Path(a.narration), Path(a.out_dir), Path(a.library), bed=a.bed.split(","),
                seconds=a.seconds, start_s=a.start, place=a.place, era=a.era)
    print(json.dumps(rep, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
