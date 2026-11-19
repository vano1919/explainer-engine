# Pilot: Blender stills from the libraries, then Qwen, then one 7.7 s LTX shot per scene (DRAFT v3, for Fable's audit)

**Status (2026-11-06 ~16:30 UTC):** the free part is done. Nothing paid is built or launched. v3 applies Fable's decisions of
15:52 UTC (option A only: Qwen on the pod, the creator cancelled the PC run; 185 frames; the room clip is the two-shot), the
creator's rule of 15:53 UTC (a still holds only what its clip needs) and Fable's 15:57 UTC note (prompts generated from shot
cards). v2 is kept as `pilot_1min/PILOT_1MIN_PLAN_v2.md`.

## Question it answers

Does LTX-2.5 distilled i2v hold **one 7.7 s single-scene shot** that starts from a Blender-composed, Qwen-styled frame, once in a
furnished room and once with many soldiers? Side question, on the stills alone: do places and props stay put across the room's
camera angles once Qwen restyles each still?

## Stage 1: free, done (Blender 5.2.3 pinned, EEVEE on the CPU)

**Room** (layout `pilot_room`): Quaternius MegaKit plaster walls, 8 x 6 m, closed on all four sides, three arched windows, a door,
a wooden ceiling, a planks floor; 18 Poly Haven CC0 pieces registered 2026-11-06 (md5 per file, sha256, fingerprint) plus four
existing ones. Fix round: no wall clock, no white chairs, no picture frame; dark gallinera armchairs; a mantel clock on the drawers
and the grandfather clock with their glass removed so the dials show; UAL1 poses (host talks seated, guest listens seated, the
elder kneels feeding the stove); light from the stove glow, the candle flame and one shadowless fill (no SSR, no AO).

**Every still is the first frame of a planned clip** (standing order 14). Each shot has an `in_shot` list (name and reason); the
still renders only those plus the room. The Qwen and LTX prompts are generated from the shot card (`pilot_stills.prompts`):
trigger, the clip's start, place and era, light; at most 90 words; clean under `qa/style_prompt.check`; each tag once.

**Cast to heroes** (for the Qwen reference images): host = H1 commander, guest = H2 scout, elder = H3 elder. The Blender figures are
stand-ins for pose and place only; Qwen draws the heroes from their turnaround fronts.

| Shot | In the still | Lens | s/frame |
|---|---|---|---|
| room_establishing | host, guest, table, chair_n, chair_s, clock, bookshelf, drawers, mantel_clock, candle, jug | 16 mm | 54.4 |
| room_two_shot | host, guest, table, chair_n, chair_s, candle, jug, plate_n, plate_s, bookshelf | 30 mm | 66.1 |
| room_close_host | host, guest, chair_n, table, candle, bookshelf | 50 mm | 65.4 |
| room_close_guest | guest, host, chair_s, table, candle, cabinet | 50 mm | 62.3 |
| room_reverse | elder, stove, host, guest, table, chair_n, chair_s, cabinet, basket, bucket | 18 mm | 49.9 |
| room_insert_table | table, jug, plate_n, plate_s, bowl, candle | 35 mm | 64.7 |
| room_insert_clock | mantel_clock, drawers, lantern | 60 mm | 53.9 |

The reasons for each entry are in `pilot_stills.json` (`in_shot`). Contact sheet: `pilot_1min/stills/room_contact_sheet_v2.jpg`.

**Soldiers:** the existing `battle` composition: 5,000 Quaternius soldiers as crowd tiers, no Freestyle, 1920x1088.
Frames 0 and 200, colour and depth. Colour took **202.3 s/frame** (404.6 s for both frames, including the crowd bake); depth took
**238.1 s/frame**. Frame 0 shows the near army from behind, facing a far army under orange banners, with a blue banner. It has no
commander and no river, so its card names no hero.

**On HF** `route_test_2026-11/pilot/blender/`, sha-checked after the upload:
- 7 room PNGs at 2560x1440 and 4 battle PNGs;
- `pilot_room_layout.json`;
- `pilot_stills.json`, which holds per shot: camera, lens and FOV, sha256, s/frame, `in_shot`, and both prompts.

The round-1 `room_insert_wall_clock.png` is still there, but no manifest names it.

## Stage 2: paid, the Qwen restyle (pod)

- **Model and LoRA:** Qwen-Image-2.1 + xworld_v2 ck3000 (sha256 `f5c420a1…`) at w0.7.
- **Settings:** true_cfg 2.5, 30 steps, seed 11, 1280x720. The output is then cover-cropped to 1920x1088 for the LTX first frame.
- **Images per edit:** Image 1 is the Blender colour still. Images 2-3 are the hero fronts that the card names:
  - two-shot: B_H1 and B_H2;
  - reverse: B_H3;
  - inserts and the battle: none.
- **Jobs:** 8 edits, the 7 room stills and battle frame 0. Frame 200 and the depth pass are no clip's first frame, so they are not
  restyled. The room's other 6 restyles answer the side question (does the set stay the same across angles).
- **The two-shot prompt** (76 words, generated):
  > xworld style, Image 1 is the scene: keep every place, size and pose. Image 2 is the commander. Image 3 is the scout. The broad commander with a grey beard and a red cloak sits leaning forward with open hands mid-sentence, the young scout in a green hood sits across a plain wooden table listening, in a timber-framed farmhouse room in a medieval village at dusk, lit by warm firelight and the glow of one candle.
