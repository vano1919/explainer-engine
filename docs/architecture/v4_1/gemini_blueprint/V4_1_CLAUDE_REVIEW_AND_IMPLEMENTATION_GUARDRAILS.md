# Explainer Engine V4.1 — Claude Independent Review Prompt & Implementation Guardrails

- **Document ID:** `V4.1-DOC-05` (`V4.1-IMPL-BLUEPRINT-001`)
- **Date:** `2026-11-19`
- **Purpose:** (1) Standalone review prompt for Claude to independently `APPROVE | APPROVE_WITH_CHANGES | REJECT | NEEDS_EVIDENCE` every ADR and WP, and (2) strict execution locks for Claude Opus / Gemini Hydrogen during implementation.

---

## 1. Standalone Claude Independent Review Prompt (Copy-Paste Verbatim)

```markdown
You are acting as an Independent Principal Software & Media Systems Reviewer for `vano1919/explainer-engine`.
Your job is NOT to endorse this plan. Your job is to rigorously audit, challenge, and independently decide whether Explainer Engine V4.1 is ready for implementation.

### Mandatory Inputs to Read First
1. `V4_1_MASTER_ARCHITECTURE_AND_DECISION_BRIEF.md` (`V4.1-DOC-01`)
2. `V4_1_FILE_BY_FILE_IMPLEMENTATION_PLAN.md` (`V4.1-DOC-02`)
3. `V4_1_DATA_CONTRACTS_AND_QA_SPECIFICATION.md` (`V4.1-DOC-03`)
4. `V4_1_EXTERNAL_RESEARCH_AND_EVIDENCE_REGISTER.md` (`V4.1-DOC-04`)
5. `V4_1_CLAUDE_REVIEW_AND_IMPLEMENTATION_GUARDRAILS.md` (`V4.1-DOC-05`)
6. `V4_1_IMPLEMENTATION_MANIFEST.yaml` (`V4.1-MANIFEST-01`)
7. Live repository on `argon/p1-2-timing-contract` (`HEAD = 0592114c6c2d44a9af00b11553f169516e175864`).

### Mandatory Verification Checklist (Audit Every Item Independently)
1. Independently inspect `episode/run.py`, `episode/timing.py`, `qa/`, `videolane/`, `finish/superres.py`, `production/{understand,layers25d,directed25d}.py`, `audio/sfx_planner.py`, and `explainer_engine/blender/{polyhaven,terrain}.py` to verify all code paths and call-graph claims.
2. Verify all 5 mandatory V4.1 amendments are completely specified: (A) `AdaptiveVideoInspectionRouter`, (B) Separate rational Video/Audio clocks (`media_clocks.py`), (C) Intentional Cut-on-Action, (D) Genuine Cross-Vendor Evaluation with exact model IDs, (E) `AudioEvidenceFusion` treating 6 signals as correlated rather than independent votes.
3. Verify Creator Amendment F (`ADR-V41-11`): Hybrid 10% Helper Split (Blender 3D for historical maps/frontlines/troop movement/territorial change/3D spatial reconstruction; 2D/FFmpeg for simple text, titles, subtitles, and non-spatial charts) with narrow `D-131` carve-out gated on `WP-B1`.
4. Challenge any unnecessary new module, hidden scope expansion, or unverified threshold.
5. Verify that `WP-02` (Single-Shot Closed-Loop Proof) actually runs inside `episode/run.py` and proves all 7 mandatory negative tests without requiring a full-repo rewrite first.
6. Verify that all licenses (`LTX-2.x` `<$10M` ARR, `HunyuanVideo-Foley` EU/UK/KR exclusion, `CC0` Poly Haven/ambientCG/Smithsonian, `Sonniss GDC` no-AI-training) and split experiment budgets are accurate and realistic.
7. Verify that `V4_1_IMPLEMENTATION_MANIFEST.yaml` allowlists and stop conditions prevent Claude Opus or Gemini Hydrogen from silently drifting.

### Required Output (`V4_1_CLAUDE_INDEPENDENT_REVIEW.md`)
For EVERY ADR (`ADR-V41-01..11`) and EVERY Work Package (`WP-00..WP-10`, `WP-B1`), output an explicit verdict:
- `APPROVE`
- `APPROVE_WITH_CHANGES`
- `REJECT`
- `NEEDS_EVIDENCE`

Every `APPROVE_WITH_CHANGES`, `REJECT`, or `NEEDS_EVIDENCE` MUST include:
- Exact issue & evidence (file path / URL)
- Why the current proposal is weak
- Recommended correction
- Affected files, contracts, and WPs
- New test required

End with ONE final overall verdict:
- `APPROVED_FOR_IMPLEMENTATION`
- `APPROVED_WITH_MANDATORY_AMENDMENTS`
- `NOT_APPROVED`

Note: Creator approval remains the final authority. Do not modify repository code during this review.
```

---

## 2. Implementation Agent Guardrails (Claude Opus / Gemini Hydrogen)

### 2.1 Mandatory Pre-WP Startup Protocol
Before writing a single line of code for any WP, the implementation agent MUST:
1. Verify SHA-256 hashes of `V4.1-DOC-01..05` against `V4_1_IMPLEMENTATION_MANIFEST.yaml`.
2. Confirm `git status` is clean on the single approved implementation branch (`argon/v4-1-closed-loop`) and all prerequisite WP dependencies have passed.
3. Read the exact WP allowlist (`allowed_modify`, `allowed_create`, `forbidden_paths`) and required tests.
4. State in writing: objective, exact files to touch, required tests, acceptance criteria, and stop conditions.

### 2.2 Non-Negotiable Prohibitions (Zero Silent Scope Expansion)
Implementers MUST NOT:
- Skip, merge, or reorder WPs without Creator approval.
- Modify any file outside the active WP's `allowed_modify` / `allowed_create` list.
- Introduce LLM orchestrators, dynamic plugin registries, or alternative architectures.
- Silently modify `config/picture_route.json`, `config/spend_caps.json`, `config/model_routing.json`, or `config/retired_era.json`.
- Disable QA gates, lower acceptance criteria, mark failing active-path tests as `skip`/`xfail` to force green CI, or launch paid API/GPU jobs without explicit Creator budget approval.
- Claim completion without pasting actual `git diff --stat` and real executed `pytest` / `docs_lint` output.

### 2.3 Mandatory Stop & Escalation Conditions
Stop immediately and escalate to the Creator (do NOT improvise) if:
1. An existing schema or module conflicts with an approved V4.1 contract.
2. A required model ID/API or Modal `RetakePipeline` behaves differently from documented specs.
3. Completing a WP requires modifying a file outside its allowlist.
4. Any mandatory test or `WP-02` negative test fails after 2 debugging passes.
5. Any paid API/GPU execution is required without a signed Creator budget ceiling.

### 2.4 Required Post-WP Completion Report
Every WP PR/handoff must report: (1) WP ID & commit SHA, (2) exact modified/created file list vs. allowlist, (3) verbatim `pytest` & `docs_lint` outputs, (4) binary acceptance criteria pass/fail table, and (5) `$0.00` or exact measured USD spend.
