# Opus medium technical check of the night's changes (2026-11-22, API)

Scope: the diff of claude/project-thread-3j9l41-modal-render since e6040b8 (explainer_engine, tests, config; 20 KB, patch saved here). Review only, no code changed by this check.
Not reviewed in this run: PRs 257, 258, 259 and the other night branches. Their diffs against main are not comparable (main shares no recent history with them; `git diff origin/main` lists about 1195 files), so they need a per-branch review with a diff against each branch's own parent. Not done tonight.

Spend (job line opus_tech_check, cap 10.0 USD):
- stream-proof call on Haiku (required first call): $0.000004
- Opus first attempt, max_tokens 6000: hit the limit during thinking, $0.1613 paid, no answer
- Opus second attempt, max_tokens 16000: $0.174
- total this check ~ $0.336 (ledger _ledger_total_usd 0.33526). No other paid call. Claude API cap 50 not exceeded.

Verdict from the model: PASS WITH FIXES. Nothing blocks the merge. Full text: out2/night_modal_render_review.md.

Should-fix items (none applied):
1. qa/technical_gate.py: a black or freeze run that is still open at the end of the stream is not counted, so a clip whose last seconds are frozen can pass with ratio 0 (fail-open). Fix: close a dangling start at the duration.
2. qa/technical_gate.py: sharpness divides by mean^2, which inflates dark frames. The guess floor does not catch dark blurred output as its JSON text claims. The unit needs a decision by the owner.
3. maps/render.py: fps defaults to 24 silently; a 25 or 30 fps spec would mistime captions. Take fps from the spec or raise.
4. maps/render.py bridges_from_words drops fill and ink, so per-item colours are lost silently.
5. tests/unit/test_bridge_caller.py: frame 48 is outside a 48-frame clip; edge frames 23/24 and 71/72 are untested.
6. technical_gate.json: the photo min_sharpness 0.002 has no GUESS marker.
7. Blackdetect and freezedetect parameters (pix_th 0.10, d 0.1, n 0.003, d 0.5) are hard-coded, not in the JSON. Freezes shorter than 0.5 s are never counted.
8. Upscaled 1080p: the gate's size check passes on interpolated frames. Sharpness floor was not measured on upscaled output.

Nits: duration 0 raises ZeroDivisionError; a bool or float16 mask would break cv2.resize; a test is fragile at rel=1e-4; the end-to-end test asserts only "not None".

Decision for the owner or coordinator: apply the should-fix items through the DeepSeek worker (free within the weekly cap, small) in a follow-up commit, or leave them as listed. Not applied tonight.
