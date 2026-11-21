# Integrating the new sound system (D-134): a guide for the other threads

> **Corrected 2026-11-13 by the integration branch (Fable audit FA-05):** section 3's example now validates against
> `production_script.schema.json` (every `sound_events` item has `kind` and `what`; `class` and `at_word` are schema keys;
> `intentional_silence`, segment `mood` and `music` are schema fields). Sections 3 and 7 are replaced by guide v2
> (`SOUND_INTEGRATION_GUIDE_v2.md`, same folder), which wins where the two differ. "D-133" for this sound decision is D-136
> since the merge (the cheapest-run decision keeps D-133).

Written 2026-11-13 by the W1 sound thread. It is for every thread that builds or changes anything an episode makes heard, such as W2 2.5D, W3 maps, W4 LTX cut, the AV event thread, the A line and the Toba sample. Read it before you touch sound. The canonical rules live in the repo: `docs/SOUND_LIBRARY.md` (LIB-01..08) and `docs/EPISODE_FIRST.md` (SP-03..SP-07). Link to those rules; do not copy them.

## 1. What changed

- **One library.** `assets/audio/library/manifest.json` (schema `sfx_manifest.schema.json` v1) has 260 items: Mixkit, BBC, OpenGameArt, Incompetech music, ElevenLabs takes and procedural placeholders. Every item has a catalog block (era, environment, materials, action tags, mood, distance and more), a licence block and QC.
- **A sound designed per shot.** `episode/sound_plan.py` gives each shot:
  - a mood, a distance, what is seen and what is only heard;
  - the 6 layers: narration, ambience, foley, spot, music, transition;
  - one of 7 coverage states. Silence that is not declared with a reason FAILs.
- **A cue sheet.** `episode/cue_sheet.py` (`cue_sheet/1`) turns the plan into rows: level, distance (gain, low-pass, reverb), duck group, sync, take rotation, music crossfades and risers. It validates the result.
- **One renderer.** `audio/stems.py` plays the cue sheet into five stems. A bus limiter keeps the voice at full level.
- **A measured mix.** `audio/mix_check.py` checks delivered loudness and true peak, clipping, BP-52 narration protection, masked shots and digital silence.

The real runner already uses this: `episode/run.py` G8 calls `stems.render`, which builds, writes and validates the cue sheet.

## 2. Branch and file ownership

- Code base: branch `claude/project-thread-xpsv3w`, commit `d1b96141`, PR #171 (draft). Branch from it on your own branch. Do not commit to xpsv3w.
- **The AV thread** ("Plan unified map, 2.5D motion and sound", branch `claude/project-thread-98b6wy`) now owns `episode/sound_plan.py`, `episode/cue_sheet.py`, `audio/stems.py`, `audio/mix_check.py` and `production/scene_join.py`. A change to these files goes through that thread.
- **The W1 thread** keeps the library: `manifest.json`, `taxonomy.json`, the `*picks*.json` files, `audio/free_import.py`, `sources.py`, `catalog.py`, `asset_qc.py`, `sfx_library.py`, `sfx_manifest.schema.json` and `docs/SOUND_LIBRARY.md`. A new sound goes through a pick list (section 5), never by hand.

## 3. How to give a shot its sound

Write the sound into the shot itself, in the production script. Never write it into a side file.

```json
"sound_events": [
  {"kind": "foley", "what": "chariot", "class": "chariot", "at_word": "crosses", "distance": "medium"},
  {"kind": "spot", "what": "war_horn", "class": "war_horn", "at_word": {"line_id": "S03_L004", "word": 0, "offset_s": -0.2},
   "distance": "distant"},
  {"kind": "spot", "what": "ov_draw", "class": "ov_draw", "at_s": 1.0, "dur_s": 1.8}
],
"intentional_silence": "the moment after the king falls: only room tone"
```

