# The visual compensator: maps, HUD and tableaux (CMP-)

Blueprint plan v2, phase P5. While the narrator speaks and no character is on screen, the picture still has to move with the
words. The compensator fills those stretches with free, deterministic frames that code draws from a spec: no model, no pod, no
paid call (CMP-14). This page is the one home of the `CMP-` ids; the contracts are in [CONTRACTS](CONTRACTS.md), the numbers in
[SOURCED_RULES](SOURCED_RULES.md) (BP-124, BP-125, BP-127, BP-140 to BP-146), the craft behind the maps in the `cartography` skill.

## What is where

| Piece | Path | Does |
|---|---|---|
| Map data | `explainer_engine/maps/data/` | the Natural Earth 1:50m extract (land, lakes, rivers, land borders; no names; public domain), its pinned sources and the build script |
| Map engine | `explainer_engine/maps/` | `geo` (projection, clipping, water test), `plate` (the letterless plate, its certificate), `camera`, `paths`, `render` (archetypes 1-4), `timeline` (words to frames), `laws` (the eight validators), `draw` (palette colours, canvas, easing) |
| HUD and graphs | `explainer_engine/edit/hud.py` | archetypes 5, 7, 10, 11, 12 |
| Cutaways and tableaux | `explainer_engine/edit/tableau.py` | archetypes 6, 8, 9 |
| Compensator | `explainer_engine/edit/visual_compensator.py` | the catalogue, the manifest check, rotation, map share, lane balance, the renderer, the measured table |
| Catalogue | `explainer_engine/edit/archetypes.json` | the one home of the twelve archetype ids, their lane and family, and the measured CPU seconds per frame |

An item is one `visual_comp_manifest/1` entry (the archetype, the shot, the spoken word that starts it, its length) and one
`comp_spec/1` file (what it draws and which word starts every change). A frame is `render_item_frame(spec, spine, trigger word,
length, frame number)`: a pure function, so a chunked render draws the same pixels (CMP-09). The spine (`audio_spine/1`) is the
clock: an event starts on the first frame of its word.

    python -m explainer_engine.edit.visual_compensator check <visual_comp_manifest.json> [--base <job folder>]
    python -m explainer_engine.edit.visual_compensator render <manifest> <item_id> <out dir> [--frames A:B] [--ss N]
    python -m explainer_engine.edit.visual_compensator measure <manifest> [--base <job folder>] [--write]
    python -m explainer_engine.maps.data.build [--from-dir <folder>] [--check]

## The twelve archetypes

Narration over a non-character stretch picks one of these; a played scene is never replaced by an archetype (a turn of the story
is a character beat, [BP-127](SOURCED_RULES.md)). Maps (1-4) run on the `MAP` lane, the rest on the `COMPENSATOR` lane of
`film_shots/2`.

| No | Id | Lane | Family | Drawn as |
|---|---|---|---|---|
| 1 | `MAP_3D_TERRAIN_FLYOVER` | MAP | map | a 2D vector map under an eased camera from the continent to the crossing (the ceiling, D-86) |
| 2 | `TACTICAL_UNIT_MANEUVER` | MAP | map | faction counters marching terrain-following curves, arrows that draw themselves on the spoken word |
| 3 | `FORMATION_MICRO_MECHANICS` | MAP | map | up to 500 proxies moving between formations, a flocking look that is a pure function of the frame |
| 4 | `LOGISTICS_TETHER_AND_ATTRITION` | MAP | map | a supply line going blue, amber, red and snapping; a strength bar driven by numbers |
| 5 | `BALLISTIC_RANGE_AND_ENERGY_HUD` | COMPENSATOR | hud | range rings, arcs, a metric stamp that locks in on the spoken number |
| 6 | `WEAPON_AND_MATERIAL_CUTAWAY` | COMPENSATOR | cutaway | a layered vector cross-section; layers peel back, heat and cracks overlay |
| 7 | `SPLIT_SCREEN_SPEED_RACE` | COMPENSATOR | hud | two panels race with millisecond counters |
| 8 | `PARALLAX_25D_TABLEAU` | COMPENSATOR | cutaway | four depth planes cut by the depth map (and a matte when there is one), a slow dolly, drifting dust |
| 9 | `PRIMARY_SOURCE_DOSSIER_CARD` | COMPENSATOR | cutaway | a tilted document with a rack focus, **without the stamp** (CMP-15) |
| 10 | `TECH_TREE_DEPENDENCY_GRAPH` | COMPENSATOR | graph | nodes light up, blocked paths stay grey |
| 11 | `ORDER_OF_BATTLE_TELEMETRY_HUD` | COMPENSATOR | hud | a transparent overlay whose counters tick to the numbers of the events |
| 12 | `MULTI_SCENARIO_VERDICT_MATRIX` | COMPENSATOR | graph | probability bars growing on their words |

