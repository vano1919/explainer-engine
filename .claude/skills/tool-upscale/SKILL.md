---
name: tool-upscale
description: Upscale this channel's pictures and clips for free and check that the result really gained detail - the 2x model upscale that turns a 1376x768 Gemini picture into the working master, the U-1..U-8 decision of which shot needs one, the Lanczos finish of a video clip to the delivery frame, the BP-198 quality rows, waxy faces and the face-aware mix, flicker of per-frame models on video, and SeedVR as a parked paid candidate. Use when promoting Gemini pictures to masters, when a still_25d shot zooms past its picture, when a clip goes to the delivery size, when an upscaled face looks plastic, and before anyone proposes a GPU upscale.
---

# Upscale, the tool (layer L16, stages G5 and G7)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the free 2x step of GC-14 and
the clip finish to BP-167's delivery frame. Pictures come from skill `tool-gemini-task-pictures`; judging the result by
eye is skill `tool-vision-qa`.

## When to use, when not

- Use after intake, to promote every accepted Gemini picture to its working master; when a `still_25d` shot's zoom or
  crop needs more width than the picture has; when a finished clip goes to the delivery size; when a frame taken from a
  clip becomes a still or a punch-in.
- Not for maps, charts and overlays: Python draws them at the size they are shown (U-7).
- Not as a fix for a bad picture: an upscale never repairs a wrong face, a wrong object or a soft composition. Those go
  to the P-5 ladder (redo or re-make), not to a sharper model.

## The tools in this repo (read before citing)

| Job | Code | What it does |
|---|---|---|
| Picture 2x/4x with detail | `explainer_engine/finish/superres.py` | RealPLKSR 4x (`realplksr4x`), on any QC miss SPAN 2x (`span2x`), on a miss the picture as it is with the rows for the reviewer; both models CC-BY-4.0 by Phips, weights fetched at a pinned revision and sha256 into `$EXPLAINER_MODELS_DIR`, never committed; results cached by picture hash + model + crop + size and written as they finish |
| Which shot needs what | `superres.decide` / `plan` | the U-1..U-8 table from the script, before any picture exists |
| The promote hook | `turn_pack.find_upscaler` in `explainer_engine/imagegen/turn_pack.py` | an `EE_UPSCALER` binary (Real-ESRGAN ncnn class, `-s 2`) wins when set; else `superres` when torch, spandrel and the weights are present; else None, and promote is NOT_RUN |
| Clip to the delivery frame | `explainer_engine/finish/upscale.py` | crop the model's extra strips to true 16:9, Lanczos to the delivery size and fps, optional `cas`/`unsharp` and temporal grain, ffmpeg only |

CLI: `python -m explainer_engine.finish.superres fetch|plan|run|qc` and
`python -m explainer_engine.finish.upscale <clip.mp4> <out.mp4> [--sharpen cas|unsharp|none] [--grain N]`.

## Order of operations

1. **Intake first** (GC-12): only a picture that passed its gates is upscaled; the original stays untouched in the asset
   vault (`explainer_engine/imagegen/vault.py`), the master is a new version with the original as parent.
2. **Promote** (GC-14, U-6): `turn_pack promote <episode>` writes the 2x master at the episode's `image_min_long_side` or
   more. No upscaler installed means NOT_RUN and the picture stays a draft; never a plain resize called a master.
3. **QC each result** with `superres.qc` (BP-198 Q1-Q7, all hypotheses at REVIEW): shrunk back it stays consistent with
   the input, colour means do not move, detail beats a plain resize, it is not oversharpened against the anchor, it does
   not invent texture (LPIPS against a plain resize). A miss tries the fallback, then hands the original to the reviewer.
4. **Per route**: a video start picture is not upscaled, because the clip worker shrinks it to its own size (U-1, D-132);
   a continuation at the same framing takes the chosen frame as it is (U-2); a punch-in after a state change runs the
   model x4 then crops (U-3); a video frame that becomes a still gets the model x2 (U-4); a `still_25d` shot asks for the
   model only when delivery width x zoom / crop exceeds the picture's width (U-5).
5. **Grade after the upscale**, never before: a model can shift colour (RealPLKSR's card says it saturates; the code
   applies a wavelet colour fix).
6. **Clip finish last**: the finished video clip gets the Lanczos finish to the delivery frame (U-8) in `finish/upscale.py`;
   a crop larger than 10 % is refused (re-render instead of cutting a picture away).

## Faces: waxy skin and the face-aware mix

The overnight test of 2026-11-19 (log, 23:00 and 23:09 UTC) ran Real-ESRGAN on the CPU: wire, frost and grass came out
crisper, faces came out waxy with no new detail. A face-aware mix (the model outside YuNet face boxes, Lanczos inside)
kept the skin grain and showed no seam on a face crop; YuNet missed the small figures of a wide frame. That mix exists as
a test result on HF (`upscale_test_2026-11-19/face_aware/`); it is not in this checkout's code, so it is not a production
path until it lands with a test. Note also that the 2026-11-14 LPIPS test in `superres.py` found Real-ESRGAN x2plus no
better than a plain resize: crispness by Laplacian and faithfulness by LPIPS are different questions; ask both.

## Video: flicker

A per-frame model sharpens each frame alone, so detail shimmers on wire, water and foliage across frames. Do not run a
per-frame picture model over a clip. `superres.upscale_with_backend` has a `temporal_video` slot that returns NOT_RUN
without a registered sequence model (honest, never a single-frame fake). The temporal candidate is SeedVR2-3B
(ByteDance-Seed/SeedVR, Apache-2.0): parked on 2026-11-19 because its inference code had no pinned revision and its card
warns it over-sharpens clean inputs like ours. Any GPU upscale is paid: the OR-23 plan, the OR-34 audit, a cap in
`config/spend_caps.json`, a ledger reservation and the owner's word first (skill `modal-operations`).

## Not usable here

- CodeFormer (S-Lab License 1.0, non-commercial; noted only, the licence does not exclude a candidate, owner 2026-11-20 08:10 UTC): a full
  candidate for face restoration, to be run and judged like the others.
- GFPGAN-style face restoration: our faces are generated, and restoration tends to a plastic look; not used.
- "4K quality" words in a Gemini prompt: measured on 2026-11-19, no change in size.

## How to check an output

1. Look at 100 % crops of the same region before and after: a face, fabric, wire or frost. Side by side, same scale.
2. Read the QC rows; any REVIEW goes to the reviewer with the crop, not silently accepted.
3. For a hero close-up, compare against the approved anchor face (Q6 is information only until it has a threshold).
4. For a clip, scrub frame by frame on a fine texture for shimmer; then `superres.qc` on a few frames.
5. Record the master's sha256 in the ledger; a changed file loses its observation (`explainer_engine/episode/shot_state.py`).

## Sources (what each taught; licence noted in one line)

- artokun/comfyui-mcp, page `video-upscale` (MIT, commit `f4c4077c25`): restore and upscale before interpolation and
  encode; per-frame ESRGAN flickers on video; downscale messy input before a temporal restorer.
- ByteDance-Seed/SeedVR (Apache-2.0, commit `e4de8c2444`): the temporal candidate, configs only read.
- xinntao/Real-ESRGAN (BSD-3-Clause, commit `a4abfb2979`): the per-frame model class.
- sczhou/CodeFormer (S-Lab non-commercial, commit `b33cc7d639`): licence noted, no exclusion.
