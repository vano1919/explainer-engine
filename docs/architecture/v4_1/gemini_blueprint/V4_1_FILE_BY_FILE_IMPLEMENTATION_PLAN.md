# Explainer Engine V4.1 — Deep File-by-File Implementation Plan (Expanded)

- **Document ID:** `V4.1-DOC-02` (`V4.1-DEEP-COMPLETION-002`)
- **Authoritative Baseline:** `argon/p1-2-timing-contract` @ `0592114c6c2d44a9af00b11553f169516e175864` (code `eb80e443`)
- **Verified Read-Only Test Run (`VERIFIED_TEST`):** `PYTHONPATH=tests/unit:. python3 -m pytest -p no:cacheprovider --basetemp=/tmp/v41_pytest -q` across 11 core WP-02 touched unit suites -> **`164 passed, 0 failed, 1 skipped`**; `python3 -m explainer_engine.docs_lint` -> **`0 finding(s)`**.
- **Cross-References:** Complete validated JSON Schemas in `V4.1-DOC-03`; upstream source evidence in `V4.1-DOC-04`; Claude review & Level A/B/C locks in `V4.1-DOC-05` + `V4_1_IMPLEMENTATION_MANIFEST.yaml`.

---

## 1. Verified Production Call-Graph & Exact `WP-02` Integration Touchpoints (`VERIFIED_CODE`)

Direct function-body inspection of `explainer_engine/episode/run.py` (`1,790`L), `explainer_engine/videolane/scene.py` (`421`L), `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` (`1,334`L), and `explainer_engine/governance/hooks.py` (`433`L) establishes all **16 mandatory `WP-02` touchpoints**:

```mermaid
sequenceDiagram
  participant Run as episode/run.py
  participant TP as imagegen/turn_pack.py
  participant ObsImg as qa/observe_image.py [NEW]
  participant Scene as videolane/scene.py
  participant LTX as modal_ltx_jobs.py
  participant ObsVid as qa/observe_video.py [NEW]
  participant Cut as edit/action_cut.py [NEW]
  participant Sync as audio/event_sync.py [NEW]
  participant QA as qa/loop.py + stage_qa

  Run->>TP: stage_pictures (L398-446) -> production/pictures.json (sha256)
  Run->>ObsImg: stage_observe_image [NEW] -> production/observed_images.json
  alt verdict != ACCEPT
    ObsImg-->>Run: StageRefused (BLOCKS LTX launch)
  end
  Run->>Scene: compose_prompt (L212-285) + build (L292-381) -> i2v_prompt_binding/1
  Scene->>LTX: verify actual_sha256 == binding.image_sha256 before submit
  LTX-->>Run: stage_clips (L901-1206) ingests clip into production/shot_clips/
  Run->>ObsVid: stage_observe_video [NEW] (VLM window -> FFmpeg/PyAV PTS + AudioEvidenceFusion)
  ObsVid->>Cut: select_cut_candidates (intentional cut-on-action allowed; mid-word blocked)
  ObsVid->>Sync: bind_audio_cue (av_events/1 + AudioOffsetPolicy -> stage_sound L1346-1485)
  Run->>Run: stage_assemble (L1557-1630) + verify_clock_alignment (L1599)
  Run->>QA: stage_qa (L1646-1713) -> BLOCKER halts all_gates_passed (L1708)
  QA-->>Run: write accepted end-state to production/continuity_memory.json
```

