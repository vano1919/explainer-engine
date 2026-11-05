# Runbook: free Blender renders on the creator's Mac

How to run Ink Chronicle review renders on the M4 Pro Mac (D-113, ICG-3): style sheets, review clips and benchmark preflight, free and local. Paid work stays cloud-first. CI stays the unattended gate. Long renders follow RULE-R1 (`CLAUDE.md`, `docs/PRODUCTION_RULES.md` section 3).

Measured 2026-11-05 on Apple M4 Pro, 24 GB, macOS 27.2.

## Install once

1. Blender: download the `macos-arm64` archive named in `config/cloud_pins.json` (`blender`), check its sha256 against that file, and copy `Blender.app` to `/Applications`. `explainer_engine/blender/project.py` installs Linux archives only; on macOS `resolve` checks a hand-installed Blender against the pin. The app is about 907 MB.

   ```sh
   shasum -a 256 blender-5.2.3-macos-arm64.dmg
   python -m explainer_engine.blender.project resolve --binary /Applications/Blender.app/Contents/MacOS/Blender
   ```

2. Python 3.12 in a venv outside the checkout, with what CI installs:

   ```sh
   uv venv --python 3.12 ../ink_render/.venv
   uv pip install --python ../ink_render/.venv/bin/python "jsonschema==4.26.0" "pillow>=10.0" "numpy>=2.0" pyyaml imageio-ffmpeg
   ```

3. ffmpeg without Homebrew: link the binary of `imageio-ffmpeg` into the venv, so `shutil.which("ffmpeg")` finds it with the venv on `PATH`.

   ```sh
   ln -s "$(../ink_render/.venv/bin/python -c 'import imageio_ffmpeg as f; print(f.get_ffmpeg_exe())')" ../ink_render/.venv/bin/ffmpeg
   ```

4. If `git` says the Xcode licence is not agreed, either accept it (`sudo xcodebuild -license`, the creator's step) or use the Command Line Tools for the session:

   ```sh
   export DEVELOPER_DIR=/Library/Developer/CommandLineTools
   ```

## Run

From the repository root, with the venv on `PATH`, on a branch that has the code (`style_sheets.py` and its `clips` command came with ICW-05b):

```sh
B=/Applications/Blender.app/Contents/MacOS/Blender
python -m explainer_engine.blender.render smoke --out OUT/smoke --binary $B
python -m explainer_engine.blender.style_sheets fetch
python -m explainer_engine.blender.style_sheets render --out OUT/sheets --binary $B --variants B --scenes dialogue_cu
python -m explainer_engine.blender.style_sheets clips --out OUT/clips --frames 4 --scale 0.5 --binary $B
python -m explainer_engine.blender.style_sheets clips --out OUT/clips --binary $B
```

Keep `OUT` outside the repository. Frames are written twice, to the work folder and to the local stand-in vault: 12 clips of 48 frames at 1440p took about 3.5 GB. Commit no binaries.

## Long renders (RULE-R1)

A render over about 10 minutes runs as a tracked background task of the session, never a detached process. The ICW-04 adapter (`explainer_engine/blender/render.py`) writes frames in chunks with a checkpoint, so running the same command again continues from the last committed frame. Keep the session's wake-up timer running, as RULE-R1 asks.

## Measured speeds

All at 2560x1440, EEVEE on Metal (`gpu_backend` METAL), 16 samples, stand-in figures only. A scene with real characters will be slower; that has not been measured.

| Render | Seconds per frame |
|---|---|
| Smoke, Workbench, 320x180 | 0.13 |
| Smoke, EEVEE, 320x180 | 0.39 |
| Style sheet, first frame after a cold start (shader compile), `dialogue_cu` / `battle_wide` | 3.28 / 1.34 |
| Clip, no shadows, steady, `dialogue_cu` / `battle_wide` | 0.33 / 0.53 |
| Clip, cast shadows, steady, `dialogue_cu` / `battle_wide` | 0.54 / 0.73 |
| Style sheet variant S (Cycles-safe, on the CPU), `dialogue_cu` | 2.32 |

Eight clips of 48 frames took 3 min 57 s in all, including MP4 encoding. Heat under a run of several hours has not been tested, and these short runs say nothing about it.

## Known limits

- `device` in the render manifest says `cpu` on the Mac, because `project.py` knows only NVIDIA cards. EEVEE still runs on the GPU; read `gpu_backend` in `bpy_report.json`.
- `apply_settings` in `bpy/render_shot.py` tries only OPTIX and CUDA for a Cycles GPU job, so `device gpu` is refused here and Cycles runs on the CPU.
- At efbcc17 `style_sheets.mp4()` does not set the colour matrix: ffmpeg writes BT.601 values with no tag, and HD players read them as BT.709, so colours shift (measured mean green error 3.15 levels on `battle_wide_B_match`, 0.47 after the fix). Until the code is fixed, make review copies for colour decisions from the frames with:

   ```sh
   ffmpeg -framerate 24 -start_number 0 -i frames/frame_%06d.png \
     -vf "scale=in_range=pc:out_range=tv:out_color_matrix=bt709:flags=accurate_rnd+full_chroma_int,format=yuv420p" \
     -c:v libx264 -preset slow -crf 16 -colorspace bt709 -color_primaries bt709 -color_trc iec61966-2-1 -color_range tv \
     -movflags +faststart clip.mp4
   ```

- This Mac has no GitHub push credentials, no `gh` and no Hugging Face token: results leave through the project's files, and PRs are opened elsewhere unless the creator signs in here.
