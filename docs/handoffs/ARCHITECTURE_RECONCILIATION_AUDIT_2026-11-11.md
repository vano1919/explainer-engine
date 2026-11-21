# Explainer Engine — Architecture Reconciliation Audit

**Audit date:** 2026-11-11  
**Input:** `Explainer_Engine_V4_Main.zip` uploaded in this conversation  
**Repository inspected:** `vano1919/explainer-engine`  
**Scope:** Architecture, rule governance, Gemini migration prompt, YouTube audience-review layer, API/provider viability. This is a read-only audit; no production code or media was changed.

## Executive finding

The supplied v4.1 master prompt is not a safe handoff for the current project. It combines at least three generations of architecture, treats historical rules as universally binding, assumes provider models that are no longer available, and asks the agent to mutate code before establishing which source snapshot is authoritative.

The uploaded archive contains a newer D-123–D-127 working set than the current GitHub Gemini branch inspected. It is not one clean source tree: it contains multiple nested bundles, overlays, deprecated bundles, completed episode media, notebooks, generated manifests, and secret-bearing configuration files. The correct action is a controlled reconciliation, not a wholesale upload or blind restoration.

**Recommended direction:** Keep the current 12-minute / 24-fps / Z1–Z5 / S01–S16 product format, the D-124 G0–G8 approval workflow, the D-125 screenplay-first adaptive pacing principle, and D-126 tiered rule governance as the intended design, but first reconcile their conflicts with the executable implementation. Retain working modules; repair traceability and dead provider routes; add a clean-room YouTube viewer critic as an advisory G2 review. Do not restore the old v4.0 validator stack indiscriminately.

## 1. Snapshot and repository state

### Uploaded archive

The outer ZIP contains **134 entries** and several competing nested project bundles. Relevant files include:

- `explainer_engine_v4_1_cohesive_film_complete.zip`
- `explainer_engine_v4_2_cohesive_film_and_rules_bundle.zip`
- `explainer_engine_v4_2_hybrid_gemini_wan_complete.zip`
- `explainer-engine-main-d124-wan-chain.zip`
- `explainer-engine-main-d124-clean-final.zip`
- `explainer-engine-main-d124-gemini-arch.zip`
- `youtube_docudrama_12_component_3tier_rules_registry.zip`
- `batch_image_generator.py`, `batch_image_generator_v4_2.py`, `gemini_workflow.py`, `rule_enforcer.py` inside the nested source bundles
- production scripts, image queues, manifests, notebooks, rendered MP4s, reference images, and deprecated/obsolete files.

There is also an outer `env_config_v4.env` and `vault_secrets.json`. Their values were not read or disclosed. These files, all credentials, generated media and large reference assets must not be uploaded to GitHub as part of this audit.

The newest plausible working set is `explainer_engine_v4_2_hybrid_gemini_wan_complete.zip` combined with the D-126 cohesive-film/rules overlay and the 12-component registry bundle. However, the overlay adds D-129-labelled logic that is not recorded in the canonical decision log, so it is not safe to call the combined set a single approved release. Treat it as a candidate source set requiring a D-129 provenance/approval decision. This is not proof that every nested copy is byte-identical or mutually compatible. The top-level `Deprecated_Old_Robotic_Drafts/` names several older artifacts explicitly as obsolete, including pre-D127 bundles and fake slideshow material; those must not be treated as active production instructions.

### GitHub mismatch

The inspected repository is `vano1919/explainer-engine`. The branch `gemini/storytelling-system-rebuild-2026-11-09` is materially behind the uploaded archive:

- Its `docs/PROGRESS.md` ends with D-121-era work (2026-11-07).
- Its `docs/DECISIONS_AND_OPEN_QUESTIONS.md` does not contain D-123–D-127.
- `GEMINI.md` is not present on that branch.
- `explainer_engine/orchestration/cohesive_film_engine.py` is not present on that branch.
- The branch's `explainer_engine/llm/gemini_api.py` remains a deliberate stub; `complete()` raises `GeminiRefused` and no Gemini completion client is built.

