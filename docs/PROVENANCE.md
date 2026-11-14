# Provenance of copied code

> **Legacy (image-generation era) note, 2026-11-05 (ICW-01, D-96).** Where this page names Qwen keyframes, LTX clips, sprites, painted pictures or 2.5D stills as the production path, it describes the legacy image-generation route (D-43, D-80, D-105); the Ink Chronicle Blender lanes follow D-97 and the decision log wins on a conflict (CLAUDE.md precedence rule). Everything else on this page stays in force.

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
| `explainer_engine/cloud/store.py` | TMR `cloud/store.py` at `1c33878` | the durable store of the Guardian (2026-10-22): stdlib backend switch (`EXPLAINER_STORE_LOCAL` folder or the HF dataset), sha256 sidecar on every push, `verify` reports and never deletes, `store_job` for the job record; env names `EXPLAINER_STORE_*` |
| `explainer_engine/production/depth.py` | TMR `tmr_engine/render/depth.py` at `1c34e27` | env `EXPLAINER_DEPTH_DIR`; maps sit next to any picture (not only graded backdrops); a `main` CLI for files and folders (D-70 stage F parallax) |

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
| `explainer_engine/imagegen/gemini.py` | `tmr_engine/render/imagegen.py` (`GeminiImages`, `PRICES`) | stdlib client reshaped: reference list, 2026-10-16 price table, 80 % cap stop, cache by prompt + references, spend log, text `judge` call |
| `explainer_engine/cloud/runpod.py` | TMR `cloud/rp.py` at `f0abe62` (branch `claude/master-directive-prompt-5rmv2y`) | one retrying HTTP layer; create never re-POSTed after an unclear answer (found by unique name); verified, idempotent stop/delete; per-pod session files instead of one `pod_meta.json`; guard enforces the name's lifetime, stays blind-safe, stops instead of deleting; `config/spend_caps.json` preflight; `check`, `cost` (billing API), `PodSession`; the in-pod side (bootstrap, conductor, painters) stays in TMR |
| `explainer_engine/cloud/store.py` | TMR `cloud/store.py` at `1c33878` | the durable store of the Guardian (2026-10-22): stdlib backend switch (`EXPLAINER_STORE_LOCAL` folder or the HF dataset), sha256 sidecar on every push, `verify` reports and never deletes, `store_job` for the job record; env names `EXPLAINER_STORE_*` |

## Third-party code copied from public repositories (rule drafted in the Fable quality report, WP-Q8)

| File here | Source | What changed |
|---|---|---|
| `explainer_engine/blender/polyhaven.py` | `ahujasid/blender-mcp@2e4b0bc294694b1570d76ed01be657c22e6d02a0:addon.py` (MIT, (c) 2025 Siddharth Ahuja) | the Poly Haven part only: API get with ETag/TTL cache, slug guard, md5-checked streamed download, texture-map selection, `include` side files with the zip-slip guard, the HDRI world node chain. `requests` became `urllib`, the User-Agent names this project, model import is glTF (the artist's `.blend` node tree would be replaced by `style.py` anyway). NOT taken: the socket server, telemetry, edit recorder, paid 3D generators. |

## Third-party data downloaded at run time (not in git)

| Data | Source | Licence | How it is used |
|---|---|---|---|
| Upscale model `4xNomos2_realplksr_dysample` (RealPLKSR with DySample, author Philip Hofmann "Phips") | Hugging Face `Phips/4xNomos2_realplksr_dysample` revision `893bd79c7eccc29cc04fa0ac4ff08f72585c2605`, file `4xNomos2_realplksr_dysample.safetensors` sha256 `371c210e419fb9a4c3f7bf1b9a94dfae0e344232a81147d4c9f9c96b44b5702a`, fetched by `python -m explainer_engine.finish.superres fetch` into `$EXPLAINER_MODELS_DIR` (never in git) | CC BY 4.0 (model card front matter `license: cc-by-4.0`, read 2026-11-14; the card body's "CC-BY-0.4" is a typo of the same licence): attribution to the author when the weights are shared; the pictures it makes are ours | `finish/superres.py` (main model; its card notes saturated colours, so a wavelet colour fix runs after it) |
| Upscale model `2xNomosUni_span_multijpg` (SPAN, author Philip Hofmann "Phips") | Hugging Face `Phips/2xNomosUni_span_multijpg` revision `ed6111c4cabdaf42b75e6535600d5370cce9e4e2`, file `2xNomosUni_span_multijpg.safetensors` sha256 `bee2a9c082f2b8f6e7f5db504b36593c24a1a959511f587114c399ca58b9c92c`, same fetch | CC BY 4.0 (model card, read 2026-11-14) | `finish/superres.py` (fallback model) |
| Natural Earth 1:10m shaded relief `SR_HR.tif` (+ `SR_HR.tfw`), version 2.0.0 | `https://naciscdn.org/naturalearth/10m/raster/SR_HR.zip`, sha256 `b2619fff2fc73c17152983c066adfaa25c4b626916b822bad2fae8bcd9be41a5`, downloaded 2026-11-12 by `python -m explainer_engine.production.relief_fetch` into `tools/maps/` | public domain ("All versions of Natural Earth raster + vector map data found on this website are in the public domain", naturalearthdata.com/about/terms-of-use, read 2026-11-12) | `maps/relief.py` samples it for the map plates' relief (v4.3 P4, replaces the synthetic DEM, F6) |
| Inter font `Inter.ttf` | github.com/google/fonts `ofl/inter` via jsDelivr, 2026-11-12 (in git: `assets/fonts/`) | SIL OFL 1.1 (`assets/fonts/OFL_Inter.txt`) | map lettering (`maps/draw.py` face `map`) |
