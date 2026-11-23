# LTX Layout-To-Render jobs (S3, 2026-11-20)

> **Route-scoped since D-116 (2026-11-06), LTX-2.5 on the Modal path since D-132 (2026-11-12):** this worker belongs to the D-116 / D-132 LTX route (the Blender layout drives an LTX clip); for the v4.3 episode-first route (D-131) it is a separate, unrouted worker until the owner says otherwise.

> Status (2026-11-20 13:25 UTC): **the worker ran on an A100-80GB: L0..L3 green and T1 (`main`, one 10 s clip, 241 frames) DONE.** Measured
> numbers are in section 10. The owner's money frame is a shared **$6.00** for the layout and series tests with the 80 % stop at
> **$4.80** (his card, relayed 09:48 UTC, and his "go" at 13:02 UTC); the first $2.00 / $3.00 text below is history. Brief: project files
> `explainer-engine/blender_series_plan_2026-11-20/BRIEFS_S3_T0B_AND_T1_CARD_ka.md`, item 1.

## 1. What the worker does

A Blender grey `layout.mp4` (T0, 1280x704, 24 fps, 241 frames) + **one** Gemini first picture on frame 0 + one or two sentences ->
a 10 s LTX-2.5 clip, through `ltx_pipelines.ic_lora` at the pinned LTX-2 commit with the Layout-To-Render IC-LoRA. A chain (T1: clip
A, then clip B from a frame of A) is one job with `chain` rows.

| File | Role |
|---|---|
| `explainer_engine/training/pods/ltx/modal_layout_jobs.py` | the Modal worker: preflight, ladder L1..L4, `body()` (the container), ledgers, upload with read-back |
| `.../ltx/launch_layout_a100.json` | the launch file (pins, settings, caps, price); a NEW file, bound by the ladder's proof |
| `.../ltx/layout_job.py` | the job format, its free validation (LR-1..LR-5), the CLI command, the hand-over frame, `pack` (sha256-named batch tar) |
| `.../ltx/ic_lora_run.py` | wrapper: runs the CLI module in its own process and writes torch's peak memory on every exit path |
| `.../ltx/rehearse_layout_cpu.py` | the free CPU rehearsal of `body()` (fake CLI, fake HF client) |
| `tests/unit/test_layout_worker.py` | the tests (71: 70 on a plain box + 1 against the real pinned parser, which skips without the LTX packages) |

**Not touched** (coordinator, Q1): `ltx/launch.json`, `cloud/cheapest.*`, `modal_ltx_jobs.py`, `config/retired_era.json`, the old J2/J4
routes and `wan`. A test keeps the copied LTX pins equal to the protected launch's pins (it only reads that file) and a second test
keeps the retired-era list free of the new names.

## 2. The command (read from the argparse at the pinned commit)

`python -m ltx_pipelines.ic_lora` (LTX-2 `e98f6d927d83c92ef2be6aec76c8440b19306e39`), one process per clip, through the wrapper:

```
--transformer-path / --text-encoder-path / --video-vae-path / --audio-vae-path / --spatial-upsampler-path  (the five W5 files on /w)
--lora <IC-LoRA file> 1.0
--video-conditioning <layout.mp4> 1.0          # required by the CLI
--image <first picture> 0 1.0                  # frame 0 = the 'replace' binding
--stage-2-ic-lora                              # from the card's own example (Q-L2)
--prompt <1-2 sentences [+ film line]> --height 704 --width 1280 --num-frames 241 --frame-rate 24 --seed N --output-path <.name.mp4>
```

Facts that differ from the model card, found by reading the code (not assumed):

- The card puts the first frame at temporal position `-1` (the ComfyUI node). The pinned CLI refuses any `frame_idx < 0` and frame 0 is
  the `ImageReplace` binding, so the worker passes **0**.
- `euler_ancestral` and CFG 1 are not CLI arguments at the pin (the distilled sigma schedule is fixed: 8 + 3 steps). There is no
  `--negative-prompt` and no CFG flag, so none is passed.
- Two-stage generation needs sides divisible by 64 (the first stage runs at half size); 1280x704 is.
- The CLI default runs stage 2 on the bare checkpoint; `--stage-2-ic-lora` keeps the IC-LoRA and the reference on stage 2.

