"""The pilot's Blender stills (the creator, 2026-11-06 15:25 UTC): a furnished room built from the libraries (``world_layouts.json``
layout ``pilot_room``: the Quaternius MegaKit walls, Poly Haven CC0 furniture and the Quaternius cast) seen by every camera of a
scene of a few minutes, and a soldiers scene (``layout_passes`` battle: 5,000 soldiers as crowd tiers, colour and depth, no
Freestyle). One frame 0 per shot; Qwen restyles them and LTX animates one shot per scene (PILOT_1MIN_PLAN.md). Free: Blender on
this container, the PC or CI (D-114).

    python -m explainer_engine.blender.pilot_stills cameras                       # the shot list with every camera, no render
    python -m explainer_engine.blender.pilot_stills prompts                       # each shot card -> its Qwen and LTX prompts
    python -m explainer_engine.blender.pilot_stills manifest --room R --battle B --out D   # pilot_stills/1: files, sha256, s/frame
    python -m explainer_engine.blender.pilot_stills upload --out D                # to HF route_test_2026-11/pilot/blender/

``R`` is a ``world_kits poc --layout pilot_room --frames 1 --scale 1.0`` output, ``B`` a ``layout_passes render --scene battle
--passes colour,depth --only-frames ...`` output. The same set, props and cast stand in every room shot; only the camera moves.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import shutil
import sys
from pathlib import Path

from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

SCHEMA = "pilot_stills/1"
LAYOUT = "pilot_room"
HF_PREFIX = "route_test_2026-11/pilot/blender"
ROOM_SIZE = (2560, 1440)
SENSOR_MM = 36.0
# what each room camera is for in the scene (the cut: establish the room, the two-shot, the over-the-shoulder pair, the reverse, inserts)
ROLE = {"room_establishing": "establishing wide from the stove corner",
        "room_two_shot": "two-shot of host and guest across the table",
        "room_close_host": "over the guest's shoulder onto the host (close-up)",
        "room_close_guest": "over the host's shoulder onto the guest (reverse close-up, same side of the line)",
        "room_reverse": "reverse wide from the clock corner",
        "room_insert_table": "insert: the table with jug, plates, bowl and candle",
        "room_insert_clock": "insert: the mantel clock on the chest of drawers"}
# the LTX style sentence of every film shot (examples/film_shots/*.json "video_sentence"), word for word
VIDEO_SENTENCE = ("Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon "
                  "timing, poses hold between quick moves.")
# the video style sentences one start-up compares (Fable 16:42 UTC): S1 our film sentence, S2 the xworld captions' look words
# (qa/style_prompt.STYLE_TAIL from "bold uneven"), S3 none (motion and settle only)
LTX_STYLES = {"S1": VIDEO_SENTENCE,
              "S2": "Hand-drawn 2D animation, bold uneven black ink outlines, chalky textured painterly background, muted earthy "
                    "colours with vivid glowing accents.",
              "S3": ""}
QWEN_MAX_WORDS = 90     # Fable, 2026-11-06 15:57 UTC: a pilot still's prompt is at most 90 words
# the soldiers scene (``layout_passes`` battle, frame 0: the near army from behind, the far army under its banners across a plain):
# one card like the room's; the still is the crowd composition itself, so everything in it acts in the clip
BATTLE = {"tags": {"near_army": "a dense army of lanky soldiers in green tunics, each with his own face and helmet",
                   "far_army": "a far army under orange banners", "banner": "a big blue banner on a pole"},
          "in_shot": {"near_army": "charges in the clip", "far_army": "what they charge at", "banner": "flaps as they run"},
          "place": "a dusty plain below a grassy ridge in a medieval war", "light": "a low golden sun under drifting clouds",
          "sub_category": "V1", "hero_refs": {},
          "card": {"start": "{near_army} stands ready, facing {far_army} across the field, {banner} above them",
                   "motion": "the near army charges forward across the plain, dust rises and the banners flap",
                   "settle": "the two armies meet in a cloud of dust", "refs": []}}
_NAME = re.compile(r"\{(\w+)\}")


def _fov_deg(lens_mm: float) -> float:
    return round(math.degrees(2 * math.atan(SENSOR_MM / (2 * lens_mm))), 2)


def cameras(layout: dict | None = None) -> dict[str, dict]:
    """Shot id -> {role, location, look_at, lens_mm, horizontal_fov_deg, size}: the room layout's ``shots`` rows."""
    from explainer_engine.blender import world_kits as WK
    spec = layout or WK.layouts()["layouts"][LAYOUT]
    out = {}
    for sid, (c0, c1, a0, a1, lens, n) in spec["shots"].items():
        if c1 or a1 or n != 1:
            raise ContractError(f"{sid}: a pilot still is one frame of a static camera")
        out[sid] = {"role": ROLE.get(sid, ""), "location": c0, "look_at": a0, "lens_mm": lens, "horizontal_fov_deg": _fov_deg(lens),
                    "size": list(ROOM_SIZE)}
    return out


