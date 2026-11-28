# Workflow 05 — Autonomous AI Director-Critic Stabilization Loop

1. **Stage 0 (Fail-Closed Gates):**
   - Run `explainer_engine.qa.cinema_gates` (all deterministic gates including narration dead-gap, `faster-whisper` ASR pronunciation/WER, map land-ratio, bridge-vs-map collision, edit grammar/dedup, ducking/SFX balance) plus `explainer_engine.qa.ai_critic_gate`.
2. **Stage 1 (Independent Component Stabilization Loops):**
   - Stabilize each component independently in order: `1A Bridges (GSAP/HTML5)` -> `1B Maps (MapLibre GL WebGL2)` -> `1C 2.5D (Three.js Layered Inpainted)` -> `1D Audio (Kokoro-ONNX + ASR + 4-Act CC0 + Visual SFX)` -> `1E Multi-Angle Cinema Scene (Elements Vault + Popcorn 2x2 + LTX-2.5)`.
   - For each component: Render 2K showcase -> Run L3 deterministic QA -> Build inspection proxy -> Invoke Clean-Room AI Media Critic subagent (`ai-media-critic` skill) -> Verify `ai_critic_verdict/1` SHA-256 (`overall >= 8.5`, `min_subscore >= 7.5`, `critical == 0`).
   - If FAIL -> fix the underlying engine/design system (never lower thresholds!) and repeat.
3. **Stage 2 (3-Minute Master Film + YouTube A/B & Viewer Panel):**
   - Assemble full 180s docudrama using ONLY locked passing components (`>= 80%` hard cuts + J/L-cuts, max pause `<= 2.5s`, unified 35mm LUT, post-assembly visual spotting).
   - Generate 3 A/B/C photoreal thumbnails + Desktop/Mobile `168x94px` YouTube Feed Mockup (`youtube_ab_packaging.py`).
   - Run Clean-Room 3-Persona Real-Viewer Retention Panel (`youtube-ab-retention-critic` skill) and remediate until `Retention @ 0:30 >= 72%`, `AI Critic >= 8.5/10`, and `0` critical defects.
