# Integrating sound with the AV event contract (D-134 + D-135): guide v2

> **Corrected 2026-11-13 by the integration branch (Fable audit FA-05, FA-06, FA-10):** the schema now has `class` and
> `at_word` on a sound event, `intentional_silence` / `sound_design.silence` on a shot, `mood` / `music` on a segment, and
> `at_frac` / `from_frac` / `to_frac` on a 2.5D motion item. The text below says so where v2 said the opposite.

Version 2, 2026-11-13, written by the AV thread (branch `claude/project-thread-98b6wy`). It replaces sections 3 and 7 of W1's guide
(`/mnt/project-files/sound_library_2026-11-13/SOUND_INTEGRATION_GUIDE.md`, v1) so that the guide fits the system and not the other way
round (the creator, 08:53 UTC). Sections 1, 2, 4, 5 and 6 of v1 still hold, with the three corrections in the box below. The canonical
rules live in the repo: `docs/EPISODE_FIRST.md` (AV-01..AV-08, MA-01..MA-08, L25-01..L25-06, SP-01..SP-07) and `docs/SOUND_LIBRARY.md`
(LIB-01..LIB-08). Link to them; do not copy them.

> **Corrections to v1 sections 1, 2, 4, 5 and 6**
> - v1 section 1: G8 now also runs the mix check (`qa/mix_check.json`) and G10 the realism rows (`qa/sound_realism.json`) and the per-event
>   report (`qa/av_event_report.json/.md`). The old "Known gap 1" is closed.
> - v1 section 2: a separate video-montage thread owns assembly (`production/assemble.py`) and the 60 % LTX lane. It calls the sound
>   files but does not change them; the AV thread does not touch assembly or LTX. A field both need (for example `continuity_mode`,
>   `handles`, `speech_window`) gets one definition, agreed between the two threads.
> - v1 section 3's example did not validate (its items had no `kind` and `what`); corrected in v1 on 2026-11-13. `class` is a
>   schema key since the integration branch (FA-05).

## 3. How to give a shot its sound (rewritten for the AV contract)

There are now **two kinds of sound in a shot**, and both live in the shot itself, in the production script. Never write them into a
side file.

### 3a. A sound tied to something the picture does: the event's `audio`

Every visible event carries its own audio decision. A visible event is an item of `actions` (a map shot) or an item of
`motion_imitation` (a 2.5D shot). `episode/events.visual_events` resolves it once, and the map renderer, the 2.5D renderer, the sound
plan and QA all read that one result.

```json
"actions": [
  {"kind": "route_arrow", "at_word": "lay", "until_word": "away", "from": "toba", "via": ["indian_ocean"], "to": "shinfa",
   "event_id": "P1.route",
   "audio": {"decision": "sfx", "class": "map_route_draw", "sync": "span", "purpose": "clarify"}},
  {"kind": "marker_travel", "at_word": "lay", "until_word": "away", "route": "P1.route", "event_id": "P1.ash",
   "audio": {"decision": "silent_by_design", "why": "rides P1.route and shares its sound"}}
],
"motion_imitation": [
  {"effect": "push", "from_frac": 0.0, "to_frac": 0.45, "easing": "ease_out", "hold_frames": 6, "event_id": "P4.cam1",
   "audio": {"decision": "silent_by_design", "why": "camera move"}}
]
```

- `decision` is exactly one of `sfx`, `ui_cue`, `ambience_only`, `music_only`, `silent_by_design` or `review_required` (AV-04).
  - `sfx` and `ui_cue` need a `class` of `sound_plan.EVENT_CLASSES`.
  - `silent_by_design` and `review_required` need a `why`.
  - `silent_by_design` counts as a beat, never as a missing sound (BP-55).
- `sync` says where the sound lands:
  - `onset` lands on the first frame;
  - `span` lasts the whole action, and a continuous action's `sfx` must be a span;
  - `end` lands on the arrival, `end_frame - 1`.
- `purpose` is one of clarify, humour, transition or sync (BP-55). A sound without one is a REVIEW.
- Timing comes from the words (AV-05):
  - `at_word` (or `at_frac`, a share of the shot; `at_frame` only on a shot without a read line) starts the event;
  - a 2.5D camera segment anchors on `from_frac` / `to_frac` (shares of the shot) or on its words, so it keeps its place when
    the read changes the shot's length (FA-06); an absolute frame under a read line is a G1 REVIEW in a locked script, and G6
    lists every anchor the retimed shot no longer holds;
  - `until_word` ends it where the word after that phrase starts;
  - frames are half-open, `[start_frame, end_frame)`.
- Derived cues are added for you (AV-06):
  - a route or supply line gets `.arrive`;
  - a marker without a route gets `.arrive`;
  - a number counted silently or with a `ui_cue` gets `.done`.
  - `"cues": "none"` turns them off. Use it to keep to BP-81's budget.
- **A locked script** (`"av_contract": "av_events/1"`) needs `event_id` and `audio` on every item, or G1 FAILs (AV-02). An older script
  still runs on derived ids and the default decision of each kind (`events.DEFAULTS`), and G1 says REVIEW (AV-03).
- **Camera moves are silent by default.** A sounding camera move is a REVIEW for a person.

### 3b. A sound the picture does not draw: `sound_events`

```json
"sound_events": [
  {"kind": "spot", "what": "eruption_boom", "class": "eruption_boom", "at_word": "erupts", "picture_event": "eruption"},
  {"kind": "foley", "what": "chariot", "class": "chariot", "at_word": {"line_id": "S03_L002", "word": 3, "offset_s": 0.1},
   "distance": "medium", "event_id": "S03.chariot", "purpose": "clarify"},
  {"kind": "spot", "what": "ov_draw", "at_s": 1.0, "dur_s": 1.8}
]
```

