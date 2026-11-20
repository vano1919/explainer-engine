# Overlay for `v-audio-production-skill`: Mix, stems and loudness (layer L20, stage G8, audio of G9)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/audio-production-skill, page `audio-production` (MIT, commit `03000d0d32`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel whose mix is drawn by one renderer of its own,
so the vendored package is a reference for how a safe audio graph is shaped, not a tool we call. The upstream text is this folder's `SKILL.md`; open its `README.md` (operation table, error codes) and `docs/` only when designing a new
audio operation in our code. The package is not installed and is not in `requirements.txt`.

## Where this layer sits

The sound of an episode is decided in three steps, and this page owns only the last one:

1. **What sounds** (skill `v-design-sound`): the AV contract gives every visible event one audio decision, the place gets
   its bed, the library supplies the takes; `episode/sound_plan` writes `audio/sound_plan.json` at G4.
2. **What plays when** (`episode/cue_sheet.build`): one row per sound with its asset, time, layer, gain, pan, fades and
   ducking group (SP-06). The renderer decides nothing that is not on a row.
3. **How it adds up** (here): `audio/stems.render` plays the rows into five 48 kHz stereo stems, `audio/mix_check.check`
   measures them, assembly normalises the master, and G10 measures the delivered file again.

Not here: choosing sounds, buying music or effects (skill `v-elevenlabs-sound-effects`, skill `v-elevenlabs-music`), the
word clock (skill `v-elevenlabs-speech-to-text`), measuring arbitrary files (skill `v-media-analysis-skill`).

## Procedure

1. G6 has a PASS or REVIEW record: the real read `audio/narration.wav` and its clock `audio/timing.json` exist. No code here
   can make a voice; without the read a shippable render stops and a rehearsal renders a preview that says so.
2. Run the stage: `python -m explainer_engine.episode run episodes/<id> --stage G8`. It rebuilds the sound plan on the
   measured clock, builds the cue sheet, renders the stems and writes `production/stages/sound.json`.
3. Read the record, not the console: `sound_is_real` (no placeholder, no missing class, the real read), the equal-level
   rows (BP-186), and `audio/stems_report.json` (`events_placed`, `placeholders`, `silent_rows`).
4. Read `mix_check.json`: delivered loudness and true peak after the same normalisation assembly uses (BP-50; Shorts BP-61),
   clipping, digital silence outside a declared silence (BP-161), and the voice against music and background in LU while
   the narrator speaks (BP-52), plus the per-shot rows where an effect covers a word.
5. Only then G9 (`--stage G9`, chunked assembly in `production/assemble.py`) and G10, where `qa/sound_realism` measures the
   master itself: no dropout and no dead dialogue (BP-189), line-to-line pauses (BP-190), sound across the cut (BP-191),
   map and chart motion heard (BP-192), no generated noise as a bed (BP-193).
6. Report each verdict with the file it was measured on. A machine PASS is never "someone listened": say plainly who did.

## Rules that bite at this layer

- **One level everywhere.** Every loudness number is read from `explainer_engine/standards/sourced_rules.json` through
  `qa/targets.py`; there is no second table. A map shot, a 2.5D shot and a video shot sound alike (BP-186): the background
  of each route group is measured and the medians compared.
- **The voice is the anchor.** Music and bed duck under it as a dip, never a cut (BP-53, `audio/duck.py`); a war cry or a
  horn dips the background bus under the ceiling (`stems.bus_limit`) and the voice is never turned down for it.
- **The bed never stops.** One continuous bed per place runs under every line and across every cut (BP-189, BP-191); the
  clip's own track cuts with its picture under a short fade while the bed crosses. A gap is a FAIL, not a style.
- **The narration is consistent before it is mixed.** Chunks levelled to their median and joined without a step
  (`audio/seams.py`, BP-59), a slow gain rider for sentence swings (`audio/level.py`), pauses filled with room tone, never
  digital zero (BP-60), and a drift check on the timbre (`audio/voice_check.py`).
- **Clip-spoken shots** (D-132): the LTX line and the narrator's read become one voice track (`videolane/voice.py`), each
  clip set to the read's speech level, so the stems duck under dialogue exactly as under narration.
- **Final-plan mix targets** (the voice-to-music gap, the tight loudness band, the codec-safe peak, the sidechain times)
  enter only as registry rows with their sources (W2 work). Never type them into code or a mix by hand.

## Failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| music "pumps" | duck attack or release too short | BP-53 range; `duck.max_step_db_per_ms` on the render; ear-only values are the creator's call |
| voice buried under an effect | gain or distance wrong on one row | the per-shot row in `mix_check.json`; fix the cue's level or distance, never lower the voice |
| loud jump at a read join | chunks at different loudness | `python -m explainer_engine.audio.seams chunk1 chunk2 ...` and re-join; a correction over its limit is a finding |
| dead air in a dialogue scene | bed missing or ending at a cut | the place's bed row in the cue sheet; `production/scene_join.py` keeps the bed under clip joins |
| master off target after encode | measured before the AAC encode | `qa/targets.measure_file` on the delivered MP4, not the WAV |
| a silent row in the stems | preview with a placeholder or missing class | fill the class in the library (skill `v-design-sound`); a shippable render refuses it |
| stems do not sum to the mix | a row played outside the five buses | `audio/stems.render` is the only renderer; no hand mix beside it |

## Checks in code

`audio/stems.render`, `level_report`; `audio/mix_check.check`, `ambience_continuity_rows`; `qa/targets.verdicts`,
`measure_file`, `normalise_file`; `audio/layers.check` (AL-01..AL-04, BP-54..BP-57, BP-62); `qa/sound_realism`
(`python -m explainer_engine.qa.sound_realism <video.mp4> --timeline <scene_timeline.json>`); `episode/acceptance` rows.

## References: when to open which

| File | Open when |
|---|---|
| `README.md` | you design a new typed audio operation and want its error-code and validation pattern |
| `docs/contract.md` | you write a request/response schema for an audio step in our code |
| `docs/architecture.md` | you want the measure-decide-execute split explained with an operation graph |
| `docs/decisions.md` | you compare `loudnorm` with `ebur128` routing (their ADR found the same samples) |
| `docs/ffmpeg-skill.md` | you need to know how it hands loudness to the FFmpeg engine (ours: skill `v-ffmpeg-skill`) |
| `src/audio_production/timeline.py` | you check how stems of programme length are built so they sum to the mix |

Ideas we keep from upstream: measure first, decide, then execute; no defaults for production values (ours come from the
registry); refuse raw filter strings; outputs never written over inputs; every output carries what made it.

## Not used from upstream

Running the package or its CLI (not installed; one renderer only), filler-word removal on the read (a wrong word is
re-read for that sentence, skill `elevenlabs-voice`), FFT noise reduction and speech clean-up presets on ElevenLabs reads
(they arrive clean), surround down-mix, broadcast delivery sets (ATSC and similar: we deliver YouTube long-form and Shorts
only), and the routing notes for its own agent ecosystem.
