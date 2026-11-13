# H1: handoff from S2 (story and script) to S3-S5 (pictures, sound, LTX; Sonnet high)

Written 2026-11-13 by the story thread (Opus high). Read the journal first: `/mnt/project-files/explainer-engine/demo_run_2026-11-13/DEMO_JOURNAL.md` (S0 has not run: FL-001).

| Field | Value |
|---|---|
| Episode id | `ep_truce_1914` (folder `episodes/ep_truce_1914/`) |
| Branch, base | `claude/project-thread-p6oesi`, on `8ae21ec` (PR #177 head, not yet merged) |
| Script A | `story/production_script.json`, sha256 `25636aba731607b94911060da011eab0993ac6b728793acf4b39805fe66de24c` |
| Variant B | `variants/B/production_script.json`, sha256 `0ce9795a7290429c81ee11a2f126dad830367feed6848856da2d95cb139efbc4` (RC-001) |
| Approval (OR-17) | **approved** by ვანო 2026-11-13 16:13 UTC (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWFCqRPmUmvb4PzH7h1aEZDY`), on the condition of five factual narrator fixes, applied in both versions (SF-001); his four follow-up notes 16:24 UTC (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWGK3dPACZAx9mwS5gMQAXKT`, NT-003) and the S3 thread's two prompt fixes are applied too (SF-002..SF-004); journal CQ-007 binds the sha above. Dialogue and structure unchanged |
| Measured mix (A, estimated clock) | 367.0 s; video 60.1 %, still_25d 31.2 %, map 8.7 %; 84 shots, 57 LTX clips (39 with a hero line, 18 narrated or silent) |
| Mix (B) | video 31.5 %, 40 clips, all of them clips of A |
| Production order (ვანო 16:13 UTC, NT-002) | Produce A first (57 clips, the quality baseline and his preferred version). Derive B from A's assets only: no extra LTX clip and no new picture for B. No version C and no hybrid before A and B are rendered and compared. Compare the real results on cinematic quality, emotional impact, pacing, character consistency and real cost |
| Spoken words | narrator 504 / dialogue 193 (72 % / 28 %, D-99 band 65-75 %) |
| Gates | A: G1-G3 PASS with no REVIEW, G4 PASS (`production/stages/`); B: G1 FAIL only on Q7 and CF-VISUAL-MIX-BOUNDS (approved RC-001) |
| Critic | 2 rounds; round 2 mean 3.92, verdict "ship after the one wording fix" (applied). Still slowest: 0:59-1:22 (four narrator lines) |
| Open cards | Stille Nacht in German (script follows ა: German verse, English answer); disclosure place (packaging follows ა: description only) |
| Look | `look.preset` crossworld_main_style_v1 (golden hour / firelight); `era_line` in episode.json; never-words: the family photograph is a "sepia portrait card" in every prompt, a lantern is an "oil lamp" (FL-008) |

## Picture list by round (GC-23)

- **R1 portraits and places:** char_thomas_hale, char_friedrich_brandt, char_sgt_harris (portraits from `world_bible.characters[].fixed_appearance_prompt`); places loc_british_trench, loc_german_trench, loc_no_mans_land; the map plate (`loc_western_front_map`) is a relief plate, not a Gemini picture.
- **R2 full bodies:** the three heroes in costume (Thomas's soft cap and greatcoat, Friedrich's field-grey cap with the red band, Harris's goatskin jerkin). Props: prop_mothers_letter, prop_family_photo, prop_brass_button, prop_grey_button, prop_candle_tree, prop_smle_rifle, prop_gew98_rifle, prop_spade, prop_flag_merry_christmas.
- **Scene pictures:** 78 start frames (every video and 2.5D shot except the black end card), each `image_prompt.start_frame_prompt` with the style anchor and the light. Houplines order (Stockwell, SF-004): the British captain fires three shots, raises the flag and salutes (S07_SH005); the German captain salutes back, gets down, then fires two shots (S07_SH006). Continuity: Thomas loses his top brass button from S06_SH009 on; Harris's cap comes off in S05_SH021.
- **B needs nothing new:** its 2.5D stills are A's start frames.

## Read list

- Narrator (ElevenLabs, Odom `CcSJ2r3qw0XU9gJpEPyk`): 33 lines, S01_L001 .. S08_L003.
- Clip-spoken lines (LTX speaks them; Q4 readback takes first): 39 lines, listed in `SCRIPT_A_READ_2026-11-13.md`. The two songs (S03_SH003 German, S03_SH008 English) are sung in the clip.
- Voices: each hero's `voice_card` and `voice_description` (Q5) are in `world_bible.characters`; `videolane/scene.compose_prompt` adds the description to every clip prompt.


## LTX launch parts (scene files sized to one launch, CH-03)

One launch has a 508 s timeout. L3 measured 38.6 s per clip with setup, and warm clips in a chain are not measured yet, so the
estimate is about 10-12 clips a launch. Each part below stays at or under 9 clips and about 34 clip-seconds, which leaves room for
the worker's one retry per clip. Every cut between two parts falls on a `scene_change` or `time_cut` shot, so the next part starts
from its own start frame and needs no hand-over frame. The script does not change: these are the ids of the scene files S5 builds
(`videolane/scene.build`), one per part, each priced on its own.

| Part | Video shots (A) | Clips | Clip-seconds (estimated) | Starts on |
|---|---|---|---|---|
| S01 | S01_SH002, S01_SH003 | 2 | 10.0 | scene_change |
| S02 | S02_SH006, S02_SH007, S02_SH009 | 3 | 16.75 | line |
| S03 | S03_SH001 .. S03_SH009 | 8 | 32.25 | scene_change |
| S04a | S04_SH002 .. S04_SH007 (the trenches) | 6 | 18.75 | scene_change |
| S04b | S04_SH008 .. S04_SH015 (no man's land) | 7 | 32.25 | scene_change |
| S05a | S05_SH004 .. S05_SH013 | 9 | 33.5 | line (follows the map and stills) |
| S05b | S05_SH014 .. S05_SH021 | 6 | 21.25 | time_cut |
| S06 | S06_SH002 .. S06_SH011 | 9 | 26.75 | line (split at the insert S06_SH009 if warm clips measure slower than 38 s) |
| S07 | S07_SH002 .. S07_SH008 | 7 | 31.0 | line |

Total 57 clips in 9 launches. B uses the same parts minus its 17 stills (B never launches: its clips are A's). A larger time cap per
launch is the other way: `launch.json` is protected (D-133), so that needs ვანო's word and the ladder L1-L3 again.

## What the next stage must know

1. Sound classes are missing for rifle and pistol shots, digging, paper, singing, clapping and match strikes (FL-002). The shots and songs live in the clip audio (Q2 quiet layer). For B, lift the signal-shot audio from A's clips (DV-001).
2. Map places live in `episode.json.places` (17 front and sector places plus Aachen, Liège, Brussels and the Marne for the August arrow). G1 does not check that an action's place id exists in the list, so a typo would only show at the map render. All ids were checked by hand on 2026-11-13.
3. Durations are on the estimated clock. G6 retimes them from the read, and the video lane resizes every clip from the measured line (VL-07).
4. Nothing paid has run. Every paid step (ElevenLabs, Modal LTX, any Gemini API fallback) needs a price, a cap line and ვანო's word (KN-07: `modal_ltx` has no episode line).
5. **Not done in S2: the continuity cards** (`continuity_card/1`, stage page `shot-continuity-writer`, CT-01..CT-14). Each scene needs its cards before its keyframes are drawn, so S3 writes them first, scene by scene, from the `edit_plan` axis sides and `screen_positions` already in the script.
