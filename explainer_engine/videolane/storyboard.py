"""The storyboard gate of the video lane (VL-10, docs/VIDEO_LANE.md): before a paid LTX scene, its start pictures are laid out
in cut order on one contact sheet and checked on the PICTURES (not the plan text):

* every shot that needs its own picture has it (the first shot, every coverage and insert shot; a continuation is derived
  from the clip before and shows its source's picture with a "from <shot>" label);
* the edit plan of the scene passes (VL-01..VL-06 FAIL rows block);
* no two shots of the scene repeat one composition (a perceptual hash a few bits apart = the same picture twice: FAIL);
* every coverage and insert picture belongs to the scene master's place: the top third (sky, ceiling, far set) and the whole
  frame's palette are compared with the master's (``training/video_qa`` palette distance, BP-166's threshold), and the
  brightness gap is measured. A miss is REVIEW: the numbers are BP-166's hypothesis, Claude and the creator look at the sheet.

The record ``production/storyboard/<scene>.json`` pins every picture's sha256 and the plan's digest; ``fresh`` says whether it
still describes the pictures on disk, and ``videolane/scene.py`` refuses to write a paid scene file without a fresh PASS.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from explainer_engine.core.store import write_json_atomic
from explainer_engine.qa import gates as G
from explainer_engine.standards import sourced_rules as SR
from explainer_engine.videolane import plan as P

SCHEMA = "video_storyboard/1"
TOP = (0.0, 0.0, 1.0, 1.0 / 3.0)
DUP_BITS = 6                 # engineering default: a 64-bit dHash this close is the same composition (calibrated in the tests)
LUMA_GAP_REVIEW = 0.18       # engineering default: a mean brightness gap (0..1) this large between a shot and its master
CELL = (320, 180)


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _rgb(p: Path, width: int = 320) -> np.ndarray:
    im = Image.open(p).convert("RGB")
    h = max(2, int(round(width * im.height / im.width)))
    return np.asarray(im.resize((width, h), Image.BILINEAR))


def dhash(a: np.ndarray) -> int:
    g = Image.fromarray(a).convert("L").resize((9, 8), Image.BILINEAR)
    x = np.asarray(g, dtype=np.int16)
    bits = (x[:, 1:] > x[:, :-1]).ravel()
    return int("".join("1" if b else "0" for b in bits), 2)


def _bits(a: int, b: int) -> int:
    return bin(a ^ b).count("1")


def picture_of(script: dict, pics: dict, sid: str) -> tuple[str | None, str | None]:
    """(picture key, the shot it comes from): a continuation shows its source chain's picture."""
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    seen, cur = set(), sid
    while cur and cur not in seen:
        seen.add(cur)
        ep = by.get(cur, {}).get("edit_plan") or {}
        if ep.get("continuity_mode") == "continuation" and ep.get("continuity_from"):
            cur = ep["continuity_from"]
            continue
        key = f"{cur}_start"
        return (key if key in pics else None), cur
    return None, None


def compare(master: np.ndarray, shot: np.ndarray) -> dict:
    from explainer_engine.training import video_qa as VQ
    return {"palette_dist": VQ._dist(VQ._palette(master), VQ._palette(shot)),
            "top_palette_dist": VQ._dist(VQ._palette(master, TOP), VQ._palette(shot, TOP)),
            "luma_gap": round(abs(float(master.mean()) - float(shot.mean())) / 255.0, 4)}


