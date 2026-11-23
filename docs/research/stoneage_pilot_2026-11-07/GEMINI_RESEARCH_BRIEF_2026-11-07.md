# Claude Research & Implementation Brief

## Qwen-Image-2.1 editing pipeline: style retention, camera control, scene consistency, LoRA integrity

**Prepared:** 2026-11-07\
**Project:** CrossWorld Chronicles / explainer-engine\
**Purpose:** Give Claude one self-contained, evidence-led brief to audit
the existing implementation, validate the research findings, and propose
the smallest safe improvements.\
**Priority:** Diagnose before changing architecture. Preserve working
components.

------------------------------------------------------------------------

# 1. Your role and operating rules

Act as a senior ML systems engineer specializing in diffusion/flow
models, Qwen image models, LoRA training and inference, Blender-based
scene production, and reproducible GPU experiments.

You must inspect the actual repository and the supplied project files
before recommending or changing code. Do not assume that the findings in
this brief are correct merely because they are written here. Verify
every important claim against the current code, model cards, issues,
pull requests, and pinned dependency versions.

## Mandatory rules

1.  **Do not replace the current architecture by default.** Prefer
    diagnosis, reuse, and incremental extension.
2.  Do not modify production code before presenting a concise audit and
    a proposed change list.
3.  Preserve current behavior unless a test demonstrates that it is
    wrong.
4.  Do not invent repository paths, class names, model capabilities,
    compatibility, benchmark results, costs, or API parameters.
5.  Separate:
    -   verified facts from primary sources;
    -   observations from the supplied project logs/images;
    -   hypotheses that still need testing;
    -   recommendations;
    -   implementation decisions.
6.  Treat Qwen-Image-2.1, Qwen-Image-Edit-2509, and Qwen-Image-Edit-2511
    as distinct model variants. Never assume their LoRAs or pipelines
    are interchangeable.
7.  If a proposed change depends on a version, commit, or model
    revision, pin and record it.
8.  Do not silently discard failed tests or hide warnings. Report them.
9.  Do not change multiple variables in one experiment.
10. Do not claim a quality improvement without an A/B comparison using
    the same input, seed, dimensions, prompt, and evaluation criteria.
11. Do not spend GPU credits on a test that can first be answered by
    inspecting code or checkpoint tensors.
12. If evidence is incomplete, state exactly what is missing and request
    only the necessary artifact.

## Required comparison format

For every significant proposed change, use:

-   CURRENT
-   NEW
-   KEEP
-   CHANGE
-   REMOVE
-   TRADE-OFFS
-   RECOMMENDATION

Before implementation, provide a short decision report. Do not implement
major architecture changes until the user approves them.

------------------------------------------------------------------------

# 2. Project context and current architecture

The project creates stylized historical animated scenes for CrossWorld
Chronicles. Blender is used for 3D scene layout and camera placement;
Qwen-Image-2.1 is used to convert rendered scenes into a consistent
hand-drawn 2D cartoon look; LTX-2.5 may later animate selected images.

## Current high-level pipeline

``` text
Blender 3D scene / camera / object placement
        |
        v
Blender render (usually 1280x720 input intent)
        |
        v
Qwen-Image-2.1 edit pipeline
  - Image 1: scene/layout reference
  - optionally Image 2: painted master/style reference
  - xworld_v2 LoRA
  - prompt describing composition and style
        |
        v
Stylized 2D cartoon image
        |
        v
LTX-2.5 image-to-video for selected shots
```

## Current model and inference details from the supplied brief

-   Base model: Qwen-Image-2.1.
-   Custom LoRA: `xworld_v2`.
-   LoRA trained with `ostris/ai-toolkit`.
-   Training checkpoint of interest: step 3000, file referred to as
    `xworld_v2_000003000.safetensors`.
-   LoRA weight currently tested: 0.7 and 1.0.
-   VideoX-Fun Qwen-Image-2.1 pipeline is used or evaluated.
-   GPU environment: Modal, A100-80GB; H100 may also be considered.
-   Dtype: bf16.
-   Model CPU offload is used.
-   Inference: 30 steps in the current setup; true CFG scale 2.5.
-   Intended dimensions: 1280x720, but the pipeline rounds to multiples
    of 32, resulting in 1280x704.