def _short(tag: str) -> str:
    """The noun of a tag ("the broad commander with a grey beard..." -> "commander"), for the second mention and the image list."""
    return tag.split(" with ")[0].split(" in ")[0].split(",")[0].split()[-1]


def _names(text: str) -> list[str]:
    return _NAME.findall(text)


def prompts(sid: str, layout: dict | None = None) -> dict:
    """The shot card -> the Qwen prompt and the LTX prompt (Fable, 2026-11-06 15:57 UTC: generated, never written by hand).

    Qwen: the trigger, the clip's START (only the shot's ``in_shot`` names, each tag said once), the place and era, the light; no
    camera or layout words (Image 1, the Blender still, carries the layout); at most QWEN_MAX_WORDS and no FAIL or REVIEW from
    ``qa/style_prompt.check``. LTX: the style sentence, the motion, then the settle at the end, and a static camera."""
    from explainer_engine.blender import world_kits as WK
    from explainer_engine.qa import style_prompt as SP
    if sid.startswith("battle"):
        spec = layout or BATTLE
        card, tags, keep = spec["card"], spec["tags"], spec["in_shot"]
    else:
        spec = layout or WK.layouts()["layouts"][LAYOUT]
        card, tags, keep = spec["cards"][sid], spec["tags"], WK.dressing(LAYOUT, sid) if layout is None else spec["in_shot"][sid]
    light = card.get("light", spec["light"])
    start_names = _names(card["start"]) + _names(light)
    used = start_names + _names(card["motion"]) + _names(card["settle"])
    stray = sorted(set(used) - set(keep or ()))
    if stray:
        raise ContractError(f"{sid}: the card names {stray}, which are not in the shot (in_shot)")
    twice = sorted({n for n in start_names if start_names.count(n) > 1})
    if twice:
        raise ContractError(f"{sid}: {twice} said twice in the start; each tag once")
    missing = sorted(set(used) - set(tags))
    if missing:
        raise ContractError(f"{sid}: no tag for {missing}")

    def fill(text, seen):
        def one(m):
            n = m.group(1)
            if n in seen:   # said once: later mentions use the short noun of the tag
                return "the " + _short(tags[n])
            seen.add(n)
            return tags[n]
        return _NAME.sub(one, text)
    seen: set[str] = set()
    start = fill(card["start"], seen)
    refs = list(card.get("refs", []))
    if set(refs) - set(keep or ()):
        raise ContractError(f"{sid}: a reference image of {sorted(set(refs) - set(keep or ()))}, who is not in the shot")
    # the edit's images (p14_qwen B): Image 1 the Blender still carries places, sizes and poses; one hero sheet per listed name
    who = "".join(f" Image {i} is the {_short(tags[n])}." for i, n in enumerate(refs, 2))
    pre = f"Image 1 is the scene: keep every place, size and pose.{who}"
    qwen = f"{SP.TRIGGER}, {pre} {start[0].upper() + start[1:]}, in {spec['place']}, lit by {fill(light, seen)}."
    n = len(qwen.split())
    if n > QWEN_MAX_WORDS:
        raise ContractError(f"{sid}: the Qwen prompt has {n} words, over {QWEN_MAX_WORDS}")
    bad = [f for f in SP.check(qwen, sub_category=spec.get("sub_category")) if f["severity"] in ("FAIL", "REVIEW")]
    if bad:
        raise ContractError(f"{sid}: the Qwen prompt fails the style check: {bad}")
    seen2: set[str] = set()
    motion, settle = fill(card["motion"], seen2), fill(card["settle"], seen2)
    ltx = f"{VIDEO_SENTENCE} {motion[0].upper() + motion[1:]}, then {settle}. Static camera."
    return {"qwen": qwen, "qwen_words": n, "ltx": ltx, "card": card, "names": sorted(set(used)),
            "hero_refs": [spec["hero_refs"][r] for r in refs], "motion": motion, "settle": settle}


def ltx_prompt(sid: str, *, style: str = "S1", audio: str | None = None, line: tuple[str, str] | None = None) -> str:
    """The LTX prompt of one clip from the shot card (the creator 2026-11-06 16:42 UTC: several prompt styles per start-up):
    ``LTX_STYLES[style]`` (S3 = none), the motion (``line``: one spoken sentence, in quotes, after the motion), the settle, a static
    camera, then ``audio`` ("We hear ...": LTX-2.5 distilled draws its native audio from the same prompt, distilled.py:563-573).
    ``line`` = (cast name, one sentence): "The <noun> says, "..."" between the motion and the settle."""
    p = prompts(sid)
    motion = p["motion"][0].upper() + p["motion"][1:]
    if line:
        name, text = line
        if name not in p["names"]:
            raise ContractError(f"{sid}: {name} speaks but is not in the shot's card")
        from explainer_engine.blender import world_kits as WK
        tags = (BATTLE if sid.startswith("battle") else WK.layouts()["layouts"][LAYOUT])["tags"]
        body = f'{motion}. The {_short(tags[name])} says, "{text}" Then {p["settle"]}. Static camera.'
    else:
        body = f"{motion}, then {p['settle']}. Static camera."
    head = LTX_STYLES[style]
    return " ".join(x for x in (head, body, audio) if x)


