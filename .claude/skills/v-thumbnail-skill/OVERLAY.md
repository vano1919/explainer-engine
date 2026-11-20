# Overlay for `v-thumbnail-skill`: Thumbnail from our own episode (layer L26, stage S18, after G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/thumbnail-skill, page `thumbnail-skill` (MIT, commit `751f21a741`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel where the thumbnail's content is the owner's choice,
its pictures are ours, and its rules live in docs/THUMBNAIL_RULES.md (TN-01..TN-19). The upstream text
is this folder's `SKILL.md`; the package in `src/thumbnail_skill/` runs locally as a compositor, and `docs/` explains its schema.

## What a thumbnail is here

One picture that makes a promise the video keeps (TN-01): a named hero or a moment that is in the episode, one thing
withheld (TN-02), one focal subject big (TN-03), at most four words set by us, never lettered by a model (TN-04),
readable at phone size (TN-05), the lower-right corner free (TN-06), 1280x720 JPEG under 2 MB (TN-09). The title and the
thumbnail say different halves of one promise, paid at a named timestamp (TN-18).

## Material: only ours

- **Allowed:** frames of our master or clips, our turn-pack pictures (`explainer_engine/imagegen/turn_pack.py`, D-131), our
  free local 2x upscale of them, our maps, our fonts and palette tokens (`explainer_engine/design/palette.json`).
- **Never:** third-party footage or stills, film posters or key art (the named era film is a style lens in prompts, not a
  source of pixels), a franchise logo or title font, stock photos, archive photos without a verified free licence, real
  victims, gore, or anything TN-07 lists (docs/RIGHTS_AND_FAIR_USE.md, `python -m explainer_engine.rights.ip_check`).
- **A new face or character** for the thumbnail is never invented; heroes keep their approved sheets (invariant 6), and
  anything new is a collage of variants for the owner first (TN-13).

## Procedure

1. **The concept in one sentence** (`thumbnail.concept` in `publish.json`): who, what stake, what is withheld, and where the
   video pays it. Write two or three concepts of different mechanism (a clash of scale, a paradox, a Day 1 to Day N jump;
   CRAFT-PKG-01 in skill `shorts-for-video`) for YouTube's Test and Compare.
2. **Pick the source frame** from the G10 contact sheet or a shot's clip: eyes open, sharp, the hero big. Pull the exact
   frame with `look.py --at T` or `thumbnail/extract_frame` (one timestamp, nothing else). The choice is ours, not the tool's.
3. **Compose for free** with the vendored renderer: a document with the picture, the headline text with explicit line
   breaks, positions, and `output.preset: youtube`:
   `PYTHONPATH=.claude/skills/v-thumbnail-skill/src python3 -m thumbnail_skill.cli run - --json < doc.json`.
   Fonts by `font_id` only; `doctor --json` shows what resolves. `render_variants` gives N layouts, each checked at
   320 px wide for text height and contrast; `place_text` moves a headline off a face.
4. **Paid paint only when asked.** `python -m explainer_engine.publish thumbnail episodes/<id>` prints the prompt and the
   price and spends nothing; `--generate --approved-by '<who, where>'` paints one picture on Gemini's premium tier, sets our
   words and checks the machine-checkable TN rules. That is a paid call: estimate in the ledger, the owner's word first,
   saved as it arrives (OR-33). Default is the free composite from step 3.
5. **Check** at phone size and in greyscale by eye, run `python -m explainer_engine.qa.publish_check <publish.json>`, and
   answer the TN-10 questions: is every element in the video, does it read small, would a viewer feel cheated at minute two.
6. **The owner picks** and sets it in Studio. The API sends no thumbnail for a Short (TN-11).

## Hard rules that bite here

- Honest promise: never an outcome the video does not reach, never a reenacted face presented as a photograph of the event.
- No model lettering; our headline, exact spelling, one typeface.
- Every picture made by Gemini carries SynthID; disclosure is decided per video by the checklist (YouTube Help 14328491).
- The owner's signature slot (TN-12) follows the wording limits in that rule, with a clear margin.
- No upload from here (invariant 4); `explainer_engine/publish/stage.py` runs only after the owner's OK.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| The headline vanishes at phone size | thin font, low contrast, too many words | four words or fewer, paper-on-night pair with an ink outline (TN-05) |
| A face is covered | text placed before faces were known | `place_text`, or move the crop |
| `MISSING_INPUT` on a font | a font path or an unknown `font_id` | use a registry `font_id`; add our font to the registry, never substitute |
| The frame is soft | a mid-motion video frame | pick a held frame, or the turn-pack picture, then the free 2x upscale |
| `preset_limit_exceeded` | canvas or file over the YouTube preset | 1280x720 JPEG under 2 MB |
| The thumbnail shows something not in the video | concept drifted | rewrite the concept from a real shot (TN-01) |

## Checks in code

`explainer_engine/publish/thumbnail.py` (paid paint, our lettering, machine TN checks), `explainer_engine/qa/publish_check.py`
(PC rows incl. the recorded approval), `explainer_engine/rights/ip_check.py`, and the planned S18 validator
`explainer_engine/validators/thumbnail.py` (planned, W2).

## References: when to open which

| File | Open when |
|---|---|
| `README.md` | the ThumbnailDocument schema, element and output tables, error codes |
| `docs/model.md` | how canvas, assets, elements and z-order fit together |
| `docs/architecture.md` | what render, variants, layers and batch do |
| `docs/ffmpeg-skill.md` | `extract_frame` from a video (needs skill `v-ffmpeg-skill` reachable) |
| `docs/decisions.md` | why the renderer refuses to wrap text or pick a frame |
| `docs/security.md` | input roots and refused keys |

## Not used from upstream

`generate_background` (an AI background from an unapproved model; our pictures come from the episode), brand-kit files of
other ecosystems, `render_batch` from CSV (one thumbnail per episode), presets for TikTok, Instagram and X (not researched,
CRAFT-PKG-09), and `choose_frame` from a third-party face detector document.