-   Later stage: LTX-2.5 for selected image-to-video shots.

**Important:** Treat these values as the state described in the supplied
project brief. Confirm them against the current repository and actual
launch configuration before editing anything.

------------------------------------------------------------------------

# 3. Problems to investigate

The initial problem brief identifies five areas. Keep these IDs in your
audit and report.

## P1 --- LoRA style fade / realism drift

Observed behavior:

-   The desired output is a hand-drawn 2D cartoon.
-   At LoRA weight 0.7, the result appears more illustrative, but can
    become noisy or over-sharpened.
-   At weight 1.0, images can become cleaner, but some
    subjects---especially mammoths---drift toward smooth,
    realistic/3D-looking surfaces.
-   Edge density and Laplacian variance appear to fall for some cave
    inputs.
-   Snow, sky, fur, and other textured regions can become excessively
    noisy.
-   The intended style uses bold/uneven outlines, simplified shapes,
    expressive caricature faces, flat/matte colors, and painterly
    backgrounds.

Do not assume that changing LoRA weight alone solves this. Determine
whether the issue comes from: - incomplete or incorrect LoRA training; -
missing or weak adapters in specific Transformer modules; - wrong base
model loading or state-dict conversion; - training captions or trigger
mismatch; - reference-image conditioning overpowering the LoRA; - prompt
conflicts; - image preprocessing/resolution; - CFG or sampler
settings; - differences between subject categories and training
distribution.

## P2 --- Camera-angle changes are not reliable

Observed behavior:

-   Qwen often returns a near-copy of the original front-facing
    composition instead of a genuinely new camera view.
-   Prompts such as left view, right view, and back view are not
    consistently respected.
-   Character turnarounds sometimes work, but full scenes do not
    reliably rotate the camera.
-   Blender can already produce the intended camera angle and is
    deterministic.

Do not treat natural-language camera instructions as a reliable 3D
camera-control mechanism. Determine which responsibilities belong in
Blender and which can reasonably belong to Qwen.

## P3 --- Scene/layout drift

Observed behavior:

-   Hut count, hut placement, characters, and relative positions may
    change.
-   Similar objects can merge (for example, a mammoth and a boulder).
-   The output may fail to preserve the scene graph implied by Blender.
-   Text labels such as A1/B2/C1 are not guaranteed to behave as
    persistent object IDs.

Investigate mask-based local editing, Blender object masks/IDs,
depth/lineart conditioning, and inpainting. The goal is to keep
geometry, object count, and placement under deterministic control
instead of relying on prose.

## P4 --- LoRA merge warnings / fused `gate_up`

The current custom merge path handles a fused `img_mlp.gate_up` adapter
by multiplying LoRA matrices, scaling the delta, and splitting the
result into two destination modules:

-   `img_mlp.gate_layer`
-   `img_mlp.proj`

The conceptual math is:

``` python
delta = (up @ down) * (alpha / rank) * sign
```

Then split the first and second halves of the output dimension into the
two target layers.

This is potentially correct only if: - the fused source tensor has the
expected `[gate; up]` ordering; - the source and destination dimensions
match; - the rank and alpha scaling are correct; - all matching adapter
keys are processed; - no keys are silently skipped; - the loaded base
weights correspond to the expected architecture.

Do not rewrite this code without inspecting the exact implementation and
tensor shapes.

## P5 --- Multiple reference-image roles

Current intended semantics:

-   Image 1: authoritative Blender scene/layout/camera reference.
-   Image 2: painted master used as a style reference.

But the current Qwen-2.1 pipeline may process both images as full image
conditions rather than separating "layout only" and "style only" roles.

Investigate: - whether Image 2 can be made style-only using prompt
instructions; - whether cropped style-reference boards are less
compositionally invasive than full painted frames; - whether image order
changes the outcome; - whether a supported control/adapter exists for
separate structure and style conditioning; - whether the model
architecture exposes per-image weights or masks.

Do not claim prompt wording guarantees style-only behavior unless
verified experimentally.

------------------------------------------------------------------------

# 4. High-priority research finding: AI Toolkit `img_mlp` LoRA issue