Proof: `test_layout_cmd_is_accepted_by_the_real_ic_lora_main_when_installed` runs the pinned `ic_lora.main()` up to the pipeline call (a
stub records the arguments) and checks frames, size, seed, prompt, the layout strength, the picture as `ImageReplace(0)` and the
LoRA. It passed in the LTX venv (torch + the pinned packages); on a box without them it skips.

## 3. The job and its rules (free, refused before any GPU)

`layout_job/1`, all paths relative to the job folder (see the module docstring for the fields). A job with a problem is never packed
and the container checks it again.

| ID | Rule |
|---|---|
| LR-1 | 1280x704 at 24 fps (CH-02, D-133), sides in 64, frames 8k+1 and not above `native.max_frames` (241); seed a whole number |
| LR-2 | the layout's sha256 is the job's (and its `report.json` `video.sha256`); ffprobe COUNTS the frames (`-count_packets`), size and rate; a report with status FAIL refuses the job |
| LR-3 | the first picture exists, is a readable image, its sha256 is the job's; a nearly grey picture is a warning (the card says a grey first frame gives a grey result; an engineering heuristic, not a source rule) |
| LR-4 | the prompt is one or two sentences and holds none of "clay", "3D", "Unreal" (the card's own rule); with a film line (variant B) more than two sentences is a recorded warning, not a refusal (Q-L4) |
| LR-5 | a chain: each row's `hop` equals its place; hop 3 and further needs `hop3_word` (the owner's message id; CT-1 in `LTX_PIPELINES.md`, Q6 open); a chained row brings no picture of its own (it starts from a frame of the previous clip; a cut is a job of its own) |

Hand-over (a chain's next first picture): `pick: last` (the default, as in `modal_ltx_jobs.handover_frame`) or `best_tail` (BP-199
person-weighted score over the last `window_s`), the speech floor (BP-187) and the crop rule (VL-05) are the LTX worker's functions,
copied, and a test keeps their source equal to that worker's. A clip whose line is not over by the last frame has no hand-over frame:
the chain stops, never a cut inside a line.

`python -m explainer_engine.training.pods.ltx.layout_job pack <job folder> <out dir> [--smoke]` validates and writes
`batch-<sha256>.tar.gz` (reproducible: sorted members, zeroed times). Upload it to HF `code/layout/batch-<sha>.tar.gz` (free) before L3;
the container fetches the sha256-NAMED file (never a name on main) and checks the hash before it unpacks.

## 4. The worker and its ladder (OR-37)

Each rung is recorded in `ladder_modal_layout.json` (shared gates folder), bound to the launch file's hash and the worker's hash (the
three files). Run only with `modal run <file>::<entry>`; the session hooks refuse raw `modal deploy|serve|shell|launch`.

| Rung | Entry | Where | What | Cap |
|---|---|---|---|---|
| L1 | `::check` | CPU | token pair, the launch file, the image imports torch, ltx_core, `ltx_pipelines.ic_lora`, PIL, numpy; ffmpeg/ffprobe exist | cents |
| L2 | `::weights` | CPU | the IC-LoRA (1.3 GB, gated) to the Volume and its sha256; the five base files checked by size (sha256 only with `--hash-base`) | `stage.cap_usd` 0.10 |
| L3 | `::smoke` | A100-80GB | the smallest legal clip (9 frames) | `caps.smoke_usd` 0.45 (was 0.20: the first smoke ran out of window) |
| L4 | `::main` | A100-80GB | the job's chain (T1: one 10 s clip) | `caps.run_usd` 1.2 |
| - | `::chain` | A100-80GB | one scene, each clip from a frame of the one before; a sibling row restarts from the first picture | `caps.chain_usd` 2.0 |

In the container (`body()`): the launch passed in is the launch baked into the image; an **attempt marker** per run key on the Volume
refuses a second attempt (Modal re-schedules a crashed input; a re-run with a fresh timeout would pay twice); the weights must be staged;
the batch hash must match; the job is validated again; a **clean deadline** (`subprocess.run(timeout=)` ends the CLI; no `os._exit`);
the end path (Volume copy, final upload, read-back) runs inside `caps.margin_s`; **after every finished clip** the record, the Volume copy
and one short HF round leave the container (OR-33); the final upload is read back from HF (LFS sha256 / git blob id) and a run
whose files do not verify ends `UPLOAD_UNVERIFIED`, not `DONE`. A next clip starts only if the time left is at least 1.15x the previous
clip's measured seconds. Results are plain JSON.

