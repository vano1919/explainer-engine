---
name: shot-visuals
description: Plan the pictures of a Crossworld Theories video so they carry stakes, conflict and named heroes instead of generic nature scenery. Use for every new shot list, every pod prompt, every plate or sprite request, and whenever a contact sheet looks like a picnic, a brochure, or "scientists seen from behind".
---

# Shot visuals: stakes in every frame, heroes you can recognise

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role image` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

> **Primary rule, above everything below (UR-22, one universe):** every picture, sprite, prop and background is drawn in the same
> universe, as if by one artist for one scene. Characters and environment share one design language (look v2: bold ink-shadowed
> silhouettes, caricature in faces, hands and posture on adult proportions), one line, one fill, one palette; an era or a place changes props, clothes and architecture, never the style. The
> look's `universe_thread` is appended to every image prompt (pod and Gemini); nothing may override it.

Read first: `docs/UNIVERSAL_RULE_BASE.md` (§E, UR-16..UR-21), `explainer_engine/edit/stakes.json`, the episode's `look.json`
(`rule_base: 2`, `caricatures`, `archetypes`, `pose_bank`). Entertainment first, facts second: the picture must make a viewer
feel what the line says (fear, panic, shock, a joke landing), and must show *who* is in trouble.

## What went wrong (Day 1, 2026-10-16) and the cause of each
| Seen by the creator | Cause | Rule that now stops it |
|---|---|---|
| "too generic, a nature photo set" | prompts described places (meadow, river, hills), not what is at risk | UR-16: `stakes` line + a cue word in every prompt; passive words banned |
| "no heroes, anonymous backs" | B shots were faceless "from behind" by default; plates were empty by design | UR-17: named heroes with emotional poses; faceless within BP-85's share, with a reason |
| no fear, no nervousness | mood clause was the only emotion; scenes were sunny and quiet | stakes cue words (storm, wind, shivering, hunger, danger) in the subject itself |
| stray people in "empty" plates | the prompt said "empty of people": the model paints what it reads | UR-20: a plate prompt never contains a people word |
| idle sprites in a pretty meadow | the only sprite poses were standing with a prop | UR-17: emotional poses (panic, shock, argue, shiver, exhausted...) from the pose bank |
| clichés of the primitive (cave, mammoth, club) | stock associations instead of the real situation | the real situation: 100 city-dressed geniuses, no fire, wind, dusk, hunger; facts from the claim map |

## How to write a shot (A / B / C)
Every shot is: **who is at risk of what, seen how**. Fill the `stakes` line first (one sentence), then the prompt.
- **A, wide:** the world is hostile or enormous and the people are tiny and exposed. Subject = scale + threat + exposure
  ("vast windswept valley at dusk under a bruised storm sky, a huddled cluster of a hundred strangers, no shelter").
  Not: "a beautiful river valley".
- **B, medium:** 1-2 named heroes doing one thing with feeling, over a *plate*. The plate is hostile ground with room for
  sprites ("bare ridge at dusk, cold grass bending in the wind, wide deserted open ground across the centre foreground").
  Heroes: `heroes: [{name, pose}]`, pose from the emotional list, a different pose from the last B shot, and at least one B
  shot per beat with friction (two heroes disagreeing, a failure, a reaction).
- **C, close-up:** the gritty detail: trembling hands, blistered palms, cracked knuckles, a spark that might die, damp wool,
  frost on glass. No faces, no environment, always something straining or about to fail.
- **Plates (UR-20):** never write person, people, man, figure, crowd, human; never "empty of people". Say "deserted open
  ground", "nothing standing on it". Check the picture afterwards: a stray figure means repaint, not "acceptable".
- **Scale:** heroes are caricatures, plates and A shots are painted at natural proportions; sprites are graded to the plate
  (UR-07) and cast a contact shadow.

## One world (UR-22): nothing may look like it came from another picture
The creator, 2026-10-16: a man seen from behind and the main hero looked like different kinds of people; every visual part
must belong to one world. The cause was our own rule (pod figures at natural proportions next to caricature sprites) and two
different renderers. Now:
- **Every person, crowd or hand painted by the pod follows the look's `figure_style`** (look v2: adult proportions, expressive
  faces and hands, one thick dark ink outline; the v1 "oversized head" figure is retired, its words are UR-24 child cues); `build_shots.py` appends it, the lint FAILs a prompt that names people or body
  parts without it. No realistic extras, no realistic hands, no "natural proportions".
- **Plates carry no people at all** (UR-20); the hero is always our sprite, never a pod-painted man.
- **Style bridge before any batch:** paint 6 test pictures (a hand, a crowd, a wide shot, plates), composite a sprite onto a
  plate and put the pod-painted hand and crowd next to it; the creator approves the sheet once per episode
  (`look.style_bridge.approved`). If pod people still look different, the extras become our sprites too (a crowd made from
  keyed cut-outs, small, flipped, tinted) and close-up hands become sprite props.
- Colour and line: sprites are graded to the plate (saturation, black level, tint, contact shadow); the same ink colour and
  line weight in prompts and sprites; one palette per beat (UR-08).

## Heroes (named, real, in character)
- Use the real figures of the topic by name in the plan and the narration; the *pod prompt never names them* (UR-06): the
  identity comes from our sprite. Each hero has an archetype line in the look; poses and jokes follow it (Newton the proud
  critic, Einstein the dreamy improviser, Franklin the organiser, Nansen the pragmatist who has actually survived ice).
- A missing hero or pose is a **reusable asset to make** (Gemini allowed for cast art, D-36): `build_shots.py` writes
  `sprite_needs.md` with the exact list; estimate the cost (about $0.067 per image), ask, then generate on the green key
  background and key it like `assets/characters/scientists_v0`.
- Real people: caricature in commentary/parody is the creator's decision (D-40); invention is announced in the intro; check
  estate-managed likenesses before publishing (docs/RIGHTS_AND_FAIR_USE.md).

## Facts stay serious
Stakes come from real constraints (cold, wet clothes, no fire, dirty water, unknown plants, hunger, predators that lived there
then). Never invent an animal, tool or technology for drama; the claim map decides what may be shown.

## Pictures are written with the line (D-43)
Do not plan pictures in a separate pass. In `production_script.json` each segment carries its shots: the phrase `at` where the picture
appears, the picture's `subject` (who does what, with which feeling), its `heroes`, `props` (with the owner), `shows` (story things
visible) and, for dialogue, `speakers` and `bubbles`. `compile` turns the subject into the D-41 prompt; `validate` checks that the
picture appears on its words (PV-04), does not show a thing before the story makes it (UR-29), shows the hero the line names (UR-30),
never shows a forbidden prop (PV-07), and that no prompt repeats (PV-06). One held picture may carry a whole exchange through speech
bubbles instead of a new picture per sentence (UR-31).

## One scene, one room (D-69, CS-01..CS-12 in docs/PRODUCTION_SCRIPT.md)
A conversation is a set of shots of ONE room, not a new illustration per sentence. For every segment whose pictures play in
one place, write `staging`: `roster` (who is in the room; default `scene.present`), `positions` (each person's seat, left to
right as the wide shot sees them), `layout` and `fixed` details, optionally `master`. The master frame is the first wide picture
and lists EVERY roster member in its `heroes` (CS-02); a crowd counted in the subject ("ten men") names its heroes or says the
rest are extras (CS-05). Vary the camera, never the room: `framing` (wide, medium, two_shot, over_shoulder, close, reaction,
insert); for an over-the-shoulder shot list the facing hero first. Write `change` when the next shot keeps the camera and only
an action changes (it is painted as an edit of the shot before). A picture of another place inside the segment is `cut_away`;
a new place or time is a new segment with its own `staging` (a following segment in the same room says `continues: true`).
Check with `python -m explainer_engine.production.staging plan <script>`; paint masters first (`paint plan --masters`), look at
each painted picture next to its master (`staging request` -> `continuity_review.json` -> `staging apply`), then the shots.

## Procedure
1. Beat by beat, from the narration: who does what, what can go wrong, which emotion. Write `stakes` first.
2. Types and order by UR-04/05; durations and cuts by the solver (UR-11/12) on the real `words.json`.
3. `python examples/<episode>/<day>/build_shots.py` -> 0 FAIL, answer every REVIEW; read `sprite_needs.md`.
4. Pod: pictures only for plates, A and C shots; cost = units x measured seconds (`cloud/job_speeds.json`), approval first.
5. Sprites: only what the plan needs, approval first.
6. **Look at the contact sheet before anything else:** would a viewer who knows nothing guess the situation? Is there a hero
   they can name? Is anything pretty-but-pointless? Repaint those pictures, with the reason logged in PROGRESS.
7. Composite a few B shots (sprite over plate) before accepting the plates: the plate must hold the pose.

**Official game screenshots are private study only (RR-15):** never an image input or reference upload to a generator; describe the look in your own words.

**Filler (D-53):** a type A plate or type C insert with no person, used once, in an explanation, pause, humour or transition beat may be marked `engine: "canva"` (at most 30 %); the script cannot declare importance, `imagegen/importance.py` computes it (PV-43).

## Sourced rules (docs/SOURCED_RULES.md)

- BP-28: on-screen text (labels, pops, bubbles, cards) stays inside x 12.5-87.5 %, y 5-95 % of the 16:9 frame, never over a
  face or a mouth, at 4.5:1 contrast against its backdrop (3:1 from 24 px); plan the picture's empty zone for it.
- BP-34: a keyed close-up matches its backdrop (anti-sticker): the same light direction, luma within 0.18 and warmth (R - B)
  within 0.12 of the backdrop, no key halo over 2 px, a contact shadow sampled from the backdrop's darks, shared grain;
  `production/faces.py` measures it when the files exist (`lint` with picture folders).
