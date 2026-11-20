---
name: v-director-cinematic
description: Direct a docudrama history episode shot by shot - visual thesis per scene, the series film as the one style lens, blocking before framing, a shot list routed video / still_25d / map_action, keyframe and motion briefs for Gemini Task pictures and LTX clips, and a coded repair ladder when a picture or clip fails. Use for the director's book, blocking, shot lists, keyframe plans, cut geometry and every "this shot looks wrong" diagnosis.
---

# Directing a docudrama episode (layer L7, stage S4)

Built from wuwangzhang1216/DirectorSKILL v2.1 (MIT, commit `c65ae0d144`), rewritten for this channel under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). The upstream text is kept unloaded and byte-pinned in
`UPSTREAM_SKILL.md`; its `references/` stay as the library this page points into. Upstream `assets/*-template.md` were not
vendored: our templates are the schemas named below.

## What the director owns here

The writers' room hands over a frozen script (skill `story-engine`): scenes with their headers, narrator lines, hero lines,
claim ids. The director turns that into pictures someone can make with **free Gemini Task batches, LTX clips on Modal,
2.5D moves and maps**, and nothing else. A plan that needs a camera crew, a set, a paid model nobody approved, or a shot no
route can make is a wrong plan, however good it reads.

Three questions decide every shot, in this order:
1. **What does the viewer learn or feel here that they did not before?** (story function; no answer, no shot)
2. **What do bodies do in the space?** (blocking; the camera comes after)
3. **Which route can make it honestly?** (`video`, `still_25d`, `map_action`; `episode/router.py` holds the route rules)

## The docudrama grammar we shoot in

Docudrama is not a feature film with narration on top. It alternates three registers, and the cut between them is where
the episode lives:

| Register | What it shows | Our route | Typical share (D-131 targets by duration; the router measures) |
|---|---|---|---|
| **Reenactment** | People in the period doing the thing the line is about: a body moves, a hero speaks his one line | `video` (LTX-2.5 distilled, `videolane/`) | about 60 % |
| **Living photograph** | A period frame that breathes: slow push, layered parallax, fog, breath vapour, smoke | `still_25d` (`production/layers25d.py`, `production/directed25d.py`) | about 30 % |
| **The map** | Where and how far: fronts, routes, the date | `map_action` (`maps/`, laws in `maps/laws.py`) | about 10 %, made last |

Rules of the grammar (creator decisions carried into the final plan):
- **Reenactment shows actions, never claims.** A reenacted face never "proves" a fact; the claim lives in the narration
  and the claim map (invariant 5). No invented letter, telegram or newspaper is shown as genuine: a document on screen is
  either a sourced real one or plainly a prop held by a hero in the scene ("no silent document cuts").
- **Evocative inserts are the docudrama's best friend and the AI pipeline's safest shot.** Hands on a rifle bolt, boots in
  frozen mud, a match flaring, a candle in a bottle on a parapet. They carry period texture, hide identity drift, and cut
  anywhere. Plan at least one per scene.
- **Bridges between scenes go by visual association**: match a shape (a candle flame to a star shell), a motion (a lifted
  mug to a lifted lantern) or a sound (a whistle to a kettle). Build shot A's last frame and shot B's first frame together.
- **One continuous sound bed per scene** carries the cut (the sound plan, skill `v-design-sound`); plan at least three
  effects per scene that belong to visible events. The director names the events, the sound stage places them.
- **Maps are made last** and come in where geography is the point, never as filler.

## The style lens: the series film, named directly

Upstream offers twenty director modules. We use **one lens per series: the era film the creator picked** (rule 20: the
creator gives the story, Claude offers two or three script variants, then two or three successful films set in that era
with a recommendation, and he picks). From then on:
- Name the film directly in every picture prompt ("a frame from the film 1917 (2019)"); the creator found this beats a long
  style description (2026-11-19 22:22 UTC). Keep one short era line beside it, never a style essay.
- Write the director's book from what that film actually does: light (motivated, natural or practical), palette, lens
  habits (focal range, eye level or not), camera behaviour (static, slow push, handheld), shot sizes it prefers, how long it
  holds. Our clips are short (VL-06 sizes them), so a long-take film becomes slow, continuous moves inside short clips plus
  cuts on motion, not one-shot sequences.
