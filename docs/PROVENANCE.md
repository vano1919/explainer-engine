# Provenance of copied code

Source: `vano1919/tmr-video-script-engine` at commit `d88ba8f` (2026-10-15), same owner. Copied files carry a
`# from vano1919/tmr-video-script-engine@d88ba8f:<path>` header. They evolve independently; nothing imports
`tmr_engine` at run time (`tests/unit/test_repo_hygiene.py` enforces both rules).

| File here | Source | What changed |
|---|---|---|
| `explainer_engine/core/store.py` | `tmr_engine/artifacts.py` | stage registry passed in (`Stage`, `JobStore`); all writes atomic; `NEEDS_REVIEW`; `completed_prefix()` for resume |
| `explainer_engine/core/jobs.py` | `tmr_engine/housekeeping.py` | `run-` → `job-`; protects `final.mp4`, `review_bundle`, `NEEDS_REVIEW` jobs; legacy adoption removed |
| `explainer_engine/core/errors.py` | `tmr_engine/errors.py` | cue/schedule errors removed; `ContractError`, `ConfigError`, `RetryableError`, `NeedsReview` added |
| `explainer_engine/core/labels.py` | `tmr_engine/labels.py` | label vocabulary: `sourced`, `measured`, `engineering_default`, `hypothesis`, `playback_dependent` |
| `explainer_engine/audio/timings.py` | `tmr_engine/render/timings.py` | kept `phoneme_words`/`align`/`estimate`/readers; TMR `build_words`/`write_words` removed |
| `explainer_engine/audio/visemes.py` | `tmr_engine/render/visemes.py` | owl sprites, moods and `OwlTrack` removed; timing logic unchanged |
| `explainer_engine/audio/envelope.py` | `tmr_engine/render/character.py` | `beak` → `mouth`; logic unchanged |
| `setup.ps1` | `setup.ps1` | Python venv + requirements only (Kokoro, Node and Remotion arrive in their phases) |

Tests adapted from `tests/unit/test_timings.py`, `test_celestial.py` (viseme part), `test_character.py` and
`test_housekeeping.py` live in `tests/unit/test_audio_timing.py` and `tests/unit/test_core.py`.

## Planned copies (made in the phase that needs them, not before)

| Phase | Source | Purpose |
|---|---|---|
| 5 | `render/voice_style.py` (Delivery, `synthesize_timed`, wpm calibration), `render/kokoro_worker.py` (`ensure_model`, `load_kokoro`, clip cache), `render/tts_prep.py` (`speakable`, pronunciations) | narration |
| 5 | `render/mix.py` (`shape_voice`, `_soft_limit`, block streaming, ducking), `render/local.py::measure_loudness` | mix + LUFS/true-peak gate |
| 6 | `audit/core.py` (tiers, gates, D/L/C/H methods, review merge), `audit/registry.json` format + YouTube entries (re-verified), `audit/lexicons.py` | QA and policy registry |
| 6 | `render/video_check.py`, `full_check.py`, `short_check.py`, `render/video.py` (`encode_args`, `probe`, `sync_checks`) | technical QA, encoding |
| 7 | `render/subtitles.py`, `shorts.captions_ass` | burned-in Shorts captions |
| later, optional | `llm/client.py`, `publish.py` (private-only upload), `render/picture_library.py`, `render/imagegen.py` budget pattern | drafts, private upload, asset library, paid-call budget |
| `explainer_engine/audio/voice_layer.py` | `tmr_engine/render/voice_style.py` (`build_style` blend), `tmr_engine/render/mix.py` (`shape_voice`, `_deess`, `_moving_average`) | blend takes any number of voices; shaping reduced to warmth, brightness, de-essing; pitch, timing checks and measurements are new |
