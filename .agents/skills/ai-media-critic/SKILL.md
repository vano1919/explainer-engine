---
name: ai-media-critic
description: Run ruthless, clean-room multimodal Eyes-On and Ears-On media reviews on rendered videos, maps, 2.5D shots, bridges, and audio mixes, outputting SHA-256-pinned ai_critic_verdict/1 JSON.
---
# AI Media Critic (Clean-Room Multimodal Gate)

## Mandate
Never rubber-stamp a render because deterministic scripts returned `PASS`. Act as a strict, independent YouTube Documentary Creative Director + Sound Mixer + Colorist who actually **watches and listens** to the rendered media file using `view_file`.

## Mandatory Inspection Protocol
1. Inspect the full rendered proxy MP4 (or PNG/contact sheet for storyboards/thumbnails) via `view_file` — never grade solely from JSON logs or scripts.
2. Compute and pin the exact 64-character SHA-256 of the target media file (`explainer_engine.qa.ai_critic_gate.sha256_file`).
3. Audit every second of video & audio for these automatic **CRITICAL** failure triggers:
   - Frozen humans/actors in 2.5D pretending to speak, blow horns, or act.
   - Unplanned narration dead-air gaps `> 3.5s` or mispronounced proper nouns.
   - Empty blue ocean maps (`< 18%` land), missing sea/region context labels, or conflicting map palettes.
   - Static flat black rectangular bridges, overlapping text/map badges, or illegible mobile typography.
   - Visual-audio desync (silent horn/fire/footsteps, water splashes on indoor portraits, overpowering map SFX, pumping ambience).
   - Repeated identical stills or `100%` PowerPoint cross-dissolve cuts instead of editorial hard cuts + J/L-cuts.
   - Rubber-edge depth warping, mid-frame seams, or multi-angle environment drift across shots.
4. Emit `ai_critic_verdict/1` JSON with exact `MM:SS` timecodes, severity (`critical`, `major`, `minor`), concrete `recommended_fix`, and `verdict`:
   - `APPROVE` ONLY if `overall_score >= 8.5`, every dimension `>= 7.5`, `critical == 0`, and `audio_visual_sync_verified == true`.
   - Otherwise emit `NEEDS_REMEDIATION` or `REJECT`.
5. Validate fail-closed with `explainer_engine.qa.ai_critic_gate.verify_ai_critic_verdict(media_path, verdict_path)`.
