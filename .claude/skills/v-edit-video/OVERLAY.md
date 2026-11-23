# Overlay for `v-edit-video`: Editing craft for a coded edit (layer L21, stage G9)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from codepawl/creator-generalist, page `edit-video` (MIT, commit `007290c354`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for an edit that is decided in data (the cut plan, the transition plan,
the video lane's cuts) and drawn by `episode/run.py`, never by hand in an editor. The upstream text is
is this folder's `SKILL.md`; `references/editing-craft.md` is the one reference worth reading in full, and
`scripts/check_blended_cuts.py` stays usable on any export.

## When to use, when not

- Use while the cut is still data: the shots' order and lengths after the read (G6 clock), the transition plan
  (`editing/transition_plan.json`), the video lane's coverage and continuation cuts (VL-03, VL-04, VL-09).
- Use after G9 to look at the master the way a viewer will, and after a Short is cut.
- Not for running the edit (that is G9, `explainer_engine/production/assemble.py`), not for sound design (skill
  `v-design-sound`), not for grading (skill `v-color-grading-skill`), not for measuring the file (skill `v-qc-skill`).
- No desktop editor. Resolve, Premiere, CapCut and Fusion pages upstream describe tools we do not run; a fix found in
  them is translated into a change of the plan, then the runner draws it again.

## The joins we use

| Join | Where | Rule |
|---|---|---|
| Hard cut | the default between any two shots | ED-04; the camera is at rest at every cut (ED-08) |
| Dissolve | a change of place or time, a period opening | ED-04 with BP-31's length; never between two shots of one moment |
| Cut on motion | reenactment to reenactment inside a scene | the video lane's continuation hand-over (VL-03, VL-05) |
| Match cut by association | scene to scene | shape, motion or sound matched across the boundary (skill `v-director-cinematic`) |
| J cut / L cut | dialogue and narrator hand-overs | the scene's one continuous sound bed carries the cut; the voice leads or trails the picture |
| Cut to an insert | a hero line that lands, a long run of talk | hands, boots, a lamp: hides identity drift and resets the eye (VL-08, ED-14) |

Crossfades between two shots of the same moment read as a slideshow. `check_blended_cuts.py` lists them on an export;
any it finds that ED-04 does not allow is fixed in the transition plan, not in the file.

## Our procedure

1. **Read the order of truth.** The read decides time: after G6 the shots tile the narration frame by frame (RN-03).
   Never trim a shot against the read; change the script or the line, then re-time.
2. **Pace by content (ED-05).** Danger and uncertainty cut faster, wonder and reveals hold, a joke lands on the cut after
   its last word. The docudrama rhythm alternates registers: reenactment (`video`), living photograph (`still_25d`), map
   (`map_action`, made last); a run of one register too long is the first thing to break.
3. **Every cut says why** (`cut_in_reason`, VL-09): a scene opens on a place or time cut, a cut on a line follows a shot
   that set it up, a reaction cut answers the line before it.
4. **Sound across the cut.** One bed per place runs under the whole scene; a cut never restarts it. At least three
   effects per scene belong to visible events (AV contract D-135); a cut alone never earns a whoosh.
5. **Draw, then look.** Run G9, then open frames on both sides of every scene boundary and three cuts inside a scene
   (ED-07). Listen to the three loudest changes. Write what you saw in the stage note.
6. **Fix at the source.** A bad join goes back to the plan that made it: the boundary manifest
   (`editing/boundary_manifest.json`), the transition plan, the video lane cut, or the clip itself.

## Hard rules that bite at this layer

- One render path: the master comes only from the runner (P-8); no hand-joined chunks.
- No stretched, looped or frozen clip to fill a gap; `assemble_shot_clips` refuses a short clip.
- On-screen text is only what the viewer must read: a date and place chip, a name label, a sourced document. No helper
  lines, no corner captions naming the shot or the tool (the upstream rule, which we share).
- No document invented and shown as genuine; a reenacted face never proves a claim (invariant 5).
- The episode opens from black and closes to black with one constant film look (ED-04, `assemble.LOOK`).

## Failure modes and fixes

| What you see | Cause | Fix |
|---|---|---|
| Slideshow feel | dissolves inside a scene, stills held too long | hard cuts; split the hold with an insert or a 2.5D move |
| A jump inside a scene | two coverage shots of one size, or an axis cross | step the size or turn the angle (VL-04); state `axis_cross_reason` |
| A line lands on nobody | no reaction after a long hero line | add the listener's face or an insert (VL-08) |
| The map arrives too early | maps planned first | maps are made last and come in where geography is the point |
| Sound jumps at a cut | the bed restarts per shot | one bed per place in the sound plan (G4) |
| The boundary row says REVIEW | an authored hard cut with a severe visual jump | write its editorial reason or change the cut |

## Checks in code

- `explainer_engine/edit/cinematic_transitions.py`: the boundary manifest and the transition plan (ED-04).
- `explainer_engine/videolane/cuts.py` and `explainer_engine/videolane/plan.py`: the video lane's cut rules (VL-03..VL-11).
- `explainer_engine/edit/motion_lint.py`: camera continuity across cuts.
- `explainer_engine/validators/edit.py` (planned, W2): the S14 validator named in skill `film-direction`.

## References: when to open which

| File | Open when |
|---|---|
| `references/editing-craft.md` | pacing, J and L cuts, which joins Shorts use, beat sync, caption safe zones |
| `references/ffmpeg.md` | a one-off command behind a measurement (prefer skill `v-ffmpeg-skill`) |
| `references/transitions.md` | understanding a named transition before deciding it is not for us |
| `references/retime-and-speed.md` | a finished faster cut (ED-06: picture and sound together, pitch kept) |
| `references/text-and-typography.md` | a title card or a chip's typography idea; our fonts and colours still rule |
| `references/color.md` | rarely; the grade belongs to skill `v-color-grading-skill` |
| `scripts/check_blended_cuts.py` | after every G9 master and every Short |

## Not used from upstream

Picking an editor, every Resolve, Fusion, CapCut, Premiere and After Effects procedure, shakes and punch-zoom effects,
speed ramps for energy, stingers and wipes, the paid-plugin map, and the "export a preview, then full quality" loop (our
chunks and their stamps make a full render cheap to resume, RULE-R1).
