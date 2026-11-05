# Fable plan — combined P12 pod (measurement + Qwen + LTX in one run)

## 1. DECISION

**Confirmed from the first pass: LTX-2.5 22B is the video model.** 0.9.8-13B-distilled serves none of L2 (Layout IC LoRA is 2.5-22B), AV (no audio path), or D-90. Evidence unchanged (D-85, D-90, `OLD_HISTORY.md:1135/1417`, PAID_TESTS_PLAN §3.4b).

**Changed from the first pass:** the creator's new word (one combined pod because no cheap-card stock, with manual stop after any stage) overrides my "separate P12c pod" recommendation on the *pod shape*, not on the model. So the LTX stages go into this pod's script as a **second process** after the Qwen process exits, in the order the creator gave (L1, L3, L2, AV), gated so that nothing LTX is loaded unless the Qwen stages are done or skipped and the creator has not stopped the pod.

**Consequence the plan cannot avoid:** `config/cloud_pins.json models.video_ltx` and `p12b.json video` must be re-pinned from 0.9.8 to LTX-2.5 — this is a pin PR (CR-18) and it contradicts the creator's 2026-10-31 brief that named 0.9.8. **The creator must say yes before the coder writes** (OPEN QUESTION 1 in §5). Without it the combined pod is Qwen-only (today's code) and the background fetch should be removed.

**UNVERIFIED (must be read by the coder before writing any LTX call, exactly as listed in the first pass items 1-10):** every `ltx_pipelines` module name, flag name, fp8 flag, the `Registry` class, the distilled I2V entry point, resolution assertions; the current `main` sha of `Lightricks/LTX-2.5` and of the Layout LoRA and the LoRA filename; whether `vano1919`'s token passes the gates; a2vid on 48 GB (no file records a run). Also UNVERIFIED by me: `p12b_measure.sh` contents (not read), `cloud/runpod.py` lines 1740-1880 beyond the grep (the `--measure` path and how `--setup-min/--work-min` reach `rp01`), the wrapper's `ee_needs_check` and whether the wrapper exposes any creator-stop file (no grep hit for a stop word — see §2.3).

## 2. COMBINED RUN DESIGN

### 2.1 Stage order and what each writes

One script `p12b.sh` → `p12b.py` (process 1, Qwen) → `p12c_ltx.py` (process 2, LTX; new file, same folder, sha256-pinned in `p12b.sh` like the other two). All outputs under `$EE_OUT`, weights under `/workspace/models`.

| # | Stage | Essential | Writes (under `$EE_OUT`) | Stage-end marker |
|---|---|---|---|---|
| 0 | **M** setup measurement (in `p12b.sh` + `p12b.py` download phase): boot facts, pull/boot seconds, Qwen 32 GB download seconds and MB/s, with `HF_XET_HIGH_PERFORMANCE=1` | yes | `t.jsonl` events `boot`, `download_start/end` (exist), **new** `measure.json` {`boot_s`, `qwen_dl_bytes`, `qwen_dl_s`, `mb_s`, `xet`: true} | `stages.txt`: `done M setup=<min> mb_s=<x>` |
| 1 | Q1 | yes | `mva/<person>/<deg>_s0.8.png` + sidecar (exists) | `done Q1` |
| 2 | Q2 | no | as Q1 (exists) | `done Q2` / `skipped Q2 (projection)` |
| 3 | Q3 | no | as Q1 (exists) | `done Q3` / `skipped Q3 (...)` |
| — | Qwen process exits; `p12b.sh` checks the LTX weights' sha256 and the stop word, then starts process 2 | | `stages.txt`: `ltx_weights ok` or `ltx_weights missing (skipped L*)` | |
| 4 | L1 plain I2V, 3 shots (tent s0, s3, s4) | yes | `ltx/<shot>_i2v.mp4` + `.json` sidecar | `done L1` |
| 5 | L3 plain I2V, 3 shots (tent s1, s2, ship s2) | no | same | `done L3` / `skipped L3` |
| 6 | L2 Layout IC, the L1 shots | yes | `ltx/<shot>_layout.mp4` + sidecar, `ltx/clay/<shot>.mp4` copied | `done L2` |
| 7 | AV, 2 audio-driven clips | yes (per §3.4b) but **last and OOM-tolerant** | `av/av{1,2}.mp4` + sidecar | `done AV` / `failed AV (oom)` |

