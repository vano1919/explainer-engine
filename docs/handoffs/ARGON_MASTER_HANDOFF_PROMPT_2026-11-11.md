# Argon Master Handoff — Explainer Engine Evidence-First Audit

**Date:** 2026-11-11  
**Purpose:** Review and reconcile the current Explainer Engine architecture, then produce a minimal, evidence-backed implementation plan for Codex.  
**Execution mode:** Planning and audit only. This prompt does not authorize code changes, production runs, model calls, uploads of episode assets, or paid compute.

---

## 1. Your role and boundaries

Act as the principal systems architect and independent reviewer for Explainer Engine. Your job is to establish what is actually current, what is only documented, what is implemented, what is tested, and what is obsolete. Do not begin by rewriting the project or restoring historical modules.

For this task:

- Inspect the attached `Explainer_Engine_V4_Main.zip` and the specified GitHub branch. Record exact archive names, repository/ref, commit when discoverable, file paths, and SHA-256 hashes for the principal source files.
- Treat the uploaded archive as a candidate working snapshot, not automatically as the canonical repository. It contains multiple nested bundles and explicitly deprecated material. Identify the newest coherent source set before relying on it.
- Treat the GitHub branch and the uploaded archive as separate snapshots until you prove they match. Report all material differences.
- Do not reveal, copy, print, or upload API keys, `.env` files, vault secrets, tokens, or other credentials. Do not upload model weights, generated video, reference images, or large episode assets as part of this planning task.
- Do not write application code or edit Python, JSON schemas, configuration, workflows, notebooks, production scripts, or model files. You may add planning documents on a dedicated handoff branch only.
- Do not start Gemini, ElevenLabs, Wan, Modal, RunPod, or other paid requests. Do not launch any inference job. A key being present does not prove an action is free or authorized.
- Do not claim a command, validator, API, or workflow ran unless you actually ran it and can show its output.

The deliverable is a precise, file-by-file plan for Codex. Codex implements only after the plan is reviewed and approved.

## 2. Evidence and precedence

Use this order when sources conflict:

