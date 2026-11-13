# Stage report: G7 clips lane (map_action + still_25d), Truce 1914 script A

Written 2026-11-13 ~21:55 UTC by the clips thread. Rehearsal state: the real G7 still follows the LTX ingest (audit condition 1). Cost: $0 (container CPU, no Modal, no Gemini).

## Result
- Script A `261d43b8...`, frames list v5 `f2e5a232...`; G5 pictures PASS on the final files; G6 rehearsal FAIL by design before the LTX ingest (`read_aligned_to_the_lines` 81.8 %, `clip_spoken_shots_timed_by_their_clips` 0/39).
- G7 rehearsal: 84 of 84 clips; own lane (5 map_action + 23 still_25d = 28 shots): **0 FAIL**, 11 PASS, 17 REVIEW. Visual mix measured: map 8.5 % / 2.5D 35.1 % / video 56.4 % of 379.83 s (target 10/30/60 +-10).
- Video-lane shots drawn by the rehearsal's 2.5D fallback (not my lane, not real clips): PASS 6, REVIEW 46, FAIL 3 (`faces_rigid`: S03_SH003, S03_SH009, S07_SH006), INCOMPLETE 1 (S05_SH005). They disappear when the LTX clips are ingested.
- Clips: HF `https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal` (28 mp4 + clip.json + MANIFEST.json with sha256, all 28 hashes match the Hub, commit 483f0af4).

## Looked at (audit condition 4)
Frame pairs (20 % / 80 %) of all 28 own shots and one frame per map label at its word. Fire and candle flicker sit on the brazier and the candles, no flickering sky on any still; map labels appear at their word (S02_SH001 absent at frame 40, visible from the word at 46; S02_SH002 absent at 12, visible at 34); the end card is black with one flickering candle. One visual note for the owner: the soft smoke/mist blobs on S05_SH003, S05_SH016, S06_SH001, S08_SH003 read as smudges on a bright sky (no flicker); not changed.

## REVIEW rows of the own lane (cause)
| Shot | Status | Gate | Measured |
|---|---|---|---|
| S01_SH004 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.610 (engineering default 0.2) |
| S01_SH005 | REVIEW | near_plane_travel | near plane travel 0.026 of the width (plan P5.2: (0.04, 0.06); BP-182 cap 0.08) |
| S02_SH001 | REVIEW | map_not_standing_still | longest still stretch 59 frames (BP-164: 6); the first action starts at frame 46 |
| S02_SH002 | REVIEW | map_not_standing_still | longest still stretch 94 frames (BP-164: 6); the first action starts at frame 16 |
| S02_SH003 | REVIEW | map_not_standing_still | longest still stretch 54 frames (BP-164: 6); the first action starts at frame 10 |
| S02_SH004 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.988 (engineering default 0.2) |
| S02_SH004 | REVIEW | near_plane_travel | near plane travel 0.026 of the width (plan P5.2: (0.04, 0.06); BP-182 cap 0.08) |
| S02_SH008 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.717 (engineering default 0.2) |
| S02_SH009 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.810 (engineering default 0.2) |
| S03_SH002 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.708 (engineering default 0.2) |
| S03_SH010 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.553 (engineering default 0.2) |
| S03_SH010 | REVIEW | near_plane_travel | near plane travel 0.028 of the width (plan P5.2: (0.04, 0.06); BP-182 cap 0.08) |
| S05_SH001 | REVIEW | map_not_standing_still | longest still stretch 152 frames (BP-164: 6); the first action starts at frame 0 |
| S05_SH002 | REVIEW | map_not_standing_still | longest still stretch 100 frames (BP-164: 6); the first action starts at frame 12 |
| S05_SH003 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 1.343 (engineering default 0.2) |
| S05_SH003 | REVIEW | near_plane_travel | near plane travel 0.026 of the width (plan P5.2: (0.04, 0.06); BP-182 cap 0.08) |
| S05_SH020 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 1.398 (engineering default 0.2) |
| S06_SH001 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.443 (engineering default 0.2) |
| S08_SH002 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.344 (engineering default 0.2) |
| S08_SH003 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 0.409 (engineering default 0.2) |
| S08_SH003 | REVIEW | near_plane_travel | near plane travel 0.034 of the width (plan P5.2: (0.04, 0.06); BP-182 cap 0.08) |

Cause summary: `face_landmarks_steady` is landmark jitter on small painted faces (11 shots, default 0.2, worst 1.40); `near_plane_travel` 0.026-0.034 of the width under the plan's 0.04 (5 shots, the camera moves are gentle by design); `map_not_standing_still` (BP-164, 6 frames) on the 5 maps because the actions sit on the narrator's words and the plate has no idle motion between them (journal FL-215). None is a FAIL.

## Rehearsal-only FAILs (video lane)
| Shot (video lane, rehearsal fallback) | Status | Gate | Measured |
|---|---|---|---|
| S03_SH003 | FAIL | faces_rigid | each face lies in one plane (worst share 0.689; one affine, no warp inside it) |
| S03_SH009 | FAIL | faces_rigid | each face lies in one plane (worst share 0.727; one affine, no warp inside it) |
| S05_SH005 | REVIEW | planes | 1 depth planes (BP-181: at least 3) |
| S05_SH005 | NOT_RUN | no_edge_tears | no plane border measured (one plane) |
| S05_SH005 | REVIEW | face_landmarks_steady | landmark geometry drift, worst 1.667 (engineering default 0.2) |
| S07_SH006 | FAIL | faces_rigid | each face lies in one plane (worst share 0.554; one affine, no warp inside it) |

## Open items
1. S07_SH005: the LTX thread says it has no clip (TD-324 from the audit thread: option c, script untouched until the owner answers the re-make question; then data-only fix: route still_25d, shots into the air + muzzle smoke + steam, no flag).
2. FL-216: the runner keeps only the status word of a gate, not its rows; I wrapped `qa.gates.verdict` to read them (no repo change).
3. Real G7 after the LTX ingest, then G8/G9 belong to the assembly thread; voice cleanup RC-004 and the sound guide are theirs (audio is not part of my lane).
4. Journal part: `DEMO_JOURNAL_part_clips_G7.md` (FL-215..217, DV-205, NT-204/205, MS-202..204).
