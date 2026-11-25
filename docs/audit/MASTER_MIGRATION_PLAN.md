# Master Architecture, Claude Constraint & Migration Plan (Wave 3)

- **Target Branch:** `feat/explainer-engine-nextgen-framework-2026-11-24`
- **Baseline HEAD:** `0f2128b0ea21dbeae2bf8d53189dcece27dcdc2b`
- **Inputs:** `docs/audit/FULL_REPO_AUDIT_OVERVIEW.md`, `docs/audit/RESEARCH_CORPUS_200.json` (327 verified unique URLs across 5 pillars)
- **Invariant Locks:** Zero modifications to the 848 protected files (`.claude/skills/v-*`, `.claude/skills/_archive/**`, `CLAUDE.md`); zero creation of `AGENTS.md` or `.mcp.json`; `$0.00` unapproved spend; zero increase to any ceiling in `config/spend_caps.json`; zero AI attribution in code/commits.

## 1. File-by-File Change Manifest

### MODIFY (Targeted Surgical Production Upgrades)
1. `explainer_engine/core/approvals.py` — Add persistent replay-protected consumed-operation tracking (`record_consumed_operation`, `is_operation_consumed`) backed by SQLite WAL alongside existing `verify_approval` and HMAC helpers (`compute_approval_hmac`, `sign_approval_proof`, `verify_approval_hmac`).
2. `explainer_engine/core/execution_gateway.py` —
   - Fix `record_stage_completion`: separate `PASS` (requires verifiable on-disk `output_paths` with SHA-256 hashes) from `REVIEW`/`HALTED` (allows recording non-passing/review halt states without crashing `skill_orchestrator.py`), while keeping `PASSING_STATES` strict for downstream progression.
   - Normalize `output_hashes` keys to POSIX relative paths (`.as_posix()`) for Windows/Linux parity.
   - Wire `approvals.sign_approval_proof` into `authorize_paid_action` so every authorized paid action emits a unique `operation_id` and HMAC-SHA256 `approval_hmac` when `EE_APPROVAL_HMAC_KEY` is configured.
   - Write/update `jobs/active_production_state.json` pointer whenever `ProductionStateMachine` saves state (making the `.claude/settings.json` Stop hook genuinely active!).
3. `explainer_engine/core/spend_ledger.py` — Set `PRAGMA busy_timeout = 15000` BEFORE `PRAGMA journal_mode = WAL` to eliminate transient SQLite lock contention on concurrent reservations.
4. `explainer_engine/core/store.py` — Make `write_text_atomic` temporary filenames PID+thread-unique (`f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"`) to prevent concurrent write clobbering.
5. `explainer_engine/orchestration/skill_orchestrator.py` — Fix `run_plan` (`lines 544-554`) so non-PASS statuses (`VALIDATED`, `PLANNED`, `AUTHORIZED`) without on-disk artifacts do NOT crash `execution_gateway.record_stage_completion`; remove synthetic fake marker file fabrication on `PASS`; ensure `dependencies`/`depends_on` are handled consistently across both `select_plan` and `run_plan`.
6. `explainer_engine/schemas/episode_manifest.schema.json` — Add optional properties `fps`, `render_size`, `enable_post_assembly_spotting`, `character_references` while preserving `"additionalProperties": false` so `episode/run.py` and `episode/context.py` agree 100%.
7. `explainer_engine/episode/run.py` —
   - Use Windows-safe `core.store.replace_file` instead of raw `.replace()` at lines 943 and 985.
   - Fix identity lock candidate lookup so it never blindly falls back to `records[0]["source_start_keyframe"]` when `character_id` is absent from shot 0; enforce mandatory `FAIL` and self-comparison refusal.
   - Ensure `active_production_state.json` is updated on stage transitions.
   - Wire `validate_film_style_bible` cleanly when `planning/film_style_bible.json` exists.
8. `explainer_engine/episode/av_report.py` — Guard `e['frames'] is None` in `markdown()` (`line 109`) to prevent `TypeError` on derived transition risers.
9. `explainer_engine/governance/gateway_hook.py` —
   - Add `config/spend_caps.json` to `PROTECTED_GATEWAY_CONFIGS` (matching docstring).
   - Add `pre-write` handler blocking `Write`/`Edit` tool mutations to `config/owner_approvals.json` and `config/spend_caps.json`.
   - Normalize `.exe`/`.cmd`/`.bat` suffixes on Windows (`Path(tok).stem.lower()` / `.removesuffix(".exe")`) for `modal`, `git`, `python`, `curl`, `wget`.
   - Block PowerShell bypass verbs (`Invoke-WebRequest`, `iwr`, `irm`, `Set-Content`) targeting protected configs or paid endpoints.
