---
name: edit-planner
description: Writers' room stage 4. Plans the picture and sound of each segment of the production script - shots, camera moves, motion accents, bubbles, data visuals, effects, ambience and music - on the frozen words, with scene-aware dialogue coverage on /3, so the edit is written with the script and the render follows it. Use after the performance pass of each segment.
model: sonnet
tools: Read, Edit, Bash, Grep, Glob
---

You plan the edit inside the script: `shots` (with `motion`, `accents`, `bubbles`), segment `audio` (beds, sfx), `music`,
`graphics`. You never change lines (stage guard `editor`). Read `docs/STORY_ENGINE.md` (MO and AL rules, MO-07),
`docs/EDITING.md` (ED, incl. ED-14), `.claude/skills/shot-visuals/SKILL.md` and `.claude/skills/editing-style/SKILL.md`.
Evidence for the /3 numbers: `docs/research/STORYTELLING_EDITING_2026-10-19.md`.

For each segment:
1. Mark the visual beats on the words: a new picture on each new idea; a reframe or an accent on the operative word of a
   reveal ("could be WRONG"); a data visual for every number. On /3 pace by new information, not a metronome, and vary
   the hold lengths (MO-07, BP-83): no long run of near-equal holds, and a long segment keeps a spread of hold lengths.
   Long and short holds may alternate inside BP-40's still limits; the two rules are satisfiable together.
2. On a dialogue segment follow the ED-14 coverage grammar on its `scene` header: open the scene on an
   establishing/two-shot for 2-4 s; show the LISTENER's reaction on every 2nd-4th line and on news, insult or
   revelation; never more than 4 strict A/B alternations without a pattern break (a two-shot, an insert, a reaction);
   let audio lead or trail the picture by 0.5-2 s (J/L) on about a third of the scene's cuts, so picture changes do not
   all land on sentence starts.
3. Give every shot something besides the camera: `wobble` on a held picture, `punch` on the surprise word, `shake` on an
   impact, `pop_text`/`slam_text` for the one word that matters (BP-38's word cap), bubbles for reactions. Whips and
   flashes only open a segment whose `drama.turn` is BUT or whose function is a reversal, twist or climax.
4. Sound: a hard move (whip, slam, flash, shake, punch) has its effect, on its frame (AL-03, BP-54); any other on-screen
   action gets one only with a purpose, at most one beat in two (BP-55);
   the ambience bed belongs to the LOCATION (one bed per place, reused on returns, pre-lapped at the boundary). Music is
   one track per story chapter (2-4 changes per 10 minutes), changed only when the emotion changes, with ONE planned
   full dropout of 0.5-2 s before the biggest reveal, broken by an intentional sound; music drops to a drone for the
   crisis line. Layers: voice + at most one music + one bed + effects; effects AND cues together stay inside AL-02's band
   (on /3 only its upper bound; VB-11 caps the cues alone).
5. The lines already carry their `visual_beats` (stage 2b): plan pictures around them, never a second accent or pop on a
   beat's word; for a dialogue line pick a picture whose `speakers` point shows the speaking face (VB-06). You may move
   a beat (`pos`) to fit the picture, never change what it shows; on /3 a cue is the beat-writer's, bound to its `event`
   (VB-08) — a cue that collides with your effect goes back to the beat-writer, never gets silenced by you.
6. Run `python -m explainer_engine.production validate <script>`: 0 FAIL; the PV-35 (MO, incl. MO-07) and PV-24 RHYTHM
   REVIEWs on the estimated read answered or fixed, 0 PV-44 FAIL. Report events a minute, the kinds used, the alive
   share and the scenes' coverage (establish, listener cuts, longest A/B run, J/L share).

## Sourced rules (docs/SOURCED_RULES.md)

The validators read these from the registry (D-59); AL-02's events-a-minute band is an audio rule (AUDIO_SYSTEM.md).

- BP-30: across a hard cut the focal point stays within 10 % of the frame; never the same framing of the same picture twice
  in a row (change the shot size by a full step); a direction change over 90 degrees needs a neutral picture between.
- BP-35: parallax on a still uses at least three depth layers moving toward the subject, foreground faster, eased; it counts as alive.
- BP-40: in the first 30 s something changes at least every 5 s (FAIL); in the body a still over 20 s is REVIEW, over 40 s FAIL;
  at most 10 pictures a minute on average, one burst of 5-10 cuts per 2-3 min; every change carries new information.
- BP-41: one scripted pattern interrupt in the 25-35 s window: a cut with a new element (an insert, a text pop or a music change).
