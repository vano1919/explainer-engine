# Universal Rule Base

The channel-wide rules every Crossworld Theories video follows: history, science, fantasy crossovers alike. The creator
set them on 2026-10-16 (D-37). Rules marked **[code]** are checked by `explainer_engine/edit/shot_rules.py`
(`python -m explainer_engine.edit.shot_rules <shots.json> <words.json> <look.json>`); **[editorial]** rules are
checked by the editor and the creator. A FAIL blocks the edit; a REVIEW goes to the creator.

The look stays the painted style of D-27 (the creator rejected the hyper-realistic modifier on 2026-10-16). Pictures come
from the local pod (D-36); Gemini only for reusable assets (D-19, D-28). Narration is Kokoro (AUDIO_SYSTEM.md), which
also gives the word timings the cuts depend on.

## A. Narrative

| ID | Rule | Check |
|---|---|---|
| UR-01 | **Hook, 0–5 s.** The first shot is a C (extreme close-up) or a moving A. The first sentence asks the episode's concrete question and the question is asked by 5 s; no greeting, no channel name. A sound event in the first second. | [code] shot 1 type and motion, a "?" word ending by 5 s, greeting words, first word or `sound_at` ≤ 1 s |
| UR-02 | **First 30 s are fast.** At least 6 shots start in the first 30 s, and each of them stays within its type's minimum + 1 s (A ≤ 6, B ≤ 4.5, C ≤ 3.5). | [code] |
| UR-03 | **Logical arc.** Beats run in story order; each beat names its time and place. Every shot belongs to a beat and shows what the narration says over it; no unrelated mood picture. Answer early, deepen after (no withheld payoff, SE-21). Shots are contiguous. | [code] beat and sentence ids present, no gaps; [editorial] relevance |

## B. Shot grammar

