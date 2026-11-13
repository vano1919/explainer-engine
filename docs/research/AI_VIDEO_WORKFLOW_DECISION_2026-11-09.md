# Explainer Engine — Decision Digest from Two Video Workflow Studies
Date: 2026-11-09

## Decision

**Primary production approach: Hybrid B → C — scene/shot keyframes first, then one short image-to-video generation per shot.**

Use a controlled 2D storyboard/keyframe stage to approve the scene, characters, framing and important start/end states before running video generation. Then generate each video shot independently with the Wan 2.2 Fun InP/I2V family. Do not ask one text-to-video generation to invent an entire multi-shot historical sequence.

**Secondary approach: per-shot video with one explicit motion/control input when a shot needs more choreography.**

Use Wan 2.2 Fun Control / Camera, or a compatible trajectory workflow, only for shots where the normal start-frame or start/end-frame method cannot express the required action. Select one control method per shot; do not stack every available control signal.

This is the decision from the overlap of the two supplied studies, adjusted for the project's priorities: coherent storytelling, character continuity, scene/camera control, stability and simplicity over hyperrealism.

## What the two reports agree on

Both studies identify the current Qwen + Blender + LTX multi-conditioned route as unnecessarily complex and recommend separating:
1. narrative and spatial/camera planning;
2. image/keyframe approval;
3. temporal motion generation;
4. audio and timeline assembly.

Both reject pure end-to-end multi-shot text-to-video as the primary production route because it provides weaker control over exact characters, props, scene composition, historical detail and editorial shot boundaries. Both support short per-shot video clips so that a failure can be regenerated locally rather than invalidating a long sequence.

Both reports also identify over-conditioning as a likely source of instability: too many simultaneous references, intermediate keyframes, depth/canny passes, style adapters and video guides can compete. The new baseline should use the minimum conditioning that demonstrably works.

## Recommendation 1 — selected primary workflow

### Anchored storyboard + per-shot Wan video

**Approach:** Hybrid B → C.

**Image / storyboard stage**
- Start from approved character, location and prop references.
- Evaluate Qwen-Image-Edit-2511 with the fal Qwen-Image-Edit-2511-Multiple-Angles-LoRA and ComfyUI-qwenmultiangle camera node for controlled shot/framing variations.
- Use the existing xworld_v2 style LoRA only if a controlled compatibility test confirms that it works with the selected Qwen image checkpoint. Do not assume a LoRA trained for Qwen-Image-2.1 transfers to Qwen-Image-Edit-2511.
- Treat the Next-Scene LoRA as optional until compatibility is demonstrated: its published model card identifies Qwen-Image-Edit-2509 as its base, not 2511.
- Approve the still/keyframe before video generation. Generate an end keyframe only when the action needs a defined destination; do not create two frames for every simple motion.

**Video stage**
- Use Wan 2.2 Fun InP for shots whose start and end states both matter; use a single-start-frame I2V workflow for simpler motion.
- Test the 5B InP/Control variants first as the efficient local candidate. Do not assume the 5B model is trivial to run: verify actual local memory and execution requirements.
- Compare against the 14B Fun InP workflow only if the 5B result fails the quality/control test. The official ComfyUI 14B Fun InP workflow documents 4-step LightX2V acceleration, but also warns that some video dynamics are lost with the accelerated LoRA. Therefore 4-step is an option to benchmark, not an unconditional default.
- Generate shots independently, normally around 5 seconds; allow longer clips only when the story/action requires it. Do not chain unrelated shots as one generation.
- Use start/end frames only for an actual continuous action or camera transition. Adjacent edited shots can use separate I2V jobs.

**Stills and maps**
- Keep composed illustrations and maps out of video diffusion by default.
- Generate/prepare the still or map, then use local deterministic 2.5D parallax/pan/zoom (e.g. DepthFlow or an already-supported local equivalent).
- Preserve the project's flexible 60% cinematic video / 30% composed visual / 10% map target.

**Dialogue**
- Preserve the existing narration, TTS and audio-timing responsibilities.
- Do not make a separate heavy lip-sync model mandatory for every dialogue shot. Evaluate local InfiniteTalk/S2V only for shots where visible mouth synchronization materially improves the scene. Use a static/reaction/OTS cut when it is sufficient.
- Keep audio generation and editing separate from visual motion generation; never let a visual prompt invent spoken dialogue or subtitles.

### Important limitations to validate

- Qwen-Image-Edit-2511 is a 20B model family and is not a lightweight model. Keep it only if its edit/reference/camera-control benefits justify the local resource cost. If it does not, compare against the existing Qwen-Image-2.1 route or a smaller supported image model.
- The 96 camera positions described by the Multi-Angles LoRA are not 96 deterministic physical 3D camera renders. The ComfyUI node emits camera prompt strings; the LoRA then performs learned image generation/editing. Expect approximate learned viewpoint changes, not guaranteed geometric correctness.
- The published Next-Scene LoRA is based on Qwen-Image-Edit-2509. Its compatibility with 2511 is not established by its card. Do not stack it with the Multiple-Angles LoRA in the baseline without an ablation test.
- The existing xworld_v2 LoRA is trained for the current Qwen route; 2511 compatibility must be tested, not presumed.
- Wan 2.2 Fun InP 14B has an official start/end-frame ComfyUI workflow. Its 4-step acceleration trades some motion dynamics for speed. The 5B Fun InP model exists, but local memory/runtime claims must be measured in the actual workflow.
- A two-frame bridge is not a general identity encoder. Keyframes help constrain composition and transition, but the video model can still drift. Measure character continuity across clips.

