## 2026-11-21 — Still-region and person-flow measurements (`qa/still_region.py`), measured on existing renders
- New module (numpy + OpenCV, free): `still_region_report` (median/p95 change, added noise, sharpness ratio, Lab shift over a region minus an exclusion)
  and `flow_in_region` (optical flow against the original, in pixels: a person bent by haze or sway shows as flow on the person mask).
  No judging number is sourced or approved by the owner, so the verdict is NOT_RUN with the measured numbers unless the caller passes `limits`
  (never a PASS by default, same rule as `audio/val_effect_audibility.py`).
- Measured on the existing smoke clips (HF `explainer-engine/comparisons/L14/still_region_measure_2026-11-21/`): the h264 round trip alone gives
  median change 2.3, noise 1.26, flow 0.017 px; S07_SH008 background is 2.9 / 1.75 / 0.09 px, S07_SH006 background 9.0 / 2.5 / 0.5 px (mist, snow
  and light included). Flow on people near the fire is 0.72 px (p95 2.3) against 0.19 px away from it on S07_SH008: the fire deformation and haze move people.
- Tests: `tests/unit/test_still_region.py` (identical frame, added noise, blur and colour shift, exclusion, limits PASS/FAIL, NOT_RUN for bad input, flow).
- Not run: new renders, any gate wiring, any limit.
