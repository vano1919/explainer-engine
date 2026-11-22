# Owner rules for maps and 2.5D: where each one is written in the repo (checked 2026-11-22)

Read-only check. No code changed. Status: IN REPO (written and enforced or tested), PARTIAL (written, not enforced or not complete), MISSING (not found in the repo; only in the team memory note or not written at all).

| # | Owner rule | Where it is in the repo | Status | What is missing |
|---|---|---|---|---|
| 1 | Maps: rich, big text, narration bridges | Bridge timing and checks: explainer_engine/maps/bridge_sync.py (B1–B5, provisional, env flag). Bridge drawing and narration timing: maps/bridge_render.py, maps/render.py (payload.bridges, tonight). Sizes: QUALITY_SPEC.md T1–T10 (plans_2026-11-21 on HF, DRAFT). | PARTIAL | "Rich" and "big text" are only proposals (T1–T4, T7) waiting for the owner's approval on samples; no approved numbers in CLAUDE.md or code. |
| 2 | Map palette: C cold, truce_cold preset | explainer_engine/maps/maplibre_lane/styles/truce_cold.json (line 2–3: "chosen by the creator 2026-11-20"). Map presets: maps/quality_options/map_presets.json (bold/balanced/light, tonight). | IN REPO | "#231" in the memory note is ambiguous: in PROGRESS.md:3834 #231 is a PR number (1917_film, truck_zoom_in), not a colour. Confirm which. |
| 3 | Font: Liberation Serif | maplibre_lane/styles/1917_film.json:4 and truce_cold.json:4 ('Liberation Serif', …). | IN REPO (style files) | No test asserts the font of every map label; M6 in QUALITY_SPEC is still a proposal. |
| 4 | Animation: no melting, no warping | EPISODE_FIRST.md RT-06 (a face is never warped; each plane moves by one affine transform). QA checks for melting exist in the legacy video QA (PROGRESS.md:1025–1040, 2026-10-23). Measurement only: qa/still_region.py (no limit). Negative fixture: only on the P6 branch (test_no_melt_provisional). | PARTIAL | No gate on main that blocks melting or warping for the 2.5D and map shots; the limit is missing (QUALITY_SPEC N1–N5 proposal). |
| 5 | Camera: only truck, zoom_in, zoom_out, truck_zoom_in, truck_zoom_out | qa/delivery_gate.py:8 (ALLOWED_CAMERA_MOVES); maps/maplibre_spec.py:26, 62–63; fx25d/living.py:61 (MOVES, orbit and static refused); tests/unit/test_camera_moves_agree.py, test_camera_move.py. Recorded in PROGRESS.md:3826 (2026-11-20). | IN REPO | The skills (cartography, animation-principles, shot-visuals) do not state the five moves. |
| 6 | Film style per episode, the owner picks it | Map style per episode: explainer_engine/production/build_map_shot.py ("map.style_preset"); episode_film.json in examples/. Recorded in progress.d/2026-11-21-claude-project-thread-9q7k0h.md (map rework v3). | PARTIAL | No decision record that the owner picks the style per episode, and no rule in CLAUDE.md or EPISODE_FIRST.md. |
| 7 | "Not in the film style, not animated" (map rework v3) | progress.d/2026-11-21-claude-project-thread-9q7k0h.md: film post-process, arrows, truck_zoom_in camera, refusal of a map spec without camera. | IN REPO (implemented on that branch) | Map shots still route through the legacy vector renderer (edit/router.py, visual_compensator.py); stated as NOT done in that fragment. |
| 8 | Rule applies to skills, code and past videos | Not written as a rule anywhere in the repo. | MISSING | Skills do not state the no-melt or the bridge rule; past videos have no re-check. |

## Gaps the owner should see before the next map test
- Rules 1, 4 and 6 are not in CLAUDE.md, EPISODE_FIRST.md or DECISIONS_AND_OPEN_QUESTIONS.md as decided rules. They exist as proposals or memory notes only.
- Rule 8 (propagation to skills, code and past videos) has no record and no check.
- Rule 2: "#231" needs a clear answer (colour or PR).

## Source of truth used
CLAUDE.md, docs/EPISODE_FIRST.md, docs/DECISIONS_AND_OPEN_QUESTIONS.md, docs/PROGRESS.md (2026-10-23, 2026-11-20), progress.d/*.md, .claude/skills/cartography, animation-principles, shot-visuals, editing-style, code and tests as listed above. The team memory note on the owner's map decisions was used only as the list of rules to check; it is not a repo source.