A particularly relevant issue was found in the `ostris/ai-toolkit`
repository:

-   Issue #1075: `img_mlp` `lora_B` tensors reportedly remain exactly
    zero for Qwen-Image-2.1.
-   Issue #1054: a separate report concerning zero/NaN gradients with
    gradient checkpointing and layer offload.
-   PR #1067 was also referenced in the initial research and must be
    checked for its actual code and resolution status.

Links: - https://github.com/ostris/ai-toolkit/issues/1075 -
https://github.com/ostris/ai-toolkit/issues/1054 -
https://github.com/ostris/ai-toolkit/pull/1067

The reported #1075 symptom: - Attention LoRA adapters reportedly trained
normally. - `img_mlp` adapters in 32 Transformer blocks reportedly had
all-zero `lora_B` tensors. - Loss could decrease while the relevant
adapters remained ineffective. - The issue discussion identified a
possible mismatch between fused `img_mlp.gate_up` and separate Diffusers
modules (`gate_layer` and `proj`). - A reported workaround was changing
the model identifier from a local Diffusers directory to the official
model ID:

``` yaml
name_or_path: "Qwen/Qwen-Image-2.1"
```

This was reported by an issue participant as fixing their particular
training path. It is **not proof** that the user's checkpoint has the
same defect.

## Required investigation

1.  Open Issue #1075, all relevant comments, linked PRs, and the exact
    code at the relevant commits.
2.  Inspect the user's actual AI Toolkit version/commit and training
    config.
3.  Inspect the actual checkpoint: `xworld_v2_000003000.safetensors`
4.  Group `lora_B` tensors by module:
    -   `img_mlp.gate_up`
    -   `img_mlp.out`
    -   attention
    -   all other modules
5.  For each group report:
    -   tensor count;
    -   fully zero tensor count;
    -   zero-element fraction;
    -   min/max/mean absolute value;
    -   NaN/Inf count;
    -   key names and tensor shapes.
6.  Compare the checkpoint keys and shapes with the base model expected
    by the current inference code.
7.  Check if the base model was loaded from an official model ID or
    local Diffusers directory.
8.  Check missing/unexpected keys and conversion warnings during
    training and inference.
9.  Determine whether the custom merge code can correctly consume the
    checkpoint.
10. If the relevant tensors are zero, do not attempt to fix the style
    with a higher LoRA weight. Establish whether retraining is required.

### Diagnostic script (adapt paths and naming to the actual checkpoint)

``` python
from collections import defaultdict
from safetensors.torch import load_file
import torch

path = "xworld_v2_000003000.safetensors"
sd = load_file(path, device="cpu")

groups = defaultdict(list)

for key, value in sd.items():
    if not key.endswith(".lora_B.weight"):
        continue

    if ".img_mlp.gate_up." in key:
        group = "img_mlp.gate_up"
    elif ".img_mlp.out." in key:
        group = "img_mlp.out"
    elif ".attn." in key:
        group = "attention"
    else:
        group = "other"

    groups[group].append((key, value.float()))

for group, items in sorted(groups.items()):
    zero_tensors = sum(torch.count_nonzero(v).item() == 0 for _, v in items)
    total = torch.cat([v.flatten() for _, v in items])

    print(
        group,
        "tensors:", len(items),
        "zero tensors:", zero_tensors,
        "zero fraction:", round((total == 0).float().mean().item(), 6),
        "max abs:", total.abs().max().item(),
        "nan:", torch.isnan(total).sum().item(),
        "inf:", torch.isinf(total).sum().item()
    )
```

Do not assume all checkpoints use exactly these key suffixes. First
print and inspect actual keys. Adapt the grouping logic to the
checkpoint's real naming convention. Avoid loading the full base model
just to inspect the LoRA checkpoint.

------------------------------------------------------------------------

# 5. P4 technical analysis: fused `gate_up` merge

The initial research found that the AI Toolkit Qwen-2.1 implementation
uses a fused `img_mlp.gate_up` layer, while a VideoX-Fun implementation
uses separate layers named `gate_layer` and `proj`.

Relevant repositories: - https://github.com/ostris/ai-toolkit -
https://github.com/aigc-apps/VideoX-Fun

A representative fused structure:

``` python
self.gate_up = nn.Linear(hidden_size, 2 * mlp_hidden_size, bias=False)

gate, up = self.gate_up(hidden_states).chunk(2, dim=-1)

return self.out(self.activation_fn(gate) * up)
```

A representative split structure:

``` python
self.out(
    self.activation_fn(self.gate_layer(hidden_states))
    * self.proj(hidden_states)
)
```

The conceptual split is valid only if the concatenation order and
dimensions are exactly as expected.

## Required validation in the merge implementation

-   Verify actual source and destination state-dict key names.
-   Verify source `gate_up` output dimension equals the sum of
    destination `gate_layer` and `proj` output dimensions.
-   Verify input dimensions match.
-   Verify source ordering (`gate` first, `up` second) against the exact
    model implementation.
-   Verify rank and alpha scaling.
-   Verify whether `alpha/rank` or another scaling convention is used by
    the actual checkpoint/training configuration.
-   Verify sign convention and merge strength.
-   Verify dtype conversion does not overflow or silently cast
    incorrectly.
-   Count all matched, merged, skipped, and unexpected keys.
-   Assert finite deltas and correct shapes.
-   Compare a reference implementation or mathematically equivalent
    forward pass on a small tensor if possible.
-   Do not treat "32 keys found" as proof that 32 adapters were
    successfully merged.
-   Report zero-delta adapters separately from missing adapters.

Possible validation assertions (adapt to actual object names):

``` python
assert up.shape[0] == (
    ff.gate_layer.weight.shape[0] + ff.proj.weight.shape[0]
)

assert down.shape[0] > 0
assert torch.isfinite(delta).all()

assert delta.shape == (
    ff.gate_layer.weight.shape[0] + ff.proj.weight.shape[0],
    ff.gate_layer.weight.shape[1]
)
```

Do not replace the custom merge with PEFT unless evidence shows that the
existing approach is incorrect or materially harder to maintain.

------------------------------------------------------------------------

# 6. P1: style retention and reference-image conditioning

The initial code inspection suggests that the Qwen-2.1 pipeline
processes reference images through both: - Qwen3-VL image/text
conditioning; - VAE image latents.

The VideoX-Fun Qwen-2.1 pipeline source must be inspected at the exact
pinned commit and compared with the user's actual pipeline. Do not
assume all branches or versions are identical.

Relevant code to inspect: -
https://github.com/aigc-apps/VideoX-Fun/blob/main/videox_fun/pipeline/pipeline_qwenimage21.py -
https://github.com/aigc-apps/VideoX-Fun -
https://github.com/huggingface/diffusers

Potential explanation to test: - A photorealistic Blender render carries
not only geometry/layout but also texture, lighting, shading, and
surface appearance. - If that reference enters both semantic and VAE
latent conditioning, it may pull the output toward the original render's
visual character. - The LoRA then competes with this conditioning rather
than receiving an isolated structure-only input.

This is a plausible architecture-based hypothesis, not yet a proven
cause of the user's mammoth style drift.

## Experiments to isolate style loss

Keep the same: - scene; - camera; - seed; - dimensions; - prompt; -
inference steps; - scheduler; - CFG; - LoRA checkpoint and weight.

Change one factor at a time:

A. Current Blender render as Image 1, no Image 2.\
B. Same Image 1 plus full painted master as Image 2.\
C. Same Image 1 plus cropped style-reference board as Image 2.\
D. Structure-only lineart/depth control instead of photorealistic image
conditioning, where supported.

Measure and visually assess: - outline strength and consistency; -
flat/matte color behavior; - shape simplification; - mammoth and human
silhouette consistency; - texture noise; - composition preservation; -
unwanted 3D shading; - subject count and placement.

Do not use edge density or Laplacian variance as the only quality
metrics. They can help identify differences but cannot independently
determine whether an image is stylistically correct.

## Style prompt

The following is only a candidate test prompt. Compare it with the exact
captions used to train `xworld_v2`; do not invent a new style tail
before reading the training data.

``` text
xworld style, hand-drawn 2D cartoon illustration,
bold uneven black ink outlines, flat matte colours,
simplified shapes, expressive silhouettes,
chalky painterly background, limited texture,
no realistic surface shading, no glossy 3D appearance.

Image 1 defines the complete scene layout, camera,
object count, relative positions and poses.
Preserve the composition and all subjects.
```