- `kind` (ambience, foley, spot, music) and `what` are required by the schema; `class` names the class id directly.
- Anchor on a word where the shot has a read line: `at_word` (a phrase of the shot's line, or `{line_id, word, offset_s}`)
  follows the read when G6 retimes the shot; `at_s` stays for shots without a line. Exactly one of the two (FA-06).
- `class` must be a class in `sound_plan.EVENT_CLASSES`. An unknown class raises `ContractError`. Add the class once, with its tags, in sound_plan (through the AV thread).
- `at_s` is relative to the shot and must fall inside the shot; G6 lists every anchor that falls outside the retimed shot.
- `distance` is close, medium or distant. If you leave it out, the shot size sets it.
- Optional fields: `library_id` (pin one take), `dur_s`, `picture_event`.
- **Every visible action gets its own sound** (ვანო, 11-12; BP-192): a map move, a counter, a route drawn, a pin set. The narrator naming a war does NOT add battle sound. Only what is seen or authored is heard.
- On a map shot, narration words never add sounds. Only the shot's actions and the `sound_events` do.
- A segment may set `"mood"` (one of `sound_plan.MOOD_NAMES`: aggressive, tragic, tense, dark, mysterious, heroic, epic, reflective, peaceful, joyful, neutral) and `"music": true/false`. If it sets nothing, the mood read from the words is used and listed as a candidate.
- Silence is a sentence, never `true`.

## 4. How to run and check

```bash
# a scene from LTX clips with their own speech (W4, the Toba sample)
python -m explainer_engine.production.scene_join assets/audio/scene_cards/<card>.json --out <dir>
#   -> final mp4, final_stems/, cue_sheet.json, sound_coverage.md, mix_check.json

# a whole episode: G8 builds the cue sheet and the stems
python -m explainer_engine.episode run <episode> --to qa

# the library
python -m explainer_engine.audio.catalog search --category weapons --era bronze_age --playable
python -m explainer_engine.audio.catalog preview --category vehicles --out <dir>
```

The example scene card is `assets/audio/scene_cards/battle_troy_2026-11-13.json`. It has clips with `"what"`, bed classes, spots, and music per clip.

Read `sound_coverage.md` and `mix_check.json` before you show anything. Anything shown to ვანო is built through this production path, not through a test build.

## 5. Missing sounds

- Never fill a missing class with an unrelated sound. List it under `needs` and leave the event `review_required`.
- Fill gaps in this order (ვანო 11-12):
  1. the library;
  2. a free source through a pick list (`free_picks_*.json` / `bbc_picks_*.json`, run with `python -m explainer_engine.audio.free_import <picks.json>`);
  3. ElevenLabs SFX, with a list priced in credits first and ვანო's word before buying.
- Missing now for maps and data:
  - map_pin_set, map_line_strain, map_line_snap and a flag-like cloth_flap;
  - only 1-2 takes each for route draw, click, tick and riser (BP-57 wants 3).
- The full table is in `W1_AV_HANDOFF.md` (same folder).

## 6. Rules that stay binding

- **Licence matters only for background music** (ვანო 07:24). Effects are chosen by quality. BBC (RemArc) is allowed for effects only (the 07:49 card), never for music.
- **Numpy or procedural sound never plays in production** (OV-56). Procedural items are preview placeholders.
- **Three statuses stay apart:**
  - `licence.production`: only `verified` plays;
  - `qc.status`: technical only;
  - `review.human`: `not_listened` everywhere today.
  A QC PASS never means "sounds good".
- **No hard-coded file names.** Pick takes through `sfx_library` and the catalog.
- **No second timeline, sound director or library.** Extend these files instead.
- **One level everywhere.** Delivery is -14 LUFS (BP-50). The voice stays protected by BP-52 (music at least 10 LU under, bed 15, combined 14).
- **Nothing paid without ვანო's word.** That covers ElevenLabs, Modal and Gemini 2K.

## 7. Known gaps (do not assume these are done)

1. `audio/mix_check` and `qa/sound_realism` run only from `scene_join`. `episode/run.py` G8 does not call them yet. Wiring them in is P0-C of the AV plan.
2. The ID D-133 is used twice: once for W1 sound on xpsv3w and once for the cheapest combination on nvctxh (PR #172). One must be renumbered at merge.
3. The demo has two REVIEW items:
   - the c1→c2 pause reads 0.68 s because the VAD hears the march bed;
   - c3's background is within 10 dB of the voice.
4. Nobody has listened yet. The creator's notes will come to the W1 thread, which will pass on any change to the AV thread's files.