Every number a frame shows is a number of its spec; the author of the spec traces it to a claim (invariant 5). The compensator
never invents one.

## The eight map laws

Hypotheses from the Blueprint (nothing here is binding until a second source type is opened), so every finding is REVIEW (D-59,
CN-11). The validator is in `explainer_engine/maps/laws.py`; each has a focused test in `tests/unit/test_maps.py`.

| ID | Law | Numbers | Validator |
|---|---|---|---|
| CMP-01 | No diffusion maps: a map is drawn from vectors and crisp type; a painted plate is the vector plate plus paint, with a certificate (no letters found by OCR, land not moved) | BP-146 | `no_diffusion`, `plate.certificate_findings` |
| CMP-02 | Terrain paths: routes follow the land, stay out of the no-go areas the spec names, and are eased (a march starts slow, cruises, halts at the line), never a constant-speed arrow | none | `terrain_paths`, `paths.validate` |
| CMP-03 | Signalling: at most 3 labels and 4 unit groups on screen, one change at a time with the changed thing flagged first, the inactive terrain dimmed round the active area | BP-124 | `signalling` |
| CMP-04 | Word lock: every element appears on a spoken word; nothing sits frozen from frame 1 | BP-140 | `word_lock` |
| CMP-05 | Scale progression: macro, meso, micro; an altitude change takes 4-8 s; the camera moves again within 8 s | BP-125, BP-141 | `scale_progression` |
| CMP-06 | Faction colours: the two palette tokens by side, never a literal colour, colour-blind safe, and told apart by a mark (square, triangle) too | BP-144 | `faction_colours`, `design/palette.py:faction_findings` |
| CMP-07 | Map to scene: the map ends at 45 degrees, exports its depth map, the next shot looks down at the same angle, the scene's sound starts 1 s early (the dissolve length is BP-31's) | BP-145 | `map_to_scene` |
| CMP-08 | Stimulus window: nothing is still for more than 4 s on a narrated stretch with no character | BP-140 | `stimulus_window` |

## The compensator's own rules

| ID | Rule | Basis | Checked by |
|---|---|---|---|
| CMP-09 | Same spec, same frame number, same bytes: no clock, no unseeded random, one PNG encoder setting | invariant 7, CN-07 | `tests/unit/test_maps.py`, `draw.png_bytes` |
| CMP-10 | Rotation: never the same archetype in two adjacent items; at most 2 of one family in any 120 s; a run of maps at most 90 s | BP-142 | `visual_compensator.rotation` |
| CMP-11 | Map share: pure maps (1-4) are at most 25 % of the runtime, flagged hard over 40 % | BP-143 | `visual_compensator.map_share` |
| CMP-12 | Lane balance: at most 60 s of non-character visuals without a character beat or a host line; no character scene over 90 s without a payoff | BP-127 | `visual_compensator.lane_balance` |
| CMP-13 | A date chip whenever map time advances | CRAFT-CART-03, ED-15 | `laws.date_chip` |
| CMP-14 | Every archetype is free: no network client, no model, no paid call in the compensator; a shot on the MAP or COMPENSATOR lane costs 0 | invariant 2, D-31 | `tests/unit/test_compensator.py` |
| CMP-15 | The dossier card has no stamp (HISTORICAL FACT / COUNTERFACTUAL): claim status lives in the claim map, not on screen | D-61, SC-11 | `tableau.validate_payload` |

`CN-15` ([CONTRACTS](CONTRACTS.md)) is the contract side: an archetype named by a shot, an item or a spec is one of the catalogue,
and on the lane its family belongs to.

## The plate, and where the paid restyle comes in

A plate is land, coast, lakes, rivers and borders in palette colours: no letters, by construction (CMP-01): the plate module never
calls the canvas's text method and its spec has no text field. Names, units, arrows and the date chip are drawn over it at the
frame the viewer sees, in the style bible's face. The same renderer draws a view of any span, so a close-up is as crisp as the
theatre map; the plate of a region is the view that frames its whole box.

