# OR-34 audit of the pilot pod package p15 (Fable, 2026-11-06 16:30 UTC)

**Branch** icw/19-pilot-pod @ a6cc403 (draft PR #149; stills code PR #148). **Verdict: PASS**, launch allowed on the
creator's word of 16:05 UTC ("გაუშვი ... საბოლოოდ რო გავიგოთ ქვენ თუ შეძლებს ... და ლტხ ვიდეოს აწყობას").

## Checked here (not from the handoff)
- `cloud.schedule check p15_schedule.json` rc 0: 4 combinations, 2 fit; cheapest A100 80GB $1.21 expected (0.87 h), $2.83 worst
  (2.04 h), idle GPU 0 min in both cases. GPU order qwen_restyle > ltx_room > ltx_battle > F.
- Wait chain (p15_pod.py): net lane = weights_qwen then weights_ltx25; gpu lane waits only weights_qwen, draws the 8 Qwen edits while
  the LTX weights download, then waits weights_ltx25 and runs the two clips, each its own process with the schedule max as timeout
  (qwen 1050 s, each clip 1050 s, F 60 s); a missing first frame or 2 LTX failures skips with the reason recorded. No stage waits on
  anything it does not need. No Blender on the pod.
- Bundle: `build bundle --ref a6cc403` and `--ref 1b46d93` both reproduce sha256 0ac0125c37529146a25a89082c2b94ecfac3a8989d0b090599b16bc96ed3bc37, the pin in p15.sh.
- p15.sh: heartbeat line, stall-minutes 30, needs line, DRY gate before any work, sha pin checked before unpack, exit 3 on mismatch;
  `lint_pod_script` = no findings; `cloud.dryrun` rc 0. Pinned installs (diffusers/peft commits, VideoX-Fun e8c314f, LTX-2 e98f6d9).
- Inputs pinned: 8 stills by sha256 in p15.json (the same shas as HF pilot_stills.json after the fix round), 3 hero fronts by sha256,
  xworld_v2 ck3000 sha f5c420a1… w0.7, LTX-2.5 files by sha256 at revision 49b093a.
- LTX jobs: ltx_i2v/1, distilled, 185 frames (7.71 s ≤ BP-172 8 s), 24 fps, 1920x1088, seed 42, no LoRA, no control video; first
  frame = the Qwen restyle written at 1920x1088.
- Tests: tests/unit/test_p15_pilot_pod.py + schedule + runpod + stop paths: 115 passed here.
- Stills reviewed (room_contact_sheet_v2.jpg): seated poses, wooden chairs, mantel clock, no modern props; battle frame 0 from behind
  the front rank. Good enough as first frames; no fill render needed before the pod.

## Notes (not blockers)
- LTX times are unmeasured (scaled from the 193-frame estimate); the schedule's 3x max covers it. F writes speeds.json for job_speeds.
- The battle i2v clip duplicates X7 asked of fix-2: fix-2 drops X7.
- The LTX style sentence says "bright colours" while xworld is "muted earthy colours with vivid glowing accents"; kept as in pod 1's
  X1 so the two runs compare; revisit after the pilot.
- Caps: --max-usd 3.5 --max-hours 2.5 ≤ per_pod_usd 10 (temporary) and ≤ balance $7.99 − $1 reserve.

## Launch (worker thread, not this thread)
1. `python -m explainer_engine.training.pods.p15.build bundle --ref a6cc403 --out ee_src.tar.gz`; sha256 must be 0ac0125c…; upload to
   HF `code/p15/ee_src.tar.gz`.
2. `python -m explainer_engine.cloud.runpod check`, then
   `runpod create --script explainer_engine/training/pods/p15/p15.sh --schedule explainer_engine/training/pods/p15/p15_schedule.json --gpu "A100 80GB" --max-usd 3.5 --max-hours 2.5 --ledger <ledger>` (H100 NVL only if no A100 places; then expected $1.6 / worst $4.2 — still under the caps).
3. Guard + watchdog; relay every qwen/*.png and ltx/*.mp4 to the Fable thread with its HF link as it lands; `check` and `cost` at the end;
   the pod ends STOPPED, never deleted.

# v4 re-audit (Fable, 2026-11-06 17:00 UTC): PASS, awaits the creator's word (scope and money changed)
- icw/19-pilot-pod @ 5385df5; bundle 2713bb69485e4b8db0a5970645c02e18df79c785c5f914d76951a31db001e3d1 reproduced here and pinned in p15.sh.
- RP-11 rc 0 (sampled 8006 of 40002 orders; 4003 fit): H100 NVL COMMUNITY $2.59/h, $3.25 expected (1.25 h), $6.37 worst (2.46 h),
  0 idle GPU. A100 SECURE $1.79/h worst $6.68 does not fit the $6.5 cap. Balance $7.99 − $1 reserve = $6.99 ≥ $6.37.
- 8 clips c1-c8 (order c1 c2 c3 c4 c6 c7 c8 c5), 185 f, seed 42, distilled i2v, native audio; each clip timeout 720 s (2× the 5.8-min
  estimate); 2 LTX failures stop the clips (worst waste if 12 min is too short: ~qwen + 24 min ≈ $1.6). Qwen 1050 s.
- dryrun rc 0; p15 + schedule tests 24 passed here; Opus: full suite 3089.
- keep_stopped_pods ygg2ztmflr8pv2: the worker adds it where the creator's 16:30 UTC word is recorded (not a blocker for this pod).

# Qwen-only audit (Fable, 2026-11-06 18:00 UTC): PASS, launch on the creator's word (17:34 UTC "only the pictures first", 17:55 UTC)
- icw/19-pilot-pod @ e29bfa7 (Qwen-only mode 5b00123); p15q.sh pins bundle b86552edbce05f34bd9cb1a815ab6de4944a08c44ab404449728f6fa75ba4979, reproduced here from `build bundle --ref b50b935`.
- p15_pod --only qwen: net lane weights_qwen only, gpu lane qwen_restyle then F, return; no LTX clone, weights or clip. Diff read.
- RP-11 p15q_schedule.json rc 0: A100 80GB expected $0.98 (0.55 h), worst $1.90 (1.06 h), 0 idle; caps max_usd 2.0 / 1.5 h.
- dryrun rc 0; p15 + schedule + d9 tests 35 passed; keep_stopped_pods has ygg2ztmflr8pv2 (58). runpod check: $0.000/h, balance $7.99.
- Launch: --script p15q.sh --schedule p15q_schedule.json --gpu "A100 80GB" --max-usd 2.0 --max-hours 1.5; pod ends STOPPED.

# 24-picture Qwen-only re-audit (Fable, 2026-11-06 18:05 UTC): PASS, launch waits for the creator's $3.4 card
- icw/19-pilot-pod @ ab533fe; bundle e21464369d050f0149788fb64937cf603c490a5c3578b92b250205e27ca610f5 reproduced from --ref ab533fe, pinned in p15q.sh.
- 8 stills x S1/S2/S3 picture-only clauses, all <= 90 words, seed + LoRA w0.7 unchanged. RP-11 rc 0 at $3.4 / 2 h, 3x maxes:
  A100 COMMUNITY $1.13 exp / $2.59 worst; SECURE $1.46 / $3.33. RP-01 passes on A100 only (work 26 min); no H100.
- dryrun rc 0; 36 tests passed here. Upload ee_src.tar.gz + p15q.sh from ab533fe; ledger recreated at 3.4.
