# V4.1 files (2026-11-19): where everything is

One folder for the V4.1 plan, Gemini's deliverables and the plan owner's reviews. Nothing here changes code. Copies, byte for
byte, of the files on HF (`vano1919/tmr-artifacts`, `explainer-engine/v4_1_plan_2026-11-19/` and `.../v4_1_review_2026-11-19/`)
and in the Drive folder `Explainer_Engine_V4_Main`.

| Folder | What | Author |
|---|---|---|
| `gemini_blueprint/` | Gemini's V4.1 blueprint package v2 (7 documents, Drive Google Docs exported to Markdown) | Gemini |
| `gemini_g2/` | G2: the schemas (22 `$defs`), fixtures, the missing specifications, manifest v2 | Gemini |
| `gemini_g1/` | G1: the task, round 1 (failed, clips not decodable), round 2 observation (JSON and raw answer), the sha256 of the six clips, and the plan owner's comparison with the measured audio | Gemini, comparison by Claude |
| `claude_review/` | The independent review of the package (MA-01..MA-18, C-01..C-12), its evidence text, the review of PRs #197-#205 | Claude (plan owner) |
| `plan/` | The full plan in Georgian (steps 0-8), the message for Gemini, the handoff to the implementation thread, the render parity matrix (1.5) | Claude |

**Not copied here (already on git, on the implementation branches, PR #197 `claude/project-thread-f0oep6`):**
`docs/architecture/V4_1_ACTION_PLAN_STEP0_STEP1_2026-11-19.md` (the final plan), `V4_1_GEMINI_PLAN_REVIEW_2026-11-19.md`
(Gemini Neon's review of the plan), `V4_1_PLAN_AMENDMENTS_V1_1_2026-11-19.md`. The slice allowlist is
`docs/architecture/v4_1_allowlists.json` on `claude/project-thread-f0oep6-s04b` (PR #198).

**Not on git (binary, on HF and Drive only):** `V4_1_G2_CONTRACTS_e4521cd.zip`, `p1_2_patches.zip` (Gemini's 7 patches),
the two contact sheets `sheet_S03_SH007.png`, `sheet_S04_SH014.png`, the six 1914 raw clips and their start pictures.

Gemini's P1.2 code snapshot (`eb80e443`, head `0592114`) lives in this branch's history as the mirror commit `e4521cd`
(PR #196).
