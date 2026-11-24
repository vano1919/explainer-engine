---
name: youtube-docudrama-editing
description: YouTube historical docudrama structure, word-synced audio-video alignment, visual bridges, 2-3 dramatic 1-2 minute LTX scenes, and post-assembly visual-aware sound spotting.
---
# YouTube Docudrama Editing & Audio-Video Harmony

## 1. Story-Driven Structure (Replaces Hardcoded 60/10/30)
Validated by `explainer_engine.scripting.docudrama_structure.validate_docudrama_structure`:
- **2–3 Dramatic Showcase Scenes** per full episode, each **60–120 seconds** with **>= 4 dialogue turns** — no isolated 1-line throwaway dialogue ("წამოძახებები").
- **Reserve LTX (`video`) strictly for those dramatic showcase scenes.** Analytical and narrated segments use **MapLibre maps (`map_action`)** and **2.5D living stills (`still_25d`)**.

## 2. Word-by-Word Sync & Visual Bridges
- `explainer_engine.episode.timing` aligns ElevenLabs `narration.scribe.json` word-by-word (`[{word, start_frame}]` at 24 fps) so cuts, map actions, 2.5D accents, and sound cues fire on exact spoken words.
- **Visual Bridges (YouTube richness):** Narration segments >= 20s MUST carry at least 1 visual bridge per 20s (`kinetic_callout`, `date_location_card`, `archival_quote_highlight`, `stat_counter`, `split_screen_comparison`, `tactical_map_overlay`, `document_zoom_highlight`).
- Use the 0.5s head/tail clip handles for clean **J-cut / L-cut** audio-led transitions (`0.25s–0.60s`).

## 3. Sound Sourcing & Post-Assembly Visual Spotting
- **Free library first** (`audio/sfx_library`); **ElevenLabs SFX** only for verified `needs` items with explicit approval/ledger tracking; zero procedural placeholders in final mix.
- **Post-assembly visual spotting (`validate_post_assembly_spotting`):** Final foley/SFX timing MUST be spotted against the assembled video cut (pinned by 64-char SHA-256) so every sound hits the exact on-screen visual event.
