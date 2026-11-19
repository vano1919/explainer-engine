# LTX pipelines and CT-1 (W5, final plan 2026-11-19, P-6 / P-10) (D-132)

Canonical home of the rule ids CT1-01..CT1-05 and of the verified facts about the official Lightricks pipelines the worker
(`explainer_engine/training/pods/ltx/modal_ltx_jobs.py`) can call. Status: **built and tested at $0; nothing was run on Modal.** (D-132)
The paid A/B is only prepared: [LTX_AB_PLAN_2026-11-20.md](LTX_AB_PLAN_2026-11-20.md). (D-132)

## 1. What exists at the pinned commit (P-10: verified before built)

Source read: `Lightricks/LTX-2` at `e98f6d927d83c92ef2be6aec76c8440b19306e39` (the launch's `ltx_code.commit`), raw files, 2026-11-19. (D-132)
LTX-2.5 weights: README line 96 "LTX-2.5 is the recommended model"; line 131 "Every pipeline in this repository also runs on (D-132)
LTX-2.3". Nothing below was run (no GPU): "exists" means the class and its CLI `main` are in the source. (D-132)

| Pipeline | File:line | Quote | Needs (README l.101, l.120) |
|---|---|---|---|
| TI2VidTwoStagesPipeline (start+end keyframes, stage-2 x2) | `ltx_pipelines/ti2vid_two_stages.py:108-115` | "Stage 1 generates video at half of the target resolution with CFG guidance (assuming full model is used), then Stage 2 upsamples by 2x and refines using a distilled LoRA ... Supports optional image conditioning via the images parameter." | dev transformer + distilled LoRA + spatial upsampler D-132 |
| Keyframe binding | `utils/types.py:111-119`, `utils/args.py:190-193`, `docs/pipelines.md` section 6 | `ImageConditioningInput.guide(path, frame_idx, strength)`: "Guide generation with a still at a pixel-frame index"; CLI `--image PATH FRAME_IDX STRENGTH [BINDING] [CRF]`, `at` = frame 0 replaces, later frames guide; "Use TI2VidTwoStagesPipeline with explicit keyframe-guide image bindings ... add `--refine-audio`" | same D-132 |
| RetakePipeline | `ltx_pipelines/retake.py:56-62`, `__call__` at `:154-160`, CLI `:340-352` | "Regenerate a time region (retake) of an existing video ... keeps the video/audio outside that window unchanged"; `start_time`, `end_time`, `seed`; the CLI builds it with `distilled=True`; the source must have 8k+1 frames and sides divisible by 32 | the distilled checkpoint (already pinned and on the Volume) D-132 |
| A2VidPipelineTwoStage | `ltx_pipelines/a2vid_two_stage.py:113-121`, flags `:539-552` | "Two-stage audio to video generation ... Stage 1 generates video at half the target resolution with audio conditioning (video-only denoising, audio frozen), then Stage 2 upsamples by 2x"; `--audio-path`, `--audio-start-time`, `--audio-max-duration` | dev transformer + distilled LoRA + upsampler D-132 |
| ICLoraPipeline | `ltx_pipelines/ic_lora.py:287-296` | "Two-stage video generation pipeline with In-Context (IC) LoRA support ... Both stages use distilled models" | distilled checkpoint + an IC-LoRA (the 2.5 Layout-To-Render one is pinned in `config/cloud_pins.json` `models.video_ltx_layout_lora`) D-132 |
| DistilledPipeline (today's clip) | `ltx_pipelines/distilled.py:164-214`, `:484` | its Stage 2 "upsamples by 2x": `VideoUpsampler(..., spatial_upsampler_path)` and `spatially_upsample_chunks` | distilled checkpoint + upsampler D-132 |

Findings the plan thread must know (all from the source above):

1. **The pinned x2 upscaler is already used today.** The distilled CLI the worker runs (`launch.uses.spatial_upsampler`, passed as
   `--spatial-upsampler-path` in `ltx_cmd`) does stage 1 at half size and stage 2 through the x2 latent upsampler. The upsampler is a (D-132)
   *latent-space* model inside the two-stage pipelines; no pipeline exposes it as a still-image or finished-clip upscaler. So the
   brief's arm "(c) (b) + x2 upscaler" has no separate switch in the official API. The A/B plan therefore compares **engines**
   (see its arm table) and uses the repo's own still upscaler (`finish/superres.py`, rule U-2) only for the CT-1 hand-over frame.
2. **The guided pipelines need two files the worker does not have on its Volume**: the dev transformer
   (`diffusion_models/ltx-2.5-22b-dev-transformer-bf16.safetensors`) and the distilled LoRA (D-132)
   (`loras/ltx-2.5-22b-distilled-lora-450-bf16.safetensors`). Both are pinned by sha256 in `config/cloud_pins.json` (D-132)
   `models.video_ltx.sha256_files`; they are now in `launch.json` `kind_model_files` (equal to the pins, a test keeps them together). (D-132)
   Staging them to the Volume is a paid CPU step (A/B plan).
3. **Retake needs no new weights** (distilled). It regenerates inside a window of a clip already made; it cannot repair identity
   outside it.
4. **ICLoraPipeline exists but is not built as a job kind**: the brief's job kinds are keyframes, upscale_x2, retake, a2v. NOT_RUN, (D-132)
   reason: its useful inputs (layout / control video) are not part of CT-1 or CT-2.
5. Not verified: that LTX-2.5 weights give good start+end interpolation, the speed of any guided run on our H100, and whether the (D-132)
   guided stage 2 keeps the painterly look. Those are what the A/B measures.

## 2. Job kinds in the worker

`job["kind"]` (default `clip`, the distilled CLI, unchanged) selects the pipeline; every kind goes through the same launch gates
(`preflight`, `container_gate`, GO, ladder), ledger claim and settle, deadline, attempt marker, per-clip Volume copy and HF upload
checked by sha256 (OR-33).

| kind | pipeline | notes |
|---|---|---|
| `keyframes` | `engine: guided` (default) TI2VidTwoStages; `engine: distilled` the launch's DistilledPipeline | start picture `replace` at frame 0, end picture `guide` at `end_frame`; the end picture is pinned by `extra.end_sha256` D-132 |
| `upscale_x2` | TI2VidTwoStages with the start picture only | the guided two-stage whose stage 2 is the pinned x2 refine (finding 1) |
| `retake` | RetakePipeline | `source` = HF path + sha256 of the clip, `start_time` < `end_time`; fetched in the container and refused unless the sha256 matches (`stage_input`) |
| `a2v` | A2VidPipelineTwoStage | `audio` = HF path + sha256 |

Every setting is written out in the job (`settings`: steps, video CFG, STG, distilled-LoRA strengths per stage, image strengths; the
defaults are the CLI's own, `launch.json` `kind_defaults`) and copied into the run record (`row["record"]`): seed, frames, size,
conditioning frames, strengths and bindings, the file and sha256 of the upsampler, dev transformer and LoRA, the LTX commit, the (D-132)
argv sha256. A job that names its own checkpoint, LoRA or upsampler path is refused; a launch whose extra files differ from
`config/cloud_pins.json` is refused (`kind_problems`).

**Worker and launch bytes changed** (`modal_ltx_jobs.py`, `launch.json`): the OR-37 rungs L1..L3 in `ladder.json` are bound to the (D-132)
old bytes, so they must be run again (L1, L2 free CPU; L3 is paid) before any paid LTX launch. (D-132)

## 3. CT-1 in the planner (`videolane/plan.py`, `videolane/scene.py`)

A clip started from the untouched vault master is hop 0. A clip started from the last frame of the clip before is one hop further.
`plan.ct1_hops(script)` computes the hop of every video shot; `scene.build` writes `hop` and `ct1_kind` on every scene row (the
worker's `kind` is never set from it) and refuses a hop above `CT1_MAX_HOP`.

| ID | Rule | Level |
|---|---|---|
| CT1-01 | hop 3 or more is refused: a forced cut and a fresh keyframe from the vault master | FAIL D-132 |
| CT1-02 | a camera change (shot size, azimuth or vertical angle) inside a continuation needs a fresh keyframe | FAIL D-132 |
| CT1-03 | hop 1-2 continues only with a recorded comparison against the master (`master`, `face_cosine`, `lab_delta_e`, `sharpness_ratio`) and the x2 upscale and LAB lock done; a plan without the record yet is listed (REVIEW), a record that is incomplete is FAIL; `ct1_check_problems` is the hand-over-time check | REVIEW / FAIL |
| CT1-04 | a shot whose script wants an end frame and names a known end pose is made from start+end keyframes (`edit_plan.end_keyframe`, job kind `keyframes`) | REVIEW D-132 |
| CT1-05 | a new shot starts from the vault master, never from a last frame (`edit_plan.start_source`) | FAIL |

Open items (decided by the plan thread, not here, rule one OR-22): the hop limit `CT1_MAX_HOP = 2` is the creator's call of
2026-11-19 held as a module constant like the other house numbers of `plan.py`; no threshold is set on the comparison's numbers (the
record must exist and carry them; what they must meet is a rule to register in `sourced_rules.json`); "long action" is the script's
own `keyframe_plan.needs_end_frame`, not a number. (D-132)

`ab_metrics.continuation_check(frame, master, master_id, ...)` writes the CT1-03 record from real pictures and `ab_metrics.lab_lock`
is the colour lock. The picture to hand over is chosen by `finish/frame_pick` (face and pose, BP-199), upscaled by
`finish/superres` (U-2), then locked.
