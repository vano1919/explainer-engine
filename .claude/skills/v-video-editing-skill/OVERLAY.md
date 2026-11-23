# Overlay for `v-video-editing-skill`: Typed edits with provenance (layer L21, stage after G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/video-editing-skill, page `video-editing-skill` (MIT, commit `2f77b39f55`). Rewritten 2026-11-20 under
RW-50 ([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for the side edits of an episode whose master is drawn by our
own runner. The upstream text is this folder's `SKILL.md`; the Python package in `src/video_editing_skill/`
runs as is, and `docs/operations.md`, `docs/contract.md`, `docs/decisions.md` explain every field.

## Why we keep it

The engine takes a JSON request (sources, typed operations, outputs) and returns, for every output, its sha256, an
observed probe and a timeline that maps each output second back to a source second. That map is what a Short needs: the
captions of a Short cut from the master are the main read's own word timings (Scribe, G6) shifted through the map, so no
second read and no second transcription are paid for. It also refuses commands, filter strings and executables in a
request, which keeps a side edit from turning into a hidden render path.

## When to use, when not

- Use for: a Short cut from `renders/final/<id>_master.mp4` (moments joined, a 9:16 `FILL` anchored on a hero, a
  `PUNCH_IN` on a face box); a review excerpt for the owner; a still title card turned into a clip (`IMAGE_INSERT`) for a
  Short's pointer frame.
- Not for: the episode master or any chunk (G9 only, P-8); choosing which moment wins (skill `shorts-for-video`); captions
  text (written in the Short's block, burned by the Short renderer); colour or loudness work.

## Procedure

1. **Environment once.** Point the engine at the vendored scripts:
   `VIDEO_EDITING_FFMPEG_SKILL_DIR=.claude/skills/v-ffmpeg-skill`, then
   `PYTHONPATH=.claude/skills/v-video-editing-skill/src python3 -m video_editing_skill doctor --json --workspace <dir>`.
   `ok` must be true and the operations you need must be listed as supported. The planned wrapper
   `explainer_engine/finish/ffwrap.py` (planned, W2) will set both and keep the workspace inside the episode folder.
2. **Build the request** from facts, not guesses: the master's probe, the moment's start and end on the master clock
   (cut on sentence edges of the main read), the hero's box from the shot record or a motion-centre probe
   (`cropdetect.py --motion-centre` in skill `v-ffmpeg-skill`).
3. **Plan** (`plan - --json`): read the operation graph, the target frame and the timeline map. Nothing is written.
4. **Run** (`run - --json --workspace episodes/<id>/shorts/work --allowed-input episodes/<id>`). Keep the response JSON
   beside the output; it is the Short's provenance.
5. **Map the words.** Shift the main read's word timings through the response timeline; drop words that fall in a cut.
6. **Hand over** to the Short renderer for captions, music bed and the pointer line, then `qa/short_format.py`.

## Operations we use, and how

| Operation | Our use | Watch |
|---|---|---|
| `TRIM`, `CUT` | pull a moment out of the master | `precision: frame`; cut on a pause of the read, never inside a word (ED-12) |
| `CONCAT` | join the Short's moments | `transition` none (hard cut); a Short never dissolves between moments |
| `FILL` with `anchor` | the 9:16 window from the 16:9 master | anchor x on the speaking hero; faces never cut (SH-03) |
| `PUNCH_IN` | a hard zoom on a face box when a hero's line lands | box from data, scale modest; the subject choice is ours |
| `IMAGE_INSERT` | the hook card or pointer frame as a clip | our own lettering, our palette |
| `SPEED` | the whole Short a little faster when the plan asks | picture and sound together; the timbre check decides (SH-02) |
| `CROP` | an exact box when `FILL` cannot place it | even sizes, inside the frame |

## Hard rules that bite at this layer

- Inputs are our own files only: the master, its clips, our pictures. No third-party footage, no stock clips (invariant 5,
  docs/RIGHTS_AND_FAIR_USE.md).
- A Short is 9:16 in the Short frame of `explainer_engine/core/delivery.py` (BP-167); anything else is a render fault.
- Outputs land in the episode folder; nothing is uploaded from here (invariant 4). Staging is `publish/stage.py` after
  the owner's word.
- The request carries no shell, argv or filter keys; the engine rejects them, and we never try.

## Failure modes and fixes

| Symptom | Cause | Fix |
|---|---|---|
| `TOOL_ERROR` before running | engine cannot find the vendored scripts | set `VIDEO_EDITING_FFMPEG_SKILL_DIR` as above |
| `UNSUPPORTED_OPERATION` | asked for a layer or motion graphic | that is not an edit here; draw it in the Short renderer |
| face cut at the window edge | anchor from the frame centre | anchor from the hero's box; `PUNCH_IN` instead of a wider fill |
| captions drift after a cut | words not shifted through the timeline | use the response timeline, never the request times |
| `INVALID_INPUT overlay_video_layer` | a video given as an overlay image | overlays are stills only here |

## Checks in code

- `explainer_engine/qa/short_format.py`: 9:16 and length of a rendered Short.
- `explainer_engine/production/shorts.py`: hook timing, caption speed and safe zone report of a Short.
- `explainer_engine/validators/shorts.py` (planned, W2): the Shorts validator named in skill `shorts-for-video`.

## References: when to open which

| File | Open when |
|---|---|
| `docs/operations.md` | the exact parameters and frame semantics of an operation (`FILL.anchor`, `PUNCH_IN`) |
| `docs/contract.md` | the request and response shape, error codes |
| `docs/decisions.md` | why an operation is refused or behaves as it does (ADR numbers) |
| `docs/security.md` | input roots and the refusal of commands |
| `examples/multi-aspect.json`, `examples/request.json` | a worked request to copy the shape from |
| `README.md` | `propose`, `validate` and the other subcommands |

## Not used from upstream

`CONDENSE` with automatic proposals (our cuts follow the script, not detected retakes), stingers, `REVERSE`, `ROTATE`,
the ecosystem roadmap and its agent hand-offs (video-production-agent, motion-graphics, detection), and installation into
the user's home skills folder.
