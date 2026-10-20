# Rule contradictions across the explainer-engine system (audit of 2026-10-19)

Scope: every production rule in `CLAUDE.md`, `docs/*` (PRODUCTION_RULES, VIDEO_PARAMETER_SPEC, UNIVERSAL_RULE_BASE, EDITING,
STORY_ENGINE, AUDIO_SYSTEM, QA_SPECIFICATION, ORCHESTRATION, DECISIONS...), the Python validators (`production/validate.py`,
`edit/board.py`, `edit/motion_lint.py`, `edit/shot_rules.py`, `audio/layers.py`, `audio/duck.py`, `audio/level.py`,
`qa/targets.py`, `qa/scorecard.py`, `qa/engagement.py`, `scripting/narration_lint.py`, `scripting/stage_guard.py`,
`production_gate.py`, `publish/*`, `standards/*`), the 11 skills and the 10 agents under `.claude/`.
Four audit passes (narration, audio, editing/motion, governance) found 211 rows; this file keeps the ones that change what
a video looks or sounds like, grouped by theme. The storytelling conflicts (scene, dialogue, cue-per-beat) are in
`storytelling_research/RULE_CONFLICTS_2026-10-19.md` (the rewrite thread) and are not repeated here.

Legend: **BLOCKS** = the described gate cannot pass or is not run on the current (D-43) production path.

## A. Gates that do not run on the real path (BLOCKS)

| # | Contradiction | Where |
|---|---|---|
| A1 | The seven-point test (PRODUCTION_RULES gate 9) has no command line for a production script; its only caller is the legacy `examples/stone_age/day1_v5/qa_run.py`. Rows 4 and 7 are always REVIEW. | `qa/scorecard.py` |
| A2 | The loudness, true-peak and voice-gap verdicts in `qa/targets.py` are called only by the scorecard; `production/assemble.py` measures LUFS and stores it (line 457) but judges nothing. No true peak is measured anywhere; Shorts are never re-measured after cues and music are added. | `qa/targets.py`, `production/assemble.py`, `production/shorts.py` |
| A3 | `edit/shot_rules.check_shots` (UR-01, 02, 04, 05, 11, 13, 14) runs only in the legacy gate and the scorecard; the D-43 path runs `check_timed`, which does not call it. Gate 3 "solver + check_shots 0 FAIL" describes a gate that does not run. | `edit/shot_rules.py`, `production/validate.py`, `production_gate.py` |
| A4 | `publish/stage.py` uploads after `publish_check` with FAIL only; PC-08 (final_qa stamp + recorded approval) is REVIEW only. Syndicate Wars was staged without a final_qa stamp. Invariant 4 says "recorded creator approval"; PRODUCTION_RULES gate 9 and D-57 say the approval is the click to Public. | `publish/stage.py`, `qa/publish_check.py`, `production_gate.py:135` |
| A5 | `.claude/active_episode.json` does not exist, so the ElevenLabs PreToolUse hook denies every paid call until someone creates it by hand; nothing in the repo creates it. | `standards/hook.py`, `.claude/settings.json` |
| A6 | PV-12 forwards only FAILs of `narration_lint`, so N-02, N-05, N-06, N-07, N-08, N-10 (all REVIEW) never reach the validator; N-01 and N-02 are called "binding" but are REVIEW and were waived 14 times in Syndicate Wars. | `production/validate.py`, `scripting/narration_lint.py` |
| A7 | ED-06 speed-up (1.05-1.15) and the long read's +8 % atempo are applied after every check: 170 wpm becomes 195, a 2.5 s minimum shot becomes 2.17 s, nothing is re-checked. PRODUCTION_RULES line 95 says "never speed the voice". | `edit/speed.py`, `production/assemble.py` |

## B. Narration pace and word budget

