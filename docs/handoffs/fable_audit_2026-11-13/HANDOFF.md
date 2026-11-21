# Handoff: Fable audit of the AV and video-lane reports (2026-11-13)

## What was done
- Both reports (AV, PR #174; video lane, PR #175), both sound guides and the Gemini picture line were checked against the code
  of their branches. The Toba script was run through G1 and the video-lane plan. The branches were merged in a local scratch
  tree and the full suite was run on it.
- Read-only. No code change, nothing paid, nothing merged. Only this folder was pushed.

## Result in five lines
1. The reports' main claims hold. The two lines merge; six conflicts, all mechanical.
2. The Toba episode cannot run today: FA-01 (G1 measures LTX shots against Wan), FA-02 (LTX never receives the line), FA-03 (the
   script and the writers' room lack the new fields), FA-04 (the Gemini queue refuses `video`), FA-05 (guides against schema).
3. Silent quality faults: anchors do not follow the read (FA-06), the hand-over cuts speech (FA-07), bed / era / mood still come
   from words (FA-09), the clip sound of narrated LTX shots is dropped (FA-13).
4. Hero identity can be gated before money with tools already in the repo (FA-14).
5. Seven questions are the creator's (report section 5).

## Files (this folder)
| File | For |
|---|---|
| `FABLE_AUDIT_REPORT.md` | findings FA-01..FA-18 with evidence, proposals P1..P9, questions Q1..Q7, the PR table |
| `OPUS_WORKING_GUIDELINE.md` | the ordered work: P0 merge, P1 blocking fixes, P2 writers' room, P3 Toba script, P4 quality, P5 before paid |
| `SUMMARY_ka.md` | the short Georgian summary for the creator |

Copies: `/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12/fable_audit_2026-11-13/`.

## Entry for the next stage (one Opus high thread, rule 7a)
Read the guideline, then the report sections it cites. Branch off `origin/systemic/next-video`. Start at P0. Free work only.
Inputs: `origin/claude/project-thread-98b6wy`, `-lncsi3`, `-1hrknf`, `-eczgwr` (`-96iqtm` is not merged, guideline P0 step 6).
Merged scratch tree, measured: 4056 of 4087 tests pass; the only failures a correct merge keeps are six on FA-04. Do not edit the LTX worker or its
launch file before P5; do not touch the D-133 protected files, `config/spend_caps.json` or `config/model_routing.json`.

## Open, not blocking the start
- Q1..Q7 wait for the creator; the guideline names the default used until he answers.
- After the integration PR is merged: close the listed PRs (report section 6); #164, #120, #112 wait for Q6.
- Proven only by a paid sample: the composed LTX prompt, the voice per speaker, the clip sound under the narrator.
