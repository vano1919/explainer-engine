# Scene assets and the J5 2.5D assembly

> **Route-scoped since D-116 (2026-11-06), amended by D-122 (2026-11-08):** this page documents J5 asset assembly as an optional
> component within an LTX-first dialogue route (a J5 shot itself contains no LTX) and to the
> first frames of J2/J4. The routes and their default mapping live in the [decision log](DECISIONS_AND_OPEN_QUESTIONS.md) (D-116) and
> in `explainer_engine/visual/archetypes_ic.json`; the plan is [ROUTE_PLAN_2026-11-06](architecture/ROUTE_PLAN_2026-11-06.md)
> (D-121: flat-lit sheets, four mouth states (closed, half, wide, round) with a two-frame cross-blend, the horizon check on a 30-degree pan).


## Stage 2 2D Master Asset & Cast Creation (D-123 Rebuild)
- **Mandatory 3D `.blend` & Grease-Pencil Scene Building Retired from Default (D-123):** Stage 2 creates and locks 2D reference anchors in `02_keyframes/assets/` (`char_<id>_turnaround.png`, `loc_<id>_anchor.png`, `prop_<id>_anchor.png`) declared in `world_bible` ([MAIN_METHOD](MAIN_METHOD.md) Stage 6 & Stage 7).
- **Optional Local 2.5D Fallback Only:** `explainer_engine/blender/assemble_25d.py` is retained strictly as an optional local deterministic 2.5D plane renderer alongside `ComfyUI-Depthflow-Nodes` and `explainer_engine/production/parallax.py`. The `SA-01..SA-09` rules below govern 2D cutouts and optional 2.5D card assembly.

Work package ICW-11 (guide step 2.1). Qwen-Image-2.1 + xworld_v2 supplies approved scene assets when a selected route needs them: one 360 backdrop, only the approved hero drawings actually needed, and props. Do not automatically generate every angle from a hero sheet: RF-03 (3)-(4) keeps mouth/blink/expression variants on the same approved drawing and leaves a new pose/angle reference unapproved until measured. No Blender/3D render is ever a Qwen input (D-120/RF-01). LTX is the primary dialogue visual route; use its footage directly when it covers the exchange. J5 assembles approved assets only for optional close-ups/reactions when there is a measurable quality-preserving production benefit (D-122). The creator's visual review decides naturalness; a successful render alone is not acceptance.

## The flow

1. **The manifest** `scene_assets/1` ([CONTRACTS](CONTRACTS.md), `schemas/scene_assets.schema.json`): per scene the backdrop
   (`backdrop_360`: asset id, prompt, size, LoRAs, turn, file), the heroes (sheet id, prompt, `lighting_note`, real height, card
   files for each supplied approved angle (front / 3q_left / 3q_right / back; an angle is not required unless a shot uses it): `base` = rest/closed, `mouth_half`, `mouth_wide`, `mouth_round`, optional legacy `mouth_open`, `blink` = an eyes-closed
   overlay patch), the props (prompt, real height, file), the light variant and the defects with their Qwen edit instruction. A
   file is `{path, sha256}`, or null until the asset pod has drawn it. The drawing stack is `qa/style_prompt.INFERENCE`.
2. **Drawing** (the asset pod, paid, OR-23): the prompts go through `qa/style_prompt.check`; every image passes the keyframe gate
   (KG-, at most three tries) before it is used; a defect is fixed by a Qwen edit, never by drawing the hero again (invariant 6).
3. **Cut-out** (`edit/cutout.py`, free): BiRefNet (`config/cloud_pins.json` `models.cutout_birefnet`, MIT) predicts the matte on the
   pod; `finish` feathers a hard matte to a 2 px edge (a BiRefNet matte is already that soft and is kept) and takes the rim's colour
   from the nearest opaque pixel; `check` runs AC-15 ([ASSET_COMPOSE](ASSET_COMPOSE.md)) and SA-04.
4. **Assembly** (`blender/assemble_25d.py` plans, `blender/bpy/assemble_25d.py` builds and renders, free): the backdrop is the
   world, every hero and prop a camera-facing card standing on its feet at its real height, a flat contact shadow under each hero,
   the four mouth states and the blink as keyed mixes of the card's images, breathing as a keyed scale; the camera from `blender/camera_setups.py`
   (`mcu_front` for the dialogue close-ups; the reverse is the same setup with the subjects swapped). PNG frames, 24 fps.

