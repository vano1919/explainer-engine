---
name: multimodal-qa-review
description: Run and interpret 3-layer deterministic, perceptual, and editorial media QA using explainer_engine.qa.perceptual_qa and technical_gate.
---
# Multimodal QA Review

## Three-Layer Gate
1. **Layer 1 (Deterministic Technical)**: Sample >= 8 temporal frames across the full clip duration with timestamps, SHA-256 hashes, and explicit uninspected-gap reporting; run `technical_gate.check_no_melt`, frozen-frame detection, and original stereo audio RMS/peak/clipping/pure-tone checks.
2. **Layer 2 (Multimodal Perceptual)**: Opt-in only (`--gemini`, default `use_gemini=False`). Authenticates exclusively via `x-goog-api-key` header (never URL query strings), checks `spend_caps.gemini_api()`, validates strict JSON booleans/enums, and converts safety blocks or malformed responses to `NEEDS_REVIEW`.
3. **Layer 3 (Editorial & Creator Sign-Off)**: Keeps `technical_status`, `perceptual_status`, `editorial_status`, and `creator_signoff_status` (`PENDING`) strictly separated.

## Command
`python -m explainer_engine.qa.perceptual_qa --video <clip.mp4> --out-dir <qa_dir>`
