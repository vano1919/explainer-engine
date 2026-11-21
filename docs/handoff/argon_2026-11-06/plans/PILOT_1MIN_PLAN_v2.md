# Pilot: Blender stills from the libraries, then Qwen, then one 8 s LTX shot per scene (DRAFT v2)

**Status (2026-11-06 ~16:10 UTC):**
- The free part is done or running. Nothing paid is built or launched.
- This replaces draft v1 (10-12 storyboard shots, 52 s). v1 is kept as an appendix.
- The creator's scope, 15:25 UTC, in the Fable thread: build the Blender frames, but not only the placement of people and the main objects. Use the libraries to furnish everything: if a clock belongs in the room, build the room with the clock, the table and everything else as 3D models. First a scene of a few minutes in a room, then another shot with many soldiers. Then test whether LTX can hold one single-scene 8-second shot.

## Question it answers

Does LTX-2.5 distilled i2v hold **one 8 s single-scene shot** that starts from a Blender-composed, Qwen-styled frame, once in a furnished room and once with many soldiers?

A side question: do positions and props stay the same across camera angles of one set once Qwen restyles each still? This is checked on the stills alone, before any LTX run.

## Stage 1: free, done in this container (Blender 5.2.3 pinned, EEVEE on the CPU)

### Room set: layout `pilot_room` in `world_layouts.json`

**Built from:**
- **Walls:** Quaternius Medieval Village MegaKit plaster walls, 8 x 6 m, all four sides closed. Three arched windows and a door. A wooden ceiling.
- **Floor:** Poly Haven weathered planks.
- **Furniture and props:** 16 new Poly Haven CC0 pieces, registered 2026-11-06 with md5 per file, sha256 and fingerprint:
  - vintage grandfather clock and a wall clock;
  - plain wooden table, two painted chairs, stool, bench;
  - worn bookshelf, masonry stove, chest of drawers, picture frame;
  - jug, two carved plates, wooden bowl, candlestick, wicker basket.
- **Existing pieces:** gothic cabinet, wine barrel, bucket, lantern.
- **Cast:** three Quaternius UBC/MCO characters.
  - host, ranger costume;
  - guest, peasant woman;
  - elder.
  - Host and guest face each other across the table.

**Cameras.** Seven, all static, all at 2560x1440. Positions, props and cast are identical in every shot; only the camera moves.

| Shot | What | Lens | s/frame |
|---|---|---|---|
| room_establishing | wide from the stove corner | 16 mm | 40.7 |
| room_two_shot | host and guest across the table | 28 mm | 47.9 |
| room_close_host | over the guest's shoulder | 55 mm | 43.7 |
| room_close_guest | over the host's shoulder, same side of the line (180° rule, tested) | 55 mm | 37.5 |
| room_reverse | wide from the clock corner | 18 mm | 39.1 |
| room_insert_table | the table, jug, plates, candle | 35 mm | 48.5 |
| room_insert_wall_clock | the wall clock | 50 mm | 41.8 |

**Look.** The reference look v01 (soft 3D, colour); Qwen does the final look. The wall clock keeps its own glTF materials, so its dial shows behind the glass. With one toon material its glass hid the dial; that is tested.

**Known flaws:**
- The wall clock reads modern.
- The bookshelf reads pale and empty.
- The grandfather clock's face is dark: its glass covers the dial. It reads as a clock only in the wides.
- The windows show a bright sky.
- In the establishing wide the elder stands at the left edge.

### Soldiers scene: the existing `battle` composition

- 5,000 Quaternius soldiers as crowd tiers: a wedge charging a shield wall.
- Frames 0 and 200, colour and depth passes, no Freestyle, 1920x1088 (the LTX size), via `layout_passes render --only-frames 0,200`.
- Seconds per frame: **filled in when the render ends** (it is running now).

### Upload

All stills go to HF `route_test_2026-11/pilot/blender/<shot>.png`, together with:
- `pilot_room_layout.json` (the full layout);
- `pilot_stills.json` (per shot: camera location, look-at, lens and FOV, sha256, seconds per frame).

The new code is `explainer_engine/blender/pilot_stills.py` (cameras, manifest, upload) with tests, on branch `icw/18-pilot-room`. CI workflow `pilot-stills.yml` re-renders the same stills for free.

## Stage 2: paid, the Qwen restyle (plan only)

- **Model:** Qwen-Image-2.1 + xworld_v2 ck3000 at w0.7. The conditioning is B's (`p14_qwen.py`): a multi-image edit with no ControlNet.
  - Image 1 is the Blender still. B used the line pass; here it is the colour still, as Fable allowed "clay or colour".
  - Images 2-3 are the hero turnaround fronts, pinned by sha256.
- **Prompt:** "keep every figure's place, size and pose" plus a description of the shot.
- **Settings:** true_cfg 2.5, 30 steps, seed 11, 1280x720 out, then cover-cropped to 1920x1088 for the LTX first frame.
- **Jobs:** 9 edits, the 7 room stills and the 2 battle colour frames, so the creator can judge consistency across angles.
- **Where it runs:**
  - **A, on the pod:** measured on pod 1's H100 NVL as 61 s load plus 33.5-38.5 s per edit, about 6.5 min in all.
  - **B, on the creator's PC:** free. It depends on the PC speed test Fable asked for (RX 5700 8 GB, Qwen Q4 in D:\qwen-local).

