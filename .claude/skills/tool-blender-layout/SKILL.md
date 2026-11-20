---
name: tool-blender-layout
description: Build a headless Blender grey blockout of a scene - plain primitives for the place, capsule people at real height with a facing marker, real cameras at the planned height and lens - and render the framing as layout pictures that fix where people stand and where the camera looks before Gemini draws the scene, as free previs on the owner's PC or CI. Not the retired Blender render route. Use when a scene with several people keeps coming back mis-staged, when a camera position must be agreed before pictures, and when anyone proposes using Blender for a v4.3 episode.
---

# Blender grey blockout as previs, the tool (layer L11, stage S6 before G5)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for one narrow use: grey boxes and
real cameras that settle staging before pictures are made. Blender makes no final pixel of a v4.3 episode (D-131); the
old Blender scene and J5 render route is legacy. Staging decisions themselves are skill `v-director-cinematic`; continuity
across shots is skill `v-scenario-storyboards`; pictures are skill `tool-gemini-task-pictures`.

## When to use, when not

- Use for a scene where a group must be staged (who stands where, who faces whom, how far the camera is), when Gemini
  keeps pushing figures away or swapping sides, and when the owner wants to see the camera before pictures.
- Not for final frames, textures, lighting looks, rigs or character animation. The legacy Blender render lanes (J5 shots,
  NPR looks, the clay/depth/line layout passes of the old J2/J4 routes, D-116) stay retired for v4.3.
- Not inside the episode runner: `explainer_engine/blender/` is an entry of `config/retired_era.json` (`blender_scene`),
  and `explainer_engine/episode/retired.py` (`refuse`) stops it when the working folder or `$EXPLAINER_EPISODE` is a v4.3
  episode. Run the blockout in a lab folder outside `episodes/<id>/` and bring back only PNG pictures and their hashes.
  Changing that boundary is the owner's word, recorded first.

## What exists, and what is only planned

- On 2026-11-19 (overnight log, stream B) a free test rendered six grey layouts for the Truce 1914 pairs: trench walls,
  fire step, ladder, wire stakes, lane, parapet, tree, capsule people at 1.75 m with a head marker for facing, cameras at
  the batch's 35, 50 and 28 mm; 1920x1080 clay with a faint floor grid; saved to HF under
  `explainer-engine/demo_truce_1914/blocking_2026-11-19/`. Its script `blender_blocking.py` sits on draft PR 217, not in
  this checkout: read it on its branch before reusing it.
- The 2026-11-20 series plan (owner's word 06:42 UTC: lay out the whole series with figures in Blender) proposes a scene
  spec `blender_scene/1`, a compiler from continuity cards, validators V1-V7 and a free test T0. None of that is built.
  Its use of the layout as a video conditioning input for the clip model is a separate, owner-gated question (its Q1),
  because it revives a retired route (D-132 kept only the distilled worker on Modal).
- Reusable pieces in `explainer_engine/blender/`, all legacy code that still runs outside an episode:
  `explainer_engine/blender/project.py` (the pinned binary, `config/cloud_pins.json` `blender`, sha256-checked install),
  `explainer_engine/blender/camera_setups.py` (named setups: lens, height and distance in head heights, a thirds target;
  `framing` says where a world point lands in frame), `explainer_engine/blender/render.py` (headless adapter, durable
  frames), `explainer_engine/blender/validate.py` (frame checks), `.github/workflows/blender-smoke.yml` (manual CI smoke).

## The procedure

1. **Start from the director's book**: per shot the place, who is in it, which way each faces, the camera height and
   lens, start and end positions. Without blocking there is nothing to lay out.
2. **Build the place from primitives** at real scale (metres): ground, walls, openings, the one or two props that fix
   geography (a ladder, a tree, a doorway). Detail only where the frame reads a silhouette.
3. **People as capsules** at real height with a facing marker on the head, one per named hero plus counted extras;
   name each object by its hero id so the picture prompt can map it.
4. **Real cameras**: position, height and lens from the shot row; aim with `camera_setups.framing` logic or by hand.
5. **Render headless**: `blender --background --factory-startup --python <script> -- <args>`, Workbench or Cycles on
   CPU, at 16:9. Free runs start without asking (D-114) on the owner's PC or a GitHub Actions run (D-113 as amended).
6. **Check the frames** before anyone draws from them: every named figure visible and separated, faces large enough to
   read (the blocking note found a figure 100 m away is about 47 px tall and faceless), the eyelines and the 180-degree
   line as the book says, nothing clipped by the frame edge.
7. **Hand over**: PNGs plus a plan view, their sha256, the script and the `.blend` to HF; the owner looks at the plan view.
8. **Use in Gemini as image 1 of a layout batch**, with the sentence that it is only a layout guide, not the look. Cost
   measured on 2026-11-19: placement improved and pair 3 was the best of all batches, but an attached image dropped the
   output to 1376x768 and Gemini still moved figures further away in pair 2. So it is a tool for group staging, used per
   scene where staging failed, followed by the free 2x upscale; plain batches stay the default input.

## Hard rules at this layer

- Grey only; never let the blockout's colour, light or capsule shapes reach a final frame or a prompt's look words.
- Real units and real heights; a 1.75 m capsule next to a 2 m trench wall is the point of the exercise.
- One scene file per place, so the next shot of the same place starts where people stood (no re-building per shot).
- Nothing paid: no GPU render, no Modal GPU, no pod. A layout that seems to need a GPU is the wrong layout.
- Untrusted add-ons and MCP bridges stay out: the community Blender MCP sends a minimal usage record by default (per
  the SK-1 notes) and drives a live GUI; our runs are headless scripts we read first.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| Figures overlap in a narrow trench | bay too narrow for the action | widen the bay (the S07_SH006 fix: 3.2 m) or move the camera off-axis |
| Faces tiny in the layout | camera too far for the lens | move closer; re-check the head height in pixels |
| Gemini ignores the layout | the guide sentence missing or the shot too wide | add the guide sentence; tighten the shot |
| Blender refuses to run in the episode folder | `retired.refuse` | work in a lab folder; never patch the refusal |
| Version mismatch | not the pinned binary | `python -m explainer_engine.blender.project resolve` |

## Checks in code

`explainer_engine/blender/project.py` (version pin), `explainer_engine/blender/validate.py` (frame files, sizes),
`explainer_engine/episode/retired.py` (the episode boundary). The plan's V1-V7 validators are planned, not built.

## Sources (idea sources only, no text copied)

- codepawl/creator-generalist, page `3d-generalist` (MIT, commit `57bcdb718c`): grey blockout or animatic with the real
  cameras before the look; build to camera, detail where the frame looks.
- kajisho5/blender-skill (MIT, commit `1c1e47cc97`): headless `blender -b --python` scripts that write JSON results,
  probe before operate, dry runs.
- mlolson/blender-orchestrator (no licence file, commit `a9dfb32d41`): README idea only - real-world sizes and spatial
  checks so a model can see a layout.
- ahujasid/blender-mcp (MIT, commit `a5a8acf2c6`): an optional live tool; not used, see the rule above.
