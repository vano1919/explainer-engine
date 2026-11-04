# Rule Conflicts and Migration Register

**Status:** all target changes are planning proposals until Opus finishes the plan and the creator approves implementation.  
**Rule:** never silently break a current rule. Record the affected canonical ID, code, schema, validator, test, agent/skill and downstream consumer.

## 1. Conflict matrix

| Existing rule / area | CURRENT | NEW TARGET | KEEP | CHANGE / REMOVE | Required action |
|---|---|---|---|---|---|
| `CLAUDE.md` project description | 2D hand-drawn / raster-first visual production | 3D geometry rendered as Ink Chronicle illustrated imagery | Safety, spend, approvals, source-of-truth and test-governance safeguards | Replace branch-local visual mission and update the canonical base instruction only after approval | TODO-RULE-01 |
| D-27 — painted raster look | Reusable raster kit and images are the visual source; 3D method untested | Reusable 3D world, characters and props; shared NPR style/render system | One visual universe; stable approved identity; reusable character/prop anchors | Replace raster-only production method; preserve selected visual identity principles only if they map to Ink Chronicle | TODO-RULE-02 |
| D-28 — tool strategy | Gemini kit + image/video generation + code animation | Blender scene builder and renderer; AI may assist with optional asset creation, not final frame generation | Cost caps, paid-asset approval, reusable asset-first discipline | Retire Gemini/LTX as required visual frame/video path | TODO-RULE-03 |
| D-30 — resolution | Design for 2560×1440 master with 1080p fallback; exact final gate still benchmarked | 2560×1440, 24 fps as target master | Resolution and fps intent | Clarify terminology as 1440p/QHD; re-benchmark render profile and fallback | TODO-RULE-04 |
| D-31 — compute | Cloud-first with RunPod GPU pods | Compare M4 Pro local, Vast.ai marketplace, RunPod Community/Secure and SheepIt; route per measured cost/reliability | Spend caps, ledger, itemized plan, no idle paid pods | Cloud-first may no longer be cheapest; choose based on measured cost per accepted frame and recovery time | TODO-RULE-05 |
| D-32 — renderer | Existing deterministic GPU layer compositor is central visual renderer; Remotion is demoted | Blender scene/render owns 3D final imagery; existing compositor/FFmpeg remains for appropriate assembly and audio | Python orchestration, FFmpeg audio/mux, deterministic compositing where useful | Reassign or retire raster-only final-frame responsibilities only after caller audit | TODO-RULE-06 |
| Blueprint card A2 / D-89 route | Blender 3D blocking / LivePortrait / MuseTalk not included in v2; `DRAMA_BLOCKED_3D` refused | Blender is the intended visual scene/render system | No unnecessary permanent hosts; do not introduce LivePortrait/MuseTalk without an independent reason | Remove the blanket Blender-blocked route after schema, routing and tests are rewritten | TODO-RULE-07 |
| D-87 — map ceiling | 2D vector maps + 2.5D parallax, no relief / no Blender pass | 2D deterministic maps by default; Blender 3D terrain only when elevation materially affects the explanation | Data accuracy, faction identity, accessibility and deterministic labels | Lift the absolute ban on 3D terrain; do not make every map 3D | TODO-RULE-08 |
| D-93 — 60/30/10 | 60% LTX video, 30% Python-moved stills, 10% Python helpers; by runtime | 60% Blender-animated VIDEO, 30% Blender-created STILL/tableaux with efficient motion, 10% HELPER data scenes rendered in the shared look | Runtime measurement, ±5pp tolerance, one separate visual lane report | Rewrite lane execution semantics and router contracts; do not change the percentages | TODO-RULE-09 |
| D-95 — 75/25 midpoint | Narrator 70–80%, dialogue 20–30%, midpoint 75/25; 5s visible dialogue target; 10–15s non-dialogue action planning | Narrator 70%, dialogue 30% target by audible words | Outer bands, voiced:false exclusion, independent word/visual ratios, 5s lip-sync target, non-dialogue action duration logic | Change midpoint to 70/30 in decision log, rule registry, variant planner, story/shot validators, agent/skill docs and tests | TODO-RULE-10 |
| D-78 / D-80 — Qwen keyframes | Fresh Qwen image keyframes and LTX video generation are primary animated route | Blender scene and reusable 3D assets generate final visual frames | Approved identity/reference discipline and asset reuse | Replace Qwen keyframes/LTX clips as required final-image path; assess whether image models remain useful for concept/asset references only | TODO-RULE-11 |
| D-85 / D-92 — frame clock | 24 fps episode clock | 24 fps Blender and FFmpeg delivery | KEEP | No change unless a measured compatibility issue exists | KEEP-RULE-01 |
| D-70 / World Bible / Asset Library | Versioned visual bible and reusable asset register | Same governance, extended to 3D assets, rigs, animations, materials and collections | KEEP versioning, provenance, license and approval | Extend schema and library indexing; do not create a second asset database | TODO-RULE-12 |
| D-84 and repository safeguards | Single model-routing config, hooks, read-only critics, test governance | Same safety/governance for the new plan and later code | KEEP | No change in this planning phase | KEEP-RULE-02 |