Drop order of the projection: **Q3, L3, Q2** (PAID_TESTS_PLAN §3.5 wording, which already includes L3). Essential stages Q1, L1, L2, AV never skipped by projection; an essential stage that would pass the deadline ends by the wrapper's CAPPED path (§3.5, unchanged).

**L2 and AV preconditions not in the repo (R1(a) reasons):** P6 numpy playblasts (`code/p12/clay/<shot>.mp4`) and the two ElevenLabs takes (`code/p12/audio/av{1,2}.wav`) must exist on HF before create. `p12c_ltx.py` checks each input's presence and sha256 (from `p12b.json`) and writes `skipped L2 (no clay)` / `skipped AV (no take)` instead of failing. **UNVERIFIED that the playblasts or takes exist** — the session must list `code/p12/` on HF before create.

### 2.2 Projection across two processes

Process 1 does not know LTX speeds. Rule: before starting an optional Qwen stage, process 1 adds to "remaining essential" a **fixed LTX reserve** from `p12b.json` `ltx.reserve_min` (plan-stated: loads 12 + L1 8 + L2 11 + AV 30 wall-min on A40 ≈ **61 min**, from §3.6 A40 numbers ×SPEED 2.0 — it is a plan number, flagged `"measured": false`). Process 2 uses its own first-unit timing per pipeline kind (`first_unit_s["L1"]` for L3). This keeps the §3.5 formula unchanged: `now + est(stage) + est(remaining essential incl. ltx_reserve) + 15 min ≤ EE_DEADLINE`.

### 2.3 Creator stop after any stage

No stop word exists in the wrapper (grep found no `EE_STOP`/stop-word in `runpod.py`; `pod_wrapper.sh` not read — **UNVERIFIED**). Do **not** invent a wrapper feature. Two mechanisms the creator already has:

1. **Hard stop:** `python -m explainer_engine.cloud.runpod stop <pod>` (exists, used in §2.2 of the plan). Outputs are on HF because the wrapper uploads `$EE_OUT` every 300 s; everything already written is kept. This is what "stop by hand after any stage" means today.
2. **Soft skip (new, in the job script only):** before each stage, `p12b.py`/`p12c_ltx.py` call `hf_hub_download('vano1919/tmr-artifacts','runs/p12b/control/stop_after.txt', repo_type='dataset')` with a 20 s timeout; the file holds one of `Q1 Q2 Q3 L1 L3 L2 AV`. Once that stage is `done`, the script writes `stages.txt: creator_stop after <X>` and exits 0 → `DONE`, self-stop. The creator writes the file with the HF web UI or `huggingface-cli upload`. Missing file or network error = no stop (logged `control_check_failed`, never raises). `huggingface_hub.hf_hub_download` exists in the pinned 1.33.0 (used already in `p12b.py`); the `etag_timeout`/timeout kwarg name is **UNVERIFIED** — coder reads `huggingface_hub` 1.33.0 `file_download.py` or wraps the call in a thread with `join(20)`.

The creator sees the stage ends in `runs/p12b/stages.txt` (uploaded every 300 s) and in `progress.txt`; the beat line itself is the wrapper's and is not changed.

### 2.4 RP-01 and money — does the combined pod pass?

Numbers (plan sources; A40 SPEED 2.0 from §3.6):

