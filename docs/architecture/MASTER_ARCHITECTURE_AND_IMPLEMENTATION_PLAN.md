# Explainer Engine — Master Architecture & Implementation Plan

> **Owner:** Creator  
> **Document role:** Master architecture, module map, phased implementation roadmap, acceptance gates and live status register.  
> **Status:** Phase 0 complete with limitations; Draft PR #195 is open for review against the active integration baseline.  
> **Audit baseline:** o239-argon-impl @ a060cf0bb33a00974568d91c1dd30816de35da32 (2026-11-16 13:52:45 UTC).  
> **Document branch:** docs/phase-0-master-architecture-2026-11-16.  
> **Authority:** This file owns the target architecture, roadmap and phase status. Existing detailed schemas/rules remain in their canonical documents and are linked rather than duplicated.

## 0. Live status — update after every milestone

**Overall:** Phase 0 is complete with explicit limitations. The target architecture and staged roadmap are documented as the proposed baseline. No production source code has been changed; no existing branch/PR has been merged, closed or retargeted; no paid generation or cloud GPU job has been launched.

| ID | Work item | Status | Evidence / limitation |
|---|---|---|---|
| P0.0 | Freeze audit scope and baseline | DONE | Read-only baseline recorded at o239-argon-impl @ a060cf0. |
| P0.1 | Repository, branch and PR inventory | DONE WITH LIMITATIONS | 2,546 tree entries; 102 branch refs; 17 open Draft PRs; branch heads sampled. Full semantic reconciliation of every unique PR change is not complete. |
| P0.2 | Current architecture, modules, contracts and runtime | DONE WITH LIMITATIONS | Episode runner, routing, timing, audio, assembly, contracts, store, ledger, governance, QA and tests inspected. No full automated import/dependency graph was generated. |
| P0.3 | Truce 1914 production and incident audit | DONE WITH LIMITATIONS | Manifest, script, 84-shot plan, edit points, runbook, correction log and incident reports inspected. Hugging Face video/image binaries were not independently opened in this audit. |
| P0.4 | Tests, CI, coding standards and release controls | DONE WITH LIMITATIONS | 367 Python unit-test files found; recent PR Quality jobs passed. No tests were run in this read-only audit. Current HEAD returned no combined status rows. Ruff absent. Branch protection/rulesets not fully verified. |
| P0.5 | KEEP / IMPROVE / REPLACE / REMOVE / BUILD disposition | DONE — INITIAL | See section 4. Code-level changes still require individual specs and tests. |
| P0.6 | Target architecture and implementation roadmap | DONE — PROPOSED BASELINE | See sections 5–9. Some concrete infrastructure products remain benchmark decisions. |
| P0.7 | Final consistency review and reviewable PR | DONE WITH LIMITATIONS | File fetched back and checked (806 lines); Draft PR #195 contains exactly one documentation file and targets the active baseline. Awaiting human review/merge; no production code changed. |

**Status protocol:** only NOT STARTED, IN PROGRESS, BLOCKED, DONE, DONE WITH LIMITATIONS. Every update records date, commit/artifact, evidence and limitation. A status is never DONE merely because code was written or an agent claimed completion.

### 0.1 Scope and safeguards

- Inspect current repository, relevant branches/PRs, active production path and recent incident evidence. Main is not the only truth; the chosen audit baseline is the creator's current branch.
- Preserve existing code, successful assets, unmerged work, history and approved visual identity.
- Do not delete, rewrite, merge, close, force-push or retarget existing branches/PRs in Phase 0.
- Do not run paid APIs, paid image/video generation, cloud GPU jobs or publishing.
- Do not change production code during Phase 0. This master Markdown file is the only intended repository change.
- Separate verified facts, historical decisions, current implementation claims, hypotheses and target proposals.
- A target architecture decision does not automatically authorize replacing a current route. Route changes require evidence, compatibility analysis, tests, acceptance criteria and required owner approval.
- A report that says a render passed is not the same as this audit independently viewing/listening to the media. State the difference.

### 0.2 Audit baseline

Repository: https://github.com/vano1919/explainer-engine

Main is the default branch, but the creator's active working baseline for this audit is o239-argon-impl at a060cf0bb33a00974568d91c1dd30816de35da32. This does not assert that o239-argon-impl is already the protected release branch.

Initial read-only inventory:
- Recursive active-branch tree: 2,546 entries, not truncated.
- Python source files under explainer_engine/: 511.
- Python files under tests/unit/: 367 (file count, not number of test cases).
- Remote branches returned: 102.
- Open PRs returned: 17; all Draft.
- o239-argon-impl vs main: 725 commits ahead, 0 behind; 300 changed files (225 added, 74 modified, 1 removed).
- Active HEAD's combined-status query returned no rows. This does not prove local/PR tests were never run.
- Branch metadata reported main as unprotected. The separate branch-protection/ruleset endpoint was inaccessible to the connected GitHub integration (403); actual ruleset state is therefore unverified.
- A scheduled RunPod watchdog workflow run on main failed on 2026-11-16 because RUNPOD_API_KEY was missing. Its scan step succeeded; the final key/billing check failed. This is an operations/secret mismatch on the default branch, not evidence of a visual render test failure.
- Quality jobs observed for PRs #194, #193 and #192 succeeded on those PR heads. These are not CI results for the active o239-argon-impl HEAD.

PRs are stacked on multiple different base branches. Do not bulk merge or bulk close them. Compare unique commits and dependencies against the active baseline before deciding where they belong. The 2026-11-12 branch inventory is historical; its count is now stale.

---

# 1. Owner decisions and project constraints

This section consolidates the creator's 81 architecture answers and later explicit corrections. It describes the target system; it does not claim all capabilities already exist.

## 1.1 Product goal

Build an AI-first historical docudrama and evidence-led explainer production system that completes a film, not merely isolated clips or images. Long-form target is 8–12 minutes. Christmas Truce 1914 is a short 6–8 minute pilot, not the long-term duration ceiling. Primary audience is English-speaking and US-oriented. Additional language versions are supported.

## 1.2 Creative authority and history

- One Main AI Director owns the automated creative direction across the film.
- Domain Experts and independent Reviewers provide specialist analysis; they do not create competing Directors.
- The creator remains Owner and final authority for required approvals, major creative changes, additional spend and publishing.
- Use professional film principles to create an original cinematic language. Study famous directors/films for specific techniques, not whole-style imitation.
- Historical events are the evidence base. Composite characters, personal scenes and invented dialogue/connective detail are allowed when properly marked and never presented as verified fact.
- Maintain a source-backed Historical Fact Database with Verified, Disputed, Unknown and Dramatized distinctions. Record disagreement instead of silently resolving it.
- Review historical claims and visuals. AI reconstructions must not be presented as genuine archival photographs.
- **Disclosure:** dramatization disclaimer only in the video description and pinned comment, Georgian and English. There is no in-video disclaimer end card and no closing disclosure line. Keep the per-scene dramatized data field. Do not add a separate narrative end card/closing line without a new explicit owner decision.

## 1.3 Story and runtime

