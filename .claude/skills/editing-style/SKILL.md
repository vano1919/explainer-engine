---
name: editing-style
description: Choose and apply an editing style for a Crossworld Theories video (cuts, dissolves, zoom continuity, sound layering, seams, speed, a mysterious look at no cost) and avoid the common editing mistakes. Use for every cut plan, every assembly, every complaint about jumps, loudness, zoom or too many sounds.
---

# Editing style

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role edit` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Rules: `docs/EDITING.md` (ED-01..ED-07). This page is the judgement behind them. Sources of the research (2026-10-17):
Adobe, Vimeo and Boris FX on split edits; Wikipedia on dissolves (typically 1-2 s, 6-12 frames to soften a hard cut) and
continuity editing; Fiveable on cuts and dissolves; editing-mistake guides (too many transition types, unlevelled audio, jump
cuts); ducking guides (6-12 dB, attack 30-80 ms, release 250-700 ms; our registry, BP-53, keeps 6-12 dB, attack 20-80 ms with the house 20 ms, release 250-700 ms, for every duck in the mix). The search results were thin on room tone and
documentary pacing, so the numbers for those come from our own measurements (the Episode 1 read: chunk loudness spread 5.6 dB).

## Pick the style from what the story is doing

| Style | Use when | How we make it |
|---|---|---|
| **Narrated montage** | time passes, many small proofs (Year 1 to Year 100) | a change on screen inside the section's window (BP-40), hard cuts inside pauses, the scene-boundary dissolve once at the start of each period (BP-31) |
| **Held tableau, narrator-told exchange** | a conversation, a joke, a hero decision (setup, exchange, conclusion: BP-90; a bubble at most one accent of BP-84's size) | one picture held as long as BP-40 allows its section, speech bubbles, slow push continued across the beat (BP-20, BP-21) |
| **J-cut / L-cut** | a reveal, a question hook, dialogue coverage | in a dialogue scene the audio leads or trails the picture by ED-14's J/L offset on about a third of the cuts (planned on the cuts); a location bed is a separate, shorter pre-lap: `production/timing.BED_LEAD` starts it just before its anchor word, which is not a J/L cut |
| **Slow dissolve** | a time jump or a change of place (a scene boundary) | BP-31's dissolve, placed after the narrator's conclusion and the held mood of the exchange (BP-94); nothing inside a scene dissolves |
| **Fade from / to black** | start, end, the Year 100 silence | 1 s in, 1.5 s out |
| **Match cut** | a object that returns (the grain, the pot, the fire) | the next shot opens on the same object at the same screen position |
| **Mystery look** | the whole episode | vignette + fine grain from one `look`, a quiet low tone under reveals; a whip or flash only opens a story turn (MO-04, BP-25, BP-26), never a spin |

One style per beat. Every cut is hard except the dissolve at a change of place or time (BP-31, D-64, the creator 2026-10-20 21:14) and the fade to or from black at the start
and the end; a whip or flash is a hard cut with an entry accent (BP-25), not a transition kind.

## Common mistakes (do not make them)

1. A zoom that restarts at the default view on the same picture: continue it or ease out (ED-02); a move past BP-20's scale,
    faster than BP-21's rate or BP-22's pan speed, or not eased (BP-23); a shake as a move (BP-24).
2. Read chunks at different loudness joined as they came: level them first (ED-01); check the three loudest joins by ear.
3. Two music tracks, the tick and a bed all under the voice: one music at a time, the tick 6 dB lower than music (ED-03).
4. Transition tricks used for variety: the more kinds, the cheaper it looks.
5. Dissolve over a spoken sentence: dissolve in the pause only.
6. A cut on the first word of a sentence: cut in the pause before it, so the picture is there when the word comes.
7. A loud sound effect that was never levelled to the voice: sounds sit under the narrator, never over.
8. Holding a picture after its beat is spent: change something on screen inside the section's window (BP-40), and script the
    pattern interrupt of the first minute (BP-41).
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

## Sourced rules (docs/SOURCED_RULES.md)

The numbers of this skill live in the registry (D-59); the code reads them with `sourced_rules.T`, this list is the reading copy.

- BP-20: scale 1.00-1.15 on a still, a default push to 1.10; a punch accent stacks on top (never more than 1.15 x 1.18).
- BP-21: a push or pull changes scale 0.5-3 % a second; over 5 %/s is rushed and only a punch accent.
- BP-22: a pan covers at most one seventh of the width a second (14.3 %); the house default stays 1.2 %/s.
- BP-23: every move is eased in and out; a brisk move keeps a 0.25 s readable hold at each end.
- BP-24: no shake as a move; a shake accent only on an impact word, decaying within 1 s, peak at most 7 % of the height.
- BP-25: whips and flashes at least 45 s apart, each opening a story turn.
- BP-26: at most 3 flashes in any second, no saturated red; a flash_in is 2 frames at most 80 % white.
- BP-27: a popped word holds max(0.83 s, 0.375 s x words) and at most 7 s.
- BP-28: on-screen text inside x 12.5-87.5 %, y 5-95 % of the 16:9 frame, never over a face, 4.5:1 contrast (3:1 from 24 px).
- BP-30: across a hard cut the focal point stays within 10 % of the frame; never the same framing of the same picture twice
  in a row; a direction change over 90 degrees needs a neutral picture between.
- BP-31: a dissolve only at a change of place or time (a scene boundary), its length inside BP-31's band; every other
  transition is a hard cut. After an exchange: hold the hero's mood (BP-94), then move slowly into the next scene.
- BP-92: a camera move never resets: a cut to the same picture continues the move; a run of shots on one picture never
  comes back to the framing it started from; a turn back comes to rest first.
- BP-91: the establishing shot shows the scene's cast; closer shots show a part of it, never a new set of people.
- BP-35: parallax on a still uses at least three depth layers moving toward the subject, foreground faster, eased; it counts as alive.
- BP-40: in the first 30 s something changes at least every 5 s (FAIL); in the body a still over 20 s is REVIEW, over 40 s FAIL;
  at most 10 pictures a minute on average, one burst of 5-10 cuts per 2-3 min; every change carries new information. A visual
  beat counts only when it is tied to a narration word (BP-93): never add a prop or ring to beat a clock; fix a long still
  with a cut or a move the story asks for, or accept the REVIEW.
- BP-41: one scripted pattern interrupt in the 25-35 s window (a cut with a new element).
