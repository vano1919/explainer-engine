---
name: voice-search
description: How to find an ElevenLabs voice that fits a character's age, gender, accent and temperament before any paid take - the library's fields and their blind spots (no child label), the free search, preview measurement, the shortlist and the verification of the first take. Use whenever a speaking character needs a voice, above all a child, a teen or an elder.
---

# Voice search: age first, proof before a paid take

Route-scoped since D-116 (2026-11-06): the J5 route is Qwen assets + Blender cards + FFmpeg, no LTX. Rules by id: VC-01..VC-10 in
`docs/STORY_ENGINE.md`; code `explainer_engine/audio/casting.py` and `explainer_engine/audio/voice_audition.py`; stage page
`.claude/agents/voice-caster.md`. The narrator is the channel voice (VC-08) and is never searched.

**Why this skill exists (2026-11-06).** The J5 dialogue test picked its two voices by hand "by description" (J5_DIALOGUE_COLLAGE section 7c): the scout
got Cam, a library voice labelled `young`, and it sounded like a 40-year-old man. The library's age labels are only `young`,
`middle_aged`, `old` and `young` holds every adult under about 40; there is no child label at all. `casting.py` was not used and
had no child band. Fixed in code by VC-10 (`age_of` returns `child`, `child_problems`) and by the steps below.

## What the connector gives (free: `creative_list_voices`)

| Field | Reliable for | Blind spot |
|---|---|---|
| `gender` | male / female / neutral | missing on many library voices |
| `age` | old and middle-aged | `young` = anything up to ~40; no `child`; many voices have no label |
| `accent` / `languages` | accent filter (one language only) | free text on uploads (`en-american`, `American`, `Southern`) |
| `use_cases`, `descriptives` | temperament words (calm, raspy, gentle...) | library voices only; the AND of filters often returns nothing |
| `search` | name and description words | one plain word works (`boy`); `child kid teen` together returned 0 |
| `preview_url` | a free listen and a free measurement | one stylised sample, not a read of our line |
| `creative_design_voice` | a new voice from words | paid, creator approves the cost; designed voices were rejected as "pure AI" for the narrator |

## Procedure (all free until step 7)

1. **Traits first.** Per speaking character write `voice.traits`: gender, **age as the character is in the picture** (`child` for a boy, girl or kid;
   `young` only for a young adult; `middle_aged`, `old`), accent, 2-4 temperament words, energy, role. Look at the picture: a boy
   with a drum is `child`, a bearded commander is `middle_aged`. Never write the age from the voice you hope to use.
2. **Search.** `casting.query(hero)` gives the arguments (a child gets one plain word, no age filter). Call `creative_list_voices` with
   `sort: usage_character_count_1y`; relax with `casting.relaxed(q)`; for a child also try `girl`, `kid`, `teenager` as single words.
3. **Eligible.** `casting.rank(results, hero, taken=<ids already cast>)`: famous, taken, wrong age band and, for a child, a voice whose name or
   description does not say child, or says adult, companion or another "boy" (boyfriend, Jersey Boy), are out (VC-10).
4. **Measure the preview, free.** Download `preview_url` (curl; the proxy allows storage.googleapis.com and api.us.elevenlabs.io), then
   `voice_audition.load_audio` + `f0_track(x, sr, 60, 500)`: the median pitch. Reference points measured 2026-11-06 on previews:
   adult men 90-115 Hz; a 17-year-old boy 154 Hz; child-labelled cartoon voices 320-360 Hz. A voice sold as "boy" with a median
   near an adult man's (Austin Boy, 117 Hz) is an adult acting: out. These are observations, not a sourced rule (D-59): they order
   the shortlist and never replace the listening in step 5. Previews with effects or radio filtering can fool the tracker (octave jumps): listen.
5. **Listen.** The creator hears each shortlisted preview or a free test sample and picks (VC-03). Show name, labels, description, median pitch.
6. **Distinct.** `voice_audition.distinct` over the whole cast (VC-04, VC-07).
7. **First take is the proof (paid, estimate first, `generations_count` 1).** One short line (under 60 characters) per new voice, estimate in the ledger. Then
   verify: transcribe (`creative_transcribe_audio` or Scribe) for words, `f0_track` on the take for pitch, and a listen against the card's age. A
   take that fails the age check is not used and not re-rolled blindly: change the voice, not the seed (no seed knob exists).
8. **Record.** The chosen `voice_id`, the traits, the measured median, the take's cost and the creator's word go into the episode's cast file
   and the ledger. Reuse the same voice for the same character in every later clip (D-90).

## Credit guard

The creator's cap for the dialogue texts is 5,000 ElevenLabs credits (ledger total before this skill: 226). Estimate = characters x 1 credit,
tags count. Log the estimate before the call and the actual after. At 80 % stop and ask.

## Never

Search or describe a voice as a named person's voice, use the `famous` category, clone, or pick a voice from its name alone.
