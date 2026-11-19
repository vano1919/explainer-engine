# Explainer Engine V4.1 — Master Architecture & Decision Brief

- **Document ID:** `V4.1-DOC-01` (`V4.1-IMPL-BLUEPRINT-001`)
- **Date:** `2026-11-19`
- **Verified Git Baseline:** `vano1919/explainer-engine`, branch `argon/p1-2-timing-contract`, `HEAD = 0592114c6c2d44a9af00b11553f169516e175864` (code baseline `eb80e4434ea120f48cb9aea094ebd7b2b423d8f0`), `git status --short` clean, `python3 -m explainer_engine.docs_lint` -> `0 finding(s)` (`VERIFIED_CODE`).
- **Companion Package Files (Untracked Research Output Directory):**
  - `V4_1_FILE_BY_FILE_IMPLEMENTATION_PLAN.md` (`V4.1-DOC-02`)
  - `V4_1_DATA_CONTRACTS_AND_QA_SPECIFICATION.md` (`V4.1-DOC-03`)
  - `V4_1_EXTERNAL_RESEARCH_AND_EVIDENCE_REGISTER.md` (`V4.1-DOC-04`)
  - `V4_1_CLAUDE_REVIEW_AND_IMPLEMENTATION_GUARDRAILS.md` (`V4.1-DOC-05`)
  - `V4_1_IMPLEMENTATION_MANIFEST.yaml` (`V4.1-MANIFEST-01`)

---

## 1. Executive Summary & Confirmed V4.1 Direction

Explainer Engine V4.1 transitions the production pipeline from an **open-loop waterfall** (where written plans dictate video prompts, cuts, and SFX) to a **Closed-Loop, Observation-Driven Hybrid Core** (`Intent -> Generate -> Observe -> Evaluate -> Adapt -> Approve -> Continue`) governed by one inviolable rule:

> **Governing Invariant:** *No downstream stage may treat an unverified assumption from a previous stage as fact.*

### Real AST Call-Graph Discovery (`VERIFIED_CODE`)
Direct AST inspection of `explainer_engine/episode/run.py` (`1,790` lines, `57` top-level definitions, `0` dynamic `import_module` calls) corrected earlier grep-based assumptions:
- **Actually Connected to `episode/run.py`:** `production.understand`, `production.directed25d`, `production.layers25d`, `qa.final_frame_qa`, `qa.look_and_listen`, `qa.motion_intent`, `qa.sound_realism`, `videolane.{plan,ingest,failure,voice,line_reads,master_qa}`, `orchestration.rule_enforcer.run_all_gate_audits`, `production.map_clip.render_action_map_clip`, and `training.pods.ltx.modal_ltx_jobs`.
- **Indirectly Connected:** `finish.superres` is imported by `imagegen/turn_pack.py`, `finish/frame_pick.py`, and `training/pods/ltx/modal_ltx_jobs.py` (not directly by `episode/run.py`).
- **Truly Disconnected from `episode/run.py`:**
  - `qa/viewer_critic.py`: **`0` callers** across all `511` Python files.
  - `qa/retry_router.py`: **`1` legacy caller** (`explainer_engine/blender/validate.py`), `0` in `episode/run.py`.
  - `qa/blind_check.py`: imported only by `qa/keyframe_gate.py`, which has **`0` callers** in `episode/run.py`.
- **Existing Blender Assets (`VERIFIED_CODE`):** `explainer_engine/blender/` already contains **`55` Python files**, including `blender/polyhaven.py` (`295`L, MIT-derived Poly Haven API + ETag + MD5 + zip-slip guard + Blender 5.2 HDRI world nodes) and `blender/terrain.py` (`209`L, deterministic fBm terrain height field).

---

## 2. Five Mandatory V4.1 Amendments + Creator 3D 10% Blender Amendment

