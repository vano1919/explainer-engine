# Blender scene proof of concept

**Branch:** `experiment/blender-scene-poc-2026-11-04`  
**Base:** `claude/master-mold-ready-2026-11-04`

## Purpose

A disposable, isolated test of whether Blender can produce a repeatable 3D animated scene that could later be compared with the current AI-image/2.5D pipeline.

This does **not** replace or modify the production renderer, contracts, scene planner, style system, spend caps, or existing visual pipeline.

## What the prototype builds

- A stylised medieval battlefield, castle silhouette, hero placeholder and three background soldiers.
- A reusable hero root with a five-second entrance/gesture animation and a subtle camera push-in.
- Orthographic camera, area lighting, 1280x720, 24 fps, 120 frames (5 seconds).
- A saved `.blend` file, rendered MP4 (H.264), and a PNG poster frame.
- Basic runtime assertions for camera, object count and animation presence.

## What it does not prove

- AI-generated avatar/mesh conversion.
- Production-quality topology, skeletal deformation, facial animation, lip-sync or cloth simulation.
- Match to the approved Wild Ink visual identity.
- Render speed, cloud cost, or compatibility with the existing episode contracts.
- Full episode automation.

The hero is assembled from primitive meshes and animated with object transforms. Parenting preserves world transforms before animation. This is deliberately a scene-pipeline smoke test, **not** a finished character rig.

## Run

Install Blender 4.2+ locally, then run from the repository root:

```bash
blender -b --python experiments/blender_scene_poc/build_scene.py
```

Expected outputs are written beside the script:

- `render_output/blender_poc.blend`
- `render_output/blender_poc_video.mp4`
- `render_output/blender_poc_frame.png`

## Evaluation gate

Do not integrate this into production unless all are reviewed:

1. The rendered frame is visually acceptable against the current approved style references.
2. The animation is inspected across the full 120-frame sequence, not only the still.
3. The hero's identity, silhouette and costume remain stable across camera angles.
4. A real AI-generated mesh is tested separately; the primitive placeholder is not evidence of avatar conversion.
5. Render time and cost are measured on the actual target GPU.
6. The existing pipeline remains unchanged until a creator-approved comparison demonstrates a material benefit.


## Automated render

The isolated workflow `.github/workflows/blender-scene-poc.yml` downloads the pinned Blender 4.2.0 runtime on GitHub Actions, renders the five-second MP4, and uploads the MP4, PNG and `.blend` file as a seven-day workflow artifact. It runs only on this experiment branch when the PoC files or its workflow change. It does not call RunPod or use paid API secrets.
