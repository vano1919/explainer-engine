"""build_episode: shot plan + the read's line durations -> the shots (build_shot) -> one film with the narration laid on it.

Input is an episode file (JSON, paths relative to it):
  {"id": "truce_test", "film_file": "episode_film.json", "durations": "durations.json",   # durations.json: [{"line_id", "file", "measured_s"}]
   "audio_dir": "reads", "lead_s": 0.25, "gap_s": 0.30, "tail_s": 0.45,
   "shots": [{"id": "S01_SH001", "spec": "shots/S01_SH001.json", "lines": ["S01_L001"]}, ...]}
``plan_from_shot_plan`` builds the ``shots`` list from a shot_plan.json (HF ``shot_plan.json`` layout: {"shots": [{"shot", "segment", "lines": [[speaker, text]]}]})
and a lines.json ([{"line_id", "text"}]) by matching the text, never by guessing: an unmatched or ambiguous line is an error.
A shot is as long as its lines are: lead + each line + a gap between lines + tail, rounded UP to whole frames (24 fps). Each shot's spec is built with that
length by ``build_shot`` (photo shots and map shots alike; a clip whose spec, picture, film and length did not change is reused from the cache). The narration is laid
on the cut at each shot's start + lead, the cut is joined by ffmpeg (hard cuts) and the voice is normalised to the long-form loudness of ``qa/targets.py``.
Free: nothing here calls a paid service; the reads must already exist.

usage: python -m explainer_engine.production.build_episode episode.json out.mp4 [--work DIR] [--tile-dir DIR] [--cache-dir DIR] [--only S01_SH001,...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import subprocess
import sys
from pathlib import Path

from explainer_engine.fx25d.living import FPS
from explainer_engine.production import build_shot as BS

DEFAULTS = dict(lead_s=0.25, gap_s=0.30, tail_s=0.45)


class BuildEpisodeError(ValueError):
    """The episode file or its inputs are wrong; nothing was built."""


def plan_from_shot_plan(shot_plan: dict, lines: list[dict], segments: list[str], spec_dir: str = "shots") -> list[dict]:
    by_text: dict[str, list[str]] = {}
    for ln in lines:
        by_text.setdefault(" ".join(ln["text"].split()), []).append(ln["line_id"])
    out = []
    for sh in shot_plan["shots"]:
        if sh["segment"] not in segments:
            continue
        ids = []
        for _speaker, text in sh.get("lines", []):
            hit = by_text.get(" ".join(text.split()), [])
            if len(hit) != 1:
                raise BuildEpisodeError(f"{sh['shot']}: line {text!r} matches {len(hit)} lines in lines.json (need exactly 1)")
            ids.append(hit[0])
        out.append({"id": sh["shot"], "spec": f"{spec_dir}/{sh['shot']}.json", "lines": ids})
    return out


def shot_seconds(durs: list[float], lead_s: float, gap_s: float, tail_s: float) -> float:
    """Length of a shot whose narration is ``durs`` seconds of lines: lead + lines + gaps + tail, rounded up to whole frames."""
    raw = lead_s + sum(durs) + gap_s * max(0, len(durs) - 1) + tail_s
    return math.ceil(raw * FPS - 1e-9) / FPS


def schedule(shots: list[dict], dur: dict[str, float], lead_s: float, gap_s: float, tail_s: float) -> list[dict]:
    """Per shot: start, seconds, and the start of each line on the film's clock."""
    t = 0.0
    rows = []
    for sh in shots:
        ds = [dur[i] for i in sh["lines"]]
        secs = shot_seconds(ds, lead_s, gap_s, tail_s)
        at, cur = [], t + lead_s
        for i, d in zip(sh["lines"], ds):
            at.append((i, round(cur, 4)))
            cur += d + gap_s
        rows.append(dict(id=sh["id"], start=round(t, 4), seconds=secs, lines=at))
        t += secs
    return rows


def _load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildEpisodeError(f"cannot read {path}: {exc}") from exc


def _digest(*parts) -> str:
    h = hashlib.sha256()
    for p in parts:
        h.update(p if isinstance(p, bytes) else str(p).encode())
    return h.hexdigest()[:12]


