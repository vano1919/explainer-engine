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

RETIRED by D-39: narration is ElevenLabs, and the Kokoro CLI below refuses to run (it exits 1). History, how that path worked: `python -m explainer_engine.audio.narrate --spec <voice.json> --text <narration.txt> --out <dir>` was the one path:
spec -> timed render -> `base.wav` + `words.json` -> alteration -> `narration.wav` + `voice_report.json` (pitch, pitch
spread, pace, level of both, the timing check). WAVs are not committed.

## Music, ambience, silence
One music state per scene group, spotted on scene or beat boundaries with a planned no-music stretch (BP-62), ducked under
speech to the LU floors of BP-52 with the dip of BP-53; ElevenLabs music or a per-track verified free library (D-52) with
per-file records; no commercial tracks and no AI-music-as-the-main-focus (disclosure trigger, V-02). Planned silence (a held
beat) is declared in the storyboard; an inserted pause is room tone, never digital zero (BP-60); unintended silence (P-95)
has no scanner yet beyond `audio/dropouts.py`.

## Audio event contract (v1; schema in Phase 3)
**Superseded** for jobs with a sound director manifest by `sound_mix_manifest/2` ([CONTRACTS](CONTRACTS.md), CN-16), which is
derived from the spine and the timed script, never written by hand; the block below is the v1 idea it grew from and still
describes the old mono path's events.
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