Local side: `preflight` (launch problems, the MODAL1 token pair, the creator's `modal` line in `spend_caps`, **CH-07**: a passing
`paid_offer/1` that names `explainer_engine/training/pods/ltx/modal_layout_jobs.py::smoke|main` and the A100-80GB), the GO
(`EE_MODAL_GO=<the creator's yes message id>:<plan sha256[:12]>`), the ladder gate, the batch on HF, the **ledger reservation before the
call** (`core/ledger.Run`, one ledger file per rung, line 3.5, STOP_FRACTION 0.8) and the night ledger, then settlement from the measured wall seconds.

## 5. The launch file's arithmetic

- A100-80GB, 4 CPU, 32 GiB = **$2.9428/h** (`cloud/modal_schedule`, prices of 2026-11-07, the same card as the P2 judge launch). CPU
  stage 4 CPU / 16 GiB = $0.3165/h.
- Caps (13:25 UTC): smoke 0.45, run 1.2, chain 2.0; each rung has its own ledger file with line 3.5 (the creator's modal per-run line), each cap
  at most 80 % of it; `caps.item_ceiling_usd` 4.8 (80 % of the owner's $6.00) must hold for smoke + run + chain + `item_spent_before_usd` 0.64
  (item 1 $0.53 + the first smoke $0.11). Function timeouts come from the caps: `floor(0.9 * (cap - cold_start_s * rate/3600) / rate * 3600)` =
  **441 s** (smoke), **1267 s** (run), **2147 s** (chain), CPU stage 996 s. Tests recompute all of it.
- `cold_start_s 60` and `margin_s 60` are **estimates** (the LTX bake-off measured about 34 s of overhead; the LTX launch uses 120/75).

## 6. What only the L3 smoke can measure (and what stops the run)

Measured at L3, nothing before: peak GPU memory (torch's `max_memory_allocated`/`reserved` from the wrapper AND nvidia-smi's peak), host
RSS peak and the cgroup peak, seconds to load and per clip, price per clip (settled from the wall seconds), whether the clip has **sound**
(ffprobe), the frame count and size of the output. If the model does not fit or the host RAM is too small: the worker writes the
failure and the numbers and stops. **No second GPU, no size change, no retry on a bigger box** (the brief).

The first smoke (window 166 s at `smoke_usd` 0.20) did not finish: the CLI builds the 22B transformer twice from the Volume (stage 1 and stage 2
with the IC-LoRA) and the deadline came during the second build. With 0.45 (window 441 s) it finished. See section 10.

## 7. Open questions (for the plan thread / the owner; nothing was decided on an assumption, OR-22)

| ID | Question | Why it matters |
|---|---|---|
| Q-L1 | **Decided 2026-11-20 09:14 UTC (coordinator, technical, cost low): smoke stays 9 frames at $0.20.** Was: smoke size: 9 frames inside $0.20 (measures loading, not the 241-frame peak) or a larger smoke cap? | A 9-frame pass cannot show whether 241 frames fit in 80 GB |
| Q-L2 | **Decided 2026-11-20 09:14 UTC (coordinator, follow the card): `--stage-2-ic-lora` stays ON.** Was: `--stage-2-ic-lora` on (the card's example) or off (the CLI default, less memory)? Now ON, not measured. | memory and time on stage 2 |
| Q-L3 | CH-01 (in-process model residency) is a rule of the protected LTX launch; this worker runs one CLI process per clip, so every clip reloads the 22B + text encoder from the Volume. Accept, or build an in-process session later? | each clip's price includes a full model load (unmeasured); a 2-clip chain pays it twice |
| Q-L4 | The film line (variant B) may push the prompt over the card's "one or two sentences": a warning today. Refuse instead? | prompt discipline vs the film-style test |
| Q-L5 | The split of the $2.00 line: smoke 0.20 + run 1.40 (my arithmetic; one launch capped at 1.40, the item's launches together at 1.6). | one failed run leaves 0.2..1.4 for a retry |
| Q-L6 | The IC-LoRA is gated: the owner's HF account must have accepted the licence for L2 to download it (not checked: the token lives in the Modal secret). | L2 fails cheaply if not |
| Q-L7 | Host RAM: 4 CPU / 32 GiB vs loading a 46 GB transformer (the LTX H100 launch uses 8 CPU / 96 GiB). An OOM kill is a stop-and-write. | UNMEASURED; a bigger box is a new card and a new CH-07 offer |
| Q-L8 | The hand-over default is `last` (as the LTX worker); `best_tail` is chosen per row by the continuation plan. Hop 3+ stays on the owner's word (CT-1, Q6). | chain quality vs cost |

## 8. Before the first paid rung

1. The owner's personal yes on a card for this plan (relayed by message id) and `EE_MODAL_GO` with this plan's hash.
2. A passing CH-07 `paid_offer/1` for `...modal_layout_jobs.py` entries `smoke` and `main` (the coordinator's thread builds it).
3. The OR-34 audit by Sonnet or Opus (never Haiku) over the changed files.
4. The ledger reservation (the worker does it before the call) and the night ledger line.
5. The Haiku low watchdog (OR-36), opened by the coordinator, told before the launch.
6. L1 (CPU, cents) and L2 (CPU, at most $0.10; needs Q-L6 true) in that order, then L3, then L4 only if L3 fits.
7. The packed batch on HF under its sha256 name; every output saved per clip with its SHA256 and read back (OR-33).

## 9. Rehearsal and tests (free, run 2026-11-20)

`python -m explainer_engine.training.pods.ltx.rehearse_layout_cpu <dir>` runs the real `body()` with the real wrapper as a child process,
real ffmpeg/ffprobe/PIL/imageio on `.mp4`-suffixed temp names, a fake `ltx_pipelines.ic_lora` (the real argument names, a clip of the
asked frame count) and a fake HF client. Tests cover: a normal two-clip chain saved after each clip and read back; sound recorded; the
smoke (one clip, no chain); a second attempt refused with nothing paid; the deadline in the middle of a clip (the CLI is ended, no half
clip anywhere); not enough time for the next clip; a failing CLI; HF down (`UPLOAD_UNVERIFIED`, files on disk and on the Volume);
unstaged weights; a wrong batch hash; a forbidden word in the container; a launch that is not the baked one. It found and fixed one real
bug (`rows()` collided on a chain row's own `hop`). It proves the plumbing and **nothing about LTX, memory, seconds or sound**.

## 10. Measured on the A100-80GB (2026-11-20, A100-80GB $2.9428/h, free Modal credit)

| Run | What | Result | Modal bill (settled from wall s) |
|---|---|---|---|
| `2f7890a82e23_54fd37dec98c` smoke | 9 frames, window 166 s | **PARTIAL**: deadline during the stage-2 transformer build, 106 s into the CLI; card peak 41.2 GiB | $0.1094 / 134 s |
| `3dea9204f241_a32ee2e2e617` smoke | 9 frames, window 441 s | **DONE**: 1280x704, 9 frames, sound yes; CLI 158 s (almost all the two loads, stage-1 denoise 4 s); torch max allocated 39.44 GiB, reserved 40.69 GiB, card peak 41.2 GiB of 79.28; host RSS peak 45.35 GiB | $0.1471 / 180 s |
| `3dea9204f241_a32ee2e2e617` main (T1) | one 10 s clip, 241 frames, the T0b `am1` layout (5 camera views of 2 s) | **DONE**: 241 frames, sound yes; CLI 261.7 s (26.2 s per generated second); torch max allocated 42.95 GiB, reserved 49.88 GiB, card peak 50.4 GiB; host RSS peak 45.58 GiB | $0.2462 / 301 s |

HF: `explainer-engine/layout_route/out/<run_id>/<smoke|main>/` (clip, `.vram.json`, `.log`, `layout_record.json`, all read back with sha256).
Observation (one clip, not a verdict): the output followed the layout's cuts, obstacle positions and the figure's place; the look is an
illustration, and a figure was smeared mid-clip. Host RSS above the 32 GiB container figure is mapped file pages, no kill happened.

