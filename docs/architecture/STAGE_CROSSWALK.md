# Stage Crosswalk: Episode Runner vs. Skill Registry vs. Skill Index

Authoritative mapping across the three stage vocabularies in `explainer-engine`:

1. **Episode Runner (8 stages)** — `explainer_engine/episode/run.py` (`STAGES`): the current working draft production runner (`python -m explainer_engine.episode run <episode> --to qa`).
2. **Skill Registry (10 stages)** — `explainer_engine/orchestration/skill_registry.json`: operational stage contracts with explicit `execution_category` (`episode_stage`, `route_worker`, `conditional_worker`, `human_gate`, `planning_only`, `not_implemented`).
3. **Skill Index (19 stages)** — `.claude/skills/INDEX.md`: editorial/craft skill taxonomy (`S1`..`S19`) pairing pinned vendored `v-*` skills with channel overlays.

## Unified Crosswalk Table

| Episode Runner (`episode/run.py`) | Skill Registry (`skill_registry.json`) | Execution Category | Skill Index (`.claude/skills/INDEX.md`) | Current Implementation Status |
| :--- | :--- | :--- | :--- | :--- |
| `script` | `S1_research` | `episode_stage` | `S1 research and claims` | Implemented via `scripting.claim_ledger`, `scripting.claims` |
| `script` | `S2_story_and_script` | `episode_stage` | `S2 story structure`, `S3 narration and hook` | Implemented (`story_lint`, `stage_guard`); `beat_level_bridge_selector_automation` gap tracked |
| `sound_plan` | `S3_film_direction` | `episode_stage` | `S4 director's book, shot list`, `S5 shot prompts`, `S6 storyboards, consistency` | Implemented (`episode_film`, `production.build_shot`, `episode.sound_plan`) |
| `pictures` (optional previs) | `S4_blender_previs` | `conditional_worker` | `S6 storyboards, consistency` | Implemented spec validation (`lab.scene_spec.check_schema` / `validate_spec`); Blender render requires local `bpy` |
| `pictures` | `S5_gemini_images` | `agent_browser_gate` | `S7 pictures` | Agent-driven browser Gemini turn packs + verified image decode/dimension/SHA-256 provenance (`unattended_chat_interface_bridge` gap tracked) |
| `clips` | `S6_ltx_video` | `route_worker` | `S8 character acting`, `S9 video clips (D-132)` | Modal LTX-2.5 (`MODAL1`) worker + strict `video_clip_record/1` (`PASS` + SHA-256) ingestion; paid GPU launch requires explicit owner approval |
| `clips` | `S7_maps_and_25d` | `conditional_worker` | `S10 2.5D and maps (D-131)` | Implemented (`maps.maplibre_spec`, `production.build_map_shot`, `fx25d.living`, `core.camera_vocab`) |
| `voice`, `sound` | `S8_audio_and_sound` | `episode_stage` | `S11 voice`, `S12 word timing`, `S13 sound design and mix` | Implemented (`audio.level`, `audio.layers`, `audio.val_stem_levels`); ElevenLabs live TTS requires credentials & ledger |
| `assemble` | `S9_edit_and_render` | `episode_stage` | `S14 edit and assembly`, `S15 colour and finish` | Implemented (`production.build_episode`, `finish.esrgan_cpu`, FFmpeg `-fps_mode passthrough`) |
| `qa` | `S10_qa_and_delivery` | `route_worker` | `S16 technical QA`, `S17 perceptual QA` | Implemented 3-layer QA (`qa.technical_gate`, `qa.perceptual_qa`, `qa.delivery_gate`); `creator_signoff_status` always starts `PENDING` |
| *(post-QA delivery)* | *(outside core runner)* | `human_gate` | `S18 subtitles and thumbnail`, `S19 Shorts` | Manual / post-approval packaging; nothing uploads publicly without creator approval |

## Portable Agent Skills (`.agents/skills/`)

Cross-agent operational skills live under `.agents/skills/*/SKILL.md` and are validated by `python -m explainer_engine.governance.agent_skills_lint`:

- `explainer-architecture`
- `multimodal-qa-review`
- `spending-and-approvals`
- `prompt-evaluation`
- `security-and-workflows`
- `ltx-cinematography`
- `youtube-docudrama-editing`
- `film-style-bible`
