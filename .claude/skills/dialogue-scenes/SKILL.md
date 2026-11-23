---
name: dialogue-scenes
description: Our scene contract for every segment where people talk in a docudrama episode - the scene header filled before any line, the narrator-scene-narrator hand-off, opposing wants, turn-taking, deflection, subtext, exposition as ammunition, real-person rules, and the v4.3 rule that each hero line lives in one video clip. Use for every dialogue segment and whenever dialogue reads as a row of isolated quips.
---

# Dialogue scenes: the contract (layer L3, stage 2)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). Craft comes from the vendored
`v-sw-scene-craft` (the scene: value turn, beats, place, prop) and `v-sw-dialogue` (the line: action under words, said and
unsaid, period voice); this page is the contract the code checks. Rule text: SC-01..SC-12 and DW-01..DW-13 in
[STORY_ENGINE](../../../docs/STORY_ENGINE.md), wired as PV-48 in `scripting/scene_lint.py`. Evidence:
`docs/research/STORYTELLING_EDITING_2026-10-19.md`.

## The scene in one sentence

Someone present wants something now, someone present opposes it, something unexpected turns it, a value flips its charge,
and the scene exits on a new problem. The narrator and the heroes stand on opposite sides of the fourth wall: a hero never
answers the narrator (SC-04).

## Production facts the writer must respect (v4.3, D-131, D-132, D-137)

- Every hero line belongs to a shot routed `video` and is spoken by the clip itself; the runner's G1
  (`episode/router.talking_check`) fails a speaking shot on any other route.
- **One line per clip** (VL-02), no speaking close-up; a line longer than one clip is split (VL-06, G1
  `video_shots_fit_the_model`), and every line ends inside its clip with BP-187's tail.
