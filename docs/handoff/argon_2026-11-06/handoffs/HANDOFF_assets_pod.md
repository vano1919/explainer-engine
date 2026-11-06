# Route-test Qwen assets: handoff (2026-11-06, 12:25 UTC)

What ran: one pod, RTX PRO 6000 Blackwell Workstation COMMUNITY ($1.69/h), id 0t2re35vf6f3sq, 11:35-12:15 UTC (40 min). Qwen-Image-2.1 + xworld_v2 ck3000 (sha f5c420a1...), weight 0.7, 30 steps, true_cfg 4.0 (edit/reference 2.5), seed 11 (C pairs 11/23). Job commit d68d3e8 on branch claude/project-thread-4i756j (PR #140, draft); job files sha-pinned in route_assets.sh.
Money: balance before $10.17, after $9.09 (spent about $1.08, RunPod billing rows lag; `runpod cost` showed $0 so far). Pod EXITED (self-stop), then `runpod stop` confirmed; nothing running; no deletion. Ledger jobs/route_test_2026-11/assets_ledger.json cap 3.5 (creator 11:28 UTC).
Outputs: HF vano1919/tmr-artifacts route_test_2026-11/assets/{A,B,C,D,D2,E,P,rejected}, manifest.jsonl, identity.json; cards page index.html here (images in full/, thumbs/), verdicts.json.
Counts: D 6 + D2 6 + redraws 2 + A 4 + B 12 + C 8 + P 2 + E 2 = 42 shown (2 moved to rejected/: B_H2_left34, E_D2_duel_90).
Question C: environment change did not break the hero. CLIP cosine vs B_H1_front: tent .81/.79, courtyard .81/.82, field .82/.78, ship .70/.74; own angles .93-.98; other heroes .62-.66. Weakest: ship.
40 vs 90 words: both hold the look; 90 adds every named prop; costs: clone crowds in D2_duel_90 (not fixed by edit).
Pano test (nomadoor outpaint LoRA, licence qwen-research): 2 images, seam scores 1.76/1.66; horizon continues, see P/.
Not done / open: no keyframe-gate VLM (72B does not fit 48 GB): verdicts are my reading; no pixel-diff report; PR #140 not merged; the guard process died once at 11:41 (restarted 12:11), pod-side dead-man and watchdog covered it.
