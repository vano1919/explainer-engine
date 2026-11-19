---
name: film-direction
description: Router for the picture, clip, sound, edit, grade, QA and packaging stages S4-S18 of an episode. Names the vendored public skill to load per stage, what NOT to call, and the validator that checks the result. Use before shot lists, prompts, clips, mixes, cuts, grades and QA.
---

# Film direction: which vendored skill for which stage

The upstream skills are copied whole into the `v-*` folders (pins and licences: `docs/VENDORED_SKILLS.md`). This page holds
only our rules: when to load which, what never to call, and which code checks the result (P-1, P-2, P-4). Numbers live in
validators, not here. The stage map is `.claude/skills/INDEX.md`; the old per-topic skills are in `_archive/` and their
rule ids are mapped in `docs/SKILL_RULE_MAP.md`.

**Never call from any vendored text:** Scenario MCP or API, HeyGen, Atlas, any usage beacon or account sign-in, any
paid provider that is not in the creator's approved plan. Paid steps need the OR-23 plan and his word (CLAUDE.md). Where
a vendored skill proposes a paid tool, use ours as named below. Upstream sound advice that says licences are only
warned about is overridden by our rule: reject only YouTube-blockable sources (the BBC RemArc set), keep the rest.

| Stage | Load | Do not call / use instead | Validator (W2 owns the modules) |
|---|---|---|---|
| S4 director's book, shot list | `v-director-cinematic` (modes, coverage, failure taxonomy F1-F19 as defect words) | its model adapters for paid tools; use our routes (`episode/router`) | `validators/shots.py`; cards `shot-continuity-writer` (CT-01..14) |
| S5 image and motion prompts | `v-visual-skills-image`, `v-visual-skills-video` (CC-BY, credit kept) | Seedance/Kling/Veo prompts are method only; our video is LTX on Modal (D-132) | `validators/prompts.py`; `world/resolver` (UR-22..27) |
| S6 storyboards, consistency | `v-scenario-storyboards`, `v-scenario-consistency` (method text only) | Scenario tools; use `imagegen/turn_pack.py` | `validators/prompts.py` |
| S7 pictures | Gemini chat turn packs (no vendored skill) | any paid image call before the creator's word | `validators/pictures.py`; `imagegen/vault.py` (W3) |
| S8 character acting | `v-animate-characters` | Blender/rig steps (retired) | `validators/clips.py` |
| S9 video clips (D-132) | `v-ltxv2-video` (settings, traps) | ComfyUI launch; use `training/pods/ltx/scene_run` on Modal | `validators/clips.py` |
| S13 sound design, mix | `v-design-sound`, `v-audio-production-skill` | its web fetching of sounds without the library-first record (OR-18) | `validators/mix.py`; `audio/layers.py`, `audio/duck.py` |
| S14 edit, assembly | `v-ffmpeg-skill`, `v-video-editing-skill`, `v-edit-video` | other render paths: render only via `episode/run.py` (P-8) | `validators/edit.py` |
| S15 colour | `v-scenario-video-color-grade` (method), `v-color-grading-skill` | Scenario tools; grade once on the master | `validators/color.py`; `finish/grade.py` |
| S16 technical QA | `v-qc-skill`, `v-media-analysis-skill`, `v-scenario-quality-gate` (discipline only) | none paid | `validators/tech_qa.py` |
| S17 perceptual QA | `v-director-cinematic` failure taxonomy as vocabulary | none | `validators/observe.py`; `qa/observe.py` (W4) |
| S18 subtitles, thumbnail | `v-subtitle-skill`, `v-thumbnail-skill` | the thumbnail's content is the creator's choice | `validators/subtitles.py`, `validators/thumbnail.py` |
| Dev process | `v-superpowers-test-driven-development`, `-systematic-debugging`, `-verification-before-completion`, `-subagent-driven-development` | none | CI and focused tests (invariant 11) |

Rule: a skill gives judgement and vocabulary; any number, count, time or yes/no check is a validator with a test (SK-2).