Therefore, uploading a report to that branch does not mean the D-123–D-127 codebase is already present there. Do not claim the latest archive is deployed or merged. The audit/prompt can be published as additive planning documents on a new branch; actual code reconciliation remains separate.

## 2. Current decisions and architectural conflicts

### D-123 — baseline workflow

D-123 defines a 12-minute target (660–780 seconds), 24 fps, five phases Z1–Z5 and sixteen segments S01–S16. It begins with a local/free-default B→C workflow: approved 2D start frames, per-shot Wan 2.2 video, deterministic 2.5D motion for illustrations/maps, and 24-fps audio-spine assembly.

It retains a 70–80% narrator / 20–30% character-dialogue target and originally states a flexible 60/30/10 visual mix.

### D-124 — amendment and approval workflow

D-124 supersedes the D-123 image-engine choice: Gemini Native Image Engine becomes the sole image/keyframe generator and Qwen is retired from active production. It adds the G0–G8 creator-approval chain: reference/style lock, scenario, script, visual/audio storyboard, sound package, Gemini image generation, voice/audio spine, parallel 10%/30% plus 60% Wan production, and 3-minute review chunks.

This creates a material policy conflict with D-123's “100% local and free default”: G5 uses Gemini API and G7 specifies Wan on Modal GPU. The two statements cannot both mean that the entire default pipeline is local and free. The implementation plan must define which stages are local, which are hosted/paid, which are opt-in, and which approval/spend gates protect each. No paid work should start until that boundary is explicit.

### D-125 — screenplay-first pacing

D-125 changes the ratio guardrails to 50–70% video, 20–40% collage, 5–20% map, with 65–85% narrator and 15–35% dialogue. It rejects rigid per-segment quotas and requires variable, story-led durations. It describes shot duration bounds of 1.5–8.5 seconds with standard deviation at least 0.65 seconds; segment duration standard deviation at least 3 seconds; anti-boilerplate and anti-cookie-cutter checks. `frame[-5]` is only for a single continuous video shot longer than five seconds.

This supersedes the older rigid 60/30/10 and 70/30 framing where applicable. The old `docs/YOUTUBE_MASTER_MANUAL_ARGON_VS_FLASH.md` still contains 12-segment language and hard-coded pacing guidance, which conflicts with the D-123 sixteen-segment model and D-125's adaptive-pacing decision.

### D-126 — three tiers and four levels

D-126 separates:

- Tier 1: applicable invariants (hard FAIL);
- Tier 2: story-bounded ranges/distributions (story chooses the value inside the allowed bounds);
- Tier 3: thematic/style guidance (advisory REVIEW).

The four audit levels are text/script, audio/soundscape, video/visuals, and editing cohesion. This is the right governance model in principle. It does not mean every historic rule remains active, nor that every registry row is already enforced by code.

### D-127 — batch image worker

D-127 adds a resumable batch generation worker, per-image ledger checkpointing, validation before skipping existing images, and transient-error retry/backoff. These are useful operational concepts. The specific primary model `imagen-3.0-generate-002` is no longer viable and must be replaced only after official model/SDK verification and an approved test.

### Post-D-126 overlay — D-129-labelled changes require review

The separate `explainer_engine_v4_2_cohesive_film_and_rules_bundle.zip` is not just a registry copy. Compared with the hybrid bundle, its `cohesive_film_engine.py` adds three catalog rows and a `verify_real_api_media_renders()` function; its `shot_prompt_lint.py` adds `YT-00-3SEC-KINETIC-HOOK`; and it includes `scripts/run_2min_pilot_real_apis.py`.

These additions are labelled D-129 in code/comments, but no D-129 entry was found in the supplied canonical `DECISIONS_AND_OPEN_QUESTIONS.md`. Do not treat them as approved policy until the decision is recorded and the code/test scope is reconciled.

Specific concerns:

