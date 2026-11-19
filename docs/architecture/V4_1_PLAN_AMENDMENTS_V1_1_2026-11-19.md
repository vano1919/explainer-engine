# Plan amendments v1.1 (2026-11-19, plan owner)

Source: Gemini Neon's review (`GEMINI_NEON_PLAN_REVIEW.md`), checked against the code. These change
`FINAL_ACTION_PLAN_STEP0_STEP1.md`; where the two differ, this file wins.

- **0.1:** explain the 4 extra skipped tests on PR #196 (24 skipped vs 20 on `fc35615`) and the 3 deselected tests. List
  them with their skip reasons in the 0.3 PROGRESS entry. Nothing may be skipped to get green.
- **0.3:** the decision row records two things explicitly: (a) the reversal of the 2026-11-13 07:49 UTC "yes, BBC too" card
  for monetised masters; (b) precedence: where MA-01..MA-18 correct the PR #195 plan, the MA wins, with a short conflict
  table. It also carries a **field contract** for the new Step 1 record fields (`picture_check`, `mute_tail_from_s`,
  `start_frame_check`, `route_proposals`, `third_party_media`, `unresolved_reviews`). Gemini's G2 schemas follow that contract.
- **0.4a:** also add `docs/architecture/v4_1_allowlists.json` and `.github/workflows/quality.yml` to `protected_files`, in the
  same edit and covered by the same typed word from the creator.
- **0.4b:** `actions/checkout` with `fetch-depth: 0`. Explicit PR-to-slice binding: either the branch name carries the slice
  id, or the PR body has a `V4.1-slice: <id>` line; pick one and document it. A PR without a slice id is not a V4.1 slice and
  is not checked. A V4.1 slice PR with an unknown id fails.
- **1.1:** (a) before locking the allowlist, find every caller and test of `scene.build`; the fixture updates fail-closed
  needs (new valid perception fixtures, never weakened assertions) go into 1.1's allowlist. (b) A shot recorded as a
  continuation needs a prior shot in the same scene that passed its own check, otherwise it is refused. (c) `job_spec`
  already re-hashes the start picture (`scene_run.py` L86-87); add a test that a picture changed after `build` is refused.
- **1.2:** `qa/sound_realism.speech_spans` measures speech-band energy against percentiles. It is not a voice detector, so
  "energy supports the word" cannot reject the S07_SH005 gunshots or loud ambience. Use a voicing classifier: Silero VAD
  through faster-whisper (`vad_filter`; faster-whisper is already the optional dependency of `audio/local_words.py`), or a
  harmonicity check when VAD is not installed. The record says which one ran. Clamp word boundaries to the overlapping
  voiced span and never keep Whisper's raw start. Add synthetic adversarial unit cases: a gunshot with a hallucinated word,
  steady loud ambience, quiet speech over a low floor, a zero-speech clip. The six-clip expected verdicts stay open until
  Gemini's blind G1 observation and the creator's short listen are in. Code and synthetic tests can start now.
- **1.3:** unresolved REVIEW items are counted into `unresolved_reviews`, which `publish_check.py` prints (non-blocking until
  QA severity, Step 5).
- **1.4:** `qa/third_party_media.json` covers every media input: sounds from `stems_report.json` (SFX, beds, music), the read,
  LTX clip audio, pictures and archival documents from their records. A class with no provenance record yet is REVIEW and
  listed by name, never PASS. Blocking visual licence gating may follow in Step 2, but the list shows visual items from the
  start. A `DO_NOT_MONETISE` marker that `publish_check` recognises goes on `render/pass1` (BBC). The creator auditions every
  replacement take, not one per pool.
- **1.5:** before the parity slice, a one-page feature matrix: G8 vs `mix.py` (narration, inserts, beds, music, ducking,
  LUFS and true peak, dips, LTX audio) and G9 vs `build_segments` (trim contract, cache key, single resize, overlay
  authority, Truce dips, ±1 vs exact frames). Whatever G8/G9 lack becomes 1.5's allowlist, decided from the matrix and not
  discovered by the slice. Parity rules: frame counts exact; video by SSIM/PSNR thresholds unless the filter graphs are
  identical; audio by LUFS, peak and the library-take log. `mix.py`'s refusal compares resolved paths.
- **Gemini G1:** it runs in a fresh chat. The Neon chat read F6, so it is no longer blind. G1 classifies what happens in each
  clip; the creator's listen fixes the contested timestamps.
- **Not accepted:** dropping the Chrome bridge. It is how Gemini gets the messages without the creator copying text.
