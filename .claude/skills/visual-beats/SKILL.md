---
name: visual-beats
description: Write the visual beats of a docudrama script on the frozen words - what new thing appears on screen where new information lands (a date and place chip, a name label, a sourced document or object insert, a reaction, an evocative detail, a camera accent), the listener's face on the line that lands, and a sound only where a visible story event earns one. Use segment by segment right after the lines are written, and whenever a cut feels like a slideshow or the sound like a machine gun.
---

# Visual beats in a docudrama (layer L7 with L4, stage 2b)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Rules: VB-00..VB-12 and PV-44 in
[STORY_ENGINE](../../../docs/STORY_ENGINE.md) ("Visual beats"); field `lines[].visual_beats`
([PRODUCTION_SCRIPT](../../../docs/PRODUCTION_SCRIPT.md)); render `production/beats.py`; cues `audio/cues.py`; stage page
`beat-writer`. Evidence for every number: `docs/research/STORYTELLING_EDITING_2026-10-19.md`.

## On a v4.3 script (D-131), read first

The beat stage writes, per shot, `sound_events` (each with its `class` and a word anchor `at_word`, so it follows the read),
`intentional_silence` (a sentence) and `sound_design`; every visible event gets one audio decision (AV-01..AV-08,
`episode/events.py`), and a word alone never earns a sound (AV-07). How: the
[sound guide v2](../../../docs/sound_guides/SOUND_INTEGRATION_GUIDE_v2.md). Older lane names from before 2026-11-12 are
legacy for the episodes already made.

## The rule of the layer: nothing by default

A beat marks **new information** tied to a word of the line (VB-12, BP-93); a cue marks a **visible story event**; a silent
beat is normal and never a finding. Never add a beat because a clock asks for one; a long hold is fixed by a cut or a camera
move the story asks for, or accepted as a REVIEW. A shot start, a reaction cut or an insert is already an event, so a line
that opens a shot needs one beat fewer. Rhythm is variance, not a rate (MO-07).

## What a docudrama beat looks like

Our pictures are realistic frames in the series film's look, so the beat vocabulary is the documentary's, not the cartoon's:

| The line brings | Beat | Notes |
|---|---|---|
| a new time or place | **date and place chip** (`text`, small, period type) | once per jump, never over a face |
| a person first named | **name label** (`label`) on him, a lower third | first appearance only; the record's rank and name |
| a number with its claim | **number on screen** (`chart` counter, or `text`) | the number is shown when it matters (ED-10, BP-38's word cap) |
| a real document, letter, order | **document insert** of the sourced original, or a hero's hands holding a prop clearly in the scene | never an invented paper shown as genuine (invariant 5) |
| an object that matters | **object insert** (`prop` or a cut to an evocative insert) | the planted prop of ST-06 gets its insert both times |
| a reveal, an insult, bad news | **the listener's face** (`expression`, `who` != speaker) | Kuleshov: the listener's reaction is the line's meaning |
| an impact, a shot fired | **camera accent** (`accent` punch or shake) | sparingly; tied to the visible event |
| "here", a detail in the frame | **highlight** at a position | rare in realism; prefer a push-in cut |
| geography, distance, a front | **map insert** (route `map_action`, made last) | only when the place is the point |

Abstract lines get no decoration: show the operative thing or let the shot hold. A beat that does none of clarify,
emphasise, reorient, compress or contrast is cut (MO jobs). At most half a segment's beats are words, no more than three of
one kind in a row (VB-05), at most BP-82's overlays at once (VB-07).

## Pacing (VB-01 on /3)

Beats land where new information lands. The hook's change interval and the body's still limits are BP-40's, with BP-36's
narration-only dead-air gaps nested inside (in the hook BP-40 is stricter, in the body VB-01). A held picture keeps
counting while its beats (a reaction, a label, an accent) keep landing (BP-41). Living photographs (`still_25d`, D-131) carry
slow motion of their own, which is not a beat; their sub-shots follow BP-109.

## Faces in dialogue (VB-02 on /3)

No quota per line. Place an expression change only where a line lands: the reveal, the risk, the refusal, the joke. A
stretch with no change past BP-37's gaps is a REVIEW; two changes of one face closer than BP-33's floor are a flicker. On
the line that lands, cut to the listener. In a reenactment the "expression" is a reaction shot of the listener (a new clip
or a held frame), drawn from the hero's sheet and the scene master; a hero who changes expression needs his sheet
(VB-09, VB-06); never ask for a new full picture per face.

## Cues (VB-08 inverted, VB-10, VB-11)

A cue is opt-in and names its event; a cue without one is a FAIL.

- `diegetic`: the sound of a visible action (a rifle bolt, boots on frozen mud, a mess tin, a match); the docudrama's main
  cue, and the way to reach the creator's floor of at least three effects per scene.
- `place`: an ambience change on a change of place; one continuous bed per place, reused on returns.
- `reveal`: a sting on the emotional turn, rare in a docudrama.
- `impact`: the blow, the shot, the number that hurts.
- `transition`: on a scene change or a fast move, never on a plain cut inside a scene.
- `build`: a riser that ends exactly on the reveal frame.
- `take`: one big expression take per line at most.

The subtractive test decides: is the moment more connected with the sound than without it? If not, delete it. Density and
repetition: BP-81 (cues a minute, the burst cap, emphasis sounds per line) and BP-80 (no same sound on consecutive cues);
cues count toward AL-02's events a minute (BP-49); duration and level within BP-64, never within BP-39's cover time of an
effect, inside BP-56's layer cap (AL-01). The mixer renders three pitch variants per sound and round-robins them so two
plays are never identical; variation is no licence for density.

## Shorts

A Short line taken from the video keeps that line's beats; a Short's own lines get beats of their own, placed inside its
9:16 crop (SS-09). PV-44 checks each Short on its own read, with BP-45's pace (PV-34).

## Check

`python -m explainer_engine.production validate <script>`: 0 PV-44 FAIL on the estimated read under the /3 semantics. A /2
script keeps its old contract (the metronome of BP-36 and BP-37 and a cue per beat); the fixture
`tests/fixtures/ep1_beats/beats_S01-S03.json` is a /2 worked example and stays one.
