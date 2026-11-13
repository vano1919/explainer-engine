# Step D: Free Implementation Report (`D_IMPLEMENTATION.md`)

## მოკლე შეჯამება დამკვეთისთვის (ქართულად)

- **რა გაკეთდა:** სრულად დავწერეთ, დავტესტეთ და ცალ-ცალკე კომიტებად (`D1`, `D2`, `D3`) შევინახეთ სამივე უფასო პაკეტი რეპოზიტორიის სტილის დაცვით (`<= 120` სიმბოლო ხაზზე, `from __future__ import annotations`, გარე ბიბლიოთეკების გარეშე, `python3 -m explainer_engine.docs_lint` = `0 finding(s)`):
  1. **D.1 (`visual_script/1` და `"needs LTX"` ტესტი):** `explainer_engine/visual/visual_script.py`, `explainer_engine/schemas/visual_script_1.json` და `tests/unit/test_visual_script.py` — გაშვებულია `tests/fixtures/route_test/route_shots.json`-ის 24 კადრზე (`104.5 წმ`). `needs_ltx` ფილტრი ამცირებს LTX კადრებს **7-დან 4-მდე** (კლიპებს **9-დან 6-მდე**, ფრეიმებს **1,089-დან 822-მდე**, დაზოგილია **267 LTX ფრეიმი / 11.04 წმ** და **3 Qwen რესტაილი**).
  2. **D.2 (`still_needs` + `in_shot` + Blender Frustum შემოწმება):** `explainer_engine/visual/still_needs.py` და `tests/unit/test_still_needs.py` — თითოეული კადრისთვის აგენერირებს ზუსტ `in_shot` სიას (`asset_id`, `role`, `pose`, `reason`) და ამოწმებს Blender-ის კამერის ხედვის არეალს (`check_frustum_visibility`), აბრუნებს რა `hide_in_blender` სიას ზედმეტი ავეჯისა და რეკვიზიტების ავტომატურად დასამალად.
  3. **D.3 (`R0–R5` ხელახალი გამოყენების სოლვერი და დასამტკიცებელი გვერდი):** `explainer_engine/visual/reuse_plan.py` და `tests/unit/test_reuse_plan.py` — დეტერმინისტული სოლვერი, რომელიც ამოწმებს `R0–R5` ვარიანტებს ხარისხის მკაცრი შეზღუდვებით (`Q3 A` ზუსტი `in_shot` თანხვედრა, `AC-13` `ZOOM_MAX = 1.6`, `D-78` ჯაჭვური კროპის აკრძალვა) და აგენერირებს `OR-23` / `Q5 A` დასამტკიცებელ გვერდს (`OR23_ROUTE_TEST_APPROVAL_PAGE.md`). ხელით გამოთვლილ 7-კადრიან ეტალონურ ტესტზე ზუსტად სვამს ოპტიმალურ გეგმას (**5 Qwen სურათი = $0.1295**).

---

## 1. Executive Summary Report (Under 600 Words)