def manifest(room: Path, battle: Path | None, out: Path, *, battle_count: int = 5000) -> dict:
    """Copy the stills to ``out/<shot>.png`` (the HF names), with the layout, the cameras and the measured seconds per frame."""
    from explainer_engine.blender import world_kits as WK
    room, out = Path(room), Path(out)
    out.mkdir(parents=True, exist_ok=True)
    looks = json.loads((room / "looks.json").read_text(encoding="utf-8"))
    cams = cameras()
    shots = {}
    for row in looks["rows"]:
        sid = row["scene"]
        if sid not in cams:
            continue
        src = room / row["frame_rel"]
        dest = out / f"{sid}.png"
        shutil.copyfile(src, dest)
        shots[sid] = {"scene": "room", "file": dest.name, "sha256": C.sha256_file(dest), "look": row["variant"], "engine": row["engine"],
                      "seconds_per_frame": row["seconds_per_frame"], "camera": cams[sid],
                      "in_shot": WK.dressing(LAYOUT, sid), "prompts": prompts(sid)}
    missing = sorted(set(cams) - set(shots))
    if missing:
        raise ContractError(f"room shots without a still: {missing}")
    if battle is not None:
        bm = json.loads((Path(battle) / "battle" / "layout_manifest.json").read_text(encoding="utf-8"))
        for kind, row in bm["passes"].items():
            for name in sorted(row["frame_sha256"]):
                idx = int(Path(name).stem.split("_")[1])
                sid = f"battle_f{idx:03d}_{kind}"
                dest = out / f"{sid}.png"
                shutil.copyfile(Path(battle) / "battle" / kind / "frames" / name, dest)
                shots[sid] = {"scene": "battle", "file": dest.name, "sha256": C.sha256_file(dest), "pass": kind, "frame": idx,
                              "engine": row["engine"], "seconds_per_frame": row["seconds_per_frame"],
                              "wall_seconds": row["wall_seconds"]}
    layout = WK.layouts()["layouts"][LAYOUT]
    write_json_atomic(out / "pilot_room_layout.json", {"layout_id": LAYOUT, **layout})
    doc = {"schema": SCHEMA, "layout": "pilot_room_layout.json", "room_cast": [r[0] for r in layout["cast"]],
           "battle": {"composition": "battle", "count": None if battle is None else battle_count,
                      "passes": None if battle is None else sorted(bm["passes"]), "size": None if battle is None else bm["plan"]["size"]},
           "shots": shots, "hf_prefix": HF_PREFIX}
    write_json_atomic(out / "pilot_stills.json", doc)
    return doc


def upload(out: Path, *, vault=None) -> list[str]:
    """Every still, the layout and the manifest to ``HF_PREFIX``, checked by sha256 against the vault's listing."""
    from explainer_engine.blender import layout_passes as LP
    from explainer_engine.blender import render as R
    out = Path(out)
    doc = json.loads((out / "pilot_stills.json").read_text(encoding="utf-8"))
    names = [s["file"] for s in doc["shots"].values()] + [doc["layout"], "pilot_stills.json"]
    pairs = [(out / n, f"{HF_PREFIX}/{n}") for n in names]
    vault = vault or R.HFVault()
    vault.upload_many(pairs, f"pilot stills ({len(doc['shots'])} shots)")
    listed = vault.listing(f"{HF_PREFIX}/")
    bad = [r for loc, r in pairs if not LP._same(listed.get(r), loc)]
    if bad:
        raise ContractError(f"not on the vault with the local hashes: {bad}")
    return [r for _, r in pairs]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.pilot_stills", description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("cameras")
    sub.add_parser("prompts")
    m = sub.add_parser("manifest")
    m.add_argument("--room", type=Path, required=True)
    m.add_argument("--battle", type=Path)
    m.add_argument("--out", type=Path, required=True)
    m.add_argument("--battle-count", type=int, default=5000)
    u = sub.add_parser("upload")
    u.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "cameras":
        print(json.dumps(cameras(), indent=1))
    elif a.cmd == "prompts":
        print(json.dumps({sid: prompts(sid) for sid in cameras()}, indent=1, ensure_ascii=False))
    elif a.cmd == "manifest":
        doc = manifest(a.room, a.battle, a.out, battle_count=a.battle_count)
        print(json.dumps({k: v["seconds_per_frame"] for k, v in doc["shots"].items()}, indent=1))
    else:
        print("\n".join(upload(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
