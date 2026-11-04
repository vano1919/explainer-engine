# CLAUDE SYNCHRONIZED TODO EXECUTION GUIDE (production_script/4 & Master Mold v2.1.0)

> **Status: unverified Gemini-generated proposal, not creator approval, except for the explicitly recorded D-95 creator override.** Read [D-95 creator override](CREATOR_OVERRIDE_NARRATION_VISUAL_SHOT_DURATIONS_2026-11-04.md) and the [Claude handoff](CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md) first. D-95 is authoritative only for the 70–80% narrator / 20–30% voiced-dialogue spoken-word mix, the 5-second visible-dialogue coverage target, and justified non-dialogue VIDEO shots up to a 15-second planning ceiling subject to actual model constraints. It is independent from D-93 visual 60/30/10. All other proposals and imported TODOs remain unverified; CD-05 remains open. This guide is an audit backlog, not blanket execution permission. No code change, batch, paid API, pod, full render, upload or publishing action is authorized unless separately approved by the creator.

**Document ID:** CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04
**Pinned PR #119 code baseline:** `5013a55aca5a17a3734150f61a5eb172abcbe3b8`
**Planning-branch base:** `bb0da660582ac0868825d88592276d7d43c234d5`
**Review branch:** `claude/master-mold-ready-2026-11-04` (re-read its live HEAD before every review)
**Target Role:** Evidence backlog for Claude Code; BATCH-M0..M8B and GATE-P1..P3 are proposals, not an approved execution sequence.

**Imported TODO coverage:** The handoff records 301 Python files with module-level TODO material (259 existing modules plus 42 new stubs) and 88 class-level annotations. The assertion that every top-level class is annotated is unverified and must not be repeated as fact. TODO text is not proof that a target module, symbol, caller, schema or test existed at the pinned baseline.

**Evidence rule:** TODO blocks include source URLs, but the presence or number of URLs does not verify the associated claim. Some references may be generic or irrelevant to the exact code change. Do not enforce an arbitrary minimum of five URLs per module. Verify each external factual claim against a relevant primary/current source; cite the exact claim it supports, include the access date and version where relevant, and label unsupported claims UNVERIFIED. Repository claims require exact paths, immutable commit SHA, line ranges and actual test evidence.

---

## 0. CRITICAL AUDIT CORRECTIONS — OVERRIDE MISLEADING TODO WORDING

1. **Baseline identity.** Use the pinned PR #119 code baseline and planning-branch base above. The previous strings `5013a55aa910820db16be2e59f9045a79573b219` and `bb0da662273ebcd18120c9eb8e2524df87efca2e` are malformed hashes and must not be used. Never reuse TODO line numbers without reopening the exact file at the pinned commit.

2. **Existing module versus newly imported stub.** At the pinned PR #119 code baseline, the following paths were not present: `explainer_engine/validate.py`, `explainer_engine/scripting/schema_version.py`, `explainer_engine/scripting/mold_contract.py`, `explainer_engine/audio/voice_chain.py`, `explainer_engine/audio/tts.py`, `explainer_engine/audio/mixer.py`, `explainer_engine/cast/voice_clearance.py`, `explainer_engine/scripting/models.py`, and `schemas/production_script_v4.schema.json`. On the review branch, several of these are TODO-only stubs. Therefore, statements such as “the current function at lines 21–29 does X” or “the current audio module has parameter Y” are not established for those files. Treat them as proposed new modules/designs. First locate the actual current equivalent, its callers, schemas, tests and approved requirements. Do not overwrite a working subsystem or create a duplicate authority simply to satisfy a stub.

3. **Blind-check TODO correction.** The earlier TODO at the top of `explainer_engine/qa/blind_check.py` referred to `BlindCheckReport`, `BlindChecker`, `guesses` and `check_script()`; those symbols/expressions are not present in the inspected source. Withdraw that description. The actual PEP 701 compatibility risk is the nested same-quote f-string used to construct `style_key` inside `describe_rules()`. A compatible implementation extracts the style entries before the outer f-string. Python's official documentation confirms same-quote reuse was introduced by PEP 701 in Python 3.12; verify the repository's lowest supported Python version from CI/runtime configuration before claiming a supported-version defect.

