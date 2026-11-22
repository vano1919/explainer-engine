******  
******\*\*What changed vs. Round 1 and why:\*\* Expanded from 10 to 14 creator-only decisions (\`D-GOV-01\`..\`D-GOV-14\`). Added decisions surfaced directly by Round 2 attachments and Opus notes: reconciling \`runpod.per\_pod\_usd\` ($10 vs $6.9), \`modal-render\`'s $50 split, 80% AUTONOMOUS stop policy, and uncapped providers (\`D-GOV-04\`, \`D-GOV-10\`), direct creator-turn vs. coordinator-relayed AUTONOMOUS attestation (\`D-GOV-12\`), \`OR-30\` auto-push (\`D-GOV-13\`; D-92 and D-83 are decided and not reopened), and \`BP-168\` vs \`D-92\` pilot gates plus literal-cap vs. invariant tests (\`D-GOV-14\`). Kept all settled owner decisions closed\[cite: 2, 3, 4, 5, 6, 7\].******  
******  
******\~\~\~\~markdown******  
******\# DECISION\_PACKAGE — Creator-Only Decisions Required Before Implementation (Round 2 Final)******  
******  
******\*(Only decisions that belong strictly to the creator are listed below. Already-settled decisions — Fable default \`5.2 medium\`, V4.1 not approved and treated as a draft (the owner confirms it himself; not asked again), no Rule "2.1", no scope reduction, work GitHub account never used, merge to \`main\` creator-only — are NOT reopened.)\*******  
******  
******1. \*\*D-GOV-01 — Canonical coding, review & delegation routing (resolves CM-04, CM-25, CM-26):\*\*******  
***   ***\* \*\*Question:\*\* Confirm the single routing hierarchy to encode in \`config/model\_routing.json\` (after updating \`validate()\`):******  
***     ***\* Does the 2026-11-21 \`deepseek-worker\` rule (\*DeepSeek Flash/Pro writes code/tests/docs/drafts; Gemini Neon checks plan structure & PRs; Hydrogen fallback; Claude plans/reviews/never-list\*) formally \*\*supersede\*\* \`OR-26\` (Sonnet writes code) and \`OR-35\` (Claude API writes docs/tests/variants)?******  
***     ***\* Confirm canonical Gemini model names (\`Argon\` vs \`Neon\` vs \`Hydrogen\`) and confirm \`script-critic\` stays \`opus\` read-only (overriding \`argon\` in \`systemic\`'s \`gemini\_youtube\_routing\`).******  
***     ***\* Confirm updating \`OR-24\` from "higher model" to "independent fresh-context Opus reviewer thread (facts only; \`xhigh\`/Extra for irreversible or money-committing plans)".******  
******  
******2. \*\*D-GOV-02 — Paid-pod launch authority in \`NORMAL\` vs. \`AUTONOMOUS\` (resolves CM-02):\*\*******  
***   ***\* \*\*Question:\*\* Can an Opus review thread (\`OR-24\`) launch a paid RunPod pod without your separate approval, or does your approval always govern spend?******  
***   ***\* \*\*Options:\*\* \*\*(A) Recommended:\*\* In \`NORMAL\`, you approve every paid pod (Opus reviews the plan, never authorizes spend); in \`AUTONOMOUS\`, pods inside your pre-approved Category E/F/G scope + caps launch without re-asking. \*\*(B)\*\* Keep \`OR-24\` letting an Opus thread launch pods in \`NORMAL\`.******  
******  
******3. \*\*D-GOV-03 — Delegation policy for business gates (\`OR-15\`, \`OR-16\`, \`OR-17\`, \`OR-19\`, \`OR-31\`) & parallel agents (\`OR-20\`) in \`AUTONOMOUS\` (resolves CM-03, CM-15):\*\*******  
***   ***\* \*\*Question:\*\* (a) In \`AUTONOMOUS\`, should \`OR-15/16/17/19/31\` be \*\*retained by creator by default with explicit per-gate opt-in checkboxes in Category G\*\* (recorded as \`kind: delegated\` + \`auth\_id\`), or permanently non-delegable? (b) Should \`OR-20\` (only critics spawned) stay strict, or may Category C/D authorize bounded parallel subagents for non-story tasks?******  
******  
******4. \*\*D-GOV-04 — Canonical \`config/spend\_caps.json\` & branch reconciliation base (resolves CM-09, CM-13):\*\*******  
***   ***\* \*\*Question:\*\* Confirm the exact live numbers and integration base (\`systemic/next-video\` after reconciliation) before any governance PR merges:******  
***     ***\* \`claude\_api.max\_usd\`: the global max_usd of 125 is approved (DECISIONS_AND_OPEN_QUESTIONS, 2026-11-22) and is not re-asked. UNVERIFIED: whether modal-render's $50 split (opus_code + opus_tech_check) is superseded by $125 or a separate budget line (the source text is damaged).******  
***     ***\* \`runpod.per\_pod\_usd\`: revert \`systemic\`/\`modal-render\`'s one-time \`******10.0\`(PR\#146)backto\`******6.9\`, or keep \`$10.0\`?******  
***     ***\* \`paid\_tests.p12e\_hosts\` (\`$1.77\`, stays unspent per \`D-89\`, no pod is planned for it; the line is not renamed or dropped): confirm whether UNVERIFIED: \`paid\_tests.total\_usd\` drops from \`******5.90\`to\`******4.13\` or keeps \`$1.77\` unassigned.******  
***     ***\* Confirm preserving all 7 \`protected\_files\` from \`systemic\`/\`modal-render\` (plus the new governance files) and bringing \`deepseek\_api\`, \`.claude/rules/cloud-platforms.md\`, and \`modal\_MAP\_25D\_RULES.md\` onto the reconciled branch.******  
******  
******5. \*\*D-GOV-05 — Formal deprecation of \`OR-34\` (Fable pre-paid-test API audit) (resolves CM-10):\*\*******  
***   ***\* \*\*Question:\*\* Confirm marking \`OR-34\` as \`DEPRECATED\` (replaced by Opus \`high\`/\`xhigh\` review per your 2026-11-19 direction) and aligning every Fable-capable class in \`config/model\_routing.json\` across all branches to \`claude-fable-5-2\` at \`medium\` default (removing Fable \`xhigh\`/\`max\` from \`whole-project-plan\` except on explicit special request).******  
******  
******6. \*\*D-GOV-06 — Opus Extra \`.py\` edit policy in \`AUTONOMOUS\` (resolves CM-11):\*\*******  
***   ***\* \*\*Question:\*\* Should \`code.effort\_ceiling: "high"\` remain a hard ceiling in both modes (keeping Opus Extra strictly for planning/audits/reviews), or may the Category D card authorize a session-scoped \`effort\_override\` when you want Opus Extra to edit \`.py\` files?******  
******  
******7. \*\*D-GOV-07 — Fail-closed protection of governance, hook, ledger & cap code (resolves CM-06, CM-07, CM-19, CM-20):\*\*******  
***   ***\* \*\*Question:\*\* Confirm adding \`.claude/settings.json\`, \`explainer\_engine/governance/\*\*\`, \`explainer\_engine/core/spend\_caps.py\`, \`explainer\_engine/core/ledger.py\`, \`config/governance\_modes.json\`, \`docs/PLAN\_SCOPE\_RULES.md\`, and auth/approval records to \`protected\_files\`, switching denying hooks to \*\*fail-closed\*\*, blocking \`EXPLAINER\_SPEND\_CAPS\` outside \`pytest\`, blocking plain \`main\` push / \`gh pr merge\` / GitHub MCP merges, and requiring explicit creator approval (NORMAL) or Category B tick (AUTONOMOUS) to modify governance files.******  
******  
******8. \*\*D-GOV-08 — Unattended RunPod pods in \`AUTONOMOUS\` before \`P12a\` proves in-pod stop key (resolves CM-05):\*\*******  
***   ***\* \*\*Question:\*\* Until \`P12a\` proves the in-pod key can stop the pod (\`CR-03\`), confirm keeping unattended \`AUTONOMOUS\` RunPod launches \*\*blocked\*\* (because session guards die in 5–30 min and GitHub Actions cron lags 4–7 h) and keeping Haiku strictly read-only monitoring.******  
******  
******9. \*\*D-GOV-09 — Claude Code native permission mechanism for \`AUTONOMOUS\` (resolves CM-08):\*\*******  
***   ***\* \*\*Question:\*\* When activating \`AUTONOMOUS\` (with Python governance hooks still active and fail-closed), which native Claude Code setting do you approve for routine tool calls: \*\*(A)\*\* launching the session with CLI \`--permission-mode bypassPermissions\` (where allowed by managed policy), or \*\*(B)\*\* user/local scoped \`permissions.allow\` prefixes without \`bypassPermissions\`?******  
******  
******10. \*\*D-GOV-10 — 80% budget policy in \`AUTONOMOUS\` & caps for currently uncapped services (resolves CM-12, F-14):\*\*******  
***    ***\* \*\*Question:\*\* (a) When you approve a task budget \`$X\` in AUTONOMOUS Category F, should the system \*\*stop and ask at 80% of \`$X\`\*\* UNVERIFIED: (current \`ledger.py\` behavior, so \`******10\`means\`******8\` spendable) or treat \`$X\` as 100% spendable up to the hard ceiling while still alerting at 80%? (b) Should hard ceilings now be added to \`config/spend\_caps.json\` for \`elevenlabs\_credits\` (per episode), \`modal\`, and \`hyperstack\` (instead of letting runs open without a ceiling)?******  
******  
******11. \*\*D-GOV-11 — Authoritative production stack & rule registry on \`systemic\` vs. \`ro5jb3\` (resolves CM-18):\*\*******  
***    ***\* \*\*Question:\*\* Removed as a question: the V4.1 status is already recorded in DECISIONS_AND_OPEN_QUESTIONS (2026-11-22). V4.1 is NOT approved and is treated as a draft; the owner will confirm it himself at the end. This point is not asked again.******  
******  
******12. \*\*D-GOV-12 — Attestation rule for activating \`AUTONOMOUS\` mode (resolves F-13):\*\*******  
***    ***\* \*\*Question:\*\* Must your acceptance of an \`AUTONOMOUS\` consolidated authorization card be typed \*\*directly by you in the executing thread\*\* (verifiable via \`UserPromptSubmit\` / direct session turn), or may a \*\*coordinator thread relay\*\* your approval (\`cmsg\_\` reference) to activate \`AUTONOMOUS\`?******  
******  
******13. \*\*D-GOV-13 — Standing background actions (\`OR-30\` auto-push, \`D-92\` auto-delete) & \`D-83\` legal-stop scope (resolves CM-22, CM-23, CM-24):\*\*******  
***    ***\* \*\*Question:\*\* In \`NORMAL\` mode, should \`OR-30\` WIP auto-backup pushes at 95% usage remain active as a standing creator authorization (with content secret-scan + \`vano1919\` account check added), or require per-session Category H/I opt-in? Not reopened: D-92 (24 h auto-delete of 0 GB stopped pods, creator's yes 2026-11-01) and D-83 (licence questions never block performance; the creator is not asked licence questions again).******  
******  
******14. \*\*D-GOV-14 — Housekeeping: \`BP-168\` vs \`D-92\` pilot gates, raster map font, and test cap-pinning (resolves CM-17, CM-21, F-21, F-22):\*\*******  
***    ***\* \*\*Question:\*\* Confirm four quick cleanups: (a) update \`BP-168\` (\`core/ledger.py\`) to match newer \`D-92\` item 7 (\`\<= 3\` seeds, \`\<= 3 min/min\`, pivot \`3–6\`, abandon \`\> 6\`); D-92 is the newer decision and is not reopened; (b) the Plan Scope Rules keep the names \`SC-1..SC-4\` (the owner's text, checked by \`test\_plan\_scope\_rules.py\`); no rename; (c) switch \`explainer\_engine/maps/draw.py\` from \`Inter.ttf\` to \`Liberation Serif\` now (\`modal\_MAP\_25D\_RULES.md\` §3); (d) replace hard-coded literal dollar caps/class counts in unit tests with invariant checks (sum \`\<= max\_usd\`, valid schema/approvals) so creator-approved cap edits don't break tests.******  
******\~\~\~\~\[cite: 2, 3, 4, 5, 6, 7\]******  
******  
******---******  
******
