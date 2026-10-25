---
name: dialogue-scenes
description: Write or fix any scene where characters talk - the scene header, opposing wants, turn-taking, subtext, exposition as ammunition. Use for every dialogue segment of a production_script/3 and whenever dialogue reads as isolated quips.
---

# Dialogue scenes: a unit that turns, not a row of quips

Rules by id: SC-01..SC-10 and DW-01..DW-13 in `docs/STORY_ENGINE.md` (wired as PV-48, `scripting/scene_lint.py`).
Evidence for every rule and number: `docs/research/STORYTELLING_EDITING_2026-10-19.md`. A scene is not a location or a
block of lines: someone present wants something now, someone present opposes it, something unexpected turns it, and a
value flips its charge. The narrator and the cast live on opposite sides of the fourth wall (SC-04): a hero never
answers the narrator.

## The scene header (fill it BEFORE any line; SC-01)

| Field | One-line guidance |
|---|---|
| `place` | One concrete room or spot the renderer can paint ("the back room of Capone's club"), never "a city". |
| `time` | When, inside the story's clock ("night, the day the clip lands"). |
| `present` | Cast ids physically here. Everyone listed speaks or reacts; nobody else may be addressed (SC-05). |
| `why_now` | What just changed that forces this talk NOW. If nothing did, the scene starts too early. |
| `pov` | Whose scene it is (one cast id); write the scene from their side. |
| `want` | The pov's short-term, concrete goal in THIS scene — winnable or losable inside it. |
| `obstacle_want` | What the opposing present character wants instead; must differ from `want` (SC-03). |
| `value` | The one value at stake (control, trust, safety, pride...). |
| `open_charge` / `close_charge` | + or - on that value at the first and last line; they MUST differ (SC-02). |
| `turn` | The beat where the charge flips — name it, don't hope for it. |
| `exit` | `fail_new_goal`, `succeed_complication` or `interrupted`. Never "resolved and calm". |
| `surface_topic` | What they literally argue about (the clip, the shipment, the map). |
| `real_subject` | What the fight is really about (status, fear, trust). No line ever states it verbatim (SC-10). |

## Plan with Johnston's 8 questions, then cut from the top (SC-06)

1 What does the pov WANT? 2 What's STOPPING them (a present character's opposing goal)? 3 What's the TURN (something
unexpected)? 4 Could CONTRAST help (a quiet negotiation instead of a shouting match)? 5 What are they THINKING
(unvoiced worries)? 6 What DON'T they say (make others work for answers)? 7 Could they SAY LESS? 8 What does it SET UP?

Enter late, leave early: no greeting opener, no wrap-up closer. The test: delete the scene's first line and check the
scene still works; repeat until it doesn't. End within 1-2 lines of the turn, on the exit state, never on a summary.

## The narrator<->scene hand-off unit

`NARRATOR 2-4 sentences (where / when / why-now, ending on the pressure) -> SCENE 5-12 beats with a turn, exiting on
the complication -> NARRATOR 1-2 sentences (the consequence + the next pressure)`. The narrator NEVER restates the
scene's turn and never quotes a character. The narrator's share is [BP-105](../../../docs/SOURCED_RULES.md)'s (25-45 % for
template D; the old ~40-60 % is superseded). A scene may run 2-4 minutes, but no more than [BP-112](../../../docs/SOURCED_RULES.md)'s
seconds stay in one place: cut away to the plan carried out, its cost or the other side moving (KP-42), and no more than
[BP-113](../../../docs/SOURCED_RULES.md)'s lines in a row without a silent reaction, an insert or a cutaway (KP-43).

Short example: N: "By lunch the clip has a million views. In the back room, Enzo is waiting." -> the scene plays and
exits on Capone's fear -> N: "The order to find the cameraman goes out that night. It comes back without a name."

## Turn-taking (SC-09, DW-06)

- Default line 5-15 words. Hard cap 35 words (FAIL). One `speech` turn of 25-60 words per scene, only at its peak.
- Three rhythm patterns to alternate: **jab-jab-speech** (runs of 3-8-word jabs, then the one longer turn, then jabs);
  **question-deflect-press** (a direct question, a deflection that reveals attitude, a harder press, a partial truth);
  **interruption** (line A ends mid-clause on a dash — line B starts with a gap of at most 0.1 s; 0-2 per scene, only
  at high tension).
