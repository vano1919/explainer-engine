"""The ICW-05 style sheets (roadmap 15 ICW-05, 9.1, 21.6 PoC 3): five scenes, one per archetype family, rendered as 2560x1440 single
frames through the ICW-04 adapter (``render.HeadlessRender``) in each style variant, and one collage for the creator's pick
(invariant 6: a new look is one collage of variants).

    python -m explainer_engine.blender.style_sheets register --downloads D      # PoC 3: the CC0 files into asset_library/2
    python -m explainer_engine.blender.style_sheets fetch                       # the registered files into tools/assets_cache
    python -m explainer_engine.blender.style_sheets render --out O [--binary B] [--scenes a,b] [--variants A,B,C,S] [--scale 1.0]
    python -m explainer_engine.blender.style_sheets collage --out O              # O/collage.png + collage_preview.jpg
    python -m explainer_engine.blender.style_sheets clips --out O [--binary B] [--scenes a,b] [--variants B_shadow,...] [--frames 48]
                                                                                 # round 2: moving clips, MP4s, s/frame, first-frame collage

Scenes: ``dialogue_cu`` (two figures across a table, close), ``battle_wide`` (two lines and their cannons, wide and high),
``travel`` (a cart road receding to hills), ``establishing`` (a walled town from above the road), ``map_tableau`` (a war table
seen from above, pieces on a map sheet). Figures are stand-in mannequins (characters come with ICW-06); every material is a
style.py toon material, the imported Poly Haven props and grounds are converted (their diffuse map kept at the token's
``texture_strength`` over its mean colour). Variants ``A``/``B``/``C`` are ``style.VARIANTS`` on the EEVEE path; ``S`` is B on the
Cycles-safe path, shown beside them for reference (roadmap 9.1: compared before any Cycles shot is allowed).

Round 2 (the creator, 2026-11-05: stills cannot show how it moves; the style must not make the video renders heavy; shadows and
reflections are secondary, frame quality and the colour palette come first): ``clips`` renders ``CLIP_SCENES`` as 48-frame
VIDEO_3D shots at 24 fps (a camera push in the dialogue close-up; the near line advancing under a camera dolly in the battle) in
``CLIP_VARIANTS``: B with cast shadows (the old heavy setting, for the cost), B light (no shadows: the new default), B and A with
the palette matched under AgX (``grade.py``). Reflections are not a switch here: every toon material is emission-only, nothing in
the frame is specular. Each clip gets an MP4 review copy (H.264, from the committed frames), its seconds per frame (first frame and
the steady rest apart), and one collage of first frames. The clips can be rendered on the creator's Mac (ICG-3, D-113) with the
same command; CI keeps them as a manual fallback (``style-sheets.yml``, mode clips).

Assets come from ``assets/library.json`` by id (the PoC 3 records, external storage: ``tools/assets_cache/<sha256>/``); ``fetch``
fills the cache from the vault, else from the source URL in ``style_sheet_assets.json``, and keeps a file only at its registered
sha256. Nothing here is paid; frames go to a ``LocalVault`` under the output folder (the creator's vault upload is a separate,
explicit step).
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import sys
import time
import urllib.request
import zipfile
from dataclasses import replace
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.blender import style as S
from explainer_engine.core import shot_cache
from explainer_engine.core.errors import ContractError
from explainer_engine.core.store import write_json_atomic

HERE = Path(__file__).resolve().parent
SOURCES = HERE / "style_sheet_assets.json"
JOB_ID = "style_sheets_icw05b"
UA = {"User-Agent": "explainer-engine-asset-import/1"}  # Poly Haven's CDN refuses Python's default agent
SCENE_IDS = ("dialogue_cu", "battle_wide", "travel", "establishing", "map_tableau")
VARIANT_IDS = ("A", "B", "C", "S")
# Scene colours the palette has no token for yet (terrain and metal): listed here so grade.py matches them too; ICW-07 / the bible
# decide whether they become palette tokens.
SCENE_COLOURS = {"scene_cannon": "#6B6F78", "scene_grass": "#9DAA6A", "scene_hill": "#B9B98A"}
CLIP_SCENES = ("dialogue_cu", "battle_wide")
CLIP_FRAMES = 48
CLIP_VARIANTS = {  # id -> (collage variant, token overrides, label)
    "B_shadow": ("B", {"shadows": True}, "B, cast shadows on"),
    "B_light": ("B", {}, "B light, no shadows"),
    "B_match": ("B", {"palette_match": True}, "B light, AgX palette match"),
    "A_match": ("A", {"palette_match": True}, "A light, fine ink, AgX palette match"),
}
LABELS = {"dialogue_cu": "dialogue close-up", "battle_wide": "battle wide", "travel": "travel", "establishing": "establishing",
          "map_tableau": "map-adjacent tableau"}


# --- PoC 3: register and fetch the CC0 files ------------------------------------------------------------------------------------

def sources(path: Path | None = None) -> list[dict]:
    return json.loads(Path(path or SOURCES).read_text(encoding="utf-8"))["assets"]


def _local_file(a: dict, downloads: Path) -> Path:
    """Where ``register`` finds a downloaded file: <downloads>/<anything>/<name>, unpacking a zip member when the source is one."""
    hits = sorted(downloads.rglob(a["name"]))
    if hits:
        return hits[0]
    if "member" in a:
        for z in downloads.rglob("*.zip"):
            with zipfile.ZipFile(z) as zf:
                if a["member"] in zf.namelist():
                    out = z.parent / a["member"]
                    out.write_bytes(zf.read(a["member"]))
                    return out
    raise FileNotFoundError(f"{a['id']}: {a['name']} is not under {downloads}")


def register(downloads: Path, *, path: Path | None = None, repo: Path | None = None) -> list[dict]:
    """Every PoC 3 file into the library as an external asset_library/2 record (never in git), its licence block from the
    source's row (``licence_sources.json``) plus the asset page and pack version (CN-19). Dependencies first."""
    from explainer_engine.world import bible as B
    bv = B.cite()["version"]
    out = []
    for a in sorted(sources(), key=lambda a: bool(a.get("deps"))):
        f = _local_file(a, Path(downloads))
        if L.sha256_file(f) != a["sha256"]:
            raise ValueError(f"{a['id']}: {f} is not the registered download (sha256 differs)")
        three_d = dict(a.get("three_d") or {}) or None
        rec, _ = L.ingest(f, a["id"], a["kind"], path=path, repo=repo, replace=True, external=True, tags=a["tags"],
                          description=a["description"], bible_version=bv, deps=a.get("deps", []), three_d=three_d,
                          made_with={"provider": "third_party"}, source=f"import {a['source']} {a['url']}",
                          licence=L.licence_from_source(a["source"], url=a["page"], version=a["version"]))
        out.append(rec)
    return out


