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
8. A set (up to 10 for one video): each Short its own scene and question, no body line or most pictures shared with
   another Short (SH-05, PV-28). A voiced dialogue line keeps its `speaker` (D-45).
9. Styles (D-48, `docs/STORY_ENGINE.md` SS-01..SS-04, PV-34): each Short has a `style` from the catalog (cold_open_cliffhanger,
   anti_intuition, countdown_hud, dialogue_clash, fact_bomb, pov_you, myth_buster, ranked_three, loop, would_you) and an
   `ending` (cliffhanger, loop, question, pointer); 10 Shorts use at least 6 styles, never the same style twice in a row.
   Tricks: on-screen text with the hook in 0-3 s, 3-6 changes every 10 s, word-highlight captions, a HUD counter for steps,
   a sound on every pop, the long video's exact title said aloud; related-video link and pinned comment are set at upload
   by hand. The agent `shorts-writer` writes the set. `anti_intuition` and `pov_you` may open with one statement of at most
   14 words instead of a question (SS-05). D-49 (`docs/research/PARAMETER_AUDIT_2026-10-19.md`, section 6 has the recipe per
   style): the hook's words on frame 0 and the first cut inside the hook line (SS-07), at least 3 visual events every 10 s
   (SS-08), the set in two length bands, 15-30 s and 45-75 s (SS-06), posted within three days of the video (SS-03).
