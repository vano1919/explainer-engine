# Mix chain (final plan S13, W6)

One function mixes every episode: `audio/mix_chain.mix_stems`, called by `audio/stems.render` (G8). It replaces the three separate
steps G8 had (duck, bus limit, scale-down) and adds the master. Judged by `validators/mix.py` (`VAL-MIX-01..05`); measured by
`mix_chain.verify` (ffmpeg ebur128, an independent measurement from the chain's own BS.1770 code, plus an AAC round trip).

| Step | What | Where the number lives |
|---|---|---|
| Voice bus | the read, centre, never ducked or filtered | |
| Music duck | sidechain from the voice, attack 10 ms, release 250 ms | depth: BP-53 house depth (`audio/duck.DEPTH_DB`); attack/release: BP-214 (hypothesis, REVIEW only) |
| Carve | 1-4 kHz of the music dips 3 dB while the voice speaks (zero-phase band split) | BP-214 (from the vendored `v-design-sound` mix.md) |
| Music under voice | static trim until the voice is at least `voice_over_music_min_lu` over the music while it speaks (+0.5 LU margin) | BP-208 |
| Bed | ducked at BP-53's floor depth; effects not ducked (the plan must hand the chain ONE bed: wind and crowd summed into one bed stem, the owner's standing decision) | BP-53, `audio/stems.BED_DUCK_DB` |
| Master | one static gain to BP-50's target, then one 4x-oversampled true-peak limiter with a ceiling `TP_MARGIN_DB` (0.5 dB) under `true_peak_max`, applied to every stem alike so the stems still sum to the mix | BP-50, BP-208 tight band (`lufs_tight_band`) |
| Per scene | at least `effects_per_scene_min` effects; one bed with no gap (rows that abut or cross-fade by at most 1 s are one bed) | BP-209 |

No loudness or peak number is written in `mix_chain`: the target and the peak ceiling come from `qa/targets.PROFILES`, the gap and the tight band from BP-208, and the chain's own settings (attack, release, carve, limiter margin, gap margin) from BP-214, a hypothesis row (REVIEW only, one source of one type: the vendored skill's mix.md). `tests/unit/test_mix_chain.py` keeps the module and the registry together.

`stems.render(..., master=False)` skips the master (a preview where loudness does not matter); the default is on.

## Parity run on the old 1914 minute

`python -m explainer_engine.audio.mix_parity --plan episodes/ep_truce_1914/audio/sound_plan.json --narration <narration.wav> --library <root> --out <dir>`
renders the first 60 s of the plan through `stems.render` as a **preview** (a library take whose file is missing stays silent, D-136)
and verifies it. Result and links: `docs/PROGRESS.md` under W6 and `HANDOFF_W6.md`. It tests the chain; it is not a final mix.

## Voice and effect generation overlays

`elevenlabs-voice` names `v-elevenlabs-text-to-speech`, `-sound-effects`, `-music` and `-speech-to-text` for API usage; its one-take
and credit rules (EL-01..EL-13) and the PreToolUse hook (`.claude/settings.json` -> `standards/hook.py`) stay the enforcement. The
voice-first test E1 is prepared in [E1_PLAN_2026-11-20](E1_PLAN_2026-11-20.md) and not run.
