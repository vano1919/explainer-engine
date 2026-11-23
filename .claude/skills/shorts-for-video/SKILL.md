---
name: shorts-for-video
description: Write and cut the YouTube Shorts that advertise a finished docudrama episode - one question hook spoken from the first second, the episode's most surprising true moment, a pointer or loop back to the long video - cut from our own master and clips in 9:16 around the named heroes, reusing the main read so no second narration is bought. Use after G10 passes for every episode, when planning a set of Shorts, and when a Short is rendered, checked or staged.
---

# Shorts cut from our own episode (layer L28, stage S19, after G10)

Rewritten 2026-11-20 under RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the v4.3 episode-first channel
(D-131): a Short is made from what the episode already made, its pictures, clips and voice, never from new material.
Feed reasoning (why the first frame matters, reading the curve) is in skill `v-viral-youtube-shorts`; the cutting engine
is skill `v-video-editing-skill`; measurements are skill `v-qc-skill`.

**The rulebook speaks first (D-51, OR-11):** run `python -m explainer_engine.standards brief <episode>/episode_rules.json
--role edit` and obey it; licence, likeness and legal questions are settled there (docs/EPISODE_STANDARDS.md), not here.
A clash goes back to the orchestrator.

## What a Short is for this channel

A trailer with its own hook, order and ending (SH-01): it sells the long video. Its body lines are the episode's own lines
and audio (SS-09, EL-09), re-cut around one moment (SS-03), never the long read shortened in its own order. Every opener is
true and maps to a claim row (SH-04). A set of up to ten per episode tells ten different scenes (SH-05, PV-28).

## Material: only what the episode made

- **Pictures and motion:** the master (`renders/final/<id>_master.mp4`), the shot clips of route `video` (D-132, LTX-2.5),
  the `still_25d` living photographs (D-131), and the `map_action` clips. No stock, no third-party footage, no
  film clips of the era film we name in prompts (docs/RIGHTS_AND_FAIR_USE.md).
