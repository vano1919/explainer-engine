# FINAL 2 (2026-11-13 19:45 UTC): script A sha256 **c2abcdd30d04bcd9446c7e6872afca4582cbd231d062e69d9c046048555b69f3** (supersedes 1c117e12)

Audit round 2 (FL-309): S02_SH009 `fire_flicker` now has `region` [0.56, 0.58, 0.67, 0.82] (the brazier, checked on the picture). Effect-only render
(with minus without the effect, frames 6/17/40): 0.4-0.5 % of the change in the top third (the auto mask had 68 %). Only that one field differs from 1c117e12
(`shots[13].motion_imitation[1].region`). `episode.json` unchanged (c85da546...). G1-G3 PASS, G4 PASS. Repo commit 2327dfe on claude/project-thread-hqs08m.
`stage_guard editor` lists only the three caster-owned `voice_description` texts the LTX thread asked for.

# FINAL (2026-11-13 19:40 UTC), supersedes the numbers below where they differ

Script A sha256 **1c117e129b5e55da46f55168ba34f8e7188a563ddb1b5328fe814b0934e62660**; `episode.json` sha256 `c85da546a33af2a47bca177cbee9ff48a131ab985b1e4b111ae9deaa1658c36b`
(two corner places for the date labels). Base `9be981d5...` (bf505m). The first commit d23b700 (sha `aab6686e...`) is withdrawn.
ვანო's answers: card 1 = A (end card with one candle), card 2 = A (S02_SH009 becomes a 2.5D shot; the "move the pause" answer cannot survive
G6, audit FL-303; `ingest.recut` never stretches a short raw clip). Builder defaults now = these answers.

Audit round 1 fixes (journal part AUDIT, FL-301..305): S01_SH001 and S05_SH016 get `sun_shaft_drift` instead of a regionless fire mask;
S02_SH004 `fire_flicker` region [0.57, 0.60, 0.70, 0.80] (the brazier) and S08_SH002 [0.78, 0.30, 0.92, 0.62] (the candle), end card [0.74, 0.48, 0.86, 0.72]
(measured effect-only: the changed pixels sit on the brazier and the candle, 0 % in the top third for S02_SH004); fire on S01_SH001, S05_SH016, S08_SH002 is
silent_by_design (no new `fire` events; G4 events differ from the base only by S02_SH009 `fire`, the British trench bed); "dawn bed" texts removed;
date labels `chip_aug` / `chip_dec` (top-left corner of each map frame, looked at on rendered frames) instead of Aachen / Nieuport;
LTX thread's three voice_description texts added (caster-owned fields, voice_card untouched); S02_SH009 2.5D = push + brazier flicker + smoke (silent).
End card picture: `clips_lane/pictures/S08_SH004_start_candle.png` sha256 `ab009277a67eb84416c208591b70f5eb172d3c568f7a97d31b188b5bf46587e4`
(a soft-masked crop of the candle of S08_SH002 on black, local, free); G5 intake row: the intake gate `no_letterbox` (edge bands) rejects it exactly like the
black frame (LTX FL-103), so G5 stays a rehearsal row for this one picture until the creator waives that gate for the end card (RC, not asked yet).
Not in this package (picture decisions, would add another sha): the S03_SH003 jump cut and the repeated two-shots (S04_SH009/010/012/014, S05_SH007/009).

---

# Script A data fix package (clips lane, 2026-11-13 ~19:30 UTC)

Script A now: `9be981d5b2ede82dabefc52dc2fb17db2fe26dad8486993cbcb669c64726e1f8` (commit on `claude/project-thread-bf505m`, SF-006..008).
Builder (no repo code touched): `clips_lane/builder/apply_data_fix.py IN OUT [--endcard black|candle] [--s02sh009 video|still]`.
Only editor-owned fields change (`shots[*].motion_imitation`, `actions`, `map_view`, `edit_plan`, and for the end card its picture text). **No narrator word, no story, no picture changes.**
Checked on a scratch copy: G1-G3 PASS, G4 PASS, `stage_guard editor` 0 violations, schema valid, every shot below re-rendered (short, low-res) with no FAIL.

## What was wrong (found by planning and rendering the 27 shots, nothing paid)

