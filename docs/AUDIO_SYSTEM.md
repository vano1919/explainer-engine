# Audio system

Python mixes all audio; the renderer produces silent video (RENDERING_ARCHITECTURE, D-11). Targets: P-90 to P-97
(D-08), every number now read from the sourced rules BP-50..BP-63 ([SOURCED_RULES](SOURCED_RULES.md)) through
`qa/targets.py`. Louder is not better: levels are validated against measurements of the rendered file.

## Chain (ElevenLabs, D-39 / D-52)
narration script -> ElevenLabs read in chunks (skill `elevenlabs-voice`) -> word timings on the exact audio
(`audio/local_words.py` / Scribe, aligned by `audio/scribe_words.py`) -> `audio/seams.py` (chunks levelled, BP-59) ->
`audio/pause_pad.py` (pauses as room tone, BP-60) -> `words.json` -> `production time` (shots, beats, cues on the words) ->
`production/assemble.py` mix: voice levelled, beds and music ducked under the voice and under every world sound
(`audio/duck.py`, BP-53), effects and cues on their frames (BP-54) -> loudness normalised, measured with ebur128 and judged
(BP-50, BP-51) -> stereo AAC export (BP-63) -> `assemble_report.json`. Kokoro (D-12) was the free draft route and is retired;
`audio/timings.py` and `audio/visemes.py` are its leftovers; `audio/narrate.py` (legacy) needs `kokoro-onnx` installed by hand, it is no longer in `requirements.txt`.

## Levels (the gates, one home each)
| what | rule | where it runs |
|---|---|---|
| integrated loudness and true peak of the long mix, measured on the delivered file | BP-50 | `assemble` (a final render stops on a FAIL), scorecard check 2 |
| dialogue anchor: the mix at most a few LU over the narration stem | BP-51 | `assemble` (`ldr_lu`), scorecard |
| music, ambience bed and their sum under the voice, in LU on the stems | BP-52 | `qa/targets.gap_verdict` |
| pre-mix gain caps of an effect and a bed (dBFS, a proxy for BP-52, never its measure) | BP-65 | `audio/layers.py` AL-04, `production/timing.py` BED_DEFAULT_DB |
| sidechain duck: depth, attack, release, hold, no step over the level JND; every duck (music and bed under the voice, under a world sound) | BP-53 | `audio/duck.py`, `assemble.build_audio` |
| picture-synced sound on its frame, never early | BP-54 | `audio/layers.py` AL-03, `production/timing.py` SFX_EARLY_MAX, scorecard check 2 |
| an effect over speech is synced to its word or it masks it | BP-66 | scorecard check 2 |
| effects carry a purpose; at most one beat in two carries one | BP-55 | `audio/layers.py`, PV-41 |
| sound events a minute, effects and cues together (upper bound only on `/3`) | BP-49 | `audio/layers.py` AL-02 |
| simultaneity: effects of one class at once, layers in all | BP-56 | `audio/layers.py` AL-01 |
| no identical sample twice in a row; the cue bus's pitch variants | BP-57 | `audio/layers.py`, `audio/cues.VARIANTS` |
| beat cue length and level (an earcon, not a one-shot) | BP-64 | `audio/cues.py`, VB-08 |
| one-shots and loops, verified seams | BP-58 | `audio/sfx_library.py lint` |
| narration consistency: chunk spread, join step, stem range | BP-59 | `audio/seams.py`, `qa/targets.stem_lra_verdict` |
| pauses as room tone, light de-essing | BP-60 | `audio/pause_pad.py` |
| Shorts: integrated, short-term cap, true peak, no LRA gate, measured on the FINAL Short | BP-61 | `production/shorts.py` |
| music spotted on boundaries, a planned no-music stretch, short stings, its fades | BP-62 | `audio/layers.py`, `production/timing.py`, `production/shorts.music_filter` |
| delivery: stereo AAC at the bitrate and rate of the upload settings | BP-63 | `assemble.AUDIO_CODEC` (video, Shorts and the sped file of `finish/speed.py`) |

