# Data contracts (CN-)

Every file one stage hands to the next has ONE versioned JSON Schema, and this page is its one home (Blueprint plan v2,
phase P2; Blueprint phase 3). A contract says what the file holds, who writes it, who reads it, and whether it is
written by hand (by an agent or a person) or **derived** by code from other contracts. A derived file is never edited
by hand: it carries the sha256 of every input it was made from, and a stale one is refused.

- Schemas: `explainer_engine/schemas/<name>.schema.json`; a document names its contract in `"schema": "<name>/<N>"`.
- Validation: `explainer_engine/core/contracts.py` (`errors(doc, base)`, `validate(doc, base)` raises `ContractError`,
  CLI `python -m explainer_engine.core.contracts check <file>...`): the JSON Schema first, then the contract's
  semantic checks below (frame geometry, derived freshness, index ranges). jsonschema only, no Pydantic (plan D1).
- Lifecycle of an episode: `explainer_engine/core/store.py` (`EpisodeJob`, `job_manifest/1`).
- Shot cache: `explainer_engine/core/shot_cache.py` (`shot_spec/1` -> SHA-256 key).
- Money: the one run ledger `explainer_engine/core/ledger.py` and `config/spend_caps.json` (D-56); nothing new here.
- Fixtures: `tests/fixtures/contracts/<name>/valid*.json` and `invalid__<what>.json`; tests
  `tests/unit/test_contracts.py`, `test_lifecycle.py`, `test_shot_cache.py`, `test_one_ledger.py`,
  `test_spend_caps_single_source.py`, `test_sourced_rules_sync.py`, `test_validator_severity_tiers.py`.
- Delivery frame rate: [D-85](DECISIONS_AND_OPEN_QUESTIONS.md).

P2 writes the contracts, the lifecycle, the cache and the tests. It does not write stage logic: the compilers that
produce the derived files belong to the phases named in the table (P3, P4, P5, P6, P7, P8, P9).

## The contracts

| Contract | File in the job | Written by | Hand or derived | Read by |
|---|---|---|---|---|
| `job_manifest/1` | `jobs/<slug>/job_manifest.json` | `core/store.EpisodeJob` | code (the lifecycle) | every stage, the coordinator (P11) |
| `script_variants/1` | `story/script_variants.json` | variant planner (P3, stage 1b) | hand (variants) + the creator's choice | scenario writer, P6 budget |
| `script_variants/2` | `story/script_variants.json` | variant planner (P3, stage 1b) | hand (variants) + the creator's choice; code fills dynamics, cost and `scores.code` | scenario writer, P6 budget |
| `screenplay_spine/1` | `story/screenplay_spine.json` | `production compile` (P3) | **derived** from `production_script/3` + `film_shots/2` | P4, P5, P7, critic |
| `voice_casting/1` | `audio/voice_casting.json` | voice director (P4b) | hand + test reads | narration, LTX dialogue |
| `voice_audition/1` | `audio/auditions/<voice_id>.json` | `audio/voice_audition.py` (P4b) | code (a free listening) | casting card, `voice_audition.distinct`, P8 |
| `channel_voices/1` | `config/channel_voices.json` | the creator's word, `voice_check.register` (P4b) | hand (baseline from `voice_audition baseline`) | `voice_check.check_against` (EL-13), voice-caster |
| `audio_spine/1` | `audio/audio_spine.json` | audio spine compiler (P4) | **derived** from `words.json` + `production_timed/1` | P5, P6, P7 (their clock) |
| `audio_spine/2` | `audio/audio_spine.json` | audio spine compiler (P4) | **derived** from `words.json` + `production_timed/1` (+ `film_shots/2`) | P5, P6, P7, the sound director |
| `sound_mix_manifest/1` | `audio/sound_mix_manifest.json` | sound director (P4) | hand, on the spine (a /1 file stays valid) | `production/assemble.py` |
| `sound_mix_manifest/2` | `audio/sound_mix_manifest.json` | sound director (P4, `audio/sound_director.py`) | **derived** from the spine + `production_timed/1` + `film_shots/2` + the library manifest | `production/assemble.py` |
| `visual_comp_manifest/1` | `visual/visual_comp_manifest.json` | compensator (P5) | hand, on the spine | maps / HUD renderer, router |
| `scene_set/1` | `sets/<set_id>.json` | set builder (P6) | hand (numeric geography) | continuity card fields (derived, P6), backdrop crop |
| `film_shots/2` | `film_shots.json` (= the scene manifest) | beat / shot writers (P6) | hand | compose, router, cache, assemble |
| `shot_spec/1` | `shots/<shot_id>.spec.json` | compose / router (P6) | **derived** from `film_shots/2` | `core/shot_cache.py`, pod scripts |
| `pod_heartbeat/1` | `jobs/cloud/.../heartbeat.json` and the pod's `beat.txt` parsed | pod scripts, guard, watchdog (P1a) | code | guard, watchdog, `runpod check` |
| `edit_and_grade_manifest/1` | `edit/edit_and_grade.json` | edit planner (P7) | hand (cuts) | assemble's own manifest (**derived**, P7), OTIO export |
| `qa_report/1` | `qa/<stage>.qa_report.json` | QA gates (P8) | code | retry router, review bundle |
| `editorial_review/3` | `story/editorial_review.json` | the critic (P3b/P8) | hand (findings), per department | `production/editorial_gate.py` (P8 accepts /3) |
| `distribution_package/1` | `packages/<clip_id>.json` | packager (P9) | code + copy | `qa/publish_check.py`, `publish/` (P10) |

