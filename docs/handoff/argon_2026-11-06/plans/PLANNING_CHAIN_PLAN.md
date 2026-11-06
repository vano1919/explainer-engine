# The story-to-montage chain: one plan (Opus medium thread, 2026-11-06, ~16:40 UTC)

Source: the creator's order of production (msg cmsg_01Hnu5zB86sjUj5GtTgaUkPW2LE7f4vcpyfDq3wtzc9opd, 16:05 UTC) and
`PLANNING_CHAIN_BRIEF.md`. Studied against `origin/icw/17-run-schedule` (36cf22b; it contains `icw/05c-ink-round` 5579081 plus
RP-11). Planning only: nothing paid, no pod, no code pushed. Numbers marked **EST** are not measured.

## 0. The answer in five lines

1. The chain is: script → lanes/routes → **narration of the sample parts** → **visual script** (`visual_script/1`, new) → numbered
   LTX clips with their prompts and frame counts → stills with `in_shot` lists → asset needs → Blender + Qwen prompts →
   **reuse plan** (new, code solver + one reviewing agent) → RP-11 pod schedule → OR-23/OR-34/the creator's word → Blender (free),
   Qwen, BiRefNet, LTX (pod) → gates → assembly.
2. About half of it exists (film_shots/3, lanes + routes, spine/timing, assemble_25d, layout passes, cutout, ltx_jobs, RP-11,
   pilot assembler). What is missing is the middle: one artifact that holds the whole video's visual plan, and the derivations
   from it (clips → stills → assets → prompts → reuse → pod jobs). Today `route_shots/draft0` does that by hand for the route
   test only.
3. Sound: **the voice before the visual script** (recommended). Shot lengths, LTX frame counts and the dialogue clips already
   depend on word timings in the code; the read costs ~$2 for 12 minutes (EST), the pod hours it protects cost more.
4. Eleven free work packages, ~50 h of Sonnet work (EST), each with its test; then the one paid run = the D-67 sample (first
   two parts) through the whole chain.
5. Six questions only the creator can answer (section 7), sent to the Fable thread with four options each.

## 1. The chain, stage by stage

Owner: **SE** = writers' room / script engine (agents), **CODE** = deterministic module, **AG** = agent, **POD** = paid GPU,
**PC** = free Blender on the creator's PC or CI, **ვანო** = his approval.

