"""The J5 route's 2.5D assembly (D-116, guide step 2.1, ICW-11; rules SA-06..SA-09 in docs/SCENE_ASSETS.md): drawn scene assets
(``scene_assets/1``) + a shot -> the ``assemble_25d/1`` job of ``bpy/assemble_25d.py`` -> PNG frames. Free: Blender on the PC or CI.

    python -m explainer_engine.blender.assemble_25d smoke --out D [--binary B | --bpy-python P] [--size 480x270] [--seconds 1]
    python -m explainer_engine.blender.assemble_25d render --assets scene_assets.json --shot shot.json --out D [--binary B]

What Blender builds (all of it from the plan below; the bpy side interprets the job and decides nothing):

- the scene's 360 backdrop as the world (an equirectangular environment, turned by ``backdrop_360.yaw_deg``): an exact
  perspective lookup, so straight lines stay straight on a pan (SA-08 measures it on the smoke's test grid);
- every hero and prop as a camera-facing card at its depth, the feet on the ground at ``pos``: the card's height is set so that
  the figure (the alpha box of the base image) is ``height_m`` tall; the image's own colours are emitted as they are (flat, the
  sheets are drawn flat-lit, plan section 9): no light, no cast shadow from or onto a card (SA-07);
- a flat contact shadow under each hero's feet (a soft dark ellipse, baked, not a light);
- the mouth: four states from the sheet (base = closed, ``mouth_half``, ``mouth_wide``, ``mouth_round``) on the cues of the line
  (``audio.words_to_mouth_cues`` or Rhubarb, read by ``rigs.LipSync``), with a ``CROSS_BLEND_FRAMES``-frame cross-blend; the
  shapes map to states by ``MOUTH_STATE``; a lip-synced shot is at most BP-108's ``dialogue_shot_max_s`` (``LipSync.plan``);
- a blink every ``BLINK_EVERY_S`` (an eyes-closed overlay patch, when the sheet has one) and breathing: a ``BREATH_SCALE``
  vertical scale at ``BREATH_HZ`` about the feet;
- the camera from ``camera_setups`` (OTS, MCU, profile two-shot, ...; ``mcu_front`` with the subjects swapped is the reverse),
  sampled by ``scene_builder.camera_path``.

The J5 card mouth uses the D-121 states (rest, half, wide, round); the 2-frame image cross-blend is local to this renderer.
The numbers of the blink and breathing are the plan's (FINAL_HIGH_LEVEL_PLAN_ka.md section 9, the creator's
07:14 UTC acceptance, D-116); they make the picture, they are not validator thresholds.
"""
from __future__ import annotations

import argparse
import json
import math
import random
import subprocess
import sys
import zlib
from pathlib import Path

from explainer_engine.blender import camera_setups as CS
from explainer_engine.blender import scene_builder as SB
from explainer_engine.blender.rigs import LipSync
from explainer_engine.core import contracts as C
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

SCRIPT = Path(__file__).with_name("bpy") / "assemble_25d.py"
JOB = "assemble_25d/1"
FPS = 24
MOUTH_STATE = {"A": "rest", "X": "rest", "B": "half", "C": "half", "G": "half", "H": "half",
               "D": "wide", "E": "round", "F": "round"}
STATES = ("rest", "half", "wide", "round")
CROSS_BLEND_FRAMES = 2           # D-121: four mouth states + a 2-frame cross-blend
BLINK_EVERY_S = (3.0, 5.0)       # guide 2.1 item 3: a blink every 3-5 s
BLINK_WEIGHTS = (0.5, 1.0, 0.5)  # the eyes-closed overlay over three frames
BREATH_SCALE = 0.005             # breathing: 0.5 % vertical scale ...
BREATH_HZ = 0.25                 # ... at 0.25 Hz
SHADOW = {"width_share": 0.9, "depth_share": 0.3, "alpha": 0.35}   # the contact shadow under the feet (share of the figure width)
ANGLES = ("front", "3q_left", "3q_right", "back")


def _rng(*keys: str) -> random.Random:
    return random.Random(zlib.crc32("/".join(keys).encode("utf-8")))