`editorial_review/2` already exists (D-60, the integrated review of `production_script/3`); the department layers are
therefore version 3, not a new meaning of 2. `continuity_card/2` (P6) takes its camera side, eyeline, landmarks and
backdrop crop from `scene_set/1` by code; P2 writes only `scene_set/1`.

### Field summary

Every contract has `schema` and `additionalProperties: false` at every level; a hash is 64 lower-case hex characters;
times are seconds (number, 3 decimals) and frames are integers at the job's fps; a file reference is
`{"path": <relative to the job folder>, "sha256": <hex>}`.

- **job_manifest/1**: `job_id`, `episode_slug`, `created`, `fps` (D-85), `state` (the lifecycle below), `state_since`,
  `history[]` (`from`, `to`, `at`, `path` = `forward` or a named back path or `abort`/`reopen`/`adopted`, `reason`,
  `approval` or null), `source_dossier_sha256` (null until RESEARCHED, then fixed), `ledger` (path to the run's
  `run.json`), `budget_reservation_id` (null or an item of that ledger), `approvals{<state>: approval}`,
  `artifacts{<key>: {path, sha256, schema|null, dossier_sha256}}`, `distribution_packages[]` (file references),
  `reopen_to` (only in a terminal state). An approval is `{kind: creator|machine|planner, by, ref, at, sha256}`:
  `ref` is the creator's message id or dated words (creator), the report file (machine) or the planning thread's
  message id (planner, OR-24).
- **script_variants/1**: `episode_slug`, `dossier_sha256`, `variants[2..3]` (`id`, `title`, `profile_id`, `logline`,
  `outline[]`, `dynamics{}` numbers, `cost{usd_planned, usd_worst, unknown_rows[]}`), `chosen` (null or
  `{variant_id, by, ref, at}`).
- **script_variants/2** (P3): the same file with, per variant, `segments[]` (`id`, `window_s`, `function`, `blocks[]` of `category`
  scene|map_pure|compensator|host|hold or `lane`, `archetype`, `seconds`, `who`, `tier`, `words`), `cost_rows[]` (what is paid: `kind` pod|api|cpu|voice),
  `cost` (`usd_planned`/`usd_worst` a number or the string `"unknown"`, the known part, `rows[]`), `risks[]`, `scores{code, critic}` and optional
  `packaging_promises[3]`; top-level `recommended` and `why`; `chosen.variants_sha256` (the sha256 of the variants array the creator picked from).
  The code fills `dynamics`, `cost`, `risks` and `scores.code` (`variant_plan score --write`); `variant_plan check` recomputes them (a stale number
  is CN-02), refuses blocks that do not add up to their windows (VP-01) and a choice whose `variants_sha256` no longer matches (CN-04).
  `EpisodeJob.move("VARIANT_CHOSEN", variants=<file>)` binds the creator's approval to the same hash.
- **screenplay_spine/1**: `derived_from{production_script, film_shots}`, `episode_slug`, `structure_profile_id`,
  `packaging_promises[3]`, `segments[]` (`id`, `est_duration_sec`, `causal_connector` THEREFORE|BUT|OPEN,
  `clock_window_sec[2]`, `lines[]` (`index`, `speaker`, `text`, `claim_ids[]`)), `claims[]` (`claim_id`,
  `status` FACT|ALTERNATE, `source_ref`).
