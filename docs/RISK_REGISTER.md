# Risk register

Probability and detectability are qualitative with the reason stated (no invented percentages). Impact: L/M/H.
Owner = the stage or role responsible.

| ID | Risk | Probability (why) | Impact | Detectability | Prevention | Mitigation / trigger | Owner |
|---|---|---|---|---|---|---|---|
| R-01 | Wrong niche | medium: demand evidence is weak (SE register) | H | late: needs analytics | small first cycle, like-for-like review | fallback positioning trigger (decision log) | creator |
| R-02 | Overgeneralising large-channel outliers | high: the research is outlier-heavy | M | early: register grading | SE treatments, no IP imitation | reject unsupported claims | S-research |
| R-03 | Too broad an audience | medium: three pillars | M | analytics | one promise, one voice | narrow to one pillar | creator |
| R-04 | Weak or misleading packaging | medium | H | CTR vs retention | honesty rule, promise-payoff check | revise per learning loop | S15 |
| R-05 | Robotic narration | medium: TTS is synthetic | H | listening test | Phase 5 blind test, lively delivery | change voice or approve a paid voice | S09 |
| R-06 | Repetitive scripts | medium: LLM drafting | M | flags, reviewer | format structures, flag list | rewrite section | S05 |
| R-07 | Visual inconsistency / character drift | medium | M | review, SVG lint | part-based rig, sheet, palette lint | fix the asset | S08 |
| R-08 | Animation too complex for one person | high: scope creep is the default | H | hours in the time log | finite vocabulary, prototype gate | cut features | architecture |
| R-09 | Weak audio | medium | M | loudness and listening checks | targets and gates | remix | S12 |
| R-10 | Unverified or fabricated claims | medium: LLM assistance | H | claim map, second read | claim-per-sentence rule, approval #1 | stop the pipeline | S04-S06 |
| R-11 | Overspending on generated assets | low: caps are enforced | M | ledger | estimate before call, D-19 | stop at 80 % | cost gate |
| R-12 | Resource exhaustion (RAM) | medium: 16 GB, Chrome tabs | M | memory log | bounded concurrency, streaming mixes | lower concurrency | S11 |
| R-13 | Disk exhaustion | medium: constrained storage | M | pre-flight | disk reserve, cleanup rule | clean jobs | S01 |
| R-14 | Render failures | medium | M | state.json | per-scene cache, retries | resume | S11 |
| R-15 | Dependency / Windows issues | medium: Node plus Python | M | setup check | pinned versions, `npm ci`, setup script | fallback renderer | Phase 10 |
| R-16 | Copyright and licensing | low-medium | H | licence register, QA | per-file records, no IP, original characters | remove asset | S08 |
| R-17 | Changing tools, APIs or policy | high over a year | M | registry age check | dated registry, re-verify before batches | update the decision | creator |
| R-18 | Unvalidated thumbnail scores trusted | medium | M | reviewer | scores are heuristics (TITLE_THUMBNAIL_SYSTEM) | ignore the score | S15 |
| R-19 | Unsustainable cadence | medium | M | time log | cadence from measured hours | lower cadence | creator |
| R-20 | Shorts misaligned with the channel | medium | M | standalone checklist | same dossier, same identity | rework | S14 |
| R-21 | Premature automation | high: tempting | M | prototype gate | no long-form before the prototype passes | stop and report | architecture |
| R-22 | Over-engineering | high | M | plan review | small phases, justified dependencies | cut | architecture |
| R-23 | Unsafe upload automation | low: no code path | H | code review | no upload code in Phases 1-8, approval record | remove | architecture |
| R-24 | Inauthentic-content perception (V-01) | medium: templated series risk | H | editorial QA | a distinct storyline and concept per video, original visuals | rework or pause | S05, S06 |
| R-25 | Made-for-kids misclassification (V-03) | low-medium: cartoon style | M | Studio check | adult/teen tone, checklist | correct the setting | S15 |
| R-26 | Kokoro timed path is untested (audit) | medium | M | Phase 5 test on the real model | real-model test, estimate fallback exists | use the loudness mouth | S09 |
| R-27 | Remotion licence or performance changes (V-04) | low-medium | M | licence check at install and at 5.0 | benchmark, skia fallback | switch renderer | Phase 4 |
