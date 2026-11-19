# Handoff: V4.1 Step 0 / Step 1 code (state 2026-11-19 ~16:00 Georgia)

All $0. All PRs draft, stacked, nothing merged. Branch prefix `claude/project-thread-f0oep6`.

| Slice | PR | Branch | State |
|---|---|---|---|
| 0.3 decision D-139 + field contract | #197 | (base) | CI green |
| 0.4a protected_files | #199 | -s04a | CI green |
| 0.4b scope check + allowlists | #198 | -s04b | CI green |
| 1.1 fail-closed picture check | #200 | -s11 | CI green |
| 1.4 third-party media (PC-10, YOUTUBE_CLAIM_RISK) | #201 | -s14 | CI green after the ICW wording fix |
| 1.2 one trim rule (voicing check) | #202 | -s12 | CI green |
| 1.3 start_frame_check, route_proposals, unresolved_reviews | #203 | -s13 | allowlist lines in #198, merged forward; re-check CI |
| 1.5 one render path (mix.py preview only, G8 mute_tail_from_s, exact frames, DIPS documented, MAC_RUNBOOK) | #204 | -s15 | allowlist lines in #198, merged forward; re-check CI |
| 0.4c plan-thread approvals in governance | #205 | -s04c | code + config keys done |

## Creator's word (done)
ვანო's own word cmsg_01Hnu5zB86sjUj5GtTgaUkPWQpbVcQvfsDtADSnt5amj19 ("გაძლევ ყვეაბაირ იფლებას ყველა ფაილზე რაც ჩამოთვალე") is recorded for `config/model_routing.json` and `docs/architecture/v4_1_allowlists.json`. #198 now holds the 1.5 additions and slice 0.4c; #205 holds `plan_thread_delegation` / `plan_thread_approvable`. All branches merged forward; CI re-running (scope checks should go green).

## Not done
- 1.5 audio-only parity (G8 LUFS/true peak/take log vs Mac mix 2f17837b; the Mac mix plays synthesized beds since 0e299cd, so takes differ, compare loudness). Library and inputs are downloaded in `/tmp/claude-0/par/hf` (may be gone). Video parity: NOT_RUN, belongs with plan 3.2.
- 1.2 six-clip expectations (PROPOSED, from Gemini G1 round 2 in `gemini_G1_2026-11-19/`): no speech in S03_SH007, S04_SH014, S07_SH005, S07_SH006; S06_SH008 three lines with measured spans 0.00-0.63, 1.64-2.15, 2.99-3.66; S03_SH003 sung German. Edges from measured voiced spans only. Test marked PROPOSED until the creator's listen.
- Creator listens: S06_SH008 which "Maybe", S03_SH007 (before 1.2 merges); every replacement sound take (before 1.4 merges).
- Drive mirror (Explainer_Engine_V4_Main) of the code and reports; HF marker DO_NOT_MONETISE_CONTAINS_BBC_REMARC.txt on render/pass1; update PR bodies #198/#201 (allowlist note, YOUTUBE_CLAIM_RISK wording), list plan-thread approvals in each PR body.
- Name the 4 extra skipped tests of PR #196 via a -rs CI run (PROGRESS entry).
- Compare field contract with Gemini's G2 `$defs` (`gemini_G2_2026-11-19/v4_1_schemas.json`).

Entry points: `docs/PROGRESS.md` last entries; `docs/architecture/v4_1_allowlists.json`; `RENDER_PARITY_MATRIX_1_5.md`.
