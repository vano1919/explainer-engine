# Blender layout scenes (blender_scene/1)

Lab only, free (Blender CPU), nothing here is imported by an episode run. Plan: `blender_series_plan_2026-11-20/PLAN_BLENDER_LTX_SERIES_2026-11-20_ka_v5.md`
(sections 2, 3, 4) in the project files. A scene spec turns into a grey 241-frame layout video that a later, paid layout-to-render step
may follow; that step needs its own OR-23 plan, OR-34 audit and the creator's recorded word and is not part of this document.

## Pieces

| File | What it is |
|---|---|
| `explainer_engine/schemas/blender_scene_1.schema.json` | the contract of one clip: place, people with tracks, cameras, cuts (authoritative, never loosened to pass a render) |
| `explainer_engine/lab/scene_spec.py` | loads and checks a spec, the pinhole projection, the validators V1-V9 (pure Python, no Blender) |
| `explainer_engine/lab/blender_lib.py` | the library: places (from `blender_blocking`), capsule people with animated tracks and poses, cameras bound to cuts |
| `explainer_engine/lab/scene_render.py` | spec -> frames -> `layout.mp4`, one PNG per view, `plan.png`, `report.json` (starts Blender itself) |
| `explainer_engine/lab/scene_sheet.py` | one contact sheet over all clips |
| `explainer_engine/lab/specs/t0/` | test T0: scene A (no man's land) and scene B (German trench), three chained clips each |
| `explainer_engine/lab/film_styles/1917.json` | version 2: film style card (DRAFT, camera language only: lenses, camera height, move types, V11/V12 thresholds; no colour or light field) |
| `explainer_engine/lab/specs/t0b/` | test T0b: `t0b_c1` (one continuous follow shot) and `t0b_am1` (5 views, each with a slow move) |

## Spec rules

- 24 fps, `clip_frames` 241 (frames 0..240 = 10.0 s of time), size divisible by 64 (1280x704 or 1920x1088).
- A cut spans `[frame_in, frame_out)`; the last cut also owns the final frame. Cuts tile the clip. One camera = one view.
- A view is 0.8-2.0 s. Five views of at most 2.0 s fill exactly 10.0 s only when every view is 2.0 s, so a clip with varied view
  lengths has six or more views.
- Positions in metres, compass headings (0 faces +y), tracks interpolate linearly, a pose holds from its key.

## Validators

`FAIL` blocks (a hard format limit or the creator's rule), `REVIEW` asks the creator to look (a hypothesis number from the blocking note,
never silently passed), `PASS`.

| ID | Checks | Status when it breaks |
|---|---|---|
| V1 | each view's focus people are in frame and at least 250/1080 of the frame height (hypothesis) | REVIEW |
| V2 | no two people overlap more than 25 % of the smaller box (hypothesis) | REVIEW |
| V3 | every view is 0.8-2.0 s | FAIL |
| V4 | a static person does not move; nobody moves faster than 2.5 m/s (hypothesis) | FAIL / REVIEW |
| V5 | lens in 28, 35, 50, 85 mm | FAIL |
| V6 | 8k+1 frames, size divisible by 64; after the render also the video's real frame count, size and fps | FAIL |
| V7 | each view PNG is the video's frame (same file as the rendered frame, PSNR >= 30 dB against the decoded mp4) | FAIL |
| V8 | chain: the next clip's first view is the previous clip's last view (camera, lens, people, poses) or it declares `new_photo` | FAIL |
| V9 | last view >= 1.0 s; camera still and people calm in the last 0.75 s (hypothesis for the movement limit) | FAIL / REVIEW |

The report also checks the pure-Python projection against Blender's own camera (`PROJ`, must stay under 1.5 px).

## Run

```
python -m explainer_engine.lab.scene_render explainer_engine/lab/specs/t0/t0_a1.json <out_dir> --samples 2 [--frames A:B]
python -m explainer_engine.lab.scene_sheet explainer_engine/lab/specs/t0 <render_root> <sheet.png>
```

`--frames A:B` renders a chunk and skips frames that exist (RULE-R1: a long render runs in chunks and resumes). Blender 4.2 is found
through `--blender`, `$BLENDER` or `PATH`. No GPU or GL is needed (Cycles CPU, OIDN fast denoise, 2 samples: about 2 s a frame at 1280x704
on 4 cores).


## Version 2: moving camera (T0b)

`version: 2` adds, and version 1 specs stay valid and unchanged (they report V11/V12 as `N/A` with what the check would have said):

- `cameras[].path = [{frame, pos, heading, pitch, lens, ease?}]`: pose by clip frame, linear between keys unless the key a segment
  starts at says `ease`: `in_out`, `out` (comes to rest, the way a camera stops), `in`. Before the first key and after the last the
  camera holds. Blender keys the camera every 4 frames from the same Python path (`PROJ` still compares it against Blender's own camera).
- `film_style`: name of a card in `lab/film_styles/`. V5 then reads the lens list and the camera-height range from it. The card is a
  `draft` (not source-checked, brief 2026-11-20): while `draft` is true a broken number is `REVIEW`, never silently passed; a card with
  `draft: false` makes V11/V12 and the height range block (`FAIL`). The card has no colour or light field (a card with one is refused).
- cut `long_take: true`: a declared single shot past the 2.0 s view limit. V3 then reports `REVIEW` (the creator's rule is broken on
  purpose and he must look); without the declaration a long view is still `FAIL`.
- cut `axis_cross_ok: true`, top-level `axis: [person, person]` (default: the first two people): the 180-degree line for V12.

| ID | Checks (version 2 only) | Status when it breaks |
|---|---|---|
| V11 | at each cut, the camera's angle change around the subject (focus person) and the size class change (close/medium/wide from the subject's height share of the frame). A jump = angle below the card's `min_angle_deg` (30, the general rule, unchecked for 1917) AND no size step | card draft: REVIEW, verified card: FAIL |
| V12a | the camera stays on one side of the line person 1 -> person 2 (within `axis_neutral_m` of the line counts as neutral) unless the incoming cut has `axis_cross_ok` | FAIL |
| V12b | movement handover: when the leaving and the entering camera both move (> `still_speed_mps`), their velocity directions in the camera's own frame differ by at most `handoff_max_direction_deg` and the speeds by at most `handoff_max_speed_ratio`; still to moving is not a handover | card draft: REVIEW, verified card: FAIL |

`report.json` gets `transitions`: per cut-to-cut transition the subject, angle change (deg), size class from/to, side of the line
from/to, camera speed and direction leaving and entering. `plan.png` draws every camera path with an arrow and the view wedge at the
first and last frame of the cut. V1/V2 sample every 12 frames while a camera moves.

All numbers on the card other than the three in the brief (eye height 1.5-1.7 m, the T0 lens list, the 30-degree rule) are the
engineer's placeholders so V11/V12 can run; the card's `unverified` list names each, and the creator confirms or replaces them.
