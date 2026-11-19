# from ahujasid/blender-mcp@2e4b0bc294694b1570d76ed01be657c22e6d02a0:addon.py (MIT)
"""Poly Haven search, download and world setup (WP-Q8; synthesis, not new code: the creator's principle of 2026-11-05).

The Poly Haven part of Blender-MCP's ``addon.py`` (MIT, (c) 2025 Siddharth Ahuja) is the maintained, field-tested piece: it
knows the API's quirks (``files`` map keys, ``include`` side files, md5 per file, ETag caching, the inconsistent casing of the
texture map names) and the HDRI world node chain. What is taken, with the changes our pipeline needs:

* ``api_get`` (``_polyhaven_api_get``): the ETag/TTL cache stays; ``requests`` became ``urllib`` (the repository has no
  ``requests`` requirement), the User-Agent names this project (Poly Haven asks integrations to identify themselves);
* ``valid_slug``, ``download`` (streamed, md5 checked against the API's), ``select_texture_maps``, ``available``,
  ``fetch_model_files`` (the zip-slip guard on ``include`` paths is kept as it was), ``hdri_world`` (the Blender 5.2 node chain,
  run INSIDE Blender with the ``bpy`` module handed in, like ``assets.import_asset``).

What is NOT taken, on purpose: the socket server, the telemetry and the edit recorder (nothing here listens or reports), the
paid generators (Hyper3D, Hunyuan, Tripo, Meshy, Sketchfab, Poly Pizza) and the Blender-side ``.blend`` append of a model (our
models arrive as ``glTF`` and every material is replaced by a ``style.py`` toon material, so the artist's node tree would be
thrown away: ``assets/library.py`` records the glTF). The Poly Haven API's own code (Poly-Haven/Public-API) is AGPL-3.0 and is
only CALLED, never copied; assets are CC0 (``licence_sources.json`` row ``polyhaven``).

CLI (free; network only to api.polyhaven.com and its CDN):

    python -m explainer_engine.blender.polyhaven search models --query barrel --limit 5
    python -m explainer_engine.blender.polyhaven fetch modular_fort_01 --type models --resolution 1k --out D
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from explainer_engine.core.errors import ContractError

API_BASE = "https://api.polyhaven.com"
UA = "explainer-engine-asset-import/1 (+https://github.com/vano1919/explainer-engine)"
API_TIMEOUT = 30
FILE_TIMEOUT = 60
CHUNK_SIZE = 1024 * 1024
CACHE_TTL = 12 * 60 * 60   # Poly Haven's own Cache-Control: max-age=43200
CACHE_MAX_ENTRIES = 16

# What we can import, per asset type, checked BEFORE any transfer (the API lists a ``usd`` entry for every model).
SUPPORTED_FORMATS = {"hdris": ("hdr", "exr"), "textures": ("jpg", "png", "exr"), "models": ("gltf",)}
DEFAULT_FORMATS = {"hdris": "hdr", "textures": "jpg", "models": "gltf"}

# The API's map keys, matched exactly (their casing is inconsistent and load-bearing), and what each map drives.
TEXTURE_MAPS = {"Diffuse": "base_color", "Rough": "roughness", "Metal": "metallic", "Displacement": "displacement",
                "nor_gl": "normal", "nor_dx": "normal"}
SLUG_RE = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
SITE = "https://polyhaven.com"


class PolyHavenError(ContractError):
    """A Poly Haven request or answer that cannot be used (bad slug, unsupported format, missing resolution, bad checksum)."""


class PolyHavenAPIError(PolyHavenError):
    """A non-2xx from the API with its status (429 and 503 want a back-off, not a generic failure)."""

    def __init__(self, status: int, retry_after=None):
        super().__init__(f"HTTP {status}")
        self.status = status
        self.retry_after = retry_after


_cache: dict = {}
_clock = 0


def _touch() -> int:
    global _clock
    _clock += 1
    return _clock


def api_get(path: str, params: dict | None = None, *, cache: bool = False, opener=None):
    """GET a Poly Haven API endpoint as JSON. With ``cache`` the answer is held for ``CACHE_TTL`` and revalidated by ETag after it."""
    key = (path, tuple(sorted((params or {}).items())))
    entry = _cache.get(key) if cache else None
    headers = {"User-Agent": UA}
    if entry is not None:
        if time.time() - entry["fetched"] < CACHE_TTL:
            entry["used"] = _touch()
            return entry["payload"]
        if entry.get("etag"):
            headers["If-None-Match"] = entry["etag"]
    url = f"{API_BASE}/{path}" + (("?" + urllib.parse.urlencode(params)) if params else "")
    try:
        with (opener or urllib.request.urlopen)(urllib.request.Request(url, headers=headers), timeout=API_TIMEOUT) as r:
            payload, etag = json.loads(r.read().decode("utf-8")), r.headers.get("ETag")
    except urllib.error.HTTPError as e:
        if e.code == 304 and entry is not None:
            entry["fetched"], entry["used"] = time.time(), _touch()
            return entry["payload"]
        raise PolyHavenAPIError(e.code, e.headers.get("Retry-After")) from e
    if cache:
        if len(_cache) >= CACHE_MAX_ENTRIES:   # least recently USED, not least recently fetched (upstream's note)
            _cache.pop(min(_cache, key=lambda k: _cache[k]["used"]), None)
        _cache[key] = {"payload": payload, "etag": etag, "fetched": time.time(), "used": _touch()}
    return payload


def valid_slug(asset_id: str) -> bool:
    """Slugs are letters, digits, underscores and hyphens; checked once because they build file names."""
    return bool(SLUG_RE.match(asset_id or ""))


def download(file_info: dict, dest: Path | str, *, opener=None) -> Path:
    """Stream one file to ``dest`` and verify the md5 the API published; a truncated or corrupted file is removed."""
    dest = Path(dest)
    expected = file_info.get("md5")
    digest = hashlib.md5()   # the API's own checksum, not a security hash (the library keeps the sha256)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(file_info["url"], headers={"User-Agent": UA})
    with (opener or urllib.request.urlopen)(req, timeout=FILE_TIMEOUT) as r, open(dest, "wb") as f:
        while True:
            chunk = r.read(CHUNK_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            f.write(chunk)
    if expected and digest.hexdigest() != expected:
        dest.unlink(missing_ok=True)
        raise PolyHavenError(f"Checksum mismatch for {dest.name}: the download was truncated or corrupted")
    return dest


def _resolution_rank(resolution: str) -> float:
    m = re.match(r"^(\d+(?:\.\d+)?)k$", resolution or "")
    return float(m.group(1)) if m else float("inf")


def sorted_resolutions(resolutions) -> list[str]:
    return sorted(resolutions, key=lambda r: (_resolution_rank(r), r))


def available(files_data: dict, asset_type: str) -> str:
    """What an asset really offers, for an error message that lets the caller correct itself."""
    supported = SUPPORTED_FORMATS.get(asset_type, ())
    resolutions, formats = set(), set()
    for by_resolution in files_data.values():
        if not isinstance(by_resolution, dict):
            continue
        for resolution, by_format in by_resolution.items():
            if isinstance(by_format, dict):
                present = {fmt for fmt in by_format if fmt in supported}
                if present:
                    resolutions.add(resolution)
                    formats |= present
    return ("available resolutions: " + (", ".join(sorted_resolutions(resolutions)) or "none")
            + "; formats: " + (", ".join(sorted(formats)) or "none"))


def select_texture_maps(files_data: dict, resolution: str, file_format: str) -> dict[str, str]:
    """The map keys worth downloading for a material: {api key: role}."""
    selected = {}
    for key, role in TEXTURE_MAPS.items():
        by_resolution = files_data.get(key)
        if isinstance(by_resolution, dict) and file_format in by_resolution.get(resolution, {}):
            selected[key] = role
    if "nor_gl" in selected:
        selected.pop("nor_dx", None)   # OpenGL normals are what Blender's Normal Map node expects
    if "base_color" not in selected.values():   # multi-variant fabrics name the albedo col_1 / col_2 / diff_...
        for key in sorted(files_data):
            by_resolution = files_data.get(key)
            if key.lower().startswith(("col", "diff")) and isinstance(by_resolution, dict) \
                    and file_format in by_resolution.get(resolution, {}):
                selected[key] = "base_color"
                break
    return selected


def safe_include(dest_dir: Path, include_path: str) -> Path | None:
    """The target of an ``include`` entry, or None when the API's key would leave ``dest_dir`` (an absolute path or ``..``;
    the answer is untrusted input, upstream's zip-slip guard)."""
    target = os.path.abspath(os.path.join(dest_dir, os.path.normpath(include_path)))
    root = os.path.abspath(dest_dir)
    if os.path.isabs(include_path) or ".." in include_path or not target.startswith(root + os.sep):
        return None
    return Path(target)