- The hook check looks for kinetic verbs in action/prompt text. It does not inspect actual generated video frames or prove that the rendered opening is visually kinetic. It requires shot 1 <= 2.4 seconds and shots 1+2 <= 4.6 seconds, despite the rule's “0–3 sec” title and some text describing a 3–3.5-second window. The exact metric/window needs one canonical definition.
- The overlay's `PV-THREE-TIER-VIDEO-ROUTING-LAW` routes 10% maps and 30% collages through `veo-2.0-generate-001` / FAL light video, while D-123 says deterministic 2.5D and D-124 defines Gemini stills plus the 10%/30% thread. This is a direct routing conflict, not a rule to add automatically.
- The overlay's `verify_real_api_media_renders()` is called by the special 2-minute pilot runner, not by the standard `rule_enforcer.run_all_gate_audits()` path. No D-129-specific test file was found in that overlay.
- Its checks are heuristics, not forensic proof: a high-bitrate re-encoded slideshow can pass; a synthetic stereo track can pass; pixel variance can misclassify legitimate dark images; a receipts JSON file is only checked for existence rather than content/provenance; and a missing/unreadable video path or failed `ffprobe` can avoid adding a failure. The function should not be described as proving real API origin. Preserve the anti-fake-render objective, but design verifiable receipts/hashes/provider job IDs and explicit missing/unreadable-file failures with tests.

Google's official deprecations page also lists `veo-2.0-generate-001` as shut down on 2026-06-30, so the overlay's Veo 2 route is unusable through that Gemini API endpoint.

## 3. Sample production script — structural measurements only

The outer archive's `ep_toba_74000bce_12min_production_script.json` was parsed without invoking any paid service or changing the file. Its measured structure is:

- Runtime: **719.8 seconds** (close to the 720-second target); 24-fps schema v4.0.0.
- **138 shots**, **12 segments**, **5 phases**, **138 audio lines**.
- Shot durations: 1.8–7.8 seconds; mean 5.22 seconds; population standard deviation 1.63 seconds.
- Segment durations: mean 60 seconds; population standard deviation 16.89 seconds.
- Average audio line length: 15.41 words; standard deviation 5.78; maximum 25 words.
- Narrator/character audio duration: 553.3/166.5 seconds, approximately **76.9%/23.1%**.
- Visual mix by shot count: approximately **60.1% cinematic video / 29.7% composed illustration / 10.1% map**.
- Visual mix by shot duration: approximately **56.9% cinematic video / 30.6% composed illustration / 12.5% map**.
- First two shots are Wan cinematic video at 1.8 and 2.2 seconds; their action text includes running/detonation. This satisfies the visible structural conditions of the D-129 hook rule, but it does not prove the rendered media actually shows those actions.

These metrics sit inside D-125's published shot-duration, variability, spoken-line and broad visual-mix bands. That is a useful sign of structural alignment, not proof of narrative quality, historical accuracy, actual media quality, or a full validator pass.

The main unresolved schema/decision mismatch is the **12 segment** count in this script versus D-123's described canonical **16 segment** structure. Do not automatically split or rewrite the sample. Confirm whether sixteen segments is a hard episode-wide contract or a target for a specific template/episode style, then add the right schema/test if needed. The separate Toba image queue requests 168 Gemini images for 138 shots, which appears to include distinct start/end images for some shots; inspect queue semantics and shot-level mapping before treating that as a duplication defect.

## 4. Implementation audit — documented coverage vs actual calls

### Rule enforcer call path

`explainer_engine/orchestration/rule_enforcer.py::run_all_gate_audits()` actually calls:

- `validate_reference_library`
- `story_lint.lint_v4`
- `scene_lint.lint_v4`
- `production.validate.check_script`
- `shot_prompt_lint.check_v4_script`
- `build_g4_audio_fx_plan`
- `build_gemini_generation_queue`
- `plan_parallel_g7_threads`
- `plan_3min_assembly_chunks`
- `check_cohesive_film_invariants_and_bounds`
- `build_cohesive_film_edl`

The function does **not** directly call a number of components its surrounding comments/coverage report imply are part of the gate execution, including `narration_lint`, `audio.layers.check`, `sound_director`, `motion_lint`, `rhythm_lint`, `qa.keyframe_gate`, `qa.frame_review`, or `qa.scorecard`. Some may be invoked by other CLI flows or later gates; those paths must be traced individually. Do not describe them as part of `run_all_gate_audits()` unless they are actually called.

