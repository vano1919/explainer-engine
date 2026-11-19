# Director guide: perception, interpretation, direction, and feedback

Machine-readable source of truth: `explainer_engine/standards/director_knowledge_base.json`. See also [EPISODE_FIRST](EPISODE_FIRST.md) (D-131, D-135) and [SOURCED_RULES](SOURCED_RULES.md) (BP-109, BP-185, BP-195, BP-196, BP-200, D-59).

## 1. Five-stage directing chain

1. **Perception (`production/perceive_picture.py`):** Reads `start_01.png` and `layers/manifest.json` (`production/understand.py`) to record measured object centroids, bounding boxes, support bases, sky bounds, active light emitters, confidence, and uncertainty. A missed detection is recorded as uncertain, never as proof of absence.
2. **Interpretation (`interpret_scene`):** Reconciles the perceived picture with `shot.director_brief`, spoken `audio_lines`, historical context, and adjacent shots (`ALIGNED`, `ADAPTED_STAGING_NON_BREAKING`, `UNCERTAIN_NEEDS_REVIEW`, or `STORY_BREAKING_CONFLICT`).
3. **Direction (`production/living_director.py`):** Selects camera paths (`<= 5.0 s` per `still_25d` sub-shot via `episode/shot_split.py`, BP-109), anchor-preserving framing (`keep_in_frame`), physically isolated living effects (`production/motion_isolation.py`), and sound decisions (`choose_sound`, `sound_of_direction`, `sound_of_map`).
4. **Execution (`production/directed25d.py`, `production/map_clip.py`, `episode/sound_plan.py`, `production/assemble.py`):** Renders clips and the authoritative post-direction sound plan and mix.
5. **Re-Perception & Feedback (`qa/look_and_listen.py`, `qa/perceive_audio.py`):** Perceives the rendered frames and audio again, comparing them against the director's decision record before packaging the look-and-listen bundle for Claude's review.

## 2. Stillness vs. broken output

No numeric effect count or family count decides artistic quality. A deliberately still shot (`DELIBERATELY_STILL`) passes when the director records a written reason (`stillness_reason` / `why` per BP-196). Accidentally frozen renders (`ACCIDENTALLY_FROZEN`) and technically broken renders (`TECHNICALLY_BROKEN`) fail in QA.
