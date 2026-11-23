---
name: explainer-architecture
description: Navigate Explainer Engine v4.3 episode-first production architecture, stage crosswalk, active routes, and canonical camera vocabulary.
---
# Explainer Architecture

## Authoritative Entrypoint
- Draft production runner: `python -m explainer_engine.episode run <episode> --to qa`
- Stage crosswalk: `docs/architecture/STAGE_CROSSWALK.md`
- Active visual stack: Blender previs (`explainer_engine.lab`), Gemini reference stills, Modal LTX-2.5 video (`MODAL1`), MapLibre cartography (`explainer_engine.maps`), and 2.5D living motion (`explainer_engine.fx25d.living`).
- Retired routes (never revive): Unreal Engine, Qwen-LoRA, legacy PIL map renderer.

## Core Invariants
1. Camera vocabulary comes solely from `explainer_engine.core.camera_vocab.ALLOWED_CAMERA_MOVES` (`truck`, `zoom_in`, `zoom_out`, `truck_zoom_in`, `truck_zoom_out`).
2. `explainer_engine.core.fingerprints.code_digest` fails loudly if any required source file is missing.
3. Never modify vendored `.claude/skills/v-*`, `.claude/skills/_archive`, or `CLAUDE.md` without explicit owner authorization.
