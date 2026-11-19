"""A slice of an episode: a run over a few shots of the real episode, never shippable (the creator and the plan owner,
2026-11-19: the first 60 s of ``ep_truce_1914`` is the permanent test bench, V4.1 Step 1.5).

``python -m explainer_engine.episode slice <episode> --shots S01_SH001..S02_SH005 --out <folder> [--clock <folder>]``
writes a derived episode folder that the one runner (``episode/run.py``) runs unchanged:

- ``story/production_script.json``: only the slice's shots, their audio lines, and the segments, phases and sections they
  belong to. ``story/full_production_script.json``: the whole script, kept for the gates that are about the whole episode.
- ``episode.json`` gains a ``slice`` block (the shots, the hashes of the full script and of the clock, ``shippable: false``).
  ``run.py`` reads it: script gates run on the full script and count only what is inside the slice; the mix, the speaker rule and
  the video share are computed on the full episode, recorded, and shown as NOT_APPLICABLE, never as a pass; every stage record
  carries the slice stamp and the qa stage ends REVIEW at best.
- with ``--clock``: the read of the slice only. The full read (``narration.wav``, its Scribe words, ``line_reads.json``) is cut
  to the window of the slice's shots on the full clock (``timing.json``) and re-based to 0.

Nothing here is paid and nothing in the source episode is changed.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

from explainer_engine.core.errors import ConfigError, ContractError
from explainer_engine.core.store import write_json_atomic, write_text_atomic

STAMP = "slice, not shippable"
FULL_SCRIPT_REL = "story/full_production_script.json"
SCRIPT_REL = "story/production_script.json"
COPY_FILES = ("story/claim_map.md", "story/research_dossier.md", "story/docudrama_disclosure.md",
              "audio/our_voices_spec.json", "qa/known_review_items.json")


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def parse_shots(spec: str, shot_ids: list[str]) -> list[str]:
    """``A..B`` (inclusive, in script order) or ``A,B,C`` (each must exist)."""
    spec = spec.strip()
    if ".." in spec:
        a, b = [x.strip() for x in spec.split("..", 1)]
        for x in (a, b):
            if x not in shot_ids:
                raise ConfigError(f"slice: shot {x!r} is not in the script")
        i, j = shot_ids.index(a), shot_ids.index(b)
        if i > j:
            raise ConfigError(f"slice: {a} comes after {b} in the script")
        return shot_ids[i:j + 1]
    keep = [x.strip() for x in spec.split(",") if x.strip()]
    missing = [x for x in keep if x not in shot_ids]
    if missing or not keep:
        raise ConfigError(f"slice: no such shot(s) in the script: {missing or spec!r}")
    return [s for s in shot_ids if s in keep]


def scoped_script(full: dict, keep: list[str]) -> dict:
    """The script reduced to the shots in ``keep``. A reference to a shot outside is left as it is; the script gates of a slice
    run on the full script (``run.stage_script``), this copy is what the later stages read."""
    d = json.loads(json.dumps(full))
    shots = [s for s in d["shots"] if s["shot_id"] in keep]
    lines = {i for s in shots for i in s.get("audio_line_ids") or []}
    segs = {s["segment_id"] for s in shots}
    d["shots"] = shots
    d["audio_lines"] = [l for l in d["audio_lines"] if l["line_id"] in lines]
    d["segments"] = [s for s in d["segments"] if s["segment_id"] in segs]
    for p in d.get("phases") or []:
        p["segment_ids"] = [x for x in p.get("segment_ids") or [] if x in segs]
    d["phases"] = [p for p in d.get("phases") or [] if p["segment_ids"]]
    for s in d.get("sections") or []:
        s["scene_ids"] = [x for x in s.get("scene_ids") or [] if x in segs]
    d["sections"] = [s for s in d.get("sections") or [] if s["scene_ids"]]
    if isinstance(d.get("scene_bibles"), list):
        d["scene_bibles"] = [b for b in d["scene_bibles"] if not isinstance(b, dict) or not b.get("scene_id")
                             or b["scene_id"] in segs]
    return d


def clock_window(timing: dict, keep: list[str]) -> tuple[float, float]:
    """(start, end) seconds of the slice's shots on the full clock; the shots must be in the clock and in one run."""
    fps = float(timing["fps"])
    rows = [timing["shots"].get(s) for s in keep]
    if any(r is None for r in rows):
        raise ContractError(f"slice: shot(s) {[s for s, r in zip(keep, rows) if r is None]} are not on the clock")
    t0 = min(r["start_frame"] for r in rows) / fps
    t1 = max(r["start_frame"] + r["frames"] for r in rows) / fps
    return t0, t1


