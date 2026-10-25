# LoRA training control (LT-)

Scope since 2026-10-25 (LT-69): only the photo style LoRA is trained; the sections on the other two stay as history.
How every LoRA of the channel is trained and judged: the photo style LoRA (Qwen-Image-2512, ai-toolkit), the image-edit
"next pose" LoRA (Qwen-Image-Edit-2511, paired data) and the video motion LoRA (LTX-2.5, ltx-trainer). Decision
[D-72](DECISIONS_AND_OPEN_QUESTIONS.md). Code: `explainer_engine/training/` (numbers in `lora_rules.json`), tests
`tests/unit/test_lora_training.py`. Pages: `lora-coordinator` (the main agent), `lora-dataset-auditor` and `lora-run-operator` (its checklists),
`lora-checkpoint-judge` (the one spawned critic, OR-20) (`.claude/agents/`); skill `lora-training`. Pods only through `explainer_engine.cloud.runpod`
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
| LT-07 | Size: style 20-1000 images (1000 for the D-80 material, ვანო 2026-10-26 02:15 Tbilisi; was 300); edit 60+ pairs; video 10-300 short coherent clips, frames-1 a multiple of 8 and width/height multiples of 32 (LTX) | source (ltx-trainer docs; RunComfy edit guide) | FAIL / WARN |
| LT-08 | Edit pairs match by file name in every control folder | source (ai-toolkit edit layout) | FAIL |
| LT-10 | Rank 16-64, learning rate 5e-5..2e-4 (FAIL above 5e-4): higher rank overfits sooner; video LoRAs 3e-5..1e-4 with cosine + 5-10 % warm-up; rank >= 64 sets `use_rslora` | source (ltx-trainer reference: rank 32, 1e-4; guides; ვანო's report 2026-10-24, section 7.1) | WARN / FAIL |
| LT-11 | A checkpoint and a sample set at least every 250 steps, all kept until judged | source (ltx-trainer `checkpoints.interval: 250`; "the best is often not the last") | FAIL / WARN |
| LT-12 | 4+ fixed-seed sample prompts, half of them held out (content not in the captions), one without the trigger | source (held-out tests, trigger-off probe) | FAIL / WARN |
| LT-13 | Cached text embeddings make caption dropout a no-op | source (guides) | WARN |
| LT-14 | Projected cost (steps left x measured s/step + samples + boot) under the cap; at 80 % stop and ask | invariant 2 | `project_cost`, `spend_findings` |
| LT-15 | The ai-toolkit image needs `boot_minutes >= 25` or the guard kills it before boot | house (2026-10-23 08:24) | FAIL |
| LT-17 | A pod's sign of life is its own upload, never the REST record (`runtime` is null, `machine` empty and no IP for running script pods too). Every pod script starts a background log upload (<= 300 s) before its first heavy step and rewrites a heartbeat file on every pass (an unchanged file is not re-uploaded, so its date freezes) (`cloud.runpod.lint_pod_script`, refused by `preflight_create(script=...)`); the session names the uploaded file (`heartbeat`), a fresh upload lifts the boot deadline, and silence only pushes an alert: a pod is stopped as stuck only after its last uploaded log was read | house (2026-10-24: a working training pod stopped at 72 min ≈$1.3, a rendering pod killed at its boot deadline ≈$0.3) | FAIL |
| LT-18 | A TEST video (a check of logic, motion, sound or editing, not a release) is rendered at the generator's base resolution: no upscale step (no 2K/4K pass, no SeedVR2). Each shot is made once and checked; only a failed check makes a new take (no fixed 1 or 2 takes). The release resolution is 2K (1440p) | house (ვანო 2026-10-24 14:38 and 14:45) | REVIEW |
| LT-19 | A pod's first GPU call runs under `timeout` and proves CUDA with a real operation; on failure or timeout the script writes `BAD_HOST ...` (exit code, driver) into its heartbeat file, uploads it and waits, and the guard stops that pod at once (`heartbeat_step` -> "bad_host"). The upload loop never overwrites a BAD_HOST line (`grep -q BAD_HOST beat.txt \|\| date > beat.txt`). Pods keep `allowedCudaVersions` (`create` refuses a body without it); a launcher may drop the filter for stock only with `any_cuda=True` and a script that passes the probe lint. The heartbeat proves the loop, not progress: read the log's last step, not only its date | house (chain pod 2026-10-24: no CUDA filter -> a driver-550 host (CUDA 12.4 + compat 13.0) for the CUDA 13 image; `torch.cuda.get_device_name` never returned, the loop kept the pod "alive" for 12 min, ≈$0.6) | `lint_pod_script` FAIL, `create` FAIL |
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
| LT-60 | Continuity across a cut (`shot-identity`, ვანო 2026-10-24 07:17): the set's palette distance (hue x saturation + brightness histograms, ink dropped) between shot A's last frame and shot B's first <= 0.08 (two scenes of the eras test measure 0.09, one clip's first vs last 0.002..0.006) | house (eras test 2026-10-24) | REVIEW |
| LT-61 | Across a cut the line weight stays within x0.7..x1.4 (share of ink pixels): a thicker or thinner drawing, or lost outlines | house | REVIEW |
| LT-62 | Each named hero's box keeps its colours across the cut (palette distance <= 0.15 on its box: clothes, skin, hair); whether it is the same face is for the eye (LT-58) or CLIP (LT-43) | house | REVIEW |
| LT-63 | **Every run uses the newest code and rules.** Before a paid run, fetch the heads of the branches that own the tools: PR #22 for pods, the gate and layout, PR #24 for the shot composer and prompt rules, or main once they are merged. Prompts come from `film_shots compose` on the current head, never written by hand. A hand-written prompt is allowed only in a test of a new approach, and its run record says so. Every run records the commit of each repository it used | house (ვანო 2026-10-24 22:19: "you use the old code") | the run record (`code_commits`) + review |
| LT-64 | **Rules the creator approved apply in every next iteration without being asked again:** the LoRA only on Qwen-Image-2.1, which draws and edits with references (KG-16, D-80; 2512, Edit-2511 and every old LoRA retired); a picture is generated once, checked, and redrawn only on a fail, at most 3 times (KG-14); every picture is compared with the approved eras sheet before it is shown; no numbers in picture prompts (film test v2; the composer rule is in PR #24); each figure is named once with its full tag and later only with "the"; prompts stay near the length of the style captions (LT-03); pods only through `cloud.runpod` with a heartbeat and a timed CUDA probe (LT-17, LT-19); I check the pod at least every 15 minutes and stop it when its finish file appears | house (ვანო 2026-10-24) | review; KG gate; `lint_pod_script` |
| LT-65 | (suspended 2026-10-26 by D-80: written for the banned wldnk look; rewritten from the 2.1 prompt-type test) **A style-LoRA prompt has the shape of the prompts that drew the approved look:** `wldnk style, ` + a short story of the moment (a place, an action at its peak, someone's reaction, caricature body words such as lanky or bony, a light source, one or two props), at most 40 words; no camera, sizes or positions in the words (they go to the layout, [ASSET_COMPOSE](ASSET_COMPOSE.md)); no grey light; the caption tail is not added (`python -m explainer_engine.qa.style_prompt`) | 2026-10-25 analysis: the 20 approved eras prompts (19-29 words) and the v5 training samples that drew the film's own heroes in the approved look (19-33 words) have this shape and no tail; the film prompts that lost the look were 73-337 words of standing figures, layout and grey light; the tail brought the look back but over-caricatured and added long-nosed extras in 6 of 8 shots. Replaces the 2026-10-24 tail rule | `style_prompt.check` |
| LT-66 | (suspended 2026-10-26 by D-80: written for the banned wldnk look; rewritten from the 2.1 prompt-type test) **The absolutes, never changed by a prompt, an episode or an agent** (`style_prompt.ABSOLUTES`, frozen by `tests/unit/test_episode_look.py`): A1 `wldnk style` first, once; A2 the LoRA at 1.0 only on Qwen-Image-2.1 bf16, 1280x720, 30 steps, true_cfg 4, in plain or edit mode with references (`INFERENCE`, D-80); A3 the negative prompt exactly `NEGATIVE`; A4 at most 40 words in the moment shape (LT-65); A5 no caption tail; A6 no camera, size, position, measurement or number words; A7 each full character tag once; A8 no other medium or art style (photo, 3D, anime, watercolour, cinematic, "in the style of" ...: FAIL); A9 an episode look adds only colour and light words (AC-16..AC-19); A10 every sheet is compared with the approved eras sheet before it is shown (KG-22). A change to one of them needs ვანო's word and a new LoRA version | ვანო 2026-10-25 03:04 Tbilisi: "define the absolutes in the prompting rules, what we never change"; the values are the ones that drew the approved eras sheet and v5 samples (LT-65 sources) | `style_prompt.check`, `test_episode_look.test_absolutes_are_frozen` |
| LT-67 | (suspended 2026-10-26 by D-80: written for the banned wldnk look; rewritten from the 2.1 prompt-type test) **Generated training pictures are drawn with the eras formula** (the prompt shape of the approved sheet): `wldnk style, ` + place and era + one comic action at its peak + another figure's reaction + body caricature words + one light source + 1-2 world props; 20-33 words; each figure named once; no numbers, no camera words, no tail; no word that names an unwanted thing ("city bus" drew a city). The set spreads over eras, single faces reacting, crowds, interiors and snow, because the 18 photos have none of those; the variety comes from the content, never from camera words (LT-66 A6) | the eras sheet ვანო called ideal (2026-10-24); 2.1 sample p0 drew a city for "city bus" (2026-10-25) | `style_prompt.check` on every prompt of the set |
| LT-68 | (suspended 2026-10-26 by D-80: written for the banned wldnk look; rewritten from the 2.1 prompt-type test) **Generated pictures enter a style set only after both gates and only as a minority.** A picture joins only with a KG-23 style PASS and a KG-25 logic PASS; its scores go into the dataset manifest. His photos keep at least half of the training weight (repeats), generated pictures at most 40 % | v1 (2026-10-23): over 50 % generated pictures made the style "too rounded" | `blind_check.compare`, `style_verdict` (KG-23, KG-25) |
| LT-69 | **One LoRA on Qwen-Image-2.1 learns the style and the scene sequence together** (replaces the 2026-10-25 "only the style" rule, [D-80](DECISIONS_AND_OPEN_QUESTIONS.md)). The data is Rick and Morty footage (singles for the look, consecutive shots of one scene for the sequence); how the sequences enter training is decided during the process with the creator. Continuity is still written as cards ([SHOT_CONTINUITY](SHOT_CONTINUITY.md), [D-75](DECISIONS_AND_OPEN_QUESTIONS.md)); each checkpoint runs the prompt-type test on held-out R&M sequences, so style loss and link loss are measured on the same frames | house (ვანო 2026-10-26 01:15 Tbilisi) | the plan (OR-23); the continuity test with and without the LoRA |
| LT-70 | **The creator's eye decides which generated picture is training data.** A generated picture joins a style set only with ვანო's 👍. The automatic gates (KG-23, KG-25) only pre-sort it. Of 70 DINO-passed frames he gave 13 a 👍. All 12 samples of v2, which was trained with self-generated pictures, got 👎. The DINO pass set was poorer than the fail set (edge density 0.20 vs 0.26): the score follows content, not richness | house (ratings 2026-10-25, 107 pictures) | the dataset audit lists each generated picture with its rating |
| LT-71 | **Every money event and every main-work result goes to the creator at once, in detail.** Covered: a hung or idle pod, a stuck or failed job, a balance warning, a result, a plan change. Each report gives what happens, $/h, $ already lost, the options (restart / wait / stop) with their cost, and a recommendation. Worker jobs carry a time limit near their expected length (per picture ~60 s x count + load), never a one-hour default, so a hang cannot burn an hour | house (ვანო 2026-10-25 21:01 Tbilisi, after job 0195 hung ~45 min at $1.43/h and was reported only as "stuck") | the thread; job time limits in the worker job files |
| LT-72 | **Every idea is checked before it is followed: critical, not negative.** That covers the creator's ideas and our own. Each claim is checked against the records (logs, ratings, billing, research) and the cost. The answer agrees or disagrees with the evidence; an unknown is named, with the cheapest test that settles it. A switch of tool, model or strategy is first compared with the current approved option on the same prompts, with its risk and cost stated. Never a plain "yes" | house (ვანო 2026-10-25 21:03 Tbilisi: the move to Qwen-Image-2.1 and the scene LoRA were followed without a comparison) | the thread; the plan of every paid run |
| LT-73 | **A new decision rewrites every older rule it contradicts, in the same change.** Before a run and with every new decision: search the docs, the code constants and the tests for the old value (a model name, a base, a limit) and change them together, so no old rule is quoted against a newer decision. The newer rule wins (D-77) | house (ვანო 2026-10-26 01:02 Tbilisi: old 2512 rules were quoted after the move to 2.1) | `tests/unit/test_keyframe_gate.py::test_only_the_2_1_stack` + review |
| LT-74 | **Captions written by a vision model are read before training.** Automatic flags first (a name of a character, show or studio; a description outside 35-120 words; a change line that does not start "Change from the previous shot:"); then Claude reads every caption against its picture: a wrong fact is fixed by hand, a caption that cannot be fixed or a picture that is wrong drops that item (`drop: true`). Training reads only `captions_reviewed.jsonl` | house (ვანო 2026-10-26 02:15 Tbilisi) | `caption_xworld_v1.problems`, review |
| LT-75 | **The prompt-type test picks its winner by measurement against the real next frame, then by eye; the creator decides.** On held-out scenes the real first frame is given and the next 5 are drawn per variant (D, V1-V6, D0 = D without the LoRA) at two checkpoints; each drawn frame is scored against the real frame of the same place in the scene: palette distance (LT-60), line weight (LT-61), CLIP image similarity, set drift and real change (LT-41, LT-42). The best mean wins, Claude confirms it on the sheet, ვანო decides | house (ვანო 2026-10-26 02:15 Tbilisi) | test report + sheet |
| LT-76 | **Held-out scenes never reach training.** Whole scene chains are held out, and every shot of their time span plus two shots on each side leaves every training folder; the build refuses a leak | house (ვანო 2026-10-26 01:44 Tbilisi: 10 % held out as whole scenes) | `xworld_v1_build.plan` |
| LT-77 | **Training samples for a 2.1 LoRA (LT-12 on D-80):** six fixed-seed prompts: two held-out scene descriptions, the first again without the trigger, one held-out edit (real frame + the change line to the next), two new subjects | house (ვანო 2026-10-26 02:15 Tbilisi) | `xworld_v1_build.samples` |

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
| FS-05 | Motion captions carry no character, show or studio names and no style words; a next-pose caption reads `nextpose, a later frame of the same continuous animated shot, same camera: <what changed>` (ვანო 2026-10-24: a frame of a video, not a photo) | `caption_findings_motion` FAIL |
| FS-06 | Pairs: control = the shot's master frame, target = 2.5-4 s later, a second pair for long shots, both from the master (never chained) | `footage.pairs` |
| FS-07 | Clips: 89 frames @ 24 fps from the shot start, 768x448 (LTX bucket), `audit-video` 0 FAIL | `footage.clips` |
| LT-34 | Video: the mid-clip frame keeps the first frame's style (distance <= the no-LoRA distance + 0.02) | judge (planned) |
| LT-44 | Edit: palette ΔE plate->output <= 1.5 x the training pairs' median | judge (planned) |
| LT-45 | Edit: style leakage on our wldnk plates <= the no-LoRA distance + 0.02; two FAILs = STOP_KEEP_BEST | judge (planned) |

## 7. The creator's 50 video criteria (VQ-01..VQ-50, ვანო 2026-10-24)

Source: ვანო's report in project files `lora_plan_2026-10-22/VIDEO_LORA_REPORT_vano_2026-10-24_ka.md` (VBench / VBench-2.0
based). The registry is `explainer_engine/training/video_criteria.json`; this table is generated from it
(`tests/unit/test_lora_training.py` keeps the two together). `code` = an LT rule measures it, `eye` = the review sheet
(LT-58) and the judge's look, `na` = not in our frames. Allowed in animation (his list): squash and stretch (VQ-25),
follow-through (VQ-26), motion blur in fast motion, a small drift of leaves, clouds or water. Unacceptable: identity
morphing, flicker, causality collapse, dynamic-degree collapse. Of the 50, 22 are measured in code, 27 by eye, 1 is n/a.
Physics (VQ-21..30) is by eye only: a still cannot prove it, so every keyframe pair is proven by animating it (section 7.1).

| ID | Criterion (ვანო) | Group | How we check | Rules |
|---|---|---|---|---|
| VQ-01 | resolution kept, no pixelation or blur | visual | code | LT-53 |
| VQ-02 | lighting consistent with the scene geometry | visual | eye |  |
| VQ-03 | contrast and dynamic range, no burnt or crushed zones | visual | code | LT-51, LT-54 |
| VQ-04 | colour temperature stable across frames | visual | code | LT-54, LT-60 |
| VQ-05 | edge sharpness between figures and set | visual | code | LT-53 |
| VQ-06 | background keeps its structure | visual | code | LT-59 |
| VQ-07 | texture fidelity (skin, cloth, metal, water) | visual | eye |  |
| VQ-08 | no diffusion grain or denoising residue | visual | eye |  |
| VQ-09 | compositional balance | visual | eye |  |
| VQ-10 | anatomy correct in a still (hands, face, proportions) | visual | eye | LT-58 |
| VQ-11 | no flicker between neighbouring frames | temporal | code | LT-51, LT-32 |
| VQ-12 | subject identity kept over time | temporal | code | LT-52, LT-62, LT-43 |
| VQ-13 | background does not drift or melt | temporal | code | LT-59, LT-41, LT-53 |
| VQ-14 | motion smoothness, no stutter | temporal | code | LT-52, LT-32 |
| VQ-15 | dynamic degree: real motion, not a camera over a still | temporal | code | LT-31, LT-57 |
| VQ-16 | object permanence (leaves and returns the same) | temporal | code | LT-55 |
| VQ-17 | micro-expressions develop naturally | temporal | eye | LT-58 |
| VQ-18 | clothes and attributes stay | temporal | code | LT-62 |
| VQ-19 | camera trajectory smooth and physical | temporal | eye |  |
| VQ-20 | several subjects move independently and logically | temporal | eye |  |
| VQ-21 | gravity | physics | eye |  |
| VQ-22 | momentum kept, no instant stops | physics | eye |  |
| VQ-23 | collision response | physics | eye |  |
| VQ-24 | fluid, fire and smoke dynamics | physics | eye |  |
| VQ-25 | squash and stretch is intentional (allowed in animation) | physics | eye |  |
| VQ-26 | follow-through of hair and cloth (allowed, wanted) | physics | eye |  |
| VQ-27 | arc motion | physics | eye |  |
| VQ-28 | shadows move with the figure | physics | eye |  |
| VQ-29 | reflections in sync | physics | eye |  |
| VQ-30 | cloth physics | physics | eye |  |
| VQ-31 | subject matches the prompt | semantics | eye | LT-22 |
| VQ-32 | the asked action is completed | semantics | eye |  |
| VQ-33 | style kept in detail | semantics | code | LT-34, LT-45 |
| VQ-34 | spatial relations as asked | semantics | eye |  |
| VQ-35 | figures interact without merging | semantics | eye | LT-58 |
| VQ-36 | temporal narrative: beginning, middle, end | semantics | eye |  |
| VQ-37 | attribute binding (the right colour on the right thing) | semantics | eye |  |
| VQ-38 | text rendering in motion | semantics | na (no text in our frames; captions are added in the edit) |  |
| VQ-39 | commonsense | semantics | eye |  |
| VQ-40 | environment context (footprints in snow) | semantics | eye |  |
| VQ-41 | overfitting: copies of the training set | lora | code | LT-23, LT-27 |
| VQ-42 | underfitting: the LoRA is not felt | lora | code | LT-21 |
| VQ-43 | concept bleeding onto the set or other figures | lora | code | LT-24, LT-44, LT-45 |
| VQ-44 | trigger word isolation | lora | code | LT-25, LT-12 |
| VQ-45 | no catastrophic forgetting (anatomy, prompts) | lora | code | LT-22 |
| VQ-46 | works across buckets and aspect ratios | lora | eye |  |
| VQ-47 | I2V leaves the first frame: new detail appears in motion | lora | code | LT-31, LT-33 |
| VQ-48 | no motion suppression by the LoRA | lora | code | LT-31 |
| VQ-49 | no geometry distortion in motion (spatial attention damage) | lora | code | LT-52, LT-32 |
| VQ-50 | no jump cuts or temporal desync from the LoRA | lora | code | LT-51, LT-32 |

### 7.1 Taken and not taken from his technical advice (evidence)

| Advice | Decision | Why |
|---|---|---|
| Mixed photo + video data, never stills only, for the video LoRA | taken (already the plan) | the motion LoRA trains on his cartoon clips (FS-07); stills-only I2V training freezes motion (his report; LT-31 guards it) |
| LR 3e-5..5e-5 for video DiTs, cosine + 5-10 % warm-up | taken for the video LoRA | ltx-trainer reference used 1e-4; his sources say lower for video; LT-10's video range becomes 3e-5..1e-4 with warm-up |
| RS-LoRA at rank 64+ | taken as a rule | our ranks are 16-32; the style LoRA (rank 64) is frozen and good, so no re-train; any future rank >= 64 sets `use_rslora` |
| Trigger isolation: caption only the subject, never the set or camera | taken for character/style captions; NOT for the scene LoRA | a next-pose caption must say what moves (the pose change is the lesson); the set is held by the control image, not the caption (FS-05, LT-02 keep set words out of every caption) |
| "A frame of a video, not a photo" for the scene LoRA | taken (v2 captions + prompts) | FS-05 now: `nextpose, a later frame of the same continuous animated shot, same camera: <what changed>`; the gate is the animation test, not the still |
| Keyframe pairs proven by animating them (start -> end through LTX) before they count | taken (gate G5 for the scene LoRA) | a still cannot show physics; `video-qa` + `shot-identity` on the animated pair; a pair that does not animate fails |
| DLoRAL: separate temporal C-LoRA and spatial D-LoRA | not taken as such | LTX-2.5 uses joint spatio-temporal attention in one DiT (no separate temporal blocks to target); our split is already three LoRAs (style on the image model, pose on the edit model, motion on LTX) |
| Optical-flow and LPIPS losses | not taken now | neither ai-toolkit nor ltx-trainer exposes them; a custom loss is a research project; the flow residual is measured after the fact instead (LT-52) |
| Two-stage training (coarse 2000 steps, then fine 1e-5 + weight decay) | not now | our runs are <= 1000 steps on a $5-15 ceiling; a second stage doubles cost; reconsider after the first video LoRA's judge |
| Previous/next shot (linked list) | taken, no training needed | LTX-2.5 `--image <start> 0 1.0` + `--image <end> N 1.0 guide` + `--video-conditioning <previous shot>` (ltx-pipelines args.py); LT-60..62 check the join; proven by one 3-shot test |

Root causes of the five eras clips (2026-10-24, `eras_video_2026-10-24/`): farm_storm (cows run out of frame, the farmer
vanishes) = the prompt asked for it on a static still, not the model (VQ-32 vs VQ-16: never prompt a hero out of frame);
wildwest_train (heroes blur in the last 3 s) = the single-photo length limit (VQ-13, LT-53); ice_age_tribe (nearly frozen,
hold 0.85) = first-frame anchor bias on a crowded still (VQ-15, VQ-47: the prompt must name one action per hero);
disco_1970s and school_class act and keep identity (VQ-12, VQ-18 PASS).