- **voice_casting/1**: `episode_slug`, `roles[]` (`role_id`, `cast_id` or `narrator`, `voice_id`, `model`,
  `settings{stability, similarity, style, speed}`, `pronunciations[]{word, say}`, `test_read` file or null,
  `approved` null or `{by, ref, at}`).
- **voice_audition/1**: `voice_id`, `name`, `source{kind library_preview|test_read|take, ref, sha256?}`, `profile{duration_s,
  sample_rate, speech_s, reliable, f0_median_hz, f0_range_st, pitch_variation_st, emphasis_db, syllable_rate, wpm_speaking,
  wpm_overall, centroid_hz, tilt_db, sibilance_db, pauses{count, per_min, median_s, ratio}}`, `consistency` null or
  `{embedder, takes, min_cosine, mean_cosine}`, `fit` null or `{trait, usage_rank, listed, unlabelled}`.
- **channel_voices/1**: `voices[]` (`voice_id`, `name`, `role` narrator|character, `status` channel|candidate|retired,
  `model`, `note`, `baseline` null or `{kind preview|read, ref, sha256?, centroid_hz, tilt_db, f0_median_hz?}`); at most one
  channel narrator (VC-08).
- **audio_spine/1**: `derived_from{words, timed}`, `fps`, `duration_s`, `total_frames`, `words[]` (`i`, `text`,
  `start_s`, `end_s`, `start_frame`, `end_frame`, `segment`, `line`), `segments[]` (`id`, `start_frame`, `end_frame`),
  `post_hoc_shots[]` (LTX-native dialogue shots whose words are timed from the rendered clip, P4).
- **audio_spine/2** (D-88): everything of `audio_spine/1`, plus optional `derived_from.film_shots`, and on every `post_hoc_shots[]` entry
  `after_word` (the last read word before the window; -1 = before the first) and `source` (`planned` or `clip`) with `clip_sha256` (a hash
  iff `source` is `clip`, else null). A window reserves the shot's planned length after `after_word`; every later word moves by it. The
  windows are in order, do not overlap, lie inside `total_frames`, and no word frame falls inside one (CN-01). A document with no window
  and no `film_shots` is written as `/1`.
- **sound_mix_manifest/1**: `audio_spine` (file reference), `stems[]` (subset of dialogue, narration, music, sfx,
  ambience), `beds[]` (`scene`, `ref`, `gain_db`, `start_frame`, `end_frame`), `vacuums[]` (`start_frame`, `end_frame`,
  `reason`), `spots[]` (`id`, `shot_id`, `ref`, `word_index` or `frame`, `stem`, `pan` -1..1, `perspective`
  near|mid|far, `gain_db`), `master{rule}` (a BP id, never a number).
