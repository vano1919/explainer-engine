# Production rules: how every Crossworld Theories video is made

The channel-wide procedure. It holds no rule text of its own: each rule has one home (linked), and this page says **in which
order they apply, what the creator has told us, and what enforces each one**. Topic-specific material (heroes, palette,
claims, look) lives in the episode folder; everything here applies to every topic, history, science or fantasy crossover.
Read it before starting any video; update the feedback log (section 3) whenever the creator gives a note.

## 1. Standing orders (the creator's, binding for every video)

1. **Entertainment first, facts second.** Dry wit, irony and situational humour; the science, history and constraints are told
   straight and never invented for a joke ([SCRIPTING_SPEC](SCRIPTING_SPEC.md) §8.1, UR-21).
2. **No generic, neutral or "safe" output.** Never a nature documentary, a picnic, anonymous "scientists", a closed ending or a
   flat read. Real, named people and real stakes ([UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) §E, D-40).
3. **One universe, the primary visual rule.** Every visual component (heroes, extras, hands, plates, props, every era and place) looks drawn by the same hand with the same thread of style; it overrides any conflicting instruction, and the `universe_thread` is in every image prompt (UR-22).
4. **Money is never a surprise.** Estimate before every paid call, state units, price and caps in the request, wait for a yes,
   stop at 80 % of any cap, finish with nothing running and the balance reported ([TOOL_STRATEGY](TOOL_STRATEGY.md),
   [COST_AND_TIME_MODEL](COST_AND_TIME_MODEL.md), CLAUDE.md invariants 1-2).
5. **The creator picks the picture provider for every batch** (D-50: paint plan -> approve -> run; on Gemini the tiers draft,
   standard, premium pick the model, D-52). Narration and sound effects come from ElevenLabs; music from ElevenLabs or a per-track
   verified free library (D-52); free procedural cues are allowed (D-54). **Library first** (creator 2026-10-20): background music,
   sound effects and reusable pictures are searched in the reusable libraries before anything new is generated, and new takes are
   registered back (OR-18, D-76; enforced by the ElevenLabs hook and PP-08).
6. **Look at the output before reporting it.** Open the contact sheet, listen to the test read, composite a sample; a green test
   is not acceptance (CLAUDE_EXECUTION_GUIDE step 5).
7. **Say what was and was not verified.** No legal or factual guarantee the sources do not give; a creator decision is recorded
   as a decision and its risk as a risk (RIGHTS_AND_FAIR_USE, invariant 5).