- The scripted silence beat: after the hardest question or on the turn, a stage beat `(beat — no answer)` worth
  1.5-3 s in the mix (normal inter-line gaps are ~0.4-0.8 s). 1-2 per scene; silence is a reply. This is a scene device,
  not a narration hold: BP-10's hold limit governs the narrator's pauses (N-15), and a speaker line's
  `pause_after` is not held to it.
- Nobody speaks twice in a row unless the other's non-response is itself a scripted beat.

## Deflection (DW-12): Stein's five moves

| Move | One-line example |
|---|---|
| Answer with a question | "Did you take it?" — "Why would you even ask me that?" |
| Change the subject | "Did you take it?" — "Your brother called. Twice." |
| Silence + action | "Did you take it?" — (she keeps wiping the counter) |
| Counterattack | "Did you take it?" — "Count your own drawer first." |
| Partial truth | "Did you take it?" — "I moved it. That's all." |

Never more than 3 clean question->answer pairs in a row (reads as an interview); at least 2 non-direct responses per
scene. A question may hang unanswered — that is an answer.

## Subtext (SC-10)

Declare `surface_topic` and `real_subject`; keep every line on the surface. The moment a character says the real
subject aloud ("you don't respect me", "I'm scared of losing control"), the scene goes flat and scene_lint FAILs it.
Mini example: real_subject "Enzo thinks the boss is slipping" — Enzo never says it; he says "The plate. The driver.
The route." and lets the list say it.

## Exposition as ammunition (DW-13, SC-07)

Knowledge-state table: mark each fact Known/Unknown per speaker.

| State | Where the fact goes |
|---|---|
| K/K (both know) | Spoken only as a weapon or stake ("You signed off on this route yourself."), never recited. |
| K/U (one knows) | Extracted: the other asks, pries, pays — or it is blurted under pressure. |
| U/U (neither knows) | The narrator's, or a discovery beat. Never a mouth. |

The test: would they say this with no audience watching? No -> rewrite as an accusation or a question, or give it to
the narrator. Ration ~1 dialogue-borne fact per 2-3 beats. The press-release register is banned in narration (SC-07);
dates and specs live only inside a scene as stakes. Three rewrites:

| Bad (press release) | Good (stakes inside the scene) |
|---|---|
| "Rockstar's page gives a release date, November 19, 2026." | ENZO: "We've got until November 19. Then every street gets a rulebook." |
| "The company announced six locations." | CAPONE: "Six towns. Pick the one we can hold." |
| "The trailer confirms the swamp region." | ENZO: "They showed the swamp. That's OUR swamp." |

Full immersion (SC-08, SC-11, BP-88; the creator 2026-10-20): the story never stops to say it is invented, a
simulation or a hypothetical, and the narrator never hedges it ("we cannot know for sure"); the title and the description
carry the what-if. A hero may doubt inside a scene. Show, don't tell (SC-12, BP-87): the narrator never names a hero's
traits, rates them or recites a biography; a trait is a choice on screen.

| Telling (FAIL on /3) | Showing |
|---|---|
| "Trump is a master of perception." | He spends forty of his hundred dollars on a rented jacket before he spends a cent on food. |
| "Musk takes huge risks." | MUSK (to the seller): "Eighty for the broken one. All of it." The seller: "That's your last eighty." |
| "This is only a simulation, of course." | (cut: the title says "What if"; the story plays as if it is happening now) |

## Conflict modes (DW-09 softened)

Pick ONE mode per scene and vary it across the episode — never two shouting matches back to back:
`balanced` (equals clash) · `asymmetric` (boss vs subordinate) · `indirect` (politeness hides the attack) ·
`comic` (the stakes are real, the tactics absurd) · `minimal` (quiet friction). The learner-corrected scene (the old
DW-09) is one mode among these, used at most once per episode, not every scene's shape. Record the mode in the scene
header's `turn`/notes.

## Character voice (DW-03, DW-11)

The voice bible per hero (in `cast.<id>.speech`, extended): register, sentence length, at most 3 signature moves,
favourite and forbidden words, `attitude_to_each_other_character` (one line per pair — this is where subtext between
two specific heroes comes from) and `what_they_never_admit` (the pressure under every deflection). The test: cover the
speaker names and attribute each line; below ~80 % the voices have blurred — regenerate with the bible restated. A
line "anyone" could say is a rewrite candidate.