- Script and Visual Storyboard evolve iteratively, not as isolated consecutive documents.
- Every narration segment passes through a mandatory Narration-to-Visual Bridge: dates, places, names, numbers, objects, events and emotional cues receive deliberate visual treatment or an intentional reason for omission.
- The working visual mix is measured by final runtime, not shot count: approximately 60% AI video, 30% photo/image animation and collage, 10% maps/graphics/other explanatory visuals.
- These percentages are adaptive targets, not quotas. Director may change the distribution when story needs justify it; report measured runtime shares and explain material deviations.
- Shot count/duration is derived from dramaturgical purpose, performance, physical action, pacing and coverage, not universal quotas.
- Long-form target 8–12 minutes; Truce remains a pilot.

## 1.4 Visual identity and generation

- Main identity is crossworld_main_style_v1, reference assets/style/main_style_5709.png. Preserve its defining palette, shapes, face/figure language and painterly grammar while allowing dramatic variation in lighting, atmosphere, composition and contrast.
- Battlefield 1's cold blue/steel-cyan versus warm amber contrast is a lighting/color reference only, not a request to replace the selected identity.
- Support AI video, photo animation, collage, 2.5D/parallax, maps, infographics, diagrams, timelines, archival materials, title/motion graphics, compositing and other appropriate visual forms.
- Separate Video Continuity and Photo Animation workflows. Blender remains an available option, not the universal renderer.
- Shot design includes shot size, angle, focal length/lens behavior, camera position/movement, blocking, composition, lighting, focus and visual continuity.
- Per-shot continuity strategy is selected among references, image-to-video, keyframes, last-frame continuation, layout conditioning or independent generation based on the model's actual capabilities.
- If a model only accepts a frame-0 conditioning image, do not claim native end-frame conditioning or video extension. Use a measured hand-over frame as the next clip's start if that is the supported approach.
- Create alternative variants for important scenes when the creative benefit justifies the cost; do not make variants mandatory for every shot.

## 1.5 Audio, editing and clock

- Audio is a full discipline: narrator, character dialogue, singing, ambience, Foley, music, SFX, mixing, ducking, spatial placement where useful, mastering and QC.
- Each voice has a persistent Voice Identity: timbre, accent, pace, pronunciation, emotional range and continuity.
- Visible singing and lip-sync are first-class cases.
- The Nov 16 audio/our_voices.py commit has a plan/cache/cost guard and fake-client tests for 39 character dialogue lines, but no live API client and no generated audio. Integrate the creator-approved voice path; do not assume LTX-native dialogue is the canonical final character voice.
- One Master Film Timeline is the single temporal source for scenes, shots, narration, dialogue, music, SFX, events, transitions, captions and frames. Every downstream stage consumes its fingerprint/version. No parallel independent clocks.
- Editing is creative post-production: montage, pacing, cut points, continuity, transitions, sound/image synchronization, color matching, compositing, alternate cuts and final mastering. FFmpeg/encoders are tools, not the creative Editor.
- Primary output is 16:9 long-form; support 9:16 Shorts and other platform formats through deliberate reframing/recomposition and independent QC.
- Support multilingual scripts, voices, localization, captions/subtitles and language-specific QC.

## 1.6 System, data, compute, quality and learning

- Hybrid distributed execution: central Orchestrator/Director, modular Engines, isolated Workers for expensive/long-running tasks, Local + Cloud execution.
- Modular core first; do not convert every module to a Microservice. Extract workers/services when isolation, GPU boundaries, scaling, failure containment or deployment needs justify them.
- Versioned contracts, explicit module interfaces, central Production State, Dependency Graph, unique asset IDs, version history and checkpoints.
- Structured state/metadata is separate from large media Assets. Use tiered storage and preserve critical originals/approved outputs.
- Model/tool/provider selection is task-based and provider-agnostic. Maintain capability/benchmark/compatibility registries and fallback.
- Compute preflight compares actual availability, GPU/VRAM, cost, queue, speed and expected result. Creator approves the resource choice before cost-bearing work; additional migration spend requires approval.
- Quality has 60/40 priority over cost as a decision preference, not a literal money split. Minimum quality cannot be sacrificed.
- Budget estimate, reservation, caps, 80% stop, retry ceiling, forecasts and final cost reports are mandatory.
- Multi-layer QC covers historical, narrative, visual/continuity, audio, editing/timing, technical export and final-media rights. Diagnose and repair locally; preserve successful work.
- Record model/version, prompt/settings, seed where available, input/output hashes, provider, run, cost, verdict, author and reason. Do not promise deterministic output from nondeterministic models.
- Tool/model/effect/technique/Skill licensing is not a selection criterion. Rights checks apply to final media assets (music, SFX, photos, footage, fonts, etc.) for YouTube/commercial use.
- Secrets live in environment variables and gitignored .env; commit only .env.example. Never log or commit credentials.

---

# 2. Current repository architecture — evidence-based

## 2.1 Current package map

| Package | Observed responsibility | Initial disposition |
|---|---|---|
| episode/ | Episode manifest/context, script routing, measured timing, stage runner, sound plan, acceptance and stage records | KEEP as current production spine; extend and reduce oversized responsibilities incrementally |
| core/ | Versioned contracts, atomic store, job state, fingerprints, cache, ledger, spend caps and errors | KEEP as foundation for state, provenance and recovery |
| production/ | 2.5D layers, scene direction, visual bridge, map integration, assembly helpers and validation | KEEP working routes; split only when a proven boundary exists |
| videolane/ + training/pods/ltx/ | LTX-2.5 shot planning, scene packaging, hand-over/continuation and Modal execution | KEEP current video route; harden contracts and benchmark alternatives |
| maps/ + infographics/ | Python map/action renderers, geography and numerical visuals | KEEP; extend with shared timing/event/asset contracts |
| audio/ + episode/sound_plan.py | Scribe timing, voice layers, clip audio, sound events, stems, mixing and checks | KEEP proven parts; integrate owner-approved character voices and one clock |
| edit/ + production/assemble.py | Boundary manifests, transitions, chunked assembly and mastering | KEEP renderer/assembler; build creative editing intelligence around them |
| qa/ + episode/acceptance.py | Frame, motion, face, visual, sound, technical, historical/publish and acceptance checks | KEEP; consolidate through shared QC report contracts |
| research/, scripting/, standards/ | Claim maps, script stages, sourced rules, episode rules and validators | KEEP; connect to Editorial Intelligence and Historical Evidence Engine |
| world/, assets/, imagegen/ | Look definition, world/character data, image intake and asset reuse | KEEP approved assets; extend provenance, versions and multi-method routing |
| cloud/, orchestration/ | Provider controls, paid-run guards, schedules, workers and orchestration | KEEP cost/availability guards; reconcile duplicate provider paths after dependency analysis |
| .claude/agents/, .claude/skills/, governance/ | Agent roles, Skills, model routing, hooks and approvals | KEEP; make the protocol portable to Gemini/other coding agents |
| docs/ | Canonical specifications, decisions, historical reports and progress | KEEP canonical specs; this file owns target architecture/roadmap/status, not every low-level rule |

## 2.2 Current executable episode path

The v4.3 episode runner exposes eight stages grouped under G1–G10:

1. script — episode isolation, schema, story/scene/shot validation and route decisions.
2. sound_plan — initial sound plan and source resolution.
3. pictures — image turn-pack intake, validation and working-resolution promotion.
4. voice — narration/transcript alignment and measured shot/frame timing.
5. clips — route dispatch to map_action, still_25d or pre-generated video.
6. sound — rebuild sound plan on the measured clock, render/validate stems and delivered mix.
7. assemble — apply boundary/transition plan and chunked assembly; verify frames and timing fingerprints.
8. qa — final acceptance gates and review artifacts.

