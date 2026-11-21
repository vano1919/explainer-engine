# Local, free checks (2026-11-21, 22:13 UTC)

Status: NO gate passed. No paid run. Test inputs are synthetic, not the owner's samples.

1. 2.5D no-melt (living.py, shot S07_SH008, 1 s, synthetic 1920x1080 gradient photo, depth from the new Apache-2.0 model):
   - Ran end to end. Output 1280x720, 24 fps, 861 kb/s.
   - Telemetry: person_share 0.0 (no person in the synthetic photo), plume area ~4–6 %, no violations.
   - Technical gate: FAIL (not measured): black_frame_ratio, frozen_frame_ratio, sharpness are not computed by measure_video; fail-closed as designed. Resolution 1280x720 is below the 1920x1080 minimum.
2. Map frames (960x540, Toba test spec, frame 24): before, bold, light saved. Unset MAP_PRESET is byte-identical to before.
   - Technical gate: FAIL on size (test size is 960x540 by choice).
   - Laplacian variance: before 1353.5, bold 1374.3, light 1296.6. The gate's min_sharpness is 0.5 in a unit the measurement does not use. The two are not comparable: unit mismatch to fix before any sharpness limit is trusted.
3. Bridge: visibility by narration timing is tested (visible_at). Not yet in the render path: no caller exists in maps/render.py.

Open before any paid run: real owner samples (not synthetic), the 1920x1080 render size, sharpness method (one unit), black/frozen metrics computed, and the bridge caller in the render path.
