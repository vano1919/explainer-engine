# Overlay for `v-ltxv2-video`: LTX-2.5 distilled clips on Modal (layer L13, stage G7)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from artokun/comfyui-mcp, page `ltxv2-video` (MIT, commit `090f9e8fcd`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the one way this channel makes a moving shot: the Lightricks
LTX-2 CLI with LTX-2.5 distilled weights, run by our Modal worker, driven by the video lane. The upstream text (a ComfyUI
node graph for LTX-2 and LTX-2.3) is this folder's `SKILL.md`; `references/workflows.md` holds its API-JSON
graphs and install scripts, opened only as background when comparing pipelines, never as something to run.

## When this page applies

- A shot the router (`explainer_engine/episode/router.py`, RT-02) gave the `video` route: a body performs what a still
  cannot fake, or a hero speaks his one line on camera. About 60 % of the episode by duration (D-131 as amended).
- Not for camera-only moves, weather, crowds far away, objects at rest: those are `still_25d` (skill
  `v-animate-characters` covers acting; the 2.5D renderer is code only). Not for maps (skill `cartography`).
- Not for the legacy LTX J2/J4 routes with their LoRAs and RunPod pods (D-116, retired by D-131): their code stays, a v4.3
  episode refuses them (`explainer_engine/episode/retired.py`).

## What our build is (facts from the launch file, not from upstream)

The pins live in `explainer_engine/training/pods/ltx/launch.json`; read it, do not restate it from memory. In short:
- Model repo Lightricks/LTX-2.5 at a pinned revision, every weight file by sha256 on the Modal Volume; the CLI module is
  `ltx_pipelines.distilled` at a pinned LTX-2 commit. The latent spatial upscaler is part of that pipeline already.
- One picture conditions frame 0. No end frame, no extend, no retake, no frame interpolation in this build (VIDEO_LANE,
  "What our generator can and cannot do"). Every clip is 1280x704 at 24 fps, at most 241 frames (10 s). 2K comes later
  from the free local upscale (`explainer_engine/finish/upscale.py`, `explainer_engine/finish/superres.py`), never from a
  bigger generation.
- The clip makes its own sound: speech, effects, ambience (D-132). The speaker's words arrive in the prompt.
- Runner `inproc`: one container per scene, Gemma and the transformer loaded once for every clip of the chain (RT-08,
  D-133 CH-03).

Upstream facts that still help: frame counts of the form 8n+1 (241 is one), sizes in multiples of 32, prompts that
describe a progression rather than a frozen moment. Upstream facts that do not apply: GGUF quants, the Gemma abliterated
LoRA, camera-control and style LoRAs, the two-stage ComfyUI graph, 24 GB VRAM tricks.

## The clip, as the lane designs it

1. **One line per clip, no speaking close-up** (VL-02). The model starts a line about 0.75 s in, leaves close to a second
   between sentences, and its mouths are weak up close. A hero who needs two sentences gets two shots.
2. **Length from the measured line** (VL-06, D-138): onset + the line's measured seconds (`explainer_engine/videolane/line_reads.py`)
   + BP-187's tail + handles, rounded up, at least the lane minimum; a line that will not fit in 10 s FAILs and is split.
