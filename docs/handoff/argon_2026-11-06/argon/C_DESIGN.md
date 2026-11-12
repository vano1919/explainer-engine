# Step C: Detailed Design of `visual_script/1` Builder & Reuse Planner (`C_DESIGN.md`)

## მოკლე შეჯამება დამკვეთისთვის (ქართულად)

- **რა გაკეთდა:** დავაპროექტეთ `visual_script/1` სქემა და ამწყობი (`explainer_engine/visual/visual_script.py`), `"needs LTX"` კადრის დეტერმინისტული ტესტი, `in_shot` სიისა და Blender-ის კამერის ხედვის არეალის (frustum) შემმოწმებელი (`explainer_engine/visual/still_needs.py`), `R0–R5` ხელახალი გამოყენების დამგეგმავი სოლვერი (`explainer_engine/visual/reuse_plan.py`) და დამკვეთის დასამტკიცებელი გვერდის (`Q5 A` / `OR-23`) გენერატორი.
- **რა გავაუმჯობესეთ არსებულ გეგმასთან (`PLANNING_CHAIN_PLAN.md` და `REUSE.md`) შედარებით და რატომ:**
  1. **`needs_ltx` ფილტრი კლიპების დაჭრამდე:** `PLANNING_CHAIN_PLAN.md` §3 ყველა კადრს ნაგულისხმევად 1 LTX კლიპად აქცევდა. ჩვენ დავამატეთ მკაცრი დეტერმინისტული ტესტი (`needs_ltx`), რომელიც ამოწმებს, შეიძლება თუ არა კადრის გადაწყვეტა უფასო J5 2.5D კოლაჟით (`assemble_25d/1`), Python გრაფიკით (`H`) ან სტატიკური/პითონით მოძრავი კადრით (`push_in`, `pan`, `truck`, `parallax_25d` `<= 1.6x`). `route_test`-ის 24 კადრზე ეს ფილტრი ამცირებს LTX კლიპებს **9-დან 6-მდე** (`43.2 წმ -> 32.16 წმ`, **-25.6%**).
  2. **`R0–R5` წესების შეთანხმება და `R4` (Clip Retime)-ის ამოღება:** `PLANNING_CHAIN_PLAN.md` §4-ში `R4` იყო ძველი LTX კლიპის შენელება/გამეორება (რაც ვიდეოს ძველ კადრებზე მორგებაა), ხოლო `REUSE.md` §2-ში მოცემულია სწორი `R0–R5` იერარქია. ჩვენ საბოლოოდ დავაკანონეთ `REUSE.md` §2-ის `R0–R5` კოდები, მკაცრი `in_shot` იდენტურობით (`Q3 A`) და `ZOOM_MAX = 1.6` (`AC-13`) შეზღუდვით.
  3. **Blender-ის ხედვის არეალის (Frustum) ავტომატური გაწმენდა:** `still_needs.py` არა მხოლოდ ამოწმებს კამერის ხედში მოხვედრილ ზედმეტ 3D ობიექტებს, არამედ აბრუნებს `hide_in_blender` სიას, რათა Blender-მა რენდერამდე ავტომატურად დამალოს ყველა რეკვიზიტი, რომელიც `in_shot`-ში არ წერია.
  4. **გადაწყვეტილების ნომრის (`D-118`) კოლიზიის გასწორება:** `D-118` უკვე დაკავებულია (`RP-10 placement watch`), ამიტომ `visual_script/1` კონტრაქტს მიენიჭა `D-119`.

---

## 1. Executive Summary Report (Under 600 Words)