## Stage 3: paid, LTX-2.5 distilled i2v, one shot per scene (plan only)

- **Model:** `Lightricks/LTX-2.5` @ `49b093a3…`, sha256 `31eb3cad…`, run with `ltx_pipelines.distilled` at code pin `e98f6d9`. No LoRA, no control video.
- **Clips:** two of them:
  - the restyled **room_two_shot** (host and guest talking: gesture and small motion);
  - the restyled **battle frame 0** (mass motion).
- **Clip settings:** 193 frames at 24 fps (8.04 s), 1920x1088, seed 42.
  - **Open item:** 193 frames is 8.04 s, just over BP-172's "at most 8 s". 185 frames would be 7.71 s. Fable or the creator picks.
- **Prompts:** the style sentence plus one motion line each:
  - room: "the host talks and gestures, the guest listens and nods; the camera holds still";
  - battle: "the wedge charges forward into the shield wall, dust rises; the camera holds still".
- **Cap:** 15 min per clip, set as the schedule max. Two failures stop the stage.
- **Speed:** unmeasured. The estimate is about 6 min per 193-frame clip on the H100.

## Stage 4: free, after the pod

FFmpeg puts the two clips side by side with their first frames, using `production/pilot.py` from ICW-15 for the conform. There is no narration: the question is the motion. The creator watches it.

## OR-23 items

- **Purpose:** the question above.
- **Model and checkpoint:** Qwen-Image-2.1 with xworld_v2 ck3000 at w0.7, and LTX-2.5 @49b093a3, as above.
- **Data:** the stills from stage 1 (on HF, pinned by sha256) and the three hero sheets (on HF, pinned).
- **Settings:** stages 2 and 3.
- **Outputs and HF paths:** under `route_test_2026-11/pilot/`, uploaded as they land (OR-33):
  - `qwen/<shot>.png` plus a sidecar;
  - `first_frames/<shot>.png`;
  - `ltx/<room|battle>.mp4` plus a sidecar;
  - `speeds.json`.
- **GPU and price.** RP-11, `python -m explainer_engine.cloud.schedule check` exits 0 for both files. The A100 is cheapest in both:

  | Schedule | Card | Expected | Worst case |
  |---|---|---|---|
  | **A: Qwen on the pod** (`pilot_1min/pilot_schedule_v2_qwen_on_pod.json`) | A100 80GB COMMUNITY, $1.39/h, 0.6x | **$1.25** (0.90 h) | **$2.95** (2.12 h) |
  | same | H100 NVL COMMUNITY, $2.59/h | $1.80 | $3.86 |
  | **B: Qwen on the PC** (`pilot_1min/pilot_schedule_v2_qwen_on_pc.json`) | A100 80GB | **$0.98** (0.70 h) | **$2.12** (1.53 h) |
  | same | H100 NVL | $1.47 | $2.89 |

  The GPU is never idle in either schedule. Both fit the current caps (max-usd 8, max-hours 3.5).
- **Caps (proposed):** max-usd 3.5 and max-hours 2.5 for A; max-usd 2.5 and max-hours 2 for B. The balance is ~$8.04.
- **Stop conditions:**
  - the 10-min deadline reserve;
  - two LTX failures;
  - Qwen producing no picture;
  - the money dead-man.
- **What he sees:**
  - the 7 room stills and 2 battle frames, Blender beside Qwen;
  - the two 8 s clips beside their first frames.
- **What follows:**
  - **If both clips hold:** the episode route becomes Blender stills, then Qwen, then LTX i2v. Blender video passes are used only where a shot needs them.
  - **If the battle breaks:** crowd shots keep Blender video control (J4).

## Work still to build before the audit (free)

1. A pod package `training/pods/p15/` reusing `p14_qwen.py` (job list from `pilot_stills.json`) and `p14_ltx.py` (two i2v jobs at 193 frames), with:
   - the RP-11 schedule above;
   - a sha256-pinned bundle;
   - tests and an offline dry run.
2. For option B, the PC Qwen run (a Remote Control step on the creator's PC; free).

## Open, for the creator (through Fable)

- Qwen on the pod (A) or on the PC (B).
- 193 frames (8.04 s) or 185 frames (7.71 s).
- Which room shot LTX animates (proposed: the two-shot).

---

## Appendix: draft v1 (superseded by the creator's 15:25 UTC scope)

v1 planned the river-field segment (place A3) of `new_route_shots.json`: 12 shots, 11 LTX clips, ~52 s with narration.
- Two sets would reach 74 s.
- S04/S05 needed a new ~$0.08 narration take.
- RP-11 for that run: A100 $2.54 expected / $5.98 worst (needs max-hours 4.5); H100 $3.24 / $7.25.
- Its schedule is `pilot_1min/pilot_schedule.json`.
