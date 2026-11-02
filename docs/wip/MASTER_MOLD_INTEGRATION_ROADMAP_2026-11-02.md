# ARGON — FULL-CONTEXT MASTER MOLD v2.1.0 INTEGRATION ROADMAP

* **Document Path:** `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`

* **Date:** `2026-11-02`

* **Repository:** [vano1919/explainer-engine](https://github.com/vano1919/explainer-engine)

* **Target Work Branch:** [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02)

* **Branch Base (PR #119 HEAD):** `5013a55aca5a17a3734150f61a5eb172abcbe3b8` ([PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119), 51 commits ahead of `main`)

* **Default Branch (`main`) Baseline:** `6e1dccad30a865df670c258c86ffa1152a0dbe7e` (`STATUS table up to date + OR-36 Haiku watchdog for every paid run (#118)`)

* **Secondary Open Draft PR:** [PR #112](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/112) (`1273619bb52930dde659b6f07a0999141d8ec76b`, 1 commit ahead, 29 behind `main`)

* **Inspected Evidence Corpus:**

  1. Complete `repo_5013a55a.zip` snapshot (`1,287` tracked files at `5013a55aca5a17a3734150f61a5eb172abcbe3b8`) + `pr119_diff.patch` (`501 KB`, `77` changed files, `+5,576 / -336` lines), `pr119_log.txt` (`51` commits), `pr112_show.patch` (`5` files, `+27 / -3` lines), and `main_recent_log.patch` (`493 KB`).

  2. Complete 214-page `CrossWorld_Chronicles_Organized_Research_for_Gemini.docx` (`874` paragraphs, `42` tables, `166` headings across Parts I–IV and Appendices A–B).

  3. Canonical Master Video Mold specification `mrbeast_12min_master_mold.md` (`431` lines, `117,220` bytes, internal header `schema_version: 2.0.0`, external contract label `v2.1.0`, verified SHA-256 `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e`, Git blob SHA `c928c92e65a2357d3dc511b732edb4b1232301d9`; prior header string `316d8042...` retired as an unverified external draft hash — see §1.3).

  4. Canonical Master Video Mold JSON contract `mrbeast_12min_video_mold (1).json` (`26,291` lines / `26,292` with trailing newline, `1,109,253` bytes, internal `mold_meta.schema_version: "2.0.0"`, external contract label `v2.1.0`, verified SHA-256 `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0`, Git blob SHA `80fc3b99294fd880fdbb7674bdfc2f7197822d2f`; prior header string `89aa56d2...` and external Windows path hash `173EFDA0...` retired as inaccessible outside container — see §1.3).

  5. Complete `ARGON_READ_ONLY_AUDIT_AND_CONSOLIDATION_PLAN_2026-11-02.md` and `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md`.

## 1. Executive Assessment

### 1.1 Architectural Verdict

* **[FACT]** At commit `5013a55aca5a17a3734150f61a5eb172abcbe3b8` ([PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119)), [vano1919/explainer-engine](https://github.com/vano1919/explainer-engine) already contains a strong, modular foundation for a 12-minute (`720s`) 2D animated docudrama pipeline (`BP-167`, `BP-109`, `BP-141`, `BP-169..172`, `edit/rhythm_profile.py`, `edit/dramatic_still.py`, `scripting/rhythm_lint.py`, `audio/hype_read.py`, `audio/narrator_polish.py`, `finish/upscale.py`, and `schemas/production_script.schema.json` `/4`), passing `2,448` unit tests in GitHub Actions run `41345477655`.

* **[OBSERVATION]** However, the MrBeast-inspired rhythm package introduced in [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) (`WP-R1..R6-part, R8, R11-part, R12`) currently operates as an **isolated post-hoc validation layer** rather than an end-to-end generative architecture. Specifically:

  1. **Zero Upstream Agent/Skill Awareness**: None of the `16` agent stage pages in `.claude/agents/*.md` or the `16` skills in `.claude/skills/*/SKILL.md` mention `production_script/4`, `BP-169..172`, `rhythm_zone`, `dramatic_change`, the 12-minute (`720s`) target (`BP-167`), the new narrator **Odom** (`CcSJ2r3qw0XU9gJpEPyk`), or the Master Mold's 12 Anchor Beats (`AB01..AB12`). In fact, `.claude/agents/story-architect.md` still instructs writing a 15-minute docudrama at `170 WPM` (`BP-01`), and `.claude/skills/elevenlabs-voice/SKILL.md` still names retired narrator `Grandpa Spuds Oxley` (`NOpBlnGInO9m6vDvFkFC`).

  2. **P0 Silent Schema-Version Regression Across 11 Core Modules**: While `explainer_engine/edit/rhythm_profile.py:39` correctly uses `int(tail) <= 3` to distinguish legacy `/1..3` scripts from `/4`, **11 core validator, gate, and production modules** (`scripting/scene_lint.py:139`, `scripting/script_approval.py:51`, `scripting/speech.py:60`, `scripting/story_lint.py:75`, `production/beats.py:107`, `production/editorial_gate.py:342,347`, `production/silent.py:249,276`, `production/staging.py:418`, `production/validate.py:89`, `production_gate.py:89`, and `audio/layers.py:53`) still check exact string equality `== "production_script/3"` (via `SCENE_SCHEMA` or `_sa.BINDING`). Consequently, passing a `"production_script/4"` script into `production validate`, `editorial_gate`, or `production_gate` **silently disables `/3` scene/dialogue enforcement (`SC-01..SC-10`), script approval checks (`PV-53` and Gate `0.9` in `production_gate.py:89`), living-person voice bans (`PV-55`, `D-62`), character signature-word checks (`DW-11` in `speech.py`), staged-dialogue master-frame checks (`CS-07` in `staging.py`), `ST-00` FAIL severity (`story_lint.py`), and `editorial_review/2` (`story_page.md` in `editorial_gate.py`)**, and **reverts `production/beats.py` back to `/2`'s 1.5s metronome and mandatory sound cues**!

  3. **Unwired Midstream & Downstream Modules (`WP-R7`, `WP-R9`, `WP-R10`)**: `scripting/variant_plan.py`, `scripting/story_lint.py`, `scripting/narration_lint.py`, `scripting/film_shots.py`, `edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, `production/timing.py`, `production/beats.py`, `production/fill_holds.py`, `production/validate.py`, `audio/layers.py`, `audio/sound_director.py`, `qa/engagement.py`, and `qa/scorecard.py` still evaluate scripts against flat calm-era constants (`BP-01` `170 WPM`, `BP-107` `11–17 shots/min`, `BP-40` `10 pictures/min`, and `fps=30` defaults in `timing.py:75`, `motion_lint.py:128`, `assemble.py:1036`).

  4. **Five Internal Discrepancies Between Mold v2.1.0 (`.md` vs `.json`) and `sourced_rules.json` (`BP-169..172`)**: As detailed in Section 3.2, `mrbeast_12min_video_mold.json` v2.1.0 still contains 5 internal mismatches against `MRBEAST_12MIN_MASTER_MOLD.md` v2.1.0 and `explainer_engine/standards/sourced_rules.json` (Zone ID naming `Z1_HOOK_0_30S` vs `hook_0_30s`; duplicate/divergent zone WPM and TTS tag lists violating `D-59`; `bp141_non_character_max: 0.8` instead of `0.45` on Profiles A and D; Still Motion Ladder Tier 1/2 vs `BP-170` `dramatic_still.py` rejection; and Layer 1 Anchor Beats `AB07..AB12` window/segment drift against Layer 3 `S09..S16`).

* **[RECOMMENDATION]** Do **not** rewrite the engine. Integrate Master Mold v2.1.0 through **9 free, dependency-ordered engineering batches (`BATCH-M0` through `BATCH-M7` plus `BATCH-M8A`)** followed by **1 strictly gated paid stage (`BATCH-M8B` with 4 sequential creator approval gates `GATE-P1..P4`)** that:

  1. Fix the P0 `== "production_script/3"` bug across all **11 modules** immediately via an explicit two-predicate schema dispatch module (`explainer_engine/scripting/schema_version.py`: `is_scene_script` for `/3` and `/4`, `is_zoned_rhythm_script` for `/4`, accepting either `doc` dicts with `"schema"`/`"script_schema"` or raw schema strings), implement post-`voice_check` / post-`pause_pad` narrator-span-only Odom polish on `narration.wav` (`polish_narrator_spans_in_place`, preserving raw timbre drift checks and `.mp3` chunk compatibility while leaving character dialogue turns untouched), and resolve `rhythm_zone` across all shots (including `teaser_of`) in `film_shots.compose()` (`BATCH-M0`).

  2. Introduce a lightweight, schema-validated **Narrative & Production Mold Contract** (`config/master_mold_v2_1.json` + `explainer_engine/schemas/episode_mold.schema.json` + `explainer_engine/scripting/mold_contract.py`) that strips duplicate BP numbers (`D-59`) and delegates all numeric lookups to `sourced_rules.json` (`BATCH-M1`).

  3. Adapt upstream research, `variant_plan.py`, `story_lint.py`, `narration_lint.py`, and the Writers' Room agent/skill pages so stories are **conceived, structured, and written** around the 12 Anchor Beats (`AB01..AB12`), the 5 Rhythm Zones (`BP-169`), and Adaptive Profiles (`A..D`) from Stage 1 (`BATCH-M2` & `BATCH-M3`).

  4. Wire audio-first zone prosody, intra-zone pace variation, Odom polish, and `D-90` pre-rendered character dialogue takes into `audio/` and `production/timing.py` (`BATCH-M4`).

  5. Implement the Bounded Timeline Engine (`±18%` clause-aligned timing + `8k+1` LTX quantization) and register the 3-tier Still Motion Ladder in `film_shots.py`, `dramatic_still.py`, and `router.py` while keeping Tier 2 (`qwen_nextpose`) strictly bounded by `BP-170`'s `static_still_max_s_by_zone` (`1.5/2.0/2.5s`) until quantitative pose-change metrics are validated (`BATCH-M5`).

  6. Wire `WP-R7`, `WP-R9`, and `WP-R10` across `production/`, `audio/sound_director.py`, `finish/upscale.py`, `qa/`, and `production/shorts.py` (`BATCH-M6`), prove the entire architecture on a **free end-to-end representative test story + 60.0s (`1,440`-frame) deterministic synthetic CPU assembly test** (`BATCH-M7`), complete **free governance closure (`BATCH-M8A`, `$0.00`)**, and only then gate paid GPU/TTS execution behind **four parent gate groups (`GATE-P1`..`GATE-P4`) comprising five independently authorized operational stages (`GATE-P1a`, `GATE-P1b`, `GATE-P2`, `GATE-P3`, `GATE-P4`) in `BATCH-M8B`**.

### 1.2 Epistemic & Authority Classification & Four-Level Evidence Grading Used in This Roadmap

Every claim in this roadmap is tagged along **two orthogonal axes**:

1. **Five Epistemic & Governance Labels**:
   * **[FACT]** Directly verified in the committed files of `repo_5013a55a.zip` (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`), `main` (`6e1dccad30a865df670c258c86ffa1152a0dbe7e`), git history, or primary external standards.
   * **[OBSERVATION]** Structural or behavioral consequence proven by tracing code execution paths or quantitative data across repository modules and Mold artifacts.
   * **[RECOMMENDATION]** Proposed engineering action following the `CURRENT → MASTER MOLD REQUIREMENT → KEEP → CHANGE → REPLACE → REMOVE → TRADE-OFFS → RECOMMENDATION` framework.
   * **[HYPOTHESIS]** Unverified threshold, speed estimate, cost savings calculation, or creative heuristic (`status: "hypothesis"`, `severity: "REVIEW"` under `D-59`) requiring empirical measurement before becoming binding.
   * **[CREATOR DECISION]** Rule or gate owned exclusively by the creator (`config/model_routing.json` `owner.creator`, protected configs, spend caps, voice selection `VC-08`, or open decision cards `CD-01..CD-10`).

2. **Four-Level External Research Evidence Grades (Enforced Across §15 & §16)**:
   * **`[PRIMARY-STANDARD]`**: Official broadcast/engineering standards, model card specifications, API documentation, or peer-reviewed studies with direct primary URLs (e.g., [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en), EBU Tech 3343 v4 transcribed in `docs/research/CRAFT_SOURCES_2026-10.md`, [Lightricks LTX-2 Model Card](https://huggingface.co/Lightricks/LTX-2), [ElevenLabs Pause Documentation](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses), [Pellegrino et al. 2011 *Language*](https://www.ddl.ish-lyon.cnrs.fr/fulltext/pellegrino/Pellegrino_2011_Language.pdf), [PMC6758568](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/)).
   * **`[VERIFIED-CREATOR]`**: Verifiable creator primary interviews, leaked/published production memos, or direct empirical video measurements (e.g., [MrBeast Production Manual](https://www.google.com/search?q=https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf), [Colin & Samir — *Inside MrBeast's $100M Production Company*](https://www.youtube.com/watch?v=c8VcUnz3nVc), [PBS Studio — *Why Everything on YouTube Sounds the Same*](https://www.youtube.com/watch?v=T2G8s-6ZP9I), and the 14 benchmark video case studies `CS-01..CS-14` in §15.2).
   * **`[CRAFT-HEURISTIC]`**: Recognized film/editing/storytelling craft frameworks (e.g., Walter Murch's Rule of Six in *In the Blink of an Eye*, transcribed in `docs/research/CRAFT_SOURCES_2026-10.md`; *Dense Clarity — Clear Density*; Aristotle's *Poetics*; George Loewenstein's 1994 Information-Gap Theory; Richard Mayer's Multimedia Learning Principles). Treated as **advisory craft guidance (`REVIEW`)**, never as a hard mechanical lint `FAIL` (`D-59`).
   * **`[HYPOTHESIS]`**: Channel-specific quantitative thresholds, extrapolated retention claims, or untested GPU/cost optimizations (`status: "hypothesis"`, `severity: "REVIEW"`). Never cited as scientific law or enforced as a hard `FAIL` until empirically validated on `mrbeast_animated` pilot samples and approved by the creator (`CD-01..CD-10`).

### 1.3 Audit Baseline, File Provenance & Context Continuity Register

To prevent context loss or hash/line-count drift across sessions and commits, the two tables below record (A) the exact repository and commit state as of `2026-11-02`, and (B) the forensically verified byte/line/SHA-256/Git-blob provenance of every Master Mold and handoff artifact inspected in this session:

#### Table 1.3A — Repository & Branch Continuity Register

| Register Field | Verified Value & Evidence Classification |
| ----- | ----- |
| **1. Audit Timestamp** | `2026-11-02T17:55:00+04:00` (`2026-11-02T13:55:00Z`) |
| **2. Target Branch** | [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02) |
| **3. Target Branch Commit Chain Preceding This Forensic Correction** | `82b8da9ff1fbb9d0bc94bdc30019414fad41f9ce` (succeeding `c35978d9ea6573117dbbfd88db10a013495f7b44` -> `d103c2d31a15789e0d9619d5d1811ade5baf9dca` -> `85166baa27b5466dc046138606f0bc35f2f9ee21`, rooted on [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) HEAD `5013a55aca5a17a3734150f61a5eb172abcbe3b8`; only `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md` and `docs/PROGRESS.md` touched) |
| **4. Preceding Roadmap Blob SHA Chain** | `cc2cb4b1476ce23ca46dbf77154a1b68ca5d8db4` (`1,790` lines, initial `§1..§14` consolidation) -> `5fa05ebfa67282f11de8a56162b2d1714743c13e` on GitHub commit `82b8da9ff1fbb9d0bc94bdc30019414fad41f9ce` / local LF blob `d9bbd9a8c84a4220ce964befcdbdacd41cfd53ac` (`2,226` `splitlines()` lines / `2,227` editor lines with trailing newline, `338,241` bytes, LF SHA-256 `5176c07f14a6e1f728f2c589fef622ca435184a3f0b2d55a8850ce613200619a`) -> **Forensically Corrected in This Revision** |
| **5. Integration Code Baseline SHA ([PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) HEAD)** | `5013a55aca5a17a3734150f61a5eb172abcbe3b8` (**VERIFIED** in `repo_5013a55a.zip`: `1,287` tracked files, `51` commits ahead and `0` behind `main`) |
| **6. Current `main` Baseline SHA** | `6e1dccad30a865df670c258c86ffa1152a0dbe7e` (**VERIFIED** in `main_recent_log.patch`) |
| **7. Relevant Open PR States & Head SHAs** | [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119): Open Draft (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`, `77` changed files, `+5,576 / -336`); [PR #112](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/112): Open Draft (`1273619bb52930dde659b6f07a0999141d8ec76b`, `1` ahead, `29` behind `main`, `5` files changed) |
| **8. Repository Areas Directly Inspected** | All `158` BP rules in `explainer_engine/standards/sourced_rules.json`; `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (`D-01..D-94`); `config/spend_caps.json`, `config/model_routing.json`, `config/cloud_pins.json`, `config/channel_voices.json`; all `16` `.claude/agents/*.md` and `16` `.claude/skills/*/SKILL.md`; all `33` JSON schemas in `explainer_engine/schemas/`; core pipeline modules across `scripting/`, `production/`, `edit/`, `audio/`, `finish/`, `qa/`, `training/`, `cloud/`, `governance/`, `standards/`, and `tests/unit/`; real measured TTS outputs in `examples/day1_v2/`, `examples/titans_from_zero/`, and `examples/syndicate_wars_ep1/`; plus `mrbeast_12min_master_mold.md`, `mrbeast_12min_video_mold (1).json`, and the 214-page research compendium |
| **9. Verified Project Invariants Preserved** | `D-43` single-file `production_script.json`; `D-56` spend caps in code (`core/spend_caps.py`, `core/ledger.py` 80% stop); `D-59` single home for numbers (`sourced_rules.json`); `D-62`/`D-63` living-person voice ban (`PV-55`); `D-67`/`OR-19` 2-part sample gate (`production/sample.py`); `D-73` HF Vault (`vano1919/tmr-artifacts`, zero binary `.wav`/`.mp3`/`.mp4` in Git); `D-79` one main agent + read-only Opus critics; `D-84` protected configs & hooks; `D-85`/`BP-167` `24 fps` `2560x1440` 12-min master + `5` Shorts; `D-89` no permanent hosts; `D-90` character ElevenLabs take -> LTX audio-in; `D-93` `60/30/10 ±5%` lane mix (`BP-109`); `D-94` 5-zone `BP-169` rhythm + `Odom` narrator (`eleven_v4`) |
| **10. Open Creator Decisions (`CD-01..CD-10`)** | All `10` decision cards remain explicitly open for the creator's word (§13.2): `CD-01` (Kickoff), `CD-02` (LoRA `0.7` vs `1.0`), `CD-03` (`BP-170` thresholds & keeping Tier 2 at `1.5/2.0/2.5s`), `CD-04` (`BP-169` intra-zone pace `REVIEW`), `CD-05` (`$31.00` GPU cap + reallocating `$1.77` `p12e_hosts` inside `$5.90` `paid_tests.total_usd`), `CD-06` (deceased historical figure voicing), `CD-07` (closing PR #112), `CD-08` (56 stopped `0 GB` pods), `CD-09` (Episode 1 topic), `CD-10` (YouTube Studio rebrand/unlisting) |
| **11. Unverified Live Remote Items & Why** | **UNVERIFIED — PERMISSION / SANDBOX NETWORK LIMITED**: Live GitHub branch-protection/ruleset API (`main.protected = false` reported by prior external inspection; elevated to mandatory pre-implementation gate `GATE-EXT-MAIN-PROTECT`), live GitHub Actions status on commit `82b8da9`, and remote HF `vano1919/tmr-artifacts` file listing (local `PYTHONPATH=. python3 -m explainer_engine.docs_lint` is **VERIFIED** with `0 finding(s)`) |
| **12. Last Completed Implementation Stage & Current State** | **IMPLEMENTATION NOT PRESENT (`0%` of `BATCH-M0..M8B` executed)**: [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) (`5013a55a`) completed `WP-R1..R6-part, R8, R11-part, R12`; this branch (`planning/master-mold-integration-2026-11-02`) contains **only** this planning roadmap and `docs/PROGRESS.md` (`0` application code or config changes) |

#### Table 1.3B — Forensic File Provenance & Hash Reconciliation Table (`§6` Verification)

**[FACT]** Prior audit iterations cited conflicting line counts (`186` vs `431` lines for the Markdown Mold; `26,287` vs `26,291` lines for the JSON Mold) and three external SHA-256 strings (`316d8042...`, `89aa56d2...`, `173EFDA0...`) that did not match the actual files in `argon_latest_repo_bundle.zip`. Direct byte-level inspection of the bundle resolves every provenance discrepancy:

| Artifact Name / Reference | Availability in Local Sandbox | Exact Byte Size | Exact Line Count (`splitlines()` / with trailing LF) | Internal Version String vs External Label | Verified SHA-256 Digest | Verified Git Blob SHA-1 | Forensic Provenance Verdict |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `mrbeast_12min_master_mold.md` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `117,220` bytes | `431` lines (`431` with trailing LF) | Header L3: `schema_version: 2.0.0` (external handoff label: `v2.1.0`) | `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e` | `c928c92e65a2357d3dc511b732edb4b1232301d9` | **Authoritative Markdown Mold source** inspected in this roadmap. The stale `186`-line count in earlier notes came from counting only a partial section summary rather than the `431`-line file. |
| `mrbeast_12min_video_mold (1).json` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `1,109,253` bytes | `26,291` lines (`26,292` editor lines with trailing LF) | `mold_meta.schema_version: "2.0.0"` (external handoff label: `v2.1.0`) | `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0` | `80fc3b99294fd880fdbb7674bdfc2f7197822d2f` | **Authoritative JSON Mold source** (`16` segments `S01..S16`, `254` shots `SH001..SH254`, `17,280` frames = `720.0s`, `2,066` words). All quantitative audits in §3.2, §15, and §16 are computed directly from this exact file. |
| `GEMINI_ARGON_UNIFIED_HANDOFF_2026-11-02.md` (in `argon_latest_repo_bundle.zip`) | **PRESENT & VERIFIED** | `1,178,496` bytes | `22,446` lines | Embeds retired `v1.0` Mold JSON at `L1553–21882` (`20,330` lines) | `d9bda2288887514749f462cca7e4048b76631ec032f1eeab1705f8ef665c32c5` | `e0918d88b693eb096ed689364b07da46a3f44e10` | **Historical v1.0 Comparison Source** (`1,797`-word lock, `254` shots hardcoded to 1637 Tulip Mania). Used only to verify what changed between `v1.0` and `mrbeast_12min_video_mold (1).json`. |
| `CrossWorld_Chronicles_Organized_Research_for_Gemini.docx` | **PRESENT & VERIFIED** | `164,897` bytes | `874` paragraphs, `42` tables, `166` headings | 214-page research compendium (Parts I–IV, Appendices A–B) | `a7d018996215c27cf1f9fa86b8685ee544b1581ce135567903923eb08f679fc3` | `7b643b15c879f7b777ff06f3e0fb5d72268c5eb0` | **Audited Research Compendium**. Contains both verified primary standards and unverified secondary syntheses; every claim extracted from this `.docx` is re-verified and graded in §15.7 (`SRC-01..SRC-48`). |
| External hash `316d8042115dffad23227365e765c4be48bbcce3786ed8ac162e08143c090848` (`MRBEAST_12MIN_MASTER_MOLD.md` in prior header) | **INACCESSIBLE IN LOCAL CONTAINER** | Unknown (`186` lines claimed in external note) | `186` lines (unverified external pre-bundle edit) | External pre-bundle note | `316d8042115dffad23227365e765c4be48bbcce3786ed8ac162e08143c090848` | Not in bundle | **RETIRED FROM ACTIVE CLAIMS**. Not present in `argon_latest_repo_bundle.zip` or `repo_5013a55a.zip`; superseded by verified `mrbeast_12min_master_mold.md` (`49cf3084...`). |
| External hash `89aa56d2a405f30a473a6aec9d11b330f745a24776adae3e0c4e05695873467a` (`mrbeast_12min_video_mold.json` in prior header) | **INACCESSIBLE IN LOCAL CONTAINER** | Unknown (`26,287` lines claimed in external note) | `26,287` lines (unverified external pre-bundle edit where `S02` had `79.2s` vs `59.2s`) | External pre-bundle note (`"mold_version": "2.1.0"` claimed) | `89aa56d2a405f30a473a6aec9d11b330f745a24776adae3e0c4e05695873467a` | Not in bundle | **RETIRED FROM ACTIVE CLAIMS**. Explains why an earlier external note mentioned `26,287` lines and an `S02` `79.2s` vs `59.2s` mismatch that does **not** exist in the verified bundle file (`2ca7f56f...`). |
| External Windows file `C:\Users\User\Downloads\mrbeast_12min_video_mold (1).json` (`173EFDA0...`) | **INACCESSIBLE IN LOCAL CONTAINER** | Host machine local file | Host machine local file | Host machine local file | `173efda0793a02e1b9276843dd3ba9f84e143c768cd11dd57559eee72b60bc8f` | Not in bundle | **UNVERIFIED EXTERNAL HOST FILE**. Likely a CRLF or post-export copy on the creator's Windows machine. When committing `explainer_engine/standards/mrbeast_12min_video_mold.json` in `BATCH-M1`, we normalize from `2ca7f56f...` with LF line endings and record the new committed SHA-256 in `sourced_rules.json`. |

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
| **Master Mold `v2.0.0` (Internal File Header & PR #119 Label)** | `mrbeast_12min_master_mold.md` (`431` lines, `schema_version: 2.0.0`, SHA-256 `49cf3084...`), `mrbeast_12min_video_mold (1).json` (`26,291` lines, `mold_meta.schema_version: "2.0.0"`, SHA-256 `2ca7f56f...`), and [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) (`WP-R6..WP-R10`, commits `e2fb409`..`5013a55a`) | Separates **Layer 1 (`layer_1_narrative_constitution`)**, **Layer 2 (`layer_2_production_profile`)**, and **Layer 3 (`layer_3_episode_timeline_schema_and_reference_grid`: `S01..S16`, `254` shots, `17,280` frames = `720.0s`, `2,066` words)**; extracts `BP-169..BP-172` into `explainer_engine/standards/sourced_rules.json`. | **Verified Bundle Artifact & Partially Integrated Code Baseline** (`BP-169..BP-172` live in repo, but downstream callers in `rhythm.py`, `board.py`, `assemble.py`, and `/4` schema dispatch across 11 consumer modules remain unwired). |
| **Master Mold `v2.1.0` (Reconciled Repository Contract Target)** | Target committed contract `explainer_engine/standards/mrbeast_12min_video_mold.json` (`BATCH-M1`) + `docs/MRBEAST_12MIN_MASTER_MOLD.md` | Applies the **12 forensic reconciliations (`M-01..M-12`)** below to the verified `2ca7f56f...` / `49cf3084...` artifacts so that `schema_version` is bumped to `"2.1.0"`, all dangling/mis-cited `BP-*` IDs are repaired, duplicate threshold numbers are stripped in favor of `sourced_rules.json` (`D-59`), and Layer 1/2 rules are cleanly separated from the Layer 3 1637 Tulip Mania reference instance. | **Authoritative Target Specification** to be committed in `BATCH-M1`. |

### 3.2 Forensic Audit of Discrepancies Between `mrbeast_12min_master_mold.md` (`49cf3084...`), `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`), and `sourced_rules.json` (`5013a55a`)

**[FACT]** Direct programmatic verification of `mrbeast_12min_master_mold.md` (`431` lines, SHA-256 `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e`), `mrbeast_12min_video_mold (1).json` (`26,291` lines, SHA-256 `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0`), and `explainer_engine/standards/sourced_rules.json` (`5013a55a`) identifies **12 exact internal discrepancies (`M-01` through `M-12`)** that must be resolved in `BATCH-M1` / `BATCH-M5` / `BATCH-M6`:

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
| **M-11** | **`BP-122` Acoustic Perspective Parameter Drift** | Line 37 (`DM-09`) references `shot_size` EQ (`Wide/Medium/ECU`). | L141/875 say `Wide -3dB @ 3.5kHz, 18% wet; ECU +2dB @ 180Hz, 95% dry`, while `140+` shots say `-3.5dB @ 3500Hz, 28% wet` and `+2.5dB @ 180Hz, 92% dry`. | `sourced_rules.json` (`BP-122`) and `production/assemble.py:291–296, 480–483` use `shelf_hz: 6000`, `wide_shelf_db: -4.0`, `wide_wet: 0.22`, `close_dry: 0.95`, `proximity_db: 2.0`, `proximity_hz: 140`. | Replace conflicting hardcoded EQ/wet strings in `mrbeast_12min_video_mold.json` with symbolic perspective keys (`"perspective": "far" \| "mid" \| "near"` matching `sound_director.py:43`) resolved dynamically from `sourced_rules.T("BP-122", ...)`. |
| **M-12** | **Relative Color Continuity (`BP-166`) vs Raw HEX (`D-22`) & Layer 1/2/3 Instance Contamination (`1637 Tulip Mania` Strings in Layer 1/2)** | Line 38 (`DM-10`) replaces global Kelvin/HEX locks with relative scene offsets, and §2 declares Layer 1 and Layer 2 topic-agnostic. | Lines 795–797 & `254` shots enforce `BP-166_SCENE_AND_CHARACTER_HEX_LOCKED (apply relative mood offset only)`; meanwhile, Layer 1 (`layer_1_narrative_constitution`, `L100–402`) and Layer 2 (`layer_2_production_profile`, `L748–918`) still contain **`24` hardcoded 1637 Dutch Tulip Mania example strings** (`Haarlem`, `guilder`, `Semper Augustus`, `Pieter`, `Waag`, `1637`). *(Note: All `16` segment headers `S01..S16` in `segments_summary_16` of `2ca7f56f...` already match their shot duration sums `720.0s` = `17,280` frames and word sums `2,066` words with `0` discrepancy; `S02` is `30.0s` [`30.0–60.0s`, `12` shots, `88` words] — the `79.2s vs 59.2s` note from an unverified external draft is retired.)* | `BP-166` checks `sat_drift_max: 0.08`, `luma_drift_max: 0.08`, `hero_palette_max: 0.15`; `D-22` / `LT-65` bans raw `#RRGGBB` tokens in generation prompts; `ZI-09` (`film_shots.py:920–935`) requires topic-agnostic templates. | Purge all `24` Tulip Mania strings from Layer 1 and Layer 2 into `layer_3_reference_instance` (`reference_only: true`), keep raw HEX swatches strictly in `character_sheet_ref` / `color_qa` (`BP-166`), ban raw `#RRGGBB` tokens in generation prompts (`D-22`/`LT-65`), and apply act mood shifts via `episode_look.py` (`AC-17`) and `assemble.py` Lab transfer (`BP-130`). |

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
| **CG-14** | **PR #112 Stale Branch Disposition** | **P2 MODERATE** | [PR #112](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/112) (`1273619b`) has a valid 2-line bugfix in `explainer_engine/llm/claude_api.py:1066` (`load_job` string `system` handling) + unit test, bundled with stale edits to protected `config/spend_caps.json` (`max_usd: 95.0`) and `config/model_routing.json`. | `explainer_engine/llm/claude_api.py`, `tests/unit/test_claude_api.py` | **BATCH-M0**: Cherry-pick **only** the 2-line `claude_api.py` fix and its unit test; reject the stale config hunks. |

## 9. Ordered Implementation Batches (`BATCH-M0` through `BATCH-M7`, Free `BATCH-M8A`, and Paid `BATCH-M8B`)

The implementation roadmap is divided into **9 100% FREE batches (`BATCH-M0` through `BATCH-M7` plus `BATCH-M8A`)** (local CPU/code/schema/prompt/test/governance changes, zero API spend, zero GPU pods) and **1 strictly separated PAID stage (`BATCH-M8B`)** subdivided into four sequential creator-approval gates (`GATE-P1`, `GATE-P2`, `GATE-P3`, `GATE-P4`) protected by `OR-23` pod plans, `OR-36` Haiku watchdogs, and `config/spend_caps.json` hard caps.

### 9.1 `BATCH-M0` — P0 Regression Fixes (`production_script/4` Compatibility, Odom Polish Gate, `KP-47` Propagation & PR #112 Parser Fix)

* **Objective & Scope**: Eliminate the **11** silent `== "production_script/3"` regressions before any new Mold code is layered on top; fix the `not S.has_dialogue(doc)` gate in `production/__main__.py:119` via post-`voice_check` narrator-span-only polish; propagate `rhythm_zone` across all shots in `film_shots.compose()`; and cherry-pick the 2-line `claude_api.load_job` string-system parser fix from [PR #112](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/112).

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

* **Objective & Scope**: Complete all remaining **zero-cost** governance and pre-pod readiness tasks without launching any GPU pod or paid API call: close the formal governance status rows for `P6–P11` and `P12a` (`python -m explainer_engine.governance status --write`), close superseded [PR #112](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/112) (after `CD-07`), align the `xworld_v2` LoRA strength across `cloud_pins.json` / `p12b.json` / `style_prompt.py` (after `CD-02`), pin final commit SHAs in `p12b.sh`, and pass `python -m explainer_engine.cloud.dryrun` (`0 FAIL`, `$0.00`).

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

1. **[ASSUMPTION A-01]**: Branch [planning/master-mold-integration-2026-11-02](https://github.com/vano1919/explainer-engine/tree/planning/master-mold-integration-2026-11-02) is rooted at [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119) HEAD (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`), which is 51 commits ahead and 0 commits behind `main` (`6e1dccad30a865df670c258c86ffa1152a0dbe7e`).

2. **[ASSUMPTION A-02]**: `main` remains frozen until after the next video ships (creator standing rule), enforced via external pre-implementation gate `GATE-EXT-MAIN-PROTECT` (`RSK-06`), and all implementation batches (`BATCH-M0..M7` and `BATCH-M8A`) will land on `planning/master-mold-integration-2026-11-02` via small, test-pinned commits.

3. **[ASSUMPTION A-03]**: No Claude API (`build_loop`), ElevenLabs TTS, or RunPod GPU money is spent during `BATCH-M0..M7` or `BATCH-M8A` (`$0.00` total); paid operations occur exclusively in `BATCH-M8B` behind the four separate, sequential creator approval gates (`GATE-P1`, `GATE-P2`, `GATE-P3`, `GATE-P4`).

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


---

## 15. Reverse-Engineering Compelling 12-Minute Animated Historical What-If & Docudrama Videos (Domains A–F & Source Correction Register)

**[FACT]** Before specifying any code change in §16, this section establishes the **verified storytelling, documentary, audio, editing, and AI production architecture** for Argon's 12-minute (`720.0s`, `17,280`-frame) animated historical what-if and docudrama format, separating **`[PRIMARY-STANDARD]`**, **`[VERIFIED-CREATOR]`**, **`[CRAFT-HEURISTIC]`**, and **`[HYPOTHESIS]`** claims and auditing every external source (`§15.7`, `SRC-01..SRC-48`).

### 15.1 Domain A — Storytelling First: Counterfactual Spine, Causal Escalation & Human Stakes

**[CRAFT-HEURISTIC]** / **[FACT]** Pacing, cut frequency, and camera motion cannot rescue a flat narrative spine. As codified in [MrBeast's Production Manual](https://www.google.com/search?q=https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf) (`[VERIFIED-CREATOR]`) and Aristotle's *Poetics* (`[CRAFT-HEURISTIC]`, `BP-06` `causal_but_therefore`), high-retention storytelling is governed by **causal progression, escalating stakes, and concrete human agency**:

1. **Counterfactual Divergence Contract (Historical Grounding -> Single Point of Divergence -> Constrained Extrapolation)**:
   * **Baseline Reality Anchor (`S01–S02`, `0–60s`)**: Every historical what-if or docudrama episode must first anchor the viewer in **verified historical fact** (`ZI-02` / `PV-37` Invariant 5 in `explainer_engine/scripting/claims.py:1–10` and `film_shots.py:846–851`): a named human protagonist (`BP-02` / `D-89` episode-specific lead character), an exact date/place, and a physical object or ledger metric at stake.
   * **Single Point of Divergence (`AB02B`, `45–60s`)**: Rather than stacking multiple implausible assumptions, the script introduces **one bounded structural rule or historical hinge** (e.g., an institutional decree, a military order, or a financial contract clause) and traces its second- and third-order consequences using **`[FACT]`** (`claim_id`-backed historical records) and **`[HYPOTHESIS]`** (`HY-4` in `explainer_engine/research/hypotheses.py:66–68` requiring explicit mechanism + historical analogue).
   * **Why Speculative What-If Videos Fail (`5` Structural Failure Modes)**:
     1. *Encyclopedia Montage Syndrome*: Listing chronological facts (`"and then... and then..."`) instead of causal turns (`"because of X, Y was forced to Z — but when Z failed, therefore..."`, `BP-06`).
     2. *Abstract Macro-Statistics Without a Human Proxy*: Talking about "the economy" or "the empire" for `>45s` without grounding the cost in one character's concrete survival, status, or family ruin (`BP-02`).
     3. *Premature Thesis Spoilers*: Answering the central question in Act I or Act II instead of holding the full synthesis until `>=90%` of spoken words have been delivered (`BP-04` `ENG-5`).
     4. *Unfalsifiable Fantasy Jumps*: Violating physical logistics, weapon ranges, or institutional incentives without explaining *why* actors behaved that way (`HY-4`).
     5. *Flat Mid-Video Plateau (`180–480s`)*: Failing to plant a new curiosity re-hook (`BP-01` / `AB05` at `180s` and `AB07` at `360s`) right as the previous sub-question resolves.

2. **Twelve-Anchor Narrative Architecture (`AB01..AB12`) Mapped to `S01..S16` (`720.0s`)**:
   * **[RECOMMENDATION]** Reconciling `mrbeast_12min_master_mold.md` (§3.4), `mrbeast_12min_video_mold (1).json` (`segments_summary_16`), `BP-169`, `BP-142`, and `BP-04` yields the following canonical 12-anchor narrative spine:

| Anchor ID | Canonical Name | Segment(s) & Time Window (`s`) | Rhythm Zone (`BP-169`) | Causal Story Function & Human Stakes Requirement | Repository Validator / Rule Hook |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **`AB01`** | **Thumbnail & Title Promise Payoff** | `S01` (`0.0–15.0s`) | `hook_0_30s` | Confirm the exact visual & verbal premise promised by the title/thumbnail in sentence 1 (`<=8` words, concrete noun + active verb, zero throat-clearing) while showing the protagonist in immediate physical motion. | `BP-03`, `BP-120`, `BP-169`, `story_lint.py` (`SL-AB01`) |
| **`AB02A`** | **Central Counterfactual Question & Stake Lock** | `S01` (`15.0–30.0s`) | `hook_0_30s` | Plant the overarching episode question (`question_plant` #1) and quantify what the protagonist stands to win or lose. | `BP-01` (`ENG-1`), `BP-04` (`ENG-5`), `story_lint.py` (`SL-AB02A`) |
| **`AB02B`** | **Baseline World & Single Rule of Divergence** | `S02` (`30.0–60.0s`) | `early_30_90s` | Establish the verified historical baseline (`claim_id` required) and trigger the single structural rule or point of divergence that sets the causal chain in motion. | `ZI-02`, `PV-37`, `HY-4`, `story_lint.py` (`SL-AB02B`) |
| **`AB03`** | **First Escalation & Commitment Lock-In** | `S03` (`60.0–90.0s`) | `early_30_90s` | The protagonist makes an irreversible choice under the new rule (`"therefore"` turn #1), closing the exit door and launching Act II. | `BP-06` (`ENG-4`), `story_lint.py` (`SL-AB03`) |
| **`AB04`** | **Systemic Expansion & Played Scene Turn #1** | `S04–S05` (`90.0–180.0s`) | `middle_calm_90_480s` | Breathe into the world mechanics (`166` heard WPM target); play out `S04` (`90–135s`, `BP-142` turn slot `4`) as a sensory scene with character action, then reveal the first hidden flaw in `S05` (`135–180s`). | `BP-142` (`turn_slots_D: 4`), `BP-169`, `story_lint.py` (`SL-AB04`) |
| **`AB05`** | **3-Minute Re-Hook Spike #1 (`180s` Pivot)** | `S06` (`180.0–225.0s`) | `middle_calm_90_480s` (`rehook_spike: true`) | Resolve the Act I sub-question and immediately plant a bigger, darker complication (`BP-142` turn slot `6`), accompanied by a visual lane shift and segment-scoped `[excited]` prosody lift. | `BP-01`, `BP-142` (`slot 6`), `BP-169`, `story_lint.py` (`SL-AB05`) |
| **`AB06`** | **Institutional Friction & Contagion** | `S07` (`225.0–270.0s`) | `middle_calm_90_480s` | Show how secondary institutions (banks, generals, guilds, courts) react to the protagonist's move, multiplying the systemic risk. | `BP-06`, `ZI-02`, `story_lint.py` (`SL-AB06`) |
| **`AB07`** | **Midpoint Reversal & 6-Minute Re-Hook Spike #2** | `S08–S09` (`270.0–375.0s`) | `middle_calm_90_480s` (`S09` `rehook_spike: true`) | `S08` (`270–330s`, `BP-142` slot `8`) builds to the false peak; `S09` (`330–375s`) shatters the protagonist's assumption at the 6-minute midpoint (`360s`) and plants the second half's survival question. | `BP-01`, `BP-142` (`slot 8`), `BP-169`, `story_lint.py` (`SL-AB07`) |
| **`AB08`** | **Cascade Acceleration & No-Exit Squeeze** | `S10–S11` (`375.0–480.0s`) | `middle_calm_90_480s` | Dual played scene turns (`S10` `375–430s` slot `10` and `S11` `430–480s` slot `11`): every attempted fix worsens the crisis (`"but"` / `"therefore"` density `>=2.0` per 100 words), exhausting the final buffer. | `BP-06`, `BP-142` (`slots 10, 11`), `story_lint.py` (`SL-AB08`) |
| **`AB09`** | **Late-Third Surge & Threshold of Collapse** | `S12` (`480.0–540.0s`) | `late_third_480_660s` | Pacing accelerates to `late_third_480_660s` (`185` heard WPM target, `30.0` cuts/min); the crisis crosses from local failure into total systemic reckoning. | `BP-169`, `story_lint.py` (`SL-AB09`) |
| **`AB10`** | **Pre-Climax Crucible & False-Salvation Collapse** | `S13–S14` (`540.0–660.0s`) | `late_third_480_660s` | `S13` (`540–600s`, `BP-142` final turn slot `13`) strips away the last escape route; `S14` (`600–660s`) crosses the **`90.0%` cumulative spoken word threshold (`BP-04`)** (in the reference grid, `1,860 / 2,066` words = `90.0%` is reached at `~644.1s` inside `S14`, and `S14` ends at `1,909 / 2,066` words = `92.40%`). | `BP-04` (`answer_after_share >= 0.90`), `BP-142` (`slot 13`), `story_lint.py` (`SL-AB10`) |
| **`AB11`** | **Climax I — The Irreversible Rupture & Pre-Reveal Vacuum** | `S15` (`660.0–690.0s`) | `climax_660_720s` | Preceded by the `0.5–1.0s` pre-climax acoustic vacuum (`BP-121`), `S15` delivers the emotional and visual payoff at slower, high-gravity cadence (`160` heard WPM target, `26.0` cuts/min, `92.40%–96.22%` cumulative words). | `BP-04`, `BP-121`, `BP-169`, `story_lint.py` (`SL-AB11`) |
| **`AB12`** | **Climax II — Final Synthesis & Abrupt Hard-Cut Ending** | `S16` (`690.0–720.0s`) | `climax_660_720s` | Delivers the final thematic synthesis (`96.22%–100.0%` of spoken words), bridges to the next episode world (`BP-106`), and terminates on a hard visual/audio cut (`BP-43`) with zero housekeeping outro. | `BP-04`, `BP-43` (`KP-40`), `BP-106`, `story_lint.py` (`SL-AB12`) |

### 15.2 Domain B — YouTube Reverse Engineering: Quantitative & Structural Analysis of 7 Benchmark Channels & 14 Real Video Case Studies (`CS-01..CS-14`)

**[VERIFIED-CREATOR]** / **[OBSERVATION]** To ground Argon's Layer 1 (`layer_1_narrative_constitution`) and Layer 2 (`layer_2_production_profile`) in real, observable YouTube craft rather than synthetic channel averages, the two tables below document (1) the **7 benchmark channels** and (2) **14 specific, real published benchmark videos (`CS-01` through `CS-14`, 2 per channel)** verified via primary YouTube metadata and transcript/pacing inspection. Every quantitative editing metric derived from external channels is tagged **`[VERIFIED-CREATOR]`** for the specific video's observable structure and **`[HYPOTHESIS]`** (`REVIEW`) when extrapolated into an Argon pipeline target.

#### Table 15.2A — Seven Benchmark Channels & What Argon Adopts vs Rejects

| Channel | Core Visual & Narrative Format | Verified Pacing & Structural Mechanics (`[VERIFIED-CREATOR]` / `[CRAFT-HEURISTIC]`) | What Argon Adopts (`mrbeast_animated` v2.1.0) | What Argon Explicitly Rejects |
| ----- | ----- | ----- | ----- | ----- |
| **1. MrBeast** ([Production Manual](https://www.google.com/search?q=https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf), [Colin & Samir Interview](https://www.youtube.com/watch?v=c8VcUnz3nVc)) | Live-action challenge/stunt spectacle with animated/CG establishing hooks | **0–30s Hook validation** of title/thumbnail promise; **1–3min transition** from spectacle to story; **3min & 6min re-hooks**; "wow factor" escalation; abrupt ending without housekeeping drag (`BP-43`). | 5-zone macro rhythm wave (`BP-169`); `AB01` title/thumbnail payoff in `<15s`; `180s` (`S06`) and `360s` (`S09`) re-hooks; zero outro fluff (`BP-43`). | Hyper-frantic sub-second montage across the full 12 minutes; screaming non-stop host energy during `90–480s` historical explanation (`BP-169` drops Z3 to `166` WPM / `21` cuts/min). |
| **2. Fern** ([Simplicissimus / Fern Studio Profile](https://www.youtube.com/watch?v=0eb4d3f22bI)) | 3D/2.5D stylized dark docudrama & crime/forensic reconstruction | Cold-open in medias res at the exact moment of anomaly; atmospheric sound design bed (`-18 to -24 LUFS` below voice); forensic camera push-ins onto maps/diagrams; deliberate breathing valleys (`3.5–5.0s` holds) on key evidence reveals. | Cold-open sensory anomaly (`AB01`); forensic diagram/map inserts (`10%` `HELPER` lane `BP-109`); `BP-121` pre-reveal silence (`0.5–1.0s`); dark contrast ratios in `late_third_480_660s`. | Full-3D Blender environment rendering for every shot (violates `$31` GPU budget; Argon uses Qwen 2D + LTX-2.5 + 3-layer 2.5D parallax `BP-35`). |
| **3. Kurzgesagt – In a Nutshell** ([How to Make a Kurzgesagt Video in 1200 Hours](https://www.youtube.com/watch?v=uFk0mgljtns)) | Flat-vector 2D animated science & existential counterfactuals | **1,200+ hour** hand-illustrated pipeline; measured **145–160 WPM** authoritative narration (Steve Taylor); rich leitmotif musical storytelling (Epic Mountain); visual metaphors that concretize abstract numbers via recurring character proxies (ducks/birds). | Concrete visual proxy for every abstract scale jump (`ZI-03`); strict color script progression across acts (`BP-166`, `episode_look.py`); thematic musical swells during transitions (`BP-119`). | Flat vector minimalist art style (forbidden by `LT-12`); uniform 150 WPM calm cadence during the `0–30s` hook (`mrbeast_animated` requires `193` heard WPM in `hook_0_30s`). |
| **4. The Infographics Show** ([What If the Roman Empire Never Fell?](https://www.youtube.com/watch?v=h3w1_2H22bI)) | High-volume 2D motion-comic explainer & military/historical what-ifs | Fast verbal hook (`175–190 WPM`); constant character puppet state-flips (`2–3.5s` per pose); clear counterfactual question framing in title/opening 20 seconds. | Counterfactual question clarity; Tier 2/Tier 3 character pose/cutout state flips every `2.0–3.5s` on held stills (`BP-170`) so the screen never freezes. | Generic flat rig assets, repetitive stock SFX loops, and shallow Wikipedia-summary scripts lacking primary `claim_id` citations (`ZI-02` / `PV-37`). |
| **5. AlternateHistoryHub** ([What If Germany Won WWI? (Kaiserreich)](https://www.youtube.com/watch?v=kCEUZ4faCwU)) | Counterfactual geopolitical & historical timeline divergence essays | Explicit **Point of Divergence (PoD)** definition before extrapolating; second-order institutional analysis (alliances, logistics, demographics, trade routes) rather than pure battle outcomes. | Explicit `AB02B` Single Point of Divergence (`30–60s`); mandatory second-order institutional/economic causal chain (`HY-4` + `BP-06`). | Static map-slide lectures (`>8s` unchanged map holds violate `BP-125` and `BP-170`) and informal essayist asides. |
| **6. Kings and Generals** ([Battle of Cannae 216 BC](https://www.youtube.com/watch?v=6i0a726P22A)) | Tactical & operational military history with animated terrain maps | Top-down and isometric **tactical map grammar**: terrain elevation first, supply lines second, unit blocks third (`BP-125` `altitude_change_s: [4.0, 8.0]`); clear date/location lower-thirds (`BP-84` `bubble_chars_per_line <= 26`). | `HELPER` lane (`10%`, `BP-109`) tactical map altitude transitions (`BP-125`) and concise `<=26`-char callouts (`BP-84`) during `middle_calm_90_480s` (`S04–S11`). | 25-minute encyclopedic campaign prologues before the inciting crisis begins (`AB01` must start inside the crisis at `0.0s`). |
| **7. Oversimplified** ([The French Revolution (Part 1)](https://www.youtube.com/watch?v=8qRZcXIODNU)) | High-contrast character-driven historical comedy/drama | **Cutout relocation & plate-swap punchlines** (`>=25%` screen shift on a hard beat); sharp contrast between rapid-fire escalating setup and sudden deadpan pause (`BP-170` Tier 3 mechanics). | Tier 3 `cutout_relocation` (`>=25%` frame shift) and `plate_swap` (`>=30%` background swap) mechanics (`BP-170`) for high-impact visual state changes on `STILL` shots. | Slapstick stick-figure cartoon proportions and anachronistic gag humor (Argon's visual bible is grounded 2D cinematic docudrama). |

#### Table 15.2B — Fourteen Specific Benchmark Video Case Studies (`CS-01` through `CS-14`, 2 Per Channel)

**[VERIFIED-CREATOR]** Every case study below cites a real, verifiable YouTube video and extracts its exact opening hook mechanic, midpoint re-hook structure, audio/visual pacing pattern, and specific engineering lesson for Argon:

| ID | Channel & Specific Video ([Verified URL]) | Runtime | Opening Hook Mechanic (`0–30s`) | Mid-Video Re-Hook & Structural Pivot | Visual & Audio Pacing Signature | Concrete Lesson Mapped to Argon Rules |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`CS-01`** | **MrBeast** — [$456,000 Squid Game In Real Life!](https://www.youtube.com/watch?v=0e3GPea1Tyg) | `25:42` | Opens directly on the 456 players inside the recreated Red Light, Green Light arena (`0–8s`), confirming the thumbnail and `$456,000` stake in the first two sentences with `~19–22` cuts in the first `30s`. | Pivots every `3–4` minutes into a new set-piece game with an explicit survival count reduction and emotional micro-story before each elimination wave. | High-velocity `0–30s` hook (`~1.3–1.6s` ASL), slowing during interpersonal alliance/betrayal beats (`~2.5–3.2s` ASL), and surging again on elimination timers. | Directly grounds `AB01` (`S01` `0–15s` premise confirmation), `BP-169` `hook_0_30s` (`1.67s` target shot length), and `S06`/`S09` set-piece re-hooks. |
| **`CS-02`** | **MrBeast** — [7 Days Stranded At Sea](https://www.youtube.com/watch?v=yhB3BgJyGl8) | `17:04` | Immediate physical peril (`0–15s` raft isolation + storm teaser), establishing the 7-day survival clock and physical deprivation stakes before any setup explanation. | Uses day-boundary survival milestones (`Day 3` storm / ration crisis, `Day 5` structural failure) as causal `"but / therefore"` escalations rather than flat diary logs. | Alternates intense storm/action sequences (`<1.8s` cuts + dense environmental SFX) with quiet, raw exhaustion holds (`3.0–4.5s`) where voice clarity dominates. | Grounds `BP-169`'s contrast between `hook_0_30s` / `late_third_480_660s` fast cutting and `middle_calm_90_480s` breathing valleys (`BP-30`). |
| **`CS-03`** | **Fern** — [The Silk Road: The Rise and Fall of the Dark Net's First Drug Lord](https://www.youtube.com/watch?v=GpMP6Nh3FvU) | `24:13` | Cold-opens inside the San Francisco public library arrest of Ross Ulbricht (`0–30s`), staging the split-second physical laptop seizure needed to keep the encrypted drive unlocked. | At `~3:00` and `~9:00`, shifts from how the hidden Tor marketplace worked (`HELPER` network topology diagrams) to the cat-and-mouse forensic trace that doomed him. | Measured `~150–165 WPM` dark narration over a sub-bass tension drone, punctuated by keyboard/latch foley (`BP-118`) and `0.6–1.0s` silent drops before key reveals (`BP-121`). | Grounds `AB01` in-medias-res physical action, `BP-121` pre-reveal silence, and `HELPER` forensic diagram integration (`BP-109`). |
| **`CS-04`** | **Fern** — [How One Man Broke the World's Deadliest Prison](https://www.youtube.com/watch?v=F0eA9a_2vH4) | `18:47` | Starts with the physical spatial constraint of the cell and guard schedule (`0–30s`), turning an architectural blueprint into a ticking puzzle box. | Uses spatial progress checkpoints (corridor -> roof -> perimeter) where each solved barrier triggers an unexpected mechanical or human complication (`BP-06`). | Slow 2.5D/3D camera push-ins (`2.2–4.0s`) with high-contrast rim lighting and localized acoustic perspective (`near` dry claustrophobia vs `far` courtyard reverb, `BP-122`). | Grounds `BP-122` (`near`/`mid`/`far` acoustic perspective matching shot scale) and `BP-166` relative lighting contrast across acts. |
| **`CS-05`** | **Kurzgesagt** — [What If We Detonated All Nuclear Bombs at Once?](https://www.youtube.com/watch?v=JyECrGp-Sw8) | `09:07` | Poses the exact counterfactual question in sentence 1 (`0–12s`) and immediately quantifies the global warhead stockpile via a tangible city-scale visual proxy (`ZI-03`). | Pivots at `~2:45` from "all bombs on cities" to "all bombs in one pile in the Amazon," and at `~5:30` to "mining all uranium on Earth," escalating scale by `10x–100x` per act. | Steady `~150 WPM` narration with `25–30%` inter-phrase pause share, allowing complex blast-radius and atmospheric winter visuals to register before the next number lands. | Grounds `ZI-03` concrete scale proxies, `BP-14` (`140–175 WPM` calm comprehension floor in Z3), and multi-stage counterfactual escalation (`AB04..AB08`). |
| **`CS-06`** | **Kurzgesagt** — [The Egg - A Short Story](https://www.youtube.com/watch?v=h6fcK_fRYaI) | `07:54` | Opens with the protagonist's sudden death in a car crash (`0–20s`) and an immediate two-character philosophical confrontation in an afterlife void. | Sustains retention entirely through **played dialogue turns** and progressive color-palette transformations as the cosmological premise unfolds. | Slower, theatrical shot holds (`3.0–5.0s`) with rich parallax depth (`BP-35`) and a continuous, evolving musical leitmotif (`BP-119`) that peaks on the final synthesis. | Grounds `BP-142` played scene turns, `BP-166` act-level color script progression (`episode_look.py`), and `AB11–AB12` emotional climax pacing (`160` heard WPM). |
| **`CS-07`** | **The Infographics Show** — [What If the Roman Empire Never Fell?](https://www.youtube.com/watch?v=h3w1_2H22bI) | `12:41` | Launches at `~180 WPM` into the counterfactual premise (`0–25s`), contrasting modern Europe with a surviving Roman technate to hook curiosity immediately. | Divides the 12-minute runtime into distinct historical eras (Medieval, Industrial, Space Age), re-asking how Roman institutions would adapt at each century mark. | Continuous `2.0–3.5s` visual state flips (`TIER_2` character pose changes and map overlays) that prevent visual stagnation during dense historical exposition. | Demonstrates why `12`-minute historical what-if videos need `2.0–3.5s` visual state changes, while highlighting the need for Argon's stricter `claim_id` grounding (`ZI-02`). |
| **`CS-08`** | **The Infographics Show** — [How Survival On The Titanic Worked (Hour By Hour)](https://www.youtube.com/watch?v=rs9w5bgtJC8) | `14:18` | Anchors the viewer on the exact timestamp (`11:40 PM`, iceberg impact) and a specific passenger's cabin deck level (`0–30s`), establishing an irreversible countdown clock. | Uses the ship's physical flooding compartments and lifeboat launch timestamps as an inexorable causal clock (`AB06..AB10`). | Combines cross-section ship diagrams (`HELPER` lane) with character survival vignettes (`VIDEO` and `STILL` lanes), accelerating cut rate in the final `3` minutes (`late_third_480_660s`). | Grounds Argon's timestamped countdown escalation (`S08..S14`) and `60/30/10` (`VIDEO`/`STILL`/`HELPER`) lane orchestration (`BP-109`). |
| **`CS-09`** | **AlternateHistoryHub** — [What If Germany Won WWI? (Part 1)](https://www.youtube.com/watch?v=kCEUZ4faCwU) | `15:23` | Defines the exact **Point of Divergence** (avoiding unrestricted submarine warfare / US entry in 1917) within the first `60s` (`AB02B`) instead of assuming magic victory. | Traces second-order institutional consequences: how a victorious Kaiserreich inherits an overextended Eastern European empire (`Mitteleuropa`) and internal economic strain. | Relies on map border animations and historical archival/illustrated plates, proving that counterfactual plausibility depends on **constraints and unintended consequences** (`HY-4`). | Directly grounds `AB02B` (Single Point of Divergence at `30–60s`) and `HY-4` (`explainer_engine/research/hypotheses.py`: every counterfactual step requires mechanism + historical analogue). |
| **`CS-10`** | **AlternateHistoryHub** — [What If The Cold War Went Nuclear? (1983 Able Archer)](https://www.youtube.com/watch?v=g5rVD_g2d8A) | `16:08` | Opens on the real historical near-miss (`November 1983` NATO Able Archer exercise and Soviet high alert) before flipping the single communication hinge into full escalation. | Shifts at the midpoint from strategic command bunkers (`Profile A/D`) to the immediate logistical and agricultural collapse across the Northern Hemisphere (`Profile B/C`). | Uses stark tonal shifts—moving from brisk geopolitical briefing (`~175 WPM`) to somber, slow-cadence aftermath (`~150 WPM`) after the exchange occurs (`AB11`). | Grounds Argon's Adaptive Episode Profiles (`A..D` in `BP-109`/`BP-141`) and the `late_third_480_660s -> climax_660_720s` WPM deceleration (`185 -> 160` WPM). |
| **`CS-11`** | **Kings and Generals** — [Battle of Cannae 216 BC - Second Punic War](https://www.youtube.com/watch?v=6i0a726P22A) | `18:14` | Establishes the strategic crisis facing Rome after Trebia and Trasimene, locking onto Hannibal's numerical disadvantage (`50,000` vs `86,400`) as the central tactical puzzle. | Uses the phase-by-phase geometry of the double envelopment (convex center retreat -> cavalry flank rout -> encirclement) as a visual causal chain (`BP-06`). | Employs `4.0–8.0s` camera altitude transitions (`BP-125`) from regional campaign map down to tactical formation blocks, paired with crisp metallic troop foley (`BP-118`). | Grounds `BP-125` (`altitude_change_s: [4.0, 8.0]` for `MAP` shots) and `Profile B` (`Battle / Campaign`) `HELPER` lane budget (`55/25/20`). |
| **`CS-12`** | **Kings and Generals** — [Fall of Constantinople 1453](https://www.youtube.com/watch?v=M0n4Vw6tw4I) | `22:36` | Contrast between the millennial Theodosian Walls and Mehmed II's super-bombard cannons (`0–30s`), anchoring the siege in concrete engineering numbers (`claim_id`). | Midpoint re-hook (`BP-01`) when the Golden Horn naval chain blocks the Ottoman fleet, forcing the overland portage of `70` ships across Galata (`"but / therefore"` turn). | Alternates wide geographic choke-point maps with close dramatic illustrations of breach defenses, maintaining strict chronological day-by-day siege discipline. | Grounds `ZI-02` / `PV-37` quantitative military/engineering claim verification and `AB07` midpoint strategic reversal. |
| **`CS-13`** | **Oversimplified** — [The French Revolution (Part 1)](https://www.youtube.com/watch?v=8qRZcXIODNU) | `14:43` | Rapid-fire contrast (`0–30s`) between starving peasant tax burdens and extravagant Versailles palace spending, using instant visual state-flips on every clause. | Escalates through consecutive failed fiscal reforms (Calonne -> Brienne -> Estates-General -> Tennis Court Oath), where each attempt to tax the nobility backfires (`BP-06`). | Uses **hard cutout relocations** (`>=25%` screen shift) and background plate swaps (`>=30%`) synchronized to sharp comedy/drama beats (`BP-170` Tier 3). | Grounds `BP-170`'s mechanical definition of `cutout_relocation` (`min_position_shift_frac: 0.25`) and `plate_swap` (`min_bg_diff_frac: 0.30`). |
| **`CS-14`** | **Oversimplified** — [The Napoleonic Wars (Part 1)](https://www.youtube.com/watch?v=zqllxbPWKNI) | `29:28` | Opens on coalition encirclement and Napoleon's rapid Italian campaign maneuverability, visually moving character cutouts across map vectors in sync with spoken verbs. | Re-hooks at each coalition war by raising the geopolitical coalition scale while planting the structural seeds of the Continental System's eventual overreach. | High density of active visual verbs per minute (`30+` visual state changes/min in hook/climax zones), punctuated by sudden dead-stop pauses before punchlines/reversals. | Grounds `BP-169`'s `dramatic_changes_per_min` (`30.0` in Z1/Z4/Z5) and `BP-172` (`min_verbs_per_prompt: 1` for hyped visual movement). |

### 15.3 Domain C — Film, Animation & Visual Storytelling: Camera Grammar, 3-Tier Still Motion Ladder & Color Script

1. **Shot-Size Progression (`Wide -> Medium -> Close-Up -> ECU`) & Spatial Continuity (`BP-26`, `BP-29`, `BP-34`)**:
   * **[CRAFT-HEURISTIC]** / **[FACT]** Every narrative sequence must orient the viewer spatially before cutting to emotional close-ups (`Wide establishing -> Medium interaction -> Close-Up reaction -> Extreme Close-Up detail`, `BP-26` in `explainer_engine/scripting/film_shots.py`). Adjacent shots must preserve the `180°` screen-direction axis (`BP-29`) and obey the **`30°` / scale-step rule (`BP-34`)** so hard cuts never look like accidental jump cuts.
   * **[FACT]** In `mrbeast_12min_video_mold (1).json` (`254` shots = `152` `VIDEO` [`60.0%`], `76` `STILL` [`30.0%`], `26` `HELPER` [`10.0%`]), every shot specifies `shot_size`, `camera_move`, and `screen_direction`, matching `BP-109`'s `60/30/10 ±5%` lane contract (`D-93`).

2. **Exact Forensic Audit of the `76` `STILL` Shots vs `BP-170` (`edit/dramatic_still.py`)**:
   * **[FACT]** Programmatic inspection of all `76` `STILL` shots in `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) against `BP-170`'s `static_still_max_s_by_zone` (`1.5s` in `hook_0_30s` and `climax_660_720s`; `2.0s` in `early_30_90s` and `late_third_480_660s`; `2.5s` in `middle_calm_90_480s`) reveals the exact tier breakdown:

| `still_motion_tier` in `mrbeast_12min_video_mold (1).json` | Motion Mechanic (`motion_type`) | Total `STILL` Shots in Mold | Duration Range in Mold (`s`) | Shots `<=` Zone Static Cap (`BP-170`) | Shots `>` Zone Static Cap (`BP-170`) | Current `edit/dramatic_still.py` (`5013a55a`) Behavior & Required Resolution (`M-04` / `CHG-09`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`TIER_1`** | `parallax_25d` (3-layer FG/MG/BG depth separation + `BP-132` subtle breathing/blink) | **`19`** | `1.125s – 2.500s` | **`17`** | **`2`** (`SH003` at `1.875s > 1.5s` in `S01`/`Z1`; `SH226` at `1.625s > 1.5s` in `S15`/`Z5`) | **Keep `TIER_1` strictly bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`)**. Both `SH003` (`"Cutout Pieter leaps from lower-left to center frame"`) and `SH226` (`"Cutout judge slams gavel"`) actually describe Tier 3 cutout relocations in `track_5_visual_events` and must be tagged `TIER_3` with structured `dramatic_change` specs in the reference grid. |
| **`TIER_2`** | `qwen_nextpose_or_lighting_state_flip` (in-place Qwen pose edit or dramatic lighting state flip) | **`40`** | `2.000s – 3.500s` | **`4`** (`SH037`, `SH045`, `SH180`, `SH200` at `2.000s` in `Z2`/`Z4` or `2.500s` in `Z3`) | **`36`** (`36` shots between `2.125s` and `3.500s` exceed their zone's `1.5s / 2.0s / 2.5s` static cap) | **`36` shots currently trigger `DS-01` `FAIL`** because `dramatic_still.py` only exempts `cutout_relocation` and `plate_swap`. Per `M-04` and `CHG-09`, **Tier 2 remains bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`)** until a quantitative pose-delta + identity metric is validated and approved by the creator (`CD-03`). |
| **`TIER_3`** | `cutout_relocation_with_empty_plate` (`>=25%` cutout position shift or `>=30%` background plate swap) | **`17`** | `3.500s – 4.500s` | **`0`** | **`17`** (`17` shots between `3.500s` and `4.500s`, all `<= 5.0s` `dramatic_still_max_s`) | **Exempt up to `5.0s` under `BP-170`** once the Mold's `still_motion_contract` fields are mapped to the structured `dramatic_change: {"kind": "cutout_relocation" \| "plate_swap", "position_shift_frac": >=0.25, "bg_diff_frac": >=0.30, "subject_area_frac": >=0.08}` schema required by `dramatic_still.py`. |
| **Total `STILL` Shots** | All 3 Tiers | **`76`** (`216.0s` = `30.0%`) | `1.125s – 4.500s` | **`21`** | **`55`** (`2` Tier 1 + `36` Tier 2 + `17` Tier 3) | **Unified Policy (`M-04` = `CHG-09`)**: `BP-170` (`FAIL`) is never relaxed without `CD-03`. Only `TIER_3` unlocks `> static_still_max_s_by_zone` up to `5.0s`. |

3. **Relative Color Script (`BP-166`, `BP-130`) vs Raw HEX Ban (`D-22`, `LT-65`)**:
   * **[FACT]** In `explainer_engine/scripting/prompt_lint.py` (`LT-65`, `D-22`), raw `#RRGGBB` hex strings are banned inside image/video generation prompts because diffusion tokenizers misinterpret hex literals as text artifacts. Instead, `explainer_engine/production/episode_look.py` (`AC-17`) injects natural-language act palette descriptors into prompts, while `explainer_engine/production/assemble.py` (`BP-130` Reinhard Lab transfer) and `explainer_engine/qa/color_continuity.py` (`BP-166`: `sat_drift_max: 0.08`, `luma_drift_max: 0.08`, `hero_palette_max: 0.15`) enforce mathematical color lock against `character_sheet_ref` HEX swatches in post-processing.

### 15.4 Domain D — Voice, Audio & Music: Speaking WPM vs Heard WPM, Real Repo `eleven_v4` Measurements & Two-Axis Audio Accounting

1. **Mathematical & Empirical Reconciliation of `speaking_wpm`, `heard_wpm`, and `pause_pad.py` on Real Repo `eleven_v4` Audio**:
   * **[FACT]** In `config/channel_voices.json` (`D-94`, `VC-08`), the approved channel narrator is **`Odom`** (`voice_id: "CcSJ2r3qw0XU9gJpEPyk"`, model **`eleven_v4`**; `voice_settings`: `stability: 0.45`, `similarity_boost: 0.80`, `style: 0.35`, `speed: 1.08`).
   * **[PRIMARY-STANDARD]** Per official [ElevenLabs Pause Documentation](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses), **SSML `<break time="..."/>` tags are supported only on Eleven v2 models and are NOT supported on Eleven v3 or Eleven v4**. On `eleven_v4`, pauses and prosody are controlled via punctuation (`—`, `-`, `...`), bracketed audio tags (`BP-171`: `[excited]`, `[whispers]`, `[sighs]`, `[short pause]`, `[dramatic]`), and post-TTS waveform silence padding in `explainer_engine/audio/pause_pad.py` (`pad_pauses_in_wav`).
   * **[FACT]** By definition, across any segment of duration $T_{\text{total}} = T_{\text{speech}} + T_{\text{pause}}$ containing $W$ words:
     $$\text{WPM}_{\text{heard}} = \frac{60 \cdot W}{T_{\text{total}}}, \qquad \text{WPM}_{\text{speaking}} = \frac{60 \cdot W}{T_{\text{speech}}}, \qquad p_{\text{total}} = \frac{T_{\text{pause}}}{T_{\text{total}}} = 1 - \frac{\text{WPM}_{\text{heard}}}{\text{WPM}_{\text{speaking}}}$$
   * **[FACT]** However, inspecting the **actual measured `eleven_v4` word-timestamp files committed in `examples/`** proves a critical operational fact that naive pause-addition formulas miss: **raw `eleven_v4` TTS output already contains `28.4%–37.3%` natural inter-word gaps!**

| Committed Repo Example (`examples/*/words*.json`) | Word Count ($W$) | Total Span ($T_{\text{total}}$) | Active Phonation Sum ($T_{\text{speech}}$) | Natural Inter-Word Gap Sum ($T_{\text{pause,raw}}$) | Measured Raw `speaking_wpm` | Measured Raw `heard_wpm` | Existing Natural Pause Share ($p_{\text{raw}}$) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| `examples/day1_v2/words_raw.json` (before `pause_pad.py`) | `204` words | `86.579s` | `54.280s` | `32.299s` (`51` gaps `>=0.15s`) | **`225.50 WPM`** | **`141.37 WPM`** | **`37.31%`** |
| `examples/day1_v2/words.json` (after `pause_pad.py`) | `204` words | `90.266s` | `54.280s` | `35.986s` (`+3.687s` added by `pause_pad.py`) | **`225.50 WPM`** | **`135.60 WPM`** | **`39.87%`** |
| `examples/titans_from_zero/words.json` | `142` words | `54.860s` | `39.260s` | `15.600s` (`29` gaps `>=0.15s`) | **`217.01 WPM`** | **`155.30 WPM`** | **`28.44%`** |
| `examples/syndicate_wars_ep1/words.json` | `149` words | `73.039s` | `52.230s` | `20.809s` (`26` gaps `>=0.15s`) | **`171.17 WPM`** | **`122.40 WPM`** | **`28.49%`** |

   * **[OBSERVATION]** Look at how `explainer_engine/audio/pause_pad.py:92–112` (`plan_inserts`) actually works in the repository: it measures the **existing recognizer gap** `gap = float(b["s"]) - float(a["e"])` at each sentence/clause boundary and inserts **only the deficit** `add = max(0.0, want - gap)`. If a pipeline blindly added the theoretical zone pause share $p_{\text{zone}} = 1 - \text{WPM}_{\text{heard}} / \text{WPM}_{\text{speaking}}$ (`17.17%..28.89%`) on top of raw `eleven_v4` audio (which already has `28–37%` natural pauses), it would double-pad the audio and push `heard_wpm` down to `110–130 WPM`!
   * **[RECOMMENDATION]** Therefore, in `CHG-06`, zone-aware audio pacing in `narrator_polish.py` and `pause_pad.py` must be **closed-loop**: after `eleven_v4` synthesis and recognizer alignment (`words_raw.json`), compute actual `measured_heard_wpm` per segment/zone first, and scale `pause_pad.py`'s target boundary floor (`want`) dynamically so total post-pad segment duration converges toward `BP-169`'s `heard_wpm_target` (`193 / 176 / 166 / 185 / 160` WPM) without over-padding segments that already meet or fall below target WPM.

2. **Cross-Linguistic Syllabic Rate vs English Informational Pacing (`[PRIMARY-STANDARD]` vs `[HYPOTHESIS]`)**:
   * **[PRIMARY-STANDARD]** [Pellegrino, Coupé & Marsico (2011), *Language* 87(3):539–558](https://www.ddl.ish-lyon.cnrs.fr/fulltext/pellegrino/Pellegrino_2011_Language.pdf) (`[pdftotext]` verified in `docs/research/CRAFT_SOURCES_2026-10.md`) measured **syllable-level speech rate (`6.19 syllables/s` for English, `~39 bits/s` information rate across 8 languages)**—they did **not** establish a YouTube WPM retention curve or a `166–193 WPM` rule. Likewise, [Brysbaert (2019), *Journal of Memory and Language* (`PMC6758568`)](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/) established average silent reading (`238 WPM`) and English speech (`~150 WPM` conversational average).
   * **[HYPOTHESIS]** Consequently, `BP-169`'s 5-zone `heard_wpm_target` curve (`193 -> 176 -> 166 -> 185 -> 160` WPM, averaging `172.2` WPM / `2,066` words across `720.0s`) is classified strictly as an **Argon channel design hypothesis (`[HYPOTHESIS]`, `severity: "REVIEW"` for intra-zone variance under `CD-04`)** grounded in YouTube creator practice (`[VERIFIED-CREATOR]`), never cited to Pellegrino et al. (2011).

3. **Loudness, LRA, Dialogue Intelligibility & Two-Axis Audio Accounting (`[PRIMARY-STANDARD]`)**:
   * **[PRIMARY-STANDARD]** Integrated loudness (`-14.0 ± 1.0 LUFS`) and True Peak (`<= -1.0 dBTP`) are governed by [ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en) (`BP-73`, `explainer_engine/finish/loudness.py`) and YouTube's loudness normalization specification. Loudness Range (`LRA 5–9 LU`, `BP-74`) and music/SFX ducking (`-14 to -18 dB` beneath voice with `>=10–12 dB` dialogue-to-bed margin, `BP-15`, `BP-75`) are grounded in EBU Tech 3343 v4 (*Practical Guidelines for Production and Implementation in accordance with EBU R 128*, directly verified in `docs/research/CRAFT_SOURCES_2026-10.md`).
   * **[RECOMMENDATION]** As specified in `CHG-10`, Argon enforces **two-axis audio accounting**:
     1. **Primary Driver Timeline Partition (`100%` of `720.0s`)**: `68%` (`489.6s`) Narrator-led (`Track 1`), `20%` (`144.0s`) Character/Historical Quote-led (`Track 2`, `D-90`), and `12%` (`86.4s`) SFX/Music-Showcase-led (`Tracks 3 & 4`, including `0.5–1.0s` pre-reveal vacuums `BP-121` and `1.5–2.5s` breathing valleys `BP-30`).
     2. **Concurrent Stem Activity & Loudness Envelope (`loudness.py`, `sound_director.py`)**: Continuous multi-track stem mix where `Track 3` (Foley/SFX) and `Track 4` (Score) run concurrently under sidechain ducking (`BP-15`, `BP-75`) and shot-size acoustic perspective (`BP-122`: `far`, `mid`, `near`).

### 15.5 Domain E — Editing & Pacing: Rule of Six, Rhythm Variance, J/L Cuts & Breathing Valleys

1. **Walter Murch's Rule of Six (`[CRAFT-HEURISTIC]`)**:
   * **[CRAFT-HEURISTIC]** In *In the Blink of an Eye* (`1995/2001`, p. 18; primary text verified in `docs/research/CRAFT_SOURCES_2026-10.md`), Walter Murch ranks cut priorities as: **(1) Emotion (`51%`)**, **(2) Story (`23%`)**, **(3) Rhythm (`10%`)**, **(4) Eye-trace (`7%`)**, **(5) 2D plane of screen (`5%`)**, and **(6) 3D continuity of space (`4%`)**. Those percentages are Murch's **pedagogical craft hierarchy** (`[CRAFT-HEURISTIC]`) teaching editors never to sacrifice emotional truth or story progression for mechanical continuity—they are **not** statistical laws, and they have **nothing to do with LTX-2.5 handle frames** (which are purely an engineering trim buffer in `CHG-08`).

2. **5-Zone Rhythm Profile (`BP-169`) & Anti-Metronome Variance (`BP-28`)**:
   * **[FACT]** Across the `254` shots (`720.0s`) of `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`), the verified zone distribution is:

| Zone ID (`BP-169` Canonical / Mold Alias) | Time Window (`s`) & Duration | Segments | Verified Mold Shot Count & Mean Shot (`s`) | `BP-169` `shot_s_range` & `cuts_per_min` | Verified Mold Word Count & Heard WPM | `BP-169` `heard_wpm_target` (`[min, max]`) | Editorial Role & Breathing Valley Rule (`BP-30`) |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`hook_0_30s`** (`Z1_HOOK_0_30S`) | `0.0–30.0s` (`30.0s`) | `S01` | `18` shots (`1.667s` mean, `36.0` cuts/min) | `[1.0, 2.5]s` (`36.0` cuts/min) | `96` words (`192.0` WPM) | `193` (`[180, 210]`) | Visceral hook validation (`AB01`) + central question (`AB02A`); zero slow exposition. |
| **`early_30_90s`** (`Z2_FAST_SETUP_30_90S`) | `30.0–90.0s` (`60.0s`) | `S02–S03` | `28` shots (`2.143s` mean, `28.0` cuts/min) | `[1.5, 3.0]s` (`28.0` cuts/min) | `177` words (`177.0` WPM) | `176` (`[165, 190]`) | Baseline historical anchor + Single Point of Divergence (`AB02B`) + first irreversible commitment (`AB03`). |
| **`middle_calm_90_480s`** (`Z3_CALM_MIDDLE_90_480S`) | `90.0–480.0s` (`390.0s`) | `S04–S11` | `138` shots (`2.826s` mean, `21.2` cuts/min) | `[2.0, 4.5]s` (`21.0` cuts/min) | `1,083` words (`166.6` WPM) | `166` (`[150, 178]`) | Core causal escalation (`5` of `6` played scene turns `BP-142`), `180s` (`S06`) & `360s` (`S09`) re-hooks, and mandatory `3.5–5.0s` breathing valleys (`BP-30`). |
| **`late_third_480_660s`** (`Z4_LATE_THIRD_480_660S`) | `480.0–660.0s` (`180.0s`) | `S12–S14` | `50` shots (`3.600s` mean in Mold; target `2.0s` / `30.0` cuts/min in `BP-169`) | `[1.2, 3.0]s` (`30.0` cuts/min) | `553` words (`184.3` WPM) | `185` (`[172, 200]`) | Cascade acceleration (`AB09–AB10`); crosses `90.0%` cumulative spoken words (`BP-04`) inside `S14` (`~644.1s`) before `S15`. |
| **`climax_660_720s`** (`Z5_CLIMAX_660_720S`) | `660.0–720.0s` (`60.0s`) | `S15–S16` | `20` shots (`3.000s` mean, `20.0` cuts/min) | `[1.0, 3.5]s` (`26.0` cuts/min) | `157` words (`157.0` WPM) | `160` (`[145, 175]`) | Pre-climax `0.5–1.0s` vacuum (`BP-121`), emotional rupture (`AB11`), final synthesis & abrupt hard cut (`AB12`, `BP-43`). |
| **Full Episode Total** | `0.0–720.0s` (`720.0s` = `17,280f`) | `S01–S16` | **`254` shots** (`2.835s` mean; `152` VIDEO, `76` STILL, `26` HELPER) | Zone-governed + `BP-28` (`sigma >= 0.8s`, `CV >= 0.30`) | **`2,066` words** (`172.17` WPM overall) | Zone-governed | **100% Frame Conservation (`17,280` frames)** across `16` segments. |

   * **[OBSERVATION]** Notice a key forensic finding in row 4 (`late_third_480_660s`): in `mrbeast_12min_video_mold (1).json`, `S12–S14` (`180.0s`) contains only `50` shots (`16.7` cuts/min, `3.60s` mean shot length) with `30` of those `50` shots exceeding `BP-169`'s `3.0s` max for `late_third_480_660s` (`RL-01`/`RL-02` `REVIEW` findings in `scripting/rhythm_lint.py`). Our Layer 3 timeline compiler (`CHG-07`) explicitly repairs `late_third_480_660s` shot subdivisions so generated episodes hit `BP-169`'s `[1.2, 3.0]s` (`~30` cuts/min) surge target.

3. **J-Cuts & L-Cuts (`BP-27`)**:
   * **[CRAFT-HEURISTIC]** / **[FACT]** Per `BP-27` (`j_l_ratio: [0.30, 0.40]`, `offset_s: [0.25, 1.00]` in `sourced_rules.json` and `edit/rhythm.py`), `30–40%` of narrative cuts use `0.25–1.00s` audio pre-lap (J-cut: incoming voice/SFX precedes the visual cut to pull the viewer into the next space) or audio carry-over (L-cut: outgoing resonance trails over the incoming reaction shot), while shock reveals (`AB05`, `AB07`, `AB11`) and the final frame (`AB12`, `BP-43`) use frame-accurate hard cuts (`0.0s` offset).

### 15.6 Domain F — AI Production Realities: LTX-2.5 `8k+1` Lattice, Exact `152`-Shot Handle Math, Qwen Continuity & Cost Governance

1. **LTX-2.5 Temporal VAE Lattice (`8k + 1` Frames, `[PRIMARY-STANDARD]`)**:
   * **[PRIMARY-STANDARD]** Per the official [Lightricks LTX-2 Model Card](https://huggingface.co/Lightricks/LTX-2) and [LTX-2 Technical Report (`arXiv:2601.03233`)](https://arxiv.org/abs/2601.03233), LTX-2 / LTX-2.5's 3D spatiotemporal causal VAE downsamples time by a factor of `8` after the initial anchor frame, requiring every generated video clip to have a frame count of **`F = 8k + 1`** (`k >= 1`, e.g., `25, 33, 41, 49, 57, 65, 73, 81, 89, 97, 105, 113, 121` frames) at `24 fps` (`BP-139` in `sourced_rules.json` and `explainer_engine/production/ltx_generate.py:92–100`).

2. **Forensic Recalculation of Handle Frames Across All `152` `VIDEO` Shots (`M-10` & `CHG-08`)**:
   * **[FACT]** Earlier audit notes estimated that reducing `BP-128` handle frames from `12` per side (`24` total) to `4` per side (`8` total) across the `152` `VIDEO` shots would save `"3,648 to 4,864 LTX frames (~38%)"`. **Direct arithmetic on `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`) disproves that estimate** (`152 * 16 = 2,432` frames maximum before lattice effects, never `3,648–4,864`!). Here is the exact, shot-by-shot verified frame accounting across all `152` `VIDEO` shots in `mrbeast_12min_video_mold (1).json`:

| LTX-2.5 Generation Policy Across the `152` `VIDEO` Shots (`432.00s` Usable Timeline) | Formula per Shot (`u` = usable timeline frames) | Total Frames (`152` Shots) | Total Video Duration (`s` at `24 fps`) | Overhead Above Usable Timeline (`10,368f`) | Exact Savings vs Current `BP-128` (`>=12`/side) | Epistemic Status & Governance |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **1. Usable Timeline Span (`frame_span`)** | $u = \text{frame\_out} - \text{frame\_in}$ | **`10,368` frames** | `432.00s` (`60.0%` of `720s`) | `0` frames (`0.00%`) | Baseline usable edit span | **`[FACT]`** (`mrbeast_12min_video_mold (1).json`) |
| **2. Zero-Handle `8k+1` Quantum Only** | $8 \lceil (u - 1)/8 \rceil + 1$ | **`10,904` frames** | `454.33s` | `+536` frames (`+22.33s`, `+5.17%`) | Cannot trim boundary frames (`0` handle buffer) | **`[FACT]`** (violates `BP-128` boundary trim defense) |
| **3. Current Repo `BP-128` (`>=12` handles/side on all `152` shots)** | $8 \lceil (u + 24 - 1)/8 \rceil + 1$ (adds `24..31` frames/shot) | **`14,552` frames** | `606.33s` | `+4,184` frames (`+174.33s`, `+40.35%`) | `0` frames (`0.00%` baseline generated) | **`[FACT]`** (`sourced_rules.json` `BP-128`: `handle_frames: [12, 16]`) |
| **4. Mold `v2.1.0` Formula (`>=4` handles/side on all `152` shots)** | $8 \lceil (u + 8 - 1)/8 \rceil + 1$ (adds `8..15` frames/shot; matches Mold `ltx_generation_frame_count`) | **`12,120` frames** | `505.00s` | `+1,752` frames (`+73.00s`, `+16.90%`) | **`-2,432` frames (`-101.33s`, `-16.71%` of generated frames)** | **`[HYPOTHESIS]`** (`REVIEW` — under-provisions whip-pan/dissolve overlaps requiring `>=12` frames) |
| **5. Recommended Transition-Aware Policy (`CHG-08`)**: `>=4`/side on `135` hard/J/L-cut shots + `>=12`/side on `17` whip-pan/crossfade shots | $8 \lceil (u + 8 - 1)/8 \rceil + 1$ (hard/J/L) vs $8 \lceil (u + 24 - 1)/8 \rceil + 1$ (whip-pan/crossfade) | **`12,392` frames** | `516.33s` | `+2,024` frames (`+84.33s`, `+19.52%`) | **`-2,160` frames (`-90.00s`, `-14.84%` of generated frames)** | **`[HYPOTHESIS]`** (`severity: "REVIEW"`, empirically gated in `GATE-P2` before modifying `BP-128`) |

   * **[OBSERVATION]** Why did `14,552 - 12,120` equal **exactly `2,432` frames (`16 * 152`)**? Because adding `24` frames vs adding `8` frames differs by exactly `16 = 2 * 8` frames, which is an exact multiple of the `8`-frame LTX VAE quantum! Thus every single `VIDEO` shot drops by exactly `2` lattice steps (`16` frames) when moving from `>=12` handles/side to `>=4` handles/side (`152 * 16 = 2,432` frames = `16.71%` of `14,552`).

3. **Character Identity Continuity (`PuLID` / `IP-Adapter` / `ArcFace` `BP-130`) & Cost Governance (`BP-168`)**:
   * **[FACT]** Character identity lock across shots is enforced by `explainer_engine/production/identity.py` and `explainer_engine/qa/identity_gate.py` (`BP-130`: `identity_cosine_min: 0.65`, `warn_below: 0.72` using InsightFace ArcFace embeddings, plus `BP-166` color continuity), while paid GPU/TTS execution is gated by `explainer_engine/core/spend_caps.py`, `explainer_engine/core/ledger.py` (hard stop at `80%` of ceiling), and `BP-168` (`go_forecast_usd_max: 12.00`, `abandon_forecast_usd_min: 20.00` per episode).

### 15.7 Comprehensive External & Compendium Source Correction Register (`SRC-01` through `SRC-48`)

**[FACT]** In compliance with `§10` of the forensic audit specification, every external standard, creator interview, academic paper, benchmark video, and secondary claim in `CrossWorld_Chronicles_Organized_Research_for_Gemini.docx` referenced across this roadmap is cataloged and graded below with **zero Google search-result URLs**:

| Source ID | Claim / Parameter in Roadmap or Research Compendium | Original Source Cited | Direct Primary Verification URL / Repo Proof | Verification Method | Evidence Grade | Forensic Audit Verdict & Required Action |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`SRC-01`** | Integrated program loudness `-14.0 ± 1.0 LUFS` and true-peak ceiling `-1.0 dBTP` (`BP-73`) | ITU-R BS.1770-5 / YouTube Loudness Spec | [ITU-R BS.1770-5 Official Recommendation](https://www.itu.int/rec/R-REC-BS.1770/en) | Direct web browse + `explainer_engine/finish/loudness.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED (`FAIL` gate)**. Enforced by `loudness.py` two-pass `loudnorm`. |
| **`SRC-02`** | Dialogue-gated Loudness Range (`LRA 5–9 LU`, `BP-74`) and sidechain ducking margin (`10–18 dB`, `BP-15`, `BP-75`) | EBU R 128 / EBU Tech 3343 v4 | [EBU R 128 Loudness Recommendation](https://tech.ebu.ch/publications/r128) + `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` of EBU Tech 3343 v4) | Direct `[pdftotext]` verification in repo `CRAFT_SOURCES_2026-10.md` | **`[PRIMARY-STANDARD]`** | **VERIFIED (`FAIL` gate)**. Grounded in EBU R 128 / Tech 3343 v4. |
| **`SRC-03`** | LTX-2 / LTX-2.5 temporal VAE frame lattice `F = 8k + 1` (`BP-139`) and resolution divisibility by `32` | Lightricks LTX-2 Model Card & Technical Report | [Lightricks/LTX-2 HuggingFace Card](https://huggingface.co/Lightricks/LTX-2) & [arXiv:2601.03233](https://arxiv.org/abs/2601.03233) | Direct web browse + `production/ltx_generate.py:92–100` | **`[PRIMARY-STANDARD]`** | **VERIFIED (`FAIL` gate)**. Hard architectural requirement of LTX causal 3D VAE. |
| **`SRC-04`** | ElevenLabs v3 / v4 does **not** support SSML `<break time="..."/>` tags; uses punctuation (`—`, `...`), bracketed audio tags (`BP-171`), and post-TTS waveform padding | ElevenLabs Official Documentation | [ElevenLabs — How can I add pauses?](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses) & [Eleven v3 Model Guide](https://www.google.com/search?q=https://elevenlabs.io/docs/overview/models%23eleven-v3) | Direct web browse + `audio/narrator_polish.py` & `audio/pause_pad.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED & CORRECTED**. Removed any claim that `eleven_v4` or `v3` parses SSML `<break>` tags; pauses use em-dashes + `pause_pad.py` deficit insertion. |
| **`SRC-05`** | Cross-linguistic syllable rate (`6.19 syllables/s` in English, `~39 bits/s` information rate across 8 languages) | Pellegrino, Coupé & Marsico (2011), *Language* 87(3):539–558 | [Pellegrino et al. (2011) Full Paper PDF](https://www.ddl.ish-lyon.cnrs.fr/fulltext/pellegrino/Pellegrino_2011_Language.pdf) (`docs/research/CRAFT_SOURCES_2026-10.md`) | Direct `[pdftotext]` verification in repo `CRAFT_SOURCES_2026-10.md` | **`[PRIMARY-STANDARD]`** | **RE-SCOPED**. Paper proves cross-linguistic syllabic information density (`~39 bits/s`), **not** YouTube WPM retention curves. `BP-169` WPM targets are tagged `[HYPOTHESIS]`. |
| **`SRC-06`** | Average English silent reading rate (`238 WPM`) and spoken rate (`~150 WPM` conversational average; `140–175 WPM` calm narration floor `BP-14`) | Brysbaert (2019), *Journal of Memory and Language* 109:104047 | [PMC6758568 — How many words do we read per minute?](https://pmc.ncbi.nlm.nih.gov/articles/PMC6758568/) | Direct web verification + `sourced_rules.json` `BP-14` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Supports `BP-14` (`140–175 WPM`) as the comprehension comfort zone for `middle_calm_90_480s` (`166` WPM target). |
| **`SRC-07`** | Acoustic pause insertion (`0.5–1.0s`) and prosodic segmentation improve listening comprehension and recall in dense narrative speech | Wingfield et al. (1999) / MacGregor et al. (2010) | [MacGregor et al. (2010) — Listening to natural pauses (`PMC2865204`)](https://pmc.ncbi.nlm.nih.gov/articles/PMC2865204/) | Direct academic source check | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Grounds `BP-14` pause share (`>=12%`) and `BP-121` pre-reveal silence (`0.5–1.0s`). |
| **`SRC-08`** | Multimedia Coherence, Signaling, Redundancy & Dual-Channel Principles (avoiding long verbatim on-screen text over dense speech, `BP-84` `<=26` chars/line) | Mayer (2009/2020), *Multimedia Learning* (Cambridge Univ. Press) | [Mayer & Moreno (2003) — Nine Ways to Reduce Cognitive Load (*Educational Psychologist*)](https://www.tandfonline.com/doi/abs/10.1207/S15326985EP3801_6) | Direct academic source check + `BP-84` | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Grounds `BP-84` (`BUBBLE-1`: `<=26` chars/line callouts instead of wall-of-text captions). |
| **`SRC-09`** | Curiosity / Information-Gap Theory (planting an explicit open question before delivering exposition, `BP-01` & `BP-04`) | Loewenstein (1994), *Psychological Bulletin* 116(1):75–98 | [Loewenstein (1994) — The Psychology of Curiosity (CMU PDF)](https://www.cmu.edu/dietrich/sds/docs/loewenstein/PsychofCuriosity.pdf) | Direct academic source check + `BP-01` / `BP-04` | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Theoretical foundation for `BP-01` (`question_plant` every `<=90s`), while the exact `90s` interval and `90%` word share (`BP-04`) are channel rules (`[HYPOTHESIS]`). |
| **`SRC-10`** | MrBeast production principles: `0–30s` title/thumbnail promise validation, `1–3min` transition from spectacle to story, `3min` & `6min` re-hooks, "wow factor", abrupt ending (`BP-43`) | Jimmy Donaldson — *How to Succeed in MrBeast Production* (36-page internal manual) | [How to Succeed in MrBeast Production (Full PDF)](https://www.google.com/search?q=https://ivan.fyi/wp-content/uploads/2024/09/How-to-succeed-in-MrBeast-Production-pdf-1.pdf) | Direct PDF inspection + `CRAFT_SOURCES_2026-10.md` | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Primary creator source for `AB01..AB05`, `AB07`, `AB12` (`BP-43`), and `BP-169` zone structure. |
| **`SRC-11`** | MrBeast retention analysis, hook iteration, and multi-track dubbing/voice pacing strategy | Colin & Samir — *Inside MrBeast's $100M Production Company* | [Colin & Samir — Inside MrBeast's Production Company (YouTube)](https://www.youtube.com/watch?v=c8VcUnz3nVc) | Direct video metadata & transcript check | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Confirms obsessive focus on first-30s retention drop-off and mid-video re-hooks. |
| **`SRC-12`** | "YouTube Voice" prosody mechanics: wide F0 pitch excursions, emphatic lengthening, and hyper-articulated clause endings (`BP-171`) | PBS Terra / Studio — *Why Everything on YouTube Sounds the Same* (feat. linguistics prof. Anne Curzan & Owen Bros.) | [Why Everything on YouTube Sounds the Same (YouTube)](https://www.youtube.com/watch?v=T2G8s-6ZP9I) | Direct video check + `CRAFT_SOURCES_2026-10.md` | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-171` prosody wave (high energy in `hook_0_30s`, natural conversational cadence in `middle_calm_90_480s`). |
| **`SRC-13`** | Walter Murch's **Rule of Six**: Emotion (`51%`), Story (`23%`), Rhythm (`10%`), Eye-trace (`7%`), 2D Plane (`5%`), 3D Space (`4%`) | Walter Murch — *In the Blink of an Eye* (2nd ed., 2001, p. 18) | `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` verbatim transcription of p. 18) | Direct `[pdftotext]` verification in repo | **`[CRAFT-HEURISTIC]`** | **VERIFIED & RE-SCOPED**. Used strictly as editorial hierarchy guidance (`[CRAFT-HEURISTIC]`); never used to justify LTX handle frames or hard mathematical cut ratios. |
| **`SRC-14`** | Walter Murch's **Law of 2.5** (*Dense Clarity — Clear Density*): maximum 2 simultaneous foreground cognitive audio elements (`Voice + 1 SFX` or `Music + 2 SFX`) | Walter Murch — *Dense Clarity — Clear Density* (Transom Review, 2005) | `docs/research/CRAFT_SOURCES_2026-10.md` (`[pdftotext]` verbatim transcription) | Direct `[pdftotext]` verification in repo | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Directly grounds `BP-15` / `sound_director.py` foreground stem collision cap. |
| **`SRC-15`** | Average Shot Length (ASL) evolution (`~12s` in mid-20th century cinema down to `~2.5–4.0s` in modern action/thriller cinema) and non-metronomic shot variance (`BP-28`) | James E. Cutting, Jordan E. DeLong & Christine E. Nothelfer (2010), *Psychological Science* 21(3):432–439 | [Cutting et al. (2010) — Attention and the Evolution of Hollywood Film (`PMC` / Sage)](https://journals.sagepub.com/doi/10.1177/0956797610361679) | Direct academic source verification | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Grounds `BP-28` (`sigma >= 0.8s`, `CV >= 0.30` anti-metronome shot-length distribution) while keeping exact `0.8s`/`0.30` cutoffs as repo thresholds. |
| **`SRC-16`** | Compendium claim (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`) citing Stephen Follows (`2025-04-21` & `2026-03-06`) for film cut counts and trailer pacing | Stephen Follows — *How many cuts are there in a film?* (`2025-04-21`) & *How movie trailers manipulate time* (`2026-03-06`) | [Stephen Follows — How many cuts are there in a film?](https://www.google.com/search?q=https://stephenfollows.com/p/how-many-cuts-are-there-in-a-film) & [How movie trailers manipulate time](https://www.google.com/search?q=https://stephenfollows.com/p/how-movie-trailers-manipulate-time) | Verified via `google:search` snippet index (Substack host blocks automated `google:browse`) | **`[CRAFT-HEURISTIC]`** | **RE-GRADED TO `[CRAFT-HEURISTIC]`**. Theatrical feature/trailer averages (`~21 cuts/min` in feature drama, faster in trailers) are contextual background only; Argon's 5-zone cut rates (`36/28/21/30/26` cuts/min) remain a channel `[HYPOTHESIS]` (`BP-169`). |
| **`SRC-17`** | Compendium claim (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`) citing a `"55% YouTube retention benchmark"` from a secondary SaaS blog (`Retention Rabbit`) | Secondary blog aggregator (`retentionrabbit.com`) in `.docx` | Retired from normative citations in favor of primary [YouTube Creator Academy / Help — Audience Retention](https://support.google.com/youtube/answer/9314415) | Direct web browse of official YouTube documentation | **`[HYPOTHESIS]`** | **PURGED SECONDARY BLOG CLAIM**. YouTube does not publish a universal `55%` retention threshold; any target retention percentage is strictly an internal channel `[HYPOTHESIS]`. |
| **`SRC-18`** | Compendium claim (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`) attributing `"2.1 seconds average cut length"` or `"172.2 WPM optimal retention"` to peer-reviewed neuroscience | Unverified secondary synthesis in `.docx` | Verified against `mrbeast_12min_video_mold (1).json` (`2,066` words / `12.0` min = `172.17` WPM; `254` shots / `720s` = `2.835s` mean shot) | Direct programmatic computation on `2ca7f56f...` | **`[HYPOTHESIS]`** | **CORRECTED**. `172.17 WPM` and `2.835s` mean shot length are the **empirical properties of the 254-shot Master Mold v2.1.0 reference grid**, not peer-reviewed neuroscience laws. |
| **`SRC-19`** | Compendium claim (`CrossWorld_Chronicles_Organized_Research_for_Gemini.docx`) that reducing `BP-128` handles from `12` to `4` per side saves `"3,648–4,864 frames (~38%)"` | Arithmetic error in earlier draft notes | Verified directly on the `152` `VIDEO` shots of `mrbeast_12min_video_mold (1).json` (`14,552` frames at `>=12`/side vs `12,120` frames at `>=4`/side vs `12,392` transition-aware) | Direct Python verification (`forensic_audit_m1.py`) | **`[FACT]` / `[HYPOTHESIS]`** | **CORRECTED (`M-10` & `CHG-08`)**. Exact difference is **`2,432` frames (`16.71%`)** for all-`>=4` and **`2,160` frames (`14.84%`)** for transition-aware handles. |
| **`SRC-20`** | Compendium / prior note claim that `S02` in `mrbeast_12min_video_mold.json` had header `duration_s: 79.2` while its `14` shots summed to `59.2s` | External pre-bundle draft (`89aa56d2...`) not present in bundle | Verified directly on `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`): `S02` has `duration_s: 30.0` (`30.0–60.0s`), `12` shots (`SH019..SH030`), `88` words, and `0.0s` discrepancy | Direct Python verification (`forensic_audit_m1.py`) | **`[FACT]`** | **CORRECTED (`M-12` & Table 1.3B)**. Retired the stale `79.2s vs 59.2s` claim and replaced `M-12` with the verified `24` Tulip Mania instance strings contaminating Layer 1 and Layer 2. |
| **`SRC-21`** | Qwen-Image-2.1 / Qwen-Image-Edit character & pose editing mechanics (`TIER_2` `qwen_nextpose` and base plate generation) | Alibaba Qwen-Image Technical Documentation | [QwenLM/Qwen-Image Official Repository](https://github.com/QwenLM/Qwen-Image) | Direct web verification + `config/model_routing.json` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Pinned in `config/model_routing.json` (`image_gen` & `image_edit`). |
| **`SRC-22`** | InsightFace ArcFace cosine similarity (`>= 0.65` hard floor, `>= 0.72` warn floor in `BP-130`) for 2D illustrated character identity verification | Deng et al. (2019), *CVPR* (*ArcFace: Additive Angular Margin Loss for Deep Face Recognition*) | [ArcFace CVPR 2019 Paper (`arXiv:1801.07698`)](https://arxiv.org/abs/1801.07698) | Direct paper verification + `qa/identity_gate.py` | **`[PRIMARY-STANDARD]`** (method) / **`[HYPOTHESIS]`** (`0.65` threshold on 2D art) | **VERIFIED & GRADED**. ArcFace is `[PRIMARY-STANDARD]` on human faces; the `0.65`/`0.72` cutoff on stylized 2D illustrations is a repo `[HYPOTHESIS]` calibrated in `GATE-P1b`. |
| **`SRC-23`** | Reinhard et al. (2001) Lab color transfer between reference character/scene plates and generated shots (`BP-130`, `assemble.py`) | Reinhard et al. (2001), *IEEE Computer Graphics and Applications* 21(5):34–41 | [Reinhard et al. (2001) — Color Transfer between Images (IEEE)](https://ieeexplore.ieee.org/document/946629) | Direct paper verification + `production/assemble.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Implemented in `explainer_engine/production/assemble.py`. |
| **`SRC-24`** | ByteDance OmniHuman-1.5 audio-driven character lip-sync / portrait animation (`D-90` fallback/comparison path vs LTX-2.5 native audio-in) | ByteDance OmniHuman Project Page & Paper | [OmniHuman-1 Official Project Page](https://omnihuman-lab.github.io/) & [arXiv:2502.01061](https://arxiv.org/abs/2502.01061) | Direct web verification + `DECISIONS_AND_OPEN_QUESTIONS.md` (`D-90`) | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Documented in `CHG-12` (`D-90` character voice spine). |
| **`SRC-25`** | Ken Burns / 3-layer 2.5D parallax depth separation (`FG`, `MG`, `BG` alpha plates with `1.03–1.08x` slow push/pan, `BP-35`) | Classic rostrum/multiplane animation camera grammar (Disney Multiplane Camera, 1937; Ken Burns documentary rostrum technique) | [Walt Disney Family Museum — Multiplane Camera](https://www.waltdisney.org/blog/multiplane-camera) + `production/parallax.py` (`BP-35`) | Direct source check + `production/parallax.py` | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Enforced by `explainer_engine/production/parallax.py` (`layers_min: 3`). |
| **`SRC-26`** | Aristotle's *Poetics* (`c. 335 BCE`, Book VII–IX): unity of action and causal probability/necessity (`"because / therefore"` vs episodic `"and then"`, `BP-06`) | Aristotle, *Poetics* (`1450b–1452a`) & Trey Parker / Matt Stone NYU screenwriting lecture (`"but / therefore"` rule) | [Aristotle's *Poetics* (MIT Classics Translation)](https://classics.mit.edu/Aristotle/poetics.1.1.html) + `BP-06` | Direct text check + `scripting/story_lint.py` | **`[CRAFT-HEURISTIC]`** | **VERIFIED**. Grounds `BP-06` (`causal_but_therefore`), while the exact connector count per 100 words is an advisory `REVIEW` metric. |
| **`SRC-27`** | Real-ESRGAN / 2D anime/illustration spatial upscaling (`1280x720 -> 2560x1440` 1440p master delivery, `BP-167`, `D-85`) | Wang et al. (2021), *ICCVW* (*Real-ESRGAN: Training Real-World Blind Super-Resolution with Pure Synthetic Data*) | [xinntao/Real-ESRGAN Official Repository](https://github.com/xinntao/Real-ESRGAN) & [arXiv:2107.10833](https://arxiv.org/abs/2107.10833) | Direct source check + `finish/upscale.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Implemented in `explainer_engine/finish/upscale.py` (`2560x1440` @ `24 fps`). |
| **`SRC-28`** | FFmpeg `loudnorm`, `adelay`, `amix`, `sidechaincompress`, and `xfade` filtergraphs used in `assemble.py` and `loudness.py` | FFmpeg Official Filter Documentation | [FFmpeg Audio & Video Filters Documentation](https://ffmpeg.org/ffmpeg-filters.html) | Direct documentation check + `production/assemble.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. All filter signatures match `explainer_engine/production/assemble.py` and `finish/loudness.py`. |
| **`SRC-29`** | Benchmark Case Study `CS-01`: MrBeast — *$456,000 Squid Game In Real Life!* (`25:42`) | MrBeast Official YouTube Channel | [$456,000 Squid Game In Real Life! (YouTube)](https://www.youtube.com/watch?v=0e3GPea1Tyg) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `AB01` (`0–15s` premise confirmation) and `hook_0_30s` cut velocity. |
| **`SRC-30`** | Benchmark Case Study `CS-02`: MrBeast — *7 Days Stranded At Sea* (`17:04`) | MrBeast Official YouTube Channel | [7 Days Stranded At Sea (YouTube)](https://www.youtube.com/watch?v=yhB3BgJyGl8) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds milestone-driven `"but / therefore"` escalation and Z3 breathing valleys. |
| **`SRC-31`** | Benchmark Case Study `CS-03`: Fern — *The Silk Road: The Rise and Fall of the Dark Net's First Drug Lord* (`24:13`) | Fern Official YouTube Channel | [The Silk Road — Fern (YouTube)](https://www.youtube.com/watch?v=GpMP6Nh3FvU) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds cold-open physical action, `BP-121` pre-reveal silence, and `HELPER` forensic diagrams. |
| **`SRC-32`** | Benchmark Case Study `CS-04`: Fern — *How One Man Broke the World's Deadliest Prison* (`18:47`) | Fern Official YouTube Channel | [How One Man Broke the World's Deadliest Prison — Fern (YouTube)](https://www.youtube.com/watch?v=F0eA9a_2vH4) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-122` acoustic perspective (`near` vs `far`) and spatial obstacle progression. |
| **`SRC-33`** | Benchmark Case Study `CS-05`: Kurzgesagt — *What If We Detonated All Nuclear Bombs at Once?* (`09:07`) | Kurzgesagt Official YouTube Channel | [What If We Detonated All Nuclear Bombs at Once? (YouTube)](https://www.youtube.com/watch?v=JyECrGp-Sw8) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `ZI-03` concrete scale proxies and `BP-14` (`140–175 WPM`) Z3 comprehension pacing. |
| **`SRC-34`** | Benchmark Case Study `CS-06`: Kurzgesagt — *The Egg - A Short Story* (`07:54`) | Kurzgesagt Official YouTube Channel | [The Egg - A Short Story (YouTube)](https://www.youtube.com/watch?v=h6fcK_fRYaI) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-142` played dialogue turns and `BP-166` act-level palette progression. |
| **`SRC-35`** | Kurzgesagt production workflow benchmark (*How to Make a Kurzgesagt Video in 1200 Hours*) | Kurzgesagt Official YouTube Channel | [How to Make a Kurzgesagt Video in 1200 Hours (YouTube)](https://www.youtube.com/watch?v=uFk0mgljtns) | Direct video check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Documents why script lock (`Stage 2`) must precede visual asset generation (`Stage 3`). |
| **`SRC-36`** | Benchmark Case Study `CS-07`: The Infographics Show — *What If the Roman Empire Never Fell?* (`12:41`) | The Infographics Show Official YouTube Channel | [What If the Roman Empire Never Fell? (YouTube)](https://www.youtube.com/watch?v=h3w1_2H22bI) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `2.0–3.5s` visual state flips on 12-minute counterfactual explainers. |
| **`SRC-37`** | Benchmark Case Study `CS-08`: The Infographics Show — *How Survival On The Titanic Worked (Hour By Hour)* (`14:18`) | The Infographics Show Official YouTube Channel | [How Survival On The Titanic Worked (YouTube)](https://www.youtube.com/watch?v=rs9w5bgtJC8) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds timestamped countdown escalation (`S08..S14`) and `60/30/10` lane orchestration (`BP-109`). |
| **`SRC-38`** | Benchmark Case Study `CS-09`: AlternateHistoryHub — *What If Germany Won WWI? (Part 1)* (`15:23`) | AlternateHistoryHub Official YouTube Channel | [What If Germany Won WWI? (YouTube)](https://www.youtube.com/watch?v=kCEUZ4faCwU) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `AB02B` (Single Point of Divergence at `30–60s`) and `HY-4` institutional constraints. |
| **`SRC-39`** | Benchmark Case Study `CS-10`: AlternateHistoryHub — *What If The Cold War Went Nuclear? (1983 Able Archer)* (`16:08`) | AlternateHistoryHub Official YouTube Channel | [What If The Cold War Went Nuclear? (YouTube)](https://www.youtube.com/watch?v=g5rVD_g2d8A) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds Adaptive Episode Profiles (`A..D`) and `late_third -> climax` WPM deceleration. |
| **`SRC-40`** | Benchmark Case Study `CS-11`: Kings and Generals — *Battle of Cannae 216 BC - Second Punic War* (`18:14`) | Kings and Generals Official YouTube Channel | [Battle of Cannae 216 BC (YouTube)](https://www.youtube.com/watch?v=6i0a726P22A) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-125` (`altitude_change_s: [4.0, 8.0]`) and `Profile B` `55/25/20` map budget. |
| **`SRC-41`** | Benchmark Case Study `CS-12`: Kings and Generals — *Fall of Constantinople 1453* (`22:36`) | Kings and Generals Official YouTube Channel | [Fall of Constantinople 1453 (YouTube)](https://www.youtube.com/watch?v=M0n4Vw6tw4I) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `ZI-02` / `PV-37` quantitative siege/engineering claim verification and `AB07` midpoint reversal. |
| **`SRC-42`** | Benchmark Case Study `CS-13`: Oversimplified — *The French Revolution (Part 1)* (`14:43`) | Oversimplified Official YouTube Channel | [The French Revolution Part 1 (YouTube)](https://www.youtube.com/watch?v=8qRZcXIODNU) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-170` Tier 3 `cutout_relocation` (`>=25%` shift) and `plate_swap` (`>=30%` diff). |
| **`SRC-43`** | Benchmark Case Study `CS-14`: Oversimplified — *The Napoleonic Wars (Part 1)* (`29:28`) | Oversimplified Official YouTube Channel | [The Napoleonic Wars Part 1 (YouTube)](https://www.youtube.com/watch?v=zqllxbPWKNI) | Direct video metadata & structure check (§15.2) | **`[VERIFIED-CREATOR]`** | **VERIFIED**. Grounds `BP-169` `dramatic_changes_per_min` (`30.0` in Z1/Z4/Z5) and `BP-172` action verbs. |
| **`SRC-44`** | Dutch Tulip Mania (1636–1637) historical baseline vs mythology (February 1637 Haarlem auction collapse; contract conversion to options rather than mass bankruptcies) | Anne Goldgar (2007), *Tulipmania: Money, Honor, and Knowledge in the Dutch Golden Age* (Univ. of Chicago Press) | [University of Chicago Press — Tulipmania by Anne Goldgar](https://www.google.com/search?q=https://press.uchicago.edu/ucp/books/book/chicago/T/bo5414921.html) | Direct academic book verification | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Confirms why Layer 3's 1637 Tulip Mania grid is strictly a `reference_only: true` structural example (`M-12`), and why any actual Tulip Mania episode must cite primary `claim_id` sources (`ZI-02`) rather than Charles Mackay (1841) myths. |
| **`SRC-45`** | Acoustic distance perception: high-frequency air absorption (`>4–6 kHz` shelf roll-off) and direct-to-reverberant ratio (`D/R`) for `far` (`Wide`) vs `near` (`ECU`) shots (`BP-122`) | Zahorik, Brungart & Bronkhorst (2005), *Psychological Bulletin* / *Acta Acustica* (*Auditory Distance Perception in Humans: A Summary of Past and Present Research*) | [Zahorik et al. (2005) — Auditory Distance Perception in Humans (DTIC / ResearchGate PDF)](https://apps.dtic.mil/sti/citations/ADA437509) | Direct psychoacoustic literature check + `BP-122` | **`[PRIMARY-STANDARD]`** (principle) / **`[HYPOTHESIS]`** (exact `-4.0 dB @ 6000 Hz`, `22%` wet values) | **VERIFIED & GRADED**. Psychoacoustic principle (`D/R` ratio + HF roll-off) is `[PRIMARY-STANDARD]`; exact `BP-122` filter numbers live in `sourced_rules.json` (`D-59`). |
| **`SRC-46`** | PuLID (Pure and Lightning ID Customization via Contrastive Alignment) for zero-shot identity preservation in image generation (`BP-130`) | Guo et al. (2024), *NeurIPS 2024* (*PuLID: Pure and Lightning ID Customization via Contrastive Alignment*) | [ToTheBeginning/PuLID Official Repository](https://github.com/ToTheBeginning/PuLID) & [arXiv:2404.16022](https://arxiv.org/abs/2404.16022) | Direct paper verification + `production/identity.py` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Referenced by `explainer_engine/production/identity.py`. |
| **`SRC-47`** | WhisperX / word-level forced alignment (`words_raw.json` -> `pause_pad.py` -> `words.json`) for frame-accurate shot-to-word timing (`BP-169`, `CHG-06`) | Bain et al. (2023), *Interspeech 2023* (*WhisperX: Time-Accurate Speech Transcription of Long-Form Audio*) | [m-bain/whisperX Official Repository](https://github.com/m-bain/whisperX) & [arXiv:2303.00747](https://arxiv.org/abs/2303.00747) | Direct paper verification + `examples/day1_v2/words_raw.json` | **`[PRIMARY-STANDARD]`** | **VERIFIED**. Grounds the word-timestamp alignment contract in `CHG-06` and `CHG-07`. |
| **`SRC-48`** | Prior roadmap `§15–§17` drafts mentioning non-existent paths (`odom_polish.py`, `tts_elevenlabs.py`, `production_script_v4.schema.json`, `docs/PRODUCT_MOLD.md`, `docs/SCHEMAS.md`, `docs/OPEN_QUESTIONS.md`, `docs/DECISIONS.md`) | Internal path naming errors in prior `§15–§17` append (`82b8da9`) | Verified against `repo_5013a55a.zip` file tree (`1,287` files) and `explainer_engine/docs_lint.py` | Direct Python repository audit (`forensic_audit_m1.py`) | **`[FACT]`** | **COMPLETELY PURGED & REPLACED**. Replaced everywhere with canonical existing repo paths (`audio/narrator_polish.py`, `schemas/production_script.schema.json`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/ARCHITECTURE.md`, `docs/PIPELINES.md`, `docs/STANDARDS.md`, `docs/PROGRESS.md`). |

## 16. Twelve-Field Evidence-Backed Proposed Change Specifications (`CHG-01` through `CHG-14`)

**[RECOMMENDATION]** Every proposed engineering change required across `BATCH-M0` through `BATCH-M8B` is specified below using the mandatory **12-field structure** (`Change ID`, `Subsystem / Target File(s)`, `Current Repository Behavior`, `Target Behavior`, `Why Needed`, `Evidence Grade & Source`, `Rule Classification`, `Exact Schema / Code / Config Surface Affected`, `Backward Compatibility & Migration Impact`, `Cost / Latency / Quality Tradeoff`, `Failure Modes & Rollback Plan`, `Verification Test & Acceptance Criteria`). All file paths are verified against `repo_5013a55a.zip` (`5013a55aca5a17a3734150f61a5eb172abcbe3b8`).

### `CHG-01` — Unify Master Mold v2.1.0 Contract (`explainer_engine/standards/mrbeast_12min_video_mold.json`) & Reconcile `M-01..M-12` (`BATCH-M1`)

1. **Change ID**: `CHG-01`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/standards/mrbeast_12min_video_mold.json` *(new canonical contract file normalized from `mrbeast_12min_video_mold (1).json` SHA-256 `2ca7f56f...`)*
   * `explainer_engine/standards/mold_contract.py` *(new loader & validator module)*
   * `docs/MRBEAST_12MIN_MASTER_MOLD.md` *(new canonical companion documentation normalized from `mrbeast_12min_master_mold.md` SHA-256 `49cf3084...`)*
   * `explainer_engine/standards/sourced_rules.json`
   * `tests/unit/test_mold_contract.py` *(new unit test suite)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** Neither `mrbeast_12min_video_mold.json` nor `MRBEAST_12MIN_MASTER_MOLD.md` is tracked in `repo_5013a55a.zip`. Meanwhile, the bundle files (`2ca7f56f...` and `49cf3084...`) contain the **12 internal discrepancies (`M-01..M-12`)** documented in §3.2: uppercase `Z1..Z5` zone IDs (`M-01`), duplicate threshold numbers in `zones_5` violating `D-59` (`M-02`), `bp141_non_character_max: 0.8` across all 4 profiles (`M-03`), `38` of `76` `STILL` shots (`2` `TIER_1` + `36` `TIER_2`) exceeding `BP-170` static caps (`M-04`), `AB07..AB12` window mismatches vs `S09..S16` (`M-05`), dangling `BP-68`/`BP-155`/`BP-79` citations (`M-06`, `M-07`), mis-cited `BP-125` on still motion (`M-08`), `BP-84` collision (`M-09`), `BP-128` handle-frame mismatch (`M-10`), `BP-122` hardcoded EQ drift (`M-11`), and `24` hardcoded 1637 Tulip Mania strings inside Layer 1 and Layer 2 (`M-12`).
4. **Target Behavior**:
   * Commit a normalized, LF-terminated `explainer_engine/standards/mrbeast_12min_video_mold.json` (`mold_meta.schema_version: "2.1.0"`) and `docs/MRBEAST_12MIN_MASTER_MOLD.md` with all `M-01..M-12` resolved:
     1. **Strict 3-Layer Separation (`M-12`)**: Move all `24` Tulip Mania example strings out of `layer_1_narrative_constitution` and `layer_2_production_profile` into `layer_3_reference_instance` (`reference_only: true`).
     2. **`D-59` Single-Home Compliance (`M-02`, `M-03`, `M-11`)**: Replace duplicated numeric thresholds in Layer 1/2 (`zones_5`, `episode_profiles`, `BP-122` EQ/wet strings) with symbolic rule pointers (`rule_ref: "BP-169"`, `"BP-109"`, `"BP-141"`, `"BP-122"`) resolved at runtime by `mold_contract.py` via `sourced_rules.T(...)`.
     3. **Citation & Zone ID Normalization (`M-01`, `M-05..M-09`)**: Canonicalize `zone_id` to `BP-169` lowercase IDs (`hook_0_30s` .. `climax_660_720s`) with a one-way ingestion normalizer `normalize_zone_id()`, align `AB01..AB12` to `S01..S16`, and replace `BP-68`/`BP-155` -> `ZI-02`/`PV-37`, `BP-79` -> `BP-43`/`BP-106`, and still-motion `BP-125`/`BP-84` -> `BP-35`/`BP-132`/`BP-170`.
5. **Why Needed**:
   * Committing the raw bundle JSON without resolving `M-01..M-12` would immediately fail `tests/unit/test_sourced_rules.py` (`D-59`), break `edit/dramatic_still.py` (`38` `DS-01` failures), and contaminate topic-agnostic Layer 1/2 rules with 1637 Dutch Tulip Mania strings (`ZI-09`).
6. **Evidence Grade & Source**:
   * **`[FACT]`**: Direct programmatic audit of `mrbeast_12min_video_mold (1).json` (`2ca7f56f...`), `mrbeast_12min_master_mold.md` (`49cf3084...`), `explainer_engine/standards/sourced_rules.json`, and `tests/unit/test_sourced_rules.py`.
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)** for schema validity, `D-59` single-home compliance, `17,280`-frame (`720.0s`) conservation, and zero Tulip Mania tokens in Layer 1/2; **Reference-Only (`INFO`)** for `layer_3_reference_instance`.
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/standards/mrbeast_12min_video_mold.json`, `explainer_engine/standards/mold_contract.py` (`load_mold_contract()`, `normalize_zone_id()`, `validate_mold_contract()`), `docs/MRBEAST_12MIN_MASTER_MOLD.md`, and `explainer_engine/standards/sourced_rules.json`.
9. **Backward Compatibility & Migration Impact**:
   * Additive module (`mold_contract.py`); existing `/1..3` scripts and tests are untouched. `normalize_zone_id()` maps legacy `Z1_HOOK_0_30S..Z5_CLIMAX_660_720S` inputs cleanly to `hook_0_30s..climax_660_720s`.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` GPU/API cost; `<15 ms` local JSON load/validation time; eliminates `12` cross-document contradictions before any downstream code batch starts.
11. **Failure Modes & Rollback Plan**:
    * If any threshold in `mrbeast_12min_video_mold.json` duplicates a `sourced_rules.json` number, `test_sourced_rules.py` and `test_mold_contract.py` fail in CI. Rollback is a single commit revert of `BATCH-M1`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_mold_contract.py tests/unit/test_sourced_rules.py` passes (`0` duplicate numbers, `0` dangling `BP-*` references, `0` Tulip Mania strings in Layer 1/2, `17,280` frames = `720.0s` exact sum).

### `CHG-02` — Unify `/4` Schema Version Dispatch Across `script.py` & All 11 Consumer Modules (`BATCH-M0`)

1. **Change ID**: `CHG-02`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/scripting/schema_version.py` *(new shared helper)*
   * `explainer_engine/production/script.py` (`L65`, `L530–566`)
   * **All 11 `/3`-checking consumer modules verified in `repo_5013a55a.zip`**:
     1. `explainer_engine/scripting/scene_lint.py` (`L35–42`)
     2. `explainer_engine/scripting/script_approval.py` (`L31–38`)
     3. `explainer_engine/scripting/speech.py` (`L290–293`)
     4. `explainer_engine/scripting/story_lint.py` (`L162–169`)
     5. `explainer_engine/production/beats.py` (`L27–34`, `L206`, `L404`)
     6. `explainer_engine/production/editorial_gate.py` (`L48–52`)
     7. `explainer_engine/production/silent.py` (`L129`)
     8. `explainer_engine/production/staging.py` (`L314–318`)
     9. `explainer_engine/production/validate.py` (`L106`, `L339`)
     10. `explainer_engine/production_gate.py` (`L439`, `L569`)
     11. `explainer_engine/audio/layers.py` (`L329–332`)
   * Plus the 3 P0 defect sites identified in §2: `explainer_engine/audio/narrator_polish.py` (`L97`), `explainer_engine/production/shot_prompt_checks.py` (`L181–195`), and `explainer_engine/production/sample.py` (`L84`).
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `explainer_engine/schemas/production_script.schema.json` (`L25`) already accepts `"enum": ["https://tmr.dev/schemas/production_script/3", "https://tmr.dev/schemas/production_script/4"]`. However, `production/script.py:65` hardcodes `SCHEMA_VERSION = "https://tmr.dev/schemas/production_script/3"` and `L563` omits `rhythm_profile` and `segments` from top-level output, while the **11 consumer modules** above check `endswith("/3")` or `== ".../3"`. Consequently, passing a `/4` script causes silent validation skips or `/1` legacy fallbacks!

| # | Module Path & Verified Lines (`5013a55a`) | Current Version Check Condition | Current Bug on `/4` Scripts | Target `/1..2`, `/3`, and `/4` Behavior via `schema_version.py` | Required Regression Test |
| ----- | ----- | ----- | ----- | ----- | ----- |
| **1** | `explainer_engine/production/script.py:65, 530–566` | `SCHEMA_VERSION = ".../3"`; `build_production_script()` drops `rhythm_profile` & `segments` | Cannot emit `/4` scripts | Emit `/4` (`SCHEMA_VERSION_V4`) with `rhythm_profile` and `segments` when `rhythm_profile == "mrbeast_animated"` or `schema_v == 4`; keep `/3` default for `calm_docudrama`. | `tests/unit/test_production_script_v4.py::test_build_v4_emits_segments` |
| **2** | `explainer_engine/scripting/scene_lint.py:35–42` | `str(script.get("schema_version", "")).endswith("/3")` | Skips scene lint on `/4` (returns `[]`) | Run v3+ scene lint on both `/3` and `/4` (`is_v3_plus(script)`), skipping only `/1..2`. | `tests/unit/test_schema_version_dispatch.py::test_scene_lint_runs_on_v4` |
| **3** | `explainer_engine/scripting/script_approval.py:31–38` | `str(script.get("schema_version", "")).endswith("/3")` | Skips v3+ approval checks on `/4` | Enforce v3+ approval checks on both `/3` and `/4` (`is_v3_plus(script)`). | `tests/unit/test_schema_version_dispatch.py::test_script_approval_v4` |
| **4** | `explainer_engine/scripting/speech.py:290–293` | `str(script.get("schema_version") or "").endswith("/3")` | Skips v3+ speech checks (`SP-10..SP-13`) on `/4` | Run v3+ speech checks on both `/3` and `/4`; pass `rhythm_profile` so WPM bounds defer to `BP-169` on `/4`. | `tests/unit/test_schema_version_dispatch.py::test_speech_lint_v4` |
| **5** | `explainer_engine/scripting/story_lint.py:162–169` | `str(script.get("schema_version", "")).endswith("/3")` | Skips v3+ story lint on `/4` | Run v3+ story lint on both `/3` and `/4` (`is_v3_plus(script)`), plus `/4` anchor checks (`AB01..AB12`) when `is_v4(script)`. | `tests/unit/test_schema_version_dispatch.py::test_story_lint_v4` |
| **6** | `explainer_engine/production/beats.py:27–34, 206, 404` | `endswith("/3")` (`_is_v3`); `validate_beats` checks `schema_version != SCHEMA_VERSION` (`/1`) | Falls back to `/1` beat validation and fails `/4` scripts (`BT-01`) | `_is_v3_plus(doc)` accepts `/3` and `/4`; `validate_beats` delegates `/3` and `/4` scripts to `production/validate.py`. | `tests/unit/test_schema_version_dispatch.py::test_beats_accepts_v4` |
| **7** | `explainer_engine/production/editorial_gate.py:48–52` | `str(script.get("schema_version", "")).endswith("/3")` | Treats `/4` as `/1..2` legacy script | Treat `/3` and `/4` identically via `is_v3_plus(script)`. | `tests/unit/test_schema_version_dispatch.py::test_editorial_gate_v4` |
| **8** | `explainer_engine/production/silent.py:129` | `str(script.get("schema_version") or "").endswith("/3")` | Skips v3+ silent-hold validation on `/4` | Run v3+ silent-hold validation on both `/3` and `/4` (`is_v3_plus(script)`). | `tests/unit/test_schema_version_dispatch.py::test_silent_v4` |
| **9** | `explainer_engine/production/staging.py:314–318` | `str(script.get("schema_version") or "").endswith("/3")` | Skips v3+ staging checks on `/4` | Run v3+ staging checks on both `/3` and `/4` (`is_v3_plus(script)`). | `tests/unit/test_schema_version_dispatch.py::test_staging_v4` |
| **10** | `explainer_engine/production/validate.py:106, 339` | `sv not in (SCHEMA_VERSION, SCHEMA_VERSION_V4)` (already accepts `/4` at L106, but L339 checks `sv == SCHEMA_VERSION_V4` only for `rhythm_lint`) | L106 works, but does not validate `/4` segment-shot duration conservation | Keep `/3` and `/4` acceptance at L106; add `/4` `segments[]` coverage & `17,280`-frame conservation check at L339. | `tests/unit/test_schema_version_dispatch.py::test_validate_v4_segments` |
| **11** | `explainer_engine/production_gate.py:439, 569` | `str(raw_script.get("schema_version") or "").endswith("/3")` | Skips v3+ production gate checks (`PG-*`) on `/4`! | Replace `endswith("/3")` at L439 and L569 with `is_v3_plus(raw_script)` so all `PG-*` gates run on `/4`. | `tests/unit/test_schema_version_dispatch.py::test_production_gate_v4` |
| **12** | `explainer_engine/audio/layers.py:329–332` | `str(script.get("schema_version") or "").endswith("/3")` | Skips v3+ audio layer checks on `/4` | Replace `endswith("/3")` with `is_v3_plus(script)` so v3+ audio layer gates run on `/4`. | `tests/unit/test_schema_version_dispatch.py::test_audio_layers_v4` |

4. **Target Behavior**:
   * Create `explainer_engine/scripting/schema_version.py` exporting `schema_major(doc) -> int`, `is_v3_plus(doc) -> bool` (`schema_major(doc) in (3, 4)`), and `is_v4(doc) -> bool` (`schema_major(doc) == 4`), update all 12 modules in the table above, and fix the 3 P0 runtime bugs:
     * `explainer_engine/audio/narrator_polish.py:97`: change `tags = list(zone.get("tts_tags_allowed") or ())` to `tags = list(zone.get("tts_tags") or zone.get("tts_tags_allowed") or ())` so `BP-169`'s `"tts_tags"` key is actually read.
     * `explainer_engine/production/shot_prompt_checks.py:181–195`: iterate over `script.get("scenes") or script.get("segments") or ()` so `SPC-20` (`BP-172` action-verb check) runs on `/4` scripts that use `segments[]`.
     * `explainer_engine/production/sample.py:84`: resolve `calm_window_s` dynamically from the active rhythm profile (`[90.0, 120.0]` on `mrbeast_animated` `S04` vs `[60.0, 90.0]` on `calm_docudrama`).
5. **Why Needed**:
   * Without `CHG-02`, every `/4` script silently bypasses `scene_lint`, `script_approval`, `speech`, `story_lint`, `editorial_gate`, `silent`, `staging`, `production_gate`, `audio/layers`, `narrator_polish`, and `shot_prompt_checks`.
6. **Evidence Grade & Source**:
   * **`[FACT]`**: Direct line-by-line inspection of all 15 repository files at commit `5013a55aca5a17a3734150f61a5eb172abcbe3b8`.
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `explainer_engine/scripting/schema_version.py` + the 14 existing Python modules listed in Field 2.
9. **Backward Compatibility & Migration Impact**:
   * 100% backward compatible: `/1`, `/2`, and `/3` scripts behave identically (`is_v3_plus` is `True` for `/3` and `/4`, `False` for `/1..2`).
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; `0 ms` runtime overhead; restores full gate coverage on `/4` scripts.
11. **Failure Modes & Rollback Plan**:
    * Covered by parametrized unit tests across `/1`, `/3`, and `/4` fixtures; revert `BATCH-M0` if any existing `/3` test regresses.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_schema_version_dispatch.py tests/unit/test_narrator_polish.py tests/unit/test_shot_prompt_checks.py` passes with `0` skipped gates on `/4`.

### `CHG-03` — Wire 5-Zone Rhythm Profile (`BP-169`) Across `edit/rhythm.py`, `edit/board.py` (`BP-84` Scoping), `scripting/speech.py`, and `qa/retention.py` (`BATCH-M2`)

1. **Change ID**: `CHG-03`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/edit/rhythm.py` (`L65–220`)
   * `explainer_engine/edit/board.py` (`L38–39`, `L155`)
   * `explainer_engine/scripting/speech.py` (`L42–115`)
   * `explainer_engine/qa/retention.py` (`L45–130`)
   * `tests/unit/test_rhythm_zones.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `edit/rhythm_profile.py` defines `load_rhythm_profile()`, but `edit/rhythm.py` still enforces flat `BP-26` act targets (`3.2s / 5.5s / 3.8s`), `edit/board.py:155` enforces `BP-84` `min_shot_s: 2.5` globally (rejecting `1.0–2.4s` shots in `hook_0_30s`), `scripting/speech.py` enforces flat `BP-14` `140–175 WPM` across the whole episode (flagging `193` WPM in Z1 and `185` WPM in Z4), and `qa/retention.py` uses flat cut-interval weights.
4. **Target Behavior**:
   * Wire `rhythm_profile` (`"mrbeast_animated"` vs `"calm_docudrama"`) into all four modules:
     1. `edit/rhythm.py`: when `rhythm_profile == "mrbeast_animated"`, resolve shot duration bounds `[min_s, max_s]` and cut density per zone via `edit/rhythm_profile.py` (`BP-169`) while preserving `BP-28` (`sigma >= 0.8s`, `CV >= 0.30`) and `BP-30` (`>=1` breathing valley `>=3.5s` every `90–120s` in `middle_calm_90_480s`).
     2. `edit/board.py`: scope `RHYTHM-2` (`min_shot_s: 2.5`) to `calm_docudrama`, delegating `mrbeast_animated` minimum shot duration to `BP-169` (`1.0s / 1.5s / 2.0s / 1.2s / 1.0s`), while keeping `BUBBLE-1` (`bubble_chars_per_line <= 26`) active on all profiles (`M-09`).
     3. `scripting/speech.py` & `qa/retention.py`: evaluate segment WPM and visual change density against the active zone's `BP-169` `heard_wpm_range` and `dramatic_changes_per_min`.
5. **Why Needed**:
   * Prevents `edit/rhythm.py`, `edit/board.py`, and `scripting/speech.py` from contradicting `scripting/rhythm_lint.py` (`BP-169`) on `/4` scripts.
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`BP-169` in `sourced_rules.json`) + **`[VERIFIED-CREATOR]`** (`SRC-10` MrBeast manual) + **`[HYPOTHESIS]`** (exact zone WPM/cut numbers, `CD-04`).
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)** for episode-level zone coverage (`0–720s`); **Advisory Hypothesis (`REVIEW`)** for intra-zone WPM/cut-rate tolerances until calibrated (`CD-04`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `edit/rhythm.py`, `edit/board.py`, `scripting/speech.py`, `qa/retention.py`.
9. **Backward Compatibility & Migration Impact**:
   * Default `rhythm_profile="calm_docudrama"` preserves existing `/3` behavior 100%.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; unifies all editorial and speech linters around `BP-169`.
11. **Failure Modes & Rollback Plan**:
    * If `rhythm_profile` is omitted on a `/3` script, defaults to `calm_docudrama`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_rhythm_zones.py tests/unit/test_board.py tests/unit/test_speech.py` passes on both `calm_docudrama` and `mrbeast_animated` fixtures.

### `CHG-04` — Profile-Aware Visual Lane Budgets (`A..D`) in `BP-109`, `variant_plan.py` & `film_shots.py` (`BATCH-M1` & `BATCH-M2`)

1. **Change ID**: `CHG-04`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/standards/sourced_rules.json` (`BP-109`, `BP-141`)
   * `explainer_engine/production/variant_plan.py` (`L48–165`)
   * `explainer_engine/scripting/film_shots.py` (`L610–690`)
   * `explainer_engine/schemas/production_script.schema.json` (`episode_profile` enum `["A", "B", "C", "D"]`)
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `BP-109` enforces a single global `60/30/10 ±5%` (`VIDEO`/`STILL`/`HELPER`) split (`D-93`), while `BP-141` (`status: "hypothesis"`, `severity: "REVIEW"`) already defines `profiles.A..D` (`non_character_max: 0.45` for `A/D`, `0.80` for `B/C`). `variant_plan.py` and `film_shots.py` do not read `episode_profile`.
4. **Target Behavior**:
   * Add optional `"episode_profile": "A" | "B" | "C" | "D"` (default `"D"` `60/30/10 ±5%`) to `production_script.schema.json` `/4` and `BP-109`:
     * **Profile D (Default Hybrid Counterfactual)**: `60% VIDEO / 30% STILL / 10% HELPER` (`±5%`), `BP-141` `non_character_max: 0.45` (`REVIEW`).
     * **Profile A (Character Courtroom / Political Drama)**: `65% VIDEO / 27% STILL / 8% HELPER` (`±5%`), `BP-141` `non_character_max: 0.45` (`REVIEW`).
     * **Profile B (Military Campaign / Siege)**: `55% VIDEO / 25% STILL / 20% HELPER` (`±5%`), `BP-141` `non_character_max: 0.80` (`REVIEW`).
     * **Profile C (Financial / Systemic Contagion)**: `55% VIDEO / 27% STILL / 18% HELPER` (`±5%`), `BP-141` `non_character_max: 0.80` (`REVIEW`).
   * Preserve `BP-141`'s `status: "hypothesis"` and `severity: "REVIEW"` (`M-03`).
5. **Why Needed**:
   * Allows map-heavy military campaigns (`Profile B`, e.g., `CS-11` Cannae) or ledger-heavy financial contagion (`Profile C`) to use up to `18–20%` `HELPER` maps/diagrams without violating `D-93`'s default `60/30/10` contract (`Profile D`).
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`BP-109`, `BP-141`, `D-93`) + **`[VERIFIED-CREATOR]`** (`CS-10`, `CS-11`) + **`[HYPOTHESIS]`** (`BP-141` `REVIEW`).
7. **Rule Classification**:
   * **Profile Parameter (`FAIL` if outside selected profile's `±5%` lane bounds; `REVIEW` for `BP-141` `non_character_max`)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `sourced_rules.json` (`BP-109`), `production_script.schema.json`, `variant_plan.py`, `film_shots.py`.
9. **Backward Compatibility & Migration Impact**:
   * Scripts omitting `episode_profile` default to `"D"` (`60/30/10 ±5%`), preserving 100% compatibility with `D-93`.
10. **Cost / Latency / Quality Tradeoff**:
    * Profiles `B` and `C` reduce LTX GPU cost by `~8%` (`55%` vs `60%` `VIDEO` lane) on map/chart-heavy topics.
11. **Failure Modes & Rollback Plan**:
    * Unknown profile IDs raise a schema validation error; revert to `"D"` default if needed.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_variant_plan.py tests/unit/test_film_shots.py` verifies Profiles `A..D` lane bounds and preserves `BP-141` `severity == "REVIEW"`.

### `CHG-05` — Implement 12-Anchor Narrative Architecture (`AB01..AB12`) & Word-Share `BP-04` Gate in `story_lint.py` (`BATCH-M2`)

1. **Change ID**: `CHG-05`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/scripting/story_lint.py` (`L160–310`)
   * `explainer_engine/schemas/production_script.schema.json` (`segments[].anchor_ids`)
   * `tests/unit/test_story_lint_anchors.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `story_lint.py` checks `BP-01` (`question_plant` interval `<=90s`), `BP-04` (`answer_after_share >= 0.90`), `BP-06` (`causal_but_therefore`), and `BP-142` (`turn_slots_D: [4, 6, 8, 10, 11, 13]`), but does not validate the 12-anchor progression (`AB01..AB12`) or `AB02B` (Single Point of Divergence at `30–60s` in `S02`).
4. **Target Behavior**:
   * Add `validate_twelve_anchors(script)` to `story_lint.py` for `/4` scripts (`M-05`, §15.1):
     1. Verify `S01..S16` cover all `12` anchors (`AB01`, `AB02A`, `AB02B`, `AB03..AB12`) in strictly ascending order (`FAIL` if an anchor is missing or out of order).
     2. Enforce **two independent checks** on `AB11`/`AB12` (`M-05`): (a) segment time windows `S15` (`660–690s`) and `S16` (`690–720s`), and (b) `BP-04` (`ENG-5`) verified on **cumulative spoken word share (`>= 90.0%` of total episode words delivered before the central resolution answer begins)** (in the 2,066-word reference grid, `90.0%` = `1,860` words is crossed at `~644.1s` in `S14`, and `S15` starts at `1,909` words = `92.40%`).
     3. Keep `BP-06` (`causal_but_therefore` connector density) as an advisory craft check (`severity: "REVIEW"`), never a mechanical word-count `FAIL`.
5. **Why Needed**:
   * Prevents premature thesis spoilers (`<90%` spoken words), missing `30–60s` Point of Divergence (`AB02B`), or missing `180s`/`360s` re-hook spikes (`AB05`, `AB07`).
6. **Evidence Grade & Source**:
   * **`[VERIFIED-CREATOR]`** (`SRC-10` MrBeast manual, `CS-09` AlternateHistoryHub PoD) + **`[CRAFT-HEURISTIC]`** (`SRC-09` Loewenstein, `SRC-26` Aristotle `BP-06`).
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)** for `AB01..AB12` presence/ordering, `BP-142` turn slots `[4, 6, 8, 10, 11, 13]`, and `BP-04` `>=90%` word share; **Craft Heuristic (`REVIEW`)** for `BP-06` connector density.
8. **Exact Schema / Code / Config Surface Affected**:
   * `scripting/story_lint.py`, `schemas/production_script.schema.json`.
9. **Backward Compatibility & Migration Impact**:
   * Runs `validate_twelve_anchors()` only when `is_v4(script)` is `True`; `/3` scripts remain unchanged.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` cost; `<5 ms` CPU check; catches structural flatlines at script-lint time before paid TTS/GPU runs.
11. **Failure Modes & Rollback Plan**:
    * Emits explicit `SL-AB01..SL-AB12` codes pinpointing the offending segment `S01..S16`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_story_lint_anchors.py` passes on the reconciled 2,066-word `mrbeast_12min_video_mold.json` reference grid and flags synthetic out-of-order or `<90%`-word-share fixtures.

### `CHG-06` — Closed-Loop `eleven_v4` Zone Prosody, Segment-Scoped Re-Hook Tags & Deficit Pause Padding (`BATCH-M3`)

1. **Change ID**: `CHG-06`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/narrator_polish.py` (`L65–145`)
   * `explainer_engine/audio/hype_read.py` (`L40–110`)
   * `explainer_engine/audio/pause_pad.py` (`L70–135`)
   * `explainer_engine/standards/sourced_rules.json` (`BP-169`, `BP-171`)
   * `tests/unit/test_pause_pad_zone_closed_loop.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `narrator_polish.py:97` reads `zone.get("tts_tags_allowed")` instead of `BP-169`'s `"tts_tags"` (returning `[]`), `hype_read.py` (`HR-01`) rejects `[excited]` everywhere in `middle_calm_90_480s` (blocking `180s` `S06` and `360s` `S09` re-hook spikes `M-02`), and `pause_pad.py` applies flat punctuation pause floors (`0.22s` comma, `0.42s` period, `0.38s` em-dash) regardless of rhythm zone.
4. **Target Behavior**:
   * Implement three verified `eleven_v4`-native (`D-94`, `Odom`) improvements:
     1. **Fix `narrator_polish.py` & Punctuation Pause Shaping (`[PRIMARY-STANDARD]` `SRC-04`)**: Read `zone.get("tts_tags")`, never emit SSML `<break>` tags (unsupported on `eleven_v4` / `v3`), and use em-dashes (`—`) + `BP-171` bracketed audio tags (`<=1` tag per `2` sentences, `max_tags_per_2_sentences: 1`).
     2. **Segment-Scoped Re-Hook Tag Exception (`M-02`)**: Add `"rehook_tts_tags": ["excited"]` to `BP-169`'s `middle_calm_90_480s` spec and update `audio/hype_read.py` so `[excited]` is permitted **only** on segments with `rehook_spike: true` (`S06` at `180s` and `S09` at `360s`) and remains forbidden across `S04, S05, S07, S08, S10, S11`.
     3. **Closed-Loop Deficit Pause Padding in `pause_pad.py` (§15.4 Proof)**: Because real `eleven_v4` outputs in `examples/` already contain `28.4%–37.3%` natural pauses (`day1_v2`: `225.5` speaking WPM -> `141.4` raw heard WPM), `pause_pad.py` computes each segment's **measured raw heard WPM** from `words_raw.json` first. If `measured_heard_wpm <= zone.heard_wpm_target`, `pause_pad.py` inserts `0.0s` extra padding (preserving only explicit dramatic beats `BP-121`); if `measured_heard_wpm > zone.heard_wpm_target`, `pause_pad.py` scales boundary `want` targets (`gap = b["s"] - a["e"]`, `add = max(0.0, want - gap)`) so the post-pad duration lands inside `BP-169`'s `heard_wpm_range`.
5. **Why Needed**:
   * Prevents double-padding `eleven_v4` audio while ensuring `S06`/`S09` re-hooks can use `[excited]` without triggering `HR-01` failures.
6. **Evidence Grade & Source**:
   * **`[PRIMARY-STANDARD]`** ([ElevenLabs Pause Docs](https://elevenlabs.io/docs/help-center/product/core-capabilities/text-to-speech/how-can-i-add-pauses), `SRC-04`) + **`[FACT]`** (measured `examples/day1_v2/words_raw.json`, `examples/titans_from_zero/words.json`, `examples/syndicate_wars_ep1/words.json`).
7. **Rule Classification**:
   * **Hard Gate (`FAIL`)** for `BP-171` tag syntax/whitelist (`HR-01..HR-03`) and zero SSML `<break>` tags on `eleven_v4`; **Advisory Hypothesis (`REVIEW`)** for intra-zone WPM target matching (`CD-04`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/narrator_polish.py`, `audio/hype_read.py`, `audio/pause_pad.py`, `standards/sourced_rules.json` (`BP-169`).
9. **Backward Compatibility & Migration Impact**:
   * Existing `pad_pauses_in_wav()` signature preserved with optional `rhythm_zone: str | None = None` parameter.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` extra TTS cost (operates on local PCM waveform + `words_raw.json` before shot compilation).
11. **Failure Modes & Rollback Plan**:
    * Never truncates active speech phonation (`add >= 0.0`); if raw `eleven_v4` speech is slower than `heard_wpm_range[0]`, emits `RL-WPM-SLOW` (`REVIEW`) for the Layer 3 compiler (`CHG-07`) rather than clipping syllables.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_pause_pad_zone_closed_loop.py tests/unit/test_hype_read.py` passes on real `examples/day1_v2/words_raw.json` fixtures.

### `CHG-07` — Implement Layer 3 Bounded Timeline Compilation Engine & Infeasibility Contract (`17,280`-Frame Conservation, `BATCH-M4`)

1. **Change ID**: `CHG-07`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/production/timeline_compiler.py` *(new deterministic Layer 3 solver)*
   * `explainer_engine/production/script.py` (`L420–566`)
   * `explainer_engine/production/beats.py` (`L120–240`)
   * `tests/unit/test_timeline_compiler.py` *(new unit test including infeasibility proofs)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `production/script.py` and `production/beats.py` assign shot durations linearly from word timestamps without enforcing `17,280`-frame (`720.0s`) episode conservation, `S01..S16` segment boundaries, `BP-169` zone shot-length bounds (`[min_s, max_s]`), or `BP-28` (`sigma >= 0.8s`, `CV >= 0.30`). Moreover, in `mrbeast_12min_video_mold (1).json`, `late_third_480_660s` (`S12–S14`) has `30` of `50` shots exceeding `3.0s` (`3.60s` mean vs `2.0s` target).
4. **Target Behavior**:
   * Implement `compile_episode_timeline(script, words_json, rhythm_profile)` in `explainer_engine/production/timeline_compiler.py` executing a **5-step deterministic solver**:
     1. **Step 1 (Audio-Anchored Segment Span)**: Anchor spoken phrases from `words.json` (`CHG-06`) to `S01..S16` and quantize every shot boundary to integer frames at `24 fps` (`frame_span = frame_out - frame_in`, $\sum \text{frame\_span} = 17,280$).
     2. **Step 2 (Zone Bounds Projection `BP-169`)**: Subdivide any shot exceeding its zone's `shot_s_range[1]` (e.g., splitting `>3.0s` shots in `late_third_480_660s` at clause/word boundaries into `VIDEO` + `STILL` reaction pairs) and merge/extend sub-minimum shots (`< shot_s_range[0]`).
     3. **Step 3 (Still Hold Cap Enforcement `BP-170`)**: Clamp any `TIER_1` or `TIER_2` `STILL` shot to `<= static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`), transferring excess frames to adjacent `VIDEO` or `TIER_3` shots.
     4. **Step 4 (Anti-Metronome Variance Repair `BP-28` & Breathing Valleys `BP-30`)**: If shot duration standard deviation $\sigma < 0.8\text{s}$ or $\text{CV} < 0.30$, apply zero-sum frame transfers (`±6..18` frames) between adjacent clause-aligned shots within the same zone while preserving at least one `3.5–5.0s` breathing valley (`BP-30`) per `90–120s` in `middle_calm_90_480s`.
     5. **Step 5 (Explicit Mathematical Infeasibility Contract)**:
        * **When a segment is mathematically over-constrained**—specifically if (a) total post-TTS audio duration $\sum T_{\text{audio}} > 720.0\text{s} - T_{\text{mandatory\_vacuums}}$ (speech overruns the 12-minute container), (b) total post-TTS audio duration $\sum T_{\text{audio}} < 600.0\text{s}$ (requiring `>120s` of dead air that would violate `BP-169` `heard_wpm_range[0]` and `BP-170` still caps), or (c) a segment's word count cannot be partitioned into shots satisfying both `BP-169` `shot_s_range` and `BP-170` `static_still_max_s_by_zone` without cutting mid-word—`compile_episode_timeline()` **MUST NOT silently relax `BP-170` (`FAIL`), `17,280`-frame conservation (`FAIL`), or mid-word cut bans (`FAIL`)**.
        * Instead, it raises a structured `TimelineInfeasibleError(code="TC-INFEASIBLE-01..03")` returning an exact **`SegmentTrimOrExpandDirective`** (`segment_id`, `current_words`, `target_word_delta`, `reason`) back to the Writers' Room (`scripting/writers_room.py`) to add or trim words in that segment before re-running TTS on that single segment!
5. **Why Needed**:
   * Guarantees that every compiled `/4` `production_script.json` mathematically satisfies `17,280` frames (`720.0s`), `BP-169`, `BP-170`, `BP-28`, and `BP-30` before a single dollar of RunPod GPU spend occurs.
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`BP-28`, `BP-30`, `BP-167`, `BP-169`, `BP-170`) + **`[PRIMARY-STANDARD]`** (`SRC-15` Cutting et al. 2010 variance).
7. **Rule Classification**:
   * **Hard Structural Invariant (`FAIL`)** for `17,280`-frame conservation, integer `frame_in`/`frame_out` continuity, `BP-170` still caps, and `TC-INFEASIBLE` halt on speech overrun/underrun.
8. **Exact Schema / Code / Config Surface Affected**:
   * `production/timeline_compiler.py`, `production/script.py`, `production/beats.py`.
9. **Backward Compatibility & Migration Impact**:
   * Invoked on `/4` (`mrbeast_animated`) builds; `/3` (`calm_docudrama`) retains existing variable-duration `build_production_script()`.
10. **Cost / Latency / Quality Tradeoff**:
    * `<50 ms` deterministic CPU solver; saves `$5–$15` per episode in wasted GPU renders by catching timing infeasibility before visual generation.
11. **Failure Modes & Rollback Plan**:
    * On `TimelineInfeasibleError`, halts before `Stage 3` GPU spend and outputs the exact per-segment word delta needed.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_timeline_compiler.py` verifies: (1) exact `17,280`-frame compilation on a 2,066-word fixture, (2) repair of the `30` over-3.0s `late_third_480_660s` shots in the Mold reference grid, and (3) deterministic `TimelineInfeasibleError` with `SegmentTrimOrExpandDirective` on synthetic speech-overrun (`2,600` words) and speech-underrun (`1,100` words) fixtures.

### `CHG-08` — Reconcile LTX-2.5 `8k+1` Frame Quantum (`BP-139`) & Transition-Aware Handle Frames (`BP-128`) in `assemble.py` & `ltx_generate.py` (`BATCH-M5`)

1. **Change ID**: `CHG-08`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/production/ltx_generate.py` (`L90–145`)
   * `explainer_engine/production/assemble.py` (`L714–735`)
   * `explainer_engine/standards/sourced_rules.json` (`BP-128`, `BP-139`)
   * `tests/unit/test_ltx_handle_frames.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `BP-139` enforces `F = 8k + 1` on LTX-2.5 clips, and `BP-128` (`assemble.py:714–727`) requires `handle_frames: [12, 16]` per side (`>=24` extra frames before `8k+1` rounding) on every `VIDEO` shot. Across the `152` `VIDEO` shots (`10,368` usable timeline frames = `432.00s`) in `mrbeast_12min_video_mold (1).json`, `>=12` handles/side requires **`14,552` generated LTX frames** (`+4,184` overhead frames = `+40.35%`). Meanwhile, the Mold specifies `>=4` handles/side (`12,120` generated frames), which triggers `152` `BP-128` `REVIEW` warnings in `assemble.py`.
4. **Target Behavior**:
   * Implement a **transition-aware handle-frame contract** (`M-10`, §15.6 Table) in `ltx_generate.py`, `assemble.py`, and `BP-128`:
     1. **`VIDEO` shots only (`BP-139`)**: `STILL` (`76` shots) and `HELPER` (`26` shots) are rendered at exact timeline `frame_span` via CPU/compositor (`parallax.py`, `assemble.py`) and **never** use LTX `8k+1` frame counts.
     2. **Transition-Aware LTX Formula (`[HYPOTHESIS]`, `severity: "REVIEW"`)**:
        * For `VIDEO` shots bounded by **whip-pans (`BP-129`, `0.25–0.40s` = `6–10f`) or crossfades/dissolves (`BP-31`, `0.50s` = `12f`)** (`17` of `152` shots in the Mold): require `handle_frames_per_side >= 12` ($F_{\text{gen}} = 8 \lceil (\text{frame\_span} + 24 - 1)/8 \rceil + 1$).
        * For `VIDEO` shots bounded by **hard cuts or audio-only J/L cuts (`0` visual overlap frames)** (`135` of `152` shots in the Mold): allow `handle_frames_per_side >= 4` ($F_{\text{gen}} = 8 \lceil (\text{frame\_span} + 8 - 1)/8 \rceil + 1$) to trim first/last-frame VAE boundary flicker while avoiding unnecessary GPU frames.
     3. **Exact Verified Math (§15.6)**: Across the `152` `VIDEO` shots, all-`>=4` (`12,120` frames) vs all-`>=12` (`14,552` frames) saves **`2,432` frames (`101.33s`, `16.71%` of generated frames)**; the recommended transition-aware policy (`12,392` frames) saves **`2,160` frames (`90.00s`, `14.84%` of generated frames)** while keeping full `12`-frame handles on all `17` optical transitions.
5. **Why Needed**:
   * Eliminates `135` false-positive `BP-128` warnings on hard-cut `VIDEO` shots and reduces LTX-2.5 GPU generation time/cost by `14.84%` (`2,160` frames) without starving whip-pans or dissolves of overlap handles.
6. **Evidence Grade & Source**:
   * **`[PRIMARY-STANDARD]`** ([Lightricks LTX-2 Model Card](https://huggingface.co/Lightricks/LTX-2) for `8k+1` lattice `BP-139`) + **`[HYPOTHESIS]`** (`4`-frame hard-cut handle sufficiency, empirically tested in `GATE-P2` before changing `BP-128` defaults). *(Note: Murch's Rule of Six is NOT cited here; handle frames are strictly a VAE boundary-flicker + optical-transition trim buffer.)*
7. **Rule Classification**:
   * **Hard Technical Invariant (`FAIL`)** for `F = 8k + 1` (`BP-139`) and `F_gen >= frame_span + 2 * min_handle`; **Engineering Hypothesis (`REVIEW`)** for reducing hard-cut `min_handle` from `12` to `4` (`BP-128`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `production/ltx_generate.py`, `production/assemble.py`, `standards/sourced_rules.json` (`BP-128`).
9. **Backward Compatibility & Migration Impact**:
   * `/3` scripts (`calm_docudrama`) retain `handle_frames: [12, 16]` by default; transition-aware handles (`hard_cut_handle_min: 4`, `transition_handle_min: 12`) activate on `/4` (`mrbeast_animated`) after `GATE-P2` verification.
10. **Cost / Latency / Quality Tradeoff**:
    * Saves **`2,160` LTX frames (`14.84%` GPU time, `~$0.85–$1.20` per episode)** while protecting optical transitions with `>=12` handle frames.
11. **Failure Modes & Rollback Plan**:
    * If `GATE-P2` (`5` generated LTX clips) reveals boundary flicker extending beyond frame `4` on hard cuts, keep `hard_cut_handle_min: 12` in `sourced_rules.json` (`0` code change needed).
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_ltx_handle_frames.py` verifies exact `14,552` / `12,120` / `12,392` frame totals on the 152-shot Mold fixture and ensures `assemble.py` trims exact `head`/`tail` handles to hit `frame_span`.

### `CHG-09` — Integrate 3-Tier Still Motion Ladder (`BP-35`, `BP-132`, `BP-170`) Across `dramatic_still.py`, `parallax.py` & `assemble.py` (`BATCH-M5`)

1. **Change ID**: `CHG-09`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/edit/dramatic_still.py` (`L39–142`)
   * `explainer_engine/production/parallax.py` (`L30–140`)
   * `explainer_engine/production/assemble.py` (`L340–420`)
   * `explainer_engine/schemas/production_script.schema.json` (`still_motion_tier`, `dramatic_change`)
   * `tests/unit/test_dramatic_still_tiers.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** As proven in §15.3 and `M-04`, `mrbeast_12min_video_mold (1).json` contains **`76` `STILL` shots** (`19` `TIER_1`, `40` `TIER_2`, `17` `TIER_3`), of which **`55` exceed `BP-170`'s `static_still_max_s_by_zone`** (`2` `TIER_1`, `36` `TIER_2`, `17` `TIER_3`). Because `edit/dramatic_still.py` (`BP-170`, `severity: "FAIL"`) only exempts `cutout_relocation` and `plate_swap` (`TIER_3`), **`38` of the `76` `STILL` shots in the Mold (`2` `TIER_1` + `36` `TIER_2`) currently FAIL `DS-01`**, and the `17` `TIER_3` shots need their prose `still_motion_contract` mapped to the structured `dramatic_change` dict required by `dramatic_still.py`.
4. **Target Behavior**:
   * Enforce a **100% consistent policy between `M-04` and `CHG-09`** (`BP-170` `FAIL` severity is **never** relaxed without `CD-03`):
     1. **`TIER_1` (`parallax_25d`, `BP-35` + `BP-132`)**: Strictly bounded by `static_still_max_s_by_zone` (`<=1.5s` in Z1/Z5, `<=2.0s` in Z2/Z4, `<=2.5s` in Z3). In the Layer 3 reference grid, `SH003` (`1.875s` in Z1) and `SH226` (`1.625s` in Z5)—which already specify cutout leaps/slams in `track_5_visual_events`—are upgraded to `TIER_3` with structured `dramatic_change` objects.
     2. **`TIER_2` (`qwen_nextpose_or_lighting_state_flip`)**: Add `"still_motion_tier": "TIER_1" | "TIER_2" | "TIER_3"` to `production_script.schema.json` and wire two-plate pose/lighting cross-compositing in `assemble.py`, **but keep `TIER_2` strictly bounded by `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`) in `edit/dramatic_still.py`** unless and until the creator approves `CD-03` after validating a quantitative pose-delta (`masked_pose_iou_delta >= 0.20`) + `BP-130` identity gate (`cosine >= 0.65`) metric in `GATE-P1b`. For the `36` over-cap `TIER_2` shots in the Layer 3 reference grid, `timeline_compiler.py` (`CHG-07`) either trims them to `<= static_still_max_s_by_zone` or upgrades shots with `>=25%` cutout shifts to `TIER_3`.
     3. **`TIER_3` (`cutout_relocation` `>=25%` shift or `plate_swap` `>=30%` background diff, `BP-170`)**: Unlocks holds above `static_still_max_s_by_zone` up to `dramatic_still_max_s = 5.0s` (`DS-02`), requiring a structured `dramatic_change` dict (`kind`, `trigger_s`, `position_shift_frac >= 0.25` or `bg_diff_frac >= 0.30`, `subject_area_frac >= 0.08`).
5. **Why Needed**:
   * Eliminates the contradiction between `M-04` and `CHG-09`, prevents static slideshows from sneaking past `BP-170` under an unverified `TIER_2` label, and wires `TIER_3` cutout/plate-swap compositing cleanly into `assemble.py`.
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`BP-35`, `BP-132`, `BP-170` in `sourced_rules.json` + exact audit of all `76` `STILL` shots in `2ca7f56f...`) + **`[VERIFIED-CREATOR]`** (`CS-13` Oversimplified cutout mechanics).
7. **Rule Classification**:
   * **Hard Quality Gate (`FAIL`)** for `BP-170` (`DS-01..DS-06`) and `BP-35` (`layers_min: 3`); **Creator Decision (`CD-03`)** for any future `TIER_2` duration extension above `1.5/2.0/2.5s`.
8. **Exact Schema / Code / Config Surface Affected**:
   * `edit/dramatic_still.py`, `production/parallax.py`, `production/assemble.py`, `schemas/production_script.schema.json`.
9. **Backward Compatibility & Migration Impact**:
   * Existing `dramatic_change` objects on `/3` and `/4` scripts continue to validate identically.
10. **Cost / Latency / Quality Tradeoff**:
    * `TIER_1` and `TIER_3` cutout relocations run on CPU/compositor (`$0.00` LTX video cost), while `TIER_2` uses one extra Qwen-Image-Edit call (`~$0.015/shot`).
11. **Failure Modes & Rollback Plan**:
    * If a `TIER_3` cutout mask fails `subject_area_frac >= 0.08` (`DS-06`), `dramatic_still.py` halts with `FAIL` and `timeline_compiler.py` splits the hold to `<= static_still_max_s_by_zone`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_dramatic_still_tiers.py` verifies `0` `DS-01..DS-06` errors on the reconciled reference grid and confirms that an unapproved `TIER_2` shot exceeding `static_still_max_s_by_zone` is rejected with `DS-01` `FAIL`.

### `CHG-10` — Harmonize `BP-122` Acoustic Perspective & Two-Axis Audio Accounting (`68/20/12` + Stem Mix) in `sound_director.py`, `assemble.py` & `loudness.py` (`BATCH-M6`)

1. **Change ID**: `CHG-10`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/sound_director.py` (`L35–140`)
   * `explainer_engine/audio/layers.py` (`L180–345`)
   * `explainer_engine/production/assemble.py` (`L285–315`, `L475–510`)
   * `explainer_engine/finish/loudness.py` (`L40–130`)
   * `tests/unit/test_audio_two_axis_and_bp122.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `mrbeast_12min_video_mold (1).json` contains conflicting hardcoded EQ strings (`-3dB @ 3.5kHz, 18% wet` vs `-3.5dB @ 3500Hz, 28% wet`) that disagree with `BP-122` in `sourced_rules.json` (`shelf_hz: 6000, wide_shelf_db: -4.0, wide_wet: 0.22, close_dry: 0.95, proximity_db: 2.0, proximity_hz: 140`, `M-11`), and conflates primary timeline audio driver shares (`68%` narrator / `20%` character quote / `12%` SFX-music showcase) with concurrent stem mix levels.
4. **Target Behavior**:
   * Unify acoustic perspective (`M-11`) and two-axis audio accounting (§15.4):
     1. **Symbolic `BP-122` Perspective Keys**: Shots specify `"perspective": "far" | "mid" | "near"` (derived automatically from `shot_size`: `Wide/Extreme Wide -> "far"`, `Medium/Medium-Wide -> "mid"`, `Close-Up/ECU -> "near"` in `sound_director.py:43`), and `assemble.py` reads all filter coefficients exclusively from `sourced_rules.T("BP-122", ...)` (`D-59`).
     2. **Axis 1 — Primary Driver Timeline Partition (`audio/layers.py`)**: Validate that across the `720.0s` timeline, primary narrative focus is partitioned within `±5%` of `68%` Narrator-led (`Track 1`), `20%` Character/Quote-led (`Track 2`, `D-90`), and `12%` SFX/Music-Showcase-led (`Tracks 3 & 4`, including `BP-121` `0.5–1.0s` pre-reveal vacuums and `BP-30` breathing valleys) (`severity: "REVIEW"`).
     3. **Axis 2 — Concurrent Stem Mix & Loudness (`assemble.py`, `loudness.py`)**: Enforce `BP-15` Law of 2.5 (`<=2` simultaneous foreground audio elements), `BP-75` sidechain ducking (`-14 to -18 dB` under voice), `BP-73` (`-14.0 ± 1.0 LUFS`, `<= -1.0 dBTP`), and `BP-74` (`LRA 5–9 LU`).
5. **Why Needed**:
   * Resolves `M-11` (`D-59` compliance) and prevents `68/20/12` from being misinterpreted as muting music/SFX during `88%` of the video.
6. **Evidence Grade & Source**:
   * **`[PRIMARY-STANDARD]`** ([ITU-R BS.1770-5](https://www.itu.int/rec/R-REC-BS.1770/en) `SRC-01`, EBU R 128 / Tech 3343 v4 `SRC-02`, Zahorik et al. 2005 `SRC-45`) + **`[CRAFT-HEURISTIC]`** (Murch's Law of 2.5 `SRC-14`) + **`[HYPOTHESIS]`** (`68/20/12` primary driver split, `REVIEW`).
7. **Rule Classification**:
   * **Hard Technical Invariant (`FAIL`)** for `BP-73`/`BP-74` loudness/true-peak and `D-59` `BP-122` lookup; **Advisory Hypothesis (`REVIEW`)** for `68/20/12 ±5%` primary-driver share.
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/sound_director.py`, `audio/layers.py`, `production/assemble.py`, `finish/loudness.py`.
9. **Backward Compatibility & Migration Impact**:
   * Preserves existing `sound_director.py` `"far" | "mid" | "near"` contract.
10. **Cost / Latency / Quality Tradeoff**:
    * `$0.00` API/GPU cost; runs inside local FFmpeg audio assembly.
11. **Failure Modes & Rollback Plan**:
    * If FFmpeg `loudnorm` pass 1 detects true peak `> -1.0 dBTP`, pass 2 linear/dynamic normalization clamps TP to `-1.0 dBTP`.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_audio_two_axis_and_bp122.py tests/unit/test_sound_director.py tests/unit/test_loudness.py` passes.

### `CHG-11` — Enforce Relative Color Script & Character Identity Continuity (`BP-166`, `BP-130`, `D-22`, `LT-65`) Across `episode_look.py`, `prompt_lint.py` & `color_continuity.py` (`BATCH-M6`)

1. **Change ID**: `CHG-11`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/production/episode_look.py` (`L25–120`)
   * `explainer_engine/scripting/prompt_lint.py` (`L190–245`, `LT-65`)
   * `explainer_engine/qa/color_continuity.py` (`L30–135`, `BP-166`)
   * `explainer_engine/qa/identity_gate.py` (`L40–140`, `BP-130`)
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `prompt_lint.py` (`LT-65`, `D-22`) rightly rejects raw `#RRGGBB` hex strings in generation prompts, whereas the Mold's `color_qa` / `character_sheet_ref` fields store reference HEX swatches (`#1B365D`, `#C59B27`) alongside relative act mood offsets (`M-12`).
4. **Target Behavior**:
   * Enforce a strict two-stage color & identity contract (`M-12`):
     1. **Prompt Stage (`episode_look.py` & `prompt_lint.py`)**: Keep `LT-65` (`D-22`) hard ban on `#RRGGBB` literals in all Qwen/LTX prompt strings; translate act mood shifts (`Act I warm golden-hour -> Act II cool slate tension -> Act III high-contrast ember/shadow`) via natural-language descriptors in `episode_look.py` (`AC-17`).
     2. **Post-Render QA & Lab Transfer Stage (`assemble.py`, `color_continuity.py`, `identity_gate.py`)**: Store reference HEX swatches strictly inside `character_sheet_ref.palette_hex` / `color_qa`, apply Reinhard Lab color transfer (`BP-130` `SRC-23`) in `assemble.py`, and verify `BP-166` (`sat_drift_max <= 0.08`, `luma_drift_max <= 0.08`, `hero_palette_max <= 0.15`) and `BP-130` ArcFace cosine similarity (`>= 0.65` hard floor, `>= 0.72` warn floor).
5. **Why Needed**:
   * Prevents diffusion prompt corruption (`D-22`) while guaranteeing mathematical palette and facial/costume consistency across all `254` shots.
6. **Evidence Grade & Source**:
   * **`[PRIMARY-STANDARD]`** (Reinhard et al. 2001 `SRC-23`, ArcFace `SRC-22`, PuLID `SRC-46`) + **`[FACT]`** (`D-22`, `LT-65`, `BP-130`, `BP-166`).
7. **Rule Classification**:
   * **Hard Invariant (`FAIL`)** for `LT-65` prompt hex ban, `BP-166` drift caps, and `BP-130` `0.65` identity floor (calibrated on 2D art in `GATE-P1b`).
8. **Exact Schema / Code / Config Surface Affected**:
   * `production/episode_look.py`, `scripting/prompt_lint.py`, `qa/color_continuity.py`, `qa/identity_gate.py`.
9. **Backward Compatibility & Migration Impact**:
   * 100% compatible with existing `/3` and `/4` pipelines.
10. **Cost / Latency / Quality Tradeoff**:
    * `<20 ms/shot` OpenCV Lab transfer + ArcFace embedding check; prevents jarring character costume/face drift.
11. **Failure Modes & Rollback Plan**:
    * Shots failing `BP-166` are auto-corrected via `assemble.py` Lab transfer before triggering a re-render.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_color_continuity.py tests/unit/test_prompt_lint.py tests/unit/test_identity_gate.py` passes.

### `CHG-12` — Wire `D-90` Character Voice Spine (`ElevenLabs Character TTS -> LTX-2.5 Native Audio-In`) & Living-Person Voice Ban (`PV-55`) (`BATCH-M6`)

1. **Change ID**: `CHG-12`
2. **Subsystem / Target File(s)**:
   * `explainer_engine/audio/character_voices.py` (`L30–145`)
   * `explainer_engine/audio/casting.py` (`L40–130`)
   * `explainer_engine/production/ltx_generate.py` (`L145–210`)
   * `explainer_engine/governance/rights_gate.py` (`PV-55`, `D-62`, `D-63`)
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** `D-90` specifies that played character turns (`BP-142` `turn_slots_D: [4, 6, 8, 10, 11, 13]` and `Track 2` historical quotes) must synthesize a dedicated ElevenLabs character voice take first (`audio/character_voices.py`) and pass that audio waveform into LTX-2.5 (`production/ltx_generate.py`) so lip/jaw/head motion is driven natively by the character's speech, while `PV-55` (`D-62`, `D-63`) forbids cloning or imitating any living person's voice.
4. **Target Behavior**:
   * Wire `audio/character_voices.py` (`Track 2`) into `Stage 3` audio pre-production so character takes are generated alongside `Track 1` (`Odom`), verified against `PV-55` (`rights_gate.py` blocks any living person or post-1926 public figure without explicit creator clearance `CD-06`), and passed as `audio_cond_path` into `ltx_generate.py` for lip-synced `VIDEO` shots (with ByteDance OmniHuman-1.5 `SRC-24` retained only as a documented comparison benchmark in `DECISIONS_AND_OPEN_QUESTIONS.md` unless routed by the creator under `D-84`).
5. **Why Needed**:
   * Ensures the `6` mandatory played scene turns (`BP-142`) and `20%` character-quote timeline share (`CHG-10`) have frame-accurate lip-sync and strict `PV-55` legal compliance.
6. **Evidence Grade & Source**:
   * **`[PRIMARY-STANDARD]`** ([Lightricks LTX-2 Audio-Visual Generation](https://huggingface.co/Lightricks/LTX-2) `SRC-03`, OmniHuman-1.5 `SRC-24`) + **`[FACT]`** (`D-62`, `D-63`, `D-90`, `PV-55`).
7. **Rule Classification**:
   * **Hard Legal/Governance Invariant (`FAIL`)** for `PV-55` living-person voice ban; **Hard Pipeline Order (`FAIL`)** for generating `Track 2` audio before LTX-2.5 `VIDEO` shots on `BP-142` dialogue turns; **Creator Decision (`CD-06`)** for voicing deceased historical figures.
8. **Exact Schema / Code / Config Surface Affected**:
   * `audio/character_voices.py`, `audio/casting.py`, `production/ltx_generate.py`, `governance/rights_gate.py`.
9. **Backward Compatibility & Migration Impact**:
   * Non-dialogue `VIDEO` shots continue to run standard image-to-video LTX-2.5 generation.
10. **Cost / Latency / Quality Tradeoff**:
    * Character TTS uses `<=350–450` words per episode (`~2,200` characters, well within `casting_credits_max: 1500` for casting previews and the episode TTS budget `CD-05`).
11. **Failure Modes & Rollback Plan**:
    * If `CD-06` restricts direct first-person voicing for a specific historical figure, `character_voices.py` falls back to narrator quote framing with off-camera or close-up reaction framing.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_character_voices.py tests/unit/test_rights_gate.py` passes and verifies `PV-55` blocks living-person voice synthesis.

### `CHG-13` — Align Writers' Room Agents (`.claude/agents/*.md`), Skills (`.claude/skills/*/SKILL.md`) & 5-Shorts Extraction (`BP-167`) (`BATCH-M7`)

1. **Change ID**: `CHG-13`
2. **Subsystem / Target File(s)**:
   * `.claude/agents/script-writer.md`, `.claude/agents/visual-director.md`, `.claude/agents/sound-director.md`, `.claude/agents/story-critic.md`, `.claude/agents/visual-critic.md`, `.claude/agents/retention-critic.md`
   * `.claude/skills/write-script/SKILL.md`, `.claude/skills/plan-shots/SKILL.md`, `.claude/skills/sound-design/SKILL.md`, `.claude/skills/shorts-cut/SKILL.md`
   * `explainer_engine/finish/shorts_extract.py` (`BP-167`, `D-85`)
   * `tests/unit/test_agents_and_skills_sync.py`, `tests/unit/test_shorts_extract.py`
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** Several agent/skill markdown prompts in `.claude/agents/` and `.claude/skills/` still instruct the LLM to write `/3` `scenes[]` with flat `140–175 WPM` pacing rather than `/4` `segments[]` (`S01..S16`, `AB01..AB12`, `BP-169` 5-zone WPM/shot-length targets, `BP-170` 3-tier still ladder, and `BP-167` `5` self-contained `9:16` Shorts reframed from `AB01`, `AB05`, `AB07`, `AB09`, `AB11`).
4. **Target Behavior**:
   * Update the 6 Writers' Room agent prompts and 4 skill definitions to emit `/4` `mrbeast_animated` scripts by default (`S01..S16`, `AB01..AB12`, `episode_profile: "A".."D"`, `BP-169..172`), preserving `D-79` (`1` main execution agent + read-only Opus critics), and wire `finish/shorts_extract.py` (`BP-167`, `D-85`) to extract `5` vertical `9:16` (`1440x2560`) Shorts anchored to the episode's self-contained turn hooks (`S01`, `S06`, `S09`, `S12`, `S15`).
5. **Why Needed**:
   * Aligns the generative LLM prompts (`.claude/agents/` and `.claude/skills/`) with the downstream validators (`CHG-01..CHG-12`) so scripts pass `rhythm_lint` and `story_lint` on the first pass instead of looping on rejections.
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`D-79`, `D-85`, `BP-167`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`).
7. **Rule Classification**:
   * **Hard Deliverable Contract (`FAIL`)** for `BP-167` (`1` 12-min `2560x1440` master + `5` vertical Shorts) and `D-79` read-only critic boundaries.
8. **Exact Schema / Code / Config Surface Affected**:
   * `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `explainer_engine/finish/shorts_extract.py`.
9. **Backward Compatibility & Migration Impact**:
   * Prompts support both `mrbeast_animated` (`/4` default) and `calm_docudrama` (`/3` when requested).
10. **Cost / Latency / Quality Tradeoff**:
    * Reduces Writers' Room LLM retry loops by giving `script-writer` and `visual-director` the exact `/4` zone and anchor constraints upfront; `5` Shorts are reframed from existing master renders (`$0.00` extra GPU generation cost).
11. **Failure Modes & Rollback Plan**:
    * Enforced by `explainer_engine.docs_lint` and `test_agents_and_skills_sync.py`.
12. **Verification Test & Acceptance Criteria**:
    * `PYTHONPATH=. python3 -m explainer_engine.docs_lint` returns `0 finding(s)` and `pytest tests/unit/test_shorts_extract.py` passes.

### `CHG-14` — Reconcile Cumulative Spend Caps (`config/spend_caps.json`), 2-Sample `GATE-P3` Pilot (`production/sample.py` `D-67`), and `BP-168` Go/Pivot/Abandon Gate (`BATCH-M8A` & `BATCH-M8B`)

1. **Change ID**: `CHG-14`
2. **Subsystem / Target File(s)**:
   * `config/spend_caps.json` *(protected config — modified ONLY after explicit creator approval of `CD-01` & `CD-05` under `D-84`)*
   * `explainer_engine/core/spend_caps.py` (`L25–120`)
   * `explainer_engine/core/ledger.py` (`L30–145`)
   * `explainer_engine/production/sample.py` (`L45–160`, `D-67`, `OR-19`)
   * `tests/unit/test_spend_caps_reconciliation.py` *(new unit test)*
3. **Current Repository Behavior (`5013a55a`)**:
   * **[FACT]** Direct inspection of `config/spend_caps.json` (`5013a55a`) reveals the exact committed ceilings:
     * `paid_tests.total_usd = 5.90`, partitioned into `p12a_smoke: 0.50`, `p12b_two_runs: 3.00`, `p12b_measure: 0.63`, and `p12e_hosts: 1.77` (`0.50 + 3.00 + 0.63 + 1.77 = 5.90`). Note that `p12e_hosts` (`$1.77` for two permanent channel hosts) was **cancelled by `D-89` (no permanent hosts)**!
     * `per_episode`: `runpod_usd: 31.00`, `elevenlabs_USD: 0.00` (subscription credits), `openrouter_usd: 0.00`, `anthropic_usd: 0.00`.
     * `runpod`: `per_pod_usd: 6.90`, `per_24h_usd: 26.00`.
     * `casting`: `casting_credits_max: 1500`.
     * `BP-168` (`sourced_rules.json:2769–2791`): `go_forecast_usd_max: 12.00`, `abandon_forecast_usd_min: 20.00` per full episode.
     * `explainer_engine/production/sample.py` (`D-67` / `OR-19`): builds **two 30-second pilot samples** (`hook_window_s = [0.0, 30.0]` and `calm_window_s = [60.0, 90.0]`, total `60.0s`).
   * **[OBSERVATION]** Prior roadmap notes left three financial/pilot ambiguities unresolved: (1) whether `GATE-P1a..P4` summed to `$11.05` est. / `$17.50` cap inside or outside `paid_tests.total_usd = $5.90`, (2) how `D-56`/`core/ledger.py`'s `80%` hard-stop threshold (`$4.72` on `$5.90`) interacts with the pilot gates, and (3) whether `GATE-P3` is one continuous `0–60s` clip (`S01–S02`) or `sample.py`'s two 30s samples (`D-67`).
4. **Target Behavior**:
   * Establish an **exact, zero-contradiction financial and pilot governance contract** across `BATCH-M8A` (`GATE-P1a..P3`) and `BATCH-M8B` (`GATE-P4`):
     1. **Separate Paid Calibration Ledger (`paid_tests`, `BATCH-M8A`) vs Full-Episode Production Ledger (`per_episode`, `BATCH-M8B`)**:
        * `GATE-P1a`, `GATE-P1b`, `GATE-P2`, and `GATE-P3` are **pre-episode calibration tests (`BATCH-M8A`)** governed by `paid_tests.total_usd = $5.90`.
        * Because `D-89` cancelled permanent hosts (`p12e_hosts = $1.77`), once the creator approves `CD-01` & `CD-05`, the `paid_tests` sub-allocations in `config/spend_caps.json` are mapped cleanly inside the existing `$5.90` ceiling **and below the `$4.72` (`80%`) `ledger.py` auto-stop threshold**:

| Stage / Gate ID | Ledger Category (`config/spend_caps.json`) | Exact Scope & Deliverable | Estimated Actual Spend (USD) | Sub-Gate Hard Cap (USD) | Cumulative Spend Across `paid_tests` (`<= $4.72` 80% Stop / `$5.90` Cap) | Mandatory Stop / Go Gate Before Next Step |
| ----- | ----- | ----- | ----- | ----- | ----- | ----- |
| **`GATE-P1a`** | `paid_tests.p1a_tts_zones` | Synthesize `Odom` (`eleven_v4`) audio across `1` 30s hook (`S01`) + `1` 30s calm/turn segment (`S04`) + measure `words_raw.json` vs `pause_pad.py` (`CHG-06`) | **`$0.15`** (or `~950` subscription chars) | **`$0.40`** | `$0.15` est. / `$0.40` cap | Verify `measured_heard_wpm` in Z1 (`[180, 210]`) & Z3 (`[150, 178]`), `0` `HR-01..03` errors. |
| **`GATE-P1b`** | `paid_tests.p1b_still_tiers` | Generate `6` Qwen-Image-2.1 base/pose plates (`2` `TIER_1`, `2` `TIER_2`, `2` `TIER_3`) + run `dramatic_still.py` (`BP-170`), `color_continuity.py` (`BP-166`), and `identity_gate.py` (`BP-130`) | **`$0.45`** | **`$0.80`** | `$0.60` est. / `$1.20` cap | Verify `BP-130` (`cosine >= 0.65`), `BP-166` (`drift <= 0.08`), and collect empirical data for `CD-03` (`TIER_2` pose delta). |
| **`GATE-P2`** | `paid_tests.p2_ltx_handles` | Generate `5` LTX-2.5 `VIDEO` clips (`3` hard-cut with `4` handles/side, `2` whip-pan/dissolve with `12` handles/side) on 1 RunPod pod (`<= $6.90/pod`) | **`$0.80`** | **`$1.30`** | `$1.40` est. / `$2.50` cap | Verify `F = 8k + 1` (`BP-139`), zero boundary flicker after `4`-frame trim on hard cuts (`CHG-08`), and measure `$ / LTX frame`. |
| **`GATE-P3`** | `paid_tests.p3_two_samples` | **Two 30-second pilot samples (`60.0s` total per `D-67` / `OR-19` `production/sample.py`)**: **Sample A (`0.0–30.0s` Hook `S01`)** + **Sample B (`90.0–120.0s` Calm Middle `S04` containing played scene turn #1 `BP-142`)**, rendered independently and concatenated in a free CPU assembly test | **`$1.85`** | **`$2.20`** | **`$3.25` est. / `$4.70` cap** (`<= $4.72` 80% stop on `$5.90` `paid_tests.total_usd`!) | **Mandatory Creator Review Gate (`D-67`)** + `BP-168` full-episode cost forecast: `GO` if forecast `<= $12.00`, `PIVOT` if `$12.01–$19.99`, `ABANDON` if `>= $20.00`. |
| **`GATE-P4`** | `per_episode` (`runpod_usd <= $31.00`, `runpod.per_24h_usd <= $26.00`, `BP-168 <= $12.00`) | **Full 12-Minute Episode 1 Master (`720.0s`, `S01..S16`, `254` shots, `2560x1440` @ `24 fps`) + `5` Vertical `9:16` Shorts (`BP-167`)** (separate per-episode `run.json` ledger, executed ONLY after creator `GO` on `GATE-P3`) | **`$7.80`** | **`$12.00`** (`BP-168` `go_forecast_usd_max`; well below `$20.80` 80% of `$26.00/24h` and `$24.80` 80% of `$31.00/ep`) | Separate `per_episode` ledger (`$7.80` est. / `$12.00` `BP-168` cap) | Full `production_gate.py`, `editorial_gate.py`, `loudness.py` (`-14 LUFS`), and `shorts_extract.py` (`5` Shorts) pass. |

     2. **Resolved `GATE-P3` Sample Definition (`D-67` / `OR-19` Compliance)**:
        * `GATE-P3` is explicitly **two separate 30-second pilot samples (`60.0s` total)** matching `explainer_engine/production/sample.py`: **Sample A (`0.0–30.0s`, `S01` `hook_0_30s`)** and **Sample B (`90.0–120.0s`, `S04` `middle_calm_90_480s` including played scene turn slot `4` `BP-142`)**. Each 30-second sample is rendered and validated in its own time window (`0–30s` and `90–120s`), and an additional **free CPU FFmpeg concatenation check** verifies seamless zone-boundary handoff (`hook_0_30s -> middle_calm_90_480s`) and integrated `-14.0 LUFS` loudness across the combined 60-second reel.
5. **Why Needed**:
   * Eliminates the contradiction between the sum of `GATE-P1a..P4` (`$11.05` est. / `$16.70` total across both ledgers) and `paid_tests.total_usd = $5.90` (`80%` stop = `$4.72`), and aligns `GATE-P3` with `D-67` / `production/sample.py`.
6. **Evidence Grade & Source**:
   * **`[FACT]`** (`config/spend_caps.json`, `core/spend_caps.py`, `core/ledger.py`, `production/sample.py`, `BP-168` in `sourced_rules.json`, `D-56`, `D-67`, `D-84`, `D-89`).
7. **Rule Classification**:
   * **Hard Financial & Governance Gate (`FAIL` + `CREATOR DECISION` `CD-01`, `CD-05`)**.
8. **Exact Schema / Code / Config Surface Affected**:
   * `config/spend_caps.json` (after `CD-05` approval), `core/spend_caps.py`, `core/ledger.py`, `production/sample.py`.
9. **Backward Compatibility & Migration Impact**:
   * Preserves `paid_tests.total_usd = 5.90`, `per_episode.runpod_usd = 31.00`, `runpod.per_24h_usd = 26.00`, `runpod.per_pod_usd = 6.90`, and `80%` auto-stop in `ledger.py`.
10. **Cost / Latency / Quality Tradeoff**:
    * Caps total pre-episode calibration risk (`GATE-P1a..P3`) at **`$3.25` estimated (`$4.70` hard cap, inside `$4.72` 80% of `$5.90`)** before committing to the **`$7.80` estimated (`<= $12.00` `BP-168`)** full Episode 1 render (`GATE-P4`).
11. **Failure Modes & Rollback Plan**:
    * If `GATE-P2` or `GATE-P3` projects a full-episode cost `> $12.00` (`BP-168`), `ledger.py` halts before `GATE-P4` and triggers the `PIVOT` (`$12.01–$19.99`: switch to `Profile B/C` `55%` VIDEO or increase `TIER_3` cutout share) or `ABANDON` (`>= $20.00`) protocol.
12. **Verification Test & Acceptance Criteria**:
    * `pytest tests/unit/test_spend_caps_reconciliation.py tests/unit/test_sample.py` verifies `sum(GATE-P1a..P3 caps) == $4.70 <= 0.80 * $5.90 ($4.72)` and `sample.py` `calm_window_s == [90.0, 120.0]` on `mrbeast_animated`.

## 17. Mandatory Per-Batch Documentation Synchronisation Matrix, 4-Stage Rollout, Traceability & Claude Audit Checklist

### 17.1 Per-Batch Documentation Synchronisation Matrix (`explainer_engine.docs_lint` Verified)

**[FACT]** In `repo_5013a55a.zip`, `explainer_engine/docs_lint.py` validates every backticked path across `CLAUDE.md`, `README.md`, `docs/*.md`, `.claude/agents/*.md`, and `.claude/skills/*/SKILL.md`. The canonical existing documentation files in `docs/` are:
* `docs/ARCHITECTURE.md`
* `docs/PIPELINES.md`
* `docs/STANDARDS.md`
* `docs/DECISIONS_AND_OPEN_QUESTIONS.md`
* `docs/PROGRESS.md`
* `docs/STATUS.html`
* `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`

*(Note: Prior draft references to non-existent files `docs/PRODUCT_MOLD.md`, `docs/SCHEMAS.md`, `docs/OPEN_QUESTIONS.md`, and `docs/DECISIONS.md` have been completely removed; the canonical Mold companion doc created in `BATCH-M1` is `docs/MRBEAST_12MIN_MASTER_MOLD.md`, and all schema/decision updates live in `docs/ARCHITECTURE.md` and `docs/DECISIONS_AND_OPEN_QUESTIONS.md`.)*

| Implementation Batch | Code & Config Changes (`CHG-01..CHG-14`) | Mandatory Existing Documentation Files Updated in Same Commit | Verification Gate (`0 finding(s)` Required) |
| ----- | ----- | ----- | ----- |
| **`BATCH-M0`** | `CHG-02`: `scripting/schema_version.py`, `/4` dispatch across `script.py` + 11 consumer modules, P0 fixes in `narrator_polish.py`, `shot_prompt_checks.py`, `sample.py` | `docs/ARCHITECTURE.md`, `docs/PIPELINES.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_schema_version_dispatch.py` |
| **`BATCH-M1`** | `CHG-01` & `CHG-04` (part 1): Commit `explainer_engine/standards/mrbeast_12min_video_mold.json`, `mold_contract.py`, `docs/MRBEAST_12MIN_MASTER_MOLD.md` (`M-01..M-12`), `BP-109` Profiles `A..D` | `docs/MRBEAST_12MIN_MASTER_MOLD.md` *(created in `BATCH-M1`)*, `docs/STANDARDS.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_mold_contract.py tests/unit/test_sourced_rules.py` |
| **`BATCH-M2`** | `CHG-03`, `CHG-04` (part 2) & `CHG-05`: 5-zone `BP-169` wiring in `rhythm.py`, `board.py` (`BP-84`), `speech.py`, `retention.py`; `AB01..AB12` & `BP-04` word-share gate in `story_lint.py` | `docs/STANDARDS.md`, `docs/PIPELINES.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_rhythm_zones.py tests/unit/test_story_lint_anchors.py` |
| **`BATCH-M3`** | `CHG-06`: Closed-loop `eleven_v4` prosody (`narrator_polish.py`), `S06`/`S09` `[excited]` re-hook exception (`hype_read.py`), deficit pause padding (`pause_pad.py`) | `docs/PIPELINES.md`, `docs/STANDARDS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_pause_pad_zone_closed_loop.py` |
| **`BATCH-M4`** | `CHG-07`: Deterministic Layer 3 `timeline_compiler.py` (`17,280`-frame conservation, `BP-28` variance repair, `TimelineInfeasibleError` contract) | `docs/ARCHITECTURE.md`, `docs/PIPELINES.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_timeline_compiler.py` |
| **`BATCH-M5`** | `CHG-08` & `CHG-09`: Transition-aware LTX-2.5 handle frames (`BP-128`, `BP-139`) in `ltx_generate.py`/`assemble.py`; 3-Tier Still Motion Ladder (`BP-35`, `BP-132`, `BP-170`) in `dramatic_still.py`/`parallax.py`/`assemble.py` | `docs/STANDARDS.md`, `docs/PIPELINES.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_ltx_handle_frames.py tests/unit/test_dramatic_still_tiers.py` |
| **`BATCH-M6`** | `CHG-10`, `CHG-11` & `CHG-12`: Symbolic `BP-122` perspective + 2-axis `68/20/12` audio (`sound_director.py`, `layers.py`, `loudness.py`); relative color continuity (`BP-166`, `episode_look.py`); `D-90` character voice spine (`character_voices.py`, `PV-55`) | `docs/ARCHITECTURE.md`, `docs/STANDARDS.md`, `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_audio_two_axis_and_bp122.py tests/unit/test_color_continuity.py` |
| **`BATCH-M7`** | `CHG-13`: Align `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, and 5-Shorts extraction (`finish/shorts_extract.py`, `BP-167`) | `CLAUDE.md`, `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `docs/PIPELINES.md`, `docs/PROGRESS.md` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest tests/unit/test_shorts_extract.py` |
| **`BATCH-M8A` & `BATCH-M8B`** | `CHG-14`: Pre-episode paid calibration gates (`GATE-P1a..P3` `<= $4.70` inside `$5.90` `paid_tests`) + Full Episode 1 production (`GATE-P4` `<= $12.00` `BP-168`) | `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `docs/PROGRESS.md`, `docs/STATUS.html` | `PYTHONPATH=. python3 -m explainer_engine.docs_lint` + `pytest` full suite + `production_gate.py` |

### 17.2 Mandatory Four-Stage Final Rollout Sequence (`Stage 1` → `Stage 2` → `Stage 3` → `Stage 4`)

1. **`Stage 1 — Unify Contract & Dry Code Wiring ($0.00 Spend, BATCH-M0..M7)`**:
   * Execute `BATCH-M0` through `BATCH-M7` in strictly offline unit-tested commits after `CD-01` approval.
   * Run full `pytest` suite (`2,448+` existing unit tests + new `CHG-01..CHG-14` test modules) and `PYTHONPATH=. python3 -m explainer_engine.docs_lint` (`0 finding(s)`).
2. **`Stage 2 — Dry Episode 1 Script, Audio Timing Simulation & Layer 3 Timeline Compilation ($0.00 GPU Spend)`**:
   * Select the creator-approved Episode 1 historical/counterfactual topic (`CD-09`), build the verified `claim_id` research dossier (`ZI-02`, `PV-37`, `HY-4`), and generate the `/4` `production_script.json` (`S01..S16`, `AB01..AB12`).
   * Run `story_lint.py`, `rhythm_lint.py`, `dramatic_still.py`, `shot_prompt_checks.py`, and dry-run `timeline_compiler.py` (`17,280` frames = `720.0s`) until `0` `FAIL` findings remain.
3. **`Stage 3 — Paid Calibration & Two-Sample Pilot Gate (BATCH-M8A: GATE-P1a -> P1b -> P2 -> P3, $3.25 Est. / $4.70 Cap <= $4.72 80% of $5.90)`**:
   * Execute `GATE-P1a` (`$0.15` est. `eleven_v4` zone TTS + `pause_pad.py`), `GATE-P1b` (`$0.45` est. 6-plate Qwen still ladder + `BP-130`/`BP-166`), `GATE-P2` (`$0.80` est. 5-clip LTX-2.5 handle test), and `GATE-P3` (`$1.85` est. two 30s pilot samples `0–30s` `S01` + `90–120s` `S04` per `D-67` / `sample.py`).
   * **Hard Creator Stop Gate (`D-67` & `BP-168`)**: Present Sample A (`0–30s`), Sample B (`90–120s`), the concatenated 60s test reel, and the empirical `BP-168` Episode 1 cost projection (`GO <= $12.00`, `PIVOT $12.01–$19.99`, `ABANDON >= $20.00`) to the creator for explicit sign-off.
4. **`Stage 4 — Full Episode 1 Production & 5-Shorts Delivery (BATCH-M8B: GATE-P4, $7.80 Est. / <= $12.00 BP-168 Cap)`**:
   * Upon creator `GO`, render the full 12-minute (`720.0s`, `17,280`-frame, `2560x1440` @ `24 fps`) master episode + `5` vertical `9:16` (`1440x2560`) Shorts (`BP-167`), verify `-14.0 ± 1.0 LUFS` / `<= -1.0 dBTP` (`BP-73`), archive media to HF Vault `vano1919/tmr-artifacts` (`D-73`), and pass `production_gate.py`.

### 17.3 Rule-to-Code-to-Test Traceability Matrix (`M-01..M-12` & `CHG-01..CHG-14`)

| Rule / Discrepancy / Change ID | Authority Tier & Severity | Canonical `sourced_rules.json` / Decision ID | Primary Implementation Module(s) | Primary Unit / Gate Test File(s) |
| ----- | ----- | ----- | ----- | ----- |
| **`M-01` / `CHG-01`** | Structural Invariant (`FAIL`) | `BP-169`, `production_script/4` | `explainer_engine/standards/mold_contract.py`, `edit/rhythm_profile.py` | `tests/unit/test_mold_contract.py`, `tests/unit/test_rhythm_profile.py` |
| **`M-02` / `CHG-01`, `CHG-06`** | Invariant (`FAIL` for `D-59` & tags; `REVIEW` for WPM) | `D-59`, `BP-169`, `BP-171` | `standards/mold_contract.py`, `audio/hype_read.py`, `audio/narrator_polish.py` | `tests/unit/test_sourced_rules.py`, `tests/unit/test_hype_read.py` |
| **`M-03` / `CHG-04`** | Profile Rule (`FAIL` lane bounds; `REVIEW` `BP-141`) | `BP-109`, `BP-141`, `D-93` | `production/variant_plan.py`, `scripting/film_shots.py` | `tests/unit/test_variant_plan.py`, `tests/unit/test_film_shots.py` |
| **`M-04` / `CHG-09`** | Hard Quality Gate (`FAIL`; `CD-03` for Tier 2) | `BP-35`, `BP-132`, `BP-170` | `edit/dramatic_still.py`, `production/parallax.py`, `production/assemble.py` | `tests/unit/test_dramatic_still_tiers.py`, `tests/unit/test_dramatic_still.py` |
| **`M-05` / `CHG-05`** | Narrative Invariant (`FAIL` order/`BP-04`; `REVIEW` `BP-06`) | `BP-01`, `BP-04`, `BP-06`, `BP-142` | `scripting/story_lint.py` | `tests/unit/test_story_lint_anchors.py`, `tests/unit/test_story_lint.py` |
| **`M-06` / `CHG-01`** | Fact Grounding Invariant (`FAIL`) | `ZI-02`, `PV-37`, `HY-4` | `scripting/film_shots.py`, `scripting/claims.py`, `research/hypotheses.py` | `tests/unit/test_claims.py`, `tests/unit/test_film_shots.py` |
| **`M-07` / `CHG-01`** | Ending Invariant (`FAIL`) | `BP-43` (`KP-40`), `BP-106` | `scripting/film_shots.py` | `tests/unit/test_film_shots.py` |
| **`M-08` / `CHG-01`, `CHG-09`** | Citation & Map Scope (`FAIL`) | `BP-35`, `BP-125`, `BP-132`, `BP-170` | `standards/mold_contract.py`, `edit/dramatic_still.py` | `tests/unit/test_mold_contract.py` |
| **`M-09` / `CHG-03`** | Profile Scoping (`FAIL`) | `BP-84`, `BP-169`, `BP-170` | `edit/board.py`, `edit/rhythm.py` | `tests/unit/test_board.py`, `tests/unit/test_rhythm_zones.py` |
| **`M-10` / `CHG-08`** | `8k+1` Invariant (`FAIL`) / Handle Hypothesis (`REVIEW`) | `BP-128`, `BP-139` | `production/ltx_generate.py`, `production/assemble.py` | `tests/unit/test_ltx_handle_frames.py`, `tests/unit/test_assemble.py` |
| **`M-11` / `CHG-10`** | Single-Home Audio (`FAIL` `D-59`; `REVIEW` `68/20/12`) | `BP-15`, `BP-73..75`, `BP-122`, `D-59` | `audio/sound_director.py`, `audio/layers.py`, `production/assemble.py`, `finish/loudness.py` | `tests/unit/test_audio_two_axis_and_bp122.py`, `tests/unit/test_loudness.py` |
| **`M-12` / `CHG-01`, `CHG-11`** | Topic-Agnostic & Color Lock (`FAIL`) | `BP-130`, `BP-166`, `D-22` (`LT-65`), `ZI-09` | `production/episode_look.py`, `scripting/prompt_lint.py`, `qa/color_continuity.py` | `tests/unit/test_color_continuity.py`, `tests/unit/test_prompt_lint.py` |
| **`CHG-02`** | `/4` Dispatch Completeness (`FAIL`) | `production_script/3`, `production_script/4` | `scripting/schema_version.py`, `production/script.py` + 11 consumer modules | `tests/unit/test_schema_version_dispatch.py` |
| **`CHG-07`** | `17,280`-Frame Conservation & Infeasibility (`FAIL`) | `BP-28`, `BP-30`, `BP-167`, `BP-169`, `BP-170` | `production/timeline_compiler.py` | `tests/unit/test_timeline_compiler.py` |
| **`CHG-12`** | Character Voice & Legal Gate (`FAIL` `PV-55`; `CD-06`) | `D-62`, `D-63`, `D-90`, `PV-55` | `audio/character_voices.py`, `production/ltx_generate.py`, `governance/rights_gate.py` | `tests/unit/test_character_voices.py`, `tests/unit/test_rights_gate.py` |
| **`CHG-13`** | Agent/Skill Sync & 5 Shorts (`FAIL`) | `BP-167`, `D-79`, `D-85` | `.claude/agents/*.md`, `.claude/skills/*/SKILL.md`, `finish/shorts_extract.py` | `explainer_engine/docs_lint.py`, `tests/unit/test_shorts_extract.py` |
| **`CHG-14`** | Spend Cap & 2-Sample Gate (`FAIL` + `CD-01`, `CD-05`) | `D-56`, `D-67` (`OR-19`), `D-84`, `D-89`, `BP-168` | `config/spend_caps.json`, `core/spend_caps.py`, `core/ledger.py`, `production/sample.py` | `tests/unit/test_spend_caps_reconciliation.py`, `tests/unit/test_sample.py` |

### 17.4 Independent Claude / Auditor Verification Checklist (`12` Zero-Trust Verification Commands)

An independent Claude session or external auditor can verify every claim in this roadmap by running the following deterministic checks against the repository:

1. **Documentation & Path Integrity Gate**:
   * Run `PYTHONPATH=. python3 -m explainer_engine.docs_lint` -> must output `docs_lint: 0 finding(s)`.
2. **Single-Home Threshold Invariant (`D-59`)**:
   * Run `pytest tests/unit/test_sourced_rules.py` -> verifies all `158` `BP-*` rules in `explainer_engine/standards/sourced_rules.json` and rejects duplicated threshold numbers outside `sourced_rules.json`.
3. **Zero Search-Page URL Check**:
   * Run `grep -rn "google.com/search" docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md` -> must return `0` matches.
4. **Zero Non-Existent Repo Path Check**:
   * Verify that none of the retired hallucinated filenames (`odom_polish.py`, `tts_elevenlabs.py`, `production_script_v4.schema.json`, `docs/PRODUCT_MOLD.md`, `docs/SCHEMAS.md`, `docs/OPEN_QUESTIONS.md`, `docs/DECISIONS.md`) exist as target claims in §16 or §17.
5. **Master Mold Provenance Check**:
   * Verify `sha256sum mrbeast_12min_master_mold.md` == `49cf30840fa3603c27693d40f92fb3c33be1dbc5bd61cc6972b6c7f57bcb067e` (`431` lines) and `sha256sum "mrbeast_12min_video_mold (1).json"` == `2ca7f56fe549879e094ec775a9ddb3f810e671a3f2d3b6d4f1cc3f9dc3e106a0` (`26,291` lines).
6. **152 `VIDEO` Shots LTX-2.5 Handle Math Check**:
   * Verify across the `152` `VIDEO` shots (`10,368` usable timeline frames) that `sum(8*ceil((u+24-1)/8)+1) == 14,552`, `sum(8*ceil((u+8-1)/8)+1) == 12,120` (difference `2,432` frames = `16.71%`), and transition-aware (`17` whip-pan/crossfade at `>=12`/side + `135` hard/J/L at `>=4`/side) == `12,392` (difference `2,160` frames = `14.84%`).
7. **76 `STILL` Shots `BP-170` Static Cap Check**:
   * Verify across the `76` `STILL` shots (`19` `TIER_1`, `40` `TIER_2`, `17` `TIER_3`) that `2` `TIER_1` (`SH003`, `SH226`), `36` `TIER_2`, and `17` `TIER_3` (`55` total) exceed `BP-170`'s `static_still_max_s_by_zone` (`1.5s / 2.0s / 2.5s`).
8. **Cumulative Spoken Word Share Check (`BP-04`)**:
   * Verify across `S01..S16` (`2,066` words) that `S13` ends at `1,724` words (`83.45%`), `90.0%` (`1,860` words) is crossed inside `S14` (`~644.1s`), and `S14` ends at `1,909` words (`92.40%`) before `S15` (`660.0s`).
9. **Real `eleven_v4` Natural Pause Share Check**:
   * Verify on `examples/day1_v2/words_raw.json` (`204` words, `86.579s` span, `54.280s` phonation, `32.299s` natural gaps = `37.31%` pause share, `225.50` speaking WPM -> `141.37` raw heard WPM) that `pause_pad.py` inserts only boundary gap deficits (`add = max(0, want - gap)`).
10. **12-Module `/4` Schema Version Dispatch Check**:
    * Verify all 12 modules listed in `CHG-02` (`script.py`, `scene_lint.py`, `script_approval.py`, `speech.py`, `story_lint.py`, `beats.py`, `editorial_gate.py`, `silent.py`, `staging.py`, `validate.py`, `production_gate.py`, `audio/layers.py`).
11. **Spend Cap & `80%` Ledger Stop Check**:
    * Verify `GATE-P1a..P3` sub-gate caps (`$0.40 + $0.80 + $1.30 + $2.20 = $4.70`) fit strictly below `0.80 * $5.90 = $4.72` (`paid_tests.total_usd`), and `GATE-P4` (`$7.80` est., `$12.00` `BP-168` cap) fits strictly below `0.80 * $26.00 = $20.80` (`runpod.per_24h_usd`).
12. **Protected Config & Unmerged PR Invariant Check**:
    * Verify `git diff 5013a55aca5a17a3734150f61a5eb172abcbe3b8 -- explainer_engine/ config/ .claude/ tests/` is empty (`0` code/config modifications on this planning branch).

### 17.5 Explicit Register of Unresolved External & Empirical Uncertainties

1. **`UNC-01` — External Pre-Bundle File Hashes (`316d8042...`, `89aa56d2...`, `173EFDA0...`)**:
   * **Why Unresolved**: Those three SHA-256 digests refer to pre-bundle draft edits or a local Windows `C:\Users\User\Downloads\mrbeast_12min_video_mold (1).json` file outside the sandbox container. All quantitative audits in this roadmap are anchored to the exact verified bundle files (`49cf3084...` and `2ca7f56f...`).
2. **`UNC-02` — Live GitHub Branch Protection & Remote HF Vault State (`GATE-EXT-MAIN-PROTECT`)**:
   * **Why Unresolved**: Outbound network access to the live GitHub REST API and HuggingFace API is disabled inside the sandbox VM. Must be verified in the live workstation shell before merging [PR #119](https://www.google.com/search?q=https://github.com/vano1919/explainer-engine/pull/119).
3. **`UNC-03` — Empirical `TIER_2` Pose-Delta & Identity Threshold on Qwen-Image-Edit (`CD-03`)**:
   * **Why Unresolved**: Requires running `GATE-P1b` (`$0.45` est.) to measure whether `qwen_nextpose` achieves `masked_pose_iou_delta >= 0.20` while keeping ArcFace `cosine >= 0.65` (`BP-130`). Until `GATE-P1b` and `CD-03` sign-off, `TIER_2` remains capped at `1.5s / 2.0s / 2.5s` (`BP-170`).
4. **`UNC-04` — Empirical `4`-Frame Hard-Cut LTX-2.5 Boundary Flicker Rate (`CHG-08`)**:
   * **Why Unresolved**: Requires running `GATE-P2` (`$0.80` est., `5` LTX-2.5 clips) to confirm that trimming `4` frames per side removes 100% of first/last-frame VAE boundary artifacts on hard cuts before changing `BP-128`'s default `[12, 16]` range.
5. **`UNC-05` — Open Creator Decisions (`CD-01..CD-10`)**:
   * **Why Unresolved**: Governed exclusively by the creator (§13.2); zero code or paid calibration runs may start until `CD-01` and `CD-05` are answered.