1. Platform, security, legal and safety constraints.
2. The creator's explicit latest instruction.
3. The latest active decision in `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (including amendments and supersession notes).
4. Canonical schemas and machine-readable registries, including `explainer_engine/standards/sourced_rules.json` and the 12 component rule registries.
5. Executable implementation and its actual call sites.
6. Tests and recorded test/CI results.
7. Active specifications and architecture documents.
8. Historical documents, archived prompts, examples, and recommendations.

A document saying that a validator runs is not proof that it is called. A function name, registry row, planned EDL field, status flag, or coverage string is not proof that the behaviour is executed. Verify call paths and outputs.

When evidence is missing, use one of these labels: `VERIFIED`, `PARTIALLY VERIFIED`, `DOCUMENTED ONLY`, `NOT IMPLEMENTED`, `NOT TESTED`, `CONFLICT`, or `UNKNOWN`. Never turn an unknown into a fact.

## 3. First task — establish the real project snapshot

Inspect the archive before changing or recommending anything.

1. List all top-level files, nested ZIP files, deprecated folders, notebooks, scripts, sample scripts, manifests, reports, and test assets. Identify files that contain secrets by filename/pattern only; do not read or display secret values.
2. Compare at minimum:
   - `explainer_engine_v4_2_hybrid_gemini_wan_complete.zip`
   - `explainer_engine_v4_2_cohesive_film_and_rules_bundle.zip`
   - `youtube_docudrama_12_component_3tier_rules_registry.zip`
   - the D-124 clean/Gemini architecture bundles
   - every bundle explicitly marked `OBSOLETE`, `DEPRECATED`, or `PRE-D127`.
3. Identify the newest coherent source tree and any overlay files that must be applied to it. Do not union directories blindly: inspect version history, file hashes, schemas, and tests.
4. Inspect GitHub `vano1919/explainer-engine`, especially `gemini/storytelling-system-rebuild-2026-11-09`. Record its current head and compare its docs/code with the archive. The archive already contains D-123 through D-127; do not assume GitHub has those changes.
5. Produce a snapshot report with the exact baseline you recommend using. If no single coherent baseline exists, say so and show the smallest reconciliation needed.

## 4. Second task — build a rule traceability matrix (do not restore rules blindly)

The old BP/KP/ST/SC/SD/AL/DL/UR/PV rules are not automatically active just because they exist in an old file. D-126 introduced three governance tiers, but tier and lifecycle status are separate concepts.

For every rule ID found in the canonical source, assign:

**Lifecycle status** (one):
- `ACTIVE`
- `CONDITIONAL` (active only for a specific route, shot, schema, episode type, or context)
- `SUPERSEDED`
- `RETIRED`
- `HYPOTHESIS`
- `UNIMPLEMENTED`
- `UNTESTED`

**Governance tier** (only for active/conditional rules):
- `TIER_1_INVARIANT`: hard failure when its applicability conditions are met.
- `TIER_2_STORY_BOUNDED`: a range or distribution guardrail; the screenplay determines the value inside the approved bounds.
- `TIER_3_ADVISORY`: contextual recommendation or `REVIEW`, never a hard failure by default.

Create a traceability table with these columns:

`rule_id | canonical_source | lifecycle_status | tier | applicability/scope | implementation_symbol | actual_call_path | test_file/test_case | evidence | gap | recommended_action`.

Rules without a code check must be marked `DOCUMENTED ONLY` or `UNIMPLEMENTED`; do not pretend the catalog itself enforces them. Tests without an assertion for the rule do not count as coverage.

For every active Tier 1 rule and every enforced Tier 2 bound, require at least one passing fixture and one failing fixture. Conditional rules need positive/negative tests for both applicable and non-applicable contexts. Tier 3 rules should produce a documented advisory finding, not an automatic blocker.

Do not remove `return` statements, schema branches, compatibility adapters, or legacy modules merely because they appear to bypass a linter. First prove whether the branch is a defect, an intentional schema-version dispatch, or a retired route. Prefer a narrow adapter only when a rule is still active and its semantics can be represented correctly in the new schema. No blanket shims and no false-positive compatibility layer.

## 5. Third task — reconcile the current decisions and pipeline

Start with D-123 through D-127 and trace every claim to current code and tests.

The current archive indicates this direction, subject to reconciliation and verification:

- Canonical episode target: approximately 12 minutes, 24 fps, five phases `Z1–Z5`, sixteen segments `S01–S16`.
- D-124 amends D-123: Gemini Native Image Engine is the intended image/keyframe generator; Qwen is retired from active production; the workflow has creator approval gates `G0–G8`.
- G5 produces unique still assets/keyframes; G7 separates the 10%/30% visual work from the 60% Wan 2.2 video work; G8 assembles reviewable approximately 3-minute chunks.
- D-125 makes the screenplay authoritative and changes the visual/speech ratios to flexible episode-level guardrails. It also adds anti-metronome pacing and repeated-pattern restrictions. `frame[-5]` is for a single continuous video shot longer than five seconds, not a generic rule for every shot.
- D-126 separates Tier 1 invariants, Tier 2 story-bounded limits, and Tier 3 advice across text, audio, video, and editing cohesion.
- D-127 describes a resumable batch image worker with a durable generation ledger and transient-error retry. Its model choice must be revalidated against current provider documentation before any implementation or use.

Do not assume all of these are mutually consistent. In particular, resolve and report:

1. D-123 says local/free-by-default, while D-124's G5 image generation uses Gemini API and G7 specifies Wan on Modal GPU. Identify which work is local, which is paid/hosted, the opt-in boundary, and the creator approval required. Do not silently choose one interpretation.
2. D-123's original 60/30/10 and 70/30 speech targets are amended by D-125's wider ranges. Identify which ranges remain canonical and which documents/config/schema still carry older values.
3. D-125's shot-duration and pacing bounds must match the code. Do not allow code, decision log and docs to carry different thresholds.
4. D-126's catalog must match actual enforcement. Check whether all listed invariants are actually run, and whether applicability conditions are represented correctly (for example, a screen-axis requirement should not automatically be applied to an unrelated map/insert shot without a reason).
5. D-126's visual mix must be measured on a meaningful basis. Determine whether it is computed by shot count or by actual timeline duration. Do not call a shot-count ratio a runtime ratio.
6. The EDL and generation plans are plans, not evidence of rendered output. Separate planned cues/flags from media-level verification.
7. Reconcile `GEMINI.md`, `docs/YOUTUBE_MASTER_MANUAL_ARGON_VS_FLASH.md`, and `docs/architecture/GEMINI_STORYTELLING_SYSTEM_REBUILD_2026-11-09.md`. They appear to describe different Gemini roles and workflow generations. Do not merge incompatible instructions into one prompt.

Keep the smallest working parts of the current system. Recommend changes only where evidence demonstrates a defect, drift, dead endpoint, untested invariant, or materially better simpler architecture.

## 6. Fourth task — verify provider and SDK assumptions

Before accepting any provider, model ID, parameter, quota, price, SDK method, workflow node, or endpoint:

- Verify it against current official provider documentation and the version used by the repository.
- Record exact model ID, SDK/package version, method signature, supported inputs/outputs, availability, quota scope, pricing, deprecation state, and date checked.
- Distinguish an API model from a UI product/model label and from a community checkpoint or workflow node.
- If a model is shut down or renamed, mark the route `BLOCKED/OBSOLETE`; do not substitute a guessed replacement. Recommend a documented candidate and require a small, approved benchmark before promotion.
- Quotas are project/model/tier dependent. Do not hardcode an account-wide RPM figure or promise that a queue can prevent every 429. Implement rate limiting and backoff from the actual quota data, with idempotent resume and a hard spend cap.

The previous prompt's Veo 3.1 and Imagen 3 assumptions must be treated as stale pending official verification. Do not build around them.

## 7. Fifth task — design an independent YouTube viewer-review agent

Add a proposal for a new agent named `youtube_viewer_critic` (name can be refined). It must be a clean-room audience review, not another technical validator.

### Context isolation

Run it in a fresh session/context. Give it only a sanitized `viewer_review_packet` containing:

- title and thumbnail concept, only if they exist;
- one-sentence video promise/logline;
- intended audience and approximate runtime;
- short premise/what-if setup;
- the complete readable script, divided into stable segment/line IDs and approximate timestamps.

Do **not** give it the repository, architecture, schema, source registry, production prompts, validators, linter results, previous model feedback, author explanations, implementation plan, or technical production constraints. Do not let it read the writer's hidden chain-of-thought or internal notes. Its blind spot is intentional: evaluate what a first-time viewer can understand from the material they receive.

### Reviewer role and limits

The agent is a skeptical first-time YouTube viewer/editor. It evaluates only audience experience and story quality:

- immediate curiosity and clarity of the promise;
- whether the opening makes a compelling question, paradox, or high-stakes situation understandable;
- stakes, human agency, conflict, cause and effect;
- escalation, reversals, discoveries, uncertainty, and open loops;
- pace, repetition, cognitive load, and changes in energy;
- emotional progression and character investment;
- whether setups are paid off and whether the ending feels earned;
- title/thumbnail promise alignment, only when supplied.

It must not grade code, schemas, shot prompts, camera moves, render feasibility, sound engineering, API choices, historical-source accuracy, or compliance. Those remain separate review lanes. It must not reward random action, noise, fake urgency, or misleading clickbait merely because they appear exciting.

### Required output

1. **Cold-viewer verdict:** Would a plausible target viewer keep watching after the opening? Why?
2. **Promise test:** What does the viewer think this video will deliver, and does the script keep that promise?
3. **Viewer-reaction timeline:** For each segment or approximately 30–45 seconds, label likely response (`curious`, `clear`, `confused`, `tense`, `bored`, `emotionally invested`, etc.) and cite exact line/segment IDs.
4. **Story scorecard:** Rate premise, clarity, stakes, causality, conflict/agency, escalation, pacing/variation, emotional investment, payoff, and ending on a 1–5 scale. Every score needs evidence; `insufficient evidence` is valid.
5. **Drop-off risks:** The five most likely points where attention weakens, with exact evidence and the smallest useful fix.
6. **One highest-impact revision:** State the single change most likely to improve the viewing experience. Do not rewrite the entire script.
7. **Confidence and blind spots:** State what could not be judged from the supplied packet.

This is a subjective editorial estimate, not a prediction of CTR, retention, watch time, or virality. Do not invent performance percentages. Do not output a technical PASS/FAIL. The report is advisory `REVIEW` only until calibrated against human reviews and actual channel analytics. Do not average its scores into the technical QA scorecard.

Keep the current `script-critic` and deterministic validators. The new viewer critic complements them; it does not replace them. Recommend a single G2 audience-review step before script lock, then at most one targeted re-review after revisions unless evidence justifies more.

Also inspect `explainer_engine/llm/gemini_api.py`: if `complete()` remains a deliberate refusal/stub, do not claim the agent already runs. Specify the smallest API/client, budget-ledger, privacy, schema, and test work needed to invoke it safely. No request is made in this task.

## 8. Required deliverables

Produce these planning artifacts:

1. `ARCHITECTURE_RECONCILIATION_AUDIT_2026-11-11.md` — snapshot identity, source-of-truth decision, branch/archive differences, rule traceability findings, implementation-vs-documentation gaps, model/API deprecations, test evidence, unresolved conflicts, and keep/change/retire recommendations.
2. `ARGON_MASTER_HANDOFF_PROMPT_2026-11-11.md` — this instruction, refined after the audit.
3. A file-by-file Codex implementation plan with priority, rationale, expected diff, tests, acceptance criteria, rollback risk, and dependencies.
4. A short list of creator decisions that truly cannot be resolved from available evidence. Do not ask questions for routine implementation details.

## 9. Acceptance criteria

The task is complete only when:

- The exact baseline archive/ref is identified and the GitHub/archive mismatch is explicit.
- Every active rule is mapped to its actual enforcement path and test, or clearly marked as a gap.
- Superseded/retired/conditional rules are not reactivated accidentally.
- Documentation, code and tests agree on the current D-125/D-126 boundaries, or the remaining mismatch is documented as a blocking issue.
- No dead model ID or unsupported API claim remains in the proposed production path.
- The local/free versus hosted/paid boundary is explicit and no paid job is launched.
- The audience critic is context-isolated, audience-only, evidence-citing, advisory, and separate from technical QA.
- The plan preserves existing working modules and proposes the smallest justified changes.
- No application code, production asset, credential, branch history, or main branch is changed by this planning task.

Start with the repository/archive inventory. Do not start by editing the old `v4.1` prompt or by deleting early returns.