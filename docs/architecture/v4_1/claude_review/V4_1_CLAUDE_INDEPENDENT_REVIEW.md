# V4.1: Claude Independent Review

- **Document:** `V4_1_CLAUDE_INDEPENDENT_REVIEW.md`
- **Date:** 2026-11-19, 12:35 Georgia time
- **Role:** independent Principal Engineer / Architecture Review Board. This is a report only. No repository file, configuration or code was changed.
- **Reviewed package:** the seven V4.1 documents. They are byte-identical to `Explainer_Engine_V4_1_Blueprint_And_Review_Package_v2.zip` on Google Drive (SHA-256 match on all seven files).
- **Final authority:** the Creator.

**Evidence labels used in this report**

| Label | Meaning |
|---|---|
| `VERIFIED` | I opened the file or ran the command myself in this session. |
| `MEASURED` | A number produced by a tool I ran on the real file in this session. |
| `REPORTED` | Stated by the V4.1 documents or project notes. I did not reproduce it. |
| `NEEDS_EVIDENCE` | Cannot be decided from what exists today. |

Line numbers refer to the Drive code snapshot `eb80e443` unless a different commit is named.

---

## მოკლედ (შემქმნელისთვის)

- **ვერდიქტი: `APPROVED_WITH_MANDATORY_AMENDMENTS`.** მიმართულება სწორია. გეგმა ისე, როგორც წერია, ჯერ ვერ დაიწყება.
- Gemini-ს კოდი (`eb80e443`) მხოლოდ Drive-ზეა, GitHub-ზე არ არის. ჩამოვტვირთე და შევამოწმე. გეგმის ხაზის ნომრები მას ზუსტად ემთხვევა.
- ტესტები: GitHub-ის ბაზაზე 4467 გავიდა, 0 ჩავარდა. Gemini-ს „177 ჩავარდნილი ტესტი" ვერ დავადასტურე.
- 1914-ის ექვსი ნედლი კლიპი HF-ზე დევს. გავზომე ხმა და დრო. ჟურნალში ჩაწერილი დროები ემთხვევა.
- მთავარი ხარვეზები: (1) ახალი სქემის სახელი `av_events/1` უკვე დაკავებულია და ცოცხალ ფაილს გააფუჭებს; (2) WP-02 არასწორ ადგილებს ეხება; (3) ხუთი ახალი მოდული იმეორებს იმას, რაც კოდში უკვე არის; (4) გეგმის ექვს ნაწილს სპეციფიკაცია საერთოდ არ აქვს; (5) Skills-ის შერწყმა 21-დან 12-მდე ცოდნას დაკარგავს.
- YouTube-ის რისკი: ხმის ბიბლიოთეკაში 34 BBC ხმაა (ლიცენზია მხოლოდ არაკომერციულია). 1914-ის ხმის გეგმა მათგან 6-ს იყენებს.
- რეკომენდაცია: ჯერ ჩაირთოს ის შემოწმებები, რაც კოდში უკვე წერია და არ მუშაობს. ეს 1914-ის სამ ხარვეზს ახალი არქიტექტურის გარეშე ასწორებს.

---

## 1. Executive verdict

### Overall verdict: `APPROVED_WITH_MANDATORY_AMENDMENTS`

What this verdict means, precisely:

1. **The architecture direction is approved.** Closed-loop, observation-driven production on the existing `episode/run.py` runner, with no new orchestrator, is the right answer to the 1914 failures. No ADR is rejected.
2. **The work-package plan is not executable as written.** `WP-02`, `WP-04`, `WP-05` and `WP-10` are rejected as written and must be re-issued. `WP-03`, `WP-07`, `WP-08` and `WP-09` cannot be judged because they have no specification, tests or acceptance criteria.
3. **This is not permission to start `WP-02`.** Section 13 lists twelve conditions. `WP-02` starts only when all twelve are met and the re-issued `WP-02` specification has been confirmed by the planning thread (OR-24, OR-26) and the Creator.

### The ten findings that decide the verdict

| # | Finding | Label |
|---|---|---|
| 1 | The baseline the documents call "verified" (`argon/p1-2-timing-contract`, `0592114`, code `eb80e443`) is **not on GitHub**. The code exists only as `REPO_TEXT_argon-p1-2-timing-contract_eb80e443.zip` on Drive. I downloaded it. Its delta against the newest pushed commit `fc35615` is small and coherent (4 modules, 1 schema, 10 fixtures, 9 test files). The plan's line numbers match this snapshot exactly. | `VERIFIED` |
| 2 | The proposed contract name **`av_events/1` is already a live contract** (`episode/events.py` L44, `production_script.schema.json`, the real file `episodes/ep_truce_1914/production/av_events.json`). The real file fails the proposed schema. | `VERIFIED` |
| 3 | **Six specifications the brief points to do not exist**: the inspection router's rules, the media clocks API, the cut-on-action rules, the cross-vendor critic, the fusion rules (only a five-row example table exists) and `RouteRegistry`. An implementer would have to invent them. | `VERIFIED` |
| 4 | `WP-02` names **the wrong integration points**. LTX generation and ingest run outside the runner. The real cut point is `videolane/ingest.py`, which is in no allowlist. The voice stage (G6) runs before the clips stage (G7) and already consumes the trimmed clips. `scene.build` has no caller in the runner. | `VERIFIED` |
| 5 | **Observation already exists and is not enforced.** `videolane/scene.py` already reconciles the prompt with the perceived start picture and returns `regeneration_required`. Nothing reads that flag. The real gap is enforcement, not a missing observer. | `VERIFIED` |
| 6 | Five proposed modules **duplicate existing ones** (`perceive_picture.py`, `ingest.py` edit points, `perceive_audio.py`, `look_and_listen.py`, `continuity_card/1`). Three existing fixes for 1914 defects sit in the code with zero production callers. | `VERIFIED` |
| 7 | **The reported "177 failing tests" are not reproduced.** The CI command on `fc35615` gives `4467 passed, 20 skipped, 3 deselected, 1 xfailed, 0 failed`. The eleven suites named in the plan give `230 passed, 1 skipped` on both `fc35615` and `eb80e443`, not `164 passed`. | `MEASURED` |
| 8 | The audio fusion table was **written without the media**. I measured the six raw clips. The measured onsets match the corrections log, but one table value is an assumption that the measurement contradicts (`S03_SH007` has a clear sound event, so "VAD = False" is not established). | `MEASURED` |
| 9 | **`RetakePipeline` exists at the pinned commit `e98f6d92`.** No pin bump is needed for availability. Its API differs from `c1b4675`, audio-only retake needs a Python call inside the Modal worker, and any worker edit forces a paid ladder re-proof. | `VERIFIED` |
| 10 | The enforcement design (Level B and C) has **three technical holes**: the hook does not bind Gemini's offline sandbox or shell edits, the CI step `pytest -m "unit"` selects zero tests, and two of the four "forbidden" config files are not protected today. | `VERIFIED` |

### What was inspected and what was not

| Area | What I did | Limit |
|---|---|---|
| Documents | Read all seven; checked hashes, cross-references, manifest. | The companion `v4_1_schemas.json` named in DOC-03 is not in the package. |
| Code | Read function bodies on `fc35615` (GitHub) and on `eb80e443` (Drive zip, rebuilt as a full tree). | Commit `0592114` itself is not available anywhere I can reach. Its difference from `eb80e443` is `NEEDS_EVIDENCE`. |
| Tests | Ran the CI command on `fc35615`; ran the eleven named suites, the changed test files and 60 delta-related test files on `eb80e443`. | Full suite was not re-run on `eb80e443`. Long runs now go to GitHub by the Creator's decision, and that code is not on GitHub. |
| Schemas | Extracted all 11, ran `Draft202012Validator.check_schema`, validated real files and hand-made bad instances. | None. |
| Upstream LTX | Cloned `Lightricks/LTX-2`, compared `e98f6d92` and `c1b4675`. | Retake was not run. VRAM, time and quality are `NEEDS_EVIDENCE`. |
| 1914 media | The six raw LTX clips exist on HF. I read their container metadata, measured loudness envelopes and looked at 2 fps contact sheets of two clips. | **Limited measurement only.** No speech recognition, no full-resolution viewing, no 2.5D or map media opened. Visual claims in the corrections log remain `REPORTED` except where stated. |

---

## 2. Architecture assessment

### 2.1 The five pillars

| Pillar | Assessment | Evidence | Required change |
|---|---|---|---|
| 12 Core Domain Skills + expert libraries | **Not ready.** The twelve are never listed. Skill #7 is never named. Rule families are under-counted. Moving rules into `docs/expert_library/` removes them from what a Skill loads. | Section 4. | Keep the 21 Skills. Add Skills for missing knowledge. No merge until a rule-level migration map exists. |
| Deterministic Python Core | **Correct, with one false premise.** Keeping `episode/run.py` and adding no orchestrator is right. But the runner is not the "sole" state machine today. | `run.py` L15-17 and L1093: clips "are made by the scene run … never by the runner". The 1914 film was assembled by `tools/render_tools/build_segments.py` and `mix.py`. | State which path renders films. Put V4.1 gates on that path. |
| Multimodal Eyes and Ears | **Right idea, wrong starting point.** The plan builds new observers and ignores four that exist. | `production/perceive_picture.py` (604 L), `qa/perceive_audio.py` (256 L), `qa/look_and_listen.py` (410 L), `videolane/plan.py` L464-907. | Extend the existing observers. A new module must name what it replaces. |
| Connected blocking QA | **Not achieved by the plan as written.** The next stage starts on `PASS` or `REVIEW`. Of the three modules to be "wired", one is a script-stage critic, one a picture-stage check and one a retry counter, and the plan wires them into the last stage. | `run.py` L47 `GO_ON = (G.PASS, G.REVIEW)`, L170-186; `qa/viewer_critic.py` docstring L11-13 ("Gate G2 in Advisory Mode"). | Define `BLOCKER = FAIL` at the stage where the defect is found. Section 6.3. |
| Creator control | **Weakened in three places.** The manifest lists all eleven ADRs under `approved_adrs` before any approval. `WP-00` may edit any test. Two config files the manifest calls forbidden are not protected by the hooks. | Manifest L16-27, L43-44; `config/model_routing.json` `protected_files`. | Section 10, MA-10, MA-11, MA-12. |