- **Voice:** the main read and the clips' own hero lines, with their Scribe word timings from G6. The pace may rise by at
  most 8 % only when `explainer_engine/audio/voice_check.py` finds no timbre drift; otherwise it stays (SH-02). The only new
  voice is one shared pointer or hook line when the Short is cut from the master, read by the same narrator voice and
  bought under the usual ElevenLabs rules (skill `elevenlabs-voice`; estimate, ledger, the owner's word).
- **Music and effects:** the episode's own stems or the library, library first (OR-18); no licensed tracks.

## The 9:16 window around the heroes

The Short frame is `explainer_engine/core/delivery.py` `shorts_frame()` (BP-167). The 16:9 source is cropped so that the
named hero who speaks or acts sits inside the window and no face is ever cut (SH-03); captions and faces stay inside the
safe zone of BP-29.
- On a still or a living photograph: `crop_x` (0..1, the window's horizontal centre on the source) and `zoom` per shot in
  the `shorts` block; `explainer_engine/production/shorts.py` draws it with a slow push.
- On a moving reenactment clip: the hero moves, so the window follows a box measured on the clip (motion centre in skill
  `v-ffmpeg-skill`, `FILL` with an anchor or `PUNCH_IN` in skill `v-video-editing-skill`). A tracked crop is not yet
  automatic in our code; record the boxes you chose in the Short's work folder.
- Two speakers at opposite edges do not fit one window: cut between them on their lines, or choose another moment.
- Fallback layout: `explainer_engine/production/clip_shorts.py` puts the full 16:9 frame over a blurred copy with a title
  band; use it only when the crop would cut the story, and say so in the Short's note.

## Procedure

1. **Pick the moments** after G10, from the contact sheet and the claim map: a visible reversal, a decision under
   pressure, a fact that sounds wrong but is sourced. Each must be clear with no context.
2. **Write the hook** (BP-11: spoken from the first second, complete inside the hook window, inside the word cap): one
   question, rising like one (N-01), or for the `anti_intuition` and `pov_you` styles one statement that raises questions
   (SS-05). Its key words are on screen from frame 0 and the first cut lands inside it (SS-07).
3. **Shape the body** inside BP-12's word budget for its length band: short lines with one action each (BP-46), a reaction,
   the stakes in plain words; lines 2-3 promise the payoff and the answer waits for the last stretch (BP-44).
4. **End** on a pointer to the full video or a loop into the hook, never a sign-off (BP-44, SS-04). The long video's exact
   title is said or shown (SS-03).
5. **Fill the `shorts` block**: `id`, `style`, `ending`, `hook`, `lines` (a voiced dialogue line keeps its `speaker`, D-45),
   `shots` reusing existing picture or clip ids with their crop. Every line carries visual beats at BP-45's pace, not the
   long video's metronome; cues stay opt-in and tied to visible events (SS-09, VB-08). Validate with
   `python -m explainer_engine.production validate <script.json>` (PV-28, PV-34, PV-44).
6. **Render**: from the shorts block with
   `python -m explainer_engine.production.shorts <script.json> --id SH01 --audio <read> --out <dir>`, or from the master
   with `python -m explainer_engine.production.clip_shorts <plan.json>`. Both are free (local ffmpeg); both write a captioned
   file and a clean master beside it.
7. **Check**: `python -m explainer_engine.qa.short_format <SH01.mp4>` (9:16, length under BP-137), the hook timing and caption
   report of the renderer, loudness against BP-61 (`explainer_engine/qa/targets.py`), and your own eyes on three frames.
8. **Stage** one at a time after its own checks, unlisted, through `python -m explainer_engine.publish stage <episode>
   --only SH01` after the owner's word; the first within days of the video, the rest spread (BP-47, SS-03). Related-video
   link and pinned comment are set by hand. Nothing goes public (invariant 4).

## A set of Shorts

Styles (D-48, `docs/STORY_ENGINE.md` SS-01..SS-04, PV-34): `cold_open_cliffhanger`, `anti_intuition`, `countdown_hud`,
`dialogue_clash`, `fact_bomb`, `pov_you`, `myth_buster`, `ranked_three`, `loop`, `would_you`. A set of ten uses at least six
(SS-01), never one style twice in a row in posting order (SS-02), and spans both length bands of BP-12 (SS-06, D-49). At
least three visual events every ten seconds (SS-08, BP-45); at most one beat in two carries an effect (BP-55). No two Shorts
share a body line or most of their pictures (SH-05).

## Packaging that the Shorts share with the long video

Before the scenario, three title-and-thumbnail promises of different mechanism go on the variant card for YouTube's Test
and Compare (BP-135); the script's first seconds pay the chosen one, and the thumbnail stays honest (TN-02, skill
`v-thumbnail-skill`). After posting, Studio's intro, top moments, spikes and dips are mapped onto segment ids (P10) with
BP-48's intro gate and BP-136's midpoint gate. TikTok and Instagram limits are not researched yet.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| A face cut at the window edge | crop from the centre on a moving clip | measure the hero's box; cut between speakers |
| Hook ends late on the real read | leading silence or a long first word | trim the lead (the renderer does), shorten the hook |
| The middle loses people | a held still, too few events | an insert, a reaction, a reframe on new information |
| PV-28 flags a shared line | two Shorts tell one scene | give one of them another moment |
| Uploaded as a normal video | horizontal or bars | re-render in the Short frame; `short_format` before staging |

### CHECKLIST (packaging)

The table below is generated from `explainer_engine/standards/craft_checklists/packaging.json`, its only home; rerun
`python -m explainer_engine.standards.craft write` after a change there (`tests/unit/test_craft_checklists.py` compares the
two). Each row stays a hypothesis until a second source type backs it ([CRAFT_CURRICULUM](../../../docs/CRAFT_CURRICULUM.md)).

<!-- craft-checklist:packaging:begin -->
| ID | check | rule | artefact field | sourced rules | enforced by |
|---|---|---|---|---|---|
| CRAFT-PKG-01 | manual | three title-and-thumbnail promises of different mechanism before the scenario | packaging promises (variant card) | BP-135 | `explainer_engine/scripting/variant_plan.py` |
| CRAFT-PKG-02 | critic | the script's first seconds pay the chosen promise | packaging promise + first 5 s of narration | BP-135 | `explainer_engine/qa/editorial_review.py` (planned, P8) |
| CRAFT-PKG-03 | eye | Studio's intro, top moments, spikes and dips mapped onto segment ids | retention report + segment times | BP-48 | manual |
| CRAFT-PKG-04 | eye | the midpoint retention gate (the intro gate is BP-48's) | retention report | BP-136, BP-48 | manual |
| CRAFT-PKG-05 | code | a Short stays inside YouTube's length limit | Short length | BP-137, BP-12 | `explainer_engine/shorts/planner.py` (planned, P9) |
| CRAFT-PKG-06 | code | captions, labels and the face inside the Shorts safe zone | Short frame layout | BP-29 | `explainer_engine/production/shorts.py` |
| CRAFT-PKG-07 | code | the hook is spoken from the first second | Short script + read | BP-11 | `explainer_engine/production/shorts.py` |
| CRAFT-PKG-08 | critic | the thumbnail opens a gap the video closes, honestly | thumbnail + title | TN-02 | `explainer_engine/publish/thumbnail.py` |
| CRAFT-PKG-09 | manual | per-platform packs (TikTok, Instagram): limits not researched yet | distribution package | - | manual |
| CRAFT-PKG-10 | manual | nothing goes public without the creator's recorded approval | approval record | - | manual |
<!-- craft-checklist:packaging:end -->

## Sourced rules (the BP numbers this page leans on)

Every binding number lives in `explainer_engine/standards/sourced_rules.json` (docs/SOURCED_RULES.md, D-59); the validator
(PV-28, PV-34) and the renderer read it from there, so a number changes in the registry with its sources, never on this page.

- BP-11 the hook's start, end and word cap; PV-28 checks words (FAIL) and the estimated end (REVIEW), the renderer the real read.
- BP-12 the word budget per length band at BP-01's heard pace; `validate.short_seconds` is the one Short duration.
- BP-44 the answer in the last stretch, the early promise, the loop-or-pointer ending with no sign-off phrases.
- BP-45 the on-screen change floor and events per ten seconds; not the long video's beat metronome.
- BP-46 line length and reading grade. BP-47 the posting schedule. BP-55 the effect share of beats.
- BP-29 the Shorts safe zone; BP-61 Shorts loudness; BP-167 the Short frame.
- BP-135, BP-136, BP-137: the three promises, the midpoint gate, YouTube's length limit (hypotheses, REVIEW).

## Vendored pages and planned code

Upstream text sits in the `v-*` folders pinned in `docs/VENDORED_SKILLS.md` (W1, P-1/P-2); nothing is copied here. The
validator `explainer_engine/validators/shorts.py` (planned, W2) and the planner `explainer_engine/shorts/planner.py`
(planned, P9) will take over checks done by hand today; the editorial critic `explainer_engine/qa/editorial_review.py`
(planned, P8) is named in the checklist.
