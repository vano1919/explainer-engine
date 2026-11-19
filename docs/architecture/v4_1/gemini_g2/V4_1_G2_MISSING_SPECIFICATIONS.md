# Explainer Engine V4.1 — G2 Missing Specifications (`MA-03`)

- **Base Commit:** `e4521cd` (PR #196, CI `4476 passed, 24 skipped, 3 deselected, 1 xfailed, 0 failed`)
- **Local Snapshot Code SHA:** `eb80e4434ea120f48cb9aea094ebd7b2b423d8f0`
- **Precedence:** Decision Log -> `DEC-2026-11-17-01` & PR #195 -> `PLAN_AMENDMENTS_v1_1.md` -> V4.1 as amended by `MA-01..MA-18`
- **Status:** G2 Contract Deliverable (zero Step 1 code changes, `$0.00` spend)

---

## 1. Adaptive Video Inspection Router (`inspection_plan/1`)

### 1.1 Core Principle: Deterministic-First Gate
Every generated or ingested clip MUST pass **Tier 0 (Deterministic)** before any paid VLM or multimodal call is permitted. A Tier 0 `BLOCKER` finding halts progression immediately on its own (`deterministic_block_can_halt: true`) without spending on VLM tiers.

### 1.2 Tier Selection Rules

| Tier | Name | Trigger Condition | Tools / Signals Run | Can Block Alone? | Est. Cost / Clip (USD) |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `T0_DETERMINISTIC_ONLY` | Deterministic Baseline | Runs unconditionally on 100% of clips. Sufficient to pass only for static/simple transitions with zero anomalies and verified start-frame SSIM. | `ffprobe` (`media_clocks/1`), start-frame comparison (`compare_ltx_first_frame_to_source`), black/frozen frame check, audio voicing/trim (`audio_evidence/1`), `av_event_timeline/1` bounds | **Yes** | `$0.000` |
| `T1_KEYFRAME_VLM` | Keyframe Visual Check | Default post-T0 visual verification for standard shots (first/middle/last keyframes) when T0 passes with no blockers. | 3-frame VLM inspection (`observed_video/1` keyframe pass) | Yes (advisory until calibrated per Spec 4) | `$0.002 – $0.005` |
| `T2_MOTION_DENSE_VLM` | Motion-Dense Inspection | Triggered when shot has fast camera/subject action, continuation boundary (`is_continuation: true`), start-frame SSIM in warning band (`0.72 <= ssim < 0.85`), or speech/lip-sync risk. | 1–2 fps sampled clip inspection + optical-flow/motion check | Yes (advisory until calibrated per Spec 4) | `$0.010 – $0.025` |
| `T3_ESCALATED_FULL_REVIEW` | Escalated Full-Clip Review | Triggered on retry attempt >= 2, hero close-up with T1/T2 `REVIEW`, or cross-vendor disagreement. Requires remaining episode spend-cap headroom. | Full-clip multimodal VLM + cross-vendor critic comparison + human `REVIEW` packet | Escalates to `FAIL` or `REVIEW` | `$0.030 – $0.060` |

### 1.3 Fail-Closed & Budget Guardrails
1. If any required perception input (frames, probe metadata, or evaluator response) is missing, emit `overall_verdict: "NO_PERCEPTION_INPUT"` (or `"REVIEW"` for missing `start_frame_check` inspection data per `PLAN_AMENDMENTS_v1_1.md` §0.3) — **never** `"PASS"`.
2. Before dispatching `T1`–`T3`, check `config/spend_caps.json`. If remaining cap is insufficient, halt escalation and emit `REVIEW` with `budget_cap_reached`.
3. `inspection_plan/1` is emitted per clip prior to evaluator execution and persisted alongside `observed_video/1`.

---

## 2. `media_clocks` Boundary API (`media_clocks/1`)

### 2.1 Strict Scope Boundary
- **Episode Clock (Unchanged):** Remains integer frames on the episode FPS grid inside `explainer_engine/episode/timing.py` (`episode_timing/1`, `retime_with_edit_points`, `frame_to_sample`).
- **`media_clocks/1` Scope:** Strictly confined to the **probe / ingest / mux boundary** (`explainer_engine/videolane/ingest.py:probe` and mux verification in `stage_assemble`). It does NOT replace integer episode frames.

### 2.2 Probe Extraction Contract (`ffprobe`)
`probe_media_clocks(path: Path) -> dict` wraps `ffprobe -v error -show_streams -show_format -print_format json` and returns a `media_clocks/1` record:
- `clip_sha256`: SHA-256 of the probed file.
- `probe_tool`: `"ffprobe"`.
- `video_stream`:
  - `timebase_num`, `timebase_den` (exact rational from `time_base`, e.g., `1/12800`)
  - `start_pts` (integer in stream timebase units)
  - `frame_count` (exact integer from `nb_frames` or counted packet fallback)
  - `fps_num`, `fps_den` (exact rational from `r_frame_rate` / `avg_frame_rate`)
  - `is_vfr` (boolean: `True` when `abs(r_frame_rate - avg_frame_rate) > 0.01`)
- `audio_stream` (or `null` for silent video-only containers):
  - `timebase_num`, `timebase_den`
  - `start_pts`
  - `sample_rate_hz` (integer, e.g., `48000`)
  - `sample_count` (exact integer)
  - `initial_padding_samples` (integer >= 0; captures AAC/Opus encoder priming delay)
- `edit_list_offset_s` (float; signed offset derived from MP4 `elst` atom or stream `start_time` delta between video and audio).

### 2.3 Boundary Invariants & Conversions
1. **VFR Rejection:** If `video_stream.is_vfr == True`, ingest MUST flag a `BLOCKER` or normalize to CFR before frame-accurate cutting (`cut()`).
2. **Sync Offset Check:** At mux verification, `abs(audio_start_s - video_start_s)` exceeding `1 / (2 * episode_fps)` (half a frame, `~20.8 ms` at 24 fps) fails deterministic sync verification.
3. **Conversion Helpers:**
   - `pts_to_seconds(pts: int, num: int, den: int) -> Fraction` (exact `fractions.Fraction`, converted to float only at FFmpeg CLI boundary).
   - `seconds_to_episode_frame(t_s: Fraction, fps_num: int, fps_den: int) -> int` (half-even rounding with explicit drift logging).

---

## 3. Intentional Cut-on-Action Rules (`cut_decision/1`)

### 3.1 Integration Points (Additive on Existing Pipeline)
- **Producer:** Extends `explainer_engine/videolane/ingest.py` (`edit_points` / `whisper_edit_points` / `build_trim_contract`) to emit a `cut_decision/1` record for every trimmed clip.
- **Consumer:** Feeds `explainer_engine/episode/timing.py:retime_with_edit_points` so cut frames propagate cleanly into the authoritative episode timing spine without mutating raw clip archives.

### 3.2 Decision & Allowability Matrix

| `reason_code` | Allowed? | Required Preconditions |
| :--- | :--- | :--- |
| `INTENTIONAL_CUT_ON_ACTION` | `true` | Motion energy peaks within `[out_frame - 3, out_frame + 1]` AND no active speech word crosses `out_frame` (`audio_evidence/1` confirms zero phonetic overlap). |
| `CLEAN_BEAT_BOUNDARY` | `true` | Cut lands in silence / inter-word gap (`>= 0.12 s` from nearest voiced word boundary) AND `out_frame > in_frame`. |
| `REACTION_TAIL_HOLD` | `true` | Post-speech visual reaction tail preserved via `resolve_reaction_tail_s` with `mute_tail_from_s` applied where tail audio contains unintended noise/speech. |
| `MID_WORD_PHONETIC_CUT` | **`false` (enforced by schema `if/then`)** | Cut intersects an active voiced word span. Hard blocked; trim point must shift to word boundary or trigger clip retry. |
| `ACCIDENTAL_UNRESOLVED_MOTION` | **`false` (enforced by schema `if/then`)** | Unintended mid-gesture/camera-whip cut with neither action-match target nor clean beat boundary. Hard blocked. |

### 3.3 Semantic Validator Invariants
- `out_frame > in_frame` (enforced in Python semantic validator; schema enforces `in_frame >= 0`, `out_frame >= 1`).
- `out_frame <= media_clocks.video_stream.frame_count` when `media_clocks/1` is present.

---

## 4. Cross-Vendor Critic Specification

### 4.1 Vendor Independence Tracking
Every perceptual evaluation record (`observed_image/1` and `observed_video/1`) MUST record:
- `generator_vendor` (e.g., `"google_imagen"`, `"ltx_video"`, `"qwen_image"`, `"blender_cycles"`)
- `evaluator_vendor` (e.g., `"anthropic_claude"`, `"google_gemini"`, `"openai_gpt"`, `"deterministic_local"`)

When `generator_vendor == evaluator_vendor` (same-family self-critique), the evaluation is marked `same_vendor_warning: true` in logs and cannot silently override a deterministic failure.

### 4.2 Advisory-Until-Calibrated Rule (`MA-03`)
- A cross-vendor VLM critic starts in **advisory mode** (`advisory_only: true`, findings capped at `REVIEW` / `MAJOR`, never hard-blocking production on its own) **until** at least **1 recorded calibration call per capability** (image intent check, video motion check, AV sync check) is logged in the repository calibration ledger with Creator sign-off.
- Deterministic checks (`T0`) and explicit `NO_PERCEPTION_INPUT` / `regeneration_required: true` guards remain **fail-closed** regardless of critic calibration status.

### 4.3 Fail-Closed Perception Contract
- Missing evaluator output, API timeout, or unreadable media MUST emit `state: "NO_PERCEPTION_INPUT"` (or `overall_verdict: "NO_PERCEPTION_INPUT"`).
- Downstream stages (`i2v_prompt_binding/1`, `stage_clips`, `stage_assemble`) MUST reject any upstream record whose state is `NO_PERCEPTION_INPUT` or `regeneration_required: true`.

---

## 5. Audio Evidence Fusion Rules (`audio_evidence/1` & §0.3 `mute_tail_from_s`)

### 5.1 Unified Voicing & Trim Contract
1. **Primary Voicing Classifier:** Silero VAD via `faster-whisper` (`vad_filter=True`) — recorded as `voicing_backend: "silero_vad"`.
2. **Fallback Voicing Classifier:** When Silero VAD is unavailable in the runtime environment, fall back to deterministic harmonicity / spectral-flatness voicing detection — recorded as `voicing_backend: "harmonicity"`. If neither runs, record `voicing_backend: "none"` and emit `verdict: "REVIEW"` (never `"PASS"`).
3. **Word Boundary Clamping:** ASR / forced-alignment word timestamps MUST be clamped to their overlapping voiced span (`word_boundaries_clamped_to_voiced_span: true`) so trailing silence or breath noise never inflates word end times.
4. **`mute_tail_from_s`:** Computed on the clip record (`float >= 0` or `null`) from the unified trim function whenever a silent reaction tail after the last spoken word contains unintended residual voicing, hallucinated speech, or bed bleed.

### 5.2 Signal Vocabulary & Minimum Signal Set
Signals are typed by role (never hardcoded to a single vendor/tool name):
- `voicing_classifier` (required for all verdicts except `NO_PERCEPTION_INPUT`)
- `asr_transcript` (required when `script_expects_speech == true`)
- `forced_alignment` (required when `script_expects_speech == true` and word-level timing is consumed)
- `energy_envelope` (required for tail muting and silence verification)
- `av_semantic` (optional multimodal corroboration)
- `script_diff` (required when `script_expects_speech == true`)

### 5.3 Hard Fusion Rules
1. **Ghost / Hallucinated Speech on Silent Beat:** If `script_expects_speech == false` AND `voicing_classifier` (or `asr_transcript`) detects a voiced speech-like span (`unintended_speech_detected == true`), `verdict` MUST be `"FAIL"` (enforced by `audio_evidence/1` schema `if/then`).
2. **Mid-Word Cut Guard:** Any proposed `out_frame` falling inside a clamped voiced word span produces `MID_WORD_PHONETIC_CUT` (`allowed: false`).
3. **One Render Path Audio Rule (Creator 2026-11-19):** Production sound comes exclusively from G8 `audio/stems`. `tools/render_tools/mix.py` is preview-only. No BBC RemArc assets may enter a monetised master (enforced by `PC-10` / `qa/third_party_media.json`).

### 5.4 Four Mandatory Synthetic Adversarial Unit Cases

| Case ID | Scenario | Synthetic Input | Expected Output |
| :--- | :--- | :--- | :--- |
| `ADV-AUD-01` | Silent beat with hallucinated LTX speech | `script_expects_speech: false`, `voicing_backend: "silero_vad"`, `voicing_classifier` span `[1.20, 2.05]` (`conf: 0.91`), `unintended_speech_detected: true` | `verdict == "FAIL"`, `mute_tail_from_s` or clip rejection triggered; schema rejects `verdict: "PASS"`. |
| `ADV-AUD-02` | Trailing ASR timestamp overshoot into silence | `script_expects_speech: true`, raw ASR word `"truce"` `[0.40, 1.85]`, `voicing_classifier` voiced span `[0.42, 1.10]` | Clamped word span `[0.42, 1.10]`, `word_boundaries_clamped_to_voiced_span: true`, `mute_tail_from_s: 1.15` (if tail noise present) or clean cut after `1.10 s`. |
| `ADV-AUD-03` | Silero VAD unavailable -> harmonicity fallback | `vad_available: false`, harmonicity detects voiced span `[0.50, 1.60]` on spoken line | `voicing_backend == "harmonicity"`, `verdict == "PASS"` (if script matches & no mid-word cut), never silently claims `silero_vad`. |
| `ADV-AUD-04` | Both VAD and harmonicity unavailable | `voicing_backend: "none"`, `signals: []` | `verdict == "REVIEW"` (never `"PASS"`), logged in `unresolved_reviews`. |

---

## 6. `RouteRegistry` Read-Only View

### 6.1 Purpose & Immutability Contract
`RouteRegistry` (`explainer_engine/core/route_registry.py`) is a **strictly read-only** facade over the existing repository configuration files:
- `config/picture_route.json` (protected)
- `config/model_routing.json` (protected)
- `config/local_models.json`
- `config/retired_era.json` (protected)
- `config/spend_caps.json` (protected)

### 6.2 Rules & Prohibitions
1. **Preserves `OR-22..36`:** All Creator routing, era-retirement, and model-selection rules (`OR-22..36`) remain authoritative in the JSON configs. `RouteRegistry` validates route strings referenced by `i2v_prompt_binding/1` against active (non-retired) routes loaded from config — replacing hardcoded model enums in schemas.
2. **Zero Config Mutation:** `RouteRegistry` exposes only query methods (`list_active_routes()`, `is_route_allowed(route_id, stage)`, `is_retired(model_id)`, `get_spend_cap(scope)`). It NEVER writes to `config/*.json`.
3. **Proposal-Only Rerouting (§0.3):** Automated rerouting (`reroute_unnatural_ltx_shots(apply_routes=False)`) may ONLY write suggestions to `production/route_proposals.json` (`route_proposals/1` with `apply_routes: false`). Proposals require explicit Creator approval before any route change is applied.
