---
name: youtube-ab-retention-critic
description: Audit YouTube A/B/C thumbnail and title packaging at desktop, 168x94 mobile, and TV feed scales and simulate a clean-room 5-persona real-viewer retention curve across the full rendered film.
---
# YouTube A/B Packaging & 5-Persona Real-Viewer Retention Critic

## Mandate
Evaluate every finished docudrama from the perspective of **5 real YouTube viewer personas** deciding whether to click in Desktop, **Mobile (`168x94px`)**, and Living-Room TV home feeds and whether to stay past `0:08`, `0:30`, `1:30`, and the climax.

## Two-Part Protocol
1. **Full-Lifecycle A/B/C Packaging Audit (`youtube_feed_ab_mockup.png`):**
   - Apply Paddy Galloway Packaging Matrix (Broad Appeal x Curiosity Gap x Zero Title-Thumbnail Duplication x Visual Contrast) + YouTube Studio "Test & Compare" Watch-Time-per-Impression (WTPI) estimation.
   - Inspect all 3 photoreal `1280x720` thumbnails + competing titles side-by-side in Desktop, **Mobile (`168x94px`)**, and TV feeds via `view_file`.
   - Reject cartoon fonts (`Bangers`), cluttered `> 3` word overlays, or clickbait mismatches with the `0:00-0:18` Hook.
2. **Clean-Room 5-Persona Retention Panel (`viewer_panel_report.json` + `youtube_retention_curve.png`):**
   - Watch and listen to the full rendered film via `view_file` through **5 distinct personas**:
     1. **History Buff** (checks paleoanthropology/history plausibility, 3D map clarity, dates, depth).
     2. **Casual Browser** (tests 3-second hook grab, open curiosity loop, clarity past `0:30`).
     3. **Docudrama Cinema Fan** (evaluates live-action LTX-2.5 acting realism, J/L-cuts, 5-layer audio, dramatic breathers).
     4. **Mobile Commuter (`168x94px`)** (checks mobile thumbnail/overlay legibility and 2–5s pattern-interrupt cadence).
     5. **Skeptical Retention Critic** (hunts reused images, looped clips, narrator-visual mismatches, `> 5s` dead zones, repetitive SFX).
   - Output second-by-second / 10-second retention curve + pattern-interrupt heatmap, exact drop-off timestamps (`> 3%` drop), and remediation actions.
   - v3 Gate passes ONLY if `personas >= 5`, `overall_youtube_readiness_score >= 8.8`, `retention_at_30s >= 80%`, `avg_percentage_viewed >= 65%`, `0` critical drop-off defects, and exact 64-char `video_sha256` match.
