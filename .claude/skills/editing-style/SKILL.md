---
name: editing-style
description: Choose and apply an editing style for a Crossworld Theories video (cuts, dissolves, zoom continuity, sound layering, seams, speed, a mysterious look at no cost) and avoid the common editing mistakes. Use for every cut plan, every assembly, every complaint about jumps, loudness, zoom or too many sounds.
---

# Editing style

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role edit` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Rules: `docs/EDITING.md` (ED-01..ED-07). This page is the judgement behind them. Sources of the research (2026-10-17):
Adobe, Vimeo and Boris FX on split edits; Wikipedia on dissolves (typically 1-2 s, 6-12 frames to soften a hard cut) and
continuity editing; Fiveable on cuts and dissolves; editing-mistake guides (too many transition types, unlevelled audio, jump
cuts); ducking guides (6-12 dB, attack 30-80 ms, release 250-700 ms). The search results were thin on room tone and
documentary pacing, so the numbers for those come from our own measurements (the Episode 1 read: chunk loudness spread 5.6 dB).

## Pick the style from what the story is doing

| Style | Use when | How we make it |
|---|---|---|
| **Narrated montage** | time passes, many small proofs (Year 1 to Year 100) | a new picture every 3-5 s, hard cuts inside pauses, the period dissolve once at the start of each period |
| **Held tableau + bubbles** | a conversation, a joke, a hero decision | one picture 6-9 s, speech bubbles, slow push continued across the beat |
| **J-cut / L-cut** | a reveal or a question hook | the next sound (bed, sting) starts 0.4 s before the picture, the old sound rings 0.4 s after (BED_LEAD) |
| **Slow dissolve** | a time jump or a mood change | 1 s at periods (UR-14), nothing else dissolves |
| **Fade from / to black** | start, end, the Year 100 silence | 1 s in, 1.5 s out |
| **Match cut** | a object that returns (the grain, the pot, the fire) | the next shot opens on the same object at the same screen position |
| **Mystery look** | the whole episode | vignette + fine grain from one `look`, a quiet low tone under reveals; never a flash or a spin |

One style per beat, at most three transition kinds in the whole video: cut, dissolve, black.

## Common mistakes (do not make them)

1. A zoom that restarts at the default view on the same picture: continue it or ease out (ED-02).
2. Read chunks at different loudness joined as they came: level them first (ED-01); check the three loudest joins by ear.
3. Two music tracks, the tick and a bed all under the voice: one music at a time, the tick 6 dB lower than music (ED-03).
4. Transition tricks used for variety: the more kinds, the cheaper it looks.
5. Dissolve over a spoken sentence: dissolve in the pause only.
6. A cut on the first word of a sentence: cut in the pause before it, so the picture is there when the word comes.
7. A loud sound effect that was never levelled to the voice: sounds sit under the narrator, never over.
8. Holding a picture after its beat is spent: change something on screen at least every 9 s (UR-31).
9. Over-compressing time to hide a weak script: speed is a finishing choice (ED-06), not a repair.
10. Silence that is a bug: every pause over 1 s is on purpose and short of a gap.

## Process

Study the cut (frames on both sides of three joins, a listen to three chunk joins), ask the creator what is unclear, update the
rules and this skill, then produce. A creator note becomes a rule with a test before the next render (OR-09).

## Show the logic, not only the story (creator 2026-10-17)

The video must look like there is a calculation and a logic behind it, not like a sleep-story. Each period gets at least one data
visual (ED-10), in this order of preference:

| Visual | Use for | Example from Episode 1 |
|---|---|---|
| Counter / ticker | one number that grows | 100 adults x 2,500 kcal = 250,000 kcal a day |
| Bar pair (before / after) | a bottleneck solved | grain: 2 kg an hour of cutting vs 75 kg needed a day |
| Line or step chart | change over time | colony size, tools, pots across the periods |
| Ledger / table of 3-5 rows | who does what | jobs of the 100 and their output |
| Timeline strip | where we are, what came first | Day 1 to Year 100 with the real record under it |
| Two-column comparison | the verdict | our group vs real history, the same milestone each row |
| Map / flow arrow | supply chains (tin, iron) | tin from far away to the furnace |

Rules: numbers only from the claim map; each visual has one sentence of narration that says what to look at; build it with a pop
(0.6-1.0 s), hold 3-7 s; hand-drawn look; do not stack a chart on the speech bubble; the period card (ED-09) comes first, the
visual after the first explanation, never in the first 5 s of a period. Voice and cut are the main work; visuals, music and
texture are bonuses that must never hurt them (ED-11).
