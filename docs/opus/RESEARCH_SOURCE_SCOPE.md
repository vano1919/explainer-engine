# Research Source Scope and Evidence Register

**Purpose:** stop Opus from mixing the new Blender target with obsolete LTX, old raster-kit, or imported Master Mold material.

## 1. Primary internal research source

`docs/research/cinematic_audio_visual_craft_and_tool_implementation_report_2026_11_04.md`

Use the following parts as the principal research foundation:
- **C.1–C.5:** visual storytelling, camera/framing, lens/depth, lighting, animation principles, helper graphics.
- **D.1–D.2:** editing grammar and pacing.
- **F.1:** 20 scene archetypes and their intended sequence, camera, light, lane and sound.
- **I.1:** 12-minute audiovisual timing blueprint.
- **J.1, J.3–J.6, J.9–J.10:** 2.5D parallax, battle choreography concepts, shot/reverse-shot, rack focus, maps, forced alignment, sound bridges. Translate LTX-specific routes into deterministic Blender methods.
- **K:** QA and evidence gaps.
- **M–N:** Pure Blender alternative, bpy and render-system architecture.
- **O:** open source repository inventory; independently verify maintenance, license and technical compatibility before reuse.
- **Q.1–Q.5:** camera rig, Geometry Nodes army, painterly NPR, Rhubarb lipsync and tactical maps.
- **R:** 20 archetype and 8 example implementation ideas; reuse the scene/craft logic, not obsolete LTX renderer steps.
- **S.11–S.15:** reusable Blender action, NPR, facial sync, map and destruction techniques.
- **T:** comparison matrix; revalidate cost and performance claims.
- **U–X:** reusable 3D libraries, style unification, world variation, selected world archetypes.

## 2. Research findings worth carrying forward

- A shot needs a visual purpose; avoid literal “see-say” duplication of the narration.
- Establish geography before action; keep screen direction and 180-degree axis consistent.
- Use deliberate shot size: EWS/WS for geography, MWS/MS for physical activity, MCU/CU for emotion/dialogue, ECU for proof/details.
- Choose lens and camera position intentionally: wide 18–28mm, normal 35–50mm, telephoto 85–200mm as a starting vocabulary, not rigid defaults.
- True camera movement is different from digital zoom. Large orbit, crane-up/overhead and complex occlusion require real 3D.
- Physical actions need first pose, anticipation, action peak/contact and settle/follow-through.
- A reaction or consequence can carry more narrative value than another action angle.
- Use deterministic geometry/text for maps, dates, labels, charts and factual evidence.
- Use Geometry Nodes instances rather than duplicating repeated troops/building parts; avoid realizing instances unnecessarily.
- Use Blender NPR material/lighting/line-art as a shared style normalization layer.
- Use Rhubarb/visemes as a lip timing aid only; body/face acting still requires rig controls and animation.
- Use cache, headless frame ranges, baked simulation and per-shot profiles to control time and spend.
- Reuse an approved World Bible and asset library across episodes; every 3D asset needs provenance, license, dependencies and style version.

## 3. Internal claims that are NOT verified performance facts

The report mentions values such as:
- EEVEE 0.1–0.25 seconds/frame for some stylized scene options;
- EEVEE 0.3–1.2 seconds/frame for a proposed full animation lane;
- 0.2 seconds/frame for a tactical map;
- estimated percent reductions from Mixamo, BlenderProc, TRELLIS and other reusable tools.

Treat every such value as a **hypothesis or illustrative estimate** until reproduced on the project's real 1440p Ink Chronicle scenes, pinned Blender build and measured hardware. Do not put these values into a hard budget.

The proposed NPR pipeline using Shader-to-RGB, line-art and Kuwahara must be tested in the actual selected Blender release. Some nodes and behavior differ between engines and versions. Verify the Blender 5.2 API/docs for each node and feature before implementation.

## 4. Research that is legacy-only for this branch

Do not use these as production instructions:
- LTX-2.3 / LTX-2.5 generation constraints, local `8n+1` frame condition and provider API workflow.
- IC-LoRA motion control and first/last-frame conditioning as required visual pipeline.
- Qwen keyframes → LTX clips as the final VIDEO route.
- LTX-specific routes in hybrid workflows and worked examples. Keep the story/camera choreography only.
- The 4-tier visual route when it is designed around LTX/keyframe generation.
- Old 2D cutout puppet-rig system in `docs/research/ANIMATION_UNIVERSE_2026-10-22.md` if it conflicts with the new reusable 3D character system.
- Old Remotion-primary proposals; the current assembly code must be inspected directly.
- Imported `CLAUDE-MASTER-MOLD-SYNC` TODO blocks, the v2.1.0 execution guide and roadmap as general authority. The handoff warns that these are unverified and incomplete; do not implement their 301-file task set.
- Old cost/throughput claims not backed by the current run ledger or a reproduced Blender benchmark.

## 5. External technical sources to re-check

Use current official documents first:
- Blender EEVEE 5.2 manual: https://docs.blender.org/manual/en/5.2/render/eevee/index.html
- Blender simplify/culling: https://docs.blender.org/manual/en/5.2/render/cycles/render_settings/simplify.html
- Blender EEVEE volumes: https://docs.blender.org/manual/en/5.2/render/eevee/render_settings/volumes.html
- Blender EEVEE sampling: https://docs.blender.org/manual/ka/latest/render/eevee/render_settings/sampling.html
- Geometry Nodes instances: https://docs.blender.org/manual/en/latest/modeling/geometry_nodes/instances.html
- Blender hardware requirements: https://www.blender.org/download/requirements/
- RunPod pricing: https://www.runpod.io/pricing
- Vast.ai pricing guide: https://vast.ai/article/how-much-does-it-cost-to-rent-a-gpu-in-the-cloud-live-pricing-guide
- SheepIt official FAQ: https://client.sheepit-renderfarm.com/faq and points FAQ: https://api.sheepit-renderfarm.com/faq
- Mixamo FAQ: https://helpx.adobe.com/creative-cloud/faq/mixamo-faq.html
- Rhubarb Lip Sync: https://github.com/DanielSWolf/rhubarb-lip-sync

## 6. Evidence classification

For every claim in the Opus plan use:
- `OFFICIAL / VERIFIED`: official source or confirmed current code.
- `MEASURED IN THIS REPO`: reproducible test or billing log from this exact pipeline.
- `PROFESSIONAL PRACTICE`: sourced industry/craft practice, still needs adaptation.
- `ESTIMATE`: arithmetic over explicit assumptions.
- `HYPOTHESIS`: plausible but unmeasured.
- `UNKNOWN`: not verified; do not fill the gap with an assumption.