- **sound_mix_manifest/2**: `derived_from{audio_spine, timed, library, film_shots?}` (file references), `fps`, `total_frames`, `stems[]`,
  `narration{ref, sha256}`, `dialogue[]` (`shot_id`, `ref` or null, `start_frame`, `end_frame`; mirrors the spine's windows), `scenes[]`
  (`scene`, `start_frame`, `end_frame`, `acoustic` outdoor|room|hall|cave|neutral, `acoustic_source` declared|inferred, `ir_seed`, `entry`
  J|L|butt, `lead_frames`), `beds[]` (`id`, `scene`, `kind` room_tone|ambience|native, `ref`, `gain_db`, `start_frame`, `end_frame`,
  `fade_in_frames`, `fade_out_frames`), `music[]` (`id`, `ref`, `motif_of` or null, frames, `gain_db`, fades, `beat_grid`
  `{bpm, offset_s, source}` or null), `vacuums[]` (`start_frame`, `end_frame`, `reason`, `reveal_frame`), `cues[]` (`name`, `frame`,
  `gain_db`, `max_ms` or null), `spots[]` (as /1 plus `group`, `layer` single|sub|body|air, `origin` timed_sfx|foley|loudest|hit),
  `presence_dip{rule}`, `perspective{rule}`, `master{rule}`: BP ids only, never numbers.
- **sfx_manifest** (the sound library, schema version 1) gains optional fields for P4, nothing else changes: `source.kind` `open_model`
  (+ `source.model`, `source.seed`, `source.admission` = the id of a record in `assets/audio/generator_admission.json`, BP-162, SD-13;
  `sfx_library.validate` refuses one whose admission is missing or for another kind), `motif_of` and `beat_grid {bpm, offset_s, source}`.
- **visual_comp_manifest/1**: `audio_spine` (file reference), `items[]` (`item_id`, `shot_id`, `archetype_id`,
  `trigger_word_index`, `duration_frames`, `layers[]` (`kind`, `ref`, `reveal_word_index` or null),
  `on_screen_text` or null).
- **scene_set/1**: `set_id`, `units` = `m`, `axis{deg 0..360, origin[2]}`, `objects[]` (`id`, `kind`, `pos[3]`,
  `size[3]`, `yaw_deg`, `landmark`), `mannequins[]` (`id`, `cast_id`, `pos[3]`, `yaw_deg`), `cameras[]` (`shot_id`,
  `pos[3]`, `yaw_deg`, `pitch_deg`, `fov_deg`).
- **film_shots/2**: everything of `film_shots/1` ([SHOT_PROMPTS](SHOT_PROMPTS.md); a `/1` document carrying any of the fields below is refused), plus top-level `fps` (D-85) and
  optional `scene_sets[]`, and on every shot `lane` (KEYFRAME_LTX, DIALOGUE_CU, HOST_COMMENTARY, DRAMA_BLOCKED_3D,
  ATMOS_BROLL, MAP, COMPENSATOR, STILL_HOLD), `archetype` (an id of the P5 catalogue), `duration_frames`, `width`,
  `height`, `lens_tier` (wide|normal|long), `focal_xy[2]` (0..1 of the frame), `continuity_ref` and `blocking_ref`
  (`<file>#<id>` or null). The shot size stays `frame.size` (one field, not two).
- **shot_spec/1**: `shot_id`, `job_id`, `lane`, `prompt`, `negative`, `seed`, `model{id, sha256|revision}`,
  `loras[]{id, sha256, weight}`, `width`, `height`, `frames` (null for a still), `fps`, `audio_slice_sha256`,
  `refs[]{role, path, sha256}`, `blocking_sha256`, `recipe` (the pipeline's version string), `params{}` (steps, cfg,
  sampler: every other number or name the renderer uses; hashed whole, so never a file path).
- **pod_heartbeat/1**: `job_id`, `pod_id`, `boot_nonce`, `seq`, `ts_utc`, `state` (BOOTING, PREFLIGHT_OK, RUNNING,
  UPLOADING, DONE, FAILED, FAILED_UPLOAD, BAD_HOST), `progress`, `stage`, `key_probe_http` (int or null), `spend_usd`
  (number or null). The text of `beat.txt` and its parser are P1a's; they map onto these fields.
- **edit_and_grade_manifest/1**: `film_shots` and `audio_spine` (file references), `scenes[]` (`scene_id`,
  `key_master_frame`, `grade{lut}` or null, `cuts[]` (`from_shot`, `to_shot`, `cut_type` STRAIGHT_CUT|ACTION_PEAK_CUT|
  DEPTH_MATCH_CUT|OCCLUSION_WIPE|WHIP_PAN|KULESHOV_L_CUT, `at_frame`, `audio_lead_frames`))).
- **qa_report/1**: `job_id`, `stage`, `status` PASS|WARN_REVIEW|REPAIR_APPLIED|ESCALATE_TO_HUMAN, `checks[]`
  (`check_id`, `rule`, `severity` FAIL|REVIEW|INFO, `measured`, `threshold`, `passed`), `retry_directive` null or
  `{shot_id, attempt, action}` (RESEED, REWEIGHT_REFERENCES, FALLBACK_KEYFRAME_LTX, FALLBACK_STILL_HOLD).
- **editorial_review/3**: `script` (file reference), `reviewer`, `layers{<department>}` for script, direction,
  cinematography, editing, sound, packaging (`status` inspected|not_applicable, `checklist_ids[]`, `findings[]` with
  the `editorial_review/2` finding keys).
- **distribution_package/1**: `clip_id`, `platform` youtube_long|yt_short|tiktok|ig_reel, `visibility`
  private|unlisted, `source_episode_sha256`, `source_time_range[2]`, `claim_ids_covered[]`, `hook_mode`
  PURE_SLICE|SYNTHETIC_BRIDGE, `files{video, cover, captions}` (file references), `post_copy`, `pinned_comment`,
  `ai_label`, `ab_packaging_variants[0..3]{title, thumbnail_brief}`, `checks[]{check_id, severity, passed}`.

## Rules