### Shot-to-audio matrix (BP-160, SD-12)
What a shot's audio is made of follows its lane. The table is rendered from `MATRIX` in `audio/sound_director.py` (`python -m
explainer_engine.audio.sound_director matrix write`) and a test keeps the two equal; the code is its one home. Legend: native `bed` =
the clip's own audio kept as a `native` bed under the scene bed (BP-160's offset) and ducked, never its speech; `dialogue` = the
clip is the line, in a spine window (D-88), centred; spots `foley`/`loudest` come from the shot card's `sound`; `cues only` = VB-08
cues; perspective follows the shot size (BP-122), `no` = centred and dry.

<!-- sd-matrix:begin -->
| lane | native clip audio | scene bed | spots | perspective |
|---|---|---|---|---|
| KEYFRAME_LTX | bed | scene | foley+loudest | yes |
| DIALOGUE_CU | dialogue | scene, ducked | none | near, dry |
| HOST_COMMENTARY | none | hosts' room tone | none | no |
| DRAMA_BLOCKED_3D | none | scene | foley | yes |
| ATMOS_BROLL | bed if present | scene | loudest | yes |
| MAP | none | neutral room tone | cues only | no |
| COMPENSATOR | none | neutral room tone | cues only | no |
| STILL_HOLD | none | scene | foley, one | yes |
| none (D-43) | none | timed beds | timed sfx | mid |
<!-- sd-matrix:end -->

**Dialogue route (D-90, supersedes card A3's native voice; amends D-88).** A `dialogue` row above is a character's line read first with
its fixed ElevenLabs voice; the take conditions the clip and its length is the window. The code still reserves post-hoc windows (D-88)
until P6/P7 wire the audio-in; SD-12 checks the same matrix either way.

Commands: `python -m explainer_engine.audio.sound_director plan <job> [--library DIR]` writes `audio/sound_mix_manifest.json` and
`audio/sound_director_report.json` (findings, every inferred choice, dropped vacuums); `check <job> [--stems DIR] [--strict]` runs
the plan-time half on the manifest and, with the rendered stems, the render-time half. A room tone the library lacks is generated
procedurally (free, seeded, circular) and registered as `procedural` in the library root passed in. The presence-band dip is
calibrated on the measured band gap: a Q 1.2 bell dips its centre by far more than the 1-4 kHz band as a whole (3.5 dB at 2.2 kHz
moves that band's share by 1.4 dB), so `acoustics.dip_centre_for_gap` derives the centre depth from the gap BP-118 asks for (SD-04
measures the gap, never the filter setting). **Limit:** the gap is 2.82 dB on the broadband synthetic fixture (floor 2.5 dB, a thin
margin) and about 1.8 dB on a mid-heavy 300 Hz-3 kHz stem, which false-REVIEWs; REVIEW accepts that, and the floor and the dip depth are
calibrated on real stems in P12a ([BP-118](SOURCED_RULES.md)).

### Free-generator gate (D8, BP-162, BP-163, SD-13)
The order for a new music, sound-effect or room-tone take is **library, then an admitted free generator, then the ElevenLabs
connector**; the narrator stays on the connector (no REST client). Today no generator is admitted, so the chain of D-52 is
unchanged. A free (open-model) generator is admitted for one kind (`music`, `sfx`, `room_tone`) only through
`assets/audio/generator_admission.json`, which `python -m explainer_engine.audio.generator_gate admit` writes only with the
creator's recorded word (`--creator-ref` = his message id, which must name a `generator_admit` record for `<generator>:<kind>`:
`python -m explainer_engine.governance ok generator_admit <generator>:<kind> <message id> "<his words>"`), the blind sheet he
answered with its `sheet_key.json` (made for this very report) and a report that passes. Flow:
1. `measure` takes (`<prompt id>__s<seed>.wav`, three seeds per prompt) against the library's ElevenLabs items of the same kind:
   per take the duration, silence share, clipped share, DC offset (reported, not judged) and, for a loop, BP-58's seam; across
   prompts the variety (`voice_audition.mfcc_embedding`, one home) against the reference set and near-duplicate seeds. The
   numbers are BP-163's; a technical miss takes the take out. Free: no network, no ElevenLabs.
2. `sheet` writes a blind A/B listening sheet (seeded; neutral file names; both sides levelled to a common RMS; the key is a
   separate file) for his ear: quality and prompt fit are never a number.
3. `admit` re-derives the verdict from the report's numbers and records `{generator, model, kind, report_sha256, sheet_sha256,
   prefer_rate, creator_ref, picks_for_generator, picks_total, at}` (his picks, recorded for the eye; every pair of the sheet must be answered, BP-162 has no minimum share);
   `admitted(kind)` is None without a file (`$EXPLAINER_GENERATOR_ADMISSION` or the `path`
   argument move the file, so tests never touch the real one).

Enforcement: `assets_reuse` gains the decision `generate_free` (needs the admission) and, while a kind is admitted,
`generate_new` needs `--why` naming what the free take could not do; `standards/hook.py` refuses a paid ElevenLabs music/SFX call
in that case with the same shape of refusal as the missing library record (OR-18); `audio/register.py --source-kind open_model
--model ... --admission <id>` and `sfx_library.validate` refuse an `open_model` item whose admission is missing, for another kind
or for another model (SD-13); the sound director's SD-13 runs the same `generator_gate.item_problems` over the library items a mix uses.

### Stereo mix (`assemble.build_audio_v2`)

`production/assemble.py` renders the manifest when `<job>/audio/sound_mix_manifest.json` exists and is fresh (CN-02); a stale one
stops the render (SD-15), and a job without a manifest takes the mono `build_audio` path unchanged. Narration: leveled, high-passed
(BP-118), cut around the spine's dialogue windows with the seam fade at each edge, centred (L == R). Beds and room tone: looped
(a procedural tone tiles, it is circular), faded, the scene's impulse response at the mid wet share, widened. Music: BP-62 fades,
widened, the presence-band dip keyed by the voice's duck curve, BP-53's duck. Spots: the shot's perspective (BP-122: wet share,
far high shelf, near proximity; `mid` is the midpoint of the two ends), the manifest's pan, a hit as three summed layers. A vacuum
pulls music, ambience and non-hit spots to `vacuum_dbfs` (mid-channel RMS) over a fall that never exceeds BP-53's step limit and
releases with BP-53's release time; narration, room tone, cues and hits are outside it. Cues are centred. The sum gets the old
0.5 s / closing ramps and the 0.89 peak, applied to the stems too, so they still add up to the mix. Stems go to
`<job>/audio/stems/*.wav` (narration, music, sfx, ambience, room_tone, cues, dialogue); `loudnorm` (qa/targets, now with a channel
count) makes the stereo `audio.wav`. The render half of the checks (SD-02, SD-04, SD-05 band shares, SD-06 level, the BP-52 gap in
LU on the speech stretches of the stems) lands in `assemble_report.json` under `sound_director`, with SD-14 as a pointer to the
BP-50 verdicts.

## Checks run on every mix
Numbers: one definition in `explainer_engine/qa/targets.py`, read from BP-50..BP-63, used by the mixer, the Shorts renderer
and the scorecard. Integrated loudness and true peak with their verdicts; the dialogue anchor; the voice-to-background gap
while speaking (LU on the stems); the duck's largest step; clipping; click detection at clip joins; the chunk spread and
join steps; measured pace against the target; level jumps between scenes. Reports go to `assemble_report.json`,
`scorecard.json` and the review bundle ([QA_SPECIFICATION](QA_SPECIFICATION.md)); `production_gate` gate 8 reads them.
