# Explainer Engine V4.1 — External Research & Evidence Register

- **Document ID:** `V4.1-DOC-04` (`V4.1-IMPL-BLUEPRINT-001`)
- **Date:** `2026-11-19`
- **Confidence Labels:** `VERIFIED_CODE` | `VERIFIED_TEST` | `VERIFIED_MEDIA` | `VERIFIED_UPSTREAM` | `REPRODUCED` | `REPORTED` | `INFERRED` | `PROPOSED` | `UNKNOWN`

---

## 1. Local Repository & 1914 Forensic Evidence

| Evidence ID | Source Path & Lines / Scope | Label | Verified Facts |
| :--- | :--- | :--- | :--- |
| `EV-V41-01` | `argon/p1-2-timing-contract` @ `0592114c6c2d44a9af00b11553f169516e175864` | `VERIFIED_CODE` | Clean tree (`git status --short == ''`), `python3 -m explainer_engine.docs_lint` -> `0 finding(s)`, `511` Python files in `explainer_engine/`, `361` `test_*.py`, `21` `.claude/skills/`, `16` `.claude/agents/*.md`, `15` `config/*.json`, `55` files in `explainer_engine/blender/`. |
| `EV-V41-02` | `explainer_engine/episode/run.py` (`1,790`L, AST call-graph) | `VERIFIED_CODE` | Directly imports `understand`, `directed25d`, `layers25d`, `final_frame_qa`, `look_and_listen`, `motion_intent`, `sound_realism`, `videolane.*`, `rule_enforcer`, `map_clip`, `modal_ltx_jobs`. Zero dynamic `import_module` calls. Truly disconnected: `viewer_critic.py` (`0` callers repo-wide), `retry_router.py` (`1` legacy caller in `blender/validate.py`), `blind_check.py`/`keyframe_gate.py` (`0` in `episode/run.py`). `superres.py` is indirectly imported by `turn_pack.py`, `frame_pick.py`, `modal_ltx_jobs.py`. |
| `EV-V41-03` | `explainer_engine/episode/timing.py` (`727`L) | `VERIFIED_CODE` | Real timing module (there is no `timing_contract.py`); aligns Scribe word timestamps to script lines and builds shot-relative word spine. |
| `EV-V41-04` | `explainer_engine/qa/retry_router.py` (`131`L) | `VERIFIED_CODE` | Implements `OR-04`/`CN-13`/`BP-165` 3-attempt router; lines 51–55 confirm `REWEIGHT_REFERENCES` lacks router input and falls back to reseed. |
| `EV-V41-05` | `explainer_engine/finish/superres.py` (`740`L) | `VERIFIED_CODE` | CPU `4xNomos2_realplksr_dysample` + `2xNomosUni_span_multijpg` (`CC-BY-4.0`, pinned SHA-256), wavelet `colour_fix`, `lpips_fn`, `BP-198` QC. |
| `EV-V41-06` | `explainer_engine/training/pods/ltx/launch.json` | `VERIFIED_CODE` | Pins `Lightricks/LTX-2.5` (`49b093a39c19169a8a81721dcc541e07e945232f`, 5 SHA-256 safetensors on Modal `ee-weights`, `ltx_pipelines.distilled`, `1280x704@24fps`, `H100`, `8 CPU`, `96 GiB RAM`, `usd_per_h: 5.0937`, `chain_overlap_frames: 0`). |
| `EV-V41-07` | `explainer_engine/blender/{polyhaven.py,terrain.py}` (`295`L, `209`L) | `VERIFIED_CODE` | `polyhaven.py` already adapts MIT `ahujasid/blender-mcp:addon.py` (`urllib`, ETag cache, MD5 check, zip-slip guard, Blender 5.2 HDRI world nodes); `terrain.py` builds deterministic fBm height fields with 6 material classes. |
| `EV-V41-08` | `episodes/ep_truce_1914/planning/full_film_2026-11-15/CORRECTIONS_LOG.md` | `VERIFIED_CODE` | Confirms real 1914 open-loop failures: `S06_SH008` (double `"Maybe"`), `S03_SH007` (silent beat `"Oh my God"` + fog bloom), `S03_SH003` (cut off `"Nacht"`), `S04_SH014` (handshake released before cut), `S07_SH005` (bangs before narration), `S07_SH006` (1 shot instead of 2). |
| `EV-V41-09` | `mac_content_audit_classification.json`, `37_SLICE_REVIEW_1.md`, `24_OPUS_VISUAL_CHECK_MAPS_S8.md` | `VERIFIED_CODE` | Confirms `43` audited rows (`5` deferred photos), 2.5D slice defects `V1–V6` (cute snow, Frame-0 leak, subject occlusion, invisible steam/breath, cropped boots, tiny pan), and map defects (clipped HUD, missing labels, blurry 60–90km relief, `99/100` map tests). |
| `EV-V41-10` | `explainer_engine/audio/sfx_planner.py` (`474`L) & `config/model_lifecycle.json` | `VERIFIED_CODE` | Confirms lexical `FOOTSTEP_KEYWORDS` (`"march"`, etc.) in `sfx_planner.py`; confirms `gemini-2.5-*` and `imagen-*` appear **only** in `config/model_lifecycle.json` (`0` active `.py` files). |
| `EV-V41-11` | `pytest` baseline at `eb80e443` (`3,147 passed / 177 failed / 24 skipped`) | `REPORTED` | `pytest` binary not installed in this sandbox container; must be re-executed and classified on live Argon in `WP-00`. |

