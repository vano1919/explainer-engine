# Project brief

> **Route-scoped since D-116 (2026-11-06); updated 2026-11-09 by D-123 (4-Stage Local Hybrid B -> C Rebuild).**

## Mission

A sustainable, solo-operated, faceless YouTube channel with a recognisable identity: stylized **2.5D Ink Chronicle** historical What-If docudrama episodes, natural documentary narration paired with dramatized character dialogue, purposeful motion and visual storytelling; plus a 4-stage, 100% local and free-by-default QA-gated production pipeline (D-123). Entertaining and analytical, never a dry lecture or a generic AI slideshow.

## Hard constraints (the creator's; precedence level 2)

* **Local-Only Execution Rule (D-123):** All default image, video, and 2.5D parallax generation runs locally and free via ComfyUI (`http://127.0.0.1:8188`, `EXPLAINER_LOCAL_ONLY=1`). Paid cloud endpoints are disabled by default and gated behind explicit creator opt-in.

* Hardware baseline: Local workstation running ComfyUI (`config/local_models.json`); legacy baseline notes (D-11) remain in the decision log.

* Budgets are ceilings (`config/spend_caps.json`, D-56); vidIQ <= 200 credits; no subscriptions without a clear need (ledger: [COST_AND_TIME_MODEL](COST_AND_TIME_MODEL.md)).

* No automatic public upload; the creator approves every publication (D-16 policy checks included).

* Original characters and visuals only: no third-party IP, footage or protected styles as the core identity.

* Facts must be sourced and checked; sensitive areas (politics, history, finance, health) get stricter review.

## Positioning & Visual Mix (D-25, D-09, D-95, D-96, D-123)

**"Worlds collide" & Historical What-If Docudrama**: what happens when a pivotal historical decision, battle, or collision of worlds unfolds differently. Each episode establishes the real history with verified sources (`actual_history`), introduces one concrete point of divergence (`divergence_point`), traces first-, second-, and third-order consequences (`counterfactual_consequence`), and explicitly signals counterfactual speculation (`historical_reflection`). English, general audience (teens and adults), set "not made for kids" (D-17). Crossover analysis episodes follow [RIGHTS_AND_FAIR_USE](RIGHTS_AND_FAIR_USE.md) (D-26). Allowed formats and scripting rules: [MAIN_METHOD](MAIN_METHOD.md) and [SCRIPTING_SPEC](SCRIPTING_SPEC.md).

* **Spoken Balance Target (D-95, D-123):** **70-80% narrator voiceover** (`0.70-0.80`) and **20-30% dramatized character dialogue** (`0.20-0.30`).

* **Flexible Visual Mix Guideline (D-93, D-123):** Approximately **60% cinematic video** (`WAN_I2V` / `WAN_FLF2V`, plus selective `WAN_CONTROL`), **30% composed historical illustrations** (`STILL_25D` animated via deterministic 2.5D parallax), and **10% animated maps** (`MAP_25D`). This 60/30/10 split is a flexible storytelling guideline, not a rigid mathematical quota.

* **Visual Direction:** Stylized **2.5D Ink Chronicle** aesthetic (D-96 scoped by D-123: bold ink linework, painterly chiaroscuro shading, muted period palette, decoupled from mandatory Blender 3D scene building and LTX multi-keyframe video diffusion).

## Products (D-123)

* **Long-form Canonical Format:** **12 minutes (`720` seconds target, acceptable window `660-780s`)** at **24 fps** (D-85), structured into **5 narrative phases (`Z1-Z5`)** and **16 segments (`S01-S16`)** inside a single canonical `production_script.json` (`explainer_engine/schemas/production_script.schema.json` v4.0.0).

* **Shorts:** Two to five standalone Shorts per long-form, each recomposed for 9:16 from the verified dossier (D-05, D-92).

* **Per-Episode Package:** `01_script/research_dossier.md` + `01_script/production_script.json` (SSOT), `02_keyframes/` (approved character turnarounds, location/prop anchors, and shot start/end keyframes in `keyframe_manifest.json`), `03_video/` (rendered 24fps clips + `wan_jobs_manifest.json` + `render_telemetry.jsonl`), and `04_assembly/` (`episode_master_24fps.mp4` + `qa_report.json`).

## Success for the first cycle (not performance promises)

The 60-second 12-shot Waterloo pilot (`tests/fixtures/pilot_60s_waterloo.json`) and Phase 1 ablations pass their acceptance criteria ([IMPLEMENTATION_PLAN](IMPLEMENTATION_PLAN.md)); then full 12-minute episodes are produced with logged local telemetry and compared like with like ([PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md)). No virality, CTR, retention, income or monetisation approval is promised anywhere in this project.

## Out of scope

Auto-upload; paid cloud inference by default; geopolitical satire; kids' content; personal-finance advice; copying any competitor's titles, scripts, thumbnails or style; multi-channel "factory" cloning (SE-22); realistic synthetic people or events.