### What Was Done
We designed the complete, implementation-ready specification for packages `V0–V3` and `V6`/`V10` of [`PLANNING_CHAIN_PLAN.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/plans/PLANNING_CHAIN_PLAN.md) and [`REUSE.md`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/docs/handoff/argon_2026-11-06/REUSE.md):
1. **Inputs & Schema (`visual_script/1`, `explainer_engine/schemas/visual_script_1.json`):** Consumes either `film_shots/3` + `audio_spine/2` or `route_shots/draft0` ([`tests/fixtures/route_test/route_shots.json`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/tests/fixtures/route_test/route_shots.json)).
2. **The `"needs LTX"` Shot Test (`needs_ltx` in `explainer_engine/visual/visual_script.py`):** Evaluates every shot before clip generation and downgrades emotional/reaction holds or simple camera moves (`push_in`, `pan`, `truck`, `drift`, `parallax_25d`) from paid `J2`/`J4` LTX to free `J5` (`assemble_25d/1`) or Python camera moves.
3. **Still-Needs Derivation & Blender Frustum Check (`explainer_engine/visual/still_needs.py`):** Derives one still per LTX clip start frame or J5/still shot with an explicit `in_shot` list (`asset_id`, `role`, `pose`, `reason`) and validates that `frustum_objects` is a strict subset of `in_shot`.
4. **Reuse Planner Solver (`explainer_engine/visual/reuse_plan.py`):** Evaluates options `R0–R5` in exact dollar + wall-clock cost order subject to hard quality gates (`in_shot` set equality per `Q3 A`, `zoom <= 1.6` per `AC-13`, no img2img chain per `D-78`).
5. **Creator Approval Page (`render_approval_page`):** Generates the single readable Markdown report (`Q5 A`, `OR-23`) for creator sign-off before any paid pod run.

### What Was Found & Key Numbers
- On [`tests/fixtures/route_test/route_shots.json`](https://github.com/vano1919/explainer-engine/blob/argon/handoff-2026-11-06/tests/fixtures/route_test/route_shots.json) (`24 shots`, `104.5 s`), the `needs_ltx` test identifies 3 shots previously routed to `J2` (`S02-05` 4 s static-camera shout, `S03-04` 4 s static-camera exhale, `S05-04` 3 s `push_in` close-up at ship rail) that pass the `"static or Python/2.5D-moved still would do"` test. Downgrading those 3 shots to `J5` (`assemble_25d/1`) reduces LTX clips from **`9 clips (43.20 s, 1,039 frames)` to `6 clips (32.16 s, 772 frames)`** — saving **`11.04 s` of LTX (`-25.6%`)** and **`3` Qwen restyle edits**.
- Reconciling `PLANNING_CHAIN_PLAN.md` §4 with `REUSE.md` §2 eliminates the broken `R4` clip-retime rule and establishes a single deterministic cost hierarchy (`R0 = $0.00`, `R1 = $0.00`, `R2 = $0.00`, `R3 = $0.0259 / N_group`, `R4 = $0.0259`, `R5 = $0.0259 + OR-18 record`).

### What Could Not Be Verified
- Live Blender 5.2.3 `bpy` camera frustum projection matrices could not be executed in the container (Blender is not installed locally per `OPEN_QUESTIONS.md` §D), so `check_frustum_visibility` accepts pre-extracted frustum object sets or bounding-box projections.

### Questions for the Creator (4 Options Each)

1. **Q-C1: Threshold for `needs_ltx` on Single-Character Emotional Gesture Shots (`V8`, e.g. `S02-05`, `S03-04`, `S05-04`)**
   - **Option A:** Route all `V8` single-character emotional close-ups/mediums with static/push-in cameras to **J5 (`assemble_25d/1` + procedural breath/blink/brow/jaw + wind/smoke FX)** (**$0.00 GPU**, saves `$0.09–$0.14/shot`).
   - **Option B:** Route silent `V8` close-ups (`S03-04`, `S05-04`) to free **J5**, but keep shouting/arm-raising gestures (`S02-05`) on **J2 LTX** (**+$0.09–$0.14** for `S02-05`).
   - **Option C:** Use a 2-pose Qwen card swap in J5 (`pose_a -> pose_b` cross-fade or snappy hold) for `V8` gestures (**$0.0259** for 1 extra Qwen pose card, `$0.00` LTX).
   - **Option D:** Keep all `V8` emotional gesture shots on **J2 LTX** (`97 frames`, **+$0.09–$0.14/shot**).

2. **Q-C2: Handling `R3` Wide Shared Renders (`1.6x` Blender Render + One Qwen Edit Cropped for Multiple Stills)**
   - **Option A:** Enable `R3` automatically whenever `>= 2` stills share `(place_id, camera_side, in_shot_assets, poses)` and max crop zoom `<= 1.6x`, marking `R3` rows `APPROVED` if zoom `<= 1.35x` and `REVIEW` if `1.35x < zoom <= 1.60x` (**saves ~$0.013–$0.020/still**).
   - **Option B:** Mark **every** `R3` shared-render crop as `REVIEW` on the creator's approval page until `p15` proves Qwen's 1280x720 -> 1920x1088 sharpness under crop (**same compute savings, human visual check**).
   - **Option C:** Render `R3` shared Qwen edits at `1920x1088` native (instead of `1280x720`) so a `1.6x` crop retains `>= 1200x680` before Lanczos+CAS upscale (**adds ~15s Qwen GPU time = +$0.011/group, still cheaper than 2 separate edits**).
   - **Option D:** Disable `R3` until `p15` runs and allow only `R0`, `R1` (on 2048x1024 plates), and `R2` (**+$0.18/episode**).

---

## 2. What We Improved vs. `PLANNING_CHAIN_PLAN.md` & `REUSE.md` (and Why)

| Area | Original Plan (`PLANNING_CHAIN_PLAN.md` / `REUSE.md` / `compose/reuse.py`) | Argon Improved Design (`C_DESIGN.md` & Step D Code) | Why Changed |
|---|---|---|---|
| **1. Shot-to-LTX Gate (`needs_ltx`)** | `PLANNING_CHAIN_PLAN.md` §3: *"1 shot = 1 clip by default, unless duration_sec > 4.0 s"*; §2 schema draft sends static dialogue `S03-02` to `J4` LTX. | Added deterministic `needs_ltx(shot)` gate *before* clip creation. Shots with `route in {"H", "J5"}`, dialogue-only action, or static/camera-only motion (`push_in`, `pan`, `truck`, `drift`, `parallax_25d`) without multi-limb physical contact/locomotion return `needs_ltx=False` and route to `J5` / `H`. | Directly enforces Strategy Rule 1 (*"LTX minimisation: decide per shot, from the script, which shots truly need LTX motion"*). |
| **2. Clip Duration & `8k+1` Math (`Q4 A`)** | `PLANNING_CHAIN_PLAN.md` §3 split any shot `> 4.0 s` and listed `25 frames = 1.00 s` (actually `25/24 = 1.0417 s`) and `129 frames` (`8*16+1 = 5.375 s`). | Enforces `BP-172` (`3–6 s` per LTX clip, hard limit `2–8 s`, `97–145` typical frames, `8k+1` per `BP-139`) and `Q4 A`: rounds clip frames up to `F = 8 * ceil((sec * 24 - 1) / 8) + 1` (adding at most `7/24 = +0.2917 s <= +0.33 s`) and records `trim_sec` so assembly trims the clip back to the exact script/audio beat! | Prevents LTX's `8k+1` frame grid from stretching the edit timeline (pictures/clips fitted to script, never script to clips). |
| **3. `R0–R5` Reuse Definitions** | `PLANNING_CHAIN_PLAN.md` §4 defined `R4` as *"Clip Retime Reuse"* and used loose *"asset overlap"* matching, contradicting `REUSE.md` §2 and `Q3 A`. | Unified on `REUSE.md` §2's canonical `R0–R5` definitions, removed `R4` clip retiming completely, and enforced exact `in_shot` asset+pose set equality (`Q3 A`). | Retiming old LTX clips or reusing frames with leftover props violates Standing Order 14 and `Q3 A`. |
| **4. Legacy `setup_key` (`compose/reuse.py`)** | `setup_key(shot)` keyed only on `(background, angle, cast)`, ignoring props and poses. | New `still_setup_key(still)` keys on `(place_id, camera_side, frozenset((item["asset_id"], item["role"], item["pose"]) for item in still["in_shot"]))`. | Prevents a shot that needs a scroll, sword, or standing pose from reusing an earlier frame where the character had empty hands or sat. |
| **5. Blender Frustum Check (`V3`)** | `PLANNING_CHAIN_PLAN.md` §1 Stage 7 noted *"no object in camera that is not in `in_shot`"* as a check only. | `check_frustum_visibility(still, frustum_objects)` returns both `violations` (`FRUSTUM_EXTRA_OBJECT`, `FRUSTUM_MISSING_OBJECT`) AND a deterministic `hide_in_blender` list to auto-hide extra set meshes before rendering. | Eliminates `pilot_room` background clutter (`bookshelf`, `cabinet`, `elder` by stove) automatically before Qwen restyle. |
| **6. Decision ID Collision (`D-118`)** | `PLANNING_CHAIN_PLAN.md` / `PLANS.md` proposed `D-118` for `visual_script/1`. | Assigned `D-119` (`visual_script/1` is the single visual plan of the episode), preserving `D-118` (`RP-10` placement watch). | Resolves the `OPEN_QUESTIONS.md` §C collision cleanly under `docs_lint.py`. |

---

## 3. Detailed Specification: `visual_script/1` Builder (`explainer_engine/visual/visual_script.py`)

### 3.1 Inputs
1. **Primary Input (`route_shots/draft0` or `film_shots/3`):**
   - `episode` / `project_id`: string identifier.
   - `cast`: mapping of hero IDs (`H1`, `H2`, `H3`) to appearance tags and voices.
   - `places`: mapping of place IDs (`A1`..`A4`) to environment descriptions.
   - `scene_assets`: per-scene 360 backdrops, hero turnaround sheets, props, and light variants.
   - `shots[]`: ordered shot cards with `id`/`shot_id`, `scene`, `kind`, `route` (`J2`/`J4`/`J5`/`H`), `seconds`/`duration_sec`, `place`/`place_id`, `narration`, `dialogue`, `assembly`/`layout`/`helper`, and `prompts`.
2. **Optional Timing Input (`audio_spine/2`):**
   - Locked word/line timestamps (`start_sec`, `end_sec`) from ElevenLabs + Scribe (`Q1 A`). When absent (as in `route_shots.json`), cumulative `start_sec` and `end_sec` are computed deterministically from each shot's `seconds`.

### 3.2 Deterministic `"Needs LTX"` Shot Test (`needs_ltx(shot) -> dict`)
Given a shot card `shot`, `needs_ltx(shot)` evaluates the following ordered rules:
1. **Helper Route (`route == "H"` or `helper` block present):**
   - Returns `{"needs_ltx": False, "effective_route": "H", "reason": "pure Python 2D vector/map helper graphic", "fallback_mode": "python_helper/1"}`.
2. **Explicit 2.5D Route (`route == "J5"` or `assembly.recipe == "assemble_25d/1"`):**
   - Returns `{"needs_ltx": False, "effective_route": "J5", "reason": "Blender 2.5D cut-out card assembly with free camera/life motion", "fallback_mode": "assemble_25d/1"}`.
3. **Voiced Dialogue Without Full-Body Locomotion/Combat (`dialogue` present and no combat/crowd keywords):**
   - Returns `{"needs_ltx": False, "effective_route": "J5", "reason": "voiced dialogue shot served by J5 2.5D cards + Rhubarb mouth cues", "fallback_mode": "assemble_25d/1"}`.
4. **Single-Character Emotional Gesture / Hold / Camera-Move Test (`kind` starts with `"V8"` or `"S1"` or `"S3"` or `"V7"`):**
   - Inspects the shot's action/motion description (`prompts.ltx_motion`, `narration`, `kind`) and `layout.camera.move`.
   - Let `CONTINUOUS_DEFORMATION_VERBS = {"clash", "duel", "lunge", "parry", "fight", "strike", "run", "sprint", "charge", "carry", "march", "splash", "swim", "climb", "fall"}`.
   - Let `STATIC_OR_25D_VERBS = {"stare", "stares", "exhale", "exhales", "breathe", "breathing", "shout", "shouts", "raise", "raises", "lower", "lowers", "stand", "stands", "look", "looks", "listen", "listens", "wait", "waits"}`.
   - If the shot has no crowd (`not layout.get("crowd")`) and no continuous multi-limb locomotion/combat verb in `CONTINUOUS_DEFORMATION_VERBS` (for example: `S02-05` *"commander raises his arm and shouts, static camera"*, `S03-04` *"young scout lowers his shoulders and exhales, static camera"*, `S05-04` *"commander stares at the sea, camera pushes in"*), then a static or Python/Blender 2.5D-moved still with procedural card life/gesture holds the shot at `$0.00` LTX cost!
   - Returns `{"needs_ltx": False, "effective_route": "J5", "reason": "passes static/Python/2.5D still-move test (no multi-limb locomotion or combat contact)", "fallback_mode": "assemble_25d/1"}`.
5. **True Motion Shots Failing the Still Test (`J2` clay action/duel `S02-03`, `S03-02`; `J4` 5,000-soldier crowd battle/march `S02-02`, `S04-01`):**
   - Returns `{"needs_ltx": True, "effective_route": shot["route"], "reason": <specific continuous motion reason>, "fallback_mode": None}`.

### 3.3 LTX Clip Derivation (`8k+1` Frame Rule & `Q4 A` Trim Handle)
For every shot with `needs_ltx == True`:
- If `seconds <= 6.0` (single LTX clip within `BP-172` `3–6 s` band):
  - Compute target frames at `fps = 24`: `raw_frames = round(seconds * fps)`.
  - Round **up** to the next valid `8k + 1` integer (`BP-139`, `Q4 A`):
    `k = max(3, math.ceil((raw_frames - 1) / 8))` -> `ltx_frames = 8 * k + 1`.
  - Compute `clip_duration_sec = round(ltx_frames / 24.0, 4)` and `trim_sec = round(clip_duration_sec - seconds, 4)` (always `<= 0.3333 s`).
  - Emit clip `{ "clip_id": f"{shot_id}.c1", "shot_id": shot_id, "route": effective_route, "start_sec": start_sec, "target_duration_sec": seconds, "clip_duration_sec": clip_duration_sec, "trim_sec": trim_sec, "ltx_frames": ltx_frames, "ltx_fps": 24, "overlap_frames": 0, "first_frame_still_id": f"{shot_id}.s1", "prompt": ltx_prompt }`.
- If `seconds > 6.0` (e.g. `10.0 s` scenes `S02-02` and `S04-01`):
  - Split into `N = math.ceil(seconds / 6.0)` chained clips (`S02-02.c1`, `S02-02.c2`) with `overlap_frames = 8` (`0.3333 s` overlap handle) and `145 frames` (`6.0417 s`, `8*18+1`) each, each anchored by its own first-frame still (`S02-02.s1`, `S02-02.s2`).

---

## 4. Detailed Specification: Still-Needs Derivation & Frustum Visibility Check (`explainer_engine/visual/still_needs.py`)

### 4.1 `in_shot` Derivation Rules (Standing Order 14)
Every still (`S<scene>-<shot>.s<n>`) is tied to exactly one purpose:
- `purpose = f"first_frame_clip_{clip_id}"` (for `J2`/`J4` LTX clips), or
- `purpose = f"j5_assembly_{shot_id}"` (for `J5` 2.5D shots).
Helper shots (`route == "H"`) require **zero** stills (`stills = []`).

For each still, `in_shot` is derived strictly from the shot card (`assembly`, `layout`, `dialogue`, `prompts`), never from a room's full 3D inventory:
1. **Backdrop item (`role = "backdrop"`):** `asset_id = place_id` (e.g. `"A1"`), `pose = light_variant` (e.g. `"dusk"`), `reason = f"scene backdrop for {shot_id}"`.
2. **Hero items (`role = "subject"` or `"speaker"` or `"listener"`):**
   - From `assembly.heroes[]` (for J5) or extracted deterministically from `cast` tags/IDs referenced in `shot` (for J2/J4), or `"crowd_soldiers_5000"` when `layout.crowd` is present.
   - Each entry records `asset_id` (`"H1"`, `"H2"`, `"H3"`, or `"crowd_soldiers_5000"`), `role`, `pose` (e.g. `"3q_right:stands at the map table"` or `"start_pose"`), and `reason` (e.g. `"voiced speaker H3"` or `"active duelist in clip S03-02.c1"`).
3. **Prop items (`role = "prop"`):**
   - Only props explicitly listed in `assembly.props_on_cards` or referenced in the shot's active motion/prompt line (e.g. `"wooden table"`, `"map"`, `"banner"`, `"broadsword"`, `"short sword"`). Passive room props from other shots are excluded.

### 4.2 Blender Camera Frustum Visibility Check (`check_frustum_visibility`)
Given a derived `still` and the set/list of 3D object IDs visible in the Blender camera frustum (`frustum_objects`):
- Let `allowed_ids = {item["asset_id"] for item in still["in_shot"]}`.
- **Extra objects (`extra = sorted(set(frustum_objects) - allowed_ids)`):** Every object in `extra` violates Standing Order 14 (`rule = "SO-14"`, `code = "FRUSTUM_EXTRA_OBJECT"`).
- **Missing objects (`missing = sorted(allowed_ids - set(frustum_objects) - {still["place_id"]})`):** Every foreground hero/prop required by `in_shot` that is missing from the camera frustum raises `code = "FRUSTUM_MISSING_OBJECT"`.
- **Auto-hide list (`hide_in_blender = extra`):** Passed directly to the Blender layout renderer so unlisted room props (`bookshelf`, `cabinet`, `bucket`, `elder` by stove) are hidden (`obj.hide_render = True`) prior to rendering!

---

## 5. Detailed Specification: Reuse Planner Solver (`R0–R5`, `explainer_engine/visual/reuse_plan.py`)

### 5.1 Canonical `R0–R5` Rules, Hard Constraints, and Cost Equations

| Option Code | Name | Hard Eligibility Constraints (Quality = Hard Constraint, Never Traded for Cost) | GPU Cost Equation (USD) | Wall-Clock Seconds (H100 NVL / Local CPU) | Review Status |
|---|---|---|---|---|---|
| **`R0`** | **Library / Prior-Episode Exact Still Reuse** | `library` contains an approved still with identical `(place_id, light_variant, camera_side)` and `source.in_shot_key == target.in_shot_key` (`Q3 A` exact match), `zoom == 1.0`. | **`$0.0000`** (`0` Qwen pics) | `0.0 s` GPU, `0.0 s` CPU | `APPROVED` |
| **`R1`** | **Intra-Episode Crop / Zoom Reuse (`AC-12/13`)** | Earlier still `src` in the same episode shares `(place_id, light_variant, camera_side)`, the cropped region of `src` holds **exactly** `target.in_shot` (`Q3 A`), `1.0 <= zoom <= ZOOM_MAX (1.6)`, and `src` is not itself a crop/img2img chain (`D-78`). | **`$0.0000`** (`0` Qwen pics) | `0.0 s` GPU, `0.2 s` FFmpeg crop | `APPROVED` if `zoom <= 1.35`; `REVIEW` if `1.35 < zoom <= 1.60` |
| **`R2`** | **J5 2.5D Card Assembly (`assemble_25d/1`)** | `still.route == "J5"` (shot passed `needs_ltx == False` and all `in_shot` heroes/props/backdrops exist in `scene_assets` / `library` or are budgeted in `asset_needs`). | **`$0.0000`** marginal per still (`0` new Qwen restyles) | `0.0 s` GPU, `23.75 s` CPU (`95 s / 4 frames`) | `APPROVED` |
| **`R3`** | **Shared Wide (`1.6x`) Blender Render + ONE Qwen Edit** | Group of `k >= 2` non-J5 stills in the episode share `(place_id, light_variant, camera_side)` and identical active `in_shot` set (`Q3 A`), with camera focal lengths / framing boxes fitting inside a single `1.6x` master frustum (`zoom_i <= 1.6` for each still `i` in group). | **`$0.02590 / k`** per still (`1` Qwen edit for the whole group of `k` stills) | `36.0 s / k` GPU + `60.0 s / k` CPU | `APPROVED` for anchor still (`zoom == 1.0`); `REVIEW` for cropped sibling stills |
| **`R4`** | **New Blender Still + New Qwen Restyle Edit** | Default for any `J2`/`J4` clip first frame not covered by `R0–R3`. Pin hero references to `B_H*` turnaround sheets (`D-75`, `D-78`). | **`$0.02590`** (`1` Qwen edit on H100 NVL; `$0.02363` on A100) | `36.0 s` GPU + `60.0 s` CPU | `APPROVED` |
| **`R5`** | **New Qwen Scene Asset (Backdrop / Hero Sheet Angle / Prop Card)** | Required when a `J5` (`R2`) or `R4` shot references a backdrop, hero angle, or prop card missing from `library`. Requires an explicit `OR-18` library-search miss record. | **`$0.02590`** per missing asset sheet/plate | `36.0 s` GPU + `20.0 s` BiRefNet CPU | `REVIEW` (requires `OR-18` reason on creator page) |

### 5.2 Deterministic Solver Algorithm (`solve_reuse_plan`)
1. **Asset Library & `OR-18` Check (`R5`):** Scan all required backdrops, hero turnaround angles, and prop cards across `stills[]`. Any asset present in `library` costs `$0.00`; any missing asset emits an `R5` asset generation row with an `OR-18` search-miss record.
2. **Per-Still Grouping & Candidate Evaluation (`R0 -> R1 -> R2 -> R3 -> R4`):**
   - Compute `in_shot_key(still) = frozenset((i["asset_id"], i["role"], i["pose"]) for i in still["in_shot"])` and `group_key(still) = (still["place_id"], still.get("light_variant", "default"), still["camera_side"], in_shot_key(still))`.
   - For each still `s`:
     - Check **`R0`** against `library["stills"]`: if an exact match on `group_key(s)` exists with `zoom <= 1.6`, assign `R0` (`$0.00`).
     - Else if `s["route"] == "J5"` and all required cards exist (via `library` or `R5`), assign **`R2`** (`$0.00` marginal still edit).
     - Else group all remaining `J2`/`J4` stills sharing `group_key(s)`:
       - Select the widest framing (`min lens_mm` / widest shot size `EWS < WS < MS < MCU < CU`) in the group as the primary anchor still (`R4`, `1` Qwen edit).
       - For every subsequent still `s_j` in the same `group_key`: compute `zoom = lens_mm(s_j) / lens_mm(anchor)`.
         - If `zoom == 1.0` (exact camera return): assign **`R1`** (`zoom = 1.0`, `$0.00`, `APPROVED`).
         - If `1.0 < zoom <= ZOOM_MAX (1.6)`: if the anchor was rendered standard, assign **`R1`** (`$0.00`, `APPROVED` if `<= 1.35` else `REVIEW`); if the group spans wide+tight cameras planned together as a `1.6x` wide master render, assign **`R3`** (`1` shared Qwen edit across the group, `$0.00` marginal cost for `s_j`).
         - If `zoom > ZOOM_MAX (1.6)`: reject crop (`AC-13` hard constraint) and assign a new **`R4`** render (`$0.02590`) for `s_j` (which then becomes a new anchor for any even tighter shots!).
3. **Tie-Breaking & Output Contract (`reuse_plan/1`):** Ties in dollar cost break toward fewer generated Qwen pictures, then lower GPU seconds.

---

## 6. Creator Approval Page Design (`Q5 A` / `OR-23`, `render_approval_page`)

Before any paid RunPod pod or ElevenLabs batch is launched, `render_approval_page(visual_script, reuse_plan)` generates a single human-readable Markdown document containing five mandatory sections:
1. **Header & Spend-Cap Gate (`OR-23`, `RP-07`):** Episode/part ID, total duration, total LTX clips & seconds, total new Qwen pictures (`R3 + R4 + R5`), expected & worst-case USD vs. `config/spend_caps.json` (`per_pod_usd = $10.00`, `min_balance_left_usd = $1.00`), and PASS/FAIL gate status.
2. **Part 1 — Shot-by-Shot `needs_ltx` & Route Table:** Every shot ID, duration, original route vs. effective route, `needs_ltx` boolean, exact reason, and LTX frame count (`8k+1`) + `trim_sec`.
3. **Part 2 — Stills & `in_shot` Manifest + Frustum Check:** Every still ID, purpose, camera setup, complete `in_shot` list (`asset_id`, `role`, `pose`, `reason`), and Blender frustum check (`PASS` or `auto-hidden objects`).
4. **Part 3 — `R0–R5` Reuse Plan Table (with `REVIEW` Highlights):** Every still and asset need, assigned `R0–R5` code, source still/library ID, crop `zoom` factor, USD cost, and status (`APPROVED` vs. `REVIEW`).
5. **Part 4 — Sign-Off Block:** Explicit command for the creator (`"Reply GO to launch pod schedule ..."`).
