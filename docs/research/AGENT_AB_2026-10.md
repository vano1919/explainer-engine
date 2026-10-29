# Agent form A/B, 2026-10-29 (P0c): one main agent vs one worker per stage

Question: does the writers' room keep its focus better as one main agent in one context ([D-79](../DECISIONS_AND_OPEN_QUESTIONS.md),
[OR-20](../ORCHESTRATION.md)) or as a separate worker per stage with a gate after every return (the proposed per-stage worker form)? Free test, no paid
call. Data and scripts: `docs/research/agent_ab_2026-10/` (inputs, every stage snapshot of both arms, `measure.py`, metrics JSON).

## Setup (identical for both arms)
- Same brief; the claim map has the same rows in both arms (`agent_ab_2026-10/input/claim_map.md`), but arm A worked from a renormalised copy (`C-NN`, invented ids `C-91..C-94`; `arm_A/claim_map.md`) because `scripting/claims.py` parses only that form, so the setups were not byte-identical: "What if Napoleon marched into Genghis Khan?", 8 segments (about 5 min), 3 Shorts, stages 1, 2, 2b, 3, 4, 5, 6 of the `story-engine` skill, Sonnet 5.5 for every worker and for arm A, no paid tool.
- Arm A: ONE Sonnet agent ran all stages in one context (interleaved writer/beats per segment, own gate harness).
- Arm B: the orchestrator spawned 22 fresh Sonnet workers: architect, then writer and beat-writer per segment (16), performer, editor, one architect repair round, caster, shorts. Each saw only its stage page, the brief and the previous snapshot. The orchestrator re-ran the gates after each return.
- The existing Napoleon script in the repo was forbidden reading for both. The Opus critic was read-only and blind (labels X = arm B, Y = arm A, hidden from the critic; ids and notes scrubbed).
- Measurement is independent of the arms: `measure.py` runs the repo's own `story_lint`, `stage_guard` and `production validate` on every snapshot.

## Numbers (all from files)
| | Arm A (one context) | Arm B (22 workers) |
|---|---|---|
| Words / lines / shots / Shorts | 1041 / 69 / 66 / 3 | 874 / 69 / 57 / 3 |
| `story_lint` final | 0 FAIL, 0 REVIEW | 0 FAIL, 0 REVIEW |
| `stage_guard` violations across snapshots | 0 | 0 (1 on the repair round, see below) |
| `production validate` final | 28 FAIL, 60 REVIEW | 27 FAIL, 133 REVIEW |
| of the FAILs: media / creator gates only | 28 (21 PV-05, 6 PV-47, 1 PV-45) | 14 (9 PV-05, 4 PV-47, 1 PV-45) |
| of the FAILs: script defects | 0 | 13 (8 PV-11 stale prompts, 2 PV-12, 1 PV-48, 1 PV-37 claim ids, 1 the rule parser did not classify) |
| REVIEWs PV-44 (beats) / PV-12 (narration) | 2 / 0 | 61 / 47 |
| Retry rounds, self-reported (`retries.json`, per-worker detail `arm_B/WORKER_REPORTS.md`) | architect 1, writer 4, beats 3, performer 1, editor 4, caster 2, shorts 1 | architect 2, writer 2 on S03 and S07, beats 2 on S04, performer 2, editor 4, caster 2, shorts 3, plus one routed repair |
| Work cost, input-price units (output x5, cache write x1.25, cache read x0.1; `cost.json`, `cost.py`) | 9.57 M | 9.62 M |
| Active worker time (`cost.json`; excludes the 18:58-22:03 usage-limit stall and the orchestrator's hand-offs) | 29 min | 36 min |

Cost is equal within 1 %. Arm B spent more on cache creation (every worker re-reads the pages), arm A on cache reads (one growing context).

## Blind critic (Opus high, read-only; text in `agent_ab_2026-10/critic_blind.md`, exact input in `critic_input/`)
Labels were random: X = arm B (workers), Y = arm A (one context). The critic scored six story criteria 1-5; the report's own
headline ("3.9 vs 3.7") did not follow from them, so the means are recomputed here from the table:

| criterion | X (workers) | Y (one context) |
|---|---|---|
| premise and dramatic question | 4 | 4 |
| escalation and turn of each scene | 3 | 4 |
| character voice, show don't tell | 4 | 4 |
| dialogue craft | 5 | 4 |
| ending and payoff of set-ups | 4 | 4 |
| would a viewer stay (30 s / 2 min) | 3 | 4 |
| **mean of six** | **3.83** | **4.00** |

A gap of 0.17 on one sample per arm is within what the critic itself called noise; its prose verdict was "Y narrowly better,
three decisive reasons: story spine and retention, sound/edit layer, claim-id defect fixable mechanically". X (workers) wrote the
best single scene of either script (the interpreter softening the insult, S07), better shot coverage, closer wording to the claim
map; X also has one music loop for 5 minutes, a lecture block at S02, a dropped set-up (Murat) and a day arc that contradicts its
shots. Y (one context) has the clearer cause-and-effect spine, a scene by 0:30, paid-off set-ups and a finished sound layer
(music per chapter, planned dropout, beds); Y's faults are the claim-id format (the invented premise got ids `C-91..` labelled as
facts), a "you" tic and 20 % over length.