def build_episode(episode_path, out_mp4, work=None, tile_dir=None, cache_dir="jobs/_depth_cache", only=None) -> dict:
    ep_file = Path(episode_path).resolve()
    ep = _load(ep_file)
    base = ep_file.parent
    P = lambda k: (Path(k) if Path(k).is_absolute() else base / k)
    for key in ("id", "film_file", "durations", "audio_dir", "shots"):
        if key not in ep:
            raise BuildEpisodeError(f"missing {key!r} in the episode file")
    lead, gap, tail = (float(ep.get(k, DEFAULTS[k])) for k in ("lead_s", "gap_s", "tail_s"))
    dlist = _load(P(ep["durations"]))
    if not isinstance(dlist, list):
        raise BuildEpisodeError("durations.json must be a list")
    durs = {d["line_id"]: d for d in dlist}
    shots = [s for s in ep["shots"] if not only or s["id"] in only]
    if not shots:
        raise BuildEpisodeError("no shots selected")
    missing = sorted({i for s in shots for i in s["lines"] if i not in durs})
    if missing:
        raise BuildEpisodeError(f"no duration for lines {missing}")
    for s in shots:
        for i in s["lines"]:
            if not (P(ep["audio_dir"]) / durs[i]["file"]).exists():
                raise BuildEpisodeError(f"read file missing for {i}: {P(ep['audio_dir']) / durs[i]['file']}")
    sched = schedule(shots, {k: float(v["measured_s"]) for k, v in durs.items()}, lead, gap, tail)
    out = Path(out_mp4)
    work = Path(work) if work else out.parent / (out.stem + "_work")
    (work / "clips").mkdir(parents=True, exist_ok=True)
    film_bytes = P(ep["film_file"]).read_bytes()
    clips, reused = [], []
    for sh, row in zip(shots, sched):
        spec_path = P(sh["spec"])
        spec = _load(spec_path)
        spec["seconds"] = row["seconds"]
        spec["film_file"] = str(P(ep["film_file"])) if spec.get("kind", "photo") == "photo" else spec.get("film_file")
        if spec.get("kind", "photo") == "photo":
            spec["photo"] = str(spec_path.parent / spec["photo"]) if not Path(spec["photo"]).is_absolute() else spec["photo"]
            pic = Path(spec["photo"]).read_bytes() if Path(spec["photo"]).exists() else b""
        else:
            for k in ("line_geojson", "film_file"):
                if k in spec and not Path(spec[k]).is_absolute():
                    spec[k] = str((spec_path.parent / spec[k]).resolve())
            pic = b""
            lt = spec.get("line_t")
            if lt and lt[1] > row["seconds"] - 0.1:      # the drawn front must finish inside a short shot
                spec["line_t"] = [min(lt[0], row["seconds"] * 0.1), round(row["seconds"] - 0.1, 3)]
        key = _digest(json.dumps({k: v for k, v in spec.items() if k != "_dir"}, sort_keys=True, default=str), pic, film_bytes)
        clip = work / "clips" / f"{sh['id']}_{key}.mp4"
        if clip.exists():
            reused.append(sh["id"])
        else:
            tmp_spec = work / "clips" / f"{sh['id']}_{key}.spec.json"
            tmp_spec.write_text(json.dumps(spec, indent=1, default=str), encoding="utf-8")
            BS.build_shot(tmp_spec, clip, cache_dir, work, tile_dir)
        clips.append(clip)
    # picture: hard cuts
    listing = work / "concat.txt"
    listing.write_text("".join(f"file '{c.resolve()}'\n" for c in clips), encoding="utf-8")
    silent = work / "silent.mp4"
    _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-c", "copy", str(silent)])
    # voice: every line at its start on the film's clock, then the long-form loudness
    total = sum(r["seconds"] for r in sched)
    inputs, filt, labels = [], [], []
    n = 0
    for row in sched:
        for lid, at in row["lines"]:
            inputs += ["-i", str(P(ep["audio_dir"]) / durs[lid]["file"])]
            ms = int(round(at * 1000))
            filt.append(f"[{n}:a]aresample=48000,adelay={ms}|{ms}[a{n}]"); labels.append(f"[a{n}]"); n += 1
    from explainer_engine.qa import targets
    filt.append("".join(labels) + f"amix=inputs={n}:normalize=0:duration=longest,{targets.loudnorm('long')},apad=whole_dur={total:.3f}[v]")
    voice = work / "voice.wav"
    _run(["ffmpeg", "-y", "-loglevel", "error", *inputs, "-filter_complex", ";".join(filt), "-map", "[v]", "-t", f"{total:.3f}", "-ar", "48000", str(voice)])
    out.parent.mkdir(parents=True, exist_ok=True)
    _run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(silent), "-i", str(voice), "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
          "-shortest", str(out)])
    log = dict(id=ep["id"], out=str(out), seconds=round(total, 3), fps=FPS, shots=[dict(r, clip=c.name) for r, c in zip(sched, clips)], reused=reused,
               lead_s=lead, gap_s=gap, tail_s=tail, loudness="qa/targets.loudnorm('long')", paid_calls=0)
    out.with_suffix(".episode_log.json").write_text(json.dumps(log, indent=1), encoding="utf-8")
    return log


def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise BuildEpisodeError(f"{cmd[0]} failed: {r.stderr.strip()[:400]}")


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.production.build_episode")
    ap.add_argument("episode"); ap.add_argument("out"); ap.add_argument("--work"); ap.add_argument("--tile-dir"); ap.add_argument("--cache-dir", default="jobs/_depth_cache")
    ap.add_argument("--only", help="comma-separated shot ids")
    a = ap.parse_args(argv)
    try:
        log = build_episode(a.episode, a.out, a.work, a.tile_dir, a.cache_dir, set(a.only.split(",")) if a.only else None)
    except (BuildEpisodeError, BS.BuildShotError) as exc:
        print(f"build_episode: {exc}", file=sys.stderr)
        return 2
    print(json.dumps({k: log[k] for k in ("id", "out", "seconds", "reused")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