def mouth_weights(shapes: list[str], *, blend: int = CROSS_BLEND_FRAMES) -> list[dict]:
    """Per frame the weights of the four mouth states (they sum to 1), cross-blended over the last ``blend`` frames."""
    hot = [{s: 1.0 if MOUTH_STATE[sh] == s else 0.0 for s in STATES} for sh in shapes]
    out = []
    for f in range(len(hot)):
        win = hot[max(0, f - blend + 1):f + 1]
        out.append({s: round(sum(h[s] for h in win) / len(win), 6) for s in STATES})
    return out


def mix_factors(w: dict) -> tuple[float, float, float]:
    """(half, wide, round) factors for sequential closed -> half -> wide -> round image mixes."""
    f_round = w["round"]
    prior = w["rest"] + w["half"] + w["wide"]
    f_wide = w["wide"] / prior if prior > 1e-9 else 0.0
    rest = w["rest"] + w["half"]
    f_half = w["half"] / rest if rest > 1e-9 else 0.0
    return round(f_half, 6), round(f_wide, 6), round(f_round, 6)


def blink_track(frames: int, fps: int, seed: str) -> list[float]:
    """The eyes-closed overlay weight per frame: blinks every ``BLINK_EVERY_S`` (seeded per shot and hero), the first one after
    0.5 s to the first interval."""
    rng = _rng("blink", seed)
    out = [0.0] * frames
    t = rng.uniform(0.5, BLINK_EVERY_S[0])
    while True:
        f0 = round(t * fps)
        if f0 >= frames:
            break
        for i, w in enumerate(BLINK_WEIGHTS):
            if f0 + i < frames:
                out[f0 + i] = max(out[f0 + i], w)
        t += rng.uniform(*BLINK_EVERY_S)
    return out


def breath_track(frames: int, fps: int, seed: str) -> list[float]:
    phase = _rng("breath", seed).uniform(0, 2 * math.pi)
    return [round(1.0 + BREATH_SCALE * math.sin(2 * math.pi * BREATH_HZ * f / fps + phase), 6) for f in range(frames)]


def alpha_box(path: Path | str) -> dict:
    """The figure's box in an RGBA card: {size: [w, h], box: [x0, y0, x1, y1]} (pixels, y down, x1/y1 exclusive)."""
    from PIL import Image
    im = Image.open(path)
    if im.mode != "RGBA":
        raise ContractError(f"{path}: a card is an RGBA PNG (edit/cutout.py finish), got {im.mode}")
    box = im.getchannel("A").point(lambda v: 255 if v > 127 else 0).getbbox()
    if box is None:
        raise ContractError(f"{path}: the card is empty")
    return {"size": list(im.size), "box": list(box)}


def card_geometry(path: Path | str, height_m: float) -> dict:
    """The plane of a card in metres, the origin at the figure's feet (the bottom centre of its alpha box): width, height and the
    offsets of the image's left and bottom edges from the feet."""
    ab = alpha_box(path)
    (w, h), (x0, y0, x1, y1) = ab["size"], ab["box"]
    m = height_m / (y1 - y0)
    feet_x = (x0 + x1) / 2
    return {"width_m": round(w * m, 6), "height_m": round(h * m, 6), "left_m": round(-feet_x * m, 6),
            "bottom_m": round(-(h - y1) * m, 6), "figure_width_m": round((x1 - x0) * m, 6), "px": [w, h]}


def _file(ref: dict | None, base: Path, what: str) -> str:
    if not ref:
        raise ContractError(f"{what}: not drawn yet (scene_assets file is null)")
    p = Path(ref["path"]) if Path(ref["path"]).is_absolute() else base / ref["path"]
    if not p.exists():
        raise ContractError(f"{what}: {p} does not exist")
    if C.sha256_file(p) != ref["sha256"]:
        raise ContractError(f"{what}: {p} differs from the sha256 scene_assets names")
    return str(p.resolve())


def _facing(pos, cam_pos) -> float:
    """The card's turn about Z (degrees) so that its front (-Y in its own frame) faces the camera."""
    dx, dy = cam_pos[0] - pos[0], cam_pos[1] - pos[1]
    return round(math.degrees(math.atan2(dx, -dy)), 6)


