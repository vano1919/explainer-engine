---
name: visual-beats
description: Write the visual beats of a Crossworld Theories script - something new on screen about every 1.5 s of narration (a word, label, object, chart, ring, sign or camera accent) and a facial expression change about every second of dialogue, each tied to the word being said and each with a short light cue sound. Use for every line of a production_script/2, segment by segment right after the lines are written, and whenever a cut feels like a slideshow between picture changes.
---

# Visual beats and their cues

Rules: `docs/STORY_ENGINE.md`, section "Visual beats" (VB-00..VB-08, PV-44). Field: `lines[].visual_beats` in the
production script (`docs/PRODUCTION_SCRIPT.md`). Render: `production/beats.py` (free, deterministic); cues:
`audio/cues.py`. Agent: `.claude/agents/beat-writer.md` (stage 2b, right after the scene-writer, same segment).

The picture still changes every 3-6 s; beats fill the time between cuts. A shot start, a bubble, an accent or a data
visual is already an event, so a line that opens a shot needs one beat fewer.

## Choosing the beat from the words

| The narrator says | Beat | Cue |
|---|---|---|
| a concrete thing (matches, skis, a lens) | `prop` (`thing`, a cut-out `asset` when one exists) or `label` on it | `pop` / `tap` |
| a person's name | `label` on them, or `highlight` (ring) round them | `tap` / `pluck` |
| a number (with its claim) | `chart`: `counter` (0 -> n) or `bars` (2-3) | `blip` |
| a key word that is the point | `text` (at most 4 words, capitals) | `tick` |
| no / not / without / fails | `symbol` `cross` | `thud` |
| more, grows, rises / less, falls | `symbol` `arrow_up` / `arrow_down` | `rise` / `fall` |
| time: night, an hour, years | `symbol` `clock` | `blip` |
| a question | `symbol` `question` | `blip` |
| yes, true, it works | `symbol` `check` | `chime` |
| same / plus, together | `symbol` `equals` / `plus` | `blip` |
| an impact, "fast", a twist word | `accent` `punch` or `shake` | `thud` / `whiff` |
| "this one", a detail in the picture | `highlight` at `pos` | `pluck` |

Abstract lines: show the operative word as a sign or ring the thing it is about; never decorate. A beat that does none of
clarify, emphasise, reorient, compress or contrast is cut (MO jobs). At most half a segment's beats are words; no more than
three of one kind in a row; at most two overlays on screen at once.

## Faces in dialogue

On a line with a `speaker`, write an `expression` beat on the first word and then about one a second, each a change:
neutral, curious, surprised, joyful, amused, smug, confused, doubtful, worried, scared, angry, sad, determined, deadpan.
Follow the words: doubt on "if", surprise on the reveal, worry on the risk, smug on the punchline, a listener's reaction with
`who`. The render pushes in on the face (the picture's `speakers` point) and draws the emotion mark beside it; a hero with
cut-outs in `cast.<id>.expressions` also gets a face inset that swaps on every change. No face point and no cut-out = FAIL
(VB-06): the edit-planner then picks a picture with the speaker's `speakers` point.

## Cues

Every beat has `cue`: one of tick, tap, pop, blip, pluck, chime, whiff, thud, rise, fall (25-180 ms, default -26 dB, at most
-20 dB), or `{"sound": "none", "why": ...}`. Use `none` when a sound effect already plays at that moment (the effect is the
beat's sound; a cue would double it and pass the 4-layer limit) and for expression changes. Only one big take a dialogue
line (surprised, scared, angry, joyful) may sound, because the voice already speaks there and a tone on every change stops
drawing attention (evidence in STORY_ENGINE, VB section). Cues are at least 0.25 s apart.

## Check

`python -m explainer_engine.production validate <script>`: 0 PV-44 FAIL on the estimated read. A worked example:
`tests/fixtures/ep1_beats/beats_S01-S03.json` (Episode 1's first three segments, 49 beats, mean gap 1.2 s).
