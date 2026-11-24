# Wave Next Baseline Inventory

- **Date:** 2026-11-24
- **Base Branch:** `fix/explainer-engine-production-hardening-2026-11-24` (`f59b5ab6`)
- **Implementation Branch:** `feat/explainer-engine-nextgen-framework-2026-11-24`
- **Upstream Main:** `origin/main` (`b3866452d38539d53a91cc3d45c145138fdc6bac`)
- **Upstream Integration:** `origin/integration/explainer-engine-unification` (`9bd5ce1638b135a8265e9921365e2fa7c9fe387`)
- **Draft PR Preserved:** PR #271 (all 9 hardening commits preserved byte-for-byte)

## 1. Existing Core Architecture & Production Execution Paths

| Subsystem | Key Modules | Current Status |
| :--- | :--- | :--- |
| Episode-First Runner | `explainer_engine/episode/run.py` (`STAGES = script..qa`), `timing.py`, `sound_plan.py`, `style_bible.py` | Active deterministic runner (`$0.00` inside runner) |
| Governance & Spending | `core/approvals.py`, `core/spend_ledger.py`, `core/spend_caps.py`, `cloud/night_budget.py`, `governance/hooks.py`, `cloud/hooks.py` | Active fail-closed SQLite WAL ledger + 64-char SHA-256 approvals + Claude Code hooks |
| Visual Routes | `maps/maplibre_spec.py`, `maps/draw.py`, `fx25d/living.py`, `videolane/scene.py`, `videolane/ltx_loop.py`, `overlay/hyperframes.py` | Active; `maps/draw.py` still defaults to `Inter.ttf` instead of `Liberation Serif` |
| Audio & Transcription | `audio/local_words.py`, `audio/sfx_library.py`, `audio/layers.py`, `audio/stems.py`, `audio/free_import.py` | Active library-first SFX + measured word spine; post-assembly spotting not yet hooked into runner |
| Multimodal & Technical QA | `qa/perceptual_qa.py`, `qa/technical_gate.py`, `qa/delivery_gate.py`, `qa/face_points.py`, `qa/prompt_eval.py` | Active 3-layer QA; cross-scene YuNet+SFace identity REVIEW gate not yet integrated |
| Orchestration & Skills | `orchestration/skill_orchestrator.py`, `skill_registry.json`, `.claude/skills/` (30 active + vendored `v-*` + `_archive`), `.agents/skills/` (8 portable) | Active; needs unified execution gateway + persistent resumable state machine |

## 2. Sandbox Environment Capabilities & Honest External Blockers

- **Available locally:** `python3` (3.11), `ffmpeg`, `ffprobe`, `node`, `npx`, `ruff`, `basedpyright`, `pytest` (`642 passed, 17 skipped` on baseline subset).
- **Unavailable / External Blockers:**
  - `blender` binary: not installed in this Linux sandbox container (Blender specs/validators run in Python; live `bpy` render requires local workstation or Blender CI runner).
  - Paid cloud GPU / APIs (`Modal H100`, `ElevenLabs`, `Gemini API`, `Claude API`): `$0.00` spend enforced — no live paid calls without explicit `owner_approvals.json` entry.

## 3. Gaps Targeted by This Autonomous Implementation Wave

1. **Unified Execution Gateway & Persistent State Machine** (`explainer_engine/core/execution_gateway.py`): single resumable state machine enforcing stage dependencies, artifact fingerprints, upstream invalidation, and fail-closed approval/spend gating.
2. **Interchangeable Video & Upscaler Adapters** (`explainer_engine/videolane/adapters.py`): strict separation of `StillUpscalerAdapter` vs `VideoUpscalerAdapter` and `LTXGenerationAdapter` (native/ComfyUI/offline rehearsal) wired into `ltx_loop.py`.
3. **Map Raster Typography Fix** (`explainer_engine/maps/draw.py`): resolve `Inter.ttf` -> `Liberation Serif` approved typography with clean fallback.
4. **Visual Bridge Compiler** (`explainer_engine/overlay/bridge_compiler.py`): compile `docudrama_structure.py` visual bridges directly into `overlay_spec/2` HyperFrames specs + FFmpeg fallback render.
5. **Cross-Scene Commercial-Safe Identity Lock** (`explainer_engine/qa/identity_lock.py`): calibrated `YuNet + SFace` / deterministic fallback returning `REVIEW` (never arbitrary FAIL on back-facing/profile faces).
6. **Post-Assembly Visual-Aware Sound Spotting** (`explainer_engine/audio/post_assembly_spotting.py`): SHA-256 video-pinned spotting + invalidation on video change + 30ms anti-pop transition A/B verification.
7. **Claude Opus Governance Hooks & Handoff** (`explainer_engine/governance/hooks.py` extension + `docs/implementation/CLAUDE_OPUS_PRODUCTION_HANDOFF.md` + `WAVE_NEXT_EXECUTION_LEDGER.md`).
