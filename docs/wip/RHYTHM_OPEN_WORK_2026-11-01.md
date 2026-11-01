# Open work of the MrBeast-style rhythm (D-94), so nothing is forgotten (2026-11-01)

Done: WP-R1..R6 (part), R8, R11, R12 (see `docs/PROGRESS.md`, the entries of 2026-11-01).

## Deferred on purpose
1. **WP-R7**: rewire the old calm checks (`film_shots` KP-35, `variant_plan` dynamics, `board` RHYTHM-*, `motion_lint`, `shot_rules`)
   so a `production_script/4` script defers to `scripting/rhythm_lint.py`. Wait for the first /4 script; it shows which old check FAILs
   on a zoned script.
2. **WP-R9**: production modules (timing, beats, fill_holds, staging, compile, assemble, validate) read the zone of a segment.
3. **WP-R10**: audio layers, sound director, engagement/scorecard/targets read the zone (sound density, pauses, loudness range).
4. **Narration/story lints** (`narration_lint`, `story_lint`): hyped thresholds from the BP-169 zones, with the first /4 script.
5. **Narrator**: one voice whose tempo follows the zones. The creator's ear decides (VC-08): audition of three energetic voices,
   about 1,050 credits, only with his word. `casting`, `voice_check`, `pause_pad`, `channel_voices.json` change after that.
6. **BP-169 as a house rule** (the creator confirms the profile); **the episode cost cap** (`config/spend_caps.json`, his edit).
7. **P12 pod** (paused): Argon audit round 2 -> fixes -> `p12b.sh` sha lines -> HF code upload -> DRY gate -> OR-23 plan with
   Opus confirmation and his word -> pod with the 5-minute watchdog. The pod measures LTX-2.5 clip time, the 73-frame clip and
   the layout LoRA; its numbers replace the guesses in `COST_AND_TIME_MODEL.md`.
8. **Simple savings** (the creator 15:25 UTC): reuse of an environment or a cut-out only where it works easily on a photo.
