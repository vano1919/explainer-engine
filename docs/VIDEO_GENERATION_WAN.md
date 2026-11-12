# Local Video & 2.5D Motion Generation Guide (`VIDEO_GENERATION_WAN.md`)

> **Legacy for a v4.3 episode (D-131, 2026-11-12; final audit C1).** The local ComfyUI Wan route and the DepthFlow 2.5D
> motion on this page are not the v4.3 method. A v4.3 `wan` shot is made by `aivideo/wan_adapter.ModalWanBackend` and the
> worker `training/pods/wan/modal_wan_jobs.py` (OR-37 ladder L0..L4, the one ledger `core/ledger.Run`); a `still_25d` shot by
> `production/layers25d`; the routes are in `docs/EPISODE_FIRST.md` (RT rows). Local ComfyUI stays the creator's free option
> (`ComfyWanBackend`), never the route. The numbers below (81 frames, 1280x720, the frame[-5] chain) are notes for the v4.3
> model pin (final audit A2), not settings. The page stays readable for the episodes made before 2026-11-12.

> **Route-scoped since D-116 (2026-11-06); created 2026-11-09 by D-123 (Local Hybrid B -> C Rebuild).**
> **Canonical Job Schema:** `explainer_engine/schemas/wan_job.schema.json`
> **Local Dispatcher:** `explainer_engine/aivideo/wan_runner.py` & `explainer_engine/aivideo/shotplan.py`

## 1. Architecture Overview (Stage 3 Motion)

Stage 3 converts approved Stage 2 2D keyframes (`02_keyframes/keyframe_manifest.json`) into 24fps motion clips (`03_video/clips/`) using **100% local ComfyUI workflows** (`http://127.0.0.1:8188`, `EXPLAINER_LOCAL_ONLY=1`). Legacy multi-keyframe LTX (`J5` with 3 keyframes) is retired from the default path (`D-123`) and archived in `docs/archive/P12_LTX_FLAGS_2026-11-08.md`.

Every shot in `production_script.json` (`v4.0.0`) selects exactly one of five local `generation_mode` routes:

| `generation_mode` | Visual Type | Local Engine & Workflow Template | Keyframe & Conditioning Inputs |
| :--- | :--- | :--- | :--- |
| **`WAN_I2V`** | `cinematic_video` | `Wan2.2-Fun-5B-InP` (or `14B-InP` escalation) via `workflows/comfyui/wan22_fun_inp_flf2v.json` | Approved `start_image` (`needs_end_frame: false`) + `motion_prompt` |
| **`WAN_FLF2V`** | `cinematic_video` | `Wan2.2-Fun-5B-InP` (or `14B-InP` escalation) via `workflows/comfyui/wan22_fun_inp_flf2v.json` | Approved `start_image` + Approved `end_image` (`needs_end_frame: true`) + `motion_prompt` |
| **`WAN_CONTROL`** | `cinematic_video` *(Selective Fallback)* | `Wan2.2-Fun-5B-Control` (or `14B-Control`) via `workflows/comfyui/wan22_fun_control.json` | Approved `start_image` + `motion_prompt` + **EXACTLY ONE** `selective_control` modality (`openpose`, `depth`, `canny`, or `camera_preset`) |
| **`STILL_25D`** | `composed_illustration` | `Depth-Anything-V2-Base` + `ComfyUI-Depthflow-Nodes` via `workflows/comfyui/depthflow_25d_motion.json` (fallback: `explainer_engine/production/parallax.py`) | Approved illustration still + deterministic `parallax_preset` (`dolly_in`, `dolly_out`, `orbital_left`, `orbital_right`, `pan_horizontal`, `pan_vertical`, `zoom_focus`) |
| **`MAP_25D`** | `map_visualization` | `Depth-Anything-V2-Base` + `ComfyUI-Depthflow-Nodes` via `workflows/comfyui/depthflow_25d_motion.json` (fallback: `explainer_engine/production/parallax.py`) | Approved map plate (`needs_end_frame: false`) + deterministic `parallax_preset` |