- A scene is one segment in one place ([VIDEO_LANE](../../../docs/VIDEO_LANE.md)).
- So: short lines, physical tasks while talking, reactions and silences as beats. A scene of eight speaking faces in a row
  is the most expensive and the most fragile thing we can ask for; more than three character lines in a row without a
  reaction or insert is a REVIEW (VL-08, KP-43 with BP-113's count).

## The header, before any line (SC-01)

| Field | What to write |
|---|---|
| `place` | one concrete spot the pictures can hold ("the British fire trench opposite Frelinghien, at the sap head") |
| `time` | inside the story clock ("dusk, 24 December 1914") |
| `present` | cast ids physically here; each speaks or visibly reacts, nobody else is addressed (SC-05) |
| `why_now` | what just changed that forces the talk now; if nothing did, the scene starts too early |
| `pov` | whose scene it is |
| `want` | the pov's concrete goal, winnable or losable in this scene |
| `obstacle_want` | what an opposing present character wants instead; differs from `want` (SC-03) |
| `value` | the one value at stake (safety, duty, trust, pride) |
| `open_charge` / `close_charge` | + or - at the first and the last line; they differ (SC-02) |
| `turn` | the beat where the charge flips, named in advance, with the conflict mode |
| `exit` | `fail_new_goal`, `succeed_complication` or `interrupted` |
| `surface_topic` | what they literally talk about |
| `real_subject` | what the scene is really about; no line ever says it (SC-10) |

## The hand-off unit

`NARRATOR 2-4 sentences (where, when, why now, ending on the pressure)` then `SCENE 5-12 beats with its turn, exiting on
the complication` then `NARRATOR 1-2 sentences (the consequence and the next pressure)`. The narrator never restates the
turn and never quotes a hero inside the scene. The narrator holds BP-105's share of the audible spoken words (ST-19); lines
marked `voiced: false` do not count. No more than BP-112's seconds stay in one place without cutting to the plan carried
out, its cost, or the other side moving (KP-42).

## Plan with eight questions, then cut from the top (SC-06)

What does the pov want; what present person stops them; what unexpected thing turns it; would contrast help (a whisper
instead of a shout); what do they think and not say; what do they refuse to say; could they say less; what does it set up.
Then enter late and leave early: no greeting opener, no wrap-up closer; delete the first line until the scene breaks.

## Turn-taking (SC-09, DW-06)

- Short lines by default; one longer turn per scene at its peak; the caps are BP-72 and BP-73 and the lint holds them.
- Rhythms to alternate: **jab-jab-speech**; **question-deflect-press** (a question, a deflection that shows attitude, a
  harder press, a partial truth); **interruption** (line A ends on `--`, line B answers it at once; rare, high tension only).
- **The scripted silence beat** after the hardest question or on the turn: a stage beat, worth a held moment in the mix;
  one or two per scene. It is a scene device, not a narration hold (BP-10 governs the narrator's pauses, N-15).
- Nobody speaks twice in a row unless the other's non-answer is itself the scripted beat.

## Deflection (DW-12): five moves

| Move | Example in a trench |
|---|---|
| Answer with a question | "Did you go over?" / "Who's asking, the colonel?" |
| Change the subject | "Did you go over?" / "Your tea's gone cold." |
| Silence and action | "Did you go over?" / (he keeps scraping mud off his boots) |
| Counterattack | "Did you go over?" / "You were the one waving the candle." |
| Partial truth | "Did you go over?" / "Halfway. To fetch the body." |

Never more than three clean question-answer pairs in a row; at least two indirect answers per scene. A question left hanging
is an answer.

## Subtext and exposition

Declare `surface_topic` and `real_subject` and keep every line on the surface (SC-10). Facts known to both speakers are only
spoken as weapons or stakes; facts one knows are pried out or blurted; facts neither knows belong to the narrator or a
discovery beat (DW-13). The press-release register is banned in narration (SC-07, BP-15); dates and numbers live inside a
scene only as stakes ("Midnight. Then they start shooting again.").

## Full immersion and show, don't tell

The story never stops to say it is invented or uncertain (SC-08, SC-11, BP-88); doubt lives in the heroes, the what-if or the
"reasoned" label lives in the title, the description and `claim_share`. The narrator never names a hero's trait, rates him,
or recites his biography (SC-12, BP-87): a trait is a choice on screen.

| Telling (fails) | Showing |
|---|---|
| "Sergeant Ellis was a brave man." | Ellis lifts the lantern above the parapet and holds it there. |
| "The Germans wanted peace too." | A voice from the other trench: "You no shoot, we no shoot." |

## Conflict modes (DW-09)

One per scene, varied across the episode: `balanced`, `asymmetric`, `indirect`, `comic`, `minimal`. Never two shouting
matches back to back. Record the mode with the `turn`.

## Character voice (DW-03, DW-11)

Each hero's `cast.<id>.speech` card: register, sentence length, at most three signature moves, favourite and forbidden
words, attitude to each other hero (one line per pair: this is where subtext between two people comes from), and what he
never admits. Test: cover the names; if the speakers cannot be told apart, rewrite with the card restated. Register examples
and the few-shot pairs live in skill `narration-script`.

## A worked docudrama scene

Header: place "British fire trench, Christmas Eve, the sap head"; present Private Turner and Lance-Corporal Wells; why_now
"a light has appeared on the German parapet"; pov Turner; want "go and look"; obstacle_want Wells: "keep everyone's head
down"; value safety, open +, close -; turn "the German voice calls Turner's regiment by name"; mode asymmetric; exit
`fail_new_goal`; surface_topic "the light"; real_subject "Turner is more afraid of the waiting than of the enemy".

> TURNER (to wells, press): "It's a tree. They've put a tree up."
> WELLS (to turner, decide): "Head down."
> TURNER (to wells, deflect): "There's candles on it."
> WELLS (to turner, counterattack): "There's snipers under it."
> (beat: singing drifts across; neither moves)
> VOICE ACROSS THE WIRE (to room, reveal): "Royal Warwicks! Merry Christmas!"
> WELLS (to turner, quieter, question): "...How do they know who we are?"

The narrator then carries the consequence: "Nobody sleeps on that stretch of line. By dawn, someone on the other side has
an answer." The value turns from a safe distance to an exposed one; the narrator never says what Turner feels.

(Illustrative names: a real episode takes its heroes, units and lines from the claim map.)

## Real people in a scene (D-63, D-65, D-64)

When the speakers are real living people, the narrator tells the exchange in reported speech, short and in the scene's
rhythm, naming the speaker before his words (ST-15, BP-95) and reporting at most two speakers in one line (ST-16, BP-96);
the speakers are never voiced (D-62), and at most one bubble stays as an accent (PV-56). A reported exchange still has at
least BP-70's turns of two named speakers (SC-05). Every exchange is framed: a setup that names who talks and why, the
exchange, a conclusion that says what came of it (ST-14, BP-90); never two exchanges chained. The establishing shot shows
the cast (BP-91). Historical people who are not living may speak in a played scene, in lines the record supports.

## What scene_lint checks (PV-48), in one list

SC-01 header complete; SC-02 the charge flips and the turn is named; SC-03 the wants differ; SC-04 every line addressed,
none to the narrator; SC-05 a real exchange of two or more speakers, everyone present speaks or reacts; SC-06 no greeting
opener or wrap-up; SC-07 no press-release narration; SC-08 and SC-11 no honesty beat or meta hedge; SC-09 line lengths and
question runs; SC-10 subtext declared and never spoken; SC-12 show, don't tell. Judgement stays with the writer and the
critic; numbers stay in the registry.