Each stage writes a record with verdict, output and input fingerprint; stale/missing previous stages block. Rehearsal cannot pass final QA. Paid video generation runs outside the episode runner and must enter as a recorded/QA'd clip.

### Current shot routes

| Route | Current implementation | Limit |
|---|---|---|
| video | LTX-2.5 distilled on Modal via videolane/scene.py, training/pods/ltx/scene_run.py, training/pods/ltx/modal_ltx_jobs.py | Current path conditions on frame 0; continuation uses a selected hand-over frame, not assumed native extension |
| still_25d | Approved still + depth/layers + deterministic camera/effects via layers25d.py or directed25d.py | Directed path needs valid layers/direction; fallback is reported; masks/faces/crowds/edges/camera defects are known incident classes |
| map_action | Python map plate + action layer, location-anchored events | Good for geography, routes and numbers; keep map-specific semantics with common timing/audio/QC contracts |

The router reports runtime mix by measured/estimated duration. The current code also has a solemn_historical_docudrama profile of 60% still, 30% video, 10% map. The Truce script declares 30% video, 60% illustration, 10% map. These are current-state facts, not the new target default.

## 2.3 Strong reusable foundations

- core/contracts.py: versioned JSON-schema contracts.
- core/store.py: atomic writes and checkpointed job/episode state.
- core/ledger.py / core/spend_caps.py: pre-call reservations, caps, 80% stop, run history.
- episode/timing.py: narration/word timing, shot frames/spines, timing fingerprint and clock-alignment checks.
- episode/sound_plan.py: sound plan on the measured clock.
- editing/boundary_manifest.json path: shared boundary decisions consumed by audio and assembly.
- production/assemble.py: chunked rendering, frame-count verification and reuse of completed chunks.
- episode/acceptance.py and qa/: measured PASS/FAIL/REVIEW/NOT_RUN gates.
- governance/, config/model_routing.json, .claude/settings.json: agent model/effort routing and hooks.
- docs_lint.py: canonical home/links for rule and decision IDs.
- 16 Claude agent files and 21 Skills were visible on the active branch. Valuable foundation, not yet the full future Director/Expert architecture.

## 2.4 Key current-state gaps and conflicts

1. **No unified AI Main Director runtime found.** production/living_director.py is a large scene-direction implementation for current 2.5D work; the Claude orchestrator is a procedural workflow agent. Neither alone is the future Main AI Director coordinating Editorial, Historical, Narrative, Cinematography, Visual, Audio and Editing Experts.
2. **Generation is not fully provider/method neutral.** Current routes are concrete lanes; Blender, older Qwen/LoRA, old LTX and RunPod remain as code/history, many retired for v4.3. Future routing needs capability contracts and benchmarks.
3. **Voice transition is incomplete.** audio/our_voices.py is a plan/cache/cost guard with fake-client tests, not live voice generation. Current sound code still supports LTX clip speech/insert handling. Integrate the approved voice assets and measured timings.
4. **Timeline generations coexist.** Active episode path uses episode/timing.py and audio/timing.json; older audio/spine.py / audio_spine/1..2 belongs to the older film-shots lane. Confirm all consumers before any retirement. Do not activate a second clock.
5. **Visual mix differs from the new decision.** New target baseline is 60% AI video / 30% photo-animation & collage / 10% maps/graphics by runtime. Truce data says 30/60/10. System must report and explain the variance; do not rewrite pilot data automatically.
6. **Oversized modules are refactor candidates, not automatic rewrites.** episode/run.py ≈108 KB, production/living_director.py ≈101 KB, production/assemble.py ≈88 KB, cloud/runpod.py ≈129 KB. Prove boundaries with tests before splitting.
7. **Docs disagree with implementation.** CLAUDE.md says no linter/formatter/CI although Quality workflow exists; EPISODE_FIRST.md has stale Wan wording while D-132 makes LTX the current video route; parts of ORCHESTRATION.md still describe old RunPod/animated-job routes.
8. **CI is incomplete.** quality.yml runs tests, docs lint and palette checks but no Ruff. The active HEAD returned no combined status rows.
9. **Branch topology is fragile.** 102 refs and 17 Draft PRs on different bases create stale-base/ownership risk.
10. **Direct render evidence is incomplete in this audit.** Shot plan and incident reports describe contact sheets, start/middle/end checks and Whisper transcripts, but this audit did not independently open the referenced video/image binaries.
11. **Truce S08 still contains an in-video closing card.** The Nov 15 shot plan includes S08_SH004 and the line “For one day, they remembered they were human.” This conflicts with the later explicit no-end-card/no-closing-line instruction and must be removed from the next approved pilot plan.
12. **Historical incident audit is not full-suite proof.** Nov 15 reports show fixed/guarded, process, open and not-checkable items; full unit suite was not completed in that audit. Do not present those reports as a current full green run.

---

# 3. Truce 1914 evidence and pilot corrections

## 3.1 Available artifacts

Active branch includes episode.json, story/production_script.json, the Nov 15 SHOT_PLAN.md with 84 director briefs, edit_points.json, picture_overrides.json, MAC_RUNBOOK.md, CORRECTIONS_LOG.md, incident journal/audit, Scribe/Whisper transcripts, existing narration reads, and the 39-line character voice specification.

## 3.2 Defect classes documented in the project

| Defect | Evidence reported | Required engineering response |
|---|---|---|
| Duplicate/cut dialogue | S06_SH008 duplicate “Maybe”; S03_SH003 cut “Nacht”; other trims in edit points | clip speech analysis, trim contracts, spoken-word continuity gate |
| False speech / visual bloom | S03_SH007 silent beat transcribed as words; white bloom | audio mute/trim when needed, visual bloom gate, human review |
| Broken action state | S04_SH014 handshake clip ends after hands separate | explicit action start/end state and continuity QA |
| Narration/picture conflict | S08_SH003 shows fraternising while narration says war continued | bookend override to opening empty field, manifest/hash trace |
| 2.5D layers/camera | invisible breath, poor pan, cropped boots, snow on frame 0/over faces, face/crowd smears, camera snaps/whips, sky blur | per-frame motion/edge/face/crop/effect gates and direct visual review |
| Lighting | burned sky, smeared faces, effects leak to people | source-aware lighting/effects with bounded ceilings and per-shot checks |
| Audio realism | missing library takes, ambience/bed continuity, timing and level issues | scene-aware sound plan, stems measurement and listening |
| Timeline | trims, word alignment, frame/sample conversions and clip handover | one clock fingerprint and dependency invalidation |

Project reports state that current photos/clips were checked through contact sheets and start/middle/end sampling, and 56 LTX clips were transcribed. The reports also record remaining defects and incomplete suite coverage. This audit did not independently open those HF media files; treat them as reported evidence until the next full Pilot acceptance review.

## 3.3 Required pilot data reconciliation

