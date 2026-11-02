# Independent Master Mold v2.1.0 Audit Prompt

The audit materials are in this repository on branch
`planning/master-mold-integration-2026-11-02`:

- Audit README and consolidated report:
  `docs/wip/ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02/README_FOR_CHATGPT.md`
- The current roadmap:
  `docs/wip/MASTER_MOLD_INTEGRATION_ROADMAP_2026-11-02.md`
- Master Mold and handoff sources:
  `docs/wip/ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02/mold_v2_1_0_and_handoff/`
- Git diffs and history:
  `docs/wip/ARGON_CHATGPT_AUDIT_BUNDLE_2026-11-02/git_patches_and_logs/`

Read `README_FOR_CHATGPT.md` first. Then independently compare the roadmap with
the repository's actual source files, not merely with the audit report. The
README's `repo_5013a55a_evidence/<path>` references map to `<path>` at repository
root, pinned to baseline commit
`5013a55aca5a17a3734150f61a5eb172abcbe3b8`. Those 134 evidence files were
compared with that commit; their content matches after normalizing Windows
CRLF versus Git LF line endings, so they are not duplicated in this directory.
The branch contains later documentation commits; distinguish those from the
pinned application-code baseline when evaluating evidence.

Verify every reconciliation in the roadmap, including Issues A–E and
NEW-01..NEW-08. In particular, inspect:

- The 11th `/3` module, `explainer_engine/production_gate.py:89`.
- Post-`voice_check`, narrator-only span polishing through
  `polish_narrator_spans_in_place`.
- `teaser_of` time advancement in `explainer_engine/scripting/film_shots.py`
  `compose()`.
- A single canonical `BP-04` `resolution_word_share` in
  `explainer_engine/qa/engagement.py`, excluding `voiced: false` lines.
- Offline synthetic versus HF Vault fixtures for the 60.0-second,
  1,440-frame test.
- `GATE-P2` pre-spend authorization versus `GATE-P3` post-render
  `sample.py approve`, and the `GATE-P4` full-episode `elevenlabs_credits`
  cap.

For each claim, report whether it is verified, contradicted, incomplete, or
unverified. Cite exact repository paths and line numbers, identify unresolved
risks, and give a clear final sign-off verdict. Do not modify the repository,
change protected configuration, run paid API/GPU operations, or treat a
documentation-lint pass as proof that implementation or end-to-end tests pass.
