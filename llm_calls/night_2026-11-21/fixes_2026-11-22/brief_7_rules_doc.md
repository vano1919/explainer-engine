Write the document docs/MAP_25D_RULES.md (Markdown, English, for the repo). Facts only; do not invent numbers, IDs or approvals. Use plain bullets, no new ID codes (the repo has a docs linter that enforces one home per ID).

Title: "Map and 2.5D rules (owner decisions and where each is enforced)". Status line: "Written 2026-11-22 from the owner's recorded decisions and the repo state. Proposals are marked PROPOSAL; nothing here is approved unless marked APPROVED."

Sections:

1. Camera. APPROVED: exactly five moves, truck, zoom_in, zoom_out, truck_zoom_in, truck_zoom_out; no orbit, no static, one move per shot. Enforced by explainer_engine/qa/delivery_gate.py (ALLOWED_CAMERA_MOVES), explainer_engine/maps/maplibre_spec.py (move values and the needs_center/needs_zoom rule), explainer_engine/fx25d/living.py (MOVES; orbit and static refused). Tests: tests/unit/test_camera_moves_agree.py, tests/unit/test_camera_move.py. Recorded in docs/PROGRESS.md under 2026-11-20.

2. Map palette. APPROVED by the creator on 2026-11-20 for the Truce 1914 episode: style "truce_cold" (explainer_engine/maps/maplibre_lane/styles/truce_cold.json, its note says so). The film look of the other style is 1917_film.json. Note: "#231" in older notes is a pull-request number (PROGRESS.md, 1917_film clip), not a colour.

3. Map font. APPROVED rule: map text uses the film preset's font, Liberation Serif. In place in the MapLibre lane styles (1917_film.json and truce_cold.json). NOT yet in place in the raster renderer explainer_engine/maps/draw.py, which uses assets/fonts/Inter.ttf (MAP_FONT). The test tests/unit/test_map_font_and_no_melt.py marks that as an expected failure until it is changed. The generic "neutral" style is not a film preset and is excluded from the rule.

4. Map text size and narration bridges. The owner's direction is rich maps with big, readable text, and bridge captions that repeat the narration's words when they are said. Implemented: bridge timing from the word clock (explainer_engine/maps/bridge_sync.py, checks B1–B5, PROVISIONAL, behind an env flag), bridge drawing (maps/bridge_render.py), narration-timed caption list in the map payload (maps/render.py, payload "bridges"). NOT approved yet: the numbers for "big" and "readable" (minimum label cap height, line widths, contrast, bridge size and hold). These are proposals T1–T10 in the QUALITY_SPEC draft (plans_2026-11-21 on the HF vault) and need the owner's approval on rendered samples.

5. No melting, no warping. Direction from the owner: animation must not melt or warp. Enforced now: a face is never warped (docs/EPISODE_FIRST.md RT-06; fx25d/living.py keeps each depth plane rigid). Gate: explainer_engine/qa/technical_gate.py check_no_melt (residual motion per frame and residual drift); it applies to a shot marked "animated": true and fails closed when its numbers are missing. The limits are PROVISIONAL (house proposals, no source; the owner approves them on rendered samples). The measurement that feeds the gate is NOT yet wired: explainer_engine/qa/still_region.py measures only and has no limits, and the camera-move compensation is not defined yet.

6. Film style per episode. Direction: each episode gets its film style; the owner chooses it. Enforced in code only: map style and film finish come from the episode's film file (explainer_engine/production/build_map_shot.py, map.style_preset). NOT recorded yet as a rule in CLAUDE.md or docs/EPISODE_FIRST.md; the owner's choice per episode is not yet a recorded decision.

7. Where the rules apply. Direction from the owner: a new rule applies to the skills, the code, and past videos. Status: MISSING as a repo rule. The skills (.claude/skills/cartography, animation-principles, shot-visuals) do not yet state these rules. Past videos have no re-check. The coverage table is llm_calls/night_2026-11-21/MAP_25D_RULES_COVERAGE_2026-11-22.md.

8. Still open for the owner: the numbers in section 4 and 5; confirmation of the film style choice per episode (section 6); whether the raster renderer must move to Liberation Serif now (section 3).

Keep the document under 180 lines. Do not claim anything passes. Do not write code.
