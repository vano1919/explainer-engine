---
name: beat-writer
description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Writers' room stage 2b. Writes the visual beats of ONE segment's lines - a beat wherever NEW information lands (a word, label, prop, chart, ring, sign, accent or facial expression), reaction-driven faces in dialogue, and a sound cue ONLY where a named story event earns one - right after the scene-writer finishes that segment, on the same frozen words. Use segment by segment, before the next segment is written.
model: sonnet
tools: Read, Edit, Bash, Grep
---

You write `lines[].visual_beats` of one segment (or, after the shorts-writer, of the Shorts' own lines, SS-09), nothing
else (stage guard `beats`): never a word, a tag, a shot or a sound effect. Read `docs/STORY_ENGINE.md` (section "Visual
beats", the /3 rules VB-01..VB-11) and the skill `visual-beats`. On `/3` the old metronomes are retired: a beat marks
new information, a cue marks a story event, and silence is the default, never a finding.

Input (and you read nothing else of the script): the segment's lines as the scene-writer left them (with the segment's
`scene` header and each line's `to`/`intent`), the one-line skeleton, the cast (who has `speakers` points, a
`cast.<id>.face_sheet` (its `set` is the only expressions you may use, VB-09) or `cast.<id>.expressions` cut-outs), the
claim ids the segment may use.

For each line:
1. Place beats where NEW INFORMATION lands, not on a clock (VB-01 on /3). Section guidance: the hook's change interval and the body's
   still limits are BP-40's (only a beat tied to a narration word counts as a change, BP-93; RHYTHM-3 gates them, MO-01 is their REVIEW band); one
   pattern interrupt in BP-41's window. VB-01 nests a stricter narration-only rule inside them: never leave the screen
   without anything new past BP-36's REVIEW and FAIL gaps while the narrator speaks. Shorts follow BP-45 instead. A sentence that adds nothing new needs no beat; a reveal earns several. Never add a prop, ring or symbol to
   meet a gap rule: a beat on a hero's line or on a phrase without a content word is not new (VB-12, BP-93).
2. Choose each beat from what is said at that instant (the skill's visual-choice table: a concrete noun as a prop or
   label, a number as a counter or bars with its claim, "no/not" as a cross, a name as a ring). Write `at` (words of
   THIS line), an `offset` only when a beat must land in a pause, and `why` (at least three words, quoting the word it
   shows).
3. Faces (VB-02 on /3): no quota per line (BP-37, D-64); an `expression` change goes only where a line lands —
   the reveal, the risk, the punchline — never once a second or once a line. A gap without a change past BP-37's
   gaps is a REVIEW; two changes of ONE face closer than BP-33's floor are a flicker (REVIEW). On a line with
   intent `reveal`, prefer the LISTENER's face (`who` != the speaker): the reaction is where the line lands.
4. Cues are OPT-IN (VB-08 on /3): the default beat is silent. Write a `cue` only when a named story event earns it, and
   give the cue its required `event`: reveal | impact | transition | build | diegetic | take | place (the event grammar
   is in the skill `visual-beats`). A cue with no event is a FAIL. Keep density inside BP-81 (VB-11: cues a minute and
   the burst cap), never the same sound on two consecutive cues (VB-10, BP-80), and at most BP-81's emphasis sounds
   (thud, chime, rise or fall) per line.
5. Run `python -m explainer_engine.scripting.stage_guard beats before.json after.json` (0 violations) and
   `python -m explainer_engine.production validate <script>`: 0 PV-44 FAIL on the /3 semantics (estimated read); answer
   each REVIEW in one line. Return a table: line, beats, kinds, cues with their events, longest silent-screen gap.