| # | Contradiction | Values |
|---|---|---|
| B1 | Pace band | P-52 155-185 · PRODUCTION_RULES gate 2 160-185 · narration-script skill 160-185 · elevenlabs-voice EL-04 150-165 vs EL-12 155-185 (same file) · NARRATION_GUIDE "155 wpm" · scorecard PASS 150-180 but prints "155-175" · engagement LONG_BEAT 155 · scene-writer 150 · schema allows 90-220 · real scripts plan at 140-158 / 150-172 |
| B2 | Word budget | P-32 1050 words / 7 min (= 150 wpm) vs PRODUCTION_RULES planning 170 wpm |
| B3 | Sentence length | N-05 < 22 words · P-35 8-18 · NARRATION_GUIDE 28 · DW-06 25 |
| B4 | Questions | P-36 / NARRATION_GUIDE ≤ 1 rhetorical question per section · N-06 ≥ 1 per 150 words · DW-10 1 per minute · narration-script every 20-30 s · ST-11 "an undeclared question is answered at once" vs N-02 rewards beats ending in "?" |
| B5 | Hook timing | UR-01 / gate 1 question by 5 s · P-30 premise by 10 s (D-07) · story-architect cold open, question by 0:15 · shorts skill 3 s · N-01 FAILs a first sentence that is not a yes/no question (kills the cold open); the scorecard's "hook by 5 s" evidence only checks that the first word starts before 1 s |
| B6 | Humour | P-05 1 joke / 60 s · SS one per beat · narration-script 20 % share; no code |
| B7 | Stress | N-04 one stressed word per sentence vs PF-02 one per line (schema: 1 emphasis per line); PF-01 ≤ 2 audio tags per line vs narration-script 1 per 2-3 sentences; interjection lists differ between `stage_guard`, `narration_lint` and PF-04 |
| B8 | Pauses | reveal pause P-53 0.9 s · PF-03 0.5 · performance-director 0.3-0.8 · `script.py` drops tags < 0.5; sentence/paragraph pause P-53 0.35/0.7 · UR-12 0.3-0.6 · `pause_pad` MIN_GAP 0.26 for every mark · validate 0.35/0.15 |
| B9 | Chunks | EL-03 400-900 characters vs speaker-change chunking with no minimum and > 900 kept whole; `previous_text`/`next_text` are written but never sent |
| B10 | P-55 "digit lint" is named but does not exist; EL-07 says keep digits |

## C. Loudness, mix and export

| # | Contradiction | Values |
|---|---|---|
| C1 | Integrated loudness | P-90 / targets PASS -15..-13, allowed -16..-13 · PRODUCTION_RULES §6 "-16 to -12" · no gate runs (A2) |
| C2 | Bed and music under voice | PRODUCTION_RULES:82 "20 dB under" · P-93 / targets 14 dB · AL-04 "-15 dB" (a peak-normalised level, not a distance) · AUDIO_SYSTEM "10 dB" · code voice-duck depth ≈ 6.9 dB max (1-0.55×mean) with no attack/release · UR-32 4 dB / 20/80/280 ms vs code 25/350 ms · scorecard compares voice with max(bed, music), P-93 with the sum |
| C3 | Export | `assemble.py` AAC 192 kbps mono (`-ac 1`) vs P-15 / Q-T19 stereo 384 kbps |
| C4 | Fades | P-96 20 ms / 1 s / 2 s · AUDIO_SYSTEM 5/40 ms · ED-01 30 ms · code sfx 5/10 ms, music 2 s, mix 0.5/1.5 s · picture fade 1.0 s vs audio 0.5 s |
| C5 | Chunk level continuity | ED-01 spread ≤ 1.5 dB vs `seams` clamp 6 dB; 26.5 dB measured; `__main__` prints REVIEW only; VOICE-1 drift is REVIEW only but Shorts treat any REVIEW as a gate |
| C6 | Silence | P-95 silence > 1.5 s flagged: no code · ED-12 0.1 s / -40 dB vs `pause_pad` 0.25 s / -46 dB vs dropouts -42 dB |
| C7 | Shorts audio | loudnorm on the voice stem only, cues hard-clipped, music ×0.10 never ducked; dialogue Shorts always lose tempo (`voice_check.check` instead of `check_speakers`) |
| C8 | Voice shaping P-92 (low-cut, de-ess) not in the mix (level rider + peak normalise only) |

## D. Sound effects and cues