- Upstream director modules (`references/director_styles/`) are a vocabulary to describe the chosen film's habits. Do not
  apply a director lens on top of the film; the film wins (precedence: series film > upstream genre playbook > defaults).
- Never copy a specific shot, line, character or plot beat of the film. The film gives the look and the camera grammar.

## Pipeline (run only the steps the request needs, in order)

1. **Intake.** The scene list, the clock (the read is timed first: voice before pictures, `gemini_task.timing`), the
   series film, the hero sheets and place references that already exist (reuse before new: OR-18, `imagegen/vault.py`).
2. **Scene breakdown.** Per scene: literal event, the dramatic question, the conflict, the subtext (the scene header's
   `real_subject`), and a **visual thesis you could photograph** ("the trench gets brighter as the men get braver", not
   "hope"). Narration that already says it means the picture must show something else (no double exposition, KP-20).
3. **Beat map.** Beats are changes of pressure, not changes of camera. Each beat gets a shot family from the nine of
   `references/cinematic-language.md` (establishing, relation, close-up, insert, reaction, transition, aftermath, POV,
   reveal). Reactions come from the listener's face on the line that lands (skill `visual-beats`).
4. **Director's book** (once per episode, from the series film): palette and light logic, the allowed camera moves, lens
   policy, performance register (restrained, period-true), the identity strings of each hero and each place, and the cut
   rhythm. Two people filling shots from it must produce compatible work. Depth: `references/lighting-and-color.md`,
   `references/continuity-bible.md` (identity string recipe).
