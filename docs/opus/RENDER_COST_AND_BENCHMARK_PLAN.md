# Render Cost and Benchmark Plan

**Status:** target budget is creator-set; prices and render times are volatile or unmeasured.  
**Goal:** find the cheapest repeatable route to an accepted 1440p Ink Chronicle episode.

## 1. Budget definition

The creator's target is **US$10–15 per finished 12–15-minute episode**. Opus must define and report two totals:

1. **Per-episode visual cash cost:** Blender render compute, cloud boot/setup billing, storage, egress, render retries, required upscale and any per-episode paid visual assets.
2. **Fully loaded episode cost:** the above plus amortized reusable-asset creation, asset/model acquisition, paid visual tooling, narration, dialogue, music and other production costs.

Do not claim the total episode costs $10–15 if only GPU rental fits. Show one-time reusable-library creation separately and report its amortization over a clearly stated number of episodes. Voice/music costs remain separate ledger lines unless the creator changes the scope.

No budget is proven until actual billing rows and completed-job manifests are compared.

## 2. Frame math

For 24 fps:
- 12 minutes: `12 × 60 × 24 = 17,280` output frames.
- 15 minutes: `15 × 60 × 24 = 21,600` output frames.

If every output frame were a full render, GPU hours would be:

`GPU hours = output frames × measured seconds per frame / 3600`

That is an intentionally conservative reference, not the desired implementation. The 10/30/60 lanes have different work:
- VIDEO: continuous 3D frame sequence.
- STILL: one or a few composed scene renders plus only the necessary motion/render passes; test whether a cheaper tableau/cache strategy preserves the approved look.
- HELPER: data-driven maps/charts/text; geometry/data may be generated cheaply by Python, then rendered/composited through the shared Ink Chronicle route. Opus must benchmark the actual chosen path.

Cost:

`episode render cash = billed GPU hours × actual GPU $/hour + billed boot/setup + storage + egress + retry cost + required upscale`

Measure billed time, not just Blender's reported render time.

## 3. Provider options — compare, do not assume

Indicative public price observations on 2026-11-04 (not guaranteed quotes):

| Option | Indicative observation | Why it matters | Main risk / TODO |
|---|---:|---|---|
| Vast.ai RTX 3090 | Live low around $0.148/GPU-hour; observed spot low around $0.121; some price trackers show a much higher market median around $0.25 | Potentially cheapest NVIDIA route | Host quality, stock, storage/egress, interruption, setup and data persistence vary by host; obtain live quote before every job |
| Vast.ai RTX 4090 | Live low around $0.309/GPU-hour; observed spot low around $0.280; other trackers report higher market medians near $0.48 | Potentially better throughput while remaining cheap | Do not budget from a single low listing; record host ID, reliability and full bill |
| RunPod RTX 3090 / 4090 | Pricing page updated 2026-10-28 lists approximately $0.50/h and $0.89/h respectively in the displayed pod price table | More predictable provider UX and established project tooling | Confirm Community vs Secure rate at deployment; fixed price may be higher than marketplace |
| RunPod A40 / RTX A6000 | Approximately $0.59/h on the same displayed table | Higher-memory alternative for scenes exceeding 24GB VRAM | Could be slower or more expensive per accepted frame; benchmark |
| Local M4 Pro, 24GB unified memory | No GPU-rental invoice; actual time and thermal throughput unknown | Free local preview / potential final render | Blender's current recommended macOS memory is 32GB; this machine has 24GB. Do not assume full-episode throughput or memory headroom |
| SheepIt | Free distributed community Blender render farm; points determine queue priority, and points are earned by contributing render work | Can reduce cash cost for non-urgent frames | No predictable deadline/SLA; projects can pause when point balance becomes too negative. Treat as optional secondary capacity only |

Price sources:
- Vast live comparison observed 2026-11-04: https://munkhbayarbr.github.io/gpu-radar/
- Vast vendor explanation that price varies by marketplace/availability and updates hourly: https://vast.ai/article/how-much-does-it-cost-to-rent-a-gpu-in-the-cloud-live-pricing-guide
- RunPod official pricing page (updated 2026-10-28): https://www.runpod.io/pricing
- Blender hardware requirements: https://www.blender.org/download/requirements/
- SheepIt FAQ / points and distributed model: https://client.sheepit-renderfarm.com/faq and https://api.sheepit-renderfarm.com/faq

Use live provider prices at execution time. Track lowest, median and actual booked price separately. Add storage, bandwidth, volume and setup fees. A spot/interruptible price is not a guaranteed job price.

## 4. Smart render optimization candidates

All values below are settings to test, not blanket defaults.

