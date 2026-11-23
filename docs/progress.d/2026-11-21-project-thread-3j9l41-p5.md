## 2026-11-21 — P5: camera-move agreement test

### Done
Added `tests/unit/test_camera_moves_agree.py` (5 tests, all pass). Checks the five map camera moves are identical in `qa/delivery_gate.py` and `maps/maplibre_spec.py`, and that `maplibre_spec` rejects orbit and static.

### State
The five-move rule was already enforced; this test only guards drift. No renderer or preset change. Map presets from QUALITY_SPEC provisional limits NOT done.

### Files
- `tests/unit/test_camera_moves_agree.py` (new).

### Tests
`python -m pytest -q tests/unit/test_camera_moves_agree.py` → 5 passed.

### Decisions
None taken; thresholds still provisional, owner approves T1–T10.

### Cost
DeepSeek Flash about $0.003. No Claude paid call.

### Next step
Map presets and bridge sync, after owner approval of T1–T10.

### Recovery
Branch `claude/project-thread-3j9l41-p5` from `claude/p5-map-presets-provisional`.