---

## 2. Primary Video Workflow (`WAN_I2V` & `WAN_FLF2V`)

1. **Default Clip Parameters:**
   - Resolution: `1280x720` (or `832x480` fast draft tier).
   - Frame Count & Rate: `81` frames conformed to **24 fps** (`~5.0s` nominal shot window, D-85).
   - Model Tier Selection: Test `wan22_fun_5b_inp` (`Wan2.2-Fun-5B-InP.safetensors`) first; escalate to `wan22_fun_14b_inp` only if a complex shot scores below `4.0/5.0` on the pilot rubric.
2. **Step-Distillation (`use_lightx2v_4step`):**
   - Controlled by `T-ABL-03` in `scripts/run_phase1_ablations.py`. Keep `use_lightx2v_4step: false` (unaccelerated 20-step inference, `cfg_scale: 5.0`) for hero action shots if 4-step `LightX2V` dampens motion amplitude.
3. **Anti-Overconditioning Guardrails (Enforced by `shot_prompt_lint.py`):**
   - `primary_action_count == 1`: Exactly one primary physical action per shot.
   - `camera_move_count <= 1`: At most one camera movement per shot.
   - Zero spoken dialogue strings or text banners inside `video_prompt.motion_prompt`.

---

## 3. Selective Secondary Control Workflow (`WAN_CONTROL`)

- **When Invoked:** Only when a `WAN_I2V` or `WAN_FLF2V` shot fails automated QA (`explainer_engine/production_gate.py`) after `max_auto_retries = 2` seed increments (`seed + 1001`) due to action choreography or camera path errors.
- **Single-Modality Rule:** `selective_control` must specify **only one** control signal (`openpose`, `depth`, `canny`, `camera_preset`, or opt-in experimental `trajectory_ati_experimental`) with `control_strength` in `[0.1, 1.0]` (default `0.75`) and a written `escalation_reason`. Never stack multiple control passes simultaneously.

---

## 4. Deterministic 2.5D Motion for Stills & Maps (`STILL_25D` & `MAP_25D`)

- Composed historical illustrations (~30%) and maps (~10%) bypass video diffusion completely (`0` diffusion retries) so map labels and fine Ink Chronicle linework never melt or hallucinate.
- Executed locally via `workflows/comfyui/depthflow_25d_motion.json` (`Depth-Anything-V2-Base` Apache-2.0 checkpoint + `ComfyUI-Depthflow-Nodes`), or automatically routed to `explainer_engine/production/parallax.py` if DepthFlow nodes are absent on a headless host.

---

## 5. Telemetry & QA Gate

Every Stage 3 dispatch appends a validated JSON record to `jobs/<episode_id>/03_video/render_telemetry.jsonl` (`explainer_engine/schemas/render_telemetry.schema.json`) capturing `wall_clock_seconds`, `peak_vram_mb`, `attempt_number`, `status`, and `qa_metrics` (`duration_match`, `frozen_frame_ratio`, `boundary_jump_score`).

## Continuous Shot Chaining via `frame[-5]` (`WAN-CHAIN-MINUS-5`, D-124)
When a continuous visual action must span more than one Wan 2.2 clip (`> 4–5 seconds`):
1. **Frame Extraction (`extract_continuation_frame_minus_5`):** Extract the **5th frame from the end (`frame[-5]`, 0-based index `N - 5`)** of Clip A rather than the very last frame (`frame[-1]`), because the final 3–4 frames of video diffusion clips experience temporal deceleration and boundary softening.
2. **Next Clip Generation:** Pass `frame[-5]` of Clip A as the `start_frame` input to Wan 2.2 for Clip B.
3. **Seamless Assembly Splice (`build_seamless_continuation_edl` in `chunked_edit.py`):** During Gate `G8` assembly, trim the trailing 5 frames of Clip A (`play_frames = N - 5`) so Clip A's last played frame (`frame[-6]`) hands off directly onto Clip B's `frame[0]` (`= Clip A's frame[-5]`) with zero duplicate frames and uninterrupted motion velocity.
