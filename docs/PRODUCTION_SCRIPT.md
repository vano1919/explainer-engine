# The production script (D-43)

One JSON file per video is the script, the voice direction, the picture plan with its prompts, the sound plan and the edit.
Schema: [`explainer_engine/schemas/production_script.schema.json`](../explainer_engine/schemas/production_script.schema.json).
Day 1: `examples/stone_age/day1_v7/production_script.json`. Code: `explainer_engine/production/`.

## Why (root causes found in the v5/v6 review, 2026-10-16)

| Defect the creator saw | Root cause in the old flow | Fixed by |
|---|---|---|
| Pictures in the wrong order, fire shown before the fire beat | the shot list was a separate file planned for an earlier read; the story state was lifted per beat; ordering was never checked against the text | shots live inside the segment they illustrate and start on written phrases (PV-04); story events are checked at the word (PV-24, UR-29) |
| A picture that does not show its line (wrong hero, wrong prop) | prompts were written in a separate task, after the script | the picture's subject, heroes and props are written with the line (PV-07, PV-08, UR-30) |
| Duplicate and stale prompts | prompts were composed by a build script and pasted into several files | prompts are compiled from the subject by `prompt_v2.compose` and checked fresh (PV-11, PV-06) |
| Cuts and sounds off the words | times were guessed from beats and shifted when the read changed | no time is ever written by hand: `timing.py` derives every start, end and frame from the read |
| Missing assets found at render | nothing checked that a file, sound or reference existed | PV-05 before any paid call, PV-25 at the render |
| Too many picture changes | no rhythm rule on the whole video | PV-24 (UR-31) on an estimated read while writing |

## Structure

* `episode`, `voice` (provider, model, style words, pace range, tags; **never a real person's name to imitate** (PV-10); candidates for the test read),
  `world` (D-41 world spec), `look`, `cast` (hero names, hero card, props), `story` (events with their phrase, forbidden props),
  `library` (pictures that already exist), `music`, `sound_dirs`, `picture_dirs`.
* `segments[]` (S01..): `lines[]` (text, tags, tone, emotion, one emphasised word, `pause_after`, claims), `shots[]` (phrase `at`, type A/B/C,
  picture id or inline picture with `subject`/`engine`/`refs`/`edit`/`heroes`/`shows`/`props`/`speakers`, motion, bubbles), `audio` (`beds`, `sfx` on phrases).
* Engines: `existing` (a file), `gemini` (D-41 prompt, channel style refs), `pod_ref` (RunPod Qwen-Image-Edit from Gemini references), `pod_text`.

## Flow (one command line: `python -m explainer_engine.production ...`)

1. **Write a segment** (lines, shots with picture subjects, sounds together) -> `validate` (free; also runs the whole board on an
   estimated read, so a rhythm or story-state problem shows while writing).
2. `compile --write --out DIR`: fills every painted picture's prompt, writes `narration.txt`, `narration_tts.txt`, `pictures_gemini.json`, `pod_job.json`.
3. Paid steps use those files (read, pictures); each needs its price and the creator's yes first.
4. `words`: local Whisper (free) or a Scribe JSON -> `scribe_words.align` on the script's own tokens -> `pause_pad` (punctuated gaps and every `pause_after`).
5. `time`: `timed.json` = frames at the episode fps (shots tile the video exactly), bubbles, beds, sounds, music, events, picture list, findings.
6. `assemble` / `run` (`--final` refuses missing pictures): graded pictures with motion and bubbles, narration, ambience, sounds, music ducked under voice and world sounds, -14 LUFS.

## Rules (PV-xx; FAIL blocks the next step)

| Id | Rule |
|---|---|
| PV-01 | the file matches the schema (unknown fields refused) |
| PV-02 | segment ids S01.. in order |
| PV-03 | every shot's picture is defined once (inline or in the library) before it is used |
| PV-04 | every phrase (shot, bubble, sound, bed) exists in its own segment, in order; a segment's first picture starts on the segment's first word |
| PV-05 | assets: a file or an engine for every picture, references exist, sounds exist, heroes and speakers are in the cast |
| PV-06 | no two pictures with the same prompt (REVIEW: nearly the same subject) |
| PV-07 | forbidden props never shown; a prop is held by its owner |
| PV-08 | a painted picture's subject shares content with its segment (REVIEW) |
| PV-10 | voice style describes a sound, never a person; a voice must be chosen before the full read (REVIEW) |
| PV-11 | prompts are compiled from the subject (fresh) and pass the D-41 prompt lint |
| PV-12 | narration lint (N-01..N-10) on the text the voice gets |
| PV-14 | if any bed is used, the first segment names one |
| PV-20 | the read matches the script text at least 97 % |
| PV-21 | shot numbers 1..N, frame 0 start, no gap or overlap, last shot ends on the final frame |
| PV-23 | bubbles inside their shot, sounds inside the video, beds cover the video |
| PV-24 | the board rules on the timed script: STATE-1/2 story state at the word, HERO-1/2 hero of the line, RHYTHM-1..3 (at most 10 pictures a minute, no shot under 2.5 s, a change at least every 9 s), BUBBLE-1..3, CUT-1 |
| PV-25 | picture file present (REVIEW in a draft, FAIL with `--final`) |

## Voice direction

The voice block states how the narrator sounds in descriptive words (soft, deep, calm, warm, mature; emotion carried quietly). It is
a description of a sound, never "like <person>": no imitation and no cloning (PV-10, rights layer). The creator picks the actual voice
from the candidates after a short test read; the full read follows only then.

The read is made in chunks (`tts_chunks.json`, written by `compile`): whole segments, at most 900 characters each, one generation
per chunk with the same voice, model and settings, each given the text before and after it. One generation of a whole 3-minute
read drifted to another-sounding voice after about three minutes (Day 1, 2026-10-16). `production words <script> T01.mp3 T02.mp3 ...`
joins the chunks in order, and `audio/voice_check.py` lists every 15 s window whose timbre is far from the read's own median
(VOICE-1, REVIEW: listen there; a chunk that sounds like another voice is read again, only that chunk).
