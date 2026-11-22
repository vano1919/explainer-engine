# PROPOSAL — map and 2.5D rules in skills and CLAUDE.md

For owner review. Do not paste into the repo files until approved. Source of truth: `docs/MAP_25D_RULES.md`.

## A. CLAUDE.md

Proposed paragraph to add under the v4.3 header:

> **Map and 2.5D rules:** read `docs/MAP_25D_RULES.md` before any map or 2.5D shot. The five camera moves — `truck`, `zoom_in`, `zoom_out`, `truck_zoom_in`, `truck_zoom_out` — apply to every map and 2.5D shot; no `orbit`, no `static`, one move per shot. The APPROVED map-font rule is Liberation Serif for the film presets, in place in the MapLibre lane styles; it is NOT yet in place in the raster renderer, which still uses Inter. A shot marked `"animated": true` must pass the no-melt gate (`qa/technical_gate.check_no_melt`), whose limits are PROVISIONAL and which fails closed when its numbers are missing. Film style is chosen per episode by the owner.

## B. `.claude/skills/cartography/SKILL.md`

Replacement for the font line in rule 8:

> **8. Our type, our art.** Map labels use the film preset’s font, Liberation Serif (APPROVED); the generic `neutral` style is excluded. This is in place in the MapLibre lane styles (`1917_film.json`, `truce_cold.json`). NOT yet in place in the raster renderer `explainer_engine/maps/draw.py`, which still uses `assets/fonts/Inter.ttf` (`MAP_FONT`). Plates are our own drawing over open data; no third-party map imagery (RIGHTS_AND_FAIR_USE).

Add one bullet list:

- **Camera moves (APPROVED):** exactly five are allowed — `truck`, `zoom_in`, `zoom_out`, `truck_zoom_in`, `truck_zoom_out`. No `orbit`. No `static`. One move per shot.
- **Bridges:** bridge captions repeat the narration’s words when they are said, timed from the word clock in `explainer_engine/maps/bridge_sync.py`; checks B1–B5 are PROVISIONAL and behind an env flag.
- **Big, readable map text (PROPOSAL):** the owner’s direction is rich maps with big, readable text. The numbers for “big” and “readable” are PROPOSAL T1–T10 in the `QUALITY_SPEC` draft (`plans_2026-11-21` on the HF vault), and need the owner’s approval on rendered samples.
- **Film style per episode:** each episode gets its film style, chosen by the owner. In code, map style and film finish come from the episode’s film file, `map.style_preset` in `explainer_engine/production/build_map_shot.py`; this is not yet recorded as a rule in `CLAUDE.md` or `docs/EPISODE_FIRST.md`.

## C. `.claude/skills/animation-principles/SKILL.md`

### No melting, no warping

A face is never warped. A shot marked `"animated": true` must pass the no-melt gate in `explainer_engine/qa/technical_gate.py` (`check_no_melt`), which measures residual motion per frame and residual drift and fails closed when its numbers are missing. The limits are PROVISIONAL. The measurement that feeds the gate is NOT yet wired end to end: `explainer_engine/qa/still_region.py` measures only and has no limits, and the camera-move compensation is not defined yet.

## D. `.claude/skills/shot-visuals/SKILL.md`

### Map and 2.5D shots

Use only the five APPROVED camera moves — `truck`, `zoom_in`, `zoom_out`, `truck_zoom_in`, `truck_zoom_out` — with one move per shot. No `static` and no `orbit`. Use the film style of the episode; map style and film finish come from the episode’s film file (`map.style_preset` in `explainer_engine/production/build_map_shot.py`), and the owner chooses that film style per episode.

## E. Applies to past videos

A rule added now is checked on new renders. Past videos are not re-rendered automatically. A re-check of past videos is MISSING and needs an owner decision; the owner’s direction is that a new rule applies to the skills, the code, and past videos, but that is not yet a repo rule.