| # | Contradiction | Values |
|---|---|---|
| D1 | Density | AUDIO_SYSTEM "one sfx per 6 s" · AL-02 4-20 per minute · VB-08 one cue per beat (~40/min; cues are not counted by AL-02) · P-94 "not every movement makes a sound" |
| D2 | Sounds on words | UR-15 / PRODUCTION_RULES:82 / seven-point check 2 "no sound on a spoken word" vs UR-32 "sound starts with the event" and VB-08 cues on the word; the scorecard would FAIL every current script |
| D3 | Stacking | AL-01 2 effects at once vs 4 layers (5 with voice); `layers.py` flags > 5, `beats.py` > 4; ED-03 ≤ 2 background layers never checked |
| D4 | Sync | Q-T06 within one frame vs SFX_OFFSET -0.05 s (1.5 frames); "cut sound ends before the next word" vs SFX_MAX 1.0 s and schema max 20 s; `reveal_sting` is 30.8 s |
| D5 | Loop vs one-shot: no field in the manifest; `loop_to` loops any bed or music; same sample twice in a row is never checked (every bubble pop is `pop_in__v1`) |
| D6 | Cues are never ducked; music never dips under cues; bubble pops duck music by 9 dB |
| D7 | Ticks: relative 6/24 dB rule vs absolute -25 dB on `clockwork_loop` only |
| D8 | `sfx_manifest` schema has no `elevenlabs` source kind and no licence URL/date fields; the library WAVs are not in git so UR-15 / PV-05 fail on a clean checkout |

## E. Picture rhythm, shot length and cuts

| # | Contradiction | Values |
|---|---|---|
| E1 | Pictures per minute | VB-01 / D-54 / edit-planner "a new picture every 3-6 s" · PRODUCTION_RULES planning 13-14 per minute (3.85 s) · UR-31 ≤ 10 per minute = RHYTHM-1 FAIL in `edit/board.py` (assemble refuses) · creator 2026-10-16 "too frequent" vs creator 2026-10-19 "needs frequent changes" |
| E2 | Shot durations | UR-11 A 5-7 / B 3.5-5 / C 2.5-4 s · ED-05 reveals 7-9 s, danger 3-5 · UR-31 min 2.5 s, max still 9 s · SS-07 reaction close-ups 0.5-1.5 s · Shorts skip the board |
| E3 | Something-new cadence | MO-01 5 s · UR-31 / RHYTHM-3 9 s (cuts + bubbles only) · VB-01 1.5-3 s · editing-style 3-7 s · `fill_holds` MAX_GAP 8 s (undocumented); `fill_holds` inserts reframes into stretches the beats already fill and raises RHYTHM-1 |
| E4 | Cut position | UR-12 only in a punctuated pause (0.05 s edge) · editing-style 0-0.15 s before the word · board: middle of the pause · SS-07 first cut inside the hook line (~2 s) |
| E5 | Zoom | UR-13 1.15 (creator) vs ED-02 1.25 vs `continuity.ZMAX` 1.25; stacking punch +18 %, wobble 1.5 %, face focus +14 %, close-up 1.3, Shorts 1.6 × 1.07; only the schema's 1.15 is enforced |
| E6 | Shake | UR-13 "no camera shake" vs the shake accent in STORY_ENGINE AL-03 / edit-planner |
| E7 | Transitions | UR-14 ≥ 90 % hard cuts, 1 s dissolve only on time_jump / place_change · ED-04 period change only · MO-04 whip / flash · editing-style "never flash" · P-76 wipe / lid-open; code draws cut, dissolve (anywhere), fade black, whip_in, flash_in, card dim, and counts whips as cuts; the schema has no time_jump / place_change and timing forces a 1 s dissolve at every period |
| E8 | Period card dims the picture 58 % over 0-4 s of the hook vs UR-01 first shot C / moving A, question by 5 s |
| E9 | Accent holds 1.6 s vs P-71 1.5 + 0.3 per word · UR-31 bubbles max(1.4, 0.3 n) · skill 1.2 s · `beats.HOLD` per kind; easing P-73 12-18 frames / overshoot 1.1 vs pop 7.5 frames 1.12, bubbles 5.4 frames 1.06 |
| E10 | MO-05 on-screen words ≥ 12 s apart vs VB-05 words on half of the beats (~ every 3 s); text/label beats are not counted |
| E11 | Grade | ED-04 one constant film look vs UR-09 grade per emotion (`moods.json` exists, `grade_for` is never called) |
| E12 | Resolution | P-12 1080p vs shot-visuals skill / Episode 1 at 1440p vs orchestrator "720p then 2K" |
| E13 | J/L cuts in the skills vs code only BED_LEAD 0.4 s before the word; chunked renders skip `whip_in` on the chunk's first shot |

