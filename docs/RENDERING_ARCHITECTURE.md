# Rendering architecture

Decision D-10 (provisional, gated by the Phase 4 benchmark). Hardware baseline: i5-8400 (6 cores), 16 GB RAM, RX 5700
8 GB (not assumed useful), constrained disk.

## Engine comparison
| Option | Best use | Strengths | Limits | Hardware impact | Licence | Confidence | Verdict |
|---|---|---|---|---|---|---|---|
| **Remotion** | data-driven 2D video from JSON | React/SVG/CSS, text layout and fonts, `Sequence`, `interpolate`/`spring`, draw-on paths, `renderMedia` with a frame range, `renderStill` for thumbnails, Studio preview | Node 20 + headless Chrome; SVG throughput on this CPU unmeasured | CPU; memory per concurrent tab estimated 0.3-0.5 GB [INF] | free for individuals and <= 3-person companies; terms may change in Remotion 5.0 (V-04) | M | **primary** after the benchmark |
| Python + skia-python + FFmpeg pipe | no-Node fallback | same language as the pipeline; the "frame(i) is a pure function" and one-FFmpeg-pipe pattern already proven in TMR | we would build text layout, rigging, easing and path drawing ourselves | CPU | BSD-3 | M | **fallback** (distinct role: no Node, no licence exposure) |
| Motion Canvas | hand-authored animation | strong timeline API | no confirmed official headless render (V-05); code-first, not JSON-first | | MIT | M | rejected |
| Revideo | headless Motion Canvas fork | headless API | current maintenance unconfirmed (V-05) | | MIT | L | rejected; re-check only if Remotion fails |
| Manim | maths diagrams | precise geometry | weak for characters; slow | CPU | MIT | M | rejected |
| TMR moderngl shaders | the sleep channel's GPU picture | working, deterministic | shader/raster art, owl-specific | GPU | | H | not reused |
Combining engines is not allowed without a documented distinct role.

## Design
- `render/` is a Remotion project (pinned `package.json` + lockfile; `npm ci`). One composition, `Episode`, receives the
  storyboard JSON, the resolved frame table (anchors to frames) and the asset manifest as input props. It contains only
  presentational React components for the vocabulary in [STORYBOARD_SCHEMA](STORYBOARD_SCHEMA.md); it never reads the
  network or the clock. Randomness is seeded per entity id.
- Determinism: frame(i) depends only on i, the props and the assets. Same inputs give byte-identical frames (tested by
  hashing a frame twice, Phase 4). Constant frame rate (P-13).
- Python bridge (`render_bridge.py`): validates, resolves anchors, writes `props.json`, runs `npx remotion render` /
  `still` per scene with a frame range, captures stdout to the job log, and reports peak memory.
- Intermediate format: silent H.264 MP4 per scene (CRF 18, yuv420p, constant fps, fixed GOP so scenes can be joined by
  stream copy). Final assembly: concatenate, then mux the Python-mixed audio once (AAC 48 kHz), +faststart.
- Scene cache key: sha256(scene JSON + referenced asset hashes + renderer lockfile hash + render profile + props schema
  version). Changing one scene re-renders that scene only; a changed asset invalidates its scenes only.
- Bounded parallelism: Remotion `concurrency` starts at 3 (benchmarked 2-5); one heavy step at a time per job; a second job
  waits. Memory: a monitor samples the process tree; above 85 % of RAM the concurrency halves for the next scene.
- Disk: pre-flight estimate = frames x measured MB per frame x 1.5; temporary files live in `<job>/tmp/` and are deleted
  on success and kept on failure (known-safe retention rules only, `core/jobs.clean_jobs` for whole jobs).
- Progress and cancellation: per-scene progress in `state.json`; cancel kills the child process tree and leaves finished
  scenes cached.
- Retry: a crashed browser tab is retryable twice; a deterministic failure (bad props, missing asset) is permanent.
- Output validation: ffprobe size/fps/duration/codec; black and frozen frame scan; every scene present; frame count equals
  duration x fps (copied TMR video checks).
- Thumbnails and contact sheets: `renderStill` from the same composition (thumbnail) and a Python tile of mid-scene frames.
- Vertical Shorts: a second composition `ShortEpisode` (1080x1920) with its own storyboard; components are shared, layouts
  are not.

## Phase 4 benchmark (decides D-10)
Measure on the real PC: a 20 s scene mix (Kit + 6 props + labels) at 1080p30: wall time, fps, peak RAM and disk, at
concurrency 2, 3, 4, 5; first-render vs cached; browser start cost. Gate: a 10-minute 1080p30 episode renders in under
2 hours with peak RAM under 10 GB; hash-identical re-render. A miss triggers the skia fallback proposal, not a silent
change.
