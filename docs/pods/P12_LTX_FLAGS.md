# P12 LTX flags and modules, checked at Lightricks/LTX-2@e98f6d9

Source: the files passed for WP-1a and WP-1a2, a verbatim copy of Lightricks/LTX-2 at commit
`e98f6d927d83c92ef2be6aec76c8440b19306e39`, kept in `jobs/ltx2_src/`:

| short name | path at e98f6d9 |
| --- | --- |
| `args.py` | `packages/ltx-pipelines/src/ltx_pipelines/utils/args.py` |
| `a2vid_two_stage.py` | `packages/ltx-pipelines/src/ltx_pipelines/a2vid_two_stage.py` |
| `ic_lora.py` | `packages/ltx-pipelines/src/ltx_pipelines/ic_lora.py` |
| `distilled.py` | `packages/ltx-pipelines/src/ltx_pipelines/distilled.py` |
| `constants.py` | `packages/ltx-pipelines/src/ltx_pipelines/utils/constants.py` |
| `listing.txt` | every file under `packages/ltx-pipelines/src` |
| `README.md`, `pyproject.toml` | `packages/ltx-pipelines/` |

Line numbers are those of the copies in `jobs/ltx2_src/`. Nothing below comes from memory. A value not found in these files
is marked **absent at e98f6d9**, which means it is not in the passed text. It does not mean the repo lacks it.

## FLAGS (`explainer_engine/training/pods/p12/p12c_ltx.py`)

| key | value | file:line | how it is called (`_common()` / `cmd_*`) |
| --- | --- | --- | --- |
| image | `--image` | args.py:1003 (ImageAction args.py:189) | `PATH 0 1.0`: 3 values, binding `auto` (frame 0 replaces the latent) |
| prompt | `--prompt` | args.py:813 (required, args.py:815) | the prompt text |
| width | `--width` | args.py:990 | int |
| height | `--height` | args.py:984 | int |
| num_frames | `--num-frames` | args.py:966 (8k+1); args.py:940 when `supports_auto_duration=True` (distilled, default `None`) | left out for AV (`frames=False`) |
| frame_rate | `--frame-rate` | args.py:997 | float |
| seed | `--seed` | args.py:759 | int |
| output | `--output-path` | args.py:819 (required, args.py:821) | mp4 path |
| transformer | `--transformer-path` | args.py:710 | split layout; args.py:611-622 accepts it in place of a checkpoint path |
| text_encoder | `--text-encoder-path` | args.py:720 | split single-file Gemma TE |
| video_vae | `--video-vae-path` | args.py:726 | was `None`, now set |
| audio_vae | `--audio-vae-path` | args.py:737 | was `None`, now set; all three parsers below call `add_model_args` with `audio_vae=True` |
| upsampler | `--spatial-upsampler-path` | args.py:1559 (2-stage, required :1561), args.py:1608 (2-stage distilled, required :1610) | path |
| distilled_lora | `--distilled-lora` | args.py:1543 (LoraAction, required :1548) | AV only: path, default strength |
| audio | `--audio-path` | a2vid_two_stage.py:540 (required :542) | wav path |
| audio_max | `--audio-max-duration` | a2vid_two_stage.py:552 | seconds; cannot be combined with `--num-frames` (a2vid_two_stage.py:525) |
| video_cond | `--video-conditioning` | ic_lora.py:820 (nargs=2 :822, required :824) | `CLAY 1.0` |
| lora | `--lora` | args.py:826 (LoraAction args.py:243) | Layout LoRA path, default strength 1.0 (constants.py `DEFAULT_LORA_STRENGTH`) |
| stage2_ic | `--stage-2-ic-lora` | ic_lora.py:855 (store_true :856) | no value |
| fp8 | `--quantization=fp8-cast` | args.py:886; value from its help text args.py:891, :896 | see below |

No FLAGS value is absent at e98f6d9. WP-1a2 added no FLAGS entry: `ltx_pipelines.distilled` accepts every flag that
`cmd_ltx_i2v` and `_common()` build (see the MODULES section).

**fp8.** `_common()` calls `_flag(cmd, "fp8")` with no value, but `--quantization` needs one. So the flag is stored as the single
argparse token `--quantization=fp8-cast`, which argparse accepts for long options. `_common()` is unchanged.
`_resolve_quantization` (args.py:410) needs a checkpoint or `--transformer-path` (args.py:427). Every `cmd_*` passes
`--transformer-path`. UNVERIFIED: `QUANTIZATION_POLICIES` comes from `QuantizationKind` (args.py:407,
`utils/quantization_factory.py`), and that file was not passed. `fp8-cast` is confirmed only by the help text.

