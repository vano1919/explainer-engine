# Fable audit of the AV report and the video-lane report (2026-11-13)

The creator's order (2026-11-13 12:05 UTC): check both threads' reports against the repository, find what must change elsewhere
(script writing and other places), find what is more correct than their decisions, and leave a report plus a working guideline
for an Opus high thread. This is the report. The guideline is `OPUS_WORKING_GUIDELINE.md`, the entry file is `HANDOFF.md`, the
short Georgian summary is `SUMMARY_ka.md` (same folder).

Read-only audit. Nothing paid ran, no code changed, nothing was pushed except this folder.

## 0. What was checked, and how

| Input | Where | Checked against |
|---|---|---|
| AV report for Fable + sound guide v2 (D-135) | `/mnt/project-files/av_system_2026-11-13/` | branch `claude/project-thread-98b6wy` (PR #174, head `372bb38`) |
| Sound guide v1 (W1) | `/mnt/project-files/sound_library_2026-11-13/SOUND_INTEGRATION_GUIDE.md` | branch `claude/project-thread-xpsv3w` (PR #171, head `d1b9614`) |
| Video lane: implementation report, media QA report, system design, forensic audit (D-137) | `/mnt/project-files/explainer-engine/v4_3_plan_2026-11-12/video_lane_2026-11-13/` | branch `claude/project-thread-lncsi3` (PR #175, head `0c58cdf`) |
| The Gemini picture line (A line) | PRs #165 to #168, #170 | branch `claude/project-thread-1hrknf` (head `d79851c`) and `96iqtm` (`db59807`) |
| The real episode | `episodes/ep_toba/story/production_script.json` | G1 of the runner, the video-lane plan, the event resolver |

Method: every claim was opened in the code of its branch; the focused tests of both branches were run; the two branches, the
A line and PR #173 were merged in a local scratch tree (never pushed) and the full suite was run on the result; the pilot script
of the AV branch was built and retimed at several read speeds; the Toba script was run through G1 and the video-lane plan.

Evidence words used below: **measured** (I ran it and saw the number), **read** (I opened the code), **proposal** (my
suggestion, not a decision). Anything about how a clip looks or sounds is outside this audit: no LTX clip was generated and no
audio was listened to.

## 1. Verdict

1. Both reports are honest about what they built. Their main claims hold in the code (section 2).
2. The two branches merge. Six files conflict between them and all six resolve mechanically (guideline, phase P0).
3. Neither line can produce the Toba episode today. Five faults stop the run or waste it, and none of them is in either report:
   the script gate still measures LTX shots against the Wan model (FA-01), LTX is never told the line it must speak (FA-02), the
   Toba script has none of the new fields and no writer page teaches them (FA-03), the Gemini picture line refuses every `video`
   shot after the merge (FA-04), and both sound guides tell the writer to use fields the script schema rejects (FA-05).
4. "Words never place a sound" (D-135) is true for effects and false for the bed, the era and the music mood: those are still
   picked by matching substrings of the prose (FA-09). One measured case: a sentence with "strains" and "marches" gets a
   heavy-rain bed.
5. Everything timed in absolute seconds or frames inside a shot breaks when the read changes the shot's length; today that is a
   silent truncation or a stop after the paid read (FA-06).
6. The script-writing stage is the largest gap. No agent or skill under `.claude/` knows `edit_plan`, `sound_events`,
   `av_contract`, event ids or continuation shots, and several still write the route `wan` (FA-03, FA-17).
7. The hero identity gap named in the video-lane report can be closed before money is spent with tools the repo already has
   (FA-14).

## 2. The reports' claims against the code

| Claim | Result | Evidence |
|---|---|---|
| AV: one resolver for visible events (`episode/events.visual_events`), used by maps, 2.5D and the sound plan | holds for `actions` and `motion_imitation` | read: `maps/actions.plan`, `production/layers25d.plan`, `episode/sound_plan.shot_events` all call it; `ACTION_AT` is gone |
| AV: a word of the read or of the action text never places an effect | holds | read + the rewritten tests `test_v43_sound_plan.py`, `test_sound_design_system.py`; words become `candidates` only |
| AV: no procedural placeholder sound plays, a missing take is silent and listed | holds | read: `audio/stems.py` (`played: "silence"`, `silent_rows`), new test in `test_v43_sound_plan.py` |
| AV: cue sheet rows for BP-54, BP-55, BP-56, BP-81 | hold, with the limits in FA-11 and FA-12 | read: `episode/cue_sheet.py` |
| AV: tests changed, none weakened | holds | read: the diff of the three changed test files replaces word-placement assertions by candidate assertions, as D-135 demands |
| AV: one event report covers every visible event | does not hold fully | FA-10: `picture_event` sound events take a second path and are not in the report |
| VL: `videolane/{plan,storyboard,scene,ingest,voice,cuts,master_qa}.py` exist and are wired into G1, G6, G7, G8, G10 | holds | read: `episode/run.py` on `lncsi3`; 46 video-lane tests pass (measured) |
| VL: clip length from the line (VL-06), continuation by a hand-over frame instead of LTX extend | holds | read: `videolane/plan.clip_seconds`, worker `handover_frame` |
| VL: cuts on measured speech, raw clip kept, recut never stretches (VL-11) | holds, with the fault in FA-07 | read + measured: `videolane/ingest.edit_points` |
| VL: known gaps, identity across cuts not checked, colour check missed a helmet change | confirmed, and closable | FA-14 |
| VL: the lane is ready for the Toba script | does not hold | FA-01, FA-02, FA-03: G1 on Toba gives `video_edit_plan FAIL 55` and `video_shots_fit_the_model FAIL 23 of 55` (measured) |

Full suite on the merged scratch tree: see section 8.

## 3. Findings

Severity: **A** stops a run, wastes a paid step, or breaks at the merge. **B** wrong output without a FAIL. **C** stale text or
small debt.

### FA-01 (A) The script gate measures LTX shots against the Wan model
`episode/run.py` `stage_script` (line 255 on the merged tree) still calls `WA.fit_rows(shots, WJ.load_launch())`, the Wan launch
file (one clip 5.09 s at 16 fps). The video route has been LTX since D-132 (`training/pods/ltx/launch.json`, 241 frames = 10 s at
24 fps). Measured on Toba: `video_shots_fit_the_model FAIL: 23 of 55 video shot(s) are longer than one clip of
Wan-AI/Wan2.2-I2V-A14B-Diffusers`. A false blocking FAIL at G1. `gemini_task/timing.py` reads the same Wan launch file.
Fix: the fit row reads the LTX launch and uses `videolane/plan.clip_seconds` (VL-06), so the row and the lane agree.

### FA-02 (A) LTX is never given the line it must speak
The worker sends only `job["motion_prompt"]` (`training/pods/ltx/modal_ltx_jobs.py`). `videolane/scene.build` copies
`video_prompt.motion_prompt` verbatim; `row["line"]` is informational. The script lint `KP-V4-DIALOGUE-LEAK`
(`scripting/shot_prompt_lint.py`, FAIL, run in G1) forbids quoted dialogue inside `motion_prompt`, correctly. So on a real script
the nine character lines of Toba never reach LTX. The clips come back silent and `ingest.edit_points` raises "a spoken clip with
no speech" after the money is spent. The hand-written battle test worked because its prompts had the line and a voice
description typed in by hand.
Fix (proposal): a deterministic LTX prompt composer inside `scene.build`: motion prompt + the speaker's voice description from
the cast + the quoted line + a sound clause; "nobody speaks" on narrated shots. The script stays lint-clean and the worker file
does not change.

### FA-03 (A) The Toba script and the writers' room do not know the new contracts
Measured on `episodes/ep_toba/story/production_script.json`: 138 shots (69 `still_25d`, 14 `map_action`, 55 `video`); of the 55
video shots 46 are narrated and 9 carry a character line; 0 shots have `edit_plan`, 0 have `sound_events`, no `av_contract`.
The video-lane gate answers `video_edit_plan FAIL 55`. Read: no file under `.claude/agents` or `.claude/skills` mentions
`edit_plan`, `sound_events`, `av_contract`, `event_id` or `continuity_mode`; `edit-planner` still describes the Ink Chronicle
lanes. A new script would have the same holes.
Also measured: the Toba video share is 35.6 % of duration (255.9 s of 719.8 s) against D-131's 60 %; VL-06 would generate about
358 s. `router.mix_report` only reports, no gate. This is the creator's call (section 5, Q7).

### FA-04 (A) The Gemini picture line refuses every `video` shot after the merge
`gemini_task/queue.py` on the A line: `BUCKET = {"map_action": 10, "still_25d": 30, "wan": 60}` and a `ContractError` for any
other route. The router now writes `video` (`LEGACY_ROUTES = {"wan": "video"}`). After the merge every video shot fails the
queue. `texts/drive_pack/04_VIDEO_SCRIPT_RULES.md` still says `wan` and has no rule for continuation shots (they need no start
picture) or coverage shots (they take the scene master as reference). Commit `db59807` (GC-21) exists only on `96iqtm` and is
missing from `1hrknf`.

### FA-05 (A) Both sound guides tell the writer to use fields the schema rejects
Guide v1 section 3 and guide v2 section 3e name `intentional_silence`, `sound_design` on a shot and `mood` / `music` on a
segment. `production_script.schema.json` has `additionalProperties: false` on segments and no such shot fields, so G1 rejects a
script that follows the guide. `INTENTIONAL_SILENCE` in the sound plan is unreachable from a valid script. `shot_events` reads
`item.get("class")`, which the schema does not define on a sound event either.
Fix: add the fields to the schema (optional, described) and correct the guides in the same change; one test loads a script
written by the guide and validates it.

### FA-06 (A) Absolute anchors inside a shot do not follow the read
`ep.timed_script()` replaces `target_duration_seconds` after the read. `sound_events` carry `at_s` only; `actions` and
`motion_imitation` carry `at_frame`, `from_frame`, `to_frame`. Measured on the built pilot: at 0.6 of the planned length a second
camera segment is silently cut to 3 or 4 frames; at 0.5 `ContractError: camera segment orbit_small [36, 37) is outside the
shot's 34 frames`; at 0.33 `sound event eruption_boom at 2.2 s is after the shot's end`. The stops come at G7 and G8, after the
paid read. The read is not lost (the words did not change), but the truncation above 0.5 is silent.
Fix (proposal): anchors that move with the shot. `at_word` (line id + word + offset) for sound events, resolved on the measured
spine the resolver already receives; fractions or word anchors for camera segments; an anchor check inside G6 right after the
retime, so the list of broken anchors appears at the read stage; a truncated segment becomes a REVIEW row, never silent.

### FA-07 (A) The hand-over cut ignores where the speech ends
Measured: `edit_points(5.0, [(0.8, 4.6)], {"tail_handle_s": 0.5}, 4.0, 24, spoken=True, handover_s=105/24)` returns
`out_s 4.4167`. The line ends at 4.6 s; the cut is 0.18 s inside the last word and BP-187's 0.5 s tail is gone, with no row.
The worker's `handover_frame` picks the calmest tail frame without knowing the speech end.
Fix: ingest FAILs when the hand-over lies before speech end + tail (free, no worker change); later the plan passes the expected
speech end to the worker so the frame search starts after it (worker change, batch it with any other worker change because the
ladder must run again).

### FA-08 (A, merge only) D-133 has two meanings across the branches
The video-lane branch renumbers W1's sound decision D-133 to D-136 (D-133 = cheapest run, D-137 = video lane). The AV branch
adds new "D-133 = W1 sound" references: `audio/stems.py` (four places), `tests/unit/test_v43_sound_plan.py`,
`docs/EPISODE_FIRST.md` SP-02, `docs/SOUND_LIBRARY.md`, PROGRESS entries. They become D-136 at the merge.

### FA-09 (B) The bed, the era and the music mood are still chosen from words
`audio/sfx_planner.build_shot_sound_design_metadata` picks weather and room by substring on prose (`"ash" in text`, "rain",
"room", "hall", "front"). Measured: "The supply line strains as the column marches" gives `heavy_rain_and_wind`; "A flash of
bronze as the brain of the army, the general, trains his men" gives `volcanic_ash_storm_and_wind`; "They wash the grain in the
shallow river" gives volcanic ash indoors. `infer_historical_period` falls back to `napoleonic_1815`: measured, an episode
`ep_troy` gets the Napoleonic era, and the manifest's `historical_period.era_id` is not read by `sound_plan.build`.
`sound_plan.segment_mood` runs a regex over title, purpose and delivery text; a "tense" result also places an automatic riser
(`cue_sheet.py`, `TENSE_MOODS`). This is the same fault D-135 removed for effects, left in for the layers that play longest.
Fix (proposal): the bed belongs to the place (authored on the scene or location, the editing guide's "place-bound ambience");
the era comes from the manifest and a missing era FAILs; the mood is an authored segment field (FA-05) and the regex result is a
candidate only.

### FA-10 (B) A second path beside the resolver
`production/layers25d.py`: `if events is None: events = [... shot.sound_events with picture_event, at_s * fps]`. Those events
shake the picture without passing `visual_events`, and `av_report.event_report` lists only `actions` and motion items. The
loudest picture events (an eruption, an impact) are the ones outside the report.

### FA-11 (B) Three checks measure too coarsely
BP-81 `cue_density` divides the cue count by the whole sheet, so a full episode dilutes any crowded minute (the 10 s burst row is
REVIEW only). BP-55 counts only visual events as beats. `av_report.timeline` makes one dialogue window from the first line to
the last line of the episode. `one_emphasis_a_line` is counted per shot. `FRAME_MS = 1000 / 24` is a constant instead of the
episode fps.
Fix (proposal): the worst 60 s window for BP-81; dialogue windows per line from the measured spine.

### FA-12 (B) BP-56 fails in code and reviews in the registry
`cue_sheet.py` uses `SR_RULES.level("BP-56")` (FAIL) while the registry row says severity REVIEW; BP-55 beside it uses the
registry (`_sev`). One of the two is wrong. The creator decides (Q1).

### FA-13 (B) The sound LTX makes for narrated shots is thrown away
`videolane/voice.py` and G8 use clip audio only for clip-spoken inserts. For the 46 narrated video shots of Toba the clip's own
sound, made in sync with its picture, is dropped, and the sound plan must rebuild it from library takes placed by hand. The
sound plan already documents `source: clip_audio`. Also read: the voice track is mono, the read pieces are hard-cut (no fades,
against BP-188's 30 ms), and the clip's non-speech sound rides inside the narration stem, so ducking treats it as voice.

### FA-14 (B) Hero identity across cuts: no check, but the tools exist
The storyboard gate VL-10 checks dHash duplicates and the palette against the master. Unwired and already in the repo:
`training/video_qa.shot_identity` / `judge_identity` (palette per hero box), `qa/face_points.py` (YuNet + SFace against hero
references), `qa/identity.py` (CLIP against the hero sheet), `qa/sheet_review.py` + `qa/visual_judge.py` (Claude answers
questions on a contact sheet, free), `qa/keyframe_gate.py`, the `shot-continuity-writer` page with its continuity cards
(costume, props, eyeline). The helmet change the colour check missed is exactly a continuity-card question. No voice check
exists across the clips of one speaker either.

### FA-15 (B) Narrated clips are sized from the estimate, then cut to the read
`clip_seconds` uses the planned length for a narrated shot. `ingest.recut` refuses when the raw clip is shorter than the
measured shot, which means a paid regeneration. The read costs the same whenever it is made.
Fix (proposal): the read (G6) before the paid LTX scenes; narrated clips sized from the measured shot length.

### FA-16 (C) The LTX route has no adapter and the retired list is wrong about it
`config/retired_era.json` names `aivideo/ltx_modal.ModalLtxBackend` as the LTX replacement. The module does not exist, so the
video route has no retry and no 2.5D fallback rule of its own (RT-07) beyond the runner's rehearsal branch. The same file lists
`training/video_qa.py` under the retired xworld LoRA while the video lane imports it.

### FA-17 (C) Stale texts that will mislead the next thread
`CLAUDE.md` header on both branches: 60 % `wan`, "LTX retired", G7 through `aivideo/wan_adapter`. `.claude/rules/cloud-platforms.md`
(Modal Wan), `GEMINI.md` (`wan`), `docs/SCENE_REUSE_RULES.md` LX-04, `docs/VIDEO_GENERATION_WAN.md` banner,
`tests/unit/test_icw01_rule_rewrite` (treats "LTX" as legacy unless D-116 or D-131 is named). Counted on the merged tree: the
route name `wan` is in the skills `shot-visuals`, `dialogue-scenes`, `editing-style`; wording of the D-116 route (Blender, Ink
Chronicle, Qwen, the old LTX roles) is in the skills `shot-visuals`, `editing-style`, `visual-beats` and the agents
`story-architect`, `scene-writer`, `edit-planner`, `beat-writer`, `voice-caster`, `shot-continuity-writer`. None of the fifteen
writer pages names `edit_plan`, `sound_events` or `av_contract`. BP-187 has `enforced_by: []` on the AV and W1 branches.

### FA-18 (C) Small debts
`sound_plan` keeps module-global `_DECISIONS`, `_CANDIDATES`, `_HEARD` (two builds in one process share state). The `at > dur`
check in `shot_events` uses the retimed duration (part of FA-06).

## 4. What is more correct than the threads' decisions (proposals)

| # | Instead of | Do | Why | Cost |
|---|---|---|---|---|
| P1 | effect anchors in seconds and frames | word anchors and fractions, checked at G6 | the read always changes shot lengths | free |
| P2 | bed, era and mood guessed from prose | bed per place, era from the manifest, mood authored | same principle D-135 applied to effects | free |
| P3 | the hand-written LTX prompt | one composer in `scene.build` | the only way a lint-clean script speaks | free; proven only by the first paid sample |
| P4 | identity checked at the end (G10) | checked at the storyboard gate before LTX, again at G10 | a wrong helmet is found before the money | free |
| P5 | LTX before the read | the read first for narrated video shots | no regeneration when the read is longer | free |
| P6 | rebuilding foley for narrated LTX shots | the clip's own sound as a ducked layer; effects authored after ingest on the measured clip ("spotting") | LTX sound is already in sync with its picture | free to build; the level is the creator's ear |
| P7 | density over the whole sheet | the worst 60 s window | a full episode hides a crowded minute | free |
| P8 | hand-over frame by calmness only | calmness after the speech end | BP-187 | free check now, worker change later |
| P9 | one voice per LTX clip, unchecked | a voice description per cast member in every prompt; a paid speech-to-speech pass only if the creator hears a drift | cheapest first | free; the paid option is unpriced and unverified |

## 5. The creator's decisions

| # | Question | Options | My recommendation |
|---|---|---|---|
| Q1 | BP-56 (crowded cues): FAIL as the code does, or REVIEW as the registry says? | a) REVIEW, the code follows the registry; b) FAIL, the registry gets his dated house call; c) REVIEW now, FAIL after the Toba sample; d) other | c |
| Q2 | Narrated LTX shots: use the clip's own sound? | a) no, as today; b) yes, as a quiet layer under the narrator; c) build a free A/B from the clips we already have and decide by ear; d) other | c, expecting b |
| Q3 | Hero identity gate before paid LTX: how strict? | a) FAIL on a face or costume mismatch; b) REVIEW, he looks at the sheet; c) FAIL for the face, REVIEW for costume and props; d) other | c |
| Q4 | The read before the LTX scenes? | a) yes for every episode; b) no, keep today's order; c) yes only for narrated video shots; d) other | a |
| Q5 | Character voices across LTX clips | a) voice description in every prompt, judge in the sample; b) paid speech-to-speech pass on every line; c) decide after the Toba sample; d) other | a then c |
| Q6 | PRs #164 (Qwen ladder), #120 (Blender PoC), #112: not contained in the new line | a) close without merging; b) keep open; c) merge into an archive branch, then close; d) other | a |
| Q7 | Toba is 35.6 % video by duration, D-131 says 60 % | a) keep the script, the mix is a frame; b) re-route shots towards 60 % (more LTX seconds, more money); c) keep for the sample, decide for the full episode; d) other | c |

