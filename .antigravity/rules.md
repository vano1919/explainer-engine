# Antigravity Operational Constitution — Super-Realistic Cinema Engine

These rules govern ALL autonomous Antigravity sessions on `vano1919/explainer-engine` and synchronize 100% with `.claude/settings.json`, `explainer_engine/governance/gateway_hook.py`, `explainer_engine/core/spend_ledger.py`, and `config/super_realistic_film_bible.json`.

## 1. Financial Ceiling & Spend Ledger Law (NON-NEGOTIABLE)
- **Modal H100 (`MODAL1` / LTX-2.5):** **$15.00 TOTAL HARD CAP** for the autonomous production session.
  - Every paid Modal launch MUST atomically `reserve()` in SQLite WAL (`explainer_engine/core/spend_ledger.py`) BEFORE calling Modal, and `settle()` actual USD IMMEDIATELY after completion.
  - **80% Checkpoint:** Hard warning & budget checkpoint at **$12.00**.
  - **100% Hard Block:** Absolute `OVERRUN` block at **$15.00** (zero exceptions).
  - Keep LTX-2.5 action clips tight at **4.0–6.0 seconds** (`97–145` frames @ 24fps, `8n+1`) so each clip costs ~$0.06–$0.10 on H100.
- **Local CPU Rendering & Built-In Photo Gen (`generate_image`):** **$0.00 unlimited** — iterate locally until maps, 2.5D, bridges, color grade, and audio mixes are spotless before spending Modal dollars.
- **Other External Paid APIs (ElevenLabs, Paid Gemini API, Paid Claude API, RunPod, BFL, Fal):** **$0.00** unless explicitly approved by the owner. Use free local TTS (`edge-tts` / `piper-tts` / WAV fixtures) labeled `rehearsal_tts` for 70/30 narration rhythm testing.

## 2. Super-Realistic 35mm Film Style Purity (TOTAL PURGE)
- **Single Source of Truth:** `config/super_realistic_film_bible.json` + `explainer_engine/episode/style_bible.py` strictly supersede legacy cartoon/illustrated/flat presets (`crossworld_main_style_v1`, `main_style_5709.png`, `ComicNeue`, `Bangers`, `design/palette.json`).
- **Zero Legacy Tokens:** Every active prompt, config, and preset MUST pass `lint_super_realistic_prompt()` — rejecting `cartoon`, `comic`, `anime`, `cel-shaded`, `clay`, `3d render`, `pixar`, `flat vector`, `neon`, `glossy cgi`, `storybook`, `painted look`.
- **Unified Cinema Lens:** LTX-2.5 clips, 2.5D parallax scenes, Natural Earth shaded-relief maps, and visual bridges MUST ALL pass through `explainer_engine/finish/cinema_grade.py` (`assets/luts/historical_docudrama_35mm.cube` + 35mm grain + soft vignette).

## 3. Production & Continuity Laws (Fixing DEF-01..DEF-11)
1. **Anchor-First ImagePaths (`DEF-01`, `DEF-02`):** Generate and SHA-256-lock `character_anchors/` + `location_anchors/` FIRST. Pass those exact anchor `ImagePaths` into EVERY subsequent scene keyframe generation and verify via `explainer_engine/qa/identity_lock.py`.
2. **Before-State Keyframes (`DEF-04`):** Transformation/ignition/movement shots MUST start from the pre-action initial state (e.g., unlit beacon, closed gate), NEVER the post-action outcome.
3. **4–6s LTX Clip Cap & Prop Continuity (`DEF-05`):** Every LTX prompt MUST be a single flowing present-tense paragraph with an explicit prop end-state clause (where held objects remain at clip end).
4. **Automatic BP-187 Tail Trimming (`DEF-03`):** Trim speech/action clips `0.35–0.50s` after the final spoken word or action beat via `explainer_engine/edit/trim.py`. NEVER ship 7-second dead pauses.
5. **Smart Hybrid Routing (`DEF-07`):** Target ~40–50% `ltx_video` (human acting/dialogue/fire/combat), ~30–40% `still_25d` (Depth Anything V2 ONNX continuous zero-tear parallax), ~15–20% `map_action` (Natural Earth 1:10m shaded-relief maps with synced CC0 SFX).
6. **2K Broadcast Master (`DEF-08`):** Every final delivery master MUST be `2560x1440`, `24 fps`, `yuv420p`, `48000 Hz` 2-ch stereo, `-14.0 ± 0.5 LUFS`, `<= -1.0 dBTP`.
7. **Scene-Locked Broadcast Audio (`DEF-06`, `DEF-11`):** Lock per-shot ambience strictly to `scene_environment` using verified CC0-1.0 WAVs (`assets/audio/library/cc0_cinema_manifest.json`), sidechain-duck music/ambience `-10` to `-14 dB` under narrator/dialogue, add `30–50ms` anti-pop fades + J/L-cut overlaps + `0.55s` ambience crossfades.

## 4. Mandatory Governed Execution & Multimodal Inspection (L0–L5)
- Route governed commands and spend accounting through `explainer_engine/governance/antigravity_runner.py` (logging every step to `jobs/antigravity_execution_ledger.jsonl` and enforcing `gateway_hook` + `ProductionStateMachine` + `spend_ledger`).
- **Eyes-On & Ears-On Rule:** NEVER claim PASS from logs alone. Always inspect per-shot 5-frame temporal strips, cut-boundary comparison sheets, audio timeline/loudness telemetry, AND directly watch/listen to rendered `.mp4` files before PASS.
- **No Attribution & No Secret Leaks:** Zero AI/assistant attribution in code/commits; zero API keys or tokens in logs, URLs, or git commits.
