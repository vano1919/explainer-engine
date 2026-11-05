"""The turnaround sheet of a character (D-101, roadmap 9.2): the raster identity carrier of approved 3D assets.

One render job of 13 frames through ``render.HeadlessRender`` (the ICW-04 adapter, the ICW-05 style): four full-body views of
the character at rest (front, three-quarter, side, back) and nine face close-ups, one per mouth shape (Rhubarb A-H and the rest
X), so the creator judges the face, the costume and the lip shapes on one page, and ``qa/identity.py`` compares rendered close-ups
with the front views (``identity_refs``). The pose is the first frame of the idle clip, held (the clip at a tiny speed).

    python -m explainer_engine.blender.turnaround render --character ink_test_m --costume costume.mco_male_ranger --out O
        [--variant B_light] [--tint support_blue] [--binary B] [--scale 1.0] [--register]

Outputs in ``O``: ``views/<view>.png`` (each frame as rendered), ``turnaround.png`` (the sheet), ``turnaround.json`` (what was
rendered: character, costume, assets with sha256, style, s/frame). ``--register`` records the sheet in ``assets/library.json``
as ``sheet.<character>_<costume>_turnaround`` (lineage: the head model; deps: every asset of the character). Free: no paid step.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import style_sheets as SS
from explainer_engine.core.store import write_json_atomic

BODY_VIEWS = (("front", (0.0, -4.9, 1.0)), ("three_quarter", (3.45, -3.45, 1.0)), ("side", (4.9, 0.0, 1.0)), ("back", (0.0, 4.9, 1.0)))
BODY_LOOK_Z = 0.92
BODY_LENS = 50.0
FACE_LENS = 85.0
FACE_CAMERA = (0.14, -0.7, 0.03)  # from the mouth centre: slightly to the side, at eye height
MOUTHS = ("A", "B", "C", "D", "E", "F", "G", "H", "X")
FRAMES = len(BODY_VIEWS) + len(MOUTHS)


def views(char_id: str, *, reg: dict | None = None) -> list[dict]:
    """Frame index -> camera pose and mouth shape of the 13 views."""
    ch = C.get(char_id, reg=reg)
    mx, my, mz = ch["mouth"]["center"]
    out = []
    for i, (name, loc) in enumerate(BODY_VIEWS):
        out.append({"frame": i, "view": name, "location": list(loc), "look_at": [0.0, 0.0, BODY_LOOK_Z], "lens_mm": BODY_LENS,
                    "mouth": "X"})
    for j, m in enumerate(MOUTHS):
        loc = [mx + FACE_CAMERA[0], my + FACE_CAMERA[1], mz + FACE_CAMERA[2]]
        out.append({"frame": len(BODY_VIEWS) + j, "view": f"mouth_{m}", "location": loc, "look_at": [mx, my + 0.05, mz + 0.03],
                    "lens_mm": FACE_LENS, "mouth": m, "track": {"rig": "subject_rig", "bone": "Head", "point": [mx, my, mz]}})
    return out


def lipsync_tracks(vs: list[dict], *, reg: dict | None = None) -> dict:
    """One shape key fully on per view (all others off): the lip-sync track format of ``rigs.tracks``."""
    keys = (reg or C.registry())["mouth"]["keys"]
    return {"tracks": {keys[m]: [[v["frame"], 1.0 if v["mouth"] == m else 0.0] for v in vs] for m in MOUTHS if m != "X"}}


def scene(char_id: str, costume_id: str, cpaths: dict[str, Path], *, tint: str | None = None, reg: dict | None = None) -> dict:
    reg = reg or C.registry()
    vs = views(char_id, reg=reg)
    obj, mats = C.scene_object("subject", char_id, costume_id, cpaths, action="Idle_Loop", action_speed=0.001, tint=tint,
                               lipsync=lipsync_tracks(vs, reg=reg), reg=reg)
    floor = {"name": "floor", "add": "plane", "params": {"size": 40}, "material": "floor"}
    keys = [{k: v[k] for k in ("frame", "location", "look_at", "lens_mm", "track") if k in v} for v in vs]
    return {"objects": [floor, obj], "materials": {"floor": {"base": "paper"}, **mats}, "frames_total": FRAMES, "views": vs,
            "camera": {"location": keys[0]["location"], "look_at": keys[0]["look_at"], "lens_mm": BODY_LENS,
                       "focus_distance_m": 4.9, "keys": keys, "interp": "CONSTANT"}}


def render(out: Path, char_id: str, costume_id: str, *, variant: str = "B_light", tint: str | None = None, binary: str | None = None,
           scale: float = 1.0, device: str = "auto", register: bool = False, log=print) -> dict:
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core import shot_cache
    from explainer_engine.core.errors import ContractError
    out = Path(out)
    paths = SS.fetch()
    cpaths = C.fetch()
    reg = C.registry()
    sc = scene(char_id, costume_id, cpaths, tint=tint, reg=reg)
    vs = sc.pop("views")
    _, tokens = SS.style_for(variant)
    sid = f"turnaround_{char_id}_{costume_id.split('.', 1)[1]}"
    job, graph = SS.job_scene(sid, variant, sc, paths)
    spec = SS.spec_for(sid, variant, tokens, scene=job, frames=FRAMES)
    spec["job_id"] = "turnaround_icw06"
    if scale != 1.0:
        spec["frame"]["render_scale"] = scale
    b = BlenderProject().resolve(binary, device=device)
    try:
        m = R.HeadlessRender(b, R.LocalVault(out / "vault")).run(spec, out / "work", scene=job)
    except ContractError as e:
        if scale == 1.0 or "master" not in str(e):
            raise
        m = json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8"))
    sdir = out / "work" / m["cache_key"]
    (out / "views").mkdir(parents=True, exist_ok=True)
    files = {}
    for v in vs:
        src = sdir / "frames" / R.FRAME_NAME.format(index=v["frame"])
        dest = out / "views" / f"{v['view']}.png"
        dest.write_bytes(src.read_bytes())
        files[v["view"]] = str(dest)
    sheet = compose(out / "turnaround.png", files, title=f"{C.get(char_id, reg=reg)['label']} - {C.costume(costume_id, reg=reg)['label']}"
                    f" - style {variant}")
    lib = L.load()
    doc = {"schema": "turnaround/1", "character": char_id, "costume": costume_id, "tint": tint, "variant": variant,
           "assets": [{"id": a, "sha256": L.get(a, lib=lib)["sha256"]} for a in C.asset_ids(char_id, costume_id, reg=reg)],
           "style_sha256": graph["sha256"], "views": files, "sheet": str(sheet), "seconds_per_frame": m["seconds_per_frame"],
           "times": SS.frame_times(sdir), "blender": m["blender"], "scaled": scale != 1.0}
    write_json_atomic(out / "turnaround.json", doc)
    if register:
        doc["asset_id"] = register_sheet(sheet, char_id, costume_id, variant, reg=reg)["id"]
        write_json_atomic(out / "turnaround.json", doc)
    log(f"{char_id}/{costume_id}: {doc['times']['steady_median_s']} s/frame, sheet {sheet}")
    return doc


def compose(dest: Path, files: dict[str, str], *, title: str, cell_h: int = 720) -> Path:
    """The sheet: the four body views in a row (each cropped to the figure's centre), the nine mouths below, labels on each."""
    from PIL import Image, ImageDraw
    body = [n for n, _ in BODY_VIEWS]
    mouths = [f"mouth_{m}" for m in MOUTHS]
    with Image.open(files[body[0]]) as im:
        w, h = im.size
    crop_w = int(h * 0.62)
    bw = int(cell_h * crop_w / h)
    rows = 2
    sheet_w = bw * len(body)
    mouths_per_row = (len(mouths) + 1) // 2
    mw = sheet_w // mouths_per_row
    mh = int(mw * h / w)
    head = 64
    canvas = Image.new("RGB", (sheet_w, head + cell_h + rows * mh), (255, 248, 236))
    d = ImageDraw.Draw(canvas)
    font, small = SS._font(34), SS._font(26)
    d.text((16, 14), title, fill=(31, 36, 48), font=font)
    for i, n in enumerate(body):
        with Image.open(files[n]) as im:
            x0 = (w - crop_w) // 2
            cell = im.convert("RGB").crop((x0, 0, x0 + crop_w, h)).resize((bw, cell_h), Image.LANCZOS)
        canvas.paste(cell, (i * bw, head))
        d.text((i * bw + 12, head + 10), n.replace("_", " "), fill=(31, 36, 48), font=small)
    for j, n in enumerate(mouths):
        r, c = divmod(j, mouths_per_row)
        with Image.open(files[n]) as im:
            cell = im.convert("RGB").resize((mw, mh), Image.LANCZOS)
        canvas.paste(cell, (c * mw, head + cell_h + r * mh))
        d.text((c * mw + 12, head + cell_h + r * mh + 10), n.replace("mouth_", "mouth "), fill=(31, 36, 48), font=small)
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_name(dest.name + ".part.png")
    canvas.save(tmp, optimize=True)
    tmp.replace(dest)
    return dest


def register_sheet(sheet: Path, char_id: str, costume_id: str, variant: str, *, reg: dict | None = None) -> dict:
    """The sheet as the character's raster identity carrier (D-101): kind ``sheet``, lineage the head model, deps every asset."""
    from explainer_engine.world import bible as B
    reg = reg or C.registry()
    ch = C.get(char_id, reg=reg)
    ids = C.asset_ids(char_id, costume_id, reg=reg)
    aid = f"sheet.{char_id}_{costume_id.split('.', 1)[1]}_turnaround"
    rec, _ = L.ingest(sheet, aid, "sheet", replace=True, external=True, tags=["turnaround", "identity", "character", char_id],
                      description=f"turnaround sheet of {ch['label']} in {C.costume(costume_id, reg=reg)['label']} (style {variant}); "
                                  f"the raster identity carrier of D-101", bible_version=B.cite()["version"], deps=ids,
                      parent=ch["head"], made_with={"provider": "blender", "model": "blender", "params": {"variant": variant}},
                      licence={"status": "own_procedural", "note": "rendered by the channel from CC0 assets (character_assets.json)"},
                      source="explainer_engine.blender.turnaround")
    return rec


def identity_refs(char_id: str, costume_id: str, *, out: Path) -> list[Path]:
    """The front views of a rendered turnaround: the references ``qa/identity.hero_identity`` compares close-ups with."""
    return [Path(out) / "views" / f"{v}.png" for v in ("front", "three_quarter")]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.turnaround", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("render")
    r.add_argument("--character", required=True)
    r.add_argument("--costume", required=True)
    r.add_argument("--out", required=True)
    r.add_argument("--variant", default="B_light")
    r.add_argument("--tint")
    r.add_argument("--binary")
    r.add_argument("--scale", type=float, default=1.0)
    r.add_argument("--device", default="auto")
    r.add_argument("--register", action="store_true")
    args = ap.parse_args(argv)
    doc = render(Path(args.out), args.character, args.costume, variant=args.variant, tint=args.tint, binary=args.binary,
                 scale=args.scale, device=args.device, register=args.register)
    print(json.dumps({k: doc[k] for k in ("sheet", "seconds_per_frame")}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
