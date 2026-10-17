---
name: elevenlabs-voice
description: How to get a natural, consistent ElevenLabs read on the first try and spend as few credits as possible - voice choice, v4 audio tags, punctuation, chunk size, tests before batches, what never to re-read, how to reuse audio for Shorts. Use before every ElevenLabs call (samples, chunks, Shorts, re-reads) and whenever a read sounds flat, drifting or wrong.
---

# ElevenLabs: right on the first take, cheapest path

Facts for this project: model `eleven_v4`, voice `NOpBlnGInO9m6vDvFkFC` (Grandpa Spuds Oxley), 1 credit per character **including
tags**, concurrency 5, signed result links live 7200 s. Episode 1 used 17,353 credits: 14,778 for the 24 chunks and **2,575 for five
Shorts that re-read text the main read already contained**. Rules below come from ElevenLabs' own model guide (read through
`creative_get_model_guide`, 2026-10-17), the public v3 prompting docs, third-party guides (marked 3P, to be tested) and our own reads.

## What the connector lets you control (v4)

`creative_get_model_schema` for `eleven_v4` exposes only `voice` and `language_code`. **There is no stability, similarity, style or
seed knob and no previous/next-text context.** The levers are therefore: (1) the voice, (2) the text (punctuation, capitals, tags),
(3) the chunking, (4) the number of takes. The read is not repeatable (3P: same text gives different output), so consistency comes from
short, similar chunks and from keeping what was already good.

## Rules (EL-01..EL-12)

| ID | Rule |
|---|---|
| EL-01 | **Voice first.** The voice's character limits what tags can do (a calm voice cannot reliably shout). Pick it by listening to one sample of the same 300-character text, never by description. Keep one voice per series. |
| EL-02 | **Test before the batch.** One chunk (300-900 characters) from the middle of the script, listened to by the creator or by `voice_check`, before 24 chunks are paid. A flat or odd test costs 600 credits; a flat batch costs 15,000. |
| EL-03 | **Chunk 400-900 characters, at paragraph/beat ends**, same size class across chunks (very short prompts under ~250 characters are inconsistent; very long ones drift in the second half; 3P). Never cut mid-sentence. |
| EL-04 | **Punctuation is the direction.** Comma = breath, period = full stop, `...` = a held thought (use rarely, each one slows the read), `—` = a short beat. No ellipsis inside a question. Over-use of pauses makes the read slow (Episode 1 read at 120 wpm; target 150-165). |
| EL-05 | **Tags: few, plain, where delivery changes.** `[curious]`, `[softly]`, `[slowly]`, `[dramatically]`, `[mischievously]`; a tag holds until the next one, so one at a beat start, two stacked at most. Describe how it is spoken, not what the speaker does (`[grinning]` is not performed). Tags cost credits (a tag of 11 characters is 11 credits). |
| EL-06 | **Capitals sparingly**: one stressed word per sentence, last in the sentence (narration-script N-04). |
| EL-07 | **Numbers, names, pronunciation.** On v4 keep numbers as written in the script's normal form; for a name the voice will misread, put IPA between slashes in the displayed text (`/ˈɡœbɛkli ˈtɛpɛ/`) and test that one sentence first. |
| EL-08 | **Do not re-read to fix one word.** Fix a single bad word by re-reading only that sentence (or the chunk if the sentence is the chunk) and splice it in the pauses; never regenerate a 900-character chunk for one word. The splice needs the same loudness (ED-01). |
| EL-09 | **Never re-read what exists.** A Short, a teaser or a trailer cuts its lines **out of the main read** (cut inside pauses, UR-12); `words.json` gives the times. Only text that does not exist in the main read is paid for. The Shorts' extra hook line is the only new text. |
| EL-10 | **Estimate, then call once.** `estimate_only` first, record it in the ledger, then one generation per chunk with `generations_count: 1`. Never repeat a call to "retry" (it charges again). Max 3 failures per chunk (OR-04). |
| EL-11 | **Download immediately** (links expire, 7200 s) and re-poll the status for fresh links if they did; write each chunk to disk and into the ledger as soon as it is paid (OR-03). |
| EL-12 | **Check every chunk when it arrives, before the next is paid.** Loudness within 1.5 dB of the others (ED-01), no clipped start/end, words match the script (coverage), timbre within the drift check (`audio/voice_check`), reading speed 140-175 wpm. A bad first chunk stops the batch. |

## Pre-flight (all free, before a paid call)

1. `narration_lint` 0 FAIL on `narration_tts.txt`.
2. Chunk plan from `tts_chunks` (900-character cap), characters counted with tags.
3. Cost = characters x 1 credit; compare with the ledger cap (stop at 80%).
4. Pronunciation list for names and places in this chunk (IPA), decided now, not after the read.
5. For Shorts: confirm every line already exists in the main read; list the lines that do not (EL-09).

## After the read

Chunk loudness is levelled and the edges faded in `production words` (ED-01); the drift check reports timbre windows. A REVIEW window
is listened to by a human before any re-read is bought, because most are natural variation in emphasis, not a different voice.

## Common waste (do not repeat)

- Reading the Shorts again (2,575 credits in Episode 1) instead of cutting them from the main read.
- Reading the whole Day 1 twice to replace a drifting voice without first testing one chunk with the new voice settings.
- Reading before the script's last edit: change the text first, read once.
- Heavy tag stacking and long ellipsis chains: slow, unstable, and charged per character.
