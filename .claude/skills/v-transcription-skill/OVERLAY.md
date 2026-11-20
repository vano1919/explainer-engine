# Overlay for `v-transcription-skill`: Local transcription (layer L17, stages G6, G7 and G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/transcription-skill, page `transcription-skill` (MIT, commit `4be7156228`). Rewritten 2026-11-20
under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for three free jobs on our own audio.
The upstream text is this folder's `SKILL.md`; the package under `src/` is not installed and not run; its `docs/` explain
choices we copy in our own code (open them only when changing it). The paid path and the clock itself are skill
`v-elevenlabs-speech-to-text`.

## The three jobs

| Job | Where | What it decides |
|---|---|---|
| **Time the read for free** | `audio/local_words.py` writes Scribe's shape; `audio/scribe_words.align` takes it unchanged | G6's clock without credits, judged by the same coverage gate |
| **Did the clip say its line?** | `training/video_qa.py` uses the local transcriber when faster-whisper is installed; `videolane/ingest.voiced_spans` hears a voice with Silero VAD through faster-whisper, else a harmonicity check | an LTX clip that drops, adds or garbles its line goes down the repair ladder (P-5) |
| **Does the master say the script?** | transcribe the delivered master's audio and compare with the script's words | a missing or doubled line after assembly (a clip-spoken line heard twice, or not at all) |

## Procedure

1. **Is the engine here?** `python3 -c "import faster_whisper"`. If not, it is an optional dependency named in
   `requirements.txt`; installing it changes the environment, so ask. Without it, a G6 run needs the paid Scribe path or
   waits; a clip check falls back to the harmonicity detector and says which detector ran.
2. **Run it on the exact file.** `python -m explainer_engine.audio.local_words audio/narration.wav audio/narration.scribe.json`
   (`--model small.en` is the default; a larger English model is slower on the CPU and rarely needed for a clean read).
   Long reads are decoded in chunks; FFmpeg decodes the audio, so any format the read arrives in works.
3. **Align, never trust raw text.** Feed the result to G6 (`python -m explainer_engine.episode run episodes/<id> --stage G6`)
   or to `python -m explainer_engine.audio.scribe_words`. The script's words are kept; the recogniser only lends its times.
4. **Read the coverage and the unmatched list** exactly as for Scribe; the gate (`scribe_words.MIN_COVERAGE`) does not
   change with the engine.
5. **Report honestly**: which engine and model ran, the file's sha256, coverage, and how many words are estimated.

## Rules that bite here

- **The recogniser is evidence, not text.** Never paste its words into captions, the script or the claim map; a name it
  spells wrongly is still the script's name.
- **Measured versus estimated.** A word whose time was interpolated carries `"estimated": true` (upstream calls the same
  thing `timing: "interpolated"`); sync-critical events are never hung on one.
- **Whisper puts leading silence on the first segment**, so the first word's start can be early; use word timestamps and
  check the first event of the read by ear when it is sync-critical.
- **One voice per run.** We do not diarize; a clip is checked on its own audio, the read on its own file.
- **Free means free.** No cloud engine, no upload of our audio to an unknown service; the paid recogniser is the
  ElevenLabs connector only, on the creator's word.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| coverage far under the gate on a clean read | wrong file or a different read | compare sha256 of the read and the transcript's source |
| names wrong, times fine | vocabulary | ignore for timing; if events hang on them, use Scribe with key terms |
| words found in music or noise | a mix was transcribed instead of the voice stem | run on the narration stem or the read, never on the mix |
| the clip check says "no speech" on a shouted line | VAD threshold vs a battle bed | listen; the harmonicity fallback and the VAD can disagree, report both |
| slow on a long read | CPU decode | chunks; keep `small.en`; it measured several times faster than real time on this container |

## References: when to open which

| File | Open when |
|---|---|
| `docs/transcript.md` | designing a transcript field (word index, measured vs interpolated timing) in our code |
| `docs/engines.md` | weighing another local engine (WhisperX alignment, Parakeet) and its licence before proposing it |
| `docs/decisions.md` | the reasons for chunked long-form runs with per-chunk cache and resume |
| `schemas/transcript.schema.json` | comparing our Scribe-shaped JSON with a richer transcript schema |
| `docs/security.md` | handling agent-supplied paths safely in a CLI |

Ideas kept: check the environment before a long run, dry-run before long media, cache by the file's fingerprint, never
"correct" recognised text silently, and say "not confident" instead of guessing a language.

## Not used from upstream

The package CLI and its engines (not installed; we keep one small wrapper), Japanese-first features (dictionary word
segmentation, readings, kinsoku), speaker merges, live "follow" transcription of a growing file, phrase search over
transcripts, SRT export from recognised text, and engine downloads it would trigger.
