# H0 readiness + S3 status (pictures thread, 2026-11-13 ~16:55 UTC)

Thread: "Make pictures for Truce 1914" (Opus), branch `claude/project-thread-bf505m` on `8da40d6` (PR #180 head, script frozen).
Journal: `DEMO_JOURNAL.md` beside this file (FL-009..FL-015, MS-005..MS-007, CQ-008, CQ-009). Nothing paid ran.

## S0 (readiness)

| Item | Result |
|---|---|
| FREEZE_SHA | provisional `8ae21ec` (the code under `8da40d6`). PR #177 is not merged; it moved on to `1406ce2` (L3-green LTX worker) and PR #179 (CH-07 `cloud/paid_offer`) is stacked on it. Set the freeze again on the merged `systemic/next-video` before S4 (FL-009) |
| Baseline | see MS-005 in the journal (full suite, cloud container, Python 3.13) |
| Script | A `25636aba731607b94911060da011eab0993ac6b728793acf4b39805fe66de24c`, B `0ce9795a7290429c81ee11a2f126dad830367feed6848856da2d95cb139efbc4`; runner status G1-G3 PASS fresh, G4 PASS fresh |
| New-episode needs | the episode was built by S2's builder; no scaffold command (KN-13 changed) |
| Accounts (read-only) | RunPod: 58 stopped pods, $0.00/day, balance $7.99, nothing billing. Env has GEMINI_API_KEY, BFL_API_kay, HF_TOKEN, MODAL_TOKEN_* (values never printed). No `modal` CLI in the container; no `tools/yunet` (KN-10). No Chrome browser connected to this thread |

### Paid-path matrix (OR-33 test + cap line)

| Path | Step-by-step saving proven by | Cap line | May run |
|---|---|---|---|
| Gemini API batch (level 2) | `tests/unit/test_gemini_api_backup.py::test_submit_prices_sends_the_same_text_and_collect_writes_each_picture` | `per_episode.gemini_usd` 10.0 | yes, but only on messages the Task package writes, which refuse before T0 (FL-010) |
| BFL Klein (level 3) | `tests/unit/test_image_providers.py::test_bfl_flow_reserves_settles_and_caches` | `per_episode.bfl_usd` 3.0 | only after levels 1-2 fail, price first |
| ElevenLabs reads (S4) | the PreToolUse hook (`standards/hook.py`) + `audio/register`; S4 names its test before the card | 100k credits standing cap | S4 checks |
| LTX on Modal (S5) | `tests/unit/test_v43_ltx_jobs.py`, `test_ltx_inproc.py` | `modal_ltx.per_run_usd` 1.5, no episode line (KN-07) | not from this base: needs #177 + #179 (CH-07) |

## S3 (pictures) so far

1. **Continuity cards: done.** `episodes/ep_truce_1914/planning/continuity/` — 16 scene files (S01-S07, one per place run),
   70 cards, **0 FAIL, 0 REVIEW**, plus `*.prompts.json` (CT-14 questions) and `report.json`. Built by
   `/mnt/project-files/explainer-engine/demo_truce_1914/builder/build_continuity_cards.py` from the repo's own draft
   (`continuity.cards_from_v4`) plus the layout: costume variants (Thomas `service` → `button_cut` from S06_SH010; Friedrich
   `field` → `button_given` from S06_SH012; Harris `cap_on`, his cap comes off inside S05_SH021), props in hands, set states of
   the hand inserts, crowd counts (layout values, not story facts), landmarks, light by shot, causes of every change.
   Sheets point at the R1 portraits (`planning/gemini_task/refs/ref_<hero>_portrait.jpg`).
2. **Picture queue: built.** `episodes/ep_truce_1914/planning/gemini_task/shot_queue.json`: 9 references (R1 3 portraits +
   3 places, R2 3 full bodies), 79 pictures, 31 batches of 6, 0 prompt FAIL after SF-002.
3. **Start frames: blocked (FL-010).** The Task route refuses every batch until T0 is PASS (never recorded); Gemini Task's limit
   is used up until 2026-11-14 ~05:19 Georgia time; the API backup reads only the Task package's messages, so it waits on the
   same gate; scene pictures also need approved style anchors A-F (all `candidate`). Two cards are open for ვანო:
   CQ-008 (`cmsg_01Hnu5zB86sjUj5GtTgaUkPWHsJHengUbe4HbZ1d7i88iw`, route and time) and CQ-009
   (`cmsg_01Hnu5zB86sjUj5GtTgaUkPW7GY6Qm56ACPTod55Tz7hik`, new 1914 anchors vs the Stone-Age T0 pictures).

## Next step after his answers (route ა)

On his PC through Remote Control (folder of the A3 run): `gemini_task t0` → paste in Task mode on Flash ("4 Hydrogen") →
`t0-record` (writes `config/gemini_t0_record.json`: a creator record under config/, FL-013) → anchors (CQ-009) →
`batch <ep> 1` and `2` (R1) → his look → `approve` → R2 → scenes. Intake (`gemini_task intake`) gates every file; the contact
sheet goes to HF `explainer-engine/demo_truce_1914/pictures/` before any report.

Open for the code update: FL-011 (two era-rule checks disagree), FL-012 (no prop anchors in the queue), FL-014 (the card
draft carries Toba's light), FL-015 (the queue's prompts ignore costume variants: the missing buttons from S06_SH010 on).

## Freeze check (`git diff --name-only 8ae21ec..HEAD`, this stage's own paths)

Only `episodes/ep_truce_1914/**` (S2's script files plus S3's `planning/continuity/` and `planning/gemini_task/`) and the
demo handoff folder. No path under `explainer_engine/`, `tests/`, `config/`, `.claude/` or `docs/*.md`.
