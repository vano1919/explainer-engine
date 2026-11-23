# Overlay for `v-scenario-video-color-grade`: Colour grade by code (layer L22, stage G9)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from scenario-labs/skills, page `scenario-video-color-grade` (MIT, commit `a14d061fe5`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for our finish: math on the pixels, no generative model, no
Scenario call. The upstream text is this folder's `SKILL.md`. Its local scripts stay usable and never call
Scenario: `scripts/render_looks.py`, `scripts/inspect_frame.py`, `scripts/match.py` with their helpers `grade.py`,
`spatial.py`, `media.py`, plus `assets/looks_library.json`, `examples/looks.json` and `references/*.md` (table below).

## Where the grade lives here

The episode's real grade is in our code, run by the assembly stage, not by these scripts:
- `explainer_engine/finish/grade.py`: the era look (saturation, contrast, shadow and highlight tints, black level, grain)
  with parameters from the `grades` table of `explainer_engine/world/eras.json`, and the shot-to-shot transfer (Reinhard
  mean and spread in CIE Lab toward the scene's key master frame, blend capped, BP-130).
- `explainer_engine/production/assemble.py`: per scene one key master frame and one grade from that table; a grade name
  not in the table is refused (invariant 7). The transfer runs first on each raw shot; the era look is the last step over
  every picture (ED-04: one constant look over the whole episode, never switched on and off).

So the vendored scripts are a lab: to try a series look on our own stills, to see what a recipe does before it becomes
grade parameters, and to hand the creator a comparison grid. A new or changed grade entry for an episode is a decision
for the creator (OR-22), not a silent edit.

## Why it matters on this channel

Three sources meet in one scene: Gemini stills (warm, clean), LTX clips (their own contrast and colour drift), and 2.5D
renders of a still. Without a pull toward one key frame the cut shows the seam even when the drawing matches. The series
film (rule 20) sets the target in words; the grade makes all three sources agree with it.

## Procedure

1. **Look first.** Pull three or four frames from different shots of the scene and from the key master frame. Note
   the light direction, skin, the darkest dark and the brightest sky. A source that is already contrasty needs a gentler
   recipe than a flat one.
2. **Pick the key master frame** of the scene: the approved master picture (CT-03), never a clip's drifted frame.
3. **Still test before any video.** `python3 scripts/render_looks.py <clip_or_frame> --looks <looks.json> --out <dir>
   --frame <n>` writes stills and a labelled `grid.jpg`. Check every candidate against the source: skin believable, no
   clipped whites in the sky, blacks not crushed under the mud, the film's palette recognisable. Test two frames on a
   moving clip.
4. **Match by measurement** when a shot drifts: `python3 scripts/match.py <clip> <our_key_frame.png> <stats.json>` measures
   the Lab statistics; compare with what `finish/grade.py` `transfer_params` gives on the same pair. The reference is
   always one of our own approved frames, never a frame taken from the series film (rights rules: our own art only).
5. **Translate the winner** into the era-grade parameters the code reads (saturation, contrast, tints, black, grain),
   propose the entry to the creator with the grid, and only then add it to the table.
6. **Run the episode**: `python -m explainer_engine.episode run <episode> --to qa`; G9 applies the transfer and the look,
   G10 measures the master.
7. **Verify**: each graded output keeps its source's frame count and length; sweep a few cuts for flicker and skin.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| A cut between a Gemini still and an LTX clip jumps in colour | no key frame, or the transfer blend capped too low | set the scene's key master frame; check BP-130's row in the scorecard |
| Orange skin after the look | a warm tint on top of warm sources | cut the highlight tint, test on the portrait anchor |
| Mud and shadows turn to one black mass | contrast and black level stacked | lift the black, lower contrast, re-test on the darkest shot |
| Grain looks like noise on the 2.5D planes | grain applied before the upscale or twice | one grain, last, over the delivery frame |
| The look changes mid-episode | two grades on one series | one grade per series; a scene grade only as the table allows |
| Loop or chunk loses its last frame | `-shortest` with slightly shorter audio | keep the scripts' handling; avoid it in custom commands |

## Rules of our system at this layer

- Grade is a finish, never a repair for the wrong picture: a wrong place or a wrong object is R3, not a colour fix (P-5).
- No relight or day-for-night on a docudrama shot: it changes the light the claim map and the film agreed on. A small
  exposure or white-balance correction is R1.
- Public names of looks stay descriptive ("cold front", "bleach"); the film's title lives only in prompts.
- Every graded file is a new asset: its hash changes and its old observation no longer counts.

## Checks in code (SK-2)

`explainer_engine/finish/grade.py` (`blend_cap`, `lab_distance`), `explainer_engine/production/assemble.py` (grade name in
the table, key frame per scene), `explainer_engine/videolane/storyboard.py` (coverage palette against the master,
BP-166, before money), `explainer_engine/qa/final_frame_qa.py` (frames of the delivered output against the graded source),
`explainer_engine/episode/acceptance.py` (G10).

## References: when to open which

| Need | Open |
|---|---|
| Every colour op and its parameters | `references/ops.md` |
| How the library looks are built (bleach bypass, film stock, cold steel) | `references/looks.md`, then `assets/looks_library.json` |
| Twelve tuned example looks as a starting set | `examples/looks.json` |
| Measuring a region's hue, saturation and brightness | `scripts/inspect_frame.py` (`grid`, `sample`) |
| Keyed selective colour (rarely right for docudrama) | `references/keying.md` |
| Why relight is avoided here | `references/relight.md` |

## Not used from upstream

Scenario's preset LUT tools and segmentation masks, uploads and credit pricing, log-footage conversion (our sources are
display-referred), the showreel and its music, colour-swap and one-kept-colour looks, relight presets on story shots, and
any grade that runs outside the assembly stage for a delivered file.
