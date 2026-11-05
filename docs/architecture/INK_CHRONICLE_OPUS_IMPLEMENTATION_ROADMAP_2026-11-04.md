# Ink Chronicle — Opus Implementation Roadmap (2026-11-04)

**Status:** authoritative planning deliverable of the Fable master task ([FABLE_CLAUDE_TO_OPUS_IMPLEMENTATION_PLAN_BRIEF_2026-11-04](FABLE_CLAUDE_TO_OPUS_IMPLEMENTATION_PLAN_BRIEF_2026-11-04.md)).
**Branch:** `opus/ink-chronicle-blender-visual-system-2026-11-04` (the ONLY working branch). Audited HEAD before this document: `bb1243e5c7d8bf7935f2a2fd59ef24dede920c4c`.
**Written:** 2026-11-05 by the Fable planning thread; **revision 2** the same day after the creator's independent review (section 19). Documentation only; no runtime, test, pod, paid call or `main` change.
**One home rule:** this file is the one roadmap. Older branch documents stay as evidence and are linked, never copied (section 3).

Evidence labels used throughout: **REPO** = verified repository fact (path, symbol, line at HEAD `bb1243e`), **EXT** = verified external fact (source + access date 2026-11-05), **CREATOR** = creator-approved requirement, **MEASURED** = measured in this repository or on CI, **VENDOR** = vendor claim, **EST** = estimate (arithmetic over stated assumptions), **HYP** = hypothesis, **OPEN** = open creator decision, **NOT FOUND** = searched, does not exist.

Dispositions: KEEP / CHANGE / REMOVE / ADD / DEFER-BEHIND-TEST / REJECT. Approval states: CREATOR-APPROVED / RECOMMENDED / NEEDS-CREATOR-APPROVAL / BLOCKED.

---

## 1. Executive recommendation and final verdict

**Recommendation (RECOMMENDED, confidence M):** build the Ink Chronicle system as a *new render lane behind the existing contracts*, not as a new pipeline. The current repository already owns everything upstream (research, script, approvals, audio spine, 24 fps clock, ledger, spend caps, pods) and everything downstream of a rendered clip (`production/assemble.py::build_video_v2` streams per-shot clips from `shots/` into one FFmpeg encode at the spine's fps and size, REPO lines 603-900). Blender's only job is to put an accepted clip per VIDEO/STILL shot into that `shots/` folder, keyed by the existing shot cache. HELPER graphics stay with the existing deterministic Python renderers (`maps/render.py`, `edit/hud.py`, `edit/tableau.py`, `production/graphics.py`), re-skinned to the Ink Chronicle palette and paper/ink treatment; Blender terrain for a HELPER map is DEFER-BEHIND-TEST (D-87 narrowed, not lifted).

Ten work packages (section 15) land in six phases; the critical path is ICW-00 → ICW-02 → ICW-04 → ICW-06 → ICW-07 → ICW-09 → ICW-10. The first paid step is one bounded benchmark pod (ICW-09, cap proposed US$3) after the OR-34 Fable audit; nothing before it costs money.

**Verdict: OPUS READY** (updated 2026-11-05 07:45 UTC) — the three creator answers of section 17 are recorded: ICG-1 = A (70/30 nominal, REVIEW band 65-75), ICG-2 = A in substance (a small RunPod cost test; the money figure is confirmed in the OR-23 pod plan before the pod starts), ICG-3 = A (the M4 Pro Mac renders the local visual tests). Revision 2 (section 19) closed the review's findings in the plan itself: a durable frame-recovery contract (10.4), the benchmark protocol the brief actually asked for (12.4, with the money figure raised to a proposed ≤ US$6 for the creator's word in the OR-23 plan), the full AI-asset PoC matrix (9.4), the four-tier resolution test (9.5), a final-mix speech check (13) and per-package effort/uncertainty (15). No evidence gate blocks Opus's first packages (ICW-00..08 cost $0); every technical decision is closed in sections 5-13. OPUS READY is not permission to launch Opus: the creator's explicit word is still required (section 18, item 12).

What this roadmap does NOT claim: that Blender is production-ready (the PoC never produced a verified render, section 3.5), that US$10-15 is achievable (section 12 shows it is plausible only below about 3-4 s per 1440p frame on a 4090-class card, HYP), or that any upscale tier is safe (section 8.2, DEFER-BEHIND-TEST).

## 2. Scope, creator targets and evidence labels

Precedence as the brief orders: platform/legal/safety → the creator's explicit instructions ([INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04](INK_CHRONICLE_VISUAL_PRODUCTION_DIRECTION_2026-11-04.md), CREATOR) → the canonical decision log ([DECISIONS_AND_OPEN_QUESTIONS](../DECISIONS_AND_OPEN_QUESTIONS.md)) → verified code and tests → verified external sources → specifications → research.

| Target (CREATOR, fixed) | Value | Where it is measured in this plan |
|---|---|---|
| Visual identity | one Ink Chronicle universe, illustrated / graphic-novel final look from real 3D geometry | style-sheet collage approval (ICW-05), visual acceptance matrix (section 13) |
| Final renderer | Blender authoritative for VIDEO and STILL pixels; EEVEE default, Cycles per-shot justified | `blender_render_manifest/1` (section 10) |
| Master | 2560x1440 (QHD/1440p), 24 fps | BP-167 (REPO `core/delivery.py`), ffprobe in `qa/frame_review.py`, CN-09 |
| Visual runtime | 10 % HELPER / 30 % STILL / 60 % VIDEO, tolerance +-5 pp kept (section 6, ICD-02) | `film_shots.lane_shares` (REPO lines 830-837) over final shot seconds |
| Spoken words | 70 narrator / 30 voiced dialogue, `voiced:false` excluded; mode OPEN (ICG-1) | `variant_plan.dynamics` words (REPO lines 240-243) + new `speech_mix_report/1` |
| Lip-sync | 5 s planning maximum for visible voiced coverage only | BP-108 `dialogue_shot_max_s` (REPO) |
| Non-dialogue action | 10-15 s allowed | BP-108 `non_dialogue_video_max_s` (REPO) |
| Cost | US$10-15 recurring render/compute per 12-15 min episode, unproven | section 12, benchmark ICW-09 |
| Governance | story, research, audio, timing, QA, approvals, spend guards, provenance, FFmpeg delivery preserved | sections 4, 5, 15 (every KEEP row names its test) |

The visual runtime ratio and the spoken-word ratio are two measurements with two validators and two reports; nothing in this plan derives one from the other (ICD-03).

## 3. Branch reconciliation

Local Git was available; all refs fetched 2026-11-05 07:03 UTC. Worktree clean, upstream `origin/opus/ink-chronicle-blender-visual-system-2026-11-04` (REPO `git status`, `git branch -vv`).

### 3.1 Heads and ancestry (REPO)

| Branch | HEAD | Relation to the final branch |
|---|---|---|
| `opus/ink-chronicle-blender-visual-system-2026-11-04` (FINAL) | `bb1243e5c7d8bf7935f2a2fd59ef24dede920c4c` | — |
| `claude/master-mold-ready-2026-11-04` | `d5925ec080600d77836eded064312da2f30bc78b` | direct ancestor of FINAL (merge-base = its HEAD); FINAL is 20 commits ahead, 0 behind; this base is itself 92 commits ahead of `main` |
| `opus/ink-chronicle-blender-plan-2026-11-04` | `5da6856e3e19d62e9e59bb3f2c55c95031044918` | diverged at `d5925ec`; 9 commits only there, 20 only on FINAL |
| `experiment/blender-scene-poc-2026-11-04` | `6f686a56d487fb846b9b4711c325f37278fabfa6` | diverged at `209eb87` (one commit before `d5925ec`); 8 commits only there, 21 only on FINAL |
| `main` | `073eb25cda135387c47dfc3aafb043cad0574ecc` | merge-base `6e1dcca`; 1 commit only on main, 112 only on FINAL |

The brief's prior counts (9 / 16 and 8) have moved: FINAL now carries 20 (not 16) unique commits over the Opus-plan branch. The 9 and 8 figures are unchanged.

### 3.2 The 20 FINAL-only commits (REPO `git log d5925ec..bb1243e`)

Fourteen are documentation (`dd5802d`..`e1e8649`, `6ea9ffa`/`8b4c047` banners, `815d064`/`dbc8255` TODO disposition, `b38d723`/`cf13768`/`74ef555` the brief and index, `bb1243e` the 8.1/8.2 hypotheses). Seven touch code: `4936a23`/`07f2cea`/`65d76ce`/`2473fec` replaced the Master Mold TODO text of `video/generator.py`, `keyframes.py`, `scene_builder.py`, `tier_router.py` with Ink Chronicle planning docstrings (each file is now a 11-12 line docstring and `from __future__ import annotations`, REPO); `7e6866e`/`a375fce`/`82d3ff7` removed the leading Master Mold comment block from `assets/library.py`, `production/assemble.py`, `production/rig.py`. `git diff d5925ec..bb1243e -- explainer_engine/` shows comment and docstring changes only (REPO). `CLAUDE.md` gained a 15-line override banner and keeps every invariant.

### 3.3 Disposition of the 9 Opus-plan-only commits

| Commit | Files | Disposition | Reason / evidence |
|---|---|---|---|
| `99743b2` OPUS_MASTER_TASK.md | docs/opus/ | ADAPT / SUMMARIZE | its 15 required sections and acceptance list are covered by this roadmap's 18 sections; its "every class is TODO" rule is kept (section 11 status column) |
| `d756d51` VISUAL_GRAMMAR_10_30_60.md | docs/opus/ | ADAPT / SUMMARIZE | its lane sub-categories, STILL render modes (`STILL_HOLD`, `TABLEAU_2_5D`, `TABLEAU_3D`, `INSERT`) and validator list are merged into section 7 |
| `9e31c94` ARCHITECTURE_AND_CLASS_MAP.md | docs/opus/ | ADAPT / SUMMARIZE | its package tree (`visual/`, `blender/`) is the starting point of section 11, reduced from 25 classes to 12 |
| `bd7f3b8` RULE_CONFLICTS_AND_MIGRATION.md | docs/opus/ | ADAPT / SUMMARIZE | its 13 rows become section 6 rows, each now with code/test evidence |
| `b996a06` RENDER_COST_AND_BENCHMARK_PLAN.md | docs/opus/ | ADAPT / SUMMARIZE + REJECT its price table | prices were third-party trackers "observed 2026-11-04"; section 12 uses the vendor pages read 2026-11-05 |
| `fb6b066` TODO_REGISTER.md | docs/opus/ | ADAPT / SUMMARIZE | its TODO-RULE/VIS/ARCH/COST/QA ids map onto ICW packages (section 14 cross-reference) |
| `6cb8748` RESEARCH_SOURCE_SCOPE.md | docs/opus/ | REFERENCE WITHOUT COPYING | its "legacy-only" list (LTX 8n+1, IC-LoRA, Qwen keyframes, Remotion, Master Mold batches) is adopted as-is (section 6) |
| `4ef20df` README.md replacement | README.md | REJECT AS CONFLICTING | it replaces the repository README with a planning-branch pointer to a branch that is not the final branch |
| `5da6856` CLAUDE.md replacement (84 insertions, 161 deletions) | CLAUDE.md | REJECT AS CONFLICTING | it deletes the twelve invariants, commands and layout; FINAL keeps the full file plus an override banner (REPO `git diff d5925ec..bb1243e -- CLAUDE.md`) |

No file of `docs/opus/` is copied to FINAL; they remain readable on their branch (REFERENCE).

### 3.4 Disposition of the 8 Blender-PoC-only commits

