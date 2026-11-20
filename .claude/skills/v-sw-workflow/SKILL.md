---
name: v-sw-workflow
description: Keep a docudrama script project on track across sessions - which stage it is in, what that stage must deliver, which writing skill to load, when to go back a stage, and where the state lives (the episode folder, never a loose story bible). Use when starting or resuming an episode script, when asked "what next" on a script, and when several writing skills fire at once and need ordering.
---

# Script project workflow and state (layer L2, every stage)

Built from jtydhr88/screenwriting-skills, page `sw-workflow` (MIT, commit `51115f18d1`), a meta-skill that routes a script
through stages and keeps state in a story bible. Rewritten for this channel under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)): our state is the episode folder and our router is
`scripting/stage_guard.py`. Upstream Chinese text: `UPSTREAM_SKILL.md`; term anchors used by every `v-sw-*` page:
`terms.md` (kept here because the other pages link `../sw-workflow/terms.md`, which resolves to this folder's file).

## The session protocol

**Start of a session.** Read `docs/PROGRESS.md` (last entry first), then the episode folder: `episode.json`,
`story/production_script.json`, `script_variants.json`, the claim map, `editorial_review.json` if any. Run
`python -m explainer_engine.scripting.stage_guard` to see which stages have a record and which are stale. Say in one line
where the project stands before touching anything.

**During.** One stage at a time. Each stage reads its page in `.claude/agents/` and the files it names, records
`stage_guard start`, writes only its own fields, and runs its gate. A design flaw found while writing goes back to the
stage that owns it (the skeleton, the header, the cast card); it is never patched in the lines.

**End of a session.** Every result saved as it is produced (OR-33 for anything paid; for script work: the JSON written
through `core/store.write_json_atomic`). One `docs/PROGRESS.md` line: what changed, which gate passed, what is next.
At the usage-limit threshold the unfinished work is backed up first (OR-30: project files plus a WIP commit).

## Stage map for an episode

| Stage | Deliverable | Load | Exit check |
|---|---|---|---|
| 0 research | dossier + claim map | `science-grounding`, `v-fact-check-workflow`, `v-source-verification` | every number has a claim |
| 0b premise | two or three story variants | `v-sw-premise-theme` | the creator's pick (project rule 0) |
| 0c series film | two or three era films | `v-director-cinematic` (style lens section) | the creator's pick (rule 20) |
| 1 skeleton | `drama`, `cast`, segments, scene headers | `v-sw-story-structure` | `story_lint` 0 FAIL, PV-48 headers |
| 2 scenes | lines per segment | `dialogue-scenes`, `v-sw-scene-craft`, `v-sw-dialogue` | `stage_guard writer`, `scene_lint` |
| 2b beats | visual beats and cues | `visual-beats` | PV-44 |
| 3 delivery | tags and emphasis | `elevenlabs-voice`, `narration-script` | `stage_guard performer` |
| 4 edit and sound | shots, routes, sound plan | `v-director-cinematic`, `film-direction` | `validate` |
| 5 voices | casting | `voice-search` | PV-10, PV-32 |
| 6 Shorts | Shorts set | `shorts-for-video` | PV-28, PV-34 |
| 7 critic | editorial review | (fresh agent `script-critic`) | `production.editorial_gate` |
| approval | the creator's word on the script | | `scripting/script_approval.py` |

## Going back a stage

Going back is normal and cheap before money is spent. The usual causes:
- Lines will not come alive in stage 2: the scene header has no real opposing want (back to 1), or the hero has no flaw
  (back to the cast card).
- The critic finds the middle sags: a missing midpoint or repeated complications (back to 1).
- The read sounds flat in the test read: the delivery (3) or the sentence shape (2); never fix it with more tags alone.
- The edit plan cannot show a beat with our routes: the beat is unshootable (back to 2 or 1, or move it to the narrator).

Every return is logged in one line in the episode's notes and in `docs/PROGRESS.md`.

## How the exit checks are used

The exit checks are gates, not grades: a FAIL stops the next stage; a REVIEW is either fixed or answered in one line; a
check that did not run is NOT_RUN and is said so (final plan P-7). Nobody self-certifies a stage that has no check: the
critic or the creator decides.

## Delegation and parallel work

The writers' room runs inline in one main agent and spawns only the critic (OR-20, D-79). Stages are sequential by design:
each depends on the frozen output of the one before. A small, well-specified side task (a search, a formatting pass, a
count) may go to a cheaper subagent with the exact files and fields; never a creative stage.

## Language and terms

The script, prompts, titles and everything the viewer sees or hears are English for the US audience; the creator is
answered in Georgian. When a `v-sw-*` page uses a craft term, use the original term (premise, controlling idea, beat,
turning point) as anchored in `terms.md`; do not coin translations.

## Writer and director split

The writer owns words and story; the director owns pictures and sound (skill `v-director-cinematic`). The writer may
suggest a picture only through `visual_beats`; the director may ask for a line change only through a critic finding to
stage 2. Neither edits the other's fields; `stage_guard` proves it.

## Anti-patterns

- Writing lines before the skeleton passes.
- Fixing a story problem with wording.
- Keeping state in a chat or a loose markdown file instead of the episode folder.
- A stage that "improves everything" instead of its own fields.
- Calling a stage done because the agent feels it is done.

Not used from upstream: the TV-series and opera stage tables, the novel hand-off, `story-bible.md` as the state file, page
targets per stage.