### 4.1 EEVEE first; Cycles selectively
- Evaluate EEVEE as the default candidate for stylized NPR rendering because it is rasterization-based, designed for speed/interactivity and supports high-quality final renders.
- Use Cycles only where a shot visibly benefits from effects that EEVEE cannot deliver adequately and the extra cost is justified.
- Workbench may be used for layout/preview, never silently substituted for the approved Ink Chronicle final look.
- Avoid default use of expensive volumetric shadows and complex volumes.

### 4.2 Render scale
Benchmark the same shots at:
- 100% = native 2560×1440;
- 75% = 1920×1080, 56.25% of native pixel count;
- 67% = approximately 1715×965, 44.89% of native pixel count.

75%/67% scale is not automatically acceptable. Thin ink lines, small faces, texture strokes and typography can soften or shimmer after upscale. Use native 1440p for hero close-ups if the lower profile fails visual QA. Add text/labels after upscale or as high-resolution geometry if needed.

### 4.3 Geometry / scene simplification
Benchmark:
- Geometry Nodes instances for repeated troops, crowd members, props and modular buildings;
- camera-frustum and distance culling;
- lower subdivision and texture-size limits for distant objects;
- avoid realizing instances unless unique geometry is required;
- reduce shadow rays, samples and volume resolution where the look remains stable;
- bake rigid-body, cloth, particle and other expensive simulations once;
- use low-cost cards/particles for distant dust, fire and debris;
- split foreground hero geometry from distant background geometry.

### 4.4 Cache and incremental rendering
- Cache by full render dependency hash.
- Store completed frame ranges and per-shot manifests.
- Retry only missing/failed frames.
- Do not rerender unchanged scenes.
- Record cache-hit ratio, invalidation cause and actual retry multiplier.
- Test frame-range resume after an intentionally interrupted job.

### 4.5 Upscaling
- Test spatial Lanczos/standard upscaling and a conservative temporal AI upscale as separate options.
- Creative AI upscaling is not the default because it can hallucinate detail and cause temporal flicker.
- Do not add interpolation unless a frame-rate test proves it helps and the 24fps output remains consistent.
- AI upscale cost and GPU time must be in the budget.

## 5. Required reproducible benchmark

Build three benchmark scenes from reusable approved assets:
1. **Hero close-up / dialogue:** face, eyes, mouth shapes, costume, ink outlines, DOF, key/fill/rim lighting.
2. **Council/interior tableau:** architecture, multiple characters, candle/window lighting, atmosphere, foreground/midground/background.
3. **Large battle / tactical diorama:** terrain, instanced army, moving camera, dust/smoke, long visible geometry and line art.
4. Add one small **HELPER map/chart** scene and one **STILL 2.5D tableau** to test lane-specific savings.

For each scene test:
- local M4 Pro;
- Vast RTX 3090 and RTX 4090 (actual host and invoice recorded);
- RunPod RTX 3090/4090 or A40/A6000;
- SheepIt as an optional queue/quality check if compatible with project requirements.

Test render profiles:
- EEVEE 100%, 75%, 67%;
- low/medium/high sample settings;
- volumes on/off or card-based alternatives;
- instancing/culling on/off;
- cached vs cold run;
- full frame vs resumed frame range.

Record:
- Blender version, build, engine and device;
- .blend and asset hashes;
- resolution and scale;
- sample/shadow/volume settings;
- frame range and frame count;
- median, p90 and max seconds/frame;
- scene-build time, startup/boot/download time;
- peak RAM/VRAM;
- file size, storage and egress;
- billed GPU time and invoice;
- failed frame count, retries and recoverability;
- image-quality review at 100% and final playback speed.

## 6. Cost scenarios Opus must calculate

At minimum calculate:
- 12-minute / 15-minute output;
- all-frames full render as an upper-bound baseline;
- 60% full VIDEO + optimized STILL + HELPER paths;
- 100% native 1440p vs 75% and 67% with validated upscale;
- low-price marketplace vs median-price marketplace vs RunPod;
- no-retry vs measured retry overhead;
- asset-reuse episode 1 vs episode 5/10 amortized costs.

Use measured seconds/frame by scene class, not one average from a simple cube test.

## 7. Go / pivot criteria

**GO** only if:
- visual review accepts the Ink Chronicle style at final 1440p playback;
- the system can complete the full representative pilot at 24fps without missing frames or broken continuity;
- measured visual cash cost fits $10–15 for the agreed 12–15-minute scope, or the creator explicitly accepts the quantified gap;
- resumable rendering and cache invalidation work;
- no unapproved paid job or uncontrolled storage remains.

**PIVOT** if cost exceeds target:
1. reduce 3D workload in STILL/HELPER before weakening VIDEO hero shots;
2. use 2.5D tableaux and low-cost helper geometry;
3. move non-hero rendering to a cheaper GPU provider;
4. render distant elements at lower geometry/texture/sampling cost;
5. increase reuse and remove redundant shots;
6. only then consider a lower resolution or alternate visual path, with creator approval.

Do not pivot to mixed final art styles to save money.
