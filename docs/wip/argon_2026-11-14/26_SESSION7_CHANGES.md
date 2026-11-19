# CHANGES.md — Scene Director Steps 1–3 (D1–D4)

## Summary of Changes

1. **D1 — Director Knowledge Base & 16 Truce 1914 Fixtures**:
   - Added `explainer_engine/standards/director_knowledge_base.json` trimmed from `18_director_knowledge_base.json` to the three runtime sections read by the code: `camera_feasibility_rules`, `variety_and_continuity_rules`, and `idiom_grammar`.
   - Added `tests/fixtures/truce_1914_examples.json` preserving all 16 Truce 1914 example rows (`S01_SH001` through `S08_SH003`) as unit-test fixtures.

2. **D2 — Picture Geometry (`understand.py`) & Rigid 2D Window Pan (`directed25d.py`)**:
   - `explainer_engine/production/understand.py`:
     - Added `GEOMETRY_KEYS` (`person_boxes`, `edge_margin_x`, `edge_margin_y`, `sky_area_pct`, `fg_bg_depth_delta`, `unlayered_people`) and pure helper `picture_geometry(manifest, seen, *, depth=None, masks=None, faces=None, d=None)` that either reads existing manifest fields or computes them from `manifest` + `seen` (and optional depth/masks/faces arrays).
     - Updated `understand()` to compute and write `person_boxes`, `edge_margin_x`, `edge_margin_y`, `sky_area_pct`, `fg_bg_depth_delta`, `unlayered_people` (plus `edge_alignment` and per-object `box`) into `manifest.json`.
   - `explainer_engine/production/directed25d.py`:
     - Added `"pan_crop_2d"` to `CAMERA_OPS` and `PAN_CROP_OVERSCAN = 1.10`.
     - Updated `Stage._fit_zoom()` to enforce at least `overscan` (default `1.10`) when a `pan_crop_2d` camera segment is planned.
     - Updated `Stage.view()` and `Stage.render()` to support `pan_crop_2d` as a rigid 2D window pan across the overscanned source image with zero z-parallax (`dp = 0`, `tx = 0`, `ty = 0`, `ox = 0`, `no_parallax = True`) and zero reveal of inpainted fill (`fill = 0`).

3. **D3 — Feasibility, Variety & Audit in `living_director.py` and `direction.py`**:
   - `explainer_engine/production/direction.py`:
     - Added `"pan_crop_2d"` to `CAMERA_OPS` and `MOVING_CAMERA`, and passed `overscan`, `from_xy`, `to_xy` through `resolve()`.
     - Added `load_knowledge_base()` to load and cache `explainer_engine/standards/director_knowledge_base.json`.
     - Added `_feasibility(d, manifest=None)` and `_audit_present(d)` to `check()`: emits `FAIL` only for the creator's veto (an angle-change move `orbit`/`orbit_small`/`truck`/`truck_25d` on a shot with people near the lateral edge or unlayered crowd) and `REVIEW` for hypothesis thresholds (D-59) or missing `choice.audit`.
   - `explainer_engine/production/living_director.py`:
     - Extended `choose_camera` (and `direct`) with optional `prev_direction=None`, `next_shot=None`, `episode_state=None`, `manifest=None`.
     - Added `classify_idiom()` and `_evaluate_feasibility()` driven by `director_knowledge_base.json` and `understand.picture_geometry()`.
     - Vetoed lateral angle-change moves (`orbit`/`truck`) when people would be cut or are unlayered, downgrading lateral group-to-group moves to `pan_crop_2d` and single-subject portrait/insert moves to `push` + `rack_focus`.
     - Enforced `no_two_same_camera_ops_in_a_row` (`CAM-VAR-01`) and `max_push_in_in_5_shot_window` (`<= 2` pushes in any 5 consecutive non-map shots, `CAM-VAR-02`).
     - Populated `choice.audit` (`idiom`, `chosen`, `rejected` with reasons, `measurements` used).

4. **D4 — Regenerated Six Direction Files**:
   - Regenerated `S01_SH001.direction.json`, `S02_SH008.direction.json`, `S05_SH016.direction.json`, `S05_SH020.direction.json`, `S06_SH001.direction.json`, and `S08_SH002.direction.json` from their `seen` blocks, manifests, and script narration.
   - `S05_SH020.direction.json` vetoes `orbit_small` and `truck_25d` (`edge_margin_x = 0.115`, `unlayered_people = True`, 11 kept faces) and uses `pan_crop_2d` (`from_xy: [0.3, 0.514]`, `to_xy: [0.717, 0.533]`, `overscan: 1.1`) for the group-to-group move on `"student"`.

5. **Unit Tests (`tests/unit/test_director_steps_1_3.py` & `tests/unit/test_s6_review_fixes.py`)**:
   - Added focused unit tests for D1, D2 (`picture_geometry` + `understand` manifest fields, `pan_crop_2d` rigid 2D window pan), D3 (`choose_camera` feasibility/variety/push-cap/audit, `direction.check` `_feasibility` & `_audit_present`), D4 (`S05_SH020` regeneration), and the 16-row Truce fixture run (0 vetoed angle-change moves, 0 consecutive identical primary moves, non-map push share `18.2% <= 40%`, 100% non-empty `choice.audit`).
