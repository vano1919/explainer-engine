---
name: story-engine
description: Run the writers' room for a Crossworld Theories dialogue "what if" episode - story skeleton, scenes with character dialogue, voice performance, edit and sound plan, voice casting and the 10-Short set - as gated Sonnet stages on one production script, each stage owning its own fields. Use for every new episode script, when a script feels dull or misses the viewer, and when the edit plan looks like a slideshow.
---

# Story engine: the writers' room in seven stages

Rules: `docs/STORY_ENGINE.md` (ST story, DW dialogue, PF performance, MO motion, AL sound layers, VC casting, SS Shorts)
plus the existing N, EL, ED, SH, PV rules. Research behind them: `docs/research/STORY_EDIT_VOICE_2026-10-19.md`.
The output is ONE `production_script.json` (D-43): text, voices, pictures and prompts, sounds and the edit, written
before anything is paid for (project rule 1).

## Why stages (and why a mid-size model can do it)

A single prompt that writes story, dialogue, tags, shots and sounds at once loses the story: the technical layer crowds
out the plot. Each stage below gets a small, fixed input, writes only its own fields, and passes a free check before the
next stage starts. `scripting/stage_guard.py` proves a later stage did not rewrite an earlier one (the words are frozen
after stage 2). Every stage is an agent in `.claude/agents/` with `model: sonnet`; the orchestrator (or the session) runs
them in order and stops at the first failed gate.

| # | Stage (agent) | Writes | Gate (free) |
|---|---|---|---|
| 0 | research (orchestrator, skill `science-grounding`) | claim map C-xx, dossier | sources graded, every number has a claim |
| 1 | `story-architect` | `drama`, `cast`, segment skeleton | `story_lint` 0 FAIL, REVIEWs answered |
| 2 | `scene-writer` (one segment per call) | segment `lines` (text, speaker, claims) | `stage_guard writer`, PV-12, PV-33 |
| 3 | `performance-director` | tags, emphasis, tone, emotion, pauses, interjections | `stage_guard performer` (words frozen), PV-12 |
| 4 | `edit-planner` | shots, motion, accents, bubbles, graphics, beds, sfx, music | `stage_guard editor`, `validate`: PV-24, PV-35, PV-36 |
| 5 | `voice-caster` | `voice`, `cast.<id>.voice` (traits, candidates) | `stage_guard caster`, PV-10, PV-32 |
| 6 | `shorts-writer` | `shorts` (10, at least 6 styles) | `stage_guard shorts`, PV-28, PV-34 |
| 7 | `script-critic` (fresh context) | findings only, each to its owner stage | SCRIPTING_SPEC gates, no "bored" window; at most 2 rounds |
| - | creator approval #1 | | nothing is paid before it |

## 1. The skeleton first (story-architect)
- Twelve premises, scored; the winner gets a one-sentence premise, a yes/no dramatic question and a promise.
- Heroes: each speaking hero has a want and a flaw (ST-04); the lead also a need and a change. Opposites talk best: the
  theorist and the hands-on one, the optimist and the cynic.
- The beat grid (`docs/STORY_ENGINE.md`): cold open in the action, the question by 0:15, a turn in every third, the
  midpoint reversal, the crisis, the climax, a button. Every join is BUT or THEREFORE (ST-02).
- Loops and set-ups are written before lines: L01 the dramatic question, a smaller loop opened every 2-3 minutes, a
  set-up planted in the first third that decides the end (ST-05, ST-06).
- Needs: pick at least three from curiosity, stakes, humour, wonder, fear, identity, justice, belonging, competence,
  surprise, and give each a segment (ST-08). Objectivity is the label on every segment: fact / reasoned / invented (ST-09).

## 2. Scenes (scene-writer), one segment per call
Input is small on purpose: the skeleton (one line per segment), this segment's drama, the last three lines before it,
the next beat, its claim ids, the arcs. The writer never sees shots or tags, so it cannot drift into them.
Dialogue rules DW-01..DW-08 in `docs/STORY_ENGINE.md`; narration rules N-01..N-10 in `narration-script`.

## 3. Performance (performance-director)
Delivery only; words frozen. Tags per speaker temperament, one stressed word, pauses before reveals and after
punchlines, interjections as reactions. Check with `stage_guard performer`.

## 4. Edit and sound (edit-planner)
Written per segment on the frozen words, with the accent vocabulary of `production/accents.py`: `wobble`, `punch`,
`shake`, `whip_in`, `flash_in`, `pop_text`, `slam_text`; plus bubbles, data visuals (ED-10), cards (ED-09). Every hard
accent has an effect (AL-03). Read the PV-35 report: events a minute, kinds per minute, alive share.

## 5. Voices (voice-caster)
Traits -> `audio/casting.query` -> ElevenLabs `creative_list_voices` (free) -> `casting.rank` -> three candidates.
A real person: documented traits only (claim ids), never an imitation, never the famous category, never a clone. The
creator picks after a one-chunk test read (EL-02).

## 6. The Shorts set (shorts-writer)
Ten moments, ten Shorts, at least six styles from the catalog (SS-01), alternating (SS-02), each with its ending kind.

## 7. Critic
Fresh context, reads as a viewer every 30 seconds, sends each finding to the stage that owns it. Two rounds at most;
then the creator decides.

## Prompts for a Sonnet stage (how to brief it)
- Give the stage its rules by ID and the file paths, not pasted text; give it the exact fields it owns.
- Give it the whole skeleton every time (the map), but only the local text it works on (the territory).
- Ask for one segment per call; ask for a short report table at the end (what changed, which checks ran).
- Never ask a stage to "improve everything": name the finding and the owner.
