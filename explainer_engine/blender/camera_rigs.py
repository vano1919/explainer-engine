"""The Add Camera Rigs extension of the Blender lanes (WP-Q7): fetch the pinned zip, check it, hand its path to the scene job.

The extension (Blender's official platform, GPL-3.0-or-later, Dolly / Crane / 2D rigs with a root, an aim and a camera bone,
focus, f-stop and lens-breathing properties) is used as shipped: ``bpy/render_shot.py`` installs the zip into the render's own
Blender (``bpy.ops.extensions.package_install_files``), builds the rig with the extension's operator and keys its bones. None of its
code is copied into this package. The pin (version, url, sha256) is the ``blender_extensions`` entry of ``config/cloud_pins.json``.

    python -m explainer_engine.blender.camera_rigs [--dir D]      # fetch + verify, print the path
"""
from __future__ import annotations

import argparse
import hashlib
import json
import urllib.request
from pathlib import Path

from explainer_engine.core.errors import ConfigError

ROOT = Path(__file__).resolve().parents[2]
PINS = ROOT / "config" / "cloud_pins.json"
CACHE = ROOT / "tools" / "blender_extensions"
KEY = "add_camera_rigs"


def pin() -> dict:
    try:
        return json.loads(PINS.read_text(encoding="utf-8"))["blender_extensions"][KEY]
    except (KeyError, FileNotFoundError) as exc:
        raise ConfigError(f"config/cloud_pins.json has no blender_extensions.{KEY} pin") from exc


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def ensure(cache: Path | None = None, *, download=None) -> Path:
    """The pinned zip in the content cache, fetched when absent; a file whose sha256 differs from the pin is refused."""
    p = pin()
    folder = Path(cache or CACHE) / p["sha256"]
    path = folder / f"add_camera_rigs-{p['version']}.zip"
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".part")
        if download is not None:
            download(p["url"], tmp)
        else:
            req = urllib.request.Request(p["url"], headers={"User-Agent": "explainer-engine/1"})   # the platform refuses urllib's own
            with urllib.request.urlopen(req, timeout=60) as r, open(tmp, "wb") as f:   # noqa: S310 (a pinned https url)
                f.write(r.read())
        tmp.replace(path)
    got = sha256_file(path)
    if got != p["sha256"]:
        path.unlink(missing_ok=True)
        raise ConfigError(f"{KEY}: sha256 {got} differs from the pin {p['sha256']}")
    return path


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dir", default=None)
    a = ap.parse_args(argv)
    print(ensure(Path(a.dir) if a.dir else None))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