10. `.claude/settings.json` — Add `permissions.deny` rules protecting `config/owner_approvals.json`, `config/spend_caps.json`, and destructive git/modal commands; wire `gateway_hook pre-write` into `PreToolUse` `Write|Edit`; keep cross-platform Python invocation clean.
11. `explainer_engine/training/pods/ltx/modal_ltx_jobs.py` & `modal_layout_jobs.py` —
    - Wire `approvals.sign_approval_proof` inside `verify_worker_approval` so every proof carries a unique `operation_id` and `approval_hmac` (when key set).
    - Pass `expected_manifest_sha256` and `estimated_max_usd` into `verify_remote_approval_payload` at remote worker entry points (`weights_stage`, `_remote_body` / `_remote`).
    - Guard `Path(__file__).resolve().parents` against `IndexError` inside shallow Modal `/root` containers.
    - Fix `modal_layout_jobs.py:night_settle` to mirror `night_reserve` guard.
12. `explainer_engine/maps/draw.py` — Remove silent fallbacks to `ComicNeue-Bold.ttf`, `Bangers-Regular.ttf`, `Inter.ttf`, and `ImageFont.load_default()`. Default `Canvas.face = "map"` and require verified `assets/fonts/LiberationSerif-Regular.ttf` (raising `FileNotFoundError`/`RuntimeError` loudly if missing).
13. `explainer_engine/overlay/bridge_compiler.py` — Add text-wrapping / overflow protection and mobile-legibility font-size floor check (`>= 36px` at 1080p / `>= 48px` at 1440p) while preserving strict `LiberationSerif-Regular.ttf` SHA-256 verification.
14. `explainer_engine/videolane/ltx_loop.py` & `videolane/adapters.py` — Deprecate/reject shared `upscaler_2k` for mixed media (enforce explicit `still_upscaler` vs `video_upscaler` separation) and align `UPSCALER_BACKENDS` with honest adapter names (`local_lanczos_unsharp_still`, `ffmpeg_2k_lanczos_cas`, plus optional external `realesrgan_x2`, `seedvr2_4n1`).
15. `explainer_engine/audio/post_assembly_spotting.py` —
    - Call `is_spotting_fresh` before merging/mixing (refuse stale spotting when assembled video SHA-256 changed).
    - Enforce 48 kHz, 2-channel stereo, 16-bit PCM on `base_wav` in `mix_spotted_cues_onto_audio` and preserve stereo channels when mixing SFX (never silently downmixing base mix or stereo SFX).
    - Keep explicit `require_human_approval` policy flag clearly surfaced in output JSON.
16. `explainer_engine/qa/identity_lock.py` —
    - Add strict self-comparison refusal: reject `ref_p.resolve() == cand_p.resolve()` OR `ref_sha == cand_sha` (raises/fails with `SELF_COMPARISON_FORBIDDEN`).
    - Keep honest backend labeling (`deterministic_portrait_hist_fallback` vs `opencv_yunet_sface` if ONNX models present).
17. `explainer_engine/qa/perceptual_qa.py` —
    - Separate single-shot (`analysis_mode="single_shot"`, runs `TG.check_no_melt` strictly without weakening thresholds) from multi-scene assembled masters (`analysis_mode="multi_scene"`, segments around hard scene cuts so intentional cuts do not trigger false-positive `SIG-VID-MELT` while intra-scene melt is still caught).
    - Add deterministic YouTube Editorial & Retention QA signals (`editorial_retention_checks`): integrated loudness (`ebur128` targeting `-14 LUFS`, true peak `<= -1.0 dBTP`), stereo balance gate (`<= 6.0 dB` L/R delta), first-30s hook visual change cadence, and mobile legibility metadata check.
18. `.github/workflows/orchestrator-drive-bridge.yml` & `.github/workflows/quality.yml` — Fix `--out` -> `--out-dir` in `orchestrator-drive-bridge.yml:108`; expand `quality.yml` Ruff lint list to cover all modified production modules and include `pytest-timeout`.
19. `docs/implementation/CLAUDE_OPUS_PRODUCTION_HANDOFF.md`, `WAVE_NEXT_BASELINE.md`, `WAVE_NEXT_EXECUTION_LEDGER.md`, `docs/research/WAVE_NEXT_TECHNOLOGY_COMPARISON.md` — Eliminate all doc-vs-code drift (honestly documenting `pil_ffmpeg_overlay`, `maps/render.py`, `production/layers25d.py`, `deterministic_portrait_hist_fallback`, and exact `--library` CLI flags).

