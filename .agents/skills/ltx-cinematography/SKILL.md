---
name: ltx-cinematography
description: Dedicated LTX-2.5 cinematography playbook covering photo-first vision prompting, FLF2V vs last-frame chaining vs IC-LoRA, 0.5s handles, 2K upscaling, and autonomous QA loops.
---
# LTX-2.5 Cinematography Playbook

## 1. Photo-First Prompting Law
- NEVER write or lock an LTX video motion prompt before inspecting the actual generated reference photo on disk.
- A Vision LLM MUST inspect the generated photo, record `PhotoObservation` (bound to the photo's 64-char SHA-256), and compose the motion prompt from the **observed pixels** via `explainer_engine.videolane.ltx_loop.build_photo_grounded_prompt`.
- Only use the 5 canonical camera moves (`truck`, `zoom_in`, `zoom_out`, `truck_zoom_in`, `truck_zoom_out`).

## 2. Mode Decision Matrix (`select_ltx_mode`)
- **First + Last Frame (`flf2v`)**: Use when a shot must land on a specific end pose, prop reveal, or matched cut. Match aspect ratios, prompt the *motion path* (not just endpoints), and allocate `97` or `121` frames (`8n + 1`) for larger changes.
- **Last-Frame Continuation (`last_frame_continuation`)**: Use ONLY within the **same scene and physical space** when continuing continuous action. Pick the sharpest/stillest tail frame (`finish/frame_pick.py`, BP-199), upscale it to max quality (2K) first, and cap chain depth at `MAX_CHAIN_DEPTH = 3` to prevent cumulative visual drift.
- **IC-LoRA Layout (`ic_lora_layout`)**: Use for multi-character spatial blocking driven by Blender previs depth/layout passes.
- **New Keyframe I2V (`new_keyframe_i2v`)**: Use on every scene change, reverse-angle coverage cut, or after chain depth reaches 3.

## 3. Handles ("ლუფტი") & 2K Upscaling
- Every clip adds `HEAD_HANDLE_S = 0.5s` and `TAIL_HANDLE_S = 0.5s` (`+1.0s` total) before quantizing up to LTX's `8n + 1` frame buckets (`compute_clip_timing_with_handles`).
- Upscale passing clips and extracted continuation tail frames to **2K (`2560x1440`)** via `realesrgan_x2` or `seedvr2_4n1` (`4n + 1` batching) before chaining or final assembly.

## 4. Closed-Loop Autonomous Shot Engine
`Photo -> Vision LLM inspects photo -> Photo-grounded LTX prompt -> LTX render (+0.5s handles) -> 3-Layer Eye+Ear QA -> PASS: 2K upscale clip + best tail frame -> loop next shot | FAIL: retry/adjust` (`explainer_engine.videolane.ltx_loop.run_continuous_shot_loop`).
