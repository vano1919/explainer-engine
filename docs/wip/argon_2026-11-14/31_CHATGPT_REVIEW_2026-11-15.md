ChatGPT-მ თქვა:
PR #192 — Independent final review

Reviewed: argon/plan-steps-1-2 · HEAD d689cd5 · base PR #188 / 302c8dd

შეჯამება

PR #192 ჯერ სრულად მზად არ არის წარმოებისთვის.
ყველაზე დიდი პრობლემა ისაა, რომ episode runner scene director-ს თვითონ არ იძახებს.
ამის გამო რეალურ გაშვებაზე 2.5D კადრები შეიძლება ისევ ძველ renderer-ზე გადავიდეს.
რუკები, კამერის უწყვეტობა და რამდენიმე ვიზუალური ხარვეზი მნიშვნელოვნად გამოსწორდა.
აუდიოს სინქრონიზაციის კრიტიკული fallback გასწორებულია, მაგრამ მოსმენით შემოწმება არ არსებობს.
ავტომატური QA იჭერს seams-ს, გადამწვარ განათებას და ერთკადრიან ნახტომებს, მაგრამ არა კინემატოგრაფიულ ხარისხს.
სცენარის მიქსი ამჟამად 56/35/9-ია და არა მოთხოვნილი 60/30/10.
ჩემი რეკომენდაციაა, PR დარჩეს draft-ად, სანამ director integration და მთლიანი ფილმის ვიზუალური/აუდიო შემოწმება არ შესრულდება.

1. Overall verdict

Not production-ready. Do not treat PR #192 as completion of the Truce 1914 production pipeline.

The direction of the work is mostly right: image understanding, geometry-aware camera choices, a dedicated map renderer, word-timed actions and defect-specific QA are sensible foundations.

But there is a critical implementation gap: the episode runner does not run the scene director. It looks for pre-generated direction files and uses the legacy renderer when those files or their layer caches are missing. The branch contains six example direction files under docs/wip/.../s7_regenerated_directions/, but none under the episodes/ep_truce_1914/production/direction/ path the runner reads.

So the director works as a separately tested component, not yet as a fully integrated production stage.

2. Code review

Area

	

Verdict

	

Evidence / concern




Sound insert handling

	

Correct improvement

	

Missing LTX inserts now raise ContractError in production. Rehearsal uses exact-duration silence and reports REVIEW. VV.compose must create the voice track or the stage fails. run.py:1137–1161




2.5D layer preparation

	

Improved

	

Morphological mask biting has been removed from the kept-layer path; the source-at-rest and crowd-depth handling have been corrected. The S6/S10 defect-specific visual checks provide useful evidence.




Director integration

	

BLOCKER

	

stage_clips only uses directed25d if a direction file and valid layer cache already exist. Otherwise it calls layers25d and records director_not_used as REVIEW. run.py:704–715




REVIEW gating

	

BLOCKER

	

GO_ON = (G.PASS, G.REVIEW) means a shot can proceed despite the director not being used or another unresolved review finding. run.py:45




Long still splitting

	

Incomplete

	

When a shot exceeds five seconds but has no usable clause boundary, split_long_still returns the original shot unchanged. The runner records long_still_unsplit as REVIEW, which can proceed. shot_split.py:178–186




Camera-jump QA

	

Useful, but limited

	

The new guard detects isolated jumps and short whips; it was calibrated against the S05_SH020 incidents. It measures mean grayscale changes at reduced resolution, so it cannot guarantee that every local visual defect is detected. motion_intent.py:508–537




Assembly / grade

	

Incomplete

	

The assembly code applies transitions and muxes the audio, but the PR does not implement the missing per-shot grade matching identified in the plan. The master assembly path concatenates encoded video chunks and muxes the audio; it does not perform a grade pass. assemble.py:1572–1581

Testing assessment

The test work is meaningful, but I cannot call it sufficient for release.

Session 2/3: new tests initially failed on the base and passed after fixes; Opus reports 96 focused tests passing with one pre-existing failure, and 1,362 related tests passing with the same eight baseline failures.

Later sessions tested camera fixes, map actions and director rules separately. The S8 map work did expose a new label-collision failure, which was fixed in S9.

S10 adds regression guards for the pan direction, whip, edge crop, close-map quality and accented labels.