Investigate whether a consistent training caption tail and trigger
phrase were used. If they were, test that exact text rather than
assuming a new phrase is better.

------------------------------------------------------------------------

# 7. P2/P3: Qwen-Image-2.1 Fun ControlNet Union

A promising candidate found in the initial research:

https://huggingface.co/alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union

The initial research identified it as a Qwen-Image-2.1-specific
ControlNet branch. Verify the current model card, license, architecture,
supported pipeline, model revision, and exact loading instructions
before using it.

The reported supported control types include: - Canny - Depth -
Grayscale - HED - Lineart - MLSD - Pose - Scribble

The branch also reportedly supports inpainting.

Relevant VideoX-Fun examples: -
https://github.com/aigc-apps/VideoX-Fun/blob/main/examples/qwen_image_21/model_inference/Qwen-Image-2.1-Fun-Controlnet-Union.py -
https://github.com/aigc-apps/VideoX-Fun/blob/main/examples/qwen_image_21/model_inference/Qwen-Image-2.1-Fun-Controlnet-Depth.py -
https://github.com/aigc-apps/VideoX-Fun/blob/main/videox_fun/pipeline/pipeline_qwenimage21_control.py -
https://github.com/aigc-apps/VideoX-Fun/blob/main/videox_fun/models/qwenimage21_transformer2d_control.py

Initial model-card parameters observed in the research: -
`control_context_scale = 1.0` - `guidance_scale = 1.0` -
`num_inference_steps = 40`

Verify these against the current official model card and example before
implementation. Do not blindly carry the current pipeline's
`true_cfg_scale=2.5` into a distilled ControlNet workflow.

The initial code inspection of the VideoX-Fun control pipeline showed: -
control image latents are encoded; - a mask and inpaint-image latents
can be concatenated into a control context; - control context is passed
to the Transformer; - the pipeline disables its condition KV cache when
`control_context` is present.

This may increase inference cost. Measure actual latency and peak VRAM
rather than estimating from model size alone.

## Why this may help

Current path:

``` text
Photorealistic Blender render
        |
        v
Qwen image edit + style LoRA
```

Candidate path:

``` text
Blender scene
        |
        +--> Lineart pass
        |
        +--> Depth pass
        |
        v
Qwen-Image-2.1 + ControlNet Union
        |
        +--> xworld_v2 LoRA (after validating it)
        |
        v
Stylized image
```

The goal is to separate structural control from the appearance of the
photorealistic Blender render.

This is a hypothesis to test. Do not claim that ControlNet will
automatically preserve the desired cartoon style. Compare outputs under
controlled conditions.

## Blender passes to consider

-   lineart / outlines;
-   depth;
-   object masks or Cryptomatte;
-   pose/skeleton pass if useful;
-   optional grayscale pass.

Do not build all passes before the first minimal experiment. Start with
lineart and depth only.

------------------------------------------------------------------------

# 8. P2: Multi-angle LoRA research --- compatibility warning

Two relevant model cards were identified:

1.  Qwen-Edit-2509 Multiple Angles:
    https://huggingface.co/dx8152/Qwen-Edit-2509-Multiple-angles

2.  Qwen-Image-Edit-2511 Multiple Angles:
    https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA

The 2511 model card reportedly describes: - training on more than 3,000
Gaussian Splatting renders; - 96 camera positions; - 8 azimuth
directions; - 4 elevation levels; - 3 distance levels; - a `<sks>`
trigger; - example camera prompts such as:

``` text
<sks> front view eye-level shot medium shot
<sks> right side view high-angle shot close-up
<sks> back view low-angle shot wide shot
<sks> front-left quarter view elevated shot medium shot
```

The 2509 card reportedly describes natural-language camera movement
instructions and notes consistency limitations.

**Critical:** These are not Qwen-Image-2.1 LoRAs unless their authors
explicitly establish that compatibility. They must not be loaded into
the Qwen-2.1 pipeline without checking: - base model; - target module
names; - tensor shapes; - architecture differences; - LoRA format; -
license; - inference implementation.

