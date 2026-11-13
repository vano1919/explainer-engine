> **HISTORICAL (moved to docs/archive/ on 2026-11-05 by ICW-01, D-108).** The Master Mold execution guide; the TODO header blocks that cite it are removed by ICW-00. It is kept as evidence and is not an active instruction. The rules in force are the decision log (D-96..D-113) and the Ink Chronicle roadmap (`docs/architecture/INK_CHRONICLE_OPUS_IMPLEMENTATION_ROADMAP_2026-11-04.md`).

> **SUPERSEDED FOR THE INK CHRONICLE BLENDER PLANNING BRANCH (2026-11-04).** This is historical audit material only. Its LTX/Qwen four-tier routing, Master Mold v2.1.0 synchronization batches and imported TODO proposals are not active implementation instructions for this branch. Do not execute them or copy their TODOs forward. Use docs/architecture/INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04.md and docs/architecture/FABLE_CLAUDE_TO_OPUS_IMPLEMENTATION_PLAN_BRIEF_2026-11-04.md instead. Preserve this file as history until the Fable audit confirms whether it can be archived or removed safely.

---

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

5. **Creator decisions.** Only decisions recorded in the canonical decision log or explicit creator instructions are approved. CD-01..CD-06 labels inside imported Gemini material are not approval. In particular, CD-05 remains open and D-67 paid-sample scope must not be extended. D-95 changes only its stated speech and shot-duration rules; it does not approve unrelated visual, audio, model, voice-policy, cost or architecture proposals. A `living == false` field is not a legal, platform or provider clearance by itself; see the current https://elevenlabs.io/use-policy (last updated 2026-10-09). YouTube disclosure classification depends on whether generated/altered content appears realistic and meets the policy's criteria; fully animated non-realistic content is listed as a non-disclosure example: https://support.google.com/youtube/answer/14328491?hl=en.

6. **Change authority.** The previous D-95 implementation authorization has been completed and recorded. Do not infer that it authorizes BATCH-M0..M8B, the 42 stubs, new paid services, a full architecture migration or this guide's proposed decisions. The current visual-grammar research should be read-only until the creator reviews and approves a specific implementation plan.

7. **Live main-branch protection gate (checked 2026-11-04).** GitHub's live API returned `protected: false` and `protection.enabled: false` for `main` (HEAD `6e1dccad30a865df670c258c86ffa1152a0dbe7e`); the repository rulesets endpoint returned an empty list. Therefore `GATE-EXT-MAIN-PROTECT` is **UNMET**, not passed. Sources: https://api.github.com/repos/vano1919/explainer-engine/branches/main and https://api.github.com/repos/vano1919/explainer-engine/rulesets (accessed 2026-11-04). Do not write to `main`, merge there, or mark the gate complete until an authorized repository administrator configures and verifies the intended protections. Do not change repository settings automatically as part of this audit.

---

## 1. CREATOR DECISION AUTHORITY — D-95 IS THE ONLY NEW OVERRIDE IN THIS HANDOFF

D-95 is the creator's explicit 2026-11-04 instruction. It supersedes the old narrator/dialogue split and universal shot-duration rule only within its scope. It does not imply approval of Gemini-generated `CD-01..CD-06`, does not close `CD-05`, and does not change D-93 visual lanes. The sections below remain Gemini-generated proposals unless their decisions are separately recorded in the canonical decision log.

## 1A. IMPORTED GEMINI DECISIONS (`CD-01` .. `CD-06`) — UNVERIFIED PROPOSALS, NOT LOCKED CREATOR DECISIONS

The imported guide claims that several creator decision points are resolved. That claim is not accepted merely because it appears here: each item remains a proposal until the canonical decision log records explicit creator approval.

