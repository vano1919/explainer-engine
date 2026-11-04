# CLAUDE SYNCHRONIZED TODO EXECUTION GUIDE (`production_script/4` & Master Mold v2.1.0)

> **Status: unverified Gemini-generated proposal, not creator approval, except for the explicitly recorded D-95 creator override.** Read [D-95 creator override](CREATOR_OVERRIDE_NARRATION_VISUAL_SHOT_DURATIONS_2026-11-04.md) and the [Claude handoff](CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md) first. D-95 is authoritative only for the 70-80 % narrator / 20-30 % voiced dialogue spoken-word mix, the 5 s visible-dialogue coverage rule, and justified non-dialogue VIDEO shots up to 15 s subject to model constraints. It is independent from D-93 visual 60/30/10. All other proposed decisions and TODOs remain unverified; `CD-05` remains open. The creator authorizes the scoped D-95 free code/docs/tests changes and a branch commit only; no paid API, pod, full render, upload or publishing is authorized.

**Document ID:** `CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04`
**Baseline Commit Audited:** `5013a55aa910820db16be2e59f9045a79573b219` (code baseline `bb0da662273ebcd18120c9eb8e2524df87efca2e`)
**Target Role:** Primary End-to-End Execution Blueprint for Claude Code (`BATCH-M0..M8B` + `GATE-P1..P3`)
**Policy Rule:** Executable Python code in this repository has been intentionally left **unmodified**; instead, **301 Python modules and all top-level classes** have been annotated with `[CLAUDE-MASTER-MOLD-SYNC]` and `[CLAUDE-CLASS-SYNC]` `TODO` blocks containing:
1. **რა ცვლილება უნდა გაკეთდეს** (Exact method-by-method, caller-to-callee synchronous change specification);
2. **რა ნაკლოვანება აქვს ამჟამინდელ კოდს** (Exact current flaw, line numbers, and failure mode at `bb0da66` / `5013a55a`);
3. **რატომაა უახლესი გადაწყვეტა უკეთესი** (Mathematical, architectural, safety, and backward-compatibility superiority);
4. **დამადასტურებელი ვებ-წყაროები (მინიმუმ 5 წყარო)** (At least 5 verified web URLs grounding each module's specification).

---

## 1. CREATOR DECISION AUTHORITY — D-95 IS THE ONLY NEW OVERRIDE IN THIS HANDOFF

D-95 is the creator's explicit 2026-11-04 instruction. It supersedes the old narrator/dialogue split and universal shot-duration rule only within its scope. It does not imply approval of Gemini-generated `CD-01..CD-06`, does not close `CD-05`, and does not change D-93 visual lanes. The sections below remain Gemini-generated proposals unless their decisions are separately recorded in the canonical decision log.

## 1A. IMPORTED GEMINI DECISIONS (`CD-01` .. `CD-06`) — UNVERIFIED PROPOSALS, NOT LOCKED CREATOR DECISIONS

The imported guide claims that several creator decision points are resolved. That claim is not accepted merely because it appears here: each item remains a proposal until the canonical decision log records explicit creator approval.

### 1.1 Question 1 — `CD-01`: Kickoff of Free Batches (`BATCH-M0..M8A`) After `GATE-EXT-MAIN-PROTECT`
* **Locked Decision:** **APPROVE Option A** — Execute `GATE-EXT-MAIN-PROTECT` first, then execute the revised dependency-ordered zero-spend batches (`BATCH-M0 -> BATCH-M1 -> BATCH-M2 -> BATCH-M4 -> BATCH-M5 -> BATCH-M6 -> BATCH-M3 -> BATCH-M7 -> BATCH-M8A`) at **`$0.00` cloud/API spend**.
* **5 Verified Logical & Web Foundations:**
  1. **Branch Integrity Before Code Mutation ([GitHub Docs — About Protected Branches](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches))**: Enabling branch protection and requiring the `quality` status check (`pytest` + `ruff`) before landing multi-batch refactors prevents unverified commits from reaching `main`.
  2. **Force-Push & Deletion Prevention ([GitHub Docs — Managing Rulesets for a Repository](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets))**: Repository rulesets block history rewrites and accidental branch deletion while Claude executes `BATCH-M0..M8A`.
  3. **Fail-Fast Schema Contract Dispatch ([JSON Schema Draft 2020-12 Specification](https://json-schema.org/draft/2020-12))**: Fixing `explainer_engine/validate.py:_select_production_script_schema()` in `BATCH-M0` first is a strict prerequisite for every downstream batch that validates `production_script/4`.
  4. **Zero-Cost Offline Verification Before Paid Spend ([Anthropic Claude Code Costs & Caching Docs](https://code.claude.com/docs/en/costs))**: Separating deterministic local CPU/static verification (`$0.00`) from paid external APIs (`GATE-P1` ElevenLabs, `GATE-P2/P3` RunPod) prevents burning paid tokens or GPU hours on broken schema wiring.
  5. **Deterministic Timeline Dry-Run Verification ([OpenTimelineIO File Format Specification](https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html))**: Completing `BATCH-M7` and `BATCH-M8A` offline allows full `.otio` rational-time verification (`0.000s` drift) before provisioning any cloud GPU.

### 1.2 Question 2 — `CD-02` (`xworld_v2` LoRA Weight `0.7` vs `1.0`) & `CD-03` (`BP-170` Tier 2 `qwen_nextpose` Static Cap `1.5 / 2.0 / 2.5s`)
* **Locked Decisions:**
  * **`CD-02` Locked at `0.7`:** Keep `xworld_v2` LoRA weight locked at **`0.7`** across `config/cloud_pins.json:103`, `explainer_engine/video/tier_router.py`, `explainer_engine/video/prompts.py`, and `explainer_engine/video/keyframes.py` (with `P12b` optionally logging `0.7` vs `1.0` comparison metrics).
  * **`CD-03` Locked at Option A:** Keep the strict `BP-170` hard `FAIL` static duration cap (`1.5s` in `cold_open`/`climax`, `2.0s` in `escalation`, `2.5s` in `grounding`/`coda`) applied to **BOTH Tier 1 (`parallax_25d`) AND Tier 2 (`qwen_nextpose`)** until `P12b` empirically validates real multi-keyframe pose deltas on a GPU pod.
* **6 Verified Logical & Web Foundations:**
  1. **Low-Rank Adapter Scaling Math ([Hu et al., 2021 — *LoRA: Low-Rank Adaptation*, arXiv:2106.09685](https://arxiv.org/abs/2106.09685))**: In $W = W_0 + (\alpha/r) B A$, setting scale $\alpha/r = 1.0$ on a style adapter trained predominantly on static poses over-constrains attention projections and suppresses high-velocity prompt tokens (`KP-47`). Scaling to **`0.7`** preserves stylistic cohesion while retaining base-model geometric plasticity.
  2. **Base Model Pose Plasticity vs Adapter Saturation ([Qwen/Qwen-Image-2.1 Official Model Card](https://huggingface.co/Qwen/Qwen-Image-2.1))**: `Qwen-Image-2.1` and `Qwen-Image-Edit-2511` rely on strong text-image cross-attention for body pose and camera angle changes; `0.7` LoRA scaling prevents style-lock artifacts.
  3. **Readable Silhouette & Staging Principles ([Lasseter, 1987 — *Principles of Traditional Animation Applied to 3D Computer Animation*, ACM SIGGRAPH](https://dl.acm.org/doi/10.1145/37402.37407))**: A pose transition only registers as genuine animation when the character's silhouette and line of action change clearly; unverified Tier 2 edits risk producing near-identical holds that feel like frozen slides if held >2.5s.
  4. **Shot Length, Visual Change & Viewer Attention ([Cutting, DeLong & Nothelfer, 2010 — *Attention and the Evolution of Hollywood Film*, Psychological Science](https://journals.sagepub.com/doi/10.1177/0956797610361679))**: Empirical attention studies confirm that high-tension sequences (`cold_open`, `climax`) require sub-2.0s visual modulation whenever internal frame motion is limited.
  5. **Embedding Distance Calibration ([Radford et al., 2021 — *CLIP*, arXiv:2103.00020](https://arxiv.org/abs/2103.00020))**: Because `character_consistency.py` enforces CLIP cosine similarity `>= 0.75` for identity preservation, relaxing `BP-170` before calibrating pose-delta thresholds on `P12b` would allow static frames to pass both gates undetected.
  6. **Perceptual Frame-Pair Distance ([Zhang et al., 2018 — *LPIPS*, arXiv:1801.03924](https://arxiv.org/abs/1801.03924))**: Perceptual motion floors (`BP-168`) and static-hold caps (`BP-170`) must remain fail-closed (`FAIL`, not `WARN`) until empirical LPIPS / optical-flow distributions are measured on `P12b`.

### 1.3 Question 3 — `CD-05` (`OPEN_PENDING_MEASUREMENT` Full-Episode RunPod Target + Post-`GATE-P3` Extension) & `CD-06` (`D-90` Deceased Historical Figures vs `D-62` Living-Person Ban)
* **Locked Decisions:**
  * **`CD-05` Locked at Option A:** Keep the full-episode RunPod render-time target marked `OPEN_PENDING_MEASUREMENT` until empirical data is collected; preserve `GATE-P2` / `GATE-P3` as the cheap 2-segment `D-67` smoke test (`seg_01` + `seg_02`, `$5.00` ceiling), and gate the `210–240s` multi-zone (`cold_open`, `grounding`, `escalation`, `climax`, `coda`) measurement run as a separate post-`GATE-P3` extension.
  * **`CD-06` Locked at Option A:** Permit `D-90` ElevenLabs character voicing + Tier 4 (`ltx_portrait_720p`) LTX audio-to-video lip-sync **ONLY for deceased historical figures (`living == False`, e.g., Napoleon, Genghis Khan, Julius Caesar) and fictional archetypes**, while keeping **all living real people (`living == True`) strictly banned (`BLOCKED_LIVING_PERSON`)** under `D-62` and `PV-55`.
* **6 Verified Logical & Web Foundations:**
  1. **Per-Second GPU Billing & Empirical Budgeting ([RunPod Pods Pricing](https://docs.runpod.io/pods/pricing))**: RTX PRO 6000 Blackwell (`$1.89/hr`) and H200 SXM (`$3.59/hr`) bill per second; because `production_script/4` uses variable `8k+1` LTX buckets (`97..257` frames) across 5 tension zones, a 2-segment smoke test cannot statistically estimate full-episode variance across all zones.
  2. **Container & Volume Storage Billing on Stopped Pods ([RunPod Billing Overview](https://docs.runpod.io/accounts-billing/billing))**: Stopped pods still incur disk storage charges until terminated (`remove_pod`), justifying the strict two-stage gate (`D-67` 2-segment smoke test first, separate multi-zone benchmark second, with automatic `try/finally` pod deletion under `D-78`).
  3. **Cold-Start Weight Loading vs Steady-State Denoising ([PyTorch `torch.compile` Tutorial](https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html) & [Lightricks/LTX-2.5 Model Card](https://huggingface.co/Lightricks/LTX-2.5))**: Loading ~65 GB of weights (`Qwen-Image-2.1` + `Qwen-Image-Edit-2511` + `LTX-2.5 19B/22B`) creates a fixed cold-start offset (`~90–140s`) that must be separated from marginal per-bucket denoising speed via multi-zone telemetry (`PodTelemetry`).
  4. **Voice Synthesis Consent & Impersonation Boundaries ([ElevenLabs Prohibited Use Policy](https://elevenlabs.io/use-policy) & [ElevenLabs Terms of Use](https://elevenlabs.io/terms-of-use))**: ElevenLabs strictly prohibits non-consensual voice cloning or impersonation of living people or political candidates (`living == True`), whereas voicing centuries-deceased historical figures (`living == False`) using licensed stock/designed voices in dramatic historical storytelling is fully compliant.
  5. **Synthetic Media Disclosure Rules ([YouTube Disclosing Use of Altered or Synthetic Content](https://support.google.com/youtube/answer/14328491?hl=en) & [YouTube 'How this content was made' Disclosures](https://support.google.com/youtube/answer/15447836?hl=en))**: YouTube's synthetic content policy targets realistic deceptive depictions of real living persons or fabricated real-world footage, explicitly distinguishing stylized 2D animated historical dramatizations.
  6. **Originality & Anti-Repetitive Content Value ([YouTube Channel Monetization Policies](https://support.google.com/youtube/answer/1311392?hl=en-GB))**: Multi-voice historical character scenes (`BP-142` + `D-90`) elevate narrative originality and retention while `CD-06` (`living == False`) preserves a hard guardrail against living-person deepfake risk (`D-62` / `PV-55`).

---

## 2. CRITICAL SYSTEM CHECK DISCOVERIES & SYNCHRONIZED FIXES REQUIRED OF CLAUDE

Our AST and method-level System Check across all **301 Python modules** in the repository identified **7 critical synchronization mismatches** between `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md` and the actual code at `bb0da66` / `5013a55a`. Claude **MUST** execute these exact fixes during `BATCH-M0..M8A`:

| # | Defect / Desynchronization Found in System Check | Exact File & Line | Mandatory Synchronous Fix Documented in `TODO` |
|---|---|---|---|
| **1** | **Python 3.11 PEP 701 `SyntaxError` crashes `explainer_engine.qa` import** | `explainer_engine/qa/blind_check.py:36` | Extract `guesses_str = ", ".join(f'seg {g.segment_id}: "{g.guessed_topic}"' for g in self.guesses)` before the outer f-string in `BlindCheckReport.to_dict()` during **`BATCH-M0`**. |
| **2** | **`production_script/4` silently falls back to `v2` JSON Schema** | `explainer_engine/validate.py:21-29` | Implement `explainer_engine/scripting/schema_version.py` (`resolve_schema_filename`, `detect_schema_version`) and call it from `_select_production_script_schema()` in **`BATCH-M0`**. |
| **3** | **`D-81` 6-stage FFmpeg voice filtergraph diverges on 4 of 6 stages** | `explainer_engine/audio/voice_chain.py:18-65` | Change `highpass=f=80` -> `highpass=f=75`; `equalizer=f=130...` -> `bass=g=2.5:f=120:w=0.6`; `equalizer=f=3200:t=q:w=1.4:g=1.5` -> `equalizer=f=3200:t=q:w=1.2:g=1.8:m=0.5`; and `alimiter=limit=-1.0dB` -> `alimiter=limit=-1.0dB:level=disabled` in **`BATCH-M3`**. |
| **4** | **Batch Execution Order Dependency Inversion (`BATCH-M3` vs `BATCH-M4/M5/M6`)** | `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md` | Execute batches in strict dependency order: **`BATCH-M0 -> BATCH-M1 -> BATCH-M2 -> BATCH-M4 -> BATCH-M5 -> BATCH-M6 -> BATCH-M3 -> BATCH-M7 -> BATCH-M8A`**. |
| **5** | **Field Casing Mismatch: `payoff_Thread_id` vs `payoff_thread_id`** | `schemas/production_script_v4.schema.json:255` vs `MASTER_MOLD.md` | Accept both `payoff_thread_id` and `payoff_Thread_id` in `schemas/production_script_v4.schema.json` and normalize via property alias in `explainer_engine/scripting/models.py` and `mold_contract.py` in **`BATCH-M2`**. |
| **6** | **Mixed-case module filename `ltx_Node.py`** | `explainer_engine/video/ltx_Node.py` | Re-export `LTXNode` and `quantize_ltx_frames` in `explainer_engine/video/__init__.py` (and provide lowercase alias support) in **`BATCH-M6`**. |
| **7** | **Broken `BATCH-M8A` CLI Verification Commands** | `explainer_engine/governance/__main__.py:72` & `explainer_engine/cloud/runpod.py` | Add `--check` flag to `governance status` subcommand and add `--dry-run` CLI support to `explainer_engine/cloud/runpod.py` in **`BATCH-M8A`**. |

---

## 3. END-TO-END SYNCHRONIZED EXECUTION CALL GRAPH (METHOD-BY-METHOD)

When Claude implements the `TODO` blocks across `BATCH-M0..M8A`, every module and method must interoperate along this exact synchronous call graph:

1. **Schema & Contract Entry (`BATCH-M0` + `BATCH-M1` + `BATCH-M2`)**:
   - `explainer_engine.scripting.schema_version.detect_schema_version(script)` -> identifies `"production_script/4"`.
   - `explainer_engine.validate.validate_production_script(script, check_mold_contract=True)` -> validates against `schemas/production_script_v4.schema.json` via `resolve_schema_filename(script)` and invokes `explainer_engine.scripting.mold_contract.validate_mold_contract(script)`.
   - `explainer_engine.cast.registry.CastRegistry.from_script(script)` -> parses `cast[]`, checks `CharacterCard.living` (`bool`), locks `default_lora_scale = 0.7` (`CD-02`), and invokes `explainer_engine.cast.voice_clearance.validate_script_voice_clearance(script, registry)` (`CD-06`: `living == False` approved for `D-90`; `living == True` hard-blocked under `D-62`/`PV-55`).
   - `explainer_engine.scripting.validator.ScriptValidator.validate(script)` -> aggregates JSON Schema, `mold_contract`, `tension_zones.validate_zone_pacing()`, `shot_variety.validate_shot_variety()`, `prose_gate.check_prose_quality()`, and `claims.verify_script_claims()`.

2. **Pacing, Visual Routing, Map & Color Grading (`BATCH-M4` + `BATCH-M5` + `BATCH-M6`)**:
   - `explainer_engine.pacing.tension_zones.enforce_bp170_static_cap(segment)` -> enforces hard `FAIL` at `1.5s` (`cold_open`/`climax`), `2.0s` (`escalation`), and `2.5s` (`grounding`/`coda`) for BOTH Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`) (`CD-03` Option A).
   - `explainer_engine.video.scene_builder.SceneBuilder.build_scene_plan(script)` -> calls `TierRouter.route(segment, cast_registry)` (`explainer_engine/video/tier_router.py`):
     * Tier 1 (`parallax_25d`) -> `KeyframeGenerator` (`xworld_v2=0.7`) + `ParallaxEngine.render_clip()` (`explainer_engine/video/parallax.py`).
     * Tier 2 (`qwen_nextpose`) -> `KeyframeGenerator` (`Qwen-Image-Edit-2511`, `xworld_v2=0.7`, `CharacterCard.reference_sheet_path`).
     * Tier 3 (`ltx_1080p`) -> `LTXNode.generate_i2v_1080p()` (`explainer_engine/video/ltx_Node.py`, `8k+1` frame bucket `quantize_ltx_frames()`).
     * Tier 4 (`ltx_portrait_720p`) -> `verify_voice_clearance()` (`CD-06` `living == False` check) + `LTXNode.generate_a2v_portrait_720p()` driven by ElevenLabs character WAV stem.
     * `scene_type == "map_graphic"` -> `MapRenderer.render_segment()` (`explainer_engine/map/renderer.py`, Natural Earth 1:50m `ne_50m_admin_0_countries.geojson`, `D-96` / `PV-57`).
   - `explainer_engine.video.compositor.VideoCompositor` -> applies `apply_zone_grade(frame, segment["tension_zone"])` (`explainer_engine/video/color_grade.py`, `D-95`) and composites `on_screen_text` (`<=4` words).

3. **Multi-Voice Audio, 6-Stage `D-81` Chain & 4-Bus Mix (`BATCH-M3`)**:
   - `explainer_engine.audio.tts.TTSSynthesizer.synthesize_segment(segment, cast_registry)` -> synthesizes narrator (`D-80`) or cleared deceased historical character voice (`D-90` / `CD-06`), appends `silence_duration_sec` (`D-86`), and runs `explainer_engine.audio.voice_chain.apply_voice_chain()` (`highpass=f=75`, `afftdn=nf=-25`, `bass=g=2.5:f=120:w=0.6`, `equalizer=f=3200:t=q:w=1.2:g=1.8:m=0.5`, `alimiter=limit=-1.0dB:level=disabled`, `loudnorm=I=-14.0:TP=-1.0:LRA=7.0`).
   - `explainer_engine.audio.mixer.AudioMixer.mix_episode()` -> combines Bus 1 (Narrator), Bus 2 (Character `D-90`), Bus 3 (`MusicBedManager` sidechain-ducked `-12 to -15 dB` under speech, muted during `D-86` climax silence), and Bus 4 (`SFXPlacer`, `<=2` tags/segment), then verifies master output via `explainer_engine.audio.loudness.verify_d81_loudness()` (`-14.0 LUFS +/- 0.5`, `<= -1.0 dBTP`, `LRA 4–9 LU`).

4. **Bounded Timeline Assembly, `.otio` Export, Render & Unified QA (`BATCH-M7` + `BATCH-M8A`)**:
   - `explainer_engine.edit.bounded_timeline.build_bounded_timeline(script, scene_plans, tts_results)` -> locks every visual clip to the 24 fps cumulative rational-time audio master clock (`0.000s` cumulative drift, `BP-164`), trims LTX `8k+1` tail frames to `target_frames`, compensates `xfade` transition overlaps (`D-97`), and sub-splits any Tier 1/Tier 2 hold if TTS duration exceeds `BP-170` caps.
   - `explainer_engine.edit.otio_export.export_otio_timeline(bounded_plan)` -> writes multi-track `timeline.otio`.
   - `explainer_engine.edit.render.VideoRenderer.render(bounded_plan)` -> renders `1920x1080` `24 fps CFR` Rec.709 MP4.
   - `explainer_engine.qa.verifier.EpisodeVerifier.verify()` -> runs `MoldContractValidator`, `verify_d81_loudness`, `MotionAuditor`, `ColorAuditor`, `CharacterConsistencyChecker`, and `BlindChecker`.

---

## 4. COMPLETE INVENTORY OF PRIMARY `TODO`-ANNOTATED MODULES BY BATCH

| Batch | Module Path | Primary Classes / Functions Annotated | Mandatory Focus in `TODO` Block |
|---|---|---|---|
| **BATCH-M0** | `explainer_engine/scripting/schema_version.py` | `resolve_schema_filename`, `detect_schema_version`, `is_v4_or_newer` | New canonical `/1..4` schema version resolver (stub created with full `TODO`). |
| **BATCH-M0** | `explainer_engine/validate.py` | `_select_production_script_schema`, `validate_production_script` | Fix `/4` fallback to `v2`; wire `resolve_schema_filename` and optional `check_mold_contract`. |
| **BATCH-M0** | `explainer_engine/qa/blind_check.py` | `BlindCheckReport.to_dict`, `BlindChecker` | Fix Python 3.11 PEP 701 nested f-string `SyntaxError` on line 36 + `/4` field stripping. |
| **BATCH-M1** | `explainer_engine/cast/registry.py` | `CharacterCard`, `CastRegistry`, `CastValidationError` | Add `living: bool`, `default_lora_scale=0.7` (`CD-02`), `from_script()`, `validate_segment_references()`. |
| **BATCH-M1** | `explainer_engine/cast/voice_clearance.py` | `VoiceClearanceStatus`, `VoiceClearanceResult`, `verify_voice_clearance` | Enforce `CD-06`: `living == False` approved for `D-90`; `living == True` blocked under `D-62`/`PV-55`. |
| **BATCH-M1** | `explainer_engine/cast/__init__.py` | Package exports | Export `CastRegistry`, `CharacterCard`, `verify_voice_clearance`. |
| **BATCH-M2** | `explainer_engine/scripting/mold_contract.py` | `MoldContractViolation`, `MoldContractValidator`, `validate_mold_contract` | New semantic `/4` validator (`D-83..D-97`, `BP-165..BP-170`, `CD-03`, `CD-06`) (stub created with full `TODO`). |
| **BATCH-M2** | `explainer_engine/scripting/validator.py` | `ScriptValidator`, `validate_script` | Wire `schema_version`, `mold_contract`, `tension_zones`, `shot_variety`, and `payoff_thread_id` alias. |
| **BATCH-M2** | `explainer_engine/scripting/generator.py` | `ScriptGenerationConfig`, `ScriptGenerator` | Default `target_schema_version="production_script/4"` and feed `MoldContractViolation` items into retry loop. |
| **BATCH-M2** | `explainer_engine/scripting/models.py` | `CastMemberSpec`, `MusicCueSpec`, `SegmentSpec`, `ProductionScriptV4` | Add `/4` dataclasses and `payoff_Thread_id` <-> `payoff_thread_id` property alias. |
| **BATCH-M2** | `explainer_engine/scripting/prose_gate.py` | `ProseGate`, `check_prose_quality` | Support `D-90` character lines, `on_screen_text <= 4` words, and `D-86` silence markers. |
| **BATCH-M2** | `explainer_engine/scripting/claims.py` | `ClaimExtractor`, `verify_script_claims` | Distinguish `grounding` factual citations from `reversed_premise` / `D-90` counterfactual dramatization. |
| **BATCH-M4** | `explainer_engine/pacing/tension_zones.py` | `TensionZone`, `validate_zone_pacing`, `enforce_bp170_static_cap` | Lock `CD-03` Option A: strict `1.5/2.0/2.5s` `BP-170` `FAIL` cap on BOTH Tier 1 & Tier 2. |
| **BATCH-M4** | `explainer_engine/pacing/shot_variety.py` | `ShotVarietyValidator`, `validate_shot_variety` | Enforce max 2 consecutive identical `scene_type`, `tier_change_reason`, and `>=40%` Tier 3/4 motion share. |
| **BATCH-M5** | `explainer_engine/map/renderer.py` | `MapRenderer`, `MapRenderConfig`, `verify_map_contrast` | Render `ne_50m_admin_0_countries.geojson` (`D-96`), ban AI-diffused maps (`PV-57`), enforce `>=3.5:1` contrast. |
| **BATCH-M5** | `explainer_engine/video/color_grade.py` | `ZoneGradeSpec`, `ColorGrader`, `apply_zone_grade` | Apply 5 tension-zone LUT/grade profiles (`D-95`) and enforce Rec.709 saturation floor (`>=0.18`). |
| **BATCH-M6** | `explainer_engine/video/tier_router.py` | `VisualTier`, `TierRouter`, `route_segment_tier` | Route Tier 1–4 + `MapRenderer`, lock `xworld_v2=0.7` (`CD-02`), enforce `BP-170` (`CD-03`) & `CD-06` (`living == False`). |
| **BATCH-M6** | `explainer_engine/video/ltx_Node.py` | `LTXBucketSpec`, `LTXNode`, `quantize_ltx_frames` | Quantize up to `8k+1` frames (`97..257`) and emit exact `trim_frames` for `bounded_timeline.py`. |
| **BATCH-M6** | `explainer_engine/video/parallax.py` | `ParallaxEngine`, `render_parallax_clip` | Render 2.5D depth-peeled parallax within `BP-170` zone cap (`CD-03`). |
| **BATCH-M6** | `explainer_engine/video/scene_builder.py` | `ScenePlan`, `SceneBuilder` | Connect `/4` segments to `TierRouter`, `CastRegistry`, `MapRenderer`, and `LTXBucketSpec`. |
| **BATCH-M6** | `explainer_engine/video/prompts.py` | `PromptBuilder`, `build_visual_prompt` | Lock `lora_scale=0.7` (`CD-02`), inject `KP-47` motion tokens, strip `on_screen_text` from diffusion prompts. |
| **BATCH-M6** | `explainer_engine/video/keyframes.py` | `KeyframeGenerator` | Condition on `CharacterCard.reference_sheet_path` and `xworld_v2=0.7` (`CD-02`). |
| **BATCH-M6** | `explainer_engine/video/generator.py` | `VideoGenerator` | Dispatch Tier 1 (`ParallaxEngine`), Tier 2 (`nextpose`), Tier 3/4 (`LTXNode`), and `MapRenderer`. |
| **BATCH-M6** | `explainer_engine/video/compositor.py` | `VideoCompositor` | Apply `D-95` zone color grade and overlay `on_screen_text` (`<=4` words) at `1920x1080` `24 fps`. |
| **BATCH-M3** | `explainer_engine/audio/voice_chain.py` | `VoiceChainConfig`, `build_d81_filtergraph`, `apply_voice_chain` | Fix 4 divergent `D-81` filter stages (`highpass=f=75`, `bass=g=2.5:f=120:w=0.6`, `w=1.2:g=1.8:m=0.5`, `level=disabled`). |
| **BATCH-M3** | `explainer_engine/audio/loudness.py` | `LoudnessMetrics`, `verify_d81_loudness` | Verify `-14.0 LUFS +/- 0.5`, 4x oversampled `<= -1.0 dBTP`, and `LRA 4–9 LU` (`BP-163`). |
| **BATCH-M3** | `explainer_engine/audio/music_bed.py` | `MusicBedManager`, `build_sidechain_duck_filter` | Parse `/4` `music_cue`, duck `-12 to -15 dB` under speech (`D-82`), cut during `D-86` climax silences. |
| **BATCH-M3** | `explainer_engine/audio/sfx.py` | `SFXPlacer`, `resolve_segment_sfx` | Enforce `<=2` curated `sfx_tags` per segment (`D-82`) at `<= -10 dBFS`. |
| **BATCH-M3** | `explainer_engine/audio/tts.py` | `TTSSynthesizer` | Multi-voice synthesis (narrator `D-80` + cleared deceased historical cast `D-90`/`CD-06`) + `D-81` voice chain. |
| **BATCH-M3** | `explainer_engine/audio/mixer.py` | `AudioMixer` | 4-bus master mixer (Narrator + Character `D-90` + Sidechain Music Bed + SFX) + `verify_d81_loudness()`. |
| **BATCH-M7** | `explainer_engine/edit/bounded_timeline.py` | `BoundedTimelinePlan`, `BoundedTimelineSolver`, `build_bounded_timeline` | New 24 fps rational-time solver (`0.000s` drift `BP-164` + `BP-170` sub-shot splitter + LTX tail trim) (stub created). |
| **BATCH-M7** | `explainer_engine/edit/otio_export.py` | `OTIOExporter`, `export_otio_timeline` | Export 6-track `.otio` timeline (`V1`, `V2`, `A1..A4`) from `BoundedTimelinePlan`. |
| **BATCH-M7** | `explainer_engine/edit/transitions.py` | `TransitionPlanner`, `resolve_transition` | Enforce `>=80%` hard cuts + zone-boundary transitions (`D-97`) with `xfade` overlap compensation. |
| **BATCH-M7** | `explainer_engine/edit/timeline.py` | `TimelineAssembler` | Integrate `build_bounded_timeline()` and `export_otio_timeline()`. |
| **BATCH-M7** | `explainer_engine/edit/render.py` | `VideoRenderer` | Render `1920x1080` `24 fps CFR` with explicit Rec.709 color atoms and `-14.0 LUFS` audio mux. |
| **BATCH-M7** | `explainer_engine/qa/character_consistency.py` | `CharacterConsistencyChecker` | Verify `>=0.75` CLIP cosine similarity against `CastRegistry` reference sheets (`D-88`/`D-89`). |
| **BATCH-M7** | `explainer_engine/qa/color_audit.py` | `ColorAuditor` | Verify `D-95` zone saturation (`>=0.18`) and `D-96` map figure-ground contrast (`>=3.5:1`). |
| **BATCH-M7** | `explainer_engine/qa/motion_audit.py` | `MotionAuditor` | Verify `BP-168` optical-flow floor and `BP-170` (`CD-03`) Tier 1 & Tier 2 static duration caps. |
| **BATCH-M7** | `explainer_engine/qa/verifier.py` | `EpisodeVerifier` | Orchestrate all 6 QA gates synchronously (`mold_contract`, `loudness`, `motion`, `color`, `character`, `blind`). |
| **BATCH-M7** | `explainer_engine/pipeline.py` | `ExplainerPipeline` | Wire all 6 synchronous Master Mold v2.1.0 stages end-to-end. |
| **BATCH-M8A** | `scripts/validate_mold_compliance.py` | `run_mold_compliance_checks`, `main` | Full offline compliance gate across `/4` schema, `CD-02..06`, `D-81`, `D-96`, and `.otio` drift. |
| **BATCH-M8A** | `explainer_engine/governance/__main__.py` | `build_parser`, `cmd_status` | Add `--check` flag to `governance status` so `python -m explainer_engine.governance status --check` succeeds. |
| **BATCH-M8A/B** | `explainer_engine/cloud/runpod.py` | `PodTelemetry`, `RunPodManager`, `dryrun_main` | Add `--dry-run` CLI entrypoint, `CD-05` per-zone runtime telemetry, and `D-78` `try/finally` pod termination. |

*(All remaining 258 repository modules across `explainer_engine/` and `scripts/` also carry synchronized `[CLAUDE-MASTER-MOLD-SYNC]` and `[CLAUDE-CLASS-SYNC]` `TODO` blocks at the top of each file and class.)*