- **The battle prompt** (71 words, crowd sub-category V1, under the 90-word clone limit):
  > xworld style, Image 1 is the scene: keep every place, size and pose. A dense army of lanky soldiers in green tunics, each with his own face and helmet stands ready, facing a far army under orange banners across the field, a big blue banner on a pole above them, in a dusty plain below a grassy ridge in a medieval war, lit by a low golden sun under drifting clouds.

## Stage 3: paid, LTX-2.5 distilled i2v, one clip per scene

- **Model:** `Lightricks/LTX-2.5` @ `49b093a3`, sha256 `31eb3cad…`, run with `ltx_pipelines.distilled` at code pin `e98f6d9`.
  No LoRA, no control video, no upscale.
- **Clips:** the restyled room_two_shot and the restyled battle frame 0.
- **Settings:** 185 frames (7.71 s, 8k+1, BP-172), 24 fps, 1920x1088, seed 42.
- **Prompts**, from the same cards:
  - room: "Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon timing, poses hold between quick moves. The broad commander with a grey beard and a red cloak talks and gestures with both hands; the young scout in a green hood listens and nods once; the candle flame flickers, then both hold still, eyes on each other. Static camera."
  - battle: "Hand-drawn 2D cartoon animation with bold black ink outlines, big bulging eyes and bright colours; snappy cartoon timing, poses hold between quick moves. The near army charges forward across the plain, dust rises and the banners flap, then the two armies meet in a cloud of dust. Static camera."
- **Overlap with fix 2:** X7 in fix 2 of the step-3 pod is nearly the same battle clip (the B prompt, 121 frames). If this pilot runs
  first, X7 can drop out of fix 2. That is Fable's call.

## The pod package (free, built): `training/pods/p15/` on branch `icw/19-pilot-pod`, draft PR #149

- `p15.json` comes from the uploaded manifest: every still and hero sheet is pinned by sha256, and the prompts must match the cards.
- `p15_pod.py` runs two lanes:
  - net: the Qwen weights, then the LTX weights;
  - gpu: restyle, then ltx_room, then ltx_battle, then F.
  - Each clip starts only when its first frame exists. Each timeout is the schedule's max. Two LTX failures stop the stage.
- `p15.sh` is the step-3 stack without Blender. Its heartbeat is `route_test_2026-11/pilot/beat.txt`, so outputs land in
  `route_test_2026-11/pilot/{qwen,first_frames,ltx}/` plus `stages.json` and `speeds.json` (OR-33).
- **Bundle:** `code/p15/ee_src.tar.gz`, sha256 **`0ac0125c37529146a25a89082c2b94ecfac3a8989d0b090599b16bc96ed3bc37`**.
  - It is pinned in `p15.sh` at commit `a6cc403`.
  - The bundle of `a6cc403` reproduces that sha.
  - The worker uploads it from the audited commit; it is NOT uploaded yet.
- **Checks:**
  - `runpod dryrun --script p15.sh`: ok (record sha256 `0c3315bf…`);
  - 8 tests in `tests/unit/test_p15_pilot_pod.py`;
  - docs_lint: 0 findings.

## OR-23 items

- **Purpose:** the question above.
- **Model and checkpoint:** as in stages 2 and 3.
- **Data:** the stills on HF and the hero fronts, all pinned.
- **Outputs:** under `route_test_2026-11/pilot/`, uploaded as they land:
  - `qwen/<shot>.png` plus a sidecar;
  - `first_frames/<shot>.png`;
  - `ltx/<job>.mp4` plus a sidecar;
  - `stages.json` and `speeds.json`.
- **GPU and price:** RP-11 (`python -m explainer_engine.cloud.schedule check explainer_engine/training/pods/p15/p15_schedule.json`) exits 0.

  | Card | Expected | Worst case |
  |---|---|---|
  | **A100 80GB COMMUNITY $1.39/h (the pick)** | **$1.21** (0.87 h) | **$2.83** (2.04 h) |
  | H100 NVL COMMUNITY $2.59/h | $1.75 | $3.73 (over the cap) |

  The GPU is idle for 0 minutes in both cases.
- **Speeds behind the estimate:**
  - Qwen was measured on pod 1's H100: 61 s to load, then 33.5-38.5 s per edit.
  - LTX is unmeasured: 185 frames are estimated at about 5.8 min per clip on the H100, with a max of 17.5 min.
- **Caps (in the schedule):** max-usd 3.5 and max-hours 2.5. The balance is about $8.04.
- **Stop conditions:**
  - the 10-minute end reserve;
  - two LTX failures;
  - a clip with no first frame is skipped;
  - the money dead-man and the wrapper's stall check (30 min).
- **What the creator sees:**
  - the 8 Blender stills beside their Qwen restyles;
  - the two 7.7 s clips beside their first frames.
- **What follows:**
  - **If both clips hold:** the route becomes Blender stills, then Qwen, then LTX i2v. Blender video passes are used only where a
    shot needs them.
  - **If the battle breaks:** crowd shots keep Blender video control (J4).

## Known flaws of the stills (Qwen redraws the look)

- The bookshelf reads pale and the candle flame is not visible.
- The Blender cast are stand-ins: the guest's figure is a ranger costume.

## Launch (after the OR-34 audit, through the worker)

1. Upload the bundle `jobs/p15/ee_src.tar.gz` (built from `a6cc403`) to HF `code/p15/ee_src.tar.gz`.
2. Run `runpod create --script explainer_engine/training/pods/p15/p15.sh --schedule explainer_engine/training/pods/p15/p15_schedule.json`
   with A100 80GB, `--max-usd 3.5`, `--max-hours 2.5` and the ledger.