- Remove S08_SH004 in-video end card/closing statement and end-card-only music arrangement.
- Keep dramatization disclaimer only in Description and Pinned Comment, Georgian and English.
- Keep per-scene dramatized metadata and Historical Accuracy Report.
- Reconcile Truce's declared 30/60/10 mix with the new 60/30/10 working profile. Director may deviate for story reasons, but needs a runtime report and reason.
- Integrate creator-approved ElevenLabs character voices before another paid generation. Do not spend credits or generate the 39 lines without an itemized price/credit plan and explicit approval.

---

# 4. Disposition matrix — KEEP / IMPROVE / REPLACE / REMOVE / BUILD

| Area | Current | Target | Decision |
|---|---|---|---|
| Episode lifecycle | v4.3 runner, stage records/fingerprints | central Orchestrator over versioned engine contracts | KEEP + EXTEND |
| Schemas/contracts | JSON Schema | contract-first cross-engine schemas and compatibility checks | KEEP + EXTEND |
| State/checkpoints | atomic file store, episode records, ledger | structured Production State, database, dependency graph and recovery | KEEP now; migrate incrementally, not wholesale |
| Timing | episode timing, word spine, timing ID, render epoch | one frame/sample timebase across all stages | KEEP current clock; extend; isolate legacy spine |
| LTX video | LTX Modal worker/video lane | capability-based video adapters | KEEP current route; improve; benchmark before changing |
| Photo animation | layers25d/directed25d/depth/segmentation | dedicated photo animation engine | KEEP proven methods; improve and isolate defects |
| Maps/graphics | Python map/action renderers | adaptive map/graphics lane with event/timing/QC contracts | KEEP + EXTEND |
| Blender | existing package and skills; old path retired in v4.3 | optional 3D method selected by benchmark and shot needs | KEEP optional; don't silently reactivate |
| Qwen/LoRA/old LTX/RunPod | retained historical code and tests | legacy/research adapters isolated from active route | KEEP history/tests; retire only with proven usage scan |
| AI Direction | procedural agents + deterministic scene director | one Main AI Director + experts + critics | BUILD above existing engines; keep deterministic helpers |
| Editorial/research | claim map, rules, script stages and skills | topic intelligence, historical evidence and iterative story/visual planning | KEEP + EXTEND |
| Audio | sound plan, stems, clip audio and voice insert code | Audio Director, canonical voices, one timeline and QC | KEEP; improve voice integration |
| Editing | boundary manifest, transitions, chunked assembly | creative editing intelligence over timeline | KEEP render path; BUILD edit director |
| QC | specialized gates/tests | shared report contract, severity, root cause and repair | KEEP + CONSOLIDATE |
| Agents/Skills | Claude-specific agents and skills/hooks | shared agent/skill contracts and provider-specific enforcement | KEEP + EXTEND |
| Docs | canonical specs, decision IDs and long progress log | master architecture/status plus canonical detailed docs | KEEP canonical sources; improve sync |
| CI/style | Pytest/docs/palette, no Ruff; stale rules | add Ruff and architecture-boundary gates | IMPROVE incrementally |
| Git process | many stacked branches and Draft PRs | one integration baseline, short task branches and reviewed PRs | CHANGE process; no mass merge |

**Disposition rules:** KEEP preserves proven behavior; IMPROVE adds contracts/observability/tests; REPLACE is per-component and requires parity/rollback evidence; REMOVE requires a complete usage/dependency scan and recorded decision; BUILD creates missing capabilities. No broad rewrite of 511 Python files.

---

# 5. Target architecture

## 5.1 Architecture style

**Chosen baseline:** Hybrid Distributed Architecture with a Modular Monolith core, bounded contexts, versioned contracts and independent Workers where expensive/isolated work justifies them.

- Direct typed calls for synchronous in-process work.
- Durable queue/events for long-running or independently retryable jobs.
- Each task includes project/episode/scene/shot IDs, task ID, contract version, input hashes, approval state, budget ceiling, provider/model, deadline and correlation ID.
- Workers return typed artifacts and evidence; they do not mutate unrelated state.
- Main AI Director owns creative decisions; Orchestrator owns execution/dependency state. Do not confuse the two.

## 5.2 High-level architecture diagram

~~~mermaid
flowchart TB
  OWNER["Creator / Owner"]
  STUDIO["Production Control Center"]

  subgraph CONTROL["CONTROL PLANE"]
    EDITORIAL["Editorial Intelligence"]
    DIRECTOR["Main AI Director"]
    EXPERTS["Domain Expert Agents"]
    APPROVAL["Approval + Budget Controller"]
    ORCH["Production Orchestrator"]
    SCHED["Dynamic Scheduler"]
    MODELS["Model / Tool Intelligence"]
  end

  subgraph PROD["PRODUCTION ENGINES"]
    RESEARCH["Historical Research + Evidence"]
    STORY["Narrative + Script"]
    BRIDGE["Narration-to-Visual Bridge"]
    WORLD["Character / World / Asset Engine"]
    CINE["Cinematography + Shot Design"]
    VIDEO["AI Video + Continuity"]
    PHOTO["Photo Animation + 2.5D"]
    THREE["Optional Blender / 3D"]
    GRAPHICS["Maps / Motion Graphics / VFX"]
    AUDIO["Voice / Music / SFX / Mixing"]
    TIMELINE["Master Film Timeline"]
    EDIT["Cinematic Editing"]
    SUBS["Subtitles / Captions / Localization"]
    MASTER["Color / Mastering / Export"]
  end

  subgraph EXEC["EXECUTION PLANE"]
    QUEUE["Durable Task Queue / Events"]
    LOCAL["Local Workers"]
    CLOUD["Cloud Workers"]
    ADAPTERS["Provider / Model Adapters"]
    RENDER["Render / Encode Workers"]
  end

  subgraph GOVERN["QUALITY & GOVERNANCE"]
    QC["Multi-Layer QC"]
    DIAG["Root Cause / Repair / Re-QC"]
    HISTORY["Decision / Version / Provenance History"]
  end

  subgraph DATA["DATA PLANE"]
    DB[("Production Database")]
    ASSETS[("Asset Storage")]
    KB[("Knowledge Base")]
    REG["Skill + Model + Asset Registries"]
    DEP["Dependency Graph"]
  end

  DELIVERY["Delivery + Publishing Package"]
  ANALYTICS["YouTube Analytics + Learning Loop"]

  OWNER <--> STUDIO
  STUDIO <--> APPROVAL
  STUDIO <--> ORCH
  EDITORIAL --> DIRECTOR
  EXPERTS <--> DIRECTOR
  APPROVAL <--> DIRECTOR
  DIRECTOR <--> ORCH
  SCHED <--> ORCH
  MODELS <--> ORCH
  ORCH --> RESEARCH
  RESEARCH --> STORY
  STORY --> BRIDGE
  BRIDGE --> CINE
  WORLD --> CINE
  CINE --> VIDEO
  CINE --> PHOTO
  CINE --> THREE
  CINE --> GRAPHICS
  AUDIO <--> TIMELINE
  VIDEO <--> TIMELINE
  PHOTO <--> TIMELINE
  GRAPHICS <--> TIMELINE
  TIMELINE --> EDIT
  EDIT --> SUBS
  EDIT --> MASTER
  VIDEO --> QUEUE
  PHOTO --> QUEUE
  THREE --> QUEUE
  GRAPHICS --> QUEUE
  AUDIO --> QUEUE
  QUEUE --> LOCAL
  QUEUE --> CLOUD
  LOCAL --> ADAPTERS
  CLOUD --> ADAPTERS
  ADAPTERS --> RENDER
  RENDER --> QC
  QC --> DIAG
  DIAG --> ORCH
  QC --> HISTORY
  MASTER --> DELIVERY
  SUBS --> DELIVERY
  DELIVERY --> OWNER
  DELIVERY --> ANALYTICS
  ANALYTICS --> EDITORIAL
  ORCH <--> DB
  AUDIO --- ASSETS
  VIDEO --- ASSETS
  DIRECTOR <--> KB
  ORCH <--> DEP
  MODELS <--> REG
  HISTORY <--> DB