## Final narrator: ElevenLabs (D-39)
The final narration is an ElevenLabs library voice (never a clone, never a famous-person voice), generated through the
connector from the plain narration text (SCRIPTING_SPEC §8). Word times come from ElevenLabs Scribe run on the exact
audio the mix uses, aligned to the script by `audio/scribe_words.py`: the written words and punctuation stay (the cut
marks of UR-12), unheard words are interpolated and flagged `estimated`, coverage below 97 % is REVIEW. No step after
the read may move time; the alteration layer below is not used on ElevenLabs audio. Scribe returns the text with its
punctuation and each dash as its own token, so `words.json` keeps the marks the cut rules read. **Pause padding**
(`audio/pause_pad.py`): ElevenLabs reads a comma, dash or ellipsis in 0.05-0.1 s, too short to cut in (a cut needs
0.05 s from both words), and then the first-30-seconds rule (UR-02) has no legal layout. A punctuated gap under 0.26 s
gets silence inserted in its middle; no word is touched, later words move by the inserted time, and `words.json` is
rewritten on the padded audio the mix uses (Day 1: 41 gaps, +6.7 s on 170.6 s), and the inserted pause is room tone at the
read's own floor (BP-60). ElevenLabs is the only narration route (D-52); Kokoro is retired.

## ElevenLabs only (D-52): what the connector really exposes (read with `creative_get_model_schema`, 2026-10-17, V-29)
| Use | Model | Parameters the tool accepts | Notes |
|---|---|---|---|
| narration | `eleven_v4` | voice, `language_code` | no stability/style/seed; delivery comes from text, tags, chunking (skill `elevenlabs-voice`) |
| music | `eleven_music_v2_5` (node `music`) | `duration_seconds` 3-600, `instrumental`, `lyrics_type`, `lyrics` | describe mood, energy, arc, instruments, tempo, ending and what to avoid; never "like <score>" |
| sound effects | `eleven_text_to_sound_v2` (node `sfx`) | `duration_seconds` 0.5-30, `prompt_influence` 0-1, `loop` | the library first (D-34); a new sound gets a library record |

Every generation call passes `generations_count: 1` after an `estimate_only` call; the PreToolUse hook (`standards/hook.py`) refuses
four-take calls, picture or video calls, and paid calls before the episode rulebook's `paid_assets` gate. Terms (V-28): commercial
use needs a paid plan; Eleven Music's terms list media rights by plan (film, TV, radio and studio games excluded below Enterprise;
attribution required only on the Free plan; streaming distribution not on Free/Starter). The creator's plan is **Creator** (confirmed 2026-10-17): individual
use only (the creator publishes as an individual; a company or a second person using the output needs a higher plan), commercial use
allowed except film, TV, radio and studio games, streaming distribution permitted, no attribution. The terms do not mention YouTube
monetisation or Content ID, so each episode's music risk stays REVIEW with the creator's recorded decision, not an assumption. Outputs are not guaranteed unique
(ElevenLabs terms s.10), so a Content ID match is possible even for our own generations: keep the generation record.

## Voice alteration layer (D-38, Kokoro drafts only)
Kokoro-82M was the only TTS when this was written (superseded for the final read by D-39): its word timings and pauses are what the edit's cuts stand on (UR-12). The narrator's own
sound is made on top of it, cheapest step first, each step optional after the one before. The voice is data:
`assets/audio/voices/<id>.json` (schema `voice_spec.schema.json`, P-98).
1. **Blend.** Kokoro voices are style vectors; the narrator is the weighted mean of a base voice and up to three others
   (the others together weigh at most 0.5, so the base keeps the larger share). `voice_layer.narrator_style` builds the
   style array, `kokoro.create_timed(voice=<array>)` speaks it. No Kokoro voice id corresponds to a person.
2. **Pitch and tone.** ffmpeg `rubberband` at tempo 1.0, pitch -2..+2 semitones, formants preserved (deeper, same size of
   voice) or shifted (older, larger voice); then a low shelf (warmth), a high shelf, and de-essing (copied from TMR
   `mix.shape_voice`). Not a replacement for the mix's own voice shaping (P-92): this is the voice, that is the level.
