---
name: animation-principles
description: Judge and direct the character animation of a Crossworld Theories episode by the twelve principles of animation (squash and stretch, anticipation, staging, pose to pose, follow-through, slow in/out, arcs, secondary action, timing, exaggeration, solid drawing, appeal), plus moving holds, blinks, planted feet, lip-sync and identity. Use for every keyframe/next-pose pair, every LTX clip review, and whenever a clip looks stiff, floaty, frozen, off-model or out of sync.
---

# Animation principles: characters that move like they think

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role image` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Department page of the craft curriculum (P3b, [CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)). Our animation is a
keyframe and a next pose (KP- rules, docs/SHOT_PROMPTS.md) turned into a clip by a video model; we do not draw in-betweens,
so the principles are mostly things we **write into the poses** and **check in the clip**. Sources:
`docs/research/CRAFT_SOURCES_2026-10.md` sections 4 and 5 (the list of the twelve, attributed to Thomas and Johnston's "The
Illusion of Life", 1981, through Wikipedia; SyncNet and ArcFace papers for the measurements). Williams' "Animator's Survival
Kit" and Alan Becker's series were not opened; every cadence below is a hypothesis to be measured on the creator's cartoons.

## The twelve, as we use them

| principle | in the keyframe / next pose | in the clip |
|---|---|---|
| squash and stretch | a body that compresses before a jump, keeping its volume | no rubber limbs, no volume loss |
| anticipation (KP-12) | the wind-up pose before the action | the action does not start cold |
| staging | one idea per shot, readable in silhouette | nothing competes with the action |
| straight ahead / pose to pose | pose to pose: the two poses carry the story | the model's in-betweens stay between them |
| follow-through and overlap (KP-16) | the cloak and hair still moving at the end pose | parts settle at different times |
| slow in and slow out | poses at the extremes of the move | limbs ease too, not only the camera (BP-23) |
| arcs | the path implied by the two poses curves | hands and heads travel on arcs |
| secondary action (KP-29) | breath, cloth, hair left free in the prompt | they move without stealing the read |
| timing | the shot's length from BP-107, holds within BP-109 | no metronome, no rush |
| exaggeration | in the caricature and the acting, never in the facts | the peak gesture reads |
| solid drawing | turnarounds and hero sheets (D-55) | no duplicated or missing limbs |
| appeal | the hero on model | the same hero from shot to shot |

## Holds, blinks and feet

- **A held character breathes.** A hold longer than BP-132's limit carries a moving hold (a blink, a weight shift, a
  breath); blinks come at BP-132's cadence and on a thought change, never in the middle of a stressed word.
- **A planted foot does not slide.** The foot's contact point stays put while the weight is on it; the pixel limit is set
  by measuring the creator's cartoons (`training/video_qa.py`, P8).
- **Camera breathing is not character breathing.** The Blueprint's continuous camera "breathing" is conflict 7 of the
  curriculum; BP-24 stays in force (a shake only as an accent on an impact).

## Acting that is measured (P8)

- **Lip-sync:** every full-tier spoken shot gets an offset and a confidence (SyncNet method, BP-133). SyncNet was trained on
  real faces; on cartoons it is a hypothesis until it agrees with the creator's eye on our own clips.
- **Identity:** a face-embedding score against the hero sheet (ArcFace class); the threshold is calibrated on our sheets,
  never the Blueprint's number (BP-133). A shot that fails twice falls back to KP-43's mouth-hiding fallback (BP-113).

### CHECKLIST (animation)

Rendered from `explainer_engine/standards/craft_checklists/animation.json` (the one home of these ids;
`python -m explainer_engine.standards.craft write` regenerates it, `tests/unit/test_craft_checklists.py` fails when they
differ). Every row is a hypothesis until a second source type is verified.

<!-- craft-checklist:animation:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-ANI-01 | eye | squash and stretch keep the volume | clip frames | - | manual |
| CRAFT-ANI-02 | eye | anticipation before every big action | clip frames + next pose | KP-12 | manual |
| CRAFT-ANI-03 | eye | staging: one idea read at a glance | keyframe | - | manual |
| CRAFT-ANI-04 | eye | pose to pose: keyframe and next pose carry the action, the model fills between | keyframe + next pose | - | manual |
| CRAFT-ANI-05 | eye | follow-through and overlapping action | clip frames | KP-16 | manual |
| CRAFT-ANI-06 | eye | slow in and slow out on limbs, not only on the camera | clip frames | BP-23 | manual |
| CRAFT-ANI-07 | eye | actions move on arcs | clip frames | - | manual |
| CRAFT-ANI-08 | eye | secondary action (hair, cloth, breath) is free | clip frames | KP-29 | manual |
| CRAFT-ANI-09 | code | timing: shot rhythm and hold share | shot cards | BP-107, BP-109 | `explainer_engine/scripting/film_shots.py` |
| CRAFT-ANI-10 | eye | exaggeration in the caricature, never in the facts | keyframe | - | manual |
| CRAFT-ANI-11 | eye | solid drawing: no duplicated or missing limbs | clip frames (VQ-10) | - | manual |
| CRAFT-ANI-12 | eye | appeal: the hero stays on model (hero references, D-55) | clip frames | D-55 | manual |
| CRAFT-ANI-13 | eye | a held character breathes: blink cadence and a moving hold on long holds | clip frames (eye state over time) | BP-132 | manual |
| CRAFT-ANI-14 | eye | a planted foot does not slide | clip frames (foot contact point) | - | manual |
| CRAFT-ANI-15 | code | lip-sync offset and confidence measured on every full-tier spoken shot | clip + its line's audio | BP-133 | `explainer_engine/qa/identity.py` (planned, P8) |
| CRAFT-ANI-16 | code | identity score against the hero sheet, threshold calibrated on our own sheets | clip frames + hero sheet | BP-133 | `explainer_engine/qa/identity.py` (planned, P8) |
<!-- craft-checklist:animation:end -->

## Sourced rules (docs/SOURCED_RULES.md)

The numbers of this page live only in the registry (D-59); code reads them with `sourced_rules.T`.

- BP-132: blink cadence and the moving hold on long holds (hypothesis, REVIEW).
- BP-133: lip-sync offset and the identity threshold, calibrated on our own sheets (hypothesis, REVIEW).
- BP-107, BP-109, BP-113: shot rhythm, the hold share, the AI-acting cap (already in force).