I found no reported commit statuses through the GitHub status endpoint, and no final branch-wide green test result.

Conclusion: good targeted regression testing; not proof of a complete working film pipeline.

3. Goal-by-goal scorecard

Goal

	

Status

	

Evidence and what current tests miss




Sound and narration alignment

	

PARTLY

	

Insert failure handling, measured timing, stem generation, cue checks, dropout checks and loudness/true-peak checks exist. But there is no human listening approval. Machine checks cannot tell whether music, ambience, foley and narration feel emotionally right together.




Overall visuals

	

PARTLY

	

Real 2.5D renders were reviewed. Several defects were found and corrected, but only a small selection of shots received the documented visual review. Automated QA catches selected technical defects, not whether a shot looks cinematic.




Storytelling / YouTube fit

	

PARTLY

	

Document 06 contains a useful shot-to-shot plan for all 84 shots. The runtime director, however, does not evaluate the whole story or make all the planned choices. There is no demonstrated complete-film review for hook, pacing, clarity or audience retention.




LTX video quality

	

NOT CHECKED

	

LTX is still the largest visual lane, but this PR does not provide a verifiable review of the 55 video shots as a complete lane.




Logic between shots

	

PARTLY

	

Map camera inheritance and map-to-map transitions are implemented. The story-flow table also proposes focal and audio handoffs. Equivalent continuity is not demonstrated across all video, still and helper transitions.




High-quality 2.5D animation

	

PARTLY

	

Frame-0 seams, crowd depth and camera movement improved. The S7 visual check found five of six reviewed shots clean of isolated jumps, but S05_SH016 still had a fill_invents review and S05_SH020 had a pan/whip defect until S10. Not every still shot has been visually approved.




Maps

	

PARTLY

	

Historical borders, map camera inheritance, standing lines, labels, date cards, counters, ghost carry-over and dual-colour front lines have been added. S9’s visual check still reported blurry close views, noisy macro relief and missing accents. S10 claims these were corrected, but I could not inspect its private render output.




Numbers and counters

	

ACHIEVED — narrow scope

	

The map counter has fixed width, a non-zero first visible value and a claim field. test_m6_counter_locked_box_width_and_nonzero_first_frame verifies the relevant behavior. This does not prove every future numerical visual is correct.




Documents, newspapers and other helpers

	

PARTLY

	

Maps, counters, bars, progress bars and split comparisons exist in maps/actions.py. I found no implemented newspaper, book, letter or document visual lane in this PR.




Variety of visual styles

	

NOT YET

	

The director varies camera operations and effects. That is not the same as selecting different visual languages for the narration. There is no demonstrated style-selection system for documents, diagrams, archival pages and other helper visuals.




Director’s knowledge

	

PARTLY

	

The knowledge base contains idioms, feasibility rules, variety constraints and 16 Truce fixtures. It is useful, but the runtime director is heuristic and the episode runner does not generate and apply its decisions itself.

The actual episode script also does not match the fixed mix:

84 shots · 367 seconds of planned runtime

Lane

	

Actual runtime share

	

Target




Video

	

56.0%

	

60%




Still 2.5D

	

35.3%

	

30%




Map helpers

	

8.7%

	

10%

router.mix_report() calculates the share, but stage_clips returns it as report data rather than a blocking acceptance gate. A report is not enforcement.

4. Prioritized changes — maximum 9

Priority

	

Change, files and proof

	

Cost




1

	

Wire the director into the actual runner. In episode/run.py, add a direction-generation step that calls living_director.direct() for every applicable still/helper shot, persists direction files under production/direction/, validates them and passes them to rendering. Do not silently accept director_not_used in production. Test a full Truce fixture and assert every eligible shot receives a valid direction and the intended renderer.

	

Free CPU for current heuristics and image geometry.




2

	

Enforce the visual mix and five-second rule. Update episode/run.py, episode/router.py, and episode/shot_split.py. Add a blocking mix gate with explicit tolerances. If a long still has no clause boundary, use a safe word-boundary split, reroute it or stop production. Test all shots and assert every produced 2.5D part is at most five seconds and the mix is within target.

	

Free CPU.




3

	