4. **No speculative batch execution.** For every TODO, establish: (a) exact pinned baseline file and line range; (b) current branch file and whether it is production code, a stub or new; (c) real caller/callee chain; (d) relevant schema and fixtures; (e) reproduction of the claimed defect; (f) existing tests and test results; (g) decision authority. If any element is missing, stop that item and report NEEDS EVIDENCE or CREATOR DECISION. A title containing “CRITICAL”, “MUST” or “EXACT” does not raise its authority.

5. **Creator decisions.** Only decisions recorded in the canonical decision log or explicit creator instructions are approved. CD-01..CD-06 labels inside imported Gemini material are not approval. In particular, CD-05 remains open and D-67 paid-sample scope must not be extended. D-95 changes only its stated speech and shot-duration rules; it does not approve unrelated visual, audio, model, voice-policy, cost or architecture proposals. A `living == false` field is not a legal, platform or provider clearance by itself; see the current https://elevenlabs.io/use-policy (last updated 2026-10-09). YouTube synthetic-content disclosure is case-specific; do not infer a blanket exemption merely because a video is animated: https://support.google.com/youtube/answer/14328491?hl=en-See.

6. **Change authority.** The previous D-95 implementation authorization has been completed and recorded. Do not infer that it authorizes BATCH-M0..M8B, the 42 stubs, new paid services, a full architecture migration or this guide's proposed decisions. The current visual-grammar research should be read-only until the creator reviews and approves a specific implementation plan.

---

## 1. CREATOR DECISION AUTHORITY — D-95 IS THE ONLY NEW OVERRIDE IN THIS HANDOFF

D-95 is the creator's explicit 2026-11-04 instruction. It supersedes the old narrator/dialogue split and universal shot-duration rule only within its scope. It does not imply approval of Gemini-generated `CD-01..CD-06`, does not close `CD-05`, and does not change D-93 visual lanes. The sections below remain Gemini-generated proposals unless their decisions are separately recorded in the canonical decision log.

## 1A. IMPORTED GEMINI DECISIONS (`CD-01` .. `CD-06`) — UNVERIFIED PROPOSALS, NOT LOCKED CREATOR DECISIONS

The imported guide claims that several creator decision points are resolved. That claim is not accepted merely because it appears here: each item remains a proposal until the canonical decision log records explicit creator approval.