| Commit | Files | Disposition | Reason |
|---|---|---|---|
| `fcaa736` build_scene.py (187 lines) | experiments/blender_scene_poc/ | REFERENCE WITHOUT COPYING | primitive hero (parented spheres/cubes), orthographic camera, EEVEE Next, 1280x720, 120 frames; useful as the shape of a bpy build script; superseded by ICW-04/ICW-06 |
| `1fe4656`, `b18a199` README | same | REFERENCE WITHOUT COPYING | its "does not prove" list is adopted verbatim in 3.5 |
| `053307e` parenting fix | same | PRESERVE AS-IS (on its branch) | `attach()` keeps world matrices before parenting; the lesson is carried into ICW-06 |
| `2570d7b` AgX look enum | same | PRESERVE AS-IS | `"AgX - Medium High Contrast"` → `"Medium High Contrast"` (REPO `git show 2570d7b`); the first CI run exited 0 with no output because Blender does not fail on a Python exception unless `--python-exit-code` is set (EXT, Blender 5.2 manual, command-line arguments) — carried into ICW-04 as a hard rule |
| `2cf4ff1`, `f25c857`, `6f686a5` workflow | .github/workflows/blender-scene-poc.yml | REFERENCE WITHOUT COPYING | ubuntu-24.04 runner, pinned Blender 4.2.0 download, 30-minute timeout; the runner has no GPU; see 3.5 |

### 3.5 Blender PoC — evidence boundary (MEASURED on GitHub Actions, read 2026-11-05 via the Actions API)

| Run | Trigger / SHA | Result | What it shows |
|---|---|---|---|
| 41880570330 | push `2cf4ff1` | **failure**: "Render five-second scene" succeeded in 1 s, "Upload render outputs" failed (no files) | Blender 4.2.0 downloads and starts on the runner; the script raised on the look enum and Blender still exited 0 |
| 41881452001, 41881555751, 41881606885, 41881616488 | pushes `2570d7b`..`6f686a5`, PR #120 | **cancelled** | each hit the job's 30-minute `timeout-minutes` |
| 41882249912 (main, manual workflow) | `073eb25` | **cancelled**: render step ran 17:58:49 → 18:28:26 and was cancelled; verify and upload skipped | 120 frames at 1280x720 EEVEE did not finish in 29.5 minutes on a CPU-only `ubuntu-24.04` runner |

Therefore: **no rendered frame, MP4 or `.blend` from the PoC exists anywhere in the repository or in an Actions artifact.** The README's "Document five-second Blender render outputs" commit describes expected outputs, not observed ones. What passed: Blender install, headless start, scene build up to the first `bpy.ops.render.render` (the 1-second run reached the look-enum line, after the scene asserts). Not tested: render time, output correctness, GPU rendering, AI mesh conversion, rigging, lip-sync, Ink Chronicle look, cost, contract compatibility. Next bounded PoC = ICW-04's smoke test (Workbench engine, 8 frames, `--python-exit-code 1`, on CI without GPU) and ICW-09's first paid EEVEE benchmark on a GPU.

### 3.6 The main-only commit

`073eb25` adds `.github/workflows/blender-scene-poc-manual.yml` (workflow_dispatch, checks out the experiment branch). Disposition: REFERENCE WITHOUT COPYING, remains on `main`; it is useful only as the record of the cancelled run above. ICW-04 replaces it with a CPU-safe smoke workflow on the final branch; `main` is not touched by this plan.

### 3.7 Other `claude/project-thread-*` branches

