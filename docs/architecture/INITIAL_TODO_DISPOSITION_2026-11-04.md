# Initial TODO Disposition — 2026-11-04

> This is a partial, evidence-based cleanup record for the planning branch, not the final repository-wide audit. Fable/Claude must scan every TODO and complete this matrix before Opus handoff.

## Removed from active instructions

| File | Removed material | Why | Runtime impact |
|---|---|---|---|
| explainer_engine/video/generator.py | Old CLAUDE-MASTER-MOLD-SYNC BATCH-M6 TODO routing parallax/Qwen/LTX/map tiers | Incompatible with Blender as final visual renderer and one Ink Chronicle universe | None: file was a planning stub with no implementation |
| explainer_engine/video/scene_builder.py | Old TODO requiring production_script/4, CastRegistry, Qwen/LoRA and LTXBucketSpec | Obsolete schema/routing assumptions; new ShotSpec and Blender scene plan must be designed after contract audit | None: file was a planning stub |
| explainer_engine/video/tier_router.py | Old four-tier Qwen/LTX/portrait-video TODO | The new router must choose HELPER/STILL/VIDEO and Blender render profiles, not external final video generators | None: file was a planning stub |
| explainer_engine/video/keyframes.py | Old Qwen keyframe / next-pose / LoRA TODO | Keyframe ownership and whether this module remains must be redesigned for Blender | None: file was a planning stub |
| explainer_engine/assets/library.py | Leading Master Mold v2.1.0 synchronization TODO block | Unverified batch instructions unrelated to the new visual production architecture; actual module retained | None: only leading comments removed |
| explainer_engine/production/assemble.py | Leading Master Mold v2.1.0 synchronization TODO block | Unverified batch instructions; existing audio/timeline/FFmpeg assembler is to be audited and preserved where compatible | None: only leading comments removed |
| explainer_engine/production/rig.py | Leading Master Mold v2.1.0 synchronization TODO block | Old synchronization instructions contradicted the module's explicit RETIRED status | None: retired historical module and docstring retained |

## Marked historical / superseded, not deleted

| File | Treatment |
|---|---|
| docs/wip/CLAUDE_SYNCHRONIZED_TODO_EXECUTION_GUIDE_2026-11-04.md | Banner added: historical only; do not execute LTX/Qwen/Master Mold batches in this branch |
| docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md | Banner added: historical only; do not use as active implementation sequence |
| docs/research/cinematic_audio_visual_craft_and_tool_implementation_report_2026_11_04.md | Retained as research source. Fable must separate still-valid craft/Blender findings from outdated LTX/Qwen implementation proposals |

## Mandatory full-repository audit still pending

Fable must scan all TODO comments, TODO-only modules, WIP guides, prompts, config, schemas, tests, CI and docs. Do not infer that the list above is complete. For every remaining TODO record:
- path, symbol and exact line range at the audited HEAD;
- whether the target exists and is called;
- whether the TODO is based on verified current code or an unverified proposal;
- status: KEEP / REWRITE / REMOVE / ARCHIVE / NEEDS EVIDENCE / CREATOR DECISION;
- why it is or is not compatible with Ink Chronicle;
- runtime/test/docs dependency check;
- exact replacement work item, owner, dependencies, tests and acceptance criteria.

No further broad TODO deletion is authorized without that audit. Preserve useful historical research and all active runtime code/tests.
