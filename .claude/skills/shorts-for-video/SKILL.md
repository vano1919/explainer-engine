---
name: shorts-for-video
description: Write and cut the YouTube Shorts that advertise a Crossworld Theories video - a 3-second question hook, the most surprising scene, a line pointing to the video - using the video's own pictures cropped to 9:16 around the named heroes. Use after the full script exists, for every episode.
---

# Shorts that sell the video

**Episode rulebook first (D-51, OR-11):** read `python -m explainer_engine.standards brief <episode>/episode_rules.json --role edit` and follow it; legal, licence, likeness and art-direction questions are decided there (docs/EPISODE_STANDARDS.md), never invented in this skill. A conflict goes back to the orchestrator.

Rules: `docs/ORCHESTRATION.md` SH-01..SH-04. A Short is a trailer with its own hook, order and ending; its body lines may be
the video's own lines and audio (SS-09, EL-09), never a cut-down of the long video's read in its order.

1. Pick the scene by surprise and clarity without context (a question the viewer wants answered, a visible reversal).
2. **Hook** (BP-11: spoken from the first second, complete inside the hook window, inside the word cap): one question, or one
   statement that raises several, true and mapped to a claim ("Did you know the 100 smartest people alive could not light a
   fire for a day?"). It rises like a question (N-01).
3. **Body** (the word budget of the Short's length band, BP-12): short sentences, one action each, a reaction line, the stakes
   in plain words, every line short and simple (BP-46); lines 2-3 foreshadow the payoff and the sentence that answers the
   hook waits for the last stretch (BP-44); same N-rules.
4. **Last line**: points to the full video without begging ("Day one is only the beginning. Full story on the channel.") or
   loops into the hook; never a sign-off (BP-44).
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
   Tricks: on-screen text with the hook from frame 0, the on-screen change cadence of BP-45, word-highlight captions, a HUD
   counter for steps, a sound on a pop only when it has a purpose (BP-55: at most one beat in two carries an effect), the
   long video's exact title said aloud; related-video link and pinned comment
   are set at upload by hand. The agent `shorts-writer` writes the set. `anti_intuition` and `pov_you` may open with one
   statement inside the BP-11 word cap instead of a question (SS-05). D-49 (`docs/research/PARAMETER_AUDIT_2026-10-19.md`,
   section 6 has the recipe per style): the hook's words on frame 0 and the first cut inside the hook line (SS-07), the
   visual-event floor of BP-45 (SS-08), the set in the two length bands of BP-12 (SS-06), posted on the BP-47 schedule
   (SS-03: the first within days of the video, the rest spread).
   Every Short carries the video's visual-beat layer (SS-09): the beat-writer gives the Short's own lines beats, on new
   information and at BP-45's pace, never a 1.5 s metronome; cues stay opt-in and event-bound as on /3 (VB-08).

## Sourced rules (docs/SOURCED_RULES.md)

The numbers that bind a Short live only in the registry (`explainer_engine/standards/sourced_rules.json`); `production validate`
(PV-28, PV-34) and `production/shorts.py` read them from there. A number changes there, with its sources, never here.

- BP-11: the hook is spoken from the first second (the first word within 1.0 s of frame 0) and complete by 3.0 s, at most 14
  words; one question, or one statement that raises several. At 170 wpm about 8 words fit in 3 s, so the time is the tighter
  bound: PV-28 checks the words (FAIL) and the hook's end on the estimated read (REVIEW); `shorts.py` refuses a real read
  whose first word starts late or whose hook ends after 3.0 s.
- BP-12: the word budget follows the length band at BP-01's heard pace with 10 % slack: 15-30 s is about 38-93 words, 45-75 s
  about 115-234 words; a set spans both bands (PV-28, PV-34). A Short's estimated length is its words at that pace
  (`validate.short_seconds`), the one duration every Short check uses.
- BP-44: the premise stays open until the last 15 %: the sentence that answers the hook starts at or after 85 % of the read;
  lines 2-3 foreshadow with a promise marker inside 3 s of the hook; the ending is a loop or a pointer, never a sign-off
  ("thanks for watching", "subscribe", "see you", "goodbye", "like and") (PV-28).
- BP-45: something changes on screen at least every 5 s, at least 3 events per 10 s, each on new information; the 1.5 s
  beat metronome of the long video is not a Shorts rule (PV-34).
- BP-46: every line at most 14 words and the whole Short at Flesch-Kincaid grade 6 or under (PV-28).
- BP-47: the first Short goes up within 3 days of the video, then at most one a day, the ten spread over at least 14 days.
