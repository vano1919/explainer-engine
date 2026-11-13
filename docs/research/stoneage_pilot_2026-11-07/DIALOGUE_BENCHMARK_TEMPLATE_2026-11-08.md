# Dialogue benchmark: LTX-only vs LTX + optional Blender

Status: **BLOCKED pending an approved LTX dialogue sample/audio pair or creator-approved generation.** Do not treat the synthetic J5 smoke as a dialogue benchmark.

## Fixed comparison setup

- One short dialogue exchange between two characters in one environment.
- Use one approved establishing image/location and the same approved character references in both pipelines.
- The opening segment targets about 5-9 seconds for this pilot evaluation. The target does not set a hard limit for other scenes.
- Use the actual dialogue audio and verified Rhubarb/phoneme timings for any J5 mouth animation.
- Keep output resolution, frame rate, audio mix and review conditions matched.
- Pipeline B starts with the same LTX establishing segment. Add only the close-ups or reactions needed for dialogue coverage.
- Do not create new character angles or a second environment image for this benchmark.

## Pipelines

| Pipeline | Sequence | Evidence to capture |
|---|---|---|
| A — LTX-only | LTX-generated dialogue scene; generate additional LTX coverage only if needed | source prompts/references, provider/model, generation attempts, clip and audio hashes, output frames/video, actual price and elapsed production time |
| B — LTX + optional Blender | Same LTX establishing segment, then optional J5 close-ups/reactions; same approved characters and place; mouth cues from the actual audio; background blurred from the same approved environment image | all Pipeline A inputs plus source cut-outs/variants, background source and derivative hashes, Blender version/engine/settings, rendered frames, edit points, setup/render/correction time |

## Review record

Fill one row per criterion. Mark `not reviewed` until a person inspects the rendered output. Keep measured values separate from judgments.

| Criterion | A — LTX-only | B — LTX + Blender | Evidence / notes |
|---|---|---|---|
| Character identity consistency | not reviewed | not reviewed | |
| Facial appearance | not reviewed | not reviewed | |
| Mouth synchronization against actual audio | not reviewed | not reviewed | |
| Expression quality | not reviewed | not reviewed | |
| Body and head movement | not reviewed | not reviewed | |
| Camera composition and spatial clarity | not reviewed | not reviewed | |
| Lighting consistency | not reviewed | not reviewed | |
| Background continuity | not reviewed | not reviewed | |
| Transition naturalness from LTX to J5 | not applicable | not reviewed | |
| Overall visual naturalness | not reviewed | not reviewed | |
| Asset-generation/preparation effort | not measured | not measured | person-hours; list every generated/edited asset |
| Setup/render/correction effort | not measured | not measured | person-hours and wall-clock time |
| Compute/provider costs | not measured | not measured | exact provider/model, actual billed amount and retries |
| Total production cost | not measured | not measured | include generation, preparation, setup, rendering and correction |

## Decision rule

Keep LTX-only when it provides enough usable footage. Consider J5 only for coverage LTX does not provide economically, and only if visual review accepts identity, naturalness, timing, lighting and transition quality. Do not count Blender's software price as total production cost; include asset generation, cut-out work, variant preparation, setup, rendering and manual correction.

## Current evidence and blockers

The local route-test handoff has creator-reviewed character and place stills, but no LTX dialogue video, paired dialogue audio/timings or four-state dialogue cut-outs. Blender is not installed on the current Windows host. The full comparison cannot be conducted from the available free/local resources, and no paid generation is authorized by this benchmark record.
