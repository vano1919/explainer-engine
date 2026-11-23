# Overlay for `v-subtitle-skill`: Captions (layer L25, after G9 and in the Shorts)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/subtitle-skill, page `subtitle-skill` (MIT, commit `abbf8effae`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for an English-only channel whose captions come from code that
already knows every word's time. The upstream text is this folder's `SKILL.md`; its package under `src/` is not
installed and not run; `docs/adr/` explains placement and Shorts captions when we change ours.

## Two kinds of caption

| Where | What | Code | Rules |
|---|---|---|---|
| **Long video** | a sidecar `subs.srt`, a switchable track the creator adds in Studio; nothing burned into the master | `production/cut_plan.py` (`subtitles`, `srt_text`, `check_subtitles`) | AS-09: the line's words only, never "MARCUS: " in a cue |
| **Shorts** | captions burned into the picture, word-timed blocks, plus `<id>_master.mp4` without them | `production/shorts.py` (`ass_captions`, `caption_report`, `safe_zone_report`) | BP-13 reading speed and block size, BP-29 the ad safe zone |

There is no caption upload code: the creator uploads the SRT in Studio with the video (invariant 4, upload per piece).

## Where the words and times come from

- **Words**: the script, exactly as written for the screen (the display form of numbers and dates, the hero's foreign
  words, the narrator's punctuation). Never the recogniser's text: a misheard name in a transcript must not reach a
  caption.
- **Times**: the measured word clock of G6 (skill `v-elevenlabs-speech-to-text`): each word's start and end from
  `audio/timing.json` and the aligned words. A clip-spoken line (D-132) is timed by its clip's measured speech
  (`videolane/ingest.py`) on the shot's frames, so its caption follows the hero's mouth, not the read.
- **Estimated words** (no heard time) still get a caption; if a block starts on one, check it by eye on the master.

## Procedure

1. G6 and G9 records are PASS or REVIEW; the master exists.
2. Long video: the cut plan writes `subs.srt` beside the master; `check_subtitles` must return no rows. Read the file
   once from top to bottom against the script: same words, no name prefix, no cue across a scene change.
3. Short: `production/shorts.py` builds the captions from the aligned words; read `caption_report` (BP-13) and
   `safe_zone_report` (BP-29) in its record; then look at frames with captions on a face-heavy shot.
4. Look before reporting: one contact sheet of caption frames per Short (skill `v-ffmpeg-skill` for tiles), a person's
   eye on placement, since a machine check cannot see whether a caption sits on a face.
5. The final plan's long-form caption limits (characters per line, characters per second) are W2 work as a registry row
   with its validator; until then BP-13 is the only sourced caption rule and applies to Shorts.

## Cue faults to look for (the upstream checklist, applied by hand or in our checks)

- **Overlap**: two cues on screen at once; after a retime the cut plan rebuilds them, never edit times in the SRT.
- **Too long a line, too many lines**: break at a phrase, never inside a name or a number with its unit.
- **Too fast to read**: more characters than the cue's time allows; lengthen the hold into the following pause before
  splitting the sentence.
- **Too short or too long on screen**: a one-word flash or a cue held over silence; join it to its neighbour.
- **On a face or a lower third**: in a Short move the block up inside the safe zone; in the long video a sidecar track is
  placed by the player.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| a caption reads "NAPOLEON: Forward!" | speaker prefix in the cue text | AS-09; the cut plan strips it; fix the source line if it carries the name |
| captions drift late over the episode | built from planned, not measured, lengths | rebuild after G6; the clock is `audio/timing.json` |
| a hero's line captioned at the wrong place | clip-spoken line timed from the read | take the clip's measured speech window |
| a wrong word | caption from transcript text | captions take the script's words only |
| Short captions jump around | block sizes outside BP-13 | adjust the block rule in `production/shorts.py`, not single cues by hand |

## References: when to open which

| File | Open when |
|---|---|
| `docs/adr/ADR-006-caption-placement.md` | designing face-aware placement for a Short (move a block when a face is under it) |
| `docs/adr/ADR-009-shorts-captions.md` | comparing its one-to-two-word Shorts chunks with our BP-13 blocks (ours win) |
| `docs/adr/ADR-011-animated-captions.md` | only if the creator asks for word-by-word highlight captions |
| `README.md` | the full list of cue fault codes and what each measures |

## Not used from upstream

The package CLI and its burn path through another skill's caption tool, machine translation and multi-language muxing
(the audience is US English), TTML and EBU-TT-D output, ruby, vertical text, East Asian line rules and regional
profiles, the font-directory option, and its default limits (ours come from the registry).