Until he answers: the code follows the registry for Q1 (REVIEW), today's behaviour for Q2 and Q5, REVIEW for Q3, and Q4 is
built as an order the runner supports, not forces.

## 6. Branches and pull requests

Topology (verified with `git merge-base --is-ancestor`): `systemic/next-video` (`6b5a1b5`) is an ancestor of every v4.3 branch.
`2hoa9u` (#163) → `92rcrx` (#169) → `xpsv3w` (#171) → `98b6wy` (#174), and `xpsv3w` → `lncsi3` (#175, contains `nvctxh` #172).
A line: `dx9fty` (#165) → `bi0g2e` (#166) → `96iqtm` (#167) and `s03igf` (#168) → `1hrknf` (#170). `eczgwr` (#173) is one commit
on main.

| PR | Branch | After the integration branch is merged into `systemic/next-video` |
|---|---|---|
| #174 | `98b6wy` | merged by it; close |
| #175 | `lncsi3` | merged by it; close |
| #171, #169, #163 | `xpsv3w`, `92rcrx`, `2hoa9u` | contained in #174 and #175; close |
| #172 | `nvctxh` | contained in #175; close |
| #170, #168, #166, #165 | `1hrknf`, `s03igf`, `bi0g2e`, `dx9fty` | merged by it (A line, with the FA-04 fix); close |
| #167 | `96iqtm` | its extra commit `db59807` is merged separately; close |
| #173 | `eczgwr` | merged by it; close |
| #119, #130, #131, #137, #140, #146, #147, #149, #150, #151, #152, #157, #158, #160, #161, #162 | older heads | already contained in `lncsi3`; close after the merge |
| #164, #120, #112 | `jtvjlt` and two older | NOT contained; retired work; Q6 |

Their bases are mostly `main`, so GitHub will not mark them merged by itself; they are closed by hand with a one-line comment
naming the integration PR. Branches are deleted only on the creator's word (hooks refuse `branch -D`).

## 7. Not verified

- No LTX clip, no read and no picture was generated; P3, P6, P8 and P9 are proven only by a paid sample.
- I did not listen to the designed sound demo or look at the 2.5D pilot frames; this audit is about contracts and gates.
- The ElevenLabs speech-to-speech price and its fit for LTX voices (P9) are unverified.
- PRs #164, #120 and #112 were checked for containment only, not for content worth saving.

## 8. Full suite on the merged scratch tree

The run was still going when this file was first committed; the result is appended in the next commit of this branch.
