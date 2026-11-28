# Wave 6 — Plan-vs-Actual Compliance Audit & Drift Correction

- **Plan Reference:** `docs/audit/MASTER_MIGRATION_PLAN_FINAL.md` (AC-01 .. AC-18)
- **Audit Date:** 2026-11-25
- **Branch:** `feat/explainer-engine-nextgen-framework-2026-11-24`

## Acceptance Criteria Compliance Matrix

| Criterion | Target Files | Plan vs. Actual Status | Concrete Evidence |
|---|---|---|---|
| **AC-01** | `core/execution_gateway.py`, `orchestration/skill_orchestrator.py` | **ALIGNED** | `record_stage_completion` enforces on-disk `output_paths` strictly for `PASS`, permits `REVIEW`/`FAIL`/`NOT_RUN` halts without crashing `skill_orchestrator`, normalizes `output_hashes` keys to `.as_posix()`. `test_skill_orchestrator_strict_contracts_and_halt_on_non_pass` passes. |
| **AC-02** | `schemas/episode_manifest.schema.json` | **ALIGNED** | Optional `fps`, `render_size`, `enable_post_assembly_spotting`, `character_references` added while keeping `"additionalProperties": false`. `episodes/ep_toba/episode.json` validates cleanly. |
| **AC-03** | `core/approvals.py`, `core/execution_gateway.py`, `modal_ltx_jobs.py`, `modal_layout_jobs.py` | **ALIGNED** | Persistent SQLite WAL consumed-operation replay ledger (`record_consumed_operation`, `is_operation_consumed`) + constant-time `verify_approval_hmac`; `authorize_paid_action` and both Modal `verify_worker_approval` entrypoints emit unique `operation_id` and sign `approval_hmac` when `EE_APPROVAL_HMAC_KEY` is set. |
| **AC-04** | `modal_ltx_jobs.py`, `modal_layout_jobs.py` | **ALIGNED** | Guarded `Path(__file__).resolve().parents` against `IndexError` in shallow Modal `/root` containers; wired `operation_id` + `sign_approval_proof` into worker approval handshake. |
| **AC-05** | `core/spend_ledger.py`, `core/store.py`, `episode/run.py` | **ALIGNED** | `PRAGMA busy_timeout=15000` moved before `PRAGMA journal_mode=WAL`; `write_text_atomic` uses PID+thread-unique `.tmp` files; `episode/run.py` uses Windows-safe `replace_file()`. |
| **AC-06** | `governance/gateway_hook.py`, `.claude/settings.json` | **ALIGNED (Reconciled)** | Added `pre-write` handler blocking `Write`/`Edit` to `config/owner_approvals.json`, Windows `.exe`/`.cmd`/`.bat` normalization, PowerShell bypass verbs, and `.claude/settings.json` `permissions.deny`. Kept `config/spend_caps.json` under `governance/hooks.py` Lock 2 (owner-recorded approval) to prevent conflicting with Lock 2 tests. |
| **AC-07** | `maps/draw.py`, `tests/unit/test_v43_map_actions.py` | **ALIGNED** | Removed all silent fallbacks to `ComicNeue-Bold.ttf`, `Bangers-Regular.ttf`, `Inter.ttf`, and `ImageFont.load_default()`. Default `Canvas.face = "map"` and `font(px, face="map")` strictly require verified `LiberationSerif-Regular.ttf`. Migrated stale `Inter`/`Comic` assertions in `test_v43_map_actions.py`. |
| **AC-08** | `overlay/bridge_compiler.py` | **ALIGNED** | Verified strict `LiberationSerif-Regular.ttf` SHA-256 verification and FFmpeg overlay composition in `stage_assemble`. |
| **AC-09** | `videolane/ltx_loop.py`, `videolane/adapters.py` | **ALIGNED** | Aligned `UPSCALER_BACKENDS` with honest local adapter names (`local_lanczos_unsharp_still`, `ffmpeg_2k_lanczos_cas`) alongside optional external backends, preserving strict `StillUpscalerAdapter` vs `VideoUpscalerAdapter` separation. |
| **AC-10** | `audio/post_assembly_spotting.py` | **ALIGNED** | Added `preview_video` freshness verification (`is_spotting_fresh`) before sound-plan integration and audio mixing; added `require_stereo_48k` validation and stereo-channel-preserving SFX mixing (`_read_pcm16_frames`). |
| **AC-11** | `qa/identity_lock.py`, `episode/run.py` | **ALIGNED** | Added direct self-comparison guard (`ref_p.resolve() == cand_p.resolve() or ref_sha == cand_sha` -> `FAIL`, `self_comparison_forbidden`) inside `check_cross_scene_identity`; removed blind `records[0]` fallback in `episode/run.py:stage_qa`. |
| **AC-12** | `qa/perceptual_qa.py` | **ALIGNED** | Added explicit `analysis_mode="single_shot"` (strict `TG.check_no_melt`, zero threshold weakening) vs `analysis_mode="multi_scene"` (cut-aware intra-scene melt check), plus deterministic YouTube editorial checks (`ebur128` integrated LUFS `-14.0` target, true peak `<= -1.0 dBTP`, stereo balance `<= 6.0 dB`, first-30s hook visual change count). |
| **AC-13** | `episode/av_report.py` | **ALIGNED** | Guarded `e["frames"] is None` in `markdown()` with `'n/a'`. |
| **AC-14** | `.github/workflows/orchestrator-drive-bridge.yml`, `.github/workflows/quality.yml` | **ALIGNED** | Fixed `--out` -> `--out-dir` in `orchestrator-drive-bridge.yml`; added `pytest-timeout` and expanded Ruff lint coverage in `quality.yml`. |
| **AC-15** | `docs/implementation/CLAUDE_OPUS_PRODUCTION_HANDOFF.md`, `docs/research/WAVE_NEXT_TECHNOLOGY_COMPARISON.md` | **ALIGNED** | Corrected active-stack descriptions (`pil_ffmpeg_overlay`, `maps/render.py`, `production/layers25d.py`, `deterministic_portrait_hist_fallback`) and added missing `--library` flag to CLI snippet. |
| **AC-16** | `tests/unit/test_wave10_audit_hardening.py`, `tests/unit/test_v43_map_actions.py` | **ALIGNED** | Added 8 comprehensive contract, integration, and adversarial tests covering AC-01..AC-15; zero weakened assertions. |
| **AC-17** | Wave 9 real local renders | **IN PROGRESS (Next Wave)** | Scheduled immediately in Wave 9. |
| **AC-18** | Wave 10 quality gates & bundle export | **IN PROGRESS (Final Wave)** | Scheduled immediately in Wave 10. |