**VAE.** `--video-vae-path` and `--audio-vae-path` are declared by `add_model_args` (args.py:649). `ic_lora` and `distilled`
(`default_2_stage_distilled_arg_parser`, args.py:1590 → `new_video_gen_arg_parser` → `basic_arg_parser`) and `a2vid_two_stage`
(`default_2_stage_arg_parser`, args.py:1525) all reach it with the defaults, so both flags are accepted. UNVERIFIED: whether split
mode needs every split file is decided by `model_paths_from_namespace` (`utils/model_paths.py`, called at args.py:444), which was
not passed. The `add_model_args` docstring says `--gemma-root` is required only in monolith mode.

## MODULES

| key | value | file:line |
| --- | --- | --- |
| ltx_i2v | `ltx_pipelines.distilled` | listing.txt:19; distilled.py:510 `main()`, :512 `resolve_cli_params(distilled=True)`, :516 parser |
| ltx_ic | `ltx_pipelines.ic_lora` | ic_lora.py:813 `main()`, :815 `resolve_cli_params(distilled=True)`, :817 parser |
| ltx_a2v | `ltx_pipelines.a2vid_two_stage` | a2vid_two_stage.py:596 `main()`, :598 `resolve_cli_params()`, :599 parser |

No MODULES value is a placeholder. `run()` skips a stage `(module unverified)` only if its kind has no entry in `MODULES`.

**ltx_i2v (L1/L3).** `packages/ltx-pipelines/src/ltx_pipelines/distilled.py` is in listing.txt, so the module is
`ltx_pipelines.distilled`. It defines `DistilledPipeline` (distilled.py:161), which README.md:12 and :33 name: two-stage
distilled, half resolution in stage 1, then 2x upsampling and refinement (docstring distilled.py:162-166). It works with
`cmd_ltx_i2v` because:

- **Image conditioning:** `main()` passes `images=args.images` (distilled.py:542). `args.images` is the `dest` of `--image`
  (args.py:1003, ImageAction args.py:189). The pipeline loads the images with `ImageConditioner.load_conditionings` and uses them
  in every chunk (`_video_conditionings`).
- **Parser:** `default_2_stage_distilled_arg_parser(params=params, supports_auto_duration=True)` (distilled.py:516), wrapped by
  `add_generated_keyframes_arg`, `add_keyframe_decode_arg` and `add_chunk_layout_args`. Their flags are optional
  (`--num-generated-keyframes` default 0, `--decode-with-keyframes` store_true, chunk flags default `None` →
  `chunk_config_from_args` returns `None`, one window).
- **Required flags:** `--prompt`, `--output-path` and `--spatial-upsampler-path` (args.py:1608) are all in `_common()`. There is
  no `--distilled-lora`, and `cmd_ltx_i2v` passes none.
- **Checkpoint:** `resolve_cli_params(distilled=True)` (distilled.py:512) → `detect_checkpoint_path` accepts
  `--transformer-path` when `--distilled-checkpoint-path` is missing. `cmd_ltx_i2v` passes `--transformer-path`.
- **Quantization:** `quantization=args.quantization` (distilled.py:527). `_resolve_quantization` reads `transformer_path`.
- **Frames:** with `supports_auto_duration=True`, `--num-frames` defaults to `None` (args.py:940). Then DurationHead predicts the
  length (`require_num_frames_source`, distilled.py:264). `_common()` always passes `--num-frames` (`frames=True` for i2v), so an
  explicit count wins (`_resolve_num_frames`). No `--duration-head-path` is needed. UNVERIFIED:
  `DurationPredictor.from_checkpoint(None)` (distilled.py:237-238) returning `None` is taken from the comment at
  distilled.py:235-236; `utils/blocks/duration_predictor.py` was not passed.
- **Other flags:** `--seed`, `--width`, `--height` and `--frame-rate` come from `new_video_gen_arg_parser` / `basic_arg_parser`.
  `--text-encoder-path`, `--video-vae-path` and `--audio-vae-path` come from `add_model_args` with defaults (the pipeline loads
  the audio VAE, distilled.py:230).

The two-stage dev pipeline (`ltx_pipelines.ti2vid_two_stages`, README.md:24) is not used for i2v.

## Install (`p12b.sh`, LTX line)

- README.md:21 gives `uv sync --frozen` at the repo root. That builds a separate `.venv`, and `sys.executable` in
  `p12c_ltx.py` would not see it, so it is not used.
- pyproject.toml:7 makes `ltx-core` a dependency. It is the sibling package `packages/ltx-core` (README.md:5, :53).
- pyproject.toml:19-20 sets the build backend to `uv_build`.
- Method used: `pip install -q -e packages/ltx-core -e packages/ltx-pipelines` in one call, so pip takes `ltx-core` from the
  checkout instead of PyPI.
- UNVERIFIED: `packages/ltx-core/pyproject.toml` was not read (its backend, and whether it re-pins torch).