| # | Stage | Artifact (schema) | Owner | Today | Missing (the diff) |
|---|---|---|---|---|---|
| 1 | Scenario | `scenario.md` + approval record (`scripting/scenario.py`, PV-45) | SE → ვანო | ✔ | — |
| 2 | Script | `film_shots/3` cards (`scripting/film_shots.py`) + `script_approval` (OR-17) | SE → ვანო | ✔ | — |
| 3 | Lanes and routes | `film_shots/3` fields `lane`, `archetype`, `route` (J2/J4/J5/H), `sub_category` (`visual/lanes.py`, `shot_design.py`, `archetypes_ic/2`) | CODE | ✔ | — |
| 4 | Narration (see §5) | ElevenLabs read → `audio/words.json` (Scribe) → `timed.json` (`production/timing.py`) → `audio_spine/2` (`audio/spine.py`); character lines read first (D-90) | CODE + paid credits → ვანო hears it | ✔ (code) | only the order changes |
| 5 | **Visual script** | **`visual_script/1`** (new; §2) | CODE builds, ვანო reads | ✘ (`route_shots/draft0` is a hand-made fixture) | schema, `core/contracts` check, builder `visual/visual_script.py` |
| 6 | LTX clips + prompts | inside `visual_script/1`: `clips[]` numbered `S03-02.c1`, frames 8k+1, prompt, conditioning | CODE | partial: `ltx_jobs.py` reads route_shots, `layout_passes` has clip geometry; `film_shots.compose` refuses /3 | composer `visual/ltx_prompts.py` (motion line from the card's action start/peak/settle) |
| 7 | Stills + `in_shot` | inside `visual_script/1`: `stills[]`, each the first frame of one clip (or a J5/still shot), with `in_shot` = only what that clip needs, each item with its reason | CODE | ✘ (rule given 15:53 UTC, sent to the Opus rules thread) | `visual/still_needs.py` + a Blender visibility check (no object in camera that is not in `in_shot`) |
| 8 | Asset needs | `asset_needs/1` (new, derived): per place the set (`world_layouts.json` id), 3D pieces, hero sheets × angles, prop cards, 360 backdrops | CODE | partial: `compose/library.needs`, `scene_assets/1`, `assets_reuse` (OR-18) | derivation from `visual_script/1` + the OR-18 search record per item |
| 9 | Render + Qwen prompts | per still: a Blender job (layout, camera, lens, pose, passes) and a Qwen edit prompt (in_shot only, START pose, place/era/light, no camera/layout words, ≤ 90 words, each tag once; `qa/style_prompt.check`) | CODE | partial: `pilot_stills.py` (cameras), `layout_passes`, `p14_qwen.py` job format, `style_prompt.check` | composer `visual/still_prompts.py` |
| 10 | **Reuse plan** | **`reuse_plan/1`** (new; §4) | CODE solver + AG reviewer | partial: `compose/reuse.py` (AC-12/13 crop reuse), library finds | solver `visual/reuse_plan.py` + agent page `asset-reuse-planner` |
| 11 | Pod schedule | `pod_schedule/1` (`cloud/schedule.py`, RP-11) + OR-23 page | CODE → Opus/Fable → ვანო | ✔ (schedule), page by hand | generator: reuse_plan → schedule stages + OR-23 page |
| 12 | Blender renders | stills (PNG + sidecar sha256), layout passes where a J2/J4 clip needs them | PC/CI, free | ✔ (`pilot_stills`, `layout_passes`, `assemble_25d`) | read jobs from `reuse_plan/1` |
| 13 | Qwen pictures | restyled stills, hero sheets, 360 backdrops, fix-edits; keyframe gate KG (≤ 3 tries) | POD | ✔ p14 (`p14_qwen.py`) | p15 package: jobs from `reuse_plan/1` |
| 14 | Cut-outs | J5 cards (`edit/cutout.py`: BiRefNet on the pod, `finish`/`check` free) | POD + CODE | ✔ | — |
| 15 | LTX clips | i2v from the Qwen still; J2/J4 with Blender control only where i2v fails (D-116) | POD | ✔ p14 (`p14_ltx.py`, `ltx_jobs.py`) | jobs from `visual_script/1` |
| 16 | Clip QA | identity, flicker, jitter (G9), clip length ≥ shot | CODE | ✘ (G9) | `qa/clip_check.py` (free, numpy + ffmpeg) |
| 17 | Assembly | `production/pilot.py` → `build_video_v2` (2560×1440, 24 fps), spine audio, sound mix (`assemble.py`) | CODE | ✔ for 60 s windows | run over the sample / whole episode, read clips by `visual_script/1` ids |
| 18 | Sample → rest | D-67: first two parts, ვანო approves, then the rest | ვანო | ✔ (`production/sample.py`) | wire to the new chain |

## 2. The visual script (`visual_script/1`)

One file per episode, **derived, never written by hand** (like `shot_spec`): built from the approved `film_shots/3` (after
lanes), the world (`world_layouts.json`, cast, places) and the clock (`audio_spine/2`, or a syllable estimate marked `timing:
estimate`). It is the "full picture" the creator asked for: every scene, every clip with its prompt, every still with what is in
it, every asset, and the counts.

```json
{
  "schema": "visual_script/1",
  "episode": "<slug>", "script_sha256": "...", "spine_sha256": "... | null", "timing": "read | estimate",
  "fps": 24, "size": [2560, 1440],
  "scenes": [{
    "id": "S03", "place": "A3", "set": "world_layout:river_ford", "seconds": 12.4,
    "shots": [{
      "id": "S03-02", "route": "J2", "sub_category": "V2", "lane": "VIDEO", "start_f": 1488, "frames": 140,
      "narration": "...", "dialogue": null,
      "clips": [{
        "id": "S03-02.c1", "frames": 145, "handle_f": 5, "first_still": "S03-02.k1",
        "motion": {"start": "...", "peak": "...", "settle": "..."},
        "ltx_prompt": "<style sentence> + <one motion line>", "conditioning": "i2v | layout:clay | restyle:colour+depth+line",
        "chain": {"after": null, "overlap_f": 0}
      }],
      "stills": [{
        "id": "S03-02.k1", "use": "first_frame", "camera": {"setup": "ots_left", "lens_mm": 55, "look_at": "host"},
        "in_shot": [{"item": "hero:host", "why": "gestures in c1"}, {"item": "prop:sword", "why": "drawn in c1"},
                    {"item": "set:walls_floor", "why": "always"}],
        "start_pose": {"hero:host": "sword sheathed, hand on hilt"},
        "blender_job": null, "qwen_prompt": null
      }]
    }]
  }],
  "totals": {"clips": 0, "ltx_seconds": 0, "stills": 0, "qwen_jobs": 0, "assets_new": 0, "j5_seconds": 0, "helper_seconds": 0},
  "lint": []
}
```

Rules it carries (homes stay where they are; the file links the IDs, never copies numbers):
- BP-108 scene length, BP-172 clip length (3-6 s, ≤ 8 s), BP-139 8k+1 frames, BP-84 shot floor, BP-109 lane shares, BP-105
  speech mix, KP-48 VIDEO runs: checked again on the derived file.
- **Stills are LTX material** (creator 15:53): every still serves one named clip or one J5/still shot; `in_shot` lists only what
  that use needs, each with its reason; walls/floor/backdrop are always allowed. Test: the Blender visibility pass lists every
  object in the camera frustum; any object not in `in_shot` = FAIL.
- **Qwen prompts from the card** (16:00): composed from `in_shot` + `start_pose` + place/era/light, no camera or layout words,
  ≤ 90 words (`style_prompt.CROWD_REVIEW_WORDS`), each tag once.
- A clip is longer than its shot by its handle, never shorter (`build_video_v2` refuses a short clip; nothing is stretched).
- D-75/D-78: a generated still is never the base of the next generation (crop reuse is allowed, img2img chains are not).

`blender_job` and `qwen_prompt` are filled by stage 9; the reuse plan may replace a still's job by "crop of S03-01.k1".
A readable page (`visual_script.md`: per scene a row per shot: route, seconds, clip prompt, still contents, thumbnails once
they exist) is what the creator reads (question Q6).

## 3. LTX clips written in advance

- Per shot: `clips = ceil(shot_frames / clip_max)`; each clip's frames = the smallest 8k+1 ≥ its share + handle; a J4 chain
  overlaps by 8 frames (as `layout_passes` already does: 12 s = 2 × 145 f overlapping by 8).
- The prompt = the house style sentence + ONE motion line from the card's action (start → peak → settle) and the others'
  reactions; camera words only where the camera moves (J4/J2 controlled moves come from the layout, not the prompt).
- Numbering `S<scene>-<shot>.c<n>`, stable across rebuilds (it keys HF paths and picks, as `pilot.py --pick` does today).
- The counts (clips, LTX seconds, by route) are in `totals` before any picture is analysed, as the creator asked.
- Input from the running pilot (PILOT_1MIN_PLAN v2, Fable's lane): whether one 8 s i2v clip holds sets `clip_max` (8 s or 6 s)
  and the measured seconds per clip that the cost model needs.

## 4. The reuse planner (`reuse_plan/1`)

**Inputs:** `visual_script/1` (stills with `in_shot`, cameras, sets), `asset_needs/1`, the libraries (`assets/library.json`,
`imagegen/picture_library`, `compose/library`, world kits), the measured speeds (`cloud/job_speeds.json`) and the cards' prices
(`cloud/schedule.py`).

**Options weighed per still / asset** (cheapest first):

| Code | Option | Allowed when |
|---|---|---|
| R0 | reuse a library picture or a still of an earlier episode as is | same place + era + cast, `in_shot` matches exactly |
| R1 | crop/zoom of another still of this episode (AC-12/13, `ZOOM_MAX` 1.6) | same set + camera side; after the crop the frame holds exactly `in_shot` (Q3) |
| R2 | J5 card: cut-out of an existing sheet or still (BiRefNet) placed on a 360 backdrop | a held / dialogue shot, no LTX motion of the body |
| R3 | one Blender render serving several stills (one wide at 1.6× size, cropped per still) → ONE Qwen edit | the stills share set, side and `in_shot` ⊆ the wide's, and the crop rule holds |
| R4 | new Blender render → new Qwen edit | default for a clip's first frame |
| R5 | new Qwen asset (hero sheet angle, 360 backdrop, prop) | nothing in R0-R3 covers it; OR-18 record with the reason |

**Cost model:** Blender seconds count as $0 (PC/CI) but enter the wall-clock; Qwen = 61 s load + 33.5-38.5 s per edit on the
H100 NVL (measured, pod 1), divided by the card's `gpu_speed`; LTX = seconds per 8k+1 frames (EST ~6 min per 193 f until the
pilot measures it); BiRefNet EST seconds per cut. The pod cost of a plan = RP-11's simulation of those stages (setup + makespan +
reserve) × price. Quality guards enter as hard constraints, not costs: `in_shot` exactness, identity (one sheet per hero,
invariant 6), no img2img chain (D-78), crop ≤ 1.6×.

