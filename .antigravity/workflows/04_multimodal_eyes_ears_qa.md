# Workflow 04: Mandatory Multimodal Eyes-On & Ears-On QA (L3–L4)

## Rule
NEVER claim PASS based on exit codes, logs, or single thumbnails.

## Steps
1. **L3 Automated Media Forensics (`cinema_gates.py`):**
   - Verify `2560x1440`, `24 fps`, `yuv420p`, `48000 Hz` 2-ch stereo, `-14.0 ± 0.5 LUFS`, `<= -1.0 dBTP`.
   - Verify `check_no_static_shots`, `check_no_midframe_tears`, `check_audio_scene_consistency`, `check_cross_cut_color_parity`, `identity_lock`, and BP-187 tail bounds.
2. **L4 Visual & Audio Artifacts Generation:**
   - Generate **Per-Shot 5-Frame Temporal Strips** (0%, 25%, 50%, 75%, 100%) to inspect prop permanence and motion smoothness.
   - Generate **Cut-Boundary Comparison Sheets** (last frame of Shot N next to first frame of Shot N+1) to inspect color parity and costume/architecture continuity.
   - Generate **Full-Film Audio Timeline & Loudness Chart** (`narrator`, `dialogue`, `ambience`, `SFX`, `LUFS` per shot).
   - Generate **24-Frame Evolution Contact Sheet**.
3. **Direct Multimodal Inspection & Remediation Logging:**
   - Watch/listen to rendered `.mp4` and inspect contact sheets directly.
   - Log EVERY observed defect and its reusable Python framework fix into `jobs/post_inspection_remediation_log.json` and re-verify before PASS.
