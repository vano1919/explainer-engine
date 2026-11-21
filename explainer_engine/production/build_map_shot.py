"""Map shots for build_shot: a spec with ``"kind": "map"`` goes to the offline MapLibre lane (``maps/maplibre_lane/render.py``) with the episode
film's map style (``truce_cold`` etc.: colours, front line, HUD, font, finish) and the owner's five camera moves; the output is a 1280x720 / 24 fps
mp4 like the photo shots, so ``build_episode`` can cut them together. Tiles come from ``--tile-dir`` / ``$EXPLAINER_MAP_TILES`` (one-time free
download: ``maps/maplibre_lane/fetch_tiles.py``). Needs playwright + a Chromium (``$EXPLAINER_CHROMIUM``) and the vendored maplibre-gl files.
The front line of a spec is whatever its ``line_geojson`` holds; ``examples/maps/truce_front_1914/`` has a minimal one traced from the public-domain
West Point map (``maps/trace_front_1914.py``, approximate, not a claim source).
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path


def build(spec_path, out_mp4, workdir=None, tile_dir=None) -> dict:
    from explainer_engine.maps.maplibre_lane import render

    tiles = tile_dir or os.environ.get("EXPLAINER_MAP_TILES")
    if not tiles:
        raise ValueError("map shot: give --tile-dir or set EXPLAINER_MAP_TILES (offline tiles from maplibre_lane/fetch_tiles.py)")
    spec_path = Path(spec_path).resolve()
    own = workdir is None
    work = Path(workdir) if workdir else Path(tempfile.mkdtemp(prefix="map_shot_"))
    try:
        info = render.render_shot(str(spec_path), str(out_mp4), str(tiles), str(work))
    finally:
        if own:
            shutil.rmtree(work, ignore_errors=True)
    log = dict(id=spec_path.stem, kind="map", out=str(out_mp4), render=info)
    Path(out_mp4).with_suffix(".render_log.json").write_text(json.dumps(log, indent=1, default=str), encoding="utf-8")
    return log
