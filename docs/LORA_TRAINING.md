# LoRA training control (LT-)

How every LoRA of the channel is trained and judged: the photo style LoRA (Qwen-Image-2512, ai-toolkit), the image-edit
"next pose" LoRA (Qwen-Image-Edit-2511, paired data) and the video motion LoRA (LTX-2.5, ltx-trainer). Decision
[D-72](DECISIONS_AND_OPEN_QUESTIONS.md). Code: `explainer_engine/training/` (numbers in `lora_rules.json`), tests
`tests/unit/test_lora_training.py`. Agents: `lora-coordinator`, `lora-dataset-auditor`, `lora-run-operator`,
`lora-checkpoint-judge` (`.claude/agents/`); skill `lora-training`. Pods only through `explainer_engine.cloud.runpod`
(invariant 1); money ceilings only in `config/spend_caps.json`.

## 1. The protocol (one run)

| Gate | Who | Free? | Passes when |
|---|---|---|---|
| G1 dataset audit | `lora-dataset-auditor` | free | `python -m explainer_engine.training audit-style|audit-edit|audit-video ...` has 0 FAIL and the auditor has looked at every picture/clip (a contact sheet) |
| G2 config check | `lora-coordinator` | free | `check-config <cfg> --kind ... --captions ... --image ... --boot-minutes ...` 0 FAIL |
| G3 spend | `lora-coordinator` | free | the `project_cost` estimate is under the run's cap and the 24 h line; the cap is written in the run ledger before the pod |
| G4 launch | `lora-run-operator` | paid | pod via `cloud.runpod` with ledger + guard; step-0 (base) samples on; checkpoints and samples sync to HF |
| G5 checkpoint judge | `lora-checkpoint-judge` | free | at every saved checkpoint: `judge-style` (photo) / `compare_video` (video) / `judge_edit` (edit) + an eye check of the sample sheet; the action goes to the operator |
| G6 decision | `lora-coordinator` | — | STOP_KEEP_BEST / STOP_FAIL / DONE: the pod is stopped, the best checkpoint is named with its numbers and sheet, and the creator gets one comparison sheet |

## 2. Rules

