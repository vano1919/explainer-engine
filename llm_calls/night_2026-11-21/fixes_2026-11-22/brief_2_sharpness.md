Task: change the sharpness unit in explainer_engine/qa/technical_gate.py, add a provisional-marker to the photo limit, and fix two test weaknesses. Files: technical_gate.py, technical_gate.json, tests/unit/test_technical_gate.py.

DECIDED UNIT (do not change it): sharpness = variance of the Laplacian of the grayscale frame (values scaled to 0..1) divided by the variance of the grayscale frame itself (values 0..1). If the frame's standard deviation is below 2/255 (flat or near-black), return 0.0. Scale-invariant to brightness and contrast, so a dark blurred frame is not inflated.

1. Rewrite sharpness_from_gray(gray) accordingly. Keep the name and signature. Use float64; add a guard: std < 2/255 returns 0.0; empty input returns 0.0.
2. Keep measure_video_sharpness(path, samples=8) using sharpness_from_gray (median of samples). Do not change its other behaviour.
3. technical_gate.json: change the video "sharpness_unit" string to "laplacian_var_over_gray_var_0_1" and the photo "sharpness_unit" to the same. Keep min_sharpness 0.002 for video and photo. Add to the photo block a key "sharpness_basis" with the same GUESS text that the video block has (copy the video block's text). Do not change any other number.
4. Tests (update tests/unit/test_technical_gate.py; do not delete existing assertions):
   - flat gray frame returns 0.0 (exact).
   - a dark frame scaled by 0.05 of a checkerboard gives the same value as the bright checkerboard (within rel 1e-3), proving brightness invariance. Use a checkerboard with values 0 and 255 scaled to 0 and 12.75 for the dark one; both have the same std ratio, so the values must agree within rel 1e-3.
   - a near-black noise-free frame with std below 2/255 returns 0.0.
   - the violation test for sharpness in check_video: the value 0.49 used for the old floor is replaced by 0.0019 (just below the 0.002 floor) so it probes the boundary; keep the test name.
   - remove any test that asserts the old mean-squared normalisation; replace it with the brightness-invariance test above.
Run: python -m pytest -q tests/unit/test_technical_gate.py
