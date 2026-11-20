"""One-time free offline downloader for OpenFreeMap vector tiles and Terrarium DEM tiles (G-04c)."""
from __future__ import annotations
import argparse
import hashlib
import json
import math
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable
OPENFREEMAP_TILEJSON_URL = "https://tiles.openfreemap.org/planet"
# The bare ".../planet/{z}/{x}/{y}.pbf" path answers 200 with ZERO bytes; the real path carries the current planet
# version, which the TileJSON above names (e.g. planet/20261115_080022_pt). Resolved at run time.
OPENFREEMAP_VECTOR_TEMPLATE = OPENFREEMAP_TILEJSON_URL + "/{version}/{z}/{x}/{y}.pbf"
TERRARIUM_DEM_TEMPLATE = "https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
USER_AGENT = "ExplainerEngine-OfflineTilePrefetch/1.0 (free-educational-docudrama)"
def lonlat_to_tile(lon: float, lat: float, zoom: int) -> tuple[int, int]:
    """Convert WGS84 (lon, lat) to Slippy Map XYZ (x, y) at integer `zoom`."""
    lat_clamped = max(-85.05112878, min(85.05112878, float(lat)))
    n = 2 ** int(zoom)
    x = int(math.floor((float(lon) + 180.0) / 360.0 * n))
    lat_rad = math.radians(lat_clamped)
    y = int(
        math.floor(
            (1.0 - math.log(math.tan(lat_rad) + (1.0 / math.cos(lat_rad))) / math.pi) / 2.0 * n
        )
    )
    x = max(0, min(n - 1, x))
    y = max(0, min(n - 1, y))
    return x, y
def iter_bbox_tiles(
    bbox: tuple[float, float, float, float],
    min_zoom: int,
    max_zoom: int,
) -> Iterable[tuple[int, int, int]]:
    """Yield (z, x, y) tiles covering `bbox = (min_lon, min_lat, max_lon, max_lat)`."""
    min_lon, min_lat, max_lon, max_lat = bbox
    for z in range(int(min_zoom), int(max_zoom) + 1):
        x0, y1 = lonlat_to_tile(min_lon, min_lat, z)
        x1, y0 = lonlat_to_tile(max_lon, max_lat, z)
        for x in range(min(x0, x1), max(x0, x1) + 1):
            for y in range(min(y0, y1), max(y0, y1) + 1):
                yield z, x, y
def sha256_bytes(data: bytes) -> str:
    """Return hex SHA-256 digest of `data`."""
    return hashlib.sha256(data).hexdigest()
def _download_tile(url: str, dest: Path, timeout: float = 30.0) -> tuple[int, str]:
    """Download `url` to `dest` if not already cached, returning (byte_size, sha256)."""
    if dest.exists() and dest.stat().st_size > 0:
        existing = dest.read_bytes()
        return len(existing), sha256_bytes(existing)
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        payload = resp.read()
    dest.write_bytes(payload)
    return len(payload), sha256_bytes(payload)