def build(root: Path, script: dict, scene_shots: list[str], scene_id: str, *, pictures: dict | None = None,
          max_s: float = 10.0) -> dict:
    """Check one scene's pictures and write its sheet and record. ``pictures`` is ``production/pictures.json``'s map."""
    root = Path(root)
    if pictures is None:
        pictures = json.loads((root / "production" / "pictures.json").read_text(encoding="utf-8"))["pictures"]
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    sub = dict(script, shots=[by[s] for s in scene_shots])
    plan_rows = P.rows(sub, max_s)
    rows = list(plan_rows)
    cells, missing, dups, env = [], [], [], []
    hashes: dict[str, tuple[int, str]] = {}
    pinned: dict[str, str] = {}
    pal_max = float(SR.T("BP-166", "palette_dist_max"))
    master_cache: dict[str, np.ndarray] = {}
    arrays: dict[str, np.ndarray] = {}
    for sid in scene_shots:
        s = by[sid]
        ep = s.get("edit_plan") or {}
        key, src = picture_of(sub, pictures, sid)
        cell = {"shot_id": sid, "mode": ep.get("continuity_mode"), "route": s.get("route"),
                "size": (s.get("camera_spec") or {}).get("shot_size"), "picture": key, "from": src if src != sid else None,
                "seconds": P.clip_seconds(script, s, max_s)["seconds"] if P.is_video(s) else s.get("target_duration_seconds")}
        if key is None:
            missing.append(sid)
            cells.append(cell)
            continue
        path = root / pictures[key]["file"]
        pinned[key] = _sha(path)
        a = _rgb(path)
        arrays[sid] = a
        cell["path"] = str(path)
        if src == sid:   # a picture of its own: duplicates and the master's place
            h = dhash(a)
            for other, (oh, okey) in hashes.items():
                if _bits(h, oh) <= DUP_BITS and okey != key:
                    dups.append(f"{sid} repeats the composition of {other} ({_bits(h, oh)} of 64 bits apart)")
            hashes[sid] = (h, key)
            mkey = ep.get("scene_master")
            if ep.get("continuity_mode") in ("coverage", "insert") and mkey:
                if mkey not in pictures:
                    missing.append(f"{sid}: scene master {mkey}")
                elif mkey != key:
                    if mkey not in master_cache:
                        master_cache[mkey] = _rgb(root / pictures[mkey]["file"])
                        pinned[mkey] = _sha(root / pictures[mkey]["file"])
                    m = compare(master_cache[mkey], a)
                    cell["vs_master"] = m
                    if m["top_palette_dist"] > pal_max or m["palette_dist"] > pal_max or m["luma_gap"] > LUMA_GAP_REVIEW:
                        env.append(f"{sid} vs {mkey}: palette {m['palette_dist']}, top third {m['top_palette_dist']} "
                                   f"(max {pal_max}), brightness gap {m['luma_gap']} (max {LUMA_GAP_REVIEW})")
        cells.append(cell)
    rows.append(G.row("storyboard_pictures_present", not missing, f"{len(missing)} shot(s) without their picture",
                      missing[:20]))
    rows.append(G.row("storyboard_no_repeated_composition", not dups, f"{len(dups)} repeated composition(s)", dups[:20]))
    rows.append(G.row("storyboard_same_place_as_master", not env, f"{len(env)} picture(s) leave the master's place or "
                      "light (BP-166 palette, brightness gap)", env[:20], level=G.REVIEW))
    # FA-14: the heroes before money (costume colours per hero box, SFace faces; level by switch Q3)
    from explainer_engine.videolane import identity as ID
    frames = {c["shot_id"]: (arrays[c["shot_id"]], arrays[c["shot_id"]]) for c in cells if c["shot_id"] in arrays}
    paths = {c["shot_id"]: c["path"] for c in cells if c.get("path")}
    out_dir = root / "production" / "storyboard"
    out_dir.mkdir(parents=True, exist_ok=True)
    rv_p = out_dir / f"{scene_id}.costume_review.json"   # Q3: the eye check of headgear, props, clothes (warning only)
    review = json.loads(rv_p.read_text(encoding="utf-8")) if rv_p.is_file() else None
    rows += ID.rows(sub, scene_shots, frames, paths, ID.references_of(root, script), "storyboard", review=review,
                    facing=ID.facing_of(root))
    cuts = ID.hero_cuts(sub, scene_shots)
    if cuts and any(c["a"] in frames and c["b"] in frames for c in cuts):
        ID.cut_sheet(frames, cuts, out_dir / f"{scene_id}.cuts.jpg")
    sheet = out_dir / f"{scene_id}.jpg"
    contact_sheet(cells, sheet)
    rec = {"schema": SCHEMA, "scene_id": scene_id, "shots": scene_shots, "cells": cells, "rows": rows,
           "verdict": G.verdict(rows), "pictures": pinned, "plan_digest": plan_digest(sub), "sheet": str(sheet),
           "sheet_sha256": _sha(sheet)}
    write_json_atomic(out_dir / f"{scene_id}.json", rec)
    return rec


def plan_digest(script: dict) -> str:
    keep = ("shot_id", "route", "edit_plan", "camera_spec", "audio_line_ids", "video_prompt", "target_duration_seconds")
    shots = [{k: s.get(k) for k in keep} for s in script.get("shots", [])]
    return hashlib.sha256(json.dumps(shots, sort_keys=True).encode()).hexdigest()


def fresh(root: Path, rec: dict, script: dict, pictures: dict) -> list[str]:
    """Why the record no longer describes the scene (empty = fresh)."""
    by = {s["shot_id"]: s for s in script.get("shots", [])}
    why = []
    if plan_digest(dict(script, shots=[by[s] for s in rec["shots"] if s in by])) != rec["plan_digest"]:
        why.append("the scene's edit plan, prompts or lines changed after the storyboard")
    for key, sha in rec["pictures"].items():
        p = Path(root) / pictures.get(key, {}).get("file", "__missing__")
        if not p.is_file() or _sha(p) != sha:
            why.append(f"picture {key} changed after the storyboard")
    return why


def contact_sheet(cells: list[dict], out: Path, cols: int = 4) -> Path:
    """The sequence in cut order: picture, shot id, mode, size, seconds; a missing picture is a red cell."""
    w, h = CELL
    rows_n = max(1, -(-len(cells) // cols))
    sheet = Image.new("RGB", (cols * w, rows_n * (h + 34)), (18, 18, 18))
    d = ImageDraw.Draw(sheet)
    for i, c in enumerate(cells):
        x, y = (i % cols) * w, (i // cols) * (h + 34)
        if c.get("path"):
            im = Image.open(c["path"]).convert("RGB")
            im.thumbnail((w, h))
            sheet.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))
        else:
            d.rectangle([x + 2, y + 2, x + w - 3, y + h - 3], outline=(220, 40, 40), width=3)
        label = f"{i + 1}. {c['shot_id']} {c.get('mode') or c.get('route')} {c.get('size') or ''} {c.get('seconds')}s"
        d.text((x + 4, y + h + 3), label[:52], fill=(235, 235, 235))
        if c.get("from"):
            d.text((x + 4, y + h + 17), f"continues {c['from']}", fill=(160, 200, 255))
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(out, quality=88)
    return out
