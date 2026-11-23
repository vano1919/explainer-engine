# Overlay for `v-color-grading-skill`: Colour operations as typed, checked steps (layer L22, stage G9 and G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/color-grading-skill, page `color-grading` (MIT, commit `92da7062a6`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a pipeline that is SDR from the first picture to the master. The
upstream text is this folder's `SKILL.md`. Its package (`src/color_grading/`, `contract/contract.json`) needs
the separate ffmpeg-skill engine, which is not vendored, so it is not run here; `README.md` and `docs/architecture.md`,
`docs/decisions.md`, `docs/security.md`, `docs/testing.md` stay as the design to copy when our own colour code grows.

## The split we take from it

Upstream's whole idea is one line: **deciding a colour treatment and executing it are two different jobs.** The decider
names the operation and every value; the executor accepts only typed operations, refuses command strings, re-measures
what it wrote and records where every byte came from. Our system already works this way in places; this page keeps it so.

| Job | Who, here |
|---|---|
| Decide the look of a series | the creator's film pick (rule 20), proposed as a grid (skill `v-scenario-video-color-grade`) |
| Decide a scene's grade and key frame | the edit plan and `explainer_engine/world/eras.json` grades, approved |
| Execute the shot-to-shot transfer and the era look | `explainer_engine/finish/grade.py` inside `explainer_engine/production/assemble.py` (G9) |
| Execute resize, sharpen and grain on clips | `explainer_engine/finish/upscale.py`, `explainer_engine/finish/superres.py` |
| Measure the result | `explainer_engine/videolane/master_qa.py`, `explainer_engine/qa/final_frame_qa.py`, `explainer_engine/episode/acceptance.py` (G10) |

## Which upstream operations matter for us

Our sources are display-referred 8-bit SDR: the chat tool's PNGs, LTX's H.264 at 1280x704, our own renders. So:
- **Relevant:** a 3D LUT applied at a stated strength; a primary correction with explicit exposure, contrast,
  saturation, temperature and tint (white balance is just these two values, never automatic); levels; matching one source
  to a reference frame (ours is the Reinhard transfer toward the key master frame, BP-130); rewriting colour tags; a soft
  clip into legal range when a delivery asks for it.
- **Not relevant:** HDR to SDR tone mapping, Dolby Vision metadata, camera log, OCIO and ACES transforms. If one of these
  ever seems needed, something upstream of us changed; stop and ask (invariant 12).

## Procedure for a colour step outside the era grade

1. **Write the decision down** before touching a file: the operation, every value, the reason, which shots. A value no
   one chose is not filled in by a default (OR-22).
2. **Run it through code that takes typed values**, never a pasted ffmpeg filter string from a chat or a note. For a
   one-off, go through the FFmpeg toolbox page's wrapper with a dry run first (skill `v-ffmpeg-skill`).
3. **Write a new file**, never over the input; keep the container.
4. **Re-probe the output**: its length and frame count equal the source's; its colour tags are what you meant; the picture
   is not visibly shifted (look at one frame of each side).
5. **Record provenance**: input sha256, the operation and values, the output sha256, the tool version. A changed file is
   a new asset; its old observation no longer counts (`explainer_engine/episode/shot_state.py`).

## Watch item found while rewriting (to measure, not yet a fix)

Our encoders pipe RGB frames into libx264 as `yuv420p` without stating a colour matrix, range or primaries
(`production/assemble.py`, `finish/upscale.py`). ffmpeg's default conversion for untagged RGB can use the BT.601 matrix,
while players and YouTube treat untagged HD as BT.709, which would show as a slight hue and saturation shift between our
graded frames and the uploaded master. This is unmeasured: compare a graded frame with the same frame decoded from the
master (`ffprobe` tags, a pixel diff) before proposing an explicit BT.709 tag as a change with its focused test.

## Failure modes and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| Colours shift after upload but not locally | untagged or wrongly tagged master | measure as above; tag explicitly only with a test |
| A LUT applied "at zero strength" still changes everything | upstream's noted LUT-strength quirk in some engines | never use a zero strength to switch a LUT off; leave the step out |
| A graded clip is one frame shorter | audio trimmed with `-shortest` | keep the frame count check in step 4 |
| A white-balance fix makes skin green | temperature corrected without tint | set both values, test on the portrait anchor |
| Banding in the sky after a grade | 8-bit source pushed hard | gentler curve; grain last (ED-04) |

## Rules of our system at this layer

- Grade fixes colour, not content: a wrong object or place is R3, not a correction (P-5).
- One constant look over the episode (ED-04); no per-shot creative grades beyond the table.
- No paid tool and no generative model touches colour.
- Never weaken a validator to make a graded file pass (invariant 7).

## References: when to open which

| Need | Open |
|---|---|
| The operation table, limits and error codes | `README.md` ("Supported operations", "Current limitations", "Error handling") |
| How a typed operation graph, identities and provenance fit together | `docs/architecture.md` |
| Why each boundary was drawn (the ADRs) | `docs/decisions.md` |
| What a colour executor must refuse | `docs/security.md` |
| How to test colour code against real media honestly | `docs/testing.md` |
| The request and response schema as data | `contract/contract.json` |

## Not used from upstream

The package itself (it needs ffmpeg-skill, which we do not vendor), its CLI and doctor, HDR, Dolby Vision, OCIO and ACES
paths, the video-production-agent it expects as a caller, and container rules beyond "keep the source's".
