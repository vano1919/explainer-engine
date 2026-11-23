---
name: cartography
description: Plan and judge the map shots of a history docudrama episode - route map_action, about a tenth of the runtime, made last once the read and the other routes exist - drawn in Python over a letter-free relief plate with an action layer timed to the spoken word, one change at a time, a date whenever time moves, colour-blind-safe faction colours, our own type, and front lines shown as illustrative unless a verified open dataset backs them. Use for every map_action shot, its actions and places, when a map looks busy, wrong or like a GIS screenshot, and before a map number or front line goes on screen.
---

# Cartography for map_action shots (layer L15, stage G7a)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the v4.3 episode-first route
(D-131): one map route, drawn by our own code, free, and made last.

Legacy note (the 2026-11-05 Ink Chronicle banner, kept for episodes made before D-131): the HELPER lane through the style
bridge (D-97, D-112), the Blender terrain benchmark, and the keyframe, sprite and 2.5D-still map wording of the old
image-generation route (D-43, D-80, D-105) are legacy and do not apply to a v4.3 episode.

**The rulebook speaks first (D-51, OR-11):** run `python -m explainer_engine.standards brief <episode>/episode_rules.json
--role image` and obey it; licence and data-use questions are settled there (docs/EPISODE_STANDARDS.md). A clash goes
back to the orchestrator.

## Where maps sit in a docudrama

The episode alternates reenactment (`video`), living photograph (`still_25d`) and the map (`map_action`). The map is the
register for "where" and "how far": routes, fronts, spread, distances, counts. By duration it is about 10 % of the runtime
(the D-131 target; `explainer_engine/episode/router.py` measures it by seconds, never by shot count, RT-04). It is a guide,
not a quota: an episode with little geography has fewer maps, and a map is never filler between two scenes.

## Maps are made last

Map shots are designed and rendered after everything they depend on exists:
1. **After the read (G6).** Every action starts on a spoken word (`actions[].at_word`, RT-03) and lasts its words (MA-05);
   until the Scribe clock exists the frames are guesses.
2. **After the reenactment and living-photograph shots are planned.** The map takes the moments where geography is the
   point; the scene shots around it decide what the viewer already knows and what the map must add.
3. **After the claim map is final.** Every number and every line shown on a map names its claim (MA-04).
So in the runner the maps are G7a, but in the planning order they come last, and a script change that moves a word
re-renders the map (the clip cache key holds the word spine, MA-08).

## What a map shot is made of

- **The plate:** land, coast, lakes, rivers and borders in palette colours, letter-free by construction (CMP-01), from
  Natural Earth vectors and Natural Earth's shaded relief raster (never invented terrain). Code: `explainer_engine/maps/plate.py`,
  `explainer_engine/maps/relief.py` (the raster is fetched once by `python -m explainer_engine.production.relief_fetch`).
- **Places:** lon/lat entries in `episode.json` `places`; every action names them by id.
- **The action layer** (`explainer_engine/maps/actions.py`): `route_arrow`, `front_line`, `spread`, `plume`, `pulse`,
  `highlight`, `label`, `counter`, `zoom`, `split_compare`, and since W3 `marker_travel`, `supply_line` with its states and
  `snap`, `bar_grow`, `progress_bar`, `milestone` (MA-01..MA-08 in docs/EPISODE_FIRST.md). A route with `via` follows its
  waypoints (`explainer_engine/maps/paths.py`).
- **The camera:** each action may ask for hold, push, pull, route pan, fly-to or scale; a dense map holds (MA-06). The view
  keeps a restrained drift so a narrated map is never frozen (MA-07, CMP-08).
- **The clip:** `explainer_engine/production/map_clip.py` encodes the frames; every frame is a pure function of the plan
  and the frame number, so chunked renders match (CMP-09).

## Front lines and borders: illustrative unless sourced

- A `front_line` from place A to place B is a **schematic** of where two sides stood. It is shown as illustrative: the
  narration says "roughly", "along", "near", never an exact line, and the claim row says the line is drawn by us.
- A front, border or territory is traced exactly **only when a verified open dataset** backs it: a named source with its
  licence (one informational line, never a blocker), URL and sha256 recorded in `explainer_engine/maps/data/SOURCES.json`,
  and its date matching the date chip. The bundled 1914 borders are borders on one date, not front lines.
- Never trace a line from a third-party map image, an atlas scan, a game map or a film still; our plates are our own
  drawing over open data (docs/RIGHTS_AND_FAIR_USE.md).

## The reading rules (the eye gets one look)

1. **A simple frame.** Few labels and unit groups, inactive terrain dimmed round the live area (BP-124, CMP-03). A frame
   that needs more is two frames.
