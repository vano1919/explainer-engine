# Truce 1914: minimal animated front (build_shot map demo)

`front.geojson` is a minimal front line traced by `explainer_engine/maps/trace_front_1914.py` from the public-domain West Point map
"Western front 1914" (HF `explainer-engine/sources/maps/Western_front_1914.jpg`, note `LICENSE.md` next to it): eight towns georeferenced the
picture by an affine fit (RMS in `properties.fit_rms_km`, about 9 km: approximate, conic projection). It is a drawing aid for an animated front, NOT a
claim source and NOT a surveyed line. `episode_film.json` is the demo film (`truce_cold`); replace it with the episode's real film.
Render: `python -m explainer_engine.production.build_shot examples/maps/truce_front_1914/spec.json out.mp4 --tile-dir <tiles>`
(tiles: `maplibre_lane/fetch_tiles.py`, boxes: z3-7 over -6 42 16 56, z7-8 over 0.5 46.5 9.5 52.5; playwright + Chromium + vendored maplibre-gl).