**Solver:** deterministic (stdlib): group stills by (set, camera side, cast); enumerate R0-R5 per group (the groups are small,
so the full enumeration fits, like RP-11's); take the cheapest plan that passes every constraint; ties → fewer generated
pictures (fewer chances of a defect). The agent page (`asset-reuse-planner`, Sonnet) only reviews the REVIEW rows (a crop near
1.6×, an R0 match from another era, a group where two options cost within 5 %) and writes its reason in the plan; it never
changes a FAIL (question Q2).

**Output:** `reuse_plan/1`: per still / asset the chosen option, its source, the Blender job, the Qwen job, the cut job, and the
totals (Qwen jobs, LTX clips, pod $ expected / worst). Stage 11 turns it into `pod_schedule/1` and the OR-23 page.

**Test:** a fixture episode of 3 scenes where the cheapest plan is known by hand (two stills of one set that one wide covers,
one still whose crop would keep an extra prop and must not be R1, one library hit, one hero needing a new angle); the solver
must return exactly that plan, and every constraint is tested by its own failing case.

## 5. Sound: at the start or at the end?

**What depends on word timings in the code today:**
- `production/timing.py`: every shot's start and end frame tiles the read; below 97 % word match it FAILs (PV-20).
- `audio/spine.py` (`audio_spine/2`): the one clock the picture, compensators and sound lock to; LTX-native dialogue windows
  (D-88) are reserved in it and retimed from the clip.
- D-90: a character's fixed voice is read first and then conditions the dialogue clip (a2v).
- J5 lip sync (`assemble_25d`, `rigs.LipSync`): mouth cues come from the read's words or Rhubarb on the line's audio.
- `build_video_v2`: a clip shorter than its shot is refused, never stretched.
- D-67 (`production/sample.py`): the sample already pays pictures AND narration for the first two parts only.

**Order A, voice first (recommended):** script approved → read the sample parts (EST ~1,800 credits for two parts of a 12-min
episode, ~$0.35; the whole 12 min EST ~10-11k credits ≈ $2) → spine → visual script with exact frames → LTX clips sized once.
Pro: every frame count is final before the pod; dialogue clips can be a2v; lip sync is exact; no re-render. Con: a script
change after the read costs a re-read of that part (cheap, `splice_read.py` exists).

**Order B, voice last:** visual script on the syllable estimate (`scripting/syllables.py`, calibrated), clips sized with
bigger handles, read at the end, edit fits the picture to the voice. Pro: no credits until the end. Con: every estimate miss
is either a clip that is too short (refused: a re-run on the pod) or a long handle paid on every clip; a2v and exact lip sync
are impossible; the measured ElevenLabs pace differs from text estimates (BP-01 zones, hype read).

**Recommendation:** A, read part by part, in step with D-67: read the sample parts, build and approve their visual script,
run them; read the rest only after the sample is approved. The visual script may be drafted on the estimate earlier (free)
so the creator sees the full picture while the read is pending; it is rebuilt on the read before any paid picture.

## 6. Work packages (all free until the paid sample)

Sizes are EST hours of a Sonnet worker; each package = its focused tests + a PROGRESS entry (invariant 11); one PR each into
the active ICW line (Q-open-1 below).

| WP | What | Builds on | Test | h |
|---|---|---|---|---|
| V0 | `visual_script/1` schema + `core/contracts` check + CONTRACTS entry | route_shots/draft0, shot_spec/3 | schema accepts the converted route-test fixture; each rule of §2 has a failing case | 3 |
| V1 | `visual/visual_script.py build`: film_shots/3 + lanes + spine (or estimate) → visual_script | lanes.py, spine.py, timing.py, syllables.py | the route-test cards rebuild the fixture's shots and seconds; frames tile the spine exactly | 6 |
| V2 | `visual/ltx_prompts.py`: clips per shot, 8k+1 frames, handles, chains, numbering, motion line | layout_passes geometry, ltx_jobs | 12 s battle = 2 × 145 f overlap 8; numbering stable on rebuild; BP-172 cap | 4 |
| V3 | `visual/still_needs.py`: still per clip, `in_shot` with reasons, START pose; Blender visibility check in `bpy` | pilot_stills.py, world_layouts | pilot room: two-shot still lists host, guest, table only if c1 uses it; an extra visible object FAILs | 6 |
| V4 | `asset_needs/1` derivation + OR-18 search record per item | compose/library.needs, assets_reuse, scene_assets/1 | fixture: needs = exactly the missing sheets/angles/props | 4 |
| V5 | `visual/still_prompts.py`: Blender job + Qwen edit prompt from the still | p14_qwen job format, style_prompt.check | ≤ 90 words, no camera words, tags once, in_shot only | 4 |
| V6 | `visual/reuse_plan.py` solver + `asset-reuse-planner` agent page | compose/reuse, cloud/schedule cost | §4 fixture returns the hand-known plan; every constraint's failing case | 8 |
| V7 | reuse_plan → `pod_schedule/1` stages + OR-23 page generator; p15 pod package (p14 reused) | cloud/schedule, training/pods/p14 | RP-11 `check` exits 0; dryrun; OR-33 step-by-step save proven | 6 |
| V8 | `qa/clip_check.py`: identity (sheet vs frames), flicker, jitter, length ≥ shot (G9) | keyframe gate, LT rules | synthetic clips: a flicker and a short clip FAIL | 4 |
| V9 | assembly over the sample / episode by visual_script ids (pilot.py generalised), spine audio, mix | pilot.py, assemble.py, sample.py | a slate run of the fixture builds a full-length preview with audio | 3 |
| V10 | `visual_script.md` readable page + an end-to-end free dry run (estimate timing, slates) in CI | all above | CI builds the preview of the fixture episode | 2 |

Order: V0 → V1 → V2 → V3 → V5 → V4 → V6 → V7 → V8 → V9 → V10 (≈ 50 h EST). V8 can run any time after V2. After V10: the Fable
audit of the whole repo (OR-34), then the one paid run = the D-67 sample through the chain (OR-23 plan generated by V7, Opus
confirms, the creator's word, Haiku watchdog). Before V6's numbers are trusted, the running pilot (PILOT_1MIN_PLAN v2) must
deliver the measured LTX seconds per clip.

## 7. Questions only the creator can answer (to the Fable thread, 4 options each; recommended = ★)

**Q1. When is the narration read?**
★ A) the sample parts are read before the visual script; the rest after the sample is approved.
B) the visual script on an estimate; the read after it, but before any paid picture.
C) the read at the very end; the edit fits the pictures to the voice (bigger clip handles, no a2v).
D) the whole episode read at once before the visual script.

