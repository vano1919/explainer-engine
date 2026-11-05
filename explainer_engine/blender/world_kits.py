"""World kits for the Blender lanes (WP-Q8; synthesis of existing free libraries, ours is the glue): a real mid-ground and real props.

Three existing parts, nothing modelled here:

* the **Quaternius Medieval Village MegaKit** (Standard, free, CC0 from the itch.io page; walls, floors, roofs, doors, props on a
  2 m module), fetched with ``assets/itch.py``;
* **Poly Haven** CC0 models (a fort, a castle door, barrels, crates, a lantern, a cabinet), fetched with ``polyhaven.py`` (the
  search/download/side-file code of Blender-MCP, MIT);
* the repository's own ``characters.pack_glb`` packer, which turns a glTF + its .bin + its images into one self-contained GLB.

Every piece is packed with only the **base-colour image**, scaled to ``max_texture_px``: ``style.py`` replaces every material with a
toon material that keeps a photo texture only as a trace over a palette tone (D-102), so normal, roughness and ORM maps (3-4 MB
each in the MegaKit) would be dead weight. The piece is registered as an external ``model`` record of ``assets/library.json``
(``tools/assets_cache/<sha256>/``, vault copy under ``assets/3d/model/<id>/``) with the licence row of its source, the pack page and
version, and the extent of its geometry; ``fetch`` rebuilds a missing file from the vault, else from the source (the pack zip's
sha256 or the Poly Haven URLs and md5s recorded in ``world_kits.json``). Nothing here is paid.

A **layout** (``world_layouts.json``) places pieces without a modeller: ``ring`` (a wall ring of modules with named replacements and
corner posts), ``floor`` (tiles), ``row`` (a street: one piece repeated along a line) and ``piece`` (one explicit placement).
``expand`` turns a layout into the ``described`` scene objects of ``bpy/render_shot.py`` (``{"gltf": {"path": ...}, ...}``, every
material a ``style.py`` toon material, so ``style.check`` sees no raw PBR) and ``scene_set`` into the ``scene_set/1`` geography the
continuity code reads (x right, z forward, y up; Blender's y and z swapped). One castle courtyard layout is reused by any number of
shots: the same ids, positions and hashes, so the cache key follows the layout and the look only.

    python -m explainer_engine.blender.world_kits register --downloads D [--polyhaven-dir P]   # pack + register (needs the pack zip)
    python -m explainer_engine.blender.world_kits fetch                                         # registered files into tools/assets_cache
    python -m explainer_engine.blender.world_kits layout castle_courtyard                       # the expanded objects and scene_set as JSON
    python -m explainer_engine.blender.world_kits list
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import math
import sys
import urllib.parse
import zipfile
from pathlib import Path

from explainer_engine.assets import library as L
from explainer_engine.blender import characters as C
from explainer_engine.blender import polyhaven as PH
from explainer_engine.core.errors import ContractError

HERE = Path(__file__).resolve().parent
KITS = HERE / "world_kits.json"
LAYOUTS = HERE / "world_layouts.json"


class WorldKitError(ContractError):
    pass


def table(path: Path | None = None) -> dict:
    doc = json.loads(Path(path or KITS).read_text(encoding="utf-8"))
    if doc.get("schema") != "world_kits/1":
        raise WorldKitError(f"{path or KITS}: not a world_kits/1 table")
    return doc


def layouts(path: Path | None = None) -> dict:
    doc = json.loads(Path(path or LAYOUTS).read_text(encoding="utf-8"))
    if doc.get("schema") != "world_layout/1":
        raise WorldKitError(f"{path or LAYOUTS}: not a world_layout/1 file")
    return doc


# --- packing -----------------------------------------------------------------------------------------------------------------------

def base_colour_uris(gltf: dict) -> set[str]:
    """The image uris some material uses as its base colour (the only maps ``style.py`` reads)."""
    out = set()
    for m in gltf.get("materials", []):
        ref = (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")
        if ref is not None:
            src = gltf["textures"][ref["index"]].get("source")
            if src is not None and "uri" in gltf["images"][src]:
                out.add(gltf["images"][src]["uri"])
    return out


def shrink(data: bytes, uri: str, max_px: int) -> bytes:
    """The image scaled so its longer side is at most ``max_px`` (Lanczos), same container as its uri says (PNG or JPEG q88);
    an image already small enough is returned untouched. Deterministic for one Pillow version."""
    from PIL import Image
    im = Image.open(io.BytesIO(data))
    if max(im.size) <= max_px:
        return data
    im.load()
    scale = max_px / max(im.size)
    im = im.convert("RGB" if uri.lower().endswith((".jpg", ".jpeg")) or im.mode not in ("RGBA", "LA") else "RGBA")
    im = im.resize((max(1, round(im.size[0] * scale)), max(1, round(im.size[1] * scale))), Image.LANCZOS)
    buf = io.BytesIO()
    if uri.lower().endswith(".png"):
        im.save(buf, "PNG", optimize=False, compress_level=6)
    else:
        im.save(buf, "JPEG", quality=88, optimize=False, progressive=False)
    return buf.getvalue()


def pack_piece(gltf: dict, read, max_px: int) -> tuple[bytes, dict]:
    """A glTF and ``read(uri)`` -> a self-contained GLB with only the base-colour images, shrunk to ``max_px``."""
    keep = base_colour_uris(gltf)

    images = {im["uri"] for im in gltf.get("images", []) if "uri" in im}

    def only_base(uri: str):
        if uri not in images:
            return read(uri)   # a buffer
        if uri not in keep:
            return None   # pack_glb drops the image, its texture and the slots that used it
        data = read(uri)
        return None if data is None else shrink(data, uri, max_px)

    data, rep = C.pack_glb(gltf, only_base)
    rep["dropped_images"] = sorted(set(rep["dropped_images"]))
    return data, rep


def pack_pack_member(zip_path: Path, member: str, max_px: int) -> tuple[bytes, dict]:
    with zipfile.ZipFile(zip_path) as zf:
        gltf = json.loads(zf.read(member).decode("utf-8"))
        return pack_piece(gltf, C._zip_reader(zf, member), max_px)


def pack_polyhaven_dir(main: Path, max_px: int) -> tuple[bytes, dict]:
    """A downloaded Poly Haven glTF (``main`` and its ``textures/`` and .bin side files) as one GLB."""
    gltf = json.loads(Path(main).read_text(encoding="utf-8"))
    base = Path(main).parent

    def read(uri: str):
        p = base / urllib.parse.unquote(uri)
        return p.read_bytes() if p.is_file() else None
    return pack_piece(gltf, read, max_px)


PACKER = "world_kits.pack_piece/1"


def fingerprint(data: bytes) -> dict:
    """The structure of a packed GLB (glTF JSON chunk only): node, mesh, primitive and image counts. Image re-encoding differs
    byte-wise between platforms and Pillow builds; the structure does not."""
    doc, _ = C.read_glb(data)
    return {"nodes": len(doc.get("nodes", [])), "meshes": len(doc.get("meshes", [])),
            "primitives": sum(len(m["primitives"]) for m in doc.get("meshes", [])), "images": len(doc.get("images", []))}


def source_sha256(a: dict, t: dict) -> str:
    """The hash of what a piece is built from: the pack zip's sha256, or for a Poly Haven piece the sha256 of its recorded file md5s."""
    if a["source"] == "polyhaven":
        return hashlib.sha256(json.dumps(t["polyhaven"][a["slug"]]["files_md5"], sort_keys=True).encode()).hexdigest()
    return t["packs"][a["source"]]["sha256"]


