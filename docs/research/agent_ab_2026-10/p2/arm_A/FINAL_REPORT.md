# ARM A2 final report (writers' room, one main agent, stages 1-6, no spawned agent, no paid call)
Episode: "What if Napoleon marched into Genghis Khan?" Deliverable: production_script.json (= s06_shorts.json). Snapshots s01..s06 + LOG.md.

## Final gate counts
- story_lint 0 FAIL / 0 REVIEW; scene_lint 0/0; narration PV-12 FAIL 0 (13 REVIEW: N-02 closed beat ends, N-12 "you"); claims PV-37 0/0.
- gate.py (input/gate.py): all sections 0 FAIL; beats PV-44 lint 19 REVIEW (VB-12 x11 beats on hero lines kept for story, VB-06 x8 props with no cut-out).
- production validate: 119 FAIL, all known noise: PV-11 x89, PV-05 x24 (files and sounds absent), PV-47 x5, PV-45 x1. Zero other FAIL.
  148 REVIEW: HERO-2 x68, VB-12 15, VB-06 13, PV-12 13, VB-02 8, PV-32 6 (no voice id yet), BP-62 x5, VB-05 5, BP-94 x4, PV-28 x3, RHYTHM-1 (10.11 pictures/min), others 1 each.
- Shape: 16 segments, 238 lines, 2,385 spoken words (narrator 43 %), 160 shots on 89 pictures, 6 staged scenes, 3 Shorts, 4 voiced heroes.
- stage_guard: 0 violations at every stage.

## Stages that needed retries
- 1 architect: 2 tries (loops/stakes REVIEWs; face_sheet missing, found only when reading the beat-writer page).
- 2 writer: retried S04/S06/S08/S10/S11/S13 (narrator share 51 %, S10 not longest); small fixes ST-11, SC-09, bad intent value.
- 2b beats: VB-03 order, VB-04 text length, and a return in stage 4 for 3 expressions not on the face sheet (VB-09).
- 3 performer: tag rate 79 % thinned to 44 % in 2 passes; adjacent held pauses; a return in stage 4 for an N-04 double emphasis (S11).
- 4 editor: about 6 regenerate rounds (dissolves inside segments BP-31, HERO-1, PV-57, VB-08 cue doubled by my sfx, BP-21 tiny moves, MO-02 quiet minutes, BP-40).
- 5 caster: 2 tries (role is a schema enum; PV-10 on two capitalised words). 6 shorts: 3 tries (hook must be one sentence, a deleted picture, VB-03 order).

## My own focus
- Rules realised late: face_sheet (cast needs it before any expression beat); a dissolve is only legal at a segment start with a period or scene change; BP-94 hold vs HERO-1 conflict; the payoff of a Short sits in the last 15 %, so the pointer cannot follow it.
- Slips: interjection capitalisation ("Oh, Am I"), first tag pass at 79 %, a stale picture id in a Short.
- Batching: words for S01-S03, S04-S06, S07-S09, S10-S16 were written in groups with beats right after, not segment by segment.
- Late in the run the early rules were not harder to hold, but the cost of a late rule grew: each fix meant regenerating stage 4 output from the generator.

## Honest limits
- production validate crashes on world.host.era "steppe_1223" (codex eras.json has no such era, nor france_1812): validated a copy with a known era; real codex entries need research. Tooling gap, not scripted around in the deliverable.
- No voice was auditioned (no connector call allowed): candidates are empty, voice_id null, PV-32 REVIEW. No accent entry for Turkic/steppe in casting.ACCENTS.
- New assets needed: amb_steppe_wind__v1, cannon_boom__v1 (not in the library); music is only the 2 library loops. Props are word stickers (no horse, tent, gun icons).
- Channel pointer worlds in S16 (Stone Age, Rome, far future) are unverified. Kerim is invented; C-91..C-94 are the invented premise.
- RHYTHM-1 10.11 pictures/min is above 10 (dialogue coverage, estimated read); BP-94 holds not met in S06/S08/S11/S13; music edges sit on the first word, 0.2 s after the cut.
- Estimated read only: no real timing, no pictures painted, hero lines' beats are not counted by VB-12.
- The stage_guard rejection of a later correction to a `scene` header (known tooling bug) was not hit in this run.
