---
name: voice-search
description: Cast an ElevenLabs library voice for the narrator and every speaking historical figure of a docudrama episode - a character sheet from the record and the picture, free library searches by age, sex, temperament and accent, ranking with the refusals of audio/casting.py, and the three-candidate card the creator picks from by ear. Use before any dialogue take and whenever a hero needs a voice.
---

# Voice search and casting (layer L6, stage 5)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). The VC rules live in
[STORY_ENGINE](../../../docs/STORY_ENGINE.md) (VC-01..VC-10); the code is `explainer_engine/audio/casting.py` and
`explainer_engine/audio/voice_audition.py`; the stage page is `voice-caster`. Why the age rule exists: in November 2026 a
boy scout of about thirteen was read first by an adult male voice and then by a library voice labelled `young`, which
means a young adult; the creator heard "a forty-year-old man's voice" on a child.

## Free and paid

`creative_list_voices` is free: it lists voices with preview links and spends no credits. A take
(`creative_generate_speech`), a designed voice (`creative_design_voice`) or a dialogue render is paid and needs the
creator's yes in a new message with the credit estimate (invariant 2, OR-23). The hook in `.claude/settings.json` holds
one take per call.

## 1. The character sheet, from the record and the picture

One row per speaker: sex, age band (child / teen / young adult / middle-aged / old), the apparent age in years from the
hero's approved reference picture, up to four temperament words, energy, origin and the accent the viewer should hear, role
in the story. For a historical figure the sheet comes from the claim map: a 19-year-old private from Birmingham, a 40-year-old
Saxon lieutenant, a Scottish chaplain. The picture and the record decide the age, never the role name ("scout", "runner"
say nothing). An unknown age is a question to the creator, never a guess.

**Accent policy for a US audience.** Clarity first: the narrator is a clear General American or a light British voice
chosen by the creator per series. Heroes may carry their nation's accent lightly (a British soldier sounds British; a German
soldier speaking English sounds lightly German), never as a caricature and never at the cost of intelligibility. A voice
whose accent the US viewer cannot follow is refused even if it is authentic.

## 2. The searches

- **Adult hero**: `casting.query(hero)` gives the connector arguments (gender, age filter, descriptives, accent, use case);
  call `creative_list_voices` with them and `sort: usage_character_count_1y`; if nothing returns, `casting.relaxed(q)`.
- **Child or teen hero**: never use the `age` filter (the library has no child band; `young` returns adults). Run every
  text of `casting.kid_search(hero)` with `languages: ["en"]`, with and without `gender`, and pool the results; leave the
  descriptive filters off (child voices rarely carry labels).
- **Narrator**: search by use case (narration, documentary, storytelling) and the creator's words for the series
  ("warm, low, unhurried"); listen for stamina over a long read, not a single impressive line.
- Never search by a real person's or a known character's name, "famous", or "sounds like" (VC-02, PV-10). A historical
  figure is cast from his documented traits, never as an imitation of a recording of him.

## 3. Rank and refuse

`casting.rank(pooled, hero, taken=<ids already cast>, top=5, by_usage=True)`. It refuses through `casting.eligible`: a voice
two age bands off its label (VC-05); an adult voice for a child hero or a child voice for an adult (`casting.kid_clash`,
VC-10: the description itself must say child, kid, teen, boy, girl or an age under 18, after phrases like "for kids" or
"children's books" are struck out); a famous or imitation voice; a voice another speaker already has (PV-32). Read every
survivor's description yourself: an adult actor doing a child's voice passes only if the description says it sounds like a
child.

## 4. The casting card

Per speaker, three candidates: name, `voice_id`, the age and tone the library states, accent, one line on why it fits this
person in this period, the preview link (the creator listens for free), and the credit estimate of the speaker's lines
(characters with tags times the account's rate times one take; re-check the rate before each estimate, it changes by
model and plan). The creator picks by ear (VC-03); nothing is generated before his pick and his yes.

## 5. After the pick

Write the voice into `cast.<id>.voice.voice_id` (and the narrator into `voice`), measure the free previews with
`audio/voice_audition.py` (VC-06, VC-07: two cast voices must differ by one of BP-138's margins), register a new channel
voice only with the creator's word (VC-08), and save the chosen ids and his message id to project memory so later episodes
of the series reuse them.

## Traps

- A library voice that is perfect for one line and wrong for a long read (fatigue, drift): test a full chunk (EL-02).
- Two heroes who sound alike in a scene: the viewer loses who speaks; casting must separate them (VC-04).
- Plan limits: a library voice can fail with `402 paid_plan_required` on a plan that cannot use it; the card says so.
- Voice design (paid) only when no library voice fits, and only after the creator agrees with the estimate.
