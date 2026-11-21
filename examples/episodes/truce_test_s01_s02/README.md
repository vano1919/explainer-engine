# Truce 1914 test film S01-S02 (build_episode demo, v2)

Ten shots: S01_SH001-005 and S02_SH004-005 are the seven new-style photos (HF `explainer-engine/demo_truce_1914/new_style_B_2026-11-19/`), S02_SH001-003 are map
shots (`truce_cold`, minimal front traced from the public-domain West Point map, approximate, not a claim source). The narration is the existing read of the
demo (HF `explainer-engine/demo_truce_1914/audio/reads/`, no new paid audio). The shot list came from `plan_from_shot_plan` on the HF `shot_plan.json`.
Media are not committed: put the photos in `media/photos/` and the reads (`S01_L001.mp3` ... `S02_L005.mp3`, `lines.json`, `durations.json`) in `media/reads/`.
Run: `python -m explainer_engine.production.build_episode examples/episodes/truce_test_s01_s02/episode.json out.mp4 --tile-dir <map tiles> --cache-dir <depth cache>`.
The living effects per photo are minimal and written from the contact sheet (fire + smoke on the brazier of S02_SH005 with the soldier and the letter as person zones,
snow only on S01_SH005 by the plan's cold rule, mist and sky elsewhere); every number is a default of the spec, not an owner decision.
