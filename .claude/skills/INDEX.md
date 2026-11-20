# Skill index: stage to skills (W1, P-1)

One line per stage. Load the vendored `v-*` skill for the method and our overlay for the channel's rules; any number or
yes/no check is a validator (`explainer_engine/validators/<stage>.py`, W2), never skill text (P-4). Pins and licences:
[docs/VENDORED_SKILLS.md](../../docs/VENDORED_SKILLS.md). Old rule ids: [docs/SKILL_RULE_MAP.md](../../docs/SKILL_RULE_MAP.md).
Archived (not loaded): `_archive/` holds `video-editing-architect`, `shot-visuals`, `animation-principles`, `animated-universe`, `editing-style`, `lora-training`.

| Stage | Load (vendored) | Overlay (ours) |
|---|---|---|
| S1 research and claims | `v-newsjack-fact-check`, `v-source-verification`, `v-fact-check-workflow` | `science-grounding` (W8 phase B pointer) |
| S2 story structure | `v-sw-story-structure` (+ `reference.md`), `v-sw-premise-theme`, `v-sw-workflow`, `v-sw-dialogue`, `v-sw-scene-craft` | `story-engine`, `dialogue-scenes`, `time-jump-episode`, `crossover-episode` (W8 phase B pointers) |
| S3 narration and hook | `v-viral-hooks`, `v-hook-writing` | `narration-script` (W8 phase B pointer) |
| S4 director's book, shot list | `v-director-cinematic` | `film-direction`, `visual-beats` |
| S5 shot prompts | `v-visual-skills-image`, `v-visual-skills-video` | `film-direction` |
| S6 storyboards, consistency | `v-scenario-storyboards`, `v-scenario-consistency` | `film-direction` |
| S7 pictures | none (Gemini chat turn packs) | `film-direction` |
| S8 character acting | `v-animate-characters` | `film-direction` |
| S9 video clips (D-132) | `v-ltxv2-video` | `film-direction` |
| S10 2.5D and maps (D-131) | none | `cartography` |
| S11 voice | `v-elevenlabs-text-to-speech`, `v-elevenlabs-speech-to-text`, `v-elevenlabs-sound-effects`, `v-elevenlabs-music` | `elevenlabs-voice`, `voice-search` |
| S12 word timing | `v-transcription-skill`, `v-elevenlabs-speech-to-text` | `elevenlabs-voice` |
| S13 sound design and mix | `v-design-sound`, `v-audio-production-skill` | `film-direction` |
| S14 edit and assembly | `v-ffmpeg-skill`, `v-video-editing-skill`, `v-edit-video` | `film-direction` |
| S15 colour and finish | `v-scenario-video-color-grade`, `v-color-grading-skill` | `film-direction` |
| S16 technical QA | `v-qc-skill`, `v-media-analysis-skill`, `v-scenario-quality-gate` | `film-direction` |
| S17 perceptual QA | `v-director-cinematic` (failure taxonomy) | `film-direction` |
| S18 subtitles and thumbnail | `v-subtitle-skill`, `v-thumbnail-skill` | `film-direction` |
| S19 Shorts | `v-viral-youtube-shorts` | `shorts-for-video` |
| Dev process, every code thread | `v-superpowers-test-driven-development`, `v-superpowers-systematic-debugging`, `v-superpowers-verification-before-completion`, `v-superpowers-subagent-driven-development` | CLAUDE.md invariants |

Cloud and cost skills (`cloud-cost-audit`, `cloud-provider-selection`, `hyperstack-operations`, `modal-operations`) are not part of the film stages and stay as they are.
