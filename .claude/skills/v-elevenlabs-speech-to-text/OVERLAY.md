# Overlay for `v-elevenlabs-speech-to-text`: Scribe and the word clock (layer L17, stage G6)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from the official elevenlabs/skills, page `speech-to-text` (MIT, commit `97478d1b23`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for one job: turning our finished read into a clock.
The upstream text is this folder's `SKILL.md` (SDK, realtime and diarization examples);
`references/transcription-options.md` stays useful to check a batch parameter's name. The free local path is skill
`v-transcription-skill`.

## Why the clock matters

Everything after G6 lands on words: an event starts on its `at_word` (AV-05), a cut between two lines falls in their
pause, a map arrow draws while its phrase is spoken, a caption shows while its words are heard. The clock is measured once
from the real read and then is the only clock (RN-03). Nobody edits `audio/timing.json` by hand; a new read means a new
transcript, a new clock, and every downstream record goes stale on its own fingerprint.

## The chain

1. The read: `audio/narration.wav`, one file, the lines in the order the shots carry them (made on the creator's word,
   skill `elevenlabs-voice`). Shots whose hero speaks inside the LTX clip (D-132) are not in it; their speech is measured
   on the clip by `videolane/ingest.py` and laid in by `videolane/voice.py`.
2. The transcript: `audio/narration.scribe.json`, shape `{"words": [{"text", "start", "end", "type"}]}` in seconds. Only
   `type: word` items carry the clock; spacing and audio-event items are dropped by `scribe_words.transcript_words`.
3. The alignment: `audio/scribe_words.align` keeps the **written** words with their punctuation (the cut rules read it)
   and takes only the times from the transcript; v4 audio tags are stripped first (`strip_tags`), numbers normalised
   (`number_words`), unmatched words interpolated and marked `"estimated": true`.
4. The clock: `python -m explainer_engine.episode run episodes/<id> --stage G6` aligns, retimes every shot so the shots
   tile the read frame by frame, writes `audio/timing.json` and the record `production/stages/voice.json`.

For a loose read outside an episode:
`python -m explainer_engine.audio.scribe_words --script narration.txt --transcript scribe.json --out words.json`.

## Getting the transcript

**Free first.** `python -m explainer_engine.audio.local_words audio/narration.wav audio/narration.scribe.json` writes the
same shape from a local Whisper on the CPU; it needs the optional faster-whisper package (installing it is a dependency
change: ask first). Use Scribe when the local pass misses names or coverage stays under the gate.

**Scribe through the connector**, a paid call (credits; the module docstring of `audio/local_words.py` records a measured
rate): estimate, write it in the ledger, ask the creator. The connector's `creative_transcribe_audio` needs the file on a
flow first: `creative_create_asset_upload` with name, type and exact size, PUT the bytes, `creative_finalize_asset_upload`,
then pass that node as `connect_from`. Never read the audio into the conversation. Poll the run; never re-submit.

Settings that matter for us (check what the connector's schema exposes before relying on any):
- **word-level timestamps**: required; a segment-level transcript cannot time an event.
- **language `en`**: the narrator is US English; foreign words inside a line stay as heard.
- **key terms**: hero names, places, period words the voice was taught by IPA (EL-07); they lift coverage on exactly the
  words events hang on.
- **no diarization**: one narrator per read; clip speakers are measured per clip.
- **numbers**: whichever form, `number_words` folds "1914" and "nineteen fourteen" together.

## The gate and what to do below it

`scribe_words.MIN_COVERAGE` is the share of written words with a heard time; below it G6's row
`read_aligned_to_the_lines` is REVIEW and lists the unmatched words.

| What the list shows | Cause | Fix |
|---|---|---|
| a name misheard everywhere | recogniser vocabulary | key terms, or the local pass with the script as its prompt; the times are usually right anyway |
| a run of words missing in one place | the read skipped or changed them | listen there; re-read that sentence only (EL-08) and splice; never "fix" the script to the take |
| a tag word heard as speech | a tag read aloud | re-read the sentence; the tag was wrong for v4 |
| words after the last sentence | a silent tail decoded as words | `scribe_words.filter_silent_tail_words` drops them; check the read's end |
| every time shifted | the transcript is of another file | re-run on the exact `audio/narration.wav` (compare sha256) |

An estimated word is a guess between neighbours: never hang a sync-critical event (a gunshot, a door slam) on one; move
the event to the next heard word or listen and set `at_frame`.

## References: when to open which

| File | Open when |
|---|---|
| `references/transcription-options.md` | checking the name or meaning of a batch option before a call |
| `references/installation.md`, `references/realtime-*.md` | not needed: no SDK, no live transcription here |

## Not used from upstream

SDK and CLI calls with an API key, realtime and WebSocket streaming and its commit strategies, multichannel input,
speaker roles and speaker libraries, the medical model, and transcript text as subtitle text (captions show the script's
words on the clock, skill `v-subtitle-skill`).
