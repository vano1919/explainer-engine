# Step 1.5 feature matrix: G8/G9 (episode/run.py) vs mix.py / build_segments.py (2026-11-19)

Read from code on branch -s13 (head 5a53b7ea). "Gap" = the runner lacks it; every gap needs a decision before 1.5's allowlist is fixed.

## Sound: G8 `audio/stems.render` + run.py G10 vs `tools/render_tools/mix.py`
| Feature | mix.py | G8 / run.py | Status |
|---|---|---|---|
| Narration read placed on the clock | `run_mix` L~690, from `narrator_offsets` | `stems._narration` (read wav), G6 timing | covered |
| Spoken LTX inserts (dialogue) | clip `clip_path` laid at `timeline_start_frame`, level-matched | run.py L1390-1420 (`timing["inserts"]`, `audio/insert_silence`, VL-13) | covered |
| `mute_tail_from_s` (hallucinated tail word muted, Step 1.2 record field) | applied (L~705) | **not read anywhere in explainer_engine** (only `stems.mute_silent_tail`, an RMS-floor rule) | **GAP** |
| Beds / ambience | synthesized noise (D-136 violation) | library takes via cue sheet, logged in `stems_report.json` | G8 better |
| Music | sine chords (D-136 violation) | library takes, BP-62 fades | G8 better |
| Ducking (BP-53) | `duck.duck_presence_band` | `duck.duck_gain` for music and bed (depths in report) | covered |
| Presence-band dip (BP-118) | yes | not in `stems.render` (only in legacy `assemble._mix`) | check: gap or not required for episode-first |
| LUFS -14 and true peak | `normalize_to_target_lufs_and_true_peak` | `qa/targets.normalise_file` in run.py L1259-1272, measured at G10 (BP-50) | covered |
| Library-take log | none | `sounds_used` -> PC-10 | G8 only |
| Map draw SFX on frame spans (BP-203) | `emit_map_audio_events_for_shot` | `sound_plan` events | covered by plan; parity test needed |
| Intentional silence shots | `is_intentional_silence_shot` | sound plan decisions (AV contract D-135) | covered by plan |

## Picture: G9 `production/assemble.assemble_shot_clips` vs `build_segments.py`
| Feature | build_segments | G9 | Status |
|---|---|---|---|
| Trim contract (`rec["clip_path"]`) | `resolve_video_source`, raw fallback refused unless allowed | records carry `clip_path`, `total_frames` | covered |
| Frame tolerance | `MAX_FRAME_DRIFT = 1` (L28, L276-284) | shorter clip refused, longer cut to shot (L1495 docstring) | **differs**: build_segments tolerates ±1, G9 refuses a short clip by even one frame. A clip one frame short has no defined path in G9 |
| Segment cache key | `compute_segment_cache_key` (L73) | chunk stamp reuse (RULE-R1, `chunk_bounds`) | covered, different mechanism |
| Single resize | `probe_dimensions` + one resize | `_fit` helper (assemble L680-690) | covered; parity test needed |
| Overlay authority | `should_apply_segment_overlay` (L143) | `overlays()` L921 | check: does G9 draw text twice when plate rendered it |
| Dips to black | hard-coded `DIPS` set (9 shots, L28-31) | cut plan transitions (`fade_to_black`, `warm_dip`; assemble L1458) | **GAP unless** the 9 shots exist as transitions in the cut plan of the 1914 episode |
| Mac paths | hard-coded defaults | none | G9 better |

## Proposed 1.5 parity rules (amendment v1.1)
Frame counts exact. Video: SSIM/PSNR thresholds unless both use identical filter graphs. Audio: LUFS, peak, library-take log.

## Decisions needed before the allowlist is fixed
1. `mute_tail_from_s`: G8 must apply it (needs `explainer_engine/audio/stems.py` or `episode/run.py` clip_audio layer + a test). Not in the current 1.5 allowlist.
2. The nine `DIPS`: check the 1914 cut plan; if absent, the cut plan generator (not assemble.py) must carry them.
3. ±1 frame: either G9 gets a measured one-frame tolerance with a record, or ingest guarantees exact frames (`recut`). Decide with the plan owner.
4. BP-118 presence dip and overlay authority in G9: confirm on the parity run, no code yet.
