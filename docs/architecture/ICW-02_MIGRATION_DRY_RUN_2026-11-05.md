# film_shots/1 and /2 -> film_shots/3: migration dry run

Roadmap 10.3 (ICW-02). Regenerate with

    python scripts/migrate_film_shots_2_to_3.py tests/fixtures/migrate_film_shots/film_shots_2_all_lanes.json tests/fixtures/contracts/film_shots_2/valid.json tests/fixtures/contracts/film_shots_2/review__geometry.json tests/fixtures/contracts/film_shots_2/invalid__host_lane.json tests/fixtures/contracts/film_shots_2/invalid__3d_lane.json examples/film_shots/bus_in_the_ice_age.json --report <this file>

A dry run writes no card. The Napoleon example's own report is `examples/napoleon_vs_genghis/migration_report.md`.

### `tests/fixtures/migrate_film_shots/film_shots_2_all_lanes.json`

- film_shots/2 -> film_shots/3, 8 shots; fps 24 -> 24; frame 2560x1440 (BP-167)
- style fields dropped (legacy prompt route, D-100/D-105): trigger, video_sentence; added house_look ink_chronicle + bible_version
- lane ATMOS_BROLL -> VIDEO_3D: 1
- lane COMPENSATOR -> HELPER: 1
- lane COMPENSATOR -> STILL_3D: 1
- lane DIALOGUE_CU -> VIDEO_3D: 1
- lane KEYFRAME_LTX -> STILL_3D: 1
- lane KEYFRAME_LTX -> VIDEO_3D: 1
- lane MAP -> HELPER: 1
- lane STILL_HOLD -> STILL_3D: 1
- still_mode camera_move_3d: 1
- still_mode hold: 1
- still_mode parallax_25d: 1
- render_profile eevee_fast: 1
- render_profile eevee_full: 5
- lipsync shots: 1; spoken lines covered off screen: 0
- BP-109 runtime shares before -> after: video 37.5% -> 37.5%, still 37.5% -> 37.5%, helper 25.0% -> 25.0% (unchanged)
- archetype: null on every shot (the shot designer assigns 1-20, ICW-03)

### `tests/fixtures/contracts/film_shots_2/valid.json`

- film_shots/2 -> film_shots/3, 2 shots; fps 24 -> 24; frame 2560x1440 (BP-167)
- style fields dropped (legacy prompt route, D-100/D-105): trigger, video_sentence; added house_look ink_chronicle + bible_version
- lane KEYFRAME_LTX -> STILL_3D: 2
- still_mode hold: 2
- render_profile eevee_full: 2
- lipsync shots: 0; spoken lines covered off screen: 0
- BP-109 runtime shares before -> after: video 0.0% -> 0.0%, still 100.0% -> 100.0%, helper 0.0% -> 0.0% (unchanged)
- archetype: null on every shot (the shot designer assigns 1-20, ICW-03)

### `tests/fixtures/contracts/film_shots_2/review__geometry.json`

- film_shots/2 -> film_shots/3, 2 shots; fps 24 -> 24; frame 2560x1440 (BP-167)
- style fields dropped (legacy prompt route, D-100/D-105): trigger, video_sentence; added house_look ink_chronicle + bible_version
- lane KEYFRAME_LTX -> STILL_3D: 2
- still_mode hold: 2
- render_profile eevee_full: 2
- lipsync shots: 0; spoken lines covered off screen: 0
- BP-109 runtime shares before -> after: video 0.0% -> 0.0%, still 100.0% -> 100.0%, helper 0.0% -> 0.0% (unchanged)
- archetype: null on every shot (the shot designer assigns 1-20, ICW-03)

### `tests/fixtures/contracts/film_shots_2/invalid__host_lane.json`

- REFUSED: shot s1: lane HOST_COMMENTARY is refused, no permanent hosts (D-89, card A1 NO)

### `tests/fixtures/contracts/film_shots_2/invalid__3d_lane.json`

- REFUSED: shot s1: lane DRAMA_BLOCKED_3D is refused, the refused 3D-blocking lane of /2 (D-75/D-77, D-106): its intent on /3 is VIDEO_3D + an archetype

### `examples/film_shots/bus_in_the_ice_age.json`

- film_shots/1 -> film_shots/3, 6 shots; fps (none, /1) -> 24; frame 2560x1440 (BP-167)
- style fields dropped (legacy prompt route, D-100/D-105): trigger, video_sentence; added house_look ink_chronicle + bible_version
- lane (none, /1) -> VIDEO_3D: 6
- render_profile eevee_full: 6
- lipsync shots: 2; spoken lines covered off screen: 0
- default: lens_tier, focal_xy, refs (/1 card): 6
- BP-109 runtime shares before -> after: video 100.0% -> 100.0%, still 0.0% -> 0.0%, helper 0.0% -> 0.0% (unchanged)
- archetype: null on every shot (the shot designer assigns 1-20, ICW-03)