## Recommendation 2 — selected secondary workflow

### Per-shot Wan control-video generation

Use the same approved start image and shot description, but provide one control-video modality for difficult actions:
- OpenPose/DWPose for human body movement;
- Depth or Canny for spatial/blocking guidance;
- camera-control preset for camera-only movement;
- trajectory drawing only where the installed implementation and model checkpoint support it.

Preferred starting point: Wan 2.2 Fun Control 5B if it meets the quality/compatibility test; compare 14B only where necessary. Wan 2.2 Fun Control's documented input controls include Canny, Depth, OpenPose and trajectory.

Wan-Move / Wan-ATI can be evaluated as a specialized trajectory option, but do not make it part of the default pipeline until its exact Wan checkpoint, ComfyUI wrapper, model weights and local inference path are verified. The official ATI implementation referenced in the study is built on Wan 2.1 and uses a 14B I2V base; do not describe it as a native small Wan 2.2 plugin.

The secondary workflow is not a universal stack. It is selected per shot when the baseline cannot express a clear action or camera move.

## Rejected as default

- **Pure multi-shot text-to-video:** too little editorial and scene control for the main historical narrative.
- **StoryMem / ShotDirector / MultiShotMaster:** the reports identify major operational, VRAM, code/weight-availability or multi-character limitations. Keep as research, not the production baseline.
- **Blender clay playblast + LTX-2.5 22B Layout-to-Render:** the PDF proposes this as its alternative, but it reintroduces the heavy Blender/LTX path we are trying to simplify. Keep Blender only as an optional tool if a specific shot cannot be controlled adequately in 2D.
- **Three or more interior video keyframes plus multiple reference sheets and multiple control passes in one job:** not the default. Avoid conditioning conflicts.
- **Video diffusion for maps and composed illustrations:** use deterministic local 2.5D motion by default.

## Cost interpretation

The two studies give different modelled costs and retry assumptions. One estimates roughly $0.16–$0.83 per accepted minute for its selected routes; the PDF reports a different cost range and a different 60-second shot mix. These are modelled estimates, not a verified Explainer Engine production result. Do not copy them into budgets as facts. The implementation must log actual local generation time, retries, failures and accepted output.

## Local-only operating requirement

- Default generation must run locally through the existing ComfyUI/local model setup and local scripts.
- Use the existing local .env configuration for paths and local service addresses where present. Inspect variable names and dependencies; never print, commit or expose secret values.
- Do not use hosted fal.ai, hosted image/video APIs, paid inference endpoints or paid cloud GPUs as the default.
- If a model cannot run through the current local environment, report the exact blocker and propose a free local alternative. Do not silently switch to paid hosting.
- Model weights and ComfyUI workflows must be local files; do not commit large model weights to Git.
- Check model and adapter licences separately. Open weights do not mean every third-party LoRA or node has the same licence.

## 60-second pilot

Run one controlled 60-second sequence using the same story, character references, style target and shot descriptions for the primary and secondary workflows.

Use approximately 12 shots following the project's target mix:
- 7 video shots (about 35 seconds);
- 4 composed still/illustration shots (about 20 seconds);
- 1 map shot (about 5 seconds).

Include an establishing shot, a two-character interaction, dialogue coverage, a clear action with cause and result, a transition and a concluding shot.

Score both workflows on:
1. story and cause/effect continuity;
2. character identity across shots;
3. location/prop continuity;
4. action accuracy;
5. camera/composition compliance;
6. accepted generation rate and retries;
7. total local runtime and manual effort.

Do not grade primarily on hyperrealism. Do not claim cost-per-minute or reliability figures until this pilot produces measured data.

## Research references checked

- Qwen-Image-Edit-2511 model card: https://huggingface.co/Qwen/Qwen-Image-Edit-2511
- Qwen Multiple-Angles LoRA: https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA
- Qwen multi-angle ComfyUI node: https://github.com/jtydhr88/ComfyUI-qwenmultiangle
- Next-Scene LoRA and its 2509 base: https://huggingface.co/lovis93/next-scene-qwen-image-lora-2509
- Wan 2.2 Fun InP official ComfyUI guide: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-inp
- Wan 2.2 Fun Control official ComfyUI guide: https://docs.comfy.org/tutorials/video/wan/wan2-2-fun-control
- Wan 2.2 Fun 5B InP weights: https://huggingface.co/alibaba-pai/Wan2.2-Fun-5B-InP
- ByteDance ATI implementation (Wan 2.1-based): https://github.com/bytedance/ATI
