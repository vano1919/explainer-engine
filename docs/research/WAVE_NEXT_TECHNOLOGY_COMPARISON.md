# Wave Next Technology Comparison

Evaluates candidate technologies across production domains against the **actually implemented** code in `explainer-engine`.

| Domain | Actually Implemented in Branch | Future / Evaluated Candidate(s) | Hardware / VRAM | License (Code / Weights) | Implemented Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| Video Generation | `videolane/adapters.py` (`LocalRehearsalVideoAdapter`, fail-closed `GovernedModalLTXRequest`), `videolane/ltx_loop.py` | LTX-2.5 22B (Modal H100/A100, pending owner approval); MiniMax H3 rejected | CPU (rehearsal) / 32–80 GB GPU (Modal LTX) | LTX-2 Community | Local rehearsal & governed request path implemented; live GPU blocked at `$0.00` |
| Visual Observation & QA | `qa/perceptual_qa.py` (deterministic signal layer + opt-in Gemini multimodal review + integrated `identity_lock`) | Qwen2.5-VL-7B/32B (not yet implemented as an active adapter) | CPU (signal) / API (Gemini) | Apache-2.0 (evaluated) | Deterministic signal + opt-in Gemini active; Qwen adapter NOT implemented |
| Still vs Video Upscaling | `LocalStillUpscaler` (PIL Lanczos + UnsharpMask) and `LocalFFmpeg2KVideoUpscaler` (FFmpeg Lanczos + CAS) | Real-ESRGAN, LTX Spatial Upscaler IC-LoRA, SeedVR2 (future plug-in adapters) | CPU (active local) / GPU (future) | MIT/GPL/LTX Community | Separate still & video local adapters active and wired into `ltx_loop.py` |
| Maps & Cartography | `maps/draw.py` using strictly verified `assets/fonts/LiberationSerif-Regular.ttf` (no silent fallback on `face="map"`) | MapLibre GL + Blender 3D terrain | CPU | OFL / BSD-3 | Active deterministic local map renderer verified |
| Overlays & Bridges | `overlay/bridge_compiler.py` (`overlay_spec/2` compiled to PIL RGBA PNGs + FFmpeg `overlay` composite) | HyperFrames (not invoked by `bridge_compiler.py`), Remotion rejected | CPU | MIT / LGPL-GPL | PIL + FFmpeg renderer active in `episode/run.py` `stage_assemble` |
| Audio Spotting & Mixing | `audio/post_assembly_spotting.py` (grayscale frame-delta peaks, SHA-256 + `commercial_use=true` WAV resolution, stereo-preserving mixer) | WavLate / WhisperX (future semantic upgrades) | CPU | CC0 / MIT | Active in `episode/run.py` `stage_assemble` with path containment |
| Face Identity Lock | `qa/identity_lock.py` (commercial-safe deterministic portrait-region RGB histogram comparator; zero InsightFace weights) | OpenCV Zoo YuNet (MIT) + SFace (Apache-2.0) when ONNX weights are installed | CPU | MIT / Apache-2.0 | Active in `perceptual_qa.py` and `episode/run.py` `stage_qa`; histogram heuristic explicitly documented |
