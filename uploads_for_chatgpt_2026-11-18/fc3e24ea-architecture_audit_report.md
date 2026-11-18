# Adversarial Architecture Audit Report — `DEC-2026-11-17-02` & `CLAUDE_CODE_NATIVE_ECOSYSTEM_ARCHITECTURE.md`

- **Repository Target:** `vano1919/explainer-engine`
- **Audit Scope:** `CLAUDE_CODE_NATIVE_ECOSYSTEM_ARCHITECTURE.md` (`52,354` bytes, SHA-256 `be29b384beb7007861926690640c8154e0b27fe7d83826993b78d0fd7b9db239`), `claude_code_ecosystem_architecture_proposal_DEC-2026-11-17-02.diff` (`64,102` bytes, SHA-256 `c5a92af685e0a86906d3513e9ad380953c44b088b2df222af5dd85b4d19293`), existing repository governance at `eb80e4434ea120f48cb9aea094ebd7b2b423d8f0`, official Claude Code documentation ([`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills)), external candidate repositories, and the 21 Argon/Opus/ChatGPT review artifacts in `docs/wip/argon_2026-11-14/`.
- **Financial Cost:** **$0.00** (strictly read-only repository audit and documentation correction).
- **Overall Recommendation:** **Approve with corrections** (apply `DEC_2026_11_17_02_CORRECTIONS.patch` after Owner sign-off).

---

## 1. Executive Scorecard Across Audit Workstreams

| Workstream / Audit Area | Verdict | Key Evidence & Primary Findings |
|---|---|---|
| **0. Repository Baseline & Reference Resolution (`eb80e443` vs. `a060cf0b`)** | **`PARTIAL`** | Local repo `/working_dir/c_0109806be13a9bd7/work_handoff/snapshot` is on branch `argon/p1-2-timing-contract` at `eb80e4434ea120f48cb9aea094ebd7b2b423d8f0` (`git status --short` = empty). However, the draft proposal conflated `eb80e443` and `a060cf0b` (`Baseline @ eb80e443 / a060cf0b` on L17, L229–232). In reality, local parent branch `o239-argon-impl` is at synthesized commit `3b275a310265865d6090fb0b7ca66996a78df092` (created from the text-only archive `REPO_TEXT_o239-argon-impl_a060cf0b.zip`), and neither `a060cf0b` (`a060cf0bb33a00974568d91c1dd30816de35da32`) nor `fc35615e` (`fc35615e1ad4b3804a6d07b7b0408e564cb8924c`) exists in `.git/objects` locally (`git rev-parse` exits `128`). |
| **A. Existing Repository & Governance Audit** | **`PASS` (with 1 minor fix)** | `CLAUDE.md` (141 lines), `.claude/settings.json` (101 lines), `.claude/rules/cloud-platforms.md` (154 lines), 16 `.claude/agents/*.md` files + 1 pending `youtube-viewer-critic.md`, 21 `.claude/skills/*/SKILL.md` files, `config/model_routing.json` (455 lines), `config/spend_caps.json` (115 lines), `explainer_engine/governance/hooks.py`, `explainer_engine/cloud/{hooks,cheapest}.py`, and `71/71` governance unit tests (`test_agent_roles.py`, `test_agent_governance.py`, `test_t3_agent_skill_banners.py`, `test_governance_hooks.py`) are accurately inventoried. **Minor defect fixed:** Draft L73 & L85 casually suggested optional new subagents for `Historical Researcher` and `Skill and Tool Researcher` without citing `config/model_routing.json` L253–261 (`multi-agent-analysis`: `"guard": "only on the creator's word (part 5)"`). |
| **B. Official Claude Code Architecture Audit** | **`PARTIAL`** | Draft correctly captured `SKILL.md` progressive disclosure, `disable-model-invocation`, `` !`cmd` `` injection, the `15,000`-token subagent description warning, and ignored plugin subagent frontmatter (`hooks`, `mcpServers`, `permissionMode`). **Defects found:** (1) Missed 3 critical plugin code-execution surfaces documented in [`code.claude.com/docs/en/plugins/security`](https://code.claude.com/docs/en/plugins/security): `bin/` PATH injection, `monitors` auto-started background processes, and `mods` in-process JS; (2) omitted reserved skill names (`synced`, `anthropic-skills`); (3) did not warn that bare `mcp__<server>__.*` hook matchers fail to match plugin-bundled MCP servers (`mcp__plugin_<plugin>_<server>__<tool>`). |
| **C. External Skill, Tool & Plugin Audit + FFmpeg Investigation** | **`PARTIAL`** | Dispositions for all 7 candidates are architecturally sound (`zq940222/blender-mcp-skill` rightly rejected as HTTP 404; `DirectorSKILL` named directors stripped per `no_names`; `cc-blender-skill` held out of v4.3 per `retired_era.json`; `ffmpeg-skill` kept out of master 24fps assembly). **Defects found:** (1) Draft L146 & L157 misattributed `"join.py: xfade offsets are written to the millisecond, so a transition whose offset rounds up starts one frame late"` to issue **`#469`**, whereas on [`github.com/kajisho5/ffmpeg-skill/issues`](https://github.com/kajisho5/ffmpeg-skill/issues) that bug is open issue **`#468`** (alongside open issue **`#455`** for millisecond clip lengths and **`#462`** for `cut.py`/`join.py` audit), while `#469` was the high-findings PR that spawned follow-up issue **`#470`**, and `#510` fixed `render` filter checks / `cut` flags without closing `#468` or `#455`; (2) Draft recorded 7-char short SHAs (`c65ae0d`, `f1c97cb`, `b5b01ac`) as if they satisfied the 40-char SHA requirement (`L211`). |
| **D. Registry, Provenance, Security & Validation Redesign** | **`FAIL` (Fixed in Patch)** | Three structural defects in Sections 7–9 of the draft: (1) **4-Table vs. 2-Table Mismatch:** L201 promised *"four linked, schema-validated tables"*, but L225–248 only rendered **two** tables and omitted the **Plugins** table entirely; (2) **`computedHash` Over-Generalization:** L212 applied `vercel-labs/skills` `skills-lock.json` v2 `computedHash` to all registry kinds, even though `computedHash` only hashes unpacked Skill folders; (3) **Hook-as-Sandbox Fallacy:** Section 9 treated `PreToolUse` hooks as a full runtime sandbox and Section 8 used a flat 7-point checklist instead of risk-tiered validation profiles (`VP-1..VP-6`). |
| **E. Argon / Opus / ChatGPT History Synthesis** | **`PARTIAL` (Fixed in Patch)** | The initial draft did not explicitly codify the 6 operational failure modes documented across the 21 files in `docs/wip/argon_2026-11-14/` (`sys.modules` monkeypatch leaks, test-accommodation production fallbacks, missing `sourced_rules write` sync, schema weakening during data fixes, false "all tests passed" claims on `KeyError: 'rows'`, and synthetic tests passing while real video frames failed eye checks). Added as Section 8.2 (`AG-01..AG-06`). |

---

## 2. Mandatory Step 1 — Repository Baseline Verification

Executed directly in `/working_dir/c_0109806be13a9bd7/work_handoff/snapshot` without mutating any branch or file:

| Baseline Check | Command Executed | Actual Measured Output | Status / Verdict |
|---|---|---|---|
| **Repository Root** | `git rev-parse --show-toplevel` | `/working_dir/c_0109806be13a9bd7/work_handoff/snapshot` | **`PASS`** |
| **Current Branch** | `git branch --show-current` | `argon/p1-2-timing-contract` | **`PASS`** |
| **Full 40-Character HEAD SHA** | `git rev-parse HEAD` | `eb80e4434ea120f48cb9aea094ebd7b2b423d8f0` (`eb80e443`) | **`PASS`** |
| **Working Tree Cleanliness** | `git status --short` | `""` (0 modified, 0 staged, 0 untracked files) | **`PASS`** |
| **Local Branches** | `git branch -a` | `argon/p1-2-timing-contract` (`eb80e443`), `o239-argon-impl` (`3b275a31`) | **`PASS`** |
| **Configured Remotes** | `git remote -v` | `""` (no remotes configured; offline sandbox VM has no outbound network) | **`PASS` (Offline VM)** |
| **Local Lookup of `a060cf0b` & `fc35615e`** | `git rev-parse --verify a060cf0b^{commit}` / `fc35615e^{commit}` | Exit code `128` (`fatal: Needed a single revision`) | **`NOT VERIFIED` as local `.git` objects** (verified via `PROJECT_STATE.md` & Drive `LATEST_COMMIT.json` metadata) |
| **Relationship Between `eb80e443` and `a060cf0b`** | `git log --oneline --decorate -n 5` | `eb80e443` (`P1.2: implement episode_timing/2 contract...`) is committed on top of local `3b275a310265865d6090fb0b7ca66996a78df092` (`Baseline: o239-argon-impl @ a060cf0b`), which was initialized from the text-only archive `REPO_TEXT_o239-argon-impl_a060cf0b.zip`. Thus `eb80e443` and `a060cf0b` are **not** the same commit; `eb80e443` is the local P1.2 child commit over the unpacked `a060cf0b` file tree. | **`PARTIAL` in draft -> Fixed in Patch** |
| **Supplied Proposal Artifacts** | `sha256sum` in `/working_dir/c_0109806be13a9bd7/artifacts/file_generation/ttl=63d/output/` | `CLAUDE_CODE_NATIVE_ECOSYSTEM_ARCHITECTURE.md` (`52,354` B, `be29b384...`) and `claude_code_ecosystem_architecture_proposal_DEC-2026-11-17-02.diff` (`64,102` B, `c5a92af6...`) exist in output artifacts and are **not** applied to `snapshot/docs/architecture/`. | **`PASS`** |

---

## 3. Workstream A — Existing Repository and Governance Audit

All governance files and unit tests were inspected directly on disk and executed (`71 passed in 3.21s`, `docs_lint: 0 finding(s)`):

### 3.1 Inspected Governance Files & Enforcement Mechanisms

1. **`CLAUDE.md` (141 lines):**
   - Line 3 imports `@.claude/rules/cloud-platforms.md`.
   - Lines 21–26 enforce Precedence (`OR-22`..`OR-26`, `OR-34`, `OR-35`): explicit creator instruction in thread (`cmsg_*`) -> `CLAUDE.md` -> `docs/EPISODE_FIRST.md` -> `docs/ORCHESTRATION.md` -> `docs/SOURCED_RULES.md` -> `docs/EPISODE_STANDARDS.md` -> `docs/VIDEO_LANE.md`.
   - Lines 37–64 define the 12 binding Invariants (no silent fallbacks, no deleting retired code/rules, no paid run without gates, `episode_timing` authoritative clock, `no_names` in prompts).
   - Lines 134–138 lock `config/model_routing.json` (`D-84`, `OR-29`).
2. **`config/model_routing.json` (455 lines):**
   - Defines 4 model families (`haiku` = `claude-haiku-5-5`, `sonnet` = `claude-sonnet-5-5`, `opus` = `claude-opus-5-5`, `fable` = `claude-fable-5-1`).
   - Enforces `"code": {"effort_ceiling": "high", "never_models": ["fable"]}` (blocked by `hooks.pre_write` if effort is `xhigh` or `max` on `*.py`).
   - Lines 253–261 define `"multi-agent-analysis"`: `{"level": "S4", "models": [], "efforts": [], "effort_text": "ultracode", "guard": "only on the creator's word (part 5)", "how": "workflow"}`.
   - Lines 268–280 lock `"critics": {"names": ["script-critic", "lora-checkpoint-judge"], "model": "opus", "effort": "high", "tools": ["Read", "Grep", "Glob"]}` and `"spawners": ["orchestrator", "lora-coordinator"]`.
   - Lines 384–392 lock `"protected_files"`: `config/spend_caps.json`, `config/model_routing.json`, `config/channel_voices.json`, `assets/audio/generator_admission.json`, `explainer_engine/cloud/cheapest.py`, `explainer_engine/cloud/cheapest.json`, `explainer_engine/training/pods/ltx/launch.json` (modifiable only within a 60-minute window after `python -m explainer_engine.governance ok protected_config <cmsg_id> "<creator words>"`).
3. **`config/spend_caps.json` (115 lines):**
   - `per_episode`: `runpod_usd: 31.0`, `gemini_usd: 10.0`, `bfl_usd: 3.0`, `fal_usd: 9.0`.
   - `allowances.qa_loop`: `elevenlabs_credits: 2000`; `paid_tests.total_usd: 5.9`; `runpod`: `per_pod_usd: 10.0`, `per_24h_usd: 26.0`, `max_hours_per_pod: 5.0`.
   - `modal_bakeoff` (`per_run_usd: 2.5`), `modal_ltx` (`per_run_usd: 1.5`), `modal_cheap_video` (`per_run_usd: 1.2`). General `modal` and `hyperstack` episode lines are unset (`$0` hard-blocked).
4. **`.claude/settings.json` (101 lines) & Hook Handlers:**
   - `PreToolUse`:
     - `Bash` -> `explainer_engine.cloud.hooks` (`pre_bash`: enforces RunPod/Modal `paid_offer/1` `CH-01..CH-07`, `EE_MODAL_GO`, picture refusal) and `explainer_engine.governance.hooks pre-bash` (blocks `git push --force` / `git branch -D` without a `backup/*` tag on the target tip, and blocks shell redirections to `protected_files`).
     - `Write|Edit|MultiEdit|NotebookEdit` -> `explainer_engine.governance.hooks pre-write` (blocks top-level `engine/`, `protected_files` without fresh creator `ok`, and `*.py` edits at `xhigh`/`max` effort).
     - `Agent|Task` -> `explainer_engine.governance.hooks pre-agent` (blocks `fable` outside story stages and enforces `opus` on critics).
     - `mcp__ElevenLabs__.*` -> `explainer_engine.standards.hook` (blocks picture/video generation over MCP, requires `generations_count == 1`, `paid_assets` gate, `script_approval`, `editorial_gate`, and prior voice library lookup).
   - `PostToolUse` (`Write|Edit|MultiEdit` -> `post-edit` running `py_compile`, JSON parse, and `docs_lint`), `PreModelSwitch`, `PostModelSwitch`, `UserPromptSubmit`, `SessionStart`, `Stop`, `StopFailure`, and `statusLine`.
   - **Important Security Observation:** `explainer_engine/governance/hooks.py` L22 states: *"Every hook fails open: an exception prints one line and exits 0; only a matched rule exits 2."* This confirms hooks are deterministic policy lints, **not** a security sandbox against adversarial third-party code.
5. **`.claude/agents/` (16 active files + `docs/agents_pending/youtube-viewer-critic.md`) & `.claude/skills/` (21 files):**
   - Locked by `tests/unit/test_agent_roles.py` (`set(CFG["agents"]) == set(NAMES)`) and `tests/unit/test_agent_governance.py` (every non-main, non-critic file must start `description:` with `"Stage page (OR-20, D-79)"`, only `orchestrator` and `lora-coordinator` may declare `Agent`/`Task` in `tools`, and every referenced module/path/skill/hook must exist on disk).
   - `tests/unit/test_t3_agent_skill_banners.py` enforces `T3-3` (`CP-07`, `CP-08`, `CP-13`): retired material (`animated-universe`, `lora-training`, `lora-*` agents) is banded in place with `## History (retired by D-80)` / `#### History (retired 2026-10-22)` and never deleted.

---

## 4. Workstream B — Official Claude Code Architecture Audit

Audited against official Claude Code documentation:
- Skills: [`https://code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills)
- Subagents: [`https://code.claude.com/docs/en/sub-agents`](https://code.claude.com/docs/en/sub-agents)
- Hooks: [`https://code.claude.com/docs/en/hooks`](https://code.claude.com/docs/en/hooks) and [`https://code.claude.com/docs/en/hooks-guide`](https://code.claude.com/docs/en/hooks-guide)
- Plugins & Security: [`https://code.claude.com/docs/en/plugins/overview`](https://code.claude.com/docs/en/plugins/overview), [`https://code.claude.com/docs/en/plugins/manifest-reference`](https://code.claude.com/docs/en/plugins/manifest-reference), [`https://code.claude.com/docs/en/plugins/components`](https://code.claude.com/docs/en/plugins/components), [`https://code.claude.com/docs/en/plugins/install`](https://code.claude.com/docs/en/plugins/install), [`https://code.claude.com/docs/en/plugins/security`](https://code.claude.com/docs/en/plugins/security), [`https://code.claude.com/docs/en/plugins/mods/overview`](https://code.claude.com/docs/en/plugins/mods/overview)

| Official Claude Code Mechanism | Verified Official Behavior & Version Requirements | Draft Proposal Status | Audit Verdict & Correction |
|---|---|---|---|
| **Skill Discovery & Frontmatter** | `.claude/skills/<name>/SKILL.md`; supports `name`, `description`, `argument-hint`, `disable-model-invocation`, `user-invocable`, `allowed-tools`, `model`, `effort`, `context` (`fork`), `agent`, `hooks`, `paths`, `shell`. Reserved names: `synced` and `anthropic-skills`. Worktree root fallback added in `v2.1.277+`; `/cd` loading in `v2.1.246+`; `/add-dir` in `v2.1.257+` / `v2.1.309+`. | Covered core fields (`L12`), omitted reserved names (`synced`, `anthropic-skills`) and full field list. | **`PARTIAL` -> Fixed in Sec. 1 & 3** |
| **Dynamic Context Injection** | `` !`<command>` `` executes shell commands before the skill prompt is sent to Claude ([`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills)). | Correctly cited (`L12`), but did not note that `` !`cmd` `` inside an external skill executes shell commands on activation! | **`PARTIAL` -> Added to `SP-1`/`SP-2` security audit** |
| **Subagent Context & Token Ceiling** | `.claude/agents/<name>.md`; combined custom subagent `description` text > `15,000` tokens triggers a startup warning. Supports `omitClaudeMd: true` (`v2.1.271+`), `autoCompactWindow` (`100000..1000000`, `v2.1.296+`), `maxTurns` (`v2.1.246+`). | Correctly cited `15,000`-token ceiling (`L68`, `L268`) and `omitClaudeMd: true` (`L73`, `L85`). | **`PASS`** |
| **Plugin Subagent Restrictions** | Per [`code.claude.com/docs/en/sub-agents`](https://code.claude.com/docs/en/sub-agents), `hooks`, `mcpServers`, and `permissionMode` frontmatter fields are **ignored** on plugin-shipped subagents for security. | Correctly cited (`L64`, `L282`). | **`PASS`** |
| **Plugin Execution Surfaces (`bin/`, `monitors`, `mods`)** | Per [`code.claude.com/docs/en/plugins/security`](https://code.claude.com/docs/en/plugins/security), plugins can execute code via **5 surfaces**: `hooks/hooks.json`, `monitors` (auto-started background shell commands), `mods` (in-process JS with full user permissions), `mcpServers`, and `bin/` (prepended to `Bash` `PATH`). | Draft only mentioned `hooks` and `mcpServers` (`L281`); completely missed `bin/` PATH injection, `monitors`, and `mods`. | **`FAIL` -> Fixed in Sec. 4.1, 7.2.B, 8.1 (`VP-5`), and 9.1 (`SP-5`)** |
| **Plugin MCP Scoped Tool Naming** | Plugin-bundled MCP tools are named `mcp__plugin_<plugin-name>_<server-name>__<tool>` ([`code.claude.com/docs/en/hooks`](https://code.claude.com/docs/en/hooks)). A `PreToolUse` matcher written only as `mcp__<server>__.*` **will not match** a plugin-bundled MCP server. | Mentioned pattern on `L98` & `L281`, but did not enforce dual matcher registration in `SP-3`/`VP-3`. | **`PARTIAL` -> Fixed in Sec. 3, 7.2.C, 8.1, 9.1** |
| **Local vs. Cloud Session Differences** | Per [`code.claude.com/docs/en/plugins/install`](https://code.claude.com/docs/en/plugins/install) and [`code.claude.com/docs/en/skills`](https://code.claude.com/docs/en/skills), cloud sessions do **not** load plugins configured in `.claude/settings.json` or user `~/.claude/skills/`. Only project-committed `.claude/skills/` and `.claude/agents/` are guaranteed across both local and cloud sessions. | Mentioned as a registry field (`L216`) without architectural guidance. | **`PARTIAL` -> Fixed in Sec. 3 & 9.1** (another reason to vendor skills into `.claude/skills/` rather than relying on `.claude/settings.json` plugins) |

---

## 5. Workstream C — External Candidate Audit & Mandatory FFmpeg (`kajisho5/ffmpeg-skill`) Investigation

### 5.1 Mandatory FFmpeg Investigation (`kajisho5/ffmpeg-skill` Issues `#468`, `#469`, `#470`, `#510`, `#455`)

The audit prompt required verifying whether `kajisho5/ffmpeg-skill` `scripts/join.py` still writes `xfade` offsets in milliseconds and resolving the exact status of issues `#468`, `#469`, `#510`, and `v3.10.1` (`f1c97cb`):

1. **Exact Open Issues Verified on [`https://github.com/kajisho5/ffmpeg-skill/issues`](https://github.com/kajisho5/ffmpeg-skill/issues) (`is:issue state:open`, `31 Open` as of `v3.10.1` / `f1c97cb`):**
   - **Issue `#468` (OPEN):** `"join.py: xfade offsets are written to the millisecond, so a transition whose offset rounds up starts one frame late"`.
   - **Issue `#455` (OPEN):** `"[from Velisa] join.py: frame-exact clip lengths (millisecond lengths leave one-frame holes in long edits)"`.
   - **Issue `#462` (OPEN):** `"Audit 2026-11: cut.py, _smartcut.py, silence.py and join.py"`.
   - **Issue `#470` (OPEN):** `"Follow-ups found while fixing the audit's high findings (#469)"`.
2. **What `#469` and `#510` Actually Were:**
   - **`#469`** was the pull request that fixed the initial batch of high-severity audit findings, which in turn spawned open follow-up issue **`#470`**. In our earlier draft (`L146`, `L157`, `L312`), we misread the adjacent issue-list snippet and cited `#469` instead of **`#468`** as the `join.py` `xfade` issue number.
   - **`#510`** was committed two days ago (`"fix: the decided items of #510 (render's up-front filter check, cut -…)"` on `mcp/` and `scripts/`), addressing `render.py`'s up-front filter check and `cut.py` flags, and was released in `v3.10.0` / `v3.10.1` (`f1c97cb`). It did **not** close `#468` or `#455`.
3. **What Could Not Be Directly Verified (`NOT VERIFIED`):**
   - Because the sandbox VM has no outbound internet access (`git clone` blocked) and `google:browse` blocks `raw.githubusercontent.com` URLs not returned in search results, the raw Python source lines of `scripts/join.py` at `f1c97cb` are logged in `NOT_VERIFIED.md`. However, the maintainer's own live `is:issue state:open` tracker at `v3.10.1` (`f1c97cb`) proves that `#468` and `#455` remain **OPEN**.
4. **Architectural Conclusion for Explainer Engine (`PASS`):**
   - Explainer Engine's `episode_timing/1` and `episode_timing/2` contracts (`explainer_engine/episode/timing.py`) and `explainer_engine/production/assemble.py` (`assemble_shot_clips`) require **24fps frame-exact clock alignment** (`clock_sha256`). Using `kajisho5/ffmpeg-skill`'s `join.py` for master assembly would risk 1-frame rounding drift (`#468`) and 1-frame holes (`#455`). Therefore, keeping `assemble.py` and `tools/render_tools/{build_segments,mix}.py` as the sole production writers while adapting only `kajisho5/ffmpeg-skill`'s read-only `probe.py -> --dry-run --json -> check.py -> look.py` diagnostic patterns is **100% validated**.

### 5.2 Summary Verdicts for All 7 Candidates

| # | Candidate | Draft Disposition | Audit Verdict on Draft | Required Correction in Patch |
|---|---|---|---|---|
| 1 | [`wuwangzhang1216/DirectorSKILL`](https://github.com/wuwangzhang1216/DirectorSKILL) (`v2.0.0`, `c65ae0d`) | Adapt `F1–F19` & routing table into `shot-visuals`; strip 20 named directors per `no_names` | **`PASS` (Provenance `PARTIAL`)** | Mark 40-char SHA as `NOT_VERIFIED_40CHAR (c65ae0d)` until cloned; assign `SP-1` / `VP-1`. |
| 2 | [`RobLe3/cc-blender-skill`](https://github.com/RobLe3/cc-blender-skill) (`v1.4.0`) | Hold for legacy / free PC benchmark only; disabled in v4.3 per `retired_era.json` | **`PASS` (Registry `PARTIAL`)** | Move plugin package into new **Table 7.2.B (Plugins Registry)**; mark 40-char SHA as `NOT_VERIFIED_40CHAR (v1.4.0 tag)`; assign `SP-5` / `VP-5`. |
| 3 | `zq940222/blender-mcp-skill` | **REJECTED (`UNVERIFIED SOURCE` — HTTP 404)** | **`PASS`** | Retain rejection verbatim. |
| 4 | [`kajisho5/ffmpeg-skill`](https://github.com/kajisho5/ffmpeg-skill) (`v3.10.1`, `f1c97cb`) | Adapt read-only `probe`/`check`/`look` patterns; keep master 24fps assembly in `assemble.py` | **`PARTIAL` (Wrong Issue #)** | Correct issue citation from `#469` to open issues **`#468`** (`xfade` millisecond rounding), **`#455`** (millisecond clip-length holes), and **`#462`**; mark raw `scripts/join.py` body & 40-char SHA in `NOT_VERIFIED.md`. |
| 5 | [`anthropics/claude-plugins-official`](https://github.com/anthropics/claude-plugins-official) (`b5b01ac`) | Adopt as canonical Plugin & Skill authoring reference | **`PASS` (Registry `PARTIAL`)** | Record in new **Table 7.2.B (Plugins & Marketplaces Registry)** with `SP-5` / `VP-5`. |
| 6 | [`vercel-labs/skills`](https://github.com/vercel-labs/skills) (`v1.5.25+`) | Adopt `skills-lock.json` v2 `computedHash` in Python stdlib without Node.js | **`PARTIAL` (Scope Over-Generalization)** | Restrict `computedHash` strictly to unpacked Skill folders (`kind == "skill"`) in Section 7.1. |
| 7 | [`agentskills.io/specification`](https://agentskills.io/specification) | Baseline open standard for `.claude/skills/*/SKILL.md` | **`PASS`** | Retain verbatim. |

---

## 6. Architecture Correction Table (`CURRENT → NEW → KEEP → CHANGE → REMOVE → TRADE-OFFS → RECOMMENDATION`)

| Architectural Area | `CURRENT` (In Repo @ `eb80e443`) | `NEW` (In Draft `DEC-2026-11-17-02`) | `KEEP` | `CHANGE` (In Corrected Patch) | `REMOVE` | `TRADE-OFFS` | `RECOMMENDATION` |
|---|---|---|---|---|---|---|---|
| **1. Provenance & Baseline Tracking** | Local `eb80e443` over local `3b275a31` (unpacked from `a060cf0b` zip) | Wrote `Baseline @ eb80e443 / a060cf0b` as if identical | Local `eb80e443` P1.2 code & tests | Explicitly document the 3-tier relationship (`eb80e443` -> `3b275a31` -> upstream `a060cf0b` / `fc35615e`) in Sec. 2.0 | Ambiguous `eb80e443 / a060cf0b` shorthand | Slightly longer baseline note, but zero git-archaeology confusion | **Apply Correction (Sec. 2.0)** |
| **2. Subagent vs. Stage-Page Topology** | 16 `.claude/agents/*.md` locked by `model_routing.json` (`2` spawners, `2` critics, `12` stage pages) + `1` pending critic | Rejected 14 new subagents in table, but L73 & L85 hinted at optional new subagents | All 16 active files + pending `youtube-viewer-critic.md` + `test_agent_roles.py` lock | Cite `multi-agent-analysis` (`"only on the creator's word (part 5)"`) and make all 14 dispositions strictly use existing stage pages/critics or on-demand Skills | Parenthetical proposals for new `historical-researcher` / `skill-researcher` subagents | Prevents context bloat (`15,000`-token limit) and preserves `test_agent_roles.py` | **Apply Correction (Sec. 3.1)** |
| **3. Central Registry Structure** | No unified registry doc | Promised 4 tables (`L201`) but only rendered 2 tables (`L225–248`), omitting Plugins | Tabular Markdown registry in architecture doc | Provide all **4 distinct linked tables** (`7.2.A` Skills, `7.2.B` Plugins, `7.2.C` MCP Servers, `7.2.D` Executable Tools) | Merged 2-table layout | Clear 1:1 mapping per component kind | **Apply Correction (Sec. 7.2.A–D)** |
| **4. Provenance & Integrity Hashing** | Git tree hashes + `clock_sha256` | Applied `skills-lock.json` v2 `computedHash` to all component types and used 7-char SHAs | `computedHash` for unpacked Skill folders (`kind == "skill"`) | Define 6 component-specific provenance fields (`source_git_sha_40`, `release_tag_or_version`, `skill_folder_computed_hash`, `package_archive_sha256`, `binary_or_image_digest`, `first_party_repo_revision`) | Universal `computedHash` claim for MCPs/binaries & unflagged 7-char SHAs | Requires recording `NOT_VERIFIED_40CHAR` until `git clone` runs on an internet-connected host | **Apply Correction (Sec. 7.1)** |
| **5. Security Model & Plugin Surfaces** | `.claude/settings.json` hooks (`fail-open` on internal exceptions) + `cheapest.py` worker preflight | Relied on `PreToolUse` hooks as primary security boundary; missed `bin/`, `monitors`, `mods` | Dual-key cloud gates (`cloud.hooks` + `cheapest.py`) & `standards.hook` | Introduce **6 Security Profiles (`SP-1..SP-6`)**, ban unreviewed plugin `bin/`, `monitors`, and `mods`, and require dual `mcp__<server>__.*` + `mcp__plugin_<plugin>_<server>__.*` matchers | Hook-as-sandbox assumption | Higher bar for full plugins (`SP-5`), strongly favoring vendored `SP-1`/`SP-2` Skills | **Apply Correction (Sec. 9.1)** |
| **6. Validation & Argon Guardrails** | `pytest` unit suite + `docs_lint` + `palette` | Flat 7-point validation list requiring 20-prompt `evals.json` for every skill | `$0.00` local deterministic test requirement | Replace flat list with **6 Risk-Based Validation Profiles (`VP-1..VP-6`)** + **6 Argon Operational Guardrails (`AG-01..AG-06`)** requiring contact-sheet eye checks for media changes | One-size-fits-all validation checklist | Aligns test effort with actual failure risk and prevents Argon's historical regressions | **Apply Correction (Sec. 8.1 & 8.2)** |
| **7. Phase 1 `P1.3` Separation** | `P1.3` (`Read-only Production State and dependency snapshot`) is next in Master Plan | Kept `P1.3` separate | Strict separation between `DEC-2026-11-17-02` and `P1.3` | None (already clean) | None | Preserves Phase 1 critical path | **Keep Unchanged** |
