# HANDOFF P1 (paused by the creator, 2026-11-06 ~16:55 UTC)

**State: PAUSED. The creator postponed this package until everything else is finished (his words in the Fable thread, 16:54 UTC: "let's cancel until everything is finished"; he also asked that Opus is used only where expensive and Sonnet after the plan). Nothing paid was launched. No pod exists for P1. Cost $0. `cloud.runpod check` at 16:3x UTC: nothing bills, balance $7.99.**

## Done (free)
- Two new static battle cameras (`explainer_engine/blender/layout_passes.py` `BATTLE_CAMERAS`: `wide_high`, `front_mid`; `crowd.scene(camera_override=)`), rendered in the cloud container (Blender 5.2.3, 5,000 soldiers, 1920x1088, frame 112). On HF, sha256-verified:
  `route_test_2026-11/pilot/blender/battle_wide_high_f112_colour.png`, `.../battle_front_mid_f112_colour.png`, `.../pilot_stills_p16.json`
  (https://huggingface.co/datasets/vano1919/tmr-artifacts/tree/main/route_test_2026-11/pilot/blender). The pinned `pilot_stills.json` was not touched (the p15 pod reads it).
- Contact sheet of all 11 stills: `pilot_1min/stills/p1_contact_sheet_11.jpg` (project files).
- Three new soldiers cards (`pilot_stills.BATTLE_CARDS`: frame 200, wide high, front mid); Qwen and LTX prompts are generated from the cards and pass `qa/style_prompt.check`.
- Pod package `explainer_engine/training/pods/p16/` (`build.py`, `p16_pod.py`, `p16_qwen.py`, `p16_ltx.py`, `p16.sh`, `p16.json`, `p16_schedule.json`): 3 Qwen restyles (battle frame 200, wide high, front mid) + 8 LTX clips (room establishing/close host/close guest/reverse 145 f, insert table 97 f, battle wide high 145 f, front mid 145 f, frame 200 121 f = 1,088 frames). The two clips p15 makes (room two-shot, battle frame 0, 185 f each) and the room restyles are REUSED from p15's HF output, not re-paid. Order (RP-11): room clips first (they need no restyle), then the restyle, then the battle clips.
- `production/pilot_minute.py`: cuts the ten clips + the clock insert (J5-style push-in) into one 2560x1440 video of ~63 s and writes `compare.html` (Blender still | Qwen restyle | clip).
- Tests: `test_pilot_stills.py` (+3), `test_p16_pod.py` (11), `test_pilot_minute.py` (5); full `tests/unit` 3090 passed, docs_lint 0 findings. PROGRESS.md entry written.
- Branch `claude/project-thread-9hpm56` (on `icw/19-pilot-pod`), draft PR.

## Not done / needs before any pod
1. The p15 pod (Fable thread) must run first: its `ltx/*.json` sidecars give the real LTX seconds per frame, and its `first_frames/*.png` + `qwen/manifest.jsonl` give the sha256 pins for the five room clips. Then rerun
   `python -m explainer_engine.training.pods.p16.build config --extra pilot_stills_p16.json --stills pilot_stills.json --p15-out <p15 out> --ltx-s-per-frame <X> --on "A100 80GB"`.
   With the current unmeasured estimate RP-11 REFUSES (worst case $4.98 / 3.6 h over the $5 / 3 h caps); with a measured speed of 1.6-2.5 s/frame on the A100 it passes ($1.3-1.7 expected, $2.1-2.6 worst, 0 idle GPU).
2. Look at p15's Qwen room restyles first: if identity or props drift across the angles, the room clips are not worth paying for and the list shrinks.
3. Then: OR-23 plan, OR-34 audit (coordinator's rule: an Opus 5.5 subagent; the Fable thread said it is live, unverified), the creator's "კი", `bundle` + upload `code/p16/ee_src.tar.gz`, Haiku watchdog via the coordinator, `runpod create --schedule p16_schedule.json` (A100 80GB, caps max-usd 5 / max-hours 3), stop (never delete).
4. After the pod: `python -m explainer_engine.production.pilot_minute --p15 <out> --p16 <out> --blender <stills dir> --out <dir>`; upload to HF `route_test_2026-11/pilot/` and give the exact paths.

## Open points
- Motion lines: the cards are the Opus rules thread's (host/guest talk, elder feeds the stove, candle flickers), not the EXEC_QUEUE table's proposals (elder walks to the table, a hand sets the jug): those objects are not in those stills (in_shot rule, creator 15:53).
- Wide high / front mid frame 112 is just before contact; the crowd baked animation has no real collision (the wedge passes through the wall after ~frame 130): LTX must invent the clash.
- Local-only leftovers (container, will vanish): Blender install, `/tmp/claude-0/bat` renders.
