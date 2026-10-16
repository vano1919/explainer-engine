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
5. **Pictures of one episode come from the local pod; Gemini only for reusable assets** (cast sprites, props, thumbnail
   elements) (D-36).
6. **Look at the output before reporting it.** Open the contact sheet, listen to the test read, composite a sample; a green test
   is not acceptance (CLAUDE_EXECUTION_GUIDE step 5).
7. **Say what was and was not verified.** No legal or factual guarantee the sources do not give; a creator decision is recorded
   as a decision and its risk as a risk (RIGHTS_AND_FAIR_USE, invariant 5).
8. **Reply to the creator in Georgian**, with numbers (words, seconds, dollars), the decision needed and the next step.

## 2. The gates, in order (a video does not skip one)

Run `python -m explainer_engine.production_gate <episode folder>` to see every gate's state (PASS / BLOCKED / WAIT) and the next
action. Gates 3-7 spend money and need the creator's yes first.

| # | Gate | What must be true | Rules and tools |
|---|---|---|---|
| 0 | **Topic and claims** | research dossier, claim map, rights check; the creator approves the script (approval #1) | [SCRIPTING_SPEC](SCRIPTING_SPEC.md) §1-5, crossover skill, `rights/ip_check.py` |
| 1 | **Script for the ear** | hook is a yes/no question by 5 s; short sentences; one stress word; open loop at every beat end; interjections where a person would say them; named heroes with archetype lines; humour from the situation; `narration_tts.txt` + plain `narration.txt` | skill `narration-script`, `scripting/narration_lint.py` 0 FAIL |
| 2 | **Voice test read** | first 45-60 s only (estimate first), the creator listens; then the full read, pace 155-175 wpm | [AUDIO_SYSTEM](AUDIO_SYSTEM.md) (D-39), `audio/scribe_words.py`, `audio/pause_pad.py` |
| 3 | **Shot plan** | every shot has `stakes`, type A/B/C in rhythm, named heroes with emotional poses in every B, friction per beat, palette and one emotion per shot, figure style on every person/hand prompt, plates without people; cuts placed by the solver inside punctuated pauses | skill `shot-visuals`, [UNIVERSAL_RULE_BASE](UNIVERSAL_RULE_BASE.md) UR-01..UR-22, `edit/shot_rules.check_shots` 0 FAIL |
| 4 | **Style bridge** | 6 test pictures, a sprite and a pod-painted hand and crowd in one frame, approved once per episode | UR-22, `look.style_bridge.approved` |
| 5 | **Sprites** | every hero and pose of the plan exists (sprite bank), keyed and graded | `sprite_needs.md`, `look.pose_bank`, [ASSET_SYSTEM](ASSET_SYSTEM.md) |
| 6 | **Pictures (pod)** | limit = units x measured seconds x margin; approval with price and caps; pushed even on failure; contact sheet reviewed by eye, bad pictures repainted | TMR `cloud/lint_manifest.py` (`picture_budget`, `fatal_before_push`), `cloud/job_speeds.json`, runbook R6 |
| 7 | **Full read and timings** | one paid read of the final text; Scribe words, coverage >= 97 %, pauses padded, `words.json` on the audio the mix uses; shot cuts recomputed | D-39, UR-12, `build_shots.py` 0 FAIL |
| 8 | **Animatic and render** | GPU compositor (D-32), motion per UR-13, transitions UR-14, sound UR-15 | [RENDERING_ARCHITECTURE](RENDERING_ARCHITECTURE.md) |
| 9 | **Seven-point test, QA and approval #2** | every video passes all seven checks of section 6 (`qa/scorecard.py`), then technical and editorial QA, the review bundle and the creator's recorded approval before any upload | section 6, [QA_SPECIFICATION](QA_SPECIFICATION.md) |

Order matters: a script is not paid-read before gate 1 is clean; pictures are not painted before the style bridge (gate 4) and
the sprite plan (gate 5); the full read waits for the creator's yes on the test read.

## 3. Feedback log (every creator note, its cause, its rule, what enforces it)

| Date | The creator said | Cause | Rule | Enforced by |
|---|---|---|---|---|
| 2026-10-16 | The hook must ask a question; first 30 s fast; ABC shots; cuts only in pauses; fixed durations; Ken Burns <= 1.15; >= 90 % hard cuts | no common edit grammar (the reference test video broke most of it) | UR-01..UR-15 (D-37) | `shot_rules` |
| 2026-10-16 | Keep the drawn style; the topic sets the colour range; every shot has one emotion through light and colour | hyper-realistic modifier rejected | UR-07..UR-10 | `shot_rules`, `moods.json`, `look.json` |
| 2026-10-16 | The narrator is too generic, too stable and flat | Kokoro blends and pitch shifts stay generic | ElevenLabs voice Clyde (D-39); Kokoro only for drafts | [AUDIO_SYSTEM](AUDIO_SYSTEM.md) |
| 2026-10-16 | Write for an expressive read; mysterious, curious, funny | plain documentary prose | SCRIPTING_SPEC §8 | `narration-script` skill |
| 2026-10-16 | The read is slow and monotone; the question is not asked like a question; stress on wrong words; add hmm / oh / eh where natural; study similar videos; write a big rules skill | wh-question hook falls; ellipses slow; no stressed word; no interjections; no open loops | N-01..N-10 | `narration_lint`, skill |
| 2026-10-16 | Humour must never touch the facts; credible science | joke-driven rewrites risk false statements | SCRIPTING_SPEC §8.1, UR-21 | skill, editorial review |
| 2026-10-16 | Pictures too generic: no named heroes, no fear, clichés of the primitive; real figures by name in every topic | prompts described places; B shots faceless; idle sprite poses; empty plates | UR-16..UR-21 (D-40) | `check_stakes`, `stakes.json`, skill `shot-visuals` |
| 2026-10-16 | The man seen from behind and the main hero are different kinds of people; everything must be one world | UR-07 asked for natural proportions next to caricatures; two generators | UR-22; style bridge | `check_stakes`, `look.figure_style` |
| 2026-10-16 | Primary rule: one universe. Environment and inhabitants share one design language, one palette and shading; a time-travelling character never breaks the style; it overrides any conflicting prompt and goes into every image prompt | the look held a style suffix but no thread tying characters, props and places together | UR-22 (primary section of the rule base) | `check_stakes`, `compose_prompt`, `universe.sprite_prompt` / `assert_thread`, `shot-visuals` |
| 2026-10-16 | Why will the 35 lost pictures not be lost again? Make the rule flexible | stage limit copied from a smaller job; fatal stop skipped the push | limits from measured speeds; push before fatal | TMR lint, `job_speeds.json`, runbook R6, R-29 |
| 2026-10-16 | How many words and pictures for 8-12 minutes? Is the animation used? | planning numbers were not written down; the compositor is not built | section 4 below; D-32 | this page |

## 4. Planning numbers for a video length (measured on Day 1, 2026-10-16)

| | 8 min | 10 min | 12 min | Source |
|---|---|---|---|---|
| words at 165 wpm | about 1,320 | about 1,650 | about 1,980 | v3/v4 test reads 155-168 wpm; the first read was 140 |
| shots at 3.85 s | about 125 | about 155 | about 187 | Day 1: 46 shots in 177 s |
| unique pictures at 0.85 per shot | about 115 | about 140 | about 170 | Day 1: 42 pictures for 46 shots |
| pod time at 22.7 s per picture | about 45 min | about 55 min | about 65 min | 35 pictures in 793 s on an RTX 4090 |
| pod cost at $0.89/h | about $0.7-0.9 | about $0.9-1.1 | about $1.1-1.4 | add about $0.1 boot; limit = pictures x 30 s x 1.25 |
| ElevenLabs read (credits; the creator has the Pro plan and counts credits, 1 credit about $0.00018) | about 6,800 credits | about 8,500 credits | about 10,200 credits | 2,337 credits for 2,550 characters (Day 1); add about 1,000 for the test read. The earlier dollar rows were about twice too high |
| hero sprites | the poses the plan names | | | about $0.067 each, reusable across videos |

These are estimates for planning; the estimate before each paid call is the number that counts.

## 4a. Cost is counted in credits
The creator has the ElevenLabs Pro plan and counts credits, not dollars: every request for approval states credits first (read
with `estimate_only`; 1 credit is about $0.00018) and the dollar equivalent second. Gemini pictures are dollars from the Gemini
key (cap $10 in total, stop at 80 %); RunPod is dollars. Estimates and charges can differ (Scribe was estimated at 61 credits
and charged 998 on 2026-10-16; sound effects were estimated at 55 and charged 17 or 67): the ledger records the charge.

## 5. What is per topic and what is universal

- **Per topic (the episode folder):** research and claim map, narration text, `look.json` (palette per phase, heroes,
  archetypes, pose bank, figure style, style bridge status), shot plan, pictures, sprites for new heroes.
- **Universal (this repository):** the gates above, UR-01..UR-22, N-01..N-10, the stakes vocabulary, the sound library, the
  voice (Clyde), the pod procedure and its money rules, the cost ledger. A new topic starts from a copy of an episode `look.json`
  with `rule_base: 2` and fills in its own heroes, palette and claims.

## 6. The seven-point test (creator, 2026-10-16: every video passes all seven; a failure is investigated, never waved through)

`explainer_engine/qa/scorecard.py` gathers the evidence; the creator decides the rows marked "creator decides".

| # | Check | What is measured or looked at |
|---|---|---|
| 1 | Narration tone and its sync with the video | words per minute (155-175), every cut inside a punctuated pause (UR-12), questions per minute; the creator listens for tone, stress and question intonation |
| 2 | Sound effects and their sync | no sound event on a spoken word, voice at least 14 dB above bed + music, loudness -16 to -12 LUFS; the creator listens: natural and helpful, not cartoon placeholders |
| 3 | Pictures fit the topic and its world | the visual judge (adults, no object from the world's `absent` list, no people in plates, one light, mood), 0 FAIL |
| 4 | Pictures fit the topic's cliché expectations | the era codex `cliches` and screen codes; the creator looks: does it read as the genre the audience knows |
| 5 | Pictures fit each other | luma, saturation and warmth outliers across the episode, one engine, one look thread, one grade; side-by-side sheet |
| 6 | Editing against general standards | UR-01..UR-15 0 FAIL, durations A/B/C, hard cuts at least 90 %, first 30 s rhythm, motion limits |
| 7 | The whole video: fun, interesting, easy to follow, sticky | open loop at each beat end, question rhythm, shots per minute; the creator watches it once without pausing |

**Failure loop.** A FAIL (or a "no" from the creator) on any row: (1) find the cause with evidence (the prompt, the timing, the
sound file, the rule that allowed it), not a guess; (2) fix the **general** rule, check or tool so no video can repeat it, and
log the creator's note in section 3; (3) run the failed step again, then the checks again; (4) three failures on the same row
stop the run and the creator is asked. Cost of the reruns is counted against the approved caps.
