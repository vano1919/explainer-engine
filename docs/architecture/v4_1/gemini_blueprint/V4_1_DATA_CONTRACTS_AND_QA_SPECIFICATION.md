# Explainer Engine V4.1 — Complete Validated Data Contracts, Clocks, Evidence Fusion & QA Specification

- **Document ID:** `V4.1-DOC-03` (`V4.1-DEEP-COMPLETION-002`)
- **Validation Standard:** JSON Schema Draft `2020-12`, programmatically validated via `jsonschema 4.23.0` (`Draft202012Validator.check_schema`) against valid & invalid fixtures.
- **Backwards Compatibility:** Existing `episode_timing/1 & /2` (`explainer_engine/schemas/episode_timing.schema.json`) and `qa_report/1` remain untouched and valid.

---

## 1. Complete Machine-Readable JSON Schemas (All 11 V4.1 Contracts)

All 11 contracts are defined in the companion schema bundle `v4_1_schemas.json` (and embedded canonically below) so `jsonschema` validates every single schema and payload with zero ambiguity:

```json
{
  "shot_intent/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/shot_intent/1",
    "title": "ShotIntent",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "episode_id", "shot_id", "intent_version", "historical_objective", "character_ids", "scene_location", "expected_composition", "camera_intention", "action_intention", "audio_intention", "approx_duration_s", "fixed_constraints", "flexible_requirements", "acceptance_criteria", "deferred_until_observed"],
    "properties": {
      "schema": {"const": "shot_intent/1"},
      "episode_id": {"type": "string", "minLength": 1},
      "shot_id": {"type": "string", "pattern": "^S[0-9]{2}_SH[0-9]{3}$"},
      "intent_version": {"type": "integer", "minimum": 1},
      "historical_objective": {"type": "string", "minLength": 5},
      "character_ids": {"type": "array", "items": {"type": "string"}},
      "scene_location": {"type": "string", "minLength": 1},
      "expected_composition": {"type": "string", "minLength": 3},
      "camera_intention": {"type": "string", "minLength": 3},
      "action_intention": {"type": "string", "minLength": 3},
      "audio_intention": {"type": "string", "minLength": 3},
      "approx_duration_s": {"type": "number", "exclusiveMinimum": 0, "maximum": 60},
      "fixed_constraints": {"type": "array", "items": {"type": "string"}, "minItems": 1},
      "flexible_requirements": {"type": "array", "items": {"type": "string"}},
      "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "minItems": 1},
      "deferred_until_observed": {"type": "array", "items": {"type": "string"}, "minItems": 1}
    }
  },
  "observed_image/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/observed_image/1",
    "title": "ObservedImageState",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "asset_id", "sha256", "observation_version", "characters_observed", "visible_props", "composition_observed", "camera_perspective", "headroom_ok", "lighting_observed", "feasible_motions", "intent_mismatches", "confidence", "verdict", "evaluator_model_id", "evaluator_vendor"],
    "properties": {
      "schema": {"const": "observed_image/1"},
      "asset_id": {"type": "string", "minLength": 1},
      "sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
      "observation_version": {"type": "integer", "minimum": 1},
      "characters_observed": {"type": "array", "items": {"type": "object", "required": ["char_id", "bbox_norm", "pose", "facing"], "properties": {"char_id": {"type": "string"}, "bbox_norm": {"type": "array", "items": {"type": "number", "minimum": 0, "maximum": 1}, "minItems": 4, "maxItems": 4}, "pose": {"type": "string"}, "facing": {"enum": ["left", "right", "front", "back", "three_quarter_left", "three_quarter_right"]}, "gaze": {"type": "string"}}}},
      "visible_props": {"type": "array", "items": {"type": "string"}},
      "composition_observed": {"type": "string"},
      "camera_perspective": {"type": "string"},
      "headroom_ok": {"type": "boolean"},
      "depth_layers_ref": {"type": ["string", "null"]},
      "lighting_observed": {"type": "string"},
      "feasible_motions": {"type": "array", "items": {"type": "string"}},
      "intent_mismatches": {"type": "array", "items": {"type": "string"}},
      "confidence": {"type": "number", "minimum": 0, "maximum": 1},
      "verdict": {"enum": ["ACCEPT", "EDIT_IMAGE", "REGENERATE", "ADAPT_INTENT"]},
      "evaluator_model_id": {"type": "string", "minLength": 1},
      "evaluator_vendor": {"enum": ["anthropic", "google", "local_cv", "human"]}
    }
  },
  "i2v_prompt_binding/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/i2v_prompt_binding/1",
    "title": "I2VPromptBinding",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "shot_id", "image_asset_id", "image_sha256", "observation_version", "prompt_version", "prompt_text", "model_route", "conditioning_assets", "prompt_author_skill", "accepted_at_utc"],
    "properties": {
      "schema": {"const": "i2v_prompt_binding/1"},
      "shot_id": {"type": "string", "pattern": "^S[0-9]{2}_SH[0-9]{3}$"},
      "image_asset_id": {"type": "string", "minLength": 1},
      "image_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
      "observation_version": {"type": "integer", "minimum": 1},
      "prompt_version": {"type": "integer", "minimum": 1},
      "prompt_text": {"type": "string", "minLength": 10, "maxLength": 2000},
      "model_route": {"enum": ["ltx25_distilled", "ltx25_guided", "ltx25_retake", "gemini_omni_1_2_flash"]},
      "conditioning_assets": {"type": "array", "items": {"type": "string"}},
      "prompt_author_skill": {"type": "string", "minLength": 1},
      "accepted_at_utc": {"type": "string", "minLength": 10}
    }
  },
  "media_clocks/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/media_clocks/1",
    "title": "MediaClockMapping",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "video_clock", "audio_clock", "edit_list_offset_num", "edit_list_offset_den"],
    "properties": {
      "schema": {"const": "media_clocks/1"},
      "video_clock": {"type": "object", "required": ["frame_index", "pts", "timebase_num", "timebase_den", "fps_num", "fps_den", "is_vfr", "stream_start_pts"], "properties": {"frame_index": {"type": "integer", "minimum": 0}, "pts": {"type": "integer"}, "timebase_num": {"type": "integer", "minimum": 1}, "timebase_den": {"type": "integer", "minimum": 1}, "fps_num": {"type": "integer", "minimum": 1}, "fps_den": {"type": "integer", "minimum": 1}, "is_vfr": {"type": "boolean"}, "stream_start_pts": {"type": "integer"}}},
      "audio_clock": {"type": "object", "required": ["pts", "timebase_num", "timebase_den", "sample_rate_hz", "sample_position", "encoder_delay_samples", "stream_start_pts"], "properties": {"pts": {"type": "integer"}, "timebase_num": {"type": "integer", "minimum": 1}, "timebase_den": {"type": "integer", "minimum": 1}, "sample_rate_hz": {"type": "integer", "minimum": 8000}, "sample_position": {"type": "integer", "minimum": 0}, "encoder_delay_samples": {"type": "integer", "minimum": 0}, "stream_start_pts": {"type": "integer"}}},
      "edit_list_offset_num": {"type": "integer"},
      "edit_list_offset_den": {"type": "integer", "minimum": 1}
    }
  },
  "inspection_plan/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/inspection_plan/1",
    "title": "InspectionPlan",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "shot_id", "clip_sha256", "tier", "run_audio_fusion", "run_python_pts_resolve", "fallback_tier", "max_estimated_usd"],
    "properties": {
      "schema": {"const": "inspection_plan/1"},
      "shot_id": {"type": "string"},
      "clip_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
      "tier": {"enum": ["DETERMINISTIC_ONLY", "FRAME_EXTRACT_PLUS_VLM", "DENSE_ADAPTIVE_SAMPLING", "VLM_SEMANTIC_PLUS_NATIVE", "AGENTIC_VIDEO_SEARCH"]},
      "vlm_model_id": {"type": ["string", "null"]},
      "sampling_fps": {"type": ["number", "null"], "minimum": 0.5, "maximum": 24},
      "run_audio_fusion": {"type": "boolean"},
      "run_python_pts_resolve": {"const": true},
      "fallback_tier": {"enum": ["DETERMINISTIC_ONLY", "FRAME_EXTRACT_PLUS_VLM", "DENSE_ADAPTIVE_SAMPLING"]},
      "max_estimated_usd": {"type": "number", "minimum": 0}
    }
  },
  "audio_evidence/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/audio_evidence/1",
    "title": "AudioEvidenceFusion",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "clip_id", "signals", "contradictions", "verdict", "requires_human_review"],
    "properties": {
      "schema": {"const": "audio_evidence/1"},
      "clip_id": {"type": "string"},
      "signals": {"type": "array", "minItems": 1, "items": {"type": "object", "required": ["source", "result", "confidence", "depends_on"], "properties": {"source": {"enum": ["vad", "asr_whisperx", "forced_alignment", "waveform_spectral", "vlm_av_semantic", "script_diff"]}, "result": {"type": "string"}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}, "depends_on": {"type": "array", "items": {"type": "string"}}}}},
      "contradictions": {"type": "array", "items": {"type": "string"}},
      "verdict": {"enum": ["PASS", "FAIL", "WARN", "HUMAN_REVIEW", "INSUFFICIENT_EVIDENCE"]},
      "requires_human_review": {"type": "boolean"},
      "calibration_ref": {"type": ["string", "null"]}
    }
  },
  "observed_video/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/observed_video/1",
    "title": "ObservedVideoState",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "clip_id", "clip_sha256", "detected_actions", "visual_defects", "motion_direction", "audio_verdict", "evaluator_model_id"],
    "properties": {
      "schema": {"const": "observed_video/1"},
      "clip_id": {"type": "string"},
      "clip_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
      "detected_actions": {"type": "array", "items": {"type": "object", "required": ["event_id", "kind", "start_frame", "peak_frame", "end_frame", "confidence"], "properties": {"event_id": {"type": "string"}, "kind": {"type": "string"}, "start_frame": {"type": "integer", "minimum": 0}, "peak_frame": {"type": "integer", "minimum": 0}, "end_frame": {"type": "integer", "minimum": 0}, "confidence": {"type": "number", "minimum": 0, "maximum": 1}}}},
      "visual_defects": {"type": "array", "items": {"type": "string"}},
      "motion_direction": {"type": "string"},
      "audio_verdict": {"enum": ["PASS", "FAIL", "WARN", "HUMAN_REVIEW", "INSUFFICIENT_EVIDENCE"]},
      "evaluator_model_id": {"type": "string"}
    }
  },
  "cut_decision/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/cut_decision/1",
    "title": "CutDecision",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "shot_id", "cut_type", "in_frame", "out_frame", "action_phase", "allowed", "rationale", "author_skill"],
    "properties": {
      "schema": {"const": "cut_decision/1"},
      "shot_id": {"type": "string"},
      "cut_type": {"enum": ["ACCIDENTAL_UNRESOLVED_MOTION", "MID_WORD_PHONETIC_CUT", "INTENTIONAL_CUT_ON_ACTION", "POST_RESOLUTION_CUT", "DRAMATIC_INTERRUPTION", "INTENTIONAL_J_CUT", "INTENTIONAL_L_CUT"]},
      "in_frame": {"type": "integer", "minimum": 0},
      "out_frame": {"type": "integer", "minimum": 1},
      "action_phase": {"enum": ["anticipation", "peak", "resolution", "hold", "speech_boundary"]},
      "screen_direction_preserved": {"type": "boolean"},
      "allowed": {"type": "boolean"},
      "rationale": {"type": "string", "minLength": 5},
      "author_skill": {"type": "string"}
    }
  },
  "av_events/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/av_events/1",
    "title": "AVEventTimeline",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "episode_id", "events"],
    "properties": {
      "schema": {"const": "av_events/1"},
      "episode_id": {"type": "string"},
      "events": {"type": "array", "items": {"type": "object", "required": ["event_id", "shot_id", "status", "event_type", "offset_samples", "duck_narration_db"], "properties": {"event_id": {"type": "string"}, "shot_id": {"type": "string"}, "status": {"enum": ["PLANNED_ONLY", "OBSERVED_ONLY", "MATCHED"]}, "event_type": {"enum": ["hard_impact", "anticipation", "foley_contact", "j_cut", "l_cut", "ambience_swell", "dialogue_word", "map_cue"]}, "offset_samples": {"type": "integer"}, "duck_narration_db": {"type": "number", "maximum": 0}}}}
    }
  },
  "continuity_memory/1": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/continuity_memory/1",
    "title": "ContinuityMemory",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "episode_id", "last_accepted_shot_id", "observed_accepted_state"],
    "properties": {
      "schema": {"const": "continuity_memory/1"},
      "episode_id": {"type": "string"},
      "last_accepted_shot_id": {"type": "string"},
      "planned_state_ref": {"type": ["string", "null"]},
      "observed_accepted_state": {"type": "object", "required": ["characters", "screen_direction", "lighting_weather", "endpoint_frame_sha256", "action_resolved", "sound_bed"], "properties": {"characters": {"type": "object"}, "screen_direction": {"type": "string"}, "lighting_weather": {"type": "string"}, "endpoint_frame_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"}, "action_resolved": {"type": "boolean"}, "sound_bed": {"type": "string"}}}
    }
  },
  "qa_result/2": {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "https://explainer-engine.local/schemas/qa_result/2",
    "title": "QAResult",
    "type": "object",
    "additionalProperties": false,
    "required": ["schema", "job_id", "stage", "asset_sha256", "overall_status", "findings", "blocks_progression"],
    "properties": {
      "schema": {"const": "qa_result/2"},
      "job_id": {"type": "string"},
      "stage": {"enum": ["observe_image", "observe_video", "clip", "sound", "assemble", "master"]},
      "asset_sha256": {"type": "string", "pattern": "^[a-f0-9]{64}$"},
      "overall_status": {"enum": ["PASS", "WARN", "REPAIR_REQUIRED", "BLOCKED", "ESCALATE_TO_HUMAN"]},
      "findings": {"type": "array", "items": {"type": "object", "required": ["check_id", "severity", "reason", "remediation"], "properties": {"check_id": {"type": "string"}, "severity": {"enum": ["BLOCKER", "MAJOR", "MINOR", "INFO"]}, "reason": {"type": "string"}, "remediation": {"type": "string"}}}},
      "blocks_progression": {"type": "boolean"}
    }
  }
}
```

