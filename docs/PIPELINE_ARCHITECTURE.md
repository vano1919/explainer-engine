# Pipeline architecture

## Current implementation status — checked 2026-10-18

The stage table below is a target architecture, not proof that every stage or a single-command DAG coordinator exists. The documented command `python -m explainer_engine run ...` is not present as a repository entry point on this branch. The current available CLI is `python -m explainer_engine.production`, with per-script validation/timing/assembly, plus `python -m explainer_engine.production_gate`. Paid image generation is exposed through `python -m explainer_engine.production.paint`.

Do not invoke the target command as if it already existed, and do not claim the entire research-to-final-video workflow is end-to-end automated. A dependency-aware resumable coordinator that schedules voice, picture, sound and music tasks together remains future implementation work. The current stages must be orchestrated by the agent workflow and verified individually.

## Target pipeline design (not yet fully wired end to end)

Python orchestrates; each stage is a module with a versioned input and output, saved as an atomic checkpoint by
`explainer_engine/core/store.JobStore` (stage list is declared, not hard-coded). The job never publishes (P-20).

## Stages (S- ids)
| Stage | Input -> output | Validation / failure | Retry, recovery | Cache key | Approval | Cost |
|---|---|---|---|---|---|---|
| S01 intake | `episode.yaml` -> validated config + job record | config schema; disk >= reserve; credentials present; cost estimate | permanent errors stop; nothing spent | config hash | | none |
| S02 suitability | topic -> risk assessment (pillar, sensitivity, claim difficulty, source availability) | sensitive topic without second reader = NEEDS_REVIEW | rerun | topic text | creator if sensitive | none |
| S03 research | topic -> dossier (sources, passages) | each source has URL, date, access date, grade | network = retryable; resume reuses fetched sources | source URL + date | | session time |
| S04 claim map | dossier -> claims C-xx | each claim has a passage and confidence | rerun | dossier hash | | |
| S05 script | dossier + claims -> script (+ Shorts candidates) | every factual sentence maps to a claim; metrics (words, pace budget) | revision loops, max 5 on the same issue then report | claims hash + format | | |
| S06 editorial QA | script -> rubric scores + flags | gates in [SCRIPTING_SPEC](SCRIPTING_SPEC.md) | below gate = NEEDS_REVIEW | script hash | **#1 creator approves script + claims** | |
| S07 storyboard | script -> storyboard v1 | schema + references + anchors unresolved yet | permanent on schema error | script hash | | |
| S08 assets | storyboard -> asset manifest + missing-asset list | licences, viewBox, palette lint; reuse search | creation tasks go to the creator/Claude; paid calls need the estimate gate | asset hashes | | possibly Gemini |
| S09 narration | script -> clips + `audio.words.json` | timed path present; pace within 10 %; ASR check | clip cache; a bad clip re-synthesises only that clip | text + delivery | | CPU time |
| S10 timing | storyboard + words -> frame table | narration never cut; no overlap | reflow once; else NEEDS_REVIEW | words hash | | |
| S11 scene render | storyboard + frame table -> scene MP4s | ffprobe, black/frozen scan | retry crashed tab twice; scenes cached | scene cache key | | CPU, disk |
| S12 mix | clips + music + SFX -> audio.wav | loudness/true peak/silence/gap | rerun mix only | audio-event hash | | CPU |
| S13 assembly | scenes + audio -> episode.mp4 | duration, A/V sync, dimensions | rerun | scene + audio hashes | | |
| S14 Shorts | Shorts scripts -> vertical storyboards -> renders | standalone checklist, safe areas | per Short | per Short | | |
| S15 packaging | script + timeline -> thumbnail, titles, description, chapters, metadata | policy checklist, thumbnail checks | rerun | script hash | | |
| S16 QA + bundle | all outputs -> technical report, editorial checklist, review bundle | FAIL stops; REVIEW listed | rerun after fixes | all hashes | **#2 creator approves the package** | |
| S17 record | approval + manual upload -> analytics record | video id supplied by the creator | | | | |

## Failure classes (every stage declares which it can raise)
Retryable (network, renderer crash): 2 tries, backoff 2 s then 4 s, counts kept in state.json. Permanent
(configuration, contract, missing credential): stop, state FAILED with the cause, nothing retried. Human review
(editorial gate, sensitive topic, QA REVIEW): state NEEDS_REVIEW, everything saved first. Duplicate work is prevented by
the cache keys above; cost is accounted per call in the ledger; resume continues after the last complete stage
(`JobStore.completed_prefix`) or from `--redo-from N`.

## Job record and directories
`jobs/<slug>/job-NNN_<date>/` holds `state.json` (status, stages, retries, cost ledger, peak memory, errors),
`artifacts/NN_<stage>.json`, `job.log`, `tmp/`, outputs (`episode.mp4`, `shorts/`, `thumbnail.png`, `package/`),
`review_bundle/`, `final_manifest.json` (every deliverable, checksum, what is missing). Cleanup deletes only job
directories that are neither protected (KEEP, final render, review bundle, NEEDS_REVIEW, active) nor needed.

## Configuration
Grouped by responsibility: channel profile, topic/format, script, voice/TTS, visual style, asset paths, storyboard/render,
audio targets, Shorts, QA thresholds, API/cost limits, retries, output, approval policy. Each group has a schema;
precedence CLI > episode file > channel profile > default; secrets only in environment variables or gitignored `tools/`,
never in a config file that is committed and never in logs.

## One command
`python -m explainer_engine run episodes/<slug>/episode.yaml` creates the job, validates configuration, checks disk and
credentials, prints the cost estimate, runs the stages up to the next approval gate, reports progress, and writes the
final manifest and the list of missing deliverables. It stops on critical QA failure and never uploads.
