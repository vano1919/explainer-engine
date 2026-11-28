# Wave 7 — Mid-Level & Principal Adversarial Code Review (Anti-Laziness & Blueprint-Hunter Pass)

- **Review Date:** 2026-11-25
- **Reviewer Role:** Principal QA Automation Architect & Adversarial Code Reviewer
- **Scope:** All files modified or created in Wave 5 and Wave 8.

## 1. Anti-Blueprint & Stub Audit
- **Checked for:** empty `Protocol`/`ABC` without concrete wired implementations, `pass`, `NotImplementedError`, `TODO`/`FIXME`, or unreachable helper functions.
- **Findings:**
  - `core/approvals.py`: `verify_approval_hmac`, `is_operation_consumed`, and `record_consumed_operation` are full SQLite WAL + `hmac.compare_digest` implementations with zero stubs.
  - `core/execution_gateway.py`: `authorize_paid_action` now directly invokes `approvals.sign_approval_proof` (eliminating the dead-code finding from Wave 1).
  - `governance/gateway_hook.py`: `check_write_payload` is wired into `main()` (`pre-write` mode) AND `.claude/settings.json` (`PreToolUse` `Write|Edit|MultiEdit|NotebookEdit`), verified by live subprocess exit code `2`.
  - `qa/identity_lock.py`: self-comparison guard executes before pose/histogram logic, catching both identical resolved paths and identical-content copies (SHA-256).
  - `qa/perceptual_qa.py`: `_measure_ebur128_lufs` executes real `ffmpeg -af ebur128=peak=true` and populates `youtube_editorial_checks` deterministically.

## 2. Hidden Fallbacks & Silent-Pass Audit
- **Caught & Fixed during Review:**
  - `maps/draw.py`: previously fell back to `Inter.ttf` (`_resolve_map_font`) and `ComicNeue-Bold.ttf` -> `Bangers-Regular.ttf` -> `ImageFont.load_default()` (`font(px, face="ui")`). Verified **0 remaining references** to `ComicNeue`, `Bangers`, `Inter.ttf`, or `load_default()` in `maps/draw.py`.
  - `governance/gateway_hook.py`: initial Wave 5 regex matched read-only `grep write_text config/...` as a false positive, and blocking `config/spend_caps.json` unconditionally conflicted with `governance/hooks.py` Lock 2 owner-recorded approval workflow. Both defects were caught by live test execution and fixed cleanly (`\.write_text\(` + Lock 2 separation).

## 3. Security, Concurrency & Cross-Platform Audit
- **SQLite WAL Ordering:** Verified `PRAGMA busy_timeout=15000` executes before `PRAGMA journal_mode=WAL` in both `core/spend_ledger.py` and `core/approvals.py`.
- **Atomic Writes:** Verified `core/store.py:write_text_atomic` uses `f"{path.name}.{os.getpid()}.{threading.get_ident()}.tmp"` and `episode/run.py` uses `replace_file()` for Windows `PermissionError` retry parity.
- **Windows Shell Parity:** Verified `_norm_exe()` strips `.exe`/`.cmd`/`.bat` and blocks PowerShell `Invoke-WebRequest`/`iwr`/`irm`/`Set-Content`/`Out-File`/`Add-Content` bypasses.
- **Protected Files & Spend Invariant:** Verified 0 modifications to the 848 protected files, `config/owner_approvals.json` remains `{}`, `config/spend_caps.json` untouched, `$0.00` paid spend.

## 4. Verdict
**PASS** — Zero remaining P0/P1 blueprint, silent-fallback, security, or cross-platform defects in the modified scope. Ready for Wave 9 real local renders.
