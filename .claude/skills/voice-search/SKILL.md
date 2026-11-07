---
name: voice-search
description: Find ElevenLabs library voices for each speaking character by age, gender, temperament and accent (free listing only, no audio), and write the casting card the creator picks from. Use before any dialogue take.
---

# Voice search: cast every speaking character by age first (VC-01..VC-10)

Why this exists: on 2026-11-06 the J5 scout, a boy of about 13, was read first by an adult male voice and then by
"Ben Young Man" (library age `young` = a young adult). The creator, 2026-11-07: "yesterday a child had a 40-year-old
man's voice". The rules live in `docs/STORY_ENGINE.md` (VC rows); the code is `explainer_engine/audio/casting.py`.

Everything here is FREE: `creative_list_voices` lists voices and returns preview links; it makes no audio and spends no
credits. A take (`creative_generate_speech`), a designed voice (`creative_design_voice`) or a dialogue render is PAID and
needs the creator's explicit yes in a new message, with the credit estimate (invariant 2, OR-23).

## 1. The character sheet (one row per speaker)

From the script and the picture card, write for each speaker: `gender`, `age` (child 4-11 / teen 12-17 / young 18-35 /
middle_aged 35-55 / old 55+), the apparent age in years from the picture, up to four temperament words, energy
(low/medium/high), origin or ethnicity (accent), role. Look at the hero's card or still yourself: the picture decides the
age, not the role name ("scout" says nothing about age). An unknown age is a question to the creator, never a guess.

## 2. The searches

- Adult hero: `casting.query(hero)` gives the connector arguments (gender, age filter, descriptives, accent, use case);
  call `creative_list_voices` with them plus `sort: usage_character_count_1y`; if nothing comes back, `casting.relaxed(q)`.
- Child or teen hero: NEVER use the `age` filter (the library has no kid band; `young` returns adults). Run every
  `casting.kid_search(hero)` text (`teen boy`, `teenager`, `boy`, `kid` / `kid boy`, `child`, `little boy`, `cartoon boy`)
  with `languages: ["en"]`, with and without `gender`, and pool the results. Descriptive filters drop most kid voices
  (they carry no labels): leave them off.
- Never search with a real person's or a known character's name, "famous", "sounds like" (VC-02, PV-10).

## 3. Rank and refuse

`casting.rank(pooled, hero, taken=<ids already cast>, top=5, by_usage=True)`. It refuses (`casting.eligible`):
a voice of the wrong age (labels two bands off, VC-05), an adult voice for a kid hero and a kid voice for an adult hero
(`casting.kid_clash`, VC-10: the voice's own description must say child/kid/teen/boy/girl or an age under 18, after the
audience phrases "for kids", "children's books", "kids storyteller" are struck out), a famous or imitation voice, a voice
another speaker has (PV-32). Read each survivor's description yourself: an adult actor "doing" a kid voice is fine only if
the description says the voice sounds like a kid.

## 4. The casting card for the creator

Per speaker, three candidates: name, `voice_id`, the age and tone the library and description state, accent, why it fits,
the preview link (he listens for free), and the credit estimate of his lines. Credits: ElevenLabs bills per character of
text (about 1 credit per character on the multilingual / v3 / v4 models; Flash and Turbo about 0.5). Measured on 2026-11-06:
3 J5 lines, 126 characters, 155 credits = about 1.2 credits per character with the audio tags. Estimate = characters x 1.2
x the number of takes. He picks by ear (VC-03); nothing is generated before his pick and his yes.

## 5. After his pick

Record the cast in the episode's `cast.<id>.voice.voice_id`; measure the free previews with `audio/voice_audition.py`
(VC-06, VC-07: two cast voices must differ by a BP-138 margin). Save the chosen ids and his words to project memory.
