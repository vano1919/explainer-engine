# Wave Next Technology Comparison

Evaluates candidate technologies across all 6 production domains against existing `explainer-engine` modules (`v4.3`).

| Domain | Existing Capability | Candidate(s) Evaluated | Hardware / VRAM | License (Code / Weights) | Status | Decision |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| Video Generation | `videolane/scene.py`, `ltx_loop.py`, `modal_ltx_jobs.py` | LTX-2.5 (22B I2V/FLF2V/IC-LoRA), MiniMax H3 | 32–80 GB VRAM (Modal H100/A100) | LTX-2 Community (<$10M rev) / H3 geo-restricted | Production (LTX-2.5) / Restricted (H3) | **KEEP & EXTEND LTX-2.5** via interchangeable adapters; **REJECT** H3 |
| Visual Observation & QA | `qa/perceptual_qa.py` (3-layer, opt-in Gemini) | Qwen2.5-VL-7B/32B, Qwen3-VL, InternVL2.5-8B | 16–24 GB VRAM (7B–8B) | Apache-2.0 / MIT | Production-ready | **ADOPT** `Qwen2.5-VL-7B` adapter interface alongside opt-in Gemini (multi-layer QA) |
| Still vs Video Upscaling | `finish/esrgan_cpu.py` (still x2) | LTX-2.5 Pixel Spatial Upscaler IC-LoRA, SeedVR2 (4n+1), Real-ESRGAN | CPU (stills) / 24–48 GB GPU (SeedVR2/LTX) | LTX-2 Community / Apache-2.0 / BSD-3 | Production-ready | **SEPARATE** `StillUpscalerAdapter` (Real-ESRGAN) from `VideoUpscalerAdapter` (LTX Spatial / SeedVR2) |
| Maps & Cartography | `maps/maplibre_spec.py`, `maps/draw.py` | MapLibre GL + Liberation Serif raster fix, Blender 3D terrain | CPU / headless browser | BSD-3 / OFL | Production-ready | **KEEP & FIX** `maps/draw.py` typography (`Inter` -> `Liberation Serif`) |
| Overlays & Timeline | `overlay/hyperframes.py` (0.9.39), FFmpeg | HyperFrames, Remotion, OpenTimelineIO (Blender 5.3) | CPU + Node 22+ | Apache-2.0 / MIT | Production-ready | **EXTEND HyperFrames** via `bridge_compiler.py`; **REJECT** Remotion duplicate |
| Audio Retrieval & Sync | `audio/sfx_library.py`, `audio/local_words.py`, `episode/timing.py` | WavLate (0.31s granularity), WhisperX forced alignment | CPU / small GPU | Apache-2.0 / BSD-4 | Experimental (WavLate) / Production (WhisperX) | **INTEGRATE** WhisperX hook in `local_words.py`; **BENCHMARK** WavLate as opt-in semantic retriever |
| Face Identity Lock | `qa/face_points.py` (YuNet + SFace) | OpenCV Zoo YuNet+SFace vs InsightFace | CPU (ONNX) | MIT + Apache-2.0 vs Non-Commercial weights | Production-ready | **EXTEND** YuNet+SFace as `REVIEW`-level cross-scene identity lock; **REJECT** non-commercial InsightFace weights |
