---
name: story-engine
description: Run the writers' room of a docudrama history episode from the creator's story to a frozen production script - two or three story variants, the series film choice, a beat skeleton with stakes and turns, scenes with dialogue inside them, delivery, the edit and sound plan, voices, Shorts and one fresh critic - as gated stages that each own their fields. Use for every new episode script, when a script feels flat, and when a stage needs to know what it may change.
---

# Story engine: the writers' room (layer L2, stages S1-S3)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)). The method behind each stage comes
from the vendored screenwriting skills (`v-sw-premise-theme`, `v-sw-story-structure`, `v-sw-scene-craft`, `v-sw-dialogue`,
`v-sw-workflow`, all rewritten for us); this page owns the order, the owners, the gates and the fields. The rule ids live in
[STORY_ENGINE](../../../docs/STORY_ENGINE.md) (ST story, SC scenes, DW dialogue, PF performance, MO motion, AL sound layers,
VC casting, SS Shorts); numbers live in the sourced registry ([SOURCED_RULES](../../../docs/SOURCED_RULES.md), BP ids).

## What we are making

An 8-15 minute English docudrama for a US audience: a true historical event told as a story, with the narrator carrying
about 70 % of the spoken words and the heroes about 30 % inside played scenes (D-99, BP-105). The story is the product;
hooks, motion and sound only turn the viewer toward it (the creator, 2026-10-20). Every factual sentence maps to a claim
with a source (invariant 5, skill `science-grounding`); the drama lives in what people do, never in invented facts.

A good episode has a **spine**: one person or small group, one question the viewer can hold in one breath (yes/no,
ST-01), and a clock ("by Christmas morning", "before the ice breaks"). If the topic has no spine yet, the research is not
finished.

## The order of work (the creator's rules 0 and 20, then the stages)

| # | Stage (page in `.claude/agents/`) | Writes | Gate (free) |
|---|---|---|---|
| 0 | research (orchestrator; skills `science-grounding`, `v-fact-check-workflow`) | claim map C-xx, dossier | every number has a claim, sources graded |
| 0b | **story variants** (`story-architect` step 1b) | two or three short story variants (half a page each: spine, question, three turns, ending) in `script_variants.json` (`scripting/variant_plan.py`, VP rules) | the creator picks one (project rule 0: the short story is approved before any script) |
| 0c | **series film** | two or three successful films set in that era, one line each on what they look like, a recommendation | the creator picks the film (rule 20); it becomes the one style lens (skill `v-director-cinematic`) |
| 1 | `story-architect` | `drama` (premise, yes/no question, promise, loops, set-ups, needs), `cast` with want and flaw, the segment skeleton, the beat template (A/B/C), every dialogue segment's `scene` header | `story_lint` 0 FAIL, headers complete (PV-48) |
| 2 | `scene-writer`, one segment per call (skill `dialogue-scenes`) | segment `lines`: text, speaker, claims, `to`, `intent` | `stage_guard writer`, PV-12, PV-33, PV-48 |
| 2b | `beat-writer`, same segment (skill `visual-beats`) | line `visual_beats`; opt-in cues, each with its story `event` | `stage_guard beats`, PV-44 |
| 3 | `performance-director` (skill `elevenlabs-voice`) | tags, the one stressed word, tone, pauses; words frozen | `stage_guard performer`, PV-12 |
| 4 | `edit-planner` | shots and routes, motion, the sound bed and events, music, the edit plan per video shot (VL-01) | `stage_guard editor`, `validate` |
| 5 | `voice-caster` (skill `voice-search`) | `voice`, `cast.<id>.voice` | `stage_guard caster`, PV-10, PV-32 |
| 6 | `shorts-writer` (skill `shorts-for-video`) | `shorts` | `stage_guard shorts`, PV-28, PV-34 |
| 7 | `script-critic`, spawned fresh | `editorial_review.json` with findings routed to their owners, and the one-page Georgian `story_page.md` | `production.editorial_gate`; at most two rounds |
| - | **creator approval of the script** (OR-17, `scripting/script_approval.py`) | | nothing is paid before it |

