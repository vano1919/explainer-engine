# Workflow 03: Scene-Locked Broadcast Audio & EBU R128 Mastering

## Prerequisites
- Verified CC0-1.0 48kHz stereo WAV library (`assets/audio/library/cc0_cinema_manifest.json`).
- Free local narration (`edge-tts` / `piper-tts`, labeled `rehearsal_tts`, `$0.00`) for 70/30 narrator-vs-dialogue documentary rhythm.

## Steps
1. **Per-Shot Environment Locking (`DEF-11`):**
   - Every shot declares its exact `scene_environment` (`dry_daylight_valley`, `map_table_war_room`, `torchlit_tent`, `windy_ridge`, `alpine_blizzard`, `roman_colonnade_dusk`, `sea_harbor_wind`, `night_rain_camp`).
   - Rain ambience is strictly forbidden on dry daylight or map shots.
2. **Multi-Track Stems & J/L-Cut Continuity (`DEF-06`):**
   - Layer 1: Narrator + LTX diegetic speech/action stem (trimmed per BP-187, `30–50ms` anti-pop fades, `0.25–0.50s` J/L-cut audio overlaps across cuts).
   - Layer 2: Scene-locked ambience bed with `0.55s` equal-power crossfades across scene changes.
   - Layer 3: Synchronized CC0 map-action & foley SFX aligned within `±40ms` of visual beats.
   - Layer 4: Restrained documentary underscore bed sidechain-ducked `-10` to `-14 dB` under speech.
3. **Mastering & Verification:**
   - Master to `48000 Hz` 2-channel stereo, `-14.0 ± 0.5 LUFS`, `<= -1.0 dBTP` via `pyloudnorm` + two-pass FFmpeg EBU R128 verification.
   - Pass `check_audio_scene_consistency()` before muxing final MP4.
