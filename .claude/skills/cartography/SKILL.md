---
name: cartography
description: Design the maps of a Crossworld Theories episode (campaign maps, fronts, routes, territories, animated map moves) so the viewer reads them at a glance - simple frames, one change at a time, labels that never fight the lines, colour-blind-safe palettes, a date whenever time moves, and our own type. Use for every map shot, map plate, map animation or HUD-over-map, and whenever a map looks busy, unreadable or like a GIS screenshot.
---

# Cartography: maps the eye reads in one look

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role image` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Department page of the craft curriculum (P3b, [CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)). The map code comes in P5
(`explainer_engine/maps/`: one letterless plate per region, Natural Earth vectors, PIL/numpy); this page is the judgement it
will follow. Sources are in `docs/research/CRAFT_SOURCES_2026-10.md` section 6: Harrower's "Tips for Designing Effective
Animated Maps" (2003) is the one primary text opened; Imhof's label rules came through secondary summaries; ColorBrewer was
opened; Brewer's and MacEachren's books were not. Nothing below is binding yet.

## Why maps fail on video

A viewer cannot pause to study a map the way a reader studies an atlas. Harrower: in an animated map "small details are
unlikely to be noticed", and motion competes with every other visual variable for attention (MacEachren, cited there). So a
map frame is a sentence, not a page.

## The rules

1. **A simple frame.** Few labels, few unit symbols, the inactive terrain dimmed so the live area pops (BP-124). If a frame
   needs more, it is two frames.
2. **One change at a time, flagged first.** Highlight what is about to change (a pulse, a brighter edge), then move it; never
   move two fronts at once (BP-124). Change blindness is the reason.
3. **Time is visible.** Whenever map time advances, a date chip or counter shows it (ED-15's counter slot); a short event is
   held long enough to be seen (Harrower's temporal exaggeration).
4. **Labels obey the lines** (Imhof): a label never crosses a river, road or border; it keeps one consistent offset and a
   halo; its size and style follow the feature's class (a city is not an army); type is at least P-64's size at delivery.
5. **Colour carries meaning, never alone.** Quantities use a sequential or diverging palette, categories a qualitative one,
   faction pairs are colour-blind safe and also differ by pattern or shape (D-22); every colour lives in
   `design/palette.json`.
6. **One map language per episode.** One projection, north up, a scale bar on every meso and micro map, a legend only when
   there are more than two symbol classes.
7. **Altitude moves are eased and timed.** Macro to meso to micro takes BP-125's duration; a faster drop reads as a jump.
8. **Our type, our art.** Map labels use the style bible's faces (Fredoka, Inter); the Blueprint's Calibri / Cinzel set is
   conflict 9 of the curriculum. Plates are our own drawing over open data; no third-party map imagery (RIGHTS_AND_FAIR_USE).
9. **Maps are a lane, not the video.** A map run without a character beat stays inside BP-127's cap; see the
   `shot-visuals` skill for the lane balance.

### CHECKLIST (cartography)

Rendered from `explainer_engine/standards/craft_checklists/cartography.json` (the one home of these ids;
`python -m explainer_engine.standards.craft write` regenerates it, `tests/unit/test_craft_checklists.py` fails when they
differ). Every row is a hypothesis until a second source type is verified.

<!-- craft-checklist:cartography:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-CART-01 | code | an animated map frame stays simple: label and unit caps, inactive terrain dimmed | map layer manifest per frame | BP-124 | `explainer_engine/maps/` (planned, P5) |
| CRAFT-CART-02 | critic | one change at a time; the changed thing is highlighted before it moves | map animation steps | BP-124 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-CART-03 | code | a temporal legend or date chip whenever map time advances | map animation steps + counters | ED-15 | `explainer_engine/maps/` (planned, P5) |
| CRAFT-CART-04 | eye | labels never cross a line feature, keep one offset and a halo, size by feature class | the rendered map frame | P-64 | manual |
| CRAFT-CART-05 | code | quantitative layers use sequential or diverging palettes; faction pairs are colour-blind safe and never colour-only | map layer palette (design/palette.json) | D-22 | `explainer_engine/design/palette.py` (planned, P5) |
| CRAFT-CART-06 | critic | one projection and north-up per episode; a scale bar on every meso and micro map; a legend only with more than two symbol classes | map plate set of the episode | - | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-CART-07 | code | a change of map altitude takes its eased duration | map camera keyframes | BP-125 | `explainer_engine/maps/` (planned, P5) |
| CRAFT-CART-08 | eye | map type is the style bible's (Fredoka, Inter), not the Blueprint's set | map label fonts | - | manual |
<!-- craft-checklist:cartography:end -->

## Sourced rules (docs/SOURCED_RULES.md)

The numbers of this page live only in the registry (D-59); code reads them with `sourced_rules.T`.

- BP-124: label and unit caps per frame, the dim of inactive terrain, one change at a time (hypothesis, REVIEW).
- BP-125: the eased duration of a map altitude change (hypothesis, REVIEW).
- BP-127: the run cap of non-character visuals, maps included (hypothesis, REVIEW).
