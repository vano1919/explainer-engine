# Handoff: route-test script, old vs new (2026-11-06)

**Done.** One story (23 shots, 100.5 s: tent dialogue, battle at the ford, duel, march in rain, aftermath; H1 commander, H2 scout, H3 elder; A1-A4) written twice on base `icw/05c-ink-round` (a3f1e1f). Text and JSON only. No pod, no paid call, no rule or schema change, nothing committed to a repo.

**Files (this folder).**
- `old_film_shots.json` (film_shots/2, script_engine/1), `old_prompts.json` (from `film_shots compose`), `old_check.txt` (0 FAIL, 27 REVIEW).
- `new_route_shots.json` (draft format `route_shots/draft0`): scene_assets per scene (360 backdrop prompts, hero sheets x4 angles with the flat-lighting note, edit template), per-shot route J5 / J2 / J4 / H with assembly, layout and prompts, and a lint block (0 FAIL, 1 REVIEW: KP-48 in the duel).
- `side_by_side.html` (the page), `SUMMARY_ka.md`, `stats.json`, `builders/` (story.py, build_old.py, build_new.py, build_page.py; rerun `python build_old.py OUT`, `build_new.py OUT`, `build_page.py`; paths inside point to this folder and the repo at /home/user/explainer-engine).

**Result.** LTX clips 18 -> 10 (82.5 s -> 46.2 s); Qwen images 25 -> 26; J5 54 s, J2 24 s, J4 20 s, H 3 s. The old composer writes an empty field for crowd shots (S02-02, S04-01) and carries `lora: null`.

**Open for the next step (not decided here).** C1 first frame = peak (old) vs start pose (layout-to-render); C2 40-word limit in code vs 90 in the pod brief; C3 360-LoRA trigger phrase missing; C4 MCU preset missing in camera_setups.json; C5 KP-48 in the duel; C6 helper share 3 %.

**Entry for the next thread.** Use `new_route_shots.json` `scene_assets` + `hero_sheets` as the prompt source for the asset pod's A/B groups; J2/J4 `qwen_frame` and `qwen_first_frame` prompts are ready for the step-3 test pod after the Fable OR-34 audit. Do not hand-edit the prompts: change `builders/` and rebuild.

**Update 2026-11-06 11:15 UTC (the creator's cards C1-C6, Fable thread).** C1 by route (J2/J4 first frame = start pose, J5/i2v = peak); C2 tested in the asset pod (group D2, 90 words); C3 closed (trigger in the pod config); C4 -> Opus step 2 (`mcu_front`); C5+C6 both: S03-03 is a J5 insert, S04-01b map helper added (4 s). Rebuilt: 24 shots, 104.5 s; LTX 18 -> 9 clips (43.2 s); old 0 FAIL / 28 REVIEW (base a3f1e1f), new 0 FAIL / 0 REVIEW. The page and JSONs are regenerated from `builders/`.
