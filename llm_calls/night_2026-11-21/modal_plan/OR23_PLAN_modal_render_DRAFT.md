# OR-23 plan item, Modal test render (DRAFT, not started)

Status: NOT APPROVED. Paid. Needs the owner's yes before any run (the workload was set by the coordinator, not by the owner).

- Purpose: test renders of existing engine samples (no new AI video model) to check technical gates.
- Workload (coordinator's proposal, 21:56 UTC): (a) map presets bold/balanced/light, 8–10 s each; (b) bridge styles card/outline/lower_third, 5–8 s each; (c) 2.5D no-melt sample, 2 variants, about 10 s; (d) audio for the same clips, for the technical gate.
- Provider and GPU: Modal, cheapest from workload_d_short_calibration (H100 about $0.36 per short run; A100-80GB about $0.45). Not verified for a render of this length: the estimate is for calibration runs, not for 10 s of video.
- Cap: $8 of the owner's $10 Modal line (80 %). Stop at $8 or after 3 failed runs.
- Outputs: mp4 and technical gate result per clip, saved as each one finishes; path on branch claude/project-thread-3j9l41-techgate or Modal volume.
- Missing before any paid run: paid_offer/1 file (free-credit check, two priced options, VRAM measured or known, watchdog), a check that the render code exists in the repo for these clips, and the card reference for a paid call (the owner's yes). The coordinator's "no card needed" is not a rule I can accept for paid runs.
- Free check done: dry-run ranks (H100 $0.36, A100 $0.45) only.
