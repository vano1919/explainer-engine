# PRS: every open PR and branch, and what this branch holds

State of GitHub at 2026-11-06 ~19:05 UTC (listed with the GitHub API). "Merged here" = a merge commit on `argon/handoff-2026-11-06`
with the PR number in its message; conflicts were only in `docs/PROGRESS.md` (both entries kept) and in
`explainer_engine/blender/pilot_stills.py` (PR #152 vs #150; both sides kept because they add independent commands, `python -m
py_compile` clean; the D-77 newer-rule test did not need to decide anything). Test counts are the `def test_` functions in the named
file on this branch, plus the number the PR's own handoff reported where one exists.

| PR | branch (head sha at listing) | base | state here | what it adds | tests |
|---|---|---|---|---|---|
| #152 | `icw/20-pilot-envs` (3b12f4b) | `icw/19-pilot-pod` | **cancelled by the creator 17:35 UTC; merged here, kept** | layouts pilot_courtyard / pilot_march / pilot_camp, night-camp light preset, `pilot_stills extend/sheet`, CI workflow `pilot-envs.yml`, p15 v5 (clips c5/c6/c8, 9 restyles). No stills were ever rendered or uploaded; the CI run failed at a Poly Haven checksum (transient) and was cancelled. See `handoffs/ENVS_CANCELLED_NOTE.md` | `test_pilot_envs.py` 11 |
| #151 | `claude/project-thread-4nebmi` (7007d7d) | `icw/05c-ink-round` | **merged here (three times: 362be4c, f7add32, then the head 7007d7d with montage rules BP-176..181, `j5_montage`, `j5_minute` v1/v2 and `docs/J5_ARGON_REVIEW.md`)** | J5 dialogue collage steps 1-4b: cut-out cards in Blender 2.5D, animated background, idle motion, dip transition, ElevenLabs voice (155 credits), Rhubarb mouth cues, blinks/brows/jaw (`blender/j5_collage.py`, `j5_background.py`, `j5_face.py`, `docs/J5_DIALOGUE_COLLAGE.md`) | collage 4, background 8, face 5 |
| #150 | `claude/project-thread-9hpm56` (6c3f68e) | `icw/19-pilot-pod` | **paused by the creator 16:54 UTC; merged here, kept** | P1 pilot minute: two new static battle cameras, p16 pod package (3 restyles + 8 LTX clips), `production/pilot_minute.py`. Nothing paid. See `handoffs/HANDOFF_P1.md` | p16 10 (handoff said 11), pilot_minute 5, pilot_stills 14; the thread reported 3090 passed |
| #149 | `icw/19-pilot-pod` (0e7e030) | `icw/16-lean-pod` | **the base of this branch (3e8f994); its head 0e7e030 (p15q pins, 48 GB cards, 3-failure stop) is merged again here** | pilot pod p15: Qwen restyle of the Blender stills, two or eight LTX i2v clips, the Qwen-only mode (24 pictures), RP-10 placement watch (D-118). The pod has not placed yet (`OPEN_QUESTIONS.md`) | p15 15 |
| #147 | `icw/17-run-schedule` (36cf22b) | `icw/05c-ink-round` | in the base | RP-11 / D-117: every combination of a pod's run costed before the pod (`cloud/schedule.py`) | `test_cloud_schedule.py` 10 |
| #146 | `icw/16-lean-pod` (d29a769) | `icw/05c-ink-round` | **merged here: icw/19 did NOT contain its newest commits** (fix 2, the step-3 pod without the battle and G, the p14.sh pin 8f64392; the brief assumed it did) | the lean step-3 pod package p14: stages A-G, extras X1-X6, one pinned code bundle | `test_p14_lean.py`, `test_p14_pod.py` 7 |
| #140 | `claude/project-thread-4i756j` (af06ad9) | `icw/05c-ink-round` | **merged here** | route-test Qwen asset pod: script, 42-picture prompt list, tests; run report in PROGRESS | `test_route_assets.py` 10 |
| #137 | `wpq/07b-resolve-cli` (8bef9b2) | `icw/05c-ink-round` | **merged here** | WP-Q7b: `camera_setups` resolve CLI for the render matrix | `test_camera_setups.py` 16 |
| #131 | `icw/05c-ink-round` (90e728b) | `icw/06-characters` | the **working base line** of the whole branch; this handoff's draft PR targets it | ICW-05c look round, plus the whole ICW line below it incl. PRs #141-#145 (rules PR D-116, J5 route, layout passes, step-3 code, pilot assembly) and #148 (pilot stills) | n/a |
| #130 | `icw/06-characters` (8a59b68) | `opus/ink-chronicle-blender-visual-system-2026-11-04` | history, below the base line | ICW-06 characters, rigs, lip sync, scene builder, camera rigs | n/a |
| #120 | `experiment/blender-scene-poc-2026-11-04` (6f686a5) | `claude/master-mold-ready-2026-11-04` | **not merged: old era, listed as history** | Blender scene PoC, five-second render | n/a |
| #119 | `claude/project-thread-zdxkv6` (5013a55) | `main` | **not merged: main-based, old era, history** | WIP P12 combined pod (measurement + Qwen + LTX), Fable plan, Opus draft code | n/a |
| #112 | `claude/project-thread-9t3vn0` (1273619) | `main` | **not merged: main-based, history** | next-video scenario routing and `next_video_script` cap | n/a |

Rules for the line: the work branch is `icw/05c-ink-round`; `main` has nothing of Ink Chronicle and changes only on the creator's word;
no branch is deleted. The pilot launch worker keeps pushing `icw/19-pilot-pod`; this branch merges its head once more at the end of
the handoff (see the last line of `OPEN_QUESTIONS.md` for the sha merged).

## Verification of this branch

Full `tests/unit` run on the final head and `python -m explainer_engine.docs_lint` result: see `OPEN_QUESTIONS.md`, last section
("Verification"). Merges were not rebuilt into the p14/p15 code bundles: the sha pins in `p14.sh`, `p15.sh` and `p15q.sh` describe
bundles built from the PR commits, not from this merge commit; **do not launch any pod from this branch** (it is a reading and
planning branch; launches come from the owning branches after OR-23/OR-34).