~~~

## 5.3 Layer responsibilities

| Layer | Components | Owns | Does not own |
|---|---|---|---|
| Owner / Studio | Dashboard, approvals, project controls | human decisions, review, pause/resume | hidden creative or spend decisions |
| Editorial | Topic discovery, audience and originality analysis | topic proposals | final owner choice |
| Direction | Main Director, Experts, Critics | creative intent, scene/shot plans | untracked mutation of unrelated assets |
| Orchestration | Orchestrator, state machine, scheduler, queue | dependencies, task dispatch, budgets, recovery | independent creative authorship |
| Research/Narrative | Historical claims, story, script, storyboard | evidence and story contracts | unverified factual assertion |
| Visual | World/characters, cinematography, video/photo/3D/graphics/VFX | visual methods and assets | audio/master timing ownership |
| Audio | voice, singing, music, SFX, Foley, mixing | audio performance and stems | second film clock |
| Timeline/Editing | master timeline, edit plan, montage, transitions | time, sequence, rhythm and final cut | hidden retiming outside contracts |
| Quality | history/narrative/visual/audio/edit/technical/rights QC | measured verdicts | weakening failed gate |
| Data/Knowledge | database, storage, registries, KB, dependency graph | state, metadata, versions, provenance | model-specific generation logic |
| Delivery/Learning | exports, metadata, subtitles, publishing, analytics | release packages and feedback | public release without approval |

## 5.4 Main AI Director hierarchy

Main AI Director is the single creative authority inside the automated system. Experts specialize and Reviewers challenge the evidence; no competing Directors are created.

| Expert | Domain | Outputs |
|---|---|---|
| Editorial Expert | topic, audience, originality, format | topic scorecard, editorial brief |
| Historical Expert | source review, claims, disputes | claim map, source ledger, uncertainty report |
| Story Expert | hook, acts, character/emotional arc | scenario, beat sheet, script recommendations |
| Visual Storyboard Expert | narration-to-visual mapping | visual bridge map, storyboard |
| Cinematography Expert | lens, angle, blocking, movement, light | shot plan/camera instructions |
| World/Character Expert | character, wardrobe, props, environment | canonical assets, continuity references |
| Video/Animation Expert | video, photo motion, 2.5D, continuation | method plan, prompts, motion specs |
| Graphics/Cartography Expert | maps, numbers, diagrams | graphic/action plan and render spec |
| Audio/Voice Expert | voice, singing, music, SFX, mix | audio plan, voice plan, event/cue sheet |
| Editing Expert | montage, pacing, transitions | edit decision list / timeline plan |
| Color/Post Expert | color matching, compositing, mastering | post-production plan |
| Independent Critics | fresh-context review | findings, severity, alternatives and recommendation |

Decision flow:
1. Director defines creative intent and bounded task contract.
2. Expert prepares specialist plan.
3. Independent Reviewer checks high-risk/important work.
4. Director reconciles findings and records choice/rationale.
5. Owner approves at required gates.
6. Orchestrator dispatches the approved work.
7. QC measures outputs; Director repairs within limits or escalates.

## 5.5 Engine specifications

### Editorial Intelligence
Discover/propose topics; score relevance, audience demand, originality, competition and docudrama potential; prepare differentiated story proposals; use analytics as evidence; Owner selects topic and approves direction.

### Historical Research & Evidence
Create a claim graph with claim wording, source, date/access date, reliability, corroboration, dispute, confidence and use. Separate fact/reasoned interpretation/hypothesis/dramatization. Validate chronology, geography, costumes, equipment, materials and social context. Produce a Historical Accuracy Report.

### Narrative & Script
Premise, story question, emotional arc, protagonists, stakes, turning points, chorus/climax and resolution. Store narration, dialogue, silent beats, speaker identity, emotion, pronunciation, timing needs, claims and dramatization status. Changes invalidate only downstream dependencies.

### Narration-to-Visual Bridge
Map each line/beat to direct evidence, place/date/name/number, object/prop, action, emotional association, contrast, map, diagram or intentional absence. Important lines need a visual reason; no unrelated filler. Every placed event shares the master timeline.

### World / Character / Asset
Character Bible, Environment Bible, wardrobe/prop states, appearance timelines, canonical references and approved assets. Store origin (archival/AI/artist/procedural), source, asset hash, model/settings, resolution, rights for final media, episode ownership and dependencies. Story-justified changes only.

### Cinematography & Shot Design
Coverage, shot size, angle, focal length, lens behavior, camera movement, framing, blocking, lighting, focus and exit transition. Duration follows story/performance/action. Preview composition and risky motion before expensive generation.

### Adaptive Visual Generation
Methods include Text-to-Video, Image-to-Video, hand-over-frame continuation, multi-reference identity conditioning, 2.5D, layered photo animation, Blender/3D, maps, procedural graphics, compositing and archival media. One capability interface per task; provider-specific code is an adapter. Preserve native and derived outputs. Fallback is explicit and QC'd.

### Photo Animation / 2.5D
Image inspection, segmentation, depth, layer/plane preparation, background reconstruction, camera path, motion isolation, lighting, atmosphere and compositing. Subjects/faces/hands/props stay rigid where required. Measure seams, masks, edge crop, face integrity, drift, camera jumps, frozen runs and artifacts. Blender and AI-assisted photo-to-video are selectable per shot.

### Maps / Motion Graphics / VFX
Maps, routes, timelines, statistics, diagrams, labels, counters, typography, source cards, particles, weather and compositing. Each element has narrative purpose, data provenance, geographic/time anchor, safe area and event timing.

### Audio, Voice & Character Performance
Voice casting/profile per narrator/character; controlled accent, pronunciation, pace, emotion and continuity. Canonical dialogue assets are separate from model-native speech unless explicitly approved. Visible singing has a performance plan, sustained vowels, face/mouth integrity and breath timing. Audio events specify ambience/Foley/music/SFX, silence-by-design, source distance, pan, level and transitions. Deliver stems, mix report and listening/QC artifacts.

### Master Timeline & Editing
Single canonical timebase (fps, frame count, sample rate, frame/sample conversion, shot spans, words, trims, visual/audio events, transitions and captions). Every stage records timing fingerprint. Editing plan defines cut points, J/L cuts, reaction tails, pacing, music arcs, visual rhythm, motif returns and montage. Important sequences may have alternative cuts. Render in chunks; never silently stretch/repeat missing clips.

### Multi-Layer QC & Recovery
Historical, narrative, visual/identity/continuity, motion, voice, audio, editing/rhythm, technical/export and media rights. Each gate returns PASS/FAIL/REVIEW/NOT_RUN with measurement, reason, hash and evaluator. Failures are classified, mapped to bounded repairs, rechecked and escalated when needed. Final assembled film is evaluated, not only component outputs.