| ID | Rule | Basis | Checked by |
|---|---|---|---|
| CN-01 | Every contract file names its contract in `schema` (`<name>/<N>`) and validates against that schema before any stage reads it; a stage never repairs a file to make it pass | invariant 7 | `core/contracts.validate` FAIL |
| CN-02 | A derived contract carries `derived_from` with the sha256 of every input; when an input changed it is stale and refused; it is never edited by hand | invariant 7 | `contracts.errors(doc, base)` FAIL |
| CN-03 | An episode job moves only forward along the lifecycle or along a named back path; any other move raises `ContractError` and writes nothing | invariant 7 | `store.EpisodeJob.move` / `back` |
| CN-04 | A gated state is entered only with an approval of its kind (table below); a creator or planner approval of a gate needs `by`, `ref` and a non-null `sha256` of what was approved (OR-15, OR-17, OR-19, D-50, invariant 4); `adopt` is held to the same gates | invariant 4 + the creator's gates | `EpisodeJob.move` |
| CN-05 | The research dossier's sha256 is fixed when the job becomes RESEARCHED; an artifact recorded under another dossier hash, or a path inside another job's folder, is refused (no cross-job bleed, Blueprint GAP-01) | invariant 5 | `EpisodeJob.record_artifact` / `check_artifact` |
| CN-06 | PUBLISHED_PUBLIC only records the creator's own Studio click (his `ref`); no code path sets a video public, and `distribution_package/1` allows only private or unlisted | invariant 4 | `EpisodeJob.move`, schema |
| CN-07 | A shot's cache key is the SHA-256 of the canonical JSON of its `shot_spec/1` without file paths: prompt, negative, seed, model hash, LoRA hashes and weights, size, frames, fps, audio slice hash, reference hashes, blocking hash, recipe and params; one changed byte in any of them is a new key, a moved file is not; a hit needs every stored output's sha256 to match | invariant 2 (nothing paid twice) | `core/shot_cache.py` |
| CN-08 | A shot on a video lane has 8k+1 frames, a width and height divisible by 32 and at most the clip frame limit; two-stage pipelines want multiples of 64; the numbers and the severity come from BP-139 | BP-139 | `contracts` (`film_shots/2`, `shot_spec/1`) |
| CN-09 | One frame rate per episode with video-model clips: the clips' native rate (D-85); `job_manifest.fps`, `film_shots/2.fps` and every `shot_spec/1.fps` of a video lane are equal; no pulldown or frame-rate conversion | D-85 | `contracts` |
| CN-10 | Pods and API calls reserve in the same episode ledger (`run.json`, D-56), stopping at 80 % of a cap; no cap number is written in code outside `config/spend_caps.json` | invariant 1, 2 | `test_one_ledger.py`, `test_spend_caps_single_source.py` |
| CN-11 | A check may FAIL only on a binding BP rule, a CLAUDE.md invariant or a house rule that quotes the creator's dated words; a check driven by a hypothesis rule is REVIEW at most (D-59) | D-59 | `test_validator_severity_tiers.py`, `sourced_rules.level` |
| CN-12 | Every module that reads a BP threshold (`T("BP-xx", ...)`) is listed in that rule's `enforced_by`, and every key it reads exists | D-59 | `test_sourced_rules_sync.py` |
| CN-13 | A `qa_report/1` with status PASS has no failed FAIL check, and a retry directive's attempt is at most the ledger's failure limit (OR-04) | OR-04 | `contracts` |
| CN-14 | A `distribution_package/1` lists only files that exist with their sha256, and when the job folder holds `job_manifest.json` its `source_episode_sha256` equals that manifest's `assembled_video` artifact (a package from an older render is refused) | invariant 4, 5 | `contracts.errors(doc, base)` FAIL |
| CN-16 | A `sound_mix_manifest/2` agrees with its spine: every frame lies inside `total_frames`, which equals the spine's; `scenes[]` tile the spine without a gap or an overlap; each hit group has exactly one `sub`, one `body` and one `air`; every `word_index` is inside the spine named by `derived_from.audio_spine` (D-88) | invariant 7, D-88 | `core/contracts.py` FAIL |

## The lifecycle (`job_manifest/1`)

Forward path:

CREATED -> RESEARCHED -> VARIANT_CHOSEN -> SCENARIO_APPROVED -> SCRIPT_APPROVED -> STORYBOARDED -> BUDGET_RESERVED ->
SAMPLE_APPROVED -> AUDIO_TIMED -> ASSETS -> ASSEMBLED -> QA_PASSED -> REVIEW_APPROVED -> STAGED_UNLISTED ->
PUBLISHED_PUBLIC.

