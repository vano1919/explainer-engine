---
name: visual-beats
description: Write the visual beats of a Crossworld Theories script - something new on screen wherever new information lands (a word, label, object, chart, ring, sign or camera accent), reaction-driven expression changes in dialogue, and a sound cue only where a named story event earns one. Use for every line of a production_script/3 (a /2 keeps its old metronome contract), segment by segment right after the lines are written, and whenever a cut feels like a slideshow or the sound like a machine gun.
---

# Visual beats and their cues

Rules: `docs/STORY_ENGINE.md`, section "Visual beats" (VB-00..VB-11, PV-44). Field: `lines[].visual_beats` in the
production script (`docs/PRODUCTION_SCRIPT.md`). Render: `production/beats.py` (free, deterministic); cues:
`audio/cues.py`. Agent: `.claude/agents/beat-writer.md` (stage 2b, right after the scene-writer, same segment).
Evidence for every number: `docs/research/STORYTELLING_EDITING_2026-10-19.md`.

**The /3 inversion:** nothing is included by default. A beat marks NEW information, a cue marks a STORY EVENT, and a
silent beat is the normal case, never a finding. A `production_script/2` keeps the old contract (the 1.5 s / 1.0 s
metronomes and the mandatory cue per beat) unchanged; everything below the table is /3.

The picture still changes every 3-6 s; beats fill the time between cuts. A shot start, a bubble, an accent or a data
visual is already an event, so a line that opens a shot needs one beat fewer.

Shorts carry the same layer (SS-09): a Short line that is a line of the video takes that line's beats; a Short's own
lines (hook, pointer, a bridging line) get beats of their own, and a `label` or `highlight` points at a spot inside the
Short's 9:16 crop (`crop_x`, `zoom` of its shot). PV-44 checks each Short on its own read at 170 wpm.

## Choosing the beat from the words

| The narrator says | Beat |
|---|---|
| a concrete thing (matches, skis, a lens) | `prop` (`thing`, a cut-out `asset` when one exists) or `label` on it |
| a person's name | `label` on them, or `highlight` (ring) round them |
| a number (with its claim) | `chart`: `counter` (0 -> n) or `bars` (2-3) |
| a key word that is the point | `text` (at most 4 words, capitals) |
| no / not / without / fails | `symbol` `cross` |
| more, grows, rises / less, falls | `symbol` `arrow_up` / `arrow_down` |
| time: night, an hour, years | `symbol` `clock` |
| a question | `symbol` `question` |
| yes, true, it works | `symbol` `check` |
| same / plus, together | `symbol` `equals` / `plus` |
| an impact, "fast", a twist word | `accent` `punch` or `shake` |
| "this one", a detail in the picture | `highlight` at `pos` |

The table says what a beat LOOKS like, never whether it sounds: on /3 no beat carries a cue by default. Abstract lines:
show the operative word as a sign or ring the thing it is about; never decorate. A beat that does none of clarify,
emphasise, reorient, compress or contrast is cut (MO jobs). At most half a segment's beats are words; no more than
three of one kind in a row; at most two overlays on screen at once.

## Pacing on /3 (VB-01)

Place beats where new information lands, not on a clock. Hook and climax: a visual event every 3-8 s, one pattern
interrupt at 25-35 s of the hook. Body: every 10-25 s. Never more than 8 s of nothing-new while the narrator speaks
(REVIEW), never more than 15 s (FAIL); MO-01's 5 s dead-air REVIEW still applies. Rhythm is variance, not a rate
(MO-07): runs of near-equal holds read as a metronome even when each hold is "correct".

## Faces in dialogue (VB-02 on /3)

The 1 s metronome is retired. Every line with a `speaker` gets AT LEAST one `expression` change (none is a FAIL),
placed on the reaction-worthy words — the reveal, the risk, the refusal, the punchline — not on a schedule. A stretch
over 4 s without a change is a REVIEW, over 6 s a FAIL; two changes of one face less than 0.7 s apart are a flicker
(REVIEW). Kuleshov note: on the line that lands (intent `reveal`, an insult, bad news), show the LISTENER's face
(`who` != the speaker) — the same neutral close-up reads as the needed emotion because of what it is cut against, and
the listener's reaction is the line's meaning.

Expressions: neutral, curious, surprised, joyful, amused, smug, confused, doubtful, worried, scared, angry, sad,
determined, deadpan. Use only the expressions of the hero's `cast.<id>.face_sheet` (VB-09: 8-12 close-ups on chroma
green, about 10, always neutral, joyful, sad, scared, angry, surprised; painted once from the hero's reference with
`paint plan --faces` and reused in every episode). A hero who speaks without a sheet is a FAIL: give the hero a sheet
(`ref` = the hero's reference picture, `set` = the ten expressions the story needs) before writing faces; never ask for
a new full picture per face. In the render the scene's picture is zoomed in on the face and blurred, and the keyed
close-up of the current expression stands over it; before the sheet is painted the face push and emotion mark stand in.
No face point and no sheet entry = FAIL (VB-06).

## Cues on /3 (VB-08 inverted, VB-10, VB-11)

A cue is opt-in: the default is silence, and a cue without an `event` is a FAIL. The event grammar — what each event
type is FOR:

- `reveal` — a sting on the emotional turn: new information that changes what the viewer thought.
- `impact` — a hit on the beat the edit declares important: the punchline, the blow, the number that hurts.
- `transition` — a whoosh on a fast camera move or a scene change, never on a plain cut inside a scene.
- `build` — a riser under anticipation, ENDING exactly on the reveal frame it was building to.
- `diegetic` — a sound of a visible on-screen action (a door, glass, rain starting); never for an unseen object.
- `take` — the one big expression take a line (surprised, scared, angry, joyful); at most one cued take per line.
- `place` — an ambience change on a location change; one bed per place, reused on returns.

The subtractive test decides every cue: does the moment feel more connected with the sound than without it? No ->
delete it. Density and repetition (VB-10, VB-11): at most ~8 cues a minute over the video (REVIEW over 8, FAIL over
14), at most 3 cues in any 10 s (REVIEW), never the same cue sound on two consecutive cues (REVIEW; 3+ times within
30 s FAIL), and emphasis sounds (thud, chime, rise, fall) at most 1 per line (FAIL). Cues count toward AL-02's 4-20
sound events a minute. Duration and level rules stay: 20-250 ms, -36..-20 dB, never within 0.15 s of an effect (the
effect is the beat's sound), two cues at least 0.25 s apart, at most 4 layers with the voice (AL-01).

The mixer auto-varies playback: `audio/cues.py` renders 3 deterministic pitch variants per sound (1.0 / 0.94 / 1.06)
and the cue bus round-robins them, so two consecutive plays of one sound are never the identical sample (the "machine
gun" bug). Variation is no licence for density: the writer still spaces the cues; the mixer only de-mechanises them.

## Check

`python -m explainer_engine.production validate <script>`: 0 PV-44 FAIL on the estimated read, under the /3 semantics
(silent default, event-bound cues, VB-10/VB-11 density and repetition). A /2 script is checked under its own old
contract; the fixture `tests/fixtures/ep1_beats/beats_S01-S03.json` is a /2 worked example and stays one.
