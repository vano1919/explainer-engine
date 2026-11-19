# Screenwriter guide: the director brief and sequential emotional continuity

Machine-readable source of truth: `explainer_engine/standards/screenwriter_guide.json`. See also [STORY_ENGINE](STORY_ENGINE.md) and [EPISODE_FIRST](EPISODE_FIRST.md) (D-131).

## 1. Purpose of the screenwriter's director brief

The screenwriter stage (`edit-planner`, guarded by `explainer_engine/scripting/stage_guard.py`) writes a free-text `director_brief` on every shot in `production_script.json`. The brief is a written note from the screenwriter to the Scene Director describing:

- `mood`: free-form emotional and atmospheric register of the shot (never a closed enum or numeric effect budget).
- `viewer_feeling`: what the viewer must feel during this spoken line.
- `physical_truth`: the concrete physical reality, weather, temperature, and light of the place.
- `focal_priority`: ordered visual focal targets tied to the spoken clauses of `audio_lines`.
- `sound_perspective`: free-form acoustic point-of-view (foreground foley, environmental bed when appropriate, J/L bridges, or intentional silence).
- `restraint_note`: explicit boundaries on what must not be over-animated, cropped, or cluttered.

## 2. Authored intent vs. approved visual staging

When an approved picture (`start_01.png`) differs from unvoiced staging prose in `screen_composition` or `action_start_state` without contradicting the spoken `audio_lines` text (for example, `S02_SH008` showing a tin mug rather than a letter, or `S08_SH002` showing an open snow-lined trench rather than a dugout bunk), the original prose is preserved in `authored_intent_archive` while the director directs the physical picture. If a painting contradicts a noun or action spoken in `audio_lines`, the shot is queued in `production/regeneration_queue.json`.
