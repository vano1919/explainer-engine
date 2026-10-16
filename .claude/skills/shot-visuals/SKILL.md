---
name: shot-visuals
description: Plan the pictures of a Crossworld Theories video so they carry stakes, conflict and named heroes instead of generic nature scenery. Use for every new shot list, every pod prompt, every plate or sprite request, and whenever a contact sheet looks like a picnic, a brochure, or "scientists seen from behind".
---

# Shot visuals: stakes in every frame, heroes you can recognise

Read first: `docs/UNIVERSAL_RULE_BASE.md` (§E, UR-16..UR-21), `explainer_engine/edit/stakes.json`, the episode's `look.json`
(`rule_base: 2`, `caricatures`, `archetypes`, `pose_bank`). Entertainment first, facts second: the picture must make a viewer
feel what the line says (fear, panic, shock, a joke landing), and must show *who* is in trouble.

## What went wrong (Day 1, 2026-10-16) and the cause of each
| Seen by the creator | Cause | Rule that now stops it |
|---|---|---|
| "too generic, a nature photo set" | prompts described places (meadow, river, hills), not what is at risk | UR-16: `stakes` line + a cue word in every prompt; passive words banned |
| "no heroes, anonymous backs" | B shots were faceless "from behind" by default; plates were empty by design | UR-17: named heroes with emotional poses; faceless <= 15 % with a reason |
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

## Procedure
1. Beat by beat, from the narration: who does what, what can go wrong, which emotion. Write `stakes` first.
2. Types and order by UR-04/05; durations and cuts by the solver (UR-11/12) on the real `words.json`.
3. `python examples/<episode>/<day>/build_shots.py` -> 0 FAIL, answer every REVIEW; read `sprite_needs.md`.
4. Pod: pictures only for plates, A and C shots; cost = units x measured seconds (`cloud/job_speeds.json`), approval first.
5. Sprites: only what the plan needs, approval first.
6. **Look at the contact sheet before anything else:** would a viewer who knows nothing guess the situation? Is there a hero
   they can name? Is anything pretty-but-pointless? Repaint those pictures, with the reason logged in PROGRESS.
7. Composite a few B shots (sprite over plate) before accepting the plates: the plate must hold the pose.
