# LTX jobs of the J2 and J4 routes

> **Route-scoped since D-116 (2026-11-06):** this page belongs to the LTX routes J2 (Blender clay layout -> LTX Layout-To-Render) and
> J4 (Blender colour, depth and line layouts -> LTX restyle). The routes live in the [decision log](DECISIONS_AND_OPEN_QUESTIONS.md)
> (D-116) and the [route plan](architecture/ROUTE_PLAN_2026-11-06.md); J5 is [SCENE_ASSETS](SCENE_ASSETS.md).

Guide step 3 (code only; every test runs in one later pod, whose OR-23 plan the Fable thread writes). `edit/ltx_jobs.py` writes one
`ltx_job/1` document ([CONTRACTS](CONTRACTS.md), `schemas/ltx_job.schema.json`) from the route shots and the layout manifests of
`blender/layout_passes.py`; the route-test pod (`training/pods/p14`) reads nothing else.

## A job

One `ltx_pipelines.ic_lora` generation at the P12 code pin (Lightricks/LTX-2@e98f6d9): a distilled checkpoint, one IC-LoRA, the
layout clip(s) as `--video-conditioning PATH STRENGTH`, the Qwen first frame as `--image PATH 0 1.0` (the layout's START pose: the
creator's C1 by route, 2026-11-06 11:12 UTC), the prompt from the route shots, a seed, the clip's frames and size. Two bases (the
creator's card 2026-11-06 11:11 UTC: J4 on both, same shots and first frames):

| base | model (`config/cloud_pins.json` models) | IC-LoRA | text encoder | J2 | J4 |
|---|---|---|---|---|---|
| `ltx25` | `video_ltx` (LTX-2.5, split files) | `video_ltx_layout_lora` (Layout-To-Render) | in the split files | clay | colour |
| `ltx23` | `video_ltx_23` (LTX-2.3 distilled 1.1 monolith) | `video_ltx_control` (Union-Control, reference 0.5x) | `text_encoder_gemma3` (gated) | — | line (inverted) or a canny of colour, + depth |

The line pass is black ink on white with the background crowd left out (fore and mid planes, plan 9.3); the Union LoRA was
trained on canny maps (white edges on black), so the pod inverts it (`derive: invert`); `canny_full` is the FFmpeg edge map of the
colour pass, background included (the guide's "canny full vs canny fore/mid"). The pod derives both before the generation and
records their hashes. J4 keeps the reference on stage 2 (`--stage-2-ic-lora`); J2 runs stage 2 on the bare checkpoint (the
pipeline's default 1080-class recipe).

## Rules

| ID | Rule | Level |
|---|---|---|
| LJ-01 | A LoRA goes only into the base it was trained on (the pin's `base`); a base that needs a text encoder names it; a weight with no sha256 is not startable (REVIEW here, the pod refuses it). | FAIL / REVIEW |
| LJ-02 | The route's recipe (J2 `ltx_layout/1`, J4 `ltx_restyle/1`) and its passes on that base, each pass once (table above). | FAIL |
| LJ-03 | CN-08 geometry on every clip: 8k+1 frames, sides in 32 (64 for the two-stage half size), BP-139. | as BP-139 |
| LJ-04 | Job ids and outputs are unique. | FAIL |
| LJ-05 | A chained clip names an earlier job of the same shot and fewer frames than that clip. | FAIL |
| LJ-07 | At most 12 generations in one test pod (the guide's section-3 matrix). | REVIEW |

## The default matrix

`ltx_jobs.MATRIX` is the writer's proposal from the guide (battle clip A on both bases and both line variants x 2 seeds, clip B chained
from A's last 8 frames on both bases, the duel on LTX-2.5 x 2 seeds: 10 generations). The OR-23 plan decides the real matrix and
passes it with `--matrix`; the audio-driven dialogue line of the guide stays with the P12 AV stage (`p12c_ltx.py`).