2. **One change at a time, flagged first:** pulse or brighten what is about to move, then move it; never two fronts at
   once (BP-124).
3. **Time is visible.** A date chip whenever map time advances (ED-15, CMP-13); a short event is held long enough to see.
4. **Labels obey the lines:** no label crosses a river, road or border; one offset, a halo, size by feature class, at least
   P-64's size at delivery.
5. **Colour never alone.** Sequential or diverging palettes for quantities, qualitative for categories; the two faction
   tokens are colour-blind safe and also differ by mark (D-22, CMP-06). Every colour lives in
   `explainer_engine/design/palette.json`.
6. **One map language per episode:** one projection, north up, a scale bar on meso and micro views, a legend only past two
   symbol classes.
7. **Altitude changes are eased and timed** (BP-125, CMP-05).
8. **Our type and art:** the map face is Inter (the style bible's set; Fredoka for display), never the Blueprint's set.
9. **A map run has a cap** without a character beat (BP-127, CMP-12); the next shot returns to people.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| The render stops on a word | `at_word` not in the shot's line, or out of order | fix the word or the line (RT-03); re-run after G6 |
| A route crosses the sea it should hug | no `via` waypoints | add `via`; `paths.validate` reports it |
| The map looks like a GIS screenshot | too many labels, full-strength terrain | dim, cut labels to the live ones, one change per beat |
| A counter shows a number nobody sourced | no `claim` on the action | add the claim id or drop the number (MA-04) |
| A front looks precise but is guessed | schematic shown as fact | soften the line's words; mark illustrative in the claim map |
| Colours clash for colour-blind viewers | literal colours | palette tokens; `python -m explainer_engine.design.palette` |

### CHECKLIST (cartography)

The table below is generated from `explainer_engine/standards/craft_checklists/cartography.json`, its only home; rerun
`python -m explainer_engine.standards.craft write` after a change there (`tests/unit/test_craft_checklists.py` compares the
two). Each row stays a hypothesis until a second source type backs it.

<!-- craft-checklist:cartography:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-CART-01 | code | an animated map frame stays simple: label and unit caps, inactive terrain dimmed | map layer manifest per frame | BP-124 | `explainer_engine/maps/laws.py:signalling` |
| CRAFT-CART-02 | critic | one change at a time; the changed thing is highlighted before it moves | map animation steps | BP-124 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-CART-03 | code | a temporal legend or date chip whenever map time advances | map animation steps + counters | ED-15 | `explainer_engine/maps/laws.py:date_chip` |
| CRAFT-CART-04 | eye | labels never cross a line feature, keep one offset and a halo, size by feature class | the rendered map frame | P-64 | manual |
| CRAFT-CART-05 | code | quantitative layers use sequential or diverging palettes; faction pairs are colour-blind safe and never colour-only | map layer palette (design/palette.json) | D-22 | `explainer_engine/design/palette.py:faction_findings` |
| CRAFT-CART-06 | critic | one projection and north-up per episode; a scale bar on every meso and micro map; a legend only with more than two symbol classes | map plate set of the episode | - | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-CART-07 | code | a change of map altitude takes its eased duration | map camera keyframes | BP-125 | `explainer_engine/maps/laws.py:scale_progression` |
| CRAFT-CART-08 | eye | map type is the style bible's (Fredoka, Inter), not the Blueprint's set | map label fonts | - | manual |
<!-- craft-checklist:cartography:end -->

## Sourced rules (registry ids this page cites)

Numbers live only in `explainer_engine/standards/sourced_rules.json` (D-59); code reads them through `sourced_rules.T`, and
`explainer_engine/maps/laws.py` turns a miss into a REVIEW finding.

- BP-124: label and unit caps per frame, the dim of inactive terrain, one change at a time (hypothesis, REVIEW).
- BP-125: the eased length of an altitude change (hypothesis, REVIEW).
- BP-127: the run cap of non-character visuals, maps included (hypothesis, REVIEW).

## Background and history

Department page of the craft curriculum (P3b, [CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)); the map code arrived in
P5. Sources are in `docs/research/CRAFT_SOURCES_2026-10.md` section 6: Harrower's 2003 tips on animated maps were opened,
Imhof's label rules came through summaries, ColorBrewer was opened, Brewer's and MacEachren's books were not. The editorial
critic named in the checklist is `explainer_engine/qa/editorial_review.py` (planned, P8). For the lane balance of older
episodes see the `shot-visuals` skill in the archive.


## Episode Film Font Rule (OR-F04)
Map typography follows the active episode film preset (`episode_film.py`, OR-F04) rather than a hardcoded style bible face.