- Setup: measured 67 min (25 boot + 42 download). With hf_xet: the creator's target 22 min, **NOT measured**. Honest `--setup-min` must be the measured 67 unless the measurement stage is what proves otherwise — but RP-01 is checked at create, before the measurement. Note the LTX download (≈ 119 GB with dev transformer, §3.1+§3.4b) runs in the background during Q1-Q3 and so is not setup; at 12.6 MB/s it takes **≈ 157 min**, longer than Q1-Q3 (≈ 92 A40-min), so the LTX process waits ≈ 65 min idle unless xet is faster. This wait counts against the deadline and the cap.
- Work (A40-min): Q1 48 + Q2 32 + Q3 48 (=92+36… use plan: 46 A100-min = 92 A40-min for Q1-Q3) + LTX plain 16 + IC 22 + AV 24-40 + loads/builds ≈ 22 wall = **≈ 176-192 min**.
- RP-01: 176 ≥ 3 × 67 = 201? **No, at the measured setup it fails (176 < 201).** At `--setup-min 59` or less it passes. With the creator's 22-min target it passes trivially.
- Time: 67 setup + 65 idle wait (if download is 12.6 MB/s) + 180 work = 5.2 h > 3.5 h cap → at the measured rate **the combined pod does not fit**; the projection would drop Q3, L3, Q2 and the wrapper's CAPPED path would still end it inside AV. At the xet target (22 min setup, download ≈ 4× faster) it is ≈ 0.4 + 3.0 = 3.4 h ≈ $2.05 on A40 — inside $2.40 with no slack.

**Honest conclusion for §2:** RP-01 and the 3.5 h cap pass only on the unmeasured xet assumption. Since the creator accepts manual stop after any stage, the pod is run as **"measurement first"**: `--setup-min` must be a plan-stated number, not a guess (OR-22). I state it as **45 min** = the midpoint the plan thread can defend (25 boot measured + 20 min download if xet gives ≥ 27 MB/s on 32 GB) — flagged in `p12b.json plan.note` as a target, and the stage-M record on HF (`measure.json`) is what the creator reads at minute ~45 to decide to continue or stop. `--work-min 176`. RP-01: 176 ≥ 135 ✓.

### 2.5 `runpod create` flags (exact; from R1(d), amended)

```
python -m explainer_engine.cloud.runpod create --yes --ledger jobs/p12b/run.json --test p12b_two_runs \
 --script explainer_engine/training/pods/p12/p12b.sh \
 --script-url https://huggingface.co/datasets/vano1919/tmr-artifacts/resolve/main/code/p12/p12b.sh \
 --vram 48 --cloud <C> --only "NVIDIA RTX 6000 Ada Generation,NVIDIA A40,NVIDIA RTX A6000,NVIDIA L40S" \
 --ref-hours 1.5 --min-ram 64 --boot-minutes 25 --image aitoolkit --disk 260 --volume 0 \
 --setup-min 45 --work-min 176 --max-usd 2.40 --max-hours 3.5 --cuda-min 12.8 --name p12b
```
`<C>` = the cloud whose printed prices match §3.2 (R1(b) rule). `--disk 260` (plan §3.2 with AV weights, $0.036/h). `--datacenters` only if the session's `runpod cards` shows stock in named sites (flag exists, `runpod.py:1873`). `--cuda-min` value: `CUDA_VERSIONS[0]` is the default (`runpod.py:1816`); the exact accepted string is **UNVERIFIED** — the session runs `create` without it if refused. If preflight prints an RP-01 refusal, stop and report (R1(d)). `# stall-minutes: 25` (longest unit = an IC clip + load, §3.2).

Stop paths unchanged (§3.7). The creator's manual stop is additional.

## 3. FILE-BY-FILE CHANGE LIST

Order of work: A (pins, creator yes) → B (json) → C (p12b.py) → D (p12c_ltx.py) → E (p12b.sh) → F (tests) → G (docs). Commit the json/py first, then compute sha256 and paste into `p12b.sh`, then `runpod dryrun`.

