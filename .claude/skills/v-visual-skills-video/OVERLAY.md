# Overlay for `v-visual-skills-video`: Motion prompts for the video lane (layer L12, stage G1 to G7)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from smixs/visual-skills, page `video` (CC-BY-4.0, credit Serge Shima, see `NOTICE`; commit `61a60d317f`).
Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for one generator: LTX-2.5 distilled
on Modal, image-to-video from our own start picture, with its own sound. The upstream text (a director, writer and editor
role for Seedance, Kling and Veo) is this folder's `SKILL.md`; its `references/dramaturgy.md`,
`universal-rules.md`, `fixes-and-skeletons.md` and `camera-lighting-vocabulary.md` stay usable as craft background.

## What a motion prompt is here

Nobody types the final LTX prompt. `explainer_engine/videolane/scene.py` `compose_prompt` builds it from the shot: the
`video_prompt.motion_prompt`, the start state read off the picture, the `director_brief`, the spoken line in the
speaker's voice text, a sound clause from `sound_events`, and "Nobody speaks." for a silent or narrated shot. So this page
is about writing those fields so the composed prompt works. The model and its limits: skill `v-ltxv2-video`. The shot's
purpose, size and blocking: skill `v-director-cinematic`. Acting: skill `v-animate-characters`.

## The four questions before any words

Upstream's order holds and suits docudrama: direct, then write, then edit, and only then phrase.
1. **What changes for the viewer in this shot?** A beat is a change of pressure. No change, no `video` shot: a held
   frame is a `still_25d` living photograph and costs nothing (RT-02).
2. **What does one body do, from where to where?** One primary action with its end state ("he lifts the rifle from the
   wall and holds it across his chest, muzzle up"). The picture already shows the start; the words carry the change.
3. **What does the camera do?** Locked, or one slow move that has a reason (follow the walk, settle on the face). The
   camera state at the end is the next continuation's start (VL-03 `camera_out` equals `camera_in`).
4. **How does it cut?** The `edit_plan` mode (continuation, coverage, insert), its `cut_in_reason` (VL-09), where the line
   sits and how much clean picture the clip keeps for the cut (VL-06).

## Writing the fields

- **motion_prompt**: present tense, one sentence for the action, one for the camera, one for the world moving (fog, breath
  vapour, brazier smoke, snow). Behaviour, not emotion: "his jaw tightens and he looks at the floor", never "he is
  ashamed". Open with the series film ("in the style of the film 1917 (2019)", rule 20) and keep the era line short. No
  dialogue here: the lint `KP-V4-DIALOGUE-LEAK` refuses a quoted line in it; the line comes from `audio_line_ids`.
- **Do not re-describe the hero.** The start picture carries face and costume; repeating them in words fights the
  picture and invites a second person. Name the role ("the private", "the officer") as the picture shows it.
- **The line**: one line per clip (VL-02), written in the script's `audio_lines`, voiced by the cast's
  `voice_description` (the voice-caster writes it; a missing one refuses the scene). Short enough for the clip: the
  measured read sizes it (VL-06).
- **sound_events**: every visible event in the shot gets an audio decision (AV contract D-135,
  `explainer_engine/episode/events.py`): a rifle bolt, boots on duckboards, a pistol shot into the sky. A word alone never
  earns a sound. The scene's one continuous bed is placed by the sound stage, not by the clip.
- **Negatives**: only what this shot really risks, as instances ("no wristwatch, no modern helmet"), never a category list.

## Upstream checks, mapped to ours

| Upstream check | Here |
|---|---|
| Scene formula and dramaturgy check | the scene header and its turn (skill `dialogue-scenes`), the beat map (skill `v-director-cinematic`) |
| Three-detail rule: environmental pressure, a physical micro-action, a sound or visual motif | the environmental motion sentence, the action's end state, the shot's `sound_events`; at least three effects per scene (owner floor) |
| Duration discipline | VL-06 from the measured line; a clip never longer than its edit needs |
| Character anchor repeated in every clip | the start picture plus the verbatim registry text in the PICTURE prompt (GC-04), not in the motion prompt |
| Final image rule | the end state, which a continuation's hand-over frame inherits (VL-05) |
| 14-field shot card | the shot's `edit_plan` plus its continuity card (`continuity_card/1`, CT rules) |

## Auditing a motion prompt (before money)

Return, in this order: what works; what will break the generation; missing direction; continuity risks across the cut;
the stronger fields. The common breaks:
- two actions joined by "then" or "while" (split the shot, or let the second be the next continuation);
- no end state, so the model loops or stops mid-gesture;
- a camera move and a body move competing at the same moment;
- the line too long for one clip, or a speaking close-up (VL-02);
- a pose in the start picture that implies no motion (a statue-like stance: R3, redraw the start frame);
- a document or letter shown as genuine without a source (invariant 5; "no silent document cuts").

## Failure after the clip, and the rung (P-5)

| Seen in the clip | Rung |
|---|---|
| Did half of two things | R2: one action, end state written |
| Nothing moves but the camera | R2: a stronger verb with an object and an end; or R4 as `still_25d` |
| Second person appears | R2: name the head count; R3 if the picture had room for one |
| Hands melt on the prop | R3: picture with the prop already in hand; or R4 an insert of hands |
| Line rushed or cut | re-measure the read, resize (VL-06), regenerate once |

At most two generative tries per shot; then change the shot.

## Checks in code (SK-2)

`explainer_engine/videolane/plan.py` (edit plan, one line, camera hand-over, cut reasons, three lines without a reaction
REVIEW), `explainer_engine/videolane/scene.py` (composition, voice text present), `explainer_engine/episode/router.py`
(talking and route checks at G1), `explainer_engine/episode/events.py` (every visible event has its audio decision).

## References: when to open which

| Need | Open |
|---|---|
| Beat, blocking, environment as pressure, the dramaturgy check | `references/dramaturgy.md` |
| The universal skeleton, weight at the start, contradictions | `references/universal-rules.md` |
| Face drift, melted hands, dialogue too fast, multi-clip continuity | `references/fixes-and-skeletons.md` |
| Exact words for framing, movement and light | `references/camera-lighting-vocabulary.md` |
| Turning beats into still panels before clips | `references/animatic-keyframes.md` |
| Escalation, discovery or catastrophe montage | `references/patterns-and-genres.md` (one pattern) |
| Director, writer or editor stance for a request | `references/role-modes.md` |
| A native-audio model's dialogue and effects habits, for comparison | `references/veo.md` (background only) |

## Not used from upstream

The Seedance, Seedance 2.5 and Kling model files and their syntax (labels, motion brush, multi-shot in one clip, element
binding), Veo JSON prompts, model selection tables (our model is fixed by D-132), race-and-speed recipes, commercial and
UGC formats, and multi-shot generation inside one clip: our cuts are made by the lane, one shot per clip.
