---
name: lora-training
description: How the channel trains and tests its LoRAs (since D-80, 2026-10-26: one LoRA on Qwen-Image-2.1 for the Rick-and-Morty-learned style and the scene sequence; older 2512/Edit-2511/wldnk notes are history) - the G1-G6 protocol, the free tools in explainer_engine.training, settings that worked and the lessons that cost money. Use before planning, launching, judging or comparing any LoRA run.
---

# LoRA training and testing

> **Retired in part by [D-80](../../../docs/DECISIONS_AND_OPEN_QUESTIONS.md) (2026-10-26):** Qwen-Image-2512, Edit-2511 and every `wldnk_*` LoRA are banned; keyframes come from Qwen-Image-2.1 (draws and edits with references) with the new LoRA learned from Rick and Morty. Model rows and the `wldnk style` prompt shape below describe the banned stack; the new prompt rules come from the 2.1 prompt-type test. Settings below that name 2512, Edit-2511 or `wldnk` are lessons, not instructions.

Rules and sources: `docs/LORA_TRAINING.md` (LT-xx). Agents: `lora-coordinator` (owner), `lora-dataset-auditor`,
`lora-run-operator`, `lora-checkpoint-judge`. Code: `explainer_engine/training/` (`audit.py`, `judge.py`, `embed.py`).

## The loop
audit (free) -> config check (free) -> cost projection (free) -> pod with ledger + guard -> judge every 250 steps (free)
-> stop at plateau or the first overfit sign, keep the best -> one sheet to the creator.

Current stack: one LoRA on Qwen-Image-2.1 (D-80, LT-79 in docs/LORA_TRAINING.md).

## Lessons that cost money
- 2026-10-24 (≈$1.6): pods judged by the REST record (runtime null for every pod) and scripts silent until their
  first stage ended. Now LT-17: every pod script uploads its log every <= 5 min from its first line, the launcher passes
  `script=` to `preflight_create` and `heartbeat=` to `new_session`; stop a "stuck" pod only after reading its last log.
- v1 (≈$1.05): >50 % generated pictures -> too round, warm, saturated. The creator's pictures must lead (LT-06).
- v2 (≈$0.9, stopped at 572): one long style phrase in every caption -> the style bound to the phrase, not the trigger.
- v3 (stopped at 500): best at 250 (progress 0.55) not 500 (0.42); at 500 the close-up fell back to semi-photo. The last
  checkpoint is not the best by default.
- v7 audit: 504x278 pictures in the creator's folder (3x upscale = learned blur) -> dropped before v4.

## History (retired by D-80, lessons only)

### Settings that worked (2026-10-23, Qwen-Image-2512, ai-toolkit, A40 48 GB, $0.59/h)
- rank 32 / alpha 32, LR 1e-4, adamw8bit, batch 1, 768-1024 buckets, qfloat8 model + text encoder, 5.21 s/step.
- Captions: `wldnk style, <what is visible>`; nothing shared by every caption; crops get their own "close-up" caption.
- Samples: 6-7 prompts, fixed seed (walk_seed keeps one seed per prompt), 1024x576, 20 steps (≈40 s each); half held
  out; one without the trigger; step 0 kept as the base.
- Boot: the aitoolkit image needs `boot_minutes=25`.

### Video and edit LoRAs
- Motion LoRA (LTX-2.5, ltx-trainer): clips `(F-1) % 8 == 0`, sizes /32, short coherent shots, captions describe the
  movement without character names; rank 32, LR 3e-5..1e-4 with cosine + 5-10 % warm-up (ვანო's report 2026-10-24,
  LT-10), rank >= 64 only with `use_rslora`; ~2,000 steps max, validation every 250 with first-frame conditioning; judge
  with/without on `benchmark_10shot.json`; motion must not drop (LT-31), jitter must not rise (LT-32). The creator's 50
  criteria (VQ-01..50, `training/video_criteria.json`, LORA_TRAINING section 7) say what the judge looks at by eye.
- Linked shots (ვანო 2026-10-24, "linked list"): no training; shot B = `--image <A's last frame> 0 1.0` +
  `--image <B's end keyframe> N 1.0 guide` + `--video-conditioning <A>` in ltx-pipelines; `shot-identity A B` checks the
  join (LT-60..62). Never prompt a hero out of frame on a single still (farm_storm 2026-10-24).
- Next-pose edit LoRA (Qwen-Image-Edit-2511): only after the zero-shot test fails; pairs from one master plate, control
  and target by file name; judge drift of the set and camera (LT-41) and that the pose really changes (LT-42).
  v1 (2026-10-24): 60 cartoon pairs redrawn into Wild Ink at strength 0.55 (0.7 invents objects) + 16 own pairs x2, so the
  LoRA never pulls style toward the cartoons. Captions (v2 on): `nextpose, a later frame of the same continuous animated
  shot, same camera: <what changed>` (FS-05): the LoRA learns "a frame of a video", not "a photo". A keyframe pair counts
  only once it animates: start -> end through LTX, `video-qa` + `shot-identity` PASS (physics cannot be read off a still).

## Voice / editing
Own TTS voice (Orpheus, F5-TTS, CosyVoice2, Chatterbox) is feasible with 2-5 h of clean transcribed narration; check the
voice's rights and the provider's terms first. Editing: measure reference cartoons into the ED-/BP- rules instead of
training a model (docs/LORA_TRAINING.md section 4).
