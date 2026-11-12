# Rules for the script

Sources: `docs/STORY_ENGINE.md` (ST, SC, DW rules, YT-01, YT-02); `docs/SOURCED_RULES.md` (the BP numbers below are
copied from the registry at export; the registry wins); `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (D-61, D-99).

The script is the approved short story written out in full: narration and dialogue, with the dialogue inside its
scenes. Nothing is paid before the creator approves it, so this check is the last cheap place to catch a problem.

## First question: is it still the approved story?

Compare the script with the approved short story (`short_story.md` in the episode folder on Drive). List every place
where the script changed the story: a new event, a missing event, a different ending, a hero who wants something else.
A change is not a defect by itself, but the creator approved the short story, so every change must be named.

## Story

All of `02_SHORT_STORY_RULES.md` still holds. In addition:
- No stretch longer than {{bp:BP-76.turn_gap_s}} seconds passes without a turn (ST-13, BP-76). Estimate seconds from
  words at {{bp:BP-01.wpm_target}} words a minute.
- The narrator never talks alone for longer than {{bp:BP-104.narration_block_max_s}} seconds (ST-17, BP-104). The
  narrator carries the jumps in time, place and cause; the scenes carry the action.
- The central scene is the longest scene (ST-18).

## Scenes and dialogue

- A scene is declared before it is played: who is present, whose scene it is, what each wants (SC-01). The wants
  collide (SC-03). Something changes between the start and the end of the scene (SC-02).
- Every spoken line is said to somebody present. A hero never talks to the narrator (SC-04).
- A scene with two or more people has a real exchange: at least {{bp:BP-70.min_exchange_lines}} lines in a row from at
  least {{bp:BP-70.min_exchange_speakers}} speakers with no narrator between them (SC-05, BP-70).
- Enter late, leave early: no greeting to open, no wrap-up to close (SC-06).
- Short turns. A spoken turn is at most {{bp:BP-72.turn_words_max}} words, and a scene has at most
  {{bp:BP-72.speeches_per_scene_max}} longer speech, at its peak (SC-09, BP-72).
- Subtext is never spoken: no hero states the scene's real subject or announces a feeling (SC-10, DW-04).
- Cover the names: you should still tell who is speaking from the words alone (DW-03).
- A fact both speakers know is spoken only as a weapon or a stake, never as information for the audience (DW-13).
  A number belongs to the narrator unless the hero is arguing about it (DW-08).
- A joke never carries a fact and never carries the explanation (DW-07).

## Narration

- The narrator talks to "you", in spoken English with contractions (DW-10).
- Sentences for the ear: one idea per sentence, no sentence over {{bp:BP-06.hard_max_words}} words (BP-06).
- A line that reports speech names the speaker first: "Kael says the river is dying", never "..., says Kael" (ST-15).
- The narrator does not repeat what the scene just played (ST-21).
- The narrator's share of the spoken words is about {{bp:BP-105.nominal_narrator_share}} (D-99, BP-105). Count the
  words and report the share.

## The two strict rules, line by line

- **Show, don't tell (SC-12).** Quote every narrator line that states a trait ("she is brave"), gives a rating or sums
  up a life.
- **Full immersion (SC-11, SC-08).** Quote every line that steps outside the story or hedges it.

## Facts

For each factual sentence: is there a claim id, and does the sentence say what the claim's source says? A wrong date,
a wrong number, a wrong name or an object that did not exist in that era is a blocker. Give the source you checked
against.

## Era and picture sense

This script becomes pictures. Flag early anything that cannot be drawn in the episode's era, any scene that needs
written words on screen to be understood, and any line that depends on a picture the style cannot give
(`05_STYLE.md`: the world is lit by a low sun or by fire).