- `class` names the class id of `sound_plan.EVENT_CLASSES`; without it `what` names the class (its id, or words that name one).
- `kind` is required: ambience, foley, spot or music.
- `at_word` (a phrase of the shot's line, or `{line_id, word (index from 0 or text), offset_s}`) lands the sound on a word of
  the read and follows it when G6 retimes the shot; `at_s` (relative to the shot) only where the shot has no read line.
  Exactly one of the two (FA-06).
- Optional fields:
  - `distance` (close, medium or distant; otherwise the composition plane or the shot size decides);
  - `dur_s` (a span);
  - `library_id` (pin one take);
  - `event_id` (default `<shot>.S<k>`);
  - `purpose`.
- `picture_event` makes the 2.5D picture react: boom and eruption give a shake and a lightning flash, impact a shake, thunder and flash
  a lightning flash. Its purpose defaults to sync. **This is the only way a shake or a timed flash reaches a picture** (L25-04).
  Since FA-10 the resolver (`events.visual_events`) resolves it too (`source: sound_events`), so the picture and the event
  report use the same frame.

### 3c. What never makes a sound

- **A word never places a sound and never moves a picture** (AV-07). A word of the read, or of the shot's action text, that names a
  class is listed under the shot's `candidates`, with its time on the measured or estimated clock, for a person to author or ignore.
  - The five regression sentences place nothing and move nothing: "The empire falls.", "In March.", "People moved into the region.",
    "The army was fired up." and "The commander was in charge." (`tests/unit/test_av_events.py`).
  - This replaces v1's "only what is seen or authored is heard". Now only what is authored is heard, either as an event's `audio` or
    as a `sound_events` item.
- **A missing take is never replaced with an unrelated one.** The event goes on the `needs` list, becomes `review_required` in the cue
  sheet and is listed by `review_required_events`.
- The library is matched on its catalog facets first. Where a catalog is `inferred`, it falls back to the legacy tags and records that
  per class (`match`, `inferred_catalog`, `qc`, `human` in the sources). Today almost every AV class uses the legacy fallback, because
  its candidate takes have `inferred` catalogs.

### 3d. The budgets the design must keep (measured on the cue sheet, G8)

| rule | what is measured | band |
|---|---|---|
| BP-54 | the onset measured on the rendered SFX stem against the event's frame | one frame PASS; -45/+125 ms REVIEW; outside FAIL |
| BP-55 | the share of visual beats that carry an audible non-cue effect | at most 50 % (REVIEW) |
| BP-56 | simultaneous layers, from the intervals (voice, music and bed counted once each) | at most 5 layers, at most 2 of one class |
| BP-81 | cues a minute (from 30 s of read), bursts in 10 s, emphasis cues a line | REVIEW over 8 a minute, FAIL over 14; REVIEW over 3 in 10 s; more than one thud, chime or rise on a line FAILs |

The first pilot run shows why these budgets matter. With every default cue on, three map shots in 43 s gave 14.1 cues a minute (FAIL)
and four emphasis cues on one line (FAIL). Since then the line's draw sound starts the line itself (no start cue), and a number with
its own riser takes no second confirmation.

### 3e. Segments

A segment may set `"mood"` (an enum: `sound_plan.MOOD_NAMES`) and `"music": true/false`; an authored mood wins, a mood read
from the words is only a candidate (FA-09). A shot is silent on purpose with `"intentional_silence": "<the reason>"` (or
`"sound_design": {"silence": "<the reason>"}`): a sentence, never `true`; it keeps only the room tone (SP-04). A place's bed is
authored once on the location (`world_bible.locations[].ambience_bed`: `classes`, `room`), never read from the prose (FA-09).

## 7. Known gaps (do not assume these are done)

1. **The AV takes are missing or thin**:
   - There are no real takes for `map_pin_set`, `map_line_strain`, `map_line_snap` or a flag-like `cloth_flap`.
   - The others have one or two takes each, under BP-57's three.
   - In the pilot these events are `review_required` and the render is not shippable. Filling them follows v1 section 5: library, then
     a free pick list, then priced ElevenLabs on the creator's word.
2. **73 library items are vault-only.** Their WAVs are not on HF, so their QC is NOT_RUN where nothing was measured.
3. **D-133 is used twice** (closed 2026-11-13 by the integration branch): W1's sound decision is D-136, the cheapest-run
   decision keeps D-133, the video lane D-137, this contract D-135.
4. **BP-56's severity differs.** The registry lists BP-56 as REVIEW, while W1's code and test FAIL a crowded mix. The FAIL is kept
   (no test is weakened); the creator's word decides.
5. **The creator has two different words on map sound.**
   - D-133 (2026-11-12): every overlay or map motion has its own heard sound.
   - The 08:43 brief and BP-81: `silent_by_design` is a valid decision, with cue budgets.
   - **Decided 2026-11-13 11:44 UTC (his card):** silence is allowed with a budget. A map or 2.5D motion may be `silent_by_design`
     with its reason, within BP-81's budget. This replaces D-133's "every map motion heard" for these routes (D-135 row).
6. **The montage thread's shots are not covered.** LTX 60 % shots, their own speech and their handles belong to the montage thread.
   This contract covers `map_action` and `still_25d` only. An LTX shot can carry `sound_events`, but nothing here draws its picture.
7. **Nobody has listened.** Every event in `qa/av_event_report` says `human: not_listened`. A machine PASS is never a person's
   approval.
