---
name: story-engine
description: Run the writers' room for a Crossworld Theories dialogue "what if" episode - story skeleton, scenes with character dialogue, voice performance, edit and sound plan, voice casting and the 10-Short set - as gated Sonnet stages on one production script, each stage owning its own fields. Use for every new episode script, when a script feels dull or misses the viewer, and when the edit plan looks like a slideshow.
---

# Story engine: the writers' room in seven stages

Rules: `docs/STORY_ENGINE.md` (ST story, SC scenes, DW dialogue, PF performance, MO motion, AL sound layers, VC casting,
SS Shorts) plus the existing N, EL, ED, SH, PV rules. Research behind them: `docs/research/STORY_EDIT_VOICE_2026-10-19.md`
and, for the /3 scene system, `docs/research/STORYTELLING_EDITING_2026-10-19.md`.
The output is ONE `production_script.json` (D-43): text, voices, pictures and prompts, sounds and the edit, written
before anything is paid for (project rule 1). New episodes are `production_script/3`; a `/2` keeps its old contract.

## Why stages (and why a mid-size model can do it)

A single prompt that writes story, dialogue, tags, shots and sounds at once loses the story: the technical layer crowds
out the plot. Each stage below gets a small, fixed input, writes only its own fields, and passes a free check before the
next stage starts. `scripting/stage_guard.py` proves a later stage did not rewrite an earlier one (the words are frozen
after stage 2). Every stage is an agent in `.claude/agents/` with `model: sonnet`; the orchestrator (or the session) runs
them in order and stops at the first failed gate.

| # | Stage (agent) | Writes | Gate (free) |
|---|---|---|---|
| 0 | research (orchestrator, skill `science-grounding`) | claim map C-xx, dossier | sources graded, every number has a claim |
| 1 | `story-architect` | `drama`, `cast`, segment skeleton, the beat-template choice (A/B/C), each dialogue segment's `scene` header | `story_lint` 0 FAIL (ST-00 FAIL on /3), PV-48 headers complete, REVIEWs answered |
| 2 | `scene-writer` (one segment per call, skill `dialogue-scenes`) | segment `lines` (text, speaker, claims, `to`, `intent`) as the hand-off unit | `stage_guard writer`, PV-12, PV-33, PV-48 (SC-01..SC-10) |
| 2b | `beat-writer` (same segment, right after the writer) | line `visual_beats`; cues OPT-IN, each with its `event` (skill `visual-beats`) | `stage_guard beats`, PV-44 (/3 semantics) |
| 3 | `performance-director` | tags, emphasis, tone, emotion, pauses, interjections | `stage_guard performer` (words frozen), PV-12 |
| 4 | `edit-planner` | shots, motion, accents, bubbles, graphics, beds, sfx, music; ED-14 coverage per scene (establish -> listener reactions -> <=4 A/B alternations, J/L 0.5-2 s, one music per chapter, one planned dropout) | `stage_guard editor`, `validate`: PV-24, PV-35, PV-36 |
| 5 | `voice-caster` | `voice`, `cast.<id>.voice` (traits, candidates) | `stage_guard caster`, PV-10, PV-32 |
| 6 | `shorts-writer` | `shorts` (10, at least 6 styles) | `stage_guard shorts`, PV-28, PV-34 |
| 7 | `script-critic` (fresh context) | findings only, each to its owner stage; writes `editorial_review.json` (`editorial_review/2` on /3: the integrated production-coherence pass, D-60) | SCRIPTING_SPEC gates + `production.editorial_gate` (EG), no "bored" window; at most 2 rounds |
| - | creator approval #1 | | nothing is paid before it |

## 1. The skeleton first (story-architect)
- Twelve premises, scored; the winner gets a one-sentence premise, a yes/no dramatic question and a promise.
- Heroes: each speaking hero has a want and a flaw (ST-04); the lead also a need and a change. Opposites talk best: the
  theorist and the hands-on one, the optimist and the cynic.
- One of the three beat templates of `docs/STORY_ENGINE.md` (A three-act/7-point default, B Save-the-Cat compressed,
  C mystery reveal ladder), recorded in `drama`; the midpoint in BP-75's word-share band (ST-12), a turn at least every
  BP-76 gap at BP-01's heard pace (ST-13). Every join is BUT or THEREFORE (ST-02).
- Every dialogue segment gets its `scene` header (SC-01): place, present, why_now, opposing wants, value and charges,
  the turn with its conflict mode, the exit, surface_topic and real_subject (skill `dialogue-scenes`).
- Loops and set-ups are written before lines: L01 the dramatic question, a forward-pointing line or smaller loop at least every BP-42 interval (150 s), a
  set-up planted in the first third that decides the end (ST-05, ST-06).
- Needs: pick at least three from curiosity, stakes, humour, wonder, fear, identity, justice, belonging, competence,
  surprise, and give each a segment (ST-08). Objectivity is labelled per segment (ST-09); on /3 nothing spoken says the
  story is invented (SC-08, SC-11): the title and the description carry it. Show, don't tell (SC-12): heroes are what
  they do. When the script is finished, the creator reads and approves it (OR-17) before anything is paid.