## 2. Critical distinction: allowed plan vs. approved implementation

The creator has requested an Ink Chronicle / Blender-based target architecture and the Opus planning branch. That authorizes this design work. It does **not** mean every technical detail is finalized or that old canonical rules can be edited silently.

Classify each proposed change:
- `CREATOR-SET TARGET`: Ink Chronicle, 10/30/60 visual runtime, 70/30 spoken-word target, 1440p/24fps master, $10–15 budget objective.
- `PROPOSED TECHNICAL CHOICE`: EEVEE as primary candidate, class/module names, scene builder design, render provider selection, exact resolution scaling, caching details.
- `HYPOTHESIS / NEEDS BENCHMARK`: seconds/frame, GPU-hour predictions, upscale quality, asset-authoring time savings, SheepIt suitability, M4 Pro throughput.
- `LEGACY / NOT AUTHORITATIVE`: contradictory raster-only/LTX-only instructions and imported Master Mold TODOs outside the approved scope.

## 3. Canonical rules that must be rewritten before implementation

Opus must deliver a synchronized edit list covering:
1. `docs/DECISIONS_AND_OPEN_QUESTIONS.md`: add/amend the new visual architecture and update D-95 midpoint.
2. `docs/SOURCED_RULES.md`: revise or supersede the lane implementation rules; retain sourced evidence and distinguish new hypotheses.
3. `explainer_engine/standards/sourced_rules.py` or current authoritative registry: synchronize IDs/values; never duplicate values by hand.
4. `scripting/film_shots.py`, `variant_plan.py`, validators and rule tests: route visual lane semantics and 70/30 speech accounting.
5. `docs/CONTRACTS.md` and schemas: new Blender render/scene artifacts only where needed; version contracts and maintain old job readability.
6. `.claude/agents/*`, skills, procedures and handoff instructions: remove the old LTX-as-required-renderer assumptions and describe Blender roles.
7. `docs/PRODUCTION_RULES.md`, `docs/RENDERING_ARCHITECTURE.md`, `docs/WORLD_BIBLE.md`, `docs/COST_AND_TIME_MODEL.md`: align one consistent pipeline and cost model.
8. Tests and fixtures: lane runtime, speech word share, route validity, 24fps, Blender render manifest, cache invalidation, output validation and spend cap.

Do not edit all files mechanically. Trace each canonical rule to its actual runtime reader and tests. Update the canonical home, then derived summaries.

## 4. Preserve vs. replace

### Keep
- claim/research discipline and script approval;
- story and scene intent;
- current audio voice, spine, sound and mix system;
- one episode clock at 24 fps;
- versioned JSON contracts and strict validation;
- ledger, spend caps, RunPod safety, no surprise spend;
- frame review, identity/continuity QA, review bundle and creator approval;
- reusable world bible / asset provenance concept;
- FFmpeg where it handles concatenation, muxing, audio and delivery correctly.

### Change
- lane render path and shot router;
- current LTX/keyframe-specific renderer specs;
- visual style contract and supported asset formats;
- maps/HUD/tableau renderer boundary;
- render profile, cache and provider backend;
- visual QA for NPR line stability, flicker, geometry, missing frames and image consistency;
- spoken-word target midpoint to 70/30.

### Remove only after proof
- LTX as mandatory final visual renderer;
- stale keyframe/video routes and their code paths if no downstream caller remains;
- unsupported duplicate renderers or old raster-only production branches;
- obsolete injected TODO annotations after independent audit.

Do not delete the old research documents, decision history or working code during this planning branch.

## 5. Migration safety

- Do not create a second source of truth for lane shares, speech ratio, frame rate, budget or model/provider settings.
- Keep old episode/job schemas readable; propose a versioned migration or adapter.
- Cache keys must include scene, asset, World Bible, renderer version, engine, profile and output-affecting settings.
- A route must fail clearly when required Blender binary, scene asset, rig or style profile is missing; no silent fallback to a different visual universe.
- Roll back one lane at a time if the visual acceptance gate fails.