| ID | Rule | Kind | Enforced by |
|---|---|---|---|
| LT-01 | Every image/clip has a caption; a style caption starts with the trigger (`wldnk style, <what is visible>`) | source + house (v2, 2026-10-23) | `audit.caption_findings` FAIL |
| LT-02 | No phrase of 4+ words in 45 % of captions (FAIL; 20 % WARN), no content word in 35 %+ (WARN): a shared phrase takes the style that the trigger should carry, a shared word appears unasked | house (v2 stopped at step 572 for exactly this) | `audit.shared_phrase_findings` |
| LT-03 | Captions describe what is visible, 6-70 words | source (ltx-trainer, RunComfy guides) | WARN |
| LT-04 | No byte-identical copies (weight with repeats, not copies); near-duplicates and reused captions are listed (a crop says "close-up of ...") | source (guides) | FAIL / WARN |
| LT-05 | Short side >= 768 px for a 768-1024 bucket (WARN), never under 512 px (FAIL: a 3x upscale teaches blur) | house (v7 audit 2026-10-23: 504x278 pictures in the creator's folder) | `size_findings` |
| LT-06 | The creator's own pictures are at least 50 % of training exposures (images x repeats) | house (ვანო 2026-10-23; v1 drifted with >50 % generated) | FAIL |
| LT-07 | Size: style 20-300 images; edit 60+ pairs; video 10-300 short coherent clips, frames-1 a multiple of 8 and width/height multiples of 32 (LTX) | source (ltx-trainer docs; RunComfy edit guide) | FAIL / WARN |
| LT-08 | Edit pairs match by file name in every control folder | source (ai-toolkit edit layout) | FAIL |
| LT-10 | Rank 16-64, learning rate 5e-5..2e-4 (FAIL above 5e-4): higher rank overfits sooner | source (ltx-trainer reference: rank 32, 1e-4; guides) | WARN / FAIL |
| LT-11 | A checkpoint and a sample set at least every 250 steps, all kept until judged | source (ltx-trainer `checkpoints.interval: 250`; "the best is often not the last") | FAIL / WARN |
| LT-12 | 4+ fixed-seed sample prompts, half of them held out (content not in the captions), one without the trigger | source (held-out tests, trigger-off probe) | FAIL / WARN |
| LT-13 | Cached text embeddings make caption dropout a no-op | source (guides) | WARN |
| LT-14 | Projected cost (steps left x measured s/step + samples + boot) under the cap; at 80 % stop and ask | invariant 2 | `project_cost`, `spend_findings` |
| LT-15 | The ai-toolkit image needs `boot_minutes >= 25` or the guard kills it before boot | house (2026-10-23 08:24) | FAIL |
| LT-16 | Launch: the config name, dataset folders and the launcher's cfg/pod.sh source paths all carry this run's name and dataset version | house (v4's first pod ran v3's config, 2026-10-23, $0.38) | `audit.check_launch` FAIL |
| LT-20 | Style progress = per-prompt move from the base sample (step 0, same seed) toward the creator's pictures; 0 = base, 1 = as close as his pictures are to each other | method (fixed prompt+seed comparison; CLIP/CSD style similarity) | `judge.score_run` |
| LT-21 | After 500 steps a progress under 0.10 is STOP_FAIL (trigger, captions or LR are wrong) | house (v2) | `judge.decide` |
| LT-22 | Prompt adherence (CLIP text-image) may not fall more than 0.03 below the base: "prompt ignored" | source (overfitting signs) | flag |
| LT-23 | No held-out sample at cosine >= 0.95 to a training picture: memorisation | source | flag |
| LT-24 | Samples of different prompts may not be more alike than the creator's own pictures (+0.05): "same background whatever the prompt" | source | flag |
| LT-25 | A no-trigger sample that moves far from the base (keep < 0.85) is noted: the LoRA acts without its trigger (fine for the universe LoRA, wrong for a character LoRA) | source (DOP idea) | note |
| LT-26 | Plateau: progress gains under 0.03 over two checkpoints -> STOP_KEEP_BEST (save the money) | source ("stop before prompt fidelity collapses") + house | `decide` |
| LT-27 | An overfit flag after a clean checkpoint -> STOP_KEEP_BEST; the best is the highest clean progress, confirmed by eye; the creator sees one sheet | source | `decide` |
| LT-28 | The metric is a signal, not the verdict: with 6 prompts x 1 seed, a difference under ~0.1 progress is noise; the sheet decides | house (v3 judge 2026-10-23) | judge agent |
| LT-30 | Video: the same benchmark shots (`plan_review_2026-10-23/benchmark_10shot.json`), seeds and stills with and without the LoRA | source (LTX blog: with/without, held-out clips) | `compare_video` |
| LT-31 | Motion may not drop under 0.7 x the base (a LoRA that freezes the picture "wins" every flicker metric) | source (VBench pairs smoothness with dynamic degree) | FAIL |
| LT-32 | Jitter (second frame difference / motion) may not rise over 1.2 x the base: flicker, wobble, morphing | source (VBench flicker; LTX troubleshooting) | FAIL |
| LT-33 | The frames at the given stills stay as close to them as the base does (-0.02) | house (our keyframe pipeline) | FAIL |
| LT-40 | Edit: output vs input on the held-out pairs, measured against the training pairs' own change | method | `judge_edit` |
| LT-41 | Set/camera drift on the frame's outer band under 2x the training pairs' | house (critic 2026-10-23: chained edits float) | FAIL |
| LT-42 | The output really changes (>= 0.25 x the training pairs' change): not a copy of the input | method | FAIL |
| LT-43 | Character identity (cosine of character crops) >= 0.85 | hypothesis | FAIL |
| LT-50 | Video QA of any generated shot (`video-qa`, ვანო 2026-10-23 22:32): a PASS lists morph p95, line keep and flicker | house | `video_qa.judge` |
| LT-51 | Brightness pop between two frames <= 0.06 (mean luma, 0..1) | house (VBench flicker idea) | FAIL |
| LT-52 | Morphing: the optical-flow warp residual per second <= 0.05; the first second over it = where a long shot breaks (max-length test) | method + house | FAIL |
| LT-53 | Line art never falls under 0.7 x frame 0's edge density (melting, blur): FAIL; detail (Laplacian variance) under 0.65 x frame 0: REVIEW (ghosting, translucent people) | house (max-length test 2026-10-23) | FAIL / REVIEW |
| LT-54 | Colour drift: saturation and brightness within ±0.08 (0..1) of frame 0: REVIEW; saturation lost by more than 0.2: FAIL (an IC render under conditioning strength 1.0 turns into its grey layout) | house (IC strength test 2026-10-24) | REVIEW / FAIL |
| LT-55 | A tracked character keeps its head and legs (outline density next to dark ink in the box's top/bottom >= 0.45 x frame 0 for 6 frames); median-flow tracking is weak, so REVIEW only | hypothesis | REVIEW |
| LT-56 | Fast-motion speed (p90, frame widths/s) inside the creator's cartoons' p10..p90 (`footage-rhythm`) | house (his 7.5 h of footage as the norm) | REVIEW |
| LT-57 | Hold share >= the cartoons' p10: always-moving "floaty" AI motion | house | REVIEW |
| LT-58 | Hands and faces are judged by eye on the `--sheet` (a crop of each tracked head and middle band per second); detectors are trained on photos | method | sheet |
| LT-59 | IC shots follow their layout: a grid cell where the render gains or loses lines (x2) the layout does not, for 0.5 s, is invented or lost content (B_ic: a second caveman drawn into the layout's ghost) | house | REVIEW |

Numbers marked house/hypothesis are starting values; a change needs a run's evidence in [PROGRESS](PROGRESS.md).

## 3. What the research says (2026-10-23)

- **Checkpoints, not loss.** Flow-matching loss stays flat (0.07-0.2) and does not show overfitting; save every 250 steps,
  render the same prompts with the same seed at each, and pick by the samples. The best is often not the last.
  ([Krea 2 style pair study](https://huggingface.co/shigure0110/krea2-style-lora-pair); [ltx-trainer configuration
  reference](https://github.com/Lightricks/LTX-2/blob/main/packages/ltx-trainer/docs/configuration-reference.md))
- **Overfitting signs:** the same background, pose or crop whatever the prompt; prompt words ignored; colour burn and hard
  edges; concepts bundled (an object that was always in the data appears unasked); only looks right at full strength.
  Fix with an earlier checkpoint, lower LR, fewer steps or rank, more varied data. Test strengths 0.6/0.8/1.0.
  ([LTX: run and monitor LoRA training](https://ltx.io/blog/run-and-monitor-lora-training); [Z-Image LoRA guide](https://dev.to/gary_yan_86eb77d35e0070f5/best-practices-for-training-lora-models-with-z-image-complete-2026-guide-4p7h))
- **Held-out tests:** hold back a few examples; mix sample prompts inside and outside the training concepts; one prompt
  without the trigger. A LoRA that only works on prompts like its captions has memorised them.
- **Style metric:** CLIP mixes content and style, so we only compare a prompt with itself across checkpoints. CSD
  ([Somepalli et al. 2024](https://arxiv.org/abs/2404.01292)) is the stronger style descriptor; raw CSD cosine must also be
  read relative to a reference set (2026 preprint), which is what our 0-1 progress does. CARLoS / AnyStyle compare LoRA vs
  base on the same prompt and seed with CLIP + DINO + text consistency.
- **Video:** with/without the LoRA on held-out shots; motion LoRA at 2,000 steps started copying training frames and was
  rolled back to 750 (community report); short coherent clips, motion described precisely, `(F-1) % 8 == 0`, 32-px sizes;
  rank 32, LR 1e-4, 2,000 steps, validation every 100-250 steps with first-frame conditioning
  ([ltx-trainer](https://github.com/Lightricks/LTX-2/tree/main/packages/ltx-trainer)). Temporal metrics are read together
  with dynamic degree ([VBench](https://arxiv.org/abs/2311.17982)).
- **Edit pairs:** targets and controls match by file name; 60-200+ pairs; captions name only what changes
  ([RunComfy 2511 guides](https://www.runcomfy.com/trainer/ai-toolkit/qwen-image-edit-2511-likeness-custom-lora)).
- **Qwen-Image numbers in the wild:** rank 16-42, LR 5e-5..1e-4, 1,000-35,000 steps depending on data; no official
  ai-toolkit style recipe ([linnea-qwen-image](https://huggingface.co/alvdansen/linnea-qwen-image),
  [RenderStyle](https://huggingface.co/Zaytron40k/Qwen-Image-RenderStyle-LoRA)).

## 4. Voice and editing: can we train our own? (ვანო 2026-10-23 14:27)

**Voice: yes, it is the most mature of the two.** Open TTS models train on a few hours of one speaker: Orpheus 3B (LoRA
or full fine-tune with Unsloth, ~3 h single-speaker example, emotion tags like laughs and sighs), F5-TTS (community LoRA),
CosyVoice2 and Kokoro (Apache-2.0), Chatterbox (MIT, watermark built in). VibeVoice is research-only; check each licence
file before use ([Unsloth TTS fine-tuning](https://docs.unsloth.ai/basics/text-to-speech-tts-fine-tuning),
[F5-LoRA](https://odunola.bearblog.dev/f5-lora-low-rank-adaptation-for-text-to-speech/)). The data problem: we need 2-5 h
of clean narration in OUR narrator's voice with transcripts. Today that voice is ElevenLabs; training an open model on
ElevenLabs output must be checked against ElevenLabs' terms first, and a real voice needs its owner's consent. Its value:
no per-character price, unlimited takes, our own emotion control. Same G1-G6 protocol: audit = transcript match and
loudness per clip; judge = word error rate (Scribe/Whisper) + speaker similarity to held-out lines + the creator's ear.

**Editing: not a LoRA problem today.** Research models learn where to cut from edited films (Pardo et al. ICCV 2021,
Huang et al. ICCVW 2021; a 2026 autoregressive "film montage" preprint with a CUT token), but none is a ready open model
we can fine-tune on cartoons and plug into `production/assemble.py`. The practical "own AI editing" is to MEASURE the
reference cartoons (shot lengths, cut on action, hold before a reaction, camera moves per minute) and feed the numbers into
the existing editing rules (BP-/ED-) and the edit-planner agent: free, testable, and it learns the same habits.

## 5. Shared files

- Benchmarks: `plan_review_2026-10-23/benchmark_10shot.json`, `shot_schema_v1.json` (project files).
- Results: HF `vano1919/tmr-artifacts/lora_plan_2026-10-22/train_<run>/` (config, samples, checkpoints, logs) and the
  judge's `judge.json` next to them.

## 6. Footage into training material (FS-, 2026-10-23)

The creator's 2D footage (ვანო 14:51: films and season collages, ~3 h; the plan in Georgian: project files
`lora_plan_2026-10-22/FOOTAGE_PLAN_2026-10-23_ka.md`) feeds both LoRAs through `training/footage.py` (free, CPU: ffmpeg,
OpenCV, PySceneDetect). The photo LoRA learns scene STABILITY from pairs of the same shot (never the world's style); the
motion LoRA learns MOVEMENT from short clips, starting from our own stills.

| ID | Rule | Enforced by |
|---|---|---|
| FS-00 | Every file probed: >= 720p, >= 23 fps, progressive; show name from the file stem | `footage.index` WARN |
| FS-01 | Shots by hard-cut detection, >= 2 s; a shot repeated in a collage (dHash) counts once | `footage.split` |
| FS-02 | Camera shift (phase correlation, p90) and motion (median residual) per shot; `pair` = fixed camera (<= 1 % shift) + motion; `clip` = motion; `static`/`dup` out | `footage.measure`, `classify` |
| FS-03 | No show over 30 % of usable footage (one style cannot settle) | `footage.balance` WARN |
| FS-04 | One whole show held out for the judge (3+ shows) | `footage.balance` |
| FS-05 | Motion captions carry no character, show or studio names and no style words | `caption_findings_motion` FAIL |
| FS-06 | Pairs: control = the shot's master frame, target = 2.5-4 s later, a second pair for long shots, both from the master (never chained) | `footage.pairs` |
| FS-07 | Clips: 89 frames @ 24 fps from the shot start, 768x448 (LTX bucket), `audit-video` 0 FAIL | `footage.clips` |
| LT-34 | Video: the mid-clip frame keeps the first frame's style (distance <= the no-LoRA distance + 0.02) | judge (planned) |
| LT-44 | Edit: palette ΔE plate->output <= 1.5 x the training pairs' median | judge (planned) |
| LT-45 | Edit: style leakage on our wldnk plates <= the no-LoRA distance + 0.02; two FAILs = STOP_KEEP_BEST | judge (planned) |