def fetch_model_files(files_data: dict, resolution: str, file_format: str, dest_dir: Path | str, *, opener=None) -> dict:
    """Download a model's main file and its side files (``include``) into ``dest_dir``; returns {main, files: [{name, url,
    md5, bytes}]} so the caller can record URL and checksum of every file. None when the resolution/format is not published."""
    dest_dir = Path(dest_dir)
    info = files_data.get(file_format, {}).get(resolution, {}).get(file_format)
    if not info:
        return None
    main = dest_dir / os.path.basename(info["url"].split("?")[0])
    done = [{"name": main.name, "url": info["url"], "md5": info.get("md5"), "bytes": download(info, main, opener=opener).stat().st_size}]
    for include_path, include_info in (info.get("include") or {}).items():
        target = safe_include(dest_dir, include_path)
        if target is None:
            continue   # skipped, as upstream does
        done.append({"name": include_path, "url": include_info["url"], "md5": include_info.get("md5"),
                     "bytes": download(include_info, target, opener=opener).stat().st_size})
    return {"main": main, "files": done}


def asset_url(slug: str, asset_type: str = "models") -> str:
    return f"{SITE}/a/{slug}"


def search(asset_type: str, query: str = "", limit: int = 20) -> list[dict]:
    """Assets of a type whose slug, name, tags or categories contain every word of ``query`` (a local match over the cached list)."""
    assets = api_get("assets", {"t": asset_type}, cache=True)
    words = [w for w in query.lower().split() if w]
    out = []
    for slug, rec in sorted(assets.items()):
        hay = " ".join([slug, rec.get("name", ""), *rec.get("tags", []), *rec.get("categories", [])]).lower()
        if all(w in hay for w in words):
            out.append({"slug": slug, "name": rec.get("name"), "categories": rec.get("categories"), "polycount": rec.get("polycount"),
                        "url": asset_url(slug)})
    return out[:limit]