## F. Shorts

| # | Contradiction | Values |
|---|---|---|
| F1 | Length | SS-06 15-30 / 45-75 s · P-11 25-60 (> 60 REVIEW) · PV-28 40-130 words (20-55 s) · SH-01 25-50 s · skills 20-45 s · validate bands 32 / 42 s |
| F2 | Hook | SH-01 question in 3 s (PV-28 FAILs any non-question hook) vs SH-04 fact / "did you know" opener; a 14-word hook takes ~4.9 s |
| F3 | Captions | P-103 current word lit, captions from frame 0 vs `shorts.py` three-word caps, no highlight, MarginR 90 < P-102 140 px |
| F4 | Tempo | default 1.05, max 1.08, timed at 170 wpm not at tempo; "never a cut of the long read" (shorts skill) vs EL-09 / SS-03 reuse |
| F5 | Event count: SS-08 kinds vs validate counts shots + accents + bubbles while Short shots forbid accents / bubbles |

## G. Providers, money and governance

| # | Contradiction | Values |
|---|---|---|
| G1 | Pictures | PP-05 enforces D-19 "Gemini only for reusable assets", PV-40 enforces D-52 "never on a pod", D-50 says the creator picks gemini / pod / local per batch, PRODUCTION_RULES standing order 5 says "Gemini batch tier", `paint.py` defaults to sync |
| G2 | Caps | CLAUDE invariant 1 "ceilings only in spend_caps.json" vs invariant 2 "Gemini ≤ $10 total, vidIQ ≤ 200 credits" (prose; `spend_caps.json` has Gemini per episode, no vidIQ or ElevenLabs); D-31 RunPod $3 project cap vs per_episode 3.0; ElevenLabs and vidIQ spend never reserved in the ledger |
| G3 | Dead invariants | 3 (60-90 s prototype first; two long videos shipped, `examples/onion` missing) and 6 (part-based rig; no rig code, D-55 expression sheets instead) |
| G4 | Kokoro remnants | UNIVERSAL_RULE_BASE "Narration is Kokoro", UR-12 Kokoro timings, P-50/51/56/98, AUDIO_SYSTEM chain, TOOL_STRATEGY:22, COST:30, CLAUDE layout (`audio/timings.py`, `visemes.py`), Q-T18 Kokoro alteration report (unmeetable) vs D-39 / D-52 ElevenLabs only; "Scribe words" vs D-42 local Whisper |
| G5 | Narrator | "one voice per channel (Clyde)" (PRODUCTION_RULES:69/130, D-39) vs per-episode `voice_id` (D-43 / voice-caster) |
| G6 | Press-release lines | the creator's 2026-10-19 rule is in no repo file, while ER-07 / RK-08 / RK-16 / RR-10 / SR-04 require source-citing narration and `rulebook.brief` passes them verbatim to the writers |
| G7 | Upload | standing order 9 "upload each piece as soon as it passes" vs OR-05 / orchestrator / CLAUDE:8 / PIPELINE / P-20 "no upload code path"; `publish/*` never calls the scorecard, `short_format` or the final_qa gate |
| G8 | Faces | UR-04 "close-ups without faces" vs D-55 face close-ups and expression sheets |
| G9 | Hook ElevenLabs gate | OR-10 "an editorial FAIL stops paid narration" but `hook.py` checks only takes and the `paid_assets` gate |
| G10 | Stale references | orchestrator.md omits the beat-writer stage (PV-44 FAILs a /2 script without beats); gate numbering differs between PRODUCTION_RULES and `production_gate.py`; INDEX says PV-01..36 (now 47); ED-09 `cards.py`, `shot_rules.route`, `qa/style_distance.py`, `render_bridge.py`, `assets/LICENSES.json`, `AUDIT_2026-10-19.md` do not exist; D-46 / D-47 undefined |