| # | Defect | Shots | Fix (data only) |
|---|---|---|---|
| 1 | BP-185 FAIL: a 2.5D shot needs 2 moving families beside the camera; each still had 1 or 0 | 21 stills | one or two items per shot (table below), each with `event_id` and an `audio` decision (all `ambience_only` or `silent_by_design`, no new sound cue, BP-81 budget untouched) |
| 2 | Map date label has no place, `maps/actions` raises `label needs 'from'` | S02_SH001, S02_SH002 | `from`: aachen (August 1914), nieuport (December 1914) |
| 3 | **New:** the map frames cut the routes off (Aachen, Brussels, Nieuport, the Swiss border, Ypres, La Bassee lie outside the frame; the label in #2 would be invisible) | S02_SH001, S02_SH002, S02_SH003, S05_SH001, S05_SH002 | `map_view` recomputed so every place of the shot lies inside with a 14 % margin: SH001 (4.84, 49.9, 530 km); SH002 and SH003 (4.95, 49.31, 1000 km, one plate, SH003 then flies to Flanders); S05 both (2.871, 50.692, 90 km) |
| 4 | **New:** two map shots name a line in their own composition text that no action draws (each shot renders alone); S05_SH002 had no place at all and was drawn as a bare orange counter card | S02_SH003, S05_SH002 | a `front_line` with `cues: none` (stands at once, silent_by_design) in both; S05_SH002 also four 3 km `highlight` glows on the patches |
| 5 | FL-023 on the real clock (`clock/timing.json`): S04_SH008 = 10.000 s, S02_SH009 = 10.4583 s; LTX holds 10.06 s and the default tail handle is 0.5 s | S04_SH008, S02_SH009 | S04_SH008: head and tail handle 0, clip = exactly 10.0 s, fits. S02_SH009: 10.4583 s does **not** fit under any handle (see card 2) |
| 6 | The black end card has nothing to animate; it cannot reach 2 families | S08_SH004 | see card 1 |

## The 21 stills (added items; the shot's own camera item stays)

| Shot | Had | Added |
|---|---|---|
| S01_SH001 | push, mist | fire_flicker (lamps at the trench edges) |
| S01_SH004 | pull, subject_sway | mist |
| S01_SH005 | truck, fire_flicker | mist |
| S02_SH004 | truck, water_shimmer | fire_flicker (brazier) |
| S02_SH005 | push, fire_flicker | embers (from the brazier) |
| S02_SH008 | push, cloud_drift | fire_flicker (brazier) |
| S03_SH002 | push, fire_flicker | dust (motes in candlelight) |
| S03_SH010 | crane, fire_flicker | mist |
| S04_SH001 | push, mist | sun_shaft_drift |
| S04_SH011 | push | sun_shaft_drift, mist |
| S05_SH003 | truck, subject_sway | smoke_drift |
| S05_SH010 | push | sun_shaft_drift, mist |
| S05_SH016 | push | smoke_drift, fire_flicker |
| S05_SH020 | push, cloud_drift | sun_shaft_drift |
| S06_SH001 | pull, sun_shaft_drift | smoke_drift |
| S06_SH005 | push | smoke_drift, sun_shaft_drift |
| S06_SH012 | pull, sun_shaft_drift | smoke_drift |
| S07_SH001 | mist, pull | sun_shaft_drift |
| S08_SH001 | push, fire_flicker | dust |
| S08_SH002 | push | fire_flicker, dust |
| S08_SH003 | crane | smoke_drift, sun_shaft_drift |

Each effect is something visible in that picture (lamps, braziers, candles, low sun, fog, smoke). Rendered check at 960 px, 1.5 s each: 2 families on all 21, 0 FAIL;
REVIEW rows are only face-landmark drift on shots with small faces (not caused by the added items; the real 1080p render measures them again).

## Card 1: the end card S08_SH004 (black, with the line "For one day, they remembered they were human.")

- **ა (recommended):** the card stays almost black, with one small candle flame low in the right corner (a local crop of the candle of S08_SH002 on black, free, no Gemini). Candle flicker + thin smoke are the 2 families; silent (the film ends in silence). The candle already appears in the letter shots S08_SH001/002, so the film closes on its own motif.
  Script change: S08_SH004 motion items, image prompt text, start/end state text. Script A sha with this and S02_SH009 kept on LTX: `aab6686e...b30732` (with S02_SH009 as 2.5D: `288923a2...8ddb`).
- **ბ:** it stays pure black. BP-185 stays FAIL on this one shot; the clips stage then reports 1 FAIL and every later stage refuses until the FAIL is waived by hand (a rule break RC for one shot, and the assembly thread must override). sha with S02_SH009 kept on LTX: `9f6d3006...a85dbe`.

## Card 2: FL-023 S02_SH009 ("At Christmas, parcels came up the line...", 10.4583 s on the real clock, LTX max 10.06 s)

- **ა:** S02_SH009 becomes a 2.5D shot on its own start picture (push + brazier flicker + smoke). Free, one LTX clip less ($0.3 less), video share 59.1 % to 56.4 % (target 60 % +-10, still inside). The soldiers then no longer move (the shot was "bodies at work").
- **ბ (recommended, keeps the action):** the shot stays LTX with both handles 0 (clip exactly 10.0 s). The 0.46 s breath after the line moves to the head of the next shot (S03_SH001, clip 8.92 s, has room: 9.38 s + handles fit). That is a hand edit of the clock file by the LTX thread (free), no word and no picture changes.
- **გ:** shorten the words or re-read the line (paid ElevenLabs, new join): not recommended, the words are approved.
Script A sha: ბ = the first number of card 1 (handles only); ა = the second.

## Not folded in (the LTX thread's items 1 and 3): they are picture changes, not data

- S03_SH003 and S03_SH001 share medium_wide at 135 degrees (the jump cut), S04_SH009/010/012/013/014 and S05_SH007/009 share coverage of one two-shot: the start pictures are already made and pinned by the LTX storyboard; editing `camera_spec` without a new picture would make the data lie. Real fixes: a free local crop (about 1.3x of the 2752x1536 frame, still above LTX's 1280 px) for the second shot of a pair, or a new Gemini picture. Needs the pictures thread and the LTX thread, and one more script sha, so decide it together with these cards.
- B (variant) has the same BP-185 defect on its 39 stills; it is not touched until A is compared.
