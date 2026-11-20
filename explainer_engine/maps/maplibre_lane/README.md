# MapLibre lane (offline map shots, G-04c)

Spec (`maplibre_spec.py`) -> offline tiles (`fetch_tiles.py`, one-time, free, OpenFreeMap + Terrarium DEM) -> headless Chromium (Playwright) draws
`page.html` frame by frame (`render.py`) -> ffmpeg. Camera: only truck, zoom_in, zoom_out, truck_zoom_in, truck_zoom_out (no orbit, tilt, rotation).

Setup: `pip install playwright` (Chromium, or `EXPLAINER_CHROMIUM=<path>`), `maplibre-gl.js/css` into `vendor/` (see `vendor/README.md`).
Tiles: `python -m explainer_engine.maps.maplibre_lane.fetch_tiles --bbox W S E N --min-zoom 3 --max-zoom 8 --dem-max-zoom 8 --tile-dir <dir> --yes`
(repeat with other boxes/zooms: the manifest is merged). Fetch the DEM with a margin around the whole camera path: hillshade exists only
inside the DEM bounds of the deepest zoom. `EXPLAINER_MAP_DEBUG=1` prints browser console, failed requests and page errors.

## Episode map style (creator 2026-11-20: every episode has its own film; the map takes its style only from it, G-06)
A shot spec names the episode film: `"film_file": "episode_film.json"` (REQUIRED, absolute or next to the spec). The film's `map.style_preset` picks `styles/<name>.json`; there is no default style and the page has no look of its own. `style_preset` in the spec is optional and must equal the film's. The font always comes from the preset (`font` in the spec: absent or `"preset"`).
A preset sets the map colours (background, water, waterways, land cover, border with dash, roads, hillshade), the front line, the HUD colours,
the font and the finish (film grain, vignette, tint). `render.py` refuses a preset whose `palette_check` colours fail contrast or
colour-blind separation against the map background. Presets: `neutral` (the old fixed look), `1917_film` (aged paper, khaki, grey-green water,
blood-red front, serif type, sepia tint, vignette, per-frame grain).
Add a style: copy `styles/neutral.json` to `styles/<episode_style>.json` (letters, digits, underscore), change the values from the episode's
reference film (project rule 20), keep the palette_check colours distinct, set `style_preset` in the episode's specs. `tests/unit/test_maps_style_presets.py`
checks every preset in the folder.

## HUD readability check
`python -m explainer_engine.maps.maplibre_lane.hud_ocr <spec.json> <frames_dir> [step]` (needs `pip install rapidocr-onnxruntime`): OCR reads back what the schedule says is on screen
(counter, label, date, towns). Scene-text OCR cannot read an isolated single glyph (measured: even a plain black "0" or "8" on white), so a
one-character counter ("0" at the start) is checked as ink in the preset's counter colour, and the report says which method decided each item.