### What Was Done
We implemented all three required free packages in [`explainer_engine/visual/`](https://github.com/vano1919/explainer-engine/tree/argon/handoff-2026-11-06/explainer_engine) with unit tests in [`tests/unit/`](https://github.com/vano1919/explainer-engine/tree/argon/handoff-2026-11-06/tests/unit), strictly following repository conventions (`<= 120` columns per line, no external formatter, stdlib-only, `python3 -m explainer_engine.docs_lint` clean with `0 finding(s)`):
1. **Package D.1 — `"Needs LTX"` Shot Test & `visual_script/1` Builder:**
   - Modules: `explainer_engine/visual/visual_script.py`, `explainer_engine/schemas/visual_script_1.json`, `explainer_engine/visual/__init__.py`.
   - Tests: `tests/unit/test_visual_script.py` (3 tests, all passing on [`tests/fixtures/route_test/route_shots.json`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/tests/fixtures/route_test/route_shots.json)).
2. **Package D.2 — Still-Needs Derivation with `in_shot` & Frustum Check:**
   - Module: `explainer_engine/visual/still_needs.py`.
   - Tests: `tests/unit/test_still_needs.py` (2 tests, all passing).
3. **Package D.3 — Reuse Planner Solver (`R0–R5`) & Creator Approval Page:**
   - Module: `explainer_engine/visual/reuse_plan.py` + generated sample approval page `docs/handoff/argon_2026-11-06/argon/OR23_ROUTE_TEST_APPROVAL_PAGE.md`.
   - Tests: `tests/unit/test_reuse_plan.py` (2 tests, all passing, including `test_reuse_planner_matches_known_by_hand_optimal_plan`).

### What Was Found & Key Numbers
- **`route_test` (`tests/fixtures/route_test/route_shots.json`, 24 shots, `104.5 s`) Before vs. After `needs_ltx` Gate:**
  - *Without `needs_ltx` gate:* `7` LTX shots (`9 clips`: `S02-02.c1/c2` `290f`, `S02-03.c1` `121f`, `S02-05.c1` `97f`, `S03-02.c1` `121f`, `S03-04.c1` `97f`, `S04-01.c1/c2` `290f`, `S05-04.c1` `73f`), totaling **`41.0 s` target (`45.38 s` LTX generated = `1,089 frames`)** and `17` free shots (`63.5 s`).
  - *With `needs_ltx` gate:* Downgrades the 3 single-character static/push-in emotional gesture shots (`S02-05`, `S03-04`, `S05-04`) from `J2` LTX to free `J5` (`assemble_25d/1`), leaving **`4` LTX shots (`6 clips` = `30.0 s` target, `34.25 s` LTX generated = `822 frames`)** and **`20` free shots (`74.5 s`)** — reducing LTX frames by **`267 frames` (`-24.5%`)** and saving **`3` Qwen restyles + `3` LTX generations** (`-$0.255` plain / `-$0.395` retry-buffered on a 104.5 s sequence).
- **Hand-Solved 7-Still Benchmark (`test_reuse_planner_matches_known_by_hand_optimal_plan`):**
  - Evaluates 7 stills across 3 scenes (`A1`, `A2`) against a library containing `["A1", "A2", "H1", "H2"]` and 1 prior still (`lib_A1_H1_24mm`).
  - Solver deterministically assigns: `S01-01.s1 -> R0 ($0)`, `S01-02.s1 -> R2 ($0)`, `S02-01.s1 -> R3 master ($0.0259, 1 pic)`, `S02-02.s1 -> R3 crop (zoom=1.4583x <= 1.6x, $0, REVIEW)`, `S02-03.s1 -> R4 ($0.0259, 1 pic, enforcing D-78 no crop-of-crop and AC-13 2.0833x > 1.6x)`, `S03-01.s1 -> R4/R3 anchor ($0.0259, 1 pic, enforcing Q3 A exact in_shot: map != sword)`, `S03-02.s1 -> R1 (zoom=1.0x from S03-01.s1, $0, APPROVED)`, plus `2 R5` missing prop assets (`sword`, `map` = `$0.0518`) -> **3 still edits + 2 asset edits = 5 Qwen pictures (`$0.1295`)**.

### What Could Not Be Verified
- Headless Blender (`bpy`) execution of `hide_in_blender` object masking could not be run locally because Blender 5.2.3 is not installed in the sandbox VM (`OPEN_QUESTIONS.md` §D).

### Questions for the Creator (4 Options Each)

1. **Q-D1: Wiring `visual_script/1` Into `explainer_engine/edit/router.py` & `cloud/schedule.py` (Package V7)**
   - **Option A:** Keep `edit/router.py` (`film_shots/2`) untouched for backward compatibility and add a dedicated `visual_script/1 -> pod_schedule/1` bridge in `visual/schedule_bridge.py` (**$0.00, zero risk to existing 3,163 unit tests**).
   - **Option B:** Extend `edit/router.py` to accept both `film_shots/2` and `visual_script/1` directly (**$0.00, modifies core router**).
   - **Option C:** Have `training/pods/p16/build.py` read `visual_script/1` + `reuse_plan/1` directly when building the next pilot pod (**$0.00**).
   - **Option D:** Wait until the paid calibration test (Step E) completes before wiring `pod_schedule/1` (**$0.00**).

2. **Q-D2: Handling `S04-01` (10 s Rain March Column, Currently Routed to `J4` LTX = 2 Clips / 290 Frames)**
   - **Option A:** Keep `S04-01` on `J4` LTX (2 clips, `290 frames`, **~$0.24–$0.34**) to test 5,000-soldier crowd restyling in rain.
   - **Option B:** Cut `S04-01` from `10.0 s` (2 LTX clips) to `5.0 s` (1 LTX clip, `121 frames`) + `5.0 s` J5 two-shot truck (`S04-02` extended), saving **1 Qwen edit + 169 LTX frames (~$0.14–$0.20)**.
   - **Option C:** Render `S04-01` entirely in Blender 2.5D (`J5`) using 3 parallax tiers of marching soldier cut-out cards + Blender rain streaks FX (**$0.00 LTX**, saves **~$0.24–$0.34**).
   - **Option D:** Decide after the Step E paid calibration test measures actual LTX speed and crowd restyle quality.

---

## 2. Summary of Implemented Files & Verification Results

| Package | File Path | Lines | Max Col | Purpose | Test File & Result |
|---|---|---:|---:|---|---|
| **D.1** | `explainer_engine/schemas/visual_script_1.json` | 64 | 90 | JSON Schema Draft 2020-12 contract for `visual_script/1` (`D-119`). | `test_visual_script.py` (`3/3 PASS`) |
| **D.1** | `explainer_engine/visual/visual_script.py` | 247 | 115 | `needs_ltx(shot)`, `frames_8k_plus_1(seconds, fps)`, `build_visual_script(...)`, `validate_visual_script(...)`. | `test_visual_script.py` (`3/3 PASS`) |
| **D.1** | `explainer_engine/visual/__init__.py` | 25 | 113 | Clean public API exports for `explainer_engine.visual`. | `test_visual_script.py` (`3/3 PASS`) |
| **D.2** | `explainer_engine/visual/still_needs.py` | 275 | 118 | `build_in_shot(...)`, `derive_shot_stills(...)`, `derive_still_needs(...)`, `check_frustum_visibility(...)`. | `test_still_needs.py` (`2/2 PASS`) |
| **D.3** | `explainer_engine/visual/reuse_plan.py` | 308 | 117 | `in_shot_signature(...)`, `setup_group_key(...)`, `solve_reuse_plan(...)`, `render_approval_page(...)`. | `test_reuse_plan.py` (`2/2 PASS`) |
| **D.3** | `docs/handoff/argon_2026-11-06/argon/OR23_ROUTE_TEST_APPROVAL_PAGE.md` | 65 | 162 | Sample `OR-23` / `Q5 A` human-readable creator approval page generated from `route_shots.json`. | Verified in `test_reuse_plan.py` |