Responsibilities are separated correctly in principle: Skills decide, Python executes, models observe, QA blocks, the Creator approves. The plan breaks its own separation in two places. First, the cut-on-action rule says "Editorial Skill decides; Python executes", but no runtime path exists by which a Skill decides one cut in one shot. Second, three operations Skills are relocated into a Python `RouteRegistry` together with rules OR-22..36, which are the Creator's ask-first rules and cannot be expressed as a registry.

### 2.2 Is the loop really closed?

`Intent → Generate → Observe → Evaluate → Adapt → Approve → Continue`

| Step | What exists today (`VERIFIED`) | What V4.1 adds | Closed? |
|---|---|---|---|
| Intent | Production script shots; `scene_layers/1`; `continuity_card/1`. | `shot_intent/1`, which duplicates script fields. | Yes, already. |
| Generate (picture) | Turn packs into `stage_pictures` (L398-446), SHA-256 in `production/pictures.json`. | Nothing. Correct. | Yes. |
| Observe (picture) | `perceive_picture` (L273), `interpret_scene` (L532) with four verdicts; `_reconcile_start_state_with_perception` (`scene.py` L122-209). | A parallel `qa/observe_image.py`. | Observation exists. |
| Evaluate and Adapt (picture → prompt) | `compose_prompt` (L212-285) already rewrites the start state from the picture ("start picture wins") and sets `regeneration_required`. | `i2v_prompt_binding/1`. | **No.** `build` (L292-381) never reads `regeneration_required`. A story-breaking picture still becomes a paid job. |
| SHA binding | Picture pinned three times: `scene.py` L352, `scene_run.job_spec` L86-87, `modal_ltx_jobs.read_job` L302 and L322. | A fourth check with a new error name. | Swap protection exists. **What is missing is binding the observation verdict to that hash.** |
| Generate (video) | Modal worker, outside the runner. | Nothing. | Yes. |
| Observe (video) | `ingest_scene` (L296-364): speech spans, optional local Whisper, clip findings. `videolane/plan.py` start-frame checks L464-907 with zero production callers. `master_qa.py`. | `qa/observe_video.py` inside `stage_clips`. | **Too late.** The clip is trimmed at ingest, and the voice stage has already timed the film from the trimmed clip (`_voice_with_clips` L844, `_stage_inputs` L145-148). |
| Adapt (cut) | `edit_points` (L221-258), `late_sound_out` (L197-218), `whisper_edit_points` (L410-497, no production caller). | `edit/action_cut.py`. | **No.** `stage_clips` raises `ContractError` when clip frames differ from clock frames (L1139-1140). A new cut must go back into `retime_with_edit_points` (`timing.py` L405). The plan has no such path. |
| Adapt (sound) | `events_report` on the measured clock (L923-924); `sound_plan`; `stems`. | `event_sync.py`, observed events. | Partly. Real gain here: observed bangs can move or add cues. |
| Approve | Creator approvals (OR-15, OR-17, OR-19), `budget` and `ledger` on `scene.build`. | `HUMAN_REVIEW` verdicts. | Yes. The number of new decisions per episode is not budgeted. |
| Continue (continuity memory) | `continuity_card/1`. | `continuity_memory.json` written in `stage_qa`. | **No.** `stage_qa` is the last stage and runs once per episode. It cannot inform "the next shot". |

**Answer to the Creator's question.** As written, V4.1 mostly adds inspections around a batch workflow. The runner is stage-major: all pictures, then all voice, then all clips. A per-shot loop does not exist in it. The loop becomes genuine with four changes, none of which needs a new orchestrator:

1. A picture without an `ACCEPT` observation bound to its SHA-256 cannot enter `scene.build`, `scene_run.job_spec` or `read_job`.
2. Video observation runs at ingest, before the clip is trimmed and before the clock is persisted.
3. A cut decision changes the clock through `retime_with_edit_points`. It never fights the clock.
4. The accepted end state of a shot is written when that shot is accepted, per shot, and the next shot's prompt reads it.

"Adapt" also needs a named actuator and an exit. Who regenerates a rejected picture (the turn-pack queue `production/regeneration_queue.json` already exists), how many attempts (`qa/retry_router.py` already counts three), and when it goes to the Creator.

### 2.3 Amendments A to E, and F

| Amendment | Decision | Evidence | Required change |
|---|---|---|---|
| A. Adaptive Video Inspection Router | `NEEDS_EVIDENCE` | The contract `inspection_plan/1` names five tiers, and nothing else exists. DOC-01 points to "DOC-02 §WP-03" and "DOC-03 §3"; DOC-02 has no WP sections and DOC-03 §3 is the test list. No rule assigns a clip to a tier, and there is no cost per tier. | Write the tier rules with measurable triggers and a cost per clip. The deterministic tier runs first and must be able to block alone. |
| B. Separate audio and video clocks | `APPROVE_WITH_CHANGES` | `MEASURED` on six raw LTX clips: video CFR `24/1`, time base `1/12288` (one frame is exactly 512 ticks), audio 48 kHz, both streams start at PTS 0, audio 18 to 45 ms shorter than video, `initial_padding=0` reported. The episode clock is integer frames (`frame_to_sample`, `timing.py` L723). None of the 1914 defects is a sample-level clock error; they are content errors of 0.2 to 1.5 s. | Scope `media_clocks` to the probe, ingest and mux boundary as a per-stream record. Keep the integer-frame episode clock. Do not present clocks as a fix for 1914. |
| C. Intentional cut-on-action | `APPROVE_WITH_CHANGES` | The principle is correct and matches `S04_SH014`. The cut code lives in `ingest.py`, not in `stage_assemble`, which joins whole clips (L1582) and plans transitions only (L1564-1574). The schema allows a mid-word cut with `allowed: true`. | Implement as an extension of ingest edit points. Feed the clock. Add schema conditionals. Define how a Skill's decision reaches a shot (an edit-plan field written at the edit-planner stage). |
| D. Genuine cross-vendor evaluation | `NEEDS_EVIDENCE` | `qa/cross_vendor_critic.py` appears in DOC-01 and in no WP allowlist. `observed_image/1` records the evaluator's vendor but not the generator's, so "the reviewer differs from the generator" cannot be checked. `observed_video/1` records neither vendor. Native video and audio input of `gemini-3.8-flash` and `gemini-4-argon` was not demonstrated; the ids exist in repo text only. A different vendor does not guarantee independent errors. | One recorded real call per claimed capability, with the Creator's approval for the spend. Measure agreement on the 1914 clips plus clean controls before any gate depends on it. Until then advisory. |
| E. Audio Evidence Fusion | `APPROVE_WITH_CHANGES` | The principle (no single signal trusted) is right. The decision table was written without media access (DOC-02 §5). Five fixtures cannot calibrate thresholds. `audio_evidence/1` stores each signal as free text. `perceive_audio.py` and ingest's speech spans already produce three of the six signals. | Replace "calibrated thresholds" with explicit rules, for example "script says silent beat and any speech-like event is present → FAIL". Typed signal results with time spans. Clean control clips to count false alarms. |
| F. 10 % helper lane in Blender 3D | `APPROVE_WITH_CHANGES` (lab only) | Blender is retired by `config/retired_era.json` (D-131). The rationale cites the S8 map review; the later S9 review in the same folder says HUD, labels, ghost arrow and dual front line are fixed and 102 map tests pass. That the Creator ordered this amendment is `REPORTED` by the document. | Lab only. Compare against the S9 2D maps on the same shots. Promotion needs the Creator's recorded word. |

---

## 3. Code-level integration assessment

### 3.1 Baseline