### Operations / Model Intelligence / Compute
Model and Tool Registry holds capabilities, versions, limits, cost, speed, quality benchmarks, VRAM/runtime requirements, availability, compatibility and failure modes. New models require benchmark and regression. Worker Registry includes local and cloud. Preflight checks live GPU/VRAM, provider status, queue, price, network/storage, imports and model hashes. Owner approves resource/cost before launch. Parallelism respects dependency, rate limit, capacity, deadline, priority and budget.

### Data / Knowledge
Production Database for projects, episodes, scenes, shots, events, tasks, approvals, contracts, versions, costs and QC. Asset Storage for large media, model files, renders and export. Dependency Graph identifies downstream invalidation. Knowledge Base stores verified professional knowledge/lessons. Skill Registry stores reusable procedures/checklists. Model/Tool Registry stores benchmark and compatibility. Exact database/queue/object storage products remain benchmark decisions; no blanket JSON-to-database rewrite.

### Delivery / Publishing / Analytics
Package master video, platform variants, subtitles/captions, thumbnail, title, description, pinned comment, source/rights provenance, audio master, edit/timeline manifest, assets and QC report. Publish only with Owner approval. Analytics include impressions, CTR, watch time, retention, engagement, traffic and audience; analytics create hypotheses, not silent rule changes.

## 5.6 Core data entities

| Entity | Purpose |
|---|---|
| Project / Episode | owner, channel/look, language, target runtime, era, geography, policy and state |
| HistoricalClaim | claim wording, sources, status, confidence, dispute and intended use |
| Character / WorldAsset | canonical ID, appearance states, voice, provenance, hashes, versions and rights |
| Scene / Shot | story purpose, duration, characters/locations, camera, route, prompt/reference and director brief |
| VisualBridgeItem | narrative beat, visual purpose, device, evidence and frame/word anchor |
| AudioLine / AudioEvent | speaker, text, voice, performance, event ID, frame/sample span and asset |
| TimelineItem | frame/sample start/end, layer, source, transition and timing fingerprint |
| GenerationTask | capability, adapter/model, input hashes, settings, price/approval, attempts and output |
| QCReport | gate, verdict, measurement, severity, evidence, version and repair action |
| Approval / CostLedgerItem | approver, object hash, budget ceiling, estimate/reservation/actual |
| DecisionRecord | chosen option, alternatives, rationale, evidence, owner, date and revisit trigger |

---

# 6. Engineering Governance & AI Coding Protocol

Mandatory for every coding agent: Gemini, Claude, Argon or other. Provider-specific hooks may differ; the specification, task contract, tests and acceptance rules remain the same.

## 6.1 Selected methodology

**Spec-Driven Development + Contract-First + Vertical-Slice Implementation + Regression-First TDD + Independent Fresh-Context Review.**

~~~text
REQUIREMENT
  -> CURRENT-CODE / EVIDENCE INVESTIGATION
  -> WRITTEN SPECIFICATION
  -> DATA CONTRACT + ACCEPTANCE CRITERIA
  -> TESTS (RED)
  -> SMALLEST IMPLEMENTATION
  -> TESTS (GREEN)
  -> INDEPENDENT REVIEW
  -> INTEGRATION + REGRESSION
  -> DOCUMENTATION + ADR / PROGRESS
  -> MERGE
~~~

An agent must not start implementation from a vague request. It must know what changes, why, which files are in/out of scope, the contracts, tests, acceptance criteria and rollback.

## 6.2 Architecture and code rules

- Modular Monolith with Bounded Contexts first.
- Ports and Adapters for model/provider/GPU/storage/third-party integrations.
- Separate Workers/services only where measured isolation/scaling/deployment needs justify them.
- No circular imports or cross-module access to private implementation.
- Each module owns clear responsibility, contracts, tests and documentation.
- No generic utils dumping ground; shared abstraction needs real callers and a clear domain.
- No duplicated independent timing, budget, asset identity, approval or QC state.
- No abstraction for a trivial one-off; no direct provider coupling inside domain logic.
- Keep orchestration, creative decisions, provider adapters and rendering responsibilities separate.

## 6.3 Required Implementation Task Contract

1. **Goal** — observable result.
2. **Current State** — exact behavior and files inspected.
3. **Evidence** — tests, incidents, renders, traces or measurements.
4. **KEEP** — code/contracts/data that must remain.
5. **CHANGE** — exact behavior/files to change.
6. **DO NOT TOUCH** — scope boundaries.
7. **Contracts** — inputs, outputs, schemas and invariants.
8. **Dependencies** — upstream/downstream modules and invalidation impact.
9. **Implementation steps** — small ordered edits.
10. **Test plan** — focused red/green, integration and regression.
11. **Acceptance criteria** — measurable finish conditions.
12. **Cost/risk** — paid API/GPU/compute, migration and failure risks.
13. **Rollback** — restore known-good state.
14. **Evidence at finish** — diff, test outputs, reports, files and limitations.

If a material creative/architecture choice is unresolved, stop at the boundary and report evidence/options; do not invent the answer.

## 6.4 Agent roles and permissions

| Role | May do | Must not do |
|---|---|---|
| Architect/Planner | inspect code, trace dependencies, write spec/ADR/test plan | implement an architectural change before the plan is agreed |
| Implementer | edit assigned scope, add tests, run checks and report | broad refactor, weaken acceptance, silent policy changes |
| Independent Reviewer | fresh-context review of a defined diff/commit | modify the code under review |
| Test/QA Reviewer | run tests, inspect media, report measurements | claim visual quality from code tests alone |
| Main Orchestrator | allocate work, track dependencies/state and gather evidence | become a second creative Director |
| Main AI Director | make creative decisions in approved scope | change spend/security/release rules |
| Owner | approve required gates and conflicts | — |

Parallel work is allowed only on non-overlapping modules or files with stable contracts. Two agents must never concurrently edit the same source of truth.

## 6.5 Test strategy

- Regression-first for defects: reproduce with a failing test, fix the root cause, verify green.
- Contract/schema tests for persisted interchange.
- Unit tests for deterministic logic; fake clients and synthetic fixtures for APIs/media.
- Integration tests for connected engines.
- E2E tests for episode runner and delivery.
- Failure injection for stop/resume, corrupted files, stale hashes, provider loss and worker interruption.
- Visual/audio regression uses objective measures where meaningful plus human review. Model nondeterminism means pixel-identical comparison is not the only quality criterion.
- Real provider/GPU system tests are opt-in, priced, capped and Owner-approved.
- A NOT_RUN gate cannot count as full pass.

## 6.6 Python standards and Ruff

**Selected tool: Ruff** for Python linting and formatting. Official docs support ruff check, ruff format and configuration via pyproject.toml or ruff.toml:
- https://docs.astral.sh/ruff/linter/
- https://docs.astral.sh/ruff/formatter/
- https://docs.astral.sh/ruff/configuration/

Introduction plan:
1. Add one project Ruff config and pin the approved dev-tool version.
2. Start with a conservative, explicit rule set; do not enable every rule blindly.
3. Lint new/changed files first.
4. Format-check new/changed files first.
5. Establish a legacy baseline; do not reformat 511 source files in one mass diff.
6. Expand CI scope after baseline and exclusions are known.
7. Keep Pytest, schema, docs, palette and architecture-boundary checks as separate gates.