def _download(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def fetch(*, repo: Path | None = None, download=_download, vault_first: bool = True) -> dict[str, Path]:
    """Asset id -> the local cached file at its registered sha256 (vault first, then the source URL)."""
    repo = Path(repo or L.REPO)
    lib = L.load()
    got = {}
    for a in sources():
        rec = L.get(a["id"], lib=lib)
        if rec["sha256"] != a["sha256"]:
            raise ValueError(f"{a['id']}: style_sheet_assets.json and the library disagree on the sha256")
        have = L.cached(rec, repo=repo)
        if have is None and vault_first:
            try:
                have = L.fetch(a["id"], lib=lib, repo=repo)
            except Exception:  # noqa: BLE001  (no token or no network to the vault: the source URL is the fallback)
                have = None
        if have is None:
            data = download(a["url"])
            if "member" in a:
                if hashlib.sha256(data).hexdigest() != a["archive_sha256"]:
                    raise ValueError(f"{a['id']}: the archive at {a['url']} changed (sha256)")
                data = zipfile.ZipFile(io.BytesIO(data)).read(a["member"])
            if hashlib.sha256(data).hexdigest() != a["sha256"]:
                raise ValueError(f"{a['id']}: {a['url']} gave other bytes than the registered file; nothing kept")
            dest = repo / rec["file"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_suffix(dest.suffix + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            have = dest
        got[a["id"]] = Path(have)
    return got


def texture_mean(path: Path) -> list[float]:
    """The mean colour of an image in Blender's linear RGB (what the toon conversion flattens a photo texture towards)."""
    from PIL import Image, ImageStat
    with Image.open(path) as im:
        mean = ImageStat.Stat(im.convert("RGB").resize((64, 64))).mean
    h = "#" + "".join(f"{round(c):02x}" for c in mean)
    return list(S.srgb_to_linear(h))


# --- the five scenes ----------------------------------------------------------------------------------------------------------

def _figure(name: str, x: float, y: float, tone: str, *, yaw: float = 0.0, scale: float = 1.0) -> list[dict]:
    """A stand-in mannequin (body, head, arms as rods): characters come with ICW-06 (MPFB2/UBC)."""
    s = scale
    return [
        {"name": f"{name}_body", "add": "cylinder", "params": {"radius": 0.24 * s, "depth": 1.0 * s, "vertices": 24},
         "location": [x, y, 0.55 * s], "material": tone, "smooth": True},
        {"name": f"{name}_head", "add": "uv_sphere", "params": {"radius": 0.16 * s, "segments": 24, "ring_count": 12},
         "location": [x, y, 1.27 * s], "material": "skin", "smooth": True},
        {"name": f"{name}_cap", "add": "cone", "params": {"radius1": 0.2 * s, "depth": 0.14 * s, "vertices": 24},
         "location": [x, y, 1.45 * s], "material": "night", "smooth": True},
    ]


def _house(name: str, x: float, y: float, w: float, d: float, h: float, *, roof: str = "roof") -> list[dict]:
    return [{"name": f"{name}_walls", "add": "cube", "params": {"size": 1.0}, "location": [x, y, h / 2], "scale": [w, d, h],
             "material": "brick"},
            {"name": f"{name}_roof", "add": "cone", "params": {"radius1": max(w, d) * 0.78, "depth": h * 0.6, "vertices": 4},
             "location": [x, y, h + h * 0.3], "rotation_deg": [0, 0, 45], "scale": [w / max(w, d), d / max(w, d), 1.0],
             "material": roof}]


def scenes(paths: dict[str, Path]) -> dict[str, dict]:
    """Scene id -> {objects, camera, materials}. ``paths`` maps asset ids to local files (``fetch``)."""
    p = {k: str(v) for k, v in paths.items()}
    tex = lambda aid, **kw: {"base": "paper", "texture": p[aid], "texture_mean": texture_mean(Path(p[aid])), **kw}  # noqa: E731
    mats = {
        "ground": tex("material.ph_cobblestone_floor_01", tile=18.0),
        "brick": tex("material.ph_brick_wall_001", tile=3.0),
        "table": tex("texture.ph_wooden_table_02_diff"),
        "crate": tex("texture.ph_wooden_crate_01_diff"),
        "cannon": {"base": SCENE_COLOURS["scene_cannon"]},
        "skin": {"base": "kit_card"},
        "night": {"base": "night"},
        "side_a": {"base": "faction_a"},
        "side_b": {"base": "faction_b"},
        "coat": {"base": "support_blue"},
        "cloak": {"base": "answer_coral"},
        "roof": {"base": "kit_shadow"},
        "grass": {"base": SCENE_COLOURS["scene_grass"]},
        "hill": {"base": SCENE_COLOURS["scene_hill"]},
        "map": {"base": "paper"},
        "stone": {"base": "grey_mid"},
    }
    table = lambda name, x, y, z, s, yaw=0: {"name": name, "append": {"path": p["model.ph_wooden_table_02"]},  # noqa: E731
                                             "location": [x, y, z], "scale": s, "rotation_deg": [0, 0, yaw], "material": "table"}
    crate = lambda name, x, y, z, s=1.6, yaw=0: {"name": name, "append": {"path": p["model.ph_wooden_crate_01"]},  # noqa: E731
                                                 "location": [x, y, z], "scale": s, "rotation_deg": [0, 0, yaw], "material": "crate"}
    cannon = lambda name, x, y, yaw: {"name": name, "append": {"path": p["model.ph_cannon_01"]}, "location": [x, y, 0],  # noqa: E731
                                      "scale": 1.0, "rotation_deg": [0, 0, yaw], "material": "cannon"}
    ground = {"name": "ground", "add": "plane", "params": {"size": 120}, "material": "ground"}
    out = {}
    # 1 dialogue close-up: two figures across a table, a brick wall behind
    out["dialogue_cu"] = {
        "objects": [ground, {"name": "wall", "add": "cube", "params": {"size": 1}, "location": [0, 3.2, 2.0], "scale": [9, 0.3, 4],
                             "material": "brick"},
                    table("table", 0, 0.9, 0, 2.6), crate("crate", 2.1, 2.2, 0, 1.4, 12),
                    *_figure("speaker_a", -0.95, 0.85, "coat"), *_figure("speaker_b", 0.95, 0.95, "cloak")],
        "camera": {"location": [-1.0, -3.4, 1.5], "look_at": [0.15, 0.9, 1.05], "lens_mm": 40, "focus_distance_m": 4.5},
    }
    # 2 battle wide: two lines and their cannons on a field
    battle = [{"name": "field", "add": "plane", "params": {"size": 160}, "material": "grass"}]
    for i in range(9):
        battle += _figure(f"a{i}", -7 + i * 1.3, -3.0 + (i % 2) * 0.5, "side_a")
        battle += _figure(f"b{i}", -7.5 + i * 1.4, 7.0 - (i % 2) * 0.5, "side_b")
    battle += [cannon("cannon_a1", -4.5, -5.0, 0), cannon("cannon_a2", 3.5, -5.2, 0), cannon("cannon_b1", -1.0, 9.5, 180),
               {"name": "ridge", "add": "uv_sphere", "params": {"radius": 1, "segments": 48, "ring_count": 24},
                "location": [0, 40, -6], "scale": [60, 14, 12], "material": "hill", "smooth": True}]
    out["battle_wide"] = {"objects": battle,
                          "camera": {"location": [6.5, -13.5, 4.2], "look_at": [-1.0, 2.5, 0.9], "lens_mm": 32, "focus_distance_m": 17.0}}
    # 3 travel: a road receding to hills, a loaded cart, two walkers
    travel = [{"name": "field", "add": "plane", "params": {"size": 200}, "material": "grass"},
              {"name": "road", "add": "plane", "params": {"size": 1}, "location": [0, 30, 0.01], "scale": [3.2, 80, 1], "material": "ground"},
              {"name": "cart", "add": "cube", "params": {"size": 1}, "location": [0.4, 4.0, 0.75], "scale": [1.6, 2.6, 0.5], "material": "table"},
              {"name": "wheel_l", "add": "cylinder", "params": {"radius": 0.5, "depth": 0.12, "vertices": 24}, "location": [-0.48, 4.0, 0.5],
               "rotation_deg": [0, 90, 0], "material": "night"},
              {"name": "wheel_r", "add": "cylinder", "params": {"radius": 0.5, "depth": 0.12, "vertices": 24}, "location": [1.28, 4.0, 0.5],
               "rotation_deg": [0, 90, 0], "material": "night"},
              crate("load_1", 0.3, 3.6, 1.0, 1.3, 5), crate("load_2", 0.5, 4.6, 1.0, 1.2, -8),
              *_figure("walker_a", -0.9, 1.6, "coat"), *_figure("walker_b", 1.6, 6.2, "cloak")]
    for i, (x, y, r) in enumerate(((-26, 70, 18), (14, 80, 24), (40, 66, 16), (-50, 60, 14))):
        travel.append({"name": f"hill{i}", "add": "uv_sphere", "params": {"radius": 1, "segments": 48, "ring_count": 24},
                       "location": [x, y, -r * 0.55], "scale": [r, r, r * 0.8], "material": "hill", "smooth": True})
    out["travel"] = {"objects": travel,
                     "camera": {"location": [-2.6, -5.5, 1.7], "look_at": [0.6, 8.0, 1.3], "lens_mm": 35, "focus_distance_m": 10.0}}
    # 4 establishing: a walled town above the road
    town = [{"name": "field", "add": "plane", "params": {"size": 300}, "material": "grass"},
            {"name": "road", "add": "plane", "params": {"size": 1}, "location": [0, 6, 0.01], "scale": [4, 40, 1], "material": "ground"}]
    for i, (x, y, w, d, h) in enumerate(((-9, 24, 5, 4, 4), (-3, 27, 4, 5, 5), (4, 25, 6, 4, 4), (10, 28, 4, 4, 6), (-6, 33, 5, 5, 5),
                                         (2, 34, 4, 6, 7), (9, 36, 5, 4, 5))):
        town += _house(f"house{i}", x, y, w, d, h)
    town += [{"name": "tower", "add": "cylinder", "params": {"radius": 2.2, "depth": 14, "vertices": 24}, "location": [-1, 40, 7],
              "material": "stone"},
             {"name": "tower_roof", "add": "cone", "params": {"radius1": 2.8, "depth": 4.5, "vertices": 24}, "location": [-1, 40, 16.2],
              "material": "roof"},
             {"name": "wall_front", "add": "cube", "params": {"size": 1}, "location": [-12, 19, 2.5], "scale": [14, 1.2, 5], "material": "stone"},
             {"name": "wall_front_b", "add": "cube", "params": {"size": 1}, "location": [12, 19, 2.5], "scale": [14, 1.2, 5], "material": "stone"},
             {"name": "gate_l", "add": "cylinder", "params": {"radius": 1.6, "depth": 8, "vertices": 16}, "location": [-4, 19, 4], "material": "stone"},
             {"name": "gate_r", "add": "cylinder", "params": {"radius": 1.6, "depth": 8, "vertices": 16}, "location": [4, 19, 4], "material": "stone"},
             crate("road_crate", 1.0, 8.0, 0, 1.6, 20), *_figure("traveller", -0.8, 9.0, "coat")]
    out["establishing"] = {"objects": town,
                           "camera": {"location": [7.0, -12.0, 9.0], "look_at": [0, 26, 4], "lens_mm": 32, "focus_distance_m": 38.0}}
    # 5 map-adjacent tableau: a war table from above, pieces on the map sheet, two figures leaning in
    pieces = []
    for i, (x, y) in enumerate(((-0.55, 0.65), (-0.25, 0.85), (0.1, 0.62), (0.45, 0.8))):
        pieces.append({"name": f"piece_a{i}", "add": "cube", "params": {"size": 0.09}, "location": [x, y, 1.12], "material": "side_a"})
    for i, (x, y) in enumerate(((-0.4, 1.25), (0.05, 1.3), (0.5, 1.2))):
        pieces.append({"name": f"piece_b{i}", "add": "cone", "params": {"radius1": 0.06, "depth": 0.14, "vertices": 3},
                       "location": [x, y, 1.14], "material": "side_b"})
    out["map_tableau"] = {
        "objects": [ground, table("table", 0, 1.0, 0, 2.6, 90),
                    {"name": "map", "add": "plane", "params": {"size": 1}, "location": [0, 0.98, 1.095], "scale": [1.5, 1.0, 1],
                     "material": "map"},
                    {"name": "river", "add": "cube", "params": {"size": 1}, "location": [0.05, 0.98, 1.098], "scale": [0.05, 0.9, 0.004],
                     "rotation_deg": [0, 0, 18], "material": "coat"},
                    *pieces, *_figure("general_a", -1.1, 0.3, "coat"), *_figure("general_b", 1.15, 1.7, "cloak")],
        "camera": {"location": [0.4, -1.4, 3.1], "look_at": [0.0, 0.98, 1.05], "lens_mm": 40, "focus_distance_m": 3.2},
    }
    for sid, sc in out.items():
        used = {o["material"] for o in sc["objects"] if o.get("material")}
        sc["materials"] = {k: v for k, v in mats.items() if k in used}
    return out


def style_for(variant_id: str) -> tuple[str, S.StyleTokens]:
    if variant_id == "S":
        return "cycles_safe", S.variant("B")
    if variant_id in CLIP_VARIANTS:
        base, over, _ = CLIP_VARIANTS[variant_id]
        return "eevee", replace(S.variant(base), **over)
    return "eevee", S.variant(variant_id)


def motion(scene_id: str, sc: dict, frames: int = CLIP_FRAMES) -> dict:
    """The round-2 clip of a scene: the same set with a ``to`` block on what moves (render_shot.build_described keys it)."""
    sc = json.loads(json.dumps(sc))
    sc["frames_total"] = frames
    if scene_id == "dialogue_cu":      # a slow push in on the two speakers (ease in and out)
        sc["camera"]["to"] = {"location": [-0.62, -2.15, 1.4], "look_at": [0.1, 0.9, 1.08]}
    elif scene_id == "battle_wide":    # the near line advances 1.6 m while the camera dollies left
        for o in sc["objects"]:
            if o["name"].startswith("a") and o["name"][1:2].isdigit():
                x, y, z = o["location"]
                o["to"] = {"location": [x, y + 1.6, z]}
                o["interp"] = "LINEAR"
        sc["camera"]["to"] = {"location": [3.2, -13.2, 4.0], "look_at": [-1.6, 3.0, 0.9]}
    else:
        raise ValueError(f"{scene_id} has no clip motion (clips: {', '.join(CLIP_SCENES)})")
    return sc


def scene_sha256(scene: dict) -> str:
    """The described scene (objects, camera, style graph) as the shot's template: its hash, with the local cache paths made
    repo-relative so two machines get the same key. shot_spec/2 has no field for a described scene (proposed to ICW-07): the
    template asset ref carries its hash so the cache key changes whenever the scene or the look does."""
    root = str(L.REPO.resolve()) + "/"
    text = json.dumps(scene, sort_keys=True, separators=(",", ":")).replace(root, "")
    return hashlib.sha256(text.encode()).hexdigest()


def spec_for(scene_id: str, variant_id: str, tokens: S.StyleTokens, *, samples: int = 16, scene: dict | None = None,
             frames: int = 1) -> dict:
    """A shot_spec/2 of the master: one frame = a STILL_3D sheet; ``frames`` > 1 = a VIDEO_3D clip (round 2), its camera rig named
    from the scene's motion. Asset refs carry the registered sha256s."""
    lib = L.load()
    ref = lambda i: {"id": i, "sha256": L.get(i, lib=lib)["sha256"]}  # noqa: E731
    path, _ = style_for(variant_id)
    profile = "cycles_hero" if path == "cycles_safe" else "eevee_fast"
    spec = {
        "schema": "shot_spec/2", "job_id": JOB_ID, "shot_id": f"{scene_id}_{variant_id}", "lane": "STILL_3D" if frames == 1 else "VIDEO_3D",
        "recipe": "blender_cycles/1" if profile == "cycles_hero" else "blender_eevee/1",
        "clock": {"fps": 24, "frames": frames, "start_frame": 0},
        "frame": {"width": S.MASTER_W, "height": S.MASTER_H, "render_scale": 1.0},
        "scene": {"template_asset": {"id": f"scene_template.style_{'sheet' if frames == 1 else 'clip'}_{scene_id}",
                                     "sha256": scene_sha256(scene) if scene is not None else "0" * 64},
                  "era": "style_sheet",
                  "set_assets": [ref(a["id"]) for a in sources() if a["kind"] in ("model", "material", "hdri")],
                  "characters": [],
                  "camera": {"rig": "static", "start": {"pos": [0, 0, 0], "yaw_deg": 0, "pitch_deg": 0},
                             "end": {"pos": [0, 0, 0], "yaw_deg": 0, "pitch_deg": 0}, "lens_mm": 35, "ease": "linear"},
                  "light_rig": "ink_key_sun", "weather": None, "props": []},
        "performance": {"lipsync": False, "rhubarb": None, "mouth_shapes": 8, "dialogue_cover": None},
        "look": {"bible_version": "1.5", "line_weight_px": tokens.line_px, "crease_deg": tokens.crease_deg,
                 "shading_steps": tokens.steps, "view_transform": tokens.view_transform, "grade_look": tokens.look,
                 "paper": {"asset": ref("texture.acg_paper003"), "opacity": tokens.paper_opacity}},
        "render": {"profile": profile, "samples": samples, "motion_blur": False, "denoise": False, "output": "png_seq"},
        "seed": 1,
    }
    if frames > 1:
        spec["scene"]["camera"]["rig"] = {"dialogue_cu": "push", "battle_wide": "dolly"}.get(scene_id, "dolly")
        spec["scene"]["camera"]["ease"] = "ease_in_out"
    if profile == "cycles_hero":
        spec["why"] = "ICW-05 style sheet: the Cycles-safe variant beside the EEVEE look (roadmap 9.1), never an episode shot"
    return spec


def job_scene(scene_id: str, variant_id: str, sc: dict, paths: dict[str, Path]) -> tuple[dict, dict]:
    path, tokens = style_for(variant_id)
    graph = S.StyleEngine(tokens).graph(path, camera=sc["camera"], materials=sc["materials"],
                                        hdri=str(paths["hdri.ph_kloofendal_48d_partly_cloudy_puresky"]),
                                        paper_texture=str(paths["texture.acg_paper003"]))
    problems = S.check(graph)
    if problems:
        raise ValueError(f"{scene_id}/{variant_id}: style graph problems: {problems}")
    scene = {"kind": "described", "objects": sc["objects"], "camera": sc["camera"], "style": graph}
    if sc.get("frames_total", 1) > 1:
        scene["frames_total"] = sc["frames_total"]
    return scene, graph


def render(out: Path, *, binary: str | None = None, scene_ids=SCENE_IDS, variant_ids=VARIANT_IDS, samples: int = 16,
           scale: float = 1.0, log=print) -> list[dict]:
    """Every scene x variant through HeadlessRender; frames go to a LocalVault under ``out``. ``scale`` < 1 renders a smaller
    test frame (the shot spec stays the 1440p master; the row is then marked ``scaled`` and never shown as a sheet)."""
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    out = Path(out)
    paths = fetch()
    scs = scenes(paths)
    b = BlenderProject().resolve(binary)
    vault = R.LocalVault(out / "vault")
    rows = []
    for sid in scene_ids:
        for vid in variant_ids:
            _, tokens = style_for(vid)
            scene, graph = job_scene(sid, vid, scs[sid], paths)
            spec = spec_for(sid, vid, tokens, samples=samples, scene=scene)
            if scale != 1.0:
                spec["frame"]["render_scale"] = scale
            t0 = time.time()
            try:
                m = R.HeadlessRender(b, vault).run(spec, out / "work", scene=scene)
            except ContractError as e:
                # a scaled test frame is refused by CN-17 (not the master) AFTER its frame is committed: keep it as a test row
                if scale == 1.0 or "master" not in str(e):
                    raise
                key = shot_cache.key(spec)
                m = dict(json.loads((out / "work" / key / "render_manifest.json").read_text(encoding="utf-8")),
                         _findings=[{"rule": "CN-17", "severity": "FAIL", "detail": str(e)}])
            sdir = out / "work" / m["cache_key"]
            rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
            row = {"scene": sid, "variant": vid, "label": S.VARIANTS.get(vid if vid != "S" else "B", {}).get("label", ""),
                   "path": graph["path"], "frame": str(sdir / "frames" / R.FRAME_NAME.format(index=0)),
                   "engine": m["engine"], "seconds_per_frame": m["seconds_per_frame"], "wall_seconds": round(time.time() - t0, 2),
                   "blender": m["blender"], "style_sha256": graph["sha256"], "line_art": graph["line_art"],
                   "applied": rep.get("style", {}).get("applied"), "appended": rep.get("appended"),
                   "gpu_backend": rep.get("gpu_backend"), "scaled": scale != 1.0,
                   "findings": [f for f in m["_findings"] if f["severity"] == "FAIL" and not (scale != 1.0 and f["rule"] == "CN-17")]}
            rows.append(row)
            log(f"{sid}/{vid}: {row['seconds_per_frame']} s/frame ({row['engine']}, {row['path']})")
            write_json_atomic(out / "style_sheets.json", {"schema": "style_sheets/1", "job_id": JOB_ID, "rows": rows})
    return rows


def frame_times(sdir: Path) -> dict:
    """Seconds per frame of a rendered clip: the first frame (it carries the shader compile) and the steady rest apart."""
    times = {int(k): float(v) for k, v in json.loads((Path(sdir) / "render_times.json").read_text(encoding="utf-8")).items()}
    ordered = [times[i] for i in sorted(times)]
    rest = sorted(ordered[1:])
    return {"first_s": round(ordered[0], 3) if ordered else None,
            "steady_median_s": round(rest[len(rest) // 2], 3) if rest else None,
            "mean_s": round(sum(ordered) / len(ordered), 3) if ordered else None, "frames": len(ordered)}


def mp4(frames_dir: Path, dest: Path, *, fps: int = 24, run=None) -> dict:
    """An H.264 review copy of a committed clip (yuv420p, CRF 16: for watching, never the master). None without ffmpeg."""
    import shutil
    import subprocess
    run = run or subprocess.run
    if shutil.which("ffmpeg") is None and run is subprocess.run:
        return {"path": None, "why": "ffmpeg is not installed (brew install ffmpeg); the PNG frames are the clip"}
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".part.mp4")
    cmd = ["ffmpeg", "-nostdin", "-y", "-loglevel", "error", "-framerate", str(fps), "-start_number", "0",
           "-i", str(Path(frames_dir) / "frame_%06d.png"), "-c:v", "libx264", "-preset", "slow", "-crf", "16",
           "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    p = run(cmd, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError(f"ffmpeg could not make {dest.name}: {(p.stderr or '').strip()[:300]}")
    tmp.replace(dest)
    return {"path": str(dest), "sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}


def clips(out: Path, *, binary: str | None = None, scene_ids=CLIP_SCENES, variant_ids=tuple(CLIP_VARIANTS),
          frames: int = CLIP_FRAMES, samples: int = 16, scale: float = 1.0, log=print) -> list[dict]:
    """Round 2: every clip scene x clip variant as a ``frames``-long VIDEO_3D shot through HeadlessRender, an MP4 review copy
    each, and ``out/style_clips.json`` (rows written as they finish, so a stop keeps what is done)."""
    from explainer_engine.blender import render as R
    from explainer_engine.blender.project import BlenderProject
    out = Path(out)
    paths = fetch()
    base = scenes(paths)
    b = BlenderProject().resolve(binary)
    vault = R.LocalVault(out / "vault")
    rows = []
    for sid in scene_ids:
        sc = motion(sid, base[sid], frames)
        for vid in variant_ids:
            _, tokens = style_for(vid)
            scene, graph = job_scene(sid, vid, sc, paths)
            spec = spec_for(sid, vid, tokens, samples=samples, scene=scene, frames=frames)
            if scale != 1.0:
                spec["frame"]["render_scale"] = scale
            t0 = time.time()
            try:
                m = R.HeadlessRender(b, vault).run(spec, out / "work", scene=scene)
            except ContractError as e:
                if scale == 1.0 or "master" not in str(e):
                    raise
                m = dict(json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8")),
                         _findings=[])
            sdir = out / "work" / m["cache_key"]
            rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
            row = {"scene": sid, "variant": vid, "label": CLIP_VARIANTS[vid][2], "tokens": tokens.to_dict(),
                   "frames_dir": str(sdir / "frames"), "frame": str(sdir / "frames" / R.FRAME_NAME.format(index=0)),
                   "engine": m["engine"], "seconds_per_frame": m["seconds_per_frame"], "times": frame_times(sdir),
                   "wall_seconds": round(time.time() - t0, 2), "blender": m["blender"], "gpu_backend": rep.get("gpu_backend"),
                   "device": m.get("device"), "motion": rep.get("motion"), "applied": rep.get("style", {}).get("applied"),
                   "style_sha256": graph["sha256"], "scaled": scale != 1.0,
                   "mp4": mp4(sdir / "frames", out / "clips" / f"{sid}_{vid}.mp4"),
                   "findings": [f for f in m["_findings"] if f["severity"] == "FAIL"]}
            rows.append(row)
            log(f"{sid}/{vid}: {row['times']['steady_median_s']} s/frame steady, first {row['times']['first_s']} s "
                f"({row['engine']}, {row['gpu_backend']})")
            write_json_atomic(out / "style_clips.json", {"schema": "style_clips/1", "job_id": JOB_ID, "frames": frames, "rows": rows})
    return rows


def _grid(rows, variants, scene_ids, label, path: Path, *, cell_w: int) -> Path:
    from PIL import Image, ImageDraw, ImageFont
    cell_h = cell_w * 9 // 16
    head, side, pad = 70, 360, 12
    W, H = side + len(scene_ids) * (cell_w + pad) + pad, head + len(variants) * (cell_h + pad) + pad
    pal = S.palette()
    sheet = Image.new("RGB", (W, H), pal["paper"])
    d = ImageDraw.Draw(sheet)
    try:
        font, small, big = (ImageFont.truetype("DejaVuSans.ttf", n) for n in (30, 22, 80))
    except OSError:
        font = small = big = ImageFont.load_default()
    for j, sid in enumerate(scene_ids):
        d.text((side + pad + j * (cell_w + pad), 20), LABELS[sid], fill=pal["ink"], font=font)
    for i, vid in enumerate(variants):
        y = head + pad + i * (cell_h + pad)
        title, text = label(vid)
        d.text((pad, y + 10), title, fill=pal["ink"], font=big)
        d.multiline_text((pad, y + 110), text, fill=pal["ink"], font=small, spacing=6)
        for j, sid in enumerate(scene_ids):
            r = next((r for r in rows if r["scene"] == sid and r["variant"] == vid), None)
            x = side + pad + j * (cell_w + pad)
            if r is None:
                d.rectangle([x, y, x + cell_w, y + cell_h], outline=pal["grey_mid"], width=2)
                continue
            with Image.open(r["frame"]) as im:
                sheet.paste(im.convert("RGB").resize((cell_w, cell_h), Image.Resampling.LANCZOS), (x, y))
    sheet.save(path, optimize=True)
    sheet.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(path.with_name(path.stem + "_preview.jpg"), quality=88)
    return path


def clip_collage(out: Path, *, cell_w: int = 960) -> Path:
    """First frames of the clips: a row per clip variant (with its steady seconds per frame), a column per scene."""
    out = Path(out)
    rows = json.loads((out / "style_clips.json").read_text(encoding="utf-8"))["rows"]
    variants = [v for v in CLIP_VARIANTS if any(r["variant"] == v for r in rows)]
    scene_ids = [s for s in CLIP_SCENES if any(r["scene"] == s for r in rows)]

    def label(vid):
        t = style_for(vid)[1]
        secs = [r["times"]["steady_median_s"] for r in rows if r["variant"] == vid and r["times"]["steady_median_s"]]
        lines = CLIP_VARIANTS[vid][2].replace(": ", ":\n").replace(", ", ",\n").split("\n")
        lines += [f"line {t.line_px:g} px", f"shadows {'on' if t.shadows else 'off'}",
                  f"palette {'matched' if t.palette_match else 'raw hex'}"]
        if secs:
            lines.append(f"{max(secs):.1f} s/frame max")
        return str(list(CLIP_VARIANTS).index(vid) + 1), "\n".join(lines)
    return _grid(rows, variants, scene_ids, label, out / "clips_collage.png", cell_w=cell_w)


def collage(out: Path, *, cell_w: int = 960) -> Path:
    """One collage of the sheets: a row per variant, a column per scene, labelled (what the creator picks from)."""
    from PIL import Image, ImageDraw, ImageFont
    out = Path(out)
    doc = json.loads((out / "style_sheets.json").read_text(encoding="utf-8"))
    rows = [r for r in doc["rows"] if not r["scaled"]] or doc["rows"]
    variants = [v for v in VARIANT_IDS if any(r["variant"] == v for r in rows)]
    scene_ids = [s for s in SCENE_IDS if any(r["scene"] == s for r in rows)]
    cell_h = cell_w * 9 // 16
    head, side, pad = 70, 360, 12
    W, H = side + len(scene_ids) * (cell_w + pad) + pad, head + len(variants) * (cell_h + pad) + pad
    pal = S.palette()
    sheet = Image.new("RGB", (W, H), pal["paper"])
    d = ImageDraw.Draw(sheet)
    try:
        font, small, big = (ImageFont.truetype("DejaVuSans.ttf", n) for n in (30, 22, 80))
    except OSError:
        font = small = big = ImageFont.load_default()
    for j, sid in enumerate(scene_ids):
        d.text((side + pad + j * (cell_w + pad), 20), LABELS[sid], fill=pal["ink"], font=font)
    for i, vid in enumerate(variants):
        y = head + pad + i * (cell_h + pad)
        lab = S.VARIANTS[vid]["label"] if vid in S.VARIANTS else "S  Cycles-safe (B), reference only"
        tokens = style_for(vid)[1]
        d.text((pad, y + 10), lab.split("  ")[0], fill=pal["ink"], font=big)
        d.multiline_text((pad, y + 110), lab.split("  ", 1)[1].replace(", ", ",\n") + f"\nline {tokens.line_px:g} px\nshade {tokens.tones[0]:g}/"
                         f"{tokens.tones[1]:g}/1\nrim {tokens.rim_strength:g}", fill=pal["ink"], font=small, spacing=6)
        for j, sid in enumerate(scene_ids):
            r = next((r for r in rows if r["scene"] == sid and r["variant"] == vid), None)
            x = side + pad + j * (cell_w + pad)
            if r is None:
                d.rectangle([x, y, x + cell_w, y + cell_h], outline=pal["grey_mid"], width=2)
                continue
            with Image.open(r["frame"]) as im:
                sheet.paste(im.convert("RGB").resize((cell_w, cell_h), Image.Resampling.LANCZOS), (x, y))
    path = out / "collage.png"
    sheet.save(path, optimize=True)
    sheet.resize((W // 2, H // 2), Image.Resampling.LANCZOS).save(out / "collage_preview.jpg", quality=88)
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.style_sheets", description=__doc__.split("\n\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    r.add_argument("--downloads", required=True)
    sub.add_parser("fetch")
    rd = sub.add_parser("render")
    rd.add_argument("--out", required=True)
    rd.add_argument("--binary", default=None)
    rd.add_argument("--scenes", default=",".join(SCENE_IDS))
    rd.add_argument("--variants", default=",".join(VARIANT_IDS))
    rd.add_argument("--samples", type=int, default=16)
    rd.add_argument("--scale", type=float, default=1.0)
    c = sub.add_parser("collage")
    c.add_argument("--out", required=True)
    cl = sub.add_parser("clips")
    cl.add_argument("--out", required=True)
    cl.add_argument("--binary", default=None)
    cl.add_argument("--scenes", default=",".join(CLIP_SCENES))
    cl.add_argument("--variants", default=",".join(CLIP_VARIANTS))
    cl.add_argument("--frames", type=int, default=CLIP_FRAMES)
    cl.add_argument("--scale", type=float, default=1.0)
    a = ap.parse_args(argv)
    if a.cmd == "register":
        for rec in register(Path(a.downloads)):
            print(f"registered {rec['id']} ({rec['bytes']} bytes, {rec['storage']['external_path']})")
        return 0
    if a.cmd == "fetch":
        for k, v in fetch().items():
            print(f"{k}: {v}")
        return 0
    if a.cmd == "render":
        render(Path(a.out), binary=a.binary, scene_ids=a.scenes.split(","), variant_ids=a.variants.split(","), samples=a.samples,
               scale=a.scale)
        return 0
    if a.cmd == "clips":
        clips(Path(a.out), binary=a.binary, scene_ids=a.scenes.split(","), variant_ids=a.variants.split(","), frames=a.frames,
              scale=a.scale)
        print(clip_collage(Path(a.out)))
        return 0
    print(collage(Path(a.out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