### 1.1 Question 1 — `CD-01`: Kickoff of Free Batches (`BATCH-M0..M8A`) After `GATE-EXT-MAIN-PROTECT`
* **Unapproved proposal (not a creator decision):** Option A suggests checking `GATE-EXT-MAIN-PROTECT` before considering a dependency-ordered batch sequence. Neither the batch sequence nor a `$0.00` spend claim is approved by this label; verify protections, tool/model costs, prerequisites and actual batch dependencies before recommending execution.
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **Branch Integrity Before Code Mutation ([GitHub Docs — About Protected Branches](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches))**: Enabling branch protection and requiring the `quality` status check (`pytest` + `ruff`) before landing multi-batch refactors prevents unverified commits from reaching `main`.
  2. **Force-Push & Deletion Prevention ([GitHub Docs — Managing Rulesets for a Repository](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets))**: Repository rulesets block history rewrites and accidental branch deletion while Claude executes `BATCH-M0..M8A`.
  3. **Fail-Fast Schema Contract Dispatch ([JSON Schema Draft 2020-12 Specification](https://json-schema.org/draft/2020-12))**: Fixing `explainer_engine/validate.py:_select_production_script_schema()` in `BATCH-M0` first is a strict prerequisite for every downstream batch that validates `production_script/4`.
  4. **Zero-Cost Offline Verification Before Paid Spend ([Anthropic Claude Code Costs & Caching Docs](https://code.claude.com/docs/en/costs))**: Separating deterministic local CPU/static verification (`$0.00`) from paid external APIs (`GATE-P1` ElevenLabs, `GATE-P2/P3` RunPod) prevents burning paid tokens or GPU hours on broken schema wiring.
  5. **Deterministic Timeline Dry-Run Verification ([OpenTimelineIO File Format Specification](https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html))**: Completing `BATCH-M7` and `BATCH-M8A` offline allows full `.otio` rational-time verification (`0.000s` drift) before provisioning any cloud GPU.

### 1.2 Question 2 — `CD-02` (`xworld_v2` LoRA Weight `0.7` vs `1.0`) & `CD-03` (`BP-170` Tier 2 `qwen_nextpose` Static Cap `1.5 / 2.0 / 2.5s`)
* **Unverified proposals — not creator-approved:**
  * **Proposed `CD-02` value:** `0.7` is an unverified candidate, not a locked parameter. Confirm the actual adapter, current config and measured comparison before recommending a default.
  * **Proposed `CD-03` option:** The zone caps and their application to both tiers are unverified proposals. Confirm the canonical BP-170 decision, the actual tiers and representative visual evidence before treating them as hard FAIL rules.
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **Low-Rank Adapter Scaling Math ([Hu et al., 2021 — *LoRA: Low-Rank Adaptation*, arXiv:2106.09685](https://arxiv.org/abs/2106.09685))**: In $W = W_0 + (\alpha/r) B A$, setting scale $\alpha/r = 1.0$ on a style adapter trained predominantly on static poses over-constrains attention projections and suppresses high-velocity prompt tokens (`KP-47`). Scaling to **`0.7`** preserves stylistic cohesion while retaining base-model geometric plasticity.
  2. **Base Model Pose Plasticity vs Adapter Saturation ([Qwen/Qwen-Image-2.1 Official Model Card](https://huggingface.co/Qwen/Qwen-Image-2.1))**: `Qwen-Image-2.1` and `Qwen-Image-Edit-2511` rely on strong text-image cross-attention for body pose and camera angle changes; `0.7` LoRA scaling prevents style-lock artifacts.
  3. **Readable Silhouette & Staging Principles ([Lasseter, 1987 — *Principles of Traditional Animation Applied to 3D Computer Animation*, ACM SIGGRAPH](https://dl.acm.org/doi/10.1145/37402.37407))**: A pose transition only registers as genuine animation when the character's silhouette and line of action change clearly; unverified Tier 2 edits risk producing near-identical holds that feel like frozen slides if held >2.5s.
  4. **Shot Length, Visual Change & Viewer Attention ([Cutting, DeLong & Nothelfer, 2010 — *Attention and the Evolution of Hollywood Film*, Psychological Science](https://journals.sagepub.com/doi/10.1177/0956797610361679))**: Empirical attention studies confirm that high-tension sequences (`cold_open`, `climax`) require sub-2.0s visual modulation whenever internal frame motion is limited.
  5. **Embedding Distance Calibration ([Radford et al., 2021 — *CLIP*, arXiv:2103.00020](https://arxiv.org/abs/2103.00020))**: Because `character_consistency.py` enforces CLIP cosine similarity `>= 0.75` for identity preservation, relaxing `BP-170` before calibrating pose-delta thresholds on `P12b` would allow static frames to pass both gates undetected.
  6. **Perceptual Frame-Pair Distance ([Zhang et al., 2018 — *LPIPS*, arXiv:1801.03924](https://arxiv.org/abs/1801.03924))**: Perceptual motion floors (`BP-168`) and static-hold caps (`BP-170`) must remain fail-closed (`FAIL`, not `WARN`) until empirical LPIPS / optical-flow distributions are measured on `P12b`.

### 1.3 Question 3 — `CD-05` (`OPEN_PENDING_MEASUREMENT` Full-Episode RunPod Target + Post-`GATE-P3` Extension) & `CD-06` (`D-90` Deceased Historical Figures vs `D-62` Living-Person Ban)
* **Unverified proposals — not creator-approved:**
  * **Proposed `CD-05` framing:** Keep the full-episode target open pending creator-approved measurement. The two-segment D-67 scope remains the existing boundary. Any 210–240-second multi-zone measurement extension is a separate, unapproved proposal requiring its own creator decision, manifest, cap, code path and approval record.
  * **Proposed `CD-06` policy idea — NOT clearance:** A `living == False` flag is not sufficient to approve a voice or likeness use. ElevenLabs' Prohibited Use Policy (last updated 2026-10-09) also prohibits impersonation of a deceased individual where reasonably likely to cause harm or infringe applicable post-mortem rights. Any historical-character voice workflow needs a separate rights / harm / deception review, the exact voice source and service terms, and creator approval. Do not implement an automatic `living == False => approved` rule. Source: https://elevenlabs.io/use-policy
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **Per-Second GPU Billing & Empirical Budgeting ([RunPod Pods Pricing](https://docs.runpod.io/pods/pricing))**: RTX PRO 6000 Blackwell (`$1.89/hr`) and H200 SXM (`$3.59/hr`) bill per second; because `production_script/4` uses variable `8k+1` LTX buckets (`97..257` frames) across 5 tension zones, a 2-segment smoke test cannot statistically estimate full-episode variance across all zones.
  2. **Container & Volume Storage Billing on Stopped Pods ([RunPod Billing Overview](https://docs.runpod.io/accounts-billing/billing))**: Stopped pods still incur disk storage charges until terminated (`remove_pod`), justifying the strict two-stage gate (`D-67` 2-segment smoke test first, separate multi-zone benchmark second, with automatic `try/finally` pod deletion under `D-78`).
  3. **Cold-Start Weight Loading vs Steady-State Denoising ([PyTorch `torch.compile` Tutorial](https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html) & [Lightricks/LTX-2.5 Model Card](https://huggingface.co/Lightricks/LTX-2.5))**: Loading ~65 GB of weights (`Qwen-Image-2.1` + `Qwen-Image-Edit-2511` + `LTX-2.5 19B/22B`) creates a fixed cold-start offset (`~90–140s`) that must be separated from marginal per-bucket denoising speed via multi-zone telemetry (`PodTelemetry`).
  4. **Voice Synthesis Consent & Impersonation Boundaries ([ElevenLabs Prohibited Use Policy](https://elevenlabs.io/use-policy) & [ElevenLabs Terms of Use](https://elevenlabs.io/terms-of-use))**: ElevenLabs strictly prohibits non-consensual voice cloning or impersonation of living people or political candidates (`living == True`), whereas voicing centuries-deceased historical figures (`living == False`) using licensed stock/designed voices in dramatic historical storytelling is fully compliant.
  5. **Synthetic Media Disclosure Rules ([YouTube Disclosing Use of Altered or Synthetic Content](https://support.google.com/youtube/answer/14328491?hl=en) & [YouTube 'How this content was made' Disclosures](https://support.google.com/youtube/answer/15447836?hl=en))**: YouTube's synthetic content policy targets realistic deceptive depictions of real living persons or fabricated real-world footage, explicitly distinguishing stylized 2D animated historical dramatizations.
  6. **Originality & Anti-Repetitive Content Value ([YouTube Channel Monetization Policies](https://support.google.com/youtube/answer/1311392?hl=en-GB))**: The policy does not establish that adding multiple voices improves retention or automatically prevents monetization issues. Performance claims require audience data; policy compliance and creative originality are separate questions.

---

## 2. GEMINI-GENERATED SYSTEM-CHECK CLAIMS — VERIFY BEFORE ANY FIX

The imported Gemini guide asserts that an AST / method-level scan found seven synchronization mismatches. This audit has not verified all seven, and at least one claim (the blind-check TODO) described symbols and an expression that do not exist in the cited source. Treat every row below as a lead only. No row authorizes a code change. Re-open the exact path at the pinned baseline, confirm the symbol and failure, locate the current implementation and callers, and run a focused reproducer/test before proposing a fix.

| # | Claimed defect / desynchronization | Claimed file & line (re-check) | Proposed remediation to evaluate — not approved |
|---|---|---|---|
| **1** | **Python 3.11 PEP 701 compatibility risk** | `explainer_engine/qa/blind_check.py`, inside `describe_rules()` (re-check current line) | The actual nested same-quote f-string was in construction of `style_key`, not in a `BlindCheckReport` / `guesses` class. The branch now extracts `style_entries` before the outer f-string. Confirm minimum supported Python version and test on it; no `/4` field-stripping change is justified by this finding. |
| **2** | **Claimed `/4` schema dispatch fallback** | `explainer_engine/validate.py:21-29` (path absent at pinned baseline; current branch path is a TODO-only stub) | Do not implement the stated line-level fix. First locate the real current validator and `/4` schema, identify their actual paths, and map every caller. Only then design schema dispatch as a new feature if still needed. |
| **3** | **Claimed D-81 audio-chain divergence** | `explainer_engine/audio/voice_chain.py:18-65` (path absent at pinned baseline; current branch file is a TODO-only stub) | Do not patch the stub as though it were an existing filtergraph. Inspect the actual narrator/audio path and approved D-81 source, compare it with existing narrator polish and timing behavior, then decide whether a separate reusable chain is justified. |
| **4** | **Claimed batch dependency inversion** | Roadmap batch definitions and actual dependency graph (must be reconstructed) | Do not accept the proposed sequence as authoritative. Derive dependencies from actual imports, data contracts, callers, gates and tests; provide a topological order and identify cycles before asking for approval. |
| **5** | **Claimed payoff-thread field casing mismatch** | `schemas/production_script_v4.schema.json:255` (schema absent at pinned baseline; actual current schema path unverified) | First locate and compare the canonical schema, Mold contract and real payload fixtures. Do not add dual aliases until the mismatch is verified and backward-compatibility behavior is specified. |
| **6** | **Claimed mixed-case LTX module name** | `explainer_engine/video/ltx_Node.py` (new/proposed path; verify at pinned baseline) | Inspect the actual video-generation adapter and import conventions before naming or adding a new module. Do not create aliases for an unverified stub API. |
| **7** | **Claimed governance / RunPod CLI mismatch** | `explainer_engine/governance/__main__.py:72` and `explainer_engine/cloud/runpod.py` (verify exact baseline versions and CLI behavior) | Reproduce the claimed commands against the pinned branch and current CLI help/tests. Propose the smallest correction only if the mismatch exists and no current command already covers it. |

---

## 3. PROPOSED TARGET CALL GRAPH — NOT THE CURRENT IMPLEMENTATION

If a future implementation is separately approved, assess whether this proposed call graph is necessary and viable. It is not evidence that these functions or modules currently exist or interoperate:

1. **Schema & Contract Entry (`BATCH-M0` + `BATCH-M1` + `BATCH-M2`)**:
   - `explainer_engine.scripting.schema_version.detect_schema_version(script)` -> identifies `"production_script/4"`.
   - `explainer_engine.validate.validate_production_script(script, check_mold_contract=True)` -> validates against `schemas/production_script_v4.schema.json` via `resolve_schema_filename(script)` and invokes `explainer_engine.scripting.mold_contract.validate_mold_contract(script)`.
   - `explainer_engine.cast.registry.CastRegistry.from_script(script)` -> proposed cast parsing; any default LoRA scale and voice-clearance result require separate evidence and creator approval. `living == False` must not automatically approve a character voice or likeness.
   - `explainer_engine.scripting.validator.ScriptValidator.validate(script)` -> aggregates JSON Schema, `mold_contract`, `tension_zones.validate_zone_pacing()`, `shot_variety.validate_shot_variety()`, `prose_gate.check_prose_quality()`, and `claims.verify_script_claims()`.

2. **Pacing, Visual Routing, Map & Color Grading (`BATCH-M4` + `BATCH-M5` + `BATCH-M6`)**:
   - `explainer_engine.pacing.tension_zones.enforce_bp170_static_cap(segment)` -> enforces hard `FAIL` at `1.5s` (`cold_open`/`climax`), `2.0s` (`escalation`), and `2.5s` (`grounding`/`coda`) for BOTH Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`) (`CD-03` Option A).
   - `explainer_engine.video.scene_builder.SceneBuilder.build_scene_plan(script)` -> calls `TierRouter.route(segment, cast_registry)` (`explainer_engine/video/tier_router.py`):
     * Tier 1 (`parallax_25d`) -> `KeyframeGenerator` (`xworld_v2=0.7`) + `ParallaxEngine.render_clip()` (`explainer_engine/video/parallax.py`).
     * Tier 2 (`qwen_nextpose`) -> `KeyframeGenerator` (`Qwen-Image-Edit-2511`, `xworld_v2=0.7`, `CharacterCard.reference_sheet_path`).
     * Tier 3 (`ltx_1080p`) -> `LTXNode.generate_i2v_1080p()` (`explainer_engine/video/ltx_Node.py`, `8k+1` frame bucket `quantize_ltx_frames()`).
     * Tier 4 (`ltx_portrait_720p`) -> any proposed audio-driven identity/lip-sync path requires an independently verified model capability, provider-policy clearance and creator approval; `living == False` alone is not an approval gate.
     * `scene_type == "map_graphic"` -> `MapRenderer.render_segment()` (`explainer_engine/map/renderer.py`, Natural Earth 1:50m `ne_50m_admin_0_countries.geojson`, unapproved D-96 proposal (no canonical decision-log entry) / `PV-57`).
   - `explainer_engine.video.compositor.VideoCompositor` -> proposed zone grading must be assigned its own verified rule / decision ID; D-95 does not authorize color-grade profiles or saturation thresholds.

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

| Batch | Module Path | Primary symbols named by the proposal (verify existence) | Unverified proposed focus in TODO |
|---|---|---|---|
| **BATCH-M0** | `explainer_engine/scripting/schema_version.py` | `resolve_schema_filename`, `detect_schema_version`, `is_v4_or_newer` | New canonical `/1..4` schema version resolver (stub created with full `TODO`). |
| **BATCH-M0** | `explainer_engine/validate.py` | `_select_production_script_schema`, `validate_production_script` | Fix `/4` fallback to `v2`; wire `resolve_schema_filename` and optional `check_mold_contract`. |
| **BATCH-M0** | `explainer_engine/qa/blind_check.py` | `BlindCheckReport.to_dict`, `BlindChecker` | Fix Python 3.11 PEP 701 nested f-string `SyntaxError` on line 36 + `/4` field stripping. |
| **BATCH-M1** | `explainer_engine/cast/registry.py` | Proposed `CharacterCard`, `CastRegistry` (verify need and current equivalent) | Candidate `living` metadata and optional LoRA-scale configuration; no default value or automatic voice clearance is approved. |
| **BATCH-M1** | `explainer_engine/cast/voice_clearance.py` | Proposed voice-clearance API (new stub; verify provider and legal policy) | Evaluate a case-by-case clearance gate; do not encode `living == False => approved`. Creator approval and rights / harm / deception review required. |
| **BATCH-M1** | `explainer_engine/cast/__init__.py` | Package exports | Export `CastRegistry`, `CharacterCard`, `verify_voice_clearance`. |
| **BATCH-M2** | `explainer_engine/scripting/mold_contract.py` | `MoldContractViolation`, `MoldContractValidator`, `validate_mold_contract` | New semantic `/4` validator (`D-83..D-97`, `BP-165..BP-170`, `CD-03`, `CD-06`) (stub created with full `TODO`). |
| **BATCH-M2** | `explainer_engine/scripting/validator.py` | `ScriptValidator`, `validate_script` | Wire `schema_version`, `mold_contract`, `tension_zones`, `shot_variety`, and `payoff_thread_id` alias. |
| **BATCH-M2** | `explainer_engine/scripting/generator.py` | `ScriptGenerationConfig`, `ScriptGenerator` | Default `target_schema_version="production_script/4"` and feed `MoldContractViolation` items into retry loop. |
| **BATCH-M2** | `explainer_engine/scripting/models.py` | `CastMemberSpec`, `MusicCueSpec`, `SegmentSpec`, `ProductionScriptV4` | Add `/4` dataclasses and `payoff_Thread_id` <-> `payoff_thread_id` property alias. |
| **BATCH-M2** | `explainer_engine/scripting/prose_gate.py` | `ProseGate`, `check_prose_quality` | Support `D-90` character lines, `on_screen_text <= 4` words, and `D-86` silence markers. |
| **BATCH-M2** | `explainer_engine/scripting/claims.py` | `ClaimExtractor`, `verify_script_claims` | Distinguish `grounding` factual citations from `reversed_premise` / `D-90` counterfactual dramatization. |
| **BATCH-M4** | `explainer_engine/pacing/tension_zones.py` | Proposed pacing APIs (verify current equivalents) | Evaluate proposed zone caps against canonical BP-170 and creator authority; do not enforce unapproved `CD-03` values. |
| **BATCH-M4** | `explainer_engine/pacing/shot_variety.py` | `ShotVarietyValidator`, `validate_shot_variety` | Enforce max 2 consecutive identical `scene_type`, `tier_change_reason`, and `>=40%` Tier 3/4 motion share. |
| **BATCH-M5** | `explainer_engine/map/renderer.py` | `MapRenderer`, `MapRenderConfig`, `verify_map_contrast` | Render `ne_50m_admin_0_countries.geojson` (unapproved D-96 proposal (no canonical decision-log entry)), ban AI-diffused maps (`PV-57`), enforce `>=3.5:1` contrast. |
| **BATCH-M5** | `explainer_engine/video/color_grade.py` | Proposed zone-grading API (verify current color pipeline) | Research optional episode/zone grading and measurable color checks. D-95 does not approve these profiles or saturation floors; creator decision required before enforcement. |
| **BATCH-M6** | `explainer_engine/video/tier_router.py` | Proposed router API (verify whether tiers exist) | Evaluate candidate tiers and routing only after inspecting actual generation adapters. `0.7`, `CD-03` caps and `CD-06` voice rules are not approved defaults. |
| **BATCH-M6** | `explainer_engine/video/ltx_Node.py` | `LTXBucketSpec`, `LTXNode`, `quantize_ltx_frames` | Quantize up to `8k+1` frames (`97..257`) and emit exact `trim_frames` for `bounded_timeline.py`. |
| **BATCH-M6** | `explainer_engine/video/parallax.py` | `ParallaxEngine`, `render_parallax_clip` | Render 2.5D depth-peeled parallax within `BP-170` zone cap (`CD-03`). |
| **BATCH-M6** | `explainer_engine/video/scene_builder.py` | `ScenePlan`, `SceneBuilder` | Connect `/4` segments to `TierRouter`, `CastRegistry`, `MapRenderer`, and `LTXBucketSpec`. |
| **BATCH-M6** | `explainer_engine/video/prompts.py` | Proposed prompt compiler (verify actual prompt path) | Explore structured prompt generation and optional LoRA settings; do not lock `0.7` without a controlled comparison and creator approval. |
| **BATCH-M6** | `explainer_engine/video/keyframes.py` | Proposed keyframe generator (verify actual image-generation path) | Evaluate reference-sheet conditioning; LoRA scale remains an unapproved experiment, not a fixed value. |
| **BATCH-M6** | `explainer_engine/video/generator.py` | `VideoGenerator` | Dispatch Tier 1 (`ParallaxEngine`), Tier 2 (`nextpose`), Tier 3/4 (`LTXNode`), and `MapRenderer`. |
| **BATCH-M6** | `explainer_engine/video/compositor.py` | `VideoCompositor` | Apply unapproved zone color-grade proposal and overlay `on_screen_text` (`<=4` words) at `1920x1080` `24 fps`. |
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
| **BATCH-M7** | `explainer_engine/qa/color_audit.py` | `ColorAuditor` | Verify unapproved zone-saturation proposal (`>=0.18`) and unapproved D-96 proposal (no canonical decision-log entry) map figure-ground contrast (`>=3.5:1`). |
| **BATCH-M7** | `explainer_engine/qa/motion_audit.py` | Proposed motion QA component (verify current equivalents) | Evaluate motion measurements and static-hold limits against existing BP-168/BP-170 authority; do not import unapproved CD-03 caps. |
| **BATCH-M7** | `explainer_engine/qa/verifier.py` | `EpisodeVerifier` | Orchestrate all 6 QA gates synchronously (`mold_contract`, `loudness`, `motion`, `color`, `character`, `blind`). |
| **BATCH-M7** | `explainer_engine/pipeline.py` | `ExplainerPipeline` | Wire all 6 synchronous Master Mold v2.1.0 stages end-to-end. |
| **BATCH-M8A** | `scripts/validate_mold_compliance.py` | `run_mold_compliance_checks`, `main` | Full offline compliance gate across `/4` schema, `CD-02..06`, `D-81`, unapproved D-96 proposal (no canonical decision-log entry), and `.otio` drift. |
| **BATCH-M8A** | `explainer_engine/governance/__main__.py` | `build_parser`, `cmd_status` | Add `--check` flag to `governance status` so `python -m explainer_engine.governance status --check` succeeds. |
| **BATCH-M8A/B** | `explainer_engine/cloud/runpod.py` | `PodTelemetry`, `RunPodManager`, `dryrun_main` | Add `--dry-run` CLI entrypoint, `CD-05` per-zone runtime telemetry, and `D-78` `try/finally` pod termination. |

*(The handoff records 301 module-level TODO-bearing Python files; class-level annotations total 88 and are not complete coverage of all top-level classes. Treat the TODO inventory as an imported proposal set, not proof of current implementation.)*
