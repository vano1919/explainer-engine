# Orchestration: how an episode is run end to end, alone, with money and stops under control

Canonical for the autonomous run of a whole episode (creator, 2026-10-16: "fully autonomous, phases, find mistakes early, a
hard cap, a stop must never lose material"). The agent that follows it is `.claude/agents/orchestrator.md`; the code that
enforces the money and stop rules is `explainer_engine/core/ledger.py`. Gates of one video stay in
[PRODUCTION_RULES](PRODUCTION_RULES.md); the script format in [PRODUCTION_SCRIPT](PRODUCTION_SCRIPT.md).

## Rules (OR-xx)

| ID | Rule | Enforced by |
|---|---|---|
| OR-01 | **Phases with gates.** Cheap, free checks come first; the first paid call is a one-item test (one read chunk, one picture); the expensive batch starts only after the test passed its check. A failed gate stops the run at that phase. | orchestrator, `ledger.Run.phase` |
| OR-02 | **Hard caps in code.** Every paid service has a cap written in the run ledger before the run (`Run.cap`), a charge is recorded before the call (`Run.reserve`) and refused past 80 % of the cap; a refusal ends the phase safely, it never raises through a half-finished batch. | `core/ledger.py` |
| OR-03 | **A stop loses nothing.** Each item (a read chunk, a picture) is written to disk and recorded in `run.json` as soon as it is paid; a re-run skips recorded items, so an interruption, a cap stop or a crash resumes at the first missing item. Paid results are never re-bought. | `ledger.Run.done`, `Run.pending` |
| OR-04 | **Ordered fallbacks, not retries.** A failed paid call is not repeated blindly. Three failures on the same item or phase stop it: write the cause from evidence, fix it in the repo with a test, record it in the feedback log, then continue with the other phases that do not depend on it. | `ledger.Run.fail` |
| OR-05 | **Nothing public.** No upload, no publish, no comment on the channel. The run ends with files and a report. | invariant 4 |
| OR-06 | **No pod without a spoken yes.** A pod needs the creator's approved price and time cap for that pod, `rp.py guard`, and a sweep before and after. A cap or a surprise near 80 % stops acting and waits. | TMR money rules |
| OR-07 | **Look at the output.** Every phase ends by opening what it made (contact sheet, listening to chunk joins, a sample frame) and writing one line of evidence in the report, never only "tests pass". | report |
| OR-08 | **Morning report.** One short Georgian message: files and links, minutes, credits and dollars per service against the caps, balances read, what failed and what was fixed, what needs the creator. | orchestrator |
| OR-09 | **Update the repo first.** A creator note becomes a rule, a check or a skill line, with a test where it can be tested, before the next production phase uses it. | feedback log |

## Series structure (SR-xx) for time-jump episodes ("what happens after a day, a week, a month, a year, 10 years, 100 years")

| ID | Rule |
|---|---|
| SR-01 | One video, one question the whole episode answers; the periods are its chapters. The final chapter compares the story with the real record ("would this group have outrun real history?"). |
| SR-02 | Periods do **not** get equal time. A period earns minutes by how many surprises it carries; a stretched period is cut. Length is a result, not a target. |
| SR-03 | Every period ends on a hook that is the question of the next period ("and a month later?"). The last chapter ends on the creator's open question about the next episode only if the creator set one. |
| SR-04 | **Science grounded, creative in the telling.** Established facts and models (historic population and technology growth, the knowledge-versus-materials problem, energy, tools, medicine) carry the story; each "what if" step says what is established, what is reasoned and what is a guess ([skill science-grounding](../.claude/skills/science-grounding/SKILL.md)). The counterfactual is a reasoned argument, not a prophecy. |
| SR-05 | Knowledge is not the only limit. Each period names its real bottleneck (people, materials, tools, food, disease, energy, trust), because the interesting argument is whether knowledge alone speeds progress. |
| SR-06 | After 100 years the original people are gone; what remains is their effect on the world (schools, written knowledge, tools, institutions, descendants) and it is shown. |
| SR-07 | Tone mix: about 40 % drama, 20 % humour, 40 % doubt and curious telling. Style: "scientific what-if". Humour never touches a fact (UR-21). |
| SR-08 | The script plans reuse: for each period it lists which pictures are unique, which repeat with a different crop or zoom, and which dialogue scenes share one picture with speech bubbles. Reuse is chosen when it fits the story, never to save money against it. |

## Shorts (SH-xx)

| ID | Rule |
|---|---|
| SH-01 | Shorts exist to advertise the video: a **hook of one question in the first 3 seconds**, then 25-50 s of the most surprising scene, then a line that points to the video. |
| SH-02 | A Short has its own text and script (`shorts` block of the production script); its voice is the episode's voice; pace may be raised by at most 8 % only when the timbre check passes, otherwise left as it is. |
| SH-03 | Pictures are the video's pictures, cropped to 9:16 around the named heroes and the action (the crop centre is set per shot); faces are never cut. |
| SH-04 | Each Short opens with a fact or a "did you know" that is true and sourced by the claim map. |
| SH-05 | **A set of Shorts tells different scenes.** For one video's set (up to 10 planned for the 8-12 min video) every Short opens its own question and tells its own scene: no two hooks alike, no body line told in two Shorts, no two Shorts on mostly the same pictures (PV-28). Which angle wins is measured per Short (viewed vs swiped away, [PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md)), never assumed. |

## Money ledger of a run
`jobs/<run>/run.json` holds caps, reservations, paid items and failures; the dollar and credit totals of the report are read from
it. Caps for the 2026-10-16 night run: Gemini US$6.00 new spend (pictures and judge), ElevenLabs credits up to 100,000 on the
account with a plan of about 25,000 for this episode, vidIQ up to 40 credits, RunPod none.