def cut_read(clock: Path, out: Path, keep: list[str], lines: list[str]) -> dict:
    """Cut the full read to the slice's window and re-base the Scribe words and the line reads."""
    clock, out = Path(clock), Path(out)
    timing = json.loads((clock / "timing.json").read_text(encoding="utf-8"))
    t0, t1 = clock_window(timing, keep)
    (out / "audio").mkdir(parents=True, exist_ok=True)
    wav = out / "audio" / "narration.wav"
    r = subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t0:.4f}", "-to", f"{t1:.4f}", "-i",
                        str(clock / "narration.wav"), "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True)
    if r.returncode or not wav.is_file():
        raise ContractError(f"slice: ffmpeg could not cut the read: {r.stderr[-300:]}")
    sc = json.loads((clock / "narration.scribe.json").read_text(encoding="utf-8"))
    words = [dict(w, start=round(w["start"] - t0, 3), end=round(w["end"] - t0, 3)) for w in sc.get("words") or []
             if t0 - 1e-6 <= float(w["start"]) < t1]
    write_json_atomic(out / "audio" / "narration.scribe.json",
                      dict(sc, words=words, seconds=round(t1 - t0, 3), slice_of_seconds=sc.get("seconds"),
                           window_s=[round(t0, 4), round(t1, 4)]))
    lr_p = clock / "line_reads.json"
    if lr_p.is_file():
        lr = json.loads(lr_p.read_text(encoding="utf-8"))
        lr["lines"] = {k: v for k, v in (lr.get("lines") or {}).items() if k in lines}
        write_json_atomic(out / "audio" / "line_reads.json", lr)
    return {"window_s": [round(t0, 4), round(t1, 4)], "words": len(words), "narration_sha256": _sha(wav),
            "source_narration_sha256": _sha(clock / "narration.wav"), "source_timing_sha256": _sha(clock / "timing.json")}


def full_episode_gates(full: dict) -> list[dict]:
    """The gates that are about the whole episode, computed on the full script (their rows are what a slice shows as
    NOT_APPLICABLE)."""
    from explainer_engine.episode import router as R
    rows = list(R.talking_check(full))
    rows += R.mix_gate_rows(full, scope="full")
    return rows


def build(src: Path, out: Path, spec: str, clock: Path | None = None) -> dict:
    src, out = Path(src).resolve(), Path(out).resolve()
    if out == src or src.is_relative_to(out) or out.is_relative_to(src):
        raise ConfigError("slice: the output folder must be another folder than the episode")
    man = json.loads((src / "episode.json").read_text(encoding="utf-8"))
    full = json.loads((src / SCRIPT_REL).read_text(encoding="utf-8"))
    keep = parse_shots(spec, [s["shot_id"] for s in full["shots"]])
    scoped = scoped_script(full, keep)
    out.mkdir(parents=True, exist_ok=True)
    write_json_atomic(out / SCRIPT_REL, scoped)
    write_json_atomic(out / FULL_SCRIPT_REL, full)
    for rel in COPY_FILES:
        if (src / rel).is_file():
            (out / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(src / rel, out / rel)
    lines = [l["line_id"] for l in scoped["audio_lines"]]
    sl = {"of": man.get("episode_id"), "shots": keep, "first": keep[0], "last": keep[-1], "stamp": STAMP,
          "shippable": False, "source_script_sha256": _sha(src / SCRIPT_REL), "scoped_script_sha256": _sha(out / SCRIPT_REL),
          "full_episode_gates": [{"gate": r["gate"], "status": r["status"], "detail": r["detail"]}
                                 for r in full_episode_gates(full)]}
    if clock is not None:
        sl["clock"] = cut_read(Path(clock), out, keep, lines)
    man = dict(man, slice=sl)
    write_json_atomic(out / "episode.json", man)
    write_text_atomic(out / "SLICE_NOT_SHIPPABLE.txt",
                      f"{STAMP}: shots {keep[0]}..{keep[-1]} ({len(keep)}) of {man.get('episode_id')}.\n"
                      "Made by `python -m explainer_engine.episode slice`; nothing made from it ships.\n")
    return sl


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("episode", type=Path)
    ap.add_argument("--shots", required=True, help="A..B (inclusive, script order) or A,B,C")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--clock", type=Path, help="folder with the full read: narration.wav, narration.scribe.json, "
                    "timing.json, line_reads.json")
    a = ap.parse_args(argv)
    sl = build(a.episode, a.out, a.shots, a.clock)
    print(json.dumps({k: sl[k] for k in ("of", "first", "last", "stamp", "shippable")} | {"shots": len(sl["shots"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