| Amendment | Core Rule | Owning Modules / Specs |
| :--- | :--- | :--- |
| **Amendment A — Adaptive Video Inspection Router** | Route clip inspection by risk & length (simple/short -> deterministic frames + VLM; rapid motion -> dense sampling; complex action -> VLM + native frames; long event search -> Gemini Agentic Video; exact final cut -> Python PTS; audio-critical -> audio fusion). | `qa/video_inspection_router.py` (`V4.1-DOC-02 §WP-03`, `V4.1-DOC-03 §3`) |
| **Amendment B — Separate Audio & Video Clocks** | Never merge video frame PTS and audio sample position into a single `float` timestamp. Maintain rational integer `VideoClockTimestamp`, `AudioClockTimestamp`, and `TimelineClockMapping` handling CFR, VFR, encoder priming/delay, stream offsets, and edit lists. | `core/media_clocks.py` (`V4.1-DOC-03 §5`) |
| **Amendment C — Intentional Cut-on-Action** | Never forbid cutting during motion. Distinguish accidental unresolved cuts vs. deliberate cut-on-action, post-resolution cuts, dramatic interruptions, mid-word phonetic cuts (blocked), and J/L-cuts. Editorial Skill decides; Python executes. | `edit/action_cut.py` (`V4.1-DOC-02 §WP-04`, `V4.1-DOC-03 §6`) |
| **Amendment D — Genuine Cross-Vendor Evaluation** | Explicit model IDs + verified native media capabilities (`Interactions API`). Google-generated images/video reviewed by Claude (or non-Google route via sampled frames + separate audio when native video unavailable); LTX video reviewed by Gemini (`gemini-3.8-flash` / `gemini-4-argon`); Creator retains final tie-break. | `core/route_registry.py`, `qa/cross_vendor_critic.py` (`V4.1-DOC-03 §8`) |
| **Amendment E — Audio Evidence Fusion & Calibration** | Treat `VAD`, `ASR` (`WhisperX`), `Forced Alignment` (conditional on transcript), `Waveform/Spectral`, `VLM`, and `Script Comparison` as **correlated signals** fused via `AudioEvidenceFusion` emitting `PASS \| FAIL \| WARN \| HUMAN_REVIEW \| INSUFFICIENT_EVIDENCE`, calibrated on 1914 fixtures (zero invented thresholds). | `audio/evidence_fusion.py` (`V4.1-DOC-03 §7`) |
| **Creator Amendment F — 10% 3D Blender Cartography & Infographics (`ADR-V41-11`)** | **Move the ~10% visual helper lane (maps, timelines, troop movements, tactical diagrams, data charts) to high-quality 3D Blender** backed by free `CC0`/open libraries (`Poly Haven`, `ambientCG`, `Smithsonian 3D`, `Quaternius`, `BlenderGIS`/SRTM, `Sonniss GDC` + `Freesound CC0` SFX) and dedicated 3D styling/sound skills. **Requires explicit Creator `D-131` narrow carve-out** (Blender remains retired for character acting/hero 2D scenes; validated first in isolated `WP-B1` before production promotion). | `experimental/blender_lab/` -> `production/blender_3d_helpers/` (`V4.1-DOC-02 §WP-B1`, `V4.1-DOC-04 §3`) |

---

## 3. Architectural Comparison: V2.1 vs. V3 vs. V4.1