Make liveliness QA region-aware. Update qa/motion_intent.py and the runner. A tiny moving flame must not make an otherwise frozen image pass. Measure motion in salient subject/background regions and in every one-second window. Calibrate thresholds against approved and rejected real shots before changing REVIEW to FAIL. Test a frozen crowd with a moving torch and a genuinely animated crowd.

	

Free CPU.




4

	

Finish map quality at delivery resolution. Update maps/plate.py, maps/geo.py and tests/unit/test_v43_map_actions.py. Render the complete S02 and S05 map sequences at 1080p. Add checks for close-range detail, excessive macro noise and readable labels, then require a contact-sheet eye review. Avoid fixing blur by simply increasing sharpening.

	

Free CPU; extra render time.




5

	

Close the audio/scene-direction gap. Connect scene decisions to the measured sound plan in production/living_director.py, episode/sound_plan.py and episode/run.py. Unresolved AV events and unauthored ambience should block a shippable run unless explicitly approved. Test event onsets against measured word timings and require a human listening approval for the mix.

	

Free CPU for checks; actual narration/audio asset generation may be paid.




6

	

Add cross-lane grade matching. Update production/assemble.py and reuse finish/grade.py. Match video, still and helper clips against a scene anchor while preserving image detail. Test cut-to-cut colour difference and review representative LTX-to-still and map-to-still cuts.

	

Free CPU.




7

	

Make story continuity a real director responsibility. Extend living_director.py, edit/cinematic_transitions.py and the Truce fixtures to evaluate all 83 cuts: story relationship, focal handoff, screen direction, scale change, transition and audio bridge. Test the complete sequence, not just isolated examples.

	

Free CPU.




8

	

Build the missing helper styles. Add dedicated renderers for archival documents, letters, newspapers and book excerpts, and let the narration intent select among them. Test at least one real Truce shot for each format and verify legibility at phone size.

	

Free CPU with Pillow/FFmpeg.




9

	

Require visual sign-off for every lane. Add a whole-episode contact sheet and a review record covering every LTX, 2.5D and helper shot. A technically passing render must not become an approved master until the human visual review is complete. Add an equivalent listening sign-off for audio.

	

Free CPU for reports; the review itself is manual.

5. Is the overall direction right?

Yes, with important changes.

Keep the director-first architecture, picture geometry analysis, explicit camera-feasibility checks, word-timed map actions, historical map data and defect-specific regression tests. The map engine is a better foundation than returning to disconnected static map clips.

Change the director from a tested component into a mandatory episode stage. It should make and record the actual shot decisions, not wait for direction JSON generated elsewhere. It also needs a film-level view of neighbouring shots and story progression.

Two current rules should be softened:

no_two_same_camera_ops_in_a_row

max_push_in_in_5_shot_window

These are useful variety preferences, not universal cinematography laws. They should influence scoring, not force a different camera move when repeating the same move is the right storytelling choice.

Keep hard failure rules for genuine technical or creator vetoes: cropped people, invalid framing, camera snaps, broken source-at-rest frames and unacceptable render defects. Treat unproven aesthetic thresholds—such as the 1.8%/s pre-accent minimum—as hypotheses until calibrated against several approved shots.

Do not replace the entire 2.5D renderer or map engine now. First integrate, test and compare the current architecture across the full episode.

6. NOT CHECKED

Private Hugging Face renders: I could not open vano1919/tmr-artifacts. The visual findings in documents 24, 27 and 30 and the incident journal were used instead.

Final S10 map reel: the incident journal and final commit describe the fixes as eye-checked, but I could not inspect the underlying reel or verify the post-S10 result independently.

Complete Truce master: no verifiable end-to-end master with all 84 shots, transitions, narration and mixed sound was available.

Complete LTX lane: I did not independently inspect all 55 video clips.

Final full-suite test run: I found per-session test results, but no definitive final branch-wide test report or reported commit status.

Final decision: PR #192 contains real fixes and a better technical foundation, but it has not yet demonstrated the central requirement: one complete, coherent, visually and sonically approved documentary film. Keep it as a draft until the director is wired into the runner and the full episode passes technical checks plus human review.

Convert to PDF
მოგწონთ პასუხების ეს სტილი?
ChatGPT შეიძლება შეცდეს. მნიშვნელოვანი ინფორმაცია გადაამოწმეთ.
ბოლო პასუხი




ფიქრი