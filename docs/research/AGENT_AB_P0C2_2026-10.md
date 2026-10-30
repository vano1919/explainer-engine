# Agent form A/B at full scale, 2026-10-30 (P0c-2): 16 segments, single context vs workers on a cheaper model

Follow-up to [AGENT_AB_2026-10.md](AGENT_AB_2026-10.md) (P0c, 8 segments, all Sonnet). That report left one argument for the per-stage worker form
untested: a long script (many segments) and a cheaper model for mechanical stages. This is that test. Free, no paid call, no code change besides `measure.py`
(it now also reads the `s03r_writer` repair snapshot). Data: `agent_ab_2026-10/p2/` (inputs, every snapshot, logs, metrics, cost, critic input and text).
The decision on A5 is the creator's / the plan thread's; this report is evidence.

## Setup
- Same material and brief as P0c, but template D: 16 segments, about 15 minutes, about 2,400 words, 3 Shorts, 4 voiced heroes, 5-6 staged scenes (`p2/input/BRIEF.md`).
  Same claim map in both arms (`p2/input/claim_map.md`, C-NN, C-91..C-94 are the invented premise). Stages 1, 2, 2b, 3, 4, 5, 6 of `story-engine`, no paid tool, the
  existing Napoleon script forbidden reading.
- Arm A2: ONE Sonnet 5.5 agent, one context, all stages, own gate harness (`gate.py`).
- Arm B2: 26 fresh workers, one per stage unit, the orchestrator (this session) re-runs the gates after each return: architect (Sonnet), one writer per segment (16, Sonnet),
  beat-writer in four groups of four segments (Haiku 5.5), performer (Haiku), one routed repair writer (Sonnet), editor (Sonnet), caster (Haiku), shorts (Haiku).
  19 Sonnet workers, 7 Haiku workers. Each worker saw only its stage page, the brief and the previous snapshot.
- Blind critic: Opus, read-only, labels random (X = A2, Y = B2, revealed only after the verdict in `p2/critic_labels.json`), episode id and notes scrubbed; see Limits for exactly what was and was not scrubbed.
- Measurement is independent of the arms: `measure.py` runs the repo's `story_lint`, `stage_guard`, `production validate` on every snapshot.

## Numbers (from files)
| | A2 (one context) | B2 (26 workers) |
|---|---|---|
| Segments / lines / words / shots / Shorts | 16 / 238 / 2,392 / 160 / 3 | 16 / 173 / 2,447 / 161 / 3 |
| `story_lint` final | 0 FAIL, 0 REVIEW | 0 FAIL, 4 REVIEW (ST-11, ST-17 x2, ST-19: story-level, cross-segment) |
| `stage_guard` violations vs previous snapshot, all stages | 0 | 0 |
| `production validate`, final, same stand-in world on both (see limits; inputs and outputs in `p2/validate_standin/`) | 119 FAIL, 148 REVIEW | 153 FAIL, 177 REVIEW |
| of the FAILs: media / creator gates and the not-yet-run compile (PV-05 files, PV-11 "prompt is missing or stale: run compile", PV-45, PV-47) | 119 | 150 |
| of the FAILs: script defects | 0 | 3 (PV-44 VB-09: base expressions of three heroes missing from the face sheet; architect-owned) |
| Real file's own schema FAIL | not measurable (validate crashes on its world era; its own harness found none) | 1 (PV-01: one line has `intent` "command", not in the enum; a stage-2/3 field) |
| Work cost, input-price units, same-model ratios (`cost.json`, per model `cost_by_model.json`) | 14.19 M | 19.08 M (Sonnet 9.23 M + Haiku 9.85 M) |
| Active worker time (`cost.json`, per model `cost_by_model.json`; excludes usage-limit stalls and hand-offs) | 47 min | 57 min (Sonnet 31, Haiku 27) |

Cost reading, independent of any price list: B2 is cheaper than A2 only if a Haiku unit costs less than (14.19 - 9.23) / 9.85 = 0.50 of a Sonnet unit. Haiku burned
more units than Sonnet (mostly cache reads: each worker re-reads the stage pages and the whole script), so the cheaper model did not shrink the work. The unit price
ratio of the two models is not in this repository; check it before reading this as money.

## Blind critic (text `p2/critic_blind.md`)
| Criterion (1-5) | X = A2 | Y = B2 |
|---|---|---|
| Premise / dramatic question | 4 | 4 |
| Escalation and turns | 4 | 3 |
| Voice distinctness (SC-12, SC-11) | 4 | 3 |
| Dialogue craft | 4 | 3 |
| Ending and payoff | 4 | 3 |
| Pacing over 15 min | 4 | 3 |
| Mean (recomputed from the table) | 4.00 | 3.17 |