## 2. Scenes (scene-writer), one segment per call
Input is small on purpose: the skeleton (one line per segment), this segment's drama AND its `scene` header, the cast
voice bibles, the last three lines before it, the next beat, its claim ids. The writer never sees shots or tags, so it
cannot drift into them. It loads the skill `dialogue-scenes` and writes the hand-off unit: narrator in on the pressure,
a played scene of 5-12 beats where every line carries `to` (and `intent` where it fits), narrator out on the
consequence. Scene and dialogue rules SC-01..SC-10 and DW-01..DW-13 in `docs/STORY_ENGINE.md`; narration rules N-01..N-10
in `narration-script`.

## 2b. Visual beats (beat-writer), same segment, before the next one is written
While the segment's words are fresh, the beat-writer marks a beat wherever NEW information lands (within the still
limits of BP-40 and VB-01's /3 cadence; skill `visual-beats` has the numbers) and at least one reaction-driven expression change
per dialogue line — the listener's face on the line that lands. Cues are OPT-IN: silent by default, a cue only with its
story `event`, density and repetition capped (VB-10/VB-11; skill `visual-beats`). It never changes a word; if the
writer later rewrites a line, run 2b again for that line (PV-44 finds beats whose phrase is gone).

## 3. Performance (performance-director)
Delivery only; words frozen. Tags per speaker temperament, one stressed word, pauses before reveals and after
punchlines, interjections as reactions. Check with `stage_guard performer`.

## 4. Edit and sound (edit-planner)
Written per segment on the frozen words, with the accent vocabulary of `production/accents.py`: `wobble`, `punch`,
`shake`, `whip_in`, `flash_in`, `pop_text`, `slam_text`; plus bubbles, data visuals (ED-10), cards (ED-09). Every hard
accent has an effect (AL-03). On a dialogue scene follow the ED-14 coverage grammar (`docs/EDITING.md`): open on an
establishing/two-shot 2-4 s, cut to the LISTENER on every 2nd-4th line and on news/insult/revelation, never more than
4 strict A/B alternations without a pattern break, J/L offsets of 0.5-2 s on about a third of scene cuts, hold-length
variance (MO-07), one music track per story chapter and ONE planned dropout of 0.5-2 s before the biggest reveal (not BP-62's
no-music stretch: plan that one as well),
broken by an intentional sound. Read the PV-35 report: events a minute, kinds per minute, alive share.

## 5. Voices (voice-caster)
Traits -> `audio/casting.query` -> ElevenLabs `creative_list_voices` (free) -> `casting.rank` -> three candidates.
A real person: documented traits only (claim ids), never an imitation, never the famous category, never a clone. The
creator picks after a one-chunk test read (EL-02).

## 6. The Shorts set (shorts-writer)
Ten moments, ten Shorts, at least six styles from the catalog (SS-01), alternating (SS-02), each with its ending kind.

## 7. Critic
Fresh context, reads as a viewer every 30 seconds, sends each finding to the stage that owns it. Two rounds at most;
then the creator decides. On a /3 the critic also walks the finished script once as ONE timeline (the integrated
production-coherence pass, D-60): story causality, each hero's entrance, each line against its speaker and the line
before, each shot/beat/cue against its instant, delivery against meaning, and the estimated clock — layers judged
together, since each validator only sees its own. The result is `editorial_review.json` schema `editorial_review/2`
(contract: `docs/SCRIPTING_SPEC.md` section 5.2; instructions: the agent file): per-layer evidence with an honest basis
(data / estimate / instructions — never a claim to have seen unrendered media), and machine-routable findings whose
FAILs block the editorial gate, paid narration and paid assets until fixed and re-reviewed (any edit invalidates the
review by hash).

## Prompts for a Sonnet stage (how to brief it)
- Give the stage its rules by ID and the file paths, not pasted text; give it the exact fields it owns.
- Give it the whole skeleton every time (the map), but only the local text it works on (the territory).
- Ask for one segment per call; ask for a short report table at the end (what changed, which checks ran).
- Never ask a stage to "improve everything": name the finding and the owner.

## What changed on /3 (2026-10-19)

The old contract optimised presence: a cue on every beat, a face every second, a source label on every sentence — and
Syndicate Wars showed each mandate producing the named anti-pattern (33 cues/min, quips at the narrator, press-release
narration). The /3 contract inverts it: **nothing is included by default** — a scene must turn a value, a cut must have
a reason, a sound must name its story event, or it is deleted. Concretely: scene headers and addressed dialogue
(SC-01..SC-10, PV-48), the three beat templates with ST-12/ST-13, opt-in event-bound cues (VB-08 inverted, VB-10/VB-11),
reaction-driven faces (VB-02), hold-length variance (MO-07) and the ED-14 dialogue coverage grammar. Sources and the
hypothesis labels for every number: `docs/research/STORYTELLING_EDITING_2026-10-19.md`.
