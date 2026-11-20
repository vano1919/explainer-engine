# Overlay for `v-qc-skill`: Technical QA of what the run made (layer L23, stage G10)

Our rules on top of this folder's `SKILL.md`, which is the upstream text kept whole and byte-pinned (`SOURCE.md`,
`tools/vendor_skill.py verify`; team plan 2026-11-20 rule 4). Read this file whenever the skill loads; skill
`film-direction` routes here. Status: a draft written 2026-11-20 for its group's MS-5 step; it becomes binding when the
group's layer record passes the layer gate (MS-6).

Built from kajisho5/qc-skill, page `qc-skill` (MIT, commit `6fba4efc7c`). Rewritten 2026-11-20 under RW-50
([docs/SKILL_LAYERS.md](../../../docs/SKILL_LAYERS.md)) for a channel whose acceptance gate is code in the repo and whose
numbers live in the BP registry. The upstream text is this folder's `SKILL.md`; the package in `src/qc_skill/`
runs as a cross-check, and `docs/checks.md` is the manual of every measurement it can take.

## The principle we share with upstream

A gate measures or it says NOT_RUN (EP-03). No row is PASS because something "should" be fine; a row that could not
measure is NOT_RUN with its reason, and a report with a NOT_RUN is INCOMPLETE, never a pass. A measurement is evidence for
the owner's decision, never the decision: machine QA is not a person's approval (AV-08: `human: not_listened`).

## What G10 is here

`python -m explainer_engine.episode run episodes/<id> --stage qa` (RN-06) calls `stage_qa` in
`explainer_engine/episode/run.py`, which builds:

| Output | Made by | What it says |
|---|---|---|
| acceptance gates | `explainer_engine/episode/acceptance.py` | map shots rendered, master length against the script, a real read (no synthesized narration), no dropouts mid-line, the visual mix by duration (RT-04), transitions per ED-04, no paid call without an approval line, assets inside the episode, no foreign-era words in prompts |
| `qa/video_master_qa.json` | `explainer_engine/videolane/master_qa.py` | the master as a file: rate, sound and picture one length, frames against the plan, black and frozen runs inside video shots (VL-12) |
| `qa/sound_realism.json`, `qa/av_event_report.json` | `explainer_engine/qa/sound_realism.py`, `explainer_engine/episode/av_report.py` | every visible event's audio decision placed and heard over its bed (D-135, BP-189..BP-193) |
| `qa/master_loudness.json` | `stage_qa` with `explainer_engine/qa/targets.py` | BP-50 on the delivered master itself |
| the contact sheet | `explainer_engine/episode/production_runner.py` | one frame per shot for the eye |
| `production/production_manifest.json` | `stage_qa` | every stage's state; `all_gates_passed` is false in a rehearsal |

The HF upload of the outputs (hashes to vano1919/tmr-artifacts) and the owner's approval come after G10, outside the runner.

## Procedure

1. **Run G10 only on a fresh G9.** `python -m explainer_engine.episode status episodes/<id>` must show `assemble` fresh;
   a stale record makes QA describe an old master.
2. **Read every non-PASS row first.** NOT_RUN: name what is missing (a stems report, a timing file, the master). FAIL:
   open the file it names. REVIEW: a hypothesis rule (D-59) or an engineering default; say so, do not upgrade it.
3. **Cross-check on the file** when a row surprises you: run the vendored engine (below) or skill `v-ffmpeg-skill`
   (`probe.py`, `loudness.py`, `scenes.py`) on the same master. Two instruments that disagree is a finding to report.
4. **Look and listen.** Open the contact sheet and frames at three scene boundaries; listen to the loudest change and one
   hero line. When the episode asks for it, `explainer_engine/qa/look_and_listen.py` holds that record.
5. **Report** per row: verdict, number, rule id, file. Never "QA passed" with a NOT_RUN in the table.

## The vendored engine as a cross-check

```bash
PYTHONPATH=.claude/skills/v-qc-skill/src python3 -m qc_skill.cli doctor --json
PYTHONPATH=.claude/skills/v-qc-skill/src python3 -m qc_skill.cli run request.json --json --workspace episodes/<id>/qa/vqc
```

- `operation: inspect` first (pure measurements), then `check` with explicit `rules`. It never assumes a target; a rule we
  do not give is not run, which is what we want.
- Take every target from our registry: loudness from `explainer_engine/qa/targets.py` (BP-50 long, BP-61 Shorts), frame
  size and rate from `explainer_engine/core/delivery.py` (BP-167). Never type a number into a request from memory.
- Useful opt-ins: `expected_cuts` (our cut list from the timed script against detected cuts), `check_photosensitivity`
  (fire, artillery flashes, lightning), `text_regions` for a date chip or a Short's hook card, `kind: delivery_package`
  for a Short with its captions and thumbnail together.
- `overall_status: FAIL` is information about the file, not a failure of the call; `status: failed` is a tool error.

## Hard rules at this layer

- QA never repairs. A finding goes back to the stage that made the thing (G7 clip, G8 mix, G9 chunk) and that stage reruns.
- Loudness is measured on the delivered file, never on a stem only; the house numbers have one home (`qa/targets.py`).
- A Short is checked as a Short: `python -m explainer_engine.qa.short_format <SH01.mp4>` (9:16, length).
- Publishing metadata is its own check: `python -m explainer_engine.qa.publish_check <publish.json>` (PC-01..PC-10).
- The review bundle is sealed with `python -m explainer_engine.qa.review_bundle write <bundle folder>` only after G10.
- Nothing goes public (invariant 4); QA output is never the owner's word.

## Failure modes and fixes

| Row or symptom | Usual cause | Fix |
|---|---|---|
| `master_length_matches_the_script` FAIL | a shot re-timed after the read, or a chunk from an old run | rerun G6 timing, then G9 |
| `narration_is_a_real_read` FAIL | a placeholder voice in the mix | run the voice stage with the real read (G6) |
| VL-12 black or frozen run | a video clip ended early or froze | re-ingest or re-generate that clip (video lane) |
| master loudness off | a manual mix fix, or stems re-rendered without the master | rerun G8 then G9; never normalise the master by hand |
| INCOMPLETE with a NOT_RUN | an input file missing | make the input; never mark it PASS |
| vendored engine and our row disagree | different gating or window | report both numbers; ours decides, the gap is a finding |

## Checks in code

`explainer_engine/qa/gates.py` (the row shape and verdict), `explainer_engine/episode/acceptance.py`,
`explainer_engine/videolane/master_qa.py`, `explainer_engine/qa/targets.py`, `explainer_engine/qa/short_format.py`,
`explainer_engine/qa/publish_check.py`, and the planned S16 validator `explainer_engine/validators/tech_qa.py` (planned, W2).

## References: when to open which

| File | Open when |
|---|---|
| `docs/checks.md` | the exact measurement, field and finding code behind a check (video, audio, subtitle, delivery) |
| `docs/architecture.md` | how inspect, check and validate differ |
| `docs/decisions.md` | why a check is opt-in or reports UNKNOWN |
| `docs/testing.md` | trusting a measurement before relying on it |
| `docs/security.md` | input roots, refused keys, timeouts |
| `contract/contract.json` | the machine-readable request and response shape |

## Not used from upstream

The publish-or-block decision framing of the ecosystem's production agent (ours is the owner's), VMAF, SSIM and PSNR
against a reference (we have no mezzanine to compare), stinger, loop-seam, alpha-edge and key-fill checks (we do not ship
graphics packages), release scripts in `scripts/`, and the ecosystem roadmap.