| ID | Rule | Check |
|---|---|---|
| UR-04 | **Three shot types.** **A** wide/establishing: a huge world, figures tiny or absent. **B** medium/action: at most 1–2 characters doing one action. **C** extreme close-up: objects and hands only, no faces, no environment. | [code] type is A, B or C; [editorial] the picture matches its type |
| UR-05 | **ABC sequencing.** A beat runs A → B → C; B → C → B inside one action and C → A after a revelation are fine. Never three shots of one type in a row. A beat after the first 30 s should open on A (UR-02 keeps long A shots out of the opening). | [code] three in a row = FAIL; a later beat not opening on A = REVIEW |
| UR-06 | **Faces: recognisable first, else faceless.** If the character has a reusable caricature (`look.caricatures`), the face is shown in B as our sprite over a pod plate. Else (no caricature, or the pose, action or object breaks UR-04 or UR-07) the figure is faceless: from behind, in silhouette, in profile in shadow, or hands with a signature prop (Einstein's spectacles, Curie's glass vials, Tesla's coil sketch). A pod prompt never names a cast member and never asks for a face. | [code] every B has `caricature:<name>` (the name must be in the look) or `faceless`; cast names and face words in prompts (a negated "no faces" is allowed) |
| UR-07 | **Painted style, one suffix.** Every pod prompt ends with the episode's style suffix (`look.style_suffix`) after its mood clause. Banned: hyper-realistic, photo-realistic, photo/photography, Unreal Engine, Octane, 3D render. Pod figures keep natural proportions; exaggeration belongs only to our own cast sprites, which are graded to their plate (saturation, black level, warm/cool tint, contact shadow) so the line styles do not clash. | [code] suffix and banned words; [editorial] the sprite grade |

## C. Mood: emotion → light → colour

| ID | Rule | Check |
|---|---|---|
| UR-08 | **The topic sets the palette range.** Each episode's `look.json` lists 5–7 colour names per story phase, and every shot names 1–4 colours from its phase. The palette moves with the story, so the colour itself tells the arc (Stone Age: ochre, umber, charcoal, fire amber, river teal; copper green in Month 1; iron grey and furnace orange in Year 1; electric white in Years 2–10). | [code] |
| UR-09 | **Every shot has one emotion,** from a fixed list: discovery, fear, tension, joy, humour, calm, sorrow (`explainer_engine/edit/moods.json`). The emotion picks the key light, the colours inside the palette and the contrast; its mood clause goes into the pod prompt and its grade (lift, saturation, warmth, contrast, vignette) into the compositor. The drawn style must still create the mood. | [code] emotion in the list; the clause in every new prompt |
| UR-10 | **Mood continuity.** The emotion changes at a beat boundary or on a sound event; light direction stays the same within a beat. | [code] a change inside a beat without `sound` = REVIEW; [editorial] light direction |

The emotion table (the canonical values are in `moods.json`):

| Emotion | Key light | Colour inside the palette | Contrast |
|---|---|---|---|
| discovery | one warm source, rim light, light shafts | warm highlights against cool shadows | medium-high, one bright focus |
| fear | low and hard, from below or behind | cold, desaturated, one warm accent at most | low-key, deep blacks |
| tension | side light through dust or haze | dusty warm earth tones | high |
| joy | high warm light, golden hour | saturated warm, open sky | high-key |
| humour | bright even daylight | clean, light | medium |
| calm | blue hour or embers | cool with a small warm glow | low |
| sorrow | overcast, flat | grey-blue, desaturated | low |

## D. Editor and timeline

| ID | Rule | Check |
|---|---|---|
| UR-11 | **Duration ranges.** A 5.0–7.0 s, B 3.5–5.0 s, C 2.5–4.0 s (the last shot may hold longer as a tail). | [code] |
| UR-12 | **Cut only in a pause.** A cut falls inside a narration pause after a comma, period, colon, semicolon or question mark, at least 0.05 s after the word before and 0.05 s before the next word (Kokoro word timings). Never inside a word, never between two words without punctuation. `solve_cuts` places cuts by dynamic programming over the pauses; if no placement exists: hold a shot longer within its range, merge two shots, or add a 0.3–0.6 s pause at the nearest comma, in that order. | [code] |
| UR-13 | **Ken Burns.** Zoom stays within 1.00–1.15. A: a slow horizontal pan (≤ 6 % of the width per 5 s) at one zoom between 1.05 and 1.08. B: a slow push-in (1.00 → ≤ 1.10). C: static or a pull-out (≤ 1.08 → 1.00). No camera shake. | [code] |
| UR-14 | **Transitions.** Hard cuts by default, at least 90 % of all transitions. A 1.0 s cross-dissolve only where the shot marks `time_jump` or `place_change` (Day 1 → Week 1, a new valley). | [code] |
| UR-15 | **Sound at cuts.** A swish or foley on a cut comes from the sound library (D-34) and never masks a word; music sits under the narration with ducking (AUDIO_SYSTEM.md). | [code] the id is in the library manifest; [editorial] masking |

## The shot record

```json
{"id": "d1-04", "beat": "rules", "phase": "day1", "type": "B", "emotion": "joy", "start": 10.611, "end": 14.899,
 "sentences": [6], "motion": {"kind": "push", "z0": 1.0, "z1": 1.06}, "transition": "cut",
 "picture": "d1_plate_riverbank", "source": "new", "face": "caricature:darwin", "palette": ["ochre", "river teal"],
 "prompt": "medium shot of a river bank ..., golden hour light, ..., painterly storybook illustration, ...",
 "sound": "pop_in__v1"}
```

Optional fields: `time_jump`, `place_change`, `transition_seconds`, `sound_at` (seconds into the shot), `tail`
(the last shot), `grade` (copied from the emotion). The first worked example is
`examples/stone_age/day1_v1/` (built by its `build_shots.py`, 39 shots, 0 FAIL).

## Where the numbers come from

The durations, the 1.15 zoom, the 90 % hard cuts and the cut-on-pause rule are the creator's channel style (D-37), not
research findings: the seed research rejected a universal cut rate (SE-20), so they are judged by the channel's own
retention curves (PUBLISHING_AND_ANALYTICS.md) and changed only on that evidence. The first-30-s slack (minimum + 1 s),
the pan speed and the 0.05 s cut margin are engineering defaults.