def annotate(t: dict, paths: dict[str, Path]) -> dict:
    """Mark every piece derived (a repack is a build, not the registered artefact) with its source hash, packer id and the
    fingerprint of the registered GLB. Called by ``register`` and, once, for pieces registered before this rule."""
    for a in t["assets"]:
        if a["id"] in paths:
            a.update({"derived": True, "packer": PACKER, "source_sha256": source_sha256(a, t),
                      "fingerprint": fingerprint(Path(paths[a["id"]]).read_bytes())})
    return t


def glb_extent(data: bytes) -> list[float]:
    """[width x, depth y, height z] in metres of the packed mesh in Blender's frame (glTF is Y-up: x, -z, y), from the POSITION
    accessors' min/max, nodes' own transforms ignored (a kit piece is one untransformed node)."""
    doc, _ = C.read_glb(data)
    lo, hi = [math.inf] * 3, [-math.inf] * 3
    for m in doc.get("meshes", []):
        for p in m["primitives"]:
            a = doc["accessors"][p["attributes"]["POSITION"]]
            lo = [min(x, y) for x, y in zip(lo, a["min"])]
            hi = [max(x, y) for x, y in zip(hi, a["max"])]
    if lo[0] == math.inf:
        raise WorldKitError("a piece without a mesh")
    return [round(hi[0] - lo[0], 3), round(hi[2] - lo[2], 3), round(hi[1] - lo[1], 3)]


# --- register / fetch --------------------------------------------------------------------------------------------------------------

def _source_files(t: dict, a: dict, downloads: Path, polyhaven_dir: Path | None) -> tuple[bytes, dict]:
    mp = t["max_texture_px"]
    if a["source"] == "polyhaven":
        d = Path(polyhaven_dir or downloads / "polyhaven") / a["slug"]
        return pack_polyhaven_dir(d / f"{a['slug']}_{t['polyhaven'][a['slug']]['resolution']}.gltf", mp)
    pack = t["packs"][a["source"]]
    z = C.pack_path(pack, downloads)
    if L.sha256_file(z) != pack["sha256"]:
        raise WorldKitError(f"{a['source']}: {z} is not the registered pack (sha256 differs)")
    return pack_pack_member(z, a["member"], mp)


