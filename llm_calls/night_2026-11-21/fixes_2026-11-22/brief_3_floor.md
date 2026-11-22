Task: re-set the provisional sharpness floor after the unit change. Files: explainer_engine/qa/technical_gate.json, tests/unit/test_technical_gate.py.

Measured on the 24 existing project samples in the NEW unit (laplacian_var_over_gray_var_0_1): min 0.02414, median 0.03383, max 0.6018.
1. In technical_gate.json set video.min_sharpness and photo.min_sharpness to 0.02 (rounded down from the lowest sample, 0.0241).
2. Replace the text of video.sharpness_basis AND photo.sharpness_basis with: "GUESS: floor at 0.02, rounded down from the lowest of 24 existing project samples (0.0241, measured 2026-11-22 in laplacian_var_over_gray_var_0_1); catches blank or badly blurred output only. Not a quality threshold; the owner sets it on approved samples."
3. In tests/unit/test_technical_gate.py: the boundary violation value that was 0.0019 must become 0.019 (just below 0.02); any other test that relies on the old floor 0.002 must use the new value. Passing values (0.05 or 0.6) stay.
Do not change any other number. Run: python -m pytest -q tests/unit/test_technical_gate.py
