You are an independent senior code reviewer (Python, OpenCV, video). Another Gemini session wrote the patch below; Claude Opus applied it to the real repo and ran the tests. Review it hard, then fix only what is wrong. Answer in ONE reply, no questions first. English.

ATTACHED `review_inputs.zip`:
- `review/argon_code_task1.patch`: the full diff against head 302c8dd of my repo "Explainer Engine" (tasks T1-T5: no silent voice desync when an LTX insert is missing; 2.5D layers without morphological bites; crowd depth flattened before the background warp; pre-accent camera floor 1.8 %/s; a sliding no-dead-second check and blown_out promoted to FAIL).
- `review/CHANGES.md`: the author's own summary. `review/OPUS_VERIFY.md`: what Claude measured on the real repo (new tests 7/7 fail on old code and pass on new; old focused suites 76/76 alone; three defects found).
- `repo_after/...`: the changed files in full after the patch, plus `events.py`, `videolane/voice.py`, conftest and the rulebook `CLAUDE.md` for context.

DO:
1. Confirm or reject each of the three defects in OPUS_VERIFY.md, with the line text.
2. Find what Claude did not: logic errors, wrong behaviour on real data (1080p/1440p pictures, real Truce shots), changes outside the task, thresholds that break rule D-59 (a hypothesis stays REVIEW; FAIL needs a known-bad and known-good calibration), tests that pass for the wrong reason or pin nothing, frame 0 no longer identical to the source picture, performance (a 5 s 1080p clip must stay CPU-cheap).
3. Fix: return IN FULL every file you change (repo path as heading). At minimum: `tests/unit/test_plan_steps_1_2.py` without touching `sys.modules` through private APIs (use `monkeypatch.setitem(sys.modules, ...)` or patch names in `explainer_engine.episode.run`'s own namespace) so it can run in one pytest session with the rest of the suite; `explainer_engine/episode/run.py` without `_compose_rehearsal_voice_fallback` (raise ContractError when voice_track.wav is missing after VV.compose). Do not refactor anything else.

OUTPUT, short: (a) a findings table: # | severity BLOCK/FIX/NOTE | file + line text | problem | fix; (b) the changed files in full; (c) the exact pytest command a reviewer must run; (d) NOT CHECKED.