| Area | V2.1 | V3 | V4.1 (Final) | Rationale |
| :--- | :--- | :--- | :--- | :--- |
| **Production Loop** | Open-loop waterfall | Deterministic-first, open-loop | **Closed-loop (`Observe -> Evaluate -> Adapt`)** | Fixes 1914 `CORRECTIONS_LOG.md` root causes (`S06_SH008`, `S03_SH007`, `S03_SH003`, `S04_SH014`, `S07_SH005/006`). |
| **Orchestration** | `CentralDirector` + 5 LLM orchestrators | `episode/run.py` | **Keep `episode/run.py` + `RouteRegistry`** | `VERIFIED_CODE`: `1,790`L working state machine; zero LLM orchestrator bloat. |
| **Domain Skills** | 14 Domain + 12 Tool | 8 Domain, 0 Tool | **12 Core Domain Skills (+ 3D Blender Cartography/Motion expansion) + Flexible Tool Knowledge + `docs/expert_library/`** | Prevents V3 over-compression of Audio/Editorial/QA while keeping Python deterministic. |
| **Timing & Clocks** | Planned float seconds | `episode/timing.py` | **Separate Rational Video & Audio Clocks (`media_clocks.py`) + Event Timeline (`av_events/1`)** | Eliminates float drift, encoder-priming shifts, and mid-word/early-SFX desync. |
| **Inspection** | Keyframe gate only | Unified `qa/` | **Adaptive Video Inspection Router + `AudioEvidenceFusion` + True Cross-Vendor Critic** | Cost-efficient funnel; no single VLM or ASR trusted blindly. |
| **10% Helper / Map Lane** | 2D `maps/` | 2D `maps/` | **High-Quality 3D Blender Cartography, Terrain & Infographics (`WP-B1` gated carve-out from `D-131`)** | Replaces blurry/flat 2D `24_OPUS` maps with cinematic 3D terrain, Geometry Nodes, PBR textures, and synced Foley. |
| **Lane Mix Ratio** | Fixed 60/30/10 | Fixed 60/30/10 | **Advisory Only (Flexible to Narrative Need)** | Never forces 2.5D where cinematic video wins. |

---

## 4. Final Architecture Decisions (`ADR-V41-01` .. `ADR-V41-11`)

- `ADR-V41-01`: Retain `episode/run.py` as sole deterministic state machine; introduce immutable `RouteRegistry` (`core/route_registry.py`).
- `ADR-V41-02`: Enforce `Plan-vs-Observed` immutability (`shot_intent/1`, `observed_image/1`, `i2v_prompt_binding/1`, `observed_video/1`, `continuity_memory/1`).
- `ADR-V41-03`: Deploy `AdaptiveVideoInspectionRouter` (Amendment A) with Interactions API and explicit versioned model IDs (Amendment D).
- `ADR-V41-04`: Separate rational integer Video & Audio Clocks (`media_clocks.py`, Amendment B) and Event-Type Offset Policy (`av_events/1`).
- `ADR-V41-05`: Support Intentional Cut-on-Action (Amendment C) owned by Editorial & Montage Skill and executed by Python.
- `ADR-V41-06`: Fuse 6 correlated audio signals via `AudioEvidenceFusion` (Amendment E), calibrated on 1914 fixtures.
- `ADR-V41-07`: Wire disconnected QA modules (`viewer_critic.py`, `blind_check.py`, `retry_router.py` with `REWEIGHT_REFERENCES`) as stage-specific blocking gates (`BLOCKER | MAJOR | MINOR | INFO`).
- `ADR-V41-08`: Keep `finish/superres.py` CPU default (evaluated on identity/hallucination, not LPIPS alone); gate `SeedVR2` (`FP16/FP8`) strictly to degraded clips.
- `ADR-V41-09`: Benchmark `layers25d.py` vs. `directed25d.py` head-to-head on `V1–V6` before selecting production 2.5D renderer.
- `ADR-V41-10`: Split paid experiments into separate Creator-approved caps (Video Gen/Retake, Restoration, Foley) and enforce Modal cost-trap rules (`H100 ~$3.95/hr`, Sandbox `3x` CPU/RAM only, `1.15x` broad-region, `keep-alive <= 15s`, in-worker MP4 encode).
- `ADR-V41-11`: **Creator-Directed 10% 3D Blender Cartography & Infographics Track** — reuse existing `explainer_engine/blender/{polyhaven.py,terrain.py,camera_rigs.py}` + free CC0 libraries (`Poly Haven`, `ambientCG`, `Smithsonian 3D`, `Quaternius`, `BlenderGIS`, `Sonniss GDC`/`Freesound CC0` SFX), validated first in `WP-B1` before narrow `D-131` carve-out for the 10% helper lane only.

---

## 5. High-Level Dependency Graph

