# H1: handoff from S2 (story and script) to S3-S5 (pictures, sound, LTX; Sonnet high)

Written 2026-11-13 by the story thread (Opus high). Read the journal first: `/mnt/project-files/explainer-engine/demo_run_2026-11-13/DEMO_JOURNAL.md` (S0 has not run: FL-001).

| Field | Value |
|---|---|
| Episode id | `ep_truce_1914` (folder `episodes/ep_truce_1914/`) |
| Branch, base | `claude/project-thread-p6oesi`, on `8ae21ec` (PR #177 head, not yet merged) |
| Script A | `story/production_script.json`, sha256 `d14f7c7d0586536b18b6ce72f3c2aa6d94e49804cc82f15381d86b2d313f2806` |
| Variant B | `variants/B/production_script.json`, sha256 `e89b5adf93bc0f9751248e9b5c8aac60d2daba34202764f1459e7b522a074a07` (RC-001) |
| Approval (OR-17) | **approved** by ვანო 2026-11-13 16:13 UTC (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWFCqRPmUmvb4PzH7h1aEZDY`), on the condition of five factual narrator fixes, applied in both versions (SF-001); journal CQ-007 binds the sha above. Dialogue and structure unchanged |
| Measured mix (A, estimated clock) | 364.8 s; video 60.2 %, still_25d 31.0 %, map 8.8 %; 84 shots, 57 LTX clips (39 with a hero line, 18 narrated or silent) |
| Mix (B) | video 31.7 %, 40 clips, all of them clips of A |
| Production order (ვანო 16:13 UTC, NT-002) | Produce A first (57 clips, the quality baseline and his preferred version). Derive B from A's assets only: no extra LTX clip and no new picture for B. No version C and no hybrid before A and B are rendered and compared. Compare the real results on cinematic quality, emotional impact, pacing, character consistency and real cost |
| Spoken words | narrator 500 / dialogue 193 (72 % / 28 %, D-99 band 65-75 %) |
| Gates | A: G1-G3 PASS with no REVIEW, G4 PASS (`production/stages/`); B: G1 FAIL only on Q7 and CF-VISUAL-MIX-BOUNDS (approved RC-001) |
| Critic | 2 rounds; round 2 mean 3.92, verdict "ship after the one wording fix" (applied). Still slowest: 0:59-1:22 (four narrator lines) |
| Open cards | Stille Nacht in German (script follows ა: German verse, English answer); disclosure place (packaging follows ა: description only) |
| Look | `look.preset` crossworld_main_style_v1 (golden hour / firelight); `era_line` in episode.json; never-words: the family photograph is a "sepia portrait card" in every prompt, a lantern is an "oil lamp" (FL-008) |

## Picture list by round (GC-23)

- **R1 portraits and places:** char_thomas_hale, char_friedrich_brandt, char_sgt_harris (portraits from `world_bible.characters[].fixed_appearance_prompt`); places loc_british_trench, loc_german_trench, loc_no_mans_land; the map plate (`loc_western_front_map`) is a relief plate, not a Gemini picture.
- **R2 full bodies:** the three heroes in costume (Thomas's soft cap and greatcoat, Friedrich's field-grey cap with the red band, Harris's goatskin jerkin). Props: prop_mothers_letter, prop_family_photo, prop_brass_button, prop_grey_button, prop_candle_tree, prop_smle_rifle, prop_gew98_rifle, prop_spade, prop_flag_merry_christmas.
- **Scene pictures:** 78 start frames (every video and 2.5D shot except the black end card), each `image_prompt.start_frame_prompt` with the style anchor and the light. Continuity: Thomas loses his top brass button from S06_SH009 on; Harris's cap comes off in S05_SH021.
- **B needs nothing new:** its 2.5D stills are A's start frames.

## Read list

- Narrator (ElevenLabs, Odom `CcSJ2r3qw0XU9gJpEPyk`): 33 lines, S01_L001 .. S08_L003.
- Clip-spoken lines (LTX speaks them; Q4 readback takes first): 39 lines, listed in `SCRIPT_A_READ_2026-11-13.md`. The two songs (S03_SH003 German, S03_SH008 English) are sung in the clip.
- Voices: each hero's `voice_card` and `voice_description` (Q5) are in `world_bible.characters`; `videolane/scene.compose_prompt` adds the description to every clip prompt.

## What the next stage must know

1. Sound classes are missing for rifle and pistol shots, digging, paper, singing, clapping and match strikes (FL-002). The shots and songs live in the clip audio (Q2 quiet layer). For B, lift the signal-shot audio from A's clips (DV-001).
2. Map places live in `episode.json.places` (17 front and sector places plus Aachen, Liège, Brussels and the Marne for the August arrow). G1 does not check that an action's place id exists in the list, so a typo would only show at the map render. All ids were checked by hand on 2026-11-13.
3. Durations are on the estimated clock. G6 retimes them from the read, and the video lane resizes every clip from the measured line (VL-07).
4. Nothing paid has run. Every paid step (ElevenLabs, Modal LTX, any Gemini API fallback) needs a price, a cap line and ვანო's word (KN-07: `modal_ltx` has no episode line).
5. **Not done in S2: the continuity cards** (`continuity_card/1`, stage page `shot-continuity-writer`, CT-01..CT-14). Each scene needs its cards before its keyframes are drawn, so S3 writes them first, scene by scene, from the `edit_plan` axis sides and `screen_positions` already in the script.
