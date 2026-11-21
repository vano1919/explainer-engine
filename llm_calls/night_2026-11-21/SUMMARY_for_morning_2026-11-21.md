# Overnight summary, 2026-11-21 (Haiku helper, thread 3j9l41)

Paid runs: none. Modal $8 approved by card, not spent. Claude API ~ $1.9 spent earlier tonight, DeepSeek ~ $0.72 of the $10 week cap.

## Branches (HEAD at time of writing, 23:05 UTC)
- claude/project-thread-3j9l41-modal-render: 279ba10c. Render fixes (1920x1080 output, one sharpness unit, measured black/frozen, bridge caller), GUESS sharpness floor 0.002, local gate NOT PASSED, QUALITY_SPEC TBD list, provenance record, known-debt record.
- claude/project-thread-3j9l41: 35d33a37 (night results, llm_calls/night_2026-11-21/).
- claude/project-thread-3j9l41-p5, -options, -budget50, -techgate: as in the earlier report.

## PRs
- 256 review (do not merge), 257 (P5, provisional), 258 (P6, provisional), 259 (P7.3 lint): no rebase needed, main has no commits they lack.
- 201, 205, 229, 244: open drafts, owner decides.

## Test status
- Full unit suite (fb7f229b): 5155 passed, 5 failed, 26 skipped, 1 xfailed. The 5 failures are tests/unit/test_v43_picture_intake.py, failing on base e6040b8 too. Recorded in llm_calls/night_2026-11-21/KNOWN_DEBT_test_v43_picture_intake_2026-11-21.md.
- P6 tests on the P6 branch: 21 passed, 3 skipped.

## Gate
- 1920x1080 2.5D test clip (1 s and 5 s): NOT PASSED. Frozen and sharpness fail on the synthetic picture; bitrate fails only on the test clip (real samples 4.7–40.6 Mbps).
- Sharpness floor 0.002 is a GUESS from 24 existing project samples (range 0.0022–0.057). It is not a quality threshold. The owner sets it on approved samples.
- Details: llm_calls/night_2026-11-21/render_compare/RESULTS_local_1080_2026-11-21.md

## Open for the owner
- Sharpness and frozen thresholds on approved samples.
- Fable routing for medium (needs a recorded word).
- PR 256 split; PR 201/205/229/244 decisions.
- QUALITY_SPEC: receipt field names, effect allowlist, photo/human mask source, and the four open questions (llm_calls/night_2026-11-21/QUALITY_SPEC_TBD_RESOLVED_2026-11-21.md).
- Upscale note: 1920x1080 frames are upscaled from the 1280x720 working space; no new detail.