The recommended production principle remains: - Blender owns camera
position and perspective. - Qwen owns visual stylization and image
synthesis. - Multi-angle LoRA is an optional isolated experiment, not
the main production camera system.

------------------------------------------------------------------------

# 9. P3: object identity, masks, and inpainting

Text identifiers such as `A1`, `B2`, and `C1` are not persistent object
handles inside Qwen. Do not rely on them for deterministic scene
editing.

Investigate Blender-generated: - object masks; - Cryptomatte; -
per-object segmentation; - depth; - lineart.

Suggested workflow for changing one subject:

``` text
Blender scene graph
    |
    +--> change selected object's transform
    |
    +--> render updated scene
    |
    +--> render object mask / Cryptomatte
    |
    +--> render depth or lineart
    |
    v
Qwen inpainting + structural control
    |
    v
Locally updated stylized image
```

The exact mask convention must be verified from the pipeline: - whether
white means preserve or regenerate; - whether masks are inverted; - how
masks are resized; - how mask values are thresholded; - how mask latent
dimensions are calculated.

Do not assume a convention based on another model or pipeline.

Acceptance criteria: - only the selected region changes; - other
characters remain stable; - object count is preserved; - new
pose/position matches Blender; - boundary artifacts are acceptable; - no
unrelated background regeneration.

------------------------------------------------------------------------

# 10. P5: multiple reference images

The current pipeline appears to pass reference images through both
semantic and latent image conditioning. Confirm this in the exact
current implementation.

The intended roles: - Image 1: authoritative scene layout, camera,
count, pose, and position. - Image 2: style donor only.

The model may not provide independent per-image semantic roles or
weights. Confirm from the actual implementation. If no such mechanism
exists, prompt wording alone cannot guarantee role separation.

Test these three conditions: 1. Image 1 only. 2. Image 1 + full painted
master. 3. Image 1 + cropped style-reference board.

The style board should contain small representative crops: - character
face; - linework; - flat color/shading; - background texture; -
silhouette/shape language.

Avoid a complete second scene if it introduces unwanted composition and
camera information.

Candidate prompt:

``` text
Image 1 is the authoritative shot layout and camera view.
Preserve its exact composition, perspective, object count,
relative positions, scale and poses.

Image 2 is a style reference only.
Use Image 2 only for its ink outlines, shape language,
colour palette, shading style and surface texture.

Do not copy Image 2's camera angle, framing,
perspective or object arrangement.

Keep every subject in the position defined by Image 1.
```

This prompt is an experiment, not a guarantee.

------------------------------------------------------------------------

# 11. Resolution and preprocessing audit

The initial code inspection found a resolution rounding behavior in the
VideoX-Fun Qwen-2.1 pipeline.

The pipeline appears to round width and height down to a multiple of:

``` python
multiple_of = self.vae_scale_factor * 2
```

With a VAE scale factor of 16, the multiple is 32.

Therefore: - 1280x720 becomes 1280x704; - 768x432 becomes 768x416.

The initial project brief says the user's validator checks divisibility
by 16. If that remains true, align validation with the actual pipeline's
multiple-of-32 constraint.

Suggested validation:

``` python
if any(v % 32 for v in j.get("size", [32, 32])):
    bad.append(
        f"{j['name']}: dimensions must be divisible by 32"
    )
```

Do not make this change until confirming the actual VAE scale factor and
pipeline implementation.

If 720 pixels is a hard output requirement, test a 736-pixel
intermediate height and crop to 720 after generation. Check composition
and crop safety. Do not silently stretch or distort the image.

The scheduler shift is reportedly calculated dynamically from target
latent sequence length. Do not modify it without evidence.

------------------------------------------------------------------------

# 12. Controlled experiment plan and cost discipline

The user wants small, reproducible experiments, ideally under
approximately \$1 of GPU cost each. The initial brief cites an A100-80GB
rate of \$2.50/hour. Treat that as a project-provided estimate, not a
guaranteed current Modal price. Verify actual workspace pricing and
billed runtime before claiming costs.

At \$2.50/hour: - 6 minutes = \$0.25; - 12 minutes = \$0.50; - 24
minutes = \$1.00.

These are arithmetic estimates excluding other charges. Measure real
runtime first.