**Q2. Who picks the reuse combination?**
★ A) code computes every combination and takes the cheapest; an agent reviews only the doubtful rows.
B) an agent decides everything, the code only gives costs.
C) code only, no agent.
D) code proposes, you approve every pick.

**Q3. May a reused still contain things its clip does not need?**
★ A) no: reuse only when, after the crop, the frame holds exactly the clip's list.
B) yes, if the extra thing is outside the area that moves.
C) yes, if the LTX prompt says it stays still.
D) no reuse of stills at all: every clip its own render.

**Q4. How long is an LTX clip against its shot?**
★ A) rounded up to the next valid length (≤ +0.33 s), the extra trimmed in the edit.
B) one more step of handle on top (≈ +0.33 s more), for safer cuts.
C) exactly the shot; the shot is retimed to the clip.
D) two takes of every clip, the better one picked.

**Q5. Do you approve the visual script before anything is paid?**
★ A) yes: one readable page per part (shots, clips, what is in each still).
B) no: only the sample video.
C) both the page and the sample.
D) only the numbers (clips, pictures, $).

**Q6. What is the first paid run of this chain?**
★ A) the D-67 sample (first two parts of a real episode) through the whole chain.
B) one scene of the episode first.
C) the plan for the whole episode, but pay only the sample.
D) first finish the current room/soldiers pilot, then decide.