3. **RVC voice conversion: specified, not built.** It needs a target voice model whose licence allows commercial use and
   whose speaker consented (`rvc.licence` in the spec, `speaker_consent: true`); the only audio we own is Kokoro
   output, so there is nothing legitimate to train a "gritty" model on today. When a model exists it runs on a pod under
   an approved cap or on CPU, and must pass the same timing checks plus an ASR word-error rate within 2 points of the
   base render and a listening check for sibilant and breath artefacts. `narrate.py` refuses a spec with `rvc` set.

**Timing contract (P-99, Q-T18).** `words.json` is measured on the *base render* (the blended voice, before steps 2-3).
Blending changes durations (measured: up to -7.5 % against `am_michael` alone), so the words file is regenerated after
the voice is chosen and the edit re-solved. Every later step keeps the length within one frame and the word onsets within
20 ms (loudness-envelope cross-correlation); audio that fails is not used, the base audio is returned and the report says
`used: base`. Only the final WAV is mixed; `words.json` stays the cut reference.

`python -m explainer_engine.audio.narrate --spec <voice.json> --text <narration.txt> --out <dir>` is the one path:
spec -> timed render -> `base.wav` + `words.json` -> alteration -> `narration.wav` + `voice_report.json` (pitch, pitch
spread, pace, level of both, the timing check). WAVs are not committed.

## Music, ambience, silence
One music state per scene group, spotted on scene or beat boundaries with a planned no-music stretch (BP-62), ducked under
speech to the LU floors of BP-52 with the dip of BP-53; ElevenLabs music or a per-track verified free library (D-52) with
per-file records; no commercial tracks and no AI-music-as-the-main-focus (disclosure trigger, V-02). Planned silence (a held
beat) is declared in the storyboard; an inserted pause is room tone, never digital zero (BP-60); unintended silence (P-95)
has no scanner yet beyond `audio/dropouts.py`.

## Audio event contract (v1; schema in Phase 3)
```json
{"schema": "explainer.audio_events", "version": 1,
 "events": [{"id": "sfx.knife_chop@w_0143", "kind": "sfx|music|ambience", "asset": "sfx.knife_chop",
   "at": {"word": "w_0143", "offset_ms": 0}, "duration_ms": 420, "gain_db": -9, "pan": 0.0,
   "fade_in_ms": 5, "fade_out_ms": 40, "priority": 2, "duck_music_db": 0, "overlap": "mix|replace|skip",
   "purpose": "clarify|humour|transition|sync", "license_id": "L-0004", "if_missing": "fail"}]}
```
Rules: SFX only where they clarify an action, reinforce a joke or aid comprehension (the purposes and the beat share of
BP-55; the old "one per 6 s" was a hypothesis and is retired); every asset has a licence record; `if_missing` is `fail` for
narration-critical sounds and `skip` only for decorative ones, and a skip is logged in the QA report. Sync check: a rendered
SFX lands on its frame inside the window of BP-54 (never early).

## Reusable sound library (D-34)
`assets/audio/library/manifest.json` (schema `explainer_engine/schemas/sfx_manifest.schema.json`) lists every sound: id
(`name__vN`), file, category (vocal, foley, music), tags, length, peak and RMS, SHA-256, source (procedural seed, Gemini TTS
model and prompt, Lyria prompt), estimated cost, licence status and review. Rules:
- Sounds are stored once, normalised to a -3 dBFS peak (peak above -1 fails validation); the mixer sets the level per event
  from the audio-event contract. Find sounds with `sfx_library.find(root, tags=[...])`.
- A model's description of a sound is a machine review only; `review.human` stays `not_listened` until the creator listens.
  Rejected sounds are hidden from `find`.
- Generated sounds carry `generated_terms_unverified` until Google's output terms for commercial use are checked.
- Gemini TTS must be called with an output-token cap (25 tokens per second of audio): one uncapped call produced 458 s.
  Plain instructions are spoken aloud; use bracketed tags (`[sighs heavily]`) for non-verbal sounds.