| # | Mandatory Question | Exact Verified File, Function & Line Range (`VERIFIED_CODE`) | V4.1 Action |
| :--- | :--- | :--- | :--- |
| 1 | Image-generation completion point | `explainer_engine/imagegen/turn_pack.py` (`ledger_rows`) consumed by `episode/run.py:stage_pictures` (`L398-446`) | Preserve Gemini Chat workflow intact |
| 2 | Image asset registration & SHA-256 | `episode/run.py:stage_pictures` (`L421, L435, L444-445`) writes `production/pictures.json` with `_sha(p)` | Reuse existing SHA-256 ledger |
| 3 | Image observation insertion point | Immediately after `stage_pictures` (`L446`) in `episode/run.py` via new `stage_observe_image` registered in `run_stage` (`L189-211`) | `MODIFY` `episode/run.py` + `NEW` `qa/observe_image.py` |
| 4 | Image observation verdict persistence | `ep.path("production/observed_images.json")` via `write_json_atomic` (`observed_image/1`) | Immutable per `sha256` |
| 5 | Video-prompt construction location | `explainer_engine/videolane/scene.py:compose_prompt(script, shot)` (`L212-285`) called by `build()` (`L292-381`) | Pass `ObservedImageState` into `compose_prompt`; emit `i2v_prompt_binding/1` |
| 6 | LTX submission location | `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` (uses `load_launch@L67`, `native_spec@L179`, `run_id@L258`) | Enforce binding check prior to Modal launch |
| 7 | SHA-256 enforcement point | Dual-enforced: `videolane/scene.py:build` (`L292-381`) AND `modal_ltx_jobs.py` pre-submit guard | Raise `ContractError("IMAGE_MUTATED_AFTER_OBSERVATION")` |
| 8 | Video generation return path | `episode/run.py:stage_clips` (`L901-1206`) ingests rendered/video clips into `production/shot_clips/` | Keep existing ingest contract |
| 9 | Video observation insertion point | Inside `stage_clips` after clip ingest (before `stage_sound@L1346` & `stage_assemble@L1557`) via `qa/observe_video.py` | Writes `production/observed_videos.json` (`observed_video/1`) |
| 10 | Exact PTS extraction location | `explainer_engine/core/media_clocks.py` (PyAV `av 10.0.0` / `ffprobe` stream timebase + PTS) called by `qa/observe_video.py` | Rational `Fraction` math only |
| 11 | Action-aware cut interface | `explainer_engine/edit/action_cut.py` feeding `videolane/plan.py:draft_edit_plans` & `stage_assemble` (`L1564-1574`) | Emits `cut_decision/1` |
| 12 | Audio event creation point | `episode/run.py:stage_clips` (`L923-924`) ALREADY calls `episode/events.py:events_report` -> `production/av_events.json`! | Extend `production/av_events.json` to `av_events/1` with `PLANNED_ONLY \| OBSERVED_ONLY \| MATCHED` |
| 13 | Audio offset application point | `episode/run.py:stage_sound` (`L1346-1485`) + `audio/sfx_planner.py` + `NEW` `audio/event_sync.py` | Apply `AudioOffsetPolicy` per `event_type` (never universal `0ms`) |
| 14 | QA blocker propagation | `episode/run.py:stage_qa` (`L1646-1713`) sets `all_gates_passed = acc["status"] == G.PASS and not rehearsal` (`L1708`); `check_before` (`L170-186`) raises `StageRefused` | Wire `qa/loop.py`, `qa/viewer_critic.py`, `qa/retry_router.py` into `stage_qa` & `check_before` |
| 15 | Final asset acceptance point | `episode/run.py:stage_qa` (`L1705-1710`) writes `production/production_manifest.json` + `qa/acceptance_report.json` | Gate on `qa_result/2` `BLOCKER == 0` |
| 16 | Continuity memory update point | `episode/run.py:stage_qa` (`L1709`, on `PASS`) writes `production/continuity_memory.json` (`continuity_memory/1`) | Read by next shot's `stage_observe_image` & `compose_prompt` |

---

## 2. Complete Crosswalk of All 21 Existing Skills & 16 Agents (`VERIFIED_CODE`)

Every single `.claude/skills/*/SKILL.md` (`21`) and `.claude/agents/*.md` (`16`) file was read and mapped so zero real craft knowledge is lost:

### 2.1 Existing 21 `.claude/skills/*/SKILL.md` Crosswalk
| Existing Skill (`Lines`) | Action | V4.1 Destination | Knowledge Retained / Relocated / Removed |
| :--- | :--- | :--- | :--- |
| `science-grounding` (`35`L) | **KEEP** | Skill #1: Historical Research | Claim-map & source verification retained verbatim. |
| `story-engine` (`130`L) | **MERGE** | Skill #2: Narrative Dramaturgy | 7-stage writers' room skeleton retained; model routing delegated to `RouteRegistry`. |
| `narration-script` (`303`L) | **MERGE** | Skill #2: Narrative Dramaturgy | All `N-01..N-17` spoken-ear rules retained verbatim in `docs/expert_library/dramaturgy/`. |
| `crossover-episode` (`70`L) | **RELOCATE** | `docs/expert_library/dramaturgy/crossover.md` | Format-specific template moved to reference library. |
| `time-jump-episode` (`27`L) | **RELOCATE** | `docs/expert_library/dramaturgy/time_jump.md` | Format-specific template moved to reference library. |
| `shot-visuals` (`201`L) | **MERGE** | Skill #3: Cinematography & Staging + Skill #5: Visual Keyframe | Stakes-in-frame, `UR-22` one-world rule, `D-43` still route retained. |
| `visual-beats` (`113`L) | **MERGE** | Skill #3: Cinematography & Staging | `VB-01..VB-11` visual beat pacing rules retained verbatim. |
| `animated-universe` (`55`L) | **MERGE** | Skill #4: Continuity & Style Bible | Silhouette, proportion, one-key-light rules retained; retired 2026-10-22 history removed. |
| `animation-principles` (`85`L) | **KEEP** | Skill #6: 2.5D Motion & Animation + Skill #8: Character Acting | All 12 animation principles, holds/blinks/feet, `P8` acting checklist retained verbatim. |
| `dialogue-scenes` (`192`L) | **MERGE** | Skill #8: Character Acting + Skill #2: Narrative | `SC-01..09`, Johnston's 8 questions, narrator<->scene handoff retained verbatim. |
| `cartography` (`72`L) | **UPGRADE** | Skill #9: **3D Blender Cartography & DataViz** | Existing glance-readability rules retained + upgraded with Blender 3D DEM/Geometry Nodes/CC0 stack (`WP-B1`). |
| `elevenlabs-voice` (`111`L) | **RELOCATE / TOOL REF** | Skill #10: Audio, Foley & Music (`docs/expert_library/audio/`) | `EL-01..EL-13` v4 tags & credit-saving rules preserved as Tool Reference. |
| `voice-search` (`53`L) | **MERGE** | Skill #10: Audio, Foley & Music | `VC-01..VC-10` age-first voice casting rules retained. |
| `editing-style` (`167`L) | **MERGE** | Skill #11: Editorial & Montage | Cut/dissolve/zoom/sound-layering rules retained verbatim. |
| `video-editing-architect` (`310`L) | **MERGE** | Skill #11: Editorial & Montage | Full 310-line genre-to-style & cut-type framework retained verbatim in `docs/expert_library/editorial/`. |
| `shorts-for-video` (`97`L) | **RELOCATE** | `docs/expert_library/editorial/shorts_packaging.md` | 3-second hook & Shorts packaging checklist retained. |
| `modal-operations` (`43`L) | **RELOCATE / TOOL REF** | `docs/expert_library/ops/modal_ltx.md` + `RouteRegistry` | Billing/Volume rules enforced deterministically in Python `RouteRegistry`; CLI notes in ref library. |
| `cloud-cost-audit` (`35`L) | **RELOCATE** | `RouteRegistry` (`OR-22..36`) | Deterministic pre-launch spend caps enforced in Python. |
| `cloud-provider-selection` (`43`L) | **RELOCATE** | `RouteRegistry` | Deterministic VRAM/RAM ranking in Python. |
| `hyperstack-operations` (`37`L) | **RETIRE / ARCHIVE** | Legacy ops archive | Not used on active Modal LTX-2.5 path. |
| `lora-training` (`59`L) | **RETIRE (`D-131`)** | Retired era archive | Qwen-Image `xworld` LoRA retired by `config/retired_era.json`. |

### 2.2 Existing 16 `.claude/agents/*.md` Crosswalk
- **11 Stage-Page Agents (`OR-20, D-79`, NOT spawned separately):** `story-architect`, `scene-writer`, `beat-writer`, `performance-director`, `edit-planner`, `voice-caster`, `shorts-writer`, `shot-continuity-writer`, `episode-standards-director`, `orchestrator`, `paid-run-watchdog` -> **MERGE** their stage checklists into the corresponding 12 Core Domain Skills (`paid-run-watchdog` stays as lightweight Haiku monitor for paid runs).
- **1 Clean-Room Critic (`script-critic`, `96`L, fresh context):** **KEEP** and align with Skill #12 (Film QA & Defect Auditing) + `qa/viewer_critic.py`.
- **4 Retired LoRA Agents (`lora-checkpoint-judge`, `lora-coordinator`, `lora-dataset-auditor`, `lora-run-operator`):** **RETIRE (`D-131`)** — all four govern the retired Qwen-Image `xworld` LoRA.

---

## 3. Level B (Detectable) & Level C (Merge-Enforced) Implementation Lock Design

Because `V4_1_IMPLEMENTATION_MANIFEST.yaml` alone is **Level A (Instructional)**, V4.1 specifies concrete Level B and Level C mechanisms (for Creator approval before implementation):

