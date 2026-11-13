# Handoff: clips lane (map_action + still_25d), Truce 1914 script A (2026-11-13 ~22:00 UTC)

State: rehearsal G7 done for my 28 shots, $0, 0 FAIL, 17 REVIEW (causes: STAGE_REPORT_clips_G7.md). The real G7 runs once after the LTX ingest.
- Script A 261d43b8...17366 (episodes/ep_truce_1914/story/production_script.json, repo commit 28f0615); episode.json c85da546...
- Pictures: final_scene_frames_A_v5.json sha f2e5a232...; G5 PASS on those files. Ledger planning/picture_ledger.jsonl (untracked, last accepted row per id wins).
- Clips on HF: https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/explainer-engine/demo_truce_1914/clips/own_lane_g7_rehearsal (MANIFEST.json has sha256 of each mp4; 28/28 verified).
- Local cache: episodes/ep_truce_1914/production/shot_clips/ (gitignored). The runner reuses a clip when shot data, picture sha, clock and paths are unchanged.
- Waivers used: RC-005 (parallel lanes trial), RC-006 (G5 no_letterbox waived for the end card S08_SH004 only).
- Open: S07_SH005 has no LTX clip (audit TD-324, option c: script untouched until the owner answers the re-make question; fallback = data-only fix to still_25d with new sha); 5 map REVIEWs BP-164 (FL-215); variant B keeps the BP-185 defect on its 39 stills (not touched); Gemini prepay credit depleted (any further paid picture needs a top-up).
- Not mine: audio (RC-004 voice cleanup, loudness, beds, sound guide), G8/G9, publishing.
- Journal part: DEMO_JOURNAL_part_clips_G7.md (FL-201..217, DV-201..205, NT-201..205, MS-201..204).
- Lessons: gate rows are not stored in the clip record (FL-216); the project-files mount rewrites a fresh file about 1 s later, hash only after 10 s and never reuse an old file name for a changed picture (FL-213).
