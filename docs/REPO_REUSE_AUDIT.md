# Repository reuse audit — vano1919/tmr-video-script-engine

Read-only audit made on 2026-10-15 at commit `d88ba8f` for the explainer channel (two code-reading passes over the
modules named below). Canonical home of the reuse classification; `docs/PROVENANCE.md` records what was actually
copied.

## Summary

[OBS] Python 3.12, ~40k lines, 339 tracked files, ~708 test functions (unit 675 / integration 28 / system 4 / e2e 1; last
runbook: "716 passed"). Windows-first (PowerShell, `.exe` tools), FFmpeg on PATH, Kokoro ONNX on CPU, moderngl on the RX 5700.
No CI for tests, no PR template, `.claude/` has one skill and no settings/hooks. **No secrets found** in tracked files or the
143-commit history; key files live under gitignored `tools/` (gap: no generic `*api_key*`/`*token*.json`/`*.pem` ignore
patterns — this repo's `.gitignore` has them). `jsonschema>=4.18` is already in `requirements.txt` but unused. Nothing in the repo does 2D vector
animation, storyboards, an SFX timeline, or a LUFS/true-peak gate for long-form (only Shorts get `loudnorm -14/-1.5`).
Kokoro timings come from phoneme durations of the re-exported `kokoro-v1.0-timed.onnx` (`voice_style.synthesize_timed`,
`create_timed`), words are matched heuristically (`timings.align`), and **the timed path has no unit test** — Phase 5 must
exercise it on the real model. Spend history in this account (TMR, `docs/KEY_FINDINGS.md`): ~$2.40 Gemini; vidIQ has since
dropped to 395 credits — the explainer ledger starts at 0 and counts only its own calls.

## Classification

| Component (path) | Classification | What changes for the explainer |
|---|---|---|
| `llm/client.py` (OpenAI-compatible, JSON repair, temperature ladder, continuation) | reuse unchanged | optional drafting only |
| `artifacts.replace_file` (Windows-safe atomic replace) | reuse unchanged | — |
| `housekeeping.py` run naming + protected cleanup | reuse with modification | protect `final.mp4`, `review_bundle/`; drop legacy adoption |
| `artifacts.ArtifactStore`, `status.py`, `control.py`, `errors.py` | reuse with modification | stage registry passed in (no hard-coded 12 stages); atomic `write_output`; drop cue errors |
| `pipeline.py` | pattern only (rewrite) | declared stage list; keep prefix-resume, partial-stage progress, save-before-fail |
| `audit/core.py` (tiers, gates, methods D/L/C/H, Claude-review merge) | reuse mechanism with modification | new layers = explainer technical + editorial QA; creator approval as an H item |
| `audit/registry.json` format + YouTube entries | reuse with modification | re-verify (accessed 2026-10-03; `yt_thumbnails`, `yt_ypp_ai_persona` unverified); add Shorts analytics + made-for-kids notes |
| `audit/lexicons.py` negation-aware lexicons | reuse with modification | explainer anti-pattern list (C) |
| `labels.py` | reuse with modification | labels: `sourced`, `measured`, `engineering_default`, `hypothesis` |
| `render/voice_style.py` (Delivery, `synthesize_timed`, wpm calibration, `intro_delivery` 160 wpm) | reuse with modification | new beat kinds instead of sleep phases; lively presets; drop calm defaults |
| `render/kokoro_worker.py` (`ensure_model`, `load_kokoro`, clip cache) | reuse with modification | extract model/cache helpers; new job renderer |
| `render/tts_prep.speakable` + pronunciations file | reuse with modification | generic number/acronym handling; own pronunciation file |
| `render/timings.py` (`phoneme_words`, `align`) | reuse with modification | new `build_words` for the explainer timeline |
| `render/visemes.py` (phoneme→opening, 120 ms smoothing, 30 ms lead) | reuse with modification | 6 mouth shapes for Kit; drop owl moods |
| `render/character.py` (`envelope`) | reuse unchanged | fallback mouth-from-loudness |
| `render/mix.py` (`shape_voice`, `_soft_limit`, block streaming, 3 duplicate duckers) | reuse with modification | one ducking helper, an SFX bus, LUFS/true-peak targets |
| `render/subtitles.py` (karaoke/typewriter ASS) + `shorts.captions_ass` | reuse with modification | Shorts burned-in captions; drop sleep fading |
| `render/video.py` | do not reuse whole | copy `encode_args`, `probe`, `sync_checks`, temp-file + rename, `-frames:v N` |
| `render/video_check.py`, `full_check.py`, `short_check.py`, `activity.py` | reuse with modification | thresholds for bright vector art; add true-peak to Short gate |
| `render/local.measure_loudness` (ebur128) | reuse unchanged | becomes a gate, not a report |
| `render/chunked_video.py` | pattern only | scene-chunk concat + single audio mux |
| `render/mp3.py`, `fonts.py` | reuse (fonts with modification) | brand fonts Fredoka/Inter |
| `render/imagegen.py` budget/estimate/cache pattern, `picture_library.py` | reuse with modification | asset library (SVG + concept refs) tag search; Gemini only for channel-identity assets |
| `publish.py` (no upload without `--yes`, always Private) | reuse with modification (Phase 9+, optional) | requires an approval record; still never public |
| `cloud/rp.py` guard/sweep, `conductor.py` | reuse unchanged if pods are ever used | not planned |
| `tests/helpers.FakeLLM` pattern | reuse pattern | fake renderer/TTS fixtures in the same style |
| `config.ProgramConfig/VoiceConfig`, `evidence.json`, `review_pack` body, `celestial`/`storybook`/`shorts_gl`/owl modules, `localimages`, `picture_check`, `music_synth` (calm drones), GUI `app.py`, flat CLI | do not reuse | sleep-specific or wrong medium |

**Placement (decided by the creator, 2026-10-15): a new, separate repository.** The TMR repo is read-only input: nothing
in it changes. The modules marked "reuse" above are **copied** into the new repo in Phase 1, each with a provenance header
(`# from vano1919/tmr-video-script-engine@d88ba8f:<path>`), together with their relevant tests (adapted). The copies then
evolve independently; there is no runtime import of `tmr_engine`. A short `docs/PROVENANCE.md` lists every copied file, the
source commit and what was changed.

---

## Facts from the audit that later phases depend on (file:line in the source repo at d88ba8f)

- **Word timing:** `voice_style.synthesize_timed` calls `kokoro.create_timed(...)` only with `kokoro-v1.0-timed.onnx`;
  per-clip `<job>.timings.json` = `[[phoneme, start, end], ...]`; words matched by `timings.align` (heuristic).
  No unit test covers the timed path (`FakeKokoro` has only `create()`): Phase 5 tests it on the real model.
- **Loudness:** long-form loudness is measured (`local.measure_loudness`, ffmpeg `ebur128=peak=true`) but has no
  target; only Shorts are normalised (`loudnorm=I=-14:TP=-1.5:LRA=11`, single pass); `short_check` gates −17…−11
  LUFS and does not check true peak.
- **Encoding:** GPU pictures `libx264 -crf 18 -profile:v high -aq-mode 3`, 30 fps; CPU pictures `-preset veryfast
  -crf 23`; audio `aac 384k 48 kHz stereo`; exact frame count `-frames:v N`, temp file + rename, no faststart.
  Shorts: 1080×1920@30, `-preset slow -crf 16`, `aac 192k`, `+faststart`.
- **Ducking:** three similar implementations (`mix.intro_music` −7 dB, `StoryMusic.block` −6 dB, `shorts.sound`
  ≈ −5 dB), binary voice-activity envelope, ~0.3 s release; no SFX bus anywhere.
- **Lively delivery:** `voice_style.intro_delivery` (am_michael, 160 wpm, no calming donor); Shorts at 175 wpm;
  preset `kokoro_neutral` 150 wpm; `MAX_SPEED` 1.4.
- **Portability:** `fonts.py` falls back to Segoe UI/Georgia; the checks call bare `ffmpeg`/`ffprobe` from PATH.
- **Repo hygiene:** no secrets in tracked files or history (checked 2026-10-15); keys rely on gitignored `tools/`.

## Cloud and compositor port list (2026-10-16, D-31, D-32; TMR at d88ba8f; copies carry provenance when made)
| TMR source | Use here | Problem seen in TMR evidence | Solution here |
|---|---|---|---|
| `cloud/rp.py` (create, sweep, guard, delete, balance, price and time caps), `notify.py`, `watch.py` | the only way a pod is started or stopped | a forgotten pod billed about $3; the in-pod stop failed once; the guard died at its 30-min tool limit | copy as is; `guard` always with a 2 h timeout; sweep at session start and end; one pod per job; no pod without the creator's approved price and cap |
| `cloud/Dockerfile`, `setup_pod.sh`, `store.py` (push/pull of run results), `lint_manifest.py`, `dryrun.py`, stage manifests and the conductor pattern | pod image and stage runner | generic pod boot cost about $0.4 per pod (apt, compile); the image is 40 GB of models | lean image: no 27B and no llama.cpp (scripts come from Claude); only Z-Image (33 GB) and the compositor; baked image, boot from GitHub; preflight on the cheapest GPU first |
| `render/celestial.py` GLBackend, `video.py` (NVENC/x264 args, one FFmpeg pipe, frame(i) determinism, temp file + rename, probe, sync checks), `render/shaders/scene.frag` (parallax, grade), `depth.py` | the compositor core | no EGL in the cloud session: the video can only be proven on a pod | numpy reference compositor for tests (the walk test script is the first one), GPU path proven by the Phase 4 pod benchmark |
| (new) | sprite layer: pose swaps with crossfade, bob and squash, glow; doodle overlays rasterised per scene (text, arrows, draw-on progress masks) and uploaded as textures | text and doodles must stay exact and editable | overlays are SVG rasterised on the CPU with a pinned library; the sprite bank has a manifest (pose, expression, anchor, foot line) |
| `render/picture_check.py`, `qa/` checkers | gate on every generated picture | 13 of 23 SDXL pictures were defective; Z-Image passed | copy; retry up to 4 seeds; Gemini kit pictures also pass identity and green-spill checks |
| `render/subtitles.py` (libass karaoke), `mix.py`, `voice_style.py`, `kokoro_worker.py`, `timings.py`, `video_check.py`, `full_check.py` | audio, captions, QA (already planned for Phases 5-6) | Kokoro on a pod CPU: 45 min per 20 min of speech | narration and mix run in the cloud session (about 8 min per 20 min), clips are pushed to the pod, never rendered there |
| `render/imagegen.py` (prices, estimate, cache, budget refuse), `owl_pair.key_green`, `patch_pose` | Gemini kit generation | Gemini repaints the whole picture on every edit | region patching for mouth or eye states if a talking mascot is ever needed (D-33 makes it unnecessary for now) |