### Level B — Detectable Scope Validator (`explainer_engine/governance/check_wp_scope.py` — `PROPOSED`, wired into `governance/hooks.py:pre_write@L200-221`)
- **Inputs:** `--manifest V4_1_IMPLEMENTATION_MANIFEST.yaml --wp WP-02 --base-ref argon/p1-2-timing-contract`.
- **Checks:** Parses `git diff --name-status` (including renames `-M`) + `git ls-files --others --exclude-standard` (untracked files); verifies every modified path matches `allowed_modify`, every added path matches `allowed_create`, and zero paths touch `global_forbidden_without_creator_approval` (`config/{picture_route,model_routing,spend_caps,retired_era}.json`).
- **Behavior:** Exits `2` (Claude Code `PreToolUse` hard block) with actionable stderr listing offending paths and the active WP ID.

### Level C — Merge Enforcement (`.github/workflows/quality.yml` + GitHub Branch Protection)
- **CI Job Addition (`quality.yml`):** Adds a `wp-scope-and-manifest` step running `python3 -m explainer_engine.governance.check_wp_scope`, `python3 -m explainer_engine.docs_lint`, and `PYTHONPATH=tests/unit:. python3 -m pytest -m "unit" -q` on every PR targeting `argon/v4-1-closed-loop` or `main`.
- **Repository Setting Requirement (Cannot Be Enforced by YAML Alone):** Creator must enable GitHub Branch Protection ("Require status checks to pass before merging" + "Require pull request review" for protected `config/` paths).

---

## 4. Test Environment Specification (`VERIFIED_CODE` / `VERIFIED_TEST`)
- **Supported Interpreter & Manager:** Python `3.11+` (`3.12` in `.github/workflows/quality.yml`; `3.12/3.13` in `setup.ps1`), `pip install -r requirements.txt` + `apt-get install ffmpeg`.
- **Exact Offline Read-Only Test Command (Verified Working Here):**
  ```bash
  PYTHONPATH=tests/unit:. python3 -m pytest -p no:cacheprovider --basetemp=/tmp/v41_pytest -q \
    tests/unit/test_audio_timing.py tests/unit/test_blind_check.py tests/unit/test_cloud_hooks_modal.py \
    tests/unit/test_governance_hooks.py tests/unit/test_retry_router.py tests/unit/test_shot_router.py \
    tests/unit/test_superres.py tests/unit/test_v43_retired.py \
    tests/unit/test_v4_2_reconciliation_and_viewer_critic.py tests/unit/test_videolane.py tests/unit/test_videolane_media.py
  # Verified result on 0592114: 164 passed, 0 failed, 1 skipped
  ```
- **Offline vs. Paid Split:** `-m unit` & `-m integration` run `$0.00` offline; `-m media` requires local sound WAVs; `-m system` / Modal / Gemini live calls require explicit Creator approval & secrets (`presence_check.yml`).

---

## 5. 1914 Media Access Manifest (Explicit Unresolved Blocker)
Direct search confirmed `vano1919/tmr-artifacts` is **not publicly indexed** on Hugging Face and the sandbox VM has no outbound internet/HF token. The following exact assets referenced in `CORRECTIONS_LOG.md`, `37_SLICE_REVIEW_1.md`, and `24_OPUS_VISUAL_CHECK_MAPS_S8.md` must be fetched on an authenticated Creator/Argon machine before visual/audio regression calibration in `WP-03`/`WP-04`:
1. `S06_SH008`: `explainer-engine/ltx_route/out/c441511c56ed_fc6ae61bf410/S05_SH008/S06_SH008_seed7303.mp4` + `S06_SH008_start_fix2.png`
2. `S03_SH007`: `explainer-engine/ltx_route/out/049b3979fea2_fc6ae61bf410/S03_SH001/S03_SH007_seed7105.mp4`
3. `S03_SH003`: `explainer-engine/ltx_route/out/dd951163fc4b_fc6ae61bf410/S03_SH003/S03_SH003_seed7200.mp4`
4. `S04_SH014`: `explainer-engine/ltx_route/out/e9359d80a54a_fc6ae61bf410/S04_SH008/S04_SH014_seed7105.mp4`
5. `S07_SH005`: `explainer-engine/demo_truce_1914/ltx_R3_2026-11-14/clips/S07_SH005_seed7111.mp4`
6. `S07_SH006`: `explainer-engine/ltx_route/out/e19396806270_fc6ae61bf410/S07_SH002/S07_SH006_seed7104.mp4`
7. `2.5D V1–V6`: `argon_loop_2026-11-15/task2_slice_r1/{S08_SH002_t2,S02_SH008_t2,S05_SH020_t2}.mp4`
8. `Maps S8`: `argon_loop_2026-11-15/maps_our_code_after_s8/maps_new_reel.mp4`
