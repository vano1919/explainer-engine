******  
******\*\*What changed vs. Round 1 and why:\*\* Hardened the architecture against every new Round 2 finding: fixed the ElevenLabs \`||\` command bug; added non-agent-writable / hash-chained attestation + durable mount storage (\`/mnt/project-files/...\` instead of ephemeral gitignored \`jobs/\`) for both \`auth\_record.json\` and the LLM ledger; bound \`auth\_record.json\` to \`branch + base\_commit\_sha + sha256(spend\_caps.json) + sha256(model\_routing.json)\`; added \`pre\_bash\` + Stop-time \`git diff\` protection for DeepSeek subprocess edits, plain \`main\` push, \`gh pr merge\`, and GitHub MCP tools (\`mcp\_\_github\_\_\*\`); planned \`validate()\` extension for DeepSeek/Gemini providers; added browser permissions for Gemini Neon, \`gh auth status\` + secret-content scan for \`OR-30\` backups, explicit OAuth upload checkpointing, and \`D-83\` scoping inside PART 10\[cite: 2, 3, 4, 5, 6, 7\].******  
******  
******\~\~\~\~markdown******  
******\# DESIGN\_TWO\_MODES — Authoritative NORMAL & AUTONOMOUS Architecture (Round 2 Final)******  
******  
******\#\# 1. Architecture Delta (\`KEEP\` / \`CHANGE\` / \`REMOVE\` / \`ADD\`)******  
******  
******\#\#\# KEEP******  
******\* Exactly two operating modes: \*\*\`NORMAL\`\*\* and \*\*\`AUTONOMOUS\`\*\* (zero competing "auto" modes).******  
******\* \`config/spend\_caps.json\` as the sole canonical ceiling file (a lower task budget always wins; 80% stop mechanism preserved).******  
******\* \`config/model\_routing.json\` as the sole canonical model/effort routing file (extended cleanly to cover external providers).******  
******\* Read-only critics (\`script-critic\`, \`lora-checkpoint-judge\`) on \`opus\` \`high\` with \`Read\`, \`Grep\`, \`Glob\` only.******  
******\* \`CLOUD\_RUNBOOK.md\` deterministic pod safeguards (\`pod\_wrapper.sh\`, \`dryrun\`, \`CR-13\` fail-closed Stop hook on live pods, \`OR-33\` stream/checkpoint saving).******  
******\* \`hooks.py:main()\` non-zero \`SystemExit\` on unknown hook subcommand.******  
******\* \`D-57\` unlisted-only staging (going public is always the creator's click in YouTube Studio); merge to \`main\` always creator-only; work GitHub account never used.******  
******\* Settled creator decisions: Fable default \`5.2 medium\`, V4.1 not approved (draft until the owner confirms it himself), no Rule "2.1", \`PLAN\_SCOPE\_RULES\` (\`SC-1..SC-4\`).******  
******  
******\#\#\# CHANGE******  
******\* \*\*\`.claude/settings.json\`:\*\*******  
***  ***\* Fix line 9 ElevenLabs hook bug: replace \`(python3 -m ... || python -m ...)\` with single-interpreter \`"$(command -v python3 || command -v python)" -m explainer\_engine.standards.hook\` (matching all other hooks).******  
***  ***\* Add \`PreToolUse\` matcher for GitHub MCP tools (\`mcp\_\_github\_\_.\*\`) routed to \`governance.hooks pre-mcp\` (blocking \`merge\_pull\_request\` to \`main\` and \`create\_or\_update\_file\` on protected paths).******  
***  ***\* Add valid baseline \`permissions.allow\` (safe reads/tests), \`permissions.ask\` (git push, paid CLIs), and \`permissions.deny\` (destructive commands, direct edits to governance/settings/secrets). Never place unsupported \`defaultMode: auto\` or \`bypassPermissions\` in project JSON.******  
***  ***\* Verify \`PreModelSwitch\`, \`PostModelSwitch\`, \`StopFailure\`, \`statusLine.refreshInterval\`, and Windows shell compatibility via \`/hooks\` and \`claude doctor\` before rollout.******  
******\* \*\*\`explainer\_engine/governance/hooks.py\` & \`governance/\_\_init\_\_.py\`:\*\*******  
***  ***\* \*\*Fail-closed split:\*\* Make denying safety/money/scope hooks \*\*fail-closed (exit \`2\`)\*\* on exceptions, malformed JSON, invalid \`model\_routing.json\`, missing/corrupt \`auth\_record.json\`, or \`shlex\` parse failures (\`pre-bash\`, \`pre-write\`, \`pre-agent\`, \`pre-switch\`, \`pre-mcp\`, plus \`stop\` when live billing exists). Keep advisory hooks \*\*fail-open (exit \`0\`)\*\* (\`prompt\`, \`statusline\`, \`post-edit\`, \`post-switch\`). To avoid deadlocking repair on a broken config, allow only a tiny hardcoded safe read-only command set (\`git status\`, \`git diff\`, \`ls\`, \`cat\`) when config load fails in \`pre-bash\`, and deny everything else.******  
***  ***\* \*\*Check order & bypass hardening:\*\* Run \`check\_git()\` \*\*before\*\* \`load(root)\` in \`pre\_bash\`; block non-force \`git push\` to \`main\`/\`master\` and \`gh pr merge\`; normalize paths across \`cd\`, relative paths, and separate git worktrees (\`\_rel()\` must inspect paths outside repo root such as \`\~/.claude/\` and sibling worktrees); block \`EXPLAINER\_SPEND\_CAPS\` and ledger/routing env overrides in \`pre\_bash\`; validate \`deepseek\_api code --files\` against \`protected\_files\` in \`pre\_bash\`; add a Stop-hook \`git diff --name-only\` audit that flags any modified protected file lacking a valid authorization record.******  
***  ***\* \*\*Model/agent enforcement:\*\* Enforce \`code.never\_models\` in \`pre\_write\`; enforce \`spawners\` and frontmatter-fallback model checks in \`pre\_agent\`; update \`validate()\` to support an explicit \`external\_providers\` section (DeepSeek Flash/Pro, Gemini Neon/Argon/Hydrogen) without breaking hook validation.******  
***  ***\* \*\*Mode awareness:\*\* Every denying hook reads canonical \`auth\_record.json\` (in \`NORMAL\` -\> strict rules; in \`AUTONOMOUS\` -\> authorized Categories A–I pass without re-prompting, out-of-scope actions exit \`2\`).******  
***  ***\* \*\*Auto-backup (\`OR-30\` / \`usage.py\`):\*\* Add content-level secret scanning (reusing \`claude\_api\` secret patterns) and verify \`gh auth status\` is personal \`vano1919\` (never work account) before any backup push.******  
******\* \*\*\`config/model\_routing.json\`:\*\*******  
***  ***\* Expand \`protected\_files\` to include all 7 files from \`systemic\`/\`modal-render\` PLUS \`.claude/settings.json\`, \`explainer\_engine/governance/\*\*\`, \`explainer\_engine/core/spend\_caps.py\`, \`explainer\_engine/core/ledger.py\`, \`config/governance\_modes.json\`, \`docs/PLAN\_SCOPE\_RULES.md\`, and the auth/approval record paths.******  
***  ***\* Align \`fable\` to \`claude-fable-5-2\` with \`medium\` default across all Fable-capable classes on every branch; add explicit DeepSeek/Gemini entries once \`D-GOV-01\` is decided.******  
******\* \*\*\`explainer\_engine/core/spend\_caps.py\`, \`core/ledger.py\`, \`llm/claude\_api.py\`, \`config/spend\_caps.json\`:\*\*******  
***  ***\* Restrict \`EXPLAINER\_SPEND\_CAPS\` env override strictly to \`PYTEST\_CURRENT\_TEST\`.******  
***  ***\* Set \`paid\_tests.p12e\_hosts.runpod\_usd\` to \`0.0\` (and refuse \`"status": "dropped"\` in \`paid\_test()\`).******  
***  ***\* Add typed validators for \`claude\_api\`, \`deepseek\_api\`, \`modal\`, and ElevenLabs ceilings.******  
***  ***\* Move LLM/paid-run ledger default to durable shared storage (e.g., \`/mnt/project-files/explainer-engine/\_ledger/\` when present, with \`LedgerConflict\` check) so fresh cloud containers never reset spend to \`$0\`.******  
***  ***\* Fix \`ClaudeAPI.run\_for\` to enforce \`min(config\_cap, session\_auth\_budget)\` instead of overwriting lower budgets; bind \`approval\` to \`amount + date + scope + ref\`; disable silent server-side model substitution (or require \`Result.model\` to match allowlist and populate \`Result.fell\_back\_to\`); enforce \`stream\_proof\` and cap checks inside \`ClaudeAPI.complete()\` as well as CLI \`main()\`.******  
******\* \*\*Canonical docs (\`CLAUDE.md\`, \`ORCHESTRATION.md\`, \`PRODUCTION\_RULES.md\`, \`DECISIONS\_AND\_OPEN\_QUESTIONS.md\`, \`SOURCED\_RULES.md\`):\*\*******  
***  ***\* Reconcile \`OR-22\`/\`OR-23\`/\`OR-24\`/\`OR-06\`/\`OR-26\`/\`OR-35\`/\`OR-36\`, \`PRODUCTION\_RULES.md\` §1.10, \`D-92\` auto-delete wording, \`BP-168\` vs \`D-92\` pilot gates, \`ORCHESTRATION.md\` table formatting (\`OR-25\`/\`OR-26\`/\`OR-09\`/\`OR-10\`), and V4.1 label (draft until the owner confirms approval; not "disqualified").******  
***  ***\* Tag legacy still-route/retired rules \`\[LEGACY\]\` or \`\[DEPRECATED\]\` (never delete historical records; prevent active paths from following them).******  
******  
******\#\#\# REMOVE******  
******\* Remove the \`||\` fallback around \`python3 -m explainer\_engine.standards.hook\` in \`.claude/settings.json\`.******  
******\* Remove blanket fail-open \`except Exception: return 0\` from denying governance hooks (replace \`test\_a\_broken\_hook\_fails\_open\_and\_garbage\_stdin\_is\_ignored\` with split fail-closed/fail-open tests).******  
******\* Remove \`OR-34\` as an active pre-paid-test blocker (retain as \`\[DEPRECATED\]\`).******  
******\* Remove unrestricted \`Bash\` tool from \`.claude/agents/paid-run-watchdog.md\` (replace with read-only status allowlist).******  
******\* UNVERIFIED (V4.1 is an unapproved draft per DECISIONS; the owner confirms it himself and D-GOV-11 must not be asked): remove disqualified \`v4.1 / D-126\` active status from \`systemic\` once creator decides \`D-GOV-11\` (retain archived copy labeled \`\[DISQUALIFIED HISTORY\]\`).******  
******\* Remove duplicated rule prose across \`CLAUDE.md\`, agents, and skills (link canonical files instead).******  
******  
******\#\#\# ADD******  
******\* \*\*\`config/governance\_modes.json\`:\*\* Single canonical definition of \`NORMAL\`, \`AUTONOMOUS\`, Categories A–I, authority hierarchy, stop conditions, and delegation defaults.******  
******\* \*\*\`explainer\_engine/governance/auth.py\` + durable \`auth\_record.json\`:\*\* Machine-readable authorization record stored on the durable mount (not ephemeral \`jobs/\`) with \`auth\_id\`, \`mode\`, \`branch\`, \`base\_commit\_sha\`, \`spend\_caps\_sha256\`, \`model\_routing\_sha256\`, \`issued\_at\`, \`expires\_at\`, \`revoked\`, \`creator\_ref\`, \`attestation\_kind\` (\`direct\_creator\_turn\` | \`coordinator\_relay\` per \`D-GOV-12\`), integrity HMAC/hash (with key outside agent-writable repo if host supports it, plus \`UserPromptSubmit\` turn-capture check), and Categories \`A\`–\`I\`.******  
******\* \*\*Consolidated Request CLI (\`python -m explainer\_engine.governance auth-request\`):\*\* Prepopulates Categories \`A\`–\`I\` from live repo state (\`git\`, \`spend\_caps.json\`, \`model\_routing.json\`, durable ledger), explicitly labeling every value \`VERIFIED\` or \`UNKNOWN\`, and showing both ceiling and 80% stop line for every financial cap.******  
******\* \*\*Unified paid-action guard (\`governance.auth.check\_paid\_action(...)\`):\*\* Called by \`runpod.py\`, \`claude\_api.py\`, \`deepseek\_api.py\`, \`opus\_code.py\`, \`paint.py\`, and \`standards/hook.py\`.******  
******\* \*\*Prompt-hook active-mode banner:\*\* \`hooks.py:prompt\` prints one compact line showing active mode, \`auth\_id\`, remaining time, and branch match so no subagent or resumed turn re-asks already-authorized permissions.******  
******\* \*\*Two-mode governance test suite (\`tests/unit/test\_two\_mode\_governance.py\`):\*\* Full PART 11 coverage using mocked providers only.******  
******  
******---******  
******  
******\#\# 2. Mode Specifications******  
******  
******\#\#\# Mode 1: \`NORMAL\` (Default)******  
******\* \*\*Behavior:\*\* Creator approves individual protected decisions, paid operations, model escalations, protected-file edits, and business gates (\`OR-15\`, \`OR-16\`, \`OR-17\`, \`OR-19\`, \`OR-31\`).******  
******\* \*\*Claude Code native mode:\*\* \`default\` (interactive prompts active; project \`permissions.allow\`/\`ask\`/\`deny\` apply; never bypass native permission prompts).******  
******\* \*\*Hooks & caps:\*\* Fail-closed denying hooks enforce protected files, \`code.effort\_ceiling: "high"\`, \`code.never\_models: \["fable"\]\`, \`opus\` critics, \`spawners\`, destructive git / \`main\` push / GitHub MCP locks, and \`spend\_caps.json\`.******  
******\* \*\*Automatic fallback:\*\* Missing, expired, revoked, corrupted, branch-mismatched, or config-hash-mismatched \`auth\_record.json\` always resolves to \`NORMAL\`.******  
******  
******\#\#\# Mode 2: \`AUTONOMOUS\` (Task-Scoped, Single Consolidated Authorization)******  
******\* \*\*Entry flow:\*\*******  
***  ***1. Creator requests \`AUTONOMOUS\` for a defined task.******  
***  ***2. Claude runs \`governance auth-request\` and presents \*\*ONE consolidated authorization request\*\* prepopulated from current config and ledger, marking every field \`VERIFIED\` or \`UNKNOWN\`.******  
***  ***3. Creator accepts (all or selected categories) in one response and enables the chosen Claude Code native permission mechanism (Section 3).******  
***  ***4. \`governance auth activate\` writes the validated \`auth\_record.json\` bound to \`auth\_id\`, \`branch\`, \`base\_commit\_sha\`, \`spend\_caps\_sha256\`, \`model\_routing\_sha256\`, \`issued\_at\`, and \`expires\_at\`.******  
******\* \*\*Consolidated Authorization Categories (\`A\`–\`I\`):\*\*******  
***  ***\* \*\*A. Working environment:\*\* repository, current branch, \`base\_commit\_sha\`, allowed branches, working directory, permitted paths, worktree/branch creation.******  
***  ***\* \*\*B. File & code operations:\*\* read/write/edit/create scope (code, tests, docs, scripts, local builds, test suites, commits) vs. protected files (\`.claude/settings.json\`, \`spend\_caps.json\`, \`model\_routing.json\`, \`governance\_modes.json\`, \`governance/\*\*\`, \`core/spend\_caps.py\`, \`core/ledger.py\`, \`auth\_record.json\`, \`creator\_ok.jsonl\`, \`cheapest.py\`, \`cheapest.json\`, \`ltx/launch.json\` — default \*\*DENIED\*\* unless explicitly ticked).******  
***  ***\* \*\*C. Shell & tools:\*\* allow-listed Bash classes (\`git\`, \`python\`, \`pytest\`, \`deepseek\_api\`, rendering), browser/web (explicitly noting Gemini Neon browser driver if used), MCP connectors (ElevenLabs, GitHub read-only vs mutating), background processes, agent/subagent spawning (\`orchestrator\`, \`lora-coordinator\`, critics, watchdog). Explicitly states: an allowed tool is NOT authorization for every action it can perform.******  
***  ***\* \*\*D. Model & agent permissions:\*\* permitted models and efforts consistent with \`config/model\_routing.json\` (Haiku Low watchdog, Sonnet routine, Opus planning/review, Opus Extra where genuinely available & explicitly approved, Fable under \`5.2 medium\` / special-request rule, DeepSeek Flash/Pro, Gemini Neon/Hydrogen), model switching within approved set, parallel agent limit.******  
***  ***\* \*\*E. Network & external services:\*\* per-provider split between \*\*read-only\*\* and \*\*billable/mutating\*\* access (GitHub including Actions \`workflow\_dispatch\`, Hugging Face, Modal, Hyperstack, RunPod, ElevenLabs, Gemini, Claude API, DeepSeek API, MCP).******  
***  ***\* \*\*F. Financial authorization:\*\* total task budget (capped \`\<= config/spend\_caps.json\`; lower user budget wins), showing both ceiling and 80% stop line; per-provider, per-call, per-run, daily/weekly, GPU runtime, API request/generation limits, retry budget, storage/egress, free credits, current durable-ledger spend, remaining budget. UNVERIFIED: paid actions within exact scope require no repeated approval (pending D-GOV-02/D-GOV-03; OR-06, OR-23 and OR-24 apply until answered); unknown prices, exceeded caps, new providers, new resource classes, or materially different workloads stop immediately.******  
***  ***\* \*\*G. Decision delegation:\*\* explicit per-item setting (\`RETAINED\_BY\_CREATOR\` default vs. \`DELEGATED\_TO\_AGENT\`) for technical/architecture choices, model/effort selection, model routing, creative/visual style, provider selection, paid-run launch, retries, git operations, publishing, and each of \`OR-15\`, \`OR-16\`, \`OR-17\`, \`OR-19\`, \`OR-31\`. Delegated approvals are recorded as \`kind: delegated\` + \`auth\_id\`, never masquerading as \`kind: creator\`.******  
***  ***\* \*\*H. Git & delivery:\*\* feature-branch commit, push, PR creation, branch updates (configurable); \*\*merge to \`main\`, modifying \`main\`, branch deletion, rebase, force push default DENIED\*\* (merge to \`main\` is never delegable).******  
***  ***\* \*\*I. Destructive operations & public exposure:\*\* deleting files, jobs, pods/cloud resources (beyond narrow \`D-92\` 0 GB rule if active), volumes, snapshots, assets, replacing approved results, publishing, making public — \*\*default DENIED\*\* (public upload is never delegable; YouTube OAuth sign-in per \`SO-9\` remains a clean creator pause).******  
******\* \*\*Execution guarantees:\*\* Unapproved categories stay restricted while authorized categories continue; no agent may re-ask an already-authorized action, rephrase a denied request, or modify/extend \`auth\_record.json\`; an out-of-scope action stops \*\*only\*\* that operation with a structured block report while unrelated authorized work continues; branch switches, config-hash changes, revocation, or expiry immediately invalidate \`auth\_record.json\` and revert to \`NORMAL\`.******  
******  
******---******  
******  
******\#\# 3. Real Claude Code Native Permission Mapping (PART 7)******  
******  
******| Mechanism | \`NORMAL\` | \`AUTONOMOUS\` | Blocking Layer & Verification |******  
******|---|---|---|---|******  
******| \*\*Project \`.claude/settings.json\`\*\* | Baseline \`permissions.allow\` (read/search/pytest), \`permissions.ask\` (git push, paid CLIs), \`permissions.deny\` (destructive ops, direct edits to governance/secrets); \*\*no\*\* \`defaultMode: auto/bypassPermissions\` | Identical project baseline (never weakened) | Project JSON cannot set \`auto\`/\`bypassPermissions\` on restricted Claude Code versions; verified via \`/permissions\` |******  
******| \*\*Native Claude Code Permission Mode\*\* | \`default\` | Creator launches session with CLI \`--permission-mode bypassPermissions\` (if permitted by managed policy \`disableBypassPermissionsMode\`) \*\*OR\*\* user/local scoped \`permissions.allow\` prefixes matching Categories B/C/E (per \`D-GOV-09\`). Hook-based JSON \`permissionDecision: "allow"\` is \*\*not\*\* assumed until verified in live runtime | If managed/cloud policy blocks \`bypassPermissions\`, report the exact blocking layer and fall back to scoped allowlist; never claim a mode is active until \`/status\` and \`/permissions\` confirm it |******  
******| \*\*Custom Python Hooks (\`PreToolUse\`, \`Stop\`, etc.)\*\* | Active & fail-closed on safety/money | \*\*Still active\*\* under native \`bypassPermissions\` (verify live); consults \`auth\_record.json\` so in-scope actions exit \`0\` and out-of-scope actions exit \`2\` | Native bypass does NOT disable Python governance hooks; hooks enforce Categories A–I deterministically |******  
******| \*\*MCP & Browser Tools\*\* | Explicit per-tool prompt + \`standards/hook.py\` + new \`pre-mcp\` GitHub hook | Explicitly allow-listed in native MCP/browser permissions AND Categories C/E of \`auth\_record.json\` | Bash permissions never cover MCP or Gemini Neon browser-driver actions; verify separately in \`/permissions\` |******  
******  
******---******  
******  
******\#\# 4. One Authoritative Governance Hierarchy & Single-Source-of-Truth Registry (PART 8)******  
******  
******The instruction precedence is the one fixed in the preamble of DECISIONS_AND_OPEN_QUESTIONS (D-23: one canonical home); the list below is the enforcement layering only, not a second precedence order. Runtime reality separates \*\*hard technical gates\*\* from \*\*policy authority\*\*; if canonical config and enforcing code disagree on any critical rule, the system \*\*halts\*\* rather than letting one silently override the other:******  
******  
******1. \*\*Platform / OS / Managed Security / Legal (scoped by \`D-83\`) & Provider Hard Controls\*\* \*(Host/OS, managed settings, GitHub branch protection, provider API auth/caps — unbypassable by repo)\*******  
******2. \*\*Creator's Latest Explicit Decisions & Validated \`auth\_record.json\`\*\* \*(Policy authority: \`DECISIONS\_AND\_OPEN\_QUESTIONS.md\` + active \`auth\_record.json\` bound to \`creator\_ref\`, branch, base SHA, config hashes, expiry — enforced by code)\*******  
******3. \*\*Canonical Governance & Financial Configuration\*\* \*(\`config/spend\_caps.json\`, \`config/model\_routing.json\`, \`config/governance\_modes.json\` — enforced by code; conflict with Layer 5 = STOP)\*******  
******4. \*\*Claude Code Native Permission Configuration\*\* \*(Managed \> CLI \> Local \> Project \> User \`permissions.allow/ask/deny\` & session mode — enforces dialog gating; can only execute within Layer 1–3 bounds)\*******  
******5. \*\*Project Runtime Hooks & Application Gates\*\* \*(\`.claude/settings.json\` -\> \`governance/hooks.py\`, \`cloud/hooks.py\`, \`standards/hook.py\`, \`core/spend\_caps.py\`, \`core/ledger.py\`, \`production\_gate\`, \`paint.py\`, \`runpod.py\`, \`llm/\*.py\` — enforced by code)\*******  
******6. \*\*Canonical Workflow Specifications\*\* \*(\`docs/ORCHESTRATION.md\`, \`docs/CLOUD\_RUNBOOK.md\`, \`docs/PRODUCTION\_RULES.md\`, \`docs/EPISODE\_STANDARDS.md\`, \`docs/PLAN\_SCOPE\_RULES.md\` — instruction unless backed by a named validator)\*******  
******7. \*\*Agent Frontmatter & Instructions\*\* \*(\`.claude/agents/\*.md\` — tool surface enforced by runtime; prose is instruction only)\*******  
******8. \*\*Skills\*\* \*(\`.claude/skills/\*/SKILL.md\` — instruction only; link canonical sources, never duplicate)\*******  
******9. \*\*Historical / Legacy / Disqualified Archive\*\* \*(\`docs/PLAN\_2026-10-15.md\`, \`docs/PROGRESS.md\`, superseded \`D-xx\`/\`OR-xx\`, V4.1 (unapproved draft) — explicitly tagged \`\[LEGACY\]\`/\`\[DEPRECATED\]\`/\`\[DISQUALIFIED\]\`)\*******  
******  
******\#\#\# Single-Source-of-Truth Registry******  
******  
******| Governance Concept | Canonical Home | Enforcement Path | Current Status |******  
******|---|---|---|---|******  
******| \`NORMAL\` / \`AUTONOMOUS\` definitions, stop conditions, delegation defaults | \`config/governance\_modes.json\` | \`governance/auth.py\` + \`governance/hooks.py\` | \`NOT\_IMPLEMENTED\` |******  
******| Active session scope, expiry, branch/hash binding | Durable \`auth\_record.json\` | \`governance/auth.py\` + all denying hooks + paid clients | \`NOT\_IMPLEMENTED\` |******  
******| Spending ceilings, allowances, paid tests | \`config/spend\_caps.json\` | \`core/spend\_caps.py\` + durable \`core/ledger.py\` | \`IMPLEMENTED (needs env-bypass, p12e, durability, run\_for fixes)\` |******  
******| Model, effort & provider routing | \`config/model\_routing.json\` | \`governance/\_\_init\_\_.py\` + \`governance/hooks.py\` + \`test\_agent\_governance.py\` | \`PARTIAL (needs external providers, never\_models, spawners, Fable 5.2 medium alignment)\` |******  
******| Approval ownership & creative gates (\`OR-15/16/17/19/31\`) | \`docs/ORCHESTRATION.md\` + \`config/governance\_modes.json\` | \`scenario.py\`, \`reference\_approval.py\`, \`script\_approval.py\`, \`sample.py\`, \`paint.py\`, \`standards/hook.py\` | \`IMPLEMENTED (needs kind: delegated + ElevenLabs \\|\\| fix)\` |******  
******| Protected files, destructive git & GitHub MCP guards | \`config/governance\_modes.json\` (migrated from \`model\_routing.json\`) | \`governance/hooks.py\` (\`pre-bash\`, \`pre-write\`, \`pre-mcp\`, \`stop\` diff check) | \`PARTIAL (needs self-protection, fail-closed, MCP/main/DeepSeek hardening)\` |******  
******  
******---******  
******  
******\#\# 5. Haiku Watchdog & Operational Reliability (PART 9)******  
******  
******\* \*\*Role:\*\* Independent, low-cost (\`haiku\`, \`low\`) \*\*read-only observer\*\* running beside paid runs.******  
******\* \*\*Capabilities:\*\* Reads \`auth\_record.json\`, durable financial ledger, stream/checkpoint files (\`OR-33\`), and read-only status outputs (\`runpod check|status|logs|cost\`). Reports progress, budget consumption, approaching 80% limits, stalled stream growth, missing outputs, failures, and claimed success without artifact evidence.******  
******\* \*\*Hard prohibitions:\*\* Never approves spend, modifies code/hooks/config/auth records, stops pods directly, or invents success. Unrestricted \`Bash\` is removed from \`.claude/agents/paid-run-watchdog.md\` (replaced by a tightly allowlisted read-only status interface).******  
******\* \*\*Deterministic stop ownership (independent of Haiku):\*\* Enforced exclusively by (1) durable \`core/ledger.py\` pre-call reservation + 80% refusal, (2) provider-side caps where available, and (3) \`pod\_wrapper.sh\` dead-man (\`CR-05\`) with a \*\*P12a-verified\*\* stop-capable in-pod key plus external GitHub watchdog (\`CR-12\`). Until P12a proves the in-pod stop key, unattended AUTONOMOUS RunPod launches remain blocked (\`D-GOV-08\`).******  
******  
******---******  
******  
******\#\# 6. Automatic Stop Conditions (PART 10 — Always Enforced, Fail-Closed)******  
******  
******1. Budget ceiling exceeded or 80% stop policy triggered (never silently raise or create a new budget).******  
******2. Action outside approved \`auth\_record.json\` scope (Categories A–I).******  
******3. Unknown/unpriced financial action, new provider, or new resource class.******  
******4. Failed mandatory validation, schema check, or test (never weaken or delete a test/criterion).******  
******5. Missing, empty, or corrupted expected output (never report success without verified output evidence).******  
******6. Unverified provider environment (failed \`dryrun\`, missing \`CR-19\` secrets check, unproven in-pod stop key for unattended pod).******  
******7. Missing, expired, revoked, corrupted, or integrity-failed \`auth\_record.json\` (in AUTONOMOUS).******  
******8. Branch mismatch, rebased/reset \`base\_commit\_sha\`, or modified \`spend\_caps.json\`/\`model\_routing.json\` hash against \`auth\_record.json\`.******  
******9. Unauthorized destructive action, merge/push to \`main\`, or public exposure outside scope.******  
******10. Credential/secret exposure (including content scan on \`OR-30\` auto-backup) or work GitHub account detected.******  
******11. Security or legal restriction (platform policy, copyright/fair use, privacy/defamation; tool/model licence questions never block and are not asked again (D-83)).******  
******12. Unresolved CRITICAL governance inconsistency (e.g., branch cap divergence or config-vs-code conflict).******  
******13. Required external/runtime permission Claude Code or OS cannot grant (e.g., managed policy blocks mode, manual OAuth upload link required).******  
******  
******\*\*Mandatory block report format:\*\* \`(1) Attempted action | (2) Blocking artifact (exact file/hook/permission/policy/provider) | (3) Classification (genuine safety restriction vs. accidental conflict) | (4) Smallest valid corrective action.\`******  
******  
******---******  
******  
******\#\# 7. Verification & Test Plan (PART 11 — Mocked Providers Only, Zero Paid Runs)******  
******  
******\* \*\*NORMAL tests (\`tests/unit/test\_two\_mode\_governance.py\`):\*\* Routine work succeeds; all expanded protected files (\`.claude/settings.json\`, \`governance/\*\*\`, \`spend\_caps.py\`, \`ledger.py\`, \`auth\_record.json\`, \`creator\_ok.jsonl\`, \`cheapest.\*\`, \`ltx/launch.json\`) fail closed without override; paid calls refuse without creator approval; \`effort\_ceiling\`, \`never\_models: \["fable"\]\`, \`opus\` critics, and \`spawners\` enforced; OR-15/16/17/19/31 gates preserved.******  
******\* \*\*AUTONOMOUS tests:\*\* \`auth-request\` produces one consolidated card with \`VERIFIED\`/\`UNKNOWN\` labels and 80% stop figures; rejection stays \`NORMAL\`; acceptance writes durable \`auth\_record.json\`; authorized edits, shell commands, model switches, agent spawns, and paid calls within \`min(config\_cap, task\_budget)\` run without re-prompting across agents; branch switch, base-commit rebase, or config-hash drift invalidates auth; expiry/revocation reverts to \`NORMAL\`; out-of-scope action stops only itself while unrelated authorized work continues; returning to \`NORMAL\` restores confirmations.******  
******\* \*\*Hooks, bypass & adversarial tests:\*\*******  
***  ***\* Broken \`model\_routing.json\`, corrupt \`auth\_record.json\`, hook exception, or heredoc-apostrophe \`shlex\` error -\> \*\*fail-closed (exit 2)\*\* on denying hooks (\`pre-bash\` preserves force-push/\`branch -D\` checks even if config fails to load); advisory hooks fail open (\`exit 0\`).******  
***  ***\* ElevenLabs hook command test proving exit \`2\` deny is never swallowed by \`||\` or missing \`python\`.******  
***  ***\* Bypass rejections: \`EXPLAINER\_SPEND\_CAPS=/tmp/x.json\`, \`cd config && sed -i ... spend\_caps.json\`, outside-root/worktree writes to protected paths, \`deepseek\_api code --files config/spend\_caps.json\`, plain \`git push origin HEAD:main\`, \`gh pr merge\`, GitHub MCP \`merge\_pull\_request\`/\`create\_or\_update\_file\`, \`p12e\_hosts\` ledger open, \`paid-run-watchdog\` mutating command, server-side silent model fallback, \`OR-30\` secret-in-file push, and non-\`vano1919\` git account.******  
***  ***\* Combined spend-cap + hook chain test (closing PR \#256 gap): authorized cap update -\> enforced by mocked \`claude\_api\` -\> blocked again after auth expiry.******  
***  ***\* Durable ledger test across simulated fresh container (\`jobs/\` wiped, durable mount retained -\> spend does not reset to \`$0\`).******  
******\* \*\*End-to-end mocked integration:\*\* \`NORMAL\` -\> \`auth-request\` -\> activate \`AUTONOMOUS\` -\> verify runtime permission state -\> run mocked DeepSeek/Claude/RunPod/watchdog task -\> encounter out-of-scope action -\> confirm scoped block + structured report -\> finish unrelated authorized work -\> return to \`NORMAL\` -\> confirm normal blocks restored.******  
******  
******---******  
******  
******\#\# 8. Requirements Coverage (\`rules/ro5\_PLAN\_SCOPE\_RULES.md\` SC-4)******  
******  
******| Owner requirement id | Quote or pointer | Where the plan covers it | Status |******  
******|---|---|---|---|******  
******| PART 3 (Adversarial audit) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 3 | \`OPUS\_AUDIT.md\` §1–2 (\`F-01\`..\`F-23\`) | covered |******  
******| PART 4 (15-layer permission chain + fail-closed hooks) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 4 | \`OPUS\_AUDIT.md\` §3 + \`DESIGN\_TWO\_MODES.md\` §1, §3 | covered |******  
******| PART 5 (Formal conflict matrix + 14 known problems + statuses) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 5; \`PART5\_14\_problems.tsv\` | \`CONFLICT\_MATRIX.md\` (\`CM-01\`..\`CM-27\`) | covered |******  
******| PART 6 (Two modes NORMAL/AUTONOMOUS + consolidated auth A–I) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 6 | \`DESIGN\_TWO\_MODES.md\` §1–2 (Categories A–I) | covered |******  
******| PART 7 (Real Claude Code native permissions) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 7 | \`DESIGN\_TWO\_MODES.md\` §3 | covered |******  
******| PART 8 (One authoritative hierarchy + single source of truth) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 8 | \`DESIGN\_TWO\_MODES.md\` §4 | covered |******  
******| PART 9 (Haiku watchdog read-only + deterministic stops) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 9 | \`DESIGN\_TWO\_MODES.md\` §5 | covered |******  
******| PART 10 (Automatic stop conditions + block format) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 10 | \`DESIGN\_TWO\_MODES.md\` §6 | covered |******  
******| PART 11 (Two-mode, hook, bypass & integration tests, mocked) | \`01\_OWNER\_TASK\_PART3\_11.md\` PART 11 | \`DESIGN\_TWO\_MODES.md\` §7 | covered |******  
******| Prior owner decisions (Fable 5.2 medium, no Rule 2.1, V4.1 not approved (draft), no scope reduction, no work GitHub, main merge creator-only) | \`01\_OWNER\_TASK\_PART3\_11.md\` FINAL INSTRUCTION; \`ro5\_PLAN\_SCOPE\_RULES.md\` | Preserved in \`DESIGN\_TWO\_MODES.md\` §1 (\`KEEP\`); UNVERIFIED: none reopened in \`DECISION\_PACKAGE.md\` | covered |******  
******\~\~\~\~\[cite: 2, 3, 4, 5, 6, 7\]******  
******  
******---******  
******