def plan(assets: dict, shot: dict, *, base: Path | str = ".", fps: int = FPS, width: int = 2560, height: int = 1440,
         engine: str = "eevee", samples: int = 16, cues_base: Path | str | None = None) -> dict:
    """The ``assemble_25d/1`` job body of one J5 shot (without the output paths and the pin, which ``job`` adds).

    ``shot``: {id, scene, seconds, camera: {setup, a?, b?, bearing_deg?}, cast: {hero_id: {pos, angle, line?: {cues, offset_s?}}},
    props?: [{id, pos}]}. ``camera.a`` / ``camera.b`` name the cast members the setup's subjects a and b stand for."""
    C.validate(assets)
    base = Path(base)
    sid = shot["id"]
    scene = assets["scenes"].get(shot["scene"])
    if scene is None:
        raise ContractError(f"{sid}: scene {shot['scene']!r} is not in scene_assets")
    frames = round(shot["seconds"] * fps)
    if frames < 1:
        raise ContractError(f"{sid}: {shot['seconds']} s is no frame")
    heroes = {h["hero"]: h for h in scene["heroes"]}
    cast = shot.get("cast") or {}
    for hid in cast:
        if hid not in heroes:
            raise ContractError(f"{sid}: cast member {hid!r} has no sheet in scene {shot['scene']}")
    cam_spec = shot["camera"]
    subjects = {}
    for role in ("a", "b"):   # a cast id, or a position [x, y, z] for a subject that is not on screen
        who = cam_spec.get(role)
        if who is None:
            continue
        if isinstance(who, list):
            subjects[role] = {"pos": [float(x) for x in who]}
        elif who in cast:
            subjects[role] = {"pos": list(cast[who]["pos"])}
        else:
            raise ContractError(f"{sid}: camera subject {role} = {who!r} is not in the cast")
    if CS.get(cam_spec["setup"])["target"] == "group":   # the group framing centres everyone in the cast
        subjects.update({f"_{hid}": {"pos": list(c["pos"])} for hid, c in cast.items()})
    resolved = CS.resolve(cam_spec["setup"], subjects, bearing_deg=cam_spec.get("bearing_deg", 0.0))
    cam = resolved["camera"]
    if cam_spec.get("pan_deg"):   # a pan on the spot (the SA-08 check): the end pose turns by pan_deg
        cam = dict(cam, rig="dolly", end=dict(cam["start"], yaw_deg=cam["start"]["yaw_deg"] - cam_spec["pan_deg"]))
    path = SB.camera_path(cam, frames)
    keys = []
    for k in path:
        f = SB.forward(k["yaw_deg"], k["pitch_deg"])
        keys.append({"frame": k["frame"], "location": k["pos"], "look_at": [k["pos"][i] + f[i] * SB.LOOK_M for i in range(3)]})
    cam_pos = path[0]["pos"]
    cards = []
    lip = LipSync(fps)
    for hid, c in cast.items():
        hero = heroes[hid]
        angle = c["angle"]
        if angle not in hero["angles"]:
            raise ContractError(f"{sid}: {hid} has no {angle} card (sheet {hero['sheet']} has {sorted(hero['angles'])})")
        ang = hero["angles"][angle]
        img = _file(ang["base"], base, f"{sid}.{hid}.{angle}.base")
        geo = card_geometry(img, hero["height_m"])
        card = {"name": f"card_{hid}", "kind": "hero", "image": img, "pos": list(c["pos"]), "yaw_deg": _facing(c["pos"], cam_pos),
                **geo, "breath": breath_track(frames, fps, f"{sid}/{hid}"),
                "shadow": {"width_m": round(geo["figure_width_m"] * SHADOW["width_share"], 6),
                           "depth_m": round(geo["figure_width_m"] * SHADOW["width_share"] * SHADOW["depth_share"], 6),
                           "alpha": SHADOW["alpha"]}}
        line = c.get("line")
        if line:
            mouth_states = ("mouth_half", "mouth_wide", "mouth_round")
            for st in mouth_states:
                if not ang.get(st):
                    raise ContractError(f"{sid}: {hid} speaks but its {angle} card has no {st} (SA-06: four mouth states)")
            states = {st: _file(ang[st], base, f"{sid}.{hid}.{angle}.{st}") for st in mouth_states}
            for st, p in states.items():
                if alpha_box(p)["size"] != geo["px"]:
                    raise ContractError(f"{sid}: {hid} {st} is not the size of its base card")
            cues = line["cues"]
            if isinstance(cues, str) and cues_base is not None and not Path(cues).is_absolute():
                cues = str(Path(cues_base) / cues)
            lp = lip.plan(cues, frames, offset_s=line.get("offset_s", 0.0))
            w = mouth_weights(list(lp["shapes"]))
            card["mouth"] = {"half": states["mouth_half"], "wide": states["mouth_wide"], "round": states["mouth_round"],
                             "shapes": lp["shapes"], "factors": [list(mix_factors(x)) for x in w]}
        if ang.get("blink"):
            card["blink"] = {"image": _file(ang["blink"], base, f"{sid}.{hid}.{angle}.blink"),
                             "track": blink_track(frames, fps, f"{sid}/{hid}")}
        cards.append(card)
    props = {p["id"]: p for p in scene["props"]}
    for pr in shot.get("props") or []:
        if pr["id"] not in props:
            raise ContractError(f"{sid}: prop {pr['id']!r} is not in scene {shot['scene']}")
        img = _file(props[pr["id"]]["file"], base, f"{sid}.{pr['id']}")
        geo = card_geometry(img, props[pr["id"]]["height_m"])
        cards.append({"name": f"card_{pr['id']}", "kind": "prop", "image": img, "pos": list(pr["pos"]),
                      "yaw_deg": _facing(pr["pos"], cam_pos), **geo})
    bd = scene["backdrop_360"]
    return {"job": JOB, "shot_id": sid, "fps": fps, "frames": frames, "width": width, "height": height, "engine": engine,
            "samples": samples,
            "world": {"image": _file(bd["file"], base, f"{sid}.backdrop_360"), "yaw_deg": bd.get("yaw_deg", 0.0)},
            "camera": {"keys": keys, "lens_mm": cam["lens_mm"], "sensor_mm": CS.SENSOR_MM, "setup": cam_spec["setup"]},
            "cards": cards,
            "probe": [{"name": "target", "at": resolved["target"]}]}


