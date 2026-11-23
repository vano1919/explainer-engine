---
name: film-direction
description: Router for every production layer of a docudrama episode (L1-L33, the ten groups of the 2026-11-20 skills team plan) - which skill to load for the judgement, which OVERLAY.md holds our rules on top of a vendored public skill, which tool skill operates the tool, what never to call, and which code checks the result. Use before any script, picture, clip, sound, edit, grade, QA, packaging or cloud step, and whenever two skills seem to fire at once.
---

# Film direction: the layer router

Rewritten 2026-11-20 under RW-50 and the skills team plan (`SKILLS_TEAM_PLAN_2026-11-20.md` in the project files): public
skills are copied whole into the `v-*` folders (pins and licences: `docs/VENDORED_SKILLS.md`, checked by
`tools/vendor_skill.py verify`); **our rules for each of them live in that folder's `OVERLAY.md`** and win where they
differ from the upstream text. Overlays and the `tool-*` skills are drafts until their group's layer record passes the layer
gate (MS-6, `explainer_engine/governance/layer_gate.py` (planned, W2)). Numbers live in validators and the sourced-rules
registry, never only in a skill (SK-2).

**How to use a row:** load the skill named first, then read the overlay and the tool skill named after it. A vendored
skill's own description and examples are upstream's; whatever its text proposes (a paid tool, a platform, another model),
our overlay decides.

**Never call from any vendored text:** Scenario MCP or API, HeyGen, Atlas, Kling, Veo, Seedance, Runway, any usage beacon or
account sign-in, any paid provider outside the owner's approved plan. Every paid step needs its plan, the audit gate and the
owner's word (CLAUDE.md invariants 1-2).

## Group 1: picture and world

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L9 picture prompts | `v-visual-skills-image` | its `OVERLAY.md`; skill `tool-gemini-task-pictures` (Task mode, batches of 6, the film named) | `imagegen/turn_pack.py` intake, GC rules |
| L10 storyboard, consistency | `v-scenario-storyboards`, `v-scenario-consistency` | their overlays (method only, no Scenario calls) | `scripting/continuity.py` (CT-01..CT-14) |
| L11 layout, photo on geometry | skill `tool-blender-layout` | previs only, never final characters | owner's look, layer record |
| L16 upscale | skill `tool-upscale` | free first; paid 2K only for a failing close-up hero shot | `finish/superres.py` quality rows |

## Group 2: motion and video

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L12 acting, motion prompts | `v-animate-characters`, `v-visual-skills-video` | overlays; one action, one camera, one line (D-132) | video lane composer |
| L13 video generation | `v-ltxv2-video` | overlay; skill `modal-operations` for money and launch | `videolane/` ingest and master QA (D-137) |
| L14 still_25d (D-131) | `v-director-cinematic` (route choice) | `production/layers25d.py`; S10 trial report in the project files | layers25d report rows |

## Group 3: maps and data

| L15 maps, counters | skill `cartography` | made last; front lines illustrative unless a verified open dataset | `maps/` render and map laws (CMP) |
|---|---|---|---|

## Group 4: story and direction

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L1 research, facts | skill `science-grounding` | `v-fact-check-workflow`, `v-newsjack-fact-check`, `v-source-verification` with overlays | `scripting/claims.py` (PV-37) |
| L2 story | skill `story-engine` | `v-sw-premise-theme`, `v-sw-story-structure`, `v-sw-workflow` overlays | `scripting/story_lint.py` |
| L3 dialogue | skill `dialogue-scenes` | `v-sw-scene-craft`, `v-sw-dialogue` overlays | scene lint (SC rules) |
| L7 director's book | `v-director-cinematic` | overlay (docudrama grammar, repair ladder R1-R4) | `episode/router.py` |
| L8 continuity | stage page `shot-continuity-writer` | CT cards | `scripting/continuity.py` |
| L29 rights | skill `crossover-episode` | RR rules | `rights/ip_check.py` |
| L30 episode format | skill `time-jump-episode`, skill `crossover-episode` | | story lint |

## Group 5: voice

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L4 narration | skill `narration-script` | `v-hook-writing`, `v-viral-hooks` overlays | `scripting/narration_lint.py` |
| L5 performance | skill `elevenlabs-voice` | `v-elevenlabs-text-to-speech` overlay | `audio/voice_check.py` |
| L6 casting | skill `voice-search` | stage page `voice-caster` | `audio/casting.py` |
| L17 word timing | `v-elevenlabs-speech-to-text`, `v-transcription-skill` | overlays | `audio/scribe_words.py` coverage |

## Group 6: sound

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L18 effects, foley | `v-design-sound`, `v-elevenlabs-sound-effects` | overlays; one bed per place, 3+ effects a scene, library first | `episode/events.py` (AV contract, D-135) |
| L19 music | `v-elevenlabs-music` | overlay | `assets_reuse.py` record |
| L20 mix | `v-audio-production-skill` | overlay; one level everywhere | `audio/stems.py`, `qa/targets.py` |

## Group 7: edit and finish

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L21 edit, assembly | `v-edit-video`, `v-video-editing-skill`, `v-ffmpeg-skill` | overlays; render only through `episode/run.py` | `production/assemble.py` chunks |
| L22 colour | `v-scenario-video-color-grade`, `v-color-grading-skill` | overlays; grade once on the master | `finish/grade.py` |
| L25 subtitles | `v-subtitle-skill` | overlay | caption checks |

## Group 8: QA

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L23 technical QA | `v-qc-skill`, `v-media-analysis-skill` | overlays | `videolane/master_qa.py`, G10 acceptance |
| L24 perceptual QA | `v-scenario-quality-gate` | overlay; skill `tool-vision-qa` | `qa/visual_judge.py`, `qa/look_and_listen.py` |

## Group 9: packaging

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L26 thumbnail | `v-thumbnail-skill` | overlay (our material only) | TN rules |
| L27 title, SEO | skill `tool-vidiq-metadata` | credits asked first | `qa/publish_check.py` |
| L28 Shorts | skill `shorts-for-video` | `v-viral-youtube-shorts` overlay | `qa/short_format.py` |
| L32 upload | skill `tool-youtube-upload` | unlisted or private only (D-57) | `publish/stage.py` |

## Group 10: infrastructure and dev process

| Layer | Load | Our rules and the tool | Check |
|---|---|---|---|
| L31 cloud, cost | skill `modal-operations` | skill `cloud-cost-audit`, skill `cloud-provider-selection`; HF storage skill `tool-hf-vault` | `cloud/paid_offer.py` (CH-07), ledger |
| L33 dev process | `v-superpowers-test-driven-development`, `v-superpowers-systematic-debugging`, `v-superpowers-verification-before-completion`, `v-superpowers-subagent-driven-development` | overlays | focused tests, docs lint |

Legacy: Hyperstack (skill `hyperstack-operations`, read-only), RunPod and the retired Blender render route (D-131,
`config/retired_era.json`) are not routed for a v4.3 episode.