def register(downloads: Path, *, polyhaven_dir: Path | None = None, path: Path | None = None, repo: Path | None = None,
             t: dict | None = None, update_table: bool = True, only: set[str] | None = None) -> list[dict]:
    """Pack every piece of ``world_kits.json`` and register it as an external ``model`` record; the packed file's sha256 goes back
    into the table (``update_table``) so ``fetch`` can check a rebuild. Licence block from the source row + page + version."""
    from explainer_engine.world import bible as B
    t = t or table()
    bv = B.cite()["version"]
    work = Path(repo or L.REPO) / L.CACHE / "packing"
    work.mkdir(parents=True, exist_ok=True)
    out = []
    for a in t["assets"]:
        if only and a["id"] not in only:
            continue
        data, rep = _source_files(t, a, Path(downloads), polyhaven_dir)
        summ = C.glb_summary(data)
        f = work / a["name"]
        f.write_bytes(data)
        if a["source"] == "polyhaven":
            src = t["polyhaven"][a["slug"]]
            src_line = f"import polyhaven {PH.asset_url(a['slug'])} :: {a['slug']} {src['resolution']} gltf"
            licence = L.licence_from_source("polyhaven", url=PH.asset_url(a["slug"]),
                                            version=f"{a['slug']} {src['resolution']} gltf, downloaded {t['downloaded_on']}")
            params = {"polyhaven_slug": a["slug"], "files_md5": src.get("files_md5"), "dropped_images": rep["dropped_images"]}
        else:
            pack = t["packs"][a["source"]]
            src_line = f"import {pack['source']} {pack['page']} :: {a['member']}"
            licence = L.licence_from_source(pack["source"], url=pack["page"], version=pack["version"])
            params = {"packed_from": a["member"], "pack_sha256": pack["sha256"], "dropped_images": rep["dropped_images"]}
        three_d = {"format": "glb", "poly_count": summ["triangles"], "materials": summ["materials"], "bounds_m": glb_extent(data)}
        rec, _ = L.ingest(f, a["id"], "model", path=path, repo=repo, replace=True, external=True, tags=a["tags"],
                          description=a["description"], bible_version=bv, three_d=three_d,
                          made_with={"provider": "third_party", "params": params}, source=src_line, licence=licence)
        f.unlink()
        a["sha256"] = rec["sha256"]
        a.update({"derived": True, "packer": PACKER, "source_sha256": source_sha256(a, t), "fingerprint": fingerprint(data)})
        out.append({"id": rec["id"], "sha256": rec["sha256"], "bytes": rec["bytes"], "triangles": summ["triangles"],
                    "extent_m": three_d["bounds_m"]})
    if update_table:
        KITS.write_text(json.dumps(t, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    return out


def _download_pack(pack: dict, pdir: Path) -> None:
    from explainer_engine.assets import itch
    done = itch.download(pack["page"], pdir, match=pack["match"])
    if not any(d["name"] == pack["file"] for d in done):
        raise WorldKitError(f"{pack['page']}: no file named {pack['file']} in the pack")


def _download_polyhaven(slug: str, src: dict, dest: Path) -> None:
    files = PH.api_get(f"files/{urllib.parse.quote(slug, safe='')}")
    got = PH.fetch_model_files(files, src["resolution"], "gltf", dest)
    if got is None:
        raise WorldKitError(f"{slug}: no {src['resolution']} glTF - {PH.available(files, 'models')}")


def _check_polyhaven_files(d: Path, src: dict) -> None:
    for rel, md5 in src["files_md5"].items():
        f = d / rel
        if not f.is_file() or hashlib.md5(f.read_bytes()).hexdigest() != md5:
            raise WorldKitError(f"{d.name}/{rel}: not the recorded Poly Haven file (md5); nothing kept")


def fetch(*, repo: Path | None = None, packs_dir: Path | None = None, t: dict | None = None, vault_first: bool = True,
          download_pack=None, download_polyhaven=None) -> dict[str, Path]:
    """Asset id -> the cached GLB at its registered sha256: the cache, else the vault, else rebuilt from the pack zip / the
    Poly Haven files (free). A rebuild is a derived build: its source hash and its structural fingerprint must match the registered ones (bytes may differ
    by platform, a derived rebuild is kept under ``derived/``); anything else is refused and nothing is kept."""
    repo = Path(repo or L.REPO)
    t = t or table()
    lib = L.load()
    got, missing = {}, []
    for a in t["assets"]:
        rec = L.get(a["id"], lib=lib)
        if a.get("sha256") and rec["sha256"] != a["sha256"]:
            raise WorldKitError(f"{a['id']}: world_kits.json and the library disagree on the sha256")
        have = L.cached(rec, repo=repo)
        if have is None and vault_first:
            try:
                have = L.fetch(a["id"], lib=lib, repo=repo)
            except Exception:  # noqa: BLE001  (no token / no network: the source is the fallback)
                have = None
        if have is None:
            missing.append((a, rec))
        else:
            got[a["id"]] = Path(have)
    if missing:
        pdir = Path(packs_dir or repo / L.CACHE / "packs")
        for key in sorted({a["source"] for a, _ in missing if a["source"] != "polyhaven"}):
            pack = t["packs"][key]
            z = C.pack_path(pack, pdir)
            if not z.exists() or L.sha256_file(z) != pack["sha256"]:
                (download_pack or _download_pack)(pack, pdir)
            if L.sha256_file(z) != pack["sha256"]:
                raise WorldKitError(f"{key}: the downloaded pack has another sha256; nothing kept")
        for a, rec in missing:
            if a["source"] == "polyhaven":
                src = t["polyhaven"][a["slug"]]
                d = pdir / "polyhaven" / a["slug"]
                if not (d / f"{a['slug']}_{src['resolution']}.gltf").exists():
                    (download_polyhaven or _download_polyhaven)(a["slug"], src, d)
                _check_polyhaven_files(d, src)
                data, _ = pack_polyhaven_dir(d / f"{a['slug']}_{src['resolution']}.gltf", t["max_texture_px"])
            else:
                data, _ = pack_pack_member(C.pack_path(t["packs"][a["source"]], pdir), a["member"], t["max_texture_px"])
            if hashlib.sha256(data).hexdigest() == rec["sha256"]:   # byte-identical to the registered build
                dest = repo / rec["file"]
            else:   # a derived build: the source hash was checked above, the structure must match the registered fingerprint
                if not a.get("derived") or fingerprint(data) != a.get("fingerprint"):
                    raise WorldKitError(f"{a['id']}: the rebuilt GLB differs from the registered file and its fingerprint "
                                        f"{fingerprint(data)} is not {a.get('fingerprint')}; nothing kept")
                dest = repo / L.CACHE / "derived" / source_sha256(a, t)[:16] / a["name"]
            dest.parent.mkdir(parents=True, exist_ok=True)
            tmp = dest.with_name(dest.name + ".part")
            tmp.write_bytes(data)
            tmp.replace(dest)
            got[a["id"]] = dest
    return got


# --- layouts -----------------------------------------------------------------------------------------------------------------------

def _yaw(side: str) -> float:
    """Yaw (deg, about +Z) that turns a Quaternius wall's front face (it looks to -Y at yaw 0) towards the ring's inside."""
    return {"north": 0.0, "south": 180.0, "west": 90.0, "east": -90.0}[side]


HOUSE_SIZES = {"small": (2, 2), "medium": (3, 2), "large": (4, 3)}   # wall modules (2 m each): 4x4 m, 6x4 m, 8x6 m
WALL_H = 3.0   # a plaster wall module is 3.125 m high; the roof sits on its top edge


def terrain_for(spec: dict):
    """The layout's ``Terrain`` (explainer_engine.blender.terrain) or None."""
    if not spec.get("terrain"):
        return None
    from explainer_engine.blender import terrain as TR
    return TR.Terrain(spec["terrain"])


def _house(block: dict, name: str, T) -> list[dict]:
    """One complete house of the kit: a wall ring (a door on the south side, windows on the others, corner posts), a roof scaled to
    the footprint with a small overhang and, on a large house, a chimney. ``size`` small/medium/large; ``yaw_deg`` turns the whole
    house about its centre; with ``terrain`` it stands on the ground (the lowest corner, a hand's breadth sunk)."""
    nx, ny = HOUSE_SIZES[block["size"]]
    m = 2.0
    hx, hy = nx * m / 2, ny * m / 2
    cx, cy = block["centre"]
    yaw = block.get("yaw_deg", 0.0)
    ca, sa = math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    rot = lambda x, y: (round(cx + x * ca - y * sa, 4), round(cy + x * sa + y * ca, 4))  # noqa: E731
    z0 = block.get("z", 0.0)
    if T is not None and block.get("terrain", True):
        z0 = min(T.height(*rot(sx * hx, sy * hy)) for sx in (-1, 0, 1) for sy in (-1, 0, 1)) - 0.12
    out = []
    plain, door = block.get("wall", "model.mvk_wall_plaster_straight"), "model.mvk_wall_plaster_door_round"
    window = "model.mvk_wall_plaster_window_wide_round"
    for side in ("north", "south", "west", "east"):
        count = nx if side in ("north", "south") else ny
        for i in range(count):
            run = (-hx if side in ("north", "south") else -hy) + m * (i + 0.5)
            x, y = {"north": (run, hy), "south": (run, -hy), "west": (-hx, run), "east": (hx, run)}[side]
            asset = plain
            if side == "south" and i == count // 2:
                asset = door
            elif (side in ("north", "east", "west")) and i % 2 == 0 and count > 1 and side != "south":
                asset = window
            px, py = rot(x, y)
            out.append({"name": f"{name}_{side}_{i}", "asset": asset, "pos": [px, py, round(z0, 3)], "yaw": round(_yaw(side) + yaw, 2),
                        "scale": 1.0, "role": "wall"})
    for k, (sx, sy) in enumerate(((-1, 1), (1, 1), (1, -1), (-1, -1))):
        px, py = rot(sx * hx, sy * hy)
        out.append({"name": f"{name}_corner_{k}", "asset": "model.mvk_corner_exterior_brick", "pos": [px, py, round(z0, 3)],
                    "yaw": round(90.0 * k + yaw, 2), "scale": 1.0, "role": "corner"})
    over = 1.0
    rx, ry = rot(0.0, 0.0)
    out.append({"name": f"{name}_roof", "asset": "model.mvk_roof_roundtiles_6x6", "pos": [rx, ry, round(z0 + WALL_H - 0.1, 3)], "yaw": round(yaw, 2),
                "scale": [round((nx * m + over) / 8.25, 4), round((ny * m + over) / 8.03, 4), 0.62], "role": "roof"})
    if block["size"] == "large":
        px, py = rot(hx * 0.45, -hy * 0.3)
        out.append({"name": f"{name}_chimney", "asset": "model.mvk_prop_chimney", "pos": [px, py, round(z0 + WALL_H + 0.8, 3)], "yaw": round(yaw, 2),
                    "scale": 1.0, "role": "prop"})
    return out


def _placements(block: dict, name: str, t: dict, T=None) -> list[dict]:
    kind = block["type"]
    if kind == "terrain":   # a mesh the renderer builds from the height field, not a kit piece
        return []
    if kind == "house":
        return _house(block, name, T)
    if kind == "piece":
        if block.get("terrain") and T is not None:
            block = {**block, "pos": [block["pos"][0], block["pos"][1], round(T.height(block["pos"][0], block["pos"][1]) + block.get("dz", 0.0), 3)]}
        return [{"name": name, "asset": block["asset"], "pos": block["pos"], "yaw": block.get("yaw_deg", 0.0),
                 "scale": block.get("scale", 1.0), "role": block.get("role", "piece")}]
    if kind == "shape":   # a primitive (hill, river, mountain) in a flat tone: {add, params, pos, scale, yaw_deg, colour}
        return [{"name": name, "asset": None, "shape": {"add": block["add"], "params": block.get("params", {}), "colour": block["colour"]},
                 "pos": block["pos"], "yaw": block.get("yaw_deg", 0.0), "scale": block.get("scale", 1.0), "role": "shape"}]
    if kind == "scatter":   # deterministic: the same seed gives the same wood in every shot
        import random
        rng = random.Random(block["seed"])
        x0, y0, x1, y1 = block["rect"]
        out = []
        while len(out) < block["count"]:
            x, y = round(rng.uniform(x0, x1), 3), round(rng.uniform(y0, y1), 3)
            if block.get("river", True) and abs(x) < 7.5 and -40 < y < 60:   # the river bed (hill_castle)
                continue
            if any(math.hypot(x - cx, y - cy) < r for cx, cy, r in block.get("avoid", [])):
                continue
            z = 0.0
            if block.get("terrain") and T is not None:
                z = T.height(x, y)
                if z < block.get("min_z", 0.4) or T.road_dist(x, y) < block.get("road_clear", 3.5):
                    continue
            elif "hill" in block.get("z_of", {}):   # the surface of the ellipsoid hill (cx, cy, cz, rx, ry, rz), never below the ground
                cx, cy, cz, rx, ry, rz = block["z_of"]["hill"]
                q = 1 - ((x - cx) / rx) ** 2 - ((y - cy) / ry) ** 2
                z = round(max(0.0, cz + rz * math.sqrt(q)) if q > 0 else 0.0, 3)
            out.append({"name": f"{name}_{len(out)}", "asset": rng.choice(block["assets"]), "pos": [round(x, 3), round(y, 3), z],
                        "yaw": round(rng.uniform(0, 360), 1), "scale": round(rng.uniform(*block.get("scale", [1.0, 1.0])), 3), "role": "scatter"})
        return out
    if kind == "row":
        (x0, y0, z0), (x1, y1, z1) = block["from"], block["to"]
        n = int(round(math.dist((x0, y0), (x1, y1)) / block["step"])) + 1
        n = max(1, n)
        return [{"name": f"{name}_{i}", "asset": block["asset"],
                 "pos": [round(x0 + (x1 - x0) * (i / (n - 1) if n > 1 else 0), 4),
                         round(y0 + (y1 - y0) * (i / (n - 1) if n > 1 else 0), 4), z0 + (z1 - z0) * (i / (n - 1) if n > 1 else 0)],
                 "yaw": block.get("yaw_deg", 0.0), "scale": block.get("scale", 1.0), "role": block.get("role", "row")}
                for i in range(n)]
    if kind == "floor":
        m = block.get("module_m", 2.0)
        nx, ny = block["nx"], block["ny"]
        cx, cy = block.get("centre", [0.0, 0.0])
        return [{"name": f"{name}_{i}_{j}", "asset": block["asset"],
                 "pos": [round(cx - nx * m / 2 + m * (i + 0.5), 4), round(cy - ny * m / 2 + m * (j + 0.5), 4), block.get("z", 0.0)],
                 "yaw": 0.0, "scale": 1.0, "role": "floor"} for i in range(nx) for j in range(ny)]
    if kind == "ring":
        m = block.get("module_m", 2.0)
        nx, ny = block["nx"], block["ny"]
        hx, hy = nx * m / 2, ny * m / 2
        cx, cy = block.get("centre", [0.0, 0.0])
        skip, rep = set(block.get("open_sides", [])), block.get("replace", {})
        out = []
        for side in ("north", "south", "west", "east"):
            if side in skip:
                continue
            count = nx if side in ("north", "south") else ny
            for i in range(count):
                run = (-hx if side in ("north", "south") else -hy) + m * (i + 0.5)
                pos = {"north": [run, hy], "south": [run, -hy], "west": [-hx, run], "east": [hx, run]}[side]
                out.append({"name": f"{name}_{side}_{i}", "asset": rep.get(f"{side}:{i}", block["wall"]),
                            "pos": [round(cx + pos[0], 4), round(cy + pos[1], 4), 0.0], "yaw": _yaw(side), "scale": 1.0, "role": "wall"})
        if block.get("corner"):
            for k, (sx, sy) in enumerate(((-1, 1), (1, 1), (1, -1), (-1, -1))):
                out.append({"name": f"{name}_corner_{k}", "asset": block["corner"], "pos": [round(cx + sx * hx, 4), round(cy + sy * hy, 4), 0.0],
                            "yaw": 90.0 * k, "scale": 1.0, "role": "corner"})
        return out
    raise WorldKitError(f"layout block {name!r}: unknown type {kind!r} (ring, floor, row, piece)")


def placements(layout_id: str, *, t: dict | None = None, doc: dict | None = None) -> list[dict]:
    """Every placed piece of a layout in a fixed order: {name, asset, pos (Blender x, y, z), yaw, scale, role}."""
    t, doc = t or table(), doc or layouts()
    if layout_id not in doc["layouts"]:
        raise WorldKitError(f"unknown layout {layout_id!r} (known: {', '.join(sorted(doc['layouts']))})")
    known = {a["id"] for a in t["assets"]}
    out = []
    T = terrain_for(doc["layouts"][layout_id])
    for i, block in enumerate(doc["layouts"][layout_id]["blocks"]):
        for p in _placements(block, block.get("name", f"{block['type']}{i}"), t, T):
            if p["asset"] is not None and p["asset"] not in known:
                raise WorldKitError(f"{layout_id}/{p['name']}: {p['asset']} is not in world_kits.json")
            out.append(p)
    names = [p["name"] for p in out]
    if len(set(names)) != len(names):
        raise WorldKitError(f"{layout_id}: two pieces share a name")
    return out


def _mean(path: Path) -> list[float]:
    return C._mean(path)


def kit_material(glb: Path, a: dict, *, strength: float | None = None, repo: Path | None = None) -> tuple[str, dict]:
    """(toon material name, ``StyleEngine.material`` kwargs) for one kit piece: its first material's base-colour image kept at
    ``strength`` over its own mean colour (D-102: a trace of the photo, no raw PBR)."""
    if a.get("flat"):   # foliage and rock: one palette-free flat tone (a single material replaces every slot)
        return f"kit_{a['id'].split('.', 1)[1]}", {"base": a["flat"]}
    doc, _ = C.read_glb(Path(glb).read_bytes())
    mats = [m["name"] for m in doc.get("materials", []) if (m.get("pbrMetallicRoughness") or {}).get("baseColorTexture")]
    if not mats:
        raise WorldKitError(f"{a['id']}: no material with a base-colour image")
    pick = a.get("material") or mats[0]
    img = C.embedded_image(glb, pick, repo=repo)
    mean = _mean(img)
    spec = {"base": mean + [1.0], "texture": str(img), "texture_mean": mean}
    if strength is not None:
        spec["strength"] = strength
    return f"kit_{a['id'].split('.', 1)[1]}", spec


def expand(layout_id: str, paths: dict[str, Path], *, t: dict | None = None, doc: dict | None = None,
           repo: Path | None = None, pbr: bool = False) -> tuple[list[dict], dict[str, dict]]:
    """(``described`` objects, toon materials) of a layout. ``paths`` is ``fetch()``'s answer. Pieces of one asset share one
    material; a piece the layout does not place costs nothing."""
    t = t or table()
    by_id = {a["id"]: a for a in t["assets"]}
    objs, mats, made = [], {}, {}
    spec = (doc or layouts())["layouts"][layout_id]
    T = terrain_for(spec)
    for i, b in enumerate(spec["blocks"]):
        if b["type"] != "terrain":
            continue
        from explainer_engine.blender import terrain as TR
        grid = (TR.Ranges(b["range"]).mesh(*b["res"]) if "range" in b else T.mesh(*b["rect"], *b["res"]))
        slots = {}
        for ci, cname in enumerate(TR.CLASSES):
            mname = f"terrain_{b['name']}_{cname}"
            mats[mname] = {"base": b["colours"][cname]}
            slots[str(ci)] = mname
        objs.append({"name": b["name"], "terrain": grid, "location": [0, 0, b.get("z", 0.0)], "material": slots, "smooth": True})
    for p in placements(layout_id, t=t, doc=doc):
        if p["asset"] is None:   # a primitive of the layout
            sh = p["shape"]
            mname = "shape_" + sh["colour"].lstrip("#").lower()
            mats[mname] = {"base": sh["colour"]}
            objs.append({"name": p["name"], "add": sh["add"], "params": sh["params"], "location": p["pos"],
                         "rotation_deg": [0, 0, p["yaw"]], "scale": p["scale"], "material": mname, "smooth": True})
            continue
        a = by_id[p["asset"]]
        if a["id"] not in made:
            made[a["id"]] = kit_material(paths[a["id"]], a, strength=a.get("texture_strength"), repo=repo)
        mname, spec = made[a["id"]]
        mats[mname] = spec
        objs.append({"name": p["name"], "gltf": {"path": str(paths[a["id"]]), "asset": a["id"]}, "location": p["pos"],
                     "rotation_deg": [0, 0, p["yaw"]], "scale": p["scale"], "material": None if pbr else mname, "smooth": False})
    return objs, mats


def scene_set(layout_id: str, *, t: dict | None = None, doc: dict | None = None, lib: dict | None = None) -> dict:
    """The ``scene_set/1`` of a layout (x right, z forward, y up): one object per placed piece with its measured size from the
    library record, a landmark when the layout names it; the axis is the layout's (default: along +Z through the origin)."""
    t, doc = t or table(), doc or layouts()
    lib = lib if lib is not None else L.load()
    spec = doc["layouts"][layout_id]
    objects = []
    for p in placements(layout_id, t=t, doc=doc):
        if p["asset"] is None:
            continue
        w, d, h = L.get(p["asset"], lib=lib)["three_d"]["bounds_m"]
        s = p["scale"] if isinstance(p["scale"], (int, float)) else 1.0
        swap = abs(p["yaw"]) % 180 == 90   # a quarter turn trades the extents
        sx, sz = (d, w) if swap else (w, d)
        objects.append({"id": p["name"], "kind": p["asset"].split(".", 1)[1], "pos": [p["pos"][0], p["pos"][2], p["pos"][1]],
                        "size": [round(sx * s, 3), round(h * s, 3), round(sz * s, 3)], "yaw_deg": p["yaw"],
                        "landmark": p["name"] in spec.get("landmarks", [])})
    doc_out = {"schema": "scene_set/1", "set_id": layout_id, "units": "m", "axis": spec.get("axis", {"deg": 0, "origin": [0, 0]}),
               "objects": objects, "mannequins": [], "cameras": []}
    from explainer_engine.core import contracts
    contracts.validate(doc_out)
    return doc_out


# --- the $0 proof (roadmap 21.6 PoC 3 with the kit): one courtyard layout, three moving shots, the real cast --------------------------

POC_JOB_ID = "world_kits_wpq8"
POC_FRAMES = 48
POC_VARIANTS = ("v01_reference_soft3d", "B_light")   # the reference look of the round and its cost yardstick
POC_CAST = (("guard", "ink_test_m", "costume.mco_male_ranger", "support_blue", (-1.6, 0.4), 150.0, "Idle_Talking_Loop", 0),
            ("traveller", "ink_test_f", "costume.mco_female_peasant", "answer_coral", (0.6, -1.0), -30.0, "Idle_Loop", 17),
            ("walker", "ink_test_m2", "costume.mco_male_peasant", "faction_a", (-3.0, -2.4), 20.0, "Walk_Formal_Loop", 5))
# (shot id, camera start, camera end, look-at start, look-at end, lens): a push in, a side dolly, a reverse from the east wall
POC_SHOTS = {
    "courtyard_wide": ([0.0, -10.5, 3.4], [0.0, -6.4, 2.5], [0.0, 4.0, 1.9], [0.0, 3.0, 1.7], 30),
    "courtyard_medium": ([-6.4, -3.2, 1.7], [-4.0, -5.0, 1.7], [-0.4, 0.2, 1.3], [-0.6, 0.0, 1.3], 40),
    "courtyard_reverse": ([6.4, -2.4, 2.3], [5.8, 1.6, 2.0], [-3.0, 1.2, 1.5], [-3.0, 1.2, 1.5], 34),
}


# The static epic set (the creator, 2026-11-05: a rich world is the main character): a 1440p still and a slow push of the same set.
C5_SAMPLES = 48   # C5 Cycles profile: low samples + denoise (the overnight plan); the cost per frame is the finding

HILL_SHOTS = {"castle_still": ([-38.0, -30.0, 26.0], None, [0.0, 60.0, 16.0], None, 28, 1),
              "castle_push": ([-38.0, -30.0, 26.0], [-26.0, -14.0, 20.0], [0.0, 60.0, 16.0], [0.0, 60.0, 16.0], 28, 0)}


RAIN_LEAD_SCALE = 1.8 / 1.63   # Rain stands 1.63 m; the UBC cast ~1.8 m (Q4's cast-lead handoff)


def _layout_cast(layout: str, cpaths, rain_blend: Path | None = None) -> tuple[list[dict], dict[str, dict]]:
    """(objects, extra toon materials): the characters a layout stands in its scene (``cast`` rows: name, character, costume, tint,
    [x, y(, z)], yaw, action, offset). A row whose character is ``rain_lead`` is Rain v3.3 adapted (WP-Q4: ``rig_blend``), placed only
    when ``rain_blend`` is given (the .blend is not in the repo); she faces -Y, so yaw 0 faces a camera that looks along +Y."""
    from explainer_engine.blender import style_sheets as SS
    out, mats = [], {}
    spec = layouts()["layouts"][layout]
    T = terrain_for(spec)
    for n, c, co, tint, xyz, yaw, act, off in spec.get("cast", []):
        if T is not None and len(xyz) == 2:
            xyz = [xyz[0], xyz[1], T.height(xyz[0], xyz[1])]
        if c == "rain_lead":
            if rain_blend is None:
                continue
            from explainer_engine.blender import character_benchmark as CB
            sc = CB.scene(Path(rain_blend), 1, tex_dir=Path(rain_blend).parent / "textures", wall=False, push=False)
            o = next(x for x in sc["objects"] if "rig_blend" in x)
            o.update({"name": n, "location": [xyz[0], xyz[1], xyz[2] if len(xyz) > 2 else 0.0], "rotation_deg": [0, 0, yaw],
                      "scale": RAIN_LEAD_SCALE})
            mats.update({k: v for k, v in sc["materials"].items() if k != "wall"})
            out.append(o)
            continue
        o = SS._cast_member(n, c, co, tint, tuple(xyz[:2]), yaw, act, off, cpaths)
        if len(xyz) > 2:
            o["location"][2] = xyz[2]
        out.append(o)
    return out, mats


def poc_scenes(paths: dict[str, Path], cpaths: dict[str, Path] | None, frames: int = POC_FRAMES,
               layout: str = "castle_courtyard", pbr: bool = False, rain_blend: Path | None = None) -> dict[str, dict]:
    """Shot id -> {objects, materials, camera, frames_total}: the SAME kit objects and cast in every shot, only the camera differs.
    A layout with its own ``shots`` (E1-E4, hill_castle) uses them: ``[camera, camera_to|null, look_at, look_at_to|null, lens, frames]``
    (frames 0 = the run's ``frames``); its ``cast`` rows put characters in the set."""
    from explainer_engine.blender import style_sheets as SS
    kit, kit_mats = expand(layout, paths, pbr=pbr)
    doc = layouts()["layouts"][layout]
    if layout == "hill_castle" or "shots" in doc:
        shots = doc.get("shots") or {k: list(v) for k, v in HILL_SHOTS.items()}
        cast, extra = _layout_cast(layout, cpaths, rain_blend) if doc.get("cast") and cpaths else ([], {})   # no character files = a set-only scene
        mats = dict(kit_mats)
        mats.update(extra)
        if cast:
            mats.update({"skin": {"base": "kit_card"}, "night": {"base": "night"}})
            for o in cast:
                for k, v in o.pop("_materials", {}).items():
                    if mats.get(k, v) != v:
                        raise WorldKitError(f"two cast members define material {k} differently")
                    mats[k] = v
        out = {}
        for sid, (c0, c1, a0, a1, lens, n) in shots.items():
            cam = {"location": c0, "look_at": a0, "lens_mm": lens, "focus_distance_m": round(math.dist(c0, a0), 2), "clip_end": 900.0}
            if c1:
                cam["to"] = {"location": c1, "look_at": a1}
            out[sid] = {"objects": [*json.loads(json.dumps(kit)), *json.loads(json.dumps(cast))], "materials": mats, "camera": cam,
                        "frames_total": n or frames}
        return out
    cast = [SS._cast_member(n, c, co, tint, xy, yaw, act, off, cpaths) for n, c, co, tint, xy, yaw, act, off in POC_CAST]
    mats = dict(kit_mats)
    mats.update({"skin": {"base": "kit_card"}, "night": {"base": "night"}})
    for o in cast:
        for k, v in o.pop("_materials", {}).items():
            if mats.get(k, v) != v:
                raise WorldKitError(f"two cast members define material {k} differently")
            mats[k] = v
    out = {}
    for sid, (c0, c1, a0, a1, lens) in POC_SHOTS.items():
        out[sid] = {"objects": [*kit, *json.loads(json.dumps(cast))], "materials": mats, "frames_total": frames,
                    "camera": {"location": c0, "look_at": a0, "lens_mm": lens, "focus_distance_m": round(math.dist(c0, a0), 2),
                               "to": {"location": c1, "look_at": a1}}}
    return out


def poc(out: Path, *, binary: str | None = None, variant_ids=POC_VARIANTS, frames: int = POC_FRAMES, scale: float = 1.0,
        device: str = "auto", layout: str = "castle_courtyard", shots=None, rain_blend: Path | None = None, log=print) -> list[dict]:
    """Render the three courtyard shots in each look as 24 fps clips (frames, MP4 review copy, s/frame) under ``out``; rows go to
    ``out/looks.json`` as they finish. Free: Blender on a CPU runner or the Mac, no paid call."""
    import time
    from explainer_engine.blender import render as R
    from explainer_engine.blender import style as S
    from explainer_engine.blender import style_sheets as SS
    from explainer_engine.blender.project import BlenderProject
    from explainer_engine.core.store import write_json_atomic
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    kit = fetch()
    paths = {**SS.fetch(), **kit}
    scn_cache = {}
    b = BlenderProject().resolve(binary, device=device)
    vault = R.LocalVault(out / "vault")
    rows = []
    for vid in variant_ids:
        pbr = vid in SS.PBR_VARIANTS   # C5: the kit's own glTF materials under Cycles, no toon replacement
        if pbr not in scn_cache:
            scn_cache[pbr] = poc_scenes(paths, C.fetch() if layout == "castle_courtyard" or layouts()["layouts"][layout].get("cast") else None, frames, layout, pbr=pbr, rain_blend=rain_blend)
        for sid, sc in scn_cache[pbr].items():
            if shots and sid not in shots:
                continue
            scene, graph = SS.job_scene(sid, vid, sc, paths)
            _, tokens = SS.style_for(vid)
            n = scene.get("frames_total", 1)
            spec = SS.spec_for(sid, vid, tokens, scene=scene, frames=n)
            spec["job_id"] = POC_JOB_ID
            if pbr:
                spec["render"].update({"samples": C5_SAMPLES, "denoise": True})
            if scale != 1.0:
                spec["frame"]["render_scale"] = scale
            t0 = time.time()
            try:
                m = R.HeadlessRender(b, vault).run(spec, out / "work", scene=scene)
            except ContractError as e:   # a scaled review render is not a master (CN-17): keep its frames, as the look round does
                if scale == 1.0 or "master" not in str(e):
                    raise
                from explainer_engine.core import shot_cache
                m = dict(json.loads((out / "work" / shot_cache.key(spec) / "render_manifest.json").read_text(encoding="utf-8")),
                         _findings=[])
            sdir = out / "work" / m["cache_key"]
            rep = json.loads((sdir / "bpy_report.json").read_text(encoding="utf-8"))
            row = SS._look_row(out, sid, vid, m, sdir, rep, graph, t0, n, scale, clip=n > 1)
            row["kit"] = {"layout": layout, "pieces": len(placements(layout)), "gltf_objects": rep.get("gltf")}
            rows.append(row)
            log(f"{sid}/{vid}: {row['times']['steady_median_s']} s/frame, first {row['times']['first_s']} s, {n} frames")
            write_json_atomic(out / "looks.json", {"schema": "look_round/1", "job_id": POC_JOB_ID, "rows": rows})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.world_kits", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("register")
    r.add_argument("--downloads", required=True)
    r.add_argument("--polyhaven-dir", default=None)
    sub.add_parser("fetch").add_argument("--packs")
    sub.add_parser("list")
    ly = sub.add_parser("layout")
    ly.add_argument("id")
    pc = sub.add_parser("poc", help="three moving courtyard shots in the reference look and B_light (free)")
    pc.add_argument("--out", required=True)
    pc.add_argument("--binary", default=None)
    pc.add_argument("--variants", default=",".join(POC_VARIANTS))
    pc.add_argument("--layout", default="castle_courtyard", choices=tuple(layouts()["layouts"]))
    pc.add_argument("--shots", default="", help="comma-separated shot ids (empty = all of the layout)")
    pc.add_argument("--frames", type=int, default=POC_FRAMES)
    pc.add_argument("--scale", type=float, default=1.0)
    pc.add_argument("--rain-blend", default=os.environ.get("WORLD_KITS_RAIN_BLEND"), help="rain_lead.blend: places Rain as the lead (else the layouts stand without her)")
    pc.add_argument("--device", default="auto", choices=("auto", "cpu", "gpu"))
    a = ap.parse_args(argv)
    if a.cmd == "register":
        print(json.dumps(register(Path(a.downloads), polyhaven_dir=Path(a.polyhaven_dir) if a.polyhaven_dir else None), indent=1))
    elif a.cmd == "fetch":
        print(json.dumps({k: str(v) for k, v in fetch(packs_dir=Path(a.packs) if a.packs else None).items()}, indent=1))
    elif a.cmd == "poc":
        poc(Path(a.out), binary=a.binary, variant_ids=a.variants.split(","), frames=a.frames, scale=a.scale, device=a.device,
            layout=a.layout, shots=[x for x in a.shots.split(",") if x] or None, rain_blend=Path(a.rain_blend) if a.rain_blend else None)
    elif a.cmd == "list":
        t = table()
        for x in t["assets"]:
            print(f"{x['id']:48} {x['source']:10} {x['role']:8} {x.get('sha256', '-')[:12]}")
        print(f"layouts: {', '.join(sorted(layouts()['layouts']))}")
    else:
        objs, mats = expand(a.id, fetch())
        print(json.dumps({"objects": objs, "materials": mats, "scene_set": scene_set(a.id)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