P12e may paint a plate with Qwen-Image-2.1 and the `xworld_v2` style (paid, the creator's collage first). A painted plate is used
only with its certificate (`plate.certificate`): the OCR's count of letters (0) and the overlap of its land with the vector land
(at least BP-146's). Until then the vector plate is the picture. Nothing in this phase paints.

## The ceiling (D-86)

The Blueprint's flyover is a 3D relief over a height model; we have none, and a 3D pass would need Blender or a pod. The compensator's
ceiling is 2D vector maps plus 2.5D parallax. Archetype 1 is the 2D camera over the plate; when a shot needs the sense of depth,
archetype 8 (the parallax tableau) is the fallback, and the camera's depth export (`camera.zdepth`) is kept for the hand-over to a
scene (CMP-07).

## The parallax tableau and the matte

`production/depth.py` (Depth-Anything V2 Small, CPU) makes the depth map. The nearest plane can be cleaned by a matte of the subject:
BiRefNet is the planned maker (D-83 allows the larger models if a measurement shows they are better); its model is not in this phase,
the spec takes the matte PNG as an input, and without one the planes are cut by depth alone.

## Map data

Natural Earth is public domain ("Made with Natural Earth", naturalearthdata.com). The extract keeps four layers at 1:50m, no names,
two decimals (about a kilometre). `maps/data/SOURCES.json` pins the sha256 of every source file and of the extract;
`python -m explainer_engine.maps.data.build --check` rebuilds the extract from the pinned sources and says whether it is current.
1:50m draws a theatre map and a 50 km corridor well; a 1.5 km field is a coast, a river and a border at that scale, which is why the
micro view draws the counters and the formation, not the terrain.

## Measured time

`measure --write` stores the median seconds of CPU per frame of every archetype at 1280x720 (supersampled twice) in the catalogue's
`measured` block, with the machine named; the planner reads it with `availability()`. A frame is cheap (tens of milliseconds to a
fraction of a second on this container's CPU): a 30 s item at 24 fps is minutes, never a pod.

## Known limits and open items

- **Side marks.** A side is told apart by more than its colour: a square or a triangle on the counters and the formation proxies, and
  on a route a solid line with a solid head (side a) against a dashed line with a hollow head (side b). Rings, the supply line and the
  strength bar carry only the colour; they sit beside a labelled counter, and a colour-blind viewer still has the 112 or more of
  CIE76 between the two tokens (D-86).
- **The camera's tilt** (`camera.tilt`) squashes the picture vertically for the 45 degree hand-over; it is not a perspective
  transform. The depth export (`zdepth`) is the real hand-over; a perspective warp is a later refinement if a measured shot needs it.
- **The painted plate's overlap** (`plate.certificate`) is computed by the caller from the painted land mask and recorded as a number;
  the certificate check trusts that number and the file's hash, it does not recompute the overlap. The OCR count is the same.
- **A word before an item's trigger word** is an error (CN-01), not frame 0; an event cannot start before its item.
- **CMP-08's cadence** (the next change within the upper end of the 2.0-3.5 s window) is reported as INFO: camera drifts, pulses and
  counters change the picture between events, so only the 4 s still-flag (BP-140) is REVIEW.
- **Numbers that differ from the research record.** `p4_variants.json` summarises the Blueprint loosely; the registry's numbers are
  the Blueprint's own text: the 2.0-3.5 s window of BP-140, the 4 s lower end of the altitude change (BP-125, BP-141) and the 0.40
  hard flag of BP-143. All are hypotheses (REVIEW only, D-59) until a second source type is opened.
- **BP-127's dramatisability score** is not implemented here (the planner, P3); only its two caps are, in `lane_balance`.
- **Open acceptance criteria of the P5 card:** the OCR count of 0 letters on a plate is tested by construction (the plate never calls
  the text method) and by tesseract where it is installed, but no OCR engine ran in this phase; and the compensator frames of the
  Napoleon demo job are not rendered, because the demo's specs and audio spine belong to the pilot (P12b/P0c). The twelve archetypes
  render from the synthetic job in `tests/unit/_comp.py`.

## Not in this phase

Painting the plates and the hosts (P12e), the shot router and lanes (P6), the staging and cuts (P7), the planner's variants and
profiles (P3), the critic's rows CRAFT-CART-02 and -06 (P8), and the sound of the map's events (P4: `sound_mix_manifest/1` carries
it; the compensator only names the event's word).
