# REUSE: what exists today, and the reuse plan rows R0-R5

## 1. What exists (open the files; do not trust this list over them)

| thing | file | what it does today |
|---|---|---|
| composed-frame reuse (AC-12/AC-13) | `explainer_engine/compose/reuse.py` | a shot that returns to a setup (background, camera angle, cast) is a crop of the earlier frame when it enlarges at most `ZOOM_MAX` 1.6; measured in the old era: about 20 % of shots return to an earlier setup (3312 shots) |
| the rest of `compose/` | `library.py`, `frame.py`, `episode_look.py`, `crowd.py`, `style_score.py` | the old-era asset composer (home: [ASSET_COMPOSE](../../ASSET_COMPOSE.md), AC-xx) |
| asset library | `explainer_engine/assets/library.py` | the library of drawn assets with licence per asset |
| picture library | `explainer_engine/imagegen/picture_library.py` | reusable pictures with tags: add, find, fetch (D-76) |
| library first | `explainer_engine/assets_reuse.py` | OR-18: search and record before any new music, SFX or reusable picture; the hook refuses a paid call without the record |
| cut-outs | `explainer_engine/edit/cutout.py` | BiRefNet mask, `finish`, `check` for J5 cards; CPU dtype fix included |
| J5 assembler | `explainer_engine/blender/assemble_25d.py` (+ `bpy/assemble_25d.py`) | equirect world, emission cards, three mouth states with a 2-frame cross-blend, camera; transparent flag |
| J5 dialogue code | `blender/j5_collage.py`, `j5_background.py`, `j5_face.py` | the dialogue test of PR #151 (home: [J5_DIALOGUE_COLLAGE](../../J5_DIALOGUE_COLLAGE.md)) |
| world kits / layouts | `blender/world_kits.py`, `blender/world_layouts.json` | sets, props and cameras per place; `dressing(layout, shot)` |
| pilot stills | `blender/pilot_stills.py` | the stills with `in_shot` per shot, Qwen and LTX prompts from shot cards |
| layout passes | `blender/layout_passes.py` | clay / colour / depth / line passes for the battle and the duel, clip geometry |
| scene assets | [SCENE_ASSETS](../../SCENE_ASSETS.md), `scene_assets/1` | the drawn scene assets and J5 assembly (SA-xx) |
| cost of a plan | `explainer_engine/cloud/schedule.py` (RP-11), `config/job_speeds.json` | costs every combination of a pod's run; the speeds table is **empty** today |

## 2. The reuse plan (from `plans/PLANNING_CHAIN_PLAN.md` section 4; not built, package V6)

Inputs: `visual_script/1` (stills with `in_shot`, cameras, sets), `asset_needs/1`, the libraries, the measured speeds, the pod cards'
prices. Options weighed per still or asset, cheapest first:

| code | option | allowed when |
|---|---|---|
| R0 | reuse a library picture or a still of an earlier episode as is | same place, era and cast; `in_shot` matches exactly |
| R1 | crop or zoom of another still of this episode (AC-12/13, ZOOM_MAX 1.6) | same set and camera side; after the crop the frame holds exactly `in_shot` (the creator's Q3 A) |
| R2 | J5 card: cut-out of an existing sheet or still placed on a 360/plate backdrop | a held or dialogue shot with no LTX motion of the body |
| R3 | one Blender render serving several stills (a wide at 1.6x size cropped per still), ONE Qwen edit | the stills share set, side and `in_shot` is a subset of the wide's, and the crop rule holds |
| R4 | new Blender render, new Qwen edit | the default for a clip's first frame |
| R5 | new Qwen asset (hero sheet angle, 360 backdrop, prop) | nothing in R0-R3 covers it; an OR-18 record with the reason |

Cost model: Blender seconds count as $0 but enter the wall clock; Qwen = load + per-edit seconds on the card (measured on the H100
NVL), divided by the card's speed; LTX = seconds per 8k+1 frames (unmeasured until the pilot); BiRefNet an estimate; a pod's cost is
RP-11's simulation of those stages times the price. Quality is a **hard constraint, not a cost**: `in_shot` exactness, one sheet per
hero, no img2img chain (D-78), crop at most 1.6x. Solver: deterministic, group stills by (set, camera side, cast), enumerate R0-R5
per group, take the cheapest plan that passes every constraint; ties go to fewer generated pictures. An agent reviews only REVIEW
rows and never changes a FAIL (Q2 A). Test idea: a fixture episode of 3 scenes whose cheapest plan is known by hand.

## 3. What is wanted beyond the plan (the creator's 18:54 UTC order)

- **Blender as an asset assembler**: cut assets (props, heroes, sets) from generated pictures and assemble a scene in Blender once,
  rendering several stills from it (R3 and the J5 route), including sets reusable in future episodes. The creator saw Blender do this
  well in the J5 collage and the pilot room.
- **Similar shots in future episodes**: a shot library keyed by (place, era, cast, camera) so a later episode finds R0/R1 candidates;
  `picture_library` and `assets_reuse` are the existing hooks.
- **Mouth/eye/brow variants as reusable assets**: no variant exists per hero today; one paid Qwen edit pass per hero would be reused
  in every J5 dialogue (open question, the creator's call).