## Experiment order

### E0 --- No-GPU checkpoint audit

Inspect `xworld_v2_000003000.safetensors`: - key names; - tensor
shapes; - zero/nonzero counts; - NaN/Inf; - module coverage; - `img_mlp`
vs attention.

**Do not spend GPU credits before this is complete.**

### E1 --- Training configuration audit

Inspect: - exact AI Toolkit commit/version; - exact model identifier and
local path; - model revision; - training configuration; - gradient
checkpointing; - layer offload; - target modules; - rank/alpha; -
learning rate; - optimizer; - training captions; - trigger; - image
dataset metadata; - training logs/warnings.

Determine whether #1075 or #1054 is applicable.

### E2 --- Baseline reproduction

Use one representative scene (prefer the scene where the style drift is
most visible) and reproduce the current output with recorded: - seed; -
dimensions; - prompt; - image inputs; - LoRA hash and weight; - base
model revision; - scheduler; - inference steps; - CFG; - package
versions; - GPU type; - runtime.

If baseline cannot be reproduced, stop and fix reproducibility before
comparing changes.

### E3 --- Style-only prompt/caption test

Only after validating the checkpoint: - current prompt; - exact training
trigger/caption tail; - LoRA weight 0.7; - LoRA weight 0.85; - LoRA
weight 1.0.

Change one variable per run.

### E4 --- Reference-image role test

-   Image 1 only;
-   Image 1 + full painted master;
-   Image 1 + cropped style board.

Keep everything else fixed.

### E5 --- ControlNet structural test

Use one Blender scene and compare: - lineart; - depth; - lineart + depth
only if supported by the official implementation.

Use the official model card's settings after verifying them. Record
runtime and peak VRAM.

### E6 --- Inpainting test

Change one object only. Use a verified mask convention and compare
before/after outside the mask.

### E7 --- Multi-angle LoRA compatibility test

Only after inspecting architecture and LoRA tensor keys. Do not mix this
with the ControlNet test.

## Evaluation rubric

Score each output from 1--5 on: 1. Style fidelity to the target art
direction. 2. Camera/perspective fidelity to Blender. 3. Object count
preservation. 4. Object position preservation. 5. Character
identity/shape consistency. 6. Outline consistency. 7. Color and shading
consistency. 8. Texture cleanliness. 9. Absence of unintended 3D
realism. 10. Suitability for later animation.

Also record: - runtime; - peak VRAM; - GPU billed cost; -
failure/warning logs.

A test is not a success just because it looks attractive. It must
satisfy the production constraints.

------------------------------------------------------------------------

# 13. Repository and source audit required from Claude

Inspect the actual repository branch and relevant files. Do not assume
the file names below are current; search the repository.

Known project references from the supplied context: -
`QWEN_PROBLEM_BRIEF_FOR_GEMINI.pdf` - `qwen_jobs.py` - current Qwen
inference runner / Modal launcher - custom LoRA merge implementation -
`xworld_v2_000003000.safetensors` - AI Toolkit training config and
logs - Blender render and style-reference assets - VideoX-Fun Qwen-2.1
pipeline - Qwen-2.1 ControlNet pipeline

The user has previously referenced the repository:
https://github.com/vano1919/explainer-engine

Inspect the exact working branch and working tree. Do not overwrite
unrelated changes.

## External sources to verify

-   Qwen-Image-2.1: https://github.com/QwenLM/Qwen-Image-2.1
-   VideoX-Fun: https://github.com/aigc-apps/VideoX-Fun
-   DiffSynth-Studio: https://github.com/modelscope/DiffSynth-Studio
-   Diffusers: https://github.com/huggingface/diffusers
-   AI Toolkit: https://github.com/ostris/ai-toolkit
-   AI Toolkit issue #1075:
    https://github.com/ostris/ai-toolkit/issues/1075
-   AI Toolkit issue #1054:
    https://github.com/ostris/ai-toolkit/issues/1054
-   AI Toolkit PR #1067: https://github.com/ostris/ai-toolkit/pull/1067
-   Qwen-Image-2.1 Fun ControlNet Union:
    https://huggingface.co/alibaba-pai/Qwen-Image-2.1-Fun-Controlnet-Union
