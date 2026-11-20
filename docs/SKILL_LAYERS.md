# Skill layers and the SKR-50 report (the owner's "RW-50" rule) (2026-11-20)

Canonical home of the SKR rules (the rewrite rule the owner and the code call RW-50). The layer list L1-L33 and the ten groups come from the skills team plan
(`SKILLS_TEAM_PLAN_2026-11-20.md` and `SKILLS_REWRITE_50_BRIEF.md` in the project files); which skill, overlay and tool
skill serves each layer is the router `.claude/skills/film-direction/SKILL.md`. A layer is decided only when its record
passes the layer gate (team plan MS-6); everything below is the state of the skill texts, not a layer decision.

| ID | Rule | Checked by |
|---|---|---|
| SKR-50 | The share of new instruction text per loaded skill, against the baseline commit of 2026-11-20 (`5e6dc41`), is measured in code and reported for information. The owner's 06:52 UTC rule asked for at least 50 %; his 07:14 UTC follow-up made the mandatory steps MS-1..MS-7 the rule and the share a report, not a target. | `explainer_engine/governance/skill_rewrite.py`, `tests/unit/test_skill_rewrite.py` |
| SKR-51 | A vendored public skill keeps its upstream `SKILL.md` whole and byte-pinned; our rules for it live in `OVERLAY.md` in the same folder, which starts with "# Overlay" and wins where it differs. Public text is never paraphrased into our words (team plan rule 4). | `tools/vendor_skill.py verify`, `tests/unit/test_skill_rewrite.py`, `tests/unit/test_vendored_skills.py` |
| SKR-52 | Every tool the pipeline calls has its own skill (`tool-*` or a tool page among the vendored skills), naming how to call it, its settings, traps, cost and the check of its output. | `tests/unit/test_agent_governance.py` (names exist) |

## Status of every loaded skill (2026-11-20)

Overlays and `tool-*` skills are drafts for their group's MS-5 step. Regenerate this table with
`python -m explainer_engine.governance.skill_rewrite`.

| skill | kind | measured file | new text share |
|---|---|---|---|
| `cartography` | ours | SKILL.md | 68% |
| `cloud-cost-audit` | ours | SKILL.md | 89% |
| `cloud-provider-selection` | ours | SKILL.md | 91% |
| `crossover-episode` | ours | SKILL.md | 93% |
| `dialogue-scenes` | ours | SKILL.md | 93% |
| `elevenlabs-voice` | ours | SKILL.md | 64% |
| `film-direction` | ours | SKILL.md | 86% |
| `hyperstack-operations` | ours | SKILL.md | 90% |
| `modal-operations` | ours | SKILL.md | 92% |
| `narration-script` | ours | SKILL.md | 73% |
| `science-grounding` | ours | SKILL.md | 89% |
| `shorts-for-video` | ours | SKILL.md | 80% |
| `story-engine` | ours | SKILL.md | 96% |
| `time-jump-episode` | ours | SKILL.md | 83% |
| `tool-blender-layout` | new | SKILL.md | 100% |
| `tool-gemini-task-pictures` | new | SKILL.md | 100% |
| `tool-hf-vault` | new | SKILL.md | 100% |
| `tool-upscale` | new | SKILL.md | 100% |
| `tool-vidiq-metadata` | new | SKILL.md | 100% |
| `tool-vision-qa` | new | SKILL.md | 100% |
| `tool-youtube-upload` | new | SKILL.md | 100% |
| `v-animate-characters` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-audio-production-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-color-grading-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-design-sound` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-director-cinematic` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-edit-video` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-elevenlabs-music` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-elevenlabs-sound-effects` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-elevenlabs-speech-to-text` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-elevenlabs-text-to-speech` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-fact-check-workflow` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-ffmpeg-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-hook-writing` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-ltxv2-video` | vendored (upstream SKILL.md + our OVERLAY.md; D-132) | OVERLAY.md | 100% |
| `v-media-analysis-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-newsjack-fact-check` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-qc-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-scenario-consistency` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-scenario-quality-gate` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-scenario-storyboards` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-scenario-video-color-grade` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-source-verification` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-subtitle-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-superpowers-subagent-driven-development` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-superpowers-systematic-debugging` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-superpowers-test-driven-development` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-superpowers-verification-before-completion` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-sw-dialogue` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-sw-premise-theme` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-sw-scene-craft` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-sw-story-structure` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-sw-workflow` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-thumbnail-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-transcription-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-video-editing-skill` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-viral-hooks` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-viral-youtube-shorts` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-visual-skills-image` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `v-visual-skills-video` | vendored (upstream SKILL.md + our OVERLAY.md) | OVERLAY.md | 100% |
| `visual-beats` | ours | SKILL.md | 93% |
| `voice-search` | ours | SKILL.md | 88% |
