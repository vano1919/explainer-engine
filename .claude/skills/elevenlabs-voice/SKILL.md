---
name: elevenlabs-voice
description: How to get a natural, consistent ElevenLabs read on the first try and spend as few credits as possible - voice choice, v4 audio tags, punctuation, chunk size, tests before batches, what never to re-read, how to reuse audio for Shorts. Use before every ElevenLabs call (samples, chunks, Shorts, re-reads) and whenever a read sounds flat, drifting or wrong.
---

# ElevenLabs: right on the first take, cheapest path

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role voice` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Facts for this project: model `eleven_v4`, voice `NOpBlnGInO9m6vDvFkFC` (Grandpa Spuds Oxley), 1 credit per character **including
tags**, concurrency 5, signed result links live 7200 s. Episode 1 used 17,353 credits: 14,778 for the 24 chunks and **2,575 for five
Shorts whose lines were written new for the Short**. Rules below come from ElevenLabs' own model guide (read through
`creative_get_model_guide`, 2026-10-17), the public v3 prompting docs, third-party guides (marked 3P, to be tested) and our own reads.

## What the connector lets you control (v4)

`creative_get_model_schema` for `eleven_v4` exposes only `voice` and `language_code` (re-read 2026-10-17, MARKET_RESEARCH V-29).
The generation tools default to `generations_count: 4` (four takes charged): always pass 1; the PreToolUse hook in
`.claude/settings.json` refuses any other value, any paid call before the episode rulebook's `paid_assets` gate, and any picture or
video request (pictures: the creator's provider per batch in the approved paint plan, D-50; never through this connector). ElevenLabs is the only audio provider (D-52): music `eleven_music_v2_5`
(`duration_seconds`, `instrumental`, `lyrics_type`, `lyrics`) and sound effects `eleven_text_to_sound_v2` (`duration_seconds`,
`prompt_influence`, `loop`) follow the same estimate-then-one-take rule (docs/AUDIO_SYSTEM.md). **There is no stability, similarity, style or
seed knob and no previous/next-text context.** The levers are therefore: (1) the voice, (2) the text (punctuation, capitals, tags),
(3) the chunking, (4) the number of takes. The read is not repeatable (3P: same text gives different output), so consistency comes from
short, similar chunks and from keeping what was already good.

## Rules (EL-01..EL-13)

| ID | Rule |
|---|---|
| EL-01 | **Voice first.** The voice's character limits what tags can do (a calm voice cannot reliably shout). Pick it by listening to one sample of the same 300-character text, never by description. Keep one voice per role within an episode and its Shorts (voices are cast per episode, `voice-caster`, D-43). |
| EL-02 | **Test before the batch.** One chunk (300-900 characters) from the middle of the script, listened to by the creator or by `voice_check`, before 24 chunks are paid. A flat or odd test costs 600 credits; a flat batch costs 15,000. |
| EL-03 | **Chunk 400-900 characters, at paragraph/beat ends** (a house preference inside BP-14's chunk limit), same size class across chunks (very short prompts under ~250 characters are inconsistent; very long ones drift in the second half; 3P). Never cut mid-sentence. |
| EL-04 | **Punctuation is the direction.** Comma = breath, period = full stop, `...` = a held thought (use rarely, each one slows the read), `—` = a short beat. No ellipsis inside a question. Over-use of pauses makes the read slow (Episode 1 read at 120 wpm; the target is BP-01's heard pace). |
| EL-05 | **Tags: few, plain, where delivery changes.** `[curious]`, `[softly]`, `[slowly]`, `[dramatically]`, `[mischievously]`; a tag holds until the next one, so one at a beat start, two stacked at most. Describe how it is spoken, not what the speaker does (`[grinning]` is not performed). Tags cost credits (a tag of 11 characters is 11 credits). |
| EL-06 | **Capitals sparingly**: one stressed word per sentence, last in the sentence (narration-script N-04). |
| EL-07 | **Numbers, names, pronunciation.** On v4 keep numbers as written in the script's normal form; for a name the voice will misread, put IPA between slashes in the displayed text (`/ˈɡœbɛkli ˈtɛpɛ/`) and test that one sentence first. |
| EL-08 | **Do not re-read to fix one word.** Fix a single bad word by re-reading only that sentence (or the chunk if the sentence is the chunk) and splice it in the pauses; never regenerate a 900-character chunk for one word. The splice needs the same loudness (ED-01). |
| EL-09 | **Do not pay twice for the same words.** A Short's script is written for the Short (SH-02), but any line that already exists in the main read is cut out of it (inside pauses, UR-12; `words.json` gives the times) instead of being read again. PV-28 reports a Short whose new text passes 400 characters (REVIEW). |
| EL-10 | **Estimate, then call once.** `estimate_only` first, record it in the ledger, then one generation per chunk with `generations_count: 1`. Never repeat a call to "retry" (it charges again). Max 3 failures per chunk (OR-04). |
| EL-11 | **Download immediately** (links expire, 7200 s) and re-poll the status for fresh links if they did; write each chunk to disk and into the ledger as soon as it is paid (OR-03). |
| EL-12 | **Check every chunk when it arrives, before the next is paid.** Loudness within 1.5 dB of the others (ED-01, BP-59), no clipped start/end, words match the script (coverage), timbre within the drift check (`audio/voice_check`), reading speed inside the BP-01 band (P-52). A bad first chunk stops the batch. |
| EL-13 | **A take sounds like the channel's voice.** `audio/voice_check.check_against(take, sr, voice_id)` compares each timbre window of a new take with the baseline the voice has in `config/channel_voices.json` (tilt and centroid, the limits of the read-drift check); a window off the baseline, a voice with no baseline and a voice not registered are REVIEW, listened to before any re-read is bought. A new channel voice needs the creator's word (VC-08). |

## Pre-flight (all free, before a paid call)

0. Sample first ([OR-19](../../../docs/ORCHESTRATION.md)): until the creator approves the stitched two-part sample
   (`python -m explainer_engine.production.sample status <episode>`), only the sample segments' chunks are read — the hook
   refuses the rest, the Shorts' reads included. Chunk the sample's text so no chunk runs past the sample.
1. `narration_lint` 0 FAIL on `narration_tts.txt`.
2. Chunk plan from `tts_chunks` (900-character cap), characters counted with tags.
3. Cost = characters x 1 credit; compare with the ledger cap (stop at 80%).
4. Pronunciation list for names and places in this chunk (IPA), decided now, not after the read.
5. For Shorts: list the lines that already exist in the main read (cut them out, do not pay) and the lines that are new (PV-28 counts them).

## After the read

Chunk loudness is levelled and the edges faded in `production words` (ED-01); the drift check reports timbre windows. A REVIEW window
is listened to by a human before any re-read is bought, because most are natural variation in emphasis, not a different voice.

## Common waste (do not repeat)

- Reading whole Shorts as new text (2,575 credits in Episode 1) when part of their lines already existed in the main read.
- Reading the whole Day 1 twice to replace a drifting voice without first testing one chunk with the new voice settings.
- Reading before the script's last edit: change the text first, read once.
- Heavy tag stacking and long ellipsis chains: slow, unstable, and charged per character.

## Voice performance and casting (P3b 2026-10-29)

- **Cast by measurement, choose by ear.** Every candidate voice gets one test read and a measured profile (median pitch and
  range, rate, spectral centroid, pitch variation, emphasis, pauses, drift; `audio/voice_audition.py`); two cast
  voices differ by at least one of BP-138's margins so VC-04 is checkable; the creator picks from the top three (VC-03).
- **Pace** is BP-01's band, measured on the finished read. The Blueprint's slower band is conflict 2 of the curriculum;
  the one opened study (Rodero 2020, advertising) found 180 wpm best of 160/180/200, so neither side is settled.
- **Delivery is written, then tagged** (performance-director page): one stressed word per sentence, a tag where the
  delivery changes, no pause before a punch line (BP-10); an animated shot's line carries pace, loudness and colour and a
  face the lens sees (KP-17, KP-18).
- **Consistency** across takes is checked against the voice's baseline (EL-13, `audio/voice_check.py`), never assumed.

### CHECKLIST (voice)

Rendered from `explainer_engine/standards/craft_checklists/voice.json` (the one home of these ids; 
`python -m explainer_engine.standards.craft write` regenerates it, `tests/unit/test_craft_checklists.py` fails when they
differ). Every row is a hypothesis until a second source type is verified ([CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)).

<!-- craft-checklist:voice:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-VOX-01 | code | the heard pace sits in BP-01's band | the finished read + word times | BP-01 | `explainer_engine/production/validate.py` |
| CRAFT-VOX-02 | code | every candidate voice has a measured profile from one test read | voice audition record | - | `explainer_engine/audio/voice_audition.py` |
| CRAFT-VOX-03 | code | two cast voices differ by at least one measured margin | voice audition records | BP-138, VC-04 | `explainer_engine/audio/voice_audition.py` |
| CRAFT-VOX-04 | manual | the creator picks the voice by ear from the top three | casting card | VC-03 | manual |
| CRAFT-VOX-05 | critic | one stressed word per sentence; a tag only where the delivery changes | lines: tags, emphasis | PF-01 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-VOX-06 | code | no pause before a punch line; held pauses inside their limit | lines: pause_after | BP-10 | `explainer_engine/scripting/narration_lint.py` |
| CRAFT-VOX-07 | manual | chunk size, carried context, pauses by tags and punctuation | ElevenLabs requests | BP-14 | manual |
| CRAFT-VOX-08 | code | a new take matches the voice's baseline (no drift) | take vs the channel voice baseline | - | `explainer_engine/audio/voice_check.py` |
| CRAFT-VOX-09 | critic | an animated shot's line carries delivery (pace, loudness, colour) and a face the lens sees | shot card delivery + face | KP-17, KP-18 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
<!-- craft-checklist:voice:end -->

## Sourced rules (docs/SOURCED_RULES.md)

The numbers that bind a read live only in the registry (`explainer_engine/standards/sourced_rules.json`). A number changes
there, with its sources, never here.

- BP-01: the heard pace (EL-04, EL-12) is one band everywhere, measured on the finished read; the target and the accepted band
  are BP-01's, read by `validate` (PV-52), the scorecard and the engagement gate.
- BP-14: chunks at most 5,000 characters (EL-03's 400-900 is a house preference inside that limit); `previous_text` and
  `next_text` carried across chunks wherever the API exposes them (the connector does not, V-29: then same-size consecutive
  chunks stand in); pauses by tags and punctuation only, no SSML on v3/v4; speed within 0.9-1.1 (the connector has no speed
  knob on v4, so the text sets the pace and any speed-up happens in finishing under BP-02).
- BP-138: the casting margins between two cast voices (hypothesis, REVIEW; checklist above).
