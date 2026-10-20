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
silent beat is the normal case, never a finding. A `production_script/2` keeps the old contract (the /2 metronomes of BP-36 and BP-37
and the mandatory cue per beat) unchanged; everything below the table is /3.

The picture changes within BP-40's still limits (a visual beat counts as a change, D-59); beats fill the time between
cuts. A shot start, a bubble, an accent or a data visual is already an event, so a line that opens a shot needs one beat
fewer.

Shorts carry the same layer (SS-09): a Short line that is a line of the video takes that line's beats; a Short's own
lines (hook, pointer, a bridging line) get beats of their own, and a `label` or `highlight` points at a spot inside the
Short's 9:16 crop (`crop_x`, `zoom` of its shot). PV-44 checks each Short on its own read at 170 wpm, except VB-01's cadence: a Short's pace is BP-45's (PV-34),
where its beats count as events.

## Choosing the beat from the words

| The narrator says | Beat |
|---|---|
| a concrete thing (matches, skis, a lens) | `prop` (`thing`, a cut-out `asset` when one exists) or `label` on it |
| a person's name | `label` on them, or `highlight` (ring) round them |
| a number (with its claim) | `chart`: `counter` (0 -> n) or `bars` (2-3) |
| a key word that is the point | `text` (BP-38's word cap, capitals) |
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

Place beats where new information lands, not on a clock. The hook's change interval and the body's still limits are
BP-40's (one pattern interrupt late in the hook); RHYTHM-3 gates them and MO-01 is their REVIEW band. VB-01 nests a
stricter narration-only dead-air rule inside them: BP-36's REVIEW and FAIL gaps of nothing-new while the narrator
speaks (in the hook BP-40 is the stricter one, in the body VB-01). A held picture counts as long as its beats
(an expression, a label, an accent) keep landing (BP-41). Rhythm is variance, not a rate
(MO-07): runs of near-equal holds read as a metronome even when each hold is "correct".

## Faces in dialogue (VB-02 on /3)

The 1 s metronome is retired. Every line with a `speaker` gets AT LEAST one `expression` change (none is a FAIL),
placed on the reaction-worthy words — the reveal, the risk, the refusal, the punchline — not on a schedule. A stretch
without a change past BP-37's gaps is a REVIEW, then a FAIL; two changes of one face closer than BP-33's floor are a
flicker (REVIEW). Kuleshov note: on the line that lands (intent `reveal`, an insult, bad news), show the LISTENER's face
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
delete it. Density and repetition (VB-10, VB-11): cues a minute over the video and the burst cap are BP-81's,
never the same cue sound on two consecutive cues (REVIEW; the repeat window and count are BP-80's), and emphasis sounds
(thud, chime, rise, fall) at most BP-81's count per line. Cues count toward AL-02's sound events a minute. Duration and level rules stay: 20-250 ms, -36..-20 dB, never within BP-39's cover time of an effect
(the effect is the beat's sound), two cues at least BP-39's gap apart, within BP-56's layer cap (AL-01).

The mixer auto-varies playback: `audio/cues.py` renders 3 deterministic pitch variants per sound (1.0 / 0.94 / 1.06)
and the cue bus round-robins them, so two consecutive plays of one sound are never the identical sample (the "machine
gun" bug). Variation is no licence for density: the writer still spaces the cues; the mixer only de-mechanises them.

## Check

`python -m explainer_engine.production validate <script>`: 0 PV-44 FAIL on the estimated read, under the /3 semantics
(silent default, event-bound cues, VB-10/VB-11 density and repetition). A /2 script is checked under its own old
contract; the fixture `tests/fixtures/ep1_beats/beats_S01-S03.json` is a /2 worked example and stays one.