Verdict (critic): A2 is the better product by a clear but moderate margin. Decisive: A2's plot is a closed causal chain (B2's midpoint leak has no consequence and its
battle has range and timeline errors); A2's wit lives in the characters (B2's narrator states traits and the moral, and the same interjections go to every speaker);
A2's sound and shot layers serve the story (B2: no steppe ambience, a mismatched bed under the cold open, 9 of 16 segments without audio entries). B2 is better in a
dramatic question that holds to the end, the ironic answer, the closing image and a more visual climax. Rule-focus losses counted by the critic: A2 about 7, B2 about 14;
spoken-fact problems: A2 5, B2 about 7 (B2 also has several story-logic errors across segments).

## What the process data show
- The cross-segment story rules (ST-11, ST-17 narrator blocks, ST-19 narrator share) are the ones a per-segment writer cannot hold: B2's 4 story-level REVIEWs and the critic's
  "moral told twice" and "same interjection everywhere" are the same effect. In A2 the one agent saw all 16 segments and rewrote S04/S06/S08/S10/S11/S13 against them.
- Hand-off gaps again: text-level PV-12 lints (N-02, N-05, ...) show only after later stages; the shared `gate.py` narration check misses them, so one repair writer
  round was routed after the performer. The 1 schema FAIL in the real B2 file (`intent` "command") passed the stage-2 and stage-3 gates and blocks `production validate`
  before every later rule runs; the editor and caster worked on a scratch copy to see their own gates.
- Haiku did the mechanical stages (beats, performer, caster, shorts) acceptably: all `stage_guard` checks clean, Shorts pass PV-28/PV-34. The weaker point is the beat layer's REVIEW volume (PV-44 45 vs 41 is a tie) so no clear Haiku penalty is visible on these gates.
- A2 retries by stage (self-reported): architect 2, writer 6 segments redone, performer 2 passes, editor about 6 rounds, caster 2, shorts 3, plus two returns to earlier stages.
  B2: architect 2, performer and caster re-runs, editor 6 rounds, shorts 3 tries, one routed writer repair. Late-found rules cost both arms a regeneration of stage 4.

## Limits
- One sample per arm; the critic is one reading. Differences of one point on a criterion are inside the noise of the P0c data; the systematic ones the critic names recur across
  segments and layers.
- Production gate: `production validate` crashes on world era `steppe_1223` and `france_1812` (not in the codex). A2 kept its own world block in the real file; for measurement both finals
  were validated with B2's stand-in world (host era `medieval_europe`, no visitors, no day arc). B2's editor chose that stand-in, A2's world entries are richer; world resolution is not a stage under test.
- The shared `gate.py` narration check misses the text-level PV-12 lint; both arms ran it, so the effect is symmetric, but B2 only learned of it late.
- Contamination: the Haiku shorts worker opened `arm_A/production_script.json` once by mistake (it printed A2's shorts block and says it used nothing from it). The arms were not
  isolated otherwise. The first line of the cold open differs between the arms here (unlike P0c).
- Blinding was imperfect. What was scrubbed: the episode id and notes in both scripts, and the `[budget N words]` planning notes in the segment headers (present in X = A2 only, removed there). 
  What was not: Y = B2's input still carries word-target hints in 16 places (3 of them read "~30 words", the others other targets) and 8 distinct BP/KP rule ids (9 occurrences), both scripts carry their claim ids, and structural traits (narrator share, tagged lines, sound-entry density) can reveal a form. The critic did not guess the forms, but this is not proof it could not.
- Cost units are token units of one price ratio; Haiku and Sonnet units are not the same money. A usage-limit stall hit both arms; its time is excluded, not measured.
- Not tested: real timing, painted pictures, a human viewer, more than one sample, workers on a model above Sonnet for the story stages.

## Evidence for A5 (the decision is not this report's)
At 16 segments the evidence points the same way as at 8: the one-context script is the better product by a moderate margin, with fewer rule losses, equal or better on every gate,
and 26% fewer cost units even though B2 ran 7 of 26 workers on the cheaper model (it would need Haiku at under half the Sonnet unit price to be cheaper). The long-context
argument for workers did not show up as an advantage in this sample; the cheaper-model argument stays open on price only. The recommended reading: keep D-79 as the default for
dialogue what-ifs; workers for isolated mechanical stages (beats, caster, shorts) are viable on Haiku but need their own ownership fixes (`scene` in `stage_guard` architect fields, a partial-gate command per stage, one claim-id format). Both
remain the creator's / the plan thread's call.

PV-11 (here and in the P0c report): the message is "prompt is missing or stale: run compile". It marks the `production compile` step as not run (or run before later text edits), so it is pipeline state, not script content. In this report neither arm compiled, so it is counted with the media gates. The P0c report originally counted arm B's 8 PV-11 as script defects; it now lists them separately for the same reason (arm A had recompiled, arm B had not).
