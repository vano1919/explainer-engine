# OR-34 audit of the lean step-3 pod package (Fable, 2026-11-06 14:10 UTC)

Branch icw/16-lean-pod @ 53e260a (PR #146, draft). Verdict: **PASS**, launch may proceed after the creator's word on the spend cap.

Checked
- The ten job files' sha256 match the handoff table (recomputed here).
- The code bundle rebuilt here with `lean bundle --ref 53e260a` gives 7fc135cd…, the sha pinned in p14.sh (byte-stable).
- p14.sh: pinned installs (VideoX-Fun e8c314fb, LTX-2 e98f6d9, diffusers d8c1b13c, peft ebf159f7), heartbeat + stall-minutes + CR-18 needs line, DRY exit, bundle sha check before unpack, Blender install + CPU resolve, then p14_pod.
- Weights: LTX-2.5 (4 files + upsampler + Layout LoRA), LTX-2.3 distilled 1.1 + upsampler + Union-Control ref0.5 + Gemma 3 (7 files), xworld_v2 ck3000 sha f5c420a1, BiRefNet pinned: all shas as verified against the Hub earlier today (#144 audit).
- Stage order and lanes as the plan: net / cpu (A, X6.move, G) / gpu (B, C, X6.still, D, E 5 jobs, X1, X2, X5, X3, X6.ltx, X4, F); each stage its own process; stages.json records; two LTX failures in a row stop E; upscale.enabled false.
- Prompts: B 76 and 88 words ("draw him once"), C 146 and 142 words (inside the 40-150 band, no camera/size words), X6 still 45, X4 fix 47; X3 is an LTX prompt (not a Qwen prompt) with the dialogue line.
- Geometry: 145/121 frames (8k+1), 1920x1088; X5 2560x1472 (nearest /64 size covering 2K, cut to 1440 later).
- Tests 46 focused here (Opus: 3043 full), offline dryrun rc 0, docs_lint 0, governance ok.

Opus's 8 decisions: accepted as written (B pictures double as first frames; H1/H2 sheets as references; X3/X4 frames from G; X5 size; zoompan 1.0→1.08; G limits 1.75 m, no props/mouths/moves; H shot off the pod; model_cpu_offload).

Open before `runpod create`
1. config/spend_caps.json per_pod_usd 6.9 < max-usd 10: the creator's word (card in the Fable thread), then `governance ok` + the edit on the launch branch.
2. HF upload of code/p14/ee_src.tar.gz (the worker, from the audited commit; sha must stay 7fc135cd…).
3. watchdog.yml dispatch within 60 min before create; Haiku watchdog thread; runpod guard with beat.
Known: G's 996 frames at ~8 s/frame on 4 vCPU ≈ 2.2 h, unmeasured scaling on more cores; G stops at the reserve, so the pilot may be short of some J5 shots (then slates).