Eight remote `claude/project-thread-*` branches exist (REPO `git branch -r`). None is named by the research index or the handoff as carrying Ink Chronicle work; they were not inspected further (bounded stop, per the brief's "inspect only if branch history or the research index shows relevant work").

## 4. Verified current architecture and code path

### 4.1 What exists today (REPO at `bb1243e`)

```
research → scenario → script (production_script/3, creator approvals OR-15/OR-17)
   → variant planner  scripting/variant_plan.py  (lane shares VP-18, narrator words VP-16, cost)
   → film_shots/2     scripting/film_shots.py    (lane enum of 8, KP-36/37/39, lane_shares, visual_lane)
   → audio spine      audio/spine.py             (audio_spine/2: every narrator word on the 24 fps clock, post-hoc windows D-88)
   → shot router      edit/router.py             (film_shots/2 → shot_spec/1 + shot_route/1; LTX/Qwen recipes; MAP/COMPENSATOR → comp manifest)
   → shot cache       core/shot_cache.py         (sha256 of the canonical shot_spec/1; outputs verified by hash)
   → [renderers]      Qwen keyframe + LTX clip pod scripts (training/pods/p12/*, LANES table says NOT available)
                      maps/render.py, edit/hud.py, edit/tableau.py (HELPER archetypes 1-12, free, pure f(spec, frame))
                      production/parallax.py + depth.py (2.5D on a still), edit/dramatic_still.py (BP-170)
   → assembly         production/assemble.py::build_video_v2 (edit_and_grade_manifest/1 + shots/<id>.{mp4,mkv,mov,webm,npy} → episode.mp4 + .otio)
                      production/assemble.py::build_audio_v2 (sound_mix_manifest/2 → stems, loudness BP-52)
   → QA               qa/frame_review.py, qa/identity.py (CLIP), qa/scorecard.py, qa/publish_check.py
   → review bundle → creator approval → publish/ (unlisted only)
```

Key facts a reader must not assume otherwise:

- **Two assemblers coexist** (REPO `assemble.py` line 606 comment "One assembler: this sits beside build_audio_v2, it does not replace _assemble"): the D-43 still-picture route `assemble()` (PIL-drawn frames, 60-second chunks, default 30 fps, lines 1139-1415) ships today's episodes; the animated route `build_video_v2` (lines 856-900) reads per-shot clips and encodes at the spine's fps. The Blender lane plugs into the second only.
- **Clip discovery** is by file name: `clip_path(shots_dir, shot_id)` over `CLIP_SUFFIXES = (".npy", ".mp4", ".mkv", ".mov", ".webm")` (line 607). A Blender render delivered as `shots/<shot_id>.mkv` (FFV1) needs no assembly change.
- **The router refuses two lanes before routing**: `core/contracts.REFUSED_LANES` = `HOST_COMMENTARY` (D-89) and `DRAMA_BLOCKED_3D` ("card A2 is 'not now': 3D blocking and LivePortrait/MuseTalk are neither in code in v2 (D-75, D-77)") (REPO `core/contracts.py` lines 111-119); `tests/unit/test_shot_router.py::test_h_the_refused_lanes_never_reach_the_router` and `test_contracts.py::test_refused_lanes_cannot_reach_a_renderer` pin it.
- **Lane shares** are computed by `film_shots.visual_lane` (lines 816-827): `helper` = `MAP`/`COMPENSATOR`/`GRAPHICS` or any archetype id, `still` = archetype 8 (`PARALLAX_25D_TABLEAU`), tier `hold` or `STILL_HOLD`, `video` = everything else. Shares and tolerance come only from BP-109 (`lane_share` {video .6, still .3, helper .1}, `lane_tolerance` .05, `still_shot_max_s` 5) via `sourced_rules.T` (lines 82-84).
- **Speech share** is words only: `variant_plan.dynamics` (lines 240-243, "never infer it from visual or played runtime"), band BP-105 `narrator_share` [0.7, 0.8], checked by VP-16 and `film_shots.episode_check` KP-39 (lines 932-937); `segments_from_script` drops `voiced: false` words (line 167). No post-mix "audible seconds" report exists (NOT FOUND; `docs/PROGRESS.md` 2026-11-04 says the same).
- **Frame rate**: `film_shots.FPS = 24`; CN-09 refuses a spine, manifest or shot at another fps (`contracts.cross_fps`, `assemble.plan_video_v2` line 704); BP-167 = 12 min, 2560x1440, 24 fps, read by `core/delivery.py`. VIDEO_PARAMETER_SPEC P-12/P-13 still carry the still route's 1920x1080 / 30 (REPO lines 32-33), explicitly scoped to that route by BP-167.
- **Geometry rule CN-08** (8k+1 frames, sizes divisible by 32/64, max 257 frames) is BP-139, an LTX hypothesis, REVIEW-level, applied to every lane in `VIDEO_LANES` (`contracts.py` lines 60, 92-107).
- **The asset library** (`assets/library.py`, schema `asset_library/1`) knows 13 kinds, all raster/audio/font/LoRA (`KINDS` line 42, `RASTER` line 44); no mesh, rig, material, animation or `.blend` kind (NOT FOUND).
- **World bible** `bible.json` v1.4 draft pins `look_v2.json`, `eras.json` (14 eras) and `design/palette.json` (15 tokens) by sha256; `motion.default` = "stills with 2.5D parallax"; `banned_drift` includes "photo-realism or a 3D-render look in any era"; `look_v2.banned_words` includes "3d render", "realistic", "unreal engine", "octane" (REPO).
- **Spend control**: `config/spend_caps.json` (`per_episode.runpod_usd` 31, `paid_tests.total_usd` 5.9 with named lines; `runpod.per_pod_usd` 6.9, `max_hours_per_pod` 5), enforced by `core/spend_caps.py`, `core/ledger.py`, `cloud/runpod.py` (2062 lines, REST v2; `create --ledger`, guard, sweep, auto-delete D-92). `config/job_speeds.json` has rows for keyframes / ltx_clip / lora_train / captions / smoke, all empty (REPO).
- **`production/rig.py`** is RETIRED (docstring line 1), `__main__` raises `SystemExit("RETIRED ...")`; callers: `tests/unit/test_rig.py` imports it (10 tests) and `tests/unit/test_repo_hygiene.py::OLD_ERA_BANNERED` asserts the banner and the refusal (REPO lines 74-93). Nothing in production code imports it.
- **The video package** `explainer_engine/video/`: four 11-12-line planning stubs (generator, keyframes, scene_builder, tier_router) and six "Stub specification module" files with zero functions (`__init__`, color_grade, compositor, ltx_Node, parallax, prompts). Repository-wide there are 37 such empty stub modules and 296 files carrying a `CLAUDE-MASTER-MOLD-SYNC` header block plus 88 `CLAUDE-CLASS-SYNC` lines in 35 files (REPO grep). The handoff states the blocks changed no executable body (REPO `docs/wip/CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md`). None of the 37 stubs has a Python importer outside the stubs themselves (REPO grep over `explainer_engine`, `tests`, `scripts`).
- **Blender in code: NOT FOUND** except the four planning docstrings and one "no Blender" comment in a pod script.
- **Test suite on FINAL (MEASURED 2026-11-05, Python 3.13.18, `pytest -m "not system and not media"`):** 17 failed, 2423 passed, 7 skipped in 324 s. Six failures need `cv2` (not installed here). Eleven are branch-inherited: the Master Mold header blocks sit above module docstrings, so tests that read the first docstring or scan comments fail (`test_repo_hygiene::test_kokoro_modules_carry_the_d39_banner…`, `test_agent_governance::test_n06…`, `test_assemble_v2::test_the_loudness_targets…`), the sourced-rules doc table and the Napoleon `script_variants.json` fixture are stale (`test_sourced_rules`, `test_variant_plan` x5, `test_film_shots` x1), `docs_lint` reports `PROGRESS.md cites D-96, which no document defines`, and three BP ids (BP-155, BP-68, BP-79) are cited but undefined. **The same seven test files pass on `main` (147 passed, MEASURED in a throw-away worktree).** The base branch, not the FINAL-only commits, carries the breakage.

### 4.2 Target flow (every stage marked)

```
approved story/script + narration timing            EXISTS   (scripting/, audio/spine.py)
→ screenplay spine / film_shots/3                   CHANGE   (ICW-02: lane enum, archetype, blender fields)
→ visual intent + lane allocation                    EXISTS/CHANGE (film_shots.visual_lane + lane_shares; ICW-03)
→ archetype + shot design                            NOT IMPLEMENTED (ICW-03 visual/shot_design.py)
→ asset / world resolution                           PARTIAL  (assets/library.py, world/bible.py; ICW-05 adds 3D kinds + style)
→ Blender scene build                                NOT IMPLEMENTED (ICW-06 blender/scene_builder.py + bpy script)
→ lane-specific render profile                       NOT IMPLEMENTED (ICW-04 blender/profiles.py)
→ headless Blender render / frame cache              NOT IMPLEMENTED (ICW-04 blender/render.py + pod script; cache = core/shot_cache.py KEEP)
→ existing assembly / audio / FFmpeg mux             EXISTS   (assemble.build_video_v2 / build_audio_v2) — unchanged
→ visual / timing / style / continuity / cost QA     PARTIAL  (qa/frame_review, qa/identity; ICW-08 adds render validator, flicker, speech report)
→ creator review                                     EXISTS   (review bundle, approvals)
```

## 5. CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION

| Area | CURRENT (REPO) | NEW (target) | KEEP | CHANGE | REMOVE | Trade-offs | Recommendation |
|---|---|---|---|---|---|---|---|
| Story → script → approvals | production_script/3, OR-15/OR-17, claims PV-37 | unchanged | all | — | — | none | KEEP (CREATOR) |
| Audio spine / timing | audio_spine/2 on the 24 fps clock, D-88 post-hoc windows | unchanged; adds a speech-mix report read from the same spine | all | `speech_mix_report/1` ADD (section 8) | — | one more artifact per job | KEEP + ADD |
| Shot planning | film_shots/2 with 8 lanes, `visual_lane`, KP checks | film_shots/3: lanes `VIDEO_3D`, `STILL_3D`, `HELPER`; sub-fields `archetype`, `still_mode`, `render_profile` | `lane_shares`, BP-109 numbers, KP-36/37/39 | enum + `visual_lane` mapping (section 7) | LTX lanes from /3 (readable in /2) | one migration script; fixtures regenerated | CHANGE |
| Shot router | `edit/router.py`: film_shots/2 → shot_spec/1 (Qwen/LTX recipes) + comp manifest | router v2: film_shots/3 → shot_spec/2 (`blender_eevee/1` recipe) + comp manifest; HELPER path unchanged | `_write`, cache key, seeds, comp manifest | recipe tables, `VIDEO_LANES` | nothing deleted; /1 route stays for /2 inputs | two recipe tables for one release | CHANGE |
| Shot cache | sha256 of canonical shot_spec, hash-verified outputs | identical; shot_spec/2 includes scene + render blocks so a profile change re-renders | all | — | — | none | KEEP (REPO `core/shot_cache.py`) |
| Still / video renderers | Qwen keyframe + LTX pods (P12 scripts, LANES says unavailable), 2.5D parallax on stills | Blender EEVEE clips; STILL = Blender plate + Blender camera move or existing 2.5D | `production/parallax.py`, `depth.py`, `edit/dramatic_still.py` as STILL motion options | — | LTX/Qwen pod scripts: KEEP on disk, mark `legacy` in `config/cloud_pins.json` (no call path from /3) | keeping two eras in the tree | CHANGE; REMOVE deferred to a creator-word cleanup after the pilot (invariant 8) |
| HELPER graphics | `maps/render.py`, `edit/hud.py`, `edit/tableau.py`, `production/graphics.py`, `visual_compensator.py` (12 archetypes) | same renderers behind an Ink Chronicle style bridge (palette, paper grain, ink line weights) | all renderers, their tests | `design/palette.json` tokens + a `style_bridge` call in each renderer | — | 2D maps stay 2D; Blender terrain is a test, not a promise | KEEP + CHANGE; Blender terrain DEFER-BEHIND-TEST (D-87 narrowed) |
| Assembly | `build_video_v2` + `build_audio_v2`, FFmpeg, OTIO | unchanged; Blender writes `shots/<id>.mkv` | all | — | — | none | KEEP (CREATOR: FFmpeg preserved) |
| Legacy still-picture route | `assemble()` D-43, 30 fps default | untouched, documented as the legacy route | all | — | — | — | KEEP (D-43 episodes shipped) |
| World bible / look | bible v1.4 bans "3D-render look"; look_v2 bans "3d render"; motion default = stills + 2.5D | bible v1.5: Ink Chronicle 3D-to-illustrated look is the house style; bans re-worded to the real enemy (photoreal / raw CGI) | eras, palette, hashes, PBAN mechanism | `banned_drift`, `look_v2.banned_words`, `motion.default` | — | wording only; prompt lint still bites on "photoreal" | CHANGE (section 9) |
| Asset library | 13 raster/audio/font/LoRA kinds, licence + approval + lineage | asset_library/2: + `model`, `rig`, `animation`, `material`, `texture`, `blend_collection`, `scene_template`; `.blend/.glb/.fbx/.exr` extensions; dependency list | schema discipline, `find`, approvals | `KINDS`, `RASTER` → `BINARY_OK`, `required` | — | big binaries: Git LFS or an outside store (ICW-05 decides, see 9.3) | CHANGE |
| QA | frame_review (ffprobe, black, dims), identity (CLIP), scorecard, publish_check | + render validator (frame count, size, fps, black/frozen/flicker, line stability), lane runtime report, speech-mix report | all | scorecard reads the two reports | — | more gates, same gate style | ADD (section 13) |
| Spend | spend_caps, ledger, runpod.py, job_speeds (empty rows) | + `blender_frame` job rows, cost estimator from measured s/frame, pod script under `training/pods/` | all | `config/job_speeds.json` rows, a `paid_tests` line (ICG-2) | — | none | KEEP + ADD |
| Master Mold comment blocks | 296 files + 88 class lines, no executable change | gone | — | — | REMOVE (ICW-00), proof = AST compare + tests green as on `main` | one large comment-only diff | REMOVE |
| 37 empty stub modules | zero importers | gone or real | — | 4 Ink Chronicle stubs → replaced by ICW-04/06/07 modules | REMOVE the other 33 after the importer proof is re-run (ICW-00) | — | REMOVE ONLY AFTER CALLER AND TEST PROOF |

## 6. Decision and supersession matrix

Ids `ICD-nn` are this roadmap's decisions; each becomes a D-row in `docs/DECISIONS_AND_OPEN_QUESTIONS.md` in ICW-01 (the log is the one home; this table is the proposal). "Code" = where the rule lives today (REPO); "Tests" = what pins it.

| ICD | Conflict (brief §6) | Old rule / where | Decision | Code to change | Tests to change | Approval |
|---|---|---|---|---|---|---|
| ICD-01 | D-93 60/30/10 kept as runtime shares but mapped onto Blender | D-93 maps VIDEO → LTX clips, STILL → Qwen keyframe + parallax, HELPER → maps/HUD (`DECISIONS` line 90; `film_shots.visual_lane`) | Shares KEEP. Mapping CHANGE: VIDEO = Blender animated clip; STILL = Blender-rendered plate (+ Blender camera move or existing 2.5D); HELPER = existing Python renderers with the style bridge | `film_shots.visual_lane`, LANES table in `variant_plan.py` 74-87 | `test_variant_plan::test_vp18…`, `test_film_shots` lane tests (fixtures regenerated) | CREATOR (direction) |
| ICD-02 | +-5 pp tolerance | BP-109 `lane_tolerance` .05; the creator wrote "approximate" on 2026-11-01 20:03 (REPO sourced_rules BP-109 source) | KEEP the number and its REVIEW level; the lane planner targets exact shares, QA reports REVIEW outside the band | none | none | CREATOR-APPROVED (existing house rule) |
| ICD-03 | D-95 75/25 midpoint vs new 70/30 nominal | BP-105 `narrator_share` [0.7, 0.8], D-95 "midpoint 75/25" (`DECISIONS` line 17, override doc) | CHANGE the nominal to 70/30; band [0.65, 0.75] at REVIEW level (ICG-1 answered A, 2026-11-05). Words-only measurement KEPT; add audible-seconds reporting (informational) | `sourced_rules.json` BP-105 (`nominal` 0.70; band per ICG-1), KP-39, VP-16 | `test_sourced_rules::test_d95_speech_mix…`, `test_variant_plan::test_vp16…` | CREATOR-APPROVED (ICG-1 = A) |
| ICD-04 | D-70 (pictures from paid image providers per batch, D-50) | D-50/D-70 provider choice per paint plan | KEEP for the legacy still route and for reference art; NOT on the Blender path (no paid image call per shot). Reference-art calls for style sheets remain under D-50 | none | none | RECOMMENDED |
| ICD-05 | D-41 (stable hero references, never redraw from scratch; invariant 6) | D-41/D-55 expression sheets and references are raster | KEEP the principle; the identity carrier becomes the rigged `model` + `material` assets with their approved turnaround sheets as the raster reference; `qa/identity.py` CLIP check compares rendered CU frames to the approved sheet | `assets/library.py` kinds; `qa/identity.py` reference lookup | `test_asset_library`, `test_identity` | RECOMMENDED |
| ICD-06 | bible "3D-render look" ban and look_v2 "3d render" ban | bible v1.4 `banned_drift`; look_v2 `banned_words` | CHANGE wording: ban "photoreal / photographic / raw CGI / PBR-photoreal / unreal engine / octane"; the Ink Chronicle illustrated-from-3D look is the house look (section 9.1) | `world/bible.json` (v1.5, rehash), `world/look_v2.json`, `world/resolver.py` UR-22 lint list | `test_world_bible`, `test_world_resolver` | NEEDS-CREATOR-APPROVAL on the collage (ICW-05), wording RECOMMENDED |
| ICD-07 | BP-109 / BP-170 lane and still rules | BP-109 shares; BP-170 dramatic still (`edit/dramatic_still.py`) | KEEP both; BP-170 becomes one `still_mode` of STILL_3D (Blender plate + the same dramatic camera curve) | `film_shots` still_mode enum | `test_dramatic_still` unchanged | RECOMMENDED |
| ICD-08 | 24 fps | BP-167, `film_shots.FPS`, CN-09; P-12/P-13 say 30 for the legacy route | KEEP 24 for every Blender lane and the spine; legacy still route keeps its own numbers | none | none | CREATOR-APPROVED |
| ICD-09 | LTX/Qwen tiers and 8k+1 geometry | `film_shots.MODEL` tiers hold/light/full → ltx-2.5; BP-139 / CN-08 on all VIDEO_LANES | CHANGE: CN-08 becomes lane-conditional (only lanes whose recipe is `ltx_i2v/*`); `MODEL` tiers replaced by `render_profile` (eevee_fast / eevee_full / cycles_hero) in /3; BP-139 stays in the registry as a legacy-recipe rule | `contracts._geometry`, `film_shots.MODEL`, router recipes | `test_contracts::test_cn08…` gets a lane-conditional case; `test_shot_router` | RECOMMENDED |
| ICD-10 | DRAMA_BLOCKED_3D | refused lane (D-75/D-77, `REFUSED_LANES`) | KEEP refused in /2; NOT in the /3 enum (its intent is now `VIDEO_3D` + archetype). History stays in the log | `contracts.REFUSED_LANES` unchanged | `test_h_the_refused_lanes…` unchanged | RECOMMENDED |
| ICD-11 | `production/rig.py` | RETIRED module, tested by `test_rig.py` and `test_repo_hygiene` | KEEP as-is (retired, bannered); the Blender character rig adapter is a new module `blender/rigs.py`, never a revival | none | none | RECOMMENDED (invariant 8) |
| ICD-12 | Master Mold TODO annotations | 296 header blocks, 88 class lines, 37 stubs, `docs/wip/*` guides | REMOVE the blocks (comment-only, proven); stubs REMOVE after importer proof; guides marked HISTORICAL (already bannered in `8b4c047`/`6ea9ffa`) | ICW-00 | repo-hygiene tests pass as on main | RECOMMENDED |
| ICD-13 | Compositor / Remotion / FFmpeg / Blender roles | Remotion in old plans only (NOT FOUND in code); `video/compositor.py` empty stub | Blender = final pixels of VIDEO/STILL shots; Python renderers = HELPER pixels; FFmpeg (`build_video_v2`) = the only compositor/encoder; Remotion REJECT; Blender VSE REJECT | none | none | RECOMMENDED |
| ICD-14 | Asset library raster assumptions | `assets/library.py` KINDS/RASTER | CHANGE (asset_library/2, section 9.3) | `assets/library.py`, schema | `test_asset_library` | RECOMMENDED |
| ICD-15 | RunPod spend controls | spend_caps / ledger / runpod.py / OR-21 pod scripts / OR-23 pod plans / OR-34 audit | KEEP all; ADD `blender_frame` job rows and the estimator; the first benchmark pod is a `paid_tests` line (ICG-2) | `config/job_speeds.json`, `training/pods/blender_render.py` | `test_job_speeds`, pod-script governance test | NEEDS-CREATOR-APPROVAL (money only) |
| ICD-16 | D-87 (maps stay 2D, no 3D terrain) | D-87 | Narrow, not lift: 2D HELPER maps stay default; a Blender terrain map is one benchmark shot in ICW-09, promoted only if it passes the visual matrix and costs under the HELPER budget | none now | none now | DEFER-BEHIND-TEST |
| ICD-17 | D-96 citation | `PROGRESS.md` cites D-96; no definition (docs_lint finding) | ICW-01 writes D-96 = "Ink Chronicle direction (2026-11-04)" into the log, clearing the finding | docs only | `test_docs` | RECOMMENDED |

## 7. Visual grammar — 10 / 30 / 60 and the 20 archetypes

### 7.1 Lane definitions (film_shots/3)

| Lane | Meaning | Renderer | Max shot | Motion allowed | Counted as |
|---|---|---|---|---|---|
| `VIDEO_3D` (60 %) | animated Blender shot: character or camera or simulation motion over real geometry | Blender EEVEE (Cycles per shot by `render_profile: cycles_hero`, justified in the shot's `why`) | BP-108: 5 s if voiced CU, 15 s non-dialogue | full | video |
| `STILL_3D` (30 %) | one Blender-rendered illustrated plate, held or moved by a camera curve | Blender render of 1 frame (or N frames for a Blender camera move); motion from `production/parallax.py` (2.5D) or `edit/dramatic_still.py` curve | BP-109 `still_shot_max_s` 5 | camera only (push, drift, parallax, dramatic curve); no character motion | still |
| `HELPER` (10 %) | maps, HUD, tableaux, cutaways, graphs, dates, quotes | existing Python renderers through the style bridge; archetype ids 1-12 of `edit/archetypes.json` | archetype's own | as today | helper |

Sub-fields on every /3 shot: `archetype` (1-20 below), `still_mode` (`hold`, `drift`, `parallax_25d`, `dramatic_curve`, `camera_move_3d`) for STILL_3D, `render_profile`, `lipsync` (bool, VIDEO_3D only; true forces `≤ dialogue_shot_max_s` and a visible mouth), `dialogue_cover` (`on_screen`, `off_screen`) for voiced lines.

`visual_lane` mapping rule (replaces lines 816-827): `HELPER` → helper; `STILL_3D` → still; `VIDEO_3D` → video. The shares and tolerance keep reading BP-109. Legacy /2 inputs keep the old mapping (both versions readable, `film_shots.visual_lane` dispatches on the contract version).

### 7.2 Rhythm rules (KEEP, REPO)

BP-108 (dialogue 5 s, non-dialogue 15 s), BP-109 `still_shot_max_s` 5, BP-169 MrBeast rhythm profile (episode 720 s, segment pacing), BP-170 dramatic-still camera, KP-36 (no still longer than its cap), KP-37 (lane shares), KP-39 (narrator words). New: a VIDEO_3D run of more than three consecutive shots without a STILL_3D or HELPER is REVIEW (anti-monotony, ES rules).

### 7.3 Archetype → lane → Blender technique (the 20 of research report F.1)

| # | Archetype | Default lane | Blender technique (EEVEE unless noted) | Fallback | Reuse |
|---|---|---|---|---|---|
| 1 | Battle / mass conflict | VIDEO_3D | instanced crowd (Geometry Nodes), 2-3 Mixamo cycles, silhouette depth layers, volumetric dust | STILL_3D plate + dramatic curve | crowd rig, dust volume |
| 2 | Duel / one-on-one | VIDEO_3D | two rigged characters, camera on a rail, line art on | STILL_3D freeze | duel cam rig |
| 3 | Two-person dialogue | VIDEO_3D (CU ≤ 5 s voiced) / STILL_3D (over-the-shoulder listener) | shot-reverse-shot template, Rhubarb mouth shapes on 8 shape keys | STILL_3D + off-screen line | dialogue template |
| 4 | Council / group | STILL_3D default, VIDEO_3D for the speaking beat | tableau plate at wide; CU VIDEO for voiced lines | — | hall set |
| 5 | Solitary emotion | STILL_3D | portrait plate, drift; VIDEO only if a gesture carries the beat | — | portrait light rig |
| 6 | Crafting / work | VIDEO_3D | hands + tool animation loop, macro camera | STILL_3D | tool props |
| 7 | Travel / journey | VIDEO_3D | camera dolly over terrain/sea, character cycle, parallax clouds | STILL_3D plate + parallax | terrain kit |
| 8 | Exploration / discovery | VIDEO_3D | slow reveal camera through a set | STILL_3D | set kit |
| 9 | Reveal | VIDEO_3D short | push-in + light change | STILL_3D dramatic curve | — |
| 10 | Chase | VIDEO_3D | tracking camera, two cycles | REJECT as still | — |
| 11 | Environmental establishing | STILL_3D | wide plate, 2.5D parallax or Blender camera drift | VIDEO_3D if weather carries | era set kits |
| 12 | Map | HELPER (archetypes 1-4 of `archetypes.json`) | Python `maps/render.py`; Blender terrain DEFER-BEHIND-TEST (ICD-16) | — | — |
| 13 | Abstract explanation | HELPER (hud/graph archetypes) | Python; Blender only for 3D diagrams (DEFER) | — | — |
| 14 | Transformation / time passing | VIDEO_3D | material/light keyframes on one set, sun arc | STILL_3D x2 with dissolve | — |
| 15 | Crowd / ceremony | VIDEO_3D or STILL_3D | as 1 with slower motion | STILL_3D | crowd rig |
| 16 | Aftermath | STILL_3D | plate, slow drift | — | — |
| 17 | Narrator over evidence | HELPER (tableau/cutaway archetypes 6, 8, 9) | Python tableau | STILL_3D | — |
| 18 | Cold open | VIDEO_3D | the episode's strongest 9/10 beat, ≤ 15 s | — | — |
| 19 | Climax | VIDEO_3D (may use `cycles_hero`) | full motion, justified Cycles | — | — |
| 20 | Ending | STILL_3D | plate, long drift into the credits | — | — |

Share sanity (EST): with the archetype defaults above and a 12-minute script of ~110-130 shots the planner reaches the 60/30/10 band only if roughly 55-65 shots are VIDEO_3D; the planner (ICW-03) allocates by beat intensity first and then swaps STILL_3D/VIDEO_3D shots at the margin until KP-37 passes. No archetype is forced into a lane; the table gives the default and the fallback.

## 8. The 70 / 30 speech model (independent axis)

### 8.1 Definition

- Measured over **audible words**: narrator words / (narrator words + voiced character words), excluding every segment with `voiced: false` (REPO `variant_plan.segments_from_script` line 167).
- Nominal target 0.70 narrator. Band: ICG-1 (OPEN). Reporting adds audible seconds from the final spine (`audio_spine/2` word windows) as a second, informational column; it never replaces the word rule.
- Lip-sync coverage ≤ 5 s per visible voiced shot (BP-108). Voiced lines longer than 5 s are split across a CU and an `off_screen` cover shot (listener, hands, environment) by the planner; the rule is visual, not audio.
- Independence test stays: `test_sourced_rules::test_d95_speech_mix_and_video_duration_rules_are_independent_from_visual_lanes` (REPO) extends to assert BP-105 and BP-109 have no shared key.

### 8.2 Exact changes

| File | Change |
|---|---|
| `explainer_engine/standards/sourced_rules.json` BP-105 | `nominal_narrator_share: 0.70`; `narrator_share` band [0.65, 0.75], severity REVIEW (ICG-1 = A, creator 2026-11-05); source line = the creator's 2026-11-04 direction and the 2026-11-05 answer |
| `scripting/film_shots.py` KP-39 (lines 932-937) | read `nominal` for the planner target; band and severity from the rule |
| `scripting/variant_plan.py` VP-16 (lines 300-302) | same |
| `qa/speech_mix.py` (ADD) | writes `speech_mix_report/1`: narrator_words, dialogue_words, unvoiced_words, narrator_share_words, narrator_share_seconds (from spine), lipsync_shots, lipsync_seconds, longest_voiced_cu |
| `schemas/speech_mix_report.v1.json` (ADD) | schema |
| `qa/scorecard.py` | one row from the report |
| `docs/SOURCED_RULES.md` | regenerate table (`python -m explainer_engine.standards.sourced_rules write`) |
| Tests | `test_sourced_rules` (band/nominal), `test_variant_plan::test_vp16…`, new `test_speech_mix.py` (voiced:false excluded; seconds column from a fixture spine; independence) |

## 9. Style system, world bible and asset architecture

### 9.1 Style tokens (world bible v1.5)

Bible v1.5 (ICW-01 for wording, ICW-05 for the collage): `house_look = "ink_chronicle"`, `source_geometry = "3D (Blender)"`, `final_treatment = "illustrated / graphic-novel"`, `line = {engine: "Blender Line Art modifier", weight_px_1440: [1.5, 3.0], crease_deg: 134}`, `shading = {steps: 3, method: "Shader to RGB + ColorRamp (EEVEE-only)", rim: true}`, `paper = {grain_asset_id, opacity: 0.12}`, `grade = {view_transform: "AgX", look: "Medium High Contrast"}` (EXT: Blender 5.2 manual names the look without the "AgX - " prefix; the PoC failed on the prefixed name). Palette and era tokens stay in `design/palette.json` and `world/eras.json`, hashed in the bible as today.

`banned_drift` rewrite: "photo-realism, photographic lighting or a raw/PBR CGI look in any era". `look_v2.banned_words`: remove "3d render"; add "photoreal", "raw cgi", "pbr"; keep "realistic", "unreal engine", "octane". UR-22 prompt lint reads the same list, so reference-art prompts still refuse photoreal.

Shader to RGB is EEVEE-only and documented as unreliable with ambient occlusion, soft shadows, screen-space reflections and render passes (EXT, Blender 5.2 manual "Shader to RGB"). Consequence: the toon look is built in EEVEE; `cycles_hero` shots use a Cycles-safe variant (ramped diffuse via emission + Line Art) and are compared against the EEVEE look in ICW-09 before any is allowed in an episode.

### 9.2 Continuity

Identity = approved `model` + `material` + `rig` assets with a `bible_version` and a raster turnaround sheet; per-era sets are `scene_template` assets; `qa/identity.py` keeps CLIP comparison of rendered CU frames against the sheet (REPO). Camera language per archetype lives in `visual/archetypes_ic.json` (ICW-03).

### 9.3 Asset library v2 (asset_library/2)

New kinds: `model` (.glb/.fbx/.blend), `rig` (.blend), `animation` (.fbx/.blend; Mixamo cycles retargeted), `material` (.blend node group), `texture` (.png/.exr/.jpg), `hdri` (.exr/.hdr), `blend_collection`, `scene_template`. Required fields unchanged (made_with, licence, approval, lineage, origin, bible_version) plus `deps` (asset ids) and `poly_count` for models. Licence enum extends with `CC0`, `CC-BY-4.0`, `GPL-3.0 (tool only)`, `Mixamo`, `own`. Storage: binaries > 5 MB outside git (the library records a sha256 and an external path; Git LFS is an ICW-05 option, cost per GB to be checked on the GitHub plan before use, OPEN but not blocking).

Source libraries (EXT, read 2026-11-05 unless marked): Poly Haven CC0 (models, textures, HDRIs); MPFB2 (code GPLv3, bundled assets CC0, generated characters the user's property, needs Blender ≥ 4.2); Mixamo (Adobe account, royalty-free in productions, bipedal humanoid only); Rhubarb Lip Sync (MIT, shapes A-H + X, English recogniser or phonetic). Quaternius and KayKit are listed CC0 in the research report (NOT verified here; verify before the first import, ICW-05 acceptance).

### 9.4 AI-assisted asset creation (brief 8.1) — KEEP / CHANGE / REJECT / DEFER-BEHIND-TEST

| Asset class | Disposition | Why |
|---|---|---|
| Hero characters, faces, rigged clothing | REJECT | identity stability (invariant 6, D-41) needs a controlled mesh and rig; image-to-3D meshes (Hunyuan3D-2 / TRELLIS) have no rig, uneven topology and unverified licences for commercial output |
| Props, set dressing, background architecture | DEFER-BEHIND-TEST | ICW-09 benchmark shot B tests one AI-generated prop set vs a Poly Haven/KayKit set on the visual matrix; promote only on PASS and a documented licence |
| Textures, paper grain, decals | DEFER-BEHIND-TEST | same shot; Gemini/other paid image calls remain under D-50 per batch |
| Concept / reference art for the collage | KEEP under D-50 | already how the creator picks a look |
| Everything primary | CC0/CC-BY libraries + MPFB2 + Mixamo + hand-built hero assets | licences verified, outputs owned |

AI-asset PoC matrix (brief 8.1, the representative set, run inside ICW-05/ICW-09; rev. 2): one hero character with **two costume variants**, one secondary/background character, one interior environment, one exterior environment and one modular prop set; each tested under rotation (turntable 360°), close-up, a broad camera move and a representative body motion (walk cycle + one gesture). Pass criteria per asset: no clipping of costume through body in the motion test, identity CLIP distance within the ICW-05 threshold across the three lighting setups, UV/texture seams invisible at 1440p close-up, licence recorded in the library. A static front view is not evidence (brief 8.1). AI-generated candidates are compared against the library/hand-built one on the same matrix; "DEFER-BEHIND-TEST" rows above are promoted only on a full-row PASS.

### 9.5 Adaptive resolution and upscale (brief 8.2)

| Tier | Disposition | Rule |
|---|---|---|
| Native 2560x1440 | KEEP (default) | faces, close-ups, any on-screen text, hero reveals, STILL_3D plates |
| 1920x1080 → Lanczos (`finish/upscale.py`, REPO, ffmpeg) | DEFER-BEHIND-TEST | wide / action VIDEO_3D only; promoted per `render_profile` if ICW-09's line-stability and SSIM checks pass against the native render |
| 1280x720 → upscale | DEFER-BEHIND-TEST, narrow | distant atmosphere / weather only; same test |
| 854x480 → upscale | REJECT (HYPOTHESIS, to be confirmed by the test) | expected: line art at ~2.5 px cannot survive a 3x scale; the brief asks for 480p→1440p in the comparison, so it is rendered in ICW-09 on the three scenes (close-up, wide tableau, action) as a moving sequence and the rejection is confirmed or revised by the line-stability, SSIM and identity checks (rev. 2) |
| AI upscalers (Real-ESRGAN etc.) | DEFER-BEHIND-TEST | compare against Lanczos in the same benchmark; only free, local, licence-checked tools |

The combined model (9.4 + 9.5) changes nothing in the cost model's baseline (section 12 scenario rows are native 1440p); it is an upside recorded as scenario "D" there.

## 10. Shot Specification contract (typed) and migration

### 10.1 shot_spec/2 (JSON Schema, `core/contracts.py` style, no new library)

```
shot_spec/2 = {
  contract: "shot_spec/2", job_id, shot_id, lane: VIDEO_3D|STILL_3D,
  recipe: "blender_eevee/1" | "blender_cycles/1",
  clock: { fps: 24, frames: int ≥ 1, start_tc },
  frame: { width: 2560, height: 1440, render_scale: 1.0|0.75|0.5 (per ICD/9.5, default 1.0) },
  scene: { template_asset, era, set_assets[], characters[{asset, rig, animation|null, position, facing}],
           camera: {rig: static|push|dolly|rail|orbit|dramatic_curve, start, end, lens_mm, ease},
           light_rig, weather|null, props[] },
  performance: { lipsync: bool, rhubarb_json|null, mouth_shapes: 8, dialogue_cover },
  look: { bible_version, line_weight, shading_steps, grade_look, paper_asset },
  render: { profile: eevee_fast|eevee_full|cycles_hero, samples, motion_blur, denoise, output: "mkv_ffv1"|"png_seq" },
  seed, why: string (creator-readable justification, required for cycles_hero)
}
```
Cache key = sha256 of the canonical spec minus job_id/shot_id (REPO `core/shot_cache.key`, unchanged). A profile or asset-version change therefore re-renders; a job rename does not.

Companion contracts: `blender_scene_manifest/1` (what the bpy script built: object counts, asset ids with sha256, bounding boxes, camera path samples) and `blender_render_manifest/1` (Blender version, engine, device, s/frame, frames written, output sha256, log path) — the second feeds `job_speeds` and the ledger.

### 10.2 film_shots/3 and shot_route/2

film_shots/3: lane enum `VIDEO_3D|STILL_3D|HELPER`, new fields of 7.1; everything else from /2 (ids, beats, `why`, `cost`) unchanged. shot_route/2: `recipe` enum adds `blender_eevee/1`, `blender_cycles/1`, `python_helper/1`; `pins` reads a `blender` entry in `config/cloud_pins.json` (version "5.2.3 LTS", image, sha256).

### 10.3 Migration

1. Validators keep /2 readable; `film_shots.visual_lane` dispatches on `contract` (ICW-02).
2. `scripts/migrate_film_shots_2_to_3.py`: KEYFRAME_LTX/ATMOS_BROLL/DIALOGUE_CU → VIDEO_3D (DIALOGUE_CU sets `lipsync: true`), STILL_HOLD → STILL_3D/hold, archetype 8 → STILL_3D/parallax_25d, MAP/COMPENSATOR/GRAPHICS → HELPER, HOST_COMMENTARY and DRAMA_BLOCKED_3D → refuse with the D-89/D-77 message. Dry-run report first; fixtures under `tests/fixtures` regenerated with `--write` and diffed in review.
3. The Napoleon fixture and `script_variants.json` are regenerated in the same package (they are already stale, section 4.1).

### 10.4 Frame-level durable recovery (`render_checkpoint/1`, rev. 2)

The existing guards are necessary but not sufficient (REPO): `core/shot_cache.py` verifies a *finished* shot output by hash; the RunPod heartbeat (LT-17) proves the pod is alive, not that a frame is safe; the vault (`explainer_engine/vault.py`, D-73, `docs/VAULT.md` VT-01..05) proves that *final* outputs reached Hugging Face with the same sha256 before a pod stops. OR-03 ("a stop loses nothing") and OR-33 ("a paid path without step-by-step saving proven by a test does not run") therefore require a per-frame protocol for Blender, which this contract defines.

| Frame state | Meaning | Who sets it |
|---|---|---|
| `RENDERED` | the frame file exists in the pod's work dir and passed the local check (decodes, expected size, expected index, not black unless declared) | `bpy/render_shot.py` after each frame (or each chunk of ≤ 8 frames) |
| `DURABLY_STORED` | the frame (or chunk archive) was uploaded outside the pod to the vault prefix `blender/<job_id>/<shot_key>/frames/` and the remote sha256 equals the local one (`vault.check_uploaded` semantics, per file) | `blender/render.py` uploader thread |
| `COMMITTED` | the atomic checkpoint file `render_checkpoint.json` (written with `core/store.write_json_atomic`, then uploaded) lists the frame with its sha256 and `DURABLY_STORED` time | `blender/render.py` after the remote verify |

Rules: (1) at job start `render.py` downloads the remote checkpoint, verifies every `COMMITTED` frame's remote hash, and renders **only the missing or mismatching frames**; (2) a frame counts for recovery only in `COMMITTED`; (3) the final MKV is built only when every frame is `COMMITTED`, is ffprobe-checked, hashed, uploaded, verified, and only then enters the shot cache; (4) the pod script ends with `python -m explainer_engine.vault check-uploaded` on the shot dir (VT-01) and the `DONE` heartbeat that lets the pod self-stop (D-74) is sent **after** that check and never before; (5) a failed upload or verify keeps the pod STOPPED, never deleted (VT-02); (6) the ledger line records frames committed per dollar, so a cap stop at 350/500 frames keeps 350 paid frames. Upload cost: a 1440p PNG frame is ~3-6 MB (EST); chunked archives of 8 frames keep the upload count at ~1,300 per episode on HF (acceptable; the exact figure is measured in ICW-09 and compared with a per-shot MKV-chunk alternative). Tests (ICW-04, before any paid run per OR-33): a fake renderer + fake vault in `tests/unit/test_blender_render.py` prove kill-at-frame-N → resume renders only N+1.., a corrupted remote frame is re-rendered, a failed upload blocks `DONE`, and the checkpoint write is atomic.

## 11. Minimal module and class tree (status: every class TODO until its ICW lands)

Task-complexity estimator: **FOUND** — `config/model_routing.json` (`classes` with `level` S0-S4 and `model`; `governance/__init__.py::LEVELS`). Sizes below use it: S1 mechanical-change, S2 straightforward-code / phase-from-plan, S3 architecture / new-method-code / pod-plan. The estimator never assigns Fable to code (`code.never_models`), so Opus (S3) takes the design-heavy packages and Sonnet (S1-S2) the mechanical ones. It is a *routing* estimator (which model, which effort), not a calendar or person-hours estimator (NOT FOUND in the repository); section 15 therefore adds an explicit effort and uncertainty line per package (rev. 2).

```
explainer_engine/visual/                              (ICW-03)
  lanes.py        LanePlanner.allocate(film_shots/3 beats) -> shares + swaps until KP-37; report()
  shot_design.py  ShotDesigner.design(beat, archetype) -> shot fields (camera rig, still_mode, lipsync, cover)
  archetypes_ic.json   the 20 archetypes of 7.3 (lane default, fallback, camera language, reuse ids)
explainer_engine/blender/                             (ICW-04/05/06)
  project.py      BlenderProject.resolve(pins) -> path/version/device; refuses an unpinned binary
  profiles.py     RenderProfile (eevee_fast/eevee_full/cycles_hero): samples, AO/SSR flags, denoise, time budget
  style.py        StyleEngine.apply(scene, bible_v1_5) -> Line Art + ramp shading + AgX look + paper (EEVEE path, Cycles-safe path)
  assets.py       AssetResolver.collect(shot_spec) -> local paths from asset_library/2 with sha256 verify
  scene_builder.py SceneBuilder.build(shot_spec) -> blender_scene_manifest/1 (writes the bpy job json)
  rigs.py         RigAdapter.retarget(mixamo_fbx, rig_asset); LipSync.apply(rhubarb_json, shape_keys)
  render.py       HeadlessRender.run(spec, out_dir) -> blender_render_manifest/1 (subprocess: --background --factory-startup
                  --python-exit-code 1 --python bpy/render_shot.py -- <job.json>; per-frame RENDERED -> DURABLY_STORED ->
                  COMMITTED protocol of 10.4 with the vault uploader; resume renders only uncommitted frames, OR-03/OR-33)
  bpy/render_shot.py   the only script that imports bpy; reads job.json, builds, renders, writes manifest
  cost.py         CostModel.estimate(frames, profile, gpu_class, job_speeds) -> ledger line (ESTIMATE until rows exist)
  validate.py     RenderValidator.check(out_dir, spec) -> qa findings (frames, size, fps, black/frozen/flicker, line stability)
explainer_engine/qa/speech_mix.py                     (ICW-03)  SpeechMix.report(script, spine) -> speech_mix_report/1
explainer_engine/training/pods/blender_render.py      (ICW-04)  the committed pod script (OR-21): pulls job json, runs render.py, pushes outputs
explainer_engine/edit/router.py                       (ICW-07)  recipe table v2; VIDEO_3D/STILL_3D -> shot_spec/2
explainer_engine/edit/style_bridge.py                 (ICW-05)  palette/paper/ink tokens for maps/hud/tableau renderers
```
Twelve classes, no Pydantic (the repo validates with JSON Schema in `core/contracts.py`). `assemble.py`, `shot_cache.py`, `ledger.py`, `runpod.py` are reused, not wrapped.

## 12. Provider alternatives, cost model and benchmark protocol

### 12.1 Where Blender can run

| Option | Price (label) | Fit | Disposition |
|---|---|---|---|
| RunPod, RTX 4090 24 GB | $0.34/h community, $0.89/h secure (VENDOR, runpod.io/pricing, page dated 2026-11-04, read 2026-11-05) | the only provider with spend controls already in code (`cloud/runpod.py`, D-56) | KEEP as primary |
| RunPod, RTX 3090 24 GB | $0.22 / $0.50 | cheaper per hour, roughly half the 4090 throughput (Blender Open Data medians quoted in forums: 3090 ≈ 5333 vs 4090 ≈ 10886, EXT but date unverified) | benchmark candidate |
| RunPod, A5000 24 GB | $0.16 / $0.27 | cheapest; EEVEE is rasterised so VRAM matters more than CUDA cores (HYP) | benchmark candidate |
| RunPod, L4 / A40 / A6000 / L40S / A100 | $0.44-1.79 secure | no advantage for EEVEE at this scale | REJECT for now |
| RunPod storage | volume $0.10/GB-mo running, $0.20 idle; network volume $0.07/GB-mo (VENDOR) | a 20 GB asset volume ≈ $1.4-4/mo | include in the recurring line |
| Vast.ai | dynamic marketplace, no static price readable (EXT: pricing pages are JS tables); third-party trackers quote 4090 ≈ $0.39-0.48/h (STALE, EST) | no spend guard in code; would need a second pod manager | REJECT for production; optional benchmark only if RunPod stock fails |
| SheepIt render farm | free, points-based queue, no SLA, 2 GB project limit, contributors run Blender 5.1 (EXT, sheepit-renderfarm.com, read 2026-11-05) | one shot per project upload; queue times unpredictable | DEFER (free overflow for non-urgent STILL plates) |
| GitHub Actions CPU runner | free minutes; the PoC's 120 frames at 720p did not finish in 29.5 min (MEASURED) | smoke tests only | KEEP for the ICW-04 smoke (Workbench, 8 frames) |
| Local machine | $0 | depends on ICG-3 (which machine exists); Blender 5.x needs Apple Silicon + macOS 13 and 8 GB minimum, 32 GB recommended (EXT, blender.org requirements) | OPEN |

### 12.2 Frame budget (EST)

12 min = 720 s x 24 fps = 17,280 frames. VIDEO_3D 60 % → 432 s → **10,368 Blender frames**. STILL_3D 30 % → 216 s → one plate per shot (~40-60 plates); Blender camera-move stills add frames only when chosen (upper bound ~2,000 if every still were a 3D move; baseline 0). HELPER → 0 Blender frames. 15 min scales by 1.25.

### 12.3 Recurring cost per episode (EST; every s/frame is HYP until ICW-09)

| Scenario | s/frame at 1440p EEVEE | GPU-hours for 10,368 frames | 4090 community $0.34 | 4090 secure $0.89 | A5000 secure $0.27 |
|---|---|---|---|---|---|
| A fast (eevee_fast, 16 samples, no SSR) | 1.0 | 2.9 | $1.0 | $2.6 | $0.8 |
| B full (eevee_full, 64 samples, AO+SSR, Line Art) | 3.0 | 8.6 | $2.9 | $7.7 | $2.3 (if the A5000 holds 3 s, HYP) |
| C heavy (Line Art on dense scenes, crowds, volumetrics) | 6.0 | 17.3 | $5.9 | $15.4 | — |
| D with 9.5 tiers (half the VIDEO frames at 1080p ≈ 0.56x cost on those) | B x 0.78 | 6.7 | $2.3 | $6.0 | — |

Add per episode: pod boot and asset sync ~10-15 min, 10-20 % re-renders after QA, Cycles hero shots (if any: ~30-60 s/frame, EST, so one 5-second hero shot ≈ 1-2 GPU-h ≈ $1-2 on a secure 4090), STILL plates (~1 min of GPU), storage $1.4-4/mo. **Benchmark cost (EST, rev. 2):** the cloud pass of 12.4 is ~6 scenes x 2 profiles x 3 repeats x 48 frames at 1440p plus the tier and asset rows ≈ 2.5-3 GPU-hours on a 4090 and ≈ 4-6 on an A5000 at the HYP frame times, i.e. ≈ US$2.5-3 (4090 secure) + US$1.5-2 (A5000 secure) + boot and storage ≈ **US$4-6**; hence the proposed cap of US$6 (the creator saw this figure as option B of ICG-2; the single-pod US$3 answer covered the brief's minimum of one GPU without repeats, so the figure goes back to his word in the OR-23 plan). **Conclusion:** US$10-15 holds for scenarios A, B and D on either tier and for C only on community pricing; a 1440p EEVEE frame slower than ~4 s on a 4090 breaks the target on secure pricing. Line Art is the known cost risk (the manual notes bake/no-cache and instancing costs; EXT). None of this is measured yet.

### 12.4 Benchmark protocol (ICW-09; the OR-23 plan is written from this)

1. **Free preflight (no money):** CI smoke (Workbench engine, 8 frames, 320x180) proves the headless path, `--python-exit-code 1`, manifest output and the validator. Local CPU/Apple-GPU run of the same five shots if ICG-3 allows, to size the first pod.
2. **Local pass first (free, ICG-3 = M4 Pro Mac):** the same scene set as the cloud pass, Blender 5.2.3 LTS, Metal; this is the brief's "local M4 Pro preview and final-render suitability" measurement and it sizes the cloud pass.
3. **Paid cloud pass, two GPU classes** (brief §7: "at least one cloud NVIDIA GPU, ideally two, with at least three repeats"): RTX 4090 and A5000 (RTX 3090 if the A5000 is out of stock), Blender 5.2.3 LTS pinned image, each pod under its own OR-23 plan line, wall-clock cap 1.5 h per pod, money cap per the creator's word (proposed total ≤ US$6, see 12.3 "benchmark cost"). Scenes, 48 frames each (a moving sequence, never a single frame): (S1) dialogue CU with lip-sync and Line Art; (S2) **interior / establishing council tableau** (the brief's second mandatory scene); (S3) crowd battle wide with Geometry Nodes instancing + dust volume; (S4) travel dolly over a Poly Haven terrain + sky HDRI; (S5) STILL_3D plate with a 48-frame camera drift; (S6) S1 under `cycles_hero` 64 samples with denoise. Profiles `eevee_fast` and `eevee_full` (S6 Cycles only). **Three repeats** of every scene x profile x GPU at native 1440p; the record keeps median, spread (min-max) and failure rate, never a single number. Resolution tiers (9.5): S1, S3 and S4 (close-up, action, wide) also at 854x480, 1280x720 and 1920x1080, one repeat each, upscaled to 1440p by `finish/upscale.py`, judged on the moving sequence. AI-asset rows (9.4): S2 and S4 once with the AI-assisted set, once with the library set.
4. **Measured outputs per configuration:** Blender version, scene complexity (objects, triangles, instances), engine/profile, resolution, samples, GPU and VRAM peak, s/frame, wall time including boot and asset sync, output size, failed frames and retries, storage and egress, the actual bill from `runpod cost` (→ `config/job_speeds.json` rows `blender_frame_{profile}_{res}_{gpu}` and the ledger). A cost pass is invalid when the visual row fails (brief §7).
5. **Stop conditions:** per-pod wall-clock cap 1.5 h; any scene above 10 s/frame in `eevee_full` at 1440p stops that series and reports; the Haiku watchdog every 5 min (project rule); every frame follows 10.4, so a stop keeps what was paid.
6. **What the creator sees:** a contact sheet and a 48-frame sequence per configuration (native vs each upscaled tier, EEVEE vs Cycles, AI assets vs library, M4 Pro vs each cloud GPU), the median/spread table, the recomputed section 12.3 with measured numbers, and the GO/NO-GO against US$10-15.
7. **Promotion rules:** a profile or tier enters an episode only if its visual matrix row (section 13) PASSes and its measured cost keeps scenario B under $15 on the chosen tier.

## 13. QA strategy

| Gate (owner) | Check | Tool | Severity |
|---|---|---|---|
| Render validator (ICW-08) | frames == spec.frames, 2560x1440 (or declared tier), 24 fps, no black frame > 2, no frozen run > 12 frames unless `still_mode: hold`, flicker (mean-luma delta > 0.08 between neighbours) REVIEW, Line Art stability (edge-pixel count variance > 25 % between neighbours) REVIEW | `blender/validate.py` (numpy + ffprobe, same style as `qa/frame_review.py`) | FAIL/REVIEW |
| Lane runtime | shares vs BP-109 band | `film_shots.lane_share_findings` (REPO) | REVIEW (ICD-02) |
| Speech mix | words vs BP-105 band; seconds column informational | `qa/speech_mix.py` | REVIEW outside 65-75 (ICG-1 = A) |
| Final-mix speech delivery (rev. 2) | every narrator and voiced-dialogue word window of `audio_spine/2` is checked on the **final mixed stem**: RMS above the ED-12 dropout floor inside the window (missing / muted / cut word), no window overlapping another speaker's (duplicated line), no `voiced:false` segment with speech energy, total voiced seconds within 10 % of the spine; uses the spine's word timings and the existing `audio/dropouts.py` scan, **no ASR dependency** | `qa/speech_mix.py::delivery_findings` over `build_audio_v2` output | FAIL on a missing or duplicated line, REVIEW on a cut word |
| Shot rhythm | BP-108/109/169 caps, KP-36 | `film_shots.episode_check` (REPO) | as today |
| Identity | CU frames vs approved turnaround sheet, CLIP distance | `qa/identity.py` (REPO) | REVIEW |
| Style conformance | palette histogram within the era's grade, paper layer present, no photoreal cue (specular highlight ratio) | `blender/validate.py::style_findings` | REVIEW |
| Cost | ledger line vs estimate within 25 % | `core/ledger.py` + `blender/cost.py` | REVIEW; stop at 80 % of cap (invariant 2) |
| Assembly | CN-09 one fps, clip present per shot, OTIO | `assemble.plan_video_v2` (REPO) | FAIL |
| Creator | collage of 5 style-sheet scenes (ICW-05); contact sheets of the benchmark (ICW-09); sample of the first two parts (ICW-10, OR-19) | review bundle | approval |

Visual acceptance matrix (used by ICW-05/09/10): line weight visible at 1440p and after YouTube's re-encode (check at 1080p playback), three-step shading readable, no PBR gloss, paper grain present but under 15 % opacity, faces consistent across three lighting setups, text never rendered inside Blender (HELPER only), motion readable at 24 fps without strobing (shutter 180°).

## 14. TODO disposition register

| Group | Count (REPO) | Disposition | Proof required | Package |
|---|---|---|---|---|
| `CLAUDE-MASTER-MOLD-SYNC` header blocks | 296 files | REMOVE | `git diff --stat`; AST equality of every module before/after (`ast.dump` compare script); unit suite green minus `cv2`; repo-hygiene docstring tests pass as on `main` | ICW-00 |
| `CLAUDE-CLASS-SYNC` lines | 88 lines / 35 files | REMOVE | same | ICW-00 |
| Empty "Stub specification module" files (33 non-Ink-Chronicle) | 33 | REMOVE ONLY AFTER CALLER AND TEST PROOF | grep over `explainer_engine`, `tests`, `scripts`, `.claude`, `docs` shows no importer; `python -m compileall`; suite green | ICW-00 |
| Ink Chronicle planning stubs (`video/generator.py`, `keyframes.py`, `scene_builder.py`, `tier_router.py`) | 4 | REWRITE AS WORK PACKAGE → replaced by `visual/` and `blender/` modules, then REMOVE | the new modules land with tests | ICW-04/06/07 |
| `docs/wip/CLAUDE_MASTER_MOLD_HANDOFF_2026-11-04.md`, `docs/wip/CLAUDE_MASTER_MOLD_EXECUTION_GUIDE_2026-11-04.md` | 2 | HISTORICAL (already bannered) | none | ICW-01 moves them to `docs/archive/` |
| `scripts/validate_mold_compliance.py` | 1 | REMOVE after the blocks are gone | no caller | ICW-00 |
| Genuine code TODO (`qa/blind_check.py:3`) | 1 | KEEP, unrelated | — | — |
| Opus-plan `TODO_REGISTER.md` ids | TODO-RULE-01..13 → ICD-01..17; TODO-VIS → ICW-03; TODO-ARCH → ICW-04/06/07; TODO-COST → ICW-09; TODO-QA → ICW-08; KEEP-RULE-01/02 (24 fps, spend guards) → ICD-08/15 | ADAPT | — | — |
| Old LTX/Qwen P12 pod scripts, `config/cloud_pins.json` LTX entries | KEEP, mark `legacy` | — | after the pilot, a creator-word cleanup | ICW-07 (marking) |
| Cited-but-undefined ids (D-96, BP-155, BP-68, BP-79) | 4 | ADD definitions or fix citations | docs_lint and `test_sourced_rules` clean | ICW-01 |

## 15. Phases and Opus work packages

Dependency order and the critical path: **ICW-00 → ICW-02 → ICW-04 → ICW-06 → ICW-07 → ICW-09 → ICW-10**. ICW-01, ICW-03, ICW-05, ICW-08 run in parallel lanes. Integration owner of every merge into the working branch: the Opus thread that runs ICW-07. Complexity uses `config/model_routing.json` levels; "effort" is the agent effort ceiling of that class. Rev. 2 adds an explicit size and uncertainty per package (EST, Fable's judgement, not measured): size S = under ~300 changed lines and one session, M = ~300-1,000 lines or two to three sessions, L = above that or dependent on an external tool; uncertainty L/M/H says how likely the acceptance line moves once the work starts.

| Package | Size | Uncertainty | Why |
|---|---|---|---|
| ICW-00 | M (296 files, comment-only) | L | mechanical, proof by AST compare |
| ICW-01 | S | L | docs and registry rows |
| ICW-02 | M | M | fixture churn, /2 compatibility |
| ICW-03 | M | M | planner heuristics may need two rounds on real scripts |
| ICW-04 | L | H | first real Blender code in the repo; CI download/time; 10.4 protocol tests |
| ICW-05 | L | H | style engine + creator collage; licences; storage decision |
| ICW-06 | L | H | rigs, retarget, lip-sync quality |
| ICW-07 | M | L | assembly already consumes clips |
| ICW-08 | M | M | thresholds need the benchmark's frames |
| ICW-09 | M code, paid | H | stock, frame times unknown |
| ICW-10 | M | H | depends on ICW-09 GO and the creator's script |

| Phase | Packages | Money |
|---|---|---|
| 0 Hygiene | ICW-00 | $0 |
| 1 Rules and contracts | ICW-01, ICW-02, ICW-03 | $0 |
| 2 Blender runtime and style | ICW-04, ICW-05 | $0 (CI smoke; reference art under D-50 if the creator orders it) |
| 3 Scenes and integration | ICW-06, ICW-07, ICW-08 | $0 |
| 4 Benchmark | ICW-09 | ICG-2 line (proposed ≤ $3), after the OR-34 Fable audit |
| 5 Pilot | ICW-10 | render of the first two parts: estimated from measured rows, approved per OR-19/OR-23 |

**ICW-00 Branch hygiene and green baseline** — S1 (mechanical-change, Sonnet). Objective: remove the Master Mold header blocks and class lines, delete the 33 proven-orphan stubs and `scripts/validate_mold_compliance.py`, regenerate the stale sourced-rules table and the Napoleon fixtures (`python -m explainer_engine.standards.sourced_rules write`; `python -m explainer_engine.scripting.variant_plan napoleon --write`), fix the three undefined BP citations. Non-goals: any behaviour change. Prerequisites: none. Paths: 296 files (list from `grep -rl CLAUDE-MASTER-MOLD-SYNC explainer_engine`), `docs/SOURCED_RULES.md`, `tests/fixtures/**napoleon**`. Reused: `tests/unit/test_repo_hygiene.py`. Sequence: AST snapshot → strip → AST compare → delete stubs → regenerate → full suite. Contracts: none. Tests/commands: `python -m pytest -m "not system and not media"` (expect only the 6 `cv2` failures where cv2 is absent), `python -m explainer_engine.docs_lint`. Acceptance: the 11 inherited failures are gone; `git diff --stat` touches comments, stubs, generated docs and fixtures only. Risks: a stub that a `.claude` agent page names (checked by `test_agent_governance`) — the test will say so; rollback = revert the single commit. Confidence H. Parallel: none (everything rebases on it).

**ICW-01 Decision log, rules registry, bible wording, docs** — S2 (Sonnet). Objective: write D-96 and ICD-01..17 into `docs/DECISIONS_AND_OPEN_QUESTIONS.md`; BP-105 nominal + band (after ICG-1), BP-109 unchanged, new BP rows for Line Art weight and flicker thresholds marked `house` until sourced; bible v1.5 wording and look_v2 ban list (ICD-06); P-12/P-13 note; archive the two wip guides; `docs/INDEX.md`, `docs/PROGRESS.md`. Prerequisites: ICW-00, ICG-1 answer. Paths: `docs/DECISIONS_AND_OPEN_QUESTIONS.md`, `standards/sourced_rules.json`, `world/bible.json`, `world/look_v2.json`, `docs/VIDEO_PARAMETER_SPEC.md`, `docs/archive/`. Tests: `test_sourced_rules`, `test_world_bible` (rehash), `test_docs`, docs_lint clean. Acceptance: docs_lint 0 findings. Risks: none technical. Confidence H. Parallel with ICW-02.

**ICW-02 Contracts and fixtures** — S3 (architecture-design, Opus). Objective: film_shots/3, shot_spec/2, shot_route/2, blender_scene_manifest/1, blender_render_manifest/1, speech_mix_report/1, asset_library/2 schemas + validators in `core/contracts.py`; CN-08 lane-conditional; `film_shots.visual_lane` version dispatch; migration script and regenerated fixtures (10.3). Non-goals: renderer code. Prerequisites: ICW-00. Paths: `explainer_engine/schemas/*.json`, `core/contracts.py`, `scripting/film_shots.py`, `scripts/migrate_film_shots_2_to_3.py`, `docs/CONTRACTS.md`, `tests/fixtures/`. Reused: `C.validate`, `cross_fps`, `shot_cache.key`. Tests: `test_contracts` (+ /3 cases, refused lanes still refused, CN-08 conditional), `test_film_shots`, `test_shot_cache` (key stable across job rename, changes on profile), new `test_migrate_film_shots.py`. Acceptance: /2 fixtures still validate; /3 fixtures validate; migration dry-run report checked in. Risks: fixture churn; rollback = keep /2 the default until ICW-07. Confidence H.

**ICW-03 Lane planner, archetype registry, speech report** — S2-S3 (Opus designs, Sonnet may implement). Objective: `visual/lanes.py`, `visual/shot_design.py`, `visual/archetypes_ic.json` (7.3), `qa/speech_mix.py` (8.2), VP/KP updates. Prerequisites: ICW-02; ICG-1. Reused: `film_shots.lane_shares`, `variant_plan.dynamics`, `audio/spine.py`. Tests: `test_visual_lanes.py` (allocation hits 60/30/10 within band on three fixture scripts; anti-monotony REVIEW), `test_speech_mix.py`, `test_variant_plan` updates. Acceptance: Napoleon fixture plans at 60/30/10 ± 5 and 70/30 words within the band. Risks: scripts that cannot reach the band (too much dialogue) → REVIEW, never silent rewrite. Confidence M.

**ICW-04 Blender project resolver, headless adapter, pod script, CI smoke** — S3 (new-method-code, Opus). Objective: `blender/project.py`, `profiles.py`, `render.py`, `bpy/render_shot.py`, `cost.py` skeleton, `training/pods/blender_render.py`, `.github/workflows/blender-smoke.yml` (ubuntu-24.04, Blender 5.2.3 LTS pinned by sha256, Workbench engine, 8 frames at 320x180, `--background --factory-startup --python-exit-code 1`, `timeout-minutes: 15`), `config/cloud_pins.json` blender entry, `config/job_speeds.json` rows (empty). Non-goals: style, characters. Prerequisites: ICW-02. Reused: `cloud/runpod.py` create/guard/stop, `core/ledger.py`, `core/store.write_json_atomic`. Tests: `test_blender_render.py` with a fake `blender` executable on PATH (asserts the argument order, exit-code propagation, per-frame resumability, manifest schema); the real smoke runs only on CI. Acceptance: CI smoke green with 8 PNG frames uploaded as an artifact (the first verified Blender output in the project); the pod script passes the OR-21 governance test. Risks: Blender download size/time on CI (~300 MB) → cache the archive; a Blender 5.3 release on 2026-11-10 (EXT) must not move the pin. Confidence M-H.

**ICW-05 Style engine, asset library v2, style sheets** — S3 (Opus) + creator collage. Objective: `blender/style.py` (9.1 EEVEE path + Cycles-safe path), `blender/assets.py`, `assets/library.py` v2 kinds and storage rule (9.3), `edit/style_bridge.py` for HELPER renderers, five style-sheet scenes (one per archetype family: dialogue CU, battle wide, travel, establishing, map-adjacent tableau) rendered via ICW-04 on CI or locally (ICG-3) at 1440p single frames; one collage for the creator (invariant 6). Prerequisites: ICW-04; licence verification of every imported asset (Quaternius/KayKit NOT verified yet). Tests: `test_asset_library` v2, `test_style_bridge.py` (palette tokens applied, deterministic output), `test_blender_style.py` (node-tree builder unit-tested without bpy via a recorded graph). Acceptance: the creator approves one collage variant; bible v1.5 rehashed. Risks: Shader to RGB artefacts with AO/SSR (EXT) → profiles disable SSR by default; rollback = keep the collage, drop the profile flag. Confidence M.

**ICW-06 Scene builder, camera rigs, character rig adapter** — S3 (Opus). Objective: `blender/scene_builder.py`, `rigs.py` (Mixamo retarget onto MPFB2 rig, Rhubarb → 8 shape keys, 5-second cap enforced), camera rigs of 10.1, `blender_scene_manifest/1` output. Prerequisites: ICW-04, ICW-05. Tests: builder unit tests on recorded graphs; a CI smoke scene with one rigged character and one camera rail (Workbench). Acceptance: the five benchmark shots of 12.4 build headless without error. Risks: Mixamo retarget quality → fallback to hand-keyed cycles for the pilot. Confidence M.

**ICW-07 Router, cache, assembly integration** — S2-S3 (Opus integrates). Objective: `edit/router.py` recipe table v2, `shot_route/2` writing, `cloud_pins` legacy marks, end-to-end: film_shots/3 → shot_spec/2 → (fake renderer) → `shots/<id>.mkv` → `build_video_v2` → episode.mp4 with CN-09 intact. Prerequisites: ICW-02, ICW-04, ICW-06. Reused: everything in `assemble.py` unchanged. Tests: `test_shot_router` v2 (HELPER path unchanged, refused lanes), `test_assemble_video_v2` with Blender-named clips, `test_ic_end_to_end.py` with a fake renderer writing FFV1 via ffmpeg. Acceptance: the fake-renderer episode assembles with the audio spine; no change to `assemble.py` needed (if one is, it is a reported deviation). Risks: FFV1 MKV decode in the assembly pipe (ffmpeg present) → verified in the test. Confidence H.

**ICW-08 QA validators and reports** — S2 (Sonnet). Objective: `blender/validate.py` (section 13 rows), scorecard rows, lane runtime and speech-mix reports in the review bundle. Prerequisites: ICW-03, ICW-07. Tests: synthetic clips (black run, frozen run, flicker, edge-count jump) each trigger exactly their finding. Acceptance: validator findings appear in `qa_report/1`. Confidence H.

**ICW-09 Benchmark harness, job speeds, cost estimator** — S3 pod-plan (Opus writes the OR-23 plan; Fable OR-34 audit; creator's money word ICG-2). Objective: 12.4 end to end; `blender/cost.py` reads measured rows; section 12.3 recomputed and committed; GO/NO-GO. Prerequisites: ICW-05..08; ICG-2 and ICG-3 answered; a `paid_tests` line in `config/spend_caps.json` (hook-protected: creator's word via `governance ok`). Tests: `test_blender_cost.py` (estimate from rows; refuses when rows are empty; 80 % stop). Acceptance: rows filled, contact sheets reviewed, verdict recorded in the decision log. Risks: RunPod stock shortage (memory: recent shortages) → retry window in the plan; cost overrun → wall-clock cap and watchdog. Confidence M.

**ICW-10 Pilot sample (first two parts)** — S3 plan, Sonnet runs. Objective: the next approved script's first two parts rendered through the full chain (OR-19, D-67, `production/sample.py`), reviewed by the creator before the rest is paid. Prerequisites: ICW-09 GO; creator approval of the script and of the OR-23 pod plan. Acceptance: the creator approves the sample. Confidence M.

## 16. Risk register and stop/go

| Risk | Likelihood | Impact | Mitigation | Stop condition |
|---|---|---|---|---|
| EEVEE 1440p frame > 4 s with Line Art | M | cost target missed | profiles, 9.5 tiers, Line Art only on hero objects | ICW-09 shot above 10 s/frame stops the series |
| Shader-to-RGB artefacts (AO/SSR) | M | look unstable | SSR off by default, AO baked into ramp | collage rejected twice → re-plan style |
| Identity drift across shots | M | invariant 6 | one rig/material set, CLIP check | identity REVIEW on > 10 % of CU shots |
| Asset licences (Quaternius/KayKit unverified) | L | rights | verify before import, library records licence | any unverifiable licence → asset refused |
| RunPod stock / price change | M | schedule | three GPU classes benchmarked, community+secure | none (retry) |
| Blender 5.3 release moves the pin | H (2026-11-10) | reproducibility | sha256-pinned 5.2.3 LTS | pin changes only by decision log entry |
| Branch base carries a red suite | certain today | every later test is noise | ICW-00 first | ICW-00 not green → nothing else merges |
| Local machine absent (ICG-3 = C) | ? | no free previews | CI smoke + SheepIt for plates | — |
| Lip-sync quality (Rhubarb 8 shapes) | M | dialogue CU reads poorly | 5-second cap, off-screen cover | creator rejects the CU style sheet → shorten CU cap to 3 s (new creator question) |

Go/no-go gates: G1 after ICW-00 (suite green as on `main`); G2 after ICW-05 (collage approved); G3 after ICW-07 (fake-renderer episode assembles); G4 after ICW-09 (measured cost ≤ $15 scenario B); G5 after ICW-10 (sample approved). Each gate is one line in `docs/PROGRESS.md` and the decision log.

## 17. Consolidated Creator Decision Gate

Only three items are genuinely the creator's; everything else is decided above (RECOMMENDED) or proven by a test. Each is asked one at a time, A-D, with a recommendation, and waited for.

**ICG-1 — 70/30 speech enforcement mode. ANSWERED 2026-11-05 07:37 UTC: A (CREATOR).** A (recommended): nominal 70/30, REVIEW band 65-75 % narrator words; outside the band the script goes back to the writers' room with a finding, never a silent rewrite. B: hard FAIL outside 65-75 (script lock refused). C: keep D-95's band 70-80 with the nominal moved to 70 (no FAIL change). D: no validator, report only. Reasoning: A matches the creator's 2026-11-04 direction (nominal, not a hard ratio) and the repo's habit of REVIEW-level house rules; B blocks scripts that are otherwise approved; C keeps a band that excludes the creator's own nominal at its lower edge; D removes the guard the creator asked to keep.

**ICG-2 — money for the first Blender benchmark. ANSWERED 2026-11-05 07:42 UTC in words (CREATOR): "if the test's purpose is to measure Blender's price, we run a small test on RunPod and count; visual checks use the local machines" = A in substance; the exact money line is fixed in the OR-23 pod plan (proposed ≤ US$3) and needs his word there.** A (recommended): one RTX 4090 pod, new `paid_tests` line ≤ US$3, wall-clock cap 1.5 h, after the OR-34 Fable audit. B: two GPU classes (4090 + A5000) ≤ US$6 in one session. C: local only, $0, no pod (needs ICG-3 = A). D: defer the benchmark until the pilot script is approved. Reasoning: A answers the one unknown (s/frame) that every cost claim depends on, at the price of one coffee; B gives a second price point but doubles the money before the first number exists; C depends on a machine we have not confirmed; D leaves section 12 hypothetical through the whole build.

**ICG-3 — local machine and invariant 1. ANSWERED 2026-11-05 07:45 UTC: A, the M4 Pro Mac (CREATOR); at 07:42 he confirmed both machines exist (an RX 5700 PC and an M4 Pro Mac) and that visual checks run locally.** Consequence: invariant 1 is amended in ICW-01 ("free local Blender renders for review, style sheets and benchmark preflight run on the creator's Mac; paid work stays cloud-first; the PC reviews and uploads"). Verified for the choice (EXT, Blender 5.2 manual "GPU Rendering", read 2026-11-05): Cycles HIP needs RDNA1 or newer on Windows/Linux (RX 5700 qualifies) with Radeon Software 24.9.1+ on Windows, but hardware ray tracing and GPU denoising need RX 6000 or newer; Metal is supported on Apple Silicon with macOS 13+ for all features; EEVEE needs OpenGL 4.3 / Vulkan 1.3 (both machines) and Blender recommends 8 GB VRAM (the RX 5700 has exactly 8 GB; the M4 Pro shares its unified memory). Recommendation: the Mac renders the style sheets, previews and benchmark preflight; the PC stays review/upload (invariant 1) and a fallback for EEVEE checks. A (recommended if true): a Mac with Apple Silicon and ≥ 16 GB exists and may run free Blender previews and the five style-sheet renders (invariant 1 amended: "free local renders for review are allowed; paid work stays cloud-first"). B: the machine exists but stays review-only (invariant 1 unchanged; all renders on CI or pods). C: only the older PC (i5-8400 / RX 5700, per the TMR repo notes) exists → cloud only; Blender 5.x on that GPU is untested here. D: another machine (the creator names it). Reasoning: Blender's minimum is 8 GB RAM / 2 GB VRAM and the recommended spec is 32 GB (EXT); a free local path removes the only paid step before the pilot except the benchmark, and the direction document's "M4 Pro 24 GB" mention is unverified in this repository (NOT FOUND in any committed file).

All three items were answered on 2026-11-05 (07:37, 07:42, 07:45 UTC); ICW-01 moves them into the decision log as D-rows. The gate is closed.

## 18. Opus launch checklist and verdict

| # | Item | State |
|---|---|---|
| 1 | Branch `opus/ink-chronicle-blender-visual-system-2026-11-04` is the only working branch; `main` untouched | done |
| 2 | Branch reconciliation with dispositions (section 3) | done |
| 3 | Code-path audit with file/line evidence (section 4) | done |
| 4 | Decision matrix ICD-01..17 (section 6) | done; ICD-03/06/15 wait on the creator (money/collage/band) |
| 5 | Contracts and module tree (sections 10, 11) | done |
| 6 | Cost model with labelled numbers and a benchmark protocol (section 12) | done (rev. 2: M4 Pro + two cloud GPUs, 3 repeats, 6 scenes, 4 tiers); every s/frame is HYP |
| 6a | Frame-level durable recovery contract (10.4) and its OR-33 tests in ICW-04 | specified (rev. 2); proven only when ICW-04's tests pass |
| 6b | Independent review of 2026-11-05 answered finding by finding (section 19) | done |
| 7 | TODO register (section 14) | done |
| 8 | Work packages with tests and acceptance (section 15) | done |
| 9 | Test suite baseline recorded (section 4.1) | done; red on the base, green on `main` |
| 10 | Creator Decision Gate | ICG-1 = A, ICG-2 = A in words (money figure in the OR-23 plan), ICG-3 = A (M4 Pro Mac); **all answered 2026-11-05** |
| 11 | OR-34 Fable audit before the first paid test | pending (after ICW-08) |
| 12 | Creator's explicit word to launch Opus | pending — OPUS READY does not grant it |

Safe checks run for this document: `git status`/`git log`/`git diff` across the five branches; `python -m pytest -m "not system and not media"` on FINAL and on a `main` worktree (removed after); `python -m explainer_engine.docs_lint` (one pre-existing finding, D-96); `git diff --check`. Not run: anything paid, any pod, any Blender render, `main` changes, PRs.

**OPUS READY — creator decisions resolved; no blocking unknowns remain.**


## 19. Independent review of 2026-11-05 — finding-by-finding response (rev. 2)

The creator forwarded an independent technical review of revision 1 (2026-11-05 08:02 UTC). Each finding was checked against the brief and the repository before this revision. Verdicts: **ACCEPT** (the review is right; fixed above), **PARTIAL** (right in part; what changed and what did not), **REJECT** (not supported; evidence).

| # | Review finding | Verdict | Evidence and what changed |
|---|---|---|---|
| R1 | Frame-level recovery after a pod loss is not specified; the shot cache is not frame-level durability | **ACCEPT** | REPO: `core/shot_cache.py` hashes finished outputs only; the vault (`vault.py`, VT-01) checks final uploads; the heartbeat (LT-17) is liveness. OR-03 and OR-33 require step-by-step saving proven by a test. Added 10.4 (`render_checkpoint/1`, states RENDERED / DURABLY_STORED / COMMITTED, resume renders only uncommitted frames, DONE only after `vault check-uploaded`, tests in ICW-04) |
| R2 | Benchmark must use the M4 Pro and at least one, ideally two, cloud GPU classes | **ACCEPT** | brief §7 line 271 says exactly that; rev. 1 planned one 4090 pod. 12.4 now has a free local pass (ICG-3 = Mac) and two cloud classes (4090 + A5000/3090) |
| R3 | Three repeats per configuration with median, spread, failure rate | **ACCEPT** | brief §7 "at least three repeats"; added |
| R4 | Interior / establishing tableau missing from the scenes | **ACCEPT** | brief §7 names it as the second mandatory scene; added as S2 |
| R5 | AI-asset workflow does not cover the hero with two costumes, secondary character, interior, exterior, modular props, rotation/close-up/camera/motion | **ACCEPT** | brief §8.1 line 312; added the matrix in 9.4 |
| R6 | 480p must be in the comparison; its rejection was premature | **ACCEPT** | brief §8.2 lines 321-347 ask for 480p→1440p on three scenes and allow rejecting it afterwards; 9.5 marks 480p REJECT as a HYPOTHESIS confirmed by the test, and 12.4 renders it |
| R7 | Final-mix audio QA (missing, muted, cut, duplicated words) is not covered by script or spine counts | **ACCEPT** | NOT FOUND in rev. 1; the repo has ED-12 `audio/dropouts.py` and spine word windows but no per-word check on the mixed stem. Added to section 13 without an ASR dependency, as the review asked |
| R8 | The complexity estimator is a routing table, not an effort/uncertainty estimate | **ACCEPT** | `config/model_routing.json` routes models; section 11 now says so and section 15 adds size and uncertainty per package |
| R9 | The $10-15 target is a hypothesis until measured | **ACCEPT (already stated)** | rev. 1 labelled every s/frame HYP and the conclusion EST; unchanged, restated in 12.3 |
| R10 | The Blender PoC proves only headless start and scene preparation | **ACCEPT (already stated)** | section 3.5 says the same; unchanged |
| R11 | Nothing from the new Blender architecture should be removed; legacy only after caller/test proof | **ACCEPT (already stated)** | sections 5 and 14 say so; unchanged |
| R12 | OPUS READY must not be read as implementation permission; the review would not start Opus until the gaps are specified with testable acceptance criteria | **PARTIAL** | agreed on the reading: READY was never permission (section 18 item 12). The gaps named by the review are now specified with acceptance lines (10.4 tests, 12.4 records, 9.4 pass criteria, 13 severities). What this revision cannot do is prove them: proof comes from ICW-04's tests and ICW-09's measurements. The verdict therefore stays READY for ICW-00..08 (US$0) and the paid benchmark keeps its two gates: the OR-34 Fable audit and the creator's money word on the OR-23 plan |
| R13 | "Vault specification" and "Vault implementation" were not used by the roadmap | **ACCEPT** | rev. 1 never cited `docs/VAULT.md`, `explainer_engine/vault.py` or `config/vault.json` (REPO, D-73); 10.4 now builds on them instead of inventing a store |

Money consequence of R2/R3: the benchmark's proposed cap moves from US$3 (one pod) to US$6 (two classes, three repeats; 12.3 "benchmark cost"). The creator's ICG-2 answer approved the principle (cost measured on a small RunPod test); the figure is his word on the OR-23 plan before ICW-09, as before.
