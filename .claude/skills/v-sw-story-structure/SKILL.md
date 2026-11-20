---
name: v-sw-story-structure
description: Structure a 8-15 minute docudrama from an approved premise - inciting incident, progressive complications, a real midpoint, crisis, climax and resolution compressed to our clock, with turns on a cadence and every join a BUT or a THEREFORE. Use at stage 1 of the writers' room, when the middle sags, when the ending does not pay the question, or when choosing beat template A, B or C.
---

# Story structure at explainer length (layer L2, stage 1)

Built from jtydhr88/screenwriting-skills, page `sw-story-structure` (MIT, commit `51115f18d1`; Field, Snyder, McKee, Hoxter,
Hicks, Lu Jun). Rewritten in English for our length and format under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)).
Upstream Chinese text: `UPSTREAM_SKILL.md`; worked examples and beat tables: `reference.md`. Our stage order and owners:
skill `story-engine`. Numbers live in BP ids and `scripting/story_lint.py` checks them.

## Feature structure does not scale down by itself

A feature has 110 pages and 40 scenes; we have roughly 1,500 spoken words, 10 to 20 segments and 4 to 8 played scenes. What
survives the compression is the **mechanism**, not the page numbers:
- an inciting incident that breaks the hero's normal,
- complications that each make the goal harder (progressive, never repetitive),
- a midpoint that changes the hero's goal or the viewer's understanding,
- a crisis where the hero must choose between two goods or two evils,
- a climax that answers the dramatic question,
- a resolution that shows the new normal and its cost.

What does not survive: page targets, act breaks at fixed pages, B-stories that need ten minutes of their own, the
"fun and games" section as filler. A docudrama B-story is usually the record against the legend (what we believe happened
against what the letters say), and it is told in the narrator's coda, not in scenes.

## The skeleton at our length

| Beat | Where (the clock decides; BP-75 band for the midpoint, ST-12) | What it must do |
|---|---|---|
| Cold open | first 30 s | the striking true moment, the yes/no question, the title's promise (BP-03, BP-04); no context before the gap (BP-05) |
| Normal world | short | the hero's want and the world's rule, shown in one scene or one living photograph |
| Inciting incident | by about 15 % | the event that makes the old normal impossible (a song across no man's land) |
| Complications | to the midpoint | each a BUT (an obstacle) or a THEREFORE (a consequence), each raising the stake (ST-02, ST-03) |
| Midpoint | mid-story | a revelation or reversal: the goal changes or the viewer's belief does |
| Bad turn | after the midpoint | the cost arrives (orders, a death, a betrayal) |
| Crisis | the last third | the choice, played as the longest scene with dialogue (ST-18) |
| Climax | near the end | the answer to the question, in action |
| Resolution and coda | the last tenth | the real record, the cost, the image that stays; the ending kind is named (ST-10) |

Between the hook and the resolution no stretch runs longer than BP-76's gap without a turn (ST-13), and at least two
turning points are of different kinds (ST-07).

## Beat templates (recorded in `drama`)

- **A, three acts with seven points** (default): hook, plot turn 1, pinch 1, midpoint, pinch 2, plot turn 2, resolution.
  Best for a single hero with a clear goal.
- **B, Save the Cat compressed**: opening image, theme stated by someone else (one line, never the narrator), catalyst,
  debate, break into two, midpoint, all-is-lost, finale, final image. Best for a hero who changes.
- **C, mystery ladder**: the puzzle, the first wrong answer, the clue, the second wrong answer, the reveal, what it means.
  Best for "how did this happen" episodes where the viewer is the detective.

## Progressive complications (McKee), docudrama version

- Each complication must be **more costly** than the last: physical, then social, then moral.
- Complications come from **people present**, from the **world** (weather, terrain, orders), or from **inside** the hero
  (fear, duty). Vary the source; three weather obstacles in a row are one obstacle.
- Every complication must be **in the record** or a **reasoned** consequence labelled as such (ST-09). The narrator never
  hedges the story (SC-11); the label lives in `claim_share`, not in the words.
- **No repetition of beats**: the same tactic three times (begging, refusing) is the biggest sin; the third time turns
  comic.

## Openings and endings (Lu Jun's "phoenix head, pig belly, leopard tail")

- **Phoenix head**: open in motion, on the most striking image; enter fast. Of Lu Jun's eight openings, ours are mostly
  "start at the crisis and flash back", "start with the strange detail", "start with the question".
- **Pig belly**: the middle is full and varied; change the place, the register (scene, living photograph, map), the rhythm.
- **Leopard tail**: end hard and short. The answer, the cost, one image. No summary, no moral spoken aloud, no
  "and that's why history matters". Endings that work for us: the bookend (the last image rhymes with the first), the
  callback (a planted object returns), the reversal (the record undoes the legend), the open question.

## Crisis, climax, resolution

The crisis is a **choice under pressure between two things the hero values**; a choice between good and bad is no choice.
The climax is the hero acting on it, and it answers the dramatic question (yes or no, never "maybe"). The resolution shows
what changed and what it cost, in the real record; if history turned the moment back (the war went on), the coda says so
plainly, and that cost is often the most moving beat of the episode.

## Diagnosis

| Symptom | Likely cause | Fix |
|---|---|---|
| The middle sags | no midpoint, or complications of one kind | add a reversal of belief at the midpoint; vary the source |
| "And then" storytelling | events joined by time | rewrite each join as BUT or THEREFORE (ST-02, ST-20) |
| The ending feels flat | the question changed on the way, or the climax is told not played | return to the yes/no question; play the climax as a scene |
| Too much context early | the setup is a lecture | cut to the cold open; context after the gap (BP-05) |
| The viewer is ahead of the story | the outcome was promised too literally | promise the question, not the answer |

## Workflow

1. Write the ending first: the answer to the question and the final image.
2. Choose template A, B or C; place the beats on the estimated clock.
3. Write one line per segment: function, BUT or THEREFORE, stake, value shift.
4. Mark the scenes with dialogue and fill their headers (skill `dialogue-scenes`).
5. Run `python -m explainer_engine.scripting.story_lint` on the skeleton; fix every FAIL before a line is written.

Not used from upstream: page counts, Chinese short-play and opera structures beyond the opening and ending devices, TV
season arcs.
