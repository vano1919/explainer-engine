Task: fix fail-open gate parsing in explainer_engine/qa/technical_gate.py. Tests: tests/unit/test_technical_gate.py.

1. _parse_blackdetect(text) and _parse_freezedetect(text) currently count only closed intervals. A "black_start:<t>" or "freeze_start:<t>" with no matching end/duration line (a run that lasts to the end of the stream) is ignored, so the ratio is wrong. Change both to accept a second argument total_duration: float. A dangling start is closed at total_duration. Keep the closed-interval behaviour unchanged. Make the parameter required in the signature and update the single caller in _ffmpeg_filter_seconds (pass duration through: change _ffmpeg_filter_seconds to take the duration and pass it to parser via a lambda or functools.partial).
2. measure_video: if duration is 0 (or below 1e-6) raise RuntimeError("video duration is zero") before dividing. Currently it would raise ZeroDivisionError.
3. Tests to add (pure, no media):
   - _parse_blackdetect with a text containing only "black_start:9.0" and total_duration 10.0 returns 1.0.
   - _parse_freezedetect with "freeze_start: 7.0" and total_duration 10.0 returns 3.0.
   - closed intervals still sum as before (keep the existing tests passing).
   - the existing end-to-end test test_measure_video_fills_filter_keys: strengthen to assert black_frame_ratio == 0.0 and that sharpness is a float >= 0.0 (do not remove the not-None checks).
Do not change any threshold value. Run: python -m pytest -q tests/unit/test_technical_gate.py
