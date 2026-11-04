# =============================================================================
# TODO [CLAUDE-MASTER-MOLD-SYNC] — BATCH-M3: 6-Stage FFmpeg Voice Post-Processing Chain (`D-81` Exact Parameter Alignment)
# Target Module : explainer_engine/audio/voice_chain.py
# Target Classes/Symbols : VoiceChainConfig, VoiceChainProcessor, build_d81_filtergraph, apply_voice_chain
# Reference Guide : docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md
# Roadmap Reference : docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md
# =============================================================================
#
# 1. რა ცვლილება უნდა გაკეთდეს (EXACT SYNCHRONOUS CHANGE SPECIFICATION):
#    CRITICAL FIX in `explainer_engine/audio/voice_chain.py`:
#    1. Align `VoiceChainConfig` and `build_d81_filtergraph()` with the exact 6-stage `D-81` specification in `MASTER_MOLD.md` §4 (`D-81`):
#       - Stage 1 (Sub-rumble cut): `highpass=f=75` (currently `80` in code — MUST change to `75` Hz).
#       - Stage 2 (Spectral denoise): `afftdn=nf=-25` (exact match).
#       - Stage 3 (Warmth shelf): `bass=g=2.5:f=120:w=0.6` (currently `equalizer=f=130:t=q:w=1.2:g=2.0` — MUST change to `bass=g=2.5:f=120:w=0.6`).
#       - Stage 4 (Presence boost): `equalizer=f=3200:t=q:w=1.2:g=1.8:m=0.5` (currently `f=3200:t=q:w=1.4:g=1.5` — MUST change to `w=1.2:g=1.8:m=0.5`, with automatic fallback omitting `:m=0.5` only if an older local FFmpeg binary lacks mixed-mode equalizer support).
#       - Stage 5 (True-peak brickwall limiter): `alimiter=limit=-1.0dB:level=disabled` (currently missing `:level=disabled` — MUST add `:level=disabled` so `alimiter` does not auto-boost make-up gain before loudness normalization!).
#       - Stage 6 (Two-pass ITU-R BS.1770-5 loudness normalization): `loudnorm=I=-14.0:TP=-1.0:LRA=7.0` (`-14.0 LUFS +/- 0.5`, `-1.0 dBTP`, target `LRA 4–9 LU`).
#    2. Wire `apply_voice_chain()` into `explainer_engine/audio/tts.py` (for both narrator and `D-90` character stems) and `explainer_engine/audio/mixer.py`.
#
# 2. რა ნაკლოვანება აქვს ამჟამინდელ კოდს (CURRENT CODE FLAW / DEFICIT AT 5013a55a):
#    `explainer_engine/audio/voice_chain.py` currently diverges from `MASTER_MOLD.md` `D-81` on 4 of the 6 stages (`highpass=f=80` vs `75`, `equalizer=f=130` vs `bass=g=2.5:f=120:w=0.6`, `w=1.4:g=1.5` vs `w=1.2:g=1.8:m=0.5`, and `alimiter` missing `level=disabled`, which causes `alimiter` to apply unwanted automatic make-up gain!). Furthermore, `voice_chain.py` is never called by `tts.py` or `mixer.py`.
#
# 3. რატომაა უახლესი გადაწყვეტა უკეთესი (WHY THE NEW SOLUTION IS SUPERIOR):
#    Restores 100% bit-exact compliance with `MASTER_MOLD.md` `D-81`, prevents `alimiter` auto-gain pumping via `level=disabled`, and ensures every narrator and historical character stem hits `-14.0 LUFS` and `<= -1.0 dBTP`.
#
# 4. დამადასტურებელი ვებ-წყაროები — მინიმუმ 5 წყარო (VERIFIED WEB SOURCES >= 5):
#    [1] ITU-R BS.1770-5: Algorithms to Measure Audio Programme Loudness and True-Peak Audio Level
#        URL: https://www.itu.int/rec/R-REC-BS.1770/en
#        Rationale: International standard defining K-weighted loudness (LUFS), gating blocks, loudness range (LRA), and 4x oversampled True Peak (dBTP) measurement.
#    [2] EBU Tech 3341 / EBU R 128 Loudness Metering Specification
#        URL: https://tech.ebu.ch/publications/tech3341
#        Rationale: Defines integrated loudness targets, short-term/momentary windows, and loudness range (LRA 4-9 LU) for broadcast and streaming dialogue.
#    [3] FFmpeg Audio Filters Official Reference (highpass, afftdn, bass, equalizer, alimiter, sidechaincompress, loudnorm)
#        URL: https://ffmpeg.org/ffmpeg-filters.html#Audio-Filters
#        Rationale: Authoritative parameter specification for the 6-stage D-81 chain (highpass=f=75, afftdn=nf=-25, bass=g=2.5:f=120:w=0.6, equalizer=f=3200:t=q:w=1.2:g=1.8:m=0.5, alimiter=limit=-1.0dB:level=disabled) and D-86 sidechain ducking.
#    [4] pyloudnorm Documentation (csteinmetz1/pyloudnorm)
#        URL: https://csteinmetz1.github.io/pyloudnorm/
#        Rationale: Python ITU-R BS.1770-4/5 implementation used in explainer_engine/audio/loudness.py for integrated_loudness and loudness_range verification.
#    [5] YouTube Stable Volume & Audio Normalization Guidelines
#        URL: https://support.google.com/youtube/answer/1722171?hl=en
#        Rationale: Establishes streaming delivery expectations around -14.0 LUFS integrated loudness and <= -1.0 dBTP true-peak ceiling to prevent platform limiting artifacts.
# =============================================================================
"""Stub specification module for explainer_engine/audio/voice_chain.py (to be implemented by Claude per TODO above)."""
from __future__ import annotations
