# D-120 / D-121 reconciliation audit

Date: 2026-11-08
Scope: `claude/stoneage-test-scenes`, PR #158, the Stone Age Qwen builders, and the p15 Modal launchers.

## CURRENT

- PR #158's `stoneage_qwen_jobs.jobs()` sends Blender `flat3` stills as Qwen `in:` references.
- `asset_jobs()` generates alternate views by editing a generated place image and omits the required `in_shot` registry metadata.
- `scene_reuse.check_refs` already enforces RF-01, RF-04 and RF-05; `check_prompts` enforces HI-01, HI-04 and HI-08.
- `paid_preflight` is integrated in `modal_qwen_jobs_v15.py` and `modal_ltx_jobs_v1.py`, before the creator go-gate and before paid `.remote()` calls.
- Superseded Qwen launchers v1/v3/v5-v13 and `modal_sa_test.py` still exposed paid `smoke` / `main` entry points without D-121 checks.

## D-120 / D-121

- D-120 forbids Blender/3D renders as Qwen references. Scene staging must come from words; a place must not be redrawn in consecutive shots.
- D-121 requires every paid Modal launch to fail closed on the applicable free checks. Qwen jobs require the scene-reuse checks; LTX jobs require the shot-prompt checks. Cut plans must pass `production.cut_plan` before drawing or assembly.

## KEEP

- Keep Blender layout generation as a free, offline comparison artifact. It is not a Qwen input.
- Keep `scene_reuse`, `paid_preflight`, `cut_plan`, and their existing rule checks. Do not duplicate these contracts.
- Keep the current v15 Qwen and v1 LTX launchers as the supported paid entry points.

## CHANGE

- Mark the two Stone Age Qwen job builders as historical research-only; add regression tests proving their current output is rejected by paid preflight (RF-01, RF-05, HI-01).
- Retire superseded paid Modal entry points. Their `smoke` and `main` functions now stop before any `.remote()` call.
- Expand the preflight tests to assert the supported launchers run the checks before the creator go-gate and that historical launchers fail closed.

## REMOVE

- Do not delete the historical experiment code or its inputs. They remain useful evidence for why D-120 superseded the earlier Blender-reference approach.
- Do not remove the existing rule engines or replace them with parallel validators.

## TRADE-OFFS

- The older Modal launchers are no longer runnable. This is intentional: their job artifacts predate D-120/D-121 and cannot be safely assumed compliant.
- The Stone Age research builders remain in the repository, but their output is explicitly not eligible for paid execution.
- The new tests establish fail-closed behavior; they do not prove that a compliant text-first Stone Age job builder has been implemented.

## REMAINING WORK / ACCEPTANCE

1. Implement a new Qwen-first job builder from the approved cast registry and scene words. It must not pass Blender renders as references.
2. Give every generated job an explicit `in_shot` list and verbatim registry blocks. Any `out:` reference must carry a valid `variant_of` and be limited to an allowed same-drawing edit.
3. Run `python -m pytest tests/unit/test_scene_reuse_rules.py tests/unit/test_paid_preflight.py tests/unit/test_stoneage_test_layouts.py tests/unit/test_cut_plan.py tests/unit/test_rule_coverage.py -q`, then the full suite and CI.
4. Do not run paid Qwen/LTX jobs until those checks pass and the creator explicitly approves the spend.

This audit does not claim that the full pilot is ready or that tests have been executed in this session.