## 2. Single Authoritative Production Pipeline Specification

| Stage | Input Contract | Output Contract | Dependencies | Artifact Location | Validation & Failure Behavior |
|---|---|---|---|---|---|
| `script` | `story/production_script.json`, `episode.json` | `stage_script.json` (`PASS`) | none | `production/stage_script.json` | Schema + `EP-01` + `rule_enforcer` + `docudrama_structure`; fail-closed on `FAIL` |
| `sound_plan` | `production_script.json` | `audio/sound_plan.json` | `script` | `audio/sound_plan.json` | Schema + era/library checks; SHA-256 pinned |
| `pictures` | `production_script.json`, `world_bible` | `images/*.png`, `stage_pictures.json` | `script` | `images/` | Dimensions, non-blank pixels, SHA-256 pinned |
| `voice` | `production_script.json`, voice takes | `audio/narration.wav`, `audio/timing.json` | `script` | `audio/timing.json` | Word alignment + 48 kHz PCM; SHA-256 pinned |
| `clips` | `images/*.png`, `audio/timing.json` | `clips/*.mp4`, `video_clip_record/1` | `pictures`, `voice` | `clips/` | Photo-first SHA-256 + 8n+1 handles + separate still/video upscalers |
| `sound` | `audio/sound_plan.json`, `audio/narration.wav` | `audio/mix.wav` (48 kHz stereo) | `sound_plan`, `voice`, `clips` | `audio/mix.wav` | 5-stem mix + `mix_check` (`-14 LUFS`, `-1 dBTP`, no dropouts) |
| `assemble` | `clips/*.mp4`, `audio/mix.wav`, `bridges` | `production/master.mp4`, `production/master.json` | `clips`, `sound` | `production/master.mp4` | FFmpeg assembly + `bridge_compiler` (verified LiberationSerif) + SHA-256 |
| `post_assembly_spotting` | `production/master.mp4`, `assets/audio/library/` | `audio/post_assembly_spotting.json`, `audio/mix_spotted.wav` | `assemble` | `audio/post_assembly_spotting.json` | Freshness check vs master SHA-256, `is_relative_to`, WAV SHA-256, `commercial_use=true`, 48 kHz stereo |
| `qa` | `production/master.mp4`, `character_references` | `qa/perceptual_qa_report.json`, `qa/identity_lock_report.json` | `assemble`, (`post_assembly_spotting` if enabled) | `qa/` | 3-layer QA (`multi_scene` vs `single_shot`), mandatory Identity Lock (no self-compare), YouTube retention/LUFS |
| `delivery` | `production/master.mp4`, `qa/*` (`PASS`) | `delivery/manifest.json` | `qa` | `delivery/manifest.json` | Requires `qa=PASS` and intact SHA-256 hashes |

## 3. Claude Code Constraint Architecture
- **Tool-level deny (`permissions.deny` in `.claude/settings.json`):** Deny direct edits/writes to `config/owner_approvals.json`, `config/spend_caps.json`, and destructive git commands (`git reset --hard`, `git push --force`).
- **PreToolUse Bash (`gateway_hook pre-bash`):** Fail-closed (exit 2) AST/shlex parser blocking wrapper/env/subshell/chaining/PowerShell/Windows-`.exe` bypasses against Modal, paid APIs, and protected configs.
- **PreToolUse Write|Edit (`gateway_hook pre-write`):** Fail-closed (exit 2) path-containment check blocking writes to `config/owner_approvals.json` and `config/spend_caps.json`.
- **PostToolUse Bash (`gateway_hook post-bash`):** Structured audit log to `jobs/gateway_audit.jsonl`.
- **Stop (`gateway_hook stop`):** Reads `jobs/active_production_state.json` (actively written by `ProductionStateMachine`), verifies every completed stage's on-disk SHA-256 hashes, and denies stop (exit 2) if any stage is stuck `RUNNING` or corrupted.

## 4. Schema Backward-Compatibility & Cross-Platform Plan
- Existing `episodes/ep_toba/episode.json` remains 100% valid because new manifest keys (`fps`, `render_size`, `enable_post_assembly_spotting`, `character_references`) are optional.
- All file writes use PID+thread-unique temp files + `replace_file()` retry on Windows `PermissionError`; all state keys use `.as_posix()`; all CLI examples for the owner use single-line PowerShell.