`run_system_logic_check()` returns `cold_open_12s_hook_verified: True` as a literal, and `qwen_removed_gemini_native: True` as a literal. Those are not proofs. Its `segment_end_cliffhangers_count` is the number of segments, not the number of verified cliffhangers. Its visual-mix summary uses job counts, not verified timeline runtime. These fields are misleading unless replaced with actual measurements/assertions.

### Cohesive film engine gaps

`explainer_engine/orchestration/cohesive_film_engine.py::THREE_TIER_RULE_CATALOG` lists more rules than `check_cohesive_film_invariants_and_bounds()` enforces. The current checker directly checks a subset, including:

- shot duration hardcoded to 1.2–10.0 seconds;
- audio-to-shot duration divergence over 1.5 seconds;
- a minimum-length `screen_direction_notes` field on every shot;
- a specific adjacent-cut jump-cut condition;
- visual mix bounds;
- shot-size variety.

The code's shot-duration bound (1.2–10.0) conflicts with D-125's stated 1.5–8.5 range. The catalog also records mean/stdev targets for shot durations, sentence lengths and segment lengths, but the audit currently reports several of these as metrics rather than enforcing the declared bounds. Argon must distinguish “measured” from “gated”.

The current visual-mix calculation is based on the **number of shots**, not total timeline duration. A two-second map shot and a nine-second video shot each count once. This cannot validly be reported as a runtime share. Propose a duration-weighted calculation with explicit treatment for overlapping timelines, or state the exact limitation; do not change the implementation in this planning task.

The unconditional screen-direction-notes requirement may also create false positives for shots where an axis is not applicable. Confirm the schema and shot types before deciding whether it should become conditional. Do not weaken the rule without a test-backed applicability definition.

The EDL builder emits edit metadata and sets fields such as ambience-bed count, ducking enabled, LUT and grain. These are plan outputs, not proof the final media actually contains those effects. Add a separate media-level verification plan where needed.

### API worker

`explainer_engine/imagegen/batch_image_generator.py` still declares:

- `DEFAULT_IMAGEN_MODEL = "imagen-3.0-generate-002"`
- `DEFAULT_GEMINI_IMAGE_MODEL = "gemini-2.0-flash-preview-image-generation"`

It uses `client.models.generate_images(...)` for Imagen and `client.models.generate_content(...)` for the Gemini multimodal path. The queue/ledger/resume/backoff design may be reusable, but both model assumptions and exact SDK compatibility must be checked against current official documentation. The 4.5-second fixed request delay does not replace dynamic project/model quota management. The Gemini 2.0 image fallback `gemini-2.0-flash-preview-image-generation` is also listed as shut down on 2025-11-14.

## 5. Current Google API viability

Official Google documentation checked on 2026-11-11:

