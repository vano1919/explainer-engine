# Creator Override — Narration, Dialogue, Visual Lanes and Shot Duration

**Decision ID:** D-95  
**Decision date:** 2026-11-04  
**Applies to:** CrossWorld Chronicles / Explainer Engine, 12-minute animated historical docudrama  
**Authority:** Explicit creator instruction. This document supersedes older conflicting recommendations only within the scope below.

## 1. Spoken content ratio — independent from visuals

Target the script and finished spoken content as:

- **Narrator narration: 70–80%** of audible spoken content.
- **Voiced character dialogue: 20–30%** of audible spoken content.
- **Planning midpoint: 75% narrator / 25% voiced dialogue.**

The ratio is measured from audible spoken words at script/variant validation. Lines explicitly marked `voiced: false` (for example, silent speech bubbles or non-voiced textual beats) are excluded from the dialogue numerator and spoken-word denominator.

Do not calculate narration share from:
- the percentage of runtime assigned to acted/character scenes;
- the VIDEO / STILL / HELPER visual lane allocation;
- the number of shots, frames or segments;
- the existence of LTX video.

**LTX video is not synonymous with dialogue.** A shot can be VIDEO and have no character speaking. A battle, overhead troop movement, marching formation, crafting task, environment action or camera-led sequence may carry narration, sound design or no speech at all.

The authoring word ratio is a measurable script-stage proxy. It does not by itself prove an exact 70/30 split of the finished 12-minute wall-clock runtime: narrator and character delivery speeds, pauses, silence and music-only intervals can differ. When actual voice/timeline durations are available, report the measured audible narrator and character seconds separately as a production QA metric. Do not silently claim that a word-share test guarantees an elapsed-time share.

## 2. Visual runtime ratio — D-93 remains unchanged

The independent visual runtime budget remains:

- **60% VIDEO:** generated video, including non-dialogue LTX action.
- **30% STILL:** still-image compositions where Python adds, layers, animates or moves objects.
- **10% HELPER:** maps, diagrams, progress indicators, calculations, counters and other Python-made helper visuals.

The total is 100%, with the existing **±5 percentage-point tolerance**. This is a flexible production target, not a reason to damage the story or spend more money to satisfy a percentage.

These visual lanes do not describe who is speaking. A VIDEO shot may contain narration, character dialogue, sound effects, music or no speech. A STILL or HELPER shot may also sit under narration.

Keep the existing STILL-specific motion/hold rules, including BP-109 and BP-170. Do not apply a still-image duration cap to LTX VIDEO clips.

## 3. Shot duration — intent-based, not one universal cap

### Visible voiced dialogue / lip-sync coverage

A shot whose purpose is to show a character visibly speaking or to carry lip-sync coverage has a **5-second maximum planning target**.

The purpose is to reduce long fragile AI facial performances and make it easier to keep mouth movement, acting and identity coherent. The editor may use motivated coverage, such as the listener's reaction, a hand/prop insert or an over-the-shoulder angle.

This is a dialogue coverage rule. It is not a universal video-duration rule.

### Non-dialogue VIDEO action

A non-dialogue VIDEO shot may run **10–15 seconds** when the uninterrupted action, geography or camera choreography is clearer and more dramatic as one continuous shot.

Examples:
- overhead / Trojan-style battle choreography and troop movement;
- a continuous battlefield camera move that reveals scale, formation and changing geography;
- a character carrying out a simple task or making something;
- a continuous physical action whose cause-and-effect would be weakened by arbitrary cuts;
- environmental or establishing action where the camera movement is itself part of the storytelling.

Do not split these shots into 5-second pieces merely to satisfy the dialogue limit. Split only when there is a real narrative beat, a visual change that deserves a cut, continuity/identity risk, pacing reason, or an actual provider/model constraint.

**15 seconds is a planning ceiling, not a universal technical guarantee.** The selected model, API/adapter, resolution, frame rate and generation mode may impose a lower maximum. The generation adapter must enforce the actual selected provider/model constraints. Where a model cannot render the planned duration, find a compatible generation strategy or a motivated split; do not pretend all models support 15 seconds.

### STILL and HELPER

STILL and HELPER are separate lanes with their own constraints. Preserve the STILL motion/hold ladder and BP-170 requirements. A long Still hold must not be disguised as a 15-second LTX shot. Conversely, a 10–15-second LTX action must not be rejected because STILL has a shorter hold limit.

## 4. Required implementation and synchronization

The active single-source registry and all dependent validators/docs must reflect D-95.

Expected behavior:
- BP-105 validates 70–80% audible narrator word share; voiced character dialogue is the complement.
- BP-105 excludes `voiced: false` character lines.
- Variant planning reports an unknown speech share when spoken-word data is absent. It must never infer narrator share as `1 - played runtime`.
- BP-108 distinguishes voiced dialogue/lip-sync coverage (5s) from non-dialogue VIDEO action (up to 15s planning ceiling).
- KP-06 and KP-36 apply the duration rule according to shot intent.
- D-93 / BP-109 remains 60/30/10 ±5pp and is tested independently from BP-105.
- Agent and skill instructions explain that LTX / VIDEO does not imply character dialogue.
- The canonical decision log, rule registry, generated rule table, story/shot specifications, tests and Claude handoff remain synchronized.

## 5. Precedence and preservation

The earlier Master Mold v2.1.0, prior Integration Roadmap and their Git history must remain available for comparison. Do not delete or overwrite historical versions.

Claude must:
1. Read this D-95 override first.
2. Read the earlier Master Mold and Integration Roadmap.
3. Trace each old rule to its actual code, schema, validator, tests, agent and skill.
4. Compare **CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION**.
5. Apply D-95 only where it explicitly supersedes an older rule.
6. Preserve D-93 and all unrelated approved constraints.
7. Flag other Gemini-generated “locked creator decisions” as unverified unless separately recorded in the canonical decision log.

No paid API generation, GPU pod, production render, YouTube Studio change, upload or publishing action is authorized by D-95.