### 1.1 Question 1 — `CD-01`: Kickoff of Free Batches (`BATCH-M0..M8A`) After `GATE-EXT-MAIN-PROTECT`
* **Unapproved proposal (not a creator decision):** Option A suggests checking `GATE-EXT-MAIN-PROTECT` before considering a dependency-ordered batch sequence. Neither the batch sequence nor a `$0.00` spend claim is approved by this label; verify protections, tool/model costs, prerequisites and actual batch dependencies before recommending execution.
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **Branch Integrity Before Code Mutation ([GitHub Docs — About Protected Branches](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/defining-the-mergeability-of-pull-requests/about-protected-branches))**: GitHub documents configurable protection and required checks. The repository's current protection state and the existence/configuration of a `quality` (`pytest` + `ruff`) check must be queried live; these docs do not prove that this repository has either configured.
  2. **Force-Push & Deletion Prevention ([GitHub Docs — Managing Rulesets for a Repository](https://docs.github.com/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets))**: Rulesets can restrict force pushes or deletion when configured. This source does not establish that the repo has such rules enabled.
  3. **Fail-Fast Schema Contract Dispatch ([JSON Schema Draft 2020-12 Specification](https://json-schema.org/draft/2020-12))**: JSON Schema defines validation semantics; it does not prove the repository needs this proposed dispatcher or that it is a prerequisite to all other batches. Validate current schemas and all callers before defining dependency order.
  4. **Offline Verification and Cost Separation ([Anthropic Claude Code Costs & Caching Docs](https://code.claude.com/docs/en/costs))**: Local checks may avoid external API charges, but total cost depends on the actual Claude plan/session, local infrastructure and tools. Do not promise `$0.00` or call all offline work free without checking the cost boundary.
  5. **Timeline Serialization ([OpenTimelineIO File Format Specification](https://opentimelineio.readthedocs.io/en/v0.13/tutorials/otio-file-format-specification.html))**: OTIO documents its timeline data model and rational-time representation. It does not prove that the proposed batch produces `0.000s` drift; that requires implementation-specific timeline tests.

### 1.2 Question 2 — `CD-02` (`xworld_v2` LoRA Weight `0.7` vs `1.0`) & `CD-03` (`BP-170` Tier 2 `qwen_nextpose` Static Cap `1.5 / 2.0 / 2.5s`)
* **Unverified proposals — not creator-approved:**
  * **Proposed `CD-02` value:** `0.7` is an unverified candidate, not a locked parameter. Confirm the actual adapter, current config and measured comparison before recommending a default.
  * **Proposed `CD-03` option:** The zone caps and their application to both tiers are unverified proposals. Confirm the canonical BP-170 decision, the actual tiers and representative visual evidence before treating them as hard FAIL rules.
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **Low-Rank Adapter Scaling Math ([Hu et al., 2021 — *LoRA: Low-Rank Adaptation*, arXiv:2106.09685](https://arxiv.org/abs/2106.09685))**: The paper describes the adapter scaling formulation. It does not show that a `0.7` value improves this repository's character motion or prevents style-lock artifacts. `0.7` versus `1.0` requires an experiment on the actual adapter/model and representative prompts.
  2. **Model Capability Lead ([Qwen/Qwen-Image-2.1 Model Card](https://huggingface.co/Qwen/Qwen-Image-2.1))**: First verify that this exact model/version and adapter are used by the current pipeline. A model card cannot establish that `0.7` is an optimal LoRA scale or guarantees pose/camera flexibility.
  3. **Readable Silhouette & Staging Principles ([Lasseter, 1987 — *Principles of Traditional Animation Applied to 3D Computer Animation*, ACM SIGGRAPH](https://dl.acm.org/doi/10.1145/37402.37407))**: This is a craft reference for readable staging and silhouette. It does not validate a fixed 2.5-second hold cap or prove a failure rate for the proposed Tier 2 method.
  4. **Shot Length and Viewer Attention ([Cutting, DeLong & Nothelfer, 2010 — *Attention and the Evolution of Hollywood Film*, Psychological Science](https://journals.sagepub.com/doi/10.1177/0956797610361679))**: The study is relevant background on editing and attention; it does not prescribe a universal sub-2-second change rule for high-tension segments. Do not turn its findings into that threshold.
  5. **CLIP Embeddings ([Radford et al., 2021 — *CLIP*, arXiv:2103.00020](https://arxiv.org/abs/2103.00020))**: CLIP is a vision-language representation. It does not, by itself, validate a character-identity threshold of `0.75`, measure temporal motion, or prove that static frames pass a separate motion gate. Verify the repo's actual metric and calibration data.
  6. **Perceptual Image Similarity ([Zhang et al., 2018 — *LPIPS*, arXiv:1801.03924](https://arxiv.org/abs/1801.03924))**: LPIPS measures perceptual image similarity. A pairwise LPIPS score is not automatically an optical-flow measure or proof of meaningful motion. Any motion threshold needs its own validated metric, representative data and creator-approved severity.

### 1.3 Question 3 — `CD-05` (`OPEN_PENDING_MEASUREMENT` Full-Episode RunPod Target + Post-`GATE-P3` Extension) & `CD-06` (`D-90` Deceased Historical Figures vs `D-62` Living-Person Ban)
* **Unverified proposals — not creator-approved:**
  * **Proposed `CD-05` framing:** Keep the full-episode target open pending creator-approved measurement. The two-segment D-67 scope remains the existing boundary. Any 210–240-second multi-zone measurement extension is a separate, unapproved proposal requiring its own creator decision, manifest, cap, code path and approval record.
  * **Proposed `CD-06` policy idea — NOT clearance:** A `living == False` flag is not sufficient to approve a voice or likeness use. ElevenLabs' Prohibited Use Policy (last updated 2026-10-09) also prohibits impersonation of a deceased individual where reasonably likely to cause harm or infringe applicable post-mortem rights. Any historical-character voice workflow needs a separate rights / harm / deception review, the exact voice source and service terms, and creator approval. Do not implement an automatic `living == False => approved` rule. Source: https://elevenlabs.io/use-policy
* **Claimed rationale and source leads — unverified; re-check direct relevance to each claim:**
  1. **GPU Billing and Sampling ([RunPod Pods Pricing](https://docs.runpod.io/pods/pricing))**: Pricing is card / cloud / region / time dependent. Do not copy the quoted GPU rates without checking the live price for the actual pod configuration. Whether two segments can estimate full-episode cost is a sampling-design question; justify the required sample with measured variance and coverage, not a categorical claim.
  2. **Pod and Volume Billing ([RunPod Billing Overview](https://docs.runpod.io/accounts-billing/billing))**: Verify current billing semantics for the exact pod, container disk and network volume configuration. Do not generalize the behavior of one storage type to every stopped pod or volume.
  3. **Cold-Start Versus Steady-State Time ([PyTorch torch.compile Tutorial](https://pytorch.org/tutorials/intermediate/torch_compile_tutorial.html) and the pinned model cards)**: The quoted `65 GB` and `90–140s` figures are not established by these references. Treat them as unknown until the exact models, weight files, container cache state and measured cold/warm run logs are supplied.
  4. **Voice Synthesis Consent & Impersonation Boundaries ([ElevenLabs Prohibited Use Policy](https://elevenlabs.io/use-policy))**: The policy (last updated 2026-10-09) prohibits cloning/impersonating a living person's voice without explicit informed consent or other valid authorization, and also prohibits impersonating a deceased person where reasonably likely to cause harm or infringe post-mortem rights. A `living` field or stock voice does not automatically clear a use; assess the actual intended voice, person, context and applicable rights. Source: https://elevenlabs.io/use-policy
  5. **Synthetic Media Disclosure Rules ([YouTube disclosure help](https://support.google.com/youtube/answer/14328491?hl=en))**: YouTube requires disclosure for AI-generated or altered content that appears realistic in specified ways (for example, making a real person say something they did not say, altering a real event/place, or generating a realistic scene that did not occur). Its examples include fully animated, non-realistic content that does not require disclosure. The classification depends on the actual content, not simply whether the creator calls it animation. Source: https://support.google.com/youtube/answer/14328491?hl=en
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
   - `explainer_engine.pacing.tension_zones.enforce_bp170_static_cap(segment)` -> a proposed implementation for zone-specific static-hold limits. The cited `CD-03` caps and hard `FAIL` severity are unapproved; verify canonical BP-170 first and require creator approval before enforcement.
   - `explainer_engine.video.scene_builder.SceneBuilder.build_scene_plan(script)` -> calls `TierRouter.route(segment, cast_registry)` (`explainer_engine/video/tier_router.py`):
     * Tier 1 (`parallax_25d`) -> `KeyframeGenerator` (`xworld_v2=0.7`) + `ParallaxEngine.render_clip()` (`explainer_engine/video/parallax.py`).
     * Tier 2 (`qwen_nextpose`) -> `KeyframeGenerator` (`Qwen-Image-Edit-2511`, `xworld_v2=0.7`, `CharacterCard.reference_sheet_path`).
     * Tier 3 (`ltx_1080p`) -> `LTXNode.generate_i2v_1080p()` (`explainer_engine/video/ltx_Node.py`, `8k+1` frame bucket `quantize_ltx_frames()`).
     * Tier 4 (`ltx_portrait_720p`) -> any proposed audio-driven identity/lip-sync path requires an independently verified model capability, provider-policy clearance and creator approval; `living == False` alone is not an approval gate.
     * `scene_type == "map_graphic"` -> `MapRenderer.render_segment()` (`explainer_engine/map/renderer.py`, Natural Earth 1:50m `ne_50m_admin_0_countries.geojson`, unapproved D-96 proposal (no canonical decision-log entry) / `PV-57`).
   - `explainer_engine.video.compositor.VideoCompositor` -> proposed zone grading must be assigned its own verified rule / decision ID; D-95 does not authorize color-grade profiles or saturation thresholds.

3. **Multi-Voice Audio, 6-Stage `D-81` Chain & 4-Bus Mix (`BATCH-M3`)**:
   - `explainer_engine.audio.tts.TTSSynthesizer.synthesize_segment(segment, cast_registry)` -> proposed narrator / character synthesis path; any historical-person voice requires independent policy/rights clearance and creator approval. The `living` field alone is not clearance. The proposed audio chain must be reconciled with the current narrator/audio implementation before adoption. (`highpass=f=75`, `afftdn=nf=-25`, `bass=g=2.5:f=120:w=0.6`, `equalizer=f=3200:t=q:w=1.2:g=1.8:m=0.5`, `alimiter=limit=-1.0dB:level=disabled`, `loudnorm=I=-14.0:TP=-1.0:LRA=7.0`).
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
| **BATCH-M0** | `explainer_engine/qa/blind_check.py` | Existing: `describe_rules`, `compare`, `second_look`, `style_verdict`, `main` | Implemented blind-description comparison module. The PEP 701 same-quote f-string compatibility refactor is already present in commit `684241fb4e0481adb09ecbe932e7908046361a68`; the imported `BlindCheckReport` / `BlindChecker` / `/4` field-stripping request is not an implementation requirement for this module. CI currently configures Python 3.12; do not claim Python 3.11 support or failure without explicit runtime metadata and a test. |
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


## 5. INDEPENDENT TECHNICAL AUDIT ADDENDUM — 2026-11-04

This addendum records a second read-only review of the live review branch. It refines priorities; it does not authorize application-code changes, implementation of TODO stubs, CI dispatch, repository-setting changes, paid API usage, GPU/pod execution or production rendering.

### 5.1 Live GitHub state — compare against main

Verified at the audit checkpoint:

- Review branch: claude/master-mold-ready-2026-11-04; reported HEAD: 6650e17d96014a0e1e942c7ed785b574fbf1e773.
- Main HEAD: 6e1dccad30a865df670c258c86ffa1152a0dbe7e.
- Compare result: 86 commits ahead, 0 behind; 300 changed paths (239 modified, 61 added, 0 deleted). This is a comparison with main, not a count of only the latest documentation work.
- GitHub PR search for this head branch returned no PR result. The target commit's combined status contained no status checks, and the commit workflow-run lookup returned no runs.
- .github/workflows/quality.yml has push triggers for main and systemic/**, plus pull_request and workflow_dispatch. Therefore, a normal push to this review branch does not match the push trigger; this does not mean the workflow is impossible to run. A PR or explicit dispatch can run it, but neither is evidenced for this audited SHA.
- Main was reported as protected=false with no repository rulesets. The API request for target-branch protection was denied (403), so target-branch protection is unknown, not false.

Treat main protection as a merge-governance blocker, not as a blocker to read-only research or isolated planning on this branch. Do not merge until an authorized administrator configures and verifies protection and required checks.

### 5.2 Confirmed architecture finding — layout geometry is not handed to the inspected P6 still route

The existing explainer_engine/scripting/layout.py is implemented: it solves item boxes/depth, validates overlap/visibility, and can produce technical, relative, EliGen and blockout representations. film_shots.py also authors textual blocking/layout information in its prompts. These are real, distinct capabilities.

In the inspected explainer_engine/edit/router.py P6 route:

- the module does not import or call scripting.layout.solve();
- the still specification is assembled from the composed prompt, model/LoRA, continuity references and inference parameters;
- _spec() defaults blocking_sha256 to null;
- the current shot_spec/1 schema has no structured layout object or layout-artifact reference field.

Scope this finding precisely: textual blocking and composition language do reach the keyframe prompt; the calculated geometry/artifacts from layout.py are not shown to reach this inspected P6 still-generation specification. Do not claim that every legacy/other generation route lacks layout usage.

Recommended next design task (not an implementation authorization): trace the actual keyframe renderer/adapter and propose the smallest compatible handoff for validated layout output. Prefer a hashed artifact reference or a small schema extension over creating a second layout engine. Acceptance tests should prove that the route carries the layout artifact identity/hash, the consumer actually reads it, stale hashes are rejected, and existing prompt/reference behavior remains intact.

### 5.3 D-95 — distinguish script planning from final delivered speech

variant_plan.py provides a pre-production spoken-word estimate from script lines and excludes voiced:false lines. audio/spine.py records measured narrator word timing and reserves/retimes native-dialogue windows with clip metadata. These are useful existing foundations.

The inspected flow does not establish a final post-mix verification that recounts the actually delivered narrator and character spoken words after all stem/clip assembly. Do not silently treat planned script words, a clip duration, or a clip hash as proof of audible words.

Before proposing code, trace the complete existing TTS/stem/mix/export path and identify the least expensive reliable measurement source. It may be validated synthesis/transcript metadata or audio analysis; do not assume a new ASR dependency is necessary. Define how the check detects missing, muted, truncated, duplicated or unintentionally unvoiced dialogue. Keep the D-95 speech ratio independent from D-93's visual runtime ratio.

### 5.4 LTX capability status and adapter-specific frame rules

variant_plan.py currently marks KEYFRAME_LTX:light and KEYFRAME_LTX:full unavailable until the relevant clip pod path passes the RunPod dryrun. A router-generated video spec is not proof of a functioning provider adapter or a successful render.

Keep local-model frame quantization and hosted-API duration validation separate. The 8k+1 convention may be required by a specific local LTX implementation; it must not be imposed on a hosted API unless that exact API/version documents the same constraint. Record provider, model/version, adapter/endpoint, resolution, FPS, duration and frame rules separately, with unknown values left unknown.

### 5.5 BlindCheck and inventory correction

The inventory row above is corrected. The existing module contains describe_rules(), compare(), second_look(), style_verdict() and main(); it does not expose the imported BlindCheckReport / BlindChecker API described by the old row. The compatibility refactor is already present. In the inspected keyframe_gate.py, the visible integration is the import/use of STYLE_SUSPENDED; do not claim that a full blind-compare / second-look cycle is integrated there without tracing an actual caller elsewhere.

### 5.6 Required verification before any implementation proposal

1. Keep this branch read-only until the creator approves a concrete implementation plan.
2. For layout handoff, map the producer, artifact contract, route, renderer/adapter and QA consumer before changing shot_spec.
3. For D-95 final-audio verification, map each source stem/clip to the final mix and identify an auditable spoken-word measurement.
4. For LTX, identify the exact local/hosted adapter and run a small smoke test only after separate creator approval for any pod or paid resource.
5. Run the existing quality workflow on the exact candidate SHA through an approved PR or workflow dispatch; report actual results, not inferred results.
6. Do not implement the remaining stubs as a batch. Each must first justify a real gap not already covered by an existing module.