## 6.7 Git / PR discipline

~~~text
INTEGRATION BASELINE
  |-- task/bounded-change -> PR -> focused tests -> fresh review -> merge
  |-- task/bounded-change -> PR -> focused tests -> fresh review -> merge
  |-- task/vertical-slice -> PR -> E2E proof -> merge
~~~

- One agreed integration baseline; short-lived task branches.
- One PR = one clear change or one vertical slice.
- Inspect unique commits and base dependencies before merging.
- Never bulk-merge stacked PRs or close PRs based only on age.
- Add branch protection/required CI once repository permissions allow.
- No force-push without explicit backup and owner rules.
- Every merged feature updates tests, canonical docs/ADR and this master status.

## 6.8 Definition of Done

Behavior exists in the intended runtime; contracts/compatibility pass; focused and regression tests pass; fresh review is complete; media is inspected when affected; cost/failure/recovery behavior is tested; no unapproved spend/publishing occurred; docs/ADR/status match the code and evidence; limitations are explicit.

---

# 7. End-to-end Production Lifecycle

| Phase | Work | Owner | Gate / output |
|---|---|---|---|
| 1. Editorial Discovery | topic ideas, audience/competition, historical potential | Editorial Expert + Director | Owner approves topic/direction |
| 2. Historical Research | claims, sources, conflicts, era/geography | Historical Expert | dossier + uncertainty list |
| 3. Story Development | premise, variants, acts, emotional arc | Narrative Expert + Director | approved scenario |
| 4. Script | narration, dialogue, silent beats, claims, character lines | Script Expert | schema/history/narrative gates; Owner approval |
| 5. Visual Development | bridge, storyboard, scene/shot design, route | Director + Visual Experts | approved Production Blueprint |
| 6. Asset Preparation | character/world refs, wardrobe, props, map/music assets | Asset/World + Audio Experts | asset/provenance manifests |
| 7. Preview & Risk Review | layout, composition, low-cost motion, important variants | Director + QC | approved methods before expensive generation |
| 8. Final Generation | video, photo/2.5D, Blender, maps, graphics, VFX | Workers | generation record + per-shot QC |
| 9. Voice & Audio | voices, singing, ambience, music, SFX, stems | Audio Director | voice identity, timing, audio QC |
| 10. Editing | montage, pacing, transitions, overlays, color | Editing Director | Rough Cut review |
| 11. Final QC | historical, narrative, visual, audio, timing, technical, rights | independent reviewers + Director | full acceptance report |
| 12. Delivery | master, platform variants, subtitles, thumbnail, metadata | Delivery Engine | Owner approves package |
| 13. Publishing | staging, upload and verification | Publishing Engine | explicit Owner approval |
| 14. Learning | analytics and postmortem | Analytics + Knowledge Engine | validated improvement proposals |

---

# 8. Implementation Roadmap

**Rule:** prove an end-to-end result early. Do not build isolated engines for months and discover at the end that their contracts do not connect.

| Phase | Scope | Outcome / acceptance evidence | Status |
|---|---|---|---|
| 0 | Evidence audit, target architecture, branch/data reconciliation, risk register | This master plan, disposition, evidence and limitations | DONE WITH LIMITATIONS |
| 1 | Core contracts, Production State, IDs, versioning, timeline contract, dependency graph | schema compatibility, checkpoint/store tests, migration plan | NOT STARTED |
| 2 | Thin end-to-end vertical slice | approved script → one bridge item → one shot → preview → render → QC → short clip/master → review bundle | NOT STARTED |
| 3 | Main AI Director, Expert interfaces, Skill/Agent registry | decision trace, mock agents, permission and approval tests | NOT STARTED |
| 4 | Editorial, historical research, narrative and bridge | claim coverage, sourced dossier, story/visual approvals | NOT STARTED |
| 5 | Visual production unification | video/photo/2.5D/maps/graphics/optional Blender through adapters | NOT STARTED |
| 6 | Character identity, voice performance and full audio | canonical dialogue, singing/lip-sync, timing/mix QC | NOT STARTED |
| 7 | Master timeline, cinematic editing, color, subtitles/localization | Rough/Final Cut, frame/sample sync, subtitle/color QC | NOT STARTED |
| 8 | Local/Cloud compute, provider registry, scheduler, storage, budget, recovery | availability/cost checks, failure injection and resume without re-buy | NOT STARTED |
| 9 | Delivery, multi-platform exports, dashboard, publishing approvals | complete release package and owner-approved staging | NOT STARTED |
| 10 | Truce 1914 pilot validation | directly reviewed 6–8 minute film and acceptance report | NOT STARTED |
| 11 | Analytics/learning and scale to 8–12 minutes | validated improvements across episodes | NOT STARTED |

## 8.1 Phase work-package template

Every phase defines: objective and scope; current files/modules to KEEP; exact CHANGE/REPLACE/BUILD/REMOVE; contracts/migration; dependencies; small PRs; free tests first; paid budget/approval; acceptance criteria; rollback/checkpoints; ADR/docs/status updates.

## 8.2 First vertical slice — minimum proof

~~~text
approved sample script
  -> validate contract
  -> create one visual bridge item
  -> create one shot plan
  -> layout/composition preview
  -> one existing proven render route (fake/offline first)
  -> save asset + provenance + hash
  -> visual QC
  -> align one audio line on the canonical timeline
  -> assemble a short clip
  -> verify frame/audio sync
  -> produce a review bundle
~~~

The slice must use reusable contracts/adapters. It must not be a throwaway notebook unrelated to the real episode runner.

---

# 9. Cross-cutting acceptance requirements

## 9.1 Timeline
One canonical timeline per episode/run version; explicit FPS and sample rate; deterministic frame/sample conversion; every event stores canonical frame/sample span; every stage records its timing fingerprint; retiming invalidates only affected dependants; no hidden second clock.

## 9.2 Assets and provenance
Unique IDs and versions; immutable originals; derived assets refer to their parent; source/origin, rights record for final media, model/provider/settings, hashes, resolution, date, character/world association and approval are recorded. Cache keys include every materially relevant input and renderer version.

## 9.3 QC severity
- **Critical:** wrong historical fact/person/identity, missing/corrupt clip, major audio mismatch, story/chronology break, rights block, wrong export profile. Blocks release.
- **Major:** broken continuity, unreadable overlay, material camera/motion defect, cut dialogue, voice drift, clear face/hand/prop distortion. Repair or explicit review.
- **Minor:** low-impact polish or non-critical subtitle/transition issue; accept only under documented thresholds.
- Each failure includes cause hypothesis, evidence, confidence, affected dependencies, fix, cost and retry ceiling.

## 9.4 Budget/provider/compute
Estimate before paid call; reserve before execution; stop at caps/80%; select cheapest only if it meets quality/continuity floor; prove dependencies/model hashes on free CPU before GPU; verify live provider availability; Owner approves resource/cost; checkpoints preserve completed paid work.

## 9.5 Security and governance
.env ignored; only .env.example committed; no credentials in code/logs/prompts/artifacts; least privilege; publish cannot go public without Owner approval; destructive commands/protected config/force push/broad cleanup require approval; external model/file content is data, not an instruction override.