def resolve_vector_template(timeout: float = 30.0) -> str:
    """Read the TileJSON of OpenFreeMap and return its versioned `{z}/{x}/{y}` vector tile template."""
    req = urllib.request.Request(OPENFREEMAP_TILEJSON_URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        tiles = json.loads(resp.read().decode("utf-8")).get("tiles") or []
    if not tiles or "{z}" not in tiles[0]:
        raise ValueError("OpenFreeMap TileJSON has no usable tiles template")
    return str(tiles[0])


def _read_manifest(path: Path) -> dict[str, object] | None:
    """Return an earlier manifest of this tile folder, or None when there is none or it is not ours."""
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError:
        return None
    if data.get("schema") != "explainer_engine.offline_tiles.v1" or not isinstance(data.get("tiles"), list):
        return None
    return data


def fetch_tiles(
    bbox: tuple[float, float, float, float],
    tile_dir: str | Path,
    min_zoom: int = 6,
    max_zoom: int = 11,
    dem_max_zoom: int = 10,
    delay_sec: float = 0.05,
    vector_template: str | None = None,
) -> dict[str, object]:
    """Fetch OpenFreeMap vector (.pbf) and Terrarium DEM (.png) tiles into `tile_dir`."""
    root = Path(tile_dir).resolve()
    root.mkdir(parents=True, exist_ok=True)
    entries: list[dict[str, object]] = []
    vector_template = vector_template or resolve_vector_template()
    for z, x, y in iter_bbox_tiles(bbox, min_zoom, max_zoom):
        url = vector_template.format(z=z, x=x, y=y)
        rel_path = Path("vector") / str(z) / str(x) / f"{y}.pbf"
        size, digest = _download_tile(url, root / rel_path)
        entries.append(
            {
                "kind": "vector",
                "z": z,
                "x": x,
                "y": y,
                "path": rel_path.as_posix(),
                "source_url": url,
                "bytes": size,
                "sha256": digest,
            }
        )
        if delay_sec > 0:
            time.sleep(delay_sec)
    for z, x, y in iter_bbox_tiles(bbox, min_zoom, min(max_zoom, dem_max_zoom)):
        url = TERRARIUM_DEM_TEMPLATE.format(z=z, x=x, y=y)
        rel_path = Path("dem") / str(z) / str(x) / f"{y}.png"
        try:
            size, digest = _download_tile(url, root / rel_path)
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                continue
            raise
        entries.append(
            {
                "kind": "dem",
                "z": z,
                "x": x,
                "y": y,
                "path": rel_path.as_posix(),
                "source_url": url,
                "bytes": size,
                "sha256": digest,
            }
        )
        if delay_sec > 0:
            time.sleep(delay_sec)
    manifest_path = root / "manifest.json"
    previous = _read_manifest(manifest_path)
    if previous:
        # a second fetch into the same folder (other bbox / zooms) ADDS to the manifest instead of overwriting it
        seen = {(e["kind"], e["z"], e["x"], e["y"]) for e in entries}
        entries = [e for e in previous["tiles"] if (e["kind"], e["z"], e["x"], e["y"]) not in seen] + entries
        bboxes = [list(previous["bbox"]), list(bbox)]
        bbox = (
            min(b[0] for b in bboxes), min(b[1] for b in bboxes),
            max(b[2] for b in bboxes), max(b[3] for b in bboxes),
        )
        min_zoom = min(min_zoom, int(previous["min_zoom"]))
        max_zoom = max(max_zoom, int(previous["max_zoom"]))
        dem_max_zoom = max(min(max_zoom, dem_max_zoom), int(previous["dem_max_zoom"]))
    manifest = {
        "schema": "explainer_engine.offline_tiles.v1",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "bbox": list(bbox),
        "min_zoom": min_zoom,
        "max_zoom": max_zoom,
        "dem_max_zoom": min(max_zoom, dem_max_zoom),
        "sources": {
            "vector": vector_template,
            "dem": TERRARIUM_DEM_TEMPLATE,
        },
        "tile_count": len(entries),
        "tiles": entries,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return manifest
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments, requiring explicit `--yes` confirmation."""
    parser = argparse.ArgumentParser(
        description="One-time free prefetch of OpenFreeMap vector tiles and Terrarium DEM tiles."
    )
    parser.add_argument(
        "--bbox",
        type=float,
        nargs=4,
        metavar=("MIN_LON", "MIN_LAT", "MAX_LON", "MAX_LAT"),
        default=(2.1, 50.6, 3.6, 51.4),
        help="Geographic bounding box (default: Flanders 1914 sector 2.1 50.6 3.6 51.4)",
    )
    parser.add_argument("--min-zoom", type=int, default=6, help="Minimum zoom level (default: 6)")
    parser.add_argument("--max-zoom", type=int, default=11, help="Maximum vector zoom (default: 11)")
    parser.add_argument("--dem-max-zoom", type=int, default=10, help="Maximum DEM zoom (default: 10)")
    parser.add_argument("--tile-dir", type=str, required=True, help="Output directory for tiles")
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Required confirmation flag to perform network downloads.",
    )
    return parser.parse_args(argv)
def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint."""
    args = parse_args(argv)
    if not args.yes:
        print(
            "Refusing to download tiles without --yes. Re-run with --yes to fetch offline tiles.",
            file=sys.stderr,
        )
        return 2
    bbox = (float(args.bbox[0]), float(args.bbox[1]), float(args.bbox[2]), float(args.bbox[3]))
    manifest = fetch_tiles(
        bbox=bbox,
        tile_dir=args.tile_dir,
        min_zoom=args.min_zoom,
        max_zoom=args.max_zoom,
        dem_max_zoom=args.dem_max_zoom,
    )
    print(f"Fetched {manifest['tile_count']} tiles into {Path(args.tile_dir).resolve()}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