-   Qwen Edit 2509 Multiple Angles:
    https://huggingface.co/dx8152/Qwen-Edit-2509-Multiple-angles
-   Qwen Edit 2511 Multiple Angles:
    https://huggingface.co/fal/Qwen-Image-Edit-2511-Multiple-Angles-LoRA

Also investigate the arXiv paper identified in the original research
brief: https://arxiv.org/abs/2508.02324

For every source, record: - exact URL; - commit or revision where
applicable; - date checked; - what it proves; - what it does not
prove; - relevance to this project's exact Qwen-2.1 setup.

Do not cite a repository README as proof of behavior that is only
visible in source code. Link the exact source file/line or commit when
possible.

------------------------------------------------------------------------

# 14. Deliverables required

Produce the following deliverables in order.

## Deliverable A --- Evidence-based audit

A concise but technically detailed report: - current architecture; -
P1--P5 status; - confirmed defects; - plausible causes; - unsupported
assumptions; - relevant external findings; - exact source links and
version information.

## Deliverable B --- Root-cause ranking

For each issue: - likely cause; - evidence; - confidence: high / medium
/ low; - cheapest validation step; - what result would confirm or reject
it.

## Deliverable C --- Proposed changes

Use this format:

  -------------------------------------------------------------------------------
  Priority   File/module   Current    Proposed   Reason     Risk       Test
                           behavior   change                           
  ---------- ------------- ---------- ---------- ---------- ---------- ----------

  -------------------------------------------------------------------------------

Do not modify code before this proposal is reviewed.

## Deliverable D --- Experiment matrix

Create a reproducible matrix with: - experiment ID; - input; - variable
changed; - fixed parameters; - expected result; - pass/fail criteria; -
estimated runtime; - estimated cost; - actual runtime/cost after
execution.

Keep GPU tests small. Start with no-GPU diagnostics.

## Deliverable E --- Implementation plan

Only after the user approves: - list exact files to change; - explain
what remains unchanged; - implement the smallest necessary patch; - add
assertions and diagnostic logs; - add tests; - run relevant tests; -
show diffs; - report failures honestly.

## Deliverable F --- Final recommendation

Choose one: 1. Keep current pipeline and fix LoRA/training defects. 2.
Keep current pipeline and add structural ControlNet conditioning. 3.
Hybrid Blender + ControlNet + LoRA + local inpainting. 4. Another
approach, but only if supported by evidence.

Explain why alternatives are rejected or deferred.

------------------------------------------------------------------------

# 15. Acceptance criteria

The audit is complete only when:

-   [ ] The current repository branch and relevant files have been
    inspected.
-   [ ] The actual LoRA checkpoint keys and tensor values have been
    inspected.
-   [ ] The applicability of AI Toolkit #1075 and #1054 has been
    determined.
-   [ ] The custom `gate_up` merge has been checked mathematically and
    against actual tensor shapes.
-   [ ] Qwen-2.1 vs Qwen-Edit-2509/2511 compatibility has been
    explicitly checked.
-   [ ] ControlNet Union compatibility and exact usage have been
    verified from current official sources/code.
-   [ ] Image 1/Image 2 conditioning behavior has been traced through
    the actual pipeline.
-   [ ] The resolution validation has been checked against the actual
    VAE/pipeline.
-   [ ] Every hypothesis has a low-cost experiment or is clearly marked
    unverified.
-   [ ] No major architecture replacement has been made without
    approval.
-   [ ] Proposed changes preserve existing working functionality.
-   [ ] Tests and acceptance criteria are explicit.

------------------------------------------------------------------------

# 16. First actions --- do these before anything else

1.  Inspect the repository branch, status, and current implementation.
2.  Locate the actual `xworld_v2_000003000.safetensors`, training
    config, training logs, and custom merge code.
3.  Run the no-GPU checkpoint tensor audit.
4.  Read AI Toolkit issue #1075 and #1054 and inspect the exact relevant
    code/PR.
5.  Determine whether the user's training path is affected.
6.  Report findings before changing anything.

**Do not start by rewriting the pipeline. Do not start by installing a
new model. Do not start by spending GPU credits. Diagnose the current
LoRA and merge path first.**