## 8. Open for Fable (not the creator's), and what I did not verify

- **Branch:** the project rule says `systemic/next-video`, but that branch exists only as a backup tag
  (`backup/pre-delete-2026-11-02/systemic/next-video`); the live line is `icw/*` (newest `icw/17-run-schedule` 36cf22b,
  `icw/18-pilot-room` not on the remote yet). Which base the V-packages target is Fable's call.
- `film_shots/3` card fields for the action (start/peak/settle) exist from /1-/2; that every /3 card carries them for the motion
  line was not checked on a real episode.
- The Blender visibility check (V3) needs a bpy frustum test; not prototyped.
- ElevenLabs credit numbers are EST from earlier ledgers (2,337 credits for ~2,400 characters).
- LTX seconds per clip and whether 8 s holds are the pilot's to measure; V6/V7 read them from `job_speeds.json`.
- Nothing here changes a rule, a cap or a decision; the new schemas need a D-entry when V0 lands (proposed D-118
  "visual script is the one plan of the picture").

## 9. Fable's answers (2026-11-06 16:13 UTC)

- Q1-Q5 are on the creator's cards in the Fable thread; V0 waits for the answers.
- Q6 is settled by the creator's 16:05 words: the current room/soldiers pilot first, then the D-67 sample (option A).
- Base branch for V0-V10: `icw/05c-ink-round` (icw/17-run-schedule merges into it via icw/16-lean-pod); never main;
  systemic/next-video is history.
- LTX seconds per clip: read from `cloud/job_speeds.json`, written by the pilot pod; never estimated in V2/V6.