```text
[WP-00: Baseline & Test Triage]
        │
        ▼
[WP-01: Data Contracts, Clocks & RouteRegistry]
        │
        ▼
[WP-02: Single-Shot Closed-Loop Proof (MILESTONE 1)]
        │
        ├──► [WP-03: Adaptive Observe & Audio Evidence Fusion]
        │            │
        │            ▼
        │    [WP-04: Action-Aware Editing & Event Sync]
        │            │
        │            ▼
        ├──► [WP-05: Wire Disconnected QA & Media Modules]
        │            │
        │            ▼
        ├──► [WP-06: 2.5D Benchmark (layers25d vs directed25d)]
        │            │
        │            ▼
        └──► [WP-07: Split Paid Benchmarks (Video / Restoration / Foley)]
                     │
                     ▼
             [WP-08: 60-Second End-to-End Vertical Slice]
                     │
                     ▼
             [WP-09: 12-Minute Full Episode Validation]
                     │
                     ▼
             [WP-10: 12+1 Skills Consolidation & Optional .otio]

[Parallel WP-B1: 3D Blender 10% Cartography/Infographics Lab (Free CC0 Stack)]
        └──► Creator D-131 Narrow Carve-Out ──► Feeds WP-08 / WP-09 10% Lane
```

---

## 6. Decisions Requiring Explicit Creator Approval

1. **Approve V4.1 Blueprint (`ADR-V41-01..11`)** after Claude's independent review (`V4_1_CLAUDE_INDEPENDENT_REVIEW.md`).
2. **Approve Narrow `D-131` Carve-Out (`ADR-V41-11`):** Confirm that Blender moves from `retired` to `production` **exclusively** for the ~10% 3D Maps/Infographics/Spatial Diagrams lane after `WP-B1` visual validation, while remaining retired for character/hero 2D scenes.
3. **Approve Split Experiment Caps (`WP-07`):** Separate caps for Experiment 1 (Video/Retake: `$5–$8`), Experiment 2 (Restoration: `$2–$3`), and Experiment 3 (Foley: `$1.50–$2.50`, plus commercial decision on `HunyuanVideo-Foley` EU/UK/KR territorial exclusion).
4. **Approve Single Active Implementation Branch:** e.g., `argon/v4-1-closed-loop` created off `argon/p1-2-timing-contract` (`0592114`) once implementation begins.

---

## 7. Refined 10% Helper Lane Split (Blender 3D vs. 2D Motion Graphics vs. FFmpeg)

Per Creator alignment (`2026-11-19`), the ~10% explanatory/helper lane is split by spatial necessity rather than forcing simple typography into 3D:

| Helper / Visual Element | Assigned Engine | Rationale |
| :--- | :--- | :--- |
| **Historical Maps & Frontlines** | **Blender 3D** | 3D DEM/SRTM terrain (`BlenderGIS` / `blender/terrain.py`), Geometry Nodes frontlines, Poly Haven HDRI lighting |
| **Troop Movements on Map** | **Blender 3D** | Depth-aware animated arrows/markers hugging 3D relief with camera parallax |
| **Territorial Change Visualization** | **Blender 3D** | Animated shader masks & elevation borders across 3D historical terrain |
| **Camera Flights Over Map Surface** | **Blender 3D** | True 3D camera rigs (`blender/camera_rigs.py`) + depth-of-field |
| **Complex Historical Spatial Reconstruction** | **Blender 3D** | Trench cross-sections, fortifications, battlefield geometry (`WP-B1`) |
| **Casualty / Troop Counters** | **2D Motion Graphics or Blender** | 2D overlay for rapid narration beats; Blender 3D when anchored directly onto a 3D map |
| **Statistical Diagrams & Charts** | **2D (Default)** | Use clean 2D unless true 3D spatial comparison adds clarity |
| **Simple Text, Subtitles, Titles** | **FFmpeg / 2D Only** | Fast, crisp, deterministic alignment via `av_events/1` without 3D overhead |
