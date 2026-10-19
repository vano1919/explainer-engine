---
name: shorts-for-video
description: Write and cut the YouTube Shorts that advertise a Crossworld Theories video - a 3-second question hook, the most surprising scene, a line pointing to the video - using the video's own pictures cropped to 9:16 around the named heroes. Use after the full script exists, for every episode.
---

# Shorts that sell the video

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role edit` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Rules: `docs/ORCHESTRATION.md` SH-01..SH-04. A Short is a trailer with its own text, never a cut of the long video's read.

1. Pick the scene by surprise and clarity without context (a question the viewer wants answered, a visible reversal).
2. **Hook** (0-3 s): a yes/no question or a "did you know" that is true and mapped to a claim ("Did you know the 100 smartest
   people alive could not light a fire for a day?"). It rises like a question (N-01).
3. **Body** (20-45 s): 6-12 short sentences, one action each, a reaction line, the stakes in plain words; same N-rules.
4. **Last line**: points to the full video without begging ("Day one is only the beginning. Full story on the channel.").
5. In the production script's `shorts` block: id, hook, `lines`, and `shots` that reuse the video's pictures
   (`picture` = existing id) with `crop_x` (0..1, the horizontal centre of the 9:16 window on the 16:9 picture, set on the
   named hero's face, never cutting a face) and `zoom`.
6. Voice: the same ElevenLabs voice; if the pace is raised (at most 8 %), run `audio/voice_check` and keep the original on any
   timbre drift.
7. Captions: English, large, inside the safe area; no text over faces.
