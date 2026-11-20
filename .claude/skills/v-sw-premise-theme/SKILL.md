---
name: v-sw-premise-theme
description: Turn a historical topic into a premise worth ten minutes - the value and its cause, the yes/no dramatic question, the counter-idea, the angle that makes an old event new, and a logline that survives the creator's variant card. Use at stage 0b of the writers' room, when a topic "has events but no story", and when picking between story variants.
---

# Premise and theme for a docudrama episode (layer L2, stage 0b)

Built from jtydhr88/screenwriting-skills, page `sw-premise-theme` (MIT, commit `51115f18d1`), which merges Egri, McKee, Hicks,
Cron, Hoxter, Snyder and Lu Jun. Rewritten in English for this channel under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)).
The upstream Chinese text is unloaded in `UPSTREAM_SKILL.md`; worked examples in `reference.md`; term anchors in
`../v-sw-workflow/terms.md`. Our order of work and gates: skill `story-engine`.

## Why this step decides the episode

A history topic arrives as a pile of true events. Events are not a story until one of them is chosen as the question the
viewer wants answered, and a value is seen to change because of a cause. Egri's line holds: the premise is a tyrant; every
scene that does not serve it is cut, however true. For us the premise also has to survive three filters the screenwriting
books do not have: it must be **true** (every factual step has a claim), it must be **shootable** with our routes, and it
must hold a **US viewer who has never heard of it** for the first 30 seconds.

## The five things a premise must contain

1. **A value that changes** (McKee's controlling idea = value + cause): war to peace, trust to betrayal, ignorance to
   knowledge. Name both ends.
2. **The cause, as an action of people**: "because soldiers on both sides sang the same carol", not "because of the
   Christmas spirit".
3. **The dramatic question, yes/no** (ST-01): "Will they climb out of the trench?" A wh-question ("what happened at
   Christmas?") is a topic, not a question.
4. **The counter-idea** (McKee): the strongest argument that it should have gone the other way (orders, snipers,
   officers' fear of court-martial). An episode where the opposite was never possible has no tension.
5. **The promise** (what the title and the first 30 s guarantee): the viewer must know what kind of payoff is coming
   (BP-04's 30-second contract).

## Finding the angle (Lu Jun's "choose strictly, dig deep, look from a new side")

- **Choose strictly.** Of ten true events, pick the one with a person in it who wants something and is opposed now. A
  statistic is not a subject; a sergeant with a candle is.
- **Dig deep.** Ask what the event reveals that is still true today. That is the theme; it is never said aloud by the
  narrator (show, don't tell, SC-12), it is the reason the scenes are chosen.
- **Look from a new side.** The channel's angle is "worlds collide": the moment two worlds (enemies, eras, beliefs) touch.
  Find whose eyes make the collision visible: the young private, the officer who has to report it, the enemy who walks
  first.
- **The core of the drama** (the "戏核"): one image that holds the whole conflict (a football between two trenches, a
  candle on a parapet). If you can name it, the director can shoot it.

## Desire against misbelief (Cron's third rail)

The hero wants something (to survive the winter, to see home) and believes something false (the enemy is a monster, orders
are sacred). The story is the pressure that forces the belief to break. In a docudrama the misbelief must come from the
record (letters, diaries, orders), never from invention; name the claim id beside it.

## Hicks' five premise questions, our version

1. Who is the hero, by name, and what does he want this week?
2. What stands in the way, present and active?
3. What is at stake if he fails, in plain physical words?
4. What is the clock?
5. Why should a viewer in Ohio in 2026 care in the first 30 seconds?

## Logline and the variant card

One sentence, in this order: the hero, the situation, the want, the opposition, the stake, with the clock if there is
one. Snyder's tests: is there irony in it, can you see a picture, does it promise a kind of story. Each of the two or three
**story variants** for the creator (project rule 0) is half a page: logline, spine, the yes/no question, three turns, the
ending kind (twist, reversal, bookend, callback, open; ST-10) and the series-film candidates. `scripting/variant_plan.py`
holds the VP checks; the creator's pick binds the script (ZI-07, ZI-08).

## Diagnosing "events but no story"

| Symptom | Cause | Fix |
|---|---|---|
| A timeline of dates | no hero who wants something | pick the person through whose choices the dates happen |
| No tension, the ending is known | no counter-idea | find what nearly stopped it, from the record |
| Every scene is interesting, nothing builds | no single value changing | name the value and cut what does not move it |
| The theme is spoken by the narrator | theme is an essay, not a cause | turn it into one image the hero sees |
| The viewer would not care | the angle is the historian's, not a person's | tell it from the eyes of the one who risks most |

## Workflow (from idea to approved premise)

1. Read the dossier and the claim map; list the events with their claim ids.
2. Pick three candidate spines (person + question + clock).
3. For each, write the five things above and the counter-idea.
4. Score them on truth (claims exist), shootability (routes: a moving body, a period frame, a map), and the 30-second pull.
5. Write the two or three variants for the creator's card. Nothing is scripted before his pick.

Not used from upstream: the Chinese short-play and opera premises, theatre-specific subject rules, and any guidance that
allows invented facts in a "based on" story.