3. **Continuity mode first** (VL-01): `continuation` starts from a chosen tail frame of the clip before (VL-05 `best_tail`,
   never before that clip's speech end); `coverage` and `insert` start from their own fresh picture drawn from the scene
   master and hero sheets (VL-04, CT-03). A continuation may hop at most twice from a fresh picture (P-6).
4. **The prompt is composed, never typed** (FA-02): `explainer_engine/videolane/scene.py` `compose_prompt` joins the
   script's `video_prompt.motion_prompt`, the start state read off the picture, the director brief, `Name says in <voice
   description>: "line"` for a clip-spoken shot, a sound clause from the shot's `sound_events`, and `Nobody speaks.` for a
   silent or narrated shot. Write the fields well (skill `v-visual-skills-video`); do not hand-edit the row.
5. **Name the series film** in the motion prompt the same way the pictures do ("in the style of the film 1917 (2019)",
   rule 20), plus one era line; no style essay.

## Procedure for one scene (free until step 7)

1. G1 passes the script: `python -m explainer_engine.episode run <episode> --to qa` stops at its first failing gate; the
   VL-01..VL-09 rows must be clean for the scene.
2. Pictures exist and passed intake (skill `v-visual-skills-image`); the line reads are measured.
3. `explainer_engine/videolane/storyboard.py` lays the start pictures out in cut order (VL-10). Claude opens the sheet and
   writes what it sees; the creator looks too. A FAIL or a stale sheet stops here.
4. `explainer_engine/videolane/scene.py` `build` writes the scene file (`ltx_scene_test/3`, called from Python; no CLI of
   its own). Without the creator's budget and ledger it is a draft that the launch refuses.
5. `python -m explainer_engine.training.pods.ltx.scene_run job <scene.json> <spec.json>`: the job spec, the run id and the
   12-character plan hash the GO must name.
6. The paid offer: `python -m explainer_engine.cloud.paid_offer check <offer.json>` (CH-07, skill `modal-operations`),
   OR-23 plan, the OR-34 audit, and the creator's word. Modal has no approved budget without its line in
   `config/spend_caps.json`.
7. `python -m explainer_engine.training.pods.ltx.scene_run reserve <scene.json>` opens the ledger line (a second reserve is
   refused), then the plain launch `EE_MODAL_GO=<msg>:<sha12> modal run ...modal_ltx_jobs.py::main --job <spec.json>`
   with the read-only watchdog beside it (OR-36). The rungs L0..L4 of the ladder must already be recorded in order.
8. Every clip lands on HF with its sha256 checked before DONE (OR-33).
9. `python -m explainer_engine.videolane.ingest <episode> <clips.json>`: raw kept and pinned, cut by measured speech,
   resampled, recorded (VL-07). Then the runner again: G6 retimes, G7 takes the cuts, G10 measures the master (VL-11, VL-12).

## Repair ladder for a clip (P-5)

Watch the whole clip at real speed with its sound, write the observation, then climb only as far as needed:

| Rung | For us | Cost |
|---|---|---|
| R1 fix | trim inside the handles, recut from raw (`ingest.recut`), reframe within the crop limit, grade toward the key frame | free |
| R2 prompt patch | one action fewer, an end state written, the instance named in a negative ("no wristwatch") | one paid clip |
| R3 new keyframe | a new start picture from the master; change the picture, not the words | one picture + one clip |
| R4 fallback | the same beat as `still_25d` with `fallback_motion_imitation`, an insert, or the reaction | free |

The worker already retries a clip it failed to make once with `seed + SEED_STEP` inside the same container and deadline.
A clip that was made but fails QA follows `explainer_engine/videolane/failure.py` `decide`: one paid retry inside the
approved plan, then the fallback. Never more than two generative tries per shot; the third idea changes the shot.

| Symptom | Usual cause | Rung |
|---|---|---|
| Line starts late, cut falls on silence | onset not trimmed | R1 (ingest cuts by measured speech) |
| Line cut off at the end | clip sized from the script, not the read | R2 after re-measuring (VL-06) |
| Soft, wrong mouth on a speaker | a speaking close-up slipped through | R3 wider framing, or R4 the listener's face |
| Helmet, sky or ground changes across a cut | continuation from a blurred last frame, or coverage drawn from the clip | R3 fresh picture from the master (VL-04, VL-05) |
| The clip freezes or fades to black mid-shot | model stall (BP-164 measured at G10) | R2 once, then R4 |
| Two actions half done | an overloaded motion prompt | R2 split into two shots |
| Face drifts from its picture | identity loss over time | R3; check with `explainer_engine/videolane/identity.py` |

## Checks in code (SK-2)

`explainer_engine/videolane/plan.py` (VL-01..VL-09), `storyboard.py` (VL-10), `scene.py` (refusals: voice missing, pin
moved, draft), `explainer_engine/training/pods/ltx/scene_run.py` (budget, plan hash, one reservation), the worker's
preflight and hand-over, `ingest.py` (VL-07), `cuts.py` (VL-11), `master_qa.py` (VL-12), `explainer_engine/cloud/hooks.py`
(raw `modal` commands refused), `explainer_engine/episode/shot_state.py` (an asset whose hash changed loses its QA).

## References: when to open which

| Need | Open |
|---|---|
| How the LTX family is named, what LTX-2.3 changed | this folder's `SKILL.md`, "Version naming" |
| Frame-count and resolution arithmetic | this folder's `SKILL.md`, "Resolution and Frame Count" |
| What a two-stage upscale graph looks like (comparison only) | `references/workflows.md` |
| Soft faces or mush when someone tries ComfyUI locally | this folder's `SKILL.md`, "Quality troubleshooting" |

## Not used from upstream

ComfyUI and its MCP converter, every install script and mirror repo, GGUF and fp8 checkpoints, the camera-control and
concept LoRAs (our LoRA routes are legacy, D-116), the Sulphur base, T2V packs (we always start from our own picture), and
any VRAM advice: the GPU and its price come from the launch file and the CH rules, not from a forum tip.
