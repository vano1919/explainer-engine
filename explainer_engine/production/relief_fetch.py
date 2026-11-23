"""Fetch the Natural Earth shaded relief raster once (free, public domain, about 44 MB) for ``maps/relief.py`` (v4.3 P4).

    python -m explainer_engine.production.relief_fetch [--check]
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
import zipfile
from pathlib import Path

from explainer_engine.core.errors import ConfigError
from explainer_engine.maps.relief import RASTER_NAME, SOURCE_URL, SOURCE_ZIP_SHA256, available, raster_path, relief_dir


def fetch() -> Path:
    """Download and unpack the raster once (free, about 44 MB), checking the archive's sha256."""
    d = relief_dir()
    d.mkdir(parents=True, exist_ok=True)
    z = d / "SR_HR.zip"
    if not z.is_file():
        tmp = z.with_suffix(".part")
        urllib.request.urlretrieve(SOURCE_URL, tmp)
        tmp.replace(z)
    h = hashlib.sha256(z.read_bytes()).hexdigest()
    if h != SOURCE_ZIP_SHA256:
        raise ConfigError(f"{z}: sha256 {h} is not the checked {SOURCE_ZIP_SHA256}; delete it and fetch again")
    with zipfile.ZipFile(z) as zf:
        for name in (RASTER_NAME, "SR_HR.tfw"):
            if not (d / name).is_file():
                zf.extract(name, d)
    return raster_path()


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--check", action="store_true", help="only say whether the raster is there")
    a = ap.parse_args(argv)
    if a.check:
        print("ok" if available() else f"missing: {raster_path()}")
        return 0 if available() else 1
    print(fetch())
    return 0


if __name__ == "__main__":
    sys.exit(main())
