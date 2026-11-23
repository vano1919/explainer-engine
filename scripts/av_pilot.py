"""Build the zero-cost AV pilot of D-135 (examples/av_pilot_2026-11-13/pilot.json) as an episode folder the v4.3 runner takes.

    python scripts/av_pilot.py <out folder> --variant new|baseline [--pictures <folder with S.._start.jpg>]

The folder is named ``ep_toba`` (EP-01: the folder carries its episode's id) and holds Toba's episode.json with the pilot's
places, a production script of the pilot's seven shots (Toba's own shots and lines; the pilot overlays the actions, motion items,
profiles and sound events of its variant), and the pictures copied in. ``baseline`` keeps only the vocabulary the code before
D-135 knew, so the same shots can be run on that code (a git worktree of the base commit). Nothing here calls a paid service.
Then: ``python -m explainer_engine.episode run <out>/ep_toba --to qa --rehearsal`` (no read: a rehearsal on the planned lengths).
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT = ROOT / "examples" / "av_pilot_2026-11-13" / "pilot.json"


def build(out: Path, variant: str, pictures: Path | None = None) -> Path:
    pilot = json.loads(PILOT.read_text(encoding="utf-8"))
    base = ROOT / pilot["base_episode"]
    doc = json.loads((base / "story" / "production_script.json").read_text(encoding="utf-8"))
    by = {s["shot_id"]: s for s in doc["shots"]}
    shots = []
    for spec in pilot["shots"]:
        sh = copy.deepcopy(by[spec["shot_id"]])
        for k in ("route", "route_locked", "route_reason", "map_view", "sound_events", "keyframe_plan",
                  "generation_mode"):
            if k in spec:
                sh[k] = copy.deepcopy(spec[k])
        sh.update(copy.deepcopy(spec["new" if variant == "new" else "old"]))
        if sh["route"] != "map_action":
            sh.pop("map_view", None)
        shots.append(sh)
    lines = {lid for s in shots for lid in s.get("audio_line_ids") or []}
    segs = {s["segment_id"] for s in shots}
    doc["shots"] = shots
    doc["audio_lines"] = [ln for ln in doc["audio_lines"] if ln["line_id"] in lines]
    doc["segments"] = [s for s in doc["segments"] if s["segment_id"] in segs]
    if variant == "new":
        doc["av_contract"] = "av_events/1"
    root = out / "ep_toba"
    if root.exists():
        shutil.rmtree(root)
    (root / "story").mkdir(parents=True)
    ep = json.loads((base / "episode.json").read_text(encoding="utf-8"))
    ep["places"] = pilot["places"]
    (root / "episode.json").write_text(json.dumps(ep, indent=2), encoding="utf-8")
    (root / "story" / "production_script.json").write_text(json.dumps(doc, indent=2), encoding="utf-8")
    if pictures:
        (root / "assets" / "generated" / "images").mkdir(parents=True)
        media = {f["path"]: f for f in json.loads((base / "media_manifest.json").read_text(encoding="utf-8"))["files"]}
        for s in shots:
            if s["route"] == "map_action":
                continue
            rel = f"assets/generated/images/{s['shot_id']}_start.jpg"
            src = pictures / Path(rel).name
            sha = hashlib.sha256(src.read_bytes()).hexdigest()
            if media.get(rel, {}).get("sha256") != sha:
                raise SystemExit(f"{src}: sha256 {sha} is not the one in {base / 'media_manifest.json'}")
            shutil.copy(src, root / rel)
    return root


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("out", type=Path)
    ap.add_argument("--variant", choices=("new", "baseline"), required=True)
    ap.add_argument("--pictures", type=Path)
    a = ap.parse_args(argv)
    print(build(a.out, a.variant, a.pictures))
    return 0


if __name__ == "__main__":
    sys.exit(main())