Each stage starts by reading its page and the files the page names, and records it with `stage_guard start`; `stage_guard
fresh` flags an output written from memory (OR-32). The main agent runs stages 0-6 itself in order and stops at the first
failed gate; only the critic is a separate agent with a fresh context (OR-20, D-79). On a v4.3 script the same stages own
the v4.3 fields (`edit_plan`, `av_contract`, `sound_events`, `intentional_silence`, a segment's `mood` and `music`, a
place's `ambience_bed`); the owner table is in STORY_ENGINE ("The v4.3 episode script: who owns the new fields").

## Building the skeleton (stage 1)

**Premise.** Load `v-sw-premise-theme`. Write the premise as a value plus its cause ("men stop a war for one night because
the enemy sings the same carol"), the dramatic question as yes/no, and the promise of the title. Test the controlling idea
against its counter-idea: the episode is strongest when the opposite was also possible (orders, snipers, officers).

**Structure for a 10-minute docudrama.** Load `v-sw-story-structure` for the vocabulary (inciting incident, progressive
complications, midpoint, crisis, climax, resolution). Our length compresses it:

| Part | Share of the runtime (the clock measures; BP-75 holds the midpoint band) | Job |
|---|---|---|
| Cold open | first 30 s | the most striking true moment, the question, the promise (BP-03, BP-04) |
| Setup | to about 15 % | the world, the hero's want, the clock; context only after the tension (BP-05) |
| Escalation | to the midpoint | each segment a complication; joins are BUT or THEREFORE, never "and then" (ST-02) |
| Midpoint | mid-story (ST-12) | a revelation that changes what the hero wants or what the viewer believes |
| Crisis to climax | the last third | the hardest choice, played as the longest scene with dialogue (ST-18) |
| Resolution and coda | the last tenth | the answer to the question, the real record, the cost, one image that stays |

A turn lands at least every BP-76 gap (ST-13); every segment after the opening names what is lost if it goes wrong (ST-03);
at least two turning points of different kinds (ST-07); a set-up planted in the first third decides the end (ST-06); loops
are declared and paid in order (ST-05); at least three human needs are each served by a segment (ST-08).

**Beat templates.** A (three-act with seven points, the default), B (Save the Cat compressed), C (mystery ladder for a
"how did this happen" episode). The choice is recorded in `drama`.

**Heroes.** Real people from the claim map, named (never "a soldier" when the record has a name). Each speaking hero gets
a want, a flaw and a speech card (DW-11, skill `narration-script` for the register examples); the lead also a need and a
change (ST-04). Pair opposites: the officer and the private, the believer and the cynic. A hero's lines are only what the
record allows him to plausibly say; quotations from the record are short and sourced.

**Scenes.** Every segment with dialogue gets its header before a line exists (SC-01; field guide in skill
`dialogue-scenes`). A docudrama scene is small and concrete: one place, one present moment, two wants that collide.

## Writing, beats, delivery, edit, voices, Shorts (stages 2-6)

- **Scenes** go one segment per call. The writer gets the whole skeleton (the map) but only its local text (the
  territory): this segment's header, the cast cards, the last three lines before it, the next beat, its claim ids. It never
  sees shots or tags. Hand-off unit: narrator in on the pressure, the scene of 5-12 beats, narrator out on the consequence.
- **Visual beats** follow at once on the same frozen words: something new on screen wherever new information lands, the
  listener's reaction on the line that lands, cues only where a named event earns one.
- **Delivery** never changes a word (`stage_guard performer` proves it).
- **Edit and sound** plan per segment: the route of every shot (D-131 shares, `episode/router.py`), one action and one camera
  behaviour per video shot (D-132 clips speak their one line, VL-02), the continuous sound bed of each scene and at least
  three effects tied to visible events, music by chapter, one planned dropout before the biggest reveal, J and L cuts on
  scene cuts, visual-association bridges between scenes, maps last.
- **Voices**: traits to library search to three candidates; a real person is never imitated or cloned (PV-10).
- **Shorts**: up to ten, from the frozen script, styles alternating (SS-01, SS-02).

## The critic (stage 7)

Fresh context, reads as a viewer every 30 seconds, then walks the whole script once as one timeline (the integrated
production-coherence pass, D-60): causality, each hero's entrance, each line against its speaker and the line before, each
shot and cue against its instant, delivery against meaning, the estimated clock. Each finding goes to the stage that owns
it. FAILs block the editorial gate, paid narration and paid assets until fixed and re-reviewed; any edit invalidates the
review by hash. A rule whose check did not run is reported as not run, never as passed (known gaps: on a
`schema_version 4.0.0` script some ST and SC rules do not run yet; the critic reads them by hand and says so).

## Briefing a stage (when a stage is delegated)

Give it the rule ids and file paths, not pasted text; the exact fields it owns; the whole skeleton and only its local text;
one segment per call; and ask for a short report table (what changed, which checks ran, what is NOT_RUN). Never ask a stage
to "improve everything": name the finding and the owner. Script text is written by the thread's own model, never generated
through the Claude API (project rule 15).

## What the vendored methods give and what stays ours

| Vendored skill | Use it for | Ours wins on |
|---|---|---|
| `v-sw-premise-theme` | premise as value plus cause, controlling idea, logline tests | the yes/no question, the creator's variant card |
| `v-sw-story-structure` | inciting incident, complications, crisis-climax-resolution, openings and endings | every number (BP ids), the beat templates, BUT/THEREFORE |
| `v-sw-workflow` | stage discipline, a state that survives sessions | our stage table, `stage_guard`, the episode folder as the state (no `story-bible.md`) |
| `v-sw-scene-craft`, `v-sw-dialogue` | value turns, beats, subtext, exposition as ammunition | the scene header, the narrator hand-off, one line per clip |

Not used: page counts, screenplay format, TV-series and stage-play branches, any upstream hand-off to a novel.

## The /3 inversion still holds

Nothing goes in by default. A scene must turn a value, a cut must have a reason, a sound must name its story event, or it
is deleted. The evidence behind every number: `docs/research/STORYTELLING_EDITING_2026-10-19.md`; for docudrama episodes
read `docs/research/DOCUDRAMA_REFERENCE_LIBRARY.md` before story planning (craft evidence only, no copied scripts).

Rules: ST-00..ST-24, SC-01..SC-12, DW-01..DW-13 and the N, EL, ED, SH, PV rules. The output is ONE `production_script.json`
(D-43): text, voices, pictures and prompts, sounds and the edit, written before anything is paid (project rule 1).