### A. `config/cloud_pins.json` (protected: pin PR, needs creator's yes)
- `models.video_ltx`: `id` → `"Lightricks/LTX-2.5"`, `revision` → the HF `main` sha read by the session on commit day (**UNVERIFIED now**), `note` → "creator's yes 2026-11-01 (replaces the 2026-10-31 brief's 0.9.8); files listed in training/pods/p12/p12b.json ltx". Keep `sha256: null, params: null, smoke_verified: false`.
- Add `models.video_ltx_layout_lora`: `{id: "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render", revision: <sha>, file: <name>, gated: true}` — file name and sha UNVERIFIED.
- Add `git."Lightricks/LTX-2"`: `{url, sha: "e98f6d927d83c92ef2be6aec76c8440b19306e39", smoke_verified: false}` (§3.4b's commit).
- Leave `video_wan`, `keyframe`, `loras` untouched.

### B. `explainer_engine/training/pods/p12/p12b.json`
- Replace `video` block with `ltx`:
```json
"ltx": {
  "repo": "Lightricks/LTX-2.5", "revision": "<sha>", "local": "ltx",
  "files": ["diffusion_models/ltx-2.5-22b-distilled-transformer-bf16.safetensors",
            "text_encoders/gemma4-12b-with-proj-ltx-2.5-bf16.safetensors",
            "vae/ltx-2.5-video-vae-bf16.safetensors", "vae/ltx-2.5-audio-vae-bf16.safetensors",
            "latent_upscale_models/ltx-2.5-latent-spatial-upscaler-x2-bf16-1.0.safetensors"],
  "av_files": ["diffusion_models/ltx-2.5-22b-dev-transformer-bf16.safetensors",
               "loras/ltx-2.5-22b-distilled-lora-450-bf16.safetensors"],
  "layout_lora": {"repo": "Lightricks/LTX-2.5-22b-IC-LoRA-Layout-To-Render", "revision": "<sha>", "file": "<name>"},
  "code": {"url": "https://github.com/Lightricks/LTX-2", "sha": "e98f6d927d83c92ef2be6aec76c8440b19306e39", "package": "packages/ltx-pipelines"},
  "expected_gb": 119, "margin_gb": 20, "reserve_min": 61, "reserve_measured": false,
  "render": {"width": 1920, "height": 1088, "frames": 121, "fps": 24, "seed": 11,
             "stage1": {"width": 960, "height": 544, "steps": 8}, "stage2_steps": 3, "cfg": 1.0},
  "shots": {"L1": ["tent_s0","tent_s3","tent_s4"], "L3": ["tent_s1","tent_s2","ship_s2"], "L2": ["tent_s0","tent_s3","tent_s4"]},
  "keyframes": {"tent_s0": "lora_plan_2026-10-26/train_xworld_v2/p2s/out/p2s/tent_11_s0.png",
                "tent_s1": ".../loop/round_3b/out/loop/X_g_n_0_0+dpl/tent_11_s1.png", "...": "s2,s3,s4,ship_11_s2 per §3.4"},
  "prompts": {"<shot>": "<P6 compiler output, committed>"},
  "clay": {"repo": "vano1919/tmr-artifacts", "dir": "code/p12/clay", "sha256": {"tent_s0": "<64hex>", "...": ""}},
  "av": {"takes": {"av1": {"path": "code/p12/audio/av1.wav", "sha256": "<64hex>", "voice_id": "<id>", "seconds": 0.0},
                   "av2": {"...": ""}},
         "images": {"av1": "keyframe:tent_s2", "av2": "q1:napoleon/front-right quarter view/0.8"},
         "mouth_box": {"av1": [x0,y0,x1,y1], "av2": [x0,y0,x1,y1]}}
}
```
Every `<...>` is filled by the session from HF/P6 outputs, never by the coder. Prompts: §3.4 says they come from P6's compiler — if P6's compiler is not merged (R1(a) says playblasts/compiler not in repo), the session fills them from `docs/SHOT_PROMPTS.md` rules and marks `"prompt_source": "hand, SHOT_PROMPTS.md"`.
- `stages`: add `L1` (order 4, essential true), `L3` (5, false), `L2` (6, true), `AV` (7, true) with `"kind": "ltx_i2v" | "ltx_ic" | "ltx_a2v"`, and add `"kind": "qwen_mva"` to Q1-Q3. `units_of` must handle kinds (below).
- `drop_order`: `["Q3","L3","Q2"]`.
- `stall_minutes`: 25. `control`: `{"repo": "vano1919/tmr-artifacts", "path": "runs/p12b/control/stop_after.txt"}`.
- `plan`: `fixed_setup_minutes 45, planned_work_minutes 176, price_per_hour_usd 0.59, hard_pod_usd 2.4, note: "45 = 25 boot measured + 20 download target with HF_XET_HIGH_PERFORMANCE, NOT measured (67 measured on 2026-10-31); stage M on this pod measures it"`.
- `outputs`: add `ltx`, `av`, `measure` paths.

### C. `p12b.py` (Qwen process) — changes only
- `units_of(stage)`: `if stage.get("kind","qwen_mva") != "qwen_mva": return len(stage["shots"])`.
- `estimate_s`: unchanged for Qwen kinds; for an LTX stage return `None` (process 1 never estimates them) — and `stage_may_start` gets a new keyword `extra_reserve_s=0.0` added to `rest`; `run()` passes `cfg["ltx"]["reserve_min"]*60`. The loop in `run()` iterates only over stages whose kind is `qwen_mva` (`ordered(stages, kind="qwen_mva")`: add optional `kind` filter).
- Replace `start_video_download(log, cfg)` by `start_ltx_download(log, cfg)`: same thread shape, but downloads `files` (+ `av_files`, + layout LoRA via `hf_hub_download` with `token=os.environ.get("HF_TOKEN")`) with `hf_hub_download(repo, filename, revision, local_dir, token)` per file (not `snapshot_download`: the repo has far more than 119 GB), writing `ltx_download_file_end` per file and a final `ltx_download_end`; on exception per file → `ltx_download_failed` with the filename; on `HTTPError` 403 → event `gated_403`. The disk guard `video_download_fits` → `ltx_download_fits` with `cfg["ltx"]`. `hf_hub_download` signature (`repo_id, filename, *, revision, local_dir, token, repo_type`) is used already in this file for the vault — verified by existing use; `token=` kwarg **UNVERIFIED** in 1.33.0 (coder checks).
- New `write_measure(log, out)`: after the base download, write `$EE_OUT/measure.json` {`boot_s`: from `t.jsonl` `script_start` time minus `RUNPOD` create time if present in env else null, `qwen_dl_bytes`, `qwen_dl_s`, `mb_s`}; `stage_line("done M setup=... mb_s=...")`.
- New `creator_stop_after(cfg, log) -> str|None`: thread + `join(20)` around `hf_hub_download(control.repo, control.path, repo_type="dataset", local_dir=tmp, force_download=True)`; returns the stripped first token or None; never raises. Called after every `done <stage>`; on match → `stage_line(f"creator_stop after {name}")`, write `$EE_OUT/control/stopped_after.txt` = name, `return 0` (skips the wait loop; `p12b.sh` reads the file and skips process 2).
- At end: `write $EE_OUT/qwen_done.txt` with the Q1 front-right-quarter path for AV2 (`mva/napoleon/60_s0.8.png`); the wait loop for the download stays but its message says `waiting for the LTX weights`.
- Keep `GateUp`, `merge_lora` calls unchanged (a test counts them).

### D. New `p12c_ltx.py` (process 2; structure mirrors `p12b.py`: `Log`, `stage_may_start` imported from `p12b.py` via `importlib` of the sibling file)
- `main()`: reads `p12b.json`, `EE_OUT`, `EE_DEADLINE`; `stopped_after.txt` present → exit 0 immediately.
- `verify_weights(cfg) -> list[str]` missing/mismatched files (size check against the sizes in json where given; sha256 is too slow for 42 GB — size + a `safetensors` header parse); missing essential set → `stage_line("skipped L1 L2 L3 AV (weights missing)")`, exit 0 (not a FAIL: the Qwen results stand).
- `prepare_inputs(cfg, out)`: keyframe centre-crop 2560×1408 → 1.765:1 → resize 1920×1088 (PIL); AV2 canvas: Q1 picture placed centred on 1920×1088 white; clay download with sha256 check; take download with sha256 check.
- `run_stage(name, ...)`: per kind builds the **CLI command** (subprocess, `timeout` = `stall_minutes*60 - 60`) — the CLI path is the plan's stated fallback (§3.4 "fallback is the CLI per clip") and avoids inventing the Python API/`Registry` (UNVERIFIED). Commands, every flag UNVERIFIED until the coder reads `Lightricks/LTX-2@e98f6d9`:
  - `ltx_i2v`: `python -m ltx_pipelines.<distilled_i2v_module> --image <png> 0 1.0 --prompt ... --width 1920 --height 1088 --num-frames 121 --frame-rate 24 --seed 11 --output-path ... ` + checkpoint/text-encoder/VAE/upsampler flags + fp8 flag.
  - `ltx_ic`: `python -m ltx_pipelines.ic_lora --video-conditioning <clay>.mp4 1.0 --lora <layout.safetensors> --stage-2-ic-lora --image <png> 0 1.0 ...`.
  - `ltx_a2v`: `python -m ltx_pipelines.a2vid_two_stage --transformer-path <dev> --distilled-lora <lora-450> --spatial-upsampler-path <x2> --audio-path <wav> --audio-max-duration <s> --image <png> 0 1.0 ...` (§3.4b).
  The coder writes each command as a function `cmd_<kind>(cfg, shot, paths) -> list[str]` with a module-level `FLAGS` dict so one place changes after verification; a test asserts the dict is the only source of flag strings.
- Error handling: non-zero rc or timeout → sidecar `{"rc", "stderr_tail"}`, `stage_line(f"failed {name}/{shot} rc={rc}")`, continue to next shot; `"CUDA out of memory"` in stderr → `oom: true`; AV OOM → `stage_line("failed AV (oom)")`, exit 0.
- Projection: `first_unit_s[name]` = first shot's seconds; L3 uses L1's; `stage_may_start` with `extra_reserve_s=0`.
- After every stage: `creator_stop_after` (imported from `p12b.py`).
- Sidecar per clip: `{stage, shot, kind, seed, width, height, frames, fps, steps, cmd (list), seconds, rc, inputs: {keyframe_sha256, clay_sha256|null, take_sha256|null, voice_id|null}, model_files: [...]}`. Audio check for AV: `ffprobe`/`ffmpeg -i out.mp4 -vn -f wav -` → sha256 compared with the take's (§3.4b pass criterion 1), recorded as `audio_sha_match`.

### E. `p12b.sh`
- Header: `# stall-minutes: 25`; comment lines updated (LTX-2.5, two processes).
- After the pinned pip line: `git clone -q https://github.com/Lightricks/LTX-2.git /workspace/LTX-2 && git -C /workspace/LTX-2 checkout -q e98f6d927d83c92ef2be6aec76c8440b19306e39 && pip install -q -e /workspace/LTX-2/packages/ltx-pipelines || { ev install_failed "\"step\":\"ltx\""; exit 1; }` — the install method of that package (uv/pyproject) is **UNVERIFIED**; coder reads its README at that commit. Must remain before the `DRY=1` gate (G9: every install before the gate, pinned, no `|| true`).
- Fetch three job files (`p12b.py`, `p12b.json`, `p12c_ltx.py`) and pin three sha256.
- After `python3 "$JOB/p12b.py"`: `rc=$?; [ $rc -ne 0 ] && exit $rc; [ -f "$EE_OUT/control/stopped_after.txt" ] && exit 0; python3 "$JOB/p12c_ltx.py"; exit $?`.
- Keep `HF_XET_HIGH_PERFORMANCE=1`, `ee_needs_check`, `# needs: none`.

### F. Tests
`tests/unit/test_p12b_pod_script.py` (exists; edit):
- `test_p12b_script_passes_the_dryrun_rules...`: change the `"ltx" not in py.lower()` and `cfg["video"]` asserts to: `"start_ltx_download" in py`, `"p12c_ltx.py" in t`, `R.stall_minutes_of_script(t) == 25`, all three sha256 in `t`, `"a2vid" not in p12b.py` (process 1 still runs no video), and the LTX-2 clone line is pinned to `e98f6d9…` and sits before `DRY`.
- `test_the_projection...`: add `extra_reserve_s` case: with reserve = 3660 s, Q2 no longer starts at `deadline-960-reserve`; `ordered(st, kind="qwen_mva") == ["Q1","Q2","Q3"]`, `ordered(st) == ["Q1","Q2","Q3","L1","L3","L2","AV"]`; `units_of` for L1 == 3, AV == 2.
- Rename video-download tests → `test_the_ltx_download_runs_per_file_in_a_background_thread_and_a_failure_does_not_stop_qwen` (fake `hf_hub_download` raising once; events `ltx_download_start`, `ltx_download_failed`), and the disk-guard test with `cfg["ltx"]`.
- New `test_creator_stop_after_reads_the_control_file_and_never_raises` (monkeypatched `hf_hub_download` returning a tmp file with `Q1`; and raising → None).
New `tests/unit/test_p12c_ltx.py`:
- `test_p12c_commands_come_only_from_the_flags_table`: AST scan — no string literal starting with `--` outside `FLAGS`.
- `test_p12c_skips_everything_when_qwen_was_stopped_by_the_creator` (tmp `stopped_after.txt` → `main()` returns 0, no subprocess; monkeypatch `subprocess.run` to raise if called).
- `test_p12c_skips_l_stages_when_weights_are_missing` (empty models dir → `stages.txt` has `skipped L1 L2 L3 AV`).
- `test_p12c_av_oom_is_recorded_and_the_script_exits_0` (fake `subprocess.run` rc=1 stderr "CUDA out of memory").
- `test_p12c_sidecar_has_every_field` (fake run → sidecar keys set).
- `test_p12c_drop_order_and_essentials` (`drop_order == ["Q3","L3","Q2"]`; L1, L2, AV essential).
`tests/unit/test_p12b_json.py` (exists; edit): `video` → `ltx` (repo `Lightricks/LTX-2.5`, revision HEX40, `code.sha` HEX40); `set(c["stages"]) == {"Q1","Q2","Q3","L1","L3","L2","AV"}`; `plan` test: `s <= 45 and 170 <= w <= 180`, `rp01(w, s) == []`, `(s+w)/60*0.59 <= 2.40` (= 2.17 ✓), `"NOT measured" in note`. Keep the `deferred_to_p12c` key removed (stages are now here); the "video_ltx agrees" test now compares `c["ltx"]["repo"]/["revision"]` with `models.video_ltx`.

### G. Docs
- `docs/PROGRESS.md`: one entry "2026-11-01 P12 combined pod: LTX-2.5 re-pinned (creator yes <time>), p12c_ltx.py added, p12b.sh two processes, stop_after control file, RP-01 numbers 45/176 (45 NOT measured)". 
- `PAID_TESTS_PLAN.md`: append **R3** (do not rewrite): combined pod, order, flags of §2.5, the RP-01 statement, the control file, "where R3 differs from R1/R2, R3 governs". 
- `docs/CLOUD_RUNBOOK.md`: one row under the pod protocol: "creator soft stop: `runs/<test>/control/stop_after.txt`" (new convention, job-script level, not the wrapper). 
- `config/spend_caps.json:24` stale `for` text — creator's file, not touched; note it in the report.
- Run `docs_lint` after.

## 4. CODER LIMITS

- **Max 9 files**: `cloud_pins.json` (only after the creator's yes; otherwise skip and say so), `p12b.json`, `p12b.py`, `p12c_ltx.py` (new), `p12b.sh`, `test_p12b_pod_script.py`, `test_p12b_json.py`, `test_p12c_ltx.py` (new), `PROGRESS.md` (+ R3 appendix of the plan: a 10th block allowed, text only).
- **Do not touch**: `config/spend_caps.json`, `cloud/runpod.py`, `cloud/batching.py`, `pod_wrapper.sh`, `p12a_*.sh`, `p12b_measure.sh`, `job_speeds.json`, any other test file, `docs/DECISIONS`.
- **Do not**: invent `ltx_pipelines` flags as facts — every flag goes in `FLAGS` with a comment `# UNVERIFIED until read at e98f6d9 <path:line>`; the session fills/validates. Do not change `GateUp`/merge call count. Do not put sha256 values into `p12b.sh` yourself — write `<SHA_P12B_PY>` placeholders; the session computes and pastes (then re-runs the sha test).
- **Output format**: one `=== FILE: <repo path> ===` block per file with the full file content (no diffs); for `PROGRESS.md` and the plan, a block containing only the appended text, headed `=== APPEND: <path> ===`.
- **Token budget**: `p12c_ltx.py` ≤ 350 lines; tests ≤ 120 lines each; no prose outside the blocks; total ≤ ~25 k output tokens. Write `p12b.json` once in full (it is the contract).

## 5. RISKS, SESSION COMMANDS, CREATOR DECISIONS

**Risks**
1. The pin flip contradicts the 2026-10-31 brief — blocked until the creator's yes.
2. Setup 45 min is unmeasured; if xet gives no gain, the pod reaches the 3.5 h cap inside L2/AV and $2.40 is spent for Qwen + partial LTX. Mitigation: the creator reads `measure.json`/`stages.txt` at ~45 min and stops if `mb_s` < 25.
3. 119 GB background download may not finish before the Qwen process ends → idle wait (counts in the deadline).
4. Gated repos (403) → LTX stages skipped, not failed; costs the Qwen time only.
5. a2vid dev transformer on 48 GB: OOM is caught; AV may yield nothing.
6. Every LTX flag is unverified until the coder reads the commit; a wrong flag = `failed <stage>` per shot, caught by the timeout, pod continues.
7. Playblasts/takes may not exist → L2/AV skipped (R1(a) reasons remain).

**Session, after the code arrives**
```
pytest tests/unit/test_p12b_pod_script.py tests/unit/test_p12b_json.py tests/unit/test_p12c_ltx.py tests/unit/test_cloud_stop_paths.py -q
python -m explainer_engine.cloud.dryrun / python -m explainer_engine.cloud.runpod dryrun --script explainer_engine/training/pods/p12/p12b.sh
sha256sum explainer_engine/training/pods/p12/p12b.py p12b.json p12c_ltx.py   # paste into p12b.sh, re-run tests + dryrun
python -m explainer_engine.tools.docs_lint   # (module name UNVERIFIED; use the project's docs_lint command)
huggingface-cli upload vano1919/tmr-artifacts explainer_engine/training/pods/p12/{p12b.sh,p12b.py,p12b.json,p12c_ltx.py} code/p12/ --repo-type dataset   # then compare sha256 (G9 step 3)
python -m explainer_engine.cloud.runpod check ; runpod balance ; runpod cards --vram 48 --cloud COMMUNITY --ref-hours 1.5 ; same with SECURE
ledger report jobs/p12b/run.json ; dispatch watchdog.yml ; then the create of §2.5
```
Before create: list `code/p12/clay/` and `code/p12/audio/` on HF; read the LTX-2.5 and Layout LoRA `main` shas and fill `p12b.json`; test the gate with a `HEAD` request using the token (a 403 here is free; on the pod it costs).

**Creator must decide (money/goal only)**
1. **Goal/pin:** yes to LTX-2.5 22B replacing the 0.9.8 pin of his 2026-10-31 brief? Without it: Qwen-only pod, no voice test.
2. **Money:** accept that at the measured download rate the combined pod cannot finish LTX inside $2.40/3.5 h, and that `--setup-min 45` is a target — he stops by hand at ~45 min if `measure.json` shows < 25 MB/s? Alternative: the separate $0.50 `--measure` pod first (R2) when stock returns.
3. **Money:** ElevenLabs ≈ 1500 credits for casting + two takes (needed before create for AV) — still approved?
4. **Money (text only):** may `spend_caps.json:24` `p12b_two_runs.for` be reworded to "Qwen MVA + LTX-2.5 plain/Layout/AV"?
## Rhythm update 2026-11-01 (WP-R3, MrBeast-style rhythm, BP-169..172)

The creator asked for fast cartoon actions. Three silent prompts (tent_s2, tent_s3, tent_s4) now name a fast verb from BP-172
(snaps, bolts/snatches/whips, snaps); the other silent prompts already did (KP-47 lints all six). The AV prompts stay as they are:
the take drives the mouth and a changed gesture could harm the lip sync. One plain clip, tent_s1 in L3, is rendered at 73 frames
(3.0 s) instead of 121 (`render.frames_by_shot`) to see how LTX-2.5 behaves at a hyped-zone length; L3 is optional, so the check
is dropped with it. No new stage, no new unit, so reserves and the drop order are unchanged.
