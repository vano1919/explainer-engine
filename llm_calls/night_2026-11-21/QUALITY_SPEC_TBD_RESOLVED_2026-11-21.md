# QUALITY_SPEC: TBD paths and fields resolved from the repo (free, read-only)

Source: plans_2026-11-21/QUALITY_SPEC.md (DRAFT, Fable 5.2). Thresholds T1–T10 are NOT touched here; they stay PROPOSALs for the owner on rendered samples.
Each line says what the repo actually has, checked with grep on branch claude/project-thread-3j9l41-modal-render.

| Spec item | Was TBD | Resolved to | Status |
|---|---|---|---|
| Map renderer | section 2 | explainer_engine/maps/render.py (render_frame) | found |
| Map presets | section 2 | explainer_engine/maps/render_presets.py + maps/quality_options/map_presets.json | found |
| Film font (M6, B6) | font name | maps/maplibre_lane/styles/1917_film.json (style file) | path found, name to read from file |
| Film palette (T5) | palette | explainer_engine/design/palette.json | found |
| Bridge module (section 3) | path | maps/bridge_render.py (draw, visible_at), maps/bridge_sync.py (find_bridge, bridge_window, check_*) | found |
| Word timing (B1–B5) | schema | bridge_sync reads items with "word" plus start/end timing; exact keys in _timing() in bridge_sync.py | partly, to confirm against production_script.json (not in repo) |
| Map spec and validator (section 4) | path | explainer_engine/maps/maplibre_spec.py; camera move rule in explainer_engine/qa/delivery_gate.py (ALLOWED_CAMERA_MOVES, camera.move field) | found |
| Five camera moves (C1) | field | camera.move (delivery_gate.py lines 68 and 95) | found; matches the five strings exactly |
| Still-region measure (section 5) | qa/still_region.py | explainer_engine/qa/still_region.py (measure only, no limits; PR 251) | found |
| Delivery gate (N4) | path | explainer_engine/qa/delivery_gate.py | found |
| map_receipt.json, fx25d_receipt.json (N1–N4, A2) | fields | not found by name in explainer_engine | NOT FOUND: owner or coordinator must confirm the names |
| Photo and human region marks (N1–N4) | mask source | not found as a spec; person mask today is a --person-mask image in fx25d/living.py (measurement only) | NOT FOUND; open |
| Effect allowlist (A1, A2): clouds, fire, smoke, light | field and code | no allowlist of these four types found; living.py has smoke, clouds, snow, mist, cloth, breath effects with no declared-type field | NOT FOUND: rule A1 cannot be enforced yet |
| Melt/warp negative fixture (N5) | location | no fixture found on main; test_no_melt_provisional exists on the P6 branch (f3d000bd) | on P6 branch only |
| Google Doc (section 8) | content | not readable from here; not used | open |

Also noted in the spec itself: section 7 row T9 is cut off in its Status cell; T10 follows it.

Open for the owner (unchanged from the draft): static shot allowed? rule for every shot or map only? M5 reading? opacity fades allowed? light crossing protected regions?