---

## 2. External Upstream Repositories, APIs, Licenses & Pricing (`VERIFIED_UPSTREAM`)

| Candidate | Exact URL | Category | Verified Capability & Limitations | License & Cost | V4.1 Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Gemini Agentic Video Understanding** | [ai.google.dev/gemini-api/docs/video-understanding](https://aistudio.google.com/docs/video-understanding) | API | Supported on `gemini-3.8-flash`, `3.7-flash`, `3.6-flash`, `3.5-flash-lite`, `gemini-4-{argon,carbon,hydrogen}` via **Interactions API**; up to `88%` fewer input tokens & `~7%` higher quality on long-form vs static 1 FPS; **not** frame-accurate PTS by itself. | Proprietary API | **Adopt** inside `AdaptiveVideoInspectionRouter` |
| **Gemini Omni 1.2 Flash** | [ai.google.dev/gemini-api/docs/omni](https://ai.google.dev/gemini-api/docs/omni) | API / Video Model | Released Nov 5, 2026; 3–15s native audio+video, first+last frame interpolation (3–10s), up to 6 ref images (3/char, 2 chars), stateful Interactions API editing. Official 720p price: **`$0.07/sec`** (`6×5s=$2.10`, `6×10s=$4.20`, `6×15s=$6.30`). | Proprietary API (`$0.07/s` @ 720p) | **Benchmark** (`WP-07` Exp 1) |
| **Gemini Nano Banana 2.1** | [ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1](https://ai.google.dev/gemini-api/docs/models/gemini-nano-banana-2.1) | API / Image Model | Up to 14 refs (4 chars, 10 objects), 1K/2K/4K; Level-2 fallback in `picture_route.json` (`$0.017` 1K / `$0.025` 2K batch). Guard against [gemini-3-pro-image Batch overbilling bug](https://discuss.ai.google.dev/t/gemini-3-pro-image-batch-api-returns-up-to-35-billed-images-for-single-image-requests-since-8-oct-2026/196940). | Proprietary API | **Keep** Level-2 fallback |
| **Lightricks/LTX-2 (LTX-2.5)** | [github.com/Lightricks/LTX-2](https://github.com/Lightricks/LTX-2) (`packages/ltx-pipelines/docs/conditioning.md`) | Code + Weights | `ImageReplace` (`0`/`1+8k`), `ImageGuide`, `ICLoraPipeline`, `DFRPipeline`, `RetakePipeline` (`8k+1` frames, `/32` res), `DubItPipeline`. Must verify `RetakePipeline` on pinned Modal `ee-weights` worker. | Code `Apache-2.0`; Weights **LTX-2.x Community License** (paid if `>= $10M` ARR) | **Adopt** + verify `RetakePipeline` (`WP-07`) |
| **Modal Pricing** | [modal.com/pricing](https://modal.com/pricing) | Serverless GPU | `H100 SXM5`: `~$3.95/hr` (`$0.001097/s`), `A100 80GB`: `$2.50/hr`, CPU `$0.0000131/core/s`, RAM `$0.00000222/GiB/s` (`H100+8CPU+96GiB = $5.094/hr`). Sandbox `3x` applies to **CPU/RAM** (GPU standard); broad-region multiplier **`1.15x`**; egress `$0.04/GiB` above free tier. | Pay-per-second (`$30/mo` Starter free credit) | **Adopt** Functions only; enforce cost rules in `RouteRegistry` |
| **ByteDance-Seed/SeedVR (SeedVR2)** | [github.com/ByteDance-Seed/SeedVR](https://github.com/ByteDance-Seed/SeedVR) | Video Restoration | 3B/7B one-step diffusion; official repo explicitly warns oversharpening on lightly degraded 720p AIGC video; ComfyUI `INT8+FlashAttention` causes black frames (use `FP16/FP8`). | `Apache-2.0` (Modal GPU) | **Benchmark Only** (`WP-07` Exp 2, defect-gated) |
| **WhisperX v3.8.6 & stable-ts** | [github.com/m-bain/whisperx](https://github.com/m-bain/whisperx) / [github.com/jianfch/stable-ts](https://github.com/jianfch/stable-ts) | Python ASR/Align | VAD + `wav2vec2` forced alignment; known limitations on overlapping speech/diarization. External `93.2%` @ 200ms precision is `REPORTED` (must calibrate on our corpus inside `AudioEvidenceFusion`). | `WhisperX`: `BSD-2-Clause` (Free) | **Adopt** inside `AudioEvidenceFusion` |
| **MMAudio & HunyuanVideo-Foley** | [github.com/hkchengrex/MMAudio](https://github.com/hkchengrex/MMAudio) / [github.com/Tencent-Hunyuan/HunyuanVideo-Foley](https://github.com/Tencent-Hunyuan/HunyuanVideo-Foley) | Video-to-Audio Foley | Synchronized visual-to-audio Foley. **Critical License Fact:** `MMAudio` is `MIT`; `HunyuanVideo-Foley` uses **Tencent Hunyuan Community License** which **excludes EU, UK, and South Korea**. | `MMAudio`: `MIT`; `Hunyuan`: Territorial Community License | **Benchmark** (`WP-07` Exp 3); check commercial distribution |
| **PySceneDetect & OmniShotCut** | [github.com/breakthrough/pyscenedetect](https://github.com/breakthrough/pyscenedetect) / [arxiv.org/html/2604.24762v2](https://arxiv.org/html/2604.24762v2) | Shot Boundary | `PySceneDetect` (fast CPU cut/fade detection); `OmniShotCut` (May 2026 research, IoU `0.644`). | `PySceneDetect`: `BSD-3` (Free) | **Adopt** `PySceneDetect`; monitor `OmniShotCut` |
| **OpenTimelineIO** | [github.com/AcademySoftwareFoundation/OpenTimelineIO](https://github.com/AcademySoftwareFoundation/OpenTimelineIO) | Editorial Interchange | Standard `.otio` export for DaVinci Resolve / NLE finishing. | `Apache-2.0` (Free) | **Optional** (`WP-10`) |
| **Claude Code Hooks** | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) | Governance | `PreToolUse` & `Stop` block via Exit Code `2`; `PostToolUse` & `SubagentStart` cannot block; hooks cannot prove semantic Skill reading. | Proprietary CLI | **Keep `<500ms`** binary guards |

---

## 3. Free Rich Libraries & Skills for the 10% 3D Blender Cartography & Infographics Track (`WP-B1`)

| Resource & URL | Category | What It Provides for 3D 10% Lane | License & Commercial Status |
| :--- | :--- | :--- | :--- |
| **[ahujasid/mcp-for-blender](https://github.com/ahujasid/mcp-for-blender)** | Blender MCP (`MIT`) | Bidirectional AI-to-Blender control; note `explainer_engine/blender/polyhaven.py` already adapts its Poly Haven client! | `MIT` (Free commercial) |
| **[scenario-labs/skills](https://github.com/scenario-labs/skills)** | Blender Pre-Vis Skill | *"Script to previs in Blender: beats to shot list, cameras and lenses"* workflow | Open Skill repo (check repo LICENSE before copying) |
| **[codepawl/creator-generalist](https://github.com/codepawl/creator-generalist)** & **[mlolson/blender-orchestrator](https://github.com/mlolson/blender-orchestrator)** | 3D Agent Skills / MCP | Spatial reasoning + automated CC0 Poly Haven / ambientCG / Quaternius scene assembly | Open GitHub repos (verify LICENSE in `WP-B1`) |
| **[domlysz/BlenderGIS](https://github.com/domlysz/blendergis)** + **Blosm** ([prochitecture.gumroad.com/l/blender-osm](https://prochitecture.gumroad.com/l/blender-osm)) | 3D Terrain / GIS Addons | Real NASA SRTM / DEM 30m elevation terrain meshes, Shapefile/GeoTIFF historical map projection, rivers/roads/railways projected onto 3D relief | `BlenderGIS`: `GPL-3.0` (Free); `Blosm` base: Free (`$0`) |
| **[Poly Haven](https://polyhaven.com/all)** | 3D Models, PBR Textures & 16K HDRIs | 2,300+ production assets (521 models, 856 textures, 993 HDRIs), no-key public API, official Blender extension | **`CC0`** (Zero attribution, 100% commercial safe) |
| **[ambientCG](https://github.com/devanshutak25/3d-resources)** | PBR Materials & HDRIs | 2,000+ seamless PBR materials (mud, parchment, brick, wood, stone, rusted iron) with Python batch-download scripts | **`CC0`** (100% commercial safe) |
| **[Smithsonian 3D Digitization](https://arxiv.org/html/2307.05663v1)** | Historical 3D Museum Scans | ~2,400+ compressed GLB scans of real historical/cultural artifacts | **`CC0`** (Public domain, commercial safe) |
| **Quaternius** & **[CC0 Stylized Textures](https://www.blendernation.com/2025/11/04/cc0-stylized-textures/)** | Modular 3D & 4K Stylized PBR | Stylized 4K PBR maps (Basecolor/Normal/Roughness/AO/Height) & modular props matching painterly aesthetic | **`CC0`** (100% commercial safe) |
| **[Sonniss GDC Bundles](https://mubert.com/blog/free-sound-effects-video-libraries-licences)** & **Freesound (`CC0` filter)** | Documentary SFX for 3D Maps | Commercial-cleared whooshes, paper/parchment rustle, brass clicks, distant artillery, wind beds for 3D map/diagram events. (**Avoid BBC Sound Effects** — non-commercial RemArc license; keep Sonniss out of AI training sets.) | `Freesound CC0`: `CC0`; `Sonniss GDC`: Royalty-free commercial (no AI training) |

---

## 4. Deep Completion Pass Additions (`V4.1-DEEP-COMPLETION-002`, `2026-11-19`)

### 4.1 Real Executed Read-Only Test Evidence (`VERIFIED_TEST`)
- **Command:** `PYTHONPATH=tests/unit:. python3 -m pytest -p no:cacheprovider --basetemp=/tmp/v41_pytest -q tests/unit/{test_audio_timing,test_blind_check,test_cloud_hooks_modal,test_governance_hooks,test_retry_router,test_shot_router,test_superres,test_v43_retired,test_v4_2_reconciliation_and_viewer_critic,test_videolane,test_videolane_media}.py`
- **Commit:** `0592114c6c2d44a9af00b11553f169516e175864` (Python `3.11.2`, `pytest`, `jsonschema 4.23.0`, `PyYAML 6.0`, `av 10.0.0`, `cv2 4.11.0`, `numpy 2.1.3`)
- **Outcome:** **`164 passed, 0 failed, 1 skipped`**, `git status --short == ''`.

### 4.2 Upstream Source-Code Verification (`VERIFIED_UPSTREAM`)
1. **`Lightricks/LTX-2` (`packages/ltx-pipelines/src/ltx_pipelines/retake.py` @ `c1b4675`, `400` lines, `2026-11-03`):**
   - `RetakePipeline.__init__(model_paths, loras, distilled=True)` requires ONLY `transformer`, `video_vae`, `audio_vae`, and `gemma` (`PromptEncoder`) — **exact match** to the 4 core safetensors already pinned in `training/pods/ltx/launch.json` (`ltx-2.5-22b-distilled-transformer-bf16`, `gemma4-12b-with-proj-ltx-2.5-bf16`, `ltx-2.5-audio-vae-bf16`, `ltx-2.5-video-vae-bf16`).
   - `RetakePipeline.__call__` exposes independent `regenerate_video: bool = True` and `regenerate_audio: bool = True` flags via `TemporalRegionMask(start_time, end_time, fps)` and validates `(frames - 1) % 8 == 0` and `width % 32 == 0` / `height % 32 == 0`.
   - **Code-Pin Delta:** `launch.json` currently pins `LTX-2.git @ e98f6d927d83c92ef2be6aec76c8440b19306e39`; `WP-07` must verify whether `e98f6d92` includes `ltx_pipelines.retake` or bump the pin to `c1b4675`.
2. **`m-bain/whisperX` (`whisperx/alignment.py` + GitHub issues `#98`, `#298`, `#408`, `#1016`, `#1287`):**
   - Confirmed limitations: numerals/symbols absent from alignment dictionary (`"2014."`, `"£13.60"`) cannot be aligned; overlapping speech degrades alignment; "phantom language" detection on background noise crashes alignment unless language is pinned (`#298`); `PR #986` alignment regression was reverted in `f2609a6` (`v3.8.5+`). Directly justifies `AudioEvidenceFusion` (`V4.1-DOC-03 §2`) and pinning language=`en` on narration/English dialogue clips.
3. **`PyAV` (`av 10.0.0` installed locally + [PyAV 19.0.2 Frame API](https://pyav.basswood-io.com/docs/stable/api/frame.html) & [Discussion #2046](https://github.com/PyAV-Org/PyAV/discussions/2046)):**
   - Confirms `CodecContext.time_base` and `Stream.time_base` can differ; audio timestamps advance by exact integer `frame.samples` in `Fraction(1, frame.sample_rate)`; simple frame counters break on VFR or dropped frames. Directly grounds `explainer_engine/core/media_clocks.py`.
4. **`vano1919/tmr-artifacts` (Hugging Face 1914 Media Access Check):**
   - Returned `0` public search results -> confirmed private/authenticated dataset; raw 1914 media inspection remains `BLOCKED` until run on an authenticated Creator/Argon environment (exact file manifest recorded in `V4.1-DOC-02 §5`).