- [Gemini API deprecations](https://ai.google.dev/gemini-api/docs/deprecations) lists `imagen-3.0-generate-002` as shut down on **2025-11-10**. D-127's hardcoded primary model is therefore obsolete.
- The same deprecations page lists the Veo 3.1 preview model IDs (`veo-3.1-generate-preview`, `veo-3.1-fast-generate-preview`, `veo-3.1-lite-generate-preview`) as shut down on **2026-10-22**, and lists `veo-2.0-generate-001` as shut down on **2026-06-30**. The original prompt's `veo-3.1-*-generate-001` names are not a viable current production contract either. The page recommends `gemini-omni-1.2-flash` for the retired Veo 3.1 preview routes, but a replacement entry does not by itself prove equal feature support or quality for this pipeline.
- Google's [rate limit documentation](https://ai.google.dev/gemini-api/docs/rate-limits) says quotas vary by project/model/tier and are expressed across RPM, TPM and RPD; the current project quota must be inspected rather than hardcoding a universal 50 RPM. Rolling 10-minute spend caps vary by tier (the documented Tier 1 cap is $10 per 10 minutes, Tier 2 $50, Tier 3 $200).

Do not blindly substitute a guessed replacement for Veo or Imagen. Verify the currently supported model ID, output modality, image/reference capabilities, SDK method and pricing; then benchmark a small representative sample behind the creator's approval and cost cap. Keep Wan 2.2 routing separate from image generation and do not reintroduce Veo just because it was in the old prompt.

## 6. Tests and verification evidence

Executed against the extracted v4.2 hybrid bundle with the D-126 cohesive/rules overlay:

- `tests/unit/test_cohesive_film_3tier_engine.py`: **3 passed**, with one Python `SyntaxWarning` in `wan_optimizer.py`. The test file is from the hybrid bundle; it does not test the additional D-129 hook or media-verification logic in the overlay.
- Full suite collection: **blocked** before execution. The first collection failures reference the missing fixture `examples/stone_age/day1_v6/world_spec.json` imported by `tests/unit/test_production_script.py`. Running with `--maxfail=2` stopped on two collection errors; the full suite was not verified. A separate import error was also observed in the broader run in `tests/unit/test_youtube_publish.py` (`cannot import name 'route' from explainer_engine.imagegen.routing`).

Therefore the accurate report is: the focused D-126 tests pass; the full suite is not currently verified because test collection is blocked by missing/mismatched repository assets/imports. Do not state “all tests pass”. Restore the correct tracked fixtures/import contract or adjust tests to the intended package layout in a separate implementation task, then run supported full CI.

## 7. Gemini YouTube audience-review layer

The current `.claude/agents/script-critic.md` is not a pure audience-only reviewer: it reads project context, story references, claim maps, technical/editorial lint outputs, and script artifacts. It is useful as a broader critic, but it does not satisfy the requested blind first-time-viewer test.

The new `youtube_viewer_critic` should run in a fresh context and receive only:

- title/thumbnail concept if supplied;
- one-sentence promise/logline;
- intended audience and runtime;
- concise premise/what-if setup;
- readable script split into stable segment/line IDs and approximate timestamps.

It must not receive schemas, source registries, production prompts, validator reports, architecture documents, writer intent, prior critiques, or technical implementation constraints. It should evaluate curiosity, clarity, stakes, cause-and-effect, agency, escalation, reversals, pacing, repetition, emotion, setup/payoff, and ending satisfaction. It must cite exact line/segment IDs, identify likely attention-loss moments, and recommend the smallest high-impact story fixes.

It must not fact-check historical claims or assess technical production feasibility. It must not predict CTR, retention, or virality. Its report is advisory REVIEW only and must not be averaged into technical QA. Keep the existing `script-critic` and deterministic validators; the viewer critic is an independent extra lens, not a replacement.

The current `explainer_engine/llm/gemini_api.py` is a stub whose `complete()` method raises `GeminiRefused`. Therefore this agent is a design proposal, not a live capability. A future implementation requires a verified Gemini client, the existing spend-cap/ledger integration, strict packet schema, context-isolation tests, retry/error handling, privacy controls, and a test proving that no repository or lint context reaches the reviewer.

## 8. Keep / change / remove

| Area | Keep | Change | Do not do |
|---|---|---|---|
| Canonical script | One `production_script.json` SSOT and schema validation | Reconcile exact schema version and stage contracts | Create parallel script sources |
| Approval process | Creator approval gates and reviewable 3-minute chunks | Reconcile G0–G8 with local/hosted cost boundaries | Replace with old 4-step Colab by assumption |
| Rules | D-126 three-tier governance; canonical rule IDs | Trace each rule to actual call path + tests; align D-125 bounds | Reactivate every BP/KP/ST/SC/PV rule as hard FAIL |
| Pacing | Screenplay-first accordion pacing | Align code and docs on bounds; duration-weight mix | Force metronomic duration/ratio quotas |
| Image generation | Gemini image engine as the current D-124 decision | Replace obsolete model IDs only after official verification; add evidence-backed provider receipts | Use Imagen 3 or old Veo 3.1/Veo 2.0 names |
| Video generation | Per-shot Wan 2.2 route, selective control | Verify checkpoint, wrapper, job schema, local/Modal spend boundary; resolve unapproved D-129 routing overlay | Add dead Veo 2.0/3.1 endpoints as a default |
| Audio | Existing voice/audio spine and sound planning | Distinguish cue plans from rendered-audio QA | Claim DSP/mix is implemented because EDL flags say so |
| YouTube story QA | Existing `script-critic` and lints | Add blind `youtube_viewer_critic` as advisory G2 review | Give this agent the whole repository or technical reports |
| GitHub | Existing history/branches | Publish only audit/planning docs on an isolated branch | Upload the full ZIP, secrets, MP4s, or overwrite `main` |

## 9. Priority implementation plan for Codex (after approval)

### P0 — establish canonical baseline and safety

1. Select one coherent source snapshot; capture SHA-256 and source/ref manifest.
2. Reconcile the archive and GitHub branch; preserve all existing branches and main history.
3. Decide whether to approve or reject the D-129 overlay, and record its provenance/decision before enabling it.
4. Remove stale API model IDs from active config only after current replacement and migration tests are approved.
5. Define the actual local/hosted/paid boundary and route-specific spend/creator approval gates.

**Acceptance:** one repeatable baseline and no production route using a shut-down model ID; no paid job can start without preflight and explicit approval.

### P1 — repair rule traceability and actual enforcement

1. Generate a machine-readable rule coverage report from the 12 registries, sourced-rules registry, schema, validator call graph and tests.
2. Resolve D-125/D-126 shot-duration mismatch and all other documented/code threshold drift.
3. Change the visual mix audit to a justified duration-weighted metric (with overlap semantics) or label it clearly as shot-count composition.
4. Replace hardcoded truth values and counts in `run_system_logic_check()` with real validation results.
5. Add positive/negative and non-applicable-context fixtures for every active enforced Tier 1/Tier 2 rule.
6. Wire missing validators only after confirming they remain active and compatible with the schema; do not duplicate checks.

**Acceptance:** no claimed coverage without a real call path and test; all Tier 1/2 enforcement behavior traceable and reproducible; Tier 3 remains advisory.

### P2 — restore deterministic testability

1. Restore the intended `examples/stone_age/day1_v6/world_spec.json` fixture or replace broken test imports with the current fixture contract.
2. Fix the `imagegen.routing.route` import mismatch if the symbol was renamed/retired.
3. Run targeted tests, full supported Linux CI, docs lint, schema validation, and one end-to-end offline/dry-run path.

**Acceptance:** a fresh checkout can collect and execute the supported test suite without relying on untracked local assets.

### P3 — add the viewer critic

1. Define `viewer_review_packet` schema and the context-isolated agent prompt.
2. Add a separate G2 audience-review artifact; preserve technical `script-critic` and validators.
3. Implement Gemini API access only after verifying current model/client and hooking the existing spend cap/ledger.
4. Add tests proving packet minimization, no technical context leakage, stable ID citations, advisory-only status, and graceful failure when Gemini is unavailable.
5. Calibrate against independent human reviews and later actual analytics; do not set a hard score threshold prematurely.

**Acceptance:** the reviewer receives only the allowed packet, returns evidence-linked audience observations, never performs technical QA, and cannot block production autonomously.

### P4 — media-level verification and pilot

1. Verify actual generated images, video clips, audio files, sync, frame rate, continuity, and chunk seams—not just plans/manifests.
2. Run an approved 60-second/12-shot representative pilot first; measure generation time, retry rate, identity/continuity, accepted-shot rate, actual runtime mix, and total cost.
3. Only promote a route after the agreed human visual/audio review. Expand to the first full episode only after the pilot passes.

**Acceptance:** a reviewable real clip and evidence report, with explicit creator approval before scaling or publishing.

## Final recommendation

Do not execute the pasted v4.1 prompt. Use the evidence-first Argon handoff instead. The current system has useful direction and real code, but the rulebook, executable gate coverage, provider IDs, and GitHub snapshot are not yet in sync. Fix those inconsistencies before any large production generation. Keep the YouTube viewer critic separate and advisory: it should challenge whether the story is worth watching, not whether the pipeline can render it.