- Procedural foley is a placeholder level of quality; replacing a sound means adding take `v2` and rejecting `v1`.
- **Library first (OR-18, D-76):** before any new music or sound effect is generated, the library is searched and the
  search recorded (`python -m explainer_engine.assets_reuse`); the ElevenLabs hook refuses a paid music/SFX call without
  the record. What the connector does generate is registered back with
  `python -m explainer_engine.audio.register <file> --name ... --category music|foley|vocal --tags ... --model ...
  --prompt "..." --cost-usd ...` (MP3/stereo is converted to the library's mono WAV; `--one-shot` for stings, music
  defaults to a loop). Media backup: HF `datasets/vano1919/tmr-artifacts/library/audio/`.
- The analyst (Dirkus) is silent: his vocal sounds are reactions, never speech. The companion (Tick) makes mechanical sounds.

## Sound director
Blueprint phase P4 ([D-88](DECISIONS_AND_OPEN_QUESTIONS.md), contracts in [CONTRACTS](CONTRACTS.md)). The spine
(`audio/spine.py`, `audio_spine/2`) compiles the narrator read, the post-hoc dialogue windows and the frame clock; the sound
director (`audio/sound_director.py`) derives `sound_mix_manifest/2` from the spine, the timed script and `film_shots/2` (CN-02,
never edited by hand); `production/assemble.py` renders it and the render-time half of the checks measures the stems. A job
without a manifest renders through the existing mix. The sound pass is a step of `edit-planner` and owns no script field.
Every SD check reads its numbers from the rule named in the table (BP ids only, no number is copied here); a hypothesis rule
is REVIEW at most (CN-11).

| ID | Check | Rule | Severity |
|---|---|---|---|
| SD-01 | every scene has a room-tone bed over its whole span, inside the band | BP-116 | REVIEW |
| SD-02 | no window of the rendered mix under the digital-silence floor | BP-161 | REVIEW |
| SD-03 | J or L at every place/acoustic change; no butt cut between a map and a drama shot | BP-117 | REVIEW |
| SD-04 | measured presence-band gap of the background under speech | BP-118 | REVIEW |
| SD-05 | a reveal or HARD accent has a three-layer hit, onsets within `sync_ms`, layers in their band; the group onset inside BP-54's window | BP-119; BP-54 | REVIEW; **FAIL** (binding) |
| SD-06 | at most `vacuums_max` vacuums, each inside `vacuum_s`, at `vacuum_dbfs`, ending on its reveal, none over speech | BP-120 | REVIEW |
| SD-07 | spot pans inside `sfx_pan_max`, on the focal side; narration, dialogue and cues centred | BP-121 | REVIEW |
| SD-08 | one encoded layer at a time; the per-stem same-colour cap; total layers | BP-121, BP-56 | REVIEW |
| SD-09 | perspective follows the shot size; one impulse response per scene | BP-122 | REVIEW |
| SD-10 | action cuts on the beat grid while music is up | BP-123 | REVIEW |
| SD-11 | at most one motif per owner | BP-123 | REVIEW |
| SD-12 | the shot timeline and the lane matrix hold (estimated timeline, missing clip, native speech outside a window) | BP-160 | REVIEW |
| SD-13 | no free-generator take without an admission for its kind | BP-162 | **FAIL** (house) |
| SD-14 | delivered loudness and true peak (a pointer to `qa/targets`, not a second implementation) | BP-50 | FAIL (binding, existing) |
| SD-15 | the manifest is fresh against its inputs | CN-02 | **FAIL** (invariant 7) |

## Checks run on every mix
Numbers: one definition in `explainer_engine/qa/targets.py`, read from BP-50..BP-63, used by the mixer, the Shorts renderer
and the scorecard. Integrated loudness and true peak with their verdicts; the dialogue anchor; the voice-to-background gap
while speaking (LU on the stems); the duck's largest step; clipping; click detection at clip joins; the chunk spread and
join steps; measured pace against the target; level jumps between scenes. Reports go to `assemble_report.json`,
`scorecard.json` and the review bundle ([QA_SPECIFICATION](QA_SPECIFICATION.md)); `production_gate` gate 8 reads them.
