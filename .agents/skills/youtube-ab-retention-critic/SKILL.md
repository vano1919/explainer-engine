---
name: youtube-ab-retention-critic
description: Audit YouTube A/B/C thumbnail and title packaging at desktop and 168x94 mobile feed scale and simulate a clean-room 3-persona real-viewer retention curve across the full rendered film.
---
# YouTube A/B Packaging & Real-Viewer Retention Critic

## Mandate
Evaluate every finished docudrama from the perspective of real YouTube viewers deciding whether to click in a crowded home feed and whether to stay past `0:08`, `0:30`, `1:30`, and `3:00`.

## Two-Part Protocol
1. **A/B/C Packaging Audit (`youtube_feed_ab_mockup.png`):**
   - Inspect all 3 photoreal `1280x720` thumbnails + competing titles side-by-side in a simulated Desktop and **Mobile (`168x94px`)** YouTube Home Feed via `view_file`.
   - Score 3-second mobile readability, visual contrast, emotional curiosity gap, and promise alignment with the `0:00-0:18` Cold Open Hook.
   - Reject cartoon fonts (`Bangers`), cluttered `> 4` word overlays, or clickbait mismatches.
   - Pick the winning variant and output `youtube_ab_ctr_report.json`.
2. **Clean-Room 3-Persona Retention Panel (`viewer_panel_report.json` + `youtube_retention_curve.png`):**
   - Watch and listen to the full rendered film via `view_file` through 3 distinct personas:
     1. **Impatient Mobile Scroller** (bounces if `0:00-0:08` lacks immediate hook or any gap `> 3.5s`).
     2. **BBC Earth / *Life on Our Planet* Documentary Fan** (demands cinematic realism, authentic soundscape, zero mannequin stiffness).
     3. **History YouTube Regular** (demands crystal-clear maps, dynamic animated bridges, micro-hooks every `25-30s`, and abrupt payoff ending).
   - Output 15-second retention curve estimates (`0:00 -> end`), exact drop-off timestamps, and remediation actions.
   - Gate passes ONLY if predicted `retention_at_30s >= 72%`, `avg_percentage_viewed >= 58%`, and `0` critical drop-off defects.