def job(body: dict, out: Path | str, pin_version: str) -> dict:
    """The job file: the plan + the pinned version + where the frames, the progress lines and the report go."""
    d = Path(out)
    return {**body, "pin_version": pin_version, "frame_list": list(range(body["frames"])), "frames_dir": str(d / "frames"),
            "frame_name": "frame_{index:06d}.png", "progress": str(d / "progress.jsonl"), "report": str(d / "bpy_report.json")}


def command(launcher: list[str], job_path: Path | str) -> list[str]:
    """Blender's command line (``launcher`` = [binary] from ``project.resolve``) or, with a Python that has the bpy wheel
    (``--bpy-python``, the same pinned 5.2.3), that Python running the script."""
    if len(launcher) == 1 and not launcher[0].endswith(("python", "python3", "python.exe")):
        return [launcher[0], "--background", "--factory-startup", "--python-exit-code", "1", "--python", str(SCRIPT), "--", str(job_path)]
    return [*launcher, str(SCRIPT), "--", str(job_path)]


def run(body: dict, out: Path | str, launcher: list[str], pin_version: str) -> dict:
    """Render one planned shot under ``out``; returns the bpy report (+ the frame files). Raises on a non-zero exit."""
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    j = job(body, out, pin_version)
    jp = out / "job.json"
    write_json_atomic(jp, j)
    proc = subprocess.run(command(launcher, jp), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    (out / "blender.log").write_text(proc.stdout, encoding="utf-8")
    if proc.returncode:
        raise ContractError(f"{body['shot_id']}: Blender exited {proc.returncode} (see {out / 'blender.log'})")
    rep = json.loads((out / "bpy_report.json").read_text(encoding="utf-8"))
    rep["frame_files"] = [str(p) for p in sorted((out / "frames").glob("frame_*.png"))]
    return rep


# --- checks on the frames (host side, numpy) ----------------------------------------------------------------------------------

HORIZON_BEND_REVIEW = 0.01   # SA-08: a straight line that bends more than 1 % of the frame height on a 30-degree pan (plan 9)


def horizon_rows(png: Path | str, *, sky=(0.0, 0.0, 1.0), ground=(0.0, 1.0, 0.0)) -> list[float]:
    """Per column the row (0 = top, share of the height) where the smoke grid's sky colour turns into its ground colour."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(png).convert("RGB"), dtype=np.float64) / 255.0
    sky_d = np.linalg.norm(a - np.array(sky), axis=-1)
    gr_d = np.linalg.norm(a - np.array(ground), axis=-1)
    is_ground = gr_d < sky_d
    h = a.shape[0]
    rows = []
    for x in range(a.shape[1]):
        col = is_ground[:, x]
        idx = np.nonzero(col)[0]
        rows.append(float(idx[0]) / h if len(idx) else float("nan"))
    return rows


def horizon_bend(png: Path | str, *, median: int = 9) -> float:
    """SA-08: the largest distance (share of the frame height) between the horizon and the straight line through its two
    ends. The rows are median-filtered over ``median`` columns first, so the anti-aliased foot of a post is not a bend."""
    rows = [r for r in horizon_rows(png) if r == r]
    if len(rows) < 2:
        return float("nan")
    k = median // 2
    rows = [sorted(rows[max(0, i - k):i + k + 1])[len(rows[max(0, i - k):i + k + 1]) // 2] for i in range(len(rows))]
    n = len(rows)
    a, b = rows[0], rows[-1]
    return max(abs(r - (a + (b - a) * i / (n - 1))) for i, r in enumerate(rows))


# --- the free smoke: synthetic flat assets, the four dialogue shots and the pan check ---------------------------------------

SMOKE_CAST = {"H1": [-1.1, 2.0, 0.0], "H3": [1.1, 2.6, 0.0]}


def _smoke_assets(d: Path) -> dict:
    """A 360 test grid (blue sky, green ground, black posts every 15 degrees) and two inked flat figures with four mouth states
    and an eyes-closed patch, all drawn here with numpy; returns the scene_assets/1 document naming them."""
    import numpy as np
    from PIL import Image, ImageDraw
    d.mkdir(parents=True, exist_ok=True)
    W, H = 2048, 1024
    g = np.zeros((H, W, 3), np.uint8)
    g[: H // 2] = (0, 0, 255)
    g[H // 2:] = (0, 255, 0)
    for k in range(24):
        x = int(k * W / 24)
        g[H // 2 - 160:H // 2, x:x + 4] = 0
    Image.fromarray(g).save(d / "grid360.png")

    def figure(name, body, skin):
        out = {}
        for st, mh in (("base", 0), ("mouth_half", 8), ("mouth_wide", 16), ("mouth_round", 24)):
            im = Image.new("RGBA", (400, 1000), (0, 0, 0, 0))
            dr = ImageDraw.Draw(im)
            dr.rounded_rectangle((90, 300, 310, 990), 60, fill=body + (255,), outline=(0, 0, 0, 255), width=8)
            dr.ellipse((110, 60, 290, 300), fill=skin + (255,), outline=(0, 0, 0, 255), width=8)
            dr.ellipse((150, 140, 180, 170), fill=(0, 0, 0, 255))
            dr.ellipse((220, 140, 250, 170), fill=(0, 0, 0, 255))
            if mh:
                dr.ellipse((170, 230 - mh // 2, 230, 230 + mh // 2), fill=(90, 0, 0, 255), outline=(0, 0, 0, 255), width=4)
            else:
                dr.line((170, 230, 230, 230), fill=(0, 0, 0, 255), width=6)
            p = d / f"{name}_{st}.png"
            im.save(p)
            out[st] = p
        lid = Image.new("RGBA", (400, 1000), (0, 0, 0, 0))
        ImageDraw.Draw(lid).rectangle((140, 135, 260, 175), fill=skin + (255,))
        ImageDraw.Draw(lid).line((145, 160, 255, 160), fill=(0, 0, 0, 255), width=6)
        out["blink"] = d / f"{name}_blink.png"
        lid.save(out["blink"])
        return out

    figs = {"H1": figure("h1", (170, 30, 30), (240, 200, 160)), "H3": figure("h3", (60, 60, 140), (220, 190, 150))}
    ref = lambda p: {"path": Path(p).name, "sha256": C.sha256_file(p)}   # noqa: E731
    L = "flat ambient lighting, no cast shadows"
    from explainer_engine.qa import style_prompt
    heroes = []
    for hid, f in figs.items():
        heroes.append({"hero": hid, "sheet": f"sheet.{hid.lower()}", "height_m": 1.75, "lighting_note": L,
                       "prompt": f"xworld style, smoke figure {hid}, seen from the front, {L}, plain neutral background",
                       "angles": {a: {"base": ref(f["base"]), "mouth_half": ref(f["mouth_half"]), "mouth_wide": ref(f["mouth_wide"]),
                                      "mouth_round": ref(f["mouth_round"]), "blink": ref(f["blink"])} for a in ANGLES}})
    return {"schema": "scene_assets/1", "episode": "assemble_25d_smoke",
            "style": {k: style_prompt.INFERENCE[k] for k in ("base", "lora", "lora_weight")},
            "scenes": {"S01": {"backdrop_360": {"asset": "grid360", "size": [W, H], "prompt": "smoke test grid", "yaw_deg": 0,
                                                "file": ref(d / "grid360.png")},
                               "heroes": heroes, "props": [], "defects": []}}}


def _smoke_cues(seconds: float) -> dict:
    """A spoken line's cues for the smoke: the words of a short sentence spread over the shot (audio.words_to_mouth_cues)."""
    from explainer_engine.audio import words_to_mouth_cues as W
    words = [
        {"text": "A", "start": round(seconds * 0.10, 3), "end": round(seconds * 0.30, 3)},
        {"text": "O", "start": round(seconds * 0.34, 3), "end": round(seconds * 0.54, 3)},
        {"text": "Me", "start": round(seconds * 0.60, 3), "end": round(seconds, 3)},
    ]
    return {"metadata": {"soundFile": "smoke", "duration": seconds}, "mouthCues": W.mouth_cues(words, duration=seconds)}


def smoke_shots(seconds: float) -> list[dict]:
    """The guide's four-shot dialogue (master two-shot, OTS A, MCU B speaking, reverse MCU A reacting) and the 30-degree pan."""
    cast = {h: {"pos": p, "angle": "front"} for h, p in SMOKE_CAST.items()}
    speaking = {**cast, "H3": {**cast["H3"], "line": {"cues": _smoke_cues(seconds)}}}
    return [
        {"id": "J5-01_master", "scene": "S01", "seconds": seconds, "camera": {"setup": "profile_two_shot", "a": "H1", "b": "H3"},
         "cast": {"H1": {**cast["H1"], "angle": "3q_right"}, "H3": {**cast["H3"], "angle": "3q_left"}}},
        {"id": "J5-02_ots_a", "scene": "S01", "seconds": seconds, "camera": {"setup": "ots_a", "a": "H1", "b": "H3"},
         "cast": {"H1": {**cast["H1"], "angle": "back"}, "H3": {**cast["H3"], "angle": "front"}}},
        {"id": "J5-03_mcu_b_speaks", "scene": "S01", "seconds": seconds, "camera": {"setup": "mcu_front", "a": "H1", "b": "H3"},
         "cast": speaking},
        {"id": "J5-04_mcu_a_reacts", "scene": "S01", "seconds": seconds, "camera": {"setup": "mcu_front", "a": "H3", "b": "H1"},
         "cast": cast},
        {"id": "J5-05_pan30", "scene": "S01", "seconds": seconds,
         "camera": {"setup": "establishing_wide", "pan_deg": 30, "a": [0.0, 2.3, 0.0]},
         "cast": {}},
    ]


def smoke(out: Path | str, launcher: list[str], pin_version: str, *, width: int, height: int, seconds: float,
          engine: str = "eevee", samples: int = 8) -> dict:
    out = Path(out)
    assets = _smoke_assets(out / "assets")
    write_json_atomic(out / "scene_assets.json", assets)
    rows, failures = {}, []
    for sh in smoke_shots(seconds):
        body = plan(assets, sh, base=out / "assets", width=width, height=height, engine=engine, samples=samples)
        rep = run(body, out / sh["id"], launcher, pin_version)
        files = rep["frame_files"]
        row = {"frames": len(files), "seconds_per_frame": rep.get("seconds_per_frame"), "cards": rep.get("cards"),
               "cast_shadows": rep.get("cast_shadows")}
        if len(files) != body["frames"]:
            failures.append(f"{sh['id']}: {len(files)} of {body['frames']} frames")
        if rep.get("cast_shadows"):
            failures.append(f"{sh['id']}: cards cast shadows: {rep['cast_shadows']} (SA-07)")
        if sh["camera"].get("pan_deg"):
            bends = [horizon_bend(files[0]), horizon_bend(files[-1])]
            row["horizon_bend"] = [round(b, 5) for b in bends]
            if max(bends) > HORIZON_BEND_REVIEW:
                failures.append(f"{sh['id']}: the horizon bends {max(bends):.3%} of the frame height (SA-08)")
        for card in body["cards"]:
            if "mouth" not in card:
                continue
            factors = card["mouth"]["factors"]
            active = sum(1 for f in factors if any(v > 0.5 for v in f))
            by_state = {name: sum(1 for f in factors if f[i] > 0.5) for i, name in enumerate(("half", "wide", "round"))}
            row["mouth_frames_active"] = active
            row["mouth_frames_by_state"] = by_state
            missing = [name for name, count in by_state.items() if count == 0]
            if missing:
                failures.append(f"{sh['id']}: dialogue smoke did not exercise mouth states {', '.join(missing)}")
            if active == 0:
                failures.append(f"{sh['id']}: speaking shot has no active mouth frames")
        rows[sh["id"]] = row
    summary = {"schema": "assemble_25d_smoke/1", "shots": rows, "failures": failures, "size": [width, height], "engine": engine}
    write_json_atomic(out / "smoke_summary.json", summary)
    return summary


def _launcher(binary: str | None, bpy_python: str | None) -> tuple[list[str], str]:
    from explainer_engine.blender import project as P
    proj = P.BlenderProject()
    if bpy_python:
        return [bpy_python], proj.version
    return [proj.resolve(binary).path], proj.version


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("smoke", "render"):
        p = sub.add_parser(name)
        p.add_argument("--out", required=True)
        p.add_argument("--binary", default=None)
        p.add_argument("--bpy-python", default=None, help="a Python with the bpy 5.2.3 wheel instead of the Blender binary")
        p.add_argument("--size", default="480x270" if name == "smoke" else "2560x1440")
        p.add_argument("--engine", default="eevee", choices=("eevee", "cycles"))
        p.add_argument("--samples", type=int, default=8 if name == "smoke" else 16)
        if name == "smoke":
            p.add_argument("--seconds", type=float, default=1.0)
        else:
            p.add_argument("--assets", required=True)
            p.add_argument("--shot", required=True)
    a = ap.parse_args(argv)
    w, h = (int(x) for x in a.size.split("x"))
    launcher, pin = _launcher(a.binary, a.bpy_python)
    if a.cmd == "smoke":
        s = smoke(a.out, launcher, pin, width=w, height=h, seconds=a.seconds, engine=a.engine, samples=a.samples)
        print(json.dumps(s, indent=1))
        return 1 if s["failures"] else 0
    assets = json.loads(Path(a.assets).read_text(encoding="utf-8"))
    shot = json.loads(Path(a.shot).read_text(encoding="utf-8"))
    body = plan(assets, shot, base=Path(a.assets).parent, width=w, height=h, engine=a.engine, samples=a.samples,
                cues_base=Path(a.shot).parent)
    rep = run(body, a.out, launcher, pin)
    print(json.dumps({k: v for k, v in rep.items() if k != "frame_files"}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
