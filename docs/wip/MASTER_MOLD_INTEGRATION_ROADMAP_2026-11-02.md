# ARGON — FULL-CONTEXT MASTER MOLD v2.1.0 INTEGRATION ROADMAP

* **Document Path:** `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`

* **Date:** `2026-11-02`

* **Repository:** [vano1919/explainer-engine](https://github.com/vano1919/explainer-engine)

* **Target Work Branch:** [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02)

* **Branch Base (PR #119 HEAD):** `5013a55aca5a17a3734150f61a5eb172abcbe3b8` ([PR #119](https://github.com/vano1919/explainer-engine/pull/119), 51 commits ahead of `main`)

* **Default Branch (`main`) Baseline:** `6e1dccad30a865df670c258c86ffa1152a0dbe7e` (`STATUS table up to date + OR-36 Haiku watchdog for every paid run (#118)`)

* **Secondary Open Draft PR:** [PR #112](https://github.com/vano1919/explainer-engine/pull/112) (`1273619bb52930dde659b6f07a0999141d8ec76b`, 1 commit ahead, 29 behind `main`)

* **Inspected Evidence Corpus:**

  1. Complete `repo_5013a55a.zip` snapshot (`1,287` tracked files at `5013a55aca5a17a3734150f61a5eb172abcbe3b8`) + `pr119_diff.patch` (`501 KB`, `77` changed files, `+5,576 / -336` lines), `pr119_log.txt` (`51` commits), `pr112_show.patch` (`5` files, `+27 / -3` lines), and `main_recent_log.patch` (`493 KB`).

  2. Complete 214-page `CrossWorld_Chronicles_Organized_Research_for_Gemini.docx` (`874` paragraphs, `42` tables, `166` headings across Parts I–IV and Appendices A–B).

  3. Canonical Master Video Mold specification `mrbeast_12min_master_mold.md` (`431` lines, `117,220` bytes, internal header `schema_version: 2.0.0`, external contract label `v2.1.0`, verified SHA-256 `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e`, Git blob SHA `c928c92e65a2357d3dc511b732edb4b1232301d9`; prior header string `316d8042...` retired as an unverified external draft hash — see §1.3).

  4. Canonical Master Video Mold JSON contract `mrbeast_12min_video_mold (1).json` (`26,291` lines / `26,292` with trailing newline, `1,109,253` bytes, internal `mold_meta.schema_version: "2.0.0"`, external contract label `v2.1.0`, verified SHA-256 `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0`, Git blob SHA `80fc3b99294fd880fdbb7674bdfc2f7197822d2f`; prior header string `89aa56d2...` and external Windows path hash `173EFDA0...` retired as inaccessible outside container — see §1.3).

  5. Complete `ARGON_READ_ONLY_AUDIT_AND_CONSOLIDATION_PLAN_2026-11-02.md` and `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md`.

## 1. Executive Assessment

### 1.1 Architectural Verdict

* **\[FACT\]** At commit `5013a55aca5a17a3734150f61a5eb172abcbe3b8` ([PR #119](https://github.com/vano1919/explainer-engine/pull/119)), [vano1919/explainer-engine](https://github.com/vano1919/explainer-engine) already contains a strong, modular foundation for a 12-minute (`720s`) 2D animated docudrama pipeline (`BP-167`, `BP-109`, `BP-141`, `BP-169..172`, `edit/rhythm_profile.py`, `edit/dramatic_still.py`, `scripting/rhythm_lint.py`, `audio/hype_read.py`, `audio/narrator_polish.py`, `finish/upscale.py`, and `schemas/production_script.schema.json` `/4`), passing `2,448` unit tests in GitHub Actions run `41345477655`.

* **\[OBSERVATION\]** However, the MrBeast-inspired rhythm package introduced in [PR #119](https://github.com/vano1919/explainer-engine/pull/119) (`WP-R1..R6-part, R8, R11-part, R12`) currently operates as an **isolated post-hoc validation layer** rather than an end-to-end generative architecture. Specifically:

  1. **Zero Upstream Agent/Skill Awareness**: None of the `16` agent stage pages in `.claude/agents/*.md` or the `16` skills in `.claude/skills/*/SKILL.md` mention `production_script/4`, `BP-169..172`, `rhythm_zone`, `dramatic_change`, the 12-minute (`720s`) target (`BP-167`), the new narrator **Odom** (`CcSJ2r3qw0XU9gJpEPyk`), or the Master Mold's 12 Anchor Beats (`AB01..AB12`). In fact, `.claude/agents/story-architect.md` still instructs writing a 15-minute docudrama at `170 WPM` (`BP-01`), and `.claude/skills/elevenlabs-voice/SKILL.md` still names retired narrator `Grandpa Spuds Oxley` (`NOpBlnGInO9m6vDvFkFC`).

  2. **P0 Silent Schema-Version Regression Across 11 Core Modules**: While `explainer_engine/edit/rhythm_profile.py:39` correctly uses `int(tail) <= 3` to distinguish legacy `/1..3` scripts from `/4`, **11 core validator, gate, and production modules** (`scripting/scene_lint.py:139`, `scripting/script_approval.py:51`, `scripting/speech.py:60`, `scripting/story_lint.py:75`, `production/beats.py:107`, `production/editorial_gate.py:342,347`, `production/silent.py:249,276`, `production/staging.py:418`, `production/validate.py:89`, `production_gate.py:89`, and `audio/layers.py:53`) still check exact string equality `== "production_script/3"` (via `SCENE_SCHEMA` or `_sa.BINDING`). Consequently, passing a `"production_script/4"` script into `production validate`, `editorial_gate`, or `production_gate` **silently disables `/3` scene/dialogue enforcement (`SC-01..SC-10`), script approval checks (`PV-53` and Gate `0.9` in `production_gate.py:89`), living-person voice bans (`PV-55`, `D-62`), character signature-word checks (`DW-11` in `speech.py`), staged-dialogue master-frame checks (`CS-07` in `staging.py`), `ST-00` FAIL severity (`story_lint.py`), and `editorial_review/2` (`story_page.md` in `editorial_gate.py`)**, and **reverts `production/beats.py` back to `/2`'s 1.5s metronome and mandatory sound cues**!

  3. **Unwired Midstream & Downstream Modules (`WP-R7`, `WP-R9`, `WP-R10`)**: `scripting/variant_plan.py`, `scripting/story_lint.py`, `scripting/narration_lint.py`, `scripting/film_shots.py`, `edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, `production/timing.py`, `production/beats.py`, `production/fill_holds.py`, `production/validate.py`, `audio/layers.py`, `audio/sound_director.py`, `qa/engagement.py`, and `qa/scorecard.py` still evaluate scripts against flat calm-era constants (`BP-01` `170 WPM`, `BP-107` `11–17 shots/min`, `BP-40` `10 pictures/min`, and `fps=30` defaults in `timing.py:75`, `motion_lint.py:128`, `assemble.py:1036`).

  4. **Five Internal Discrepancies Between Mold v2.1.0 (`.md` vs `.json`) and `sourced_rules.json` (`BP-169..172`)**: As detailed in Section 3.2, `mrbeast_12min_video_mold.json` v2.1.0 still contains 5 internal mismatches against `MRBEAST_12MIN_MASTER_MOLD.md` v2.1.0 and `explainer_engine/standards/sourced_rules.json` (Zone ID naming `Z1_HOOK_0_30S` vs `hook_0_30s`; duplicate/divergent zone WPM and TTS tag lists violating `D-59`; `bp141_non_character_max: 0.8` instead of `0.45` on Profiles A and D; Still Motion Ladder Tier 1/2 vs `BP-170` `dramatic_still.py` rejection; and Layer 1 Anchor Beats `AB07..AB12` window/segment drift against Layer 3 `S09..S16`).

* **\[RECOMMENDATION\]** Do **not** rewrite the engine. Integrate Master Mold v2.1.0 through **9 free, dependency-ordered engineering batches (`BATCH-M0` through `BATCH-M7` plus `BATCH-M8A`)** followed by **1 strictly gated paid stage (`BATCH-M8B` with 4 sequential creator approval gates `GATE-P1..P4`)** that:

  1. Fix the P0 `== "production_script/3"` bug across all **11 modules** immediately via an explicit two-predicate schema dispatch module (`explainer_engine/scripting/schema_version.py`: `is_scene_script` for `/3` and `/4`, `is_zoned_rhythm_script` for `/4`, accepting either `doc` dicts with `"schema"`/`"script_schema"` or raw schema strings), implement post-`voice_check` / post-`pause_pad` narrator-span-only Odom polish on `narration.wav` (`polish_narrator_spans_in_place`, preserving raw timbre drift checks and `.mp3` chunk compatibility while leaving character dialogue turns untouched), and resolve `rhythm_zone` across all shots (including `teaser_of`) in `film_shots.compose()` (`BATCH-M0`).

  2. Introduce a lightweight, schema-validated **Narrative & Production Mold Contract** (`config/master_mold_v2_1.json` + `explainer_engine/schemas/episode_mold.schema.json` + `explainer_engine/scripting/mold_contract.py`) that strips duplicate BP numbers (`D-59`) and delegates all numeric lookups to `sourced_rules.json` (`BATCH-M1`).

  3. Adapt upstream research, `variant_plan.py`, `story_lint.py`, `narration_lint.py`, and the Writers' Room agent/skill pages so stories are **conceived, structured, and written** around the 12 Anchor Beats (`AB01..AB12`), the 5 Rhythm Zones (`BP-169`), and Adaptive Profiles (`A..D`) from Stage 1 (`BATCH-M2` & `BATCH-M3`).

  4. Wire audio-first zone prosody, intra-zone pace variation, Odom polish, and `D-90` pre-rendered character dialogue takes into `audio/` and `production/timing.py` (`BATCH-M4`).

  5. Implement the Bounded Timeline Engine (`±18%` clause-aligned timing + `8k+1` LTX quantization) and register the 3-tier Still Motion Ladder in `film_shots.py`, `dramatic_still.py`, and `router.py` while keeping Tier 2 (`qwen_nextpose`) strictly bounded by `BP-170`'s `static_still_max_s_by_zone` (`1.5/2.0/2.5s`) until quantitative pose-change metrics are validated (`BATCH-M5`).

  6. Wire `WP-R7`, `WP-R9`, and `WP-R10` across `production/`, `audio/sound_director.py`, `finish/upscale.py`, `qa/`, and `production/shorts.py` (`BATCH-M6`), prove the entire architecture on a **free end-to-end representative test story + 60.0s (`1,440`-frame) deterministic synthetic CPU assembly test** (`BATCH-M7`), complete **free governance closure (`BATCH-M8A`, `$0.00`)**, and only then gate paid GPU/TTS execution behind **four parent gate groups (`GATE-P1`..`GATE-P4`) comprising five independently authorized operational stages (`GATE-P1a`, `GATE-P1b`, `GATE-P2`, `GATE-P3`, `GATE-P4`) in `BATCH-M8B`**.

### 1.2 Epistemic & Authority Classification & Four-Level Evidence Grading Used in This Roadmap

Every claim in this roadmap is tagged along **two orthogonal axes**:

1. **Five Epistemic & Governance Labels**:

   * **\[FACT\]** Directly verified in the committed files of `repo_5013a55a.zip` (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`), `main` (`6e1dccad30a865df670c258c86ffa1152a0dbe7e`), git history, or primary external standards.

   * **\[OBSERVATION\]** Structural or behavioral consequence proven by tracing code execution paths or quantitative data across repository modules and Mold artifacts.

   * **\[RECOMMENDATION\]** Proposed engineering action following the `CURRENT → MASTER MOLD REQUIREMENT → KEEP → CHANGE → REPLACE → REMOVE → TRADE-OFFS → RECOMMENDATION` framework.

   * **\[HYPOTHESIS\]** Unverified threshold, speed estimate, cost savings calculation, or creative heuristic (`status: "hypothesis"`, `severity: "REVIEW"` under `D-59`) requiring empirical measurement before becoming binding.

   * **\[CREATOR DECISION\]** Rule or gate owned exclusively by the creator (`config/model_routing.json` `owner.creator`, protected configs, spend caps, voice selection `VC-08`, or open decision cards `CD-01..CD-10`).

2. **Four-Level External Research Evidence Grades (Enforced Across §15 & §16)**:

   * **`[PRIMARY-STANDARD]`**: Official broadcast/engineering standards, model card specifications, API documentation, or peer-reviewed studies with direct primary URLs (e.g., [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en), EBU Tech 3343 v4 transcribed in `docs/research/CRAFT_SOURCES_2026-10.md`, [Lightricks LTX-2 Model Card](https://huggingface.co/Lightricks/LTX-2), [ElevenLabs Pause Documentation](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses), [Pellegrino et al. 2011 *Language*](https://www.ddl.ish-lyon.cnrs.fr/fulltext/pellegrino/Pellegrino_2011_Language.pdf), [PMC6758568](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/)).

   * **`[VERIFIED-CREATOR]`**: Verifiable creator primary interviews, leaked/published production memos, or direct empirical video measurements (e.g., [MrBeast Production Manual](https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf), [Colin & Samir — *Inside MrBeast's \$100M Production Company*](https://www.youtube.com/watch?v=c8VcUnz3nVc), [PBS Studio — *Why Everything on YouTube Sounds the Same*](https://www.youtube.com/watch?v=T2G8s-6ZP9I), and the 14 benchmark video case studies `CS-01..CS-14` in §15.2).

   * **`[CRAFT-HEURISTIC]`**: Recognized film/editing/storytelling craft frameworks (e.g., Walter Murch's Rule of Six in *In the Blink of an Eye*, transcribed in `docs/research/CRAFT_SOURCES_2026-10.md`; *Dense Clarity — Clear Density*; Aristotle's *Poetics*; George Loewenstein's 1994 Information-Gap Theory; Richard Mayer's Multimedia Learning Principles). Treated as **advisory craft guidance (`REVIEW`)**, never as a hard mechanical lint `FAIL` (`D-59`).

   * **`[HYPOTHESIS]`**: Channel-specific quantitative thresholds, extrapolated retention claims, or untested GPU/cost optimizations (`status: "hypothesis"`, `severity: "REVIEW"`). Never cited as scientific law or enforced as a hard `FAIL` until empirically validated on `mrbeast_animated` pilot samples and approved by the creator (`CD-01..CD-10`).

### 1.3 Audit Baseline, File Provenance & Context Continuity Register

To prevent context loss or hash/line-count drift across sessions and commits, the two tables below record (A) the exact repository and branch state as of `2026-11-03`, including every non-code audit/handoff file present on the planning branch, and (B) the forensically verified byte/line/SHA-256/Git-blob provenance of every Master Mold and handoff artifact inspected in this session:

#### Table 1.3A — Repository & Branch Continuity Register

| Register Field | Verified Value & Evidence Classification |
| ----- | ----- |
| **1. Audit Timestamp** | `2026-11-03T00:35:00+04:00` (`2026-11-02T20:35:00Z`) |
| **2. Target Branch** | [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02) |
| **3. Target Branch Commit & Blob Chain Preceding This Final Reconciliation** | Rooted on [PR #119](https://github.com/vano1919/explainer-engine/pull/119) HEAD `5013a55aca5a17a3734150f61a5eb172abcbe3b8` -> `85166baa27b5466dc046138606f0bc35f2f9ee21` -> `d103c2d31a15789e0d9619d5d1811ade5baf9dca` -> `c35978d9ea6573117dbbfd88db10a013495f7b44` (`cc2cb4b1476ce23ca46dbf77154a1b68ca5d8db4`, `1,790` lines) -> `82b8da9ff1fbb9d0bc94bdc30019414fad41f9ce` (`5fa05ebfa67282f11de8a56162b2d1714743c13e`, `2,226` lines) -> intermediate revision `7312f660040214867554712b482b320cfb850f50` (SHA-256 `65672b4c904305d57424617e2854e883d5406b31e07d612b91930e624274615a`, `2,635` lines) -> **Final Forensically Verified & Source-Backed Revision in This File** |
| **4. Complete Inventory of Non-Code Files on Branch / Bundle vs `5013a55a`** | **Zero (`0`) application code (`explainer_engine/**`), schema (`explainer_engine/schemas/**`), agent/skill (`.claude/**`), test (`tests/**`), or protected config (`config/**`) files modified** vs `5013a55aca5a17a3734150f61a5eb172abcbe3b8`. Non-code planning & audit artifacts on the branch/bundle include: `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`, `docs/PROGRESS.md`, and the audit bundle materials (`ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02.zip`, `README_FOR_CHATGPT_AUDITOR.md`, `CHATGPT_MASTER_AUDIT_PROMPT_GEORGIAN.txt`, `ARGON_READ_ONLY_AUDIT_AND_CONSOLIDATION_PLAN_2026-11-02.md`, `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md`, `MRBEAST_12MIN_MASTER_MOLD.md`, `mrbeast_12min_video_mold.json`, `mold_254_shots_verified_digest.json`, `pr119_diff.patch`, `pr119_log.txt`, `pr112_show.patch`, `main_recent_log.patch`). |
| **5. Integration Code Baseline SHA ([PR #119](https://github.com/vano1919/explainer-engine/pull/119) HEAD)** | `5013a55aca5a17a3734150f61a5eb172abcbe3b8` (**VERIFIED** in `repo_5013a55a.zip`: `1,287` tracked files, `51` commits ahead and `0` behind `main`) |
| **6. Current `main` Baseline SHA** | `6e1dccad30a865df670c258c86ffa1152a0dbe7e` (**VERIFIED** in `main_recent_log.patch`) |
| **7. Relevant Open PR States & Head SHAs** | [PR #119](https://github.com/vano1919/explainer-engine/pull/119): Open Draft (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`, `77` changed files, `+5,576 / -336`); [PR #112](https://github.com/vano1919/explainer-engine/pull/112): Open Draft (`1273619bb52930dde659b6f07a0999141d8ec76b`, `1` ahead, `29` behind `main`, `5` files changed) |
| **8. Repository Areas Directly Inspected** | All `158` BP rules in `explainer_engine/standards/sourced_rules.json` and `docs/SOURCED_RULES.md`; `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-01..D-94`); `docs/MARKET_RESEARCH.md` (`V-22`, `V-51`); `config/spend_caps.json`, `config/model_routing.json`, `config/cloud_pins.json`, `config/channel_voices.json`; all `16` `.claude/agents/*.md` and `16` `.claude/skills/*/SKILL.md`; all `33` JSON schemas in `explainer_engine/schemas/`; core pipeline modules across `scripting/`, `production/`, `edit/`, `audio/`, `finish/`, `qa/`, `compose/`, `training/`, `cloud/`, `governance/`, `standards/`, and `tests/unit/`; real measured TTS outputs in `examples/day1_v2/`, `examples/titans_from_zero/`, and `examples/syndicate_wars_ep1/`; plus `mrbeast_12min_master_mold.md`, `mrbeast_12min_video_mold (1).json`, and the 214-page research compendium |
| **9. Verified Project Invariants Preserved** | `D-43` single-file `production_script.json`; `D-56` spend caps in code (`core/spend_caps.py`, `core/ledger.py` 80% stop); `D-59` single home for numbers (`sourced_rules.json`); `D-62`/`D-63` living-person voice ban (`PV-55` in `production/silent.py`); `D-67`/`OR-19` 2-part sample gate (`production/sample.py`); `D-73` HF Vault (`vano1919/tmr-artifacts`, zero binary `.wav`/`.mp3`/`.mp4` in Git); `D-79` one main agent + read-only Opus critics; `D-84` protected configs & hooks; `D-85`/`BP-167` `24 fps` `2560x1440` 12-min master + `5` Shorts (`1440x2560`); `D-89` no permanent hosts; `D-90` character ElevenLabs take -> LTX audio-in (`audio/spine.py` + `edit/router.py`); `D-92` creator answers (`24 fps`, `170` WPM `BP-01`, `1440x2560` Shorts, pilot gates `<=3` seeds/shot & `<=3` review min/finished min); `D-93` `60/30/10 ±5%` lane mix (`BP-109`); `D-94` 5-zone `BP-169` house rhythm + `Odom` narrator (`eleven_v4`) + `REVIEW`-only retention rules |
| **10. Open Creator Decisions (`CD-01..CD-10`)** | All `10` decision cards remain explicitly open for the creator's word (§13.2): `CD-01` (Kickoff), `CD-02` (LoRA `0.7` vs `1.0`), `CD-03` (`BP-170` thresholds & keeping Tier 2 at `1.5/2.0/2.5s`), `CD-04` (`BP-169` intra-zone pace `REVIEW` hypothesis), `CD-05` (`$31.00` GPU cap + full-episode TTS credit cap + reallocating `$1.77` `p12e_hosts`), `CD-06` (deceased historical figure voicing under `D-90` / `V-51`), `CD-07` (closing PR #112), `CD-08` (56 stopped `0 GB` pods), `CD-09` (Episode 1 topic), `CD-10` (YouTube Studio rebrand/unlisting) |
| **11. Unverified Live Remote Items & Why** | **UNVERIFIED — PERMISSION / SANDBOX NETWORK LIMITED**: Live GitHub branch-protection/ruleset API (`main.protected = false` reported by prior external inspection; elevated to mandatory pre-implementation gate `GATE-EXT-MAIN-PROTECT`), live GitHub Actions status, and remote HF `vano1919/tmr-artifacts` file listing (local `PYTHONPATH=. python3 -m explainer_engine.docs_lint` is **VERIFIED** with `0 finding(s)`) |
| **12. Last Completed Implementation Stage & Current State** | **IMPLEMENTATION NOT PRESENT (`0%` of `BATCH-M0..M8B` executed)**: [PR #119](https://github.com/vano1919/explainer-engine/pull/119) (`5013a55a`) completed `WP-R1..R6-part, R8, R11-part, R12`; zero application code or config changes have been executed on this planning branch |

#### Table 1.3B — Forensic File Provenance & Hash Reconciliation Table (`§6` Verification)

**[FACT]** Direct byte-level inspection of `argon_latest_repo_bundle.zip` and `repo_5013a55a.zip` resolves every provenance question and includes a compact `<45 KB` `mold_254_shots_verified_digest.json` in `ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02.zip` so external auditors whose GitHub connectors truncate the `1.1 MB` JSON can independently verify all `254` shots and `16` segments:

| Artifact Name / Reference | Availability in Local Sandbox | Exact Byte Size | Exact Line Count (`splitlines()` / with trailing LF) | Internal Version String vs External Label | Verified SHA-256 Digest | Verified Git Blob SHA-1 | Forensic Provenance Verdict |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `mrbeast_12min_master_mold.md` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `117,220` bytes | `431` lines (`431` with trailing LF) | Header L3: `schema_version: 2.0.0` (external handoff label: `v2.1.0`) | `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e` | `c928c92e65a2357d3dc511b732edb4b1232301d9` | **Authoritative Markdown Mold source** inspected in this roadmap. |
| `mrbeast_12min_video_mold (1).json` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `1,109,253` bytes | `26,291` lines (`26,292` editor lines with trailing LF) | `mold_meta.schema_version: "2.0.0"` (external handoff label: `v2.1.0`) | `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0` | `80fc3b99294fd880fdbb7674bdfc2f7197822d2f` | **Authoritative JSON Mold source** (`16` segments `S01..S16`, `254` shots `SH001..SH254`, `17,280` frames = `720.0s`, `2,066` words). Full per-segment and per-zone tables are embedded in §15.5 and exported to `mold_254_shots_verified_digest.json`. |
| `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `1,178,496` bytes | `22,446` lines | Embeds retired `v1.0` Mold JSON at `L1553–21882` (`20,330` lines) | `d9bda2288887514749f462cca7e4048b76631ec032f1eeab1705f8ef665c32c5` | `e0918d88b693eb096ed689364b07da46a3f44e10` | **Historical v1.0 Comparison Source** (`1,797`-word lock, `254` shots hardcoded to 1637 Tulip Mania). |
| `CrossWorld_Chronicles_Organized_Research_for_Gemini.docx` | **PRESENT & VERIFIED** | `164,897` bytes | `874` paragraphs, `42` tables, `166` headings | 214-page research compendium (Parts I–IV, Appendices A–B) | `a7d018996215c27cf1f9fa86b8685ee544b1581ce135567903923eb08f679fc3` | `7b643b15c879f7b777ff06f3e0fb5d72268c5eb0` | **Audited Research Compendium**. Every claim extracted from this `.docx` is re-verified and graded in §15.7 (`SRC-01..SRC-48`). |
| External hashes `316d8042...`, `89aa56d2...`, `173EFDA0...` | **INACCESSIBLE IN LOCAL CONTAINER** | External pre-bundle notes or host Windows copy | External pre-bundle / host files | External pre-bundle notes | `316d8042...`, `89aa56d2...`, `173efda0...` | Not in bundle | **RETIRED FROM ACTIVE CLAIMS**. Superseded by verified `49cf3084...` and `2ca7f56f...`. |

## 2. Current Architecture and Actual Implementation State

### 2.1 End-to-End Information Flow Reconstruction (Actual Source Code at `5013a55a`)

```
[Stage 0: Governance & Job Init]
  explainer_engine/governance/hooks.py, status.py, records.py
  explainer_engine/core/ledger.py (Run), spend_caps.py, store.py (EpisodeJob), delivery.py (BP-167: 12m, 2560x1440@24fps, 5 Shorts)
         │
         ▼
[Stage 1: Topic, Research Dossier, Claim Map, Episode Rulebook & Story Hypotheses]
  .claude/agents/episode-standards-director.md + .claude/skills/science-grounding/SKILL.md + crossover-episode/SKILL.md
  explainer_engine/standards/rulebook.py -> episode_rules.json (gate --at provisional / final)
  explainer_engine/research/fan_brief.py (fan_brief/1), hypotheses.py (story_hypotheses/1), reference_study.py
  explainer_engine/scripting/claims.py -> claim_map.md / JSON
         │
         ▼
[Stage 1b: Priced Structure Variants & Creator Variant Pick (OR-31, D-86)]
  explainer_engine/scripting/variant_plan.py (brief -> Opus 2-3 variants A-D -> score dynamics & cost -> critic score -> creator card)
  Output: script_variants.json (script_variants/2) -> EpisodeJob.move(..., "VARIANT_CHOSEN")
         │
         ▼
[Stage 2: Short Scenario & Creator Approval Gate (OR-15, PV-45)]
  explainer_engine/scripting/scenario.py -> episode.scenario {file, approved_by, approved_at, sha256}
         │
         ▼
[Stage 3: 7-Stage Writers' Room on ONE production_script.json (OR-20, D-48, D-79)]
  Enforced after every stage by: explainer_engine/scripting/stage_guard.py (start / fresh / violations)
  ├─ 3.1 Story Architect (.claude/agents/story-architect.md) -> writes drama, cast, periods, segments[id,beat,purpose,drama,scene,rhythm_zone]
  │      Checked by: scripting/story_lint.py (ST-00..ST-24)
  ├─ 3.2 Scene Writer (.claude/agents/scene-writer.md) -> writes segments[].lines[text,speaker,claims,to,intent]
  │      Checked by: scripting/scene_lint.py (SC-01..SC-12), register_lint.py (RG-01..RG-04), narration_lint.py (N-01..N-17)
  ├─ 3.2b Beat Writer (.claude/agents/beat-writer.md) -> writes lines[].visual_beats (VB-01..VB-12)
  │      Checked by: production/beats.py (lint)
  ├─ 3.3 Performance Director (.claude/agents/performance-director.md) -> writes lines[tags,emphasis,tone,emotion,pause_after]
  │      Checked by: scripting/narration_lint.py, audio/hype_read.py (HR-01..HR-04, NOT YET WIRED into validate.py)
  ├─ 3.4 Edit Planner (.claude/agents/edit-planner.md) -> writes segments[shots,audio,staging], music, graphics + film_shots.json
  │      Checked by: scripting/film_shots.py, shot_prompt_lint.py (KP-01..KP-47), scripting/rhythm_lint.py (RL-01..RL-04, NOT YET WIRED into validate.py)
  ├─ 3.5 Voice Caster (.claude/agents/voice-caster.md) -> writes voice, cast.<id>.voice
  │      Checked by: audio/casting.py, audio/voice_audition.py (BP-138), audio/voice_check.py
  ├─ 3.6 Shorts Writer (.claude/agents/shorts-writer.md) -> writes shorts[] (up to 10 in /3 doc, 5 in BP-167)
  │      Checked by: production/validate.py (PV-28, PV-34)
  └─ 3.7 Script Critic (.claude/agents/script-critic.md, spawned read-only Opus) -> writes editorial_review.json (/2) + story_page.md
         Checked by: production/editorial_gate.py (EG-01..EG-23), qa/engagement.py (ENG-1..ENG-8), scripting/script_approval.py (PV-46)
         │
         ▼
[Stage 4: Audio Generation, Word Alignment, Pause Padding, Polish & Audio Spine (P4)]
  explainer_engine/audio/narrate.py (ElevenLabs connector under PreToolUse hook & ledger)
  explainer_engine/production/__main__.py:cmd_words -> scribe_words.py / local_words.py -> pause_pad.py -> narrator_polish.py -> voice_check.py
  explainer_engine/production/timing.py -> timed.json
  explainer_engine/audio/spine.py -> audio/audio_spine.json (audio_spine/2, with post_hoc_shots windows for DIALOGUE_CU / KEYFRAME_LTX)
  explainer_engine/audio/sound_director.py (step 4b of edit-planner) -> audio/sound_mix_manifest.json (sound_mix_manifest/2)
         │
         ▼
[Stage 5: Continuity Cards, Shot Routing & Visual Asset Generation (P5, P6, P12)]
  ├─ Scene Continuity (.claude/agents/shot-continuity-writer.md): scripting/continuity.py -> continuity_card/1 & /2 -> prompts.json
  ├─ Deterministic Shot Router (P6): edit/router.py (film_shots/2 -> shots/<id>.still.spec.json, <id>.video.spec.json, shots/route.json)
  ├─ Helper & Compensator Lane (10% runtime, BP-109): edit/visual_compensator.py (Archetypes 1-12: maps/render.py, edit/hud.py, edit/tableau.py)
  ├─ Still Lane (30% runtime, BP-109): edit/dramatic_still.py (BP-170), production/parallax.py, production/accents.py, production/faces.py
  └─ Video Lane (60% runtime, BP-109): cloud/runpod.py + training/pods/p12/p12b.py & p12c_ltx.py (Qwen-Image-2.1 + xworld_v2 -> LTX-2.5 22B)
     Checked by: qa/keyframe_gate.py (KG-01..23), qa/blind_check.py, training/video_qa.py (LT-50..62, LT-80, CLIP-01..12)
         │
         ▼
[Stage 6: Video/Audio Assembly, 2K Upscale, QA & Retry Loop (P7, P8, P10)]
  explainer_engine/finish/upscale.py (1920x1088 LTX -> crop 1920x1080 -> Lanczos 2560x1440 @ 24 fps)
  explainer_engine/production/assemble.py (build_audio_v2 stereo stems + build_video_v2 with BP-128 handles, BP-129 whips, BP-130 LAB grade + export_otio)
  explainer_engine/qa/retry_router.py (attempt 1 RESEED -> attempt 2 REWEIGHT -> attempt 3 FALLBACK_KEYFRAME_LTX / FALLBACK_STILL_HOLD -> ESCALATE)
  explainer_engine/qa/scorecard.py, qa/targets.py, qa/frame_review.py, qa/review_bundle.py (BP-168 Go/Pivot/Abandon)
         │
         ▼
[Stage 7: Shorts Extraction & Distribution Staging (P9)]
  explainer_engine/production/shorts.py (1440x2560 @ 24 fps, burned ASS captions + caption-free _master.mp4)
  explainer_engine/production/clip_shorts.py (1440x2560 @ 24 fps loop-cut Shorts from finished long video)
  explainer_engine/publish/plan.py, stage.py, thumbnail.py, youtube.py (unlisted staging only after REVIEW_APPROVED; never public)





```

### 2.2 Subsystem Implementation State Classification at `5013a55aca5a17a3734150f61a5eb172abcbe3b8`

| Subsystem / Module Group | Status Classification | Verified Evidence in Repository (`5013a55a`) | Integration Gap Relative to Master Mold v2.1.0 | 
| ----- | ----- | ----- | ----- | 
| **Canonical Rules Registry (`standards/sourced_rules.json`, `sourced_rules.py`)** | **Implemented and tested** | `158` BP rules (`BP-01..BP-172`); `BP-167` (`12m`, `2560x1440@24fps`, `5` Shorts), `BP-109` (`60/30/10 ±5%`), `BP-141` (`A/D non_character_max: 0.45`), `BP-169..172` added in PR #119; pinned by `tests/unit/test_sourced_rules.py`. | `BP-169` lacks intra-zone pace-variation frequency parameters and re-hook spike allowances (`S06` at `180s`, `S09` at `360s`); `BP-170` enforces `static_still_max_s_by_zone` (`1.5/2.0/2.5s`) as a hard `FAIL` ceiling unless a Tier 3 `cutout_relocation` or `plate_swap` is present; Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`) must remain strictly within `static_still_max_s_by_zone` (`1.5/2.0/2.5s`). | 
| **Rhythm Profile Reader (`edit/rhythm_profile.py`, `schemas/rhythm_profile.schema.json`)** | **Implemented but incompletely integrated** | Reads `BP-169` (`mrbeast_animated` vs `calm_docudrama`); provides `zone_at_time`, `zone_for_window`, `zone_wpm`, `words_to_seconds`; pinned by `tests/unit/test_rhythm_profile.py`. | Only called by `rhythm_lint.py`, `dramatic_still.py`, `hype_read.py`, and `syllables.py`. **Not called** by `variant_plan.py`, `story_lint.py`, `narration_lint.py`, `film_shots.py`, `board.py`, `motion_lint.py`, `timing.py`, `validate.py`, `sound_director.py`, `engagement.py`, or `scorecard.py`. | 
| **Dramatic Still Validator & Renderer (`edit/dramatic_still.py`, `schemas/dramatic_still.schema.json`)** | **Implemented but incompletely integrated** | Validates `cutout_relocation` (`>=0.25` dist, `>=0.08` area), `plate_swap` (`>=0.30` px), and `composite_cutout_and_plate` within `[0.25, 0.75]` hold window (`BP-170`); renders RGBA cutout relocation; pinned by `tests/unit/test_dramatic_still.py`. | Not wired into `edit/router.py`, `production/assemble.py` (`build_video_v2`), or `variant_plan.py`. Enforces `static_still_max_s_by_zone` (`1.5s` in Hook/Climax, `2.0s` in Early/Late, `2.5s` in Calm Middle) on all stills lacking a Tier 3 `dramatic_change` (`cutout_relocation` or `plate_swap`); Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`) are capped at `1.5/2.0/2.5s` under `BP-170` (`FAIL`). | 
| **Multi-Zone Rhythm Lint (`scripting/rhythm_lint.py`)** | **Implemented but incompletely integrated** | Checks `RL-01` (shots/min band per zone), `RL-02` (>15% shots above zone max length), `RL-03` (>30% shots below zone min length), `RL-04` (`dramatic_still.check_script_stills`); pinned by `tests/unit/test_rhythm_lint.py`. | Standalone CLI only; **not called** by `production/validate.py`, `scripting/film_shots.py:episode_check`, or `production_gate.py`. | 
| **Hyped Narrator Prosody & Odom Polish (`audio/hype_read.py`, `audio/narrator_polish.py`, `config/channel_voices.json`)** | **Implemented but incompletely integrated** | Odom (`CcSJ2r3qw0XU9gJpEPyk`, `eleven_v4`) set as `status: "channel"` in `config/channel_voices.json`; `narrator_polish.py` (`+12 dB @ 150 Hz` shelf, `-2 dB @ 300 Hz`, `-0.6 dB` trim, `0.95` limiter) wired into `production/__main__.py:cmd_words` (when `not S.has_dialogue(doc)`); `hype_read.py` checks `HR-01..04`; pinned by `test_hype_read.py` and `test_narrator_polish.py`. | `narrator_polish.py` is **skipped** when `S.has_dialogue(doc)` is `True` (`production/__main__.py:119`), even though all docudrama episodes have character dialogue! Also `hype_read.check_prosody_plan` is not wired into `production/validate.py` or `narration_lint.py`, and Odom's `baseline` in `channel_voices.json` is still `null`. | 
| **Production Script Schema `/4` (`schemas/production_script.schema.json`) & Stage Guard (`scripting/stage_guard.py`)** | **Implemented with P0 regression in downstream validators** | `production_script/4` added to schema enum; `episode.rhythm_profile`, `segments[].rhythm_zone`, and `shots[].dramatic_change` added; `rhythm_zone` added to `stage_guard.py:SEG_STORY`; pinned by `test_production_script_schema.py`. | **P0 Bug**: 10 validator modules (`scene_lint.py`, `script_approval.py`, `speech.py`, `story_lint.py`, `beats.py`, `editorial_gate.py`, `silent.py`, `staging.py`, `validate.py`, `audio/layers.py`) check `== "production_script/3"`, silently breaking `/3` rules when `schema == "production_script/4"`. | 
| **Writers' Room Agents (`.claude/agents/*.md`) & Skills (`.claude/skills/*/SKILL.md`)** | **Implemented for `/3` calm era; unadapted for Mold v2.1.0** | All 16 agents and 16 skills exist and enforce `/3` `stage_guard` and `OR-32` re-read protocol. | Still instruct `/3` schema, `15-minute` runtime (`story-architect.md`), `170 WPM` flat pace (`scene-writer.md`, `shorts-writer.md`), `Grandpa Spuds Oxley` (`elevenlabs-voice/SKILL.md`), and `BP-40` `10 pictures/min` (`beat-writer.md`, `edit-planner.md`). Zero awareness of Master Mold v2.1.0 (`AB01..AB12`, 5 zones, Still Motion Ladder, Bounded Timeline Engine). | 
| **Variant Planner (`scripting/variant_plan.py`) & Film Shots (`scripting/film_shots.py`)** | **Implemented but partially wired to Mold v2.1.0** | `variant_plan.py` and `film_shots.py` read `BP-109` (`60/30/10 ±5%`), `BP-141` (`A/D 0.45`), and `BP-167` (`12m`). | Both still check flat `BP-107` (`11–17 shots/min`, `2.5–4.5s` median shot) instead of `BP-169` zone bands (`WP-R7`), and `variant_plan.py:segments_from_script` still estimates durations at flat `BP-01` (`170 WPM`) without passing `zone=seg.get("rhythm_zone")`. | 
| **Shot Router (`edit/router.py`), Visual Compensator (`edit/visual_compensator.py`), Maps (`maps/`)** | **Implemented and tested** | `router.py` routes `KEYFRAME_LTX`, `DIALOGUE_CU`, `ATMOS_BROLL`, `STILL_HOLD`, `MAP`, `COMPENSATOR` and refuses `HOST_COMMENTARY` & `DRAMA_BLOCKED_3D` (`D-89`, `D-75`). `visual_compensator.py` implements all 12 archetypes. | `router.py` only emits static keyframe specs for `STILL_HOLD` — it does not yet route Mold v2.1.0's 3-tier Still Motion Ladder (`TIER_1` `parallax_25d`, `TIER_2` `qwen_nextpose`, `TIER_3` `dramatic_still`) or output a still-motion spec for `build_video_v2`. | 
| **Video Assembly (`production/assemble.py`) & 2K Upscale (`finish/upscale.py`)** | **Implemented but incompletely integrated** | `assemble.py` implements `build_audio_v2` (stereo stems, `BP-116..123`) and `build_video_v2` (`BP-128` handles, `BP-129` whips, `BP-130` Reinhard LAB grade, `export_otio`); `finish/upscale.py` crops `1920x1088` -> `1920x1080` and Lanczos-scales to `2560x1440 @ 24 fps`. | `build_video_v2` is not yet wired to call `finish/upscale.py` automatically on `1920x1088` LTX clips or to render `dramatic_still.py` (`BP-170`) / `parallax_25d` on `STILL_HOLD` shots in the v2 animated timeline. | 
| **Bounded Timeline Engine (`±18%` Speech-Clause + `1/f` + `8k+1` Quantization)** | **Planned in Mold v2.1.0; not implemented in repo code** | Specified and mathematically verified in `MRBEAST_12MIN_MASTER_MOLD.md` §4.4 and `mrbeast_12min_video_mold.json` `bounded_timeline_engine_and_jitter_protocol`. | Not yet implemented as a Python module in `explainer_engine/edit/` or wired into `film_shots.py` / `timing.py`. | 
| **P12 Combined Pod (`training/pods/p12/p12b.py`, `p12c_ltx.py`, `p12b.json`, `edit/clay_video.py`)** | **Implemented and dry-run tested; unverified on real GPU** | Stubbed end-to-end tests (`test_p12b_pod_script.py`, `test_p12c_ltx.py`, `test_clay_video.py`) pass on CPU; `p12b.json` has fast-action prompts (`KP-47`) and Raymond Verne AV takes pinned. | **Unverified on real GPU** until the creator approves the `OR-23` P12b pod run (`$0.50` measurement / `$2.40` full pod). `xworld_v2` LoRA strength is `0.7` in `cloud_pins.json:103` vs `1.0` in `p12b.json` and `qa/style_prompt.py:25`. | 

## 3. Master Mold v2.1.0 Requirement Map & MD-vs-JSON-vs-Repo Audit

### 3.1 Three-Layer Architecture of Master Mold v2.1.0

Master Mold v2.1.0 replaces the rigid v1 254-shot template with a **3-Layer Controlled-Adaptive Architecture**:

| Layer | JSON Key in `mrbeast_12min_video_mold.json` | Markdown Section in `MRBEAST_12MIN_MASTER_MOLD.md` | Role in Production Pipeline | Classification | 
| ----- | ----- | ----- | ----- | ----- | 
| **Layer 1: Narrative Constitution** | `layer_1_narrative_constitution` | Section 3 (`§3.1–§3.4`) | Governs **Topic/Research → Story Hypotheses → Variants → Scenario → Story Architect → Scene Writer → Script Critic**: Two-Phase Hook Contract (`0:00–0:12` Cold Promise + `BP-111` teasers; `0:12–0:36` Counterfactual Hinge + Central Dramatic Question by `0:32`), Curiosity Loop & Re-Engagement Laws (`180s` and `360s` spikes), Immersion & Anti-Anachronism Laws (`BP-87`, `BP-88`), Narrator vs. Diegetic Character Dialogue separation (`D-90`, `D-62`, `D-63`), Genre-Adapted Rhetorical Drivers (banning game-show clichés), and the **12 Anchor Beats (`AB01..AB12`)**. | `hard_invariant` + `adaptive_target` | 
| **Layer 2: Production Profile** | `layer_2_production_profile` | Section 4 (`§4.1–§4.4`) | Governs **Variant Planner → Beat Writer → Performance Director → Edit Planner → Voice Caster → Audio Spine → Shot Router → Visual Generators → Assembly → QA**: 12-parameter registry (`PRM_TOTAL_DURATION_S`..`PRM_LUFS_AND_TRUE_PEAK`) linked via `canonical_bp_ref` to `sourced_rules.json` (`D-59`), 4 Episode Profiles (`D`, `B`, `A`, `C`), 3-Tier Still Motion Ladder (`TIER_1` `parallax_25d`, `TIER_2` `qwen_nextpose`, `TIER_3` `dramatic_still`), Semantic Palette Token Binding (`D-22`, `BP-166`), Audio Architecture (`Odom` + `narrator_polish.py` + `hype_read.py` + `D-90` character audio-in), and the **6-Step Bounded Timeline Engine (`±18%` + `8k+1` LTX quantization)**. | `hard_invariant` + `adaptive_target` + `diagnostic_metric` | 
| **Layer 3: Episode Timeline Schema & Reference Grid** | `layer_3_episode_timeline_schema_and_reference_grid` | Section 5 (`§5.1–§5.2`) | Provides the **Typed Semantic Slots Registry** (`{COUNTERFACTUAL_STAKES_BADGE}` etc.), the **5 Rhythm Zones (`zones_5`)**, the **16-Segment Structural Matrix (`segments_summary_16`, `S01..S16`, `720.0s`, `17,280` frames, `2,066` words)**, and one worked **254-Shot Reference Instantiation (`reference_timeline_254_shots`)** (`152` VIDEO = `432.0s` / `60%`, `76` STILL = `216.0s` / `30%`, `26` HELPER = `72.0s` / `10%`). Explicitly marked `classification: "reference_only"` so the 254-shot count is **never** enforced as a mandatory shot count. | `reference_only` (non-binding instantiation) | 

### 3.1B Version Genealogy: Master Mold `v1.0` → `v2.0.0` (Internal Header / Branch Label) → `v2.1.0` (Canonical Reconciled Contract)

| Version Label | Artifact / Commit Location | Structural Scope & Defining Characteristics | Status & Role in Unified Plan | 
| ----- | ----- | ----- | ----- | 
| **Master Mold `v1.0`** | Embedded in `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md` (`L1553–21882`, `20,330` lines; initial single-episode Tulip Mania draft) | Hardcoded 1637 Tulip Mania text across all global rules; fixed `1,797`-word lock; `VIDEO`/`STILL`/`HELPER` all carried LTX `8k+1` frame counts without handle frames; global absolute Kelvin/HEX overrides (`5800K -> 2900K`); single-axis `68/20/12` audio split. | **Retired / Superseded** (`10` defect clusters `DM-01..DM-10` replaced in `mrbeast_12min_master_mold.md` and `mrbeast_12min_video_mold (1).json`). | 
| **Master Mold `v2.0.0` (Internal File Header & PR #119 Label)** | `mrbeast_12min_master_mold.md` (`431` lines, `schema_version: 2.0.0`, SHA-256 `49cf3084...`), `mrbeast_12min_video_mold (1).json` (`26,291` lines, `mold_meta.schema_version: "2.0.0"`, SHA-256 `2ca7f56f...`), and [PR #119](https://github.com/vano1919/explainer-engine/pull/119) (`WP-R6..WP-R10`, commits `e2fb409`..`5013a55a`) | Separates **Layer 1 (`layer_1_narrative_constitution`)**, **Layer 2 (`layer_2_production_profile`)**, and **Layer 3 (`layer_3_episode_timeline_schema_and_reference_grid`: `S01..S16`, `254` shots, `17,280` frames = `720.0s`, `2,066` words)**; extracts `BP-169..BP-172` into `explainer_engine/standards/sourced_rules.json`. | **Verified Bundle Artifact & Partially Integrated Code Baseline** (`BP-169..BP-172` live in repo, but downstream callers in `rhythm.py`, `board.py`, `assemble.py`, and `/4` schema dispatch across 11 consumer modules remain unwired). | 
| **Master Mold `v2.1.0` (Reconciled Repository Contract Target)** | Target committed contract `explainer_engine/standards/mrbeast_12min_video_mold.json` (`BATCH-M1`) + `docs/MRBEAST_12MIN_MASTER_MOLD.md` | Applies the **12 forensic reconciliations (`M-01..M-12`)** below to the verified `2ca7f56f...` / `49cf3084...` artifacts so that `schema_version` is bumped to `"2.1.0"`, all dangling/mis-cited `BP-*` IDs are repaired, duplicate threshold numbers are stripped in favor of `sourced_rules.json` (`D-59`), and Layer 1/2 rules are cleanly separated from the Layer 3 1637 Tulip Mania reference instance. | **Authoritative Target Specification** to be committed in `BATCH-M1`. | 

### 3.2 Forensic Audit of Discrepancies Between `mrbeast_12min_master_mold.md` (`49cf3084...`), `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`), and `sourced_rules.json` (`5013a55a`)

**\[FACT\]** Direct programmatic verification of `mrbeast_12min_master_mold.md` (`431` lines, SHA-256 `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e`), `mrbeast_12min_video_mold (1).json` (`26,291` lines, SHA-256 `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0`), and `explainer_engine/standards/sourced_rules.json` (`5013a55a`) identifies **12 exact internal discrepancies (`M-01` through `M-12`)** that must be resolved in `BATCH-M1` / `BATCH-M5` / `BATCH-M6`:

| ID | Discrepancy Location | What `mrbeast_12min_master_mold.md` (`49cf3084...`) Says | What `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) Says | What Repository `sourced_rules.json` (`5013a55a`) Says | Required Resolution in `BATCH-M1` / `BATCH-M5` / `BATCH-M6` | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **M-01** | **Zone ID Identifiers** (`zones_5[].zone_id` vs `BP-169` & `production_script/4`) | Uses `Z1_HOOK_0_30S`, `Z2_FAST_SETUP_30_90S`, `Z3_CALM_MIDDLE_90_480S`, `Z4_LATE_THIRD_480_660S`, `Z5_CLIMAX_660_720S` (while referencing `BP-169`). | `zones_5[].zone_id` (`L477–618`) and `segments_summary_16[].zone_id` (`L974–1294`) use `Z1_HOOK_0_30S` .. `Z5_CLIMAX_660_720S`. | `BP-169` (`sourced_rules.json:2792–2889`) and `schemas/production_script.schema.json:505–515` (`segments[].rhythm_zone` enum) use `hook_0_30s`, `early_30_90s`, `middle_calm_90_480s`, `late_third_480_660s`, `climax_660_720s`. | Standardize on `BP-169`'s lowercase canonical IDs (`hook_0_30s`, `early_30_90s`, `middle_calm_90_480s`, `late_third_480_660s`, `climax_660_720s`) in both Mold files and all internal code; provide a **one-way input normalization** helper (`normalize_zone_id`) at the ingestion boundary for legacy uppercase `Z1..Z5` strings and raise a hard validation error on any unknown zone ID. | 
| **M-02** | **Duplicate & Divergent Zone Numbers and TTS Tags in `zones_5`** (`D-59` single-home rule) | States in §1.1 that all numeric thresholds live in `sourced_rules.json` (`D-59`), yet tables in §4/§5 retain the 2,066-word instance averages (`192.0`, `177.0`, `166.6`, `184.3`, `157.0` WPM). | `zones_5` (`L477–618`) embeds numeric targets that differ from `BP-169`: `heard_wpm_target` (`192.0` vs `193`, `177.0` vs `176`, `166.6` vs `166`, `184.3` vs `185`, `157.0` vs `160`), `speaking_wpm_target` (`217` vs `233` in Z1), `dramatic_changes_per_min` (`34.0` vs `30.0` in Z1), and extra `tts_tags_allowed` (`[gasps]` in Z1, `[playful]` in Z2, `[excited]` at 180s/360s in Z3, `[shouts]` in Z4, `[pause]`/`[amazed]` in Z5). | `BP-169` has `heard_wpm_target`: `193, 176, 166, 185, 160`; `speaking_wpm_target`: `233, 225, 205, 230, 225`; and `tts_tags` without `gasps` in Z1 or `excited` in Z3 (`audio/hype_read.py:HR-01` flags any tag not in `BP-169`). | Per `D-59` (`tests/unit/test_sourced_rules.py`), remove duplicate threshold numbers from the committed repo Mold contract (`zones_5` references `BP-169` via `rhythm_profile.py`), isolate the 2,066-word empirical numbers strictly under `reference_instance_metrics` (never used as validator bounds), and add a segment-scoped `rehook_tts_tags: ["excited"]` exception in `BP-169` + `audio/hype_read.py` strictly limited to segments with `rehook_spike: true` (`S06` at `180s`, `S09` at `360s`), keeping `[excited]` forbidden across all other `middle_calm_90_480s` segments. | 
| **M-03** | **Episode Profiles `A..D` `bp141_non_character_max`, `lane_allowed_ranges_pct`, and `rationale` in JSON** | §1.1 and §4.2 state `BP-109` tolerance is `±5 percentage points` (`0.05`) and `BP-141` `non_character_max` is `0.45` for Profiles `A` and `D` and `0.80` for `B` and `C`. | In `mrbeast_12min_video_mold (1).json` `episode_profiles.profiles` (`L622–742`), all 4 profiles (`D`, `B`, `A`, `C`) have `"bp141_non_character_max": 0.8`, retain `"lane_allowed_ranges_pct"` (`±3%`, e.g. `[57.0, 63.0]`) alongside `"allowed_ranges"` (`[0.55, 0.65]`), and all 4 profiles have Profile D's `rationale` text pasted into them. | `BP-141` (`sourced_rules.json:2231–2271`) has `A.non_character_max = 0.45`, `D.non_character_max = 0.45`, `B.non_character_max = 0.80`, `C.non_character_max = 0.80` (`status: "hypothesis"`, `severity: "REVIEW"`). `BP-109` (`L1651–1673`) has `lane_tolerance = 0.05` (`55–65%` VIDEO, `25–35%` STILL, `5–15%` HELPER). | Fix `mrbeast_12min_video_mold.json` so Profiles `A` and `D` resolve `non_character_max = 0.45` and `B` and `C` resolve `0.80` from `BP-141`, remove the stale `±3%` `lane_allowed_ranges_pct` keys, restore distinct `rationale` strings per profile, and **preserve `BP-141`'s `status: "hypothesis"` and `severity: "REVIEW"`** (never escalating to `FAIL` without an explicit creator decision). | 
| **M-04** | **Still Motion Ladder (3-Tier) vs `BP-170` (`edit/dramatic_still.py`) Across All `76` `STILL` Shots** | §4.3 defines a 3-Tier Still Motion Ladder: `TIER_1` (`1.0–2.2s` `parallax_25d`), `TIER_2` (`2.2–3.5s` `qwen_nextpose` / state flip), `TIER_3` (`3.5–5.0s` cutout relocation `>=25%` / plate swap `>=30%`). | Across the `76` `STILL` shots in `mrbeast_12min_video_mold (1).json` (`19` `TIER_1`, `40` `TIER_2`, `17` `TIER_3`), **`55` of `76` shots exceed their zone's `BP-170` `static_still_max_s_by_zone`** (`1.5s` in Z1/Z5, `2.0s` in Z2/Z4, `2.5s` in Z3): specifically **`2` of `19` `TIER_1` shots** (`SH003` at `1.875s > 1.5s` in `S01`/`Z1` and `SH226` at `1.625s > 1.5s` in `S15`/`Z5`, both describing cutout leaps/slams in `track_5_visual_events`), **`36` of `40` `TIER_2` shots**, and **`17` of `17` `TIER_3` shots**. | `BP-170` (`edit/dramatic_still.py:39–142`) sets `static_still_max_s_by_zone` (`1.5s` in Z1/Z5, `2.0s` in Z2/Z4, `2.5s` in Z3) and **FAILs any still longer than `static_still_max_s_by_zone`** unless it has a `TIER_3` `dramatic_change` (`cutout_relocation` or `plate_swap`). Consequently, `38` of the `76` `STILL` shots in the reference grid (`2` `TIER_1` + `36` `TIER_2`) currently trigger `DS-01` `FAIL`. | Preserve `BP-170` (`edit/dramatic_still.py`) severity (`FAIL`) without relaxation (identical policy in both `M-04` and `CHG-09`): add `still_motion_tier` (`TIER_1`, `TIER_2`, `TIER_3`) to the schema, and **keep both Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose_or_lighting_state_flip`) strictly bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`)** until a measurable pose-delta + identity metric for Tier 2 is validated and approved by the creator (`CD-03`). Only Tier 3 (`cutout_relocation >= 0.25` or `plate_swap >= 0.30`) unlocks holds up to `5.0s`. In the Layer 3 reference grid, upgrade `SH003` (`1.875s`) and `SH226` (`1.625s`) to structured `TIER_3` `dramatic_change` specs matching their `track_5_visual_events` text, and either supply structured `TIER_3` specs or trim the `36` over-cap `TIER_2` reference shots. | 
| **M-05** | **Layer 1 Anchor Beats (`AB07..AB12`) vs Layer 3 Segments (`S09..S16`) & `BP-142` / `BP-04`** | §3.4 lists `AB07..AB12` windows (`360–420s`, `420–540s`, `540–570s`, `570–600s` Climax, `600–690s` Aftermath), while §5.1 lists `S09..S16` windows (`S09: 330–375s`, `S10: 375–430s`, `S11: 430–480s`, `S12: 480–540s`, `S13: 540–600s`, `S14: 600–660s`, `S15: 660–690s` Climax I, `S16: 690–720s` Climax II/Resolution). | `twelve_anchor_beats` (`AB07..AB12`, `L305–402`) and `segments_summary_16` (`S09..S16`, `L1119–1294`) have mismatched `window_s` and climax placement (`AB10` puts Climax in `S13` at `570–600s`, while `segments_summary_16` and `zones_5` put Climax `Z5` in `S15–S16` at `660–720s`). In `mrbeast_12min_video_mold (1).json`, cumulative spoken words reach `1,724 / 2,066` (`83.45%`) at the end of `S13` (`600.0s`), cross `90.0%` (`1,860` words) at `~644.1s` inside `S14`, and reach `1,909 / 2,066` (`92.40%`) at the end of `S14` (`660.0s`). | `BP-169` puts `late_third_480_660s` at `480–660s` (`S12–S14`) and `climax_660_720s` at `660–720s` (`S15–S16`). `BP-04` (`ENG-5`, `answer_after_share = 0.90`) requires the central answer/resolution to start **only after at least `90%` of the episode's spoken words have been delivered**, and `BP-142` sets `turn_slots_D = [4, 6, 8, 10, 11, 13]`. | Align `AB07..AB12` in Layer 1 to match `segments_summary_16`, `BP-169`, `BP-142`, and `BP-04`: `AB07` (`S08–S09`, `270–375s`), `AB08` (`S10–S11`, `375–480s`), `AB09` (`S12`, `480–540s`), `AB10` (`S13–S14`, `540–660s`), `AB11` (`S15`, `660–690s`, starting at `92.40%` cumulative words), and `AB12` (`S16`, `690–720s`, starting at `96.22%` cumulative words). Enforce `AB11`/`AB12` via **two independent checks**: (1) timeline windows `660–690s` (`S15`) and `690–720s` (`S16`), and (2) `BP-04` (`answer_after_share >= 0.90`) checked on **cumulative spoken word share (`>= 90%` of episode words)**. | 
| **M-06** | **Dangling `BP-68` and `BP-155` Citations** (Claim-ID Grounding) | Line 15 cites `BP-68` for historical fact/claim grounding. | Line 100 (`topic_and_editorial_contract`) cites `BP-68, BP-155` for `claim_id` verification of dates, troop counts, weapon ranges, and economic figures. | **Neither `BP-68` nor `BP-155` exists in `sourced_rules.json`!** Claim grounding is enforced by `ZI-02` (`explainer_engine/scripting/film_shots.py:846–851`), `PV-37` (`explainer_engine/scripting/claims.py:1–10`, Invariant 5), and `HY-4` (`explainer_engine/research/hypotheses.py:66–68`). | Replace dangling `BP-68` and `BP-155` citations in `mrbeast_12min_master_mold.md` and `mrbeast_12min_video_mold.json` with canonical `ZI-02` / `PV-37` (Invariant 5). | 
| **M-07** | **Dangling `BP-79` Citation** in `AB12` (Hard-Cut Ending) | Line 82 (`AB12_FINAL_SYNTHESIS_AND_HARD_CUT`) cites `BP-79`. | Line 394 (`AB12`) cites `"ending on a hard cut (BP-79)"`. | **`BP-79` does not exist in `sourced_rules.json`!** Abrupt post-payoff ending is **`BP-43`** (`film_shots.py:56, 938–940`, `KP-40`) and channel-worlds outro bridge is **`BP-106`** (`film_shots.py:55, 941–947`). | Replace dangling `BP-79` in `mrbeast_12min_master_mold.md:82` and `mrbeast_12min_video_mold.json:394` with canonical `BP-43` and `BP-106`. | 
| **M-08** | **Mis-Cited `BP-125` in Still Motion Ladder** (`37` shot `qa_gate` entries) | Lines 33, 115, 117 cite `BP-125` for 2.5D parallax & character eye-blink/breathing cycle. | Lines 39, 751, 760 and `37` shot `qa_gate` strings cite `BP-125_motion_contract_pass` / `BP-125_and_BP-84_state_change_pass`. | In `sourced_rules.json`, **`BP-125` is `area: "maps"`** (`altitude_change_s: [4.0, 8.0]`)! 3-layer 2.5D parallax is **`BP-35`** (`layers_min: 3`), character eye-blink/moving hold is **`BP-132`** (`blink_every_s: [2.0, 4.0]`, `moving_hold_after_s: 2.0`), and dramatic still hold is **`BP-170`**. | Re-key Still Motion Ladder citations from `BP-125` to `BP-35` (Tier 1 2.5D parallax), `BP-132` (moving hold / blink), and `BP-170` (Tier 3 dramatic state change); reserve `BP-125` strictly for `MAP` altitude transitions. | 
| **M-09** | **`BP-84` vs `BP-169` / `BP-170` Scope Collision** | Lines 33, 96, 115 cite `BP-84` for `<=5.0s` still hold cap. | `18` shot `qa_gate` strings cite `BP-84_dramatic_state_change_mandatory`. | In `sourced_rules.json`, **`BP-84`** (`edit/board.py:38–39, 155`) sets `min_shot_s: 2.5`, `min_insert_s: 2.0`, and `bubble_chars_per_line: 26` (`BUBBLE-1`), colliding with `BP-169` (`1.0–2.5s` hyped shots). | Scope `RHYTHM-2` (`min_shot_s: 2.5` in `edit/board.py`) to `calm_docudrama` (`/3`), keep `BUBBLE-1` (`bubble_chars_per_line: 26`) active across all profiles, and re-key still-hold `qa_gate` strings to `BP-170` (`RL-04`). | 
| **M-10** | **`BP-128` Handle-Frame Mismatch (`[4, 12]` vs `[12, 16]`) & Exact `152`-Shot LTX Frame Math** | Line 95 sets `ltx_generation_frame_count = 8*ceil((usable_frames + 8 - 1)/8) + 1` (`>=4` handles/side). | Lines 29, 466, 940 and `152` `VIDEO` shots (`10,368` usable frames = `432.0s`) set `handle_frames in [4, 12]` (`head >= 4, tail >= 4`), totaling **`12,120` generated LTX frames** (`+1,752` overhead frames = `73.0s`). | In `sourced_rules.json` and `production/assemble.py:714–727`, **`BP-128`** requires `handle_frames: [12, 16]` (`>=24` total extra frames before `8k+1` rounding), which on the same `152` `VIDEO` shots requires **`14,552` generated LTX frames** (`+4,184` overhead frames = `174.33s`), flagging `REVIEW` on every shot with `4..11` handle frames. | Propose a **transition-aware handle hypothesis** (`[HYPOTHESIS]`, `severity: "REVIEW"`) in `BP-128` & `assemble.py`: hard/J/L-cut `VIDEO` shots (`135` of `152` in the Mold) use `handle_frames >= 4` per side (`>=8` total), while whip-pan (`BP-129`) and crossfade (`BP-31`) boundary shots (`17` of `152`) require `handle_frames >= 12` per side (`>=24` total). Exact verified math across the `152` `VIDEO` shots: all-`>=4` (`12,120` frames) vs all-`>=12` (`14,552` frames) saves **`2,432` frames (`16 * 152` = `101.33s` of LTX generation, a `16.71%` reduction in generated frames)**; transition-aware (`12,392` frames) saves **`2,160` frames (`90.00s`, a `14.84%` reduction)** (correcting prior unverified `3,648–4,864` / `~38%` estimates). | 
| **M-11** | **`BP-122` Acoustic Perspective Parameter Drift** | Line 37 (`DM-09`) references `shot_size` EQ (`Wide/Medium/ECU`). | L141/875 say `Wide -3dB @ 3.5kHz, 18% wet; ECU +2dB @ 180Hz, 95% dry`, while `140+` shots say `-3.5dB @ 3500Hz, 28% wet` and `+2.5dB @ 180Hz, 92% dry`. | `sourced_rules.json` (`BP-122`) and `production/assemble.py:291–296, 480–483` use `shelf_hz: 6000`, `wide_shelf_db: -4.0`, `wide_wet: 0.22`, `close_dry: 0.95`, `proximity_db: 2.0`, `proximity_hz: 140`. | Replace conflicting hardcoded EQ/wet strings in `mrbeast_12min_video_mold.json` with symbolic perspective keys (`"perspective": "far" | "mid" | "near"` matching `sound_director.py:43`) resolved dynamically from `sourced_rules.T("BP-122", ...)`. | 
| **M-12** | **Relative Color Continuity (`BP-166`) vs Raw HEX (`D-22`) & Layer 1/2/3 Instance Contamination (`1637 Tulip Mania` Strings in Layer 1/2)** | Line 38 (`DM-10`) replaces global Kelvin/HEX locks with relative scene offsets, and §2 declares Layer 1 and Layer 2 topic-agnostic. | Lines 795–797 & `254` shots enforce `BP-166_SCENE_AND_CHARACTER_HEX_LOCKED (apply relative mood offset only)`; meanwhile, Layer 1 (`layer_1_narrative_constitution`, `L100–402`) and Layer 2 (`layer_2_production_profile`, `L748–918`) still contain **`24` hardcoded 1637 Dutch Tulip Mania example strings** (`Haarlem`, `guilder`, `Semper Augustus`, `Pieter`, `Waag`, `1637`). *(Note: All `16` segment headers `S01..S16` in `segments_summary_16` of `2ca7f56f...` already match their shot duration sums `720.0s` = `17,280` frames and word sums `2,066` words with `0` discrepancy; `S02` is `30.0s` \[`30.0–60.0s`, `12` shots, `88` words\] — the `79.2s vs 59.2s` note from an unverified external draft is retired.)* | `BP-166` checks `sat_drift_max: 0.08`, `luma_drift_max: 0.08`, `hero_palette_max: 0.15`; `D-22` / `LT-65` bans raw `#RRGGBB` tokens in generation prompts; `ZI-09` (`film_shots.py:920–935`) requires topic-agnostic templates. | Purge all `24` Tulip Mania strings from Layer 1 and Layer 2 into `layer_3_reference_instance` (`reference_only: true`), keep raw HEX swatches strictly in `character_sheet_ref` / `color_qa` (`BP-166`), ban raw `#RRGGBB` tokens in generation prompts (`D-22`/`LT-65`), and apply act mood shifts via `explainer_engine/compose/episode_look.py` (`AC-17`) and `explainer_engine/finish/grade.py` / `production/assemble.py` Reinhard CIE LAB transfer (`BP-130`), while keeping `BP-166` (`training/video_qa.py`) at `REVIEW` severity. | 

## 4. Component & Subsystem Impact Analysis (`CURRENT → MASTER MOLD REQUIREMENT → KEEP → CHANGE → REPLACE → REMOVE → TRADE-OFFS → RECOMMENDATION`)

Every major pipeline subsystem is evaluated below using the mandatory preservation framework.

### 4.1 Topic, Research Dossier, Claim Map & Episode Rulebook

* **Files & Agents**: `.claude/agents/episode-standards-director.md`, `.claude/skills/science-grounding/SKILL.md`, `.claude/skills/crossover-episode/SKILL.md`, `explainer_engine/standards/rulebook.py`, `explainer_engine/research/fan_brief.py`, `explainer_engine/research/hypotheses.py`, `explainer_engine/research/reference_study.py`, `explainer_engine/scripting/claims.py`.

* **CURRENT**:

  * `episode-standards-director.md` and `standards/rulebook.py` build `episode_rules.json` with legal/platform/provider rules, risk register, and anti-monotony rules.

  * `research/fan_brief.py` checks crossover research depth (`MIN_SOURCES=6`, `MIN_THEORIES=5`, `MIN_CASUAL_SHARE=0.30`, `MIN_FAN_SHARE=0.30`) and flags stock clichés (`TEMPLATE_PHRASES`).

  * `research/hypotheses.py` validates `story_hypotheses.json` (`>=3` distinct premises, `evidence >= 3`, beat sheet starting on `hook`/`question` and containing `payoff`).

  * `scripting/claims.py` loads `claim_map.md` (`established`, `model`, `reasoned`, `guess`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 1)**:

  * Topic and research outputs must supply the raw material required by the Two-Phase Hook (`AB01` concrete physical visual stake + `AB02` exact historical divergence date/place and binary measurable question), the 2–3 Re-Engagement Spikes (`180s` `S06` spectacle/anomaly and `360s` `S09` midpoint reversal), and the 4 Creative Rubrics from Part I of the Research Compendium (`Cross-Era Clash`, `Modern Tech in Past`, `Historical Mystery/What-If`, `Civilization Bootstrap`).

  * Game-show/challenge filler phrases (`"Last one standing wins"`, `"Subscribe in the next 3 seconds"`, `"I spent $1,000,000"`) must be flagged alongside `TEMPLATE_PHRASES`.

* **KEEP**:

  * All of `standards/rulebook.py`, `scripting/claims.py`, `research/fan_brief.py`, `research/hypotheses.py`, and `research/reference_study.py`.

* **CHANGE**:

  * Extend `research/fan_brief.py:TEMPLATE_PHRASES` with the game-show/challenge ban list from Mold Layer 1 (`§3.3`).

  * Extend `schemas/story_hypotheses.schema.json` and `research/hypotheses.py` with optional `mold_hooks` fields (`cold_promise_visual`, `rehook_180s_candidate`, `midpoint_360s_reversal_candidate`, `recommended_profile_id` in `A..D`) so research directly feeds Stage 1b (`variant_plan.py`) and Stage 1 (`story-architect.md`).

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Making `mold_hooks` optional on `story_hypotheses/1` (or required only when `rhythm_profile == "mrbeast_animated"`) preserves 100% backward compatibility with existing hypothesis fixtures (`tests/unit/test_hypotheses.py`) while ensuring new episodes gather re-hook evidence during research rather than inventing it during scripting.

* **RECOMMENDATION**: **KEEP** all research/rulebook modules; **CHANGE** `fan_brief.py` and `hypotheses.py` / `story_hypotheses.schema.json` with backward-compatible Mold hook/spike fields.

### 4.2 Story Architect, Narrative Anchors (`AB01..AB12`) & Adaptive Profiles (`A..D`)

* **Files & Agents**: `.claude/agents/story-architect.md`, `.claude/skills/story-engine/SKILL.md`, `explainer_engine/scripting/variant_plan.py`, `explainer_engine/scripting/scenario.py`, `explainer_engine/scripting/story_lint.py`, `explainer_engine/schemas/script_variants.schema.json`.

* **CURRENT**:

  * `variant_plan.py` (Stage 1b, `OR-31`) scores 2–3 variants across profiles `A..D` (`BP-141`), checking `BP-109` (`60/30/10 ±5%`), `BP-142` (`turn_slots_D = [4, 6, 8, 10, 11, 13]` must be played scenes), `BP-141` (`map_run_max_s=90`, `kuleshov_max_s=7`), `BP-127` (`non_character_run_max_s=45`), `BP-105` (`narrator_share` `45–70%`), and `BP-107` (`11–17 shots/min`).

  * `story-architect.md` lays out 16 segments on Template D ("the 15-minute historical docudrama"), placing midpoint at `40–60%` of words (`BP-75`), turn gap `<=150s` at `170 WPM` (`BP-76`), and resolution after `90%` of words (`BP-04`).

  * `story_lint.py` checks `ST-00..ST-24`, converting word counts to seconds using flat `WORDS_PER_S = SR.T("BP-01", "wpm_target") / 60` (`170 WPM`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 1 & Layer 2)**:

  * Episode target runtime is `12 minutes` (`720.0s`, `BP-167`), structured into `16` segments (`S01..S16`) across `5` Rhythm Zones (`BP-169`) and `12` Anchor Beats (`AB01..AB12`).

  * Word-to-second conversion in `variant_plan.py:segments_from_script` and `story_lint.py` must use zone-aware pace (`rhythm_profile.words_to_seconds` or `syllables.seconds(..., zone=seg.get("rhythm_zone"))`) on `/4` scripts instead of flat `170 WPM`.

  * `variant_plan.py:checks` (`VP-18`) must check per-zone shot density (`BP-169`) when `rhythm_profile == "mrbeast_animated"`, rather than flagging `22.1 shots/min` as a `BP-107` (`11–17 shots/min`) violation!

  * `story_lint.py` must check `ST-00` as `FAIL` on `is_scene_script` (fixing the `== "production_script/3"` bug on line 75) and verify the 12 Anchor Beats (`AB01..AB12`: e.g., `3:00` re-hook spike in `S06`, `6:00` midpoint reversal in `S08/S09`, pre-climax convergence in `S12`, climax in `S13–S15`, resolution in `S16` after `90%`).

* **KEEP**:

  * Stage 1b variant selection (`OR-31`), `scenario.py` approval gate (`OR-15`, `PV-45`), Template D 16-segment backbone, `BP-141` profiles `A..D`, `BP-142` turn-scene enforcement (`ST-24`), and causal `BUT`/`THEREFORE` checks (`ST-02`, `ST-20`).

* **CHANGE**:

  * Update `.claude/agents/story-architect.md` and `.claude/skills/story-engine/SKILL.md`: change `15-minute` to `12-minute (720s, BP-167)`, require `production_script/4` with `episode.rhythm_profile: "mrbeast_animated"` and `segments[].rhythm_zone`, and embed the `16`-segment / `12`-Anchor-Beat mapping table.

  * Update `scripting/variant_plan.py`: (a) in `segments_from_script`, pass `zone=seg.get("rhythm_zone")` to `syllables.seconds`; (b) in `dynamics` and `checks` (`VP-18`), if `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, check shot rate against the `BP-169` weighted episode band (`18–28 shots/min`) and per-zone bands via `rhythm_lint` instead of `BP-107` (`11–17 shots/min`).

  * Update `scripting/story_lint.py`: (a) replace `doc.get("schema") == SCENE_SCHEMA` with `is_scene_script(doc)`; (b) on zoned scripts (`mrbeast_animated`), compute `line_starts` and `ST-13` turn gaps using `rhythm_profile.words_to_seconds` / `syllables.seconds(zone=...)`.

* **REPLACE**: None.

* **REMOVE**: Remove hardcoded `15-minute` prose in `.claude/agents/story-architect.md` (preserving `calm_docudrama` compatibility in code).

* **TRADE-OFFS**: Keeping `BP-142` (`turn_slots_D = [4, 6, 8, 10, 11, 13]`) while aligning `AB01..AB12` to `S01..S16` means zero breaking changes to `test_variant_plan.py` or `test_story_engine.py`, while giving the Story Architect explicit 12-minute window budgets (`30s` hook, `60s` early setup, `390s` calm middle with `S06` 180s and `S09` 360s spikes, `180s` late third, `60s` climax/resolution).

* **RECOMMENDATION**: **KEEP** `variant_plan.py`, `scenario.py`, and `story_lint.py`; **CHANGE** them to be profile-aware (`mrbeast_animated` vs `calm_docudrama`) and fix the `/4` schema check in `story_lint.py`.

### 4.3 Scene Writer & Register / Immersion Linting

* **Files & Agents**: `.claude/agents/scene-writer.md`, `.claude/skills/dialogue-scenes/SKILL.md`, `.claude/skills/narration-script/SKILL.md`, `explainer_engine/scripting/scene_lint.py`, `explainer_engine/scripting/register_lint.py`, `explainer_engine/scripting/narration_lint.py`.

* **CURRENT**:

  * `scene-writer.md` writes `segments[].lines` (`text`, `speaker`, `claims`, `to`, `intent`), budgeting words at flat `BP-01` (`170 WPM`).

  * `scene_lint.py` enforces `SC-01..SC-12` (`BP-70..73`, `BP-87` show-don't-tell, `BP-88` full immersion), but line 139 checks `doc.get("schema") == "production_script/3"`, returning `[]` on `production_script/4`!

  * `narration_lint.py` enforces `N-01..N-17`, including `BP-06` sentence length (`median <= 12`, `max <= 20` REVIEW, `hard_max <= 25` FAIL), `BP-03` hook forms, `BP-04` 30-second contract (`contract_words = 85`), `BP-10` pause holds (`<=1.0s`, boundary `<=1.5s`), and `BP-17`/`BP-18` questions.

  * `register_lint.py` enforces `RG-01` (`BP-140` banned AI-register words, FAIL) and `RG-02..04` (`BP-114` soft tier, REVIEW).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 1 & Layer 2)**:

  * On `/4` scripts (`mrbeast_animated`), `scene-writer.md` must budget segment words using the segment's `rhythm_zone` target WPM (`BP-169`: `193` in `hook_0_30s`, `176` in `early_30_90s`, `166` in `middle_calm_90_480s`, `185` in `late_third_480_660s`, `160` in `climax_660_720s`) AND vary sentence lengths inside each zone (`BP-169` creator decision `2026-11-01`: pace variation inside and between zones, never flat tempo).

  * Per-zone median sentence length caps from `BP-169` (`median_words_max`: `8` in Z1, `9` in Z2, `11` in Z3, `9` in Z4, `7` in Z5) are tighter than `BP-06`'s flat `12` words.

  * `scene_lint.py` must bind on `production_script/4` (`is_scene_script`).

  * `register_lint.py` (`BP-140`) must remain strictly enforced (banning AI-slop words like `"delve"`, `"tapestry"`, `"testament"`), while energetic historical verbs (`BP-172` `fast_action_verbs`) remain fully allowed.

* **KEEP**:

  * All `SC-01..SC-12` scene/dialogue rules, `BP-87`/`BP-88` immersion and show-don't-tell rules, `register_lint.py` (`RG-01..04`), and `D-62`/`D-63` reported-speech rules for living people.

* **CHANGE**:

  * Fix `scene_lint.py:139` (`binding(doc)`) from `doc.get("schema") == SCENE_SCHEMA` to `is_scene_script(doc)`.

  * Add zone-aware sentence-length and pace-variation checks to `narration_lint.py:doc_findings(doc)` when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`: check each segment's median sentence words against `BP-169`'s `median_words_max` for its zone (`8 / 9 / 11 / 9 / 7`) and verify intra-zone sentence-length variance (so a zone does not read at a robotic flat cadence).

  * Update `.claude/agents/scene-writer.md` and `.claude/skills/narration-script/SKILL.md` to reference `rhythm_zone` word budgets (`BP-169`), the Two-Phase Hook (`0–12s` promise + `12–36s` hinge), and intra-zone sentence-length modulation (alternating 4–6 word punch sentences with 10–14 word setup sentences).

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Keeping `narration_lint.lint(text)` unchanged for raw `.txt` files while adding zone-aware checks in `narration_lint.doc_findings(doc)` preserves all existing unit tests on legacy `.txt` files (`examples/stone_age/day1_v3/narration_tts.txt`) while enforcing `BP-169` zone word/sentence targets on `/4` JSON scripts.

* **RECOMMENDATION**: **KEEP** `scene_lint.py`, `register_lint.py`, and `narration_lint.py`; **CHANGE** `scene_lint.py` for `/4` binding and add zone-aware sentence/cadence checks to `narration_lint.doc_findings`.

### 4.4 Beat Writer & Visual Beats (`lines[].visual_beats`)

* **Files & Agents**: `.claude/agents/beat-writer.md`, `.claude/skills/visual-beats/SKILL.md`, `explainer_engine/production/beats.py`, `explainer_engine/production/accents.py`, `explainer_engine/production/graphics.py`, `explainer_engine/production/parallax.py`, `explainer_engine/production/fill_holds.py`.

* **CURRENT**:

  * `beats.py` validates and renders `lines[].visual_beats` (`text`, `label`, `prop`, `chart`, `highlight`, `symbol`, `accent`, `expression`) and opt-in event-bound `cue`s (`VB-08`).

  * Line 107 of `beats.py` defines `def scene_rules(doc: dict) -> bool: return doc.get("schema") == "production_script/3"`. On `/4`, `scene_rules(doc)` evaluates to `False`, which causes `beats.py` to fall back to `/2` metronome rules (`v2_target_s = 1.5s`, `v2_gap_fail_s = 4.0s`, mandatory sound cue on every beat)!

  * `fill_holds.py` cuts reframed shots into still holds exceeding `BP-40` (`hook_max_still_s = 5.0s`, `body_review_still_s = 20.0s`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 2)**:

  * On `/4` scripts, `scene_rules(doc)` must be `True` (`is_scene_script`): beats are tied to new information (`BP-93`), cues are opt-in and event-bound (`VB-08`), and silence is the default.

  * Visual-event gaps and still holds on `/4` scripts are governed by `BP-169` (`still_max_s`: `2.5s` in Z1/Z5, `3.5s` in Z2/Z4, `5.0s` in Z3) and `BP-170` (`dramatic_still.py`), not `BP-40`'s `20s / 40s` body still limits.

* **KEEP**:

  * All 8 visual beat kinds, `BP-93` word-anchoring (`anchored`), `VB-08..11` event-bound cue grammar, `accents.py`, `graphics.py`, and `parallax.py`.

* **CHANGE**:

  * Fix `production/beats.py:107` (`scene_rules(doc)`) and `audio/layers.py:53` (`silence_is_default(timed)`) to check `is_scene_script` (`in ("production_script/3", "production_script/4")`).

  * Update `production/fill_holds.py` so that when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, `max_gap` per shot uses the zone's `still_max_s` from `rhythm_profile.zone_at_time` (`2.5s / 3.5s / 5.0s`) instead of `BP-40`'s `20.0s`.

  * Update `.claude/agents/beat-writer.md` and `.claude/skills/visual-beats/SKILL.md` to reference `/4` alongside `/3` and note that `BP-169`/`BP-170` govern still hold limits on zoned episodes.

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Fixing `scene_rules(doc)` to `is_scene_script` prevents a catastrophic regression on `/4` scripts with a 2-line change.

* **RECOMMENDATION**: **KEEP** `beats.py`, `accents.py`, `graphics.py`, `parallax.py`; **CHANGE** `beats.py:107`, `layers.py:53`, and `fill_holds.py` for `/4` and `BP-169` zone awareness.

### 4.5 Performance Director, Voice Casting, Odom Polish & Character Dialogue (`D-90`)

* **Files & Agents**: `.claude/agents/performance-director.md`, `.claude/agents/voice-caster.md`, `.claude/skills/elevenlabs-voice/SKILL.md`, `config/channel_voices.json`, `explainer_engine/audio/hype_read.py`, `explainer_engine/audio/narrator_polish.py`, `explainer_engine/audio/casting.py`, `explainer_engine/audio/voice_audition.py`, `explainer_engine/audio/voice_check.py`, `explainer_engine/scripting/speech.py`, `explainer_engine/production/silent.py`, `explainer_engine/production/__main__.py`.

* **CURRENT**:

  * `config/channel_voices.json` names **Odom** (`CcSJ2r3qw0XU9gJpEPyk`, `eleven_v4`, `status: "channel"`) with `baseline: null` (awaiting the approved first sample read per `OR-19`) and retires `Grandpa Spuds Oxley`.

  * `audio/narrator_polish.py` applies the creator-approved ffmpeg EQ/bass-shelf chain (`+12 dB @ 150 Hz`, `-2 dB @ 300 Hz`, `-0.6 dB` trim, `highpass=60`, `afftdn`, `alimiter=0.95`), preserving exact duration (`abs(after - before) <= 1/30 s`).

  * **Critical Bug in `production/__main__.py:119`**: `if not S.has_dialogue(doc): polish = narrator_polish.polish_in_place(out / "narration.wav")`. When a script has character dialogue (`S.has_dialogue(doc) == True`), `narrator_polish` is **completely skipped**, even for the narrator's own turns!

  * `audio/hype_read.py` validates per-zone ElevenLabs v4 tags (`HR-01`), max 1–2 stressed ALL-CAPS words per sentence (`HR-02`), max 1 tag per clause (`HR-03`), and chunk reset limits (`<=800` chars / `<=90s`, `HR-04`), plus `hype_score` (`f0_iqr_st >= 5.0`, `speaking_wps` `3.3–4.2`, `dynamic_range_db` `10–14`), but is **not wired** into `production/validate.py` or `.claude/agents/performance-director.md`.

  * `D-90` (`voice-caster.md` step 7): each speaking character gets one fixed ElevenLabs voice for the whole episode, read first, and that audio slice conditions the LTX-2.5 `DIALOGUE_CU` clip (`audio_slice_sha256` in `shot_spec/1`). However, `audio/spine.py` still only reserves post-hoc windows (`source: "planned"`), and no helper slices pre-recorded character takes into `audio_spine/2` with `source: "clip"` + `clip_sha256` before `edit/router.py` runs!

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 1 §3.2 & Layer 2 §4.1)**:

  * **Narrator (`narrator_vo`)**: Single voice **Odom** (`CcSJ2r3qw0XU9gJpEPyk`, `eleven_v4`) across all 5 zones; energy and tempo modulate across zones via sentence length, punctuation pause trimming (`pause_pad.py`), and `BP-169` zone-allowed v4 audio tags (`hype_read.py`). Zero pitch-shifting or unverified TTS API speed knobs. Every Odom narrator take must pass through `narrator_polish.py` regardless of whether the episode contains character dialogue (applying `narrator_polish` only to Odom's narrator chunks/turns, never to character voices).

  * **Diegetic Character Dialogue (`diegetic_character_dialogue`)**: Governed by `D-90`, `BP-138`, `D-62` (living real people silent, `PV-55`), and `D-63` (reported speech by narrator). Character takes must be generated/sliced before `edit/router.py` routes `DIALOGUE_CU` shots so `audio_spine/2` holds a verified `clip_sha256` and `shot_size` EQ (`BP-122`) applies only to diegetic dialogue and foley, while narrator VO stays on its locked studio chain (`ED-01`).

* **KEEP**:

  * `config/channel_voices.json`, `audio/narrator_polish.py`, `audio/hype_read.py`, `audio/casting.py`, `audio/voice_audition.py`, `audio/voice_check.py`, `scripting/speech.py`, `production/silent.py`.

* **CHANGE**:

  * Fix `scripting/speech.py:60` and `production/silent.py:249,276` to check `is_scene_script(doc)` so `PV-55` (`D-62`) and `PV-56` (`D-63`) bind on `production_script/4`.

  * Fix `production/__main__.py:cmd_words` and `audio/narrator_polish.py` so that when `S.has_dialogue(doc)` is `True`, `narrator_polish.polish_narrator_spans_in_place(out / "narration.wav", words, toks, doc)` runs at line `119` (**after** `join_reads`, `scribe_words.align`, `voice_check.check_speakers` on raw unpolished timbre, and `pause_pad.pad_pauses` writing `48 kHz` mono PCM `narration.wav`), splicing the polished `NP.CHAIN` signal strictly over Odom's narrator spans (`S.speaker(line) == "narrator"`) with `10 ms` cosine ramps inside inter-turn silence gaps while leaving character dialogue spans bit-for-bit untouched.

  * Wire `audio/hype_read.py:check_prosody_plan` into `production/validate.py:check_script` for `/4` (`mrbeast_animated`) scripts (checking narrator lines only).

  * Add a pre-render character take registration helper in `audio/spine.py` (`bind_character_takes`) that records the ElevenLabs character take's measured frame length and `clip_sha256` into `audio_spine/2.post_hoc_shots` (`source: "clip"`) so `edit/router.py:_spine_window` succeeds for `DIALOGUE_CU` shots (`D-90`).

  * Update `.claude/agents/performance-director.md`, `.claude/agents/voice-caster.md`, and `.claude/skills/elevenlabs-voice/SKILL.md` to replace `Grandpa Spuds Oxley` with `Odom`, document `hype_read.py` zone tag palettes (`BP-169`, `BP-171`), and enforce `narrator_polish.py`.

* **REPLACE**: None.

* **REMOVE**: Remove stale references to `Grandpa Spuds Oxley` as the active narrator in `.claude/skills/elevenlabs-voice/SKILL.md` (keeping his historical note in `config/channel_voices.json`).

* **TRADE-OFFS**: Applying `polish_narrator_spans_in_place` on `narration.wav` at line `119` (after `voice_check` and `pause_pad`) guarantees: (1) `voice_check.check_speakers` always evaluates raw unpolished timbre (`EL-13`), (2) `wave.open` in `narrator_polish.py:45` never crashes on `.mp3` chunk inputs, (3) both single-file (`len(audio) == 1`) and multi-chunk (`len(audio) > 1`) CLI invocations work identically, and (4) Odom always receives his `+12 dB @ 150 Hz` bass shelf while character voices stay 100% unpolished.

* **RECOMMENDATION**: **KEEP** all voice/audio modules; **CHANGE** `production/__main__.py`, `production/validate.py`, `audio/spine.py`, `speech.py`, `silent.py`, and the 3 voice agent/skill markdown files.

### 4.6 Script Schemas, Stage Guard, Validation & Editorial Gate

* **Files & Agents**: `.claude/agents/script-critic.md`, `explainer_engine/schemas/production_script.schema.json`, `explainer_engine/scripting/stage_guard.py`, `explainer_engine/scripting/script_approval.py`, `explainer_engine/production/validate.py`, `explainer_engine/production/editorial_gate.py`.

* **CURRENT**:

  * `schemas/production_script.schema.json` supports `production_script/1`..`production_script/4` and defines `episode.rhythm_profile`, `segments[].rhythm_zone`, and `shots[].dramatic_change`.

  * `stage_guard.py` includes `rhythm_zone` in `SEG_STORY` (owned by `architect`).

  * **Critical P0 Bug**: **11 modules** (`validate.py:89`, `editorial_gate.py:342,347`, `script_approval.py:51`, `production_gate.py:89`, `scene_lint.py:139`, `story_lint.py:75`, `speech.py:60`, `beats.py:107`, `silent.py:249,276`, `staging.py:418`, and `audio/layers.py:53`) hardcode `== "production_script/3"` (or `_sa.BINDING` / `SCENE_SCHEMA`), causing `/4` scripts to bypass `/3` gates.

  * Furthermore, `validate.py:check_script` still checks `PV-52` against flat `BP-01` (`155–185 WPM`) and runs `board.check` (`RHYTHM-1` `BP-40` `<=10 pictures/min`, `RHYTHM-2` `BP-84` `min_shot_s = 2.0s`), which **FAILs or flags REVIEW on every zoned `/4` script** (since Z1/Z2/Z4/Z5 have `24–30 shots/min` and `1.0–2.5s` shots!), and never calls `scripting/rhythm_lint.py` or `audio/hype_read.py` (`WP-R7`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 1–3)**:

  * `production_script/4` must inherit 100% of `/3`'s scene, dialogue, immersion, real-person, editorial review (`editorial_review/2` + `story_page.md`), and approval guarantees (`is_scene_script(doc)`), while delegating rhythm, shot rate, still hold, and prosody checks to `rhythm_lint.py`, `dramatic_still.py`, `rhythm_profile.py`, and `hype_read.py` (`WP-R7`).

  * `production_script.schema.json` `/4` should also allow optional `anchor_beat_id` (`AB01..AB12`) on `segments[]` and optional `still_motion_tier` (`TIER_1_SHORT_PARALLAX_STILL`, `TIER_2_MEDIUM_STATE_SHIFT_STILL`, `TIER_3_LONG_DRAMATIC_RELOCATION_STILL`) on `shots[]`.

* **KEEP**:

  * Single-file `production_script.json` architecture (`D-43`), `stage_guard.py` field ownership and `OR-32` fresh-read verification, `editorial_gate.py` (`EG-01..23`), and `script_approval.py`.

* **CHANGE**:

  * Add a canonical helper `explainer_engine/scripting/schema_version.py` (`is_scene_script(doc_or_schema) -> bool` for `/3` and `/4`, `is_zoned_rhythm_script(doc_or_schema) -> bool` for `/4`) and replace all **11** hardcoded `== "production_script/3"` checks with `is_scene_script(...)`.

  * In `production/validate.py`: when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`:

    1. Call `rhythm_lint.check` and `hype_read.check_prosody_plan`.

    2. In `estimated_words(doc)`, estimate per-line word timings using the segment's `rhythm_zone` WPM (`rhythm_profile.zone_wpm`) rather than a single flat `voice.pace_wpm`.

    3. In `board_findings(timed, doc)`, suppress `BP-40` `RHYTHM-1` (`10 pictures/min` ceiling) and `BP-84` `RHYTHM-2` (`2.0s` floor where zone `shot_len_s_band` allows `1.0s` or `1.2s`), deferring to `rhythm_lint.py` (`WP-R7`) while preserving `STATE-1`, `HERO-1`, and `BUBBLE-*` checks on `board.py`!

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Deferring only `RHYTHM-1..3` in `board.py` on `/4` scripts while keeping `STATE-1` (no object shown before its word), `HERO-1` (correct hero on screen), and `BUBBLE-*` preserves the repository's strongest semantic storyboard checks without false-failing fast MrBeast-style cuts.

* **RECOMMENDATION**: **KEEP** `production_script.schema.json`, `stage_guard.py`, `validate.py`, `editorial_gate.py`, `production_gate.py`; **CHANGE** all 11 modules to `is_scene_script` and wire `WP-R7` in `validate.py` and `board.py`.

### 4.7 Film Shots, Storyboard Generation, Scene Manifests, Continuity & Bounded Timeline Engine

* **Files & Agents**: `.claude/agents/edit-planner.md`, `.claude/agents/shot-continuity-writer.md`, `.claude/skills/shot-visuals/SKILL.md`, `explainer_engine/scripting/film_shots.py`, `explainer_engine/scripting/continuity.py`, `explainer_engine/scripting/shot_prompt_lint.py`, `explainer_engine/production/staging.py`, `explainer_engine/schemas/film_shots.schema.json`, `explainer_engine/schemas/continuity_card.schema.json`, `explainer_engine/schemas/scene_set.schema.json`, `explainer_engine/schemas/screenplay_spine.schema.json`.

* **CURRENT**:

  * `film_shots.py` validates `film_shots/1` and `film_shots/2` cards (`KP-15..KP-43`), composes keyframe/nextpose/cut/video prompts (`KP-30`), checks `BP-109` lane shares (`60/30/10 ±5%`), and checks `KP-35` against flat `BP-107` (`11–17 shots/min`, `2.5–4.5s` median shot).

  * `shot_prompt_lint.py` checks `KP-01..KP-25` and `KP-47` (`BP-172` fast-action verbs and no slow modifiers in `HYPED_ZONES`).

  * `continuity.py` validates `continuity_card/1` and derives `continuity_card/2` from `scene_set/1` (`CT-01..CT-16`: 180-degree axis `camera_side`, `MAX_CHAIN=0` fresh keyframe from master + character sheets, size step `>=1` or angle `>=30°`, `vision_questions`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 2 §4.3–§4.4 & Layer 3)**:

  * **254-Shot Grid Is Reference-Only**: The shot count of an episode must emerge organically from the script's clauses and zone pacing bands (`BP-169`), never forced to `254`.

  * **Bounded Timeline Engine (`±18%` + `8k+1` Quantization)**: Shot durations are derived from speech-clause boundaries (`UR-12`) + `1/f` drift within `[-0.18, +0.18]`, clamped to lane/zone limits (`VIDEO` `<=8.0s` target / `<=10.0s` hard, `STILL` `<=5.0s`), projected to exact segment frame totals (`24 fps`), and for `VIDEO` shots mapped to LTX `8k+1` generation frames including `BP-128` handles (`4..12` frames).

  * **Master Room vs. Narrative Segment Decoupling (`BP-112`)**: A narrative segment (`S01..S16`, `30–60s`) can reuse an existing `master_room_id` (`MR01..MR10`) across segments, provided continuous hold in one room without a cutaway/helper shot stays `<=45s` target (`<=90s` hard ceiling, `BP-112`).

  * **`film_shots.py` Zone Awareness (`WP-R7`)**: On `film_shots/2` documents using `mrbeast_animated`, `episode_check` (`KP-35`) must delegate shot-rate and shot-length checks to `scripting/rhythm_lint.py` (`BP-169`) instead of flagging `BP-107` (`11–17 shots/min`), and `shots[]` in `film_shots.schema.json` must accept `rhythm_zone`, `dramatic_change`, and `still_motion_spec`.

* **KEEP**:

  * `film_shots.py` prompt composer (`KP-30`), `continuity.py` (`CT-01..16`, `scene_set/1`, `continuity_card/2`), `shot_prompt_lint.py` (`KP-01..47`), `BP-111` cold-open teaser links (`teaser_of`), `BP-112` same-place cutaway limit, and `BP-113` talk-run limit (`<=4` lines before reaction/insert/cutaway).

* **CHANGE**:

  * Extend `schemas/film_shots.schema.json` with optional top-level `rhythm_profile` and per-shot `rhythm_zone`, `dramatic_change` (`$ref` to `dramatic_still.schema.json`), and `still_motion_tier`.

  * Update `scripting/film_shots.py:episode_check`: when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, run `rhythm_lint.check(doc)` for `KP-35` and zone-aware WPM (`BP-169`) instead of flat `BP-107` (`11–17 shots/min`) and flat `BP-01` (`185 WPM`), and pass `rhythm_zone` into `compose()` so `shot_prompt_lint.py` (`KP-47`) automatically lints hyped-zone video prompts!

  * Add `explainer_engine/edit/bounded_timeline.py` implementing the 6-step Bounded Timeline Engine from Mold v2.1.0 (`§4.4`) as a **shot-duration quantizer on top of the existing timing authorities** (`production/timing.py` and `audio/spine.py` remain the sole word/segment clock authority under `CN-01`; `bounded_timeline.py` reuses `edit/shot_rules.py:pauses_from_words` for `UR-12` clause-pause candidates and `scripting/film_shots.py:frames` for `8k+1` LTX frame math rather than duplicating them).

* **REPLACE**: Replace the v1 naive `±12%` uniform jitter table (which existed only in old Mold v1 docs) with `edit/bounded_timeline.py`.

* **REMOVE**: None.

* **TRADE-OFFS**: Passing `rhythm_zone` from `film_shots.py:compose()` into each composed video shot dict makes `KP-47` (`shot_prompt_lint.py:194`, which checks `if shot.get("rhythm_zone") in HYPED_ZONES`) actually fire during `film_shots check` — currently `film_shots.compose()` omits `rhythm_zone`, so `KP-47` never triggers during `film_shots check`!

* **RECOMMENDATION**: **KEEP** `film_shots.py`, `continuity.py`, and `shot_prompt_lint.py`; **CHANGE** `film_shots.schema.json` and `film_shots.py` to propagate `rhythm_zone` and `dramatic_change` and call `rhythm_lint`, and add `edit/bounded_timeline.py`.

### 4.8 Rhythm, Narration, Audio-First Timing & Sound Director

* **Files & Agents**: `explainer_engine/edit/rhythm_profile.py`, `explainer_engine/scripting/syllables.py`, `explainer_engine/production/timing.py`, `explainer_engine/audio/pause_pad.py`, `explainer_engine/audio/spine.py`, `explainer_engine/audio/layers.py`, `explainer_engine/audio/sound_director.py`.

* **CURRENT**:

  * `syllables.py:seconds(text, pause_after=..., zone=..., wpm=...)` already supports `zone`, looking up `rhythm_profile.zone_wpm(zone)`.

  * `timing.py:75` defaults to `fps = int(doc["episode"].get("fps", 30))` instead of `delivery.fps()` (`24 fps`, `D-85`/`BP-167`) when `episode.fps` is omitted.

  * `pause_pad.py` pads every punctuated gap shorter than `MIN_GAP = 0.26s` to `0.26s`. In `BP-171`, `hyped_min_gap_s` is `0.18s` (and Mold `zones_5` specifies clause pauses of `120–200ms` in `Z1`/`Z5`), because padding every comma in a `193 WPM` hook to `260ms` artificially slows the hook read!

  * `audio/layers.py` checks `AL-02` against flat `BP-49` (`4–20 events/min`), and `audio/sound_director.py` plans room tone (`BP-116`), J/L cuts (`BP-117`), spectral notch (`BP-118`), 3-layer hits (`BP-119`), audio vacuums (`BP-120`), panning (`BP-121`), shot-size perspective EQ (`BP-122`), and beat-grid music (`BP-123`), without reading `BP-169` zone sound density (`sfx_events_per_min_band`) or ensuring a pre-reveal silence vacuum (`BP-120`) lands in `Z5_CLIMAX_660_720S` (`688.5–689.5s`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 2 & Layer 3)**:

  * Audio-first clock at `24 fps` (`D-85`, `BP-167`) everywhere on the animated route.

  * Zone-aware `pause_pad.py`: in `hyped` / `hyped_climax` zones (`Z1`, `Z2`, `Z4`, `Z5`), use `BP-171`'s `hyped_min_gap_s` (`0.18s`) for clause gaps while keeping `0.26s` in `calm_story` (`Z3`) and `calm_docudrama`.

  * Narrator VO (`Odom`) stays on its locked dry studio EQ chain (`ED-01` / `narrator_polish.py`); `BP-122` shot-size perspective EQ (`near`/`mid`/`far`) in `sound_director.py` / `assemble.py` applies **only** to world foley spots and diegetic character dialogue (`DIALOGUE_CU`), never to the narrator stem (which `assemble.py:build_audio_v2` already respects!).

  * `audio/layers.py` (`WP-R10`) checks per-zone `sfx_events_per_min_band` from `BP-169` on zoned scripts.

* **KEEP**:

  * `audio/spine.py` (`audio_spine/2`), `audio/sound_director.py` (`sound_mix_manifest/2`, `SD-01..15`), `audio/duck.py` (`BP-53`), `audio/acoustics.py`, `scripting/syllables.py`.

* **CHANGE**:

  * Update `audio/pause_pad.py` to accept an optional `zone_at_s` callback or `rhythm_profile` so punctuated gaps in hyped zones use `SR.T("BP-171", "hyped_min_gap_s")` (`0.18s`).

  * Update `production/timing.py:75` and `edit/motion_lint.py:128` to default to `delivery.fps()` (`24`) on `/4` (or animated) scripts while preserving `30` when `episode.fps == 30` or on `/1..3` legacy still scripts (`D-92` item 1).

  * Update `audio/layers.py` (`WP-R10`) to fix `silence_is_default` (`is_scene_script`) and check `BP-169` `sfx_events_per_min_band` per zone when `rhythm_profile == "mrbeast_animated"`.

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Using `0.18s` (`BP-171` `hyped_min_gap_s`) in `pause_pad.py` for hyped zones still leaves `2 x EDGE` (`0.10s`) plus `80ms` safety margin for `UR-12` cuts while preventing artificial slow-down of Odom's hook and climax reads.

* **RECOMMENDATION**: **KEEP** `spine.py`, `sound_director.py`, `syllables.py`; **CHANGE** `pause_pad.py`, `timing.py`, `motion_lint.py`, and `layers.py` (`WP-R9`, `WP-R10`).

### 4.9 `VIDEO` / `STILL` / `HELPER` Routing & `DOC_MAP` / `HOST_COMMENTARY` / `DRAMA_BLOCKED_3D` / `DIALOGUE_CU` Execution Paths

* **Files**: `explainer_engine/edit/router.py`, `explainer_engine/core/contracts.py`, `explainer_engine/scripting/film_shots.py`, `explainer_engine/scripting/variant_plan.py`, `explainer_engine/edit/visual_compensator.py`, `explainer_engine/edit/dramatic_still.py`, `explainer_engine/edit/clay_video.py`, `explainer_engine/edit/archetypes.json`, `explainer_engine/maps/laws.py`, `explainer_engine/maps/render.py`, `explainer_engine/schemas/film_shots.schema.json`, `explainer_engine/schemas/shot_route.schema.json`, `explainer_engine/schemas/shot_spec.schema.json`.

* **CURRENT**:

  * **Macro Lanes (`BP-109`, `D-93`)**: `film_shots.py:visual_lane(shot)` maps every shot into one of 3 runtime budget buckets (`60%` `video`, `30%` `still`, `10%` `helper`, `±5%` tolerance):

    * `helper` (`10%`): `lane in {"MAP", "COMPENSATOR", "GRAPHICS"}` or `archetype` in `{1..7, 9..12}`.

    * `still` (`30%`): `tier == "hold"` or `lane == "STILL_HOLD"` or `archetype == 8` (`PARALLAX_25D_TABLEAU`).

    * `video` (`60%`): `lane in {"KEYFRAME_LTX", "DIALOGUE_CU", "ATMOS_BROLL"}` (or `tier in {"light", "full"}`).

  * **Execution Lanes (`film_shots/2` & `edit/router.py`)**:

    * `DOC_MAP`: **Does not exist as an enum string in code** (`0` occurrences in `explainer_engine/`). In the repository, documentary cartography is the `MAP` lane (`Archetypes 1–4` in `edit/archetypes.json`, rendered by `maps/render.py` and checked by `maps/laws.py`).

    * `HOST_COMMENTARY`: **Refused in code** (`core/contracts.py:77` `REFUSED_LANES["HOST_COMMENTARY"]`) per creator decision `D-89` (`2026-10-30`: no permanent hosts). Kept in schema enums solely for historical compatibility.

    * `DRAMA_BLOCKED_3D`: **Refused in code** (`core/contracts.py:78` `REFUSED_LANES["DRAMA_BLOCKED_3D"]`) per `D-75`/`D-77` (card A2 "not now"). However, 2.5D grey clay layout conditioning for LTX-2.5 (`Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render`) **is** implemented in `explainer_engine/edit/clay_video.py` (rendering `1920x1088` `8k+1` clay layout clips from JSON specs) and tested in P12b Stage L2!

    * `DIALOGUE_CU`: **Implemented in `router.py`, `spine.py`, and `sound_director.py`**, routing a keyframe spec (`qwen_image_keyframe/1`) + an audio-conditioned LTX video spec (`ltx_i2v/1` carrying `audio_slice_sha256` from `audio_spine/2.post_hoc_shots`, `D-90`), with retry fallback `FALLBACK_KEYFRAME_LTX` (`qa/retry_router.py:48`).

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 2 §4.2–§4.3)**:

  * Must route `60%` `VIDEO` (`KEYFRAME_LTX`, `DIALOGUE_CU`, `ATMOS_BROLL`), `30%` `STILL` (`STILL_HOLD` with the 3-tier Still Motion Ladder + `Archetype 8` `PARALLAX_25D_TABLEAU`), and `10%` `HELPER` (`MAP` Archetypes 1–4 + `COMPENSATOR` Archetypes 5–7, 9–12).

  * For `STILL_HOLD` shots, `router.py` must preserve and route the shot's Still Motion Ladder tier (`TIER_1` `parallax_25d`; `TIER_2` `qwen_nextpose` 2-keyframe state shift; `TIER_3` `dramatic_still` cutout relocation / plate swap requiring an empty background plate + subject layer) so `assemble.py` (`build_video_v2`) renders the moving still clip rather than a frozen image!

* **KEEP**:

  * `BP-109` 3-bucket macro accounting (`video` / `still` / `helper`) in `film_shots.py` and `variant_plan.py`.

  * Refusal of `HOST_COMMENTARY` (`D-89`) and `DRAMA_BLOCKED_3D` (`D-75`/`D-77`) in `core/contracts.py`.

  * `MAP` (`Archetypes 1–4`) and `COMPENSATOR` (`Archetypes 5–12`) in `edit/visual_compensator.py` and `maps/render.py`.

  * `DIALOGUE_CU` and `KEYFRAME_LTX` routing in `edit/router.py`, plus `edit/clay_video.py` for Layout-IC conditioning if L2 beats L1 in P12b.

* **CHANGE**:

  * Map `DOC_MAP` -> `MAP` as an alias in `scripting/mold_contract.py` (never add a duplicate `DOC_MAP` lane to `shot_spec.schema.json`).

  * Extend `edit/router.py` and `schemas/shot_route.schema.json` so a `STILL_HOLD` route entry can carry `still_motion` (`tier_1_parallax`, `tier_2_nextpose`, or `tier_3_dramatic_still` with `dramatic_change` spec and second keyframe/cutout refs).

  * Flip `variant_plan.py:LANES["DIALOGUE_CU"]["available"]` and `LANES["KEYFRAME_LTX:light/full"]["available"]` **only after** `P12b` dryrun/pod verification (`OR-21`), keeping `test_variant_plan.py` honest.

* **REPLACE**: None.

* **REMOVE**: Do **not** remove `HOST_COMMENTARY` or `DRAMA_BLOCKED_3D` from schema enums (they are intentionally retained and refused by `contracts.REFUSED_LANES` so any accidental use produces a clear `CN-11` refusal).

* **TRADE-OFFS**: Keeping the existing 8 lane enum values in `film_shots.schema.json` while adding `still_motion` metadata to `STILL_HOLD` routes avoids breaking `shot_route/1` or `shot_spec/1` contracts while enabling all 3 tiers of the Mold's Still Motion Ladder.

* **RECOMMENDATION**: **KEEP** current router and lane refusals; **CHANGE** `STILL_HOLD` routing in `edit/router.py` and `dramatic_still.py` to support the 3-Tier Still Motion Ladder.

### 4.10 Visual Generation, Animation, Assembly, QA, Delivery & Shorts

* **Files & Agents**: `.claude/agents/orchestrator.md`, `.claude/agents/shorts-writer.md`, `.claude/skills/animation-principles/SKILL.md`, `.claude/skills/editing-style/SKILL.md`, `.claude/skills/video-editing-architect/SKILL.md`, `.claude/skills/shorts-for-video/SKILL.md`, `explainer_engine/training/pods/p12/p12b.py`, `p12c_ltx.py`, `p12b.json`, `explainer_engine/training/video_qa.py`, `explainer_engine/production/assemble.py`, `explainer_engine/finish/upscale.py`, `explainer_engine/qa/engagement.py`, `explainer_engine/qa/scorecard.py`, `explainer_engine/qa/targets.py`, `explainer_engine/qa/retry_router.py`, `explainer_engine/qa/review_bundle.py`, `explainer_engine/production/shorts.py`, `explainer_engine/production/clip_shorts.py`, `explainer_engine/publish/plan.py`.

* **CURRENT**:

  * **Visual Generation (`P12`)**: `p12b.py` and `p12c_ltx.py` run Qwen-Image-2.1 (`2560x1408` keyframes with `xworld_v2` LoRA) and LTX-2.5 22B (`1920x1088 @ 24 fps`, `8k+1` frames, testing plain i2v `L1`, Layout-To-Render IC-LoRA `L2` via `clay_video.py`, and audio-driven `L3`). `video_qa.py` checks `LT-50..62`, `CLIP-01..12`, and `LT-80` (`check_fast_action_rhythm`, `BP-172`).

  * **2K Upscale (`finish/upscale.py`)**: Crops `1920x1088` -> `1920x1080` and Lanczos-scales to `2560x1440 @ 24 fps`, but is **not yet called** by `assemble.py:build_video_v2` or `production/__main__.py` (`--size` in `__main__.py:148` still defaults to `"1920x1080"`!).

  * **Assembly (`production/assemble.py`)**: `build_video_v2` reads `edit_and_grade_manifest/1`, trims `BP-128` handles, applies `BP-129` whip blurs and `BP-130` Reinhard LAB colour-transfer clamping, and exports OTIO (`export_otio`). However, `build_video_v2` currently expects every shot in `shots_dir` to already be an `.mp4` clip at the delivery size — it does not yet invoke `dramatic_still.render_dramatic_still` / `parallax` to pre-render `STILL_HOLD` shots or `visual_compensator` to pre-render `MAP`/`COMPENSATOR` shots into `shots_dir` (`WP-5a`).

  * **QA (`engagement.py`, `scorecard.py`, `targets.py`)**: `engagement.py:26` and `scorecard.py:31` still evaluate heard WPM against flat `BP-01` (`170 WPM`, accepted `155–185`) instead of `BP-169` zone-weighted pace on `/4` scripts (`WP-R10`).

  * **Shorts (`production/shorts.py`, `clip_shorts.py`, `validate.py:PV-34`)**: `BP-167` sets `shorts: 5` (`1440x2560 @ 24 fps`), whereas `shorts-writer.md` still says "up to 10 YouTube Shorts" and `validate.py:546` (`PV-34`) requires at least 3 Shorts in each of the two `BP-12` length bands (`>= 6` Shorts total) when `len(shorts) >= 6`.

* **MASTER MOLD REQUIREMENT (v2.1.0 Layer 2 & Layer 3)**:

  * **4-Stage Resolution Pipeline**: `2560x1408` Qwen keyframes → `1920x1088` (`8k+1`) LTX-2.5 source clips → `2560x1440 @ 24 fps` delivery master (`finish/upscale.py` + `assemble.build_video_v2`) → `1440x2560 @ 24 fps` (`5` Shorts per `BP-167`).

  * **Three-Lane Assembly (`WP-5a`)**: `VIDEO` clips (upscaled via `finish/upscale.py`), `STILL` clips (rendered at `2560x1440 @ 24 fps` via `dramatic_still.py` / `parallax.py`), and `HELPER` clips (rendered at `2560x1440 @ 24 fps` via `visual_compensator.py`) must all materialize as frame-accurate `2560x1440 @ 24 fps` `.mp4` segments for `build_video_v2`.

  * **Zone-Aware QA (`WP-R10`)**: `engagement.py` and `scorecard.py` must evaluate `/4` (`mrbeast_animated`) episodes against `BP-169` zone WPM bands and `rhythm_lint.py`.

* **KEEP**:

  * `finish/upscale.py`, `assemble.py` (`build_audio_v2`, `build_video_v2`, `export_otio`), `qa/retry_router.py`, `qa/keyframe_gate.py`, `training/video_qa.py`, `production/shorts.py`, `production/clip_shorts.py`, `publish/plan.py`.

* **CHANGE**:

  * Add a lane-materialization step (`production/assemble.py:materialize_lane_clips`) that renders `STILL_HOLD` (Tier 1/2/3) and `MAP`/`COMPENSATOR` items to `2560x1440 @ 24 fps` `.mp4` clips and runs `finish/upscale.py` on `1920x1088` `VIDEO` clips before `build_video_v2` stitches the master (`WP-5a`).

  * Update `production/__main__.py` default `--size` on animated/v2 runs to read `core/delivery.size()` (`2560x1440`).

  * Update `qa/engagement.py` and `qa/scorecard.py` (`WP-R10`) to read `rhythm_profile.zone_wpm` / `BP-169` on zoned scripts.

  * Update `.claude/agents/shorts-writer.md` and `validate.py:PV-34` to align with `BP-167` (`5` Shorts default: e.g., at least `2` per length band when `len(shorts) == 5`).

* **REPLACE**: None.

* **REMOVE**: None.

* **TRADE-OFFS**: Materializing `STILL` and `HELPER` shots into `shots/<shot_id>.mp4` at `2560x1440 @ 24 fps` alongside upscaled `VIDEO` clips allows `assemble.build_video_v2` (`BP-128` handles, `BP-129` whip transitions, `BP-130` LAB boundary grading, and `export_otio`) to assemble all three lanes through **one unified, already-tested v2 video assembler** without rewriting `build_video_v2`!

* **RECOMMENDATION**: **KEEP** `build_video_v2`, `upscale.py`, `video_qa.py`, `shorts.py`; **CHANGE** lane clip materialization (`WP-5a`) and wire `WP-R10` into `engagement.py` and `scorecard.py`.

## 5. Agent-by-Agent & Skill-by-Skill Impact Matrix

### 5.1 All 16 Repository Agent Stage Pages (`.claude/agents/*.md`)

| \# | Agent File | Model / Effort (`model_routing.json`) | Current Role (`5013a55a`) | Master Mold v2.1.0 Impact & Decision (`KEEP` / `CHANGE`) | Exact Required Adaptation | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| 1 | `.claude/agents/orchestrator.md` | `opus` / `high` | Runs full episode phase-by-phase (Phases 0–7) for both still (`D-43`) and animated (`D-77`/`D-85`) routes. | **CHANGE** | Add `production_script/4` (`mrbeast_animated`) + `mold_contract.py` check at Phase 2; wire `rhythm_lint` and `hype_read` before Approval #1; wire `finish/upscale.py` and 3-lane clip materialization (`WP-5a`) before `build_video_v2` in Phase 6. | 
| 2 | `.claude/agents/episode-standards-director.md` | `sonnet` / `high` | Builds and stamps `episode_rules.json` at `provisional`, `final`, `script_lock`, `paid_assets`, `final_qa`. | **KEEP** (no change needed) | Already format-agnostic; `standards/rulebook.py` works identically with `/4` scripts once `script_approval.py` uses `is_scene_script`. | 
| 3 | `.claude/agents/story-architect.md` | `sonnet` / `high` (`fable` if enabled) | Stage 1 (+ Stage 1b variants): writes `drama`, `cast`, `periods`, `segments[]` skeleton on Template A–D ("15-minute historical docudrama"). | **CHANGE** | Replace `15-minute` with `12-minute (720s, BP-167)`; require `schema: "production_script/4"`, `episode.rhythm_profile: "mrbeast_animated"`, `segments[].rhythm_zone` (`BP-169`), and map Template D's 16 segments to the 12 Anchor Beats (`AB01..AB12`, including `S06` 180s spike and `S09` 360s reversal). | 
| 4 | `.claude/agents/scene-writer.md` | `sonnet` / `high` (`fable` if enabled) | Stage 2: writes `segments[].lines` (`text`, `speaker`, `claims`, `to`, `intent`) at flat `BP-01` (`170 WPM`). | **CHANGE** | Budget each segment's words using its `rhythm_zone` heard WPM (`BP-169`: `193 / 176 / 166 / 185 / 160`), enforce Two-Phase Hook (`AB01` `0–12s` + `AB02` `12–36s`), enforce intra-zone sentence-length modulation (`BP-169` `median_words_max`), and ban game-show filler phrases. | 
| 5 | `.claude/agents/beat-writer.md` | `sonnet` / `high` | Stage 2b: writes `lines[].visual_beats` and opt-in `cue`s (`VB-01..12` on `/3`). | **CHANGE** | Update `/3` references to `/3` and `/4`; replace `BP-40` still-hold reference on zoned animated scripts with `BP-169` (`still_max_s`) and `BP-170` (`dramatic_still`). | 
| 6 | `.claude/agents/performance-director.md` | `sonnet` / `high` | Stage 3: writes `tags`, `emphasis`, `tone`, `emotion`, `pause_after` on finished lines. | **CHANGE** | Add `BP-169` / `BP-171` zone tag palettes (`audio/hype_read.py:allowed_tags`), `1–2` stressed ALL-CAPS words per sentence in hyped zones (`HR-02`), max `1` tag per clause (`HR-03`), and run `hype_read.check_prosody_plan` alongside `narration_lint`. | 
| 7 | `.claude/agents/edit-planner.md` | `sonnet` / `high` | Stage 4 (+ Step 4b Sound): plans `shots`, `audio`, `music`, `graphics`, `film_shots.json`, and `sound_mix_manifest.json`. | **CHANGE** | Update to `/4` and `film_shots/2`: require `rhythm_zone` on shots, 3-Tier Still Motion Ladder (`parallax_25d`, `qwen_nextpose`, `dramatic_change` per `BP-170`), `KP-47` fast-action verbs in hyped zones (`BP-172`), Bounded Timeline Engine (`edit/bounded_timeline.py`), `scripting/rhythm_lint.py` (`0 FAIL`), and `BP-120` climax silence vacuum in `S15`. | 
| 8 | `.claude/agents/voice-caster.md` | `sonnet` / `high` | Stage 5: casts narrator (`channel_voices.json`) and speaking characters (`audio/casting.py`, `voice_audition.py`, `D-90`). | **CHANGE** | Note Odom (`CcSJ2r3qw0XU9gJpEPyk`) + `audio/narrator_polish.py` as the channel narrator standard, and wire `audio/spine.py:bind_character_takes` for `D-90` character takes before `DIALOGUE_CU` routing. | 
| 9 | `.claude/agents/shorts-writer.md` | `sonnet` / `high` | Stage 6: writes `shorts` block ("up to 10 YouTube Shorts") at `170 WPM`. | **CHANGE** | Align default Shorts count with `BP-167` (`5` Shorts at `1440x2560 @ 24 fps`, `>=2` per `BP-12` length band, 5 distinct styles from catalog). | 
| 10 | `.claude/agents/script-critic.md` | `opus` / `high` (spawned read-only) | Stage 7: evaluates full script, writes `editorial_review.json` (`editorial_review/2`) and Georgian `story_page.md` (`BP-89`). | **CHANGE** | Update `/3` references to `/3` and `/4`; add inspection of `rhythm_lint` output, `AB01..AB12` anchor beat fulfillment (especially `180s` and `360s` re-hooks and `BP-111` climax payoff), and intra-zone pace variation (`BP-169`). | 
| 11 | `.claude/agents/shot-continuity-writer.md` | `sonnet` / `high` | Writes `continuity_card/1` per scene (`CT-01..14`) and runs `scripting/continuity.py`. | **CHANGE** | Add note on `master_room_id` reuse across segments (`BP-112` `<=45s` target / `<=90s` hard ceiling before cutaway) and `empty_bg_plate` flag for Tier 2/3 `STILL_HOLD` shots. | 
| 12 | `.claude/agents/lora-coordinator.md` | `opus` / `high` | Coordinates `xworld_v2` style LoRA training on Qwen-Image-2.1 (`D-80`). | **KEEP** (no change needed) | LoRA training protocol (`G1–G6`) is independent of episode rhythm mold. | 
| 13 | `.claude/agents/lora-dataset-auditor.md` | `sonnet` / `medium` | Audits style LoRA training dataset (`LT-01..08`). | **KEEP** (no change needed) | Independent of episode rhythm mold. | 
| 14 | `.claude/agents/lora-run-operator.md` | `sonnet` / `high` | Launches/stops LoRA training pods via `cloud/runpod.py`. | **KEEP** (no change needed) | Independent of episode rhythm mold. | 
| 15 | `.claude/agents/lora-checkpoint-judge.md` | `opus` / `high` (spawned read-only) | Scores LoRA checkpoints (`LT-20..43`). | **KEEP** (no change needed) | Independent of episode rhythm mold. | 
| 16 | `.claude/agents/paid-run-watchdog.md` | `haiku` / `low` (separate thread, `OR-36`) | Read-only watchdog thread monitoring pod/API spend and progress every 5 min. | **KEEP** (no change needed) | Mandatory safety control (`OR-36`, PR #118); preserve untouched. | 

### 5.2 All 16 Repository Skills (`.claude/skills/*/SKILL.md`)

| \# | Skill File | Current Role (`5013a55a`) | Master Mold v2.1.0 Impact & Decision (`KEEP` / `CHANGE`) | Exact Required Adaptation | 
| ----- | ----- | ----- | ----- | ----- | 
| 1 | `.claude/skills/story-engine/SKILL.md` | Writers' room 7-stage table and gates (`production_script/3`). | **CHANGE** | Update schema to `production_script/4` for new episodes; add `rhythm_lint` and `hype_read` to the Stage 3/4 gate column; reference `12-minute (720s)` target (`BP-167`) and `AB01..AB12`. | 
| 2 | `.claude/skills/narration-script/SKILL.md` | Spoken narration craft rules (`N-01..N-17`, `BP-01` `170 WPM`, `BP-06`). | **CHANGE** | Add section on `BP-169` 5-zone pace modulation (`193 / 176 / 166 / 185 / 160` heard WPM), intra-zone sentence-length contrast, Two-Phase Hook (`0–12s` + `12–36s`), and game-show cliché ban. | 
| 3 | `.claude/skills/elevenlabs-voice/SKILL.md` | ElevenLabs v4 voice guide; still names `NOpBlnGInO9m6vDvFkFC` (`Grandpa Spuds Oxley`). | **CHANGE** | Update active channel narrator to `CcSJ2r3qw0XU9gJpEPyk` (`Odom`) + `audio/narrator_polish.py`; document `BP-171` / `audio/hype_read.py` per-zone tag rules and `<=800` char / `<=90s` chunk resets (`HR-04`). | 
| 4 | `.claude/skills/dialogue-scenes/SKILL.md` | Scene headers and dialogue craft (`SC-01..10`, `DW-01..13` on `/3`). | **CHANGE** | Update `/3` to `/3` and `/4`; document `D-90` pre-rendered character ElevenLabs takes conditioning `DIALOGUE_CU` clips and `BP-113` `<=4` lines before reaction/cutaway. | 
| 5 | `.claude/skills/visual-beats/SKILL.md` | Visual beats and cues (`VB-00..12` on `/3`, `BP-40`). | **CHANGE** | Update `/3` to `/3` and `/4`; note that `BP-169`/`BP-170` govern still-hold limits on zoned episodes. | 
| 6 | `.claude/skills/shot-visuals/SKILL.md` | Shot planning for still (`D-43`) vs animated (`D-77`, `D-80`) episodes. | **CHANGE** | Add the 3-Tier Still Motion Ladder (`TIER_1` `parallax_25d`, `TIER_2` `qwen_nextpose`, `TIER_3` `dramatic_still` `BP-170`) and `BP-109` (`60/30/10 ±5%`) lane rules. | 
| 7 | `.claude/skills/animation-principles/SKILL.md` | 12 principles of animation, holds, lip-sync (`BP-107`, `BP-109`). | **CHANGE** | Reference `BP-169` zone cut rates alongside `BP-107` and `BP-172` (`KP-47`, `LT-80` `hyped_hold_share_max = 0.35`). | 
| 8 | `.claude/skills/editing-style/SKILL.md` | Cuts, dissolves, ducking, room tone (`ED-01..14`, `BP-40`). | **CHANGE** | Add `BP-169` 5-zone editing curve, `BP-120` climax audio vacuum (`688.5–689.5s`), and `finish/upscale.py` (`1920x1088` -> `2560x1440 @ 24 fps`). | 
| 9 | `.claude/skills/video-editing-architect/SKILL.md` | General editing reference & QA checklist (`BP-40`). | **CHANGE** | Add pointer to `BP-169..172` and `edit/bounded_timeline.py` for `mrbeast_animated` episodes. | 
| 10 | `.claude/skills/shorts-for-video/SKILL.md` | Shorts writing and 9:16 cropping (`BP-11`, `BP-12`, `BP-44..46`). | **CHANGE** | Note `BP-167` (`5` Shorts at `1440x2560 @ 24 fps`) and `production/clip_shorts.py` loop-cut option. | 
| 11 | `.claude/skills/cartography/SKILL.md` | Map design rules (`BP-124`, `BP-150`, `maps/`). | **KEEP** (no change needed) | Fully aligned with `HELPER` lane (`10%` default, `<=25%` Profile B cap). | 
| 12 | `.claude/skills/science-grounding/SKILL.md` | Research & claim map rules (`established`, `model`, `reasoned`, `guess`). | **KEEP** (no change needed) | Fully aligned with Mold Layer 1 §3.1/§3.3. | 
| 13 | `.claude/skills/crossover-episode/SKILL.md` | Fan research and casual/fan balance (`fan_brief.py`). | **KEEP** (no change needed) | Fully aligned with Mold Layer 1. | 
| 14 | `.claude/skills/time-jump-episode/SKILL.md` | Multi-period time-jump structure (`SR-01..08`). | **KEEP** (no change needed) | Compatible with Profile C / Template D. | 
| 15 | `.claude/skills/animated-universe/SKILL.md` | Character silhouette and design rules (`D-77`/`D-80`). | **KEEP** (no change needed) | Compatible with `xworld_v2` style LoRA. | 
| 16 | `.claude/skills/lora-training/SKILL.md` | LoRA training loop (`G1–G6`, `D-80`). | **KEEP** (no change needed) | Independent of episode rhythm mold. | 

## 6. File-by-File Impact Matrix (All 86 Candidates from `FILES_AFFECTED.md` + 23 Newly Identified Repository Files)

Every file from `FILES_AFFECTED.md` (`#1..#86`) plus the `23` additional repository files identified during our full-context inspection of `5013a55aca5a17a3734150f61a5eb172abcbe3b8` is accounted for below.

### 6.1 Complete File-by-File Disposition Table (`109` Repository Paths)

| \# | Repository Path | Area | Status at `5013a55a` (PR #119) | Action Needed Now | Exact Implementation Specification | Pinning Test(s) | 
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | 
| 1 | `config/channel_voices.json` | Voice | **DONE in PR #119** (`Odom` `CcSJ2r3qw0XU9gJpEPyk` active; `Oxley` retired; `baseline: null`). | **KEEP** (Later: update `baseline` after OR-19 sample) | Protected config (`60`). Do not edit until creator approves first Odom sample read (`OR-19`), then run `python -m explainer_engine.audio.voice_audition baseline`. | `tests/unit/test_voice_audition.py`, `test_narrator_polish.py` | 
| 2 | `explainer_engine/audio/voice_audition.py` | Voice | Unchanged in PR #119 (`hype_score` was placed in `audio/hype_read.py`). | **KEEP** | `voice_audition.py` measures raw acoustic features (`f0_iqr_st`, `speaking_wps`, `dynamic_range_db`); `hype_read.py` scores them against `BP-171`. No change needed in `voice_audition.py`. | `tests/unit/test_voice_audition.py` | 
| 3 | `explainer_engine/audio/casting.py` | Voice | Unchanged (`BP-138` margins, trait search). | **KEEP** | Used for character voices (`D-90`); narrator is fixed to Odom (`VC-08`). Keep as-is. | `tests/unit/test_casting.py` | 
| 4 | `explainer_engine/audio/voice_check.py` | Voice | Unchanged (`EL-13` returns `REVIEW` while Odom `baseline` is `null`). | **KEEP** | Works with `channel_voices.json` and `narrator_polish.py` (which runs after `voice_check`). | `tests/unit/test_voice_check.py` | 
| 5 | `explainer_engine/scripting/syllables.py` | Narration | **DONE in PR #119** (`seconds(..., zone=...)` added). | **CHANGE** (minor) | Add `seconds_across_zones(text, t_start_s, total_s, profile_name)` helper so multi-sentence segments crossing a zone boundary scale accurately. | `tests/unit/test_syllables.py` | 
| 6 | `explainer_engine/scripting/narration_lint.py` | Narration | Unchanged in PR #119 (still checks flat `BP-06` `12`-word median). | **CHANGE** | In `doc_findings(doc)`, when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, check per-zone `median_words_max` (`8/9/11/9/7` from `BP-169`), check intra-zone sentence-length variance, and call `hype_read.check_prosody_plan`. | `tests/unit/test_narration_lint.py`, `test_rhythm_end_to_end.py` | 
| 7 | `explainer_engine/scripting/register_lint.py` | Narration | Unchanged (`BP-140` FAIL tier, `BP-114` REVIEW tier). | **CHANGE** | Update docstring/comment for `/3` and `/4`; add banned game-show filler phrases from Mold Layer 1 (`§3.3`) as `RG-05` (`REVIEW`). | `tests/unit/test_register_lint.py` | 
| 8 | `explainer_engine/scripting/speech.py` | Narration | **BUG at line 60**: `if doc.get("schema") == "production_script/3"`. | **CHANGE** (P0 fix) | Replace `doc.get("schema") == "production_script/3"` with `is_scene_script(doc)`. | `tests/unit/test_production_script_schema.py` | 
| 9 | `explainer_engine/production/timing.py` | Narration / Timing | **BUG at line 75**: `fps = int(doc["episode"].get("fps", 30))`. | **CHANGE** | Default `fps` to `delivery.fps()` (`24`) when `is_zoned_rhythm_script(doc)` (preserving `30` when `episode.fps` is explicitly `30` or `schema_version <= 3`). Propagate segment `rhythm_zone` and shot `dramatic_change` / `still_motion_tier` into `timed["shots"]`. | `tests/unit/test_timing.py`, `test_rhythm_end_to_end.py` | 
| 10 | `explainer_engine/audio/pause_pad.py` | Narration | Unchanged (`MIN_GAP = 0.26s` everywhere). | **CHANGE** | Add optional `zone_for_time` lookup so gaps in hyped zones (`hook_0_30s`, `early_30_90s`, `late_third_480_660s`, `climax_660_720s`) use `SR.T("BP-171", "hyped_min_gap_s")` (`0.18s`) instead of `0.26s`. | `tests/unit/test_pause_pad.py` | 
| 11 | `.claude/skills/narration-script/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Add `BP-169` 5-zone WPM table, Two-Phase Hook (`0–12s` + `12–36s`), intra-zone sentence-length modulation, and game-show phrase ban. | `explainer_engine/docs_lint.py` | 
| 12 | `.claude/skills/elevenlabs-voice/SKILL.md` | Skill | Unchanged in PR #119 (still names `Oxley`). | **CHANGE** | Replace active narrator `Oxley` with `Odom` (`CcSJ2r3qw0XU9gJpEPyk`) + `audio/narrator_polish.py`; document `BP-171` (`audio/hype_read.py`). | `explainer_engine/docs_lint.py` | 
| 13 | `.claude/agents/scene-writer.md` | Agent | Unchanged in PR #119 (still budgets at `170 WPM`). | **CHANGE** | Budget segment words by `rhythm_zone` (`BP-169`), enforce Two-Phase Hook and intra-zone sentence-length contrast. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 14 | `.claude/agents/performance-director.md` | Agent | Unchanged in PR #119. | **CHANGE** | Wire `BP-169` / `BP-171` zone `tts_tags` (`hype_read.py`), `1–2` ALL-CAPS words per sentence (`HR-02`), and `hype_read.check_prosody_plan`. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 15 | `.claude/agents/voice-caster.md` | Agent | Unchanged in PR #119. | **CHANGE** | Reference `Odom` + `narrator_polish.py` and `audio/spine.py:bind_character_takes` for `D-90`. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 16 | `.claude/agents/shorts-writer.md` | Agent | Unchanged in PR #119 ("up to 10 Shorts"). | **CHANGE** | Align default count with `BP-167` (`5` Shorts at `1440x2560 @ 24 fps`). | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 17 | `docs/NARRATION_AND_LANGUAGE_GUIDE.md` | Docs | Unchanged in PR #119. | **CHANGE** | Add pointer to `BP-169` (`mrbeast_animated` 5-zone profile) alongside `BP-01` (`calm_docudrama`). | `explainer_engine/docs_lint.py` | 
| 18 | `docs/STORY_ENGINE.md` | Docs | Unchanged in PR #119. | **CHANGE** | Document `production_script/4`, `BP-169..172`, 12-minute Template D mapping (`AB01..AB12`), and 3-Tier Still Motion Ladder. | `explainer_engine/docs_lint.py` | 
| 19 | `.claude/skills/story-engine/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Update stage table to `production_script/4`, add `rhythm_lint` and `hype_read` gates. | `explainer_engine/docs_lint.py` | 
| 20 | `.claude/agents/story-architect.md` | Agent | Unchanged in PR #119 ("15-minute historical docudrama"). | **CHANGE** | Change `15-minute` to `12-minute (720s, BP-167)`, require `production_script/4` with `rhythm_zone` and `AB01..AB12` anchors. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 21 | `.claude/agents/beat-writer.md` | Agent | Unchanged in PR #119. | **CHANGE** | Update `/3` to `/3` and `/4`; reference `BP-169` `still_max_s` and `BP-170`. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 22 | `.claude/agents/edit-planner.md` | Agent | Unchanged in PR #119. | **CHANGE** | Add `rhythm_lint`, `dramatic_still` (`BP-170`), `bounded_timeline.py`, `KP-47` (`BP-172`), and `BP-120` climax vacuum. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 23 | `.claude/agents/script-critic.md` | Agent | Unchanged in PR #119. | **CHANGE** | Add `rhythm_lint` review, `AB01..AB12` anchor verification, and intra-zone pace variation check. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 24 | `.claude/agents/shot-continuity-writer.md` | Agent | Unchanged in PR #119. | **CHANGE** | Document `master_room_id` reuse (`BP-112` `<=45s` target / `<=90s` cap) and `empty_bg_plate` for Tier 2/3 stills. | `tests/unit/test_agent_roles.py`, `docs_lint.py` | 
| 25 | `explainer_engine/scripting/story_lint.py` | Story | **BUG at line 75**: `doc.get("schema") == "production_script/3"`; flat `WORDS_PER_S` (`170 WPM`). | **CHANGE** (P0 fix + zone timing) | Use `is_scene_script(doc)` for `ST-00`; use zone-aware `rhythm_profile.words_to_seconds` for `line_starts` and `ST-13` on `/4` scripts; add optional `AB01..AB12` anchor beat check (`ST-25`). | `tests/unit/test_story_engine.py` | 
| 26 | `explainer_engine/scripting/stage_guard.py` | Story | **DONE in PR #119** (`rhythm_zone` added to `SEG_STORY`). | **CHANGE** (minor) | Add `anchor_beat_id` and `rehook_spike` to `SEG_STORY` so `architect` owns them. | `tests/unit/test_story_engine.py` | 
| 27 | `explainer_engine/scripting/scenario.py` | Story | Unchanged (`LEGACY = "production_script/1"`, binds `/2`+). | **KEEP** | Already binds on `/4` (`doc.get("schema") != "production_script/1"` -> `FAIL`). | `tests/unit/test_scenario.py` | 
| 28 | `explainer_engine/scripting/variant_plan.py` | Story | **PARTIAL in PR #119** (`BP-109` `±5%` and `BP-141` `0.45` updated, but `VP-18` still checks `BP-107` `11–17 shots/min`). | **CHANGE** (`WP-R7`) | In `segments_from_script`, pass `zone=seg.get("rhythm_zone")` to `syllables.seconds`. In `checks` (`VP-18`), when `rhythm_profile != "calm_docudrama"`, check shot rate against `BP-169` instead of `BP-107`. | `tests/unit/test_variant_plan.py` | 
| 29 | `explainer_engine/schemas/production_script.schema.json` | Contract | **DONE in PR #119** (`production_script/4`, `rhythm_profile`, `rhythm_zone`, `dramatic_change`). | **CHANGE** (minor extension) | Add optional `segments[].anchor_beat_id` (`AB01..AB12`), `segments[].rehook_spike`, and `shots[].still_motion_tier` (`TIER_1..3`). | `tests/unit/test_production_script_schema.py` | 
| 30 | `explainer_engine/scripting/film_shots.py` | Shots | **PARTIAL in PR #119** (`BP-109` `60/30/10 ±5%` wired, but `episode_check` `KP-35` still checks `BP-107` `11–17 shots/min` and `compose()` drops `rhythm_zone`). | **CHANGE** (`WP-R7`) | Propagate `rhythm_zone` and `dramatic_change` in `compose()`; in `episode_check`, when `rhythm_profile != "calm_docudrama"`, delegate `KP-35` to `rhythm_lint.check(doc)` and check zone WPM against `BP-169`. | `tests/unit/test_film_shots.py` | 
| 31 | `explainer_engine/edit/shot_rules.py` | Shots | Unchanged (`BP-85` UR-11 shot lengths `A: 5–7s`, `B: 3.5–5s`, `C: 2.5–4s`). | **CHANGE** (`WP-R7`) | Keep `cut_ok`, `solve_cuts`, and `UR-12` pause-at-cut alignment; in `check_shots`, when `rhythm_profile != "calm_docudrama"`, defer shot-duration band checks (`UR-02`, `UR-11`) to `rhythm_lint.py`. | `tests/unit/test_shot_rules.py` | 
| 32 | `explainer_engine/edit/motion_lint.py` | Shots | Unchanged (`fps=30` default at line 128; `MO-01` checks `BP-40`). | **CHANGE** (`WP-R7`) | Default `fps` to `delivery.fps()` (`24`) when not specified on `/4`; in `check(timed)`, when `rhythm_profile != "calm_docudrama"`, check `MO-01` max gap against the zone's `still_max_s` (`BP-169`) instead of `BP-40`. | `tests/unit/test_motion_lint.py` | 
| 33 | `explainer_engine/edit/router.py` | Shots | Unchanged in PR #119 (`film_shots/2` -> `shot_spec/1` + `shot_route/1`). | **CHANGE** | Preserve `still_motion_tier` and `dramatic_change` on `STILL_HOLD` route entries in `shots/route.json` so `assemble.py` renders Tier 1/2/3 moving stills. | `tests/unit/test_shot_router.py` | 
| 34 | `explainer_engine/edit/visual_compensator.py` | Shots | Unchanged (`12` archetypes, `BP-149`, `BP-150`, `BP-127`). | **KEEP** | Fully compatible with `10%` `HELPER` lane (`MAP` + `COMPENSATOR`) and `Archetype 8` (`PARALLAX_25D_TABLEAU`). | `tests/unit/test_compensator.py` | 
| 35 | `explainer_engine/edit/archetypes.json` | Shots | Unchanged (`12` archetypes). | **KEEP** | Already maps Archetypes 1–4 to `MAP` and 5–12 to `COMPENSATOR`. | `tests/unit/test_compensator.py` | 
| 36 | `explainer_engine/edit/tableau.py` | Stills | Unchanged (`Archetypes 6, 8, 9` renderer). | **KEEP** | Renders `PARALLAX_25D_TABLEAU` (`Archetype 8`). | `tests/unit/test_compensator.py` | 
| 37 | `explainer_engine/edit/universe.py` | Stills | Unchanged. | **KEEP** | Used by legacy still look. | `tests/unit/test_episode_look.py` | 
| 38 | `explainer_engine/edit/board.py` | Stills | Unchanged (`RHYTHM-1` `BP-40` `<=10 pics/min`, `RHYTHM-2` `BP-84` `>=2.0s`, `RHYTHM-3` `BP-40`). | **CHANGE** (`WP-R7`) | In `check(board, timed)`, when `rhythm_profile != "calm_docudrama"`, skip `RHYTHM-1..3` (which are replaced by `rhythm_lint.py` `RL-01..04`) while keeping `STATE-1`, `HERO-1`, `BUBBLE-*`, and `BP-41`. | `tests/unit/test_board.py` | 
| 39 | `explainer_engine/edit/hud.py` | Helper | Unchanged (`Archetypes 5, 7, 10, 11, 12` renderer). | **KEEP** | Renders deterministic HUD/chart helpers for the `10%` `HELPER` lane. | `tests/unit/test_compensator.py` | 
| 40 | `explainer_engine/edit/prompt_v2.py` | Prompts | Unchanged (still-picture prompt composer). | **KEEP** | Used by D-43 still-picture route; animated route uses `film_shots.py`. | `tests/unit/test_prompt_v2.py` | 
| 41 | `explainer_engine/production/beats.py` | Beats | **BUG at line 107**: `scene_rules(doc)` checks `== "production_script/3"`. | **CHANGE** (P0 fix + `WP-R9`) | Change `scene_rules(doc)` to `is_scene_script(doc)`; on `mrbeast_animated`, bound `VB-01` narration beat gap by `BP-169` zone `still_max_s`. | `tests/unit/test_beats.py` | 
| 42 | `explainer_engine/production/fill_holds.py` | Stills | Unchanged (uses `BP-40` `20s` body gap). | **CHANGE** (`WP-R9`) | On `mrbeast_animated`, use `rhythm_profile.zone_at_time(t)["still_max_s"]` (`2.5s / 3.5s / 5.0s`) and zone `shot_len_s_band[0]` instead of `BP-40` / `BP-84`. | `tests/unit/test_fill_holds.py` | 
| 43 | `explainer_engine/production/accents.py` | Stills | Unchanged (`punch`, `shake`, `wobble`, `pop_text`, `slam_text`, `flash_in`, `whip_in`). | **KEEP** | Draws minor visual events (`C8.2`) on stills and shots. | `tests/unit/test_accents.py` | 
| 44 | `explainer_engine/production/graphics.py` | Helper | Unchanged (`counter`, `bars`, `comparison` cards). | **KEEP** | Part of `10%` `HELPER` lane (`BP-109`). | `tests/unit/test_graphics.py` | 
| 45 | `explainer_engine/production/parallax.py` | Stills | Unchanged (`3-layer` depth parallax). | **KEEP** | Powers `TIER_1_SHORT_PARALLAX_STILL` (`1.0–2.2s`, `BP-35`). | `tests/unit/test_parallax.py` | 
| 46 | `explainer_engine/production/assemble.py` | Assembly | Unchanged in PR #119 (`build_audio_v2`, `build_video_v2`, `export_otio`). | **CHANGE** (`WP-5a`, `WP-R9`) | Add `materialize_lane_clips` helper that calls `finish/upscale.py` on `1920x1088` `VIDEO` clips, renders `STILL_HOLD` (Tier 1 `parallax`, Tier 2 `nextpose`, Tier 3 `dramatic_still`) and `MAP`/`COMPENSATOR` items to `2560x1440 @ 24 fps` `.mp4` clips, and feeds `build_video_v2`. | `tests/unit/test_assemble_v2.py`, `test_finish_upscale.py` | 
| 47 | `explainer_engine/production/validate.py` | Validation | **BUG at line 89**: `!= "production_script/3"`; `PV-52` checks flat `BP-01` (`170 WPM`); `rhythm_lint` & `hype_read` not called. | **CHANGE** (P0 fix + `WP-R7`, `WP-R9`) | Use `is_scene_script(doc)`; in `estimated_words(doc)`, use zone WPM on `/4`; in `check_script`, run `rhythm_lint.check` and `hype_read.check_prosody_plan` and check `PV-52` against `BP-169` weighted WPM; in `PV-34`, allow `5` Shorts (`BP-167`). | `tests/unit/test_validate.py`, `test_rhythm_end_to_end.py` | 
| 48 | `explainer_engine/production/compile.py` | Compile | Unchanged (`compile_doc`, `compile_spine`). | **CHANGE** (`WP-R9`) | In `write_outputs`, when `rhythm_profile == "mrbeast_animated"`, format `narration_tts.txt` lines through `audio/hype_read.py:format_line_for_tts` so zone default tags are emitted when a hyped-zone line has none. | `tests/unit/test_compile.py`, `test_hype_read.py` | 
| 49 | `explainer_engine/production/staging.py` | Stills | **BUG at line 418**: `== "production_script/3"`. | **CHANGE** (P0 fix) | Replace `doc.get("schema") == "production_script/3"` with `is_scene_script(doc)`. | `tests/unit/test_staging.py` | 
| 50 | `explainer_engine/qa/engagement.py` | QA | Unchanged (uses flat `WPM = 170` from `BP-01`). | **CHANGE** (`WP-R10`) | On `/4` (`mrbeast_animated`) scripts, convert word counts to seconds via `rhythm_profile.words_to_seconds` and check `180s` (`S06`) and `360s` (`S09`) re-engagement hooks (`BP-42`). | `tests/unit/test_engagement.py` | 
| 51 | `explainer_engine/qa/scorecard.py` | QA | Unchanged (`pace_verdict` checks flat `BP-01` `155–185 WPM`). | **CHANGE** (`WP-R10`) | On `/4` (`mrbeast_animated`) episodes, check overall and per-zone heard WPM against `BP-169` (`rhythm_profile.zone_wpm`) and include `rhythm_lint` findings in Check 6. | `tests/unit/test_scorecard.py` | 
| 52 | `explainer_engine/qa/targets.py` | QA | Unchanged (`BP-50` `-14 LUFS`, `-1 dBTP`, `BP-51`, `BP-52`, `BP-59`, `BP-61`). | **KEEP** | Fully aligned with `PRM_LUFS_AND_TRUE_PEAK` (`-14.0 LUFS`, `-1.0 dBTP`). | `tests/unit/test_targets.py` | 
| 53 | `explainer_engine/qa/publish_check.py` | QA | Unchanged (`PC-01..12` title/thumbnail checks). | **KEEP** | Compatible with Mold packaging rules. | `tests/unit/test_publish_check.py` | 
| 54 | `explainer_engine/standards/craft_checklists/animation.json` | QA | **DONE in PR #119** (updated for `D-93` 60/30/10). | **KEEP** | Already updated in PR #119 commit `92e95ae`. | `tests/unit/test_craft.py` | 
| 55 | `docs/EDITING.md` | Docs | Unchanged in PR #119. | **CHANGE** | Add `BP-169` 5-zone editing reference and `finish/upscale.py` 2K delivery note. | `explainer_engine/docs_lint.py` | 
| 56 | `docs/SHOT_PROMPTS.md` | Docs | **DONE in PR #119** (`KP-47` fast-action verbs and `D-93` 60/30/10 added). | **KEEP** | Already updated in PR #119. | `explainer_engine/docs_lint.py` | 
| 57 | `docs/PRODUCTION_RULES.md` | Docs | Unchanged in PR #119. | **KEEP** | Binding governance rules remain in force. | `explainer_engine/docs_lint.py` | 
| 58 | `docs/PRODUCTION_SCRIPT.md` | Docs | Unchanged in PR #119 (still describes `/3` as latest). | **CHANGE** | Document `production_script/4` fields (`episode.rhythm_profile`, `segments[].rhythm_zone`, `segments[].anchor_beat_id`, `shots[].dramatic_change`, `shots[].still_motion_tier`). | `explainer_engine/docs_lint.py` | 
| 59 | `docs/SCRIPT_ENGINE.md` | Docs | **PARTIAL in PR #119** (`D-93` 60/30/10 updated, still says `15-minute`). | **CHANGE** | Update `15-minute` references to `12-minute (720s, BP-167)` and document `BP-169` zone integration in `variant_plan.py`. | `explainer_engine/docs_lint.py` | 
| 60 | `docs/CRAFT_CURRICULUM.md` | Docs | Unchanged in PR #119 (`D-91` recorded). | **KEEP** | Craft curriculum baseline intact. | `explainer_engine/docs_lint.py` | 
| 61 | `.claude/skills/shot-visuals/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Document 3-Tier Still Motion Ladder (`BP-170`) and `BP-109` (`60/30/10 ±5%`). | `explainer_engine/docs_lint.py` | 
| 62 | `.claude/skills/editing-style/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Add `BP-169` 5-zone rhythm and `BP-120` climax vacuum. | `explainer_engine/docs_lint.py` | 
| 63 | `.claude/skills/video-editing-architect/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Add pointer to `BP-169..172` and `edit/bounded_timeline.py`. | `explainer_engine/docs_lint.py` | 
| 64 | `.claude/skills/visual-beats/SKILL.md` | Skill | Unchanged in PR #119. | **CHANGE** | Update `/3` to `/3` and `/4`; reference `BP-169`/`BP-170`. | `explainer_engine/docs_lint.py` | 
| 65 | `.claude/skills/animation-principles/SKILL.md` | Skill | **DONE in PR #119** (`D-93` updated). | **CHANGE** (minor) | Add pointer to `BP-172` (`LT-80` `hyped_hold_share_max = 0.35`). | `explainer_engine/docs_lint.py` | 
| 66 | `explainer_engine/training/pods/p12/p12b.json` | Video Pod | **DONE in PR #119** (`WP-R3` fast-action prompts, 73-frame clip, SHA pins). | **KEEP** (Pending `CD-02` LoRA weight `0.7` vs `1.0`) | Only update `style_lora.strength` if creator locks `0.7` in `CD-02`. | `tests/unit/test_p12b_config.py`, `test_dryrun_placeholders.py` | 
| 67 | `explainer_engine/training/pods/p12/p12c_ltx.py` | Video Pod | **DONE in PR #119** (`WP-R3` 73-frame clip, AV checks, `BP-172`). | **KEEP** | Ready for P12b pod execution once creator approves `OR-23` plan. | `tests/unit/test_p12c_ltx.py` | 
| 68 | `docs/pods/P12_PROMPTS.md` | Docs | **DONE in PR #119** (`WP-R3` fast-action prompts). | **KEEP** | Already updated in PR #119. | `tests/unit/test_p12b_config.py` | 
| 69 | `docs/pods/P12_LTX_FLAGS.md` | Docs | **DONE in PR #119** (`WP-1a`, `WP-1a2`). | **KEEP** | Already updated in PR #119. | `tests/unit/test_p12c_ltx.py` | 
| 70 | `explainer_engine/training/video_qa.py` | Video QA | **DONE in PR #119** (`LT-80` `check_fast_action_rhythm` added for `BP-172`). | **KEEP** | Already enforces `BP-172` (`hyped_hold_share_max = 0.35`, `hyped_frozen_run_frames_max = 12`). | `tests/unit/test_video_qa_clip_rows.py` | 
| 71 | `explainer_engine/scripting/shot_prompt_lint.py` | Video Lint | **DONE in PR #119** (`KP-47` fast-action verb & slow-modifier check added). | **KEEP** | Once `film_shots.py:compose()` propagates `rhythm_zone`, `KP-47` runs automatically on every composed video prompt. | `tests/unit/test_shot_prompt_lint.py` | 
| 72 | `explainer_engine/audio/layers.py` | Audio | **BUG at line 53**: `silence_is_default` checks `== "production_script/3"`; `AL-02` checks flat `BP-49`. | **CHANGE** (P0 fix + `WP-R10`) | Fix `silence_is_default` to `is_scene_script`; on `mrbeast_animated`, check per-zone `sfx_events_per_min_band` from `BP-169`. | `tests/unit/test_audio_layers.py` | 
| 73 | `explainer_engine/audio/cues.py` | Audio | Unchanged (`BP-57`, `BP-64` cue variants). | **KEEP** | Event-bound cues (`VB-08`) work unchanged. | `tests/unit/test_cues.py` | 
| 74 | `explainer_engine/audio/sfx_library.py` | Audio | Unchanged (`BP-162` library-first). | **KEEP** | Library-first SFX lookup (`D-76`, `BP-162`) stays intact. | `tests/unit/test_sfx_library.py` | 
| 75 | `explainer_engine/audio/duck.py` | Audio | Unchanged (`BP-53` sidechain ducking). | **KEEP** | Used by `assemble.py:build_audio_v2`. | `tests/unit/test_duck.py` | 
| 76 | `explainer_engine/audio/sound_director.py` | Audio | Unchanged in PR #119 (`SD-01..15`, `BP-116..123`, `BP-160`). | **CHANGE** (`WP-R10`) | Add zone-aware check ensuring at least one `BP-120` pre-reveal silence vacuum (`0.5–1.0s` at `-65 dBFS`) is planned in `climax_660_720s` (`Z5`) when `rhythm_profile == "mrbeast_animated"`, and check zone SFX density against `BP-169`. | `tests/unit/test_sound_director.py` | 
| 77 | `explainer_engine/audio/spine.py` | Audio | **PARTIAL in PR #119** (`1bfd540` fixed `native_lines` for `DIALOGUE_CU`). | **CHANGE** (`D-90`) | Add `bind_character_takes(spine, takes_map)` so pre-recorded ElevenLabs character takes populate `post_hoc_shots` with `source="clip"` and `clip_sha256` before `edit/router.py` runs. | `tests/unit/test_audio_spine.py` | 
| 78 | `docs/AUDIO_SYSTEM.md` | Docs | Unchanged in PR #119. | **CHANGE** | Document `audio/hype_read.py` (`BP-171`), `audio/narrator_polish.py` (`Odom`), and `D-90` pre-recorded character take binding in `audio_spine/2`. | `explainer_engine/docs_lint.py` | 
| 79 | `docs/COST_AND_TIME_MODEL.md` | Docs | **DONE in PR #119** (`5f04757` added `D-94` rhythm cost table). | **KEEP** (Update after P12b real speed measurements) | Already updated with initial `D-94` cost estimate; replace estimates with measured `config/job_speeds.json` rows after P12b pod. | `explainer_engine/docs_lint.py` | 
| 80 | `explainer_engine/standards/sourced_rules.py` | Rules | Unchanged (`rule()`, `T()`, `level()`). | **KEEP** | Canonical reader of `sourced_rules.json`. | `tests/unit/test_sourced_rules.py` | 
| 81 | `explainer_engine/standards/sourced_rules.json` | Rules | **DONE in PR #119** (`BP-167..172`, `BP-109` `0.05`, `BP-141` `0.45`). | **CHANGE** (minor reconciliation) | Add `rehook_tts_tags: ["excited"]` on `middle_calm_90_480s` in `BP-169` (strictly for `rehook_spike: true` segments `S06`/`S09`); preserve `BP-170` `FAIL` severity and `static_still_max_s_by_zone` (`1.5/2.0/2.5s`) ceiling for both Tier 1 and Tier 2 stills (`CD-03`). | `tests/unit/test_sourced_rules.py` | 
| 82 | `explainer_engine/edit/rhythm_profile.py` | Rhythm | **DONE in PR #119** (`WP-R2`). | **CHANGE** (minor alias support) | Add `ZONE_ALIASES` mapping `Z1_HOOK_0_30S -> hook_0_30s`, etc., so both Mold and BP-169 zone IDs resolve cleanly. | `tests/unit/test_rhythm_profile.py` | 
| 83 | `explainer_engine/edit/dramatic_still.py` | Stills | **DONE in PR #119** (`WP-R4`, Tier 3 cutout/plate swap). | **CHANGE** | Support 3-Tier Still Motion Ladder while preserving `BP-170` (`FAIL`): both `TIER_1` (`parallax_25d`) and `TIER_2` (`qwen_nextpose` / `nextpose_flip`) are strictly capped at `static_still_max_s_by_zone` (`1.5s` Hook/Climax, `2.0s` Early/Late, `2.5s` Calm Middle); only `TIER_3` (`cutout_relocation >= 0.25` with `min_subject_area_frac >= 0.08` or `plate_swap >= 0.30`) unlocks holds above `static_still_max_s_by_zone` up to `5.0s`. | `tests/unit/test_dramatic_still.py` | 
| 84 | `explainer_engine/scripting/rhythm_lint.py` | Rhythm | **DONE in PR #119** (`WP-R8`, `RL-01..04`). | **CHANGE** (minor) | Accept `production_script/4` documents directly (extracting shots across `segments[].shots` when top-level `shots` is not flat) so `validate.py` can pass `doc` directly to `rhythm_lint.check(doc)`. | `tests/unit/test_rhythm_lint.py` | 
| 85 | `explainer_engine/audio/hype_read.py` | Voice | **DONE in PR #119** (`WP-R5`, `HR-01..04`). | **CHANGE** (minor) | Allow `rehook_tts_tags` (`[excited]`) on segments marked as `rehook` (`S06`, `S09`) inside `middle_calm_90_480s`, and accept `production_script/4` `doc` directly. | `tests/unit/test_hype_read.py` | 
| 86 | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` | Governance | **DONE in PR #119** (`D-92`, `D-93`, `D-94` recorded). | **KEEP** (Update when `CD-01..10` are answered) | Already contains `D-92`, `D-93`, and `D-94`. | `tests/unit/test_d92_creator_answers.py` | 
| 87 | `explainer_engine/scripting/scene_lint.py` *(Added)* | Story / Scene | **P0 BUG at line 139**: `doc.get("schema") == "production_script/3"`. | **CHANGE** (P0 fix) | Change `binding(doc)` to `is_scene_script(doc)` so `SC-01..SC-10` bind on `production_script/4`. | `tests/unit/test_scene_lint.py` | 
| 88 | `explainer_engine/scripting/script_approval.py` *(Added)* | Governance | **P0 BUG at line 51**: `if doc.get("schema") != "production_script/3"`. | **CHANGE** (P0 fix) | Change `doc.get("schema") != BINDING` to `not is_scene_script(doc)` so `PV-53` binds on `/4`. | `tests/unit/test_script_approval.py` | 
| 89 | `explainer_engine/production/editorial_gate.py` *(Added)* | QA Gate | **P0 BUG at lines 342, 347**: `doc.get("schema") == "production_script/3"`. | **CHANGE** (P0 fix) | Change to `is_scene_script(doc)` so `EG-19` (`editorial_review/2`) and `EG-23` (`story_page.md`) bind on `/4`. | `tests/unit/test_editorial_gate.py` | 
| 90 | `explainer_engine/production/silent.py` *(Added)* | Voice Safety | **P0 BUG at lines 249, 276**: `doc.get("schema") != "production_script/3"`. | **CHANGE** (P0 fix) | Change to `not is_scene_script(doc)` so `PV-55` (`D-62` living-person voice ban) and `PV-56` (`D-63` bubble cap) bind on `/4`. | `tests/unit/test_silent.py` | 
| 91 | `explainer_engine/production/__main__.py` *(Added)* | CLI / Audio | **BUG at line 119**: `if not S.has_dialogue(doc): narrator_polish...`; line 148 `--size 1920x1080`. | **CHANGE** | Polish Odom's narrator chunks/turns even when `S.has_dialogue(doc)` is `True`; use `delivery.size()` on `/4` animated runs. | `tests/unit/test_narrator_polish.py`, `test_dialogue_and_shorts_set.py` | 
| 92 | `explainer_engine/finish/upscale.py` *(Added)* | Finish | **DONE in PR #119** (`WP-5b`, `1920x1088` -> `2560x1440 @ 24 fps`). | **KEEP** (Wire into `assemble.py`) | Module is complete and tested; wire into `assemble.py:materialize_lane_clips`. | `tests/unit/test_finish_upscale.py` | 
| 93 | `explainer_engine/core/delivery.py` *(Added)* | Delivery | **DONE in PR #119** (`BP-167` reader: `12m`, `2560x1440`, `24 fps`, `5` Shorts). | **KEEP** | Canonical reader of `BP-167`. | `tests/unit/test_delivery_defaults.py` | 
| 94 | `explainer_engine/core/contracts.py` *(Added)* | Contracts | Unchanged in PR #119 (`CN-01..16`, `REFUSED_LANES`). | **CHANGE** (minor) | Register `episode_mold/1` (`schemas/episode_mold.schema.json`) in contract validator. | `tests/unit/test_contracts.py` | 
| 95 | `explainer_engine/schemas/film_shots.schema.json` *(Added)* | Schema | Unchanged in PR #119. | **CHANGE** | Add optional `rhythm_profile` at root and `rhythm_zone`, `dramatic_change`, `still_motion_tier` on `shots[]`. | `tests/unit/test_film_shots.py` | 
| 96 | `explainer_engine/schemas/shot_route.schema.json` *(Added)* | Schema | Unchanged in PR #119. | **CHANGE** | Allow optional `still_motion` object on `STILL_HOLD` route entries. | `tests/unit/test_shot_router.py` | 
| 97 | `explainer_engine/research/fan_brief.py` *(Added)* | Research | Unchanged in PR #119. | **CHANGE** | Add Mold Layer 1 game-show filler phrases to `TEMPLATE_PHRASES`. | `tests/unit/test_fan_brief.py` | 
| 98 | `explainer_engine/research/hypotheses.py` *(Added)* | Research | Unchanged in PR #119. | **CHANGE** | Validate optional `mold_hooks` (`cold_promise_visual`, `rehook_180s_candidate`, `midpoint_360s_reversal_candidate`, `recommended_profile_id`). | `tests/unit/test_hypotheses.py` | 
| 99 | `explainer_engine/schemas/story_hypotheses.schema.json` *(Added)* | Schema | Unchanged in PR #119. | **CHANGE** | Add optional `mold_hooks` object to hypothesis items. | `tests/unit/test_hypotheses.py` | 
| 100 | `explainer_engine/llm/claude_api.py` *(Added from PR #112)* | LLM API | Missing PR #112's 2-line `load_job` string `system` fix (`1273619b`). | **CHANGE** | Cherry-pick lines 1066–1067 (`sys0 = spec.get("system", [])`; `([sys0] if isinstance(sys0, str) else list(sys0))`) from PR #112. | `tests/unit/test_claude_api.py` | 
| 101 | `config/master_mold_v2_1.json` *(NEW)* | Mold Contract | Does not exist in repo tree (`GEMINI_ARGON_UNIFIED_HANDOFF` §7). | **NEW** | Canonical machine-readable Mold contract (`schema: "episode_mold/1"`), reconciled with `M-01..M-05` and delegating all BP numbers to `sourced_rules.json` (`D-59`). | `tests/unit/test_master_mold_contract.py (NEW)` | 
| 102 | `docs/MASTER_MOLD_V2_1.md` *(NEW)* | Mold Spec | Does not exist in repo tree. | **NEW** | Canonical human-readable Master Mold v2.1.0 specification in `docs/` (reconciled with `M-01..M-05`) and indexed in `docs/INDEX.md`. | `explainer_engine/docs_lint.py` | 
| 103 | `explainer_engine/schemas/episode_mold.schema.json` *(NEW)* | Schema | Does not exist in repo tree. | **NEW** | JSON Schema Draft 2020-12 validating `config/master_mold_v2_1.json` (`episode_mold/1`). | `tests/unit/test_master_mold_contract.py (NEW)` | 
| 104 | `explainer_engine/scripting/mold_contract.py` *(NEW)* | Mold Reader | Does not exist in repo tree. | **NEW** | Stdlib reader of `config/master_mold_v2_1.json` providing `anchor_beats()`, `profile_spec(pid)`, `still_motion_tier(shot_s, zone_id)`, `semantic_slots()`, and cross-checking every `canonical_bp_ref` against `sourced_rules.json`. | `tests/unit/test_master_mold_contract.py (NEW)` | 
| 105 | `explainer_engine/edit/bounded_timeline.py` *(NEW)* | Timeline Engine | Does not exist in repo tree. | **NEW** | Implements the 6-step Bounded Timeline Engine (`±18%` clause-aligned proposal, hard lane/zone clamp, `24 fps` integer frame projection, `8k+1` + `BP-128` handle derivation, and local frame-transfer auto-replan). | `tests/unit/test_bounded_timeline.py (NEW)` | 
| 106 | `explainer_engine/scripting/schema_version.py` *(NEW)* | Versioning | Does not exist in repo tree. | **NEW** | Tiny helper `version(doc, prefix="production_script") -> int` and `is_scene_script(doc) -> bool` used across all 10 validator modules so `/4` automatically inherits `/3` scene/approval/safety rules. | `tests/unit/test_production_script_schema.py` | 
| 107 | `tests/unit/test_master_mold_contract.py` *(NEW)* | Unit Test | Does not exist in repo tree. | **NEW** | Validates `config/master_mold_v2_1.json` against `episode_mold.schema.json`, verifies zero raw `#XXXXXX` HEX codes (`D-22`), verifies zero duplicate BP numbers (`D-59`), and pins `AB01..AB12` and `S01..S16` alignment. | Self | 
| 108 | `tests/unit/test_bounded_timeline.py` *(NEW)* | Unit Test | Does not exist in repo tree. | **NEW** | Verifies the 6-step Bounded Timeline Engine across 100 seeds per segment (`17,280` frames exact, `8k+1` LTX frames, `CV >= 0.20`, `max_similar_run <= 3`). | Self | 
| 109 | `explainer_engine/production_gate.py` *(Added)* | Gate CLI | **P0 BUG at line 89**: `if doc.get("schema") == _sa.BINDING:` (`"production_script/3"`) skips Gate `0.9` (`approval #1 (script)`) on `/4` scripts! | **CHANGE** (P0 fix) | Replace `doc.get("schema") == _sa.BINDING` with `is_scene_script(doc)` so Gate `0.9` runs on both `/3` and `/4`. | `tests/unit/test_production_script_schema.py` | 

## 7. Existing Functionality and Controls to Preserve

The following repository invariants, modules, and governance locks **work well today and must be preserved without weakening**:

1. **Single Canonical Home for Numeric Rules (`D-59`)**:

   * `explainer_engine/standards/sourced_rules.json` + `sourced_rules.py` (`SR.T(bp_id, key)`, `SR.level(bp_id)`).

   * **Preservation Rule**: `config/master_mold_v2_1.json` must **never** become a competing copy of `BP-169`, `BP-170`, `BP-171`, `BP-172`, `BP-109`, `BP-141`, or `BP-167`. Instead, `config/master_mold_v2_1.json` stores `canonical_bp_ref` pointers (`{"bp_id": "BP-169", "key": "profiles.mrbeast_animated.zones"}`), and `mold_contract.py` reads the numbers live from `sourced_rules.py`.

2. **Single Canonical Home for Palette Colours (`D-22`)**:

   * `explainer_engine/design/palette.json` + `design/palette.py`.

   * **Preservation Rule**: `tests/unit/test_palette.py` and `explainer_engine/docs_lint.py` forbid raw `#XXXXXX` hex strings outside `design/palette.json`. All Mold zone color grades use semantic tokens (`paper`, `ink`, `night`, `support_blue`, `mechanism_teal`, `uncertain_amber`, `answer_coral`, `true_green`, `false_red`, `grey_mid`, `faction_a`, `faction_b`) plus `episode.world.light_key` and `BP-130` Reinhard LAB clamping.

3. **Hard Money Ceilings, Protected Configs & Paid-Run Watchdog (`D-56`, `D-74`, `D-84`, `OR-23`, `OR-36`)**:

   * `config/spend_caps.json`, `config/model_routing.json`, `config/channel_voices.json`, `config/cloud_pins.json`, `explainer_engine/core/spend_caps.py`, `core/ledger.py`, `cloud/runpod.py` (80% stop, `self_stop_sh`, `dead_man_sh`, `auto_delete_stopped` for 0 GB pods after 24h per `D-92`), `governance/hooks.py`, and `.claude/agents/paid-run-watchdog.md` (`OR-36` Haiku watchdog).

   * **Preservation Rule**: Zero edits to protected configs without explicit creator approval; zero paid API or GPU calls during roadmap implementation.

4. **7-Stage Writers' Room Field Isolation & Fresh-Read Guard (`D-48`, `D-79`, `OR-20`, `OR-32`)**:

   * `explainer_engine/scripting/stage_guard.py` (`start`, `fresh`, `violations`) and `production/editorial_gate.py` (`editorial_review/2` + Georgian `story_page.md`, `BP-89`).

   * **Preservation Rule**: Keep the exact stage order (`architect -> writer -> beats -> performer -> editor -> caster -> shorts -> script-critic`) and field-ownership locks so later mechanical stages can never silently alter frozen story words.

5. **Visual & Audio Stack Decisions (`D-80`, `D-85`, `D-87`, `D-89`, `D-90`, `D-62`, `D-63`)**:

   * `D-80`: Qwen-Image-2.1 + `xworld_v2` LoRA (`checkpoint-3000`); all old `2512`/`Edit-2511`/`wldnk_*` models remain banned in `qa/keyframe_gate.py`.

   * `D-85` / `D-92`: Native `24 fps` across the animated route (`job_manifest/1`, `film_shots/2`, `audio_spine/2`, `sound_mix_manifest/2`, `build_video_v2`, `shorts.py`).

   * `D-87`: 2D Natural Earth vector maps (`maps/render.py`) with `faction_a` (blue) / `faction_b` (vermilion) colour-blind-safe palette (`BP-151`).

   * `D-89`: `HOST_COMMENTARY` remains refused in `core/contracts.py:REFUSED_LANES`.

   * `D-90`: Character dialogue lines cast via `voice-caster.md`, read first on ElevenLabs, and conditioning LTX-2.5 `DIALOGUE_CU` clips (`audio_slice_sha256`), while living real people remain unvoiced (`D-62`, `PV-55`) and told in reported speech (`D-63`, `PV-56`).

6. **Backward Compatibility for Legacy `/1`–`/3` and `calm_docudrama` Episodes**:

   * Shipped still-picture episodes (`30 fps`, `production_script/1..3`) and `examples/napoleon_vs_genghis/film_shots.json` (`calm_docudrama`) must continue to pass all existing unit tests without modification.

## 8. Conflicts, Silent Regressions, and Missing Capabilities

### 8.1 Complete Conflict & Gap Registry (`CG-01` through `CG-14`)

| ID | Category | Severity | Conflict / Gap Description | Exact Files Affected | Resolution in Roadmap | 
| ----- | ----- | ----- | ----- | ----- | ----- | 
| **CG-01** | **Current Code vs. `/4` Schema** | **P0 BLOCKER** | **11 core modules check `== "production_script/3"` (exact string equality via `SCENE_SCHEMA` or `_sa.BINDING`)**. Passing a `"production_script/4"` script disables `SC-01..10` (`scene_lint.py`), `PV-53` (`script_approval.py`), Gate `0.9` (`production_gate.py:89`), `DW-11` signature-word check (`speech.py`), `PV-55`/`PV-56` (`silent.py`), `PV-57` (`validate.py`), `EG-19`/`EG-23` (`editorial_gate.py`), `CS-07` staged-dialogue master check (`staging.py`), downgrades `ST-00` from FAIL to REVIEW (`story_lint.py`), breaks `AL-02` silence-default (`audio/layers.py` checking `timed["script_schema"]`), and **reverts `production/beats.py` to `/2` 1.5s metronome rules**! | `scene_lint.py:139`, `script_approval.py:51`, `production_gate.py:89`, `speech.py:60`, `story_lint.py:75`, `beats.py:107`, `editorial_gate.py:342,347`, `silent.py:249,276`, `staging.py:418`, `validate.py:89`, `audio/layers.py:53` | **BATCH-M0**: Introduce `scripting/schema_version.py` with explicit `is_scene_script(doc_or_schema)` (`/3` and `/4` only) and `is_zoned_rhythm_script(doc_or_schema)` (`/4` only), accepting either a `dict` (`"schema"` or `"script_schema"`) or a `str` schema name, and update all 11 modules. | 
| **CG-02** | **Current Code vs. Odom Narrator Polish** | **P0 BLOCKER** | `explainer_engine/production/__main__.py:119` runs `if not S.has_dialogue(doc): polish = narrator_polish.polish_in_place(...)`. Because every CrossWorld docudrama script has character dialogue (`S.has_dialogue(doc) == True`), **Odom's mandatory bass-shelf polish (`audio/narrator_polish.py`) is never applied on real episodes**! | `explainer_engine/production/__main__.py:119`, `explainer_engine/audio/narrator_polish.py` | **BATCH-M0 / BATCH-M4**: Implement `narrator_polish.polish_narrator_spans_in_place(narration_wav, words, toks, doc)` at `production/__main__.py:119` (**after** `join_reads`, `scribe_words.align`, `voice_check.check_speakers` on raw unpolished timbre, and `pause_pad.pad_pauses` writing `48 kHz` WAV): polish a temp WAV copy via `NP.CHAIN` and splice polished samples strictly over narrator spans (`S.speaker(line) == "narrator"`) with `10 ms` cosine ramps in inter-turn silence, leaving character spans bit-for-bit untouched and avoiding `wave.open` errors on `.mp3` chunk inputs. | 
| **CG-03** | **Current Code vs. `KP-47` Fast-Action Lint** | **P1 MAJOR** | `scripting/shot_prompt_lint.py:194` checks `KP-47` (`BP-172` fast-action verbs in hyped zones) only when `shot.get("rhythm_zone") in HYPED_ZONES or shot.get("fast_action") is True`. However, `scripting/film_shots.py:compose()` does **not** copy `rhythm_zone` onto composed video shot dicts, so `KP-47` never runs during `film_shots check`! | `explainer_engine/scripting/film_shots.py:449`, `explainer_engine/schemas/film_shots.schema.json` | **BATCH-M0 / BATCH-M5**: Add optional `rhythm_zone` to `schemas/film_shots.schema.json` AND compute `rhythm_zone` in `film_shots.py:compose()` from `shot.get("rhythm_zone") or rhythm_profile.zone_at_time(cum_t)` on zoned profiles so `KP-47` fires during `film_shots check` even when `shot["rhythm_zone"]` is omitted. | 
| **CG-04** | **Mold JSON v2.1.0 vs. `sourced_rules.json` (`D-59`)** | **P1 MAJOR** | `mrbeast_12min_video_mold.json` v2.1.0 embeds zone numbers (`192.0`, `177.0`, `166.6`, `184.3`, `157.0` WPM), `Z1..Z5` IDs, `bp141_non_character_max: 0.8` on Profiles A/D, and extra TTS tags (`[gasps]` in Z1, `[excited]` in Z3) that differ from `BP-169` and `BP-141` (`M-01..M-03`). | `config/master_mold_v2_1.json`, `explainer_engine/standards/sourced_rules.json`, `explainer_engine/edit/rhythm_profile.py`, `explainer_engine/audio/hype_read.py` | **BATCH-M1**: Reconcile `M-01..M-03`, add `ZONE_ALIASES` in `rhythm_profile.py`, add `rehook_tts_tags` (`["excited"]` for `S06`/`S09`) in `BP-169` + `hype_read.py`, and strip duplicate BP numbers from `config/master_mold_v2_1.json`. | 
| **CG-05** | **Mold Layer 1 (`AB07..AB12`) vs. Layer 3 (`S09..S16`) & `BP-04`** | **P1 MAJOR** | Layer 1 `twelve_anchor_beats` places Climax (`AB10`) in `S13` (`570–600s`) and Aftermath (`AB11`) at `600–690s`, whereas Layer 3 `segments_summary_16` and `BP-169` place Climax (`climax_660_720s`) in `S15–S16` (`660–720s`) and `BP-04` (`ENG-5`, `answer_after_share = 0.90`) requires the resolution/answer to wait until `>= 90%` of spoken words have been delivered (`M-05`). | `config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `explainer_engine/scripting/mold_contract.py`, `explainer_engine/scripting/story_lint.py`, `explainer_engine/qa/engagement.py` | **BATCH-M1 / BATCH-M2 / BATCH-M6**: Align `AB07..AB12` segment IDs and windows with `S08..S16` (`AB11` -> `S15` `660–690s`, `AB12` -> `S16` `690–720s`) and enforce **two independent checks**: (1) `S16` occupies `690–720s`, and (2) `BP-04` cumulative spoken-word share (`words_before_resolution / total_spoken_words >= 0.90`, inclusive boundary) is verified across actual voiced narrator + character words (excluding TTS tags and non-spoken metadata), never approximated by a fixed `648s` timestamp. | 
| **CG-06** | **Mold Still Motion Ladder vs. `BP-170` (`dramatic_still.py`)** | **P1 MAJOR** | Mold v2.1.0 proposes a 3-Tier Still Motion Ladder (`TIER_1` `parallax_25d`; `TIER_2` `qwen_nextpose` / `nextpose_flip`; `TIER_3` `cutout_relocation` / `plate_swap`), whereas `BP-170` (`dramatic_still.py`, severity `FAIL`) rejects any still above `static_still_max_s_by_zone` (`1.5s` in Hook/Climax, `2.0s` in Early/Late, `2.5s` in Calm Middle) unless it has a verified Tier 3 `dramatic_change` (`M-04`). | `explainer_engine/edit/dramatic_still.py`, `explainer_engine/schemas/dramatic_still.schema.json`, `explainer_engine/standards/sourced_rules.json` (`BP-170`) | **BATCH-M5** (exact alignment with `M-04`): Preserve `BP-170`'s `FAIL` severity and keep `static_still_max_s_by_zone` (`1.5s` Hook/Climax, `2.0s` Early/Late, `2.5s` Calm Middle) as the strict maximum hold for **both Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose` / `nextpose_flip`)**. Only Tier 3 (`cutout_relocation >= 0.25` with `min_subject_area_frac >= 0.08` or `plate_swap >= 0.30`) unlocks holds above `static_still_max_s_by_zone` up to `5.0s`. Any future Tier 2 hold extension beyond `1.5/2.0/2.5s` is strictly conditional on (a) quantitative masked subject pose-delta measurement, (b) character identity validation (`KG-13`), (c) a measurable acceptance threshold, and (d) explicit creator approval (`CD-03`). | 
| **CG-07** | **Legacy Calm Checks vs. Zoned Scripts (`WP-R7`)** | **P1 MAJOR** | `film_shots.py` (`KP-35`, `BP-107` `11–17 shots/min`), `variant_plan.py` (`VP-18`, `BP-107`), `board.py` (`RHYTHM-1` `BP-40` `<=10 pics/min`, `RHYTHM-2` `BP-84` `>=2.0s`), `motion_lint.py` (`MO-01` `BP-40`), and `shot_rules.py` (`UR-11` `BP-85`) flag REVIEW/FAIL on every `/4` zoned script. | `film_shots.py`, `variant_plan.py`, `board.py`, `motion_lint.py`, `shot_rules.py`, `validate.py` | **BATCH-M2 / BATCH-M5 / BATCH-M6**: When `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, defer shot-rate and hold-length checks in those modules to `scripting/rhythm_lint.py` (`BP-169`, `BP-170`). | 
| **CG-08** | **Existing Prompts/Agents vs. New Mold** | **P1 MAJOR** | All 16 `.claude/agents/*.md` and 16 `.claude/skills/*/SKILL.md` still instruct `/3`, `15-minute` runtime (`story-architect.md`), flat `170 WPM` (`scene-writer.md`), `Oxley` (`elevenlabs-voice/SKILL.md`), and `10` Shorts (`shorts-writer.md`). | 10 agent `.md` files and 10 skill `SKILL.md` files (Section 5) | **BATCH-M3**: Update the 10 affected agent pages and 10 affected skill files so the Mold governs story design and script writing from Stage 1. | 
| **CG-09** | **Old Research (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`) vs. New Mold & Creator Decisions** | **P1 MAJOR** | The 214-page research compendium contains older recommendations superseded by creator decisions: (a) `899s` (`15-min`) flagship blueprint (`Part I §Second-by-Second Episode Architecture`) vs `720s` (`12-min`, `BP-167`); (b) permanent 2.5D hosts (`Strategy E`) vs `D-89` (`NO permanent hosts`); (c) `DOC_MAP` / `DRAMA_BLOCKED_3D` lane names vs `MAP` and refused `DRAMA_BLOCKED_3D` (`D-75`); (d) `-16 LUFS` / `135–145 WPM` craft proposals vs `D-91`/`D-92` (`-14 LUFS`, `BP-169` zones). | Documentation & agent instructions | **Enforced throughout Roadmap**: Never copy obsolete `15-min`, permanent-host, `DOC_MAP`, or `-16 LUFS` rules from the old research doc; creator decisions `D-89`, `D-91`, `D-92`, `D-93`, `D-94` and `BP-167..172` strictly win. | 
| **CG-10** | **`D-90` Character Voice Audio-In vs. `audio_spine/2` & `router.py`** | **P1 MAJOR** | `edit/router.py:77` refuses `DIALOGUE_CU` unless `audio_spine/2.post_hoc_shots` has `source == "clip"` and a non-null `clip_sha256`. Currently `audio/spine.py:114` only writes `source: "planned", clip_sha256: None` until post-render `retime_post_hoc`! Under `D-90`, the ElevenLabs character take is recorded **before** LTX rendering and conditions the clip. | `explainer_engine/audio/spine.py`, `explainer_engine/edit/router.py` | **BATCH-M4**: Add `spine.bind_character_takes(spine, takes_dir)` to slice/hash pre-recorded ElevenLabs character takes into `post_hoc_shots` (`source: "clip"`, `clip_sha256: <sha256>`) before `router.py` runs. | 
| **CG-11** | **Bounded Timeline Engine Missing in Code** | **P2 MODERATE** | The 6-step Bounded Timeline Engine (`±18%` clause-aligned timing + `24 fps` integer projection + `8k+1` LTX frame derivation) exists in the Mold spec but not yet as a callable Python module in `explainer_engine/edit/`. | `explainer_engine/edit/bounded_timeline.py (NEW)` | **BATCH-M5**: Implement `explainer_engine/edit/bounded_timeline.py` + `tests/unit/test_bounded_timeline.py`. | 
| **CG-12** | **Three-Lane Clip Materialization (`WP-5a`) Missing Before `build_video_v2`** | **P1 MAJOR** | `production/assemble.py:build_video_v2` expects every shot in `shots_dir` to be a rendered `.mp4` at the target frame size, but nothing automatically runs `finish/upscale.py` on `1920x1088` `VIDEO` clips or renders `STILL_HOLD` (`dramatic_still`/`parallax`) and `MAP`/`COMPENSATOR` items into `shots_dir` `.mp4` files. | `explainer_engine/production/assemble.py`, `explainer_engine/finish/upscale.py` | **BATCH-M6**: Implement `assemble.materialize_lane_clips(job, route, manifest, out_shots_dir)` to unify `VIDEO` (upscaled), `STILL` (Tier 1/2/3), and `HELPER` (`visual_compensator`) into `2560x1440 @ 24 fps` `.mp4` clips for `build_video_v2`. | 
| **CG-13** | **`xworld_v2` LoRA Strength Inconsistency (`0.7` vs `1.0`)** | **P2 MODERATE** | `config/cloud_pins.json:103` pins `models.loras.xworld_v2.weight = 0.7`, whereas `training/pods/p12/p12b.json` (`style_lora.strength`) and `qa/style_prompt.py:25` (`INFERENCE["lora_strength"]`) use `1.0`. | `config/cloud_pins.json`, `explainer_engine/training/pods/p12/p12b.json`, `explainer_engine/qa/style_prompt.py` | **BATCH-M8A** (gated on creator decision `CD-02` before P12 bundle upload to HF and `BATCH-M8B` `GATE-P1`): Lock `0.7` (or `1.0`) across all 3 files once creator answers `CD-02`. | 
| **CG-14** | **PR #112 Stale Branch Disposition** | **P2 MODERATE** | [PR #112](https://github.com/vano1919/explainer-engine/pull/112) (`1273619b`) has a valid 2-line bugfix in `explainer_engine/llm/claude_api.py:1066` (`load_job` string `system` handling) + unit test, bundled with stale edits to protected `config/spend_caps.json` (`max_usd: 95.0`) and `config/model_routing.json`. | `explainer_engine/llm/claude_api.py`, `tests/unit/test_claude_api.py` | **BATCH-M0**: Cherry-pick **only** the 2-line `claude_api.py` fix and its unit test; reject the stale config hunks. | 

## 9. Ordered Implementation Batches (`BATCH-M0` through `BATCH-M7`, Free `BATCH-M8A`, and Paid `BATCH-M8B`)

The implementation roadmap is divided into **9 100% FREE batches (`BATCH-M0` through `BATCH-M7` plus `BATCH-M8A`)** (local CPU/code/schema/prompt/test/governance changes, zero API spend, zero GPU pods) and **1 strictly separated PAID stage (`BATCH-M8B`)** subdivided into four sequential creator-approval gates (`GATE-P1`, `GATE-P2`, `GATE-P3`, `GATE-P4`) protected by `OR-23` pod plans, `OR-36` Haiku watchdogs, and `config/spend_caps.json` hard caps.

### 9.1 `BATCH-M0` — P0 Regression Fixes (`production_script/4` Compatibility, Odom Polish Gate, `KP-47` Propagation & PR #112 Parser Fix)

* **Objective & Scope**: Eliminate the **11** silent `== "production_script/3"` regressions before any new Mold code is layered on top; fix the `not S.has_dialogue(doc)` gate in `production/__main__.py:119` via post-`voice_check` narrator-span-only polish; propagate `rhythm_zone` across all shots in `film_shots.compose()`; and cherry-pick the 2-line `claude_api.load_job` string-system parser fix from [PR #112](https://github.com/vano1919/explainer-engine/pull/112).

* **Exact Repository Files to Inspect or Change (`19` files)**:

   1. `explainer_engine/scripting/schema_version.py` *(NEW)*

   2. `explainer_engine/scripting/scene_lint.py` (line 139)

   3. `explainer_engine/scripting/script_approval.py` (line 51)

   4. `explainer_engine/scripting/speech.py` (line 60)

   5. `explainer_engine/scripting/story_lint.py` (line 75)

   6. `explainer_engine/production/beats.py` (line 107)

   7. `explainer_engine/production/editorial_gate.py` (lines 342, 347)

   8. `explainer_engine/production/silent.py` (lines 249, 276)

   9. `explainer_engine/production/staging.py` (line 418)

  10. `explainer_engine/production/validate.py` (line 89)

  11. `explainer_engine/audio/layers.py` (line 53)

  12. `explainer_engine/production_gate.py` (line 89)

  13. `explainer_engine/production/__main__.py` (line 119) & `explainer_engine/audio/narrator_polish.py`

  14. `explainer_engine/scripting/film_shots.py` (line 449 `compose`) & `explainer_engine/schemas/film_shots.schema.json`

  15. `explainer_engine/llm/claude_api.py` (lines 1063–1067, from PR #112 `1273619b`)

  16. `tests/unit/test_production_script_schema.py`

  17. `tests/unit/test_claude_api.py`

* **Agents & Prompts Affected**: None in `BATCH-M0` (pure code bugfix batch).

* **Required Implementation Changes**:

  1. Create `explainer_engine/scripting/schema_version.py` with explicit schema dispatch predicates:

     * `SCENE_SCHEMAS = frozenset({"production_script/3", "production_script/4"})`

     * `ZONED_RHYTHM_SCHEMAS = frozenset({"production_script/4"})`

     * `def schema_name(doc_or_schema: dict | str | None) -> str`: extracts `doc.get("schema") or doc.get("script_schema")` if given a `dict`, or returns the `str` directly (handling `audio/layers.py:53` `timed["script_schema"]`).

     * `def is_scene_script(doc_or_schema: dict | str | None) -> bool: return schema_name(doc_or_schema) in SCENE_SCHEMAS` (never blindly matching an unknown future `/5` schema).

     * `def is_zoned_rhythm_script(doc_or_schema: dict | str | None) -> bool: return schema_name(doc_or_schema) in ZONED_RHYTHM_SCHEMAS`.

  2. Replace `doc.get("schema") == "production_script/3"` (and `!= "production_script/3"`, `doc.get("schema") == _sa.BINDING` in `production_gate.py:89`, and `timed.get("script_schema") == BEATS.SCENE_SCHEMA` in `audio/layers.py:53`) across all **11** validator/gate/production modules with `is_scene_script(...)`.

  3. In `explainer_engine/audio/narrator_polish.py` and `explainer_engine/production/__main__.py:119`, implement **post-`voice_check` narrator-span-only polish (`polish_narrator_spans_in_place`)**:

     * **Why pre-`join_reads` in-place chunk polish is unsafe**: (a) `narrator_polish._seconds()` calls `wave.open()`, which raises `wave.Error` when CLI `audio` inputs are `.mp3` files (`seams.py:8`); (b) `voice_check.check_speakers` at `production/__main__.py:107` must evaluate **raw unpolished timbre** (`EL-13`) before EQ; and (c) `cmd_words` accepts either a single pre-joined file (`len(audio) == 1`) or multiple chunk files (`len(audio) > 1`).

     * **Safe Span-Level Implementation**: Keep `join_reads`, `scribe_words.align`, `SIL.insert`, `voice_check` (raw timbre), and `pause_pad.pad_pauses` in their exact existing order (`__main__.py:72–117`). At line `119` (after `voice_layer.write_wav(out / "narration.wav", padded, sr)` guarantees a `48 kHz` mono PCM WAV on disk): if `not S.has_dialogue(doc)`, run `narrator_polish.polish_in_place(out / "narration.wav")`; if `S.has_dialogue(doc)`, run `narrator_polish.polish_narrator_spans_in_place(out / "narration.wav", words, toks, doc)` which runs `NP.polish` to a temp WAV and splices the polished samples into `padded` **strictly over narrator token intervals (`S.speaker(line) == "narrator"`)** with `10 ms` cosine ramps inside the inter-speaker silence gaps, leaving character dialogue samples bit-for-bit untouched and preserving exact sample count (`len(out_pcm) == len(padded)`).

  4. In `explainer_engine/schemas/film_shots.schema.json` and `explainer_engine/scripting/film_shots.py:compose()`:

     * Add optional `rhythm_profile` at the root and optional `rhythm_zone` (`enum` of the 5 `BP-169` canonical lowercase IDs) on `shots[]` in `schemas/film_shots.schema.json`.

     * In `film_shots.py:compose(doc)`, advance cumulative `t_start_s` across **every** shot in `doc["shots"]` in timeline order (`start_s = float(shot.get("start_s", cum_t)); cum_t = start_s + float(shot["seconds"])` — **including `teaser_of` cold-open shots**, which occupy real timeline seconds at `0–12s` in `hook_0_30s`!) and set `"rhythm_zone": shot.get("rhythm_zone") or (rhythm_profile.zone_at_time(start_s, total_s=total_s, profile_name=profile_name)["id"] if profile_name != "calm_docudrama" else None)` on each composed `.video` dict so `KP-47` fires during `film_shots check`.

  5. Apply PR #112's 2-line `sys0 = spec.get("system", [])` fix in `explainer_engine/llm/claude_api.py` and add `test_a_string_system_in_a_job_file_is_one_block_not_one_per_character` in `tests/unit/test_claude_api.py`.

* **Dependencies & Prerequisites**: Creator kickoff approval (`CD-01`) + external operational prerequisite **`GATE-EXT-MAIN-PROTECT`** (`RSK-06`: verify GitHub branch protection is enabled on `main`—requiring PRs, `quality` CI checks, no force-pushes, and no direct pushes—and confirm `git branch --show-current == "planning/master-mold-integration-2026-11-02"` on base `5013a55aca5a17a3734150f61a5eb172abcbe3b8`).

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/test_production_script_schema.py tests/unit/test_claude_api.py tests/unit/test_narrator_polish.py tests/unit/test_shot_prompt_lint.py` passes with `0` failures.

  * New regression test `test_schema_4_enforces_all_v3_scene_beats_silent_and_editorial_rules` proves that changing `"schema": "production_script/3"` to `"schema": "production_script/4"` on an invalid script still triggers `SC-01..10`, `PV-53`, `DW-11`, `CS-07`, `ST-00` (`FAIL`), `PV-55`, `PV-57`, `EG-19`, `AL-02` (`layers.silence_is_default`), and `/3` `beats.scene_rules`, while an unknown `"production_script/5"` is rejected.

  * New integration test `test_film_shots_check_fires_kp47_in_hyped_zone_and_skips_calm_zone` runs `film_shots.check(doc)` end-to-end on a 2-shot document (1 shot in `hook_0_30s` at `t=2.0s` with a slow/static prompt, 1 shot in `middle_calm_90_480s` at `t=150.0s`) and verifies `KP-47` fires on the hyped shot and does not fire on the calm shot.

* **Expected Outputs / Artifacts**: Clean commit on target branch; `0` regressions across the 2,448-test suite.

* **Risks & Recovery Paths**: Low risk; if any legacy `/2` fixture is misclassified, `version(doc)` returns `2` (`is_scene_script == False`), preserving `/2` behavior.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: All 11 modules use `is_scene_script(...)` and full unit test suite is green.

### 9.2 `BATCH-M1` — Canonical Master Mold v2.1.0 Contract, Schema & Registry Reconciliation (`M-01..M-05`)

* **Objective & Scope**: Commit the reconciled Master Mold v2.1.0 into the repository (`config/master_mold_v2_1.json` and `docs/MASTER_MOLD_V2_1.md`), create `explainer_engine/schemas/episode_mold.schema.json` (`episode_mold/1`) and `explainer_engine/scripting/mold_contract.py`, resolve all 5 internal discrepancies (`M-01..M-05`) identified in Section 3.2, and enforce `D-59` (no duplicated BP numbers) and `D-22` (no raw HEX codes).

* **Exact Repository Files to Inspect or Change (`10` files)**:

   1. `config/master_mold_v2_1.json` *(NEW)*

   2. `docs/MASTER_MOLD_V2_1.md` *(NEW)*

   3. `docs/INDEX.md` (add `MASTER_MOLD_V2_1.md` link)

   4. `explainer_engine/schemas/episode_mold.schema.json` *(NEW)*

   5. `explainer_engine/scripting/mold_contract.py` *(NEW)*

   6. `explainer_engine/edit/rhythm_profile.py` (add `ZONE_ALIASES` for `Z1..Z5 <-> hook_0_30s..climax_660_720s`)

   7. `explainer_engine/audio/hype_read.py` (support `rehook_tts_tags` on `rehook` segments in `middle_calm_90_480s`)

   8. `explainer_engine/standards/sourced_rules.json` (add `rehook_tts_tags: ["excited"]` to `BP-169` `middle_calm_90_480s`)

   9. `explainer_engine/core/contracts.py` (register `episode_mold/1`)

  10. `tests/unit/test_master_mold_contract.py` *(NEW)*

* **Agents & Prompts Affected**: None yet (contract & schema foundation for `BATCH-M2` and `BATCH-M3`).

* **Required Implementation Changes**:

  1. Resolve `M-01..M-05` in `config/master_mold_v2_1.json` and `docs/MASTER_MOLD_V2_1.md`:

     * Use canonical `BP-169` zone IDs (`hook_0_30s`, `early_30_90s`, `middle_calm_90_480s`, `late_third_480_660s`, `climax_660_720s`) with `mold_zone_alias` (`Z1_HOOK_0_30S`..`Z5_CLIMAX_660_720S`).

     * Replace duplicate BP threshold values in `parameter_registry`, `zones_5`, and `episode_profiles` with `canonical_bp_ref` pointers resolved at runtime by `scripting/mold_contract.py` (`SR.T(bp_id, key)`), keeping the 2,066-word numbers strictly inside `reference_instance_metrics` (`classification: "reference_only"`).

     * Fix `AB07..AB12` segment IDs and `window_s` in Layer 1 to match `S08..S16` in Layer 3 (`AB07: S08–S09 270–375s`, `AB08: S10–S11 375–480s`, `AB09: S12 480–540s`, `AB10: S13–S14 540–660s`, `AB11: S15 660–690s`, `AB12: S16 690–720s`), `BP-169`, `BP-142`, and `BP-04` (`answer_after_share >= 0.90` checked on cumulative spoken-word share independently of `S16`'s `690–720s` clock window).

     * **Single Canonical `BP-04` Cumulative Spoken-Word Share Implementation (`qa/engagement.py:resolution_word_share(doc)`)**:

       * **No Duplicate Logic**: Because `BP-04.enforced_by` in `sourced_rules.json` already designates `explainer_engine/qa/engagement.py:ANSWER_AFTER_SHARE`, define `resolution_word_share(doc: dict) -> dict` **once** in `explainer_engine/qa/engagement.py` and import it in `scripting/story_lint.py` and `scripting/mold_contract.py` so two validators can never diverge.

       * **Episode Spoken Word Definition & `voiced: false` Fix**: Update `qa/engagement.py:_text(seg)` (which currently joins all `seg["lines"]` without checking `voiced`) to include a line iff `line.get("voiced", True) is not False` (excluding `voiced: false` silent/thought-bubble lines per `D-62`, while defaulting omitted `voiced` to `True`). Both narrator lines (`speaker` omitted or `"narrator"`) and voiced diegetic character dialogue lines (`speaker` present and `voiced: true`) count in exact script order. The denominator `total_spoken_words` is the sum of spoken words across the **entire episode (`S01..S16`)**, including all words spoken during and after the resolution.

       * **Exclusions & Tokenization**: Separate `line["tags"]` arrays are never tokenized; inline bracketed tags (`[excited]`, `[short pause]`, etc.) in `line["text"]` are stripped via `re.sub(r"\[[^\]]*\]", " ", line["text"])` before tokenizing with `re.findall(r"[a-z0-9']+", clean.lower().replace("’", "'"))`. Stage directions, `intent`, `tone`, `emotion`, `pause_after`, `visual_beats`, `scene` headers, `shots`, and `graphics` are never counted.

       * **Deterministic Resolution Point `(i*, j*)` & Edge Cases**:

         1. For each line `(seg_idx, line_idx)`, `words_before_line(seg_idx, line_idx)` is the count of spoken words in all prior segments `0..seg_idx-1` plus all prior voiced lines `0..line_idx-1` in `seg_idx` (so if the resolution marker sits on a voiced line `(i*, j*)`, that line's own words are part of the resolution payload, not counted in `words_before_line`).

         2. The resolution start `(i*, j*)` is the earliest `(seg_idx, line_idx)` where `line.get("discloses_answer") is True`, OR `(line_idx == 0 and ((seg.get("drama") or {}).get("function") == "resolution" or seg.get("anchor_beat_id") == "AB12_FINAL_SYNTHESIS_AND_HARD_CUT"))`.

         3. If `total_spoken_words == 0`, return `status="FAIL"` (`empty spoken script`) without dividing by zero.

         4. If no segment or line in a `/4` script carries a resolution marker, return `status="FAIL"` (`missing resolution marker`, closing the current loop fall-through in `qa/engagement.py:165–171`).

         5. **Inclusive Boundary Rule**: `share_res = words_before_line(i*, j*) / total_spoken_words`. Matching `qa/engagement.py:167` (`before / total_words < ANSWER_AFTER_SHARE`), `share_res < 0.90` -> `FAIL`, `share_res == 0.90` -> `PASS`, and `share_res > 0.90` -> `PASS`, evaluated independently of `S16`'s `690–720s` clock window.

  2. Write `explainer_engine/schemas/episode_mold.schema.json` (`episode_mold/1`) and `explainer_engine/scripting/mold_contract.py`.

  3. Add `tests/unit/test_master_mold_contract.py` verifying: (a) `contracts.validate` passes on `config/master_mold_v2_1.json`; (b) every `canonical_bp_ref` resolves in `sourced_rules.json`; (c) zero `#XXXXXX` hex strings exist in `config/master_mold_v2_1.json` or `docs/MASTER_MOLD_V2_1.md` (`D-22`); (d) all `palette.json` token names in `zones_5` exist in `design/palette.json`; (e) `AB01..AB12` windows partition `[0.0, 720.0]` contiguously and align with `S01..S16`.

* **Dependencies & Prerequisites**: `BATCH-M0`.

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/test_master_mold_contract.py tests/unit/test_sourced_rules.py tests/unit/test_rhythm_profile.py` passes with `0` failures.

  * `python -m explainer_engine.docs_lint` passes with `0` errors.

* **Expected Outputs / Artifacts**: `config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `explainer_engine/schemas/episode_mold.schema.json`, `explainer_engine/scripting/mold_contract.py`.

* **Risks & Recovery Paths**: If `test_sourced_rules.py` checks for duplicate numbers across JSON files, stripping raw BP numbers from `config/master_mold_v2_1.json` in favor of `canonical_bp_ref` pointers guarantees `D-59` compliance.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: `contracts.validate` and `docs_lint` pass on the committed Mold files.

### 9.3 `BATCH-M2` — Upstream Research, Variant Planner & Story/Narration Lints (`WP-R6` Completion & `WP-R7` Part 1)

* **Objective & Scope**: Make the upstream planning and script-linting modules (`fan_brief.py`, `hypotheses.py`, `variant_plan.py`, `story_lint.py`, `narration_lint.py`, `register_lint.py`, `rhythm_lint.py`) fully Mold-aware so stories are planned, budgeted, and linted around the 12 Anchor Beats (`AB01..AB12`), Adaptive Profiles (`A..D`), and 5 Rhythm Zones (`BP-169`).

* **Exact Repository Files to Inspect or Change (`11` files)**:

   1. `explainer_engine/research/fan_brief.py`

   2. `explainer_engine/research/hypotheses.py`

   3. `explainer_engine/schemas/story_hypotheses.schema.json`

   4. `explainer_engine/scripting/variant_plan.py`

   5. `explainer_engine/scripting/story_lint.py`

   6. `explainer_engine/scripting/narration_lint.py`

   7. `explainer_engine/scripting/register_lint.py`

   8. `explainer_engine/scripting/rhythm_lint.py`

   9. `explainer_engine/schemas/production_script.schema.json`

  10. `explainer_engine/scripting/stage_guard.py`

  11. `tests/unit/test_variant_plan.py`, `tests/unit/test_story_engine.py`, `tests/unit/test_rhythm_lint.py`

* **Agents & Prompts Affected**: Prepares the validators that gate `story-architect`, `scene-writer`, and `performance-director` (updated in `BATCH-M3`).

* **Required Implementation Changes**:

  1. **Research (`fan_brief.py`, `hypotheses.py`, `story_hypotheses.schema.json`)**: Add Mold Layer 1 game-show filler phrases to `TEMPLATE_PHRASES` (`fan_brief.py`) and `register_lint.py`; add optional `mold_hooks` (`cold_promise_visual`, `rehook_180s_candidate`, `midpoint_360s_reversal_candidate`, `recommended_profile_id`) to `story_hypotheses.schema.json`.

  2. **Production Script Schema (`/4`) & Stage Guard**: Add optional `anchor_beat_id` (`enum: ["AB01_COLD_PROMISE" .. "AB12_FINAL_SYNTHESIS_AND_HARD_CUT"]`) and `rehook_spike` (`boolean`) to `segments[]`, and optional `still_motion_tier` to `shots[]` in `schemas/production_script.schema.json`; add `anchor_beat_id` and `rehook_spike` to `stage_guard.py:SEG_STORY`.

  3. **Variant Planner (`variant_plan.py`)**:

     * In `segments_from_script(doc)`, pass `zone=seg.get("rhythm_zone")` to `syllables.seconds`.

     * In `checks(dyn, prof)` (`VP-18`), accept an optional `rhythm_profile_name`: when `rhythm_profile_name == "mrbeast_animated"`, check `dyn["shots_per_min"]` against the `BP-169` weighted episode band (`18.0–28.0` shots/min) instead of `BP-107` (`11–17` shots/min), and include `mold_contract.profile_spec(pid)` guidance in `variant_plan.brief()`.

  4. **Story Lint (`story_lint.py`)**:

     * On `mrbeast_animated` (`/4`) scripts, compute `line_starts` and `ST-13` turn gaps using `rhythm_profile.words_to_seconds` (or per-segment `rhythm_zone` WPM) instead of flat `170 WPM`.

     * Add `ST-25`: verify on `/4` scripts with `template == "D"` that the `16` segments cover the `12` Anchor Beats (`AB01..AB12`), that `S16` (`AB12`) occupies `690–720s`, and that `BP-04` cumulative spoken-word share at the first resolution/answer disclosure satisfies `words_before_resolution / total_spoken_words >= 0.90` (inclusive boundary; `FAIL` when `< 0.90`, even if `S16`'s `690–720s` timeline window is valid).

     * Pin `BP-04` cumulative spoken-word validation (`engagement.resolution_word_share`) with **9 explicit unit tests** in `tests/unit/test_story_engine.py` and `tests/unit/test_engagement.py`: (1) resolution starts before 90% (`890 / 1000 = 0.890 < 0.90` -> `FAIL`); (2) resolution starts at exact 90% boundary (`900 / 1000 = 0.900 == 0.90` -> `PASS`); (3) resolution starts after 90% (`915 / 1000 = 0.915 > 0.90` -> `PASS`); (4) varying WPM across all 5 `BP-169` zones (`193/176/166/185/160` WPM); (5) mixed narrator VO + voiced character dialogue counted and `voiced: false` silent lines excluded; (6) exclusion of `line["tags"]`, inline `[tags]`, and non-spoken visual/scene metadata; (7) a script whose `S16` timeline window (`690–720s`) is valid but whose cumulative spoken-word share is `< 0.90` (`FAIL`); (8) a `/4` script with **no resolution marker** (`drama.function == "resolution"` absent) -> `FAIL` (no silent pass); and (9) `total_spoken_words == 0` -> `FAIL` without `ZeroDivisionError`.

  5. **Narration Lint (`narration_lint.py`)**:

     * In `doc_findings(doc)`, when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, check each segment's median sentence length against `BP-169`'s `median_words_max` for its zone (`8 / 9 / 11 / 9 / 7` words) and verify intra-zone sentence-length contrast (`std_words >= 2.0` on segments with `>= 4` sentences, `REVIEW`).

  6. **Rhythm Lint (`rhythm_lint.py`)**:

     * Allow `rhythm_lint.check(doc)` to accept a full `production_script/4` dict (flattening `segments[].shots` with estimated or timed `seconds` and `start_s`) in addition to `{shots: [...]}`.

* **Dependencies & Prerequisites**: `BATCH-M0`, `BATCH-M1`.

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/test_variant_plan.py tests/unit/test_story_engine.py tests/unit/test_rhythm_lint.py tests/unit/test_production_script_schema.py` passes with `0` failures.

* **Expected Outputs / Artifacts**: Updated upstream planners/linters supporting `/4` + `mrbeast_animated` while leaving `/1..3` + `calm_docudrama` untouched.

* **Risks & Recovery Paths**: Existing `napoleon_vs_genghis` variant tests use `calm_docudrama` (`BP-107` `11–17 shots/min`); defaulting `variant_plan.checks` to `calm_docudrama` unless `rhythm_profile == "mrbeast_animated"` guarantees zero breakage of `test_variant_plan.py`.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: A `/4` script and a `mrbeast_animated` variant pass `variant_plan`, `story_lint`, `narration_lint`, and `rhythm_lint` with `0` false-positive calm-era findings.

### 9.4 `BATCH-M3` — Writers' Room Agent Prompts, Skills & Documentation Adaptation

* **Objective & Scope**: Update the 10 affected `.claude/agents/*.md` pages, 10 affected `.claude/skills/*/SKILL.md` files, and 6 `docs/*.md` specifications so the AI agents design and write 12-minute Mold-driven episodes from the very first prompt rather than reformatting a calm script after the fact.

* **Exact Repository Files to Inspect or Change (`26` files)**:

  * **Agents (`10`)**: `.claude/agents/orchestrator.md`, `story-architect.md`, `scene-writer.md`, `beat-writer.md`, `performance-director.md`, `edit-planner.md`, `voice-caster.md`, `shorts-writer.md`, `script-critic.md`, `shot-continuity-writer.md`.

  * **Skills (`10`)**: `.claude/skills/story-engine/SKILL.md`, `narration-script/SKILL.md`, `elevenlabs-voice/SKILL.md`, `dialogue-scenes/SKILL.md`, `visual-beats/SKILL.md`, `shot-visuals/SKILL.md`, `animation-principles/SKILL.md`, `editing-style/SKILL.md`, `video-editing-architect/SKILL.md`, `shorts-for-video/SKILL.md`.

  * **Docs (`6`)**: `docs/STORY_ENGINE.md`, `docs/SCRIPT_ENGINE.md`, `docs/PRODUCTION_SCRIPT.md`, `docs/NARRATION_AND_LANGUAGE_GUIDE.md`, `docs/EDITING.md`, `docs/AUDIO_SYSTEM.md`.

* **Agents & Prompts Affected**: All 10 episode-production agents and 10 skills listed in Section 5.

* **Required Implementation Changes**:

  1. Apply the exact per-agent and per-skill adaptations specified in Tables 5.1 and 5.2 (updating `15-minute` -> `12-minute (720s, BP-167)`, `production_script/3` -> `production_script/4`, `Oxley` -> `Odom` + `narrator_polish.py`, `BP-01` flat `170 WPM` -> `BP-169` 5-zone WPM + intra-zone variation, `AB01..AB12` anchor beats, 3-Tier Still Motion Ladder, Bounded Timeline Engine, and `5` Shorts default).

  2. Preserve all `OR-32` `stage_guard start` / `fresh` command lines and `docs_lint.py` cross-reference markers (`<!-- sd-matrix:begin -->`, BP link syntax).

* **Dependencies & Prerequisites**: `BATCH-M1`, `BATCH-M2`.

* **Tests & Acceptance Criteria**:

  * `python -m explainer_engine.docs_lint` passes with `0` errors.

  * `pytest tests/unit/test_agent_roles.py tests/unit/test_agent_governance.py tests/unit/test_voice_route_docs.py` passes with `0` failures.

* **Expected Outputs / Artifacts**: Updated agent pages, skills, and docs aligned with Master Mold v2.1.0.

* **Risks & Recovery Paths**: `tests/unit/test_voice_route_docs.py` and `docs_lint.py` check specific strings and markdown links in `docs/` and `.claude/`; run both after every doc edit to catch any broken anchor immediately.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: `docs_lint` and all agent/doc unit tests pass (`0` errors).

### 9.5 `BATCH-M4` — Audio-First Timing, Zone Pause Padding, Odom Polish & `D-90` Character Voice Spine Wiring

* **Objective & Scope**: Ensure the audio pipeline (`hype_read.py`, `pause_pad.py`, `narrator_polish.py`, `spine.py`, `compile.py`, `production/__main__.py`) formats zoned TTS chunks properly, pads pauses at zone-appropriate widths (`0.18s` in hyped zones vs `0.26s` in calm middle), polishes Odom's narrator voice on all episodes (including dialogue episodes), and binds pre-recorded ElevenLabs character takes (`D-90`) into `audio_spine/2` before `edit/router.py` runs.

* **Exact Repository Files to Inspect or Change (`7` files)**:

  1. `explainer_engine/audio/hype_read.py`

  2. `explainer_engine/audio/pause_pad.py`

  3. `explainer_engine/audio/narrator_polish.py`

  4. `explainer_engine/audio/spine.py`

  5. `explainer_engine/production/compile.py`

  6. `explainer_engine/production/__main__.py`

  7. `tests/unit/test_hype_read.py`, `tests/unit/test_narrator_polish.py`, `tests/unit/test_audio_spine.py`

* **Agents & Prompts Affected**: `performance-director.md`, `voice-caster.md`, `edit-planner.md` (Step 4b Sound).

* **Required Implementation Changes**:

  1. **`compile.py` + `hype_read.py`**: In `compile.write_outputs(doc, out_dir)`, when `rhythm_profile.resolve_profile_name(doc) == "mrbeast_animated"`, format narrator lines for `narration_tts.txt` via `hype_read.format_line_for_tts` and split `tts_chunks.json` respecting `BP-171`'s `chunk_reset_max_chars` (`800`) and `chunk_reset_max_s` (`90.0s`) (`HR-04`).

  2. **`pause_pad.py`**: Allow `pad_pauses(words, audio, sr, min_gap=..., targets=..., zone_for_time=...)` to use `SR.T("BP-171", "hyped_min_gap_s")` (`0.18s`) for punctuated gaps falling inside `hyped` or `hyped_climax` zones while keeping `MIN_GAP = 0.26s` in `calm_story` (`middle_calm_90_480s`) and `calm_docudrama`.

  3. **`narrator_polish.py` + `production/__main__.py`**: Wire `polish_narrator_spans_in_place(out / "narration.wav", words, toks, doc)` at `production/__main__.py:119` (after `voice_check.check_speakers` on raw timbre and `pause_pad.pad_pauses`) so Odom's narrator spans receive the standard `+12 dB @ 150 Hz` `NP.CHAIN` on dialogue scripts (`S.has_dialogue(doc) == True`) while character dialogue spans remain unpolished.

  4. **`audio/spine.py` (`D-90` Character Take Binding)**: Add `bind_character_takes(spine: dict, takes: dict[str, Path], fps: int) -> dict` which measures each character `DIALOGUE_CU` take's exact frame count and SHA-256 (`contracts.sha256_file`), updates the corresponding `post_hoc_shots` entry to `source="clip"` and `clip_sha256=<hash>`, and shifts subsequent word/segment frames deterministically so `edit/router.py:_spine_window` succeeds before pod launch!

* **Dependencies & Prerequisites**: `BATCH-M0`, `BATCH-M1`.

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/test_hype_read.py tests/unit/test_narrator_polish.py tests/unit/test_audio_spine.py tests/unit/test_dialogue_and_shorts_set.py` passes with `0` failures.

  * New unit test `test_d90_character_take_binds_into_spine_and_routes_dialogue_cu` proves `spine.bind_character_takes` -> `edit/router.route` produces a valid `shot_spec/1` with `audio_slice_sha256`.

* **Expected Outputs / Artifacts**: Zone-aware TTS compilation, pause padding, narrator polish on dialogue scripts, and `D-90` pre-render spine binding.

* **Risks & Recovery Paths**: Polishing narrator audio before word-boundary dropout scanning (`dropouts.scan`) could alter RMS floor if not careful; keep `narrator_polish` after `voice_check` and `pause_pad` (exactly where PR #119 placed it for non-dialogue reads) and verify `abs(after - before) <= 1/30 s`.

* **Cost Classification**: **FREE** (`$0.00` — tested with synthetic/fixture WAVs on CPU).

* **Explicit Completion Gate**: `cmd_words`, `spine.py`, and `router.py` pass end-to-end on a multi-speaker `/4` fixture with `DIALOGUE_CU`.

### 9.6 `BATCH-M5` — Bounded Timeline Engine, 3-Tier Still Motion Ladder & Shot Router Integration (`WP-R7` Part 2)

* **Objective & Scope**: Implement the 6-step Bounded Timeline Engine (`explainer_engine/edit/bounded_timeline.py`), reconcile the 3-Tier Still Motion Ladder (`parallax_25d`, `qwen_nextpose`, `dramatic_still`) with `edit/dramatic_still.py` and `edit/router.py`, and wire `film_shots.py` to delegate zone rhythm checks to `rhythm_lint.py`.

* **Exact Repository Files to Inspect or Change (`9` files)**:

  1. `explainer_engine/edit/bounded_timeline.py` *(NEW)*

  2. `explainer_engine/edit/dramatic_still.py`

  3. `explainer_engine/schemas/dramatic_still.schema.json`

  4. `explainer_engine/edit/router.py`

  5. `explainer_engine/schemas/shot_route.schema.json`

  6. `explainer_engine/scripting/film_shots.py`

  7. `explainer_engine/schemas/film_shots.schema.json`

  8. `tests/unit/test_bounded_timeline.py` *(NEW)*

  9. `tests/unit/test_dramatic_still.py`, `tests/unit/test_film_shots.py`, `tests/unit/test_shot_router.py`

* **Agents & Prompts Affected**: `edit-planner.md`, `shot-continuity-writer.md`.

* **Required Implementation Changes**:

  1. **Bounded Timeline Engine (`explainer_engine/edit/bounded_timeline.py`)**:

     * Implement the 6-step deterministic algorithm from Mold v2.1.0 (`§4.4`):

       * Step 1: Speech-clause (`UR-12`) + `1/f` duration proposal within `[-0.18, +0.18]`.

       * Step 2: Hard lane & zone clamp (`VIDEO` `<=8.0s` target / `<=10.0s` cap and `BP-172` zone clip bands; `STILL` `<= zone["still_max_s"]`; `HELPER` `<=7.0s` Kuleshov cap `BP-141`).

       * Step 3: Constrained slack-weighted projection onto exact integer frames at `24 fps` (`sum(frames) == segment_target_frames`, `17,280` total for `720.0s`).

       * Step 4: LTX-2.5 `8k+1` generation frame + `BP-128` handle (`4..12` frames) derivation for `VIDEO` shots (`ltx_frames = 8 * ceil((usable_frames + 8 - 1) / 8) + 1`).

       * Step 5 & 6: Diagnostic evaluation (`CV >= 0.20` per `BP-83`, `max_similar_run <= 3`) with local `±4`-frame transfer between adjacent same-lane shots when a segment's `CV < 0.20` or `similar_run > 3`.

  2. **3-Tier Still Motion Ladder (`dramatic_still.py`, `dramatic_still.schema.json`)**:

     * **Do not relax `BP-170` static hold caps for Tier 2 yet**: keep `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`) as the strict ceiling for **both Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`)** until a measurable visual-change metric for Tier 2 (masked subject pose delta + identity gate pass beyond mere `min_subject_area_frac = 0.08`) is validated and approved by the creator (`CD-03`).

     * Register `still_motion_tier` (`TIER_1_SHORT_PARALLAX_STILL`, `TIER_2_MEDIUM_STATE_SHIFT_STILL`, `TIER_3_LONG_DRAMATIC_RELOCATION_STILL`) in `film_shots.schema.json` and `production_script.schema.json`, allowing holds above `static_still_max_s_by_zone` (up to `5.0s`) **only** for Tier 3 (`cutout_relocation >= 0.25` or `plate_swap >= 0.30`).

  3. **Shot Router (`edit/router.py`, `shot_route.schema.json`)**:

     * For `STILL_HOLD` shots, include `still_motion` metadata (`tier`: `TIER_1` / `TIER_2` both capped at `static_still_max_s_by_zone` `1.5/2.0/2.5s`, or `TIER_3` up to `5.0s` with validated `dramatic_change` spec, plus second pose reference when `tier == "TIER_2_MEDIUM_STATE_SHIFT_STILL"`) in `shots/route.json` so `assemble.py` renders the still shot without relaxing `BP-170`.

  4. **Film Shots (`film_shots.py`, `film_shots.schema.json`)**:

     * In `episode_check(doc)`, when `rhythm_profile.resolve_profile_name(doc) != "calm_docudrama"`, call `rhythm_lint.check(doc)` instead of flat `BP-107` (`11–17 shots/min`) and check zone WPM against `BP-169`.

* **Dependencies & Prerequisites**: `BATCH-M1`, `BATCH-M2`, `BATCH-M3`, and `BATCH-M4` (`bounded_timeline.py` consumes `timed.json` and `audio_spine/2` produced by `BATCH-M4`, matching the Section 10 dependency DAG).

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/test_bounded_timeline.py tests/unit/test_dramatic_still.py tests/unit/test_film_shots.py tests/unit/test_shot_router.py` passes with `0` failures.

* **Expected Outputs / Artifacts**: `explainer_engine/edit/bounded_timeline.py`, updated `dramatic_still.py`, `router.py`, `film_shots.py`, and `tests/unit/test_bounded_timeline.py`.

* **Risks & Recovery Paths**: `test_sourced_rules.py` pins `BP-170` keys and `FAIL` severity; keep all existing `BP-170` threshold keys and `static_still_max_s_by_zone` (`1.5/2.0/2.5s`) completely intact for both Tier 1 and Tier 2. Do **not** introduce or activate any `tier_2_max_s: 3.5` rule unless quantitative masked pose-delta + identity validation (`KG-13`) thresholds are proven and explicitly approved by the creator (`CD-03`).

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: All 16 segments of a `/4` shot plan quantize to exact `24 fps` frame totals with `8k+1` LTX specs and route cleanly through `edit/router.py`.

### 9.7 `BATCH-M6` — Production, Three-Lane Assembly, Audio Layers, Sound Director, QA & Shorts Wiring (`WP-R9`, `WP-R10`, `WP-5a`)

* **Objective & Scope**: Complete `WP-R9`, `WP-R10`, and `WP-5a` by wiring zone semantics into `production/timing.py`, `beats.py`, `fill_holds.py`, `validate.py`, `edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, `audio/layers.py`, `audio/sound_director.py`, `qa/engagement.py`, `qa/scorecard.py`, and implementing 3-lane clip materialization (`VIDEO` via `finish/upscale.py`, `STILL` via `dramatic_still.py` / `parallax.py`, `HELPER` via `visual_compensator.py`) into `production/assemble.py`.

* **Exact Repository Files to Inspect or Change (`14` files)**:

   1. `explainer_engine/production/timing.py`

   2. `explainer_engine/production/beats.py`

   3. `explainer_engine/production/fill_holds.py`

   4. `explainer_engine/production/validate.py`

   5. `explainer_engine/production/assemble.py`

   6. `explainer_engine/edit/board.py`

   7. `explainer_engine/edit/motion_lint.py`

   8. `explainer_engine/edit/shot_rules.py`

   9. `explainer_engine/audio/layers.py`

  10. `explainer_engine/audio/sound_director.py`

  11. `explainer_engine/qa/engagement.py`

  12. `explainer_engine/qa/scorecard.py`

  13. `explainer_engine/production/shorts.py`

  14. `tests/unit/test_rhythm_end_to_end.py`

* **Agents & Prompts Affected**: `orchestrator.md`, `edit-planner.md`, `shorts-writer.md`.

* **Required Implementation Changes**:

  1. **`WP-R9` (`timing.py`, `beats.py`, `fill_holds.py`, `validate.py`, `board.py`, `motion_lint.py`, `shot_rules.py`)**:

     * Ensure `timed.json` carries `"rhythm_profile": rhythm_profile.resolve_profile_name(doc)` and per-shot `"rhythm_zone"`.

     * In `board.py`, `motion_lint.py`, `shot_rules.py`, `beats.py`, and `fill_holds.py`, when `timed.get("rhythm_profile") == "mrbeast_animated"`, read max still hold and shot rate from `rhythm_profile.zone_at_time` (`BP-169`) and `rhythm_lint.py` instead of `BP-40` (`10 pics/min`, `20s` body hold) and `BP-85`.

     * In `validate.py:check_script`, run `rhythm_lint.check(doc)` and `hype_read.check_prosody_plan`, check `PV-52` against `rhythm_profile.zone_wpm()`, and allow `5` Shorts in `PV-34` (`BP-167`).

  2. **`WP-R10` (`audio/layers.py`, `audio/sound_director.py`, `qa/engagement.py`, `qa/scorecard.py`)**:

     * In `audio/layers.py`, check `AL-02` against the zone's `sfx_events_per_min_band` (`BP-169`) on `mrbeast_animated` scripts.

     * In `audio/sound_director.py`, verify that at least one `BP-120` vacuum lands in `climax_660_720s` when `mrbeast_animated` is active.

     * In `qa/engagement.py` and `qa/scorecard.py`, compute word timing and `pace_verdict` using `rhythm_profile.words_to_seconds` and `BP-169` zone bands on `/4` scripts.

  3. **`WP-5a` Three-Lane Assembly (`production/assemble.py`)**:

     * Add `materialize_lane_clips(job: Path, route: dict, comp_manifest: dict | None, out_shots_dir: Path, size: tuple[int, int] = (2560, 1440))` which:

       * For `KEYFRAME_LTX`, `DIALOGUE_CU`, `ATMOS_BROLL` (`VIDEO` lane): runs `finish/upscale.upscale(raw_clip, out_shots_dir / f"{shot_id}.mp4", size=size)` if the raw clip is `1920x1088` (or not yet `size`).

       * For `STILL_HOLD` (`STILL` lane): renders the `duration_frames` frames at `fps` (`24`) using `dramatic_still.render_dramatic_still` (Tier 3), `render_nextpose_flip` (Tier 2), or `parallax.py` (Tier 1) and encodes `out_shots_dir / f"{shot_id}.mp4"` at `size`.

       * For `MAP` and `COMPENSATOR` (`HELPER` lane): renders the `duration_frames` frames via `visual_compensator.render_item_frame` and encodes `out_shots_dir / f"{shot_id}.mp4"` at `size`.

     * Then `assemble.build_video_v2` stitches all three lanes seamlessly with `BP-128` handles, `BP-129` whip transitions, `BP-130` Reinhard LAB colour-transfer clamping, and `export_otio`!

* **Dependencies & Prerequisites**: `BATCH-M0` through `BATCH-M5`.

* **Tests & Acceptance Criteria**:

  * `pytest tests/unit/` passes across the entire unit test suite.

* **Expected Outputs / Artifacts**: Unified 3-lane `2560x1440 @ 24 fps` assembly pipeline and zone-aware validation/QA across all modules.

* **Risks & Recovery Paths**: Rendering `2560x1440` frames in unit tests can be slow on CPU; allow `materialize_lane_clips` to take `size=delivery.size()` by default and a small test size (e.g. `(320, 180)`) in unit tests, matching `test_finish_upscale.py`.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: `WP-R7`, `WP-R9`, `WP-R10`, and `WP-5a` pass unit tests with `0` failures.

### 9.8 `BATCH-M7` — Free End-to-End Representative Story Validation & Pre-Pod Falsification Suite

* **Objective & Scope**: Build and run the comprehensive free end-to-end validation test (`tests/unit/test_mold_v2_1_full_pipeline.py`) over a representative 12-minute (`720.0s`) historical counterfactual episode (see Section 12 for full specification) and run the full repository test suite (`pytest -q -m "not system and not media"` + `docs_lint`).

* **Exact Repository Files to Inspect or Change (`2` files)**:

  1. `tests/unit/test_mold_v2_1_full_pipeline.py` *(NEW)*

  2. `tests/unit/test_rhythm_end_to_end.py` (extended)

* **Agents & Prompts Affected**: Verifies the contracts consumed and produced by all stages.

* **Required Implementation Changes**:

  * Implement `tests/unit/test_mold_v2_1_full_pipeline.py` exercising all 10 contract handoffs from `story_hypotheses/1` -> `script_variants/2` -> `production_script/4` -> `words.json` -> `timed.json` -> `audio_spine/2` -> `film_shots/2` -> `shot_route/1` & `shot_spec/1` -> `visual_comp_manifest/1` & `dramatic_still` -> `sound_mix_manifest/2` -> `materialize_lane_clips` & `build_video_v2` -> `qa_report/1` & `scorecard.json` -> `shorts` plan.

* **Dependencies & Prerequisites**: `BATCH-M0` through `BATCH-M6`.

* **Tests & Acceptance Criteria**:

  * Full unit test suite (`2,450+` tests) + `docs_lint` + `palette` check pass with `0` failures.

  * The deterministic 60.0-second 2-zone (`S01` `0–30s` + `S15` `660–690s` remapped to contiguous local `0.0–60.0s`) CPU assembly test in `test_mold_v2_1_full_pipeline.py` executes real audio/video rendering and asserts:

    * `fps == 24`

    * `video_frames == 1440`

    * `video_duration_s == 60.0`

    * `audio_duration_s == 60.0` (`audio_samples == 2880000` at `48000 Hz`, zero unintended padding or truncation)

    * `narrator_chunks_polished is True` and `character_chunks_polished is False`

    * `vacuum_rms_dbfs <= -65.0` across `local_t in [58.5, 59.5]` (`BP-120` climax silence vacuum).

* **Expected Outputs / Artifacts**: Green CI proof that the entire Master Mold v2.1.0 architecture works end-to-end on CPU for `$0.00`.

* **Risks & Recovery Paths**: Any contract mismatch surfaced by the end-to-end test is fixed in `BATCH-M5`/`M6` before any paid step is ever proposed.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: `test_mold_v2_1_full_pipeline.py` and full CI quality workflow pass (`0` FAIL).

### 9.9 `BATCH-M8A` — Free Governance Closure, PR #112 Closure & Pre-Pod Dry-Run (`FREE`, `$0.00`)

* **Objective & Scope**: Complete all remaining **zero-cost** governance and pre-pod readiness tasks without launching any GPU pod or paid API call: close the formal governance status rows for `P6–P11` and `P12a` (`python -m explainer_engine.governance status --write`), close superseded [PR #112](https://github.com/vano1919/explainer-engine/pull/112) (after `CD-07`), align the `xworld_v2` LoRA strength across `cloud_pins.json` / `p12b.json` / `style_prompt.py` (after `CD-02`), pin final commit SHAs in `p12b.sh`, and pass `python -m explainer_engine.cloud.dryrun` (`0 FAIL`, `$0.00`).

* **Exact Repository Files to Inspect or Change (`7` files)**:

  1. `docs/blueprint/routing_log.jsonl`

  2. `docs/blueprint/phases.json` (via `governance status --write`)

  3. `docs/blueprint/STATUS.md` (via `governance status --write`)

  4. `config/cloud_pins.json` (if `CD-02` locks `0.7` or `1.0`)

  5. `explainer_engine/training/pods/p12/p12b.json` (if `CD-02` locks `0.7` or `1.0`)

  6. `explainer_engine/qa/style_prompt.py` (if `CD-02` locks `0.7` or `1.0`)

  7. `explainer_engine/training/pods/p12/p12b.sh` (final SHA pins)

  *(Note on Cost Classification: uploading the \~200 KB P12 Python code bundle to the existing private Hugging Face dataset `vano1919/tmr-artifacts` uses the free HF Hub Git/HTTP API under `D-73` and incurs `$0.00` in storage or compute charges.)*

* **Dependencies & Prerequisites**: `BATCH-M7` green (`CD-07` for closing PR #112; `CD-02` for locking LoRA weight before P12 bundle upload). Does **not** require an `OR-23` paid pod approval or any paid spend.

* **Tests & Acceptance Criteria**:

  * `python -m explainer_engine.governance status --check` passes with `0` drift.

  * `python -m explainer_engine.cloud.dryrun` passes with `0` FAIL.

  * `python -m explainer_engine.docs_lint` passes with `0` findings.

* **Cost Classification**: **FREE** (`$0.00`).

* **Explicit Completion Gate**: `governance status --check` and `cloud.dryrun` both return exit code `0` (`$0.00` spent).

### 9.10 `BATCH-M8B` — Creator-Gated Paid Execution (`4` Parent Gate Groups `GATE-P1..P4` / `5` Independently Authorized Operational Stages `GATE-P1a`, `GATE-P1b`, `GATE-P2`, `GATE-P3`, `GATE-P4`)

* **Objective & Scope**: Execute paid GPU benchmarks and Episode 1 production through **four parent gate groups (`GATE-P1`..`GATE-P4`) comprising five independently authorized operational stages (`GATE-P1a`, `GATE-P1b`, `GATE-P2`, `GATE-P3`, `GATE-P4`)**. **Critical Spending Authority Invariant**: A budget ceiling in `config/spend_caps.json` is **not** an authorization to spend, and approval for one operational stage **never** authorizes the next; every paid stage requires its own pre-spend creator `"YES"` on a service-specific cost table (`Standing Order 10` / `OR-23`), a bounded `Run` ledger (`core/ledger.py` with `STOP_FRACTION = 0.8` 80% stop and `MAX_FAILURES = 3`), and an active `OR-36` Haiku watchdog thread:

  1. **`GATE-P1` (`P12b` Micro-Benchmark Pods — Two Independently Authorized Paid Pod Stages)**:

     * **`GATE-P1a` (Pre-Spend Authorization #1 — Stage M Measurement Pod)**: Measures exact RunPod SECURE download/setup speed (`paid_tests.p12b_measure.runpod_usd = $0.63` ledger reservation; `$0.50` pod hard cap in `p12b.json`). Requires `cloud.dryrun` PASS + `OR-23` pod plan + standalone creator `"YES"` + `OR-36` watchdog.

     * **`GATE-P1b` (Pre-Spend Authorization #2 — Combined Qwen + LTX-2.5 Pod `Q1–Q3`, `L1–L3`)**: Runs only after `GATE-P1a` settles (`paid_tests.p12b_two_runs.runpod_usd = $3.00` ledger reservation; `$2.40` pod hard cap). Requires measured Stage M speed + fresh `OR-23` pod plan + standalone creator `"YES"` + `OR-36` watchdog. Updates `config/job_speeds.json` and `docs/COST_AND_TIME_MODEL.md` and evaluates `BP-168` (`Go / Pivot / Abandon`).

  2. **`GATE-P2` (Pre-Spend Authorization #3 — Episode 1 Voice Auditions & Two-Part Sample Generation `OR-19`, `D-67`)**:

     * **Pre-Spend Scope Distinction**: In `explainer_engine/production/sample.py` (`OR-19`) and `standards/hook.py`, paid voice reads and pictures/clips for the **two-part sample** run *before* `sample.py approve` (which is the post-render review gate). Therefore, `GATE-P2` is the **mandatory pre-spend authorization** covering:

       * (a) Stage 5 character voice auditions bounded by `casting.casting_credits_max = 1,500` credits (`voice_audition.py`), plus Odom's first sample read to populate `channel_voices.json` `baseline`; and

       * (b) Generating the voice reads and visual clips **strictly for the 2-part sample segments** (`sample.py:scope_segments` defaults to `["S01", "S02"]`; if the creator chooses `["S01", "S15"]` Hook + Climax as the 2-part sample, `{"scope_segments": ["S01", "S15"]}` must be written to `sample_approval.json` *before* paid generation starts so `standards/hook.py` and `PP-09` permit `S15` and block `S02..S14, S16`!).

     * **Enforced Caps & Guards**: Requires `CD-09` topic, Script Approval #1 (`PV-53`), `editorial_gate` `0 FAIL` (`OR-10`), `standards gate --at paid_assets` (`OR-12`), opening `run.json` (`Run.open`) with explicit sample-only caps (`elevenlabs_credits <= 3,500`, `runpod_usd <= $4.50`, `MAX_FAILURES = 3`, 80% stop), `OR-23` pod plan, standalone creator `"YES"`, and `OR-36` watchdog.

  3. **`GATE-P3` (Post-Render Sample Quality Sign-Off #4 — `production/sample.py approve`, `$0.00` Review Gate)**:

     * After the 2-part sample authorized in `GATE-P2` is rendered and stitched, all paid tools halt at Gate `6.5` (`production_gate.py:130`, `standards/hook.py:114`).

     * The creator watches the stitched sample video and either (a) approves it via `python -m explainer_engine.production.sample approve <folder> --by <creator> --ref <msg> --video <sample.mp4>` (binding `sample_approval.json` to `script_sha256`), or (b) requests revisions (any paid re-read or re-render exceeding the `GATE-P2` sample ledger requires a fresh pre-spend creator `"YES"`).

  4. **`GATE-P4` (Pre-Spend Authorization #5 — Episode 1 Full Remaining Production Run `S03..S16` + `5` Shorts)**:

     * **Multi-Service Budget Requirement**: Inspection of `config/spend_caps.json` (`per_episode`) shows ceilings for `runpod_usd: $31.00`, `gemini_usd: $10.00`, `bfl_usd: $3.00`, and `fal_usd: $9.00`, but **no `per_episode.elevenlabs_credits` line** (`casting_credits_max = 1,500` is for auditions only, and `allowances.qa_loop = 2,000` is a sub-allowance inside the run's `elevenlabs_credits` cap). A 12-minute (`~2,066`-word, `~12,500`-char) episode plus `5` Shorts and `D-90` character lines requires `~18,000–25,000` ElevenLabs credits.

     * **Enforced Caps & Guards**: Before any full-episode TTS or GPU call runs after `GATE-P3`, `GATE-P4` requires opening `run.json` (`Run.open(path, caps={"runpod_usd": 31.0, "elevenlabs_credits": <creator_approved_cap_e.g._25000>})`) so `core/ledger.py` enforces the 80% stop (`STOP_FRACTION = 0.8`) and `MAX_FAILURES = 3` on **both** RunPod USD and ElevenLabs credits, backed by a fresh `OR-23` pod plan, standalone creator `"YES"` on the combined full-episode cost table (`Standing Order 10`), and continuous `OR-36` Haiku watchdog monitoring.

* **Exact Repository Files Updated After Paid Measurements (`3` files, creator-gated)**:

  1. `config/job_speeds.json` & `docs/COST_AND_TIME_MODEL.md` (after `GATE-P1b`)

  2. `config/channel_voices.json` (Odom `baseline` after `GATE-P2`)

  3. `config/spend_caps.json` (only if creator adjusts episode cap in `CD-05` before `GATE-P4`)

* **Dependencies & Prerequisites**: `BATCH-M8A` green + separate explicit creator `"YES"` at each of `GATE-P1`, `GATE-P2`, `GATE-P3`, and `GATE-P4`.

* **Cost Classification**: **CREATOR APPROVAL REQUIRED / PAID** (strictly bounded by `config/spend_caps.json` per-gate caps).

* **Explicit Completion Gate**: Each of `GATE-P1`..`GATE-P4` closes only upon creator sign-off and verified `Run` ledger settlement within cap.

## 10. Dependency Graph & Critical Path

```
                       ┌──────────────────────────────────────────────────────────┐
                       │   Baseline Branch: planning/master-mold-integration      │
                       │   (from PR #119 HEAD: 5013a55aca5a17a3734150f61a5eb172)  │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                       ═════════════╪═════════════
                                        PRE-IMPLEMENTATION GATES:
                                        • CD-01 (Kickoff Approval)
                                        • GATE-EXT-MAIN-PROTECT (RSK-06:
                                          GitHub main branch protection)
                                       ═════════════╪═════════════
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M0 (FREE, P0 BLOCKER FIXES)                        │
                       │ • scripting/schema_version.py (is_scene_script /3,/4)        │
                       │ • Fix 10 modules checking == "production_script/3"       │
                       │ • Chunk-level Odom narrator_polish before join_reads      │
                       │ • Propagate rhythm_zone in film_shots.compose (KP-47)    │
                       │ • Cherry-pick PR #112 claude_api.load_job 2-line fix     │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M1 (FREE, CANONICAL MOLD CONTRACT & RECONCILIATION)│
                       │ • Resolve M-01..M-05 (Zone IDs, D-59 refs, AB07..12)     │
                       │ • config/master_mold_v2_1.json + docs/MASTER_MOLD_V2_1.md│
                       │ • schemas/episode_mold.schema.json + mold_contract.py    │
                       │ • ZONE_ALIASES in rhythm_profile.py + rehook_tts_tags    │
                       └──────────────┬─────────────────────────────┬─────────────┘
                                      │                             │
                    ┌─────────────────▼────────────────┐            ▼
                    │ BATCH-M2 (FREE, UPSTREAM LINTS)  │   ┌──────────────────────────────────────┐
                    │ • variant_plan.py (BP-169 zones) │   │ BATCH-M4 (FREE, AUDIO & D-90 SPINE)  │
                    │ • story_lint.py (AB01..12, zones)│   │ • compile.py + hype_read.py chunking │
                    │ • narration_lint.py (zone words) │   │ • pause_pad.py (0.18s hyped gap)     │
                    │ • fan_brief.py + hypotheses.py   │   │ • spine.py:bind_character_takes(D-90)│
                    └─────────────────┬────────────────┘   └──────────────────┬───────────────────┘
                                      │                                       │
                    ┌─────────────────▼────────────────┐                      │
                    │ BATCH-M3 (FREE, AGENTS & SKILLS) │                      │
                    │ • Update 10 .claude/agents/*.md  │                      │
                    │ • Update 10 .claude/skills/*.md  │                      │
                    │ • Update 6 docs/*.md + docs_lint │                      │
                    └─────────────────┬────────────────┘                      │
                                      │                                       │
                                      └───────────────────┬───────────────────┘
                                                          │
                                                          ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M5 (FREE, TIMELINE ENGINE & STILL MOTION LADDER)   │
                       │ • edit/bounded_timeline.py (±18% clause + 8k+1 + handles)│
                       │ • edit/dramatic_still.py (3-Tier Still Motion Ladder)    │
                       │ • edit/router.py + film_shots.py (zone & still routing)  │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M6 (FREE, WP-R9, WP-R10 & WP-5a 3-LANE ASSEMBLY)   │
                       │ • Wire zone semantics into timing, beats, fill_holds,    │
                       │   validate, board, motion_lint, shot_rules               │
                       │ • Wire zone audio/QA into layers, sound_director,        │
                       │   engagement, scorecard                                  │
                       │ • assemble.py:materialize_lane_clips + finish/upscale.py │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M7 (FREE, END-TO-END REPRESENTATIVE STORY SUITE)   │
                       │ • tests/unit/test_mold_v2_1_full_pipeline.py             │
                       │ • 60.0s (1,440 frames @ 24fps) deterministic CPU render  │
                       │ • Full 2,450+ unit test suite + docs_lint green          │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M8A (FREE, $0.00 GOVERNANCE & DRYRUN CLOSURE)      │
                       │ • Close P6-P11 & P12a status rows (governance status)    │
                       │ • Close PR #112 (CD-07) & lock LoRA weight (CD-02)       │
                       │ • Upload P12 code bundle + pass cloud/dryrun.py ($0.00)  │
                       └────────────────────────────┬─────────────────────────────┘
                                                    │
                                      ══════════════╪══════════════
                                       SEQUENTIAL PAID GATES (BATCH-M8B)
                                       (Each gate requires separate YES)
                                      ══════════════╪══════════════
                                                    ▼
                       ┌──────────────────────────────────────────────────────────┐
                       │ BATCH-M8B (PAID / SEQUENTIALLY CREATOR-GATED)            │
                       │ • GATE-P1: P12b Measure ($0.50 cap) & Combined ($2.40)   │
                       │ • GATE-P2: Ep 1 Odom + Cast Voice Sample (<=1500 creds)  │
                       │ • GATE-P3: Ep 1 Two-Part Sample Approval (OR-19)         │
                       │ • GATE-P4: Ep 1 Full Production ($31.00 cap + OR-36)     │
                       └──────────────────────────────────────────────────────────┘





```

## 11. Migration and Backward-Compatibility Strategy

### 11.1 Versioned Contract & Profile Dispatch Architecture

To introduce Master Mold v2.1.0 into [vano1919/explainer-engine](https://github.com/vano1919/explainer-engine) with **zero regression risk** to shipped episodes (`examples/stone_age/day1_v1..v5`, `Syndicate Wars`, `titans`) or existing calm animated examples (`examples/napoleon_vs_genghis/film_shots.json`), migration uses a **two-axis versioned dispatch**:

1. **Axis 1 — Schema Version (`scripting/schema_version.py`)**:

   * `version(doc, "production_script")`:

     * `1`: Legacy `/1` contract (optional beats, scenario approval is `REVIEW`).

     * `2`: `/2` contract (metronome visual beats `v2_target_s = 1.5s`, mandatory beat cues).

     * `>= 3` (`/3` and `/4`): Scene & dialogue era (`SC-01..12` binding, `ST-00` `drama` required, event-bound opt-in cues `VB-08`, `BP-93` word-anchoring, `PV-53` script approval, `PV-55`/`PV-56` living-person protections, `editorial_review/2` + `story_page.md`).

2. **Axis 2 — Rhythm Profile (`edit/rhythm_profile.py:resolve_profile_name(doc)`)**:

   * `"calm_docudrama"` (automatic default for `production_script/1..3` or any document that explicitly sets `"rhythm_profile": "calm_docudrama"`):

     * Runs the existing calm-era rules unchanged (`BP-01` `170 WPM`, `BP-107` `11–17 shots/min`, `BP-40` `10 pictures/min`, `BP-85` `UR-11` shot bands, `BP-49` `4–20 SFX/min`).

   * `"mrbeast_animated"` (automatic default for `production_script/4` and `BP-169`):

     * Activates the 5-zone Master Mold v2.1.0 rules (`BP-169` zone WPM, shot density, and SFX density; `BP-170` 3-Tier Still Motion Ladder via `dramatic_still.py`; `BP-171` zone prosody via `hype_read.py`; `BP-172` fast-action video prompts via `KP-47` and `LT-80`; `AB01..AB12` narrative anchor checks; and `edit/bounded_timeline.py`).

### 11.2 What Remains Operational During Every Migration Step & How Regressions Are Detected

* **Invariant 1**: Every existing test in `tests/unit/` (`2,448` passed tests in CI run `41345477655`) must pass after **every single batch (`BATCH-M0`..`BATCH-M7`)**.

* **Invariant 2**: `examples/napoleon_vs_genghis/film_shots.json` and `examples/napoleon_vs_genghis/script_variants.json` remain valid and tested by `test_film_shots.py`, `test_variant_plan.py`, and `test_rhythm_end_to_end.py`.

* **Invariant 3**: Any divergence between `config/master_mold_v2_1.json` and `explainer_engine/standards/sourced_rules.json` is immediately caught by `tests/unit/test_master_mold_contract.py` and `tests/unit/test_sourced_rules.py`.

## 12. End-to-End Validation & Smallest Pre-Paid Falsification Experiment

### 12.1 Free End-to-End Representative Test Story (`tests/unit/test_mold_v2_1_full_pipeline.py`)

Before spending `$0.01` on any API or GPU pod, `BATCH-M7` constructs and validates a complete, deterministic representative test story (`"The 1812 Neman River Crossing vs. 1223 Subutai Feigned Retreat"` — Profile `D_HISTORICAL_COUNTERFACTUAL_CLASH`, `720.0s`, `17,280` frames at `24 fps`, `16` segments `S01..S16`, `12` Anchor Beats `AB01..AB12`) across all **10 pipeline stages**:

| Step | Pipeline Stage Tested | Input Contract | Module Executed (Free CPU) | Output Contract & Assertions Verified | 
| ----- | ----- | ----- | ----- | ----- | 
| **1** | **Topic & Story Hypotheses** | `claim_map.md` + `story_hypotheses.json` (`story_hypotheses/1` with `mold_hooks`) | `research.hypotheses.check` + `research.fan_brief.check` | `0 FAIL`; `mold_hooks` provides `cold_promise_visual`, `180s` spike (`S06`), `360s` reversal (`S09`), and `recommended_profile_id: "D"`. | 
| **2** | **Priced Structure Variants (Stage 1b)** | `script_variants.json` (`script_variants/2` with Profiles `D`, `B`, `A` and `rhythm_profile: "mrbeast_animated"`) | `scripting.variant_plan.score` + `variant_plan.check_file` | `0 FAIL`; `60/30/10 ±5%` (`BP-109`), `BP-141` (`non_character_max <= 0.45` for D/A), `BP-142` (`turn_slots_D` played scenes), and `BP-169` shot density pass without triggering false `BP-107` warnings. | 
| **3** | **Approved Scenario & `/4` Production Script** | `scenario.md` + `production_script.json` (`production_script/4`, `16` segments `S01..S16`, `rhythm_zone` on each segment, `AB01..AB12` anchors, `Odom` narrator + 2 cast heroes) | `scripting.stage_guard` (all 7 stages) + `scripting.story_lint` + `scripting.scene_lint` + `scripting.narration_lint` + `scripting.register_lint` + `production.beats.lint` + `audio.hype_read.check_prosody_plan` | `0 FAIL` across all linters; negative test proves invalid `/4` script (missing `scene` header, real living person voiced, banned tag `[softly]` in `hook_0_30s`, or static `4.5s` still without `dramatic_change`) is caught with `FAIL` / `HR-01` / `RL-04`. | 
| **4** | **Script Compile & TTS Chunking** | `production_script.json` (`/4`) | `production.compile.compile_doc` + `compile.write_outputs` | Emits `narration.txt`, zone-tagged `narration_tts.txt` (`hype_read.format_line_for_tts`), and `tts_chunks.json` respecting `<=800` chars / `<=90s` (`BP-171`). | 
| **5** | **Audio Alignment, Zone Pause Pad, Odom Polish & Spine (`D-90`)** | Synthetic/fixture WAVs + `words_raw.json` + character `DIALOGUE_CU` take WAV | `production.__main__.cmd_words` (`pause_pad` `0.18s` hyped / `0.26s` calm + `narrator_polish` on Odom turns) + `production.timing.time_script` + `audio.spine.compile_spine` + `spine.bind_character_takes` | `timed.json` (`24 fps`, `17,280` frames) + `audio_spine.json` (`audio_spine/2`) with verified `clip_sha256` on `DIALOGUE_CU` post-hoc window (`CN-01`, `D-90`). | 
| **6** | **Bounded Timeline Engine & Film Shots (`film_shots/2`)** | `production_script.json` + `audio_spine.json` + `continuity_card/2` | `edit.bounded_timeline.quantize_episode` + `scripting.film_shots.check` + `film_shots.compose` + `scripting.rhythm_lint.check` | `0 FAIL`; `17,280` contiguous frames (`[0, 17280)`); all `VIDEO` shots carry `8k+1` LTX frames + `BP-128` handles (`4..12` frames) and pass `KP-47` (`BP-172`); all `STILL` shots satisfy the 3-Tier Still Motion Ladder (`BP-170`); `CV >= 0.20` and `max_similar_run <= 3` in all 16 segments. | 
| **7** | **Deterministic Shot Router (`P6`)** | `film_shots.json` (`film_shots/2`) + `audio_spine.json` + `visual_comp_manifest.json` | `edit.router.route` + `core.contracts.validate` | Emits `shots/route.json` (`shot_route/1`) and `shot_spec/1` files for `KEYFRAME_LTX`, `DIALOGUE_CU` (with `audio_slice_sha256`), and `STILL_HOLD` (with `still_motion` tier/spec), links `MAP` & `COMPENSATOR` items, and refuses `HOST_COMMENTARY` & `DRAMA_BLOCKED_3D` (`CN-11`). | 
| **8** | **Sound Director (`P4`)** | `audio_spine.json` + `timed.json` + `film_shots.json` | `audio.sound_director.plan` + `sound_director.check` + `audio.layers.check` | Emits `audio/sound_mix_manifest.json` (`sound_mix_manifest/2`) with `0 FAIL`, room tones (`BP-116`), J/L cuts (`BP-117`), spectral notch (`BP-118`), 3-layer hits (`BP-119`), `BP-120` climax silence vacuum (`688.5–689.5s`), and `BP-122` shot-size perspective EQ on diegetic sounds only. | 
| **9** | **Three-Lane Materialization, 2K Upscale & Assembly (`P7`)** | Stub `1920x1088` LTX clip + clean plates/cutouts + `visual_comp_manifest.json` + `edit_and_grade_manifest.json` | `finish.upscale` + `edit.dramatic_still.render_dramatic_still` + `edit.visual_compensator.render_item_frame` + `production.assemble.build_video_v2` + `build_audio_v2` + `export_otio` | Produces frame-accurate assembled video and stereo stems (`-14.0 LUFS`, `<= -1.0 dBTP`, `BP-50..52`) + valid `.otio` timeline with `0 FAIL` on `BP-128..130`. | 
| **10** | **QA Scorecard, Traceability & Shorts (`P8`, `P9`)** | Assembled job directory | `qa.engagement.check` + `qa.scorecard.run` + `qa.retry_router` + `production.shorts` / `clip_shorts` | `0 FAIL`; full SHA-256 provenance chain traced from `job_manifest.json` -> `production_script/4` -> `config/master_mold_v2_1.json` -> `film_shots/2` -> `shot_route/1` -> `sound_mix_manifest/2` -> final master & `5` `1440x2560 @ 24 fps` Shorts. | 

### 12.2 Smallest Realistic Pre-Paid Falsification Experiment (Before Full Episode Production)

Before committing budget to a full 12-minute episode (\~`120–152` LTX clips), what is the **smallest realistic experiment that can falsify the Master Mold v2.1.0 architecture**?

1. **Free CPU Falsification Experiment (`$0.00`, 2 minutes runtime — Run in `BATCH-M7`)**:

   * **What it tests**: Render a **60-second 2-zone slice (`S01` Hook `0–30s` at `28 shots/min` + `S15` Climax `660–690s` with the `688.5–689.5s` `-65 dBFS` audio vacuum)** using:

     * **Deterministic Source-to-Local 60.0s (`1,440`-Frame at `24 fps`) Timeline Remapping & Audio Composition**:

       * Episode Window A (`S01` Hook, episode source `[0.0s, 30.0s]`, source frames `[0, 720)`) maps identically to local `[0.0s, 30.0s]`, local frames `[0, 720)` (`720` frames).

       * Episode Window B (`S15` Climax, episode source `[660.0s, 690.0s]`, source frames `[15840, 16560)`) shifts by `-630.0s` (`-15,120` frames) into contiguous local `[30.0s, 60.0s]`, local frames `[720, 1440)` (`720` frames), yielding a contiguous `60.0s` (`1,440`-frame) local timeline:

         * **Fixture Provenance (`D-73` Vault vs. Offline CI)**: Repository inspection confirms that **zero `.wav`, `.mp3`, or `.mp4` files are tracked in Git** (`repo_5013a55a`); per `D-73`, the real `41.0s` Odom `eleven_v4` take, the 2 Raymond Verne takes (`a01c5ca`), and the LTX-2.5 clips reside in the private Hugging Face dataset `vano1919/tmr-artifacts`, while Git unit tests (`test_narrator_polish.py`, `test_assemble_v2.py`, `test_finish_upscale.py`) generate deterministic `numpy` / `ffmpeg lavfi` media in `tmp_path`. Accordingly, the `BATCH-M7` 60.0s test runs deterministically in **two modes**: (a) **Offline CI Mode (default in `pytest`)**, which synthesizes exact `48,000 Hz` `numpy` speech-band WAVs (`110 Hz + 2000 Hz` for Odom narrator chunks so `narrator_polish` bass lift `> +6 dB` at `110 Hz` is measurably asserted; `220 Hz + 1500 Hz` for Raymond Verne character chunks so `0.0 dB` change at `220 Hz` proves character audio was not polished!) and `ffmpeg lavfi` `1920x1088 @ 24 fps` source clips; and (b) **Vault Replay Mode (`--vault-dir` after `vault pull`)**, which runs the exact same 60.0s pipeline over the real HF `vano1919/tmr-artifacts` recordings:

         1. `local 0.0–30.0s` (source `S01` `0.0–30.0s`, frames `0..719`, `30.0s`): first `30.0s` of the `41.0s` Odom narrator read, pause-padded at `0.18s` (`hyped_min_gap_s`) and polished via `polish_narrator_spans_in_place`.

         2. `local 30.0–41.0s` (source `S15` `660.0–671.0s`, frames `720..983`, `11.0s`): remaining `11.0s` of the `41.0s` Odom narrator read, pause-padded at `0.18s` and polished via `polish_narrator_spans_in_place`.

         3. `local 41.0–58.5s` (source `S15` `671.0–688.5s`, frames `984..1403`, `17.5s`): Raymond Verne character dialogue turns (`D-90`, **left unpolished** — zero Odom EQ chain) + deterministic battle foley stems (`audio/foley.py`).

         4. `local 58.5–59.5s` (source `S15` `688.5–689.5s`, frames `1404..1427`, `1.0s`): `BP-120` pre-reveal silence vacuum (`<= -65.0 dBFS` across all stems).

         5. `local 59.5–60.0s` (source `S15` `689.5–690.0s`, frames `1428..1439`, `0.5s`): post-vacuum 3-layer impact hit (`BP-119`).

       * **Mandatory Programmatic Assertions on Rendered Output**: `fps == 24`, `video_frames == 1440`, `video_duration_s == 60.0`, `audio_duration_s == 60.0` (`2,880,000` samples at `48,000 Hz`, zero unintended padding or truncation), `narrator_chunks_polished is True`, `character_chunks_polished is False`, and `vacuum_rms_dbfs <= -65.0`. *(Note: `BATCH-M7` proves CPU contract/timeline/routing/assembly integration; real generative LTX prompt adherence, character identity stability, and lip-sync quality are falsified in `BATCH-M8B` `GATE-P1`'s paid `P12b` canary pod.)*

     * Real `visual_compensator.py` renders (`Archetype 2` `TACTICAL_UNIT_MANEUVER` map + `Archetype 5` `BALLISTIC_RANGE_AND_ENERGY_HUD`).

     * Real `dramatic_still.py` Tier 3 cutout relocation (`>=25%` shift) and Tier 1 `parallax.py` 3-layer depth push on existing `examples/napoleon_vs_genghis` / `assets/` keyframes.

     * Existing committed LTX test clips (`1920x1088 @ 24 fps`) upscaled via `finish/upscale.py` to `2560x1440 @ 24 fps`.

   * **Falsification Criterion**: If the 60-second assembled cut exhibits audio/video drift (`>1` frame), click artifacts at the `0.18s` padded pauses, muddiness from `narrator_polish.py` under `-10 dB` `124 BPM` music, or jarring visual seams between `finish/upscale.py` LTX clips and `dramatic_still.py` / `visual_compensator.py` frames at `2560x1440 @ 24 fps`, the assembly/audio parameterization is falsified and tuned **for `$0.00`** before launching any GPU pod!

2. **Paid GPU Falsification Experiment (`P12b` Combined Pod — `$0.50` Measurement + `$2.40` Hard Cap, Gated on Creator Approval)**:

   * **What it tests (`explainer_engine/training/pods/p12/p12b.json`)**:

     * Stage `M`: Exact download and setup wall-clock time on RunPod SECURE A40/A6000.

     * Stages `Q1–Q3`: Qwen-Image-2.1 + `xworld_v2` keyframe and multi-view generation speed and character consistency (`KG-01..23`).

     * Stages `L1–L3`: LTX-2.5 22B fast-action prompt adherence (`KP-47`, `73`-frame `3.0s` clip), plain i2v (`L1`) vs Layout-To-Render IC-LoRA (`L2` with `clay_video.py`) vs audio-conditioned `DIALOGUE_CU` lip-sync (`L3` with Raymond Verne ElevenLabs takes, `D-90`).

   * **Falsification Criterion (`BP-168`)**:

     * If LTX-2.5 22B clip generation time on the pod exceeds the budget envelope for `152` clips (e.g., if `152` clips x measured `s/clip` + retries exceeds `per_episode.runpod_usd = $31.00`), the Bounded Timeline Engine's adaptive shot-count knob (`shots_per_min_band` lower bound in `BP-169`: `24/20/14/22/26 shots/min` = `~185` total shots, `~110` LTX clips instead of `152`) is activated automatically without changing the 60/30/10 runtime share!

     * If `L3` audio-conditioned lip-sync (`DIALOGUE_CU`) fails `video_qa.py` (`LT-80` / lip-sync check), `qa/retry_router.py` automatically falls back to `FALLBACK_KEYFRAME_LTX` (narrator-framed reported speech per `D-63` or silent reaction cutaways per `BP-113`).

## 13. Cost Controls and Creator Approval Gates

### 13.1 Strict Cost Classification Across All Roadmap Batches

| Batch / Activity | Cost Classification | Service / Resource | Budget Cap in `config/spend_caps.json` | Required Approval Gate | 
| ----- | ----- | ----- | ----- | ----- | 
| **`BATCH-M0` .. `BATCH-M7`** (All code, schema, prompt, skill, doc, and CPU test work) | **FREE (`$0.00`)** | Local CPU / Git only | `$0.00` | `CD-01` kickoff approval + `GATE-EXT-MAIN-PROTECT` (`RSK-06` GitHub `main` branch protection). | 
| **60.0-Second (`1,440`-Frame) Pre-Pod CPU Assembly Falsification Test** | **FREE (`$0.00`)** | Local CPU (`ffmpeg`, `PIL`, `numpy`, committed fixtures) | `$0.00` | Included in `BATCH-M7` (`$0.00`). | 
| **`BATCH-M8A` (Governance Status Closure, PR #112 Closure & `cloud/dryrun.py`)** | **FREE (`$0.00`)** | Local CPU / Git / HF code bundle upload | `$0.00` | `BATCH-M7` green (`CD-07` before closing PR #112; `CD-02` before locking LoRA weight). Zero paid API/GPU spend. | 
| **`BATCH-M8B — GATE-P1a` (`P12b` Stage M Measurement Pod)** | **PAID (Standalone Creator Approval #1)** | RunPod SECURE GPU | Ledger reservation `paid_tests.p12b_measure.runpod_usd = $0.63`; pod hard cap `$0.50` (`p12b.json`) | `BATCH-M8A` (`cloud/dryrun.py` PASS) + `OR-23` pod plan + **Explicit Creator "YES" for `GATE-P1a`** + `OR-36` Haiku watchdog. | 
| **`BATCH-M8B — GATE-P1b` (`P12b` Combined Qwen + LTX-2.5 Pod `Q1–Q3`, `L1–L3`)** | **PAID (Standalone Creator Approval #2)** | RunPod SECURE GPU | Ledger reservation `paid_tests.p12b_two_runs.runpod_usd = $3.00`; pod hard cap `$2.40` (`p12b.json`) | Measured Stage M speed + `OR-23` pod plan + **Explicit Creator "YES" for `GATE-P1b`** + `OR-36` Haiku watchdog. | 
| **`BATCH-M8B — GATE-P2` (Episode 1 Voice Auditions + Two-Part Sample Generation `OR-19`)** | **PAID (Pre-Spend Creator Authorization #3)** | ElevenLabs (`eleven_v4`) + RunPod sample slice | Auditions `<= 1,500` credits (`casting_credits_max`); 2-part sample ledger cap (`elevenlabs_credits <= 3,500`, `runpod_usd <= $4.50`, 80% stop) | `CD-09` topic + Script Approval #1 (`PV-53`) + `paid_assets` stamp + `OR-23` plan + **Explicit Creator "YES" for `GATE-P2` pre-spend sample table** + `OR-36` watchdog. | 
| **`BATCH-M8B — GATE-P3` (Post-Render Two-Part Sample Quality Sign-Off `OR-19`)** | **FREE REVIEW GATE (`$0.00`)** | `python -m explainer_engine.production.sample approve` | `$0.00` (post-render review of `GATE-P2` sample; any paid re-render requires fresh pre-spend `"YES"`) | **Explicit Creator quality sign-off (`sample.py approve`, `GATE-P3`)** bound to `script_sha256` before `S03..S16` can be planned. | 
| **`BATCH-M8B — GATE-P4` (Episode 1 Full Remaining GPU & Voice Production)** | **PAID (Pre-Spend Creator Authorization #5)** | RunPod + ElevenLabs (`S03..S16` + `5` Shorts) | `per_episode.runpod_usd = $31.00` hard cap + explicit `run.json` `elevenlabs_credits` cap (e.g. `<= 25,000` credits, 80% stop, `MAX_FAILURES = 3`) | `GATE-P3` (`sample.py approve` PASS) + `OR-23` pod plan + **Explicit Creator "YES" for `GATE-P4` full-episode GPU + TTS cost table** + `OR-36` Haiku watchdog. | 

### 13.2 Ten Explicit Creator Decision Cards (`CD-01` through `CD-10`)

Nothing in this roadmap treats a research recommendation as a creator decision. The following `10` items are separated for the creator's word:

| Card ID | Decision Question | Current State in Repo (`5013a55a`) | Argon Technical Recommendation | When Needed | 
| ----- | ----- | ----- | ----- | ----- | 
| **`CD-01`** | **Implementation Kickoff & Branch**: Approve executing the free batches (`BATCH-M0..M7` and `BATCH-M8A`) on `planning/master-mold-integration-2026-11-02`? | Roadmap complete; `0` code files mutated yet. | **Approve `BATCH-M0..M7` + `BATCH-M8A` (all FREE, `$0.00`)** once `GATE-EXT-MAIN-PROTECT` (`RSK-06`) is verified. | **Before `BATCH-M0`** | 
| **`CD-02`** | **`xworld_v2` LoRA Strength (`0.7` vs `1.0`)**: `cloud_pins.json:103` has `0.7` (per 2026-10-31 brief), while `p12b.json` and `qa/style_prompt.py:25` have `1.0`. Which weight should be locked across all 3 files? | `0.7` in `cloud_pins.json`; `1.0` in `p12b.json` & `style_prompt.py`. | **Lock `0.7`** across all 3 files (or compare `0.7` vs `1.0` on 1 frame in `P12b`). Does **not** block `BATCH-M0..M7`. | **Before `BATCH-M8A` P12 bundle upload / `BATCH-M8B` `GATE-P1`** | 
| **`CD-03`** | **`BP-170` Still Motion Ladder Thresholds**: Confirm the coordinator's numeric thresholds in `BP-170` (`0.25` relocation distance, `0.08` area, `0.30` plate swap, `1.5/2.0/2.5s` static limits) and whether Tier 2 (`qwen_nextpose`) remains capped at `1.5/2.0/2.5s`? | Recorded in `BP-170.next_step` as awaiting creator confirmation. | **Keep Tier 1 and Tier 2 strictly capped at `1.5/2.0/2.5s` (`static_still_max_s_by_zone`)** in `BATCH-M5`; require creator approval (`CD-03`) + measured pose-delta & identity (`KG-13`) thresholds before any future Tier 2 hold extension. | **Before `BATCH-M5`** (for `BP-170` threshold confirmation; `BATCH-M5` defaults to strict `1.5/2.0/2.5s` cap) | 
| **`CD-04`** | **Intra-Zone Pace Variation Rule (`BP-169`)**: Confirm how code should check intra-zone pace variation (`std_words >= 2.0` per sentence and `>=15%` short `<=6`-word punch sentences inside each zone) as a `REVIEW` metric? | `BP-169.statement` notes frequency is open until sourced/confirmed. | **Confirm `REVIEW` check** (never hard `FAIL` while `status: "hypothesis"`) in `narration_lint.py` for `BATCH-M2`. | **Before `BATCH-M2`** | 
| **`CD-05`** | **Per-Episode GPU Cap (`config/spend_caps.json`)**: Keep `per_episode.runpod_usd = $31.00` until `GATE-P1` (`P12b`) measures real LTX-2.5 `s/clip`, or adjust now? | Protected config (`$31.00`). | **Keep `$31.00` unchanged during `BATCH-M0..M8A` and `GATE-P1..P3`**; revisit only before `GATE-P4` after `GATE-P1b` records real speeds in `config/job_speeds.json`. | **Before `BATCH-M8B` `GATE-P4`** (after `GATE-P1b`) | 
| **`CD-06`** | **Deceased Historical Figures Voicing (`D-90` / `PV-55`)**: `D-62` bans synthetic voices for *living* real people. May deceased historical figures (e.g., Napoleon, Subutai, Caesar) receive dramatized cast ElevenLabs voices under `D-90`? | Marked `OPEN` in `DECISIONS_AND_OPEN_QUESTIONS.md` row `D-90`. | **Yes for deceased historical figures** (`real_living_person: false`), keeping `D-62` (`PV-55`) strictly enforced (`FAIL`) for living real people. | **Before `BATCH-M4`** | 
| **`CD-07`** | **PR #112 Disposition**: After cherry-picking the 2-line `claude_api.load_job` fix + test in `BATCH-M0`, close stale Draft PR #112 on GitHub? | Open Draft PR #112 (`1` ahead, `29` behind `main`). | **Close PR #112 as superseded in `BATCH-M8A`** after `BATCH-M0` lands and tests the parser fix. | **Before `BATCH-M8A` PR #112 closure** (does not block `BATCH-M0..M7`) | 
| **`CD-08`** | **56 Stopped `0 GB` RunPod Pods (`keep_stopped_pods`)**: Keep the 56 legacy stopped pods (`$0.00/day`) listed in `spend_caps.json`, or prune them? | Listed in `spend_caps.json`; `D-92` auto-delete only deletes pods created *after* `D-92`. | **Leave untouched** (`$0.00/day`). | **Non-blocking** | 
| **`CD-09`** | **First 12-Minute Episode Topic Selection**: Which topic should enter Episode 1 production (`GATE-P2`..`GATE-P4`)? | Open (`TOPICS_2_ka.md` / Part I 60-Day Calendar). | Pick 1 flagship topic before Episode 1 production (`BATCH-M7` uses a self-contained deterministic CPU test fixture and does **not** wait on `CD-09`). | **Before `BATCH-M8B` `GATE-P2`** | 
| **`CD-10`** | **Channel Rebrand & Unlisted GTA 6 Video**: Execute the channel name/banner update and unlisted setting for the old GTA 6 video? | Open external YouTube Studio action. | Creator performs in YouTube Studio before publishing Episode 1 (external to code repo). | **Before Episode 1 YouTube upload** (non-blocking for code) | 

## 14. Risks, Unresolved Decisions, Explicit Assumptions, and Final Recommended Implementation Sequence

### 14.1 Risk Register & Mitigation Matrix

| Risk ID | Risk Description | Likelihood | Impact | Mitigation & Recovery Path | 
| ----- | ----- | ----- | ----- | ----- | 
| **RSK-01** | **Silent `/4` Validator Bypass**: Running a `production_script/4` episode before fixing the **11** `== "production_script/3"` checks (`CG-01`, including `production_gate.py:89`) would skip scene linting, script approval Gate `0.9`, living-person voice checks, and editorial review. | Certain (if unpatched) | **Critical** | Placed in **`BATCH-M0` (Step 1)** before any other work; pinned by regression test `test_schema_4_enforces_all_v3_scene_beats_silent_and_editorial_rules`. | 
| **RSK-02** | **LTX-2.5 Clip Count Exceeds Episode GPU Budget**: `152` LTX clips in the 254-shot reference grid could exceed `$31.00` if LTX-2.5 22B takes `>200s/clip` on RunPod. | Medium | **High** | 1) Measure real speed in `P12b` (`$0.50`/`$2.40` cap) first. 2) Because the 254-shot grid is `reference_only`, `bounded_timeline.py` can target the lower end of `BP-169`'s `shots_per_min_band` (`~185` total shots = `~110` LTX clips, `-28%` GPU cost) while still maintaining `60%` `VIDEO` runtime share (`BP-109`). | 
| **RSK-03** | **Odom Timbre Shift or Bass Muddiness Under Fast Music**: Adding `+12 dB @ 150 Hz` (`narrator_polish.py`) in hyped zones (`Z1`/`Z4`/`Z5`) where music sits at `-10 dB` could crowd the low-mid spectrum. | Low–Medium | **Medium** | `assemble.py:build_audio_v2` applies `BP-118` spectral presence dip and `BP-53` sidechain ducking on music/beds under the voice; verify in `BATCH-M7`'s free 60-second assembly test before paid reads. | 
| **RSK-04** | **`D-90` Character Lip-Sync Drift in LTX-2.5 (`DIALOGUE_CU`)**: LTX-2.5 audio-to-video conditioning (`Stage L3` in `P12b`) is unverified on cartoon faces. | Medium | **Medium** | Tested in `P12b` Stage `L3` on 2 pinned Raymond Verne takes (`97` credits already spent and uploaded at `a01c5ca`). If `L3` fails `video_qa.py`, `qa/retry_router.py` automatically falls back to `FALLBACK_KEYFRAME_LTX` + reported speech (`D-63`) or reaction cutaways (`BP-113`). | 
| **RSK-05** | **Duplicate Rule Numbers Breaking `D-59` Tests**: Committing a Mold JSON with raw copies of `BP-169` or `BP-109` numbers could violate the repository's single-home principle. | High (if copied raw) | **Medium** | `BATCH-M1` replaces duplicate threshold numbers in `config/master_mold_v2_1.json` with `canonical_bp_ref` pointers read dynamically from `standards/sourced_rules.json` via `scripting/mold_contract.py`. | 
| **RSK-06** | **Unprotected `main` Branch on GitHub (`main.protected = false`, `protection.enabled = false`)**: GitHub currently reports that `main` has branch protection disabled (`protected: false`), and the current automated agent environment does not hold GitHub repository admin permissions to enable branch protection via the API. | Medium | **High** | Elevate to **Explicit External Pre-Implementation Gate `GATE-EXT-MAIN-PROTECT`**: before the first implementation commit of `BATCH-M0`, the repository owner enables GitHub branch protection on `main` (**Require a pull request before merging**, **Require status checks to pass (`quality` CI)**, **Block force pushes**, and **Block direct pushes to `main` / Include administrators**), and every local session verifies `git branch --show-current == "planning/master-mold-integration-2026-11-02"`. | 

### 14.2 Explicit Assumptions

1. **\[ASSUMPTION A-01\]**: Branch [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02) is rooted at [PR #119](https://github.com/vano1919/explainer-engine/pull/119) HEAD (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`), which is 51 commits ahead and 0 commits behind `main` (`6e1dccad30a865df670c258c86ffa1152a0dbe7e`).

2. **\[ASSUMPTION A-02\]**: `main` remains frozen until after the next video ships (creator standing rule), enforced via external pre-implementation gate `GATE-EXT-MAIN-PROTECT` (`RSK-06`), and all implementation batches (`BATCH-M0..M7` and `BATCH-M8A`) will land on `planning/master-mold-integration-2026-11-02` via small, test-pinned commits.

3. **\[ASSUMPTION A-03\]**: No Claude API (`build_loop`), ElevenLabs TTS, or RunPod GPU money is spent during `BATCH-M0..M7` or `BATCH-M8A` (`$0.00` total); paid operations occur exclusively in `BATCH-M8B` behind the four separate, sequential creator approval gates (`GATE-P1`, `GATE-P2`, `GATE-P3`, `GATE-P4`).

### 14.3 Final Recommended Implementation Sequence (Step-by-Step Checklist)

 0. **Step 0 (`GATE-EXT-MAIN-PROTECT` & `CD-01`, External Pre-Implementation Prerequisite, `$0.00`)**: Repository owner enables GitHub branch protection on `main` (`Require pull request`, `Require status checks (quality)`, `Block force pushes`, `Block direct pushes to main` per `RSK-06`) and confirms `CD-01` kickoff on branch `planning/master-mold-integration-2026-11-02`.

 1. **Step 1 (`BATCH-M0`, Free, \~30 min)**: Create `explainer_engine/scripting/schema_version.py` (`is_scene_script` for `/3` and `/4`, `is_zoned_rhythm_script` for `/4`), fix all **11** `== "production_script/3"` modules (including `production_gate.py:89`), implement post-`voice_check` / post-`pause_pad` `polish_narrator_spans_in_place` in `audio/narrator_polish.py` and `production/__main__.py:119`, add `rhythm_zone` to `film_shots.schema.json` + `film_shots.compose()` (advancing `t_start_s` across all shots including `teaser_of`), cherry-pick PR #112's 2-line `claude_api.load_job` fix + test, and run `pytest`.

 2. **Step 2 (`BATCH-M1`, Free, \~45 min)**: Reconcile `M-01..M-05`, commit `config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `explainer_engine/schemas/episode_mold.schema.json`, and `explainer_engine/scripting/mold_contract.py`, add `ZONE_ALIASES` in `rhythm_profile.py` and `rehook_tts_tags` in `BP-169`/`hype_read.py`, and run `pytest tests/unit/test_master_mold_contract.py` + `docs_lint`.

 3. **Step 3 (`BATCH-M2`, Free, \~45 min)**: Update `fan_brief.py`, `hypotheses.py`, `variant_plan.py`, `story_lint.py`, `narration_lint.py`, `register_lint.py`, `rhythm_lint.py`, `production_script.schema.json`, and `stage_guard.py` for `/4` + `mrbeast_animated` + `AB01..AB12` anchors.

 4. **Step 4 (`BATCH-M3`, Free, \~60 min)**: Update the 10 `.claude/agents/*.md` pages, 10 `.claude/skills/*/SKILL.md` files, and 6 `docs/*.md` files (Tables 5.1 & 5.2), and verify `python -m explainer_engine.docs_lint` + `test_agent_roles.py`.

 5. **Step 5 (`BATCH-M4`, Free, \~45 min)**: Wire `compile.py` + `hype_read.py` chunking, zone-aware `pause_pad.py` (`0.18s` hyped gap), dialogue-safe `narrator_polish.py`, and `audio/spine.py:bind_character_takes` (`D-90`).

 6. **Step 6 (`BATCH-M5`, Free, \~60 min)**: Implement `explainer_engine/edit/bounded_timeline.py`, update `edit/dramatic_still.py` (3-Tier Still Motion Ladder), `edit/router.py` (`STILL_HOLD` motion routing), and `scripting/film_shots.py` (`rhythm_lint` delegation).

 7. **Step 7 (`BATCH-M6`, Free, \~60 min)**: Complete `WP-R9`, `WP-R10`, and `WP-5a` (`assemble.py:materialize_lane_clips` + `finish/upscale.py` + zone-aware `timing.py`, `beats.py`, `fill_holds.py`, `validate.py`, `board.py`, `motion_lint.py`, `shot_rules.py`, `layers.py`, `sound_director.py`, `engagement.py`, `scorecard.py`).

 8. **Step 8 (`BATCH-M7`, Free, \~45 min)**: Run `tests/unit/test_mold_v2_1_full_pipeline.py` and the deterministic `60.0s` (`1,440`-frame at `24 fps`) free CPU assembly falsification test (`S01` `0–30s` + `S15` `660–690s` remapped to `0.0–60.0s`); verify `video_frames == 1440`, `video_duration_s == 60.0`, `audio_duration_s == 60.0`, `fps == 24`, and confirm all `2,450+` unit tests and `docs_lint` pass with `0` errors.

 9. **Step 9 (`BATCH-M8A`, Free, `$0.00`, \~20 min)**: Close `P6–P11` and `P12a` status rows via `python -m explainer_engine.governance status --write`, close superseded Draft PR #112 (after `CD-07`), align `xworld_v2` LoRA strength (after `CD-02`), upload P12 code bundle to HF, and verify `python -m explainer_engine.cloud.dryrun` passes with `0` FAIL (`$0.00` spent).

10. **Step 10 (`BATCH-M8B`, Paid / 4 Parent Gate Groups `GATE-P1..P4` Comprising 5 Independently Authorized Operational Stages)**: Execute each operational stage **only** after its dedicated, standalone creator `"YES"` approval and with the `OR-36` Haiku watchdog active: `GATE-P1a` (`P12b` Stage M `$0.50` pod hard cap) -> `GATE-P1b` (`P12b` Combined `$2.40` pod hard cap) -> `GATE-P2` (pre-spend authorization for Stage 5 voice auditions `<=1,500` credits + 2-part sample generation `elevenlabs_credits <= 3,500`, `runpod_usd <= $4.50`) -> `GATE-P3` (`$0.00` post-render `sample.py approve` quality sign-off bound to `script_sha256`) -> `GATE-P4` (pre-spend authorization for Episode 1 full remaining production with `runpod_usd <= $31.00` hard cap and explicit `run.json` `elevenlabs_credits` cap).

## 15. Reverse-Engineering Compelling 12-Minute Animated Historical What-If & Docudrama Videos (Domains A–F, Verified 254-Shot Math & Source Correction Register)

**[FACT]** Before specifying any code change in §16, this section establishes the **forensically verified storytelling, documentary, audio, editing, and AI production architecture** for Argon's 12-minute (`720.0s`, `17,280`-frame) animated historical what-if and docudrama format. Every change in this revision satisfies a strict **two-part evidentiary rule**:
1. **Proof of Prior Misconception (`CURRENT MISCONCEPTION → VERIFIED CORRECTION`)**: Every modification explicitly demonstrates what was misunderstood in earlier drafts (`7312f660`), in the 214-page research compendium (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`), or in the un-reconciled Mold files (`2ca7f56f...` / `49cf3084...`).
2. **2–3 Independent Verifiable Primary Sources (`SOURCE 1`, `SOURCE 2`, `SOURCE 3`)**: Every corrected technical, scientific, or editorial rule is backed by **2 to 3 independent primary sources** (official standards, peer-reviewed studies, creator primary manuals, and exact repository file/line proofs in `repo_5013a55a.zip`).

### 15.1 Domain A — Storytelling First: Counterfactual Spine, Causal Escalation & Human Stakes

**[CRAFT-HEURISTIC]** / **[FACT]** Pacing, cut frequency, and camera motion cannot rescue a flat narrative spine. High-retention historical counterfactual and docudrama storytelling is governed by **causal progression, escalating human stakes, and delayed central resolution**:

1. **Counterfactual Divergence Contract (Historical Grounding -> Single Point of Divergence -> Constrained Extrapolation)**:
   * **Baseline Reality Anchor (`S01–S02`, `0–60s`)**: Every historical what-if or docudrama episode must first anchor the viewer in **verified historical fact** (`ZI-02` in `explainer_engine/scripting/film_shots.py:846–851` and `PV-37` Invariant 5 in `explainer_engine/scripting/claims.py:1–10`): a named episode-specific lead character (`D-89` no permanent hosts), an exact date/place, and a concrete physical object or ledger metric at stake (`BP-08` `ENG-3` in `explainer_engine/qa/engagement.py:64–73`).
   * **Single Point of Divergence (`AB02B`, `30–60s`)**: Rather than stacking multiple implausible assumptions, the script introduces **one bounded structural rule or historical hinge** in `S02` and traces its second- and third-order consequences using **`[FACT]`** (`claim_id`-backed records) and **`[HYPOTHESIS]`** (`HY-4` in `explainer_engine/research/hypotheses.py:66–68` requiring explicit mechanism + historical analogue).
   * **Why Speculative What-If Videos Fail (`5` Structural Failure Modes)**:
     1. *Encyclopedia Montage Syndrome*: Listing chronological facts (`"and then... and then..."`) instead of causal turns (`"because of X, Y was forced to Z — but when Z failed, therefore..."`, `ENG-2` in `qa/engagement.py:90–98`).
     2. *Abstract Macro-Statistics Without a Human Proxy*: Talking about "the economy" or "the empire" without grounding the cost in one character's survival, status, or ruin (`ZI-03`, `BP-08`).
     3. *Premature Thesis Spoilers*: Answering the central question in Act I or Act II instead of holding the central resolution until `>=90%` of spoken words have been delivered (`BP-04` `ENG-5` in `qa/engagement.py:162–172`).
     4. *Unfalsifiable Fantasy Jumps*: Violating physical logistics, weapon ranges, or institutional incentives without explaining *why* actors behaved that way (`HY-4`).
     5. *Flat Mid-Video Plateau (`180–480s`)*: Failing to plant a forward-pointing question or promise at least every `90s` (`BP-42` `ENG-7` in `qa/engagement.py:120–134`, `AB05` at `175–210s` `S06` and `AB07` at `330–375s` `S09`).

2. **Twelve-Anchor Narrative Architecture (`AB01..AB12`) Mapped to `S01..S16` (`720.0s`)**:
   * **[RECOMMENDATION]** Reconciling `mrbeast_12min_master_mold.md` (§3.4), `mrbeast_12min_video_mold (1).json` (`segments_summary_16`), `BP-169`, `BP-142`, and `BP-04` yields the canonical 12-anchor narrative spine (note that per `D-94`, retention/engagement checks remain `REVIEW` severity unless backed by a binding rule such as `BP-43` `FAIL` on sign-off fluff or `BP-142` `FAIL` on played turn scenes):

| Anchor ID | Canonical Name | Segment(s) & Exact Mold Window (`s`) | Rhythm Zone (`BP-169`) | Causal Story Function & Human Stakes Requirement | Canonical Repository Rule & Validator Hook |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **`AB01`** | **Thumbnail & Title Promise Payoff** | `S01` (`0.0–15.0s` inside `0.0–30.0s`) | `hook_0_30s` | Confirm the exact visual & verbal premise promised by the title/thumbnail in the opening lines (`<=14` cold-open words `BP-03`, `<=8` median words `BP-169`) while showing the protagonist in immediate physical motion. | `BP-03` (`FAIL`), `BP-04` (`85`-word `30s` contract, `REVIEW`), `BP-169` (`REVIEW`), `qa/engagement.py` (`ENG-1`) |
| **`AB02A`** | **Central Counterfactual Question & Stake Lock** | `S01` (`15.0–30.0s`) | `hook_0_30s` | Plant the overarching episode question within the first `85` words (`30s` at `170 WPM`, `BP-04`) plus `>=2` payoff teasers (`BP-111`) and quantify what the protagonist stands to win or lose (`BP-08`). | `BP-04` (`REVIEW`), `BP-08` (`ENG-3`), `BP-111` (`REVIEW`) |
| **`AB02B`** | **Baseline World & Single Rule of Divergence** | `S02` (`30.0–60.0s`) | `early_30_90s` | Establish the verified historical baseline (`claim_id` required by `ZI-02`/`PV-37`) and trigger the single structural rule or Point of Divergence (`HY-4`). | `ZI-02` (`FAIL`), `PV-37` (`FAIL`), `HY-4` (`REVIEW`), `story_lint.py` (`ST-25`) |
| **`AB03`** | **First Escalation & Commitment Lock-In** | `S03` (`60.0–90.0s`) | `early_30_90s` | The protagonist makes an irreversible choice under the new rule, closing the exit door and launching Act II (`BP-42` forward-pointing promise). | `BP-42` (`ENG-7` `REVIEW`), `story_lint.py` (`ST-25`) |
| **`AB04`** | **Systemic Expansion & Played Scene Turn #1** | `S04–S05` (`90.0–175.0s`: `S04` `90–135s`, `S05` `135–175s`) | `middle_calm_90_480s` | Breathe into the world mechanics (`166` heard WPM target); play out `S04` (`BP-142` turn slot `4`) as a multi-speaker or acted scene turn (`ST-24` / `VP-08`), then reveal the first hidden flaw in `S05`. | `BP-142` (`turn_slots_D: 4`, `FAIL`), `BP-169` (`REVIEW`) |
| **`AB05`** | **3-Minute Re-Hook Spike #1 (`S06`)** | `S06` (`175.0–210.0s`) | `middle_calm_90_480s` (`rehook_spike: true`) | Resolve the Act I sub-question and immediately plant a darker complication (`BP-42` `rehook_at_s`, `BP-142` turn slot `6`), accompanied by a segment-scoped `[excited]` prosody lift (`M-02`). | `BP-42` (`REVIEW`), `BP-142` (`slot 6`, `FAIL`), `audio/hype_read.py` |
| **`AB06`** | **Institutional Friction & Contagion** | `S07` (`210.0–270.0s`) | `middle_calm_90_480s` | Show how secondary institutions react to the protagonist's move, multiplying the systemic risk (`ZI-02` grounded claims). | `ZI-02` (`FAIL`), `BP-42` (`REVIEW`), `story_lint.py` (`ST-25`) |
| **`AB07`** | **Midpoint Reversal & 6-Minute Re-Hook Spike #2** | `S08–S09` (`270.0–375.0s`: `S08` `270–330s`, `S09` `330–375s`) | `middle_calm_90_480s` (`S09` `rehook_spike: true`) | `S08` (`BP-142` slot `8`) builds to the false peak; `S09` shatters the protagonist's assumption at the midpoint (`40–60%` of script words per `BP-75` `ST-12`) and plants the second half's survival question. | `BP-75` (`ST-12` `REVIEW`), `BP-142` (`slot 8`, `FAIL`), `BP-169` |
| **`AB08`** | **Cascade Acceleration & No-Exit Squeeze** | `S10–S11` (`375.0–480.0s`: `S10` `375–430s`, `S11` `430–480s`) | `middle_calm_90_480s` | Dual played scene turns (`S10` slot `10` and `S11` slot `11`, `BP-142`): every attempted fix worsens the crisis, exhausting the final buffer. | `BP-142` (`slots 10, 11`, `FAIL`), `story_lint.py` (`ST-25`) |
| **`AB09`** | **Late-Third Surge & Threshold of Collapse** | `S12` (`480.0–540.0s`) | `late_third_480_660s` | Pacing accelerates to `late_third_480_660s` (`185` heard WPM target, `25.0` shots/min target in `BP-169`); local failure crosses into total systemic reckoning. | `BP-169` (`25.0` shots/min, `REVIEW`), `story_lint.py` (`ST-25`) |
| **`AB10`** | **Pre-Climax Crucible & False-Salvation Collapse** | `S13–S14` (`540.0–660.0s`: `S13` `540–600s`, `S14` `600–660s`) | `late_third_480_660s` | `S13` (`BP-142` final turn slot `13`) strips away the last escape route; `S14` (`600–660s`) crosses the **`90.0%` cumulative spoken word threshold (`BP-04`)** (`1,860 / 2,066` words = `90.0%` is reached at `~644.1s` inside `S14`, and `S14` ends at `1,909 / 2,066` words = `92.40%`). | `BP-04` (`ENG-5` `REVIEW`), `BP-142` (`slot 13`, `FAIL`), `qa/engagement.py` |
| **`AB11`** | **Climax I — The Irreversible Rupture & Pre-Reveal Vacuum** | `S15` (`660.0–690.0s`) | `climax_660_720s` | Preceded by the `0.8–1.2s` (`-42 dBFS`) pre-reveal acoustic vacuum (`BP-120`) and `0.5–1.0s` narrator silence (`BP-171`), `S15` delivers the climax payoff (`160` heard WPM target, `30.0` shots/min in `BP-169`, `92.40%–96.22%` cumulative words). | `BP-120` (`REVIEW`), `BP-171` (`REVIEW`), `BP-169` (`30.0` shots/min, `REVIEW`) |
| **`AB12`** | **Climax II — Final Synthesis & Abrupt Hard-Cut Ending** | `S16` (`690.0–720.0s`) | `climax_660_720s` | Delivers the final answer (`96.22%–100.0%` of spoken words, satisfying `BP-04` `answer_after_share >= 0.90`), bridges to the next episode world (`BP-106`), and ends abruptly (`BP-43` `FAIL` on any recap/goodbye lexicon in the last `10%` of words). | `BP-04` (`ENG-5` `REVIEW`), `BP-43` (`ENG-8` `FAIL`), `BP-106` (`FAIL`) |

### 15.2 Domain B — YouTube Reverse Engineering: 7 Benchmark Channels & 14 Video Case Studies (`CS-01..CS-14`) with Explicit Epistemic Boundaries

* **Prior Misconception Corrected (`CORR-01`)**: In the previous draft (`7312f660`), Table `15.2B` labeled the 14 benchmark video case studies (`CS-01..CS-14`) as `"direct video metadata & transcript measurements"` while quoting specific cut counts (`19–22` cuts) and WPM/ASL ranges without an attached frame-by-frame cut-count worksheet or transcript word-timestamp log, and listed `14:43` as the runtime of Oversimplified's *The French Revolution (Part 1)* (`CS-13`) when secondary catalogs list `~17:53` (Part 1) / `~14:43` (other episodes).
* **Verified Correction (`SOURCE 1`: [YouTube Help — Audience Retention](https://support.google.com/youtube/answer/9314415); `SOURCE 2`: [How to Succeed in MrBeast Production PDF](https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf); `SOURCE 3`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` `D-94`)**:
  1. Per `D-94` (`"The research file's own 'BINDING' labels mix source types ... so none of its numbers is binding here"`), qualitative structural patterns across the 7 channels and 14 videos are graded **`[CRAFT-HEURISTIC]`** / **`[VERIFIED-CREATOR]`**, while any quantitative cut-rate, ASL, or WPM figure extrapolated to Argon is explicitly tagged **`[HYPOTHESIS]` (`REVIEW`)** until logged with a reproducible `ffprobe`/`scdet` + `WhisperX` measurement sheet.
  2. Official [YouTube Audience Retention documentation](https://support.google.com/youtube/answer/9314415) defines four observable curve features—**Intro (`0–30s` retention share)**, **Top moments**, **Spikes**, and **Dips**—and does **not** mandate a universal `90s` re-hook timer, `180s/360s` pivot timestamp, or `90%` word-share rule; those are CrossWorld's house format design (`BP-04`, `BP-42`, `BP-169`).

#### Table 15.2A — Seven Benchmark Channels & What Argon Adopts vs Rejects

| Channel | Core Visual & Narrative Format | Structural & Craft Mechanics (`[VERIFIED-CREATOR]` / `[CRAFT-HEURISTIC]`) | What Argon Adopts (`mrbeast_animated` v2.1.0) | What Argon Explicitly Rejects |
| ----- | ----- | ----- | ----- | ----- |
| **1. MrBeast** ([Production Manual](https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf), [Colin & Samir Interview](https://www.youtube.com/watch?v=c8VcUnz3nVc)) | Live-action challenge/stunt spectacle with animated/CG establishing hooks | **0–30s Hook validation** of title/thumbnail promise; **1–3min transition** from spectacle to story; **3min & 6min re-hooks**; "wow factor" escalation; abrupt ending without housekeeping drag (`BP-43`). | 5-zone macro rhythm wave (`BP-169`); `AB01` title/thumbnail payoff in `<15s`; `S06` (`175–210s`) and `S09` (`330–375s`) re-hooks; zero outro fluff (`BP-43`). | Non-stop screaming host energy during `90–480s` historical explanation (`BP-169` drops Z3 to `166` WPM / `17.0` shots/min target). |
| **2. Fern** ([Simplicissimus / Fern Profile](https://www.youtube.com/watch?v=0eb4d3f22bI)) | 3D/2.5D stylized dark docudrama & forensic reconstruction | Cold-open in medias res at the moment of anomaly; atmospheric sound design bed (`BP-52` `10–15 LU` under voice); forensic camera push-ins onto maps/diagrams; deliberate silence drops before reveals (`BP-120`). | Cold-open sensory anomaly (`AB01`); forensic diagram/map inserts (`10%` `HELPER` lane `BP-109`); `BP-120` pre-reveal vacuum (`0.8–1.2s` at `-42 dBFS`). | Full-3D Blender environment rendering for every shot (violates `$31` GPU budget; Argon uses Qwen 2D + LTX-2.5 + 3-layer 2.5D parallax `BP-35`). |
| **3. Kurzgesagt – In a Nutshell** ([1200-Hour Pipeline Video](https://www.youtube.com/watch?v=uFk0mgljtns)) | Flat-vector 2D animated science & existential counterfactuals | **1,200+ hour** hand-illustrated pipeline where script lock precedes visual production; measured calm narration (`BP-01` `155–185 WPM`); leitmotif score; visual metaphors that concretize abstract numbers (`BP-08`). | Concrete visual proxy for every number (`BP-08` `ENG-3`); strict color script progression across acts (`compose/episode_look.py` `AC-17`); script lock before paid GPU spend (`D-67`). | Flat vector minimalist art style (forbidden by `LT-12`); uniform calm cadence during the `0–30s` hook (`mrbeast_animated` targets `193` heard WPM in `hook_0_30s`). |
| **4. The Infographics Show** ([What If the Roman Empire Never Fell?](https://www.youtube.com/watch?v=h3w1_2H22bI)) | High-volume 2D motion-comic explainer & military/historical what-ifs | Fast verbal hook; frequent character pose/state shifts so held frames do not freeze; explicit counterfactual question framing in the opening 30 seconds (`BP-04`). | Counterfactual question clarity (`BP-04`); Tier 2/Tier 3 character pose/cutout state flips on held stills (`BP-170`). | Generic flat rig assets, repetitive stock SFX loops, and shallow Wikipedia-summary scripts lacking primary `claim_id` citations (`ZI-02` / `PV-37`). |
| **5. AlternateHistoryHub** ([What If Germany Won WWI?](https://www.youtube.com/watch?v=kCEUZ4faCwU)) | Counterfactual geopolitical & historical timeline divergence essays | Explicit **Point of Divergence (PoD)** definition before extrapolating; second-order institutional analysis (alliances, logistics, demographics, trade routes) rather than pure battle outcomes. | Explicit `AB02B` Single Point of Divergence (`30–60s` `S02`); mandatory second-order institutional/economic causal chain (`HY-4`). | Static map-slide lectures (`>90s` pure map run violates `BP-141` `map_run_max_s: 90`) and informal essayist asides. |
| **6. Kings and Generals** ([Battle of Cannae 216 BC](https://www.youtube.com/watch?v=6i0a726P22A)) | Tactical & operational military history with animated terrain maps | Top-down and isometric **tactical map grammar**: terrain elevation first, supply lines second, unit blocks third (`BP-124`, `BP-125` `altitude_change_s: [4.0, 8.0]`); concise labels (`BP-27`, `BP-84`). | `HELPER` lane (`10%`, `BP-109`) tactical map altitude transitions (`BP-125`) and `<=26`-char labels (`BP-84`) during `middle_calm_90_480s`. | 25-minute encyclopedic campaign prologues before the inciting crisis begins (`AB01` starts inside the crisis at `0.0s`). |
| **7. Oversimplified** ([The French Revolution Part 1](https://www.youtube.com/watch?v=8qRZcXIODNU)) | High-contrast character-driven historical comedy/drama | **Cutout relocation & plate-swap punchlines** (`>=25%` screen shift on a hard beat); sharp contrast between rapid-fire escalating setup and sudden deadpan pause (`BP-170` Tier 3 mechanics). | Tier 3 `cutout_relocation` (`min_relocation_distance_frac: 0.25`) and `plate_swap` (`min_plate_swap_pixel_frac: 0.30`) mechanics (`BP-170`) for held `STILL` shots. | Slapstick stick-figure cartoon proportions and anachronistic gag humor (Argon's visual bible is grounded 2D cinematic docudrama). |

#### Table 15.2B — Fourteen Benchmark Video Case Studies (`CS-01` through `CS-14`: Qualitative Structural Mechanics `[CRAFT-HEURISTIC]` vs Quantitative Extrapolations `[HYPOTHESIS]`)

| ID | Channel & Video ([Verified URL]) | Qualitative Opening Hook Mechanic (`0–30s`, `[CRAFT-HEURISTIC]`) | Qualitative Mid-Video Pivot & Escalation Structure (`[CRAFT-HEURISTIC]`) | Audio/Visual Craft Pattern Observed (`[CRAFT-HEURISTIC]`) | Argon Rule Mapping & Quantitative Hypothesis Status (`[HYPOTHESIS]` / `REVIEW`) |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **`CS-01`** | **MrBeast** — [$456,000 Squid Game In Real Life!](https://www.youtube.com/watch?v=0e3GPea1Tyg) | Opens directly inside the recreated Red Light, Green Light arena, confirming the thumbnail and `$456,000` stake in the opening lines (`BP-03`, `BP-04`). | Pivots at each game boundary with an explicit player-count reduction and interpersonal micro-story before the next elimination wave. | Contrasts fast opening hook cutting with longer interpersonal reaction beats in the middle and rapid climax timers. | Grounds `AB01` (`S01` promise payoff) and `BP-169` `hook_0_30s` (`28.0` shots/min house target, `REVIEW`). |
| **`CS-02`** | **MrBeast** — [7 Days Stranded At Sea](https://www.youtube.com/watch?v=yhB3BgJyGl8) | Immediate physical peril on the open-ocean raft, establishing the 7-day survival clock and physical stakes before any setup exposition. | Uses day-boundary survival crises (storm, ration failure, shelter damage) as causal `"but / therefore"` turns rather than flat diary logs. | Alternates high-density storm/action sequences with quiet exhaustion holds where voice clarity dominates. | Grounds `BP-169`'s contrast between `hook_0_30s` / `late_third_480_660s` hyped zones and `middle_calm_90_480s`. |
| **`CS-03`** | **Fern** — [The Silk Road: The Rise and Fall of the Dark Net's First Drug Lord](https://www.youtube.com/watch?v=GpMP6Nh3FvU) | Cold-opens inside the San Francisco public library arrest of Ross Ulbricht, staging the physical laptop seizure needed to keep the encrypted drive unlocked. | Shifts from how the hidden marketplace operated (`HELPER` network diagrams) to the forensic trace that exposed him. | Measured dark narration over a sub-bass tension drone (`BP-52`), punctuated by foley hits (`BP-119`) and pre-reveal silence (`BP-120`). | Grounds `AB01` cold-open action, `BP-120` pre-reveal vacuum (`0.8–1.2s`), and `HELPER` forensic diagrams (`BP-109`). |
| **`CS-04`** | **Fern** — [How One Man Broke the World's Deadliest Prison](https://www.youtube.com/watch?v=F0eA9a_2vH4) | Starts with the physical spatial constraint of the cell and guard schedule, turning an architectural blueprint into a ticking puzzle box. | Uses spatial progress checkpoints (corridor -> roof -> perimeter) where each solved barrier triggers a new complication. | Slow camera push-ins (`BP-20..22`) with localized acoustic perspective (`near` dry claustrophobia vs `far` courtyard reverb, `BP-122`). | Grounds `BP-122` (`near`/`mid`/`far` acoustic perspective) and `compose/episode_look.py` (`AC-17`) lighting shifts. |
| **`CS-05`** | **Kurzgesagt** — [What If We Detonated All Nuclear Bombs at Once?](https://www.youtube.com/watch?v=JyECrGp-Sw8) | Poses the exact counterfactual question in sentence 1 (`BP-03`) and quantifies the global stockpile via a concrete visual proxy (`BP-08`). | Escalates scale in three distinct acts ("all bombs on cities" -> "one pile in the Amazon" -> "mining all uranium on Earth"). | Steady calm narration (`BP-01` `155–185 WPM`) with clear inter-phrase pauses so complex blast-radius visuals register before the next number lands. | Grounds `BP-08` (`ENG-3` visual number demonstration), `BP-01` (`170 WPM` baseline), and 3-act counterfactual escalation. |
| **`CS-06`** | **Kurzgesagt** — [The Egg - A Short Story](https://www.youtube.com/watch?v=h6fcK_fRYaI) | Opens with the protagonist's sudden death and an immediate two-character philosophical dialogue in an afterlife void. | Sustains retention through **played dialogue turns** (`BP-142`) and progressive color-palette transformations across acts. | Theatrical 3-layer parallax holds (`BP-35`) and an evolving musical leitmotif that peaks on the final synthesis (`AB11–AB12`). | Grounds `BP-142` played scene turns (`turn_slots_D`) and `compose/episode_look.py` (`AC-17`) act-level palette progression. |
| **`CS-07`** | **The Infographics Show** — [What If the Roman Empire Never Fell?](https://www.youtube.com/watch?v=h3w1_2H22bI) | Launches directly into the counterfactual premise, contrasting modern Europe with a surviving Roman state to hook curiosity (`BP-04`). | Divides the runtime into distinct historical eras (Medieval, Industrial, Space Age), re-asking how Roman institutions adapt at each century mark (`BP-42`). | Frequent visual state flips (character pose changes and map overlays) that prevent visual stagnation during exposition. | Grounds `BP-42` (`microhook_every_s`) and `BP-170` still state-change requirements while reinforcing Argon's stricter `ZI-02` claim grounding. |
| **`CS-08`** | **The Infographics Show** — [How Survival On The Titanic Worked (Hour By Hour)](https://www.youtube.com/watch?v=rs9w5bgtJC8) | Anchors the viewer on the exact iceberg-impact timestamp (`11:40 PM`) and passenger deck level, establishing an irreversible countdown clock. | Uses physical flooding compartments and lifeboat launch timestamps as an inexorable causal clock (`AB06..AB10`). | Combines cross-section ship diagrams (`HELPER` lane) with character survival vignettes (`VIDEO` and `STILL` lanes), accelerating in the final third. | Grounds timestamped countdown escalation (`S08..S14`) and `60/30/10 ±5%` (`VIDEO`/`STILL`/`HELPER`) lane orchestration (`BP-109`, `D-93`). |
| **`CS-09`** | **AlternateHistoryHub** — [What If Germany Won WWI? (Part 1)](https://www.youtube.com/watch?v=kCEUZ4faCwU) | Defines the exact **Point of Divergence** (avoiding unrestricted submarine warfare / US entry in 1917) in the opening setup (`AB02B`) rather than assuming magic victory. | Traces second-order institutional consequences: how a victorious Kaiserreich inherits an overextended Eastern European sphere (`Mitteleuropa`) and internal strain. | Relies on map border animations and historical plates, showing that counterfactual plausibility depends on **constraints and unintended consequences** (`HY-4`). | Directly grounds `AB02B` (`S02` Single Point of Divergence) and `HY-4` (`research/hypotheses.py`: mechanism + historical analogue). |
| **`CS-10`** | **AlternateHistoryHub** — [What If The Cold War Went Nuclear? (1983 Able Archer)](https://www.youtube.com/watch?v=g5rVD_g2d8A) | Opens on the real historical near-miss (`November 1983` NATO Able Archer exercise and Soviet high alert) before flipping the single communication hinge into full escalation. | Shifts at the midpoint from command bunkers (`Profile A/D`) to logistical and agricultural collapse across the Northern Hemisphere (`Profile B/C`). | Stark tonal shift from brisk geopolitical briefing (`late_third_480_660s`) to somber, slower-cadence aftermath (`climax_660_720s`). | Grounds `BP-141` Episode Structure Profiles (`A..D`) and `BP-169`'s `late_third_480_660s -> climax_660_720s` WPM deceleration (`185 -> 160` WPM). |
| **`CS-11`** | **Kings and Generals** — [Battle of Cannae 216 BC - Second Punic War](https://www.youtube.com/watch?v=6i0a726P22A) | Establishes the strategic crisis after Trebia and Trasimene, locking onto Hannibal's numerical disadvantage (`50,000` vs `86,400`, `BP-08`) as the central tactical puzzle. | Uses the phase-by-phase geometry of the double envelopment (convex center retreat -> cavalry flank rout -> encirclement) as a visual causal chain. | Camera altitude transitions (`BP-125` `altitude_change_s: [4.0, 8.0]`) from campaign map down to tactical blocks (`BP-124`), paired with metallic troop foley. | Grounds `BP-124`/`BP-125` map grammar and `BP-141` `Profile B` (`tactical hybrid`, `non_character_max: 0.80`). |
| **`CS-12`** | **Kings and Generals** — [Fall of Constantinople 1453](https://www.youtube.com/watch?v=M0n4Vw6tw4I) | Contrasts the Theodosian Walls with Mehmed II's super-bombard cannons, anchoring the siege in concrete engineering numbers (`claim_id`). | Midpoint reversal (`BP-75`) when the Golden Horn naval chain blocks the Ottoman fleet, forcing the overland portage of `70` ships across Galata. | Alternates wide geographic choke-point maps with close dramatic illustrations of breach defenses along a strict day-by-day siege timeline. | Grounds `ZI-02` / `PV-37` quantitative siege/engineering claim verification and `AB07` midpoint strategic reversal. |
| **`CS-13`** | **Oversimplified** — [The French Revolution (Part 1)](https://www.youtube.com/watch?v=8qRZcXIODNU) *(Note: Part 1 catalog runtime `~17:53` on [OverSimplified Wiki](https://oversimplified.fandom.com/wiki/The_French_Revolution_(Part_1)) / [IMDb](https://www.imdb.com/title/tt10540208/); prior `14:43` figure corrected)* | Rapid-fire contrast between peasant tax burdens and Versailles palace spending, using instant visual state-flips on every clause. | Escalates through consecutive failed fiscal reforms (Calonne -> Brienne -> Estates-General -> Tennis Court Oath), where each reform backfires. | Uses **hard cutout relocations** (`>=25%` screen shift) and background plate swaps (`>=30%`) synchronized to sharp comedy/drama beats (`BP-170` Tier 3). | Grounds `BP-170`'s mechanical definition of `cutout_relocation` (`min_relocation_distance_frac: 0.25`) and `plate_swap` (`min_plate_swap_pixel_frac: 0.30`). |
| **`CS-14`** | **Oversimplified** — [The Napoleonic Wars (Part 1)](https://www.youtube.com/watch?v=zqllxbPWKNI) | Opens on coalition encirclement and Napoleon's rapid Italian campaign maneuverability, moving character cutouts across map vectors in sync with spoken verbs. | Re-hooks at each coalition war by raising the geopolitical scale while planting the structural seeds of the Continental System's eventual overreach. | High density of active visual verbs per minute (`BP-172` `fast_action_verbs`), punctuated by sudden pauses before punchlines/reversals. | Grounds `BP-169`'s `dramatic_changes_per_min_target` (`30.0` in Z1, `28.0` in Z5) and `BP-172` (`KP-47` in `scripting/shot_prompt_lint.py`). |

### 15.3 Domain C — Film, Animation & Visual Storytelling: Camera Grammar, 3-Tier Still Motion Ladder & Color Script

1. **Camera Motion, Continuity & Safe-Area Rules in `sourced_rules.json` (`BP-20..35`, `BP-126`, `BP-132`)**:
   * **Prior Misconception Corrected (`CORR-02`)**: The previous `§15.3` draft mis-cited `BP-26`, `BP-29`, and `BP-34` as shot-size progression, `180°` axis, and `30°` rule. Direct verification of `explainer_engine/standards/sourced_rules.json` and `docs/SOURCED_RULES.md` proves that in the canonical registry:
     * `BP-26` is **photosensitive flash safety** (`flashes_per_s_max: 3, flash_frames: 2, flash_white_max: 0.8`),
     * `BP-27` is **on-screen label hold time** (`hold_min_s: 0.83, s_per_word: 0.375, hold_max_s: 7.0`),
     * `BP-28` is **16:9 text safe area & contrast** (`safe_x: [0.125, 0.875], safe_y: [0.05, 0.95], contrast_min: 4.5`),
     * `BP-29` is **9:16 Shorts safe area** (`safe_x_px: [48, 888], safe_y_px: [288, 1248]` scaled by `4/3` to `1440x2560` in `production/shorts.py:149`),
     * `BP-30` is **hard-cut focal/direction continuity** (`focal_shift_max: 0.1, direction_change_max_deg: 90, same_framing_zoom_tol: 0.02`),
     * `BP-34` is **face cutout composite tolerance** (`halo_px_max: 2, luma_tolerance: 0.18, warmth_tolerance: 0.12`),
     * while **camera lens tiers (`24/35/50/85mm`), `30°` cut angle (`cut_angle_min_deg: 30`), and lens change (`lens_change_min_mm: 15`) live in `BP-126`** (`area: "film"`), **3-layer 2.5D parallax lives in `BP-35`** (`layers_min: 3`), and **character eye-blink / moving hold lives in `BP-132`** (`blink_every_s: [2.0, 4.0], moving_hold_after_s: 2.0`).

2. **Exact Forensic Audit of the `76` `STILL` Shots vs `BP-170` (`edit/dramatic_still.py`)**:
   * **[FACT]** Programmatic inspection of all `76` `STILL` shots (`216.0s` = `5,184` frames = `30.0%` of runtime) in `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) against `BP-170`'s `static_still_max_s_by_zone` (`1.5s` in `hook_0_30s` and `climax_660_720s`; `2.0s` in `early_30_90s` and `late_third_480_660s`; `2.5s` in `middle_calm_90_480s`) confirms:

| `still_motion_spec.duration_tier` in `mrbeast_12min_video_mold (1).json` | Motion Mechanic (`motion_type`) | Total `STILL` Shots in Mold | Duration Range in Mold (`s`) | Shots `<=` Zone Static Cap (`BP-170`) | Shots `>` Zone Static Cap (`BP-170`) | Current `edit/dramatic_still.py` (`5013a55a`) Behavior & Required Resolution (`M-04` / `CHG-09`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`TIER_1_SHORT_HOLD_1.0_TO_2.2S`** | `parallax_25d` (`BP-35` 3-layer FG/MG/BG depth separation + `BP-132` subtle breathing/blink) | **`19`** | `1.125s – 2.500s` | **`17`** | **`2`** (`SH003` at `1.875s > 1.5s` in `S01`/`Z1`; `SH226` at `1.625s > 1.5s` in `S15`/`Z5`) | **Keep `TIER_1` strictly bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`)**. Both `SH003` (`"Cutout Pieter leaps from lower-left to center frame"`) and `SH226` (`"Cutout judge slams gavel"`) describe Tier 3 cutout relocations in `track_5_visual_events` and are upgraded to `TIER_3` with structured `dramatic_change` specs in the reference grid. |
| **`TIER_2_MEDIUM_HOLD_2.2_TO_3.5S`** | `qwen_nextpose_or_lighting_state_flip` (in-place Qwen pose edit or lighting state flip) | **`40`** | `2.000s – 3.500s` | **`4`** (`SH037`, `SH045`, `SH180`, `SH200` at `2.000s` in `Z2`/`Z4` or `2.500s` in `Z3`) | **`36`** (`36` shots between `2.125s` and `3.500s` exceed their zone's `1.5s / 2.0s / 2.5s` static cap) | **`36` shots currently trigger `DS-01` `FAIL`** because `dramatic_still.py` only exempts `cutout_relocation` and `plate_swap`. Per `M-04`, `CG-06`, and `CHG-09`, **Tier 2 remains bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`)** until a quantitative pose-delta + identity metric is validated and approved by the creator (`CD-03`). |
| **`TIER_3_LONG_HOLD_3.5_TO_5.0S`** | `cutout_relocation_with_empty_plate` (`>=25%` cutout position shift or `>=30%` background plate swap) | **`17`** | `3.500s – 4.500s` | **`0`** | **`17`** (`17` shots between `3.500s` and `4.500s`, all `<= 5.0s` `still_max_s`) | **Exempt up to `5.0s` under `BP-170`** once the Mold's `still_motion_spec` fields are mapped to the structured `dramatic_change` schema required by `dramatic_still.py` (`min_relocation_distance_frac: 0.25`, `min_subject_area_frac: 0.08`, `min_plate_swap_pixel_frac: 0.30`). |
| **Total `STILL` Shots** | All 3 Tiers | **`76`** (`216.0s` = `30.0%`) | `1.125s – 4.500s` | **`21`** | **`55`** (`2` Tier 1 + `36` Tier 2 + `17` Tier 3) | **Unified Policy (`M-04` = `CG-06` = `CHG-09`)**: `BP-170` (`FAIL`) is never relaxed without `CD-03`. Only `TIER_3` unlocks `> static_still_max_s_by_zone` up to `5.0s`. |

3. **Relative Color Script (`AC-17`, `BP-130`, `BP-166`) & Character Identity (`BP-133`) in Actual Repo Code**:
   * **Prior Misconception Corrected (`CORR-03`)**: The previous `§15.3` / `CHG-11` draft attributed ArcFace `0.65`/`0.72` identity thresholds to `BP-130` and `qa/identity_gate.py`, and described `BP-166` as a hard `FAIL` gate in `qa/color_continuity.py`.
   * **Verified Correction (`SOURCE 1`: `explainer_engine/qa/identity.py:1–70`; `SOURCE 2`: `explainer_engine/finish/grade.py:34–115`; `SOURCE 3`: `explainer_engine/training/video_qa.py:101–220` & `explainer_engine/compose/episode_look.py:1–60`)**:
     1. **`BP-130` (`finish/grade.py` & `production/assemble.py:749–791`)** is **Reinhard et al. (2001) CIE LAB mean/std colour transfer** (`blend_max: 0.65`, `status: "hypothesis"`, `severity: "REVIEW"`), NOT facial identity!
     2. **`BP-133` (`explainer_engine/qa/identity.py:1–70`)** is **character identity & lip-sync QA** (`status: "hypothesis"`, `severity: "REVIEW"`). It uses **CLIP ViT-B-32 embeddings (`training/embed.py`)**, NOT InsightFace ArcFace, and line 4–5 of `qa/identity.py` explicitly mandates: `The identity threshold is "calibrate on our hero sheets" (BP-133): until a calibrated number is passed in, the row is INFO (score only), never a guess and never the Blueprint's 0.65.`
     3. **`BP-166` (`explainer_engine/training/video_qa.py:101–220`)** is **clip motion & colour-drift QA** (`sat_drift_max: 0.08`, `luma_drift_max: 0.08`, `hero_palette_max: 0.15`, `status: "hypothesis"`, `severity: "REVIEW"`).
     4. **`AC-17` (`explainer_engine/compose/episode_look.py` & `scripting/film_shots.py:120–125`)** injects the episode's `<=10`-word colour/light phrase at the end of style-LoRA prompts (`LT-65` in `qa/style_prompt.py`), while `D-22` (`tests/unit/test_palette.py`) bans raw `#RRGGBB` hex literals outside `explainer_engine/design/palette.json`.

### 15.4 Domain D — Voice, Audio & Music: WPM Literature vs House Rules, Real `eleven_v4` Pause Measurements & Canonical `BP-50..53` / `BP-120..122` Audio Rules

1. **Disentangling WPM & Speech-Rate Scientific Literature from House Hypothesis `BP-169` (`CORR-04`)**:
   * **Prior Misconception Corrected (`CORR-04`)**: Earlier drafts and the research compendium conflated four distinct scientific studies—attributing `"~39 bits/s across 8 languages"` to Pellegrino et al. (2011), calling Brysbaert (2019)'s `183 WPM` oral reading rate `"conversational average"`, and treating `BP-169`'s `193 / 176 / 166 / 185 / 160 WPM` zone targets as neuroscience laws.
   * **Verified Correction Backed by 4 Primary Academic Sources**:
     * **`SOURCE 1` ([Pellegrino, Coupé & Marsico 2011, *Language* 87(3):539–558](https://www.cambridge.org/core/journals/language/article/abs/crosslinguistic-perspective-on-speech-information-rate/8690E5D7B9D99CE4F54DC3C4A1AB3A2D), verified in `docs/research/CRAFT_SOURCES_2026-10.md`)**: Analyzed **7 languages** (English, French, German, Italian, Japanese, Mandarin, Spanish; `8` only when counting Vietnamese as the SDIR reference base) and demonstrated a negative trade-off between syllabic rate and information density per syllable, while explicitly noting that cross-linguistic compensation does *not* imply a strictly constant bit rate.
     * **`SOURCE 2` ([Coupé, Oh, Dediu & Pellegrino 2019, *Science Advances* 5(9):eaaw2594, `PMC6984970`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6984970/))**: Analyzed **17 languages from 9 families (`170` native speakers, `~240,000` syllables)** and established the **`39.15 ± 5.10 bits/s` (`6.63 ± 1.15 syllables/s`)** cross-linguistic information-rate attractor.
     * **`SOURCE 3` ([Brysbaert 2019, *Journal of Memory and Language* 109:104047, `PMC6758568`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/) & [Yuan, Liberman & Cieri 2006, *Interspeech*](https://www.isca-archive.org/interspeech_2006/yuan06_interspeech.pdf))**: Brysbaert (2019) meta-analyzed **silent reading (`238 WPM` non-fiction, `260 WPM` fiction)** and **oral reading (`183 WPM`)**; conversational speaking rates (`152–170 WPM` topic means, `111–291 WPM` individual spread on Switchboard) were measured by Yuan, Liberman & Cieri (2006).
     * **`SOURCE 4` ([Rodero 2012, *Communication Research*](https://repositori.upf.edu/bitstreams/132a1675-b3a3-4bd5-8edc-976a80727538/download) & [Rodero 2020, *Journal of Advertising Research* / ARF](https://www.researchgate.net/publication/336819723_Do_Your_Ads_Talk_Too_Fast_To_Your_Audio_Audience_How_Speech_Rates_of_Audio_Commercials_Influence_Cognitive_and_Physiological_Outcomes))**: Compared `160`, `180`, and `200 WPM` in audio commercials (`200` English/Spanish listeners), finding `180 WPM` optimized recall/attention in short ad spots.
   * **Resulting Governance Rule (`D-92`, `D-94`)**: None of those papers prove a 12-minute YouTube docudrama 5-zone WPM curve. In Argon, `170 WPM` (`155–185 WPM`, `BP-01`, `D-92` item 2) is the creator's calm baseline, and `BP-169` (`193 / 176 / 166 / 185 / 160` heard WPM across the 5 zones) is a **channel house rule (`status: "house"`, `severity: "REVIEW"` per `D-94`)**.

2. **Real Measured `eleven_v4` Pause Share in `examples/` & Exact Module Ownership (`hype_read.py`, `pause_pad.py`, `narrator_polish.py`, `CORR-05`)**:
   * **Prior Misconception Corrected (`CORR-05`)**: In `7312f660`, `CHG-02`/`CHG-06` mistakenly stated that `audio/narrator_polish.py:97` read `tts_tags_allowed`. In reality (`repo_5013a55a`), `explainer_engine/audio/narrator_polish.py` is a **`46`-line FFmpeg EQ/limiter filter module** (`volume=-0.6dB,highpass=f=60,afftdn=nr=8:nf=-50,bass=g=12:f=150:w=0.7,equalizer=f=300:t=q:w=1:g=-2,alimiter=limit=0.95`), whereas **zone TTS tags (`BP-169`, `BP-171`) are owned exclusively by `explainer_engine/audio/hype_read.py` (`110` lines)**, and **punctuation pause insertion (`MIN_GAP = 0.26s`, room-tone fill `BP-60`) is owned by `explainer_engine/audio/pause_pad.py` (`157` lines)**!
   * **[PRIMARY-STANDARD]** Per official [ElevenLabs Pause Documentation](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses) and [Eleven v3/v4 Model Guide](https://elevenlabs.io/docs/overview/models#eleven-v3), **SSML `<break>` tags are NOT supported on `eleven_v4` or `eleven_v3`**.
   * **[FACT]** Direct measurement of the committed `eleven_v4` word-timestamp files in `examples/` proves that raw `eleven_v4` reads already contain **`28.4%–37.3%` natural inter-word gaps**:

| Committed Repo Example (`examples/*/words*.json`) | Word Count ($W$) | Total Span ($T_{\text{total}}$) | Active Phonation Sum ($T_{\text{speech}}$) | Natural Inter-Word Gap Sum ($T_{\text{pause,raw}}$) | Measured Raw `speaking_wpm` | Measured Raw `heard_wpm` | Existing Natural Pause Share ($p_{\text{raw}}$) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `examples/day1_v2/words_raw.json` (before `pause_pad.py`) | `204` words | `86.579s` | `54.280s` | `32.299s` (`51` gaps `>=0.15s`) | **`225.50 WPM`** | **`141.37 WPM`** | **`37.31%`** |
| `examples/day1_v2/words.json` (after `pause_pad.py`) | `204` words | `90.266s` | `54.280s` | `35.986s` (`+3.687s` added by `pause_pad.py`) | **`225.50 WPM`** | **`135.60 WPM`** | **`39.87%`** |
| `examples/titans_from_zero/words.json` | `142` words | `54.860s` | `39.260s` | `15.600s` (`29` gaps `>=0.15s`) | **`217.01 WPM`** | **`155.30 WPM`** | **`28.44%`** |
| `examples/syndicate_wars_ep1/words.json` | `149` words | `73.039s` | `52.230s` | `20.809s` (`26` gaps `>=0.15s`) | **`171.17 WPM`** | **`122.40 WPM`** | **`28.49%`** |

   * **[FACT]** In `explainer_engine/audio/pause_pad.py:85–98`, `pad_pauses()` iterates over consecutive words `(a, b)`, checks if `a["w"]` ends with a punctuation mark in `edit.shot_rules.CUT_MARKS`, computes `gap = b["s"] - a["e"]` and `want = max(min_gap if mark in CUT_MARKS else 0.0, targets.get(k, 0.0))`, finds the quietest `10 ms` window `<= -46.0 dB` (`QUIET_DB`), and inserts `want - gap` of room tone (`BP-60`). On zoned scripts (`BATCH-M4` / `CHG-06`), `pause_pad.py` uses `SR.T("BP-171", "hyped_min_gap_s")` (`0.18s`) in `hyped` / `hyped_climax` zones and `MIN_GAP = 0.26s` in `calm_story` (`middle_calm_90_480s`).

3. **Canonical Audio `BP-*` Mapping & International Standards vs House Targets (`CORR-06`)**:
   * **Prior Misconception Corrected (`CORR-06`)**: In `7312f660`, `§15.4`, `§15.7`, and `CHG-10` mis-cited `BP-73`, `BP-74`, `BP-75`, and `BP-15` for loudness (`-14 LUFS`), LRA (`5–9 LU`), sidechain ducking, and Murch's Law of 2.5, and presented `-14.0 LUFS` as an official ITU/EBU standard.
   * **Verified Correction (`SOURCE 1`: [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en); `SOURCE 2`: [EBU R 128](https://tech.ebu.ch/publications/r128) & EBU Tech 3343 v4 in `docs/research/CRAFT_SOURCES_2026-10.md`; `SOURCE 3`: [Walter Murch — *Dense Clarity — Clear Density* (Transom 2005)](https://rompusnetwork.org/portfolio/dense_clarity_by_walter_murch.pdf) & `explainer_engine/standards/sourced_rules.json` / `docs/SOURCED_RULES.md`)**:
     1. **Measurement Algorithm vs House Target**: [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en) defines the **K-weighted loudness (LKFS/LUFS) and True-Peak (dBTP) measurement algorithm** (`[PRIMARY-STANDARD]`), while [EBU R 128](https://tech.ebu.ch/publications/r128) sets a broadcast target of **`-23.0 LUFS`** and EBU Tech 3343 v4 explicitly states there is **no universal maximum Loudness Range (LRA)** across all genres. In Argon, **`-14.0 LUFS` (`pass_band: [-15.0, -13.0]`, `true_peak_max: -1.0 dBTP`) is a binding project house rule in `BP-50`** (`explainer_engine/qa/targets.py` & `qa/scorecard.py`; as `docs/SOURCED_RULES.md:105` notes: `"YouTube publishes no number; louder is turned down, quieter is never lifted"`).
     2. **Canonical Audio Registry IDs (`BP-50..53`, `BP-117..122`)**:
        * **`BP-50` (`area: "audio"`, `severity: "FAIL"`)**: Long-form integrated loudness `-14.0 LUFS` (`pass_band: [-15.0, -13.0]`), `true_peak_max: -1.0 dBTP`, `limiter_tp: -1.5 dBTP` (`qa/targets.py`, `qa/scorecard.py`, `qa/frame_review.py`).
        * **`BP-51` (`area: "audio"`, `severity: "REVIEW"`)**: Dialogue anchor (`ldr_max_lu: 5.0`, `ldr_review_lu: 4.0` — programme loudness minus narration stem loudness in LU, `qa/targets.py:68–72`).
        * **`BP-52` (`area: "audio"`, `severity: "FAIL"`)**: Background under speech measured in gated LU on stems (`music_under_lu: 10.0`, `bed_under_lu: 15.0`, `combined_under_lu: 14.0`, `qa/targets.py:80–98`).
        * **`BP-53` (`area: "audio"`, `severity: "REVIEW"`)**: Sidechain ducking (`depth_db: [6.0, 12.0]`, `house_depth_db: 9.0`, `attack_ms: [20, 80]`, `release_ms: [250, 700]`, enforced in `audio/duck.py` and `production/assemble.py:195, 241, 411`).
        * **`BP-117` (`area: "audio"`, `severity: "REVIEW"`)**: Scene-boundary J-cut and L-cut audio leads (`j_cut_s`, `l_cut_s`, enforced in `audio/sound_director.py:459–461, 719`).
        * **`BP-120` (`area: "audio"`, `severity: "REVIEW"`)**: Pre-reveal acoustic vacuum (`vacuum_s: [0.8, 1.2]`, `vacuum_dbfs: -42.0`, `vacuums_max: 3`, `micro_cue_dbfs: -22.0`, enforced in `audio/sound_director.py:441–445` and `production/assemble.py:519`).
        * **`BP-121` (`area: "audio"`, `severity: "REVIEW"`)**: Stereo panning (`sfx_pan_max: 0.45`) and **Walter Murch's Law of 2.5** (`same_colour_layers: 2.5`, `spread_layers: 5` in `audio/sound_director.py:785`). As Murch explains in [*Dense Clarity — Clear Density*](https://rompusnetwork.org/portfolio/dense_clarity_by_walter_murch.pdf) (`docs/research/CRAFT_SOURCES_2026-10.md`), when sounds occupy the **same spectral "colour" / cognitive register**, the listener's brain tracks at most `~2.5` layers before masking sets in (`int(2.5) = 2` in `sound_director.py:785`), whereas across **distinct spectral bands** up to `5` layers (`spread_layers: 5`) can coexist (`[CRAFT-HEURISTIC]`, `REVIEW`).
        * **`BP-122` (`area: "audio"`, `severity: "REVIEW"`)**: Shot-size acoustic perspective (`shelf_hz: 6000, wide_shelf_db: -4.0, wide_wet: 0.22, close_dry: 0.95, proximity_db: 2.0, proximity_hz: 140`, enforced in `production/assemble.py:291–296, 480–481`).

### 15.5 Domain E — Editing & Pacing: Exact 5-Zone & 16-Segment Verification of `mrbeast_12min_video_mold (1).json` vs `BP-169` (`CORR-07`)

* **Prior Misconception Corrected (`CORR-07`)**: In the previous draft (`7312f660`), `§15.5` listed zone shot counts as `18, 28, 138, 50, 20` (`36, 28, 21.2, 16.7, 20` shots/min) from a stale pre-bundle table and conflated `shots_per_min_target` with `cuts_per_min`.
* **Verified Correction (`SOURCE 1`: `mrbeast_12min_video_mold (1).json` SHA-256 `2ca7f56f...` `zones_5` & `reference_timeline_254_shots`; `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` `BP-169`; `SOURCE 3`: `explainer_engine/edit/motion_lint.py` `BP-83`)**:
  1. Direct programmatic summation over `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) proves that the `254` shots in `reference_timeline_254_shots` are partitioned across the 5 zones as **`14, 24, 111, 75, 30` shots**—which equals **`28.0, 24.0, 17.08, 25.0, 30.0` shots/min**, matching `BP-169`'s `shots_per_min_target` (`28.0, 24.0, 17.0, 25.0, 30.0`) in `sourced_rules.json`!
  2. **Explicit Definition of `shots_per_min` vs `cuts_per_min`**: In a contiguous segment/zone of duration $D$ seconds containing $N$ shots, `shots_per_min` is $\frac{60 \cdot N}{D}$. A segment with $N$ shots has $N - 1$ internal cuts plus $1$ entry boundary cut from the preceding segment ($N$ shot boundaries total across the episode except shot 1 at $t = 0.0\text{s}$, so across `254` shots there are `253` internal cuts). All Argon validators (`rhythm_lint.py`, `variant_plan.py`, `BP-169`) measure **`shots_per_min` ($60 \cdot N / D$)**.
  3. **Anti-Metronome Hold Variance (`BP-83` in `edit/motion_lint.py:33–36`, NOT `BP-28`)**: In `sourced_rules.json`, shot-hold variance (`hold_cv_min`, `cv_from_shots`, `hold_similar`, `similar_run_max`) lives in **`BP-83`** (`area: "motion"`, `status: "hypothesis"`, `severity: "REVIEW"` in `explainer_engine/edit/motion_lint.py`), grounded qualitatively in [Cutting, DeLong & Nothelfer (2010), *Psychological Science*](https://journals.sagepub.com/doi/10.1177/0956797610361679) (`1/f` shot-length correlation across 150 Hollywood films), while the exact `CV >= 0.20` threshold is a repo hypothesis (`REVIEW`).

#### Table 15.5A — Verified 5-Zone Breakdown of `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) vs `BP-169` (`sourced_rules.json`)

| Zone ID (`BP-169` Canonical / Mold Alias) | Window (`s`) & Duration | Segments | Exact Mold Shot Count & ASL (`s`) | Exact Mold `shots_per_min` vs `BP-169` `shots_per_min_target` (`band`) | `BP-169` `shot_len_s_band` (`s`) | Exact Mold Word Count & Heard WPM | `BP-169` `heard_wpm_target` (`band`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`hook_0_30s`** (`Z1_HOOK_0_30S`) | `0.0–30.0s` (`30.0s`, `720f`) | `S01` | **`14` shots** (`2.143s` ASL) | **`28.00` shots/min** vs `BP-169` **`28.0`** (`[24, 34]`) | `[1.0, 2.5]s` | **`96` words** (`192.00` WPM) | **`193` WPM** (`[180, 215]`) |
| **`early_30_90s`** (`Z2_FAST_SETUP_30_90S`) | `30.0–90.0s` (`60.0s`, `1,440f`) | `S02–S03` | **`24` shots** (`2.500s` ASL) | **`24.00` shots/min** vs `BP-169` **`24.0`** (`[20, 28]`) | `[1.2, 3.5]s` | **`177` words** (`177.00` WPM) | **`176` WPM** (`[165, 195]`) |
| **`middle_calm_90_480s`** (`Z3_CALM_MIDDLE_90_480S`) | `90.0–480.0s` (`390.0s`, `9,360f`) | `S04–S11` | **`111` shots** (`3.514s` ASL) | **`17.08` shots/min** vs `BP-169` **`17.0`** (`[14, 20]`) | `[2.0, 5.0]s` | **`1,083` words** (`166.62` WPM) | **`166` WPM** (`[150, 180]`) |
| **`late_third_480_660s`** (`Z4_LATE_THIRD_480_660S`) | `480.0–660.0s` (`180.0s`, `4,320f`) | `S12–S14` | **`75` shots** (`2.400s` ASL) | **`25.00` shots/min** vs `BP-169` **`25.0`** (`[22, 28]`) | `[1.2, 3.2]s` | **`553` words** (`184.33` WPM) | **`185` WPM** (`[170, 200]`) |
| **`climax_660_720s`** (`Z5_CLIMAX_660_720S`) | `660.0–720.0s` (`60.0s`, `1,440f`) | `S15–S16` | **`30` shots** (`2.000s` ASL) | **`30.00` shots/min** vs `BP-169` **`30.0`** (`[26, 34]`) | `[1.0, 2.5]s` | **`157` words** (`157.00` WPM) | **`160` WPM** (`[145, 185]`) |
| **Episode Total** | `0.0–720.0s` (`720.0s`, `17,280f`) | `S01–S16` | **`254` shots** (`2.835s` ASL) | **`21.17` shots/min** overall (`152` VIDEO, `76` STILL, `26` HELPER) | Zone-governed | **`2,066` words** (`172.17` WPM) | Zone-governed (`D-94` house `REVIEW`) |

#### Table 15.5B — Complete 16-Segment (`S01..S16`) Programmatic Verification Table from `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`)

*(Embedded here and in `mold_254_shots_verified_digest.json` inside `ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02.zip` so any external auditor can verify the 16-segment / 254-shot sums without loading the full 1.1 MB JSON over a connector)*:

| Segment ID | Zone ID | Time Window (`s`) | Duration (`s` / Frames) | Header vs Actual Shot Count (`shots_per_min`) | Header vs Actual Word Count | Cumulative Spoken Words & Share (`BP-04`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`S01`** | `Z1_HOOK_0_30S` (`hook_0_30s`) | `[0.0, 30.0]` | `30.0s` / `720f` | `14` / `14` (`28.00` shots/min) | `96` / `96` words (`192.0` WPM) | `96 / 2,066` (`4.65%`) |
| **`S02`** | `Z2_FAST_SETUP_30_90S` (`early_30_90s`) | `[30.0, 60.0]` | `30.0s` / `720f` | `12` / `12` (`24.00` shots/min) | `88` / `88` words (`176.0` WPM) | `184 / 2,066` (`8.91%`) |
| **`S03`** | `Z2_FAST_SETUP_30_90S` (`early_30_90s`) | `[60.0, 90.0]` | `30.0s` / `720f` | `12` / `12` (`24.00` shots/min) | `89` / `89` words (`178.0` WPM) | `273 / 2,066` (`13.21%`) |
| **`S04`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[90.0, 135.0]` | `45.0s` / `1,080f` | `12` / `12` (`16.00` shots/min) | `124` / `124` words (`165.3` WPM) | `397 / 2,066` (`19.22%`) — `BP-142` Turn Slot `4` |
| **`S05`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[135.0, 175.0]` | `40.0s` / `960f` | `11` / `11` (`16.50` shots/min) | `110` / `110` words (`165.0` WPM) | `507 / 2,066` (`24.54%`) |
| **`S06`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[175.0, 210.0]` | `35.0s` / `840f` | `13` / `13` (`22.29` shots/min) | `98` / `98` words (`168.0` WPM) | `605 / 2,066` (`29.28%`) — `BP-142` Turn Slot `6` & Re-Hook #1 |
| **`S07`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[210.0, 270.0]` | `60.0s` / `1,440f` | `16` / `16` (`16.00` shots/min) | `167` / `167` words (`167.0` WPM) | `772 / 2,066` (`37.37%`) |
| **`S08`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[270.0, 330.0]` | `60.0s` / `1,440f` | `16` / `16` (`16.00` shots/min) | `166` / `166` words (`166.0` WPM) | `938 / 2,066` (`45.40%`) — `BP-142` Turn Slot `8` |
| **`S09`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[330.0, 375.0]` | `45.0s` / `1,080f` | `16` / `16` (`21.33` shots/min) | `123` / `123` words (`164.0` WPM) | `1,061 / 2,066` (`51.36%`) — Midpoint Re-Hook #2 (`BP-75`) |
| **`S10`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[375.0, 430.0]` | `55.0s` / `1,320f` | `14` / `14` (`15.27` shots/min) | `154` / `154` words (`168.0` WPM) | `1,215 / 2,066` (`58.81%`) — `BP-142` Turn Slot `10` |
| **`S11`** | `Z3_CALM_MIDDLE_90_480S` (`middle_calm_90_480s`) | `[430.0, 480.0]` | `50.0s` / `1,200f` | `13` / `13` (`15.60` shots/min) | `141` / `141` words (`169.2` WPM) | `1,356 / 2,066` (`65.63%`) — `BP-142` Turn Slot `11` |
| **`S12`** | `Z4_LATE_THIRD_480_660S` (`late_third_480_660s`) | `[480.0, 540.0]` | `60.0s` / `1,440f` | `25` / `25` (`25.00` shots/min) | `184` / `184` words (`184.0` WPM) | `1,540 / 2,066` (`74.54%`) |
| **`S13`** | `Z4_LATE_THIRD_480_660S` (`late_third_480_660s`) | `[540.0, 600.0]` | `60.0s` / `1,440f` | `25` / `25` (`25.00` shots/min) | `184` / `184` words (`184.0` WPM) | `1,724 / 2,066` (`83.45%`) — `BP-142` Turn Slot `13` |
| **`S14`** | `Z4_LATE_THIRD_480_660S` (`late_third_480_660s`) | `[600.0, 660.0]` | `60.0s` / `1,440f` | `25` / `25` (`25.00` shots/min) | `185` / `185` words (`185.0` WPM) | `1,909 / 2,066` (`92.40%`, crosses `90.0%` = `1,860w` at `~644.1s`) |
| **`S15`** | `Z5_CLIMAX_660_720S` (`climax_660_720s`) | `[660.0, 690.0]` | `30.0s` / `720f` | `15` / `15` (`30.00` shots/min) | `79` / `79` words (`158.0` WPM) | `1,988 / 2,066` (`96.22%`) |
| **`S16`** | `Z5_CLIMAX_660_720S` (`climax_660_720s`) | `[690.0, 720.0]` | `30.0s` / `720f` | `15` / `15` (`30.00` shots/min) | `78` / `78` words (`156.0` WPM) | `2,066 / 2,066` (`100.00%`) |

### 15.6 Domain F — AI Production Realities: Open-Source PyTorch LTX (`8k+1` `BP-139`) vs Hosted LTX-2.5 API, Exact `152`-Shot Handle Math & `D-92` / `BP-168` Reconciliation (`CORR-08`)

1. **Distinguishing Open-Source Self-Hosted LTX (`BP-139`, RunPod ComfyUI/PyTorch) from Hosted LTX-2.5 REST API (`CORR-08`)**:
   * **Prior Misconception Corrected (`CORR-08`)**: Earlier drafts stated `F = 8k + 1` as a universal rule across all LTX calls without distinguishing Argon's self-hosted RunPod open-source worker (`aivideo/pod/clips.py`, `training/pods/p12/p12c_ltx.py`, `core/contracts.py:60–67`) from the hosted LTX-2.5 REST API (`api.ltx.io`), and misclassified `BP-139` as a `FAIL` rule when `sourced_rules.json` defines `BP-139` with `status: "hypothesis"`, `severity: "REVIEW"` (`D-59`).
   * **Verified Correction (`SOURCE 1`: [LTX Open-Source PyTorch API & IC-LoRA Docs](https://docs.ltx.io/open-source-model/integration-tools/pytorch-api); `SOURCE 2`: [Hosted LTX-2.5 API Documentation & Support Matrix](https://docs.ltx.io/models/ltx-2-5); `SOURCE 3`: [Lightricks LTX-2 Technical Report `arXiv:2601.03233`](https://arxiv.org/abs/2601.03233) & `explainer_engine/core/contracts.py:10, 60–67`)**:
     * **Self-Hosted Open-Source / RunPod PyTorch & ComfyUI Path (Argon's Primary Production Route, `BP-139`)**: The 3D causal spatiotemporal VAE packs `8` video frames per latent step after frame `0`, requiring raw generation frame counts of **`F = 8k + 1`** (`frame_table: [97, 121, 145, 169, 193, 241, 257]` at `24 fps`) and spatial dimensions divisible by `32` (`size_multiple: 32`, `two_stage_size_multiple: 64`). In `sourced_rules.json` and `core/contracts.py:10`, `BP-139` has `status: "hypothesis"`, `severity: "REVIEW"` (`CN-08`, `CLIP-02`).
     * **Hosted LTX-2.5 REST API Path (`api.ltx.io/v2/*`)**: Exposes discrete duration buckets in seconds (`ltx-2-5-fast` at `720p/1080p` `24/25 fps`: `6, 8, 10, 12, 14, 16, 18, 20s`; `ltx-2-5-fast` at `1440p/4K` and `ltx-2-5-pro` at `720p..4K`: `6, 8, 10s`; `audio-to-video`: duration follows the input audio length) and abstracts the internal `8k+1` latent padding behind the API.

2. **Exact Verified Handle-Frame Math Across All `152` `VIDEO` Shots (`M-10` & `CHG-08`)**:
   * **[FACT]** Across the `152` `VIDEO` shots (`10,368` usable timeline frames = `432.00s`) in `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`):
     * Usable timeline frames (`usable_frame_count`): **`10,368` frames** (`432.00s`).
     * Zero-handle `8k+1` quantum sum (`8*ceil((u-1)/8)+1`): **`10,904` frames** (`454.33s`).
     * Current `BP-128` (`handle_frames: [12, 16]` per side -> `8*ceil((u+24-1)/8)+1`): **`14,552` generated frames** (`606.33s`, `+4,184` overhead frames = `+40.35%`).
     * Mold `ltx_generation_frame_count` (`>=4` handles/side -> `8*ceil((u+8-1)/8)+1`): **`12,120` generated frames** (`505.00s`, `+1,752` overhead frames = `+16.90%`), saving **`2,432` frames (`101.33s`, `16.71%` reduction in generated frames)**.
     * Transition-aware policy (`>=12` handles/side on the `17` whip-pan/crossfade shots + `>=4` handles/side on the `135` hard/J/L-cut shots): **`12,392` generated frames** (`516.33s`), saving **`2,160` frames (`90.00s`, `14.84%` reduction)** (`[HYPOTHESIS]`, `REVIEW`).

### 15.7 Master Correction Register (`CORR-01` through `CORR-12`) & External Source Audit (`SRC-01` through `SRC-48`)

#### Table 15.7A — Twelve Confirmed Misconceptions & Multi-Source Corrections (`CURRENT → CORRECTION → SOURCE 1 → SOURCE 2 → SOURCE 3 → TEST`)

| ID | Subsystem / Topic | What Was Misunderstood at the Time (`CURRENT MISCONCEPTION`) | Verified Engineering / Scientific Correction (`CORRECTION`) | `SOURCE 1` (Repo Code / Primary Doc) | `SOURCE 2` (Official Standard / Paper) | `SOURCE 3` (Independent Corroboration) | Verification Test (`TEST`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`CORR-01`** | **Schema Version Field & `/4` Dispatch (`CHG-02`)** | `CHG-02` in `7312f660` claimed scripts use `doc.get("schema_version")` (`"https://tmr.dev/..."`) and that `production/script.py` (`206` lines) defines `SCHEMA_VERSION = ".../3"`, `narrator_polish.py:97` reads `tts_tags_allowed`, `sample.py:84` uses `calm_window_s`, and `production/shot_prompt_checks.py` exists. | As already proven in `§8.1` (`CG-01..CG-03`) and `§9.1` (`BATCH-M0`), scripts use **`doc.get("schema")`** (`"production_script/3"` or `"production_script/4"`) and `timed.get("script_schema")` (`audio/layers.py:53`). The 3 real P0 bugs are: (1) 11 modules checking `== "production_script/3"`, (2) `production/__main__.py:119` skipping `narrator_polish` when `S.has_dialogue(doc)` is true, and (3) `scripting/film_shots.py:compose()` not copying `rhythm_zone` for `scripting/shot_prompt_lint.py` (`KP-47`). | `explainer_engine/schemas/production_script.schema.json:17–25` & `scripting/scene_lint.py:28, 139` | `explainer_engine/production/__main__.py:119` & `audio/narrator_polish.py:1–46` | `explainer_engine/scripting/shot_prompt_lint.py:74–78, 183–191` & `scripting/film_shots.py:449` | `pytest tests/unit/test_production_script_schema.py tests/unit/test_narrator_polish.py tests/unit/test_shot_prompt_lint.py` |
| **`CORR-02`** | **Audio Module Ownership (`CHG-06`)** | `CHG-06` in `7312f660` assigned zone TTS tag lookup (`tts_tags`) and punctuation pause insertion to `audio/narrator_polish.py` and claimed `pause_pad.py` already had dynamic zone WPM scaling. | `audio/narrator_polish.py` is strictly Odom's fixed FFmpeg EQ/limiter chain (`NP.CHAIN`). Zone TTS tag validation (`HR-01..04`) lives in **`audio/hype_read.py`** (`BP-169`, `BP-171`), and punctuation gap padding (`MIN_GAP = 0.26s` in calm zones vs `hyped_min_gap_s = 0.18s` in hyped zones, room-tone fill `BP-60`) lives in **`audio/pause_pad.py`**. | `explainer_engine/audio/hype_read.py:1–110` & `audio/pause_pad.py:1–157` | [ElevenLabs — How can I add pauses?](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses) | [ElevenLabs — Eleven v3/v4 Model Guide](https://elevenlabs.io/docs/overview/models#eleven-v3) & `examples/day1_v2/words_raw.json` | `pytest tests/unit/test_hype_read.py tests/unit/test_pause_pad.py tests/unit/test_narrator_polish.py` |
| **`CORR-03`** | **`D-67` Two-Part Sample Scope (`CHG-14`)** | `CHG-14` in `7312f660` claimed `production/sample.py` (`D-67`) slices a 30s `[90.0, 120.0]` sub-window out of `S04` (`90–135s`). | `production/sample.py:44–50` (`scope_segments`) operates strictly at **whole-segment granularity**: it defaults to `ids[:2]` (`["S01", "S02"]`, `0–60s`) or reads whole segment IDs from `sample_approval.json.scope_segments` (e.g., `["S01", "S04"]` = `75s` or `["S01", "S15"]` = `60s`, as documented in `§9.10` `L1502`). It never slices a 30s sub-window inside a 45s segment. | `explainer_engine/production/sample.py:31–56` | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-67` & `OR-19`) | `tests/unit/test_sample_gate.py` | `pytest tests/unit/test_sample_gate.py` |
| **`CORR-04`** | **`D-92` vs `BP-168` Go/Pivot/Abandon & `$20` Threshold (`CHG-14`)** | `sourced_rules.json` (`BP-168`) still holds pre-`D-92` values (`go_retry_max: 2.0, pivot_retry_max: 3.0, go_review_min_per_min_max: 4.0`), while `CHG-14` in `7312f660` invented an unverified `abandon_forecast_usd_min: 20.00` key not in `BP-168` or `D-92`. | In `D-92` item 7 (`2026-11-01`), the creator already decided: **GO = `<= 3` seeds per accepted shot and `<= 3` review min/finished min; PIVOT = `(3, 6]` on either; ABANDON = `> 6`**, with explicit unit mapping `seeds_per_accepted_shot = 1 + retries_per_shot` (or `retry_mult` defined directly as total generated seeds / accepted shots). `BP-168` (`severity: "REVIEW"` in `core/ledger.py:330–348`) must be updated in `BATCH-M1` to match `D-92`, removing the invented `$20` key, while recognizing that `$12.00` (`go_forecast_usd_max`) is a `REVIEW` forecast threshold unless passed as `caps={"runpod_usd": ...}` to `Run.open()`. | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-92` item 7) | `explainer_engine/standards/sourced_rules.json` (`BP-168`) & `core/ledger.py:330–348` | `tests/unit/test_d92_creator_answers.py` & `config/spend_caps.json` | `pytest tests/unit/test_d92_creator_answers.py tests/unit/test_ledger.py` |
| **`CORR-05`** | **Identity (`BP-133`), Colour Transfer (`BP-130`), and Voice Safety (`PV-55`, `V-51`) (`CHG-11`, `CHG-12`)** | `CHG-11`/`CHG-12` in `7312f660` tied `BP-130` to ArcFace `0.65` in non-existent `qa/identity_gate.py`, cited non-existent `governance/rights_gate.py`, and invented a `"post-1926 public figure"` cutoff. | `BP-130` is Reinhard LAB colour transfer (`finish/grade.py`); **identity & lip-sync is `BP-133` in `explainer_engine/qa/identity.py`** (using CLIP ViT-B-32 `training/embed.py`, `REVIEW` only, explicitly forbidding uncalibrated `0.65` guesses). Living-person voice protection (`PV-55`, `D-62`) lives in **`explainer_engine/production/silent.py:246–267`**. Per [ElevenLabs Prohibited Use Policy (09 Oct 2026, `V-51`)](https://elevenlabs.io/use-policy) §3 & §4, cloning/impersonating any living individual without consent or political candidates/elected officials is prohibited, and deceased individuals are barred where likely to cause harm or infringe post-mortem rights (no `"1926"` cutoff exists; deceased historical figure voicing remains open under `D-90` / `CD-06`). | `explainer_engine/qa/identity.py:1–70` & `finish/grade.py:34–115` | `explainer_engine/production/silent.py:246–267` & `docs/MARKET_RESEARCH.md` (`V-51`, `L106`) | [ElevenLabs Prohibited Use Policy (Updated 09 Oct 2026)](https://elevenlabs.io/use-policy) | `pytest tests/unit/test_identity_qa.py tests/unit/test_silent_lines.py tests/unit/test_voice_route_docs.py` |
| **`CORR-06`** | **`BP-04` (`ENG-5`) Spoken-Word Share & `voiced: false` Exclusion (`CHG-05`)** | `qa/engagement.py:55, 163` (`_text(seg)`) currently counts all `seg["lines"]` including `voiced: false` silent bubble lines (`D-62`), and if `drama.function == "resolution"` is absent on all segments, the loop exits without emitting an `ENG-5` finding. Also, `CHG-05` in `7312f660` marked `BP-04` as a hard `FAIL` despite `D-94` keeping retention rules at `REVIEW`. | As specified in `§9.2` (`L1060–1078`), `qa/engagement.py:resolution_word_share(doc)` must filter `if line.get("voiced", True) is not False`, strip bracketed TTS tags, flag missing resolution markers on `/4` scripts, and use `SR.level("BP-04", "REVIEW")` (`REVIEW` severity per `D-94` and `sourced_rules.json` `BP-04`). | `explainer_engine/qa/engagement.py:51–62, 162–177` | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-62`, `D-94`) | [Loewenstein (1994) Information-Gap Theory (CMU PDF)](https://www.cmu.edu/dietrich/sds/docs/loewenstein/PsychofCuriosity.pdf) | `pytest tests/unit/test_engagement.py tests/unit/test_story_engine.py` |
| **`CORR-07`** | **Canonical `BP-*` Registry ID Mapping (`§15.3`, `§15.4`, `§15.7`, `CHG-10`)** | `§15` and `CHG-10` in `7312f660` used wrong `BP-*` numbers from an old external table (`BP-14` for WPM, `BP-15` for Law of 2.5, `BP-27` for J/L cuts, `BP-28` for shot CV, `BP-30` for breathing valleys, `BP-73..75` for LUFS/LRA/ducking). | Re-keyed everywhere to the exact `explainer_engine/standards/sourced_rules.json` IDs: `BP-01` (`170 WPM`), `BP-50` (`-14 LUFS` / `-1.0 dBTP`), `BP-51` (`dialogue anchor <= 5 LU`), `BP-52` (`music >= 10 LU, bed >= 15 LU under speech`), `BP-53` (`sidechain duck 6–12 dB`), `BP-83` (`shot hold CV >= 0.20`), `BP-117` (`J/L cuts`), `BP-120` (`pre-reveal vacuum 0.8–1.2s @ -42 dBFS`), `BP-121` (`Murch Law of 2.5: same_colour_layers 2.5, spread_layers 5`), `BP-122` (`acoustic perspective`), `BP-126` (`30° / lens tiers`), `BP-130` (`Reinhard colour transfer`), `BP-133` (`CLIP identity & lip-sync`). | `explainer_engine/standards/sourced_rules.json` (`158` rules) | `docs/SOURCED_RULES.md` (`L57–214`) | `explainer_engine/qa/targets.py`, `audio/sound_director.py`, `edit/motion_lint.py` | `pytest tests/unit/test_sourced_rules.py tests/unit/test_sourced_rules_sync.py` |
| **`CORR-08`** | **Audio Loudness Standards vs House Target `-14 LUFS` (`SRC-01`, `SRC-02`, `CHG-10`)** | `7312f660` described `-14.0 LUFS` and `LRA 5–9 LU` as mandatory ITU-R BS.1770-5 / EBU R 128 broadcast requirements. | ITU-R BS.1770-5 defines only the **measurement algorithm**; EBU R 128 mandates **`-23.0 LUFS`** for broadcast; and EBU Tech 3343 v4 states there is **no universal LRA ceiling**. `-14.0 LUFS` (`BP-50`) and `<= 5.0 LU` dialogue-to-mix anchor (`BP-51`) are CrossWorld's **binding house rules** designed for YouTube playback normalization. | `explainer_engine/qa/targets.py:1–170` & `docs/SOURCED_RULES.md:105–108` | [ITU-R BS.1770-5 Official Specification](https://www.itu.int/rec/R-REC-BS.1770/en) | [EBU R 128 Recommendation](https://tech.ebu.ch/publications/r128) & EBU Tech 3343 v4 (`docs/research/CRAFT_SOURCES_2026-10.md`) | `pytest tests/unit/test_sourced_audio.py tests/unit/test_scorecard.py` |
| **`CORR-09`** | **Speech Information Rate & WPM Studies (`SRC-05`, `SRC-06`, `§15.4`)** | `7312f660` conflated Pellegrino et al. (2011) (`7` languages) with Coupé et al. (2019) (`17` languages, `~39 bits/s`), and called Brysbaert (2019)'s `183 WPM` oral reading rate `"conversational speech"`. | Separated and cited all four primary studies accurately: Pellegrino et al. (2011) (`7` languages, syllable density vs rate trade-off), Coupé et al. (2019) (`17` languages, `39.15 ± 5.10 bits/s`), Brysbaert (2019) (`238 WPM` silent reading, `183 WPM` oral reading), Yuan et al. (2006) (`152–170 WPM` conversational topic averages), and Rodero (2012/2020) (`180 WPM` radio/ad comprehension). | [Coupé et al. (2019) *Science Advances* `PMC6984970`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6984970/) & [Pellegrino et al. (2011) *Language*](https://www.cambridge.org/core/journals/language/article/abs/crosslinguistic-perspective-on-speech-information-rate/8690E5D7B9D99CE4F54DC3C4A1AB3A2D) | [Brysbaert (2019) *J. Mem. Lang.* `PMC6758568`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/) & [Yuan et al. (2006) *Interspeech*](https://www.isca-archive.org/interspeech_2006/yuan06_interspeech.pdf) | [Rodero (2012) UPF Repository](https://repositori.upf.edu/bitstreams/132a1675-b3a3-4bd5-8edc-976a80727538/download) & [Rodero (2020)](https://www.researchgate.net/publication/336819723_Do_Your_Ads_Talk_Too_Fast_To_Your_Audio_Audience_How_Speech_Rates_of_Audio_Commercials_Influence_Cognitive_and_Physiological_Outcomes) | `pytest tests/unit/test_syllables.py tests/unit/test_rhythm_profile.py` |
| **`CORR-10`** | **Walter Murch's Rule of Six (`BP-128`) & Law of 2.5 (`BP-121`) (`SRC-13`, `SRC-14`)** | Earlier notes treated Rule of Six percentages (`51/23/10/7/5/4%`) as hard mathematical cut-scoring weights and simplified Law of 2.5 to `"max 2 foreground elements"`. | Murch's Rule of Six is an **editorial priority hierarchy** (partially tongue-in-cheek, ranking Emotion and Story above 2D/3D continuity), and his Law of 2.5 caps **same-colour spectral layers at `2.5` (`int(2.5) = 2` in `sound_director.py:785`) while allowing up to `5` layers spread across distinct spectral bands (`spread_layers: 5` in `BP-121`)**. Both remain `REVIEW` craft heuristics (`D-59`). | `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` of *In the Blink of an Eye* p. 18 & *Dense Clarity*) | [Walter Murch — *Dense Clarity — Clear Density* PDF](https://rompusnetwork.org/portfolio/dense_clarity_by_walter_murch.pdf) | `explainer_engine/audio/sound_director.py:780–792` (`BP-121`) & `production/assemble.py:714` (`BP-128`) | `pytest tests/unit/test_sound_director.py tests/unit/test_assemble_video_v2.py` |
| **`CORR-11`** | **LTX-2.5 Open-Source PyTorch (`8k+1`, `BP-139`) vs Hosted REST API (`SRC-03`, `CHG-08`)** | `7312f660` stated `8k+1` as a universal LTX rule and marked `BP-139` as a `FAIL` invariant. | Open-source self-hosted LTX (`aivideo/pod/clips.py`, `training/pods/p12/p12c_ltx.py`) requires `F = 8k + 1` frames and `width/height % 32 == 0` (`BP-139`, `severity: "REVIEW"` in `core/contracts.py:60–67`), whereas the hosted LTX-2.5 API (`api.ltx.io`) takes discrete second durations (`6..20s` on Fast 720p/1080p; `6/8/10s` on 1440p/4K and Pro). | `explainer_engine/core/contracts.py:10, 60–67` & `training/video_qa.py:515–520` | [LTX Open-Source PyTorch API Docs](https://docs.ltx.io/open-source-model/integration-tools/pytorch-api) & [arXiv:2601.03233](https://arxiv.org/abs/2601.03233) | [LTX-2.5 Hosted API Support Matrix](https://docs.ltx.io/models/ltx-2-5) | `pytest tests/unit/test_contracts.py tests/unit/test_video_qa_clip_rows.py` |
| **`CORR-12`** | **`BP-169` `shots_per_min` vs `mrbeast_12min_video_mold (1).json` (`§15.5`, `CHG-07`)** | `§15.5` in `7312f660` listed `18, 28, 138, 50, 20` shots (`36, 28, 21.2, 16.7, 20` cuts/min) from a stale pre-bundle table, creating a fake discrepancy with `BP-169`. | Direct summation on `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) proves the 5 zones actually contain **`14, 24, 111, 75, 30` shots** (`30s, 60s, 390s, 180s, 60s`), which equals **`28.0, 24.0, 17.08, 25.0, 30.0` shots/min**—matching `BP-169`'s `shots_per_min_target` (`28.0, 24.0, 17.0, 25.0, 30.0`) in `sourced_rules.json`! | `mrbeast_12min_video_mold (1).json` (`zones_5` & `reference_timeline_254_shots`) | `explainer_engine/standards/sourced_rules.json` (`BP-169`, `L2792–2889`) | `explainer_engine/scripting/rhythm_lint.py` & `edit/rhythm_profile.py` | `pytest tests/unit/test_rhythm_profile.py tests/unit/test_rhythm_lint.py` |

#### Table 15.7B — Comprehensive External & Compendium Source Correction Register (`SRC-01` through `SRC-48`)

| Source ID | Claim / Parameter in Roadmap or Research Compendium | Original Source Cited | Direct Primary Verification URL / Repo Proof | Verification Method | Evidence Grade | Forensic Audit Verdict & Required Action |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`SRC-01`** | K-weighted loudness (`LKFS`/`LUFS`) and True-Peak (`dBTP`) measurement algorithm; Argon house target `-14.0 LUFS` (`pass_band: [-15.0, -13.0]`, `true_peak_max: -1.0 dBTP`, `BP-50`) | ITU-R BS.1770-5 + Repo `BP-50` (`qa/targets.py`) | [ITU-R BS.1770-5 Official Recommendation](https://www.itu.int/rec/R-REC-BS.1770/en) + `explainer_engine/qa/targets.py` (`BP-50`) | Direct web browse + repo verification (`CORR-08`) | **`[PRIMARY-STANDARD]`** (algorithm) / **House `FAIL` Rule** (`-14 LUFS` `BP-50`) | **VERIFIED & RE-SCOPED (`CORR-08`)**. ITU-R BS.1770-5 defines the measurement algorithm; `-14.0 LUFS` is CrossWorld's binding house target (`BP-50`), not an ITU requirement. |
| **`SRC-02`** | Broadcast loudness (`-23.0 LUFS`), context-dependent Loudness Range (`LRA`), dialogue anchor (`<= 5.0 LU`, `BP-51`), stem floors (`10/15 LU`, `BP-52`), and sidechain ducking (`6–12 dB`, `BP-53`) | EBU R 128 / EBU Tech 3343 v4 + Repo `BP-51..53` | [EBU R 128 Recommendation](https://tech.ebu.ch/publications/r128) + `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` of EBU Tech 3343 v4) | Direct `[pdftotext]` verification in repo + `qa/targets.py` & `audio/duck.py` | **`[PRIMARY-STANDARD]`** (EBU R 128) / **House Rules** (`BP-51..53`) | **VERIFIED & RE-KEYED (`CORR-07`, `CORR-08`)**. Re-keyed from `BP-73..75` to `BP-50..53`; noted that EBU Tech 3343 sets no universal LRA cap. |
| **`SRC-03`** | Self-hosted open-source LTX-2 / LTX-2.5 causal 3D VAE frame lattice `F = 8k + 1` and `width/height % 32 == 0` (`BP-139`, `REVIEW`) vs Hosted LTX-2.5 API discrete second durations (`6..20s` / `6, 8, 10s`) | Lightricks LTX-2 Docs & Technical Report | [LTX PyTorch API Docs](https://docs.ltx.io/open-source-model/integration-tools/pytorch-api), [LTX-2.5 Hosted API Matrix](https://docs.ltx.io/models/ltx-2-5), & [arXiv:2601.03233](https://arxiv.org/abs/2601.03233) | Direct web browse + `core/contracts.py:60–67` (`CORR-11`) | **`[PRIMARY-STANDARD]`** | **VERIFIED & DISTINGUISHED (`CORR-11`)**. Separated self-hosted PyTorch `8k+1` (`BP-139`, `REVIEW`) from hosted LTX-2.5 API second buckets. |
| **`SRC-04`** | ElevenLabs `eleven_v4` (`Odom`) and `eleven_v3` do **not** support SSML `<break>` tags; pauses use punctuation (`—`, `...`), bracketed audio tags (`BP-171` in `audio/hype_read.py`), and room-tone padding (`BP-60` in `audio/pause_pad.py`) | ElevenLabs Official Documentation | [ElevenLabs — How can I add pauses?](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses) & [Eleven v3/v4 Model Guide](https://elevenlabs.io/docs/overview/models#eleven-v3) | Direct web browse + `audio/hype_read.py` & `audio/pause_pad.py` (`CORR-02`) | **`[PRIMARY-STANDARD]`** | **VERIFIED & CORRECTED (`CORR-02`)**. Module ownership fixed (`hype_read.py` for tags, `pause_pad.py` for gaps, `narrator_polish.py` for FFmpeg EQ). |
| **`SRC-05`** | Cross-linguistic syllable rate vs information density trade-off (`7` languages in Pellegrino et al. 2011) and `39.15 ± 5.10 bits/s` (`6.63 ± 1.15 syll/s`) across `17` languages in Coupé et al. (2019) | Pellegrino et al. (2011) *Language* & Coupé et al. (2019) *Science Advances* | [Pellegrino et al. (2011) *Language*](https://www.cambridge.org/core/journals/language/article/abs/crosslinguistic-perspective-on-speech-information-rate/8690E5D7B9D99CE4F54DC3C4A1AB3A2D) & [Coupé et al. (2019) *Science Advances* `PMC6984970`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6984970/) | Direct full-text verification (`PMC6984970` + `CRAFT_SOURCES_2026-10.md`, `CORR-09`) | **`[PRIMARY-STANDARD]`** | **RE-SCOPED & SEPARATED (`CORR-09`)**. Separated the 2011 (7-language) and 2019 (17-language, `39.15 bits/s`) papers; neither sets YouTube WPM targets (`BP-169` is a house `REVIEW` rule). |
| **`SRC-06`** | English silent reading (`238 WPM` non-fiction, `260 WPM` fiction), oral reading (`183 WPM`), conversational speech (`152–170 WPM` topic means, `111–291 WPM` spread), and radio/ad comprehension (`180 WPM`) | Brysbaert (2019), Yuan et al. (2006), & Rodero (2012/2020) | [Brysbaert (2019) `PMC6758568`](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/), [Yuan et al. (2006) *Interspeech*](https://www.isca-archive.org/interspeech_2006/yuan06_interspeech.pdf), & [Rodero (2020)](https://www.researchgate.net/publication/336819723_Do_Your_Ads_Talk_Too_Fast_To_Your_Audio_Audience_How_Speech_Rates_of_Audio_Commercials_Influence_Cognitive_and_Physiological_Outcomes) | Direct academic verification (`CORR-09`) | **`[PRIMARY-STANDARD]`** | **VERIFIED & SEPARATED (`CORR-09`)**. Grounds `BP-01` (`170 WPM`, accepted `155–185 WPM`, `D-92` item 2) while keeping `BP-169` zone WPM targets as house `REVIEW` rules. |
| **`SRC-07`** | Acoustic pause insertion (`0.5–1.0s`) and prosodic segmentation improve listening comprehension and recall in dense narrative speech | MacGregor et al. (2010) | [MacGregor et al. (2010) — Listening to natural pauses (`PMC2865204`)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2865204/) | Direct academic source check | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Grounds `BP-120` pre-reveal vacuum (`0.8–1.2s`) and `BP-171` `pre_reveal_silence_s: [0.5, 1.0]`. |
| **`SRC-08`** | Multimedia Coherence, Signaling & Redundancy Principles (concise on-screen accent bubbles `<= BP-38 max_words` and `<= 26` chars/line `BP-84`, held `BP-27` reading time) | Mayer & Moreno (2003) + Repo `BP-27`, `BP-38`, `BP-84` | [Mayer & Moreno (2003) — Nine Ways to Reduce Cognitive Load](https://www.tandfonline.com/doi/abs/10.1207/S15326985EP3801_6) + `production/silent.py:31–39` | Direct academic + repo verification | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Grounds `D-62`/`D-63` (`BP-27`, `BP-38`, `BP-84`) short accent bubbles instead of wall-of-text captions. |
| **`SRC-09`** | Curiosity / Information-Gap Theory (opening an explicit question in the first `85` words / `30s` and holding the central answer until `>=90%` of spoken words, `BP-04` `ENG-5`) | Loewenstein (1994) + Repo `BP-04` (`qa/engagement.py`) | [Loewenstein (1994) — The Psychology of Curiosity (CMU PDF)](https://www.cmu.edu/dietrich/sds/docs/loewenstein/PsychofCuriosity.pdf) | Direct academic + `qa/engagement.py` check (`CORR-06`) | **`[CRAFT-HEURISTIC]`** | **VERIFIED (`REVIEW` per `D-94`)**. Theoretical foundation for `BP-04` (`ENG-5`) and `BP-42` (`ENG-7`); exact `85`-word and `90%` numbers are house `REVIEW` thresholds. |
| **`SRC-10`** | MrBeast production principles: `0–30s` title/thumbnail promise validation, `1–3min` spectacle-to-story transition, `3min` & `6min` re-hooks, "wow factor", abrupt ending (`BP-43`) | Jimmy Donaldson — *How to Succeed in MrBeast Production* | [How to Succeed in MrBeast Production (Full PDF)](https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf) | Direct PDF inspection + `CRAFT_SOURCES_2026-10.md` | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Primary creator source for `AB01..AB05`, `AB07`, `AB12` (`BP-43`), and `BP-169` 5-zone structure. |
| **`SRC-11`** | MrBeast retention analysis, hook iteration, and multi-track dubbing/voice pacing strategy | Colin & Samir — *Inside MrBeast's $100M Production Company* | [Colin & Samir — Inside MrBeast's Production Company (YouTube)](https://www.youtube.com/watch?v=c8VcUnz3nVc) | Direct video metadata & transcript check | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Confirms focus on first-30s retention drop-off and mid-video re-hooks. |
| **`SRC-12`** | "YouTube Voice" prosody mechanics: wide F0 pitch excursions (`>=5.0 st` IQR), emphatic lengthening, and hyper-articulated clause endings (`BP-171`) | PBS Terra / Studio — *Why Everything on YouTube Sounds the Same* | [Why Everything on YouTube Sounds the Same (YouTube)](https://www.youtube.com/watch?v=T2G8s-6ZP9I) | Direct video check + `CRAFT_SOURCES_2026-10.md` | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-171` prosody wave (`audio/hype_read.py`, `REVIEW`). |
| **`SRC-13`** | Walter Murch's **Rule of Six**: Emotion (`51%`), Story (`23%`), Rhythm (`10%`), Eye-trace (`7%`), 2D Plane (`5%`), 3D Space (`4%`) (`BP-128`) | Walter Murch — *In the Blink of an Eye* (2nd ed., 2001, p. 18) | `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` of p. 18) & `sourced_rules.json` (`BP-128`) | Direct `[pdftotext]` verification in repo (`CORR-10`) | **`[CRAFT-HEURISTIC]`** | **VERIFIED & RE-SCOPED (`CORR-10`)**. Pedagogical editorial hierarchy (`REVIEW`); never used as a mathematical cut-scoring formula or handle-frame justification. |
| **`SRC-14`** | Walter Murch's **Law of 2.5** (*Dense Clarity — Clear Density*): `<= 2.5` same-colour spectral layers (`int(2.5) = 2`), up to `5` layers spread across distinct spectral bands (`BP-121`) | Walter Murch — *Dense Clarity — Clear Density* (Transom Review, 2005) | [Walter Murch — *Dense Clarity — Clear Density* PDF](https://rompusnetwork.org/portfolio/dense_clarity_by_walter_murch.pdf) & `docs/research/CRAFT_SOURCES_2026-10.md` | Direct PDF + repo `audio/sound_director.py:785` verification (`CORR-10`) | **`[CRAFT-HEURISTIC]`** | **VERIFIED & REFINED (`CORR-10`)**. Tied to `BP-121` (`same_colour_layers: 2.5, spread_layers: 5`, `REVIEW`). |
| **`SRC-15`** | Average Shot Length (ASL) evolution and `1/f` non-metronomic shot-length correlation across 150 Hollywood films (grounding `BP-83` `hold_cv_min: 0.20` in `edit/motion_lint.py`) | Cutting, DeLong & Nothelfer (2010), *Psychological Science* 21(3):432–439 | [Cutting et al. (2010) — Attention and the Evolution of Hollywood Film](https://journals.sagepub.com/doi/10.1177/0956797610361679) | Direct academic verification + `edit/motion_lint.py:35` (`CORR-07`) | **`[PRIMARY-STANDARD]`** (paper) / **`[HYPOTHESIS]`** (`BP-83` `CV >= 0.20`) | **VERIFIED & RE-KEYED (`CORR-07`)**. Re-keyed from `BP-28` (text safe area) to **`BP-83`** (`edit/motion_lint.py`, `REVIEW`). |
| **`SRC-16`** | Stephen Follows (`2025-04-21` & `2026-03-06`) film cut-count and trailer pacing analyses | Stephen Follows Substack | [Stephen Follows — How many cuts are there in a film?](https://stephenfollows.com/p/how-many-cuts-are-there-in-a-film) & [How movie trailers manipulate time](https://stephenfollows.com/p/how-movie-trailers-manipulate-time) | Verified via search index | **`[CRAFT-HEURISTIC]`** | **RE-GRADED TO `[CRAFT-HEURISTIC]`**. Contextual background only; Argon's 5-zone shot rates (`28/24/17/25/30` shots/min) live in `BP-169` (`REVIEW`). |
| **`SRC-17`** | Official YouTube Audience Retention metrics (Intro `0–30s` share, Top moments, Spikes, Dips) replacing secondary SaaS blog `"55% retention"` claims | YouTube Help Center | [YouTube Help — Measure key moments for audience retention](https://support.google.com/youtube/answer/9314415) | Direct web browse (`CORR-01`) | **`[PRIMARY-STANDARD]`** | **VERIFIED (`CORR-01`)**. Purged secondary blog claims; confirmed YouTube publishes no fixed `55%` threshold or `90s` re-hook timer (`BP-48` & `BP-42` are house `REVIEW` rules). |
| **`SRC-18`** | Exact 5-zone (`14, 24, 111, 75, 30` shots = `28.0, 24.0, 17.08, 25.0, 30.0` shots/min) and 16-segment (`254` shots, `17,280` frames = `720.0s`, `2,066` words = `172.17` WPM) properties of `mrbeast_12min_video_mold (1).json` | `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) | Verified programmatically in Table `15.5A` & Table `15.5B` + `mold_254_shots_verified_digest.json` | Direct Python summation (`CORR-12`) | **`[FACT]`** (artifact math) / **`[HYPOTHESIS]`** (retention optimality) | **VERIFIED & CORRECTED (`CORR-12`)**. Replaced stale `18/28/138/50/20` counts with exact `14/24/111/75/30` counts matching `BP-169`. |
| **`SRC-19`** | Exact `152`-shot `VIDEO` LTX-2.5 handle-frame math (`10,368` usable frames; `14,552` at `>=12`/side vs `12,120` at `>=4`/side = `2,432` frames / `16.71%`; `12,392` transition-aware = `2,160` frames / `14.84%`) | `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) | Verified programmatically in `§15.6` & `mold_254_shots_verified_digest.json` | Direct Python verification | **`[FACT]`** (frame math) / **`[HYPOTHESIS]`** (`4`-frame handle sufficiency) | **VERIFIED (`M-10` & `CHG-08`)**. Tagged `REVIEW` pending `GATE-P1b`/`GATE-P2` clip boundary inspection. |
| **`SRC-20`** | Exact `16`-segment duration/word conservation (`S02` = `30.0s`, `12` shots, `88` words, `0.0s` discrepancy) and `24` Tulip Mania instance strings contaminating Layer 1/2 | `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) | Verified programmatically in Table `15.5B` | Direct Python verification | **`[FACT]`** | **VERIFIED (`M-12`)**. Retired stale `79.2s vs 59.2s` draft claim; Layer 1/2 Tulip Mania strings purged in `BATCH-M1`. |
| **`SRC-21`** | Qwen-Image-2.1 / Qwen-Image-Edit character & pose editing mechanics (`TIER_2` `qwen_nextpose` and base plate generation) | Alibaba Qwen-Image Documentation | [QwenLM/Qwen-Image Official Repository](https://github.com/QwenLM/Qwen-Image) + `config/cloud_pins.json` | Direct web + repo verification | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Pinned in `config/cloud_pins.json` (`D-78`, `D-80`). |
| **`SRC-22`** | CLIP ViT-B-32 hero-sheet cosine similarity (`explainer_engine/qa/identity.py`, `BP-133`, `REVIEW` only, `"calibrate on our hero sheets"`) vs external ArcFace literature | Repo `qa/identity.py` & `training/embed.py` (`BP-133`) | `explainer_engine/qa/identity.py:1–70` & [Radford et al. 2021 CLIP (`arXiv:2103.00020`)](https://arxiv.org/abs/2103.00020) | Direct repo code inspection (`CORR-05`) | **`[FACT]`** (repo uses CLIP) / **`[HYPOTHESIS]`** (`BP-133` threshold) | **CORRECTED (`CORR-05`)**. Replaced `qa/identity_gate.py` / `BP-130` ArcFace `0.65` claim with actual `qa/identity.py` (`BP-133`, CLIP ViT-B-32, uncalibrated `INFO`/`REVIEW`). |
| **`SRC-23`** | Reinhard et al. (2001) CIE LAB mean/std colour transfer (`BP-130`, `blend_max: 0.65` in `explainer_engine/finish/grade.py` and `production/assemble.py:749–791`) | Reinhard et al. (2001), *IEEE CG&A* 21(5):34–41 | [Reinhard et al. (2001) — Color Transfer between Images (IEEE)](https://ieeexplore.ieee.org/document/946629) + `finish/grade.py:34–115` | Direct paper + repo verification (`CORR-05`) | **`[PRIMARY-STANDARD]`** (method) / **`[HYPOTHESIS]`** (`BP-130` `0.65` blend cap) | **VERIFIED (`CORR-05`)**. Implemented in `explainer_engine/finish/grade.py` and `production/assemble.py`. |
| **`SRC-24`** | Character dialogue voice spine (`D-90`): fixed ElevenLabs character voice take read first -> bound into `audio_spine/2` (`audio/spine.py`) -> conditions LTX clip (`edit/router.py` `DIALOGUE_CU`) | `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-90`) & `audio/spine.py` | `explainer_engine/audio/spine.py:84` & `explainer_engine/edit/router.py:7, 79–90` + [LTX-2.5 Audio-to-Video Docs](https://docs.ltx.io/models/ltx-2-5) | Direct repo + LTX docs verification | **`[FACT]`** (`D-90`) / **`[PRIMARY-STANDARD]`** (LTX audio-to-video) | **VERIFIED (`CG-10`, `BATCH-M4`, `CHG-12`)**. Uses existing `audio/spine.py` and `edit/router.py` (`0` non-existent `character_voices.py` references). |
| **`SRC-25`** | 3-layer 2.5D parallax depth separation (`FG`, `MG`, `BG` alpha plates, `BP-35` `layers_min: 3` in `production/parallax.py`) | Multiplane camera grammar + Repo `production/parallax.py` | [Walt Disney Family Museum — Multiplane Camera](https://www.waltdisney.org/blog/multiplane-camera) + `production/parallax.py` (`BP-35`) | Direct source + repo verification | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Enforced by `explainer_engine/production/parallax.py` (`BP-35`, `REVIEW`). |
| **`SRC-26`** | Causal plot progression (`"because / therefore"` vs episodic `"and then"`, `ENG-2` in `qa/engagement.py`) and sentence-length ear rules (`BP-06` `median_max: 12, max_words: 20, hard_max_words: 25` in `narration_lint.py`) | Aristotle, *Poetics* + Repo `BP-06` & `qa/engagement.py` | [Aristotle's *Poetics* (MIT Classics)](https://classics.mit.edu/Aristotle/poetics.1.1.html) + `explainer_engine/scripting/narration_lint.py` (`BP-06`) | Direct text + repo check | **`[CRAFT-HEURISTIC]`** | **VERIFIED & DISTINGUISHED**. Note that in `sourced_rules.json`, `BP-06` is **sentence word-length (`median <= 12, max <= 25`)**, while flat-beat detection is `ENG-2` in `qa/engagement.py`! |
| **`SRC-27`** | 2K master delivery framing (`1920x1088 -> 2560x1440` at `24 fps` in `explainer_engine/finish/upscale.py`, `BP-167`, `D-85`, `D-92`) and `5` vertical `1440x2560` Shorts (`production/shorts.py` & `clip_shorts.py`) | Repo `finish/upscale.py`, `production/shorts.py`, `core/delivery.py` (`BP-167`) | `explainer_engine/finish/upscale.py:1–45` & `explainer_engine/production/shorts.py:1–50` | Direct repo code inspection | **`[FACT]`** | **VERIFIED**. Uses actual `finish/upscale.py`, `production/shorts.py`, and `production/clip_shorts.py` (purged non-existent `shorts_extract.py`). |
| **`SRC-28`** | FFmpeg `ebur128`, `highpass`, `afftdn`, `bass`, `equalizer`, and `alimiter` filterchains in `qa/frame_review.py`, `audio/narrator_polish.py`, and `production/assemble.py` | FFmpeg Official Filter Documentation | [FFmpeg Audio & Video Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html) | Direct documentation + repo check | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Matches `audio/narrator_polish.py:14–15` and `qa/frame_review.py:399`. |
| **`SRC-29`..`SRC-42`** | Benchmark Video Case Studies `CS-01` through `CS-14` (`2` per channel across MrBeast, Fern, Kurzgesagt, The Infographics Show, AlternateHistoryHub, Kings and Generals, Oversimplified) | Primary YouTube URLs in Table `15.2B` (`CS-01..CS-14`) | All `14` direct `https://www.youtube.com/watch?v=...` URLs in Table `15.2B` + [OverSimplified Wiki (`CS-13` `17:53`)](https://oversimplified.fandom.com/wiki/The_French_Revolution_(Part_1)) & [IMDb `tt10540208`](https://www.imdb.com/title/tt10540208/) | Direct metadata check + epistemic separation (`CORR-01`) | **`[CRAFT-HEURISTIC]`** (qualitative mechanics) / **`[HYPOTHESIS]`** (quantitative extrapolations) | **VERIFIED & EPISTEMICALLY BOUNDED (`CORR-01`)**. Qualitative hook/pivot mechanics separated from unlogged quantitative cut/WPM estimates; `CS-13` runtime updated with dual references (`17:53`). |
| **`SRC-43`** | ElevenLabs Prohibited Use Policy (`09 Oct 2026`, `V-51` in `docs/MARKET_RESEARCH.md:106`): §3 living-person consent requirement & post-mortem harm/rights clause; §4 political candidates/elected officials ban | ElevenLabs Official Prohibited Use Policy (`09 Oct 2026`) | [ElevenLabs Prohibited Use Policy (`09 Oct 2026`)](https://elevenlabs.io/use-policy) + `docs/MARKET_RESEARCH.md:106` (`V-51`) + `production/silent.py:246–267` (`PV-55`) | Direct full-text web browse (`4.1`) + repo check (`CORR-05`) | **`[PRIMARY-STANDARD]`** | **VERIFIED (`CORR-05`)**. Confirmed exact `09 Oct 2026` policy sections (§3 & §4 match `V-51` in `MARKET_RESEARCH.md:106` and `PROGRESS.md:1472` verbatim!) and removed the invented `"1926"` cutoff. |
| **`SRC-44`** | Dutch Tulip Mania (1636–1637) historical baseline vs Charles Mackay (1841) myths | Anne Goldgar (2007), *Tulipmania* (Univ. of Chicago Press) | [University of Chicago Press — *Tulipmania* by Anne Goldgar](https://press.uchicago.edu/ucp/books/book/chicago/T/bo5414921.html) | Direct academic book verification | **`[PRIMARY-STANDARD]`** | **VERIFIED (`M-12`)**. Reinforces why Layer 3's 1637 Tulip Mania grid is strictly `reference_only: true`. |
| **`SRC-45`** | Acoustic distance perception: HF air absorption (`>6 kHz` shelf roll-off) and direct-to-reverberant ratio (`D/R`) for `far` (`Wide`) vs `near` (`Close-Up`) shots (`BP-122`) | Zahorik, Brungart & Bronkhorst (2005), *Acta Acustica* | [Zahorik et al. (2005) — Auditory Distance Perception in Humans](https://apps.dtic.mil/sti/citations/ADA437509) + `production/assemble.py:291–296` | Direct psychoacoustic + repo check | **`[PRIMARY-STANDARD]`** (principle) / **`[HYPOTHESIS]`** (`BP-122` numbers, `REVIEW`) | **VERIFIED**. Enforced dynamically from `sourced_rules.T("BP-122", ...)` in `production/assemble.py`. |
| **`SRC-46`** | Style-LoRA prompt contract (`LT-65` in `qa/style_prompt.py` and `scripting/film_shots.py`) and episode colour/light phrase (`AC-17` in `compose/episode_look.py`) | Repo `qa/style_prompt.py`, `compose/episode_look.py`, `design/palette.py` | `explainer_engine/qa/style_prompt.py:67–85` & `explainer_engine/compose/episode_look.py:1–60` | Direct repo code inspection (`CORR-03`) | **`[FACT]`** | **VERIFIED (`CORR-03`)**. Replaced non-existent `scripting/prompt_lint.py` and `production/episode_look.py` with actual `qa/style_prompt.py` and `compose/episode_look.py`. |
| **`SRC-47`** | Forced word-level alignment (`audio/scribe_words.py` + `audio/local_words.py` -> `words_raw.json` -> `audio/pause_pad.py` -> `words.json`) | Bain et al. (2023) WhisperX + Repo `audio/scribe_words.py` | [m-bain/whisperX Official Repository](https://github.com/m-bain/whisperX) & [arXiv:2303.00747](https://arxiv.org/abs/2303.00747) + `audio/scribe_words.py` | Direct paper + repo verification | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Grounds the word-timestamp alignment contract in `production/script.py` and `production/timing.py`. |
| **`SRC-48`** | Complete purge of all `22` `google.com/search?q=` wrapper URLs and all non-existent `.py`/`.md` paths across `§1..§17` | Repo `explainer_engine/docs_lint.py` & `repo_5013a55a.zip` | Verified via `PYTHONPATH=. python3 -m explainer_engine.docs_lint` (`0 finding(s)`) and regex audit (`0` search wrappers) | Direct Python verification | **`[FACT]`** | **VERIFIED**. `0` search-wrapper URLs and `0` non-existent existing-file claims remain anywhere in this document. |

## 16. Twelve-Field Evidence-Backed Proposed Change Specifications (`CHG-01` through `CHG-14`, 100% Aligned with `§8.1`, `§9.1..§9.10` & `repo_5013a55a`)

**[RECOMMENDATION]** Every proposed engineering change across `BATCH-M0` through `BATCH-M8B` is specified below using the mandatory **12-field structure** plus the explicit **`CURRENT MISCONCEPTION → VERIFIED CORRECTION → 2–3 SOURCES → TEST`** proof chain. Every file path and line number below is verified directly against `repo_5013a55a.zip` (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`) and matches `§8.1` (`CG-01..CG-14`) and `§9.1..§9.10` (`BATCH-M0..M8B`).

### `CHG-01` — Unify Master Mold v2.1.0 Contract (`config/master_mold_v2_1.json` & `docs/MASTER_MOLD_V2_1.md`) & Reconcile `M-01..M-12` + `D-92` `BP-168` (`BATCH-M1`)

1. **Change ID**: `CHG-01` (implements `CG-04`, `CG-05`, `BATCH-M1` `§9.2`, and `CORR-04`)
2. **Subsystem / Target File(s)**:
   * `config/master_mold_v2_1.json` *(NEW — normalized from `mrbeast_12min_video_mold (1).json` SHA-256 `2ca7f56f...`)*
   * `docs/MASTER_MOLD_V2_1.md` *(NEW — normalized from `mrbeast_12min_master_mold.md` SHA-256 `49cf3084...`)*
   * `docs/INDEX.md` *(existing — add link to `MASTER_MOLD_V2_1.md`)*
   * `explainer_engine/schemas/episode_mold.schema.json` *(NEW — `episode_mold/1`)*
   * `explainer_engine/scripting/mold_contract.py` *(NEW — loader & `canonical_bp_ref` resolver)*
   * `explainer_engine/core/contracts.py` (`L45–95`, register `episode_mold/1`)
   * `explainer_engine/standards/sourced_rules.json` (`BP-168` updated to match `D-92` item 7; `BP-169` `middle_calm_90_480s` adds `rehook_tts_tags: ["excited"]`)
   * `docs/SOURCED_RULES.md` (sync `BP-168` and `BP-169` descriptions)
   * `tests/unit/test_master_mold_contract.py` *(NEW)*
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-04`)**:
   * **[FACT]** The raw Mold files (`2ca7f56f...` and `49cf3084...`) contain the `12` internal discrepancies (`M-01..M-12` in §3.2), including duplicated threshold numbers violating `D-59`, dangling `BP-68`/`BP-155`/`BP-79` citations, mis-cited `BP-125`/`BP-84` still-motion strings, and `24` hardcoded 1637 Tulip Mania strings in Layer 1/2. Furthermore, in `sourced_rules.json`, **`BP-168` (`L2769–2791`) still holds pre-`D-92` thresholds (`go_retry_max: 2.0, pivot_retry_max: 3.0, go_review_min_per_min_max: 4.0`)**, contradicting the creator's binding decision in **`D-92` item 7 (`2026-11-01`: GO `<= 3` seeds/accepted shot and `<= 3` review min/finished min; PIVOT `(3, 6]`; ABANDON `> 6`)**!
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Commit `config/master_mold_v2_1.json` and `docs/MASTER_MOLD_V2_1.md` with all `M-01..M-12` resolved (matching `§9.2` `BATCH-M1`):
     1. Strip duplicate BP numbers in favor of `canonical_bp_ref` pointers resolved via `scripting/mold_contract.py` (`SR.T(bp_id, key)`), keeping the 2,066-word numbers strictly inside `reference_instance_metrics` (`classification: "reference_only"`).
     2. Purge all `24` Tulip Mania strings from Layer 1 and Layer 2 into `layer_3_reference_instance` (`reference_only: true`) and strip raw `#RRGGBB` hex strings outside `design/palette.json` (`D-22`).
     3. Update `BP-168` in `explainer_engine/standards/sourced_rules.json`, `docs/SOURCED_RULES.md`, and `explainer_engine/core/ledger.py:330–348` to reflect **`D-92` item 7**: `go_seeds_per_shot_max: 3.0` (where `seeds_per_shot = 1 + retries_per_shot`), `pivot_seeds_per_shot_max: 6.0` (`ABANDON` when `> 6.0`), `go_review_min_per_min_max: 3.0`, `pivot_review_min_per_min_max: 6.0` (`ABANDON` when `> 6.0`), and `go_forecast_usd_max: 12.0` (`REVIEW` severity).
5. **Why Needed**:
   * Enforces `D-59` single-home compliance, `D-22` hex hygiene, `ZI-09` topic-agnostic Layer 1/2 templates, and reconciles `BP-168` with `D-92` item 7.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-59`, `D-92` item 7, `D-94`).
     * `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` (`BP-168`, `BP-169`) & `explainer_engine/core/ledger.py:330–348`.
     * `SOURCE 3`: `tests/unit/test_sourced_rules.py`, `tests/unit/test_d92_creator_answers.py`, & `tests/unit/test_palette.py`.
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)** for `episode_mold/1` schema validity, `D-59` single-home compliance, and `D-22` hex ban; **House Rule (`REVIEW`)** for `BP-168` Go/Pivot/Abandon report rows (`core/ledger.py:330`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `docs/INDEX.md`, `explainer_engine/schemas/episode_mold.schema.json`, `explainer_engine/scripting/mold_contract.py`, `explainer_engine/core/contracts.py`, `explainer_engine/standards/sourced_rules.json`, `docs/SOURCED_RULES.md`, `explainer_engine/core/ledger.py`.
9. **Backward Compatibility & Migration Impact**:
   * Additive contract (`episode_mold/1`); all existing `/1..3` scripts and tests remain 100% compatible.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; `<15 ms` local validation time.
11. **Failure Modes & Rollback Plan**:
    * `test_sourced_rules.py`, `test_sourced_rules_sync.py`, and `test_palette.py` catch any duplicate threshold, unsynced doc row, or raw hex literal in CI.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_master_mold_contract.py tests/unit/test_sourced_rules.py tests/unit/test_sourced_rules_sync.py tests/unit/test_d92_creator_answers.py tests/unit/test_palette.py` passes with `0` failures.

### `CHG-02` — Fix `/4` Schema Dispatch Across All 11 `== "production_script/3"` Modules + Odom Span Polish & `KP-47` Zone Propagation (`BATCH-M0`)

1. **Change ID**: `CHG-02` (implements `CG-01`, `CG-02`, `CG-03`, `CG-14`, `BATCH-M0` `§9.1`, and `CORR-01`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/scripting/schema_version.py` *(NEW shared predicate helper)*
   * **All 11 modules in `repo_5013a55a.zip` that check `== "production_script/3"` (`SCENE_SCHEMA` / `BINDING`)**:
     1. `explainer_engine/scripting/scene_lint.py` (`L28`, `L139`)
     2. `explainer_engine/scripting/script_approval.py` (`L27`, `L51`)
     3. `explainer_engine/scripting/speech.py` (`L60`)
     4. `explainer_engine/scripting/story_lint.py` (`L34`, `L75`)
     5. `explainer_engine/production/beats.py` (`L45`, `L107`)
     6. `explainer_engine/production/editorial_gate.py` (`L31`, `L342`, `L347`)
     7. `explainer_engine/production/silent.py` (`L249`, `L276`)
     8. `explainer_engine/production/staging.py` (`L418`)
     9. `explainer_engine/production/validate.py` (`L89`)
     10. `explainer_engine/production_gate.py` (`L89`)
     11. `explainer_engine/audio/layers.py` (`L53`)
   * **Plus the 3 verified P0 bugfix sites from `§9.1`**:
     12. `explainer_engine/production/__main__.py` (`L119`) & `explainer_engine/audio/narrator_polish.py` (`polish_narrator_spans_in_place`)
     13. `explainer_engine/scripting/film_shots.py` (`L449` `compose()`) & `explainer_engine/schemas/film_shots.schema.json` (propagate `rhythm_zone` so `scripting/shot_prompt_lint.py:183–191` `KP-47` fires)
     14. `explainer_engine/llm/claude_api.py` (`L1063–1067`, 2-line `load_job` string `system` fix from [PR #112](https://github.com/vano1919/explainer-engine/pull/112))
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-01`)**:
   * **[FACT]** In `7312f660`, `CHG-02` misnamed the schema field as `doc.get("schema_version")` and cited non-existent lines in `production/script.py` (`206` lines), `narrator_polish.py` (`46` lines), `sample.py` (`177` lines), and non-existent `production/shot_prompt_checks.py`.
   * **[FACT]** Direct inspection of `repo_5013a55a.zip` (`§8.1` `CG-01..CG-03` and `§9.1`) proves the **exact real code contract**: `schemas/production_script.schema.json:17–25` defines `"schema": {"enum": ["production_script/1", "production_script/2", "production_script/3", "production_script/4"]}` (while `production/timing.py:256` writes `"script_schema": doc.get("schema")` onto `production_timed/1`, which `audio/layers.py:53` reads). Because the 11 modules below check exact equality `== "production_script/3"`, passing `"schema": "production_script/4"` silently disables v3+ gates and reverts `beats.py` to `/2` metronome rules:

| # | Verified Repository Module & Line (`5013a55a`) | Exact Existing Code Line in `5013a55a` | Exact Failure on `"schema": "production_script/4"` | Verified Fix Using `scripting/schema_version.py` |
| ----- | ----- | ----- | ----- | ----- |
| **1** | `explainer_engine/scripting/scene_lint.py:28, 139` | `SCENE_SCHEMA = "production_script/3"` / `return doc.get("schema") == SCENE_SCHEMA` | `scene_rules(doc)` returns `False` -> skips `SC-01..SC-12` on `/4`! | `return is_scene_script(doc)` (`True` on `/3` and `/4`, `False` on `/1..2`). |
| **2** | `explainer_engine/scripting/script_approval.py:27, 51` | `BINDING = "production_script/3"` / `if doc.get("schema") != BINDING:` | Skips `PV-53` script approval verification on `/4`! | `if not is_scene_script(doc): return []`. |
| **3** | `explainer_engine/scripting/speech.py:60` | `if doc.get("schema") == "production_script/3" and len(lines) >= 3 ...` | Skips `DW-11` hero signature-word usage check on `/4`! | `if is_scene_script(doc) and len(lines) >= 3 ...`. |
| **4** | `explainer_engine/scripting/story_lint.py:34, 75` | `SCENE_SCHEMA = "production_script/3"` / `"FAIL" if doc.get("schema") == SCENE_SCHEMA else "REVIEW"` | Downgrades missing `drama` block (`ST-00`) from `FAIL` to `REVIEW` on `/4`! | `"FAIL" if is_scene_script(doc) else "REVIEW"`. |
| **5** | `explainer_engine/production/beats.py:45, 107` | `SCENE_SCHEMA = "production_script/3"` / `return doc.get("schema") == SCENE_SCHEMA` | `scene_rules(doc)` returns `False` -> **reverts `/4` to `/2` 1.5s metronome rules (`VB-01`, `VB-08`)**! | `return is_scene_script(doc)` (`True` on `/3` and `/4`). |
| **6** | `explainer_engine/production/editorial_gate.py:31, 342, 347` | `SCENE_SCHEMA = "production_script/3"` / `if doc.get("schema") == SCENE_SCHEMA:` | Skips `EG-19` (`editorial_review/2` requirement) and `EG-23` (`story_page`) on `/4`! | `if is_scene_script(doc):` at both L342 and L347. |
| **7** | `explainer_engine/production/silent.py:249, 276` | `if doc.get("schema") != "production_script/3": return []` | **Disables `PV-55` (`D-62` living-person voice ban!) and `PV-56` (`D-63` bubble cap) on `/4`!** | `if not is_scene_script(doc): return []` at both L249 and L276. |
| **8** | `explainer_engine/production/staging.py:418` | `if doc.get("schema") == "production_script/3":` | Skips `CS-07` staged-dialogue master check on `/4`! | `if is_scene_script(doc):`. |
| **9** | `explainer_engine/production/validate.py:89` | `if doc.get("schema") != "production_script/3": return []` | Skips `PV-57` shot-opening / hero reveal validation on `/4`! | `if not is_scene_script(doc): return []`. |
| **10** | `explainer_engine/production_gate.py:89` | `if doc.get("schema") == _sa.BINDING:` | Skips Gate `0.9` (`script_approval`) in `production_gate.py` on `/4`! | `if is_scene_script(doc):`. |
| **11** | `explainer_engine/audio/layers.py:53` | `return timed.get("script_schema") == BEATS.SCENE_SCHEMA` | `silence_is_default(timed)` returns `False` -> flags quiet beats with `AL-02` on `/4`! | `return is_scene_script(timed)` (reads `timed.get("script_schema") or timed.get("schema")`). |

4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Execute the exact 5-step implementation specified in `§9.1` (`BATCH-M0`, `L976–1002`):
     1. Create `explainer_engine/scripting/schema_version.py` with `schema_name(doc_or_schema)` (reading `doc.get("schema") or doc.get("script_schema")`), `is_scene_script(doc_or_schema)` (`in {"production_script/3", "production_script/4"}`), and `is_zoned_rhythm_script(doc_or_schema)` (`== "production_script/4"`).
     2. Update all 11 modules in the table above to call `is_scene_script(...)`.
     3. Add `polish_narrator_spans_in_place(narration_wav, words, toks, doc)` in `explainer_engine/audio/narrator_polish.py` and call it at `explainer_engine/production/__main__.py:119` so Odom's narrator spans are polished even when `S.has_dialogue(doc)` is `True`.
     4. Propagate `rhythm_zone` onto composed video shot dicts in `explainer_engine/scripting/film_shots.py:compose()` (`L449`) so `explainer_engine/scripting/shot_prompt_lint.py:183–191` (`KP-47`, `BP-172`) fires during `film_shots check`.
     5. Cherry-pick the 2-line `claude_api.py:1066` string `system` fix from [PR #112](https://github.com/vano1919/explainer-engine/pull/112).
5. **Why Needed**:
   * Prevents `/4` scripts from bypassing `PV-55` (`D-62` living-person voice ban), `PV-53` (`script_approval`), `SC-01..12` (`scene_lint`), `EG-19`/`EG-23` (`editorial_gate`), `KP-47` (`shot_prompt_lint`), and `narrator_polish.py`.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `explainer_engine/schemas/production_script.schema.json:17–25` & `explainer_engine/production/timing.py:256`.
     * `SOURCE 2`: Exact lines in the 11 modules (`scene_lint.py:139`, `script_approval.py:51`, `speech.py:60`, `story_lint.py:75`, `beats.py:107`, `editorial_gate.py:342,347`, `silent.py:249,276`, `staging.py:418`, `validate.py:89`, `production_gate.py:89`, `audio/layers.py:53`).
     * `SOURCE 3`: `explainer_engine/production/__main__.py:119`, `explainer_engine/audio/narrator_polish.py:1–46`, & `explainer_engine/scripting/shot_prompt_lint.py:183–191`.
7. **Rule Classification**:
   * **Hard Structural & Safety Invariant (`FAIL`)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/scripting/schema_version.py` *(NEW)* + the 16 existing files listed in `§9.1` (`L938–970`).
9. **Backward Compatibility & Migration Impact**:
   * 100% backward compatible: `/1`, `/2`, and `/3` scripts and `production_timed/1` files behave identically.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; `0 ms` overhead.
11. **Failure Modes & Rollback Plan**:
    * Unknown future schemas (`/5`) return `False` on `is_scene_script` unless explicitly added to `SCENE_SCHEMAS`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_production_script_schema.py tests/unit/test_claude_api.py tests/unit/test_narrator_polish.py tests/unit/test_shot_prompt_lint.py` passes with `0` failures.

### `CHG-03` — Wire 5-Zone Rhythm Profile (`BP-169`) Across `edit/board.py` (`BP-40`/`BP-84`), `edit/motion_lint.py`, `edit/shot_rules.py`, `scripting/film_shots.py` & `qa/scorecard.py` (`BATCH-M2` & `BATCH-M6`)

1. **Change ID**: `CHG-03` (implements `CG-07`, `BATCH-M2` `§9.3`, `BATCH-M6` `§9.7`, and `CORR-07`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/edit/rhythm_profile.py` (`L20–65`)
   * `explainer_engine/edit/board.py` (`L37–45`, `L146–156`)
   * `explainer_engine/edit/motion_lint.py` (`L28–36`, `L290–355`)
   * `explainer_engine/edit/shot_rules.py` (`L20–95`)
   * `explainer_engine/scripting/film_shots.py` (`L780–875`)
   * `explainer_engine/scripting/narration_lint.py` (`L90–180`)
   * `explainer_engine/qa/scorecard.py` (`L120–210`)
   * `tests/unit/test_rhythm_end_to_end.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-07`)**:
   * **[FACT]** In `7312f660`, `CHG-03` cited non-existent `explainer_engine/edit/rhythm.py` and `explainer_engine/qa/retention.py`. In the actual repository (`5013a55a`), calm-era rhythm checks live in **`explainer_engine/edit/board.py`** (`BP-40` `MAX_PER_MIN = 10` pics/min, `BP-84` `MIN_SHOT = 2.5s`), **`explainer_engine/edit/motion_lint.py`** (`BP-40`, `BP-83`), **`explainer_engine/edit/shot_rules.py`** (`BP-85`), **`explainer_engine/scripting/film_shots.py`** (`BP-107` `11–17` shots/min), **`explainer_engine/scripting/narration_lint.py`** (`BP-06` flat `12`-word median), and **`explainer_engine/qa/scorecard.py`**.
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Wire `rhythm_profile.resolve_profile_name(doc)` into those exact existing modules (matching `§9.3` and `§9.7`):
     1. In `edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, and `scripting/film_shots.py`: when `rhythm_profile == "mrbeast_animated"`, delegate shot-rate (`shots_per_min_band`), shot-length (`shot_len_s_band`), and static-still hold caps (`static_still_max_s_by_zone`) to `edit/rhythm_profile.py` (`BP-169`) and `scripting/rhythm_lint.py` (`BP-170`), while keeping `BP-84` `bubble_chars_per_line: 26` and `BP-38` `max_words` active across all profiles (`M-09`).
     2. In `scripting/narration_lint.py`: evaluate per-segment median sentence words against `BP-169`'s zone `median_words_max` (`8 / 9 / 11 / 9 / 7` words); keep intra-zone sentence-length contrast (`std_words >= 2.0`, `CD-04`) strictly as a **`REVIEW` hypothesis (`D-94`)**, never a hard `FAIL`.
5. **Why Needed**:
   * Prevents calm-era `BP-40` (`<=10` pics/min), `BP-84` (`>=2.5s` shot floor), and `BP-107` (`11–17` shots/min) from rejecting valid `/4` `mrbeast_animated` scripts.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[HYPOTHESIS]`**:
     * `SOURCE 1`: `explainer_engine/edit/board.py:37–45, 146–156`, `edit/motion_lint.py:28–36`, & `scripting/film_shots.py:780–875`.
     * `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` (`BP-40`, `BP-83`, `BP-84`, `BP-107`, `BP-169`) & `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-94`).
     * `SOURCE 3`: [Cutting, DeLong & Nothelfer (2010) *Psychological Science*](https://journals.sagepub.com/doi/10.1177/0956797610361679) (`1/f` shot-length variance grounding `BP-83`).
7. **Rule Classification**:
   * **House Profile Rule (`REVIEW` for `BP-169` and `BP-83` per `D-94`; `FAIL` for `BP-84` bubble caps and `BP-170` static still caps)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `edit/rhythm_profile.py`, `edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, `scripting/film_shots.py`, `scripting/narration_lint.py`, `qa/scorecard.py`.
9. **Backward Compatibility & Migration Impact**:
   * `/1..3` (`calm_docudrama`) scripts keep all existing `BP-40`, `BP-84`, `BP-85`, and `BP-107` checks unchanged.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; eliminates false-positive calm-era lint failures on `/4` scripts.
11. **Failure Modes & Rollback Plan**:
    * Defaulting `resolve_profile_name` to `calm_docudrama` on `/1..3` scripts guarantees zero regression on existing unit tests.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_rhythm_end_to_end.py tests/unit/test_board_bubbles_duck.py tests/unit/test_film_shots.py` passes with `0` failures.

### `CHG-04` — Profile-Aware Visual Lane Budgets (`A..D`) in `BP-109`, `scripting/variant_plan.py` & `scripting/film_shots.py` (`BATCH-M1` & `BATCH-M2`)

1. **Change ID**: `CHG-04` (implements `M-03`, `BATCH-M2` `§9.3`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/standards/sourced_rules.json` (`BP-109`, `BP-141`)
   * `explainer_engine/scripting/variant_plan.py` (`L65–70`, `L160–260`) *(Note: in `explainer_engine/scripting/`, NOT `production/`)*
   * `explainer_engine/scripting/film_shots.py` (`L46–48`, `L780–825`)
   * `explainer_engine/schemas/production_script.schema.json`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`)**:
   * **[FACT]** In `7312f660`, `CHG-04` listed `explainer_engine/production/variant_plan.py` instead of the actual path **`explainer_engine/scripting/variant_plan.py`**. In `sourced_rules.json`, `BP-109` (`status: "house"`, `severity: "REVIEW"`, `D-93`) sets `lane_share: {"video": 0.6, "still": 0.3, "helper": 0.1}` with `lane_tolerance: 0.05` (`±5%`), while `BP-141` (`status: "hypothesis"`, `severity: "REVIEW"`) defines `episode_structure_profiles` `A..D` (`A` & `D` `non_character_max: 0.45`, `B` & `C` `non_character_max: 0.80`).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Wire `scripting/variant_plan.py` and `scripting/film_shots.py` so `mrbeast_animated` variants check `shots_per_min` against `BP-169` (`18.0–28.0` shots/min) instead of `BP-107` (`11–17` shots/min), resolve `non_character_max` (`0.45` for `A/D`, `0.80` for `B/C`) from `BP-141`, and preserve **`REVIEW` severity** on both `BP-109` (`D-94`: `"the 60/30/10 mix numbers are approximate and must not cost the video anything, so BP-109's tolerance is +-5%"`) and `BP-141`.
5. **Why Needed**:
   * Aligns `scripting/variant_plan.py` and `scripting/film_shots.py` with `M-03`, `D-93`, and `D-94`.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `explainer_engine/scripting/variant_plan.py:67, 164–255` & `explainer_engine/scripting/film_shots.py:46–48, 781–820`.
     * `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` (`BP-109`, `BP-141`).
     * `SOURCE 3`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-93`, `D-94`).
7. **Rule Classification**:
   * **House Rule (`REVIEW`)** for `BP-109` (`±5%` lane share) and **Hypothesis (`REVIEW`)** for `BP-141` (`non_character_max`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/scripting/variant_plan.py`, `explainer_engine/scripting/film_shots.py`, `explainer_engine/schemas/production_script.schema.json`.
9. **Backward Compatibility & Migration Impact**:
   * Preserves `calm_docudrama` (`BP-107`) defaults on `/1..3` scripts and existing `napoleon_vs_genghis` variant tests.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost.
11. **Failure Modes & Rollback Plan**:
    * Unknown profile IDs raise a `KeyError`/`ContractError` in `variant_plan.py`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_variant_plan.py tests/unit/test_film_shots.py` passes with `0` failures.

### `CHG-05` — Implement 12-Anchor Narrative Architecture (`AB01..AB12`) & Spoken-Only `BP-04` (`ENG-5`) Check in `qa/engagement.py` & `scripting/story_lint.py` (`BATCH-M1` & `BATCH-M2`)

1. **Change ID**: `CHG-05` (implements `M-05`, `CG-05`, `BATCH-M1` `§9.2`, `BATCH-M2` `§9.3`, and `CORR-06`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/qa/engagement.py` (`L51–62`, `L162–178`)
   * `explainer_engine/scripting/story_lint.py` (`L140–260`)
   * `explainer_engine/schemas/production_script.schema.json` (`segments[].anchor_beat_id`, `segments[].rehook_spike`)
   * `explainer_engine/scripting/stage_guard.py` (`SEG_STORY`)
   * `tests/unit/test_engagement.py`, `tests/unit/test_story_engine.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-06`)**:
   * **[FACT]** As verified in `qa/engagement.py:55, 163–171` (`§9.2` `L1060–1078` and ChatGPT's P1 finding):
     1. `_text(seg)` joins `line["text"] for line in seg["lines"]` **without filtering out `voiced: false` silent bubble lines (`D-62`)**, so silent speech bubbles inflate the word count!
     2. In `qa/engagement.py:165–171`, `ENG-5` loops over `segs` looking for `(seg.get("drama") or {}).get("function") == "resolution"`; if no segment has that marker, the loop finishes without emitting any `ENG-5` finding!
     3. Per `D-94` (`2026-11-01 20:03 UTC`: `"retention rules (hook, beats, no outro) as REVIEW-only"`) and `sourced_rules.json` (`BP-04`: `severity: "REVIEW"`), `ENG-5` (`BP-04`) is a **`REVIEW` finding** (`sev("BP-04") == "REVIEW"`), whereas missing `AB01..AB12` structural fields or missing resolution markers on a `/4` Template D script are structural `story_lint.py` (`ST-25`) checks.
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Implement the exact single-source `resolution_word_share(doc)` function in `explainer_engine/qa/engagement.py` (as specified in `§9.2` `L1060–1078` and `§9.3` `L1146–1148`):
     1. Filter lines to `line.get("voiced", True) is not False` (excluding `voiced: false` silent bubble lines per `D-62`), strip inline `[tags]` via `re.sub(r"\[[^\]]*\]", " ", text)`, and tokenize with `re.findall(r"[a-z0-9']+", clean.lower().replace("’", "'"))`.
     2. Emit an explicit `ENG-5` finding when no segment/line carries a resolution marker (`drama.function == "resolution"`, `discloses_answer: true`, or `anchor_beat_id == "AB12_FINAL_SYNTHESIS_AND_HARD_CUT"`), closing the silent loop fall-through.
     3. Preserve `BP-04`'s `REVIEW` severity (`sev("BP-04") == "REVIEW"` per `D-94`) in `qa/engagement.py`, while checking `AB01..AB12` ordering and `BP-142` played scene turns (`turn_slots_D: [4, 6, 8, 10, 11, 13]`, `FAIL`) in `scripting/story_lint.py`.
5. **Why Needed**:
   * Fixes the `voiced: false` word-count bug and missing-marker silent pass in `qa/engagement.py:163–171` while honoring `D-94`'s `REVIEW`-only policy on retention rules.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[CRAFT-HEURISTIC]`**:
     * `SOURCE 1`: `explainer_engine/qa/engagement.py:51–62, 162–177` & `explainer_engine/production/silent.py:27–29, 83–85`.
     * `SOURCE 2`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-62`, `D-94`) & `explainer_engine/standards/sourced_rules.json` (`BP-04`, `BP-142`).
     * `SOURCE 3`: [Loewenstein (1994) — The Psychology of Curiosity (CMU PDF)](https://www.cmu.edu/dietrich/sds/docs/loewenstein/PsychofCuriosity.pdf) & [How to Succeed in MrBeast Production PDF](https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf).
7. **Rule Classification**:
   * **House / Binding `REVIEW` Rule** for `BP-04` (`ENG-5` `answer_after_share >= 0.90` per `D-94`); **Hard House Invariant (`FAIL`)** for `BP-142` (`ST-24` / `VP-08` played scene turns at slots `[4, 6, 8, 10, 11, 13]`) and `BP-43` (`ENG-8` sign-off lexicon ban).
8. **Exact Schema / Code / Config Surface Affected**:
   * `qa/engagement.py`, `scripting/story_lint.py`, `scripting/stage_guard.py`, `schemas/production_script.schema.json`.
9. **Backward Compatibility & Migration Impact**:
   * Lines omitting `"voiced"` default to `True` (`line.get("voiced", True)`), preserving 100% backward compatibility on narrator-only scripts.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; `<5 ms` CPU execution.
11. **Failure Modes & Rollback Plan**:
    * Guards `total_spoken_words == 0` against `ZeroDivisionError`.
12. **Verification Test & Acceptance Criteria**:
    * All 9 unit tests in `tests/unit/test_engagement.py` and `tests/unit/test_story_engine.py` (`§9.3` `L1148`) pass with `0` failures.

### `CHG-06` — Correct Audio Module Ownership (`hype_read.py`, `pause_pad.py`, `narrator_polish.py`) & Zone-Aware `eleven_v4` Timing (`BATCH-M4`)

1. **Change ID**: `CHG-06` (implements `M-02`, `CG-02`, `CG-04`, `BATCH-M4` `§9.5`, and `CORR-02`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/hype_read.py` (`L30–95`, `BP-169` & `BP-171` tag formatting and `rehook_tts_tags` support)
   * `explainer_engine/audio/pause_pad.py` (`L77–135`, zone-aware `min_gap`: `0.18s` `BP-171` `hyped_min_gap_s` vs `0.26s` `MIN_GAP` in calm middle, room-tone fill `BP-60`)
   * `explainer_engine/audio/narrator_polish.py` (`L13–46`, add `polish_narrator_spans_in_place` for Odom's FFmpeg EQ/limiter chain)
   * `explainer_engine/production/compile.py` & `explainer_engine/production/__main__.py` (`L119`)
   * `tests/unit/test_hype_read.py`, `tests/unit/test_pause_pad.py`, `tests/unit/test_narrator_polish.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-02`)**:
   * **[FACT]** As corrected in `CORR-02` and `§9.5` (`BATCH-M4`), `audio/narrator_polish.py` (`46` lines) is strictly Odom's FFmpeg filterchain (`CHAIN = "volume=-0.6dB,highpass=f=60,afftdn=nr=8:nf=-50,bass=g=12:f=150:w=0.7,equalizer=f=300:t=q:w=1:g=-2,alimiter=limit=0.95"`), **not** a TTS tag reader! Meanwhile:
     1. `audio/hype_read.py:77` checks `if tag not in zone["tts_tags"]`, which flags `[excited]` on `S06` (`175–210s`) and `S09` (`330–375s`) re-hook spikes inside `middle_calm_90_480s` (`M-02`).
     2. `audio/pause_pad.py:77` (`pad_pauses`) uses a single global `MIN_GAP = 0.26s` across all zones instead of reading `BP-171`'s `hyped_min_gap_s = 0.18s` (`sourced_rules.json`) in hyped zones.
     3. `production/__main__.py:119` skips `narrator_polish.polish_in_place` whenever `S.has_dialogue(doc)` is `True` (`CG-02`).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Keep module responsibilities strictly separated (matching `§9.5` `BATCH-M4`):
     1. **`audio/hype_read.py` + `BP-169`**: Add `"rehook_tts_tags": ["excited"]` to `middle_calm_90_480s` in `BP-169` and allow `hype_read.check_prosody_plan` to accept `rehook_tts_tags` when `line.get("rehook_spike")` is `True` (`S06`, `S09`), keeping `HR-01..04` at `REVIEW` severity (`SR.level("BP-171", "REVIEW")`).
     2. **`audio/pause_pad.py`**: Extend `pad_pauses(words, audio, sr, min_gap=MIN_GAP, targets=None, zone_for_time=None)` so punctuated `CUT_MARKS` gaps inside `hyped` / `hyped_climax` zones use `SR.T("BP-171", "hyped_min_gap_s")` (`0.18s`) while `calm_story` (`middle_calm_90_480s`) and `calm_docudrama` keep `MIN_GAP = 0.26s`, inserting only the deficit `want - gap` of room tone (`BP-60`) at `quiet_point <= -46.0 dB`.
     3. **`audio/narrator_polish.py` + `production/__main__.py:119`**: Run `polish_narrator_spans_in_place` after `voice_check` and `pause_pad` so Odom's narrator spans receive `NP.CHAIN` without altering character dialogue spans or word timings (`abs(after - before) <= 1/30 s`).
5. **Why Needed**:
   * Aligns `CHG-06` 100% with the actual code in `audio/hype_read.py`, `audio/pause_pad.py`, `audio/narrator_polish.py`, and `§9.5` (`BATCH-M4`).
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[PRIMARY-STANDARD]`**:
     * `SOURCE 1`: `explainer_engine/audio/hype_read.py:1–110`, `audio/pause_pad.py:1–157`, & `audio/narrator_polish.py:1–46`.
     * `SOURCE 2`: [ElevenLabs — How can I add pauses?](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses) & [Eleven v3/v4 Model Guide](https://elevenlabs.io/docs/overview/models#eleven-v3).
     * `SOURCE 3`: Measured `eleven_v4` word-alignment files in `examples/day1_v2/words_raw.json`, `examples/titans_from_zero/words.json`, & `examples/syndicate_wars_ep1/words.json`.
7. **Rule Classification**:
   * **Hypothesis (`REVIEW`)** for `BP-171` (`HR-01..04`); **Binding (`REVIEW`/`FAIL`)** for `BP-60` room-tone pause fill and `ConfigError` if `narrator_polish` shifts duration by `> 1/30 s`.
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/hype_read.py`, `audio/pause_pad.py`, `audio/narrator_polish.py`, `production/compile.py`, `production/__main__.py`, `standards/sourced_rules.json` (`BP-169`).
9. **Backward Compatibility & Migration Impact**:
   * Default `zone_for_time=None` in `pause_pad.pad_pauses` preserves `MIN_GAP = 0.26s` for all `/1..3` scripts and existing unit tests.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` API cost (pure local waveform processing).
11. **Failure Modes & Rollback Plan**:
    * If `quiet_point` exceeds `QUIET_DB = -46.0 dB` (inside a word or breath), `pause_pad.py:94–96` skips the insertion so no consonant is ever clipped.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_hype_read.py tests/unit/test_pause_pad.py tests/unit/test_narrator_polish.py` passes with `0` failures.

### `CHG-07` — Implement 6-Step Bounded Timeline Engine (`explainer_engine/edit/bounded_timeline.py`) & Explicit Infeasibility Contract (`BATCH-M5`)

1. **Change ID**: `CHG-07` (implements `CG-11` and `BATCH-M5` `§9.6`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/edit/bounded_timeline.py` *(NEW — canonical path matching `§4.7`, `§6.1`, `CG-11`, and `§9.6` `BATCH-M5`)*
   * `explainer_engine/production/timing.py` (`L170–260`)
   * `tests/unit/test_bounded_timeline.py` *(NEW — canonical test path matching `§9.6`)*
3. **Current Repository Behavior & Prior Misconception (`5013a55a`)**:
   * **[FACT]** In `7312f660`, `CHG-07` used the path `production/timeline_compiler.py` whereas `§4.7`, `§6.1`, `CG-11`, and `§9.6` (`BATCH-M5`) use `explainer_engine/edit/bounded_timeline.py` and `tests/unit/test_bounded_timeline.py`, and cited `BP-28`/`BP-30` instead of `BP-83` (`hold_cv_min: 0.20, similar_run_max: 3` in `edit/motion_lint.py`). Currently, `production/timing.py` computes shot start/end times from word timestamps (`words.json`) without projecting onto exact `17,280`-frame (`720.0s` at `24 fps`) segment totals or checking `BP-83` hold variance.
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Implement `explainer_engine/edit/bounded_timeline.py` executing the 6-step deterministic algorithm from `§9.6` (`L1284–1296`) plus the **Step 7 Mathematical Infeasibility Contract**:
     1. **Step 1**: Speech-clause (`UR-12` in `edit/shot_rules.py`) + `1/f` duration proposal within `[-0.18, +0.18]`.
     2. **Step 2**: Hard lane & zone clamp (`VIDEO` `<=8.0s` target / `<=10.0s` cap `KP-06` and `BP-172` zone clip bands; `STILL` `<= static_still_max_s_by_zone` `1.5/2.0/2.5s` for Tier 1/2 or `<=5.0s` for Tier 3 `BP-170`; `HELPER` `<=7.0s` Kuleshov cap `BP-141`).
     3. **Step 3**: Constrained slack-weighted projection onto exact integer frames at `24 fps` (`sum(frames) == segment_target_frames`, `17,280` total for `720.0s`).
     4. **Step 4**: Self-hosted LTX-2.5 `8k+1` generation frame + transition-aware `BP-128` handle derivation for `VIDEO` shots (`CHG-08`).
     5. **Step 5 & 6**: Diagnostic evaluation (`CV >= 0.20` per **`BP-83`**, `max_similar_run <= 3` per **`BP-83`**) with local `±4`-frame transfer between adjacent same-lane shots when a segment's `CV < 0.20` or `similar_run > 3`.
     6. **Step 7 (Explicit Infeasibility Contract)**: If post-TTS segment audio duration or word-boundary lock makes it mathematically impossible to satisfy `17,280`-frame conservation, `UR-12` legal cut points (never cutting mid-word), and `BP-170` static-still hold caps simultaneously, `bounded_timeline.py` **never relaxes `BP-170` (`FAIL`) or `UR-12` (`FAIL`)**; it raises `TimelineInfeasibleError(code="BT-INFEASIBLE-01..03")` with an exact `SegmentTrimOrExpandDirective(segment_id, current_words, target_word_delta, reason)` so the segment's lines are adjusted before any GPU spend.
5. **Why Needed**:
   * Unifies the module name (`explainer_engine/edit/bounded_timeline.py`) and rule ID (`BP-83`) across `§4.7`, `§6.1`, `§8.1`, `§9.6`, and `§16`, and guarantees `17,280`-frame conservation.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[PRIMARY-STANDARD]`**:
     * `SOURCE 1`: `explainer_engine/edit/motion_lint.py:28–36` (`BP-83`), `edit/shot_rules.py` (`UR-12`), & `production/timing.py`.
     * `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` (`BP-83`, `BP-141`, `BP-169`, `BP-170`, `BP-172`).
     * `SOURCE 3`: [Cutting, DeLong & Nothelfer (2010) *Psychological Science*](https://journals.sagepub.com/doi/10.1177/0956797610361679) (`1/f` shot-length structure).
7. **Rule Classification**:
   * **Hard Invariant (`FAIL`)** for `17,280`-frame conservation, `UR-12` legal cut points, `BP-170` still caps, and `BT-INFEASIBLE` halt; **Hypothesis (`REVIEW`)** for `BP-83` (`CV >= 0.20`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/edit/bounded_timeline.py` *(NEW)*, `explainer_engine/production/timing.py`, `tests/unit/test_bounded_timeline.py` *(NEW)*.
9. **Backward Compatibility & Migration Impact**:
   * `/1..3` scripts continue using variable-duration `production/timing.py` without `bounded_timeline.py` projection.
10. **Cost / Latency / Quality Tradeoff**:
    * `<30 ms` CPU solver; prevents wasted GPU renders on mis-timed segments.
11. **Failure Modes & Rollback Plan**:
    * Halts cleanly with `TimelineInfeasibleError` before `Stage 3` / `BATCH-M8B` paid runs.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_bounded_timeline.py` passes on the 254-shot Mold fixture (`14/24/111/75/30` shots) and on synthetic speech-overrun/underrun infeasibility fixtures.

### `CHG-08` — Reconcile Open-Source PyTorch LTX `8k+1` (`BP-139` `REVIEW`) vs Hosted LTX-2.5 API & Transition-Aware Handle Frames (`BP-128`) in `assemble.py` & `aivideo/shotplan.py` (`BATCH-M5`)

1. **Change ID**: `CHG-08` (implements `M-10`, `BATCH-M5` `§9.6`, and `CORR-11`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/production/assemble.py` (`L685–755`, `L894`)
   * `explainer_engine/core/contracts.py` (`L60–67`, `CN-08` `BP-139`)
   * `explainer_engine/training/video_qa.py` (`L515–520`, `CLIP-02` `BP-139`)
   * `explainer_engine/aivideo/shotplan.py` & `explainer_engine/training/pods/p12/p12c_ltx.py`
   * `explainer_engine/standards/sourced_rules.json` (`BP-128`, `BP-139`)
   * `tests/unit/test_assemble_video_v2.py`, `tests/unit/test_video_qa_clip_rows.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a` & `CORR-11`)**:
   * **[FACT]** In `7312f660`, `CHG-08` cited non-existent `explainer_engine/production/ltx_generate.py`, marked `BP-139` as a `FAIL` rule (when `sourced_rules.json` and `core/contracts.py:10, 60` explicitly define `BP-139` as `status: "hypothesis"`, `severity: "REVIEW"`), and did not distinguish the self-hosted open-source RunPod PyTorch path (`8k+1` frames, `size_multiple: 32`) from the hosted LTX-2.5 REST API (`6..20s` / `6, 8, 10s` duration buckets).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Implement in the actual repository modules (`production/assemble.py`, `aivideo/shotplan.py`, `edit/bounded_timeline.py`):
     1. **Separate Self-Hosted PyTorch (`BP-139`) vs Hosted LTX-2.5 API**: On the self-hosted RunPod ComfyUI/PyTorch path (`aivideo/pod/clips.py`, `p12c_ltx.py`), enforce `F = 8k + 1` (`BP-139`, `REVIEW` in `core/contracts.py:60–67` and `training/video_qa.py:515`); if routing through the hosted LTX-2.5 API (`docs.ltx.io/models/ltx-2-5`), request the smallest supported discrete second bucket (`6, 8, 10s` at `24 fps`) covering `usable_frames + 2 * handle_frames`.
     2. **Transition-Aware `BP-128` Handle Hypothesis (`[HYPOTHESIS]`, `REVIEW`)**: In `production/assemble.py:714–727`, keep `handle_frames >= 12` per side on shots bounded by `BP-129` whip-pans (`whip_frames: [8, 10]`) or `BP-31` dissolves (`dissolve_s: 1.0`), and allow `handle_frames >= 4` per side on hard/J/L-cut `VIDEO` shots after `GATE-P1b` empirical verification (saving `2,160` generated frames = `14.84%` across the `152` `VIDEO` shots, or `2,432` frames = `16.71%` if all `152` use `>=4` handles/side).
5. **Why Needed**:
   * Fixes the non-existent `ltx_generate.py` path, preserves `BP-139`'s `REVIEW` severity (`D-59`), and distinguishes self-hosted vs hosted LTX-2.5 constraints.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[PRIMARY-STANDARD]`** + **`[FACT]`** + **`[HYPOTHESIS]`**:
     * `SOURCE 1`: `explainer_engine/production/assemble.py:685–755`, `core/contracts.py:10, 60–67`, & `training/video_qa.py:515–520`.
     * `SOURCE 2`: [LTX Open-Source PyTorch API Docs](https://docs.ltx.io/open-source-model/integration-tools/pytorch-api) & [Lightricks LTX-2 Technical Report `arXiv:2601.03233`](https://arxiv.org/abs/2601.03233).
     * `SOURCE 3`: [Hosted LTX-2.5 API Documentation & Support Matrix](https://docs.ltx.io/models/ltx-2-5).
7. **Rule Classification**:
   * **Hypothesis (`REVIEW`)** for both `BP-139` (`CN-08`, `CLIP-02`) and `BP-128` (`assemble.py:727`) per `D-59`.
8. **Exact Schema / Code / Config Surface Affected**:
   * `production/assemble.py`, `edit/bounded_timeline.py`, `aivideo/shotplan.py`, `standards/sourced_rules.json` (`BP-128`).
9. **Backward Compatibility & Migration Impact**:
   * Existing `test_assemble_video_v2.py` and `test_contracts.py` remain 100% green.
10. **Cost / Latency / Quality Tradeoff**:
    * Saves `2,160` LTX frames (`14.84%` GPU time) on hard-cut shots while protecting optical transitions with `>=12` handle frames.
11. **Failure Modes & Rollback Plan**:
    * If `GATE-P1b` (`L1–L3` clips) shows VAE boundary flicker beyond frame `4`, keep `handle_frames: [12, 16]` for all shots in `BP-128`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_assemble_video_v2.py tests/unit/test_contracts.py tests/unit/test_video_qa_clip_rows.py` passes with `0` failures.

### `CHG-09` — Integrate 3-Tier Still Motion Ladder (`BP-35`, `BP-132`, `BP-170`) Across `edit/dramatic_still.py`, `production/parallax.py`, `edit/router.py` & `production/assemble.py` (`BATCH-M5` & `BATCH-M6`)

1. **Change ID**: `CHG-09` (implements `M-04`, `M-08`, `CG-06`, `CG-12`, `BATCH-M5` `§9.6`, and `BATCH-M6` `§9.7`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/edit/dramatic_still.py` (`L25–142`)
   * `explainer_engine/schemas/dramatic_still.schema.json`
   * `explainer_engine/production/parallax.py` (`BP-35`)
   * `explainer_engine/edit/router.py` & `explainer_engine/schemas/shot_route.schema.json`
   * `explainer_engine/production/assemble.py` (`materialize_lane_clips`)
   * `tests/unit/test_dramatic_still.py`, `tests/unit/test_shot_router.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`)**:
   * **[FACT]** Across the `76` `STILL` shots in `mrbeast_12min_video_mold (1).json`, `55` exceed `BP-170`'s `static_still_max_s_by_zone` (`2` `TIER_1`, `36` `TIER_2`, `17` `TIER_3`), and `37` shot `qa_gate` strings mis-cite `BP-125` (which is `area: "maps"` altitude change `4.0–8.0s`!) instead of `BP-35`, `BP-132`, and `BP-170` (`M-08`).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Execute the exact `BATCH-M5` (`§9.6` `L1298–1307`) and `BATCH-M6` (`§9.7` `L1380–1390`) specification:
     1. Re-key still-motion citations from `BP-125`/`BP-84` to `BP-35` (Tier 1 3-layer parallax), `BP-132` (blink/moving hold), and `BP-170` (Tier 3 dramatic state change).
     2. Keep `BP-170` (`FAIL` severity) and `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`) strictly enforced on **both Tier 1 (`parallax_25d`) and Tier 2 (`qwen_nextpose`)** until `CD-03` is approved after `GATE-P1b`. Only Tier 3 (`cutout_relocation >= 0.25` with `min_subject_area_frac >= 0.08` or `plate_swap >= 0.30`) unlocks holds above `1.5/2.0/2.5s` up to `5.0s`.
     3. Wire `assemble.materialize_lane_clips` (`BATCH-M6`) to render `STILL_HOLD` (`dramatic_still.py` / `parallax.py`), `HELPER` (`edit/visual_compensator.py`), and upscaled `VIDEO` (`finish/upscale.py`) into `2560x1440 @ 24 fps` `.mp4` clips for `assemble.build_video_v2`.
5. **Why Needed**:
   * Guarantees zero relaxation of `BP-170` (`FAIL`) while completing 3-lane clip materialization (`CG-12`).
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `explainer_engine/edit/dramatic_still.py:1–142` & `explainer_engine/production/parallax.py`.
     * `SOURCE 2`: `explainer_engine/standards/sourced_rules.json` (`BP-35`, `BP-125`, `BP-132`, `BP-170`).
     * `SOURCE 3`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-93`, `D-94`).
7. **Rule Classification**:
   * **Hard House Invariant (`FAIL`)** for `BP-170`; **Binding/Hypothesis (`REVIEW`)** for `BP-35` and `BP-132`; **Creator Decision (`CD-03`)** for any Tier 2 extension.
8. **Exact Schema / Code / Config Surface Affected**:
   * `edit/dramatic_still.py`, `schemas/dramatic_still.schema.json`, `production/parallax.py`, `edit/router.py`, `schemas/shot_route.schema.json`, `production/assemble.py`.
9. **Backward Compatibility & Migration Impact**:
   * Existing `test_dramatic_still.py` and `test_shot_router.py` pass without modification.
10. **Cost / Latency / Quality Tradeoff**:
    * Tier 1 and Tier 3 run on CPU compositor (`$0.00` GPU video cost).
11. **Failure Modes & Rollback Plan**:
    * Over-cap Tier 1/2 stills are rejected by `dramatic_still.py` (`FAIL`) and clamped/split by `bounded_timeline.py`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_dramatic_still.py tests/unit/test_shot_router.py tests/unit/test_parallax.py` passes with `0` failures.

### `CHG-10` — Harmonize Canonical Audio Rules (`BP-50..53`, `BP-117..122`) & Two-Axis Audio Accounting Across `audio/sound_director.py`, `audio/layers.py`, `qa/targets.py` & `production/assemble.py` (`BATCH-M6`)

1. **Change ID**: `CHG-10` (implements `M-11`, `BATCH-M6` `§9.7` `WP-R10`, `CORR-07`, `CORR-08`, and `CORR-10`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/sound_director.py` (`L9–15`, `L59–62`, `L300–465`, `L715–795`)
   * `explainer_engine/audio/layers.py` (`L51–55`, `L100–230`)
   * `explainer_engine/audio/duck.py` (`BP-53`) & `explainer_engine/audio/acoustics.py` (`BP-121`, `BP-122`)
   * `explainer_engine/qa/targets.py` (`L1–170`, `BP-50`, `BP-51`, `BP-52`, `BP-61`) & `explainer_engine/qa/scorecard.py` (`L126–198`)
   * `explainer_engine/production/assemble.py` (`L195–525`)
   * `tests/unit/test_sound_director.py`, `tests/unit/test_sourced_audio.py`, `tests/unit/test_scorecard.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`, `CORR-07`, `CORR-08`, `CORR-10`)**:
   * **[FACT]** In `7312f660`, `CHG-10` cited non-existent `finish/loudness.py` and mis-mapped audio rules to `BP-15` and `BP-73..75`. In `repo_5013a55a`, loudness and stem targets live in **`explainer_engine/qa/targets.py`** and **`explainer_engine/qa/scorecard.py`** (`BP-50` `-14.0 LUFS` / `-1.0 dBTP` `FAIL`, `BP-51` dialogue anchor `<= 5.0 LU` `REVIEW`, `BP-52` music `>= 10 LU` & bed `>= 15 LU` under voice `FAIL`), sidechain ducking lives in **`explainer_engine/audio/duck.py`** and **`production/assemble.py`** (`BP-53` `6–12 dB`, house `9 dB`), J/L cuts live in **`audio/sound_director.py`** (`BP-117`), pre-reveal vacuums live in **`BP-120`** (`0.8–1.2s` at `-42.0 dBFS`), Murch's Law of 2.5 lives in **`BP-121`** (`same_colour_layers: 2.5, spread_layers: 5` in `sound_director.py:785`), and acoustic perspective lives in **`BP-122`** (`assemble.py:291–296, 480–481`).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Execute `WP-R10` (`§9.7` `L1372–1379`) using the exact canonical `BP-*` IDs and modules:
     1. Replace hardcoded EQ strings in `config/master_mold_v2_1.json` with symbolic `"perspective": "far" | "mid" | "near"` keys resolved from `SR.T("BP-122", ...)` in `production/assemble.py:291–296` (`M-11`).
     2. In `audio/layers.py`, evaluate `AL-02` against the active zone's `sfx_events_per_min_band` (`BP-169`) on `mrbeast_animated` scripts.
     3. In `audio/sound_director.py`, verify at least one `BP-120` pre-reveal vacuum (`0.8–1.2s` at `-42.0 dBFS`) lands before `climax_660_720s` (`S15`), enforce `BP-121` (`same_colour_layers: 2.5`, `spread_layers: 5`, `sfx_pan_max: 0.45`, `REVIEW`), and keep `BP-50..53` stem mix and loudness checks in `qa/targets.py` and `qa/scorecard.py` alongside the `68% / 20% / 12%` primary-driver timeline partition (`REVIEW`).
5. **Why Needed**:
   * Fixes all `BP-*` ID mappings and non-existent `finish/loudness.py` references in `CHG-10` while preserving `D-59` compliance.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[PRIMARY-STANDARD]`** + **`[CRAFT-HEURISTIC]`** + **`[FACT]`**:
     * `SOURCE 1`: `explainer_engine/qa/targets.py:1–170`, `audio/sound_director.py:1–65, 441–465, 767–792`, & `production/assemble.py:195–525`.
     * `SOURCE 2`: [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en) & [EBU R 128](https://tech.ebu.ch/publications/r128) + EBU Tech 3343 v4 (`docs/research/CRAFT_SOURCES_2026-10.md`).
     * `SOURCE 3`: [Walter Murch — *Dense Clarity — Clear Density* PDF](https://rompusnetwork.org/portfolio/dense_clarity_by_walter_murch.pdf) & [Zahorik et al. (2005) Auditory Distance Perception](https://apps.dtic.mil/sti/citations/ADA437509).
7. **Rule Classification**:
   * **Binding House `FAIL` Gate** for `BP-50` (`-14 LUFS`, `-1.0 dBTP`) and `BP-52` (`music >= 10 LU`, `bed >= 15 LU` under voice); **Binding/Hypothesis `REVIEW`** for `BP-51`, `BP-53`, `BP-117`, `BP-120`, `BP-121`, `BP-122`, and `68/20/12` primary-driver share.
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/sound_director.py`, `audio/layers.py`, `qa/targets.py`, `qa/scorecard.py`, `production/assemble.py`.
9. **Backward Compatibility & Migration Impact**:
   * 100% compatible with existing `sound_mix_manifest/2` and `assemble_report.json` contracts.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost.
11. **Failure Modes & Rollback Plan**:
    * Covered by `tests/unit/test_sourced_audio.py` and `tests/unit/test_sound_director.py`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_sound_director.py tests/unit/test_sourced_audio.py tests/unit/test_scorecard.py` passes with `0` failures.

### `CHG-11` — Enforce Relative Color Script (`AC-17`, `BP-130`, `BP-166`, `D-22`) & Calibrated CLIP Character Identity (`BP-133`) in Actual Repo Modules (`BATCH-M6`)

1. **Change ID**: `CHG-11` (implements `M-12`, `CORR-03`, and `CORR-05`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/compose/episode_look.py` (`L1–60`, `AC-17`) *(Note: in `compose/`, NOT `production/`)*
   * `explainer_engine/qa/style_prompt.py` (`L65–90`, `LT-65`) & `explainer_engine/scripting/film_shots.py` (`L120–125`, `L746–775`)
   * `explainer_engine/finish/grade.py` (`L34–115`, `BP-130` Reinhard CIE LAB transfer) & `explainer_engine/production/assemble.py` (`L749–791`)
   * `explainer_engine/training/video_qa.py` (`L101–225`, `BP-166` `sat_drift_max`, `luma_drift_max`, `hero_palette_max`)
   * `explainer_engine/qa/identity.py` (`L1–70`, `BP-133` CLIP ViT-B-32 hero-sheet cosine check, `REVIEW` only)
   * `explainer_engine/design/palette.py` (`D-22`)
   * `tests/unit/test_episode_look.py`, `tests/unit/test_style_prompt.py`, `tests/unit/test_identity_qa.py`, `tests/unit/test_palette.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`, `CORR-03`, `CORR-05`)**:
   * **[FACT]** In `7312f660`, `CHG-11` referenced three non-existent paths (`production/episode_look.py`, `scripting/prompt_lint.py`, `qa/color_continuity.py`, `qa/identity_gate.py`), confused `BP-130` (Reinhard colour transfer) with `BP-133` (character identity), and claimed `BP-133` uses ArcFace `0.65` as a `FAIL` gate when `explainer_engine/qa/identity.py:3–6` uses **CLIP ViT-B-32 (`training/embed.py`)** at **`REVIEW` severity** and explicitly forbids guessing `0.65` before hero-sheet calibration!
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Use the exact existing repository modules:
     1. **Prompt Colour/Light Phrase (`compose/episode_look.py` `AC-17` & `qa/style_prompt.py` `LT-65`)**: Enforce `<=10` colour/light words (`AC-17` `FAIL`) appended to style-LoRA prompts (`LT-65` `FAIL`) and ban raw `#RRGGBB` hex strings outside `design/palette.json` (`D-22` `FAIL` in `test_palette.py`).
     2. **Scene LAB Colour Transfer (`finish/grade.py` `BP-130` & `training/video_qa.py` `BP-166`)**: Apply Reinhard CIE LAB mean/std transfer capped at `blend_max: 0.65` (`BP-130`, `REVIEW`) in `finish/grade.py` / `production/assemble.py`, and evaluate `sat_drift_max: 0.08`, `luma_drift_max: 0.08`, `hero_palette_max: 0.15` (`BP-166`, `REVIEW`) in `training/video_qa.py`.
     3. **CLIP Character Identity (`qa/identity.py` `BP-133`)**: Keep `qa/identity.py` at **`REVIEW` / `INFO` severity (`BP-133`)** using `clip_embedder` (`training/embed.py`), and calibrate the empirical hero-sheet threshold during `GATE-P1b` (`Q1–Q3` plates) without ever hardcoding the uncalibrated `0.65` Blueprint guess as a `FAIL` gate.
5. **Why Needed**:
   * Eliminates all 4 non-existent path references in `CHG-11` and aligns 100% with `qa/identity.py`, `finish/grade.py`, `compose/episode_look.py`, `qa/style_prompt.py`, and `training/video_qa.py`.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[PRIMARY-STANDARD]`**:
     * `SOURCE 1`: `explainer_engine/qa/identity.py:1–70`, `finish/grade.py:34–115`, `compose/episode_look.py:1–60`, `qa/style_prompt.py:67–85`, & `training/video_qa.py:101–225`.
     * `SOURCE 2`: [Reinhard et al. (2001) — Color Transfer between Images (IEEE)](https://ieeexplore.ieee.org/document/946629).
     * `SOURCE 3`: [Radford et al. (2021) CLIP (`arXiv:2103.00020`)](https://arxiv.org/abs/2103.00020) & `explainer_engine/standards/sourced_rules.json` (`BP-130`, `BP-133`, `BP-166`).
7. **Rule Classification**:
   * **Hard Invariant (`FAIL`)** for `LT-65` (`qa/style_prompt.py`), `AC-17` (`compose/episode_look.py`), and `D-22` (`test_palette.py`); **Hypothesis (`REVIEW`)** for `BP-130`, `BP-133`, and `BP-166`.
8. **Exact Schema / Code / Config Surface Affected**:
   * `compose/episode_look.py`, `qa/style_prompt.py`, `finish/grade.py`, `training/video_qa.py`, `qa/identity.py`, `design/palette.json`.
9. **Backward Compatibility & Migration Impact**:
   * Zero breaking changes; preserves existing `qa_report/1` schema rows.
10. **Cost / Latency / Quality Tradeoff**:
    * Free CPU QA checks (`$0.00`).
11. **Failure Modes & Rollback Plan**:
    * Uncalibrated `qa/identity.py` reports cosine scores as `REVIEW` (`passed: True`) until a calibrated hero-sheet threshold is supplied.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_episode_look.py tests/unit/test_style_prompt.py tests/unit/test_identity_qa.py tests/unit/test_palette.py` passes with `0` failures.

### `CHG-12` — Wire `D-90` Character Voice Spine (`audio/spine.py` + `edit/router.py`) & `PV-55` / `V-51` Voice Safety (`production/silent.py`) (`BATCH-M4`)

1. **Change ID**: `CHG-12` (implements `CG-10`, `BATCH-M4` `§9.5`, and `CORR-05`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/spine.py` (`L80–210`, add `bind_character_takes`)
   * `explainer_engine/edit/router.py` (`L7`, `L77–92`, `DIALOGUE_CU` `audio_slice_sha256` routing)
   * `explainer_engine/audio/casting.py` & `explainer_engine/audio/voice_audition.py`
   * `explainer_engine/production/silent.py` (`L246–290`, `PV-55` `D-62` living-person voice ban & `PV-56` `D-63` bubble cap)
   * `tests/unit/test_audio_spine.py`, `tests/unit/test_silent_lines.py`, `tests/unit/test_voice_route_docs.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`, `CG-10`, `CORR-05`)**:
   * **[FACT]** In `7312f660`, `CHG-12` cited non-existent `audio/character_voices.py`, `production/ltx_generate.py`, and `governance/rights_gate.py`, and invented a `"post-1926 public figure"` rule.
   * **[FACT]** In `repo_5013a55a` (`§8.1` `CG-10` and `§9.5` `BATCH-M4`):
     1. **`explainer_engine/edit/router.py:77–90`** routes `DIALOGUE_CU` shots and requires `audio_spine/2.post_hoc_shots` to have `source == "clip"` and a non-null `clip_sha256` (`audio_slice_sha256`), whereas **`explainer_engine/audio/spine.py:114`** currently initializes `source: "planned", clip_sha256: None` until post-render `retime_post_hoc`!
     2. **`explainer_engine/production/silent.py:246–267`** (`check_real_people`, `PV-55`, `D-62`) bars any voiced line for a cast member with `traits.real_person == True` and `traits.living == True` (default `True`), grounded in **`V-51` (`docs/MARKET_RESEARCH.md:106` — [ElevenLabs Prohibited Use Policy, 09 Oct 2026](https://elevenlabs.io/use-policy))**: §3 bars cloning/synthesizing/impersonating any living person without explicit consent or any deceased person in a manner likely to cause harm or infringe post-mortem rights, and §4 bars impersonating political candidates or elected officials (`PROGRESS.md:1472`). Whether a deceased historical figure (`traits.living: false`) may be voiced remains explicitly **`OPEN` in `D-90` (`CD-06`)**—there is no `"1926"` cutoff!
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Execute the exact `BATCH-M4` (`§9.5` `L1238`) and `BATCH-M0` (`silent.py:249, 276`) changes:
     1. In `explainer_engine/audio/spine.py`, add `bind_character_takes(spine: dict, takes: dict[str, Path], fps: int) -> dict` which measures each pre-recorded ElevenLabs character take (`D-90`), sets `source="clip"` and `clip_sha256=<sha256>` on `post_hoc_shots`, and updates downstream frame offsets so `edit/router.py` produces a valid `shot_spec/1` with `audio_slice_sha256` before pod launch.
     2. In `explainer_engine/production/silent.py:249, 276`, replace `doc.get("schema") != "production_script/3"` with `not is_scene_script(doc)` so `PV-55` (`D-62`) and `PV-56` (`D-63`) bind `/4` scripts, while holding deceased historical figure voicing (`traits.living: false`) behind `CD-06` (`D-90`).
5. **Why Needed**:
   * Fixes the `audio/spine.py` -> `edit/router.py` deadlock on `DIALOGUE_CU` (`CG-10`) and enforces `PV-55` (`D-62`) on `/4` scripts using the real repository modules.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`** + **`[PRIMARY-STANDARD]`**:
     * `SOURCE 1`: `explainer_engine/audio/spine.py:84–210`, `edit/router.py:7, 79–90`, & `production/silent.py:246–290`.
     * `SOURCE 2`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-62`, `D-63`, `D-90`) & `docs/MARKET_RESEARCH.md:106` (`V-51`).
     * `SOURCE 3`: [ElevenLabs Prohibited Use Policy (Updated 09 Oct 2026, §3 & §4)](https://elevenlabs.io/use-policy).
7. **Rule Classification**:
   * **Hard Legal/Governance Invariant (`FAIL`)** for `PV-55` (`D-62`) and `PV-56` (`D-63`); **Hard Contract Gate (`ContractError`)** for `D-90` `audio_slice_sha256` in `edit/router.py`; **Creator Decision (`CD-06`)** for deceased historical figures.
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/spine.py`, `edit/router.py`, `production/silent.py`.
9. **Backward Compatibility & Migration Impact**:
   * Preserves `retime_post_hoc` in `audio/spine.py` when a rendered LTX clip duration differs slightly from the input take (`D-88`, `D-90`).
10. **Cost / Latency / Quality Tradeoff**:
    * Character takes use `~1,500–3,000` ElevenLabs credits per episode (`D-90`).
11. **Failure Modes & Rollback Plan**:
    * If `CD-06` is answered `NO` for deceased historical figures, historical quotes use `voiced: false` accent bubbles (`D-63`, `PV-56`) + narrator reporting.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_audio_spine.py tests/unit/test_shot_router.py tests/unit/test_silent_lines.py tests/unit/test_voice_route_docs.py` passes with `0` failures.

### `CHG-13` — Align the 10 Real Writers' Room Agents (`.claude/agents/*.md`), 10 Skills (`.claude/skills/*/SKILL.md`), 6 Docs & `production/shorts.py` (`BP-167`) (`BATCH-M3` & `BATCH-M6`)

1. **Change ID**: `CHG-13` (implements `CG-08`, `BATCH-M3` `§9.4`, and `BATCH-M6` `§9.7`)
2. **Subsystem / Target File(s)**:
   * **10 Real Repository Agent Files in `.claude/agents/`** (matching `§5.1` and `§9.4` `L1178`):
     `orchestrator.md`, `story-architect.md`, `scene-writer.md`, `beat-writer.md`, `performance-director.md`, `edit-planner.md`, `voice-caster.md`, `shorts-writer.md`, `script-critic.md`, `shot-continuity-writer.md`
   * **10 Real Repository Skill Files in `.claude/skills/*/SKILL.md`** (matching `§5.2` and `§9.4` `L1180`):
     `story-engine/SKILL.md`, `narration-script/SKILL.md`, `elevenlabs-voice/SKILL.md`, `dialogue-scenes/SKILL.md`, `visual-beats/SKILL.md`, `shot-visuals/SKILL.md`, `animation-principles/SKILL.md`, `editing-style/SKILL.md`, `video-editing-architect/SKILL.md`, `shorts-for-video/SKILL.md`
   * **6 Real Repository Docs in `docs/`** (matching `§9.4` `L1182`):
     `docs/STORY_ENGINE.md`, `docs/SCRIPT_ENGINE.md`, `docs/PRODUCTION_SCRIPT.md`, `docs/NARRATION_AND_LANGUAGE_GUIDE.md`, `docs/EDITING.md`, `docs/AUDIO_SYSTEM.md`
   * **Existing Shorts Modules (`BP-167`, `D-85`, `D-92`)**:
     `explainer_engine/production/shorts.py`, `explainer_engine/production/clip_shorts.py`, `explainer_engine/qa/short_format.py`, `explainer_engine/production/validate.py` (`PV-34`)
3. **Current Repository Behavior & Prior Misconception (`5013a55a`)**:
   * **[FACT]** In `7312f660`, `CHG-13` listed generic agent/skill names (`script-writer.md`, `visual-director.md`, `retention-critic.md`, `write-script/SKILL.md`, `finish/shorts_extract.py`) instead of the actual files in `.claude/agents/`, `.claude/skills/`, and `production/shorts.py` (`§5.1`, `§5.2`, `§9.4` `L1178–1182`). In `repo_5013a55a`, those 10 agents and 10 skills still instruct `15-minute` runtime (`story-architect.md`), `"production_script/3"`, flat `170 WPM` (`scene-writer.md`), `Oxley` (`elevenlabs-voice/SKILL.md`), and `10` Shorts (`shorts-writer.md`).
4. **Target Behavior (`VERIFIED CORRECTION`)**:
   * Update the exact 10 `.claude/agents/*.md`, 10 `.claude/skills/*/SKILL.md`, and 6 `docs/*.md` files listed in Field 2 (matching `§5.1`, `§5.2`, and `§9.4` `BATCH-M3`) to target `12-minute (720s, BP-167)`, `production_script/4`, `Odom` + `narrator_polish.py` (`D-94`), 5-zone `BP-169` pacing, `AB01..AB12` anchors, 3-Tier Still Motion Ladder (`BP-170`), `edit/bounded_timeline.py`, and `5` vertical `1440x2560` Shorts (`production/shorts.py`, `production/clip_shorts.py`, `validate.py` `PV-34`).
5. **Why Needed**:
   * Eliminates all non-existent agent/skill/shorts filenames from `CHG-13` and ensures `explainer_engine.docs_lint` and `test_agent_roles.py` pass with `0` findings.
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `.claude/agents/*.md` (`16` files) & `.claude/skills/*/SKILL.md` (`16` files) in `repo_5013a55a.zip`.
     * `SOURCE 2`: `explainer_engine/production/shorts.py`, `production/clip_shorts.py`, `core/delivery.py` (`BP-167`, `1440x2560` @ `24 fps`).
     * `SOURCE 3`: `explainer_engine/docs_lint.py` & `tests/unit/test_agent_roles.py`, `tests/unit/test_agent_governance.py`, `tests/unit/test_voice_route_docs.py`.
7. **Rule Classification**:
   * **Hard Governance & Deliverable Contract (`FAIL`)** for `docs_lint.py`, `D-79` read-only critic boundaries, and `BP-167` (`5` Shorts at `1440x2560`).
8. **Exact Schema / Code / Config Surface Affected**:
   * The 10 `.claude/agents/*.md`, 10 `.claude/skills/*/SKILL.md`, and 6 `docs/*.md` files in Field 2 + `production/validate.py` (`PV-34`).
9. **Backward Compatibility & Migration Impact**:
   * Preserves all `OR-32` `stage_guard` banners and `<!-- sd-matrix:begin -->` markers enforced by `test_t3_agent_skill_banners.py` and `docs_lint.py`.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; prevents LLM script-generation retry loops.
11. **Failure Modes & Rollback Plan**:
    * Verified after every edit via `PYTHONPATH=. python3 -m explainer_engine.docs_lint`.
12. **Verification Test & Acceptance Criteria**:
    * `PYTHONPATH=. python3 -m explainer_engine.docs_lint` (`0 finding(s)`) + `pytest tests/unit/test_agent_roles.py tests/unit/test_agent_governance.py tests/unit/test_voice_route_docs.py tests/unit/test_shorts_2k.py` passes with `0` failures.

### `CHG-14` — Reconcile `D-67` Whole-Segment Sample Scope (`production/sample.py`), `D-92` `BP-168` Thresholds & `BATCH-M8B` Paid Gate Caps (`GATE-P1a..P4`) (`BATCH-M8A` & `BATCH-M8B`)

1. **Change ID**: `CHG-14` (implements `BATCH-M8A` `§9.9`, `BATCH-M8B` `§9.10`, `CORR-03`, and `CORR-04`)
2. **Subsystem / Target File(s)**:
   * `explainer_engine/production/sample.py` (`L31–125`, `OR-19`, `D-67`)
   * `explainer_engine/core/ledger.py` (`L30–145`, `L330–348`, `STOP_FRACTION = 0.8`, `BP-168`)
   * `explainer_engine/core/spend_caps.py` & `config/spend_caps.json` *(protected config under `D-84` — touched only if creator approves `CD-05`)*
   * `explainer_engine/standards/sourced_rules.json` (`BP-168` updated per `D-92` item 7)
   * `tests/unit/test_sample_gate.py`, `tests/unit/test_d92_creator_answers.py`, `tests/unit/test_ledger.py`, `tests/unit/test_spend_caps.py`
3. **Current Repository Behavior & Prior Misconception (`5013a55a`, `CORR-03`, `CORR-04`)**:
   * **[FACT]** In `7312f660`, `CHG-14` contradicted `§9.10` (`BATCH-M8B`, `L1486–1530`) in three ways that ChatGPT's audit caught:
     1. **Sample Scope (`D-67`, `CORR-03`)**: `CHG-14` claimed `production/sample.py` slices a `90–120s` 30-second sub-window out of `S04` (`90–135s`). In reality, `explainer_engine/production/sample.py:44–50` (`scope_segments`) operates strictly on **whole segments** (`ids[:2]` = `["S01", "S02"]` `0–60s` by default, or whole segments listed in `sample_approval.json.scope_segments`, e.g., `["S01", "S15"]` = `30s + 30s = 60.0s` or `["S01", "S04"]` = `30s + 45s = 75.0s`).
     2. **`D-92` vs `BP-168` (`CORR-04`)**: `CHG-14` cited `abandon_forecast_usd_min: 20.00` (which does not exist in `sourced_rules.json` or `D-92`) and missed that `D-92` item 7 (`2026-11-01`) updated pilot gates to **GO = `<= 3` seeds/accepted shot and `<= 3` review min/finished min; PIVOT = `(3, 6]`; ABANDON = `> 6`**, while `go_forecast_usd_max: 12.0` in `BP-168` (`core/ledger.py:343`) is a `REVIEW` recommendation (`per_episode.runpod_usd = $31.00`, `80%` `ledger.py` stop = `$24.80`, unless a lower cap is passed to `Run.open(caps=...)`).
     3. **Exact `config/spend_caps.json` Keys (`§9.10`)**: `config/spend_caps.json` already defines `paid_tests.total_usd = 5.90` with existing keys `p12a_smoke: 0.50`, `p12b_measure: 0.63`, `p12b_two_runs: 3.00`, and `p12e_hosts: 1.77` (unspent per `D-89`: `"The p12e_hosts line in config/spend_caps.json stays unspent: no pod is planned for it"`).
4. **Target Behavior (`VERIFIED CORRECTION` — 100% Aligned with `§9.10` `BATCH-M8B`)**:
   * Enforce the exact 5-stage paid gate architecture from `§9.10` (`L1486–1530`) without inventing non-existent config keys or sub-segment slicing:

| Operational Stage (`§9.10` `BATCH-M8B`) | Exact `config/spend_caps.json` / `Run.open` Ledger Binding | Exact Scope & Whole-Segment `sample.py` Contract (`D-67` / `OR-19`) | Ledger Reservation / Cap | `core/ledger.py` `80%` Stop & `BP-168` (`D-92`) Gate |
| ----- | ----- | ----- | ----- | ----- |
| **`GATE-P1a`** (Stage M Measurement Pod) | `paid_tests.p12b_measure.runpod_usd` (already in `config/spend_caps.json`) | Measure exact RunPod SECURE download/setup speed (`p12b.json` `$0.50` pod cap) after `BATCH-M8A` `cloud.dryrun` PASS | **`$0.63`** ledger reservation (`$0.50` pod cap) | `OR-23` pod plan + standalone creator `"YES"` + `OR-36` Haiku watchdog. |
| **`GATE-P1b`** (`P12b` Combined Qwen + LTX-2.5 Benchmark Pod) | `paid_tests.p12b_two_runs.runpod_usd` (already in `config/spend_caps.json`) | Render `Q1–Q3` Qwen keyframes/nextposes + `L1–L3` LTX-2.5 clips on 1 pod (`$2.40` pod cap); calibrate `BP-133` CLIP hero-sheet identity threshold (`qa/identity.py`) and evaluate **`BP-168` (`D-92` item 7: GO `<=3` seeds/shot & `<=3` review min/min, forecast `<= $12.00`; PIVOT `(3, 6]`; ABANDON `>6`)** | **`$3.00`** ledger reservation (`$2.40` pod cap; cumulative `paid_tests` used = `$0.50 + $0.63 + $3.00 = $4.13 <= $4.72` 80% of `$5.90`, leaving `p12e_hosts = $1.77` unspent per `D-89`!) | Updates `config/job_speeds.json` & `docs/COST_AND_TIME_MODEL.md`; halts for creator review of `BP-168` (`REVIEW`) report. |
| **`GATE-P2`** (Episode 1 Voice Auditions + 2-Part Sample Generation `OR-19`, `D-67`) | Episode 1 `run.json` (`Run.open` sample-only caps under `per_episode`) + `casting.casting_credits_max = 1,500` | (a) Stage 5 character voice auditions (`<=1,500` credits) + Odom baseline; (b) Paid voice + pictures/clips **strictly for the 2 whole sample segments** (`production/sample.py:scope_segments`: defaults to `["S01", "S02"]` `0–60s`, or `{"scope_segments": ["S01", "S15"]}` `30s + 30s = 60s` / `["S01", "S04"]` `30s + 45s = 75s` written to `sample_approval.json` before generation so `PP-09` and `standards/hook.py` enforce exact whole-segment scope) | Sample `Run.open` caps: **`runpod_usd <= $4.50`**, **`elevenlabs_credits <= 3,500`** | Enforced in code by `paint.preflight` (`PP-09`), `standards/hook.py` (`hook_speech`), and `core/ledger.py` (`80%` stop = `$3.60` / `2,800` credits, `MAX_FAILURES = 3`). |
| **`GATE-P3`** (Post-Render 2-Part Sample Approval `OR-19`) | **`$0.00` Review Gate** (`production/sample.py approve`) | All paid tools halt at Gate `6.5` (`production_gate.py:130`). Creator watches the stitched 2-part sample video and runs `python -m explainer_engine.production.sample approve <folder> --by <creator> --ref <msg> --video <sample.mp4>` (bound to `script_sha256`) | **`$0.00`** | Unlocks remaining segments (`S03..S16` + `5` Shorts) only after recorded `sample_approval.json`. |
| **`GATE-P4`** (Episode 1 Remaining Full Production `S03..S16` + `5` Shorts) | Episode 1 `run.json` (`Run.open(caps={"runpod_usd": 15.0, "elevenlabs_credits": <CD-05_cap>})` inside `per_episode.runpod_usd = $31.00` & `runpod.per_24h_usd = $26.00`) | Render remaining `14` segments + `5` vertical `1440x2560` Shorts (`production/shorts.py`, `BP-167`), verify `BP-50` (`-14.0 LUFS`, `<= -1.0 dBTP`), and archive media to HF Vault `vano1919/tmr-artifacts` (`D-73`) | Forecast **`~$7.80–$12.00`** (`BP-168` `go_forecast_usd_max: 12.0`; enforced as a hard stop by passing `caps={"runpod_usd": 15.0}` to `Run.open` so `80%` stop = **`$12.00`**!) | Full `production_gate.py`, `editorial_gate.py`, `qa/scorecard.py` (`BP-50..52`), and `qa/short_format.py` pass. |

5. **Why Needed**:
   * Reconciles `CHG-14` 100% with `§9.10` (`BATCH-M8B`), `production/sample.py` (whole-segment `D-67` scope), `D-89` (`p12e_hosts = $1.77` stays unspent while `p12a_smoke + p12b_measure + p12b_two_runs = $4.13 <= $4.72` 80% of `$5.90`!), and `D-92` item 7 (`BP-168` `<=3` seeds/shot & `<=3` review min/min). Also shows how passing `caps={"runpod_usd": 15.0}` to `Run.open()` makes `core/ledger.py`'s `80%` stop (`0.80 * 15.0 = $12.00`) enforce `BP-168`'s `$12.00` forecast ceiling in code without touching protected `config/spend_caps.json`!
6. **Evidence Grade & 2–3 Independent Sources**:
   * **`[FACT]`**:
     * `SOURCE 1`: `explainer_engine/production/sample.py:31–125` & `config/spend_caps.json`.
     * `SOURCE 2`: `explainer_engine/core/ledger.py:30–145, 330–348` & `explainer_engine/standards/sourced_rules.json` (`BP-168`).
     * `SOURCE 3`: `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-56`, `D-67`, `D-84`, `D-89`, `D-92` item 7).
7. **Rule Classification**:
   * **Hard Financial & Governance Gate (`FAIL` in `core/ledger.py`, `sample.py` `PP-09`, and `standards/hook.py`; `REVIEW` recommendation in `BP-168` `ledger.py:330`; `CREATOR DECISION` at `GATE-P1a..P4` and `CD-01`, `CD-05`)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/standards/sourced_rules.json` (`BP-168`), `docs/SOURCED_RULES.md`, `explainer_engine/core/ledger.py` (`BP-168` keys aligned with `D-92`). Zero changes required to protected `config/spend_caps.json` unless creator elects to adjust episode caps under `CD-05`!
9. **Backward Compatibility & Migration Impact**:
   * Preserves `test_spend_caps.py`, `test_spend_caps_single_source.py`, `test_sample_gate.py`, and `test_d92_creator_answers.py`.
10. **Cost / Latency / Quality Tradeoff**:
    * Uses existing `p12b_measure` (`$0.63`) + `p12b_two_runs` (`$3.00`) allocations (`$4.13` cumulative with `$0.50` `p12a_smoke`, strictly below `$4.72` 80% of `$5.90`) while leaving `p12e_hosts` (`$1.77`) untouched per `D-89`.
11. **Failure Modes & Rollback Plan**:
    * `core/ledger.py` halts automatically at `80%` of the `Run.open` cap or on `3` consecutive failures (`MAX_FAILURES = 3`).
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_sample_gate.py tests/unit/test_d92_creator_answers.py tests/unit/test_ledger.py tests/unit/test_spend_caps.py` passes with `0` failures.

## 17. Mandatory Per-Batch Documentation Synchronisation Matrix, 4-Stage Rollout, Traceability & Claude Audit Checklist

### 17.1 Per-Batch Documentation Synchronisation Matrix (`explainer_engine.docs_lint` Verified Against Real `docs/` Files)

**[FACT]** Every documentation file listed below is verified to exist in `/tmp/repo_5013a55a/docs/` (plus `docs/MASTER_MOLD_V2_1.md` created in `BATCH-M1`, matching `§9.2` and `§9.4`):
* `docs/INDEX.md`
* `docs/STORY_ENGINE.md`
* `docs/SCRIPT_ENGINE.md`
* `docs/PRODUCTION_SCRIPT.md`
* `docs/NARRATION_AND_LANGUAGE_GUIDE.md`
* `docs/EDITING.md`
* `docs/AUDIO_SYSTEM.md`
* `docs/SOURCED_RULES.md`
* `docs/DECISIONS_AND_OPEN_QUESTIONS.md`
* `docs/COST_AND_TIME_MODEL.md`
* `docs/PROGRESS.md`
* `docs/blueprint/STATUS.md`
* `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`

| Implementation Batch (`§9.1..§9.10`) | Code, Schema & Config Scope (`CHG-01..CHG-14`) | Mandatory Existing `docs/` Files Updated in Same Commit | Verification Gate (`0 finding(s)` Required) |
| ----- | ----- | ----- | ----- |
| **`BATCH-M0` (`§9.1`)** | `CHG-02`: `scripting/schema_version.py`, `/4` dispatch across 11 `== "production_script/3"` modules, `narrator_polish.polish_narrator_spans_in_place` at `production/__main__.py:119`, `rhythm_zone` propagation in `film_shots.py:compose()`, `claude_api.py:1066` fix | `docs/PRODUCTION_SCRIPT.md`, `docs/AUDIO_SYSTEM.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_production_script_schema.py tests/unit/test_narrator_polish.py tests/unit/test_shot_prompt_lint.py` |
| **`BATCH-M1` (`§9.2`)** | `CHG-01` & `CHG-05` (part 1): Commit `config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `schemas/episode_mold.schema.json`, `scripting/mold_contract.py`; update `BP-168` (`D-92` item 7) & `BP-169` (`rehook_tts_tags`); add `qa/engagement.py:resolution_word_share` | `docs/MASTER_MOLD_V2_1.md` *(created)*, `docs/INDEX.md`, `docs/SOURCED_RULES.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_master_mold_contract.py tests/unit/test_sourced_rules.py tests/unit/test_sourced_rules_sync.py tests/unit/test_d92_creator_answers.py` |
| **`BATCH-M2` (`§9.3`)** | `CHG-03` (part 1), `CHG-04` & `CHG-05` (part 2): Upstream `research/fan_brief.py`, `research/hypotheses.py`, `scripting/variant_plan.py`, `scripting/story_lint.py` (`ST-25`), `scripting/narration_lint.py`, `scripting/rhythm_lint.py`, `scripting/stage_guard.py` | `docs/STORY_ENGINE.md`, `docs/SCRIPT_ENGINE.md`, `docs/SOURCED_RULES.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_variant_plan.py tests/unit/test_story_engine.py tests/unit/test_engagement.py tests/unit/test_rhythm_lint.py` |
| **`BATCH-M3` (`§9.4`)** | `CHG-13`: Update the 10 `.claude/agents/*.md` pages, 10 `.claude/skills/*/SKILL.md` files, and 6 `docs/*.md` guides (`12-min` `BP-167`, `/4`, `Odom`, `BP-169`, `AB01..AB12`, `5` Shorts) | `docs/STORY_ENGINE.md`, `docs/SCRIPT_ENGINE.md`, `docs/PRODUCTION_SCRIPT.md`, `docs/NARRATION_AND_LANGUAGE_GUIDE.md`, `docs/EDITING.md`, `docs/AUDIO_SYSTEM.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_agent_roles.py tests/unit/test_agent_governance.py tests/unit/test_voice_route_docs.py` |
| **`BATCH-M4` (`§9.5`)** | `CHG-06` & `CHG-12`: Zone TTS compilation (`production/compile.py`, `audio/hype_read.py`), zone gap padding (`audio/pause_pad.py` `0.18s` vs `0.26s`), Odom span polish (`audio/narrator_polish.py`), `D-90` character take binding (`audio/spine.py:bind_character_takes`) | `docs/AUDIO_SYSTEM.md`, `docs/NARRATION_AND_LANGUAGE_GUIDE.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_hype_read.py tests/unit/test_pause_pad.py tests/unit/test_narrator_polish.py tests/unit/test_audio_spine.py` |
| **`BATCH-M5` (`§9.6`)** | `CHG-07`, `CHG-08` & `CHG-09` (part 1): Implement `edit/bounded_timeline.py` (`17,280`-frame projection, `BP-83` `CV >= 0.20`, `BP-139` `8k+1`, `TimelineInfeasibleError`), 3-Tier Still Motion Ladder (`edit/dramatic_still.py`, `edit/router.py`), `scripting/film_shots.py` | `docs/EDITING.md`, `docs/SHOT_CONTINUITY.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_bounded_timeline.py tests/unit/test_dramatic_still.py tests/unit/test_shot_router.py tests/unit/test_film_shots.py` |
| **`BATCH-M6` (`§9.7`)** | `CHG-03` (part 2), `CHG-09` (part 2), `CHG-10` & `CHG-11`: Zone wiring across `production/timing.py`, `beats.py`, `fill_holds.py`, `validate.py`, `edit/board.py`, `motion_lint.py`, `shot_rules.py`, `audio/layers.py`, `sound_director.py`, `qa/engagement.py`, `qa/scorecard.py`, `production/shorts.py`, and 3-lane `assemble.materialize_lane_clips` | `docs/EDITING.md`, `docs/AUDIO_SYSTEM.md`, `docs/RENDERING_ARCHITECTURE.md`, `docs/QA_SPECIFICATION.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_rhythm_end_to_end.py tests/unit/test_assemble_video_v2.py tests/unit/test_sound_director.py tests/unit/test_scorecard.py` |
| **`BATCH-M7` (`§9.8`)** | Full-pipeline CPU validation suite (`tests/unit/test_mold_v2_1_full_pipeline.py` & `test_rhythm_end_to_end.py`) | `docs/QA_SPECIFICATION.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest -q -m "not system and not media"` |
| **`BATCH-M8A` & `BATCH-M8B` (`§9.9–§9.10`)** | `CHG-14`: Free governance closure (`governance status --write`, `cloud.dryrun`, `$0.00`) followed by creator-gated `GATE-P1a`, `GATE-P1b`, `GATE-P2` (`sample.py`), `GATE-P3` (`sample.py approve`), and `GATE-P4` | `docs/blueprint/STATUS.md`, `docs/COST_AND_TIME_MODEL.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `python -m explainer_engine.governance status --check` + `python -m explainer_engine.cloud.dryrun` |

### 17.2 Mandatory Four-Stage Final Rollout Sequence (`Stage 1` → `Stage 2` → `Stage 3` → `Stage 4`)

1. **`Stage 1 — Unify Contract & Free Code/Agent Wiring ($0.00 Spend, BATCH-M0..M6)`**:
   * Execute `BATCH-M0` through `BATCH-M6` in offline unit-tested commits after `CD-01` approval and `GATE-EXT-MAIN-PROTECT` verification.
2. **`Stage 2 — Free End-to-End Representative Story Validation & Governance Dry-Run ($0.00 Spend, BATCH-M7 & BATCH-M8A)`**:
   * Run `tests/unit/test_mold_v2_1_full_pipeline.py` (`60.0s` 2-zone `S01` + `S15` CPU assembly proof), `python -m explainer_engine.governance status --check`, `python -m explainer_engine.cloud.dryrun`, and `python -m explainer_engine.docs_lint` (`0 finding(s)`).
3. **`Stage 3 — Paid Micro-Benchmarks & Two-Part Whole-Segment Sample Gate (BATCH-M8B: GATE-P1a -> GATE-P1b -> GATE-P2 -> GATE-P3)`**:
   * Execute `GATE-P1a` (`p12b_measure = $0.63` reservation / `$0.50` pod cap) and `GATE-P1b` (`p12b_two_runs = $3.00` reservation / `$2.40` pod cap; cumulative `paid_tests` = `$4.13 <= $4.72` 80% of `$5.90`), calibrate `BP-133` CLIP identity on hero sheets (`qa/identity.py`), and evaluate `BP-168` (`D-92` item 7: `<=3` seeds/shot, `<=3` review min/min, forecast `<= $12.00`).
   * Execute `GATE-P2` (Episode 1 auditions `<=1,500` credits + 2 whole sample segments via `production/sample.py` `D-67`: `["S01", "S02"]` default or `["S01", "S15"]` / `["S01", "S04"]` in `sample_approval.json`) and halt at `GATE-P3` (`sample.py approve`, `$0.00`) for creator sign-off.
4. **`Stage 4 — Full Episode 1 Production & 5-Shorts Delivery (BATCH-M8B: GATE-P4)`**:
   * Upon recorded `sample_approval.json` (`GATE-P3`) and standalone creator `"YES"` (`GATE-P4`), open `run.json` with `caps={"runpod_usd": 15.0, "elevenlabs_credits": <CD-05_cap>}` (`80%` `ledger.py` stop = `$12.00`), render `S03..S16` + `5` vertical `1440x2560` Shorts (`production/shorts.py`, `BP-167`), verify `BP-50` (`-14.0 LUFS`, `<= -1.0 dBTP`), and pass `production_gate.py`.

### 17.3 Rule-to-Code-to-Test Traceability Matrix (`M-01..M-12`, `CORR-01..CORR-12` & `CHG-01..CHG-14`)

| Rule / Change ID | Authority Tier & Repo Severity | Canonical `sourced_rules.json` / Decision ID | Verified Repository Implementation Module(s) (`5013a55a`) | Verified Repository Unit Test File(s) (`tests/unit/`) |
| ----- | ----- | ----- | ----- | ----- |
| **`M-01` / `CHG-01`** | Structural Invariant (`FAIL`) | `BP-169`, `production_script/4` | `explainer_engine/scripting/mold_contract.py` *(NEW)*, `explainer_engine/edit/rhythm_profile.py` | `tests/unit/test_master_mold_contract.py` *(NEW)*, `tests/unit/test_rhythm_profile.py` |
| **`M-02` / `CHG-06`** | Invariant (`FAIL` `D-59`; `REVIEW` `BP-169`/`171`) | `D-59`, `BP-169`, `BP-171` | `explainer_engine/audio/hype_read.py`, `explainer_engine/audio/pause_pad.py`, `explainer_engine/audio/narrator_polish.py` | `tests/unit/test_sourced_rules.py`, `tests/unit/test_hype_read.py`, `tests/unit/test_pause_pad.py`, `tests/unit/test_narrator_polish.py` |
| **`M-03` / `CHG-04`** | House/Hypothesis (`REVIEW`) | `BP-109`, `BP-141`, `D-93`, `D-94` | `explainer_engine/scripting/variant_plan.py`, `explainer_engine/scripting/film_shots.py` | `tests/unit/test_variant_plan.py`, `tests/unit/test_film_shots.py` |
| **`M-04` / `CHG-09`** | Hard House Gate (`FAIL`; `CD-03` Tier 2) | `BP-35`, `BP-132`, `BP-170` | `explainer_engine/edit/dramatic_still.py`, `explainer_engine/production/parallax.py`, `explainer_engine/edit/router.py`, `explainer_engine/production/assemble.py` | `tests/unit/test_dramatic_still.py`, `tests/unit/test_parallax.py`, `tests/unit/test_shot_router.py` |
| **`M-05` / `CHG-05`** | `REVIEW` (`BP-04` `D-94`) / `FAIL` (`BP-142`, `BP-43`) | `BP-04`, `BP-42`, `BP-43`, `BP-75`, `BP-142` | `explainer_engine/qa/engagement.py`, `explainer_engine/scripting/story_lint.py` | `tests/unit/test_engagement.py`, `tests/unit/test_story_engine.py` |
| **`M-06` / `CHG-01`** | Fact Grounding Invariant (`FAIL`) | `ZI-02`, `PV-37`, `HY-4` | `explainer_engine/scripting/film_shots.py`, `explainer_engine/scripting/claims.py`, `explainer_engine/research/hypotheses.py` | `tests/unit/test_claims.py`, `tests/unit/test_film_shots.py` |
| **`M-07` / `CHG-01`** | Ending Invariant (`FAIL`) | `BP-43` (`ENG-8`, `KP-40`), `BP-106` | `explainer_engine/qa/engagement.py`, `explainer_engine/scripting/film_shots.py` | `tests/unit/test_engagement.py`, `tests/unit/test_film_shots.py` |
| **`M-08` / `CHG-09`** | Map vs Still Scope (`REVIEW`/`FAIL`) | `BP-35`, `BP-125`, `BP-132`, `BP-170` | `explainer_engine/maps/camera.py`, `explainer_engine/edit/dramatic_still.py` | `tests/unit/test_maps.py`, `tests/unit/test_dramatic_still.py` |
| **`M-09` / `CHG-03`** | Profile Scoping (`FAIL` `BP-84` bubbles; `REVIEW` `BP-169`) | `BP-40`, `BP-83`, `BP-84`, `BP-169`, `BP-170` | `explainer_engine/edit/board.py`, `explainer_engine/edit/motion_lint.py`, `explainer_engine/edit/shot_rules.py` | `tests/unit/test_board_bubbles_duck.py`, `tests/unit/test_rhythm_end_to_end.py` |
| **`M-10` / `CHG-08`** | Hypothesis (`REVIEW` `BP-128`, `BP-139`) | `BP-128`, `BP-129`, `BP-139` | `explainer_engine/production/assemble.py`, `explainer_engine/core/contracts.py`, `explainer_engine/training/video_qa.py` | `tests/unit/test_assemble_video_v2.py`, `tests/unit/test_contracts.py`, `tests/unit/test_video_qa_clip_rows.py` |
| **`M-11` / `CHG-10`** | `FAIL` (`BP-50`, `BP-52`) / `REVIEW` (`BP-51`, `BP-53`, `BP-117..122`) | `BP-50..53`, `BP-117..122`, `D-59` | `explainer_engine/qa/targets.py`, `explainer_engine/qa/scorecard.py`, `explainer_engine/audio/sound_director.py`, `explainer_engine/audio/layers.py`, `explainer_engine/production/assemble.py` | `tests/unit/test_sourced_audio.py`, `tests/unit/test_sound_director.py`, `tests/unit/test_scorecard.py` |
| **`M-12` / `CHG-11`** | `FAIL` (`LT-65`, `AC-17`, `D-22`) / `REVIEW` (`BP-130`, `BP-133`, `BP-166`) | `BP-130`, `BP-133`, `BP-166`, `LT-65`, `AC-17`, `D-22` | `explainer_engine/compose/episode_look.py`, `explainer_engine/qa/style_prompt.py`, `explainer_engine/finish/grade.py`, `explainer_engine/training/video_qa.py`, `explainer_engine/qa/identity.py` | `tests/unit/test_episode_look.py`, `tests/unit/test_style_prompt.py`, `tests/unit/test_identity_qa.py`, `tests/unit/test_palette.py` |
| **`CHG-02`** | `/4` Dispatch Completeness (`FAIL`) | `production_script/3`, `production_script/4` | `explainer_engine/scripting/schema_version.py` *(NEW)* + 11 `== "production_script/3"` modules + `production/__main__.py` + `scripting/film_shots.py` | `tests/unit/test_production_script_schema.py`, `tests/unit/test_narrator_polish.py`, `tests/unit/test_shot_prompt_lint.py` |
| **`CHG-07`** | `17,280`-Frame Conservation & Infeasibility (`FAIL`) | `BP-83`, `BP-167`, `BP-169`, `BP-170`, `UR-12` | `explainer_engine/edit/bounded_timeline.py` *(NEW)*, `explainer_engine/production/timing.py` | `tests/unit/test_bounded_timeline.py` *(NEW)* |
| **`CHG-12`** | Character Voice & Legal Gate (`FAIL` `PV-55`; `CD-06`) | `D-62`, `D-63`, `D-90`, `PV-55`, `PV-56`, `V-51` | `explainer_engine/audio/spine.py`, `explainer_engine/edit/router.py`, `explainer_engine/production/silent.py` | `tests/unit/test_audio_spine.py`, `tests/unit/test_silent_lines.py`, `tests/unit/test_voice_route_docs.py` |
| **`CHG-13`** | Agent/Skill Sync & `5` Shorts (`FAIL`) | `BP-167`, `D-79`, `D-85`, `D-92` | 10 `.claude/agents/*.md`, 10 `.claude/skills/*/SKILL.md`, 6 `docs/*.md`, `explainer_engine/production/shorts.py`, `production/clip_shorts.py` | `explainer_engine/docs_lint.py`, `tests/unit/test_agent_roles.py`, `tests/unit/test_shorts_2k.py` |
| **`CHG-14`** | Spend Cap, Whole-Segment Sample & `D-92` `BP-168` (`FAIL`/`REVIEW`) | `D-56`, `D-67` (`OR-19`), `D-84`, `D-89`, `D-92`, `BP-168` | `explainer_engine/production/sample.py`, `explainer_engine/core/ledger.py`, `explainer_engine/core/spend_caps.py`, `config/spend_caps.json` | `tests/unit/test_sample_gate.py`, `tests/unit/test_d92_creator_answers.py`, `tests/unit/test_ledger.py`, `tests/unit/test_spend_caps.py` |

### 17.4 Independent Claude / Auditor Verification Checklist (`12` Zero-Trust Verification Commands)

1. **Documentation & Path Integrity Gate**:
   * Run `PYTHONPATH=. python3 -m explainer_engine.docs_lint` -> must output `0 finding(s)`.
2. **Single-Home Threshold Invariant (`D-59`)**:
   * Run `pytest tests/unit/test_sourced_rules.py tests/unit/test_sourced_rules_sync.py` -> verifies all `158` `BP-*` rules in `explainer_engine/standards/sourced_rules.json` and `docs/SOURCED_RULES.md`.
3. **Zero Search-Wrapper URL Check**:
   * Run `python3 -c 'import re; t=open("docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md").read(); assert not re.search(r"https?://[^\s\)]*google\.com/search", t)'` -> must pass with `0` matches.
4. **Zero Non-Existent Repo Module Claim Check**:
   * Verify that all existing repository modules referenced in `§16` and `§17` (`production/script.py`, `scripting/scene_lint.py`, `scripting/shot_prompt_lint.py`, `audio/hype_read.py`, `audio/pause_pad.py`, `audio/narrator_polish.py`, `audio/spine.py`, `edit/router.py`, `edit/board.py`, `edit/motion_lint.py`, `edit/dramatic_still.py`, `compose/episode_look.py`, `qa/style_prompt.py`, `finish/grade.py`, `training/video_qa.py`, `qa/identity.py`, `qa/targets.py`, `qa/scorecard.py`, `qa/engagement.py`, `production/silent.py`, `production/sample.py`, `production/shorts.py`, `core/ledger.py`) exist in `repo_5013a55a.zip`, and only the 5 explicitly marked `*(NEW)*` files (`config/master_mold_v2_1.json`, `docs/MASTER_MOLD_V2_1.md`, `explainer_engine/schemas/episode_mold.schema.json`, `explainer_engine/scripting/mold_contract.py`, `explainer_engine/scripting/schema_version.py`, `explainer_engine/edit/bounded_timeline.py`) are created in `BATCH-M0..M5`.
5. **Master Mold Provenance & Compact Digest Check**:
   * Verify `sha256sum mrbeast_12min_master_mold.md` == `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e` (`431` lines) and `sha256sum "mrbeast_12min_video_mold (1).json"` == `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0` (`26,291` lines), and inspect `mold_254_shots_verified_digest.json` (`<45 KB`) for the complete 16-segment and 254-shot metrics.
6. **5-Zone Shot Count & `BP-169` Alignment Check (`CORR-12`)**:
   * Verify across `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) that `Z1..Z5` contain `14, 24, 111, 75, 30` shots (`254` total), equaling `28.0, 24.0, 17.08, 25.0, 30.0` shots/min, matching `BP-169`'s `shots_per_min_target` (`28.0, 24.0, 17.0, 25.0, 30.0`).
7. **152 `VIDEO` Shots LTX-2.5 Handle Math Check**:
   * Verify across the `152` `VIDEO` shots (`10,368` usable timeline frames) that `sum(8*ceil((u+24-1)/8)+1) == 14,552`, `sum(8*ceil((u+8-1)/8)+1) == 12,120` (difference `2,432` frames = `16.71%`), and transition-aware (`17` whip-pan/crossfade at `>=12`/side + `135` hard/J/L at `>=4`/side) == `12,392` (difference `2,160` frames = `14.84%`).
8. **76 `STILL` Shots `BP-170` Static Cap Check**:
   * Verify across the `76` `STILL` shots (`19` `TIER_1`, `40` `TIER_2`, `17` `TIER_3`) that `2` `TIER_1` (`SH003`, `SH226`), `36` `TIER_2`, and `17` `TIER_3` (`55` total) exceed `BP-170`'s `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`).
9. **Cumulative Spoken Word Share Check (`BP-04` `ENG-5`, `CORR-06`)**:
   * Verify across `S01..S16` (`2,066` words) that `S13` ends at `1,724` words (`83.45%`), `90.0%` (`1,860` words) is crossed inside `S14` (`~644.1s`), and `S14` ends at `1,909` words (`92.40%`) before `S15` (`660.0s`), with `voiced: false` lines excluded in `qa/engagement.py`.
10. **11-Module `doc.get("schema")` `/4` Dispatch Check (`CORR-01`)**:
    * Verify all 11 modules (`scene_lint.py:139`, `script_approval.py:51`, `speech.py:60`, `story_lint.py:75`, `beats.py:107`, `editorial_gate.py:342,347`, `silent.py:249,276`, `staging.py:418`, `validate.py:89`, `production_gate.py:89`, `audio/layers.py:53`).
11. **`D-92` `BP-168` & `D-67` Sample Gate Check (`CORR-03`, `CORR-04`)**:
    * Verify `BP-168` matches `D-92` item 7 (`GO <= 3` seeds/shot & `<= 3` review min/min; `PIVOT (3, 6]`; `ABANDON > 6`), `paid_tests` uses existing `p12b_measure ($0.63) + p12b_two_runs ($3.00)` (`$4.13 <= $4.72` 80% of `$5.90` with `p12e_hosts = $1.77` unspent per `D-89`), and `sample.py` operates on whole segments (`["S01", "S02"]` or `sample_approval.json.scope_segments`).
12. **Protected Config & Unmerged PR Invariant Check**:
    * Verify `git diff 5013a55aca5a17a3734150f61a5eb172abcbe3b8 -- explainer_engine/ config/ .claude/ tests/` is empty (`0` code/config modifications on this planning branch).

### 17.5 Explicit Register of Unresolved External & Empirical Uncertainties

1. **`UNC-01` — External Pre-Bundle File Hashes (`316d8042...`, `89aa56d2...`, `173EFDA0...`)**:
   * **Why Unresolved**: Refer to pre-bundle draft edits or a local Windows host file outside the container. All quantitative audits in this roadmap are verified on `49cf3084...` and `2ca7f56f...` and exported in `mold_254_shots_verified_digest.json`.
2. **`UNC-02` — Live GitHub Branch Protection & Remote HF Vault State (`GATE-EXT-MAIN-PROTECT`)**:
   * **Why Unresolved**: Outbound network access to the live GitHub REST API and HuggingFace API is disabled inside the sandbox VM. Must be verified in the live workstation shell before merging [PR #119](https://github.com/vano1919/explainer-engine/pull/119).
3. **`UNC-03` — Empirical `TIER_2` Pose-Delta & CLIP Hero-Sheet Identity Threshold (`CD-03`, `BP-133`)**:
   * **Why Unresolved**: Requires running `GATE-P1b` (`p12b_two_runs = $3.00` reservation / `$2.40` pod cap) to calibrate `BP-133` (`qa/identity.py` CLIP ViT-B-32 hero-sheet cosine threshold) and measure `qwen_nextpose` pose delta. Until `GATE-P1b` and `CD-03` sign-off, `TIER_2` remains capped at `1.5s / 2.0s / 2.5s` (`BP-170`) and `BP-133` remains `REVIEW`.
4. **`UNC-04` — Empirical `4`-Frame Hard-Cut LTX-2.5 Boundary Flicker Rate (`CHG-08`, `BP-128`)**:
   * **Why Unresolved**: Requires inspecting `L1–L3` clips in `GATE-P1b` to confirm that trimming `4` frames per side removes first/last-frame VAE boundary artifacts on hard cuts before changing `BP-128`'s default `[12, 16]` range.
5. **`UNC-05` — Frame-by-Frame Cut-Count & Transcript WPM Logs on External Benchmark Videos (`CS-01..CS-14`)**:
   * **Why Unresolved**: Qualitative structural patterns in `CS-01..CS-14` (`§15.2`) are verified, whereas exact frame-level cut counts and transcript-aligned WPM curves across external YouTube videos require running `ffprobe`/`scdet` + `WhisperX` on downloaded reference video streams; therefore all quantitative pacing numbers remain classified as house hypotheses (`REVIEW` per `D-94`).
6. **`UNC-06` — Open Creator Decisions (`CD-01..CD-10`)**:
   * **Why Unresolved**: Governed exclusively by the creator (§13.2); zero code or paid calibration runs may start until `CD-01` is answered.
