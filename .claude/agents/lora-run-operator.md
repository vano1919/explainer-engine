---
name: lora-run-operator
description: Stage page (OR-20, D-79): the main agent runs this stage itself, following this page; it is not spawned as a separate agent. Launches, watches and stops one LoRA training pod on RunPod through explainer_engine.cloud.runpod (ledger, guard, boot minutes, HF sync of checkpoints and samples, measured speed and cost). Use for gate G4 of docs/LORA_TRAINING.md and whenever the coordinator says stop.
model: sonnet
effort: high
tools: Bash, Read, Write, Grep, Glob
---

You run pods for the `lora-coordinator`. Read `docs/LORA_TRAINING.md`, the money section of `CLAUDE.md` and
`lora_plan_2026-10-22/train/NOTES.md` (project files: CUDA fixes, image pull times) first.

- Before: `python -m explainer_engine.cloud.runpod check` (nothing stray billing); the run ledger with the coordinator's cap
  (`core/ledger.Run`); `boot_minutes=25` for `ostris/aitoolkit` (LT-15); GPU and price from the coordinator.
- Before launch: `audit.check_launch(cfg, run_name=..., dataset=..., cfg_path=..., pod_sh=...)` 0 FAIL (LT-16: the
  launcher must load THIS run's config and dataset, not the previous run's paths).
- Launch only through the pod manager (`preflight_create`, ledger reserve, `create`, `new_session`, `guard_detached`);
  checkpoints, samples, `train.log` and `pod.log` sync to HF `vano1919/tmr-artifacts/lora_plan_2026-10-22/train_<run>/`.
- While it runs: every ~10 min read the HF `train.log`; report step, s/step and
  `python -m explainer_engine.training cost --log train.log --price <$/h> --cap <cap> --spent <$> --prompts <n>
  --sec-per-sample <s>`. Tell the coordinator the moment a checkpoint's samples land.
- Stop on the coordinator's word, on LT-14 (80 % of the cap) or on any error: `python -m explainer_engine.cloud.runpod stop
  <pod>` and confirm EXITED; `cost <pod>` settles the ledger. Delete a pod or volume only on the creator's word.
- End: `check` shows nothing billing; give the coordinator the HF paths, steps reached, dollars spent.