## What the process data show
1. **The hand-off fields are the weak point of per-stage workers, not focus.** Three defects only surfaced at the editor stage and could not be fixed by the worker that saw them: no `face_sheet` for heroes (VB-09/VB-06) although the beat-writer used expression beats; a dialogue segment without a `scene` header (PV-48); delivery tags the PV-12 lint does not know. Arm A hit the first one too but spotted it earlier because one agent looked ahead at the later pages. In arm B the orchestrator had to route a repair round back to the architect.
2. **A real tooling bug, found by the repair round:** `scripting/stage_guard.py` `SEG_STORY` does not contain `scene`, although the architect page, CLAUDE.md and STORY_ENGINE SC-01 say the architect owns it. The guard passes a first architect pass (empty before-state) and rejects any later correction of a scene header. Not fixed here (this phase writes no code); needs its own fix and test.
3. **Gates that cannot run early.** `production validate` stops at the schema check while `voice`/`shots` are missing, so several workers reported "PV-44 not reached". Arm A built a small scratch harness running the individual lints (PV-12, PV-44, PV-37, PV-48) after each stage and got earlier feedback. This is a skill of the agent, not of the form, but it shows the per-stage gate needs a documented partial-gate command in either form.
4. **No focus loss was observed in arm A at this scale.** Its self-report lists late discoveries (its first gate ran only the document-level narration lint, so about 14 lines changed after beats and delivery existed; one field written outside the editor's ownership, caught by the guard) but nothing that stage_guard or story_lint failed to catch. The context-length argument for workers is NOT tested here: 8 segments and about 5 minutes are far below a 15-minute episode.
5. Claim ids: arm A silently changed the claim map format so the repo parser could read it (`C-NN`); arm B kept the map and PV-37 then found zero claims. The parser and the map format should agree whatever the agent form.

## Independence of the two samples
Both scripts open with the identical line "The drums stop first." and the same fog-on-the-road hook. No cross-read was found: arm B's architect listed the then-empty `arm_A` folder once and read nothing from it, and both briefs forbade the earlier Napoleon script. The most likely cause is the shared model prior plus the shared claim map (I01 is the fog), but the arms are therefore NOT fully independent draws; treat the story-level comparison with extra caution.

## Limits
Traceability: the subagent transcripts are not committed (only `cost.json`, `retries.json` and `arm_B/WORKER_REPORTS.md` derived from them; retry counts are self-reported). Arm A's working files are committed (`arm_A/story/`, `arm_A/scratch/*.py|*.md`, its LOG and FINAL_REPORT); its stage-page versions are those of the repo at commit 504fa35 (the branch base when the arms ran; main moved afterwards). The critic prompt is committed in condensed form (`critic_prompt.md`, paths shortened). Blinding is imperfect: arm A's `C-NN` claim ids and its sound-library choices were visible to the critic and it noticed the id format, so it could infer a different setup even though the labels and the episode id were scrubbed.

One sample per arm, one topic, one model (Sonnet) for both; the critic's own noise/systematic split is a judgement. Per-stage model choice (the other half of the worker case) was not tested because the models were held equal on purpose. Scale was 8 segments, not the 16 of template D. Costs are token units, not money. No picture, voice or render was produced, so everything about look and sound is judged on the written plan only. The shared input stage 0 was given, not tested.

## Evidence for A5 (the decision is the creator's / the plan thread's, not this report's)
On this sample the evidence does not support replacing the one-main-agent form with per-stage workers: at equal cost the one-context script was narrowly better as a product, equal on every free structural gate that failed anywhere, and the worker form cost a routed repair round and exposed three ownership gaps. It also does not refute the worker form: the argument that matters for workers (a 135k-token context across 16 segments, and a cheaper model for mechanical stages) was out of scale. The evidence points to: **keep D-79 as the default; do not make the worker form the A5 answer on this evidence.** If the creator wants the long-context argument tested, the next free test is the same A/B at 16 segments on template D, with arm B's mechanical stages (beats, performer) on a cheaper model.

Independent of the A5 answer, three fixes are worth a small separate phase (each with a test): `scene` in the architect's segment fields of `stage_guard`; a documented partial-gate command per stage (the lints that run before `voice`/`shots` exist); one claim-id format accepted by `scripting/claims.py` and the claim-map writers.
