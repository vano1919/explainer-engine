# v4.3 branch inventory and merge record (P0.2 / P0.3, 2026-11-12)

Plan: `/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12/PLAN_v4_3_IMPLEMENTATION.md` section 0.5.3 (the creator's answer of
2026-11-12 09:33 UTC: the new branch from `main` is a technical choice; every line's work is reviewed and the best rules carried in).
Work branch: `claude/project-thread-2hoa9u`, started from `main` 073eb25 (the session's assigned branch; it is the "brand-new branch
from main" the creator asked for, the plan's proposed name `v43/episode-first` was not pushable from this session).

Baseline before any merge (main 073eb25, Python 3.13, `pytest -q`): **2357 passed, 3 skipped, 0 failed**.

## Method

All 69 remote heads were fetched. For every head: commits ahead of `main`, commits not in the Gemini line by hash, and by patch id
(`git cherry`). The union of commits that are in neither `main` nor the Gemini line is **146** (b1uzvn excluded, see below); each
was assigned to the most advanced head that holds it.

## Table

| Line | Unique commits | What it adds | Already in the Gemini line? | Verdict | Done |
|---|---|---|---|---|---|
| `gemini/storytelling-system-rebuild-2026-11-09` | base (+412 over main) | bulk of the engine: D-116..D-129 work, J5, LTX-first dialogue, cut plan, AS/LV/HI/DL rules, Toba script | - | **keep (base)** | merged d8515c5 |
| `codex/argon-gemini-handoff-2026-11-11` | 8 | architecture reconciliation audit, viewer-critic spec, Toba metrics (docs) | no | **keep** | merged |
| `systemic/next-video` (+ `claude/project-thread-a6ccn6`) | 14 | writer rules from the spoken-storytelling research, register lint, SR/RF/ID/DL rules, LX rules, ID-06/ID-07, stone-age pilot v4.4-4.6 | SR/RF/ID/DL were re-homed as LV/RF/HI/DL in the Gemini line (D-120); LX-01..05 were not | **keep** | merged; LX section added to `SCENE_REUSE_RULES.md` (4c), `LX` registered in docs_lint |
| `claude/project-thread-4nebmi` (+ `argon/ltx-minimisation`) | 30 | J5 LTX minimisation: shot router, action rig, v3 minute plan, BP-182..184; VC-10 (first version) | no | **keep** | merged; BP-176..181 identical on both sides, 182..184 new: no id collision left |
| `argon/handoff-2026-11-06` (+ `icw/16-lean-pod`, `claude/project-thread-9hpm56`, `-4i756j`, `wpq/07b-resolve-cli` partly) | 68 | J5 dialogue/montage rules BP-176..181, j5_montage lint, route-test assets, p15 Qwen pods, RP-10 placement watch (D-118) | partly | **keep** (rules); pods are retired-era code kept as history (Q10) | merged; D-118 row restored |
| `icw/19-modal-schedule` (+ `icw/19-combo*`, `-ltx`, `-cards`, `-mouth`, `-pilot-pod`) | 34 | Modal run plan (cheapest hardware per step), `modal_p15d`, J5 CPU smoke on Modal, p15 combo windows | no | **keep** (Modal is where Wan runs, Q3) | merged; p15 clip table reconciled (only c4 is the battle clip in the Gemini line's v5 table) |
| `icw/21-mouth-job` | 18 | dated cloud-provider research: Modal and Hyperstack guides, cost comparison, `.claude/rules/cloud-platforms.md` | no | **keep** (docs); its mouth job is reference-only | merged; `p15_mouth.py` kept from icw/19-mouth as the commit itself says |
| `icw/05c-ink-round` (+ `claude/project-thread-t4x3vo`, `-1jk2d4`) | 4 | provider-neutral cloud adapters (PR #154, dry-run only, caps proposed and disabled), VC-10 child voice (PR #156) | no | **keep** | merged; VC-10: PR #156 kept (child 4-11 / teen 12-17), the other version's test follows it, plus a fix: a kid hero never gets a voice labelled middle-aged/old |
| `icw/19-hyperstack` | 1 (beyond combo4) | Hyperstack fallback for p15d, not enabled | - | superseded (Modal chosen, Q3); adapters arrive with #154 | not merged |
| `TEMP` | 1 (beyond 05c) | Georgian summary of Qwen/Blender prompting rules + a 1.2 MB sheet | the rules it summarises live in `SHOT_PROMPTS.md`, `UNIVERSAL_RULE_BASE.md` | retired-era summary | not merged (remains on the branch) |
| `opus/ink-chronicle-blender-plan-2026-11-04`, `experiment/blender-scene-poc-2026-11-04` | 9 + 8 | Blender planning package and scene PoC | - | retired era (Blender scenes retired, Q10) | not merged (remain on their branches) |
| `claude/project-thread-hzgjo1`, `-9yzh4a`, `-3c48lm`, `-14jebf-stream`, `-9t3vn0` | 7 + 3 + 2 + 1 + 1 | 10-30/31 work: J3 cite check, KG-23 wording, routing log, claude_api streaming, next-video routing | the Gemini line carries newer versions of every touched file (e.g. `claude_api.py` streams with `StreamSink` + `stream_proof`) | superseded | not merged |
| `claude/project-thread-b1uzvn` | 583 by hash / 484 by patch | the pre-squash history of main (Phase 1 .. J3, up to 10-30) | main was re-rooted; b1uzvn only deletes or reverts files relative to main | superseded | not merged |
| 37 further heads (`icw/00..20`, `wpq/*`, `fix/*`, `work/*`, other `claude/*`) | 0 | - | fully contained | - | nothing to do |

## Merge results

Order: Gemini line, codex handoff, systemic/next-video, 4nebmi, argon handoff, icw/19-modal-schedule, icw/21-mouth-job, icw/05c-ink-round.
Conflicts were in logs and tables (`PROGRESS.md`, `DECISIONS_AND_OPEN_QUESTIONS.md`, `INDEX.md`: both sides kept, rows sorted by id,
duplicates dropped), in `SCENE_REUSE_RULES.md` (the Gemini line's merged version kept, LX added), in the retired p15 pod tables and in
VC-10 (above). No rule id was lost or reused: the BP registry has no duplicate ids after the merges (`test_sourced_rules`).

The Gemini line's tip commit (68b99e8, "uSE BRANCH AND DELETE") added `GeminiNew/` (a 6.7 MB rar, a 7.0 MB zip, a v4.2 notebook and
a manifest). They stay in history; the working tree drops the two archives (repo rule: media and archives go to HF, not git):
`ep_toba_v4_2_demo_master.rar` sha256 `117756c8ecc774a42690df9cbc53939ee8b45d3ca72968466e3b0d51bcf74eef`,
`explainer_engine_v4_2_canonical_reconciled.zip` sha256 `347130ca490dfabc5667d79abbd93d67575f4e3b7ae684ae0b72451ea7438004`
(recoverable with `git show 68b99e8:GeminiNew/<name>`).

## Media of the v4.3 archive (P0.4)

The archive's media are on HF `vano1919/tmr-artifacts` (dataset), commit `b96593d4d5562ca9cabfa926f8a1319bf75d4719`, every sha256 checked after the upload: the Toba episode's 39 pictures, maps and references under `explainer-engine/episodes/ep_toba/` (list: `episodes/ep_toba/media_manifest.json`), and under `explainer-engine/v4_3_import_2026-11-12/`:

- `explainer-engine/v4_3_import_2026-11-12/GeminiNew/ep_toba_v4_2_demo_master.rar` (6700018 bytes, sha256 `117756c8ecc774a42690df9cbc53939ee8b45d3ca72968466e3b0d51bcf74eef`)
- `explainer-engine/v4_3_import_2026-11-12/GeminiNew/explainer_engine_v4_2_canonical_reconciled.zip` (7038280 bytes, sha256 `347130ca490dfabc5667d79abbd93d67575f4e3b7ae684ae0b72451ea7438004`)
- `explainer-engine/v4_3_import_2026-11-12/docs/Explainer Engine Architecture Technical Analysis.docx` (103364 bytes, sha256 `cb847b4d8802f37c2b7e97caef4f26ef400ef30536a6991a11c28e2717d6cecf`)