def authors(slug: str) -> list[str]:
    """The names the API lists for an asset (kept in the library record's note; CC0 needs no credit, it is courtesy)."""
    info = api_get(f"info/{urllib.parse.quote(slug, safe='')}", cache=True)
    return sorted((info.get("authors") or {}).keys())


# --- inside Blender -----------------------------------------------------------------------------------------------------------------

def hdri_world(bpy, image_path: Path | str, asset_id: str, resolution: str = "1k"):
    """A NEW world with the HDRI as its background (upstream ``_polyhaven_import_hdri``): the scene's current world is left
    intact (upstream wiped ``worlds[0]``), the image is packed so the .blend is self-contained, its colour space stays the
    loader's (scene-linear). Returns the world. Runs inside Blender; ``style.py`` may replace the graph, this is the plain setup."""
    world = bpy.data.worlds.new(f"PolyHaven {asset_id}")
    world.use_nodes = True
    tree = world.node_tree
    tree.nodes.clear()
    coord = tree.nodes.new(type="ShaderNodeTexCoord")
    mapping = tree.nodes.new(type="ShaderNodeMapping")
    env = tree.nodes.new(type="ShaderNodeTexEnvironment")
    env.image = bpy.data.images.load(str(image_path), check_existing=True)
    env.image.name = f"{asset_id}_{resolution}"
    env.image.pack()
    background = tree.nodes.new(type="ShaderNodeBackground")
    output = tree.nodes.new(type="ShaderNodeOutputWorld")
    tree.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
    tree.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
    tree.links.new(env.outputs["Color"], background.inputs["Color"])
    tree.links.new(background.outputs["Background"], output.inputs["Surface"])
    bpy.context.scene.world = world
    return world


# --- CLI ----------------------------------------------------------------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m explainer_engine.blender.polyhaven", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("search")
    s.add_argument("type", choices=sorted(SUPPORTED_FORMATS))
    s.add_argument("--query", default="")
    s.add_argument("--limit", type=int, default=20)
    f = sub.add_parser("fetch")
    f.add_argument("slug")
    f.add_argument("--type", default="models", choices=sorted(SUPPORTED_FORMATS))
    f.add_argument("--resolution", default="1k")
    f.add_argument("--format", default=None)
    f.add_argument("--out", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "search":
        print(json.dumps(search(a.type, a.query, a.limit), indent=1))
        return 0
    if not valid_slug(a.slug):
        raise PolyHavenError(f"invalid asset id {a.slug!r}")
    fmt = (a.format or DEFAULT_FORMATS[a.type]).lower()
    if fmt not in SUPPORTED_FORMATS[a.type]:
        raise PolyHavenError(f"unsupported {a.type} format {fmt}; supported: {', '.join(SUPPORTED_FORMATS[a.type])}")
    files = api_get(f"files/{urllib.parse.quote(a.slug, safe='')}")
    if a.type == "models":
        got = fetch_model_files(files, a.resolution, fmt, Path(a.out))
    else:
        info = files.get({"hdris": "hdri", "textures": "Diffuse"}[a.type], {}).get(a.resolution, {}).get(fmt)
        got = None if not info else {"main": download(info, Path(a.out) / f"{a.slug}_{a.resolution}.{fmt}"),
                                     "files": [{"name": f"{a.slug}_{a.resolution}.{fmt}", "url": info["url"], "md5": info.get("md5")}]}
    if got is None:
        raise PolyHavenError(f"{a.slug} has no {a.resolution} {fmt} - {available(files, a.type)}")
    print(json.dumps({"slug": a.slug, "main": str(got["main"]), "files": got["files"], "page": asset_url(a.slug)}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
