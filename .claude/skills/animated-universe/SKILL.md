---
name: animated-universe
description: Design rules for the channel's drawn characters (silhouette, proportions, one key light); a character moves through its clip prompt (docs/SHOT_PROMPTS.md), the cut-out rig is retired (creator 2026-10-22, D-77).
---

# The animated universe: simple to make, good to feel

> **Retired in part (creator 2026-10-22, docs/PROGRESS.md "so bad there is no hope"; D-77/D-78):** the cut-out rig (production/rig.py CYCLES, mouth_at, drop_y, Spring) moves no character in an episode. A character moves through a clip prompt: docs/SHOT_PROMPTS.md (KP-xx) and docs/SHOT_CONTINUITY.md (CT-xx). The design rules below (silhouette, proportions, one key light) stay.

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

- Name the beat, the physics and the acting in the shot card's clip prompt, per the KP rules (docs/SHOT_PROMPTS.md).
- Cite the continuity card for position and eye-line (docs/SHOT_CONTINUITY.md, CT rules).
- Never a rig call: no cycle, `mouth_at`, `drop_y` or `Spring` in a shot.
- Squash and stretch is rationed: bounded, tied to real speed, at most one off-model beat per scene and it belongs to the
  story's turn. On-model the rest of the time.
- Long holds are allowed and good: a held frame with sound is a beat. Each character gets its own timing scale.

#### History (retired 2026-10-22)
- The shot named a rig cycle (`idle`, `walk`, `run`, `point`, `react`, `fall`, `production/rig.py` CYCLES; a turn was a flip) and its start; the rig did the anticipation, follow-through and easing.
- A dropped or swinging thing used `drop_y` or a `Spring`; the mouth followed the word timings (`mouth_at`).

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