A shot (the planner's input) names its scene, seconds, the camera (`setup`, the cast members that stand for the setup's subjects
`a` and `b`, or a position for an off-screen subject; `pan_deg` for a pan on the spot) and the cast (position of the feet, the card
angle, and for the speaker the line's mouth cues: `audio/words_to_mouth_cues.py` or Rhubarb, read by `blender/rigs.LipSync`).

## Rules

| ID | Rule | Severity | Code |
|---|---|---|---|
| SA-01 | Every hero prompt carries the lighting note "flat ambient lighting, no cast shadows" (the `lighting_note` field is that text and nothing else): the sheets are lit flat, so a card can stand in any light (plan 9) | FAIL | `core/contracts._scene_assets`, the schema |
| SA-02 | A 360 backdrop is equirectangular: width = 2 x height | FAIL | `core/contracts._scene_assets` |
| SA-03 | A defect names an asset of its own scene, and its instruction starts "change nothing, fix: ..." (an edit of the drawn image, never a redraw); a hero is listed once per scene | FAIL | `core/contracts._scene_assets`, the schema |
| SA-04 | A card is an RGBA PNG of the figure alone (AC-15); its rim carries the figure's own edge colour: a halo score (mean luma gap between the semi-transparent rim and the nearest opaque pixel, share of 255) over 0.06 is a REVIEW. The threshold is an engineering default: on the four 10-25 BiRefNet cut-outs the straight cut scored 0.30-0.50 and `finish` 0.0005-0.0006 | FAIL (mode, AC-15), REVIEW (halo) | `edit/cutout.check` |
| SA-05 | The manifest's drawing stack is `qa/style_prompt.INFERENCE` (base, LoRA, weight), which reads `cloud_pins` (one home) | FAIL | `core/contracts._scene_assets` |
| SA-06 | A speaking card has four mouth states (base = rest/closed, half, wide, round), all the size of the base card; Rhubarb shapes map A/X to rest, B/C/G/H to half, D to wide, E/F to round, with a two-frame cross-blend; a lip-synced shot keeps BP-108's dialogue limit | FAIL (planner refuses) | `blender/assemble_25d.plan`, `rigs.LipSync.plan` |
| SA-07 | No light in the scene and no card casts a shadow: a card emits its drawn colours (view transform Standard); the only shadow is the flat contact ellipse under the feet | FAIL (smoke) | `bpy/assemble_25d.py` report, `assemble_25d.smoke` |
| SA-08 | On a 30-degree pan a straight horizontal line of the backdrop bends by at most 1 % of the frame height (measured on the smoke's 360 test grid; a real backdrop's seam and horizon are the creator's eye) | REVIEW | `assemble_25d.horizon_bend` |
| SA-09 | Life on a held card: a blink every 3-5 s (seeded per shot and hero, three frames, only when the sheet has the eyes-closed patch) and breathing of 0.5 % vertical scale at 0.25 Hz about the feet (plan 9) | - | `assemble_25d.blink_track`, `breath_track` |

## D-120 / DL-02 integration boundary

J5 close-up jobs derive a Gaussian-blurred panorama from the same approved 360° source used by the scene. The renderer records the original path and hash plus the derived file hash; it never edits the approved source or calls Qwen for a second background. Wide shots keep the sharp source. The 40 px blur is a starting value only; visual review must confirm that landmarks are not readable and continuity is preserved.

## D-121 update (2026-11-08)

The earlier three-state J5 mouth contract is superseded by D-121. A speaking card now requires `mouth_half`, `mouth_wide`, and `mouth_round` in addition to the rest/closed `base`; `mouth_open` is retained in the schema only as a deprecated legacy field and is not consumed by the current renderer. The planner and Blender material implement the same sequential four-state blend. The synthetic smoke now plans a separate actual-render probe for each state and compares the decoded frame pixels; its figures are still placeholders and it does not replace the real visual dialogue benchmark.

## D-122 LTX-first dialogue

The conversation's opening is normally an LTX establishing two-shot, with about 5-9 seconds as the pilot test target rather than a universal duration. If that segment contains enough usable dialogue footage, keep it and create no J5 cut-outs. If the exchange needs more coverage, compare further LTX footage with optional J5 close-ups/reactions. Do not force a fixed sequence. The benchmark protocol and current evidence are in [DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08](research/stoneage_pilot_2026-11-07/DIALOGUE_BENCHMARK_TEMPLATE_2026-11-08.md).

## Measured (2026-11-06, the cloud container, free)

- Cut-outs: the four 10-25 BiRefNet cut-outs (HF `film_1min_2026-10-24/comp_test/img/cut_*.png`): halo 0.30-0.50 as cut, 0.0005-0.0006
  after `finish`; their soft edge is 2.5-3.1 px, so no second blur; the girl's cut still fails AC-15 (the snow patch the 10-25 test found).
- Assembly smoke (`python -m explainer_engine.blender.assemble_25d smoke`, Blender 5.2.3 bpy wheel, EEVEE on the CPU, 480x270,
  4 samples): the four dialogue shots and the pan, 24 frames each, about 1.8-2.0 s per frame; no shadow-casting card; the target
  lands on the setup's thirds point (`mcu_front` 0.5000, 0.6667); horizon bend 0.37 % (one pixel). These are not PC numbers: the
  `job_speeds.blender_25d_s_per_frame_pc` row is filled only by a render on the creator's PC.
- Not done yet: the real J5 dialogue at 1440p waits for the asset pod's sheets and backdrop (step 2.2); then it renders on the
  PC and goes to `route_test_2026-11/j5_dialogue/` for the creator's eye.
