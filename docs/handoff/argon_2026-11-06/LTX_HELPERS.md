# LTX_HELPERS: what LTX needs from us, what helps it, and the measured numbers

Homes (read these; this page only points): [LTX jobs](../../LTX_JOBS.md) (LJ-01..LJ-07), [P12 LTX flags](../../pods/P12_LTX_FLAGS.md)
(every CLI flag with file and line at Lightricks/LTX-2 commit e98f6d9), `explainer_engine/edit/router.py` (recipes), `explainer_engine/
edit/ltx_jobs.py`, the [route plan](../../architecture/ROUTE_PLAN_2026-11-06.md), [sourced rules](../../SOURCED_RULES.md).

## 1. What LTX takes as input, by route

| route | recipe (`edit/router.py`) | first frame | control input | base model |
|---|---|---|---|---|
| plain image to video | `ltx_i2v/1` | the **Qwen restyle of a Blender still** (`--image PATH 0 1.0`) | none | LTX-2.5 distilled (the pilot's route) |
| J2 | `ltx_layout/1` | Qwen first frame = the layout's START pose | **clay** layout clip (grey blocks, 24 fps, the clay's first frame must match the keyframe), Layout-To-Render IC-LoRA | LTX-2.5 |
| J4 | `ltx_restyle/1` | Qwen first frame | Blender **colour, depth and line** layout (line = black ink on white, fore and mid planes only; inverted for the Union LoRA, or a canny of the colour pass) | LTX-2.3 Union-Control (reference 0.5) or LTX-2.5 with colour |
| J5 | `assemble_25d/1` | none: no LTX | Blender 2.5D cards | none |
| H | `python_helper/1` | none | Python graphics | none |

A LoRA goes only into the base it was trained on (LJ-01): Layout-To-Render is LTX-2.5 only, Union-Control is LTX-2.3 only. Both are
sha-pinned in `config/cloud_pins.json`.

## 2. What helps LTX (from the plans and handoffs)

- **First frame = the Qwen restyle**, with the hero's identity coming from the approved sheet as a reference image, never from the
  prompt. The still holds only what the clip needs (`in_shot`), because LTX animates what it sees and invents the rest.
- **Layout passes for J2/J4** (clay / depth / line): "LTX only invents what the layout leaves open". The earlier IC attempt failed only
  because the layout had no motion (plan finding F-21): the clay must move the way the clip should.
- **Native audio**: LTX-2.5 can generate sound with the video. The pilot's prompt text adds one audio sentence beginning "We hear ..."
  and puts a spoken line in quotes by a name the card lists (`pilot_stills.ltx_prompt`, three style variants S1 film sentence, S2 the
  xworld caption look words, S3 no style sentence). Whether this audio is usable is **not measured**; the creator's own voice rule is that a
  character's fixed ElevenLabs voice is read first and conditions the clip (a2v, D-90); a2v has never been run.
- **Prompt shape**: the house style sentence + ONE motion line from the card (start, peak, settle) + "Static camera" unless the layout
  moves the camera. Generated from shot cards (`blender/pilot_stills.py`), never hand-written; a Qwen prompt is at most 90 words.
- **Geometry** (CN-08, BP-139, LJ-03): 8k+1 frames (121, 145, 185, 193 ...), sides in 32 (64 for the two-stage half size); seed 42 in the
  pilot; one take each. Clip length: **one LTX clip 3-6 s, limit 2-8 s** (BP-172); a scene 10-15 s (BP-108), a dialogue shot at most 5 s
  (D-95); a longer scene is cut or chained (overlap 8 frames; chaining has never been run, plan F-20).
- **Upscale** is not done on the pod: a free FFmpeg chain (crop, lanczos to 2560x1440, cas 0.4, light temporal noise) keeps ink and
  palette (`MATERIAL.md`, `upscale_chain_check`).
- **LoRA facts**: Qwen-Image-2.1 + `xworld_v2` checkpoint 3000, weight 0.7 (sha256 `f5c420a1...`), 30 steps, true_cfg 4.0 (2.5 for
  edit/reference), seed 11. `wldnk_*` models and Qwen-Image 2512 are forbidden (D-80).

## 3. What was measured (and where)

| item | value | source | status |
|---|---|---|---|
| Qwen-Image-2.1 + LoRA, one picture or edit | 33.5-38.5 s on an H100 NVL after a 61 s load | step-3 pod 1 (`handoffs/`, plans) | measured |
| Qwen on an A100 | about 1.7x slower than the H100 reference (25.8 min against 15.4 min for the 24-picture job) | PROGRESS 2026-11-06 18:20 UTC (RP-11 card speed) | an estimate from a speed table, not measured |
| **LTX seconds per clip** | about 5.8 min for 185 frames on an H100, at most 12 min | PROGRESS (pilot v4), plans v3 | **UNMEASURED**; `config/job_speeds.json` has no row |
| old film A (LTX-2.5, 1280x704, 121 frames per clip) | US$2.99 RunPod for the whole film, 52.6 s of film (the brief's length) | `film_ledger.json` in project files | measured cost, length not re-checked |
| `assemble_25d` (J5) | 7.8-8.3 s per frame with cards, 3.7 s without, at 2560x1440, EEVEE 16 samples, 4 vCPU | PROGRESS 2026-11-06 (lean pod) | measured on a cloud sandbox CPU |
| J5 dialogue: layer passes | 3.4-5.8 s each, 95 s for four 2560x1440 frames | `docs/J5_DIALOGUE_COLLAGE.md` | measured |
| J5 dialogue: animated background | 1.3 s per frame at 2560x1440 on 4 cores (300 frames about 6.5 min) | same | measured |
| J5 dialogue: cut-out (BiRefNet, CPU) | about 20 s per sheet | same | measured |
| Blender pilot stills | room 50-66 s per still; battle colour 202.3 s per frame, depth 238.1 s | `plans/PILOT_1MIN_PLAN_v3.md` | measured |
| Blender battle on the Mac | about 0.76 s per frame | plan F-35 | quoted, not re-measured |
| Local picture on the creator's RX 5700 (SDXL, old tmr engine) | 6-7 minutes a picture; the Argon brief says about 10 minutes for Z-Image | plan section 9; brief | quoted; the Qwen-2.1 20B model does not run on this card |
| GPU prices | A100 80GB community $1.39/h, secure $1.79/h; H100 NVL community $2.59/h; RTX PRO 6000 community $1.69/h (asset pod), about $2.8/h estimated | PROGRESS, `HANDOFF_assets_pod.md`, step-3 plan | card prices change; `runpod cards` is the live source |
| 12-minute episode | about $13-15 | `plans/COST_REDUCTION_NOTE.md` | estimate |

## 4. Unmeasured and open for LTX

LTX seconds and dollars per clip at 1920x1088; whether an 8 s i2v clip holds (the pilot sets `clip_max`); whether J4 keeps the Ink
Chronicle style from a canny or a clean line pass; whether chained clips join (E4 of the step-3 plan never ran); native audio and
a2v quality; upscaling to 2560x1440 of Ink Chronicle clips; clip QA (identity, flicker, jitter: none exists, gap G9). All are in
`OPEN_QUESTIONS.md`.
