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
| OR-11 | **One episode rulebook binds every step.** After the topic and format are known the `episode-standards-director` writes `episode_rules.json` (provisional), finalises it before the script is committed, and the orchestrator passes `python -m explainer_engine.standards brief <rules> --role <role>` to research, script, voice, image, music, sound, edit, metadata and QA; no step invents its own legal policy, licence assumption or art direction; conflicts come back to the orchestrator, which decides or asks the creator. | `standards/rulebook.py`, [EPISODE_STANDARDS](EPISODE_STANDARDS.md) ES-18 |
| OR-12 | **Rechecks at the irreversible steps.** The rulebook gate runs at `script_lock`, before any paid or high-cost generation (`paid_assets`) and at `final_qa`; a changed script or rulebook re-checks only the affected rules and stamps again; a BLOCK or an undecided REVIEW stops that step, not the whole episode. | `standards gate`/`stamp` (ES-16), `production/paint.py`, `production_gate` |
| OR-13 | **Every executor has a contract** (table below): it receives the slice of the plan it executes (shot, line, sound event), the rulebook brief for its role, references and limits, and returns its output with provenance; it never invents another scene, voice direction or art direction. | this table, `standards brief` |
| OR-14 | **Code before prose.** A rule that can be checked by code is checked by code: schemas, validators (PV, ES, ENG, HY), the run ledger, and the PreToolUse hook on the ElevenLabs connector (`.claude/settings.json`). | tests |
| OR-09 | **Update the repo first.** A creator note becomes a rule, a check or a skill line, with a test where it can be tested, before the next production phase uses it. | feedback log |


| OR-10 | **Independent editorial gate before spending.** A new production script must carry the source/claim contract and each narration line's kind. The independent review must match the exact script SHA-256 and meet the existing rubric thresholds. A FAIL or unresolved REVIEW stops paid narration and asset creation; any script edit invalidates the review. The paid image CLI (`production.paint`) enforces this gate itself; `--estimate` and collecting an already-paid batch remain available without a new spend. | `production.editorial_gate`, `production_gate.py`, `CHATGPT_WORKFLOW.md` |

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
| SH-01 | Shorts exist to advertise the video: a **hook of one question in the first 3 seconds** (one statement for the `anti_intuition` and `pov_you` styles, SS-05 in [STORY_ENGINE](STORY_ENGINE.md)), then 25-50 s of the most surprising scene, then a line that points to the video. |
| SH-02 | A Short has its own text and script (`shorts` block of the production script); its voice is the episode's voice; pace may be raised by at most 8 % only when the timbre check passes, otherwise left as it is. |
| SH-03 | Pictures are the video's pictures, cropped to 9:16 around the named heroes and the action (the crop centre is set per shot); faces are never cut. |
| SH-04 | Each Short opens with a fact or a "did you know" that is true and sourced by the claim map. |
| SH-05 | **A set of Shorts tells different scenes.** For one video's set (up to 10 planned for the 8-12 min video) every Short opens its own question and tells its own scene: no two hooks alike, no body line told in two Shorts, no two Shorts on mostly the same pictures (PV-28). Which angle wins is measured per Short (viewed vs swiped away, [PUBLISHING_AND_ANALYTICS](PUBLISHING_AND_ANALYTICS.md)), never assumed. |

## Executor contracts (OR-13)

| Executor | Inputs and source of truth | Tools and models | Output | Constraints and checks | Budget and failure limits | Returns |
|---|---|---|---|---|---|---|
| research (skill `science-grounding`) | topic, rulebook brief `research` | web search and fetch, vidIQ within cap | claim map, `story_hypotheses.json` | sources dated, labels established/model/reasoned/guess; HY-0..HY-4 | vidIQ cap in the ledger | URLs, access dates, what was not verified |
| script (skills `narration-script`, `time-jump-episode`, `crossover-episode`) | selected hypothesis, claim map, brief `script` | none paid | `production_script.json` | PV-01..PV-42, narration lint, engagement gate | free | validator output |
| voice (skill `elevenlabs-voice`) | the script's chunks (`tts_chunks.json`), brief `voice` | ElevenLabs `eleven_v4`, one take | read files in the episode folder | EL-01..EL-12, hook, `voice_check`, coverage >= 97 % | estimate first; ledger cap; 3 failures stop a chunk | credits per chunk, files, checks |
| image (`production/paint.py`, skill `shot-visuals`) | the shot's picture spec (subject, heroes, props, refs, tier), compiled prompt, brief `image` | Gemini batch tier only (D-52) | PNG per picture id | PV-05..PV-11, PV-26, PV-40, visual judge, contact sheet by eye | ledger cap, stop at 80 %; repaint at most twice | batch name, cost, file per id |
| music and sound (`audio/sfx_library.py`, AUDIO_SYSTEM) | the script's audio events with purpose, brief `music`/`sound` | library first; ElevenLabs `eleven_music_v2_5`, `eleven_text_to_sound_v2`, one take | library record per asset | PV-29, PV-41, licence record (ES-09), `qa/targets.py` | estimate first; hook | prompt, model, parameters, duration, cost, licence basis |
| edit and mix (`production time`/`assemble`, skills `editing-style`, `video-editing-architect`) | timed script from the real read | ffmpeg, our code | preview, final video | ED-01..ED-12, PV-20..PV-31, `qa/targets.py` | free | measurements, frames and joins looked at |
| metadata and QA | final video, rulebook, claim map | vidIQ within cap | metadata draft, QA report | Q-T, Q-E, `standards gate --at final_qa`, disclosure `upload_action` | vidIQ cap | report; nothing uploaded |

## Money ledger of a run
`jobs/<run>/run.json` holds caps, reservations, paid items and failures; the dollar and credit totals of the report are read from
it. Caps for the 2026-10-16 night run: Gemini US$6.00 new spend (pictures and judge), ElevenLabs credits up to 100,000 on the
account with a plan of about 25,000 for this episode, vidIQ up to 40 credits, RunPod none.