## H. Numbers that live only in code (no rule names them)

board STATE_GRACE 0.3, BUBBLE_LEAD 0.12 · fill_holds MAX_GAP 8, pull 1.10→1.04, push 1.0→1.07 · continuity STEP 0.04 / TOL 0.005 ·
accents PUNCH 0.18, SHAKE 0.018 at 13/17 Hz, WOBBLE 0.015, POP 0.25, FADE 0.15, SLAM 0.12 · beats HOLD prop 2.0 / symbol 1.2 /
highlight 1.3 / chart 2.6, EXPR_TAIL 0.3 · faces DIM 0.82 BLUR 0.014 · timing visual hold 4.0 · graphics card 0.5/2.6/0.9, dim 58 % ·
assemble CHUNK 60 · shorts margins 0.03/0.08, font 76, MarginV 430, 3 words, CRF 16/17, tempo 1.05/1.08, music 0.10 · schema Short
zoom 1.6, text 32 chars, pace 90-220, pause 2.5, gain -40..-6, max_s 20 · bubbles POP 0.18 OUT 0.15 MAX_CHARS 26 · level.py -27 / 0.35
/ 0.7 / -48 · seams 6 dB · voice peak -3.9 · duck 0.55 / 0.25 s · peak cap 0.89 · loop xfade 0.5 · lra 9 · BED_FADE 1.5, SFX_OFFSET
-0.05, SFX_MAX 1.0, BED_LEAD 0.4 · TICK -25 · pause_pad 0.26 / 0.25 / -46 / 10 ms · dropouts 0.05 / -42 · voice_check 3.5 dB / 22 %
· narration_lint 2/3 ellipses, PAUSE_TAGS 0.5/1.0/1.8 · engagement 3/5/155 · scorecard 150-180, hook < 1 s, k 2.5 · speed.py 1.5.

## What this means

Three habits produced most of the rows: (1) each new document restated a number instead of linking its home (D-23 was written
for IDs, not for numbers); (2) gates were described before they were wired to the D-43 path; (3) creator notes were added as
prose without retiring the rule they replaced.

## Resolutions (D-59, the same day)

