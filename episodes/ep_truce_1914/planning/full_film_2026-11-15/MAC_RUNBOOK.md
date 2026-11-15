# Truce 1914 full film: how to run it on the Mac (M4 Pro, 24 GB)

The render starts only after the creator's OK on SHOT_PLAN.md. Every step is free: no paid call and no Modal.
Modal is the fallback only. It needs its own price card and his word first.

## 0. Inputs
- Code and data: branch `claude/project-thread-o239rq` (PR #193). It is based on `argon/plan-steps-1-2` @ 09232ca.
  Do NOT merge the Argon loop's later commits into this run unless the creator says so. The run must be reproducible.
- `inputs_manifest.json` (this folder) lists every input with its HF URL:
  - 79 pictures with their SHA-256 (from final_scene_frames_A_v5). S08_SH003_start is overridden to S01_SH001_start.
  - 56 LTX clips (the accepted takes, including R3 for S06_SH009, S07_SH005 and S07_SH008).
  - 72 ElevenLabs reads.
  - The clock: narration.wav, scribe words, timing.json and line_reads.json.
  - The two sound libraries.
  HF needs the token (private dataset). Verify every SHA-256 after download.
- Place the files in the episode folder the way `episode/run.py` expects them:
  - pictures go where `stage_pictures` finds them, and `production/pictures.json` is written;
  - the read and the transcript go under `audio/` (READ_REL / TRANSCRIPT_REL in run.py);
  - the LTX clips go where the video lane ingest reads them.
  Check each path in the code before you copy (Blueprint Lock 5).

## 1. Environment
- Python 3.12/3.13 venv, `pip install -r requirements.txt`, ffmpeg.
- SAM 2.1, Depth-Anything V2 and LaMa on MPS where they support it, CPU otherwise.
- Run `pytest -q tests/unit/test_v43_episode_contract.py tests/unit/test_task2_step2b_vertical_slice.py` first. Both must pass.

## 2. One-shot benchmark
Render S02_SH008, the hardest still (10.96 s, split in two). Record the wall time, the speed per frame and the peak memory.
Send the timing to the coordinator. Pick the parallelism (3-4 shots at once) from the measured memory.

## 3. Direction, checked BEFORE any render (the creator's rule)
1. Run the direction stage only, for the 23 still_25d shots and the 5 maps
   (`stage_direction`; the runner splits stills longer than 5 s).
2. For every shot, open the picture, the narration line and SHOT_PLAN.md, and compare them with
   `production/direction/<shot>.json`:
   - camera target and the word it lands on;
   - every planned living effect is present, at a visible strength;
   - nothing on the "never moves" list moves;
   - the keep-in-frame boxes cover people and boots;
   - falling snow only where the plan allows it;
   - the sound events sit at their source.
3. Where the file differs from the plan, edit the direction JSON. That is a data edit. Never edit code.
   Log any code cause in `docs/wip/argon_2026-11-14/INCIDENT_JOURNAL_argon_loop.md`.
4. The 6 hand-made directions (`docs/wip/argon_2026-11-14/s7_regenerated_directions/`) are the starting point for
   S01_SH001, S02_SH008, S05_SH016, S05_SH020, S06_SH001 and S08_SH002. Apply the plan's FIX notes on top of them
   (S02_SH008 boots, S05_SH020 a visible pan, S08_SH002 snow only behind the hands).

## 4. Clips (G7), long render rules (RULE-R1)
- Run it as a tracked background task, in chunks, with a wake-up timer.
- After each still or map: frames 0, middle and end, plus a crop where a small effect lives (steam, breath, candle).
- Frame 0 must equal the picture.
- An effect that the plan names but that is invisible is a FAIL. Re-run it once at a higher strength (data).
  If it is still invisible, log it and go on.
- The LTX clips are not re-rendered. They are ingested with `edit_points.json`: the trims, the clip-audio levels,
  the added second shot in S07_SH006, and the J-cut S07_SH004 -> S07_SH005.

## 5. Sound (G8)
- Narrator: narration.wav (ElevenLabs, 11-13).
- Dialogue: the LTX clip voices.
- Beds per place, and spot sounds panned to their source. Follow SHOT_PLAN.md "Sound staging", the shot `snd` lines and
  the music list.
- Library: `--sound-library` pointing at the merged library (sound_library_2026-11-13 + realism_w1).
- Known trap (journal 183): the master's mix comes out near -25 LUFS. Run `qa/targets.normalise_file` on `audio/stems/mix.wav`
  before G9, and check that the master lands on the targets in `qa/targets.py`.

## 6. Assembly (G9) and QA (G10)
- Write `editing/transition_plan.json` from the plan's "Out" lines. The script's `transition_out` field is not read.
  The dips to black are at: S01_SH005, S02_SH009, S03_SH010, S04_SH015, S05_SH021, S06_SH012, S07_SH008, S08_SH003,
  and the end card fade.
- Draw the chunks with `--chunks A:B`, then join them once. Master 2560x1440 at 24 fps (BP-167).
- End card S08_SH004: the text "For one day, they remembered they were human." fades in at 0.8 s and out at 5.2 s.
- Eye and ear check of every adjacent clip pair (the continuity rule), with frame strips.

## 7. Delivery
- Upload the master mp4, the frame strips and the QA reports to HF
  `explainer-engine/demo_truce_1914/full_film_2026-11-15/render/`, with direct resolve links.
- Nothing is uploaded to YouTube without the creator's recorded OK.
