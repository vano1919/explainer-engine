---
name: animated-universe
description: How the Cross Worlds animated universe is designed and moved - simple shapes, one silhouette per character, a cut-out rig with reusable cycles, rationed squash and stretch, real physics for props, one key light per scene. Use when designing a character or environment piece, writing a shot that needs a figure to act (walk, run, point, fall, react, talk), choosing between rig motion, parallax and generated video, or judging whether a design is simple enough to produce repeatedly.
---

# The animated universe: simple to make, good to feel

The creator's muse (2026-10-22): a world of simple, beautiful animation; complexity is never required, but the emotion
and the physics must be good. Sources and tools: `docs/research/ANIMATION_TOOLS_2026-10-22.md`; the four candidate
directions and the production plan: `docs/research/ANIMATION_UNIVERSE_2026-10-22.md`; the rig: `production/rig.py`.
No show, studio, artist or character of another work is ever named in a prompt (`world/look_v2.json` no_names).

## Design a character (before any picture is paid for)

1. Silhouette first: 3-5 primary shapes; it must read in solid black at 10 % of the frame height. If it needs more
   strokes, simplify.
2. Adult proportions (look v2), the caricature in the face, hands and posture; one costume layer that an era can swap.
3. Plan the pieces: head, torso, upper/lower arm x2, hand x2, upper/lower leg x2, foot x2, plus the secondary pieces
   that will lag (scarf, hair, coat tail). Mark the pivots. A sheet is painted on flat chroma with limbs apart.
4. Faces: 8-12 expressions + the mouth set (4 now; Rhubarb's A-H + X later). Nothing else is drawn per shot.
5. Ask: can the walk, point, react and talk of this character be the shared cycles? If yes, it is cheap. If it needs
   its own cycle for a story reason, say which and why.

## Move a character (writing a shot)

- Use the rig's cycles: `idle`, `walk`, `run`, `point`, `react`, `fall` (`production/rig.py` CYCLES); a turn is a flip
  until a second angle set exists. Name the cycle and its start in the shot; the rig does the easing.
- Anticipation before the action, follow-through after it (the scarf, the hair), slow in / slow out: these are in the
  code; do not ask a prompt for them.
- Squash and stretch is rationed: bounded, tied to real speed, at most one off-model beat per scene and it belongs to the
  story's turn. On-model the rest of the time.
- Physics is real or absent: a dropped, swinging or floating thing uses `drop_y`, a `Spring` or pymunk; never a guessed
  curve, never "it just appears".
- The mouth follows the narration's word timings (`mouth_at`); the narrator's acting lives in the face set and the pose.
- Long holds are allowed and good: a held frame with sound is a beat. Each character gets its own timing scale.

## Stage a scene

- One key light and one palette decision per scene, written down (the era codex's light keys, UR-26). The colour of a
  thing carries meaning; a plate gets its hold before the figures act.
- Compose on silhouette and negative space; most of the frame may be empty.
- Layers: sky, far, mid, near; the figure on the near layer; parallax (`production/parallax.py`) for the camera.
- Motion ladder: rig motion first (free), parallax second (free), generated video only for a few atmosphere hero shots
  (paid, never the figure's acting).

## Checks before reporting a shot or a design

- The silhouette test passed; pieces and pivots listed; no per-shot drawing.
- The shot names its cycle(s), its key light, its palette decision and any physics object.
- Frames are a pure function of the frame number (the rig and the assembler guarantee it; do not break it with state).
- Nothing paid was generated without the creator's card (D-50, invariant 2).