AUDIO_TIMED comes after SAMPLE_APPROVED and not before BUDGET_RESERVED (the Blueprint's order): the narration is a
paid ElevenLabs read, and OR-19 allows only the two-part sample to be paid before the creator approves it. The sample's
own partial timing is part of the sample stage.

| Entered state | Gate | Approval kind | What it binds |
|---|---|---|---|
| RESEARCHED | dossier recorded | machine | the dossier's sha256 (fixed from here, CN-05) |
| VARIANT_CHOSEN | the creator picks one variant | creator | `script_variants.json` |
| SCENARIO_APPROVED | OR-15 | creator | the scenario file |
| SCRIPT_APPROVED | gate #1, OR-17 | creator | the words' sha256 (`script_approval`) |
| STORYBOARDED | gate #2: shot cards locked, validators 0 FAIL | machine | `film_shots.json` and the validator report |
| BUDGET_RESERVED | gate #3: the estimate and the provider choice (D-50, OR-17 cost table); a pod plan also OR-23/OR-24 | creator or planner | the paint/pod plan hash; `budget_reservation_id` must be a reserved item of the ledger |
| SAMPLE_APPROVED | OR-19 | creator | `sample_approval.json` |
| AUDIO_TIMED | the audio spine is written and valid, and the sound director's plan has 0 FAIL (`audio/sound_director.py`, the SD checks of [AUDIO_SYSTEM](AUDIO_SYSTEM.md)) | machine | `audio_spine.json` and `sound_mix_manifest.json` |
| ASSETS, ASSEMBLED, STAGED_UNLISTED | the stage's own checks | machine | the stage's output or report |
| QA_PASSED | `qa_report/1` PASS | machine | the report |
| REVIEW_APPROVED | approval #2, invariant 4 | creator | the review bundle |
| PUBLISHED_PUBLIC | gate #4: the creator's click in Studio | creator | his message (CN-06) |

Named back paths (anything else is refused, CN-03):

| Path | From | To | When |
|---|---|---|---|
| `variant_changed` | VARIANT_CHOSEN, SCENARIO_APPROVED | RESEARCHED | the creator wants another variant |
| `scenario_changed` | SCENARIO_APPROVED .. REVIEW_APPROVED | VARIANT_CHOSEN | the scenario is rewritten |
| `words_changed` | SCRIPT_APPROVED .. REVIEW_APPROVED | SCENARIO_APPROVED | a spoken word changed after approval #1 (OR-17); the reservation id is cleared |
| `storyboard_changed` | STORYBOARDED .. QA_PASSED | SCRIPT_APPROVED | shot cards rewritten; the budget is approved again |
| `plan_changed` | BUDGET_RESERVED | STORYBOARDED | the estimate or the provider changed |
| `retime` | ASSETS, ASSEMBLED, QA_PASSED | AUDIO_TIMED | lines re-read (the QA loop's allowance) |
| `repair` | ASSEMBLED, QA_PASSED | ASSETS | a QA retry or the creator's notes on the review bundle |
| `post_review_fix` | REVIEW_APPROVED, STAGED_UNLISTED | ASSETS | a fix after approval #2 (needs the creator's ref) |

Terminal states: FAILED_PREFLIGHT, FAILED_QA_ESCALATED, ABORTED_SPEND_CAP, CANCELLED_BY_CREATOR. Any state before
PUBLISHED_PUBLIC may abort into one of them (the state left is kept in `reopen_to`); a terminal state leaves only by
`reopen`, back to `reopen_to`, with the creator's approval. PUBLISHED_PUBLIC has no moves.

A back path drops `budget_reservation_id` but not the reservation in the ledger (`run.json`): the next `reserve` counts on top of it, so the 80 % stop arrives early, which is the safe direction. P12 settles or refunds the old reservation before it reserves again.

`job_manifest.json` is the episode's lifecycle; `state.json` of `JobStore` stays the run status of one stage pipeline,
and `cloud/jobs.py` the lifecycle of one pod job. An existing episode folder without a manifest gets one with
`EpisodeJob.adopt` (history path `adopted`): the right approval of every gated state from the first step up to the target is shown and recorded (bound to a sha256 where a person approved), the dossier file is named and hashed, a state past BUDGET_RESERVED names a reservation the ledger holds, and PUBLISHED_PUBLIC (the creator's click, CN-06) or a terminal state is never adopted into. `create` makes only CREATED.
