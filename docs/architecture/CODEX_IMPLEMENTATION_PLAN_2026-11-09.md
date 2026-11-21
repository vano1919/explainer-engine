# CODEX IMPLEMENTATION PLAN: Explainer Engine Storytelling System Rebuild (2026-11-09)

- **Document Path:** `docs/architecture/CODEX_IMPLEMENTATION_PLAN_2026-11-09.md`  
- **Target Repository & Branch:** [`vano1919/explainer-engine` (`gemini/storytelling-system-rebuild-2026-11-09`)](https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09)  
- **Upstream Brief & Decision Digest:**  
  - [`docs/architecture/GEMINI_STORYTELLING_SYSTEM_REBUILD_2026-11-09.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/architecture/GEMINI_STORYTELLING_SYSTEM_REBUILD_2026-11-09.md)  
  - [`docs/research/AI_VIDEO_WORKFLOW_DECISION_2026-11-09.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/research/AI_VIDEO_WORKFLOW_DECISION_2026-11-09.md)  
- **Role Boundary:** This document is the definitive, self-contained architectural blueprint for **Codex**. All architectural, routing, schema, and model decisions are resolved herein. Codex must execute the implementation tasks (`TODO-01` through `TODO-16`) in dependency order without re-opening architectural debates or introducing paid cloud inference defaults.

---

## 0\. Executive Decision Record & Repository Audit (Phase 0\)

### 0.1 Locked Architectural Direction

Explainer Engine produces approximately **12-minute (720-second) English-language historical What-If docudrama episodes** organized into **16 segments (`S01–S16`)** across **5 narrative phases (`Z1–Z5`)**, targeting a **70–80% narrator voiceover / 20–30% dramatized character dialogue** audio balance and a flexible **60% cinematic video / 30% composed historical illustrations / 10% animated maps** visual allocation in a **stylized 2.5D / Ink Chronicle** aesthetic.

To eliminate the instability, latent conditioning collisions, and 3D maintenance overhead of the legacy Qwen \+ Blender \+ multi-keyframe LTX pipeline, the architecture is locked to a **4-stage, 100% local and free-by-default pipeline**:

1. **Primary Production Workflow — Hybrid B → C (2D Anchored Storyboard → Independent Per-Shot Wan 2.2 Video):**  
   - **Approach B in 2D Image Space (Scene/Shot-to-Storyboard):** Generate, edit, and human/VLM-approve 2D keyframes (Start Frame and, *only where an explicit destination state is required*, End Frame) from locked character, location, and prop reference anchors before any video generation occurs.  
   - **Approach C in Video Space (Per-Shot Image-to-Video):** Generate each short video shot (\~5 seconds default) independently via local ComfyUI using **Wan 2.2 Fun InP** (First-Last-Frame-to-Video when both start and end states matter) or **Wan 2.2 I2V** (single start frame when motion is open-ended).  
   - **Deterministic 2.5D Motion for Stills & Maps:** Composed illustrations (\~30%) and maps (\~10%) bypass video diffusion completely and are animated locally using deterministic 2.5D parallax/pan/zoom via [`akatz-ai/ComfyUI-Depthflow-Nodes`](https://github.com/akatz-ai/ComfyUI-Depthflow-Nodes) (with [`depth-anything/Depth-Anything-V2-Large`](https://huggingface.co/depth-anything/Depth-Anything-V2-Large)) or the existing local 2.5D plane renderer in [explainer\_engine/production/parallax.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/parallax.py).  
2. **Selective Secondary Workflow — Per-Shot Wan 2.2 Fun Control / Camera:**  
   - Used **only on specific shots** where standard start-frame I2V or start/end FLF2V fails to execute a required physical action or camera move.  
   - Uses the same approved Start Frame plus **at most ONE explicit control signal** (`openpose`, `depth`, `canny`, `camera_preset`, or verified `trajectory`) via [`Wan 2.2 Fun Control`](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control).  
3. **Explicitly Rejected from Default Pipeline:**  
   - **Blender 3D clay playblast \+ LTX-2.5 22B IC-LoRA Layout-to-Render:** Rejected as default because it reintroduces the heavy Blender/LTX toolchain that stalled production.  
   - **Pure End-to-End Multi-Shot Text-to-Video (`StoryMem`, `ShotDirector`, `MultiShotMaster`):** Rejected as production defaults due to unreleased weights (`ShotDirector`), two-character joint generation failure modes (`StoryMem`), and high multi-shot latent VRAM spikes (`MultiShotMaster`).  
   - **Multi-Keyframe LTX (`J5` route with 3+ keyframes \+ stacked control passes):** Retired as default due to causal `1+8k` latent clamping and boolean mask collisions in [`ComfyUI-LTXVideo`](https://github.com/Lightricks/ComfyUI-LTXVideo).  
   - **Paid Cloud Endpoints as Default:** All hosted endpoints (`https://api.ltx-cloud.internal/v1/jobs`, `https://qwen-api.internal/v2/generate`, `https://cloud-run.internal/preflight/verify`, fal.ai, Replicate, RunPod) are stripped from the default execution path.

### 0.2 End-to-End Legacy Pipeline Trace & Failure Diagnosis

An audit of [`vano1919/explainer-engine` (`gemini/storytelling-system-rebuild-2026-11-09`)](https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09) reveals how the legacy pipeline currently routes episodes and why it conflicts with the new architecture:

| Pipeline Stage | Current Repository Files | Legacy Behavior on Branch | Architectural Defect / Conflict |
| :---- | :---- | :---- | :---- |
| **1\. Episode & Story Spec** | [`docs/PROJECT_BRIEF.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/PROJECT_BRIEF.md), [docs/STORY\_ENGINE.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/STORY_ENGINE.md), [docs/SCRIPT\_ENGINE.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCRIPT_ENGINE.md), [explainer\_engine/schemas/production\_script.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/production_script.schema.json) | `PROJECT_BRIEF.md` specifies a 5–11 min range (7-min baseline). `D-120` specifies 11 min (660s) across 5–7 acts (`hook`, `setup`, `confrontation`, `climax`, `resolution`) and routes `J1–J5`. No `MAIN_METHOD.md` exists. | Contradicts the canonical **12-minute (720s)** episode format structured into **16 segments (`S01–S16`)** and **5 phases (`Z1–Z5`)**. ChatGPT rules are fragmented across 14+ markdown files. |
| **2\. Spatial & Scene Layout** | [docs/SCENE\_ASSETS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCENE_ASSETS.md), [`explainer_engine/blender/`](https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/blender) (31 `.py` modules), [explainer\_engine/schemas/blender\_scene\_manifest.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/blender_scene_manifest.schema.json) | Mandates building `.blend` files with Blender 4.2 LTS grease-pencil layers and `xworld_v2` 3D camera rigs (`D-96`, `D-121`) before keyframe rendering. | Creates a manual 3D bottleneck per shot and couples 2D illustration styling to headless Blender scene geometry. |
| **3\. Keyframe Routing & Generation** | [explainer\_engine/imagegen/routing.py](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/imagegen/routing.py), [explainer\_engine/imagegen/plan.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/imagegen/plan.py), [docs/SHOT\_PROMPTS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SHOT_PROMPTS.md) | `ShotRouter` assigns routes `J1–J5`, defaults to `Qwen-Image-2.1` (`D-80`), bans `Qwen-Image-Edit-2511` (`keyframe_gate.RETIRED`), and references internal cloud URL `https://qwen-api.internal/v2/generate`. | Blocks `Qwen-Image-Edit-2511` evaluation, assigns 1–3 keyframes per shot for LTX (`J5`), and points to a non-local endpoint. |
| **4\. Video Job Dispatch** | [explainer\_engine/aivideo/shotplan.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/aivideo/shotplan.py), [explainer\_engine/schemas/ltx\_job.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/ltx_job.schema.json), [docs/pods/P12\_LTX\_FLAGS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/pods/P12_LTX_FLAGS.md) | `build_ltx_payload()` constructs multi-keyframe (`start_keyframe`, `middle_keyframe`, `end_keyframe`) LTX jobs (`D-116`, `D-122`) and references `https://api.ltx-cloud.internal/v1/jobs`. | No native Wan 2.2 I2V / Fun-InP / Fun-Control payload builder or schema exists in `explainer_engine/aivideo/`. |
| **5\. Preflight, Audio & Assembly** | [explainer\_engine/production/paid\_preflight.py](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/paid_preflight.py), [explainer\_engine/production/assemble.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/assemble.py), [explainer\_engine/production\_gate.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production_gate.py) | `paid_preflight.py` checks `SPEND_LIMIT_USD` and calls `https://cloud-run.internal/preflight/verify` while validating LTX keyframe triplets. | Preflight assumes paid cloud execution and LTX job schemas rather than local ComfyUI readiness and local model file verification. |

### 0.3 Resolution of Contradictory Repository Decisions (`D-80` through `D-122`)

Codex must append **Decision `D-123` (2026-11-09)** to [`docs/DECISIONS_AND_OPEN_QUESTIONS.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/DECISIONS_AND_OPEN_QUESTIONS.md), explicitly superseding or scoping prior decisions as follows:

| Decision ID | Current Status on Branch | Conflict with Rebuild | Resolution in `D-123` (Action for Codex) |
| :---- | :---- | :---- | :---- |
| **`D-80`** *(2026-10-26)* | Locks `Qwen-Image-2.1` (`qwen_image_2`) with a single style/sequence LoRA; bans all pre-2026-10-26 LoRAs; marks `Qwen-Image-Edit-2511` as `keyframe_gate.RETIRED`. | Prevents evaluating [`Qwen/Qwen-Image-Edit-2511`](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) \+ [`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`](https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA). | **Partially Superseded:** Keep the ban on pre-2026-10-26 legacy LoRAs, but un-retire `Qwen-Image-Edit-2511` so it can be benchmarked head-to-head against `Qwen-Image-2.1` \+ `xworld_v2` in Phase 1\. |
| **`D-95`** *(2026-11-04)* | Locks 70–80% narrator voiceover and 20–30% character dialogue (75/25 midpoint) and intent-based shot duration. | None — aligns with the 12-minute format specification. | **Retained Active:** Enforce in `production_script.schema.json` (`narrator_dialogue_ratio`: `0.70–0.80`, `character_dialogue_ratio`: `0.20–0.30`). |
| **`D-96`** *(2026-11-06)* | Defines "Ink Chronicle" as a 3D-to-illustrated universe rendered in Blender with Qwen keyframes \+ LTX clips. | Couples the Ink Chronicle visual style to mandatory Blender 3D scene construction and LTX video generation. | **Scoped:** Retain the **Ink Chronicle 2.5D visual style bible**, but decouple it from mandatory Blender 3D layout and LTX video diffusion. |
| **`D-116`** *(2026-11-08)* | Makes `LTX-Video 0.9.5` with multi-keyframe `ltx_job.schema.json` and route `J5` (up to 3 keyframes) the universal video engine. | Directly contradicts the Wan 2.2 Hybrid B → C decision. | **Superseded as Default:** Replace with `wan_job.schema.json` (Wan 2.2 Fun InP / I2V primary; Wan 2.2 Fun Control selective fallback). Demote `ltx_job.schema.json` to an explicit legacy/fallback route (`WAN_FALLBACK_LTX`). |
| **`D-120`** *(2026-11-09)* | Sets episode runtime to 11 minutes (660s) across 5–7 acts (`110–140` shots). | Conflicts with both `PROJECT_BRIEF.md` (5–11 min / 7-min target) and the canonical 12-minute `Z1–Z5` / `S01–S16` structure. | **Superseded:** Standardize canonical episode target at **12 minutes (`720` seconds, acceptable window `660–780s`)** organized into **5 phases (`Z1–Z5`)** and **16 segments (`S01–S16`)**. |
| **`D-121`** *(2026-11-09)* | Mandates Blender 4.2 LTS grease-pencil `.blend` files and `xworld_v2` 3D camera rigs for all scene assets. | Violates the Hybrid B → C directive to eliminate 3D layout per shot as the default. | **Superseded as Default:** Retire Blender 3D grease-pencil scene building from the default path. Keep `explainer_engine/blender/assemble_25d.py` only as an optional local deterministic 2.5D plane renderer alongside DepthFlow. |
| **`D-122`** *(2026-11-09)* | Routes 1–3 keyframes per shot into LTX jobs gated by `paid_preflight.py` cloud spend checks. | Violates both the single-start-frame / start-end bridge B → C model and the local-only free default constraint. | **Superseded:** Replace with `local_preflight.py` (verifying local ComfyUI reachability, local checkpoint hashes, and 1-or-2 keyframe conformance without paid cloud calls). |

### 0.4 Explicit KEEP / CHANGE / REMOVE Matrix

| Disposition | Subsystem / Asset | Specific Repository Paths & Rationale |
| :---- | :---- | :---- |
| **KEEP** | **Ink Chronicle Visual Direction & Trained Style Assets** | Keep [docs/CREATIVE\_STYLE\_BIBLE.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/CREATIVE_STYLE_BIBLE.md), [`config/vault.json`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/vault.json) critical pointers (`lora_plan_2026-10-26/train_xworld_v2/output/**`, `night_run_2026-10-22/train/wldnk_wan22_v1/**`), and [explainer\_engine/assets\_reuse.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/assets_reuse.py). Note: [`config/vault.json`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/vault.json) already tracks trained Wan 2.2 high/low noise LoRAs (`wldnk_wan22_v1_high_noise.safetensors`, `wldnk_wan22_v1_low_noise.safetensors`), which Codex should test in Phase 1\! |
| **KEEP** | **Scripting Lints, Audio Spine, Deterministic 2.5D & NLE Assembly** | Keep [explainer\_engine/audio/](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/audio), [explainer\_engine/scripting/claims.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/claims.py), [narration\_lint.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/narration_lint.py), [register\_lint.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/register_lint.py), [rhythm\_lint.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/rhythm_lint.py), [speech.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/speech.py), [syllables.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/scripting/syllables.py), [explainer\_engine/production/timing.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/timing.py), [parallax.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/parallax.py), [depth.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/depth.py), [cutout\_prep.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/cutout_prep.py), [assemble.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/assemble.py), and [explainer\_engine/edit/](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/edit). |
| **CHANGE** | **Episode Structure, Storyboard Stage & Video Engine** | Update [explainer\_engine/schemas/production\_script.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/production_script.schema.json) to the 12-minute `Z1–Z5` / `S01–S16` single-source-of-truth contract. Replace `J1–J5` routing in [explainer\_engine/imagegen/routing.py](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/imagegen/routing.py) and [explainer\_engine/aivideo/shotplan.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/aivideo/shotplan.py) with the 4-stage Hybrid B → C modes (`WAN_I2V`, `WAN_FLF2V`, `WAN_CONTROL`, `STILL_25D`, `MAP_25D`). |
| **CHANGE** | **Local ComfyUI Runtime & `.env` Configuration** | Extend [`explainer_engine/vault.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/vault.py) and [`config/model_routing.json`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/model_routing.json) with a unified local model/workflow registry (`config/local_models.json`) and local preflight check (`explainer_engine/production/local_preflight.py`) enforcing `EXPLAINER_LOCAL_ONLY=1` by default. |
| **REMOVE (from Default)** | **Mandatory Blender 3D Scene Building, Multi-Keyframe LTX (`J5`), & Paid Cloud Preflight** | Deprecate and remove from default execution: 3D layout builders in [`explainer_engine/blender/`](https://github.com/vano1919/explainer-engine/tree/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/blender) (retaining only `assemble_25d.py` as an optional 2.5D plane renderer), [docs/pods/P12\_LTX\_FLAGS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/pods/P12_LTX_FLAGS.md), middle-keyframe LTX chaining in [explainer\_engine/schemas/ltx\_job.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/ltx_job.schema.json), and default cloud spend calls in [explainer\_engine/production/paid\_preflight.py](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/paid_preflight.py). |

---

## 1\. Local Model, Adapter & ComfyUI Validation Spec (Phase 1\)

### 1.1 Exact Local Model & Checkpoint Registry

All model weights live outside Git under `$COMFYUI_MODELS_DIR` (resolved from `.env` via `explainer_engine/vault.py`). Codex must register the following exact model identifiers, revisions, and licence rules in `config/local_models.json`:

| Stage & Role | Model / Adapter Name | Official Source URL | Expected Local Relative Path (`$COMFYUI_MODELS_DIR/`) | Parameter Class & Precision | Licence & Commercial Note | Baseline vs. Optional Status |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **Stage 2: Existing Image Baseline (Control Candidate A)** | `Qwen-Image-2.1` (`qwen_image_2`) \+ `xworld_v2` LoRA | [`config/vault.json` (`train_xworld_v2`)](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/vault.json) | `diffusion_models/qwen_image_2_1_bf16.safetensors` \+ `loras/xworld_v2.safetensors` | 20B class (BF16 / FP8 / Q8 GGUF) | Apache-2.0 (Base) / Proprietary Internal (`xworld_v2`) | **Benchmark Candidate A** (Existing local path; verified compatible with `xworld_v2`). |
| **Stage 2: Edit & Multi-Angle Candidate (Candidate B)** | `Qwen-Image-Edit-2511` | [`Qwen/Qwen-Image-Edit-2511`](https://huggingface.co/Qwen/Qwen-Image-Edit-2511) | `diffusion_models/qwen_image_edit_2511_fp8_e4m3fn.safetensors` (or GGUF Q8\_0) | 20B class (FP8 / GGUF Q8) | Apache-2.0 | **Benchmark Candidate B** (Keep as primary *only* if pilot proves superior framing/character consistency over `Qwen-Image-2.1`). |
| **Stage 2: Multi-Angle Camera LoRA** | `Qwen-Image-Edit-2511-Multiple-Angles-LoRA` | [`fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA`](https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA) | `loras/qwen-image-edit-2511-multiple-angles-lora.safetensors` | LoRA (\~295 MB, rank 64\) | Check fal.ai repository licence card before commercial redistribution; free local inference | **Primary Camera Adapter** for Candidate B (96 learned `<sks>` prompt viewpoints). |
| **Stage 2: Next-Scene Progression LoRA** | `next-scene-qwen-image-lora-2509` | [`lovis93/next-scene-qwen-image-lora-2509`](https://huggingface.co/lovis93/next-scene-qwen-image-lora-2509) | `loras/next-scene-qwen-image-lora-2509.safetensors` | LoRA | Community / HuggingFace card terms (verify before commercial use) | **Strictly Optional / Gated:** Base is `2509`, not `2511`. Do NOT enable by default or stack with Multi-Angle LoRA unless ablation test `T-ABL-02` passes. |
| **Stage 3: Primary Video Engine (5B Local Tier — Test First)** | `Wan2.2-Fun-5B-InP` | [`alibaba-pai/Wan2.2-Fun-5B-InP`](https://huggingface.co/alibaba-pai/Wan2.2-Fun-5B-InP) | `diffusion_models/Wan2.2-Fun-5B-InP.safetensors` | 5B dense (BF16 / FP8) | Apache-2.0 | **Primary Video Default Candidate** (Test first for both single-frame I2V and start/end FLF2V). |
| **Stage 3: Primary Video Comparison Tier (14B MoE)** | `Wan2.2-Fun-A14B-InP` / `Wan2.2-I2V-A14B` | [`ComfyUI Wan 2.2 Fun InP Guide`](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-inp) / [`Wan-AI/Wan2.2-I2V-A14B`](https://huggingface.co/Wan-AI/Wan2.2-I2V-A14B) | `diffusion_models/wan2.2_fun_inp_high_noise_14B_fp8_scaled.safetensors` & `low_noise_14B_fp8_scaled.safetensors` | 27B total / 14B active MoE (FP8 / GGUF) | Apache-2.0 | **Escalation Comparison Tier** (Adopt only if 5B fails pilot quality/control bar). |
| **Stage 3: Step-Distillation LoRA (Benchmark Option)** | `Wan2.2-Distill-Loras` (`LightX2V` 4-step) | [`lightx2v/Wan2.2-Distill-Loras`](https://huggingface.co/lightx2v/Wan2.2-Distill-Loras) | `loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors` & `low_noise.safetensors` | Dual High/Low Noise LoRA | Apache-2.0 | **Benchmark Option:** Compare 4-step LightX2V vs. unaccelerated 20-step inference (`T-ABL-03`) to measure motion dynamic loss. |
| **Stage 3: Internal Style Video LoRA (Vault Asset)** | `wldnk_wan22_v1` (High/Low Noise) | [`config/vault.json` (`wldnk_wan22_v1`)](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/vault.json) | `loras/wldnk_wan22_v1_high_noise.safetensors` & `wldnk_wan22_v1_low_noise.safetensors` | Dual High/Low Noise LoRA | Internal Asset | **Optional Style Adapter:** Test compatibility with Wan 2.2 Fun InP in `T-ABL-04`. |
| **Stage 3: Secondary Selective Control Video (5B Tier — Test First)** | `Wan2.2-Fun-5B-Control` | [`ComfyUI Wan 2.2 Fun Control Guide`](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control) | `diffusion_models/Wan2.2-Fun-5B-Control.safetensors` | 5B dense (BF16 / FP8) | Apache-2.0 | **Secondary Selective Fallback (Default Control Tier)** for single-modality OpenPose/Depth/Canny/Camera control. |
| **Stage 3: Secondary Selective Control Video (14B Tier)** | `Wan2.2-Fun-A14B-Control` | [`ComfyUI Wan 2.2 Fun Control Guide`](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control) | `diffusion_models/wan2.2_fun_control_high_noise_14B_fp8_scaled.safetensors` & `low_noise` | 14B active MoE (FP8) | Apache-2.0 | **Control Escalation Tier** (Use only if 5B Control fails pilot action test). |
| **Stage 3: Experimental Trajectory Control** | `ByteDance ATI` (Wan 2.1 14B I2V base) | [`bytedance/ATI`](https://github.com/bytedance/ATI) | `diffusion_models/wan2.1_ati_14b_i2v.safetensors` | 14B Wan 2.1 I2V base | Apache-2.0 | **Strictly Experimental / Opt-In Only:** Built on Wan 2.1 14B, NOT Wan 2.2 5B. Excluded from baseline until wrapper/checkpoint verified. |
| **Stage 3: Deterministic 2.5D Parallax (Stills & Maps)** | `Depth-Anything-V2-Large` \+ `ComfyUI-Depthflow-Nodes` | [`depth-anything/Depth-Anything-V2-Large`](https://huggingface.co/depth-anything/Depth-Anything-V2-Large) / [`akatz-ai/ComfyUI-Depthflow-Nodes`](https://github.com/akatz-ai/ComfyUI-Depthflow-Nodes) | `depthanything/depth_anything_v2_vitl_fp16.safetensors` | \~335M ViT-L (FP16) | Apache-2.0 (`vitb`/`vits`) / CC-BY-NC-4.0 (`vitl` — use `vitb` Apache-2.0 for commercial episodes\!) | **Primary 2.5D Motion Engine** for the 30% illustration and 10% map allocation (or fallback to `explainer_engine/production/parallax.py`). |
| **Stage 3: Selective Close-Up Lip-Sync (Optional)** | `Wan2.1-InfiniteTalk` | [`MeiGen-AI/InfiniteTalk`](https://github.com/MeiGen-AI/InfiniteTalk) | `diffusion_models/wan2.1_infiniteTalk_single_fp16.safetensors` | Diffusion-Forcing Adapter | Apache-2.0 | **Strictly Optional:** Use OTS/reaction cuts by default; invoke InfiniteTalk only when close-up visible lip-sync is narratively mandatory. |

> **Critical Licence Audit Rule for Codex:** While `Depth-Anything-V2-Small` and `Base` are Apache-2.0, `Depth-Anything-V2-Large` carries a CC-BY-NC-4.0 weight licence due to DINOv2-Large roots, and `fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA` and `lovis93/next-scene-qwen-image-lora-2509` carry custom HuggingFace card terms. Codex must implement a `licence_status` field (`"commercial_ok"`, `"non_commercial_research"`, `"verify_card"`) in `config/local_models.json` and enforce a preflight warning in `explainer_engine/rights/` if a non-commercial weight is selected for a monetized publish run.

### 1.2 Required Local ComfyUI Custom Nodes & Native Nodes

Codex must verify via `explainer_engine/production/local_preflight.py` (querying `GET http://127.0.0.1:8188/object_info`) that the local ComfyUI installation exposes:

1. **Native ComfyUI Core Nodes (Official):**  
   - `WanFunInpaintToVideo` (official node for [Wan 2.2 Fun InP](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-inp) supporting `start_image` and optional `end_image`).  
   - `WanImageToVideo` (official single-frame I2V conditioning node).  
   - `Wan22FunControlToVideo` & `WanCameraEmbedding` (official nodes for [Wan 2.2 Fun Control](https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control)).  
   - `TextEncodeQwenImageEditPlus` (official multi-image reference encoder for `Qwen-Image-Edit-2511`).  
2. **Community Custom Nodes (Tracked in `config/local_models.json` with pinned Git commit SHAs):**  
   - [`jtydhr88/ComfyUI-qwenmultiangle`](https://github.com/jtydhr88/ComfyUI-qwenmultiangle): Provides `QwenMultiangleCameraNode` emitting `<sks>` camera prompt strings.  
   - [`akatz-ai/ComfyUI-Depthflow-Nodes`](https://github.com/akatz-ai/ComfyUI-Depthflow-Nodes): Provides deterministic 2.5D parallax presets (`DepthflowPresetDolly`, `DepthflowPresetOrbital`, `DepthflowPresetZoom`, `DepthflowPresetHorizontal`, `DepthflowPresetVertical`). *Fallback if unavailable locally:* [explainer\_engine/production/parallax.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/parallax.py) \+ [explainer\_engine/blender/assemble\_25d.py](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/blender/assemble_25d.py).  
   - [`Fannovel16/comfyui_controlnet_aux`](https://github.com/Fannovel16/comfyui_controlnet_aux): Provides `DWPreprocessor`, `CannyEdgePreprocessor`, and `DepthAnythingV2Preprocessor` for the selective secondary Wan 2.2 Fun Control route.

### 1.3 Mandatory Phase 1 Compatibility & Ablation Protocol

Before locking the production defaults in `config/local_models.json`, Codex must implement an automated local compatibility harness (`scripts/run_phase1_ablations.py`) executing four controlled tests on a single 2-shot micro-fixture:

- **`T-ABL-01` (`xworld_v2` vs. `Qwen-Image-Edit-2511` Compatibility):** Test whether `xworld_v2.safetensors` (trained on `Qwen-Image-2.1` per `D-80`) loads cleanly and preserves the Ink Chronicle aesthetic on `Qwen-Image-Edit-2511` without tensor shape mismatch or style frying.  
  - *Decision Rule:* If `xworld_v2` fails or degrades on `2511`, use `Qwen-Image-2.1` \+ `xworld_v2` for master asset generation and pass the resulting Ink Chronicle master anchor image as `image1` into `Qwen-Image-Edit-2511` \+ `Multiple-Angles-LoRA` (which inherits the Ink Chronicle style from the input reference image without loading `xworld_v2` onto `2511`).  
- **`T-ABL-02` (`Next-Scene-2509` Compatibility & Non-Stacking Rule):** Test `next-scene-qwen-image-lora-2509.safetensors` alone on `2511` vs. omitted. Never stack `Next-Scene-2509` and `Multiple-Angles-LoRA` in the same generation pass unless `T-ABL-02` proves zero identity/style degradation.  
- **`T-ABL-03` (`Wan2.2-Fun-5B-InP` vs. `14B-InP` & 4-Step `LightX2V` vs. Unaccelerated 20-Step):** Measure local runtime, peak memory, motion amplitude, and Ink Chronicle line integrity across (a) `5B-InP` unaccelerated, (b) `5B-InP` accelerated, (c) `14B-InP` 4-step `LightX2V`, and (d) `14B-InP` unaccelerated.  
  - *Decision Rule:* Select the smallest configuration (`5B-InP` preferred) that scores $\geq 4.0/5.0$ on the pilot rubric.  
- **`T-ABL-04` (`wldnk_wan22_v1` Vault LoRA Verification):** Test whether the repository's existing vault LoRAs (`wldnk_wan22_v1_high_noise.safetensors` and `wldnk_wan22_v1_low_noise.safetensors` listed in [`config/vault.json`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/config/vault.json)) improve Ink Chronicle line stability on Wan 2.2 without damping motion.

---

## 2\. Target 4-Stage Architecture & Canonical Data Contracts (Phase 2\)

### 2.1 Four-Stage Pipeline Overview & Folder Layout

The pipeline is strictly bounded to **4 major production stages**. A single canonical JSON file (`episodes/<episode_id>/production_script.json`) serves as the **Single Source of Truth (SSOT)** for the episode story, narration/dialogue lines, asset bible, and shot list. Parallel duplicate shotlists are forbidden.

```
jobs/<episode_id>/
├── 01_script/
│   ├── research_dossier.md             # Human-readable historical research & citations
│   └── production_script.json          # CANONICAL SSOT (Story + Audio Spine + Bible + 16-Segment Shot Plan)
├── 02_keyframes/
│   ├── assets/
│   │   ├── char_<id>_turnaround.png    # Approved 4-panel character reference sheets
│   │   ├── loc_<id>_anchor.png         # Approved master location anchors
│   │   └── prop_<id>_anchor.png        # Approved prop anchors
│   ├── shots/
│   │   ├── S01_SH001_start.png         # Approved Start Frame (all shots)
│   │   ├── S01_SH001_end.png           # Approved End Frame (ONLY for WAN_FLF2V shots)
│   │   └── S01_SH003_depth.png         # Extracted depth/pose/canny map (ONLY for STILL_25D/MAP_25D/WAN_CONTROL)
│   └── keyframe_manifest.json          # Approval hashes, seed logs, and repair history
├── 03_video/
│   ├── clips/
│   │   ├── S01_SH001_raw.mp4           # Rendered 5s clip (Wan 2.2 or DepthFlow 2.5D)
│   │   └── ...
│   ├── wan_jobs_manifest.json          # Dispatched ComfyUI payloads & seeds
│   └── render_telemetry.jsonl          # Measured wall-clock time, retries, VRAM peak, accept/reject status
└── 04_assembly/
    ├── audio/
    │   ├── narration_spine.wav         # Master narrator TTS + character dialogue stems
    │   └── audio_spine_manifest.json   # Word/line timestamps driving shot durations
    ├── timeline/
    │   └── episode_master_24fps.mp4    # Final assembled 24fps MP4
    └── qa_report.json                  # Final automated gate + creator review checklist
```

### 2.2 Stage State Machine & Retry Rules

Every shot (`shot_id`, formatted `S<01-16>_SH<001-999>`) transitions deterministically through:

1. `PLANNED`: Defined in `production_script.json` and passes `narration_lint`, `shot_prompt_lint`, and schema validation.  
2. `KEYFRAME_GENERATED` → `KEYFRAME_APPROVED`: Start frame (and optional end frame) rendered via local ComfyUI Qwen workflow and verified for character/location/prop fidelity. **Rule:** Never dispatch Stage 3 video generation on an unapproved keyframe. If hands, props, or faces are defective, repair in 2D (`Qwen-Image-Edit` inpaint/edit or seed retry, max 3 automatic retries before human review flag).  
3. `MOTION_RENDERED` → `MOTION_APPROVED`:  
   - For `STILL_25D` and `MAP_25D`: Deterministic DepthFlow / 2.5D plane render completes in 1 pass (0 diffusion retries).  
   - For `WAN_I2V` and `WAN_FLF2V`: Local ComfyUI Wan 2.2 render. If automated QA (`explainer_engine/production_gate.py`) detects temporal flicker, frozen frames, or boundary snapping, retry up to `max_auto_retries = 2` with deterministic seed increment (`seed + 1001`).  
   - **Escalation Rule to Secondary Workflow (`WAN_CONTROL`):** If a `WAN_I2V` or `WAN_FLF2V` shot fails after 2 retries specifically due to action choreography or camera path error, escalate that individual shot's `generation_mode` to `WAN_CONTROL` with **exactly one** `control_modality` (`openpose`, `depth`, `canny`, or `camera_preset`).  
4. `ASSEMBLED` → `QA_PASSED`: Trimmed to exact `audio_spine` duration at 24fps, mixed with narration/dialogue/SFX stems, and validated by `production_gate.py`.

### 2.3 Canonical Schema 1: `explainer_engine/schemas/production_script.schema.json` (v4.0)

Codex must update [explainer\_engine/schemas/production\_script.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/production_script.schema.json) (and deprecate separate duplicate shot schemas by making `film_shots.schema.json` a `$ref` alias to `#/$defs/ShotSpec`) with the following exact JSON Schema:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://explainer-engine.local/schemas/production_script.schema.json",
  "title": "ExplainerEngineProductionScriptV4",
  "type": "object",
  "required": [
    "schema_version",
    "episode_id",
    "title",
    "what_if_premise",
    "target_duration_seconds",
    "fps",
    "audio_balance_target",
    "visual_mix_target",
    "historical_dossier_ref",
    "world_bible",
    "phases",
    "segments",
    "audio_lines",
    "shots"
  ],
  "additionalProperties": false,
  "properties": {
    "schema_version": { "const": "4.0.0" },
    "episode_id": { "type": "string", "pattern": "^ep_[a-z0-9_]+$" },
    "title": { "type": "string", "minLength": 5 },
    "what_if_premise": { "type": "string", "minLength": 15 },
    "target_duration_seconds": { "type": "number", "minimum": 60, "maximum": 900, "default": 720 },
    "fps": { "type": "integer", "const": 24 },
    "audio_balance_target": {
      "type": "object",
      "required": ["narrator_ratio_min", "narrator_ratio_max", "dialogue_ratio_min", "dialogue_ratio_max"],
      "properties": {
        "narrator_ratio_min": { "type": "number", "const": 0.70 },
        "narrator_ratio_max": { "type": "number", "const": 0.80 },
        "dialogue_ratio_min": { "type": "number", "const": 0.20 },
        "dialogue_ratio_max": { "type": "number", "const": 0.30 }
      }
    },
    "visual_mix_target": {
      "type": "object",
      "description": "Flexible target guideline (~60% video, ~30% illustration, ~10% map); not a rigid quota.",
      "required": ["cinematic_video_target", "composed_illustration_target", "map_visualization_target"],
      "properties": {
        "cinematic_video_target": { "type": "number", "default": 0.60 },
        "composed_illustration_target": { "type": "number", "default": 0.30 },
        "map_visualization_target": { "type": "number", "default": 0.10 }
      }
    },
    "historical_dossier_ref": { "type": "string" },
    "world_bible": {
      "type": "object",
      "required": ["style_anchor_token", "characters", "locations", "props"],
      "properties": {
        "style_anchor_token": { "type": "string", "default": "2.5D Ink Chronicle historical docudrama illustration" },
        "characters": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["character_id", "name", "historical_role", "fixed_appearance_prompt", "costume_continuity_notes", "reference_sheet_path"],
            "properties": {
              "character_id": { "type": "string", "pattern": "^char_[a-z0-9_]+$" },
              "name": { "type": "string" },
              "historical_role": { "type": "string" },
              "fixed_appearance_prompt": { "type": "string", "minLength": 20 },
              "costume_continuity_notes": { "type": "string" },
              "voice_profile_id": { "type": "string" },
              "reference_sheet_path": { "type": "string" }
            }
          }
        },
        "locations": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["location_id", "name", "era_and_geography", "fixed_environment_prompt", "lighting_palette", "anchor_image_path"],
            "properties": {
              "location_id": { "type": "string", "pattern": "^loc_[a-z0-9_]+$" },
              "name": { "type": "string" },
              "era_and_geography": { "type": "string" },
              "fixed_environment_prompt": { "type": "string", "minLength": 20 },
              "lighting_palette": { "type": "string" },
              "anchor_image_path": { "type": "string" }
            }
          }
        },
        "props": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["prop_id", "name", "fixed_prop_prompt", "anchor_image_path"],
            "properties": {
              "prop_id": { "type": "string", "pattern": "^prop_[a-z0-9_]+$" },
              "name": { "type": "string" },
              "fixed_prop_prompt": { "type": "string" },
              "anchor_image_path": { "type": "string" }
            }
          }
        }
      }
    },
    "phases": {
      "type": "array",
      "minItems": 1,
      "maxItems": 5,
      "items": {
        "type": "object",
        "required": ["phase_id", "title", "target_window", "segment_ids", "narrative_objective"],
        "properties": {
          "phase_id": { "enum": ["Z1", "Z2", "Z3", "Z4", "Z5"] },
          "title": { "type": "string" },
          "target_window": { "type": "string" },
          "segment_ids": { "type": "array", "items": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])$" } },
          "narrative_objective": { "type": "string" }
        }
      }
    },
    "segments": {
      "type": "array",
      "minItems": 1,
      "maxItems": 16,
      "items": {
        "type": "object",
        "required": ["segment_id", "phase_id", "title", "narrative_purpose", "target_duration_seconds", "factual_status", "cause_from_segment_id", "effect_to_segment_id"],
        "properties": {
          "segment_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])$" },
          "phase_id": { "enum": ["Z1", "Z2", "Z3", "Z4", "Z5"] },
          "title": { "type": "string" },
          "narrative_purpose": { "type": "string" },
          "target_duration_seconds": { "type": "number", "minimum": 10 },
          "factual_status": { "enum": ["actual_history", "divergence_point", "counterfactual_consequence", "historical_reflection"] },
          "cause_from_segment_id": { "type": ["string", "null"] },
          "effect_to_segment_id": { "type": ["string", "null"] }
        }
      }
    },
    "audio_lines": {
      "type": "array",
      "minItems": 1,
      "items": {
        "type": "object",
        "required": ["line_id", "segment_id", "speaker_type", "speaker_id", "text", "register_type", "estimated_duration_seconds"],
        "properties": {
          "line_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])_L[0-9]{3}$" },
          "segment_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])$" },
          "speaker_type": { "enum": ["narrator", "character", "silent_beat"] },
          "speaker_id": { "type": "string" },
          "addressee_id": { "type": ["string", "null"] },
          "delivery_direction": { "type": "string" },
          "text": { "type": "string" },
          "register_type": { "enum": ["verified_historical_fact", "plausible_counterfactual_inference", "dramatized_in_scene_speech"] },
          "citation_ids": { "type": "array", "items": { "type": "string" } },
          "estimated_duration_seconds": { "type": "number", "minimum": 0.5 },
          "requires_visible_lipsync": { "type": "boolean", "default": false }
        }
      }
    },
    "shots": {
      "type": "array",
      "minItems": 1,
      "items": { "$ref": "#/$defs/ShotSpec" }
    }
  },
  "$defs": {
    "ShotSpec": {
      "type": "object",
      "required": [
        "shot_id",
        "segment_id",
        "target_duration_seconds",
        "narrative_purpose",
        "visual_type",
        "generation_mode",
        "location_id",
        "character_ids",
        "prop_ids",
        "audio_line_ids",
        "action_start_state",
        "action_end_state",
        "camera_spec",
        "screen_composition",
        "lighting_and_time",
        "continuity_refs",
        "keyframe_plan",
        "image_prompt",
        "video_prompt",
        "transition_out"
      ],
      "additionalProperties": false,
      "properties": {
        "shot_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])_SH[0-9]{3}$" },
        "segment_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])$" },
        "target_duration_seconds": { "type": "number", "minimum": 2.0, "maximum": 12.0, "default": 5.0 },
        "narrative_purpose": { "type": "string", "minLength": 10 },
        "visual_type": { "enum": ["cinematic_video", "composed_illustration", "map_visualization"] },
        "generation_mode": {
          "enum": [
            "WAN_I2V",
            "WAN_FLF2V",
            "WAN_CONTROL",
            "STILL_25D",
            "MAP_25D",
            "WAN_FALLBACK_LTX"
          ]
        },
        "location_id": { "type": "string", "pattern": "^loc_[a-z0-9_]+$" },
        "character_ids": { "type": "array", "items": { "type": "string", "pattern": "^char_[a-z0-9_]+$" } },
        "prop_ids": { "type": "array", "items": { "type": "string", "pattern": "^prop_[a-z0-9_]+$" } },
        "audio_line_ids": { "type": "array", "items": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])_L[0-9]{3}$" } },
        "action_start_state": { "type": "string" },
        "action_end_state": { "type": "string" },
        "camera_spec": {
          "type": "object",
          "required": ["shot_size", "vertical_angle", "horizontal_azimuth_deg", "camera_move"],
          "properties": {
            "shot_size": { "enum": ["extreme_wide", "wide", "medium_wide", "medium", "medium_close_up", "close_up", "extreme_close_up", "over_the_shoulder", "top_down_map"] },
            "vertical_angle": { "enum": ["worm_eye_-30", "eye_level_0", "high_angle_30", "bird_eye_60"] },
            "horizontal_azimuth_deg": { "enum": [0, 45, 90, 135, 180, 225, 270, 315] },
            "camera_move": { "enum": ["static", "slow_push_in", "slow_pull_back", "pan_left", "pan_right", "tilt_up", "tilt_down", "parallax_dolly", "parallax_orbital"] },
            "multiangle_token": { "type": ["string", "null"], "description": "Optional <sks> camera token emitted by ComfyUI-qwenmultiangle." }
          }
        },
        "screen_composition": {
          "type": "object",
          "required": ["foreground", "midground", "background", "screen_direction_notes"],
          "properties": {
            "foreground": { "type": "string" },
            "midground": { "type": "string" },
            "background": { "type": "string" },
            "screen_direction_notes": { "type": "string" }
          }
        },
        "lighting_and_time": { "type": "string" },
        "continuity_refs": {
          "type": "object",
          "required": ["reuse_location_anchor", "inherit_from_previous_shot_id"],
          "properties": {
            "reuse_location_anchor": { "type": "boolean" },
            "inherit_from_previous_shot_id": { "type": ["string", "null"] }
          }
        },
        "keyframe_plan": {
          "type": "object",
          "required": ["needs_start_frame", "needs_end_frame", "start_frame_source", "end_frame_reason"],
          "properties": {
            "needs_start_frame": { "type": "boolean", "const": true },
            "needs_end_frame": { "type": "boolean" },
            "start_frame_source": { "enum": ["new_master_anchor", "multiangle_from_anchor", "edit_from_prev_shot", "reuse_existing_asset"] },
            "end_frame_reason": { "type": ["string", "null"], "description": "Required when needs_end_frame is true; must explain why start/end state transition is needed." }
          }
        },
        "image_prompt": {
          "type": "object",
          "required": ["start_frame_prompt", "negative_prompt"],
          "properties": {
            "start_frame_prompt": { "type": "string", "minLength": 20 },
            "end_frame_prompt": { "type": ["string", "null"] },
            "negative_prompt": { "type": "string" }
          }
        },
        "video_prompt": {
          "type": "object",
          "required": ["motion_prompt", "primary_action_count", "camera_move_count"],
          "properties": {
            "motion_prompt": { "type": "string", "minLength": 15 },
            "primary_action_count": { "type": "integer", "const": 1, "description": "Hard guardrail: exactly 1 primary physical action per simple shot." },
            "camera_move_count": { "type": "integer", "minimum": 0, "maximum": 1, "description": "Hard guardrail: at most 1 camera move per shot." },
            "parallax_preset": { "enum": ["dolly_in", "dolly_out", "orbital_left", "orbital_right", "pan_horizontal", "pan_vertical", "zoom_focus", null] }
          }
        },
        "selective_control": {
          "type": ["object", "null"],
          "description": "Populated ONLY when generation_mode == 'WAN_CONTROL'. Enforces single control modality.",
          "required": ["control_modality", "control_source_path", "escalation_reason"],
          "properties": {
            "control_modality": { "enum": ["openpose", "depth", "canny", "camera_preset", "trajectory_ati_experimental"] },
            "control_source_path": { "type": "string" },
            "control_strength": { "type": "number", "minimum": 0.1, "maximum": 1.0, "default": 0.75 },
            "escalation_reason": { "type": "string", "minLength": 10 }
          }
        },
        "transition_out": { "enum": ["hard_cut", "j_cut", "l_cut", "cross_dissolve_8f", "fade_to_black"] }
      }
    }
  }
}
```

### 2.4 Canonical Schema 2: `explainer_engine/schemas/wan_job.schema.json` (Replaces `ltx_job.schema.json` as Default)

Create `explainer_engine/schemas/wan_job.schema.json` to govern local ComfyUI video dispatch:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://explainer-engine.local/schemas/wan_job.schema.json",
  "title": "WanLocalVideoJobSpec",
  "type": "object",
  "required": [
    "job_id",
    "episode_id",
    "shot_id",
    "generation_mode",
    "model_tier",
    "workflow_template_path",
    "comfy_local_url",
    "start_image_path",
    "motion_prompt",
    "negative_prompt",
    "width",
    "height",
    "num_frames",
    "fps",
    "steps",
    "cfg_scale",
    "seed"
  ],
  "additionalProperties": false,
  "properties": {
    "job_id": { "type": "string" },
    "episode_id": { "type": "string" },
    "shot_id": { "type": "string", "pattern": "^S(0[1-9]|1[0-6])_SH[0-9]{3}$" },
    "generation_mode": { "enum": ["WAN_I2V", "WAN_FLF2V", "WAN_CONTROL", "STILL_25D", "MAP_25D"] },
    "model_tier": { "enum": ["wan22_fun_5b_inp", "wan22_fun_14b_inp", "wan22_fun_5b_control", "wan22_fun_14b_control", "depthflow_local_25d"] },
    "workflow_template_path": { "type": "string" },
    "comfy_local_url": { "type": "string", "pattern": "^https?://(127\\.0\\.0\\.1|localhost)(:[0-9]+)?$" },
    "start_image_path": { "type": "string" },
    "end_image_path": { "type": ["string", "null"] },
    "single_control_input": {
      "type": ["object", "null"],
      "required": ["modality", "control_file_path", "strength"],
      "properties": {
        "modality": { "enum": ["openpose", "depth", "canny", "camera_preset", "trajectory_ati_experimental"] },
        "control_file_path": { "type": "string" },
        "strength": { "type": "number", "minimum": 0.1, "maximum": 1.0 }
      }
    },
    "use_lightx2v_4step": { "type": "boolean", "default": false },
    "motion_prompt": { "type": "string" },
    "negative_prompt": { "type": "string" },
    "width": { "type": "integer", "enum": [832, 1280] },
    "height": { "type": "integer", "enum": [480, 720] },
    "num_frames": { "type": "integer", "enum": [49, 81, 121], "default": 81 },
    "fps": { "type": "integer", "const": 24 },
    "steps": { "type": "integer", "minimum": 4, "maximum": 40 },
    "cfg_scale": { "type": "number", "minimum": 1.0, "maximum": 7.0 },
    "seed": { "type": "integer" }
  }
}
```

### 2.5 Canonical Schema 3: `explainer_engine/schemas/render_telemetry.schema.json`

To satisfy the requirement that retry rates and cost/runtime numbers are measured empirically rather than copied from research estimates, Codex must create `explainer_engine/schemas/render_telemetry.schema.json`:

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "$id": "https://explainer-engine.local/schemas/render_telemetry.schema.json",
  "title": "LocalRenderTelemetryRecord",
  "type": "object",
  "required": [
    "timestamp_utc",
    "episode_id",
    "shot_id",
    "stage",
    "generation_mode",
    "model_id",
    "attempt_number",
    "wall_clock_seconds",
    "status",
    "qa_metrics"
  ],
  "properties": {
    "timestamp_utc": { "type": "string", "format": "date-time" },
    "episode_id": { "type": "string" },
    "shot_id": { "type": "string" },
    "stage": { "enum": ["keyframe_gen", "keyframe_edit", "video_gen", "parallax_25d"] },
    "generation_mode": { "type": "string" },
    "model_id": { "type": "string" },
    "use_lightx2v_4step": { "type": "boolean" },
    "attempt_number": { "type": "integer", "minimum": 1 },
    "wall_clock_seconds": { "type": "number", "minimum": 0 },
    "peak_vram_mb": { "type": ["number", "null"] },
    "status": { "enum": ["ACCEPTED", "REJECTED_AUTO_QA", "REJECTED_HUMAN", "ESCALATED_TO_CONTROL", "ERROR_RUNTIME"] },
    "failure_reason": { "type": ["string", "null"] },
    "qa_metrics": {
      "type": "object",
      "properties": {
        "duration_match": { "type": "boolean" },
        "frozen_frame_ratio": { "type": "number" },
        "boundary_jump_score": { "type": "number" }
      }
    }
  }
}
```

---

## 3\. Documentation & Codebase Reorganization Manifest (Phase 3\)

### 3.1 Documentation Reorganization By Group (Groups A–G)

#### Group A — Project & Episode Format

- **Modify [`docs/PROJECT_BRIEF.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/PROJECT_BRIEF.md):**  
  - *Section `## Products` & `## Hard constraints`:* Replace the legacy `5–11 minute range (7-minute target)` and `D-120` 11-minute references with the canonical **12-minute (720-second) historical What-If docudrama format** organized into **16 segments (`S01–S16`)** across **5 narrative phases (`Z1–Z5`)**.  
  - *Section `## Positioning` & `## Visual Mix`:* Document the **70–80% narrator / 20–30% character dialogue** spoken target and the **flexible 60% cinematic video / 30% composed illustrations / 10% animated maps** visual target (explicitly stating 60/30/10 is a flexible storytelling guide, not a rigid mathematical quota).  
  - *Section `## Local-Only Execution Rule`:* Add hard constraint that all default generation runs locally and free via ComfyUI (`http://127.0.0.1:8188`).  
- **Modify [explainer\_engine/schemas/episode\_rules.schema.json](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/schemas/episode_rules.schema.json):** Update default `target_duration_seconds` to `720`, `segments_count` to `16`, and `phases_count` to `5`.

#### Group B — ChatGPT Main Production Method

- **Create `docs/MAIN_METHOD.md` (and symlink or stub root [`CHATGPT.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/CHATGPT.md) & [`docs/CHATGPT_WORKFLOW.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/CHATGPT_WORKFLOW.md) to point directly to `docs/MAIN_METHOD.md`):**  
  - Author the complete 12-section canonical manual specified in Section 4 of this plan.  
  - Replace the body of [`docs/CHATGPT_WORKFLOW.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/CHATGPT_WORKFLOW.md) with a 10-line pointer to `docs/MAIN_METHOD.md` so no conflicting workflow instructions remain.

#### Group C — Story & Script Rules

- **Consolidate [docs/STORY\_ENGINE.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/STORY_ENGINE.md), [docs/SCRIPT\_ENGINE.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCRIPT_ENGINE.md), and [docs/SCRIPTING\_SPEC.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCRIPTING_SPEC.md):**  
  - *In `docs/STORY_ENGINE.md` (`## Act Decomposition` & `## Pacing & Duration`):* Replace the 5–7 act structure with the 5 narrative phases (`Z1` Hook & Setup 0:00–2:00 `S01–S03`, `Z2` Point of Divergence 2:00–4:00 `S04–S06`, `Z3` Escalation & Transformation 4:00–7:00 `S07–S10`, `Z4` Major Consequences & Climax 7:00–10:00 `S11–S14`, `Z5` Resolution & Reflection 10:00–12:00 `S15–S16`). Preserve causal chain (`cause_from_segment_id` → `effect_to_segment_id`) and historical vs. counterfactual boundary rules.  
  - *In `docs/SCRIPT_ENGINE.md` (`## Shot Breakdown` & `## Schema Enforcement`):* Remove `J1–J5` routing and LTX keyframe rules; align strictly with `production_script.schema.json` v4.0 (`audio_lines` \+ `shots` in one file). Preserve `narration_lint`, `register_lint`, `rhythm_lint`, and `claims.py` fact-checking rules.  
  - *In `docs/SCRIPTING_SPEC.md`:* Convert into a thin pointer to `docs/SCRIPT_ENGINE.md` and `docs/MAIN_METHOD.md` Section 4\.

#### Group D — Visual Script, Assets & Image Generation

- **Reconcile [docs/SHOT\_PROMPTS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SHOT_PROMPTS.md), [docs/SCENE\_ASSETS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCENE_ASSETS.md), and [docs/SCENE\_REUSE\_RULES.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/SCENE_REUSE_RULES.md):**  
  - *In `docs/SCENE_ASSETS.md`:* Remove mandatory `.blend` file creation, `xworld_v2` 3D camera rig setup, and grease-pencil layer extraction (`## Blender Layout Files`, `## xworld_v2 Rigging`, `## Grease Pencil Vectors`). Replace with **2D Master Asset & Cast Creation** (`char_<id>_turnaround.png`, `loc_<id>_anchor.png`, `prop_<id>_anchor.png`).  
  - *In `docs/SCENE_REUSE_RULES.md`:* Replace Blender scene environment caching with **2D Anchor & Multi-Angle Keyframe Reuse** (`reuse_location_anchor: true`, passing the master location anchor and character turnaround sheets into Qwen multi-angle/edit workflows).  
  - *In `docs/SHOT_PROMPTS.md`:* Replace `## LTX Motion Prompts` and multi-keyframe cards with **Stage 2 Qwen Keyframe Prompt Rules** (including `<sks>` multi-angle tokens and start/end frame selection rules) and **Stage 3 Wan 2.2 Motion Prompt Rules** (1 primary action \+ at most 1 camera move).

#### Group E — Video Generation Guides

- **Create `docs/VIDEO_GENERATION_WAN.md` and Deprecate [docs/pods/P12\_LTX\_FLAGS.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/pods/P12_LTX_FLAGS.md) & [docs/VIDEO\_PARAMETER\_SPEC.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/VIDEO_PARAMETER_SPEC.md) LTX defaults:**  
  - Document the primary **Wan 2.2 Fun InP / I2V** workflow (`WAN_I2V` vs. `WAN_FLF2V` decision rules, 81-frame 5s standard clip length, `5B` vs `14B` tier selection, `LightX2V` 4-step vs 20-step unaccelerated rules, and seed retry rules).  
  - Document the separate, explicitly optional **Secondary Selective Control Workflow (`WAN_CONTROL`)** using `Wan 2.2 Fun Control` with a single control modality (`openpose`, `depth`, `canny`, or `camera_preset`).  
  - Move `docs/pods/P12_LTX_FLAGS.md` to `docs/archive/P12_LTX_FLAGS_2026-11-08.md`.

#### Group F — Local Runtime & Model Setup

- **Create `docs/LOCAL_COMFYUI_SETUP.md` and Update [docs/CLOUD\_RUNBOOK.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/CLOUD_RUNBOOK.md):**  
  - Specify local ComfyUI setup, `config/local_models.json` schema, `.env` variable names, `python -m explainer_engine.production --check-local` health validation, and strict model weight exclusion from Git.  
  - Add an explicit banner at the top of `docs/CLOUD_RUNBOOK.md` marking cloud pods as **Disabled by Default (`EXPLAINER_LOCAL_ONLY=1`)**.

#### Group G — Audio, Editing, Orchestration & QA

- **Reconcile [docs/AUDIO\_SYSTEM.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/AUDIO_SYSTEM.md), [`docs/EDITING.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/EDITING.md), [docs/ORCHESTRATION.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/ORCHESTRATION.md), [docs/PRODUCTION\_RULES.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/PRODUCTION_RULES.md), [`docs/CONTRACTS.md`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/CONTRACTS.md), and [docs/TOOL\_STRATEGY.md](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/docs/TOOL_STRATEGY.md):**  
  - *In `docs/EDITING.md`:* Remove `J5` multi-keyframe LTX splicing and mandatory Blender grease-pencil overlay rules from `ED-01..ED-15`; update to assemble independent Wan 2.2 clips \+ deterministic 2.5D still/map clips locked to `audio_spine` timestamps at 24fps.  
  - *In `docs/ORCHESTRATION.md` & `docs/PRODUCTION_RULES.md`:* Replace `paid_preflight.py` cloud budget checks with `local_preflight.py` ComfyUI/model verification and `render_telemetry.jsonl` logging.  
  - *In `docs/TOOL_STRATEGY.md`:* Replace `J1–J5` route classification with the 5 canonical `generation_mode` routes (`WAN_I2V`, `WAN_FLF2V`, `WAN_CONTROL`, `STILL_25D`, `MAP_25D`).

### 3.2 Complete File-by-File Code & Config Action Manifest

| Action | File Path | Exact Modification / Consolidation Specification |
| :---- | :---- | :---- |
| **CREATE** | `docs/MAIN_METHOD.md` | Canonical 12-section ChatGPT production manual (exact contents specified in Section 4 below). |
| **CREATE** | `docs/VIDEO_GENERATION_WAN.md` | Local Wan 2.2 Fun InP / I2V \+ selective Fun Control \+ DepthFlow 2.5D production guide. |
| **CREATE** | `docs/LOCAL_COMFYUI_SETUP.md` | Local ComfyUI verification, `.env` variable reference, custom node commit pins, and model path guide. |
| **CREATE** | `config/local_models.json` | Local checkpoint, LoRA, custom node, workflow JSON, and licence registry (Section 5.2). |
| **CREATE** | `workflows/comfyui/qwen_keyframe_multiangle.json` | API-format ComfyUI workflow for Stage 2 keyframe generation/editing (`Qwen-Image-Edit-2511` \+ `QwenMultiangleCameraNode` or `Qwen-Image-2.1` \+ `xworld_v2`). |
| **CREATE** | `workflows/comfyui/wan22_fun_inp_flf2v.json` | API-format ComfyUI workflow for `WanFunInpaintToVideo` (supports single start frame `WAN_I2V` and start+end frame `WAN_FLF2V` for `5B` and `14B`). |
| **CREATE** | `workflows/comfyui/wan22_fun_control.json` | API-format ComfyUI workflow for selective `Wan22FunControlToVideo` (single control input: `openpose`, `depth`, `canny`, or `camera_preset`). |
| **CREATE** | `workflows/comfyui/depthflow_25d_motion.json` | API-format ComfyUI workflow for deterministic 2.5D parallax on illustrations and maps (`Depth-Anything-V2` \+ `ComfyUI-Depthflow-Nodes`). |
| **CREATE** | `explainer_engine/schemas/wan_job.schema.json` | JSON Schema for local Wan 2.2 / DepthFlow jobs (Section 2.4). |
| **CREATE** | `explainer_engine/schemas/keyframe_manifest.schema.json` | JSON Schema tracking Stage 2 approved keyframe paths, seeds, and approval status. |
| **CREATE** | `explainer_engine/schemas/render_telemetry.schema.json` | JSON Schema for empirical local runtime, retry, and QA telemetry logging (Section 2.5). |
| **CREATE** | `explainer_engine/aivideo/wan_runner.py` | Local ComfyUI HTTP/WebSocket dispatcher for `wan22_fun_inp_flf2v.json`, `wan22_fun_control.json`, and `depthflow_25d_motion.json` with telemetry logging. |
| **CREATE** | `explainer_engine/production/local_preflight.py` | Replaces `paid_preflight.py` as default: checks `EXPLAINER_LOCAL_ONLY`, `GET /system_stats`, `GET /object_info`, local model files, and approved keyframes. |
| **CREATE** | `scripts/run_phase1_ablations.py` | Runs `T-ABL-01` through `T-ABL-04` compatibility checks and writes `jobs/phase1_ablation_report.json`. |
| **CREATE** | `tests/fixtures/pilot_60s_waterloo.json` | Canonical 12-shot (60s) Waterloo counterfactual fixture conforming to `production_script.schema.json` v4.0. |
| **MODIFY** | `explainer_engine/vault.py` | Add `.env` key readers (`get_comfyui_url()`, `get_comfyui_models_dir()`, `is_local_only()`) without printing or exposing secret values. |
| **MODIFY** | `config/model_routing.json` | Remove hosted cloud endpoints (`api.ltx-cloud.internal`, `qwen-api.internal`) from default routes; point default image/video routes to `local_comfyui` via `config/local_models.json`. |
| **MODIFY** | `explainer_engine/schemas/production_script.schema.json` | Upgrade to v4.0 schema (`Z1–Z5`, `S01–S16`, unified `world_bible`, `audio_lines`, and `shots` with `WAN_I2V`/`WAN_FLF2V`/`WAN_CONTROL`/`STILL_25D`/`MAP_25D`). |
| **MODIFY** | `explainer_engine/schemas/shot_route.schema.json` | Replace `route_type` enum `["J1","J2","J3","J4","J5"]` with `["WAN_I2V","WAN_FLF2V","WAN_CONTROL","STILL_25D","MAP_25D","WAN_FALLBACK_LTX"]`. |
| **MODIFY** | `explainer_engine/imagegen/routing.py` | Update `ShotRouter` to route Stage 2 keyframe jobs to local ComfyUI Qwen workflows (1 start frame by default; end frame only for `WAN_FLF2V`) and remove `https://qwen-api.internal/v2/generate`. |
| **MODIFY** | `explainer_engine/aivideo/shotplan.py` | Replace `build_ltx_payload()` default with `build_wan_payload()` validating against `wan_job.schema.json` and remove `https://api.ltx-cloud.internal/v1/jobs`. |
| **MODIFY** | `explainer_engine/scripting/shot_prompt_lint.py` | Enforce single primary action (`primary_action_count == 1`), max 1 camera move (`camera_move_count <= 1`), single control input on `WAN_CONTROL`, and ban spoken dialogue strings inside visual prompts. |
| **MODIFY** | `explainer_engine/production/__main__.py` | Add `--check-local`, `--stage {1,2,3,4,all}`, `--pilot-60s`, and wire default preflight to `local_preflight.py` instead of `paid_preflight.py`. |
| **MODIFY** | `explainer_engine/production_gate.py` | Update pre-render and post-render gates to validate `wan_job.schema.json`, check keyframe approval status before Stage 3, and record metrics to `render_telemetry.jsonl`. |
| **DEPRECATE** | `explainer_engine/production/paid_preflight.py` | Gate behind explicit `--allow-paid-cloud` flag (`EXPLAINER_LOCAL_ONLY=0`); remove `https://cloud-run.internal/preflight/verify` from default path. |
| **DEPRECATE** | `explainer_engine/schemas/ltx_job.schema.json` | Retain only for explicit `WAN_FALLBACK_LTX` legacy tests; remove from default pipeline validation. |
| **DEPRECATE** | `explainer_engine/blender/` (30 of 31 modules) | Keep `assemble_25d.py` as optional local 2.5D fallback; mark 3D layout/grease-pencil/crowd/world-kit modules (`scene_builder.py`, `layout_passes.py`, `world_kits.py`, `stoneage_qwen_jobs.py`, etc.) as deprecated legacy tools and disable `.github/workflows/blender-smoke.yml`, `crowd-proof.yml`, and `world-kits.yml` on default PR runs. |

---

## 4\. Structure and Mandatory Contents of `docs/MAIN_METHOD.md` (Phase 4\)

Codex must create `docs/MAIN_METHOD.md` containing the exact 12-section structure, rules, templates, and checklists below. This document is the single self-contained manual that ChatGPT reads when authoring a new Explainer Engine episode.

```markdown
# Explainer Engine — Main Production Method (`MAIN_METHOD.md`)
Version: 4.0 (2026-11-09)
Canonical Schema Contract: `explainer_engine/schemas/production_script.schema.json` (v4.0.0)

## Role & Operating Boundary
You (ChatGPT) are the **Narrative Architect, Historical Researcher, and Visual Script Director** for **Explainer Engine**.
- **What you do:** Gather the episode brief, build a source-backed historical dossier, structure the 12-minute (`S01–S16` / `Z1–Z5`) narrative, write the narration and dramatized character dialogue, define the Character/Location/Prop Bible, and author the complete shot-by-shot visual script with exact image and video prompts inside one canonical `production_script.json`.
- **What the Local Engine does:** Executes local ComfyUI image generation (`Qwen-Image`), local video generation (`Wan 2.2 Fun InP / I2V / Control`), deterministic 2.5D parallax (`DepthFlow`), local TTS/audio synthesis, and 24fps NLE assembly.
- **Hard Prohibition:** Never claim that you have rendered, inspected, or approved an image, audio stem, or video clip. Never invent parallel shotlist formats, never use paid cloud API assumptions, and never stack multiple simultaneous actions, camera moves, or control passes into a single shot.

---

## Stage 1: Episode Brief
### Required Inputs from Creator
Before drafting the dossier or script, confirm (or use explicitly stated defaults for):
1. `what_if_premise`: The single central counterfactual question (e.g., *"What if Napoleon had won at Waterloo?"*).
2. `historical_period_and_anchor_event`: Exact date, theatre, and real-world historical baseline.
3. `target_duration_seconds`: Default `720` seconds (12 minutes; acceptable range `660–780s`).
4. `tone_and_audience`: Broad English-language audience interested in history and cinematic counterfactual storytelling; stylized **2.5D Ink Chronicle** docudrama tone.
5. `existing_asset_constraints`: Any recurring historical characters or locations already present in `assets/library.json`.

### Mandatory Output Fields
- `episode_id` (`ep_<slug>`), `title`, `what_if_premise`, `target_duration_seconds` (`720`), `fps` (`24`).

### Reusable Episode Brief Template
```yaml
episode_id: ep_waterloo_napoleon_victory
title: "What If Napoleon Had Crushed Wellington at Waterloo?"
what_if_premise: "On June 18, 1815, Marshal Grouchy marches toward the sound of the guns at Wavre, intercepting Blücher's Prussians and allowing the Imperial Guard to break Wellington's center at Mont-Saint-Jean."
target_duration_seconds: 720
fps: 24
visual_style: "2.5D Ink Chronicle historical docudrama illustration"
```

&nbsp;

### Validation Checklist

- [ ] Premise hinges on one concrete, historically grounded point of divergence (not magical or sci-fi intervention).  
- [ ] Target duration is set to `720` seconds (`60` seconds only when explicitly running a 1-segment pilot).

### What ChatGPT Must NOT Invent or Overcomplicate

- Do not introduce multiple unrelated points of divergence in the same episode.  
- Do not invent fictional protagonists when documented historical figures carried the real decision.

### What Gets Passed to the Local Engine

- Top-level header fields of `jobs/<episode_id>/01_script/production_script.json`.

---

## Stage 2: Historical Research Dossier

### Required Inputs

- Confirmed Episode Brief and verified historical primary/secondary sources.

### Mandatory Output Fields (in `jobs/<episode_id>/01_script/research_dossier.md`)

1. **Verified Chronology (`Actual History`):** Date-stamped timeline leading up to and immediately following the anchor event.  
2. **Key Historical Figures:** Full names, titles, ages in the anchor year, documented motivations, and physical/uniform descriptions.  
3. **The Exact Point of Divergence (`PoD`):** The physical, military, political, or technological mechanism that changes and why it was historically plausible.  
4. **First-, Second-, and Third-Order Counterfactual Consequences:** Grounded in logistics, geography, economics, and institutional incentives.  
5. **Uncertain Claims & Speculation Boundaries:** Explicit table separating `verified_historical_fact` from `plausible_counterfactual_inference`.

### Reusable Dossier Template

```markdown
# Historical Research Dossier: [Episode Title]
## 1. Verified Real-World Baseline & Citations
- [CITE-01] Date / Fact / Source Title & URL
## 2. Historical Cast & Institutional Motivations
- Figure Name | Role | Verified Motivation | Period Uniform & Appearance
## 3. Point of Divergence (PoD) Feasibility Analysis
- Real Decision vs. Counterfactual Decision | Immediate Physical Mechanism
## 4. Causal Chain (Z2 -> Z5)
- Immediate (Days/Weeks) -> Medium-Term (Months/Years) -> Long-Term (Decades)
## 5. Fact vs. Speculation Boundary Ledger
| Claim | Status (`verified_historical_fact` / `plausible_counterfactual_inference`) | Source / Reasoning |
```

&nbsp;

### Validation Checklist

- [ ] Every pre-divergence historical date, treaty, troop strength, and geography claim cites a verifiable source (`[CITE-xx]`).  
- [ ] Counterfactual consequences obey physical logistics (supply lines, travel speed, treasury limits, coalition politics).

### What ChatGPT Must NOT Invent or Overcomplicate

- Never present counterfactual events using factual archival phrasing without signalling the counterfactual timeline.  
- Never fabricate historical quotes; dramatized in-scene dialogue must be tagged `dramatized_in_scene_speech`.

### What Gets Passed to the Local Engine

- Saved to `jobs/<episode_id>/01_script/research_dossier.md` and referenced via `historical_dossier_ref` in `production_script.json` for `explainer_engine/scripting/claims.py`.

---

## Stage 3: 12-Minute Story Structure (`Z1–Z5` & `S01–S16`)

### Required Inputs

- Approved Historical Research Dossier.

### Mandatory Output Fields

Every full episode MUST populate all **5 narrative phases (`Z1–Z5`)** and **16 segments (`S01–S16`)** inside `production_script.json`:

| Phase | Target Window | Segments | Segment Roles & Mandatory Narrative Objective |
| :---- | :---- | :---- | :---- |
| **`Z1` — Hook & Historical Setup** | `0:00–2:00` (\~120s) | `S01`, `S02`, `S03` | **`S01`:** Striking counterfactual hook/consequence. **`S02`:** Real historical context, cast, and locations (`actual_history`). **`S03`:** Critical decision/event at stake. |
| **`Z2` — The Point of Divergence** | `2:00–4:00` (\~120s) | `S04`, `S05`, `S06` | **`S04`:** Historical event unfolds differently (`divergence_point`). **`S05`:** Immediate physical/tactical consequences. **`S06`:** First major shockwaves and reactions from commanders/governments. |
| **`Z3` — Escalation & Transformation** | `4:00–7:00` (\~180s) | `S07`, `S08`, `S09`, `S10` | **`S07`:** First major systemic consequences develop. **`S08`:** New conflicts, coalitions, or unexpected friction. **`S09`:** Key characters and institutions respond. **`S10`:** Major turning point locking in the new timeline. |
| **`Z4` — Major Consequences & Climax** | `7:00–10:00` (\~180s) | `S11`, `S12`, `S13`, `S14` | **`S11`:** Wider political/military/economic/social transformation. **`S12`:** Contrast alternative world vs. real history. **`S13`:** Build toward central crisis/climax. **`S14`:** Deliver the single most significant climax consequence. |
| **`Z5` — Resolution & Reflection** | `10:00–12:00` (\~120s) | `S15`, `S16` | **`S15`:** Resulting world, long-term institutional fate, and character fates. **`S16`:** Meaningful historical reflection answering the core What-If question (`historical_reflection`). |

### Validation Checklist

- [ ] Every segment `S02–S16` specifies a non-null `cause_from_segment_id` linking it to the preceding cause (“Therefore…”, never “And then…”).  
- [ ] Segment durations vary naturally by dramatic weight while summing to \~`720` seconds (`660–780s`).

### What ChatGPT Must NOT Invent or Overcomplicate

- Do not impose a rigid 45.0-second mechanical timer on every segment; let climax segments (`S04`, `S10`, `S14`) breathe and setup/transition segments run tighter.

### What Gets Passed to the Local Engine

- `phases` and `segments` arrays in `production_script.json`.

---

## Stage 4: Script-Writing Guide (Narration & Dialogue Spine)

### Required Inputs

- Approved `Z1–Z5` / `S01–S16` segment outline.

### Mandatory Output Fields (`audio_lines` array)

- `line_id` (`S01_L001`), `segment_id`, `speaker_type` (`narrator`, `character`, `silent_beat`), `speaker_id`, `addressee_id`, `delivery_direction`, `text`, `register_type` (`verified_historical_fact`, `plausible_counterfactual_inference`, `dramatized_in_scene_speech`), `citation_ids`, `estimated_duration_seconds` (calculated at \~2.5 words/sec or 150 WPM plus pauses), `requires_visible_lipsync` (`boolean`).

### Spoken Balance & Register Rules

1. **70–80% Narrator Voiceover (`speaker_type: "narrator"`):** Carries historical context, macro transitions, analytical cause-and-effect, and timeline leaps.  
2. **20–30% Character Dialogue (`speaker_type: "character"`):** Short, punchy, era-appropriate dramatized exchanges at key turning points (`S03`, `S04`, `S09`, `S10`, `S14`). Maximum 2 sentences per spoken turn.  
3. **Explicit Speculation Signalling:** When transitioning from `actual_history` (`S02–S03`) to `divergence_point` (`S04`) and `counterfactual_consequence` (`S05–S15`), narration must use clear analytical markers (*"In this altered timeline..."*, *"With Prussian forces pinned at Wavre..."*) so viewers never confuse counterfactual events with real history.

### Reusable Audio Line Template

```json
{
  "line_id": "S04_L001",
  "segment_id": "S04",
  "speaker_type": "narrator",
  "speaker_id": "narrator_main",
  "addressee_id": null,
  "delivery_direction": "grave, measured documentary pacing",
  "text": "At 11:30 AM in actual history, Marshal Grouchy ignored the distant thunder of Waterloo. Here, he turns his thirty thousand men west toward the sound of the guns.",
  "register_type": "plausible_counterfactual_inference",
  "citation_ids": ["CITE-04"],
  "estimated_duration_seconds": 9.5,
  "requires_visible_lipsync": false
}
```

### Validation Checklist

- [ ] Total `narrator` duration is between `70%` and `80%` of spoken duration; `character` dialogue is between `20%` and `30%`.  
- [ ] Every line passes `narration_lint.py`, `register_lint.py`, and `rhythm_lint.py` (no modern slang, no throat-clearing filler).

### What ChatGPT Must NOT Invent or Overcomplicate

- Never embed camera directions or visual prompt instructions inside `audio_lines[].text`.

### What Gets Passed to the Local Engine

- `audio_lines` array in `production_script.json`, consumed by `explainer_engine/audio/` and `explainer_engine/production/timing.py`.

---

## Stage 5: Visual-Script Guide (Shot Breakdown & 60/30/10 Allocation)

### Required Inputs

- Approved `segments` and `audio_lines`.

### Mandatory Output Fields (`shots` array)

Every shot object in `shots[]` MUST define:

- `shot_id` (`S01_SH001`), `segment_id` (`S01`), `target_duration_seconds` (`2.0–12.0`, default `5.0`), `narrative_purpose`, `visual_type` (`cinematic_video`, `composed_illustration`, `map_visualization`), `generation_mode` (`WAN_I2V`, `WAN_FLF2V`, `WAN_CONTROL`, `STILL_25D`, `MAP_25D`), `location_id`, `character_ids`, `prop_ids`, `audio_line_ids`, `action_start_state`, `action_end_state`, `camera_spec`, `screen_composition`, `lighting_and_time`, `continuity_refs`, `keyframe_plan`, `image_prompt`, `video_prompt`, `selective_control` (`null` unless `WAN_CONTROL`), and `transition_out`.

### Visual Type & Generation Mode Routing Rules

1. **`cinematic_video` (\~60% flexible target) → `WAN_I2V` or `WAN_FLF2V`:**  
   - Use for physical character actions, emotional reactions, troop movement, and dramatic turning points.  
   - Default clip duration: **5.0 seconds** (`81` frames at 24fps/16fps resample).  
2. **`composed_illustration` (\~30% flexible target) → `STILL_25D`:**  
   - Use for sweeping architectural panoramas, institutional portraits, treaty signings, and dense historical tableaux where 2D painterly detail and slow 2.5D parallax (`DepthFlow`) outperform video diffusion.  
3. **`map_visualization` (\~10% flexible target) → `MAP_25D`:**  
   - Use for strategic geography, troop corridors, border shifts, and trade routes animated via deterministic 2.5D pan/zoom (`DepthFlow`).

### Validation Checklist

- [ ] Every `audio_line_id` in `audio_lines[]` is covered by at least one shot in `shots[]`.  
- [ ] Sum of `shots[].target_duration_seconds` within each segment equals `segments[].target_duration_seconds` ($\pm 0.5\text{s}$).  
- [ ] 180-degree screen direction axis (`screen_composition.screen_direction_notes`) is preserved across adjacent cuts in the same scene.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never create a separate `shotlist.json` or `prompts.md` outside `production_script.json`.

### What Gets Passed to the Local Engine

- `shots[]` array inside `production_script.json`.

---

## Stage 6: Character, Location & Prop Bible (`world_bible`)

### Required Inputs

- Historical cast, settings, and signature objects from the Dossier.

### Mandatory Output Fields (`world_bible`)

- `style_anchor_token`: Fixed episode-wide aesthetic string (`"2.5D Ink Chronicle historical docudrama illustration, bold ink linework, painterly chiaroscuro shading, muted period palette"`).  
- `characters[]`: `character_id` (`char_napoleon_1815`), `name`, `historical_role`, `fixed_appearance_prompt` (exact age, facial structure, hair, uniform/coat color, epaulets, headwear), `costume_continuity_notes`, `reference_sheet_path` (`02_keyframes/assets/char_<id>_turnaround.png`).  
- `locations[]`: `location_id` (`loc_waterloo_ridge`), `name`, `era_and_geography`, `fixed_environment_prompt`, `lighting_palette`, `anchor_image_path`.  
- `props[]`: `prop_id` (`prop_imperial_eagle_standard`), `name`, `fixed_prop_prompt`, `anchor_image_path`.

### Validation Checklist

- [ ] Every ID referenced in `shots[].character_ids`, `shots[].location_id`, and `shots[].prop_ids` exists in `world_bible`.  
- [ ] `fixed_appearance_prompt` is verbatim-reusable and never changes a character's core facial features or uniform across shots within the same historical era.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never invent a fresh character description per shot; always inject the canonical `fixed_appearance_prompt` from `world_bible`.

### What Gets Passed to the Local Engine

- `world_bible` object in `production_script.json`, consumed by `explainer_engine/imagegen/` and `explainer_engine/assets_reuse.py`.

---

## Stage 7: Image Generation Guide (Stage 2 Keyframes)

### Required Inputs

- `world_bible` anchors and per-shot `camera_spec`, `screen_composition`, and `keyframe_plan`.

### Keyframe Decision Rules

1. **When to Reuse an Existing Asset (`start_frame_source: "reuse_existing_asset"`):** If returning to an identical framing in an established scene or holding on a map base.  
2. **When to Generate a Multi-Angle Variant (`start_frame_source: "multiangle_from_anchor"`):** Standard path for 80%+ of shots. Pass the approved `loc_<id>_anchor.png` and `char_<id>_turnaround.png` into the local Qwen workflow with `camera_spec` (`horizontal_azimuth_deg`, `vertical_angle`, `shot_size`).  
   - *Important Technical Caveat:* `QwenMultiangleCameraNode` \+ `Multiple-Angles-LoRA` provides **learned camera-prompt control**, not physical 3D projection. Write clear foreground/midground/background composition descriptions alongside the `<sks>` token.  
3. **When to Generate an End Frame (`needs_end_frame: true`, `generation_mode: "WAN_FLF2V"`):** Create an End Frame **ONLY** when the shot requires a specific destination state (e.g., a character rises from a map table and walks to a window, or doors swing open to reveal an army). Do **not** generate end frames for simple gestures, breathing, atmospheric rain/smoke, or subtle camera pushes (`needs_end_frame: false`, `generation_mode: "WAN_I2V"`).  
4. **2D Repair Rule Before Video:** Any anatomical, hand, weapon, or text defect in a generated keyframe must be fixed in 2D image space (seed retry or `Qwen-Image-Edit` region edit) before Stage 3 video generation begins.

### Reusable Image Prompt Template (`image_prompt.start_frame_prompt`)

```
[STYLE_ANCHOR_TOKEN]. [MULTIANGLE_TOKEN_IF_USED] [SHOT_SIZE], [VERTICAL_ANGLE]. Location: [FIXED_ENVIRONMENT_PROMPT], [LIGHTING_AND_TIME]. Foreground: [FOREGROUND_COMPOSITION]. Midground: [CHARACTER_FIXED_APPEARANCE_PROMPT] performing [ACTION_START_STATE] holding [FIXED_PROP_PROMPT]. Background: [BACKGROUND_COMPOSITION]. Crisp ink contours, dramatic historical lighting, no modern artifacts, no text overlays.
```

- **Standard `negative_prompt`:** `"photorealistic DSLR skin pores, 3D CGI plastic sheen, anime cel-shading, extra fingers, malformed hands, modern clothing, watermark, subtitles, text banner, blurry lines"`

### Validation Checklist

- [ ] `needs_end_frame` is `true` if and only if `generation_mode == "WAN_FLF2V"` and `end_frame_reason` is non-null.  
- [ ] `image_prompt.start_frame_prompt` embeds the exact `style_anchor_token` and character/location descriptors.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never request 3 or more keyframes (no middle keyframes).  
- Never assume `Next-Scene LoRA` (`2509` base) is stacked with `Multiple-Angles LoRA`.

### What Gets Passed to the Local Engine

- `keyframe_plan` and `image_prompt` objects inside each shot of `production_script.json`, executed via `workflows/comfyui/qwen_keyframe_multiangle.json`.

---

## Stage 8: Video Generation Guide (Stage 3 Per-Shot Wan 2.2)

### Required Inputs

- Approved Start Frame (`Sxx_SHyyy_start.png`), optional Approved End Frame (`Sxx_SHyyy_end.png`), and `video_prompt`.

### `WAN_I2V` vs. `WAN_FLF2V` vs. `WAN_CONTROL` Selection Matrix

| Mode | Inputs Passed to Local Wan 2.2 | When to Select |
| :---- | :---- | :---- |
| **`WAN_I2V`** *(Default Video)* | `start_image` \+ `motion_prompt` | Single-state actions, subtle character expression/posture shifts, environmental motion (smoke, rain, banners), or simple slow push/pan. |
| **`WAN_FLF2V`** *(Bridged Video)* | `start_image` \+ `end_image` \+ `motion_prompt` | Shots where the character or camera must arrive at a specific final pose/composition (`action_end_state`) to match the next cut. |
| **`WAN_CONTROL`** *(Selective Fallback Only)* | `start_image` \+ `motion_prompt` \+ **EXACTLY ONE** `control_modality` (`openpose`, `depth`, `canny`, or `camera_preset`) | **Only** when a shot has failed standard `WAN_I2V`/`WAN_FLF2V` or involves complex physical choreography that start/end frames cannot express. |

### Mandatory Video Prompt Rules (Anti-Overconditioning)

1. **One Action \+ At Most One Camera Move Rule:** Every `video_prompt.motion_prompt` must specify **exactly 1 primary subject action** (`primary_action_count: 1`) and **at most 1 camera movement** (`camera_move_count: 0` or `1`).  
2. **Temporal Progression Phrasing:** Describe motion sequentially over the 5-second window: `[Subject] starts in [Start State], smoothly [Single Action Verb + Direction] while [Environment Motion]. Camera: [Static or Single Camera Move].`  
3. **No Contradictory Conditioning:** Never command a camera pan left in `motion_prompt` if `start_image` and `end_image` depict a static locked frame.

### Reusable Video Prompt Template (`video_prompt.motion_prompt`)

```
Subject: [Character/Object] smoothly [1 clear physical action from action_start_state to action_end_state]. Environment: [Subtle secondary motion: wind in cloak, drifting cannon smoke, flickering lantern]. Camera: [Static locked frame OR slow push-in / pan]. Maintain 2.5D Ink Chronicle linework and consistent facial features.
```

### Validation Checklist

- [ ] `primary_action_count == 1` and `camera_move_count <= 1`.  
- [ ] `selective_control` is `null` for all baseline shots, and contains only 1 modality when `generation_mode == "WAN_CONTROL"`.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never stack OpenPose \+ Depth \+ Canny \+ Multi-Reference in the same video job.  
- Never write spoken dialogue lines or sound effects inside `video_prompt.motion_prompt`.

### What Gets Passed to the Local Engine

- `generation_mode`, `video_prompt`, and `selective_control` fields in `production_script.json`, compiled into `wan_job.schema.json` payloads by `explainer_engine/aivideo/shotplan.py`.

---

## Stage 9: Dialogue & Audio Guide

### Required Inputs

- `audio_lines[]` and matching `shots[]`.

### Mandatory Coverage Rules

1. **Narrator Spine First:** All shot durations (`target_duration_seconds`) are slaved to the synthesized duration of their linked `audio_line_ids`.  
2. **Default Dialogue Visual Coverage (No Mandatory Lip-Sync):** Cover 80%+ of character dialogue lines using over-the-shoulder (`over_the_shoulder`) framing, medium profile shots, cutaway reaction shots of the listener (`addressee_id`), or shadow/silhouette compositions where `requires_visible_lipsync: false`.  
3. **Selective Lip-Sync Escalation (`requires_visible_lipsync: true`):** Set `requires_visible_lipsync: true` **only** on pivotal close-up dramatic lines (at most 2–4 shots per episode) where seeing the speaker's mouth synchronization materially elevates emotional impact (routed locally to `InfiniteTalk` if installed, or downgraded gracefully to an OTS reaction cut if unavailable).

### Validation Checklist

- [ ] `requires_visible_lipsync` is `false` on all `narrator` lines and on non-close-up `character` lines.  
- [ ] Every `character` line specifies `speaker_id`, `addressee_id`, and `delivery_direction`.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never require a heavy lip-sync diffusion pass for every dialogue line in an episode.

### What Gets Passed to the Local Engine

- `audio_lines[]` and `requires_visible_lipsync` flags in `production_script.json`.

---

## Stage 10: Stills & Maps Guide (Deterministic 2.5D Motion)

### Required Inputs

- Shots with `visual_type: "composed_illustration"` (`generation_mode: "STILL_25D"`) or `visual_type: "map_visualization"` (`generation_mode: "MAP_25D"`).

### Mandatory Execution Rules

1. **Zero Video Diffusion on Stills & Maps:** Composed historical illustrations (\~30% of episode) and maps (\~10% of episode) must **never** be sent to Wan 2.2 or LTX video diffusion (which hallucinates map labels and melts fine illustration ink work).  
2. **Deterministic 2.5D Presets (`video_prompt.parallax_preset`):** Every `STILL_25D` and `MAP_25D` shot must select one deterministic motion preset executed locally via `ComfyUI-Depthflow-Nodes` (or `explainer_engine/production/parallax.py`):  
   - `dolly_in` / `dolly_out`: Slow Z-axis depth push/pull across foreground/midground/background layers.  
   - `orbital_left` / `orbital_right`: Subtle 2.5D horizontal parallax arc around the focal subject.  
   - `pan_horizontal` / `pan_vertical`: Clean 2D/2.5D camera pan across battle lines or troop corridors on maps.  
   - `zoom_focus`: Targeted zoom into a specific city, treaty seal, or tactical chokepoint.

### Validation Checklist

- [ ] Every `composed_illustration` shot uses `generation_mode: "STILL_25D"` and a non-null `parallax_preset`.  
- [ ] Every `map_visualization` shot uses `generation_mode: "MAP_25D"`, `needs_end_frame: false`, and a non-null `parallax_preset`.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never ask video diffusion models to animate text labels, arrows, or map borders.

### What Gets Passed to the Local Engine

- `STILL_25D` and `MAP_25D` shots routed to `workflows/comfyui/depthflow_25d_motion.json` (or `explainer_engine/production/parallax.py`).

---

## Stage 11: Assembly & QA Guide

### Required Inputs

- Rendered Stage 3 video/2.5D clips, Stage 4 audio stems, and `production_script.json`.

### Mandatory Assembly & Gate Rules

1. **Frame Rate & Resolution Standard:** All clips are conformed to **24 fps** (`1280x720` or `1920x1080` upscale) before NLE concatenation in `explainer_engine/production/assemble.py`.  
2. **Editorial Transitions (`transition_out`):** Use `hard_cut` within continuous scenes, `j_cut` / `l_cut` across dialogue and segment bridges, and `cross_dissolve_8f` or `fade_to_black` only at phase boundaries (`Z1→Z2→Z3→Z4→Z5`).  
3. **Automated & Creator QA Checklist (`qa_report.json`):**  
   - **Continuity Check:** Do character uniforms, facial features, and screen directions match across adjacent shots?  
   - **Historical Fact-Check:** Are all pre-divergence claims cited in `research_dossier.md` and free of counterfactual bleed?  
   - **Technical Gate:** Zero frozen clips, zero silent gaps, and 100% duration alignment with `audio_spine`.

### What ChatGPT Must NOT Invent or Overcomplicate

- Never mark an episode `QA_PASSED` in planning output; `qa_report.json` is generated by `explainer_engine/production_gate.py` after local rendering and creator sign-off.

### What Gets Passed to the Local Engine

- `transition_out` and segment metadata consumed by `explainer_engine/production/assemble.py` and `explainer_engine/production_gate.py`.

---

## Stage 12: Canonical Output Package

When asked to produce a complete episode or pilot package, ChatGPT must output **strictly two artifacts**:

1. **`jobs/<episode_id>/01_script/research_dossier.md`**: The human-readable historical research dossier and citation ledger (Stage 2).  
2. **`jobs/<episode_id>/01_script/production_script.json`**: The single canonical machine-readable JSON file conforming to `explainer_engine/schemas/production_script.schema.json` (v4.0.0) containing the Episode Brief, World Bible, `Z1–Z5` Phases, `S01–S16` Segments, `audio_lines`, and `shots`.  
- **Zero Duplicate Files:** Never emit separate `shotlist.json`, `keyframes.json`, `video_prompts.json`, or `narration.txt` files that could drift out of sync with `production_script.json`.

````

---

## 5. Local ComfyUI Integration, `.env` Mapping, Model Registry & CLI (Phase 5)

### 5.1 Safe `.env` & Environment Variable Integration (`explainer_engine/vault.py`)
Codex must inspect and wire the following **environment variable names only** (never printing, logging, or committing secret values) inside [`explainer_engine/vault.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/vault.py):

| Variable Name | Currently Referenced In | Required Role in Rebuilt Architecture | Default Fallback (If Unset in `.env`) |
| :--- | :--- | :--- | :--- |
| `EXPLAINER_LOCAL_ONLY` | *(New guard in `vault.py`)* | Hard boolean lock blocking any outbound HTTP request to non-localhost inference APIs. | `"1"` (Strictly Local & Free by default) |
| `COMFY_SERVER_ADDRESS` | [`explainer_engine/production/__main__.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/__main__.py) | Primary local ComfyUI host:port address. | `"127.0.0.1:8188"` |
| `COMFYUI_API_ENDPOINT` | [`explainer_engine/imagegen/routing.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/imagegen/routing.py) | Full HTTP base URL for local ComfyUI API calls (`http://<COMFY_SERVER_ADDRESS>`). | `"http://127.0.0.1:8188"` |
| `COMFYUI_MODELS_DIR` | *(New path resolver in `vault.py`)* | Local filesystem path to ComfyUI `models/` directory so `local_preflight.py` can verify weight files exist before queueing jobs. | Resolved dynamically from ComfyUI `/system_stats` or local config path |
| `HF_TOKEN` / `HUGGING_FACE_HUB_TOKEN` | [`explainer_engine/vault.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/vault.py) | Used **only** for one-time local weight download helper (`scripts/check_or_pull_local_weights.py`), never for paid hosted inference. | Read via `os.environ.get()` without logging value |
| `EXPLAINER_ENGINE_ENV` | [`explainer_engine/production/__main__.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/__main__.py) | Execution profile (`"local_default"`, `"ci_dry_run"`, `"opt_in_cloud"`). | `"local_default"` |
| `SPEND_LIMIT_USD` / `PAID_PREFLIGHT_STRICT` / `COMFY_API_KEY` | [`explainer_engine/production/paid_preflight.py`](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/paid_preflight.py) | Ignored in default `local_default` mode; evaluated only if user explicitly passes `--allow-paid-cloud`. | `"0.00"` in default local mode |

### 5.2 Model & Workflow Registry (`config/local_models.json`)
Codex must create `config/local_models.json` to serve as the single local registry mapping abstract model roles to local file names, workflow templates, and licence notes:

```json
{
  "schema_version": "1.0.0",
  "local_only_default": true,
  "comfyui": {
    "default_url": "http://127.0.0.1:8188",
    "required_nodes": [
      "WanFunInpaintToVideo",
      "WanImageToVideo",
      "Wan22FunControlToVideo",
      "TextEncodeQwenImageEditPlus",
      "QwenMultiangleCameraNode"
    ],
    "optional_nodes": [
      "DepthflowPresetDolly",
      "DWPreprocessor",
      "CannyEdgePreprocessor",
      "DepthAnythingV2Preprocessor"
    ]
  },
  "active_defaults": {
    "stage2_image_model": "qwen_image_edit_2511",
    "stage2_fallback_image_model": "qwen_image_2_1_xworld_v2",
    "stage3_video_inp_model": "wan22_fun_5b_inp",
    "stage3_video_escalation_model": "wan22_fun_14b_inp",
    "stage3_video_control_model": "wan22_fun_5b_control",
    "stage3_parallax_engine": "depthflow_local_25d"
  },
  "models": {
    "qwen_image_2_1_xworld_v2": {
      "hf_repo": "Qwen/Qwen-Image-2.1",
      "checkpoint_file": "diffusion_models/qwen_image_2_1_bf16.safetensors",
      "lora_files": ["loras/xworld_v2.safetensors"],
      "workflow_json": "workflows/comfyui/qwen_keyframe_multiangle.json",
      "licence": "Apache-2.0 + Internal Vault LoRA",
      "licence_status": "commercial_ok"
    },
    "qwen_image_edit_2511": {
      "hf_repo": "Qwen/Qwen-Image-Edit-2511",
      "checkpoint_file": "diffusion_models/qwen_image_edit_2511_fp8_e4m3fn.safetensors",
      "lora_files": ["loras/qwen-image-edit-2511-multiple-angles-lora.safetensors"],
      "workflow_json": "workflows/comfyui/qwen_keyframe_multiangle.json",
      "licence": "Apache-2.0 (base) / fal.ai Multiple-Angles card terms",
      "licence_status": "verify_card"
    },
    "wan22_fun_5b_inp": {
      "hf_repo": "alibaba-pai/Wan2.2-Fun-5B-InP",
      "checkpoint_file": "diffusion_models/Wan2.2-Fun-5B-InP.safetensors",
      "vae_file": "vae/Wan2.2_VAE.safetensors",
      "text_encoder_file": "text_encoders/umt5_xxl_fp8_e4m3fn_scaled.safetensors",
      "workflow_json": "workflows/comfyui/wan22_fun_inp_flf2v.json",
      "licence": "Apache-2.0",
      "licence_status": "commercial_ok"
    },
    "wan22_fun_14b_inp": {
      "hf_repo": "alibaba-pai/Wan2.2-Fun-A14B-InP",
      "checkpoint_files": [
        "diffusion_models/wan2.2_fun_inp_high_noise_14B_fp8_scaled.safetensors",
        "diffusion_models/wan2.2_fun_inp_low_noise_14B_fp8_scaled.safetensors"
      ],
      "optional_accel_loras": [
        "loras/wan2.2_i2v_lightx2v_4steps_lora_v1_high_noise.safetensors",
        "loras/wan2.2_i2v_lightx2v_4steps_lora_v1_low_noise.safetensors"
      ],
      "workflow_json": "workflows/comfyui/wan22_fun_inp_flf2v.json",
      "licence": "Apache-2.0",
      "licence_status": "commercial_ok"
    },
    "wan22_fun_5b_control": {
      "hf_repo": "alibaba-pai/Wan2.2-Fun-5B-Control",
      "checkpoint_file": "diffusion_models/Wan2.2-Fun-5B-Control.safetensors",
      "workflow_json": "workflows/comfyui/wan22_fun_control.json",
      "licence": "Apache-2.0",
      "licence_status": "commercial_ok"
    },
    "depthflow_local_25d": {
      "hf_repo": "depth-anything/Depth-Anything-V2-Base",
      "checkpoint_file": "depthanything/depth_anything_v2_vitb_fp16.safetensors",
      "workflow_json": "workflows/comfyui/depthflow_25d_motion.json",
      "python_fallback_module": "explainer_engine.production.parallax",
      "licence": "Apache-2.0 (vitb)",
      "licence_status": "commercial_ok"
    }
  }
}
````

### 5.3 CLI Entrypoint Changes & Example Commands

Codex must update [explainer\_engine/production/\_\_main\_\_.py](https://github.com/vano1919/explainer-engine/blob/gemini/storytelling-system-rebuild-2026-11-09/explainer_engine/production/__main__.py) to support stage-isolated local execution:

```sh
# 1. Validate local ComfyUI endpoint, custom nodes, .env variables (names only), and local model files:
python -m explainer_engine.production --check-local --config config/local_models.json

# 2. Validate a canonical production_script.json (Stage 1 lints + schema v4.0 check, zero model inference):
python -m explainer_engine.production --script jobs/ep_waterloo_pilot/01_script/production_script.json --stage 1 --dry-run

# 3. Execute Stage 2 (2D Keyframe & Master Asset Generation via local ComfyUI Qwen):
python -m explainer_engine.production --script jobs/ep_waterloo_pilot/01_script/production_script.json --stage 2

# 4. Execute Stage 3 (Per-Shot Wan 2.2 Video & DepthFlow 2.5D Motion Generation on approved keyframes):
python -m explainer_engine.production --script jobs/ep_waterloo_pilot/01_script/production_script.json --stage 3

# 5. Execute Stage 4 (Audio Spine alignment, 24fps NLE assembly, and QA report generation):
python -m explainer_engine.production --script jobs/ep_waterloo_pilot/01_script/production_script.json --stage 4

# 6. Run the reproducible 60-second 12-shot Waterloo pilot benchmark (dry-run or live local ComfyUI):
python -m explainer_engine.production --pilot-60s --script tests/fixtures/pilot_60s_waterloo.json --dry-run
```

### 5.4 Dependency-Ordered Implementation TODO List for Codex

Codex must execute these 16 tasks in exact sequential order:

| TODO ID | Depends On | Target Files | What Changes & Why | Expected Result | Verification Test |
| :---- | :---- | :---- | :---- | :---- | :---- |
| **`TODO-01`** | None | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` | Append Decision `D-123` (Hybrid B → C Local Rebuild) superseding `D-116`, `D-120`, `D-121`, `D-122` and scoping `D-80`, `D-96`. | Ends decision ambiguity across docs and code. | `pytest tests/unit/test_docs_lint.py` |
| **`TODO-02`** | `TODO-01` | `explainer_engine/vault.py`, `config/local_models.json`, `config/model_routing.json` | Add `EXPLAINER_LOCAL_ONLY=1` default, local ComfyUI URL/path getters in `vault.py`, create `config/local_models.json`, and strip internal cloud URLs from `config/model_routing.json`. | Engine routes all image/video tasks locally by default without reading/printing secrets. | `pytest tests/unit/test_vault_local_only.py` |
| **`TODO-03`** | `TODO-02` | `explainer_engine/schemas/production_script.schema.json`, `shot_route.schema.json`, `wan_job.schema.json`, `keyframe_manifest.schema.json`, `render_telemetry.schema.json` | Upgrade `production_script.schema.json` to v4.0 (`Z1–Z5`, `S01–S16`, unified `world_bible`, `audio_lines`, `shots`); add `wan_job`, `keyframe_manifest`, and `render_telemetry` schemas. | Machine contracts match the 4-stage Hybrid B → C architecture. | `pytest tests/unit/test_schemas_v4.py` |
| **`TODO-04`** | `TODO-03` | `docs/MAIN_METHOD.md`, `CHATGPT.md`, `docs/CHATGPT_WORKFLOW.md` | Create `docs/MAIN_METHOD.md` with all 12 mandatory sections (Section 4\) and point `CHATGPT.md` and `docs/CHATGPT_WORKFLOW.md` to it. | ChatGPT has one unambiguous production manual aligned with schema v4.0. | `pytest tests/unit/test_docs_lint.py` |
| **`TODO-05`** | `TODO-04` | `docs/PROJECT_BRIEF.md`, `docs/STORY_ENGINE.md`, `docs/SCRIPT_ENGINE.md`, `docs/SCRIPTING_SPEC.md`, `explainer_engine/schemas/episode_rules.schema.json` | Reconcile Group A & Group C docs to 12-minute (`720s`) `Z1–Z5` / `S01–S16` structure, 70–80% narrator / 20–30% dialogue, and flexible 60/30/10 visual mix. | Zero contradictions between `PROJECT_BRIEF.md`, `STORY_ENGINE.md`, and `MAIN_METHOD.md`. | `pytest tests/unit/test_episode_rules.py` |
| **`TODO-06`** | `TODO-05` | `docs/SCENE_ASSETS.md`, `docs/SCENE_REUSE_RULES.md`, `docs/SHOT_PROMPTS.md`, `docs/VIDEO_GENERATION_WAN.md`, `docs/LOCAL_COMFYUI_SETUP.md` | Reconcile Group D, E, and F docs: replace Blender `.blend` \+ LTX `J5` docs with 2D anchor/multi-angle keyframes \+ Wan 2.2 Fun InP/I2V/Control \+ DepthFlow 2.5D. Archive `docs/pods/P12_LTX_FLAGS.md`. | Documentation matches the local Qwen \+ Wan \+ DepthFlow stack. | `pytest tests/unit/test_docs_lint.py` |
| **`TODO-07`** | `TODO-06` | `docs/EDITING.md`, `docs/ORCHESTRATION.md`, `docs/PRODUCTION_RULES.md`, `docs/CONTRACTS.md`, `docs/TOOL_STRATEGY.md`, `docs/CLOUD_RUNBOOK.md` | Reconcile Group G docs: update `ED-01..ED-15` for Wan/2.5D clips, replace `J1–J5` with the 5 canonical `generation_mode` values, and mark `CLOUD_RUNBOOK.md` opt-in only. | All operational docs align with the 4-stage local pipeline. | `pytest tests/unit/test_docs_lint.py` |
| **`TODO-08`** | `TODO-03` | `explainer_engine/scripting/shot_prompt_lint.py`, `scene_lint.py`, `story_lint.py` | Enforce `primary_action_count == 1`, `camera_move_count <= 1`, single control modality on `WAN_CONTROL`, `needs_end_frame` consistency, and `Z1–Z5` / `S01–S16` causal chain links. | Bad or over-conditioned prompts are rejected at Stage 1 before GPU execution. | `pytest tests/unit/test_shot_prompt_lint_v4.py` |
| **`TODO-09`** | `TODO-02`, `TODO-03` | `workflows/comfyui/qwen_keyframe_multiangle.json`, `explainer_engine/imagegen/routing.py`, `explainer_engine/imagegen/plan.py` | Create local ComfyUI Qwen workflow template and update `ShotRouter` to generate Stage 2 start frames (and conditional end frames for `WAN_FLF2V`) locally, recording approvals in `keyframe_manifest.json`. | Stage 2 generates and gates 2D keyframes locally without Blender or cloud endpoints. | `pytest tests/unit/test_stage2_keyframe_routing.py` |
| **`TODO-10`** | `TODO-03`, `TODO-09` | `workflows/comfyui/wan22_fun_inp_flf2v.json`, `workflows/comfyui/wan22_fun_control.json`, `workflows/comfyui/depthflow_25d_motion.json` | Create the three parameterized ComfyUI API workflow templates for Stage 3 (`WAN_I2V`/`WAN_FLF2V`, `WAN_CONTROL`, and `STILL_25D`/`MAP_25D`). | ComfyUI templates exist in Git (without weights) and validate node graph connections. | `pytest tests/unit/test_comfyui_workflow_templates.py` |
| **`TODO-11`** | `TODO-10` | `explainer_engine/aivideo/shotplan.py`, `explainer_engine/aivideo/wan_runner.py` | Implement `build_wan_payload()` and `WanLocalRunner` in `explainer_engine/aivideo/` dispatching Stage 3 jobs to `http://127.0.0.1:8188/prompt`, handling seed retries (`max_auto_retries=2`), selective `WAN_CONTROL` escalation, and `render_telemetry.jsonl` output. | Stage 3 executes per-shot video and 2.5D motion locally and logs empirical telemetry. | `pytest tests/unit/test_wan_shotplan_and_runner.py` |
| **`TODO-12`** | `TODO-02`, `TODO-11` | `explainer_engine/production/local_preflight.py`, `explainer_engine/production/paid_preflight.py` | Implement `local_preflight.py` verifying local-only mode, ComfyUI reachability, required nodes, local model files, and approved keyframes. Gate `paid_preflight.py` behind `--allow-paid-cloud`. | Default runs never contact cloud preflight or spend endpoints. | `pytest tests/unit/test_local_preflight.py` |
| **`TODO-13`** | `TODO-11`, `TODO-12` | `explainer_engine/production/__main__.py`, `explainer_engine/production/assemble.py`, `explainer_engine/production_gate.py` | Wire the 4-stage pipeline (`--stage 1..4`, `--check-local`, `--pilot-60s`) in `__main__.py` and update `production_gate.py` to enforce keyframe approval before Stage 3 and audio-spine duration conformance at 24fps in Stage 4\. | End-to-end 4-stage CLI works in both `--dry-run` and live local ComfyUI modes. | `pytest tests/unit/test_production_pipeline_e2e_dryrun.py` |
| **`TODO-14`** | `TODO-09`, `TODO-13` | `explainer_engine/blender/__init__.py`, `.github/workflows/blender-smoke.yml`, `crowd-proof.yml`, `world-kits.yml` | Mark 3D layout/grease-pencil Blender modules as deprecated legacy tools (retaining `assemble_25d.py` for 2.5D plane fallback) and set legacy Blender CI workflows to manual `workflow_dispatch` only. | Eliminates mandatory Blender 3D overhead from default CI and production runs. | `pytest tests/unit/test_legacy_deprecation_guards.py` |
| **`TODO-15`** | `TODO-11` | `scripts/run_phase1_ablations.py` | Implement the local Phase 1 compatibility & ablation test runner (`T-ABL-01` through `T-ABL-04`) to measure `Qwen-2.1` vs `2511`, `xworld_v2`, `5B` vs `14B`, and `LightX2V` 4-step vs unaccelerated. | Provides empirical local data before locking model switches. | `pytest tests/unit/test_ablation_runner_dryrun.py` |
| **`TODO-16`** | `TODO-13`, `TODO-15` | `tests/fixtures/pilot_60s_waterloo.json`, `scripts/migrate_film_shots_2_to_3.py` \-\> `scripts/migrate_script_to_v4.py` | Create the complete 12-shot 60-second Waterloo pilot fixture (`tests/fixtures/pilot_60s_waterloo.json`) and a migration utility upgrading v2/v3 shot specs to `production_script.schema.json` v4.0. | Reproducible 60-second benchmark is ready for immediate dry-run and live ComfyUI execution. | `pytest tests/unit/test_pilot_60s_fixture.py` |

### 5.5 Unit, Schema, Dry-Run & Local Smoke Test Suite

Codex must ensure `pytest tests/unit/` runs in `< 10 seconds` offline (without requiring a running GPU or ComfyUI process) while providing an opt-in `--run-local-comfy` flag for live smoke tests:

1. **`tests/unit/test_vault_local_only.py`:** Asserts `is_local_only()` defaults to `True`, blocks any URL not matching `127.0.0.1` or `localhost`, and verifies `vault.py` never prints or logs secret values from `.env`.  
2. **`tests/unit/test_schemas_v4.py`:** Validates `tests/fixtures/pilot_60s_waterloo.json` against `production_script.schema.json` v4.0, and verifies rejection of invalid payloads (e.g., `primary_action_count > 1`, `camera_move_count > 1`, `WAN_FLF2V` with `needs_end_frame: false`, or `WAN_CONTROL` with multiple control modalities).  
3. **`tests/unit/test_shot_prompt_lint_v4.py`:** Tests `shot_prompt_lint.py` against over-conditioned prompts, missing `style_anchor_token`, spoken dialogue leaked into `video_prompt`, and broken `cause_from_segment_id` links.  
4. **`tests/unit/test_wan_shotplan_and_runner.py`:** Mocks `http://127.0.0.1:8188/prompt` and `/history` to verify `WanLocalRunner` constructs valid node graphs for `WAN_I2V` (1 image), `WAN_FLF2V` (2 images), `WAN_CONTROL` (1 image \+ 1 control), and `STILL_25D`/`MAP_25D` (DepthFlow), retries up to 2 times on simulated QA failure, and writes valid `render_telemetry.jsonl` rows.  
5. **`tests/unit/test_production_pipeline_e2e_dryrun.py`:** Runs `python -m explainer_engine.production --pilot-60s --script tests/fixtures/pilot_60s_waterloo.json --dry-run` across all 4 stages and verifies folder creation (`01_script/`, `02_keyframes/`, `03_video/`, `04_assembly/`) and manifest generation.

---

## 6\. Reproducible 60-Second Pilot & Validation Plan (Phase 6\)

### 6.1 Pilot Story & Parameters (`tests/fixtures/pilot_60s_waterloo.json`)

The controlled 60-second pilot tests Segment `S04` (*The Point of Divergence: June 18, 1815 — Waterloo, 11:30 AM to 4:00 PM*) using **2 recurring characters** (`char_napoleon_1815` and `char_grouchy_1815`), **2 recurring locations** (`loc_caillou_command_tent` and `loc_wavre_crossroads_mud`), **1 recurring prop** (`prop_brass_spyglass`), and **12 shots totaling 60.0 seconds** matching the exact 60% / 30% / 10% visual mix:

- **7 Cinematic Video Shots (`35.0 seconds`, 58.3%):** 4 `WAN_I2V` shots (`20.0s`) \+ 3 `WAN_FLF2V` start/end bridged shots (`15.0s`), with 2 difficult action shots (`S04_SH006`, `S04_SH009`) designated for head-to-head comparison against the **Secondary Selective Workflow (`WAN_CONTROL`)**.  
- **4 Composed Illustration Shots (`20.0 seconds`, 33.3%):** 4 `STILL_25D` shots animated locally via deterministic DepthFlow 2.5D parallax.  
- **1 Map Visualization Shot (`5.0 seconds`, 8.3%):** 1 `MAP_25D` shot animated locally via deterministic 2.5D pan/zoom.  
- **Spoken Balance:** `45.0 seconds` Narrator Voiceover (`75.0%`) / `15.0 seconds` Character Dialogue (`25.0%`, covering 3 exchanges between Napoleon and Grouchy/Aide).

### 6.2 Exact 12-Shot Pilot Breakdown (`S04_SH001` – `S04_SH012`)

| Shot ID | Dur (s) | Visual Type | Primary Mode | Secondary Test Mode | Narrative & Coverage Beat | Start / End Frame & Control Plan | Audio Spine Line (`Speaker` / `Duration`) |
| :---- | :---- | :---- | :---- | :---- | :---- | :---- | :---- |
| **`S04_SH001`** | `5.0s` | `composed_illustration` | `STILL_25D` | *(Same)* | **Establishing Shot:** Rain-swept ridge of Mont-Saint-Jean at dawn; Anglo-Allied redcoats formed along the crest. | 1 Still (`new_master_anchor`) \+ `parallax_preset: "dolly_in"` | `S04_L001` (`narrator`, `5.0s`): *"Dawn, June eighteenth, eighteen-fifteen. Across the sodden ridge of Mont-Saint-Jean, Wellington's line waits."* |
| **`S04_SH002`** | `5.0s` | `map_visualization` | `MAP_25D` | *(Same)* | **Strategic Map:** 1815 campaign map of Belgium showing Waterloo, Wavre, and the 15-mile gap between Napoleon, Wellington, and Blücher. | 1 Map Still (`new_master_anchor`) \+ `parallax_preset: "zoom_focus"` | `S04_L002` (`narrator`, `5.0s`): *"Fifteen miles east at Wavre, Marshal Grouchy holds thirty thousand French troops—the hinge of fate."* |
| **`S04_SH003`** | `5.0s` | `cinematic_video` | `WAN_I2V` | *(Baseline only)* | **Character Intro:** Grouchy on horseback at the muddy Wavre crossroads as distant cannon fire rumbles on the western horizon; cloak ripples in wind. | Start Frame (`new_master_anchor`), `needs_end_frame: false` | `S04_L003` (`narrator`, `5.0s`): *"In real history, Grouchy marched east into emptiness. Here, the first cannonade stops him cold."* |
| **`S04_SH004`** | `5.0s` | `cinematic_video` | `WAN_FLF2V` | *(Baseline only)* | **Two-Character Interaction:** General Gérard rides up beside Grouchy and points urgently west toward the smoke of Waterloo; Grouchy turns head west. | Start Frame \+ End Frame (`multiangle_from_anchor`, `azimuth: 45`), bridged pose | `S04_L004` (`character: char_gerard`, `5.0s`, OTS framing, `requires_visible_lipsync: false`): *"Marshal\! That is the Emperor's grand battery at Mont-Saint-Jean—we must march to the sound of the guns\!"* |
| **`S04_SH005`** | `5.0s` | `cinematic_video` | `WAN_I2V` | *(Baseline only)* | **Dialogue Coverage (Reverse OTS):** Close medium shot over Gérard's shoulder onto Grouchy's weathered face; Grouchy lowers his reins in decisive resolve. | Start Frame (`multiangle_from_anchor`, `azimuth: 225`), `needs_end_frame: false` | `S04_L005` (`character: char_grouchy_1815`, `5.0s`, `requires_visible_lipsync: true` test candidate): *"Wheel the vanguard west toward Chapelle-Saint-Lambert. We seal the Prussian flank before noon."* |
| **`S04_SH006`** | `5.0s` | `cinematic_video` | `WAN_FLF2V` | **`WAN_CONTROL` (`openpose` / `trajectory`)** | **Action Cause:** Grouchy's cavalry column wheels sharply left across the sunken mud road and surges west through splashing water. | Primary: Start \+ End Frame. Secondary Test: Start Frame \+ 1 control pass (`openpose`/`depth`). | `S04_L006` (`narrator`, `5.0s`): *"By turning west at eleven-thirty, Grouchy's corps seizes the Lasne river bridges two hours ahead of Blücher."* |
| **`S04_SH007`** | `5.0s` | `composed_illustration` | `STILL_25D` | *(Same)* | **Action Result Tableau:** Wide Ink Chronicle illustration of French dragoons and artillery blocking the narrow Lasne river wooden bridge against Prussian scouts. | 1 Still (`new_master_anchor`) \+ `parallax_preset: "pan_horizontal"` | `S04_L007` (`narrator`, `5.0s`): *"Trapped in the muddy defiles of the Lasne, thirty thousand Prussians are pinned five miles from Wellington's left."* |
| **`S04_SH008`** | `5.0s` | `cinematic_video` | `WAN_FLF2V` | *(Baseline only)* | **Transition to Napoleon's HQ:** At La Belle Alliance, Napoleon lowers `prop_brass_spyglass` from his eye toward the empty eastern woods, a fierce smile forming. | Start Frame (spyglass raised) \+ End Frame (spyglass lowered), `azimuth: 315` | `S04_L008` (`narrator`, `5.0s`): *"At La Belle Alliance, Napoleon scans the eastern treeline—and sees French tricolors holding the flank."* |
| **`S04_SH009`** | `5.0s` | `cinematic_video` | `WAN_I2V` | **`WAN_CONTROL` (`openpose` / `camera_preset`)** | **Climactic Command:** Napoleon steps forward beside the campaign table and extends his gloved hand toward Wellington's center ridge as aides salute. | Primary: Start Frame (`multiangle_from_anchor`, `azimuth: 0`). Secondary Test: Start Frame \+ `openpose`. | `S04_L009` (`character: char_napoleon_1815`, `5.0s`, `requires_visible_lipsync: false`): *"Blücher is caged. Send the Old Guard straight up the ridge—all reserves forward\!"* |
| **`S04_SH010`** | `5.0s` | `composed_illustration` | `STILL_25D` | *(Same)* | **Escalation Panorama:** Towering Ink Chronicle illustration of the Imperial Guard advancing in dense bearskin columns through drifting cannon smoke up Mont-Saint-Jean. | 1 Still (`new_master_anchor`) \+ `parallax_preset: "dolly_in"` | `S04_L010` (`narrator`, `5.0s`): *"Unbroken by Prussian flank attacks, ten thousand fresh Imperial Guardsmen surge up the center slope at four o'clock."* |
| **`S04_SH011`** | `5.0s` | `cinematic_video` | `WAN_I2V` | *(Baseline only)* | **Consequence:** French Imperial Eagle standard (`prop_imperial_eagle_standard`) planted on the shattered Allied breastworks as redcoats retreat into the smoke. | Start Frame (`new_master_anchor`), `needs_end_frame: false` | `S04_L011` (`narrator`, `5.0s`): *"Without Prussian relief, Wellington's exhausted center fractures along the Ohain road."* |
| **`S04_SH012`** | `5.0s` | `composed_illustration` | `STILL_25D` | *(Same)* | **Concluding Shot:** Dusk over the silent Waterloo battlefield; Napoleon's silhouette on horseback overlooking the ridge as rain clears. | 1 Still (`multiangle_from_anchor` of `loc_waterloo_ridge`) \+ `parallax_preset: "dolly_out"` | `S04_L012` (`narrator`, `5.0s`): *"By nightfall, the road to Brussels lies open—and the Seventh Coalition faces sudden collapse."* |

### 6.3 Pilot Scoring Rubric & Required Empirical Measurements

Codex must distinguish strictly between **Code/Dry-Run Verification** (which Codex executes automatically via `pytest`) and **Live Local Model Execution** (which requires a running local ComfyUI instance with downloaded weights and must never be faked by dry-run tests). When the live local pilot runs, `scripts/evaluate_pilot_60s.py` must log and score both workflows across 7 dimensions (`1–5` scale, minimum passing bar `4.0` average, no individual criterion `< 3.0`):

1. **Story & Cause/Effect Continuity (Weight 20%):** Does every shot visually follow from the prior cause (`S04_SH001 → S04_SH012`) without jarring spatial jumps?  
2. **Character Identity Across Shots (Weight 20%):** Do `char_napoleon_1815` and `char_grouchy_1815` retain identical facial geometry, uniform colors, and Ink Chronicle linework across angles (`0°`, `45°`, `225°`, `315°`)?  
3. **Location & Prop Continuity (Weight 15%):** Do `loc_wavre_crossroads_mud`, `loc_waterloo_ridge`, and `prop_brass_spyglass` remain consistent across cuts?  
4. **Action Accuracy (Weight 15%):** Did the model execute the single specified action (especially on `S04_SH006` cavalry wheel and `S04_SH009` command gesture)?  
5. **Camera & Composition Compliance (Weight 10%):** Did the shot respect the requested `shot_size`, `vertical_angle`, `horizontal_azimuth_deg`, and 180-degree screen direction axis?  
6. **Accepted Generation Rate & Retries (Weight 10%):** Measured directly from `render_telemetry.jsonl`: $\text{Yield} = \frac{12}{\text{Total Dispatched Jobs}}$ (Target: $\leq 1.4$ jobs per accepted shot).  
7. **Total Local Runtime & Manual Effort (Weight 10%):** Measured wall-clock seconds per accepted shot and number of manual 2D keyframe edits required.

---

## 7\. Phase-by-Phase Acceptance Criteria, Risks & Rollback Path

### 7.1 Acceptance Criteria by Implementation Phase

- **Phase A (Config, Vault & Schemas — `TODO-01..03`):**  
  - `EXPLAINER_LOCAL_ONLY` defaults to `"1"`; zero outbound cloud URLs remain in `config/model_routing.json`; `production_script.schema.json` v4.0, `wan_job.schema.json`, `keyframe_manifest.schema.json`, and `render_telemetry.schema.json` pass JSON Schema Draft 2020-12 meta-validation.  
- **Phase B (Documentation & `MAIN_METHOD.md` — `TODO-04..07`):**  
  - `docs/MAIN_METHOD.md` exists and passes `explainer_engine/docs_lint.py`; zero active docs reference `5–11 minutes (7-minute target)`, mandatory `.blend` grease-pencil files, or `J5` 3-keyframe LTX as default.  
- **Phase C (Local Engine & Workflow Templates — `TODO-08..14`):**  
  - All 4 ComfyUI JSON templates exist under `workflows/comfyui/`; `shot_prompt_lint.py` rejects multi-action or multi-control shots; `local_preflight.py` replaces `paid_preflight.py` in `__main__.py`; legacy Blender CI workflows are switched to manual dispatch.  
- **Phase D (Ablation Harness & 60s Pilot Fixture — `TODO-15..16`):**  
  - `pytest tests/unit/` passes 100% offline; `python -m explainer_engine.production --pilot-60s --script tests/fixtures/pilot_60s_waterloo.json --dry-run` completes all 4 stages cleanly and emits valid dry-run manifests.

### 7.2 Key Risks, Mitigations & Rollback Path

| Risk / Blocker | Detection Mechanism | Mitigation & Local Fallback Path |
| :---- | :---- | :---- |
| **`Qwen-Image-Edit-2511` \+ `xworld_v2` LoRA incompatibility or excessive local runtime** | `T-ABL-01` in `scripts/run_phase1_ablations.py` | Automatically fall back to `qwen_image_2_1_xworld_v2` for master anchor creation and use `Qwen-Image-Edit-2511` (without `xworld_v2`, inheriting style from the reference anchor) only when multi-angle rotation is needed, OR stay 100% on `Qwen-Image-2.1` (`active_defaults.stage2_image_model`). |
| **`Wan2.2-Fun-5B-InP` insufficient motion quality on complex action shots** | Pilot scoring rubric (`< 4.0` on `S04_SH006` / `S04_SH009`) | Escalate only the failing shot to `wan22_fun_5b_control` (single `openpose` or `depth` pass) first; if still below bar, switch `active_defaults.stage3_video_inp_model` in `config/local_models.json` to `wan22_fun_14b_inp` (FP8/GGUF). |
| **4-step `LightX2V` acceleration LoRA flattens motion dynamics** | `T-ABL-03` motion amplitude check (`frozen_frame_ratio` in `render_telemetry.jsonl`) | Keep `use_lightx2v_4step: false` (unaccelerated 20-step inference) for dramatic hero shots and enable `use_lightx2v_4step: true` only on subtle atmospheric `WAN_I2V` shots. |
| **`ComfyUI-Depthflow-Nodes` missing or OpenGL shader issue on headless local host** | `local_preflight.py` check on `GET /object_info` | Automatically route `STILL_25D` and `MAP_25D` shots to `explainer_engine/production/parallax.py` (CPU/PyTorch deterministic 2.5D plane projection), guaranteeing zero blockage. |
| **Rollback Path if Full Migration Needs Reversion** | Git branch isolation & schema versioning | Legacy `ltx_job.schema.json`, `paid_preflight.py`, and `explainer_engine/blender/` files remain preserved on disk behind explicit opt-in flags (`--allow-paid-cloud`, `WAN_FALLBACK_LTX`) until the live 60-second pilot passes creator sign-off. |

&nbsp;