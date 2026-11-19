# Explainer Engine V4.1: final action plan, Step 0 and Step 1

Date: 2026-11-19. Author: Claude (review thread). Status: **proposal, waiting for the creator's approval**.
Baseline: GitHub `e4521cd` (draft PR #196 = `fc35615` + the 31 files of Gemini's Drive snapshot `eb80e443`).
Inputs: `V4_1_CLAUDE_INDEPENDENT_REVIEW.md` (verdict `APPROVED_WITH_MANDATORY_AMENDMENTS`, MA-01..MA-18), Gemini's reply
(accepts MA-01..MA-18, proposes Step 0 and Step 1, asks three decisions), ChatGPT's assessment and its recommended answers.
No code is written in this thread. No step in this plan costs money.

---

## მოკლედ (ქართულად)

**რას ვაკეთებთ ახლა:** სამ კითხვას წყვეტ (ქვემოთ ჩემი რჩევაა), მერე Step 0 (დღეს-ხვალ) და Step 1 (5 პატარა PR). ყველაფერი $0.

**ჩემი რჩევა სამ კითხვაზე:**
1. **P1.2 მივიღოთ.** PR #196-ის CI ახლა მწვანეა: 4476 passed, 0 failed. ბოლომდე ვადასტურებთ, როცა Gemini Drive-ზე
   დადებს ზუსტ git ასლს (bundle) და ზუსტი commit-ები GitHub-ზეც იქნება. V4.1 აგრძელებს PR #195-ის გეგმას, არ ცვლის.
2. **ერთი გზა ფილმისთვის: `episode/run.py`.** აქ ChatGPT-ს ნაწილობრივ არ ვეთანხმები. დღეს `mix.py` ბიბლიოთეკიდან
   არცერთ ხმას არ უკრავს. ფონი ხელოვნური შიშინია, მუსიკა სინუსებით აწყობილი აკორდებია. შენი წესი ამას კრძალავს
   ("procedural numpy sound never plays"). Mac-ის მიქსმა ტესტი მხოლოდ ხმამაღლობაზე გაიარა. სწორი ხმის გზა არის runner-ის
   G8 (`audio/stems`): უკრავს ნამდვილ ბიბლიოთეკას და ჩაიწერს რა დაუკრა, ამიტომ ლიცენზიის შემოწმებაც მხოლოდ იქ მუშაობს.
   `build_segments.py`-ის კარგ დაცვებს ვინარჩუნებთ. არაფერს ვშლით.
3. **BBC-ის 6 ხმას ვცვლით, $0.** ისინი runner-ის ოთხ ხმის ჯგუფშია (ხალხის ბუზღუნი 58 შოტში, ცეცხლი 22-ში, ქარი
   84-ში, დარტყმა 1-ში), ანუ მიქსში მოხვდებოდნენ. იმავე ჯგუფებში უკვე გვაქვს Mixkit/CC0 შემცვლელები.
   13 ნოემბრის შენს "კი, BBC-ც" ბარათს ეს აუქმებს მონეტიზებული ვიდეოსთვის.

**ჯემინაისთან პარალელურად:** კი. Chrome-ის extension ახლა ორ ბრაუზერზეა მიერთებული (Mac და Windows). შენი "კი"-ს
მერე Gemini-ს ჩატში მე თვითონ ვწერ და ვკითხულობ, შენ აღარ გიწევს გადაკოპირება. ჩემი რჩევა: Step 1-ის კოდს წერს ცალკე
Claude-ის სრედი (CI-ც და 1914-ის 6 ნამდვილი კლიპიც მას აქვს, Gemini-ს არ აქვს). Gemini კი იმას აკეთებს, რაშიც
ძლიერია: 6 კლიპს უყურებს და უსმენს, წერს სქემებს და სპეკებს, ამოწმებს Claude-ის კოდს და ასწორებს სურათებს.

**რა გჭირდება შენგან:** ერთი ბარათი (ქვემოთ), GitHub-ზე ერთი დაჭერა (main-ის დაცვა) და სიტყვა ყოველი PR-ის მერჯზე.

---

## 1. Goal

The goal is a 1914 film where every reported defect is stopped by code before it reaches the master, and where every
sound and picture in the master can be traced to its source and licence. Step 0 makes one trusted code state with working
locks. Step 1 switches on checks the code already has but nothing calls, plus one licence gate. It adds no new model and no
paid call. Steps 2 to 8 follow section 12 of the review unchanged.

## 2. Facts verified today (2026-11-19)

| # | Fact | Evidence |
|---|---|---|
| F1 | PR #196 CI is green: `4476 passed, 24 skipped, 3 deselected, 1 xfailed` in 693 s; docs_lint and palette passed. On `fc35615` the same command gave 4467 passed, 20 skipped. | Actions run 44490235037, job 135443705782, head `e4521cd` |
| F2 | Since commit `0e299cd` (2026-11-16) `tools/render_tools/mix.py` loads **no library sound**. Beds are band-passed white noise (`synth_sfx` L547-567, called L720). Map sounds are synthesized (L782). Music is sine chords (`synth_music_cue` L570-598, called L795). The Mac mix of `2f17837b` logged `WROTE full_mix.wav {"status": "PASS", "lufs": -14.71}`: the PASS covers loudness only. D-136 and OV-56 say "procedural numpy sound never plays, in the demo either". The earlier pass-1 mixer (`f0f9903`, HF `render/tools/mix.py`) did load library files. | `git show` of each commit; HF `mac_loop_2026-11-16/mix_run1.log`; `docs/HYPERFRAMES_OVERLAY.md` OV-56 |
| F3 | The runner's G8 (`audio/stems.py`) plays library takes only. It refuses a placeholder in a shippable mix (L110-141) and logs every take it used (`sounds_used`, `credits`) into `audio/stems_report.json` (`run.py` L1444). | code |
| F4 | The runner's G9 (`production/assemble.assemble_shot_clips`, L1487+) already refuses a clip whose frame count differs from the shot (L1503). That is stricter than `build_segments`' ±1 frame. `build_segments` adds the single-trim contract, the cache key, the single-resize guard and the overlay authority. It also hard-codes Mac paths (L36-40) and the Truce dip list (L28-31). | code |
| F5 | The six BBC ids sit in four class pools of the runner's sound plan: `crowd_murmur` (58 shots), `fire` (22), `wind` (84) and `impact` (1). `stems.Sounds.get` picks `ids[k % len(ids)]` (L132), so they would play. The full-film shot plan names `army_waiting_murmur__v1` in S01_SH004, S02_SH009, S03_SH002 and S03_SH009. Licence-safe items are already in the same pools (section 3.3). | `episodes/ep_truce_1914/audio/sound_plan.json`, `planning/full_film_2026-11-15/shot_plan.json`, library manifest |
| F6 | The recorded Whisper words of the six clips (`planning/full_film_2026-11-15/ltx_whisper_small_en_2026-11-15.json`) contain words the measured sound does not support. S07_SH006 "I'll see you next time" runs 0.00-7.64 s, but the clip has one onset, at 7.80 s. S04_SH014 "You" at 2.9-4.3 s sits over steady ambience. S03_SH007 "Oh, my God" starts at 0.00 s over a −54 dBFS floor whose only event is at 2.4-2.8 s. S07_SH005 "BANG! BANG!" is the two gunshot onsets. S06_SH008 has "Maybe." twice (0.0-0.6 and 1.72-1.92 s), both with real energy. So `whisper_edit_points` (words only) would cut on invented words. `ingest_scene` already fuses detector spans with words (`speech_with_words`). | word file in the repo; review Appendix measurements |
| F7 | `regeneration_required` is computed (`scene.py` L206) and copied into the prompt output (L279-282), but nothing refuses on it. Without perception input the result is `NO_PERCEPTION_INPUT` with `regeneration_required: False` (L152-160): a silent pass. | code |
| F8 | `worker_sha()` hashes only `modal_ltx_jobs.py` (L250-251). An edit to `scene_run.py` leaves the ladder proof valid ($0). An edit to `read_job` changes the worker hash, so ladder L1-L3 must be proven again, including the paid L3 smoke. | code |
| F9 | Two Chrome browsers with the Claude extension are connected to this account now: "Browser 1" (macOS) and "Browser 2" (Windows). | `list_connected_browsers` |

## 3. The three decisions: recommendation

### 3.1 Decision 1: P1.2 and precedence

**Recommendation: accept P1.2. V4.1 continues the PR #195 plan and does not replace it.** This agrees with ChatGPT.

- Condition (a) is met: CI is green on PR #196 (F1).
- Condition (b): Gemini puts a `git bundle` of `argon/p1-2-timing-contract` (commits `eb80e443` and `0592114`) on Drive,
  or at least `git rev-parse eb80e443^{tree}`. Claude compares it with PR #196's tree `52e6feee432c1dfaaa23346f571c23b2ed521542`.
  The trees can differ only through binary files the text snapshot left out. With the creator's OK, the exact commits go to
  GitHub branch `argon/p1-2-timing-contract`, so every SHA in the documents can be fetched.
- Merge into PR #195's branch only on the creator's word.
- Precedence, written into `docs/DECISIONS_AND_OPEN_QUESTIONS.md`: the decision log comes first, then `DEC-2026-11-17-01`
  and the PR #195 plan, then the V4.1 documents as amended by MA-01..MA-18. Each conflict gets one ADR line, never a silent rewrite.
- PR #195's P1.3 (read-only production state) and P1.4 stay. P1.3 is read-only, so it can run beside V4.1 Step 1.

### 3.2 Decision 2: one render path (MA-18)

**Recommendation: `episode/run.py` is the only way to make a master.**

- **Sound:** only G8 `audio/stems`. It plays real library takes and logs what it played (F3). The licence gate of Step 1.4
  can only work on that path.
- **Picture:** G9 `production/assemble`, which already has the strict frame check (F4). `build_segments`' extra guards
  (single resize, overlay authority, cache key) move into G9, or G9 calls `build_segments.build` as a function. A free
  parity test on a 60-second slice decides which (Step 1.5).
- **`tools/render_tools/mix.py` never makes a master again.** Its synthetic sound breaks D-136 and OV-56 (F2). The file
  and its tests stay, and the tool is marked preview only. Nothing is deleted.

**Where this differs from ChatGPT:** ChatGPT chose "`build_segments.py` + `mix.py` as the official backend, the runner as
orchestration". I agree with its principle (no two independent final-assembly systems) and with keeping `build_segments`'
guards. I disagree on `mix.py`, because of F2 and F3: that mixer plays no real sound and keeps no record of sources, so a
licence or realism gate cannot see what it played.
**Risk:** the runner has not yet assembled the full 1914 film; only the script and sound-plan stage records exist in the
repo. The Step 1.5 parity slice is there to find runner failures before a full render.

### 3.3 Decision 3: the six BBC sounds

**Recommendation: no BBC RemArc sound in any monetised master. Replace them at $0 with items already in the same pools.**
This agrees with ChatGPT and adds the measured facts.

| BBC id (licence: "personal, educational or research only") | Pool | Licence-safe replacements already in the pool |
|---|---|---|
| `army_camp_16c__v1`, `army_waiting_murmur__v1` | crowd_murmur | `crowd_talking_big__v1`, `crowd_angry_men__v1` (Mixkit), `amb_crowd_shouting__v1` (CC0) |
| `bonfire_close__v1`, `fire_small_cracks__v1` | fire | `campfire_crackles__v1`, `campfire_night_wind__v1`, `fire_big_burning__v1` (Mixkit) |
| `woodland_wind_birds__v1` | wind | `forest_wind_birds__v1`, `forest_european__v1` (Mixkit), `amb_wind_open_land__v1/v2` (CC0) |
| `bow_twang_hits__v1` (archery, foreign to 1914 anyway) | impact | `soft_thud__v1..v3` (CC0), `wood_hard_hit__v1` (Mixkit) |

- This reverses the creator's card of 2026-11-13 07:49 UTC ("yes, BBC too"), recorded in `audio/sources.py`
  `SFX_EXCEPTIONS`, so it needs his word. The BBC files stay in the library for research and previews.
- The replacements are marked `human: not_listened`. The creator listens to one 30-second sample per pool before the master.
- The old pass-1 film (`render/pass1`) used a library mixer and may contain BBC sound. It must not be uploaded monetised.

## 4. Working with Gemini in parallel

**What each side does best.** Gemini watches and listens to whole video clips natively, reads very long contexts (the
whole repo text), has a free picture tool in the chat, and has Deep Research. It cannot reach GitHub or HF, cannot run our
CI, and sees our clips only if we put them on Drive. The Claude cloud session has GitHub, CI, the HF media, ffmpeg
measurements and the real-clip tests. It can also drive the Gemini chat through Chrome on the creator's computer.

**Recommended split (option A):**

| Lane | Who | Work |
|---|---|---|
| Code | A separate Claude implementation thread, at effort `high` (the governance ceiling; no change to `config/model_routing.json`) | Writes Step 0 and Step 1 code and tests, runs CI and the six-clip media test, fixes failures at the root cause, and mirrors every change to Drive |
| G1 Eyes and ears | Gemini (chat, $0) | Watches and listens to the six raw clips (Claude copies them from HF to Drive) and returns per-clip JSON with timestamps: what is seen, who speaks, the words, non-speech sounds, action start and end. Claude compares this with the measurements. Agreement is the evidence MA-15 asks for; disagreement shows where Gemini cannot yet be trusted as a gate |
| G2 Contracts | Gemini | Writes the six missing schemas, `v4_1_schemas.json` and the manifest corrections (MA-03, MA-07, MA-12) as text against the named base SHA. Claude checks them against the code |
| G3 Review | Gemini | Reviews each Step 1 PR diff from a Drive snapshot and returns findings: real cross-vendor review (Amendment D) |
| G4 Pictures | Gemini | The 5 photo fixes and 5 bridge stills still open, in its free image tool |

**Option B** keeps the current arrangement: Gemini writes the Step 1 code and Claude applies and verifies it. It is slower
for Step 1, because every round trip goes through Drive zips and Gemini cannot run the media test.

**Chrome bridge:** with the creator's yes, and once he picks the browser (his Windows PC or the Mac), Claude opens Gemini in
a new tab and sends and reads the messages, so he no longer copies text between chats. It works only in a new tab. It never
changes settings, never uses a paid feature and never downloads a file without asking. He can watch it. I have not seen his
"Task mode" yet. I will use it for long reading and research tasks once I see what it offers in his account.

**Rules for both lanes:** one writer per file at a time. Every Gemini delivery is a zip against a named base SHA. Everything
goes through a branch and CI. GitHub and Drive stay in sync (standing rule, 2026-11-19). No paid call.

## 5. Step 0: one trusted state and working locks ($0)

| # | Item | Owner | Done when |
|---|---|---|---|
| 0.1 | PR #196 CI green | Claude | **Done** (F1) |
| 0.2 | Exact P1.2 commits: a bundle on Drive, the tree compared, the exact branch pushed (with OK) | Gemini → Claude | Tree hashes match, or the differing files are listed and explained |
| 0.3 | Decisions recorded: one row in `docs/DECISIONS_AND_OPEN_QUESTIONS.md` (the three decisions, precedence, MA-01..MA-18 accepted) and a `docs/PROGRESS.md` entry | Implementation thread | docs_lint green |
| 0.4a | Add `config/picture_route.json` and `config/retired_era.json` to `protected_files` in `config/model_routing.json`. That file is itself protected, so the creator's card answer is recorded first: `python -m explainer_engine.governance ok protected_config config/model_routing.json <answer id> "<his words>"` | Implementation thread | The hook refuses an edit to either file in a test |
| 0.4b | A scope job in `.github/workflows/quality.yml`: the PR's changed paths compared with `docs/architecture/v4_1_allowlists.json` (one list per slice), red on any path outside the list | Implementation thread | A unit test of the checker, plus one real red run on a test branch |
| 0.4c | Branch protection on `main` and on PR #195's base: the quality check must pass, no direct push | **The creator, one click**: https://github.com/vano1919/explainer-engine/settings/branches | Settings saved |
| 0.5 | Copy the six raw clips and their start pictures from HF to Drive for G1 | Claude | Files on Drive with sha256 list |

## 6. Step 1: switch on what exists, plus one licence gate ($0)

Each slice is one PR with its own allowlist. Rollback is a revert of that PR's merge: records only gain fields, and no
data is migrated. **Stop and ask** when a slice would need a test weakened, when a file outside its allowlist must change,
or when a refusal blocks a shot the creator has approved.

### 1.1 Fail-closed picture check before the LTX job (MA-05, first half)
- **Files:** `explainer_engine/videolane/scene.py` (`build`), `explainer_engine/training/pods/ltx/scene_run.py` (`job_spec`),
  tests (`tests/unit/test_videolane.py` plus one new test file).
- **Change:** `build` refuses a shot with its own start picture when `regeneration_required` is true **or** the state is
  `NO_PERCEPTION_INPUT` (F7). It writes `picture_check {state, regeneration_required, picture_sha256}` per shot into the
  scene file. Continuation shots (no own picture) are recorded as such. `job_spec` refuses a scene without `picture_check`
  or with a refused shot.
- **Not touched:** `modal_ltx_jobs.py` and `launch.json` (ladder, F8). The `read_job` refusal waits for Step 7 with an
  OR-23 plan, the OR-34 audit and the creator's word (cap: `launch.json` `smoke_usd` 0.50).
- **Tests:** a story-breaking conflict refuses; no perception refuses; a clean shot passes and records its sha; a scene file
  without `picture_check` is refused by `job_spec`. Existing assertions stay as they are.

### 1.2 One trim rule from the clip's own sound (part of MA-06)
- **Files:** `explainer_engine/videolane/ingest.py` (`speech_with_words`, `ingest_scene`, `whisper_edit_points`), tests.
- **Change:** one function decides where speech is: detector spans plus words, and **a word counts only where measured
  energy supports it** (F6). The two filters of `whisper_edit_points` (duplicate opening word, hallucinated tail token) move
  into it. `whisper_edit_points` calls the same function, so the film's `edit_points.json` and the runner's cut cannot drift
  apart. The clip record keeps `mute_tail_from_s`. `late_sound_out` stays as it is (already wired, L245).
- **Correction to Gemini's Step 1:** "wire `whisper_edit_points`" as written would put cuts on invented words (F6).
- **Tests in CI (no media):** the six recorded word lists plus energy windows built from the measurements. Expected: the
  S07_SH006 words before 7.8 s are rejected; S04_SH014 "You" is rejected; S03_SH007 keeps only the 2.4-2.8 s event;
  S07_SH005 is two non-speech events; S03_SH003 runs on until its level falls.
- **Media test (cloud, `media` marker):** the six raw clips from HF.
- **The creator listens** to two cuts (S06_SH008: which "Maybe" stays; S03_SH007) from short files on HF before merge.

### 1.3 Start-frame checks recorded, routes only proposed
- **Files:** `explainer_engine/videolane/ingest.py` (after the cut), `explainer_engine/videolane/storyboard.py`, tests.
  `plan.py` keeps its five functions.
- **Change:** after a clip arrives, frame 0 is compared with the pinned start picture (`compare_ltx_first_frame_to_source`)
  and `inspect_ltx_start_frame` runs on the picture. Both results go into the clip record, as REVIEW when inspection data is
  missing and never as PASS. `classify_ltx_natural_fit` becomes a REVIEW finding of the storyboard.
  `reroute_unnatural_ltx_shots(apply_routes=False)` writes `production/route_proposals.json`.
  `apply_and_persist_ltx_routes` is not called: a route change is the creator's (the 10/30/60 mix of D-131).
- **Runs after 1.2** (same file).
- **Tests:** the six clips' frame 0 against their start pictures (media; if a start picture is missing from HF, that clip is
  marked `NEEDS_EVIDENCE`); a unit test that missing inspection gives REVIEW.

