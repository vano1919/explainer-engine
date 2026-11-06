# OR-34 audit of step-3 pod package fix 2 (Fable, 2026-11-06 16:40 UTC)

**Branch** icw/16-lean-pod @ 8f64392 (PR #146). **Verdict: PASS technically; launch waits for the creator's word** (the pilot pod
p15 is running first; his 16:05 word covered the pilot only).

## Checked here
- `cloud.schedule check p14_schedule.json` rc 0: 4712 combinations, all fit; cheapest A100 80GB $1.27 expected (0.91 h), $2.62 worst
  (1.88 h), 0 idle GPU minutes; H100 $1.81 / $3.50. GPU order qwen1 > X6.ltx > D > B.duel > E.duel > F; Blender stays on the CPU
  (A.preflight, A.frame0.duel, A.duel), and the duel layouts come from pod 1's HF files sha-checked (no render unless they changed).
- Graph: 12 stages; every stage waits only on its own inputs (E.duel on weights + B.duel + A.duel; X6.ltx on weights + qwen1; B.duel on
  weights_qwen + A.frame0.duel). No battle, no G, no X3/X4, no X7 on this pod.
- Bundle sha256 1a8e5587cc717c982d89b51578ed614f616d651336930baf2975246e7ae131c1 reproduced from `lean bundle --ref 8f64392` and
  pinned in p14.sh. dryrun rc 0, lint_pod_script no findings. Tests: test_p14_lean, test_p14_pod, test_cloud_schedule, test_d9_config
  = 62 passed here (Opus: full suite 3071).

## What this pod answers (distinct from the pilot)
- E.duel: Blender clay motion → Qwen first frame → LTX-2.5 Layout-To-Render (J2) on the duel, against the pilot's plain i2v: does
  Blender motion control pay for itself (the creator's 15:19 balance question)?
- X6: the travel still with a free camera move (FFmpeg) vs LTX i2v of the same still (STILL_3D route).
- D: BiRefNet cutouts of the 12 asset pictures (J5 inputs), fixed dtype.
- qwen1: C ×2 at 150 words (already drawn on pod 1; re-drawn here only because the restyle manifest is per pod; EST 1.3 min, ~$0.03).

## Caps for the launch block (mine to set, per Opus)
- `--gpu "A100 80GB" --max-usd 3.5 --max-hours 2.5` (worst $2.62 / 1.88 h fits); H100 only if no A100 places.
- per_pod_usd 10 still in force (creator's card 14:10); balance after the pilot's worst case ≥ $5.1.

## Open for the creator (card in the Fable thread)
When to run it: after the pilot's verdict (recommended) / now in parallel / only E.duel + D / not at all.
