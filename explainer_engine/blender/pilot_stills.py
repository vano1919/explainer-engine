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

Three more environments (the creator's card, 2026-11-06 17:17 UTC: several different environments in one pilot, same price): the castle
courtyard with the commander and the scout crossing it, a column marching on a dirt road, a night camp at a forest edge
(``ENV_LAYOUTS``: layouts ``pilot_courtyard`` / ``pilot_march`` / ``pilot_camp``, one shot each, built clip-first like the room: each
holds only its ``in_shot`` list). ``extend`` adds their stills to an existing manifest without re-rendering the room or the battle:

    python -m explainer_engine.blender.pilot_stills extend --base pilot_stills.json --env pilot_courtyard=DIR ... --out D
    python -m explainer_engine.blender.pilot_stills sheet --base pilot_stills.json --stills DIR --out sheet.png   # contact sheet
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
# the picture-only look clauses of the three Qwen prompt variants (Fable 2026-11-06 18:00 UTC: the word cap stays 90, video words go;
# the LTX_STYLES text above is unchanged). Short clauses first; a variant adds clauses while they fit under QWEN_MAX_WORDS, so every still
# keeps its cap: the 87-word establishing reverse gets three words, the short inserts get all of them. S3 = the card's prompt as is.
QWEN_LOOK = {"S1": ["bold ink outlines", "bright colours", "big bulging eyes"],
             "S2": ["chalky painterly background", "muted earthy colours", "vivid glowing accents", "bold uneven ink outlines"],
             "S3": []}

# the three more environments: layout id -> (scene name in the manifest, the look the CI renders it in)
ENV_LAYOUTS = {"pilot_courtyard": ("courtyard", "v01_reference_soft3d"),
               "pilot_march": ("march", "v01_reference_soft3d"),
               "pilot_camp": ("camp", "q1_c2_native_skin@night_camp")}
ENV_ROLE = {"courtyard_cross": "the commander and the scout cross the castle courtyard, side-on, towards the gate",
            "march_side": "a column marches along a dirt road from left to right, seen side-on from the road's edge",
            "camp_fire": "the commander and the scout sit either side of a campfire at a forest edge, at night"}
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
# P1 (the 60 s pilot, 2026-11-06): three more soldiers stills. ``f200`` is the existing camera 200 frames in (the wedge has run into
# the wall); ``wide_high`` and ``front_mid`` are the static cameras of ``layout_passes.BATTLE_CAMERAS`` just before contact. The
# wedge wears tan leather and orange banners, the shield wall green tunics and blue banners (crowd.battle_formations). Same rule as
# the room: the card names only what is in the still, each tag once, nothing about the camera.
_BATTLE_BASE = {"place": BATTLE["place"], "light": BATTLE["light"], "sub_category": "V1", "hero_refs": {}}
_WALL = "a long shield wall of lanky soldiers in green tunics under blue banners"
_WEDGE = "a charging wedge of soldiers in tan leather tunics"
BATTLE_CARDS = {
    "f000": BATTLE,
    "f200": dict(_BATTLE_BASE, tags={"near_army": BATTLE["tags"]["near_army"], "raiders": "soldiers in tan leather tunics",
                                      "banner": BATTLE["tags"]["banner"]},
                 in_shot={"near_army": "the line that breaks", "raiders": "have broken into it", "banner": "above them, flaps"},
                 card={"start": "{raiders} have broken into {near_army}, {banner} above them",
                       "motion": "the line breaks, men stagger and fall back, smoke drifts over them",
                       "settle": "the dust hangs over the field", "refs": []}),
    "wide_high": dict(_BATTLE_BASE, tags={"wall": _WALL, "wedge": _WEDGE, "far_army": BATTLE["tags"]["far_army"]},
                      in_shot={"wall": "the line that holds", "wedge": "charges at it", "far_army": "waits behind the wedge"},
                      card={"start": "{wall} holds the field while {wedge} runs at it, {far_army} behind them",
                            "motion": "the wedge runs into the shield wall, dust rises and the banners sway",
                            "settle": "the two lines are locked together", "refs": []}),
    "front_mid": dict(_BATTLE_BASE, tags={"wall": "a shield wall of lanky soldiers in green tunics under a blue banner",
                                          "wedge": "soldiers in tan leather tunics"},
                      in_shot={"wall": "the line that holds", "wedge": "run into it"},
                      card={"start": "{wall} stands shoulder to shoulder as {wedge} run at it",
                            "motion": "shields push and swords thrust, men stagger",
                            "settle": "the wall holds", "refs": []}),
}
_BATTLE_ID = re.compile(r"^battle_(?:(wide_high|front_mid)_)?f(\d+)_")


def battle_card(sid: str) -> dict:
    """The soldiers card of a battle still id (``battle_f000_colour``, ``battle_wide_high_f096_colour``...)."""
    m = _BATTLE_ID.match(sid)
    if not m:
        raise ContractError(f"{sid}: not a battle still id")
    return BATTLE_CARDS[m.group(1) or ("f200" if int(m.group(2)) >= 150 else "f000")]
_NAME = re.compile(r"\{(\w+)\}")


def _fov_deg(lens_mm: float) -> float:
    return round(math.degrees(2 * math.atan(SENSOR_MM / (2 * lens_mm))), 2)


def cameras(layout: dict | None = None, *, layout_id: str = LAYOUT) -> dict[str, dict]:
    """Shot id -> {role, location, look_at, lens_mm, horizontal_fov_deg, size}: the layout's ``shots`` rows (the room's by default)."""
    from explainer_engine.blender import world_kits as WK
    spec = layout or WK.layouts()["layouts"][layout_id]
    out = {}
    for sid, (c0, c1, a0, a1, lens, n) in spec["shots"].items():
        if c1 or a1 or n != 1:
            raise ContractError(f"{sid}: a pilot still is one frame of a static camera")
        out[sid] = {"role": {**ROLE, **ENV_ROLE}.get(sid, ""), "location": c0, "look_at": a0, "lens_mm": lens,
                    "horizontal_fov_deg": _fov_deg(lens), "size": list(ROOM_SIZE)}
    return out


def all_cameras() -> dict[str, dict]:
    """The room's cameras and the three environments' (one still each)."""
    out = cameras()
    for lid in ENV_LAYOUTS:
        out.update(cameras(layout_id=lid))
    return out


def layout_of(sid: str) -> str:
    """The layout (or ``battle``) a shot id belongs to."""
    from explainer_engine.blender import world_kits as WK
    if sid.startswith("battle"):
        return "battle"
    lay = WK.layouts()["layouts"]
    for lid in (LAYOUT, *ENV_LAYOUTS):
        if sid in lay[lid]["shots"]:
            return lid
    raise ContractError(f"{sid}: no pilot layout has this shot")


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
    owner = layout_of(sid) if layout is None else None
    if sid.startswith("battle"):
        spec = layout or battle_card(sid)
        card, tags, keep = spec["card"], spec["tags"], spec["in_shot"]
    else:
        spec = layout or WK.layouts()["layouts"][owner]
        card, tags, keep = spec["cards"][sid], spec["tags"], WK.dressing(owner, sid) if layout is None else spec["in_shot"][sid]
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


def qwen_variant(sid: str, style: str) -> str:
    """The Qwen prompt of one still in one look variant: the card's prompt, then the style's clauses that fit under ``QWEN_MAX_WORDS``
    (S3: none). Same seed, same LoRA; only these words differ."""
    base = prompts(sid)["qwen"]
    room = QWEN_MAX_WORDS - len(base.split())
    add: list[str] = []
    for c in QWEN_LOOK[style]:
        if len(" ".join([*add, c]).split()) <= room:
            add.append(c)
    return base if not add else base + " " + (", ".join(add)).capitalize() + "."


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
        owner = layout_of(sid)
        tags = (BATTLE if owner == "battle" else WK.layouts()["layouts"][owner])["tags"]
        body = f'{motion}. The {_short(tags[name])} says, "{text}" Then {p["settle"]}. Static camera.'
    else:
        body = f"{motion}, then {p['settle']}. Static camera."
    head = LTX_STYLES[style]
    return " ".join(x for x in (head, body, audio) if x)


def _env_shots(envs: dict[str, Path], out: Path) -> tuple[dict, dict]:
    """(shots, layout files) of the environment stills: each ``world_kits poc --layout <id> --frames 1`` output copied to
    ``out/<shot>.png`` with its camera, ``in_shot`` list, prompts and the layout written beside it as ``<id>_layout.json``."""
    from explainer_engine.blender import world_kits as WK
    shots, files = {}, {}
    for lid, src in envs.items():
        if lid not in ENV_LAYOUTS:
            raise ContractError(f"{lid}: not a pilot environment (known: {', '.join(ENV_LAYOUTS)})")
        scene, _look = ENV_LAYOUTS[lid]
        cams = cameras(layout_id=lid)
        looks = json.loads((Path(src) / "looks.json").read_text(encoding="utf-8"))
        for row in looks["rows"]:
            sid = row["scene"]
            if sid not in cams:
                continue
            dest = Path(out) / f"{sid}.png"
            shutil.copyfile(Path(src) / row["frame_rel"], dest)
            shots[sid] = {"scene": scene, "layout": lid, "file": dest.name, "sha256": C.sha256_file(dest), "look": row["variant"],
                          "engine": row["engine"], "seconds_per_frame": row["seconds_per_frame"], "camera": cams[sid],
                          "in_shot": WK.dressing(lid, sid), "prompts": prompts(sid)}
        missing = sorted(set(cams) - set(shots))
        if missing:
            raise ContractError(f"{lid} shots without a still: {missing}")
        files[lid] = f"{lid}_layout.json"
        write_json_atomic(Path(out) / files[lid], {"layout_id": lid, **WK.layouts()["layouts"][lid]})
    return shots, files


def extend(base: dict, envs: dict[str, Path], out: Path) -> dict:
    """``base`` (a ``pilot_stills/1`` manifest already on the vault: the room and the battle) plus the environments' stills: the base's
    shots keep their files and hashes (nothing is re-rendered), the new ones are copied to ``out`` with their layout files, and
    ``out/pilot_stills.json`` is the merged manifest (``carried`` names the base's shots, whose files are not in ``out``)."""
    if base.get("schema") != SCHEMA:
        raise ContractError(f"not a {SCHEMA} manifest")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shots, files = _env_shots(envs, out)
    clash = sorted(set(shots) & set(base["shots"]))
    if clash:
        raise ContractError(f"shots already in the base manifest: {clash}")
    doc = json.loads(json.dumps(base))
    doc["carried"] = sorted(base["shots"])
    doc["shots"].update(shots)
    doc["layouts"] = {**doc.get("layouts", {}), **files}
    write_json_atomic(out / "pilot_stills.json", doc)
    return doc


def manifest(room: Path, battle: Path | None, out: Path, *, battle_count: int = 5000, envs: dict[str, Path] | None = None) -> dict:
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
    env_shots, env_files = _env_shots(envs or {}, out)
    shots.update(env_shots)
    layout = WK.layouts()["layouts"][LAYOUT]
    write_json_atomic(out / "pilot_room_layout.json", {"layout_id": LAYOUT, **layout})
    doc = {"schema": SCHEMA, "layout": "pilot_room_layout.json", "room_cast": [r[0] for r in layout["cast"]],
           "battle": {"composition": "battle", "count": None if battle is None else battle_count,
                      "passes": None if battle is None else sorted(bm["passes"]), "size": None if battle is None else bm["plan"]["size"]},
           "shots": shots, "hf_prefix": HF_PREFIX}
    if env_files:
        doc["layouts"] = env_files
    write_json_atomic(out / "pilot_stills.json", doc)
    return doc


EXTRA_SCHEMA = "pilot_stills_extra/1"
EXTRA_FILE = "pilot_stills_p16.json"


def extra_manifest(dirs: dict[str, Path], picks: dict[str, list[int]], out: Path, *, battle_count: int = 5000) -> dict:
    """The P1 battle stills of the named static cameras (``layout_passes render --scene battle --camera NAME --out DIR``): the picked
    colour frames copied to ``out/battle_<camera>_f<NNN>_colour.png`` with camera, sha256, seconds per frame and the generated
    prompts. A file of its own (``pilot_stills_p16.json``): ``pilot_stills.json`` is pinned by the running p15 pod and stays as it is."""
    from explainer_engine.blender import layout_passes as LP
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    shots = {}
    for name, d in dirs.items():
        if name not in LP.BATTLE_CAMERAS:
            raise ContractError(f"unknown battle camera {name!r}")
        bm = json.loads((Path(d) / "battle" / "layout_manifest.json").read_text(encoding="utf-8"))
        if bm.get("camera") != name:
            raise ContractError(f"{d}: rendered with camera {bm.get('camera')!r}, not {name!r}")
        row = bm["passes"]["colour"]
        for idx in picks[name]:
            fname = f"frame_{idx:06d}.png"
            if fname not in row["frame_sha256"]:
                raise ContractError(f"{name}: frame {idx} was not rendered")
            sid = f"battle_{name}_f{idx:03d}_colour"
            dest = out / f"{sid}.png"
            shutil.copyfile(Path(d) / "battle" / "colour" / "frames" / fname, dest)
            shots[sid] = {"scene": "battle", "file": dest.name, "sha256": C.sha256_file(dest), "pass": "colour", "frame": idx,
                          "camera_name": name, "camera": LP.BATTLE_CAMERAS[name], "engine": row["engine"],
                          "seconds_per_frame": row["seconds_per_frame"], "wall_seconds": row["wall_seconds"],
                          "prompts": prompts(sid)}
    doc = {"schema": EXTRA_SCHEMA, "battle": {"composition": "battle", "count": battle_count, "size": [1920, 1088]},
           "shots": shots, "hf_prefix": HF_PREFIX}
    write_json_atomic(out / EXTRA_FILE, doc)
    return doc


def upload_extra(out: Path, *, vault=None) -> list[str]:
    """The P1 stills and ``pilot_stills_p16.json`` to ``HF_PREFIX``, checked by sha256; no existing file is touched."""
    from explainer_engine.blender import layout_passes as LP
    from explainer_engine.blender import render as R
    out = Path(out)
    doc = json.loads((out / EXTRA_FILE).read_text(encoding="utf-8"))
    pairs = [(out / s["file"], f"{HF_PREFIX}/{s['file']}") for s in doc["shots"].values()] + [(out / EXTRA_FILE, f"{HF_PREFIX}/{EXTRA_FILE}")]
    vault = vault or R.HFVault()
    vault.upload_many(pairs, f"pilot stills P1 ({len(doc['shots'])} battle shots)")
    listed = vault.listing(f"{HF_PREFIX}/")
    bad = [r for loc, r in pairs if not LP._same(listed.get(r), loc)]
    if bad:
        raise ContractError(f"not on the vault with the local hashes: {bad}")
    return [r for _, r in pairs]


def clip_labels(clips) -> dict[str, str]:
    """Shot id -> "c1 S1 · c2 S2": which clips start from this still (``clips`` = ``p15.build.CLIPS`` rows)."""
    out: dict[str, list[str]] = {}
    for stage, sid, style, *_ in clips:
        out.setdefault(sid, []).append(f"{stage[4:]} {style}")
    return {k: " · ".join(v) for k, v in out.items()}


def sheet(doc: dict, dirs: list[Path], labels: dict[str, str], out: Path, *, cols: int = 3, tile: tuple[int, int] = (800, 450)) -> Path:
    """A contact sheet of the stills that start a clip, one tile per still with its place and the clips that use it. ``dirs`` are
    searched in order for ``<file>`` (the new stills first, then the base's on the vault)."""
    from PIL import Image, ImageDraw, ImageFont
    cap, pad = 44, 12
    shots = [k for k in labels if k in doc["shots"]]
    if len(shots) != len(labels):
        raise ContractError(f"stills without a manifest row: {sorted(set(labels) - set(doc['shots']))}")
    rows = -(-len(shots) // cols)
    W, H = cols * (tile[0] + pad) + pad, rows * (tile[1] + cap + pad) + pad
    img = Image.new("RGB", (W, H), (24, 24, 28))
    dr = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 22)
    except OSError:
        font = ImageFont.load_default()
    for i, sid in enumerate(shots):
        f = next((Path(d) / doc["shots"][sid]["file"] for d in dirs if (Path(d) / doc["shots"][sid]["file"]).is_file()), None)
        if f is None:
            raise ContractError(f"{sid}: {doc['shots'][sid]['file']} is in none of {[str(d) for d in dirs]}")
        im = Image.open(f).convert("RGB").resize(tile, Image.LANCZOS)
        x, y = pad + (i % cols) * (tile[0] + pad), pad + (i // cols) * (tile[1] + cap + pad)
        img.paste(im, (x, y))
        dr.text((x + 6, y + tile[1] + 8), f"{sid}   [{labels[sid]}]", fill=(235, 235, 235), font=font)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    img.save(out, "PNG", optimize=True)
    return out


def upload(out: Path, *, vault=None) -> list[str]:
    """Every still, the layout and the manifest to ``HF_PREFIX``, checked by sha256 against the vault's listing."""
    from explainer_engine.blender import layout_passes as LP
    from explainer_engine.blender import render as R
    out = Path(out)
    doc = json.loads((out / "pilot_stills.json").read_text(encoding="utf-8"))
    carried = set(doc.get("carried", ()))   # an ``extend`` manifest: the base's files are already on the vault
    names = [s["file"] for k, s in doc["shots"].items() if k not in carried] + list(doc.get("layouts", {}).values()) + ["pilot_stills.json"]
    if not carried:
        names.append(doc["layout"])
    pairs = [(out / n, f"{HF_PREFIX}/{n}") for n in names]
    vault = vault or R.HFVault()
    vault.upload_many(pairs, f"pilot stills ({len(doc['shots'])} shots)")
    listed = vault.listing(f"{HF_PREFIX}/")
    bad = [r for loc, r in pairs if not LP._same(listed.get(r), loc)]
    if bad:
        raise ContractError(f"not on the vault with the local hashes: {bad}")
    return [r for _, r in pairs]


def _envs(pairs: list[str]) -> dict[str, Path]:
    out = {}
    for p in pairs:
        lid, _, d = p.partition("=")
        if not d:
            raise ContractError(f"--env {p!r}: LAYOUT=DIR")
        out[lid] = Path(d)
    return out


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
    m.add_argument("--env", action="append", default=[], metavar="LAYOUT=DIR", help="a pilot environment's poc output")
    e = sub.add_parser("extend")
    e.add_argument("--base", type=Path, required=True)
    e.add_argument("--env", action="append", default=[], metavar="LAYOUT=DIR", required=True)
    e.add_argument("--out", type=Path, required=True)
    sh = sub.add_parser("sheet")
    sh.add_argument("--base", type=Path, required=True, help="the merged pilot_stills.json")
    sh.add_argument("--stills", type=Path, action="append", required=True, help="a folder holding the PNGs (repeat; searched in order)")
    sh.add_argument("--out", type=Path, required=True)
    u = sub.add_parser("upload")
    u.add_argument("--out", type=Path, required=True)
    e = sub.add_parser("extra", help="the P1 battle stills of the named cameras -> pilot_stills_p16.json")
    e.add_argument("--camera", action="append", required=True, metavar="NAME=DIR:FRAMES", help="e.g. wide_high=/tmp/wh:96")
    e.add_argument("--out", type=Path, required=True)
    ue = sub.add_parser("upload-extra")
    ue.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    if a.cmd == "cameras":
        print(json.dumps(cameras(), indent=1))
    elif a.cmd == "prompts":
        print(json.dumps({sid: prompts(sid) for sid in cameras()}, indent=1, ensure_ascii=False))
    elif a.cmd == "manifest":
        doc = manifest(a.room, a.battle, a.out, battle_count=a.battle_count, envs=_envs(a.env))
        print(json.dumps({k: v["seconds_per_frame"] for k, v in doc["shots"].items()}, indent=1))
    elif a.cmd == "extra":
        dirs, picks = {}, {}
        for spec in a.camera:
            name, rest = spec.split("=", 1)
            d, frames = rest.rsplit(":", 1)
            dirs[name], picks[name] = Path(d), [int(x) for x in frames.split(",")]
        doc = extra_manifest(dirs, picks, a.out)
        print(json.dumps({k: v["seconds_per_frame"] for k, v in doc["shots"].items()}, indent=1))
    elif a.cmd == "upload-extra":
        print("\n".join(upload_extra(a.out)))

    elif a.cmd == "extend":
        doc = extend(json.loads(a.base.read_text(encoding="utf-8")), _envs(a.env), a.out)
        print(json.dumps({k: v["seconds_per_frame"] for k, v in doc["shots"].items() if k not in doc["carried"]}, indent=1))
    elif a.cmd == "sheet":
        from explainer_engine.training.pods.p15 import build as B
        print(sheet(json.loads(a.base.read_text(encoding="utf-8")), a.stills, clip_labels(B.CLIPS), a.out))
    else:
        print("\n".join(upload(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