| Fact | Label |
|---|---|
| `git ls-remote` shows no branch `argon/p1-2-timing-contract`; fetching `0592114…` or `eb80e443…` by SHA fails ("not our ref"). No PR head matches. | `VERIFIED` |
| Closest pushed commit: `fc35615` (head of PR #195, `docs/phase-0-master-architecture-2026-11-16`). | `VERIFIED` |
| Drive holds `REPO_TEXT_argon-p1-2-timing-contract_eb80e443.zip` (1,691 text files), `Explainer_Engine_P1_2_Complete_eb80e443_2026-11-17.zip` and the patch. | `VERIFIED` |
| Delta `fc35615 → eb80e443`: `core/contracts.py` (+115), `episode/timing.py` (+29 −3: `clock_sha256`, `load_clock`, validation on load and persist), `episode/run.py` (+7 −2: `TIMING_REL` hashed into later stages, `clock_sha256` in the voice record), `production/map_clip.py`, `tools/render_tools/build_segments.py` and `mix.py` (use `load_clock`), new `schemas/episode_timing.schema.json` (828 L), 10 fixtures, 9 test files. The test changes make fixtures stricter. No assertion was removed. | `VERIFIED` |
| On `eb80e443` the counts and line counts in the plan are exact: 511 `.py`, 361 test files, 21 Skills, 16 Agents, `run.py` 1,790 L, `timing.py` 727 L, `scene.py` 421 L, `modal_ltx_jobs.py` 1,334 L, `hooks.py` 433 L. | `VERIFIED` |
| What `0592114` adds on top of `eb80e443`. | `NEEDS_EVIDENCE` |
| The Phase 0/1 master plan on PR #195 calls the P1.2 slice "Awaiting Owner acceptance". V4.1 never says whether it replaces or continues that plan. Two governing plans overlap. | `VERIFIED` |

### 3.2 The sixteen `WP-02` touchpoints

| # | Plan claim | Result | Problem |
|---|---|---|---|
| 1 | Picture completion: `turn_pack.py` consumed by `stage_pictures` L398-446 | Correct. | None. |
| 2 | SHA-256 registration in `production/pictures.json` | Correct (`_sha`, L57). | None. |
| 3 | New `stage_observe_image` "registered in `run_stage` L189-211" | **Wrong mechanism.** Stages are registered in `STAGES` (L35), `GATES` (L36), `ALIASES` (L38) and `STAGE_FUNCS` (L1725). | A new stage changes the fingerprint chain (`fingerprint` L152-156 hashes the previous stage's record). Every existing record after it goes stale. No migration is planned. |
| 4 | Verdicts in `production/observed_images.json` | New file. | `production/regeneration_queue.json` and `perception_result/1.0` already hold this. |
| 5 | Prompt built in `scene.compose_prompt` L212-285, called by `build` L292-381 | Correct. | `build` has **no caller in the runner**. It is driven by hand. A runner test cannot assert "`StageRefused` before `scene.build`". |
| 6 | LTX submission in `modal_ltx_jobs.py` (`load_launch` L67, `native_spec` L179, `run_id` L258) | Functions exist. | The actual guard is `read_job` L292-328, not cited. `scene_run.job_spec` L75-100 is not cited either. |
| 7 | SHA enforcement "dual-enforced" in `scene.build` and the worker | Already enforced three times. | `WP-02` `allowed_modify` lists only `run.py` and `scene.py`. The plan contradicts its own allowlist. Editing the worker changes `worker_sha()` (L250) and voids ladder rungs L1 to L3, which forces a paid L3 smoke. `WP-02` is declared `$0.00`. |
| 8 | Clip return path: `stage_clips` L901-1206 | Partly. | Ingest (`ingest_scene`) runs outside the runner and writes `production/video/<shot>.json`. `stage_clips` only reads it (`_wan_clip` L889) and recuts (L1070-1073). |
| 9 | Video observation inside `stage_clips` after ingest | **Too late.** | Voice (G6) runs before clips (G7) and times clip-spoken shots from the already trimmed clip (L844, L145-148). |
| 10 | PTS extraction in new `core/media_clocks.py` with PyAV | Feasible. | `av` is not in `requirements.txt` and is imported nowhere. `ffprobe` is already used by `ingest.probe` (L84-96). |
| 11 | Cut interface feeding `plan.draft_edit_plans` and `stage_assemble` L1564-1574 | **Wrong place.** | L1564-1574 builds the boundary manifest and transition plan. Trimming happens in `ingest.cut` (L261-281) and `recut` (L367-389). |
| 12 | Events: `stage_clips` L923-924 already writes `av_events.json` | Correct. | "Extend to `av_events/1`" overwrites a live contract of the same name. |
| 13 | Offsets in `stage_sound` L1346-1485 + `sfx_planner.py` | Correct call site. | The runner's sound path is `episode/sound_plan.py`, `audio/stems.py`, `episode/events.py`. `audio/spine.py` is not on the runner path (it serves `production/assemble.build_audio_v2` and `audio/sound_director.py`), yet `WP-04` lists it and omits the three real files. |
| 14 | Blocker propagation in `stage_qa` L1646-1713, `all_gates_passed` L1708, `check_before` L170-186 | Line numbers correct. | `all_gates_passed` is a field in a manifest written at the end. It stops nothing earlier. `check_before` continues on `REVIEW`. |
| 15 | Final acceptance writes L1705-1710 | Correct. | None. |
| 16 | Continuity memory written in `stage_qa` L1709 | **Cannot work as described.** | Last stage, once per episode. |

Summary: 3 of the 16 touchpoints are correct and sufficient (1, 2, 15). 9 point at real code but miss a dependency, a guard or a file (4, 5, 6, 7, 8, 10, 12, 13, 14). 4 are wrong in mechanism, timing or place (3, 9, 11, 16).

### 3.3 Hidden state dependencies the plan does not name

| Dependency | Where | Consequence |
|---|---|---|
| Fingerprint chain | `run.py` L127-156 | A new stage or a new stage input invalidates downstream records of every existing episode. |
| Ladder proof bound to file hashes | `modal_ltx_jobs.worker_sha` L250; `cloud/modal_run.gate` | Any edit to the worker or `launch.json` needs L1 to L3 again, including a paid smoke (cap `smoke_usd` 0.5). `launch.json` is a protected file. |
| Clip frames must equal clock frames | `run.py` L1139-1140 | A cut decision that ignores the clock crashes the clips stage. Test T3 ("out_frame == 82, never 48") fails here unless the clock is retimed. |
| Voice before clips | `STAGES` L35; `_voice_with_clips` L844 | Clip-spoken shots are final before the proposed video observation runs. |
| `REVIEW` passes | L47, L170-186 | A gate that returns `REVIEW` does not block. |
| Rehearsal mode | L1708 | `all_gates_passed` is always false in rehearsal. T7 must not run in rehearsal. |
| Timing validation on load (new in `eb80e443`) | `timing.py` L273-291 | Every reader of `audio/timing.json` now raises `ContractError` on an old or hand-written file. No `timing.json` is stored in the repo, so the effect on the 1914 files on the Mac is `NEEDS_EVIDENCE`. |
| Effort ceiling | `hooks.py` L39, `config/model_routing.json` `code.effort_ceiling: high` | A session above effort `high` cannot edit `.py` files. One governance test also fails when `CLAUDE_EFFORT=xhigh` is set in the environment. |

### 3.4 Proposed new modules against what already exists

| Proposed (`NEW`) | Already in the code | Callers today | Recommendation |
|---|---|---|---|
| `qa/observe_image.py`, `observed_image/1` | `production/perceive_picture.py`: `perceive_picture` L273, `interpret_scene` L532, verdicts `ALIGNED`, `ADAPTED_STAGING_NON_BREAKING`, `UNCERTAIN_NEEDS_REVIEW`, `STORY_BREAKING_CONFLICT`; `qa/blind_check.py` (KG-23..27); `videolane/storyboard.py` | `scene.py` L122-209 | Extend. Add the SHA binding and the block. |
| `qa/observe_video.py`, `observed_video/1` | `videolane/ingest.py` `ingest_scene`; `videolane/plan.py` `inspect_ltx_start_frame` L464, `compare_ltx_first_frame_to_source` L594, `classify_ltx_natural_fit` L649, `reroute_unnatural_ltx_shots` L814, `apply_and_persist_ltx_routes` L907; `qa/look_and_listen.py`; `videolane/master_qa.py` | The five `plan.py` functions have **zero** production callers. | Wire the existing checks first. Add action events as a new field of the clip record. |
| `edit/action_cut.py`, `cut_decision/1` | `ingest.edit_points` L221-258, `late_sound_out` L197-218, `whisper_edit_points` L410-497 (`edit_points/2`), `recut` L367-389 | `whisper_edit_points` has **zero** production callers. | Extend ingest. One cut owner. |
| `audio/evidence_fusion.py`, `audio_evidence/1` | `qa/perceive_audio.py` (DSP, YAMNet, AST, CLAP, `verify_j_cut_bridge`); ingest speech spans and local Whisper | Used by `look_and_listen`. | Fusion rules as a thin layer over these signals. |
| `continuity_memory/1` | `continuity_card/1` (`scripting/continuity.py`, `production/continuity.py`, `qa/scene_continuity.py`) | In use. | Add "observed accepted end state" to the card or define the relation. |
| `core/route_registry.py` | `episode/router.py`, `edit/router.py`, `qa/retry_router.py`, `config/model_routing.json`, `config/picture_route.json`, `imagegen/routing.py`, `cloud/cheapest.py` | In use. | A read-only view over these. Never a new source of truth. |
| "Adopt PySceneDetect", "optional OTIO" | `scenedetect>=0.6` is in `requirements.txt`; `production/assemble.export_otio` L830 | In use. | Remove from the "new" list. |

Three existing but unwired fixes map directly to 1914 defects:

- `whisper_edit_points` L447-453 filters a duplicated opening word. Its own comment names `S06_SH008 "Maybe"`.
- The same function mutes hallucinated tail tokens (L454-496).
- `late_sound_out` L197-218 was written for `S03_SH003` (comment: "measured 8.4 dB under the span on the mean").

### 3.5 The second production path

`tools/render_tools/build_segments.py` (366 L) and `mix.py` (848 L) assemble a film from an external clock file. The Truce 1914 film on the Mac was built this way. V4.1 treats `episode/run.py` as the only path and never mentions these tools. If films keep being assembled there, gates placed in the runner do not protect the film.

---

## 4. Skill and expert knowledge assessment

### 4.1 What is verified

The crosswalk's counts are exact: 21 Skills with the stated line counts and 16 Agents. The plan's statement that every file was read is plausible.

### 4.2 Why the consolidation cannot be approved

| Problem | Evidence |
|---|---|
| The twelve target Skills are never listed. Destinations name Skills #1 to #6 and #8 to #12. Skill #7 has no name anywhere. | DOC-02 §2.1; DOC-01 §3. |
| Rule families are under-counted. The crosswalk keeps `SC-01..09`; the Skill holds `SC-01..SC-12`, and SC-11 and SC-12 are binding (D-61). It keeps `VB-01..11`; the Skill holds `VB-00..VB-12`. | `.claude/skills/dialogue-scenes`, `visual-beats`; `CLAUDE.md`. |
| "Retained verbatim in `docs/expert_library/`" weakens the rule in practice. A Skill is loaded when its trigger fires. A document library is not. | Crosswalk rows `narration-script`, `video-editing-architect`, `elevenlabs-voice`. |
| Three operations Skills move into a Python `RouteRegistry` together with "OR-22..36". Those are the Creator's rules (ask first, plan before a pod, the planning thread decides, the audit before a paid test). They are not routing data. | Crosswalk rows `modal-operations`, `cloud-cost-audit`, `cloud-provider-selection`; `CLAUDE.md`. |
| Tests and documentation read Skill files by path. `tests/unit/test_agent_governance.py` L104-151 opens `.claude/skills/shot-visuals/SKILL.md`; `test_narration_lint.py`, `test_speech_registers_fewshot.py`, `test_rule_consistency_audio.py` and `docs_lint` (one home per ID) depend on the current layout. | `VERIFIED` |
| `WP-10` has no allowlist, no tests, no acceptance criteria and no rollback. | Manifest L176-181. |
| Eleven stage-page Agents are to be merged into Skills. `scripting/stage_guard.py` and the `story-engine` Skill rely on one stage owning its own fields (OR-20, D-79). | `CLAUDE.md`; crosswalk §2.2. |
| Retiring `lora-training` and four LoRA Agents removes Skills and Agents. That needs the Creator's word, and an archive, not a deletion. | Crosswalk; restriction "Do not remove or weaken Skills". |

### 4.3 The twelve knowledge areas the Creator named

| Area | Where the knowledge lives today | V4.1 plan | Risk | Recommendation |
|---|---|---|---|---|
| Directing and cinematography | `shot-visuals` (201 L), `visual-beats` (113 L), `docs/SHOT_PROMPTS.md` | Merge into Skills #3 and #5 | Rule IDs VB-00, VB-12 not listed | Keep both Skills. |
| Screenwriting and dramaturgy | `story-engine`, `narration-script` (N-01..N-17), `dialogue-scenes` (SC-01..SC-12), stage pages | Merge into Skill #2, rules to a doc library | SC-11, SC-12 lost; stage ownership blurred | Keep. |
| Animation | `animation-principles` (85 L) | Keep, split across #6 and #8 | Low | Keep as is. |
| Character acting | `animation-principles`, `dialogue-scenes`, `performance-director` page | Skill #8 | Medium | Keep. |
| Foley and sound design | `docs/SOUND_LIBRARY.md`, `audio/layers.py` rules, `elevenlabs-voice` (EL-01..EL-13), `voice-search` | Skill #10 plus doc library | EL rules demoted to "tool reference" | Keep `elevenlabs-voice`. **Add** a foley and sound-design Skill; none exists today. |
| Editorial montage | `editing-style` (167 L, ED rules), `video-editing-architect` (310 L) | Merge into #11 | Two different purposes merged | Keep both. |
| LTX workflows | **No Skill.** Knowledge is in `docs/VIDEO_LANE.md`, `docs/SHOT_PROMPTS.md`, BP-205 rules in `videolane/plan.py` | Not addressed | The largest gap for a closed loop on LTX | **Add** an LTX Skill (prompting from the observed picture, 8k+1 frames, retake, ladder, cost). |
| Gemini image editing | **No Skill.** Turn packs GC-01..17 in docs and code | Not addressed ("preserve Gemini Chat workflow") | Regeneration after a rejected picture has no written craft | **Add** a Skill for the turn-pack and correction workflow. |
| FFmpeg | **No Skill.** Knowledge is in code | Not addressed | Clock and cut work depends on it | **Add** a media-timing Skill (probe, CFR, priming, frame-exact cuts). |
| Historical research | `science-grounding` (35 L), claim map | Keep | Low | Keep. |
| Cartography | `cartography` (72 L); S9 map code and tests | "Upgrade" to 3D Blender | Rewrites a Skill around a retired tool before the lab proves it | Keep the 2D Skill. A Blender Skill only after `WP-B1`. |
| QA | `script-critic` Agent, `docs/KEYFRAME_GATE.md`, `qa/` modules | Skill #12 | Not specified | Keep `script-critic` clean-room. **Add** a film-QA Skill that maps defect classes to gates. |

**Conclusion.** I do not recommend reducing the Skills, and I do not approve the reduction to twelve. The proof that no specialist knowledge is lost does not exist. The correct move is additive: keep 21, add four (LTX, Gemini picture correction, media timing, foley and film QA can be two), and keep the Agents.

---

## 5. 1914 failure coverage

### 5.1 The limitation, and what I measured

The documents say the raw media are unreachable. That is true for the offline sandbox, not for the project: **all eight assets listed in DOC-02 §5 exist on `vano1919/tmr-artifacts`** (`VERIFIED` by HTTP status and size). Items 7 and 8 need the prefix `explainer-engine/` that the document omits.

I did a limited, deterministic measurement of the six raw LTX clips. This is not a review of the film and not a confirmation of the corrections log as a whole.

| Clip | Video | Audio | `MEASURED` signal | Corrections log (`REPORTED`) | Agreement |
|---|---|---|---|---|---|
| `S06_SH008` | 97 frames, 4.042 s | 4.010 s | Three energy bursts: 0.1-0.6 s, 1.6-2.1 s, 2.9-3.7 s | "Maybe" at 0.0-0.6 s and 1.72-1.92 s; fix: start at 1.45 s | Consistent. Words not checked (no speech recognition). |
| `S03_SH007` | 105 frames, 4.375 s | 4.330 s | Quiet floor −54 dBFS; one event 2.4-2.8 s peaking −33 dBFS. Mean brightness rises 57 → 81 from 0.75 s, with no clipped highlights. In the 2 fps sheet the mist is plain from 1.0 s and the mouth appears open at 2.0 and 2.5 s. | Silent beat transcribes "Oh my God"; white fog bloom from about 2 s | Consistent. The bloom starts earlier than logged. The mouth observation is from a 384 px sheet and needs a full-resolution check. |
| `S03_SH003` | 113 frames, 4.708 s | 4.690 s | Three sung phrases with two short pauses; the last phrase's level falls only during the final 0.7 s | "Nacht" was cut; fix: play to 4.71 s | Consistent. **4.71 s is the full length of the clip.** By the log, the word ends where the clip ends. |
| `S04_SH014` | 105 frames, 4.375 s | 4.330 s | Steady ambience, no audio event. In the 2 fps sheet the hands are clasped at 3.5 s and apart at 4.0 s. | Handshake released at the end; out at 2.6 s | Consistent. Audio cannot detect this defect. |
| `S07_SH005` | 193 frames, 8.042 s | 8.010 s | Sharp onsets at 0.45 s and 1.65 s | Two bangs at 0.5 s and 1.6 s | Match. |
| `S07_SH006` | 209 frames, 8.708 s | 8.690 s | One sharp onset at 7.80 s | One bang at 7.9 s; script wanted two | Match. |

Three consequences for the design:

1. **The fusion table contains an unmeasured value.** For `S03_SH007` it assumes "VAD = False / low" and builds the verdict on a contradiction with speech recognition. The clip has a 21 dB event over its floor. Whether a voice detector fires on it is unknown. The rule must be "the script says silent and a speech-like event exists".
2. **Muting may not be enough for `S03_SH007`.** If the mouth is really open at 2.0-2.5 s, a muted clip shows a silent mouth. That defect needs video observation, not audio.
3. **`S03_SH003` is a generation problem, not only a cut problem.** If the logged word end is right, the word ends with the clip and no reaction tail (BP-201) can follow it. The correct adaptive action is then a longer generation or an audio retake. A cut rule alone cannot fix it.

### 5.2 Coverage of every reported failure

"Chain complete" means all five exist: root cause, V4.1 owner, task, regression test, acceptance criterion.

| Failure | Root cause in code | V4.1 owner | Task | Regression test | Acceptance | Chain complete |
|---|---|---|---|---|---|---|
| `S06_SH008` duplicated word | `ingest_scene` uses `edit_points` (in = first word − lead). The duplicate filter sits in `whisper_edit_points` L447-453, never called. | Fusion (`WP-03`), cut (`WP-04`) | Not written | None in `WP-02`; fixture id undefined | None | **No** |
| `S03_SH007` unexpected speech | No check that a silent beat is silent. Hallucinated-tail muting exists, uncalled. | Fusion (`WP-03`) | Not written | T4 (mocked) | None | **No** |
| `S03_SH007` fog bloom | No drift check on the generated clip | **None** | None | None | None | **No** |
| `S03_SH003` word cut | Old assembly recut the clip to the planned length. Ingest now refuses a hand-over before speech ends (FA-07). | Cut (`WP-04`) | Not written | T4 (mocked) | None | **No** |
| `S04_SH014` action released | No action observation | `observe_video`, `action_cut` | In `WP-02` | T3, which conflicts with the clock rule | None | **No** |
| `S07_SH005` bangs before narration | Sound events planned, not observed | `event_sync` | Not written | None | None | **No** |
| `S07_SH006` one event instead of two | Same | `event_sync`, `av_events` | Not written | None | None | **No** |
| `S08_SH003` picture contradicts its line | Plan data error; no narration-versus-picture check blocks | **None** | None | None | None | **No** |
| `S02_SH008`, `S05_SH020`, `S08_SH002` 2.5D defects V1-V6 | Renderer | `WP-06` (a benchmark, not a fix) | Script only | None | None | **No** |
| `S02_SH009`, `S05_SH003`, `S06_SH005` grey sky blobs | Mist effect without a sky mask | **None** | None | None | None | **No** |
| `S05_SH001`, `S05_SH002` label lost its accent ("La Bassée") | Font or text handling | **None** (moving maps to Blender does not fix text) | None | None | None | **No** |

### 5.3 Conclusion

- **No reported failure has a complete chain.** Six have an owner. Five have none.
- The manifest's fixtures `1914-F01` to `1914-F06` and `1914-F10` are never defined. F07 to F09 are skipped without explanation.
- DOC-04 cites the S8 map review (`24_OPUS_VISUAL_CHECK_MAPS_S8.md`) as current evidence. The S9 review (`30_OPUS_VISUAL_CHECK_MAPS_S9.md`) supersedes it.
- Three of the first four failures can be fixed by wiring code that already exists (section 3.4). That is the cheapest proof that the closed loop pays off.

---

## 6. Contract and QA assessment

### 6.1 The eleven schemas

All eleven pass `Draft202012Validator.check_schema` (`VERIFIED`). Structural validity is where the good news ends.

| Schema | Problem (each proven by an instance that validates, or by a real file that fails) | Required change |
|---|---|---|
| `av_events/1` | **Name collision.** The real `ep_truce_1914/production/av_events.json` fails: "Additional properties are not allowed ('contract', 'decisions', 'fps', 'resolver', 'shots')", "'events' is a required property". An event with no time position validates. | New name or version (`av_events/2` or `av_event_timeline/1`), a migration, and the existing event ids (`S01_SH001.M1`). |
| `cut_decision/1` | `MID_WORD_PHONETIC_CUT` with `allowed: true` and `out_frame < in_frame` validates. | `if/then`: that cut type forces `allowed: false`. Frame order in `core/contracts.py`. |
| `observed_image/1` | `verdict: ACCEPT` with two mismatches and confidence 0 validates. Mismatches are free strings without severity, so a blocking mismatch cannot be expressed. No `shot_id`, no intent version, no generator vendor. | Add the fields. Typed mismatches with severity. Conditional: a blocking mismatch forbids `ACCEPT`. |
| `i2v_prompt_binding/1` | It carries an integer `observation_version` but no hash of the observation record and no verdict, so it binds prompt to picture but not to the observation. `model_route` hard-codes `ltx25_guided`, `ltx25_retake` and `gemini_omni_1_2_flash`, none of which is an approved route (D-132 is LTX-2.5 distilled). | Add `observation_sha256` and `observation_verdict`. Routes come from config, not from an enum in a schema. |
| `observed_video/1` | An event with end < peak < start and an unknown nested key validates. No `shot_id`, no fps or time base for its frame numbers, no overall verdict. | Add them. Order checks in `contracts.py`. |
| `media_clocks/1` | Modelled per timestamp (`frame_index`, `pts` required), not per stream. No clip hash. | Per-stream record: time base, start PTS, frame count, sample count, priming, edit list, clip SHA-256. |
| `audio_evidence/1` | One free-text signal, a dangling `depends_on` and verdict `PASS` validate. The source enum hard-codes a tool name (`asr_whisperx`). | Typed signals with spans. Minimum signal set per verdict. Name the signal, not the tool. |
| `qa_result/2` | `PASS` with a `BLOCKER` finding and `blocks_progression: false` validates. Its `stage` enum (`observe_image`, `observe_video`, `clip`, `sound`, `assemble`, `master`) does not match the runner's stages, so the script, pictures and voice stages cannot emit it. Together with `observed_image`, `audio_evidence`, `qa/gates` rows and `qa_report/1` this makes five verdict vocabularies with no mapping. | Conditional: any `BLOCKER` forbids `PASS`. Stage names from `STAGES`. One written mapping to `PASS / FAIL / REVIEW / NOT_RUN / INCOMPLETE`. |
| `shot_intent/1` | Duplicates production-script fields. Forces at least one "deferred until observed" item even when nothing is deferred. | A view over the script, or drop it. |
| `continuity_memory/1` | Overlaps `continuity_card/1`. Nested state accepts any key. | Section 3.4. |
| `inspection_plan/1` | Five tiers are named. No rule says which clip gets which tier. `max_estimated_usd` has no price source. | The tier rules and a cost table (Amendment A). |

Further points:

- Eight nested objects accept unknown keys, so typos pass silently.
- The `shot_id` pattern exists in two schemas only. Elsewhere it is a free string.
- `WP-01` may create `explainer_engine/schemas/*.schema.json` by wildcard. That allows overwriting any existing schema.
- **Valid and invalid examples do not exist.** P1.2 set the right precedent: `tests/fixtures/contracts/episode_timing/` has three valid and seven invalid files, and `_episode_timing` in `core/contracts.py` (L660) carries the semantic checks. V4.1 contracts must follow it.
- Test T6 is a unit test of the clock module. It cannot "run strictly through `episode/run.py`".

**Are the schemas complete enough for implementation? No.** They are a draft of field names. Six lack the fields that carry the architecture's central promises (binding, vendor, clock basis, blocking).

### 6.2 Does a QA failure block production today?

| Situation | Blocks? | Evidence |
|---|---|---|
| A gate row `FAIL` | Yes, the next stage is refused. | `check_before` L170-186, `StageRefused`. |
| A gate row `REVIEW` | **No.** | `GO_ON` L47. |
| Story-breaking picture conflict | **No.** Queued for regeneration, and the scene still builds. | `scene.py` L206, L282; no reader of the flag. |
| Look-and-listen | Only if its record exists or the manifest requires it. | `run.py` L1663. |
| `all_gates_passed = false` | Nothing is stopped by the field itself. | L1708. |
| Viewer critic | Advisory by design (D-130). | `viewer_critic.py` L11-13. |

### 6.3 What the three "disconnected" modules really are

| Module | What it does | Correct home | The plan says |
|---|---|---|---|
| `qa/viewer_critic.py` (287 L) | A clean-room critic of the **script text** at Gate G2, advisory, with an offline simulator; the live call is paid. | `stage_script`. Making it blocking is the Creator's decision. | Wire into `stage_qa` and `check_before`. |
| `qa/blind_check.py` (199 L) | Describes a **picture** without its prompt and compares with the scene contract (KG-23..27). | Picture observation. | Wire as a QA gate. |
| `qa/retry_router.py` (131 L) | The fixed retry order: reseed, reweight references, fallback, escalate; never a fourth attempt. Counts attempts in `jobs/<phase>/attempts.json`. | The "Adapt" step of the loop, per shot. | "With `REWEIGHT_REFERENCES`", which already exists (L30). |
| `qa/loop.py` (330 L) | The older chunk-pair review loop. It renders through `production assemble`, a different path from the runner. | Unclear. Wiring it into `stage_qa` would start a second render path inside QA. | In `WP-05` `allowed_modify`. |

### 6.4 Level A, B and C protections

| Level | Proposed | What it really enforces | Holes |
|---|---|---|---|
| A. Manifest | YAML with allowlists | Nothing. It is text. The plan says so itself. | Its own hash is anchored nowhere. It pre-approves all ADRs. Four WPs have no allowlist at all (`WP-07` to `WP-10`). |
| B. `check_wp_scope.py` in `pre_write` | Refuse out-of-scope writes | Only Claude Code `Write` and `Edit` calls. | It does not bind Gemini, whose sandbox is offline and returns zips. Shell edits (`sed -i`, `git apply`, scripts) bypass `pre_write`, except for protected files. A `git diff` check inside a pre-write hook sees the tree before the write; it must test the target path from the event. |
| C. CI step and branch protection | Scope check, `docs_lint`, `pytest -m "unit"` on PRs | Real enforcement, once configured. | `pytest -m "unit"` selects **zero** tests: the marker is declared and never used. `quality.yml` already runs `python -m pytest -q -m "not system and not media"`, `docs_lint` and the palette check on every pull request. `tests/integration/` does not exist. Branch protection is a manual repository setting. |

Protected files today (`config/model_routing.json`): `spend_caps.json`, `model_routing.json`, `channel_voices.json`, `generator_admission.json`, `cloud/cheapest.py`, `cloud/cheapest.json`, `ltx/launch.json`. **`config/picture_route.json` and `config/retired_era.json` are not protected**, although the manifest lists them as forbidden.

### 6.5 Minimum enforcement before implementation starts

1. The baseline is on GitHub and CI is green on that exact SHA.
2. Branch protection on the implementation branch: required status check, no direct push.
3. `picture_route.json` and `retired_era.json` added to `protected_files` on the Creator's recorded word.
4. One CI job that fails when a PR touches a path outside the active WP's allowlist. It runs on the PR diff, so it binds every author, including zips applied by a Claude thread.
5. Tests are read-only during `WP-00`. A test edit needs the Creator's approval per file (invariant 10).
6. A demonstration: one deliberate out-of-scope change is refused by CI before any real work starts.

---

## 7. Tool, model and third-party media assessment

### 7.1 LTX pin `e98f6d92` against `RetakePipeline` at `c1b4675`

I cloned `Lightricks/LTX-2` and compared the two commits (`VERIFIED`).

| Fact | Detail |
|---|---|
| Ancestry | `e98f6d927d83…` (2026-10-18) is an ancestor of `c1b4675863c0…` (2026-11-03). Upstream head is `f0f2f86` (2026-11-12). The diff between the two is 251 files, +23,837 −21,666. |
| Availability | `packages/ltx-pipelines/src/ltx_pipelines/retake.py` **exists at the pinned commit** (406 lines; 400 at `c1b4675`). DOC-04's "UNKNOWN" is resolved: no pin bump is needed to have `RetakePipeline`. |
| API drift | `Registry` became `ModelRegistry`, the `SimpleDenoiser()` signature changed, `tiling_scale_factors_for_vae` was removed. Code written from the `c1b4675` source will not run on the pin. |
| Audio-only retake | The class accepts `regenerate_video` and `regenerate_audio`. The command-line `main()` at both commits does not pass them, so both are always true. Audio-only retake needs a Python call inside the Modal worker. |
| Cost of that call | Editing `modal_ltx_jobs.py` changes `worker_sha()`. Ladder rungs L1 to L3 must be proven again, including a paid L3 smoke (cap `smoke_usd` 0.5). The `module` pin in `launch.json` is a protected file. |
| Constraints | Frames must be 8k+1 and sizes divisible by 32. All six measured 1914 clips satisfy 8k+1 (97, 105, 113, 193, 209 frames). |
| Open | Retake runs single-stage on the full-resolution latent. VRAM, run time and quality on the H100 worker with the pinned weights (`Lightricks/LTX-2.5` revision `49b093a3…`, five files) are `NEEDS_EVIDENCE`. |

**Decision: requires code and weight compatibility verification.** It is neither ready nor in need of deferral for lack of code. Integration waits for one Creator-approved smoke on the pinned commit with the pinned weights. All code must be written against `e98f6d92`.

### 7.2 Other technical claims

| Claim in the documents | Status |
|---|---|
| `gemini-3.8-flash` and `gemini-4-argon` can review native video with audio | `NEEDS_EVIDENCE`. The ids appear in repository text (five occurrences each). No recorded call proves the capability, the price per clip or the repeatability. Not approved as a gate. |
| "Interactions API" | `NEEDS_EVIDENCE`. I found no client for it in `explainer_engine/`. |
| WhisperX as the ASR signal | New dependency, not in `requirements.txt`. Ingest already has an optional local Whisper (`_local_words`, L141). The gain over it must be measured on the six clips first. |
| PyAV `av 10.0.0` for PTS | Not in `requirements.txt`, imported nowhere. `ffprobe` gave every number in section 5.1. |
| "Adopt PySceneDetect", "optional OTIO" | Already present (section 3.4). |
| SeedVR2 restoration | Not in the repository. Experiment only. |
| HunyuanVideo-Foley | A new sound generator. `assets/audio/generator_admission.json` is a protected file, so admission needs the Creator's recorded word. Current rule: ElevenLabs for narration and effects (D-52). |
| H100 at "~$3.95/hr" | Contradicts the project's own pin: `launch.json` has `usd_per_h 5.0937`. The current Modal list price is `NEEDS_EVIDENCE`. Money ceilings live only in `config/spend_caps.json`. |
| Modal cost rules (sandbox multiplier, region multiplier, keep-alive) | `REPORTED`. Not checked. |
| Blender 5.2 with Poly Haven assets | The retired code exists (55 files). Where it would render and how long a map shot takes are `NEEDS_EVIDENCE`. |

### 7.3 Third-party media that YouTube could block

This is the only licence question in scope, by the Creator's instruction. Source of the facts: `assets/audio/library/manifest.json` (260 items) and the 1914 plans (`VERIFIED`).

| Source | Items | Terms recorded in the repository | Risk on YouTube | What V4.1 should add |
|---|---|---|---|---|
| **BBC Sound Effects (RemArc)** | 34 effects | The library's own note: "personal, educational or research only: never on a monetised channel". Admitted as an exception by the Creator's card of 2026-11-13 (`audio/sources.py` L138-141). | **Highest.** A monetised video is outside the licence. The risk is a removal request by the owner, which is a strike, not a Content ID claim. | The 1914 sound plan (`episodes/ep_truce_1914/audio/sound_plan.json`) references six: `army_camp_16c__v1`, `army_waiting_murmur__v1`, `bonfire_close__v1`, `bow_twang_hits__v1`, `fire_small_cracks__v1`, `woodland_wind_birds__v1`. Whether they are in the final mix is `NEEDS_EVIDENCE`. Before a public monetised upload, list them and let the Creator decide item by item. |
| incompetech (Kevin MacLeod) | 15 music tracks | CC BY 4.0. The exact attribution text is stored per track. "Silent Night" (ISRC `USUAN1100075`) and "Ancient Rite" are in the 1914 plan. | Low to medium. Allowed with attribution. Tracks with an ISRC can attract third-party Content ID claims; how often is `NEEDS_EVIDENCE`. | Attribution in the video description. Keep the licence page as proof for a dispute. |
| Mixkit | 74 effects | Mixkit free licence, read 2026-11-13 and recorded per item. | Low. | None. |
| OpenGameArt | 63 effects, 1 arrangement | CC0. | Low. | None. |
| ElevenLabs | 12 items | Terms verified on the paid plan. | Low. | None. |
| Gemini TTS, Lyria | 15 + 1 | Status `generated_terms_unverified`. | Unknown. | None of them is referenced by the 1914 sound plan. Keep them out of public videos until the terms are read. |
| Proposed: Sonniss GDC | new | DOC-04 cites a blog post, not the Sonniss licence. | `NEEDS_EVIDENCE` | Read the primary licence before any import. |
| Proposed: Freesound "CC0 filter" | new | Freesound also hosts CC BY and CC BY-NC files. | Per file. | Record the licence per file, as the library already does. |
| Proposed: Poly Haven, ambientCG, Quaternius | new | CC0 models and textures. | None. | None. |
| Proposed: Smithsonian 3D | new | Only its Open Access items are CC0. | Per item. | Record per item. |
| Proposed: BlenderGIS map data | new | Elevation data from NASA is free. Commercial basemap imagery is not. | Medium if imagery tiles are used. `NEEDS_EVIDENCE` per source. | Restrict to public elevation data and OpenStreetMap with attribution. |
| Archive pages in the 10 % reel (the Pope's appeal, the Princess Mary card, Hale's letter) | 3 | Whether they are scans or drawn recreations is not recorded where I looked. | `NEEDS_EVIDENCE` | If scans: record the holding archive and its terms. |
| Third-party video footage | none | All video is generated in the pipeline. | None. | None. |

**Gap in V4.1:** no gate lists the third-party media that end up in a finished film. The library already stores a licence per item. One per-episode list at the sound stage, checked by `qa/publish_check.py`, closes the gap.

### 7.4 Tool licences

Out of scope by the Creator's rule. One correction for the record: DOC-04 calls the LTX code Apache-2.0; the repository's `LICENSE` at the pinned commit is the LTX-2 Community License.

---

## 8. ADR-by-ADR decisions

| ID | Decision | Evidence | Problem | Required change | Implementation blocker |
|---|---|---|---|---|---|
| `ADR-V41-01` Keep `episode/run.py`; add `RouteRegistry` | `APPROVE_WITH_CHANGES` | Runner with fingerprint chain (`run.py` L35, L127-156). Clips are made outside it (L15-17, L1093). 1914 film assembled by `tools/render_tools`. Seven routing sources exist. | "Sole state machine" is not true today. `RouteRegistry` has no specification. | Keep the runner, no new orchestrator. Decide which path renders films. `RouteRegistry` as a read-only view over existing config. | Yes for the `RouteRegistry` part of `WP-01`. |
| `ADR-V41-02` Plan-versus-observed immutability | `APPROVE_WITH_CHANGES` | `regeneration_required` is produced (`scene.py` L206, L282) and never read. The picture hash is pinned three times. Existing `perception_result/1.0`, `interpretation_record/1.0`, `continuity_card/1`. | New parallel contracts. The binding lacks the observation hash and verdict. | Build on `perceive_picture`. First deliverable: a picture without a bound `ACCEPT` cannot be built into a scene. | Yes for `WP-02`. |
| `ADR-V41-03` Adaptive inspection router, explicit model ids | `NEEDS_EVIDENCE` | Only `inspection_plan/1` exists. Model capabilities unproven (section 7.2). | No tier rules, no cost, no fallback rule. | Tier rules, cost table, one recorded call per capability. | Yes for `WP-03`. |
| `ADR-V41-04` Separate rational clocks; event offset policy | `APPROVE_WITH_CHANGES` | Six clips measured: CFR 24, exact 512-tick frames, zero stream offsets, audio 18-45 ms short. Episode clock is integer frames. `av_events/1` is taken. | Over-scoped for the problem. Name collision. Offset numbers ("−48000 samples", "−4 dB") have no source (D-59 needs two source types). | Clocks at the ingest and mux boundary only. New contract name. Offsets as sourced rules (BP entries). | Yes for `WP-01` (the name). |
| `ADR-V41-05` Intentional cut-on-action | `APPROVE_WITH_CHANGES` | Cut code is in `ingest.py` L221-281, L367-389. Clock equality rule L1139-1140. Schema permits a blocked cut type as allowed. | Wrong files. No path from a Skill's decision to a shot. | Extend ingest; feed `retime_with_edit_points`; schema conditionals; decision recorded in the edit plan. | Yes for `WP-02` and `WP-04`. |
| `ADR-V41-06` Audio Evidence Fusion | `APPROVE_WITH_CHANGES` | Measured onsets match the log (section 5.1). The table's `S03_SH007` voice-detector value is assumed. Existing signals in `perceive_audio.py` and ingest. | "Calibrated on 1914 fixtures" is unsupported: no fixtures existed and five clips cannot calibrate. | Rules instead of thresholds. Typed signals. Clean controls. Fixtures defined with HF paths and hashes. | Yes for `WP-03`. |
| `ADR-V41-07` Wire disconnected QA as blocking gates | `APPROVE_WITH_CHANGES` | The three modules are a script critic, a picture check and a retry counter (section 6.3). `REVIEW` passes (L47). | The plan wires them into the last stage. Severity has no mapping to gate rows. | One home per module at its own stage. `BLOCKER = FAIL` where found. Making the viewer critic blocking is the Creator's call (D-130). | Yes for `WP-05`. |
| `ADR-V41-08` Keep CPU super-resolution; SeedVR2 only for degraded clips | `APPROVE_WITH_CHANGES` | `finish/superres.py` (740 L) is imported by `turn_pack.py`, `frame_pick.py`, `modal_ltx_jobs.py`. SeedVR2 is not in the repository. | "Degraded" is undefined. Worker edits void the ladder. | SeedVR2 stays an experiment until a measured before and after on identity. Define the trigger. | No. |
| `ADR-V41-09` Benchmark `layers25d` against `directed25d` | `APPROVE_WITH_CHANGES` | The runner already prefers `directed25d` and falls back to `layers25d` with a `director_not_used` review row (`run.py` L904-910). | They are a preferred and a fallback route that share the layers cache, not two rivals. V1-V6 have no measurable definition in the package. | Compare on shots where both can run; same inputs; a side-by-side reel. The Creator judges the look. | No. |
| `ADR-V41-10` Split paid caps; Modal cost rules | `APPROVE_WITH_CHANGES` | `spend_caps.json` `paid_tests.total_usd` is 5.9. The request is 8.0 + 3.0 + 2.5 = 13.5. `launch.json` pins 5.0937 USD per hour, not 3.95. | Caps cannot be set by an ADR. Hidden ladder cost. No experiment has a pod plan. | Caps only through `spend_caps.json` on the Creator's word. Each experiment gets an item-by-item plan (OR-23), the planning thread's confirmation (OR-24) and the audit (OR-34). | Yes for `WP-07`. |
| `ADR-V41-11` Blender 3D helper lane | `APPROVE_WITH_CHANGES` (lab only) | Blender retired by D-131 (`config/retired_era.json`; guard `episode/retired.py`). S9 map review supersedes the cited S8 review. | Reactivates a retired tool. The Creator's order is `REPORTED` only. The label-accent defect is not a 2D-versus-3D problem. | Lab only, outside production. Blind comparison with the S9 maps. Promotion by the Creator's recorded word. | No for `WP-02`. Yes for promotion. |

---

## 9. WP-by-WP decisions

| ID | Decision | Evidence | Problem | Required change | Implementation blocker |
|---|---|---|---|---|---|
| `WP-00` Baseline and test triage | `APPROVE_WITH_CHANGES` | CI command on `fc35615`: `4467 passed, 20 skipped, 3 deselected, 1 xfailed`, zero failures. Eleven suites on `eb80e443`: `230 passed, 1 skipped`. Sixty delta-related test files on `eb80e443`: `1303 passed, 1 skipped, 1 failed`; the failure is my rebuilt tree having no `.git` (`test_p14_lean.py` calls `git ls-files`). | The premise "177 legacy failures" is `REPORTED` and not reproduced. `allowed_modify: tests/**/*.py` conflicts with invariant 10. The baseline is not on GitHub. | Push the baseline. Record the CI result. Tests read-only; classification file only. | **Yes.** Nothing can be verified by CI until the code is pushed. |
| `WP-01` Contracts, clocks, `RouteRegistry` | `APPROVE_WITH_CHANGES` | Eleven schemas valid as documents; defects in section 6.1. `core/contracts.py` registry and fixture pattern from P1.2 (L660, L794). | Name collision. Wildcard create. No fixtures. No specification for `media_clocks.py`, `shot_state.py`, `route_registry.py`. | Section 6.1 changes. Explicit file list instead of a wildcard. Valid and invalid fixtures per contract. Semantic checks in `contracts.py`. | Yes for `WP-02`. |
| `WP-02` Single-shot closed-loop proof | `REJECT` (as written; re-issue) | Section 3.2: four touchpoints wrong, nine incomplete. Allowlist omits `ingest.py`, `timing.py`, `scene_run.py`, `modal_ltx_jobs.py`, `contracts.py`. `tests/integration/` does not exist. | T1 cannot be asserted through the runner. T3 conflicts with the clock rule. T6 is a unit test. T7's "timeline export" does not exist. A mocked model proves plumbing, not observation. The `$0.00` budget ignores the ladder. | Re-specify per section 13. | **Yes.** |
| `WP-03` Inspection router and fusion | `NEEDS_EVIDENCE` | No rules, no tests named beyond file names, no acceptance criteria. | Vague. | Tier rules, fusion rules, fixtures with HF paths and hashes, acceptance per fixture, false-alarm limit on clean controls. | Yes. |
| `WP-04` Action-aware editing and event sync | `REJECT` (as written; re-issue) | Allowlist is `sfx_planner.py`, `spine.py`, `plan.py`. The cut lives in `ingest.py`; the runner's sound path is `episode/sound_plan.py`, `audio/stems.py`, `episode/events.py`. Fixtures `1914-F01…F10` undefined. No tests, no acceptance. | Wrong files. | Correct allowlist. Defined fixtures. One acceptance line per 1914 defect. | Yes. |
| `WP-05` Wire QA and media modules | `REJECT` (as written; re-issue) | Section 6.3. `qa/loop.py` drives a different render path. No tests, no acceptance. | Modules wired at the wrong stage. | One row per module: stage, verdict mapping, test. | Yes. |
| `WP-06` 2.5D benchmark | `APPROVE_WITH_CHANGES` | `run.py` L904-910. Only `scripts/benchmark_25d_v1_v6.py` is allowed; no metric definitions. | No acceptance. | Define V1-V6 as measurements. Fixed shot list. Creator's side-by-side. | No. |
| `WP-07` Paid benchmarks | `NEEDS_EVIDENCE` | Three caps and three names. No model and checkpoint, data, settings, outputs, GPU and price, stop condition (OR-23). Sum exceeds the current paid-test ceiling. | Not a plan. | Three OR-23 plans. Retake smoke first (section 7.1). | Yes; also needs the Creator's budget decision. |
| `WP-08` 60-second vertical slice | `NEEDS_EVIDENCE` | No allowlist, tests, acceptance or budget. | Vague. | Name the shots and lanes. Acceptance: zero blockers, the Creator's watch, the 1914 defect list re-checked. | Yes. |
| `WP-09` 12-minute episode | `NEEDS_EVIDENCE` | Same. The existing gates apply (script approval OR-17, sample first OR-19, `paid_assets` gate). | Vague. | Same pattern as `WP-08` plus the existing gates. | Yes. |
| `WP-10` Skills consolidation, expert library, OTIO | `REJECT` (as written) | Section 4.2. OTIO export already exists. | Removes and merges Skills without proof. No allowlist, tests or acceptance. | Additive plan: keep 21, add the missing ones. Any merge needs a rule-level map and the Creator's word. | Yes for itself. Not for `WP-02`. |
| `WP-B1` Blender lab | `APPROVE_WITH_CHANGES` | `allowed_create: explainer_engine/experimental/blender_lab/**`; `forbidden_modify` covers `run.py` and `retired_era.json`. | The retired guard only refuses inside a v4.3 episode, so the lab is possible. No acceptance, no comparison target, no render-cost figure. `retired_era.json` is not hook-protected. | Acceptance against the S9 maps. Protect the two config files first. No import of lab code from production. | No for `WP-02`. |

---

## 10. Mandatory amendments

| ID | Amendment |
|---|---|
| MA-01 | **Baseline on GitHub.** Push `argon/p1-2-timing-contract` (`eb80e443`, and `0592114` if it differs). Run CI. The Creator accepts or rejects P1.2. State in writing whether V4.1 replaces or continues the Phase 0/1 master plan of PR #195. |
| MA-02 | **No reuse of `av_events/1`.** New name or version, a migration for existing files, existing event ids kept. |
| MA-03 | **Complete the specification.** Every section reference must resolve. Write the missing six (router rules, clocks API, cut rules, cross-vendor critic, fusion rules, `RouteRegistry`). Ship `v4_1_schemas.json` and hash it. Anchor the manifest's own hash. |
| MA-04 | **Reuse map.** For each new module, name the existing module it extends or replaces (section 3.4). A new module is allowed only where no home exists. |
| MA-05 | **Enforcement before observation.** The existing `regeneration_required` and the absence of a bound `ACCEPT` must refuse `scene.build`, `scene_run.job_spec` and `read_job`. |
| MA-06 | **Re-issue `WP-02`** with the correct insertion points: observation at ingest, the cut feeding the clock, continuity written per accepted shot. |
| MA-07 | **Schema hardening** per section 6.1, with valid and invalid fixtures and semantic checks in `core/contracts.py`. |
| MA-08 | **Stage-chain decision.** Either observation as rows and inputs inside existing stages, or new stages with a written migration for existing episodes. I recommend the first: it does not change `STAGES`. |
| MA-09 | **Honest cost.** Any WP that edits `modal_ltx_jobs.py` or `launch.json` states the ladder re-proof and its paid smoke, and needs the Creator's recorded word. No WP that can trigger it is labelled `$0.00`. |
| MA-10 | **Tests are read-only in `WP-00`.** |
| MA-11 | **Working locks** per section 6.5: CI scope job on the PR diff, the existing test command instead of `-m "unit"`, two more protected files, branch protection, one demonstrated refusal. |
| MA-12 | **Manifest corrections.** `approved_adrs` becomes `proposed_adrs` until the Creator approves. Every WP gets an allowlist, tests, acceptance criteria, a rollback and a stop condition. |
| MA-13 | **Skills are additive.** Keep the 21 Skills and 16 Agents. Add Skills for LTX workflows, Gemini picture correction, media timing, foley and film QA. Archiving the LoRA Skill and Agents is the Creator's decision. |
| MA-14 | **Define the 1914 fixtures.** Each id gets a shot, an HF path, a SHA-256, the measured facts and the expected verdict. Add clean controls. Add the five failures that have no owner. |
| MA-15 | **Model capabilities are proven before they gate.** One recorded call per capability. Deterministic checks first. Cross-vendor value measured on fixtures. |
| MA-16 | **Blender stays in the lab** until a blind comparison with the S9 maps and the Creator's recorded carve-out of D-131. |
| MA-17 | **Third-party media list per film**, checked before upload (section 7.3). |
| MA-18 | **One render path.** Decide whether films are assembled by `episode/run.py` or by `tools/render_tools`, and place the gates there. |

---

## 11. Remaining risks

| Risk | Why it remains after the amendments |
|---|---|
| Observer quality is unmeasured | No number exists for how often a vision model wrongly accepts or wrongly blocks. A closed loop with a weak observer either passes defects or stalls production. |
| The loop costs money and attention | Each rejected clip is a new paid scene run (cap `run_usd` 0.97) and each rejected picture a manual turn in Gemini chat. Each `HUMAN_REVIEW` is a decision for the Creator. No budget per episode is stated. |
| Stage-major runner | Adaptation per shot inside a per-episode batch remains awkward even with sub-gates. |
| Two authors | Gemini writes offline and returns zips; Claude threads apply them. Hooks bind only one of the two. Divergence is likely unless every change passes the same CI. |
| Code that exists only on Drive | It can be lost or drift. Every line reference in the plan depends on it. |
| Architecture churn | Drive holds five generations of architecture documents created within about fifteen hours (v2, v2.1, v3, V4 and V4.1 between 2026-11-18 16:42 and 2026-11-19 07:55 UTC). Documents are being produced faster than they can be verified. |
| `S03_SH003`-type defects | When speech fills the whole clip, no cut helps. Regeneration or retake is the only fix, and retake is unproven on the pin. |
| Visual defects without an owner | Fog bloom, sky blobs, label accents and picture-versus-narration mismatch stay uncovered until fixtures and checks exist. |
| Eleven new contracts | Each is a maintenance cost and a place for two truths. |
| Skills regressions | Any later merge can silently drop a rule that a test or a writer relies on. |
| Review limits | I did not run speech recognition, view clips at full resolution, open the 2.5D or map media, or see commit `0592114`. |

---

## 12. Recommended implementation order

This order is a recommendation to the planning thread and the Creator. It starts with what is free and already written.

| Step | Work | Why first |
|---|---|---|
| 0 | Push the baseline; CI; the Creator's decisions on P1.2 and on plan precedence (MA-01). Locks (MA-11). | Nothing else can be verified. |
| 1 | **Enforcement slice with no new model.** Make the existing picture observation block (MA-05). Wire `whisper_edit_points` (duplicate opening word, hallucinated tail) and the five start-frame checks in `videolane/plan.py`. Test on the six real clips. | It targets `S06_SH008`, the audio of `S03_SH007` and `S03_SH003` with code that already exists. It proves the closed-loop idea at zero spend. |
| 2 | `WP-01` with amended contracts (MA-02, MA-07). | Contracts before behaviour. |
| 3 | Re-issued `WP-02`: observation bound to the picture hash, video observation at ingest, cut feeding the clock, continuity per shot (MA-06, MA-08). | The real Milestone 1. |
| 4 | Audio evidence rules and event sync on the runner's real sound path (`S07_SH005`, `S07_SH006`). | Needs steps 2 and 3. |
| 5 | QA severity mapping and one home per QA module (`WP-05` re-issued). | Needs the verdict mapping from step 2. |
| 6 | 2.5D comparison (`WP-06`). Blender lab in parallel, outside production (`WP-B1`). | Independent of the loop. |
| 7 | Paid experiments, one at a time, each with its own plan. Retake smoke first. | Needs the Creator's budget. |
| 8 | 60-second slice, then a full episode. | Needs everything above. |
| Alongside | New Skills (MA-13), written as each step teaches something. | Additive, no risk. |

---

## 13. Explicit conditions that must be satisfied before `WP-02`

All twelve are required. Each is checkable.

| # | Condition | How it is checked |
|---|---|---|
| C-01 | The baseline commit is on GitHub and CI is green on that exact SHA. | The CI run on the SHA, with pass and fail counts recorded. |
| C-02 | The Creator has decided on P1.2 acceptance and on V4.1 against the Phase 0/1 plan. | His recorded word. |
| C-03 | `WP-01` is merged with amended contracts. No schema named `av_events/1` is redefined. Every contract has valid and invalid fixtures. | `tests/unit/test_contracts.py` green; the real `ep_truce_1914/production/av_events.json` still validates. |
| C-04 | A written `WP-02` specification names the insertion points: where picture observation runs; where the binding is checked (`scene.build`, `scene_run.job_spec`, `read_job`); where video observation runs relative to ingest and the voice stage; how a cut reaches `retime_with_edit_points`; where continuity is written per shot. | Confirmed by the planning thread (OR-24, OR-26) and approved by the Creator. |
| C-05 | The `WP-02` allowlist lists every file the specification touches. If the Modal worker is on it, the ladder re-proof budget and the Creator's recorded word exist. | The manifest; the CI scope job. |
| C-06 | The stage-chain decision is made (MA-08), with a statement of what happens to the existing records of `ep_truce_1914`. | Written decision; a test that an existing episode's state is still readable. |
| C-07 | The reuse map is accepted (MA-04). No `WP-02` module duplicates `perceive_picture`, ingest edit points or `continuity_card`. | Review of the specification against section 3.4. |
| C-08 | Tests T1 to T7 are rewritten so they can run. T1 asserts the refusal at the real refusal point. T3 includes the clock retime. T6 is a unit test. T7 is defined on outputs that exist. Clean-control tests show a good shot is not blocked. One media-marked test replays the six real clips with expected outcomes. | The test file, reviewed before code. |
| C-09 | The locks work: the CI scope job refuses a deliberate out-of-scope change; `picture_route.json` and `retired_era.json` are protected; branch protection is on. | The refused demonstration PR. |
| C-10 | Verdict semantics are defined and tested: an observation `BLOCKER` cannot pass through `GO_ON`. | A unit test on `check_before`. |
| C-11 | `WP-02` makes no paid call. If any live model call is wanted, it has its own plan and the Creator's approval. Results from mocked models are labelled as plumbing proof only. | The ledger; the report wording. |
| C-12 | The manifest is corrected: proposed, not approved, ADRs; acceptance, rollback and stop condition for `WP-02`. | The manifest diff. |

---

## Appendix A. Commands and raw results of this review

| What | Command or method | Result |
|---|---|---|
| Baseline search | `git ls-remote`, `git fetch <sha>` | Branch and both SHAs absent on GitHub. |
| Drive code | Downloaded `REPO_TEXT_argon-p1-2-timing-contract_eb80e443.zip`, `Explainer_Engine_P1_2_Complete_eb80e443_2026-11-17.zip`, `Explainer_Engine_V4_1_Blueprint_And_Review_Package_v2.zip` | 1,691 text files; rebuilt a full tree by overlaying on `fc35615`. |
| Package identity | `sha256sum` on the seven uploaded files and the seven in the Drive zip | Identical. Manifest: `e90b29697ef2412a7a860eb08caf2e6d4a573ed75998e8504b275bc152ed5246`. |
| Full suite on `fc35615` | `python -m pytest -q -m "not system and not media"` (Python 3.13.18, `CLAUDE_EFFORT` unset) | `4467 passed, 20 skipped, 3 deselected, 1 xfailed in 778.53s` |
| Eleven named suites on `fc35615` | The exact command of DOC-02 §4 | `230 passed, 1 skipped` (first run `1 failed` because my session had `CLAUDE_EFFORT=xhigh`; with it unset the governance suite gives `31 passed`). |
| Eleven named suites on `eb80e443` | Same | `230 passed, 1 skipped in 87.68s` |
| Changed test files on `eb80e443` | Eight files | `295 passed in 30.48s` |
| Delta-related tests on `eb80e443` | 60 test files that import timing, contracts, map clip, runner or render tools | `1 failed, 1303 passed, 1 skipped in 263.89s`; the failure needs a `.git` directory. |
| Schemas | `jsonschema.Draft202012Validator.check_schema`; real and hand-made instances | 11 of 11 valid as schemas; defects in section 6.1. |
| Upstream LTX | `git clone https://github.com/Lightricks/LTX-2.git`, `git merge-base --is-ancestor`, `git diff --shortstat`, `git show <sha>:…/retake.py` | Section 7.1. |
| 1914 media existence | HTTP status on eight `vano1919/tmr-artifacts` paths | Eight of eight exist (two need the `explainer-engine/` prefix). |
| Clip metadata | `ffprobe -show_entries stream=…` on six clips | H.264, `24/1`, time base `1/12288`, AAC 48 kHz stereo, `start_pts=0`, `initial_padding=0`. |
| Loudness envelope | `ffmpeg` to 48 kHz mono PCM; RMS per 50 ms; onset = more than 15 dB over the median and at least 8 dB over the previous window | Section 5.1. |
| Contact sheets | `ffmpeg -vf "fps=2,scale=384:-1,tile=5x2"` on `S03_SH007` and `S04_SH014` | Section 5.1. Stored next to this report. |
| Sound library | Parsed `assets/audio/library/manifest.json` | 260 items; section 7.3. |

## Appendix B. What I did not do

- I did not change any repository file, configuration or code, and I pushed nothing.
- I made no paid call.
- I did not run speech recognition on any clip.
- I did not open the 2.5D slice files or the map reel.
- I did not see commit `0592114`.
- I did not check current Modal prices or any model's live capabilities.
