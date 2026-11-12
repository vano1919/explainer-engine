# Episode-first contract (v4.3, D-131): one folder, one id, one route per shot

Since the v4.3 rebuild (the creator, 2026-11-12; plan `PLAN_v4_3_IMPLEMENTATION.md` P1) an episode lives in ONE folder
`episodes/<episode_id>/`: `episode.json` (schema `episode_manifest`), `story/production_script.json` (schema
`production_script`, `schema_version` 4.0.0), its planning, assets, QA and edit. Code: `explainer_engine/episode/`
(`context.py` the folder and its era isolation, `validate.py` EP rules, `router.py` RT rules). Dialogue inside scenes is
SC-01 of [STORY_ENGINE](STORY_ENGINE.md); picture making through the Gemini chat is GC-01.. of
`docs/GEMINI_CONSISTENCY_RULES.md` (P3).

| ID | Rule | Checked by | Severity |
|---|---|---|---|
| EP-01 | **One id per episode.** The folder is named by `episode.json`'s `episode_id`, and every JSON document in the folder that names an episode (`episode_id`, or `episode` as a plain string) names the same one (the Toba folder carried `ep_toba` and `ep_toba_74000bce_12min` side by side, plan F12). | `python -m explainer_engine.episode.validate episodes/<id>` | FAIL |
| EP-02 | **One look per episode.** `episode.json` names its `look_id`, its map system `map_style`, the intake floor `image_native_min_long_side` (the chat tool's 1376) and the working master `image_min_long_side` (2752 after the free 2x upscale, never under 2048, plan 0.7). The look's two sentences (`look.style_sentence`, `look.face_sentence`) are set in the reference round with the creator; until then picture export refuses to start. | `episode_manifest.schema.json`; `imagegen/turn_pack` (P3) | FAIL |
| RT-01 | **Every shot has one route and a written reason**: `map_action` (Python map with an action layer, P4), `still_25d` (a picture moved by the layered 2.5D renderer with motion imitation, P5) or `wan` (Wan on Modal, P6). The router is deterministic; a hand-picked route sets `route_locked` and must carry its own `route_reason`. | `episode/router.route_script`; schema | FAIL |
| RT-02 | **Wan only where a body performs** what a still cannot fake (running, fighting, throwing, handling an object, a fall), and for the speaker's performance shot of a played scene (a Wan clip, no lip-sync, no talking still; Q4, Q7). Camera moves, weather, fire, water, crowds at a distance, establishing shots and objects at rest are `still_25d`. | `episode/router.route_shot` | — (the router decides) |
| RT-03 | **Geography and numbers are `map_action`**: map shots, spread, routes and counters are drawn by Python over a letter-free plate, each action tied to a spoken word (`actions[].at_word`, Q6). `actions` appear only on `map_action` shots and `motion_imitation` only on `still_25d` shots. | schema (`ShotSpec.allOf`) | FAIL |
| RT-04 | **The visual mix is measured by duration, never by shot counts** (R-C): `router.mix_report` sums the seconds per route from the timed spine (`basis: measured`) or, before the read exists, from `target_duration_seconds` (`basis: estimated`). The creator's target 10/30/60 (map/still/wan) is a guide, not a quota; the script decides. | `episode/router.mix_report` | REVIEW |
| RT-05 | **No unapproved engine in a shot**: `video_engine_tier` keeps only archive labels that name a route we run; the Gemini video engines (`GEMINI_LIGHT_VIDEO_I2V`, `GEMINI_VIDEO_API_BATCH`) were never approved and are refused. | schema | FAIL |
