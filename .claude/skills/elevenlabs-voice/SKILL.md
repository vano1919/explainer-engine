---
name: elevenlabs-voice
description: Direct and buy the ElevenLabs reads of a docudrama episode - the narrator and the hero lines - right on the first take and at the lowest credit cost - voice choice by ear, v4 tags and punctuation as the only direction, chunking, the sample before the batch, one take per call, checks on arrival, splicing instead of re-reading, and reuse for Shorts. Use before every ElevenLabs call and whenever a read sounds flat, drifting, too slow or wrong.
---

# ElevenLabs reads: performance and credit discipline (layer L5, stage 3 and G6)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). The API facts come from the official
`v-elevenlabs-text-to-speech` (rewritten for our connector); what the words say comes from `narration-script`; voice search
from `voice-search`. This page owns the EL rules and the performance stage's craft.

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role voice` and follow it; likeness and licence questions are decided there (docs/EPISODE_STANDARDS.md).

## The levers we actually have

Through the connector, `eleven_v4` exposes the **voice** and the **language code** only (MARKET_RESEARCH V-29, re-read
2026-10-17; re-check with `creative_get_model_schema` when a read surprises you). The API itself has stability and
similarity on v4 and an `audio_effects` block (distance, reverb environment, filter presets such as an old radio), but none
of that reaches us unless the schema shows it; never assume a knob. So the performance lives in four things:

1. **The voice** (cast per episode in `production_script.json`, D-43; registered voices and their timbre baselines in
   `config/channel_voices.json`).
2. **The text**: punctuation, the one capital, the few tags (written by the performance stage, words frozen).
3. **The chunking**: similar sizes, cut at beat ends.
4. **The number of takes**: one, always. The tools default to four takes charged; pass `generations_count: 1`. The
   PreToolUse hook in `.claude/settings.json` refuses any other value, any paid call before the rulebook's `paid_assets`
   gate, and any picture or video request through this connector.

The read is not repeatable (the same text gives a different take), so consistency comes from short, similar chunks and from
keeping what was already good.

## Performance for a docudrama (the performance-director stage)

The narrator is a storyteller, not an announcer: restrained, close, present. Emotion comes from short lines and timing,
not volume. Heroes are people under pressure in a period: tired, cold, frightened, polite to officers.

| Moment | What to write | Avoid |
|---|---|---|
| Cold open | short sentences, one capital on the surprise, a `[softly]` or `[curious]` at the start | `[dramatically]` on every line |
| A reveal | a full stop before it, the reveal word last, at most one `...` in the beat | stacked ellipses, a pause before a punch line (BP-10) |
| A death, a cost | `[softly]`, short lines, a held `pause_after` within BP-10 | sentimental adjectives, a trembling tag on a calm voice |
| A hero's line in a clip | the line as the character would say it under that pressure, `intent` set, one tag at most | period accents spelled out, theatrical tags |
| A whisper across the wire | `[whispers]` on the hero line; distance is a sound-stage job, not a tag | `[far away]` (not performed) |

Tags describe how a line is spoken (`[curious]`, `[softly]`, `[whispers]`, `[sighs]`, `[short pause]`), never what the
speaker does (`[grinning]`, `[standing]`). A tag holds until the next one: one at a delivery change, two stacked at most.
Every tag costs its characters. No SSML on v4 (BP-14); edit marks sit on the speaker label and are stripped before the
read. `stage_guard performer` proves no word changed.

## EL rules (credit discipline and quality, EL-01..EL-13)

| ID | Rule |
|---|---|
| EL-01 | **Choose the voice by ear, first.** A calm voice cannot reliably shout; tags cannot fix the wrong voice. Listen to one sample of the same text per candidate; keep one voice per role for an episode and its Shorts (VC rules, stage page `voice-caster`). |
| EL-02 | **Test one chunk before a batch.** A middle chunk of the script, listened to (by the creator or `audio/voice_check.py`), before the rest is paid. A flat test costs one chunk; a flat batch costs the episode. |
| EL-03 | **Chunk at beat ends, in one size class**, inside BP-14's limit (the house prefers medium chunks: very short ones read unevenly, very long ones drift late). Never cut mid-sentence. |
| EL-04 | **Punctuation is the direction.** Comma a breath, full stop a stop, dash a short beat, ellipsis a held thought (rare, slows the read), no ellipsis inside a question. Too many pauses make the read slow; the target is BP-01's heard pace. |
| EL-05 | **Tags few and plain, where delivery changes**; describe speech, not action; they cost credits. |
| EL-06 | **One capital per sentence, last in it** (narration-script N-04). |
| EL-07 | **Names and places first.** Decide pronunciation before the read; for a name the voice will miss, write IPA between slashes in the line and test that one sentence first (French and German place names of the Western Front are the usual traps). |
| EL-08 | **Fix a word by re-reading its sentence and splicing it in the pauses**, at the same loudness (ED-01); never regenerate a whole chunk for one word. |
| EL-09 | **Never pay twice for the same words.** A Short's line that exists in the main read is cut from it (`words.json` gives the times, UR-12); PV-28 reports a Short whose new text runs long. |
| EL-10 | **Estimate, record, then call once** with `generations_count: 1`. Never repeat a call to retry (it charges again); at most three failures per chunk (OR-04). |
| EL-11 | **Save each take the moment it arrives** (signed links expire; OR-33): download, write to disk, record in the ledger, then the next chunk. |
| EL-12 | **Check each chunk before paying the next**: loudness within BP-59's spread of the others (ED-01), no clipped edges, words match the script, timbre within the drift check, pace inside BP-01 (PV-52). A bad first chunk stops the batch. |
| EL-13 | **A take must sound like the cast voice**: `audio/voice_check.check_against` compares timbre windows with the baseline in `config/channel_voices.json`; a window off baseline, a voice without baseline, or an unregistered voice is REVIEW and is listened to before any re-read is bought; a new channel voice needs the creator's word (VC-08). |

## Pre-flight (free, before any paid read)

0. **Sample first** (OR-19): until the creator approves the stitched two-part sample
   (`python -m explainer_engine.production.sample status <episode>`), only the sample segments are read; the hook refuses the
   rest, Shorts included. No chunk crosses the sample's end.
1. `narration_lint` 0 FAIL on the TTS text; register lint clean.
2. The chunk plan, characters counted with tags.
3. Cost = characters at the account's rate; compare with the ledger and `config/spend_caps.json`; stop at 80 %.
4. The pronunciation list for this chunk's names and places.
5. For Shorts: the lines already in the main read (cut, not paid) and the new ones.

## After the read

Chunks are levelled and their edges faded in the words stage (ED-01); Scribe gives word times (`audio/scribe_words.py`,
skill `v-elevenlabs-speech-to-text`); the clock is built from them (`episode/timing.py`). A REVIEW timbre window is heard
by a person before any re-read: most are natural emphasis, not a different voice.

## Waste we have already paid for (do not repeat)

- Shorts read as new text when their lines already existed in the main read.
- A whole day's narration re-read to replace a drifting voice before testing one chunk with the new voice.
- Reading before the script's last edit: change the text first, read once.
- Stacked tags and ellipsis chains: slow, unstable, and charged per character.
- Four takes charged by a default left in place.

## Casting by measurement, choosing by ear

Every candidate gets one test read and a measured profile (pitch median and range, rate, spectral centroid, pitch
variation, pauses, drift; `audio/voice_audition.py`); two cast voices differ by at least one of BP-138's margins (VC-04);
the creator picks from the top three (VC-03). Pace is measured on the finished read against BP-01. A real person's voice is
never imitated or cloned (PV-10).

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


## Related skills and checks

API details for the connector calls: `v-elevenlabs-text-to-speech` (reads), `v-elevenlabs-speech-to-text` (Scribe),
`v-elevenlabs-sound-effects`, `v-elevenlabs-music`; local word timing fallback: `v-transcription-skill`. Never call an
ElevenLabs endpoint straight from upstream examples: every paid call goes through the connector and its hook (one take,
library first, OR-18). Validators: `explainer_engine/validators/voice.py` (planned, W2), `explainer_engine/validators/timing.py` (planned, W2), and the existing `explainer_engine/audio/voice_check.py`.
