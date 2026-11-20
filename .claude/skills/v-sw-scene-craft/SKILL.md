---
name: v-sw-scene-craft
description: Build one docudrama scene that turns - McKee's five-step scene design, the value that flips, enter late and leave early, action over talk, suspense and delay, the one prop or detail that carries the period, and a place our routes can shoot. Use when writing or fixing a single scene, when "nothing happens" in it, when choosing its place, or when a scene needs a prop that pays off later.
---

# Scene craft for docudrama (layer L3, stage 2)

Built from jtydhr88/screenwriting-skills, page `sw-scene-craft` (MIT, commit `51115f18d1`; McKee's scene design and Dialogue
scene types, Field, Hicks, Walter, Henson, Hoxter, Mei Feng, Lu Jun). Rewritten in English for our format under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Upstream Chinese text: `UPSTREAM_SKILL.md`; the scene analyses:
`reference.md`. The scene header and the scene rules are ours: skill `dialogue-scenes` and SC-01..SC-12 in
[STORY_ENGINE](../../../docs/STORY_ENGINE.md).

## What a scene is here

A scene is a unit of action in one place and one continuous time in which a value at stake turns from one charge to the
other because people present want opposite things. In a docudrama it is also **a reenactment our routes can make**: a
small number of people, one place the pictures can hold, actions a short clip can show. A scene is not a location and not a
block of lines. If nothing turns, it is a summary; give it to the narrator or cut it.

## McKee's five steps, applied

1. **Define the conflict.** Whose scene is it (pov), what do they want now, who present wants the opposite. Write both
   wants in the header (SC-03).
2. **Note the opening value.** One value (safety, trust, duty, pride) and its charge at the first line.
3. **Break it into beats.** A beat is an action and a reaction, written as verbs ("he offers a cigarette / the German
   hesitates"). Every beat must change the pressure; a beat that repeats a tactic is cut.
4. **Note the closing value** and compare: if it equals the opening, the scene did not turn (SC-02 FAIL).
5. **Find the turning point**: the beat where the gap between expectation and result opens. Name it in `turn` before
   writing the lines.

## Enter late, leave early

Start at the last moment before the conflict is unavoidable; end within a line or two of the turn, on the new problem
(exit `fail_new_goal`, `succeed_complication` or `interrupted`; never "resolved and calm"). Test: delete the first line;
if the scene still works, delete it for good and try again (SC-06).

## Action over talk

Walter and Henson: a scene shown is stronger than a scene said. In our pipeline this is also a production rule: every
hero line is one short clip (D-131 video shots speak one line, VL-02), and a silent action is cheaper and safer than a
speaking face. So:
- Put the turn in an **action** where you can (a hand lowers a rifle, a man steps onto the parapet).
- Give each speaker a **physical task** while talking (cleaning a mess tin, writing a letter): it gives the picture a motion
  and the actor-less clip something true to do.
- A **silence beat** after the hardest question is often the turn itself (skill `dialogue-scenes`, scripted silence).
- Avoid scenes that are only talk in a static room: they become a row of speaking heads, the hardest shot to make well.

## Suspense, delay and wit (Lu Jun's "the interest must be full")

- **Suspense**: let the viewer know more than a hero (the officer is coming down the trench); the scene plays on the gap.
- **Delay**: the answer the viewer wants is withheld by a credible obstacle (a flare goes up, someone coughs), then given.
  Delay without a cause feels like a trick.
- **Wit**: the small human surprise inside a grim scene (a German asks for an English football score). Humour comes from
  the situation, never from a false fact.

## The detail and the prop (Lu Jun's "details must be clever, props must be precise")

- **One period detail per scene** that a modern viewer notices and believes: a tin of Princess Mary's gift box, a
  Pickelhaube cover, a candle stub in a bottle. It must be in the claim map or the period references.
- **A prop that travels**: planted in an early scene, it returns at the turn of a later one (ST-06 set-up and pay-off).
  Give the director the prop's identity string once (skill `v-director-cinematic`).
- Details do work: they show status, time, cold, fear. A detail that does nothing is set dressing; let the pictures carry it
  without a line.

## Choosing the place (Lu Jun's "the scene must fit"; Walter's twelve alternatives)

List at least five places where the scene could happen and pick the one that adds pressure: a cramped dugout makes a
quarrel hotter than an open field; no man's land makes a handshake dangerous. Prefer places the series references already
hold (reuse: one place, one picture, LV rules in `docs/SCENE_REUSE_RULES.md`). A new place costs a reference round.

## Scene types (McKee's Dialogue), for variety across the episode

`balanced` (equals clash), `asymmetric` (officer and private), `indirect` (politeness hides the attack), `comic` (real
stakes, absurd tactics), `minimal` (quiet friction), `reflexive` (a man against himself, often a letter read aloud by the
narrator). Never two of the same in a row (skill `dialogue-scenes`, conflict modes).

## Sequences

Three to five scenes that build to one larger turn form a sequence (the night of 24 December). Each scene inside it turns a
smaller value; the sequence turns the big one. Between scenes the narrator carries time and place in one or two sentences,
and the director bridges by visual association.

## Diagnosis

| Symptom | Cause | Fix |
|---|---|---|
| Nothing happens | no opposing want present | give the obstacle a person in the room |
| It turns but nobody feels it | the value is abstract | make the stake physical and visible |
| It is all talk | the turn is a sentence | move the turn into an action or a silence |
| It runs long | entered early, left late | cut the first lines and the wrap-up |
| It feels invented | the detail is generic | replace it with one sourced period detail |

## Writing one scene

1. Fill the header (SC-01) from the skeleton line.
2. List the beats as action / reaction verbs; mark the turn.
3. Pick the place from five options and the one detail and prop.
4. Write the lines (skill `v-sw-dialogue` for the line craft); keep each speaker's line inside one clip.
5. Run `python -m explainer_engine.scripting.scene_lint` on the script; fix every FAIL.

Not used from upstream: stage-play scene directions, phone/car/restaurant rules that assume live actors, page lengths.