## The worked example (the real failure, rewritten)

Old Syndicate Wars S11 — the hero answers the narrator, nobody is present (audit, quoted):

> N: "Someone films him handing out free sandwiches. Millions of views by lunch." / CAPONE: "Millions? For a
> sandwich? Print more sandwiches!" / N: "Brilliant! Oh, but then someone films the car he arrived in. Then the
> driver. Then the licence plate." / CAPONE: "Wait. Who filmed my car?"

The fixed form is a SCENE. Header:

```json
{"place": "the back room of Capone's club", "time": "night", "present": ["capone", "enzo"],
 "why_now": "the clip hit a million views an hour ago", "pov": "capone",
 "want": "make the clip work for him", "obstacle_want": "enzo: kill the clip before it kills them",
 "value": "control", "open_charge": "+", "close_charge": "-",
 "turn": "the list of what the camera caught lands; mode: asymmetric",
 "exit": "fail_new_goal", "surface_topic": "the sandwich clip", "real_subject": "the boss is slipping"}
```

The scene (8 turns; `to` and `intent` on every line):

> CAPONE (to enzo, decide): "Print more sandwiches."
> ENZO (to capone, press): "They filmed your car, boss."
> CAPONE (to enzo, deflect): "So?"
> ENZO (to capone, press): "The plate. The driver. The route."
> CAPONE (to enzo, banter): "A million views, Enzo. Nobody's reading plates."
> ENZO (to capone, reveal): "The Northside boys froze the frame. They're reading."
> (beat — no answer; Capone sets his glass down)
> CAPONE (to room, quieter, question): "...Who filmed my car?"

Why it works: the same fact as before — being filmed is dangerous — now turns a value (control, + to -) through two
opposing wants, and the narrator never touches it. Zero press-release lines; the turn is Capone's triumph curdling
into fear, shown by a silence beat and a quieter repeat of his own question.

## Closing checklist (what scene_lint will check, PV-48)

- SC-01 the header exists and is complete; pov and present are in the cast.
- SC-02 open_charge != close_charge and `turn` names the turning beat.
- SC-03 want != obstacle_want, both concrete.
- SC-04 every line has `to` (someone present, self or room); no hero line answers the narrator.
- SC-05 a run of >=4 consecutive character lines (>=2 speakers, no narrator inside); every present hero speaks or reacts.
- SC-06 no greeting opener, no wrap-up closer.
- SC-07 no press-release register in narration; dates and specs only inside a scene as stakes.
- SC-08 no spoken honesty beat (BP-71 is 0); SC-11 no meta disclaimer or hedge on the story (BP-88).
- SC-12 show, don't tell: no trait statements, ratings or biographies from the narrator, no stat cards (BP-87).
- SC-09 line lengths (BP-72, BP-73): >35 words FAIL, >15 REVIEW unless the scene's one speech, one >=25-word turn per scene,
  <=3 "?" runs.
- SC-10 surface_topic and real_subject declared; no line states the real subject verbatim.

## Real people in a scene (D-63, creator 2026-10-20)

When the speakers are real living people, the narrator tells the exchange in reported speech ("O'Leary asks if he can still build things. Musk says he can build anything."), short and in the scene's rhythm; the speakers are never voiced (D-62) and a scene keeps at most one bubble as an accent (PV-56). Plan the end of each exchange as a held face of the last speaker in its mood, then a slow move to the next shot, never a cut straight into other people's talk.

A reported exchange is a real exchange (SC-05, BP-70, D-65, the creator 2026-10-20 21:14/21:17): at least BP-70's turns of two named speakers told by
the narrator ("O'Leary asks ... Musk says ..."); name the speaker before his words (ST-15, BP-95) and report at most two
speakers in one line (ST-16, BP-96). The narrator need not repeat what is written on screen; what matters is that the listener
follows the story. After the conversation, the picture moves slowly to a new shot.

Frame every exchange (ST-14, BP-90, D-64, the creator 2026-10-20 21:14): a narrator setup that names who talks and what idea or want brings them there, then the exchange, then a narrator conclusion that says what came of it, and only then the next exchange: never two exchanges chained. The narrator gives the context whenever a conversation needs it. The establishing shot of the scene shows its cast (BP-91); a bubble, when the scene keeps one, is a key phrase within BP-84's cap that the narrator has just told.
