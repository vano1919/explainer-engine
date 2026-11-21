# Decision: Claude budget $50 (2026-11-21, 21:48 UTC)

Owner words (cmsg_01Hnu5zB86sjUj5GtTgaUkPWU86xfQSP7W7oPE2qg2ka7R): "$40 for Claude code writing, and separately an Opus medium $10 limit for technical checks." Relayed by the coordinator with the same numbers.

Applied on this branch only (from the $40 caps branch claude/project-thread-gi6ebh):
- claude_api.max_usd 40.0 -> 50.0
- opus_code 15.0 -> 40.0
- opus_tech_check 0 -> 10.0 (new line, Opus medium technical checks)
- fable_medium 15.0 -> 0.0 and opus_high_review 10.0 -> 0.0 (the $0.76 already used is counted in the total)
- sum of lines = 50.0 = max_usd
- test pinned to the old numbers updated to the owner's words (tests/unit/test_claude_api.py)

Tests: tests/unit/test_claude_api.py, test_claude_api_limits.py, test_opus_code.py: 149 passed.

Not decided: whether opus_tech_check needs its own routing class (job label only for now). Route check and class mapping to confirm before the first call.
