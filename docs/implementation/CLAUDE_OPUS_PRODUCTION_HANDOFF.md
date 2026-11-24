# Claude Opus Production Handoff Guide

Authoritative operational manual for **Claude Opus** acting as the primary creative and production orchestrator of `vano1919/explainer-engine`.

## 1. Division of Responsibilities

- **Claude Opus (Creative & Production Orchestrator):** Research interpretation, premise/scenario writing, dialogue scenes, character bibles, director's book, shot lists, photo-grounded creative prompts, candidate render selection, visual/audio critique, and iterative revision.
- **Deterministic Python Framework (Governance & Execution):** Typed contracts, stage ordering, SHA-256 artifact fingerprints, upstream invalidation, spend ledger (`spend_ledger.py`), 64-char SHA-256 owner approvals (`approvals.py`), rendering (MapLibre, 2.5D, HyperFrames, FFmpeg, LTX adapters), and 3-layer QA (`perceptual_qa.py`, `technical_gate.py`, `identity_lock.py`).
- **Hard Rule:** Claude Opus can NEVER mark a mandatory stage complete by natural-language claim; `ProductionStateMachine` (`explainer_engine/core/execution_gateway.py`) verifies on-disk files and SHA-256 hashes before accepting any stage.

## 2. Skills & Agents to Load

1. Operational skills (`.agents/skills/*/SKILL.md`, validated by `python -m explainer_engine.governance.agent_skills_lint`):
   - `explainer-architecture`
   - `spending-and-approvals`
   - `security-and-workflows`
   - `film-style-bible`
   - `ltx-cinematography`
   - `youtube-docudrama-editing`
   - `multimodal-qa-review`
   - `prompt-evaluation`
2. Craft skills (`.claude/skills/`): Load via `.claude/skills/INDEX.md` and `docs/architecture/STAGE_CROSSWALK.md`. Never load retired skills from `.claude/skills/_archive/`.

## 3. Step-by-Step Production Run Sequence

1. **Initialize Persistent State:** Create `episodes/<id>/production_state.json` via `ProductionStateMachine`. Check status anytime with:
   `python -m explainer_engine.core.execution_gateway status episodes/<id>/production_state.json`
2. **Research, Scenario & Docudrama Structure (`script`):**
   - Ground claims (`explainer_engine.scripting.claim_ledger`) and write the script.
   - Validate 2–3 dramatic 60–120s LTX scenes (>= 4 turns) and >= 1 visual bridge per 20s of narration via `explainer_engine.scripting.docudrama_structure.validate_docudrama_structure`.
3. **Unified Film Style Bible (`sound_plan` / `S3_film_direction`):**
   - Validate `film_style_bible/1` and compile layer directives (`explainer_engine.episode.style_bible.render_layer_directives`) covering maps (`Liberation Serif`), photos, LTX acting/motion (`camera_vocab`), visual bridges, and sound palette.
4. **Reference Photos (`pictures` / `S5_gemini_images` — `agent_browser_gate`):**
   - Generate reference turn-packs via browser agent and verify decode, dimensions, and SHA-256 through `SkillOrchestrator.run_stage("S5_gemini_images", ...)`.
5. **Voice & Measured Word Spine (`voice`):**
   - Align narration word-by-word (`explainer_engine.episode.timing` with `narration.scribe.json` or `audio/local_words.py`).
6. **Visual Clips (`clips`):**
   - `map_action`: MapLibre / `explainer_engine.maps` (approved `Liberation Serif` typography).
   - `still_25d`: `explainer_engine.fx25d.living` + `technical_gate.check_no_melt`.
   - `video` (LTX-2.5): Run photo-first loop (`explainer_engine.videolane.ltx_loop.run_continuous_shot_loop`) with 0.5s head/tail handles (`8n+1` frames), separate `StillUpscalerAdapter` and `VideoUpscalerAdapter` (`explainer_engine.videolane.adapters`), and strict `video_clip_record/1` (`PASS` + 64-char SHA-256).
7. **Visual Bridges, Sound & Assembly (`sound`, `assemble`):**
   - Compile bridges via `explainer_engine.overlay.bridge_compiler.compile_bridges_to_overlay_spec` + HyperFrames/FFmpeg composite.
   - Run free library-first SFX (`episode/sound_plan.py`) + `episode/run.py --to assemble`.
8. **Post-Assembly Visual-Aware Sound Spotting (`post_assembly_spotting`):**
   - Run `python -m explainer_engine.audio.post_assembly_spotting <preview.mp4> --out <spotting.json>` to pin visual-event SFX cues to the assembled video's SHA-256. Any edit to the video automatically invalidates old spotting records.
9. **3-Layer Perceptual QA & Identity Lock (`qa`):**
   - Run `python -m explainer_engine.qa.perceptual_qa --video <final.mp4> --out-dir <qa_dir>` (>= 8 frames, stereo audio, `check_no_melt`; opt-in `--gemini` for AI Eye+Ear review) and `explainer_engine.qa.identity_lock.check_cross_scene_identity` (commercial-safe YuNet+SFace `REVIEW` gate).
10. **Resuming Failed Runs & Approvals:**
    - If any stage fails or an upstream file changes, `ProductionStateMachine` marks downstream stages `INVALIDATED` and resumes cleanly from the earliest invalid stage.
    - Before ANY paid GPU/API call, obtain an explicit `config/owner_approvals.json` record bound to the 64-char SHA-256 manifest and authorize through `ProductionStateMachine.authorize_paid_action(...)`.