| theme | resolution | where |
|---|---|---|
| A1 seven-point test never ran | a command line on the D-43 flow, `python -m explainer_engine.qa.scorecard <episode>`; gate 8 of `production_gate` reads it | `qa/scorecard.py`, `production_gate.py` |
| A2 audio verdicts never ran | loudness, true peak and dialogue anchor measured on the delivered file and gated (BP-50, BP-51); Shorts measured on the final file (BP-61) | `production/assemble.py`, `production/shorts.py`, `qa/targets.py` |
| A3 `check_shots` not on the D-43 path | the UR rules it carried now bite through BP checks on the timed script: zoom BP-20, durations and stills BP-40, dissolves BP-31, hook BP-03/BP-40, cuts in pauses stay in `edit/board.py` | `edit/motion_lint.py`, `edit/board.py` |
| A4 staging before approval | PC-08 is FAIL without a recorded approval, a final_qa stamp and a clean scorecard; the click to Public is approval #3, not #2 | `qa/publish_check.py`, `publish/stage.py` |
| A5 `.claude/active_episode.json` missing | by design: the orchestrator writes it at the start of a run (`.claude/agents/orchestrator.md` step 1); not a defect | - |
| A6 PV-12 drops REVIEWs | every narration finding reaches the validator with its own severity | `production/validate.py` |
| A7 speed-up after the checks | the ceiling is the creator's 1.08 (BP-02); 1.15 is gone; the checks re-run on the sped clock | `finish/speed.py`, `production/shorts.py` |
| B pace and word budgets | one band, BP-01 (170, 155-185; a hypothesis, so REVIEW): every other document links it | `scripting/narration_lint.py`, `qa/scorecard.py`, `qa/engagement.py`, docs |
| B hook form and timing | BP-03: the first sentence in one of YouTube's four hook forms, a greeting FAILs; BP-04 the 30-second contract; BP-05 no context before the tension | `narration_lint` N-01, N-11; skills |
| B sentences, register, numbers | BP-06 (median 12, max 20, FAIL over 25), BP-07, BP-08 | `narration_lint` N-05, N-12, N-13 |
| B humour and pauses | BP-09, BP-10 (no punch-line pause; emphasis in the text) | skills, performance-director |
| C loudness, balance, export | BP-50, BP-52 (LU on the stems: music 10, bed 15, combined 14 under the voice), BP-53 ducking numbers in code, BP-63 stereo 384 kbps | `qa/targets.py`, `audio/duck.py`, `production/assemble.py` |
| C chunk levels, silence, fades | BP-59 (1.5 dB spread gated, 7 LU stem range), BP-60 room tone, BP-62 fades | `audio/seams.py`, `audio/pause_pad.py`, `audio/layers.py` |
| D sound effects | BP-54 asymmetric sync (never early), BP-55 purpose and the one-in-two beats cap, BP-56 layers, BP-57 no repeated sample, BP-58 one-shot vs loop | `audio/layers.py`, `audio/sfx_library.py` |
| E pictures per minute and stills | BP-40 section-aware: 5 s in the first 30 s, 20 s REVIEW / 40 s FAIL in the body, the creator's 10 a minute on average, one burst allowed; `fill_holds` stops stacking on beats; BP-41 the 25-35 s interrupt | `edit/board.py`, `production/fill_holds.py` |
| E zoom, shake, transitions | BP-20..24 (1.15 everywhere, a rate, a pan cap, easing, shake only on impact), BP-25, BP-26 flash safety, BP-31 dissolves on period boundaries only | `edit/motion_lint.py`, `edit/shot_rules.py`, `production/continuity.py`, `production/accents.py` |
| E text, faces, continuity | BP-27, BP-28, BP-30, BP-32..34 | `production/accents.py`, `production/faces.py`, `production/continuity.py` |
| F Shorts | BP-11 (spoken hook inside 1 s, done by 3 s, 14 words), BP-12 word bands, BP-13 captions, BP-29 safe zone, BP-44..47 | `production/validate.py` PV-28/PV-34, `production/shorts.py`, skills |
| G providers | D-50 wins: the creator picks the provider per batch; PV-40 and PP-05 stop refusing what the plan approved | `production/validate.py`, `production/paint.py`, PRODUCTION_RULES standing order 5 |
| G caps | the numbers live only in `config/spend_caps.json` (invariant 2 reworded); vidIQ and ElevenLabs stay ledger lines | CLAUDE.md |
| G dead invariants | invariant 3 retired, invariant 6 reworded to D-55 | CLAUDE.md |
| G Kokoro remnants, Clyde | the Kokoro rows and the single-voice line are marked superseded (D-39, D-52; the voice is cast per episode, D-45) | VIDEO_PARAMETER_SPEC, UNIVERSAL_RULE_BASE, AUDIO_SYSTEM, QA_SPECIFICATION, TOOL_STRATEGY, COST_AND_TIME_MODEL |
| G press-release lines | BP-15 (house, FAIL); the rulebook rules that asked for source-citing narration now say the source lives in the claim map and the description | `narration_lint` N-14, `standards/policy_baseline.json`, EPISODE_STANDARDS, RIGHTS_AND_FAIR_USE, ORCHESTRATION |
| G upload path | the unlisted staging of D-57 is the one upload path (OR-05 and P-20 link it) | ORCHESTRATION |
| G stale references | orchestrator lists the beat-writer stage; the missing files are named as such | `.claude/agents/orchestrator.md` |
| H numbers only in code | the ones a rule names are now read from the registry; the rest are implementation details listed above, left where they are | - |

Not resolved here (owned by the scene-rewrite PR of the same day): the cue-per-beat density (VB-08 vs AL-02), scene and
dialogue structure, the beat-writer and edit-planner contracts, the production_script/3 schema.