---

## 2. Amendment E — `AudioEvidenceFusion` Decision Table (1914 Fixtures)

| 1914 Fixture | `VAD` | `ASR` (`WhisperX`) | `Forced Align` *(dep on ASR)* | `Waveform/Spectral` | `Script Diff` | Fusion Verdict & Required Action |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`S03_SH007`** (silent beat w/ `"Oh my God"` noise) | `False` / low | `"Oh my God"` | Low-score forced match | Wind noise floor | Unexpected speech on silent beat | **`FAIL` (Contradiction: VAD=False vs ASR!=empty)** -> Mute clip audio or `RetakePipeline(regenerate_audio=True)` |
| **`S06_SH008`** (double `"Maybe"` at `0.0s` & `1.72s`) | `True` (2 bursts) | `"Maybe. Maybe. But not today."` | Aligned 3 segments | 2 speech envelopes | Duplicate opening word | **`FAIL` (Duplicate dialogue)** -> Trim `in_frame` past 1st `"Maybe"` (`1.45s` PTS) |
| **`S03_SH003`** (`"Stille Nacht..."` cut mid-word) | `True` at out-point | `"Nacht"` ends at `4.71s` | Word spans `out_frame` | Active vocal energy at boundary | Word truncated | **`FAIL` (`MID_WORD_PHONETIC_CUT`)** -> Extend `out_frame` to `4.71s` PTS |
| **`S07_SH005`** (2 bangs before narration) | `False` at `0.5s, 1.6s` | Empty at `0.5s, 1.6s` | N/A | 2 sharp impulse peaks (`0.5s`, `1.6s`) | Bangs precede `"shots into the air"` | **`WARN` -> `INTENTIONAL_J_CUT`** (`offset_samples = -48000`, `duck_narration_db = -4.0`) |
| **`S07_SH006`** (2 planned shots, 1 generated) | `False` | Empty | N/A | 1 impulse peak (`7.9s`) | Planned 2 impulses, observed 1 (`PLANNED_ONLY` #2) | **`HUMAN_REVIEW` / `ADAPT`** -> Layer 2nd bang cue from library via `av_events/1` |

---

## 3. Mandatory `WP-02` Negative Test Fixtures (`tests/integration/test_v41_wp02_single_shot_closed_loop.py`)

Every negative test runs strictly through `episode/run.py` with synthetic/mocked VLM & local FFmpeg clips (`$0.00`):
1. **`T1_image_mismatch`:** Fixture `shot_intent/1` (`facing="left"`, `props=["candle"]`) vs. `observed_image/1` (`facing="right"`, `props=[]`, `verdict="REGENERATE"`) -> asserts `StageRefused` before `videolane/scene.py:build`, `0` LTX submissions.
2. **`T2_post_observe_swap`:** Observe Image A (`sha256=aaa...`, `verdict="ACCEPT"`), overwrite PNG with Image B (`sha256=bbb...`) -> asserts `ContractError("IMAGE_MUTATED_AFTER_OBSERVATION")`.
3. **`T3_motion_timing_diff`:** `approx_duration_s=2.0`, `observed_video/1` resolves handshake at `frame 82` (`3.417s` @ `24fps`) -> asserts `CutDecision.out_frame == 82`, never `48`.
4. **`T4_mid_word_and_ghost_speech`:** Replays `S03_SH003` & `S03_SH007` fixtures -> asserts `MID_WORD_PHONETIC_CUT` blocks & `AudioEvidenceFusion` flags VAD/ASR contradiction.
5. **`T5_intentional_cut_on_action`:** `cut_type="INTENTIONAL_CUT_ON_ACTION"`, `action_phase="peak"`, `screen_direction_preserved=True`, `allowed=True` -> asserts `PASS` (not falsely rejected).
6. **`T6_av_clock_offset`:** Synthetic clip with `timebase=Fraction(1, 90000)`, `fps=Fraction(24, 1)`, `sample_rate_hz=48000`, `encoder_delay_samples=1024`, `edit_list_offset=Fraction(1, 24)` -> asserts exact integer sample placement with `0`-sample drift vs float error.
7. **`T7_qa_blocker_halt`:** Injects `qa_result/2` finding `severity="BLOCKER"`, `blocks_progression=True` -> asserts `episode/run.py:stage_qa` sets `all_gates_passed=False`, blocks timeline export, and resumes cleanly after defect is cleared.