5. **Blocking.** For every shot with people: start position, movement, props, eyeline, end position, which side of the axis
   the camera is on. Write it into the continuity card (`continuity_card/1`, CT rules in
   [SHOT_CONTINUITY](../../../docs/SHOT_CONTINUITY.md); stage page `shot-continuity-writer`). A grey Blender layout of the
   key frames is an optional lab aid when staging is hard (the 2026-11-19 test: it fixed group staging but an attached
   image halves Gemini's output size, so it costs an upscale). Depth: `references/blocking-and-staging.md`.
6. **Shot list.** One row per shot: id, route, duration from the clock, story function, size, lens, angle, the one camera
   move or "locked", blocking start to end, light direction, continuity anchors, transition in, risk, and for `video`
   shots the `edit_plan` with its continuity mode (VL-01: continuation, coverage, insert). Cut geometry: two size steps on
   an unchanged axis, or one step plus a 30-degree change, unless the match is deliberate (`references/cinematic-language.md`).
7. **Keyframes (pictures).** Every new shot gets a fresh start frame drawn from the untouched scene master and the hero
   sheets (CT-03, VL-04), never from the last frame of the clip before; a same-shot continuation may hop at most twice
   (final plan P-6). Start and end frames only where the action has a definite end the model would miss. Pictures come
   from the Gemini Task route in batches of six (GC-20..GC-27, `python -m explainer_engine.gemini_task --help`): image 1
   is the shot type's style anchor, then approved references; prompts are pasted word for word. Before any paid clip,
   the start pictures of a scene sit in cut order on one contact sheet and are looked at (VL-10).
8. **Motion briefs (clips).** The LTX prompt is composed by `videolane/scene.py` from the shot fields; the director's job
   is the fields: **one primary action with an end state, one camera behaviour (or locked), one environmental motion**, the
   one hero line if the shot speaks (VL-02: one line per clip, no speaking close-up), and only the negatives this shot
   really risks, named as instances ("no wristwatch, no rubber soles"), never categories. Depth:
   `references/prompt-lexicon.md`; the upstream tool adapters (`references/ai-video-tool-adapters.md`) are background,
   our model is LTX-2.5 distilled on Modal (D-132; skill `v-ltxv2-video` for its traps).
9. **2.5D briefs.** A `still_25d` shot names what breathes (fog, breath, smoke, a flag) and the one slow camera path; each
   sub-shot stays within BP-109's length (`episode/shot_split.py`). The director keeps the anchor (the face, the candle) in
   frame; `production/living_director.py` executes.
10. **Edit intent.** Order, transitions, J/L cuts, where silence falls, which cut is the visual-association bridge. The
    edit stage executes (skill `v-edit-video`); the director says why each cut cuts (VL-09).
11. **Look at everything before moving on** (final plan P-5): a picture is opened, a clip is watched, and the observation is
    written per asset. Failures go to the repair ladder below.

## Hard rules (ours, on top of upstream's eleven)

1. Story function first; a shot without one is cut, not polished.
2. Blocking before framing; a well-blocked scene reads even on a locked camera.
3. One action, one camera behaviour, one environmental motion per clip. A clip that needs two actions is two shots.
4. Every action has an end state written down.
5. Behaviour, not emotion: "his jaw tightens, he looks at the floor" instead of "he is ashamed".
6. Invariants are written once in the hero and place identity strings and repeated verbatim; never re-describe a hero
   inside a shot.
7. The keyframe is the control point: fix the picture before a paid clip.
8. Faces the model cannot hold go small, turned, backlit or out of frame; let inserts and reactions carry the beat.
9. Period truth: name the period things (puttees, Brodie helmets are wrong for December 1914: caps then) after checking
   the claim map; one wrong object breaks the docudrama more than a soft frame.
10. Answer the size of the question: a prompt request gets a prompt, a repair request gets a diagnosis and the cheapest fix.

## Repair ladder when a picture or a clip fails

Diagnose before rewriting. Name every symptom with the upstream code (`references/failure-modes.md`, F1-F19; read the
symptom index and only the codes you need), find the one decision that produced them, then climb only as far as needed:

| Rung | Action | Costs |
|---|---|---|
| R1 fix | trim, reframe, grade, cut around it in the edit | free |
| R2 prompt patch | one positive correction sentence (GC-25 for pictures), fewer actions, an end state, a named negative | one regeneration |
| R3 new keyframe | redraw the start frame from the master; for a clip, change the picture not the prompt | one picture + one clip |
| R4 fallback | the same beat as `still_25d`, an insert, a reaction, or the consequence off screen | free |

At most two generative retries per shot (final plan P-5); after that, change the shot, not the prompt. Common roots: an
overloaded clip (F4, F6), a pose with no implied motion (F2), no end state (F5), a continuation drawn from a degraded last
frame (F7), a reference set that disagrees with itself (F1, F3).

## Checked in code, not here (SK-2)

Route and talking checks `episode/router.py` (G1); the edit plan and cut reasons `videolane/plan.py` (VL-01..VL-09); the
contact sheet `videolane/storyboard.py` (VL-10); continuity cards `production/continuity.py`; shot cards
`explainer_engine/validators/shots.py` (planned, W2); 2.5D depth sanity and map laws in their lanes; every observation in
`qa/look_and_listen.py`. A rule here that names a number points at its BP id or validator, and a check that did not run is
reported NOT_RUN, never as a pass.

## Upstream references: when to open which

| Need | Open |
|---|---|
| Shot families, cut geometry, axis, eyeline, 30-degree rule | `references/cinematic-language.md` |
| Staging two or three people, proxemics, what AI renders badly | `references/blocking-and-staging.md` |
| Light roles, colour script | `references/lighting-and-color.md` |
| Identity strings, location plates, multi-scene bibles | `references/continuity-bible.md` |
| Verb banks, negatives by failure class | `references/prompt-lexicon.md` (index first, one bank) |
| Failure codes F1-F19 with before/after repairs | `references/failure-modes.md` (symptom index, then one code) |
| Edit timelines, match cuts, average shot length | `references/editing-and-assembly.md` |
| Sound layers per shot | `references/sound-and-dialogue.md` |
| Retries, versioning, the difficulty rubric for the risk column | `references/production-workflow.md` |
| Describing the series film's habits | `references/director_styles/README.md`, then the nearest module as vocabulary only |
| Genre registers (horror stillness, comedy holds) | `references/genre-playbooks.md` (one genre) |

Not used from upstream: the Chinese-UI prompt defaults, the paid tool adapters as targets, product and macro playbooks,
the `assets/` templates (not vendored), and any "pick a director" step.
