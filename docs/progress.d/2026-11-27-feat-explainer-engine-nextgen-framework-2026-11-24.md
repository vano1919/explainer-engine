## 2026-11-27 — v5 cinema hardening: plate bans, dialogue floor, gentler conversation sound
- Done: `extract_axis_locked_coverage_plates` raises; new gates `check_no_cropped_seed_plates` and `check_no_cutout_compositing` in `qa/cinema_gates.py`, wired into `run_full_cinema_audit` (`enforce_v5_contracts`); `DialogueWordClippedError` in the timeline compiler and the stitcher; `plan_dialogue_j_l_cuts`, `render_dialogue_scene_track` and one room-tone bed per dramatic scene; `clean_ltx_dialogue_stem` re-tuned and speaker levelling added. Rules BP-214..BP-217 (house).
- Dependencies declared that the code already imported: `soundfile`, `rasterio`, `playwright`.
- Changed test: the v5 loop-1 coverage-plate test now expects the ban; the loop-4 compiler test gives its dialogue shot speech times.
- Limits: the manifest part of the cutout gate judges only shot entries that declare `characters`; the 2x2 contact-sheet slicer (`studio/popcorn_storyboard.py`) is unchanged and not covered by the crop ban.
- Not done: the existing v5 master was not re-rendered.
- Test: `tests/unit/test_v5_hardening_bans.py`.
- Cost: $0.00 (local only).

### Integration of the v9/v10 acting and lip-sync work (creator's choices, 2026-11-27)
- Taken: lazy `playwright`/`rasterio` imports, the `LOYAL LEGIONS` layout fix, relative paths in `ides_v5_loop5_batch_m4.json`, the closed-mouth clause for silent shots and the active acting style, `check_shot_plate_diversity`, `check_acting_dynamics_and_freeze` (thresholds from BP-211 and the new BP-218).
- Changed: the crop helper stays banned (BP-217); the duplicate `validate_native_keyframe_plates` is not taken (it also refused the real 1280x704 plates). `validate_acting_blocking_prompt` matches whole words.
- Speaking close-ups (BP-205 changed by the creator): allowed only through the voice-first route. `lipsync_pipeline.require_voice_first_inputs` and `ltx_loop.validate_dialogue_framing` refuse a close-up without its WAV; the shot loop sends an `a2v` request with the WAV's sha256, needs a refinement stage for a close-up and accepts the clip only when the mouth gate passes; VL-02 in `videolane/plan.py` passes a speaking close-up only with a declared `lipsync` route.
- Mouth gate rebuilt (BP-219): `check_mouth_motion_sync` tracks the face (YuNet when installed, else scikit-image's bundled LBP cascade) and removes the head's own motion. On the v5 clips: 11 of 12 dialogue clips with a face pass (0.34-0.69), `b4_artemidorus` fails (-0.06), 3 have no detectable face (NOT_RUN); the 4 silent clips with a face pass (1.34-2.00). The earlier frame-centre version failed 7 of 15 dialogue clips.
- New LatentSync 1.5 refinement worker `training/pods/latentsync/` with pinned code, weights and VAE (`config/cloud_pins.json` `models.lipsync_latentsync`). It cannot run yet: `base_image` and the face-detector zip's sha256 are open, and `config/spend_caps.json` has no `modal_latentsync` line. Not run, nothing paid.
- Tests: `tests/unit/test_v5_loop5_acting_lipsync_hardening.py`, `tests/unit/test_latentsync_worker.py`.

### Stack-2: no ElevenLabs REST call (2026-11-28)
- Changed: `cloud/hybrid_api_clients.run_elevenlabs_v4_tts` keeps its dry run and refuses a live call before reserving money; speech goes through the ElevenLabs connector, its hook and ledger (D8).
- Consequence: a live (not dry-run) `cli/stack2_runner` run stops at the first shot routed to ElevenLabs.
- Not changed: `audio/elevenlabs_narrator.py` still calls the REST API, so `test_there_is_no_elevenlabs_rest_client_in_the_package` still fails on it.
- Test: `tests/unit/test_v6_stack2_full_launchers.py`.
- Cost: $0.00 (local only).
