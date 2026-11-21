# Known debt: 5 failing tests in tests/unit/test_v43_picture_intake.py (existing, not caused by tonight's work)

Failing on the current branch claude/project-thread-3j9l41-modal-render (fb7f229b, full unit suite 2026-11-21 23:00 UTC: 5155 passed, 5 failed, 26 skipped, 1 xfailed):

- test_intake_accepts_a_native_picture_as_a_draft_and_rejects_bad_ones
- test_promote_is_not_run_without_an_upscaler_and_gates_the_master
- test_a_master_under_the_long_side_stays_a_draft
- test_export_after_intake_resumes_with_what_is_still_open
- test_an_identity_miss_is_review_and_listed

Evidence that it is pre-existing: the same file run on base commit e6040b8 (before tonight's render fixes) gives "5 failed, 16 passed", with the same five tests.

Not investigated tonight: the cause of each failure. Files touched tonight (living.py, render.py, technical_gate.py/.json, bridge tests) are not imported by this test file, so they are not the cause on the evidence above.
