You are a senior Python engineer. This is a BINDING code task: do exactly what it says, nothing more. Answer in ONE reply (this chat has room for one exchange; do not ask questions first: when something is ambiguous, choose the safer option and list it under ASSUMPTIONS). English only.

ATTACHED `code_task_inputs.zip`:
- `repo/...`: the exact current files (head 302c8dd of my repo "Explainer Engine") that you may change, plus their tests. Rulebook: `repo/CLAUDE.md` (read it first). Numbers a rule enforces live in `repo/explainer_engine/standards/sourced_rules.json` (read via `sourced_rules.py`, e.g. `SR.T("BP-21", "rate_min_per_s")`); rule D-59: a threshold that is only an engineering hypothesis stays REVIEW; FAIL needs a calibration on at least one known-bad and one known-good case, recorded in the comment.
- `context/ARGON_PLAN_session1.md` and `context/ARGON_FOLLOWUP_session1.md`: the plan and code sketches an earlier session wrote (Claude Opus verified its code claims). Use them as design input, not as code to paste blindly.

THE TASK (plan steps 1 and 2; CPU only, no new dependencies beyond numpy/opencv already used):

T1. `explainer_engine/episode/run.py`, stage_sound (around lines 821-840): today, if any LTX dialogue insert clip record is missing, the code silently keeps the unsplit narration over the insert-expanded timeline (a 54 s voice desync in S05). Change it: when `missing` is non-empty and the run is NOT a rehearsal, raise `ContractError` naming the missing shot ids; in a rehearsal, build the voice track with exact-length silence in place of each missing insert (so timing still matches) and add a REVIEW row that names them. Never fall back to the unsplit narration.

T2. `explainer_engine/production/directed25d.py`, `_rest_background` (lines ~174-227): remove the morphological "bite" that cuts thin parts out of a kept layer's alpha (the `MORPH_OPEN` parts subtracted from `o["alpha"]`, and the REST_ALPHA_GAIN dilation that exposes the plate round outlines). New rule: measure the object's thin-stroke share with the same opening; if share >= THIN_SHARE_MAX (new constant 0.35, engineering default) the whole object stays on the background (not layered); otherwise keep the mask whole with a soft inward feather (~3 px at 1080p). Frame 0 must equal the source picture inside every layer (rest_seam stays at the C4A-fixed level, <= 0.04).

T3. `directed25d.py`, before `bg_maps` warps the background (lines ~590-604): inside every person/face box that stays on the background sheet (people not layered, e.g. a crowd), flatten `bg_depth` to the box's median with a soft edge, so the per-pixel remap moves those people rigidly and never stretches faces.

T4. `explainer_engine/production/living_director.py`, `choose_camera` (line ~413): when a shot has a trigger word, the pre-word base move uses RATE_MIN, which reads as static. Use a pre-accent floor `max(RATE_MIN, PRE_ACCENT_RATE)` where PRE_ACCENT_RATE is read from sourced_rules.json (add a new entry under BP-21's id, e.g. `pre_accent_rate_min_per_s`: 0.018, status hypothesis/engineering default, with reason: the creator saw 0.5 %/s holds as static). Keep everything else in that function unchanged.

T5. `explainer_engine/qa/motion_intent.py`: add check `sliding_liveliness` (no dead second): over every sliding 1.0 s window, the share of pixels whose luma changed by more than 2 levels between the window's first and last frame (at 480x270); REVIEW below 1.5 % (hypothesis). Promote `blown_out` to FAIL at 0.015 (calibration exists in its comment: C5 10-13 % bad, untouched 0.0-0.5 % good). Do not promote any other REVIEW check.

TESTS (required, pytest, no model weights, synthetic numpy images only): for each of T1-T5 at least one focused test that FAILS on the old code and PASSES on the new one, e.g.: T1 missing insert -> ContractError, rehearsal -> silence of exact length + REVIEW row; T2 a person mask with a thin rifle: frame 0 identical to source inside the outline, a wire-only object is not layered; T3 a crowd box on a depth ramp moves rigidly (no stretch inside the box); T4 a shot with a trigger word gets rate >= 0.018; T5 a 2 s clip frozen for 1.2 s in the middle -> REVIEW row; a burned sky 3 % -> FAIL. Update existing tests in `tests/unit/` only where they pinned the old behaviour, and say which and why.

RETURN (as Canvas files or code blocks):
1. Every changed file IN FULL (not diffs), with its repo path as the heading.
2. New test files in full.
3. CHANGES.md: per task, what changed (function + line area), and which old tests changed and why.
4. ASSUMPTIONS and NOT CHECKED (you cannot run the suite here; say what a reviewer must run: `python -m pytest -q tests/unit/test_directed25d.py tests/unit/test_living_director.py tests/unit/test_motion_intent.py tests/unit/test_c4a_review_fixes.py tests/unit/test_v43_runner.py` plus your new tests).
Do not refactor, rename or reformat anything outside these tasks. Keep the repo's comment style (labels like "engineering default", rule ids).
