# Overlay for `v-animate-characters`: Acting and body motion without a rig (layer L12, stage G1 to G7)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from codepawl/creator-generalist, page `animate-characters` (MIT, commit `007290c354`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel whose bodies move in two ways only: an LTX
clip that invents the in-betweens from one start picture and a written action, or a `still_25d` living photograph where
only loose matter moves. The upstream text (keyframing in Blender, Grease Pencil and Krita) is this folder's `SKILL.md`; its `references/principles.md` and `references/overlap-acting-and-shot-planning.md` stay the most useful
as vocabulary (table below).

## What changes when nobody keys the motion

The twelve principles still decide whether a body reads as alive, but we control them only through three levers:
1. **The start picture**: the pose, the weight on one foot, where the hands are, which way the head is turned.
2. **The written action**: one verb with an object and an end state, plus the small behaviours around it.
3. **The choice of route**: a body that must perform goes to `video` (RT-02); a body that only breathes goes to
   `still_25d`, where the face is never warped (RT-06).

Everything an animator would key, we either pose in the picture, ask for in words, or judge afterwards and repair.
Blender rigs, IK and the graph editor belong to the legacy routes (D-116) and are not part of a v4.3 shot.

## Writing an action that moves well

- **Pose with an implied move** in the start picture: the weight already shifting, a hand already reaching. A
  symmetrical, square-on stance gives the model nothing to start from (the frozen statue clip). Ask for the pose in the
  picture prompt (skill `v-visual-skills-image`).
- **Anticipation**: a small opposite move first, kept small for realism ("he glances down, then pushes up onto the fire
  step"). Big cartoon wind-ups break the docudrama.
- **The head leads**: the eyes and head turn toward the thing before the body follows ("he looks up at the parapet, then
  turns his shoulders to it").
- **Weight and spacing**: say what is heavy and how it moves ("he hefts the rifle", "the sack drags"); a fall is quick, a
  rise is slow; nothing heavy floats.
- **Arcs**: arms and heads travel on curves; "swings", "sweeps", "ducks under" read better than a straight "moves to".
- **Overlap and follow-through on loose parts**: greatcoat hems, scarves, rifle slings, hair, a flag, the candle flame;
  name one so the model gives it life.
- **Staggered stops**: do not end the shot on everything freezing at once; let the breath or the coat settle after the
  body stops. The end state is a held pose with breathing, not a still frame.
- **One action per clip**; the second action is the next shot or the next continuation (VL-01, VL-03).

## Acting a historical person

- Behaviour, not emotion words: "his jaw tightens and he looks at the floor", "she folds the letter twice before she
  speaks". Upstream's acting-from-reference habit applies: picture a real person doing it, then describe what you saw.
- Restrained, period-true register: small gestures, held looks, no modern shrugs, finger guns, thumbs up or eye rolls.
- The listener carries the beat: the face on the line that lands is often the strongest shot (skill `visual-beats`).
- A speaking hero gets one line per clip and never a speaking close-up (VL-02); mouths are weak close up, so let a medium
  shot, a turned head or the listener's reaction carry speech. We do not lip-sync; LTX speaks the line itself (D-132).
- A crowd moves as a few readable groups with one shared motion (marching, turning toward a sound), never as dozens of
  individual actions; far crowds are `still_25d`.

## What a living photograph may move

A `still_25d` shot (`explainer_engine/production/layers25d.py`, chosen by `explainer_engine/production/living_director.py`)
may move the camera on one path, and loose matter: breath vapour, smoke, fog, a flag, a candle, snow, water. It never bends
a limb or a face; a face lies on one plane (RT-06), and the shot must be alive beyond the camera (BP-185). If the beat
needs a hand to move, it is a `video` shot or an insert.

## Judging the clip (the animator's checks, adapted)

Watch at real speed with sound, several times, then scrub:
- **Floaty**: heavy things drift, feet slide, no contact. Rung R2 with weight words, or R3 a picture with clearer contact.
- **Robotic**: all parts stop on one frame, no overlap. R2: name the settling part.
- **Rubbery or melting**: hands or props deform. R3: a start picture with the prop already in a firm grip; or R4 an insert.
- **Frozen**: only the camera moves. R2 a stronger verb with an end state, or accept it as `still_25d` (R4).
- **Silhouette**: fill the figure black in your head; if the action is not readable, the pose or the angle is wrong (R3).
- **Pops at the cut**: a continuation must start from a settled tail frame (VL-05) and keep the motion direction (VL-11).

Write every observation (P-5); at most two generative tries per shot, then change the shot.

## Checks in code (SK-2)

`explainer_engine/episode/router.py` (route and talking checks), `explainer_engine/videolane/plan.py` (one line, camera
hand-over, continuity modes), `explainer_engine/videolane/cuts.py` (motion direction across a continuation, jump cuts),
`explainer_engine/videolane/master_qa.py` (frozen and black runs, BP-164), `explainer_engine/production/layers25d.py` (face
plane, tears, frozen runs), `explainer_engine/qa/liveliness.py` (a photo shot that stands still too long),
`explainer_engine/finish/frame_pick.py` (the stillest frame for a hand-over, BP-199).

## References: when to open which

| Need | Open |
|---|---|
| The twelve principles and silhouette reading | `references/principles.md` |
| Acting from reference, overlap on hair and cloth, planning a shot | `references/overlap-acting-and-shot-planning.md` |
| Spacing words: slow in, slow out, holds | `references/timing-and-graph-editor.md` (the ideas, not the editor) |
| Walk and march cadence for a moving group | `references/cycles-and-locomotion.md` |
| Blinks and faces, as background for what LTX gets wrong close up | `references/acting-and-faces.md` |
| Easing for a map arrow or a label move | `references/motion-design-2d.md` (then skill `cartography`) |

## Not used from upstream

Rigs, IK and FK, the graph editor and hotkeys, shape keys, Grease Pencil, Krita and OpenToonz, frame-by-frame and cut-out
animation, stepped 2D looks and smears (the hand-drawn era is legacy), lip-sync, playblasts, and the "ask four questions"
step: we ask the creator only what his words leave open (OR-22).