8. **Reply to the creator in Georgian**, with numbers (words, seconds, dollars), the decision needed and the next step.
9. **Upload each piece as soon as it passes** (creator, 2026-10-19: "whatever video or Short passes every test goes up to YouTube,
   not everything together"). The long video and each Short are staged one by one, unlisted, the moment that piece has passed its
   own tests (the seven-point test and QA for the video; render, frame look and loudness for a Short): `python -m
   explainer_engine.publish stage <episode> --only <id> --yes --confirm '<the creator's standing order, 2026-10-19>'`. No waiting
   for the batch, and no waiting for the creator to ask: the moment a piece passes, Claude posts a fresh sign-in link
   (`publish auth-url`) in the thread, and when the creator sends back the 127.0.0.1 address it runs `auth-finish` and uploads
   at once (creator, 2026-10-19: "it's ready, it passed every test: ask me to log in, upload, done"). A Short goes up only
   when `python -m explainer_engine.qa.short_format <file>` passes (vertical 9:16, at most 3 min; `production.shorts` refuses
   to hand on any other file), and its link is given as `youtube.com/shorts/<id>`, never `youtu.be`. Unchanged: never public (the creator clicks Public), the creator sets the thumbnail in Studio, sign-in is a fresh
   link per upload session (`publish auth-url` / `auth-finish`), and a piece that fails a test is fixed, not uploaded.
10. **Pictures and audio are approved together and run in parallel** (creator, 2026-10-20: "once the script is approved, approve
   the pictures and the audio together and start them together: the batch makes the pictures wait for nothing"). Right after the
   creator approves the finished script (OR-17), Claude asks ONE question that covers every paid asset of the video: the paint
   plans (provider per batch, D-50), the narration, the sound effects and the music, with one cost table and the caps they need.
   On the yes, the Gemini batch is submitted first (it takes minutes to hours) and the voice and sounds are made while it runs.
   Every step keeps its own estimate, ledger entry and gate; a cap at 80 % still stops and asks. Assets that depend on an earlier
   OK (a hero's first picture before that hero's later pictures and face sheet) are a second, smaller question.
11. **The first two parts are shown before the rest is rendered** (creator, 2026-10-20: "when the first 2 parts are rendered,
   join them and show me; I will watch and tell you what and how"). The render runs in chunks (ED-13, RULE-R1): Claude
   renders only the first two (`assemble --chunks 0:2`), joins them into one preview file, looks at it, sends it to the creator
   and waits. His notes become rules (with a test, OR-09) before the remaining chunks are rendered.
12. **Claude watches every render before the creator does** (creator, 2026-10-20: "why can't you watch and evaluate it
   yourself?", after the first Titans preview showed a bubble on the wrong face, faces swapping every 1-2 s and rings on empty
   wall). Before any render, preview or part is shown to the creator, Claude runs
   `python -m explainer_engine.qa.frame_review <timed.json> <video> --from S --to S --out <dir>` on it, opens every contact
   sheet it writes and looks at each frame itself, fixes what it finds (timing, beats, bubbles, pictures) and re-renders. A FAIL
   is never shown; each REVIEW is either fixed or named to the creator with its sheet. The checks and their thresholds live in
   `explainer_engine/qa/frame_review.py` (loudness: BP-50 through `qa/targets.py`).
   **The QA loop runs this after every two rendered chunks** (creator, 2026-10-20):
   `python -m explainer_engine.qa.loop <script> --read <read dir> --out <dir> --chunks A:B --pics <dir>` times the script,
   renders only chunks A:B, joins them, runs the frame review with the free pixel checks (`qa/pixels.py`: an unplanned cut
   or a frozen picture FAIL; camera jumps, jump cuts, black, a bubble over a face REVIEW) and the face-point check
   (`qa/face_points.py`, REVIEW), and writes `loop_report.json`: every finding classed *systemic* (fix the code, with a
   focused test) or *script* (fix the script), with the file that owns it. The loop never edits anything itself; the session
   fixes the owners and runs the same command again until no FAIL is left. A finding still there after 5 iterations stops
   the loop: report it to the creator. Its only paid allowance: at most 2,000 ElevenLabs credits per run, on its own, for
   re-reads of script lines it changed (`config/spend_caps.json` `allowances.qa_loop`, enforced by
   `core/ledger.Run.reserve_allowance` inside the run's ElevenLabs cap).
13. **A two-part sample before the rest** (creator, 2026-10-21): after the script approval, voice and pictures are paid for
   the first two parts only, stitched into one sample the creator watches; his notes are fixed and only his recorded word
   opens the rest ([OR-19](ORCHESTRATION.md), gate 6.5 below, `production/sample.py`).

## 2. The gates, in order (a video does not skip one)

Run `python -m explainer_engine.production_gate <episode folder>` to see every gate's state (PASS / BLOCKED / WAIT) and the next
action. Gates 3-7 spend money and need the creator's yes first.

| # | Gate | What must be true | Rules and tools |
|---|---|---|---|
| 0 | **Topic and claims** | research dossier, claim map, the episode rulebook (provisional, then final before the script; gate row `R`), rights check; the source/claim contract and independent editorial gate pass, then the creator approves the finished script (approval #1, recorded in `episode.script_approval`, [OR-17](ORCHESTRATION.md)) | [SCRIPTING_SPEC](SCRIPTING_SPEC.md) §1-5, crossover skill, `rights/ip_check.py` |
| 1 | **Script for the ear** | the first sentence is the hook in one of the forms of [BP-03](SOURCED_RULES.md) (a yes/no question rises best); short sentences; one stress word; open loop at every beat end; interjections where a person would say them; named heroes with archetype lines; humour from the situation; `narration_tts.txt` + plain `narration.txt` | skill `narration-script`, `scripting/narration_lint.py` 0 FAIL |
| 2 | **Voice test read** | first 45-60 s only (estimate first), the creator listens; then the full read, pace per BP-01 (one band for every document) | [AUDIO_SYSTEM](AUDIO_SYSTEM.md) (D-39), `audio/scribe_words.py`, `audio/pause_pad.py` |
| 3 | **Shot plan** | every shot has `stakes`, type A/B/C in rhythm, named heroes with emotional poses in every B, friction per beat, palette and one emotion per shot, figure style on every person/hand prompt, plates without people; cuts placed by the solver inside punctuated pauses | skill `shot-visuals`, [UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) UR-01..UR-22, `edit/shot_rules.check_shots` 0 FAIL |
| 4 | **Style bridge** | 6 test pictures, a sprite and a pod-painted hand and crowd in one frame, approved once per episode | UR-22, `look.style_bridge.approved` |
| 5 | **Sprites** | every hero and pose of the plan exists (sprite bank), keyed and graded | `sprite_needs.md`, `look.pose_bank`, [ASSET_SYSTEM](ASSET_SYSTEM.md) |
| 6 | **Pictures (pod)** | limit = units x measured seconds x margin; approval with price and caps; pushed even on failure; contact sheet reviewed by eye, bad pictures repainted | TMR `cloud/lint_manifest.py` (`picture_budget`, `fatal_before_push`), `cloud/job_speeds.json`, runbook R6 |
| 6.5 | **Two-part sample** | the sample's voice and pictures (first two segments, [OR-19](ORCHESTRATION.md)) are rendered and stitched; the creator watches, his notes are fixed and re-rendered; his recorded word (`production.sample approve`, bound to the script's sha256) opens paid generation for the rest | `production/sample.py`, PP-09, the ElevenLabs hook, gate 6.5 |
| 7 | **Full read and timings** | one paid read of the final text; Scribe words, coverage >= 97 %, pauses padded, `words.json` on the audio the mix uses; shot cuts recomputed | D-39, UR-12, `build_shots.py` 0 FAIL |
| 7.5 | **keyframes** | every keyframe of an animated episode passes the keyframe gate | [KEYFRAME_GATE](KEYFRAME_GATE.md) (docs/KEYFRAME_GATE.md, KG rules; log `qa_log.jsonl` in the episode folder); wired as production_gate rows keyframes/clips (P8 bundle; until they land the two CLIs are run by hand and their outputs kept with the episode) |
| 7.6 | **clips** | every generated clip passes `training/video_qa` (LT-5x rows and the CLIP container/audio rows; one video_qa JSON per clip kept in the episode folder) | `explainer_engine/training/video_qa.py`; wired as production_gate rows keyframes/clips (P8 bundle; until they land the two CLIs are run by hand and their outputs kept with the episode) |
| 8 | **Animatic and render** | GPU compositor (D-32), motion per UR-13, transitions UR-14, sound UR-15 | [RENDERING_ARCHITECTURE](RENDERING_ARCHITECTURE.md) |
| 9 | **Seven-point test, QA and approval #2** | every video passes all seven checks of section 6 (`qa/scorecard.py`), then technical and editorial QA; each piece that passes is staged unlisted at once (standing order 9: the creator's standing approval for unlisted staging); approval #2 is the creator's own click to Public | section 6, [QA_SPECIFICATION](QA_SPECIFICATION.md) |

For an episode with a `production_script.json` (D-43) the gate command reads what that flow writes (audit 2026-10-19):
the script (gate 0, PV rules with the picture folders), its voice text (1), `words.json` (2), the board on the real read (3),
hero references (4, PV-26), the paint plans in `pictures/plans` and their approvals in the run ledger (5, `--run run.json`;
the creator picks the provider for every batch) and the picture files (6). Day folders without a production script keep
the legacy reading of `shots.json` and `look.json`.

Order matters: no paid read, picture or music before the rulebook's `paid_assets` checkpoint passes (OR-12); a script is not paid-read before gate 1 is clean; pictures are not painted before the style bridge (gate 4) and
the sprite plan (gate 5); the full read waits for the creator's yes on the test read; and past the sample's own assets,
nothing is paid before the creator's word on the stitched two-part sample (gate 6.5, [OR-19](ORCHESTRATION.md)).

## 3. Feedback log (every creator note, its cause, its rule, what enforces it)

| Date | The creator said | Cause | Rule | Enforced by |
|---|---|---|---|---|
| 2026-10-16 | The hook must ask a question (widened to BP-03's hook forms, D-59); first 30 s fast; ABC shots; cuts only in pauses; fixed durations; Ken Burns <= 1.15; >= 90 % hard cuts | no common edit grammar (the reference test video broke most of it) | UR-01..UR-15 (D-37) | `shot_rules` |
| 2026-10-16 | Keep the drawn style; the topic sets the colour range; every shot has one emotion through light and colour | hyper-realistic modifier rejected | UR-07..UR-10 | `shot_rules`, `moods.json`, `look.json` |
| 2026-10-16 | The narrator is too generic, too stable and flat | Kokoro blends and pitch shifts stay generic | ElevenLabs voice Clyde (D-39); Kokoro retired (D-39), drafts are ElevenLabs first takes (skill elevenlabs-voice) | [AUDIO_SYSTEM](AUDIO_SYSTEM.md) |
| 2026-10-16 | Write for an expressive read; mysterious, curious, funny | plain documentary prose | SCRIPTING_SPEC §8 | `narration-script` skill |
| 2026-10-16 | The read is slow and monotone; the question is not asked like a question; stress on wrong words; add hmm / oh / eh where natural; study similar videos; write a big rules skill | wh-question hook falls; ellipses slow; no stressed word; no interjections; no open loops | N-01..N-10 | `narration_lint`, skill |
| 2026-10-19 | Upload whatever video or Short passes every test right away, not everything together | Shorts waited for the long video and the whole batch | standing order 9 | `publish stage --only <id>` (per-piece state in `publish/youtube_state.json`) |
| 2026-10-20 | Approve pictures and audio together after the script and start them together | the Titans pictures were asked for only after the voice was recorded, and the batch waited | standing order 10 | the orchestrator's single paid-assets question; each step's own gate |
| 2026-10-20 | Dialogue frame: the blurred scene with the big face (variant A of four), the background a little more blurred | at blur 0.014 the other heroes behind the face still read as a second focus | `faces.BLUR` 0.024 | `test_face_sheets.py::test_dialogue_backdrop_blur_is_the_creators_choice` |
| 2026-10-20 | Render the first two parts, join them and show me before the rest | a whole video was rendered before the creator saw any of it | standing order 11 | the orchestrator's render phase |
| 2026-10-20 | The first preview had errors Claude should have seen itself: a bubble across a cut into a face close-up, one speaker's words on another's face, faces swapping every 1-2 s, rings on empty wall | nothing looked at the rendered frames; the bubble layout and the close-ups were checked separately, never together on the timeline | standing order 12 | `qa/frame_review.py` (exit 1 on FAIL), `tests/unit/test_frame_review.py` |
| 2026-10-16 | Humour must never touch the facts; credible science | joke-driven rewrites risk false statements | SCRIPTING_SPEC §8.1, UR-21 | skill, editorial review |
| 2026-10-16 | Pictures too generic: no named heroes, no fear, clichés of the primitive; real figures by name in every topic | prompts described places; B shots faceless; idle sprite poses; empty plates | UR-16..UR-21 (D-40) | `check_stakes`, `stakes.json`, skill `shot-visuals` |
| 2026-10-16 | The man seen from behind and the main hero are different kinds of people; everything must be one world | UR-07 asked for natural proportions next to caricatures; two generators | UR-22; style bridge | `check_stakes`, `look.figure_style` |
| 2026-10-16 | Primary rule: one universe. Environment and inhabitants share one design language, one palette and shading; a time-travelling character never breaks the style; it overrides any conflicting prompt and goes into every image prompt | the look held a style suffix but no thread tying characters, props and places together | UR-22 (primary section of the rule base) | `check_stakes`, `compose_prompt`, `universe.sprite_prompt` / `assert_thread`, `shot-visuals` |
| 2026-10-16 | Pictures: "children on an excursion"; wants era-true worlds in the cinema's visual language, one look everywhere, Gemini where it is worth it | 1.6x heads and storybook words, two light keys, no costumes, style held by words only | D-41, UR-22..UR-26, look v2, era codex | `world/`, `prompt_v2`, `visual_judge`, `finish/grade` |
| 2026-10-16 | Generate a full test video and pass it through seven checks (narration, sound, topic fit, cliché fit, consistency, editing, fun); a failure is investigated and the general rules are fixed | no end-to-end acceptance existed | section 6 | `qa/scorecard.py` |
| 2026-10-16 | (found in the first test video, Day 1 v5) campfires and smoke in the first beats, before anyone could make fire | the prompt wrote "woodsmoke" and "no fire" (naming it paints it); no story state | UR-27 story state: `not_yet` per beat, positive phrasing, judge question `too_early` | `resolver.not_yet`, `check_text`, `visual_judge` |
| 2026-10-16 | (found) tents, daggers and bones on the ground | the prompt carried the flat list "hides, flint, bone" | no flat material lists in prompts | `prompt_v2.compose` |
| 2026-10-16 | (found) the picture did not match the words: mean 3.2 s and worst 9.3 s late | the shot plan used anchors written for an earlier read; shots need their minimum duration | UR-28 plan fits the read | `shot_rules.anchor_spacing`, solver may drop shots by cost |
| 2026-10-16 | (found) loudness -25 LUFS, bed and music about 35 dB under the voice, cut sounds on spoken words | peak-normalised beds, 0.8 s whooshes at cuts | loudness -14 LUFS, bed and music about 20 dB under the voice, a cut sound ends before the next word (since D-59 the distances are [BP-52](SOURCED_RULES.md)'s, in LU on the stems; the cut sound is [BP-66](SOURCED_RULES.md)) | `assemble.build_audio`, `scorecard` check 2 |
| 2026-10-16 | (found) the visual judge failed 46 of 46 pictures, then 32, then 22 | visitor clothes counted as anachronisms, text answers noisy, temperature above 0 | judge prompt names the intended visitors; temperature 0; every "true" must say why; `one_light` is advisory | `visual_judge`, `GeminiClient.judge` |
| 2026-10-16 | Why will the 35 lost pictures not be lost again? Make the rule flexible | stage limit copied from a smaller job; fatal stop skipped the push | limits from measured speeds; push before fatal | TMR lint, `job_speeds.json`, runbook R6, R-29 |
| 2026-10-16 | How many words and pictures for 8-12 minutes? Is the animation used? | planning numbers were not written down; the compositor is not built | section 4 below; D-32 | this page |
| 2026-10-16 | The voice should be more emotional; this voice actor does not fit (annoying); livelier, but not very young | Clyde is a vintage radio announcer; the read had few emotional turns | new narrator chosen from 3 middle-aged storytellers by the creator; more audio tags at turns (gasps, whispers, sighs) in `narration_tts.txt` | creator's ear; test read before the full read |
| 2026-10-16 | Pictures and text often do not match and are illogical (the fire was already burning when the magnifier was taken); two causes: logic and too frequent picture changes | `not_yet` lifted for the whole fire beat; 44 pictures in 3 min; wrong hero and wrong prop in two pictures | UR-29, UR-30, UR-31 (D-42) | `edit/board.py` |
| 2026-10-16 | Keep animation where it fits: imitate a conversation on one picture with speech bubbles, the other answers | one picture per sentence | UR-31 bubbles | `finish/bubbles.py`, `edit/board.py` |
| 2026-10-16 | The pictures are good but too expensive; use local models: Gemini gives references, RunPod paints in its style | Gemini painted every picture ($3.6 for 67) | D-42 routing: Gemini references, Qwen-Image-Edit-2511 on a pod | `cloud/gen_ref_pictures.py` |
| 2026-10-16 | Where there are world sounds (hits, friction) lower the music with millisecond fades so it is not noise; the dip must not sound like a cut | music only ducked under the voice | UR-32 | `audio/duck.py` |

| 2026-10-16 | From 3:17 almost to the end another voice actor seems to read | one ElevenLabs v4 generation of the whole read (2,917 characters, 223 s) drifted: darker, duller timbre from ~190 s (tilt -4 dB, centroid -16 % off the read's median) | reads in chunks of whole segments, at most 900 characters, same voice and settings, with the text before and after; every read is checked for timbre drift before use | `script.tts_chunks`, `compile` writes `tts_chunks.json`, `production words` joins chunk reads, `audio/voice_check.py` (VOICE-1 REVIEW) |
| 2026-10-16 | The voice sounds somewhat unstable | per-sentence loudness swung 9 dB (std 2.1 dB) | a slow gain rider (+4/-5 dB, pauses untouched) | `audio/level.py` in `production/assemble.py` |
| 2026-10-16 | (found) a voice test cost 501 credits, quoted as 349 | the price was guessed from an earlier, shorter text | `estimate_only` before every paid ElevenLabs call, the estimate is what is quoted | this rule; spend log in PROGRESS |
| 2026-10-16 | (found) the slower voice left six stretches over 9 s with nothing new on screen | the shot plan was timed at 140-158 wpm, the read ran slower with its pauses | after every new read, `production time` again; dead holds are fixed with shots, never by speeding the voice | PV-24 RHYTHM-3 |
| 2026-10-16 | (found) a re-run of the one-off `make_script.py` overwrote compiled prompts and the manual shots | the one-off was still runnable | the script is edited directly; one-off builders refuse to run without `--force` | `day1_v7/make_script.py` |
| 2026-10-16 | (found) a shell chain started a 2K render on a timing with 3 FAIL, and a second render wrote into the same folder | `assemble` trusted its caller; no lock; the video file was written in place | `assemble` refuses a timing with FAIL, locks its folder, writes `video.part.mp4` and renames it when done | `production/assemble.py`, test |
| 2026-10-16 | (found) RunPod had no 48 GB card five times in a row | capacity | never widen the price on our own; ask; the creator allowed Gemini for the three Day 1 pictures once ($0.16) | RUNBOOK R-rules; PROGRESS |
| 2026-10-16 | When a run fails, find the cause, document it and push the fix to the repo so it cannot repeat | the Week 1 pod stopped on a guessed model size (58.0 GB against a real 57.7 GB) and a 60 GB volume | a failure is closed only when its cause is read from evidence (ntfy history, listing), fixed in the repo, covered by a test and written in the incident log | TMR `docs/INCIDENTS_RUNPOD.md`, `tests/unit/test_conductor.py::test_models_manifest_sizes_and_dry_run` |
| 2026-10-16 | Episode 1 is one whole video: what happens to the 100 minds after a day, a week, a month, a year, 10 years, 100 years, then compare with the real record; lean on real science and logic, be creative; periods do not get equal time; a hook closes every period; tone: scientific what-if, 20 % humour, 40 % drama, 40 % doubt and telling (the humour share is superseded by BP-09's joke density, D-59) | the earlier plan treated Day 1 as a separate video and gave every period the same length | SR-01..SR-08, PV-27, skills `science-grounding`, `time-jump-episode` | [ORCHESTRATION](ORCHESTRATION.md), `validate` PV-27 |
| 2026-10-16 | Shorts advertise the video: a 3-second question hook, then the most surprising scene, own text and script, 9:16 crops that keep faces on the heroes | Shorts had no template | SH-01..SH-04, PV-28, skill `shorts-for-video` | `validate` PV-28 |
| 2026-10-16 | Run alone overnight in phases so mistakes show early; hard stops that lose nothing; Gemini for this video's pictures with a US$6 new cap; reuse pictures where the story fits and plan it in the script | long unattended runs had no ledger; pods failed four times | OR-01..OR-09, D-44, agent `orchestrator`, SR-08 | `core/ledger.py`, `tests/unit/test_ledger.py` |
| 2026-10-21 | After the script, do not generate the whole video's audio and pictures any more: make the first two parts, I watch, I correct with my notes, and only then generate the audio and pictures of the rest | the Syndicate Wars and titans flows paid for full voice and picture batches before the creator saw one rendered frame; his notes then cost re-reads and repaints | [OR-19](ORCHESTRATION.md), gate 6.5, PP-09 | `production/sample.py`, `paint.preflight`, the ElevenLabs hook, `production_gate`, `tests/unit/test_sample_gate.py` |
| 2026-10-17 | The 2K render kept dying (five times) and the video was not finished; fix it, and write the rule so it does not happen again | a long render was started as a detached process (`setsid nohup`) with no tool task attached; the sandbox stopped the machine after the session went quiet, and every process died with it (timing matched the creator's messages; not proven by a log) | RULE-R1: a render longer than ~10 minutes runs as a tracked background task of the session (never `setsid`, never a detached `nohup`); it is written in chunks (ED-13); each run draws its own chunk range (`assemble --chunks A:B`) until all chunks exist, then joins once; the session keeps a wake-up timer while it runs and says so in plain words; a stale `.assemble.lock` is removed only after its pid is confirmed gone | ED-13, `assemble --chunks`, `tests/unit/test_chunked_render.py`; the rule itself is procedural (OR-09) |

## 4. Planning numbers for a video length (measured on Day 1, 2026-10-16)

Measurements, not rules: the binding numbers are the BP rules of [SOURCED_RULES](SOURCED_RULES.md) (D-59).

| | 8 min | 10 min | 12 min | Source |
|---|---|---|---|---|
| words at the BP-01 target pace | about 1,360 | about 1,700 | about 2,040 | v3/v4 test reads 155-168 wpm; the first read was 140; target raised to 170 by D-49 |
| shots at 3.85 s (a Day 1 measurement, not a target: BP-40 caps the average at 10 pictures a minute) | about 125 | about 155 | about 187 | Day 1: 46 shots in 177 s |
| unique pictures at 0.85 per shot | about 115 | about 140 | about 170 | Day 1: 42 pictures for 46 shots |
| pod time at 22.7 s per picture | about 45 min | about 55 min | about 65 min | 35 pictures in 793 s on an RTX 4090 |
| pod cost at $0.89/h | about $0.7-0.9 | about $0.9-1.1 | about $1.1-1.4 | add about $0.1 boot; limit = pictures x 30 s x 1.25 |
| ElevenLabs read (credits; the creator has [the plan recorded in D-52 (Creator)](DECISIONS_AND_OPEN_QUESTIONS.md) and counts credits, 1 credit about $0.00018) | about 6,800 credits | about 8,500 credits | about 10,200 credits | 2,337 credits for 2,550 characters (Day 1); add about 1,000 for the test read. The earlier dollar rows were about twice too high |
| hero sprites | the poses the plan names | | | about $0.067 each, reusable across videos |

These are estimates for planning; the estimate before each paid call is the number that counts.

## 4a. Cost is counted in credits
The creator has [the ElevenLabs plan recorded in D-52 (Creator)](DECISIONS_AND_OPEN_QUESTIONS.md) and counts credits, not dollars: every request for approval states credits first (read
with `estimate_only`; 1 credit is about $0.00018) and the dollar equivalent second. Gemini pictures are dollars from the Gemini
key (cap $10 in total, stop at 80 %); RunPod is dollars. Estimates and charges can differ (Scribe was estimated at 61 credits
and charged 998 on 2026-10-16; sound effects were estimated at 55 and charged 17 or 67): the ledger records the charge.

## 5. What is per topic and what is universal

- **Per topic (the episode folder):** research and claim map, narration text, `look.json` (palette per phase, heroes,
  archetypes, pose bank, figure style, style bridge status), shot plan, pictures, sprites for new heroes.
- **Universal (this repository):** the gates above, UR-01..UR-22, N-01..N-10, the stakes vocabulary, the sound library, the
  the channel voice recorded in config/channel_voices.json (card C10), the pod procedure and its money rules, the cost ledger. A new topic starts from a copy of an episode `look.json`
  with `rule_base: 2` and fills in its own heroes, palette and claims.

## 6. The seven-point test (creator, 2026-10-16: every video passes all seven; a failure is investigated, never waved through)

Run on a production script with `python -m explainer_engine.qa.scorecard <episode folder>` (D-59: before this the test had no command line on
the D-43 flow and ran only on the legacy day folders). The numbers it checks are the BP rules.

`explainer_engine/qa/scorecard.py` gathers the evidence; the creator decides the rows marked "creator decides".

| # | Check | What is measured or looked at |
|---|---|---|
| 1 | Narration tone and its sync with the video | words per minute (BP-01), every cut inside a punctuated pause (UR-12), questions per minute; the creator listens for tone, stress and question intonation |
| 2 | Sound effects and their sync | a synced effect lands on its frame, never early (BP-54); a cue on a word is a designed cue, a whoosh on a word is not; background under the voice per BP-52 (LU on the stems); loudness and true peak per BP-50; the creator listens: natural and helpful, not cartoon placeholders |
| 3 | Pictures fit the topic and its world | the visual judge (adults, no object from the world's `absent` list, no people in plates, one light, mood), 0 FAIL |
| 4 | Pictures fit the topic's cliché expectations | the era codex `cliches` and screen codes; the creator looks: does it read as the genre the audience knows |
| 5 | Pictures fit each other | luma, saturation and warmth outliers across the episode, one engine, one look thread, one grade; side-by-side sheet |
| 6 | Editing against general standards | UR-01..UR-15 0 FAIL, durations A/B/C, hard cuts by default ([BP-31](SOURCED_RULES.md)), first 30 s rhythm, motion limits |
| 7 | The whole video: fun, interesting, easy to follow, sticky | open loop at each beat end, question rhythm, shots per minute; the creator watches it once without pausing |

**Failure loop.** A FAIL (or a "no" from the creator) on any row: (1) find the cause with evidence (the prompt, the timing, the
sound file, the rule that allowed it), not a guess; (2) fix the **general** rule, check or tool so no video can repeat it, and
log the creator's note in section 3; (3) run the failed step again, then the checks again; (4) three failures on the same row
stop the run and the creator is asked. Cost of the reruns is counted against the approved caps.
