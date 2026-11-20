# MapLibre lane (offline map shots, G-04c)

Spec (`maplibre_spec.py`) -> offline tiles (`fetch_tiles.py`, one-time, free, OpenFreeMap + Terrarium DEM) -> headless Chromium (Playwright) draws
`page.html` frame by frame (`render.py`) -> ffmpeg. Camera: only truck, zoom_in, zoom_out, truck_zoom_in, truck_zoom_out (no orbit, tilt, rotation).

Setup: `pip install playwright` (Chromium, or `EXPLAINER_CHROMIUM=<path>`), `maplibre-gl.js/css` into `vendor/` (see `vendor/README.md`).
Tiles: `python -m explainer_engine.maps.maplibre_lane.fetch_tiles --bbox W S E N --min-zoom 3 --max-zoom 8 --dem-max-zoom 8 --tile-dir <dir> --yes`
(repeat with other boxes/zooms: the manifest is merged). Fetch the DEM with a margin around the whole camera path: hillshade exists only
inside the DEM bounds of the deepest zoom. `EXPLAINER_MAP_DEBUG=1` prints browser console, failed requests and page errors.

## Episode map style (creator 2026-11-20: every episode has its own map style, matching the video's look)
A shot spec names it: `"style_preset": "<name>"` (default `neutral`), loaded from `styles/<name>.json`; `"font": "preset"` takes the preset's font.
A preset sets the map colours (background, water, waterways, land cover, border with dash, roads, hillshade), the front line, the HUD colours,
the font and the finish (film grain, vignette, tint). `render.py` refuses a preset whose `palette_check` colours fail contrast or
colour-blind separation against the map background. Presets: `neutral` (the old fixed look), `1917_film` (aged paper, khaki, grey-green water,
blood-red front, serif type, sepia tint, vignette, per-frame grain).
Add a style: copy `styles/neutral.json` to `styles/<episode_style>.json` (letters, digits, underscore), change the values from the episode's
reference film (project rule 20), keep the palette_check colours distinct, set `style_preset` in the episode's specs. `tests/unit/test_maps_style_presets.py`
checks every preset in the folder.