### 1.4 Third-party media gate (Decision 3, MA-17)
- **Files:** `explainer_engine/audio/sources.py` (remove `bbc_remarc` from `SFX_EXCEPTIONS`, on the creator's word),
  `explainer_engine/qa/publish_check.py` (new PC-10), `docs/QA_SPECIFICATION.md` (the PC-10 row, its one canonical home), tests.
- **Change:** PC-10 reads `audio/stems_report.json` (`sounds_used`, `credits`) and the library manifest. **FAIL** for any used
  item with `commercial_use: false`. **FAIL** when the report is missing (not run never passes). **REVIEW** for
  `generated_terms_unverified` items and for CC BY music without its credit line in the description. It also writes
  `qa/third_party_media.json`, the per-film list.
- **Tests:** BBC in the log fails; Mixkit or CC0 passes; unverified generated audio gives REVIEW; a missing log fails.
  Re-resolving the 1914 sound plan leaves no BBC id in any pool.

### 1.5 One render path (Decision 2)
- **Files:** `tools/render_tools/mix.py` (refuses to write into `renders/final`, reports `preview_only`),
  `production/assemble.py` (only if the parity test shows a missing guard), `planning/full_film_2026-11-15/MAC_RUNBOOK.md`
  (runner commands only for a master), tests.
- **Parity slice ($0, CPU):** one 60-second slice through G8 and G9 from the same clips and clock. Per-shot frame counts and
  hashes are compared with `build_segments`' output, and the sound log is checked for library takes only.
  The report goes on HF.
- **Runs after 1.4.**

**Order:** 1.1 and 1.4 in parallel; 1.2, then 1.3; then 1.5. One writer per file.

## 7. After Step 1

Section 12 of the review continues unchanged: WP-01 contracts (with Gemini's G2 schemas), the re-issued WP-02 (conditions
C-01..C-12), audio evidence and event sync, QA severity, the 2.5D comparison and the Blender lab, then paid experiments one
at a time (the `read_job` worker change and its L3 smoke first, each with an OR-23 plan, the OR-34 audit and the creator's
word), then a 60-second slice and the full film.

## 8. Approvals and cost

| What | Who | When | Cost |
|---|---|---|---|
| This plan, the three decisions, option A or B | Creator, one card | now | $0 |
| `protected_files` edit (0.4a) | His card answer, recorded with `governance ok` | Step 0 | $0 |
| Branch protection (0.4c) | His click | Step 0 | $0 |
| Push Gemini's exact P1.2 branch | Covered by the card | Step 0 | $0 |
| Chrome bridge | His yes and the browser pick | any time | $0 |
| Merge of each Step 1 PR | His word per PR | Step 1 | $0 |
| Two cut checks and three replacement-sound samples | He listens | Step 1 | $0 |
| `read_job` worker change and paid L3 smoke | OR-23 plan, OR-34 audit, his word | Step 7 | cap $0.50 |

## 9. Message for Gemini (paste after the creator approves)

> Thank you. The creator has decided:
> 1. **P1.2 accepted.** PR #196 (`e4521cd`, your 31 files on `fc35615`) passed CI: 4476 passed, 0 failed. Please upload
>    `git bundle create p1_2.bundle argon/p1-2-timing-contract` to Drive and send `git rev-parse eb80e443 eb80e443^{tree} 0592114`,
>    so the exact commits can be pushed to GitHub. V4.1 continues the PR #195 plan. Precedence: decision log, then
>    DEC-2026-11-17-01 and the PR #195 plan, then V4.1 as amended by MA-01..MA-18; each conflict gets an ADR line.
> 2. **One render path: `episode/run.py`.** Sound comes only from G8 `audio/stems`. Since `0e299cd`, `tools/render_tools/mix.py`
>    synthesizes every bed (band-passed noise, L547-567, L720), the map sounds (L782) and the music (sine chords, L570-598,
>    L795), against D-136 and OV-56, and it plays no library file. It becomes preview only. `build_segments`' guards move into
>    G9 or are called by G9, decided by a 60-second parity slice.
> 3. **No BBC RemArc sound in a monetised master.** Replace them from the same pools (crowd_talking_big, campfire_crackles,
>    forest_wind_birds, soft_thud, ...). Add PC-10 to `qa/publish_check.py`, reading `audio/stems_report.json`.
>
> Corrections to your Step 1: (a) the picture check is fail-closed: `NO_PERCEPTION_INPUT` refuses too, not only
> `regeneration_required`; `read_job` is not touched now, because it changes `worker_sha` and needs a paid L3 smoke.
> (b) Do not wire `whisper_edit_points` as it is: the recorded words of S07_SH006 ("I'll see you next time", 0-7.64 s, while
> the clip's only onset is at 7.80 s), S04_SH014 and S03_SH007 are not supported by the measured sound. One trim function
> (detector spans + words + an energy check) is used by both ingest and the edit points. (c) The start-frame checks record
> REVIEW; route changes are written only as proposals.
>
> Your tasks now (no code for Step 1, no paid calls; deliver each as a file on Drive against base `e4521cd`):
> G1: watch and listen to the six raw 1914 clips we put on Drive and return JSON per clip with timestamps (what is seen, who
> speaks, the exact words, non-speech sounds, action start and end). G2: the six missing schemas, `v4_1_schemas.json` and the
> manifest corrections (MA-03, MA-07, MA-12). G3: review each Step 1 PR diff we send and list findings with file:line.
> G4: the 5 photo fixes and 5 bridge stills still open, in the chat's image tool.

## 10. What changes against Gemini's proposed Step 0 and Step 1

| Gemini's item | Change | Why |
|---|---|---|
| Push `eb80e443` + CI | Done as PR #196 (green); exact commits through a bundle | F1 |
| Protect `picture_route.json`, `retired_era.json` | Kept; needs the creator's recorded word because `model_routing.json` is protected | governance hook |
| PR allowlist CI check | Kept, plus branch protection and one demonstrated red run | MA-11 |
| `regeneration_required` blocks `scene.build`, `job_spec`, `read_job` | `scene.build` and `job_spec` now, fail-closed; `read_job` in Step 7 | F7, F8 |
| Wire `whisper_edit_points` | One trim function with an energy check instead | F6 |
| Wire the five start-frame checks | Record and propose only; no automatic reroute | route mix is the creator's |
| BBC check in `publish_check.py` | Kept as PC-10, reading the G8 sound log; plus removal from the pools | F3, F5 |
| (missing) | Step 1.5: one render path, `mix.py` preview only, parity slice | F2, MA-18 |