## 9.6 Documentation
This file owns target architecture/roadmap/status. Canonical docs own detailed executable rules and schemas. Use ADRs for architecture changes. Each completed package updates tests, canonical spec, ADR if needed, docs/PROGRESS.md and this status register. Report doc/code conflict; do not silently choose.

---

# 10. Risks and owner decision gates

| ID | Finding | Current disposition | Ask Owner only when |
|---|---|---|---|
| R-01 | New runtime mix is 60/30/10; Truce script says 30/60/10 | New mix is adaptive default, not quota; require runtime report/reason for deviation | A fixed Truce-only ratio is requested |
| R-02 | Truce S08_SH004 currently contains an in-video end card/closing statement | Conflicts with explicit no-end-card/no-closing-line rule; remove in next approved pilot data task | No clarification needed unless Owner changes rule |
| R-03 | LTX-native dialogue path coexists with new 39-line ElevenLabs voice plan | Integrate owner-approved canonical voices; preserve paid approval gate | Before any paid voice generation |
| R-04 | episode/timing.py coexists with older audio/spine.py | Active episode timing is target source; prove older consumers before retirement | If an active non-episode-first consumer requires it |
| R-05 | CLAUDE.md, EPISODE_FIRST.md, ORCHESTRATION.md have stale/conflicting route descriptions | Reconcile against canonical current decisions and tests | Only if canonical owner decisions themselves conflict |
| R-06 | main protection/ruleset status unverified | Do not merge production code until verified | GitHub admin/owner action if protection cannot be managed |
| R-07 | RunPod watchdog on main fails from missing RUNPOD_API_KEY; RunPod is legacy for v4.3 | Do not change secrets/disable workflow in Phase 0; decide if watchdog is needed for historical jobs | Before changing a secret or disabling a live watchdog |
| R-08 | 17 Draft PRs stacked across multiple bases | Preserve; reconcile unique commits one task at a time | If a unique change conflicts with approved target behavior |
| R-09 | Media binaries not directly reviewed in this audit | Reports are secondary evidence; full pilot requires direct viewing/listening | No architecture question; it is an acceptance test |
| R-10 | DB/queue/dashboard/object-storage products unselected | Keep interfaces independent; benchmark before locking technology | When benchmark shows materially different trade-offs |

### 10.1 Not selected yet (deliberately)

Concrete DB, queue/event broker, dashboard framework, object-storage vendor, provider adoption order, exact Ruff rules and deployment topology remain benchmark decisions. Do not ask the creator to choose popular products by name before there is a measured architectural need.

---

# 11. Phase 0 execution log

## 2026-11-16 — Phase 0 started
- Created a separate documentation branch from the active o239-argon-impl baseline.
- Created this master architecture/status document. No production source code changed.
- Repository, branch, PR and CI metadata inspected.
- Current runner, router, timing, sound, assembly, core contracts/store/ledger and governance inspected.
- Current Truce manifest/script, full-film shot plan, edit points, runbook, correction log, incident journal/audit and latest progress tail inspected.
- No paid API, GPU job or publishing executed.

## 2026-11-16 — Phase 0 findings
- Existing episode-first runner and contracts/ledger/checkpoint/timing/QC foundations are valuable. Preserve and extend.
- Current system is primarily a deterministic staged production pipeline with isolated generation workers; the future Main AI Director + Expert hierarchy must be added as a new orchestration layer.
- Active episode/timing.py is the best Master Timeline starting point.
- Recent owner decisions conflict with old Truce data in visual mix, LTX-native dialogue assumptions and S08 closing card.
- Documentation, branch integration and CI coding standards need reconciliation before broad architecture work.
- This audit did not independently view the HF media and did not execute tests; project reports are attributed as reports.

## Next actions
1. Review this master document on the dedicated documentation branch.
2. Finish final consistency and branch-diff review; create a reviewable PR to the active integration baseline.
3. Do not start code migration until Phase 1 has an accepted spec, contracts, tests and acceptance criteria.
4. Start Phase 1 with the smallest core/contract vertical slice, not a broad refactor.

---

# 12. Source register

## Repository and governance
- [Active baseline branch](https://github.com/vano1919/explainer-engine/tree/o239-argon-impl)
- [Default branch main](https://github.com/vano1919/explainer-engine/tree/main)
- [README](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/README.md)
- [CLAUDE.md](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/CLAUDE.md)
- [GEMINI.md](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/GEMINI.md)
- [Documentation index](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/INDEX.md)
- [Decision log](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/DECISIONS_AND_OPEN_QUESTIONS.md)
- [Orchestration rules](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/ORCHESTRATION.md)
- [Episode-first contract](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/EPISODE_FIRST.md)
- [Progress log](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/PROGRESS.md)
- [Model routing config](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/config/model_routing.json)
- [Agent governance tests](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/tests/unit/test_agent_governance.py)
- [Repository hygiene tests](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/tests/unit/test_repo_hygiene.py)
- [Vertical-slice tests](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/tests/unit/test_task2_step2b_vertical_slice.py)
- [Quality workflow](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/.github/workflows/quality.yml)
- [RunPod watchdog workflow](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/.github/workflows/watchdog.yml)
- [Watchdog run with missing key](https://github.com/vano1919/explainer-engine/actions/runs/43903635637)

## Runtime and core
- [Episode runner](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/episode/run.py)
- [Episode router](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/episode/router.py)
- [Episode timing](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/episode/timing.py)
- [Episode sound plan](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/episode/sound_plan.py)
- [Core contracts](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/core/contracts.py)
- [Core checkpoint store](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/core/store.py)
- [Core cost ledger](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/core/ledger.py)
- [Scene Director](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/production/living_director.py)
- [2.5D renderer](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/production/directed25d.py)
- [Chunked assembly](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/production/assemble.py)
- [Audio stems engine](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/audio/stems.py)
- [Legacy audio spine](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/audio/spine.py)
- [Visual bridge](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/production/visual_bridge.py)
- [Retired-era registry](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/config/retired_era.json)

## Truce 1914 evidence
- [Episode manifest](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/episode.json)
- [Production script](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/story/production_script.json)
- [Nov 15 full-film shot plan](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/planning/full_film_2026-11-15/SHOT_PLAN.md)
- [MAC runbook](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/planning/full_film_2026-11-15/MAC_RUNBOOK.md)
- [Correction log](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/planning/full_film_2026-11-15/CORRECTIONS_LOG.md)
- [Edit points](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/planning/full_film_2026-11-15/edit_points.json)
- [39-line voice specification](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/episodes/ep_truce_1914/audio/our_voices_spec.json)
- [Our voices plan/cache/cost guard](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/audio/our_voices.py)
- [Nov 15 incident audit](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/wip/argon_2026-11-14/INCIDENT_AUDIT_2026-11-15.md)
- [Argon incident journal](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/docs/wip/argon_2026-11-14/INCIDENT_JOURNAL_argon_loop.md)

## Visual identity and coding tools
- [Main visual reference](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/assets/style/main_style_5709.png)
- [World look configuration](https://github.com/vano1919/explainer-engine/blob/o239-argon-impl/explainer_engine/world/look_v2.json)
- [Ruff linter docs](https://docs.astral.sh/ruff/linter/)
- [Ruff formatter docs](https://docs.astral.sh/ruff/formatter/)
- [Ruff configuration docs](https://docs.astral.sh/ruff/configuration/)
